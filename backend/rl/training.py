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
from .policy import AgentScoringPolicy


DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "claim_routing_ppo.zip"
DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "data" / "synthetic_claim_routing_expert_transitions.csv"


def pretrain_policy_from_transitions(
    model: PPO,
    dataset_path: str | Path,
    *,
    epochs: int = 5,
    batch_size: int = 256,
) -> dict[str, Any]:
    """Warm-start PPO by imitating logged expert actions and fitting the critic.

    The actor learns the expert's choices (cross-entropy). The critic learns
    discounted returns of the logged episodes, so PPO's first advantage
    estimates are not driven by a random value network. Agent slots are
    shuffled per batch: the expert's choice does not depend on slot order, so
    this multiplies the effective data and removes slot-position bias.
    """
    if epochs < 1 or batch_size < 1:
        raise ValueError("pretraining epochs and batch size must be positive")

    observations: list[list[float]] = []
    actions: list[int] = []
    rewards: list[float] = []
    episode_ids: list[str] = []

    with Path(dataset_path).expanduser().open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "episode_id",
            "action_agent_index",
            "behavior_policy",
            "reward",
            *[f"obs_{i}" for i in range(3 + MAX_AGENTS * 4)],
        }

        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                "Dataset must contain episode_id, behavior_policy, action_agent_index, "
                f"reward, and obs_0 through obs_{2 + MAX_AGENTS * 4}. "
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
                reward = float(row["reward"])
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(
                    "Dataset contains a malformed observation or action."
                ) from exc

            if not np.isfinite([*obs, reward]).all() or not 0 <= action < MAX_AGENTS:
                raise ValueError(
                    "Dataset contains a non-finite observation or out-of-range action."
                )

            observations.append(obs)
            actions.append(action)
            rewards.append(reward)
            episode_ids.append(row["episode_id"])

    if not actions:
        raise ValueError("Dataset has no transitions.")

    # Discounted return of each logged step within its episode (rows are in order).
    returns = np.zeros(len(rewards), dtype=np.float32)
    running = 0.0
    for index in range(len(rewards) - 1, -1, -1):
        if index == len(rewards) - 1 or episode_ids[index + 1] != episode_ids[index]:
            running = 0.0
        running = rewards[index] + model.gamma * running
        returns[index] = running

    device = model.device
    obs_tensor = torch.as_tensor(
        np.asarray(observations), dtype=torch.float32, device=device
    )
    action_tensor = torch.as_tensor(
        actions, dtype=torch.long, device=device
    )
    return_tensor = torch.as_tensor(returns, device=device)

    optimizer = torch.optim.Adam(model.policy.parameters(), lr=3e-4)
    # Clip actor and critic separately: large early value errors must not
    # shrink the imitation gradients through one shared norm.
    actor_parameters = list(model.policy.mlp_extractor.actor.parameters())
    actor_ids = {id(parameter) for parameter in actor_parameters}
    critic_parameters = [
        parameter for parameter in model.policy.parameters() if id(parameter) not in actor_ids
    ]
    model.policy.set_training_mode(True)
    actor_losses: list[float] = []
    critic_losses: list[float] = []

    for epoch in range(epochs):
        order = torch.randperm(len(actions), device=device)

        for indices in order.split(batch_size):
            batch_obs, batch_actions = _shuffle_agent_slots(
                obs_tensor[indices], action_tensor[indices]
            )
            distribution = model.policy.get_distribution(batch_obs).distribution
            actor_loss = torch.nn.functional.cross_entropy(
                distribution.logits, batch_actions
            )
            critic_loss = torch.nn.functional.mse_loss(
                model.policy.predict_values(batch_obs).flatten(),
                return_tensor[indices],
            )
            loss = actor_loss + 0.5 * critic_loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(actor_parameters, 0.5)
            torch.nn.utils.clip_grad_norm_(critic_parameters, 0.5)
            optimizer.step()
            if epoch == epochs - 1:
                actor_losses.append(float(actor_loss.detach().cpu()))
                critic_losses.append(float(critic_loss.detach().cpu()))

    model.policy.set_training_mode(False)

    with torch.no_grad():
        predicted = model.policy.get_distribution(obs_tensor).distribution.logits.argmax(dim=1)
    return {
        "method": "behavior_cloning_actor_and_critic_warm_start",
        "dataset_path": str(Path(dataset_path).expanduser().resolve()),
        "transitions": len(actions),
        "epochs": epochs,
        "final_epoch_actor_loss": round(float(np.mean(actor_losses)), 6),
        "final_epoch_critic_loss": round(float(np.mean(critic_losses)), 6),
        "expert_action_agreement": round(float((predicted == action_tensor).float().mean()), 4),
        "agent_slot_shuffling": True,
        "uses_logged_rewards_for_critic_warm_start": True,
    }


def _shuffle_agent_slots(
    observations: torch.Tensor, actions: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    """Randomly reorder each row's agent blocks and remap its expert action."""
    rows = observations.shape[0]
    agents = observations[:, 3:].reshape(rows, MAX_AGENTS, 4)
    # Slot j of the new row holds old agent permutation[j].
    permutation = torch.argsort(torch.rand(rows, MAX_AGENTS, device=observations.device), dim=1)
    shuffled = torch.gather(agents, 1, permutation.unsqueeze(-1).expand(-1, -1, 4))
    new_actions = torch.argsort(permutation, dim=1).gather(1, actions.unsqueeze(1)).squeeze(1)
    return torch.cat([observations[:, :3], shuffled.reshape(rows, -1)], dim=1), new_actions


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
        randomize_fleet=True,
    )

    model = PPO(
        AgentScoringPolicy,
        env,
        seed=seed,
        verbose=0,
        # Gentle fine-tuning so PPO refines, rather than overwrites, the
        # behavior-cloned policy.
        learning_rate=1e-5,
        n_steps=2048,
        batch_size=256,
        clip_range=0.1,
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
