
import json
from pathlib import Path

from stable_baselines3 import PPO

from rl.evaluation import evaluate_across_seeds

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "claim_routing_ppo.zip"
REPORT_PATH = BASE_DIR / "evaluation_report.json"

model = PPO.load(str(MODEL_PATH), device="cpu")

results = evaluate_across_seeds(
    steps=100,
    seeds=tuple(range(10)),
    model=model,
)

REPORT_PATH.write_text(
    json.dumps(results, indent=2),
    encoding="utf-8",
)

print("\n=== RL EVALUATION SUMMARY ===")

for policy, metrics in results["policies"].items():
    print(f"\nPolicy: {policy}")
    for metric in (
        "average_reward",
        "average_wait_time",
        "average_workload_standard_deviation",
        "skill_mismatch_rate",
    ):
        if metric in metrics:
            print(f"  {metric}: {metrics[metric]}")

print(f"\nReport saved to: {REPORT_PATH}")
