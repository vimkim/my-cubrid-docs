/*
 *
 * Copyright 2016 CUBRID Corporation
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */

/*
 * test_oos_sql_show.cpp - SHOW HEAP OOS diagnostic SQL tests (CBRD-26972)
 */

#include <algorithm>
#include <string>

#include "partition_sr.h"
#include "locator_sr.h"
#include "heap_oos.hpp"
#include "log_impl.h"
#include "record_descriptor.hpp"
#include "test_oos_sql_common.hpp"

// Direct server interfaces in SA must use server allocation, just like network_interface_cl.c.
extern unsigned int db_on_server;
void bridge_heap_attrinfo_fail_after_oos_publication_reset_once ();
void bridge_heap_attrinfo_disarm_publication_reset_failure ();

namespace
{
  class scoped_sa_server
  {
    public:
      scoped_sa_server ()
      {
	db_on_server++;
      }
      ~scoped_sa_server ()
      {
	db_on_server--;
      }
  };

  enum show_heap_oos_column
  {
    COL_TABLE_NAME = 0,
    COL_CLASS_OID,
    COL_HEAP_VOLUME_ID,
    COL_HEAP_FILE_ID,
    COL_HEAP_HEADER_PAGE_ID,
    COL_HAS_OOS_FILE,
    COL_OOS_VOLUME_ID,
    COL_OOS_FILE_ID,
    COL_OOS_NUM_USER_PAGES,
    COL_OOS_PAGE_SIZE,
    COL_OOS_NUM_RECS,
    COL_OOS_RECS_SUMLEN,
    COL_OOS_PHYSICAL_BYTES,
    COL_OOS_UNUSED_BYTES
  };

  static int
  show_heap_oos_query (const char *sql, DB_QUERY_RESULT **result)
  {
    int rc = exec_sql_with_result (sql, result);
    if (rc < 0)
      {
	return rc;
      }
    if (*result == nullptr)
      {
	return ER_FAILED;
      }

    rc = db_query_first_tuple (*result);
    if (rc != DB_CURSOR_SUCCESS)
      {
	db_query_end (*result);
	*result = nullptr;
	return ER_FAILED;
      }

    return NO_ERROR;
  }

  static int
  get_int_column (DB_QUERY_RESULT *result, int column, int *out_val)
  {
    DB_VALUE val;
    int rc;

    db_make_null (&val);
    rc = db_query_get_tuple_value (result, column, &val);
    if (rc != NO_ERROR)
      {
	return rc;
      }

    DB_TYPE type = db_value_type (&val);
    if (type == DB_TYPE_INTEGER)
      {
	*out_val = db_get_int (&val);
      }
    else if (type == DB_TYPE_BIGINT)
      {
	*out_val = (int) db_get_bigint (&val);
      }
    else if (type == DB_TYPE_SHORT)
      {
	*out_val = (int) db_get_short (&val);
      }
    else
      {
	rc = ER_FAILED;
      }

    db_value_clear (&val);
    return rc;
  }

  static int
  get_bigint_column (DB_QUERY_RESULT *result, int column, DB_BIGINT *out_val)
  {
    DB_VALUE val;
    int rc;

    db_make_null (&val);
    rc = db_query_get_tuple_value (result, column, &val);
    if (rc != NO_ERROR)
      {
	return rc;
      }

    DB_TYPE type = db_value_type (&val);
    if (type == DB_TYPE_BIGINT)
      {
	*out_val = db_get_bigint (&val);
      }
    else if (type == DB_TYPE_INTEGER)
      {
	*out_val = (DB_BIGINT) db_get_int (&val);
      }
    else if (type == DB_TYPE_SHORT)
      {
	*out_val = (DB_BIGINT) db_get_short (&val);
      }
    else
      {
	rc = ER_FAILED;
      }

    db_value_clear (&val);
    return rc;
  }

  static int
  get_is_null_column (DB_QUERY_RESULT *result, int column, bool *out_is_null)
  {
    DB_VALUE val;
    int rc;

    db_make_null (&val);
    rc = db_query_get_tuple_value (result, column, &val);
    if (rc == NO_ERROR)
      {
	*out_is_null = DB_IS_NULL (&val);
      }

    db_value_clear (&val);
    return rc;
  }

