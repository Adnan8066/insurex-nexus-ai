# Claim routing RL advisory simulator

This package trains and serves a **simulation-only recommendation policy**. It
does not update claims, investigator assignments, repair jobs, or any database
record. A human must review every recommendation. The reward coefficients,
agent skill tiers, workload units, and simulated service rate are assumptions;
they are not measured insurance operating data.

## Install

From the repository root, install the backend dependencies:

```powershell
python -m pip install -r backend/django_backend/requirements.txt
```

The RL dependencies are Gymnasium 1.4 and Stable-Baselines3 2.9. If you install
only a minimal backend environment, install those two packages separately.

## Train, compare, and save PPO

Run it from the `backend` directory:

```powershell
python -m rl.training --timesteps 50000 --evaluation-steps 100 --evaluation-seeds 10 --seed 123 --dataset-path rl/data/synthetic_claim_routing_transitions.csv
```

Training first warm-starts the PPO actor by behavior-cloning the action choices
in `synthetic_claim_routing_transitions.csv` (100 epochs by default), then
continues PPO learning by interacting with the simulator. The CSV's logged
rewards are not used in that warm start: PPO is an on-policy algorithm, and
replaying an old action's reward as if it came from PPO's newly selected action
would train against mismatched outcomes. Use `--pretrain-epochs` to change the
warm-start duration. Regenerate the CSV before training so its actions come
from the least-workload expert policy:

```powershell
python -m rl.generate_dataset --episodes 200 --steps 100 --seed 2026 --policy least_workload
```

This dataset is synthetic; its behavior labels encode a heuristic, not human
or adjuster decisions. The simulator's wait reward weight is 10 to better
align the training objective with the wait-time evaluation metric. These are
experimental tuning choices; a passing synthetic gate still does not establish
real-world routing quality.

The command evaluates a random policy and a least-estimated-workload heuristic
for 100 simulated arrivals, trains PPO, and evaluates all three on ten held-out
seeds. It prints mean, variation, and per-seed reward, wait, workload standard
deviation, and skill mismatch metrics. The weights are saved to
`backend/rl/models/claim_routing_ppo.zip`. Use `--evaluation-seeds` and
`--model-path` to change the evaluation size and artifact location. Training
output and weights are ignored by Git; keep the archive and its evaluation
report together in a controlled artifact store for deploys.
The evaluation report includes a gate that requires PPO to beat the
least-workload policy on average reward, wait, workload imbalance, and skill
mismatch across all held-out seeds. A failed gate marks the candidate as not
qualified for an advisory pilot; do not promote it based only on training success.

The simulator supports 3–5 agents. PPO is trained against the five-agent
observation/action space. The recommendation service accepts 3–5 current agent
records, pads missing slots, and filters unavailable agents from its ranking.

## Recommendation input

The service expects normalized claim values between 0 and 1 and three to five
agent records:

```python
claim_data = {
    "complexity_score": 0.7,
    "severity_score": 0.6,
    "processing_difficulty": 0.5,
}
active_agents_status = [
    {"id": "agent-1", "queue_length": 2, "workload": 12.0,
     "skill_tier": 4, "available": True},
    # Provide at least two more agents, up to five total.
]
```

```python
from rl.recommendation import ClaimRecommendationEngine

engine = ClaimRecommendationEngine.load()
advice = engine.get_routing_recommendations(claim_data, active_agents_status)
```

The return value includes a recommended agent ID, predicted simulator wait,
workload impact, alternatives with normalized relative policy-preference
percentages, and explicit human-review/advisory flags. Percentages are not
calibrated probabilities of successful claim handling.

## Agent and claim data

Apply Django migrations, then in Django Admin create one `Routing agent profile`
for each eligible employee or investigator. Set the skill tier and availability
from an approved source. The application calculates queue length from active
claims assigned to each person and estimates workload using the simulator's
documented feature weights. Estimated wait is not a measured time. The policy
accepts at most five candidates per recommendation. The website requires a
reviewer to choose the 3–5 candidates when the configured roster is larger.

`GET /api/v1/ai/routing-agents/` supplies the configured team.
`GET /api/v1/ai/routing-claims/` supplies unassigned open claims with normalized
features derived from incident severity, vehicles, injuries, property damage,
witnesses, and police reports. Those feature weights are assumptions; validate
them with claim operations staff before relying on the advice.

## Recommendation and human feedback API

After training a model, authorized staff can request advice at:

```text
POST /api/v1/ai/route-recommendation/
```

The endpoint requires a JWT and an employee/admin/investigator account. The
request has `claim_data` and `active_agents_status` fields matching the example.
The recommendation request itself does not write to the database. It returns a
signed, short-lived review token. A staff member can explicitly post a useful / not
useful decision to `POST /api/v1/ai/route-recommendation/review/`; this saves a
feedback snapshot only and never changes a claim or assignment. Review feedback
is visible in Django Admin. Check model availability at
`GET /api/v1/ai/routing-model-status/`.

Set `CLAIM_ROUTING_MODEL_PATH` to the deployed PPO archive path. Without the
artifact or dependencies, model status is not ready and recommendation inference
returns HTTP 503. Model status also checks whether the accompanying evaluation
report passed the synthetic advisory-pilot gate. The repository does not include
a deployable weight archive; publish the qualified archive and its
`.evaluation.json` report to your controlled artifact store and provide both to
the backend deployment. `CLAIM_ROUTING_MODEL_PATH` can point at a mounted or
downloaded artifact path. The Render configuration includes the inference
dependencies, but the model artifact still needs to be supplied by the deployer.
The Render config enforces the evaluation gate with
`CLAIM_ROUTING_ENFORCE_EVALUATION_GATE=True`; requests return HTTP 503 until the
report passes. Local development leaves the gate off so the experimental UI can
be exercised, and the status page still warns when the candidate is unqualified.
The gate compares PPO with the least-workload heuristic on held-out mean reward,
wait, imbalance, and mismatch metrics.

## Automatic claim assignment

New claim intake calls the routing hook after the claim is saved. Assignment is
off by default. It proceeds only when `CLAIM_ROUTING_AUTO_ASSIGN_ENABLED=True`,
the deployed model's adjacent `.evaluation.json` passes the evaluation gate,
and there are 3-5 active, available, non-demo employee routing profiles. The
selected employee must also meet the model's required skill tier. Otherwise,
the claim remains unassigned and can be handled through the existing staff
assignment flow. Successful assignments are recorded in the claim timeline.

Before enabling this setting, retrain and evaluate with representative,
reviewed operational data. The current evaluation is synthetic and fails the
gate, so it cannot trigger automatic assignments. Do not enable the setting
with that candidate.

## Checks

From the `backend` directory:

```powershell
python -m pytest rl/tests
python django_backend/manage.py test apps.assessments
```

Model metrics from this synthetic environment must not be described as real
claim outcomes or used for automatic claim approval, denial, or settlement.
