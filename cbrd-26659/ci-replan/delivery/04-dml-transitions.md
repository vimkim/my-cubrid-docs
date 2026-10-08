# Ticket04: UPDATE and DELETE state transitions

Date: 2026-10-08 (Asia/Seoul). Engine reference `fb567a629cdb390fff920542173fa36f454c74a0`; source branch `CBRD-26659-oos-testcases-handover` has no associated PR. Related integration PR is CUBRID/CUBRID #7990. This delivery implements [Ticket04](../tickets/04-dml-transitions.md), strengthening the recovered P05/P06 scenarios with complete row/column models and a separate physical companion.

## Delivered behavior and independent expectations

Public SQL `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql04_update.sql` checks 18 ordered states. Four target rows have distinct head/middle/tail VARBIT patterns and 300-byte tags; every snapshot checks every target payload/tag/note, including untouched survivors, against a separately maintained expected model. Fixed external MD5 answers and octet counts detect common truncation and row/column substitution. Sources 11/12 have distinct 5003/9001-byte payloads, separate expected values and independently fixed hashes; subquery/join UPDATE and later source DELETE preserve the intended targets.

The UPDATE phases include payload-predicate growth 4207→20003, shrink 20003→5103→3000, inline→large, integer-only assignment leaving OOS payload unassigned, explicit equal-value `payload=payload`, tag-only assignment leaving payload genuinely unassigned, NULL→empty→large, and three repeated writes 5001→6002→4207 with a full snapshot after each. Empty and NULL remain distinct: empty octets 0/MD5 `d41d8cd98f00b204e9800998ecf8427e`, NULL octet sentinel -1/digest sentinel `NULL`. No answer prescribes a new or reused head OOS OID.

Public `cbrd_26659_oos_sql04_delete.sql` checks 8 ordered states: initial four-row fixture; PK DELETE of ID2; OOS-value-predicate DELETE of ID3; reinsert both IDs without changing survivors; DELETE all and reinsert; TRUNCATE and reinsert. Exact IDs, all payload/tag/note values and row counts are checked at each phase. Default JDBC autocommit remains true, no session parameters change, and both cases require a final catalog count 0 for all owned tables.

The existing [public inventory](../public-sql-inventory.md) identifies P05/P06 as the reusable structures. The new cases remove the 50-write stress repetition and retain three discriminating writes with intermediate assertions. Their answers were derived before execution from the row model and `hashlib.md5(lowercase_hex.encode('ascii'))`; captured engine output was never promoted to a golden answer.

## Separate physical companion

Private case `shell/_40_guava/cbrd_26659_dml_transitions/cases/cbrd_26659_dml_transitions.sh` runs a separate quiescent 16 KiB standalone fixture under optdebug. The additional SA mode is needed because CS aggregate OOS statistics include old MVCC versions, obscuring the current value's inline/chunk state. Source [heap_oos.cpp:680](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/heap_oos.cpp:680) describes the non-MVCC eager path; it is distinct from JDBC CS lifetime behavior. CS MVCC DELETE retention remains the separate snapshot/lifetime requirement. This companion does not observe the actual public execution.

`setup.sql` uses INSERT SELECT for the large survivor; positive named OOS statistics are required before transition acceptance. Ordinary tables without triggers/views/meta-attribute assignments use the heap-writing query UPDATE route ([execute_statement.c:9597](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/execute_statement.c:9597)); workspace-built VALUES success does not establish activation. The CBRD-27424 workspace/SA-demotion gap remains separate.

For N≥32 payload bytes the serialized VARBIT size is `ALIGN(5+N,4)`. Current chunk headers are 24 bytes, and complete SHOW slot bytes are serialized bytes plus 24 per chunk. [Maximum chunk payload calculation](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/oos_file.cpp:3645) is based on aligned slotted-page record capacity minus the header. These fixtures avoid both current 4086 B and accepted 4060 B record-gate boundaries.

| Physical phase | Payload bytes | Chunks | Slot bytes | File |
| --- | ---: | ---: | ---: | --- |
| initial inline |3000|0|0|absent|
| first growth |4207|1|4236|present|
| growth to multiple |20003|2|20056|present|
| shrink to single |5103|1|5132|present|
| note-only / equal assignment |5103|1|5132|present|
| re-inline / NULL / empty |3000 / NULL /0|0|0|retained|
| regrow |20003|2|20056|present|
| DELETE |absent row|0|0|retained|

Every phase verifies all survivor columns and unchanged named SHOW state: 33001 B payload, 3 chunks, 33080 slot bytes. Positive states use the unchanged common observer. The scoped `oos_dml_empty.py` validates all 14 SHOW fields, saved class/heap/OOS identifiers, page size 16344, allocated file state and exactly zero current records/slot bytes. It does not weaken the shared observer or equate zero records with file/page reclamation. Final assertions remove the three owned tables; trap cleanup deletes only the owned database/fixture and restores configuration within the contained native slot.

## Validation evidence

Root independently approved all 26 states and source-derived physical sums before runtime, recorded in `/home/vimkim/tmp/oos-developer-regressions-20261008/root-oracle-review-ticket04.md` and `ticket04-root-independent-model.json`. Worker pre-runtime review record: `/home/vimkim/tmp/oos-developer-regressions-20261008/ticket04-oracle.md`; all 26 ordered expected states: `ticket04-logical-oracle.json`. External model/attempt scripts and raw receipts remain outside Git repositories.

Static checks passed: Bash syntax, shellcheck, Python compile and native `testkit check-cases` (one selected shell case; zero cannot-fail, misspelt-verdict or self-comparison findings). CQT answer trailing whitespace follows the existing native-rendered answer convention; SQL source whitespace checks exclude those intentional answer fields.

