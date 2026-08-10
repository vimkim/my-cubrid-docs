#!/usr/bin/env bash
#
# quiz-2 — contrast vacuum block traces of an UNDISTURBED run (experiment-1)
# with an INTERRUPTED one (experiment-2). Read-only over $CUBRID/log/server.
set -uo pipefail
[ -n "${CUBRID:-}" ] || { echo "CUBRID not set" >&2; exit 2; }
LOGDIR="$CUBRID/log/server"

latest() { ls -1t "$LOGDIR"/${1}_*.err 2>/dev/null | head -1; }

for spec in "experiment-1 (undisturbed):oos26950exp1" "experiment-2 (interrupted):oos26950"; do
    label=${spec%%:*}; db=${spec##*:}
    log=$(latest "$db")
    printf '\n=== %s — %s\n' "$label" "${log:-<no log found>}"
    [ -n "$log" ] || { printf '    run the experiments first\n'; continue; }
    printf '    Add block ..................... %s\n' "$(grep -ac 'Add block' "$log" || true)"
    printf '    is complete. Notify master .... %s\n' "$(grep -ac 'is complete. Notify master' "$log" || true)"
    printf '    is interrupted! ............... %s   <-- 0 이어도 재처리 없음의 증거가 아니다 (vacuum.c:4400-4403)\n' \
        "$(grep -ac 'is interrupted!' "$log" || true)"
done
printf '\n(비교 근거: experiment-2 는 경고 0건에서도 12,432건 재삭제 — ch12, CUBRID-C012)\n'
