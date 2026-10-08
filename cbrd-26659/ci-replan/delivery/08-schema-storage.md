# Ticket08: schema changes, storage policies and partition ownership

Ticket08 delivers three passing public SQL cases and one passing schema/storage-policy shell companion, with independent negative controls. Correct full partition movement/reorganization and destination-owner regressions remain separate failing reproducers. The passing partition slice covers creation, routing, exact reads and duplicate rejection; it receives no movement, reorganization or destination-chain owner credit. No engine changes, publication or CI trigger are included.

## Implementation and independent review

The workers are `/home/vimkim/gh/cubrid-testcases/oos-08-schema-storage` and `/home/vimkim/gh/cubrid-testcases-private-ex/oos-08-schema-storage`, both on `task/oos-08-schema-storage`; the unique report lives in `/home/vimkim/gh/my-cubrid-docs-oos-08-schema-storage`, branch `docs/oos-08-schema-storage`. They started from the task integration branches after Tickets01/02 and include current integration through Ticket09. [Delivery manifest](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-delivery-manifest.json) records exact final tips, eleven task-file hashes, case selections and receipts. No shared coverage/index or local ticket/map is owned by this worker.

[Independent oracle](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-oracle.md), authoring recipes and root's [independent review](/home/vimkim/tmp/oos-developer-regressions-20261008/root-oracle-review-ticket08.md) / [literal model](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-root-independent-model.json) precede accepted execution. Root approved the original cases, source-derived external error mapping, one-line DDL parser and routing subset at public68aa8b364/private1a8653318. Root then approved private16fee048e's separate literal-default add and explicit UPDATE materialization model at11:41UTC. Answers were authored from those models; actual output was never used as a golden generator.

| Public case under `sql/_36_guava/cbrd_26659/cases/` | Delivered scope |
| --- | --- |
| `cbrd_26659_oos_schema.sql` | Reorder; metadata/data-bearing add/drop; variable precision/nullability and VARCHAR precision; rejected ALTER preserving schema/exact data; explicit DEFAULT read; OOS attribute drop; added growth value. |
| `cbrd_26659_oos_storage_policy.sql` | CREATE/LIKE/MODIFY/CHANGE/omission/reset preserve exact values; explicit policies reject current INT/fixed BIT/shared/class/view domains; eligible CHAR accepted; omitted policy clears on fixed conversion. |
| `cbrd_26659_oos_partition_routing.sql` | Passing creation/routing/read/duplicate-rejection subset, with exact row identities and values. |
| `cbrd_26659_oos_partition.sql` | Correct full movement/reorganization expectations retained separately; HA movement triggers a server assertion. |

| Private case under `shell/_40_guava/` | Delivered scope |
| --- | --- |
| `cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh` | Exact per-attribute SHOW CREATE policies; unequal placement and soft fallback; FORCE_OUTLINE profitability controls; nonretroactive ALTER followed by write; schema value preservation; literal-default add followed by explicit growth rewrite; positive SHOW/diagdb owner correspondence. |
| `cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh` | Correct root/child destination-only ordinary/forced ownership expectations. All phases execute, but the first insertion already violates ownership; later phases are diagnostic. |

The scoped `policy_ddl.py` parser requires exactly one CSQL row and CREATE TABLE, one occurrence of each named bracketed attribute, exact normalized policy options, and no empty/error/duplicate evidence. Its comma-delimited domain parser is approved for these BIT/VARCHAR/INT fixtures; it does not claim arbitrary nested-domain syntax. Synthetic controls accept the independently modeled positive/mixed-case DDL and reject wrong, missing, empty, error, duplicate-column and missing-row evidence.

## Physical models and proof limits

Current serialized VARBIT length is ALIGN(5+bytes,4); the stub and chunk header are24 bytes. DEFAULT3500/2500 creates one chunk3532, while PREFER_INLINE protects3500 and selects2500 for one chunk2532. Soft fallback5000/1000 creates two chunks6064. These unequal controls identify the selected attribute rather than simply observing a positive file. FORCE_OUTLINE VARBIT300 creates one chunk332; VARCHAR22 serializes24 and stays inline, VARCHAR23 serializes28 and creates one chunk52, while NULL/empty values stay inline. Policy ALTER alone preserves the old inline row; UPDATE301 creates its reviewed chain.

