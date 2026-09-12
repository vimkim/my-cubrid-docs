#!/usr/bin/env python3
"""CBRD-26659 ticket 16: apply the instrumentation edits to the oos-instr-f4299ac0c worktree.

Every edit is an exact, unique string replacement; the script aborts before writing anything if any
anchor is missing or ambiguous, so a partial application cannot happen.
"""
import sys

WT = "/home/vimkim/gh/cb/oos-instr-f4299ac0c"
T = "\t"

edits = []  # (path, old, new)


def rep(path, old, new):
    edits.append((WT + "/" + path, old, new))


# --------------------------------------------------------------------------------------------------
# 0001: fault-injection facility -- OOS codes, site descriptor, acknowledging handlers
# --------------------------------------------------------------------------------------------------
rep("src/base/fault_injection.h",
    "  FI_TEST_DBLINK_2PC_CRASH_BETWEEN_6_7 = 600004,\t/* after (6) send decision, before (7) DELETE row */\n"
    "\n"
    "  /* etc .... */\n",
    "  FI_TEST_DBLINK_2PC_CRASH_BETWEEN_6_7 = 600004,\t/* after (6) send decision, before (7) DELETE row */\n"
    "\n"
    "  /* OOS -- CBRD-26659 adversarial testcase campaign (700000 ~ 700099)\n"
    "   * Deterministic sites. Each passes an FI_SITE_DESC as the FI_TEST_ARG argument; the acknowledging handler\n"
    "   * (fi_handler_ack_fail, fi_handler_ack_crash) writes a \"FAULT INJECTION ACK\" line to the server error log\n"
    "   * when it fires. fault_injection_fire_at_occurrence selects the reach at which an armed site fires.\n"
    "   */\n"
    "  FI_TEST_OOS_PUBLISH_OID_BAD_ALLOC = 700000,\t/* allocation: OOS OID publication during insert */\n"
    "  FI_TEST_OOS_READ_GROUPED_BAD_ALLOC = 700001,\t/* allocation: grouped Resolve prefetch during read */\n"
    "  FI_TEST_OOS_DELETE_HINT_BAD_ALLOC = 700002,\t/* allocation: reclaim hint list during chain delete */\n"
    "  FI_TEST_OOS_PAGE_WRITE_FAIL = 700003,\t/* data I/O: disk write of a PAGE_OOS page fails */\n"
    "  FI_TEST_OOS_LOG_WRITE_FAIL = 700004,\t/* log I/O: disk write of an active log page fails */\n"
    "  FI_TEST_OOS_INSERT_MANY_FAIL = 700005,\t/* interruption: oos_insert_many fails between publications */\n"
    "  FI_TEST_OOS_CRASH_BETWEEN_CHUNKS = 700006,\t/* interruption: crash between the chunk inserts of one chain */\n"
    "  FI_TEST_OOS_CRASH_BEFORE_HEAP_PUBLICATION = 700007,\t/* interruption: crash after the chunks, before the heap insert */\n"
    "  FI_TEST_OOS_RV_UNDO_INSERT_FAIL = 700008,\t/* rollback: undo of RVOOS_INSERT fails at run time */\n"
    "  FI_TEST_OOS_VACUUM_DELETE_FAIL = 700009,\t/* vacuum: forward-walk delete of a value chain fails */\n"
    "  FI_TEST_OOS_RECLAIM_WRITE_FIX_SKIP = 700010,\t/* reclamation: write fix of a reclaim candidate is skipped */\n"
    "  FI_TEST_OOS_RV_REDO_INSERT_FAIL = 700011,\t/* recovery: redo of RVOOS_INSERT fails during restart */\n"
    "\n"
    "  /* etc .... */\n")

rep("src/base/fault_injection.h",
    "#define FI_INIT_STATE 0\n",
    "#define FI_INIT_STATE 0\n"
    "\n"
    "/*\n"
    " * FI_SITE_DESC - identity of a deterministic fault-injection site. The site passes one static descriptor as the\n"
    " * FI_TEST_ARG argument. The acknowledging handler counts the reaches, decides whether this reach fires\n"
    " * (fault_injection_fire_at_occurrence: 0 = every reach, k > 0 = the k-th reach only) and, when it fires, logs\n"
    " * \"FAULT INJECTION ACK site=... code=... target_operation=... requested_action=... reach=... fired=...\" as a\n"
    " * notification in the server error log, so a test can prove that the fault fired and how often.\n"
    " */\n"
    "typedef struct fi_site_desc FI_SITE_DESC;\n"
    "struct fi_site_desc\n"
    "{\n"
    "  FI_TEST_CODE code;\t\t/* code the site is armed with */\n"
    "  const char *site;\t\t/* function that hosts the site */\n"
    "  const char *target_operation;\t/* operation the fault interrupts */\n"
    "  const char *requested_action;\t/* what the site does when the handler fires */\n"
    "  volatile int reach_count;\t/* times the armed site was reached */\n"
    "  volatile int fired_count;\t/* times the handler told the site to act */\n"
    "};\n")

