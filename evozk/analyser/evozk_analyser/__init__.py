"""EvoZK impact analyser (Section 5.1 and Algorithm 1 of the paper).

Input: two path inventories of a standard's record type (every leaf path with its type, array bounds and value
constraints) and the statement policy P (the path of every statement field in each version). Output: Delta-sigma, the
path differences, W6 / W6x and the change classes W0-W6x, and for every design (A0-tight, A0-pad under both capacity
policies, PX, MR, A1) whether the circuit, keys and verifier contract must be regenerated, plus the adapter-mapping lines
the release changes.

Line numbers refer to Algorithm 1 as typeset in the paper (l.1 ... l.21). Rule -> Algorithm 1 line -> code:

R1  sigma_D(v) = sum over counted leaves of prod(bounds), unbounded = B (B=1 primary, B=4 sensitivity); a choice group
    counts its widest alternative, nested groups recursively (ties: first alternative in sorted order).
    -> l.1                                                            inventory.sigma
R2  Leaves are matched across versions by their path with every "[]" removed (adapter lines, path kinds). Renames are
    known only when declared: rename map, inventory hints ("maps_to_<version>"), or a statement-policy field whose
    paths differ.                                                     diff.diff
R3  Path change kinds: added, removed, renamed, retyped, arrayness, bounds, pattern, format, codelist-change,
    codelist-extension; informative only: constraint-other, required.   diff.compare
R4  Statement fields: for each field f of P defined in v or in v' (l.3), p = pi_v(f), p' = pi_v'(f) resolved to leaves
    (l.4); a field undefined in both versions is skipped:
    W6 if p or p' is undefined (added, removed; e unchanged)                                 -> l.5-6
    else (l.7): W6 if the path strings differ (renamed)                                      -> l.8-9
          and, independently, W6 and e = true if type, bounds, pattern or format differ, or codes(p) is not a subset
          of codes(p'), codes(p) = all values when p has no code list (encoding or format)  -> l.10-11
          else W6x if f is not in W6 and codes(p) is a proper subset of codes(p')            -> l.12-13
    A renamed field whose encoding also changes is W6 and sets e; a change of array-ness that alters the path string is
    a rename and a bounds change. Carrier constraints never give W6, W6x or e.
R5  Labels (Appendix A, not part of Algorithm 1): W0: delta 0 and W6 empty (strict: and W6x empty); W1: delta > 0 and
    sigma' <= K; W2: sigma' > K, first exhaustion; W3: a further one; W4: history level, sigma rises, falls and rises;
    W5: (delta != 0 and the number of listed leaf paths unchanged) or a leaf changes array-ness; shrink: delta < 0.
R6  Regeneration set R (l.14 R <- {}):
    A0-tight iff delta != 0 or e (carrier encodings do not count)                            -> l.15
    A0-pad, per capacity policy: iff sigma' > K, then K <- sigma' (tight-refit) or the smallest ladder rung >= sigma',
    or sigma' if no rung covers it (structural-step)                                         -> l.16-17
    else iff e (K unchanged)                                                                 -> l.18
    PX iff W6 != {} (strict sensitivity: W6 or W6x)                                          -> l.19
    MR iff sigma' > 2^h, h = 32 by default (MRdepth)                                         -> l.20
    A1 never.                                       A regeneration = circuit, keys, verifier. -> l.21 returns
R7  Ladder L = (16, 31, 64, 128, 256, 512, 1024, 2048, 4096); initial K = smallest rung >= sigma of the first version,
    or sigma beyond 4096 (as l.17); flagged beyond_ladder.
R8  Adapter: one mapping line per listed leaf holding (path, type, bounds, enum, pattern, format, target); target is
    statement:<field> or carrier for PX and a single constant for the other designs. A line changes when any of
    these differ; added/removed leaves and declared renames count once.
"""
__version__ = "1.1.1"

from .errors import AnalyserError, InventoryError, PolicyError, StateError  # noqa: F401
from .inventory import Inventory, Leaf, load_inventory, norm_key, sigma  # noqa: F401
from .ladder import LADDER, beyond_ladder, ladder_ceil, ladder_min, next_K  # noqa: F401
from .policy import Field, PairPolicy, load_pair_policy, load_history_policy  # noqa: F401
from .diff import diff, KINDS, LINE_KINDS, W6_KINDS, W6X_KINDS  # noqa: F401
from .analyse import analyse_pair, analyse_history, CONFIGS, MR_DEPTH, POLICIES, READINGS, LABEL_ORDER  # noqa: F401
