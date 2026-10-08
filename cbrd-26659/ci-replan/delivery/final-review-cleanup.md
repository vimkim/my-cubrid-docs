# CBRD-26659: final-review lifecycle and cleanup correction

The corrected shell selection passes **14/14 cases, zero failures/skips, all 336 required assertions and 941 mandatory artifacts** in one fresh native contained invocation. The final independent review had found that four shell companions could delete a preexisting registered database after setup failed. A second, independent Standards review identified duplicated lifecycle and checked-command code across those cases and transactions. The correction shares that code in `shell/_40_guava/oos_common/oos_lifecycle.sh` and requires explicit directory and registry ownership before destructive cleanup.

The source change is private testcase commit `f5fc1fa815fbc6eec71135f506e377c0b1096da3`, based on reviewed integration `f16dd0ba9d041cbe6c1d4486feb78108262dd2e5`. Public input, fixture values, physical models, assertion phase labels and expected results are unchanged. The source engine remains `fb567a629cdb390fff920542173fa36f454c74a0`; no engine correction is included. This report supplements [complete selected validation](14-complete-local-validation.md), whose original receipt remains intact.

## Separate review findings

The Spec finding concerned ownership: owner-drop, representation/chunks, DML transitions and read paths promoted their created state when a fixed database name appeared in the registry, even when mkdir failed and the case never created that directory. Native slot containment does not make that registry entry case-owned.

The Standards review found no documented-standard violations and one P2 duplication heuristic. Separate cleanup and checked-command implementations already differed in ownership adoption and TERM-to-KILL timeout behavior. Transactions had a directory guard, but still adopted partial creations by name without checking the registered path. It now uses the same lifecycle implementation as the other four companions.

Both original reviewers independently rechecked the committed correction. The Standards closure reports zero documented violations and zero remaining heuristics; the Spec closure resolves the original P2 and reports zero new findings. These are source and ownership-control reviews, separate from native execution credit. The read-only closure reports are retained at `final-review/standards-closure.md` and `final-review/spec-closure.md` under the external evidence root.

## Required preservation behavior

Setup rejects a preexisting database name before mkdir, and rejects existing files, directories and live or dangling symlinks. Successful mkdir and a createdb attempt are tracked separately; a failed unregistered create can remove its newly owned directory without acquiring ownership of a database registration.

Partial-create cleanup requires a well-formed unambiguous registry, the original nonsymlink directory device/inode, a create attempt, matching absolute volume and log paths, and the exact owned `file:<directory>/lob` location. Missing, unreadable, malformed, duplicate or foreign registrations retain the resources and produce a failing verdict. Server stop or process-inspection failure prevents database deletion. Failed deletedb or incomplete registry cleanup prevents directory removal. Name-based deletion and filesystem removal recheck the ownership predicates.

Product commands have a five-second TERM-to-KILL grace. The original readiness probes, phase expectations and successful cleanup labels remain stable. Shared case cleanup finishes before the framework teardown. Framework init/finish performs slot-wide service/process/IPC operations and requires native containment; this report does not claim unrelated slot processes survive that teardown. The helper assumes the case's serialized contained environment, rather than an atomic ownership lock against concurrent outside filesystem or registry mutation.

## Ownership regression controls

The controls execute complete shell entrypoints and their EXIT traps, with product CLI/process-table and framework init/finish boundaries stubbed. The framework stub performs no resource teardown. Predicates independently inspect registry bytes, markers, directory existence and symlink targets after the case exits, so a framework cleanup cannot hide an ownership violation. These are shell-boundary controls, not database or native-runner qualification.

The frozen original source fails 13 of 15 controls: four destructive preexisting-registered paths, five foreign-path registrations wrongly adopted, and four newly owned unregistered partial directories left behind. The original transactions guards pass the remaining two controls. Corrected committed entrypoints pass 105 of 105 controls across five cases and 21 scenarios, including preexisting resources, failed creation before/after registration, foreign/malformed/duplicate/missing/unreadable registry, real-directory and symlink replacement, stopped/unstoppable server, failed deletion and failed process inspection.

Five supplemental command-interface controls pass: valid output, rejection of empty output, failing status and FATAL output, and a real GNU timeout control with an owned Python child that ignores TERM. It exits 137 after 5.2066s for a 0.2s deadline plus 5s grace; the control's Linux subreaper records SIGKILL/waitpid and proves the child was reaped. `bash -n`, shellcheck and diff checks pass for all six changed files. A separate source comparison confirms the five fixture/value/physical bodies are unchanged after lifecycle/setup extraction; owner-drop checkdb also gains KILL grace.

Raw controls and the immutable review packet are outside the repositories at `/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/`: `oracle-review.md`, `review-packet.json`, `implementation.patch`, `static-checks.json`, `red-final/summary.json`, `green-final/summary.json`, and `bounded-final-reaped/summary.json`. Their exact hashes are in the review packet. Earlier failed controls and harness errors remain retained; they do not receive native validation credit.

