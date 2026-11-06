/*
 * probe_ss3_read_after_tail_reclaim.cpp - NOT RUN. Proposed gtest for candidate SS-3 (systems-storage report).
 *
 * Question: with tail-first reclaim and no LSA reclaim gate, a multi-chunk chain whose head still verifies can have
 * its tail chunk deleted AND the tail's page deallocated. oos_read_within_page (src/storage/oos_file.cpp:2601-2619)
 * fixes continuation pages with plain pgbuf_fix (OLD_PAGE). What does a read through the head do then?
 *
 * Source argument: pgbuf_fix (OLD_PAGE) on a deallocated page asserts in debug builds
 * (src/storage/page_buffer.c:2511-2519, `case OLD_PAGE: assert (false);`) and returns ER_PB_BAD_PAGEID in release
 * builds; the head-page path (oos_fix_page_if_oos) is the tolerant one, the continuation path is not.
 *
 * Reachability caveat (see report SS-3): ADR-0008 says no legitimate reader can race a reclaimer (vacuum waits for
 * snapshots; the eager path has no concurrent reader), so this is a robustness probe, not a repro of a user path.
 *
 * How to use (coordinator or lead, later):
 *   1. Paste into unit_tests/oos/test_oos_reclaim.cpp, inside the OosReclaimTest fixture file (uses its
 *      insert_chain, chunk_is_present, bridge_oos_get_max_chunk_size_within_page helpers).
 *   2. Debug preset, run: ./test_oos_reclaim --gtest_filter=OosReclaimTest.ReadThroughAVerifiedHeadAfterTheTailPageIsReclaimed
 *      Expected (debug) if SS-3 is real: process abort on `assert (false)` in pgbuf_fix, backtrace through
 *      oos_read_within_page <- oos_read_across_pages <- oos_read.
 *      Expected (release): oos_read returns ER_PB_BAD_PAGEID, not ER_HEAP_OOS_CORRUPTED_RECORD.
 *   3. After a fix that routes the continuation fix through oos_fix_page_if_oos and maps "gone" to
 *      ER_HEAP_OOS_CORRUPTED_RECORD, the test passes in both builds.
 */

TEST_F (OosReclaimTest, ReadThroughAVerifiedHeadAfterTheTailPageIsReclaimed)
{
  std::vector<oos_chain_ref> chunks;
  insert_chain (oos_vfid, 3, chunks);	/* head h, c1, tail c2; each chunk fills its own page */

  const int total = oos_get_length (thread_p, chunks[0].head_oid);
  ASSERT_GT (total, 0);

  /* Reclaim one chunk (the tail) and stop before the head: the "interrupted reclaim" state. */
  oos_test_fail_reclaim_after_chunk_deletes (1);
  ASSERT_EQ (oos_delete (thread_p, oos_vfid, chunks[0], NULL, NULL), ER_GENERIC_ERROR);
  er_clear ();
  ASSERT_TRUE (chunk_is_present (chunks[0]));
  ASSERT_TRUE (chunk_is_present (chunks[1]));
  ASSERT_FALSE (chunk_is_present (chunks[2]));

  /* No LSA gate any more: the emptied tail page is deallocated at once. */
  std::vector<VPID> candidates = { VPID { chunks[2].head_oid.pageid, chunks[2].head_oid.volid } };
  ASSERT_EQ (oos_reclaim_empty_pages (thread_p, oos_vfid, candidates), NO_ERROR);

  std::vector<char> dest ((std::size_t) total);
  const int err = oos_read (thread_p, chunks[0], oos_buffer (dest.data (), dest.size ()));

  /* A tolerant continuation fix reports a stale chain, never an assertion or a raw page-buffer error. */
  EXPECT_EQ (err, ER_HEAP_OOS_CORRUPTED_RECORD);
  er_clear ();
}
