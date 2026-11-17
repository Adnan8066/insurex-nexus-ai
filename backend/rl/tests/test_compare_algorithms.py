import json

import numpy as np
import pytest
from stable_baselines3 import DQN

from rl.compare_algorithms import AgentQPolicy, LinUCB, compare, q_value_action
from rl.environment import MAX_AGENTS, ClaimRoutingEnv


def test_action_masks_match_available_employees():
    env = ClaimRoutingEnv(randomize_fleet=True)
    for seed in range(20):
        env.reset(seed=seed)
        mask = env.action_masks()
        assert mask.shape == (MAX_AGENTS,)
        assert mask.dtype == bool
        assert mask.any()
        assert not mask[env.n_agents:].any()  # padding is never a valid action
        assert np.array_equal(mask[: env.n_agents], env.available[: env.n_agents].astype(bool))


def test_dqn_scores_employees_independently_of_slot_order_and_skips_absent():
    model = DQN(AgentQPolicy, ClaimRoutingEnv(randomize_fleet=True), learning_starts=10, seed=3, device="cpu")
    env = ClaimRoutingEnv(randomize_fleet=True)
    for seed in range(20):
        observation, _ = env.reset(seed=seed)
        assert env.available[q_value_action(model, observation)]

    observation, _ = env.reset(seed=1)
    tensor, _ = model.policy.obs_to_tensor(observation)
    agents = tensor[:, 3:].reshape(1, MAX_AGENTS, 4)
    permutation = np.random.default_rng(0).permutation(MAX_AGENTS)
    shuffled = tensor.clone()
    shuffled[:, 3:] = agents[:, permutation].reshape(1, -1)
    q = model.q_net(tensor).detach().numpy()[0]
    q_shuffled = model.q_net(shuffled).detach().numpy()[0]
    assert np.allclose(q[permutation], q_shuffled, atol=1e-5)


def test_linucb_learns_to_avoid_skill_mismatch():
    bandit = LinUCB()
    bandit.learn(3_000, seed=5)
    env = ClaimRoutingEnv(randomize_fleet=True)
    mismatches = choices = 0
    for seed in range(200, 260):
        observation, _ = env.reset(seed=seed)
        agents = observation[3:].reshape(MAX_AGENTS, 4)
        if not (agents[:, 2] * agents[:, 3]).any():
            continue  # no qualified employee on duty for this claim
        action = bandit.act(observation, explore=False)
        assert env.available[action]
        mismatches += int(agents[action, 2] < 0.5)
        choices += 1
    assert choices > 10
    assert mismatches / choices < 0.1


def test_maskable_ppo_never_picks_masked_employees():
    pytest.importorskip("sb3_contrib")
    from sb3_contrib import MaskablePPO

    from rl.compare_algorithms import _maskable_policy_class

    env = ClaimRoutingEnv(randomize_fleet=True)
    model = MaskablePPO(_maskable_policy_class(), env, n_steps=32, batch_size=16, seed=2, device="cpu")
    for seed in range(20):
        observation, _ = env.reset(seed=seed)
        action, _ = model.predict(observation, action_masks=env.action_masks(), deterministic=False)
        assert env.available[int(action)]


def test_compare_writes_reports(tmp_path):
    report = compare(
        algorithms=("linucb",), total_timesteps=300, evaluation_steps=10, evaluation_seed_count=2,
        output_dir=tmp_path / "out", model_dir=tmp_path / "models", log=lambda _message: None,
    )
    policies = report["evaluation"]["policies"]
    assert {"random", "least_workload", "reward_aware", "linucb"} <= set(policies)
    assert set(report["gate_vs_least_workload"]["linucb"]) == {
        "average_reward", "average_wait_time", "average_workload_standard_deviation", "skill_mismatch_rate",
    }
    saved = json.loads((tmp_path / "out" / "algorithm_comparison.json").read_text(encoding="utf-8"))
    assert saved["algorithms"] == ["linucb"]
    assert "| linucb |" in (tmp_path / "out" / "algorithm_comparison.md").read_text(encoding="utf-8")


def test_unknown_algorithm_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        compare(algorithms=("sac",), output_dir=tmp_path, model_dir=tmp_path, log=lambda _message: None)
