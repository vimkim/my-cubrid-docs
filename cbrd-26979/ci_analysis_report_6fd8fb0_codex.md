# CI Failure Analysis: PR #7611 at `6fd8fb0`

## Executive Summary

CircleCI `test_sql` job [146981](https://circleci.com/gh/CUBRID/cubrid/146981) ran the corrected PR head
`6fd8fb0e52966e14c3e92d94d6f34f5e479f7844`. It executed 17,449 tests: 17,430 succeeded and 19 failed;
there were no errors, skipped tests, or unknown results.

The review-item-2 regression is fixed. The exact
`_15_class_attribute/cases/constraints.sql` testcase is `[OK]` in the current job. Its testcase revision is
unchanged from the preceding `ea2439d` run, and its answer requires `Error:-710` for the CLASS ATTRIBUTE
`AUTO_INCREMENT` statement. The preceding broad `parser_attr_type` fix had produced `Error:-493` and made this
the twentieth failure.

All 19 residual failed-test names and normalized failure messages are byte-for-byte identical to the other 19
failures at `ea2439d`. Therefore they are unrelated to corrective commit `6fd8fb0e5` with high confidence. This
comparison alone does not prove whether they originate in the current `feat/oos` base, another merged develop
change, or stale testcase expectations. Do not change answer files without an exact-base comparison.

## CI Snapshot

| Suite | State | CircleCI job | Tests | Failures | Errors | Unknown | Warning |
|---|---|---:|---:|---:|---:|---:|---|
| `test_sql` | failed | [146981](https://circleci.com/gh/CUBRID/cubrid/146981) | 17,449 | 19 | 0 | 0 | Residual failures unchanged from `ea2439d` |
| `test_medium` | passed | [146980](https://circleci.com/gh/CUBRID/cubrid/146980) | — | — | — | — | Snapshot context only; artifacts were not collected |
| `test_shell` | missing | — | — | — | — | — | `/run all` was posted; a missing status can mean shell is still queued |

## Evidence Scope

- PR: https://github.com/CUBRID/cubrid/pull/7611
- Exact source commit: `6fd8fb0e52966e14c3e92d94d6f34f5e479f7844`
- Testcase revision: `274a17d2114e383827765322d836fe221bfa84c8`
- Collector: `cubrid-ci 0.1.0 (3e9502f72350, release)`
- Current evidence: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26979/6fd8fb0/test_sql`
- Comparison evidence: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26979/ea2439d/test_sql`
- Collection mode: bounded text artifacts and referenced testcase sources

The two jobs use the same testcase revision. After excluding the former `constraints.sql` failure, canonical JSON
containing each failed test's name and complete upstream message has the same SHA-256 on both runs:
`053af565f1fa02f3100f5577160f7089f483a89491325740975272113ba580de`.

## Review Item 2 Verification

The exact testcase contains:

```sql
ALTER TABLE c1 CHANGE CLASS ATTRIBUTE c_i c_i INTEGER AUTO_INCREMENT;
```

The exact answer contains:

```text
Error:-710
```

Current CircleCI execution log:

```text
[22:03:45] Testing .../_15_class_attribute/cases/constraints.sql (1741/2538 68.60%) [OK]
```

Observed comparison:

| Head | Result |
|---|---|
| `ea2439d` with broad pre-`attr_def_one` `parser_attr_type` setting | testcase failed; expected `-710`, actual `-493` |
| `6fd8fb0` with post-parse STORAGE-only check | testcase `[OK]`; actual output matched expected `-710` |

This proves the minimal fix preserves the pre-existing schema constraint error while still selecting message 339
for an explicit STORAGE clause on a CLASS/SHARED attribute.

## Failure Inventory

Every row below is observed in the exact `6fd8fb0` bundle. “Unchanged” means the complete test name and failure
message match the `ea2439d` bundle, not merely that the symptoms look similar.

| Test | Observed signature | Category | Relation to `6fd8fb0e5` |
|---|---|---|---|
| `inst_num.sql` | derived column `a_?` became `col_a` | Query/plan text drift | Unchanged; unlikely |
| `cbrd_24258.sql` | derived columns `a_?` became source names | Query/plan text drift | Unchanged; unlikely |
| `bug_bts_4563_3.sql` | `idx-join` became `nl-join` | Query/plan text drift | Unchanged; unlikely |
| `cbrd_25098.sql` | derived-query and scan-plan output changed | Query/plan text drift | Unchanged; unlikely |
| `cbrd_25801.sql` | derived aliases and plan output changed | Query/plan text drift | Unchanged; unlikely |
| `bug_bts_5861_2.sql` | plan node/order output changed | Query/plan text drift | Unchanged; unlikely |
| `bug_bts_10516.sql` | expected success became `Error:-1380` | FBO behavior | Unchanged; unlikely |
| `bug_bts_13199.sql` | plan order label `id` became `course_id` | Query/plan text drift | Unchanged; unlikely |
| `bug_bts_14002.sql` | optimizer class/index order changed | Query/plan text drift | Unchanged; unlikely |
| `cbrd_21452.sql` | derived column `a_?` became `a` | Query/plan text drift | Unchanged; unlikely |
| `cbrd_24013.sql` | derived aliases and scan plan changed | Query/plan text drift | Unchanged; unlikely |
| `cbrd_26419.sql` | optimizer class ordering changed | Query/plan text drift | Unchanged; unlikely |
| `cbrd_25214.sql` | covered-index key reference changed | Query/plan text drift | Unchanged; unlikely |
| `19_user_cursor_system_view.sql` | INFORMATION_SCHEMA count `299` became `288` | Catalog/view drift | Unchanged; unlikely |
| `cbrd_26959_bind_peek.sql` | expected table-scan/rewritten-query output absent | Bind/plan output | Unchanged; unlikely |
| `cbrd_26599.sql` | optimizer term ordering changed | Query/plan text drift | Unchanged; unlikely |
| `cbrd_26959_enum_histogram.sql` | `UPDATE STATISTICS` returned `Error:-493`; plans changed | Statistics behavior | Unchanged; unlikely |
| `fbo_ddl02.sql` | expected success became `Error:-1380` | FBO behavior | Unchanged; unlikely |
| `json_table_group_concat.sql` | derived alias output changed | Query/plan text drift | Unchanged; unlikely |

## Root-Cause Analysis

### Corrective parser change (one failure removed)

**Observed:** `constraints.sql` was the only testcase present in the `ea2439d` failure list and absent from the
`6fd8fb0` list. The current run marks it `[OK]`, and the testcase revision is identical.

**Inferred:** Moving the CLASS/SHARED STORAGE error selection after `attr_def_one` removed the unintended parser
context change while retaining the intended message-339 behavior. Confidence is high because the changed
testcase directly exercises that control flow and the local regression test asserts internal error `-710`.

### Residual failures (19 unchanged tests)

The residual set consists of 14 query/plan-text differences, two FBO failures, one INFORMATION_SCHEMA count
difference, one bind/plan-output difference, and one statistics failure. Their complete failure messages are
identical across the two PR heads.

**Observed:** corrective commit `6fd8fb0e5` changes only the ALTER CLASS ATTRIBUTE STORAGE parsing seam and adds
one regression test. None of the 19 tests exercise that syntax, and none changed signature after the correction.

**Inferred:** the residual failures are unrelated to the corrective parser commit. Confidence is high for that
narrow attribution.

**Unknown:** this evidence does not distinguish an intentional engine change from a defect or stale expected
output in the current testcase baseline. An exact `test_sql` run on base commit
`e1e651debf6cc100172bde96603b17424f9c135a` is the falsifying comparison needed before changing code or answers.

## Recommended Actions

1. Accept review item 2 as verified: `constraints.sql` again matches `Error:-710` on exact-head CircleCI.
2. Do not change any of the 19 residual answer files as part of CBRD-26979.
3. If the red `test_sql` status must be cleared, run or locate an exact-base `test_sql` result at `e1e651de...` and
   compare the same 19 complete messages. Fix only failures newly introduced by the PR relative to that base.
4. Preserve the current `/run all` shell queue; do not post a second trigger merely because shell status is absent.

## Evidence and Limitations

- Inspected the exact manifest, SQL summary, complete failure inventory, all normalized upstream failure messages,
  current execution log, and the same-revision `constraints.sql` case/answer.
- Counts reconcile: 17,430 successes + 19 failures = 17,449 total; errors and unknown results are zero.
- The SQL suite is red even though the targeted regression is fixed.
- `test_medium` passed according to the exact commit manifest but was outside the explicitly analyzed subset.
- `test_shell` had no status when the snapshot was collected; this is not evidence of pass, failure, or a lost
  trigger.
