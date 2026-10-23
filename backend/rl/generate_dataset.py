"""Generate a synthetic transition dataset from ClaimRoutingEnv.

Run from the backend directory: python -m rl.generate_dataset
The output is simulator data for experimentation, not observed claim outcomes.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from .environment import (
    MAX_AGENTS,
    ClaimRoutingEnv,
    estimate_wait_time,
)


DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "synthetic_claim_routing_transitions.csv"


def _choose_action(env: ClaimRoutingEnv, rng: np.random.Generator, policy: str) -> int:
    eligible = [
        i for i in range(env.n_agents)
        if env.available[i] and env.skill_tiers[i] >= env.required_skill_tier
    ]
    candidates = eligible or [i for i in range(env.n_agents) if env.available[i]]
    if policy == "random" or (policy == "mixed" and rng.random() < 0.25):
        return int(rng.choice(candidates or list(range(env.n_agents))))
    if policy == "least_workload" or policy == "mixed":
        return min(
            candidates or list(range(env.n_agents)),
            key=lambda i: estimate_wait_time(
                float(env.queue_lengths[i]), float(env.workloads[i])
            ),
        )
    raise ValueError(f"Unknown behavior policy: {policy}")


def generate_dataset(
    *, episodes: int = 200, steps_per_episode: int = 100, seed: int = 2026,
    output: str | Path = DEFAULT_OUTPUT, policy: str = "least_workload",
) -> Path:
    if episodes < 1 or steps_per_episode < 1:
        raise ValueError("episodes and steps_per_episode must be positive")
    rng = np.random.default_rng(seed)
    env = ClaimRoutingEnv(n_agents=MAX_AGENTS, max_episode_steps=steps_per_episode)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "episode_id", "step", "behavior_policy", "action_agent_index",
        *[f"obs_{i}" for i in range(env.observation_space.shape[0])],
        "reward", "next_episode_id",
        *[f"next_obs_{i}" for i in range(env.observation_space.shape[0])],
        "terminated", "truncated", "predicted_wait_time",
        "workload_standard_deviation", "claim_workload", "skill_mismatch",
        "wait_penalty", "imbalance_penalty", "mismatch_penalty",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for episode in range(episodes):
            obs, _ = env.reset(seed=seed + episode)
            for step in range(steps_per_episode):
                action = _choose_action(env, rng, policy)
                next_obs, reward, terminated, truncated, info = env.step(action)
                row = {
                    "episode_id": episode,
                    "step": step,
                    "behavior_policy": policy,
                    "action_agent_index": action,
                    "reward": reward,
                    "next_episode_id": episode,
                    "terminated": terminated,
                    "truncated": truncated,
                    **{f"obs_{i}": float(value) for i, value in enumerate(obs)},
                    **{f"next_obs_{i}": float(value) for i, value in enumerate(next_obs)},
                    **{key: info[key] for key in (
                        "predicted_wait_time", "workload_standard_deviation",
                        "claim_workload", "skill_mismatch", "wait_penalty",
                        "imbalance_penalty", "mismatch_penalty",
                    )},
                }
                writer.writerow(row)
                obs = next_obs
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--policy", choices=("mixed", "random", "least_workload"), default="least_workload")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path = generate_dataset(
        episodes=args.episodes, steps_per_episode=args.steps, seed=args.seed,
        output=args.output, policy=args.policy,
    )
    print(f"Wrote {args.episodes * args.steps} transitions to {path}")


if __name__ == "__main__":
    main()
