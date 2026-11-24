# Coverage: CUBRID/cubrid#8531 ([CBRD-27935]) at `d26383d2df856a1bfb6989bbff8aa7760de8055c`

Comparison: `git diff 95cc1bc172a7b431948e7b8297987a9466371986 d26383d2df856a1bfb6989bbff8aa7760de8055c` (merge base = PR base). One changed path: [`src/query/vacuum.c#L2436-L2446`](https://github.com/CUBRID/cubrid/blob/d26383d2df856a1bfb6989bbff8aa7760de8055c/src/query/vacuum.c#L2436-L2446) (+5/-2, one hunk in `vacuum_heap_record`, `REC_RELOCATION` case). No renames, deletions, submodules, or binaries. Patch SHA-256 `bc6916b2612df0ba65732839802be0ef64d66e34302d5c40bb2cfefac9bf18d1`.

## Path and invariant coverage

| Surface / invariant | Primary owner | Pinned source | Evidence | Result | Remaining |
| --- | --- | --- | --- | --- | --- |
| Changed hunk: `pgbuf_set_dirty(fwd, DONT_FREE)` → `log_sysop_commit` → `pgbuf_unfix_and_init(fwd)` (`vacuum.c:2439-2445`) | Latch reviewer | `vacuum.c`, `page_buffer.c:5530-5570`, `page_buffer.h:73` | L3 source; L5 runtime replay (coordinator) | Correct. WRITE latch retained; dirty mark not lost; no new fallible branch; outer cleanup (`vacuum.c:1738-1741, 1771-1774`) sees NULL | none |
| I1 Durable reuse vs. open sysop: a second writer's committed change to the forward slot or its bytes never becomes durable without `LOG_SYSOP_END` | Latch + Recovery (shared challenge) | `vacuum.c:2003/2026, 2443-2445`; `log_manager.c:3906-3985, 4564-4620`; `log_append.cpp:1381-1559`; `log_page_buffer.c:3157-3200`; `bestspace.cpp:753, 962` | L3 source (both seats, independent); TLC model PASS at head; L5 runtime replay at head 2/2 pass, base 2/2 fail | Holds at head; broken at base (the reported defect) | none |
| I2 Restart undo of an open vacuum sysop reinserts into the original slot via `spage_insert_for_recovery` | Recovery reviewer | `log_recovery.c:987-1009, 1634-1660, 4756-4790, 4995-5130`; `vacuum.c:7589-7594`; `slotted_page.c:1933-1995` | L2-3 source; base runtime replay hit the assertion at `slotted_page.c:1969` | Confirmed as the failing path at base; unreachable with a foreign occupant at head | none |
| I3 Page/log deadlock: retaining forward page through `log_sysop_commit` adds no reverse edge | Latch + Recovery (shared challenge) | `log_manager.c:3962-3963, 3974-3988, 4582-4618, 8288-8292`; `log_append.cpp:1556-1581`; `log_page_buffer.c:3114-3198, 7454-7475` | L3 source (both seats) | No new edge; home page already held through the same call at base | none |
| I4 Home page and `REC_BIGONE` paths unchanged | Recovery reviewer | `vacuum.c:2405, 2448-2481` | L2 (diff is a single hunk) | Unchanged | none |
| I5 No latch-free consumer of the advertised bestspace candidate (`heap_add_bestpage` stays before sysop commit) | Latch + Recovery | `heap_file.c:4621-4642, 4736-4778`; `bestspace.cpp:370-383, 745-774, 947-1008, 1543-1600`; `heap_file.c:22246-22250` | L2-3 | Every consumer WRITE-latches (waits or conditional-fails); the hint is harmless | none |
| I6 Bytes-only variant (writer consumes returned bytes via another slot) | Coordinator (model) | model `VacuumUndoFindsRoom` | TLC PASS at head (225116 states); base known finding `relocation-forward-window-room` | Holds at head in model; same latch guard as slot case | runtime replay of bytes-only variant not run (optional; author also did not run it) |
| Log prefix flush under the in-flight prior window (U1) | Coordinator | `log_page_buffer.c:3157-3200` (`prior_lsa_remove_prior_list`, `logpb_prior_lsa_append_all_list`); `log_prior_inflight.hpp` | L3 source | Whole prior list is detached in LSA order under `prior_lsa_mutex`; in-flight ring is a read-side cache for MVCC undo images only | none |
| HA / CDC / log & disk format | Recovery reviewer | `log_manager.c:3962-3963`; `log_applier.c:5825-5845, 6257-6275` | L2 | Not applicable: no record added/removed/reordered by the vacuum worker; system worker writes no repl/supplemental records; format unchanged | none |
| SA mode | Latch + Recovery | `log_manager.c:3881-3891`; `page_buffer.c:9493-9500` | L2 source | Single-threaded; own-held WRITE page accepted by checkpoint flush; same class as home page at base | SA checkpoint not executed (optional) |
| Performance (longer forward WRITE hold) | Latch reviewer | `log_append.cpp:1556-1581` | L2 | Added hold = one `log_sysop_commit` (no I/O normally; 1 ms sleep only under prior-list pressure). No measured regression claimed | none |
| Standards, requirements, assertions | Coordinator | diff; CBRD-27935; PR body; `cubrid-static-check` | static check 0 new findings; indentation preserved; comment accurate | Conforms; matches Jira goal | none |
| Existing CI at pinned head | Coordinator | run 44051622940 | `cubrid-ci collect`; `cubrid-tcc status` | build debug/release, `test_medium`, `test_sql` pass. `test_shell` 2 NOK (`apis_1124`, `apis_1125`, CCI/JDBC `sslmode`; fail in 68/68 and 72/72 recent runs across PRs). `test_sql_by_cci` failed; artifact collection failed (remote decode error) | `sql_by_cci` triage is outside code review (not a review blocker) |

## Shared challenge

Question: "Can a second writer reuse the forward slot or its bytes and make its transaction durable while recovery still treats the relocation sysop as open, or can retaining the page through `log_sysop_commit` introduce a page/log mutex cycle?"

| Seat | Model | Independent answer |
| --- | --- | --- |
| Latch / systems / storage | `gpt-6.1-sol`, high (previous Codex session) | No to both. Guard: forward WRITE latch held until after `log_append_sysop_end` → `prior_lsa_next_record` links `SYSOP_END`; prefix flush + WAL. No reverse edge from append/drain. |
| Recovery / HA | `claude-opus-5-5` (this session) | No to both. Same guard, plus the restart-side trace (outermost system-worker sysop, `lastparent_lsa = NULL`, descending-LSA undo). No new wait-for edge. |

Model diversity: two vendors. The planned `gpt-6.2-sol` recovery seat from the first attempt never ran. This session filled it with Opus. No disagreement.

## Not-applicable domains

- `cubrid-verify-vacuum-slot-undo`: not applicable. The pinned tree has no OOS code (`git ls-tree` finds no OOS sources), and the script reports `OUT OF SYNC` (exit 2), as its SKILL documents for `develop`.
- HA: no HA-visible delta (see row above).