rep("src/base/fault_injection.c",
    "#include <assert.h>\n",
    "#include <assert.h>\n"
    "#include <stdio.h>\n")

rep("src/base/fault_injection.c",
    "static int fi_handler_hold (THREAD_ENTRY * thread_p, void *arg, const char *caller_file, const int caller_line);\n",
    "static int fi_handler_hold (THREAD_ENTRY * thread_p, void *arg, const char *caller_file, const int caller_line);\n"
    "static int fi_handler_ack_fail (THREAD_ENTRY * thread_p, void *arg, const char *caller_file, const int caller_line);\n"
    "static int fi_handler_ack_crash (THREAD_ENTRY * thread_p, void *arg, const char *caller_file, const int caller_line);\n"
    "static bool fi_site_fire_and_acknowledge (void *arg, const char *caller_file, const int caller_line);\n")

rep("src/base/fault_injection.c",
    "  {FI_TEST_DBLINK_2PC_CRASH_BETWEEN_6_7, fi_handler_exit, FI_INIT_STATE}\n"
    "};\n",
    "  {FI_TEST_DBLINK_2PC_CRASH_BETWEEN_6_7, fi_handler_exit, FI_INIT_STATE},\n"
    "  /* OOS -- CBRD-26659 campaign sites: deterministic, acknowledged in the server error log */\n"
    "  {FI_TEST_OOS_PUBLISH_OID_BAD_ALLOC, fi_handler_ack_fail, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_READ_GROUPED_BAD_ALLOC, fi_handler_ack_fail, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_DELETE_HINT_BAD_ALLOC, fi_handler_ack_fail, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_PAGE_WRITE_FAIL, fi_handler_ack_fail, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_LOG_WRITE_FAIL, fi_handler_ack_fail, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_INSERT_MANY_FAIL, fi_handler_ack_fail, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_CRASH_BETWEEN_CHUNKS, fi_handler_ack_crash, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_CRASH_BEFORE_HEAP_PUBLICATION, fi_handler_ack_crash, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_RV_UNDO_INSERT_FAIL, fi_handler_ack_fail, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_VACUUM_DELETE_FAIL, fi_handler_ack_fail, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_RECLAIM_WRITE_FIX_SKIP, fi_handler_ack_fail, FI_INIT_STATE},\n"
    "  {FI_TEST_OOS_RV_REDO_INSERT_FAIL, fi_handler_ack_fail, FI_INIT_STATE}\n"
    "};\n")

