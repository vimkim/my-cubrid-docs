# Tickets 04–07: baseline lifecycle blocker

Date: 2026-09-08. Work item: 82. User authorized all remaining tickets, isolated tests/measurements, scoped repairs, final review, and a local feature commit; **no push**. The parent specification remains unchanged.

## Outcome

Implementation acceptance is blocked. A new SERVER_MODE regression demonstrates that a committed OOS value becomes unreadable after UPDATE → ROLLBACK → vacuum on **both the exact-original engine and the effective-key candidate**. Matching failures do not satisfy lifecycle correctness. This matches the existing CBRD-27237 analysis; repairing that reclamation mechanism is outside this routing design's approved scope.

No engine code was changed during this remaining-ticket work. One failing regression was added to the existing server vacuum test file. The isolated runner was extended to support allowlisted SERVER_MODE binaries and exact-original engine comparisons. No feature commit, push, benchmark, or final acceptance review has been performed; the stop condition was reached first.

## Evidence so far

| Check | Result | Scope |
|---|---|---|
| Existing publication checks | 11/11 pass | SERVER_MODE: reset, missing transaction, preparation/class/file lookup failures, partial publication, allocation failure, and successful publication controls |
| Existing real-vacuum tests | 10/10 pass | SERVER_MODE: actual daemon reclamation, old snapshots, committed updates, multiversion chains, chunk boundaries, and live-row controls |
| New rollback-survival regression, candidate | Fails | Original chain reads correctly after abort; read returns `-2` after observed vacuum progress |
| Same test binary, exact-original engine | Fails identically | Original engine has no source changes; dynamic library resolution checked before execution |
| Independently compiled/linked baseline test | Fails identically | Same test source, unchanged original engine; no candidate library dependency |

Raw evidence: [publication checks](ticket04-evidence/candidate-publication.json), [existing vacuum suite](ticket05-evidence/candidate-real-vacuum.json), [candidate failure](ticket05-evidence/candidate-rollback-vacuum.json), [baseline failure](ticket05-evidence/baseline-rollback-vacuum.json). Failed test processes stop with SIGTRAP because the existing Google Test main enables `break_on_failure`; the runner records child return code `-5` (shell status 251). This is a failed assertion, not a successful test.

## What the new test establishes

The test extends [the existing real-vacuum fixture](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/unit_tests/oos/test_oos_real_vacuum_server.cpp:831):

1. Insert and commit a heap row referencing a 4096-byte `a` payload in the heap's OOS file.
2. Insert and commit a separate `w` row used only as a vacuum-progress witness.
3. Insert a replacement `b` chain, update the original heap row through real MVCC heap DML, and abort the transaction.
4. Require the original OOS chain to read back as the original `a` payload immediately after rollback.
5. Delete/commit the witness, close the relevant log blocks using the existing filler helper, and wait until its OOS chain is actually unreadable.
6. Require the original chain still to be readable and unchanged. This assertion fails.

Both original and witness OOS chains are allocated before the aborted update. No subsequent OOS insertion can recycle the original OID into the witness. The heap is not dropped before the failing read. The original value was readable after abort, so this is not simply a mistaken expectation that the uncommitted replacement should survive rollback. A witness proves actual reclamation progress rather than merely assuming a daemon wakeup completed.

This is the existing low-level heap/OOS SERVER_MODE seam with a borrowed catalog class and actual attached heap/OOS file. It does **not** invoke attribute routing, claim SQL-level partition-movement coverage, or establish crash recovery. Its failure demonstrates a baseline lifecycle prerequisite that the routing optimization cannot fix. A passing witness would not by itself prove that every earlier parallel vacuum job had completed; the observed loss of the protected original chain is nevertheless a concrete failure.

## Attribution and source evidence

The candidate fails in both independent fixtures: [first run](ticket05-evidence/candidate-rollback-vacuum.json), [repeat](ticket05-evidence/candidate-rollback-vacuum-repeat.json). The exact-original engine also fails twice with the test-binary overlay: [first run](ticket05-evidence/baseline-rollback-vacuum.json), [repeat](ticket05-evidence/baseline-rollback-vacuum-repeat.json). This overlay's `ldd` output additionally shows both the candidate binary's CCI 11.2 dependency and the baseline engine's CCI 11.3 dependency. To eliminate this confound, the identical new test source was applied to the baseline worktree and compiled/linked there. That [fully baseline-linked test also fails](ticket05-evidence/baseline-native-rollback-vacuum.json), with only baseline libraries in its recorded resolution. The baseline engine library hash did not change. The baseline worktree differs only in this added test and a generated CCI Windows version header, not engine source. Total: candidate fails 2/2; baseline fails 3/3, including one native-baseline build.

