"""Compare routing algorithms on the synthetic claim-routing simulator.

Trains several learners with the same budget, evaluates them on the same
held-out seeds as ``rl.training``, and writes a comparison report:

    random, least_workload, reward_aware   hand-written baselines (no training)
    ppo           PPO from scratch            (same per-employee network as production)
    ppo_bc        PPO warm-started by behaviour cloning, then fine-tuned (production recipe)
    a2c           A2C from scratch            (same network)
    maskable_ppo  MaskablePPO from scratch    (same network; absent employees masked out)
    dqn           DQN from scratch            (per-employee Q-network)
    linucb        LinUCB contextual bandit    (linear model, no neural network)

Run from the ``backend`` directory:

    python -m rl.compare_algorithms --timesteps 50000

All results describe the synthetic simulator only. This script never touches
the production model at ``rl/models/claim_routing_ppo.zip``.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from stable_baselines3 import A2C, DQN, PPO
from stable_baselines3.dqn.policies import DQNPolicy, QNetwork

from .environment import MAX_AGENTS, ClaimRoutingEnv
from .evaluation import Policy, evaluate_across_seeds, masked_model_action
from .policy import AGENT_FEATURES, CLAIM_FEATURES, AgentScorer, AgentScoringPolicy
from .training import DEFAULT_DATASET_PATH, pretrain_policy_from_transitions


RL_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = RL_DIR / "reports"
DEFAULT_MODEL_DIR = RL_DIR / "models" / "comparison"
ALL_ALGORITHMS = ("ppo", "ppo_bc", "a2c", "maskable_ppo", "dqn", "linucb")
BASELINES = ("random", "least_workload", "reward_aware")
METRICS = (
    "average_reward",
    "average_wait_time",
    "average_workload_standard_deviation",
    "skill_mismatch_rate",
)
# Higher is better only for reward.
HIGHER_IS_BETTER = {"average_reward"}


# ---------------------------------------------------------------- networks


class _PairQ(torch.nn.Module):
    """Per-employee Q-values: one shared scorer over [claim + employee] features."""

    def __init__(self, hidden: int = 64) -> None:
        super().__init__()
        self.scorer = torch.nn.Sequential(
            torch.nn.Linear(CLAIM_FEATURES + AGENT_FEATURES, hidden), torch.nn.ReLU(),
            torch.nn.Linear(hidden, hidden), torch.nn.ReLU(),
            torch.nn.Linear(hidden, 1),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        claim = features[:, :CLAIM_FEATURES]
        agents = features[:, CLAIM_FEATURES:].reshape(-1, MAX_AGENTS, AGENT_FEATURES)
        pairs = torch.cat([claim.unsqueeze(1).expand(-1, MAX_AGENTS, -1), agents], dim=-1)
        return self.scorer(pairs).squeeze(-1)


class AgentQNetwork(QNetwork):
    """DQN Q-network that scores every employee with the same small network."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.q_net = _PairQ()


class AgentQPolicy(DQNPolicy):
    def make_q_net(self) -> QNetwork:
        net_args = self._update_features_extractor(self.net_args, features_extractor=None)
        return AgentQNetwork(**net_args).to(self.device)


def _maskable_policy_class() -> type:
    """MaskablePPO policy with the production per-employee scorer (needs sb3-contrib)."""
    from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy

    class MaskableAgentScoringPolicy(MaskableActorCriticPolicy):
        def _build_mlp_extractor(self) -> None:
            self.mlp_extractor = AgentScorer()

        def _build(self, lr_schedule) -> None:
            super()._build(lr_schedule)
            self.action_net = torch.nn.Identity()
            self.optimizer = self.optimizer_class(
                self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs
            )

    return MaskableAgentScoringPolicy


# ---------------------------------------------------------------- bandit


