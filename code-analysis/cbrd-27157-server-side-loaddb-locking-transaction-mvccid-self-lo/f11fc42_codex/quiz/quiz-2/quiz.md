# Quiz 2 — 같은 unique key를 두 transaction이 넣는다면

## 실행 전 예측

T1이 key 7을 삽입하고 잠시 transaction을 끝내지 않습니다. T2가 같은 key를 삽입합니다. 다음을 순서대로 적으세요.

1. T1의 row에 적힌 INSID는 무엇을 가리키나요?
2. T1은 어느 resource에 어느 mode를 보유하나요?
3. T2는 어느 resource에 어느 mode를 요청하나요?
4. T1이 rollback한 뒤 T2가 이전 B-tree 판단을 그대로 쓰면 왜 위험한가요?
5. 일반 snapshot reader도 항상 같은 S self-lock을 요청하나요?

## 안전한 실행

예상 시간은 약 10초다. launcher는 전용 DB `ca27157q2mvf11`만 만든다. 기존 동명 DB가 있으면 소유권을 얻기 전에 중단하며, 그 DB의 server를 멈추거나 process를 죽이거나 DB를 삭제하지 않는다. `trap` cleanup은 `owned == 1`인 launcher 소유 자원에만 적용된다.

```bash
./run.sh
```

성공 조건은 다른 key 대조군 성공, 같은 transaction self-lock에서 X/S contention, rollback 뒤 observer 행 성공, exact cleanup이다. sample output은 비권위 예시다.

## 답안 공백

T1 삽입부터 T2 최종 성공까지 여섯 단계를 적으세요.

1. `__________`
2. `__________`
3. `__________`
4. `__________`
5. `__________`
6. `__________`

runtime이 `mvcc_is_active_id` 재호출과 page latch 해제 순서까지 직접 증명하는지도 쓰세요: `__________`.

연결: `mvccid-self-lock-rendezvous`, `CUBRID-C010`, 6·7장.
