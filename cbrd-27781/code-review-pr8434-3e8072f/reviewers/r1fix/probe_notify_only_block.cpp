/*
 * Probe for candidate R1F-1 (r1fix reviewer, PR 8434 + R1 fix). NOT RUN in this review pass.
 *
 * Paste into unit_tests/oos/test_oos_real_vacuum_server.cpp of a worktree that carries head 3e8072f plus the
 * R1 fix (evidence/r1-fix-worktree.patch), next to NotifyOlderThanBlockOldestKeepsBlockOrderAndDrains. It reuses
 * that file's fixture (OosRealVacuum: thread_p, hfid, oos_vfid, oos_unreadable) and helpers (commit_current_tran,
 * current_log_blockid, wait_for_vacuum).
 *
 * What it checks: a log block whose only MVCC record is an RVOOS_NOTIFY_VACUUM whose MVCCID precedes the global
 * oldest visible MVCCID. With the fix, prior_update_header_mvcc_info sets the block's oldest to the global oldest
 * visible MVCCID and its newest to the notify's MVCCID, so oldest > newest.
 *
 * Expected with the fix:
 *   - release and debug: the EXPECT_LE right after the append fails (header oldest > header newest);
 *   - debug: closing the block calls vacuum_produce_log_block_data -> vacuum_data_entry (const log_header &)
 *     -> assert (oldest <= newest) (src/query/vacuum.c:8447 in head+fix), and the test binary aborts.
 * Expected at head without the fix: the EXPECT_LE passes (head lowers the oldest to the notify's MVCCID).
 *
 * Why only non-MVCC filler: vacuum workers and the master append no MVCC records, so LOG_DUMMY_GENERIC records
 * move the append position across block boundaries without giving the block another MVCC record.
 */
TEST_F (OosRealVacuum, ProbeNotifyOnlyBlockKeepsOldestAtOrBelowNewest)
{
  /* A committed transaction with MVCCID m0 that leaves a chain no row references. */
  RECDES oos_rec {};
  ASSERT_EQ (test_oos_utils::from_string_into_recdes (test_oos_utils::make_repeated_pattern_string (4096), oos_rec),
	     NO_ERROR);
  test_oos_utils::auto_freed_recdes_ptr defer_oos (&oos_rec, recdes_free_data_area);
  OID oos_oid = OID_INITIALIZER;
  ASSERT_EQ (test_oos_utils::oos_insert_from_recdes (thread_p, oos_vfid, oos_rec, oos_oid), NO_ERROR);
  const MVCCID m0 = logtb_get_current_mvccid (thread_p);
  ASSERT_TRUE (MVCCID_IS_VALID (m0));
  commit_current_tran ();

  LOG_LSA stamp = NULL_LSA;
  ASSERT_EQ (oos_get_identity_stamp (thread_p, oos_oid, &stamp), NO_ERROR);

  /* The commit-postpone condition of R1: the global oldest visible MVCCID has passed the UPDATE's MVCCID. */
  ASSERT_TRUE (wait_for_vacuum ([m0] { return log_Gl.mvcc_table.get_global_oldest_visible () > m0; }, 30));

  /* Enter a fresh block with non-MVCC records only. The first record that starts in the new block produces the
   * previous block (if it had MVCC records) and clears does_block_need_vacuum. */
  const VACUUM_LOG_BLOCKID start_block = current_log_blockid ();
  for (int guard = 0; current_log_blockid () == start_block; guard++)
    {
      ASSERT_LT (guard, 1000000);
      log_append_empty_record (thread_p, LOG_DUMMY_GENERIC, NULL);
    }
  /* One more record, so that the crossing check in prior_lsa_next_record_internal has run in the new block. */
  log_append_empty_record (thread_p, LOG_DUMMY_GENERIC, NULL);
  ASSERT_FALSE (log_Gl.hdr.does_block_need_vacuum) << "the fresh block already holds an MVCC record";

  /* The notification is the block's first and only MVCC record. If the transaction is not active here, wrap the
   * append in log_sysop_start () / log_sysop_commit (), as log_execute_run_postpone wraps the real one. */
  std::vector<char> payload = oos_test_make_reclaim_intent_payload (oos_vfid, { oos_chain_ref { oos_oid, stamp } });
  LOG_DATA_ADDR addr (&hfid.vfid, NULL, -1);
  log_append_mvcc_undo_data_with_mvccid (thread_p, RVOOS_NOTIFY_VACUUM, &addr, (int) payload.size (),
					 payload.data (), m0);
  const VACUUM_LOG_BLOCKID notify_block = current_log_blockid ();
  /* log_append_undo_crumbs_internal returns silently for an inactive transaction outside a system operation. */
  ASSERT_TRUE (log_Gl.hdr.does_block_need_vacuum) << "the notification was not appended";
  ASSERT_EQ (log_Gl.hdr.newest_block_mvccid, m0);

  /* Release-safe check of the invariant the debug assert in vacuum_data_entry enforces. */
  EXPECT_LE (log_Gl.hdr.oldest_visible_mvccid, log_Gl.hdr.newest_block_mvccid)
      << "notify-only block: oldest " << log_Gl.hdr.oldest_visible_mvccid << " > newest "
      << log_Gl.hdr.newest_block_mvccid;

  /* Close the notify-only block with non-MVCC records only. In a debug build the next line aborts in
   * vacuum_data_entry::vacuum_data_entry (assert (oldest <= newest)). */
  for (int guard = 0; current_log_blockid () <= notify_block + 1; guard++)
    {
      ASSERT_LT (guard, 1000000);
      log_append_empty_record (thread_p, LOG_DUMMY_GENERIC, NULL);
    }
  commit_current_tran ();

  /* Release only: reclaim still happens, because dispatch gates on newest (= m0). */
  ASSERT_TRUE (wait_for_vacuum ([this, oos_oid] { return oos_unreadable (oos_oid); }, 60));
}

/*
 * Realistic trigger for the same assert (also not run): one transaction UPDATEs many rows whose OOS chains it
 * replaces, so its commit postpone appends one RVOOS_NOTIFY_VACUUM per row, all with the same MVCCID m. The
 * vacuum master (vacuum_master_interval_in_msecs = 10 by default) moves the global oldest visible MVCCID past m
 * during the postpone phase, after logtb_complete_mvcc. Every block that starts after that point and holds only
 * these notifications gets oldest = global > m = newest. With vacuum_log_block_pages=4 (unittestdb), a few
 * hundred updated rows span more than one block. The test needs the postpone phase to outlast one master
 * iteration, so it is a stress test, not a deterministic one; the probe above is the deterministic check.
 */
