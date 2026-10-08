# Ticket06: trigger outcomes with explicit OOS path limits

Date: 2026-10-08 (Asia/Seoul). Approved implementation ticket06 of [the developer regression specification](../spec.md). The public native contained SQL case passed with one exact executed case, 60 expected statement results, zero failures and zero skips. A fresh unchanged Ticket02 shell baseline also passed with one exact case and 21 successful assertions. Triggered writes receive logical credit only.

## Delivered behavior and independent model

Public worker `/home/vimkim/gh/cubrid-testcases/oos-06-triggers`, branch `task/oos-06-triggers`, starts at integration `5e25be4e2d1d471b1f1b3ea6736c970f8c323e34`. New public pair is `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql06_triggers.sql` with matching `answers/cbrd_26659_oos_sql06_triggers.answer`, initial behavior commit `4e294f7c4`; final tested code is `d477b8646`, which changes only comment compatibility. It follows existing cases/answers, deterministic EVALUATE groups, ordered SELECT results, explicit cleanup and JDBC answer conventions. P09 supplied the behavior structure; fixture and independent expected values were reconciled before runtime.

Private worker `/home/vimkim/gh/cubrid-testcases-private-ex/oos-06-triggers`, branch `task/oos-06-triggers`, is unchanged at `4de68fb31499ecb2dfeb42b14ece8d7e902cd448`. It reuses `shell/_40_guava/cbrd_26659_owner_drop/cases/cbrd_26659_owner_drop.sh` and its existing fixture/observer. No additional private testcase code is needed for this ticket. [Ticket02](02-shell-owner-drop.md) describes this separately executed physical baseline.

The pre-trigger row schema and VALUES/INSERT SELECT construction exactly match [Ticket01](01-sql-value-copy.md) and Ticket02: INT primary key, VARBIT payload/tag, four distinguishable head/middle/tail patterns. Sizes are safely away from the disputed demotion boundary.

| id | Payload byte segments | Payload octets | Initial tag bytes | Payload MD5 over lowercase hex text |
| --- | --- | ---: | --- | --- |
| 1 | aa×1000, bb×1000, cc×1000 | 3000 | 11×300 | `4d99190ee568772b70b0244abddbaa00` |
| 2 | d1×1401, e2×1403, f3×1403 | 4207 | 22×300 | `5a43433dc26414a3625551ee8fc23cd2` |
| 3 | 12×7001, 34×6501, 56×6501 | 20003 | 33×300 | `127967dc901ebb2776d754d2257cadf3` |
| 4 | 78×11001, 9a×11000, bc×11000 | 33001 | 44×300 | `ec5759eaa4472233734552dfd216c552` |

The independent model fixes the following nine phases. The answer is derived from literal row/event state and Python hashlib before execution; actual results never supply expected replacements.

| Phase | Independent expected result |
| --- | --- |
| TEST1 pre-trigger fixture | Four ordered exact values with full equality, lengths and literal payload/tag digests; initial payload total 60211 |
| TEST2 AFTER UPDATE log | Row2 tag 55 creates log seq1 with unchanged 4207-byte payload and exact post-image tag digest |
| TEST3 AFTER UPDATE mirror | Row2 tag 66 creates log seq2 and mirror seq1; exact values and post-image digests match |
| TEST4 BEFORE UPDATE rejection | Row2 attempted ff×5000 payload and tag 99 fail with `Error:-517`, `ER_TR_REJECTED` |
| TEST5 rejected state | Row2 retains original 4207-byte payload/tag 66; log remains two ordered rows and mirror remains one exact row |
| TEST6 valid neighbor | While rejection remains active for row 2, row 1 tag 77 succeeds; log seq3 and mirror seq2 |
| TEST7 valid same-row write | Drop rejection, replace row 2 with a1/b2/c3×1403 bytes=4209 and tag 88; log seq4 and mirror seq3; final four-row payload total 60213 and four distinct payloads |
| TEST8 triggered INSERT | Separate id5 receives original 4207-byte payload and tag 99; exact row and one INSERT log; logical credit only |
| TEST9 cleanup | Drop all remaining triggers and all six tables/helpers; catalog counts fixture_tables=0 and fixture_triggers=0 |

