#!/usr/bin/env python3
"""Turn one CTP SQL invocation into campaign records (ticket 15).

    ctp_sql_records.py build --bundle DIR --result-dir DIR --declarations FILE
                             --manifest-id ID --attempt-ids a,b,... --evidence-dir DIR
                             [--kind original|checker-validation|coexistence]
                             [--activation CASE=DIR ...] [--read-only] [--promotions FILE]
                             [--producer-version TEXT] [--tier fast] [--cap-reached]

Reads what the launcher and the wrapper left behind and writes, after validating each
against ticket 12's schemas, one manifest (kind original only), one attempt record per
executed case and one replay-bundle index per attempt. Nothing invalid is ever written.

What it reads, and the rules encoded (sources in brackets):

* `<result-dir>/main.info` (execute_case, success, fail, total) and `summary.info`
  (okList, nokList, notRunList, per-case totalTime). NEVER the launcher exit status, which
  is 0 on failures and on unexecuted cases [ticket 13 findings a, b]. NEVER `hasAnswer`,
  which is `false` on every run [ticket 13 finding d, independent review O1].
* A case in `notRunList` (CTP found no .answer: `shouldRun=false`, `isSuccessFul=true`,
  `execute_case` short by one) is a failure of proof, kind `case-not-executed`, never a
  pass [ticket 13 finding a, spec "Campaign manifest"].
* Declared cases absent from the scenario or from CTP's discovery are `case-not-discovered`;
  discovered cases nobody declared are `unexpected-case`; any mismatch sets
  `proof.verdict` to `failure-of-proof` [ticket 12 section 3].
* Outcome mapping: okList (result equals answer byte for byte) -> PASS; nokList -> FAIL;
  not run -> outcome null plus `outstanding`. The SQL seam has no SKIP, UNSUPPORTED or
  BLOCKED signal of its own; UNSUPPORTED/BLOCKED come from the declaration when the case
  declares that its requirement's catalogue status is UNSUPPORTED/BLOCKED [decision 07].
* The SQL runner has no assertion counter: `executed.assertion_count` and the per-case
  `assertions.executed` are null; a hand-derived count from the declaration goes into
  `outstanding_coverage.note` with its derivation [ticket 35 F3, schemas document section 11].
* `configurations_not_run` enumerates the 12-combination domain minus what the CTP case ran
  in this invocation [ticket 35 F4].
* The paired activation check is read from its output directory; `proven` only when it ran
  in the case's own run mode, `reused` only with a declared applicability block, otherwise
  `missing` [user decision O2 in ticket 35; ticket 12 section 3].

Bundle layout expected (the wrapper writes it; a ticket 13 bundle is accepted too):
  ctp.log, timing.txt, identity.txt, sql_*.conf (the CTP configuration used), workload.sql or
  workload/<case>.sql, expected.answer or expected/<case>.answer, actual.result or
  candidate.result or actual/<case>.result, activation/<case>/ (optional), ctp_result/
  (optional copy of the result directory).
"""
from __future__ import annotations

import argparse
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign_records import (  # noqa: E402
    CAMPAIGN_PORTS, RecordError, TIER_CAPS, TOOL_VERSION, assertable_requirement_ids, bundle_hash,
    bundle_total_bytes, configuration_label, configurations_not_run, ctp_fingerprint, docs_relative,
    gib, item, load_json, not_applicable, now_iso, read_kv, requirement, retention_block, sha256_bytes,
    sha256_file, sha256_prefixed, write_record,
)
from record_builders import (  # noqa: E402
    retention_for,
    attempt_skeleton, declared_case_list_text, engine_identity_from, evidence_block, load_declarations,
    manifest_skeleton, parse_identity, read_activation, testcase_identity_from,
)


def parse_main_info(result_dir: Path) -> dict:
    out = {}
    for line in (result_dir / "main.info").read_text(errors="replace").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    for k in ("execute_case", "success", "fail", "total"):
        if k not in out:
            raise RecordError(f"{result_dir}/main.info has no {k!r} line")
        out[k] = int(out[k])
    return out


