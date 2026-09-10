// PR7600 interactive timing harness; diagnostic only, not a shipped regression test.
#include <chrono>
#include <ctime>
#include <cstdlib>
#include <string>
#include <vector>
#include "test_oos_sql_common.hpp"
int bridge_oos_get_max_chunk_size_within_page ();

extern "C" __attribute__((noinline)) void pr7600_measure_begin () { asm volatile ("" ::: "memory"); }
extern "C" __attribute__((noinline)) void pr7600_measure_end () { asm volatile ("" ::: "memory"); }

static double cpu_seconds ()
{
  timespec value;
  clock_gettime (CLOCK_PROCESS_CPUTIME_ID, &value);
  return value.tv_sec + value.tv_nsec * 1e-9;
}

static void owner_count (const std::string &table, int expected)
{
  DB_QUERY_RESULT *result = nullptr;
  ASSERT_GE (exec_sql_with_result (("SHOW HEAP OOS OF " + table).c_str (), &result), 0);
  ASSERT_NE (result, nullptr);
  ASSERT_EQ (db_query_first_tuple (result), DB_CURSOR_SUCCESS);
  DB_VALUE value;
  db_make_null (&value);
  ASSERT_EQ (db_query_get_tuple_value (result, 10, &value), NO_ERROR);
  EXPECT_EQ (db_value_type (&value) == DB_TYPE_BIGINT ? db_get_bigint (&value) : db_get_int (&value), expected);
  db_value_clear (&value);
  db_query_end (result);
}

