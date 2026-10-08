# CBRD-26659: approved implementation tickets

Date: 2026-10-08 (Asia/Seoul). Status: approved by the user. The 14definitions are published as separate local Markdown issues; no implementation has started.

The user agreed local optdebug validation, separate informal SQL/shell timing, passing delivered cases with explicit gaps, and ordinary HA as a follow-up gap. The configured tracker is local Markdown. One issue per ticket is published locally using the configured ready-for-agent state, with approved definitions retained durably. No remote issue or parent JIRA description is changed.

## Breakdown

1. **[Prove one SQL value-copy case end to end](tickets/01-sql-value-copy.md)** — **Blocked by:** None. **Delivers:** A compact public INSERT SELECT regression preserves independently modeled source and copied values through the real SQL runner, with complete discovery, answer, cleanup and timing evidence.

2. **[Prove one shell OOS owner-file lifecycle case end to end](tickets/02-shell-owner-drop.md)** — **Blocked by:** None. **Delivers:** A compact private shell regression positively identifies an owned OOS file before DROP, checks its removal and an independent survivor, and proves the native verdict and cleanup path.

3. **[Validate representation and discriminating chunk boundaries](tickets/03-representation-chunks.md)** — **Blocked by:** 01, 02. **Delivers:** Public logical checks and narrow delivered shell observers establish profitable-value, largest-first and chunk behavior with distinct bytes and independent physical expectations.

4. **[Validate UPDATE and DELETE state transitions](tickets/04-dml-transitions.md)** — **Blocked by:** 01, 02. **Delivers:** Compact public DML regressions preserve exact values and survivors across inline/OOS, size and NULL transitions, with paired shell evidence for any claimed physical transition.

5. **[Validate transaction and rejected-DML atomicity](tickets/05-transactions-errors.md)** — **Blocked by:** 01. **Delivers:** Public cases prove that commit, rollback, savepoints and rejected writes preserve the independently intended rows and schema, including legal and illegal OOS/bigone neighbors.

6. **[Validate trigger outcomes with explicit OOS path limits](tickets/06-triggers.md)** — **Blocked by:** 01, 02. **Delivers:** Public trigger cases prove intended log/mirror, rejection and row outcomes while distinguishing an OOS-positive pre-trigger fixture from client-template writes that bypass OOS.

7. **[Validate supported relational and raw read paths](tickets/07-read-paths.md)** — **Blocked by:** 01, 02. **Delivers:** Public query regressions return identical independently modeled complete values through the intended heap/index and relational paths, with explicit plan/path and paired-fixture evidence.

8. **[Validate schema and storage-policy rewrites](tickets/08-schema-storage.md)** — **Blocked by:** 01, 02. **Delivers:** Public DDL checks and discriminating shell placement/owner phases preserve intended data and metadata across schema and storage-policy changes, with partition defects visibly dispositioned.

9. **[Validate external LOB locator and copy independence](tickets/09-lob-locators.md)** — **Blocked by:** 01, 02. **Delivers:** Public LOB cases and private file-lifecycle phases preserve independently known external contents and prove legal locator demotion/copy behavior without confusing adjacent large VARBIT with locator coverage.

10. **[Validate committed crash durability and uncommitted undo](tickets/10-crash-recovery.md)** — **Blocked by:** 02. **Delivers:** Private shell cases journal acknowledged transaction outcomes, crash a contained owned server and verify exact recovered committed contents and undone uncommitted changes through separately asserted scenarios.

11. **[Validate real snapshot visibility and observable safe reclaim](tickets/11-snapshots-reclaim.md)** — **Blocked by:** 02. **Delivers:** Private shell coordinates acknowledged live sessions to prove old/new value visibility and survivor safety, then checks only reclaim progress that product observations can actually establish.

12. **[Validate utility and backup round trips](tickets/12-utility-roundtrips.md)** — **Blocked by:** 02. **Delivers:** Compact private shell fixtures retain independently modeled values and schema through supported unload/load/compact and backup/restore/check operations, with route-specific OOS evidence.

13. **[Validate OOS TDE attribution and WAL behavior](tickets/13-tde-wal.md)** — **Blocked by:** 02. **Delivers:** A compact private shell TDE fixture identifies the owned OOS file and intended encryption policy, checks relevant WAL classifications and exact values through lifecycle operations, and reports any remaining ciphertext gap.

14. **[Validate the complete delivered SQL and shell sets locally](tickets/14-complete-local-validation.md)** — **Blocked by:** 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13. **Delivers:** A final reproducible local receipt reconciles every delivered case with coverage, proves the complete SQL set and shell set pass with correct expectations, and reports separate whole-suite timing and remaining gaps.

## Approval and execution boundary

The user approved the granularity and blocking edges on 2026-10-08. This finishes local specification/ticket planning; it does not authorize testcase implementation, pushes or GHA.

Tickets 01/02 can start independently once implementation is authorized. The transaction/error SQL group depends on 01; companion/physical groups, including the positive pre-trigger witness, additionally need 02's observer and shell workflow. Shell groups depend on 02. Final validation depends on 03–13, which transitively include 01/02. No new setup-only or historical campaign framework ticket is inserted.

A group can deliver its useful passing subset with explicit accepted defects/gaps, but cannot report missing behavior verified. If no useful repository-conforming case can pass, it remains unresolved and requires an explicit scope disposition rather than an empty completion. Actual file counts are settled by the first tracers and implementation, not promised here.

Dependency clarification: ticket 06 also depends on 02, because its positive pre-trigger witness requires the shell observer. No behavior scope or ticket count changed.