The new native journal gate has separate offline controls: 45 state/snapshot corruptions and 10 exact-root positive/negative controls pass. Root required attribution to the frozen private checkout, selected case parent and database; a first suffix-only gate accepted five consistently remapped foreign-root journals and is retained as a red proof control. The strengthened gate rejects them. Synthetic journal copies supply these controls; they receive no native database credit. Preliminary proof packages and the first foreign-path harness mistake are preserved outside the repositories.

## Native receipt and SQL retention

Root approved the implementation/ownership model in [root-implementation-review.json](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/root-implementation-review.json), then reviewed the frozen proof delta and released exactly one full native shell invocation in [root-runtime-release.json](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/root-runtime-release.json). The fresh attempt is [/home/vimkim/tmp/oos306-sh-final-a01](/home/vimkim/tmp/oos306-sh-final-a01). Native verdict, outer cleanup and mandatory raw-model proof all return 0; there were no actual native failures, source corrections, retries or CTP fallback in this fix.

The run preserves 14 exact discovered case identities, 336 numbered passing assertions and the 936 original required artifacts, and adds five mandatory registry ownership journals. All 11 typed verifier functions covering 14 cases, independently reviewed values/physical models and phase labels remain unchanged. The journals positively establish initial name absence, case mkdir/create-attempt state, stable original device/inode, exact frozen source-root directory, matching absolute volume/log/LOB registration, and final registration absence before framework teardown. This strengthens case ownership evidence separately from slot-wide containment cleanup.

The pinned [proof04 contract](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/proof04/frozen-contract.json) SHA-256 is `9bc0e0ed8bf27d1a2a5dea6c2dab58d07034a66ecacec8e2f104347741e87895`; [driver](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/proof04/native-shell-final-attempt.py) `da5f39463a555011c56ac00ff42c08687c09f56789b4a9e0312cac7612f709cd`; [verifier](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/proof04/verify.py) `5879df3ecb7a6ef231d5a976bd55095e710a1a45f989d3aff339e54b2ec553eb`. The complete six-file input delta, all source/control hashes, exact command and original proof/raw-manifest provenance remain in the reviewed packets. Private 40 inputs are frozen; public 32 inputs and every non-lifecycle shell fixture/helper remain unchanged. No golden output was generated from actual defects.

The [required proof](/home/vimkim/tmp/oos306-sh-final-a01/required-proof.json) SHA-256 is `fbed970d46c0d8ab14827d96c42c4dc7a2482d4a1225ea0e5261bda370e3be06`. It replays raw logical/physical observations for all 14 cases and hashes **1,234 per-case raw files**, exactly the original 1,229 retention scope plus five registry journals. The separate [complete case-log-tree manifest](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/native-final-artifacts.sha256.json) hashes 1,521 files, including additional framework/capture files outside that per-case proof scope.

| Exact case stem under `shell/_40_guava/<stem>/cases/<stem>.sh` | OK assertions | Native case seconds | Retained per-case raw files |
| --- | ---: | ---: | ---: |
| `cbrd_26659_backup_restore` | 11 | 24.645341 | 81 |
| `cbrd_26659_crash_committed` | 10 | 14.149704 | 52 |
| `cbrd_26659_crash_undo` | 10 | 14.616862 | 51 |
| `cbrd_26659_dml_transitions` | 59 | 81.401109 | 109 |
| `cbrd_26659_lob_locators` | 21 | 13.465972 | 50 |
| `cbrd_26659_owner_drop` | 21 | 13.946627 | 38 |
| `cbrd_26659_read_paths` | 19 | 13.733959 | 45 |
| `cbrd_26659_representation_chunks` | 46 | 12.057799 | 137 |
| `cbrd_26659_schema_policy` | 54 | 11.140855 | 132 |
| `cbrd_26659_snapshot_visibility` | 9 | 10.902245 | 107 |
| `cbrd_26659_tde_wal` | 30 | 17.963545 | 85 |
| `cbrd_26659_transactions` | 12 | 8.271201 | 33 |
| `cbrd_26659_utility_cs` | 17 | 36.883306 | 156 |
| `cbrd_26659_utility_sa` | 17 | 39.994096 | 158 |

Native selection uses the existing source-matching optdebug install, matching Java 8/JDBC, native runner and copied CTP assets. It retains the original 16KiB profile and each reviewed SA/CS/recovery/vacuum/utility/TDE parameter. Owner-drop and representation use 20MiB DB/log volumes; the other fixtures retain 64MiB. `scenario_disk=on`, one slot, retry/update/continuation off, file feedback, case_logs=all/64MiB and the explicit sorted 14-case list remain. The irrelevant whole-corpus macro filter is cleared for the explicit selection, and actual selected skips are 0. `TESTKIT_NATIVE=shell`, `TESTKIT_CONTAIN=1`; `TESTKIT_SLOT_VOLATILE` stays unset. No build, host-workenv switch or dependency change occurred.

