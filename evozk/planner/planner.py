#!/usr/bin/env python3
"""EvoZK design planner (Section 5.2 and Algorithm 2 of the paper): count model, setup feasibility, calibration,
prediction, recommendation.

Algorithm 2 states this module line for line; the comments "Alg. 2 line N" mark the correspondence.
Library only: it reads no file and writes nothing.

Count model (never timing):
  Groth16, rapidsnark : n_b(cell) = R1CS constraints (data/rq1_proving/circuit_sizes.tsv, nConstraints)
  PLONK, FFLONK       : n_b(cell) = p 2^p, with 2^p the evaluation domain (p = plonkPower / fflonkPower)
Setup feasibility under a powers-of-tau file of power P (snarkjs 0.7.6):
  Groth16, rapidsnark : groth16Power <= P                 (src/zkey_new.js: "circuit too big for this power of tau")
  PLONK               : plonkPower <= P                   (src/plonk_setup.js: cirPower > power is refused)
  FFLONK              : 9 * 2^fflonkPower + 18 <= 2^(P+1) - 1, the G1 points of ptau section 2
                        (src/fflonk_setup.js: "Section 2 too small"); a ptau of power P holds 2^(P+1) - 1 tau G1 points.
  A design whose circuit cannot be set up on backend b in some version is unsupported on b in that history: it is
  excluded from the planner (here), the oracle and the fixed policies (lifecycle.py), and reported.
Calibration: one scale constant per backend, alpha_b = exp(mean_i(ln m_i - ln n_b(cell_i))) over the design cells of
  that backend's calibration run only (m_i = per-cell median per-proof time). The same estimator on the setup
  medians of that run gives the setup constant beta_b.
Prediction: c_hat = alpha_b * n_b(cell); S_hat_time = beta_b * n_b(cell).
Lifecycle of design D over a history: the V proofs are spread evenly over the history's versions, so
  c_D = mean over versions v of c(D(v)); every release k whose regeneration set contains D costs one regeneration of
  the post-release cell D(v_k): S = setup time + lambda_gas * deploy gas + lambda_gov * 1 governance event.
  C_D(V) = V * c_D + sum_k S(D(v_k))   (= V c_D + R_D S_D when S is the same at every release).
  With lambda_gas = 0 no deploy gas is read (FFLONK has deploy gas for a few cells only).
Recommendation: the supported, feasible design with the lowest predicted lifecycle cost; ties go to the declared order.
"""
import math

BACKENDS = ("groth16", "rapidsnark", "plonk", "fflonk")
# Declared design order (tie-break) and the statements each design supports (Table 2 of the paper).
DESIGNS = ("A0-tight", "A0-pad-TR", "A0-pad-SS", "PX", "MR32", "A1")
SUPPORTS = {"A0-tight": {"S1", "S2", "S3"}, "A0-pad-TR": {"S1", "S2", "S3"}, "A0-pad-SS": {"S1", "S2", "S3"},
            "PX": {"S2", "S3"}, "MR32": {"S2", "S3"}, "A1": {"S1"}}


def count(z, backend):
    """Exact count n_b of one cell (z = its SIZES.tsv row) for backend b."""
    if backend in ("groth16", "rapidsnark"):
        return int(z["nConstraints"])
    if backend in ("plonk", "fflonk"):
        p = int(z["plonkPower"] if backend == "plonk" else z["fflonkPower"])
        return p * 2 ** p                                    # p 2^p, 2^p the evaluation domain
    raise ValueError(f"unknown backend {backend!r}")


def feasible(z, backend, ptau_power):
    """True iff snarkjs 0.7.6 can set up cell z (its SIZES.tsv row) on backend b with a ptau of power ptau_power."""
    if backend in ("groth16", "rapidsnark"):
        return int(z["groth16Power"]) <= ptau_power
    if backend == "plonk":
        return int(z["plonkPower"]) <= ptau_power
    if backend == "fflonk":
        return 9 * 2 ** int(z["fflonkPower"]) + 18 <= 2 ** (ptau_power + 1) - 1
    raise ValueError(f"unknown backend {backend!r}")


def calibrate(pairs):
    """One scale constant from (measured value, count) pairs of one backend's calibration run: Alg. 2 line 1
    (per-proof medians, alpha_b) and line 2 (setup medians, beta_b)."""
    if not pairs:
        raise ValueError("calibration needs at least one block-C cell")
    if any(m <= 0 or n <= 0 for m, n in pairs):
        raise ValueError("calibration values and counts must be positive")
    return math.exp(sum(math.log(m) - math.log(n) for m, n in pairs) / len(pairs))


def supports(design, statement):
    return statement in SUPPORTS[design]


def path_cost(path, V, c_of, s_of):
    """Lifecycle cost of one design path: V * mean_v c(D(v)) + sum over its regeneration cells of S(cell)."""
    cells, regen = path["cells"], path["regen"]
    c_bar = sum(c_of(x) for x in cells) / len(cells)                     # Alg. 2 line 4
    s_tot = sum(s_of(x) for x in regen)                                  # Alg. 2 line 5
    return V * c_bar + s_tot                                             # Alg. 2 line 6


def recommend(paths, V, statement, n, alpha, beta, gas, lam_gas=0.0, lam_gov=0.0, ok=None):
    """Planner decision for one history, backend and volume V.

    paths     : {design: {"cells": [cell of each version], "regen": [post-release cell of each regeneration]}}
    n         : {cell: exact count n_b}; alpha, beta: calibrated constants; gas: {cell: deploy gas} (read only when
                lam_gas > 0); ok: {cell: feasible on b} (None: every cell feasible)
    Returns (design, {design: predicted lifecycle cost}). Unsupported or infeasible designs are never returned.
    """
    pred = {}
    for D in DESIGNS:                                                     # Alg. 2 line 3
        if D not in paths or not supports(D, statement):                   # Alg. 2 line 3 (supports s)
            continue
        if ok is not None and not all(ok[x] for x in paths[D]["cells"]):   # Alg. 2 line 3 (every D(v_i) feasible on b)
            continue
        c_hat = lambda x: alpha * n[x]                                     # Alg. 2 line 4 (alpha_b n_b)
        s_hat = lambda x: beta * n[x] + (lam_gas * gas[x] if lam_gas else 0.0) + lam_gov   # Alg. 2 line 5
        pred[D] = path_cost(paths[D], V, c_hat, s_hat)                     # Alg. 2 lines 4-6
    if not pred:
        raise ValueError(f"no feasible design supports statement {statement!r}")
    best = min(pred, key=lambda D: (pred[D], DESIGNS.index(D)))          # Alg. 2 line 7 (ties: declared order)
    return best, pred                                                    # Alg. 2 line 7
