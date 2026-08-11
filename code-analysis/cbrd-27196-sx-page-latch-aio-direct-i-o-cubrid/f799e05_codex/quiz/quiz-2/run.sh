#!/bin/bash
set -eu

db_name="sxq2codex"
database_list="${CUBRID_DATABASES:?}/databases.txt"
created=0

cleanup ()
{
  if test "$created" -eq 1; then
    cubrid deletedb "$db_name" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT HUP INT TERM

if grep -q "^${db_name}[[:space:]]" "$database_list"; then
  echo "quiz-owned database name is already registered: $db_name" >&2
  exit 1
fi

cubrid createdb --db-volume-size=64M --log-volume-size=64M "$db_name" en_US.utf8
created=1
csql -S -u dba "$db_name" -i observe.sql
cubrid deletedb "$db_name"
created=0

if grep -q "^${db_name}[[:space:]]" "$database_list"; then
  echo "quiz cleanup failed: $db_name" >&2
  exit 1
fi

echo "quiz_cleanup_verified=1"
