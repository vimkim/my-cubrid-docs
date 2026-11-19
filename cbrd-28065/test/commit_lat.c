/*
 * Commit latency of an autocommit-style INSERT loop through the CUBRID C API.
 *
 *   commit_lat DB N CLIENT_ID
 *
 * Runs N transactions of one INSERT INTO lat VALUES (CLIENT_ID, i) followed by db_commit_transaction, and prints
 * one line per transaction: "<commit microseconds> <transaction microseconds>". Table lat must exist.
 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "dbi.h"

static long long
now_us (void)
{
  struct timespec ts;

  clock_gettime (CLOCK_MONOTONIC, &ts);
  return (long long) ts.tv_sec * 1000000 + ts.tv_nsec / 1000;
}

int
main (int argc, char **argv)
{
  DB_QUERY_RESULT *result;
  DB_QUERY_ERROR query_error;
  char sql[128];
  long long t0, t1, t2;
  int n, client, i;

  if (argc != 4)
    {
      fprintf (stderr, "usage: commit_lat DB N CLIENT_ID\n");
      return 2;
    }
  n = atoi (argv[2]);
  client = atoi (argv[3]);
  if (db_login ("dba", "") != NO_ERROR || db_restart ("commit_lat", 0, argv[1]) != NO_ERROR)
    {
      fprintf (stderr, "connect failed: %s\n", db_error_string (3));
      return 1;
    }

  for (i = 0; i < n; i++)
    {
      snprintf (sql, sizeof (sql), "insert into lat values (%d, %d)", client, i);
      t0 = now_us ();
      if (db_execute (sql, &result, &query_error) < 0)
	{
	  fprintf (stderr, "insert failed: %s\n", db_error_string (3));
	  return 1;
	}
      db_query_end (result);
      t1 = now_us ();
      if (db_commit_transaction () != NO_ERROR)
	{
	  fprintf (stderr, "commit failed: %s\n", db_error_string (3));
	  return 1;
	}
      t2 = now_us ();
      printf ("%lld %lld\n", t2 - t1, t2 - t0);
    }

  db_shutdown ();
  return 0;
}
