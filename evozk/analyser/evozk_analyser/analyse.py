"""Change classes and regeneration sets: Algorithm 1 of the paper ("Impact analysis of one release").

`analyse_pair` is Algorithm 1 for one release, line for line; each step is marked "Alg.1 l.<n>" with the line number of
the algorithm as typeset in the paper (l.1 = the sigma line ... l.21 = return). The W0-W5 labels and the
adapter-mapping lines are additional outputs of the analyser (Section 5.1 and Appendix A of the paper); they do not
enter the regeneration set.
"""
import json

from . import __version__
from .diff import KINDS, LINE_KINDS, diff, ordered
from .errors import PolicyError, StateError
from .inventory import sigma
from .ladder import POLICIES, beyond_ladder, ladder_min, next_K

DESIGNS = ("A0-tight", "A0-pad", "PX", "MR", "A1")
CONFIGS = ("A0-tight", "A0-pad:tight-refit", "A0-pad:structural-step", "PX", "MR", "A1")
READINGS = ("primary", "strict")
LABEL_ORDER = ("W0", "W1", "W2", "W3", "W4", "W5", "W6", "W6x", "shrink")
ARTEFACTS = ["circuit", "keys", "verifier"]
MR_DEPTH = 32   # h of MR: macros/design.tex \MRdepth (viable MR depth); Algorithm 1 input h


def _labels(s):
    return [x for x in LABEL_ORDER if x in s]


def _hint_renames(old, new):
    """Renames declared by the inventory itself: maps_to_<new version with '.' as '_'> on an old leaf."""
    key = "maps_to_" + new.version.replace(".", "_")
    out = {}
    for lf in old.leaves:
        h = lf.hints.get(key)
        if h is None:
            continue
        tgt = h.get("path") if isinstance(h, dict) else h
        if not isinstance(tgt, str):
            raise PolicyError(f"{lf.path}: bad {key} hint")
        if tgt != lf.path:
            out[lf.path] = tgt
    return out


def _merge(a, b, what):
    out = dict(a)
    for k, v in b.items():
        if k in out and out[k] != v:
            raise PolicyError(f"conflicting renames for {k}: {out[k]} ({what}) vs {v}")
        out[k] = v
    return out


def _default_state(s_old):
    k = ladder_min(s_old)
    return {"K": {p: k for p in POLICIES}, "exhaustions": {p: 0 for p in POLICIES}}


def _check_state(state, s_old):
    try:
        K = {p: state["K"][p] for p in POLICIES}
        E = {p: state["exhaustions"][p] for p in POLICIES}
    except (KeyError, TypeError):
        raise StateError("state needs K and exhaustions for tight-refit and structural-step") from None
    for p in POLICIES:
        if not isinstance(K[p], int) or isinstance(K[p], bool) or K[p] < s_old:
            raise StateError(f"{p}: K={K[p]!r} is below sigma of the old version ({s_old})")
        if not isinstance(E[p], int) or isinstance(E[p], bool) or E[p] < 0:
            raise StateError(f"{p}: bad exhaustion count {E[p]!r}")
    return {"K": K, "exhaustions": E}


def _codes(leaf):
    """codes(p): the code list of p as a set, or None standing for 'all values' when p has no code list."""
    e = leaf.constraints.get("enum")
    return None if e is None else {json.dumps(x, sort_keys=True) for x in e}


def _subset(a, b):
    """codes(p) subseteq codes(p'), with None = all values."""
    if b is None:
        return True
    if a is None:
        return False
    return a <= b


def _proper_subset(a, b):
    """codes(p) subsetneq codes(p')."""
    if b is None:
        return a is not None
    return a is not None and a < b


def _encoding_change(o, n):
    """Alg.1 l.10 condition (p and p' both defined): which of type, bounds, pattern, format differ, and whether codes(p) is not a
    subset of codes(p'). Returns the list of reasons (empty: no encoding or format change)."""
    why = []
    if o.type != n.type:
        why.append("type")
    if o.bounds != n.bounds:
        why.append("bounds")
    for k in ("pattern", "format"):
        if o.constraints.get(k) != n.constraints.get(k):
            why.append(k)
    if not _subset(_codes(o), _codes(n)):
        why.append("codes")
    return why