class LinUCB:
    """Contextual bandit with one shared linear model over (claim, employee) features.

    Each step it scores every available employee as theta . x + alpha * sqrt(x' A^-1 x)
    (estimate plus an exploration bonus), assigns the claim, and updates on the
    immediate reward. It does not plan for future workload, unlike the RL methods.
    """

    def __init__(self, alpha: float = 0.5, ridge: float = 1.0) -> None:
        self.alpha = alpha
        self.dimension = 10
        self.A = np.eye(self.dimension) * ridge
        self.b = np.zeros(self.dimension)

    @staticmethod
    def features(observation: np.ndarray) -> np.ndarray:
        observation = np.asarray(observation, dtype=np.float64).reshape(-1)
        claim = observation[:CLAIM_FEATURES]
        agents = observation[CLAIM_FEATURES:].reshape(MAX_AGENTS, AGENT_FEATURES)
        queue, workload, skill = agents[:, 0], agents[:, 1], agents[:, 2]
        claim_rows = np.repeat(claim[None, :], MAX_AGENTS, axis=0)
        return np.column_stack([
            np.ones(MAX_AGENTS), claim_rows, queue, workload, skill,
            queue * claim[2], workload * claim[2], 1.0 - skill,
        ])

    def act(self, observation: np.ndarray, explore: bool) -> int:
        x = self.features(observation)
        available = np.asarray(observation).reshape(-1)[CLAIM_FEATURES + 3::AGENT_FEATURES][:MAX_AGENTS] > 0.5
        a_inv = np.linalg.inv(self.A)
        scores = x @ (a_inv @ self.b)
        if explore:
            scores = scores + self.alpha * np.sqrt(np.einsum("ij,jk,ik->i", x, a_inv, x))
        return int(np.argmax(np.where(available, scores, -np.inf)))

    def update(self, observation: np.ndarray, action: int, reward: float) -> None:
        x = self.features(observation)[action]
        self.A += np.outer(x, x)
        self.b += reward * x

    def learn(self, total_timesteps: int, seed: int) -> None:
        env = ClaimRoutingEnv(n_agents=MAX_AGENTS, max_episode_steps=100, randomize_fleet=True)
        observation, _ = env.reset(seed=seed)
        for _ in range(total_timesteps):
            action = self.act(observation, explore=True)
            next_observation, reward, terminated, truncated, _ = env.step(action)
            self.update(observation, action, float(reward))
            observation = next_observation
            if terminated or truncated:
                observation, _ = env.reset()

    def save(self, path: Path) -> None:
        np.savez(path, A=self.A, b=self.b, alpha=self.alpha)


# ---------------------------------------------------------------- policies


def q_value_action(model: DQN, observation: np.ndarray) -> int:
    """Highest-Q available employee (padded and absent slots are skipped)."""
    observation_tensor, _ = model.policy.obs_to_tensor(observation)
    with torch.no_grad():
        q_values = model.q_net(observation_tensor).cpu().numpy().reshape(-1)
    available = np.asarray(observation).reshape(-1)[CLAIM_FEATURES + 3::AGENT_FEATURES][:MAX_AGENTS] > 0.5
    return int(np.argmax(np.where(available, q_values, -np.inf)))


def _make_env() -> ClaimRoutingEnv:
    return ClaimRoutingEnv(n_agents=MAX_AGENTS, max_episode_steps=100, randomize_fleet=True)