def parse_summary_info(result_dir: Path) -> dict:
    """{case name: {list: ok|nok|notRun, totalTime_ms, caseFile, hasAnswer, shouldRun, isSuccessFul}}"""
    tree = ET.parse(result_dir / "summary.info")
    cases = {}
    for child in tree.getroot().iter("summary"):
        for list_name in ("okList", "nokList", "notRunList"):
            lst = child.find(list_name)
            if lst is None:
                continue
            for cr in lst.findall("caseresult"):
                case_file = (cr.findtext("caseFile") or "").strip()
                name = (cr.findtext("caseName") or Path(case_file).stem).strip()
                if not name:
                    continue
                cases[name] = {
                    "list": list_name[:-4],
                    "totalTime_ms": int((cr.findtext("totalTime") or "0").strip() or 0),
                    "caseFile": case_file,
                    "hasAnswer": (cr.findtext("hasAnswer") or "").strip(),   # recorded, never used
                    "shouldRun": (cr.findtext("shouldRun") or "").strip(),
                    "isSuccessFul": (cr.findtext("isSuccessFul") or "").strip(),
                }
    return cases


def find_one(bundle: Path, names, case_name=None):
    for n in names:
        p = bundle / n
        if p.exists():
            return p
    if case_name:
        for sub, ext in (("workload", ".sql"), ("expected", ".answer"), ("actual", ".result")):
            p = bundle / sub / f"{case_name}{ext}"
            if p.exists() and any(n.endswith(ext) for n in names):
                return p
    return None


def parse_ctp_conf(conf_path: Path) -> dict:
    """Ports and db options from the CTP SQL configuration (ini-like, sections in brackets)."""
    section = ""
    out = {"cubrid_port_id": None, "broker_port": None, "createdb_opts": "", "scenario": None, "ha_port_id": None}
    for raw in conf_path.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            section = line.strip("[]")
            continue
        if "=" not in line:
            continue
        k, v = (x.strip() for x in line.split("=", 1))
        if section == "sql/cubrid.conf" and k == "cubrid_port_id":
            out["cubrid_port_id"] = int(v)
        elif section.startswith("sql/cubrid_broker.conf/%BROKER1") and k == "BROKER_PORT":
            out["broker_port"] = int(v)
        elif section == "sql/cubrid_ha.conf" and k == "ha_port_id":
            out["ha_port_id"] = int(v)
        elif section == "sql" and k == "cubrid_createdb_opts":
            out["createdb_opts"] = v
        elif section == "sql" and k == "scenario":
            out["scenario"] = v
    return out


def page_size_from_createdb_opts(opts: str, default=16384) -> int:
    for tok in opts.split():
        if tok.startswith("--db-page-size="):
            return int(tok.split("=", 1)[1])
    return default


def diff_text(expected: Path | None, actual: Path | None) -> tuple[str, str]:
    """(verdict, text). MATCH when both exist and are byte-identical."""
    if expected is None or actual is None:
        return "INCOMPLETE", (f"# expected: {expected}\n# actual:   {actual}\n"
                              "# one side is missing; no comparison possible\n")
    e, a = expected.read_bytes(), actual.read_bytes()
    if e == a:
        return "MATCH", (f"# expected {sha256_file(expected)}  {expected.name}\n"
                         f"# actual   {sha256_file(actual)}  {actual.name}\n"
                         "# byte-identical: CTP's whole-result comparison and this one agree\n")
    import difflib
    d = difflib.unified_diff(e.decode(errors="replace").splitlines(True), a.decode(errors="replace").splitlines(True),
                             fromfile=f"expected/{expected.name}", tofile=f"actual/{actual.name}")
    return "MISMATCH", (f"# expected {sha256_file(expected)}  {expected.name}\n"
                        f"# actual   {sha256_file(actual)}  {actual.name}\n") + "".join(d)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--bundle", required=True)
    b.add_argument("--result-dir", required=True)
    b.add_argument("--declarations", required=True)
    b.add_argument("--manifest-id", required=True)
    b.add_argument("--attempt-ids", required=True, help="comma-separated, assigned to declared cases in sorted order")
    b.add_argument("--evidence-dir", required=True)
    b.add_argument("--kind", default="original", choices=["original", "checker-validation", "coexistence"])
    b.add_argument("--activation", action="append", default=[], help="CASE=DIR of the activation checker output")
    b.add_argument("--read-only", action="store_true", help="never write into the bundle (sealed retained bundle)")
    b.add_argument("--promotions", help="JSON list of answer_promotions entries recorded by the reviewer")
    b.add_argument("--producer-version", default=TOOL_VERSION)
    b.add_argument("--tier", default="fast", choices=list(TIER_CAPS))
    b.add_argument("--cap-reached", action="store_true")
    b.add_argument("--cap-seconds", type=int, help="invocation cap actually enforced when it differs from the tier's")
    b.add_argument("--launcher-exit", type=int, default=None)
    b.add_argument("--build-mode", choices=["release", "debug"])
    b.add_argument("--run-mode", default="client-server", choices=["client-server", "standalone"])
    b.add_argument("--bundle-path-recorded", help="path to record for the bundle (default: --bundle)")
    b.add_argument("--activation-evidence-copy", action="store_true",
                   help="copy each checker's assertions.txt into <evidence-dir>/<manifest-id>/ and cite that path")
    args = ap.parse_args(argv)
    try:
        return build(args)
    except RecordError as exc:
        print(f"[ctp_sql_records] REFUSED: {exc}", file=sys.stderr)
        return 2


