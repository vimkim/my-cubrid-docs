#!/bin/bash
# quiz-2 실행기.
# 사용법: bash run.sh <버려도-되는-DB이름> <백업-임시디렉터리>
# 이 스크립트가 만드는 것: sx_quiz2_t 테이블(스스로 삭제), watcher 1개(스스로 종료),
# 백업 아카이브(자동 삭제: -r 옵션 + 임시디렉터리 정리는 사용자 몫).
set -eu
DB="${1:?사용법: bash run.sh <버려도-되는-DB이름> <백업-임시디렉터리>}"
BK="${2:?사용법: bash run.sh <버려도-되는-DB이름> <백업-임시디렉터리>}"
cd "$(dirname "$0")"
mkdir -p "$BK"

# (1) 통계 수집 watcher — CUBRID는 watcher가 붙어 있는 동안에만 전역 카운터를 누적한다.
nohup cubrid statdump -i 60 -o quiz2_watch.out "$DB" > quiz2_watch.log 2>&1 &
WRAPPER_PID=$!
sleep 2

# (2) dirty 생성 워크로드 + 세션 histogram 관측
csql -u dba "$DB" -i flush_quiz.sql

# (3) 동기 checkpoint 강제 (-C: 압축, -r: 아카이브 보관 안 함)
cubrid backupdb -D "$BK" -C -r "$DB"

# (4) 전역 카운터 관측
cubrid statdump "$DB" | grep -E "Num_data_page_iowrites|Num_data_page_flushed|Num_data_page_dirties"

# (5) watcher 정리 — wrapper가 자식 statdump를 띄우므로 cmdline 패턴으로 자기 소유만 종료
kill "$WRAPPER_PID" 2>/dev/null || true
for pid in $(pgrep -f "statdump -i 60 -o quiz2_watch.out $DB" || true); do
  kill "$pid" 2>/dev/null || true
done
sleep 1
if pgrep -f "statdump -i 60 -o quiz2_watch.out $DB" > /dev/null 2>&1; then
  echo "경고: watcher가 남아 있습니다. pgrep -f statdump 로 확인 후 종료하세요." >&2
  exit 1
fi
rm -f quiz2_watch.out quiz2_watch.log
echo "quiz-2 done."
