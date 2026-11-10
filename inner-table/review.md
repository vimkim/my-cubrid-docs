# Sidecar review and remaining proof

The review asks whether the proposed Sidecar contracts contradict the baseline
engine or admit a demonstrated protocol failure. The intended reader is the
designer approving the POC. Review date is 2026-11-04, Asia/Seoul. Source is
CUBRID/CUBRID at `e64a04a79a5842827a124b3f8313516d0da2594c`.

Independent `gpt-6-astra` and `gpt-6.1-terra` adversaries reported no verified
design defects. This is an approval-stage design review. No engine
implementation, real crash, native savepoint, HA, or performance run occurred.
The configured pool provides two OpenAI models rather than a cross-vendor
review. No stronger independence claim is made.

## Executed visibility and cancellation probe

The coordinator reran the Astra probe, retained as
[probes/visibility.py](probes/visibility.py), with this command:

```sh
python3 inner-table/probes/visibility.py --repo /home/vimkim/gh/cb/sidecar-codex
```

Run it from this documentation checkout. It requires Python 3 and `c++`, checks
the relevant baseline sources against the pinned revision, and writes its
generated code and binary to a temporary directory. A newer documentation or
skill-only commit does not invalidate the baseline source check.

It extracts the unchanged bodies of `logtb_is_current_mvccid`,
`mvcc_is_id_in_snapshot`, `mvcc_satisfies_snapshot`,
`mvcc_satisfies_vacuum`, and `repl_log_abort_after_lsa`. Transaction-table and
snapshot-container dependencies use explicit harness state.

Observed results were:

- All 256 four-operation sequences passed 11,520 visibility assertions for
  coordinated hot updates, replacement, inline replacement, and deletion.
- Old snapshots, own writes, active nested IDs, and post-commit visibility
  matched the coordinated model. Saved state restoration was a proxy for
  complete rollback, not execution of engine undo.
- Vacuum decisions retained the test row before its horizon and removed it
  afterward.
- Replication cancellation at LSAs 15, 25, and 35 left event masks 1, 3, and 7.
- Incorrect old deletion and child identity controls both failed as intended.
- Under the same snapshot, a chunk was visible before an own DELETE and
  invisible afterward.

The final observation sharpened the design. `VisibleRow` now has storage
operation lifetime. Its requested values materialize before reentrant user
callbacks or same-transaction mutations. It cannot promise deferred-read
stability merely by keeping a snapshot registered. No reachable stale-view
engine execution was established, so the reviewer dropped that candidate as
a confirmed defect. The source boundary observation remains useful evidence.

This probe tests baseline decision functions inside a coordinated bounded
mutation model. It does not prove actual nested-statement identity assignment,
physical rollback, allocation, durable WAL, or concurrent engine execution.

## Formal-check review

A fresh Astra reviewer read the project skill and every model/helper file,
then ran its self-test. It confirmed independent home and forward checks and
the safe-order control. [Verification](verification.md) records those results.
The no-comments review found no actionable comment or suppression issue.

Two implementation corrections were made and checked. The mock replay uses
static page objects to preserve their values across `longjmp`. Sync parsing
now occurs under error handling, and a missing sync record reports
`OUT OF SYNC` with exit 2. The sync revision comes from `SKILL.md` rather than a
second manually maintained constant.

A later maintenance pass replaced the self-test's hardcoded expectation of
the baseline forward finding. Its scenario table derives the input shape,
tests unsafe home and forward controls independently, and restores the
original input. This allows sensitivity checks after the forward release is
corrected. A fresh Terra reviewer checked this correction separately.

That review also identified missing model/replay consistency enforcement. The
coordinator injected a replay finding while the actual safe-order model
passed. Before the correction, the checker returned 0. After the correction,
it reports `MODEL/REPLAY DISAGREEMENT` and returns 2. Both normal release-order
control matrices still pass. This tests diagnostic error handling and is not
an observed disagreement between the real model and real extracted replay.

The reviewer found no open property defect within the stated model bounds.
It confirmed that the baseline counterexample occurs before the sysop end
append. Some later safe persistence outcomes are omitted conservatively. The
model is not an enumeration of every real WAL persistence outcome.

## Required POC evidence

The Terra review inspected compatibility, encryption, archive deletion, and
replica apply entry points. It ran configure/build preset discovery, which the
coordinator repeated. The `release` preset exists for both. Those checks are
orientation, not an engine validation result.

The remaining obligations are:

| Obligation | Required evidence before declaring the POC successful |
| --- | --- |
| Parent/chunk MVCC identity | Native savepoints, repeated overwrite, nested triggers, own writes, isolation levels, and standalone DML. |
| Undo destination protection | Forced allocation, competing commit, crash, and real restart. Protect slots, bytes, and page lifetime independently. |
| Complete history | Atomic fragment construction and publication, rollback-filtered operations, retained dependencies from first append, and every archive-deletion path. |
| Replica progress | Atomic local apply/progress or proven deduplication, with crashes on both sides of commit and source-unavailable replay. |
| Security and format | Explicit page-less WAL encryption, all hidden files and utilities, old server/log-reader refusal before mutation. |
| Public consumers | Full values through object fetch, loaders, unload, compact, indexes, schema lifecycle, and reentrant evaluation. |
| Measurement | Verified page attribution, equal results/plans, separate instrumentation and throughput builds, and negative controls for a real slowdown. |

These obligations appear in the [POC plan](poc-plan.md). They are unverified
assumptions and future checks, not claims that a missing POC implementation is
already a defect.

## Document checks

Markdown source checks pass for the design, plan, and formal result.
`docserve-check mermaid` could not validate diagrams because Python Playwright
is unavailable. It returned dependency error 2 before examining diagrams.
Diagram syntax and rendering remain unverified. No dependency setup was
performed.

The personal viewing URL could not be checked from this environment because
`dev2.baboon-rudd.ts.net` did not resolve. The files and relative links exist
locally. A generated personal viewing link is not a verified service-health
claim.

## Decision-trail audit

A fresh Terra reviewer checked the decision trail against this run's active
transcript. It confirmed that model and mocked replay claims remain separate
from engine results. The audit identified temporary draft/output pointers in
the early log. The later consolidation points to these retained reports and
reproduction scripts. Original candidate drafts and raw outputs may expire.
They are intentionally excluded from the documentation history.

The audit also found an early handback checkbox. The workflow now distinguishes
completed verification from delivery and pending user agreement. The source
skill's local commit has been checked. No engine changes, merge, push, or
deployment occurred.
