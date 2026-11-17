#!/usr/bin/env python3
"""Lifecycle model: C_D(V), break-even V*, oracle, fixed policies, regret, bootstrap summaries.

Library only (reads no file). Every function works on plain floats and, elementwise, on numpy arrays of bootstrap
replicates (shape (B,)), so the point estimate and the replicates go through the same code.

Definitions (Section 5.2 of the paper):
  C_D(V)   = V * c_D + S_D,tot, with c_D the version-averaged per-proof cost and S_D,tot the sum of the regeneration
             costs of D over the history (= R_D * S_D when every regeneration costs the same; R_D = 0 gives S_D,tot = 0).
  V*(X, Y) = the volume above which X is cheaper than Y. For c_X < c_Y: max(0, (S_X,tot - S_Y,tot) / (c_Y - c_X)),
             which is the paper's (R_X S_X - R_Y S_Y)/(c_Y - c_X) when R_X S_X > R_Y S_Y and 0 when X is never
             dearer. For c_X >= c_Y X never overtakes Y at large V: V* = +inf, except c_X = c_Y with S_X,tot <= S_Y,tot
             (X never dearer): V* = 0.
  oracle   = the supported design with the lowest MEASURED lifecycle cost (ties: declared design order).
  regret   = C_meas(planner's choice) / C_meas(oracle) >= 1.
  agreement: the planner's choice and the oracle's are the same decision, i.e. the same design or designs whose cell
             paths and regeneration events are identical in that history (they cost the same by construction).
  fixed policy worse: C_meas(policy) > C_meas(planner's choice), strictly.
  unsupported designs: a design that cannot express the statement, or whose circuit cannot be set up on the backend
             in some version, is not a candidate of the planner, the oracle or a fixed policy. evaluate() drops the
             first kind itself; the caller passes only the feasible paths of a backend (planner.feasible), so a fixed
             policy whose design is unsupported is n/a there, never a silent zero.
"""
import math
import numpy as np

from planner import DESIGNS, supports

FIXED = (("always-A0", "A0-tight"), ("always-PX", "PX"), ("always-MR32", "MR32"))


def lifecycle(V, c_bar, s_tot):
    """C_D(V) = V c_D + S_D,tot."""
    return V * c_bar + s_tot


def break_even(c_x, s_x, c_y, s_y):
    """V* above which X is cheaper than Y (elementwise on arrays). See the module docstring."""
    c_x, s_x, c_y, s_y = (np.asarray(v, dtype=float) for v in (c_x, s_x, c_y, s_y))
    with np.errstate(divide="ignore", invalid="ignore"):
        lower = np.maximum(0.0, (s_x - s_y) / (c_y - c_x))
    out = np.where(c_x < c_y, lower, np.where((c_x == c_y) & (s_x <= s_y), 0.0, np.inf))
    return float(out) if out.ndim == 0 else out


def decision_classes(paths):
    """{design: class id}: designs with identical cell paths and regeneration cells share one decision class."""
    key, cls = {}, {}
    for D in DESIGNS:
        if D in paths:
            k = (tuple(paths[D]["cells"]), tuple(paths[D]["regen"]))
            cls[D] = key.setdefault(k, len(key))
    return cls


def choose(costs):
    """Argmin over a {design: cost} dict in declared order (first minimum wins). Arrays: per replicate."""
    names = [D for D in DESIGNS if D in costs]
    stack = np.stack([np.asarray(costs[D], dtype=float) for D in names])
    idx = np.argmin(stack, axis=0)
    return names, idx, stack


def evaluate(paths, statement, grid, cbar_meas, stot_meas, cbar_pred, stot_pred):
    """Planner vs oracle vs fixed policies on a V grid for one history and backend.

    cbar_*, stot_*: {design: float or (B,) array}. Returns arrays of shape (len(grid),) or (len(grid), B):
    agree (bool), regret, worse[policy] (bool), planner and oracle choice indices into `names`, and `names`."""
    ok = [D for D in DESIGNS if D in paths and supports(D, statement)]
    if not ok:
        raise ValueError(f"no design supports {statement!r}")
    cls = decision_classes({D: paths[D] for D in ok})
    agree, regret, pick_p, pick_o = [], [], [], []
    worse = {p: [] for p, D in FIXED if D in ok}       # a policy whose design cannot express the statement: n/a
    for V in grid:
        meas = {D: lifecycle(V, cbar_meas[D], stot_meas[D]) for D in ok}
        pred = {D: lifecycle(V, cbar_pred[D], stot_pred[D]) for D in ok}
        names, ip, _ = choose(pred)
        _, io, ms = choose(meas)
        cp = np.take_along_axis(ms, np.asarray(ip)[None, ...], axis=0)[0] if ms.ndim > 1 else ms[ip]
        co = np.take_along_axis(ms, np.asarray(io)[None, ...], axis=0)[0] if ms.ndim > 1 else ms[io]
        cid = np.array([cls[D] for D in names])
        agree.append(cid[ip] == cid[io]); regret.append(cp / co); pick_p.append(ip); pick_o.append(io)
        for p in worse:
            worse[p].append(meas[dict(FIXED)[p]] > cp)
    return dict(names=names, agree=np.array(agree), regret=np.array(regret), worse={p: np.array(v) for p, v in worse.items()},
                pick_planner=np.array(pick_p), pick_oracle=np.array(pick_o))


def summarise(results):
    """Grid summaries pooled over one or more evaluate() results (same backend). Elementwise over replicates."""
    ag = np.concatenate([r["agree"] for r in results], axis=0)
    rg = np.concatenate([r["regret"] for r in results], axis=0)
    out = dict(agree=ag.mean(axis=0), regret_median=np.median(rg, axis=0), regret_max=rg.max(axis=0))
    for p, _ in FIXED:
        if all(p in r["worse"] for r in results):
            out["worse_" + p] = np.concatenate([r["worse"][p] for r in results], axis=0).mean(axis=0)
    return out


def os_q(x, q):
    """Order statistic x_(ceil(qB)) of a replicate vector, as in the proving-campaign analysis."""
    s = np.sort(np.asarray(x, dtype=float))
    i = max(1, math.ceil(q * len(s)))
    return float(s[i - 1])


def interval(x, level=0.95):
    a = (1 - level) / 2
    return os_q(x, a), os_q(x, 1 - a)
