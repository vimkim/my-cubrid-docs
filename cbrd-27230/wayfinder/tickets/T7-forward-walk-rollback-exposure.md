# T7 — Report the forward-walk rollback exposure as CBRD-27237

- label: `wayfinder:task`
- status: closed
- assignee: dhkim (claimed 2026-08-13)
- blocked-by: (none)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

T3's analysis ([findings §7](../findings/T3-cleanup-paths-under-chain-reuse.md)) found the **current** `feat/oos` forward-walk exposed to **rolled-back UPDATEs**, independent of dedup: `vacuum_process_log_record` has no commit/abort filter, rollback never unlinks the UPDATE record from the MVCC-op chain, and after the aborted MVCCID retires the forward-walk deletes the pre-image's chains — which the rollback-restored live record still references. Silent data loss, same symptom class as CBRD-26950.

Per the dev's decision (2026-08-13): **no runtime verification** — write it up as an analysis-based issue report and publish it to the existing JIRA sub-task **[CBRD-27237 "vacuum delete old chains for rolled back update"](http://jira.cubrid.org/browse/CBRD-27237)** (currently empty description, under the M2 epic CBRD-26583), via `cubrid-jira-issue-write`. The report must state plainly that it is 분석 기반 (no reproduction run) and cite the code evidence chain. Note the tie-in: option 2's commit-conditional notify emission fixes this too (input to the T4 decision and the T6 spec's 이유 section).

## Resolution

(2026-08-13) Report written, grill-reviewed (3 rounds, all citations source-verified at `725a32c6e`, verdict APPROVED), committed and pushed (`my-cubrid-jira` commit `42b8887`, `issues/CBRD-27237-oos-forward-walk-rollback-delete_725a32c_claude.md`), and **uploaded to [CBRD-27237](http://jira.cubrid.org/browse/CBRD-27237)** with read-back verification. Framed honestly as analysis-only (재현 미실시). 방안 offers two ranked candidates — CBRD-27230's notify-log architecture (removes the forward-walk, defect path disappears) vs. a short-term commit-check gate — with the choice marked TBD pending T4. Input to T4: if option 2 is adopted with commit-conditional emission, this bug is fixed for free, a genuine tiebreaker for the architecture decision.
