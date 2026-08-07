# experiment-1 기대 오라클

단일 csql 세션에서 `workload_hist.sql` 을 실행하면 `;.dump_hist` 출력이 다음 불변식을 만족해야 한다.

1. `Num_btree_inserts` ≈ 20,012~20,024 (20,000 데이터 행 + 카탈로그 등 소량; 첫 실행이 약간 크다).
2. `Data_page_total_promote_success` > 0 — B-tree insert 하강이 non-leaf 수정 순간마다 `pgbuf_promote_read_latch` 를 호출한다는 직접 증거. 관측값은 88,779~89,587 (insert 1건당 약 4.4회).
3. `Data_page_total_promote_fail` == 0 — 단일 세션에는 경쟁 reader가 없어 승격이 항상 제자리 분기(page_buffer.c:2929)로 성공한다.

타이밍이나 정확한 카운트 값은 오라클이 아니다. 값은 page 배치에 따라 수 % 변동한다(obs-1/2/3 실행 순: 89587/88779/88779).
