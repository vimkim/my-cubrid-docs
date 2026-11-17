# PR 8547 review handoff

The user requested the discussed three-track review of [PR 8547](https://github.com/CUBRID/cubrid/pull/8547). The bounded review found one confirmed P2 request-flag race and material remaining evidence gaps. The [report](code-review.md) and [coverage](coverage.md) preserve this snapshot. No source fixes or formal GitHub review submission were authorized or performed.

| Identity | Revision |
| --- | --- |
| PR base | `086f8acf31be4c1e1213e8119c2c2ec13f8f0047` |
| Merge base | `95cc1bc172a7b431948e7b8297987a9466371986` |
| Head | `02bebe81790980ef8e3ffd7767a444d035603261` |
| Diff SHA-256 | `16aeed133170ff6a88996fd5c79dc8f9dad2046a3c10a3c1747c56ef434bbd8e` |

Compare merge base to head. Recheck PR movement before additional work. Preserve this report when reviewing a changed snapshot.

1. Recheck F1 after correction. Run the published [production-source probe](request-race.py) and independently repeat the sanitizer run. Check that every access to `temp_writeback_requested` uses a consistent atomic interface.
2. Resolve CDC shutdown lifetime before merge. Trace CDC schema extraction through `heap_attrinfo_start`, class representation cache miss, `pgbuf_fix`, and synchronous victim flushing after the page-flush daemon is gone. Use a debug server with supplemental logging, a permanent volume with temporary purpose, dirty cached temporary-file headers, and buffer pressure. Establish or rule out actor overlap with deterministic barriers around the request and daemon deletion. A constructed pointer-only test does not prove these runtime prerequisites.
3. Finish temporary-volume cache growth/reuse coverage. Check metadata publication and descriptor/entry lifetime against the new independent scanner. Distinguish inherited lookup conventions from a newly reachable consequence.
4. Decide the existing 4 KiB startup override problem. The report reproduces `[@DB]=1M` becoming `[common]=2M`. Track an existing loader correction separately if appropriate; do not call it a new generic loader defect introduced by this PR.
5. Complete effectiveness and performance evidence. Establish temporary-page writeback on representative server workloads, then compare base, enabled head, and disabled head under controlled conditions. Measure file-specific dirty plus writeback, storage demand, and victim-dependent tail latency. Resolve the PR's open sort-tail explanation. Cover multiple temporary volumes, slow/stable-write storage, and the original constrained-cgroup YCSB claim if that remains in issue scope. An asynchronous threshold is not a universal memory cap.
6. Recheck current engine/TC revisions and finish regression evidence. Live TC refs inspected for this report were public `708d67916aeb850f340b264959965b0a1ebacce1` and private `20424387689feb04a7f6fe489ff4cd4128fdf430`; both are initialization-only. Update affected paramdump answers and add the planned functional coverage. Keep TC PRs open through review and CI; defer their gate finalization to the authorized engine merge handoff.

The coordinator retained raw evidence and isolated debug runtime artifacts under `/home/vimkim/temp/cubrid-pr-8547-review-20261117T1008Z`. The durable work item is `992`. Local-only logs are supplementary; the report includes the essential results and published reproduction needed by remote readers. The submitted source checkout and its unrelated submodule changes were preserved. Reuse the existing review evidence rather than restarting a full panel.
