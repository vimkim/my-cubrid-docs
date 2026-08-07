# quiz-2 정답과 해설

## 정답

1. `Num_data_page_dirties` 는 **수만~십만대**다(기준 빌드 관측값 약 102,000). insert 는 data page 와 index page 를 반복해서 dirty 로 만들고, 같은 page 를 여러 번 dirty 처리해도 매번 센다.
2. `Num_data_page_flushed` 는 **0** 이다. checkpoint 가 dirty page 를 실제로 디스크에 밀어냈는데도 0 이다.
3. `Num_data_page_iowrites` 는 **수백~천 단위로 증가**한다(기준 빌드 관측 229 → 1163). 이것이 실제 물리 flush 를 반영하는 카운터다.

## 인과 메커니즘

- **watcher 없이는 0**: CUBRID 는 `stats_on=no` 가 기본(숨김 파라미터)이라, watcher(interval `cubrid statdump`, csql `;.hist on` 등)가 붙어 있는 동안에만 perfmon 카운터를 누적한다(`perf_monitor.c:3201-3206` 부근). 그래서 run.sh 가 먼저 watcher 를 붙인다.
- **flushed=0 의 진실**: `Num_data_page_flushed`(PSTAT_PB_NUM_FLUSHED)의 증가 지점은 소스 전체에서 `pgbuf_flush_victim_candidates`(page_buffer.c:4167) **한 곳**뿐이다. 즉 이 카운터는 "victim 후보 flush"만 세고, checkpoint flush 는 세지 않는다. 이름만 보면 모든 data page flush 의 지표 같지만 아니다 — 이 보고서가 소스와 런타임으로 독립 확인한 불일치이고, CUBRID JIRA page buffer EPIC 에도 결함 D6 으로 기록되어 있다(발췌 사본: research/jira/CBRD-27193.md). 이 퀴즈가 그것을 직접 재현한다.
- **iowrites 가 진짜 지표**: `Num_data_page_iowrites` 의 살아 있는 증가 지점은 네 곳이다 — DWB(Double Write Buffer) 쓰기 경로 세 곳(`double_write_buffer.cpp:2115/2150/2339`)과, DWB 미사용 시 깔때기가 데이터 볼륨에 직접 쓰는 분기 한 곳(`page_buffer.c:10893`). checkpoint flush 든 victim flush 든 모든 data page 물리 쓰기는 `pgbuf_bcb_flush_with_wal` 깔때기를 지나 이 네 지점 중 하나에서 집계되므로, DWB 활성 여부와 무관하게 이 카운터가 물리 flush 를 반영한다. (`page_buffer.c:4873` 의 다섯째 지점은 `ENABLE_UNUSED_FUNCTION` 아래라 컴파일되지 않는다.) 이 실험 환경에서는 DWB 가 활성이었다(statdump 의 `Num_DWB_flush_block` &gt; 0).
- **사본 flush 구조**: 깔때기는 BCB mutex 아래에서 page 의 16KiB 사본을 뜨고(`page_buffer.c:10820`) mutex 를 풀어 준다. 이후 디스크 I/O 는 사본으로 진행되므로 writer 는 I/O 동안에도 frame 을 자유롭게 수정할 수 있고, 새 수정은 DIRTY 재설정으로 추적된다. buffered write 는 write() 시스템콜이 반환되는 순간 kernel 이 데이터를 이미 복사해 갔으므로 이 구조가 성립한다. direct I/O/AIO write 는 시스템콜 반환 후에도 kernel/DMA 가 사용자 버퍼를 계속 읽을 수 있어, "사본" 또는 "I/O 내내 frame 불변 보장(SX 등가 latch)" 중 하나가 필수가 된다 — 사본을 유지하면 zero-copy 라는 direct I/O 의 이점이 반감되므로, InnoDB 와 PostgreSQL 20devel 은 SX 보유 쪽으로 수렴했다.

## 흔한 오답

- "checkpoint 됐으니 flushed 가 커져야 한다" — 이름을 믿은 답. 카운터의 증가 지점을 소스에서 확인하는 습관이 이 퀴즈의 목적이다.
- "iowrites 는 backupdb 의 아카이브 쓰기다" — 아카이브 쓰기는 `fileio_write_backup` 계열의 별도 경로로 진행되어 위 네 증가 지점 중 어느 것도 지나지 않는다. 반대로 "iowrites 는 DWB 전용 카운터다"라고 답했다면 절반만 맞다 — DWB 를 끈 환경에서는 직접 쓰기 분기(`page_buffer.c:10893`)가 같은 카운터를 올린다.
- "statdump 를 안 붙여도 서버가 알아서 센다" — stats_on=no 기본값에서는 세지 않는다.

## 이 실험이 증명하지 않는 것

- checkpoint flush 와 flush 데몬 자발 flush 의 구분(둘 다 같은 깔때기).
- 사본 비용(memcpy)의 CPU 비중 — perf 프로파일 필요(CBRD-27196 측정 항목).

## 관련 장 / claim

- 6장 `chapters/06-flush-frame-stability.html#flush-frame-stability` — CUBRID-C007(사본 flush), CUBRID-C012(런타임 관측)
- 11장 `chapters/11-performance-observability.html` — 카운터 의미와 관측 함정
- 9장 `chapters/09-policies-algorithms.html` — 사본 flush vs SX 직접 flush 트레이드오프
