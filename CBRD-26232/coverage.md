# PR 8547 review coverage

Snapshot: base `086f8acf31be4c1e1213e8119c2c2ec13f8f0047`, merge base `95cc1bc172a7b431948e7b8297987a9466371986`, head `02bebe81790980ef8e3ffd7767a444d035603261`, reviewed 2026-11-17 KST. [Report](code-review.md).

| Changed path or boundary | Primary owner | Evidence and result | Remaining action |
| --- | --- | --- | --- |
| `src/base/system_parameter.c` | Configuration | Source and live SA bounds; live server 4 KiB override loss corroborates inherited loader behavior | Decide handling of inherited override loss; test reload |
| `src/base/system_parameter.h` | Configuration | Appended IDs; Java PL ordinal assertions and consumers traced; Linux targets build | Non-Linux compilation not run |
| `src/storage/file_io.c` | Concurrency; I/O | F1 independently replayed with TSan; narrow request-state checks pass; syscall and traversal traced | Correct atomic access; complete volume lifecycle and multi-volume checks |
| `src/storage/file_io.h` | I/O | Declarations and callers inspected; server, SA and client targets build | Other supported platforms not built |
| `src/storage/page_buffer.c` | I/O; concurrency | Flush hook, WAL/DWB, SA, daemon lifecycle and neighbor flushing traced | CDC shutdown overlap and slow-device behavior remain unverified |
| Standards and specification | Coordinator | Full patch, JIRA/PR requirements, diff whitespace and static results inspected | Effectiveness/performance and final regression evidence remain bounded |

The shared challenge was whether ordinary shutdown can destroy the new daemon while a producer can still wake it. Concurrency used `gpt-6.1-sol`; I/O used `gpt-6.1-terra`. Both independently found worker stop and page-flush join before daemon deletion, without establishing a request-worker overlap. Concurrency subsequently identified the surviving CDC path; I/O checked that path after recording its independent answer. Both retain CDC as an unverified risk. A real-server overlap was not executed.

Recovery was combined with I/O because this patch retains the existing temporary-page classification and WAL/DWB branch. No recovery-insert, vacuum slot, or new durable-record invariant is changed. HA format review was combined with configuration and I/O because there is no changed replication producer, wire format, or durable layout. These dispositions are source-based and do not substitute for regression tests.

Dropped or separated candidates: concurrency's ordinary request-worker shutdown hypothesis was narrowed by stop/join evidence; a simple common-section byte conversion problem was disproved by the page-size-triggered reload; the database-specific override loss was reproduced and separated as inherited behavior; throwing daemon registration was not established as a distinct defect. Stale descriptor hints, inherited partial counts on volume reuse, and slow-volume serialization remain bounded source concerns without demonstrated wrong database behavior.

The concurrency assignment ended with a saved checkpoint followed by a tool-level error. Volume cache growth, reuse, and all surviving indirect producers were not fully verified. Runtime benchmarks, constrained-cgroup OOM, stable-write storage, slow-device isolation, and cross-platform builds were not completed. The exact next checks are in [handoff.md](handoff.md).
