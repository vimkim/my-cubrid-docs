#!/usr/bin/env bash
#
# quiz-3 — lay the two evidence channels of experiment-2 side by side.
# Read-only over the experiment's artifact directory and oos.log.
set -uo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WORK=${WORK:-$HERE/../../experiments/experiment-2/raw/poc-work}
ROWS=${ROWS:-20000}

need() { [ -f "$1" ] || { echo "missing $1 — run experiment-2 first" >&2; exit 2; }; }
need "$WORK/deleted_A.txt"; need "$WORK/deleted_C.txt"; need "$WORK/double_deleted.txt"

A=$(wc -l < "$WORK/deleted_A.txt"); C=$(wc -l < "$WORK/deleted_C.txt")
D=$(wc -l < "$WORK/double_deleted.txt")
R=$( [ -f "$WORK/damaged_ids.txt" ] && wc -l < "$WORK/damaged_ids.txt" || echo 0 )

printf '\n=== 채널 B (보강) — 두 pass 모두에서 삭제된 OOS 슬롯\n'
printf '    pass 1 삭제 ................. %s개 OID\n' "$A"
printf '    pass 2 삭제 ................. %s개 OID\n' "$C"
printf '    양쪽 모두 ................... %s개  <- 청크는 점유된 슬롯에서만 삭제되므로,\n' "$D"
printf '    이들 슬롯은 두 삭제 사이에 재배부되었다 (재사용의 스토리지 물증)\n'

printf '\n=== 채널 A (결정적) — 값을 잃은 살아있는 커밋 행\n'
printf '    판독 불가 행 ................ %s개\n' "$R"
printf '    전부 슬롯이 비워진 뒤 INSERT-COMMIT 되었고 이후 무수정\n'

printf '\n=== 교차 검증\n'
printf '    채널 B(%s) vs 채널 A(%s): ' "$D" "$R"
if [ "$D" -eq "$R" ]; then printf '일치 (선행 3회 run 의 패턴)\n'
else printf '불일치 — 채널 B 에는 피해가 아닌 재삭제(예: 셧다운 중 abort 된 sysop 의 복원 청크\n'
     printf '    재삭제)가 섞이며, 이번 run 의 잔여 구성은 unknown 으로 기록됨 (CUBRID-C048)\n'; fi
printf '    대조군(id 1..%s) 가운데 피해: %s개   <-- 반드시 0\n' "$ROWS" \
    "$( [ -f "$WORK/damaged_ids.txt" ] && awk -v r="$ROWS" '$1 >= 1 && $1 <= r' "$WORK/damaged_ids.txt" | wc -l || echo 0 )"

if [ -n "${CUBRID:-}" ] && [ -s "$WORK/double_deleted.txt" ]; then
    printf '\n=== 원시 oos.log — 한 슬롯이 재기동을 사이에 두고 두 번 삭제된 흔적\n'
    IFS='|' read -r v p s < "$WORK/double_deleted.txt"
    grep -a "deleted chunk at oid={vol=$v,page=$p,slot=$s}" "$CUBRID/log/oos.log" | tail -2 | sed 's/^/    /'
fi
printf '\n'
