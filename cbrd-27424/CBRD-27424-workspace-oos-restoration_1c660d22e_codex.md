# CBRD-27424: restore the attrinfo workspace OOS implementation

Date: 2026-10-07. Work-tracker item: **286**. PR: [CUBRID/cubrid#7925](https://github.com/CUBRID/cubrid/pull/7925).

The new commit [`1c660d22e`](https://github.com/vimkim/cubrid/commit/1c660d22e4340ee707336ad08c8b4bf4b69744de) restores the production implementation from `90f3bd79e` while retaining standalone workspace OOS support and subsequent useful regression coverage. It follows the [published revert rationale](https://github.com/vimkim/my-cubrid-docs/blob/b9752a333a6eb4ce279da00e063653bcf82fc4e5/cbrd-27424/CBRD-27424-workspace-oos-revert-rationale_a142503dc_codex.md).

## Scope and preservation

The four production files below are byte-identical to `90f3bd79e`; this is a new commit on the existing PR branch, preserving its history:

- `src/storage/heap_file.c`
- `src/storage/heap_oos.cpp`
- `src/storage/heap_oos.hpp`
- `src/transaction/locator_sr.c`

Workspace writes again decode into heap attribute values and use `heap_attrinfo_transform_to_disk_except_lob`, after selecting the destination heap. Existing force flags, change numbers, system-operation cleanup, partition ownership and external BLOB/CLOB preservation remain in that implementation. The direct-byte demotion helper and shared layout planner introduced later are removed.

The 13 loader/workspace cases and licensed benchmark harness are unchanged from `a142503dc`. All 21 comparison cases are retained and adapted to create and flush an actual workspace object through `locator_flush_instance`. They fetch that object's committed record by its OID and compare value bytes and OOS selection against independently serialized source values and the query writer. Committed heap records can omit the insert MVCC ID, so length comparisons exclude each record's header. Raw-helper-only input-buffer and pre-force change-number assertions no longer apply; the broader loader/workspace coverage remains.

The user's unrelated `cubrid-cci/win/cci_version.h` changes were excluded from the commit and verified unchanged after both builds. Its before/after diff matches; the file SHA-256 is `f9766b68dab0c3f615a02cf29368396a43e887b8bc052e0fba321add407259a3`.

## Build and CTest verification

The GCC Debug build and installation passed. The full configured CTest run passed **37/37** in **291.98 seconds**, including **21/21** adapted comparison cases and **13/13** workspace/loader cases. These cover OOS+bigone rejection and ordinary-bigone acceptance, references, rollback, ignored errors, storage policy, partition movement, external LOB preservation and successful no-logging loading.

Both matched Release builds and installations passed. The local `release_gcc` configuration uses **GNU 11.5.0**, CMake **RelWithDebInfo**, and **`-O2 -ggdb3 -DNDEBUG -finline-functions`**, with the same warning exceptions on both sides. The saved CMake caches are byte-identical. This measurement is explicitly an optimized Release preset, rather than an `-O3` CMake Release build.

The benchmark executable hashes are identical; the engine libraries differ as expected. The rebuilt Java archive has a different file hash, but every archive entry has identical contents, so the difference is archive metadata. Both installations retain separate engine-library identities in the verification file.

## Matched benchmark results

The fresh comparison supports the revert rationale: restored large loads have **9.1% lower median elapsed time** and **11.6% lower median user + system CPU**. Large-load CPU is lower in all five matched pairs, with a median paired reduction of **13.4%**. Small-load results do not show a consistent improvement.

| Workload | Measure, seconds | Direct-byte median | Restored median | Restored change |
| --- | --- | ---: | ---: | ---: |
| Small | elapsed | 2.21 | 2.16 | -2.3% |
| Small | user CPU | 0.90 | 0.91 | +1.1% |
| Small | system CPU | 0.10 | 0.11 | +10.0% |
| Small | user + system CPU | 1.00 | 1.02 | +2.0% |
| Large | elapsed | 6.16 | 5.60 | -9.1% |
| Large | user CPU | 3.60 | 3.18 | -11.7% |
| Large | system CPU | 0.29 | 0.27 | -6.9% |
| Large | user + system CPU | 3.89 | 3.44 | -11.6% |

All **20/20 samples** returned `VALUE_OK`. Every fixture for a workload has the same SHA-256, matching the historical experiment's fixtures. All ten large samples report 10,000 OOS records, 50,320,000 stored bytes, 3,335 pages of 16,344 bytes, 54,507,240 physical bytes and 4,187,240 unused bytes. Small samples have no OOS file. The gain therefore does not come from omitting values or changing this workload's OOS placement.

Shared-host variability is material. Sampled one-minute load ranges from **7.52 to 68.49**. Large elapsed times span 5.29–10.04 seconds for direct-byte and 4.93–11.08 seconds for restored; one pair is slower after restoration. Small elapsed times span 2.09–3.50 and 2.09–3.47 seconds. The observed CPU reduction across every large pair strengthens the performance rationale, but five pairs on a shared host do not establish statistical confidence or a profiled root cause. Historical and new absolute timings are not interchangeable.

Retained evidence: [raw measurements](evidence/workspace-oos-restoration-2026-10-07/measurements.csv), [run order and host load](evidence/workspace-oos-restoration-2026-10-07/execution-order.csv), [build/binary identities and verification](evidence/workspace-oos-restoration-2026-10-07/verification.json), [CTest summary](evidence/workspace-oos-restoration-2026-10-07/ctest-summary.txt), and representative [direct-byte](evidence/workspace-oos-restoration-2026-10-07/direct-large-check.txt) / [restored](evidence/workspace-oos-restoration-2026-10-07/restored-large-check.txt) OOS output.

The comparator is the freshly built direct-byte implementation at `a142503dc1a6f85b498a425aa58d6a78136ccc6b`. The restored side is `1c660d22e4340ee707336ad08c8b4bf4b69744de`. This remains an implementation-to-implementation comparison inside the PR; it is not a benchmark against PR merge-base `fb567a629`.

The unchanged harness creates private databases and times only `cubrid loaddb -S`. Each side receives five samples of each workload: 100,000 rows with a 48-byte value and 10,000 rows with a 5,000-byte value. Pair order alternates direct/restored, restored/direct, direct/restored, restored/direct, direct/restored. Each invocation runs small then large. All commands inherit CPU affinity to logical CPU 79. The host is shared, and affinity does not reserve that CPU or isolate storage; no local build or CTest ran during measurement. Elapsed and user/system CPU measurements are retained separately.

The initial copied installations had paths too long for Java's Unix-domain socket. That attempt stopped during schema creation, before producing a timed sample. Both installations were moved to shorter paths and the complete measurement sequence restarted. The abandoned startup attempt is excluded from the results.

To repeat the sequence, build and install the two pinned revisions with the matched CMake/GCC flags in `verification.json`, retaining separate `direct/` and `restored/` installation directories under a short installation root. Run the [parameterized replay driver](matched-workspace-oos-benchmark_1c660d22e.sh) with a new output directory:

```bash
bash matched-workspace-oos-benchmark_1c660d22e.sh /path/to/source /short/install/root /path/to/new-results 79
```

The driver parameterizes machine paths and CPU selection; its pairing, labels, workload order and sample counts match the executed sequence. The original driver's hash is retained in the verification file. Original CTest and build logs remain in the local execution record; the published CTest excerpt retains verdict lines and counts. Representative CSQL exports strip trailing whitespace only, with original and export hashes recorded.

## Standards

One P2 finding: the restored `heap_attrinfo_determine_disk_layout` constructs `column_size` and grows `oos_candidates` without catching `std::bad_alloc`. Personal CUBRID policy requires throwing STL operations to translate exceptions into CUBRID errors. Under memory pressure, an exception can unwind past workspace attribute and copy-area cleanup rather than return `ER_OUT_OF_VIRTUAL_MEMORY`. This is inherited from the explicitly requested restoration revision and remains unfixed here to preserve the exact production implementation. It warrants a separate focused correction. No actionable baseline smell findings were reported; the adapted test follows the documented GoogleTest exception.

## Spec

No confirmed findings. All four production files match the specified revision. The 13 loader/workspace cases and repaired benchmark remain unchanged; all 21 comparisons exercise real workspace flushing and retain meaningful independent comparisons. Scan-cache record bytes are copied before ending the cache, and reference OOS chains are aborted in their separate system operation. CCI changes remain outside the commit. The read-only review assessed `a142503dc...1c660d22e`; runtime verification is reported separately above.

The source checkout lacks the skill's optional `docs/agents/issue-tracker.md` convention, so this review used the explicit published rationale and work-tracker item 286 as its spec. `/setup-matt-pocock-skills` can install that convention separately; it was not needed to perform this authorized restoration.

Review totals: **Standards 1 finding (P2 allocation-error handling); Spec 0 findings**.

The separate CBRD-27057 threshold gap remains: both implementations use `DB_PAGESIZE/4`, whereas the normative OOS context specifies a derived four-record heap target. This restoration does not repair that gap. Historical shell CI failures are not attributed to or resolved by this commit.

## Publication and CI

Source commit `1c660d22e4340ee707336ad08c8b4bf4b69744de` was pushed to `vk/CBRD-27424-oos-loaddb-sa`; PR #7925 reports that exact head. The pre-push base-freshness hook passed. Both testcase `tc/pr-7925` branches contain their latest `feature/oos-merge` baseline. No existing same-PR gha-ci run was active before triggering.

Exactly one [`/run all`](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-6031371655) was posted at **2026-10-07 05:09:55 UTC**. Pickup was verified on [gha-ci run 37574973482](https://github.com/CUBRID/cubrid/actions/runs/37574973482): both build contexts and `test_shell`, `test_sql`, `test_medium` all point to that run and were pending at 05:10:13–05:10:15 UTC. The five ordinary GitHub checks passed. This is trigger/pickup evidence, not a claim that the regression suites have passed.

The live `gh pr checks --required` query returns exit 1 and `no required checks reported on the 'CBRD-27424-oos-loaddb-sa' branch`. The stable gha-ci release-build and three-suite gate is present but still pending; absence of configured required checks does not establish merge readiness. The [CI receipt and status snapshot](evidence/workspace-oos-restoration-2026-10-07/ci-pickup.json) retain exact head, context links and states.

Item **286** covers the completed restoration, local verification, publication, PR summary and verified CI pickup. Parent item **267** remains waiting for the new exact-head CI results and broader PR-readiness work.
