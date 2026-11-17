# PR 8547 temporary-page writeback review

Review date: 2026-11-17, Asia/Seoul. This report helps PR reviewers decide what needs correction and further verification in [CUBRID/cubrid#8547](https://github.com/CUBRID/cubrid/pull/8547).

**Verdict: changes-required. One confirmed P2 defect. Coverage remains partial and follow-up review is required before merge.** The new request flag mixes atomic writes with an ordinary read. A production-source probe and an independent coordinator replay both report a data race. A possible CDC shutdown overlap remains unverified. The original YCSB OOM and performance non-regression have not been independently established.

## Reviewed snapshot

| Identity | Value |
| --- | --- |
| PR base, `develop` | `086f8acf31be4c1e1213e8119c2c2ec13f8f0047` |
| PR head | `02bebe81790980ef8e3ffd7767a444d035603261` |
| Merge base | `95cc1bc172a7b431948e7b8297987a9466371986` |
| Patch SHA-256 | `16aeed133170ff6a88996fd5c79dc8f9dad2046a3c10a3c1747c56ef434bbd8e` |
| Comparison | `git diff 95cc1bc172a7b431948e7b8297987a9466371986 02bebe81790980ef8e3ffd7767a444d035603261` |

All five changed paths were inspected: `src/base/system_parameter.c`, `src/base/system_parameter.h`, `src/storage/file_io.c`, `src/storage/file_io.h`, and `src/storage/page_buffer.c`. The patch adds 276 lines and removes three. Source was inspected in a detached checkout at the pinned head, without submitted-source modifications. Requirements came from the PR and [CBRD-26232](https://jira.cubrid.org/browse/CBRD-26232), including its later comments narrowing the implementation to temporary-page dirty cache. [Coverage](coverage.md) records owners and limits.

## F1: P2 request flag has a C++ data race

The new [consumer condition at `file_io.c:814`](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/storage/file_io.c#L814) reads `temp_writeback_requested` as an ordinary `int`. The [producer at line 797](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/storage/file_io.c#L797) concurrently writes it with `ATOMIC_TAS_32`. On Linux that helper uses `__sync_lock_test_and_set` in [porting.h](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/base/porting.h#L833). There is no common lock around these accesses. Atomic writes do not make an ordinary read race-free.

The normal producer and writeback daemon can access the same volume concurrently. The probe sets the supported threshold to one page and runs each actor for 100,000 iterations. Its startup gate synchronizes only startup, leaving the production request operations unchanged. ThreadSanitizer reports the conflicting producer write and consumer read. This is a demonstrated language-level concurrency defect. A lost writeback request, server crash, or data corruption was not demonstrated.

Both the flag and its accesses are added by this patch and absent from the merge base. Use a consistent atomic interface for every access. Removing the ordinary early test and relying on the existing atomic exchange result is one possible correction.

### Reproduce F1

[request-race.py](request-race.py) extracts the pinned production structures, four functions, and atomic templates verbatim. It supplies type aliases, the parameter getter, and a replacement at the syscall boundary. It does not replace the request algorithm. This is a real-source probe rather than a full-server sanitizer run.

From this document's directory, with a source checkout at the reviewed head and Clang 19 available:

```sh
python3 request-race.py /path/to/cubrid /tmp/pr8547-request-probe
clang++-19 -std=c++17 -O1 -g -fsanitize=thread -fno-omit-frame-pointer -pthread /tmp/pr8547-request-probe/request_probe.cpp -o /tmp/pr8547-request-probe/request_probe_tsan
/tmp/pr8547-request-probe/request_probe_tsan race
```

Expected: no data race. Reviewer result and independent coordinator replay: exit 66, with these conflicting operations in the sanitizer report:

```text
WARNING: ThreadSanitizer: data race
Atomic write: ATOMIC_TAS_32 -> fileio_writeback_temp_pages
Previous read: fileio_writeback_requested_volume
ThreadSanitizer: reported 1 warnings
```

The coordinator also compiled a disposable control that removed only `vol_info_p->temp_writeback_requested == 0 || ` from the extracted consumer. That run exited 0 with no sanitizer warning. Submitted source was unchanged. A normal C++17 build of the same probe passed the 256-page threshold, pending-request coalescing, re-mark during syscall, and empty-pass cases. GCC's sanitizer runtime was unavailable, so the successful sanitizer runs used Clang 19.

## Observed inherited configuration problem

This is separate from F1 and is not counted as a newly introduced PR defect. The existing page-size discovery path reloads configuration with a null database name, resetting reloadable values and omitting the database-specific section. The new parameter inherits that behavior.

On the actual pinned debug server, these settings were tested with 16 KiB and 4 KiB databases:

```ini
[common]
temp_writeback_size=2M
[@r16]
temp_writeback_size=1M
[@r4]
temp_writeback_size=1M
```

| Database page size | Expected override | CSQL `;get temp_writeback_size` after startup | Server paramdump |
| --- | --- | --- | --- |
| 16 KiB | 1 MiB | `1.0M` | `[S*] temp_writeback_size=1.0M (4.0M)` |
| 4 KiB | 1 MiB | `2.0M` | `[S*] temp_writeback_size=2.0M (1.0M)` |

Both databases started and stopped successfully. The result was checked through separate CSQL and `cubrid paramdump -C` invocations. The source path is [initial parameter loading](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/transaction/boot_sr.c#L2028), [page-size discovery and reload](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/transaction/log_manager.c#L9087), and [reset of reloadable values](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/base/system_parameter.c#L6581). Preserve the database identity when reloading, or track this existing loader problem separately and state its effect on this parameter.

The initial hypothesis that all common-section byte values remained converted with a 16 KiB page size was rejected. Common settings are reloaded after page-size detection. The observed problem concerns database-specific overrides.

## Unverified CDC shutdown safety

Both reviewers independently traced ordinary request-worker shutdown before reading each other's conclusions. Request, loader, and vacuum workers stop before normal server shutdown, and the page-flush daemon is joined before the new daemon. Those facts rule out the initially proposed ordinary request-worker schedule under the existing stop/join contracts.

A remaining actor is CDC. [boot shutdown](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/transaction/boot_sr.c#L3131) destroys page-buffer daemons before CDC daemons. CDC schema extraction can call [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/transaction/log_manager.c#L13330), and a class representation cache miss can fix a page. With no page-flush daemon and no clean victim, [the fallback](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/storage/page_buffer.c#L12454) flushes victims synchronously. Dirty temporary-file headers in permanent volumes with temporary purpose may survive removal of temporary-ID volumes.

The unverified schedule requires active CDC, pending schema extraction, a cache miss, buffer pressure, a surviving dirty temporary-purpose victim, and a threshold crossing. A producer could then pass [the daemon-pointer check](https://github.com/CUBRID/cubrid/blob/02bebe81790980ef8e3ffd7767a444d035603261/src/storage/page_buffer.c#L11715) while shutdown deletes that daemon before its wakeup. The coordinator checked the relevant shutdown, fallback, and reload source locations; the second reviewer corroborated the CDC path after recording its independent initial answer.

No live-server crash or deterministic overlap was reproduced. Treat this as a material source-only risk, not a confirmed P1 finding. Before merge, establish that CDC cannot produce such a victim flush, or exercise this schedule with deterministic barriers in a debug server. [The handoff](handoff.md) records the remaining check.

## Other safety facts and verification

The existing temporary-purpose classification controls both DWB bypass and the new hook. Ordinary permanent pages retain their WAL and DWB path. Neighbor flushing reaches the same hook. These are source-trace results rather than crash-recovery tests. No log, disk, or replication format was changed, and the parameter enum was appended without shifting existing IDs, including Java PL consumers.

The threshold controls when writeback is requested. It does not bound dirty-plus-writeback memory under arbitrary storage pressure. A single daemon processes volumes serially, and a blocked volume can delay the others. Linux documents both the whole-file zero-length range and possible queue waits for WRITE requests in [sync_file_range(2)](https://man7.org/linux/man-pages/man2/sync_file_range.2.html). SA performs the request directly from the flushing thread. Slow devices, stable-write devices, and several temporary volumes need separate evidence.

The pinned source configured, built, and installed successfully with GCC, C++17, and `CMAKE_BUILD_TYPE=Debug` on Linux 5.14 x86-64. This included server, standalone, and client targets. CTest returned 0 but reported **no tests found**; that is not a unit-test pass. `git diff --check` passed.

The actual standalone CSQL runtime verified these values:

| Page size | Default | Input 0 | Input 1 byte | Input 16,385 bytes | Oversized input |
| --- | --- | --- | --- | --- | --- |
| 16 KiB | 4 MiB | 0 | 16 KiB | 32 KiB | 1 GiB accepted; 1 GiB + 1 byte rejected |
| 4 KiB | 1 MiB | 0 | 4 KiB | 20 KiB | 1 GiB rejected |

The runtime parser and bounds were exercised through CSQL `;set` and `;get`. Rejected inputs retained the preceding valid value. A separate exact-conversion-body probe sampled 4, 8, and 16 KiB pages. Dynamic reload, non-Linux compilation, and concurrent setting changes were not tested.

Static differential analysis reported zero new cppcheck, duplicate-code, or flagged-complexity findings. Clang-tidy reported throwing static initialization at the new `REGISTER_DAEMON`. That registration follows the existing `count_registry` contract, so no distinct PR defect was established. Clang-tidy coverage was incomplete for `file_io.c` and `system_parameter.c` because its isolated analysis could not resolve TBB headers. The successful full build is separate evidence and does not repair this static-analysis gap.

### Actual temporary-writeback execution

On the same debug build, standalone insertion and index creation with 456,533 rows, a 496-byte generated key, a 32 MiB data buffer, and a 1 MiB sort buffer completed with correct row counts. `strace -f -yy -e trace=sync_file_range` observed five successful calls with the default 4 MiB threshold, all on `r16_t32766`, and zero calls with `temp_writeback_size=0` on the same-size workload. The caller was the standalone flushing process, as expected. An earlier 150,000-row workload produced zero calls with either setting and was insufficient to exercise the threshold.

The workload used fresh table names for the two runs:

```sql
CREATE TABLE wb (i INTEGER, pad VARCHAR(512));
INSERT INTO wb
  SELECT ROWNUM, LPAD(CAST(ROWNUM AS VARCHAR), 16, '0') || REPEAT('x', 480)
  FROM db_class a, db_class b, db_class c
  LIMIT 456533;
CREATE INDEX wb_pad ON wb(pad);
SELECT COUNT(*) FROM wb;
```

Each run used `csql -S -u dba -c '<SQL above>' r16` under the tracer. Both returned 0 with `COUNT(*) = 456533`. One representative enabled trace was:

```text
sync_file_range(37<.../r16_t32766>, 0, 0, SYNC_FILE_RANGE_WRITE) = 0
```

This verifies the real standalone hook, syscall arguments, successful temporary-volume target, and disabled setting. It does not establish a dirty-memory bound, performance non-regression, or correct CDC shutdown. No base/head performance benchmark or constrained-cgroup OOM reproduction was performed. The host was shared and busy, so elapsed workload times are not used as comparative evidence.

### CI and testcase readiness

At 2026-11-17 19:25 KST, [the exact-head engine CI run](https://github.com/CUBRID/cubrid/actions/runs/44034316211) reported release and debug builds successful; medium, shell, SQL, and SQL-by-CCI suites remained pending. Existing cppcheck, code style, license, PR style, and memory-monitor checks passed. The TC gate reported failure because the two draft TC PRs remain open. That gate is deferred to the final engine merge handoff and is separate from regression failure.

Live GitHub refs matched the inspected local testcase refs: public `708d67916aeb850f340b264959965b0a1ebacce1`, private `20424387689feb04a7f6fe489ff4cd4128fdf430`. They contain only initialization commits and no testcase changes. The affected complete-paramdump answers under `shell/_06_issues/_11_2h/bug_bts_5423` and `shell/_40_guava/cbrd_26111` lack the new parameter line; the planned `shell/_40_guava/cbrd_26232` functional coverage is absent. This is a readiness gap, not a locally executed testcase failure. Keep the [public TC PR](https://github.com/CUBRID/cubrid-testcases/pull/4214) and [private TC PR](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4921) open during review and CI.

The remote PR base and head were rechecked after runtime verification and still matched the reviewed snapshot.

## Budget and completion limits

The bounded plan used three reviewers: `gpt-6.1-sol` for concurrency and `gpt-6.1-terra` for I/O and configuration. Each logical assignment had a 15-minute target, with a 10-minute checkpoint. Two short follow-ups remained within the original I/O and configuration assignments. No nested reviewers were launched. The planned envelope was 65 agent-minutes, including 20 minutes reserved for the coordinator. No hard spending cap was enforced. Token consumption and provider allowance were unavailable and are not inferred from response length.

The concurrency reviewer saved its checkpoint report and reproduction, then its final turn ended in a tool-level error. Its remaining volume-lifetime coverage is incomplete. The coordinator independently replayed F1 and checked the cited shutdown source, preserving the unresolved CDC risk. The other two assignments returned terminal reports with their stated gaps. Inspection ended at approximately 19:26 KST within the coordinator's analysis target; document preparation and publication followed. Individual reviewer time targets were met where completion was observable, while the interrupted reviewer had no successful terminal coverage result. Actual token consumption and any per-agent spending compliance are unverifiable. Source inspection, passing probes, and successful builds do not certify merge safety. Follow-up is required for F1 after correction, CDC lifetime, regression/TC readiness, and the remaining effectiveness/performance evidence.
