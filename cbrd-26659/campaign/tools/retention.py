#!/usr/bin/env python3
"""Retention and admission for campaign replay bundles (ticket 15).

    retention.py admit --bytes N [--limit-gib 100] [--root DIR]
        Exit 0 when the campaign storage root plus N bytes stays under the limit, 3 when it
        would not. The wrappers call this before a launcher starts: at the storage limit the
        campaign stops admitting work instead of deleting unresolved evidence (decision 08).

    retention.py status [--evidence DIR ...] [--root DIR] [--today YYYY-MM-DD]
        One line per bundle index found (bundle-*.json): class, expiry, hold, whether the
        bundle directory still exists and its size; then the storage usage against the limit.

    retention.py triage BUNDLE_INDEX.json --date YYYY-MM-DD [--hold TEXT]
        Records the triage date of a failure bundle: expires_on becomes the date plus thirty
        days and the "awaiting triage" hold is lifted, or replaced by --hold when an
        unresolved finding still needs the bundle. Validated before writing.

    retention.py expire [--evidence DIR ...] [--today YYYY-MM-DD] [--apply]
        Lists (dry run, the default) the bundles whose bulky files may be deleted: class
        success-bulky, expires_on before today, no hold reason, bundle directory under an
        unprotected prefix. With --apply it deletes those bundle directories, rewrites the
        matching attempt record's `bundle` to null (the schema allows that only for a PASS
        whose bulky artifacts expired) and marks the bundle index's root as expired in its
        hold_reason. It never touches failure or minimized-reproducer bundles, held bundles,
        bundles it has no index for, or anything under the protected prefixes (tickets 13, 14
        and 16 evidence).

Retention classes (spec "Execution tiers, configurations and budgets"): success-bulky seven
days; failure bundles through triage plus thirty days; compact attempt records and minimized
reproducers kept. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign_records import (  # noqa: E402
    CAMPAIGN_DIR, RETENTION_FAILURE_DAYS_AFTER_TRIAGE, STORAGE_LIMIT_BYTES, STORAGE_ROOT, RecordError, load_json,
    storage_used_bytes, write_record,
)

PROTECTED_PREFIXES = (
    "/home/vimkim/.cub/campaign/cbrd-26659/attempts/att-T13-",
    "/home/vimkim/.cub/campaign/cbrd-26659/ticket14/",
    "/home/vimkim/.cub/campaign/cbrd-26659/ticket16/",
    "/home/vimkim/.cub/campaign/cbrd-26659/db",
    "/home/vimkim/.cub/campaign/cbrd-26659/negative-control/",
)
DEFAULT_EVIDENCE = CAMPAIGN_DIR / "evidence"


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink()) if path.exists() else 0


def find_indexes(evidence_dirs):
    for d in evidence_dirs:
        for p in sorted(Path(d).rglob("bundle-*.json")):
            try:
                idx = load_json(p)
            except Exception:  # noqa: BLE001
                continue
            if idx.get("schema_version") == 1 and "retention" in idx:
                yield p, idx


def cmd_admit(args) -> int:
    used = storage_used_bytes(args.root)
    limit = int(args.limit_gib * 1024 ** 3)
    projected = used + args.bytes
    ok = projected <= limit
    print(f"[retention] storage {args.root}: used {used / 1024 ** 3:.2f} GiB, requested {args.bytes / 1024 ** 3:.2f} GiB, "
          f"limit {args.limit_gib} GiB -> {'ADMITTED' if ok else 'REFUSED: stop admitting work; nothing is deleted (decision ticket 08)'}")
    return 0 if ok else 3


def cmd_status(args) -> int:
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    rows = 0
    for p, idx in find_indexes(args.evidence or [DEFAULT_EVIDENCE]):
        rows += 1
        root = Path(idx["root_path"])
        ret = idx["retention"]
        exp = ret.get("expires_on")
        state = "kept"
        if ret["class"] == "success-bulky" and exp and dt.date.fromisoformat(exp) < today and not ret.get("hold_reason"):
            state = "EXPIRED"
        elif ret["class"] == "failure" and not exp:
            state = "awaiting triage"
        prot = any(str(root).startswith(pp) for pp in PROTECTED_PREFIXES)
        print(f"{idx['bundle_id']:28} {ret['class']:20} expires={exp or '-':10} {state:15} "
              f"{'exists' if root.exists() else 'ABSENT':6} {dir_size(root) / 1024 ** 2:9.1f} MiB {'protected' if prot else ''} {p}")
    used = storage_used_bytes(args.root)
    print(f"[retention] {rows} bundle index(es); storage {args.root}: {used / 1024 ** 3:.2f} GiB of {STORAGE_LIMIT_BYTES / 1024 ** 3:.0f} GiB")
    return 0


def cmd_triage(args) -> int:
    path = Path(args.index)
    idx = load_json(path)
    if idx["retention"]["class"] != "failure":
        raise RecordError(f"{path}: triage applies to failure bundles, this one is {idx['retention']['class']}")
    date = dt.date.fromisoformat(args.date)
    idx["retention"]["expires_on"] = (date + dt.timedelta(days=RETENTION_FAILURE_DAYS_AFTER_TRIAGE)).isoformat()
    idx["retention"]["hold_reason"] = args.hold
    write_record(idx, "replay-bundle", path)
    print(f"[retention] {idx['bundle_id']}: triaged {args.date}, expires_on {idx['retention']['expires_on']}, hold={args.hold!r}")
    return 0


def cmd_expire(args) -> int:
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    candidates = []
    for p, idx in find_indexes(args.evidence or [DEFAULT_EVIDENCE]):
        ret = idx["retention"]
        root = Path(idx["root_path"])
        if ret["class"] != "success-bulky" or ret.get("hold_reason") or not ret.get("expires_on"):
            continue
        if dt.date.fromisoformat(ret["expires_on"]) >= today:
            continue
        if any(str(root).startswith(pp) for pp in PROTECTED_PREFIXES):
            print(f"[retention] {idx['bundle_id']}: expired but PROTECTED ({root}); never deleted by this tool")
            continue
        if not root.exists():
            continue
        if not str(root).startswith(str(STORAGE_ROOT)):
            print(f"[retention] {idx['bundle_id']}: root {root} is outside the campaign storage; refusing")
            continue
        candidates.append((p, idx, root))
    for p, idx, root in candidates:
        size = dir_size(root)
        print(f"[retention] {'DELETE' if args.apply else 'would delete'} {root} ({size / 1024 ** 2:.1f} MiB), "
              f"{idx['bundle_id']} expired {idx['retention']['expires_on']}")
        if not args.apply:
            continue
        att_path = p.parent / f"{idx['attempt_id']}.json"
        if att_path.exists():
            att = load_json(att_path)
            if att.get("outcome") != "PASS":
                print(f"[retention]   attempt record {att_path.name} is not a PASS; refusing to delete its bundle")
                continue
            att["bundle"] = None
            att["notes"] = (att.get("notes") or "") + f" BULKY ARTIFACTS EXPIRED on {today.isoformat()} (success-bulky, seven days); the compact record is kept."
            write_record(att, "attempt-record", att_path)
        shutil.rmtree(root)
        idx["retention"]["hold_reason"] = f"bulky files deleted on {today.isoformat()} after success-bulky expiry; index kept as the record of what existed"
        write_record(idx, "replay-bundle", p)
    if not candidates:
        print("[retention] nothing expired")
    elif not args.apply:
        print("[retention] dry run; pass --apply to delete the bundles listed above")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("admit")
    a.add_argument("--bytes", type=int, required=True)
    a.add_argument("--limit-gib", type=float, default=STORAGE_LIMIT_BYTES / 1024 ** 3)
    a.add_argument("--root", default=str(STORAGE_ROOT))
    s = sub.add_parser("status")
    s.add_argument("--evidence", action="append")
    s.add_argument("--root", default=str(STORAGE_ROOT))
    s.add_argument("--today")
    t = sub.add_parser("triage")
    t.add_argument("index")
    t.add_argument("--date", required=True)
    t.add_argument("--hold")
    e = sub.add_parser("expire")
    e.add_argument("--evidence", action="append")
    e.add_argument("--today")
    e.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    try:
        return {"admit": cmd_admit, "status": cmd_status, "triage": cmd_triage, "expire": cmd_expire}[args.cmd](args)
    except RecordError as exc:
        print(f"[retention] REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
