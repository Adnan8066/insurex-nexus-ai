"""Read-only routing recommendations from a trained PPO policy."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.parsers.expat import model

import numpy as np
from stable_baselines3 import PPO

from .environment import (
    MAX_AGENTS,
    MAX_QUEUE_LENGTH,
    MAX_SKILL_TIER,
    MAX_WORKLOAD,
    QUEUE_WAIT_UNIT,
    SERVICE_CAPACITY_PER_STEP,
    estimate_claim_workload,
    estimate_wait_time,
)


class RecommendationInputError(ValueError):
    """Raised when claim or agent data cannot be safely scored."""


class ModelArtifactError(RuntimeError):
    """Raised when the trained routing model is missing or cannot load."""


class ClaimRecommendationEngine:
    """Produce ranked, advisory-only options without writing application state.

    Required claim fields are normalized floats in ``[0, 1]``:
    ``complexity_score``, ``severity_score``, and ``processing_difficulty``.
    Agent records require ``id``, ``queue_length``, ``workload``, and
    ``skill_tier`` (1 through 5); ``available`` defaults to ``True``.
    """

    OBSERVATION_SIZE = 3 + MAX_AGENTS * 4

    def __init__(
        self,
        model: Any,
        model_version: str = "unversioned",
        strategy: str = "reward_aware",
) -> None:
        if strategy not in {"reward_aware", "ppo"}:
            raise ValueError("strategy must be 'reward_aware' or 'ppo'.")

        self.model = model
        self.model_version = model_version
        self.strategy = strategy

    @classmethod
    def load(cls, model_path: str | Path | None = None) -> "ClaimRecommendationEngine":
        """Load a trained SB3 PPO archive from disk (CPU inference)."""
        path = Path(
            model_path
            or os.environ.get(
                "CLAIM_ROUTING_MODEL_PATH",
                Path(__file__).resolve().parent / "models" / "claim_routing_ppo.zip",
            )
        ).expanduser().resolve()
        if not path.is_file():
            raise ModelArtifactError(
                f"Routing model not found at {path}. Train it with `python -m rl.training` first."
            )
        try:
            model = PPO.load(str(path), device="cpu")
        except Exception as exc:
            raise ModelArtifactError(f"Could not load routing model: {exc}") from exc
        return cls(model=model, model_version=path.stem)

    def get_routing_recommendations(
        self,
        claim_data: Mapping[str, Any],
        active_agents_status: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Return ranked agent options for a human reviewer.

        The method only reads its arguments and model weights. It has no Django
        model imports, database connections, or assignment side effects.
        """
        claim = self._validate_claim(claim_data)
        agents = self._validate_agents(active_agents_status)
        available_agents = [agent for agent in agents if agent["available"]]
        if not available_agents:
            return {
                "advisory_only": True,
                "automated_assignment": False,
                "requires_human_review": True,
                "status": "no_available_agents",
                "recommended_agent_id": None,
                "predicted_wait_time": None,
                "workload_impact_summary": "No active agent is available; assign only after human review.",
                "ranked_alternatives": [],
                "ranked_options": [],
                "wait_time_basis": "synthetic workload approximation; not measured operational wait time",
                "model_version": self.model_version,
            }

        observation = self._encode_observation(claim, agents)
        action, _state = self.model.predict(observation, deterministic=True)
        deterministic_action = int(np.asarray(action).reshape(-1)[0])
        action_probabilities = self._action_probabilities(observation)

        # The model was trained with up to five actions. Ignore unavailable
        # agents and padding, then renormalize over the real available fleet.
        raw_scores = [
            action_probabilities[agent["index"]]
            if agent["index"] < len(action_probabilities)
            else 0.0
            for agent in available_agents
        ]
        total = float(sum(raw_scores))
        if total <= 0.0 or not math.isfinite(total):
            scores = [1.0 / len(available_agents)] * len(available_agents)
        else:
            scores = [score / total for score in raw_scores]

        ranked = sorted(
            zip(available_agents, scores),
            key=lambda item: (-item[1], item[0]["index"]),
        )
        best_agent, best_score = ranked[0]
        # Use deterministic PPO prediction when it maps to an available agent;
        # otherwise choose the highest-probability valid option.
        if deterministic_action in {agent["index"] for agent in available_agents}:
            recommended_agent = next(
                agent for agent, _score in ranked if agent["index"] == deterministic_action
            )
            recommended_score = next(
                score for agent, score in ranked if agent["index"] == deterministic_action
            )
        else:
            recommended_agent, recommended_score = best_agent, best_score

        options = [
            self._format_option(agent, score, claim, rank=index + 1)
            for index, (agent, score) in enumerate(ranked)
        ]
        recommended_option = next(
            option
            for option in options
            if option["agent_id"] == recommended_agent["id"]
        )
        alternatives = [
            option for option in options
            if option["agent_id"] != recommended_agent["id"]
        ]
        summary = (
            f"Estimated workload for agent {recommended_agent['id']} changes from "
            f"{recommended_agent['workload']:.1f} to "
            f"{recommended_option['estimated_workload_after_assignment']:.1f} work units "
            "after natural service progress and this simulated assignment."
        )
        if not recommended_option["skill_match"]:
            summary += " Skill tier does not match claim severity; human authorization review is required."

        return {
            "advisory_only": True,
            "automated_assignment": False,
            "requires_human_review": True,
            "status": "recommendation_available",
            "recommended_agent_id": recommended_agent["id"],
            "predicted_wait_time": recommended_option["predicted_wait_time"],
            "workload_impact_summary": summary,
            "wait_time_basis": "synthetic workload approximation; not measured operational wait time",
            "confidence": {
                "percentage": round(recommended_score * 100, 2),
                "calibrated": False,
                "interpretation": "Relative PPO policy preference among currently available options; not a probability of success.",
            },
            "ranked_alternatives": alternatives,
            "ranked_options": options,
            "deterministic_model_action_index": deterministic_action,
            "model_version": self.model_version,
            "observation_version": "claim-routing-v1",
        }

    @staticmethod
    def _validate_claim(claim_data: Mapping[str, Any]) -> dict[str, float]:
        if not isinstance(claim_data, Mapping):
            raise RecommendationInputError("claim_data must be an object.")
        values: dict[str, float] = {}
        for field in ("complexity_score", "severity_score", "processing_difficulty"):
            try:
                value = float(claim_data[field])
            except (KeyError, TypeError, ValueError) as exc:
                raise RecommendationInputError(
                    f"claim_data.{field} must be a normalized number from 0 to 1."
                ) from exc
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise RecommendationInputError(
                    f"claim_data.{field} must be a normalized number from 0 to 1."
                )
            values[field] = value
        return values

    @staticmethod
    def _validate_agents(
        active_agents_status: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        if isinstance(active_agents_status, (str, bytes)) or not isinstance(
            active_agents_status, Sequence
        ):
            raise RecommendationInputError("active_agents_status must be a list.")
        if not 3 <= len(active_agents_status) <= MAX_AGENTS:
            raise RecommendationInputError("Provide between 3 and 5 agent records.")

        agents: list[dict[str, Any]] = []
        ids: set[str] = set()
        for index, raw in enumerate(active_agents_status):
            if not isinstance(raw, Mapping):
                raise RecommendationInputError(f"Agent at index {index} must be an object.")
            if "id" not in raw or raw["id"] is None:
                raise RecommendationInputError(f"Agent at index {index} requires an id.")
            identifier = str(raw["id"])
            if not identifier or identifier in ids:
                raise RecommendationInputError("Agent ids must be non-empty and unique.")
            ids.add(identifier)
            try:
                queue_length = float(raw["queue_length"])
                workload = float(raw["workload"])
                tier_raw = float(raw["skill_tier"])
            except (KeyError, TypeError, ValueError) as exc:
                raise RecommendationInputError(
                    f"Agent {identifier} requires queue_length, workload, and skill_tier."
                ) from exc
            if not math.isfinite(queue_length) or queue_length < 0:
                raise RecommendationInputError(f"Agent {identifier} queue_length must be non-negative.")
            if not math.isfinite(workload) or workload < 0:
                raise RecommendationInputError(f"Agent {identifier} workload must be non-negative.")
            if not tier_raw.is_integer() or not 1 <= tier_raw <= MAX_SKILL_TIER:
                raise RecommendationInputError(
                    f"Agent {identifier} skill_tier must be an integer from 1 to {MAX_SKILL_TIER}."
                )
            available = raw.get("available", True)
            if not isinstance(available, bool):
                raise RecommendationInputError(f"Agent {identifier} available must be a boolean.")
            agents.append(
                {
                    "index": index,
                    "id": raw["id"],
                    "queue_length": queue_length,
                    "workload": workload,
                    "skill_tier": int(tier_raw),
                    "available": available,
                }
            )
        return agents

    @staticmethod
    def _encode_observation(
        claim: Mapping[str, float], agents: Sequence[Mapping[str, Any]]
    ) -> np.ndarray:
        observation = np.zeros(ClaimRecommendationEngine.OBSERVATION_SIZE, dtype=np.float32)
        observation[:3] = [
            claim["complexity_score"],
            claim["severity_score"],
            claim["processing_difficulty"],
        ]
        required_tier = min(
            MAX_SKILL_TIER,
            max(1, int(math.ceil(claim["severity_score"] * MAX_SKILL_TIER))),
        )
        for agent in agents:
            offset = 3 + int(agent["index"]) * 4
            observation[offset : offset + 4] = [
                min(float(agent["queue_length"]) / MAX_QUEUE_LENGTH, 1.0),
                min(float(agent["workload"]) / MAX_WORKLOAD, 1.0),
                float(int(agent["skill_tier"]) >= required_tier),
                float(agent["available"]),
            ]
        for index in range(len(agents), MAX_AGENTS):
            offset = 3 + index * 4
            observation[offset : offset + 4] = [0.0, 0.0, 0.0, 0.0]
        return observation

    def _action_probabilities(self, observation: np.ndarray) -> np.ndarray:
        """Read the PPO categorical policy distribution for ranking only."""
        try:
            observation_tensor, _vectorized = self.model.policy.obs_to_tensor(observation)
            distribution = self.model.policy.get_distribution(observation_tensor)
            probabilities = distribution.distribution.probs.detach().cpu().numpy().reshape(-1)
        except Exception as exc:
            raise ModelArtifactError(f"Could not read PPO action preferences: {exc}") from exc
        if probabilities.size != MAX_AGENTS:
            raise ModelArtifactError(
                f"Expected {MAX_AGENTS} PPO action scores, received {probabilities.size}."
            )
        return probabilities.astype(float)

    @staticmethod
    def _format_option(
        agent: Mapping[str, Any],
        preference: float,
        claim: Mapping[str, float],
        *,
        rank: int,
    ) -> dict[str, Any]:
        required_tier = min(
            MAX_SKILL_TIER,
            max(1, int(math.ceil(claim["severity_score"] * MAX_SKILL_TIER))),
        )
        skill_match = int(agent["skill_tier"]) >= required_tier
        decayed_workload = max(
            0.0, float(agent["workload"]) - SERVICE_CAPACITY_PER_STEP
        )
        incoming_workload = estimate_claim_workload(
            claim["complexity_score"], claim["processing_difficulty"]
        )
        post_assignment_workload = min(
            MAX_WORKLOAD, decayed_workload + incoming_workload
        )
        estimated_wait = estimate_wait_time(
            float(agent["queue_length"]), float(agent["workload"])
        )
        return {
            "rank": rank,
            "agent_id": agent["id"],
            "match_percentage": round(preference * 100, 2),
            "predicted_wait_time": round(estimated_wait, 2),
            "skill_tier": int(agent["skill_tier"]),
            "required_skill_tier": required_tier,
            "skill_match": skill_match,
            "estimated_workload_before": round(float(agent["workload"]), 2),
            "estimated_workload_after_assignment": round(post_assignment_workload, 2),
        }
