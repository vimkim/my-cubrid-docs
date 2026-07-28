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

# Optional controls used by the persistent Podman runner:
#   CUBRID_TEST_USE_SERVER=1     Run through cub_server instead of standalone csql.
#   CUBRID_TEST_KEEP_RUNNING=1   Leave the database (and server, when used) alive.
#   CUBRID_TEST_DB_NAME=name     Use a stable database name for later inspection.
#   CUBRID_TEST_DB_DIR=path      Put database volumes in a known directory.
CUBRID_TEST_USE_SERVER=${CUBRID_TEST_USE_SERVER:-${CUBRID_PODMAN_USE_SERVER:-0}}
CUBRID_TEST_KEEP_RUNNING=${CUBRID_TEST_KEEP_RUNNING:-${CUBRID_PODMAN_KEEP_ALIVE:-0}}

for boolean_name in CUBRID_TEST_USE_SERVER CUBRID_TEST_KEEP_RUNNING; do
  if [[ "${!boolean_name}" != "0" && "${!boolean_name}" != "1" ]]; then
    echo "ERROR: ${boolean_name} must be 0 or 1." >&2
    exit 1
  fi
done

# CUBRID database/log prefixes must be shorter than 17 characters.
DB_NAME=${CUBRID_TEST_DB_NAME:-${CUBRID_PODMAN_DB_NAME:-"c26${BASHPID}"}}
if [[ ${#DB_NAME} -ge 17 ]]; then
  echo "ERROR: database name must be shorter than 17 characters: ${DB_NAME}" >&2
  exit 1
fi

DB_DIR_OVERRIDE=${CUBRID_TEST_DB_DIR:-${CUBRID_PODMAN_DB_DIR:-}}
if [[ -n "${DB_DIR_OVERRIDE}" ]]; then
  DB_DIR=${DB_DIR_OVERRIDE}
  mkdir -p "${DB_DIR}"
else
  DB_DIR=$(mktemp -d "${TMPDIR:-/tmp}/c26.XXXXXX")
fi

DB_CREATED=0
SERVER_STARTED=0

cleanup()
{
  set +e
  if [[ "${CUBRID_TEST_KEEP_RUNNING}" -eq 1 ]]; then
    if [[ "${DB_CREATED}" -eq 1 ]]; then
      echo "INFO: preserved database ${DB_NAME} at ${DB_DIR} for inspection"
      if [[ "${SERVER_STARTED}" -eq 1 ]]; then
        echo "INFO: cub_server ${DB_NAME} remains running"
      fi
    else
      echo "INFO: database creation did not complete; preserved ${DB_DIR} for inspection"
    fi
    return
  fi

  if [[ "${SERVER_STARTED}" -eq 1 ]]; then
    cubrid server stop "${DB_NAME}" >/dev/null 2>&1
  fi
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

CSQL_MODE=(-S)
if [[ "${CUBRID_TEST_USE_SERVER}" -eq 1 ]]; then
  cubrid server start "${DB_NAME}" >/dev/null
  SERVER_STARTED=1
  CSQL_MODE=()
fi

csql "${CSQL_MODE[@]}" -u dba -c "
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
  csql "${CSQL_MODE[@]}" -u dba -q -N --delimiter='^' -c "$1" "${DB_NAME}" \
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
