"""PPO training and baseline comparison for the synthetic routing simulator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from stable_baselines3 import PPO

from .environment import MAX_AGENTS, ClaimRoutingEnv
from .evaluation import evaluate_across_seeds, evaluate_baselines, evaluate_model


DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "claim_routing_ppo.zip"
DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "data" / "synthetic_claim_routing_transitions.csv"


def pretrain_policy_from_transitions(
    model: PPO,
    dataset_path: str | Path,
    *,
    epochs: int = 5,
    batch_size: int = 256,
) -> dict[str, Any]:
    """Warm-start PPO's actor by imitating the logged behavior actions."""
    if epochs < 1 or batch_size < 1:
        raise ValueError("pretraining epochs and batch size must be positive")

    observations: list[list[float]] = []
    actions: list[int] = []

    with Path(dataset_path).expanduser().open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "action_agent_index",
            "behavior_policy",
            *[f"obs_{i}" for i in range(3 + MAX_AGENTS * 4)],
        }

        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                "Dataset must contain behavior_policy, action_agent_index, and "
                f"obs_0 through obs_{2 + MAX_AGENTS * 4}. "
                "Regenerate it with rl.generate_dataset."
            )

        for row in reader:
            if row["behavior_policy"] != "least_workload":
                raise ValueError(
                    "PPO warm-start requires least_workload expert actions. "
                    "Regenerate the CSV with: "
                    "python -m rl.generate_dataset --policy least_workload"
                )

            try:
                obs = [
                    float(row[f"obs_{i}"])
                    for i in range(3 + MAX_AGENTS * 4)
                ]
                action = int(row["action_agent_index"])
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(
                    "Dataset contains a malformed observation or action."
                ) from exc

            if not np.isfinite(obs).all() or not 0 <= action < MAX_AGENTS:
                raise ValueError(
                    "Dataset contains a non-finite observation or out-of-range action."
                )

            observations.append(obs)
            actions.append(action)

    if not actions:
        raise ValueError("Dataset has no transitions.")

    device = model.device
    obs_tensor = torch.as_tensor(
        np.asarray(observations), dtype=torch.float32, device=device
    )
    action_tensor = torch.as_tensor(
        actions, dtype=torch.long, device=device
    )

    optimizer = torch.optim.Adam(model.policy.parameters(), lr=1e-4)
    model.policy.set_training_mode(True)
    losses: list[float] = []

    for _ in range(epochs):
        order = torch.randperm(len(actions), device=device)

        for indices in order.split(batch_size):
            distribution = model.policy.get_distribution(
                obs_tensor[indices]
            ).distribution
            loss = torch.nn.functional.cross_entropy(
                distribution.logits, action_tensor[indices]
            )

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.policy.parameters(), 0.5)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))

    model.policy.set_training_mode(False)

    return {
        "method": "behavior_cloning_actor_warm_start",
        "dataset_path": str(Path(dataset_path).expanduser().resolve()),
        "transitions": len(actions),
        "epochs": epochs,
        "mean_training_loss": round(float(np.mean(losses)), 6),
        "uses_logged_rewards_for_pretraining": False,
    }


