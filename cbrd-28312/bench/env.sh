# usage: source env.sh A|B
V=${1:?variant}
for _v in $(env | grep -oE '^CUBRID[A-Z_]*='); do unset ${_v%=}; done
unset CUB_WORKENV_INSTALL PRESET_MODE
BENCH=/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-develop/20b768f1-37f0-4831-a512-25dbba2cb615/scratchpad/bench
export CUBRID=/home/vimkim/.cub/install/oos-pending-record-alloc/$V
export CUBRID_DATABASES=$BENCH/db$V
export CUBRID_TMP=/home/vimkim/.cub/pra/tmp$V
export PATH=$CUBRID/bin:/usr/bin:/bin:/usr/sbin
export LD_LIBRARY_PATH=$CUBRID/lib:$CUBRID/cci/lib
unset CUBRID_MSG_LANG CUBRID_CHARSET
DB=benchdb
