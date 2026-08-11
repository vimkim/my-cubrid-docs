# Answer 3 — visibility와 exclusion

Plain read는 T1의 uncommitted 900 대신 snapshot-visible committed 100을 읽을 수 있다. Ordinary MVCC path는 class IS를 유지하지만 qualifying row S를 요구하지 않는다. 이는 version visibility의 결과이지 latch, class lock, 모든 logical lock이 없다는 뜻이 아니다.

FOR UPDATE는 class IX와 latest instance X가 필요해 T1의 X와 충돌한다. Wake 뒤에는 row가 삭제·변경되었거나 predicate에서 벗어났을 수 있어 latest version과 조건을 재평가한다. T1 rollback 변형에서는 locked=100, observer update 뒤 final=101이 된다.

PostgreSQL은 MVCC heap visibility와 XMAX/MultiXact/XID wait를, InnoDB는 LOCK_NONE read view와 table IX/record X를 조합한다. 책임은 닮지만 resource와 retry Interface는 부분 유사다.

흔한 오답은 MVCC가 모든 lock을 없앤다고 보는 것, plain 100이 모든 wait 부재를 증명한다고 보는 것, page latch와 transaction row lock을 같은 것으로 보는 것, pre-wait tuple이 wake 뒤에도 유효하다고 보는 것이다. 이 Quiz는 recorded READ COMMITTED, rollback holder, 한 row만 다루며 exact function이나 다른 isolation을 증명하지 않는다.
