#!/bin/bash
set -eu
exec timeout -s KILL "${REPRO_TIMEOUT:-420}" unshare -r --mount-proc -i -p -f -n --kill-child=SIGKILL -- bash -c '
set -eu
mount --bind /home/vimkim/gh/cb/oos-bug-bts-4633/.scratch/bts4633/runtime /mnt
mount --bind /mnt/ns_hosts /etc/hosts
mount --bind /mnt/ns_resolv.conf /etc/resolv.conf
mount -t tmpfs -o size=256m tmpfs /tmp
ip link set lo up
export CUBRID=/mnt/install CUBRID_DATABASES=/mnt/databases LD_LIBRARY_PATH=/mnt/install/lib:/mnt/install/cci/lib
export PATH=/mnt/install/bin:$PATH init_path=/mnt/CTP/shell/init_path
exec bash /mnt/driver-gdb2.sh "$@"
' _ "$@"
