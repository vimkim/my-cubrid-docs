# CBRD-26659 public SQL inventory

Research date: 2026-10-08, Asia/Seoul. This is a read-only inventory, not a test result or finalized selection. No testcase edits, builds, test execution, CI triggers, JIRA writes, publication, or ref changes were performed.

Nine historical SQL cases and nine matching answers remain recoverable in local Git. They provide useful content, DML, and transaction oracles, but **none is delivered on current `feature/oos-merge` / `tc/pr-7990`**. None executes `SHOW HEAP OOS`; historical activation evidence belongs to separate documentation-repository checkers. Reusing the SQL therefore requires current validation and a delivered activation check, not inheritance of historical passes.

The proposed additions below remain subject to the scope interview. Initial creation/debugging/validation is local with **optdebug**. The user's revised timing guidance is approximately **ten minutes for public SQL and ten minutes for private shell separately**, informally. There is no combined 600-second cap, 480-second target, or required company-worker timing limit; useful coverage must not be dropped to manufacture a budget fit.

## Revision and recovery evidence

| Repository/ref | Observed revision and significance |
| --- | --- |
| Engine investigation | `fb567a629cdb390fff920542173fa36f454c74a0`, `/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover`. Existing ` m cubrid-cci` was preserved. `gh-pr-info` found no PR for this local branch. |
| Normative context | Context repository HEAD `75f8b58674ac901d478ba60f9b2cc2fff11f66f6`; document updated 2026-09-22; SHA-256 `8b42fe41a314cca6dcdeac90d32d40b51974a11177fd14f4f2ca0d590e912dc7`. Entire [context][context] and relevant locator/Expand ADRs were read. |
| Public local `develop` | `4a7a4aed983ccc0acfef7f2d970810e434ccb29d`, clean, 24 commits behind local `origin/develop`. |
| Public origin `develop` | `3b2e782814805a278a8fb3e18de24d8bc021cf97`. Remote head and local tracking object agree. |
| Public `feature/oos-merge`, `tc/pr-7990` | Both `bdba62aee0faec05abdd861518824c69b6c1b3c5`; local and remote heads agree. |
| Public `feat/oos`, `feature/oos-m2` | Respectively `396504540fdbde32e6773c2800300f9f6ddb1c2d` and `1fdcaf93511acf0f94c71e0fdacc45e42fa34e16`; local/remote agree. Only the latter contains the CBRD-27006 original. |
| Recovered historical branch | Local `CBRD-26659-oos-testcases-handover` at `4f06f9bdd3d4d9a95ab4c471416df5875b5848dd`. No matching `*26659*` remote head was returned by origin/vk queries. |

The old physical directory `/home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659` has a broken `.git` pointer into the former `/home/vimkim/gh/tc/` location. Its **18 SQL/answer files byte-match the live Git objects at `4f06f9bdd`**. Historical links below point to that verified snapshot; Git inspection used the functioning develop object store.

Commands included `git ls-remote`, `for-each-ref`, `ls-tree`, `show`, `grep`, and revision-specific diffs. No additional testcase AGENTS instructions were found. Environment validation succeeded, but current `PRESET_MODE=debug_gcc` is not an optdebug verification. Relative to **latest origin/develop**, integration adds only two legacy SQL adaptations and two answers. Changes visible against stale local develop are not additional OOS coverage.

## Accountable inventory of the nine recovered pairs

All entries use exact prefix `sql/_36_guava/cbrd_26659/`: `cases/<basename>.sql` and `answers/<basename>.answer`, at historical ref `4f06f9bdd`. All eighteen paths are absent from current develop, origin/develop, feat/oos, feature/oos-merge, and tc/pr-7990. “Reuse” describes useful source assets, not a current pass.

