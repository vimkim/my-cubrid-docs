# Replay request RCV-P1: restart undo of RVOOS_INSERT (new 8-byte undo image)

Status: sketch, not compiled. The coordinator or author turns it into a test case. Pattern to copy:
unit_tests/oos/test_oos_server_crash_recovery.cpp (fork a child, std::_Exit after a log flush, boot a second child).

Pinned head: 8e139f4db. Build: build_preset_debug_gcc (coordinator-owned).

Steps
1. Child A (SERVER_MODE, own database): boot; create an OOS file (oos_create_file); start a transaction;
   oos_insert one multi-page value (at least 2 chunks, so at least one data page holds only this
   transaction's chunks); record the head OID and the VPIDs of the chunk pages; logpb_force_flush_pages;
   std::_Exit (the transaction is a loser: no commit, no abort record).
2. Child B: boot_restart_server (restart recovery undoes the loser: oos_rv_undo_insert runs with
   rcv->length == sizeof (VFID); a second crash variant can _Exit in B after the undo phase and boot a
   child C, so the LOG_COMPENSATE redo path, which also calls oos_rv_undo_insert, is exercised).
3. In B (and C): for each recorded chunk OID, oos_chunk_exists -> expect false;
   oos_test_reclaim_emptied_count (oos_vfid) -> expect >= the number of pages that held only this
   transaction's chunks; then one oos_insert of a value of the same size -> expect no new sector
   (file page count unchanged, or reclaim_growth_examined_pages > 0 and the inserted chunk lands on one
   of the recorded VPIDs).

Expected (if the code is correct): boot succeeds in B and C, no assert in oos_rv_delete_chunk
(spage_delete never returns NULL_SLOTID), the chunk slots are empty, the emptied pages are reused.

Predicted actual: same as expected (source argument in reviewers/recovery.md, Q1 and S-3/S-4).
What it would refute: a wrong undo-image length/layout, a CLR redo that reads other bytes, or a
recovery-time set update that crashes because oos_Bestspace is not ready
(heap_manager_initialize at boot_sr.c:2299 precedes log_initialize at boot_sr.c:2435).
