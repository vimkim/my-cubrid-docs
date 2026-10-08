# Ticket02: owned OOS DROP and survivor regression

Date: 2026-10-08 (Asia/Seoul). Approved implementation ticket02 of [the developer regression specification](../spec.md). The delivered private shell case passed the native contained runner with **one exact executed case, 21 successful assertions, zero failures and zero skips**. A fresh wrong-seven-chunk negative control on the final code failed as intended and proved failed-case cleanup. This delivers the narrow R24 lifecycle and R16 diagnostic subset; the matching public SQL invocation retains separate logical coverage.

## Delivery and independent model

Private checkout `/home/vimkim/gh/cubrid-testcases-private-ex/oos-02-owner-drop`, branch `task/oos-02-owner-drop`, initial integration base `c4b9d482fbd491a68510b2552df2c3cac91911fc`, final tested commit `4de68fb31499ecb2dfeb42b14ece8d7e902cd448`.

| Delivered path relative to the private repository | Responsibility |
| --- | --- |
| `shell/_40_guava/cbrd_26659_owner_drop/cases/cbrd_26659_owner_drop.sh` | Bounded CS setup, named phase assertions, owned DROP, offline utilities and normal/failing EXIT cleanup |
| `shell/_40_guava/cbrd_26659_owner_drop/cases/setup.sql` | Small independent metadata model, inline-only control, owner and surviving copy |
| `shell/_40_guava/oos_common/oos_observe.py` | Small reusable strict reader of named CSQL fields and diagdb owner descriptors; retains volatile class/file identities for joins |

The case follows `<name>/cases/<name>.sh`, `init test`, `write_ok`/`write_nok` and `finish`; verdicts use native file feedback, rather than generated answers. `bash -n`, `shellcheck -S warning`, native `testkit check-cases` and staged whitespace checks passed. The read-only checker found one case, no ineffective verdicts, misspelled verdict calls or self-comparisons.

The independently recomputed four-row fixture matches Ticket01 public commit `5e25be4e2d1d471b1f1b3ea6736c970f8c323e34`: INT primary key, payload and tag BIT VARYING, distinct head/middle/tail byte segments. Source id1 uses VALUES, ids2–4 use INSERT SELECT from metadata, and survivor uses INSERT SELECT from owner. Inline-only control copies id1. Writes commit before observation.

| id | Payload hex-byte segments in order | Payload octets / serialized bytes | Tag | Intended payload chunks |
| --- | --- | --- | --- | ---: |
| 1 | aa × 1000, bb × 1000, cc × 1000 | 3000 / 3008 | 11 × 300 bytes | 0 |
| 2 | d1 × 1401, e2 × 1403, f3 × 1403 | 4207 / 4212 | 22 × 300 bytes | 1 |
| 3 | 12 × 7001, 34 × 6501, 56 × 6501 | 20003 / 20008 | 33 × 300 bytes | 2 |
| 4 | 78 × 11001, 9a × 11000, bc × 11000 | 33001 / 33008 | 44 × 300 bytes | 3 |

Each tag serializes to 308 bytes and stays inline. Full value equality, independent literal payload/tag MD5 digests, actual row count4, matched ids4, payload octets60211 and tag octets1200 are required. Digests were recomputed with Python hashlib over the lowercase hex text before runtime. The expected six OOS chunk records occupy `4212+20008+33008+6×24=57372` slot-record bytes, including the accepted 24-byte chunk headers. Inline id1 is below both normative/current-source targets; the other payloads are safely above both, so this case does not certify the disputed exact demotion boundary.

The pre-runtime [oracle note](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket02/oracle-review.md), [independent model](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket02/independent-model.json) and [coordinator review](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket02/root-oracle-review.md) retain the model, source-backed format corrections and review decisions. Actual results never supplied replacement expected values.

## Verified physical phases

SHOW requires one row with all14 named fields, exact class identity, valid class/heap identifiers, correct NULL/zero absent-file fields, six positive chunk records and57372 slot bytes for each live OOS owner. Missing, duplicate, empty or erroneous parses fail. All writes are committed and no writer overlaps SHOW. Successful offline `diagdb -d 2` must contain parseable file records and correlate class OID, OOS VFID and owner HFID; malformed OOS rows and unknown-class diagnostics reject.

Final observed identities are retained in [the observed-state proof](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket02/attempt-07-reviewed-final-clean/observed-state-proof.json):

| Class | Class OID | Owner HFID: header / volume / file | OOS VFID: volume / file | Chunks / slot bytes | After owner DROP |
| --- | --- | --- | --- | --- | --- |
| `dba.oos_inline` | 0 / 195 / 5 | 769 / 1 / 768 | NULL | 0 / 0 | Remains file-free |
| `dba.oos_owner` | 0 / 195 / 7 | 897 / 1 / 896 | 1 / 1088 | 6 / 57372 | Saved VFID, owner HFID and class absent |
| `dba.oos_survivor` | 0 / 208 / 1 | 1025 / 1 / 1024 | 1 / 1152 | 6 / 57372 | Same class/file/full SHOW state and exact model values |

