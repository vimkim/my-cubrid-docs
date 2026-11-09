# TC PR4360 review coverage

Snapshot 2026-11-09, Asia/Seoul. Base and merge base `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`; head `1d349fe7392b41384bbf3bdb327755f10f4a4286`. [Review report](tc-pr4360-review.md).

| Path or boundary | Primary reviewer | Invariant and evidence | Result |
| --- | --- | --- | --- |
| `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh`, every changed hunk | Systems-loader, gpt-6.1-terra high | Routing, direct-child domain, explicit commit interval, expected failure counts, batch rollback, preserved rows and later valid load. Source tracing and revalidated native case with 28 OK. | Complete within the selected Linux fixture. No confirmed defect. |
| `shell/_06_issues/_14_1h/bug_bts_13242/cases/bug_bts_13242.sh`, every changed hunk | Concurrency-locking, gpt-6.1-sol high | SELECT precedes readiness, transaction remains open during lockdb, timeout/child errors persist as NOK, unchanged golden answer. Three revalidated native runs and actual child-status probe. | Complete within bounded source/probe coverage. No confirmed defect. |
| Failure-to-verdict challenge, both scripts | Both reviewers, independent initial answers | Can SQL, CSQL or utility failure, or early rollback, produce a false PASS? Both traced CSQL and actual CTP append/verdict consumers. Coordinator replayed actual wait function with real child statuses. | NOK persistence verified. CSQL statement-exit caveat is pre-existing; no newly introduced false PASS established. |
| Standards and specification | Coordinator | Pinned diff, unchanged test1/test3 and golden files, related CBRD-27424 context and prior partition assessment. Bash syntax and whitespace checks. | No material documented-standard or conformance violation found. |
| HA and storage/WAL | Not applicable | Only two local shell regression scripts change. No engine, replication, recovery-record, storage-format or HA configuration changes. Ordinary rollback assertions remain covered above. | No engine-domain safety claim. |

The two specialist targets were eight minutes each, with a six-minute checkpoint and twelve coordinator minutes reserved. Targets were not hard-enforced. Per-agent token usage is unknown. No reviewer dropout, continuation agent or extra specialist was used.

No changed path is unowned. Windows execution, crash/restart, forced descendant failure, and a live lockdb delay beyond the barrier deadline were not run. These are stated scope limits, not evidence of a newly introduced defect. Follow-up review is not required for a demonstrated blocking issue at this snapshot.
