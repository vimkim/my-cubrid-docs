#!/usr/bin/env python3
"""Validate any ticket's campaign records against ticket 12's schemas (ticket 15).

    validate_records.py PATH [PATH ...] [--schema-only] [--quiet]

PATH is a directory (searched recursively for inv-*.json, att-*.json, bundle-*.json and
matrix*.json) or a single record. Generalised from evidence/ticket14/tools/validate_records.py,
which knew only ticket 14's directory. Records are classified by content (manifest_id,
attempt_id, bundle_id, rows) and validated with the same minischema evaluator that judges the
schemas' own examples, so a ticket's records are judged by exactly the code that judges the
examples. tools/check_campaign_records.py is still needed for the catalogue, the schemas and
their examples; it never looks at a ticket's records.

Beyond the schema, the rules a schema cannot express (ticket 12 section 3) are checked unless
--schema-only is given:

  manifest       proof.verdict is failure-of-proof iff proof.mismatches is non-empty; a case
                 with outcome null has outstanding set and vice versa; every SKIP has a reason;
                 configurations_not_run has no duplicates and stays inside the 12-combination
                 domain; requirement ids exist in the catalogue; the engine's library hashes
                 name a build the campaign knows -- the current one or the superseded ticket 11
                 one, which stays recognised for replaying the records that cite it.
  attempt        checker-validation and coexistence attempts name no real manifest; a reached
                 deadline is not PASS (also schema-enforced); requirement ids exist.
  bundle         complete equals "no item is missing"; a success-bulky bundle has an expiry;
                 when the bundle root exists, every present item's path exists under it and
                 its hash matches the file. A core-only index (demoted by retention.py expire,
                 ticket 45 item 5) must still have its root and SHA256SUMS, SHA256SUMS must
                 still list every present item with the hash the index records, and the bundle
                 hash the paired attempt record cites must still be sha256(SHA256SUMS).
  cross-check    for every bundle index whose root_path exists (ticket 49 F2): sha256 of its
                 SHA256SUMS -- or, for a bundle sealed without one, the digest of the listing
                 the convention would write -- equals the hash EVERY attempt record citing that
                 root carries, and a full (not core-only) bundle's total_bytes equals the sum of
                 its regular files. A digest that verifies against nothing was taken while the
                 invocation's shared bundle was still being written (ticket 44 F3). Bundles under
                 retention.py's protected prefixes were sealed under an older convention (tickets
                 13 and 14) and stay as recorded (ticket 36 item 1): they are reported as notes,
                 never failed and never corrected.
  matrix         gap_kind none only for latest PASS with proven or reused evidence;
                 ever_failed is true iff history has a FAIL; flakiness.attempts equals the
                 history length and failures the FAIL count; caseless rows have an empty
                 history and a null outcome; accepted exclusions are dated and user-accepted.

Exit 0 when everything passes, 1 otherwise. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign_records import (  # noqa: E402
    BUILD_MODES, PAGE_SIZES, RUN_MODES, bundle_hash, bundle_total_bytes, load_catalogue, load_json, recognised_build,
    sha256_prefixed, sha256sums_entries, validate_record,
)
from retention import PROTECTED_PREFIXES  # noqa: E402

VALID_CONFIGS = {f"{p}/{b}/{r}" for p in PAGE_SIZES for b in BUILD_MODES for r in RUN_MODES}


def classify(rec: dict):
    if "manifest_id" in rec and "invocation" in rec:
        return "manifest"
    if "attempt_id" in rec and "kind" in rec:
        return "attempt-record"
    if "bundle_id" in rec and "items" in rec:
        return "replay-bundle"
    if "rows" in rec and "accepted_exclusions" in rec:
        return "matrix"
    return None


def rule_checks(kind, rec, path: Path, known_reqs: set) -> list:
    errs = []
    if kind == "manifest":
        p = rec["proof"]
        if (p["verdict"] == "failure-of-proof") != bool(p["mismatches"]):
            errs.append(f"proof.verdict {p['verdict']} disagrees with {len(p['mismatches'])} mismatch(es)")
        for c in rec["cases"]:
            if (c["outcome"] is None) != (c["outstanding"] is not None):
                errs.append(f"case {c['case']['name']}: outcome null must pair with outstanding")
            if c["outcome"] == "SKIP" and not c.get("skip_reason"):
                errs.append(f"case {c['case']['name']}: SKIP without reason")
            if c["oos_evidence"]["status"] == "reused" and not c["oos_evidence"]["applicability"]:
                errs.append(f"case {c['case']['name']}: reused evidence without applicability")
            for r in c["requirements"]:
                if r not in known_reqs:
                    errs.append(f"case {c['case']['name']}: unknown requirement {r}")
        cnr = rec["outstanding_coverage"]["configurations_not_run"]
        if len(set(cnr)) != len(cnr):
            errs.append("configurations_not_run has duplicates")
        for cfg in cnr:
            if cfg not in VALID_CONFIGS:
                errs.append(f"configurations_not_run entry {cfg!r} is outside the 12-combination domain")
        if p["verdict"] == "proven" and rec["executed"]["case_count"] != rec["expected"]["case_count"]:
            errs.append("proven verdict but executed.case_count differs from expected.case_count")
        # The engine a manifest cites must be a build the campaign can name: the current one
        # (ticket 41) or the superseded ticket 11 one, which stays recognised so the records
        # written against it still resolve when their bundles are replayed. Anything else is an
        # engine nobody can identify, and the manifest's identity proves nothing.
        engine = rec["invocation"]["engine"]
        if recognised_build(rec["invocation"]["build_mode"], engine["library_hashes"]) is None:
            errs.append(f"engine library hashes match neither the campaign's {rec['invocation']['build_mode']} build "
                        f"nor the superseded ticket 11 one: {engine['install_prefix']}")
    elif kind == "attempt-record":
        if rec["kind"] in ("checker-validation", "coexistence") and not str(rec["manifest_id"]).startswith("none"):
            errs.append(f"{rec['kind']} attempt names manifest {rec['manifest_id']!r}; it must have none")
        if rec["deadline"]["reached"] and rec["outcome"] == "PASS":
            errs.append("deadline reached but outcome PASS")
        for r in rec["requirements"]:
            if r not in known_reqs:
                errs.append(f"unknown requirement {r}")
        if rec["outcome"] == "SKIP" and not rec.get("skip_reason"):
            errs.append("SKIP without reason")
    elif kind == "replay-bundle":
        missing = [k for k, v in rec["items"].items() if v["state"] == "missing"]
        if rec["complete"] != (not missing):
            errs.append(f"complete={rec['complete']} but missing items: {missing}")
        ret = rec["retention"]
        if ret["class"] == "success-bulky" and not ret["expires_on"]:
            errs.append("success-bulky bundle without expires_on")
        root = Path(rec["root_path"])
        if ret.get("state") == "core-only":
            # A demoted bundle keeps exactly its core (ticket 45 item 5): the root and SHA256SUMS
            # are still there, every present item still hashes as recorded (checked below with
            # every other bundle), SHA256SUMS still lists the items with those hashes, and the
            # bundle hash the attempt record beside this index cites is still sha256(SHA256SUMS).
            if ret["class"] != "success-bulky":
                errs.append(f"core-only state on a {ret['class']} bundle; only success-bulky bundles are demoted")
            if not ret.get("demoted_on"):
                errs.append("core-only without demoted_on")
            if not root.exists():
                errs.append(f"core-only bundle but its root {root} does not exist")
            elif not (root / "SHA256SUMS").exists():
                errs.append("core-only bundle without SHA256SUMS")
            else:
                listed = sha256sums_entries(root / "SHA256SUMS")
                for k, v in rec["items"].items():
                    if v["state"] == "present" and v.get("path") and v.get("hash") \
                            and listed.get(v["path"]) != v["hash"].split(":")[-1]:
                        errs.append(f"item {k}: SHA256SUMS no longer lists {v['path']} with the hash the index records")
                att = path.parent / f"{rec['attempt_id']}.json"
                if att.exists():
                    cited = (load_json(att).get("bundle") or {}).get("hash")
                    got = sha256_prefixed(root / "SHA256SUMS")
                    if cited and cited != got:
                        errs.append(f"SHA256SUMS hashes {got}; the attempt record {att.name} cites {cited}")
        if root.exists():
            for k, v in rec["items"].items():
                if v["state"] == "present" and v.get("path"):
                    f = root / v["path"]
                    if not f.exists():
                        errs.append(f"item {k}: path {v['path']} does not exist under {root}")
                    elif f.is_file() and v.get("hash") and sha256_prefixed(f) != v["hash"]:
                        errs.append(f"item {k}: hash of {v['path']} differs from the index")
    elif kind == "matrix":
        for row in rec["rows"]:
            f = row["finding"]
            hist = f["history"]
            ev = row["oos_evidence"]["status"]
            if f["gap_kind"] == "none" and not (f["latest_outcome"] == "PASS" and ev in ("proven", "reused")):
                errs.append(f"row {row['row_id']}: gap_kind none but latest {f['latest_outcome']} with evidence {ev}")
            if f["ever_failed"] != any(h["outcome"] == "FAIL" for h in hist):
                errs.append(f"row {row['row_id']}: ever_failed disagrees with history")
            if row["flakiness"]["attempts"] != len(hist):
                errs.append(f"row {row['row_id']}: flakiness.attempts {row['flakiness']['attempts']} != history length {len(hist)}")
            if row["flakiness"]["failures"] != sum(1 for h in hist if h["outcome"] == "FAIL"):
                errs.append(f"row {row['row_id']}: flakiness.failures disagrees with history")
            if row["case"] is None and (hist or f["latest_outcome"] is not None):
                errs.append(f"row {row['row_id']}: caseless row with history or outcome")
            if hist and f["latest_outcome"] != sorted(hist, key=lambda h: h["at"])[-1]["outcome"]:
                errs.append(f"row {row['row_id']}: latest_outcome is not the outcome of the latest history entry")
            if row["requirement"] not in known_reqs:
                errs.append(f"row {row['row_id']}: unknown requirement")
        for ex in rec["accepted_exclusions"]:
            if ex.get("accepted_by") != "user" or not ex.get("date"):
                errs.append("accepted exclusion without date or not accepted by the user")
    return errs


def cross_check_bundles(attempts: list, indexes: list) -> tuple:
    """Ticket 49 F2: every record citing an existing bundle root carries the finished bundle's digest.

    `attempts` is [(path, record)] of every attempt record validated in this run and `indexes`
    [(path, record)] of every bundle index. The truth for a root is sha256 of its SHA256SUMS; a
    bundle sealed without one (a read-only regeneration) is judged by the digest the convention
    would write, computed in memory. Ticket 17 wrote eight records of `inv-T17-0002` -- and
    ticket 47 eight of `inv-T47-0001` -- while the shared root was still growing, so their hash
    and `total_bytes` described no bundle that ever existed; the schema could not see it because
    the numbers were well-formed. Returns (failures, notes): a failure is [(path, message)]; a
    note is the same for a root under a protected prefix, whose records are sealed evidence of an
    older hash convention and stay as recorded (ticket 36 item 1).
    """
    truth: dict = {}

    def digest_of(root: Path):
        key = str(root)
        if key not in truth:
            sums = root / "SHA256SUMS"
            truth[key] = sha256_prefixed(sums) if sums.exists() else bundle_hash(root, write_sums=False)
        return truth[key]

    def protected(root: Path) -> bool:
        return any(str(root).startswith(p) for p in PROTECTED_PREFIXES)

    failures, notes = [], []

    def report(root: Path, path: Path, message: str):
        (notes if protected(root) else failures).append((path, message))

    for path, rec in attempts:
        bundle = rec.get("bundle") or {}
        root = Path(bundle.get("path") or "")
        if not bundle or not root.is_dir():
            continue
        got = digest_of(root)
        if bundle.get("hash") != got:
            report(root, path, f"cites bundle hash {bundle.get('hash')} for {root}, whose finished bundle hashes {got}: "
                               "a digest that verifies against nothing (ticket 44 F3: sealed once, after the last file)")
    for path, rec in indexes:
        root = Path(rec["root_path"])
        if not root.is_dir():
            continue
        if (rec.get("retention") or {}).get("state") == "core-only":
            continue  # its bulk is gone by design; the hash check above still holds through SHA256SUMS
        total = bundle_total_bytes(root)
        if rec["total_bytes"] != total:
            report(root, path, f"total_bytes {rec['total_bytes']} but the finished bundle's regular files sum to {total} "
                               "(ticket 44 F3: the size is the finished bundle's)")
    return failures, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--schema-only", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    known = {r["id"] for r in load_catalogue()["requirements"]}
    files = []
    for p in args.paths:
        p = Path(p)
        if p.is_dir():
            for pat in ("inv-*.json", "att-*.json", "bundle-*.json", "matrix*.json"):
                files += sorted(p.rglob(pat))
        else:
            files.append(p)
    if not files:
        print("no records found")
        return 1
    failures = 0
    counts = {}
    attempts, indexes = [], []
    for f in files:
        try:
            rec = json.loads(f.read_text())
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {f}: not JSON ({exc})")
            failures += 1
            continue
        kind = classify(rec)
        if kind is None:
            print(f"[SKIP] {f}: not a campaign record")
            continue
        if kind == "attempt-record":
            attempts.append((f, rec))
        elif kind == "replay-bundle":
            indexes.append((f, rec))
        errors = validate_record(rec, kind)
        if not args.schema_only:
            errors += rule_checks(kind, rec, f, known)
        counts[kind] = counts.get(kind, 0) + 1
        if errors:
            failures += 1
            print(f"[FAIL] {f} ({kind})")
            for e in errors:
                print(f"       {e}")
        elif not args.quiet:
            print(f"[ OK ] {f} ({kind})")
    if not args.schema_only:
        cross_failures, cross_notes = cross_check_bundles(attempts, indexes)
        for f, message in cross_failures:
            print(f"[FAIL] {f} (bundle cross-check)\n       {message}")
        for f, message in cross_notes:
            print(f"[NOTE] {f} (bundle cross-check, protected prefix, sealed as recorded)\n       {message}")
        failures += len(cross_failures)
        print(f"[validate_records] bundle cross-check: {len(attempts)} attempt record(s) and {len(indexes)} bundle index(es) "
              f"read; {len(cross_failures)} failing; {len(cross_notes)} note(s) on protected prefixes")
    print(f"[validate_records] {sum(counts.values())} record(s) checked ({', '.join(f'{v} {k}' for k, v in sorted(counts.items()))}); {failures} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
