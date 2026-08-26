#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

targets=(
  "$script_dir/run-build.sh"
  "$script_dir/run-plans.sh"
  "$script_dir/run-qa-five-b.sh"
  "$script_dir/run-pmu.sh"
  "$script_dir/run-timings-single.sh"
  "$script_dir/render-perf-reports.sh"
  "$script_dir/runtime-common.sh"
)

if rg -n '/home/vimkim|\.scratch|cbrd26382-single|taskset -[^[:space:]]*c? 3,4|taskset -c 5' "${targets[@]}"; then
  echo "origin-host execution input remains in a portable script" >&2
  exit 1
fi

for script in run-plans.sh run-qa-five-b.sh run-pmu.sh run-timings-single.sh; do
  grep -Fq 'source "$script_dir/runtime-common.sh"' "$script_dir/$script"
done

grep -Fq 'query_plan=$artifact_root/query-plan.sql' "$script_dir/run-plans.sh"
grep -Fq 'patch_file=$artifact_root/scope-exit-C.patch' "$script_dir/run-build.sh"

for script in "$script_dir"/*.sh; do
  bash -n "$script"
done

echo "portable script checks passed"