The initial schema5000/4600 has two chunks9664. Reorder/add/drop/precision/default/OOS-column-drop phases preserve each intended remaining value, and stopped-server diagdb confirms the original class/heap/file association. No post-MVCC live-chain count, reuse or reclamation assumption is made. Growth starts with inline d4×3000; adding the literal e5×2500 default preserves inline physical state while both values are readable. Explicit UPDATE materializes the added value and creates the unchanged largest-candidate chunk3032, with positive owner correspondence. This grants no ALTER-alone physical rewrite credit.

The default distinction is source-backed: `execute_schema.c:14861` skips attributes with explicit DEFAULT in the hard-default update path; `14974` skips DB_DEFAULT_NONE in the dynamic-expression update path. `add_column_update_hard_default` applies to NOT NULL attributes without DEFAULT. The public explicit DEFAULT77 assertion establishes its readable schema/data value, not a mandatory physical rewrite. The failed first positive shell attempt is retained rather than lowering its incorrect ALTER-alone claim.

Public JDBC and shell CS are separate invocations. The shell schema/policy fixture often omits the public id PRIMARY KEY; matching payloads do not establish whole-schema or interface identity. Physical claims apply only to the executed shell fixture. Both use16KiB I/O pages and the source-matching OptDebug installation; SQL's selected profile enables HA, while the CS shell profile uses default HA off. SQL provides no physically observed JDBC, HA transport, retry, snapshot/recovery, producer-ownership or reclaim credit.

The fully read normative context SHA256 is `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`. Its missing FORCE_OUTLINE description is a canonical documentation omission, distinguished from accepted CBRD-26067 behavior. The issue's dated16-byte wording is reconciled with current canonical24. Proposed FORCE_INLINE, fixed DEFAULT exceptions and variable fixed BIT semantics are not asserted as existing behavior.

## Accepted native evidence and timing

All attempt preparation, native execution, verdict and cleanup held the exclusive `validation.lock`. The pinned source is `fb567a629cdb390fff920542173fa36f454c74a0`; source/install/JDBC/runner/testcase/config/environment identities and actual commands are retained per attempt. Each attempt uses a fresh contained native slot, short owned DB name, explicit64MiB DB/log volumes,16KiB pages and unset TESTKIT_SLOT_VOLATILE. Shared build129.45s and JDBC preparation are excluded from execution measurements.

| Attempt under `/home/vimkim/tmp/` | Exact artifact verdict | Preparation seconds | Native runner seconds | Locked runner/proof/cleanup seconds |
| --- | --- | ---: | ---: | ---: |
| `oos306-sql08-n03` | Exclusive false first digest rejects; actual single schema result byte-matches the reviewed real answer. verify1, cleanup0. | 1.018 | 94.902 | 95.412 |
| `oos306-shell08-n02` | Exclusive copied PREFER_INLINE2533 rejects; actual retained SHOW accepts independently reviewed2532. One intended NOK, verify1, cleanup0. | 1.777 | 10.655 | 11.106 |
| `oos306-sql08-a01` | Exact selected3 SQL, success3/fail0/skip0; verify0, cleanup0. | 1.043 | 88.265 | 88.747 |
| `oos306-shell08-a02` | Exact selected1 shell, success1/fail0/skip0;54/54 assertions,76/76 required logs, verify0, cleanup0. | 1.033 | 12.992 | 13.384 |
| `oos306-shell08-r01` | Correct owner repro: total1/fail1/skip0,14 NOK; verify1, cleanup0. | 1.035 | 11.189 | 11.570 |

The SQL result root is `oos306-sql08-a01/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_0820331484_11.5.0.2637-fb567a6`; summary XML and native verifier prove the three exact identities. Native per-case times are routing0.064s, schema0.136s and policy0.109s. The whole invocation includes native DB/broker setup and normal stop/deletion, explaining its larger measured cost.

The accepted shell proof requires all54 named policy/value/placement/owner/cleanup tokens and all76 raw case logs, checked for exactly one retained file per name. `raw-log-retention.json` establishes actual evidence retention after teardown. Successful deletedb emits an empty retained utility log; its actual zero exit, cleanup verdict and registry/directory absence supply the proof. All assertion-bearing SHOW/value/DDL/diag logs are nonempty. [Final artifact proof](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-final-proof.json) independently checks the exact verdicts, tokens, raw files and owned cleanup. The shell's measured case interval through cleanup is11.030s; native recorded case time is11.269s.. The two `exclusive-negative-proof.json` receipts prove only copied expectations changed and independently discriminate the intended phase. Earlier inconclusive negatives receive no red credit.