  static int
  get_string_column (DB_QUERY_RESULT *result, int column, std::string *out_val)
  {
    DB_VALUE val;
    int rc;

    db_make_null (&val);
    rc = db_query_get_tuple_value (result, column, &val);
    if (rc == NO_ERROR)
      {
	const char *str = db_get_string (&val);
	if (str == nullptr)
	  {
	    rc = ER_FAILED;
	  }
	else
	  {
	    *out_val = str;
	  }
      }

    db_value_clear (&val);
    return rc;
  }

  static std::string
  unqualified_table_name (const std::string &table_name)
  {
    std::string::size_type separator = table_name.rfind ('.');
    return separator == std::string::npos ? table_name : table_name.substr (separator + 1);
  }

  static void
  expect_sql_count (const char *sql, int expected)
  {
    SCOPED_TRACE (sql);
    int count = -1;
    ASSERT_EQ (fetch_single_int (sql, &count), NO_ERROR);
    EXPECT_EQ (count, expected);
  }

  static void
  expect_oos_records (const char *table, int has_file, int expected_records)
  {
    SCOPED_TRACE (table);
    std::string sql = std::string ("SHOW HEAP OOS OF ") + table;
    DB_QUERY_RESULT *result = nullptr;
    ASSERT_EQ (show_heap_oos_query (sql.c_str (), &result), NO_ERROR);
    int actual_has_file = -1;
    int actual_records = -1;
    EXPECT_EQ (get_int_column (result, COL_HAS_OOS_FILE, &actual_has_file), NO_ERROR);
    EXPECT_EQ (get_int_column (result, COL_OOS_NUM_RECS, &actual_records), NO_ERROR);
    EXPECT_EQ (actual_has_file, has_file);
    EXPECT_EQ (actual_records, expected_records);
    EXPECT_EQ (db_query_next_tuple (result), DB_CURSOR_END);
    db_query_end (result);
  }
}

class OosSqlShow : public ::testing::Test
{
  protected:
    void SetUp () override
    {
      exec_sql ("DROP TABLE IF EXISTS t_oos_show_no");
      exec_sql ("DROP TABLE IF EXISTS t_oos_show_yes");
      exec_sql ("DROP TABLE IF EXISTS t_oos_show_part");
      db_commit_transaction ();
    }

    void TearDown () override
    {
      exec_sql ("DROP TABLE IF EXISTS t_oos_show_no");
      exec_sql ("DROP TABLE IF EXISTS t_oos_show_yes");
      exec_sql ("DROP TABLE IF EXISTS t_oos_show_part");
      db_commit_transaction ();
    }
};

TEST_F (OosSqlShow, PartitionPreparationFailuresRollBackAndAllowNextWrite)
{
  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT, "
                      "a BIT VARYING STORAGE FORCE_OUTLINE, b BIT VARYING STORAGE FORCE_OUTLINE) "
                      "PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), "
                      "PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
  ASSERT_GE (exec_sql ("INSERT INTO t_oos_show_part VALUES "
                      "(1, REPEAT(X'AA',64), REPEAT(X'BB',64)), "
                      "(11, REPEAT(X'AA',64), REPEAT(X'BB',64))"), 0);
  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);

  for (bool update : { false, true })
    {
      for (int failure = 0; failure < 4; failure++)
        {
          SCOPED_TRACE (failure);
          SCOPED_TRACE (update ? "moving UPDATE" : "INSERT");
          // A multi-chunk second value prevents both values publishing in one small-page batch.
          if (failure == 0)
            {
              oos_test_fail_insert_many_after_publications (1);
            }
          else if (failure == 1)
            {
              bridge_heap_attrinfo_fail_after_oos_publication_reset_once ();
            }
          else if (failure == 2)
            {
              heap_oos_test_fail_before_vfid_lookup_once ();
            }
          else
            {
              oos_test_throw_bad_alloc_on_next_oid_publication ();
            }
          int error = exec_sql (update
                               ? "UPDATE t_oos_show_part SET id=12, a=REPEAT(X'CC',64), "
                                 "b=REPEAT(X'DD',20000) WHERE id=1"
                               : "INSERT INTO t_oos_show_part VALUES (12, REPEAT(X'CC',64), REPEAT(X'DD',20000))");
          oos_test_disarm_insert_publication_failures ();
          bridge_heap_attrinfo_disarm_publication_reset_failure ();
          heap_oos_test_disarm_fail_before_vfid_lookup ();
          EXPECT_EQ (error, failure == 3 ? ER_OUT_OF_VIRTUAL_MEMORY : ER_GENERIC_ERROR);
          ASSERT_EQ (db_abort_transaction (), NO_ERROR);

          expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id IN (1,11) "
                            "AND a=CAST(REPEAT(X'AA',64) AS BIT VARYING) "
                            "AND b=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 2);
          expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id=12", 0);
          expect_oos_records ("t_oos_show_part", 0, 0);
          expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
          expect_oos_records ("t_oos_show_part__p__p1", 1, 2);

          ASSERT_GE (exec_sql ("INSERT INTO t_oos_show_part VALUES (12, REPEAT(X'CC',64), REPEAT(X'DD',64))"), 0);
          expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=12 "
                            "AND a=CAST(REPEAT(X'CC',64) AS BIT VARYING) "
                            "AND b=CAST(REPEAT(X'DD',64) AS BIT VARYING)", 1);
          expect_oos_records ("t_oos_show_part__p__p1", 1, 4);
          ASSERT_EQ (db_abort_transaction (), NO_ERROR);
          expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
        }
    }
}

