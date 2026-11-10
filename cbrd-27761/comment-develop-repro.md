CBRD-27325 수정(`604ab8b22`, PR #7887)이 들어간 develop에서도 같은 손실이 남는 것을 확인해 공유드립니다. 이 이슈의 "큐 크기나 재탐색 범위를 늘리는 방식은 손실을 줄일 뿐" 판단을 뒷받침하는 측정입니다.

**재현 (develop `e64a04a79` release, 기본 설정에 data_buffer_size=512M, 새 DB)**

행 수를 240,000으로 유지한 채 위쪽 절반 id를 지우고 같은 수를 다시 넣기를 5회 반복했다. 각 단계 뒤 40초 기다려 vacuum이 끝나게 했다(삭제 뒤 페이지당 평균 여유가 약 11KB로 오른 것으로 확인).

``` sql
create table seed (i int);
insert into seed values (0);
-- 18회: insert into seed select i + 2^k from seed;  (k = 0..17, 262,144 행)
create table t (id int primary key, c varchar(400), r int);
-- 압축되지 않는 384B 값
insert into t select i, sha2(to_char(i),512)||sha2(to_char(i+1000000000),512)||sha2(to_char(i+2000000000),512), 0
  from seed where i < 240000;
-- r = 1..5, nxt는 240000에서 시작해 라운드마다 120000 증가
delete from t where id >= nxt - 120000;
insert into t select i + nxt, <같은 값>, r from seed where i < 120000;
show heap capacity of t;   -- Num_pages
```

| 단계 | Num_pages (삭제 뒤 / 재삽입 뒤) | 증가 |
|---|---|---|
| 적재 | 7,273 | |
| 1회 | 7,273 / 9,607 | +2,334 |
| 2회 | 9,606 / 9,606 | 0 |
| 3회 | 9,606 / 9,992 | +386 |
| 4회 | 9,906 / 9,906 | 0 |
| 5회 | 9,906 / 10,639 | +733 |

- 행 수는 끝까지 240,000이다. 힙은 7,273장에서 10,639장으로 46% 커졌고, 마지막 평균 여유 공간은 페이지당 6,661B다(측정).
- 1회차는 삭제로 비운 약 3,600장이 있는데도 2,334장을 새로 할당했다. 재사용은 약 1,000장에 그쳤다(측정값에서 추론).
- 증가는 라운드마다 들쭉날쭉하다. 재탐색이 커서 위치와 재가동 시점에 따라 일부만 찾기 때문으로 보인다(추론).

**원인 (develop `e64a04a79` 코드)**

- vacuum이 비운 페이지는 `heap_add_bestpage`(`heap_file.c:4770`)가 후보 큐에 하나씩 넣는다. 큐(`MAX_CANDIDATES_QUEUE_SIZE` 128)가 차 있고 새 페이지 여유가 최솟값 이하이면 `candidate_queue::push`가 그냥 버린다(`bestspace.cpp:1255`). 같은 크기로 비운 페이지가 128장을 넘으면 나머지는 기록되지 않는다.
- CBRD-27325의 `bestspace::rediscover`는 지속 커서에서 64장씩 훑고, 쓸 페이지 없이 1,024장(`REDISCOVER_FRUITLESS_BUDGET`)을 지나면 꺼진다(`bestspace.cpp:1868`). 꺼진 뒤에는 다른 스레드의 `push_candidates`가 있을 때 1초(`REDISCOVER_REARM_INTERVAL`)에 한 번만 다시 켜진다(`bestspace.cpp:1708`). 꺼져 있는 동안의 INSERT는 재탐색 없이 파일을 늘리고, 커서가 비운 범위에 닿기 전에 대부분의 재삽입이 끝난다(코드에서 추론).
- 그동안 `shard::allocate`는 후보가 모자란 배치마다 `allocate_new_pages`로 파일을 늘린다(`bestspace.cpp:1048`).
- 헤더에도 같은 한계가 TODO로 적혀 있다(`bestspace.hpp:449`): "free pages beyond the budget from the cursor are missed (e.g. after a range DELETE)".

**참고: 같은 코드의 다른 사용처**

내부 실험 브랜치에서 같은 bestspace 코드를 쓰는 별도 힙(큰 값 UPDATE마다 INSERT가 일어나는 구조)에서도 같은 손실을 측정했다. 라운드마다 비운 약 1,000장 중 약 870장이 큐에서 버려졌고, 5라운드 동안 1,002장에서 2,934장으로 늘었다. 임시 완화로 (1) 큐가 버린 첫 페이지를 재탐색 시작점으로 기록하고, (2) 그 지점부터 힙 체인 한 바퀴까지 예산을 늘리며, (3) 그동안은 파일 확장 전에 재탐색을 더 돌리게 했더니 2,040장에서 멈췄다. 이 방법도 한 바퀴 스캔 비용을 INSERT가 치르는 유계 보완이라, 이 이슈의 전 페이지 맵이 들어오면 필요 없다. 참고용으로만 남긴다.

이 이슈의 인수 조건에 위 범위 DELETE 시나리오(힙 중간·뒤쪽 범위를 지운 뒤 재삽입)도 넣으면 좋겠습니다.