Log and mirror have their own AUTO_INCREMENT keys, so the case assumes no ordering between different trigger actions. Mirror stores event rows rather than imposing duplicate id uniqueness. Queries always order by id or seq. Rejection happens BEFORE any AFTER action, so it must consume no AFTER sequence or mirror event. Final ordered log identities are `(1,2,4207,55)`, `(2,2,4207,66)`, `(3,1,3000,77)`, `(4,2,4209,88)`; mirror identities are `(1,2,4207,66)`, `(2,1,3000,77)`, `(3,2,4209,88)`.

The final 4209-byte payload has independently computed MD5 `378483aa571a3c8e2f12265d34c992ec`; tag 88 MD5 is `697b5cd5ef35b9eeb62c82312669da8b`. Each event also checks the corresponding literal digests. Full equality catches incorrect payload/tag content, lengths catch truncation, and independent digests give a separately calculable oracle.

[Pre-runtime oracle](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket06/oracle-review.md), [independent values](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket06/independent-values.json) [offline derivation](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket06/build-fixture.py) and [coordinator review](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket06/root-oracle-review.md) retain the review inputs outside the repository.

## Source-qualified physical limits

Engine is pinned to `fb567a629cdb390fff920542173fa36f454c74a0`; no PR is associated with its local task branch. Matching triggers prevent server eligibility in [is_server_update_allowed](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/execute_statement.c:9615) and [is_server_insert_allowed](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/execute_statement.c:12446). Client UPDATE uses object templates at [dbt_edit_object](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/execute_statement.c:8075); client INSERT creates templates at [13309](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/execute_statement.c:13309). Locator flush calls [tf_mem_to_disk](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/transaction/locator_cl.c:4374), whose full-object serializer writes [put_varinfo/put_attributes](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/object/transform_cl.c:879). The server demotion planner is [heap_attrinfo_determine_disk_layout](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/heap_file.c:12800). This reconciles P09's historical path qualification at the current revision; source routing does not establish actual storage in an invocation.

All public triggered UPDATE/mirror INSERT/triggered INSERT claims are logical. Correct triggered values provide no OOS placement credit. The SQL case neither measures placement nor assumes an UPDATE preserves the original physical representation. DISK_SIZE and OCTET_LENGTH expose logical sizes and cannot prove demotion.

The private companion observes its own quiescent committed CS fixture, with the same four base row values constructed before any trigger. Its owner and survivor each require six OOS chunks and 57372 slot bytes: serialized 4212+20008+33008 plus six 24-byte chunk headers. The inline comparator requires no OOS file and zero chunks. SHOW class/VFID/HFID identity and diagdb owner descriptors must agree. These baseline observations are a separate execution; they do not observe public JDBC t_oos06 or any triggered write. [Ticket02](02-shell-owner-drop.md) documents its positive-file, DROP and survivor evidence and the same source-derived layout model.

## Validation, cleanup and cost

The first disposable negative attempt retained four malformed query fragments from this case's block header, with extra -493 syntax errors. Its XML shows the exact fragmentation. The matching [CTP SQLParser source](/home/vimkim/gh/ctp/run-sql/CTP/sql/src/com/navercorp/cubridqa/cqt/common/SQLParser.java:121) checks `line.endsWith(";")` outside PL/CSQL text and separately skips `--` comments; this header had such line-ending semicolons. This identifies the observed Ticket06 input failure, without claiming every semicolon inside a block comment fails. Final code uses supported `--` line comments; SQL and expected values are unchanged. An offline probe using the actual CQT jar now discovers exactly 60 statements with the first owned-table DROP. This is an input-format repair, with no runner or engine change.

Final-code negative a02 executes exactly one selected case, fails only the deliberately false copied final total 60214 versus actual 60213, and has zero skips. Actual 60 statement results are byte-identical to the independently reviewed original answer, including expected -517 rejection and catalog zero controls. Its helper exits1 even though runner exits0, demonstrating why process exit is insufficient. [Strict negative proof](/home/vimkim/tmp/oos306-sql06-a02/strict-proof.json) retains the exact identity, one failure and cleanup gates.

