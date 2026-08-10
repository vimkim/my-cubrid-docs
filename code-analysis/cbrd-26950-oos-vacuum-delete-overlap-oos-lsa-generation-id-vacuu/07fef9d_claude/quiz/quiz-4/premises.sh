#!/usr/bin/env bash
#
# quiz-4 premises — verify the three load-bearing source facts behind the
# candidate verdicts, directly from a pinned CUBRID worktree. Read-only.
# Usage: bash premises.sh [/path/to/cubrid-worktree]
set -uo pipefail
ROOT=${1:-/home/vimkim/gh/cb/CBRD-26950-oos-vacuum-delete-overlap}
[ -d "$ROOT/src" ] || { echo "not a CUBRID tree: $ROOT" >&2; exit 2; }

echo "== 전제 1 — insid 정리가 헤더에서 insert MVCCID 를 물리 제거한다 (6a 의 사인, R1)"
grep -n "OR_MVCC_FLAG_VALID_INSID | OR_MVCC_FLAG_VALID_PREV_VERSION" "$ROOT/src/query/vacuum.c" | head -3

echo
echo "== 전제 2 — MVCCID 는 단조증가·비재사용 (6b 성립 / threshold 반례의 축)"
grep -n "MVCCID_FORWARD (log_Gl.hdr.mvcc_next_id)" "$ROOT/src/transaction/mvcc_table.cpp" | head -2

echo
echo "== 전제 3 — 청크 헤더에 신원 필드가 없다 (모든 후보의 출발점)"
sed -n '26,31p' "$ROOT/src/storage/oos_file.hpp"

echo
echo "== 전제 4 — 디스패치 게이트는 닫힌 블록만 배포한다 (6b 의 R2 전제)"
grep -n "newest_mvccid >= m_oldest_visible_mvccid" "$ROOT/src/query/vacuum.c" | head -2
echo
echo "(각 줄이 출력되면 전제가 이 리비전에서 성립한다. 라인 번호는 HEAD 07fef9d48 기준과 다를 수 있다.)"