TEST_F (OosSqlShow, PartitionLobPreparationAndIndexFailuresPreserveCommittedValues)
{
  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT PRIMARY KEY, "
                      "data_col BIT VARYING STORAGE FORCE_OUTLINE, text_lob CLOB, "
                      "binary_lob BLOB STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) "
                      "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
                      "(1,REPEAT(X'AA',64),CHAR_TO_CLOB('old text'),BIT_TO_BLOB(X'AABB')), "
                      "(11,REPEAT(X'AA',64),CHAR_TO_CLOB('old text'),BIT_TO_BLOB(X'AABB'))"), 2);
  ASSERT_EQ (db_commit_transaction (), NO_ERROR);

  for (int failure = 0; failure < 3; failure++)
    {
      SCOPED_TRACE (failure);
      if (failure == 0)
        {
          // Fail after OOS payload preparation, which copies the written BLOB locator.
          heap_oos_test_fail_before_vfid_lookup_once ();
        }
      int error = exec_sql (failure == 0
                           ? "UPDATE t_oos_show_part SET id=12, text_lob=CHAR_TO_CLOB('new text'), "
                             "binary_lob=BIT_TO_BLOB(X'CCDD') WHERE id=1"
                           : failure == 1
                           ? "UPDATE t_oos_show_part SET id=11, text_lob=CHAR_TO_CLOB('new text'), "
                             "binary_lob=BIT_TO_BLOB(X'CCDD') WHERE id=1"
                           : "UPDATE t_oos_show_part SET id=11 WHERE id=1");
      heap_oos_test_disarm_fail_before_vfid_lookup ();
      EXPECT_EQ (error, failure == 0 ? ER_GENERIC_ERROR : ER_BTREE_UNIQUE_FAILED);
      ASSERT_EQ (db_abort_transaction (), NO_ERROR);
      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id IN (1,11) "
                        "AND CLOB_TO_CHAR(text_lob)='old text' AND BLOB_TO_BIT(binary_lob)=X'AABB'", 2);
      expect_oos_records ("t_oos_show_part", 0, 0);
      expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
      expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=12, text_lob=CHAR_TO_CLOB('next text'), "
                          "binary_lob=BIT_TO_BLOB(X'EEFF') WHERE id=1"), 1);
      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=12 "
                        "AND CLOB_TO_CHAR(text_lob)='next text' AND BLOB_TO_BIT(binary_lob)=X'EEFF'", 1);
      expect_oos_records ("t_oos_show_part__p__p1", 1, 4);
      ASSERT_EQ (db_abort_transaction (), NO_ERROR);
    }
}

int
main (int argc, char **argv)
{
  ::testing::InitGoogleTest (&argc, argv);
  if (db_login ("DBA", NULL) != NO_ERROR)
    {
      fprintf (stderr, "db_login failed\n");
      return EXIT_FAILURE;
    }
  ::testing::AddGlobalTestEnvironment (new SqlServerEnv ());
  return RUN_ALL_TESTS ();
}
