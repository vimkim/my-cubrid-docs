# PR7925 ticket 02 acceptance evidence

Ticket 02 source and private runtime acceptance passed at `1932b3ec3d1b83bec83b7de1a6dd482f3a03b63d`: 38/38 configured OOS CTests and 374/374 actual cases, with no failures, skips or disabled cases. Both independent source review axes passed and measurements completed. The coordinator owns independent review and private integration. Shared prerequisite integration remains external; this report does not close the whole specification or work item 292.

## Identities and scope

- Worktree: `/home/vimkim/gh/cb/pr7925-02-record-owner`.
- Branch: `task/pr7925-02-record-owner`.
- Assigned, clean starting base: `b59f243fd0f30bb94344558ffa1755c37c43d2d4`.
- Accepted prerequisite: `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`, verified as an ancestor. The entire `src/storage` tree is unchanged from that prerequisite (`dependency-storage.diff` is empty).
- Original PR7925 head: `1c660d22e4340ee707336ad08c8b4bf4b69744de`; whole-PR review baseline: `fb567a629cdb390fff920542173fa36f454c74a0`.
- `gh-pr-info` reported no PR for this private branch, as expected. `AGENTS.user.md` was absent. Personal CUBRID, source/transaction, approved spec/ticket, handoff, accepted owner designs, OOS context and LOB ADR guidance were read. The stale source-root AGENTS.md was not loaded.
- Two scoped commits change only `src/transaction/locator_sr.c`: `9ba5e42ad6dfaa74cc9062f6fe55a459ba088924` removes duplicate ownership/conversion, and `1932b3ec3d1b83bec83b7de1a6dd482f3a03b63d` preserves current inline workspace records. Combined delta: 24 insertions and 110 deletions. No storage owner, shared header/interface, test source, CMake, policy, allocator implementation, threshold or persisted format changes.
- Final locator source SHA-256: `e292ade0df72742d660a21f85ba29f00c65e340490350c765256f89d9896495a`. The first commit hash is separately retained in `source-control.sha256`.
- All 21 comparison, 13 utility/workspace and 36 dependency cases remain unchanged. The comparison hash remains `adc506598e3e69e4346e2392611b95cb00dbda8c060f9e3260e42f90c305feb6`. Test/storage hashes and fixed diffs are retained separately.

## Why an additional owner is unnecessary

`locator_finalize_oos_record` already calls the accepted `heap_prepare_oos_record`, borrows the enclosing `heap_pending_record received` through `converted`, and finalizes after destination selection. Both INSERT and nonmoving UPDATE initialize that owner before error jumps. Moving UPDATE forwards the original owner/origin to destination INSERT, which performs the same adaptation. Actual workspace flush and multi-update callers arrive as copy-area input.

The legacy workspace helper was redundant. INSERT ran it after received-owner preparation/finalization: an OOS row exited immediately, while an inline row allocated/converted/discarded a cached copyarea without changing the active row. UPDATE ran it before received-owner preparation: it eagerly wrote chains that the received adapter then resolved and rewrote as fresh destination chains. The first chains were no longer referenced by the stored row.

The delta removes that helper, its two call sites, separate workspace RECDES/copyarea declarations, and manual frees. It retains one existing owner instead of introducing a class or substituting another generic descriptor. The existing copyarea allocator/cache and necessary foreign-key scratch ownership are unchanged. Surviving foreign-key scratch still releases before received-owner destruction, as on the base. Only redundant workspace allocation/conversion/release disappears.

The existing helper receives both origin booleans and selects preparation with `from_copyarea || from_workspace`. INSERT still extracts `LC_FORCE_FLAG_FROM_WORKSPACE`; the public defaulted signature (`from_copyarea=false`, `pending=nullptr`) therefore continues to request conversion when that flag alone is supplied. Nonmoving UPDATE uses the same selection. Moving UPDATE preserves the workspace origin and owner forwarding. The force enum, signature and other flags are unchanged. This source audit preserves meaningful origin semantics without adding a test of boolean/private-helper structure or another manual-serialization seam. The second commit retains the existing allocator but promptly releases unused conversion memory as described below.