| Measured fresh shell boundary | Seconds |
| --- | ---: |
| Proof freeze/copy preparation under exclusive lock | 0.147599 |
| Attempt install/CTP/config preparation | 2.519735 |
| Native case sum | 313.172622 |
| Native whole invocation, including setup and normal teardown | 316.414065 |
| Mandatory raw-model/ownership proof | 9.744288 |
| Locked preflight/invocation/verification/cleanup, excluding preparation | 326.563374 |
| Entire attempt driver, including preparation and proof | 329.167290 |

These boundaries overlap and are not added together. [native-final-measurements.json](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/native-final-measurements.json) retains unrounded measurements, every wrapper timing and source/artifact identities. The original SQL receipt remains 88.523774s for its separate native invocation; its timing is neither rerun nor combined with this fresh shell measurement. Build/download overhead for this correction is 0; control/review work remains outside invocation timings. About ten minutes per suite remains guidance, without a hard threshold or company-CI extrapolation.

[cleanup.json](/home/vimkim/tmp/oos306-sh-final-a01/cleanup.json) proves no accessible copied-install processes, an empty outer registry/database directory and native slot root, restoration of all 14 copied configuration files, and all 40 testcase source hashes unchanged. Inaccessible/racing host PIDs are recorded, outside owned-process claims. Inner case result/journal evidence proves successful applicable case-owned cleanup before framework containment teardown. The exclusive validation lock spans each proof copy/preparation through execution, strict artifact verification and cleanup; original Ticket14 proofs, frozen inputs and manifests remain byte-identical. Root [accepted the correction and fresh qualification](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/root-final-acceptance.json) after an [independent locked audit](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/fix/root-fresh-native-artifact-audit.json): all 14 raw model replays, 336 labels, 941 requirements, 1,234 per-case raw hashes, 82 proof-source hashes, 72 live/copied public/private inputs and five exact-root ownership journals passed. That audit took 8.569452s of retained-read verification after execution and made no runtime invocation.

Root independently reconciled the original SQL16 receipt before this fix: 32 unchanged public inputs, 130 artifact hashes, 16 actual-result byte comparisons against reviewed answers, and source/install/dependency/runner/CTP identities and cleanup gates. No public input changes are part of this correction, so SQL is not repeated. Root's [post-shell SQL reconciliation](/home/vimkim/tmp/oos-developer-regressions-20261008/final-review/sql-reconciliation-after-shell.json) passes the same 32 input, 130 artifact, 16 actual/answer byte comparisons and identity/cleanup gates; it performs no SQL invocation. Root handles the final integration reconciliation. The original SQL timing stays distinct from any fresh shell measurement.

## Retained failed controls and preparation history

All paths below are under the external `final-review/fix/` evidence directory; none is tracked as a repository artifact.

| Retained path | Outcome and scope |
| --- | --- |
| `red-preexisting/`, `red-partial-create/`, `red-final/` | Substantive original-source ownership violations; final frozen controls fail 13/15 as intended. |
| `green-ownership-matrix/` | Harness readiness stub caused its own 20s timeout; incomplete control, no product verdict. |
| `green-ownership-matrix02/` | One SA unstoppable expectation lacked the simulated running process; corrected harness setup. |
| `green-lookup-matrix/` | Harness hashed a chmod000 registry before recording its expected bytes; setup exception before testcase invocation. |
| `bounded-final/` | TERM-ignore child termination observed, zombie state retained; no reap credit. `bounded-final-reaped/` proves SIGKILL/waitpid and absence. |
| `proof-offline-controls/` | First foreign-path corruption accidentally modified an unrelated entry; five false reject expectations retained. |
| `path-attribution-red/` | First suffix-only journal verifier accepted five foreign-root journals; exact-root gate rejects them in `path-attribution-green/`. |
| `proof/`, `proof02/`, `proof03/` | Preliminary frozen packages retained; only reviewed `proof04/` drove native execution. |

The final accepted controls are `green-final/` 105/105, `bounded-final-reaped/` 5/5, `proof-offline-controls04/` 45/45 and `path-attribution-green/` 10/10. Earlier passing controls also remain. Root's original SQL audit-only wrong search-root rejection is separately retained at `final-review/sql-reconciliation-first-rejection.json`; no SQL or result artifact was mutated. Historical actual database failures/defect reproducers remain in the individual delivery reports linked from the original 14 report.

## Remaining scope

The independent source reviewers close both lifecycle ownership and code duplication findings; the fresh native receipt qualifies the complete selected passing shell set, accepted by root's independent locked audit. Existing target/partition/page-return/SA-placement defects, rollback-after-vacuum identity limitations, accepted chain reuse/commit notification, existing-file TDE application, ordinary HA replication, ciphertext and internal-only gaps retain their original coverage dispositions. The selected set does not establish full-company-corpus shell equivalence or complete engine conformity.
