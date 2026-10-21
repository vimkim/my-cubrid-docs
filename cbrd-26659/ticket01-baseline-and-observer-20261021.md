# Work456/01: baseline and stored-record observer receipt

Date: 2026-10-21, Asia/Seoul. Reader: the Work456 coordinator and implementers of local tickets 02–16. Related PRs: engine [8128](https://github.com/CUBRID/cubrid/pull/8128), public TC [3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), private TC [4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

The product `SELECT_RECORD_INFO` observer passed the required mixed-record tracer through native shell execution. It connects complete logical values to real stored `REC_HOME` slots and separates physical presence from transaction visibility. Two disposable wrong-expectation controls failed at their intended assertions. The [83-operation population](supplement-operation-inventory-work456-20261021.md) and [complete C++ inventory](supplement-cpp-inventory-work456-20261021.md) assign remaining obligations to approved tickets. Ticket 01 adds no engine repair or production observation API.

## Exact baseline and dependencies

| Component | Exact identity and scope |
| --- | --- |
| Handover source and installation | `1ef86a7efa34002e971b1b30bcf5d451e9db441b`. Source worktree `work456-ticket01`, branch `task/work456-01-source`, created from exactly `CBRD-26659-oos-testcases-handover`. No production/source test changes. Installed `cubrid_rel` reports `1ef86a7`, with native preflight `commit_match=yes` and no exception. |
| Private TC baseline → new case | `5c9d8de1a916ae0acbddc8409770b51fd31da13b` → `5e8a9eaa885a53922826ff5320787f1115034a13`, own worktree/branch `work456-ticket01` / `task/work456-01-private`. Three shell files only. |
| Public TC | `df8596dd999e825b1ec9812a735bbe01e50ac715`, clean `tc/pr-8128`. No public edits or fresh SQL-suite run. |
| Separate SA-loaddb source | `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f`, PR 7925. Its historical evidence stays separate. |
| Separate deferred-write source | `4a4d069c21fc19f14337efceca512b726724ecd8`, PR 7927. No result imported into this baseline. |
| Current local source destination | `feature/oos-merge` at `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2`. Its newer integration state does not change this tracer's source. |
| CCI | Gitlink `79d0888c26a2543d31f53eb7b6c9738db110fff4`. Build preparation generated `win/cci_version.h` dirt. Its SHA-256 is `f9766b68dab0c3f615a02cf29368396a43e887b8bc052e0fba321add407259a3`. Original checkout dirt remains preserved. |
| CTP assets | `9c62858b10005d721546cc007be260844033b9e9`, with five pre-existing tracked edits. Raw patch SHA-256: `7cf9fb96b65838d4665cd0ee028370257aa16e26a3c07c4ea5250a942549c0dc`. Full source-asset hash manifest SHA-256: `7e3bf66b244398a17dc29c87efb523f6c8b10e8b75beba081a260b39b311de00`. CTP supplied assets, while native testkit ran the case. |
| Native runner | `cubrid-testkit dev`, binary SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Go build: revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, `vcs.modified=true`, Go 1.25.0. Version label alone is insufficient. |
| JDK / copied JDBC asset | Temurin `8.0.462+8`, release-file SHA-256 `0aef67a7d4bd29979b949a570cb3e04a376e1fbbfa87a5959354c5d453032ee3`. Copied CTP JDBC jar SHA-256 `17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98`. This tracer executes CSQL, so it gives no JDBC coverage. |
| Normative context | Complete read of OOS context dated 2026-10-08. SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`, unchanged across the read. |

The product build uses Linux, 16 KiB database/log pages and the checked-in `optdebug` preset (`CMAKE_BUILD_TYPE=OptDebug`). Configure, full build and installation succeeded through the maintained preset-aware workflow. The OOS environment validator passed after selecting the preset and creating the compile-database link. The product preset leaves `UNIT_TEST_OOS` disabled. The **302 declarations / 29 source-registered binaries** therefore remain **unexecuted C++ inventory**, with no fresh C++ PASS claim.

The own installation prefix is `/home/vimkim/.cub/install/work456-ticket01/optdebug`. Its complete hash manifest has SHA-256 `99e9fc128b2a4b8df261ce820bbfe65e17a80a3557f22de87df3d6609638cfd1`. Key binaries/libraries and JDK/CCI/JDBC identities are retained in `dependencies.json`. `source-dependency.patch`, `ctp.patch`, `initial-identities.json`, CMake/configuration hashes and build logs remain with the raw receipt.

## Resource containment and run configuration

The coordinator granted the exclusive native slot before initialization or DB execution. `cub-workenv init --no-db` selected only the own optdebug installation. Its allocation is master port 41072, broker port 41073, broker SHM IDs 1644167240/1644167241, TMP `/tmp/cwe-1000/7790d6321838`, and the own `.cub-workenv` config/registry. No host database was created or opened.

Every invocation copied the installation and CTP into a fresh attempt, preserved the copied registry directory separately, and created an empty attempt-local registry. It also used its own HOME, TMP, configuration and scenario overlay. Install/CTP paths in PATH and LD_LIBRARY_PATH were rewritten. Runtime config overrides were removed from the later attempts. The first red attempt retained an own-worktree broker-config override, but opened no broker and used native containment. It did not touch a shared installation or registry.

The command was `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <attempt>/conf/shell.conf`. Effective config selected one slot, `scenario_disk=on`, exact `testcase_from_file`, file feedback, no retry/continuation/update, and no macro exclusions for the exact selection. The shell source remained read-only to the run, with writes in the disposable overlay. The existing lifecycle/runtime helpers owned the DB directory/inode/registration and subreaper process groups. Daemon stdin/output used bounded owned launchers and regular-file logs. Framework service/IPC cleanup ran inside native containment.

The one selected case is `shell/_40_guava/cbrd_26659_record_flags/cases/cbrd_26659_record_flags.sh`. Final config SHA-256 is `07ab3c4aa2b820bad1baefbfe71faf58b513a86925420bae7a2bddb260b5e6db`. Final expected-list SHA-256 is `2ba63d17f3ed1e0218165f4e0aa33c32446de17f5ffc795f049b7eb514b7e220`. Final testcase/helper manifest SHA-256 is `e593a132ac86bcde83bdb45825ce9a1a022970adc722ca05cc0cd6c90c391700`, and every listed input matches the clean TC commit.

The DB was stopped/deleted, its registration and owned directory disappeared, all owned groups were empty, and configuration was restored. Native artifacts contain cleanup assertions in all six attempts. The final doctor was read-only and found the own environment ready. It reported inaccessible PIDs from other users, so it supplies no global-host inactivity claim. The coordinator accepted release of the native slot after the controls finished.

## Independent value and physical-state oracle

The fixture creates one unpartitioned heap, `flags_mixed(id PRIMARY KEY, note, payload BIT VARYING)`. The only variable attribute is `payload`. Row 1 has literal `X'19ab23cd45ef'` and note 101. Row 2 has note 202 and a distinguishable 5,107-byte value: 1,701 bytes `a1`, 1,703 bytes `b2`, then 1,703 bytes `c3`. Row 3's uncommitted value is 5,407 bytes across `d4/e5/f6`, with note 303.

Every relevant byte is compared by SQL equality against the input model. Counts support the exact row model and cannot replace it. The physical query projects that same full-value equality beside aliased `t_volumeid`, `t_pageid`, `t_slotid`, `t_rectype`, `t_flags`, `t_insid` and `t_delid`. The observer rejects incomplete/duplicate fields, duplicate rows/slots, wrong note/value, unexpected type, delete-marked records and wrong HAS_OOS states. It also checks that the initial rows share one physical page. Existing row-to-slot identities stay the same when the third physical slot appears.

In final execution, the initial current slots were:

| Logical row | Stored slot `(volume,page,slot)` | Record type | Flags / HAS_OOS | Full values |
| --- | --- | --- | --- | --- |
| id 1, note 101 | `(1,641,1)` | 2 (`REC_HOME`) | 1 / clear | Exact equality 1 |
| id 2, note 202 | `(1,641,2)` | 2 (`REC_HOME`) | 9 / set | Exact equality 1 |
| id 3, note 303, uncommitted writer | `(1,641,3)` | 2 (`REC_HOME`) | 9 / set | Exact equality 1 in physical diagnostic |

These allocated IDs are observations, not golden constants. The test independently requires valid distinct slots and relational identity. Row 3 has insert ID 6 while the original rows have insert ID 5. Acknowledged writer INSERT leaves row 3 uncommitted. Another ordinary SELECT sees exactly rows 1 and 2, while `SELECT_RECORD_INFO` sees all three physical records. The writer then rolls back, and ordinary SELECT again returns the exact original two-row model. Committed DELETE of row 2 leaves exactly row 1. That absence receives no clear-flag credit.

At the pinned source, [reserved-name binding](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/parser/name_resolution.c#L5884) permits normal attributes beside record-info fields. [heap_get_record_info](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/storage/heap_file.c#L20710) extracts the slot type and stored header flags before value resolution. [heap_next_record_info](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/storage/heap_file.c#L20835) scans physical slots. Expanded copies and aggregate SHOW data do not supply this proof.

## Native verdicts and controls

All paths below are relative to `/home/vimkim/temp/work456-implementation/ticket01/`. Each attempt retains preflight, effective config, expected list, environment, input hashes, command, process status, timing and native result artifacts. The result root is `<attempt>/CTP/result/shell/current_runtime_logs`. The maintained verifier checked exact positive dispatch/finish sets, status, feedback, XML and assertion logs. A separate XML/input/cleanup audit is retained in `independent-artifact-audit.json`.

| Attempt | Native case verdict | Runner time | Meaning |
| --- | --- | ---: | --- |
| `red01` | 1 FAIL, 0 skip | 7.884 s | TDD red: required observer helper absent. Real diagnostic query already showed mixed stored flags and full values. |
| `green01` | 1 FAIL, 0 skip | 8.253 s | Observer parser used an incorrect jq slurp option. Corrected as a test implementation error. |
| `green02` | 1 PASS, 0 skip | 8.087 s | Complete initial mixed/visibility/rollback/delete tracer passed. |
| `final01` | 1 PASS, 0 skip | 8.725 s | Clean committed inputs, stricter same-page/stable-slot assertions and printed phase evidence passed. |
| `negative-flag` | 1 FAIL, 0 skip | 9.294 s | Disposable expectation sets row 2 HAS_OOS false. Observer reports expected false versus actual true. |
| `negative-value` | 1 FAIL, 0 skip | 7.481 s | Disposable oracle changes row 1's last byte `ef`→`ee` at unchanged length. Full-value assertion reports exact_rows mismatch. |

Every runner process returned zero, including the four failed cases. The native verifier rejected every failed case using verdict artifacts. This confirms why process status alone cannot establish PASS. Controls use separate copied scenario roots. The committed case and correct expectations remain unchanged.

Bash syntax, warning-level ShellCheck and `git diff --check` passed. The engine was fully configured/built/installed without source edits. No remote publication, integration merge, legacy CTP run or CI trigger occurred.

## Reuse limits and acceptance

The shared observer `oos_common/oos_record_flags.sh` accepts one result containing current unrelocated `REC_HOME` slots, exact aliased fields and an explicit independent `{id,note,has_oos}` model. Each caller must establish complete `value_ok` equality and the transaction schedule. It does not validate relocation/forwarding identity, old visible-version chains, partition owner mapping or per-attribute IS_OOS. Tickets 06/08/09/14/15 must validate those relationships for their actual fixtures. A record flag identifies the indexed attribute only when the fixture independently excludes other eligible attributes or provides a validated per-attribute observer.

All ticket 01 acceptance items have supporting evidence. The reports preserve exact baselines, historical boundaries, operations/C++ populations, state obligations and owners. Runtime evidence connects same-heap clear/set records with logical rows, slots, types and visibility. Native verdicts and independent wrong-expectation controls passed their intended checks. No capability gap blocks this current-REC_HOME tracer. Work458/459 remain incomplete until later tickets deliver their required tests and native receipts.

The coordinator additionally found current remote TC heads behind their latest feature baselines. That is a ticket 16 publication/CI prerequisite. Ticket 01 preserves its approved source/TC baselines. Production target, partition owner, SA placement, page return and rollback/vacuum regressions retain their correct historical failure dispositions.
