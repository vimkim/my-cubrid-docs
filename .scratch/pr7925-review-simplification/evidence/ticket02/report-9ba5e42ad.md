# PR7925 ticket 02 acceptance evidence

Source fixed at `9ba5e42ad6dfaa74cc9062f6fe55a459ba088924`; final runtime and performance verification are in progress. The coordinator owns independent review and private integration. This report does not close the whole specification or work item 292.

## Identities and scope

- Worktree: `/home/vimkim/gh/cb/pr7925-02-record-owner`.
- Branch: `task/pr7925-02-record-owner`.
- Assigned, clean starting base: `b59f243fd0f30bb94344558ffa1755c37c43d2d4`.
- Accepted prerequisite: `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`, verified as an ancestor. The entire `src/storage` tree is unchanged from that prerequisite (`dependency-storage.diff` is empty).
- Original PR7925 head: `1c660d22e4340ee707336ad08c8b4bf4b69744de`; whole-PR review baseline: `fb567a629cdb390fff920542173fa36f454c74a0`.
- `gh-pr-info` reported no PR for this private branch, as expected. `AGENTS.user.md` was absent. Personal CUBRID, source/transaction, approved spec/ticket, handoff, accepted owner designs, OOS context and LOB ADR guidance were read. The stale source-root AGENTS.md was not loaded.
- Only `src/transaction/locator_sr.c` changes: 7 insertions and 110 deletions. No storage owner, shared header/interface, test source, CMake, policy, allocator implementation, threshold or persisted format changes.
- Final locator source SHA-256: `7e4ff41d770d24f634fca3374a3b36bd55c5b718e959cae11f3066f2be3b151f`.
- All 21 comparison, 13 utility/workspace and 36 dependency cases remain unchanged. The comparison hash remains `adc506598e3e69e4346e2392611b95cb00dbda8c060f9e3260e42f90c305feb6`. Test/storage hashes and fixed diffs are retained separately.

## Why an additional owner is unnecessary

`locator_finalize_oos_record` already calls the accepted `heap_prepare_oos_record`, borrows the enclosing `heap_pending_record received` through `converted`, and finalizes after destination selection. Both INSERT and nonmoving UPDATE initialize that owner before error jumps. Moving UPDATE forwards the original owner/origin to destination INSERT, which performs the same adaptation. Actual workspace flush and multi-update callers arrive as copy-area input.

The legacy workspace helper was redundant. INSERT ran it after received-owner preparation/finalization: an OOS row exited immediately, while an inline row allocated/converted/discarded a cached copyarea without changing the active row. UPDATE ran it before received-owner preparation: it eagerly wrote chains that the received adapter then resolved and rewrote as fresh destination chains. The first chains were no longer referenced by the stored row.

The delta removes that helper, its two call sites, separate workspace RECDES/copyarea declarations, and manual frees. It retains one existing owner instead of introducing a class or substituting another generic descriptor. The existing copyarea allocator/cache and necessary foreign-key scratch ownership are unchanged. Surviving foreign-key scratch still releases before received-owner destruction, as on the base. Only redundant workspace allocation/conversion/release disappears.

The existing helper now receives `from_copyarea || from_workspace`. INSERT still extracts `LC_FORCE_FLAG_FROM_WORKSPACE`; the public defaulted signature (`from_copyarea=false`, `pending=nullptr`) therefore continues to request conversion when that flag alone is supplied. Nonmoving UPDATE uses the same selection. Moving UPDATE preserves the workspace origin and owner forwarding. The force enum, signature and other flags are unchanged. This source audit preserves meaningful origin semantics without adding a test of boolean/private-helper structure or another manual-serialization seam.

## Preserved behavior and limitations

The accepted owner retains compact record/payload allocations; only its borrowed view is active in force processing. Redirection follows successful preparation. Destruction releases memory and does not restore an active pointer, so a later foreign-key replacement remains active. Heap/index/OOS rollback stays in the existing caller transaction/top-operation scopes; no destructor performs database undo.

CHN/current MVCC header restoration and `copy_lobs=false` stay in prerequisite `heap_prepare_oos_record`. Raw caller copy-area bytes remain intact; existing raw insertion/movement, failing UPDATE and MVCC-source checks cover this. Small/no-demotion rows use the same prerequisite adaptation that was already present on the base. The removed helper previously returned its input unchanged in that case; the delta adds no rewrite or header change. Do not confuse preserving original caller bytes and CHN with the prerequisite's already-existing current-representation rebuilding: this ticket does not claim to eliminate that inherited adaptation/allocation.