def train_algorithm(
    name: str,
    *,
    total_timesteps: int,
    seed: int,
    model_dir: Path,
    dataset_path: Path,
    pretrain_epochs: int,
) -> tuple[Policy, dict[str, Any]]:
    """Train one algorithm and return (evaluation policy, training details)."""
    model_dir.mkdir(parents=True, exist_ok=True)
    details: dict[str, Any] = {"timesteps": total_timesteps}

    if name == "linucb":
        bandit = LinUCB()
        bandit.learn(total_timesteps, seed)
        bandit.save(model_dir / "linucb.npz")
        details["model"] = "LinUCB (10 linear features, alpha=0.5)"
        return (lambda _env, observation: bandit.act(observation, explore=False)), details

    env = _make_env()
    if name in ("ppo", "ppo_bc"):
        model = PPO(AgentScoringPolicy, env, seed=seed, verbose=0, device="cpu",
                    learning_rate=3e-4, n_steps=2048, batch_size=256, gamma=0.99)
        if name == "ppo_bc":
            # Production recipe: copy the least-workload expert, then fine-tune gently.
            details["behaviour_cloning"] = pretrain_policy_from_transitions(
                model, dataset_path, epochs=pretrain_epochs,
            )
            model.learning_rate = 1e-5
            model.lr_schedule = lambda _progress: 1e-5
            model.clip_range = lambda _progress: 0.1
        details["model"] = "PPO + per-employee actor-critic"
    elif name == "a2c":
        model = A2C(AgentScoringPolicy, env, seed=seed, verbose=0, device="cpu",
                    learning_rate=7e-4, n_steps=16, gamma=0.99)
        details["model"] = "A2C + per-employee actor-critic"
    elif name == "maskable_ppo":
        from sb3_contrib import MaskablePPO

        model = MaskablePPO(_maskable_policy_class(), env, seed=seed, verbose=0, device="cpu",
                            learning_rate=3e-4, n_steps=2048, batch_size=256, gamma=0.99)
        details["model"] = "MaskablePPO + per-employee actor-critic (invalid actions masked)"
    elif name == "dqn":
        model = DQN(AgentQPolicy, env, seed=seed, verbose=0, device="cpu",
                    learning_rate=5e-4, buffer_size=50_000, learning_starts=1_000,
                    batch_size=128, train_freq=4, target_update_interval=1_000,
                    exploration_fraction=0.3, exploration_final_eps=0.05, gamma=0.99)
        details["model"] = "DQN + per-employee Q-network"
    else:
        raise ValueError(f"Unknown algorithm: {name}")

    model.learn(total_timesteps=total_timesteps)
    model.save(str(model_dir / name))
    if name == "dqn":
        return (lambda _env, observation: q_value_action(model, observation)), details
    return (lambda _env, observation: masked_model_action(model, observation)), details


# ---------------------------------------------------------------- report


def _beats_heuristic(means: dict[str, float], heuristic: dict[str, float]) -> dict[str, bool]:
    return {
        metric: (means[metric] >= heuristic[metric]) if metric in HIGHER_IS_BETTER
        else (means[metric] <= heuristic[metric])
        for metric in METRICS
    }


def build_markdown(report: dict[str, Any]) -> str:
    policies = report["evaluation"]["policies"]
    heuristic = policies["least_workload"]["mean"]
    lines = [
        "# Claim routing: algorithm comparison",
        "",
        f"Synthetic simulator only. {report['timesteps']:,} training steps per learner, "
        f"evaluated on {len(report['evaluation']['seeds'])} held-out seeds x "
        f"{report['evaluation']['steps_per_seed']} claims. Mean (+/- std across seeds).",
        "",
        "| Rank | Policy | Reward (higher better) | Wait (lower) | Workload std (lower) | Skill mismatch (lower) | Gate vs heuristic | Train time |",
        "|---|---|---|---|---|---|---|---|",
    ]
    ranked = sorted(policies, key=lambda name: policies[name]["mean"]["average_reward"], reverse=True)
    for rank, name in enumerate(ranked, start=1):
        mean, std = policies[name]["mean"], policies[name]["std"]
        if name in BASELINES:
            gate, seconds = ("(baseline)" if name != "least_workload" else "(reference)"), "-"
        else:
            checks = _beats_heuristic(mean, heuristic)
            gate = f"{'PASS' if all(checks.values()) else 'FAIL'} ({sum(checks.values())}/4)"
            seconds = f"{report['training'][name]['train_seconds']:.0f}s"
        lines.append(
            f"| {rank} | {name} | {mean['average_reward']:.3f} +/- {std['average_reward']:.3f} "
            f"| {mean['average_wait_time']:.3f} | {mean['average_workload_standard_deviation']:.3f} "
            f"| {mean['skill_mismatch_rate']:.1%} | {gate} | {seconds} |"
        )
    lines += [
        "",
        "Gate: the learner must be at least as good as `least_workload` on all four metrics "
        "(the same rule `rl.training` uses before a model may give advice).",
    ]
    return "\n".join(lines) + "\n"


