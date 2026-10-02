# Implementation continuation

Work-tracker item: 261. Handoff contract: `/tmp/handoff-cbrd-27443-orchestrated-Sb9MbYnm.md`. Read the whole parent spec and all tickets from this worktree's `.scratch/cbrd-27443/` when resuming. Parent spec is unchanged.

## Ownership and bases

- Engine: `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`.
- User-confirmed implementation base: `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`. User confirmed this new base and exclusive worktree availability after an external fast-forward. Never include the earlier upstream advance as our implementation diff.
- Shell tests: `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, original base `dfb7da195`.
- Documentation: `/home/vimkim/gh/my-cubrid-docs-cbrd-27443-implementation`, branch `docs/cbrd-27443-implementation`, original base `ece982c`.
- Main alone edits ticket status, map and docs. One fresh implementation worker per ticket, numeric order, no nested workers. Tickets01–02 accepted. Latest engine `11ad631c56b35675a96c7c9c15fc66025fb0aab0`, shell `7df0ede4bb5e76f59f644a1d6c7df03cfcd2e93c`. See per-ticket report/review files. Next dispatch: ticket03.

## Preparation evidence

`baseline-15e7dc8b5/` contains exact-base reproduction, binary hashes and native preflight. Full debug_gcc build/install passed. Source/install commit match and native containment passed. Earlier `baseline/` retains the c63a3b9 reproduction and transient shared-tooling preparation failure.

Runtime initialized using supported `cub-workenv init --no-db`. Shared personal tooling changed during preparation; inspect live recipes. `CUBRID_TESTCASES_PRIVATE_EX_DIR` was not exported; use the assigned exact shell root above when invoking test tools. CTP assets resolve to `/home/vimkim/gh/ctp/run-sql/CTP`. Native runner is installed; do not install/update it. Preserve containment and PID-1 reaping.

## Ticket 01 design checkpoint

Main accepted the worker's proposed explicit background spawn plus separately executed console relay. It separates startup diagnostics by attempt using anonymous spools, preserves original streams, appends continued output, and drops launcher-facing resources after a finite drain barrier. Subsequent log rotation belongs to ticket 04. This is a design checkpoint, not an implementation or acceptance claim.

Review constraints: no unbounded drain under continuous writers; preserve existing registration timing and SIGCHLD/termination semantics; helper exec/log-open failures must reach launcher; relay keeps no caller stdio/lock; parent loss closes attempt spool/control descriptors; safely encode DB log names; document relay lifecycle and prepare for coordinated rotation among multiple relays sharing a log.

## Completion workflow

For each ticket, capture immutable dispatch base, require narrowly committed source/tests and native verdict-bearing evidence, review actual diff against both Standards and Spec, and resolve checkboxes only when evidence supports them. Return corrections to the same worker. Main performs the two review axes itself in place of stock code-review's extra reviewer agents.

Current reports should be returned under `/home/vimkim/.cache/cbrd27443-ticketNN-report.md`; main copies meaningful results into this documentation worktree. No develop merge, push, PR, external CI or JIRA mutation is authorized. At completion, request one concrete local rebase/fast-forward approval covering relevant repositories, then clean only merged task worktrees/branches.

## Formatting decision

The user explicitly approved following the enforced repository formatter on 2026-10-02. The supplied AGENTS.md line133 says no tabs, but codestyle.sh line28 uses AStyle `-xT8`, which forces mixed tab/space indentation. Use the live formatter and normal commit hooks; no hook changes or bypass are authorized. This task-specific user decision resolves the conflict for subsequent workers.

## Ticket 02 checkpoint

Service and direct daemon master use the explicit background helper. Preserve the existing PID1/NO_DAEMON foreground exceptions. Linux re-exec uses `/proc/self/exe` and carries actual PR_GET_NAME through a private last argument; original argv interpretation is preserved. The relay is included in Application installs. Final native `ticket02-final-11ad631c5.8gBHRC` passed 1 case, 216 master checks and 121 original checks. Earlier d031 native failure exposed comm restoration and a strict post-stop observation race; both were corrected and prior evidence retained. Source/test worktrees are clean and released. Ticket03 owns server/PL restart and internal FD cleanup; the basic present probe still visibly shows PL inheriting parent error-log/volume targets before that work.
