#!/usr/bin/env python3
"""Turn one CTP shell invocation into campaign records (ticket 15).

    ctp_shell_records.py build --bundle DIR --declarations FILE --manifest-id ID
                               --attempt-ids a,b,... --evidence-dir DIR
                               [--kind original|checker-validation|coexistence]
                               [--oracle expected-oracle.md] [--planted CASE:ASSERTION=NOK ...]
                               [--read-only] [--namespace campaign_ns.sh|none] [--tier fast]

Reads a bundle laid out the way run_ctp_shell.sh (and ticket 14's run_attempt.sh) leaves it
and writes, after schema validation, one manifest (kind original only), one attempt record
per executed case and one replay-bundle index per attempt.

Rules encoded (sources in brackets):

* Proof comes from `ctp_runtime_logs/test_status.data` (total, executed, success, fail, skip
  counts), `ctp_runtime_logs/dispatch_tc_ALL.txt` (what CTP discovered) and the case's own
  `.result` file; never from the launcher exit status, which is 0 on a failed case
  [ticket 14 finding b].
* The shell runner has a real assertion counter: one `<case>-<n> : OK|NOK` line per
  assertion, counted with `^<case>-[0-9]+ : (OK|NOK)`; SKIP lines share the numbering and are
  never counted as executed or as OK [ticket 14 finding a, SKIP semantics]. A declared
  expected count that differs from the executed count is `assertion-count-mismatch`.
* The case-level outcome comes from the case's own `<evidence>/case_outcome` file
  (PASS|FAIL|SKIP|reason), not from CTP's success count [ticket 14 section 4]; any NOK line
  is FAIL whatever the file says; a SKIP is SKIP with its reason; a skipped assertion that
  also appears as OK is `skip-recorded-as-ok`; a case with no OK/NOK line at all is
  `case-not-executed`. UNSUPPORTED and BLOCKED come from the case_outcome file or from the
  declaration when the requirement's catalogue status says so [decision 07].
* OOS-path evidence is `proven` only when the case PASSed and every declared activation
  marker (a regex the case's own evidence must match) is present in this run's evidence
  [spec: activation evidence captured in this run; ticket 14 section 4]. A SKIP never has
  proven evidence. `recovery-log` is now a channel of its own [ticket 36 item 2, applied by
  ticket 40], and a case whose OOS-path evidence IS the recovery log declares it. Ticket 14's
  case keeps `other` with an explicit reference because its evidence is two channels at once,
  SHOW HEAP OOS and the recovery log, and the field holds one [ticket 14 section 10, request 4].
* The expected side of expected_vs_actual.txt is built from the oracle's ordered assertion
  table when an oracle is given, never re-grepped from the result file [ticket 34 F3].
* `configurations_not_run` and `requirements_without_executed_case` follow the same rules
  as the SQL post-processor [ticket 35 F4].
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign_records import (  # noqa: E402
    CAMPAIGN_PORTS, RecordError, TIER_CAPS, TOOL_VERSION, assertable_requirement_ids, bundle_hash,
    bundle_total_bytes, configuration_label, configurations_not_run, ctp_fingerprint, docs_relative,
    gib, item, load_json, not_applicable, now_iso, read_kv, requirement, retention_block, sha256_bytes,
    sha256_file, write_record,
)
from record_builders import (  # noqa: E402
    retention_for,
    attempt_skeleton, declared_case_list_text, engine_identity_from, evidence_block, load_declarations,
    manifest_skeleton, parse_identity, testcase_identity_from,
)

RESULT_LINE = re.compile(r"^(?P<case>.+?)-(?P<n>[0-9]+) : (?P<status>OK|NOK|SKIP)\b\s*(?P<rest>.*)$")


def parse_result(path: Path, case_name: str) -> dict:
    """Assertion lines of one case's .result file."""
    lines = {"OK": [], "NOK": [], "SKIP": []}
    by_number = {}
    case_time = None
    for raw in path.read_text(errors="replace").splitlines():
        m = RESULT_LINE.match(raw)
        if m and m.group("case") == case_name:
            status = m.group("status")
            rest = m.group("rest").strip()
            name = rest.split(" :")[0].split(" ")[0] if rest else ""
            lines[status].append((int(m.group("n")), name, rest))
            by_number[int(m.group("n"))] = (status, name, rest)
            continue
        t = re.search(r"--- time=(\d+)\s*$", raw)
        if t:
            case_time = int(t.group(1))
    return {"lines": lines, "by_number": by_number, "case_time_s": case_time,
            "executed": len(lines["OK"]) + len(lines["NOK"]), "ok": len(lines["OK"]), "nok": len(lines["NOK"]),
            "skipped": len(lines["SKIP"])}


