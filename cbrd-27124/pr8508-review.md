# PR 8508 review and CMake alternatives

The user asks whether PR #8508 has a better CMake design, reviewed in a new worktree. For maintainers and the PR author, the most useful immediate change is to pass `BUILD_NUMBER` only to `cci_network.c`. Keep the version-header split. A build-time Git query is a promising replacement for storage-specific watchers, but it also needs explicit package and Windows resource handling.

Reviewed on 2026-11-16 KST. Repository [CUBRID/cubrid, PR #8508](https://github.com/CUBRID/cubrid/pull/8508), issue [CBRD-27124](https://jira.cubrid.org/browse/CBRD-27124).

| Identity | Value |
| --- | --- |
| Base and merge base | `b7987f91fac2c50838706ded24c879f560691216` |
| Head | `7a15874f821bd87807e06a59bcd72cc524b94251` |
| Comparison | `git diff b7987f91fac2c50838706ded24c879f560691216 7a15874f821bd87807e06a59bcd72cc524b94251` |
| CCI submodule pin | `df47f014731e977263b25cb5ea53dc6d0846328a` |
| Source worktree | `/home/vimkim/gh/cb/CBRD-27124-pr8508-review` |
| Source branch | `review/CBRD-27124-pr8508` |

## Verdict and recommendation

**Verdict `no-confirmed-findings` for newly introduced functional defects in the bounded inspected scope.** Zero confirmed introduced defects. One reproduced pre-existing freshness failure remains unhandled by the new watcher. It is documented below as R1 and is excluded from that count. This does not certify merge safety or qualify untested platforms.

**Follow-up review required: yes.** If the PR intends general linked-worktree reftable support, fix R1 and replay its cases before claiming that support. If adopting the CCI recommendation, validate generated commands on supported generators and Windows. A polling rewrite needs its own integration review; the isolated prototype establishes feasibility only.

For this PR, I recommend these changes:

1. Keep `build_version.h` separate from the common configuration headers and keep the broker calls to `rel_build_number()`.
2. Replace target-wide CCI forced inclusion with a source-specific `BUILD_NUMBER` definition.
3. Keep configure-time version calculation for the immediate fix, repair the missing common reftable dependency, and place the Git watcher in a small CMake module with focused tests. Moving the code alone does not fix its dependency model.
4. Consider build-time polling as a separate change if avoiding Git storage details is a priority. Include package and Windows resource consumers in that change.

Laziness Protocol shaped the choice of a source-specific CCI definition and a bounded immediate fix. Prove It Works required executable version output, real Git transitions, compiler preprocessing, and generated packages. No speedup or cache-hit improvement was measured in this review.

## D1. Give the CCI build number only to its consumer

The [new CCI block](https://github.com/CUBRID/cubrid/blob/7a15874f821bd87807e06a59bcd72cc524b94251/CMakeLists.txt#L861) forces `build_version.h` into every source of each existing CCI library target. At the pinned CCI revision, its source list has 14 Unix files and 16 Windows files. Only `src/cci/cci_network.c:217` uses the parent engine's `BUILD_NUMBER`. `cas_cci.c` uses the separate `CCI_BUILD_NUMBER`.

Consequently, every CCI object acquires a dependency on the volatile header. The PR's stated 14 CCI recompilations are consistent with that source dependency, although this review did not run or time a full CCI build. This is an improvement opportunity within the PR's purpose, rather than an introduced functional regression.

The following candidate replaces the current target-wide option for the normal embedded configuration, where `cascci` exists:

```cmake
set_property(SOURCE
  "${CMAKE_CURRENT_SOURCE_DIR}/cubrid-cci/src/cci/cci_network.c"
  TARGET_DIRECTORY cascci
  APPEND PROPERTY COMPILE_DEFINITIONS
  "BUILD_NUMBER=${BUILD_NUMBER}")
```

`TARGET_DIRECTORY` selects the directory scope where CCI created the target. Setting a source property in the parent's default scope would miss that child target. CMake added this mechanism in 3.18, before this project's minimum 3.21. [CMake source-property documentation](https://cmake.org/cmake/help/v3.21/command/set_source_files_properties.html)

If retaining support for either target name, choose one existing target as the directory scope and preserve the configure-time failure when none exists. Both targets, when present, use the same source in the same directory scope. The snippet is the normal-case proposal, not a complete replacement for that validation.

This definition preserves `MAKE_STR(BUILD_NUMBER)` without a compiler-specific `/FI` or `-include` option. It needs no submodule modification. The parent remains coupled to the pinned CCI source path and macro name, which are explicit dependencies to maintain when upgrading CCI.

Executed checks:

- A two-source child-directory fixture builds shared and static targets using the current target-wide include, a source-specific include, and a source-specific definition. All print `11.5.0.123`, then `11.5.0.124` after version change. The target-wide option rebuilds both sources per target. The source-specific options rebuild only the network consumer.
- Preprocessing the actual pinned `cci_network.c`, with copied generated headers adjusted to match this PR's layout, produces `strncpy (ver_str, "11.5.0.123", 20);` with both the current include and the proposed definition. Both commands exit 0.
- The coordinator reran both probes successfully. The fixture's dual-target configuration checks scope behavior; normal parent `WITH_CCI` creates the shared target at this pin.

These checks establish macro expansion and generated dependency behavior on Linux, CMake 3.26.5, GCC 11.5.0, and Ninja 1.10.2. They do not establish a complete Windows build or an actual broker handshake.

## R1. The watcher still misses common reftable updates

This is a demonstrated remaining freshness defect, **not a regression introduced by this PR**. Both reviewed revisions fail the affected cases. The new watcher repairs ordinary files-backend commits but leaves this path unhandled.

At [CMakeLists.txt:172](https://github.com/CUBRID/cubrid/blob/7a15874f821bd87807e06a59bcd72cc524b94251/CMakeLists.txt#L172), every candidate reftable path is based on `git rev-parse --git-dir`. For a linked worktree this is its private metadata directory. Its branch ref belongs to the common repository. The code resolves the common directory later but does not watch its `reftable/tables.list`.

Two scenarios reproduce stale version output:

- Initialize a reftable repository with `core.logAllRefUpdates=false`, create a linked worktree, configure and build it, then make an empty commit there. The common stack changes and the private stack does not. The next build retains the old version.
- With reflogs enabled, update the linked worktree's checked-out branch from the primary worktree using `git update-ref refs/heads/linked <new-commit>`. The tracked content is unchanged because the new commit is empty. The linked build again retains the old version.

The coordinator independently extracted the exact production version block from both SHAs, used the submitted header template, compiled a consumer of `VERSION_STRING`, and compared its output with Git. On Git 2.47.3 and Ninja:

| Revision and scenario | Actual result |
| --- | --- |
| Base, files backend, external branch update | Stale, pre-existing failure |
| Head, files backend, external branch update | Refreshed correctly |
| Base, linked reftable, external update | Stale |
| Head, linked reftable, external update | Stale |
| Base, linked reftable, ordinary commit without reflogs | Stale |
| Head, linked reftable, ordinary commit without reflogs | Stale |

For the head without reflogs, Git advances from `aaf7e25` to `93726b2`. The compiled consumer still prints `11.5.0.0001-aaf7e25`, and the build prints `ninja: no work to do.` Every command exits 0. This is level 4 evidence against the production CMake block, not a full `cubrid_rel` execution.

The narrow fix direction is to watch the existing common `reftable/tables.list` as well as the worktree-private stack. Verify both scenarios after the fix. Build-time Git queries avoid this particular storage dependency. The PR already says reftable was untested; this review supplies the missing evidence and does not treat that disclosure as proof of support.

## D2. Polling can simplify the model, with a wider integration scope

An always-run CMake target can ask Git for the current version before version consumers build. Generate `build_version.h` with `configure_file`, which preserves its timestamp when content is unchanged. Declare generated byproducts and dependencies for every consuming target. This removes the need to model loose refs, packed refs, reflogs, and shared reftable stacks. [CMake custom-target documentation](https://cmake.org/cmake/help/v3.21/command/add_custom_target.html), [content-stable file generation](https://cmake.org/cmake/help/v3.21/command/configure_file.html).

The metadata to generate is broader than a header:

| Consumer | Current responsibility | Polling integration requirement |
| --- | --- | --- |
| `release_string.c` and CCI network source | Compile the runtime version | Refresh their header or definition before compilation |
| CPack binary and source names | Use configure-time `CUBRID_VERSION` | Read generated version metadata at package time or explicitly reconfigure |
| Windows `version.rc` | Embed `CUBRID_EXTRA_VERSION` | Regenerate the resource before its consumers build |
| Explicit `VERSION` or `VERSION-DIST` | Supply a fixed distribution identity | Preserve precedence and Git-free archive builds |

The relevant current consumers are [CPack version assignment](https://github.com/CUBRID/cubrid/blob/7a15874f821bd87807e06a59bcd72cc524b94251/CMakeLists.txt#L971), [package filenames](https://github.com/CUBRID/cubrid/blob/7a15874f821bd87807e06a59bcd72cc524b94251/CMakeLists.txt#L982), and [Windows version-resource template](https://github.com/CUBRID/cubrid/blob/7a15874f821bd87807e06a59bcd72cc524b94251/cmake/version.rc.cmake#L21).

A disposable prototype generates the actual submitted header template plus a small CPack metadata file. A package-time `CPACK_PROJECT_CONFIG_FILE` loads the latter. CPack supports per-generator overrides there. Production already uses that hook for `CPackOptions.cmake`, so integration would extend its behavior rather than overwrite it. [CPack configuration lifecycle](https://cmake.org/cmake/help/v3.21/module/CPack.html)

The prototype passes these checks on Ninja and Unix Makefiles:

- An empty commit followed only by a build updates the compiled version.
- Another build without changes preserves the object and header timestamps.
- After the build, direct `cpack` creates a package with the same version in its filename. In the linked reftable run, the executable extracted from each generated archive also prints that version.
- The same checks pass in a linked reftable repository with reflogs disabled, where the submitted watcher fails.
- A header-only variant produces a newer executable and an older package filename, demonstrating why package handling belongs in the design.

This is a feasibility experiment, not an integrated CUBRID patch. It does not test Windows resources, source packaging, fixed distribution versions, installation behavior, or concurrent Git changes. The always-run query adds work to every build, and this review does not measure its cost.

| Approach | Judgment |
| --- | --- |
| Keep the old HEAD-only dependency | Rejected. Executed base controls retain stale versions after ordinary branch commits. |
| Keep current configure-time design, narrow CCI dependency, fix and isolate watchers | Recommended immediate scope. It retains one configure-time version for headers, resources, and packages. Storage-layout tests remain necessary. |
| Build-time Git query plus generated metadata | Preferred direction if the project wants to stop tracking Git's internal files. It requires a deliberate update of all consumers and supported generators. |

## Safety facts, coverage, and limits

The header split removes volatile macros from `config.h`'s dependency path. `release_string.c` owns their stringification. Broker tools call the existing exported `rel_build_number()` through their existing `cubridcs` linkage. The reported identity now follows the loaded client library, as the PR description acknowledges. Source inspection found no missing remaining `makestring` use in the affected broker scope.

| Changed paths or boundary | Owner and evidence | Result |
| --- | --- | --- |
| `CMakeLists.txt`, Git version and watcher block | CMake specialist and coordinator, exact-block compiled probes on both revisions | Ordinary supported fixtures pass, R1 remains |
| `CMakeLists.txt`, CCI block | Systems specialist and independent CMake specialist, coordinator replay | Macro value preserved, D1 narrows dependencies |
| `cmake/build_version.h.cmake`, `cmake/version.h.cmake` | Systems, consumer audit and generated-header probes | No functional defect identified |
| `src/base/release_string.c`, `src/base/release_string.h` | Systems, macro/API and linkage audit | No functional defect identified, full build not run |
| `src/broker/broker_admin.c`, `broker_admin_pub.c`, `broker_admin_so.c`, `broker_changer.c`, `broker_monitor.c`, `cas.c`, `cas_cgw.c`, `cas_common.h` | Systems, consumers, link targets, Windows export audit | No functional defect identified, Windows runtime not run |
| Package and Windows resource boundary | Coordinator and CMake specialist, production source plus prototype | Current configure-time dependency explained, polling integration remains a proposal |
| Concurrency, storage recovery, HA | Not applicable | No engine-state, page, WAL, or replication changes. CCI version metadata is covered above. |

The CMake specialist ran 17 exact-block conditions in fresh fixtures. The coordinator replayed that full probe as well as the focused R1 reproduction. Conditions include no-op builds, ordinary commits, loose-ref deletion through packing, packed-ref commits, detached commits and checkouts, linked files/reftable commits with normal reflogs, and packed branch commits with reflogs disabled. The base ordinary-commit control intentionally remains stale.

No full engine build, DB regression suite, Windows/MSVC build, Visual Studio generator, Ninja Multi-Config, old Git executable, network handshake, performance benchmark, or CI run was performed. Source/configuration probes do not replace those integration checks. No new material source-only correctness concern remains asserted. R1 is a confirmed pre-existing gap, and the proposed alternatives have the explicit untested integration scope above.

Candidate disposition: the CMake specialist's proposed P2 R1 is retained as a pre-existing purpose-related failure and excluded from introduced findings after coordinator base comparison. The systems specialist's broad CCI dependency is retained as D1, not promoted to a functional defect. Comment-only deletion suggestions were omitted from correctness findings. Two reviewers independently identified CCI's one macro consumer before reading each other's results.

## Reproduction artifacts and budget

Local run directory `/home/vimkim/temp/pr8508-review-20261116-7a15874` contains `manifest.json`, `coverage.md`, reviewer reports, the exact patch, and raw evidence. The following commands were executed successfully; each script preserves commands and output under `evidence`:

```text
python3 evidence/coordinator-reftable.py
python3 evidence/cmake/probe.py evidence/coordinator-main
bash evidence/systems/probe.sh
python3 evidence/systems/preprocess.py
python3 evidence/polling-probe.py
python3 evidence/polling-probe.py --reftable-linked
```

The scripts execute production blocks or exact pinned preprocessing where stated. The CCI dependency fixture and polling alternative are intentionally small experimental projects. No submitted source changed. Raw logs and disposable projects stay outside the lasting documentation repository; the essential observations are recorded above.

Budget mode was bounded with no user-specified absolute limit. Two initial specialists used `gpt-6.1-sol` and `gpt-6.1-terra`, both with high reasoning. Each had a 12-minute target and an 8-minute checkpoint, within a total target of 64 agent-minutes, including a 40-minute coordinator reservation, and a 30-minute elapsed target. No hard cap was enforced. Token, credit, and account allowance telemetry was unavailable, so actual per-agent usage and exact target compliance are unknown. No extra reviewer, nested agent, or retry panel was launched.

## Follow-up and publication state

Before finishing, the PR metadata was reread and both source SHAs remained unchanged. Revalidate them again before a follow-up review.

For R1, add the common-stack dependency or adopt an explicitly scoped support contract, then replay ordinary linked reftable commits without reflogs and external branch updates. For D1, apply the source-specific definition and inspect both CCI target variants where supported, including MSVC generated commands. A polling implementation must additionally cover Windows resources, fixed-version archives, source packages, and package-time metadata.

The local report is prepared for the review publication workflow. The documentation repository's `main` checkout contains an unrelated uncommitted change to `cbrd-27259/review-20261111/heap-bigone-assert.md`. It was preserved. The required clean destination precondition prevents integration and publication in this run. No report push or PR-page comment was performed. A saved draft and publication context remain in the run directory.
