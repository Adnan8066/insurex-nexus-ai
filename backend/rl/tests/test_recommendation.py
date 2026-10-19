from copy import deepcopy

import pytest
from stable_baselines3 import PPO

from rl.environment import ClaimRoutingEnv
from rl.recommendation import (
    ClaimRecommendationEngine,
    RecommendationInputError,
)


@pytest.fixture
def engine():
    model = PPO(
        "MlpPolicy",
        ClaimRoutingEnv(),
        n_steps=16,
        batch_size=8,
        verbose=0,
        seed=12,
    )
    return ClaimRecommendationEngine(model, model_version="test-model")


@pytest.fixture
def routing_inputs():
    claim = {
        "complexity_score": 0.7,
        "severity_score": 0.6,
        "processing_difficulty": 0.5,
    }
    agents = [
        {"id": "adjuster-a", "queue_length": 2, "workload": 12, "skill_tier": 4},
        {"id": "adjuster-b", "queue_length": 4, "workload": 19, "skill_tier": 3},
        {"id": "adjuster-c", "queue_length": 0, "workload": 8, "skill_tier": 5},
    ]
    return claim, agents


def test_recommendations_are_ranked_and_advisory_only(engine, routing_inputs):
    claim, agents = routing_inputs
    claim_before, agents_before = deepcopy(claim), deepcopy(agents)

    result = engine.get_routing_recommendations(claim, agents)

    assert result["recommended_agent_id"] in {agent["id"] for agent in agents}
    assert result["automated_assignment"] is False
    assert result["requires_human_review"] is True
    assert result["advisory_only"] is True
    assert len(result["ranked_options"]) == 3
    assert len(result["ranked_alternatives"]) == 2
    assert sum(option["match_percentage"] for option in result["ranked_options"]) == pytest.approx(100.0)
    assert result["confidence"]["calibrated"] is False
    assert claim == claim_before
    assert agents == agents_before


def test_unavailable_agents_are_excluded(engine, routing_inputs):
    claim, agents = routing_inputs
    agents[0]["available"] = False

    result = engine.get_routing_recommendations(claim, agents)

    assert len(result["ranked_options"]) == 2
    assert all(option["agent_id"] != "adjuster-a" for option in result["ranked_options"])


def test_no_available_agent_returns_no_recommendation(engine, routing_inputs):
    claim, agents = routing_inputs
    for agent in agents:
        agent["available"] = False

    result = engine.get_routing_recommendations(claim, agents)

    assert result["status"] == "no_available_agents"
    assert result["recommended_agent_id"] is None
    assert result["ranked_options"] == []


def test_invalid_claim_data_is_rejected(engine, routing_inputs):
    _, agents = routing_inputs

    with pytest.raises(RecommendationInputError):
        engine.get_routing_recommendations(
            {"complexity_score": 4, "severity_score": 0.5, "processing_difficulty": 0.5},
            agents,
        )
