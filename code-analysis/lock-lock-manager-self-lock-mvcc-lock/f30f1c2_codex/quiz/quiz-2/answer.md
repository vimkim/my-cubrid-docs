# Answer 2 — one-way wait/release

T1은 row 1 instance X holder이고 T2는 같은 instance X waiter다. Wait metadata와 queue link가 준비된 뒤 resource mutex를 놓고 suspend해야 한다. Holder release는 aggregate mode를 재계산하고 grant를 shared state에 게시한 뒤 waiter를 깨운다.

T1 rollback 뒤 900은 사라지고 T2의 `+1`이 committed 100에 적용되어 101이 된다. Wakeup 자체가 101을 만드는 것이 아니라 X grant, latest row fetch, operation 재개, commit이 이어진 결과다.

Timeout은 개별 wait 제한, interrupt는 외부 취소, deadlock은 cycle victim 결정이다. 모두 waiter link와 transaction-held locks를 알맞게 정리해야 한다. Deadlock test는 어느 actor가 victim인지 고정하지 말고 exactly one survivor, victim의 선행 변경 rollback, no residual holder/waiter를 채점한다.

흔한 오답은 SLEEP 자체가 101을 만들었다고 보는 것, wakeup과 commit을 같은 event로 보는 것, 한 방향 대기가 detector/victim을 시험했다고 보는 것이다. 이 Quiz는 timeout, interrupt, cycle, victim, starvation freedom을 실행하지 않는다.
