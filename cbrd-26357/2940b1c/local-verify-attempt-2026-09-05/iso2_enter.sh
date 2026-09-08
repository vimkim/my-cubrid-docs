#!/bin/bash
# usage: iso2_enter.sh preflight | run <cases_dir>     (host side)
exec timeout -s KILL ${ISO2_TIMEOUT:-900} unshare -r --mount-proc -i -p -f -n --kill-child=SIGKILL -- bash -c '
  mount --bind "/tmp/claude-1000/-home-vimkim-gh-cb-oos-storage/777ff0f7-1761-4b37-9859-227a4803818a/scratchpad/CUBRID_iso2" /mnt || exit 2
  mount --bind /mnt/ns_hosts /etc/hosts || exit 2
  mount --bind /mnt/ns_resolv.conf /etc/resolv.conf || exit 2
  mount -t tmpfs -o size=64m tmpfs /tmp || exit 2
  exec bash /mnt/iso2_driver.sh "$@"' _ "$@"