## Preserved behavior and limitations

The accepted owner retains compact record/payload allocations; only its borrowed view is active in force processing. Redirection follows successful preparation. Destruction releases memory and does not restore an active pointer, so a later foreign-key replacement remains active. Heap/index/OOS rollback stays in the existing caller transaction/top-operation scopes; no destructor performs database undo.

CHN/current MVCC header restoration and `copy_lobs=false` stay in prerequisite `heap_prepare_oos_record`. Existing raw insertion/movement, failing UPDATE and MVCC-source checks cover preservation of caller bytes and headers. A bounded standalone no-demotion branch requires explicit workspace origin, no supplied pending owner, both source/prepared HAS_OOS flags clear, and equal source/prepared representation IDs. The prepared ID is the destination's current ID, stamped by `heap_prepare_oos_record`, so old representations retain adaptation.

That branch leaves the original RECDES and active pointer untouched. It finalizes the unused received inline view once, retaining publication reset/error propagation, then releases only its local record buffer with existing `set_external_buffer(nullptr, 0)` and `set_record_length(0)` APIs. It clears the unused converted view and calls the existing disk validator on the original row; validation adds no preparation or publication. The received owner is already finalized with zero payloads, and a supplied/borrowed owner cannot enter this branch. SERVER copy-area input keeps received adaptation because heap processing can grow/mutate MVCC headers. Old representations, existing OOS input, and any newly selected OOS value also keep received adaptation. This distinguishes preserved original workspace bytes/CHN from the prerequisite's necessary current-representation rebuilding; no inherited allocator or storage API is changed.

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
| First committed-source build/install (`9ba5e42ad`) | PASS | `build-committed.log` |
| First committed full suite (`9ba5e42ad`, historical after repair) | 38/38 CTests, 374/374 actual cases in 32 XMLs, 391.02s, zero failures/skips/disabled | `oos-full-9ba5e42ad.log`, `cases-9ba5e42ad.json` |
| No-demotion repair build/install and format | PASS | `build-repair.log`, `formatter-repair.log` |
| No-demotion repair focus | 32/32 actual cases, 5/5 CTests, 58.34s; zero failures/skips/disabled | `focused-repair.log`, `cases-repair-focus.json` |
| Final committed-source build/install (`1932b3ec3`) | PASS | `build-repair-committed.log` |
| Final configured OOS suite (`1932b3ec3`) | 38/38 CTests, 374/374 actual cases in 32 XMLs, 348.55s; zero failures/skips/disabled. All 70 baseline identities retained, including 21 comparisons and 13 utility cases. | `oos-full-final.log`, `cases-final.json`, `verification-final.json` |
| Independent integrated focus (`1932b3ec3`) | 5/5 CTests, 70/70 actual cases (36 dependency + 21 comparison + 13 utility); zero failures/skips/disabled. All 70 baseline identities retained. | coordinator `focused-integrated-1932b3ec.log`, `coordinator-focus-1932b3ec.json` |
| Independent full XML/log audit (`1932b3ec3`) | Same 38/38 CTests and 374/374 cases; no missing baseline identity | coordinator `coordinator-full-1932b3ec.json` |
| Independent Standards/Spec review (`1932b3ec3`) | Standards: 0 breaches/0 actionable smells; Spec: 0 remaining source findings/0 scope creep. | `reviews/final/standards.md`, `reviews/final/spec.md`; originals in coordinator docs evidence |

The four unchanged base failures were count assertions in `LoaderPreservesForwardAndBackwardReferences`, `WorkspaceUpdateRollbackCommitAndDelete`, `WorkspaceUpdatePreservesExternalLobFiles`, and `PartitionMovementTransfersOwnership`; values/references/file observations passed. Each passed after removal of duplicate conversion. The control also passed `RawCopyAreaRoutesInsertAndMovementWithoutChangingPayload`, `RawClientUpdatePreservesUnassignedValuesAndRollsBackFailure`, `SerializedPreparationPreservesMvccAndOutlivesSource`, and `InternalAndAddressReservationsBypassPreparation`. This is a direct red/green control for duplicate preparation, not a chain-reuse implementation. No prerequisite/base repair or test relaxation was needed. The repair focus contains 21 comparisons, six dependency controls and five utility controls; it is 32 cases, not another all-70 run.

