"""Statement policy P (Section 4.3 of the paper): the ordered list of paths on which statements may act.

A field has a name and a path in each version (null when the field is not a statement field in that version), so a
renamed statement field keeps its identity. Accepted forms:
  pair:    ["a", "b"]                                   (same path in both versions; the name is the path)
           {"fields": [{"name": n, "old": p|null, "new": p|null} | {"name": n, "path": p}]}
  history: ["a", "b"]                                   (same path in every version)
           {"fields": [{"name": n, "paths": {version: p|null}} | {"name": n, "path": p}]}
"""
from dataclasses import dataclass

from .errors import PolicyError


@dataclass(frozen=True)
class Field:
    name: str
    old: object  # str or None
    new: object


@dataclass(frozen=True)
class PairPolicy:
    fields: tuple

    def names(self):
        return [f.name for f in self.fields]


def _check(fields):
    seen = set()
    for f in fields:
        if not isinstance(f.name, str) or not f.name:
            raise PolicyError("every policy field needs a non-empty name")
        if f.name in seen:
            raise PolicyError(f"duplicate policy field {f.name}")
        seen.add(f.name)
        for p in (f.old, f.new):
            if p is not None and (not isinstance(p, str) or not p):
                raise PolicyError(f"field {f.name}: paths must be non-empty strings or null")
    for side in ("old", "new"):
        ps = [getattr(f, side) for f in fields if getattr(f, side) is not None]
        if len(ps) != len(set(ps)):
            raise PolicyError(f"two policy fields share a path in the {side} version")
    return PairPolicy(tuple(fields))


def load_pair_policy(obj):
    if isinstance(obj, list):
        return _check([Field(p, p, p) for p in obj])
    if isinstance(obj, dict) and isinstance(obj.get("fields"), list):
        out = []
        for f in obj["fields"]:
            if not isinstance(f, dict):
                raise PolicyError("policy fields must be objects")
            if "path" in f:
                out.append(Field(f.get("name", f["path"]), f["path"], f["path"]))
            else:
                if "old" not in f or "new" not in f:
                    raise PolicyError(f"field {f.get('name')}: give 'path', or both 'old' and 'new'")
                out.append(Field(f.get("name"), f["old"], f["new"]))
        return _check(out)
    raise PolicyError("a pair policy is a list of paths or {'fields': [...]}")


def load_history_policy(obj, versions):
    """One PairPolicy per adjacent pair of the given version labels."""
    versions = [str(v) for v in versions]
    if isinstance(obj, list):
        return [load_pair_policy(obj) for _ in range(len(versions) - 1)]
    if not (isinstance(obj, dict) and isinstance(obj.get("fields"), list)):
        raise PolicyError("a history policy is a list of paths or {'fields': [...]}")
    per_version = []
    for f in obj["fields"]:
        if not isinstance(f, dict) or not f.get("name"):
            raise PolicyError("history policy fields need a name")
        if "path" in f:
            per_version.append((f["name"], {v: f["path"] for v in versions}))
        elif isinstance(f.get("paths"), dict):
            unknown = set(map(str, f["paths"])) - set(versions)
            if unknown:
                raise PolicyError(f"field {f['name']}: unknown versions {sorted(unknown)}")
            per_version.append((f["name"], {v: f["paths"].get(v) for v in versions}))
        else:
            raise PolicyError(f"field {f['name']}: give 'path' or 'paths'")
    out = []
    for a, b in zip(versions, versions[1:]):
        out.append(_check([Field(n, m[a], m[b]) for n, m in per_version]))
    return out