Clean SQL a03 passed the shared helper and [strict SQL proof](/home/vimkim/tmp/oos306-sql06-a03/strict-proof.json): exactly one executed identity, 60 statement results, no failures/skips, intended -517 and exact reviewed answer. The unchanged shell baseline passed the shared helper and [strict shell proof](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket06/attempt-04-shell-baseline/strict-proof.json): exactly one dispatched/finished identity, all 21 assertions OK, no failures/skips, positive named file/chunk/descriptor observations and owned cleanup. Each invocation uses exclusive validation.lock across copy/preparation, runtime, verification and cleanup; no database/timing invocations overlap. All attempts remain retained, including the initial invalid negative.

The selected public configuration is source-matching optdebug, company-compatible JDBC/16 KiB pages, normal logging/HA profile and approved 64 MiB initial DB/log volumes. Existing shell fixture remains 16 KiB, 20 MiB initial DB/log volumes, CS DML/SHOW plus offline SA diagnostics. Native explicit families, containment, one slot and TESTKIT_SLOT_VOLATILE unset are required. Original source/host workenv/shared install/CCI dirt remains outside attempt ownership.

Cleanup ownership is limited to fixture triggers/tables and the native attempt's disposable installation, registry, database, sessions/processes and runtime socket paths. SQL changes no parameters and leaves autocommit=true. The native runner tore down its owned basic DB after both failed answer comparisons; a01/a02/a03 cleanup receipts prove this. Shell's existing bounded EXIT cleanup and slot namespaces retain their own ownership boundaries. No new broad process/file cleanup is introduced.

The final SQL exact manifest path is `/home/vimkim/tmp/oos306-sql06-a03/testcases/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql06_triggers.sql`; native artifacts are under `/home/vimkim/tmp/oos306-sql06-a03/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_0819021838_11.5.0.2637-fb567a6`. The shell exact manifest path is `/home/vimkim/gh/cubrid-testcases-private-ex/oos-06-triggers/shell/_40_guava/cbrd_26659_owner_drop/cases/cbrd_26659_owner_drop.sh`; verdict artifacts are under `ticket06/attempt-04-shell-baseline/CTP/result/shell/current_runtime_logs/`, with raw testcase diagnostics under its adjacent `case-logs/_40_guava/cbrd_26659_owner_drop/cases/case/`. SQL result roots are taken only from each fresh runner marker; copied historical CTP artifacts are never verdict evidence.

