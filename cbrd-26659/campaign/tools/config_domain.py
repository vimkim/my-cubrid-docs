#!/usr/bin/env python3
"""The campaign's configuration domain, re-verified against the pinned engine (ticket 17).

    config_domain.py check  --results DIR
    config_domain.py table  --results DIR [--format md|json]

The spec's "Execution tiers, configurations and budgets" requires that scheduled and extended
invocations cover 4, 8 and 16 KiB pages, unmodified release and debug builds and standalone and
client-server where applicable, and the "Engine baseline" section adds that a build directory's
presence is not proof of a matching binary. Ticket 17 criterion 2 therefore asks for each of the
twelve combinations to be **either proven runnable with a matching binary or recorded as a
Capability gap**.

This module owns what "proven" means, so that the probe cannot decide it about itself:

  * the cell names the engine commit it ran and the sha256 of the four binaries that ran it;
  * the database really was created at the declared page size, read back from the engine;
  * the workload reached the OOS path (SHOW HEAP OOS reports a file and at least one record) --
    a cell that ran SQL without ever leaving the row proves nothing about OOS at that page size;
  * the value read back byte-identical.

A cell that cannot be run is a Capability gap and must name its reason; it then carries no OOS
evidence, because there is none to carry.

`problems()` returns one line per defect and is what `selftest_config_domain.py` plants defects
against. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PAGE_SIZES = (4096, 8192, 16384)
BUILDS = ("release", "debug")
RUN_MODES = ("standalone", "client-server")
MODE_TAG = {"standalone": "sa", "client-server": "cs"}
ENGINE_COMMIT = "f4299ac0cd777a2a964c1f197ae5ebf9841a4936"
REQUIRED_BINARIES = ("libcubrid.so", "libcubridsa.so", "csql", "cub_server")


def cell_id(page_size: int, build: str, run_mode: str) -> str:
    return f"{page_size}-{build}-{MODE_TAG[run_mode]}"


def expected_cells():
    return [cell_id(p, b, m) for p in PAGE_SIZES for b in BUILDS for m in RUN_MODES]


def load_cells(results_dir) -> dict:
    cells = {}
    for path in sorted(Path(results_dir).glob("*.json")):
        data = json.loads(path.read_text())
        cells[data.get("cell", path.stem)] = data
    return cells


def problems(cells: dict) -> list:
    out = []
    for want in expected_cells():
        cell = cells.get(want)
        if cell is None:
            out.append(f"{want}: no probe result -- the cell is neither proven runnable nor recorded as a Capability gap")
            continue
        verdict = cell.get("verdict")
        if verdict not in ("runnable", "capability-gap"):
            out.append(f"{want}: verdict {verdict!r} is neither 'runnable' nor 'capability-gap'")
            continue
        if verdict == "capability-gap":
            if not cell.get("reason"):
                out.append(f"{want}: recorded as a Capability gap with no reason; a gap that does not say why it is a gap is not a record")
            continue
        if cell.get("engine_commit") != ENGINE_COMMIT:
            out.append(f"{want}: engine commit {cell.get('engine_commit')!r} is not the pinned commit {ENGINE_COMMIT}")
        missing = [b for b in REQUIRED_BINARIES if not cell.get("binaries", {}).get(b)]
        if missing:
            out.append(f"{want}: does not name the binaries that ran it ({', '.join(missing)} absent); a build directory is not proof of a matching binary")
        if cell.get("page_size_readback") != cell.get("page_size"):
            out.append(f"{want}: the database's page size reads back as {cell.get('page_size_readback')!r}, not the declared {cell.get('page_size')}")
        ev = cell.get("oos_evidence") or {}
        if not (ev.get("has_oos_file") == 1 and (ev.get("oos_num_recs") or 0) >= 1):
            out.append(f"{want}: runnable, but the workload produced no OOS-path evidence (has_oos_file={ev.get('has_oos_file')!r}, oos_num_recs={ev.get('oos_num_recs')!r}); running SQL at a page size proves nothing about OOS at that page size")
        if cell.get("value_roundtrip") != "byte-identical":
            out.append(f"{want}: the value roundtrip reads {cell.get('value_roundtrip')!r}, not byte-identical")
    for extra in sorted(set(cells) - set(expected_cells())):
        out.append(f"{extra}: not a cell of the configuration domain")
    return out


def table_markdown(cells: dict) -> str:
    lines = [
        "| Page size | Build | Run mode | Verdict | Engine | OOS-path evidence | Value | Wall |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    for page in PAGE_SIZES:
        for build in BUILDS:
            for mode in RUN_MODES:
                cid = cell_id(page, build, mode)
                c = cells.get(cid)
                if c is None:
                    lines.append(f"| {page // 1024} KiB | {build} | {mode} | **absent** | — | — | — | — |")
                    continue
                if c.get("verdict") == "capability-gap":
                    lines.append(f"| {page // 1024} KiB | {build} | {mode} | **Capability gap** | — | — | — | — |")
                    continue
                ev = c.get("oos_evidence") or {}
                lines.append(
                    f"| {page // 1024} KiB | {build} | {mode} | runnable | `{(c.get('binaries') or {}).get('libcubrid.so', '')[:8]}…` | "
                    f"`Has_oos_file` {ev.get('has_oos_file')}, `Oos_num_recs` {ev.get('oos_num_recs')}, `Oos_recs_sumlen` {ev.get('oos_recs_sumlen')} | "
                    f"{c.get('value_roundtrip')} | {c.get('wall_seconds')} s |"
                )
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "table"):
        p = sub.add_parser(name)
        p.add_argument("--results", required=True)
        if name == "table":
            p.add_argument("--format", choices=("md", "json"), default="md")
    args = ap.parse_args(argv)
    cells = load_cells(args.results)
    if args.cmd == "check":
        probs = problems(cells)
        for p in probs:
            print("PROBLEM: " + p)
        print(f"[config_domain] {len(cells)} cell(s) read, {len(expected_cells())} expected, {len(probs)} problem(s)")
        return 1 if probs else 0
    if args.format == "json":
        print(json.dumps({c: cells.get(c) for c in expected_cells()}, indent=2, sort_keys=True))
    else:
        print(table_markdown(cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())
