
from stable_baselines3 import PPO
from rl.environment import ClaimRoutingEnv, estimate_wait_time

# Load the trained PPO model
model = PPO.load("rl/models/claim_routing_ppo.zip", device="cpu")

# Create the simulation with the same seed
env = ClaimRoutingEnv()
obs, info = env.reset(seed=4)

print("Checking PPO assignments...\n")

for step in range(100):
    action, _ = model.predict(obs, deterministic=True)
    action = int(action)

    # Read the actual, unnormalized values BEFORE assignment
    queue = float(env.queue_lengths[action])
    workload = float(env.workloads[action])
    wait = estimate_wait_time(queue, workload)

    obs, reward, terminated, truncated, info = env.step(action)

    if step % 10 == 0 or step >= 97:
        print(
            f"Step {step:3} | Agent {action} | "
            f"Queue={queue:.2f} | "
            f"Workload={workload:.2f} | "
            f"Wait={wait:.2f} | "
            f"Reward={reward:.3f}"
        )

    if terminated or truncated:
        break
