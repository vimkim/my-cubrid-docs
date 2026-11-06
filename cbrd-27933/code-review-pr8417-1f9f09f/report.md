# Review report: CUBRID PR #8417 (CBRD-27933)

Goal: confirm the fix that defers a failed vacuum OOS header lookup (-1393, interrupted block, 1 s re-run gate) is correct before marking the PR ready.

- Snapshot: base d52b1889e907abcf84190ec504dde3bc93de260d, head 1f9f09f362390e10ed06d80f9aae3ae2e361b2d2, patch sha256 97a6f25c590b352690852ec16af8a9fbcfed5513b26ad9902740fdf81ffa870a.
- Verdict: no-confirmed-findings. Follow-up review required: no (before merge). Optional evidence: SYS-1 load check.
- Coverage: complete for all assigned rows ([coverage.md](coverage.md)). Reviewers: Systems+Storage (opus), Concurrency (sonnet), Recovery (opus). HA n/a.

## Confirmed findings
None.

## Accepted design risk (not a defect of the stated intent)
- SYS-1 / R2 (P3, unproven): a lookup that keeps failing on one heap keeps blocks interrupted. Re-run work grows with the number of such blocks, and log archives and vacuum data grow. This is the open "fixed 1 s vs backoff" decision that the user settled as fixed 1 s. Cheapest check: debug FI 700000 run holding one heap header for 60 s while deleting across many blocks, counting "is interrupted" lines per second.

## Low-priority / informational
- N1 = INFO-2: shutdown ER_INTERRUPTED becomes -1393; bounded extra work, correctness holds.
- R3: a page whose only object was deferred keeps vacuum status ONCE; same as existing OOM interruption; space only.
- INFO-1: SA xvacuum stops at the first -1393 block; conservative.

## Disproven candidates
- R1 (Recovery): emptied OOS pages lost on the failing page. Disproven by coordinator: helper.oos_vfid is reset per page (vacuum.c:1721) and a later lookup happens only while it is NULL, so no earlier record on that page deleted OOS; the emptied list is empty. Systems reached the same conclusion independently.

## Pre-existing, not attributed to this PR
- C1: vacuum_forward_walk_reclaim_oos swallows a failed lookup (tracked as CBRD-27953).
- P1: release same-page retry loop on repeated non-OOM error.
- P2: release skip of vacuum_heap_record error (assert_release(false); continue).

## Checks run
- Systems compile probe: 14 compiles exit 0 (evidence/).
- Coordinator: debug ctest test_oos_real_vacuum_latch_timeout at 1f9f09f36, 6/6 passed (local log, not committed).
- CI: gha-ci run 42023440775 success (71 success, 1 skipped) at 80d6e721e; cppcheck success at 1f9f09f36.

## Budget
Best effort (no enforceable per-agent cap; user requested subagent review). 3 agents, no retries. Reported subagent tokens: concurrency 126,892; recovery 161,090; systems 154,550. Percentage compliance unverified.
