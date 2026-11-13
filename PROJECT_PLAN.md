# QIS-NET Project 2 — Group 4 / Variant 04: Game Plan

Entanglement distribution network simulator. Internal finish target: **Saturday 21 Nov 2026** (end of week 10). Official deadline is end of week 11, which gives us roughly a one-week safety buffer.

> **Status of dates:** the week 9 checkpoint (~13 Nov) and the official deadline (~28 Nov) are inferred from week numbers. Confirm both on the course page and correct this file.

---

## 1. What we are building

Using the provided harness `qnetsim.py` (**do not modify it**; the autograder ships its own copy), we complete three files and produce a report and a video.

| File | What it must contain |
|---|---|
| `simulator.py` | `run_one_hop`, `run_two_hop`, `run_variant_scenario` (with FIFO request buffer and latency metrics) |
| `policy.py` | Our own policy class replacing `BaselinePolicy` (same constructor and `on_pair_ready` hook), returned by `make_policy` |
| `experiments.py` | `run_sensitivity`: OAT sweep of delivered rate against memory T2, writes `experiment_results.json` |

Zip with the three files at the **zip root**. Unlimited resubmissions, last one counts.

### Marking (autograded code)

| Component | Marks |
|---|---|
| API conformance | 10 |
| Validation against analytics | 25 |
| Seeded determinism | 10 |
| SLO attainment | 25 |
| Robustness across held-out seeds | 10 |
| Experiment artefacts | 20 |

**Validation below 15/25 caps the SLO marks.** An unvalidated simulator earns little, so validation comes first.

### Other deliverables

- **Report:** one PDF per group, max 8 pages. Model description, validation evidence, policy design rationale, sensitivity results with confidence intervals, engineering conclusions against our SLOs, and a discussion of where classical networking concepts appear in the design (and where they break).
- **Video:** max 3 minutes, **all members appear in person**. What we did, why, how, what we achieved, and the single achievement we are proudest of.
- **Peer contribution form:** each member completes it after submission.

### Rules to remember

- numpy + standard library only (plus `qnetsim`).
- Group work within the group only; code similarity is screened across groups.
- **Declare AI-assistant use in file headers.**
- Check that `group` in `variant_params.json` is set to our group number (it currently reads `"4"`).
- Team decision: **we write all code ourselves.**

---

## 2. Our variant (from `variant_params.json`)

| Item | Value |
|---|---|
| Topology | `chain3`: link 0 (nodes 0-1), link 1 (nodes 1-2); swap chain `[0, 1]` |
| Link 0 | attempt rate 1.7746 /ms, p = 0.0554 |
| Link 1 | attempt rate 4.7379 /ms, p = 0.0325 |
| Fresh link fidelity `f_link` | 0.8709 |
| Swap fidelity factor `f_swap` | 0.9762 |
| Swap success `q_swap` | 0.887 |
| Memory T2 | 238.1 ms |
| Purification | allowed |
| Workload | 64.2 requests/s, endpoints (0, 2) |

### SLO targets

| Metric | Target |
|---|---|
| Delivered rate | >= 57.5 pairs/s |
| Mean fidelity | >= 0.7157 |
| p95 latency | <= 1.0 ms |

### Grading setup

- Graded seed 1004; held-out seeds 7012, 7013, 7014.
- Simulation time 8137 ms.
- Tolerances: rate relative 0.08, fidelity absolute 0.01.

### Experiment spec

- T2 grid (ms): 59.5, 119.0, 238.1, 476.2, 952.4.
- 5 seeds per point: 5004, 5104, 5204, 5304, 5404.
- 95% t-interval half-width over per-seed rates.

### Validation targets (expected values)

| Scenario | Rate | Fidelity |
|---|---|---|
| One hop | 98.313 /s | n/a |
| Two hop (T2 = inf, q_swap = 1, immediate swap) | 98.313 /s | 0.7404 |

### Calibration numbers (use as a yardstick, not a target to copy)

