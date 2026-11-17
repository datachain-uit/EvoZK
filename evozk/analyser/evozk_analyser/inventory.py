"""Path inventories and slot demand sigma (Section 4.3 of the paper and its encoding rules).

Accepted format (the files under data/rq2_evolution/versions/): an object with "version" and
"paths": [{path, type, array_bounds, constraints?, required?, choices? | choice_group?/choice_alt?, maps_to_*?}].
A path writes each array level as "[]"; array_bounds has one entry (int >= 1 or null) per level.
"""
import json
from dataclasses import dataclass, field

from .errors import InventoryError

ARRAY = "[]"


def norm_key(path):
    """Matching key of a leaf: its path with every array marker removed (R2)."""
    return path.replace(ARRAY, "")


@dataclass(frozen=True)
class Leaf:
    path: str
    type: str
    bounds: tuple
    constraints: dict = field(compare=False, hash=False)
    choices: tuple = ()
    required: object = None
    hints: dict = field(default_factory=dict, compare=False, hash=False)

    @property
    def key(self):
        return norm_key(self.path)

    def slots(self, B):
        n = 1
        for b in self.bounds:
            n *= B if b is None else b
        return n

    def line(self, target):
        """The adapter-mapping line of this leaf (R8): the inventory attributes plus the design's target."""
        c = self.constraints
        return (self.path, self.type, self.bounds, _canon(c.get("enum")), c.get("pattern"), c.get("format"), target)


def _canon(v):
    """A code list as a set (order is not part of the encoding), in canonical text form."""
    return None if v is None else tuple(sorted({json.dumps(x, sort_keys=True) for x in v}))


def _leaf(obj, i):
    if not isinstance(obj, dict):
        raise InventoryError(f"paths[{i}] is not an object")
    path, typ = obj.get("path"), obj.get("type")
    if not isinstance(path, str) or not path:
        raise InventoryError(f"paths[{i}]: missing or empty 'path'")
    if not isinstance(typ, str) or not typ:
        raise InventoryError(f"paths[{i}] {path}: missing 'type'")
    bounds = obj.get("array_bounds", [])
    if not isinstance(bounds, list):
        raise InventoryError(f"{path}: array_bounds must be a list")
    if len(bounds) != path.count(ARRAY):
        raise InventoryError(f"{path}: {len(bounds)} array bounds for {path.count(ARRAY)} array levels")
    for b in bounds:
        if b is not None and (not isinstance(b, int) or isinstance(b, bool) or b < 1):
            raise InventoryError(f"{path}: bad array bound {b!r}")
    cons = obj.get("constraints")
    cons = {} if cons is None else cons
    if not isinstance(cons, dict):
        raise InventoryError(f"{path}: constraints must be an object")
    if "enum" in cons and cons["enum"] is not None and not isinstance(cons["enum"], list):
        raise InventoryError(f"{path}: constraints.enum must be a list")
    ch = obj.get("choices")
    if ch:
        try:
            choices = tuple((c["group"], c["alt"]) for c in ch)
        except (TypeError, KeyError):
            raise InventoryError(f"{path}: choices must be [{{group, alt}}, ...]") from None
    elif obj.get("choice_group"):
        choices = ((obj["choice_group"], obj.get("choice_alt")),)
    else:
        choices = ()
    for g, a in choices:
        if not isinstance(g, str) or not isinstance(a, str):
            raise InventoryError(f"{path}: choice group and alternative must be strings")
    hints = {k: v for k, v in obj.items() if k.startswith("maps_to_")}
    req = obj.get("required")
    return Leaf(path, typ, tuple(bounds), dict(cons), choices, req, hints)


class Inventory:
    def __init__(self, version, leaves, meta=None):
        self.version = version
        self.leaves = list(leaves)
        self.meta = meta or {}
        self.by_path, self.by_key = {}, {}
        for lf in self.leaves:
            if lf.path in self.by_path:
                raise InventoryError(f"version {version}: duplicate path {lf.path}")
            if lf.key in self.by_key:
                raise InventoryError(f"version {version}: paths {self.by_key[lf.key].path} and {lf.path} "
                                     "differ only in array markers")
            self.by_path[lf.path] = lf
            self.by_key[lf.key] = lf

    def __len__(self):
        return len(self.leaves)

    def resolve(self, path):
        """The leaf a policy or rename path names: exact path first, else the unique leaf with the same key."""
        if path in self.by_path:
            return self.by_path[path]
        return self.by_key.get(norm_key(path))


def load_inventory(obj, version=None):
    if not isinstance(obj, dict) or not isinstance(obj.get("paths"), list):
        raise InventoryError("an inventory must be an object with a 'paths' list")
    v = version if version is not None else obj.get("version")
    if v is None:
        raise InventoryError("inventory has no version")
    leaves = [_leaf(p, i) for i, p in enumerate(obj["paths"])]
    meta = {k: obj[k] for k in ("domain", "record_type", "status", "release_date") if k in obj}
    return Inventory(str(v), leaves, meta)


class _Node:
    __slots__ = ("leaves", "groups")

    def __init__(self):
        self.leaves, self.groups = [], {}


CHOICE_MODES = ("nested", "outermost")


def _tree(inv, choice):
    root = _Node()
    for lf in inv.leaves:
        node = root
        chain = lf.choices if choice == "nested" else lf.choices[:1]
        for g, a in chain:
            node = node.groups.setdefault(g, {}).setdefault(a, _Node())
        node.leaves.append(lf)
    return root


def _eval(node, B, chosen):
    s = sum(lf.slots(B) for lf in node.leaves)
    counted = [lf.path for lf in node.leaves]
    for g in sorted(node.groups):
        best = None
        for a in sorted(node.groups[g]):
            sub = {}
            r = _eval(node.groups[g][a], B, sub)
            if best is None or r[0] > best[1][0]:
                best = (a, r, sub)
        a, (bs, bc), sub = best
        s += bs
        counted += bc
        chosen[g] = a
        chosen.update(sub)
    return s, counted


def sigma(inv, B=1, choice="nested"):
    """(sigma, sorted counted leaf paths, {choice group: widest alternative}).

    choice="nested" (default, R1): every choice group, nested ones included, counts its widest alternative.
    choice="outermost" (declared sensitivity): only the outermost group of a leaf is resolved; all alternatives of a
    nested group inside the chosen alternative are counted (this reproduces the RQ2 dataset's derived FHIR sigma).
    """
    if not isinstance(B, int) or isinstance(B, bool) or B < 1:
        raise InventoryError(f"B must be a positive integer, got {B!r}")
    if choice not in CHOICE_MODES:
        raise InventoryError(f"choice mode must be one of {CHOICE_MODES}, got {choice!r}")
    chosen = {}
    s, counted = _eval(_tree(inv, choice), B, chosen)
    return s, sorted(counted), dict(sorted(chosen.items()))
