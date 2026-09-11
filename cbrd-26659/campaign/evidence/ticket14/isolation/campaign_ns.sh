#!/bin/bash
# CBRD-26659 campaign ticket 14 -- process-ownership containment for the CTP shell runner.
#
# Why this exists
# ---------------
# The CTP shell helpers (CTP/shell/init_path/init.sh) perform unscoped cleanup on
# every case:
#
#   init()                       -> `cubrid service stop` ; `pkill cub`
#   finish()                     -> `cubrid service stop` ; `pkill cub` ;
#                                   release_broker_sharedmemory()
#   release_broker_sharedmemory()-> `ipcs | grep $USER | awk '{print $2}'` | `ipcrm -m`
#   xkill <pattern>              -> `ps -u $USER` | grep pattern | `kill -9`
#
# `pkill cub` is a name match over every process this UNIX user owns, and the ipcrm
# sweep destroys every System V shared-memory segment this user owns. Neither is scoped
# to the scenario, so on a shared host they reach databases, servers and brokers the
# campaign does not own -- including other sessions' work.
#
# Containment method
# ------------------
# Run the whole invocation in a user namespace that owns a private PID namespace and a
# private System V IPC namespace:
#
#   unshare --user --map-current-user --pid --fork --mount-proc --ipc -- <command>
#
#   --user --map-current-user  unprivileged namespace, uid/gid unchanged, so $USER,
#                              file ownership under /home and `ps -u $USER` all keep
#                              their normal meaning inside.
#   --pid --fork --mount-proc  the command becomes PID 1 of a new PID namespace with its
#                              own /proc, so pkill/ps/kill can only see and signal
#                              processes this invocation started. Processes outside are
#                              not merely protected, they are unaddressable.
#   --ipc                      a new System V IPC namespace, so `ipcs` lists only this
#                              invocation's segments and `ipcrm` cannot name any other.
#
# Not isolated, and therefore handled by allocation instead: TCP ports. A network
# namespace would need CAP_NET_ADMIN to bring `lo` up, which --map-current-user does not
# grant, so the campaign allocates private ports (cubrid_port_id 26659, brokers 33120 and
# 33121, ha 33122) and the caller verifies they are free.
#
# Usage:  campaign_ns.sh <command> [args...]
set -u

if [ "$#" -lt 1 ]; then
    echo "usage: campaign_ns.sh <command> [args...]" >&2
    exit 2
fi

exec unshare --user --map-current-user --pid --fork --mount-proc --ipc -- "$@"
