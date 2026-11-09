import json

from simulator import run_one_hop

with open("variant_params.json") as f:
    params = json.load(f)

result = run_one_hop(
    params,
    sim_time_ms=8137,
    seed=1004
)

print(result)