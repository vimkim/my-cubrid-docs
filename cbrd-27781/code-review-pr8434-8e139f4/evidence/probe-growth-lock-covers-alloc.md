# Replay request S-1 (test gap, not a defect claim)
Goal: show that the growth lock held through file_alloc (oos_alloc_page_with_reclaim, oos_file.cpp:2095-2122)
excludes a second grower between the first grower's set check and its file_alloc.
Probe (unit_tests/oos/test_oos_growth_sweep.cpp, new TEST):
 1. oos_create_file; fill 3 pages; delete chunks of page B so it is empty and in the set (oos_test_reclaim_emptied_count==1).
 2. Thread G1 runs insert_page_filling_record with a hook pausing after oos_reclaim_check_emptied returned reclaimed=false
    for a BUSY page (hold B's WRITE latch from the test thread so G1 sees BUSY) and before file_alloc.
 3. Thread G2 starts insert_page_filling_record; assert oos_test_reclaim_waiter_count()==1 (blocked on the growth lock).
 4. Release B's latch, release G1. Expect count_user_pages unchanged after both inserts finish (B reused by one, other grows by at most 1).
Expected: passes. Existing ConcurrentGrowerWaitsForActiveSweep only forces sweep_in_progress and calls oos_test_reclaim_sweep_step; it
never reaches file_alloc, so it does not cover the lock-through-alloc fix of 8e139f4db.