| Policy | Rate | Fidelity | p95 latency | Pairs generated per delivery |
|---|---|---|---|---|
| Reference (seed 1004) | 69.93 | 0.7374 | 0.0 ms | 3.44 |
| Baseline | 79.76 | 0.2512 | 0.0 ms | 3.08 |

Held-out reference runs give rates of 72.4, 74.1 and 73.4 /s and fidelity of about 0.738 to 0.740. One held-out run shows a p95 latency of 194 ms.

---

## 3. What the files tell us (analysis so far)

1. **Validation numbers are checkable by hand.**
   - One-hop rate: 1.7746 x 0.0554 x 1000 = 98.31 /s.
   - Two-hop rate equals the same value because link 0 is the bottleneck.
   - Two-hop fidelity: 0.8709^2 x 0.9762 = 0.7404.
   - If our runners reproduce these, we secure most of the validation marks. Reproducing the baseline calibration row (79.76 /s, 0.2512) is a second strong validation check.
2. **Why the baseline fails (likely).** It swaps the oldest pairs and never discards. Link 1 produces about 154 pairs/s against about 98/s on link 0, so aged pairs pile up on link 1 and decay toward the 0.25 floor. Hypotheses to test first: swap the freshest pairs, and discard pairs below a fidelity floor.
3. **Fidelity slack is small.** Ideal two-hop fidelity is 0.7404 and the SLO floor is 0.7157, so there is about 0.025 of room for ageing.
4. **Heavy purification looks infeasible (back-of-envelope, to be tested).**
   - One BBPSSW round on f = 0.8709 gives F' of about 0.901 with success probability about 0.843.
   - That costs about 2.4 raw pairs per purified pair, which caps link 0 at roughly 41 purified pairs/s, or about 36/s after swap losses. That is below the 57.5/s rate SLO.
   - So test purification only as a selective, fidelity-triggered action, not as a default on every link.
5. **The `summarise()` trap.** `p95_delivery_time_ms` is the 95th percentile of absolute delivery timestamps, **not latency**. Latency has to come from the request queue: a request consumes a buffered pair at zero latency, or waits FIFO for a later delivery. Unserved requests are excluded from p95.
6. **The latency SLO is a startup problem.** A p95 of <= 1 ms needs the buffer non-empty for at least 95% of requests. With 64.2 req/s over 8.137 s there are only about 520 requests, so the start-up transient (before the buffer fills) can dominate. The 194 ms held-out reference run shows exactly this risk.
7. **Rate is capped by demand and supply.** Requests arrive at 64.2/s and raw supply is about 98/s on the bottleneck link, so the SLO of 57.5/s sits in a band where swap success (0.887) and discarding both matter.
8. **Fidelity is measured at generation; the buffer does not model further decay** (per the `run_variant_scenario` docstring). Decay still matters while pairs wait on links before swapping.
9. **Harness behaviours to know:**
   - `swap(left, right, left_index, right_index)` takes indices, so the freshest pair is selectable.
   - `purify(link_id)` consumes the two *oldest* pairs on the link and returns a fresh purified pair with `born = now`.
   - `discard(link_id, index)` exists for dropping aged pairs.
   - The simulator sets `self.policy` inside `run()`, and `on_pair_ready` fires on every successful link generation.
10. **Experiment details.** The provided t-table lookup gives 2.776 for 5 seeds (df = 4), which is correct. Each grid point must deep-copy params and set `physics.t2_ms`.

### Physics reference (from the harness docs)

- Decay: F(t) = 0.25 + (F0 - 0.25) exp(-t / T2).
- Swap: succeeds with probability q_swap; output fidelity = F_left x F_right x F_swap.
- BBPSSW on two identical depolarising pairs of fidelity f: with e = (1 - f)/3, P_succ = f^2 + 2fe + 5e^2 and F' = (f^2 + e^2) / P_succ.

---

## 4. Team roles

