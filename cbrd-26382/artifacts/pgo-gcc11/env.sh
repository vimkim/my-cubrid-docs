# usage: source env.sh <preset>
# Sets the CUBRID runtime environment for one installed build variant.
PGO_BENCH_PRESET=${1:?usage: source env.sh <preset>}
PGO_BENCH_WORKTREE_NAME=cbrd-26382-pgo
export CUBRID="$HOME/.cub/install/$PGO_BENCH_WORKTREE_NAME/$PGO_BENCH_PRESET"
export CUBRID_DATABASES="$HOME/.cub/db/$PGO_BENCH_WORKTREE_NAME/pgo-bench-$PGO_BENCH_PRESET"
export PATH="$CUBRID/bin:$PATH"
export LD_LIBRARY_PATH="$CUBRID/cci/lib:$CUBRID/lib:${LD_LIBRARY_PATH:-}"
export CUBRID_MSG_LANG=en_US
