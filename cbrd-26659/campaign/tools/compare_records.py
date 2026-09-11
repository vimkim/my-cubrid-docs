#!/usr/bin/env python3
"""Field-by-field comparison of two campaign records (ticket 15 criterion 7).

    compare_records.py HAND.json REGENERATED.json [--label TEXT] [--markdown]

Walks both JSON documents and classifies every leaf:

  identical    same value in both
  prose        differs, and the field is free text the tool cannot derive (notes, summaries,
               review notes, applicability text, cleanup evidence, skip reasons, item notes,
               producer, descriptions)
  hash         differs, and the field is a hash of a regenerated file or bundle (bundle hash
               convention, SHA256SUMS ordering, files the tool rewrote)
  timestamp    differs, and the field is a creation or generation time
  path         differs, and the field is a path (evidence homes differ by construction)
  SUBSTANTIVE  differs and is none of the above: a disagreement to explain or a finding

The classification is a heuristic on the field name; the person reading the table decides
whether a SUBSTANTIVE difference is a finding. The tool never edits either record.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROSE_KEYS = {"notes", "summary", "review_note", "reviewer", "fixture", "execution_path", "engine_configuration",
              "conditions", "evidence", "note", "skip_reason", "detail", "name", "version", "description",
              "hold_reason", "identity", "processes", "databases", "command", "what"}
HASH_KEYS = {"hash", "bundle_hash", "manifest_hash", "case_list_hash"}
TIME_KEYS = {"created_at", "generated_at", "expires_on"}
PATH_KEYS = {"path", "root_path", "reference", "attempt_record", "bundle", "case_list", "setup_log", "manifest_path",
             "expected_versus_actual", "attempt_records", "directories", "storage_root", "worktree"}


def walk(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                yield (f"{path}.{k}", "<absent>", b[k])
            elif k not in b:
                yield (f"{path}.{k}", a[k], "<absent>")
            else:
                yield from walk(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if a and b and all(isinstance(x, dict) for x in a + b):
            key = align_key(a + b)
            if key:
                ka = {str(x.get(key)): x for x in a}
                kb = {str(x.get(key)): x for x in b}
                for k in list(ka) + [k for k in kb if k not in ka]:
                    if k not in kb:
                        yield (f"{path}[{key}={k}]", ka[k], "<absent>")
                    elif k not in ka:
                        yield (f"{path}[{key}={k}]", "<absent>", kb[k])
                    else:
                        yield from walk(ka[k], kb[k], f"{path}[{key}={k}]")
                return
            for i in range(max(len(a), len(b))):
                if i >= len(a):
                    yield (f"{path}[{i}]", "<absent>", b[i])
                elif i >= len(b):
                    yield (f"{path}[{i}]", a[i], "<absent>")
                else:
                    yield from walk(a[i], b[i], f"{path}[{i}]")
        elif a and b and all(isinstance(x, list) for x in a + b):
            for i in range(max(len(a), len(b))):
                yield from walk(a[i] if i < len(a) else "<absent>", b[i] if i < len(b) else "<absent>", f"{path}[{i}]")
        else:
            yield (path, a, b)


def align_key(items):
    """Rows, cases, attempts, history entries and services are sets keyed by an identity field,
    so they are aligned by that field rather than by position."""
    for key in ("row_id", "attempt_id", "manifest_id", "identity", "kind", "case"):
        if all(isinstance(x, dict) and key in x for x in items):
            if key == "case" and all(isinstance(x["case"], dict) for x in items):
                return None  # manifest cases: align on case.name below
            return key
    if all(isinstance(x, dict) and isinstance(x.get("case"), dict) and "name" in x["case"] for x in items):
        for x in items:
            x.setdefault("_case_name", x["case"]["name"])
        return "_case_name"
    return None


def classify(path, a, b):
    if a == b:
        return "identical"
    if path.endswith("._case_name"):
        return "identical"
    key = re.sub(r"\[\d+\]$", "", path.rsplit(".", 1)[-1])
    if key in HASH_KEYS or (isinstance(a, str) and isinstance(b, str) and a.startswith("sha256:") and b.startswith("sha256:")):
        return "hash"
    if key in TIME_KEYS:
        return "timestamp"
    if key in PATH_KEYS:
        return "path"
    if key in PROSE_KEYS:
        return "prose"
    if key == "producer" or ".producer." in path:
        return "prose"
    return "SUBSTANTIVE"


def short(v, n=90):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hand")
    ap.add_argument("regenerated")
    ap.add_argument("--label", default="")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--only", choices=["SUBSTANTIVE", "differing"], help="print only these rows")
    args = ap.parse_args(argv)
    a = json.loads(Path(args.hand).read_text())
    b = json.loads(Path(args.regenerated).read_text())
    rows = [(p, classify(p, x, y), x, y) for p, x, y in walk(a, b)]
    counts = {}
    for _, c, _, _ in rows:
        counts[c] = counts.get(c, 0) + 1
    label = args.label or f"{Path(args.hand).name} vs {Path(args.regenerated).name}"
    if args.markdown:
        print(f"### {label}\n")
        print("| class | count |\n|---|---|")
        for c in ("identical", "prose", "hash", "timestamp", "path", "SUBSTANTIVE"):
            if c in counts:
                print(f"| {c} | {counts[c]} |")
        print("\n| field | class | hand-written | regenerated |\n|---|---|---|---|")
        for p, c, x, y in rows:
            if c == "identical":
                continue
            if args.only == "SUBSTANTIVE" and c != "SUBSTANTIVE":
                continue
            print(f"| `{p}` | {c} | {short(x)} | {short(y)} |")
        print()
    else:
        print(f"== {label}: " + ", ".join(f"{c}={counts.get(c, 0)}" for c in ("identical", "prose", "hash", "timestamp", "path", "SUBSTANTIVE")))
        for p, c, x, y in rows:
            if c == "identical":
                continue
            if args.only == "SUBSTANTIVE" and c != "SUBSTANTIVE":
                continue
            print(f"  [{c:11}] {p}\n      hand: {short(x, 160)}\n      regen: {short(y, 160)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
