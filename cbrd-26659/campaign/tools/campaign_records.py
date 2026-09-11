#!/usr/bin/env python3
"""Shared helpers for the CBRD-26659 campaign record tooling (ticket 15).

Everything the SQL and shell post-processors, the matrix aggregator, the retention tool
and the validator share lives here: the campaign constants (ticket 11 identities, the
configuration domain, the tier caps, the campaign ports), hashing, timestamps, the
catalogue, the schema-validated writer, and the bundle index builder.

Rules encoded here and where they come from:

* Every record is validated against ticket 12's schema (schemas/*.schema.json) with
  tools/minischema.py BEFORE it is written; an invalid record is never written
  (ticket 15 criteria; ticket 12 section 3 "rules tooling must add").
* The configuration domain is 4096/8192/16384 x release/debug x standalone/client-server,
  12 combinations; `configurations_not_run` enumerates every combination the CTP case did
  not run in this invocation (ticket 35 F4, adopted by ticket 34).
* Bundle hash convention (ticket 15 decision, recorded in the ticket 15 record): the
  bundle's SHA256SUMS lists every regular file below the bundle root except SHA256SUMS
  itself, as `<sha256>  <relative path>` in bytewise (LC_ALL=C) path order; the bundle
  hash is `sha256:` + sha256 of that SHA256SUMS file. Ticket 13 used the same shape with
  a locale-ordered listing; ticket 14 used `find | sort | xargs sha256sum | sha256sum`,
  which hashes absolute paths and therefore changes when a bundle is moved. Both legacy
  conventions can be recomputed for comparison (bundle_hash_legacy_t14).
* Retention classes (spec "Execution tiers, configurations and budgets"; decision ticket
  08): success-bulky expires seven days after creation; failure bundles expire thirty
  days after triage, so their expiry is null with a hold reason until retention.py
  records the triage date; minimized reproducers never expire.
* Storage: everything lives under /home/vimkim/.cub/campaign/cbrd-26659 (spec: under
  /home, never the temporary filesystem); the aggregate limit is 100 GiB.

Standard library only.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
CAMPAIGN_DIR = TOOLS_DIR.parent
DOCS_REPO = CAMPAIGN_DIR.parent.parent
SCHEMAS_DIR = CAMPAIGN_DIR / "schemas"
CATALOGUE_PATH = CAMPAIGN_DIR / "catalogue" / "requirements.json"
CATALOGUE_REL = "cbrd-26659/campaign/catalogue/requirements.json"

sys.path.insert(0, str(TOOLS_DIR))
from minischema import validate as _schema_validate  # noqa: E402

# --- campaign constants (ticket 11 section 2, decision ticket 08, ticket 14 section 2) ------
ENGINE_BASELINE_COMMIT = "f4299ac0cd777a2a964c1f197ae5ebf9841a4936"
ENGINE_WORKTREE = "/home/vimkim/gh/cb/oos-baseline-f4299ac0c"
INSTALL_ROOT = Path("/home/vimkim/.cub/install/oos-baseline-f4299ac0c")
#: ticket 11, section 2: sha256 of the two engine libraries per build mode.
LIBRARY_HASHES = {
    "release": {
        "libcubrid.so": "a3256a7a40748752165e65a395b8aebcf8d85e00b87ee62e68bf75e1a5c85444",
        "libcubridsa.so": "8009c322633055df41af045fe560a86f1f8171648863d11f2e44d949e3cdd76e",
    },
    "debug": {
        "libcubrid.so": "27399fae11a5ef134ba303e5ac6d672748b224bdf593504a2d4fae533a357253",
        "libcubridsa.so": "9a3db918bc01738666bbb1ede762da973a714090c15e6709c78b7dc9c825ba69",
    },
}
BUILD_DIRS = {"release": "release_gcc", "debug": "debug_gcc"}
STORAGE_ROOT = Path("/home/vimkim/.cub/campaign/cbrd-26659")
STORAGE_LIMIT_BYTES = 100 * 1024 ** 3
CAMPAIGN_PORTS = [26659, 33120, 33121, 33122]
RESOURCE_CPUS = 8
RESOURCE_MEMORY_GIB = 16
TIER_CAPS = {"fast": (900, 120), "scheduled": (7200, 900), "extended": (28800, 3600)}
PAGE_SIZES = (4096, 8192, 16384)
BUILD_MODES = ("release", "debug")
RUN_MODES = ("standalone", "client-server")
CTP_HOME = Path("/home/vimkim/CTP")
CTP_FINGERPRINT_FILES = {
    "ctp-sql": CTP_HOME / "sql" / "lib" / "cubridqa-cqt.jar",
    "ctp-shell": CTP_HOME / "shell" / "lib" / "cubridqa-shell.jar",
}
REPOSITORY_WORKTREES = {
    "testcases": "/home/vimkim/gh/tc/cubrid-testcases-cbrd-26659",
    "testcases-private-ex": "/home/vimkim/gh/tc/cubrid-testcases-private-ex-cbrd-26659",
}
RETENTION_SUCCESS_DAYS = 7
RETENTION_FAILURE_DAYS_AFTER_TRIAGE = 30
REQUIREMENT_ID_RE = re.compile(r"^OOS-(REP|SQL|RD|SCH|CL|DUR|OPS|RES)-[0-9]{2}$")
OUTCOMES = ("PASS", "FAIL", "SKIP", "UNSUPPORTED", "BLOCKED")

TOOL_VERSION = "ticket15-1.0"
PRODUCER_NAME = "CBRD-26659 campaign tooling (ticket 15)"


class RecordError(Exception):
    """A record could not be produced or would be invalid; nothing was written."""


# --- small utilities ----------------------------------------------------------------------
def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_prefixed(path) -> str:
    return "sha256:" + sha256_file(path)


def now_iso() -> str:
    """Local time with numeric offset, second precision, as the schemas' timestamp pattern."""
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def iso_from_epoch(epoch: float) -> str:
    return _dt.datetime.fromtimestamp(epoch).astimezone().replace(microsecond=0).isoformat()