The original engine is `b871ea386d2c5419b7abae07dda58b9b7f36377a`, built in the new detached worktree `/home/vimkim/gh/cb/pr7600-original-baseline`, with the normal `debug_gcc` configuration and pinned submodule. The candidate is that HEAD plus tickets 01–03's uncommitted routing changes. Both use the same newly compiled regression binary, and each runs with its own engine installation and fresh database. The baseline report records the separate test-only source overlay and verified `ldd` resolution; no candidate engine library is substituted into the baseline comparison.

SERVER_MODE engine library SHA-256:

- Original: `d1947e8c79c722d17ed408c75f13e4e665d29ea48bde9e57c9e41f94a8ad70a3`.
- Candidate: `7bb867020270821098234c2ffc6e6983333f7ec27089029976e1445e0f82b8d5`.

The unchanged [vacuum UPDATE branch](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/vacuum.c:3606) assumes the old OOS OIDs survive only in the undo image and reclaims them for `RVHF_UPDATE_NOTIFY_VACUUM`. That assumption does not hold after rollback restores the old row. [Forward-walk reclamation](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/vacuum_oos.cpp:275) extracts the OOS OIDs from the undo image and deletes them. Neither file differs between the candidate and original engine.

The local [CBRD-27237 analysis](/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27237-oos-forward-walk-rollback-delete_725a32c_claude.md) predicted this failure without a runtime reproduction. These paired runs now establish a matching lower-layer runtime failure at PR7600's pinned revision. No existing JIRA description or authoritative OOS context has been edited or published. The accepted future chain-reuse/commit-conditional notification design is not implemented by this task.

## Reproduce safely

Candidate:

```bash
python3 /home/vimkim/gh/my-cubrid-docs/cbrd-27089/design/ticket01-evidence/run-isolated.py NEW-CANDIDATE-LABEL \
  --server-test --binary test_oos_real_vacuum_server \
  --filter OosRealVacuum.RolledBackUpdateKeepsCommittedOosAfterVacuum \
  --output-dir /home/vimkim/gh/my-cubrid-docs/cbrd-27089/design/ticket05-evidence
```

For the independently built baseline test, add:

```bash
--source /home/vimkim/gh/cb/pr7600-original-baseline
```

Use a fresh label for every run. All databases/configurations/logs are under separately created `/tmp/pr7600-ticket01-*` fixtures and retained in the JSON provenance. No network server, shared `commondb`, or broad fixture cleanup was used. Build/install succeeded for the candidate test and the exact-original worktree. The bootstrap's shared-justfile path issue was worked around by stowing the standard files into the explicit new worktree, running preparation there, and rerunning the standard bootstrap; no shared tooling was patched.

## Ticket status and decision needed

Artifact storage note: these four failed assertions generated cores that filled the root filesystem. Only their four exact core files were moved, without deletion, to `/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/.artifacts/pr7600-ticket05-cores-C0BaEm/`. The original basenames retain the process IDs. The two repeat cores are partial because space ran out; they are not used as proof. The JSON assertion output and fixtures remain at their recorded paths. One subsequent baseline test compilation failed with `No space left on device`; the same build succeeded after moving the cores, without source changes. The final native-baseline check used shell `ulimit -c 0` to avoid another core, not to suppress assertions. No preexisting artifact was removed. Root filesystem headroom recovered to about 2.4 GiB; it remains low.

- **04: incomplete.** Existing publication assertions pass; broader routing/preparation failures, durable rollback/owner observations, LOB failure/retry accounting, and final heap/index failure coverage remain.
- **05: blocked, not resolved.** Baseline rollback/vacuum safety fails. Partitioned concurrent readers, movement/rollback, and crash recovery remain unverified.
- **06: not started.** No allocation/copying or performance benefit is claimed.
- **07: blocked.** Full integrated suite, requirement matrix, final two-axis review, and acceptance commit remain pending. The failing regression remains uncommitted and intentionally red; it must not be silently disabled to claim acceptance.

Recommendation: retain CBRD-27237 as a separate prerequisite and keep this design's final acceptance blocked. Do not expand the routing patch into a vacuum/notification redesign. The user must decide whether to continue independent cleanup/measurement work with that explicit dependency, or pause routing work until the prerequisite is resolved. Neither choice waives the lifecycle gate.

Parent spec SHA-256: `dfa82a53337a2cf85c9d18bfe3707d99670a6e7070320a97fc3183b50c01f31f`.
