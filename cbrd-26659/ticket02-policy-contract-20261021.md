# Work456/02: storage policy syntax and preservation

Date: 2026-10-21, Asia/Seoul. Reader: the Work456 coordinator and policy-test reviewers.
Related PRs: engine [8128](https://github.com/CUBRID/cubrid/pull/8128), public TC [3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), private TC [4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

This report asks whether accepted storage policy statements preserve their syntax, semantics, metadata and stored records. The new cases distinguish grammar rejection, parser semantic rejection, domain rejection and attribute-context rejection. Final SQL and shell selections pass. The separate SA storage selection also passes. No engine repair or C++ deletion belongs to this change.

## Exact identities and authority

| Component | Identity and scope |
| --- | --- |
| Engine source | `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, branch `task/work456-02-source`, worktree `work456-ticket02`. Exact starting integration HEAD. No task source changes. `gh-pr-info` found no PR for the own topic branch, as expected. |
| Integration PR | `vimkim/cubrid`, `CBRD-26659-oos-testcases-handover` → `feature/oos-merge`, PR 8128. The source integration retains its unrelated CCI dirt. |
| Public TC | `df8596dd999e825b1ec9812a735bbe01e50ac715` → `410ba5d2ce3151054b11f8443d2da9966a5eafff`, branch `task/work456-02-public`. Two new SQL/answer files. |
| Private TC | `5e8a9eaa885a53922826ff5320787f1115034a13` → `f934b56621c352df84fc7b5a7965148adb07d5ea`, branch `task/work456-02-private`. Three new shell files and one focused extension of the existing schema-policy case. |
| Installation | Immutable ticket01 Linux 16 KiB optdebug installation, copied into own prefix `/home/vimkim/.cub/install/work456-ticket02/optdebug`. Every run copies it again. All completed preflights report installed commit `1ef86a7`, `commit_match=yes`, no mismatch exception. |
| Native runner | `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Same native binary as ticket01. Go build revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified build. |
| CTP / JDBC | Asset source commit `9c62858b10005d721546cc007be260844033b9e9`, with pre-existing tracked edits preserved. Existing JDBC jar SHA-256 `17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98`. SQL attempts copy it into their own installation. |
| Java | Temurin `8.0.462+8`, same selection as ticket01. |
| Normative context | Complete read of OOS-CONTEXT dated 2026-10-08, unchanged SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`. |
| Accepted policy decisions | CBRD-26067 and CBRD-26979, fetched through `cubrid-jira` on the report date. The former's literal 16-byte wording is historical. The current canonical 24-byte stub defines the profitability floor. |
| Manual | Local manual `3b6ae97bfbdc664b010ffa933ded5a05b291ae03` contains no matching policy description. It supplies no undocumented OOS oracle. |

The accepted four spellings are DEFAULT, PREFER_OUTLINE, PREFER_INLINE and FORCE_OUTLINE. DEFAULT and PREFER_OUTLINE share current default behavior. An omitted ALTER clause preserves an eligible policy. Explicit reset clears both hint flags. An omitted clause on a compatible variable-to-fixed conversion clears an invalid old hint. All four explicit policies reject fixed-layout domains under CBRD-26979. Proposed FORCE_INLINE and fixed DEFAULT exceptions receive no acceptance credit.

At the pinned engine, [grammar alternatives and identifier echo rules](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/parser/csql_grammar.y#L10705) appear at lines 10705, 20853 and 20954. The duplicate constraint check is at `:10244`. The [eligibility helper](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/query/execute_schema.c#L8224) checks variable normal attributes of real classes. The accepted duplicate-name precedence uses `ER_SM_NAME_RESERVED_BY_ATT` (-245), with message 245 in `msg/en_US.utf8/cubrid.msg`. JDBC wrappers alone do not identify the rejection stage.

## Required and executed cases

| Native family | Selected path relative to its TC root | Assertions |
| --- | --- | --- |
| SQL, reused | `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_storage_policy.sql` | Accepted policies, CHAR eligibility, fixed/shared/class/view rejection, LIKE values, omission/reset and failed conversion preservation. |
| SQL, added | `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_policy_syntax.sql` | 76 statements. 49 intended errors, exact row models, rejected class absence, four non-reserved identifiers, ADD/CHANGE and DEFAULT/NOT NULL/COMMENT ordering. |
| Shell, added | `shell/_40_guava/cbrd_26659_policy_contract/cases/cbrd_26659_policy_contract.sh` | 38 separate rejection/preservation checks, full metadata, mixed stored records, policy copying/reset and nonretroactive clear/set rewrites. |
| Shell, reused and extended | `shell/_40_guava/cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh` | Existing unequal policy-selection, soft fallback, force/floor, omission/reset/copy, schema and owner assertions. New current REC_HOME/full-value checks connect five policy fixtures to real flags. |
| C++, retained | `OosSqlStorage.*`, 25 tests in `test_oos_sql_storage` | SA shared-DB execution, exact internal error identities and existing placement/statistics assertions. No case removed. |

Every SQL case has its committed answer. SQL uses the native JDBC executor and `test_default.xml` with autocommit true. The SQL database charset is `en_US.utf8`. Native SQL selected paths refer to disposable copied groups. Native shell uses a read-only source corpus with a writable contained scenario overlay. This report claims CS SQL and CS shell behavior. SA credit requires its separate receipt below.

The malformed clauses are missing policy, unknown identifier, numeric value, quoted value, FORCE_INLINE and `=` form. Duplicate identical and conflicting STORAGE clauses parse through the duplicate-constraint semantic check. Normal INT and fixed BIT domains reject the accepted explicit policies. CLASS and SHARED CREATE/ADD contexts and VCLASS CREATE reject them. Normal fixed ADD/MODIFY/CHANGE and CLASS MODIFY/CHANGE each receive explicit coverage. Valid policy tokens remain usable as table/column identifiers. The tests preserve their supported naming behavior.

## Independent logical, metadata and physical oracles

`C` means a current stored record with HAS_OOS clear. `S` means HAS_OOS set. These states come from stored record diagnostics. Policy and payload size do not establish either state.

The new rejection fixture is one unpartitioned heap. The only variable normal attribute is `payload`. Row 1 has `id=1`, `note=101`, `X'19ab23cd45ef'`. Row 2 has `id=2` and `note=202`. Its payload has 1,701 bytes `a1`, 1,703 bytes `b2` and 1,703 bytes `c3`. The primary key, NOT NULL/default, policy, comment, class attribute, table options and collation appear in the canonical full SHOW CREATE field.

The final initial diagnostic reports row 1 with flags 1 and row 2 with flags 9. Both have record type 2 (REC_HOME). HAS_OOS is bit 0x08. Allocated volume/page/slot IDs remain observations, not fixed expected constants.

Each rejection checks complete value equality and exactly two rows. It then checks actual diagnostic rows, flags, record types, insert/delete IDs and stable slots against the before image. Finally, it compares the complete canonical DDL field byte for byte. The metadata helper excludes only CSQL result/timing text. A count, error or policy string cannot replace these comparisons.

The shared observer requires current unrelocated REC_HOME slots, complete aliased fields, distinct logical IDs and slots, and no delete mark. Each caller supplies its full-value expression and model. These fixtures have no partitions or version readers. The report gives no relocation, old-version or partition ownership proof. Exact physical-target boundaries remain ticket12 obligations.

The nonretroactive fixture contains one 311-byte independently patterned value. Insertion and FORCE_OUTLINE ALTER leave the record C. An assigned equal-value UPDATE changes it to S. DEFAULT ALTER retains S. Another assigned equal-value UPDATE changes it to C. Both ALTER phases compare the entire stored diagnostic row with the previous phase. The fixture therefore distinguishes a metadata change from a rewrite.

The FORCE_OUTLINE floor fixture contains four exact VARCHAR values. Twenty-two characters serialize to 24 bytes and remain C. Twenty-three serialize to 28 bytes and become S. NULL and empty string remain distinct values and C records. Every row's actual state appears beside complete value equality in the same diagnostic query.

The reused policy fixtures retain independently derived unequal serialized chunk totals. DEFAULT selects the 3,500-byte candidate for one 3,532-byte chunk record. PREFER_INLINE selects the 2,500-byte ordinary candidate for one 2,532-byte chunk record. Necessary fallback selects both 5,000/1,000-byte candidates for 6,064 bytes across two chunks. New per-record observations verify S in each actual fixture. Chunk arithmetic discriminates the selected candidates. This is not a claim of direct per-attribute IS_OOS observation.

CREATE LIKE policy checks use an empty target, so their state obligation is metadata N. SQL copy values remain logical evidence for their own invocation. Ticket05 owns the broader source/destination state matrix. Metadata rejections use E: C and S pre-images remain exact. Rejection itself has no HAS_OOS flag. No absence receives clear-state credit.

## Containment and native receipt

The coordinator granted native lease A. Own `cub-workenv init --no-db` allocated master 41074, broker 41075, SHM IDs `0x6200004a`/`0x6200004b` and TMP `/tmp/cwe-1000/887b01145d81`. Every attempt uses its own copied install, CTP, HOME, registry, configuration and TMP. Runtime paths and effective overrides point into that attempt. The copied registry is archived and replaced with an empty registry before launch.

SQL uses `TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 testkit sql -c <attempt>/conf/sql.conf`. Shell uses `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <attempt>/conf/shell.conf`. Exact expected lists, dispatched/finished identities, XML, summaries, feedback, assertion logs and result files establish verdicts. Process exit zero supplies no independent PASS.

The retained harness is `/home/vimkim/temp/work456-implementation/ticket02/run_attempt.py`. Raw files remain under that ticket02 directory. The final audit records source/TC identities, input/configuration hashes, timing, native artifacts and controls. No raw logs or disposable corpus belongs in Git. `independent-audit.json` confirms every final input hash matches its TC commit. It also confirms the own installation equals the immutable ticket01 installation. The source CTP patch remains `7cf9fb96b65838d4665cd0ee028370257aa16e26a3c07c4ea5250a942549c0dc`.

| Attempt | Native verdict | Runner seconds | Meaning |
| --- | --- | ---: | --- |
| `sql01` | No native execution | N/A | Expected list order differed from sorted discovery. |
| `sql02` | No testcase execution | 102.715 | Missing install JDBC jar and stale copied JDBC path. Native setup failed. |
| `sql03` | No testcase execution | 45.054 | Decimal SHM text caused own broker setup failure. |
| `sql04` | 2 PASS, 0 FAIL | 54.024 | Earlier 68-statement syntax case and existing storage policy case. |
| `shell-red` | 1 FAIL, 0 skip | 9.715 | TDD red: metadata helper absent after mixed stored records were observed. |
| `shell-green01` | 1 FAIL, 0 skip | 9.253 | Test implementation: grammar message match was too narrow. |
| `shell-green02` | 1 FAIL, 0 skip | 18.152 | Test implementation: duplicate-name message match was too narrow. |
| `shell-green03` | 2 PASS, 0 FAIL/skip | 35.782 | Earlier 30-rejection fixture plus strengthened reused policy fixture. |
| `shell-final` | 2 PASS, 0 FAIL/skip | 40.151 | Clean committed inputs. All 38 rejection checks and five reused physical policy fixtures. |
| `sql-final` | 2 PASS, 0 FAIL | 77.956 | Clean committed inputs. 76 new statements, including 49 expected errors. 314 ms case time. |
| `negative-metadata` | 1 FAIL, 0 skip | 10.486 | Disposable wrong schema expectation fails complete DDL comparison after grammar rejection. |
| `negative-flag` | 1 FAIL, 0 skip | 10.986 | Disposable row-1 set-flag expectation fails against actual clear record. |
| `negative-sql` | 1 FAIL, 1 PASS | 52.473 | Disposable SQL answer expects 3 exact rows instead of 2. Native comparison fails the intended case. |

The shell red reached real mixed flags 1/9 before the intentional missing metadata helper. Later shell failures corrected test message matching against pinned source definitions. They are testcase implementation failures. SQL setup failures executed no accepted cases and receive no passing credit. SQL03 used decimal text for a hexadecimal broker setting. The next attempt corrected the owned configuration to the allocated hexadecimal values.

One resource error occurred: shell-red overlapped SQL02 preparation for 9.7 seconds. The coordinator received this correction immediately. Both attempts had independent contained resources. All later invocations ran sequentially under lease A.

The own environment validator reports no build directory or compile database. No ticket02 compilation or LSP-dependent claim uses this checkout. The immutable install supports its SQL/shell runs.

All three negative controls returned runner exit zero. Native verdict artifacts and the maintained verifier rejected them. The committed expected answers and models remain unchanged.

Final shell cleanup checked successful owned-server stop, native DB deletion, absent registration/directory, empty owned process groups and restored configuration. SQL cleanup stopped and deleted its attempt-owned database. Native containment ended with each runner. The own doctor reports ready and opens no database. It reports inaccessible other-user PIDs, so it proves no global inactivity claim. The coordinator received release of native lease A after the final control. There were no shared service stops, global kills, shared installation writes, pushes or CI runs.

## C++ assertion disposition

All 25 source cases remain retained. CS JDBC or shell cannot replace SA workspace/schema behavior. Raw API error identities also differ from JDBC error wrappers. Existing length-only and aggregate checks retain those stated limits. New complete-value and per-record tests supplement them.

Ticket14 supplied the separate baseline SA receipt at source `1ef86a7`. The Linux 16 KiB optdebug build enables `UNIT_TEST_OOS`. Its build and prefix are `work456-ticket14/build_preset_optdebug` and `/home/vimkim/.cub/install/work456-ticket14/optdebug`. The own runtime uses port 41080 and a private registry/TMP.

The selected binary is `test_oos_sql_storage`. The retained harness uses `ctest --test-dir <owned-build> -R '^test_oos_sql_storage$' -j 1 --output-on-failure -V --output-junit <attempt>/ctest.xml` with GTest XML output enabled. GTest reports **25/25 PASS**, zero failures, disabled tests or skips, in 0.228 seconds overall. CTest reports setup, selected binary and cleanup **3/3 PASS** in 2.25 seconds. The declaration, discovered, started and XML identity sets each contain the same 25 unique cases. Ticket02 independently reconciled those sets in `cpp-independent-audit.json`.

Raw artifacts are under `/home/vimkim/temp/work456-implementation/ticket14/baseline/test_oos_sql_storage/`: `discovered.log`, `ctest.log`, `ctest.xml` and `gtest.xml`. Shared `baseline/receipt.json` has SHA-256 `d55d4243db537e6c8c5338ffd15d8f41429e76391f04d18990b367cbbb585b9e`. Ticket14 confirmed no source edits at this baseline. Its generated CCI header dirt remains recorded separately. Every binary's before/after checks found no own-prefix/build processes. Cleanup preserved the registry's original header and the workenv configuration hash. No global-host inactivity claim follows.

This SA receipt belongs to the shared baseline campaign. Ticket14's later test additions have separate revisions and receipts. The new CS fixtures do not replace these SA cases.

| Case | Disposition | Inspected assertions | Execution owner |
| --- | --- | --- | --- |
| `OosSqlStorage.CreateTablePersistsPreferInline` | retain | CREATE succeeds. SHOW CREATE contains PREFER_INLINE. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.CreateTablePersistsForceOutline` | retain | CREATE succeeds. SHOW CREATE contains FORCE_OUTLINE and excludes PREFER_INLINE. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.DefaultColumnHasNoStorageClause` | retain | Default CREATE succeeds. SHOW CREATE excludes PREFER_INLINE only. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.ExplicitDefaultStorageClausesActAsDefault` | retain | DEFAULT/PREFER_OUTLINE CREATE succeeds. SHOW CREATE excludes PREFER_INLINE, PREFER_OUTLINE and DEFAULT. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.CreateTableLikeCopiesPreferInline` | retain | LIKE succeeds. Copied SHOW CREATE contains PREFER_INLINE. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.CreateTableLikeCopiesForceOutline` | retain | LIKE succeeds. Copied SHOW CREATE contains FORCE_OUTLINE and excludes PREFER_INLINE. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.SharedAttributeRejectsPreferInline` | retain | Three shared spellings reject with the normal-attribute message. FORCE has a separate case. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.CreateRejectsAllStorageSettingsForFixedTypes` | retain | All four INT policies and fixed BIT PREFER_INLINE reject with the variable-normal message. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.CreateAcceptsStorageForPhysicalVariableTypes` | retain | CHAR/PREFER_INLINE and VARBIT/FORCE_OUTLINE CREATE succeeds. SHOW CREATE contains both hints. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.VclassRejectsAllStorageSettings` | retain | All four VCLASS policies reject with the variable-normal message. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterRejectsAllStorageSettingsForFixedTypes` | retain | All four MODIFY INT policies and CHANGE INT/PREFER_INLINE reject with the variable-normal message. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterAddDuplicateAttributeKeepsDuplicateErrorPrecedence` | retain | Two duplicate ADD policies return raw -245. A nonduplicate fixed ADD returns the domain message. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterModifyClassAttributeReportsNonNormalAttributeError` | retain | MODIFY CLASS/PREFER_INLINE returns the dedicated normal-attribute message. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterChangeClassAttributeReportsNonNormalAttributeError` | retain | CHANGE CLASS/PREFER_INLINE returns the dedicated normal-attribute message. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterChangeClassAttributePreservesConstraintValidation` | retain | CLASS CHANGE with AUTO_INCREMENT returns raw ER_SM_INVALID_CONSTRAINT. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.ForceOutlineRejectsUnsupportedAttributes` | retain | Fixed/shared/class/view CREATE and fixed MODIFY reject with their distinct accepted messages. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterModifyAddsAndDropsPreferInline` | retain | MODIFY adds PREFER_INLINE, omission preserves it and both default spellings reset it. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterModifyPreservesAndTransitionsForceOutline` | retain | Omission retains FORCE. Hint transitions exclude the opposite hint. Both defaults clear FORCE/PREFER_INLINE. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterModifyDropsForceOutlineForFixedType` | retain | Omitted-policy fixed conversion removes FORCE and preserves numeric value 1234. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterModifyDropsPreferInlineForFixedType` | retain | Omitted-policy fixed conversion removes PREFER_INLINE and preserves numeric value 1234. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.FailedExplicitFixedTypeAlterPreservesSchemaAndData` | retain | Explicit fixed DEFAULT rejects. After abort, PREFER_INLINE remains and CAST value equals 1234. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.ForceOutlineBypassesRecordGateOnlyAboveInlineStubSize` | retain | SA stats report one file and two chunks. Lengths, disk-size floor and NULL count match. No full-value or individual-flag assertion. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.AlterForceOutlineAppliesOnlyAfterRewrite` | retain | SA stats show no file before/after ALTER, then one chunk after UPDATE. Result length is 3001. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.ForceOutlineRemainsNonReservedIdentifier` | retain | Unquoted FORCE_OUTLINE column accepts and returns integer 7. | SA shared `unittestdb`. Ticket14 receipt above. |
| `OosSqlStorage.PreferInlineColumnRoundTripsLargeValue` | retain | Both equal-size VARBIT lengths equal 6000. No full-value or demotion-order assertion. | SA shared `unittestdb`. Ticket14 receipt above. |


## Delivery and limits

Selected durable content is this report and its ticket README row. Supporting test files belong in their TC repositories. The canonical local ticket/map and work ledger remain coordinator-owned. Work109/401 historical evidence and separate SA-loaddb/deferred-write branches remain unchanged.

All ticket02 required cases are delivered and executed against their intended oracles. Final native evidence is SQL 2/2, shell 2/2 and the separate retained SA storage 25/25. Three disposable wrong-expectation controls failed at their intended assertions. No reproduced engine FAIL or unexecuted ticket02 case remains.

Focused Bash syntax, warning-level ShellCheck, Markdown source checks, exact input/identity audits and diff checks pass. The source tooling validator's missing build/compile-database limitation remains explicit.

Source, public/private TC and docs branches merged their latest local integration tips before handoff. No integration merge, remote publication, CI trigger, TC PR closure/merge or branch deletion occurred in this implementation. The coordinator owns local integration and canonical status updates. Wider boundaries, schema/partition ownership, full copy matrices and final CI remain with their approved tickets.
