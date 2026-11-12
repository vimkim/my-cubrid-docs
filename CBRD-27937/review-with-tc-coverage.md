# Coverage: PR #8454 / TC PR #4803

| Path or invariant | Owner | Evidence | Result | Remaining |
|---|---|---|---|---|
| `src/storage/tde.h`: six added indexes reach an encryption decision | engine-opus (primary), latch-perf-sonnet (Q1) | Level 3 source trace for each writer. Level 5 from the TC (pre-fix NOK, post-fix OK) | Closed for all six | none |
| `log_manager.c` `log_append_undo_crumbs`: new `pgptr == NULL` branch, its callers and vfid validity | engine-opus | Level 3. Level 5 from TC scenario 4 | Only `btree_load.c:4792`/`4882` reach it. The vfid is flagged | none |
| New branch: latch context, deadlock, failure mode, error state | latch-perf-sonnet | Level 3 | No deadlock. Fail-open and stale-error risk recorded as R3 | optional hardening |
| New branch: per-record cost | latch-perf-sonnet | Model only | R5 | optional benchmark |
| `RVPGBUF_NEW_PAGE`: page flag set before logging | latch-perf-sonnet, engine-opus | Level 3. Level 5 from TC scenario 5 | OK | none |
| Recovery: redo and undo of the newly encrypted records, key load order | engine-opus, coordinator P1 | Level 5 (kill -9, revive, recovery, checkdb) | OK | release build not run |
| Vacuum, CDC and archive readers decrypt | engine-opus | Level 3 | OK | none |
| HA producer and consumer | engine-opus | Level 2–3 | No new requirement. Replica copies are plaintext by design | runtime HA not run |
| Shared Q1: remaining plaintext paths | engine-opus (opus) and latch-perf-sonnet (sonnet), independent | Level 3, plus coordinator level-5 probes | Both agree. Residuals R1, R2 and R4 predate the PR | new issues |
| TC (1): fails pre-fix, passes post-fix | coordinator | Level 5 (contained testkit runs) | Confirmed | none |
| TC (2): detection reliability | tc-sonnet, coordinator | Level 3, plus run traces (no archive created) | Sound now. Suggestions T1–T3 | none |
| TC (3): cleanup, environment, runtime | tc-sonnet, coordinator | Level 5 for cleanup and runtime, level 3 for the rest | Sound. Needs CTP with `wait_until` | none |

Domains not applicable: none fully. The HA role was combined into engine-opus. The changes touch log production that HA consumes.

Dropped candidates by reviewer:
- **engine-opus.** C5 (HA plaintext copies) and C6 (statement text) were kept as informational and out of scope. C4 (dropped record on an encrypt-mark failure) was rejected as unreachable at level 2–3.
- **latch-perf-sonnet.** None dropped. C-1 merged into R3, P-1 became R5, and its R-1, R-2 and R-3 merged into R2, R3 and R1.
- **tc-sonnet.** No defects. Its suggestions became T1 to T4.
