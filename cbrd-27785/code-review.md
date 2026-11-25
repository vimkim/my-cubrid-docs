# PR 8299 code review

This independent review checks whether the ordinary-row read and UPDATE optimization preserves value ownership, physical layout and recovery/replication contracts. It is for the PR author and engine reviewers. No defect introduced by this patch was confirmed within the inspected scope.

Review date is 2026-11-04, Asia/Seoul. The delta verdict is `no-confirmed-findings`. Follow-up review required is **yes** for the inherited rollback/vacuum concern and the explicitly unexecuted checks below. This verdict is not a merge approval. Applicable source coverage is complete; runtime evidence is bounded by the executed tests.

## Fixed scope

| Item | Value |
| --- | --- |
| PR and issue | [CUBRID/cubrid#8299](https://github.com/CUBRID/cubrid/pull/8299), [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785) |
| Base branch | `feature/oos-merge` |
| Remote base and merge base | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Head | `4c3c8d791ee619ad61701eff9555bc9ef27d9994` |
| Binary-capable patch SHA-256 | `d41182925a1822a368da3e00314c51b75fdf2bef1871e8068f08737e9383d433` |
| Inventory | 16 text paths, 2,398 added lines, 263 removed lines. No deletion, rename, submodule or binary change. |
| Source and tests | Clean detached head. Tests come from the same engine revision. No submitted-source edit or instrumentation. |
| Specification | OOS normative specification SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`, plus the live CBRD-27785 description. |

The literal comparison was:

```sh
git diff --binary --full-index dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67 4c3c8d791ee619ad61701eff9555bc9ef27d9994
```

## Safety facts and changed behavior

The central data shapes are `HEAP_REC_LAYOUT`, the per-attribute `DB_VALUE`, grouped `RECDES` payloads, and the pending record that owns serialized values until publication. Ordinary scalar values and grouped OOS values now share the conversion loop. Layout decoding and writer sizing are reused, while OOS scratch and optional UPDATE ownership are created only where needed.

Scalar OOS resolution sets the transient-storage flag for both stack scratch and heap allocations. The converter receives COPY before scratch expires or allocated bytes are freed. Grouped values also pass COPY through the common reader before all payload buffers are released. Missing/shared attributes and equal variable offsets take the default or NULL path. Both eager callers recache their representation before grouping. The loop frees partial payloads on failure, and the synchronous continuation array keeps pointers only into a fully populated request vector. These are source arguments supported by native scalar/grouped, NULL, old-representation and 2/8/9-column tests. The executed tests cover their stated values and paths, not every type or injected failure. [Scalar and grouped ownership](https://github.com/CUBRID/cubrid/blob/4c3c8d791ee619ad61701eff9555bc9ef27d9994/src/storage/heap_file.c#L11547-L11737), [group eligibility and buffers](https://github.com/CUBRID/cubrid/blob/4c3c8d791ee619ad61701eff9555bc9ef27d9994/src/storage/heap_oos.cpp#L705-L834).

The physical target reserves four slot entries from usable nonheader capacity before division and alignment. It excludes heap unfill. Selection uses the same target for its trigger and stop and requires demotion to shrink the representation. The bigone/OOS guard dominates both legacy insertion and pending retention. Native boundary and deferred-write tests passed, including the newly crossing 4,012-byte fixture and workspace MVCC headroom. This establishes those configured page-size cases, not every possible page size. [Target and planning](https://github.com/CUBRID/cubrid/blob/4c3c8d791ee619ad61701eff9555bc9ef27d9994/src/storage/heap_file.c#L13131-L13298), [guard before publication](https://github.com/CUBRID/cubrid/blob/4c3c8d791ee619ad61701eff9555bc9ef27d9994/src/storage/heap_file.c#L14290-L14369).

The optional received owner is emplaced under the same `from_copyarea || from_workspace` predicate that permits its dereference. Its scope covers index, foreign-key and heap consumers. Ordinary server UPDATE already has an outer pending owner, and partition moves forward that owner to the destination. Existing physical UPDATE logging copies the old compact record as-is, including stubs. The inspected WAL formats and recovery dispatch remain unchanged. Native workspace, rollback, failure and committed-restart tests passed. An injected crash during partial finalization or restart undo was not run. [UPDATE owner and consumers](https://github.com/CUBRID/cubrid/blob/4c3c8d791ee619ad61701eff9555bc9ef27d9994/src/transaction/locator_sr.c#L6116-L6224).

Replication producers still send OOS items before the row. The applier inserts replica-local values, fixes local OID and identity stamp, and retains the existing row top-operation group. The target changes selection frequency, not the 24-byte stub or protocol. Native replica-helper tests exercised malformed-stub rejection, ordered fixup, and rollback of incomplete/failed groups. No live master/applier pair, promotion or failover was run. [Applier path](https://github.com/CUBRID/cubrid/blob/4c3c8d791ee619ad61701eff9555bc9ef27d9994/src/transaction/log_applier.c#L5044-L5262), [native replica helper tests](https://github.com/CUBRID/cubrid/blob/4c3c8d791ee619ad61701eff9555bc9ef27d9994/unit_tests/oos/test_oos_server.cpp).

## Coverage and verification

| Changed path or explicit path group | Primary reviewer | Evidence and disposition |
| --- | --- | --- |
| `src/storage/heap_file.c` | Systems for readers/offsets, Concurrency for grouped cleanup, Storage for sizing, Recovery for publication | All changed hunks owned. Source traced through primitive decoders, callers and undo consumers. Native OOS coverage passed. |
| `src/storage/heap_file.h` | Systems | New helper declarations and all callers inspected; debug server and standalone compiled. |
| `src/storage/heap_oos.cpp`, `src/storage/heap_oos.hpp` | Concurrency | Eligibility, ownership and partial cleanup traced; scalar/grouped and pending-value tests passed. |
| `src/storage/oos_file.cpp` | Concurrency | Stack/heap continuation threshold and request lifetime traced; grouped identity and multi-chunk tests passed. |
| `src/transaction/locator_sr.c` | HA | Received-owner lifetime, index, partition and replica consumers traced; native workspace and replica-helper tests passed. Live HA unrun. |
| `contrib/benchmarks/oos-performance/README.md`, `bench.py`, `ordinary.py`, `test_bench.py` | Storage | Complete tool source inspected, all 16 Python tests passed, synthetic comparator probes run. No new performance measurement. |
| `unit_tests/oos/sql/test_oos_sql_boundary.cpp`, `test_oos_sql_common.hpp` | Systems | Boundary and shared-helper assertions inspected and executed through the native suite. |
| `unit_tests/oos/sql/test_oos_sql_crud.cpp`, `test_oos_sql_workspace_bytes.cpp` | HA | Full changed tests inspected; their actual native cases passed. |
| `unit_tests/oos/sql/test_oos_sql_deferred_write.cpp`, `test_oos_sql_storage.cpp` | Recovery | Guard, failure/rollback and storage expectations inspected; native cases passed. |

Systems/Terra and Concurrency/Astra independently examined COPY-before-cleanup. Both found the same ownership condition, and the coordinator ran `GroupedAttributeReadsAcrossOldRepresentation`, `GroupedReadOfManyOosColumnsKeepsEveryValue`, `GroupedReadReleasesItsPayloadBuffers`, `OosFlagOnEmptyVariableFieldReadsAsNull`, pending-value tests and identity tests as part of the suite. Storage/Terra and Recovery/Astra independently examined validation-before-write and old-byte preservation. Both found the pre-write guard and unchanged old-record log path. The coordinator executed the boundary, storage, rollback and failure cases. Neither pair's agreement was treated as execution proof.

The fresh build used `debug_gcc`, C++17 and `UNIT_TEST_OOS=ON`, with separate installation, configuration, registry and allocated port. CCI is pinned by this source tree. Server and standalone binaries compiled and installed successfully. The engine and test source diff remained empty at the pinned head. Compiler, configuration and executable hashes are retained in local `evidence/build-identity.json`.

| Executed check | Actual result |
| --- | --- |
| Debug configure/build/install of the pinned head | Exit 0. |
| `ctest --test-dir /home/vimkim/gh/cb/review-pr8299-20261104/build_preset_debug_gcc --output-on-failure --verbose` under the selected runtime | 44/44 configured entries passed, exit 0. Includes setup/cleanup, SQL, workspace, vacuum, identity and existing crash-recovery tests. |
| `python3 -B -m unittest -v test_bench.py` in the pinned benchmark directory | 16/16 passed, exit 0. These use mocks for perf/server boundaries. |
| Comparator behavior replay with the reviewer's synthetic manifests | Exit 0. Rejected as a defect for the contract reason below. It is not a performance measurement. |

GNU-indent guards and exception-to-C-error handling were checked under the personal CUBRID policy. No material documented-standard violation was identified. This review did not trigger CI or reuse a historical CI pass as fresh execution.

## Candidates, inherited risk and follow-up

Confirmed delta findings are **zero**. `S8299-1`, the sole executable utility candidate, was independently replayed by the coordinator. The comparator accepted a synthetic complete manifest without capture identities. The documented gate validates selected observed conditions, not provenance authenticity, and submitted tests intentionally use such minimal fixtures. No promised rejection contract was violated, so the candidate was rejected. Invalid endpoint and excessive-spread controls returned exit 2, and a synthetic regression returned exit 1. None of these values is an engine benchmark.

The role reports also rejected concrete source hypotheses. Systems rejected four ownership/bounds hypotheses. Concurrency rejected seven lifetime/request hypotheses. Storage rejected three target/guard hypotheses plus `S8299-1`. Recovery rejected four introduced ownership/logging hypotheses. HA rejected six owner/replication hypotheses. Source disproof and passing bounded checks are distinct evidence levels.

`B1` is the inherited rollback/vacuum risk, separate from this PR. In the common base, vacuum reclaims an UPDATE's undo-image OOS references without the accepted commit-conditional ownership protocol. After rollback restores the old row, those references can be live. The normative specification requires a committed dropped-chain notification and forbids undo images as deletion sources. `vacuum.c` and `recovery.c/h` are byte-identical between this head and the base. The current source argument is evidence level 3. This review did not reproduce that scenario at the current head. The [earlier survey](https://github.com/vimkim/my-cubrid-docs/blob/0c5c05f713ca1953725743b865c7d3c14bd1272f/cbrd-27881/CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md) records a 2026-11-03 reproduction at the exact common base. Treat that as dated baseline evidence, not a fresh current-head failure. Track it through [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237) and [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230) before OOS integration.

`Q1` covers fresh ASan and read/allocation/conversion fault injection after partial grouped conversion. Source cleanup and normal native tests support the inspected paths, but those failures were not injected. `Q2` covers a loser transaction stopped during partial finalization or restart undo. Existing rollback and committed-restart tests do not cover that crash boundary. `Q3` covers a live OOS master/applier workload and failover; native replica helpers do not establish it. These remain named follow-up checks, not confirmed patch defects. The local handoff contains their conditions and commands. No fresh release benchmark, release regression suite, or all-page-size matrix was run. The review makes no measured speedup claim.

## Budget and artifacts

Five specialists shared these two PRs, using `gpt-6.1-terra` for Systems and Storage and `gpt-6-astra` for Concurrency, Recovery, and HA, all at xhigh. The user explicitly authorized best effort. The shared planning envelope was 20 minutes per specialist plus 30 coordinator minutes, 130 agent-minutes in total. It is one envelope across both reports, not 130 per PR. These are estimates, not spending caps. Actual tokens, subscription quota consumption, allowance windows and percentage compliance are unknown. No extra panel or reviewer retry was launched. The coordinator independently replayed candidate utility behavior, checked source attribution and ran the native checks recorded above. Specialist reports initially marked native verification partial because the coordinator owned those resources; this report includes the subsequent coordinator evidence.

The retained local run is `/mnt/nvme/data-5/tmp/cubrid-pr-audit-20261104T0957Z/pr8299/`. It contains `report.md`, `coverage.md`, `manifest.json`, `handoff.md`, the full patch, five specialist reports and raw evidence. The published document keeps the substantive analysis and reproducing commands; raw logs and generated inventories remain local.
