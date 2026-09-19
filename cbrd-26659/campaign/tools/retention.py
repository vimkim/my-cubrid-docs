#!/usr/bin/env python3
"""Retention and admission for campaign replay bundles (ticket 15; shrink-not-delete, ticket 45 item 5).

    retention.py admit --bytes N [--limit-gib 100] [--root DIR]
        Exit 0 when the campaign storage root plus N bytes stays under the limit, 3 when it
        would not. The wrappers call this before a launcher starts: at the storage limit the
        campaign stops admitting work instead of deleting unresolved evidence (decision 08).

    retention.py status [--evidence DIR ...] [--root DIR] [--today YYYY-MM-DD]
        One line per bundle index found (bundle-*.json): class, retention state (full or
        core-only), expiry, standing (kept, EXPIRED, awaiting triage, held, demoted on a date,
        or expired-by-policy), whether the bundle directory still exists and its size; then
        the storage usage against the limit.

    retention.py triage BUNDLE_INDEX.json --date YYYY-MM-DD [--hold TEXT]
        Records the triage date of a failure bundle: expires_on becomes the date plus thirty
        days and the "awaiting triage" hold is lifted, or replaced by --hold when an
        unresolved finding still needs the bundle. Validated before writing.

    retention.py expire [--evidence DIR ...] [--today YYYY-MM-DD] [--apply]
        Lists (dry run, the default) the bundles whose bulk may go: class success-bulky,
        expires_on before today, no hold reason, not already core-only, bundle directory under
        an unprotected prefix. With --apply it DEMOTES each one to its core instead of deleting
        it (ticket 45 item 5, applied by ticket 46): every file and directory under root_path
        that no index of that directory names -- not an item's path, not SHA256SUMS, not a path
        the index lists -- is removed, and the fourteen items, SHA256SUMS and the index stay.
        The bundle hash (sha256 of SHA256SUMS), the per-item hashes and `complete` are therefore
        unchanged and every record citing the bundle stays valid. The index gains
        retention.state core-only and demoted_on. The attempt record is never touched and its
        `bundle` is never nulled.

        The bundle directory is the unit, because one directory belongs to one invocation and
        may be cited by several indexes (ticket 44 F3): it is left whole while any index citing
        it is a failure or minimized-reproducer bundle, is held, or has not expired, and the core
        kept is the union of what every citing index names. A bundle whose core cannot be kept
        (root missing, SHA256SUMS or an enumerated item gone) is recorded in its index as
        expired-by-policy -- demoted_on plus a hold_reason naming what was missing -- and nothing
        is deleted. A bundle whose SHA256SUMS does not hash to what the paired attempt record
        cites, or whose enumerated item does not hash as the index records, is refused and
        nothing is written. It never touches failure or minimized-reproducer bundles, held
        bundles, bundles it has no index for, or anything under the protected prefixes (tickets
        13, 14 and 16 evidence).

Retention classes (spec "Execution tiers, configurations and budgets"): success-bulky seven
days, then core-only; failure bundles through triage plus thirty days; compact attempt
records and minimized reproducers kept. Standard library only.
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
    sha256_prefixed, sha256sums_entries, storage_used_bytes, write_record,
)

PROTECTED_PREFIXES = (
    "/home/vimkim/.cub/campaign/cbrd-26659/attempts/att-T13-",
    "/home/vimkim/.cub/campaign/cbrd-26659/ticket14/",
    "/home/vimkim/.cub/campaign/cbrd-26659/ticket16/",
    "/home/vimkim/.cub/campaign/cbrd-26659/db",
    "/home/vimkim/.cub/campaign/cbrd-26659/negative-control/",
)
DEFAULT_EVIDENCE = CAMPAIGN_DIR / "evidence"
STATE_FULL = "full"
STATE_CORE_ONLY = "core-only"


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink()) if path.exists() else 0


def find_indexes(evidence_dirs, unreadable=None):
    """Yield (path, index) for every readable bundle index below the directories. An index
    that cannot be parsed is appended to `unreadable` when a list is given, else skipped."""
    for d in evidence_dirs:
        for p in sorted(Path(d).rglob("bundle-*.json")):
            try:
                idx = load_json(p)
            except Exception as exc:  # noqa: BLE001
                if unreadable is not None:
                    unreadable.append((p, exc))
                continue
            if idx.get("schema_version") == 1 and "retention" in idx:
                yield p, idx


def retention_state(idx) -> str:
    return idx["retention"].get("state") or STATE_FULL


def is_protected(root) -> bool:
    return any(str(root).startswith(pp) for pp in PROTECTED_PREFIXES)


def standing(idx, today) -> str:
    """Where the bundle stands under the retention rule, for the status listing."""
    ret = idx["retention"]
    exp = ret.get("expires_on")
    if retention_state(idx) == STATE_CORE_ONLY:
        return f"demoted {ret.get('demoted_on')}"
    if ret.get("demoted_on"):
        return "expired-by-policy"
    if ret["class"] == "failure" and not exp:
        return "awaiting triage"
    if ret.get("hold_reason"):
        return "held"
    if ret["class"] == "success-bulky" and exp and dt.date.fromisoformat(exp) < today:
        return "EXPIRED"
    return "kept"


def expiry_verdict(idx, today):
    """('core-only', None) when already demoted, ('eligible', None) when the bulk may go,
    else ('blocked', why): this index keeps its whole directory, whoever else cites it."""
    ret = idx["retention"]
    if retention_state(idx) == STATE_CORE_ONLY:
        return STATE_CORE_ONLY, None
    if ret["class"] != "success-bulky":
        why = f"{ret['class']} bundle"
        if ret["class"] == "failure":
            why += " awaiting triage" if not ret.get("expires_on") else f", triaged, expires {ret['expires_on']}"
        return "blocked", why
    if ret.get("hold_reason"):
        return "blocked", f"held: {ret['hold_reason']}"
    if not ret.get("expires_on"):
        return "blocked", "no expires_on"
    if dt.date.fromisoformat(ret["expires_on"]) >= today:
        return "blocked", f"not expired until {ret['expires_on']}"
    return "eligible", None


def core_paths(indexes) -> set:
    """Bundle-relative paths the indexes of one directory name: every present item's path,
    SHA256SUMS, and any snapshot path (those are docs-repository paths today and are kept
    only if they happen to exist under the root)."""
    keep = {"SHA256SUMS"}
    for idx in indexes:
        for item in idx["items"].values():
            if item["state"] == "present" and item.get("path"):
                keep.add(item["path"].strip("/"))
        for snap in idx.get("uncommitted_snapshots") or []:
            if snap.get("path"):
                keep.add(snap["path"].strip("/"))
    return keep


def paired_bundle_hash(index_path: Path, idx) -> str | None:
    """The bundle hash the attempt record beside the index cites, when that record exists."""
    att = index_path.parent / f"{idx['attempt_id']}.json"
    if not att.exists():
        return None
    try:
        return (load_json(att).get("bundle") or {}).get("hash")
    except Exception:  # noqa: BLE001
        return None


def core_check(root: Path, citing):
    """None when the core of every citing index is on disk as recorded. ('missing', what) when
    the rule cannot keep the core because something enumerated is gone. ('refused', why) when
    what is on disk does not hash as the records say, so the bundle must not be touched."""
    sums = root / "SHA256SUMS"
    if not sums.exists():
        return "missing", "SHA256SUMS is not in the bundle"
    for _, idx in citing:
        for name, item in idx["items"].items():
            if item["state"] == "present" and item.get("path") and not (root / item["path"]).exists():
                return "missing", f"item {name} ({item['path']}) of {idx['bundle_id']} is gone"
    listed = sha256sums_entries(sums)
    for _, idx in citing:
        for name, item in idx["items"].items():
            if item["state"] != "present" or not item.get("path") or not item.get("hash"):
                continue
            f = root / item["path"]
            if f.is_file() and sha256_prefixed(f) != item["hash"]:
                return "refused", f"item {name} ({item['path']}) of {idx['bundle_id']} does not hash as the index records"
            if listed.get(item["path"]) != item["hash"].split(":")[-1]:
                return "refused", f"SHA256SUMS does not list {item['path']} with the hash {idx['bundle_id']} records"
    got = sha256_prefixed(sums)
    for p, idx in citing:
        cited = paired_bundle_hash(p, idx)
        if cited and cited != got:
            return "refused", f"SHA256SUMS hashes {got}, the attempt record of {idx['bundle_id']} cites {cited}"
    return None


def tree_stats(path: Path):
    """(files, apparent bytes, disk bytes) of a file, a symlink or a directory tree."""
    if path.is_symlink() or path.is_file():
        st = path.lstat()
        return 1, st.st_size, st.st_blocks * 512
    files = apparent = disk = 0
    for p in path.rglob("*"):
        if p.is_symlink() or p.is_file():
            st = p.lstat()
            files, apparent, disk = files + 1, apparent + st.st_size, disk + st.st_blocks * 512
    return files, apparent, disk


def removal_plan(root: Path, keep: set) -> list:
    """What leaves the bundle, as (relative path, is_dir, files, apparent, disk) units: a file,
    or a whole directory holding nothing kept. A directory holding a kept path is descended."""
    units = []

    def walk(directory: Path, rel: str):
        for child in sorted(directory.iterdir()):
            crel = f"{rel}/{child.name}" if rel else child.name
            if crel in keep:
                continue
            is_dir = child.is_dir() and not child.is_symlink()
            if is_dir and any(k.startswith(crel + "/") for k in keep):
                walk(child, crel)
                continue
            units.append((crel, is_dir, *tree_stats(child)))

    walk(root, "")
    return units


def remove_units(root: Path, units) -> None:
    for rel, is_dir, _, _, _ in units:
        target = root / rel
        if is_dir:
            shutil.rmtree(target)
        else:
            target.unlink()


def record_expired_by_policy(eligible, today, what, apply) -> int:
    """The core rule cannot keep this bundle: say so in each index, delete nothing."""
    for p, idx in eligible:
        print(f"[retention] {'RECORD' if apply else 'would record'} expired-by-policy for {idx['bundle_id']}: {what}; nothing deleted")
        if apply:
            idx["retention"]["demoted_on"] = today.isoformat()
            idx["retention"]["hold_reason"] = (
                f"expired-by-policy on {today.isoformat()}: the core rule (ticket 45 item 5) could not keep this bundle "
                f"because {what}; nothing was deleted, the hash stays as recorded and the attempt record is untouched")
            write_record(idx, "replay-bundle", p)
    return len(eligible)


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
        print(f"{idx['bundle_id']:28} {ret['class']:20} {retention_state(idx):9} expires={exp or '-':10} {standing(idx, today):19} "
              f"{'exists' if root.exists() else 'ABSENT':6} {dir_size(root) / 1024 ** 2:9.1f} MiB {'protected' if is_protected(root) else ''} {p}")
    used = storage_used_bytes(args.root)
    print(f"[retention] {rows} bundle index(es); storage {args.root}: {used / 1024 ** 3:.2f} GiB of {STORAGE_LIMIT_BYTES / 1024 ** 3:.0f} GiB "
          "(apparent size, the sum of st_size; the settled cap is disk usage, decision request 48.5)")
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
    evidence = [Path(d) for d in (args.evidence or [DEFAULT_EVIDENCE])]
    unreadable = []
    asked = {p for p, _ in find_indexes(evidence, unreadable)}
    for p, exc in unreadable:
        print(f"[retention] {p}: index unreadable ({exc}); nothing can be recorded in it and its bundle is not touched")
    # One bundle directory serves every attempt of its invocation (ticket 44 F3), so the
    # decision is per directory and every index citing it has a say, wherever it lives: the
    # sibling map covers the whole evidence tree as well as the directories asked for.
    by_root, seen = {}, set()
    for p, idx in find_indexes([*evidence, DEFAULT_EVIDENCE]):
        if p.resolve() in seen:
            continue
        seen.add(p.resolve())
        by_root.setdefault(idx["root_path"], []).append((p, idx))
    n_candidates = n_demoted = n_marked = n_recorded = 0
    freed_apparent = freed_disk = 0
    for root_s in sorted(by_root):
        citing = by_root[root_s]
        verdicts = {p: expiry_verdict(idx, today) for p, idx in citing}
        eligible = [(p, idx) for p, idx in citing if verdicts[p][0] == "eligible"]
        if not any(p in asked for p, _ in eligible):
            continue
        n_candidates += 1
        root = Path(root_s)
        ids = ", ".join(idx["bundle_id"] for _, idx in eligible)
        if is_protected(root):
            print(f"[retention] {ids}: expired but PROTECTED ({root}); never touched by this tool")
            continue
        blockers = [f"{idx['bundle_id']} ({verdicts[p][1]})" for p, idx in citing if verdicts[p][0] == "blocked"]
        if blockers:
            print(f"[retention] {ids}: expired, but the bundle directory {root} is shared with {'; '.join(blockers)}; left whole")
            continue
        if not str(root).startswith(str(STORAGE_ROOT)):
            print(f"[retention] {ids}: root {root} is outside the campaign storage; refusing")
            continue
        if not root.exists():
            n_recorded += record_expired_by_policy(eligible, today, f"root_path {root} does not exist", args.apply)
            continue
        problem = core_check(root, citing)
        if problem and problem[0] == "missing":
            n_recorded += record_expired_by_policy(eligible, today, problem[1], args.apply)
            continue
        if problem:
            print(f"[retention] {ids}: REFUSED, {problem[1]}; nothing written, nothing deleted")
            continue
        keep = core_paths([idx for _, idx in citing])
        units = removal_plan(root, keep)
        files, apparent, disk = (sum(u[i] for u in units) for i in (2, 3, 4))
        kept = sorted(k for k in keep if (root / k).exists())
        done = [idx["bundle_id"] for p, idx in citing if verdicts[p][0] == STATE_CORE_ONLY]
        print(f"[retention] {'DEMOTE' if args.apply else 'would demote'} {root} to core-only: keep {len(kept)} path(s) named by {ids}"
              f"{' and already core-only ' + ', '.join(done) if done else ''}; remove {files} file(s) in {len(units)} unit(s), "
              f"{apparent / 1024 ** 2:.1f} MiB apparent, {disk / 1024 ** 2:.1f} MiB on disk")
        for rel, is_dir, n, a, _ in units:
            print(f"[retention]     - {rel}{'/' if is_dir else ''} ({n} file(s), {a / 1024:.1f} KiB)")
        if not args.apply:
            continue
        before = sha256_prefixed(root / "SHA256SUMS")
        remove_units(root, units)
        after = sha256_prefixed(root / "SHA256SUMS")
        if after != before:
            raise RecordError(f"{root}: SHA256SUMS changed during demotion ({before} -> {after}); the bundle hash is no longer as recorded")
        n_demoted += 1
        freed_apparent, freed_disk = freed_apparent + apparent, freed_disk + disk
        for p, idx in eligible:
            idx["retention"]["state"] = STATE_CORE_ONLY
            idx["retention"]["demoted_on"] = today.isoformat()
            write_record(idx, "replay-bundle", p)
            n_marked += 1
            print(f"[retention]   {idx['bundle_id']}: core-only, demoted_on {today.isoformat()}, sha256(SHA256SUMS) {after} unchanged ({p})")
    if not n_candidates:
        print("[retention] nothing expired")
    elif args.apply:
        print(f"[retention] {n_demoted} bundle director{'y' if n_demoted == 1 else 'ies'} demoted to core-only, {n_marked} index(es) marked, "
              f"{n_recorded} index(es) recorded expired-by-policy; freed {freed_apparent / 1024 ** 2:.1f} MiB apparent, "
              f"{freed_disk / 1024 ** 2:.1f} MiB on disk; no bundle deleted, no attempt record touched")
    else:
        print("[retention] dry run; pass --apply to demote the bundles listed above to their core (no bundle is deleted whole; "
              "attempt records are never touched)")
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