TEST (Pr7600Measure, Matrix)
{
  struct workload { const char *name; int bytes; bool force; bool multiple; int update; bool partition; bool string_key; };
  const workload cases[] = {
    {"large", 64000, false, false, 0, true, false},
    {"multiple", 32000, false, true, 0, true, false},
    {"small_forced", 64, true, false, 0, true, false},
    {"small_inline", 4, false, false, 0, true, false},
    {"unchanged_update", 32000, false, false, 1, true, false},
    {"moving_update", 32000, false, false, 2, true, false},
    {"nonpartition_large", 64000, false, false, 0, false, false},
    {"nonpartition_small", 4, false, false, 0, false, false},
    {"string_expression", 32000, false, false, 0, true, true}
  };
  const int rows = getenv ("PR7600_ROWS") ? atoi (getenv ("PR7600_ROWS")) : 128;
  const int repetitions = getenv ("PR7600_REPETITIONS") ? atoi (getenv ("PR7600_REPETITIONS")) : 9;
  ASSERT_TRUE (getenv ("PR7600_WORKLOAD") != nullptr);
  ASSERT_TRUE (std::string (getenv ("PR7600_WORKLOAD")) == "small_inline"
               || std::string (getenv ("PR7600_WORKLOAD")) == "nonpartition_small");
  ASSERT_GT (rows, 0);
  ASSERT_GT (repetitions, 0);
  for (const auto &w : cases)
    {
      if (getenv ("PR7600_WORKLOAD") && std::string (getenv ("PR7600_WORKLOAD")) != w.name) continue;
      SCOPED_TRACE (w.name);
      std::string ddl = "CREATE TABLE t_measure (k INT)";
      if (w.partition)
        ddl += std::string (" PARTITION BY RANGE(") + (w.string_key ? "LENGTH(k)" : "k")
               + ") (PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)";
      ASSERT_GE (exec_sql (ddl.c_str ()), 0);
      std::string payload = "REPEAT(X'CC'," + std::to_string (w.bytes) + ")";
      std::string old_key = w.string_key ? "'x'" : "1";
      std::string new_key = w.string_key ? "'xxxxxxxxxxxx'" : "11";
      if (w.update)
        {
          for (int row = 0; row < rows; row++)
            {
              ASSERT_EQ (exec_sql (("INSERT INTO t_measure VALUES (" + std::to_string (row) + "," + old_key
                                   + ",REPEAT(X'AA'," + std::to_string (w.bytes) + "))").c_str ()), 1);
            }
        }
      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
      for (int rep = -2; rep < repetitions; rep++)
        {
          SCOPED_TRACE (rep);
          // Build SQL outside timing; SQL compile/execute and storage are inside timing.
          std::vector<std::string> statements;
          for (int row = 0; row < rows; row++)
            {
              statements.push_back ("INSERT INTO t_measure VALUES (11)");
            }
          // Handshake is outside the measured interval. Keep both paired processes alive
          // so the driver can interleave batches without repeated engine startup.
          if (getenv ("PR7600_STREAM"))
            {
              printf ("PR7600_READY\n");
              fflush (stdout);
              if (getchar () != 'g') break;
            }
          double cpu_start = cpu_seconds ();
          auto start = std::chrono::steady_clock::now ();
          pr7600_measure_begin ();
          for (const auto &sql : statements)
            {
              ASSERT_EQ (exec_sql (sql.c_str ()), 1);
            }
          pr7600_measure_end ();
          double elapsed = std::chrono::duration<double> (std::chrono::steady_clock::now () - start).count ();
          double cpu = cpu_seconds () - cpu_start;
          int actual = -1;
          std::string predicate = "k=11";
          ASSERT_EQ (fetch_single_int (("SELECT COUNT(*) FROM t_measure WHERE " + predicate).c_str (), &actual), NO_ERROR);
          ASSERT_EQ (actual, rows);
          // SHOW counts physical chunks, not logical value chains. These sizes are far from chunk boundaries;
          // the VARBIT disk length prefix fits within the conservative 16-byte allowance.
          int chunk = bridge_oos_get_max_chunk_size_within_page ();
          ASSERT_GT (chunk, 16);
          ASSERT_EQ ((w.bytes + chunk - 1) / chunk, (w.bytes + 16 + chunk - 1) / chunk);
          int oos = w.bytes > 4 ? rows * (w.multiple ? 2 : 1) * ((w.bytes + 16 + chunk - 1) / chunk) : 0;
          if (w.partition)
            {
              owner_count ("t_measure", 0);
              owner_count ("t_measure__p__p0", w.update == 1 ? oos : 0);
              owner_count ("t_measure__p__p1", w.update == 1 ? 0 : oos);
            }
          else owner_count ("t_measure", oos);
          ASSERT_FALSE (::testing::Test::HasFailure ());
          printf ("PR7600_SAMPLE {\"workload\":\"%s\",\"rep\":%d,\"rows\":%d,\"cpu_seconds\":%.9f,\"elapsed_seconds\":%.9f}\n",
                  w.name, rep, rows, cpu, elapsed);
          fflush (stdout);
          ASSERT_EQ (db_abort_transaction (), NO_ERROR);
          ASSERT_EQ (fetch_single_int ("SELECT COUNT(*) FROM t_measure", &actual), NO_ERROR);
          ASSERT_EQ (actual, w.update ? rows : 0);
          if (w.update)
            {
              ASSERT_EQ (fetch_single_int (("SELECT COUNT(*) FROM t_measure WHERE k=" + old_key
                         + " AND a=CAST(REPEAT(X'AA'," + std::to_string (w.bytes)
                         + ") AS BIT VARYING)").c_str (), &actual), NO_ERROR);
              ASSERT_EQ (actual, rows);
            }
          if (getenv ("PR7600_STREAM"))
            {
              printf ("PR7600_DONE\n");
              fflush (stdout);
            }
        }
      ASSERT_GE (exec_sql ("DROP TABLE t_measure"), 0);
      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
    }
}

int main (int argc, char **argv)
{
  ::testing::InitGoogleTest (&argc, argv);
  if (db_login ("DBA", NULL) != NO_ERROR) return EXIT_FAILURE;
  ::testing::AddGlobalTestEnvironment (new SqlServerEnv ());
  return RUN_ALL_TESTS ();
}