rep("src/base/fault_injection.c",
    "      return ER_FAILED;\n"
    "    }\n"
    "\n"
    "  return NO_ERROR;\n"
    "}\n"
    "#endif\n",
    "      return ER_FAILED;\n"
    "    }\n"
    "\n"
    "  return NO_ERROR;\n"
    "}\n"
    "\n"
    "/*\n"
    " * fi_site_fire_and_acknowledge - count a reach of a deterministic site, decide whether this reach fires and,\n"
    " *   when it does, write the acknowledgement to the server error log (CBRD-26659 campaign).\n"
    " *\n"
    " * return: true when the site must act, false when it must behave normally\n"
    " *\n"
    " *   arg(in): the site's FI_SITE_DESC\n"
    " *   caller_file(in), caller_line(in): the site\n"
    " *\n"
    " * Note: The acknowledgement is a notification, not an error of the calling thread; the error state is cleared\n"
    " *       afterwards and the site sets whatever error its action requires. With fault_injection_fire_at_occurrence\n"
    " *       = 0 every reach fires; with k > 0 only the k-th reach since the server started fires (one-shot).\n"
    " */\n"
    "static bool\n"
    "fi_site_fire_and_acknowledge (void *arg, const char *caller_file, const int caller_line)\n"
    "{\n"
    "  FI_SITE_DESC *desc = (FI_SITE_DESC *) arg;\n"
    "  char msg[512];\n"
    "  int reach, fired, fire_at;\n"
    "\n"
    "  if (desc == NULL)\n"
    "    {\n"
    "      assert (desc != NULL);\n"
    "      return false;\n"
    "    }\n"
    "\n"
    "  reach = ATOMIC_INC_32 (&desc->reach_count, 1);\n"
    "  fire_at = prm_get_integer_value (PRM_ID_FAULT_INJECTION_FIRE_AT_OCCURRENCE);\n"
    "  if (fire_at > 0 && reach != fire_at)\n"
    "    {\n"
    "      return false;\n"
    "    }\n"
    "\n"
    "  fired = ATOMIC_INC_32 (&desc->fired_count, 1);\n"
    "  snprintf (msg, sizeof (msg),\n"
    "\t    \"FAULT INJECTION ACK site=%s code=%d target_operation=\\\"%s\\\" requested_action=\\\"%s\\\" reach=%d fired=%d \"\n"
    "\t    \"fire_at=%d\", desc->site, (int) desc->code, desc->target_operation, desc->requested_action, reach, fired,\n"
    "\t    fire_at);\n"
    "  er_set (ER_NOTIFICATION_SEVERITY, caller_file, caller_line, ER_FAILED_ASSERTION, 1, msg);\n"
    "  er_clear ();\n"
    "\n"
    "  return true;\n"
    "}\n"
    "\n"
    "/*\n"
    " * fi_handler_ack_fail - acknowledge and tell the site to fail (the site chooses how: error return, throw, skip)\n"
    " *\n"
    " * return: ER_FAILED when the site must act, NO_ERROR otherwise\n"
    " */\n"
    "static int\n"
    "fi_handler_ack_fail (THREAD_ENTRY * thread_p, void *arg, const char *caller_file, const int caller_line)\n"
    "{\n"
    "  if (fi_site_fire_and_acknowledge (arg, caller_file, caller_line))\n"
    "    {\n"
    "      return ER_FAILED;\n"
    "    }\n"
    "\n"
    "  return NO_ERROR;\n"
    "}\n"
    "\n"
    "/*\n"
    " * fi_handler_ack_crash - acknowledge and terminate the process at once, like fi_handler_random_exit but\n"
    " *   deterministically; fault_injection_action_prefer_abort_to_exit selects abort () or _exit ().\n"
    " *\n"
    " * return: NO_ERROR when the site does not fire (it never returns when it fires)\n"
    " */\n"
    "static int\n"
    "fi_handler_ack_crash (THREAD_ENTRY * thread_p, void *arg, const char *caller_file, const int caller_line)\n"
    "{\n"
    "  if (fi_site_fire_and_acknowledge (arg, caller_file, caller_line))\n"
    "    {\n"
    "      if (prm_get_bool_value (PRM_ID_FAULT_INJECTION_ACTION_PREFER_ABORT_TO_EXIT))\n"
    "\t{\n"
    "\t  abort ();\n"
    "\t}\n"
    "      else\n"
    "\t{\n"
    "\t  _exit (0);\n"
    "\t}\n"
    "    }\n"
    "\n"
    "  return NO_ERROR;\n"
    "}\n"
    "#endif\n")

# --------------------------------------------------------------------------------------------------
# 0001 (continued): the fire-at-occurrence system parameter
# --------------------------------------------------------------------------------------------------
rep("src/base/system_parameter.h",
    "  PRM_ID_PLAN_CACHE_BIND_SENSITIVITY,\n"
    "\n"
    "  /* change PRM_LAST_ID when adding new system parameters */\n"
    "  PRM_LAST_ID = PRM_ID_PLAN_CACHE_BIND_SENSITIVITY\n",
    "  PRM_ID_PLAN_CACHE_BIND_SENSITIVITY,\n"
    "\n"
    "  PRM_ID_FAULT_INJECTION_FIRE_AT_OCCURRENCE,\n"
    "\n"
    "  /* change PRM_LAST_ID when adding new system parameters */\n"
    "  PRM_LAST_ID = PRM_ID_FAULT_INJECTION_FIRE_AT_OCCURRENCE\n")

rep("src/base/system_parameter.c",
    "#define PRM_NAME_FAULT_INJECTION_ACTION_PREFER_ABORT_TO_EXIT \"fault_injection_action_prefer_abort_to_exit\"\n",
    "#define PRM_NAME_FAULT_INJECTION_ACTION_PREFER_ABORT_TO_EXIT \"fault_injection_action_prefer_abort_to_exit\"\n"
    "#define PRM_NAME_FAULT_INJECTION_FIRE_AT_OCCURRENCE \"fault_injection_fire_at_occurrence\"\n")

