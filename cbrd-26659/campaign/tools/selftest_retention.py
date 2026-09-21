#!/usr/bin/env python3
"""Self-test of shrink-not-delete retention (ticket 45 item 5, applied by ticket 46).

    selftest_retention.py [--keep DIR]

A passing bundle that reaches its expiry is demoted to its core, never deleted: `retention.py
expire --apply` removes what no index of the bundle directory names and keeps the fourteen
items, SHA256SUMS and the index, so the bundle hash is unchanged and no attempt record is
touched. These checks build synthetic bundles under a throwaway storage root beside the
campaign's (never inside it, so `admit` counts nothing here), point the tool's storage root and
protected prefixes at it, expire them, and assert what the rule owes. Every identifier carries
SELFTEST so nothing here can be mistaken for campaign evidence.

  1. the dry run (the default) lists the demotion and changes nothing;
  2. --apply on an expired success-bulky bundle: the bulk is gone, the item and SHA256SUMS are
     present, sha256(SHA256SUMS) is equal before and after, `complete` is still true, the
     attempt record is byte-identical (its `bundle` intact), the index is core-only with
     demoted_on;
  3. validate_records accepts the core-only index, and refuses it once SHA256SUMS is altered or
     the kept item is removed;
  4. a failure bundle is untouched (negative control);
  5. an expired bundle under a protected prefix is untouched (negative control);
  6. a bundle directory shared with a failure index is left whole and the passing index stays
     full (ticket 44 F3: one directory per invocation);
  7. a directory cited only by expired passing indexes is demoted once, keeping the union of
     their items, and every index is marked;
  8. a bundle whose directory is gone is recorded expired-by-policy: demoted_on and a note
     naming the directory, state not core-only, attempt record intact;
  9. a bundle whose enumerated item is gone is recorded expired-by-policy and nothing is
     deleted;
 10. a bundle whose SHA256SUMS does not hash to what its attempt record cites is refused and
     untouched;
 11. a second --apply is idempotent: core-only indexes are skipped and stay byte-identical;
 12. an unexpired passing bundle is untouched and unmentioned;
 13. the schema requires demoted_on on a core-only index.

Exit 0 when every check holds.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign_records import (  # noqa: E402
    SCHEMAS_DIR, STORAGE_ROOT, bundle_hash, bundle_total_bytes, load_json, sha256_prefixed, validate_record, write_record,
)
import retention  # noqa: E402
import validate_records  # noqa: E402

TODAY = "2026-09-19"
EXPIRED = {"class": "success-bulky", "expires_on": "2026-09-08", "hold_reason": None}
UNEXPIRED = {"class": "success-bulky", "expires_on": "2026-12-31", "hold_reason": None}
FAILURE = {"class": "failure", "expires_on": None, "hold_reason": "SELFTEST: non-PASS outcome, kept through triage"}
ITEMS = ["workload", "seed_and_generator_version", "session_and_barrier_trace", "injection_acknowledgements",
         "engine_identity", "testcase_identity", "specification_identity", "build_and_configuration_identity",
         "instrumentation_identity", "fixture_identity", "expected_versus_actual", "logs", "cores",
         "replay_command_with_prerequisites"]
BULK = {"home/db/SELFTEST_vol001": b"\0" * 65536, "home/db/SELFTEST_lgat": b"\0" * 4096,
        "ctp_result/summary.info": b"SELFTEST scratch\n", "scratch.log": b"SELFTEST scratch log\n"}
FAILS = []


def check(n, label, ok):
    print(("PASS  " if ok else "FAIL  ") + f"{n:<4}{label}")
    if not ok:
        FAILS.append(f"{n} {label}")


def make_bundle(root: Path, items: dict, bulk: bool = True) -> str:
    """Write the item files and the bulk, then seal with SHA256SUMS; return the bundle hash."""
    root.mkdir(parents=True)
    for rel, text in items.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    if bulk:
        for rel, data in BULK.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)
    return bundle_hash(root, write_sums=True)


def write_index(evd: Path, n: str, root: Path, present: dict, ret: dict) -> Path:
    """A schema-valid bundle index: `present` maps item name -> bundle-relative path."""
    items = {}
    for name in ITEMS:
        rel = present.get(name)
        if rel:
            items[name] = {"state": "present", "path": rel, "hash": sha256_prefixed(root / rel), "note": None}
        else:
            items[name] = {"state": "not-applicable", "path": None, "hash": None, "note": "SELFTEST: not applicable"}
    idx = {"schema_version": 1, "bundle_id": f"bundle-att-SELFTEST-{n}", "attempt_id": f"att-SELFTEST-{n}",
           "created_at": "2026-09-01T10:00:00+09:00", "root_path": str(root), "total_bytes": bundle_total_bytes(root),
           "complete": True, "items": items, "uncommitted_snapshots": [], "retention": dict(ret), "minimization": None}
    path = evd / f"bundle-att-SELFTEST-{n}.json"
    write_record(idx, "replay-bundle", path)
    return path


def write_attempt(evd: Path, n: str, root: Path, bundle_hash_value: str) -> Path:
    """The paired attempt record, shaped like the schemas' valid example, citing the bundle."""
    att = load_json(SCHEMAS_DIR / "examples" / "valid" / "attempt-record.example.json")
    att["attempt_id"] = f"att-SELFTEST-{n}"
    att["manifest_id"] = f"inv-SELFTEST-{n}"
    att["bundle"] = {"path": str(root), "hash": bundle_hash_value}
    att["notes"] = "SELFTEST attempt record; never campaign evidence"
    path = evd / f"att-SELFTEST-{n}.json"
    write_record(att, "attempt-record", path)
    return path


