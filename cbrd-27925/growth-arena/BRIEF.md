# Arena brief: bounded OOS file growth, one candidate per agent

## The user's goal

An OOS (out-of-row overflow) file must not grow without limit under repeated insert/delete churn at constant live data. The current rule is strict: if a reclaimable empty page exists, the file must not reserve a new sector. The user worries that this rule costs INSERT/UPDATE throughput. They want several candidate designs, each verified with TLA+/TLC, and a recommendation per candidate. Bounded growth is the requirement; the strict rule is negotiable.

## Work style

Follow poteto mode. Read `/home/vimkim/.claude/skills/poteto-mode/SKILL.md` and the leaf principle skills it links that you apply. Name the principles that changed a decision in your report. Write the report in Korean, plain and short.

## Facts (engine `feature/oos-merge` d52b1889e, read-only at `/home/vimkim/gh/cb/CBRD-27925-adr0008-claude`)

- `src/storage/oos_file.cpp`:
  - `oos_alloc_page_with_reclaim` (2012) is the only growth point. Every new-page allocation first calls `oos_reclaim_sweep_step` (1816).
  - Arming: `pending_deletes > 0 || !swept_this_boot`. `oos_delete` arms after every successful chain delete, whether or not a page became empty (3512). Armed sweep collects and sorts the sector table, then READ-fixes pages from a cursor until one empty page is reclaimed or a lap ends.
  - Pages become empty at exactly two places: `oos_delete_chain` (~3375) and `oos_rv_redo_delete` (~3655, INSERT rollback undo, holds the page WRITE latch while it notes).
  - Per-file single-flight growth (`pthread_cond_wait`).
  - Bestspace cache evicts pages (423–447); `oos_find_best_page` (3007) sync is ratio-gated (3065–3075).
- `file_dealloc` returns a page to the file's own sectors. Permanent-file sectors return to disk only in `file_destroy` (`src/storage/file_manager.c:4318`). So file size on disk = reserved sectors, and it never shrinks.
- ADR-0008 (accepted): no LSA gate; redo-only chain reclaim after the deciding unit commits. Model the post-ADR-0008 target.
- ADR-0009 (accepted): returning empty pages while a file is idle is NOT required. `/home/vimkim/gh/cubrid-oos-context/docs/adr/0009-reclaim-empty-pages-before-growth-not-while-idle.md`.

## Prior work (baseline, do not just repeat it)

- `cbrd-27925/growth-bound-design.md` in this worktree: eight designs compared with `cbrd-27925/growth-model/OosGrowthBound.tla` and `run.py`. Its recommendation is `cand_fullboot` (an in-memory set of emptied VPIDs; full lap after restart/overflow).
- Its known open spots: crash + concurrent writes reaches the cap for every design; undo may take a new latch at most once per grow (model restriction); refilled pages are removed from the set immediately (simplification); designs 1 (ratio/slack bound) and 3 (off-path sweep) were argued away, not modeled.
- You may reuse or copy that model. You may also write your own. Either way, re-derive the facts you depend on from the source; do not trust the prior report's conclusions.

## Rules

- Work only in your own directory `cbrd-27925/growth-arena/<your-id>/`. Do not edit other files. Do not commit; the coordinator commits.
- TLC: `java -XX:+UseParallelGC -cp ~/.cache/tlaplus/tla2tools-1.7.4.jar tlc2.TLC -workers 12 ...`. Use at most 12 workers; other agents share the 80-core machine. Put TLC metadir and state under your directory, and delete `states/` dirs when done. Keep each config under ~10 minutes; shrink constants rather than wait.
- State that results come from a finite model and give the constants.
- Never edit engine source, build, start a CUBRID server or DB, merge, push, or post to JIRA. No GUI programs.
- `rm` targets: literal paths or `${NAME:?}` expansions only.

## Deliverable

`cbrd-27925/growth-arena/<your-id>/REPORT.md` (Korean) plus your `.tla`/`.cfg`/runner files, and a final reply that contains:

1. The candidate in two or three sentences and its data shape.
2. A results table: property × setting (crashes on/off, writes during grow on/off) → PASS/FAIL, worst file size (or "cap"), worst pages examined per grow, distinct states, TLC runtime.
3. Shortest counterexample for each FAIL, in a few lines.
4. Per-allocation cost and implementation size estimate, with source lines touched.
5. Recommendation: 추천 / 조건부 추천 / 비추천, one line of reason.
6. Limits of the model.
