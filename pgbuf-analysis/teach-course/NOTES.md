# Teaching notes

- The learner's outcome is a teammate presentation with heavy questioning, not passive source familiarity.
- Keep lessons offline, visual, short, and source-anchored. Always report exact filesystem paths because a graphical browser may be unavailable.
- Use Korean explanations with exact English/C identifiers so the material transfers directly to code review and presentation language.
- Do not create a learning record until the learner demonstrates understanding through retrieval or teach-back.
- Start at the public contract and converged postcondition before descending into latch CAS/waiter mechanics.
- Whenever asking the learner a question, show the model/recommended answer together with the question. Ask for reasoning or comparison so the learner can demonstrate understanding without relying on hidden-answer recall.

## Session progress (2026-09-01, lesson 0002 mastery check)

- Passed: main caller-contract ordering (log → set dirty → unfix) and failure-matrix row 6 (crash after durable commit WAL but before page flush is recoverable via redo).
- Gaps: row 4 (did not know what "누락 from writeback" means — DIRTY flag as the flusher's work queue membership) and row 7 (flush generation accounting / concurrent re-dirty — did not understand). Row 7 is the next lesson's topic (writer/flusher interleaving), so teach it in-line first, then re-check before writing learning record 0002.
- Follow-up in-chat teaching: row 4 passed on retrieval (two corrections: "flusher assumes page never used" → "no unpropagated generation"; `pgbuf_set_lsa` sets dirty only in release build, still a caller bug). Answered "is concurrent write during flush a bug?" with source evidence (local snapshot buffer `memcpy` at `page_buffer.c:10930`, `PGBUF_BCB_UNLOCK` before WAL force/write at 10951, flag algebra `pgbuf_bcb_mark_is_flushing/was_flushed/was_not_flushed` at 16188–16237).
- Learner then asked to step back to fundamentals: what BCB, hash chain, and the internal structures are. Created lesson 0003 (`lessons/0003-one-bcb-many-lists.html`), diagram asset (`assets/pgbuf-pool-map.svg`), and reference card (`reference/pgbuf-structure-map.html`). PENDING: lesson 0003 retrieval, then the still-open row-7 variant check (flush-failure path: `was_dirty` → `pgbuf_bcb_mark_was_not_flushed()` → `oldest_unflush_lsa` restore) before writing learning record 0002.
- Lesson 0003 retrieval PASSED (2026-09-01): learner restated the `pgbuf_lock_page()` mechanism, reasoned the prefetch/slot-sizing question, and completed the no-lock-table counterfactual (duplicate BCBs → split-brain → flush-order lost update). Learning record 0002 written (`0002-pool-structures-and-load-serialization.md`). Cardinality/sizing content was also added to the presentation deck as §2.1. STILL PENDING: row-7 flush-failure variant, which gates the durability-chain learning record (will be 0003).
- Learner asked for cardinality/sizing (per-DB vs per-thread vs global, sizes). Answered from `pgbuf_initialize_*()` with a table; added a "Cardinality & sizing" section to `reference/pgbuf-structure-map.html`. Notables surfaced: hash table fixed at `1<<20` buckets (~56MB regardless of pool size), AOUT disabled by default (`pb_aout_ratio` default 0.0 — soften lesson 0003's 2Q claim when rehearsing), private LRU is per-transaction not per-thread, debug holders carry `fixed_at[64KB]`.
