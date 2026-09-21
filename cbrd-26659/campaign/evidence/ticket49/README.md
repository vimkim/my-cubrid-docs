# Evidence for CBRD-26659 campaign ticket 49 — closing the independent review of ticket 17

Record: revision 2 (§15) of [`../../CBRD-26659-representative-timings-tier-placement_f4299ac_claude.md`](../../CBRD-26659-representative-timings-tier-placement_f4299ac_claude.md);
review closed: [`../../CBRD-26659-ticket17-independent-review_f4299ac_claude.md`](../../CBRD-26659-ticket17-independent-review_f4299ac_claude.md).
Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`, re-pinned by ticket 41 (`release_gcc_nounit`);
private testcase worktree at `66b66f1` (the barrier case is byte-identical at `c4fe45173`, the commit ticket 17 recorded).
Bulky artifacts stay under `~/.cub/campaign/cbrd-26659/ticket49/` (1.2 MiB) and are listed with sha256 in
[`SHA256SUMS-bulky.txt`](SHA256SUMS-bulky.txt).

| Path | What it holds |
|---|---|
| `att-T49-000{1,2}.json`, `bundle-att-T49-000{1,2}.json` | The two attempts of the private suite's multi-session barrier scenario `bug_bts_22449` at the shell seam (review F1), written by the wrappers through the corrected post-processor. Kind `coexistence` — an executed attempt that adds no coverage, ticket 14's precedent — so no manifest and no matrix row; outcome FAIL because the case time (131 s) exceeds the fast tier's 120 s per-case cap: the schedule halts at its fourth participant and is killed by the isolation tool's own timeout, in both runs. Retention class `failure`, held through triage, as the rule writes for any non-PASS. |
| `inv-T49-000{1,2}/` | Per run: `identity.txt` (engine, testcase, CTP and context identities), `summary.txt` (counts, drift lines, elapsed), `test-shell.xml` (CTP's per-case time), `bug_bts_22449.result`, `case-list.txt`, the isolation tool's `run.log`, `runone.log` (the schedule's own elapsed milliseconds), `timeout.log`, the formatted controller transcript `22449.ctl-transcript-formatted.log` (the raw one is overwritten by the tool's own `write_nok`), the `ctldb` server error log copied out of the install's log directory, and `resource-sample-summary.json` from `tools/resource_sampler.py`. |
| `ctltool-listing.{before,after}` | sha256 listing of `/home/vimkim/CTP/isolation/ctltool/` before the first run and after `make clean` following the second: identical (19 files); the case compiles `qactl` and `qacsql` in place and ticket 49 removed the build products. |
| `validate-before.txt`, `validate-after.txt` | `tools/validate_records.py evidence --quiet` with the new finished-bundle cross-check, before the record corrections (32 failing: ticket 17's eight `inv-T17-0002` attempt records and indexes, and ticket 47's eight of `inv-T47-0001`; 12 notes on protected-prefix bundles of the older conventions) and after (307 records, 0 failing, the same 12 notes). |
| `apply-record-corrections.txt` | `evidence/ticket17/apply_ticket49_record_corrections.py` on `evidence/ticket17` and `evidence/ticket47`: dry run, apply, and a second apply that changes nothing. |
| `planted-defects.txt` | Review F3 and F4 re-planted on scratch copies: `selftest_tier_placement.py` against `tier_placement.py` with `per_case = per_seed` (check 9b fails, nothing else), and `config_domain.py check` against the twelve real cells with defects A and B planted (3 problems, named; the unplanted cells 0). |
| `checks/` | The captured outputs of every check §15 of the record cites. |

The private and public testcase worktrees are unchanged (`git status` clean, both); the runs read a
byte-identical copy of the case directory under the ticket 49 storage because the case writes its
isolation-tool outputs into its own directory (8 drift lines on the copy, 0 on the install's conf and
databases and on the user's `.CUBRID_SHELL_FM`). Both runs used the one port block the wrappers know
(26659, 33120–33122), alone; ticket 50 applies the private lane.
