/*
 * Boundary probe for CBRD-26399.
 *
 * Links against the unmodified slotted_page.c object of a CUBRID build and drives
 * the public spage_* API on an in-memory page.  Page-buffer, log and error-manager
 * entry points are replaced by the minimal stubs below; saved-space bookkeeping is
 * off (is_saving = false) because it only subtracts from free space.
 *
 * Output: one JSON object per line.
 */

#include "config.h"

#include <algorithm>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>
#include <vector>

#include "slotted_page.h"
#include "storage_common.h"
#include "file_io.h"
#include "page_buffer.h"
#include "error_manager.h"
#include "log_manager.h"
#include "log_impl.h"
#include "memory_alloc.h"

static int last_er_id = 0;
static long er_count = 0;
static long spage_check_cont_free_rejects = 0;

void
er_set (int severity, const char *file_name, const int line_no, int err_id, int num_args, ...)
{
  (void) severity;
  (void) num_args;
  last_er_id = err_id;
  er_count++;
  std::fprintf (stderr, "er_set: id=%d at %s:%d\n", err_id, file_name, line_no);
}

int
er_errid (void)
{
  return last_er_id;
}

void
_er_log_debug (const char *, const int, const char *, ...)
{
}

void
pgbuf_set_dirty_debug (THREAD_ENTRY *, PAGE_PTR, bool, const char *, int, const char *)
{
}

static VPID probe_vpid = { 1, 0 };

void
pgbuf_get_vpid (PAGE_PTR, VPID * vpid)
{
  *vpid = probe_vpid;
}

VPID *
pgbuf_get_vpid_ptr (PAGE_PTR)
{
  return &probe_vpid;
}

PGBUF_LATCH_MODE
pgbuf_get_latch_mode (PAGE_PTR)
{
  return PGBUF_LATCH_WRITE;
}

PAGEID
pgbuf_get_page_id (PAGE_PTR)
{
  return probe_vpid.pageid;
}

PAGE_TYPE
pgbuf_get_page_ptype (THREAD_ENTRY *, PAGE_PTR)
{
  return PAGE_HEAP;
}

const char *
pgbuf_get_volume_label (PAGE_PTR)
{
  return "probe";
}

char *
fileio_get_volume_label (VOLID, bool)
{
  return (char *) "probe";
}

TRANID
logtb_find_current_tranid (THREAD_ENTRY *)
{
  return 1;
}

bool
logtb_is_active (THREAD_ENTRY *, TRANID)
{
  return false;
}

bool
logtb_is_current_active (THREAD_ENTRY *)
{
  return true;
}

bool
log_is_in_crash_recovery (void)
{
  return false;
}

PGLENGTH db_User_page_size = 0;

static const int GUARD = 64;
static const unsigned char GUARD_BYTE = 0xA5;

struct page_buf
{
  std::vector < unsigned char >mem;
  int psize;

  explicit page_buf (int p):mem (p + GUARD + 16), psize (p)
  {
  }
  PAGE_PTR page ()
  {
    uintptr_t base = (uintptr_t) mem.data ();
    return (PAGE_PTR) ((base + 15) & ~(uintptr_t) 15);
  }
  void arm_guard ()
  {
    std::memset (page () + psize, GUARD_BYTE, GUARD);
  }
  bool guard_ok ()
  {
    for (int i = 0; i < GUARD; i++)
      {
	if ((unsigned char) page ()[psize + i] != GUARD_BYTE)
	  {
	    return false;
	  }
      }
    return true;
  }
  void copy_from (page_buf & other)
  {
    std::memcpy (page (), other.page (), psize + GUARD);
  }
};

static SPAGE_SLOT *
slot_at (PAGE_PTR page, int psize, int slot_id)
{
  return (SPAGE_SLOT *) (page + psize - sizeof (SPAGE_SLOT)) - slot_id;
}