def build(args) -> int:
    bundle = Path(args.bundle).resolve()
    result_dir = Path(args.result_dir).resolve()
    evidence_dir = Path(args.evidence_dir)
    decl = load_declarations(args.declarations)
    if decl["runner"] != "ctp-sql":
        raise RecordError("declarations are not for the ctp-sql runner")
    repository = decl["repository"]
    ident = parse_identity(bundle / "identity.txt")
    timing = read_kv(bundle / "timing.txt")
    if (result_dir / "main.info").exists():
        main_info = parse_main_info(result_dir)
        summary = parse_summary_info(result_dir)
        no_result_dir = False
    else:
        main_info = {"execute_case": 0, "success": 0, "fail": 0, "total": 0, "cubrid_rel": None}
        summary = {}
        no_result_dir = True
    conf_path = next(iter(sorted(bundle.glob("sql_*.conf"))), None)
    if conf_path is None:
        raise RecordError(f"no sql_*.conf (the CTP configuration used) in {bundle}")
    conf = parse_ctp_conf(conf_path)
    build_mode = args.build_mode or ident.get("build_mode") or ("debug" if "debug_gcc" in ident.get("install_prefix", ident.get("install", "")) else "release")
    run_mode = ident.get("run_mode", args.run_mode)
    page_size = int(ident.get("page_size") or page_size_from_createdb_opts(conf["createdb_opts"]))
    started_at = timing.get("started_at") or ident.get("started_at")
    ended_at = timing.get("ended_at")
    if not (started_at and ended_at):
        raise RecordError("timing.txt must carry started_at and ended_at")
    launcher_exit = args.launcher_exit if args.launcher_exit is not None else (
        int(timing["ctp_exit"]) if "ctp_exit" in timing else None)
    engine = engine_identity_from(ident, build_mode, main_info.get("cubrid_rel") or ident.get("cubrid_rel"))
    testcase = testcase_identity_from(ident, repository)
    worktree = Path(testcase["worktree"])
    scenario_abs = conf["scenario"] or str(worktree / decl["scenario"])
    inv_cap, case_cap = TIER_CAPS[args.tier]

    # --- declared, repository-discovered, CTP-discovered, executed --------------------------
    declared = sorted(decl["cases"])
    case_list_text = declared_case_list_text(decl)
    case_list_hash = "sha256:" + sha256_bytes(case_list_text.encode())
    repo_cases = set()
    scenario_dir = worktree / decl["scenario"]
    for p in scenario_dir.rglob("*.sql"):
        if p.parent.name == "cases":
            repo_cases.add(p.stem)
    ctp_names = sorted(summary)
    executed = [n for n in ctp_names if summary[n]["list"] in ("ok", "nok")]
    mismatches = []
    for n in declared:
        if n not in repo_cases and n not in summary:
            mismatches.append({"kind": "case-not-discovered",
                               "detail": f"declared case {n} ({decl['cases'][n]['path']}) exists neither under "
                                         f"{scenario_dir} nor in CTP's summary.info"})
        elif n not in summary:
            mismatches.append({"kind": "case-not-discovered",
                               "detail": f"declared case {n} is in the scenario tree but CTP's summary.info does not list it"})
        elif summary[n]["list"] == "notRun":
            mismatches.append({"kind": "case-not-executed",
                               "detail": f"declared case {n} is in CTP's notRunList (shouldRun={summary[n]['shouldRun']}, "
                                         f"isSuccessFul={summary[n]['isSuccessFul']}): CTP found no .answer and did not run it; "
                                         "execute_case fell short. Failure of proof, never a pass (ticket 13 finding a)"})
    for n in ctp_names:
        if n not in decl["cases"]:
            mismatches.append({"kind": "unexpected-case", "detail": f"CTP discovered {n} ({summary[n]['caseFile']}), which no declaration names"})
    for n in sorted(repo_cases - set(declared)):
        if n not in summary:
            mismatches.append({"kind": "unexpected-case", "detail": f"{n}.sql is under {scenario_dir}/cases but is neither declared nor in CTP's summary"})
    if main_info["execute_case"] != len(executed):
        mismatches.append({"kind": "case-not-executed",
                           "detail": f"main.info execute_case={main_info['execute_case']} but summary.info lists {len(executed)} executed case(s)"})
    if main_info["total"] != len(declared):
        mismatches.append({"kind": "case-not-discovered",
                           "detail": f"main.info total={main_info['total']} differs from the declared count {len(declared)}"})
    if launcher_exit not in (0, None):
        mismatches.append({"kind": "launcher-exit-mismatch", "detail": f"launcher exit status {launcher_exit}" + (" (124: the wrapper's invocation-cap timeout ended the launcher)" if launcher_exit == 124 else "")})
    if no_result_dir:
        mismatches.append({"kind": "setup-log-error", "detail": "CTP wrote no result directory (no main.info): the launcher did not reach execution" + (" because the invocation cap ended it" if args.cap_reached else "")})
    ctp_log = bundle / "ctp.log"
    if ctp_log.exists():
        text = ctp_log.read_text(errors="replace")
        # "Could not connect to master server" is printed by every run (do_clean stops a server
        # that is not running before setup) and is therefore not an error signal.
        for needle in ("No Results!!", "createdb FAILED", "ClassNotFoundException", "NoClassDefFoundError",
                       "Please confirm JAVA_HOME"):
            if needle in text:
                mismatches.append({"kind": "setup-log-error", "detail": f"launcher log contains {needle!r}"})
    else:
        mismatches.append({"kind": "setup-log-error", "detail": "no ctp.log (launcher transcript) in the bundle"})

    # --- per case ---------------------------------------------------------------------------
    attempt_ids = [a for a in args.attempt_ids.split(",") if a]
    activation_dirs = dict(a.split("=", 1) for a in args.activation)
    promotions = load_json(args.promotions) if args.promotions else []
    cases_out, attempt_records, bundle_indexes = [], [], []
    executed_reqs = set()
    ran_configs = set()
    aid_iter = iter(attempt_ids)
    for n in declared:
        c = decl["cases"][n]
        case_identity = {"repository": repository, "path": c["path"], "name": n}
        entry = summary.get(n)
        if entry is None or entry["list"] == "notRun":
            reason = "prerequisite-missing" if entry is not None else ("cap-reached" if args.cap_reached else "not-discovered")
            detail = ("CTP found no .answer file for the case and put it in notRunList without executing it; "
                      "bootstrap the case with an empty .answer (ticket 13 finding a)" if entry is not None
                      else ("the invocation cap ended the launcher before the case was reached; evidence captured so far is in the bundle"
                            if args.cap_reached else "the case was not discovered by CTP; see proof.mismatches"))
            cases_out.append({"case": case_identity, "requirements": c["requirements"], "outcome": None,
                              "skip_reason": None,
                              "assertions": {"expected": c.get("expected_assertions"), "executed": None, "failed": 0},
                              "oos_evidence": evidence_block("missing"), "attempts": [],
                              "outstanding": {"reason": reason, "detail": detail}})
            continue
        attempt_id = next(aid_iter, None)
        if attempt_id is None:
            raise RecordError("fewer --attempt-ids than executed cases")
        outcome = "PASS" if entry["list"] == "ok" else "FAIL"
        declared_outcome = c.get("declared_outcome")
        notes_extra = []
        if declared_outcome in ("UNSUPPORTED", "BLOCKED"):
            statuses = {requirement(r)["status"] for r in c["requirements"]}
            if declared_outcome in statuses:
                notes_extra.append(f"outcome {declared_outcome} declared by the case from its requirement's catalogue status; "
                                   f"CTP classified the run as {entry['list']}")
                outcome = declared_outcome
            else:
                raise RecordError(f"{n} declares {declared_outcome} but no cited requirement has that catalogue status")
        # expected versus actual
        workload = find_one(bundle, ["workload.sql"], n)
        answer = find_one(bundle, ["expected.answer"], n)
        actual = find_one(bundle, ["actual.result", "candidate.result"], n)
        verdict, dtext = diff_text(answer, actual)
        eva_path = bundle / ("expected_vs_actual.diff" if len(declared) == 1 else f"expected_vs_actual_{n}.diff")
        if not args.read_only:
            eva_path.write_text(dtext)
        elif not eva_path.exists():
            eva_path = None
        if verdict == "MISMATCH" and outcome == "PASS":
            outcome = "FAIL"
            notes_extra.append("CTP listed the case as OK but the retained answer and result differ; recorded FAIL, never PASS")
        if verdict == "MATCH" and outcome == "FAIL":
            notes_extra.append("CTP listed the case as failed although the retained expected.answer and result are identical: "
                               "the retained files may not be the pair CTP compared; FAIL is kept")
        failed = 0 if outcome == "PASS" else 1
        # activation evidence
        act_dir = activation_dirs.get(n)
        oos, act_note = read_activation(act_dir, run_mode, c.get("activation_check"))
        if oos.get("applicability"):
            # the checker ran in this invocation, so this manifest is the evidence's source
            oos["applicability"] = dict(oos["applicability"], source_manifest=args.manifest_id if args.kind == "original" else "none (not a suite invocation)")
        if oos["status"] in ("proven", "reused") and act_dir:
            ref = Path(act_dir) / "assertions.txt"
            if args.activation_evidence_copy:
                dest_dir = evidence_dir / args.manifest_id
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f"activation_{n}_{build_mode}.txt"
                shutil.copyfile(ref, dest)
                oos["reference"] = docs_relative(dest)
            else:
                oos["reference"] = str(ref)
        if c.get("oos_evidence_when_unchecked") == "not-applicable" and oos["status"] == "missing" and not act_dir:
            oos = evidence_block("not-applicable")
            act_note = c.get("oos_evidence_note", "the case asserts a non-activation property; declared not-applicable")
        executed_reqs.update(c["requirements"])
        ran_configs.add(configuration_label(page_size, build_mode, run_mode))
        case_ms = entry["totalTime_ms"]
        deadline_reached = case_ms / 1000.0 > case_cap
        if deadline_reached and outcome == "PASS":
            outcome = "FAIL"
            notes_extra.append(f"the case ran {case_ms} ms, over the {case_cap} s per-case cap: a reached deadline never reports success")
        # bundle index
        created_at = now_iso()
        bundle_path_recorded = args.bundle_path_recorded or str(bundle)
        items = {
            "workload": item(bundle, workload.relative_to(bundle).as_posix() if workload else None,
                             f"the case file as executed (testcase commit {testcase['commit'][:9]})"),
            "seed_and_generator_version": not_applicable("fixed deterministic workload; no generator and no seed") if not c.get("seed") else item(bundle, "seed.txt", "seed and generator version"),
            "session_and_barrier_trace": not_applicable("single-session SQL case: no barrier to acknowledge") if c.get("single_session", True) else item(bundle, "barrier_trace.txt", "session and barrier trace"),
            "injection_acknowledgements": not_applicable("unmodified engine, no fault armed"),
            "engine_identity": item(bundle, "identity.txt", "baseline commit, install prefix, cubrid_rel, library sha256 values verified against ticket 11 before the launcher started"),
            "testcase_identity": item(bundle, "identity.txt", f"repository {repository}, branch, commit {testcase['commit'][:9]}, base commit {testcase['base_commit'][:9]}"),
            "specification_identity": item(bundle, "identity.txt", "context revision and content hash, catalogue hash"),
            "build_and_configuration_identity": item(bundle, conf_path.name, f"the CTP SQL configuration used (createdb options set the {page_size} B page size; ports); {build_mode} build, {run_mode}"),
            "instrumentation_identity": not_applicable("unmodified engine; no instrumentation worktree"),
            "fixture_identity": item(bundle, "identity.txt", f"CTP database `basic` created with {conf['createdb_opts'] or 'default createdb options'} under the campaign-private CUBRID_DATABASES named in identity.txt"),
            "expected_versus_actual": item(bundle, eva_path.name if eva_path else None,
                                           f"answer versus result: {verdict}; expected.answer and the retained result file sit beside it" if eva_path else
                                           "no expected-versus-actual comparison could be built: the answer or the result file is not in the bundle"),
            "logs": item(bundle, "ctp.log", "the launcher transcript (setup, discovery, execution, do_clean); ctp_result/ holds main.info and summary.info"),
            "cores": (item(bundle, "cores", "core files found by the launcher's core scan or under the install") if (bundle / "cores").exists() and any((bundle / "cores").iterdir())
                      else not_applicable("no core file: the launcher's core scan found none (it proceeded to do_clean)")),
            "replay_command_with_prerequisites": item(bundle, "replay.sh" if (bundle / "replay.sh").exists() else "replay_command.txt",
                                                      "the replay command and the prerequisites it does not create (pinned install with the JDBC client artifact, CTP, the testcase worktree at the recorded commit, free campaign ports, unprivileged user namespaces)"),
        }
        complete = not any(v["state"] == "missing" for v in items.values())
        if not args.read_only:
            bhash = bundle_hash(bundle, write_sums=True)
            # SHA256SUMS changed total bytes; recompute after writing
        else:
            bhash = bundle_hash(bundle, write_sums=False)
        bundle_index = {
            "schema_version": 1, "bundle_id": f"bundle-{attempt_id}", "attempt_id": attempt_id,
            "created_at": created_at, "root_path": bundle_path_recorded, "total_bytes": bundle_total_bytes(bundle),
            "complete": complete, "items": items,
            "uncommitted_snapshots": [{"what": "OOS-CONTEXT.md at the pinned content hash (uncommitted in the context repository at pin time, ticket 11 section 3)",
                                       "path": "cbrd-26659/campaign/ticket11-evidence/normative-snapshot/OOS-CONTEXT.md",
                                       "hash": "sha256:c9daf3c4ed25e16356ebf3c79c55f6bb7391d76c5664675a9aaf55cd5ac11698"}],
            "retention": retention_for(args.kind, outcome, created_at), "minimization": None,
        }
        res_owned = c.get("resources_owned") or {
            "databases": [f"basic (CTP-created under the campaign-private CUBRID_DATABASES {ident.get('cubrid_databases', 'recorded in identity.txt')})"]
                         + ([f"{c['activation_check'].get('database', 'activation-check database')} (paired activation checker)"] if act_dir else []),
            "processes": [f"cub_master port {conf['cubrid_port_id']}", "cub_server basic", f"broker BROKER1 port {conf['broker_port']}"],
            "ports": sorted({p for p in (conf["cubrid_port_id"], conf["broker_port"], conf["ha_port_id"]) if p}),
            "directories": [str(Path(bundle_path_recorded).parent.parent)],
        }
        ns = ident.get("namespace", "unknown")
        drift = {k: ident.get(k) for k in ("install_conf_drift_lines", "install_databases_drift_lines", "worktree_drift_lines")}
        cleanup = {
            "performed": True,
            "scope_verified": ns == "campaign_ns.sh" and all(v == "0" for v in drift.values() if v is not None),
            "evidence_preserved_first": True,
            "evidence": (f"Namespace: {ns}. " + ("The whole invocation ran under campaign_ns.sh (unshare --user --map-current-user --pid --fork --mount-proc --ipc), so CTP's unscoped `pkill cub` and ipcrm sweep could reach only processes and segments this invocation started; the launcher's exit tore the namespace down. " if ns == "campaign_ns.sh" else "The invocation did not run under campaign_ns.sh; CTP's `pkill cub` was unscoped and only the kernel's EPERM protected other users' processes (ticket 13 att-T13-0002 cleanup note). ")
                         + f"Install hygiene by hashing before and after: conf drift {drift['install_conf_drift_lines']}, databases drift {drift['install_databases_drift_lines']}, testcase worktree drift {drift['worktree_drift_lines']} (None = not measured by this bundle's producer). "
                         "All launcher artifacts were copied into the bundle before the install and worktree were restored."),
        }
        notes = (f"{args.kind} attempt of {n}, CTP SQL runner, {build_mode} build, {run_mode}, {page_size} B pages. "
                 f"CTP listed the case in {entry['list']}List with totalTime {case_ms} ms; expected-versus-actual {verdict}. "
                 "assertions.executed is null because the CTP SQL runner has no assertion counter (ticket 35 F3); "
                 + (f"the declared hand-derived count is {c['expected_assertions']} ({c.get('assertion_count_derivation', 'derivation not declared')}). " if c.get("expected_assertions") else "")
                 + f"OOS-path evidence: {act_note}. "
                 + " ".join(notes_extra))
        attempt = attempt_skeleton(attempt_id, args.kind, case_identity, c["requirements"],
                                   args.manifest_id if args.kind == "original" else f"none: {args.kind} attempts have no manifest and no matrix row (schemas document section 11)",
                                   page_size, build_mode, run_mode, started_at, ended_at, case_cap, deadline_reached,
                                   outcome, None, {"executed": None, "failed": failed},
                                   str(Path(bundle_path_recorded) / eva_path.name) if eva_path else None, oos,
                                   res_owned, cleanup, bundle_path_recorded, bhash, notes)
        attempt_records.append(attempt)
        bundle_indexes.append(bundle_index)
        cases_out.append({"case": case_identity, "requirements": c["requirements"], "outcome": outcome, "skip_reason": None,
                          "assertions": {"expected": c.get("expected_assertions"), "executed": None, "failed": failed},
                          "oos_evidence": oos,
                          "attempts": [{"attempt_id": attempt_id, "attempt_record": docs_relative(evidence_dir / f"{attempt_id}.json"),
                                        "bundle": bundle_path_recorded, "bundle_hash": bhash}],
                          "outstanding": None})

    # --- manifest ---------------------------------------------------------------------------
    verdict = "failure-of-proof" if mismatches else "proven"
    services = [{"kind": "cub_master", "identity": f"CTP-owned master, port {conf['cubrid_port_id']}", "port": conf["cubrid_port_id"], "owned": True},
                {"kind": "cub_server", "identity": "basic", "port": None, "owned": True},
                {"kind": "broker", "identity": f"BROKER1 port {conf['broker_port']}", "port": conf["broker_port"], "owned": True}]
    runner = {"kind": "ctp-sql", "ctp_fingerprint": ctp_fingerprint("ctp-sql", ident.get("ctp_home")),
              "command": ident.get("command", f"ctp.sh sql -c {conf_path}"), "scenario_selection": scenario_abs}
    manifest = manifest_skeleton(args.manifest_id, args.producer_version, started_at, ended_at, args.tier, args.cap_reached,
                                 gib(bundle_total_bytes(bundle)), ident.get("storage_root", str(bundle.parent.parent)),
                                 engine, testcase, page_size, build_mode, run_mode, services, runner,
                                 inv_cap_override=args.cap_seconds)
    setup_log_rel = None
    if ctp_log.exists():
        dest_dir = evidence_dir / args.manifest_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ctp_log, dest_dir / "setup.log")
        (dest_dir / "case-list.txt").write_text(case_list_text)
        setup_log_rel = docs_relative(dest_dir / "setup.log")
    declared_total = sum(decl["cases"][n].get("expected_assertions") or 0 for n in declared) if all(decl["cases"][n].get("expected_assertions") for n in declared) else None
    without_case = [r for r in assertable_requirement_ids() if r not in executed_reqs]
    manifest.update({
        "expected": {"case_list": docs_relative(evidence_dir / args.manifest_id / "case-list.txt"), "case_list_hash": case_list_hash,
                     "case_count": len(declared), "assertion_count": declared_total},
        "discovered": {"case_count": len(ctp_names), "case_names": ctp_names},
        "executed": {"case_count": main_info["execute_case"], "assertion_count": None},
        "proof": {"verdict": verdict, "launcher_exit_status": launcher_exit, "setup_log": setup_log_rel, "mismatches": mismatches},
        "cases": cases_out,
        "outstanding_coverage": {
            "cases_not_executed": [c_["case"]["name"] for c_ in cases_out if c_["outcome"] is None],
            "configurations_not_run": configurations_not_run(ran_configs),
            "requirements_without_executed_case": without_case,
            "note": ("GENERATED by ctp_sql_records.py. PROOF: expected case count == discovered == executed (execute_case in main.info) with no notRunList entry; the launcher exit status is recorded but never used as proof (ticket 13 findings a, b); hasAnswer is never read (finding d). "
                     "ASSERTION COUNTS: executed.assertion_count is null because the CTP SQL runner reports only total, success, fail and execute_case (ticket 35 F3); "
                     + ("; ".join(f"{n}: declared {decl['cases'][n]['expected_assertions']} ({decl['cases'][n].get('assertion_count_derivation', 'derivation not declared')})" for n in declared if decl['cases'][n].get('expected_assertions')) or "no hand-derived count was declared")
                     + ". CONFIGURATIONS_NOT_RUN RULE (ticket 35 F4): every page-size x build-mode x run-mode combination of the 12-combination domain that the CTP case did not run in this invocation; this invocation ran "
                     + (", ".join(sorted(ran_configs)) or "no case") + f". REQUIREMENTS_WITHOUT_EXECUTED_CASE RULE: every catalogue requirement with status assertable or observation-only not cited by a case executed in this invocation ({len(without_case)} of {len(assertable_requirement_ids())}); BLOCKED and UNSUPPORTED requirements are gaps of another kind and are not listed."
                     + (" FAILURE OF PROOF: " + "; ".join(m["detail"] for m in mismatches) if mismatches else "")),
        },
        "answer_promotions": promotions,
    })
    # auto-detected promotion events: an empty or absent answer makes the result a candidate
    for n in declared:
        entry = summary.get(n)
        if entry is None:
            continue
        answer = find_one(bundle, ["expected.answer"], n)
        if answer is not None and answer.stat().st_size == 0 and entry["list"] == "nok" and not any(p.get("case") == n for p in promotions):
            manifest["answer_promotions"].append({"case": n, "action": "candidate", "flagged_for_user": bool(decl["cases"][n].get("flagged_for_user", False)),
                                                  "review_note": "the answer was empty (bootstrap run): the first-run result is retained as a candidate in the bundle and must be reviewed against its requirements before promotion by rename",
                                                  "reviewer": None})
        elif entry["list"] == "nok" and answer is not None and answer.stat().st_size > 0 and not any(p.get("case") == n for p in promotions):
            manifest["answer_promotions"].append({"case": n, "action": "retained-as-failure-evidence", "flagged_for_user": False,
                                                  "review_note": "result differs from the reviewed answer; retained in the bundle as failure evidence, never promoted",
                                                  "reviewer": None})

    # --- write, validating first -------------------------------------------------------------
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
    print(f"[ctp_sql_records] proof={verdict} mismatches={len(mismatches)} cases={[(c_['case']['name'], c_['outcome']) for c_ in cases_out]}")
    for w in written:
        print(f"[ctp_sql_records] wrote {w}")
    return 0 if verdict == "proven" else 1


if __name__ == "__main__":
    sys.exit(main())
