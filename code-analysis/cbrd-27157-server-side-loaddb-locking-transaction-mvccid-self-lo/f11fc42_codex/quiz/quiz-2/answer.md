# Quiz 2 모범 답안과 해설

1. INSID는 그 version을 만든 inserter의 MVCCID를 가리킨다.
2. T1은 자기 MVCCID를 key로 하는 transaction resource에 X self-lock을 가진다.
3. unique 검사자인 T2는 같은 MVCCID resource에 S lock을 요청한다. X와 S가 충돌하여 기다린다.
4. 기다리는 동안 T1이 commit할 수도, rollback할 수도 있고 index page도 달라질 수 있다. 이전 B-tree 판단을 그대로 쓰면 stale decision이 된다.
5. 일반 snapshot reader 전체가 이 protocol을 쓰는 것은 아니다. 이 책에서 말하는 waiter는 unique/FK 같은 특수 검사 경로다.

별도의 여섯 단계 시간축 답은 `T1 insert → T1의 MVCCID X self-lock → T2 same-key 검사 → 같은 resource의 S wait → T1 rollback/종료 → T2 재판정·insert·commit`이다. T1의 rollback으로 key 7이 사라졌기 때문에 마지막 재검사와 삽입이 성공한다.

runtime은 MVCCID resource와 X/S rendezvous, wait 뒤 최종 성공을 보여 준다. 그러나 `mvcc_is_active_id` 재호출 자체와 page latch를 wait 전에 놓는 정확한 순서는 밖에서 직접 보이지 않으며 source evidence가 필요하다.

`self`는 자기 자신을 멈춘다는 뜻이 아니다. inserter가 자기 번호에 “아직 작업 중” 표지를 걸어 observer가 같은 번호에서 종료를 기다리게 한다는 뜻이다.

흔한 오답은 rollback 뒤 성공했다는 사실만으로 특정 내부 함수 호출까지 증명됐다고 말하거나, 모든 reader가 S self-lock을 잡는다고 일반화하는 것이다.
