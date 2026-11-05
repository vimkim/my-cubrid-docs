#!/usr/bin/env python3
"""Exhaustive interleaving model of one OOS growth-gate sweep lap vs. an INSERT-undo.

Pure model. It never starts CUBRID. It mirrors, at d52b188, oos_rv_redo_delete (note under
the undo's WRITE latch), oos_try_reclaim_page_internal phase 1/2, oos_reclaim_settle_lap and
the arming test in oos_reclaim_sweep_step. Pages: P (emptied by the INSERT undo) and Q
(a second data page whose state is an input).

Variants:
  gate      : True = LSA gate present (P's page LSA is newer than the horizon while the
              aborting transaction is active); False = ADR-0008 (no gate).
  busy_rule : "skip" = current code (phase-1 READ busy -> SKIPPED);
              "defer" = candidate fix (phase-1 READ busy -> DEFERRED).

Property checked after both threads finish (quiescent state):
  P is empty and still allocated  ==>  the next growth arms a sweep (pending > 0 or boot rule).
Reported alongside: whether P was reclaimed, and counts of extra sweeps forced by busy Q.
"""

import hashlib
import itertools
import json
from pathlib import Path
import re
import sys

SOURCE = "src/storage/oos_file.cpp"
DIGEST = "9c746a2e313cc3e468c101578f16f69dc6f509ddb0d9850f81752bfaa141798a"  # d52b1889e


def body(src, name):
    m = re.search(r"^" + re.escape(name) + r" \(.*?^\}", src, re.M | re.S)
    if m is None:
        raise ValueError(f"Function missing: {name}")
    return m.group()


def check_source(repo):
    data = (Path(repo) / SOURCE).read_bytes()
    if hashlib.sha256(data).hexdigest() != DIGEST:
        raise ValueError("Source drift: re-read the functions before trusting this model")
    src = data.decode()
    rec = body(src, "oos_try_reclaim_page_internal")
    # Phase-1 busy returns (result still SKIPPED) before any LSA comparison.
    assert rec.index("if (page_ptr == NULL)") < rec.index("oos_reclaim_lsa_gate_passes")
    settle = body(src, "oos_reclaim_settle_lap")
    assert settle.index("-= pending_at_start") < settle.index("+= n_deferred")
    undo = body(src, "oos_rv_redo_delete")
    # The hint is re-armed inside the undo callback, i.e. while log_rollback holds the WRITE latch.
    assert "oos_stats_del_bestspace_by_vpid (thread_p, &page_vpid, true" in undo
    step = body(src, "oos_reclaim_sweep_step")
    assert "pending_deletes > 0 || !it->second.swept_this_boot" in step
    assert step.index("return NO_ERROR;\n\t\t}\n\t      if (result == OOS_RECLAIM_DEFERRED)") > 0
    print(f"source pin ok: {SOURCE} sha256={DIGEST[:12]}")