Baseline failed DBs remain at `/home/vimkim/tmp/cubrid-workspace-oos-MgSSTA`, `/home/vimkim/tmp/cubrid-workspace-oos-6eV16a`, `/home/vimkim/tmp/cubrid-workspace-oos-1bS3R3`, and `/home/vimkim/tmp/cubrid-workspace-oos-88DIyv`. Their paths/output are preserved in the baseline receipt.

The initial independent Spec review found that the first commit always selected the received view even when the standalone current row remained inline, retaining an unused buffer until force exit. This was inherited on actual copy-area inputs but also affected flag-only input. The second scoped commit addresses that resulting conformance gap with the bounded branch above. Its proposal and final source passed independent review; the first commit's passing runtime/performance receipts are historical, not substitutes for final-revision checks. No private owner/destructor test or manual third serialization was added.

## Measurements

The legacy benchmark script was inspected before use. Its Release/native-deletion lifecycle was not run. Evidence-only `benchmark.py` uses this ticket's debug installation, selected configuration/registry/TMP, installation-use lock and CLI-owned wholly internal databases, retaining all DBs. Three ordered before/after samples each load 50,000 48-byte rows or 5,000 5,000-byte OOS rows. Every sample checks exact logical values and expected OOS chunk counts before dropping its table. Fixture bytes/configuration and row counts are the same across revisions. The script does not add a runtime-improvement or no-logging recovery claim.

All 18 completed baseline/first-commit/final-repair measurements passed exact value and OOS-count verification. Baseline elapsed/user CPU medians are small 3.92/2.51s and OOS 7.40/4.63s; final repaired medians are small 3.63/2.28s and OOS 6.73/4.06s. First-commit medians (historical) were small 3.47/2.22s and OOS 7.72/4.74s. Baseline/final repaired elapsed ranges overlap: small 3.76–4.71/3.55–4.22s and OOS 6.43–7.76/5.61–7.50s. Final OOS user CPU ranges 3.99–4.77s versus baseline 4.57–4.70s. No reproducible regression beyond noise was observed; apparent faster medians are not an improvement claim. OOS INSERT already skipped the old helper on the base, so its necessary allocation/conversion remains the same. These are three sequential debug samples per configuration, taken baseline then first commit then repair; the coordinator deferred runtime testing during repaired measurements. This is limited regression screening, not a statistically controlled Release benchmark. Both `benchmark-summary.json` and `benchmark-summary-final.json` explicitly identify `baseline` (b59), `historical_first_commit` (9ba), and `final_repair` (1932), with raw samples, identical fixture hashes, configuration and receipt folders. The historical invocation used script argument `final`; its archived folder is `benchmark-9ba5e42ad/`, and the retained `benchmark-final.log` is an alias of that historical receipt, not the repaired result. Final samples are in `benchmark-repair/` and `benchmark-repair.log`.

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

The install remains `/home/vimkim/.cub/install/pr7925-02-record-owner/debug_gcc`; selected registry is `<worktree>/.cub-workenv/databases/databases.txt`. Build, workenv, benchmark DBs, failure DBs, TMP, allocation, logs and branch/worktree remain for coordinator inspection. The final read-only inventory and selected metadata copies are in `retained-inventory.json`, `ignored-top-final.txt`, `ignored-all-final.txt`, and `selected-workenv/`. No process/IPC/socket/install/database cleanup is performed by this ticket.

The final repair used the same per-file formatter/build workflow, then the selected 32-case filter recorded verbatim in `focused-repair.log`, followed by:

```sh
git add -- src/transaction/locator_sr.c
git commit -m '[CBRD-27424] Keep current inline workspace records on force'
direnv exec . just build
direnv exec . sh -c '"${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-build-coordinator.sh" installation-use 300 -- python3 /home/vimkim/tmp/pr7925-ticket02-evidence/benchmark.py repair'
git rebase review/pr7925-combined
direnv exec . env GTEST_OUTPUT=xml:/home/vimkim/tmp/pr7925-ticket02-evidence/gtest-full/ just --justfile /home/vimkim/tmp/pr7925-ticket02-evidence/ctest.just selected '^(oos_|test_oos|test_byte_span_writer)'
```

The repaired rebase onto private `9ba5e42ad` was again a no-op between native operations (`rebase-repair-private.log`). Source/owned CCI were clean and hash unchanged. The coordinator then fast-forwarded the private branch to the exact final `1932b3ec3` commit. No existing PR, shared/default branch, push, CI, remote comment, JIRA or publication operation was performed.

## Final retained-artifact and cleanup receipt

`verify-final.py` and `verification-final.json` confirm the final task tip and authorized private integration tip both equal `1932b3ec3d1b83bec83b7de1a6dd482f3a03b63d`, source/owned CCI statuses are empty, the sole ticket file is `src/transaction/locator_sr.c`, the accepted storage tree is unchanged (`5e5ce98d080cde6749f5ab418f59f7acbdcf8490`), and the diff check passes. XML audit preserves every baseline identity. Source and build/install receipts identify the final revision; `binary-receipt-final.json` hashes selected installed engine/native test artifacts. Earlier full/performance results remain separately archived. The stable evidence is hashed in `evidence-manifest.json`.

```sh
python3 /home/vimkim/tmp/pr7925-ticket02-evidence/audit.py /home/vimkim/tmp/pr7925-ticket02-evidence/gtest-full /home/vimkim/tmp/pr7925-ticket02-evidence/cases-final.json
python3 /home/vimkim/tmp/pr7925-ticket02-evidence/inventory.py
python3 /home/vimkim/tmp/pr7925-ticket02-evidence/verify-final.py
python3 /home/vimkim/tmp/pr7925-ticket02-evidence/seal-evidence.py
```

The selected allocation is master port 41042, broker port 41043, broker shared-memory IDs 1644167210/1644167211, and TMP `/tmp/cwe-1000/9c03679608bb`. Seven benchmark DB registrations remain: one harness-oracle failure plus two databases per completed revision. Their data/log/LOB paths and createdb logs remain under `.cub-workenv/ticket02-benchmark/`; the failed overlong-name directory also remains. Three fixture directory/LOB remnants (`unittestdb`, `oosnologdb`, `oosrecoverydb`) remain after the fixtures' own cleanup, with no current fixture registrations. Four baseline failed utility databases and their data/files are retained at the paths above. The inventory records file sizes, modes, timestamps and symlink destinations without following personal stow symlinks or copying database volumes. No ELF core was identified among core-named files in the selected worktree build, workenv, install, TMP or four retained failure roots; this makes no claim about other host paths.

Ignored outputs include 15,794 build files, 76 workenv files, 15 Gradle files, personal configuration symlinks, `csql.access`, `csql.err`, and the formatter backup `src/transaction/locator_sr.c~`. The backup is inventoried and retained; final source is committed and separately hashed. Native benchmark loader logs are preserved in `native-loader-logs/`. Ignore rules were not changed, and no meaningful source change is hidden.

The final `cub-workenv doctor` exits 1 because seven benchmark Unix socket entries are stale or unconfirmed. It also reports inaccessible host PIDs, so absent owner evidence cannot establish inactivity. The read-only doctor output and scoped TMP metadata are preserved. No socket, process, IPC, DB, install, task branch or worktree deletion is eligible from that evidence alone. The parent explicitly requested retention for inspection; cleanup must remain separate and use established ownership evidence. Ticket source and private runtime work are ready; shared prerequisite/partition acceptance remains the coordinator's external gate.