def analyse_pair(old, new, policy, renames=None, B=1, state=None, use_hints=True, choice="nested", h=MR_DEPTH):
    """Algorithm 1 for one release (adjacent pair v -> v'). Returns a JSON-ready dict (deterministic).

    state: A0-pad capacity K and exhaustion count per capacity policy before the release (default: K = smallest rung
    covering sigma(v), no earlier exhaustion). h: depth of MR (default 32)."""
    if not isinstance(h, int) or isinstance(h, bool) or h < 1:
        raise StateError(f"MR depth h must be a positive integer, got {h!r}")
    # Alg.1 l.1: sigma <- sigma_D(v); sigma' <- sigma_D(v'); delta <- sigma' - sigma
    s_old, counted_old, chosen_old = sigma(old, B, choice)
    s_new, counted_new, chosen_new = sigma(new, B, choice)
    d = s_new - s_old
    state = _default_state(s_old) if state is None else _check_state(state, s_old)

    # statement fields: p = pi_v(f), p' = pi_v'(f), resolved to leaves of the two inventories (Alg.1 l.4, done up front
    # because the diff below needs the declared renames)
    st_old, st_new, fields = {}, {}, []
    stmt_renames = {}
    for f in policy.fields:
        o = old.resolve(f.old) if f.old is not None else None
        n = new.resolve(f.new) if f.new is not None else None
        if f.old is not None and o is None:
            raise PolicyError(f"statement field {f.name}: {f.old} is not a leaf of version {old.version}")
        if f.new is not None and n is None:
            raise PolicyError(f"statement field {f.name}: {f.new} is not a leaf of version {new.version}")
        if o is not None:
            st_old[o.path] = f.name
        if n is not None:
            st_new[n.path] = f.name
        if o is not None and n is not None and o.path != n.path:
            stmt_renames[o.path] = n.path
        fields.append((f, o, n))
    ren = renames or {}
    if use_hints:
        ren = _merge(_hint_renames(old, new), ren, "inventory hint")
    ren = _merge(ren, stmt_renames, "statement policy")
    pairs = diff(old, new, ren)

    by_old = {p.old.path: p for p in pairs if p.old is not None}
    changes = []
    for p in pairs:
        if not p.kinds:
            continue
        role = "statement" if ((p.old is not None and p.old.path in st_old) or
                               (p.new is not None and p.new.path in st_new)) else "carrier"
        changes.append({"key": p.key, "old": p.old.path if p.old else None, "new": p.new.path if p.new else None,
                        "role": role, "kinds": p.kinds, "detail": p.detail})
    summary = {k: sum(1 for c in changes if k in c["kinds"]) for k in KINDS}

    # Alg.1 l.2: W6 <- {}; W6x <- {}; e <- false
    W6, W6x, e = [], [], False
    st_changes, enc_fields = [], []
    for f, o, n in fields:                                            # Alg.1 l.3: foreach statement field f of P
        if o is None and n is None:                                   #   defined in v or in v' (a field undefined in
            continue                                                  #   both versions is skipped)
        if o is not None and n is not None:                           # Alg.1 l.4: p <- pi_v(f); p' <- pi_v'(f)
            p = by_old.get(o.path)
            if p is None or p.new is None or p.new.path != n.path:
                raise PolicyError(f"statement field {f.name}: {o.path} and {n.path} are not paired by the diff")
            kinds = list(p.kinds)
        else:
            kinds = ["added"] if o is None else ["removed"]
        lines, cls, why = [], None, []
        if o is None or n is None:                                    # Alg.1 l.5: p or p' undefined
            lines.append(5)
            W6.append(f.name)                                         # Alg.1 l.6: W6 <- W6 + {f} (added or removed)
        else:                                                         # Alg.1 l.7: else (both defined)
            if o.path != n.path:                                      # Alg.1 l.8: p != p' (path strings)
                lines.append(8)
                W6.append(f.name)                                     # Alg.1 l.9: W6 <- W6 + {f} (renamed)
            why = _encoding_change(o, n)
            if why:                                                   # Alg.1 l.10: type/bounds/pattern/format differ,
                lines.append(10)                                      #   or codes(p) not subseteq codes(p')
                if f.name not in W6:
                    W6.append(f.name)
                e = True                                              # Alg.1 l.11: W6 <- W6 + {f}; e <- true
                enc_fields.append((f.name, why))
            elif f.name not in W6 and _proper_subset(_codes(o), _codes(n)):   # Alg.1 l.12: f not in W6 and
                lines.append(12)                                      #   codes(p) subsetneq codes(p')
                W6x.append(f.name)                                    # Alg.1 l.13: W6x <- W6x + {f}
        cls = "W6" if f.name in W6 else ("W6x" if f.name in W6x else None)
        if not kinds and cls is None:
            continue
        st_changes.append({"field": f.name, "old": o.path if o else None, "new": n.path if n else None,
                           "kinds": ordered(set(kinds)), "class": cls, "alg1_lines": lines,
                           "encoding_change": why})
    has_w6, has_w6x = bool(W6), bool(W6x)
    arrayness = any("arrayness" in c["kinds"] for c in changes)
    same_count = len(old) == len(new)

    # Alg.1 l.14: R <- {} (the regeneration set is assembled below, per reading)
    # Alg.1 l.16-18: A0-pad per capacity policy (K threaded by the caller; independent of the reading)
    pad = {}
    for pol in POLICIES:
        K = state["K"][pol]
        ex = s_new > K                                                # Alg.1 l.16: if sigma' > K
        Ka = next_K(pol, K, s_new)                                    # Alg.1 l.17: K <- sigma' (tight-refit), min{l >= sigma'} or sigma'
        pad[pol] = {"K_before": K, "K_after": Ka, "exhausted": ex,
                    "beyond_ladder": bool(ex and pol == "structural-step" and beyond_ladder(s_new)),
                    "regen": ex or e,                                 # Alg.1 l.17 (exhaustion) / l.18 (else if e)
                    "exhaustions_before": state["exhaustions"][pol]}
    state_after = {"K": {p: pad[p]["K_after"] for p in POLICIES},
                   "exhaustions": {p: state["exhaustions"][p] + (1 if pad[p]["exhausted"] else 0) for p in POLICIES}}
    mr = s_new > 2 ** h                                               # Alg.1 l.20: if sigma' > 2^h -> MR

    labels, regen, design_r = {}, {}, {}
    for r in READINGS:
        # strict reading (sensitivity, not part of Algorithm 1): W6x counted as W6 -- PX and the W0/W6 labels only
        stmt_change = has_w6 or (r == "strict" and has_w6x)
        labels[r] = {}
        for pol in POLICIES:
            s = set()
            if d == 0 and not stmt_change:
                s.add("W0")
            if d > 0 and not pad[pol]["exhausted"]:
                s.add("W1")
            if pad[pol]["exhausted"]:
                s.add("W2" if pad[pol]["exhaustions_before"] == 0 else "W3")
            if (d != 0 and same_count) or arrayness:
                s.add("W5")
            if stmt_change:
                s.add("W6")
            if r == "primary" and has_w6x:
                s.add("W6x")
            if d < 0:
                s.add("shrink")
            labels[r][pol] = _labels(s)
        reasons = {"A0-tight": [], "PX": [], "MR": [], "A1": []}
        if d != 0:                                                    # Alg.1 l.15: delta != 0 or e -> A0-tight
            reasons["A0-tight"].append(f"delta_sigma={d}")
        for name, why in enc_fields:
            reasons["A0-tight"].append(f"statement field {name}: encoding/format change ({','.join(why)})")
        for c in st_changes:                                          # Alg.1 l.19: W6 != {} -> PX (strict: or W6x)
            if c["class"] == "W6" or (r == "strict" and c["class"] == "W6x"):
                reasons["PX"].append(f"{c['class']} on statement field {c['field']}: {','.join(c['kinds']) or 'path'}")
        if mr:
            reasons["MR"].append(f"sigma_new={s_new} > 2^{h}")
        # A1: never (Algorithm 1 never adds it to R)
        rg = {"A0-tight": bool(reasons["A0-tight"]), "PX": bool(reasons["PX"]), "MR": mr, "A1": False}
        for pol in POLICIES:
            rg[f"A0-pad:{pol}"] = pad[pol]["regen"]
        regen[r] = {c: rg[c] for c in CONFIGS}
        dr = {}
        for dsg in ("A0-tight", "PX", "MR", "A1"):
            dr[dsg] = {"regenerate": rg[dsg], "artefacts": ARTEFACTS[:] if rg[dsg] else [], "reasons": reasons[dsg]}
        dr["A0-pad"] = {}
        for pol in POLICIES:
            x = pad[pol]
            why = []
            if x["exhausted"]:
                why.append(f"sigma_new={s_new} > K={x['K_before']}")
            elif e:
                why += [f"statement field {name}: encoding/format change ({','.join(w)})" for name, w in enc_fields]
            dr["A0-pad"][pol] = {"regenerate": x["regen"], "artefacts": ARTEFACTS[:] if x["regen"] else [],
                                 "reasons": why}
        design_r[r] = dr

    # adapter-mapping lines (R8)
    def target(design, leaf, side):
        if design != "PX":
            return design
        name = (st_old if side == "old" else st_new).get(leaf.path)
        return f"statement:{name}" if name is not None else "carrier"

    adapter = {}
    for dsg in DESIGNS:
        lines = []
        for p in pairs:
            if p.old is None or p.new is None:
                lines.append(p.key)
            elif p.old.line(target(dsg, p.old, "old")) != p.new.line(target(dsg, p.new, "new")):
                lines.append(p.key)
        adapter[dsg] = {"changed": bool(lines), "lines": len(lines), "line_keys": lines}
    # sanity: for the non-PX designs a changed line is exactly a path change of a line kind
    assert adapter["A1"]["lines"] == sum(1 for c in changes if set(c["kinds"]) & LINE_KINDS)

    def m(inv, st):
        return sum(inv.by_path[p].slots(B) for p in st)

    designs = {}
    for dsg in DESIGNS:
        ent = {"adapter": adapter[dsg]}
        if dsg == "A0-pad":
            for pol in POLICIES:
                ent[pol] = {"K_before": pad[pol]["K_before"], "K_after": pad[pol]["K_after"],
                            "exhausted": pad[pol]["exhausted"], "beyond_ladder": pad[pol]["beyond_ladder"],
                            **{r: design_r[r]["A0-pad"][pol] for r in READINGS}}
        else:
            for r in READINGS:
                ent[r] = design_r[r][dsg]
        designs[dsg] = ent
    designs["A0-tight"]["parameters"] = {"sigma": [s_old, s_new]}
    designs["PX"]["parameters"] = {"m": [m(old, st_old), m(new, st_new)]}
    designs["MR"]["parameters"] = {"h": h, "capacity": 2 ** h}

    return {                                                          # Alg.1 l.21: delta, W6, W6x, R, K
        "analyser": {"name": "evozk_analyser", "version": __version__},
        "B": B,
        "choice": choice,
        "old": {"version": old.version, "sigma": s_old, "n_paths": len(old), "n_counted_paths": len(counted_old),
                "choice_widest": chosen_old},
        "new": {"version": new.version, "sigma": s_new, "n_paths": len(new), "n_counted_paths": len(counted_new),
                "choice_widest": chosen_new},
        "delta_sigma": d,
        "W6": sorted(W6),
        "W6x": sorted(W6x),
        "e": e,
        "renames_used": dict(sorted(ren.items())),
        "path_changes": changes,
        "path_summary": summary,
        "statement_changes": st_changes,
        "labels": labels,
        "regeneration": regen,
        "designs": designs,
        "state_before": state,
        "state_after": state_after,
    }