def train_and_evaluate(
    *,
    total_timesteps: int = 50_000,
    evaluation_steps: int = 100,
    evaluation_seed_count: int = 10,
    seed: int = 123,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    pretrain_epochs: int = 100,
) -> dict[str, Any]:
    """Evaluate behavior cloning, fine-tune with PPO, and compare baselines.

    All metrics describe the synthetic simulator only. They must not be used
    to automate real insurance claim assignments.
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

    # Use identical seeds for BC-only and post-PPO evaluations.
    evaluation_seeds = tuple(
        range(seed + 10_000, seed + 10_000 + evaluation_seed_count)
    )

    env = ClaimRoutingEnv(
        n_agents=MAX_AGENTS,
        max_episode_steps=100,
    )

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

    # Phase 1: behavior cloning.
    dataset_pretraining = pretrain_policy_from_transitions(
        model,
        dataset_path,
        epochs=pretrain_epochs,
    )

    # Save and evaluate a separate snapshot BEFORE PPO fine-tuning.
    bc_only_model_path = output_path.with_name(
        f"{output_path.stem}_bc_only.zip"
    )
    model.save(str(bc_only_model_path.with_suffix("")))

    bc_only_robust_evaluation = evaluate_across_seeds(
        steps=evaluation_steps,
        seeds=evaluation_seeds,
        model=model,
        n_agents=MAX_AGENTS,
    )

    # Phase 2: PPO fine-tuning.
    model.learn(total_timesteps=total_timesteps)
    model.save(str(output_path.with_suffix("")))

    # Phase 3: evaluate the final PPO policy.
    results = {
        "simulator_only": True,
        "advisory_only": True,
        "seed": seed,
        "training_timesteps": total_timesteps,
        "reward_weights": {
            "wait": env.reward_weights.wait,
            "imbalance": env.reward_weights.imbalance,
            "skill_mismatch": env.reward_weights.skill_mismatch,
            "assignment": env.reward_weights.assignment,
        },
        "dataset_pretraining": dataset_pretraining,
        "dataset_transitions_used": dataset_pretraining["transitions"],
        "evaluation_steps": evaluation_steps,
        "evaluation_seeds": list(evaluation_seeds),
        "bc_only_model_path": str(bc_only_model_path),
        "bc_only_robust_evaluation": bc_only_robust_evaluation,
        "model_path": str(output_path),
        "baselines": evaluate_baselines(
            steps=evaluation_steps,
            seed=seed,
        ),
        "ppo": evaluate_model(
            model,
            steps=evaluation_steps,
            seed=seed,
            n_agents=MAX_AGENTS,
        ),
        "robust_evaluation": evaluate_across_seeds(
            steps=evaluation_steps,
            seeds=evaluation_seeds,
            model=model,
            n_agents=MAX_AGENTS,
        ),
        "note": (
            "Metrics use synthetic assumptions. Do not treat them as real-world "
            "performance or as authority to route a claim automatically."
        ),
    }

    robust_policies = results["robust_evaluation"]["policies"]
    ppo_mean = robust_policies["ppo"]["mean"]
    heuristic_mean = robust_policies["least_workload"]["mean"]

    quality_gates = {
        "average_reward_at_least_heuristic": (
            ppo_mean["average_reward"] >= heuristic_mean["average_reward"]
        ),
        "average_wait_no_worse_than_heuristic": (
            ppo_mean["average_wait_time"] <= heuristic_mean["average_wait_time"]
        ),
        "workload_imbalance_no_worse_than_heuristic": (
            ppo_mean["average_workload_standard_deviation"]
            <= heuristic_mean["average_workload_standard_deviation"]
        ),
        "skill_mismatch_no_worse_than_heuristic": (
            ppo_mean["skill_mismatch_rate"]
            <= heuristic_mean["skill_mismatch_rate"]
        ),
    }

    results["evaluation_gate"] = {
        "passed": all(quality_gates.values()),
        "checks": quality_gates,
        "note": (
            "Passing synthetic comparisons is necessary for an advisory pilot, "
            "not proof of real-world suitability."
        ),
    }

    results["evaluation_report_path"] = str(
        output_path.with_suffix(".evaluation.json")
    )

    report_path = output_path.with_suffix(".evaluation.json")
    temporary_report_path = report_path.with_suffix(
        report_path.suffix + ".tmp"
    )
    temporary_report_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )
    temporary_report_path.replace(report_path)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timesteps", type=int, default=50_000)
    parser.add_argument("--evaluation-steps", type=int, default=100)
    parser.add_argument("--evaluation-seeds", type=int, default=10)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--pretrain-epochs", type=int, default=100)
    args = parser.parse_args()

    result = train_and_evaluate(
        total_timesteps=args.timesteps,
        evaluation_steps=args.evaluation_steps,
        evaluation_seed_count=args.evaluation_seeds,
        seed=args.seed,
        model_path=args.model_path,
        dataset_path=args.dataset_path,
        pretrain_epochs=args.pretrain_epochs,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
