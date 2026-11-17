# Claim routing: algorithm comparison

Synthetic simulator only. 50,000 training steps per learner, evaluated on 10 held-out seeds x 100 claims. Mean (+/- std across seeds).

| Rank | Policy | Reward (higher better) | Wait (lower) | Workload std (lower) | Skill mismatch (lower) | Gate vs heuristic | Train time |
|---|---|---|---|---|---|---|---|
| 1 | dqn | -1.192 +/- 2.018 | 0.743 | 2.834 | 25.0% | FAIL (3/4) | 97s |
| 2 | ppo_bc | -1.263 +/- 2.046 | 1.986 | 5.088 | 22.5% | PASS (4/4) | 233s |
| 3 | a2c | -1.263 +/- 2.046 | 1.985 | 5.084 | 22.5% | PASS (4/4) | 111s |
| 4 | linucb | -1.263 +/- 2.046 | 1.985 | 5.084 | 22.5% | PASS (4/4) | 15s |
| 5 | least_workload | -1.263 +/- 2.046 | 1.986 | 5.088 | 22.5% | (reference) | - |
| 6 | ppo | -1.263 +/- 2.046 | 1.987 | 5.092 | 22.5% | FAIL (1/4) | 136s |
| 7 | maskable_ppo | -1.263 +/- 2.046 | 1.987 | 5.092 | 22.5% | FAIL (1/4) | 130s |
| 8 | reward_aware | -1.264 +/- 2.048 | 1.995 | 5.089 | 22.5% | (baseline) | - |
| 9 | random | -4.302 +/- 1.398 | 1.060 | 2.680 | 63.2% | (baseline) | - |

Gate: the learner must be at least as good as `least_workload` on all four metrics (the same rule `rl.training` uses before a model may give advice).
