"""
simulator.py — QIS-NET Project 2 runner (STUDENT FILE: complete the TODOs).

Drive the provided harness (qnetsim.py) to implement the three graded
entry points. Signatures are normative; the autograder imports them.

Only numpy + standard library + qnetsim may be used.
"""

from email import policy
import math

import numpy as np

from qnetsim import Link, Simulator, summarise
from policy import BaselinePolicy, make_policy


# ---------------------------------------------------------------- helpers


def make_links(params, which="variant"):
    """Build Link objects from the variant parameter dict.

    `which="one_hop"` / `"two_hop"` select the reference scenarios defined in
    params["reference"]; `which="variant"` builds the full variant topology.
    PROVIDED — you should not need to change this.
    """
    links = []
    if which == "one_hop":
        ref = params["reference"]["one_hop"]
        links.append(Link(link_id=0, nodes=(0, 1),
                          attempt_rate=ref["attempt_rate"],
                          p_success=ref["p_success"],
                          f_link=params["physics"]["f_link"]))
    elif which == "two_hop":
        ref = params["reference"]["two_hop"]
        for i, lp in enumerate(ref["links"]):
            links.append(Link(link_id=i, nodes=(i, i + 1),
                              attempt_rate=lp["attempt_rate"],
                              p_success=lp["p_success"],
                              f_link=params["physics"]["f_link"]))
    else:
        for i, lp in enumerate(params["topology"]["links"]):
            links.append(Link(link_id=i, nodes=tuple(lp["nodes"]),
                              attempt_rate=lp["attempt_rate"],
                              p_success=lp["p_success"],
                              f_link=params["physics"]["f_link"]))
    return links


def request_times(params, sim_time_ms, seed):
    """Deterministic request arrival times (ms) for the variant workload.
    Uses a generator derived from `seed` so runs are reproducible.
    PROVIDED."""
    wl = params["workload"]
    rng = np.random.default_rng(seed + 7919)
    t, times = 0.0, []
    while True:
        t += rng.exponential(1000.0 / wl["arrival_rate_per_s"])
        if t > sim_time_ms:
            break
        times.append(t)
    return times


# ---------------------------------------------------------------- graded entry points


def run_one_hop(params, sim_time_ms, seed) -> dict:
    """Reference scenario: a single elementary link, no swapping.
    Return {"rate": ..., "mean_fidelity": ...}.

    TODO: build the one-hop links, run the Simulator for sim_time_ms with
    policy=None, and use qnetsim.summarise on a delivered-list you fill
    yourself (every generated pair counts as delivered here — record
    deliveries via a tiny inline policy or by reading state.pairs/stats).

    HINT: the harness only records `delivered` on swap; for the one-hop
    case, write a 3-line policy class whose on_pair_ready appends a
    DeliveredPair-equivalent record (or count pairs via state.stats and
    track fidelities in a list).
    """
    # read link and network state, build simulator, run, summarise, return dict
    links = make_links(params, which="one_hop")
    simulator = Simulator(links=links, t2=params['physics']['t2_ms'], q_swap=params['physics']['q_swap'], f_swap=params['physics']['f_swap'],
                          purification_allowed=params['physics']['purification_allowed'], seed=seed)
    simulator.run(sim_time_ms)
    network_state = simulator.state
    delivered_pairs = []
    for link_id, pairs in network_state.pairs.items():
        for pair in pairs:
            delivered_pairs.append(pair)

    # calculate rate and mean fidelity
    rate = network_state.stats["generated"] / (sim_time_ms / 1000.0)  # convert ms to seconds
    mean_fidelity = sum(pair.f0 for pair in delivered_pairs) / len(delivered_pairs) if delivered_pairs else 0.0
    return {"rate": rate, "mean_fidelity": mean_fidelity}   
    raise NotImplementedError("TODO: implement run_one_hop")


def run_two_hop(params, sim_time_ms, seed) -> dict:
    """Reference scenario: two links, one repeater, immediate swap,
    T2 = infinity, q_swap = 1 (params['reference']['two_hop']).
    Return {"rate": ..., "mean_fidelity": ...}.

    TODO: build links, construct the Simulator with t2=math.inf,
    q_swap=1.0, f_swap=params['physics']['f_swap']; use a policy that swaps
    as soon as both links hold a pair; summarise with qnetsim.summarise.
    """

    links = make_links(params, which="two_hop")
    simulator = Simulator(links=links, t2=math.inf, q_swap=1.0, f_swap=params['physics']['f_swap'],
                          purification_allowed=params['physics']['purification_allowed'], seed=seed)

    policy = BaselinePolicy(params)
    simulator.run(sim_time_ms, policy=policy)

    #print("Generated:", simulator.state.stats["generated"])
    #print("Delivered:", len(simulator.delivered))
    #print("Remaining pairs:", {
    #    link_id: len(pairs)
    #    for link_id, pairs in simulator.state.pairs.items()
    #})

    # calculate rate and mean fidelity
    results = summarise(simulator.delivered, sim_time_ms)
    return {"rate": results['rate'], "mean_fidelity": results['mean_fidelity']}

    raise NotImplementedError("TODO: implement run_two_hop")


