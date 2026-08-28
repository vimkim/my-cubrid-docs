#!/usr/bin/env bash
# usage: train.sh <preset> <training_queries>
# Runs the training workload on the instrumented build. Every instrumented
# process (createdb, csql, cub_master, cub_server) merges counters into the
# -fprofile-generate directory on clean exit.
set -euo pipefail
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
preset=${1:?usage: train.sh <preset> <queries>}
queries=${2:?usage: train.sh <preset> <queries>}

bash "$script_dir/setup-db.sh" "$preset"
CSQL_TIMEOUT=3600 bash "$script_dir/run-sample.sh" "$preset" "$queries"
echo "[train] training complete"