def expire(evd: Path, apply: bool) -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = retention.main(["expire", "--evidence", str(evd), "--today", TODAY] + (["--apply"] if apply else []))
    return f"rc={rc}\n" + out.getvalue()


def validate(*paths) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = validate_records.main([str(p) for p in paths] + ["--quiet"])
    return rc, out.getvalue()


def bulk_present(root: Path) -> bool:
    return all((root / rel).exists() for rel in BULK)


def bulk_absent(root: Path) -> bool:
    return not any((root / rel).exists() for rel in BULK) and not (root / "home").exists()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", help="directory to keep the synthetic bundles in (default: a temporary directory, removed)")
    args = ap.parse_args(argv)
    parent = STORAGE_ROOT.parent / "selftest"
    parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="selftest-retention-", dir=parent))
    tmp.mkdir(parents=True, exist_ok=True)
    # The tool's storage root, protected prefixes and default evidence tree are pointed at the
    # fixture, so nothing under the campaign's storage or evidence is read or written.
    retention.STORAGE_ROOT = tmp
    retention.PROTECTED_PREFIXES = (str(tmp / "protected") + "/",)
    retention.DEFAULT_EVIDENCE = tmp / "no-evidence"
    retention.DEFAULT_EVIDENCE.mkdir()
    try:
        return run(tmp)
    finally:
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)
            with contextlib.suppress(OSError):
                parent.rmdir()


