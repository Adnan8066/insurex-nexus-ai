from gymnasium.utils.env_checker import check_env

from rl.environment import ClaimRoutingEnv
from rl.evaluation import evaluate_across_seeds, evaluate_baselines
import numpy as np

def test_environment_passes_gymnasium_checker():
    check_env(ClaimRoutingEnv(), skip_render_check=True)


def test_simulator_decays_workload_and_penalizes_skill_mismatch():
    low_skill_env = ClaimRoutingEnv(max_episode_steps=5)
    low_skill_env.reset(seed=22)
    low_skill_env.queue_lengths[:] = 2
    low_skill_env.workloads[:] = 20
    low_skill_env.skill_tiers[:] = 1
    low_skill_env.required_skill_tier = 5
    low_skill_env.claim_complexity = 0.5
    low_skill_env.processing_difficulty = 0.5
    before = low_skill_env.workloads.copy()
    _, low_skill_reward, _, _, low_skill_info = low_skill_env.step(0)

    high_skill_env = ClaimRoutingEnv(max_episode_steps=5)
    high_skill_env.reset(seed=22)
    high_skill_env.queue_lengths[:] = 2
    high_skill_env.workloads[:] = 20
    high_skill_env.skill_tiers[:] = 5
    high_skill_env.required_skill_tier = 5
    high_skill_env.claim_complexity = 0.5
    high_skill_env.processing_difficulty = 0.5
    _, high_skill_reward, _, _, high_skill_info = high_skill_env.step(0)

    assert low_skill_info["skill_mismatch"] is True
    assert high_skill_info["skill_mismatch"] is False
    assert np.isclose(high_skill_reward - low_skill_reward, 8.0)
    assert (low_skill_env.workloads <= before + 6.0).all()
    assert (low_skill_env.queue_lengths == [2, 1, 1, 1, 1]).all()


def test_baselines_run_for_one_hundred_simulated_arrivals():
    results = evaluate_baselines(steps=100, seed=5)

    assert results["random"]["steps"] == 100
    assert results["least_workload"]["steps"] == 100
    for metrics in results.values():
        assert "average_reward" in metrics
        assert "average_wait_time" in metrics
        assert "average_workload_standard_deviation" in metrics


def test_multi_seed_evaluation_reports_variability_and_reproducible_seeds():
    result = evaluate_across_seeds(steps=20, seeds=(41, 42))

    assert result['synthetic_only'] is True
    assert result['evaluation_seed_count'] == 2
    assert len(result['policies']['random']['per_seed']) == 2
    assert 'std' in result['policies']['least_workload']