| Role | Team member | Owns |
|---|---|---|
| A — Simulator lead | _TBD_ | Runners, request buffer, latency metric, packaging |
| B — Policy lead | _TBD_ | Policy prototype, tuning, robustness |
| C — Validation & experiments lead | _TBD_ | Analytic checks, determinism tests, T2 sweep, statistics |
| D — Report lead | _TBD_ | PDF report, video script, classical-networking section |

**Cross-review rule:** every file is reviewed by someone who did not write it, and all four of us must be able to explain the whole system on camera.

---

## 5. Schedule (30 Oct to 21 Nov)

```mermaid
gantt
    title QIS-NET Project 2 plan
    dateFormat YYYY-MM-DD
    axisFormat %b %d

    section Setup
    Kickoff, roles, repo (All)                 :2026-10-30, 3d

    section Simulator (A)
    one_hop / two_hop runners                  :2026-11-01, 5d
    Variant runner and request buffer          :2026-11-05, 6d
    Zip, AI headers, autograder dry run        :2026-11-16, 3d

    section Validation and experiments (C)
    Validate against analytics                 :2026-11-03, 5d
    Reproduce baseline calibration (A+C)       :2026-11-08, 4d
    Determinism and seed tests                 :2026-11-08, 5d
    T2 sweep, CI, JSON, plots                  :2026-11-11, 5d

    section Policy (B)
    Policy prototype                           :2026-11-02, 8d
    Policy tuning against SLOs                 :2026-11-09, 8d
    Held-out seed checks (B+C)                 :2026-11-14, 4d

    section Report and video (D, All)
    Report: model and validation               :2026-11-05, 8d
    Report: policy and results                 :2026-11-12, 8d
    Classical networking section (D+B)         :2026-11-11, 6d
    Video: script, rehearse, record (All)      :2026-11-15, 5d
    Final review and PDF (All)                 :2026-11-18, 4d

    section Milestones
    Week 9 checkpoint (approx.)                :milestone, 2026-11-13, 0d
    Code freeze                                :milestone, 2026-11-17, 0d
    Internal target                            :milestone, 2026-11-21, 0d
```

### Task table

| # | Task | Owner | Dates | Done when |
|---|---|---|---|---|
| 1 | Kickoff, roles, repo, read spec | All | 30 Oct to 1 Nov | Roles agreed, repo set up, spec read by everyone |
| 2 | `run_one_hop`, `run_two_hop` | A | 1 to 5 Nov | Both match expected values within tolerance |
| 3 | Validate against analytics | C | 3 to 7 Nov | Hand calculations written down and matched |
| 4 | `run_variant_scenario` and request buffer | A | 5 to 10 Nov | Returns all four metrics; p95 computed from request queue |
| 5 | Policy prototype | B | 2 to 9 Nov | Beats baseline fidelity; freshest-first and discard floor tested |
| 6 | Reproduce baseline calibration | A+C | 8 to 11 Nov | Baseline gives about 79.8/s, 0.251, 3.08 consumed per delivery |
| 7 | Determinism and seed tests | C | 8 to 12 Nov | Same seed gives identical output across repeated runs |
| 8 | Policy tuning against SLOs | B | 9 to 16 Nov | All three SLOs met on seed 1004 |
| 9 | T2 sweep, CI, JSON, plots | C | 11 to 15 Nov | `experiment_results.json` matches the output contract |
| 10 | Held-out seed checks | B+C | 14 to 17 Nov | SLOs hold on seeds 7012 to 7014 |
| 11 | Report: model and validation | D | 5 to 12 Nov | Sections drafted with evidence |
| 12 | Report: policy and results | D (+ All) | 12 to 19 Nov | Policy rationale, sensitivity results with CIs, SLO conclusions |
| 13 | Classical networking discussion | D+B | 11 to 16 Nov | Analogies and breakdowns written up |
| 14 | Zip, AI headers, dry run | A | 16 to 18 Nov | Fresh-environment run of the zip passes |
| 15 | Video: script, rehearse, record | All | 15 to 19 Nov | Recorded with all members present, under 3 min |
| 16 | Final review, PDF, forms | All | 18 to 21 Nov | PDF under 8 pages; everything ready to submit |

