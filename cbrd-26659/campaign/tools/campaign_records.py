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
  08): success-bulky expires seven days after creation, after which retention.py expire
  demotes the bundle to its core -- the fourteen items, SHA256SUMS and the index -- and
  never deletes it or nulls the attempt record's reference (ticket 45 item 5); failure
  bundles expire thirty days after triage, so their expiry is null with a hold reason until
  retention.py records the triage date; minimized reproducers never expire.
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
#: sha256 of the two engine libraries per build mode, for the build a NEW run must use.
#: Ticket 41 re-pinned the build under ticket 39 item 1: the same worktree and the same commit
#: (nothing about the engine source changed), configured with UNIT_TESTS, UNIT_TEST_OOS,
#: UNIT_TEST_SPAGE and UNIT_TEST_PAGE_BUFFER all OFF, so CUBRID_UNIT_TEST_ENABLED is not
#: compiled in and the engine exports no OOS test seams (11 before, 0 after).
LIBRARY_HASHES = {
    "release": {
        "libcubrid.so": "1bbbe44663c79d069181b0d812df95c7f7d793b7f16f2850ab4e8af899986b7c",
        "libcubridsa.so": "559a955ea2c46ae3de15efc572fd6a8dbaef7751e38b6c418656437d7a158179",
    },
    "debug": {
        "libcubrid.so": "30c520623ea5ab4661a1e1151e41922698e149f71f84a3dce669e24ffb34661f",
        "libcubridsa.so": "bc0de923e72f2c0464a69df20de9a58715d370382bc58274f85a2cf9e31a1931",
    },
}
BUILD_DIRS = {"release": "release_gcc_nounit", "debug": "debug_gcc_nounit"}
#: The shell wrappers gate a run before any Python here executes, so campaign_env.sh carries
#: the same four hashes and the same two build directories in campaign_expected_hash and
#: campaign_build_dir. A re-pin must change BOTH files; the baseline record's revision is the
#: authority both transcribe.
#: ticket 11, section 2: the superseded build. Four recorded invocations cite it, so it stays
#: recognised for replaying one of their bundles and is never used for a new run (ticket 41).
LEGACY_LIBRARY_HASHES = {
    "release": {
        "libcubrid.so": "a3256a7a40748752165e65a395b8aebcf8d85e00b87ee62e68bf75e1a5c85444",
        "libcubridsa.so": "8009c322633055df41af045fe560a86f1f8171648863d11f2e44d949e3cdd76e",
    },
    "debug": {
        "libcubrid.so": "27399fae11a5ef134ba303e5ac6d672748b224bdf593504a2d4fae533a357253",
        "libcubridsa.so": "9a3db918bc01738666bbb1ede762da973a714090c15e6709c78b7dc9c825ba69",
    },
}
LEGACY_BUILD_DIRS = {"release": "release_gcc", "debug": "debug_gcc"}
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
#: ticket 37 item 1: the runner jars and init.sh join the engine hashes in the identity list,
#: so a swapped CTP tree is caught the way a swapped library is. The expected hashes live in
#: ONE place, campaign_env.sh's campaign_check_ctp, which gates every wrapper run before any
#: Python here executes; the baseline record's revision 2 documents them. Python records the
#: tree that actually ran through ctp_fingerprint rather than re-asserting the expectation.
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


def recognised_build(build_mode: str, library_hashes: dict) -> str | None:
    """Which recorded build a pair of library hashes names.

    `'repin'` is the campaign's build, the only one a new run may use. `'ticket11'` is the
    superseded build carrying the unit-test seams, kept recognisable so a record written
    against it still resolves when its bundle is replayed (ticket 41). `None` is neither, and
    a record whose engine matches neither build cites an engine the campaign cannot identify.

    Takes the hashes rather than a prefix, with or without the `sha256:` the records carry, so
    it reads a recorded manifest as readily as an install on disk.
    """
    got = {lib: h.split(":")[-1] for lib, h in library_hashes.items()}
    if got == LIBRARY_HASHES.get(build_mode):
        return "repin"
    if got == LEGACY_LIBRARY_HASHES.get(build_mode):
        return "ticket11"
    return None


def verify_install(build_mode: str) -> dict:
    """Hash the two libraries of the pinned install and compare with the campaign's build.

    Returns the engine identity block for a manifest. Raises when the install is not the
    re-pinned build of ticket 41: a wrong library must stop a run before the launcher starts
    (ticket 11 section 2, identity-check pitfall). A prefix holding the superseded ticket 11
    build is named as such in the refusal, because that is the likely mistake.
    """
    prefix = install_prefix(build_mode)
    hashes = {}
    for lib, want in LIBRARY_HASHES[build_mode].items():
        got = sha256_file(prefix / "lib" / lib)
        if got != want:
            legacy = LEGACY_LIBRARY_HASHES[build_mode][lib]
            extra = (" -- that is the superseded ticket 11 build, which carries the unit-test seams and is kept "
                     "only for replaying the bundles that cite it (ticket 41)" if got == legacy else "")
            raise RecordError(f"{prefix}/lib/{lib} hashes {got}, not the campaign's {build_mode} build {want}{extra}")
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


def sha256sums_entries(path) -> dict:
    """The `<sha256>  <relative path>` lines of a SHA256SUMS file as {path: sha256 hex}."""
    out = {}
    for line in Path(path).read_text(errors="replace").splitlines():
        if len(line) > 66 and line[64:66] == "  ":
            out[line[66:]] = line[:64]
    return out


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


#: What a record carries for the bundle digest and size until the invocation is sealed. Schema-valid
#: in shape, so that an unsealed record is caught by seal_bundle_records, never by the validator.
SEAL_PENDING_HASH = "sha256:" + "0" * 64


def seal_bundle_records(bundle, attempt_records, bundle_indexes, cases_out, write_sums: bool) -> tuple:
    """Seal a shared bundle root ONCE and write the finished digest and size into every record.

    One bundle belongs to one invocation (ticket 44 F3, user decision 2026-09-16), so the digest
    and the `total_bytes` a record carries are the FINISHED bundle's, computed after the
    invocation's last file is written. Sealing as each record was built -- which both
    post-processors did until campaign ticket 49 -- wrote the digest of a directory that was
    still growing into every record but the last: 64 of ticket 19's 83 records, then 8 of
    ticket 17's 12 and 8 of ticket 47's 10, each verifying against nothing (ticket 44 F3;
    ticket 17's independent review, F2). The post-processors therefore build every record with
    SEAL_PENDING_HASH and a total of 0 and call this once, after the loop, before writing.
    Returns (bundle_hash, total_bytes).
    """
    bhash = bundle_hash(bundle, write_sums=write_sums)
    total = bundle_total_bytes(bundle)
    for att in attempt_records:
        if att["bundle"]["hash"] != SEAL_PENDING_HASH:
            raise RecordError(f"{att['attempt_id']}: bundle hash was sealed before the invocation's last file "
                              "was written; records are sealed once, after the loop (ticket 44 F3)")
        att["bundle"]["hash"] = bhash
    for bi in bundle_indexes:
        bi["total_bytes"] = total
    for case in cases_out:
        for entry in case.get("attempts", []):
            entry["bundle_hash"] = bhash
    return bhash, total


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
