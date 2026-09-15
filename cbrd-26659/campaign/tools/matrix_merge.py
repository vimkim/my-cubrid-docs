#!/usr/bin/env python3
"""Merge campaign manifests into the coverage matrix (ticket 15).

    matrix_merge.py --manifest FILE ... [--existing matrix.json] --out matrix.json
                    [--attempt-records-dir DIR ...] [--generated-at ISO]

The matrix is the cross-invocation aggregation; the manifest is the per-invocation record
(spec "Campaign manifest"). Rows are keyed by requirement ID and (case name, configuration):
one row per (requirement, case, page size, build mode, run mode, instrumentation), so the same
case run on release and on debug gives two rows, as ticket 14's matrix does.

Rules encoded (sources in brackets):

* Merge by requirement ID; append to `finding.history` (deduplicated by attempt id); set
  `ever_failed` monotonically; a later pass never erases an earlier failure; never drop a row
  because a later invocation passed [ticket 12 section 3; decision 07].
* Never write `accepted_exclusions`; preserve every entry verbatim [spec "Review, sign-off"].
* A row carrying `hand_maintained: true` is preserved verbatim: never regenerated, never
  merged into, and never duplicated by a new row with the same key [ticket 36 item 6]. The
  field replaces recognition by row id FOR PRESERVATION, which is what ticket 36 decided: it
  says a human owns THIS row. A caseless row (`case: null`) is preserved whether or not it
  carries the field, because no manifest produces one.
* Withdrawal is a different rule with a home of its own: the matrix-level `withdrawn_claims`
  list, hand-maintained and never written here, exactly as `accepted_exclusions` is [ticket 42].
  An entry says a named CASE no longer claims a named requirement, so no manifest creates a row
  for that (requirement, case) pair however the manifest still reads -- `inv-T14-0001` and
  `inv-T14-0002` are sealed evidence and cite `OOS-REP-07` forever. Withdrawal is scoped to
  cases because that is what the fact is about: `cbrd_26659_oos_dur01` does not claim
  `OOS-REP-07`, which says nothing about any other case. A requirement-scoped rule would drop
  the `OOS-REP-07` case row ticket 39 item 3 requires of ticket 18, so a different case citing
  the requirement still gets its row. `hand_maintained` carries preservation only: ticket 13's
  four caseless rows are hand-owned too, and `OOS-REP-05/-/-` is a plain "no case written yet"
  placeholder whose first real case row must not be suppressed.
* No meaning is read from a row id anywhere [ticket 42, completing ticket 36 item 6]. A row
  whose id ends `/claim-withdrawn` with no matching `withdrawn_claims` entry is REFUSED, not
  fallen back on: the fallback would be requirement scope, which is the defect above.
* `flakiness`, `known_issue` and `attribution` are preserved on existing rows; the tool only
  updates the counts it can measure (attempts, failures, intermittent) and never touches
  `consecutive_fresh_fixture_reproductions`, `deterministic_claim`, `known_issue` or
  `attribution` [ticket 15 criteria].
* `gap_kind: none` only for a latest PASS with proven or reused evidence [ticket 12 section 2].
  The qualified rule for rows whose evidence comes from a checker outside every executed suite
  [ticket 13 report section 8 at docs commit f164879]: a row is NOT `none` when a clause of the
  requirement's stated behaviour is evidenced solely by that checker; a row whose every clause
  the case asserts at the seam may keep `none` while its summary records the checker as the
  source of its OOS-backed premise. Whether a clause is checker-only is a judgement about the
  requirement's text that tooling cannot make, so: a hand-set gap kind on an existing row is
  preserved verbatim (the tool never upgrades a row to `none`), and a NEW row gets `none` only
  under the schema rule with a summary that names the evidence status and asks the author to
  scope the row. A row whose latest outcome stops being a proven/reused PASS loses `none`.
* Provisional gap kinds for non-PASS latest outcomes: SKIP -> Delivery gap (the coverage was
  not delivered), UNSUPPORTED -> Capability gap, BLOCKED -> Specification gap when the
  requirement's catalogue status is BLOCKED else Capability gap, FAIL -> Engine defect only
  when the row's attribution is `engine` (hand-set, with evidence), otherwise `Under triage`:
  an unexplained failure is not automatically an engine defect [decision 07], and it is not a
  Delivery gap either, which would say the case was never delivered [ticket 36 item 5].
* Attempts of kind checker-validation or coexistence never reach the matrix: they have no
  manifest [schemas document section 11].

The output is validated against matrix.schema.json before it is written.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign_records import (  # noqa: E402
    RecordError, catalogue_identity, docs_relative, load_json, now_iso, requirement, row_configuration_suffix,
    sha256_prefixed, write_record,
)


def hand_maintained_list(matrix, key):
    """A matrix-level list a human owns: `accepted_exclusions`, `withdrawn_claims`.

    Returns (present, copy). The copy is what the never-written guard compares against at the end
    of the merge. Reading the live list instead would compare the object with itself, so the guard
    could never fire on an in-place edit -- which is the one thing it exists to catch.
    """
    return key in matrix, list(matrix.get(key, []))


def row_key(req, case_name, cfg):
    return (req, case_name, cfg["page_size"], cfg["build_mode"], cfg["run_mode"], cfg.get("instrumentation_id"))


def is_hand_maintained(row) -> bool:
    """Ticket 36 item 6: a hand-owned row, preserved verbatim and never regenerated.

    The row says so with `hand_maintained: true`. A caseless row is hand-owned whether or not
    it carries the field, because no manifest produces a row without a case; that is a fact
    about the row's shape, not a reading of its id.
    """
    return row.get("hand_maintained") is True or row.get("case") is None or row.get("configuration") is None


def provisional_gap_kind(outcome, evidence_status, req_id, attribution_target):
    if outcome == "PASS":
        return "none" if evidence_status in ("proven", "reused") else "Delivery gap"
    if outcome == "SKIP":
        return "Delivery gap"
    if outcome == "UNSUPPORTED":
        return "Capability gap"
    if outcome == "BLOCKED":
        return "Specification gap" if requirement(req_id)["status"] == "BLOCKED" else "Capability gap"
    if outcome == "FAIL":
        return "Engine defect" if attribution_target == "engine" else "Under triage"
    return "Delivery gap"


def generated_summary(outcome, evidence, req_id, case_name, gap_kind, from_checker_note=None):
    ev = evidence["status"]
    base = f"GENERATED by matrix_merge.py for {case_name}: latest outcome {outcome}, OOS-path evidence {ev}"
    if evidence.get("channel"):
        base += f" over channel {evidence['channel']}"
    if outcome == "PASS" and ev in ("proven", "reused"):
        base += (". gap_kind none under the schema rule (PASS with proven or reused evidence). SCOPE TO BE CONFIRMED BY THE AUTHOR: "
                 "if any clause of the requirement's stated behaviour is evidenced solely by a checker outside every executed suite, "
                 "set gap_kind to Delivery gap and say so here (qualified rule, ticket 13 report section 8); the merge preserves a hand-set gap kind.")
    elif outcome == "PASS":
        base += ". Logical success without OOS-path evidence is not OOS coverage; gap_kind Delivery gap until the activation evidence is captured."
    elif outcome == "FAIL":
        base += (f". gap_kind {gap_kind}: the attribution is not yet established, and an unexplained failure is neither automatically an "
                 "Engine defect (decision 07) nor a Delivery gap, which would say the case was never delivered (ticket 36 item 5). "
                 "Triage sets attribution.target, with evidence for `engine`, and the gap kind follows. The failure stays in history "
                 "and ever_failed whatever later runs show.")
    elif outcome == "SKIP":
        base += ". A SKIP is never PASS; the coverage this row owes was not delivered in the latest attempt."
    else:
        base += f". Outcome {outcome} recorded from the case's declaration against the requirement's catalogue status."
    return base


def new_row(req_id, case_entry, manifest, manifest_path, attempt_id, att_record_path, at):
    cfg = {"page_size": manifest["invocation"]["page_size"], "build_mode": manifest["invocation"]["build_mode"],
           "run_mode": manifest["invocation"]["run_mode"],
           "instrumentation_id": (manifest["invocation"].get("instrumentation") or {}).get("patch_id"),
           "services": [f"{s['kind']}:{s['port'] if s.get('port') else s['identity'].split(',')[0].split(' for ')[-1].split()[-1] if s['kind'] != 'cub_server' else s['identity'].split(',')[0]}"
                        for s in manifest["invocation"]["services"]]}
    outcome = case_entry["outcome"]
    gap = provisional_gap_kind(outcome, case_entry["oos_evidence"]["status"], req_id, "unknown")
    return {
        "row_id": f"{req_id}/{case_entry['case']['name']}/{row_configuration_suffix(cfg['page_size'], cfg['build_mode'], cfg['run_mode'], cfg['instrumentation_id'])}",
        "requirement": req_id,
        "family": requirement(req_id)["family"],
        "case": case_entry["case"],
        "configuration": cfg,
        "run": None,
        "oos_evidence": None,
        "finding": {"latest_outcome": None, "ever_failed": False, "history": [], "gap_kind": gap, "summary": None},
        "flakiness": {"attempts": 0, "failures": 0, "intermittent": False, "consecutive_fresh_fixture_reproductions": 0, "deterministic_claim": False},
        "known_issue": {"ticket": None, "relation": "none"},
        "attribution": {"target": "unknown", "evidence": None, "note": "no failure to attribute" if outcome == "PASS" else "not yet attributed; an unexplained failure stays unknown until evidence supports attribution"},
        "attempt_records": [],
    }


def apply_attempt(row, req_id, case_entry, manifest, manifest_path, attempt, att_record_path, at):
    hist = row["finding"]["history"]
    if any(h["attempt_id"] == attempt["attempt_id"] for h in hist):
        return False  # already merged; idempotent
    outcome = case_entry["outcome"]
    hist.append({"manifest_id": manifest["manifest_id"], "attempt_id": attempt["attempt_id"], "outcome": outcome, "at": at})
    hist.sort(key=lambda h: h["at"])
    latest = hist[-1]
    # run and evidence follow the latest attempt in time, not the order of merging
    if latest["attempt_id"] == attempt["attempt_id"]:
        inv = manifest["invocation"]
        row["run"] = {"manifest_id": manifest["manifest_id"], "manifest_path": docs_relative(manifest_path),
                      "manifest_hash": sha256_prefixed(manifest_path), "engine_commit": inv["engine"]["baseline_commit"],
                      "testcase_commit": inv["testcase"]["commit"], "context_content_hash": inv["context"]["content_hash"]}
        row["oos_evidence"] = dict(case_entry["oos_evidence"])
        row["finding"]["latest_outcome"] = outcome
    row["finding"]["ever_failed"] = row["finding"]["ever_failed"] or outcome == "FAIL"
    row["flakiness"]["attempts"] = len(hist)
    row["flakiness"]["failures"] = sum(1 for h in hist if h["outcome"] == "FAIL")
    row["flakiness"]["intermittent"] = row["flakiness"]["failures"] > 0 and any(h["outcome"] == "PASS" for h in hist)
    if att_record_path and att_record_path not in row["attempt_records"]:
        row["attempt_records"].append(att_record_path)
    # gap kind: never upgrade a hand-set gap to none; leave none only while PASS + proven/reused holds
    latest_outcome = row["finding"]["latest_outcome"]
    ev_status = (row["oos_evidence"] or {}).get("status")
    computed = provisional_gap_kind(latest_outcome, ev_status, req_id, row["attribution"]["target"])
    current = row["finding"]["gap_kind"]
    if current == "none" and computed != "none":
        row["finding"]["gap_kind"] = computed
        row["finding"]["summary"] = generated_summary(latest_outcome, row["oos_evidence"], req_id, case_entry["case"]["name"], computed) + \
            (f" PREVIOUS SUMMARY (hand-written, superseded by outcome change): {row['finding'].get('summary')}" if row["finding"].get("summary") else "")
    elif current is None or row["finding"].get("summary") is None:
        row["finding"]["gap_kind"] = computed if current is None else current
        row["finding"]["summary"] = generated_summary(latest_outcome, row["oos_evidence"], req_id, case_entry["case"]["name"], row["finding"]["gap_kind"])
    # else: hand-set gap kind and summary preserved verbatim
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", action="append", required=True)
    ap.add_argument("--existing")
    ap.add_argument("--out", required=True)
    ap.add_argument("--attempt-records-dir", action="append", default=[])
    ap.add_argument("--generated-at")
    args = ap.parse_args(argv)
    try:
        return merge(args)
    except RecordError as exc:
        print(f"[matrix_merge] REFUSED: {exc}", file=sys.stderr)
        return 2


def merge(args) -> int:
    matrix = load_json(args.existing) if args.existing else {"schema_version": 1, "generated_at": None, "catalogue": catalogue_identity(),
                                                             "rows": [], "accepted_exclusions": []}
    if matrix.get("catalogue", {}).get("hash") != catalogue_identity()["hash"]:
        print(f"[matrix_merge] note: existing matrix cites catalogue {matrix.get('catalogue', {}).get('hash')}, current is {catalogue_identity()['hash']}; rows keep their ids, the matrix header is updated")
    matrix["catalogue"] = catalogue_identity()
    rows_by_key = {}
    preserved = []
    hand_keys = set()      # hand-maintained rows that do name a case and a configuration
    for row in matrix["rows"]:
        if is_hand_maintained(row):
            preserved.append(row)  # verbatim: never regenerated, never merged into
            if row.get("case") is not None and row.get("configuration") is not None:
                hand_keys.add(row_key(row["requirement"], row["case"]["name"], row["configuration"]))
            continue
        rows_by_key[row_key(row["requirement"], row["case"]["name"], row["configuration"])] = row
    exclusions_present, exclusions_before = hand_maintained_list(matrix, "accepted_exclusions")
    withdrawn_present, withdrawn_before = hand_maintained_list(matrix, "withdrawn_claims")
    # Withdrawal, not preservation, and scoped to the cases the claim was withdrawn from
    # (ticket 42). `hand_maintained` says a human owns THIS row; it does not say a claim was
    # withdrawn, and reading it that way suppressed the first real case row of every caseless
    # placeholder -- OOS-REP-05/-/- among them, which is waiting for a case, not refusing one.
    withdrawn_pairs = {(entry["requirement"], case)
                       for entry in withdrawn_before for case in entry["cases"]}
    # A row id is not a marker. A `/claim-withdrawn` row with no entry behind it would otherwise
    # fall back to the requirement-scoped rule this replaces, so it is refused instead. The row is
    # caseless, so its requirement is the only key an entry can be matched on; the pair set is not
    # consulted here, because re-deriving requirement scope from it is the defect being removed.
    for row in preserved:
        if str(row.get("row_id", "")).endswith("/claim-withdrawn") and \
                not any(entry["requirement"] == row["requirement"] for entry in withdrawn_before):
            raise RecordError(
                f"row {row['row_id']} reads as a withdrawal but no withdrawn_claims entry names "
                f"{row['requirement']}; withdrawal is declared at matrix level and names the cases "
                f"it was withdrawn from (ticket 42), and a row id is never read as a marker")
    merged_attempts = 0
    for mpath in sorted(args.manifest):
        mpath = Path(mpath)
        manifest = load_json(mpath)
        if manifest.get("producer", {}).get("kind") not in ("wrapper", "hand-written"):
            raise RecordError(f"{mpath}: not a manifest")
        att_dirs = [Path(d) for d in args.attempt_records_dir] or [mpath.parent]
        for case_entry in manifest["cases"]:
            if case_entry["outcome"] is None:
                continue  # not executed: outstanding, no attempt, no row change
            for attempt in case_entry["attempts"]:
                att_path = None
                at = manifest["invocation"]["ended_at"]
                for d in att_dirs:
                    cand = d / f"{attempt['attempt_id']}.json"
                    if cand.exists():
                        att_path = cand
                        rec = load_json(cand)
                        if rec.get("kind") in ("checker-validation", "coexistence"):
                            raise RecordError(f"{cand}: {rec['kind']} attempts never reach the matrix")
                        at = rec.get("ended_at", at)
                        break
                att_rel = docs_relative(att_path) if att_path else attempt["attempt_record"]
                for req_id in case_entry["requirements"]:
                    if (req_id, case_entry["case"]["name"]) in withdrawn_pairs:
                        print(f"[matrix_merge] {manifest['manifest_id']}: {case_entry['case']['name']} cites {req_id}, whose claim a "
                              f"human withdrew from this case (withdrawn_claims); no row is created for the pair. Another case "
                              f"citing {req_id} is unaffected")
                        continue
                    cfg = {"page_size": manifest["invocation"]["page_size"], "build_mode": manifest["invocation"]["build_mode"],
                           "run_mode": manifest["invocation"]["run_mode"],
                           "instrumentation_id": (manifest["invocation"].get("instrumentation") or {}).get("patch_id")}
                    key = row_key(req_id, case_entry["case"]["name"], cfg)
                    if key in hand_keys:
                        print(f"[matrix_merge] {manifest['manifest_id']}: {case_entry['case']['name']} would merge into the "
                              f"hand-maintained row for {req_id}; it is preserved verbatim and no attempt is merged into it")
                        continue
                    row = rows_by_key.get(key)
                    if row is None:
                        row = new_row(req_id, case_entry, manifest, mpath, attempt["attempt_id"], att_rel, at)
                        rows_by_key[key] = row
                    if apply_attempt(row, req_id, case_entry, manifest, mpath, attempt, att_rel, at):
                        merged_attempts += 1
    # order: every existing row keeps its position (caseless rows included); new rows are appended
    ordered = []
    seen = set()
    for row in matrix["rows"]:
        if is_hand_maintained(row):
            ordered.append(row)
            continue
        k = row_key(row["requirement"], row["case"]["name"], row["configuration"])
        ordered.append(rows_by_key[k])
        seen.add(k)
    for k, row in rows_by_key.items():
        if k not in seen:
            ordered.append(row)
    matrix["rows"] = ordered
    for key, present, before in (("accepted_exclusions", exclusions_present, exclusions_before),
                                 ("withdrawn_claims", withdrawn_present, withdrawn_before)):
        if matrix.get(key, []) != before:
            raise RecordError(f"{key} changed during the merge; the tool must never write them")
        if present:
            matrix[key] = before
    matrix["generated_at"] = args.generated_at or now_iso()
    write_record(matrix, "matrix", args.out)
    print(f"[matrix_merge] merged {merged_attempts} attempt(s) from {len(args.manifest)} manifest(s); "
          f"{len(ordered) - len(preserved)} case row(s), {len(preserved)} hand-maintained row(s) preserved verbatim, "
          f"{len(exclusions_before)} accepted exclusion(s) and {len(withdrawn_before)} withdrawn claim(s) "
          f"preserved; wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
