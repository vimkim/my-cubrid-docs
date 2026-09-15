#!/usr/bin/env python3
"""Apply ticket 19's hand-owned matrix judgements to the merged coverage matrix.

    apply_matrix_scoping.py --matrix evidence/ticket19/matrix.json

`matrix_merge.py` can decide everything mechanical: which rows exist, what their history is,
and that a PASS with proven evidence is eligible for `gap_kind: none`.  What it cannot decide
is whether the case actually asserted every clause of the requirement's stated behaviour --
that is a judgement about the requirement's text, and the ticket 35 F2 rule (qualified by the
delta review's D1) puts it in human hands:

  a row says where its OOS-path evidence comes from, and it must NOT carry `gap_kind: none`
  when a clause of the requirement's stated behaviour is evidenced only by a checker outside
  every executed suite; a row whose every clause the case asserts at the seam records the
  checker as the source of its OOS-backed premise and may keep `none`.  Where the case
  executes no clause at all, use the two-row form: a scoped case row plus a caseless companion
  with `latest_outcome: null`.

`matrix_merge.py` preserves a hand-set gap kind and never upgrades it to `none`, and preserves
caseless rows verbatim, so re-merging after this script is safe and is what proves it.

`hand_maintained` is set on the caseless rows ONLY.  On a case row it would mean more than it
should: the merger preserves such a row verbatim and refuses to merge any further attempt into
it, which would freeze its history at ticket 19's two invocations and silently drop every later
run of the same case.  A hand-set gap kind needs no flag to survive -- the merger never upgrades
one to `none`, which is what the re-merge check demonstrates.

This script is idempotent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FAMILY = {"OOS-SQL": "SQL operations", "OOS-REP": "Representation"}

# ---------------------------------------------------------------------------------------------
# 1. case rows whose every clause the case asserts at the seam: keep `none`, say where the
#    OOS-backed premise came from.
# ---------------------------------------------------------------------------------------------
KEEP_NONE = {
    "OOS-SQL-01": (
        "EVERY CLAUSE ASSERTED AT THE SEAM. OOS-SQL-01 states that an inserted OOS-backed row "
        "reads back byte-identical 'for single rows and bulk inserts of varying sizes', and the "
        "case asserts exactly that: one row, 100 rows of 4,207..4,900 B and 1,000 rows of "
        "4,100..4,196 B, each verified by whole-value equality, by OCTET_LENGTH and by an MD5 "
        "computed independently in Python, with COUNT(DISTINCT MD5(payload)) equal to the row "
        "count so the aggregates cannot pass on identical rows. The one thing the seam cannot "
        "see is the premise that the rows were OOS-backed at all; that comes from "
        "tools/activation_check_spec.sh, a validated checker outside every executed suite, "
        "which asserts Oos_num_recs and Oos_recs_sumlen against figures derived from the pinned "
        "engine's record accounting. Under the ticket 35 D1 qualification that is the "
        "OOS-SQL-01 situation and the row keeps gap_kind none."),
    "OOS-SQL-02": (
        "EVERY CLAUSE ASSERTED AT THE SEAM. OOS-SQL-02 states that after an UPDATE of an "
        "OOS-backed attribute, or of an inline attribute in an OOS-backed record, the updater "
        "and every later reader see the exact new value, and that repeated updates leave the "
        "final value correct. The case asserts all of it: the OOS-backed attribute updated, the "
        "inline attribute updated alone with the OOS-backed one still exact afterwards, three "
        "and fifty repeated updates with the final value checked, the single-chunk to two-chunk "
        "transition at 20,000 B and back, an UPDATE whose value comes from a subquery over "
        "another table's OOS-backed column, and an UPDATE through a join. Chain ownership is "
        "explicitly not this requirement's (its authority note assigns it to OOS-SQL-03 and "
        "OOS-SQL-04), so nothing is left to the checker but the OOS-backed premise, which "
        "tools/activation_check_spec.sh supplies. gap_kind none under the ticket 35 D1 "
        "qualification."),
}

# ---------------------------------------------------------------------------------------------
# 2. case rows with at least one clause the case does not execute: scoped, never `none`.
# ---------------------------------------------------------------------------------------------
SCOPED = {
    "OOS-SQL-05": ("Delivery gap",
        "SCOPE OF THIS ROW: the clauses the case executes, not the whole requirement. "
        "OOS-SQL-05 has four clauses. The case asserts two of them -- a deleted OOS-backed row "
        "is gone for the deleter and for later readers (three deletes, including one whose "
        "predicate reads the OOS-backed column itself, each with its affected-row count), and "
        "the table stays reusable (delete-all and TRUNCATE, each followed by a re-INSERT that "
        "reads back byte-exactly). It asserts NEITHER of the other two. 'The deleted record "
        "keeps its stubs and its value chains are not removed at delete time in MVCC mode' is "
        "invisible to portable SQL; the paired activation check reaches it but deliberately "
        "OBSERVES rather than asserts it, because the moment vacuum reclaims a chain is a "
        "background event and an assertion there would be an assertion against a race. 'Earlier "
        "snapshots can still read the value' needs a second session and belongs to OOS-CL-01 on "
        "the private shell seam. latest_outcome PASS refers to the executed attempts and must "
        "not be read as coverage of OOS-SQL-05; the companion row OOS-SQL-05/-/physical-half "
        "carries the gap with a null outcome."),
    "OOS-SQL-06": ("Delivery gap",
        "SCOPE OF THIS ROW: the clauses the case executes, not the whole requirement. "
        "OOS-SQL-06 states that ROLLBACK, savepoint rollback and statement failure restore the "
        "previous record as-is, 'including its OOS inline stubs whose head OIDs still reference "
        "live chains', with 'no partial effect and no orphan chain remains from the aborted "
        "work'. The three cases assert the logical half completely: the writer sees its own "
        "uncommitted OOS writes, a ROLLBACK restores the original 4,200 B value by digest and "
        "not merely by length, a partial rollback keeps the pre-savepoint value and discards "
        "everything after it, and four failing statements -- primary key, secondary unique, NOT "
        "NULL and a three-row INSERT colliding on its last row -- each store nothing at all. "
        "The two physical clauses are asserted nowhere: 'whose head OIDs still reference live "
        "chains' and 'no orphan chain remains' are not observable from portable SQL, and the "
        "requirement's own authority note assigns orphan-chain cleanup to OOS-CL-02 on the "
        "private shell seam. The companion row OOS-SQL-06/-/chain-clauses carries the gap."),
    "OOS-REP-06": ("Delivery gap",
        "SCOPE OF THIS ROW: the LOB copy-semantics half only. OOS-REP-06 states that "
        "'eligibility depends only on the value being variable-length and larger than the "
        "floor; BLOB/CLOB locator values demote like any other variable value with LOB copy "
        "semantics preserved, and deleting or vacuuming a demoted locator never removes the "
        "external LOB payload'. The case asserts that a row carrying four BLOB locators, a CLOB "
        "locator and an OOS-backed BIT VARYING column reads every one of them back exactly, "
        "that INSERT ... SELECT copies all of them, and that deleting the source rows leaves "
        "every one of the copy's external payloads readable -- the clause that would fail if "
        "the copy had borrowed the source's external file rather than copying it. It does NOT "
        "assert that a locator was demoted: beside a 4,200 B payload the largest-first loop "
        "stops long before a ~60-byte locator becomes the largest candidate, and portable SQL "
        "cannot see per-attribute placement anyway. So the eligibility clause, and with it the "
        "'deleting or vacuuming a DEMOTED locator' clause, are untested here. The companion row "
        "OOS-REP-06/-/locator-demotion carries the gap."),
}

# ---------------------------------------------------------------------------------------------
# 3. caseless rows: the clauses no ticket 19 case reaches, the withheld requirements, and the
#    engine defect this ticket found.
# ---------------------------------------------------------------------------------------------
CASELESS = [
    ("OOS-SQL-05/-/physical-half", "OOS-SQL-05", "Delivery gap", "missing", "show-heap-oos",
     "NO EXECUTED SUITE ASSERTS THAT A DELETED ROW'S CHAINS SURVIVE. Recorded as its own row "
     "with a null outcome so that no outcome filter counts OOS-SQL-05 as covered by the PASS of "
     "its companion case rows. The observation exists: evidence/ticket19/activation/"
     "cbrd_26659_oos_sql05_delete.spec replays the case's four-row fixture client-server and "
     "reads SHOW HEAP OOS after one DELETE and after deleting the rest, printing the chunk "
     "count and payload sum each time. It observes rather than asserts them on purpose -- the "
     "expected value is stated in the spec beside the observation, but vacuum reclaims a chain "
     "on its own schedule, so an assertion immediately after a DELETE would be an assertion "
     "against a race rather than against the requirement. The requirement's own authority note "
     "already limits the clause to client-server mode, because the standalone eager path "
     "deletes synchronously (ticket 11 section 6). Closing this needs the private shell seam, "
     "where a controlled vacuum and a second session are available: OOS-CL-01 and OOS-CL-02."),
    ("OOS-SQL-06/-/chain-clauses", "OOS-SQL-06", "Delivery gap", "missing", None,
     "NO EXECUTED SUITE ASSERTS THE TWO PHYSICAL CLAUSES OF OOS-SQL-06. Recorded as its own row "
     "with a null outcome so the PASS of the three companion case rows cannot be read as "
     "coverage of the requirement. 'Restore the previous record as-is, INCLUDING ITS OOS INLINE "
     "STUBS WHOSE HEAD OIDS STILL REFERENCE LIVE CHAINS' and 'NO ORPHAN CHAIN REMAINS from the "
     "aborted work' are statements about head OIDs and chain liveness after an undo. Portable "
     "SQL exposes neither, and the public activation channel cannot separate a restored stub "
     "from a rewritten one: SHOW HEAP OOS reports per-class totals, not per-record identity. "
     "The value half is fully asserted by the three cases, which is why they PASS. The "
     "requirement's own authority note assigns orphan-chain cleanup eventuality to OOS-CL-02; "
     "rollback survival against vacuum is OOS-CL-03, and both are private shell seam work."),
    ("OOS-REP-06/-/locator-demotion", "OOS-REP-06", "Delivery gap", "missing", None,
     "NO EXECUTED SUITE OBSERVES A DEMOTED LOB LOCATOR. Recorded as its own row with a null "
     "outcome. OOS-REP-06's eligibility clause -- that a BLOB/CLOB locator value demotes like "
     "any other variable value once it exceeds the floor -- needs a fixture in which the "
     "locator string IS the largest eligible candidate, which means a record above the gate "
     "whose other variable values are all smaller than a locator (about 60 bytes). Ticket 19's "
     "case deliberately does the opposite: it places the locators beside a 4,200 B payload, "
     "because its subject is LOB copy semantics on the OOS path, not locator demotion. Building "
     "the demoting fixture is Representation-family work and belongs to ticket 18, whose "
     "checklist owns the eligibility floor and the many-demoted-attributes cases; a record "
     "assembled from ten or more locator columns and nothing else is the natural shape."),
    ("OOS-SQL-03/-/update-chain-growth", "OOS-SQL-03", "Delivery gap", "proven",
     "show-heap-oos",
     "OBSERVATION ONLY, NEVER A PASS. OOS-SQL-03 is catalogued observation-only with policy "
     "observe: at the pin every UPDATE allocates fresh OOS value chains even for attributes the "
     "statement did not assign, and that behaviour is superseded on paper by the accepted "
     "CBRD-27230 design, so it must never be promoted as required behaviour. It is recorded "
     "here as what it is. evidence/ticket19/activation/cbrd_26659_oos_sql02_update.spec replays "
     "the UPDATE case's fixture client-server and reads SHOW HEAP OOS after the initial INSERT "
     "and after three UPDATEs, one of which assigns ONLY the inline attribute; the chunk count "
     "and payload sum after each are printed as observations. latest_outcome is null because "
     "there is no requirement here to pass: the row exists so that the pin's behaviour is "
     "visible in the matrix and so that whoever implements CBRD-27230 has a before picture. "
     "gap_kind is Delivery gap rather than none for the same reason every other caseless row "
     "here carries one: the schema allows none only for a latest PASS with proven or reused "
     "evidence, this row has no outcome at all, and the observation is made by a checker "
     "outside every executed suite, so nothing in the campaign's executed coverage would "
     "notice if the pin stopped behaving this way."),
    ("OOS-SQL-04/-/-", "OOS-SQL-04", "Capability gap", "not-applicable", None,
     "WITHHELD AT THE PIN. OOS-SQL-04 (UPDATE chain reuse and commit-conditional cleanup, "
     "CBRD-27230) is catalogued UNSUPPORTED with authority policy withhold: the accepted design "
     "is absent from the pinned engine (forward walk present at vacuum_oos.cpp:154 and :275; no "
     "notify emitter, recovery.c:899 and mvcc.h:268 reserve the record). No ticket 19 case "
     "claims it and none may: asserting the pin's always-new-chain behaviour would enshrine "
     "superseded behaviour as required, and asserting the accepted design would fail on an "
     "engine that has not implemented it. Rollback-survival correctness continues under "
     "OOS-CL-03 on the private shell seam. Expected engine finding on this requirement: "
     "CBRD-27237."),
    ("OOS-SQL-07/-/-", "OOS-SQL-07", "Specification gap", "not-applicable", None,
     "BLOCKED ON A QUESTION ONLY THE USER CAN SETTLE. OOS-SQL-07 records that the normative "
     "context's section 5 Optimization Ideas A and its Milestones section still describe UPDATE "
     "value-chain reuse as a cancelled-M3 future improvement, while the 2026-08-13 spec note "
     "records CBRD-27230 as an accepted design and M2 as the umbrella for all remaining OOS "
     "work. Whether reuse is a merge-gating conformance item is undecided, and the specification "
     "says an unresolved question blocks only the affected cases. It blocks no ticket 19 case: "
     "every case of this family asserts value correctness, which holds under either answer. The "
     "row exists so the question stays visible in the coverage picture rather than disappearing "
     "because nothing failed."),
    ("OOS-REP-02/-/client-path-gate-bypass", "OOS-REP-02", "Engine defect", "proven",
     "show-heap-oos",
     "ENGINE DEFECT FOUND BY THIS TICKET (finding T19-F1). The OOS record gate is applied only "
     "on the server-side DML path. do_check_insert_server_allowed calls sm_class_has_triggers "
     "(..., TR_EVENT_INSERT) and leaves server_allowed at SERVER_INSERT_IS_NOT_ALLOWED when a "
     "trigger is involved (src/query/execute_statement.c:12445-12456); the client-side "
     "object-template path then serializes the record itself and hands the server a finished "
     "one, so heap_attrinfo_determine_disk_layout (src/storage/heap_file.c:12310) -- the only "
     "place the gate is applied, reached through heap_attrinfo_transform_to_disk* from "
     "src/transaction/locator_sr.c:7509 and :7513 -- is never called. Consequences at the pin, "
     "each reproduced: a 4,564 B record inserted into a table carrying an AFTER INSERT trigger "
     "is stored fully inline with no OOS file created, while the identical record inserted into "
     "an identical table without one demotes as derived (Has_oos_file 1, Oos_num_recs 1, "
     "Oos_recs_sumlen 4224); the same happens with NO trigger at all when "
     "insert_execution_mode excludes server INSERT ... VALUES, which is what shows the trigger "
     "is not the cause and the execution path is; and an UPDATE through that path MIGRATES AN "
     "EXISTING OOS-BACKED VALUE BACK INLINE, dropping its chain. Values stay byte-correct on "
     "both paths, which is exactly why no value-only test can see it -- the hazard the campaign "
     "specification names. It also interacts with OOS-REP-08: a record above "
     "heap_maxslotted_reclength arriving on the client path cannot be demoted and becomes a "
     "non-OOS REC_BIGONE instead. Evidence: the refused activation check of inv-T19-0001 "
     "(activation/cbrd_26659_oos_sql06_triggers/assertions.txt) and the probes recorded in "
     "expected-oracle.md section 13. Engine repair is out of the campaign's scope; no answer "
     "file encodes the defect, and the affected case was restructured to build its fixture "
     "before any trigger exists so that it covers what it claims to."),
]


def blank_row(row_id, req, gap_kind, evidence_status, channel, summary):
    return {
        "row_id": row_id,
        "requirement": req,
        "family": FAMILY[req.rsplit("-", 1)[0]],
        "case": None,
        "configuration": None,
        "run": None,
        "oos_evidence": {"status": evidence_status, "channel": channel,
                         "reference": None, "applicability": None},
        "finding": {"latest_outcome": None, "ever_failed": False, "history": [],
                    "gap_kind": gap_kind, "summary": summary},
        "flakiness": {"attempts": 0, "failures": 0, "intermittent": False,
                      "consecutive_fresh_fixture_reproductions": 0, "deterministic_claim": False},
        "known_issue": {"ticket": None, "relation": "none"},
        "attribution": {"target": "unknown", "evidence": None, "note": "no failure to attribute"},
        "attempt_records": [],
        "hand_maintained": True,
    }


TICKET19_CASES = {
    "cbrd_26659_oos_rep06_lob_neighbours", "cbrd_26659_oos_sql01_insert_select",
    "cbrd_26659_oos_sql02_mixed_chunks", "cbrd_26659_oos_sql02_update",
    "cbrd_26659_oos_sql05_delete", "cbrd_26659_oos_sql06_constraints",
    "cbrd_26659_oos_sql06_rollback", "cbrd_26659_oos_sql06_triggers",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", type=Path, required=True)
    args = ap.parse_args()

    m = json.loads(args.matrix.read_text())
    scoped = kept = added = 0

    for row in m["rows"]:
        case = (row.get("case") or {}).get("name")
        if case not in TICKET19_CASES:
            continue
        req = row["requirement"]
        if req in SCOPED:
            gap, summary = SCOPED[req]
            row["finding"]["gap_kind"] = gap
            row["finding"]["summary"] = summary
            scoped += 1
        elif req in KEEP_NONE:
            row["finding"]["summary"] = KEEP_NONE[req]
            kept += 1

    have = {r["row_id"] for r in m["rows"]}
    for row_id, req, gap, status, channel, summary in CASELESS:
        if row_id in have:
            for r in m["rows"]:
                if r["row_id"] == row_id:
                    r["finding"]["gap_kind"] = gap
                    r["finding"]["summary"] = summary
                    r["oos_evidence"]["status"] = status
                    r["oos_evidence"]["channel"] = channel
                    r["hand_maintained"] = True
            continue
        m["rows"].append(blank_row(row_id, req, gap, status, channel, summary))
        added += 1

    args.matrix.write_text(json.dumps(m, indent=2) + "\n")
    print(f"scoped {scoped} case row(s), kept gap_kind none on {kept} with a stated reason, "
          f"added {added} caseless row(s); {len(m['rows'])} rows total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