| ID / exact basename | Observable behavior and deterministic expectation | Disposition and remaining limitation |
| --- | --- | --- |
| P01 `cbrd_26659_oos_rep02_largest_first` [SQL][p01s] / [answer][p01a] | Inline 1000/500-byte comparator and 3000/1200-byte demotion candidate. Disk/octet/bit lengths, independently calculable MD5, equality; final rows/exact/alias = **2/2/0**. | **Reuse and strengthen.** Smaller-first demotion produces the same logical answer. Add a controlled physical discriminator; the header explicitly acknowledges this false positive. |
| P02 `cbrd_26659_oos_rep06_lob_neighbours` [SQL][p02s] / [answer][p02a] | 4200/3000-byte payloads, 300-byte tag, four BLOBs and one CLOB. INSERT SELECT copies remain readable after source DELETE. | **Reuse.** Locators need not themselves demote beside the large payload. Add legal locator-heavy success and later reclamation checks separately. |
| P03 `cbrd_26659_oos_sql01_insert_select` [SQL][p03s] / [answer][p03a] | Deterministic 1..1000 helper; bulk100/bulk1000 and 100-row copy. Expected totals **455350/4147025 bytes**, distinct digests **100/1000**, matching row-by-row lengths/content. | **Reuse.** Keep VALUES, INSERT SELECT and copy-destination activation distinct. The two bulk sizes are scale levels of one family, not separate features. |
| P04 `cbrd_26659_oos_sql02_mixed_chunks` [SQL][p04s] / [answer][p04a] | 3500/20000/3500 and 3600/21000/3400-byte rows; update first to 3700/22000/3300. Length, MD5, equality, two rows, zero aliases. | **Reuse.** Already strengthens the CBRD-27006 original; do not double-count it. Equal 3500-byte candidates deliberately have no prescribed attribute winner. Logical output alone does not prove topology. |
| P05 `cbrd_26659_oos_sql02_update` [SQL][p05s] / [answer][p05a] | Payload/tag-only changes, three/fifty updates, single→20000-byte→single, subquery and join UPDATE including inline→large. Final rows/source-value/alias/distinct tags = **2/2/0/2**. | **Reuse and strengthen.** Add multi→inline, NULL/empty, self-assignment/unassigned preservation and rollback combinations. The answer does not freeze always-new-chain behavior. |
| P06 `cbrd_26659_oos_sql05_delete` [SQL][p06s] / [answer][p06a] | PK and payload-predicate DELETE, untouched survivors, delete-all/reinsert, TRUNCATE/reinsert. Final rows/exact/distinct/alias = **4/4/4/0**. | **Reuse.** Row absence and reuse do not prove chain/page reclamation. DELETE rollback, snapshots and post-vacuum survival remain gaps; SA eager and CS MVCC differ physically. |
| P07 `cbrd_26659_oos_sql06_constraints` [SQL][p07s] / [answer][p07a] | PK/secondary UNIQUE INSERT errors **-670**, NOT NULL **-631**, whole three-row statement cancellation. Existing rows/exact/distinct = **2/2/2**. | **Reuse and strengthen.** NULL payload failure is not a positive OOS fixture. Add UPDATE failures, rejection controls and subsequent successful DML; verify current unique-error configuration. |
| P08 `cbrd_26659_oos_sql06_rollback` [SQL][p08s] / [answer][p08a] | Committed fixture; INSERT+UPDATE rollback, UPDATE rollback, savepoint preserving 4600-byte value while discarding later 4700-byte/new-row writes, then COMMIT. | **Reuse and strengthen.** Immediate undo is covered; DELETE/multi-chunk rollback, vacuum after abort, crash undo and orphan absence are not. Same-connection post-COMMIT SELECT is not restart durability. |
| P09 `cbrd_26659_oos_sql06_triggers` [SQL][p09s] / [answer][p09a] | Fixture precedes triggers; AFTER UPDATE digest log/mirror, BEFORE UPDATE REJECT **-517**, unchanged value/log/mirror, INSERT-trigger round-trip. | **Conditional reuse.** Header documents pinned client-template OOS bypass. Triggered INSERT gets no OOS credit. Revalidate pre-trigger activation and the current path. |

P01 declares handwritten provenance; eight other headers declare one-time generation followed by hand maintenance. `35c815943..4f06f9bdd` changes comments only: statement bodies and answers agree. Provenance labels do not authorize deriving correctness from observed engine output.

## Other relevant assets and duplicates

