#!/usr/bin/env python3
"""Check DevelopHeapReservation.tla against facts read from pinned CUBRID develop source.

Exit 0: every verdict matches EXPECTED. Exit 1: a verdict differs. Exit 2: tool error or source drift.
"""
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
MODEL = HERE / "DevelopHeapReservation.tla"
PINNED = "2362424f25bcebd1bd9733bddd59a993e2852ac5"
TLC_JAR = pathlib.Path.home() / ".cache/tlaplus/tla2tools-1.7.4.jar"
SOURCES = {
    "heap": "src/storage/heap_file.c",
    "fm": "src/storage/file_manager.c",
    "log": "src/transaction/log_manager.c",
    "vac": "src/query/vacuum.c",
    "pb": "src/storage/page_buffer.c",
    "bs_cpp": "src/storage/bestspace.cpp",
    "bs_hpp": "src/storage/bestspace.hpp",
    "common": "src/storage/storage_common.h",
}


class Drift(Exception):
    pass


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def ordered(texts, key, start, end, *parts, strict=True):
    """Line numbers of parts in order inside [start, end), or None when the order breaks.

    strict: a missing part is source drift. Fact markers pass strict=False so a missing
    part turns the fact FALSE instead."""
    text = texts[key]
    begin = text.find(start)
    if begin < 0:
        raise Drift(f"{SOURCES[key]}: missing {start!r}")
    stop = text.find(end, begin + len(start))
    if stop < 0:
        raise Drift(f"{SOURCES[key]}: missing end {end!r} after {start!r}")
    lines, offset = [], begin
    for part in parts:
        if text.find(part, begin, stop) < 0:
            if not strict:
                return None
            raise Drift(f"{SOURCES[key]}: missing {part!r} in {start!r}")
        found = text.find(part, offset, stop)
        if found < 0:
            return None
        lines.append(line_of(text, found))
        offset = found + len(part)
    return {"file": SOURCES[key], "start": line_of(text, begin + start.startswith("\n")), "markers": dict(zip(parts, lines))}


def require(evidence):
    if evidence is None:
        raise Drift("required marker order changed")
    return evidence


