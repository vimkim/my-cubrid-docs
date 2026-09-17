#!/usr/bin/env python3
"""Checker for the configuration-domain table (campaign ticket 17).

`config_domain.py` turns one probe result per cell into the domain table criterion 2 asks
for: 4, 8 and 16 KiB pages x release and debug x standalone and client-server, each cell
either proven runnable with a matching binary or recorded as a Capability gap. This selftest
plants the defects that would let an unproven cell read as proven and requires the checker to
report each one, the way selftest_matrix_completeness.py plants ticket 44's F1 back.

Standard library only. Writes nothing outside a temporary directory.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_domain  # noqa: E402

FAILS = []


def check(n, label, ok):
    print(("PASS  " if ok else "FAIL  ") + f"{n:<4}{label}")
    if not ok:
        FAILS.append(f"{n} {label}")


def good_cell(page, build, mode):
    return {
        "cell": f"{page}-{build}-{'sa' if mode == 'standalone' else 'cs'}",
        "page_size": page,
        "build": build,
        "run_mode": mode,
        "verdict": "runnable",
        "engine_commit": "f4299ac0cd777a2a964c1f197ae5ebf9841a4936",
        "cubrid_rel": f"CUBRID 11.5.0 (11.5.0.2648-f4299ac) (64bit {build} build for Linux)",
        "binaries": {
            "libcubrid.so": "1" * 64,
            "libcubridsa.so": "2" * 64,
            "csql": "3" * 64,
            "cub_server": "4" * 64,
        },
        "page_size_readback": page,
        "oos_evidence": {"has_oos_file": 1, "oos_num_recs": 2, "oos_recs_sumlen": 8032},
        "value_roundtrip": "byte-identical",
        "wall_seconds": 6.5,
        "reason": None,
    }


def full_domain():
    cells = []
    for page in config_domain.PAGE_SIZES:
        for build in config_domain.BUILDS:
            for mode in config_domain.RUN_MODES:
                cells.append(good_cell(page, build, mode))
    return cells


def problems_for(cells, tmp):
    d = Path(tempfile.mkdtemp(dir=tmp))
    for c in cells:
        (d / f"{c['cell']}.json").write_text(json.dumps(c))
    return config_domain.problems(config_domain.load_cells(d))


def main():
    with tempfile.TemporaryDirectory(prefix="selftest-config-domain-") as tmp:
        base = full_domain()

        check(1, "a complete domain of twelve proven cells reports no problem",
              problems_for(base, tmp) == [])

        missing = [c for c in base if c["cell"] != "4096-debug-sa"]
        probs = problems_for(missing, tmp)
        check(2, "a missing cell is reported by name",
              len(probs) == 1 and "4096-debug-sa" in probs[0] and "no probe result" in probs[0])

        no_oos = copy.deepcopy(base)
        for c in no_oos:
            if c["cell"] == "8192-release-cs":
                c["oos_evidence"] = {"has_oos_file": 0, "oos_num_recs": 0, "oos_recs_sumlen": 0}
        probs = problems_for(no_oos, tmp)
        check(3, "a 'runnable' cell whose workload never reached the OOS path is reported",
              len(probs) == 1 and "8192-release-cs" in probs[0] and "OOS" in probs[0])

        wrong_page = copy.deepcopy(base)
        for c in wrong_page:
            if c["cell"] == "4096-release-cs":
                c["page_size_readback"] = 16384
        probs = problems_for(wrong_page, tmp)
        check(4, "a cell whose database was not created at the declared page size is reported",
              len(probs) == 1 and "4096-release-cs" in probs[0] and "page size" in probs[0])

        no_hash = copy.deepcopy(base)
        for c in no_hash:
            if c["cell"] == "16384-debug-sa":
                c["binaries"] = {"libcubrid.so": "1" * 64}
        probs = problems_for(no_hash, tmp)
        check(5, "a cell that does not name the binary that ran it is reported",
              len(probs) == 1 and "16384-debug-sa" in probs[0] and "binar" in probs[0])

        wrong_commit = copy.deepcopy(base)
        for c in wrong_commit:
            if c["cell"] == "8192-debug-sa":
                c["engine_commit"] = "0" * 40
        probs = problems_for(wrong_commit, tmp)
        check(6, "a cell measured against another engine commit is reported",
              len(probs) == 1 and "8192-debug-sa" in probs[0] and "commit" in probs[0])

        gap_no_reason = copy.deepcopy(base)
        for c in gap_no_reason:
            if c["cell"] == "4096-debug-cs":
                c["verdict"] = "capability-gap"
                c["reason"] = None
        probs = problems_for(gap_no_reason, tmp)
        check(7, "a Capability gap with no recorded reason is reported",
              len(probs) == 1 and "4096-debug-cs" in probs[0] and "reason" in probs[0])

        gap_ok = copy.deepcopy(base)
        for c in gap_ok:
            if c["cell"] == "4096-debug-cs":
                c["verdict"] = "capability-gap"
                c["reason"] = "createdb refuses: the log volume minimum is 20 MiB"
                c["oos_evidence"] = None
                c["page_size_readback"] = None
                c["value_roundtrip"] = None
        check(8, "a Capability gap that names its reason is accepted without OOS evidence",
              problems_for(gap_ok, tmp) == [])

        roundtrip = copy.deepcopy(base)
        for c in roundtrip:
            if c["cell"] == "16384-release-cs":
                c["value_roundtrip"] = "differs"
        probs = problems_for(roundtrip, tmp)
        check(9, "a 'runnable' cell whose value did not read back byte-identical is reported",
              len(probs) == 1 and "16384-release-cs" in probs[0] and "roundtrip" in probs[0])

    print(f"[selftest_config_domain] {len(FAILS)} failing check(s)")
    for f in FAILS:
        print("  " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