All four retained attempts below used source-matching optdebug `11.5.0.2637-fb567a6`, matching JDBC and Java `temurin-8.0.462+8`, explicit public/private worker roots, one contained native slot and `TESTKIT_SLOT_VOLATILE` unset. SQL is JDBC/16 KiB; shell is SA/16 KiB. Both explicitly use 64 MiB DB/log volumes. Testkit binary SHA-256 was `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`; CTP assets were revision `9c62858b10005d721546cc007be260844033b9e9` with pre-existing helper/config differences recorded in `identities.json`. Preflight confirmed installed/source commit match and available containment. Source's unrelated `m cubrid-cci` remained preserved.

| Retained attempt | Exact selected verdict | Case time | Whole runner | Preparation | Locked verification/cleanup |
| --- | --- | ---: | ---: | ---: | ---: |
| `/home/vimkim/tmp/oos306-sql04-red01` | UPDATE only; deliberate digest rejection, total 1/fail 1 | 0.297s | 93.097s | 1.116s | 93.622s |
| `/home/vimkim/tmp/oos306-sql04-clean01` | DELETE+UPDATE, total 2/success 2/fail 0 | 0.184s+0.208s | 86.074s | 1.174s | 86.580s |
| `/home/vimkim/tmp/oos306-sh04-red01` | one case; deliberate chunk rejection, fail 1/skip 0 | 15.854s | 17.297s | 2.145s | 17.699s |
| `/home/vimkim/tmp/oos306-sh04-clean01` | one case, success 1/fail 0/skip 0; all 59 assertions OK | 84.331s | 85.908s | 1.040s | 86.296s |

Timing starts after acquiring the exclusive `validation.lock`; copying/preparation, invocation and cleanup all hold that lock. Whole runner time includes native setup, fixture execution and normal cleanup. Copy/config preparation and post-run verification/cleanup are recorded separately; no new build was performed by this worker. SQL and shell remain separate measured costs without a hard cutoff or assumed company-CI speedup. Shell uses fresh SA invocations between quiescent phases, so its measured cost includes repeated database/session initialization; this preserves visibility and current-state diagnostics.

Both negative controls changed only attempt copies. The SQL actual-result diff contains exactly the deliberately false first payload digest; every other modeled state and final fixture cleanup matched. Shell positively observed survivor 3/33080 and first growth actual 1/4236 before the deliberately incorrect expected 2 failed with `wrong Oos_num_recs`. In both, runner exit 0 was correctly rejected by the strict artifact helper. Neither negative failure reflects an engine defect or changed golden.

Clean SQL result root is `/home/vimkim/tmp/oos306-sql04-clean01/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_0819055073_11.5.0.2637-fb567a6`. `verify.log` confirms exact positive identities, complete `summary_info`, `main.info`, XML and both `.result` files. Ordered answers verify all 26 expected states; both final fixture catalog counts are 0. Shell result root is `/home/vimkim/tmp/oos306-sh04-clean01/CTP/result/shell/current_runtime_logs`; `test_status.data`, feedback, environment logs and XML establish exact one dispatched/finished case with no failures/skips. Retained case logs include every named physical JSON/SHOW/value phase, scoped empty-file states and the complete 59-OK assertion result. Mandatory phase/cleanup tokens were checked separately by the driver.

All four `cleanup.json` receipts prove no accessible attempt-install processes, empty registry/database/slot state as applicable and restored copied configuration. SQL additionally proves normal final server-stop/database-delete messages and the attempt TMP removed after retaining its contents; the native locale preparation file was restored separately and recorded. Shell proves source testcase hashes unchanged, explicit owned database/registry/fixture deletion and restored case configuration. Failed assertions triggered the same owned cleanup path; no timeout occurred. Terminating command deadlines include a 5-second forced-kill grace, and the native slot owns any descendant cleanup. No cleanup touches other host databases/processes.

Raw attempts, external model/driver scripts and receipts are intentionally not committed. The lasting delivery document records their identities, verdicts, timings and proof limits. Tested public tip `6dce621cc59453666bbc1b7b644c35ad92321ea3` and private tip `992cf93bc02d1221ee9cfcc82cc2de20aee75929` retain frozen source/answer/helper hashes in the attempt manifests.

## Coverage limits and integration delta

R09 gains exact public UPDATE/DELETE logical states plus separately qualified SA current-state transitions. R01/R05 receive only incidental fixture premises; this ticket does not replace the representation/chunk-boundary ticket. R21 remains **accepted implementation gap**: CBRD-27230 is Open/Unresolved, and exact source [recovery.h:206](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/transaction/recovery.h:206) reserves `RVOOS_NOTIFY_VACUUM` without an emitter. Immediate successful DML gets no reuse, commit-notification, ownership-lifetime, vacuum or page-reclaim credit. R19 snapshots, R20 rollback-after-vacuum and R24 reclamation remain separate work.

Worker branches: public `task/oos-04-dml` (base 5e25be4e2), private `task/oos-04-dml-shell` (base 4de68fb31), docs `docs/oos-04-dml` (base ed0a89f). Root/merger owns shared coverage/index edits; task integration is authorized, while main/develop merge requires the user's approval. No engine changes, push, JIRA publication or GHA run are included.

Before handoff, all three workers merged the current task integration refs (`5e25be4e2`, `4de68fb31`, `ed0a89f`); each was already included, so no runtime-affecting merge change occurred. Final focused source/answer/helper hashes match the tested manifests; public/private workers are clean. Shared R09 coverage and README indexing are explicitly delegated to root/merger.