def parse_iso(ts: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(ts)


def today_plus(days: int, base: str | None = None) -> str:
    base_dt = parse_iso(base) if base else _dt.datetime.now().astimezone()
    return (base_dt + _dt.timedelta(days=days)).date().isoformat()


def read_kv(path) -> dict:
    """Parse `key=value` lines (identity.txt, summary.txt, timing.txt, test_status.data)."""
    out = {}
    if not Path(path).exists():
        return out
    for line in Path(path).read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out.setdefault(k.strip(), v.strip())
    return out


def run(cmd, cwd=None, check=True) -> str:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RecordError(f"command failed ({res.returncode}): {' '.join(map(str, cmd))}\n{res.stderr}")
    return res.stdout.strip()


def git(worktree, *args) -> str:
    return run(["git", "-C", str(worktree), *args])


def repo_relative(worktree, path) -> str:
    p = Path(path).resolve()
    w = Path(worktree).resolve()
    try:
        return str(p.relative_to(w))
    except ValueError as exc:
        raise RecordError(f"{path} is not inside the worktree {worktree}") from exc


def docs_relative(path) -> str:
    """Path of a docs-repository file as the hand-written records cite it (repo-relative)."""
    p = Path(path).resolve()
    try:
        return str(p.relative_to(DOCS_REPO.resolve()))
    except ValueError:
        return str(p)


# --- catalogue --------------------------------------------------------------------------------
_catalogue_cache = None


def load_catalogue() -> dict:
    global _catalogue_cache
    if _catalogue_cache is None:
        _catalogue_cache = json.loads(CATALOGUE_PATH.read_text())
    return _catalogue_cache


def catalogue_identity() -> dict:
    return {"path": CATALOGUE_REL, "hash": sha256_prefixed(CATALOGUE_PATH)}


def context_identity() -> dict:
    pin = load_catalogue()["pin"]
    return {
        "revision": pin["context_revision"],
        "content_hash": pin["content_hashes"]["OOS-CONTEXT.md"],
        "snapshot": pin["snapshot"],
    }


def requirement(rid: str) -> dict:
    for r in load_catalogue()["requirements"]:
        if r["id"] == rid:
            return r
    raise RecordError(f"requirement {rid!r} is not in the catalogue")


def assertable_requirement_ids() -> list:
    """Requirements whose absence from executed coverage is a Delivery gap: assertable and
    observation-only ones. BLOCKED and UNSUPPORTED requirements are gaps of another kind and
    are deliberately not listed (inv-T13-0002 note)."""
    return [r["id"] for r in load_catalogue()["requirements"]
            if r["status"] in ("assertable", "observation-only")]


# --- engine identity --------------------------------------------------------------------------
def install_prefix(build_mode: str) -> Path:
    return INSTALL_ROOT / BUILD_DIRS[build_mode]


def verify_install(build_mode: str) -> dict:
    """Hash the two libraries of the pinned install and compare with ticket 11.

    Returns the engine identity block for a manifest. Raises when the install is not ticket
    11's build: a wrong library must stop a run before the launcher starts (ticket 11
    section 2, identity-check pitfall).
    """
    prefix = install_prefix(build_mode)
    hashes = {}
    for lib, want in LIBRARY_HASHES[build_mode].items():
        got = sha256_file(prefix / "lib" / lib)
        if got != want:
            raise RecordError(f"{prefix}/lib/{lib} hashes {got}, not ticket 11's {build_mode} build {want}")
        hashes[lib] = "sha256:" + got
    env = dict(os.environ)
    env["CUBRID"] = str(prefix)
    env["PATH"] = f"{prefix}/bin:" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = f"{prefix}/lib:{prefix}/cci/lib"
    res = subprocess.run([str(prefix / "bin" / "cubrid_rel")], env=env, capture_output=True, text=True)
    version = " ".join(res.stdout.split())
    if "f4299ac" not in version:
        raise RecordError(f"cubrid_rel of {prefix} reports {version!r}, not the pinned build")
    return {
        "baseline_commit": ENGINE_BASELINE_COMMIT,
        "worktree": ENGINE_WORKTREE,
        "modified": False,
        "install_prefix": str(prefix),
        "version_string": version,
        "library_hashes": hashes,
    }


def testcase_identity(repository: str, worktree: str | None = None) -> dict:
    wt = worktree or REPOSITORY_WORKTREES[repository]
    return {
        "repository": repository,
        "branch": git(wt, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit": git(wt, "rev-parse", "HEAD"),
        "base_commit": git(wt, "merge-base", "HEAD", "origin/develop"),
        "worktree": str(wt),
    }


def ctp_fingerprint(runner_kind: str, ctp_home=None) -> str:
    """sha256 of the runner's jar in the CTP tree that ran (identity.txt's ctp_home), not of a
    tree assumed from a constant: two CTP checkouts with different jars exist on this host."""
    home = Path(ctp_home) if ctp_home else CTP_HOME
    rel = CTP_FINGERPRINT_FILES[runner_kind].relative_to(CTP_HOME)
    return sha256_prefixed(home / rel)


# --- configuration domain -------------------------------------------------------------------
def configuration_label(page_size: int, build_mode: str, run_mode: str) -> str:
    return f"{page_size}/{build_mode}/{run_mode}"


def configurations_not_run(ran: set) -> list:
    """Every combination of the 12-combination domain not in `ran` (ticket 35 F4 rule)."""
    out = []
    for p in PAGE_SIZES:
        for b in BUILD_MODES:
            for r in RUN_MODES:
                label = configuration_label(p, b, r)
                if label not in ran:
                    out.append(label)
    return out


def row_configuration_suffix(page_size: int, build_mode: str, run_mode: str, instrumentation_id=None) -> str:
    rm = {"client-server": "cs", "standalone": "sa"}[run_mode]
    s = f"{page_size}-{build_mode}-{rm}"
    if instrumentation_id:
        s += f"-{instrumentation_id}"
    return s


# --- schema-validated writing -------------------------------------------------------------------
_schema_cache = {}


def load_schema(name: str) -> dict:
    if name not in _schema_cache:
        _schema_cache[name] = json.loads((SCHEMAS_DIR / f"{name}.schema.json").read_text())
    return _schema_cache[name]


def validate_record(record: dict, schema_name: str) -> list:
    return list(_schema_validate(record, load_schema(schema_name)))


def write_record(record: dict, schema_name: str, path) -> str:
    """Validate, then write. Never writes an invalid record. Returns the file's sha256."""
    errors = validate_record(record, schema_name)
    if errors:
        raise RecordError(f"refusing to write {path}: {len(errors)} schema error(s) against {schema_name}:\n  "
                          + "\n  ".join(errors))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    path.write_text(data)
    return sha256_bytes(data.encode())


def load_json(path):
    return json.loads(Path(path).read_text())


# --- bundle hashing and indexing ------------------------------------------------------------
def bundle_files(root) -> list:
    """Regular files below root, bundle-relative, bytewise sorted, SHA256SUMS excluded."""
    root = Path(root)
    files = []
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink():
            rel = str(p.relative_to(root))
            if rel == "SHA256SUMS":
                continue
            files.append(rel)
    return sorted(files)


def sha256sums_text(root) -> str:
    root = Path(root)
    return "".join(f"{sha256_file(root / rel)}  {rel}\n" for rel in bundle_files(root))


def bundle_hash(root, write_sums: bool) -> str:
    """The ticket 15 convention. With write_sums the SHA256SUMS file is (re)written; without
    it the hash is computed in memory so a sealed bundle is never modified."""
    text = sha256sums_text(root)
    if write_sums:
        (Path(root) / "SHA256SUMS").write_text(text)
    return "sha256:" + sha256_bytes(text.encode())


def bundle_hash_legacy_t14(root) -> str:
    """Ticket 14's convention: find <root> -type f | sort | xargs sha256sum | sha256sum."""
    root = str(Path(root))
    files = sorted(str(p) for p in Path(root).rglob("*") if p.is_file() and not p.is_symlink())
    text = "".join(f"{sha256_file(f)}  {f}\n" for f in files)
    return "sha256:" + sha256_bytes(text.encode())


def bundle_total_bytes(root) -> int:
    """Sum of regular file sizes (not `du`, whose directory blocks depend on the filesystem)."""
    return sum((Path(root) / rel).stat().st_size for rel in bundle_files(Path(root))) + (
        (Path(root) / "SHA256SUMS").stat().st_size if (Path(root) / "SHA256SUMS").exists() else 0)


def item(root, rel_path, note, state=None):
    """Bundle-index item: present when the file exists, else missing with the note."""
    root = Path(root)
    if rel_path and (root / rel_path).exists():
        return {"state": "present", "path": rel_path, "hash": sha256_prefixed(root / rel_path), "note": note}
    return {"state": state or "missing", "path": None, "hash": None, "note": note}


def not_applicable(note):
    return {"state": "not-applicable", "path": None, "hash": None, "note": note}


def retention_block(outcome: str, created_at: str, minimized: bool = False) -> dict:
    if minimized:
        return {"class": "minimized-reproducer", "expires_on": None,
                "hold_reason": "minimized reproducers are kept (decision ticket 08)"}
    if outcome == "PASS":
        return {"class": "success-bulky", "expires_on": today_plus(RETENTION_SUCCESS_DAYS, created_at),
                "hold_reason": None}
    return {"class": "failure", "expires_on": None,
            "hold_reason": f"non-PASS outcome {outcome}: kept through triage; retention.py triage sets "
                           f"expires_on to the triage date plus {RETENTION_FAILURE_DAYS_AFTER_TRIAGE} days "
                           "(decision ticket 08); never deleted while an unresolved finding needs it"}


def storage_used_bytes(root=STORAGE_ROOT) -> int:
    total = 0
    for p in Path(root).rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def gib(n_bytes: int) -> float:
    return max(0.01, round(n_bytes / 1024 ** 3, 2))
