#!/usr/bin/env python3
"""Code-level check of the Sidecar POC: store read, write order, lock fallback and store cursor.

Run it from the Sidecar worktree, or pass --repo.  The script reads from the
source the shape that each model assumes (the order of the store writes and
the hot write, the plan's applied state, the store read's home recheck, the
retry bound, the lock fallback, the store cursor's release sites), stops with
OUT OF SYNC when the code no longer has a shape the models describe, runs TLC
once per property, and compares each failure with known_findings.json.  A
property that fails as a known finding runs again with that finding's cause
removed, so a known finding cannot hide another failure.  See README.md and
the cubrid-verify-sidecar-code skill.

Exit status:
  0  every property passes, or fails only as recorded known findings,
     and the covered code is unchanged since the sync commit
  1  a property fails in a way that is not a recorded known finding,
     or fails under a hypothetical --set shape
  2  the code no longer has the shape the models assume, or a tool error
  3  the results are as in 0, but covered code changed since the sync commit
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
README = os.path.join(HERE, "README.md")
KNOWN_FINDINGS = os.path.join(HERE, "known_findings.json")

TLA2TOOLS_VERSION = "1.7.4"
TLA2TOOLS_SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
TLA2TOOLS_URL = "https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar"

YN = ("yes", "no")
SHAPE_DOMAINS = {
    # store read (SidecarStoreRead)
    "home_recheck": ("on_miss", "always", "no"),
    "fwd_type_check": YN,
    "fwd_slot_reuse": YN,
    "vacuum_fwd_held": YN,
    "stamp_relocates": YN,
    "reread_bound": ("none",) + tuple(str(n) for n in range(1, 11)),
    "model.stamp_cycles": ("reread_bound", "below_reread_bound"),
    # row write and fetch (SidecarRowWrite)
    "write_order": ("store_then_hot", "hot_then_store"),
    "plan_once": YN,
    "row_lock": YN,
    "retry_bound": tuple(str(n) for n in range(0, 6)),
    "on_absent": ("retry", "doesnt_exist"),
    "delid_test": YN,
    "fallback": YN,
    "fallback_lock": ("s_lock_around_read", "none"),
    # store cursor (SidecarCodeLatch)
    "rel_before_call": YN,
    "rel_before_hot_fix": YN,
    "rel_before_store_fix": YN,
    "fix_guard": YN,
    "apply_no_page": YN,
}
MAX_ROUNDS = 4


class ShapeError(Exception):
    """The source no longer has a shape that a model describes."""


# ---------------------------------------------------------------------------
# Source access


def repo_root(path):
    out = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    root = out.stdout.strip() if out.returncode == 0 else os.path.abspath(path)
    if not os.path.isfile(os.path.join(root, "src", "storage", "sidecar.cpp")):
        raise ShapeError("%s has no src/storage/sidecar.cpp: run from the Sidecar worktree or pass --repo" % root)
    return root


class Source:
    """Reads files from the work tree, or from a commit when rev is set."""

    def __init__(self, root, rev=None):
        self.root, self.rev, self.cache = root, rev, {}

    def read(self, path):
        if path not in self.cache:
            if self.rev is None:
                with open(os.path.join(self.root, path), encoding="utf-8", errors="replace") as f:
                    text = f.read()
            else:
                out = subprocess.run(["git", "-C", self.root, "show", "%s:%s" % (self.rev, path)],
                                     capture_output=True, text=True, errors="replace")
                if out.returncode != 0:
                    raise ShapeError("cannot read %s at %s: %s" % (path, self.rev, out.stderr.strip()))
                text = out.stdout
            self.cache[path] = (text, strip_comments_and_strings(text))
        return self.cache[path]


def strip_comments_and_strings(text):
    """Blank comments and the contents of string and char literals, keeping offsets."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out[i:j] = " " * (j - i)
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif text[i] in "\"'":
            c, j = text[i], i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            for k in range(i + 1, min(j, n)):
                out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def match_brace(code, open_idx):
    depth = 0
    for i in range(open_idx, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ShapeError("unbalanced braces")


class Fn:
    """The body of one function definition: code without comments, and where it starts."""

    def __init__(self, src, path, name):
        text, code = src.read(path)
        self.path, self.name, self.text = path, name, text
        for m in re.finditer(r"^[^\n;{}#]*?\b%s\s*\(" % re.escape(name), code, re.M):
            brace = re.compile(r"\n\{").search(code, m.end())
            semi = code.find(";", m.end())
            if brace and (semi < 0 or brace.start() < semi):
                start = brace.start() + 1
                self.start, self.end = start, match_brace(code, start)
                self.body = code[start:self.end]
                return
        raise ShapeError("%s: no definition of %s" % (path, name))

    def find(self, pattern, start=0):
        m = re.compile(pattern, re.S).search(self.body, start)
        return m

    def at(self, m_or_offset):
        off = m_or_offset.start() if hasattr(m_or_offset, "start") else m_or_offset
        return "%s:%d" % (self.path, self.text.count("\n", 0, self.start + off) + 1)

    def require(self, pattern, what, start=0):
        m = self.find(pattern, start)
        if not m:
            raise ShapeError("%s no longer %s" % (self.name, what))
        return m


def define(src, path, name):
    text, code = src.read(path)
    m = re.search(r"#define\s+%s\s+(\d+)" % name, code)
    if not m:
        raise ShapeError("%s: no #define %s" % (path, name))
    return m.group(1), "%s:%d" % (path, text.count("\n", 0, m.start()) + 1)


# ---------------------------------------------------------------------------
# Shape extraction.  Each value comes with the source line that decides it.

SC = "src/storage/sidecar.cpp"
HF = "src/storage/heap_file.c"


def extract_shape(src):
    shape = {}

    def put(key, value, why):
        shape[key] = (value, why)

    # -- the store read
    rd = Fn(src, SC, "sidecar_read_store_record_at")
    first = rd.require(r"sidecar_fix_store_page\s*\(\s*thread_p\s*,\s*oid\s*,", "fixes the home page")
    fwd_fix = rd.require(r"sidecar_fix_store_page\s*\(\s*thread_p\s*,\s*&forward\s*,", "fixes the forward page")
    again = rd.find(r"sidecar_fix_store_page\s*\(\s*thread_p\s*,\s*oid\s*,", fwd_fix.end())
    same = rd.find(r"OID_EQ\s*\(\s*\(OID\s*\*\)\s*peeked\.data\s*,\s*&forward\s*\)", fwd_fix.end())
    miss = rd.find(r"missed\s*=\s*forward\s*;", fwd_fix.end())
    miss_test = rd.find(r"OID_EQ\s*\(\s*&forward\s*,\s*&missed\s*\)[^;]*\)\s*\{[^}]*return\s+SIDECAR_READ_ABSENT",
                        first.end())
    copy_ret = rd.find(r"if\s*\(\s*read\s*\)\s*\{\s*return\s+SIDECAR_READ_PRESENT", fwd_fix.end())
    if again and same:
        put("home_recheck", "always", "home page fixed again at %s" % rd.at(again))
    elif miss and miss_test and copy_ret:
        put("home_recheck", "on_miss", "REC_NEWHOME copy returned at %s; missed forward slot kept at %s, absent when "
            "the home forwards to it again at %s" % (rd.at(copy_ret), rd.at(miss), rd.at(miss_test)))
    else:
        put("home_recheck", "no", "no second home fix after the forward fix")
    ty = rd.find(r"spage_get_record_type\s*\(\s*page\s*,\s*forward\.slotid\s*\)\s*==\s*REC_NEWHOME", fwd_fix.end())
    put("fwd_type_check", "yes" if ty else "no", "REC_NEWHOME test at %s" % rd.at(ty) if ty else "no REC_NEWHOME test")
    try:
        val, where = define(src, SC, "SIDECAR_REREAD_BOUND")
    except ShapeError:
        loop = rd.require(r"while\s*\(\s*true\s*\)", "loops over rounds")
        val, where = "none", "no SIDECAR_REREAD_BOUND; unbounded loop at %s" % rd.at(loop)
    put("reread_bound", val, where)
    rd.require(r"type\s*!=\s*REC_HOME\s*&&\s*type\s*!=\s*REC_RELOCATION", "reads only REC_HOME, REC_RELOCATION and REC_BIGONE")

    sdr = Fn(src, "src/storage/slotted_page.c", "spage_delete_for_recovery")
    reuse = sdr.find(r"slot_p->record_type\s*=\s*REC_DELETED_WILL_REUSE")
    rui = Fn(src, HF, "heap_rv_undo_insert")
    store_keep = rui.find(r"if\s*\(\s*sidecar_store\s*\)\s*\{[^}]*\bspage_delete\s*\(")
    if store_keep and rui.find(r"sidecar_store\s*=\s*heap_page_is_sidecar_store\s*\("):
        reuse = None
    vac = Fn(src, "src/query/vacuum.c", "vacuum_heap_record")
    vfwd = vac.find(r"spage_vacuum_slot\s*\(\s*thread_p\s*,\s*helper->forward_page\s*,[^;]*,\s*true\s*\)")
    vkeep = vac.find(r"forward_reusable\s*=\s*!\s*heap_page_is_sidecar_store\s*\(\s*thread_p\s*,\s*helper->forward_page")
    if not vfwd and not vkeep:
        vfwd = vac.find(r"spage_vacuum_slot\s*\(\s*thread_p\s*,\s*helper->forward_page")
    put("fwd_slot_reuse", "yes" if reuse or vfwd else "no",
        "; ".join(x for x in ["undo of a newhome insert: REC_DELETED_WILL_REUSE at %s" % sdr.at(reuse) if reuse else "",
                              "vacuum of a forward slot with reuse at %s" % vac.at(vfwd) if vfwd else ""] if x)
        or "a freed store slot stays REC_MARKDELETED: heap_rv_undo_insert at %s, vacuum_heap_record at %s"
        % (rui.at(store_keep), vac.at(vkeep)) if store_keep and vkeep else "no forward slot is freed for reuse")
    dont = vac.find(r"pgbuf_set_dirty\s*\(\s*thread_p\s*,\s*helper->forward_page\s*,\s*DONT_FREE\s*\)")
    commit = vac.find(r"log_sysop_commit\s*\(", dont.end()) if dont else None
    unfix = vac.find(r"pgbuf_unfix_and_init\s*\(\s*thread_p\s*,\s*helper->forward_page\s*\)", commit.end()) if commit else None
    put("vacuum_fwd_held", "yes" if unfix else "no",
        "forward page unfixed after log_sysop_commit at %s" % vac.at(unfix) if unfix
        else "forward page released before the sysop ends")

    dh = Fn(src, HF, "heap_delete_home")
    nh = dh.find(r"built_recdes\.type\s*=\s*REC_NEWHOME")
    ins = dh.find(r"heap_insert_newhome\s*\(", nh.end()) if nh else None
    put("stamp_relocates", "yes" if ins else "no",
        "heap_delete_home relocates a stamped record at %s" % dh.at(ins) if ins else "a stamp never relocates")

    # -- the write order and the release-and-relocate step
    ap = Fn(src, SC, "sidecar_apply_plan_body")
    iv = ap.require(r"sidecar_insert_values\s*\(", "inserts fresh values")
    sv = ap.require(r"sidecar_stamp_values\s*\(", "stamps dropped values")
    applied = ap.require(r"plan->state\s*=\s*SIDECAR_PLAN_APPLIED", "marks the plan applied", sv.end())
    held = ap.require(r"pgbuf_has_perm_pages_fixed\s*\(\s*thread_p\s*\)", "tests for a held page")
    ap.require(r"return\s+ER_SIDECAR_NOT_SUPPORTED", "refuses a store write with a page held", held.end())
    if iv.start() > sv.start():
        raise ShapeError("sidecar_apply_plan_body stamps before it inserts; SidecarRowWrite runs insert, then stamp")
    order = "store_then_hot"
    why = ["insert %s, stamp %s" % (ap.at(iv), ap.at(sv))]
    release_ok = True
    for fname, hot in (("heap_update_logical", r"heap_update_(home|relocation|bigone)\s*\("),
                       ("heap_delete_logical", r"heap_delete_(home|relocation|bigone)\s*\(")):
        fn = Fn(src, HF, fname)
        call = fn.require(r"rc\s*=\s*sidecar_apply_plan\s*\(", "calls sidecar_apply_plan")
        reloc = fn.require(r"goto\s+relocate\s*;", "goes back to relocate", call.end())
        label = fn.require(r"\brelocate\s*:", "has the relocate label")
        if label.start() > call.start():
            raise ShapeError("%s: the relocate label follows sidecar_apply_plan" % fname)
        unf = fn.find(r"heap_unfix_watchers\s*\(\s*thread_p\s*,\s*context\s*\)\s*;\s*$", 0)
        prior = list(re.finditer(r"heap_unfix_watchers\s*\(\s*thread_p\s*,\s*context\s*\)\s*;", fn.body[:call.start()]))
        if not prior or fn.body[prior[-1].end():call.start()].strip():
            release_ok = False
        hw = fn.find(hot, reloc.end())
        if not hw:
            raise ShapeError("%s: no hot write after goto relocate" % fname)
        if hw.start() < call.start():
            order = "hot_then_store"
        why.append("%s: apply %s, goto relocate %s, hot write %s" % (fname, fn.at(call), fn.at(reloc), fn.at(hw)))
    il = Fn(src, HF, "heap_insert_logical")
    icall = il.require(r"rc\s*=\s*sidecar_apply_plan\s*\(", "calls sidecar_apply_plan")
    iloc = il.require(r"heap_get_insert_location_with_lock\s*\(", "gets the insert location")
    if iloc.start() < icall.start():
        order = "hot_then_store"
    why.append("heap_insert_logical: apply %s, location %s" % (il.at(icall), il.at(iloc)))
    put("write_order", order, "; ".join(why))
    put("apply_no_page", "yes" if release_ok else "no",
        "heap_unfix_watchers just before sidecar_apply_plan; sidecar_apply_plan_body refuses a held page at %s" % ap.at(held)
        if release_ok else "a hot page may be held into sidecar_apply_plan")

    once = []
    for fname in ("sidecar_plan_update_body", "sidecar_plan_delete_body"):
        fn = Fn(src, SC, fname)
        m = fn.find(r"plan->state\s*==\s*SIDECAR_PLAN_APPLIED\s*\)\s*\{\s*[^}]*return\s+NO_ERROR")
        once.append((fname, fn.at(m) if m else None))
    put("plan_once", "yes" if all(w for _, w in once) else "no",
        "; ".join("%s returns on an applied plan at %s" % (f, w) if w else "%s replans an applied plan" % f
                  for f, w in once) + "; applied at %s" % ap.at(applied))
    put("row_lock", "yes", "assumed: the locator takes the row's X lock before heap_update_logical and heap_delete_logical")

    # -- the committed fetch, its retry and the lock fallback
    val, where = define(src, SC, "SIDECAR_RETRY_BOUND")
    put("retry_bound", val, where)
    oa = Fn(src, SC, "sidecar_on_absent")
    dt = oa.find(r"MVCC_IS_HEADER_DELID_VALID\s*\(\s*&header\s*\)\s*&&\s*!\s*log_Gl\.mvcc_table\.is_active")
    put("delid_test", "yes" if dt else "no", "committed DELID test at %s" % oa.at(dt) if dt else "no committed DELID test")
    rt = oa.find(r"attempt\s*<\s*SIDECAR_RETRY_BOUND[^;]*;[^}]*return\s+S_SIDECAR_RETRY")
    put("on_absent", "retry" if rt else "doesnt_exist", "S_SIDECAR_RETRY at %s" % oa.at(rt) if rt else "no retry")
    ln = oa.find(r"return\s+S_SIDECAR_LOCK_NEEDED")
    lr = Fn(src, "src/transaction/locator_sr.c", "locator_lock_and_return_object")
    lf = lr.find(r"scan\s*==\s*S_SIDECAR_LOCK_NEEDED[^;]*\)\s*\{?\s*[^;]*sidecar_fetch_locked\s*\(")
    put("fallback", "yes" if ln and lf else "no",
        "S_SIDECAR_LOCK_NEEDED at %s, sidecar_fetch_locked at %s" % (oa.at(ln), lr.at(lf)) if ln and lf
        else "no lock fallback after the bound")
    fl = Fn(src, SC, "sidecar_fetch_locked")
    lk = fl.find(r"lock_object\s*\([^;]*S_LOCK[^;]*\)")
    lv = fl.find(r"heap_get_last_version\s*\(", lk.end() if lk else 0)
    ul = fl.find(r"lock_unlock_object\s*\(", lv.end()) if lv else None
    put("fallback_lock", "s_lock_around_read" if lk and lv and ul else "none",
        "S lock %s, heap_get_last_version %s, unlock %s" % (fl.at(lk), fl.at(lv), fl.at(ul)) if lk and lv and ul
        else "heap_get_last_version without the S lock around it")

    # -- the store cursor's release sites
    _, code = src.read("src/sp/pl_executor.cpp")
    text, _ = src.read("src/sp/pl_executor.cpp")
    m = re.search(r"executor::execute\s*\(\s*DB_VALUE\s*&\s*value\s*\)\s*\{", code)
    rel_call = m and re.match(r"[^{}]*sidecar_cursor_release\s*\(", code[m.end():])
    put("rel_before_call", "yes" if rel_call else "no",
        "cubpl::executor::execute releases at src/sp/pl_executor.cpp:%d" % (text.count("\n", 0, m.end() + rel_call.end()) + 1)
        if rel_call else "a routine call keeps the cursor's page")
    sites = []
    for path, fname in ((HF, "heap_scan_pb_latch_and_fetch"), (HF, "heap_prepare_object_page"),
                        ("src/query/scan_manager.c", "scan_batch_next_page")):
        fn = Fn(src, path, fname)
        h = fn.find(r"sidecar_cursor_before_hot_fix\s*\(")
        sites.append((fname, fn.at(h) if h else None))
    put("rel_before_hot_fix", "yes" if all(w for _, w in sites) else "no",
        "; ".join("%s %s" % (f, w or "MISSING") for f, w in sites))
    cr = Fn(src, SC, "sidecar_cursor_read_value")
    cu = cr.find(r"sidecar_cursor_unfix\s*\(\s*thread_p\s*\)\s*;")
    cf = cr.find(r"sidecar_fix_store_page\s*\(")
    put("rel_before_store_fix", "yes" if cu and cf and cu.start() < cf.start() else "no",
        "sidecar_cursor_unfix %s before sidecar_fix_store_page %s" % (cr.at(cu), cr.at(cf)) if cu and cf
        else "the next store page is fixed with the kept one held")
    pf = Fn(src, "src/storage/page_buffer.c", "pgbuf_fix_release")
    g = pf.find(r"sidecar_cursor_page\s*!=\s*NULL\)[^;]*;?.*?sidecar_cursor_release\s*\(\s*thread_p\s*\)")
    put("fix_guard", "yes" if g else "no",
        "pgbuf_fix_release releases a kept page at %s" % pf.at(g) if g else "no release of last resort in pgbuf_fix_release")
    return shape


# ---------------------------------------------------------------------------
# Runs

def B(v):
    return "TRUE" if v == "yes" else "FALSE"


def runs_for(shape):
    v = {k: x[0] for k, x in shape.items()}
    # with no bound, the old code's bound of 8 stamp cycles
    bound = 0 if v["reread_bound"] == "none" else int(v["reread_bound"])
    cycles = (bound or 8) if v["model.stamp_cycles"] == "reread_bound" else (bound or 8) - 1
    read = {"RereadBound": str(bound), "MaxStampsB": "1", "HomeRecheck": '"%s"' % v["home_recheck"],
            "FwdTypeCheck": B(v["fwd_type_check"]), "FwdSlotReuse": B(v["fwd_slot_reuse"]),
            "VacuumAtomic": B(v["vacuum_fwd_held"])}
    if v["stamp_relocates"] != "yes":
        raise ShapeError("heap_delete_home no longer relocates a stamped store record; SidecarStoreRead assumes it can")
    row = {"Ops": '{"UPDATE", "DELETE"}', "RetryBound": v["retry_bound"], "WriteOrder": '"%s"' % v["write_order"],
           "PlanOnce": B(v["plan_once"]), "RowLock": B(v["row_lock"]),
           "FallbackLock": '"%s"' % v["fallback_lock"], "DelidTest": B(v["delid_test"]),
           "Fallback": B(v["fallback"]), "OnAbsent": '"%s"' % v["on_absent"]}
    w3 = '{"t1", "t2", "t3"}'
    w_fetch = "{%s}" % ", ".join('"t%d"' % i for i in range(1, int(v["retry_bound"]) + 2))
    latch = {"RelBeforeCall": B(v["rel_before_call"]), "RelBeforeHotFix": B(v["rel_before_hot_fix"]),
             "RelBeforeStoreFix": B(v["rel_before_store_fix"]), "FixGuard": B(v["fix_guard"]),
             "ApplyNoPage": B(v["apply_no_page"])}
    return [
        ("SidecarStoreRead", "ReadReturnsOwnValue", dict(read, MaxStampsA="2", FwdSlots='{"F", "O", "P"}'), "View",
         "the read of store record A; stamps of A twice and B once, each relocating or in place, rollback, commit, vacuum"),
        ("SidecarStoreRead", "AbsentOnlyIfRemoved",
         dict(read, MaxStampsA=str(cycles), FwdSlots="{%s}" % ", ".join('"F%d"' % i for i in range(1, cycles + 1))),
         "View",
         "the read of A while A is stamped and rolled back up to %d times" % cycles),
        ("SidecarRowWrite", "LatchedReaderFinds", dict(row, Writers=w3), "View",
         "three writers (UPDATE or DELETE, commit or rollback), store vacuum, a latched reader"),
        ("SidecarRowWrite", "StoreMatchesRow", dict(row, Writers=w3), "View", "three writers, store vacuum"),
        ("SidecarRowWrite", "FetchNoLostRow", dict(row, Writers=w3), "View", "three writers, a committed fetch"),
        ("SidecarRowWrite", "FetchNoError", dict(row, Writers=w3), "View", "three writers, a committed fetch"),
        ("SidecarRowWrite", "FetchNoError", dict(row, Writers=w_fetch, Ops='{"UPDATE"}'), "View",
         "%s committed UPDATEs during one committed fetch: the retries run out and the lock fallback reads"
         % (int(v["retry_bound"]) + 1)),
        ("SidecarRowWrite", "FetchNoError", dict(row, Writers='{"t1", "t2", "t3", "t4"}', Ops='{"UPDATE"}',
                                                 RetryBound="1"), "View",
         "the retry bound reduced to 1 and 4 UPDATEs: the fallback, and after it a second visible read"),
        ("SidecarCodeLatch", "NoDeadlock", latch, "StateView",
         "a cursor scan, a large-column UPDATE, store vacuum of a relocated record, a routine's worker"),
    ]


def tla2tools_jar(cache_dir):
    env = os.environ.get("TLA2TOOLS_JAR")
    if env:
        return env
    jar = os.path.join(cache_dir, "tla2tools-%s.jar" % TLA2TOOLS_VERSION)
    if not os.path.isfile(jar):
        os.makedirs(cache_dir, exist_ok=True)
        tmp = jar + ".part"
        urllib.request.urlretrieve(TLA2TOOLS_URL, tmp)
        os.replace(tmp, jar)
    with open(jar, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != TLA2TOOLS_SHA256:
        raise ShapeError("%s has SHA-256 %s, expected %s" % (jar, digest, TLA2TOOLS_SHA256))
    return jar


def run_tlc(jar, work, module, prop, consts, view, workers):
    os.makedirs(work, exist_ok=True)
    shutil.copy(os.path.join(HERE, module + ".tla"), work)
    with open(os.path.join(work, prop + ".cfg"), "w") as f:
        f.write("CONSTANTS\n" + "".join("    %s = %s\n" % kv for kv in sorted(consts.items())))
        f.write("INIT Init\nNEXT Next\nVIEW %s\nINVARIANT %s\n" % (view, prop))
    java = os.environ.get("JAVA", "java")
    os.makedirs(os.path.join(work, "tmp"), exist_ok=True)
    # each TLC unpacks its standard modules into java.io.tmpdir; a shared one races between parallel runs
    cmd = [java, "-XX:+UseParallelGC", "-Djava.io.tmpdir=" + os.path.join(work, "tmp"), "-cp", jar, "tlc2.TLC", "-workers", str(workers), "-config", prop + ".cfg",
           "-metadir", os.path.join(work, "states"), "-cleanup", module]
    with open(os.path.join(work, prop + ".out"), "w") as log:
        subprocess.run(cmd, cwd=work, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    with open(os.path.join(work, prop + ".out")) as f:
        out = f.read()
    states = re.findall(r"(\d+) distinct states found", out)
    count = states[-1] if states else "?"
    if "Model checking completed. No error has been found." in out:
        return "PASS", count, [], []
    if re.search(r"Invariant %s is violated" % re.escape(prop), out):
        actions = re.findall(r"^State \d+: <(\w+)", out, re.M)
        words = [json.loads(w) for w in re.findall(r'^/\\ last = (".*")$', out, re.M)]
        return "FAIL", count, actions, words[1:]
    return "ERROR", count, [], [os.path.join(work, prop + ".out")]


def contains_in_order(seq, sub):
    it = iter(seq)
    return all(any(x == s for x in it) for s in sub)


def check_property(jar, out, idx, run, shape, known, hypothetical, workers):
    module, prop, consts, view, about = run
    lines, removed, status = [], {}, "pass"
    cur = dict(shape)
    for rnd in range(MAX_ROUNDS):
        res, count, actions, words = run_tlc(jar, os.path.join(out, "%d-%s-%d" % (idx, prop, rnd)),
                                             module, prop, runs_for(cur)[idx][2], view, workers)
        head = "    " + ("with %s: " % ", ".join("%s=%s" % kv for kv in removed.items()) if removed else "")
        if res == "PASS":
            lines.append(head + "PASS  [%s distinct states]" % count)
            return status, lines
        if res == "ERROR":
            lines.append(head + "MODEL OR TOOL ERROR: read %s" % words[0])
            return "error", lines
        match = None
        for fid, f in known.items():
            if f["property"] == prop and all(cur[k][0] == v for k, v in f["when"].items()) \
                    and contains_in_order(actions, f["signature"]):
                match = (fid, f)
                break
        steps = ["      %2d. %s" % (i + 1, w) for i, w in enumerate(words)]
        if match is None:
            lines.append(head + ("FAIL under the hypothetical shape" if hypothetical else "NEW FINDING")
                         + "  [%s distinct states]" % count)
            lines.extend(steps)
            return "new", lines
        fid, f = match
        lines.append(head + "KNOWN FINDING %s (%s)  [%s distinct states]" % (fid, f["ticket"], count))
        lines.extend(steps)
        status = "known"
        for k, v in f["neutralize"].items():
            cur[k] = (v, "neutralized for the next run")
            removed[k] = v
    lines.append("    stopped after %d rounds" % MAX_ROUNDS)
    return "error", lines


# ---------------------------------------------------------------------------
# Coverage record and drift


def read_coverage():
    with open(README, encoding="utf-8") as f:
        md = f.read()
    m = re.search(r"<!-- coverage:begin -->\s*```text\n(.*?)```\s*<!-- coverage:end -->", md, re.S)
    if not m:
        raise ShapeError("README.md has no coverage block")
    sync, covers = None, []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("sync-commit:"):
            sync = line.split(":", 1)[1].strip()
        elif ":" in line and not line.startswith("covers"):
            path, names = line.split(":", 1)
            covers.extend((path.strip(), n.strip()) for n in names.split(","))
    return sync, covers


def drift(root, src):
    sync, covers = read_coverage()
    if subprocess.run(["git", "-C", root, "cat-file", "-e", sync + "^{commit}"], capture_output=True).returncode:
        return sync, None
    old = Source(root, sync)
    changed = []
    for path, name in covers:
        try:
            a = " ".join(Fn(old, path, name).body.split())
        except ShapeError:
            a = None
        try:
            b = " ".join(Fn(src, path, name).body.split())
        except ShapeError:
            b = None
        if b is None:
            changed.append("%s: %s (no longer found)" % (path, name))
        elif a != b:
            changed.append("%s: %s" % (path, name))
    return sync, changed


# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--rev")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--only", default="", help="run only properties whose name contains this")
    ap.add_argument("--out")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()

    try:
        root = repo_root(args.repo)
        src = Source(root, args.rev)
        shape = extract_shape(src)
        shape["model.stamp_cycles"] = ("reread_bound", "model bound: as many stamp cycles of A as the reread bound")
        hypothetical = False
        for kv in args.set:
            k, _, v = kv.partition("=")
            if k not in SHAPE_DOMAINS or v not in SHAPE_DOMAINS[k]:
                raise ShapeError("--set %s: keys and values are in SHAPE_DOMAINS" % kv)
            shape[k] = (v, "HYPOTHETICAL (--set)")
            hypothetical = True
        jar = tla2tools_jar(os.path.expanduser("~/.cache/tlaplus"))
    except ShapeError as e:
        print("OUT OF SYNC: %s" % e)
        return 2

    print("source: %s" % ("commit %s" % args.rev if args.rev else "work tree %s" % root))
    print("shape read from the code:")
    for k in SHAPE_DOMAINS:
        print("  %-22s %-20s %s" % (k, shape[k][0], shape[k][1]))

    with open(KNOWN_FINDINGS) as f:
        known = json.load(f)
    out = args.out or tempfile.mkdtemp(prefix="sidecar-code-")
    try:
        runs = runs_for(shape)
    except ShapeError as e:
        print("OUT OF SYNC: %s" % e)
        return 2
    chosen = [(i, r) for i, r in enumerate(runs) if args.only in r[1]]
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {pool.submit(check_property, jar, out, i, r, shape, known, hypothetical, args.workers): i
                for i, r in chosen}
        for fu in concurrent.futures.as_completed(futs):
            results[futs[fu]] = fu.result()

    print("results (TLC %s):" % TLA2TOOLS_VERSION)
    worst = 0
    for i, r in chosen:
        status, lines = results[i]
        print("  %s.%s  (%s)" % (r[0], r[1], r[4]))
        for line in lines:
            print(line)
        worst = max(worst, {"pass": 0, "known": 0, "new": 1, "error": 2}[status])
    for fid, f in known.items():
        if not all(shape[k][0] == v for k, v in f["when"].items()):
            print("note: known finding %s no longer applies (the code no longer has its shape): confirm the fix, "
                  "then update known_findings.json" % fid)

    sync, changed = drift(root, src)
    if changed is None:
        print("sync commit %s is not in this repository; covered code not compared" % sync)
    elif changed:
        print("covered code changed since sync commit %s:" % sync[:12])
        for c in changed:
            print("  " + c)
        print("Confirm that the models still describe this code (README.md, 'Update the verification').")
        if worst == 0:
            worst = 3
    print("generated models and TLC output: %s" % out)
    return worst


if __name__ == "__main__":
    sys.exit(main())