- **Current legacy pair:** `bdba62aee` contains `sql/_13_issues/_14_1h/cases/bug_bts_10516.sql` and `sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql`, with matching answers. They reject the 1000 non-NULL LOB row with **-1384**, then insert a sparse row to continue copy/update/delete. Their main DML bodies duplicate each other; transaction/cleanup wrappers differ. Preserve compatibility coverage, but count one OOS workload family. `bug_bts_10516` explicitly drops all four tables, whereas `fbo_ddl02` ends by dropping only `allcolumn_t4`. Sparse success is not locator-heavy OOS success. [First SQL][lob1s] / [answer][lob1a], [second SQL][lob2s] / [answer][lob2a].
- **Original mixed fixture:** `feature/oos-m2@1fdcaf935` contains `sql/_36_guava/cbrd_27006/cases/cbrd_27006_oos_ha_repl.sql` and its matching answer. P04 already reuses it with stronger content checks. The SQL itself has no replica connection, convergence wait or comparison; its HA name is insufficient replication evidence. Its LENGTH answers use a different unit from byte sizes. [Original SQL][ha].
- **Schema candidate:** docs revision `69560cf51e7833d09c33621d1dab98902d4a727b` contains `cbrd-26659/oos-schema-change/cbrd_26517_oos_schema_change.sql` and `.answer`: reorder/add/drop, rewrite, precision/nullability, hard default, dropping a large attribute and growing inline data. **Port and strengthen**, adapting csql syntax/output to native SQL. The report lacks an exact engine/build/page/runtime identity and physical proof, so it supplies scenarios, not current validation. [SQL][schema], [report][schemareport].
- **Neighboring read cases:** origin/develop has `sql/_16_index_enhancement/_12_descending_index_scan/cases/_04_overflow.sql` and `_13_index_grouping/cases/_010_index_grouping_10.sql`, with answers. Local oos-ctp has `.sql.disable` snapshots. Compressible long VARCHAR and comparisons of only the first 20/10 characters neither establish activation nor catch tail corruption. Treat these as path references, not verified exclusions. [Descending][desc], [grouping][group].

This enumerates **15 SQL files**, with original/P04 and the two legacy bodies duplicating workloads. ADR-0002 names `bug_xdbms3693` as the canonical locator bounds regression, but that named public path was not found in the inspected current refs; its absence from other suites/private repositories is not established. [Locator ADR][adr2].

## Required physical-oracle corrections

1. **Recalculate 16→24-byte headers.** Current stub/chunk headers include identity stamps. Stats sum complete slot record lengths. A 4200-byte VARBIT serializes to 4208 bytes: its single chunk contributes **4232**, not old **4224**. P01's 3000-byte value derives **3032**; P04 row1 derives `20008+3508+3×24 = 23588`. These are source-derived expectations, not observations; logical DISK_SIZE does not gain the chunk-header bytes. [Stub][stub], [chunk][chunk], [stats][stats], [old 4224 spec][oldspec].
2. **Control the observation.** Stats conditionally latch pages and silently skip busy/deallocated pages, accepting undercount. Use owned fresh fixtures and quiescent phases with bounded stable-observation checks; missing output/fields and parse errors fail. Do not freeze OIDs/VFIDs/page allocation in answers. SHOW is DBA-only. Aggregate count/length is not identity, ownership or liveness proof. [Skip contract][statsskip], [SHOW columns/permission][show].
3. **Deliver activation with the selected run.** Separate VALUES/copy/UPDATE/trigger premises. Current source still uses trigger presence to determine server eligibility; current runtime bypass remains unexecuted here. A documentation-only checker is not delivered CI coverage. [Current routing][trigger], [historical path-specific checks][updatechecks].
4. **Preserve conformance gaps.** Normative target is **4060 bytes**, floor is serialized value **>24 bytes**. Current trigger and stop still use raw `DB_PAGESIZE/4`; historical fixtures deliberately avoid this disagreement band. Current oversize macro is **-1384**, whereas the context retains an older numeric -1375: bind symbol and number to revision. [Target][target], [trigger/stop][gate], [error macro][err].

