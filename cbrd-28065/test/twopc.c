/*
 * Drive one step of the CBRD-28065 2PC attach scenario through the CUBRID C API.
 *
 *   twopc prepare DB         start a 2PC transaction, UPDATE r SET v = 42 WHERE id = 7, prepare it,
 *                            print "gtrid N", then stay connected until killed
 *   twopc attach-commit DB N attach to prepared gtrid N and commit it, print "committed N"
 *   twopc list DB            print "prepared N" for each prepared transaction the server knows
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "dbi.h"

static int
fail (const char *what)
{
  fprintf (stderr, "%s failed: %s\n", what, db_error_string (3));
  return 1;
}

static int
connect_db (const char *db)
{
  if (db_login ("dba", "") != NO_ERROR || db_restart ("twopc", 0, db) != NO_ERROR)
    {
      return fail ("connect");
    }
  return 0;
}

int
main (int argc, char **argv)
{
  DB_QUERY_RESULT *result;
  DB_QUERY_ERROR query_error;
  int gtrid, gtrids[64], n, i;

  if (argc < 3 || connect_db (argv[2]) != 0)
    {
      return 2;
    }

  if (strcmp (argv[1], "prepare") == 0)
    {
      gtrid = db_2pc_start_transaction ();
      if (gtrid < 0)
	{
	  return fail ("db_2pc_start_transaction");
	}
      if (db_execute ("update r set v = 42 where id = 7", &result, &query_error) < 0)
	{
	  return fail ("update");
	}
      db_query_end (result);
      if (db_2pc_prepare_transaction () != NO_ERROR)
	{
	  return fail ("db_2pc_prepare_transaction");
	}
      printf ("gtrid %d\n", gtrid);
      fflush (stdout);
      pause ();
      return 0;
    }

  if (strcmp (argv[1], "attach-commit") == 0 && argc == 4)
    {
      gtrid = atoi (argv[3]);
      if (db_2pc_attach_transaction (gtrid) != NO_ERROR)
	{
	  return fail ("db_2pc_attach_transaction");
	}
      if (db_commit_transaction () != NO_ERROR)
	{
	  return fail ("db_commit_transaction");
	}
      printf ("committed %d\n", gtrid);
      fflush (stdout);
      pause ();
      return 0;
    }

  if (strcmp (argv[1], "list") == 0)
    {
      n = db_2pc_prepared_transactions (gtrids, 64);
      if (n < 0)
	{
	  return fail ("db_2pc_prepared_transactions");
	}
      for (i = 0; i < n; i++)
	{
	  printf ("prepared %d\n", gtrids[i]);
	}
      printf ("count %d\n", n);
      db_commit_transaction ();
      db_shutdown ();
      return 0;
    }

  fprintf (stderr, "usage: twopc prepare DB | attach-commit DB GTRID | list DB\n");
  return 2;
}
