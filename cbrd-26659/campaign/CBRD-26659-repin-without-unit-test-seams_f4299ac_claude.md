# CBRD-26659 — Re-pinning the campaign build without the unit-test seams (ticket 41)

> Observed: 2026-09-14 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` — **unchanged**; normative context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…`.
> Author: Claude Opus 5 (1M context), session `41260474`, for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 41, carrying out [ticket 39](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/issues/39-build-configuration-and-scope.md) item 1.
> Scope: build configuration and identity only. No engine source was modified, no recorded record or sealed evidence was edited, nothing was pushed.
> Records: [`evidence/ticket41/`](evidence/ticket41/) — three manifests, three attempt records, three replay-bundle indexes, the matrix seed and the merged matrix. Identity evidence: [`ticket11-evidence/repin-nounit/`](ticket11-evidence/repin-nounit/). Site re-verification: [`evidence/ticket41/instr-sites/`](evidence/ticket41/instr-sites/).
> Companions: [engine baseline §10](CBRD-26659-engine-baseline_f4299ac_claude.md#10-revision-2-2026-09-14-the-re-pinned-build-without-the-unit-test-seams) is the authoritative identity record; this document is the ticket's account of the change.

Vocabulary follows the [docs glossary](../../CONTEXT.md): Capability gap, Delivery gap, Outcome, Campaign manifest, Coverage matrix, Attempt record, Replay bundle, OOS-path evidence.

## 1. What changed, and what did not

The campaign's "unmodified" engine was unmodified *source* built with the source's default options, and `UNIT_TEST_OOS` is ON by default at the pin. Any enabled `UNIT_TEST_*` option compiles `CUBRID_UNIT_TEST_ENABLED` into the whole engine, so both pinned installs exported the OOS test seams and the debug counters — not what a customer runs. Ticket 39 chose the strictest of three options: rebuild both installs without them and re-pin.

**Unchanged.** The engine baseline commit, the worktree, the source, the normative context and its hash, the requirement catalogue, the boundary table, and every requirement citation. The pinned worktree's `git diff --stat HEAD` is as clean as ticket 11 recorded it.

**Changed.** The build identity: four configure options, and therefore every library, executable and hash. Ticket 15's tooling now verifies the new hashes. The instrumentation build follows, so instrumented and regression runs still differ only by the patches.

**Not over-written.** Both new builds went to **new install prefixes**. The ticket 11 installs are left in place, byte-identical, so the four invocations that cite them stay reproducible.

## 2. The builds

Both were configured through CMake presets that **inherit** `release_gcc` and `debug_gcc` and set only the four options OFF, so "nothing else changed" is structural rather than transcribed by hand.

| | Release | Debug |
|---|---|---|
| Preset | `release_gcc_nounit` (inherits `release_gcc`) | `debug_gcc_nounit` (inherits `debug_gcc`) |
| Install prefix | `~/.cub/install/oos-baseline-f4299ac0c/release_gcc_nounit` | `~/.cub/install/oos-baseline-f4299ac0c/debug_gcc_nounit` |
| `lib/libcubrid.so` | `1bbbe446…` | `30c52062…` |
| `lib/libcubridsa.so` | `559a955e…` | `bc0de923…` |
| `bin/cub_server` | `824083bf…` | `4bb61423…` |
| `bin/csql` | `4a25ee3b…` | `91315d4d…` |

Full identity, including version strings taken with `CUBRID`, `PATH` and `LD_LIBRARY_PATH` pointed at the install under test: [`ticket11-evidence/repin-nounit/binary-identity-nounit.txt`](ticket11-evidence/repin-nounit/binary-identity-nounit.txt), with both configure logs beside it.

### The seams are gone, proven rather than assumed

| Check | Ticket 11 build | Re-pinned build |
|---|---|---|
| `nm -D lib/libcubrid.so \| grep -c 'oos_test_\|heap_oos_test_'` | 11 | **0** |
| the same on `lib/libcubridsa.so` | 11 | **0** |
| `grep -c CUBRID_UNIT_TEST_ENABLED build.ninja` | 1246 | **0** |
| configure log `==== with_unit_tests() =` | ` 1` | *empty* (CMake's false) |
| `lib64/` with gtest and gmock static libraries | present | absent |

The last row was not asked for and is recorded because it is visible: those archives were installed only because the unit tests were enabled, and their absence is a second, independent sign of the same change.

## 3. Identity in the tooling

`campaign_records.py` and `campaign_env.sh` name the re-pinned build, and both CTP wrappers refuse to start against anything else. The ticket 11 hashes did not disappear: they moved to `LEGACY_LIBRARY_HASHES` / `campaign_legacy_hash`, which exist so a record written against the old build still resolves when its bundle is replayed, and so that a run pointed at the old install is refused with a message that names it rather than with an anonymous hash mismatch.

"Recognised" is a code path, not a comment. `recognised_build(build_mode, library_hashes)` answers `repin`, `ticket11` or `None` from the hashes a record carries, and `validate_records.py` now uses it on every manifest: a manifest whose engine matches neither build is a failing record, because its identity proves nothing. On the campaign's 21 manifests it resolves ticket 13's and 14's to `ticket11` and ticket 41's to `repin`, and all 75 records still pass; a manifest with one hash altered fails with the engine named.

`t16env.sh` gained the same shape for the instrumentation install: the re-pinned prefix is the default, and `T16_INSTALL` selects the superseded one for a replay.

**CTP tree identity** ([ticket 37](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/issues/37-invocation-contract.md) item 1). The runner jars and `init.sh` of `/home/vimkim/CTP` joined the identity list and are now *checked*, not only recorded: `campaign_check_ctp` runs in both wrappers beside the port and namespace checks, and `run_ctp_sql.sh` records `init.sh` in `identity.txt` as the shell wrapper already did. The four hashes are in [engine baseline §10](CBRD-26659-engine-baseline_f4299ac_claude.md#10-revision-2-2026-09-14-the-re-pinned-build-without-the-unit-test-seams).

## 4. Tickets 13 and 14 re-run on the new build

Three invocations through ticket 15's wrappers, one per configuration the two tracer bullets recorded. Every one is a fresh run: new database, new bundle, records validated against ticket 12's schemas before they were written.

| Invocation | Case | Runner | Build | Outcome | Proof | Assertions | OOS-path evidence |
|---|---|---|---|---|---|---|---|
| `inv-T41-0001` | `cbrd_26659_oos_rep02_largest_first` | CTP SQL | release, client-server, 16 KiB | PASS | proven | expected 27, executed null (the runner has no counter), failed 0 | `proven` over `show-heap-oos` |
| `inv-T41-0002` | `cbrd_26659_oos_dur01` | CTP shell | release, client-server, 16 KiB | PASS | proven | 17 of 17 OK, 1 SKIP | `proven` over `other` (SHOW HEAP OOS + recovery log) |
| `inv-T41-0003` | `cbrd_26659_oos_dur01` | CTP shell | debug, client-server, 16 KiB | PASS | proven | 18 of 18 OK | `proven` over `other` |

**Set against their predecessors on the old build, nothing observable moved.** `inv-T41-0001` against `inv-T15-0003`, `inv-T41-0002` against `inv-T15-0004`, `inv-T41-0003` against `inv-T14-0004`: the outcome, the proof verdict, the expected and executed assertion counts, the failed count and the evidence status and channel are identical in all three pairs. The differences are the ones that must differ — identities, timestamps, case times, and the hashes of regenerated files. The release shell run's 17-of-18 and the debug run's 18-of-18 are the same split ticket 14 recorded, and it is the documented one: the release build has no `SHOW HEAP OOS`, so one assertion skips.

Each run left the install and the testcase worktree byte-identical (`conf` drift 0, `databases` drift 0, worktree drift 0), and each ran under `campaign_ns.sh`.

### The coverage matrix

[`evidence/ticket41/matrix.json`](evidence/ticket41/matrix.json) carries ten rows: five case rows and five hand-maintained caseless ones. The new attempts joined the histories; none of the recorded ones was touched.

| Row | History after the merge |
|---|---|
| `OOS-REP-01/…/16384-release-cs` | `att-T13-0001` `att-T13-0002` `att-T15-0001` `att-T15-0003` **`att-T41-0001`** — 5 attempts, all PASS |
| `OOS-REP-02/…/16384-release-cs` | the same five |
| `OOS-SQL-01/…/16384-release-cs` | the same five |
| `OOS-DUR-01/…/16384-release-cs` | `att-T14-0026` `att-T14-0029` `att-T15-0002` `att-T15-0004` **`att-T41-0002`** — 5 attempts, all PASS |
| `OOS-DUR-01/…/16384-debug-cs` | `att-T14-0027` `att-T14-0030` **`att-T41-0003`** — 3 attempts, all PASS |

The hand-set gap kinds survived the merge: `OOS-REP-01` and `OOS-REP-02` keep `Delivery gap` under the qualified rule of ticket 13's report, although their latest attempt is a PASS with proven evidence.

**How the matrix was seeded, and why by hand.** `matrix_merge.py` merges manifests into **one** existing matrix, and the campaign's recorded rows live in two: ticket 13's seven and ticket 14's three. Re-merging ticket 14's manifests into ticket 13's matrix would have regenerated ticket 14's rows and dropped its hand-written `OOS-REP-07/-/claim-withdrawn` row — the erasure this ticket forbids. [`evidence/ticket41/seed_matrix.py`](evidence/ticket41/seed_matrix.py) takes the union instead: every row verbatim, in order, refusing on a row-id collision, a differing catalogue or any accepted exclusion. It makes one edit, a hand act on hand-owned rows in a new record: each caseless row gains `hand_maintained: true`, the field ticket 36 item 6 added. The two source matrices are untouched.

## 5. Ticket 16's sites re-verified on the rebuilt instrumentation build

The instrumentation worktree was rebuilt with the same four options OFF, to `~/.cub/install/oos-instr-f4299ac0c/debug_gcc_nounit`. Patch set `t16-set1` is unchanged — `11 files changed, 324 insertions(+), 5 deletions(-)`, the figure ticket 16 recorded — and the worktree's HEAD is still the pin. New identity in [`evidence/ticket16/identity/identity-patched-set1-nounit.txt`](evidence/ticket16/identity/identity-patched-set1-nounit.txt):

| | Ticket 16 build | Rebuilt |
|---|---|---|
| `lib/libcubrid.so` | `dec89384…` | `2b109c9d…` |
| `lib/libcubridsa.so` | `a457e0ff…` | `11f1d728…` |
| `bin/cub_server` | `b626ea55…` | `49485244…` |
| `bin/csql` | `d865f62b…` | `c94cdee4…` |
| OOS test seams exported | 11 | **0** |
| fault-injection symbols exported | 11 | **11** |

Ticket 39 predicted the sites would survive, because the fault-injection facility is gated on `NDEBUG` (`fault_injection.h:33`) and not on the unit-test seams. They did: the symbol count is identical.

All twelve site scenarios were re-run through ticket 16's own runner, each in fault and in fault-disabled control mode — the same criterion ticket 16 used: **the fault run must acknowledge, the control run must not**.

| Site | Code | Fault run | Control run | Fault wall | Ticket 16's verdict, reproduced? |
|---|---|---|---|---|---|
| a1 | 700000 `oos_publish_oos_oid` | acknowledged, reach 1 fired 1 | no acknowledgement | 8.7 s | yes |
| b1 | 700001 `heap_oos_read_grouped_payloads` | acknowledged | none | 7.6 s | yes |
| c1 | 700002 `oos_delete_chain` | acknowledged | none | 11.1 s | yes |
| d1 | 700003 `pgbuf_bcb_flush_with_wal` | acknowledged | none | 33.0 s | yes |
| e1 | 700004 `logpb_write_page_to_disk` | acknowledged | none | 49.9 s | yes |
| f1 | 700005 `oos_insert_many` loop | acknowledged | none | 35.9 s | yes |
| g1 | 700006 `oos_insert_across_pages` | acknowledged | none | 10.4 s | yes |
| h1 | 700007 `heap_attrinfo_insert_to_oos` | acknowledged | none | 9.5 s | yes |
| i1 | 700008 `oos_rv_redo_delete` | acknowledged | none | 65.7 s | yes |
| j1 | 700009 `vacuum_forward_walk_oos_delete_atomic` | acknowledged | none | 29.1 s | yes |
| k1 | 700010 reclaim phase-2 write fix | **did not fire** | none | 25.7 s | yes — still a Capability gap |
| l1 | 700011 redo of `RVOOS_INSERT` at restart | **did not fire** | none | 16.7 s | yes — still a Capability gap |

**No site was lost and no gap was closed.** The ten validated sites acknowledge exactly as ticket 16 recorded — a1's acknowledgement line is byte-for-byte the one quoted in ticket 16 §3, the surrounding NOTIFICATION line differing only in timestamp, pid and source path — and the two Capability gaps (700010, 700011) again did not fire, for the reasons ticket 16 established. Ticket 41's criterion "a site that does not survive is recorded as a Capability gap of the new build" therefore records nothing: there is no such site.

The runner gained one change, so that this re-verification could not write over ticket 16's sealed bulky evidence: `T16_ROOT` selects the output root (default unchanged) and `T16_INSTALL` selects the install (default now the rebuilt one). Everything else is the same script. Because the two edited files are listed in ticket 16's `SHA256SUMS-evidence.txt`, that index was amended: the two hashes were updated and a header records which lines moved, why, and their old values, so `sha256sum -c` passes again on the whole directory. Ticket 16's bulky index does not cover `tools/` and still verifies file for file; no run output, patch, identity file or bulky artifact was touched.

Evidence: [`evidence/ticket41/instr-sites/`](evidence/ticket41/instr-sites/) — the run-all log and, per site and mode, the acknowledgement file and the journal. The bulky remainder (server error logs, cores, workload outputs, the disposable databases) stays under `/home/vimkim/.cub/campaign/cbrd-26659/ticket41-instr/`, indexed by [`SHA256SUMS-bulky.txt`](evidence/ticket41/instr-sites/SHA256SUMS-bulky.txt) (606 files). The re-verification cost about 13.8 GiB; campaign storage stands at 42.32 GiB of the 100 GiB limit.

## 6. What a reader has to do differently now

- **A new run uses the revision-2 identity.** Nothing needs changing in a caller: `campaign_env.sh` and `campaign_records.py` resolve `release`/`debug` to the new prefixes, and both wrappers refuse to start against anything else.
- **Replaying a recorded bundle still works.** The ticket 11 installs are in place and their hashes are still recognised — in `LEGACY_LIBRARY_HASHES`, `campaign_legacy_hash` and, for the instrumentation install, `T16_INSTALL`.
- **Requirement citations did not move.** The commit, the context hash and the catalogue are the same; a citation written before today is still correct.
- **The `.env` of both engine worktrees now selects the `_nounit` preset**, so interactive work in them builds what the campaign runs. `PRESET_MODE=debug_gcc` still builds the superseded configuration if one is wanted.

## 7. Ticket 41 criteria checklist

| Criterion | Status |
|---|---|
| Both installs rebuilt from the same worktree and commit with the four `UNIT_TEST_*` options OFF, nothing else changed, to new prefixes | met (§2); the presets inherit `release_gcc`/`debug_gcc`, so only the four options differ |
| Seams gone, proven: `nm -D` count 0 where it is 11, on both builds; configure log's `with_unit_tests()` false | met (§2), on both libraries of both builds, plus `CUBRID_UNIT_TEST_ENABLED` 1246 → 0 in `build.ninja` |
| New identity recorded as ticket 11 recorded the old: version string with the loader environment set, sha256 of the two libraries, `cub_server` and `csql` | met — [`ticket11-evidence/repin-nounit/binary-identity-nounit.txt`](ticket11-evidence/repin-nounit/binary-identity-nounit.txt) |
| Ticket 11's baseline record gains a revision: new identity beside the old, configure options, the reason, and the supersession statement; CTP jar and `init.sh` hashes join the identity list | met — [engine baseline §10](CBRD-26659-engine-baseline_f4299ac_claude.md#10-revision-2-2026-09-14-the-re-pinned-build-without-the-unit-test-seams), with a pointer at the head of §2 |
| Ticket 15's tooling verifies the new hashes; the old ones recognised only for replay | met (§3); `verify_install` refuses a new run and names the superseded build when it sees it, and `validate_records.py` resolves every manifest's engine through `recognised_build`, accepting the superseded build only as the identity of an already-recorded run |
| Tickets 13's and 14's cases re-run on the new build through ticket 15's wrappers; matrix rows gain the new attempts without erasing the old | met (§4): three invocations, all PASS, all proof `proven`, ten matrix rows with every recorded attempt intact |
| Instrumentation worktree rebuilt with the same options; ticket 16's ten sites re-verified through its own runner; patch-set build identity updated; a site that does not survive recorded as a Capability gap | met (§5): twelve scenarios re-run fault and control, ten acknowledge, the two known gaps still do not fire, no new gap |
| Each record citing the old build carries one line saying it is superseded for new runs, without editing the sealed evidence it points at | met: one `>` line in the headers of the ticket 13, 14, 15 and 16 records and at the head of the baseline record's §2; no record body, no JSON record and no bulky evidence was edited |
| Committed locally in the docs repository; nothing pushed | see the commit this record lands in |
