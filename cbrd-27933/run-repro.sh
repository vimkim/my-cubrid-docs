#!/usr/bin/env bash
# CBRD-27933 repro runner. Runs what CTest test_oos_real_vacuum_latch_timeout runs, in the worktree's
# selected preset: for each OosRealVacuumHeaderHeld case, a fresh unittestdb fixture, test_oos_real_vacuum_server
# with CUBRID_PAGE_LATCH_TIMEOUT_IN_MSECS=2000, then the fixture cleanup. Each case gets its own process because
# the binary breaks on the first failure. The fixture database lives in a scratch registry, so the run needs no
# initialized host workenv.
#
# usage: run-repro.sh <label> [case ...]     (from the CUBRID worktree root)
# output: $OUT/<label>/{test.log,<case>.server.err,summary.txt}
set -euo pipefail

label=${1:?label}
shift
cases=("$@")
if [ ${#cases[@]} -eq 0 ]; then
  cases=(HomeRowOosReclaimedAfterHeaderLookupFailure RelocatedRowOosReclaimedAfterHeaderLookupFailure
         ShutdownDuringHeaderLookupFailureLeavesHomeRowToVacuum)
fi
worktree=$(git rev-parse --show-toplevel)
out_root=${OUT:-/mnt/nvme/data-5/tmp/cbrd27933-repro/runs}
out="$out_root/$label"
registry="$out/databases"
mkdir -p "$out" "$registry"

cd "$worktree"
# .envrc unsets inherited CUBRID_* variables, so extra server parameters travel in CBRD27933_EXTRA_ENV.
direnv exec . env CUBRID_DATABASES="$registry" CBRD27933_OUT="$out" CBRD27933_WT="$worktree" \
  CBRD27933_CASES="${cases[*]}" CBRD27933_EXTRA_ENV="${EXTRA_ENV:-CUBRID_ER_LOG_VACUUM=4099}" bash -c '
  set -u
  run ()
  {
    export PATH="$CUBRID/bin:$PATH" LD_LIBRARY_PATH="$CUBRID/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    if [ "${CUBRID_RUNTIME_READY:-0}" != 1 ]; then
      # A preset other than the initialized one: borrow TMP, port and JDK of this worktree for the in-process server.
      eval "$(grep -E "^export (CUBRID_TMP|CUBRID_CUBRID_PORT_ID|CUBRID_JAVA_HOME)=" "$CBRD27933_WT/.cub-workenv/env.sh")"
      export JAVA_HOME="$CUBRID_JAVA_HOME"
      echo "borrowed runtime: CUBRID_TMP=$CUBRID_TMP port=$CUBRID_CUBRID_PORT_ID JAVA_HOME=$JAVA_HOME"
    fi
    scripts="$CBRD27933_WT/unit_tests/oos/scripts"
    worst=0
    for c in $CBRD27933_CASES; do
      echo "=== case $c"
      bash "$scripts/setup_unittestdb.sh" || { echo "fixture setup failed"; return 1; }
      rc=0
      (cd "$CUBRID_BUILD_DIR/unit_tests/oos" \
        && env CUBRID_PAGE_LATCH_TIMEOUT_IN_MSECS=2000 $CBRD27933_EXTRA_ENV timeout 900 "$CUBRID_BUILD_DIR/bin/test_oos_real_vacuum_server" \
             "--gtest_filter=OosRealVacuumHeaderHeld.$c") || rc=$?
      # The server log is per minute and can hold the previous case too: keep this boot only.
      err="$CUBRID/log/server/unittestdb_latest.err"
      up=$(grep -n "Server status is UP" "$err" 2>/dev/null | tail -1 | cut -d: -f1)
      [ -n "$up" ] && tail -n "+$((up - 1))" "$err" > "$CBRD27933_OUT/$c.server.err"
      bash "$scripts/cleanup_unittestdb.sh" || echo "fixture cleanup failed"
      echo "test binary exit=$rc ($c)"
      [ "$rc" -ne 0 ] && worst=$rc
    done
    return "$worst"
  }
  export -f run
  "${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-build-coordinator.sh" installation-use 300 -- bash -c run
' > "$out/test.log" 2>&1 </dev/null && rc=0 || rc=$?

{
  printf 'label=%s rc=%s extra_env=%s\n' "$label" "$rc" "${EXTRA_ENV:-CUBRID_ER_LOG_VACUUM=4099}"
  printf 'source HEAD=%s, dirty paths: %s\n' "$(git rev-parse --short HEAD)" \
    "$(git status --porcelain | awk '{print $2}' | tr '\n' ' ')"
  direnv exec . bash -c 'printf "preset=%s install=%s\nlibcubrid sha256 install=%s build=%s\n" "$PRESET_MODE" "$CUBRID" \
    "$(sha256sum "$CUBRID/lib/libcubrid.so.11.5" | cut -c1-12)" \
    "$(sha256sum "$CUBRID_BUILD_DIR/cubrid/libcubrid.so.11.5" | cut -c1-12)"' 2>/dev/null
  git diff --stat -- src | tail -1 | sed 's/^/engine diff: /'
  grep -E 'borrowed runtime|\[CBRD-27933\]|Assertion|Failure$|must|never |\[  (PASSED|FAILED|SKIPPED) |\[       OK|test binary exit' \
    "$out/test.log" | awk '!seen[$0]++'
  for c in "${cases[@]}"; do
    f="$out/$c.server.err"
    [ -f "$f" ] || continue
    python3 -I - "$c" "$f" "$out/test.log" <<'EOF'
import re, statistics, sys
case, err, log = sys.argv[1:4]
text = open(err, errors="replace").read()
lines = text.splitlines(keepends=True)
section, on = [], False
for line in open(log, errors="replace"):
    if line.startswith("=== case "):
        on = line.strip() == "=== case " + case
    elif on:
        section.append(line)
section = "".join(section)
m = re.search(r"delete log block (\d+)", section)
delete_block = m.group(1) if m else None
m = re.search(r"deleted in log block (\d+)", section)
unrelated_block = m.group(1) if m else None
head = re.compile(r"^Time: \S+ (\d+):(\d+):(\d+\.\d+) - (\w+) \*\*\* file \S*?(src/\S+?), line (\d+)(?:.*CODE = (-?\d+))?")
events, offset = [], 0
for i, line in enumerate(lines):
    hm = head.match(line)
    if hm:
        h, mi, sec, level, src, num, code = hm.groups()
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        events.append(dict(t=int(h) * 3600 + int(mi) * 60 + float(sec), level=level, where=f"{src}:{num}",
                           code=code, next=nxt, offset=offset))
    offset += len(line.encode())
timeouts = [e for e in events if e["code"] == "-836"]
gaps = [b["t"] - a["t"] for a, b in zip(timeouts, timeouts[1:])]
print(f"{case} server.err: {len(text.encode())} bytes, {len(lines)} lines")
if gaps:
    print(f"{case} latch timeouts: {len(timeouts)} over {timeouts[-1]['t'] - timeouts[0]['t']:.1f} s; gap s: min {min(gaps):.2f} "
          f"median {statistics.median(gaps):.2f} max {max(gaps):.2f}; first gap {gaps[0]:.2f}")
else:
    print(f"{case} latch timeouts: {len(timeouts)}")
total = len(text.encode())
for i, e in enumerate(events):
    e["size"] = (events[i + 1]["offset"] if i + 1 < len(events) else total) - e["offset"]
    if e["level"] != "DEBUG":
        e["kind"] = "er_set"
    elif e["next"].startswith(("VACUUM ERROR", "VACUUM WARNING")):
        e["kind"] = "vacuum_err"
    else:
        e["kind"] = "job_debug"
kinds = {k: sum(e["size"] for e in events if e["kind"] == k) for k in ("er_set", "vacuum_err", "job_debug")}
print(f"{case} bytes by kind: er_set events with stacks {kinds['er_set']}, VACUUM ERROR/WARNING lines {kinds['vacuum_err']}, "
      f"job/debug lines (CUBRID_ER_LOG_VACUUM test setting) {kinds['job_debug']}")
if len(timeouts) > 1:
    t0, t1 = timeouts[0]["t"], timeouts[-1]["t"]
    grown = sum(e["size"] for e in events if e["kind"] != "job_debug" and t0 <= e["t"] < t1)
    print(f"{case} error-log growth between first and last latch timeout (excluding job/debug lines): {grown} bytes in "
          f"{t1 - t0:.1f} s = {grown / (t1 - t0) / 1024:.1f} KiB/s")
def count(pattern):
    return len(re.findall(pattern, text))
print(f"{case} counts: OOS-flag-without-VFID={count('OOS flag set but no OOS VFID')}, "
      f"could-not-prepare={count('Could not prepare vacuum')}, heap-page-error={count('Vacuum heap page [0-9|]+, error_code')}, "
      f"block-interrupted-lines={count('is interrupted')}")
for name, block in (("delete", delete_block), ("unrelated", unrelated_block)):
    if block is not None:
        verdicts = re.findall(rf"Processing log block {block} is (\w+)", text)
        tally = {v: verdicts.count(v) for v in dict.fromkeys(verdicts)}
        print(f"{case} {name} block {block} verdicts: {tally} sequence: {' '.join(v[0] for v in verdicts)}")
asserts = {}
for e in events:
    if "Assertion" in e["next"]:
        asserts[e["where"]] = asserts.get(e["where"], 0) + 1
noise = {k: v for k, v in asserts.items() if k == "src/storage/slotted_page.c:4544"}
other = {k: v for k, v in asserts.items() if k not in noise}
print(f"{case} assertion notifications: known noise {noise or 0}, other {other or 'none'}")
errors = {}
for e in events:
    if e["level"] in ("ERROR", "FATAL", "WARNING", "SYNTAX"):
        key = f"{e['level']} {e['where']} {e['code']}"
        errors[key] = errors.get(key, 0) + 1
print(f"{case} error sources: " + "; ".join(f"{k} x{v}" for k, v in sorted(errors.items(), key=lambda kv: -kv[1])))
EOF
  done
} | tee "$out/summary.txt"
exit "$rc"