rep("src/base/system_parameter.c",
    "  {PRM_ID_PLAN_CACHE_BIND_SENSITIVITY,\n"
    "   PRM_NAME_PLAN_CACHE_BIND_SENSITIVITY,\n"
    "   (PRM_FOR_CLIENT | PRM_USER_CHANGE),\n"
    "   PRM_BOOLEAN,\n"
    "   PRM_CLEAR_DYNAMIC_FLAG,\n"
    "   {false, {.b = false}},\n"
    "   {false, {.b = false}},\n"
    "   NULL_SYSPRM_PARAM_VALUE,\n"
    "   NULL_SYSPRM_PARAM_VALUE,\n"
    "   (char *) NULL,\n"
    "   (DUP_PRM_FUNC) NULL,\n"
    "   (DUP_PRM_FUNC) NULL},\n"
    "};\n",
    "  {PRM_ID_PLAN_CACHE_BIND_SENSITIVITY,\n"
    "   PRM_NAME_PLAN_CACHE_BIND_SENSITIVITY,\n"
    "   (PRM_FOR_CLIENT | PRM_USER_CHANGE),\n"
    "   PRM_BOOLEAN,\n"
    "   PRM_CLEAR_DYNAMIC_FLAG,\n"
    "   {false, {.b = false}},\n"
    "   {false, {.b = false}},\n"
    "   NULL_SYSPRM_PARAM_VALUE,\n"
    "   NULL_SYSPRM_PARAM_VALUE,\n"
    "   (char *) NULL,\n"
    "   (DUP_PRM_FUNC) NULL,\n"
    "   (DUP_PRM_FUNC) NULL},\n"
    "  /* CBRD-26659 campaign: reach at which an armed deterministic fault-injection site fires (0 = every reach) */\n"
    "  {PRM_ID_FAULT_INJECTION_FIRE_AT_OCCURRENCE,\n"
    "   PRM_NAME_FAULT_INJECTION_FIRE_AT_OCCURRENCE,\n"
    "   (PRM_USER_CHANGE | PRM_FOR_SERVER | PRM_HIDDEN),\n"
    "   PRM_INTEGER,\n"
    "   PRM_CLEAR_DYNAMIC_FLAG,\n"
    "   {false, {.i = 0}},\n"
    "   {false, {.i = 0}},\n"
    "   NULL_SYSPRM_PARAM_VALUE,\n"
    "   {false, {.i = 0}},\n"
    "   (char *) NULL,\n"
    "   (DUP_PRM_FUNC) NULL,\n"
    "   (DUP_PRM_FUNC) NULL},\n"
    "};\n")

# --------------------------------------------------------------------------------------------------
# 0002: allocation-failure sites (group 1)
# --------------------------------------------------------------------------------------------------
rep("src/storage/oos_file.cpp",
    "#include \"error_manager.h\"\n#include \"file_manager.h\"\n",
    "#include \"error_manager.h\"\n#include \"fault_injection.h\"\n#include \"file_manager.h\"\n")

rep("src/storage/oos_file.cpp",
    "      throw std::bad_alloc ();\n"
    "    }\n"
    "#endif\n"
    "  thread_p->oos_oids.push_back (oid);\n",
    "      throw std::bad_alloc ();\n"
    "    }\n"
    "#endif\n"
    "#if !defined(NDEBUG)\n"
    "  {\n"
    "    /* CBRD-26659 campaign site (group: allocation during value construction) */\n"
    "    static FI_SITE_DESC fi_desc = { FI_TEST_OOS_PUBLISH_OID_BAD_ALLOC, \"oos_publish_oos_oid\",\n"
    "\t\t\t\t    \"OOS OID publication during insert (value construction)\",\n"
    "\t\t\t\t    \"throw std::bad_alloc\", 0, 0 };\n"
    "    if (FI_TEST_ARG (thread_p, FI_TEST_OOS_PUBLISH_OID_BAD_ALLOC, &fi_desc, 0) != NO_ERROR)\n"
    "      {\n"
    "\tthrow std::bad_alloc ();\n"
    "      }\n"
    "  }\n"
    "#endif\n"
    "  thread_p->oos_oids.push_back (oid);\n")

rep("src/storage/oos_file.cpp",
    "\t  try\n"
    "\t    {\n"
    "\t      touched_vpids->push_back (vpid);\n"
    "\t    }\n",
    "\t  try\n"
    "\t    {\n"
    "#if !defined(NDEBUG)\n"
    "\t      /* CBRD-26659 campaign site (group: allocation during cleanup) */\n"
    "\t      static FI_SITE_DESC fi_desc = { FI_TEST_OOS_DELETE_HINT_BAD_ALLOC, \"oos_delete_chain\",\n"
    "\t\t\t\t\t      \"reclaim hint list growth while deleting an OOS value chain (cleanup)\",\n"
    "\t\t\t\t\t      \"throw std::bad_alloc\", 0, 0 };\n"
    "\t      if (FI_TEST_ARG (thread_p, FI_TEST_OOS_DELETE_HINT_BAD_ALLOC, &fi_desc, 0) != NO_ERROR)\n"
    "\t\t{\n"
    "\t\t  throw std::bad_alloc ();\n"
    "\t\t}\n"
    "#endif\n"
    "\t      touched_vpids->push_back (vpid);\n"
    "\t    }\n")

rep("src/storage/heap_oos.cpp",
    "#include \"error_manager.h\"\n#include \"file_manager.h\"\n",
    "#include \"error_manager.h\"\n#include \"fault_injection.h\"\n#include \"file_manager.h\"\n")