def _w4(deltas):
    """Index of the transition that completes a rise-fall-rise of sigma, or None."""
    phase = 0
    for i, d in enumerate(deltas):
        if phase == 0 and d > 0:
            phase = 1
        elif phase == 1 and d < 0:
            phase = 2
        elif phase == 2 and d > 0:
            return i
    return None


def analyse_history(invs, policies, renames=None, B=1, use_hints=True, choice="nested", h=MR_DEPTH):
    """Replay a history v1..vn with Algorithm 1 per release: K starts at the smallest rung covering sigma(v1) and is
    threaded per capacity policy."""
    if len(invs) < 2:
        raise StateError("a history needs at least two versions")
    if len(policies) != len(invs) - 1:
        raise PolicyError("one pair policy per transition is required")
    renames = renames or [None] * (len(invs) - 1)
    s_first = sigma(invs[0], B, choice)[0]
    state = _default_state(s_first)
    trans = []
    for i in range(len(invs) - 1):
        r = analyse_pair(invs[i], invs[i + 1], policies[i], renames[i], B, state, use_hints, choice, h)
        trans.append(r)
        state = r["state_after"]
    deltas = [t["delta_sigma"] for t in trans]
    w4 = _w4(deltas)
    counts = {r: {c: sum(1 for t in trans if t["regeneration"][r][c]) for c in CONFIGS} for r in READINGS}
    label_counts = {r: {p: {lab: sum(1 for t in trans if lab in t["labels"][r][p]) for lab in LABEL_ORDER}
                        for p in POLICIES} for r in READINGS}
    exhaustions = {p: sum(1 for t in trans if t["designs"]["A0-pad"][p]["exhausted"]) for p in POLICIES}
    return {
        "analyser": {"name": "evozk_analyser", "version": __version__},
        "B": B,
        "choice": choice,
        "versions": [inv.version for inv in invs],
        "sigma": [trans[0]["old"]["sigma"]] + [t["new"]["sigma"] for t in trans],
        "K_initial": ladder_min(s_first),
        "K_initial_beyond_ladder": beyond_ladder(s_first),
        "K_trajectory": {p: [ladder_min(s_first)] + [t["state_after"]["K"][p] for t in trans] for p in POLICIES},
        "history_labels": ["W4"] if w4 is not None else [],
        "W4_completed_at": None if w4 is None else f"{trans[w4]['old']['version']}->{trans[w4]['new']['version']}",
        "regen_counts": counts,
        "A0_pad_exhaustions": exhaustions,
        "label_counts": label_counts,
        "transitions": trans,
    }
