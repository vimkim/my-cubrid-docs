#!/usr/bin/env python3
"""Record builders shared by the SQL and shell post-processors (ticket 15).

Identity-file parsing (the three layouts the campaign has produced), the declared case list,
the manifest and attempt-record skeletons, and the activation-checker reader. Rules and
their sources are documented on each function. Standard library only.
"""
from __future__ import annotations

import re
from pathlib import Path

from campaign_records import (
    retention_block,
    ENGINE_BASELINE_COMMIT, ENGINE_WORKTREE, LIBRARY_HASHES, PRODUCER_NAME, REPOSITORY_WORKTREES,
    REQUIREMENT_ID_RE, RESOURCE_CPUS, RESOURCE_MEMORY_GIB, TIER_CAPS, RecordError, catalogue_identity,
    context_identity, install_prefix, load_json, requirement,
)


# --- identity.txt parsing (ticket 13 layout, run_attempt.sh layout, ticket 15 layout) ----------
def parse_identity(path) -> dict:
    """Tolerant parser for the identity files the campaign has produced so far.

    Handles `key=value` lines; several `key=value` pairs on one line (ticket 13's
    `page_size=16384 build_mode=release ...`); `sha256 lib/libcubrid.so=<hex>` (run_attempt.sh);
    and bare `<hex>  <path>` sha256sum lines (ticket 13), keyed as `sha256:<basename>`.
    """
    out = {}
    if not Path(path).exists():
        return out
    hex64 = re.compile(r"^([0-9a-f]{64})\s+(\S.*)$")
    for raw in Path(path).read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = hex64.match(line)
        if m:
            out[f"sha256:{Path(m.group(2)).name}"] = m.group(1)
            continue
        if line.startswith("sha256 ") and "=" in line:
            k, v = line[7:].split("=", 1)
            out[f"sha256:{Path(k.strip()).name}"] = v.strip()
            continue
        if "=" not in line:
            continue
        if line.count("=") > 1 and " " in line and not line.startswith("cubrid_rel") \
                and all("=" in tok for tok in line.split()):
            for tok in line.split():
                k, v = tok.split("=", 1)
                out.setdefault(k, v)
            continue
        k, v = line.split("=", 1)
        out.setdefault(k.strip(), v.strip())
    return out


def engine_identity_from(ident: dict, build_mode: str, version_string: str | None) -> dict:
    """Engine block from a parsed identity file. The recorded library hashes must be ticket
    11's for the build mode, or the record is refused (ticket 11 section 2)."""
    hashes = {}
    for lib, want in LIBRARY_HASHES[build_mode].items():
        got = ident.get(f"sha256:{lib}")
        if got is None:
            raise RecordError(f"identity file carries no sha256 for {lib}")
        if got != want:
            raise RecordError(f"identity file says {lib} = {got}, ticket 11's {build_mode} build is {want}")
        hashes[lib] = "sha256:" + got
    prefix = ident.get("install_prefix") or ident.get("install") or str(install_prefix(build_mode))
    version = " ".join((version_string or ident.get("cubrid_rel") or "").split())
    if not version:
        raise RecordError("no cubrid_rel version string available for the engine identity")
    return {
        "baseline_commit": ident.get("engine_baseline_commit", ENGINE_BASELINE_COMMIT),
        "worktree": ident.get("engine_worktree", ENGINE_WORKTREE),
        "modified": False,
        "install_prefix": prefix,
        "version_string": version,
        "library_hashes": hashes,
    }


def testcase_identity_from(ident: dict, repository: str) -> dict:
    branch = ident.get("testcase_branch") or ident.get("branch")
    commit = ident.get("testcase_commit")
    base = ident.get("testcase_base_commit")
    if not (branch and commit and base):
        raise RecordError("identity file lacks testcase_branch/testcase_commit/testcase_base_commit")
    return {
        "repository": repository,
        "branch": branch,
        "commit": commit,
        "base_commit": base,
        "worktree": ident.get("testcase_worktree", REPOSITORY_WORKTREES[repository]),
    }


