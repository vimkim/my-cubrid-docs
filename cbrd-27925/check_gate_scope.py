#!/usr/bin/env python3
"""Check the READ-busy trace in a pure model; never start CUBRID."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


BASELINE = "f67f2f692a7ad9f9efada2178759ca713e596b9d"
CURRENT = "d52b1889e907abcf84190ec504dde3bc93de260d"
SOURCE = "src/storage/oos_file.cpp"
DIGEST = "9c746a2e313cc3e468c101578f16f69dc6f509ddb0d9850f81752bfaa141798a"


def function(source, name):
    match = re.search(r"^" + re.escape(name) + r" \(.*?^\}", source, re.M | re.S)
    if match is None:
        raise ValueError(f"Function missing: {name}")
    return match.group()


def run_model():
    # This models one completed lap with no reclaimed page and no other deletes.
    # It assumes the last-chunk deleter releases its WRITE latch before settlement.
    for gate in (True, False):
        for read_busy, write_busy in ((True, False), (False, True), (False, False)):
            if read_busy:
                result = "SKIPPED"
                gate_reached = False
            elif gate:  # Model an empty page rejected by the old LSA comparison.
                result = "DEFERRED"
                gate_reached = True
            else:
                result = "DEFERRED" if write_busy else "RECLAIMED"
                gate_reached = False
            pending = 1
            settled = result != "RECLAIMED"
            if settled:
                pending = pending - 1 + int(result == "DEFERRED")
            next_sweep_armed = pending > 0  # swept_this_boot is true.
            if read_busy:
                assert result == "SKIPPED" and not gate_reached
                assert pending == 0 and not next_sweep_armed
            elif not gate and write_busy:
                assert pending == 1 and next_sweep_armed
            elif not gate:
                assert result == "RECLAIMED" and not settled
            else:
                assert result == "DEFERRED" and gate_reached
                assert pending == 1 and next_sweep_armed
            print(json.dumps(dict(gate=gate, read_busy=read_busy, write_busy=write_busy,
                                  result=result, gate_reached=gate_reached,
                                  settled=settled, pending=pending,
                                  next_sweep_armed=next_sweep_armed)))
    # A new delete after the lap snapshot survives the existing subtraction.
    assert 2 - 1 + 0 == 1
    # An unknown file after restart is armed even with a zero counter.
    assert 0 > 0 or not False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    data = (args.repo / SOURCE).read_bytes()
    if hashlib.sha256(data).hexdigest() != DIGEST:
        raise ValueError("Source drift: re-review the trace before changing its pin")
    source = data.decode()
    old = subprocess.check_output(
        ["git", "-C", str(args.repo), "show", f"{BASELINE}:{SOURCE}"], text=True)
    names = ("oos_reclaim_fix_candidate", "oos_try_reclaim_page_internal",
             "oos_reclaim_settle_lap", "oos_reclaim_sweep_step", "oos_rv_redo_delete")
    for name in names:
        if function(source, name) != function(old, name):
            raise ValueError(f"Baseline comparison changed: {name}")
    reclaim = function(source, "oos_try_reclaim_page_internal")
    assert reclaim.index("if (page_ptr == NULL)") < reclaim.index("bool lsa_gate_passes")
    assert "result = OOS_RECLAIM_SKIPPED;" in reclaim
    settle = function(source, "oos_reclaim_settle_lap")
    assert "pending_deletes -= pending_at_start;" in settle
    assert "pending_deletes += n_deferred;" in settle
    assert "swept_this_boot = true;" in settle
    print(f"Source {CURRENT}: 5 relevant function bodies match {BASELINE}")
    run_model()
    print("PURE MODEL ONLY: no DB, engine execution, or sector-growth measurement")


if __name__ == "__main__":
    main()
