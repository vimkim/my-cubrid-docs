#!/usr/bin/env bash

set -euo pipefail

# CBRD-26067 regression demonstration:
#   FORCE_OUTLINE keeps values whose serialized size is <= 16 bytes inline,
#   but sends larger values to OOS even when the heap record itself is small.

for command_name in cubrid csql; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} is not available in PATH." >&2
    exit 1
  fi
done

if [[ -z "${CUBRID_DATABASES:-}" ]]; then
  echo "ERROR: CUBRID_DATABASES is not set. Source the CUBRID environment first." >&2
  exit 1
fi

# CUBRID database/log prefixes must be shorter than 17 characters.
DB_NAME="c26${BASHPID}"
DB_DIR=$(mktemp -d "${TMPDIR:-/tmp}/c26.XXXXXX")
DB_CREATED=0

cleanup()
{
  set +e
  if [[ "${DB_CREATED}" -eq 1 ]]; then
    cubrid deletedb "${DB_NAME}" >/dev/null 2>&1
  fi
  rmdir "${DB_DIR}/lob" >/dev/null 2>&1 || true
  rmdir "${DB_DIR}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

mkdir -p "${DB_DIR}/lob"
cubrid createdb --db-volume-size=20M --log-volume-size=20M \
  "${DB_NAME}" en_US.utf8 -F "${DB_DIR}" >/dev/null
DB_CREATED=1

csql -S -u dba -c "
CREATE TABLE force_outline_16 (
  id INTEGER PRIMARY KEY,
  payload BIT VARYING STORAGE FORCE_OUTLINE
);
CREATE TABLE force_outline_20 (
  id INTEGER PRIMARY KEY,
  payload BIT VARYING STORAGE FORCE_OUTLINE
);

-- Packed VARBIT sizes:
--   15 data bytes + 1-byte length prefix, aligned to 4 bytes = 16 bytes
--   16 data bytes + 1-byte length prefix, aligned to 4 bytes = 20 bytes
INSERT INTO force_outline_16 VALUES (1, REPEAT(X'AA', 15));
INSERT INTO force_outline_20 VALUES (1, REPEAT(X'BB', 16));
COMMIT;
" "${DB_NAME}" >/dev/null

query_one()
{
  csql -S -u dba -q -N --delimiter='^' -c "$1" "${DB_NAME}" \
    | sed '/^[[:space:]]*$/d'
}

assert_equal()
{
  local actual=$1
  local expected=$2
  local description=$3

  if [[ "${actual}" != "${expected}" ]]; then
    echo "FAIL: ${description}: expected ${expected}, got ${actual}" >&2
    exit 1
  fi
}

size_16=$(query_one "SELECT DISK_SIZE(payload) FROM force_outline_16;")
size_20=$(query_one "SELECT DISK_SIZE(payload) FROM force_outline_20;")

oos_16=$(query_one "SHOW HEAP OOS OF force_outline_16;")
oos_20=$(query_one "SHOW HEAP OOS OF force_outline_20;")

IFS='^' read -r _ _ _ _ _ has_oos_16 _ _ _ _ oos_recs_16 _ _ _ <<< "${oos_16}"
IFS='^' read -r _ _ _ _ _ has_oos_20 _ _ _ _ oos_recs_20 _ _ _ <<< "${oos_20}"

assert_equal "${size_16}" "16" "serialized size of the boundary value"
assert_equal "${has_oos_16}" "0" "16-byte value must not create an OOS file"
assert_equal "${oos_recs_16}" "0" "16-byte value must remain inline"

assert_equal "${size_20}" "20" "serialized size above the boundary"
assert_equal "${has_oos_20}" "1" "20-byte value must create an OOS file"
assert_equal "${oos_recs_20}" "1" "20-byte value must be stored in OOS"

echo "PASS: FORCE_OUTLINE respects the 16-byte inline boundary"
echo "  serialized 16 bytes -> Has_oos_file=${has_oos_16}, Oos_num_recs=${oos_recs_16}"
echo "  serialized 20 bytes -> Has_oos_file=${has_oos_20}, Oos_num_recs=${oos_recs_20}"