static std::string
check_geometry (page_buf & pb)
{
  PAGE_PTR page = pb.page ();
  int P = pb.psize;
  SPAGE_HEADER *h = (SPAGE_HEADER *) page;
  int a = h->alignment;
  int hdr = DB_ALIGN ((int) sizeof (SPAGE_HEADER), a);
  int slot_area = P - h->num_slots * (int) sizeof (SPAGE_SLOT);
  char buf[256];

  if (!pb.guard_ok ())
    {
      return "write past DB_PAGESIZE";
    }
  if (h->offset_to_free_area + h->cont_free > slot_area)
    {
      std::snprintf (buf, sizeof (buf), "free area overlaps slot array: off=%d cont=%d slot_area=%d",
		     h->offset_to_free_area, h->cont_free, slot_area);
      return buf;
    }

  struct rec
  {
    int off, len;
  };
  std::vector < rec > recs;
  long aligned_sum = 0;
  for (int i = 0; i < h->num_slots; i++)
    {
      SPAGE_SLOT *s = slot_at (page, P, i);
      if (s->offset_to_record == 0)
	{
	  continue;
	}
      int off = s->offset_to_record, len = s->record_length;
      if (off < hdr || off % a != 0)
	{
	  std::snprintf (buf, sizeof (buf), "slot %d bad offset %d", i, off);
	  return buf;
	}
      if (off + len > h->offset_to_free_area || off + len > slot_area)
	{
	  std::snprintf (buf, sizeof (buf), "slot %d record [%d,%d) beyond free_off=%d or slot_area=%d", i, off,
			 off + len, h->offset_to_free_area, slot_area);
	  return buf;
	}
      recs.push_back ({off, len});
      aligned_sum += DB_ALIGN (len, a);
    }
  if ((int) recs.size () != h->num_records)
    {
      return "num_records mismatch";
    }
  std::sort (recs.begin (), recs.end (),[](const rec & x, const rec & y)
	     {
	     return x.off < y.off;});
  for (size_t i = 1; i < recs.size (); i++)
    {
      if (recs[i].off < recs[i - 1].off + recs[i - 1].len)
	{
	  return "records overlap";
	}
    }
  long expect_total_free = (long) P - hdr - (long) h->num_slots * (long) sizeof (SPAGE_SLOT) - aligned_sum;
  if (h->total_free != expect_total_free)
    {
      std::snprintf (buf, sizeof (buf), "total_free=%d but geometry implies %ld", h->total_free, expect_total_free);
      return buf;
    }
  /* spage_check() asserts when cont_free <= -(alignment - 1); for alignment 1 that rejects a full page
   * (cont_free == 0).  Count it instead of aborting so the rest of the probe still runs. */
  if (h->cont_free <= -(a - 1))
    {
      spage_check_cont_free_rejects++;
      return "";
    }
  if (spage_check (NULL, page) != NO_ERROR)
    {
      return "spage_check failed";
    }
  return "";
}

static const char *
rc_name (int rc)
{
  switch (rc)
    {
    case SP_SUCCESS:
      return "SP_SUCCESS";
    case SP_DOESNT_FIT:
      return "SP_DOESNT_FIT";
    case SP_ERROR:
      return "SP_ERROR";
    default:
      return "OTHER";
    }
}

static const char *
anchor_name (int anchor)
{
  switch (anchor)
    {
    case ANCHORED:
      return "ANCHORED";
    case ANCHORED_DONT_REUSE_SLOTS:
      return "ANCHORED_DONT_REUSE_SLOTS";
    case UNANCHORED_ANY_SEQUENCE:
      return "UNANCHORED_ANY_SEQUENCE";
    case UNANCHORED_KEEP_SEQUENCE:
      return "UNANCHORED_KEEP_SEQUENCE";
    default:
      return "?";
    }
}

static int
insert_len (page_buf & pb, int len, PGSLOTID * slot)
{
  std::vector < char >data (len > 0 ? len : 1, 'x');
  RECDES r;
  r.area_size = len;
  r.length = len;
  r.type = REC_HOME;
  r.data = data.data ();
  return spage_insert (NULL, pb.page (), &r, slot);
}

static int
update_len (page_buf & pb, PGSLOTID slot, int len)
{
  std::vector < char >data (len > 0 ? len : 1, 'y');
  RECDES r;
  r.area_size = len;
  r.length = len;
  r.type = REC_HOME;
  r.data = data.data ();
  return spage_update (NULL, pb.page (), slot, &r);
}

static void
init_page (page_buf & pb, int anchor, unsigned short align)
{
  std::memset (pb.page (), 0, pb.psize);
  pb.arm_guard ();
  spage_initialize (NULL, pb.page (), (INT16) anchor, align, DONT_SAFEGUARD_RVSPACE);
}

