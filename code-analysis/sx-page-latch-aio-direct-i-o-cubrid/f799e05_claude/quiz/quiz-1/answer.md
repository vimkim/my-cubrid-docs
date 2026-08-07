# quiz-1 정답과 해설

## 정답

1. 승격은 **수만 번** 일어난다. 기준 빌드(f799e05d, debug)에서 20,000건 insert 에 `Data_page_total_promote_success` ≈ 88,000~90,000 — insert 1건당 약 4.4회다. 수치는 page 배치에 따라 수 % 변동하므로 "8만~9만대"면 정답으로 본다.
2. `Data_page_total_promote_fail` 은 **0** 이다. 승격 실패는 (a) 다른 promoter 가 먼저 대기 중이거나 (b) ONLY_READER 조건에서 다른 reader 가 있을 때만 발생하는데, 단일 세션 실행에는 경쟁자가 없어 모든 승격이 제자리(in-place) 분기로 즉시 성공한다.

## 인과 메커니즘

B-tree insert 는 non-leaf 를 `PGBUF_LATCH_READ` 로 잡고 내려간다(`btree.c`). leaf 가 가득 차 split 이 필요해지면 그 순간에만 부모/형제 page 의 WRITE 권한이 필요해지고, unfix 후 재획득 대신 `pgbuf_promote_read_latch` 로 쥔 채 승격한다 — unfix 하면 그 사이 page 가 바뀌어 탐색을 다시 해야 하기 때문이다. 순차 key 20,000건은 오른쪽 끝 leaf 를 계속 채워 split 을 반복 유발하므로 승격이 대량 발생한다. 하강 단계마다, 그리고 split 시 root/부모/형제 각각에 승격이 필요해 insert 1건당 여러 번이 된다.

승격이 "실패 기반"인 이유는 upgrade deadlock 이다: READ 를 쥔 두 스레드가 서로 WRITE 승격을 기다리면 영원히 풀리지 않으므로, CUBRID 는 경쟁을 감지하면 한쪽을 `ER_PAGE_LATCH_PROMOTE_FAIL` 로 포기시킨다. 실패한 B-tree insert 는 page 를 unfix 하고 `nonleaf_latch_mode = PGBUF_LATCH_WRITE` 로 바꿔 **루트부터 재시작**한다(`btree.c:28645-28654`) — 재시작 하강은 지나는 non-leaf 마다 WRITE 로 잡아 그 node 의 reader 를 직렬화한다.

SX latch 가 있다면: SX 는 SX 끼리 배타라 페이지당 승격 후보가 1명으로 직렬화되고, blocking READ→SX 승격을 금지하면 교착 사이클 자체가 성립하지 않아 SX→WRITE 승격은 "기다리면 반드시 얻는" 연산이 된다. 실패 분기와 루트 재시작이 구조적으로 사라진다.

## 흔한 오답

- "insert 2만 건이니 승격도 2만 번" — 하강 경로와 split 대상 page 수를 잊은 답. 승격은 insert 단위가 아니라 "READ로 잡았는데 고쳐야 하는 page" 단위다.
- "실패가 0이니 승격 실패 문제는 실존하지 않는다" — 단일 세션의 필연일 뿐이다. 실패 분기는 동시 세션 경쟁에서만 발동하며, 이 퀴즈는 그 빈도를 측정하지 않는다.
- "숫자가 88779와 다르니 오답" — 카운트는 오라클이 아니다. 규모(수만)와 실패 0 이 오라클이다.

## 이 실험이 증명하지 않는 것

- 승격 실패의 실제 빈도(동시 워크로드 필요 — CBRD-27196 의 baseline 측정 항목).
- SX 도입 시의 성능 이득 크기(프로토타입 비교 필요).

## 관련 장 / claim

- 5장 `chapters/05-core-workflows.html#promote-fail-restart` — CUBRID-C004(승격 분기), CUBRID-C005(재시작 fallback), CUBRID-C011(런타임 관측)
- 7장 `chapters/07-concurrency.html` — upgrade deadlock 과 SX 의 교착 회피 전제
