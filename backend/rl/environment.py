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


MAX_AGENTS = 5
MIN_AGENTS = 3
MAX_QUEUE_LENGTH = 20.0
MAX_WORKLOAD = 100.0
MAX_SKILL_TIER = 5
QUEUE_WAIT_UNIT = 1.5
SERVICE_CAPACITY_PER_STEP = 4.0
BASE_CLAIM_WORKLOAD = 1.0
COMPLEXITY_WORKLOAD = 4.0
DIFFICULTY_WORKLOAD = 5.0


@dataclass(frozen=True)
class RewardWeights:
    """Reward coefficients used by the synthetic scheduling objective."""

    # Keep the training objective aligned with the evaluation's wait metric.
    wait: float = 10.0
    imbalance: float = 2.0
    skill_mismatch: float = 8.0
    assignment: float = 1.0


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
         (queue_length, workload, skill_match, available) * 5 agents]

    Claim attributes and agent status are synthetic. One step represents one
    scheduling interval: existing agents make natural progress, then the
    selected agent receives the incoming claim.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        n_agents: int = MAX_AGENTS,
        max_episode_steps: int = 100,
        reward_weights: RewardWeights | None = None,
    ) -> None:
        super().__init__()
        if not MIN_AGENTS <= n_agents <= MAX_AGENTS:
            raise ValueError(f"n_agents must be between {MIN_AGENTS} and {MAX_AGENTS}.")
        if max_episode_steps < 1:
            raise ValueError("max_episode_steps must be positive.")

        self.n_agents = n_agents
        self.max_episode_steps = max_episode_steps
        self.reward_weights = reward_weights or RewardWeights()
        self.action_space = spaces.Discrete(n_agents)
        # Padding keeps the observation shape fixed so models trained with five
        # agents can score live requests that contain three or four agents.
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(3 + MAX_AGENTS * 4,),
            dtype=np.float32,
        )

        self.queue_lengths = np.zeros(n_agents, dtype=np.float32)
        self.workloads = np.zeros(n_agents, dtype=np.float32)
        self.skill_tiers = np.ones(n_agents, dtype=np.int8)
        self.available = np.ones(n_agents, dtype=np.float32)
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
        self.queue_lengths = self.np_random.integers(0, 7, size=self.n_agents).astype(np.float32)
        self.workloads = self.np_random.uniform(0, 24, size=self.n_agents).astype(np.float32)
        self.skill_tiers = self.np_random.integers(1, MAX_SKILL_TIER + 1, size=self.n_agents, dtype=np.int8)
        self.available = np.ones(self.n_agents, dtype=np.float32)
        self._sample_claim()
        return self._get_observation(), self._get_info()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if not self.action_space.contains(action):
            raise ValueError(f"Action must be an agent index from 0 to {self.n_agents - 1}.")
        selected = int(action)
        if not self.available[selected]:
            raise ValueError("The selected agent is unavailable.")

        wait_time = estimate_wait_time(
            float(self.queue_lengths[selected]), float(self.workloads[selected])
        )
        mismatch = self.required_skill_tier > int(self.skill_tiers[selected])
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

        workload_std = float(np.std(self.workloads))
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
                float(self.skill_tiers[index] >= self.required_skill_tier),
                float(self.available[index]),
            ]
        # Padded agents have availability 0 so recommendation callers can
        # exclude them from the candidate list.
        for index in range(self.n_agents, MAX_AGENTS):
            observation[3 + index * 4 + 3] = 0.0
        return observation

    def _get_info(self) -> dict[str, Any]:
        return {
            "step": self.steps,
            "required_skill_tier": self.required_skill_tier,
            "agent_skill_tiers": self.skill_tiers.astype(int).tolist(),
            "agent_queue_lengths": self.queue_lengths.astype(float).tolist(),
            "agent_workloads": self.workloads.astype(float).tolist(),
        }