def extract(texts):
    """Model constants and the source evidence that grounds them."""
    hold = ordered(texts, "heap", "\nheap_alloc_new_pages (THREAD_ENTRY", "\nerror:\n",
                   "pgbuf_ordered_fix (thread_p, &heap_hdr_vpid, OLD_PAGE, PGBUF_LATCH_WRITE, &heap_hdr_watcher)",
                   "log_sysop_start (thread_p)", "file_alloc_multiple (thread_p, &hfid->vfid",
                   "log_sysop_commit (thread_p)", "pgbuf_ordered_unfix (thread_p, &heap_hdr_watcher)", strict=False)
    vac_gates = require(ordered(texts, "heap", "\nheap_remove_page_on_vacuum (THREAD_ENTRY", "Page removed successfully",
                                "pgbuf_ordered_fix (thread_p, &header_vpid, OLD_PAGE, PGBUF_LATCH_WRITE, &header_watcher)",
                                "spage_number_of_records (crt_watcher.pgptr) > 1",
                                "pgbuf_has_prevent_dealloc (crt_watcher.pgptr)", "pgbuf_has_any_waiters (crt_watcher.pgptr)",
                                "log_sysop_start (thread_p)", "file_dealloc (thread_p, &hfid->vfid, &page_vpid, FILE_HEAP)"))
    vac_order = ordered(texts, "heap", "\nheap_remove_page_on_vacuum (THREAD_ENTRY", "Page removed successfully",
                        "file_dealloc (thread_p, &hfid->vfid, &page_vpid, FILE_HEAP)", "log_sysop_commit (thread_p)",
                        "pgbuf_ordered_unfix (thread_p, &header_watcher)", strict=False)
    sysop_postpone = ordered(texts, "log", "\nlog_sysop_commit_internal (THREAD_ENTRY", "\nlog_sysop_commit (THREAD_ENTRY",
                             "log_sysop_do_postpone (thread_p, tdes, log_record", strict=False)
    dealloc_postpone = require(ordered(texts, "fm", "\nfile_dealloc (THREAD_ENTRY", "\nfile_perm_dealloc (",
                                       "log_append_postpone (thread_p, RVFL_DEALLOC"))
    batch = re.search(r"static constexpr std::size_t ALLOC_BATCH_SIZE = (\d+);", texts["bs_hpp"])
    sector = re.search(r"#define DISK_SECTOR_NPAGES (\d+)", texts["common"])
    if not batch or not sector:
        raise Drift("ALLOC_BATCH_SIZE or DISK_SECTOR_NPAGES not found")
    evidence = {
        "batch_hold": hold, "vacuum_gates": vac_gates, "vacuum_order": vac_order, "sysop_postpone": sysop_postpone,
        "dealloc_postpone": dealloc_postpone,
        "batch_request": require(ordered(texts, "bs_cpp", "\n  bestspace::shard::allocate_new_pages (", "m_num_pages.fetch_add",
                                         "heap_alloc_new_pages (thread_p, hfid, ALLOC_BATCH_SIZE - num_candidates")),
        "batch_file_header": require(ordered(texts, "fm", "\nfile_alloc_multiple (THREAD_ENTRY", "\nfile_alloc_sticky_first_page (",
                                             "PGBUF_LATCH_WRITE, PGBUF_UNCONDITIONAL_LATCH", "file_alloc (thread_p, vfid",
                                             "log_sysop_attach_to_outer (thread_p)", "pgbuf_unfix (thread_p, page_fhead)")),
        "perm_alloc": require(ordered(texts, "fm", "\nfile_perm_alloc (THREAD_ENTRY", "\nfile_alloc (THREAD_ENTRY",
                                      "if (fhead->n_page_free == 0)", "file_perm_expand (thread_p, page_fhead)",
                                      "file_partsect_alloc (partsect, vpid_alloc_out", "FILE_ALLOC_TABLE_PAGE_FULL_SECTOR",
                                      "file_table_append_full_sector_page", "is_full = file_partsect_is_full (partsect)",
                                      "file_extdata_remove_at (extdata_part_ftab, 0, 1)",
                                      "file_table_add_full_sector (thread_p, page_fhead, &vsid_full)")),
        "full_table_recursion": require(ordered(texts, "fm", "\nfile_table_add_full_sector (THREAD_ENTRY", "\nfile_table_",
                                                "file_extdata_find_not_full (thread_p, &extdata_full_ftab",
                                                "file_perm_alloc (thread_p, page_fhead, FILE_ALLOC_TABLE_PAGE_FULL_SECTOR")),
        "expand": require(ordered(texts, "fm", "\nfile_perm_expand (THREAD_ENTRY", "\nfile_perm_",
                                  "log_sysop_start (thread_p)", "disk_reserve_sectors (",
                                  "file_extdata_append (extdata_part_ftab, &partsect)", "log_sysop_commit (thread_p)")),
        "perm_dealloc": require(ordered(texts, "fm", "\nfile_perm_dealloc (THREAD_ENTRY", "\nfile_rv_dealloc_",
                                        "file_partsect_clear_bit (partsect, offset_to_dealloc_bit)",
                                        "file_extdata_find_and_remove_item (thread_p, extdata_full_ftab",
                                        "file_extdata_find_ordered (extdata_part_ftab, &vsid_dealloc")),
        "run_postpone_dealloc": require(ordered(texts, "fm", "\nfile_rv_dealloc_internal (THREAD_ENTRY", "\nfile_rv_dealloc_on_",
                                                "PGBUF_LATCH_WRITE, PGBUF_UNCONDITIONAL_LATCH",
                                                "file_perm_dealloc (thread_p, page_fhead, vpid_dealloc, FILE_ALLOC_USER_PAGE)")),
        "vacuum_gate": require(ordered(texts, "vac", "\nvacuum_heap_page (THREAD_ENTRY", "\nvacuum_heap_prepare_record (",
                                       "spage_number_of_records (helper.home_page) <= 1 && helper.reusable",
                                       "heap_remove_page_on_vacuum (thread_p, &helper.home_page, &helper.hfid)",
                                       "heap_add_bestpage (thread_p, &helper.hfid, helper.home_page")),
        "ordered_fix": require(ordered(texts, "pb", "\npgbuf_ordered_fix_release (THREAD_ENTRY", "\npgbuf_get_groupid_and_unfix (",
                                       "latch_condition = PGBUF_CONDITIONAL_LATCH", "LK_FORCE_ZERO_WAIT",
                                       "pgbuf_bcb_register_avoid_deallocation (holder->bufptr)",
                                       "PGBUF_UNCONDITIONAL_LATCH", "pgbuf_bcb_unregister_avoid_deallocation (bufptr)")),
    }
    facts = {
        "BatchHoldsHeapHeader": hold is not None,
        "PostponeBeforeHeaderUnfix": vac_order is not None and sysop_postpone is not None,
        "MaxBatch": int(batch.group(1)),
        "SectorPages": int(sector.group(1)),
    }
    return facts, evidence