| Input | Recorded identity |
| --- | --- |
| Public final tested commit | `d477b86466285ed328acecf468f4ab2b3df4d9a0` |
| Public final SQL SHA-256 | `e9bf18d7fe104b25e0153ae4be86c8b77849fa2b0d3ac3dd17ad72afa1efe97c` |
| Independently prepared answer SHA-256 | `6fc308b55abce6249d29f7448ecde2e67a7b4d47e4fd503337ca6c6e3668acdc` |
| Private baseline commit | `4de68fb31499ecb2dfeb42b14ece8d7e902cd448`, unchanged |
| Native runner SHA-256 | `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, `cubrid-testkit dev` |
| JDBC jar SHA-256 | `0f5e56c7eaed0ebeb1eba3a8bba5a5db513e7eec455498d268e2205d48c02576` |
| CTP assets | `9c62858b10005d721546cc007be260844033b9e9`; preexisting modified assets were recorded and copied |
| Java executor | Temurin8.0.462+8, javac1.8.0_462 |
| Source/install identity | Exact source `fb567a629`, `11.5.0.2637-fb567a6` OptDebug; preflight match, no mismatch exception |

The private observation again found owner class OID0/195/7, owner HFID897/1/896 (header/volume/file), OOS VFID1/1088; survivor class0/208/1, HFID1025/1/1024, VFID1/1152. Owner/survivor each had 6 chunks/57372 slot bytes, and survivor retained exactly the same SHOW state after owner DROP. The saved owner file/class/HFID disappeared from successful post-DROP diagdb; inline file remained absent. These volatile identities are retained joins for this attempt, not golden constants or triggered-placement evidence.

| Retained attempt | Outcome | Case seconds | Runner seconds | Copy/config preparation seconds | Preparation + locked preflight/runner/verify/cleanup seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| `/home/vimkim/tmp/oos306-sql06-a01` | Invalid negative control: specific block-header fragmentation; native fail1, cleanup passed | 0.215 | 94.479 | 1.059 | 96.061 |
| `/home/vimkim/tmp/oos306-sql06-a02` | Strict deliberate60214 expectation rejects actual60213 only; failure1/skip0 | 0.209 | 93.948 | 1.089 | 95.553 |
| `/home/vimkim/tmp/oos306-sql06-a03` | Clean public success1/failure0/skip0, all 60 results exact | 0.230 | 94.958 | 1.061 | 96.528 |
| `ticket06/attempt-04-shell-baseline` | Clean separate baseline success1/failure0/skip0, all 21 assertions OK | 12.878 | 14.345 | 1.038 | 15.759 |

The final SQL runner spent about 61 seconds preparing its normal JDBC database/assets and includes teardown; the 230ms native case time measures its statement body. Shell case time includes its init, fixture, observations, utilities and case cleanup; native feedback also records 13.151s around case dispatch/capture. Whole runner times include native setup and normal cleanup. Locked preflight/runner/verification/cleanup took 95.467s for clean SQL and 14.721s for shell; copying/configuration is listed separately and also included in the last column. Lock wait is excluded and unmeasured. Coordinator-owned shared build 129.45s is separate overhead. SQL/shell costs are not combined into a threshold or predicted company-CI timing. [Attempt summary](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket06/attempt-summary.json) retains exact measurements.

All three SQL attempts proved empty owned registry, deleted basic DB directory, no accessible process executable from their copied install, restored runtime parameters/configuration, final normal stop/deletion messages, and removed owned short socket directories after processes exited. Native locale preparation changed copied cubrid_locales.txt; the driver preserved the observed file and restored the copied original after cleanup gates passed. SQL TEST9 independently proved none of the six fixture tables or four fixture triggers remained. Shell passed five normal cleanup assertions and outer empty registry/database/slot-directory, unchanged testcase hashes, no accessible copied-install processes and restored disposable configuration. Shell outer deployment changes are retained separately before restoration; original shared install was never modified.

The failing a01/a02 receipts are preserved with cleanup; no timeout occurred. Host process scans record inaccessible/racing PIDs, so they establish attempt ownership cleanup and do not certify global host cleanliness. The reused shell case's failed/interrupt cleanup path and deliberate assertion rejection were already verified in [Ticket02](02-shell-owner-drop.md); Ticket06 adds no new shell fixture or cleanup code.

Focused checks passed: actual-CQT parser 60-statement discovery, independent MD5/event model and root review, shared native helpers plus strict SQL/shell receipt checks, `bash -n`, `shellcheck -S warning`, `testkit check-cases` (one shell case, zero ineffective/misspelled/self-comparison verdicts), and SQL-source/docs whitespace plus local-link checks. Golden answers deliberately retain the repository/JDBC renderer's trailing spaces and blank final result line; ordinary `git diff --check` flags those answer-only conventions. A command-scoped check ignores only blank-at-eol/blank-at-eof for the `.answer`; the tracked answer remains byte-identical to reviewed native output. All three worker branches merged their current authorized task-integration destination immediately before handoff; each was already up to date. Public/private workers are clean; docs contains only this committed durable report. Unrelated source CCI and preexisting CTP asset dirt remain preserved.

## Coverage delta for coordinator

Coordinator owns coverage.md and README updates; only this unique delivery document is authored by Ticket06. The new selected-set delta is one public SQL pair and zero new private cases: the existing Ticket02 baseline is reused.

| Coverage row | Delivered identifiers and intended result | Verified proof scope | Remaining disposition |
| --- | --- | --- | --- |
| R12 trigger subset; SQL 94.958s/230ms, separate shell 14.345s/12.878s | `cbrd_26659_oos_sql06_triggers` TEST1–9: ordered exact row/log/mirror state, -517 rejection, unchanged rejected values and subsequent valid writes, logical triggered INSERT, complete cleanup | Logical SQL trigger subset; separately rerun Ticket02 pre-trigger baseline supplies positive physical companion evidence only for its own fixture | Triggered placement, per-row chain/ownership/reuse, internal retry, recovery, reclaim and ordinary HA remain explicit gaps; constraints belong to Ticket05 |

No mandatory criterion remains unmet for this narrow ticket. Triggered placement is an explicit capability/conformance gap, not a missing passing assertion promised by this slice. No engine fix, push, JIRA publication or GHA occurred. A focused local pass does not certify the full company corpus, all OOS conformance or company CI.