def explore(gate, busy_rule, q_state, start_pending, swept_this_boot):
    # q_state: "empty_old" (reclaimable empty), "full", "busy" (WRITE-latched by an inserter
    # for the whole lap, never empty from the sweep's view).
    undo = ["latch", "delete_note", "release", "end"]
    sweep = ["claim", "visit_P", "visit_Q", "settle"]
    results = []
    # Every interleaving of the two programs (order within each preserved).
    n = len(undo) + len(sweep)
    for pos in itertools.combinations(range(n), len(undo)):
        s = dict(p_latched=False, p_empty=False, p_alloc=True, undo_active=True,
                 pending=start_pending, boot=swept_this_boot, claimed=False,
                 at_start=0, deferred=0, reclaimed_any=False, settled=False,
                 stopped=False, reclaimed=[])
        ui = si = 0
        for k in range(n):
            if k in pos:
                step = undo[ui]; ui += 1
                if step == "latch":
                    s["p_latched"] = True
                elif step == "delete_note":
                    s["p_empty"] = True
                    s["pending"] += 1
                elif step == "release":
                    s["p_latched"] = False
                elif step == "end":
                    s["undo_active"] = False  # the aborting transaction ends later
            else:
                step = sweep[si]; si += 1
                if step == "claim":
                    if s["pending"] > 0 or not s["boot"]:
                        s["claimed"] = True
                        s["at_start"] = s["pending"]
                elif not s["claimed"] or s["stopped"]:
                    continue
                elif step == "visit_P":
                    if not s["p_alloc"]:
                        continue
                    if s["p_latched"]:  # conditional READ fails
                        if busy_rule == "defer":
                            s["deferred"] += 1
                        continue
                    if not s["p_empty"]:
                        continue
                    if gate and s["undo_active"]:
                        s["deferred"] += 1
                        continue
                    s["p_alloc"] = False
                    s["reclaimed"].append("P")
                    s["stopped"] = True  # sweep stops at first reclaimed page
                elif step == "visit_Q":
                    if q_state == "busy":
                        if busy_rule == "defer":
                            s["deferred"] += 1
                        continue
                    if q_state == "empty_old":
                        s["reclaimed"].append("Q")
                        s["stopped"] = True
                elif step == "settle":
                    s["pending"] = max(0, s["pending"] - s["at_start"]) + s["deferred"]
                    s["boot"] = True
                    s["settled"] = True
        stranded = s["p_empty"] and s["p_alloc"]
        armed = s["pending"] > 0 or not s["boot"]
        results.append(dict(order="".join("U" if k in pos else "S" for k in range(n)),
                            stranded=stranded, armed=armed, violation=stranded and not armed,
                            spurious_armed=armed and not stranded,
                            p_reclaimed="P" in s["reclaimed"]))
    return results


def main():
    if len(sys.argv) > 1:
        check_source(sys.argv[1])
    summary = []
    for gate, busy_rule, q_state, (start_pending, boot) in itertools.product(
            (True, False), ("skip", "defer"), ("full", "empty_old", "busy"),
            ((0, True), (1, True), (0, False))):
        r = explore(gate, busy_rule, q_state, start_pending, boot)
        bad = [x["order"] for x in r if x["violation"]]
        summary.append(dict(gate=gate, busy_rule=busy_rule, q=q_state,
                            start_pending=start_pending, swept_this_boot=boot,
                            orders=len(r), violations=len(bad), example=bad[:1],
                            p_reclaimed_orders=sum(x["p_reclaimed"] for x in r),
                            stranded_armed=sum(x["stranded"] and x["armed"] for x in r),
                            spurious_armed=sum(x["spurious_armed"] for x in r)))
    for row in summary:
        print(json.dumps(row))
    # Expectations derived from the source reading; a failure here means the reading is wrong.
    def pick(**kw):
        return [x for x in summary if all(x[k] == v for k, v in kw.items())]
    skip_viol = [x for x in pick(busy_rule="skip") if x["violations"]]
    defer_viol = [x for x in pick(busy_rule="defer") if x["violations"]]
    assert skip_viol, "expected the lost-hint order under the current busy rule"
    for q in ("full", "busy"):
        g = pick(gate=True, busy_rule="skip", q=q, start_pending=0, swept_this_boot=True)[0]
        ng = pick(gate=False, busy_rule="skip", q=q, start_pending=0, swept_this_boot=True)[0]
        assert ng["p_reclaimed_orders"] > g["p_reclaimed_orders"], "gate removal must reclaim more"
        assert ng["violations"] == g["violations"], "gate removal must not change lost-hint orders"
    assert any(not x["gate"] for x in skip_viol), "gate removal must not remove the lost-hint order"
    assert not defer_viol, "busy->DEFERRED must keep every stranded P armed"
    print("violations(skip):", sorted({(x["gate"], x["q"], x["start_pending"], x["swept_this_boot"])
                                       for x in skip_viol}))
    print("PURE MODEL ONLY: no DB, engine execution, or sector-growth measurement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
