#!/bin/bash
set -eu

db_name="sxaio_codex"
backup_dir="/tmp/sx-aio-report-codex-backup"
database_list="${CUBRID_DATABASES:?}/databases.txt"

if grep -q "^${db_name}[[:space:]]" "$database_list"; then
  echo "database already exists: $db_name" >&2
  exit 1
fi

if test -e "$backup_dir"; then
  echo "backup directory already exists: $backup_dir" >&2
  exit 1
fi

if pgrep -f "statdump -i 60 -o watch-statdump.out $db_name" >/dev/null 2>&1; then
  echo "report-owned watcher already exists" >&2
  exit 1
fi

echo "database_absent=1"
echo "backup_dir_absent=1"
echo "watcher_absent=1"