Before DROP, diagdb parsed80 distinct file records; after DROP it parsed77, retaining the survivor descriptor while removing the three owner files. There are six OOS user pages per live owner/survivor file, internal page size16344, physical bytes98064 and unused bytes40692. These observed page counts are supporting evidence; the independent model requires positive pages and exact chunks/slot bytes.

Sixteen behavior assertions cover exact inline/owner/survivor values, absent/present named SHOW fields, pre-DROP descriptor joins, committed DROP and catalog absence, unchanged survivor state, saved owner VFID/class/HFID disappearance, survivor descriptor retention and successful checkdb. Checkdb is quiet on success: explicit exit0 plus a nonempty invocation-specific diagnostic log and absence of errors/warnings/corruption are required. Failed post-DROP commands and empty parses cannot establish disappearance.

## Configuration and artifact verdict

| Component | Recorded validation identity |
| --- | --- |
| Engine source | `fb567a629cdb390fff920542173fa36f454c74a0`; no PR for its local task branch; unrelated CCI dirt preserved |
| Original shared install | `/home/vimkim/.cub/install/CBRD-26659-oos-testcases-handover/optdebug`; copied into each attempt |
| Installed identity | `11.5.0.2637-fb567a6`, 64-bit OptDebug Linux, built2026-10-08 18:06:49; exact source/install match, no mismatch exception |
| Native runner | `/home/vimkim/.local/bin/testkit`, `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`; local build metadata reports revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0` with modifications |
| CTP assets | `9c62858b10005d721546cc007be260844033b9e9`; existing modified helpers/configuration were recorded and copied, not edited in place |
| Shell profile | 16 KiB I/O/log pages, 20MiB initial DB/log volumes; CSQL CS writes/SHOW, offline SA diagdb/checkdb, DBA, normal logging, no testcase parameter changes |
| Native configuration | Explicit shell family, containment, one slot, scenario_disk=on, file feedback, no update/continuation/retry; TESTKIT_SLOT_VOLATILE unset; case_logs=all with64MiB capture budget |

JAVA_HOME selects Temurin8.0.462+8 for framework compatibility; this shell fixture uses CSQL and has no JDBC execution prerequisite. The matching public case uses JDBC CS with autocommit=true and the coordinator later selected64MiB initial public DB/log volumes. This shell uses explicit COMMIT and directly drops the populated owner; public Ticket01 DELETEs its source before DROP. Those invocation, interface and volume-size differences are explicit. The shell neither observes nor certifies public SQL placement.

Final exact manifest identity is `/home/vimkim/gh/cubrid-testcases-private-ex/oos-02-owner-drop/shell/_40_guava/cbrd_26659_owner_drop/cases/cbrd_26659_owner_drop.sh`. The helper verified matching positive dispatch and finished lists, total/executed/success1, failure/skip0, feedback completion, per-environment logs and successful JUnit XML. All21 testcase assertions passed:16 behavior and5 normal-cleanup assertions. Runner exit0 alone was not used as a verdict.

| Input | SHA-256 |
| --- | --- |
| Final shell case | `2637e10f182f7f88c5ced8ce6d7281b3ebe66c1813aba77874f9bd5a3e29ad5e` |
| Setup fixture | `770c052dad1c5a43c28ba239511350bde093da2286e1015f8980b41cbd7b8f23` |
| Strict observer | `01cab781669134563b1f3ffcec32607a0b4449ce181708a01bd7b91678b1f348` |

## Retained attempts and measured cost

All attempts remain under `/home/vimkim/tmp/oos-developer-regressions-20261008/ticket02/`; [attempt-summary.json](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket02/attempt-summary.json) records exact revisions, counts and times. Each directory retains identities/hashes, environment, exact manifest, copied configuration, preflight, command, runner log/status, verdict artifacts and cleanup/timing receipts. Native diagnostics for attempts02–07 are under `CTP/result/shell/case-logs/_40_guava/cbrd_26659_owner_drop/cases/`; exact verdict artifacts are under `CTP/result/shell/current_runtime_logs/`.

| Retained attempt directory | Outcome and reason | Case seconds | Runner seconds | Preparation seconds |
| --- | --- | ---: | ---: | ---: |
| `attempt-01-wrong-seven-chunks` | Wrong7 assertion NOK;21 unrelated global macro skips inflate total22, so non-strict negative receipt | 7.357 | 9.177 | 1.826 |
| `attempt-02-wrong-seven-strict` | Exact one-case negative: failure1/skip0; intentional7 rejects actual6 | 7.612 | 9.044 | 1.880 |
| `attempt-03-reviewed-clean` | Testcase reader failure: HFID components joined in wrong order, before DROP | 7.799 | 9.182 | 0.992 |
| `attempt-04-wrong-seven-corrected-reader` | Corrected reader strict negative: failure1/skip0 | 7.448 | 8.822 | 1.904 |
| `attempt-05-reviewed-clean-corrected-reader` | All15 pre-checkdb behavior assertions pass; overstrict reader rejects normal quiet checkdb stdout | 12.633 | 16.340 | 1.075 |
| `attempt-06-wrong-seven-final` | Final-code strict negative: failure1/skip0, one NOK, six failed-case cleanup assertions OK | 7.461 | 8.821 | 1.780 |
| `attempt-07-reviewed-final-clean` | Final-code clean pass: success1/failure0/skip0, all21 assertions OK, helper0 | 12.593 | 13.926 | 1.041 |

The wrong7 modification exists only in copied negative scenarios; committed expected chunks remain6 throughout. Final attempts06/07 share commit `4de68fb31499ecb2dfeb42b14ece8d7e902cd448`; [negative strict proof](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket02/attempt-06-wrong-seven-final/strict-proof.json), [clean strict proof](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket02/attempt-07-reviewed-final-clean/strict-proof.json) and [passing helper receipt](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket02/attempt-07-reviewed-final-clean/verify.log) establish the final red/green loop.

The local native runner filters unsupported-platform macros over the full corpus before applying testcase_from_file, so a one-case focused selection initially counted21 unrelated skips. The coordinator approved clearing that attempt-only macro filter for this selected case, which contains no unsupported-platform branch; every required selected assertion still executes. No repository exclusion policy or runner code was changed.

The initial reader assumed file/volume/header HFID order. Pinned `storage_common.h:201` and `file_manager.c:1409` instead define header/volume/file; the correction preserves the intended ownership join. Pinned `util_cs.c:checkdb` reaches EXIT_SUCCESS after consistency checks/shutdown without a success print; checkdb handling now retains status and inspects its diagnostics. These are testcase format/utility-contract corrections, not engine defects or replacement value expectations.

Final case timing includes framework initialization, fixture, observations, DROP, utilities and cleanup. Whole-run timing includes native setup/dispatch/capture/teardown. Final locked invocation including preflight, helper verification and external cleanup was14.306s; the additional verification/preflight/cleanup cost was0.380s over runner time. Copy/config preparation was1.041s, separately measured after lock acquisition. Lock wait is excluded. All DB/runner runs were serialized; attempt01 preparation overlapped Ticket01 setup before the coordinator expanded locking to preparation. Final attempts06/07 preparation and execution were fully serialized. Coordinator-owned build overhead was129.45s and is outside testcase timing. These local costs are not predictions of company CI or the final selected whole-suite cost, and no hard time cutoff was applied.

## Cleanup and coverage delta

The case owns only `oos02_owner_drop`, its exact cub_server processes identified by command name and DB argument, and its scenario-overlay files. All CSQL commands have bounded completion; server readiness is bounded. Normal and assertion-failure EXIT paths stop only the owned server when needed, prove no owned server PID, delete the owned DB, remove its registry entry and remove the fixture directory only after safe stop and successful deletedb. Stop/delete failure leaves owned DB files retained. No new broad kill logic is introduced; inherited init/finish process and IPC cleanup is bounded by the native slot namespaces.

Final negative06 proves six failed-case cleanup assertions. Final clean07 proves five normal cleanup assertions, with its two prior explicit server stops already checked. Both record empty outer registry, absent outer owned DB directory, empty slot scratch parent, no accessible process executable from the attempt install and restored original disposable configuration. Host process scans also record inaccessible/racing PIDs and do not certify global host cleanliness. Each case restores its deployed configuration baseline; native deployment's separate outer-attempt changes are preserved in `conf-after-runner/`, then the attempt wrapper restores `conf-before-invocation/`. Original shared source/Debug workenv and CCI user dirt remain outside attempt ownership and were preserved.

The coordinator owns the shared coverage table/index updates. Apply this delta using case `cbrd_26659_owner_drop` and the following phase identifiers:

| Coverage row | Delivered phase / independent result | Actual verified scope | Remaining disposition |
| --- | --- | --- | --- |
| R01 Basic insert/read and copy | `inline`, `owner`, `survivor`: matching VALUES/INSERT SELECT model, literal digests; each large-owner file6 chunks/57372 bytes | Physical companion for this separately executed shell fixture; copied survivor retains full values after populated-source DROP | Public JDBC placement remains separate; no per-row head-chain identity, retry, raw fetch or reclaim credit |
| R16 Product SHOW diagnostics | `inline`/`inline-after`: no file, NULL VFID and zeros; `owner`/`survivor`/`survivor-after`: all14 named fields, exact class/file/HFID joins and positive stats | DBA, quiescent CS named-field and absent/present-file subset; malformed/empty/error parses reject | Non-DBA permissions, partition expansion, busy-page behavior and broader diagnostic contract remain uncovered |
| R24 Lazy file creation, DROP and ownership | `diag-before`, `drop`, `diag-after`, `checkdb`: inline file absent, distinct owner/survivor files present, saved owner removed and survivor intact | Successful populated-owner DROP, exact surviving copy, positive pre-DROP and successful post-DROP diagnostics, checkdb and cleanup | Empty-page reclaim, retry, recovery, rollback/vacuum, SA/workspace demotion and HA remain separate gaps |

No mandatory criterion remains unmet for this narrow ticket. No engine fix, push, JIRA publication or GHA execution occurred. Whole-company-corpus native/CTP equivalence and broader OOS conformance are not established by this focused pass.