rep("src/storage/heap_oos.cpp",
    "  try\n"
    "    {\n"
    "      oos_payloads.resize ((std::size_t) attr_info->num_values, empty_payload);\n",
    "  try\n"
    "    {\n"
    "#if !defined(NDEBUG)\n"
    "      /* CBRD-26659 campaign site (group: allocation during expansion / read) */\n"
    "      static FI_SITE_DESC fi_desc = { FI_TEST_OOS_READ_GROUPED_BAD_ALLOC, \"heap_oos_read_grouped_payloads\",\n"
    "\t\t\t\t      \"grouped Resolve prefetch buffers of an OOS-bearing record (read/expansion)\",\n"
    "\t\t\t\t      \"throw std::bad_alloc\", 0, 0 };\n"
    "      if (FI_TEST_ARG (thread_p, FI_TEST_OOS_READ_GROUPED_BAD_ALLOC, &fi_desc, 0) != NO_ERROR)\n"
    "\t{\n"
    "\t  throw std::bad_alloc ();\n"
    "\t}\n"
    "#endif\n"
    "      oos_payloads.resize ((std::size_t) attr_info->num_values, empty_payload);\n")

# --------------------------------------------------------------------------------------------------
# 0003: data and log I/O error sites (group 2)
# --------------------------------------------------------------------------------------------------
rep("src/storage/page_buffer.c",
    "#include \"error_manager.h\"\n#include \"file_io.h\"\n",
    "#include \"error_manager.h\"\n#include \"fault_injection.h\"\n#include \"file_io.h\"\n")

rep("src/storage/page_buffer.c",
    "      perfmon_inc_stat (thread_p, PSTAT_PB_NUM_IOWRITES);\n"
    "      if (fileio_write (thread_p, fileio_get_volume_descriptor (bufptr->vpid.volid), iopage, bufptr->vpid.pageid,\n"
    "\t\t\tIO_PAGESIZE, write_mode) == NULL)\n"
    "\t{\n"
    "\t  error = ER_FAILED;\n"
    "\t}\n",
    "      perfmon_inc_stat (thread_p, PSTAT_PB_NUM_IOWRITES);\n"
    "#if !defined(NDEBUG)\n"
    "      if (iopage->prv.ptype == PAGE_OOS)\n"
    "\t{\n"
    "\t  /* CBRD-26659 campaign site (group: data I/O error): the write fails as fileio_write would on an I/O error.\n"
    "\t   * Reached only on the direct write path, so the double write buffer must be off (double_write_buffer_size=0). */\n"
    "\t  static FI_SITE_DESC fi_desc = { FI_TEST_OOS_PAGE_WRITE_FAIL, \"pgbuf_bcb_flush_with_wal\",\n"
    "\t    \"disk write of a dirty PAGE_OOS page (data I/O)\", \"fail the write with ER_IO_WRITE\", 0, 0\n"
    "\t  };\n"
    "\t  if (FI_TEST_ARG (thread_p, FI_TEST_OOS_PAGE_WRITE_FAIL, &fi_desc, 0) != NO_ERROR)\n"
    "\t    {\n"
    "\t      er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_IO_WRITE, 2, bufptr->vpid.pageid,\n"
    "\t\t      fileio_get_volume_label (bufptr->vpid.volid, PEEK));\n"
    "\t      error = ER_FAILED;\n"
    "\t    }\n"
    "\t}\n"
    "#endif\n"
    "      if (error == NO_ERROR\n"
    "\t  && fileio_write (thread_p, fileio_get_volume_descriptor (bufptr->vpid.volid), iopage, bufptr->vpid.pageid,\n"
    "\t\t\t   IO_PAGESIZE, write_mode) == NULL)\n"
    "\t{\n"
    "\t  error = ER_FAILED;\n"
    "\t}\n")

rep("src/transaction/log_page_buffer.c",
    "#include \"file_io.h\"\n#include \"disk_manager.h\"\n",
    "#include \"file_io.h\"\n#include \"fault_injection.h\"\n#include \"disk_manager.h\"\n")

rep("src/transaction/log_page_buffer.c",
    "  char enc_pgbuf[IO_MAX_PAGE_SIZE + MAX_ALIGNMENT];\n"
    "  LOG_PAGE *enc_pgptr = NULL;\n"
    "\n"
    "  enc_pgptr = (LOG_PAGE *) PTR_ALIGN (enc_pgbuf, MAX_ALIGNMENT);\n",
    "  char enc_pgbuf[IO_MAX_PAGE_SIZE + MAX_ALIGNMENT];\n"
    "  LOG_PAGE *enc_pgptr = NULL;\n"
    "  bool fi_write_fails = false;\n"
    "\n"
    "  enc_pgptr = (LOG_PAGE *) PTR_ALIGN (enc_pgbuf, MAX_ALIGNMENT);\n")