---

## 6. Checkpoints and definition of done

- [x] **6 Nov:** both reference runners match 98.313 /s and 0.7404; roles and repo settled.
- [x] **13 Nov (week 9 checkpoint):** full simulator reproduces the baseline calibration numbers and passes determinism tests; a first policy beats the baseline.
- [ ] **17 Nov (code freeze):** policy meets rate, fidelity and p95 SLOs on seed 1004 **and** on held-out seeds 7012 to 7014; sweep JSON generated.
- [ ] **21 Nov:** dry-run zip passes; PDF under 8 pages; video recorded with all four members; AI use declared in file headers.
- [ ] Peer contribution forms completed after submission.

---

## 7. Risks and open questions

| Risk or question | Mitigation |
|---|---|
| Start-up latency transient breaks the p95 <= 1 ms SLO | Study early-request behaviour on all four seeds; consider policy choices that fill the buffer sooner |
| Purification hurts rate more than it helps fidelity | Test selective, threshold-triggered purification only; compare against no purification |
| Held-out seeds behave differently from seed 1004 | Tune with margin, not to the edge; check all four seeds before freeze |
| Unclear whether "rate" means delivered pairs or served requests | Follow the docstrings and `summarise` (delivered pairs per second); raise with the module team if still unsure |
| Deadlines inferred, not confirmed | Check the course page and update Section 1 |
| Time lost on report and video at the end | Draft report sections as results land; fix a video recording slot now |

---

## 8. Helpful resources

> **How to use these:** they are for **understanding concepts, structure and validation methods**, not for copying code. Our submission is numpy + standard library only, similarity is screened, and the course expects original work. Cite anything that shapes our design in the report, and declare any AI-assistant use in file headers.

### Closest to our problem (read these first)

| Resource | Why it helps | Link |
|---|---|---|
| SeQUeNCe (GitHub) | Discrete-event quantum network simulator. Its examples include a **three-router linear network with entanglement generation, purification and swapping**, which mirrors our `chain3` setup. Good for seeing how swap and purify ordering is organised. | https://github.com/sequence-toolbox/SeQUeNCe |
| SeQUeNCe tutorial docs | Walkthrough chapters on modules (hardware, entanglement management, resource management, network management). | https://sequence-rtd-tutorial.readthedocs.io/ |
| SeQUeNCe paper (Wu et al., Quantum Sci. Technol., 2021) | Architecture and validation approach. | https://doi.org/10.1088/2058-9565/ac22f6 |
| QuISP paper (Satoh et al., IEEE QCE 2022) | **Validated against analytic results for a small network**, which is the same idea as our validation section. Also discusses purify-and-swap (1G) repeater networks. | https://arxiv.org/pdf/2112.07093 |
| QuISP (GitHub) | Event-driven simulator of quantum repeater networks, built on OMNeT++ (heavy install, so read rather than run). | https://github.com/sfc-aqua/quisp |
| QuISP site and docs | Documentation and design goals. | https://aqua.sfc.wide.ad.jp/quisp/ |

### Other simulators (for comparison and report background)

| Resource | Notes | Link |
|---|---|---|
| SimQN (GitHub) | Python, discrete-event, supports entanglement distribution and routing; positioned like ns-3 for quantum networks. Useful for the classical-networking discussion. | https://github.com/QNLab-USTC/SimQN |
| SimQN docs | Tutorial and API manual. | https://www.github.com/ertuil/SimQN (documentation linked from the README) |
| NetSquid | Widely used discrete-event platform for quantum networks; registration needed for the package. | https://netsquid.org/ |
| QuNetSim | Python framework for quantum network simulation. | https://github.com/tqsd/QuNetSim |
| SimulaQron | Application-level quantum internet simulator. | https://github.com/SoftwareQuTech/SimulaQron |
| GitHub topic: quantum-network-simulator | Browse for small student-scale projects and experiments. | https://github.com/topics/quantum-network-simulator |
| Review: "Simulators for Quantum Network Modelling: A Comprehensive Review" | Side-by-side comparison of the simulators above. | https://arxiv.org/pdf/2408.11993 |

