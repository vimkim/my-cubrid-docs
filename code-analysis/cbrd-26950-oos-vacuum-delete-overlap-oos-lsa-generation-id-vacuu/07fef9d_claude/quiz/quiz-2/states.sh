#!/usr/bin/env bash
#
# quiz-2 — compare the vacuum block traces of the two experiment-2 repetitions
# across their two boot cycles each (pre-stop / restart).
#
# Reads the PRESERVED excerpts in ./preserved (copied into the report so the
# exercise stays reproducible after $CUBRID/log/server rotates). Pass --live to
# re-derive from $CUBRID instead; note the live logs rotate and the newest file
# is the *restart* boot, not the one that produced the blocks.
set -uo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
P="$HERE/preserved"
MODE=${1:-preserved}

count() { local n; n=$(grep -ac "$2" "$1" 2>/dev/null); echo "${n:-0}"; }

row() { # $1 label, $2 file
    local f=$2
    if [ ! -f "$f" ]; then printf '    %-22s (파일 없음: %s)\n' "$1" "$f"; return; fi
    printf '    %-22s Add block=%-4s  완료 통지=%-4s  is interrupted!=%s\n' \
        "$1" "$(count "$f" 'Add block')" "$(count "$f" 'is complete. Notify master')" \
        "$(count "$f" 'is interrupted!')"
}

if [ "$MODE" = --live ]; then
    L="${CUBRID:?CUBRID not set}/log/server"
    printf '\n[live 모드] %s 의 최신 로그만 봅니다 — 최신 파일은 재기동 부팅이라 블록 생산 기록이 없습니다.\n' "$L"
    for db in oos26950exp1 oos26950; do
        row "$db (최신)" "$(ls -1t "$L"/${db}_*.err 2>/dev/null | head -1)"
    done
    exit 0
fi

printf '\n=== experiment-2 rep 1 — 종료가 abort 였던 회차 (백로그 완주)\n'
row "부팅 1 (정지 전)"   "$P/rep1-pre-stop.txt"
row "부팅 2 (재기동)"    "$P/rep1-restart.txt"
printf '\n=== experiment-2 rep 2 — 정상 셧다운 회차 (백로그 12,031 잔존)\n'
row "부팅 1 (정지 전)"   "$P/rep2-pre-stop.txt"
row "부팅 2 (재기동)"    "$P/rep2-restart.txt"
printf '\n=== experiment-1 — 무중단 대조군\n'
row "부팅 1"            "$P/exp1-undisturbed.txt"
cat <<'EOF'

읽는 법:
  · 블록 생산(`Add block`)은 정지 전 부팅에만 나온다 — 재기동 부팅은 남은 블록을 소비할 뿐이다.
  · rep 2 는 `is interrupted!` 가 1건 — 백로그가 남은 채 worker 가 블록을 포기한 정상 셧다운 회차다.
  · rep 1 은 `is interrupted!` 가 0건인데도 재기동 후 12,432건이 재삭제됐다. 경고 0 은 안전의
    근거가 아니다(vacuum.c:4400-4403). 단 그 회차는 abort 종료였으므로 ch12 의 대안 설명을 함께 읽어라.
  · experiment-1 은 vacuum 로그가 아예 없다 — 그 DB 의 conf 에 `er_log_vacuum` 이 설정되지 않았기
    때문이다(관측 채널을 켜지 않으면 아무것도 보이지 않는다는 ch11 의 논점을 그대로 보여준다).
EOF