def parse_oracle_table(oracle: Path) -> list:
    """Rows `| n | `name` | expectation | skips when |` of the oracle's assertion table."""
    rows = []
    for raw in oracle.read_text(errors="replace").splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|\s*`([a-z0-9_]+)`\s*\|(.*)\|\s*$", raw)
        if not m:
            continue
        cells = [c.strip() for c in m.group(3).split("|")]
        rows.append({"n": int(m.group(1)), "name": m.group(2), "skips_when": cells[-1] if cells else ""})
    return rows


def expected_status(row, build_mode, planted: dict) -> str:
    if planted.get(row["name"]) == "NOK":
        return "NOK"
    sw = row["skips_when"].lower()
    if f"{build_mode} build" in sw:
        return "SKIP"
    return "OK"


def build_expected_vs_actual(case_name, result, oracle_rows, build_mode, planted, attempt_id, oracle_path) -> tuple[str, str]:
    """(verdict, text). Port of finalize_bundle.sh revision 8 (ticket 34 F3)."""
    out = [f"# expected versus actual -- {attempt_id}"]
    if oracle_rows:
        skips = [str(r["n"]) for r in oracle_rows if expected_status(r, build_mode, planted) == "SKIP"]
        noks = [f"#{r['n']} {r['name']}" for r in oracle_rows if expected_status(r, build_mode, planted) == "NOK"]
        out.append(f"# expected: the {len(oracle_rows)} assertions of the oracle's ordered table, each OK,")
        out.append(f"#           except: skipped on this {build_mode} build: {' '.join('#' + s for s in skips) or 'none'};")
        out.append(f"#           planted defect, expected NOK: {' '.join(noks)} (a checker-validation run: the case must FAIL)" if noks
                   else "#           no planted defect (a regression run: the case as a whole must PASS)")
        out.append(f"# actual  : {case_name}.result as written by the case; each oracle row is set against the actual")
        out.append("#           line with the same number, compared by status and by full assertion name.")
        out.append(f"# oracle  : {sha256_file(oracle_path)}  {Path(oracle_path).name}")
        out += ["", "## comparison", "n | oracle name | expected | actual status | actual name | verdict"]
        mismatches = 0
        for r in oracle_rows:
            want = expected_status(r, build_mode, planted)
            got = result["by_number"].get(r["n"])
            if got is None:
                verdict, gs, gn = "MISSING", "-", "-"
                mismatches += 1
            else:
                gs, gn = got[0], got[1]
                verdict = "match" if (gs == want and gn == r["name"]) else "MISMATCH"
                mismatches += verdict == "MISMATCH"
            out.append(f"{r['n']} | {r['name']} | {want} | {gs} | {gn} | {verdict}")
        extra = [n for n in result["by_number"] if n not in {r["n"] for r in oracle_rows}]
        out += ["", "## numbered actual lines the oracle does not list"]
        out += [f"{n}: {result['by_number'][n]}" for n in sorted(extra)] or ["(none)"]
        mismatches += bool(extra)
        overall = "MATCH" if mismatches == 0 else f"MISMATCH ({mismatches})"
    else:
        out.append("# expected: no oracle table was given; only the declared assertion count is compared (see tally)")
        out.append(f"# actual  : {case_name}.result as written by the case")
        overall = "NO-ORACLE"
    out += ["", "## tally", f"executed(OK|NOK) = {result['executed']}", f"OK               = {result['ok']}",
            f"NOK              = {result['nok']}", f"SKIP             = {result['skipped']}", "",
            "## verdict", f"expected_vs_actual={overall}", "", "## actual (verbatim)"]
    return overall, "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--bundle", required=True)
    b.add_argument("--declarations", required=True)
    b.add_argument("--manifest-id", required=True)
    b.add_argument("--attempt-ids", required=True)
    b.add_argument("--evidence-dir", required=True)
    b.add_argument("--kind", default="original", choices=["original", "checker-validation", "coexistence"])
    b.add_argument("--oracle", help="expected-oracle.md whose ordered assertion table is the expected side")
    b.add_argument("--planted", action="append", default=[], help="CASE:ASSERTION=NOK for a negative control")
    b.add_argument("--read-only", action="store_true")
    b.add_argument("--namespace", choices=["campaign_ns.sh", "none"], help="override identity.txt's namespace= line")
    b.add_argument("--producer-version", default=TOOL_VERSION)
    b.add_argument("--tier", default="fast", choices=list(TIER_CAPS))
    b.add_argument("--cap-reached", action="store_true")
    b.add_argument("--cap-seconds", type=int, help="invocation cap actually enforced when it differs from the tier's")
    b.add_argument("--bundle-path-recorded")
    args = ap.parse_args(argv)
    try:
        return build(args)
    except RecordError as exc:
        print(f"[ctp_shell_records] REFUSED: {exc}", file=sys.stderr)
        return 2


