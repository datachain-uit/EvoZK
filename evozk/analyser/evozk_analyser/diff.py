"""Path differences between two inventories (added, removed, retyped, changed in array-ness; plus the renames, bound
changes and value-constraint changes that W6 and the adapter need)."""
import json
from dataclasses import dataclass

from .errors import PolicyError

KINDS = ("added", "removed", "renamed", "retyped", "arrayness", "bounds", "pattern", "format",
         "codelist-change", "codelist-extension", "constraint-other", "required")
# kinds that change an adapter-mapping line (R8) -- every inventory attribute
LINE_KINDS = frozenset(KINDS[:10])
# kinds that make a statement-field change W6 (R4); W6X_KINDS alone gives W6x
W6_KINDS = frozenset(("added", "removed", "renamed", "retyped", "arrayness", "bounds", "pattern", "format",
                      "codelist-change"))
W6X_KINDS = frozenset(("codelist-extension",))
CONSTRAINT_KEYS = ("enum", "pattern", "format")


def ordered(kinds):
    return [k for k in KINDS if k in kinds]


@dataclass
class Pair:
    old: object  # Leaf or None
    new: object
    kinds: list
    detail: dict

    @property
    def key(self):
        if self.old is None:
            return self.new.path
        if self.new is None:
            return self.old.path
        if self.old.path == self.new.path:
            return self.old.path
        return f"{self.old.path}->{self.new.path}"


def _enum_set(v):
    return {json.dumps(x, sort_keys=True) for x in v}


def compare(o, n, renamed):
    """Change kinds and detail for a matched pair of leaves."""
    kinds, detail = set(), {}
    if renamed:
        kinds.add("renamed")
        detail["path"] = [o.path, n.path]
    if o.type != n.type:
        kinds.add("retyped")
        detail["type"] = [o.type, n.type]
    if len(o.bounds) != len(n.bounds) or (not renamed and o.path != n.path):
        kinds.add("arrayness")
        detail["array_bounds"] = [list(o.bounds), list(n.bounds)]
        if not renamed:
            detail["path"] = [o.path, n.path]
    elif o.bounds != n.bounds:
        kinds.add("bounds")
        detail["array_bounds"] = [list(o.bounds), list(n.bounds)]
    oc, nc = o.constraints, n.constraints
    for k in ("pattern", "format"):
        if oc.get(k) != nc.get(k):
            kinds.add(k)
            detail[k] = [oc.get(k), nc.get(k)]
    oe, ne = oc.get("enum"), nc.get("enum")
    if oe is not None or ne is not None:
        if oe is None:
            kinds.add("codelist-change")
            detail["enum"] = {"introduced": len(ne)}
        elif ne is None:
            kinds.add("codelist-extension")
            detail["enum"] = {"dropped": len(oe)}
        else:
            so, sn = _enum_set(oe), _enum_set(ne)
            if so != sn:
                rem, add = sorted(so - sn), sorted(sn - so)
                kinds.add("codelist-change" if rem else "codelist-extension")
                detail["enum"] = {"removed": [json.loads(x) for x in rem], "added": [json.loads(x) for x in add]}
    other = sorted(k for k in set(oc) | set(nc) if k not in CONSTRAINT_KEYS and oc.get(k) != nc.get(k))
    if other:
        kinds.add("constraint-other")
        detail["constraint_other"] = other
    if o.required != n.required:
        kinds.add("required")
        detail["required"] = [o.required, n.required]
    return ordered(kinds), detail


def diff(old, new, renames=None):
    """All leaf pairs between two inventories: matched pairs (changed or not), removed (new None), added (old None).

    renames: {old path: new path}, declared. Returns a list of Pair sorted by key.
    """
    renames = renames or {}
    pairs, used_old, used_new = [], set(), set()
    for op in sorted(renames):
        np = renames[op]
        o, n = old.resolve(op), new.resolve(np)
        if o is None:
            raise PolicyError(f"rename source {op} is not a leaf of version {old.version}")
        if n is None:
            raise PolicyError(f"rename target {np} is not a leaf of version {new.version}")
        if o.path in used_old or n.path in used_new:
            raise PolicyError(f"rename {op} -> {np} reuses a leaf already paired")
        used_old.add(o.path)
        used_new.add(n.path)
        pairs.append((o, n, o.key != n.key))
    for key in sorted(old.by_key):
        o = old.by_key[key]
        n = new.by_key.get(key)
        if o.path in used_old or n is None or n.path in used_new:
            continue
        used_old.add(o.path)
        used_new.add(n.path)
        pairs.append((o, n, False))
    out = []
    for o, n, ren in pairs:
        kinds, detail = compare(o, n, ren)
        out.append(Pair(o, n, kinds, detail))
    for lf in old.leaves:
        if lf.path not in used_old:
            out.append(Pair(lf, None, ["removed"], {}))
    for lf in new.leaves:
        if lf.path not in used_new:
            out.append(Pair(None, lf, ["added"], {}))
    out.sort(key=lambda p: (p.key, p.old.path if p.old else "", p.new.path if p.new else ""))
    return out
