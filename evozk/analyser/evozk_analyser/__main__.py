"""Command line.

  python -m evozk_analyser pair OLD.json NEW.json --policy P.json [--renames R.json] [--state S.json] [--B 1]
                                [--no-hints] [--h 32] [-o OUT.json]
  python -m evozk_analyser history V1.json V2.json ... --policy P.json [--renames R.json] [--B 1] [--no-hints]
                                [--h 32] [--name NAME] [-o OUT.json] [--tsv OUT.tsv]

Policy, renames and state formats: see evozk_analyser.policy and the package docstring. For history,
--renames is {"<from>-><to>": {old path: new path}}.
"""
import argparse
import sys

from .analyse import analyse_history, analyse_pair
from .errors import AnalyserError
from .inventory import load_inventory
from .io import dumps, load_json, write_tsv
from .policy import load_history_policy, load_pair_policy


def _out(text, path):
    if path:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="evozk_analyser")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pair")
    p.add_argument("old")
    p.add_argument("new")
    h = sub.add_parser("history")
    h.add_argument("versions", nargs="+")
    h.add_argument("--name", default="history")
    h.add_argument("--tsv")
    for x in (p, h):
        x.add_argument("--policy", required=True)
        x.add_argument("--renames")
        x.add_argument("--B", type=int, default=1)
        x.add_argument("--no-hints", action="store_true", help="ignore maps_to_<version> rename hints")
        x.add_argument("--choice", choices=("nested", "outermost"), default="nested")
        x.add_argument("--h", type=int, default=32, help="depth h of MR (Algorithm 1 l.17), default 32")
        x.add_argument("-o", "--output")
    p.add_argument("--state")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "pair":
            old, new = load_inventory(load_json(a.old)), load_inventory(load_json(a.new))
            pol = load_pair_policy(load_json(a.policy))
            ren = load_json(a.renames) if a.renames else None
            st = load_json(a.state) if a.state else None
            res = analyse_pair(old, new, pol, ren, a.B, st, not a.no_hints, a.choice, a.h)
            _out(dumps(res), a.output)
        else:
            invs = [load_inventory(load_json(v)) for v in a.versions]
            pols = load_history_policy(load_json(a.policy), [i.version for i in invs])
            ren = None
            if a.renames:
                rmap = load_json(a.renames)
                ren = [rmap.get(f"{x.version}->{y.version}") for x, y in zip(invs, invs[1:])]
            res = analyse_history(invs, pols, ren, a.B, not a.no_hints, a.choice, a.h)
            _out(dumps(res), a.output)
            if a.tsv:
                write_tsv(a.tsv, [(a.name, res)])
    except AnalyserError as e:
        sys.stderr.write(f"evozk_analyser: error: {e}\n")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
