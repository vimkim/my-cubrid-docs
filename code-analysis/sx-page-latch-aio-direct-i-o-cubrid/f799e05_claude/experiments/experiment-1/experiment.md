# experiment-1: B-tree insert는 page latch 승격을 실제로 사용하는가

## Question

CUBRID B-tree insert가 READ로 하강하다가 수정 순간에만 WRITE로 승격한다는 소스 분석(`btree.c` 의 `pgbuf_promote_read_latch` 호출 11곳)이 실제 런타임에서 관측되는가? 승격 빈도는 어느 규모인가?

## Hypothesis

단조 증가 key 20,000건 insert는 leaf split 과 non-leaf 수정을 반복 유발하므로, promote 성공 카운터가 수만 단위로 증가하고, 단일 세션(경쟁 없음)이므로 실패는 0이다.

## Setup

- 기준 소스 f799e05d 로 빌드된 debug_gcc 바이너리 (evidence/runtime-tools-baseline.json).
- 실험 전용 데이터베이스 `sx_latch_lab` 생성(exp-setup-createdb), 서버 기동(exp-setup-server-start).
- CUBRID 통계는 기본값(stats_on=no)에서 watcher가 있어야만 수집된다. 이 실험은 csql 세션 자체의 per-transaction histogram(`;set communication_histogram=yes` + `;.hist on`)을 watcher로 사용해, 관측을 실행과 같은 csql 프로세스 안에 내장했다.

## Action

`csql -u dba sx_latch_lab -i workload_hist.sql` 3회 (exp1-obs-1/2/3). runner는 PRIMARY KEY 테이블 생성 → 20,000건 insert → COUNT 확인 → `;.dump_hist` → 테이블 정리.

## Observation (raw: evidence/runs/exp1-obs-*/stdout.txt)

| run | Num_btree_inserts | promote_success | promote_fail |
|---|---|---|---|
| exp1-obs-1 | 20024 | 89587.00 | 0.00 |
| exp1-obs-2 | 20012 | 88779.00 | 0.00 |
| exp1-obs-3 | 20012 | 88779.00 | 0.00 |

(첫 실행의 insert 12건 초과분은 첫 DDL 이 유발한 카탈로그 B-tree insert 다. 수치는 evidence/runs/exp1-obs-*/stdout.txt 원문과 일치한다.)

## Interpretation

- B-tree insert 경로는 승격을 대량 사용한다: insert 1건당 약 4.4회. "SX 도입이 승격 경로를 대체한다"는 논의가 실존하는 hot path를 다루고 있음을 보여 준다.
- 실패 0은 단일 세션의 필연이다. 실패 분기(경쟁 promoter, ONLY_READER 위반)는 동시 세션에서만 발동하며 이 실험은 그 빈도를 측정하지 않는다 — 실운영 실패율 baseline은 CBRD-27196 의 측정 항목으로 남는다.

## Alternative explanations

manifest.json 의 alternative_explanations_ko 참조. 요지: 전용 DB + 단일 세션 + per-tran histogram이라 다른 작업의 승격이 섞일 수 없고, 카운터-이벤트 결합은 소스로 확인했다.

## Observer effect

histogram 수집 자체가 각 perfmon 지점에 카운터 증가 비용을 더한다(관측 없는 실행보다 느릴 수 있음). 승격 "횟수"는 수집 여부와 무관하므로 이 실험의 결론에는 영향이 없다.

## Cleanup

runner가 마지막에 `DROP TABLE sx_promote_t` 를 수행한다(자체 정리). 데이터베이스 전체는 모든 실험/퀴즈 종료 후 exp-final-server-stop / exp-final-deletedb 로 삭제했다.

## 부수 관측 (stats_on 게이트)

최초 시도(exp1-run-1~3 + exp1-statdump-before/after)는 histogram 없이 실행했고 모든 카운터가 0이었다. 이는 CUBRID 기본 설정(stats_on=no, PRM_HIDDEN)에서 watcher가 없으면 perfmon 수집 자체가 꺼져 있음을 보여 주는 관측-장치 대조군 증거다 (perf_monitor.c:3201-3206).
