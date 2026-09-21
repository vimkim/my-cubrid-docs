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
from campaign_records import LIBRARY_HASHES  # noqa: E402

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
            "libcubrid.so": LIBRARY_HASHES[build]["libcubrid.so"],
            "libcubridsa.so": LIBRARY_HASHES[build]["libcubridsa.so"],
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
                c["binaries"] = {"libcubrid.so": LIBRARY_HASHES["debug"]["libcubrid.so"]}
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

        # Ticket 17's independent review, F4: the two artefact defects that escaped the checker.
        fake_hashes = copy.deepcopy(base)
        for c in fake_hashes:
            if c["cell"] == "8192-release-cs":
                c["binaries"] = {b: "dead" + "beef" * 15 for b in c["binaries"]}   # planted defect A
        probs = problems_for(fake_hashes, tmp)
        check(10, "a cell whose four binary hashes are not the pinned build's is reported by name (the review's planted defect A)",
              len(probs) == 2 and all("8192-release-cs" in p and "not the campaign's release build" in p for p in probs)
              and any("libcubrid.so" in p for p in probs) and any("libcubridsa.so" in p for p in probs))

        fake_rel = copy.deepcopy(base)
        for c in fake_rel:
            if c["cell"] == "4096-debug-sa":
                c["cubrid_rel"] = "CUBRID 11.5.0 (11.5.0.0001-deadbee) (64bit debug build for Linux)"   # planted defect B
        probs = problems_for(fake_rel, tmp)
        check(11, "a cell whose cubrid_rel names another build id is reported (the review's planted defect B)",
              len(probs) == 1 and "4096-debug-sa" in probs[0] and "pinned commit" in probs[0])

        wrong_build = copy.deepcopy(base)
        for c in wrong_build:
            if c["cell"] == "16384-release-sa":
                c["cubrid_rel"] = c["cubrid_rel"].replace("release build", "debug build")
        probs = problems_for(wrong_build, tmp)
        check(12, "a release cell whose cubrid_rel says the engine that answered was a debug build is reported",
              len(probs) == 1 and "16384-release-sa" in probs[0] and "does not name a release build" in probs[0])

        wrong_field = copy.deepcopy(base)
        for c in wrong_field:
            if c["cell"] == "8192-debug-cs":
                c["build"] = "release"
        probs = problems_for(wrong_field, tmp)
        check(13, "a cell whose build field disagrees with its cell id is reported",
              any("8192-debug-cs" in p and "field build" in p for p in probs))

    print(f"[selftest_config_domain] {len(FAILS)} failing check(s)")
    for f in FAILS:
        print("  " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
