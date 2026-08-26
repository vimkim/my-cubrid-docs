#!/bin/bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 TOOLCHAIN_LABEL OUTPUT_DIRECTORY" >&2
  exit 2
fi

toolchain_label=$1
output_dir=$2
source_dir=$(cd "$(dirname "$0")" && pwd)

mkdir -p "$output_dir"

gcc --version > "$output_dir/compiler.txt"
ld --version >> "$output_dir/compiler.txt"
cat /etc/os-release > "$output_dir/os-release.txt"

common_flags=(
  -std=c++17
  -O2
  -DNDEBUG
  -finline-functions
  -ggdb
  -fno-omit-frame-pointer
  -fPIE
  -fno-ident
  -ffile-prefix-map="$source_dir"=.
  -frandom-seed=scope-exit-probe
)

gcc -O2 -ggdb -fno-omit-frame-pointer -fPIE -fno-ident \
  -ffile-prefix-map="$source_dir"=. -frandom-seed=scope-exit-probe \
  -c "$source_dir/external_cleanup.c" -o "$output_dir/external_cleanup.o"

for variant_number in 1 2 3; do
  case "$variant_number" in
    1) variant_name=original ;;
    2) variant_name=refactored-conditional ;;
    3) variant_name=refactored-forced ;;
  esac

  binary="$output_dir/$variant_name"
  g++ "${common_flags[@]}" -DPROBE_VARIANT="$variant_number" \
    "$source_dir/scope_exit_probe.cpp" "$output_dir/external_cleanup.o" \
    -Wl,-Map,"$binary.map" -o "$binary"
  objcopy --only-keep-debug "$binary" "$binary.debug"
  cp "$binary" "$binary.stripped"
  strip --strip-debug "$binary.stripped"
  readelf -W -h -l -S -d -s "$binary" > "$binary.readelf.txt"
  size -A -d "$binary" > "$binary.size.txt"
  nm -n -S -C "$binary" > "$binary.nm.txt"
  objdump -drwC -Mintel "$binary" > "$binary.objdump.txt"
  "$binary" 1000000 > "$binary.run.txt"
done

"$source_dir/capture_existing.sh" "$toolchain_label" "$output_dir"