HDR_OFF = {"BatchHoldsHeapHeader": False}
POST_OFF = {"PostponeBeforeHeaderUnfix": False}
CASES = {
    "A1_partial_batch1": dict(Fixture="partial", InitFree=1, Batch=1, FullRoom=0),
    "A4_partial_batch4": dict(Fixture="partial", InitFree=1, Batch=4, FullRoom=0),
    "B1_full_batch1": dict(Fixture="full", InitFree=1, Batch=1, FullRoom=0),
    "B2_full_batch2": dict(Fixture="full", InitFree=1, Batch=2, FullRoom=0),
    "O1_outer_expand": dict(Fixture="full", InitFree=0, Batch=1, FullRoom=0),
    "R1_table_room": dict(Fixture="partial", InitFree=1, Batch=1, FullRoom=1),
    "M1_no_header_hold": dict(Fixture="partial", InitFree=1, Batch=1, FullRoom=0, **HDR_OFF),
    "M2_late_postpone": dict(Fixture="partial", InitFree=1, Batch=1, FullRoom=0, **POST_OFF),
}
QUESTIONS = ["NoReserveWhileUnlinkable", "NoReserveWhileUnlinkedNotFree", "NoReserveWhilePhysicallyEmpty",
             "NoRecursiveReserveWhilePhysicallyEmpty", "NoOuterReserveWhilePhysicallyEmpty",
             "ReclaimFirstAvoidsReservation", "NoReservation", "NoCompletedRun"]
STRUCTURAL = ["TypeOK", "PartialSectorsHaveFreeBits", "Accounting", "ReserveOnlyWithoutFreeBits"]
P, F = "PASS", "FAIL"
EXPECTED = {
    #                     unlinkable unlinkedNF physEmpty recursive outer reclaimFirst noReserve completed
    "A1_partial_batch1": [P, P, F, F, P, P, F, F],
    "A4_partial_batch4": [P, P, F, F, P, F, F, F],
    "B1_full_batch1":    [P, P, F, F, P, P, F, F],
    "B2_full_batch2":    [P, P, F, F, P, F, F, F],
    "O1_outer_expand":   [P, P, F, P, F, P, F, F],
    "R1_table_room":     [P, P, P, P, P, P, P, F],
    "M1_no_header_hold": [F, F, F, F, P, P, F, F],
    "M2_late_postpone":  [P, F, F, F, P, P, F, F],
}


def tla_value(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return f'"{value}"' if isinstance(value, str) else str(value)


def cfg_text(constants, invariants):
    lines = ["SPECIFICATION Spec", "CONSTANTS"]
    lines.extend(f"  {name} = {tla_value(value)}" for name, value in constants.items())
    lines.append("INVARIANTS")
    lines.extend(f"  {name}" for name in invariants)
    return "\n".join(lines) + "\n"


def classify(output, code):
    if "Model checking completed. No error has been found." in output:
        return P
    if re.search(r"Invariant \w+ is violated", output):
        return F
    return f"ERROR(exit {code})"


def run_tlc(case_dir, name):
    # TLC unpacks standard modules into java.io.tmpdir; concurrent runs sharing /tmp corrupt each other's parse.
    tmp = case_dir / f"tmp-{name}"
    tmp.mkdir()
    cmd = ["java", "-XX:+UseParallelGC", f"-Djava.io.tmpdir={tmp}", "-cp", str(TLC_JAR), "tlc2.TLC", "-workers", "1",
           "-metadir", str(case_dir / f"states-{name}"), "-config", f"{name}.cfg", "DevelopHeapReservation.tla"]
    proc = subprocess.run(cmd, cwd=case_dir, capture_output=True, text=True, timeout=600)
    (case_dir / f"{name}.log").write_text(proc.stdout + proc.stderr)
    shutil.rmtree(case_dir / f"states-{name}", ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    states = re.search(r"(\d+) distinct states found", proc.stdout)
    return classify(proc.stdout, proc.returncode), int(states.group(1)) if states else None


def run_case(out, case, overrides, facts):
    case_dir = out / case
    case_dir.mkdir()
    shutil.copy(MODEL, case_dir)
    constants = dict(SectorPages=facts["SectorPages"], TablePageSlots=8,
                     BatchHoldsHeapHeader=facts["BatchHoldsHeapHeader"],
                     PostponeBeforeHeaderUnfix=facts["PostponeBeforeHeaderUnfix"])
    constants.update(overrides)
    if constants["Batch"] > facts["MaxBatch"]:
        raise Drift(f"{case}: Batch exceeds ALLOC_BATCH_SIZE {facts['MaxBatch']}")
    jobs = {"structural": STRUCTURAL, **{q: [q] for q in QUESTIONS}}
    results = {}
    for name, invariants in jobs.items():
        (case_dir / f"{name}.cfg").write_text(cfg_text(constants, invariants))
        results[name] = run_tlc(case_dir, name)
    return case, constants, results


def check(out, facts, cases):
    report, mismatches = {}, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run_case, out, case, overrides, facts) for case, overrides in cases.items()]
        for future in futures:
            case, constants, results = future.result()
            want = dict(zip(QUESTIONS, EXPECTED[case]), structural=P)
            rows = {}
            for name, (verdict, states) in results.items():
                rows[name] = {"verdict": verdict, "expected": want[name], "states": states}
                if verdict != want[name]:
                    mismatches.append(f"{case}/{name}: got {verdict}, expected {want[name]}")
            report[case] = {"constants": constants, "results": rows}
    return report, mismatches


