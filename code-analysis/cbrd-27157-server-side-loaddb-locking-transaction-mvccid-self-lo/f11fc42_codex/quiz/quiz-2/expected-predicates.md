# 기계적 성공 조건

- 다른 key 8 대조군은 남은 행 0으로 끝난다.
- `Transaction self-lock`, `X_LOCK`, `S_LOCK`이 한 lockdb dump에 있다.
- 최종 observer 출력은 `observer-after-wait`를 포함한다.
- 마지막 줄은 전용 DB의 `CLEANUP_VERIFIED`다.

함수 호출과 latch 순서는 이 predicate만으로 답할 수 없다.
