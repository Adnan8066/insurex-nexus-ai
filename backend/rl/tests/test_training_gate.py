from rl.training import _candidate_quality, _gate_checks


def _evaluation(candidate, baseline):
    metrics = ("average_reward", "average_wait_time", "average_workload_standard_deviation", "skill_mismatch_rate")
    return {"policies": {
        "ppo": {"mean": dict(zip(metrics, candidate))},
        "least_workload": {"mean": dict(zip(metrics, baseline))},
    }}


def test_checkpoint_matching_baseline_passes_non_regression_gate():
    report = _evaluation((1.0, 2.0, 3.0, 0.2), (1.0, 2.0, 3.0, 0.2))
    assert all(_gate_checks(report).values())


def test_checkpoint_quality_prefers_more_gate_checks():
    baseline = (1.0, 2.0, 3.0, 0.2)
    passing = _evaluation(baseline, baseline)
    failing = _evaluation((0.9, 2.1, 3.1, 0.2), baseline)
    assert _candidate_quality(passing) > _candidate_quality(failing)
