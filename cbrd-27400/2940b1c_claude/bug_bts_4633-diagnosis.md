# CBRD-27400 bug_bts_4633: `log_get_undo_record` assertion is a torn read of `append_lsa` during log page rollover

Date: 2026-09-08. Engine: `2940b1cfbc3c2d4d0fac3f9244a960350debd380` (PR #6864 head). Testcase: `01af62db73351ea3fdb445ccd03a19c39084d1cc` (`tc/pr-6864`). JIRA: [CBRD-27400](http://jira.cubrid.org/browse/CBRD-27400) (sub-task of CBRD-26583; originally observed while analysing PR #6864 CI for CBRD-26939). Work item: **72**. Agent: Claude (continuing the Codex handoff in `/tmp/handoff-bug-bts-4633-claude.md`).

## Verdict

The `cub_server` core in GHA run 34186373809 shard 31 is caused by a **non-atomic read of `log_Gl.hdr.append_lsa`** inside `log_get_undo_record` (`src/transaction/log_manager.c:9855-9856`) racing with the **append-page rollover** in `logpb_next_append_page` (`src/transaction/log_page_buffer.c:2658-2659`). The optimizer splits the 8-byte `LOG_LSA` read into a page-ID load and a later offset load; the rollover writes the page ID and the offset with two separate stores. A reader that loads the page ID before the rollover and the offset after it compares `process_lsa` against the impossible address `(old page, new small offset)`, and `assert (LSA_LT (&process_lsa, &oldest_prior_lsa))` fires.

This is pre-existing engine code (blame: `63378ed15c`, 2016-05-06, for both the assertion and the caller's `TODO: fix atomicity issue on x86` at `src/storage/heap_file.c:26369`), byte-for-byte identical on `origin/develop`. The test tables are integer-only; the failing path contains no OOS logic. **The CI failure is not an OOS regression.** It is a latent race whose crash only optdebug builds can show: a debug build copies the struct with one 8-byte load and cannot tear, and release/RelWithDebInfo build with `-DNDEBUG` (`CMakeLists.txt:230-233`) so the plain `assert` is compiled out and the torn value flows on silently into the same comparisons.

Reproduced 4 of 4 probed runs on this PR head with identical signature and captured inputs (see below); the exact CI binary (GCC 8.5.0) contains the same split read.

## Evidence identity

| Item | Value |
|---|---|
| GHA job | https://github.com/CUBRID/cubrid/actions/runs/34186373809/job/101937472116 |
| CI core summary | `Core dumped in log_get_undo_record at src/transaction/log_lsa.hpp:173` (inlined `log_lsa::operator<` from `log_manager.c:9856`) |
| CI stack | `log_get_undo_record <- heap_get_visible_version_from_log (heap_file.c:26399) <- heap_get_visible_version_internal <- heap_scan_get_visible_version_impl <- heap_next_internal <- heap_next <- scan_next_heap_scan <- ... <- qexec_intprt_fnc` |
| CI binary | `http://192.168.1.48:30080/builds/pr/2940b1c.../debug/CUBRID/lib/libcubrid.so.11.5`, BuildID `2d15b11204389cb271f79f0403a11645a494d72b`, `.comment` = `GCC: (GNU) 8.5.0 20210514 (Red Hat 8.5.0-28)` (see `evidence/PROVENANCE.txt`) |
| Local build | optdebug, GCC 11.5, `/home/vimkim/.cub/install/oos-bug-bts-4633/optdebug`, copied to the harness |

The test script prints `bug_bts_4633-1 : OK` because it accepts a non-empty Java stderr (the `MaxPermSize` JVM warning); only CTP's core detection reports the failure.

## Mechanism

### Data layout and the two accesses

`LOG_LSA` (`src/transaction/log_lsa.hpp:36-40`) is one 8-byte word: `int64 pageid:48` (bytes 0-5) and `int64 offset:16` (bytes 6-7). `log_get_append_lsa()` returns `&log_Gl.hdr.append_lsa` (`log_manager.c:605`), and `log_get_undo_record` does:

```c
oldest_prior_lsa = *log_get_append_lsa ();
assert (LSA_LT (&process_lsa, &oldest_prior_lsa));
```

**Reader, exact CI binary (GCC 8.5.0, `evidence/ci-gcc8-get-undo.asm`):**

```text
+45   mov    -0x4048(%rbp),%rdx        ; process_lsa (spilled 3rd argument)
+52   mov    (%rax),%rcx               ; LOAD 1: whole word -> page id (shl/cmp on low 48 bits)
+66   cmp    %rdx,%rsi ; jg +144       ; append.pageid > process.pageid -> pass
+71   xor    -0x4048(%rbp),%rcx ; test $0xffffffffffff ; jne +106   ; page ids differ -> assert
+93   movzwl -0x4042(%rbp),%edx        ; process.offset
+100  cmp    0x6(%rax),%dx             ; LOAD 2: offset RE-READ FROM MEMORY, ~10 instructions later
+104  jl     +151                      ; process.offset < append.offset -> pass
+106  ... call __assert_fail
```

**Reader, local optdebug (GCC 11.5, `evidence/local-gcc11-optdebug-get-undo.asm`):** same shape, `+45 mov (%rax),%rcx` then `+48 movzwl 0x6(%rax),%esi`; the assert-failure branch is the unique entry at `+117`.

**Writer, `logpb_next_append_page` (both binaries, `evidence/*next-append.asm`):**

```text
mov  %rax,0x118(%rbx)      ; STORE 1: pageid++ as a whole-word read-modify-write -> (P+1, old offset)
xor  %eax,%eax
mov  %ax,0x11e(%rbx)       ; STORE 2: offset = 0 as a 2-byte store          -> (P+1, 0)
```

The writer holds `LOG_CS`; the reader holds nothing. x86 preserves store order, so a reader whose LOAD 1 precedes STORE 1 and whose LOAD 2 follows STORE 2 (plus any subsequent appends to page P+1) computes `(P, y)` where `y` is the young offset on the new page.

### Why only this assertion can fire

`heap_get_visible_version_from_log` (`heap_file.c:26369-26377`) first checks the same address and, if needed, flushes the prior list under `LOG_CS` and asserts `!LSA_LT (append, prev)`. `logpb_fetch_page` (`log_page_buffer.c:1740`) re-checks `LSA_LE (append, req)` under `LOG_CS`. `append_lsa` is monotonic and every `prev_version_lsa` is `tdes->tail_lsa`, which `prior_lsa_next_record_internal` assigns and links into the prior list under one `prior_lsa_mutex` hold (`log_append.cpp:1359-1522`, `:1619`). So for coherent values, `append > prev` always holds by the time `log_get_undo_record` runs, and the CI signature (caller's checks pass, strict `<` fails) would require `prev == append`, which is structurally impossible. Only the torn read produces it. The captured values below confirm this directly.

## Reproduction

### Harness

Isolated PID/IPC/network/mount namespaces (`enter-gdb2.sh`, runtime bound at `/mnt`), the exact testcase Java workload, optdebug engine. GDB attaches to `cub_server` in **non-stop** mode (set via `-iex` before attach) and runs `probe.py`:

- Breakpoint at `log_get_undo_record+48`, i.e. between LOAD 1 and LOAD 2. Its Python `stop()` never reports a stop; it reads `rcx` (LOAD 1 word) and `process_lsa`, and only when `process_lsa.pageid == LOAD1.pageid` **and** `log_Gl.prior_info.prior_lsa.pageid > LOAD1.pageid` (the next prior-list flush will roll the page) it polls `log_Gl.hdr.append_lsa` for up to 200 ms until the rollover lands, then resumes. Nothing in the database or log is modified; the thread is merely preempted where the OS scheduler could preempt it.
- Breakpoint at `+117` (assert branch, registers still intact) records LOAD 1, LOAD 2 (`esi`), `process_lsa`, the coherent `append_lsa`/`prior_lsa`, and a backtrace, then detaches so the server aborts and dumps core normally.
- `PROBE_MODE=count` disables the pause entirely (the breakpoint still costs one ptrace stop per hit).

Command (one unattended run):

```bash
CASES_DIR=/mnt/shell-s7/cases PROBE_MODE=pause REPRO_TIMEOUT=900 \
  bash .scratch/bts4633/enter-gdb2.sh <attempt> > .scratch/bts4633/evidence/<attempt>.console 2>&1
```

### Results

| Attempt | Workload | Mode | Time to assert | LOAD 1 word | `process_lsa` | LOAD 2 offset | Compared value | Coherent `append_lsa` at assert | Caller path |
|---|---|---|---|---|---|---|---|---|---|
| gdb-02 | full 7 scenarios | pause | ~6 s (scenario 1) | (201, 16328) | (201, 15112) | 48 | **(201, 48)** | (202, 48) | index scan: `heap_get_visible_version <- scan_next_index_lookup_heap <- qexec_execute_update` |
| gdb-03 | scenario 7 only | pause | 6.6 s | (208, 15488) | (208, 14720) | 3912 | **(208, 3912)** | (209, 3912) | **CI path**: `heap_scan_get_visible_version_impl <- heap_next_internal <- heap_next <- scan_next_heap_scan <- ... <- qexec_intprt_fnc` |
| gdb-04 | full 7 scenarios | count (no pause) | 4.7 s (scenario 1) | (182, 16368) | (182, 15976) | 712 | **(182, 712)** | (183, 712) | index scan, as gdb-02 |
| gdb-05 | scenario 7 only | pause, using the compact probe published in CBRD-27400 (`evidence/probe-issue.py`, `process_lsa` read via DWARF) | ~3 s | (204, 11968) | (204, 11416) | 1224 | **(204, 1224)** | (205, 1224) | **CI path** |

All four: `+117` reached, `__assert_fail` in `log_get_undo_record`, `SIGABRT`, core written (`runtime/gdb-0N/core.transaction.*`, ~2.5 GB each). `evidence/gdb-02.core-bt.txt` is the core's own backtrace. `evidence/gdb-0N.probe-events.log` hold the probe records (attach-time spurious stops removed).

In every case `process_lsa` was a valid, already-appended record: it is below the coherent `append_lsa` observed by LOAD 1 on the same page. Each failure needs `process_lsa.offset >= LOAD 2 offset`, which is why the compared value shows the young offset of the *next* page.

gdb-04 matters: no artificial pause was applied, only the sub-millisecond ptrace stop that any breakpoint costs, and the race still landed within 5 s. In gdb-03, seven earlier 200 ms pauses on one thread saw no rollover (the paused reader holds the heap page read latch, so updaters block and no commit triggers a flush); the eighth coincided with a flush and failed. The rollover is executed by whoever runs `logpb_prior_lsa_append_all_list` (log flush thread or another reader), so the window is between two reader instructions and an unrelated thread's two stores.

Attempt gdb-01 is discarded: the first probe treated an attach-time spurious stop as terminal and detached before the workload ran.

### Unprobed rate

Ten consecutive runs of the scenario-7-only workload with **no debugger attached** (`loop-plain.sh`, attempts `plain-s7-01..10`, ~20 s of load each) produced no core and no Java error. Together with the earlier full-workload replays (debug_gcc `baseline-02`: clean; optdebug `optdebug-baseline-01`: clean until a Java heap exhaustion in scenario 7 that is a test artifact), this shows the natural rate is low: about 200 s of unprobed optdebug load here versus one hit in CI. Widening the window by a single ptrace stop (gdb-04) or a targeted pause (gdb-02, gdb-03) makes it fire within seconds every time. A statistically meaningful natural rate would need far more unprobed CI-like runs and was not attempted.

### Hypotheses from the handoff

1. **Mixed append address from the two reads during rollover: confirmed.** Captured LOAD 1 and LOAD 2 straddle a rollover in all three runs; the compared value is never a value `append_lsa` ever held.
2. Invalid previous-version address stored in the row: **excluded.** Captured `process_lsa` values are below the coherent append position and lie on the current append page, exactly where a fresh undo record should be; an invalid address would also trip `heap_file.c:26377` first.
3. Undo record still pending in the prior list: **excluded.** Same captured values; the caller flushes the prior list under `LOG_CS` before fetching, and `tail_lsa` assignment and list linking share one mutex hold.

## Why CI hits it rarely

The unwidened window is a few nanoseconds (adjacent loads locally; ~10 instructions in the GCC 8 binary), and the two rollover stores must both land inside it. Under this workload the other preconditions are almost always true: the previous version is on the current append page in 82/82 (gdb-02), 74/135 (gdb-03) and 34/34 (gdb-04) hits, and the young offset on the new page is below almost any offset on the old page. Log pages are 16 KB and 40 threads keep updating the indexed `t1`, so rollovers are frequent (8 in 4.7 s even with the server slowed by breakpoints; scenario 1's table has a primary key plus one index, scenario 7's has a primary key plus nine). Debug builds are immune (single 8-byte struct copy), which matches the earlier debug_gcc replays that never failed; release builds tear the same way but have no assert to fail.

## Related exposure (not reproduced, noted only)

Between STORE 1 and STORE 2 the word transiently reads `(P+1, old offset)`, a position *ahead* of reality. A coherent single-load reader (`heap_file.c:26369`, `logpb_fetch_page`) that sees it for a record on page P+1 can skip the prior-list flush or try to copy a log page that has not been created yet. Same root cause, different symptom; it should be covered by the same fix.

## Fix direction (not implemented; no engine edits were made)

Publish and consume `log_Gl.hdr.append_lsa` as one 64-bit value: in `logpb_next_append_page` build the new LSA and store the whole word once (an atomic 8-byte store), and give lock-free readers (`log_get_undo_record`, `heap_get_visible_version_from_log`, `logpb_fetch_page`) an accessor that performs a single atomic 8-byte load into a local copy before any field access. Alternatively take `LOG_CS` for the check, at a cost. The 2016 `TODO: fix atomicity issue on x86` describes exactly this. A regression test at the public JDBC seam cannot pin a nanosecond window; the probe harness in `evidence/` is the reproducible check.

## Implications for PR #6864

`bug_bts_4633` should be treated as a pre-existing flaky engine race, independent of OOS and of the CDC failure `cbrd_27064` in the same shard. Caveat: OOS could change log volume and therefore rollover frequency in other workloads; this was not measured against `develop`, and the test's integer-only tables do not exercise OOS at all.

## Files

- This directory: `bug_bts_4633-diagnosis.md`, `evidence/` (probe, drivers, probe records, both binaries' disassembly, CI binary provenance, core backtrace, scenario-7-only `TestBasel.java`).
- Harness and cores (not copied, large): `/home/vimkim/gh/cb/oos-bug-bts-4633/.scratch/bts4633/` (`runtime/gdb-02`, `gdb-03`, `gdb-04`, `evidence/`).
- Earlier CI extraction (Codex): `/home/vimkim/gh/my-cubrid-docs/cbrd-26939/2940b1c_codex/bug_bts_4633.gha-failure.txt`.
