#!/usr/bin/env python3
"""Correct the bundle digests and sizes ticket 17's (and ticket 47's) sealed records took too early.

    apply_ticket49_record_corrections.py --evidence-dir DIR [--dry-run]

**Ticket 17's independent review, F2.** `inv-T17-0002` ran nine cases into one bundle
directory, and each attempt record's `bundle.hash`, its bundle index's `total_bytes` and the
manifest's per-attempt `bundle_hash` were written as that directory's digest and size at the
moment the record was built -- while the directory was still growing. Only `att-T17-0010`, the
last record written, carries the finished bundle's numbers; `att-T17-0002` to `-0009` carry
eight digests that verify against nothing and sizes that climb in nine steps. This is the defect
ticket 44 F3 corrected in ticket 19's 64 records on the user's 2026-09-16 decision -- **one
bundle per invocation; the digest and the size are the finished bundle's** -- and the tooling
that reintroduced it two days later did the same to ticket 47's `inv-T47-0001` on 2026-09-19
(eight of its nine records). Ticket 49 seals the tooling once per invocation and corrects both.

Three phases, each re-derived from the bundle on disk rather than patched by hand:

1. every attempt record under `--evidence-dir` whose `bundle.hash` disagrees with the finished
   bundle, and the replay-bundle index beside it, take the finished bundle's digest and size.
   The attempt record's `notes` say it was corrected and what it used to carry, so nothing is
   re-hashed silently (ticket 44's `apply_ticket44_record_corrections.py` is the model);
2. the manifests' per-attempt `bundle_hash` takes the same value, because a manifest and its
   attempt record agreeing on a wrong number is one defect and disagreeing would be two;
3. every matrix row under `--evidence-dir` whose `run.manifest_hash` seals a manifest phase 2
   rewrote takes that manifest's new file hash: the run did not change, the record of it was
   corrected, and a seal that no longer matches the file it seals is worse than no seal.

No bundle is modified: the finished digest is the sha256 of the `SHA256SUMS` the bundle already
carries (`sha256sum -c` verifies it), computed in memory. A record that already matches is left
alone, so the script is idempotent and reports what it did; a record that claims to have been
corrected and still disagrees is refused rather than corrected twice.
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

CORRECTION_MARK = "BUNDLE HASH CORRECTED by ticket 49 F2"
CORRECTION_DATE = "2026-09-21"


def truth(root: str, cache: dict) -> tuple:
    if root not in cache:
        path = Path(root)
        if not path.is_dir():
            raise RecordError(f"bundle root {root} does not exist; nothing can be corrected against it")
        sums = path / "SHA256SUMS"
        if not sums.exists():
            raise RecordError(f"{root} carries no SHA256SUMS; a bundle sealed without one is not this script's to correct")
        in_memory = bundle_hash(path, write_sums=False)
        on_disk = sha256_prefixed(sums)
        if in_memory != on_disk:
            raise RecordError(f"{root}: SHA256SUMS on disk hashes {on_disk} but the listing the convention writes "
                              f"hashes {in_memory}; the bundle changed after it was sealed, reconcile by hand")
        cache[root] = (on_disk, bundle_total_bytes(path))
    return cache[root]


def correction_note(old_hash: str, old_bytes, new_hash: str, new_bytes: int) -> str:
    """What this record used to say, naming only what actually changed (ticket 44's rule)."""
    parts = []
    if old_hash != new_hash:
        parts.append(f"the recorded digest {old_hash} is replaced by the finished bundle's {new_hash}")
    if old_bytes != new_bytes:
        parts.append(f"the replay-bundle index's total_bytes {old_bytes} is replaced by {new_bytes}")
    if not parts:
        raise RecordError("refusing to write a correction note for a record that changed nothing")
    return (
        f" {CORRECTION_MARK} on {CORRECTION_DATE}: " + "; and ".join(parts) + ". Both were taken while this "
        "invocation's shared bundle directory was still being written, so they described no bundle that ever "
        "existed on disk -- the defect ticket 44 F3 corrected in ticket 19's records on the user's 2026-09-16 "
        "decision (one bundle per invocation; the digest and the size are the finished bundle's), reintroduced by "
        "the post-processors sealing inside their per-case loop and found again by ticket 17's independent review "
        "(F2). The bundle is unchanged and was not re-hashed silently: the new digest is the sha256 of the "
        "SHA256SUMS the bundle carries, which `sha256sum -c` verifies, and the new size is the sum of the files it "
        "lists. The tooling now seals a shared root once, after the invocation's last file (ticket 49)."
    )


def correct_attempt_records(evidence: Path, cache, dry_run) -> tuple:
    corrected, already = [], 0
    for path in sorted(evidence.rglob("att-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        bundle = record.get("bundle")
        if not bundle:
            continue
        new_hash, new_bytes = truth(bundle["path"], cache)
        index_path = path.with_name(f"bundle-{path.name}")
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else None
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


def correct_manifests(evidence: Path, cache, dry_run) -> tuple:
    corrected, entries = [], 0
    for path in sorted(evidence.rglob("inv-*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if "cases" not in manifest:
            continue
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


def refresh_matrix_seals(evidence: Path, dry_run) -> list:
    refreshed = []
    for matrix_path in sorted(evidence.rglob("matrix*.json")):
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        if "rows" not in matrix or "accepted_exclusions" not in matrix:
            continue
        rows = []
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
                rows.append(row["row_id"])
        if rows:
            if not dry_run:
                write_record(matrix, "matrix", matrix_path)
            refreshed.append((matrix_path.name, rows))
    return refreshed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence-dir", required=True, help="the ticket's evidence directory (evidence/ticket17, evidence/ticket47)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        return apply_corrections(args)
    except RecordError as exc:
        print(f"[apply_ticket49_record_corrections] REFUSED: {exc}", file=sys.stderr)
        return 2


def apply_corrections(args) -> int:
    evidence = Path(args.evidence_dir).resolve()
    if not evidence.is_dir():
        raise RecordError(f"{evidence} is not a directory")
    cache: dict = {}
    verb = "would correct" if args.dry_run else "corrected"
    tag = f"[apply_ticket49_record_corrections] {evidence.name}:"

    corrected, already = correct_attempt_records(evidence, cache, args.dry_run)
    print(f"{tag} 1. {verb} {len(corrected)} attempt record(s) and their bundle indexes "
          f"({', '.join(corrected) or 'none'}); {already} already matched the finished bundle")

    manifests, entries = correct_manifests(evidence, cache, args.dry_run)
    print(f"{tag} 2. {verb} {entries} attempt entr(ies) across {len(manifests)} manifest(s): {', '.join(manifests) or 'none'}")

    refreshed = refresh_matrix_seals(evidence, args.dry_run)
    for name, rows in refreshed:
        print(f"{tag} 3. {verb} run.manifest_hash on {len(rows)} row(s) of {name}")
    if not refreshed:
        print(f"{tag} 3. {verb} run.manifest_hash on 0 matrix row(s)"
              + (" (a dry run re-derives seals over the manifests as they are on disk, so a manifest phase 2 would "
                 "rewrite still seals as recorded here)" if args.dry_run and manifests else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