### Theory papers behind the model

| Paper | Relevance | Link |
|---|---|---|
| Bennett et al., "Purification of Noisy Entanglement and Faithful Teleportation via Noisy Channels", PRL 76, 722 (1996) | Origin of BBPSSW, the purification model used in `qnetsim.py` | https://arxiv.org/abs/quant-ph/9511027 |
| Briegel, Dür, Cirac, Zoller, "Quantum Repeaters: The Role of Imperfect Local Operations in Quantum Communication", PRL 81, 5932 (1998) | The repeater scheme (swap plus purify) our chain topology represents. Link from memory; verify before citing. | https://arxiv.org/abs/quant-ph/9803056 |
| Wehner, Elkouss, Hanson, "Quantum internet: A vision for the road ahead", Science 362 (2018) | Overview of the quantum internet and its stages; good report background. Verify link before citing. | search the title on Science / arXiv |
| Horodecki et al., "Quantum entanglement", Rev. Mod. Phys. (2009), Section XII | Reference on entanglement distillation and purification protocols | https://arxiv.org/pdf/quant-ph/0702225 |

### Classical networking and simulation background (for the report discussion)

| Topic | Suggested source |
|---|---|
| Queueing, buffers, FIFO service, latency percentiles | Kurose and Ross, *Computer Networking: A Top-Down Approach* (queueing delay and packet scheduling chapters) |
| Discrete-event simulation design | Law, *Simulation Modeling and Analysis* (event lists, random streams, output analysis) |
| Confidence intervals from replications | Same text, output-analysis chapter; also any intro statistics source on the Student t-distribution |

Points worth developing for the "where classical concepts appear and where they break" section: store-and-forward versus swap (pairs cannot be copied or buffered indefinitely), buffer ageing (pairs decay while waiting), retransmission versus purification, and admission/queueing at the request buffer.

### Python references (standard library and numpy only)

| Topic | Link |
|---|---|
| `heapq` (event queue used by the harness) | https://docs.python.org/3/library/heapq.html |
| `numpy.random.Generator` (seeded determinism) | https://numpy.org/doc/stable/reference/random/generator.html |
| `json` module (experiment output contract) | https://docs.python.org/3/library/json.html |
| `statistics` and numpy for mean/stdev (note `ddof=1` for sample standard deviation) | https://numpy.org/doc/stable/reference/generated/numpy.std.html |
| `copy.deepcopy` (isolating params per grid point) | https://docs.python.org/3/library/copy.html |

---

## 9. Suggested repo layout (no code)

```
.
├── PROJECT_PLAN.md          # this file
├── README.md                # how to run, team, AI-use declaration
├── submission/              # the three graded files only, at zip root when zipped
│   ├── simulator.py
│   ├── policy.py
│   └── experiments.py
├── provided/                # qnetsim.py, variant_params.json, spec PDF (read-only reference)
├── validation/              # hand calculations, notes, comparison tables
├── results/                 # experiment_results.json, plots, SLO tables per seed
├── report/                  # report drafts and figures
└── video/                   # script and slot details
```

Keep `provided/qnetsim.py` untouched. When zipping, include only the three submission files at the root.

---

## 10. Working agreements

- Agree who reviews whom before the first commit.
- Short commit messages that say which task number (Section 5) they belong to.
- Record every policy experiment (what changed, seed, rate, fidelity, p95) in `results/` so the report writes itself.
- Add an AI-assistant use declaration to each file header as soon as a file is created.
- Do not look at or share code with other groups.
