# Ticket08: schema changes, storage policies and partition ownership

Ticket08 implements the required schema kinds and accepted storage-policy behavior as three proposed passing public SQL cases, a separate full partition movement/reorganization reproducer, and two independent private shell cases. The original pre-runtime oracle was approved and three inconclusive attempts are retained. Narrow amended source/error/parser/routing reviews and final native validation remain pending; this ticket is unresolved. The correct partition destination-owner regression retains CBRD-27089 expectations and is kept separate from the proposed passing set. No engine changes, publication or CI trigger are included.

## Frozen implementation and independent expectations

Public worker `/home/vimkim/gh/cubrid-testcases/oos-08-schema-storage`, branch `task/oos-08-schema-storage`, initial commit `78089f45a`; private worker `/home/vimkim/gh/cubrid-testcases-private-ex/oos-08-schema-storage`, same branch, initial commit `37d463d57`. Both started from their current integration task branches after Tickets01/02. Source is `fb567a629cdb390fff920542173fa36f454c74a0`; the ready OptDebug install is source matching.

The reviewed expectation note is [ticket08-oracle.md](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-oracle.md). It freezes exact row/schema/policy/physical models before execution. The independent authoring recipes and read-only JIRA receipts remain in that coordination directory. CQT answer rendering contains required trailing spaces, independently authored from intended results rather than captured actual output.

| Public SQL identity under `sql/_36_guava/cbrd_26659/cases/` | Observable evidence |
| --- | --- |
| `cbrd_26659_oos_schema.sql` | Reorder; metadata and data-bearing add/drop; variable precision/not-null and VARCHAR type/precision changes; rejected ALTER preserving schema/exact data; hard DEFAULT rewrite; OOS attribute drop; inline-to-OOS candidate growth. |
| `cbrd_26659_oos_storage_policy.sql` | CREATE/LIKE/MODIFY/CHANGE/omission/reset preserve exact values; explicit policies reject current INT/fixed BIT/shared/class/view domains; eligible CHAR accepted; omitted policy during fixed conversion clears the setting. |
| `cbrd_26659_oos_partition_routing.sql` | Supported creation/routing/read/duplicate-rejection subset. Exact row identity and values; no movement, reorganization or owner credit. |
| `cbrd_26659_oos_partition.sql` | Full intended movement/reorganization regression kept with correct expectations. The current OptDebug/HA profile crashes during movement; later outputs are diagnostic. |

| Private shell identity under `shell/_40_guava/` | Observable evidence |
| --- | --- |
| `cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh` | Named SHOW CREATE policy state, independent unequal-candidate placement, soft fallback, FORCE_OUTLINE small-record/profitability controls, nonretroactive ALTER then rewrite, schema physical positive/negative controls, exact data through transformations and diagdb owner correspondence. |
| `cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh` | Correct ordinary/forced destination-only root/child requirements for creation, insertion, movement and duplicate probes; SHOW and saved owner descriptors. Independently retained defect regression. |

## Physical scope and dispositions

Each SQL run and shell companion is an independent invocation. The shell case uses CS and 16 KiB I/O pages with fresh fixtures; its SHOW evidence does not observe the public JDBC invocation. The current 24-byte inline stub and chunk header determine exact slot-byte sums. With unequal VARBIT candidates3500/2500, DEFAULT requires one chunk3532 while PREFER_INLINE requires one chunk2532. Fallback5000/1000 requires two chunks6064. These differences distinguish selected attributes rather than crediting positive OOS state alone.

FORCE_OUTLINE bypasses the ordinary record gate for profitable values. VARBIT300 requires one chunk332. VARCHAR22 serializes24 and stays inline; VARCHAR23 serializes28 and creates one chunk52; NULL and empty values create none. Changing an existing inline row's policy does not itself rewrite; the later UPDATE301 creates the expected chain. Initial schema5000/4600 requires two chunks9664, and inline3000 plus a hard-default2500 rewrite requires one chunk3032.

