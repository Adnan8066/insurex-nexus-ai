"""Synthetic, advisory-only claim routing environment.

This environment is a training simulator. It has no database, HTTP, or claim
workflow integration and must not be used to mutate real assignments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces


MAX_AGENTS = 10
MIN_AGENTS = 1
MAX_QUEUE_LENGTH = 20.0
MAX_WORKLOAD = 100.0
MAX_SKILL_TIER = 5
QUEUE_WAIT_UNIT = 1.5
SERVICE_CAPACITY_PER_STEP = 4.0
BASE_CLAIM_WORKLOAD = 1.0
COMPLEXITY_WORKLOAD = 4.0
DIFFICULTY_WORKLOAD = 5.0
# Chance that a simulated employee is off work for an episode when the fleet is randomized.
UNAVAILABLE_PROBABILITY = 0.15


def required_experience_years(complexity: float, processing_difficulty: float) -> int:
    """Synthetic experience reference shared with the live routing feature."""
    return min(10, int(np.ceil(max(complexity, processing_difficulty) * 10)))


@dataclass(frozen=True)
class RewardWeights:
    """Reward coefficients used by the synthetic scheduling objective."""

    # Keep the training objective aligned with the evaluation's wait metric.
    wait: float = 10.0
    imbalance: float = 2.0
    skill_mismatch: float = 8.0
    assignment: float = 1.0
    # Choosing a padded or unavailable slot assigns nothing.
    invalid_action: float = 10.0


def estimate_claim_workload(complexity: float, processing_difficulty: float) -> float:
    """Map normalized claim attributes to synthetic work units."""
    return BASE_CLAIM_WORKLOAD + COMPLEXITY_WORKLOAD * complexity + DIFFICULTY_WORKLOAD * processing_difficulty


def estimate_wait_time(queue_length: float, workload: float) -> float:
    """Estimate wait in simulator time units from the current queue and workload."""
    return max(0.0, queue_length) * QUEUE_WAIT_UNIT + max(0.0, workload) / SERVICE_CAPACITY_PER_STEP


class ClaimRoutingEnv(gym.Env[np.ndarray, int]):
    """A Gymnasium environment for comparing simulated agent assignments.

    Observation layout:
        [complexity, severity, processing_difficulty,
         (queue_length, workload, skill_match, available) * MAX_AGENTS]

    Claim attributes and agent status are synthetic. One step represents one
    scheduling interval: existing agents make natural progress, then the
    selected agent receives the incoming claim.

    The action space always has MAX_AGENTS slots. With ``randomize_fleet`` each
    episode draws 1..n_agents employees and marks some unavailable, so the
    policy learns to handle padding and absences like live rosters.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        n_agents: int = MAX_AGENTS,
        max_episode_steps: int = 100,
        reward_weights: RewardWeights | None = None,
        randomize_fleet: bool = False,
    ) -> None:
        super().__init__()
        if not MIN_AGENTS <= n_agents <= MAX_AGENTS:
            raise ValueError(f"n_agents must be between {MIN_AGENTS} and {MAX_AGENTS}.")
        if max_episode_steps < 1:
            raise ValueError("max_episode_steps must be positive.")

        self.max_fleet_size = n_agents
        self.randomize_fleet = randomize_fleet
        self.n_agents = n_agents
        self.max_episode_steps = max_episode_steps
        self.reward_weights = reward_weights or RewardWeights()
        self.action_space = spaces.Discrete(MAX_AGENTS)
        # Padding keeps the observation shape fixed so one model can score
        # live requests with any number of employees up to MAX_AGENTS.
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(3 + MAX_AGENTS * 4,),
            dtype=np.float32,
        )

        self.queue_lengths = np.zeros(MAX_AGENTS, dtype=np.float32)
        self.workloads = np.zeros(MAX_AGENTS, dtype=np.float32)
        self.skill_tiers = np.ones(MAX_AGENTS, dtype=np.int8)
        self.agent_experience = np.zeros(MAX_AGENTS, dtype=np.int8)
        self.available = np.zeros(MAX_AGENTS, dtype=np.float32)
        self.available[:n_agents] = 1.0
        self.claim_complexity = 0.5
        self.claim_severity = 0.5
        self.processing_difficulty = 0.5
        self.required_skill_tier = 3
        self.steps = 0

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        self.steps = 0
        if self.randomize_fleet:
            self.n_agents = int(self.np_random.integers(MIN_AGENTS, self.max_fleet_size + 1))
        else:
            self.n_agents = self.max_fleet_size
        n = self.n_agents
        self.queue_lengths = np.zeros(MAX_AGENTS, dtype=np.float32)
        self.workloads = np.zeros(MAX_AGENTS, dtype=np.float32)
        self.skill_tiers = np.ones(MAX_AGENTS, dtype=np.int8)
        self.agent_experience = np.zeros(MAX_AGENTS, dtype=np.int8)
        self.available = np.zeros(MAX_AGENTS, dtype=np.float32)
        self.queue_lengths[:n] = self.np_random.integers(0, 7, size=n)
        self.workloads[:n] = self.np_random.uniform(0, 24, size=n)
        self.skill_tiers[:n] = self.np_random.integers(1, MAX_SKILL_TIER + 1, size=n)
        self.agent_experience[:n] = self.np_random.integers(0, 16, size=n)
        self.available[:n] = 1.0
        if self.randomize_fleet:
            self.available[:n] = self.np_random.random(n) >= UNAVAILABLE_PROBABILITY
            if not self.available[:n].any():
                self.available[int(self.np_random.integers(n))] = 1.0
        self._sample_claim()
        return self._get_observation(), self._get_info()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if not self.action_space.contains(action):
            raise ValueError(f"Action must be an agent index from 0 to {MAX_AGENTS - 1}.")
        selected = int(action)
        if not self.available[selected]:
            # Nobody receives the claim; it is offered again next interval.
            self.steps += 1
            info = self._get_info()
            info.update({
                "invalid_action": True,
                "assigned_agent_index": None,
                "predicted_wait_time": 0.0,
                "workload_standard_deviation": round(float(np.std(self.workloads[: self.n_agents])), 4),
                "claim_workload": 0.0,
                "skill_mismatch": False,
                "wait_penalty": 0.0,
                "imbalance_penalty": 0.0,
                "mismatch_penalty": 0.0,
            })
            return (
                self._get_observation(), -float(self.reward_weights.invalid_action),
                self.steps >= self.max_episode_steps, False, info,
            )

        wait_time = estimate_wait_time(
            float(self.queue_lengths[selected]), float(self.workloads[selected])
        )
        mismatch = bool(
            self.required_skill_tier > int(self.skill_tiers[selected])
            or self.agent_experience[selected] < required_experience_years(
                self.claim_complexity, self.processing_difficulty
            )
        )
        claim_workload = estimate_claim_workload(
            self.claim_complexity, self.processing_difficulty
        )

        # Natural service progress occurs for the whole fleet before the new
        # task is added. One queued task per agent is completed per interval.
        self.workloads = np.maximum(0.0, self.workloads - SERVICE_CAPACITY_PER_STEP)
        self.queue_lengths = np.maximum(0.0, self.queue_lengths - 1.0)
        self.workloads[selected] = min(
            MAX_WORKLOAD, self.workloads[selected] + claim_workload
        )
        self.queue_lengths[selected] = min(
            MAX_QUEUE_LENGTH, self.queue_lengths[selected] + 1.0
        )

        workload_std = float(np.std(self.workloads[: self.n_agents]))
        normalized_wait = wait_time / (QUEUE_WAIT_UNIT * MAX_QUEUE_LENGTH + MAX_WORKLOAD / SERVICE_CAPACITY_PER_STEP)
        normalized_imbalance = workload_std / MAX_WORKLOAD
        weights = self.reward_weights
        reward = (
            weights.assignment
            - weights.wait * normalized_wait
            - weights.imbalance * normalized_imbalance
            - (weights.skill_mismatch if mismatch else 0.0)
        )

        self.steps += 1
        terminated = self.steps >= self.max_episode_steps
        truncated = False
        self._sample_claim()
        info = self._get_info()
        info.update(
            {
                "invalid_action": False,
                "assigned_agent_index": selected,
                "predicted_wait_time": round(wait_time, 4),
                "workload_standard_deviation": round(workload_std, 4),
                "claim_workload": round(claim_workload, 4),
                "skill_mismatch": mismatch,
                "wait_penalty": round(weights.wait * normalized_wait, 6),
                "imbalance_penalty": round(weights.imbalance * normalized_imbalance, 6),
                "mismatch_penalty": weights.skill_mismatch if mismatch else 0.0,
            }
        )
        return self._get_observation(), float(reward), terminated, truncated, info

    def _sample_claim(self) -> None:
        self.claim_complexity = float(self.np_random.uniform(0.0, 1.0))
        self.required_skill_tier = int(self.np_random.integers(1, MAX_SKILL_TIER + 1))
        self.claim_severity = (self.required_skill_tier - 1) / (MAX_SKILL_TIER - 1)
        self.processing_difficulty = float(self.np_random.uniform(0.0, 1.0))

    def _get_observation(self) -> np.ndarray:
        observation = np.zeros(3 + MAX_AGENTS * 4, dtype=np.float32)
        observation[:3] = [
            self.claim_complexity,
            self.claim_severity,
            self.processing_difficulty,
        ]
        for index in range(self.n_agents):
            offset = 3 + index * 4
            observation[offset : offset + 4] = [
                min(float(self.queue_lengths[index]) / MAX_QUEUE_LENGTH, 1.0),
                min(float(self.workloads[index]) / MAX_WORKLOAD, 1.0),
                float(
                    self.skill_tiers[index] >= self.required_skill_tier
                    and self.agent_experience[index] >= required_experience_years(
                        self.claim_complexity, self.processing_difficulty
                    )
                ),
                float(self.available[index]),
            ]
        # Padded agents stay all-zero (availability 0) so callers can exclude them.
        return observation

    def _get_info(self) -> dict[str, Any]:
        n = self.n_agents
        return {
            "step": self.steps,
            "required_skill_tier": self.required_skill_tier,
            "agent_skill_tiers": self.skill_tiers[:n].astype(int).tolist(),
            "agent_experience_years": self.agent_experience[:n].astype(int).tolist(),
            "required_experience_years": required_experience_years(self.claim_complexity, self.processing_difficulty),
            "agent_queue_lengths": self.queue_lengths[:n].astype(float).tolist(),
            "agent_workloads": self.workloads[:n].astype(float).tolist(),
            "agent_available": self.available[:n].astype(bool).tolist(),
        }
