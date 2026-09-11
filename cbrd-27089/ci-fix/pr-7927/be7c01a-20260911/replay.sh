#!/bin/bash
set -eu
root=/home/vimkim/.cache/codex/pr7927-be7c01a
label=$1; suite=$2
exec timeout -s KILL 1200 unshare -r --mount-proc -i -p -f -n --kill-child=SIGKILL -- bash -c '
set -eu
root=$1; label=$2; suite=$3; d=$root/$label
mount --bind "$d/install" /mnt
mount --bind /home/vimkim/.cache/codex/pr6864-f4299ac/ns_hosts /etc/hosts
mount --bind /home/vimkim/.cache/codex/pr6864-f4299ac/ns_resolv.conf /etc/resolv.conf
mount -t tmpfs -o size=1g tmpfs /tmp
ip link set lo up
export CUBRID=/mnt CUBRID_DATABASES=/mnt/databases LD_LIBRARY_PATH=/mnt/lib:/mnt/cci/lib
export PATH=/mnt/bin:$PATH CTP_HOME="$d/CTP"
export JAVA_HOME=/home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8
ulimit -c 0
mkdir -p /mnt/databases
: > /mnt/databases/databases.txt
cubrid_rel
sha256sum /mnt/bin/cub_server /mnt/lib/libcubridsa.so
bash "$CTP_HOME/bin/ctp.sh" "$suite" -c "$d/$suite.conf"
' _ "$root" "$label" "$suite"
