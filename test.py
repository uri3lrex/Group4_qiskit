import json

from simulator import run_one_hop, run_two_hop

with open("variant_params.json") as f:
    params = json.load(f)

result = run_one_hop(
    params,
    sim_time_ms=8137,
    seed=1004
)


result = run_two_hop(
    params,
    sim_time_ms=8137,
    seed=1004
)

for seed in [1005, 1006, 1007, 1008]:
    result = run_two_hop(params, 8137, seed)
    print(seed, result["rate"])