static void
probe_empty_page (int io_page, unsigned short align)
{
  int P = DB_PAGESIZE;
  page_buf pb (P), work (P);
  spage_check_cont_free_rejects = 0;
  init_page (pb, ANCHORED, align);
  SPAGE_HEADER *h = (SPAGE_HEADER *) pb.page ();
  int max_rec = spage_max_record_size ();
  int max_new = spage_max_space_for_new_record (NULL, pb.page ());
  int exact_total_free = P - DB_ALIGN ((int) sizeof (SPAGE_HEADER), align);

  int ins_largest_ok = -1, ins_rc_at_max = 0, upd_largest_ok = -1, upd_rc_at_max = 0;
  std::string ins_geom_err, upd_geom_err;

  for (int len = max_rec + 8; len >= max_rec - 24; len--)
    {
      work.copy_from (pb);
      PGSLOTID slot;
      int rc = insert_len (work, len, &slot);
      if (len == max_rec)
	{
	  ins_rc_at_max = rc;
	}
      if (rc == SP_SUCCESS)
	{
	  std::string g = check_geometry (work);
	  if (!g.empty () && ins_geom_err.empty ())
	    {
	      ins_geom_err = g;
	    }
	  if (len > ins_largest_ok)
	    {
	      ins_largest_ok = len;
	    }
	}
    }

  page_buf seeded (P);
  seeded.copy_from (pb);
  PGSLOTID seed_slot;
  insert_len (seeded, 1, &seed_slot);
  for (int len = max_rec + 8; len >= max_rec - 24; len--)
    {
      work.copy_from (seeded);
      int rc = update_len (work, seed_slot, len);
      if (len == max_rec)
	{
	  upd_rc_at_max = rc;
	}
      if (rc == SP_SUCCESS)
	{
	  std::string g = check_geometry (work);
	  if (!g.empty () && upd_geom_err.empty ())
	    {
	      upd_geom_err = g;
	    }
	  if (len > upd_largest_ok)
	    {
	      upd_largest_ok = len;
	    }
	}
    }

  std::printf ("{\"probe\":\"empty_page\",\"io_page\":%d,\"db_pagesize\":%d,\"alignment\":%u,"
	       "\"sizeof_spage_header\":%zu,\"sizeof_spage_slot\":%zu,"
	       "\"init_total_free\":%d,\"init_cont_free\":%d,\"init_offset_to_free_area\":%d,"
	       "\"exact_total_free\":%d,\"spage_max_record_size\":%d,\"spage_max_space_for_new_record\":%d,"
	       "\"insert_rc_at_max_record_size\":\"%s\",\"insert_largest_ok\":%d,\"insert_geometry\":\"%s\","
	       "\"update_rc_at_max_record_size\":\"%s\",\"update_largest_ok\":%d,\"update_geometry\":\"%s\","
	       "\"spage_check_cont_free_rejects\":%ld}\n",
	       io_page, P, align, sizeof (SPAGE_HEADER), sizeof (SPAGE_SLOT), h->total_free, h->cont_free,
	       h->offset_to_free_area, exact_total_free, max_rec, max_new, rc_name (ins_rc_at_max), ins_largest_ok,
	       ins_geom_err.empty ()? "ok" : ins_geom_err.c_str (), rc_name (upd_rc_at_max), upd_largest_ok,
	       upd_geom_err.empty ()? "ok" : upd_geom_err.c_str (), spage_check_cont_free_rejects);
}

/*
 * Random insert/delete/update/vacuum workload.  After every operation the page geometry is checked, and
 * spage_max_space_for_new_record() is tested by inserting a record of exactly that length into a copy.
 */
