#!/usr/bin/env bash
#
# test_prefer_inline_unloaddb.sh  (CBRD-26912)
#
# End-to-end check that the STORAGE PREFER_INLINE column option survives a
# `cubrid unloaddb` schema dump and a `cubrid loaddb` reload.
#
# It exercises the three sites that must carry the SM_ATTFLAG_OOS_PREFER_INLINE
# flag the same way the INVISIBLE option does:
#   - CREATE TABLE column option  -> unloaddb emit (emit_attribute_def)
#   - CREATE TABLE ... LIKE       -> classobj_copy_attribute_like
#   - ALTER TABLE ... MODIFY      -> build_attr_change_map GAINED path
#
# Prerequisite: a CUBRID install on PATH (e.g. a direnv-loaded .envrc) so that
# `cubrid`, `csql`, etc. resolve. The script uses its own throwaway
# CUBRID_DATABASES under a temp dir, so it does not touch your real databases.
#
# Exit status: 0 = PASS, non-zero = FAIL.

set -euo pipefail

command -v cubrid >/dev/null 2>&1 || { echo "FAIL: 'cubrid' not on PATH - source your CUBRID environment first"; exit 1; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/prefer_inline_unload.XXXXXX")"
export CUBRID_DATABASES="$WORK/databases"
mkdir -p "$CUBRID_DATABASES"
cd "$WORK"

SRC=prefer_inline_src
DST=prefer_inline_dst
PREFIX=dump
SCHEMA="$WORK/${PREFIX}_schema"

cleanup () {
  cubrid server stop "$SRC" >/dev/null 2>&1 || true
  cubrid server stop "$DST" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

fail () { echo "FAIL: $*"; exit 1; }

echo "## 1. create source database"
mkdir -p "$CUBRID_DATABASES/$SRC"
cubrid createdb --db-volume-size=20M --log-volume-size=20M "$SRC" en_US.utf8 -F "$CUBRID_DATABASES/$SRC" >/dev/null

echo "## 2. define STORAGE PREFER_INLINE three ways (CREATE / LIKE / ALTER MODIFY)"
csql -S "$SRC" >/dev/null <<'SQL'
CREATE TABLE prefer_inline_t (
  id   INT PRIMARY KEY,
  hot  VARCHAR(4096) STORAGE PREFER_INLINE,   -- prefer inline
  cold VARCHAR(4096)                          -- default (size-order OOS)
);
CREATE TABLE prefer_inline_like LIKE prefer_inline_t;
CREATE TABLE prefer_inline_alter (id INT PRIMARY KEY, c VARCHAR(4096));
ALTER TABLE prefer_inline_alter MODIFY c VARCHAR(4096) STORAGE PREFER_INLINE;
COMMIT;
SQL

echo "## 3. cubrid unloaddb (schema only, standalone)"
cubrid unloaddb -S -s -O "$WORK" --output-prefix "$PREFIX" "$SRC" >/dev/null
[ -f "$SCHEMA" ] || fail "unloaddb did not produce schema file: $SCHEMA"

echo "## 4. assert the option is present in the unloaddb schema dump"
echo "--- STORAGE PREFER_INLINE lines in ${PREFIX}_schema ---"
grep -n "STORAGE PREFER_INLINE" "$SCHEMA" || fail "no STORAGE PREFER_INLINE in unloaddb schema dump"
count=$(grep -c "STORAGE PREFER_INLINE" "$SCHEMA")
[ "$count" -ge 3 ] || fail "expected >= 3 occurrences (t.hot, like.hot, alter.c); got $count"
# negative: a default column must not carry the clause
grep -E "\[cold\][^,]*STORAGE PREFER_INLINE" "$SCHEMA" && fail "default column 'cold' wrongly got STORAGE PREFER_INLINE"
echo "ok: found $count STORAGE PREFER_INLINE column(s), none on the default column"

echo "## 5. reload the dumped schema into a fresh database"
mkdir -p "$CUBRID_DATABASES/$DST"
cubrid createdb --db-volume-size=20M --log-volume-size=20M "$DST" en_US.utf8 -F "$CUBRID_DATABASES/$DST" >/dev/null
cubrid loaddb -u dba -S -s "$SCHEMA" "$DST" >/dev/null

echo "## 6. confirm the option survived the round-trip (SHOW CREATE TABLE on reloaded db)"
for tbl in prefer_inline_t prefer_inline_like prefer_inline_alter; do
  ddl=$(csql -S -l -c "SHOW CREATE TABLE $tbl;" "$DST")
  echo "$ddl" | grep -q "STORAGE PREFER_INLINE" || fail "hint lost after reload on table $tbl"
done
echo "ok: STORAGE PREFER_INLINE present on all 3 reloaded tables"

echo
echo "PASS: STORAGE PREFER_INLINE survives cubrid unloaddb dump and cubrid loaddb reload"