# --- declarations: the declared case list ------------------------------------------------------
def load_declarations(path) -> dict:
    """The declared case list the invocation must reproduce (spec, "Campaign manifest").

    A declarations file names the repository, the runner, the scenario (repository-relative)
    and, per case, its repository-relative path and the requirement IDs it cites; optionally a
    hand-derived expected assertion count with its derivation, an activation check, the
    resources the case owns, and whether it is single-session. The testcase repositories never
    depend on this file; it is the tooling's input.
    """
    decl = load_json(path)
    for key in ("repository", "runner", "scenario", "cases"):
        if key not in decl:
            raise RecordError(f"declarations {path}: missing {key!r}")
    if decl["runner"] not in ("ctp-sql", "ctp-shell"):
        raise RecordError(f"declarations {path}: runner must be ctp-sql or ctp-shell")
    if not decl["cases"]:
        raise RecordError(f"declarations {path}: no cases declared")
    for name, c in decl["cases"].items():
        reqs = c.get("requirements") or []
        if not reqs:
            raise RecordError(f"declarations {path}: case {name} cites no requirement")
        for rid in reqs:
            if not REQUIREMENT_ID_RE.match(rid):
                raise RecordError(f"declarations {path}: {name} cites malformed requirement id {rid!r}")
            requirement(rid)
        if "path" not in c:
            raise RecordError(f"declarations {path}: case {name} has no repository-relative path")
    return decl


def declared_case_list_text(decl: dict) -> str:
    return "".join(f"{decl['cases'][n]['path']}\n" for n in sorted(decl["cases"]))


# --- skeletons ------------------------------------------------------------------------------------
def manifest_skeleton(manifest_id, producer_version, started_at, ended_at, tier, cap_reached,
                      storage_gib, storage_root, engine, testcase, page_size, build_mode, run_mode,
                      services, runner, seed=None, instrumentation=None, inv_cap_override=None):
    inv_cap, case_cap = TIER_CAPS[tier]
    if inv_cap_override:
        inv_cap = int(inv_cap_override)  # a deliberately lowered cap (cap-enforcement control) is recorded as run
    return {
        "schema_version": 1,
        "manifest_id": manifest_id,
        "producer": {"kind": "wrapper", "name": PRODUCER_NAME, "version": producer_version},
        "invocation": {
            "started_at": started_at,
            "ended_at": ended_at,
            "tier": tier,
            "caps": {"invocation_seconds": inv_cap, "per_case_seconds": case_cap,
                     "invocation_cap_reached": bool(cap_reached)},
            "resources": {"cpus": RESOURCE_CPUS, "memory_gib": RESOURCE_MEMORY_GIB,
                          "storage_gib": storage_gib, "storage_root": str(storage_root)},
            "engine": engine,
            "testcase": testcase,
            "context": context_identity(),
            "catalogue": catalogue_identity(),
            "page_size": int(page_size),
            "build_mode": build_mode,
            "run_mode": run_mode,
            "services": services,
            "instrumentation": instrumentation,
            "seed": seed,
            "runner": runner,
        },
    }


def attempt_skeleton(attempt_id, kind, case, requirements, manifest_id, page_size, build_mode, run_mode,
                     started_at, ended_at, case_cap, deadline_reached, outcome, skip_reason, assertions,
                     expected_versus_actual, oos_evidence, resources_owned, cleanup, bundle_path,
                     bundle_hash, notes, seed=None, instrumentation_id=None):
    return {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "kind": kind,
        "parent_attempt": None,
        "finding_id": None,
        "case": case,
        "requirements": requirements,
        "manifest_id": manifest_id,
        "configuration": {"page_size": int(page_size), "build_mode": build_mode, "run_mode": run_mode,
                          "instrumentation_id": instrumentation_id, "seed": seed},
        "started_at": started_at,
        "ended_at": ended_at,
        "deadline": {"seconds": case_cap, "reached": bool(deadline_reached),
                     "evidence_captured_on_timeout": True if deadline_reached else None},
        "outcome": outcome,
        "skip_reason": skip_reason,
        "assertions": assertions,
        "expected_versus_actual": expected_versus_actual,
        "oos_evidence": oos_evidence,
        "barriers": [],
        "injections": [],
        "resources_owned": resources_owned,
        "cleanup": cleanup,
        "bundle": {"path": str(bundle_path), "hash": bundle_hash},
        "reproduction": {"fresh_fixture": True, "consecutive_reproductions_so_far": 0,
                         "failure_reproduced": False},
        "notes": notes,
    }


