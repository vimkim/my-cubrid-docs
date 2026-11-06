/*
 * probe_ss2_unpack_uninit.cpp - NOT RUN. Proposed gtest for candidate SS-2 (systems-storage report).
 *
 * Question: when oos_unpack_reclaim_intent rejects a payload that is shorter than the fixed header, does the
 * caller then read an indeterminate `oos_reclaim_intent_header header` (src/storage/oos_file.cpp:3839 and :3952,
 * passed as header.oos_vfid to oos_reclaim_fail_stop at :3845 and :3958)?
 *
 * Source argument: oos_unpack_reclaim_intent returns at :3682-3686 before the memcpy at :3687 initialises its
 * out-parameter, so `header.oos_vfid` is read uninitialised by VFID_AS_ARGS in the oos_error call of
 * oos_reclaim_fail_stop (:3808-3815).
 *
 * How to use (coordinator or lead, later):
 *   1. Paste this TEST into unit_tests/oos/test_oos_reclaim.cpp (SA_MODE binary, same fixture and includes), or
 *      build it as its own binary next to it.
 *   2. Build the unit test binary in a DEBUG preset with CUBRID_UNIT_TEST_ENABLED.
 *   3. Run it under valgrind:
 *        valgrind --track-origins=yes --error-exitcode=9 ./test_oos_reclaim \
 *                 --gtest_filter=OosReclaimPayload.*
 *      Expected result if SS-2 is real: a "Conditional jump or move depends on uninitialised value(s)" or
 *      "Use of uninitialised value" report whose origin is the stack variable `header` in
 *      oos_rv_reclaim_on_postpone, reached from vfprintf via oos_error. The gtest assertions themselves pass.
 *      (AddressSanitizer does not detect this; MemorySanitizer would.)
 *   4. After the fix (`oos_reclaim_intent_header header = {};` in both callers) valgrind must report nothing.
 */

#include "gtest/gtest.h"

#include "oos_file.hpp"
#include "recovery.h"
#include "xserver_interface.h"
#include "test_oos_common.hpp"

// XXX: SHOULD BE THE LAST INCLUDE HEADER
#include "memory_wrapper.hpp"

namespace
{
  int g_probe_fail_stops = 0;
  int g_probe_fail_stop_error = NO_ERROR;

  void
  probe_record_fail_stop (int error)
  {
    g_probe_fail_stops++;
    g_probe_fail_stop_error = error;
  }
}

TEST (OosReclaimPayload, ShortIntentPayloadFailStopsWithoutReadingAnUninitialisedHeader)
{
  g_probe_fail_stops = 0;
  oos_test_set_reclaim_fail_stop_hook (probe_record_fail_stop);

  /* Shorter than sizeof (oos_reclaim_intent_header) (60 bytes with the head layout), so the length check in
   * oos_unpack_reclaim_intent fails before it initialises the caller's header. */
  const char tiny[4] = { 1, 2, 3, 4 };
  LOG_RCV rcv;
  rcv.data = tiny;
  rcv.length = (int) sizeof (tiny);

  EXPECT_EQ (oos_rv_reclaim_on_postpone (thread_p, &rcv), NO_ERROR);
  EXPECT_EQ (g_probe_fail_stops, 1) << "a malformed committed intent must fail-stop";
  EXPECT_EQ (g_probe_fail_stop_error, ER_GENERIC_ERROR);

  oos_test_set_reclaim_fail_stop_hook (NULL);
  er_clear ();
}

TEST (OosReclaimPayload, NegativeCountAndLengthMismatchAreRejected)
{
  /* Complements SS-2: the length validation itself. n_refs is at offset 32 of the 60-byte header
   * (VFID 8 + HFID 12 + OID 8 + flags 4, then n_refs). Build a header-sized buffer with n_refs = -1 and one with
   * n_refs = 1 but no ref bytes; both must fail-stop, neither may allocate or read beyond the buffer. */
  oos_test_set_reclaim_fail_stop_hook (probe_record_fail_stop);

  for (int n_refs : { -1, 1, 0x7fffffff })
    {
      g_probe_fail_stops = 0;
      char buf[60] = {};
      std::memcpy (buf + 32, &n_refs, sizeof (n_refs));
      LOG_RCV rcv;
      rcv.data = buf;
      rcv.length = (int) sizeof (buf);
      EXPECT_EQ (oos_rv_reclaim_on_postpone (thread_p, &rcv), NO_ERROR) << "n_refs=" << n_refs;
      EXPECT_EQ (g_probe_fail_stops, 1) << "n_refs=" << n_refs;
      er_clear ();
    }

  oos_test_set_reclaim_fail_stop_hook (NULL);
}
