"""Deterministic JSON and TSV output."""
import json

from .analyse import CONFIGS, LABEL_ORDER, POLICIES
from .diff import KINDS


def dumps(obj):
    return json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


TSV_COLUMNS = (["history", "from", "to", "B", "sigma_old", "sigma_new", "delta_sigma", "n_paths_old", "n_paths_new"]
               + [f"n_{k.replace('-', '_')}" for k in KINDS]
               + ["statement_changes", "W_primary_tight_refit", "W_primary_structural_step",
                  "W_strict_tight_refit", "W_strict_structural_step",
                  "K_before_tight_refit", "K_after_tight_refit", "K_before_structural_step", "K_after_structural_step"]
               + [f"regen_{c.replace(':', '_').replace('-', '_')}" for c in CONFIGS]
               + [f"regen_strict_{c.replace(':', '_').replace('-', '_')}" for c in CONFIGS]
               + ["adapter_lines_A0", "adapter_lines_PX", "adapter_lines_MR", "adapter_lines_A1",
                  "e_statement_encoding", "W6_fields", "W6x_fields", "exhausted_tight_refit", "exhausted_structural_step",
                  "beyond_ladder_structural_step"])


def tsv_rows(history_name, h):
    rows = []
    for t in h["transitions"]:
        sc = ";".join(f"{c['field']}:{c['class'] or '-'}:{'+'.join(c['kinds'])}" for c in t["statement_changes"])
        row = [history_name, t["old"]["version"], t["new"]["version"], t["B"], t["old"]["sigma"], t["new"]["sigma"],
               t["delta_sigma"], t["old"]["n_paths"], t["new"]["n_paths"]]
        row += [t["path_summary"][k] for k in KINDS]
        row.append(sc or "-")
        for r in ("primary", "strict"):
            for p in POLICIES:
                row.append(",".join(t["labels"][r][p]))
        for p in POLICIES:
            row += [t["designs"]["A0-pad"][p]["K_before"], t["designs"]["A0-pad"][p]["K_after"]]
        for r in ("primary", "strict"):
            row += [int(t["regeneration"][r][c]) for c in CONFIGS]
        a = t["designs"]
        row += [a["A0-tight"]["adapter"]["lines"], a["PX"]["adapter"]["lines"], a["MR"]["adapter"]["lines"],
                a["A1"]["adapter"]["lines"]]
        row += [int(t["e"]), ",".join(t["W6"]) or "-", ",".join(t["W6x"]) or "-",
                int(a["A0-pad"]["tight-refit"]["exhausted"]), int(a["A0-pad"]["structural-step"]["exhausted"]),
                int(a["A0-pad"]["structural-step"]["beyond_ladder"])]
        assert a["A0-tight"]["adapter"]["lines"] == a["A0-pad"]["adapter"]["lines"]
        rows.append(row)
    return rows


def write_tsv(path, named_histories):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(TSV_COLUMNS) + "\n")
        for name, h in named_histories:
            for row in tsv_rows(name, h):
                f.write("\t".join(str(x) for x in row) + "\n")


__all__ = ["dumps", "load_json", "write_tsv", "tsv_rows", "TSV_COLUMNS", "LABEL_ORDER"]
