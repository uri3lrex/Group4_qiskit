import json
from simulator import run_one_hop, run_two_hop, run_variant_scenario

with open("variant_params.json") as f:
    params = json.load(f)

sim_time_ms = params["grading"]["sim_time_ms"]
main_seed = params["grading"]["seed"]

# Reference scenario tests
print("<--- ONE-HOP -->")
print(run_one_hop(params, sim_time_ms, main_seed))

print("\n<--- TWO-HOP -->")

test_seeds = [main_seed, 1005, 1006, 1007, 1008]

for seed in test_seeds:
    result = run_two_hop(params, sim_time_ms, seed)

    print(
        f"Seed {seed}: "
        f"Rate = {result['rate']:.3f} pairs/s, "
        f"Fidelity = {result['mean_fidelity']:.4f}"
    )

print("\n<--- VARIANT -->")

test_seeds = [main_seed, 2005, 2006, 2007, 2008]
for seed in test_seeds:
    result = run_variant_scenario(params, sim_time_ms, seed, policy=None)

    print(
        f"Seed {seed}: "
        f"Rate = {result['rate']:.3f} pairs/s, "
        f"Fidelity = {result['mean_fidelity']:.4f}, "
        f"p95 latency = {result['p95_latency_ms']:.2f} ms, "
        f"Pairs consumed per delivery = {result['pairs_consumed_per_delivery']:.2f}"
    )