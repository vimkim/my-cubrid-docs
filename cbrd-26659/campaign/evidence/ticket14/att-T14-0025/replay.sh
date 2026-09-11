#!/bin/bash
# Replay of att-T14-0025.
#
# Prerequisites, none of which this script creates:
#   * the pinned engine installed at
#       /home/vimkim/.cub/install/oos-baseline-f4299ac0c/release_gcc
#     built from /home/vimkim/gh/cb/oos-baseline-f4299ac0c at
#     f4299ac0cd777a2a964c1f197ae5ebf9841a4936. identity.txt holds the library hashes
#     run_attempt.sh checks before it will start.
#   * CTP installed at /home/vimkim/CTP (jar hashes in identity.txt).
#   * the testcase worktree on branch CBRD-26659-oos-testcases-handover, with the case at
#       /home/vimkim/.cub/campaign/cbrd-26659/ticket14/negctl/oos_dur01_negative_control/cases/oos_dur01_negative_control.sh
#   * TCP ports 26659, 33120, 33121 and 33122 free.
#   * util-linux unshare with unprivileged user namespaces enabled, which is what
#     contains the CTP helpers' unscoped process and IPC cleanup.
#
# No service needs to be running: the case creates, starts, crashes, restarts and drops
# its own database.
exec bash /home/vimkim/.cub/campaign/cbrd-26659/ticket14/tools/run_attempt.sh <new-attempt-id> release_gcc /home/vimkim/.cub/campaign/cbrd-26659/ticket14/negctl/oos_dur01_negative_control