**Delivered assertion feasibility:** no existing portable public-SQL physical assertion was identified. At engine `fb567a629`, `SHOW HEAP OOS OF table` is a standalone statement; FROM subqueries accept SELECT/VALUES expressions, so `SELECT stable_fields FROM (SHOW ...)` is unsupported by the checked grammar. The manual's neighboring HEAP CAPACITY syntax is likewise standalone. Native testkit source `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0` compares the complete CQT rendering after removing only CR/LF. The inspected CQT parser has no result-column masking directive, and its renderer emits every column; number normalization applies only to SHOW TRACE. Existing public HEAP cases exercise errors, not stable physical projections. This is source inspection, not runtime verification of the installed binary/CQT jar. [Grammar][showgrammar], [subquery][subquerygrammar], [manual][showmanual], [comparison][nativecompare], [parser][cqtparser], [renderer][cqtrender].

Raw SHOW before DROP would capture the actual SQL phase but leaves volatile IDs in its golden answer. A proposed **delivered private shell placement companion** can instead execute a fixture copied from an exact public revision, recording its hash, build/page/configuration, DML route and transaction phases; inspect stable SHOW fields before cleanup; apply the corrected 24-byte oracle; and fail missing output, parse errors or mismatched positive/negative controls. Its own native shell verdict must count as delivered coverage. **A paired fixture proves that fixture/configuration's placement premise, not physical observation of the actual public SQL execution.** Credit public logical and shell physical checks separately. Observing the actual SQL run requires an explicit pre-cleanup observation seam or a validated SQL assertion helper; neither is established here, and post-run inspection cannot recover already dropped tables.

## Proposed strengthen/new families

| Family | Existing reach | Proposed completion |
| --- | --- | --- |
| Gate/floor/representation | P01 distant comparator | **New:** physical-target boundary, next aligned size, unfill independence, serialized floor, VOT widths, exhausted-candidate valid slotted rows. Small VARBIT prefix/alignment means logical 24 bytes is not serialized floor24. [Serializer][serializer] |
| Demotion/policy | P01 unequal values; P04 tie | **Strengthen/new:** physical largest-first discriminator, eligible smaller inline, many attributes, PREFER_INLINE priority/fallback; accepted FORCE_OUTLINE small-row bypass, stub floor, NULL and ALTER/DDL round trip. [Policy][policy], [source][force], [accepted issue contract][forcecontract] |
| Chunks/transitions | P04 mixed, P05 single/multi | **Strengthen:** exact capacity boundaries, distinct head/middle/tail patterns, 3+ chunks/50KB, non-byte-aligned values, shrink/NULL/empty and rollback combinations. |
| Failure/bigone/undo | P07/P08 and legacy rejection | **Strengthen/new:** DELETE/multi-chunk rollback, UPDATE constraints, failure followed by success, INSERT/UPDATE bigone rejection preserving prior row; non-OOS bigone and intermediate-size success controls. [Pre-insert guard][guard] |
| Read/schema/type paths | DML reads and docs schema | **New/port:** heap/index projection, joins/subqueries/sort/group/aggregate, prepared/bind, CTAS/view/client fetch, schema/partition rewrites, legal locator-heavy copy; activation for each relevant path. [Expand ADR][adr3] |
| Lifetime and infrastructure | No restart/second session/vacuum/replica in nine SQL files | **Private shell responsibility:** snapshots, rollback-after-vacuum, identity reuse/retry, reclamation, restart/crash, HA and utilities/TDE. Immediate P08 success does not catch recorded CBRD-27237. [Known defect][defect] |

CBRD-26067 is **Resolved/Fixed with an accepted FORCE_OUTLINE contract**, as documented in the issue inventory. Its omission from OOS-CONTEXT is a documentation-completeness gap, not unresolved scope. Current source defines 25 storage-policy tests, including the 24-byte floor discriminator; these are scenario references, not executed proof or substitutes for delivered placement checks. [Issue evidence][forcecontract], [C++ floor fixture][forcefloor].

## Layout, validation and runtime limits

Keep `cases/*.sql` / matching `answers/*.answer`, deterministic ordered content/counts and externally calculable digests. Do not promote the first actual result to expected output or encode known defects as successful expectations. Existing neighbors use explanatory headers, EVALUATE groups and explicit cleanup; `.answer_cci` variants exist elsewhere but none in these nine pairs. Restore parameters, trace, autocommit, triggers and helper tables. [Neighbor example][neighbor], [pre-run oracle][oracle].

