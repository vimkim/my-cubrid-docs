#!/bin/bash
# Generate per-connection INSERT workload files (autocommit per statement).
set -eu
DIR="$(dirname "$0")"
NCLIENTS="${1:-8}"
NROWS="${2:-500}"

cat > "$DIR/setup_multi.sql" <<'EOF'
drop table if exists bt_multi;
create table bt_multi (id int, src int, payload varchar(200));
EOF

for c in $(seq 1 "$NCLIENTS"); do
  f="$DIR/worker_$c.sql"
  : > "$f"
  for i in $(seq 1 "$NROWS"); do
    printf "insert into bt_multi values (%d, %d, '%s');\n" "$i" "$c" \
      "payload-client$c-row$i-0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz" >> "$f"
  done
done
echo "generated $NCLIENTS workers x $NROWS rows"
