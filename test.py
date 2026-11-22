import json
from policy import make_policy, BaselinePolicy
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

seeds = [
    params["grading"]["seed"],
    *params["grading"]["held_out_seeds"]
]

slo = params["slo"]

for seed in seeds:
    # run the same seed with the baseline policy and with the applied fidelity policy
    for policy_name, policy in [("Baseline", BaselinePolicy(params)), ("Fidelity", make_policy(params))]:

        result = run_variant_scenario(
            params,
            sim_time_ms=params["grading"]["sim_time_ms"],
            seed=seed,
            policy=policy
        )

        slo_pass = (
            result["rate"] >= slo["min_rate"]
            and result["mean_fidelity"] >= slo["min_fidelity"]
            and result["p95_latency_ms"] <= slo["max_p95_latency_ms"]
        )

        print(
            f"Seed {seed} {policy_name:8s}: "
            f"Rate = {result['rate']:.3f} pairs/s, "
            f"Fidelity = {result['mean_fidelity']:.4f}, "
            f"P95 = {result['p95_latency_ms']:.3f} ms, "
            f"Consumed/delivery = {result['pairs_consumed_per_delivery']:.3f}, "
            f"SLO pass = {slo_pass}"
        )

        if policy_name == "Baseline":
            baseline_fidelity = result["mean_fidelity"]
        else:
            improvement = (result["mean_fidelity"] - baseline_fidelity) / baseline_fidelity * 100
            print(f"Seed {seed} fidelity improvement: {improvement:.1f}%\n")