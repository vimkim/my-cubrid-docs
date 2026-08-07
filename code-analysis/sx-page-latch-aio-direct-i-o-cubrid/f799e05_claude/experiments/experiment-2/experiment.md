# experiment-2: flush 깔때기는 실제로 실행되고, 무엇으로 관측되는가

## Question

CUBRID 의 data page flush(사본을 떠서 WAL 선행 후 디스크에 쓰는 `pgbuf_bcb_flush_with_wal` 깔때기)가 실제로 실행됨을 어떤 카운터로 관측할 수 있는가? 이름상 가장 그럴듯한 `Num_data_page_flushed` 는 신뢰할 수 있는가?

## Hypothesis

대량 insert 로 dirty page 를 만들고 checkpoint 를 강제하면 flush 깔때기가 실행된다. dirty 생성은 사용자 스레드 소관이라 per-transaction histogram 에 잡히고, 물리 쓰기는 전역 카운터 `Num_data_page_iowrites`(DWB 경로)로 잡힌다. `Num_data_page_flushed` 는 victim flush 전용이라 움직이지 않을 것이다(소스 분석 기반 예측).

## Setup

- experiment-1 과 동일한 `sx_latch_lab` 환경.
- 전역 카운터는 watcher 가 붙어 있어야 누적되므로(stats_on=no 기본), `start_watcher.sh` 가 interval statdump 를 백그라운드로 붙인다(exp2-watcher-start).
- 사전 상태 기록: exp2-statdump-before.

## Action

1. `csql -u dba sx_latch_lab -i flush_workload.sql` 2회 (exp2-obs-1/2) — 10,000건 insert + `;.dump_hist`.
2. `cubrid backupdb -D <scratch> -C -r sx_latch_lab` (exp2-backupdb-checkpoint) — 동기적 checkpoint 를 강제해 dirty page flush 를 유발.
3. `cubrid statdump sx_latch_lab` (exp2-statdump-after).
4. watcher 정리: exp2-watcher-stop, 그리고 wrapper-자식 PID 문제를 바로잡은 exp2-watcher-stop-2 (아래 Cleanup).

## Observation (raw: evidence/runs/exp2-*/stdout.txt)

- exp2-obs-1: `Num_data_page_dirties = 102218`; exp2-obs-2: `102158`.
- `Num_data_page_iowrites`: before 229 → after 1163 (+934).
- `Num_data_page_flushed`: before 0 → after 0.

## Interpretation

- flush 깔때기는 실행되었다: +934 페이지가 DWB 경로로 물리 기록되었다.
- `Num_data_page_flushed` 는 checkpoint flush 를 세지 않는다 — 증가 지점이 `pgbuf_flush_victim_candidates`(page_buffer.c:4167) 하나뿐이라는 소스 사실의 런타임 확인이다. 같은 불일치를 CUBRID JIRA page buffer EPIC 에 결함 D6 으로 기록해 두었다(발췌 사본: research/jira/CBRD-27193.md). flush 관측 지표를 고를 때 이름만 믿으면 안 된다는 교훈이 이 보고서 performance-observability 장의 핵심 사례다.
- 시도 과정에서 csql sysadm `;checkpoint` 는 비동기 요청이라 per-tran histogram 으로는 flush 를 관측할 수 없었고(카운터는 데몬 스레드에서 증가), 체크포인트 데몬의 페이싱 때문에 수 분간 완료되지 않는 경우도 관찰했다. 그래서 동기적 강제 수단으로 backupdb 를 채택했다.

## Alternative explanations

manifest.json 참조. 핵심: iowrites 의 살아 있는 증가 지점은 네 곳(DWB 경로 double_write_buffer.cpp:2115/2150/2339 + 비-DWB 직접 쓰기 분기 page_buffer.c:10893)이고, backupdb 아카이브 쓰기는 fileio_write_backup 계열이라 이들 지점을 지나지 않는다. checkpoint flush 와 flush 데몬 자발 flush 는 구분하지 못한다(둘 다 같은 깔때기).

## Observer effect

interval watcher 는 60초마다 통계를 읽을 뿐 카운터를 리셋하지 않는다. histogram/perfmon 수집 비용은 experiment-1 과 동일하게 존재하나 카운트 사실 자체에는 영향 없다.

## Cleanup

- `stop_watcher.sh`(exp2-watcher-stop)는 watcher.pid 를 종료했으나, `cubrid statdump` 가 wrapper 로 실제 statdump 를 자식으로 띄우는 탓에 자식 프로세스가 살아남는 문제를 발견했다. `kill_stray_watchers.sh`(exp2-watcher-stop-2)가 이 실험 소유의 cmdline 패턴만 정확히 골라 종료했고 잔여 0 을 확인했다.
- 백업 아카이브(scratch 디렉터리)는 삭제했다. runner 가 만든 `sx_flush_t` 테이블과 데이터베이스 전체는 모든 실험/퀴즈 종료 후 exp-final-server-stop / exp-final-deletedb 로 삭제했다.