Metadata/root/address exclusions, existing OOS-input adaptation, reserved OIDs, references, storage selection, locator-byte OOS eligibility, LOB file-copy exclusions, ordinary bigone and OOS+bigone rejection remain on the accepted paths. No SA suppression of received ownership is introduced. Logged failure/ignored-duplicate cleanup, successful no-logging loading, SQL and CS loader behavior retain their existing tests. Fresh-workspace-LOB INSERT and failed-unlogged recovery remain excluded.

Private partition passes are interim. Final shared partition acceptance requires PR7927 integration into `feature/oos-merge`, recording both actual source identities. Future squash transplant and source/shared/remote promotion are coordinator-owned separate operations; this ticket does not authorize them.

## Verification

The approved test seams are actual SQL/workspace writes and stored observations plus real standalone loader/CSQL callers. This already-green refactor retains their assertions; no failure was manufactured and no private destructor/member test was added.

| Revision/run | Result | Receipt |
| --- | --- | --- |
| Base configure/build/install | PASS, debug_gcc, fresh owned CCI clone | `configure-baseline.log`, `build-baseline.log` |
| Explicit workenv `--no-db`, reconfigure | PASS, dedicated install/registry/TMP | `init.log`, `configure-workenv.log` |
| Unchanged base focus | 70 actual cases; 66 pass, 4 fail; zero skips/disabled. 4/5 CTests, 198.77s | `focused-baseline.log`, `cases-baseline.json`, `gtest-baseline/` |
| Control build/install | PASS | `build-control.log` |
| Control focus | 8/8 actual cases, 4/4 CTests, 52.67s; zero failures/skips/disabled | `focused-control.log`, `cases-control.json`, `gtest-control/` |
| Per-file GNU indent and diff check | PASS; no unrelated formatter changes | `formatter.log`, `control.diff`, `commit.log` |
| Exact committed-source build/install | PASS | `build-committed.log` |
| Final configured OOS suite | Pending | final receipt to be recorded |
| Independent Standards/Spec review | Coordinator running reviews against fixed commit | coordinator-owned evidence |

The four unchanged base failures were count assertions in `LoaderPreservesForwardAndBackwardReferences`, `WorkspaceUpdateRollbackCommitAndDelete`, `WorkspaceUpdatePreservesExternalLobFiles`, and `PartitionMovementTransfersOwnership`; values/references/file observations passed. Each passed after removal of duplicate conversion. The control also passed `RawCopyAreaRoutesInsertAndMovementWithoutChangingPayload`, `RawClientUpdatePreservesUnassignedValuesAndRollsBackFailure`, `SerializedPreparationPreservesMvccAndOutlivesSource`, and `InternalAndAddressReservationsBypassPreparation`. This is a direct red/green control for duplicate preparation, not a chain-reuse implementation. No prerequisite/base repair or test relaxation was needed.

Baseline failed DBs remain at `/home/vimkim/tmp/cubrid-workspace-oos-MgSSTA`, `/home/vimkim/tmp/cubrid-workspace-oos-6eV16a`, `/home/vimkim/tmp/cubrid-workspace-oos-1bS3R3`, and `/home/vimkim/tmp/cubrid-workspace-oos-88DIyv`. Their paths/output are preserved in the baseline receipt.

## Measurements

The legacy benchmark script was inspected before use. Its Release/native-deletion lifecycle was not run. Evidence-only `benchmark.py` uses this ticket's debug installation, selected configuration/registry/TMP, installation-use lock and CLI-owned wholly internal databases, retaining all DBs. Three ordered before/after samples each load 50,000 48-byte rows or 5,000 5,000-byte OOS rows. Every sample checks exact logical values and expected OOS chunk counts before dropping its table. Fixture bytes/configuration and row counts are the same across revisions. The script does not add a runtime-improvement or no-logging recovery claim.

All twelve measurements passed exact value and OOS-count verification. Baseline elapsed/user CPU medians are small 3.92/2.51s and OOS 7.40/4.63s; final medians are small 3.47/2.22s and OOS 7.72/4.74s. Baseline/final elapsed ranges overlap: small 3.76–4.71/3.44–3.88s, OOS 6.43–7.76/7.52–7.87s. OOS user-CPU ranges also overlap (4.57–4.70/4.58–4.88s). The OOS median differences (+4.3% elapsed, +2.4% user CPU) are within the observed spread; no reproducible regression beyond noise was established. OOS INSERT already skipped the old helper on the base, so its necessary allocation/conversion remains the same. These are three sequential debug samples per configuration, taken baseline first then final under host load; this is limited regression screening, not a statistically controlled Release benchmark or performance-improvement claim. See `benchmark-summary.json`, per-phase CSVs, fixtures, timing and command outputs.

