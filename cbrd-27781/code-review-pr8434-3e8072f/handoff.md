# Handoff — PR 8434 review run 2

Next checks, in order:

1. Debug OOS ctest on head+fix, plus `reviewers/r1fix/probe_notify_only_block.cpp`. Decides R2.
2. SERVER_MODE crash test: `_exit` hook in `oos_rv_update_drop_on_postpone`, at least 2 drop postpones, then a debug restart. Decides R4 and R3-restart; adds the missing ADR-0008 consequence-5 test.
3. Zero-wait gtest for R5: `xlogtb_reset_wait_msecs(0)`, hold a W latch on a chain page, commit, observe with the fail-stop hook (CS-1 in concurrency's notes). Decides R5's reachability.
4. Decide R8 (ADR note) and R6, R7, R9, R10 (small fixes).

After any fix, revalidate `prior_update_header_mvcc_info`, `vacuum_recover_lost_block_data`, the `vacuum_data_entry` constructor, and `set_oldest_unvacuumed_on_boot`.

Resume request: "Run cubrid-code-review using manifest /home/vimkim/gh/my-cubrid-docs/cbrd-27781/code-review-pr8434-3e8072f/manifest.md, scope d52b1889e..3e8072f56 plus R1 fix 38f1a458, unresolved R2 R3 R4 R5."
