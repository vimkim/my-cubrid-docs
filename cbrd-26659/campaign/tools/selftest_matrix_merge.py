#!/usr/bin/env python3
"""Self-test of the matrix merge rules with synthetic manifests (ticket 15 criterion 4).

    selftest_matrix_merge.py [--keep DIR]

Every identifier carries SELFTEST so nothing here can be mistaken for campaign evidence.
The manifests are built from schemas/examples/valid/manifest.example.json (ticket 12's own
valid example) with the outcome, attempt ids and timestamps changed, and are validated
before use. The checks, each one rule the merge must add beyond the schema:

  1. a FAIL followed by a PASS keeps both in history, ever_failed stays true, latest is PASS,
     flakiness counts 2 attempts / 1 failure / intermittent, and gap_kind is not `none` while
     ever_failed rows carry an untriaged FAIL (the tool never writes none over a FAIL history
     without a hand-set classification);
  2. a PASS followed by a FAIL moves gap_kind off `none` and keeps the earlier PASS;
  3. merging the same manifest twice changes nothing (idempotent);
  4. accepted_exclusions and caseless rows in an existing matrix come out verbatim;
  5. a hand-set gap kind (Delivery gap) on a row that keeps passing is preserved, never
     upgraded to `none`;
  6. a checker-validation attempt record beside a manifest is refused.

Exit 0 when every check holds.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign_records import SCHEMAS_DIR, load_json, validate_record, write_record  # noqa: E402
import matrix_merge  # noqa: E402

EXAMPLE = SCHEMAS_DIR / "examples" / "valid" / "manifest.example.json"


def make_manifest(tmp: Path, mid: str, attempt_id: str, outcome: str, ended: str, evidence="proven") -> Path:
    m = copy.deepcopy(load_json(EXAMPLE))
    m["manifest_id"] = mid
    m["invocation"]["started_at"] = ended
    m["invocation"]["ended_at"] = ended
    c = m["cases"][0]
    c["case"]["name"] = "SELFTEST_case"
    c["outcome"] = outcome
    c["skip_reason"] = "SELFTEST skip" if outcome == "SKIP" else None
    c["oos_evidence"]["status"] = evidence
    if evidence != "reused":
        c["oos_evidence"]["applicability"] = None
    c["attempts"] = [{"attempt_id": attempt_id, "attempt_record": f"SELFTEST/{attempt_id}.json", "bundle": None, "bundle_hash": None}]
    c["requirements"] = ["OOS-REP-02"]
    c["outstanding"] = None
    errors = validate_record(m, "manifest")
    assert not errors, errors
    p = tmp / f"{mid}.json"
    p.write_text(json.dumps(m, indent=1))
    return p


def merge(tmp: Path, manifests, existing=None, out="matrix.json"):
    argv = []
    for m in manifests:
        argv += ["--manifest", str(m)]
    if existing:
        argv += ["--existing", str(existing)]
    argv += ["--out", str(tmp / out), "--generated-at", "2026-09-11T23:00:00+09:00"]
    rc = matrix_merge.main(argv)
    assert rc == 0, f"merge failed ({rc})"
    return load_json(tmp / out)


def row(matrix, req="OOS-REP-02"):
    rows = [r for r in matrix["rows"] if r["requirement"] == req and r["case"] is not None]
    assert len(rows) == 1, [r["row_id"] for r in matrix["rows"]]
    return rows[0]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", help="directory to keep the synthetic files in (default: a temporary directory)")
    args = ap.parse_args(argv)
    tmp = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="selftest-matrix-"))
    tmp.mkdir(parents=True, exist_ok=True)
    fails = []

    def check(label, cond):
        print(("PASS  " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    m_fail = make_manifest(tmp, "inv-SELFTEST-01", "att-SELFTEST-01", "FAIL", "2026-09-11T10:00:00+09:00", evidence="missing")
    m_pass = make_manifest(tmp, "inv-SELFTEST-02", "att-SELFTEST-02", "PASS", "2026-09-11T11:00:00+09:00")
    # 1. FAIL then PASS
    mx = merge(tmp, [m_fail, m_pass], out="m1.json")
    r = row(mx)
    check("1a history keeps both attempts in time order", [h["attempt_id"] for h in r["finding"]["history"]] == ["att-SELFTEST-01", "att-SELFTEST-02"])
    check("1b ever_failed stays true after a later PASS", r["finding"]["ever_failed"] is True)
    check("1c latest_outcome is PASS", r["finding"]["latest_outcome"] == "PASS")
    check("1d flakiness 2 attempts / 1 failure / intermittent", (r["flakiness"]["attempts"], r["flakiness"]["failures"], r["flakiness"]["intermittent"]) == (2, 1, True))
    check("1e run points at the latest manifest", r["run"]["manifest_id"] == "inv-SELFTEST-02")
    # 2. PASS then FAIL: gap kind moves off none; a later FAIL never erases the PASS either
    mx2 = merge(tmp, [m_pass], out="m2a.json")
    r2 = row(mx2)
    check("2a a PASS with proven evidence starts at gap_kind none", r2["finding"]["gap_kind"] == "none")
    m_fail_later = make_manifest(tmp, "inv-SELFTEST-03", "att-SELFTEST-03", "FAIL", "2026-09-11T12:00:00+09:00", evidence="missing")
    mx2b = merge(tmp, [m_fail_later], existing=tmp / "m2a.json", out="m2b.json")
    r2b = row(mx2b)
    check("2b a later FAIL moves gap_kind off none", r2b["finding"]["gap_kind"] != "none")
    check("2c the earlier PASS stays in history", [h["outcome"] for h in r2b["finding"]["history"]] == ["PASS", "FAIL"])
    check("2d an untriaged FAIL is not classified as Engine defect", r2b["finding"]["gap_kind"] != "Engine defect" and "UNTRIAGED" in r2b["finding"]["summary"])
    # 3. idempotent
    mx3 = merge(tmp, [m_fail, m_pass], existing=tmp / "m1.json", out="m3.json")
    a, b = load_json(tmp / "m1.json"), mx3
    a.pop("generated_at"); b.pop("generated_at")
    check("3  merging the same manifests again changes nothing", a == b)
    # 4. accepted exclusions and caseless rows preserved verbatim
    ex = load_json(SCHEMAS_DIR / "examples" / "valid" / "matrix.example.json")
    seed = copy.deepcopy(mx)
    seed["accepted_exclusions"] = ex["accepted_exclusions"]
    caseless = copy.deepcopy(seed["rows"][0])
    caseless.update({"row_id": "OOS-REP-05/-/SELFTEST-caseless", "requirement": "OOS-REP-05", "case": None, "configuration": None, "run": None,
                     "oos_evidence": {"status": "missing", "channel": None, "reference": None, "applicability": None},
                     "finding": {"latest_outcome": None, "ever_failed": False, "history": [], "gap_kind": "Delivery gap", "summary": "SELFTEST caseless row"},
                     "flakiness": {"attempts": 0, "failures": 0, "intermittent": False, "consecutive_fresh_fixture_reproductions": 0, "deterministic_claim": False},
                     "attempt_records": []})
    seed["rows"].insert(0, caseless)
    write_record(seed, "matrix", tmp / "seed.json")
    mx4 = merge(tmp, [m_pass], existing=tmp / "seed.json", out="m4.json")
    check("4a accepted_exclusions come out verbatim", mx4["accepted_exclusions"] == ex["accepted_exclusions"])
    check("4b the caseless row comes out verbatim and in place", mx4["rows"][0] == caseless)
    # 5. hand-set gap kind preserved while the row keeps passing
    seed5 = copy.deepcopy(mx2)
    r5 = row(seed5)
    r5["finding"]["gap_kind"] = "Delivery gap"
    r5["finding"]["summary"] = "HAND-SET: one clause is evidenced only by a checker outside every executed suite"
    write_record(seed5, "matrix", tmp / "seed5.json")
    m_pass2 = make_manifest(tmp, "inv-SELFTEST-04", "att-SELFTEST-04", "PASS", "2026-09-11T13:00:00+09:00")
    mx5 = merge(tmp, [m_pass2], existing=tmp / "seed5.json", out="m5.json")
    r5b = row(mx5)
    check("5a a hand-set Delivery gap survives a later PASS (never upgraded to none)", r5b["finding"]["gap_kind"] == "Delivery gap")
    check("5b the hand-written summary survives", r5b["finding"]["summary"].startswith("HAND-SET"))
    check("5c the later PASS was still appended", len(r5b["finding"]["history"]) == 2)
    # 6. checker-validation attempts are refused
    att = copy.deepcopy(load_json(SCHEMAS_DIR / "examples" / "valid" / "attempt-record.example.json"))
    att["attempt_id"] = "att-SELFTEST-02"
    att["kind"] = "checker-validation"
    att["manifest_id"] = "none: SELFTEST"
    (tmp / "att-SELFTEST-02.json").write_text(json.dumps(att, indent=1))
    rc = matrix_merge.main(["--manifest", str(m_pass), "--attempt-records-dir", str(tmp), "--out", str(tmp / "m6.json")])
    check("6  a checker-validation attempt record is refused by the merge", rc != 0)
    print(f"[selftest_matrix_merge] {len(fails)} failing check(s); files under {tmp}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