def evidence_block(status, channel=None, reference=None, applicability=None):
    return {"status": status, "channel": channel, "reference": reference, "applicability": applicability}


def read_activation(activation_dir, case_run_mode, decl_check):
    """Turn an activation checker's output directory into an oos_evidence block.

    The checker writes assertions.txt ending in a `RESULT:` line; only the literal
    `RESULT: activation proven` counts. Its identity.txt carries `run_mode=`; when that equals
    the case's run mode the evidence is `proven` (user decision O2, ticket 35; spec: activation
    evidence captured in this run, same fixture, same execution path), otherwise it is
    `reused`, which needs the declared applicability block, or `missing` when none was
    declared. A checker that did not run, or did not prove activation, yields `missing`:
    logical success with missing evidence is not OOS coverage.
    """
    channel = (decl_check or {}).get("channel", "show-heap-oos")
    if not activation_dir or not Path(activation_dir).exists():
        return evidence_block("missing"), ("no activation check ran for this case; the logical checks "
                                           "executed without OOS-path evidence (not OOS coverage)")
    assertions = Path(activation_dir) / "assertions.txt"
    if not assertions.exists():
        return evidence_block("missing"), f"the activation check wrote no assertions.txt under {activation_dir}"
    lines = assertions.read_text(errors="replace").splitlines()
    result = next((l for l in reversed(lines) if l.startswith("RESULT:")), "")
    proven = result.startswith("RESULT: activation proven")
    ident = parse_identity(Path(activation_dir) / "identity.txt")
    checker_mode = ident.get("run_mode", "unknown")
    if not proven:
        return evidence_block("missing", channel, None), (
            f"the activation checker did NOT prove activation ({result or 'no RESULT line'}); not OOS coverage")
    if checker_mode == case_run_mode:
        return evidence_block("proven", channel, None), (
            f"activation proven by the paired checker in the case's own run mode ({checker_mode}), "
            "same fixture, same install, same page size")
    app = (decl_check or {}).get("applicability")
    if not app:
        return evidence_block("missing", channel, None), (
            f"the activation checker ran {checker_mode} while the case ran {case_run_mode}; without a "
            "declared applicability block the evidence cannot be reused (ticket 12 section 3)")
    return evidence_block("reused", channel, None, app), (
        f"the activation checker ran {checker_mode} while the case ran {case_run_mode}: recorded as "
        "reused under the declared applicability block")


def retention_for(kind: str, outcome: str, created_at: str) -> dict:
    """Retention class per attempt kind.

    original/rerun/reproduction: PASS is success-bulky (seven days), anything else is a failure
    bundle held through triage (decision 08). checker-validation: the control is expected to
    FAIL -- that FAIL is the checker working, not a finding (schemas document section 11) -- so
    an expected FAIL is success-bulky, and a control that PASSED (the checker missed the planted
    defect) is the failure that needs triage. coexistence: as original.
    """
    if kind == "checker-validation":
        if outcome == "FAIL":
            return retention_block("PASS", created_at)
        blk = retention_block("FAIL", created_at)
        blk["hold_reason"] = ("checker-validation attempt did not FAIL: the checker missed the planted defect; "
                              "kept through triage plus thirty days")
        return blk
    return retention_block(outcome, created_at)
