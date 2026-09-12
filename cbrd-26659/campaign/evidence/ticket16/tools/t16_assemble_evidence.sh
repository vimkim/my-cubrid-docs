#!/bin/bash
# CBRD-26659 campaign ticket 16 -- copy the compact evidence into the docs repository and hash the bulky rest.
#
# Compact evidence (journals, acknowledgement lines, csql outputs, configurations, excerpts, scripts) goes to
# my-cubrid-docs/cbrd-26659/campaign/evidence/ticket16/. Bulky artifacts (full server error logs, cores,
# copied database images, build logs, databases) stay under ~/.cub/campaign/cbrd-26659/ticket16/ and are
# listed with sha256 in evidence/ticket16/SHA256SUMS-bulky.txt.
set -u
T16=/home/vimkim/.cub/campaign/cbrd-26659/ticket16
EV=/home/vimkim/gh/my-cubrid-docs/cbrd-26659/campaign/evidence/ticket16
mkdir -p "$EV/sites" "$EV/controls" "$EV/corruption" "$EV/bounded-fs" "$EV/tools" "$EV/identity"

excerpt () {   # excerpt <errlog> : acknowledgement lines with context plus the engine's reaction lines
  local f=$1
  echo "##### $(basename "$f") (excerpt; full file hashed in SHA256SUMS-bulky.txt)"
  grep -n -B2 -A3 "FAULT INJECTION ACK" "$f" 2>/dev/null
  echo "..... engine reaction lines:"
  grep -n -A1 -E "ERROR CODE = -14\b|LOG FATAL|MAYNEED|was not undone|bounded leak|dropping empty-page reclaim hints|Out of virtual memory|Internal system failure|Log recovery: (REDO|UNDO) Phase is started|Assertion .false. failed" "$f" 2>/dev/null | grep -v "^--$" | head -60
}

for site in a1 b1 c1 d1 e1 f1 g1 h1 i1 j1 k1 l1; do
  for mode in fault control; do
    src=$T16/sites/$site/$mode
    [ -d "$src" ] || continue
    if [ "$mode" = fault ]; then dst=$EV/sites/$site; else dst=$EV/controls/$site; fi
    rm -rf "$dst"; mkdir -p "$dst"
    cp "$src"/journal.txt "$src"/pids.txt "$src"/cubrid.conf* "$dst"/ 2>/dev/null
    cp "$src"/*.sql "$src"/csql-*.out "$src"/createdb.out "$src"/checkdb.out "$src"/server-status*.out "$src"/server-start*.out "$dst"/ 2>/dev/null
    [ -f "$src/acks.txt" ] && cp "$src/acks.txt" "$dst/acks.txt"
    if ls "$src"/server-err/*.err >/dev/null 2>&1; then
      for f in "$src"/server-err/*.err; do excerpt "$f"; done > "$dst/server-err-excerpt.txt"
    fi
  done
done
cp -r "$T16/sites/conf-arming-probe" "$EV/sites/" 2>/dev/null
cp "$T16/sites/run-all.log" "$EV/sites/run-all-first-pass.log"

# corruption procedure
C=$T16/corruption/out
cp "$C"/journal.txt "$C"/E*-mutation.json "$C"/E0-oos-pages*.json "$C"/SHA256SUMS.sources.* "$C"/cores-listing.txt "$EV/corruption/" 2>/dev/null
for f in "$C"/E*-checkdb.out "$C"/E*-read.out "$C"/source-c16k-build.out; do
  [ -f "$f" ] || continue
  { echo "##### $(basename "$f") (last 40 lines)"; tail -40 "$f"; } > "$EV/corruption/$(basename "$f" .out)-tail.txt"
done

# bounded filesystem procedure
B=$T16/boundedfs
cp "$B"/out/journal.txt "$B"/out/A-inner.txt "$B"/out/A-*.txt "$B"/out/A-createdb.out "$B"/out/B-createdb.out "$B"/out/B-volumes-*.txt "$B"/out/B-vinf-after.txt "$B"/journal-attempts-1-2.txt "$EV/bounded-fs/" 2>/dev/null
{ echo "##### A-fill.out (first error context and tail)"; grep -n -m3 -B2 -A2 "ERROR\|Assertion\|Aborted" "$B/out/A-fill.out" 2>/dev/null; echo "....."; tail -15 "$B/out/A-fill.out" 2>/dev/null; } > "$EV/bounded-fs/A-fill-excerpt.txt"
{ echo "##### B-fill.out (tail)"; tail -15 "$B/out/B-fill.out" 2>/dev/null; } > "$EV/bounded-fs/B-fill-tail.txt"
cp "$B/inner_A.sh" "$EV/bounded-fs/inner_A.sh" 2>/dev/null
cp "$B/out/probe-tmpfs-userns.txt" "$B/out/probe-tmpfs-userns-ctypes.txt" "$EV/bounded-fs/" 2>/dev/null
cp "$B"/probe-*.txt "$EV/bounded-fs/" 2>/dev/null

# tools and configuration
cp "$T16/tools/t16env.sh" "$T16/tools/t16_run.sh" "$T16/tools/t16_run_all.sh" "$T16/tools/t16_corruption.sh" "$T16/tools/t16_boundedfs.sh" "$T16/tools/oos_pages.py" "$T16/tools/t16_assemble_evidence.sh" "$EV/tools/"
cp "$T16/conf/cubrid.conf.template" "$EV/tools/cubrid.conf.template"
cp /tmp/claude-1000/-home-vimkim-gh-cb-CBRD-26659-oos-testcases-handover/6f4722b1-aec8-4ffc-81d4-37142dec0097/scratchpad/apply_t16_patches.py "$EV/tools/apply_t16_patches.py" 2>/dev/null
cp "$T16/cores/CORE-LISTING-before-trim.txt" "$EV/identity/cores-listing-before-trim.txt" 2>/dev/null
ls -la "$T16/cores" > "$EV/identity/cores-listing-final.txt"

# bulky artifacts: hashed, not copied
( cd "$T16" && find sites corruption/out corruption/copies boundedfs build-logs cores conf -type f \
    ! -name '*.lock' 2>/dev/null | sort | xargs -d '\n' sha256sum ) > "$EV/SHA256SUMS-bulky.txt" 2>/dev/null
echo "bulky files hashed: $(wc -l < "$EV/SHA256SUMS-bulky.txt")"
( cd "$EV" && find . -type f ! -name SHA256SUMS-evidence.txt | sort | xargs -d '\n' sha256sum ) > "$EV/SHA256SUMS-evidence.txt"
echo "evidence files: $(wc -l < "$EV/SHA256SUMS-evidence.txt")"
du -sh "$EV"
