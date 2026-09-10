# PR #7600 — execution and worktree review

Date: 2026-09-09. Engine head: `988a4d2fa258222aef792a2a6afde9641b8c5228`. PR base and merge-base: `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`. Review command: `git diff f4299ac0cd777a2a964c1f197ae5ebf9841a4936...HEAD`; uncommitted changes inspected separately. The committed diff spans nine files. Commits: `d9f59cb3a`, `b871ea386`, `213ce80f5`, and merge `988a4d2fa`.

## Fresh verification

| Check | Result | Evidence |
|---|---|---|
| Debug GCC compile and install | Passed | [Build log](evidence/build.log) |
| Existing SQL routing/ownership/cleanup suite | 32/32 passed; process exit 0 | [Run record](evidence/review-988a4d2-sql.json), [GTest XML](evidence/sql-gtest.xml) |
| Uncommitted rollback/vacuum regression | Failed at test line 864; process terminated by SIGTRAP | [Run record](evidence/review-988a4d2-vacuum.json), [test patch](evidence/vacuum-regression.patch) |
| Committed diff and uncommitted source whitespace checks | Passed | `git diff <base>...HEAD --check`; `git diff --check` |

Tests used separate private configuration and database directories with the freshly installed engine. The retained runner records binary/library hashes, CMake-cache hash, source status, command, output and exit code. Its generated placeholder build-log path was corrected to the actual saved build log and a SHA-256 added. No existing database was deleted to run these tests. Private fixtures remain available at the paths in the run records. The complete configured CTest suite, CTP suites, crash recovery, Windows/CCI runtime, and paired performance matrix were not rerun.

The standalone SQL suite covers range/list/hash, NULL/boundary/expression routing, explicit-partition rejection, legal key defaults and codecs, generated/default keys, CHAR/collation behavior, unchanged/changed UPDATE keys, old representations, dedicated increments, duplicate probes, LOB lifecycle, failure cleanup, and physical owner statistics. These 32 tests do not establish SERVER_MODE old-reader or vacuum safety.

## Vacuum decision

`OosRealVacuum.RolledBackUpdateKeepsCommittedOosAfterVacuum` creates a committed original OOS value and a separate witness, replaces the original through MVCC update, then aborts. Reading the original succeeds before vacuum. Deleting the witness and waiting for its OOS chain to become unreadable establishes vacuum progress. The subsequent original-value read fails:

```text
test_oos_real_vacuum_server.cpp:864: Failure
test_oos_utils::oos_read_with_alloc (thread_p, original_oid, after_vacuum)
  Which is: -2
NO_ERROR: 0
rolled-back UPDATE must not make the committed OOS value reclaimable
```

The test then terminates with signal 5; the runner records subprocess return `-5` (shell status 251). No completed GTest XML was produced for this failed run. The reported failure is the readback assertion, not merely a timeout or teardown failure.

**Decision: leave the test uncommitted and skip adding it to this PR, following the user's instruction.** Preserve the patch and red evidence for the lifecycle repair. Skipping the test does not make lifecycle acceptance pass.

The observed failure matches the previously recorded baseline/candidate CBRD-27237 rollback-vacuum regression. `src/query/vacuum_oos.cpp` is byte-identical between this PR base and HEAD (SHA-256 `ca43e5bf85b90ae495df3053b35069b3322e005986fd61336cb4f35beb78e560`). Its [undo-image chain extraction and deletion](https://github.com/CUBRID/cubrid/blob/988a4d2fa258222aef792a2a6afde9641b8c5228/src/query/vacuum_oos.cpp#L337) remains present. This attribution combines current failure, unchanged source and historical baseline evidence; the base was not rebuilt/rerun during this review. The test is a useful lower-layer regression, but successful execution would still not establish partition-specific lifecycle coverage.

## Worktree inventory

- **Vacuum test:** reviewed and executed as above; unchanged, unstaged and uncommitted.
- **CCI dependency mismatch:** the PR pins `bd86063a5bd481f0e22bf07c8a76bf736f86443a`; the local checkout is `2fb8d6d02c41386be0d56c3cfc6a14ad7e17ac15`, five commits behind. Fetching the pinned object confirmed this is a dependency rollback, including reverting CCI's OpenSSL build configuration from 3.5.7 to 1.1.1f and BUILD_NUMBER from 11.3.0 to 11.2.0. Do not sweep this unrelated gitlink into a PR7600 commit. Local build evidence includes this mismatch and cannot certify the exact pinned CCI dependency. No CCI runtime regression is asserted from the OOS tests. The generated Windows version-header delta reflects the local 11.2 checkout. [Exact comparison](evidence/cci-state.json).
- **`repro-cbrd-27089.sh`:** inspected as a historical manual reproducer, not executed. It changes shared configuration, deletes an existing fixed-name `cbrd27089` database, and intentionally tolerates backup failure. Its evidence cannot establish successful backup/restart; use isolated fixtures for review verification.
- **`prompt.md`, `prompt-no-git-add.md`:** historical investigation instructions, not product code or current review requirements. They were not followed as new commands.
- **`.artifacts/`:** existing generated logs/fixtures were inventoried as historical evidence, not new product changes or fresh acceptance results. No bulk staging or deletion was performed.

Source status is preserved in [source-status.txt](evidence/source-status.txt). Neither engine source nor tests were edited by this review.

Artifact checks: JSON parses, the SQL XML records 32 tests with zero failures/errors, local report links resolve, and the archived vacuum patch equals the untouched source diff. The patch retains a single-space blank context line required by unified-diff syntax; `git diff --check` flags that raw evidence line when adding the patch file. Authored Markdown passes whitespace checks.