rep("src/transaction/log_page_buffer.c",
    "  if (fileio_write (thread_p, log_Gl.append.vdes, log_pgptr, phy_pageid, LOG_PAGESIZE, write_mode) == NULL)\n"
    "    {\n"
    "      if (er_errid () == ER_IO_WRITE_OUT_OF_SPACE)\n"
    "\t{\n"
    "\t  nbytes = log_Gl.hdr.db_logpagesize;\n",
    "#if !defined(NDEBUG)\n"
    "  {\n"
    "    /* CBRD-26659 campaign site (group: log I/O error): the write fails as fileio_write would on an I/O error */\n"
    "    static FI_SITE_DESC fi_desc = { FI_TEST_OOS_LOG_WRITE_FAIL, \"logpb_write_page_to_disk\",\n"
    "      \"disk write of an active log page (log I/O)\", \"fail the write with ER_IO_WRITE (fatal for the server)\", 0, 0\n"
    "    };\n"
    "    if (FI_TEST_ARG (thread_p, FI_TEST_OOS_LOG_WRITE_FAIL, &fi_desc, 0) != NO_ERROR)\n"
    "      {\n"
    "\ter_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_IO_WRITE, 2, phy_pageid, log_Name_active);\n"
    "\tfi_write_fails = true;\n"
    "      }\n"
    "  }\n"
    "#endif\n"
    "  if (fi_write_fails\n"
    "      || fileio_write (thread_p, log_Gl.append.vdes, log_pgptr, phy_pageid, LOG_PAGESIZE, write_mode) == NULL)\n"
    "    {\n"
    "      if (er_errid () == ER_IO_WRITE_OUT_OF_SPACE)\n"
    "\t{\n"
    "\t  nbytes = log_Gl.hdr.db_logpagesize;\n")

# --------------------------------------------------------------------------------------------------
# 0004: interruption sites (group 3)
# --------------------------------------------------------------------------------------------------
rep("src/storage/oos_file.cpp",
    "\t      er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);\n"
    "\t      return ER_GENERIC_ERROR;\n"
    "\t    }\n"
    "#endif\n"
    "\n"
    "\t  if (requests[pos].src.size () > (std::size_t) max_chunk_size)\n",
    "\t      er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);\n"
    "\t      return ER_GENERIC_ERROR;\n"
    "\t    }\n"
    "#endif\n"
    "#if !defined(NDEBUG)\n"
    "\t  {\n"
    "\t    /* CBRD-26659 campaign site (group: interruption between chunk operations). Reached once per loop\n"
    "\t     * iteration, so the k-th reach fails after k - 1 iterations have published their values. */\n"
    "\t    static FI_SITE_DESC fi_desc = { FI_TEST_OOS_INSERT_MANY_FAIL, \"oos_insert_many\",\n"
    "\t\t\t\t\t    \"next chunk insert of oos_insert_many, after the preceding publications\",\n"
    "\t\t\t\t\t    \"fail with ER_GENERIC_ERROR\", 0, 0 };\n"
    "\t    if (FI_TEST_ARG (thread_p, FI_TEST_OOS_INSERT_MANY_FAIL, &fi_desc, 0) != NO_ERROR)\n"
    "\t      {\n"
    "\t\ter_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);\n"
    "\t\treturn ER_GENERIC_ERROR;\n"
    "\t      }\n"
    "\t  }\n"
    "#endif\n"
    "\n"
    "\t  if (requests[pos].src.size () > (std::size_t) max_chunk_size)\n")

rep("src/storage/oos_file.cpp",
    "\t  return error_code;\n"
    "\t}\n"
    "\n"
    "      if (track_repl && i == required_page_nums - 1)\n",
    "\t  return error_code;\n"
    "\t}\n"
    "\n"
    "#if !defined(NDEBUG)\n"
    "      {\n"
    "\t/* CBRD-26659 campaign site (group: interruption between chunk operations). Chunks are inserted tail\n"
    "\t * first, so the k-th reach crashes after k chunks of the chain exist and before the next one. */\n"
    "\tstatic FI_SITE_DESC fi_desc = { FI_TEST_OOS_CRASH_BETWEEN_CHUNKS, \"oos_insert_across_pages\",\n"
    "\t\t\t\t\t\"between two chunk inserts of one multi-chunk OOS value chain\",\n"
    "\t\t\t\t\t\"crash (_exit or abort)\", 0, 0 };\n"
    "\t(void) FI_TEST_ARG (thread_p, FI_TEST_OOS_CRASH_BETWEEN_CHUNKS, &fi_desc, 0);\n"
    "      }\n"
    "#endif\n"
    "\n"
    "      if (track_repl && i == required_page_nums - 1)\n")

