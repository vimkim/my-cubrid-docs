# Work456/07: alternative writes and actual OOS records

Date: 2026-10-21, Asia/Seoul. Reader: the Work456 coordinator and ticket 16 coverage reviewer. Related PRs: [engine PR 8128](https://github.com/CUBRID/cubrid/pull/8128), [public TC PR 3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), [private TC PR 4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

This report checks whether MERGE, REPLACE and duplicate-key UPDATE preserve complete row models and actual stored OOS states. Native SQL passes 3/3. The final ten-case native shell selection has8 PASS, 2 FAIL and no skips. All 122 required ordinary/indexed checkpoints pass. Both failures isolate the accepted unassigned-attribute whole 24-byte stub contract, linked to [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230). Their values, record flags, attribute placement, owners and reopen checks pass. These failures remain enabled.

The work delivers tests for O35–O37 and the alternative-write part of O78 in the [operation inventory](supplement-operation-inventory-work456-20261021.md). It changes no engine implementation or production observation API. Test delivery is complete within this ticket. Passing coverage excludes the two conformance failures. The [approved specification](supplement-spec-work456-20261021.md) permits this distinction.

## Revisions and execution profile

| Component | Exact identity |
| --- | --- |
| Source | `5551d08fcfa2dc08b3352a71e1b4568af4f72a44`, branch `task/work456-07-source`. No source changes. Source installation and every preflight match without an exception. |
| Public TC | Initial integration `754dfffd83f7b3a14e13e8a5b965ccf4f2ae2920`. Three SQL/answer pairs added by `ceaf2638b378b5ec71a888a5e5c1d1f910c75401`, answer-format correction `d58bfa238`, current owned head `d58bfa2388852ee1e438fbbc01ab2208e3568a26`. Current local `tc/pr-8128` merged into the owned branch. |
| Private TC | Initial integration `216d131098becb3f44056844052ca907b67dfae0`. Ten entrypoints and six helpers added by `f80dc6035d779709a5b02a08a7e53668fb2237ab`. Current local integration merged, then Python 3.6 compatibility commit `ea6be4b85230a83a25f4dadf6d412f6bbe5d5c66`. |
| Build/install | Immutable provider 11 at source 5551, copied into `/home/vimkim/.cub/install/work456-ticket07/optdebug`. All 247 immutable manifest entries match. Each attempt copies this installation again. Linux, little-endian, 16 KiB I/O pages, OptDebug. Actual SHOW reports DB page size 16344. No build in this task. |
| Native runner | `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Explicit family and `TESTKIT_CONTAIN=1`. Shell serial disk overlay, exact selected file list, no retry/continuation/update. |
| Dependencies | CTP `9c62858b10005d721546cc007be260844033b9e9`, existing patch SHA-256 `7cf9fb96b65838d4665cd0ee028370257aa16e26a3c07c4ea5250a942549c0dc` preserved. JDK Temurin 8.0.462+8. Native SQL copies the CTP JDBC jar (SHA-256 `17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98`) and rewrites only the attempt's `System.xml`. |
| Authority | Complete normative OOS context,2026-10-08, SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`. Manual commit `3b6ae97bfbdc664b010ffa933ded5a05b291ae03`. |

`cub-workenv init --no-db` allocated master 41094, broker 41095, SHM 1644167262/1644167263 and TMP `/tmp/cwe-1000/721eb0b3eac3`. The coordinator granted native B before DB activity. Each attempt owns its install, empty registry, configuration, CTP, HOME and TMP. Actual native slot process observations confirm distinct network, PID, IPC and mount namespaces. Preflight and namespace receipts remain with the attempts. No host DB is created by initialization.

The isolated source has no build directory or compilation database. The matching copied installation supports execution. No result relies on LSP or an implicit build. The source branch has no associated PR. Starting-branch `gh-pr-info` and explicit PR metadata identify vimkim/cubrid, head `CBRD-26659-oos-testcases-handover`, base `feature/oos-merge` and PR 8128.

## Independent support and error oracles

| Operation | Intended contract and independent source |
| --- | --- |
| MERGE | `en/sql/query/merge.rst:13–48`: matched UPDATE, unmatched INSERT and DELETE after UPDATE are supported. DELETE evaluates the updated value. The match and survivor models are explicit in the fixture. |
| REPLACE VALUES/SET/SELECT | `en/sql/query/replace.rst:9–38`: duplicate PK/UNIQUE causes DELETE plus INSERT. Omitted columns follow INSERT defaults. New physical row incarnations are expected. |
| Duplicate-key UPDATE | `en/sql/query/insert.rst:256–307`: a hit updates the conflicting row, a miss inserts. VALUES/SET/SELECT forms accept ordinary expressions. The fixture uses CASE on existing target IDs. |
| Generic TC precedent | Public `_32_damson/cbrd_23679/_03_insert/_04_type_varbit_allow/cases/_008_varbit_merge.sql`, `_006_varbit_replace_values_set.sql`, `_007_varbit_replace_select.sql`, `_002_varbit_on_duplicate.sql` and their pre-existing answers establish ordinary syntax and behavior. They give no OOS placement credit. |
| NOT NULL | Revision5551 `msg/en_US.utf8/cubrid.msg:277,704`, messages 205 and 631. Both accepted rejection routes identify the payload's NULL assignment. |
| Constraint and size | Unique violation is independently required. VARBIT(50000) accepts the 5107/5407-byte values and rejects 7001 bytes. The OOS+REC_BIGONE rejection uses the accepted guard and current `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`, numeric -1384 at this revision. The canonical context's historical numeric -1375 is not copied as the current error number. |
| Unassigned chain reuse | Normative OOS §3, accepted 2026-08-13: unassigned attributes preserve all 24 stub bytes, including head OOS OID, full length and identity stamp. Assigned attributes and REPLACE have no such reuse expectation. |

The MySQL `VALUES(column)` function is unsupported. A development attempt used it incorrectly. Pre-existing `_23_apricot_qa/_01_sql_extension3/_03_pseudocolumn_in_default_clause/_02_insert/answers/insert_008.answer` rejects that expression with-493. The final fixture uses supported expressions. No observed defective result became an answer.

## Full models and actual record mapping

| Value | Independent complete bytes | Role |
| --- | --- | --- |
| small | `19 ab 23 cd 45 ef` | Clear-flag control |
| other | `29 bc 34 de 56 fa` | Distinguishable clear-flag replacement |
| large |1701 bytes a1,1703 bytes b2,1703 bytes c3, total 5107 | Set-flag value |
| newlarge |1801 bytes d4,1803 bytes e5,1803 bytes f6, total 5407 | Distinguishable set-flag replacement |

SQL input expressions and independent Python byte models use separate constructions. Normal SQL compares every row's ID, note and complete payload against full expected literals. PK/unique identities, exact population and exact-model population reject substituted, duplicate, missing or extra survivors. Counts, lengths and hashes alone are insufficient. The raw reader also compares every reconstructed payload byte against the independent segments.

Every ordinary form starts with C,C,S,S target rows and an untouched OOS survivor 9. It executes C→C,C→S,S→C,S→S and new C/S keys. MERGE and each duplicate-key form additionally distinguish assigned and unassigned hit/miss branches. SELECT/MERGE inputs have separately named heaps and their own full-value/flag checks. The supported MERGE DELETE removes previously proven C and S rows after note updates. Absence receives no clear-flag credit.

The all-slot diagnostic query has no row predicate. It does not hide NULL, retired or failed-write slots. `alt_check.py` extends the qualified [ticket 01 observer](ticket01-baseline-and-observer-20261021.md) and ticket 06 provenance controller. Current rows must have the exact complete model, REC_HOME and no delete ID. Ordinary UPDATE paths retain their qualified home slot. Only documented REPLACE incarnations may use new current slots. Every retired slot must match an earlier owned slot. Unknown failed-insert slots require an acknowledged failed owned statement, ended client, before/after slot sets, NULL logical/header fields, type 6/7 and an allocation bound no larger than attempted rows. They receive no HAS_OOS credit.

Persistent CSQL writers acknowledge each statement before checks. Each form executes rollback, savepoint restoration and commit. Multirow forms check statement atomicity after NULL failure. SET supports one tuple per statement, so it has single-statement rejection checks and a serial transaction schedule. All forms execute domain overflow and actual OOS+REC_BIGONE rejection. The latter preserves a plain non-OOS bigone control and creates no OOS file. The independently observed C/S target survivors, complete DDL policies, class/HFID/VFID identity and chunk totals remain unchanged after rejected writes. Chunk totals describe this schedule. They do not prove vacuum reclamation or page eligibility.

## Native receipts and coverage

Raw root: `/home/vimkim/temp/work456-implementation/ticket07`. It retains every attempt, copied configuration, environment, command, preflight, exact selection, input SHA-256 map, logs, XML, verification output and cleanup evidence. `attempt-identities.json` also pins each final effective configuration, expected-case list, command, environment and copied JDBC jar.

| Required population | Receipt | Result and scope |
| --- | --- | --- |
| Public SQL 3 | `final-sql02` |3/3 PASS,0 FAIL/skip. Ordinary SQL models only. No borrowed shell physical credit. |
| Shell 10 | `final-shell01` |10 executed,8 PASS / 2 correct FAIL / 0 skip. Both failing cases are the whole-stub regressions. Required main checkpoints 122/122 PASS. |
| Updated raw reader 2 | `final-stubs02` |Exact 2/2 correct FAIL, no missing/skip. Each required seven-assertion schedule has 6 PASS / 1 stub FAIL. This rerun is the same two cases, not two additional required cases. |
| Retained C++ 19 | Ticket 14 baseline |19/19 PASS at source 1ef, separate SA receipt and limits below. |
| Wrong flag/value | `negative-flag01`, `negative-tail01` |Each native shell case reports NOK. The important flag and complete-byte verdict mechanisms reject wrong independent expectations. |
| Wrong SQL answer | `negative-sql01` |Native SQL reports 1 NOK. Only expected exact-model population 4→3 changes. SQL inputs remain byte-identical. |
| Wrong whole stub | `stub-verdict-control` |File-based comparator control: identical input exits 0, one changed expected stub byte exits 1 while value/owner identity stays equal. This is comparator evidence, not another engine execution. |

Whole-invocation elapsed time is 66.123 s for SQL 3 and 222.303 s for shell 10. The two-case compatibility rerun takes 61.858 s. These are separate operational costs, with no performance qualification. The independent rejection audit finds exactly one expected error in each of 26 required rejection invocations.

The strict native verifier rejects the final shell selection because two cases fail, although runner status is 0. The report preserves this rejection. `main-audit.json` reconciles exact XML identities,122 phase records, complete physical JSON and owned cleanup. `stub-audit.json` reconciles both final raw-byte schedules and the exact failing comparison. No missing phase or skip is treated as a pass.

| Main shell form | Required complete checkpoints |
| --- | ---: |
| MERGE |21 |
| REPLACE VALUES / SET / SELECT |13 / 13 / 17 |
| Duplicate-key VALUES / SET / SELECT |15 / 15 / 20 |
| Indexed alternative writes |8 |

O78 uses the indexed VARBIT attribute itself as the only variable/OOS-eligible attribute. It checks actual S rows, MERGE matched/unmatched behavior, REPLACE, duplicate hit/miss, rollback, duplicate rejection and reopen. A forced named `alt_key` lookup must show an index scan of `alt_rows` and complete key equality. Stopped file diagnostics join the actual heap OOS owner and separately identify B-tree OVERFLOW_KEY. This fixture uses the validated ticket 09 model with provenance, but proves its own actual invocation. Its scope is narrower than the [complete large-key matrix](ticket09-large-indexed-oos-keys-20261021.md).

## Whole-stub conformance failures

Both fresh committed fixtures have fixed INT id/note and one VARBIT payload. No old reader or transaction rollback participates. The candidate INSERT payload differs from the retained payload, while the matched/duplicate UPDATE assigns only note.

The stopped raw seam reads existing `diagdb -d 9 --dump-records --class-name`, `diagdb -d 1`, `SELECT_RECORD_INFO` and owned volume bytes. The copied qualified 08→15 reader originally has SHA-256 `a6a2ecc0e6f1dad13ee32e2804590da2593b100b0a3982f826ace0e4291e8cdc`. Its owned copy replaces only `int.bit_count` and `Path.is_relative_to` for Python 3.6 compatibility. Final SHA-256 is `4bc934af23398d68ac2efddac9683074288a12d8dd1d1749311c44ce7faab505`. Both actual executions qualify the format, complete byte model, stored representation, OOS allocated-page owner and head stamp before comparison.

The reader accepts only plain Linux little-endian 16 KiB pages, current REC_HOME rows, the latest dumped class representation, fixed INT identities and modeled VARBIT attributes. It rejects encryption, relocation, unknown volume mapping, bounds mismatch and unsupported representations. The profile's historical d13 label describes its binary format, not the executed source identity. The actual source/install remains5551. No CHN monotonicity or unused-padding equality is invented.

The server runs normal CS vacuum settings. Only stopped diagnostic SA boots suppress vacuum, then restore configuration before server restart. Intermediate `green-merge02`, `green-all03` and `green-all05` used an unguarded diagnostic SA boot. Their later corruption/timeout observations remain retained and under triage. They do not establish an ordinary CS alternative-write defect. The final qualified observer profile passes every ordinary/indexed reopen check. Earlier helper failures in source-heap provenance, unsupported syntax, error-message routing and two-result parsing remain recorded as implementation attempts. `final-sql01` differs only by an extra terminal answer separator, corrected from the established native answer convention.

For `merge`, logical OID `[1, 641, 2]` and owner `[1, 704]` remain equal. The 5107-byte payload and serialized length 5112 remain exact. Head `[1, 706, 0]` becomes `[1, 707, 0]`, and stamp `[176, 11768]` becomes `[176, 15240]`. The full stub changes from `000002c20000000100000000000013f80000000000b02df8` to `000002c30000000100000000000013f80000000000b03b88`. This correctly fails CBRD-27230.

For `duplicate`, logical OID `[1, 641, 2]` and owner `[1, 704]` remain equal. The 5107-byte payload and serialized length 5112 remain exact. Head `[1, 706, 0]` becomes `[1, 707, 0]`, and stamp `[176, 11800]` becomes `[176, 15216]`. The full stub changes from `000002c20000000100000000000013f80000000000b02e18` to `000002c30000000100000000000013f80000000000b03b70`. This correctly fails CBRD-27230.

The two cases stay in the selected population. The existing CBRD-27230 repair scope owns this accepted reuse gap. No source repair or remote JIRA edit occurs here. Ticket 15's ordinary UPDATE/notification work remains separate. This ticket proves neither commit-notification emission nor borrowed-undo reclamation safety.

## C++ retain/add/migrate/remove

Retain 19, add 0, migrate 0, remove 0. The separate source is `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, Linux 16 KiB OptDebug with `UNIT_TEST_OOS=ON`. Baseline receipt SHA-256 is `d55d4243db537e6c8c5338ffd15d8f41429e76391f04d18990b367cbbb585b9e`. `cpp-reconciliation.json` checks the exact declared ID set against completed, unskipped, successful XML for each binary. It preserves the root's separate 29-invocation / 302-case baseline reconciliation.

| Binary/suite | Exact retained case suffixes and assertions |
| --- | --- |
| `test_oos_sql_bigone` / `OosSqlBigone` 4 | `OosColumnWithBigoneRejected`, `BigoneWithoutOosColumnSucceeds`, `OosColumnInlineBetween4kAnd16kSucceeds`, `UpdateIntoOosBigoneRejected`: exact guard error, unaffected ordinary bigone, allowed residual range and rejection preservation. |
| `test_oos_sql_txn` / `OosSqlTxn` 8 | `RollbackInsert`, `RollbackUpdate`, `CommittedDataPersists`, `RollbackMultiChunk`, `ComboThenCommit`, `RollbackDelete`, `DeleteCommit`, `DeleteRollback`: SA API transaction outcomes, survivor counts and lengths. |
| `test_oos_sql_update_delete` / `OosSqlUpdateDelete` 7 | `UpdateOosValue`, `UpdateNonOosColumn`, `RepeatedUpdates`, `SizeChangeChunkTransition`, `DeleteOosRows`, `TruncateAndReinsert`, `UpdateMultiChunk`: direct SA SQL API writes, exact selected lengths/counts, repeat/chunk/truncate lifecycle. |

The preferred test seam remains each existing module or user interface. These retained tests are not MERGE/REPLACE/duplicate-path replacements. Some assert lengths/counts rather than individual stored flags. They receive only their existing SA contract credit. New CS value/flag coverage neither deletes these assertions nor proves SA equivalence. This baseline does not become a 5551 C++ rerun or an actual 07 CS observation. The [C++ inventory](supplement-cpp-inventory-work456-20261021.md) keeps the wider disposition population.

## Delivery and remaining boundaries

New public files are the `cbrd_26659_oos_alt_merge`, `..._replace` and `..._duplicate` case/answer pairs under `sql/_36_guava/cbrd_26659`. New private entrypoints are `cbrd_26659_alt_merge`, `..._replace_values/set/select`, `..._duplicate_values/set/select`, `..._indexed` and `..._stub_merge/duplicate` under `shell/_40_guava`. Their six owned helpers live under `oos_alternative`.

Bash syntax, warning-level ShellCheck, Python syntax, task diff checks, Markdown source checks, selected relative links, README indexing and incoming-document history checks pass. Native answer trailing spaces follow the established runner format. All selected docs are substantive analysis. No raw logs or generated inventories enter Git.

Every owned database, registry entry and fixture directory is removed. Controllers restore configuration and reap owned children. Final host checks find no process from an attempt prefix. The original handover's unrelated CCI dirt and the existing five tracked CTP edits remain preserved. NativeB is released after the final controls.

No source/TC push, CI trigger, TC PR merge/closure/deletion, remote JIRA write, baseline synchronization or new Work ID occurs. The coordinator owns integration and tracker updates. Ticket 16 still owns final cross-ticket reconciliation and CI handoff. Performance and HA/replication remain deferred to their existing work, including Work463.
