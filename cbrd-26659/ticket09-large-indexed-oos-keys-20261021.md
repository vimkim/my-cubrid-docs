# Work456/09: large indexed OOS keys

Date: 2026-10-21, Asia/Seoul. Reader: the Work456 coordinator and tickets 10/16. Related reviews: [engine 8128](https://github.com/CUBRID/cubrid/pull/8128), [public TC 3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), [private TC 4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

This report checks whether PK/UNIQUE operations preserve complete large keys when the indexed attribute itself is OOS-backed. The original complete shell run passed all 108 declared phases. The native JDBC case passed its independent answer. The final 108-phase shell receipt and three effective failure controls complete the required execution. No ticket 09 functional or oracle gap remains in the supported selection. This delivery adds tests and a reusable referenced-key fixture. It changes no production behavior. The [earlier post-DDL connection failures](ticket09-post-ddl-connection-observation-20261021.md) remain preserved and unattributed. The final complete run executes those scenarios successfully. This result establishes no repair or crash attribution.

`C` means stored HAS_OOS clear. `S` means stored HAS_OOS set. The [ticket 01 observer](ticket01-baseline-and-observer-20261021.md) supports current, unpartitioned, unrelocated `REC_HOME` records. A record flag establishes the indexed attribute's placement here because that attribute is the only eligible variable attribute.

## Revisions and execution identity

| Component | Exact identity |
| --- | --- |
| Native source | `CUBRID/cubrid@1ef86a7efa34002e971b1b30bcf5d451e9db441b`, branch `task/work456-09-source`, initially based exactly on `CBRD-26659-oos-testcases-handover`. No ticket 09 source edits. After native execution, this branch incorporates integration `d13aebf6428a68c2852d16df143d1da203d86dea`, which adds only ticket 14 C++ tests. The native receipts remain at `1ef86a7`. |
| Public TC | Base `df8596dd999e825b1ec9812a735bbe01e50ac715`. Logical oracle commit `285f231c06fb1973b0de4caf1cbf764b0cb33d4a`. Native-format correction `0dffcb424ea88539ae90861ab6cd178fc1185c73`. Branch `task/work456-09-public`, final merge commit `ae161ccea946b84b9f5a0fca384f703c2b73fa51`, includes integration `754dfffd83f7b3a14e13e8a5b965ccf4f2ae2920`. |
| Private TC | Base `5e8a9eaa885a53922826ff5320787f1115034a13`. Original 108-phase receipt `fc6d37033eff703be75ea526f267f401cd0856c1`. Constraint recreation addition `e7320251c0109a202c8ffcb7ce4f24b2534fee0b`. Failure-only diagnostics `91fc999e9ef60c9532299b3614b8f060864845ad`. Branch `task/work456-09-private`, final merge commit `02594c2f794e5b1fcb7711b9b53f4271f11a1f78`, includes integration `216d131098becb3f44056844052ca907b67dfae0`. |
| Docs | Initial main `c784cd0008f8943bf7f1b25be8bd49381d60391e`, branch `docs/work456-09`. The task branches include current integration tips at handoff. |
| Installation | Read-only source `/home/vimkim/.cub/install/work456-ticket01/optdebug`. Own immutable copy `ticket09/immutable-product`, then a new installation copy per attempt. Linux x86_64, OptDebug, 16 KiB I/O pages, `DB_PAGESIZE=16344`. Installed commit `1ef86a7`, preflight `commit_match=yes`, no mismatch exception. |
| Install manifest | `install-sha256.json`, SHA-256 `99e9fc128b2a4b8df261ce820bbfe65e17a80a3557f22de87df3d6609638cfd1`, equal to ticket 01. |
| CTP | Commit `9c62858b10005d721546cc007be260844033b9e9`, pre-existing five tracked modifications preserved. Patch SHA-256 `7cf9fb96b65838d4665cd0ee028370257aa16e26a3c07c4ea5250a942549c0dc`. Each attempt copies CTP. |
| Native runner | `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Go 1.25.0, embedded revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified build. |
| JDBC | Temurin `8.0.462+8`. CTP-provided JDBC jar SHA-256 `17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98`. The copied `System.xml` points at the attempt-local jar. |
| Manual | `CUBRID/cubrid-manual@3b6ae97bfbdc664b010ffa933ded5a05b291ae03`. |
| OOS authority | Complete normative context read, SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`. Accepted policy and ownership requirements remain independent of implementation observations. |

`gh-pr-info` identified PR 8128 on the handover checkout: head `vimkim/cubrid:CBRD-26659-oos-testcases-handover`, base `feature/oos-merge`. The own source branch has no PR. The original CCI submodule dirt remains untouched. No build directory or compile database exists in this own source checkout. These external tests reuse the exact matching installation.

The coordinator granted native slot A before initialization or database execution. `cub-workenv init --no-db` allocated master 41082, broker 41083, SHM IDs 1644167250/1644167251 and TMP `/tmp/cwe-1000/6f63ac001cff`. Each attempt owns its installation, HOME, empty registry, configuration, TMP, CTP and results. SQL uses hexadecimal broker SHM values. Explicit native SQL/shell runs use one serial slot with network, PID, IPC and mount isolation. Shell additionally uses the disposable scenario write layer. Each retained `preflight.log` identifies the exact source/install/runner and successful containment.

The controller owns its master, server and client process groups. It uses acknowledged writer phases, bounded commands, a Linux subreaper and regular daemon log files. Cleanup proves owned registry absence, database-directory absence, process-group exhaustion and configuration restoration. It does not stop another attempt or edit shared CTP/install files.

## Independent complete-value oracle

The private input model uses a deterministic SHA-256 counter stream. It writes literal SQL inputs and independent HEX byte literals before storage. The engine never generates an expected value. Large A/B keys share their entire prefix and differ in their final byte or character. C has a distinct leading marker for replacement and reinsertion. Every accepted row must match its complete expected key, fixed markers and fixed ballast.

| Domain | Input bytes | Observed serialized size | Placement design |
| --- | ---: | ---: | --- |
| VARBIT | A/B 5107, short control 1 | A/B 5112, short 4 | Only `k` is variable. Long keys S, short C. |
| VARCHAR(6001), UTF8_BIN | A/B 6001, short control 1 | A/B 5996, short 4 | Only `k` is variable. Long keys S despite the actual string representation/compression, short C. |
| CHAR(2048), UTF8_BIN | Three complete 2048-byte values | 2060 | Fixed `BIT(24000)` ballast adds 3000 bytes and cannot demote. Only indexed `k` can demote. All three keys S. UNIQUE NULL controls are C. |

The pinned manual documents string compression and `DISK_SIZE` in `en/sql/datatype.rst:1128`. Its algorithm name is historical. Pinned `src/object/object_primitive.c:14519` uses LZ4. The receipt records actual serialized sizes and flags for each combination. Input length or FORCE_OUTLINE alone never supplies S credit.

CHAR's supported maximum is 2048 for this fixture, documented at `en/sql/datatype.rst:1137–1148` and `DB_MAX_CHAR_PRECISION` in `src/compat/dbtype_def.h:601`. The rejected CHAR(6001) preparation remains in the attempt ledger. CHAR uses a variable disk representation at `object_primitive.c:12745`. Full-width input avoids trailing-pad ambiguity. The fixed ballast has its own complete zero-byte oracle.

## Support and rejection ledger

The tested support set is explicit. It does not qualify every charset, alias, generated locale or Cartesian combination.

| Combination | Required and executed interpretation |
| --- | --- |
| 72 core cells | 3 domains × DEFAULT/PREFER_INLINE/FORCE_OUTLINE × PK/UNIQUE × maintenance/build × single/composite `(tenant,k)`. Every cell proves the actual indexed attribute S. |
| Policy aliases | Omitted policy with VARBIT PK maintenance/single and PREFER_OUTLINE with VARBIT UNIQUE build/composite. Both use DEFAULT semantics. These two cells do not imply a second 72-cell cross product. |
| Ordinary prefix index | Prefix length 16 for each domain. Positive actual index lookup and range return complete A/B tail-distinct keys. |
| Rejected prefix forms | UNIQUE prefix, PK prefix and composite prefix. Each rejection preserves complete rows and creates no rejected index. Fixed INT prefix also rejects. Manual `en/sql/schema/index_stmt.rst:60` records prefix deprecation. Pinned `msg/en_US.utf8/cubrid.msg:1080–1083,1925` and `src/parser/semantic_check.c:8960–9004` identify the rejected forms and collation gate. |
| UTF8_EN_CS | VARCHAR, FORCE_OUTLINE, single PK/UNIQUE, before/after population. Real named index lookup/range/order. Uppercase A is distinct and remains complete/S. |
| UTF8_EN_CI | Same four PK/UNIQUE build/maintenance cells. Uppercase A compares equal and rejects as a duplicate. Independent HEX equality preserves original spelling. Explicit heap lookup checks key correctness. Ordinary CI prefix creation/metadata/full rows/S also pass. |
| Generic CI physical path restriction | The pinned optimizer disallows these CI predicates as key-range/filter terms. The query path is inapplicable at this revision. CI key storage, constraints and logical reads remain required and executed. No observed sequential-scan plan becomes a new golden answer. |
| Rejected indexed domains | BLOB, CLOB, JSON, SET, MULTISET and SEQUENCE reject ordinary and UNIQUE indexes. The fixed marker/NULL row and index catalog remain exact. These are rejection tests, not successful indexed OOS coverage. |
| Rejected schema combinations | Incompatible ISO88591 charset with UTF8_EN_CS, unknown collation and CHAR(6001). No rejected table remains. Accepted explicit CS/CI CAST coercion has a separate positive full-value oracle. |
| Inapplicable large OOS keys | Fixed BIT and other fixed scalar index domains cannot supply this variable-attribute OOS state. NUMERIC's serialized representation (`object_primitive.c:115–153,8665`) is at most 20 bytes, below the strict greater-than-24-byte profitability floor. These receive no large-key S credit. |
| Unselected generated collations | `utf8_ja_exp` is not installed in this baseline. The preserved probe's unknown-collation error proves environment availability only. It supplies no domain-unsupported claim or coverage credit. |

Indexability is revision-specific source evidence: [tp_valid_indextype](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/object/object_domain.c#L11214). It accepts the tested scalar key domains and rejects LOB/JSON/collections. Independent generic UNIQUE rejection evidence is public baseline `sql/_01_object/_06_index/_002_unique_index/{cases/1022.sql,answers/1022.answer:25}`. Ordinary catalog message 269 and UNIQUE template message 248 are distinct accepted rejection routes.

CI restrictions are generic collation policy. [Built-in options](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/base/language_support.c#L102) set `CI_COLL_OPTIONS={false,false,true}`. [UTF8_EN_CI registration](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/base/language_support.c#L757) uses those options and no expansion. `allow_prefix_index` stays true. [Parser collation inspection](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/parser/parser_support.c#L1283) and [optimizer term classification](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/optimizer/query_graph.c#L2418) disable key-range/filter use when `allow_index_opt` is false. Manual `en/sql/i18n.rst:89` describes collation-specific optimization restrictions. Lines 1602–1610 separately explain case-insensitive covering restrictions. Covering, key-range and prefix support are distinct claims.

The accepted CAST coercion oracle comes from public baseline `_19_apricot/_12_collation/_09_index/answers/_01_index_cs_coll.answer`. Its case contains a stale rejection comment. The committed answer requires success. The charset rejection oracle is `_24_aprium_qa/_01_i18n/issue_9403_collationperclass/{cases/05_errors.sql:6,answers/05_errors.answer}`.

## Operations, atomicity and current-row mapping

Each core cell inserts B, short, A in that order. Named index directives and the actual detailed plan accompany the same query's complete result oracle. Equality, inclusive range, ascending/descending window order, projected keys and self-join check full values. A plan alone cannot satisfy the result assertion. The core then checks committed key replacement, indexed replacement lookup, DELETE absence, surviving full keys and committed reinsertion.

The duplicate tests reject INSERT, UPDATE and a multirow INSERT whose last tuple collides. The preceding new tuple must disappear too. PK rejects NULL in either applicable component. Single UNIQUE accepts repeated NULL. Composite UNIQUE accepts distinct `(tenant,NULL)` keys and repeated all-NULL keys, but rejects a repeated identical partial-NULL key.

The independent partial-NULL oracle predates this work: public baseline `df8596dd999e825b1ec9812a735bbe01e50ac715`, `sql/_13_issues/_14_1h/cases/bug_bts_13479.sql:3–8` and `answers/bug_bts_13479.answer:16–18`. Repeating `(1,NULL)` takes duplicate-key UPDATE and yields `(11,NULL)`, beside `(2,NULL)`. Its VARCHAR pair repeats the contract at case lines 11–17 and answer lines 35–37. Original import is `d1449addb2a070abb4f45d37cdfe29df04cc4374` from 2016. This independent answer supports collision classification. Current B-tree implementation alone does not define the SQL oracle.

The writer acknowledges UPDATE of id 2, DELETE of id 3 and INSERT of id 6. It then proves its changed complete three-row model. An outside reader sees the original three rows. Rollback restores every original full key through both ordinary and index reads. SHOW preserves the exact owner tuple and original chunk count/serialized total. Actual post-rollback records retain S/C and the original physical slot identities.

Expected errors and rolled-back INSERTs can leave physical ghost slots. New markers 4/5/6/14 are distinct from preexisting 1/2/3. Post-error/rollback diagnostics select those three original markers explicitly. They require exact complete values, unique slots, `REC_HOME`, no delete id and unchanged original physical identities. They do not filter by desired flags or derive expected flags from output. A relocation, duplicate marker or unmatched value fails qualification. Positive NULL rows use markers 8/9/12/13. Committed reinsertion uses 7. DELETE absence receives no clear-flag credit.

Populated duplicate-build failures preserve all full values, S observations, nullable metadata and absence of the failed index. Existing-NULL PK build rejects without partial schema change. UNIQUE build with repeated NULL succeeds. Constraint DROP/recreate requires the same full rows and actual S/C after DROP, absent/present named index metadata, and a positive rebuilt index lookup.

These checks establish current external ownership association and rollback conservation. They do not inspect full stub identity, borrowed undo ownership, commit notifications, vacuum eligibility or page return. Tickets 14/15 retain the internal assertions for those contracts.

## Native receipts and controls

Raw root: `/home/vimkim/temp/work456-implementation/ticket09/`. `run_attempt.py` creates every fresh instance. `run-selected.sh NAME shell` or `run-selected.sh NAME sql` invokes explicit native testkit. Each attempt retains input hashes, exact expected case list, command, environment, preflight, effective config, timing, runner exit and native verification. Runner exit 0 is never sufficient: several failing runs also return 0.

Shell artifacts are `NAME/CTP/result/shell/current_runtime_logs/` plus `large_keys_evidence.tar.gz`. The archive contains commands, complete literal model, per-phase logical/physical JSON, plan output, writer acknowledgements, owner joins and cleanup. SQL artifact roots are the exact `Result Root Dir` in `run.log`. Native summary.info, summary_info, summary.xml and per-case JUnit XML agree on selection and verdict. Pinned `CTP .../ConsoleBO.java:633–650` writes `.result` on mismatch only. A successful answer comparison therefore retains XML/summary evidence rather than a fabricated `.result` copy.

| Attempt | Verdict and disposition |
| --- | --- |
| `red01` | Required controller absent, intentional native 1 FAIL. No database coverage. |
| `green01` / `green02` / `green03` | Initial observer tracer PASS, stale committed-note oracle FAIL, then first complete VARBIT cell plus referenced-key fixture PASS. These runs cover bounded slices of the final matrix. |
| `matrix01` | FAIL from reused writer bootstrap receipt in a second combination. Per-phase writer names prevent receipt collisions. |
| `matrix02` | FAIL from the initial unsupported partial-NULL assumption. Corrected from the pre-existing generic case/answer above. |
| `matrix03` | First 48 VARBIT/VARCHAR cells completed, then invalid CHAR(6001) preparation rejected. Supported CHAR(2048)+fixed ballast replaces that fixture. |
| `matrix04` | All 72 core cells, two aliases and three prefixes completed. Collation setup then failed because an INSERT named a nonexistent tenant column. |
| `extra01` / `extra02` | FAIL from the generic CI index-path assumption. Full values remained correct. The support ledger records the exact physical-path inapplicability. |
| `extra03` | FAIL from a prefix-negative test reaching an existing UNIQUE restriction first. Isolated the intended DDL target. |
| `extra04` | Uninstalled optional generated collation. No unsupported-domain credit. |
| `extra05` | FAIL from the stale generic CAST rejection comment. Corrected from its independent committed success answer. |
| `extra06` | Correct BLOB UNIQUE rejection used catalog 248 rather than ordinary 269. Corrected error-route recognition from the independent generic answer. |
| `extra07` | 1 PASS, all 22 declared domain/build/reference phases complete, 20.849 s. |
| `final01` | 1 PASS, 0 fail/skip, all 108 declared phases exactly once, 350.967 s. Original complete matrix before explicit O58 recreation. |
| `sql01` | 1 FAIL, 58.835 s. Every logical value/error matched. Native field padding differed. |
| `sql02` | 1 PASS, 0 fail/skip, 55.287 s. Oracle `0dffcb424` restores CTP's four-space column/five-space value suffix from `ConsoleDAO.java:880–901`. Logical expected tokens remain equal to pre-native `285f231c0`. |
| `final02` / `final03` | FAIL at the first post-recreated-PK CSQL connection, 22.359 / 20.863 s. ADD PK committed and owned server later stopped normally. No value mismatch or crash attribution. Preserved separately. |
| `final04` | 1 PASS, 0 fail/skip, 108 phases, 395.474 s. Every core/alias cell additionally retains full rows/S/C across constraint DROP/recreate. Earlier connection failures remain unattributed. |
| `negative-tail01` | Intentional 1 FAIL, 8.782 s. Disposable model expects B for id 2 while storage receives A. Both have identical lengths/prefix and different tails. The exact model reports 2/3 matches and native verification rejects. |
| `negative-flag01` | Intentional 1 FAIL, 9.633 s. Disposable expectation says id 2 is C. Actual complete value passes, but HAS_OOS is S. Native verification rejects and cleanup succeeds. |
| `negative-sql01` | Intentional 1 FAIL, 52.732 s. Disposable answer expects full-key Boolean 0. Actual is 1. The complete native diff contains only that value. |

The independent `final01/independent-audit.json` reconciles 108 phases, 72 core combinations, 527 physical observations containing 1601 record observations and 618 positive index query plans. It independently compares original/error/rollback/update physical identities, every full-value success marker, all owner-restoration tuples and the reference fixture. Archive SHA-256 is `ecb826c0f2add0c6882767504dce5d7a26a50f5192d8135b0af4fde96fc593f7`. The final `final04/independent-audit.json` separately reconciles 108 phases, 675 physical observations containing 2045 records, and 692 positive actual index plans. It also checks all 72 core DROP/recreate metadata/models. Final archive SHA-256 is `a7ff94d9b4f61d83553e1a304c4977f33ee930f1b968b8e0127381fe62498801`. These are observation counts, not native testcase counts or branch coverage.

## Inventory reconciliation and downstream fixture

| Assignment | Ticket 09 disposition |
| --- | --- |
| O15/O16/O18 | Large-key equality/range/ASC/DESC, projected complete keys, window order, exact aggregate model and join. Ticket 05 supplies wider relational/set/group/limit operations. |
| O39 | Existing narrow-key constraint assertions stay retained. This addition supplies actual indexed-key S beside fixed markers. |
| O57/O75 | Both PK/UNIQUE maintenance and build in every core cell. Duplicate/NULL build preservation adds 12 phases. |
| O58 | Explicit constraint removal/recreation with retained row/flag/model and named index metadata. Final receipt states the observed disposition. |
| O74/story 39 | Small and large keys remain functional. Reference diagnostics separately identify heap OOS ownership and a `BTREE_OVERFLOW_KEY` file. Exact overflow boundary neighbors remain ticket 12. |
| O76/O77 | Support/rejection ledger and actual attribute placement, complete query models and applicable real index plans. CI path limits remain precise. |
| O78 | INSERT/UPDATE/DELETE and rejected duplicate statements here. REPLACE and duplicate-key UPDATE belong to shared ticket 07. |
| O79 | Intended NULL/duplicate/atomicity, acknowledged changed writer, original outside reader, rollback full keys/flags/owner conservation. |
| O80 | Valid parent handed to ticket 10. No FK child, cascade, RESTRICT or SET NULL execution credited here. |
| C++ dispositions | Canonical inventory assigns no internal cases to 09. Zero removals/migrations or C++ replacement claims. Retained dispatch, raw fetch, identity, lifetime and reclamation assertions remain with 14/15. |

The portable parent is private TC `shell/_40_guava/cbrd_26659_large_keys/cases/reference_fixture.sql`, unchanged in tested commit `91fc999e9ef60c9532299b3614b8f060864845ad` and final merged commit `02594c2f794e5b1fcb7711b9b53f4271f11a1f78`. Exact final path/commit/hash appear in `handoff.json`. Its schema is `oos09_reference(id INT,note INT,k BIT VARYING, CONSTRAINT oos09_reference_pk PRIMARY KEY(k)) DONT_REUSE_OID`. Only `k` is variable. Its two 5107-byte keys are `a1×1701 || b2×1703 || c3×1703` and the same value with final byte `c4`.

The same invocation proves both complete keys and their current `REC_HOME` HAS_OOS flags. It also proves a real named PK lookup and full values after graceful reopen. SHOW class/HFID/OOS-VFID joins offline diagdb. Separate diagnostics identify the key-overflow file. These observations establish the parent-key prerequisites for ordinary single-node FK work. Ticket 10 must create its own fresh fixture and prove its actual child/action behavior. It must preserve full-key oracles and observer limits. The final-byte and flag controls test the initial matrix oracle only. They do not establish fault recovery or exercise every later rollback/collation assertion. All three controls use disposable copies. The authoritative SQL/answer and shell inputs remain unchanged.

No performance comparator, throughput/latency threshold, optimizer enhancement, HA replication qualification or Work463 closure is part of this delivery. The known physical target boundary and reclaim/ownership defects retain their existing owners. This report gives no immediate chain/page reclamation credit after committed DELETE or UPDATE. No source/TC push, CI, integration merge, PR closure or branch deletion occurs in ticket 09.
