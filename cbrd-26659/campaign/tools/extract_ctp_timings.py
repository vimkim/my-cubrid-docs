#!/usr/bin/env python3
"""Extract per-case and per-invocation times from retained CTP bundles (campaign ticket 17).

    extract_ctp_timings.py --bundles DIR [DIR ...] [--format md|json]

Ticket 17 has to place workloads in tiers against the per-case caps, which needs a per-case
time. Ticket 19's record says the SQL runner has none ("the SQL runner reports no per-case
time, only this total"), so this module goes and looks: CTP's `summary.info` carries one
`<caseresult>` per case and each carries its own `<totalTime>`. The figures below are read out
of the retained bundles of tickets 13, 14, 15, 17, 19 and 41, so the claim is checkable against
sealed evidence rather than against this ticket's own runs.

For the shell seam the per-case time is in `ctp_runtime_logs/test-shell.xml` as the JUnit
`time` attribute, which ticket 14 and ticket 15 already used.

Reads only; writes nothing. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CASE_RE = re.compile(r"<caseresult>(.*?)</caseresult>", re.S)
TIME_RE = re.compile(r"<totalTime>(\d+)</totalTime>")
FILE_RE = re.compile(r"<caseFile>(.*?)</caseFile>")
SHELL_RE = re.compile(r'<testcase[^>]*\bname="([^"]+)"[^>]*\btime="([\d.]+)"')


def read_timing(bundle: Path):
    out = {}
    for line in (bundle / "timing.txt").read_text().splitlines() if (bundle / "timing.txt").exists() else []:
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    if not out and (bundle / "summary.txt").exists():
        for line in (bundle / "summary.txt").read_text().splitlines():
            if line.startswith(("elapsed_seconds=", "ended_at=")):
                k, v = line.split("=", 1)
                out[k] = v
    return out


def read_build_mode(bundle: Path):
    """release or debug, read from the bundle rather than inferred from how long the case took.

    Ticket 14's `att-T14-0001` is a release run that took 19.3 s, longer than several debug runs, so
    splitting the case times by duration mislabels it. The bundles carry `build_mode` in summary.txt
    and identity.txt (`release_gcc`, `debug_gcc_nounit`, ...); the prefix is the mode.
    """
    for name in ("summary.txt", "identity.txt"):
        path = bundle / name
        if not path.exists():
            continue
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith("build_mode="):
                value = line.split("=", 1)[1].strip()
                return "debug" if value.startswith("debug") else "release" if value.startswith("release") else value
    return None


def sql_cases(bundle: Path):
    path = bundle / "ctp_result" / "sql" / "summary.info"
    if not path.exists():
        cands = list(bundle.rglob("summary.info"))
        path = cands[-1] if cands else None
    if path is None or not path.exists():
        return None
    text = path.read_text(errors="replace")
    cases = []
    for m in CASE_RE.finditer(text):
        blk = m.group(1)
        t, f = TIME_RE.search(blk), FILE_RE.search(blk)
        if t and f:
            cases.append({"case": Path(f.group(1)).stem, "milliseconds": int(t.group(1))})
    return cases or None


def shell_cases(bundle: Path):
    path = bundle / "ctp_runtime_logs" / "test-shell.xml"
    if not path.exists():
        return None
    return [{"case": Path(n).stem, "milliseconds": round(float(t) * 1000)}
            for n, t in SHELL_RE.findall(path.read_text(errors="replace"))] or None


def collect(roots):
    rows = []
    for root in roots:
        for bundle in sorted(Path(root).glob("*")):
            if not bundle.is_dir():
                continue
            cases = sql_cases(bundle)
            seam = "sql"
            if cases is None:
                cases = shell_cases(bundle)
                seam = "shell"
            if cases is None:
                continue
            timing = read_timing(bundle)
            rows.append({
                "bundle": str(bundle),
                "invocation": bundle.name,
                "seam": seam,
                "build_mode": read_build_mode(bundle),
                "launcher_seconds": int(timing["elapsed_seconds"]) if "elapsed_seconds" in timing else None,
                "started_at": timing.get("started_at"),
                "ended_at": timing.get("ended_at"),
                "case_count": len(cases),
                "cases": cases,
                "case_milliseconds_total": sum(c["milliseconds"] for c in cases),
            })
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundles", nargs="+", required=True)
    ap.add_argument("--format", choices=("md", "json"), default="md")
    args = ap.parse_args(argv)
    rows = collect(args.bundles)
    if args.format == "json":
        print(json.dumps(rows, indent=2))
        return 0
    print("| Invocation | Seam | Cases | Launcher | Per-case total | Slowest case |")
    print("|---|---|---:|---:|---:|---|")
    for r in rows:
        slow = max(r["cases"], key=lambda c: c["milliseconds"])
        print(f"| `{r['invocation']}` | {r['seam']} | {r['case_count']} | "
              f"{r['launcher_seconds'] if r['launcher_seconds'] is not None else '—'} s | "
              f"{r['case_milliseconds_total']} ms | {slow['case']} {slow['milliseconds']} ms |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
