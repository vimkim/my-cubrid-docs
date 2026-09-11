#!/bin/bash
# CBRD-26659 campaign ticket 14 -- demonstrate that campaign_ns.sh contains the CTP shell
# helpers' unscoped cleanup primitives.
#
# Four checks, arranged as two matched pairs so that the demonstration is shown to
# discriminate rather than merely to report success:
#
#   1  process containment : a `cub`-named process started OUTSIDE the namespace survives
#                            `pkill cub` and the `ps -u $USER | kill -9` sweep run INSIDE.
#   2  process control     : the same sweep, run in the namespace that OWNS the decoy,
#                            does kill it. Without this, check 1 would also pass if the
#                            sweep silently did nothing.
#   3  ipc containment     : a System V segment created OUTSIDE is invisible to `ipcs`
#                            inside and cannot be destroyed by `ipcrm -m` inside.
#   4  ipc control         : the same commands, run in the namespace that OWNS the
#                            segment, do list and destroy it.
#
# Exit status 0 only when all four hold. Writes its transcript to stdout; the caller
# redirects it into the evidence directory.
#
# The host is never swept: no unscoped `pkill cub` or `ipcrm` is ever executed outside a
# namespace. Checks 2 and 4 run their sweeps inside a namespace that contains only the
# decoy, so the only things they can reach are the things this script created.
set -u

here=$(cd "$(dirname "$0")" && pwd)
ns="${here}/campaign_ns.sh"
work=$(mktemp -d "${TMPDIR:-${HOME}/.cub/campaign/cbrd-26659/ticket14}/isolation.XXXXXX")
decoy="${work}/cubdecoy"
failures=0

cleanup() {
    [ -n "${decoy_pid:-}" ] && kill "${decoy_pid}" 2>/dev/null
    [ -n "${outside_shmid:-}" ] && ipcrm -m "${outside_shmid}" 2>/dev/null
    rm -rf "${work}"
}
trap cleanup EXIT

report() {
    # report <ok|nok> <check> <detail>
    if [ "$1" = ok ]; then
        echo "[OK]  $2 : $3"
    else
        echo "[NOK] $2 : $3"
        failures=$((failures + 1))
    fi
}

echo "== isolation demonstration for CBRD-26659 ticket 14 =="
echo "date          : $(date -Is)"
echo "host          : $(uname -srm)"
echo "unshare       : $(unshare --version 2>&1)"
echo "user          : $(id -un) uid=$(id -u)"
echo "namespace cmd : unshare --user --map-current-user --pid --fork --mount-proc --ipc"
echo

# The sweep under test: exactly the primitives CTP's init.sh / finish() / xkill /
# release_broker_sharedmemory use, in one place so both members of each pair run the same
# code.
sweep_processes='pkill cub >/dev/null 2>&1; for p in $(ps -u $(id -un) -o pid,comm | grep cub | grep -v grep | awk "{print \$1}"); do kill -9 "$p" 2>/dev/null; done; true'
sweep_ipc='for s in $(ipcs -m | grep "$(id -un)" | awk "{print \$2}"); do ipcrm -m "$s" 2>/dev/null; done; true'

# --- 1. process containment -------------------------------------------------------
cp /bin/sleep "${decoy}"
"${decoy}" 600 &
decoy_pid=$!
sleep 0.3
if ! kill -0 "${decoy_pid}" 2>/dev/null; then
    report nok process_containment "the decoy (pid ${decoy_pid}) did not start; the check cannot run"
else
    echo "decoy started outside the namespace: pid=${decoy_pid} comm=$(ps -o comm= -p ${decoy_pid})"
    "${ns}" /bin/bash -c "
        echo '  inside: processes visible to ps -u \$(id -un):' \$(ps -u \$(id -un) -o comm= | tr '\n' ' ')
        ${sweep_processes}
        echo '  inside: sweep finished'
        if [ -d /proc/${decoy_pid} ]; then echo '  inside: /proc/${decoy_pid} IS visible'; else echo '  inside: /proc/${decoy_pid} is not visible'; fi
        kill -9 ${decoy_pid} 2>&1 | sed 's/^/  inside: direct kill -> /'
    "
    sleep 0.3
    if kill -0 "${decoy_pid}" 2>/dev/null; then
        report ok process_containment "outside decoy pid ${decoy_pid} survived pkill/ps-sweep/direct kill run inside the namespace"
    else
        report nok process_containment "outside decoy pid ${decoy_pid} was killed from inside the namespace"
    fi
fi

# --- 2. process control (the sweep really kills what it can see) -------------------
control_out=$("${ns}" /bin/bash -c "
    ${decoy} 600 &
    inner=\$!
    sleep 0.3
    kill -0 \$inner 2>/dev/null || { echo 'START_FAILED'; exit 0; }
    ${sweep_processes}
    sleep 0.3
    if kill -0 \$inner 2>/dev/null; then echo 'SURVIVED'; else echo 'KILLED'; fi
")
case "${control_out}" in
    *KILLED*)  report ok  process_control "a decoy started inside the namespace was killed by the same sweep" ;;
    *)         report nok process_control "control sweep did not kill its own decoy (got '${control_out}'); check 1 proves nothing" ;;
esac

# --- 3. ipc containment ------------------------------------------------------------
outside_shmid=$(ipcmk -M 4096 2>/dev/null | awk '{print $NF}')
if [ -z "${outside_shmid}" ]; then
    report nok ipc_containment "could not create a System V segment outside; the check cannot run"
else
    echo "segment created outside the namespace: shmid=${outside_shmid}"
    "${ns}" /bin/bash -c "
        echo '  inside: ipcs -m rows for this user:' \$(ipcs -m | grep -c \"\$(id -un)\")
        ${sweep_ipc}
        ipcrm -m ${outside_shmid} 2>&1 | sed 's/^/  inside: direct ipcrm -> /'
    "
    if ipcs -m | awk '{print $2}' | grep -qx "${outside_shmid}"; then
        report ok ipc_containment "outside segment ${outside_shmid} survived the ipcrm sweep and a direct ipcrm run inside the namespace"
    else
        report nok ipc_containment "outside segment ${outside_shmid} was destroyed from inside the namespace"
    fi
fi

# --- 4. ipc control ----------------------------------------------------------------
ipc_control_out=$("${ns}" /bin/bash -c "
    id=\$(ipcmk -M 4096 2>/dev/null | awk '{print \$NF}')
    [ -z \"\$id\" ] && { echo 'CREATE_FAILED'; exit 0; }
    ipcs -m | awk '{print \$2}' | grep -qx \"\$id\" || { echo 'NOT_LISTED'; exit 0; }
    ${sweep_ipc}
    if ipcs -m | awk '{print \$2}' | grep -qx \"\$id\"; then echo 'SURVIVED'; else echo 'DESTROYED'; fi
")
case "${ipc_control_out}" in
    *DESTROYED*) report ok  ipc_control "a segment created inside the namespace was listed and destroyed by the same sweep" ;;
    *)           report nok ipc_control "control sweep did not destroy its own segment (got '${ipc_control_out}'); check 3 proves nothing" ;;
esac

echo
echo "failures=${failures}"
[ "${failures}" -eq 0 ]
