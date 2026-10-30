## Why

CTP must include all completed testcases so engine authors and QA can trust CI reports. A category with its own cases currently stops summary traversal, which omits nested cases from aggregate counts and JUnit while their verdict rows remain in physical reports. This caused a 3,533 versus 3,531 discrepancy in [PR 8347's CI](https://github.com/CUBRID/cubrid/actions/runs/41048233875).

## What changed

- Recompute summary counts and links from direct cases and every child category. Keep directory-owned case lists separate from group aggregates.
- Emit direct JUnit cases and traverse children independently.
- Normalize category separators and preserve serialized SQL/medium hierarchy, root run counts, and directly owned result paths.

## Scope

This covers CTP summary and JUnit generation with an offline producer regression. Runtime publication and fresh company CI remain separate steps.

## Blast Radius

SQL and medium reports share this producer. Regression checks cover physical row ownership, serialized hierarchy and metadata, mixed verdicts, repeated generation, and result-mode paths.

## Verification

- `./tests/sql-summary/run.sh` reproduces omission before the fix and passes afterward, including the reporting compatibility assertions.
- Full Ant compilation and the same regression against a newly built temporary SQL runtime JAR pass.
- Replaying the recorded 3,533 passing case paths and durations yields 3,533 unique JUnit cases and verdict rows. This simulates report generation without rerunning SQL. Existing CI artifacts remain inconsistent.