Case lifecycle cleanup distinguishes owned directory creation from registered DB ownership, rejects preexisting names/paths, removes only its own empty failed-create directory, and preserves valuable partial DBs or failed-deletion files as NOK. Names oos08sp/oos08po are below MAXLOGNAME18's maximum17-character prefix. Every shell timeout has a5-second forced-kill grace. Accepted runs prove normal server stop/database deletion, absence of owned process/registry/fixture/slot, unchanged testcase inputs and full configuration restoration. Earlier failures also leave no owned process/database/config changes; when mandatory phases were unreached, cleanup.exit1 records that evidence-gate failure rather than disguising a pass.

Bash syntax, parser AST, task diffs and native `testkit check-cases` pass. The shell checker uses the explicit CTP helper directory:145 helpers,37 failure-capable, zero cannot-fail/misspelt-verdict/self-comparison findings. The first mistaken checker helper argument is superseded by these focused checks. Public diff checks allow CQT's required trailing answer spaces. No engine/profile workaround or host workenv change was made; unrelated CCI dirt and the existing prepared CTP checkout changes recorded in identities.json are preserved.

## Retained failures and dispositions

| Earlier attempt | Honest disposition | Runner seconds |
| --- | --- | ---: |
| `oos306-sql08-n01` | Inconclusive full-partition false-digest negative: correct movement also crashes HA server. | 131.859 |
| `oos306-sql08-n02` | Inconclusive schema negative: additional internal-versus-external rejection-code mismatch. | 85.223 |
| `oos306-shell08-n01` | Inconclusive physical negative: initial parser assumed multiline DDL and never reached the deliberately false placement. | 8.655 |
| `oos306-shell08-a01` | Correctly rejects an unsupported ALTER-alone materialization assumption; growth/owner phases unreached. | 12.333 |

External rejection codes are independently corrected from source: the schema validator's internal-494 parser error is reported through `db_vdb.c:2389` PT_EXECUTION and `query_result.c:379` as-495. Shared/class grammar rejection clears statements at `csql_grammar.y:24083`, then `db_vdb.c:843` reports PT_SYNTAX as-493. Intended domain rejection and preserved schemas/values are unchanged.

The n01 movement crash report remains under its exact result root at `CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_0819372214_11.5.0.2637-fb567a6/crash/cbrd_26659_oos_partition.cub_server_20261008193749.320.coredump`. The stack is `repl_log_insert` → `locator_add_or_remove_index_internal:8179` → `locator_delete_force_internal:7856` → `locator_update_force:5423`. Pinned `replication.c:468` asserts on an empty oos_insert_lsa_queue for RVREPL_OOS_INSERT/DUMMY. Full movement/reorganization remains unearned; this HA failure is distinct from CBRD-27089 without stronger causal evidence.

Correct owner r01 retains35 assertions and75 raw logs. Empty root/children pass, then ordinary insertion wrongly reports root1/5032 and destination p0 nofile; FORCE insertion wrongly reports root1/332 and child nofile. Movement, duplicate probes, exact reads, SHOW ALL and final diagdb all execute diagnostically after that failure. Raw diagdb includes root-owned files1|960/1|1472 and source-p0 files1|1024/1|1536, with no destination-p1 descriptor. Child expected-positive SHOW parsing leaves empty JSON, so final owned JSON errors are downstream evidence, not an independently positive owner result. [Failure disposition](/home/vimkim/tmp/oos306-shell08-r01/failure-disposition.json) retains raw identities and every actual phase. No source-drain count is required before vacuum, and no destination-owner passing credit is claimed.

Existing CDC regressions are untouched and remain enabled. The new full movement and owner reproducers retain correct expectations and are excluded from the documented passing selection; any whole-subtree run must account for these known failures.

## Coverage delta for serialized merger

| Row | Delivered assertions and evidence | Remaining limits |
| --- | --- | --- |
| R06 | Passing public accepted policy/domain matrix; shell exact metadata, DEFAULT/PREFER discrimination, fallback, FORCE gate/profitability and nonretroactive rewrite. SQL a01/shell a02 plus independent negatives. | Canonical FORCE_OUTLINE omission explicit; proposed contracts receive no credit. |
| R14 | Passing compact schema categories, failed ALTER schema/data preservation, exact rewrite/drop values, initial OOS owner persistence, inline add followed by explicit growth UPDATE1/3032 and owner proof. | Explicit default add is virtual until write; no ALTER-alone materialization, live-chain identity or reclaim credit. |
| R15 | Passing exact public creation/routing/read/duplicate subset. Correct full movement/owner failures retained separately with exact-source diagnostics. | No passing movement/reorganization/destination-owner claim; HA queue assertion and CBRD-27089 remain distinct dispositions. |
