#!/bin/bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 TOOLCHAIN_LABEL OUTPUT_DIRECTORY" >&2
  exit 2
fi

toolchain_label=$1
output_dir=$2

sha256sum "$output_dir"/original "$output_dir"/refactored-conditional "$output_dir"/refactored-forced \
  "$output_dir"/original.stripped "$output_dir"/refactored-conditional.stripped "$output_dir"/refactored-forced.stripped \
  > "$output_dir/sha256.txt"

for variant_name in original refactored-conditional refactored-forced; do
  binary="$output_dir/$variant_name"
  for section_name in .text .rodata .eh_frame .gcc_except_table .data; do
    section_file="$binary${section_name}.bin"
    if readelf -W -S "$binary" | grep -q " $section_name "; then
      objcopy --dump-section "$section_name=$section_file" "$binary"
    else
      rm -f "$section_file"
    fi
  done
  sha256sum "$binary".*.bin > "$binary.sections.sha256.txt"
done

for left_right in \
  "original refactored-conditional" \
  "refactored-conditional refactored-forced" \
  "original refactored-forced"; do
  read -r left right <<< "$left_right"
  comparison="$output_dir/diff-$left-vs-$right"
  different_bytes=$({ cmp -l "$output_dir/$left.stripped" "$output_dir/$right.stripped" 2>/dev/null || true; } | wc -l)
  {
    printf 'toolchain=%s\nleft=%s\nright=%s\n' "$toolchain_label" "$left" "$right"
    printf 'left_bytes='; stat -c %s "$output_dir/$left.stripped"
    printf 'right_bytes='; stat -c %s "$output_dir/$right.stripped"
    printf 'different_overlapping_bytes=%s\n' "$different_bytes"
  } > "$comparison.summary.txt"
  diff -u "$output_dir/$left.size.txt" "$output_dir/$right.size.txt" > "$comparison.size.diff" || true
  diff -u "$output_dir/$left.nm.txt" "$output_dir/$right.nm.txt" > "$comparison.nm.diff" || true
  diff -u "$output_dir/$left.objdump.txt" "$output_dir/$right.objdump.txt" > "$comparison.objdump.diff" || true
done