Future validation uses native testkit, explicit `TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1`, copied attempts and one slot. Exact positive expected/executed identities, complete summary/main/XML/results and zero failures/skips establish the verdict; exit0 alone does not. Testkit configuration and install/source identities must be checked before running; no implicit CTP fallback. [Native SQL contract][native].

All timings below are **historical local measurements**, not estimates for current native/optdebug or company CI. The recorded host is dev2, **80 logical CPUs/251GiB**, not the company 8CPU/64GiB worker. [Measurement record][measure].

| Exact provenance | Recorded cost and qualification |
| --- | --- |
| `inv-T17-0002`,2026-09-18; engine `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`; testcase `35c81594333c49e4faf8b645d2019cfca8aa1422`; release_gcc_nounit/16KiB/CS/CTP, nine cases. [Manifest][t17] | Sampler whole **111.83s**, rounded manifest window110s, launcher44s, SQL bodies **661ms**. Whole includes wrapper setup/restore and paired checker databases. Do not mix clocks. |
| Same invocation, attempts `att-T17-0002` through `0010` | P01..P09 respectively **51,47,231,28,115,48,38,37,66ms**, totaling661ms. Body timings exclude per-case setup. [Representative attempt][attempt] |
| `inv-T17-0001`, same engine/build/page/mode, P01 alone | Sampler52.3s, launcher43s, body55ms; historical fixed-launcher cost, not a native forecast. [Timing report][timereport] |
| Ticket19 release series,2026-09-15 | Launcher40–55s; final bodies1099ms; first all-PASS whole114s, final whole137s as checker phases increased. [Operations report][opsreport] |
| `inv-T47-0001`,2026-09-19 | Prose launcher43s; manifest120s window. **Manifest testcase is35c815943**, while prose names4f06f9bdd, committed Sep21 with comment-only changes. Cite executed manifest identity rather than claim a new 4f pass. [Manifest][t47] |
| Current engine/optdebug/native/delivered selection | **Unmeasured and unexecuted.** Historical public debug suite was explicitly not run; shell/configuration debug multipliers are not SQL optdebug estimates. [Limitation][timereport] |

The old 7.33s/check figure is `(110−44)/9`, not nine independently timed checker invocations. Legacy, schema-port and additional-family current costs are unknown. Measure the completed local SQL set with runner/setup/cleanup included, separately from shell, and report gaps alongside the passing selected set. Developers remain responsible for **creating and validating both public SQL and private shell**; this inventory finalizes neither selection nor publication destination.

