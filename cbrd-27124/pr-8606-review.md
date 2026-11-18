# PR 8606 build version review

The version refresh is worth fixing. An ordinary incremental build at the merge base can report an earlier commit even after Git advances on the same branch. The PR fixes that common case on Ninja and Unix Makefiles. It also introduces a way for Make-based packaging to label an archive with a different commit from the binary it contains.

**Verdict `changes-required`.** Follow-up review is required on the packaging path and the Git cases below. A focused CMake module is the smallest maintainable revision. A build-time Git query is a stronger long-term design once package metadata and Windows resources consume the same build version.

## Scope and necessity

- Reviewed on 2026-11-18 KST for CUBRID maintainers. Base and merge base `25b933925529907a9ad092a36de76a0ab944e3f3`. Head `85290eb56965d46fc5a00402a01c13c146d271d0`. The diff changes only `CMakeLists.txt`. Patch SHA-256 `e1e153b1dfabe780304d5688ae16b49ffee23de6c6c3617c5e8ce9ec0050e292`. [PR 8606](https://github.com/CUBRID/cubrid/pull/8606)
- An attached `HEAD` contains a symbolic ref. A same-branch commit advances its target ref while leaving the `HEAD` file unchanged. The base only watches `HEAD`. Linux probes used the pinned CUBRID version block and header template to compile an executable that prints `VERSION_STRING`. The base kept its old version after an empty commit on both generators. The PR regenerated once, printed the current commit, and skipped configuration and compilation on the next unchanged build. [Base version code](https://github.com/CUBRID/cubrid/blob/25b933925529907a9ad092a36de76a0ab944e3f3/CMakeLists.txt#L101-L175)
- An incorrect commit in a binary complicates QA and diagnosis. `./build.sh build` explicitly runs CMake configuration first, so this failure concerns an already configured build. PR 8508 isolated volatile macros from the common header and addressed the broad recompile cost. The current review found no evidence that PR 8606 is urgent for CI that configures for each build. [CBRD-27124](https://jira.cubrid.org/browse/CBRD-27124), [PR 8508](https://github.com/CUBRID/cubrid/pull/8508), [build.sh build path](https://github.com/CUBRID/cubrid/blob/85290eb56965d46fc5a00402a01c13c146d271d0/build.sh#L656-L670)

## Confirmed findings

### P2 / CV-1. Direct CPack can mislabel a Make package

Configure with Unix Makefiles, build commit A, create an empty commit B on the same branch, and run `cpack -G TGZ` directly in the build directory. CPack reads A's `CPackConfig.cmake`. During Make's preinstall step the new ref dependency triggers regeneration and recompilation for B. CPack retains A's filename. The probe extracted the resulting archive and ran the binary. The filename contained `11.5.0.0002-4f32b9c`, while the binary printed `11.5.0.0003-41b4c52`. CPack returned success.

The base also misses the version refresh in this sequence. Its package filename and binary both remained on A. With the PR's Ninja build, direct CPack packaged both as A. With the PR's generated `package` target after a fresh commit, both Ninja and Make built that commit before spawning CPack, and both archive names matched their extracted executables. CUBRID's `build.sh dist` calls CPack directly and can be invoked separately from `build`. Decide how that entry point handles a changed checkout. Build before CPack reads its configuration, or reject packaging when the build snapshot is stale. Add the Make sequence to the regression check. This is a regression in artifact identity even though a stale standalone package was possible before the PR. [Version dependencies](https://github.com/CUBRID/cubrid/blob/85290eb56965d46fc5a00402a01c13c146d271d0/CMakeLists.txt#L165-L205), [Package metadata](https://github.com/CUBRID/cubrid/blob/85290eb56965d46fc5a00402a01c13c146d271d0/CMakeLists.txt#L961-L1016), [Direct package invocations](https://github.com/CUBRID/cubrid/blob/85290eb56965d46fc5a00402a01c13c146d271d0/build.sh#L458-L471), [CPack configuration](https://cmake.org/cmake/help/v3.21/manual/cpack.1.html)

### P3 / CV-2. Linked reftable worktrees miss changes in the common stack

The PR watches `reftable/tables.list` under `--git-dir`. A linked worktree has a local stack for per-worktree refs or reflogs and a common stack for branch refs. With Git 2.47.3, an ordinary commit in a linked reftable worktree with `core.logAllRefUpdates=false` changed the branch in the common stack. The pinned PR kept `11.5.0.0002-91bbae4` after HEAD advanced to `261ad8a` and should have yielded `11.5.0.0003-261ad8a`. With reflogs enabled, moving the linked worktree's branch ref using `git update-ref` in the primary worktree also changed only the common stack. Both Ninja and Make returned success with a stale version for the external update. The base is also stale. This case falls within the PR's stated goals of reftable and branch moves from another worktree.

Register the existing `reftable/tables.list` under `--git-common-dir` as well as the per-worktree path if the configure-time approach stays. The specialist's disposable variant verified both reftable scenarios after adding that dependency. [Watch paths](https://github.com/CUBRID/cubrid/blob/85290eb56965d46fc5a00402a01c13c146d271d0/CMakeLists.txt#L157-L205), [Git reftable format](https://git-scm.com/docs/reftable)

### P3 / CV-3. Foreign hooks can produce an empty build number

A real `pre-receive` hook in another repository exports object directory variables as well as `GIT_DIR`. The PR removes `GIT_DIR`, `GIT_WORK_TREE`, and `GIT_COMMON_DIR`, leaving `GIT_OBJECT_DIRECTORY` and `GIT_ALTERNATE_OBJECT_DIRECTORIES` set. The pinned PR resolved the source repository's abbreviated hash, but `rev-list` could not read that repository's commit. CMake reported the result of the last command (`awk`), so the configure succeeded with `11.5.0.-b651a2b` instead of `11.5.0.0002-b651a2b`. The base failed this probe rather than completing with an empty count.

When running Git against another repository, clear Git-local environment variables for those subprocesses using the list from `git rev-parse --local-env-vars`. Check Git's status before zero-padding the count. The specialist confirmed that scoped environment handling makes the same hook return the right version. [Git environment and count](https://github.com/CUBRID/cubrid/blob/85290eb56965d46fc5a00402a01c13c146d271d0/CMakeLists.txt#L108-L156), [Git hook environment](https://git-scm.com/docs/githooks), [CMake execute_process return values](https://cmake.org/cmake/help/v3.21/command/execute_process.html)

## Design recommendation

For this PR, extract the lookup and dependency registration into `cmake/TrackGitRevision.cmake`. The same ticket's earlier PR 8298 already used that module layout. Keep the pack and ref edge cases covered by small repeatable tests. The module can use `GIT_EXECUTABLE` from `FindGit` and register `CMAKE_CONFIGURE_DEPENDS` directly. A `.sh` helper would add a shell requirement to the CMake path used by MSVC and keep the same Git-storage and CMake timestamp assumptions. Preserve explicit `VERSION` and `VERSION-DIST` handling. [Earlier CMake module](https://github.com/vimkim/cubrid/blob/0d2a76e60f944be0ababe9c466766c553189fcda/cmake/TrackGitRevision.cmake), [CMake configure dependencies](https://cmake.org/cmake/help/v3.21/prop_dir/CMAKE_CONFIGURE_DEPENDS.html)

For a longer-term fix, let a build target call a small `cmake -P` script. Resolve HEAD to a full commit ID once and use that ID for the count and abbreviation. Update generated version files only when their content changes. Attach the target to every version consumer, including the engine targets with `release_string.c`, bundled CCI targets, and Windows targets that compile `version.rc`. Pass the same build version to CPack before it initializes. A package operation after a partial build needs a full build or a freshness check. CPack should use the version of the packaged artifacts.

The prototype generated a header and a version file and demonstrated the dependency on a named executable target. It refreshed a reftable linked worktree with reflogs off on Ninja and Make. It also picked up an external ref move, packaged the matching commit through the `package` target, and preserved header mtime with zero recompiles on the next build at the same HEAD. The prototype cached the count by commit ID. If count freshness across `git fetch --unshallow` is part of the contract, production needs to account for the changed shallow boundary in its cache or recompute the count. [Build header and CCI](https://github.com/CUBRID/cubrid/blob/85290eb56965d46fc5a00402a01c13c146d271d0/CMakeLists.txt#L861-L878), [MSVC resource template](https://github.com/CUBRID/cubrid/blob/85290eb56965d46fc5a00402a01c13c146d271d0/cmake/version.rc.cmake#L19-L25), [CMake custom target and byproducts](https://cmake.org/cmake/help/v3.21/command/add_custom_target.html)

## Verification and limits

Linux x86-64, Git 2.47.3, CMake 3.26.5, Ninja 1.10.2, and GNU Make 4.3. The primary experiment extracted the exact version block, package declarations, and templates from the pinned Git objects into disposable repositories. Each used a small executable and a real CPack TGZ archive. The specialist used an independent CMake fixture from the same Git objects. The coordinator replayed the reftable, hook, and split-count checks.

| Case | Result |
| --- | --- |
| Same-branch empty commit, Ninja and Make | Base stale. PR refreshes the binary and CPack configuration once. |
| No-op, loose ref and packed ref with reflog off | PR performs no configure or compile after the current version is built. A commit that recreates the loose ref is detected. |
| Ordinary files-backed linked worktree and ordinary reftable commits | PR refreshes in both generators under the tested defaults. |
| Reftable linked worktree with reflog off or external branch ref update | PR remains stale. CV-2. |
| Standalone CPack after a commit in a Make build | PR filenames disagree with extracted binary. CV-1. The build-system `package` target matches on both generators. |
| Git pre-receive hook with foreign object directories | PR configures with an empty build number. CV-3. |
| Commit between separate count and hash queries | Both revisions can persist a mixed version. This pre-existing issue supports deriving both fields from one resolved commit. |
| Integration coverage | Actual Windows/MSVC targets, CCI libraries, and CUBRID engine binaries were traced from source. Their build and packaging paths still need an integration run for a revised PR. |

Local evidence entry points are `evidence/check_watch.py`, `evidence/check_snapshot.py`, and `specialist/probe.py` in the review run. Run the first two scripts from a checkout that contains the pinned revisions. The specialist script's `reftable_no_reflog`, `foreign_hook`, and `race` cases take `base` or `head`. All reported outcomes are from those runs. The suite does not measure time or cache performance.

The review allocated one bounded specialist and coordinator replay. There was no hard budget or per-agent usage telemetry. Follow-up on the revised PR should verify CV-1 through CV-3, then exercise the affected production targets and Windows version resources if that path changes.
