#!/usr/bin/env python3
"""Correct the two claims ticket 19's sealed records make that the artifacts do not bear out.

    apply_ticket44_record_corrections.py [--dry-run]

**F3, the bundle hashes.**

Nine attempts of an invocation share one bundle directory, and each attempt record's
`bundle.hash` was written as that directory's digest at the moment the record was written --
while the directory was still growing.  Only the last attempt written per invocation recorded
the digest the finished bundle has.  Across ticket 19's tree that is 19 records right and 64
wrong; `total_bytes` in the matching replay-bundle indexes and `bundle_hash` in the manifests'
attempt entries carry the same 64 wrong numbers, because all three were written from the same
call.

The bundles themselves are sound: `sha256sum -c SHA256SUMS` passes on every one of them, and
the hash convention is implemented correctly.  What was wrong is the contract -- the
specification says "Each attempt retains one replay bundle" and the implementation gives nine
attempts one bundle -- and the user settled it on 2026-09-16 the way the artifacts already
are: **one bundle per invocation, one hash, referenced by its attempt records** (ticket 44 F3,
recorded in the traceability-schemas change log).

**F7, the oracle's provenance.** All 24 promotion reviewer notes -- eight in `promotions.json`
and the eight each that `inv-T19-0004` and `inv-T19-0009` copied from it -- say the oracle "was
written before any CTP invocation of these cases".  It was, but nothing in the artifacts can
show it: `expected-oracle.md` is sealed in no replay bundle and was first committed in `27dee8b`,
after every run.  A promotion record that rests on an unfalsifiable claim is weaker than one that
rests on a checkable one, and there is a checkable one in the same sentence -- the derivation
reproduces every promoted answer's `(length, digest)` pairs in Python without the engine, which
the independent review re-ran.  The clause is removed and the record says it was removed and why.
Sealing the oracle in a future bundle is the other half and belongs to the next invocation that
runs; no CTP invocation is made here.

Four phases, each re-derived from its source rather than patched:

1. every attempt record whose `bundle.hash` disagrees with the finished bundle, and the
   replay-bundle index beside it, take the finished bundle's digest and size.  The attempt
   record's `notes` say it was corrected and what it used to say, so nothing is re-hashed
   silently;
2. the manifests' per-attempt `bundle_hash` takes the same value.  A manifest and its attempt
   record agreeing on a wrong number is one defect; disagreeing would be two;
3. the 24 promotion reviewer notes drop the unfalsifiable clause and say so;
4. every matrix row whose `run.manifest_hash` seals a manifest phase 2 or 3 rewrote takes that
   manifest's new file hash.  The run did not change, the record of it was corrected, and a
   seal that no longer matches the file it seals is worse than no seal.

No bundle is modified: `bundle_hash` is computed in memory.  A record that already matches is
left alone, so this script is idempotent and reports what it did.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parents[1]
DOCS_ROOT = CAMPAIGN.parents[1]
sys.path.insert(0, str(CAMPAIGN / "tools"))
from campaign_records import (  # noqa: E402
    RecordError, bundle_hash, bundle_total_bytes, sha256_prefixed, write_record,
)

CORRECTION_MARK = "BUNDLE HASH CORRECTED by ticket 44 F3"
MATRIX = HERE / "matrix.json"


def truth(root: str, cache: dict) -> tuple:
    if root not in cache:
        path = Path(root)
        if not path.is_dir():
            raise RecordError(f"bundle root {root} does not exist; nothing can be corrected against it")
        cache[root] = (bundle_hash(path, write_sums=False), bundle_total_bytes(path))
    return cache[root]


def correction_note(old_hash: str, old_bytes, new_hash: str, new_bytes: int) -> str:
    """What this record used to say, naming only what actually changed.

    A record can be wrong in the hash, in `total_bytes`, or in both: the three numbers were
    written from one call, but a file that arrived between two attempts changes the size of the
    listing as well as its digest, and an attempt whose digest happened to be taken after the
    last file can still carry a size from before it.  A note that claimed a digest was replaced
    by itself would be a second false record, not a correction of the first.
    """
    parts = []
    if old_hash != new_hash:
        parts.append(f"the recorded digest {old_hash} is replaced by the finished bundle's {new_hash}")
    if old_bytes != new_bytes:
        parts.append(f"the replay-bundle index's total_bytes {old_bytes} is replaced by {new_bytes}")
    if not parts:
        raise RecordError("refusing to write a correction note for a record that changed nothing")
    return (
        f" {CORRECTION_MARK} on 2026-09-16: " + "; and ".join(parts) + ". Both were taken while this "
        "invocation's shared bundle directory was still being written, so they described no bundle that ever "
        "existed on disk. The bundle is unchanged and was not re-hashed silently: the new digest is the sha256 "
        "of the SHA256SUMS the bundle carries, which `sha256sum -c` verifies, and the new size is the sum of "
        "the files it lists. One bundle per invocation, referenced by its attempt records, is the contract the "
        "user settled on 2026-09-16 (ticket 44 F3)."
    )


def correct_attempt_records(cache, dry_run) -> tuple:
    corrected, already = [], 0
    for path in sorted(HERE.glob("att-*.json")) + sorted((HERE / "controls").glob("att-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        bundle = record.get("bundle")
        if not bundle:
            continue
        new_hash, new_bytes = truth(bundle["path"], cache)
        index_path = path.with_name(f"bundle-{path.name}")
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else None
        # read both old values out before anything is written: `bundle` is `record["bundle"]`
        old_hash = bundle["hash"]
        old_bytes = index["total_bytes"] if index else new_bytes
        if old_hash == new_hash and old_bytes == new_bytes:
            already += 1
            continue
        if CORRECTION_MARK in (record.get("notes") or ""):
            raise RecordError(f"{path.name} says it was already corrected but still disagrees with the bundle; "
                             "reconcile by hand rather than layering a second correction")
        note = correction_note(old_hash, old_bytes, new_hash, new_bytes)
        bundle["hash"] = new_hash
        record["notes"] = (record.get("notes") or "").rstrip() + note
        if index is not None:
            index["total_bytes"] = new_bytes
        if not dry_run:
            write_record(record, "attempt-record", path)
            if index is not None:
                write_record(index, "replay-bundle", index_path)
        corrected.append(path.name)
    return corrected, already


def correct_manifests(cache, dry_run) -> tuple:
    corrected, entries = [], 0
    for path in sorted(HERE.glob("inv-T19-*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        changed = 0
        for case in manifest["cases"]:
            for attempt in case["attempts"]:
                new_hash, _ = truth(attempt["bundle"], cache)
                if attempt["bundle_hash"] != new_hash:
                    attempt["bundle_hash"] = new_hash
                    changed += 1
        if not changed:
            continue
        if not dry_run:
            write_record(manifest, "manifest", path)
        corrected.append(path.name)
        entries += changed
    return corrected, entries


ORACLE_CLAIM = ("expected-oracle.md, which was written before any CTP invocation of these cases, and against "
                "the (length, digest) table")
ORACLE_REPLACEMENT = (
    "expected-oracle.md and against the (length, digest) table")
ORACLE_DISCLOSURE = (
    " CLAIM CORRECTED by ticket 44 F7 on 2026-09-16: this note used to add that expected-oracle.md \"was written "
    "before any CTP invocation of these cases\". No artifact can show that -- the prose oracle is sealed in no "
    "replay bundle and was first committed in 27dee8b, after every run -- so the claim is withdrawn rather than "
    "repeated, in favour of the one a reader can verify: derive_ticket19_sizes.py reproduces this answer's "
    "(length, digest) pairs in Python without the engine, which the specification's independent review re-ran and "
    "confirmed. Nothing about the review this note records changed.")


def correct_oracle_claim(dry_run) -> tuple:
    """Phase 3: the promotion notes rest on the checkable half of their own sentence."""
    files, notes = [], 0
    for path in [HERE / "promotions.json"] + sorted(HERE.glob("inv-T19-*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        entries = doc if isinstance(doc, list) else doc.get("answer_promotions", [])
        changed = 0
        for entry in entries:
            reviewer = entry.get("reviewer") or ""
            if ORACLE_CLAIM not in reviewer:
                continue
            entry["reviewer"] = reviewer.replace(ORACLE_CLAIM, ORACLE_REPLACEMENT).rstrip() + ORACLE_DISCLOSURE
            changed += 1
        if not changed:
            continue
        if not dry_run:
            if isinstance(doc, list):
                # promotions.json is a hand-written tooling INPUT, not a campaign record: no schema
                # describes it, so `write_record` has nothing to validate it against. Its writer
                # shape is copied so the file keeps the form every other record here has.
                path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            else:
                write_record(doc, "manifest", path)
        files.append(path.name)
        notes += changed
    return files, notes


def refresh_matrix_seals(dry_run) -> list:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    refreshed = []
    for row in matrix["rows"]:
        run = row.get("run")
        if not run:
            continue
        manifest_path = DOCS_ROOT / run["manifest_path"]
        if not manifest_path.exists():
            continue
        current = sha256_prefixed(manifest_path)
        if run["manifest_hash"] != current:
            run["manifest_hash"] = current
            refreshed.append(row["row_id"])
    if refreshed and not dry_run:
        write_record(matrix, "matrix", MATRIX)
    return refreshed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        return apply_corrections(args)
    except RecordError as exc:
        print(f"[apply_ticket44_record_corrections] REFUSED: {exc}", file=sys.stderr)
        return 2


def apply_corrections(args) -> int:
    cache: dict = {}
    verb = "would correct" if args.dry_run else "corrected"

    corrected, already = correct_attempt_records(cache, args.dry_run)
    print(f"[apply_ticket44_record_corrections] 1. {verb} {len(corrected)} attempt record(s) and their bundle "
          f"indexes; {already} already matched the finished bundle")

    manifests, entries = correct_manifests(cache, args.dry_run)
    print(f"[apply_ticket44_record_corrections] 2. {verb} {entries} attempt entr(ies) across "
          f"{len(manifests)} manifest(s): {', '.join(manifests) or 'none'}")

    oracle_files, oracle_notes = correct_oracle_claim(args.dry_run)
    print(f"[apply_ticket44_record_corrections] 3. {verb} {oracle_notes} promotion reviewer note(s) across "
          f"{len(oracle_files)} file(s): {', '.join(oracle_files) or 'none'}")

    refreshed = refresh_matrix_seals(args.dry_run)
    print(f"[apply_ticket44_record_corrections] 4. {verb} run.manifest_hash on {len(refreshed)} matrix row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