def load_sources(repo, rev):
    texts = {}
    for key, path in SOURCES.items():
        texts[key] = subprocess.check_output(["git", "-C", str(repo), "show", f"{rev}:{path}"], text=True)
    return texts


def mutate(texts, key, old, new):
    if texts[key].count(old) != 1:
        raise Drift(f"self-test mutation anchor not unique in {SOURCES[key]}: {old!r}")
    return {**texts, key: texts[key].replace(old, new)}


def self_test(texts, out):
    unfix = "  pgbuf_ordered_unfix (thread_p, &heap_hdr_watcher);\n  heap_hdr_watcher.pgptr = NULL;\n"
    moved = mutate(texts, "heap", unfix, "")
    moved = mutate(moved, "heap", "  log_sysop_start (thread_p);\n  is_sysop_started = true;\n\n  error_code = file_alloc_multiple",
                   unfix + "  log_sysop_start (thread_p);\n  is_sysop_started = true;\n\n  error_code = file_alloc_multiple")
    early = mutate(texts, "heap", "  pgbuf_ordered_unfix (thread_p, &header_watcher);\n\n  /* Page removed successfully. */",
                   "\n  /* Page removed successfully. */")
    early = mutate(early, "heap", "  /* Finished. */\n  log_sysop_commit (thread_p);",
                   "  /* Finished. */\n  pgbuf_ordered_unfix (thread_p, &header_watcher);\n  log_sysop_commit (thread_p);")
    mutations = {
        "header_released_before_batch": moved,
        "vacuum_unfixes_header_before_commit": early,
        "sysop_commit_skips_postpone": mutate(texts, "log", "      log_sysop_do_postpone (thread_p, tdes, log_record, data_size, data);\n", ""),
    }
    outcome = {}
    for name, mutated in mutations.items():
        facts, _ = extract(mutated)
        mdir = out / f"selftest-{name}"
        mdir.mkdir()
        _, mismatches = check(mdir, facts, {"A1_partial_batch1": CASES["A1_partial_batch1"]})
        outcome[name] = {"facts": facts, "caught": bool(mismatches), "mismatches": mismatches}
    try:
        extract(mutate(texts, "fm", "      error_code = file_perm_expand (thread_p, page_fhead);\n", ""))
        outcome["drift_detected"] = False
    except Drift as exc:
        outcome["drift_detected"] = str(exc)
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", type=pathlib.Path)
    parser.add_argument("--rev", default=PINNED)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true", help="also prove the check fails on mutated source")
    args = parser.parse_args()
    args.out = args.out.resolve()
    if args.out.exists():
        print(f"output path exists: {args.out}", file=sys.stderr)
        return 2
    if not TLC_JAR.exists() or shutil.which("java") is None:
        print(f"need java and {TLC_JAR}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True)
    try:
        texts = load_sources(args.repo, args.rev)
        facts, evidence = extract(texts)
        report, mismatches = check(args.out, facts, CASES)
        selftest = self_test(texts, args.out) if args.self_test else None
    except (Drift, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    summary = {
        "rev": args.rev, "facts": facts, "evidence": evidence,
        "source_sha256": {SOURCES[k]: hashlib.sha256(v.encode()).hexdigest() for k, v in texts.items()},
        "model_sha256": hashlib.sha256(MODEL.read_bytes()).hexdigest(),
        "cases": report, "mismatches": mismatches, "self_test": selftest,
    }
    (args.out / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"facts: {facts}")
    for case, data in report.items():
        cells = " ".join(f"{name}={row['verdict']}" for name, row in data["results"].items())
        print(f"{case}: {cells}")
    if selftest:
        print(f"self-test: {json.dumps(selftest)}")
    errors = [m for m in mismatches if "ERROR" in m]
    print("MATCH" if not mismatches else "MISMATCH:\n  " + "\n  ".join(mismatches))
    selftest_ok = selftest is None or (all(v["caught"] for k, v in selftest.items() if k != "drift_detected")
                                       and selftest["drift_detected"])
    if errors:
        return 2
    return 0 if not mismatches and selftest_ok else 1


if __name__ == "__main__":
    sys.exit(main())
