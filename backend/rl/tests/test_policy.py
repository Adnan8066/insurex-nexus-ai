import torch
from stable_baselines3 import PPO

from rl.environment import MAX_AGENTS, ClaimRoutingEnv
from rl.evaluation import masked_model_action
from rl.policy import AgentScoringPolicy


def make_model():
    return PPO(AgentScoringPolicy, ClaimRoutingEnv(randomize_fleet=True), n_steps=16, batch_size=8, seed=4, device="cpu")


def test_agent_scores_follow_the_agent_not_the_slot():
    model = make_model()
    env = ClaimRoutingEnv()
    observation, _ = env.reset(seed=9)
    obs = torch.as_tensor(observation).unsqueeze(0)
    permutation = torch.randperm(MAX_AGENTS)
    agents = obs[:, 3:].reshape(1, MAX_AGENTS, 4)[:, permutation]
    shuffled = torch.cat([obs[:, :3], agents.reshape(1, -1)], dim=1)

    with torch.no_grad():
        logits = model.policy.get_distribution(obs).distribution.logits
        shuffled_logits = model.policy.get_distribution(shuffled).distribution.logits

    assert torch.allclose(logits[0, permutation], shuffled_logits[0], atol=1e-5)


def test_padded_and_unavailable_slots_are_never_chosen():
    model = make_model()
    env = ClaimRoutingEnv(randomize_fleet=True)
    for seed in range(30):
        observation, _ = env.reset(seed=seed)
        assert env.available[masked_model_action(model, observation)]
        action, _ = model.predict(observation, deterministic=True)
        assert env.available[int(action)]
