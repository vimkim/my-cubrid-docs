#!/usr/bin/env bash
#
# quiz-5 self-scoring aid — prints the five rubric checkpoints one at a time
# so the learner can grade their own written design before reading answer.md.
# Read-only; no database needed.
set -uo pipefail
cat <<'EOF'
당신의 설계 답안을 옆에 두고, 각 항목에 예/아니오로 답하라.

[1] 원자성: 레코드가 heap update 와 같은 원자 단위에서 로깅되는가?
    두 크래시 방향(로그 유실 → aaa 영구 누수 / 로그 생존+heap 롤백 → 살아있는 aaa 회수)을
    모두 다뤘는가?

[2] 게이팅: 소비 시점이 기존 NOTIFY_VACUUM 경로와 동일한 MVCCID 게이트를 받는가?
    (스냅샷 독자가 aaa 를 아직 볼 수 있는 동안의 회수를 배제했는가?)

[3] 신원(핵심): 블록 재처리가 이 레코드를 두 번 읽고 같은 물리 aaa 를 재유도할 때,
    두 번째 소비가 재사용 슬롯을 지우지 않도록 하는 장치가 설계에 있는가?
    "update log 는 참조의 거처를 옮길 뿐, 소비의 검증(스탬프)을 대체하지 않는다"에
    도달했는가?

[4] 다중 참조: dedup 후 aaa 가 여러 버전에 공유될 수 있음을 다뤘는가?
    (마지막 참조자 판정 — bump / old∩new 검사 / refcount 중 택일과 비용)

[5] replication: 물리 OID 가 slave 에서 무의미함을 다뤘는가?
    (값-논리적 표현 또는 slave 로컬 재생성)

5개 모두 '예'면 answer.md 와 대조하라. [3] 이 '아니오'면 ch16 §7 의 네 번째 성립 요건을
다시 읽어라 — 이 퀴즈의 존재 이유가 그 항목이다.
EOF