def run(tmp: Path) -> int:
    evd = tmp / "evidence"
    cases = {}

    def case(n, subdir, root, present, ret, bulk=True, attempt_hash=None):
        d = evd / subdir
        d.mkdir(parents=True, exist_ok=True)
        h = make_bundle(root, {rel: f"SELFTEST item {rel}\n" for rel in present.values()}, bulk) \
            if not root.exists() else bundle_hash(root, write_sums=False)
        idx = write_index(d, n, root, present, ret)
        att = write_attempt(d, n, root, attempt_hash or h)
        cases[n] = {"root": root, "index": idx, "attempt": att, "hash": h,
                    "index_bytes": idx.read_bytes(), "attempt_bytes": att.read_bytes()}
        return cases[n]

    a = case("0001", "a", tmp / "bundles" / "inv-SELFTEST-A", {"workload": "workload.sql"}, EXPIRED)
    b = case("0002", "b", tmp / "bundles" / "inv-SELFTEST-B", {"workload": "workload.sql"}, FAILURE)
    c = case("0003", "c", tmp / "protected" / "inv-SELFTEST-C", {"workload": "workload.sql"}, EXPIRED)
    d1 = case("0004", "d", tmp / "bundles" / "inv-SELFTEST-D", {"workload": "workload/d1.sql"}, EXPIRED)
    (tmp / "bundles" / "inv-SELFTEST-D" / "workload" / "d2.sql").write_text("SELFTEST item d2\n")
    bundle_hash(d1["root"], write_sums=True)      # reseal with both items listed
    d2 = case("0005", "d", d1["root"], {"workload": "workload/d2.sql"}, FAILURE)
    d1["hash"] = d2["hash"]
    write_attempt(evd / "d", "0004", d1["root"], d2["hash"])
    # the first index was written before the directory was resealed with d2, so its total_bytes
    # described a bundle that no longer exists -- the very defect validate_records now
    # cross-checks (ticket 49 F2); the fixture must carry the finished directory's figures
    write_index(evd / "d", "0004", d1["root"], {"workload": "workload/d1.sql"}, EXPIRED)
    d1["attempt_bytes"] = d1["attempt"].read_bytes()
    d1["index_bytes"] = d1["index"].read_bytes()
    e = case("0006", "e", tmp / "bundles" / "inv-SELFTEST-E", {"workload": "workload.sql"}, EXPIRED)
    shutil.rmtree(e["root"])
    f = case("0007", "f", tmp / "bundles" / "inv-SELFTEST-F", {"workload": "workload.sql"}, EXPIRED)
    (f["root"] / "workload.sql").unlink()
    g = case("0008", "g", tmp / "bundles" / "inv-SELFTEST-G", {"workload": "workload.sql"}, UNEXPIRED)
    h1 = case("0009", "h", tmp / "bundles" / "inv-SELFTEST-H", {"workload": "workload/h1.sql", "logs": "logs/h.log"}, EXPIRED)
    (h1["root"] / "workload" / "h2.sql").write_text("SELFTEST item h2\n")
    bundle_hash(h1["root"], write_sums=True)
    h2 = case("0010", "h", h1["root"], {"workload": "workload/h2.sql", "logs": "logs/h.log"}, EXPIRED)
    h1["hash"] = h2["hash"]
    write_attempt(evd / "h", "0009", h1["root"], h2["hash"])
    write_index(evd / "h", "0009", h1["root"], {"workload": "workload/h1.sql", "logs": "logs/h.log"}, EXPIRED)
    h1["attempt_bytes"] = h1["attempt"].read_bytes()
    h1["index_bytes"] = h1["index"].read_bytes()
    j = case("0011", "j", tmp / "bundles" / "inv-SELFTEST-J", {"workload": "workload.sql"}, EXPIRED,
             attempt_hash="sha256:" + "0" * 64)

    def untouched(cs) -> bool:
        return cs["index"].read_bytes() == cs["index_bytes"] and cs["attempt"].read_bytes() == cs["attempt_bytes"]

    def sums_hash(cs) -> str:
        return sha256_prefixed(cs["root"] / "SHA256SUMS")

    # 1. the dry run
    dry = expire(evd, apply=False)
    check(1, "the dry run lists the demotion of the expired passing bundle and its bulk",
          "would demote" in dry and str(a["root"]) in dry and "home/" in dry and "rc=0" in dry)
    check("1b", "the dry run changes nothing: bulk present, every index and attempt record byte-identical",
          bulk_present(a["root"]) and all(untouched(cs) for cs in cases.values()))

    # 2. --apply on the expired passing bundle
    applied = expire(evd, apply=True)
    a_idx = load_json(a["index"])
    check(2, "--apply removed the bulk and kept the item and SHA256SUMS",
          bulk_absent(a["root"]) and (a["root"] / "workload.sql").exists() and (a["root"] / "SHA256SUMS").exists())
    check("2b", "the bundle hash (sha256 of SHA256SUMS) is equal before and after", sums_hash(a) == a["hash"])
    check("2c", "`complete` is still true and every item is as recorded",
          a_idx["complete"] is True and a_idx["items"] == json.loads(a["index_bytes"])["items"])
    check("2d", "the attempt record is byte-identical: `bundle` never nulled",
          a["attempt"].read_bytes() == a["attempt_bytes"] and load_json(a["attempt"])["bundle"]["hash"] == a["hash"])
    check("2e", "the index is core-only with demoted_on = today",
          a_idx["retention"]["state"] == "core-only" and a_idx["retention"]["demoted_on"] == TODAY
          and a_idx["retention"]["class"] == "success-bulky" and a_idx["retention"]["expires_on"] == EXPIRED["expires_on"])
    check("2f", "the run output says what it did, per bundle and in total",
          "DEMOTE" in applied and "core-only, demoted_on 2026-09-19" in applied and "demoted to core-only" in applied
          and "no attempt record touched" in applied)

    # 3. the validator on the demoted index
    rc, out = validate(evd / "a")
    check(3, "validate_records accepts the core-only index and its attempt record", rc == 0 and "0 failing" in out)
    sums = a["root"] / "SHA256SUMS"
    original = sums.read_bytes()
    sums.write_bytes(original + b"0" * 64 + b"  SELFTEST_extra\n")
    rc, out = validate(evd / "a")
    check("3b", "a core-only index whose SHA256SUMS no longer hashes as the attempt record cites is refused",
          rc == 1 and "the attempt record" in out and "cites" in out)
    sums.write_bytes(original)
    item = a["root"] / "workload.sql"
    item_bytes = item.read_bytes()
    item.unlink()
    rc, out = validate(evd / "a")
    check("3c", "a core-only index whose kept item is gone is refused", rc == 1 and "does not exist" in out)
    item.write_bytes(item_bytes)
    rc, _ = validate(evd / "a")
    check("3d", "restored, it validates again", rc == 0)

    # 4, 5. negative controls
    check(4, "a failure bundle is untouched: bulk present, index and attempt record byte-identical",
          bulk_present(b["root"]) and untouched(b))
    check(5, "an expired bundle under a protected prefix is untouched and reported PROTECTED",
          bulk_present(c["root"]) and untouched(c) and "PROTECTED" in applied and str(c["root"]) in applied)

    # 6. a directory shared with a failure index
    check(6, "a directory shared with a failure index is left whole and the passing index stays full",
          bulk_present(d1["root"]) and untouched(d1) and untouched(d2)
          and "shared with bundle-att-SELFTEST-0005 (failure bundle awaiting triage)" in applied)

    # 7. a directory shared by two expired passing indexes
    h1_idx, h2_idx = load_json(h1["index"]), load_json(h2["index"])
    check(7, "a directory cited only by expired passing indexes is demoted once, keeping the union of their items",
          bulk_absent(h1["root"]) and (h1["root"] / "workload" / "h1.sql").exists()
          and (h1["root"] / "workload" / "h2.sql").exists() and (h1["root"] / "logs" / "h.log").exists()
          and sums_hash(h1) == h1["hash"] and applied.count(str(h1["root"]) + " to core-only") == 1)
    check("7b", "every index of that directory is marked core-only",
          h1_idx["retention"]["state"] == "core-only" and h2_idx["retention"]["state"] == "core-only"
          and h1["attempt"].read_bytes() == h1["attempt_bytes"] and h2["attempt"].read_bytes() == h2["attempt_bytes"])

    # 8, 9. expired-by-policy
    e_idx = load_json(e["index"])
    check(8, "a bundle whose directory is gone is recorded expired-by-policy, hash kept, attempt record intact",
          e_idx["retention"]["demoted_on"] == TODAY and e_idx["retention"].get("state", "full") == "full"
          and "does not exist" in (e_idx["retention"]["hold_reason"] or "")
          and e_idx["items"] == json.loads(e["index_bytes"])["items"] and e["attempt"].read_bytes() == e["attempt_bytes"])
    f_idx = load_json(f["index"])
    check(9, "a bundle whose enumerated item is gone is recorded expired-by-policy and nothing is deleted",
          f_idx["retention"]["demoted_on"] == TODAY and "workload.sql" in (f_idx["retention"]["hold_reason"] or "")
          and f_idx["retention"].get("state", "full") == "full" and bulk_present(f["root"])
          and f["attempt"].read_bytes() == f["attempt_bytes"])

    # 10. a hash that does not verify
    check(10, "a bundle whose SHA256SUMS does not hash to what its attempt record cites is refused and untouched",
          "REFUSED" in applied and "bundle-att-SELFTEST-0011" in applied and bulk_present(j["root"]) and untouched(j))

    # 11. idempotence
    snapshot = {n: cs["index"].read_bytes() for n, cs in cases.items()}
    again = expire(evd, apply=True)
    check(11, "a second --apply skips the core-only indexes and rewrites nothing",
          all(cs["index"].read_bytes() == snapshot[n] for n, cs in cases.items())
          and "0 bundle directories demoted" in again and "DEMOTE" not in again)

    # 12. an unexpired passing bundle
    check(12, "an unexpired passing bundle is untouched and unmentioned",
          bulk_present(g["root"]) and untouched(g) and "SELFTEST-0008" not in applied and "SELFTEST-0008" not in dry)

    # 13. the schema
    bad = json.loads(a["index"].read_text())
    del bad["retention"]["demoted_on"]
    check(13, "the schema requires demoted_on on a core-only index",
          any("demoted_on" in err for err in validate_record(bad, "replay-bundle")))
    rc, out = validate(evd)
    # Three reports, all planted: F's item loss (its index, twice: the item check and, since
    # ticket 49 F2, the finished-bundle cross-check on its total_bytes) and J's attempt record,
    # whose digest is the zero digest the hash-mismatch control plants (check 10).
    check("13b", "the whole fixture still validates apart from the planted item loss (F) the rule recorded and the "
                 "planted digest mismatch (J) the cross-check reports",
          rc == 1 and out.count("[FAIL]") == 3 and out.count("bundle-att-SELFTEST-0007") == 2
          and "att-SELFTEST-0011.json (bundle cross-check)" in out)

    print(f"[selftest_retention] {len(FAILS)} failing check(s); files under {tmp}")
    for fl in FAILS:
        print("  " + fl)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
