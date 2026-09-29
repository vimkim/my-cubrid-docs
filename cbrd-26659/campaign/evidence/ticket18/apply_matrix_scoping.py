#!/usr/bin/env python3
"""Apply ticket 18's hand-owned matrix judgements to evidence/ticket18/matrix.json.

    apply_matrix_scoping.py [--matrix PATH] [--dry-run]

Three things a merge cannot decide, written as code rather than as an edit so that a reader can
see the rule and re-run it (the shape ticket 19's apply_matrix_scoping.py established, and
ticket 19's T2 finding: it writes through `write_record`, never raw).

1.  **Attribution for the bootstrap failures.**  Every ticket-18 case row on the release
    configuration carries `ever_failed: true`, from `inv-T18-0001` and `inv-T18-0002`, whose
    `.answer` files were deliberately empty.  An empty answer is how CTP is made to execute a
    new case and write a candidate rather than skip it and still exit 0 (ticket 13 finding a),
    so the failure is the mechanism, not a finding.  The merger cannot know that, so it leaves
    `gap_kind: Under triage` and `attribution.target: unknown`; both are set here, and the
    attribution says in so many words that the cause is not the engine.

2.  **The ticket 35 F2 scoping rule, as qualified by the ticket 35 delta review's D1.**  A row
    must not carry `gap_kind: none` when a clause of the requirement's stated behaviour is
    evidenced only by a checker outside every executed suite; a row whose every OBLIGATION the
    case asserts at the seam may keep `none` and records the checker as the source of its
    OOS-backed premise.  For the Representation family that distinction bites hard: nine of the
    ten requirements these cases cite state their obligation as a placement, and placement is
    exactly what portable SQL cannot see.  One requirement keeps `none` -- see SCOPING below.

3.  **The caseless rows.**  Nine are added: the two conformance bands the cases enter and the
    two they do not, the two OOS-REP-07 clauses ticket 39 item 3 requires, and four clause-level
    rows for the obligations no executed suite asserts.  One is RETIRED: `OOS-REP-07/-/
    claim-withdrawn`, whose last remaining function was to say that OOS-REP-07 had no public
    case row yet (ticket 43's note).  It now has one.  The withdrawal itself is unaffected: it
    lives in `withdrawn_claims`, where ticket 42 put it, and still suppresses the two sealed
    ticket 14 manifests that cite the requirement.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from campaign_records import write_record  # noqa: E402

T18_CASES = {
    "cbrd_26659_oos_rep01_gate_boundary", "cbrd_26659_oos_rep02_demotion_order",
    "cbrd_26659_oos_rep04_eligibility_floor", "cbrd_26659_oos_rep07_chunk_boundary",
    "cbrd_26659_oos_rep08_bigone_rejection", "cbrd_26659_oos_rep09_null_empty",
    "cbrd_26659_oos_rep10_many_stubs", "cbrd_26659_oos_rep11_transitions",
    "cbrd_26659_oos_rep13_placement_hints",
}

BOOTSTRAP_NOTE = (
    "The two failures in this row's history are att-* of inv-T18-0001 and inv-T18-0002, the two "
    "bootstrap invocations, whose .answer files for this case were deliberately EMPTY. An empty "
    "answer is how CTP is made to execute a new case and write a candidate rather than skip it "
    "and still exit 0 (ticket 13 finding a), so the FAIL is the mechanism by which the candidate "
    "was produced. It is explicitly NOT an engine defect and not flakiness: the same case on the "
    "same build PASSes in inv-T18-0003 and inv-T18-0004 against the answers promoted from "
    "inv-T18-0002's candidates. inv-T18-0001 additionally ran an earlier revision of "
    "cbrd_26659_oos_rep13_placement_hints, whose expected error identity the first candidate "
    "review corrected from -494 to -495 (finding T18-F2)."
)

# requirement -> (gap kind, the judgement).  The Representation family's obligations are mostly
# placements, and placement is what the public SQL seam cannot observe.
SCOPING = {
    "OOS-REP-01": ("Delivery gap",
        "SCOPED (ticket 35 F2, as qualified by D1). Every obligation of OOS-REP-01 is a "
        "placement -- 'no attribute is demoted', 'HAS_OOS stays clear', 'a class that has never "
        "demoted a value has no OOS file' -- and none of the three is observable at the public "
        "SQL seam: SHOW cannot be projected, DISK_SIZE is placement-blind, and the case asserts "
        "values. What this case DOES assert is that the record below both gates reads back "
        "exactly; the three placement clauses are asserted by the paired SHOW HEAP OOS check "
        "(phases `inline`, `vot_inline`, `inline_before`: Has_oos_file 0, Oos_num_recs 0, "
        "Oos_recs_sumlen 0), which is outside every executed suite. The companion caseless row "
        "OOS-REP-01/-/inline-placement-observation, written by ticket 19, states the same thing "
        "and its rule is the one applied here."),
    "OOS-REP-02": ("Delivery gap",
        "SCOPED (ticket 35 F2). 'Demoted one at a time in descending size until the record is at "
        "or below the target or candidates are exhausted' and 'smaller eligible values may "
        "remain inline' are placement obligations; only 'every value reads back exactly' is at "
        "the seam, and that is what the answer asserts. The order itself is asserted by the "
        "paired check, which is built to fail on the wrong one: the unequal-candidate phase "
        "asserts Oos_recs_sumlen 2024, and 1924 -- the smaller candidate -- would fail it. The "
        "equal-size tie is deliberately NOT resolved anywhere: the normative text says only "
        "'sort candidates by size descending' and fixes no tie-break, so the payload sum is "
        "asserted (it is the same either way) and the identity of the moved column is not."),
    "OOS-REP-04": ("Delivery gap",
        "SCOPED (ticket 35 F2), two-row form. OOS-REP-04's whole statement is a placement: 'a "
        "value whose serialized size is at or below 16 B is never demoted, and a value whose "
        "serialized size exceeds 24 B is a demotion candidate whenever its record exceeds the "
        "gate'. The case executes no clause of it at the seam -- its answer asserts values -- so "
        "it carries a companion caseless row, OOS-REP-04/-/floor-placement. What makes the "
        "fixture worth its weight is in the checker: a fixed BIT(40000) filler leaves the record "
        "5,080 B after `payload` moves, still above the 4,086 B gate, so the loop runs out of "
        "candidates; Oos_num_recs is then 1 with a 15 B neighbour and 2 with a 24 B one, which "
        "is the floor and not the loop stopping early."),
    "OOS-REP-07": ("Delivery gap",
        "SCOPED (ticket 39 item 3, user decision 2026-09-14). The case asserts what the seam can "
        "see: the value reads back complete and byte-identical at one, two and three chunks, and "
        "the chain is written at all. 'Inserted tail first' and 'total_data_length excludes "
        "every chunk header' are carried as clause-level rows of their own with no case and no "
        "outcome -- OOS-REP-07/-/tail-first-insertion and "
        "OOS-REP-07/-/total-data-length-excludes-headers -- so that neither clause silently "
        "disappears and neither is claimed. The chunk counts are asserted by the paired check "
        "(1, 2 and 3 with payload sums 16296, 16324 and 32632), which is outside every executed "
        "suite."),
    "OOS-REP-08": ("Delivery gap",
        "SCOPED (ticket 35 F2). Three of the requirement's clauses are at the seam and the case "
        "asserts them: the rejection identity (Error:-1382), 'no row is stored' (COUNT(*) 0), and "
        "'a non-OOS bigone record, or an OOS-backed record left between the target and the "
        "bigone threshold, succeeds' (both neighbours accepted, values exact). Two are not: "
        "'before any chunk is written' and 'no OOS value chain is created' are placement facts, "
        "asserted by the paired check as Has_oos_file 0 on the rejected class, which is outside "
        "every executed suite. Companion row: OOS-REP-08/-/pre-write-rejection."),
    "OOS-REP-09": ("Delivery gap",
        "SCOPED (ticket 35 F2). 'Reads back as NULL or as the empty value' is at the seam and the "
        "case asserts it in both directions, including after the demoted sibling is set to NULL "
        "and reassigned. 'Is never demoted' is a placement, asserted by the paired check as "
        "Oos_num_recs 1 on a record carrying a NULL column, a zero-length column and a demoted "
        "4,200 B column -- two or three would be the finding. Companion row: "
        "OOS-REP-09/-/null-empty-placement."),
    "OOS-REP-10": ("Delivery gap",
        "SCOPED (ticket 35 F2). 'Every value reads back exactly' is at the seam and the case "
        "asserts it for all eighteen columns, with eighteen distinct digests so the group cannot "
        "pass on eighteen identical values. 'A record may carry many OOS inline stubs (ten or "
        "more)' and 'HAS_OOS is set once' are asserted by the paired check (Oos_num_recs 12, "
        "Oos_recs_sumlen 8016, which names WHICH twelve of the eighteen moved). 'Each demoted "
        "attribute's VOT entry carries IS_OOS' is observable at NEITHER campaign seam and not "
        "even through SHOW HEAP OOS; it is carried by OOS-REP-10/-/is-oos-vot-flags."),
    "OOS-REP-11": ("none",
        "`none` KEPT, which is the D1 case (the OOS-SQL-01 situation). OOS-REP-11's obligation is "
        "'the logical value is never affected by the transition'; its first half, 'an attribute's "
        "representation MAY move between inline and OOS as the record size crosses the target', "
        "is a permission and the premise, not an obligation. The case asserts the obligation at "
        "the seam at every step of four crossings of the gate, and the premise -- that a crossing "
        "really creates a chain -- comes from the paired check, whose `crossed_up` phase asserts "
        "Oos_num_recs 1 after an UPDATE on a row that was inline before it. The crossing back "
        "down is OBSERVED, not asserted, because the chain the previous UPDATE created is not "
        "reclaimed synchronously at this revision (OOS-SQL-03, observation-only)."),
    "OOS-REP-13": ("Specification gap",
        "BLOCKED, not PASS, and a Specification gap: whether PREFER_INLINE ordering and the "
        "FORCE_OUTLINE gate bypass are required behaviour is undecided, so a case cannot pass "
        "the question (ticket 39 item 2, user decision 2026-09-14; catalogue status BLOCKED, "
        "policy withhold). The case asserts logical correctness and one error path, both of "
        "which hold whatever the policy turns out to be, and asserts no placement. What the pin "
        "does is in the paired check as four observations and is recorded on "
        "OOS-REP-12/-/placement-hint-observation."),
}


def caseless(row_id, requirement, gap_kind, summary, evidence_ref=None):
    return {
        "row_id": row_id,
        "requirement": requirement,
        "family": "Representation",
        "case": None,
        "configuration": None,
        "run": None,
        "oos_evidence": {"status": "missing" if evidence_ref is None else "proven",
                         "channel": None if evidence_ref is None else "show-heap-oos",
                         "reference": evidence_ref, "applicability": None},
        "flakiness": {"attempts": 0, "failures": 0, "intermittent": False,
                      "consecutive_fresh_fixture_reproductions": 0, "deterministic_claim": False},
        "known_issue": {"ticket": None, "relation": "none"},
        "attribution": {"target": "unknown", "evidence": None,
                        "note": "a caseless row records a gap, not a failure; there is nothing to attribute"},
        "finding": {"latest_outcome": None, "ever_failed": False, "history": [],
                    "gap_kind": gap_kind, "summary": summary},
        "attempt_records": [],
        "hand_maintained": True,
    }


REL = "cbrd-26659/campaign/evidence/ticket18/inv-T18-0003"

NEW_ROWS = [
    caseless(
        "OOS-REP-03/-/quarter-page-gate", "OOS-REP-03", "Capability gap",
        "THE RECORD GATE DEVIATES FROM THE ACCEPTED FOUR-RECORD TARGET, AND TICKET 18 MEASURED "
        "THE DEVIATION AT THE PUBLIC SEAM. Re-verified at the pin rather than assumed: "
        "heap_attrinfo_determine_disk_layout compares header + payload + mvcc_extra against "
        "DB_PAGESIZE / 4 (src/storage/heap_file.c:12350 and :12383), 4,086 B at a 16 KiB page, "
        "and `heap_oos_inline_target_size` does not exist anywhere in the source. The accepted "
        "CBRD-27057 target is ALIGN_BELOW((heap_nonheader_page_capacity - 4 * SPAGE_SLOT_SIZE) / "
        "4, 4) = 4,060 B. For the family's schema (id INT, payload BIT VARYING, tag BIT "
        "VARYING(300 B)) the two disagree over a payload of 3,700 to 3,723 B, a range the "
        "derivation searches rather than remembers. cbrd_26659_oos_rep01_gate_boundary carries "
        "both edges of that band as fixtures, and the paired SHOW HEAP OOS check OBSERVED "
        "Has_oos_file 0, Oos_num_recs 0 and Oos_recs_sumlen 0 on both, where the accepted target "
        "requires 1 / 1 / 3724 and 1 / 1 / 3744. RECORDED AGAINST THE NORMATIVE EXPECTATION: the "
        "pin's answer is not promoted to an expectation and the accepted design's is not "
        "asserted at an engine that does not implement it, which is what policy `withhold` "
        "requires. GAP KIND: the catalogue fixes OOS-REP-03 as UNSUPPORTED with gap kind "
        "Capability gap -- an accepted design absent at the pin -- so that is the kind used here; "
        "ticket 18's criterion 4 names 'Engine defect or Specification gap per the authority "
        "policy', and the authority policy is the catalogue. The two answers whose case carries "
        "these fixtures are FLAGGED for the user's sign-off.",
        f"{REL}/activation_cbrd_26659_oos_rep01_gate_boundary_release.txt"),
    caseless(
        "OOS-REP-05/-/boundary-bands", "OOS-REP-05", "Capability gap",
        "THE 24-BYTE IDENTITY LAYOUT MOVES THREE BOUNDARIES, AND TICKET 18 DERIVED ALL THREE AND "
        "MEASURED ONE. At the pin OR_OOS_INLINE_SIZE is 16 and oos_record_header is 16 bytes; the "
        "accepted CBRD-26950 layout makes both 24. (a) ELIGIBILITY FLOOR: a BIT VARYING of 16 to "
        "23 logical bytes serializes to 20 to 24 B, which the pinned floor demotes and the "
        "accepted one does not. cbrd_26659_oos_rep04_eligibility_floor carries a 20 B value and "
        "the paired check OBSERVED Oos_num_recs 2, Oos_recs_sumlen 4264, where the accepted "
        "layout requires 1 and 4224. (b) SINGLE-TO-MULTI CHUNK: the boundary is 16,275 B under "
        "the 24-byte header and 16,283 B under the pinned one, so 16,276 to 16,283 is a range no "
        "case may claim a chunk count for; cbrd_26659_oos_rep07_chunk_boundary stays one byte "
        "outside it on either side and NO CASE ENTERS IT. (c) OOS + BIGONE REJECTION: an 8-byte "
        "larger stub moves the rejection threshold from a BIT filler of 16,177 B to 16,169 B, so "
        "16,169 to 16,176 is a range no case may claim an outcome for; "
        "cbrd_26659_oos_rep08_bigone_rejection stays outside it and NO CASE ENTERS IT. All three "
        "ranges are searched by derive_ticket19_sizes.py and asserted by its self-test, so an "
        "accounting change moves them there before it reaches a case. The answer whose case "
        "carries the floor band is FLAGGED for the user's sign-off. This row does not replace "
        "OOS-REP-05/-/-, ticket 41's row, which is preserved verbatim.",
        f"{REL}/activation_cbrd_26659_oos_rep04_eligibility_floor_release.txt"),
    caseless(
        "OOS-REP-07/-/tail-first-insertion", "OOS-REP-07", "Capability gap",
        "CLAUSE-LEVEL ROW (ticket 39 item 3, user decision 2026-09-14). OOS-REP-07 says a "
        "multi-chunk value is 'inserted tail first'. Chunk insertion ORDER is observable at "
        "neither campaign seam: SHOW HEAP OOS reports per-class totals and no ordering, the "
        "public SQL seam sees values, and the private shell seam sees utility output. Ticket 34 "
        "F2 withdrew the claim from cbrd_26659_oos_dur01 for exactly this reason. Ticket 18's "
        "case row is scoped to what the seam does execute and this clause is carried here, with "
        "no case and no outcome, so that it neither disappears nor is claimed. Observing it needs "
        "an instrumented run that logs the chunk write order, which no executed suite performs.",
        None),
    caseless(
        "OOS-REP-07/-/total-data-length-excludes-headers", "OOS-REP-07", "Capability gap",
        "CLAUSE-LEVEL ROW (ticket 39 item 3, user decision 2026-09-14). OOS-REP-07 says "
        "'total_data_length excludes every chunk header'. The field belongs to the accepted "
        "CBRD-26950 identity layout, which is absent at the pin (OOS-REP-05, UNSUPPORTED, policy "
        "withhold), so the clause is withheld rather than tested: there is nothing at this "
        "revision whose exclusion of a header could be checked. What the pin does expose, "
        "Oos_recs_sumlen, INCLUDES one 16-byte chunk header per chunk record -- 16296 for a "
        "16,275 B value, which is 16280 + 16 -- and that figure is used only by the paired "
        "checker and appears in no answer, precisely because it is layout-specific. Carried here "
        "with no case and no outcome.",
        None),
    caseless(
        "OOS-REP-04/-/floor-placement", "OOS-REP-04", "Delivery gap",
        "NO EXECUTED SUITE OBSERVES THE ELIGIBILITY FLOOR. Recorded as its own row with a null "
        "outcome, the two-row form of the ticket 13 report section 13, because the companion "
        "case row's PASS would otherwise let a reader filtering on outcome conclude that "
        "OOS-REP-04 is covered at the seam. Every word of the requirement is a placement -- "
        "'never demoted', 'is a demotion candidate' -- and the public SQL seam asserts values. "
        "The observation exists and is validated: the paired SHOW HEAP OOS check of "
        "cbrd_26659_oos_rep04_eligibility_floor asserts Oos_num_recs 1 for a 15 B neighbour and "
        "2 for a 24 B one on records that are still 5,080 B after demotion, and exits non-zero on "
        "mismatch. It is a script outside every CTP suite, so nothing in the campaign's executed "
        "coverage fails if a sub-floor value is wrongly demoted.",
        f"{REL}/activation_cbrd_26659_oos_rep04_eligibility_floor_release.txt"),
    caseless(
        "OOS-REP-08/-/pre-write-rejection", "OOS-REP-08", "Delivery gap",
        "TWO CLAUSES OF OOS-REP-08 ARE NOT OBSERVED BY ANY EXECUTED SUITE: that the rejection "
        "happens 'before any chunk is written', and that 'no OOS value chain is created'. The "
        "public SQL seam can see that the statement failed with Error:-1382 and that the table "
        "holds no row, and cbrd_26659_oos_rep08_bigone_rejection asserts both; it cannot see "
        "whether a chunk was written and then abandoned. The paired check asserts Has_oos_file 0 "
        "on the rejected class, which is the strongest statement available at this revision -- "
        "it would catch a chunk written before the check and not reclaimed, and it would not "
        "catch one written and reclaimed inside the failed statement. That residue needs an "
        "instrumented run and no executed suite performs one.",
        f"{REL}/activation_cbrd_26659_oos_rep08_bigone_rejection_release.txt"),
    caseless(
        "OOS-REP-09/-/null-empty-placement", "OOS-REP-09", "Delivery gap",
        "'IS NEVER DEMOTED' IS NOT OBSERVED BY ANY EXECUTED SUITE. cbrd_26659_oos_rep09_null_empty "
        "asserts the half of OOS-REP-09 the seam can see -- a NULL reads back NULL and a "
        "zero-length value reads back as zero bytes and not NULL, before and after the demoted "
        "sibling is set to NULL and reassigned -- and the other half is asserted by the paired "
        "check as Oos_num_recs 1 on a record carrying both of them beside a demoted 4,200 B "
        "value. A NULL variable value occupies no payload bytes at all and a zero-length one "
        "serializes to 4 B, so neither can be a candidate under any accounting; that is a "
        "derivation, and the check is what turns it into an observation.",
        f"{REL}/activation_cbrd_26659_oos_rep09_null_empty_release.txt"),
    caseless(
        "OOS-REP-10/-/is-oos-vot-flags", "OOS-REP-10", "Delivery gap",
        "'EACH DEMOTED ATTRIBUTE'S VOT ENTRY CARRIES IS_OOS' IS OBSERVABLE AT NEITHER SEAM AND "
        "NOT THROUGH SHOW HEAP OOS EITHER. The flag lives in the record's variable-offset table "
        "and the only channel that could report it is a debug or instrumented build with a record "
        "dumper; the campaign's diagnostic channel reports per-class chunk totals. What "
        "cbrd_26659_oos_rep10_many_stubs and its paired check do establish is the rest of the "
        "requirement: eighteen values read back exactly with eighteen distinct digests, and "
        "Oos_num_recs 12 with Oos_recs_sumlen 8016, which is ten or more stubs and identifies "
        "which twelve of the eighteen columns carry them. The record's own flag bits are carried "
        "here with no case and no outcome. An OOS-bearing record never reaches four-byte VOT "
        "entries at any supported page size, because it must fit heap_Maxslotted_reclength "
        "(16,236 B at 16 KiB) which is below OR_MAX_SHORT: that is a STRUCTURAL EXCLUSION, "
        "recorded as such rather than as an untested combination (ticket 11 section 5.1).",
        f"{REL}/activation_cbrd_26659_oos_rep10_many_stubs_release.txt"),
    caseless(
        "OOS-REP-12/-/placement-hint-observation", "OOS-REP-12", "Delivery gap",
        "OBSERVATION ONLY, NEVER A PASS. OOS-REP-12 is observation-only with policy `observe`: "
        "logical correctness and error paths are tested, and where a hinted value is placed is "
        "recorded as an implementation observation. cbrd_26659_oos_rep13_placement_hints is that "
        "one observation case (ticket 39 item 2) and cites OOS-REP-13, not this requirement, so "
        "this row has no case and no outcome; the gap kind is Delivery gap rather than none "
        "because the schema allows none only for a latest PASS with proven evidence. WHAT THE PIN "
        "DOES, observed by the paired check and asserted nowhere: STORAGE FORCE_OUTLINE demoted a "
        "40 B value out of a record far below the gate (Oos_num_recs 1, Oos_recs_sumlen 64), "
        "confirming the gate bypass; STORAGE PREFER_INLINE on the LARGEST column of an over-gate "
        "record left it inline and moved the second-largest instead (Oos_recs_sumlen 1924, the "
        "1,900 B column, against 2024 for the 2,000 B one), confirming that the hinted column "
        "sinks to the tail of the candidate list; and STORAGE PREFER_OUTLINE behaved exactly like "
        "an unhinted control (2024 in both), confirming that it is an alias of STORAGE DEFAULT at "
        "this revision, which the parse tree says in so many words (parse_tree.h:1948-1949). A "
        "storage hint on a column that is not variable-length is refused with Error:-495.",
        f"{REL}/activation_cbrd_26659_oos_rep13_placement_hints_release.txt"),
]

RETIRE = "OOS-REP-07/-/claim-withdrawn"
RETIRE_REASON = (
    "Ticket 43's note left the fate of this row to ticket 18: fold it into one of the two "
    "clause-level rows ticket 39 item 3 requires, or retire it. RETIRED. Its Delivery gap said "
    "'still true until ticket 18's case row exists', and that row now exists "
    "(OOS-REP-07/cbrd_26659_oos_rep07_chunk_boundary). Folding it into a clause row would mix a "
    "case-scoped withdrawal note into a requirement-level clause gap, which is a different "
    "thing: the withdrawal says one named case no longer claims the requirement, while the "
    "clause rows say two clauses of the requirement are claimed by nobody. The withdrawal itself "
    "is untouched -- it lives in the matrix-level `withdrawn_claims` list where ticket 42 put it, "
    "it still names cbrd_26659_oos_dur01 only, and it still keeps inv-T14-0001 and inv-T14-0002 "
    "from resurrecting the rows they cite. Its text is preserved in the ticket 18 delivery "
    "record."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", type=Path,
                    default=Path(__file__).resolve().parent / "matrix.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    matrix = json.loads(args.matrix.read_text())
    changed = []

    for row in matrix["rows"]:
        case = (row.get("case") or {}).get("name")
        if case not in T18_CASES:
            continue
        req = row["requirement"]
        gap, judgement = SCOPING[req]
        before = row["finding"].get("gap_kind")
        if row["finding"].get("ever_failed"):
            row["attribution"] = {"target": "harness", "evidence": BOOTSTRAP_NOTE,
                                  "note": "the cause is the deliberately empty bootstrap answer, "
                                          "not the engine"}
        row["finding"]["gap_kind"] = gap
        note = judgement
        if row["finding"].get("ever_failed"):
            note = f"{judgement} {BOOTSTRAP_NOTE}"
        row["finding"]["summary"] = note
        changed.append((row["row_id"], before, gap))

    existing = {r["row_id"] for r in matrix["rows"]}
    added = []
    for row in NEW_ROWS:
        if row["row_id"] in existing:
            raise SystemExit(f"{row['row_id']} already exists; refusing to overwrite a row")
        matrix["rows"].append(row)
        added.append(row["row_id"])

    retired = [r for r in matrix["rows"] if r["row_id"] == RETIRE]
    if len(retired) != 1:
        raise SystemExit(f"expected exactly one {RETIRE} row, found {len(retired)}")
    matrix["rows"] = [r for r in matrix["rows"] if r["row_id"] != RETIRE]
    if not any(e["requirement"] == "OOS-REP-07" for e in matrix.get("withdrawn_claims", [])):
        raise SystemExit("the OOS-REP-07 withdrawn_claims entry is gone; retiring the row would "
                         "lose the withdrawal, which is not what this ticket decided")

    for row_id, before, after in changed:
        print(f"scoped   {row_id:<74} {before} -> {after}")
    for row_id in added:
        print(f"added    {row_id}")
    print(f"retired  {RETIRE}")
    print(f"\n{len(changed)} row(s) scoped, {len(added)} caseless row(s) added, 1 retired; "
          f"{len(matrix['rows'])} rows total")
    if args.dry_run:
        print("(dry run; nothing written)")
        return 0
    write_record(matrix, args.matrix, "matrix")
    print(f"wrote {args.matrix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
