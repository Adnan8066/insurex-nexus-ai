"""Reproducible synthetic-policy evaluation helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from .environment import (
    MAX_AGENTS,
    ClaimRoutingEnv,
    estimate_wait_time,
)


Policy = Callable[[ClaimRoutingEnv, np.ndarray], int]


def _random_action(env: ClaimRoutingEnv, _observation: np.ndarray) -> int:
    return int(env.action_space.sample())


def _least_workload_action(env: ClaimRoutingEnv, _observation: np.ndarray) -> int:
    """Choose the eligible available agent with the smallest estimated wait."""
    eligible = [
        i
        for i in range(env.n_agents)
        if env.available[i] and env.skill_tiers[i] >= env.required_skill_tier
    ]
    candidates = eligible or [i for i in range(env.n_agents) if env.available[i]]
    if not candidates:
        return 0
    return min(
        candidates,
        key=lambda i: estimate_wait_time(
            float(env.queue_lengths[i]), float(env.workloads[i])
        ),
    )


def evaluate_policy(
    policy: Policy,
    *,
    steps: int = 100,
    n_agents: int = MAX_AGENTS,
    seed: int = 123,
) -> dict[str, Any]:
    """Evaluate one policy for a fixed number of synthetic arrivals."""
    if steps < 1:
        raise ValueError("steps must be positive.")
    env = ClaimRoutingEnv(n_agents=n_agents, max_episode_steps=steps)
    observation, _ = env.reset(seed=seed)
    env.action_space.seed(seed + 1)
    rewards: list[float] = []
    wait_times: list[float] = []
    workload_stds: list[float] = []
    mismatches = 0

    for _ in range(steps):
        action = policy(env, observation)
        observation, reward, terminated, truncated, info = env.step(action)
        rewards.append(float(reward))
        wait_times.append(float(info["predicted_wait_time"]))
        workload_stds.append(float(info["workload_standard_deviation"]))
        mismatches += int(info["skill_mismatch"])
        if terminated or truncated:
            break

    count = max(1, len(rewards))
    return {
        "steps": len(rewards),
        "average_reward": round(float(np.mean(rewards)), 4),
        "average_wait_time": round(float(np.mean(wait_times)), 4),
        "average_workload_standard_deviation": round(float(np.mean(workload_stds)), 4),
        "skill_mismatch_rate": round(mismatches / count, 4),
    }


def evaluate_baselines(
    *, steps: int = 100, n_agents: int = MAX_AGENTS, seed: int = 123
) -> dict[str, dict[str, Any]]:
    """Compare random assignment with a least-estimated-workload heuristic."""
    return {
        "random": evaluate_policy(
            _random_action, steps=steps, n_agents=n_agents, seed=seed
        ),
        "least_workload": evaluate_policy(
            _least_workload_action, steps=steps, n_agents=n_agents, seed=seed
        ),
    }


def evaluate_model(
    model: Any,
    *,
    steps: int = 100,
    n_agents: int = MAX_AGENTS,
    seed: int = 123,
) -> dict[str, Any]:
    """Evaluate an SB3-compatible model deterministically."""

    def model_action(_env: ClaimRoutingEnv, observation: np.ndarray) -> int:
        action, _state = model.predict(observation, deterministic=True)
        return int(np.asarray(action).item())

    return evaluate_policy(model_action, steps=steps, n_agents=n_agents, seed=seed)


def evaluate_across_seeds(
    *,
    steps: int = 100,
    seeds: tuple[int, ...] = tuple(range(1000, 1010)),
    model: Any | None = None,
    n_agents: int = MAX_AGENTS,
) -> dict[str, Any]:
    """Compare baselines and optional PPO over repeatable independent scenarios.

    Report per-seed values plus mean and population standard deviation so a
    single favorable synthetic episode cannot stand in for policy validation.
    """
    if not seeds:
        raise ValueError("Provide at least one evaluation seed.")
    policies: dict[str, Policy] = {
        "random": _random_action,
        "least_workload": _least_workload_action,
    }
    if model is not None:
        def model_action(_env: ClaimRoutingEnv, observation: np.ndarray) -> int:
            action, _state = model.predict(observation, deterministic=True)
            return int(np.asarray(action).item())

        policies["ppo"] = model_action

    metric_names = (
        "average_reward",
        "average_wait_time",
        "average_workload_standard_deviation",
        "skill_mismatch_rate",
    )
    results: dict[str, Any] = {}
    for name, policy in policies.items():
        per_seed = [
            evaluate_policy(policy, steps=steps, n_agents=n_agents, seed=seed)
            for seed in seeds
        ]
        results[name] = {
            "mean": {
                metric: round(float(np.mean([row[metric] for row in per_seed])), 4)
                for metric in metric_names
            },
            "std": {
                metric: round(float(np.std([row[metric] for row in per_seed])), 4)
                for metric in metric_names
            },
            "per_seed": [
                {"seed": seed, **row} for seed, row in zip(seeds, per_seed)
            ],
        }
    return {
        "evaluation_seed_count": len(seeds),
        "steps_per_seed": steps,
        "seeds": list(seeds),
        "synthetic_only": True,
        "policies": results,
    }
