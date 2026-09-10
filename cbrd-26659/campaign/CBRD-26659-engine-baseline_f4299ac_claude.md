# CBRD-26659 — Campaign engine baseline pin and boundary table (ticket 11)

> Observed: 2026-09-10 (KST). Engine baseline: `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (`origin/feat/oos`).
> Author: Claude Fable 5.1, session `session_01Wq38qC19cw3fGeq1oCFqjJ`, for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 11.
> Scope: pin, build, verify, derive, record. No engine source was modified, no database outside this ticket's own directory was touched, nothing was pushed.
> Evidence: [`ticket11-evidence/`](ticket11-evidence/) (derivation script and output, probe script, raw probe outputs for both builds, normative snapshot with hashes).

Every campaign run cites this record for its engine identity. Vocabulary follows the [docs glossary](../../CONTEXT.md): Capability gap, Specification gap, Engine defect, Delivery gap, Campaign acceptance. The ticket asks for each conformance observation to be classified as *conforming*, *gap* or *observation*; every *gap* below is mapped to its glossary kind, and "BLOCKED" is used only as the campaign spec's per-attempt outcome word (BLOCKED, UNSUPPORTED, SKIP, PASS, FAIL), never as a synonym for a gap kind.

## 1. Engine baseline

| Item | Value |
|---|---|
| Canonical origin | `https://github.com/CUBRID/CUBRID` (remote `origin` of the local clone) |
| Remote tip verified | `git ls-remote https://github.com/CUBRID/CUBRID refs/heads/feat/oos` → `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`; `git fetch origin feat/oos` returned the same object |
| **Campaign engine baseline** | **`f4299ac0cd777a2a964c1f197ae5ebf9841a4936`** — "Merge origin/develop into feat/oos" |
| Coordinating worktree | `/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover` at `07fef9d48b4776e60c42e8afa25b9f21c54b8226`. It is an ancestor of the pin, 157 commits behind. **It is not the baseline**; it holds only the planning record under `.scratch/oos-adversarial/`. |
| **Pinned engine worktree** | **`/home/vimkim/gh/cb/oos-baseline-f4299ac0c`**, detached HEAD at the baseline SHA (created with `git worktree add --detach`). A detached checkout cannot drift when `feat/oos` moves. |
| Pinned worktree cleanliness | `git diff --stat HEAD` shows no tracked engine file changed. The only status entry is the `cubrid-cci` submodule, whose generated `win/cci_version.h` is rewritten by the CCI build (the coordinating worktree shows the same artifact). Personal build tooling (`justfile`, `.envrc`, `.just/`, `CMakeUserPresets.json`, `local.just`, `lefthook.yml`, `cub_server.gdb`) is present as git-excluded symlinks and is not source. |
| Instrumentation worktree (ticket 16) | Not created here. It must be a third worktree at the same SHA; the pinned worktree above is reserved for unmodified-engine runs. |
| Other worktrees | Untouched. Two other worktrees also sit at the same SHA: `/home/vimkim/gh/cb/oos-storage` (branch `feat/oos`, untracked files, movable branch ref) and `/home/vimkim/gh/cb/CBRD-27237-oos-rollback-vacuum-delete` (a defect-repair branch). Neither was reused as the baseline: both carry movable branch refs and their own work. |
| Work tracker | Item 109 (campaign) carries the ticket 11 notes. |

## 2. Unmodified builds and binary identity

Both builds come from the pinned worktree, the same source tree, the same toolchain (gcc 11.5.0, cmake 3.26.5, ninja 1.10.2, ccache) and the same configure options; only the CMake build type and its flags differ.