rep("src/storage/heap_file.c",
    "#include \"heap_oos.hpp\"\n",
    "#include \"heap_oos.hpp\"\n#include \"fault_injection.h\"\n")

rep("src/storage/heap_file.c",
    "\t\t\t\t\t cubbase::span < oos_insert_request > (requests.data (), requests.size ()))\n"
    "      != S_SUCCESS)\n"
    "    {\n"
    "      goto cleanup;\n"
    "    }\n"
    "\n"
    "  scan_code = S_SUCCESS;\n",
    "\t\t\t\t\t cubbase::span < oos_insert_request > (requests.data (), requests.size ()))\n"
    "      != S_SUCCESS)\n"
    "    {\n"
    "      goto cleanup;\n"
    "    }\n"
    "\n"
    "#if !defined(NDEBUG)\n"
    "  {\n"
    "    /* CBRD-26659 campaign site (group: interruption before heap publication): every OOS chunk of the record is\n"
    "     * inserted and published, the heap record itself is not inserted yet. */\n"
    "    static FI_SITE_DESC fi_desc = { FI_TEST_OOS_CRASH_BEFORE_HEAP_PUBLICATION, \"heap_attrinfo_insert_to_oos\",\n"
    "\t\t\t\t    \"after all OOS chunks of a record are inserted and published, before the heap insert\",\n"
    "\t\t\t\t    \"crash (_exit or abort)\", 0, 0 };\n"
    "    (void) FI_TEST_ARG (thread_p, FI_TEST_OOS_CRASH_BEFORE_HEAP_PUBLICATION, &fi_desc, 0);\n"
    "  }\n"
    "#endif\n"
    "\n"
    "  scan_code = S_SUCCESS;\n")

# --------------------------------------------------------------------------------------------------
# 0005: rollback, vacuum, reclamation and recovery sites (group 4)
# --------------------------------------------------------------------------------------------------
rep("src/storage/oos_file.cpp",
    "oos_rv_redo_delete (THREAD_ENTRY *thread_p, LOG_RCV *rcv)\n"
    "{\n"
    "  INT16 slotid;\n"
    "\n"
    "  slotid = rcv->offset;\n",
    "oos_rv_redo_delete (THREAD_ENTRY *thread_p, LOG_RCV *rcv)\n"
    "{\n"
    "  INT16 slotid;\n"
    "\n"
    "#if !defined(NDEBUG)\n"
    "  if (LOG_ISRESTARTED ())\n"
    "    {\n"
    "      /* CBRD-26659 campaign site (group: failure during rollback). At run time this function is the undo of\n"
    "       * RVOOS_INSERT, so it runs when a transaction that inserted OOS chunks rolls back. */\n"
    "      static FI_SITE_DESC fi_desc = { FI_TEST_OOS_RV_UNDO_INSERT_FAIL, \"oos_rv_redo_delete\",\n"
    "\t\t\t\t      \"undo of RVOOS_INSERT during a transaction rollback\",\n"
    "\t\t\t\t      \"fail with ER_GENERIC_ERROR\", 0, 0 };\n"
    "      if (FI_TEST_ARG (thread_p, FI_TEST_OOS_RV_UNDO_INSERT_FAIL, &fi_desc, 0) != NO_ERROR)\n"
    "\t{\n"
    "\t  er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);\n"
    "\t  return ER_GENERIC_ERROR;\n"
    "\t}\n"
    "    }\n"
    "#endif\n"
    "\n"
    "  slotid = rcv->offset;\n")

rep("src/storage/oos_file.cpp",
    "oos_rv_redo_insert (THREAD_ENTRY *thread_p, LOG_RCV *rcv)\n"
    "{\n"
    "  INT16 slotid;\n"
    "  RECDES recdes;\n"
    "  int sp_success;\n"
    "\n"
    "  slotid = rcv->offset;\n",
    "oos_rv_redo_insert (THREAD_ENTRY *thread_p, LOG_RCV *rcv)\n"
    "{\n"
    "  INT16 slotid;\n"
    "  RECDES recdes;\n"
    "  int sp_success;\n"
    "\n"
    "#if !defined(NDEBUG)\n"
    "  if (!LOG_ISRESTARTED ())\n"
    "    {\n"
    "      /* CBRD-26659 campaign site (group: failure during recovery). During restart recovery this function is the\n"
    "       * redo of RVOOS_INSERT (and the undo of RVOOS_DELETE); a failure here is fatal for the restart. */\n"
    "      static FI_SITE_DESC fi_desc = { FI_TEST_OOS_RV_REDO_INSERT_FAIL, \"oos_rv_redo_insert\",\n"
    "\t\t\t\t      \"redo of RVOOS_INSERT (or undo of RVOOS_DELETE) during restart recovery\",\n"
    "\t\t\t\t      \"fail with ER_GENERIC_ERROR\", 0, 0 };\n"
    "      if (FI_TEST_ARG (thread_p, FI_TEST_OOS_RV_REDO_INSERT_FAIL, &fi_desc, 0) != NO_ERROR)\n"
    "\t{\n"
    "\t  er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);\n"
    "\t  return ER_GENERIC_ERROR;\n"
    "\t}\n"
    "    }\n"
    "#endif\n"
    "\n"
    "  slotid = rcv->offset;\n")

