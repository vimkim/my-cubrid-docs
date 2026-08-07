# experiment-2 기대 오라클

1. 각 runner 실행(`flush_workload.sql`)의 `;.dump_hist` 출력: `Num_data_page_dirties` > 0 (관측값 약 102,000). 10,000건 insert가 data/index page 를 dirty 로 만든다는 직접 증거.
2. `exp2-statdump-after` 대 `exp2-statdump-before`: `Num_data_page_iowrites` 증가 (관측 229 → 1163). 이 카운터의 살아 있는 증가 지점은 네 곳 — DWB 쓰기 경로(`double_write_buffer.cpp:2115/2150/2339`)와 비-DWB 직접 쓰기 분기(`page_buffer.c:10893`) — 이며, 이 실험 환경에서는 DWB 활성이 확인되므로(`Num_DWB_flush_block` &gt; 0) 증가분은 DWB 경로 집계다. 어느 쪽이든 flush 깔때기 `pgbuf_bcb_flush_with_wal` 이 실행되었다는 증거다.
3. `Num_data_page_flushed` 는 두 시점 모두 0 — 이 카운터는 victim flush(`pgbuf_flush_victim_candidates`, page_buffer.c:4167)에서만 증가하므로 checkpoint 유발 flush 를 세지 않는다. 이름과 달리 "모든 data page flush"의 지표가 아니라는 사실의 런타임 확인이며, 같은 불일치가 JIRA 발췌 사본 `research/jira/CBRD-27193.md` 의 D6 항목에 기록되어 있다.

정확한 수치는 오라클이 아니다. dirty 수는 수백 단위로, iowrites 델타는 워크로드/DWB 배치에 따라 변동한다.
