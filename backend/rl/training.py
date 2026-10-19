"""PPO training and baseline comparison for the synthetic routing simulator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from stable_baselines3 import PPO

from .environment import MAX_AGENTS, ClaimRoutingEnv
from .evaluation import evaluate_across_seeds, evaluate_baselines, evaluate_model


DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "claim_routing_ppo.zip"


def train_and_evaluate(
    *,
    total_timesteps: int = 50_000,
    evaluation_steps: int = 100,
    evaluation_seed_count: int = 10,
    seed: int = 123,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> dict[str, Any]:
    """Train PPO, save its weights, and report baseline/PPO metrics.

    Metrics describe only the generated simulator. They are not estimates of
    real claim outcomes and must not be used to automate assignments.
    """
    if total_timesteps < 1:
        raise ValueError("total_timesteps must be positive.")
    if evaluation_steps < 1:
        raise ValueError("evaluation_steps must be positive.")
    if evaluation_seed_count < 1:
        raise ValueError("evaluation_seed_count must be positive.")

    output_path = Path(model_path).expanduser().resolve()
    if output_path.suffix.lower() != ".zip":
        output_path = output_path.with_suffix(".zip")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    env = ClaimRoutingEnv(n_agents=MAX_AGENTS, max_episode_steps=100)
    model = PPO(
        "MlpPolicy",
        env,
        seed=seed,
        verbose=0,
        learning_rate=3e-4,
        n_steps=256,
        batch_size=64,
        gamma=0.99,
        device="cpu",
    )
    model.learn(total_timesteps=total_timesteps)
    model.save(str(output_path.with_suffix("")))

    results = {
        "simulator_only": True,
        "advisory_only": True,
        "seed": seed,
        "training_timesteps": total_timesteps,
        "evaluation_steps": evaluation_steps,
        "model_path": str(output_path),
        "baselines": evaluate_baselines(steps=evaluation_steps, seed=seed),
        "ppo": evaluate_model(
            model, steps=evaluation_steps, seed=seed, n_agents=MAX_AGENTS
        ),
        "robust_evaluation": evaluate_across_seeds(
            steps=evaluation_steps,
            seeds=tuple(range(seed + 10_000, seed + 10_000 + evaluation_seed_count)),
            model=model,
            n_agents=MAX_AGENTS,
        ),
        "note": (
            "Metrics use synthetic assumptions. Do not treat them as real-world "
            "performance or as authority to route a claim automatically."
        ),
    }
    robust_policies = results['robust_evaluation']['policies']
    ppo_mean = robust_policies['ppo']['mean']
    heuristic_mean = robust_policies['least_workload']['mean']
    quality_gates = {
        'average_reward_at_least_heuristic': ppo_mean['average_reward'] >= heuristic_mean['average_reward'],
        'average_wait_no_worse_than_heuristic': ppo_mean['average_wait_time'] <= heuristic_mean['average_wait_time'],
        'workload_imbalance_no_worse_than_heuristic': (
            ppo_mean['average_workload_standard_deviation']
            <= heuristic_mean['average_workload_standard_deviation']
        ),
        'skill_mismatch_no_worse_than_heuristic': ppo_mean['skill_mismatch_rate'] <= heuristic_mean['skill_mismatch_rate'],
    }
    results['evaluation_gate'] = {
        'passed': all(quality_gates.values()),
        'checks': quality_gates,
        'note': 'Passing synthetic comparisons is necessary for an advisory pilot, not proof of real-world suitability.',
    }
    results['evaluation_report_path'] = str(output_path.with_suffix('.evaluation.json'))
    report_path = output_path.with_suffix(".evaluation.json")
    temporary_report_path = report_path.with_suffix(report_path.suffix + ".tmp")
    temporary_report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    temporary_report_path.replace(report_path)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timesteps", type=int, default=50_000)
    parser.add_argument("--evaluation-steps", type=int, default=100)
    parser.add_argument("--evaluation-seeds", type=int, default=10)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    args = parser.parse_args()

    result = train_and_evaluate(
        total_timesteps=args.timesteps,
        evaluation_steps=args.evaluation_steps,
        evaluation_seed_count=args.evaluation_seeds,
        seed=args.seed,
        model_path=args.model_path,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