| | Release | Debug |
|---|---|---|
| CMake configure preset (personal `CMakeUserPresets.json`) | `release_gcc` | `debug_gcc` |
| `CMAKE_BUILD_TYPE` | `RelWithDebInfo` (`-O2 -ggdb3 -DNDEBUG -finline-functions`) | `Debug` (`-O0 -ggdb3 -fno-omit-frame-pointer`) |
| Build directory | `oos-baseline-f4299ac0c/build_preset_release_gcc` | `oos-baseline-f4299ac0c/build_preset_debug_gcc` |
| Install prefix (`$CUBRID`) | `~/.cub/install/oos-baseline-f4299ac0c/release_gcc` | `~/.cub/install/oos-baseline-f4299ac0c/debug_gcc` |
| `VERSION_STRING` (`build_preset_*/version.h`) | `11.5.0.2648-f4299ac`, `BUILD_TYPE release` | `11.5.0.2648-f4299ac`, `BUILD_TYPE debug` |
| `cubrid_rel` output | `CUBRID 11.5.0 (11.5.0.2648-f4299ac) (64bit release build for Linux) (Sep 10 2026 16:19:43)` | `CUBRID 11.5.0 (11.5.0.2648-f4299ac) (64bit debug build for Linux) (Sep 10 2026 16:15:40)` |
| sha256 `bin/cub_server` | `d7e6862666eae693c8832c07e1887cc3557b1523862d7bae088d9690b9433529` | `0edcc7a3947688886688f45bffcaeebc75ad2e9dc846f04a04b58b7abd2d24ac` |
| sha256 `bin/csql` | `e9d992382894ed0b5351f7caf1333b89aeb9322034936a7c7e040a386e8d45f6` | `8fcce3c15261307bc5faba9d64e283cd5a903e0e7585c11849e605f6cfcc489c` |
| sha256 `lib/libcubrid.so` | `a3256a7a40748752165e65a395b8aebcf8d85e00b87ee62e68bf75e1a5c85444` | `27399fae11a5ef134ba303e5ac6d672748b224bdf593504a2d4fae533a357253` |
| sha256 `lib/libcubridsa.so` | `8009c322633055df41af045fe560a86f1f8171648863d11f2e44d949e3cdd76e` | `9a3db918bc01738666bbb1ede762da973a714090c15e6709c78b7dc9c825ba69` |

**Why the binaries prove the SHA.** `CMakeLists.txt` at the pin runs `git rev-parse --short=7 HEAD` on the source tree at configure time and embeds the result as `-f4299ac` in `CUBRID_VERSION`, which becomes `VERSION_STRING` and is compiled into `libcubrid.so` and `libcubridsa.so`; `cubrid_rel` prints it. Both installs print `11.5.0.2648-f4299ac`, and the same string is present as data in both shared libraries (`strings -a lib/libcubridsa.so`). All version outputs, hashes and the gdb struct sizes of §5 are recorded in [`binary-identity.txt`](ticket11-evidence/binary-identity.txt). A build directory alone was not used as proof.