rep("src/storage/oos_file.cpp",
    "      page_out = NULL;\n"
    "      return NO_ERROR;\n"
    "    }\n"
    "#endif\n"
    "\n"
    "  page_out = pgbuf_fix (thread_p, &vpid, OLD_PAGE_MAYBE_DEALLOCATED, latch_mode, PGBUF_CONDITIONAL_LATCH);\n",
    "      page_out = NULL;\n"
    "      return NO_ERROR;\n"
    "    }\n"
    "#endif\n"
    "#if !defined(NDEBUG)\n"
    "  if (latch_mode == PGBUF_LATCH_WRITE)\n"
    "    {\n"
    "      /* CBRD-26659 campaign site (group: failure during reclamation) */\n"
    "      static FI_SITE_DESC fi_desc = { FI_TEST_OOS_RECLAIM_WRITE_FIX_SKIP, \"oos_reclaim_fix_candidate\",\n"
    "\t\t\t\t      \"write fix of an empty-page reclaim candidate\",\n"
    "\t\t\t\t      \"skip the candidate (page_out = NULL, NO_ERROR)\", 0, 0 };\n"
    "      if (FI_TEST_ARG (thread_p, FI_TEST_OOS_RECLAIM_WRITE_FIX_SKIP, &fi_desc, 0) != NO_ERROR)\n"
    "\t{\n"
    "\t  page_out = NULL;\n"
    "\t  return NO_ERROR;\n"
    "\t}\n"
    "    }\n"
    "#endif\n"
    "\n"
    "  page_out = pgbuf_fix (thread_p, &vpid, OLD_PAGE_MAYBE_DEALLOCATED, latch_mode, PGBUF_CONDITIONAL_LATCH);\n")

rep("src/query/vacuum_oos.cpp",
    "#include \"error_manager.h\"\n#include \"file_manager.h\"\n",
    "#include \"error_manager.h\"\n#include \"fault_injection.h\"\n#include \"file_manager.h\"\n")

rep("src/query/vacuum_oos.cpp",
    "      if (!exists)\n"
    "\t{\n"
    "\t  continue;\n"
    "\t}\n"
    "      error_code = oos_delete (thread_p, *oos_vfid, oid, &touched_pages);\n",
    "      if (!exists)\n"
    "\t{\n"
    "\t  continue;\n"
    "\t}\n"
    "#if !defined(NDEBUG)\n"
    "      {\n"
    "\t/* CBRD-26659 campaign site (group: failure during vacuum) */\n"
    "\tstatic FI_SITE_DESC fi_desc = { FI_TEST_OOS_VACUUM_DELETE_FAIL, \"vacuum_forward_walk_oos_delete_atomic\",\n"
    "\t\t\t\t\t\"vacuum forward-walk delete of an old row version's OOS value chain\",\n"
    "\t\t\t\t\t\"fail with ER_GENERIC_ERROR (the forward-walk sysop is aborted)\", 0, 0 };\n"
    "\tif (FI_TEST_ARG (thread_p, FI_TEST_OOS_VACUUM_DELETE_FAIL, &fi_desc, 0) != NO_ERROR)\n"
    "\t  {\n"
    "\t    er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);\n"
    "\t    error_code = ER_GENERIC_ERROR;\n"
    "\t    break;\n"
    "\t  }\n"
    "      }\n"
    "#endif\n"
    "      error_code = oos_delete (thread_p, *oos_vfid, oid, &touched_pages);\n")


def main():
    contents = {}
    problems = []
    for path, old, new in edits:
        if path not in contents:
            with open(path, encoding="utf-8") as f:
                contents[path] = f.read()
        n = contents[path].count(old)
        if n != 1:
            problems.append(f"{path}: anchor occurs {n} times:\n{old[:200]!r}")
            continue
        contents[path] = contents[path].replace(old, new, 1)
    if problems:
        print("NOT APPLIED. Problems:\n" + "\n".join(problems))
        sys.exit(1)
    for path, text in contents.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("edited", path)
    print("applied", len(edits), "edits to", len(contents), "files")


if __name__ == "__main__":
    main()