Two harness iterations are preserved: the first database name exceeded the engine's 16-character log prefix limit; the next verifier mistook its unaliased column expression containing `VALUE_BAD` for an output result. The corrected harness uses short unique names and `AS verdict`. Existing failed storage/logs are retained; these were measurement harness failures before source edits, not engine-refactor regressions.

## Commands and retained state

Commands ran in the assigned worktree. `ctest.just` is an evidence-only filtered live recipe preserving socket preflight and `installation-use 300`; its working directory is this worktree.

```sh
just -f /home/vimkim/my-cubrid/cubrid-justfiles/justfile -d . prepare-build
cmake --list-presets=configure
direnv exec . just configure
direnv exec . just build
direnv exec . sh -c 'cub-workenv init --worktree "$PWD" --install "$CUBRID" --preset "$PRESET_MODE" --no-db'
direnv exec . just configure
direnv exec . env GTEST_OUTPUT=xml:/home/vimkim/tmp/pr7925-ticket02-evidence/gtest-baseline/ just --justfile /home/vimkim/tmp/pr7925-ticket02-evidence/ctest.just selected '^test_oos_(sql_workspace_bytes|workspace|sql_deferred_write)$'
direnv exec . sh -c '"${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-build-coordinator.sh" installation-use 300 -- python3 /home/vimkim/tmp/pr7925-ticket02-evidence/benchmark.py baseline'
bash .github/workflows/codestyle.sh src/transaction/locator_sr.c
git diff --check
direnv exec . just build
direnv exec . env GTEST_FILTER='OosWorkspaceTest.LoaderPreservesForwardAndBackwardReferences:OosWorkspaceTest.WorkspaceUpdateRollbackCommitAndDelete:OosWorkspaceTest.WorkspaceUpdatePreservesExternalLobFiles:OosWorkspaceTest.PartitionMovementTransfersOwnership:OosSqlDeferredWrite.RawCopyAreaRoutesInsertAndMovementWithoutChangingPayload:OosSqlDeferredWrite.RawClientUpdatePreservesUnassignedValuesAndRollsBackFailure:OosSqlDeferredWrite.SerializedPreparationPreservesMvccAndOutlivesSource:OosSqlDeferredWrite.InternalAndAddressReservationsBypassPreparation' GTEST_OUTPUT=xml:/home/vimkim/tmp/pr7925-ticket02-evidence/gtest-control/ just --justfile /home/vimkim/tmp/pr7925-ticket02-evidence/ctest.just selected '^test_oos_(workspace|sql_deferred_write)$'
git add -- src/transaction/locator_sr.c
git commit -m '[CBRD-27424] Reuse received owner for workspace OOS writes'
direnv exec . just build
direnv exec . sh -c '"${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-build-coordinator.sh" installation-use 300 -- python3 /home/vimkim/tmp/pr7925-ticket02-evidence/benchmark.py final'
git rebase review/pr7925-combined
direnv exec . env GTEST_OUTPUT=xml:/home/vimkim/tmp/pr7925-ticket02-evidence/gtest-full/ just --justfile /home/vimkim/tmp/pr7925-ticket02-evidence/ctest.just selected '^(oos_|test_oos|test_byte_span_writer)'
```

Build-generated tracked `win/cci_version.h` changes in this worktree's fresh CCI clone were saved exactly (`generated-cci-version-baseline.diff`, `generated-cci-version-control.diff`) and restored only there before commit. The original dirty CCI/JDBC clones were never touched. Native loader cwd logs were moved into this evidence directory, preserving their contents. No ignore rule conceals unfinished work.

After the exact-commit build and measurements finished, the coordinator requested rebase onto the frozen private integration branch at `b59f243fd0`. The rebase was a no-op, with source/owned CCI both clean and source hash unchanged (`rebase-private.log`). The coordinator then fast-forwarded that private branch to the same `9ba5e42ad` commit. No other branch was rebased, reset, merged or published by this ticket.

The install remains `/home/vimkim/.cub/install/pr7925-02-record-owner/debug_gcc`; selected registry is `<worktree>/.cub-workenv/databases/databases.txt`. Build, workenv, benchmark DBs, failure DBs, TMP, allocation, logs and branch/worktree remain for coordinator inspection. Final inventory and process/cleanup uncertainty will be recorded after tests. No process/IPC/socket/install/database cleanup is performed by this ticket.
