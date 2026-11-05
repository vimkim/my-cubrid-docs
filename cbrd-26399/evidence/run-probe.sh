#!/usr/bin/env bash
# Build and run the CBRD-26399 slotted-page boundary probe against a configured CUBRID build tree.
# Usage: run-probe.sh <cubrid-build-dir> <output-dir> [ops-per-workload]
# The build dir must contain compile_commands.json; the SA-mode slotted_page object is built if missing.
set -euo pipefail

build_dir=$(cd "${1:?cubrid build dir}" && pwd)
out_dir=${2:?output dir}
ops=${3:-20000}
probe_dir=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out_dir"
out_dir=$(cd "$out_dir" && pwd)

obj_rel=sa/CMakeFiles/cubridsa.dir/__/src/storage/slotted_page.c.o
ninja -C "$build_dir" "$obj_rel" >"$out_dir/ninja.log" 2>&1

python3 -I - "$build_dir" "$obj_rel" >"$out_dir/compile-flags.txt" <<'PY'
import json, shlex, sys
build_dir, obj_rel = sys.argv[1], sys.argv[2]
for e in json.load(open(f"{build_dir}/compile_commands.json")):
    if e.get("output") == obj_rel:
        args = shlex.split(e["command"])
        keep, skip = [], False
        for a in args[1:]:
            if skip:
                skip = False
                continue
            if a in ("-o", "-c", "-MF", "-MT", "-MQ"):
                skip = True
                continue
            if a in ("-MD", "-MMD") or a.endswith("slotted_page.c"):
                continue
            keep.append(a)
        print(" ".join(shlex.quote(k) for k in keep))
        break
else:
    sys.exit(f"no compile command for {obj_rel}")
PY

src_file=$(python3 -I -c "import json,sys; print([e['file'] for e in json.load(open(sys.argv[1])) if e.get('output')==sys.argv[2]][0])" \
  "$build_dir/compile_commands.json" "$obj_rel")
src_root=${src_file%/src/storage/slotted_page.c}

{
  echo "source_root: $src_root"
  echo "source_revision: $(git -C "$src_root" rev-parse HEAD)"
  echo "source_dirty: $(git -C "$src_root" status --porcelain -- src | wc -l) tracked/untracked entries under src/"
  echo "slotted_page.c sha256: $(sha256sum "$src_root/src/storage/slotted_page.c" | cut -d' ' -f1)"
  echo "object: $build_dir/$obj_rel"
  echo "compiler: $(g++ --version | head -1)"
  echo "ops_per_workload: $ops"
} >"$out_dir/identity.txt"

eval "g++ $(cat "$out_dir/compile-flags.txt") -fno-pie -c \"$probe_dir/spage_boundary_probe.cpp\" -o \"$out_dir/probe.o\"" \
  2>"$out_dir/compile.log"
g++ -no-pie -o "$out_dir/spage_boundary_probe" "$out_dir/probe.o" "$build_dir/$obj_rel" \
  -Wl,--unresolved-symbols=ignore-all -lpthread 2>"$out_dir/link.log"

"$out_dir/spage_boundary_probe" "$ops" >"$out_dir/results.jsonl" 2>"$out_dir/stderr.log"
echo "exit: $?" >>"$out_dir/identity.txt"
cat "$out_dir/results.jsonl"