def build(args) -> int:
    bundle = Path(args.bundle).resolve()
    evidence_dir = Path(args.evidence_dir)
    decl = load_declarations(args.declarations)
    if decl["runner"] != "ctp-shell":
        raise RecordError("declarations are not for the ctp-shell runner")
    repository = decl["repository"]
    ident = parse_identity(bundle / "identity.txt")
    summary = read_kv(bundle / "summary.txt")
    status = read_kv(bundle / "ctp_runtime_logs" / "test_status.data")
    if not status:
        raise RecordError(f"{bundle}/ctp_runtime_logs/test_status.data is missing or empty: no proof source")
    build_mode = {"release_gcc": "release", "debug_gcc": "debug"}.get(ident.get("build_mode", ""), ident.get("build_mode"))
    if build_mode not in ("release", "debug"):
        raise RecordError(f"cannot determine the build mode from identity.txt ({ident.get('build_mode')!r})")
    run_mode = ident.get("run_mode", decl.get("run_mode", "client-server"))
    page_size = int(ident.get("page_size") or decl.get("page_size") or 16384)
    started_at = ident.get("started_at")
    ended_at = summary.get("ended_at")
    if not (started_at and ended_at):
        raise RecordError("identity.txt started_at and summary.txt ended_at are both required")
    launcher_exit = int(summary["launcher_exit_status"]) if "launcher_exit_status" in summary else None
    engine = engine_identity_from(ident, build_mode, None)
    testcase = testcase_identity_from(ident, repository)
    worktree = Path(testcase["worktree"])
    scenario_abs = ident.get("scenario") or str(worktree / decl["scenario"])
    inv_cap, case_cap = TIER_CAPS[args.tier]
    namespace = args.namespace or ident.get("namespace", "unknown")
    conf_path = next(iter(sorted(bundle.glob("shell_*.conf"))), None)
    if conf_path is None:
        raise RecordError(f"no shell_*.conf (the CTP configuration used) in {bundle}")

    declared = sorted(decl["cases"])
    case_list_text = declared_case_list_text(decl)
    case_list_hash = "sha256:" + sha256_bytes(case_list_text.encode())
    dispatch = bundle / "ctp_runtime_logs" / "dispatch_tc_ALL.txt"
    discovered_paths = [l.strip() for l in dispatch.read_text().splitlines() if l.strip()] if dispatch.exists() else []
    discovered = sorted(Path(p).stem for p in discovered_paths)
    mismatches = []
    for n in declared:
        if n not in discovered:
            mismatches.append({"kind": "case-not-discovered", "detail": f"declared case {n} ({decl['cases'][n]['path']}) is not in CTP's dispatch_tc_ALL.txt"})
    for n in discovered:
        if n not in decl["cases"]:
            mismatches.append({"kind": "unexpected-case", "detail": f"CTP discovered {n}, which no declaration names"})
    total = int(status.get("total_case_count", -1))
    executed_count = int(status.get("total_executed_case_count", -1))
    if total != len(declared):
        mismatches.append({"kind": "case-not-discovered", "detail": f"test_status.data total_case_count={total} differs from the declared count {len(declared)}"})
    if executed_count != len(discovered):
        mismatches.append({"kind": "case-not-executed", "detail": f"test_status.data total_executed_case_count={executed_count} but {len(discovered)} case(s) were dispatched"})
    if launcher_exit not in (0, None):
        mismatches.append({"kind": "launcher-exit-mismatch", "detail": f"launcher exit status {launcher_exit}"})
    if not (bundle / "ctp.log").exists() and not (bundle / "transcript.log").exists():
        mismatches.append({"kind": "setup-log-error", "detail": "no launcher transcript (ctp.log or transcript.log) in the bundle"})

    oracle_rows = parse_oracle_table(Path(args.oracle)) if args.oracle else []
    planted_all = {}
    for p in args.planted:
        case_, rest = p.split(":", 1)
        name_, st = rest.split("=", 1)
        planted_all.setdefault(case_, {})[name_] = st
    attempt_ids = [a for a in args.attempt_ids.split(",") if a]
    aid_iter = iter(attempt_ids)
    cases_out, attempt_records, bundle_indexes = [], [], []
    executed_reqs, ran_configs = set(), set()
    total_executed_assertions = 0
    total_expected_assertions = 0
    all_declared_counts = True
    for n in declared:
        c = decl["cases"][n]
        case_identity = {"repository": repository, "path": c["path"], "name": n}
        exp_count = c.get("expected_assertions_by_build", {}).get(build_mode, c.get("expected_assertions"))
        if exp_count is None:
            all_declared_counts = False
        else:
            total_expected_assertions += exp_count
        result_path = bundle / f"{n}.result"
        if n not in discovered or not result_path.exists():
            cases_out.append({"case": case_identity, "requirements": c["requirements"], "outcome": None, "skip_reason": None,
                              "assertions": {"expected": exp_count, "executed": None, "failed": None},
                              "oos_evidence": evidence_block("missing"), "attempts": [],
                              "outstanding": ({"reason": "cap-reached", "detail": f"the invocation cap ended the launcher before {n} completed; evidence captured so far is in the bundle"}
                                              if args.cap_reached else
                                              {"reason": "not-discovered", "detail": "CTP did not dispatch the case or it left no .result file; see proof.mismatches"})})
            if n in discovered:
                mismatches.append({"kind": "case-not-executed", "detail": f"{n} was dispatched but left no .result file"})
            continue
        attempt_id = next(aid_iter, None)
        if attempt_id is None:
            raise RecordError("fewer --attempt-ids than executed cases")
        result = parse_result(result_path, n)
        # single-case bundles keep case evidence in case-evidence/, multi-case in case-evidence/<case>/
        ev_dir = bundle / "case-evidence" / n if (bundle / "case-evidence" / n).is_dir() else bundle / "case-evidence"
        case_outcome_file = ev_dir / "case_outcome"
        notes_extra = []
        skip_reason = None
        co_raw = case_outcome_file.read_text().strip() if case_outcome_file.exists() else ""
        co_word = co_raw.partition("|")[0]
        if result["nok"] > 0:
            outcome = "FAIL"
        elif result["executed"] == 0 and not (co_word == "SKIP" and result["skipped"] > 0):
            # no assertion executed and the case did not declare a reasoned SKIP: CTP treats a blank
            # result as a failure and so does the campaign; a reasoned all-SKIP run is handled below
            mismatches.append({"kind": "case-not-executed", "detail": f"{n} produced no `OK` or `NOK` assertion line and no reasoned SKIP outcome; CTP treats a blank result as a failure and so does the campaign"})
            outcome = "FAIL"
        elif case_outcome_file.exists():
            raw = case_outcome_file.read_text().strip()
            co, _, reason = raw.partition("|")
            if co == "PASS":
                outcome = "PASS"
            elif co in ("SKIP", "UNSUPPORTED", "BLOCKED"):
                outcome = co
                skip_reason = reason or f"case_outcome {co} without a reason text"
            elif co == "FAIL":
                outcome = "FAIL"
                notes_extra.append(f"case_outcome FAIL ({reason}) although no NOK line was written")
            else:
                outcome = "FAIL"
                notes_extra.append(f"unrecognised case_outcome {raw!r}: recorded FAIL, never PASS")
        else:
            outcome = "PASS"
            notes_extra.append("the case wrote no case_outcome file; outcome derived from the OK/NOK lines alone and the OOS-path evidence stays missing unless declared markers match")
        declared_outcome = c.get("declared_outcome")
        if declared_outcome in ("UNSUPPORTED", "BLOCKED") and outcome != "FAIL":
            if declared_outcome in {requirement(r)["status"] for r in c["requirements"]}:
                outcome = declared_outcome
                notes_extra.append(f"outcome {declared_outcome} declared from the requirement's catalogue status")
            else:
                raise RecordError(f"{n} declares {declared_outcome} but no cited requirement has that catalogue status")
        # skipped assertions that also appear as OK
        skipped_names = set()
        sj = ev_dir / "skipped.journal"
        if sj.exists():
            for line in sj.read_text().splitlines():
                skipped_names.add(line.split("|", 1)[0].strip())
        skipped_names |= {name for _, name, _ in result["lines"]["SKIP"] if name}
        for _, name, _ in result["lines"]["OK"]:
            if name and name in skipped_names:
                mismatches.append({"kind": "skip-recorded-as-ok", "detail": f"{n}: assertion {name} is listed as skipped and also as OK"})
                outcome = "FAIL" if outcome == "PASS" else outcome
        if outcome == "SKIP" and not skip_reason:
            skip_reason = "SKIP without reason text in case_outcome"
        if outcome != "SKIP" and result["skipped"] > 0 and outcome == "PASS":
            skip_reason = None
            notes_extra.append(f"{result['skipped']} assertion(s) skipped on this {build_mode} build and recorded as SKIP lines, never OK: "
                               + "; ".join(f"#{num} {name}: {rest.split(' : ', 1)[-1]}" for num, name, rest in result["lines"]["SKIP"]))
        if exp_count is not None and result["executed"] != exp_count:
            mismatches.append({"kind": "assertion-count-mismatch", "detail": f"{n}: declared {exp_count} executed assertions for the {build_mode} build, measured {result['executed']}"})
        total_executed_assertions += result["executed"]
        # expected versus actual
        verdict, text = build_expected_vs_actual(n, result, oracle_rows, build_mode, planted_all.get(n, {}), attempt_id, args.oracle or "")
        eva_name = "expected_vs_actual.txt" if len(declared) == 1 else f"expected_vs_actual_{n}.txt"
        eva_path = bundle / eva_name
        if not args.read_only:
            eva_path.write_text(text + result_path.read_text(errors="replace"))
        elif not eva_path.exists():
            eva_path = None
        if verdict.startswith("MISMATCH") and outcome == "PASS":
            outcome = "FAIL"
            notes_extra.append("the oracle comparison mismatched although every line was OK: recorded FAIL, never PASS")
        # OOS-path evidence
        ev = c.get("oos_evidence", {})
        markers = ev.get("activation_markers", [])
        matched = []
        for mk in markers:
            f = ev_dir / mk["file"]
            ok = f.exists() and re.search(mk["regex"], f.read_text(errors="replace")) is not None
            matched.append((mk, ok))
        if outcome == "PASS" and markers and all(ok for _, ok in matched):
            oos = evidence_block("proven", ev.get("channel", "other"), None, ev.get("applicability"))
            ref_rel = ev.get("reference_file")
            if ref_rel and (ev_dir / ref_rel).exists():
                dest_dir = evidence_dir / attempt_id
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ev_dir / ref_rel, dest_dir / Path(ref_rel).name)
                oos["reference"] = docs_relative(dest_dir / Path(ref_rel).name)
            else:
                oos["reference"] = str(ev_dir)
            if oos["applicability"]:
                oos["applicability"] = dict(oos["applicability"], source_manifest=args.manifest_id if args.kind == "original" else "none (not a suite invocation)")
            act_note = "activation markers all matched in this run's own evidence: " + ", ".join(f"{mk['file']} ~ /{mk['regex']}/" for mk, _ in matched)
        elif args.kind != "original":
            oos = evidence_block("not-applicable")
            act_note = f"a {args.kind} attempt certifies the checker, not the requirement; its observations count as coverage of nothing"
        elif outcome == "SKIP":
            oos = evidence_block("missing")
            act_note = "the case skipped: the activation channel was not observed, so this run is not OOS coverage"
        elif markers:
            oos = evidence_block("missing", ev.get("channel", "other"))
            act_note = "activation markers not all matched (" + ", ".join(f"{mk['file']}:{'ok' if ok else 'MISSING'}" for mk, ok in matched) + ") or the case did not PASS; not OOS coverage"
        else:
            oos = evidence_block("missing")
            act_note = "no activation markers declared for this case; logical checks only, not OOS coverage"
        executed_reqs.update(c["requirements"])
        ran_configs.add(configuration_label(page_size, build_mode, run_mode))
        case_time = result["case_time_s"]
        deadline_reached = case_time is not None and case_time > case_cap
        if deadline_reached and outcome == "PASS":
            outcome = "FAIL"
            notes_extra.append(f"case time {case_time} s exceeds the {case_cap} s per-case cap: a reached deadline never reports success")
        created_at = now_iso()
        bundle_path_recorded = args.bundle_path_recorded or str(bundle)
        rel = lambda p: str(Path(p).relative_to(bundle)) if p and Path(p).exists() else None  # noqa: E731
        server_logs = sorted((ev_dir / "server_log").glob("*.err")) if (ev_dir / "server_log").is_dir() else []
        items = {
            "workload": item(bundle, "workload.sh" if (bundle / "workload.sh").exists() else f"workload/{n}.sh",
                             f"the case exactly as executed (testcase commit {testcase['commit'][:9]}; identity.txt records the committed file's hash beside it)"),
            "seed_and_generator_version": not_applicable("fixed deterministic workload; no generator and no seed") if not c.get("seed") else item(bundle, "seed.txt", "seed and generator version"),
            "session_and_barrier_trace": (item(bundle, rel(ev_dir / "operations.journal"), "the case's ordered external operation journal: request and acknowledgement per transaction, crash, restart, observations, final outcome" + ("; single-session, so no participant barrier" if c.get("single_session", True) else ""))
                                          if (ev_dir / "operations.journal").exists() else
                                          (not_applicable("single-session case without an operation journal: no schedule to acknowledge") if c.get("single_session", True)
                                           else item(bundle, None, "multi-session case wrote no operations journal"))),
            "injection_acknowledgements": not_applicable("unmodified engine, no fault armed"),
            "engine_identity": item(bundle, "identity.txt", "baseline commit, install prefix, cubrid_rel and the sha256 of libcubrid.so, libcubridsa.so, cub_server and csql, verified against ticket 11 before the launcher started; CTP jar and init.sh hashes"),
            "testcase_identity": item(bundle, "identity.txt", f"repository {repository}, branch, commit {testcase['commit'][:9]}, base commit {testcase['base_commit'][:9]}"),
            "specification_identity": item(bundle, "identity.txt", "context revision and content hash, catalogue hash"),
            "build_and_configuration_identity": item(bundle, conf_path.name, f"the CTP shell configuration used (scenario, no update, no retry, campaign ports); {build_mode} build; the case's own createdb sets the {page_size} B page size; install_conf_backup/ holds the pinned install's configuration as found"),
            "instrumentation_identity": not_applicable("unmodified engine; no instrumentation worktree"),
            "fixture_identity": (item(bundle, rel(ev_dir / "createdb.out"), "the case's createdb output: database name, page size and volume options; fixture sizes are constants in workload.sh")
                                 if (ev_dir / "createdb.out").exists() else item(bundle, "identity.txt", "no createdb output captured; the fixture is described by workload.sh")),
            "expected_versus_actual": item(bundle, eva_path.name if eva_path else None,
                                           (f"expected side from the oracle's ordered assertion table ({len(oracle_rows)} rows), actual side the .result file, compared by number, status and full name; verdict {verdict}" if oracle_rows
                                            else f"actual side only (no oracle table given); tally against the declared count; verdict {verdict}") if eva_path else "no comparison file"),
            "logs": (item(bundle, rel(server_logs[0]), "the server's own error log for the case's database (recovery lines included); CTP runtime logs and the PTY transcript sit beside it")
                     if server_logs else item(bundle, "ctp_runtime_logs/feedback.log", "CTP's feedback log (per-assertion lines); no server log was captured by the case")),
            "cores": (item(bundle, "cores", "core files found under the install or the bundle") if (bundle / "cores").exists() and any((bundle / "cores").iterdir())
                      else not_applicable("no core file: a kill -9 produces none and the post-run scan found none")),
            "replay_command_with_prerequisites": item(bundle, "replay.sh", "the replay command and the prerequisites it does not create: pinned install and hashes, CTP, the testcase worktree at the recorded commit, the four free campaign ports, unprivileged user namespaces"),
        }
        complete = not any(v["state"] == "missing" for v in items.values())
        bhash = bundle_hash(bundle, write_sums=not args.read_only)
        bundle_index = {"schema_version": 1, "bundle_id": f"bundle-{attempt_id}", "attempt_id": attempt_id, "created_at": created_at,
                        "root_path": bundle_path_recorded, "total_bytes": bundle_total_bytes(bundle), "complete": complete, "items": items,
                        "uncommitted_snapshots": [{"what": "OOS-CONTEXT.md at the pinned content hash (uncommitted in the context repository at pin time, ticket 11 section 3)",
                                                   "path": "cbrd-26659/campaign/ticket11-evidence/normative-snapshot/OOS-CONTEXT.md",
                                                   "hash": "sha256:c9daf3c4ed25e16356ebf3c79c55f6bb7391d76c5664675a9aaf55cd5ac11698"}],
                        "retention": retention_for(args.kind, outcome, created_at), "minimization": None}
        drift = {k: summary.get(k) for k in ("install_conf_drift_lines", "install_databases_drift_lines", "user_shell_fm_drift_lines", "worktree_drift_lines")}
        res_owned = c.get("resources_owned") or {
            "databases": [f"the database(s) the case creates and drops (see {rel(ev_dir / 'createdb.out') or 'workload.sh'})"],
            "processes": ["cub_master started by the case", "cub_server of the case's database", "cub_pl of the case's database"],
            "ports": list(CAMPAIGN_PORTS),
            "directories": [str(Path(bundle_path_recorded).parent.parent), str(worktree / decl["scenario"])],
        }
        cleanup = {"performed": True,
                   "scope_verified": namespace == "campaign_ns.sh" and all(v in (None, "0") for v in drift.values()),
                   "evidence_preserved_first": True,
                   "evidence": ((f"The whole invocation ran under campaign_ns.sh (unshare --user --map-current-user --pid --fork --mount-proc --ipc), so the CTP helpers' unscoped `pkill cub` and `ipcrm` sweep could reach only processes and IPC segments this invocation started, and the launcher's exit tore them all down. " if namespace == "campaign_ns.sh"
                                 else f"Namespace containment: {namespace}. ")
                                + "HOME was redirected to a campaign-owned directory seeded from the pinned install so CTP's reset of $CUBRID/conf could not install a foreign configuration. Install hygiene by hashing before and after: "
                                + ", ".join(f"{k}={v}" for k, v in drift.items() if v is not None) + ". "
                                + "Launcher artifacts, the case's result and evidence files were copied into the bundle before the install's conf and databases were restored verbatim.")}
        notes = (f"{args.kind} attempt of {n}, CTP shell runner, {build_mode} build, {run_mode}, {page_size} B pages. "
                 f"Measured: {result['executed']} executed assertions ({result['ok']} OK, {result['nok']} NOK), {result['skipped']} SKIP line(s); "
                 f"case time {case_time} s; case_outcome file: {case_outcome_file.read_text().strip() if case_outcome_file.exists() else 'absent'}; "
                 f"expected-versus-actual {verdict}. OOS-path evidence: {act_note}. " + " ".join(notes_extra))
        attempt = attempt_skeleton(attempt_id, args.kind, case_identity, c["requirements"],
                                   args.manifest_id if args.kind == "original" else f"none: {args.kind} attempts have no manifest and no matrix row (schemas document section 11)",
                                   page_size, build_mode, run_mode, started_at, ended_at, case_cap, deadline_reached, outcome,
                                   skip_reason if outcome == "SKIP" else (skip_reason if outcome in ("UNSUPPORTED", "BLOCKED") else None),
                                   {"executed": result["executed"], "failed": result["nok"]},
                                   str(Path(bundle_path_recorded) / eva_path.name) if eva_path else None, oos, res_owned, cleanup,
                                   bundle_path_recorded, bhash, notes)
        attempt_records.append(attempt)
        bundle_indexes.append(bundle_index)
        cases_out.append({"case": case_identity, "requirements": c["requirements"], "outcome": outcome,
                          "skip_reason": attempt["skip_reason"],
                          "assertions": {"expected": exp_count, "executed": result["executed"], "failed": result["nok"]},
                          "oos_evidence": oos,
                          "attempts": [{"attempt_id": attempt_id, "attempt_record": docs_relative(evidence_dir / f"{attempt_id}.json"),
                                        "bundle": bundle_path_recorded, "bundle_hash": bhash}],
                          "outstanding": None})

    verdict = "failure-of-proof" if mismatches else "proven"
    services = decl.get("services") or [
        {"kind": "cub_master", "identity": f"started (and crashed where the case does so) by the case; port {CAMPAIGN_PORTS[0]}", "port": CAMPAIGN_PORTS[0], "owned": True},
        {"kind": "cub_server", "identity": "the case's own database server", "port": None, "owned": True},
        {"kind": "other", "identity": "cub_pl of the case's database, started by the server", "port": None, "owned": True}]
    runner = {"kind": "ctp-shell", "ctp_fingerprint": ctp_fingerprint("ctp-shell", ident.get("ctp_home")),
              "command": ident.get("command", f"campaign_ns.sh {sys.argv[0] and ''}/home/vimkim/CTP/bin/ctp.sh shell -c {conf_path}"),
              "scenario_selection": scenario_abs}
    manifest = manifest_skeleton(args.manifest_id, args.producer_version, started_at, ended_at, args.tier, args.cap_reached,
                                 gib(bundle_total_bytes(bundle)), ident.get("storage_root", str(bundle.parent.parent)),
                                 engine, testcase, page_size, build_mode, run_mode, services, runner,
                                 inv_cap_override=args.cap_seconds)
    dest_dir = evidence_dir / args.manifest_id
    setup_log_rel = None
    if args.kind == "original":
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "case-list.txt").write_text(case_list_text)
        shutil.copyfile(bundle / "summary.txt", dest_dir / "summary.txt")
        setup_log_rel = docs_relative(dest_dir / "summary.txt")
    without_case = [r for r in assertable_requirement_ids() if r not in executed_reqs]
    manifest.update({
        "expected": {"case_list": docs_relative(dest_dir / "case-list.txt"), "case_list_hash": case_list_hash,
                     "case_count": len(declared), "assertion_count": total_expected_assertions if all_declared_counts else None},
        "discovered": {"case_count": len(discovered), "case_names": discovered},
        "executed": {"case_count": executed_count, "assertion_count": total_executed_assertions},
        "proof": {"verdict": verdict, "launcher_exit_status": launcher_exit, "setup_log": setup_log_rel, "mismatches": mismatches},
        "cases": cases_out,
        "outstanding_coverage": {
            "cases_not_executed": [c_["case"]["name"] for c_ in cases_out if c_["outcome"] is None],
            "configurations_not_run": configurations_not_run(ran_configs),
            "requirements_without_executed_case": without_case,
            "note": ("GENERATED by ctp_shell_records.py. PROOF: declared case count == dispatched == total_executed_case_count in test_status.data; every declared case left a .result file with at least one OK or NOK line; the launcher exit status is recorded but never used as proof (ticket 14 finding b). "
                     "ASSERTION COUNTS ARE MEASURED: one `<case>-<n> : OK|NOK` line per assertion; SKIP lines share the numbering and are never counted (ticket 14 finding a). "
                     "THE CASE OUTCOME IS THE CASE'S OWN (case_outcome file), never CTP's success count; any NOK is FAIL. "
                     "CONFIGURATIONS_NOT_RUN RULE (ticket 35 F4): every page-size x build-mode x run-mode combination of the 12-combination domain that the CTP case did not run in this invocation; this invocation ran "
                     + (", ".join(sorted(ran_configs)) or "no case") + f". REQUIREMENTS_WITHOUT_EXECUTED_CASE RULE: every catalogue requirement with status assertable or observation-only not cited by a case executed in this invocation ({len(without_case)} of {len(assertable_requirement_ids())}); BLOCKED and UNSUPPORTED requirements are not listed. "
                     + "RECOVERY-LOG CHANNEL: recorded as `other` with an explicit reference until ticket 12 decides on a `recovery-log` enum value (ticket 14 section 10, request 4)."
                     + (" FAILURE OF PROOF: " + "; ".join(m["detail"] for m in mismatches) if mismatches else "")),
        },
        "answer_promotions": [],
    })
    written = []
    if args.kind == "original":
        write_record(manifest, "manifest", evidence_dir / f"{args.manifest_id}.json")
        written.append(str(evidence_dir / f"{args.manifest_id}.json"))
    for att in attempt_records:
        write_record(att, "attempt-record", evidence_dir / f"{att['attempt_id']}.json")
        written.append(str(evidence_dir / f"{att['attempt_id']}.json"))
    for bi in bundle_indexes:
        write_record(bi, "replay-bundle", evidence_dir / f"{bi['bundle_id']}.json")
        written.append(str(evidence_dir / f"{bi['bundle_id']}.json"))
    print(f"[ctp_shell_records] proof={verdict} mismatches={len(mismatches)} cases={[(c_['case']['name'], c_['outcome']) for c_ in cases_out]}")
    for w in written:
        print(f"[ctp_shell_records] wrote {w}")
    return 0 if verdict == "proven" else 1


if __name__ == "__main__":
    sys.exit(main())