static void
probe_workload (int io_page, unsigned short align, int anchor, unsigned seed, int ops)
{
  int P = DB_PAGESIZE;
  page_buf pb (P), work (P);
  spage_check_cont_free_rejects = 0;
  init_page (pb, anchor, align);
  std::mt19937 rng (seed);
  std::vector < PGSLOTID > live;
  long n_ins = 0, n_del = 0, n_upd = 0, n_vac = 0, n_fit_fail = 0;
  long max_space_checked = 0, max_space_rejected = 0, max_space_rejected_with_markdeleted = 0;
  long total_free_not_aligned = 0;
  std::string first_geom_err, first_reject;
  int max_rec = spage_max_record_size ();

  auto pick_len =[&](void)
  {
    int r = rng () % 10;
    if (r < 6)
      return (int) (rng () % 200) + 1;
    if (r < 9)
      return (int) (rng () % 2000) + 1;
    return (int) (rng () % max_rec) + 1;
  };

  for (int op = 0; op < ops; op++)
    {
      int r = rng () % 100;
      int rc = SP_SUCCESS;
      if (r < 50 || live.empty ())
	{
	  PGSLOTID slot;
	  rc = insert_len (pb, pick_len (), &slot);
	  if (rc == SP_SUCCESS)
	    {
	      live.push_back (slot);
	      n_ins++;
	    }
	  else
	    {
	      n_fit_fail++;
	    }
	}
      else if (r < 75)
	{
	  size_t idx = rng () % live.size ();
	  PGSLOTID slot = live[idx];
	  if (anchor == ANCHORED && (rng () % 4) == 0)
	    {
	      spage_vacuum_slot (NULL, pb.page (), slot, (rng () % 2) == 0);
	      n_vac++;
	    }
	  else
	    {
	      spage_delete (NULL, pb.page (), slot);
	      n_del++;
	    }
	  live.erase (live.begin () + idx);
	  if (anchor == UNANCHORED_KEEP_SEQUENCE || anchor == UNANCHORED_ANY_SEQUENCE)
	    {
	      for (auto & s:live)
		{
		  if (s > slot)
		    {
		      s--;
		    }
		}
	    }
	}
      else
	{
	  PGSLOTID slot = live[rng () % live.size ()];
	  rc = update_len (pb, slot, pick_len ());
	  if (rc == SP_SUCCESS)
	    {
	      n_upd++;
	    }
	  else
	    {
	      n_fit_fail++;
	    }
	}

      std::string g = check_geometry (pb);
      if (!g.empty ())
	{
	  if (first_geom_err.empty ())
	    {
	      first_geom_err = "op " + std::to_string (op) + ": " + g;
	    }
	  break;
	}

      if (((SPAGE_HEADER *) pb.page ())->total_free % align != 0)
	{
	  total_free_not_aligned++;
	}

      int m = spage_max_space_for_new_record (NULL, pb.page ());
      if (m > 0)
	{
	  work.copy_from (pb);
	  PGSLOTID s2;
	  int rc2 = insert_len (work, m, &s2);
	  max_space_checked++;
	  if (rc2 != SP_SUCCESS)
	    {
	      SPAGE_HEADER *h = (SPAGE_HEADER *) pb.page ();
	      bool has_markdeleted = false;
	      bool has_reusable = false;
	      for (int i = 0; i < h->num_slots; i++)
		{
		  SPAGE_SLOT *s = slot_at (pb.page (), P, i);
		  if (s->offset_to_record == 0 && s->record_type == REC_MARKDELETED)
		    {
		      has_markdeleted = true;
		    }
		  if (s->record_type == REC_DELETED_WILL_REUSE)
		    {
		      has_reusable = true;
		    }
		}
	      max_space_rejected++;
	      if (has_markdeleted && !has_reusable)
		{
		  max_space_rejected_with_markdeleted++;
		}
	      if (first_reject.empty ())
		{
		  char buf[256];
		  std::snprintf (buf, sizeof (buf),
				 "op %d: max_space=%d rc=%s total_free=%d num_slots=%d num_records=%d markdeleted=%d reusable=%d",
				 op, m, rc_name (rc2), h->total_free, h->num_slots, h->num_records, has_markdeleted,
				 has_reusable);
		  first_reject = buf;
		}
	    }
	  else
	    {
	      std::string g2 = check_geometry (work);
	      if (!g2.empty () && first_geom_err.empty ())
		{
		  first_geom_err = "op " + std::to_string (op) + " (max_space insert): " + g2;
		}
	    }
	}
    }

  std::printf ("{\"probe\":\"workload\",\"io_page\":%d,\"db_pagesize\":%d,\"alignment\":%u,\"anchor\":\"%s\","
	       "\"seed\":%u,\"ops\":%d,\"inserts\":%ld,\"deletes\":%ld,\"vacuums\":%ld,\"updates\":%ld,"
	       "\"doesnt_fit\":%ld,\"total_free_not_aligned\":%ld,\"geometry\":\"%s\",\"max_space_checked\":%ld,\"max_space_rejected\":%ld,"
	       "\"max_space_rejected_only_markdeleted_empty_slots\":%ld,\"first_max_space_reject\":\"%s\","
	       "\"spage_check_cont_free_rejects\":%ld}\n",
	       io_page, P, align, anchor_name (anchor), seed, ops, n_ins, n_del, n_vac, n_upd, n_fit_fail,
	       total_free_not_aligned, first_geom_err.empty ()? "ok" : first_geom_err.c_str (), max_space_checked, max_space_rejected,
	       max_space_rejected_with_markdeleted, first_reject.c_str (), spage_check_cont_free_rejects);
}

int
main (int argc, char **argv)
{
  int ops = argc > 1 ? std::atoi (argv[1]) : 20000;
  const int io_pages[] = { 4096, 8192, 16384 };
  const unsigned short aligns[] = { CHAR_ALIGNMENT, SHORT_ALIGNMENT, INT_ALIGNMENT, DOUBLE_ALIGNMENT };
  const int anchors[] = { ANCHORED, ANCHORED_DONT_REUSE_SLOTS, UNANCHORED_KEEP_SEQUENCE };
  const int reserved = (int) (sizeof (FILEIO_PAGE_RESERVED) + sizeof (FILEIO_PAGE_WATERMARK));

  for (int io:io_pages)
    {
      db_User_page_size = (PGLENGTH) (io - reserved);
      for (unsigned short a:aligns)
	{
	  probe_empty_page (io, a);
	}
      for (unsigned short a:aligns)
	{
	  for (int anchor:anchors)
	    {
	      probe_workload (io, a, anchor, 26399u + io + a * 7 + anchor, ops);
	    }
	}
    }
  std::fprintf (stderr, "er_set calls: %ld\n", er_count);
  return 0;
}