def save_chart(report: dict[str, Any], path: Path) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    policies = report["evaluation"]["policies"]
    names = sorted(policies, key=lambda name: policies[name]["mean"]["average_reward"], reverse=True)
    titles = {
        "average_reward": "Average reward (higher is better)",
        "average_wait_time": "Average wait (lower is better)",
        "average_workload_standard_deviation": "Workload imbalance (lower is better)",
        "skill_mismatch_rate": "Skill mismatch rate (lower is better)",
    }
    figure, axes = plt.subplots(2, 2, figsize=(13, 8))
    for axis, metric in zip(axes.flat, METRICS):
        values = [policies[name]["mean"][metric] for name in names]
        errors = [policies[name]["std"][metric] for name in names]
        colors = ["#9ca3af" if name in BASELINES else "#2563eb" for name in names]
        axis.bar(names, values, yerr=errors, color=colors, capsize=3)
        axis.axhline(policies["least_workload"]["mean"][metric], color="#dc2626", linestyle="--", linewidth=1)
        axis.set_title(titles[metric])
        axis.tick_params(axis="x", rotation=35)
    figure.suptitle("Claim routing algorithms (synthetic simulator; red line = least_workload heuristic)")
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)
    return True


def compare(
    *,
    algorithms: tuple[str, ...] = ALL_ALGORITHMS,
    total_timesteps: int = 50_000,
    evaluation_steps: int = 100,
    evaluation_seed_count: int = 10,
    seed: int = 123,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    model_dir: Path = DEFAULT_MODEL_DIR,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    pretrain_epochs: int = 100,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    unknown = set(algorithms) - set(ALL_ALGORITHMS)
    if unknown:
        raise ValueError(f"Unknown algorithm(s): {', '.join(sorted(unknown))}")

    learned: dict[str, Policy] = {}
    training: dict[str, Any] = {}
    for name in algorithms:
        log(f"Training {name} ({total_timesteps:,} steps)...")
        started = time.perf_counter()
        policy, details = train_algorithm(
            name, total_timesteps=total_timesteps, seed=seed, model_dir=model_dir,
            dataset_path=dataset_path, pretrain_epochs=pretrain_epochs,
        )
        details["train_seconds"] = round(time.perf_counter() - started, 1)
        learned[name], training[name] = policy, details
        log(f"  done in {details['train_seconds']}s")

    # Same held-out seeds as rl.training, so numbers are comparable with the production report.
    seeds = tuple(range(seed + 10_000, seed + 10_000 + evaluation_seed_count))
    log("Evaluating all policies on held-out seeds...")
    evaluation = evaluate_across_seeds(steps=evaluation_steps, seeds=seeds, extra_policies=learned)

    heuristic = evaluation["policies"]["least_workload"]["mean"]
    report = {
        "simulator_only": True,
        "advisory_only": True,
        "seed": seed,
        "timesteps": total_timesteps,
        "algorithms": list(algorithms),
        "training": training,
        "evaluation": evaluation,
        "gate_vs_least_workload": {
            name: _beats_heuristic(evaluation["policies"][name]["mean"], heuristic) for name in algorithms
        },
        "note": "Synthetic simulator metrics; not real claim-handling performance.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "algorithm_comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = build_markdown(report)
    (output_dir / "algorithm_comparison.md").write_text(markdown, encoding="utf-8")
    if save_chart(report, output_dir / "algorithm_comparison.png"):
        log(f"Chart: {output_dir / 'algorithm_comparison.png'}")
    log("")
    log(markdown)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--algorithms", default=",".join(ALL_ALGORITHMS),
                        help=f"comma-separated subset of: {', '.join(ALL_ALGORITHMS)}")
    parser.add_argument("--timesteps", type=int, default=50_000)
    parser.add_argument("--evaluation-steps", type=int, default=100)
    parser.add_argument("--evaluation-seeds", type=int, default=10)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--pretrain-epochs", type=int, default=100)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET_PATH)
    args = parser.parse_args()
    compare(
        algorithms=tuple(name.strip() for name in args.algorithms.split(",") if name.strip()),
        total_timesteps=args.timesteps,
        evaluation_steps=args.evaluation_steps,
        evaluation_seed_count=args.evaluation_seeds,
        seed=args.seed,
        output_dir=args.output_dir,
        model_dir=args.model_dir,
        dataset_path=args.dataset_path,
        pretrain_epochs=args.pretrain_epochs,
    )


if __name__ == "__main__":
    main()
