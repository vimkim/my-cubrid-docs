#!/usr/bin/env python3
"""Self-test of the one-seal-per-invocation rule (ticket 44 F3, applied to the tooling by ticket 49).

    selftest_bundle_sealing.py [--keep DIR]

One bundle belongs to one invocation, so the digest and the size every attempt record, bundle
index and manifest entry of that invocation carries are the FINISHED bundle's -- computed after
the invocation's last file is written, never as each record is built. Both post-processors
sealed inside their per-case loop until campaign ticket 49, which wrote a digest of a still-growing
directory into every record but the last (64 of ticket 19's 83 records, 8 of ticket 17's 12, 8 of
ticket 47's 10). These checks build one synthetic three-case bundle per seam under a throwaway
directory, run the real post-processors on them, and assert what the rule owes:

  1. (shell) all three attempt records carry ONE digest, equal to sha256 of the SHA256SUMS the
     tool wrote, and the listing names every per-case file the tool itself wrote during the loop
     -- the proof that the seal came after the last of them;
  2. (shell) all three bundle indexes carry the finished bundle's total_bytes;
  3. (sql) the same for the three attempt records and the manifest's three bundle_hash entries;
  4. (sql) the same for total_bytes;
  5. validate_records accepts every record as written;
  6. validate_records reports an attempt record whose digest was planted back to the
     still-growing value (the ticket 17 defect), and one whose total_bytes was;
  7. seal_bundle_records refuses a record that was sealed before the loop ended.

Every identifier carries SELFTEST so nothing here can be mistaken for campaign evidence. The
synthetic identity carries the campaign's pinned library hashes as text: no engine, no CTP tree
and no database is involved. Exit 0 when every check holds.
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
    ENGINE_BASELINE_COMMIT, LIBRARY_HASHES, SEAL_PENDING_HASH, RecordError, bundle_total_bytes, load_json,
    seal_bundle_records, sha256_prefixed, sha256sums_entries, write_record,
)
import ctp_shell_records  # noqa: E402
import ctp_sql_records  # noqa: E402
import validate_records  # noqa: E402

CASES = ["selftest_seal_a", "selftest_seal_b", "selftest_seal_c"]
STARTED, ENDED = "2026-09-21T10:00:00+09:00", "2026-09-21T10:00:40+09:00"
REL = "CUBRID 11.5.0 (11.5.0.2648-f4299ac) (64bit release build for Linux) (Sep 14 2026 22:45:25)"
FAILS = []


def check(n, label, ok):
    print(("PASS  " if ok else "FAIL  ") + f"{n:<4}{label}")
    if not ok:
        FAILS.append(f"{n} {label}")


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def identity_lines(tmp: Path, manifest_id: str, repository: str, scenario: Path) -> str:
    install = tmp / "install"
    return "\n".join([
        f"manifest_id={manifest_id}",
        f"engine_baseline_commit={ENGINE_BASELINE_COMMIT}",
        "engine_worktree=/home/vimkim/gh/cb/oos-baseline-f4299ac0c",
        f"install_prefix={install}",
        "build_mode=release",
        "run_mode=client-server",
        f"cubrid_rel={REL}",
        f"{LIBRARY_HASHES['release']['libcubrid.so']}  {install}/lib/libcubrid.so",
        f"{LIBRARY_HASHES['release']['libcubridsa.so']}  {install}/lib/libcubridsa.so",
        f"ctp_home={tmp / 'ctp'}",
        f"testcase_repository={repository}",
        "testcase_branch=SELFTEST",
        "testcase_commit=" + "1" * 40,
        "testcase_base_commit=" + "2" * 40,
        f"testcase_worktree={tmp / 'wt'}",
        "testcase_worktree_dirty=0",
        f"scenario={scenario}",
        f"cubrid_databases={tmp / 'ctpdb'}",
        "namespace=campaign_ns.sh",
        f"storage_root={tmp}",
        "install_conf_drift_lines=0",
        "install_databases_drift_lines=0",
        "worktree_drift_lines=0",
        "command=SELFTEST: no launcher ran",
        f"started_at={STARTED}",
    ]) + "\n"


def common_tree(tmp: Path):
    """The CTP tree the fingerprint reads and the worktree the SQL tool scans, both synthetic."""
    write(tmp / "ctp" / "shell" / "lib" / "cubridqa-shell.jar", "SELFTEST shell jar\n")
    write(tmp / "ctp" / "sql" / "lib" / "cubridqa-cqt.jar", "SELFTEST sql jar\n")


def declarations(tmp: Path, runner: str) -> Path:
    if runner == "ctp-shell":
        repo, scenario, ext, req = "testcases-private-ex", "shell/selftest", "sh", "OOS-DUR-01"
    else:
        repo, scenario, ext, req = "testcases", "sql/selftest", "sql", "OOS-SQL-01"
    decl = {"declaration_version": 1, "description": "SELFTEST declaration; never campaign evidence",
            "repository": repo, "runner": runner, "scenario": scenario, "tier": "fast", "page_size": 16384,
            "run_mode": "client-server", "cases": {}}
    for n in CASES:
        decl["cases"][n] = {"path": f"{scenario}/{n}/cases/{n}.{ext}" if runner == "ctp-shell" else f"{scenario}/cases/{n}.{ext}",
                            "requirements": [req], "expected_assertions": 1, "single_session": True,
                            "flagged_for_user": False}
    path = tmp / f"decl-{runner}.json"
    write(path, json.dumps(decl, indent=2))
    return path


def shell_bundle(tmp: Path) -> Path:
    root = tmp / "attempts" / "inv-SELFTEST-SEAL-S"
    scenario = tmp / "wt" / "shell" / "selftest"
    write(root / "identity.txt", identity_lines(tmp, "inv-SELFTEST-SEAL-S", "testcases-private-ex", scenario))
    write(root / "summary.txt", "\n".join([
        "manifest_id=inv-SELFTEST-SEAL-S", "build_mode=release", "launcher_exit_status=0", "cap_reached=0",
        "elapsed_seconds=9", "install_conf_drift_lines=0", "install_databases_drift_lines=0",
        "user_shell_fm_drift_lines=0", "worktree_drift_lines=0", f"ended_at={ENDED}"]) + "\n")
    write(root / "ctp_runtime_logs" / "test_status.data", "\n".join([
        "total_case_count=3", "total_executed_case_count=3", "total_success_case_count=3",
        "total_fail_case_count=0", "total_skip_case_count=0"]) + "\n")
    write(root / "ctp_runtime_logs" / "dispatch_tc_ALL.txt",
          "".join(f"{scenario}/{n}/cases/{n}.sh\n" for n in CASES))
    write(root / "ctp_runtime_logs" / "feedback.log", "SELFTEST feedback\n")
    write(root / "shell_inv-SELFTEST-SEAL-S.conf", "scenario=SELFTEST\n")
    write(root / "ctp.log", "SELFTEST launcher transcript\n")
    write(root / "replay.sh", "#!/bin/bash\n# SELFTEST replay\n")
    for n in CASES:
        write(root / "workload" / f"{n}.sh", f"#!/bin/bash\n# SELFTEST case {n}\n")
        write(root / f"{n}.result", f"{n}-1 : OK\n2026-09-21 10:00:03 ---- {root} --- time=1\n")
        write(scenario / n / "cases" / f"{n}.sh", f"#!/bin/bash\n# SELFTEST case {n}\n")
    return root


def sql_bundle(tmp: Path) -> Path:
    root = tmp / "attempts" / "inv-SELFTEST-SEAL-Q"
    scenario = tmp / "wt" / "sql" / "selftest"
    write(root / "identity.txt", identity_lines(tmp, "inv-SELFTEST-SEAL-Q", "testcases", scenario))
    write(root / "timing.txt", f"started_at={STARTED}\nended_at={ENDED}\nctp_exit=0\nelapsed_seconds=40\n")
    write(root / "sql_inv-SELFTEST-SEAL-Q.conf", "\n".join([
        "[sql]", f"scenario={scenario}", "cubrid_createdb_opts=--db-page-size=16384",
        "[sql/cubrid.conf]", "cubrid_port_id=26659",
        "[sql/cubrid_broker.conf/%BROKER1]", "BROKER_PORT=33120",
        "[sql/cubrid_ha.conf]", "ha_port_id=33122"]) + "\n")
    write(root / "ctp.log", "SELFTEST launcher transcript\n")
    write(root / "replay.sh", "#!/bin/bash\n# SELFTEST replay\n")
    result = root / "ctp_result" / "sql"
    write(result / "main.info", "execute_case: 3\nsuccess: 3\nfail: 0\ntotal: 3\n" + f"cubrid_rel: {REL}\n")
    okl = "".join(f"<caseresult><caseFile>{scenario}/cases/{n}.sql</caseFile><totalTime>50</totalTime>"
                  "<hasAnswer>false</hasAnswer><shouldRun>true</shouldRun><isSuccessFul>true</isSuccessFul></caseresult>"
                  for n in CASES)
    write(result / "summary.info", f"<?xml version=\"1.0\"?><results><summary><okList>{okl}</okList><nokList/><notRunList/></summary></results>\n")
    for n in CASES:
        write(root / "workload" / f"{n}.sql", f"-- SELFTEST case {n}\nSELECT 1;\n")
        write(root / "expected" / f"{n}.answer", "1\n")
        write(root / "actual" / f"{n}.result", "1\n")
        write(scenario / "cases" / f"{n}.sql", f"-- SELFTEST case {n}\nSELECT 1;\n")
    return root, result


def run(tool, argv) -> tuple:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = tool.main(argv)
    return rc, out.getvalue()


def validate(*paths) -> tuple:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = validate_records.main([str(p) for p in paths] + ["--quiet"])
    return rc, out.getvalue()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", help="keep the synthetic tree under this directory instead of a temporary one")
    args = ap.parse_args(argv)
    tmp = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="selftest-bundle-sealing-", dir=Path.home() / "tmp"))
    tmp.mkdir(parents=True, exist_ok=True)
    common_tree(tmp)

    # --- shell seam -------------------------------------------------------------------------
    sroot = shell_bundle(tmp)
    sevd = tmp / "evidence-shell"
    sdecl = declarations(tmp, "ctp-shell")
    ids = ["att-SELFTEST-SEAL-S1", "att-SELFTEST-SEAL-S2", "att-SELFTEST-SEAL-S3"]
    rc, out = run(ctp_shell_records, ["build", "--bundle", str(sroot), "--declarations", str(sdecl),
                                      "--manifest-id", "inv-SELFTEST-SEAL-S", "--attempt-ids", ",".join(ids),
                                      "--evidence-dir", str(sevd)])
    if rc != 0:
        print(out)
    sums_hash = sha256_prefixed(sroot / "SHA256SUMS")
    listed = sha256sums_entries(sroot / "SHA256SUMS")
    hashes = [load_json(sevd / f"{a}.json")["bundle"]["hash"] for a in ids]
    last_written = f"expected_vs_actual_{CASES[-1]}.txt"
    check(1, "shell: three attempts of one invocation carry ONE digest, sha256 of the SHA256SUMS written after the "
             "last per-case file (the listing names the last case's expected-versus-actual)",
          rc == 0 and len(set(hashes)) == 1 and hashes[0] == sums_hash and last_written in listed
          and all(f"expected_vs_actual_{n}.txt" in listed for n in CASES))
    totals = [load_json(sevd / f"bundle-{a}.json")["total_bytes"] for a in ids]
    check(2, "shell: the three bundle indexes carry the finished bundle's total_bytes",
          len(set(totals)) == 1 and totals[0] == bundle_total_bytes(sroot) and totals[0] > 0)

    # --- SQL seam ---------------------------------------------------------------------------
    qroot, qresult = sql_bundle(tmp)
    qevd = tmp / "evidence-sql"
    qdecl = declarations(tmp, "ctp-sql")
    qids = ["att-SELFTEST-SEAL-Q1", "att-SELFTEST-SEAL-Q2", "att-SELFTEST-SEAL-Q3"]
    rc, out = run(ctp_sql_records, ["build", "--bundle", str(qroot), "--result-dir", str(qresult),
                                    "--declarations", str(qdecl), "--manifest-id", "inv-SELFTEST-SEAL-Q",
                                    "--attempt-ids", ",".join(qids), "--evidence-dir", str(qevd)])
    if rc != 0:
        print(out)
    qsums_hash = sha256_prefixed(qroot / "SHA256SUMS")
    qlisted = sha256sums_entries(qroot / "SHA256SUMS")
    qhashes = [load_json(qevd / f"{a}.json")["bundle"]["hash"] for a in qids]
    manifest = load_json(qevd / "inv-SELFTEST-SEAL-Q.json")
    mhashes = [a["bundle_hash"] for c in manifest["cases"] for a in c["attempts"]]
    check(3, "sql: three attempt records and the manifest's three bundle_hash entries carry ONE digest, sha256 of a "
             "SHA256SUMS that names every per-case diff the tool wrote",
          rc == 0 and len(set(qhashes + mhashes)) == 1 and qhashes[0] == qsums_hash and len(mhashes) == 3
          and all(f"expected_vs_actual_{n}.diff" in qlisted for n in CASES))
    qtotals = [load_json(qevd / f"bundle-{a}.json")["total_bytes"] for a in qids]
    check(4, "sql: the three bundle indexes carry the finished bundle's total_bytes",
          len(set(qtotals)) == 1 and qtotals[0] == bundle_total_bytes(qroot))

    # --- the validator's cross-check (ticket 49 F2) ---------------------------------------------
    rc, out = validate(sevd, qevd)
    check(5, "validate_records accepts every record as written, cross-check included",
          rc == 0 and "0 failing" in out.splitlines()[-1])

    planted_dir = tmp / "evidence-planted"
    shutil.copytree(sevd, planted_dir)
    stale = load_json(planted_dir / f"{ids[1]}.json")
    stale["bundle"]["hash"] = "sha256:" + "8b27599105" + "0" * 54   # the shape of a still-growing digest
    write_record(stale, "attempt-record", planted_dir / f"{ids[1]}.json")
    stale_idx = load_json(planted_dir / f"bundle-{ids[0]}.json")
    stale_idx["total_bytes"] = totals[0] - 433
    write_record(stale_idx, "replay-bundle", planted_dir / f"bundle-{ids[0]}.json")
    rc, out = validate(planted_dir)
    check(6, "validate_records reports a record whose digest was planted back to a still-growing value, and an "
             "index whose total_bytes was (the ticket 17 defect)",
          rc == 1 and f"{ids[1]}.json" in out and "verifies against nothing" in out
          and f"bundle-{ids[0]}.json" in out and "total_bytes" in out and "2 failing" in out.splitlines()[-1])

    # --- the helper refuses a record sealed inside the loop ------------------------------------
    early = load_json(sevd / f"{ids[0]}.json")
    refused = False
    try:
        seal_bundle_records(sroot, [early], [], [], write_sums=False)
    except RecordError:
        refused = True
    pending = load_json(sevd / f"{ids[0]}.json")
    pending["bundle"]["hash"] = SEAL_PENDING_HASH
    sealed_hash, _ = seal_bundle_records(sroot, [pending], [], [], write_sums=False)
    check(7, "seal_bundle_records refuses a record whose digest was already taken, and seals a pending one to sha256(SHA256SUMS)",
          refused and pending["bundle"]["hash"] == sealed_hash == sums_hash)

    print(f"[selftest_bundle_sealing] {len(FAILS)} failing check(s); files under {tmp}")
    for f in FAILS:
        print("  " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
