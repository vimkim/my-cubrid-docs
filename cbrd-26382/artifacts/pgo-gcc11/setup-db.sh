#!/usr/bin/env bash
# usage: setup-db.sh <preset>
# Creates a fresh benchmark database for one installed build variant.
set -euo pipefail
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=/dev/null
source "$script_dir/env.sh" "${1:?usage: setup-db.sh <preset>}"

db=pgobench
mkdir -p "$CUBRID_DATABASES/$db"

if cubrid server status 2>/dev/null | grep -q "$db"; then
  cubrid server stop "$db" || true
fi

if grep -q "^$db " "$CUBRID_DATABASES/databases.txt" 2>/dev/null; then
  cubrid deletedb "$db" || true
  mkdir -p "$CUBRID_DATABASES/$db"
fi

cd "$CUBRID_DATABASES/$db"
cubrid createdb --db-volume-size=128M --log-volume-size=128M "$db" en_US

# 49-row table reproduces the QA workload magnitude: 49^5 = 282,475,249,
# the same cartesian row count as the QA db_class query in CBRD-26382.
values=$(seq 1 49 | sed 's/.*/(&)/' | paste -sd, -)
csql -u dba -S "$db" -c "CREATE TABLE qa49 (a INT); INSERT INTO qa49 VALUES $values;"
csql -u dba -S "$db" -c "SELECT COUNT(*) FROM qa49" | grep -q " 49" || {
  echo "qa49 row count mismatch" >&2
  exit 1
}
echo "created $db with qa49(49 rows) under $CUBRID_DATABASES"
