# Work456/04: utility policies, complete values and destination ownership

Date: 2026-10-21, Asia/Seoul. Readers: the Work456 coordinator and reviewers of engine PR [8128](https://github.com/CUBRID/cubrid/pull/8128). Testcase PRs: [public3688](https://github.com/CUBRID/cubrid-testcases/pull/3688) and [private4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

CS load, SA unload followed by CS load, and independent CS/SA compaction preserve the full policy/value/owner model in the recorded executions. It also separates readable output from actual stored-record state and destination ownership. Independent CS and SA compaction fixtures execute without depending on an SA loader success. Correct SA loader regressions remain failures linked to [CBRD-27424 / PR7925](https://github.com/CUBRID/cubrid/pull/7925). This report makes no combined-source acceptance claim.

## Revisions and containment

| Component | Identity |
| --- | --- |
| Engine source and immutable installation | `CUBRID/cubrid@1ef86a7efa34002e971b1b30bcf5d451e9db441b`. Own branch `task/work456-04-source`, worktree `/home/vimkim/gh/cb/work456-ticket04`, starts exactly at the handover integration tip. No source changes or source build. |
| Private TC base | `5e8a9eaa885a53922826ff5320787f1115034a13`, including the accepted ticket01 observer. Own branch `task/work456-04-private`, final implementation tip `373c16c62`. |
| Public TC | `df8596dd999e825b1ec9812a735bbe01e50ac715`. Own branch `task/work456-04-public`, no changes or new public SQL-suite receipt. |
| Documentation base | `c784cd0008f8943bf7f1b25be8bd49381d60391e`, own branch `docs/work456-04`. |
| Runner | `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Go build revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified working tree. |
| Normative context | Complete read of `OOS-CONTEXT.md`, dated 2026-10-08. Unchanged SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`. |

The [ticket01 receipt](ticket01-baseline-and-observer-20261021.md) identifies the shared read-only installation and dependencies. Each ticket04 attempt copies that installation and CTP into its own directory. No attempt modifies the shared installation. Each attempt has its own HOME, TMP, configuration and initially empty registry. Successful preflight requires `commit_match=yes`, no mismatch exception, and available containment.

The coordinator granted native slot B before execution. Commands use `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <attempt>/conf/shell.conf`. The actual native shell slot isolates network, PID, IPC, mounts, sockets and temporary storage. The scenario uses a disposable overlay. The route opens only attempt-owned databases and stops only attempt-owned processes. The existing lifecycle checks owned directory identity, registration, executable, PID generation and database name before cleanup.

The initial profile remains Linux, 16 KiB database/log pages and the matching optdebug product. The new source worktree has no build directory or compile database. That tooling limitation does not supply C++ execution credit. This report reuses the separate centralized ticket14 C++ baseline below.

## Independent oracle and physical relationship

The new utility fixtures use one unpartitioned heap with an INTEGER primary key and a named secondary tag index. The heap also has four VARBIT attributes and a NOT NULL tag default. The attributes specify `FORCE_OUTLINE`, explicit `DEFAULT`, `PREFER_INLINE`, and an omitted policy. SHOW CREATE checks each attribute independently. The normalized default and omitted forms must both omit a storage clause. Catalog attribute count, index metadata, NULLs and an actual default insertion also remain checked.

The intended values come from literal distinct hexadecimal regions. Equality checks every relevant byte. The small control contains six bytes. Ordinary and multi-chunk payloads contain 5,107 and 33,001 bytes. The preferred control contains 307 bytes. A fourth row contains a distinct 311-byte FORCE_OUTLINE value below the ordinary record gate. The expected flags are clear for ID1 and set for IDs2–4. The independent serialized model requires six chunks and 38,892 slot bytes. No length-only assertion can establish equality. `value-oracle.json` records independently calculated byte counts and SHA-256 values outside Git.

The actual `SELECT_RECORD_INFO` invocation joins each logical ID and complete value predicate to its physical volume/page/slot, record type and flags. The ticket01 observer rejects duplicate IDs or slots, deleted records, incomplete fields and non-`REC_HOME` records. A physical mismatch does not suppress independent owner or diagnostic collection. The route records those observations, then retains its failed verdict. A separate normal SELECT checks the complete live-row model. A rolled-back default insertion can leave `REC_MARKDELETED` slots with NULL attributes. The diagnostic selection targets only the independently verified live identities. Those ghost slots receive no HAS_OOS-clear credit.

SHOW identifies the actual class OID, HFID and OOS VFID. Stopped-database `diagdb` must agree with that same class/heap owner. `checkdb` requires status zero and fresh clean diagnostics. `spacedb` must succeed. These checks inspect the utility's actual source and destination. They do not transfer physical credit from companion fixtures.

The loader routes unload schema, objects and indexes, then load a fresh owned destination. They require explicit loader completion and zero failed objects. The source DROP must delete its saved OOS owner before destination validation. The CS, logged SA and no-logging SA loader routes use separate fixtures. A fourth roundtrip stops its checked source for SA unload, then uses CS load. This fixture isolates SA unload from SA loader failure. The two compact routes also use independent CS-populated fixtures, then invoke CS or SA compaction. An earlier loader failure cannot suppress either compact route.

## Execution receipts

Raw attempts remain under `/home/vimkim/temp/work456-implementation/ticket04`. Every attempt retains preflight, exact selection, effective configuration, input hashes, command/environment, runner exit, status, XML, feedback and verifier result. Runner exit zero never establishes a passing case. Final captures also retain raw case logs.

The initial `probe01` failed because the observer received a rolled-back default probe's deleted slot. `probe02` reached the utility observations but failed because its executing wrapper changed during the run. These are implementation/setup attempts, with no engine-failure or passing-coverage credit. The subsequent unchanged `tracer03` passed the exact one-case CS policy selection with zero failures/skips.

`utility10` executed all ten selected cases in 287.959 seconds. Its exact result is seven PASS, three FAIL and zero skips. It is a failed invocation. The failures are the logged SA policy load, no-logging SA policy load, and retained SA physical regression. The passing cases are CS policy load, independent CS and SA compact, retained CS utility, retained logical SA utility, owner-DROP and backup/restore. The policy/compact fixtures in this invocation contained three rows. The final fixture adds the independent force-only fourth row. That distinction prevents the earlier receipt from silently qualifying the changed inputs.

The four-row `final06` invocation used private TC `48176a10d`. It executed all six selected cases in 173.637 seconds, with three PASS, three FAIL and zero skips. Both SA loader failures are the intended physical regressions. The other failure came from an over-strict compact progress assertion. All raw logs and the failed verdict remain retained.

Targeted SA compact intentionally omits the global third phase. Pinned [`compactdb_start`](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/executables/compactdb.c#L194) sets `skip_phase3` for an explicit class list and checks it before catalog-wide work. The test incorrectly required that global phase. Commit `373c16c62` restricts the phase-three requirement to CS. It retains the SA four-object completion, both applicable phases, complete post-values, policies, individual flags and ownership assertions. This corrects a test oracle. It changes no engine behavior or data expectation.

The corrected `compact-final02` invocation used private TC `373c16c62`. It passed both compact cases with zero failures/skips in 44.280 seconds. The policy routes' data and assertions did not change in this correction. Their receipt remains the separate `48176a10d` invocation. Ticket16 must replay the complete frozen selection. These receipts do not form one passing six-case invocation.

Each case below uses `shell/_40_guava/<name>/cases/<name>.sh`. All six required routes executed. The table reports each route's accepted current outcome, with its actual invocation.

| Exact case name | Receipt | Outcome and scope |
| --- | --- | --- |
| `cbrd_26659_utility_policy_cs` | `final06` | PASS. CS unload/load, source DROP, complete destination values/policies, mixed flags and owner. |
| `cbrd_26659_utility_policy_unload_sa` | `final06` | PASS. SA unload of the checked source, CS load and the same destination checks. |
| `cbrd_26659_utility_policy_sa` | `final06` | FAIL. Logged SA load retains full values/schema, but expected stored OOS flags and owner are absent. |
| `cbrd_26659_utility_policy_sa_nolog` | `final06` | FAIL. No-logging SA load reaches the same physical failure. No-logging carries no recovery guarantee. |
| `cbrd_26659_utility_compact_cs` | `compact-final02` | PASS. Four objects, all applicable phases, six chunks/38,892 bytes, full values/policies/flags and owner after compact. |
| `cbrd_26659_utility_compact_sa` | `compact-final02` | PASS. Four objects, targeted phases one/two and the same complete post-image/owner checks. |

Independent raw-log audits check the mixed current records and six chunks/38,892 bytes in all successful source/destination phases. Both SA-loaded destinations instead report zero OOS chunks/bytes and no associated OOS owner. IDs2 and4 are `REC_HOME` with clear flags. The multi-chunk row ID3 is `REC_BIGONE` and receives no qualified `REC_HOME` flag credit. Normal SELECT still verifies all four complete values and policy/default/index checks pass. Source DROP, actual owner absence, `diagdb`, fresh `checkdb`, and `spacedb` all execute before the final physical FAIL. These failures receive no passing placement credit. Their separate engine dependency remains CBRD-27424 / PR7925 at its separate revision.

The disposable `negative-policy01` changes only the expected force policy to DEFAULT in a copied corpus. The actual source schema remains `STORAGE FORCE_OUTLINE`. Native execution records exactly one FAIL and zero skips in 8.957 seconds. Runner exit is zero, while the strict verifier rejects the case. The first-failure log names the wrong policy assertion and retains the actual SHOW CREATE output. The committed expected policy remains correct.

All final/correction/control raw case captures show empty cleanup failure lists, owned DB/registry/directory/process-group removal, and restored configuration. An independent post-run audit finds seven empty attempt registries. An additional readable-UID process scan finds no ticket04 attempt selection. Per-case lifecycle receipts and native namespace teardown provide the primary cleanup proof. Other users' unreadable processes remain outside that claim. The original handover CCI dirt remains unchanged, with version-header SHA-256 `f9766b68dab0c3f615a02cf29368396a43e887b8bc052e0fba321add407259a3`.

## Existing obligations and reuse

| Inventory obligation | Ticket04 disposition and limit |
| --- | --- |
| O05 copied defaults and policies | Utility schema serialization/load checks explicit and omitted policies, defaults, constraints and index metadata. Ticket02 retains ordinary CREATE LIKE behavior. |
| O34 owner/DROP | Retain the existing independent owner/survivor fixture. The utility policy fixture also drops its actual source before checking its destination. |
| O59 CS unload/load | Actual unload/load preserves full values, policy metadata, flags and destination owner. No external LOB-copy claim from the new VARBIT fixture. |
| O60 logged/no-logging SA load | Independent executions retain intended destination physical expectations. Readable values alone give no OOS placement credit. No-logging gives no WAL durability or stamp-uniqueness guarantee. |
| O61 compact/checkdb/diagdb/spacedb | Independent CS/SA compaction plus full post-images, metadata, flags and actual ownership. No exact packing, reclaim or OS-file shrink claim. |
| O62 backup/restore | Retain the bounded engine-volume/log destructive restore contract. External LOB payloads remain present during restore and receive no disaster-recovery credit. |
| O63 LOB locator/copy | Preserve the accepted ADR0002 locator contract and the existing separate locator fixture. Ticket05 supplies the separate audited receipt described below. OOS locator chains and external payload lifetime remain different claims. |
| O64 crash redo/undo | Reuse the exact source/scope in [Work401](coverage-additions-work401-20261016.md). Its 19-case run and separate sentinel run remain separate invocations. Utility no-logging supplies no recovery credit. |
| O65 TDE | Reuse only Work401's lazy-AES/WAL/crash/sentinel subset at its recorded identities. Existing-file NONE→AES application remains a required gap for ticket15. Coexisting NONE and lazy AES files cannot close it. |

The separately audited ticket05 `final-shell01` invocation passed three cases with zero failures/skips at engine `1ef86a7` and private TC `83524eea2`. Its actual `cbrd_26659_lob_locators` case observes seed flag1/clear, locator and copy flag9/set, and survivor flag8/set after source removal. All four observations are `REC_HOME` with complete-value predicates equal to one. Copy volume/page/slot identity survives source removal. Existing external payload content/path, destination-owner and source-file destruction checks also pass. Ticket04 independently matches the 14 LOB/helper inputs to committed `83524eea2`, XML verdict and four physical snapshots. Raw evidence stays in `ticket05/final-shell01` and `ticket04/lob-reuse-audit.json`. This remains a separate invocation and gives no unload/backup payload-copy credit.

The [prior utility report](ci-replan/delivery/12-utility-roundtrips.md) and [Work401](coverage-additions-work401-20261016.md) retain their original revisions and scope. Their passing assertions do not update the handover source to the separate SA branch. The [accepted SA decision](../cbrd-27424/sa-inline-preservation-decision-20261017.md) applies to values, meaningful headers, CHN, policy, destination ownership, transactions and buffer lifetime. Its `6a487cdb6` execution results remain separate. Unused-padding identity remains superseded.

## C++ assertion dispositions

All 82 existing declarations assigned to ticket04 remain retained and passed in the shared unchanged-source baseline. No C++ test migrates or disappears. The [complete case inventory](supplement-cpp-inventory-work456-20261021.md) supplies exact names and revision-pinned assertions. `required-cpp-cases.txt` supplies the exact shared execution selection outside Git.

Independent `cpp-audit.json` reconciles all 82 IDs against discovery logs, `[ RUN ]` markers and GTest XML. It finds exactly one execution per required ID, with no failure, skip, duplicate or missing ID. Seven targets supply these 82 cases. They belong to ticket14's 29 separate fixture-aware invocations, which contain 302 passing cases in total. This is not one 302-case invocation.

The shared source is exactly `1ef86a7efa34002e971b1b30bcf5d451e9db441b`. Its separate installation is `/home/vimkim/.cub/install/work456-ticket14/optdebug`, with `UNIT_TEST_OOS=ON` and `CMAKE_BUILD_TYPE=OptDebug`. Its own configuration/registry and TMP use master port 41080. Per-binary CTest fixture verdicts and GTest XML pass. Registry cleanup and process checks find no leaked database registrations or native processes. The build's generated CCI version-header change remains recorded. None of these facts changes the shell install's product profile.

Shared receipt: `/home/vimkim/temp/work456-implementation/ticket14/baseline/receipt.json`, SHA-256 `d55d4243db537e6c8c5338ffd15d8f41429e76391f04d18990b367cbbb585b9e`. The matching configuration and install manifests remain beside that receipt. This report's independent subset audit remains under ticket04.

| Target and declarations | Assertions retained | Why the new shell cases cannot replace them |
| --- | --- | --- |
| `test_oos_sql_storage`, 25 | Policy persistence/defaults, rejected-state preservation, eligibility/floor, nonretroactive rewrite and SA placement | External utility answers do not establish every syntax rejection, internal placement or SA SQL assertion. Shared baseline execution: ticket14. |
| `test_oos_sql_crash_recovery`, 2 | Persisted stub identity, clean SA restart and actual forked crash redo | Contained CS recovery and utility reads do not prove the SA process contract. Shared baseline execution: ticket14. |
| `test_oos_no_logging`, 1 | Logged slot reuse gives distinct stamps, unlogged reuse may repeat stamps, complete multi-chunk bytes remain readable | Actual loaddb exercises another boundary and does not expose the internal stamps. Shared baseline execution: ticket14. |
| `test_oos_remove_file`, 8, and `_server`, 7 | File destruction, cache/isolation, page reclaim, active-LSA deferral and sticky first page | External owner disappearance does not prove internal page/horizon behavior. SA and SERVER remain distinct. Shared baseline execution: ticket14. |
| `test_oos_server`, 36 | Protected owner enumeration, publication/reset/error state, allocation faults, replica fixup, batching and read bytes | Utility success cannot replace injected faults or replica-local publication contracts. Shared baseline execution: ticket14. |
| `test_oos_tde_gate`, 3 | User-data recovery-index classification and metadata-only negative control | This classifies WAL. It neither proves ciphertext nor replaces existing-file encryption application. Shared baseline execution: ticket14. |

Engine source stays unchanged. No engine/TC push, CI trigger, integration merge, TC closure or branch deletion occurs in this ticket's implementation. The required existing-file TDE gap remains outside this report's passing coverage. The 82 internal passes do not close that missing application proof.

## Delivery and remaining requirements

The private TC delta contains six native entrypoints, the policy controller, and a library route in the existing utility controller. Source and public TC remain unchanged. All task files pass Bash syntax, warning-level ShellCheck and Git whitespace checks. The report and README pass the Markdown source check and relative-link checks. Raw logs, helpers for independent audits and complete input/configuration manifests remain outside Git. The only selected documents are this report and its README index row.

Ticket04 supplies every new required utility route and preserves the intended engine failures. Its 82 retained internal cases also executed and passed. The existing-file TDE application requirement remains explicitly assigned to ticket15. It must not become unsupported or PASS because the present utility controls cannot reach it. No statement here completes all of Work456 or combined-source integration. The coordinator owns ticket status, local integration and ticket16's final replay/publication gates.