[p01s]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_rep02_largest_first.sql:66
[p01a]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_rep02_largest_first.answer:12
[p02s]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_rep06_lob_neighbours.sql:58
[p02a]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_rep06_lob_neighbours.answer:18
[p03s]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql01_insert_select.sql:96
[p03a]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql01_insert_select.answer:70
[p04s]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql02_mixed_chunks.sql:63
[p04a]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql02_mixed_chunks.answer:40
[p05s]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql02_update.sql:81
[p05a]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql02_update.answer:186
[p06s]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql05_delete.sql:60
[p06a]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql05_delete.answer:114
[p07s]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql06_constraints.sql:67
[p07a]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql06_constraints.answer:20
[p08s]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql06_rollback.sql:48
[p08a]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql06_rollback.answer:93
[p09s]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql06_triggers.sql:79
[p09a]: /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql06_triggers.answer:86
[context]: /home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:3
[adr2]: /home/vimkim/gh/cubrid-oos-context/docs/adr/0002-oos-lob-locator-demotion.md:1
[adr3]: /home/vimkim/gh/cubrid-oos-context/docs/adr/0003-oos-expansion-is-opt-in.md:1
[target]: /home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:96
[policy]: /home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:142
[defect]: /home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:475
[stub]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/base/object_representation.h:474
[chunk]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/oos_file.hpp:32
[stats]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/oos_file.cpp:3899
[statsskip]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/oos_file.cpp:3880
[show]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/parser/show_meta.c:388
[trigger]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/execute_statement.c:12446
[gate]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/heap_file.c:12840
[err]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/base/error_code.h:1785
[serializer]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/base/object_representation.h:2340
[force]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/heap_file.c:12819
[guard]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/heap_file.c:13801
[lob1s]: https://github.com/CUBRID/cubrid-testcases/blob/bdba62aee0faec05abdd861518824c69b6c1b3c5/sql/_13_issues/_14_1h/cases/bug_bts_10516.sql#L3424
[lob2s]: https://github.com/CUBRID/cubrid-testcases/blob/bdba62aee0faec05abdd861518824c69b6c1b3c5/sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql#L3422
[ha]: https://github.com/CUBRID/cubrid-testcases/blob/1fdcaf93511acf0f94c71e0fdacc45e42fa34e16/sql/_36_guava/cbrd_27006/cases/cbrd_27006_oos_ha_repl.sql#L5
[desc]: https://github.com/CUBRID/cubrid-testcases/blob/3b2e782814805a278a8fb3e18de24d8bc021cf97/sql/_16_index_enhancement/_12_descending_index_scan/cases/_04_overflow.sql#L18
[group]: https://github.com/CUBRID/cubrid-testcases/blob/3b2e782814805a278a8fb3e18de24d8bc021cf97/sql/_16_index_enhancement/_13_index_grouping/cases/_010_index_grouping_10.sql#L22
[neighbor]: https://github.com/CUBRID/cubrid-testcases/blob/3b2e782814805a278a8fb3e18de24d8bc021cf97/sql/_36_guava/cbrd_26431/cases/cbrd_26431.sql#L1
[schema]: ../oos-schema-change/cbrd_26517_oos_schema_change.sql
[schemareport]: ../oos-schema-change/oos-schema-change-report.md
[oracle]: ../campaign/evidence/ticket19/expected-oracle.md
[oldspec]: ../campaign/evidence/ticket19/activation/cbrd_26659_oos_sql01_insert_select.spec
[updatechecks]: ../campaign/evidence/ticket19/activation/cbrd_26659_oos_sql02_update.spec
[native]: /home/vimkim/.agents/skills/cubrid-test-sql-run/SKILL.md:1
[measure]: ../campaign/evidence/ticket17/measurements.json
[t17]: ../campaign/evidence/ticket17/inv-T17-0002.json
[attempt]: ../campaign/evidence/ticket17/att-T17-0004.json
[timereport]: ../campaign/CBRD-26659-representative-timings-tier-placement_f4299ac_claude.md
[opsreport]: ../campaign/CBRD-26659-sql-operations_f4299ac_claude.md
[t47]: ../campaign/evidence/ticket47/inv-T47-0001.json
[lob1a]: https://github.com/CUBRID/cubrid-testcases/blob/bdba62aee0faec05abdd861518824c69b6c1b3c5/sql/_13_issues/_14_1h/answers/bug_bts_10516.answer#L14
[lob2a]: https://github.com/CUBRID/cubrid-testcases/blob/bdba62aee0faec05abdd861518824c69b6c1b3c5/sql/_15_fbo/_02_qa_test/answers/fbo_ddl02.answer#L12
[showgrammar]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/parser/csql_grammar.y:7473
[subquerygrammar]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/parser/csql_grammar.y:18677
[showmanual]: /home/vimkim/gh/cubrid-manual/en/sql/query/show.rst:1110
[nativecompare]: /home/vimkim/gh/cubrid-testkit/main/internal/runner/sqlsuite/compare.go:8
[cqtparser]: /home/vimkim/CTP/sql/src/com/navercorp/cubridqa/cqt/common/SQLParser.java:76
[cqtrender]: /home/vimkim/CTP/sql/src/com/navercorp/cubridqa/cqt/console/dao/ConsoleDAO.java:873
[forcecontract]: /home/vimkim/gh/my-cubrid-docs-cbrd-26659-ci-replan/cbrd-26659/ci-replan/issue-inventory.md:113
[forcefloor]: /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/unit_tests/oos/sql/test_oos_sql_storage.cpp:658
