# 기계적 성공 조건

- loaddb가 `2 object(s) inserted, 0 object(s) failed`로 끝난다.
- small/large 값 일치가 각각 1이다.
- small은 `has no OOS file`, large는 OOS statistics와 live record 1 이상을 보인다.
- 마지막 줄은 두 전용 DB의 `CLEANUP_VERIFIED`다.

pre-fix assert나 cross-DBMS 설계 결론은 이 predicate가 자동으로 답하지 않는다.