**Identity-check pitfall for run records.** Every CUBRID executable, `cubrid_rel` included, reports the version of the shared library the dynamic loader resolves, not of its own file. Run with the login environment (which puts the coordinating worktree's install on `LD_LIBRARY_PATH`), the pinned install's `cubrid_rel` printed `11.5.0.2491-07fef9d (64bit debug build) (Aug 14 2026)`. Identity checks in run records must therefore set `CUBRID`, `PATH` and `LD_LIBRARY_PATH` to the install under test (as `probe_boundaries.sh` does) and should record the sha256 of `lib/libcubrid.so` and `lib/libcubridsa.so`, not only of the executables. The `cub_server` start-up banner prints `11.5.0.2648` without the hash.

**Configure options recorded for both builds.** `UNIT_TEST_OOS=ON`, `UNIT_TEST_SPAGE=ON`, `UNIT_TEST_PAGE_BUFFER=ON`, `UNIT_TESTS=OFF`, `WITH_CCI=true`, `VIMKIM_BUILD=ON`, `CUBVEC_TEAM_BUILD=ON`, `ENABLE_CUBVEC_LOG=ON`. Two of these matter for the campaign:

- `UNIT_TEST_OOS` is **ON by default in the pinned source itself** (`CMakeLists.txt:74`), and any enabled `UNIT_TEST_*` option sets `AT_LEAST_ONE_UNIT_TEST`, which adds the `CUBRID_UNIT_TEST_ENABLED` compile definition to the whole engine (`CMakeLists.txt:789-792`). Consequently both "unmodified" engine libraries export the OOS test seams `oos_test_fail_insert_many_after_publications` and `oos_test_throw_bad_alloc_on_next_oid_publication` and the debug counters declared in `oos_file.hpp`. These seams are C entry points with no SQL or parameter trigger; they are reachable from unit tests only. "Unmodified" here means unmodified source with the source's default options. A variant configured with `-DUNIT_TEST_OOS=OFF` was not built; ticket 17 should decide whether the campaign's release configuration needs it (decision request, see §9).
- `WITH_CCI=true` initialises the `cubrid-cci` submodule, which is the source of the modified `win/cci_version.h` noted in §1.

**Page sizes are a database parameter, not a build parameter.** `IO_MIN_PAGE_SIZE` is 4 KiB, `IO_MAX_PAGE_SIZE` and `IO_DEFAULT_PAGE_SIZE` are 16 KiB (`storage_common.h:91-93`); the size is chosen per database by `cubrid createdb --db-page-size`. One binary per build mode therefore serves 4, 8 and 16 KiB. Feasibility at the pin:

| Configuration | Release | Debug |
|---|---|---|
| 16 KiB, standalone (`csql -S`, `diagdb`, `spacedb -S`, `checkdb -S`) | runnable (database `br16k`) | runnable (database `bd16k`) |
| 8 KiB, standalone | runnable (`br8k`) | runnable (`bd8k`) |
| 4 KiB, standalone | runnable (`br4k`) | runnable (`bd4k`) |
| 16 KiB, client-server (`cub_master`/`cub_server` on private port 26659) | runnable; `SHOW HEAP OOS` answered over the network; server and master stopped cleanly | runnable, same |
| 4 and 8 KiB, client-server | not exercised here — pending for ticket 17 | pending for ticket 17 |

All six databases live under `~/.cub/db/oos-baseline-f4299ac0c/commondb` (64 MiB data, 32 MiB log each) and are disposable evidence; `checkdb -S` passed on every one of them (`ticket11-evidence/probes-*/checkdb_*.txt`, each ending `checkdb exit=0`). The first debug pass ran `spacedb`/`checkdb` in client-server mode by mistake and failed to connect; those two utilities were re-run in standalone mode for the debug databases and the outputs replaced before this record was finalised.

## 3. Normative context revision, content hash, ADRs

| Item | Value |
|---|---|
| Context repository | `/home/vimkim/gh/cubrid-oos-context` |
| Committed HEAD | `f6543de680b91ae357466b72a983f982892859cd` (2026-09-01, "CBRD-27350 is the ticket of record…") |
| `OOS-CONTEXT.md` working copy | **Modified and uncommitted** at pin time: 41 insertions, 32 deletions versus HEAD. It carries the 2026-09-09 identity-layout reconciliation (24-byte stub and chunk header, CBRD-26950 policies, CDC/flashback decision) that the campaign spec already relies on. Header reads `Last updated: 2026-09-09`. |
| **Pinned normative content hash** (working copy) | **sha256 `c9daf3c4ed25e16356ebf3c79c55f6bb7391d76c5664675a9aaf55cd5ac11698`** |
| Committed blob hash at HEAD (for contrast) | sha256 `d7d3259d647bb2ed0ee9b45f336863266573fcbac952e21ad1b40e21fa55cbaf` |
| Snapshot | [`ticket11-evidence/normative-snapshot/OOS-CONTEXT.md`](ticket11-evidence/normative-snapshot/OOS-CONTEXT.md) plus the four ADRs and [`SHA256SUMS`](ticket11-evidence/normative-snapshot/SHA256SUMS), so the pinned hash stays resolvable even if the working copy changes before it is committed. |

Accepted ADRs at pin time (all carry `status: accepted`):

| ADR | Title | Tracking state in the context repository | sha256 |
|---|---|---|---|
| 0001 | OOS pages use a non-numerable file enumerated by a sector-bitmap scan | tracked at HEAD | `9531a213d24c44353902264de5840dd65c170246a64ff968adec797d29598e55` |
| 0002 | BLOB/CLOB locator columns remain OOS-demotable | tracked at HEAD | `2bdcbce486a97f29acbd4a75d5f45858d0f09205b886480238db22930810e528` |
| 0003 | OOS record expansion is opt-in for raw-byte consumers | tracked at HEAD | `09a8649904e63094fa39f984e5290ccbd9dc68bc930bef916b780b4274605585` |
| 0004 | Preserve OOS historical values in supplemental images (accepted 2026-09-08) | **untracked** (`??` in `git status`) | `2a4b94c06782e17db1cfeab3a5d953617730873dcabb6d8ad928e23e7e50c155` |

**Provenance observation for the user.** Requirement IDs (ticket 12) must cite `f6543de` **plus** content hash `c9daf3c4…`, because the 24-byte wording exists only in the uncommitted working copy, and ADR-0004 is not yet under version control. Committing the context working copy and ADR-0004 would let later citations name a committed revision. This ticket did not edit or commit anything in the context repository (out of scope by the spec).

## 4. Conformance observations re-verified at the pin

Source citations are `git show f4299ac0cd777a2a964c1f197ae5ebf9841a4936:<path>` line numbers. "Empirical" refers to the probe outputs in `ticket11-evidence/probes-{debug,release}/`, identical between the two builds.

| # | Subject | Normative requirement | Pinned source | Empirical at the pin | Classification |
|---|---|---|---|---|---|
| a | Record gate | Four-record physical target `heap_oos_inline_target_size()` (4,060 B at 16 KiB), CBRD-27057, OOS-CONTEXT §1 | `heap_file.c:12350` and `:12383` still compare `header_size + payload_size + mvcc_extra` with `DB_PAGESIZE / 4`. `heap_oos_inline_target_size` does not exist; `heap_nonheader_page_capacity()` exists (`heap_file.c:27567`) but is not used by the gate. | Schema A value N = 4,012 B (8 KiB: 1,964; 4 KiB: 940) stays inline (`Oos_num_recs` 0) although the normative target would demote it; N = 4,036 / 1,988 / 964 goes out of row. | **Gap → Capability gap**: the pinned engine cannot exhibit the accepted target, so the requirement is unreachable on it. Cases at the normative boundary take the BLOCKED outcome; results inside the disputed band (§5) must never be promoted from engine output. |
| b | Placement hints | Context lists `STORAGE PREFER_INLINE` (CBRD-26912) as proposed and not merged; `FORCE_OUTLINE` is not an accepted design | Grammar accepts `STORAGE PREFER_INLINE` and `STORAGE FORCE_OUTLINE` (`csql_grammar.y:10574-10582`, `parse_tree.h:1950-1951`); `heap_attrinfo_determine_disk_layout` implements a FORCE_OUTLINE bypass of the record gate and PREFER_INLINE demotion priority. | Table `h` with `q BIT VARYING STORAGE FORCE_OUTLINE`: a 40-byte value in a record far below the gate was demoted (`Oos_num_recs` 1, `Oos_recs_sumlen` 64). | **Observation** — implemented behaviour beyond accepted policy. Recorded, not asserted as correct. Coverage of these hints requires a decision ticket on the map (spec authority policy). |
| c | Reclaim mechanisms | Empty-page reclaim invariant with vacuum fast path, LSA reclaim gate and growth-gate sweep (CBRD-26786); context marks it "pending merge" | Present: `oos_reclaim_lsa_gate_passes` (`oos_file.cpp:1512`), `oos_reclaim_empty_pages` (`:1726`), `oos_reclaim_sweep_step` (`:1819`), `oos_alloc_page_with_reclaim` (`:2015`), per-VFID `pending_deletes` growth-gate bookkeeping (`:1281-1377`). | After a standalone-mode `DELETE FROM a_out`, `Oos_num_recs` dropped to 0 while `Oos_num_user_pages` stayed 2 — deferral consistent with the LSA gate. Eventual reclamation was not tested here. | **Conforming (mechanisms present)**; the context's "pending merge" note is stale for this pin. The invariant's *eventuality* remains for the reclaim cases to prove. |
| d | Identity layout | 24-byte inline stub and 24-byte chunk header with page-LSA identity stamp (CBRD-26950, accepted 2026-09-04) | `OR_OOS_INLINE_SIZE = OR_OID_SIZE + OR_BIGINT_SIZE` = 16 (`object_representation.h:466`); `struct oos_record_header {int; int; OID}` = 16 B (`oos_file.hpp:28-33`, gdb `sizeof` = 16 in both libraries); `oos_delete` takes no expected identity (`oos_file.cpp:3233`). | `Oos_recs_sumlen` = payload + 16 per chunk (for example 4,044 + 16 = 4,060; two chunks 16,292 + 32 = 16,324). | **Gap → Capability gap**: accepted design not on the pin (PR #7695 unmerged), so identity-stamp requirements are unreachable and their cases take the BLOCKED outcome. CBRD-26950 remains an expected Engine defect. |
| e | Eligibility floor | Value strictly greater than 24 B (follows from d) | `column_size > OR_OOS_INLINE_SIZE` with the 16-byte constant (`heap_file.c:12359`) | 15-byte `BIT VARYING` stays inline; 16-, 23- and 24-byte values are demoted (`Oos_recs_sumlen` 36, 40, 44). Normatively only the 24-byte value may be demoted. | **Gap → Capability gap**, same root cause as d. Cases in the 16–23 byte band take the BLOCKED outcome; their engine output must not be promoted. |
| f | UPDATE chain reuse and vacuum cleanup | Commit-conditional `RVOOS_NOTIFY_VACUUM` emission; forward-walk removed (CBRD-27230, accepted) | Forward walk present (`vacuum_oos.cpp:154`, `:275`, `oos_chunk_exists` probe at `:181`); no notify emitter. | Not exercised (needs client-server vacuum schedules; private shell tickets). | **Gap → Capability gap**: accepted design not on the pin, so its requirements are unreachable and their cases take the BLOCKED outcome. CBRD-27237 remains an expected Engine defect. |
| g | Error code of the OOS + bigone rejection | Context text says `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` is -1375 | `error_code.h:1782`: **-1382**; `ER_LAST_ERROR` -1385. Message: "The record cannot be stored because its size (%1$d bytes) still exceeds the maximum record size (%2$d bytes) even after moving large variable-length columns to out-of-row storage (OOS). Reduce the size of fixed-length or non-eligible columns." | Rejection observed with exactly this text at all three page sizes (§5). | **Observation** — context drift; expected-error cases must use the pinned code and text. Report to the context maintainer. |

Also confirmed for the run-record: `SHOW HEAP OOS OF <class>` / `SHOW ALL HEAP OOS` exist at the pin (`csql_grammar.y:7558-7565`, `show_scan.c:173-182`), and `FILE_OOS` owner descriptors exist (`file_manager.c:1407-1409`), superseding the context's "no release tool proves OOS placement" statement at the per-class level (per-attribute placement is still not observable in release builds).

## 5. Boundary table

Derived from the pinned engine's serialized record accounting by [`oos_boundaries.py`](ticket11-evidence/oos_boundaries.py) (full output: [`boundary-derivation.md`](ticket11-evidence/boundary-derivation.md)). Every struct size the derivation uses was confirmed with gdb on the pinned debug `libcubrid.so` (recorded in [`binary-identity.txt`](ticket11-evidence/binary-identity.txt)): `spage_header` 32, `spage_slot` 4, `heap_chain` 40, `oos_record_header` 16, `fileio_page_reserved` 32, `fileio_page_watermark` 8, `OID` 8, `VPID` 8. The probe script no longer carries its own copy of the boundary numbers; it reads them from `oos_boundaries.py --probe-rows`.

### 5.1 Page-level constants

| Quantity | Source at the pin | 4 KiB | 8 KiB | 16 KiB |
|---|---|---:|---:|---:|
| `IO_PAGESIZE` (createdb `--db-page-size`) | `storage_common.h:91-93` | 4,096 | 8,192 | 16,384 |
| `DB_PAGESIZE` = IO − 40 (reserved 32 + watermark 8) | `storage_common.c:44-48`, `file_io.h:165-186` | 4,056 | 8,152 | 16,344 |
| `spage_max_record_size()` = DB_PAGESIZE − 32 − 4 | `slotted_page.c:841-843` | 4,020 | 8,116 | 16,308 |
| `heap_nonheader_page_capacity()` = above − 40 | `heap_file.c:27567` | 3,980 | 8,076 | 16,268 |
| `heap_Maxslotted_reclength` = ALIGN_BELOW(spage_max − ALIGN(40,4) − 8·4, 4); longer records become `REC_BIGONE` | `heap_file.c:3714` | 3,948 | 8,044 | 16,236 |
| **Record gate, pinned** = `DB_PAGESIZE / 4` | `heap_file.c:12350,12383` | **1,014** | **2,038** | **4,086** |
| **Record gate, normative four-record target** = ALIGN_BELOW((capacity − 4·4)/4, 4) | OOS-CONTEXT §1 (CBRD-27057) | **988** | **2,012** | **4,060** |
| **Max single-chunk payload, pinned** = ALIGN_BELOW(spage_max, 8) − 16 | `oos_file.cpp:3249-3255`, `OOS_ALIGNMENT` = 8 (`:124`) | **4,000** | **8,096** | **16,288** |
| Max single-chunk payload, normative 24-byte chunk header | OOS-CONTEXT §2 layout | 3,992 | 8,088 | 16,280 |

Page-size-independent boundaries:

- **Eligibility floor.** Pinned: serialized value > 16 B (`OR_OOS_INLINE_SIZE`). Normative: > 24 B. For `BIT VARYING` the serialized size is ALIGN(1 + N, 4) for N < 32 logical bytes (1-byte length prefix) and ALIGN(5 + N, 4) from N = 32 (5-byte prefix), so in logical bytes the pinned floor is **N ≥ 16** and the normative floor is **N ≥ 24**; N in [16, 23] is the disputed band.
- **VOT width.** `heap_attrinfo_get_record_header_size` (`heap_file.c:12264-12290`) starts with 1-byte offsets and widens to 2 bytes when header + payload exceeds `OR_MAX_BYTE` = **127** (not 255), and to 4 bytes above `OR_MAX_SHORT` = 32,767. Because an OOS-bearing record must stay at or below `heap_Maxslotted_reclength` (16,236 at most), **an OOS-bearing record never uses 4-byte VOT entries at any supported page size**; the 4-byte width is reachable only by non-OOS `REC_BIGONE` records. Record this as a structural exclusion in the matrix rather than as a Delivery gap. The 1→2 byte transition changes the header only when the table has two or more variable columns (VOT = ALIGN(width × (n_var + 1), 4)).
- **Gate arithmetic.** Gate test is `header + payload + mvcc_extra > gate`, with `header = 16 (MVCC insert header) + VOT + bound-bit bytes(⌈n_fixed/32⌉·4)`, `payload = Σ fixed disk sizes + Σ serialized variable sizes`, `mvcc_extra = OR_MVCC_MAX_HEADER_SIZE − OR_MVCC_INSERT_HEADER_SIZE = 16`. After demotion each demoted column contributes the stub size instead of its value. The OOS + bigone check compares `header + payload_after_demotion + 16` with `heap_Maxslotted_reclength` (`heap_file.c:13300-13304`).

### 5.2 Concrete boundaries and their empirical confirmation

Schema A is `CREATE TABLE a (id INT, v BIT VARYING)`; N is the logical byte length of `v`. Schema B is `CREATE TABLE b (id INT, f BIT(8·F), v BIT VARYING)` with a 64-byte `v`; F is the fixed column's byte length. Values were produced with `CAST(REPEAT('XX', N) AS BIT VARYING)`. Every row below was observed identically on the release and the debug build (`ticket11-evidence/probes-*/probe_{16k,8k,4k}.out`).

| Boundary (schema A unless stated) | 4 KiB | 8 KiB | 16 KiB | Observed at the pin |
|---|---:|---:|---:|---|
| Largest N that stays inline (pinned gate) | 963 | 1,987 | 4,035 | `Has_oos_file` 0, `Oos_num_recs` 0 |
| Smallest N demoted (pinned gate) | 964 | 1,988 | 4,036 | `Oos_num_recs` 1; `Oos_recs_sumlen` 988 / 2,012 / 4,060 (= ALIGN(5+N,4) + 16) |
| Smallest N the normative target would demote | 940 | 1,964 | 4,012 | **stays inline at the pin** (`Oos_num_recs` 0) → disputed band [940, 963] / [1,964, 1,987] / [4,012, 4,035] |
| Largest N stored as one chunk (pinned) | 3,995 | 8,091 | 16,283 | `Oos_num_recs` 1, `Oos_recs_sumlen` 4,016 / 8,112 / 16,304, `Oos_num_user_pages` 2 |
| Smallest N needing two chunks (pinned) | 3,996 | 8,092 | 16,284 | `Oos_num_recs` 2, `Oos_recs_sumlen` 4,036 / 8,132 / 16,324, `Oos_num_user_pages` 3 |
| Smallest N needing two chunks (normative 24-byte header) | 3,988 | 8,084 | 16,276 | not observable at the pin |
| Eligibility floor probes (fixed `BIT` pushes the record over the gate; only `s` is a candidate) | 15 B inline; 16, 23, 24 B demoted | same | same | `Oos_recs_sumlen` 36 / 40 / 44 for 16 / 23 / 24 B |
| Schema B: largest F accepted with `v` demoted | 3,888 | 7,984 | 16,176 | 1 row, `Oos_num_recs` 1, `Oos_recs_sumlen` 88 |
| Schema B: smallest F rejected (`ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`, -1382) | 3,889 | 7,985 | 16,177 | error text reports `3949 > 3948` / `8045 > 8044` / `16237 > 16236`; 0 rows; no OOS file created (rejection precedes chunk writes) |
| Schema B rejection under the normative 24-byte stub (derived only) | 3,881 | 7,977 | 16,169 | not observable at the pin |
| Smallest N switching schema A to 2-byte VOT entries | 92 | 92 | 92 | not observable through SQL; derived |

Worked derivation for schema A at 16 KiB, pinned engine: header = 16 + ALIGN(1·2, 4) + 4 = 24; payload = 4 + ALIGN(5 + N, 4); gate `24 + 4 + L + 16 > 4,086` ⇔ `L ≥ 4,044` ⇔ `N ≥ 4,036`. Normative: `L > 4,016` ⇔ `N ≥ 4,012`. The probe's `DISK_SIZE(v)` returned 4,040 / 4,044 / 4,020 for N = 4,035 / 4,036 / 4,012, confirming the serialized-length formula and confirming that `DISK_SIZE` reports the logical serialized size regardless of placement (it is not a placement oracle).

**How case authors use this table.** Derive every size from `oos_boundaries.py` for the schema actually used (the script's `layout()` mirrors `heap_attrinfo_determine_disk_layout`), never from SQL string length. Assert the pinned boundary only where pinned and normative agree; inside a disputed band the requirement is a Capability gap of the pinned engine, the case takes the BLOCKED outcome, and its engine output is retained as evidence, not promoted to an answer.

## 6. Evidence channels exercised once (candidates, not oracles)

| Channel | Builds | Mode | What it exposed at the pin | Limits |
|---|---|---|---|---|
| `SHOW HEAP OOS OF <class>` (DBA) | release, debug | standalone and client-server | Per class: `Has_oos_file`, OOS VFID, `Oos_num_user_pages`, `Oos_page_size`, `Oos_num_recs` (chunk records), `Oos_recs_sumlen` (payload + 16 B header per chunk), physical and unused bytes. Confirmed gate, chunk-split and floor boundaries; also showed eager deletion (`Oos_num_recs` 1 → 0) and deferred page release. | Per class, not per row or per attribute; requires DBA; counts chunks, not values. Strong activation evidence when combined with an isolated table per case. |
| `cubrid diagdb -d 1` / `-d 2` | release, debug | standalone only | `-d 1` (file tracker dump) prints the owner descriptor `CLASS_OID … (dba.<class>), OOS for HFID …`; `-d 2` lists each OOS file as `OUT_OF_LINE_OVERFLOW_STORAGE` with its page count. Eight OOS files per probe database were attributed to their classes. | Whole-database dump (~190 KiB, ~2,900 lines per `-d 1` run); offline only. The repository keeps the `-d 2` outputs in full and only the OOS excerpts of `-d 1`; the six full `-d 1` dumps live under `~/.cub/db/oos-baseline-f4299ac0c/evidence/ticket11/` and are referenced by [`diagdb-d1-full-dumps.SHA256SUMS`](ticket11-evidence/diagdb-d1-full-dumps.SHA256SUMS). |
| `cubrid spacedb -S -p` | release, debug | standalone | Totals only; OOS files are folded into the `HEAP` row (53 heap files reported where 45 are heaps and 8 are OOS files). | No OOS category (CBRD-27350 T1 gap); cannot attribute space to OOS. Weak channel. |
| `cubrid checkdb -S` | release, debug | standalone | Passed (`checkdb exit=0`) on all six databases after the probes. | Consistency only; says nothing about placement. |
| Debug `$CUBRID/log/oos.log` (`oos_trace/debug/info`, compiled out under `NDEBUG`) | debug only | any | **Not written by the SQL INSERT path at the pin.** The heap writer calls `oos_insert_many` (`heap_oos.cpp:653`), which has no `oos_debug` calls; the `oos_insert … src.size=` line the context cites (`oos_file.cpp:2086`) is reached only from the HA applier (`locator_sr.c:5326`). DELETE and UPDATE in standalone mode did write it: `heap_recdes_get_oos_oids` (debug-only, `heap_file.c:28364,28388`), `oos_delete` (`:3236`) and `oos_delete_chain` (`:3135`) lines ([`probes-debug/oos.log`](ticket11-evidence/probes-debug/oos.log)). Default level is DEBUG, so the 11 `oos_trace` sites (bestspace hints, file creation) are suppressed; `oos_log_set_level` is called only from unit tests (`unit_tests/oos/test_oos*.cpp`), never from the engine, so there is no runtime or parameter control over the level. | Delete-side channel only at the pin; no insert-side line; no runtime level control. Release builds cannot produce it. |
| `oos_warn` / `oos_error` → server error log | release, debug | any | Always compiled; none fired during the probes (expected on the happy path). | Failure-side only. |
| `CUBRID_UNIT_TEST_ENABLED` counters and seams | release, debug (both, see §2) | unit tests only | Symbols present in both libraries; not exercised. | No SQL or parameter trigger; ticket 16 decides whether they count as "existing controls". |
| `DISK_SIZE()` | release, debug | any | Returns the serialized logical size (4,040 / 4,044 / 4,020) regardless of placement. | Not a placement oracle; useful only to verify size arithmetic. |
| Whole-value equality (`v = CAST(REPEAT(...))`) | release, debug | any | Every probe value read back equal after demotion, chunk split, eager delete of a sibling row and client-server access. | Correctness oracle, not activation evidence. |

## 7. Reproduction

```bash
# 1. pin (already done; shown for audit)
git -C /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover ls-remote https://github.com/CUBRID/CUBRID refs/heads/feat/oos
git -C /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover worktree add --detach /home/vimkim/gh/cb/oos-baseline-f4299ac0c f4299ac0cd777a2a964c1f197ae5ebf9841a4936

# 2. builds (CMake presets debug_gcc / release_gcc from the personal CMakeUserPresets.json; ccache-backed)
#    Both installs already exist under ~/.cub/install/oos-baseline-f4299ac0c/{debug_gcc,release_gcc}.
#    The worktree's .env selects debug_gcc by default; set PRESET_MODE=release_gcc to work on the release tree.

# 3. identity check before every campaign run -- the loader environment must point at the install under test
for b in release_gcc debug_gcc; do
  C=~/.cub/install/oos-baseline-f4299ac0c/$b
  CUBRID=$C PATH=$C/bin:$PATH LD_LIBRARY_PATH=$C/lib:$C/cci/lib $C/bin/cubrid_rel   # expect 11.5.0.2648-f4299ac and the matching build type
  sha256sum $C/lib/libcubrid.so $C/lib/libcubridsa.so                              # compare with ticket11-evidence/binary-identity.txt
done

# 4. boundary probes (creates <prefix>{16k,8k,4k} under ~/.cub/db/oos-baseline-f4299ac0c/commondb;
#    side effect: sets cubrid_port_id=26659 in <install>/conf/cubrid.conf; optional `cs` starts one 16 KiB server)
bash ticket11-evidence/probe_boundaries.sh ~/.cub/install/oos-baseline-f4299ac0c/debug_gcc   bd /tmp/out-debug   cs
bash ticket11-evidence/probe_boundaries.sh ~/.cub/install/oos-baseline-f4299ac0c/release_gcc br /tmp/out-release cs

# 5. debug oos.log probe (delete side; produces $CUBRID/log/oos.log on the debug install only)
C=~/.cub/install/oos-baseline-f4299ac0c/debug_gcc
CUBRID=$C CUBRID_DATABASES=~/.cub/db/oos-baseline-f4299ac0c/commondb PATH=$C/bin:$PATH LD_LIBRARY_PATH=$C/lib \
  csql -S -u dba bd16k -c "UPDATE c1 SET v = CAST(REPEAT('EF', 5000) AS BIT VARYING); DELETE FROM a_out; SHOW HEAP OOS OF a_out; SHOW HEAP OOS OF c1;"
cat $C/log/oos.log        # compare with ticket11-evidence/probes-debug/ooslog-delete-probe.txt

# 6. derivation (also feeds the probe script through --probe-rows)
python3 ticket11-evidence/oos_boundaries.py
```

Bulky evidence policy: raw outputs small enough to read stay in `ticket11-evidence/`; the six full `diagdb -d 1` dumps (1.1 MiB together) live under `~/.cub/db/oos-baseline-f4299ac0c/evidence/ticket11/` with a `SHA256SUMS` file whose copy is committed here, following the spec's rule that bulky bundles live under `/home` and are referenced by path and hash.

Tooling note (personal environment, not project workflow): the worktree bootstrap script failed on the fresh detached worktree because its `stow` step ran in the shared package directory instead of the worktree. The prepare step was done by hand (`stow --dir=$HOME/my-cubrid/stow --target=<worktree> cubrid` and `gdb`, then `stow-create.sh`, `git submodule update --init cubrid-cci`, `direnv allow`, `lefthook install`), after which the bootstrap configured and built normally.

## 8. Ticket 11 criteria checklist

| Criterion | Status |
|---|---|
| Remote `feat/oos` tip verified against the canonical origin and recorded; coordinating worktree recorded as not the baseline | met (§1) |
| Dedicated engine worktree at the pin, distinct from the coordinating and the (future) instrumentation worktree; existing worktrees untouched | met (§1) |
| Unmodified release and debug builds at 16 KiB; a binary from each proven to correspond to the SHA; 4 and 8 KiB feasibility recorded | met (§2). Page size is a createdb parameter; 4/8/16 KiB databases created and probed on both builds; client-server at 4/8 KiB left to ticket 17 |
| Normative context revision and content hash, accepted ADR list | met (§3), with a provenance observation about the uncommitted working copy and untracked ADR-0004 |
| Three conformance observations re-verified and classified with source evidence | met (§4): record gate = gap (Capability gap), placement hints = observation, reclaim mechanisms = conforming (present); plus four further findings (d–g) |
| Boundary table for 4, 8, 16 KiB with derivation shown | met (§5), derived and empirically confirmed on both builds |
| Debug OOS logging and release diagnostics exercised once; recorded as candidate channels | met (§6), including the finding that the INSERT path does not write `oos.log` at the pin |
| Record committed to the docs repository under the CBRD-26659 folder using the glossary vocabulary | this file and `ticket11-evidence/` |
| Nothing pushed; no engine source modified in the pinned worktree | confirmed (§1; `git diff --stat HEAD` clean apart from the CCI submodule's generated header) |

## 9. Hand-offs and decision requests

- **Ticket 12 (requirement catalogue):** cite `f6543de` + `c9daf3c4…` and the snapshot; use the pinned error code -1382 and message text; record findings a, d, e, f as Capability gaps of the pinned engine whose cases take the BLOCKED outcome, and g as a context-drift note.
- **Ticket 16 (instrumentation):** create a third worktree at the pin. The `CUBRID_UNIT_TEST_ENABLED` seams already compiled into both unmodified builds are not runtime controls; count them as existing controls only if a trigger path exists.
- **Ticket 17 (timings, configuration domain):** client-server at 4 and 8 KiB, and standalone versus client-server timings, remain to be measured. Databases and the probe script above are reusable.
- **Decision requests for the map (not settled here):** whether the campaign's "unmodified release" must be configured with `-DUNIT_TEST_OOS=OFF`; whether `STORAGE PREFER_INLINE` / `FORCE_OUTLINE` coverage is in scope given they exceed accepted policy.
- **User action:** commit the 2026-09-09 `OOS-CONTEXT.md` working copy and ADR-0004 in the context repository; report the -1375 → -1382 error-code drift and the stale "pending merge" reclaim note to the context maintainer.
