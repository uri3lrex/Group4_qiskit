"""
experiments.py — QIS-NET Project 2 sensitivity experiment (STUDENT FILE).

Implement run_sensitivity: one-at-a-time (OAT) sensitivity of the variant
scenario's delivered RATE to memory T2 over params['experiment']['t2_grid_ms'],
using >= params['experiment']['seeds_per_point'] seeds per grid point.

Output contract (autograded): write experiment_results.json containing
{
  "parameter": "t2_ms",
  "grid": [...],
  "seeds_per_point": int,
  "points": [
     {"t2_ms": x, "rate_mean": m, "rate_ci95": h, "n_seeds": k}, ...
  ]
}
CI: 95% t-interval half-width over the per-seed rates.

AI-assistant use declaration: run_sensitivity was written with help from
Claude (Anthropic AI assistant) and reviewed by Group 4.
"""

import copy
import json
import math

import numpy as np

from policy import make_policy, BaselinePolicy, FidelityPolicy
import csv
from simulator import run_variant_scenario


def mean_ci95(values):
    """Return (mean, 95% CI half-width) using the t-distribution."""
    n = len(values)
    m = float(np.mean(values))
    if n < 2:
        return m, 0.0
    s = float(np.std(values, ddof=1))
    # t_{0.975, df} for small df (table lookup, no scipy needed)
    t_table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
               6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}
    t = t_table.get(n - 1, 1.96)
    return m, t * s / math.sqrt(n)


def run_sensitivity(params, seeds, sim_time_ms=None,
                    out_path="experiment_results.json") -> dict:
    """One-at-a-time (OAT) sweep of delivered rate against memory T2.

    For each T2 value in the grid we change ONLY physics.t2_ms (everything
    else stays as in the variant), run the variant scenario once per seed,
    and summarise the per-seed rates as mean +/- 95% t-interval half-width.
    """
    exp = params["experiment"]
    grid = list(exp["t2_grid_ms"])
    seeds_per_point = int(exp["seeds_per_point"])
    if sim_time_ms is None:
        sim_time_ms = params["grading"]["sim_time_ms"]

    use_seeds = list(seeds)[:seeds_per_point]
    if len(use_seeds) < seeds_per_point:
        raise ValueError(f"need at least {seeds_per_point} seeds, "
                         f"got {len(use_seeds)}")

    points = []
    for t2 in grid:
        # copy so one grid point can never change another (or the caller's params)
        params_copy = copy.deepcopy(params)
        params_copy["physics"]["t2_ms"] = t2

        rates = []
        for seed in use_seeds:
            policy = make_policy(params_copy)   # fresh policy per run
            #print(type(policy).__name__) # debug statement
            result = run_variant_scenario(params_copy, sim_time_ms, seed, policy)
            #print( # debug statement
               #f"T2={t2:6.1f} | "f"Seed={seed} | "f"Rate={result['rate']:.4f} | "f"Fidelity={result['mean_fidelity']:.4f} | "f"P95={result['p95_latency_ms']:.4f} | "f"Consumption={result['pairs_consumed_per_delivery']:.4f}" )
            
            rates.append(float(result["rate"]))

        mean, half_width = mean_ci95(rates)
        points.append({
            "t2_ms": t2,
            "rate_mean": mean,
            "rate_ci95": half_width,
            "n_seeds": len(rates),
        })

    results = {
        "parameter": "t2_ms",
        "grid": grid,
        "seeds_per_point": seeds_per_point,
        "points": points,
    }
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    return results

def compare_policies(
    params,
    seeds,
    sim_time_ms=None,
    out_path="policy_comparison.csv"
):
    """Compare baseline and optimized policies across the T2 grid."""

    exp = params["experiment"]
    grid = exp["t2_grid_ms"]
    seeds_per_point = exp["seeds_per_point"]

    if sim_time_ms is None:
        sim_time_ms = params["grading"]["sim_time_ms"]

    use_seeds = list(seeds)[:seeds_per_point]

    if len(use_seeds) < seeds_per_point:
        raise ValueError("Not enough experiment seeds")

    policies = {
        "Baseline": BaselinePolicy,
        "Fidelity": FidelityPolicy,
    }

    results = []

    for t2 in grid:

        for policy_name, policy_class in policies.items():

            for seed in use_seeds:

                params_copy = copy.deepcopy(params)
                params_copy["physics"]["t2_ms"] = t2

                policy = policy_class(params_copy)

                result = run_variant_scenario(
                    params_copy,
                    sim_time_ms,
                    seed,
                    policy
                )

                slo = params_copy["slo"]

                rate_pass = (
                    result["rate"] >= slo["min_rate"]
                )
                fidelity_pass = (
                    result["mean_fidelity"] >= slo["min_fidelity"]
                )
                latency_pass = (
                    result["p95_latency_ms"] <= slo["max_p95_latency_ms"]
                )

                row = {
                    "policy": policy_name,
                    "t2_ms": t2,
                    "seed": seed,
                    **result,
                    "rate_pass": rate_pass,
                    "fidelity_pass": fidelity_pass,
                    "latency_pass": latency_pass,
                    "all_slo_pass": (
                        rate_pass
                        and fidelity_pass
                        and latency_pass
                    ),
                }

                results.append(row)

                print(
                    f"{policy_name:8s} | "
                    f"T2={t2:6.1f} | "
                    f"Seed={seed} | "
                    f"Rate={result['rate']:.4f} | "
                    f"Fidelity={result['mean_fidelity']:.4f} | "
                    f"P95={result['p95_latency_ms']:.4f} | "
                    f"SLO pass={row['all_slo_pass']}"
                )

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=results[0].keys()
        )
        writer.writeheader()
        writer.writerows(results)

    return results


if __name__ == "__main__":
    import sys
    params = json.load(open(sys.argv[1] if len(sys.argv) > 1
                            else "variant_params.json"))
    exp = params["experiment"]
    seeds = exp["seeds"]
    out = run_sensitivity(params, seeds)
    print(json.dumps(out, indent=2))
    # Additional policy comparison
    print("\n--- POLICY COMPARISON ---")
    comparison = compare_policies(params, seeds)
    rate_passes= [x["rate"]>57.5 for x in comparison if x["policy"] == "Fidelity"]
    fidelity_passes = [x["fidelity_pass"] for x in comparison if x["policy"] == "Fidelity"]
    latency_passes = [x["latency_pass"] for x in comparison if x["policy"] == "Fidelity"]
    slo_passes = [x["all_slo_pass"] for x in comparison if x["policy"] == "Fidelity"]
    print(f"Rate passes: {rate_passes.count(True)}/{len(rate_passes)}")
    print(f"Fidelity passes: {fidelity_passes.count(True)}/{len(fidelity_passes)}")
    print(f"Latency passes: {latency_passes.count(True)}/{len(latency_passes)}")
    print(f"SLO passes: {slo_passes.count(True)}/{len(slo_passes)}")