The normative context fully read on2026-10-08 has SHA256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`. Its missing FORCE_OUTLINE description is a documentation omission. The accepted CBRD-26067 contract supplies this behavior; the issue's dated16-byte wording is reconciled to current canonical24. Proposed FORCE_INLINE, fixed DEFAULT exceptions and variable fixed BIT semantics receive no existing-behavior assertion.

The partition owner contract requires only the destination child to own an inserted/moved chain. The source child's old records may remain before vacuum, so this testcase does not assert premature source drain. Logical equality does not close CBRD-27089. Identity, retry, vacuum/reclaim, snapshot/recovery, ordinary HA and client workspace/loader producer ownership are outside the physical proof established here.

## Validation and cleanup

Root approved public9bff57e86/private19590c93f in [root-oracle-review-ticket08.md](/home/vimkim/tmp/oos-developer-regressions-20261008/root-oracle-review-ticket08.md), with [independent model](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-root-independent-model.json). That approval preceded the source-derived SQL error mapping, one-line DDL parser correction and routing-only addition. Amended public68aa8b364/private1a8653318 await review; no native runtime is active. The coordinator currently cannot respond, and the merger correctly declined to authorize runtime in its place. Each attempt will retain configuration/identity/artifact proofs under the coordination directory and hold `validation.lock` through preparation, runtime and cleanup. SQL and shell timing remain separate. Initial build/JDBC preparation was shared and is not attributed to these testcase execution costs.

Focused checks already pass: both Bash scripts parse, policy parser compiles, and native `testkit check-cases` with the explicit CTP helper directory sees145 helpers and zero cannot-fail, misspelt-verdict or self-comparison findings for each case. A first checker invocation accidentally supplied a testcase directory as the helper path and emitted false missing-helper warnings; the proper explicit-helper check supersedes that configuration mistake. Independent one-line SHOW CREATE parser controls accept the modeled positive and reject wrong, absent, empty, error, duplicate-column and missing-row fixtures. Public `git -c core.whitespace=-blank-at-eol diff --check` passes the repository CQT rendering convention; private diff check passes normally.

## Coverage delta for serialized merger

| Row | Delivered independent assertions | Credit/disposition |
| --- | --- | --- |
| R06 | Public accepted policy/domain matrix; shell per-attribute metadata and exact policy placement controls. | Pending native proof. Canonical FORCE_OUTLINE omission stays explicit. |
| R14 | Complete compact schema categories; exact failed-ALTER schema/data and growth physical control. | Pending native proof. No live-chain identity/reclaim claim. |
| R15 | Public logical routing/movement/reorganization; correct root/child destination-owner shell regression. | Supported routing subset pending native proof; movement/reorganization blocked by the retained replication assertion, destination ownership independently dispositioned. |

## Retained attempts and diagnosed limits

| Attempt | Exact selection / result | Native runner seconds | Cleanup |
| --- | --- | ---: | --- |
| `/home/vimkim/tmp/oos306-sql08-n01` | One full partition case with intentionally false first digest. Inconclusive negative: besides detecting the false digest, the correct movement triggers server crash. | 131.859 | cleanup.exit0; no owned process/registry/database, config restored. |
| `/home/vimkim/tmp/oos306-sql08-n02` | One schema case with intentionally false first digest. Inconclusive negative: expected external rejection number was modeled from internal unit return rather than the SQL reporting layer. All intended row/schema predicates match; external code correction requires reviewed rerun. | 85.223 | cleanup.exit0; normal DB stop/delete and config restoration. |
| `/home/vimkim/tmp/oos306-shell08-n01` | One copied schema-policy case with deliberately false PREFER_INLINE sum2533. Inconclusive negative: initial SHOW CREATE parser expected multiline attributes, while the product emits one DDL string; discriminator was not reached. | 8.655 | All process/registry/slot/config/source-hash cleanup gates true; cleanup.exit1 accurately records missing required discriminator tokens. |

The external SQL error model is corrected from primary source: `do_validate_oos_storage_setting` returns the internal semantic code, but `db_vdb.c:2389` reports execution-time parser errors through `pt_report_to_ersys_with_statement(...PT_EXECUTION...)`, which maps them to `ER_PT_EXECUTE=-495`. Grammar-time shared/class policy rejection leaves parser errors and returns no tree (`csql_grammar.y:24083`); `db_vdb.c:843` maps that to `ER_PT_SYNTAX=-493`. Domain rejection and preserved data/schema expectations are unchanged. This is an interface-oracle correction, not acceptance of a product defect.

The n01 crash report is retained under that attempt's result root `CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_0819372214_11.5.0.2637-fb567a6/crash/cbrd_26659_oos_partition.cub_server_20261008193749.320.coredump`. Its stack is `repl_log_insert` → `locator_add_or_remove_index_internal:8179` → `locator_delete_force_internal:7856` → `locator_update_force:5423` during partition movement. At pinned `replication.c:468`, RVREPL_OOS_INSERT/DUMMY handling asserts on an empty `oos_insert_lsa_queue`. This public-profile movement failure is distinct from the destination-owner mismatch unless stronger causal evidence connects them. No engine/profile workaround is used; full correct movement/reorganization expectations remain retained and the proposed passing routing subset is explicitly narrower.

## Exact outstanding work and portable resume

The mandatory selected native verdicts are not yet established. Do not integrate this ticket as a green delivery or mark its local ticket resolved. All required schema/policy/partition fixtures are implemented; the remaining gate is independent review of narrowly amended expectations and parser behavior, followed by actual verification.

Review frozen [routing addition](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-routing-frozen.patch), [external error mapping](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-error-mapping.patch) and [one-line parser correction](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-ddl-parser.patch) against the original reviewed literal/schema/physical model. Correct movement/reorganization and destination-owner expectations remain unchanged. No later runtime has used these amendments yet.

After that gate, rerun a single-schema false-digest negative with `ticket08-native-sql-attempt.py --wrong-ticket08-digest`, then execute exactly `cbrd_26659_oos_schema.sql`, `cbrd_26659_oos_storage_policy.sql` and `cbrd_26659_oos_partition_routing.sql` through the same driver with fresh short attempts. Rerun a copied physical negative with `ticket08-native-shell-attempt.py --wrong-ticket08-prefer`; only the copied2532→2533 assertion changes. Require the intended failing phase and complete owned cleanup. Then run the tracked schema-policy case with every named phase/owner/cleanup token and the correct partition-owner repro separately. The Ticket08 shell driver writes cleanup.exit inside the held lock, in addition to the generic source-hash, token and lifecycle gates. Its compile and independent parser controls pass.

The proposed passing SQL list excludes the correct failing full movement/reorganization repro, and the proposed passing shell list excludes the correct owner repro unless that exact source passes. These exclusions concern new documented correct defect reproducers; existing CDC regressions are untouched and remain enabled. Narrow logical routing gets no movement, reorganization or destination-owner credit. R06/R14 native passing credit also remains pending until clean artifacts exist.

Current preserved worker tips after authorized task-integration updates are public0e3ddffa2a0b3424d77baa47ec1efe0ad8413d30/private037d31c42c46768e0ead2356058e8bf1dff8aaea. [Exact manifest and status](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket08-delivery-manifest.json) freezes all11 task files, proposed passing lists, correct reproducers and retained attempts. No shared coverage/index or local issue/map was edited by this worker. Both testcase workers are clean; the unrelated CCI dirt and shared build/host environment remain preserved.
