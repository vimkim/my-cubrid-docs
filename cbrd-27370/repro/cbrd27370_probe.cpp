/* CBRD-27370 verification probe: nested READ, READ, then ordinary WRITE pgbuf_fix on the same page,
 * followed by matching unfixes. Prints the BCB global fcnt and latch mode after each step.
 * holder->fix_count is read by the accompanying gdb script at probe_point(). */
#include "config.h"
#include "dbi.h"
#include "error_manager.h"
#include "page_buffer.h"
#include "storage_common.h"
#include "thread_manager.hpp"

#include <cstdio>
#include <cstdlib>

__attribute__ ((noinline)) static void
probe_point (const char *label, THREAD_ENTRY *thread_p, PAGE_PTR page)
{
  std::printf ("%s: global_fcnt=%d latch=%d er_errid=%d%s%s\n", label, pgbuf_get_fix_count (page),
               static_cast<int> (pgbuf_get_latch_mode (page)), er_errid (),
               er_errid () != NO_ERROR ? " msg=" : "", er_errid () != NO_ERROR ? er_msg () : "");
  er_clear ();
}

int
main (int argc, char **argv)
{
  if (argc != 2)
    {
      std::fprintf (stderr, "usage: %s <dbname>\n", argv[0]);
      return 2;
    }

  std::setvbuf (stdout, nullptr, _IONBF, 0);
  db_login ("dba", nullptr);
  if (db_restart (argv[0], 0, argv[1]) != NO_ERROR)
    {
      std::fprintf (stderr, "db_restart failed: %s\n", db_error_string (3));
      return 3;
    }

  THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
  VPID vpid = { 0, 0 };

  PAGE_PTR p1 = pgbuf_fix (thread_p, &vpid, OLD_PAGE, PGBUF_LATCH_READ, PGBUF_UNCONDITIONAL_LATCH);
  probe_point ("after READ 1", thread_p, p1);

  PAGE_PTR p2 = pgbuf_fix (thread_p, &vpid, OLD_PAGE, PGBUF_LATCH_READ, PGBUF_UNCONDITIONAL_LATCH);
  probe_point ("after READ 2", thread_p, p2);

  PAGE_PTR p3 = pgbuf_fix (thread_p, &vpid, OLD_PAGE, PGBUF_LATCH_WRITE, PGBUF_UNCONDITIONAL_LATCH);
  probe_point ("after WRITE", thread_p, p3);

  std::printf ("pointers equal: %s\n", (p1 == p2 && p2 == p3) ? "yes" : "no");

  pgbuf_unfix (thread_p, p3);
  probe_point ("after UNFIX 1", thread_p, p1);

  pgbuf_unfix (thread_p, p2);
  probe_point ("after UNFIX 2", thread_p, p1);

  pgbuf_unfix (thread_p, p1);
  probe_point ("after UNFIX 3", thread_p, p1);

  std::_Exit (0);
}