def run_variant_scenario(params, sim_time_ms, seed, policy) -> dict:
    """Full variant scenario with YOUR policy.
    Return {"rate": ..., "mean_fidelity": ..., "p95_latency_ms": ...,
            "pairs_consumed_per_delivery": ...}.

    TODO:
      * build the variant topology links;
      * construct the Simulator with your variant's physics
        (t2, q_swap, f_swap, purification_allowed, seed);
      * generate request_times(...); use a pooled unlimited end-to-end buffer.
        A request consumes a buffered pair at zero latency, or queues FIFO
        for a later delivery. Exclude unserved requests from p95. Fidelity
        is measured at generation; this buffer does not model further decay;
      * return the four metrics. pairs_consumed_per_delivery =
        stats['generated'] / max(1, delivered).
    """

    # setting up the simulator with the variant topology and physics parameters

    from collections import deque

    # 1. Initialize queues and tracking lists
    unserved_request = deque()
    end_to_end_buffer = deque()
    served_fidelities = []
    latencies = []

    # create simsulator with variant links and physics parameters

    links = make_links(params, which="variant")
    simulator = Simulator(
        links=links,
        t2=params["physics"]["t2_ms"],
        q_swap=params["physics"]["q_swap"],
        f_swap=params["physics"]["f_swap"],
        purification_allowed=params["physics"]["purification_allowed"],
        seed=seed
    )

    # handle request arrivals: either serve immediately from buffer or queue for later
    def on_request_arrival(request_id):
        arrival_time = simulator.state.now
        if end_to_end_buffer:
            # consume a pair from the buffer
            fidelity = end_to_end_buffer.popleft()
            served_fidelities.append(fidelity)
            latencies.append(0)  # Zero latency for immediate delivery
        else:
            # No available pairs, queue the request
            unserved_request.append((request_id, arrival_time))

    # wrap policy to track delivered pairs and handle waiting requests

    class RequestAwarePolicy:

        def __init__(self, inner_policy):
            self.inner_policy = inner_policy

        def on_pair_ready(self, link, pair, state, sim):

            # Number of successful swaps before running the policy
            before = len(sim.delivered)
            self.inner_policy.on_pair_ready(link, pair, state, sim)
            new_pairs = sim.delivered[before:]

            for delivered_pair in new_pairs:
                if unserved_request:
                    # Serve the oldest waiting request
                    request_id, arrival_time = unserved_request.popleft()

                    served_fidelities.append(delivered_pair.fidelity)
                    latencies.append(state.now - arrival_time)

                else:
                    # Store the pair until a request arrives
                    end_to_end_buffer.append(delivered_pair.fidelity)
    # generate request times and run the simulator
    request_arrivals = request_times(params, sim_time_ms, seed)

    for request_id, arrival_time in enumerate(request_arrivals):
        simulator.eq.push(
            arrival_time,
            on_request_arrival,
            request_id
        )

    # Use the RequestAwarePolicy to wrap the provided policy
    if policy is None:
        policy = make_policy(params)
    wrapped_policy = RequestAwarePolicy(policy)


    simulator.run(
        sim_time_ms,
        policy=wrapped_policy
    )

    # calculate rate, mean fidelity, p95 latency, pairs consumed per delivery
    delivered_count = len(served_fidelities)
    rate = delivered_count / (sim_time_ms / 1000.0)
    mean_fidelity = (float(np.mean(served_fidelities)) if served_fidelities else 0.0)
    p95_latency = (float(np.percentile(latencies, 95))if latencies else 0.0)
    pairs_consumed_per_delivery = (simulator.state.stats["generated"] / max(1, delivered_count))

    return {
        "rate": rate,
        "mean_fidelity": mean_fidelity,
        "p95_latency_ms": p95_latency,
        "pairs_consumed_per_delivery": pairs_consumed_per_delivery
    }

    raise NotImplementedError("TODO: implement run_variant_scenario")
