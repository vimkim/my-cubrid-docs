#!/bin/bash
set -euo pipefail
root=/home/vimkim/.cache/codex/develop-partition-ba88e470
label=$1
case "$label" in baseline|patched|probe) ;; *) exit 2;; esac
exec timeout --signal=TERM --kill-after=15s 900 bwrap --ro-bind / / --bind "$root/$label/home" /home/vimkim --ro-bind /home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8 /home/vimkim/java --tmpfs /tmp --dev /dev --proc /proc --unshare-user --uid 0 --gid 0 --unshare-pid --unshare-ipc --unshare-net --cap-add CAP_NET_ADMIN --unshare-uts --hostname localhost --die-with-parent --chdir /home/vimkim /usr/bin/env -i HOME=/home/vimkim USER=root LOGNAME=root SHELL=/bin/bash TERM=xterm LANG=en_US.UTF-8 PATH=/usr/bin:/bin /bin/bash --noprofile --norc -c '
set -eu
/usr/sbin/ip link set lo up
/usr/sbin/ip link add ctp0 type dummy
/usr/sbin/ip address add 192.0.2.27/24 dev ctp0
/usr/sbin/ip link set ctp0 up
source /home/vimkim/.bash_profile
ulimit -c 0
cubrid_rel
command -v cubrid csql
sha256sum "$CUBRID/bin/cub_server" "$CUBRID/lib/libcubridsa.so" "$CUBRID/lib/libcubrid.so"
ldd "$CUBRID/bin/cub_server"
if [ -f /home/vimkim/probe.py ]; then exec python3 /home/vimkim/probe.py; fi
exec /usr/bin/script -qefc "bash /home/vimkim/CTP/bin/ctp.sh shell -c /home/vimkim/shell.conf" /home/vimkim/transcript.log
'
