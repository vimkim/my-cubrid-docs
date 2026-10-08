# Ticket 14 complete local SQL and shell validation

Date: 2026-10-08 (Asia/Seoul). Parent CBRD-26659; source branch has no PR (`gh-pr-info`). Approved [spec](../spec.md), [coverage](../coverage.md) and [local workflow](../local-validation.md) govern this receipt.

**Current qualification:** retained unchanged SQL16/16 at public `c94961578dc43bfe05a74591d52dff30d44a43d3` remains 88.523774s; fresh corrected shell14/14 at private `f5fc1fa815fbc6eec71135f506e377c0b1096da3` passes in **316.414065s**, zero failures/skips, 336 assertions, 941 mandatory artifacts and all verdict/proof/cleanup gates0. The separate Standards/Spec findings are independently closed. [Current post-review qualification](#current-post-review-qualification) and the [correction report](final-review-cleanup.md) identify the accepted revision and evidence. All original report content below through “Immutable evidence and handoff” records the **initial qualification at private f16dd0ba9**: initial shell304.532742s, 71 inputs and 936 requirements. Its original tables, hash identities and scope statements are retained as revision-specific initial evidence.

The complete reviewed passing selection succeeds in two fresh, separate native contained invocations: **SQL 16/16, 88.523774s whole; shell 14/14, 304.532742s whole**, both **zero failures/skips**. Every selected SQL result matches its independently reviewed answer byte for byte. Shell verifies **336 mandatory behavior/cleanup assertions**, all **936 frozen required artifact entries**, and **1,229 actual retained raw files**, including dynamic controller/command/drain journals. Native verdict, required proof and cleanup gates all return 0. These are completed supported subsets; the report preserves all 31 behavior dispositions and makes no full engine-requirement or company-corpus qualification.

No testcase, answer, helper or engine source was changed. Root approved the complete frozen model/phase/artifact/cleanup plan and drivers before execution in [root-oracle-review-ticket14.md](/home/vimkim/tmp/oos-developer-regressions-20261008/root-oracle-review-ticket14.md). Its separate post-run [immutable artifact audit](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/root-final-artifact-audit.json), under the same exclusive validation lock, independently confirms 16 exact result/answer identities, 1,229 shell hashes, 78 retained proof-source hashes per attempt, 936 requirements, 336 assertions and all 71 integrated input hashes.

## Revisions, dependencies and preservation

| Component | Exact identity / configuration |
| --- | --- |
| Read-only engine checkout | `/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover`; branch `CBRD-26659-oos-testcases-handover`; `fb567a629cdb390fff920542173fa36f454c74a0` |
| Read-only public integration | `/home/vimkim/gh/cubrid-testcases/oos-regressions-integration`; branch `task/oos-regressions-public`; `c94961578dc43bfe05a74591d52dff30d44a43d3` |
| Read-only private integration | `/home/vimkim/gh/cubrid-testcases-private-ex/oos-regressions-integration`; branch `task/oos-regressions-shell`; `f16dd0ba9d041cbe6c1d4486feb78108262dd2e5` |
| Docs worker / starting integration | `/home/vimkim/gh/my-cubrid-docs-oos-14-local-validation`; branch `task/oos-14-local-validation`; from `docs/oos-developer-regressions` at `048b726aa304572a1834173b6995263ffce9c9ab` |
| Optdebug installation | `/home/vimkim/.cub/install/CBRD-26659-oos-testcases-handover/optdebug`; `cubrid_rel` `11.5.0.2637-fb567a6`; copied separately for each attempt |
| CCI / JDBC / manager pins | CCI `79d0888c26a2543d31f53eb7b6c9738db110fff4`; JDBC `71d7dfeef93eb788f8b03b7bd21a9e4974a7a7c0`; manager `83655ae2c174226c296637abd219389c705440f1` uninitialized |
| Matching installed JDBC | SHA-256 `0f5e56c7eaed0ebeb1eba3a8bba5a5db513e7eec455498d268e2205d48c02576` |
| Java | `/home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8`; javac 1.8.0_462 |
| CTP assets | `/home/vimkim/gh/ctp/run-sql/CTP`; HEAD `9c62858b10005d721546cc007be260844033b9e9`; pre-existing modifications retained |
| Native runner | `/home/vimkim/.local/bin/testkit`; SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`; dev; build revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified=true |

[Installed identity](/home/vimkim/tmp/oos-developer-regressions-20261008/install-identity.json), [pre-runtime dependency/preserved-byte baseline](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/dependency-identity-before.json) and [final identities](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/final-identity-and-artifacts.json) retain critical installed executable/library/JDBC checksums, exact submodules, native build metadata and five modified CTP file hashes. Each invocation checks them before runtime and after cleanup, including copied-install critical bytes. All 71 reviewed fixture/answer/helper/model bytes remain unchanged:32 public and 39 private. Each unchanged case matches its prior accepted receipt's source hashes and retains every independent pre-runtime review pointer in `frozen-contract.json`, including Ticket 03 representation/chunk/VOT reviews and Ticket 10 initial value/recovery, final delta and stop-correction reviews.

Original unrelated source `cubrid-cci/win/cci_version.h` and `.env` hashes stay equal to the baseline; source status ends solely ` m cubrid-cci`. Public remains clean; private retains only its original untracked `.ropeproject/autoimport.db`. Existing host Debug/`debug_gcc` and workenv were not switched. No install preparation, rebuild, runner update, downloads, publication, GHA, engine fix or local destination merge occurred.

## Frozen selection, models and profiles

| Frozen input/proof | SHA-256 |
| --- | --- |
| [sql-manifest.txt](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/sql-manifest.txt) | `3ff3db125347203ab4e9b5a17b20398e9bfa774419545814a41b89893d90f4b1` |
| [shell-manifest.txt](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/shell-manifest.txt) | `4164efaaf064f1e1654990642595c7bea47491e115512c9d235c65b4bfb14a79` |
| [frozen-contract.json](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/frozen-contract.json) | `0c8e4bc405cca0610c154e5e63ff8ee16308ea3f99b032e30daf4ad06f709219` |
| [verify.py](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/verify.py) | `8f0cca3243a4b6e1bf85c75aaaafd6fbb9b74a353e0b155891498c4a6c275349` |
| [native-sql14-attempt.py](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/native-sql14-attempt.py) | `ce5e8ddec4f12bd575c13af3ee3c528ea7864aa560f64ca05a2e0194d0cf4f8f` |
| [native-shell14-attempt.py](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/native-shell14-attempt.py) | `ae56e83ffdd8ad4419279f6f87580baf8ea9f17a4d77be5109d17da995f71d1c` |
| [dependency-identity-before.json](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/dependency-identity-before.json) | `c367c142893ed2bbcc60861b040f18bbfb40575a9f0d6088e3abb1f2ef407de2` |
| [freeze.py](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/freeze.py) | `fa5f128cadc30a6b4e10a3d90a4f3da6f375528b7d03253ef6c9e4f218672202` |

The freeze is independently source-derived. Historical positive logs supply artifact retention mechanics and source-emitted phase-label schema; actual values never supply an expected answer. The [compact oracle](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/oracle-review.md), [contract](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/frozen-contract.json), captured `frozen-inputs`, [offline rejecting controls](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/offline-red-proof.json) and root's approval preserve that ordering. The offline schema check passes 14 cases/336 assertions; removing a required owner SHOW file or changing intended 6 chunks to 7 rejects. Restoring the unchanged archived artifact passes.

SQL uses copied cases/answers and fixture siblings under `/home/vimkim/tmp/oos306-sql14-a01/testcases`; its exact absolute [scenario selection](/home/vimkim/tmp/oos306-sql14-a01/expected-cases.txt) equals the 16-entry frozen list. The correct 17th full partition SQL remains tracked outside the green selection. Native JDBC `test_default.xml`, autocommit=true, company HA configuration, test_mode=yes, charset en_US, 16KiB database/log pages and 64MiB database/log volumes are explicitly retained in [prepared sql.conf](/home/vimkim/tmp/oos306-sql14-a01/conf/sql.conf). No mode/page matrix is inferred.

Shell uses the 14 exact tracked same-name scripts below through a contained read-only disk overlay of the private corpus. It runs CS except qualified quiescent DML SA, TDE SA phases and offline SA diagnostics/checkdb. All use 16KiB DB/log pages; DB/log volumes are 64MiB except the unchanged owner_drop/representation fixtures use 20MiB. Case recovery/vacuum/utility/TDE parameters remain their approved literals. [Prepared shell.conf](/home/vimkim/tmp/oos306-sh14-a01/conf/shell.conf) retains scenario_disk=on, one slot, retry/update/continuation off, file feedback, `case_logs=all`/64MiB and the sorted exact list. The copied whole-corpus `LINUX_NOT_SUPPORTED` macro filter is explicitly cleared for this reviewed selection; none of its cases carries an unsupported macro, and actual skip counts are 0.

Both invocations bind explicit source/public/private/install/CTP/Java roots in their [SQL environment](/home/vimkim/tmp/oos306-sql14-a01/environment.json) and [shell environment](/home/vimkim/tmp/oos306-sh14-a01/environment.json), set `TESTKIT_NATIVE` to the selected family and `TESTKIT_CONTAIN=1`, and leave `TESTKIT_SLOT_VOLATILE` unset. Both [SQL preflight](/home/vimkim/tmp/oos306-sql14-a01/preflight.log) and [shell preflight](/home/vimkim/tmp/oos306-sh14-a01/preflight.log) prove exact installed/source match without an exception and available native containment. The exclusive `validation.lock` is held before preparation/copy until native result checks, required artifact/model checks and cleanup complete. SQL and shell run serially; there is one invocation for each, no retry or fallback.

## Exact SQL results and timings

| Exact filename under `sql/_36_guava/cbrd_26659/cases/` | Ticket/model provenance | Body seconds | Verdict |
| --- | --- | ---: | --- |
| `cbrd_26659_oos_chunk_boundaries.sql` | [03](03-representation-chunks.md) | 0.102 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_partition_routing.sql` | [08](08-schema-storage.md) | 0.035 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_representation.sql` | [03](03-representation-chunks.md) | 0.061 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_schema.sql` | [08](08-schema-storage.md) | 0.136 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql01_insert_select.sql` | [01](01-sql-value-copy.md) | 0.075 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql04_delete.sql` | [04](04-dml-transitions.md) | 0.125 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql04_update.sql` | [04](04-dml-transitions.md) | 0.177 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql05_bigone.sql` | [05](05-transactions-errors.md) | 0.054 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql05_constraints.sql` | [05](05-transactions-errors.md) | 0.129 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql05_transactions.sql` | [05](05-transactions-errors.md) | 0.062 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql06_triggers.sql` | [06](06-triggers.md) | 0.139 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql07_read_paths.sql` | [07](07-read-paths.md) | 0.086 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql09_lob_copy.sql` | [09](09-lob-locators.md) | 0.068 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_sql09_lob_maxcols.sql` | [09](09-lob-locators.md) | 0.904 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_storage_policy.sql` | [08](08-schema-storage.md) | 0.094 | PASS / unchanged reviewed answer |
| `cbrd_26659_oos_vot_many_attributes.sql` | [03](03-representation-chunks.md) | 0.055 | PASS / unchanged reviewed answer |

All 16 `.result` files byte-match the captured pre-reviewed `.answer` files, including intended error blocks and final cleanup catalog queries. [Native verification](/home/vimkim/tmp/oos306-sql14-a01/verify.log), the current result root's [summary.xml](/home/vimkim/tmp/oos306-sql14-a01/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_0821591611_11.5.0.2637-fb567a6/summary.xml), [JUnit](/home/vimkim/tmp/oos306-sql14-a01/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_0821591611_11.5.0.2637-fb567a6/linux_sql_64bit.xml) and [required-proof.json](/home/vimkim/tmp/oos306-sql14-a01/required-proof.json) prove exactly 16 completed positive identities, success 16/fail 0/skip 0. Copied case/answer hashes and original source hashes remain fixed. Body timers total **2.302s**, as reported by this JUnit/summary; they exclude global native setup/normal teardown.

## Exact shell results, raw models and timings

Every case below has a passing native status, every numbered assertion 1..N is present and OK, and every exact reviewed behavior/cleanup phase is present. Full per-case reparse results, raw-file SHA-256 maps and timing receipts are under [required-proof](/home/vimkim/tmp/oos306-sh14-a01/required-proof). The ordered [actual manifest](/home/vimkim/tmp/oos306-sh14-a01/expected-cases.txt), [native verification](/home/vimkim/tmp/oos306-sh14-a01/verify.log), `test_status.data`, full feedback/environment and [JUnit](/home/vimkim/tmp/oos306-sh14-a01/CTP/result/shell/current_runtime_logs/test-shell.xml) independently prove 14 success/0fail/0skip with no missing or extra dispatch/finish identities.

| Exact stem under `shell/_40_guava/<stem>/cases/<stem>.sh` | Native case seconds | Wrapper seconds | OK assertions | Retained raw files |
| --- | ---: | ---: | ---: | ---: |
| `cbrd_26659_backup_restore` | 23.216937 | 22.982277 | 11 | 81 |
| `cbrd_26659_crash_committed` | 12.658282 | 12.401596 | 10 | 52 |
| `cbrd_26659_crash_undo` | 12.336038 | 12.078367 | 10 | 51 |
| `cbrd_26659_dml_transitions` | 80.933456 | 80.679108 | 59 | 108 |
| `cbrd_26659_lob_locators` | 12.986079 | 12.741450 | 21 | 50 |
| `cbrd_26659_owner_drop` | 12.784528 | 12.532932 | 21 | 37 |
| `cbrd_26659_read_paths` | 13.020951 | 12.762516 | 19 | 44 |
| `cbrd_26659_representation_chunks` | 11.105654 | 10.855653 | 46 | 136 |
| `cbrd_26659_schema_policy` | 10.362771 | 10.109781 | 54 | 132 |
| `cbrd_26659_snapshot_visibility` | 10.214202 | 9.964608 | 9 | 107 |
| `cbrd_26659_tde_wal` | 17.313382 | 17.055431 | 30 | 85 |
| `cbrd_26659_transactions` | 7.744591 | 7.481968 | 12 | 32 |
| `cbrd_26659_utility_cs` | 36.743196 | 36.495536 | 17 | 156 |
| `cbrd_26659_utility_sa` | 39.970946 | 39.689318 | 17 | 158 |

Native case timers total **301.391011961s** and include per-case setup, body and normal teardown. Wrapper timers are independently recorded by each unchanged testcase and have a narrower boundary inside native startup/teardown. These totals are not SQL body time. The utility and snapshot controllers additionally retain:

| Case | Controller seconds | Command seconds sum |
| --- | ---: | ---: |
| `cbrd_26659_backup_restore` | 22.565932 | 21.488626 |
| `cbrd_26659_snapshot_visibility` | 9.307142 | Not separately sampled |
| `cbrd_26659_utility_cs` | 36.058956 | 35.903545 |
| `cbrd_26659_utility_sa` | 39.266169 | 39.111871 |

The following unchanged pre-reviewed semantic gates were reparsed from the final raw artifacts; all pass. Counts are OOS chunk records/slot bytes, distinct from logical row counts and allocated pages.

| Shell case suffix | OK count | Mandatory source-derived phase/physical model and raw evidence |
| --- | ---: | --- |
|backup_restore|11|Acknowledged/restored exact 2 rows/37208 bytes/schema/default;4/37316; owner equality; full backup header/primary+active-log completion; destructive engine-directory/backup manifest; retained external LOB 22/21-byte hashes; all command statuses 0 and inner cleanup.|
|crash_committed|10|Initial 5/56528, workload/recovered 9/97832; schema/baseline/workload commit ACKs; real server/master SIGKILL wait=-9; recovery ACK and positive typed RVOOS_INSERT REDO; full intended committed model, owner joins/checkdb; all utility groups/process cleanup. Initial value/recovery review and later stop correction reviews retained.|
|crash_undo|10|Initial/recovered 5/56528, acknowledged pending 9/97832; live autocommit-off session and independent flush-fence commit ACK; SIGKILL and positive typed RVOOS_INSERT REDO and UNDO; recovered exact pre-images/absent inserted row; owned utility/session/process cleanup. Typed traces are reported from actual journals, with no DELETE attribution inferred.|
|dml_transitions|59|Quiescent SA 0/1/2 current chunks with 4236/20056/5132; saved empty file after re-inline/NULL/empty/delete; untouched survivor 3/33080 at all ten transitions; all row columns and catalog 0.|
|lob_locators|21|Only two eligible FORCE_OUTLINE locator variables; source/copy independently recomputed packed URI/class serialization and 2 chunks; six distinct independently hashed external files; source destruction/copy survival; owner DROP/survivor joins; checkdb 0 and owned DB/LOB/input cleanup.|
|owner_drop|21|Inline 0/0/0; positive owner/survivor 6/57372; exact four-row full values/digests; saved class/VFID/HFID removal after DROP; survivor exact state; fresh checkdb status/log; owned process/database/registry/fixture/config cleanup.|
|read_paths|19|Twelve exact ordered read models and four required scan plans; inline 0, source/copy 6/57372; source DROP/copy full survivor; successful diagnostic ownership and removed descriptors; checkdb status/log; catalog 0.|
|representation_chunks|46|20 independently modeled logical receipts and 40 SHOW samples; two equal quiescent states per phase; chunks/bytes from approved source JSON models; checkdb and cleanup.|
|schema_policy|54|Literal source fields/DDL parsers; DEFAULT 1/3532, PREFER 1/2532, fallback 2/6064, forced 1/332, floor 1/52; nonretroactive 0→write 1/332; schema 2/9664; literal default added inline→UPDATE 1/3032; eight owner joins and actual intended rejected ALTER.|
|snapshot_visibility|9|Nine real-session ACKs, exact A/D/S old reads during/after writer commit, new N/S;6/57372→9/90452→stable 4/37316; at least three retained full-value survivor reads, each raw SHOW reparsed against 4/37316, last three identical; actual log eligibility/daemon completion; full process/session/group/config/registry/fixture cleanup; page_reclaim_credit=false.|
|tde_wal|30|Inline controls and effective owned-key/AES/hidden logging parameters; lazy AES/existing NONE 3/24292; full file headers owner joins; actual user-chunk DELETE 2/INSERT 3 encrypted flags; lazy graceful reopen 4/37316, existing 3/24292; identity unchanged and owned keystore cleanup. Existing-file NONE→AES and ciphertext/crash/HA receive zero credit.|
|transactions|12|Constraint baseline 3/24292, ordinary bigone 0, legal residual 1/1032; strict ten transaction result blocks include baseline 3/24292 and live writer 8/80428 plus eight full value phases; catalog 0 and cleanup.|
|utility_cs|17|Source/source-after-unload/loaded/compacted/source-final exact 2 rows/schema/default and 4/37316; owner joins/checkdb each; unload indexes/schema/objects, load/compact completion; independently hashed explicit external LOB transfer; every retained command status 0; effective auto_restart_server=no and owned cleanup.|
|utility_sa|17|Same full logical/schema round trip; source positive 4/37316; loaded/compacted logical qualification records actual 0 or 4 chunks without prescribing failure; no physical destination/WAL/no-logging stamp credit; explicit LOB transfer and cleanup.|

Final observed recovery traces are committed INSERT REDO 4/UNDO 0 and undo INSERT REDO 4/UNDO 4; positive typed insertion trace gates pass, with no DELETE-replay attribution. Snapshot retains at least three full N/S survivor reads with corresponding raw SHOW samples reparsed as 4/37316 and unchanged owner; the last three states are identical. Its actual daemon-completion/eligibility sample reports first-unvacuumed page 184 beyond mutation page 178, but pages stay 9→9 and `page_reclaim_credit=false`. The final SA utility loaded/compacted destination remains inline 0/0; its exact logical/schema pass earns zero destination-placement credit. TDE existing-file application and ciphertext flags remain false in its required proof.

Every retained utility command has a zero status and its actual raw output/input where applicable; csql `-i` means SQL input, while loaddb `-i` is the indexes file. Backup proof requires completed primary volume and active log, full/16KiB/active-log header, nonempty inventory, actual owned volume/log destruction, restored exact values/schema/owner and retained external LOB hashes. External payloads were preserved, so their independent backup/restoration is untested.

## Whole invocation and overhead

| Measured boundary | SQL seconds | Shell seconds |
| --- | ---: | ---: |
| Preparation/copy before native launch | 2.581152 | 2.423132 |
| Whole native launch through normal runner teardown | 88.523774 | 304.532742 |
| SQL body sum / shell native case sum | 2.302000 | 301.391012 |
| Native global setup/teardown/dispatch remainder | 86.221774 | 3.141730 |
| Preflight, native verification and outer cleanup remainder | 0.532744 | 0.433462 |
| Mandatory retained model/artifact proof | 2.854042 | 11.096283 |
| Locked invocation including verification/cleanup | 91.910559 | 316.062486 |

Unrounded [SQL measurements](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/sql14-measurements.json) and [shell measurements](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/shell14-measurements.json) derive from original runner/preparation/invocation/JUnit receipts. Root's earlier shared optdebug build **129.45s** is separate. Ticket 14 build/download overhead is 0; static/freeze/review work is outside runtime and was not separately wall-timed. Later immutable audit overhead is also outside these receipts. Roughly ten minutes per suite is informal guidance; each complete selected suite is measured separately, with no combined/hard gate or company-CI extrapolation.

SQL's 86.221774s global setup/teardown remainder dominates its 2.302s body. One complete 16-case invocation amortizes that existing setup without altering fixture semantics. Shell's longest DML case 80.933456s preserves repeated fresh SA startup/observation phases: consolidating them would change quiescent current-chain visibility and lose the reviewed 59-assertion model. CS/SA utility native cases 36.743196s/39.970946s and backup 23.216937s include real unload/load/compact/destructive-restore commands and repeated successful offline ownership/checkdb phases; controller command timing records the cost. The approved compact fixtures and shared controllers already remove bulk/redundant payload levels. No new speed optimization traded away complete values, phase diagnostics or cleanup.

## Cleanup and retained failure history

Both attempts have `exit.status=0`, `verify.exit=0`, `cleanup.exit=0` and `required-proof.exit=0`. Inner shell cleanup requires every case's source-emitted successful teardown assertion and relevant process/session/group/controller predicates. Outer [SQL cleanup](/home/vimkim/tmp/oos306-sql14-a01/cleanup.json) proves final normal stop/delete messages after the result marker, no accessible copied-install processes, empty registry/absent basic database, restored runtime configuration, separately preserved/restored locale preparation changes and relocated retained runtime TMP. Outer [shell cleanup](/home/vimkim/tmp/oos306-sh14-a01/cleanup.json) proves no accessible copied-install process, empty registry/database/slot roots, every copied configuration restored and unchanged testcase/dependency hashes. Retained source/controller artifacts also prove owned fixtures, inputs, LOB roots, backups/unload roots, keystore and registrations absent as applicable. Inaccessible/racing unrelated host PIDs are recorded and excluded from owned-process claims.

The clean final selections do not repeat deliberate failure/timeout controls. Relevant rejected or timeout history remains in the individual [01](01-sql-value-copy.md), [02](02-shell-owner-drop.md), [03](03-representation-chunks.md), [04](04-dml-transitions.md), [05](05-transactions-errors.md), [06](06-triggers.md), [07](07-read-paths.md), [08](08-schema-storage.md), [09](09-lob-locators.md), [10](10-crash-recovery.md), [11](11-snapshots-reclaim.md), [12](12-utility-roundtrips.md) and [13](13-tde-wal.md) reports. Wrong answers/counts/value tails/models/metadata reject in independent copies; failed prerequisites stop dependent phases. Normal/failure cleanup and bounded timeout/group/session controls retain their exact historical exercised scope, separate from this final pass.

Ticket 11 `abort01` retains sourcehash-after=false and no captured executed-overlay controller hash. Git reconstruction is labelled reconstruction and grants no verified rollback-after-vacuum safety credit. Ticket 12 `clean07` original driver cleanup/token rejection and failed supplemental-v1 loaddb-index interpretation remain unchanged; reviewed v2 reparses immutable artifacts and passes without rewriting receipts or unnecessary runtime repetition. Ticket 14 uses actual source literal phases and correct option semantics. Ticket 10 failed stop/session receipts remain distinct from the accepted source's positive interruption control. Ticket 13 criterion 2 existing-file NONE→AES remains OPEN/UNVERIFIED, irrespective of its supported lazy-file pass.

The Ticket 14 offline transaction parser initially wrote ten relative segment logs into the engine cwd. Each was proven byte-identical to the archived transaction output segment, moved outside the engine and retained in [correction receipt](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/parser-cwd-correction/receipt.json). The parser now runs in its external per-case proof directory; the offline CLI runs externally. Engine status returned to solely the original CCI dirt before runtime approval. This containment correction changes no source or product expectation, and final proof outputs are external.

## Company conventions and scope

Static discovery/answer/helper/configuration audit and complete native dispatch agree: public `cases/*.sql` map to same-stem `answers/*.answer`, deterministic query/model ordering and explicit final cleanup; private same-name `<family>/cases/<family>.sh` use `init_path/init.sh`, standard verdict helpers, retained `.result`/logs and owned EXIT/controller cleanup. Shared observers/controllers are existing tracked dependencies and match accepted hashes. `bash -n` for 14 scripts and selected Python/orchestration AST checks pass. [Native check-cases receipt](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/static-checks.json) reads all 14 against 145 standard helpers/37 failure-capable: cannot-fail 0, misspelt-verdict 0, self-comparison 0. An earlier unsupported `check-cases --help` probe was interpreted as a path and returned 255; the documented positional audit passed. It was source-only and supplied no product-runtime evidence.

The frozen independent SQL answers, exact native copied scenario and full results qualify this selection. The documented native multiline-comment/statement-splitting limit remains relevant to future SQL; no invalid/truncated statement fragments appear in these complete results. CTP is a specific locally modified asset checkout and the native runner is a modified dev binary, both exactly pinned above. No legacy CTP execution/fallback or GHA comparison was performed, so the result does not prove equivalence for the full company corpus, unselected macro families, arbitrary modes/pages or other runner builds.

## All 31 coverage dispositions

Case keys abbreviate the exact manifests/tables above; repeated row references share the measured full invocation, not an invented independent row timer. Logical public SQL and separate paired-shell physical proof remain distinct. Rows with no selected proof stay unmeasured/unverified. Existing negative/capability/deferred dispositions remain visible.

| ID / behavior | Final selected case keys | Truthful final disposition |
| --- | --- | --- |
| R01 Basic insert/read and copy | `sql01_insert_select; owner_drop` | Verified logical SQL and separate physical companion: full four-row copy/source destruction, 6/57372 owner/survivor and DROP. JDBC placement, per-row chain identity/retry/reclaim unverified. |
| R02 Largest-first and inline comparator | `representation; representation_chunks` | Verified logical and separate physical largest/inline/twelve-attribute subset (1/3032 and 6/4200); no tie-order claim. |
| R03 Record target and profitability floor | `representation; representation_chunks; schema_policy` | Verified strict profitable-floor subset only (at/below 24B inline;28B creates 1/52). Correct 4060/4064 ordinary-target candidate still fails under 4086 target, outside green. |
| R04 NULL/empty, many attributes and VOT widths | `representation; vot_many_attributes; representation_chunks` | Verified values and separate physical neighbor/many-attribute demotion subset; binary VOT-width introspection unverified. |
| R05 Single/multiple chunks and boundaries | `chunk_boundaries; representation_chunks` | Verified full boundary/copy/update values and separate fresh-heap initial chunks from 16280B capacity/24B headers. Physical UPDATE reuse/stub identity/retry/reclaim unverified. |
| R06 Storage policies and DDL | `storage_policy; schema_policy` | Verified accepted variable/fixed/shared/class/view matrix, largest/protection/fallback/forced/floor placement, nonretroactive ALTER then explicit write. FORCE_INLINE/fixed DEFAULT proposals, actual JDBC placement/lifetime/recovery/HA unverified. |
| R07 Mixed types/compression-sensitive values | `representation; read_paths; representation_chunks; read_paths(shell)` | Verified relevant uncompressed VARBIT/VARCHAR and mixed scalar interactions; broader types/compression-sensitive activation unverified. |
| R08 External BLOB/CLOB locators | `sql09_lob_copy; lob_locators` | Verified logical contents and separate FORCE_OUTLINE locator-only 2-column server copy route, independent serialized URI/class model, six distinct external files, source destruction and surviving copy/owner. JDBC/workspace placement, size-drift/lifetime/recovery/HA unverified. |
| R09 UPDATE/DELETE transitions | `sql04_update; sql04_delete; dml_transitions` | Verified full logical U01–18/D01–8 and separate quiescent SA 0/1/2 current chunks; saved empty file and untouched 3/33080 survivor. CS MVCC/JDBC placement/reclaim/reuse/notification unverified. |
| R10 Transactions and failed-DML atomicity | `sql05_transactions; sql05_constraints; transactions` | Verified immediate commit/rollback/savepoint/statement atomicity and separate CS 3/24292 baseline/8/80428 live writer; no post-vacuum safety/lifetime claim. |
| R11 Bigone rejection/legal neighbors | `sql05_bigone; sql09_lob_maxcols; transactions` | Verified revision-bound -1384 atomic rejection, legal ordinary/residual and qualified 1000-locator rejection/sparse compatibility. Locator-heavy activation/orphan-chain/internal-fault coverage unverified. |
| R12 Constraints and triggers | `sql05_constraints; sql06_triggers; transactions; owner_drop` | Verified exact -670/-631/-975/-495/-517 logical atomicity/trigger effects and separate positive baselines. Table CHECK unsupported; triggered placement/JDBC failed-write ownership/recovery unverified. |
| R13 Relational heap/index read paths | `sql07_read_paths; read_paths` | Verified full ordered read models and separate four scan plans, 6/57372 owners/source DROP/copy. Actual JDBC plans/per-row identity/raw-fetch/retry/recovery unverified. |
| R14 Schema evolution and rewrites | `schema; schema_policy` | Verified supported exact DDL/surviving values, 2/9664 saved owner and explicit write-induced 1/3032; ALTER-alone default stays inline. Post-MVCC live chains, binary identity/reuse/reclaim/recovery unverified. |
| R15 Partition routing/movement/ownership | `partition_routing` | Verified creation/routing/read/duplicate logical subset only. Correct full SQL movement/reorganization and partition_owner still failing/outside green: HA queue crash and root-owned destination defects retain distinct evidence. |
| R16 SHOW diagnostics and permissions | `owner_drop; representation_chunks; schema_policy; read_paths` | Verified DBA 14 named fields absent/present and class/VFID/HFID diagnostic joins. Non-DBA permissions, busy pages, partition expansion unverified. |
| R17 Committed crash redo | `crash_committed` | Verified acknowledged INSERT/UPDATE/DELETE model after actual owned SIGKILL, 5/56528→9/97832, positive typed RVOOS_INSERT REDO, owner/checkdb/cleanup. Typed DELETE, HA, internal retry/reclaim/lifetime unverified. |
| R18 Uncommitted crash undo | `crash_undo` | Verified live acknowledged autocommit-off writer plus independent flush fence, 9/97832→original 5/56528 after SIGKILL; positive typed RVOOS_INSERT REDO/UNDO. Typed DELETE, page reclaim, general lifetime/HA/internal faults unverified. |
| R19 Old snapshots and concurrent writers | `snapshot_visibility` | Verified repeatable-read ACKs/exact old/new values and 6/57372→9/90452→4/37316 chunk drain with >=3 retained full survivor/raw SHOW samples and actual eligibility. Pages stay 9→9; no page-return/retry/abort-safety credit. |
| R20 Rollback followed by vacuum | `none` | Defect disposition consistent CBRD-27237 retained. `abort01` source changed during attempt/no executed-overlay hash; no verified rollback-after-vacuum safety credit or final rerun. |
| R21 Accepted chain reuse/commit cleanup | `none` | Accepted implementation gap CBRD-27230: no notification emitter, no-op dispatch, old-value walk. Ordinary CRUD/snapshot passes grant no reuse/commit-notification credit. |
| R22 Same-slot retry safety | `none` | Capability gap: deterministic same-slot stale-reference/latch-loss schedule remains unestablished. Ordinary churn/drain receives zero credit. |
| R23 Page reclaim/horizon/growth reuse | `snapshot_visibility` | Verified obsolete chunk-record removal/live survivors only. Correct page-drop prerequisite fails 9→9; dependent three-cycle churn not executed; internal horizon/cursor/deallocation and reuse unverified. |
| R24 Lazy files/DROP/ownership | `owner_drop; lob_locators` | Verified inline nofile, populated owned DROP descriptors removed and complete survivor state unchanged; normal/failing historical cleanup retained. Retry/recovery/rollback-vacuum/workspace gaps separate. |
| R25 Unload/load/compact/workspace | `utility_cs; utility_sa` | Verified CS logical/schema/physical 4/37316 roundtrip and SA logical roundtrip with actual inline placement; explicit external-LOB transfer gets separate credit. SA physical candidate remains CBRD-27424 failed; no SA-WAL/stamp/reclaim/internal-fault/HA claim. |
| R26 Backup/restore/inspection | `backup_restore` | Verified acknowledged full 16KiB/active-log backup, completed primary/log headers, destruction of inventoried engine volumes/logs, exact restored values/schema/owner 4/37316 and checkdb. Retained external LOB payloads were not independently restored; no crash/stamp/HA claim. |
| R27 TDE pages/encrypted WAL | `tde_wal` | Verified owned lazy AES/existing NONE headers, isolated user-chunk DELETE 2/INSERT 3 encrypted flags and graceful reopen. Existing-file NONE→AES criterion 2 remains OPEN/UNVERIFIED; ciphertext, crash/HA/general lifetime unverified. |
| R28 Ordinary HA replication | `none` | Explicit agreed follow-up topology/transport gap; single DB HA SQL configuration and TDE case do not prove two-node values/queue alignment. Unmeasured. |
| R29 CDC/flashback historical values | `none` | Deferred product history scope/known existing failures; existing CDC remains enabled and unchanged, outside selected pass. Unmeasured. |
| R30 Corruption/fault/allocation internals | `sql05_transactions; sql05_constraints; sql05_bigone (reachable error subset)` | Reachable user-visible atomicity/error subset is verified under R10–12; corruption and deterministic allocation/fault injection remain capability gaps, unmeasured; native units not run here. |
| R31 Future/proposed/non-OOS | `none` | Deferred/proposed/cancelled/non-OOS inventory preserved; unsupported compression/PEEK/sharding/FORCE_INLINE/fixed BIT/internal LOB/>2GiB/spacedb contracts receive no invented test credit. |

Five correct tracked candidates remain outside the green set: public `cbrd_26659_oos_partition.sql`; private `cbrd_26659_partition_owner`, `cbrd_26659_snapshots_reclaim`, `cbrd_27237_rollback_vacuum`, `cbrd_26659_utility_sa_physical`. The correct [4060/4064 target supporting reproducer](03-target-4060-reproducer.sql) is outside the corpus. They were not changed, silently skipped or accepted with weakened expectations. Existing CDC remains enabled and unchanged. HA topology/transport, deterministic internal retry/fault/horizon controls and TDE existing-file application retain their separate partial/unverified status.

## Immutable evidence and handoff

Exact external launcher argument arrays are retained in [SQL launch](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/sql14-launch.json) and [shell launch](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/shell14-launch.json); actual native command arrays are [SQL command](/home/vimkim/tmp/oos306-sql14-a01/command.json) and [shell command](/home/vimkim/tmp/oos306-sh14-a01/command.json). New reproduction must choose unused short attempt paths and keep the same frozen full manifests, reviewed driver hashes, explicit identities and lock.

Fresh retained attempts are [SQL](/home/vimkim/tmp/oos306-sql14-a01) and [shell](/home/vimkim/tmp/oos306-sh14-a01); original commands, explicit environments/configuration, manifests, preflight, binaries, native verdicts, source/proof hashes, timings, raw results/journals and cleanup remain intact. Each attempt captures 78 frozen proof-source files, plus its own driver and hashed source manifests. The following manifests identify the selected evidence and proof files, excluding unrelated copied historical CTP results and software trees; critical copied software bytes are separately gated above.

| Suite | Retained evidence manifest | SHA-256 | Count |
| --- | --- | --- | ---: |
| sql | [sql14-artifacts.sha256.json](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/sql14-artifacts.sha256.json) | `37c76908d078137dac1212098761587e1cc251b456e445ec39fa2c9b00880c5e` | 130 files |
| shell | [shell14-artifacts.sha256.json](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/shell14-artifacts.sha256.json) | `7dce561b042c32dc66c03f002a8c430bdf655c3ef4907a13bfb457c12fb3cf09` | 1708 files |

Raw logs/scripts/generated proof inventory remain external and are not committed. This durable report is the only Ticket 14 docs-worker file. [All 31 coverage delta](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/coverage-delta.json) and [index/integration delta](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket14/coverage-index-delta.md) are supplied to root/merger, who owns shared coverage/README/local issue/map changes. Before handoff the worker merged current docs integration `048b726aa304572a1834173b6995263ffce9c9ab`, which was already included, and explicitly commits its report; the handoff records that commit. Fresh Standards+Spec review is owned by root. No testcase branch merge, publication or source mutation is part of this delivery.

## Current post-review qualification

The current private revision is `f5fc1fa815fbc6eec71135f506e377c0b1096da3`. Five existing entrypoints now share `oos_common/oos_lifecycle.sh`; their fixture values, physical models, expected results and 336 successful phase labels are unchanged. The [separate Standards/Spec correction and closure report](final-review-cleanup.md) retains each axis's original P2 and independent source/control closure, with zero remaining findings. Root [accepted the correction and fresh qualification](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/root-final-acceptance.json); this records those specific approvals rather than claiming a full rereview of unchanged fixtures.

SQL was not rerun. Root's [post-shell reconciliation](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/sql-reconciliation-after-shell.json) checks the retained original16 results byte for byte against reviewed answers,32 public inputs,130 artifact hashes, critical installed/runner/dependency identities and all original cleanup/proof gates. Its separate [final integration reconciliation](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/sql-reconciliation-final-integration.json) confirms the same retained evidence without a runtime invocation. Public `c94961578` is unchanged; the original SQL receipt and timing remain the current qualified SQL evidence.

The fresh [/home/vimkim/tmp/oos306-sh-final-a01](/home/vimkim/tmp/oos306-sh-final-a01) shell invocation passes exact14/14,0fail/skip,336 assertions and941 mandatory artifact requirements:936 unchanged original requirements plus5 owned registry journals. The [required proof](/home/vimkim/tmp/oos306-sh-final-a01/required-proof.json) SHA-256 is `fbed970d46c0d8ab14827d96c42c4dc7a2482d4a1225ea0e5261bda370e3be06`. [Root's independent retained-raw audit](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/root-fresh-native-artifact-audit.json) matches all14 typed models,1,234 per-case raw files,82 retained proof sources,72 public/private inputs and5 exact frozen-root ownership journals. The separate [complete case-log manifest](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/native-final-artifacts.sha256.json) hashes1,521 files; its scope includes framework/capture files beyond per-case proof. All native verdict/cleanup/required-proof gates are0.

Source/proof identities are frozen in the [final handoff](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/final-handoff.json), [proof04 contract](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/proof04/frozen-contract.json), [prepared hashes](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/proof04/prepared-hashes.json) and [review packet](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/review-packet.json). The contract SHA-256 is `9bc0e0ed8bf27d1a2a5dea6c2dab58d07034a66ecacec8e2f104347741e87895`; driver is `da5f39463a555011c56ac00ff42c08687c09f56789b4a9e0312cac7612f709cd`; verifier is `5879df3ecb7a6ef231d5a976bd55095e710a1a45f989d3aff339e54b2ec553eb`. Current frozen inputs are32 public and40 private; six committed shell paths account for the source delta. Original SQL16 and shell14 receipts, frozen contracts, manifests and result hashes remain byte-identical.

| Measured boundary | Retained original SQL | Initial shell at f16dd0ba9 | Corrected shell at f5fc1fa81 |
| --- | ---: | ---: | ---: |
| Preparation/copy seconds | 2.581152 | 2.423132 | 2.519735 |
| Additional proof freeze/copy seconds | — | — | 0.147599 |
| Whole native invocation seconds | 88.523774 | 304.532742 | 316.414065 |
| SQL body / shell native case sum seconds | 2.302000 | 301.391012 | 313.172622 |
| Mandatory retained proof seconds | 2.854042 | 11.096283 | 9.744288 |
| Locked invocation/verification/cleanup seconds, excluding preparation | 91.910559 | 316.062486 | 326.563374 |

The fresh driver whole boundary is 329.167290s including preparation/proof; the boundaries above overlap and are not added together. [Unrounded fresh measurements](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/native-final-measurements.json) retain each case/wrapper and command cost. Final qualification has **one SQL native invocation and two shell native invocations**, initial1 plus corrected1. No additional native correction attempt, retry or legacy fallback occurred; retained failed correction controls are shell stubs or offline proof checks, not native invocations. For comparing these two qualification runs, shell whole invocation times sum **620.946807s**, native case sums **614.563634s**, and mandatory proof overhead sums **20.840571s**, each its own boundary. These counts exclude earlier per-ticket implementation attempts, whose complete histories remain in their delivery reports. SQL stays a separate88.523774s invocation. The initial shared optdebug build129.45s remains separate; correction build/download overhead is0. About ten minutes per suite is guidance, without a hard600s or combined campaign gate.

The corrected source adds strict directory/device/inode and volume/log/LOB registration ownership before destructive cleanup and bounds command KILL grace. Full fixture/model proof and actual case-owned cleanup precede slot-wide framework containment teardown. The helper's serialized contained ownership checks do not claim an atomic guard against outside mutation or preservation of unrelated slot processes. Normal/failing original controls, all preliminary/failing proof packages, original SQL reconciliation search-root rejection and both initial native receipts remain external and unchanged.

All31 original dispositions and selected case keys above remain unchanged. Five correct tracked failing candidates, the4060/4064 target fixture, enabled unchanged CDC, HA topology/transport, internal retry/fault/horizon gaps, Ticket11 page-return/churn criterion4, abort01 missing executed-overlay identity, Ticket12 original rejected token/v1 receipts and Ticket13 existing-file NONE→AES criterion2 retain their prior failed, partial or unverified status. No engine correction, new physical coverage, public testcase change, build, destination merge or publication is implied. Root owns final integration reconciliation and local ticket/map/tracker closure.
