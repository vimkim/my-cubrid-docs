# CBRD-26399 slotted page alignment accounting

[CBRD-26399](http://jira.cubrid.org/browse/CBRD-26399) claimed that `spage_initialize()` and `spage_max_record_size()` over-report usable slotted-page space because they ignore alignment. The 2026-11-05 re-verification at CUBRID develop `e64a04a79a5842827a124b3f8313516d0da2594c` found no defect and recommends closing the issue without a code change. The same conclusion holds on the OOS branch `feature/oos-merge` at `d52b1889e907abcf84190ec504dde3bc93de260d`, with one condition recorded for the CBRD-27781 fix. The issue was closed as `Not a bug` on 2026-11-05. No PR is associated with this ticket.

Last modified: 2026-11-05, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [alignment-research.md](alignment-research.md) | Claim-by-claim verdicts, slotted page accounting contract, boundary calculations, probe results over 4K/8K/16K pages and alignments 1/2/4/8, caller impact, out-of-scope observations, and the OOS branch check | 2026-11-05 | 2026-11-05 | Decide with evidence whether the old issue describes a real defect before rewriting it |

Supporting files under [evidence/](evidence/) substantiate the report. `spage_boundary_probe.cpp` and `run-probe.sh` rebuild and rerun the probe against any configured CUBRID build tree. `results.jsonl` and `identity.txt` are the recorded output and its source, build, and compiler identity.
