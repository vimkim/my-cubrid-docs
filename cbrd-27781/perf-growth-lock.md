# U-1 측정: OOS growth lock이 동시 INSERT 처리량을 떨어뜨리는가

2026-11-11 (Asia/Seoul). PR [CUBRID/cubrid#8434](https://github.com/CUBRID/cubrid/pull/8434), [CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781) / CBRD-27925. 대상 독자: PR 작성자와 [후속 리뷰](code-review-pr8434-8e139f4/report.md)의 U-1 항목을 닫을 사람.

## 결론

- **측정 가능한 회귀 없음.** 한 OOS 파일에 페이지를 채우는 값을 16·32·64 세션이 동시에 넣을 때, head `8e139f4db`의 처리량은 base `c255c7c3b`와 구별되지 않는다. 엄격 교대 A/B 10회씩의 중앙값 차이는 N=16 −0.4%, N=32 −1.1%, N=64 +3.6%이고, 순열 검정 p는 0.88, 0.45, 0.72다. 반복 간 범위(최대 ±35%)가 차이보다 훨씬 크다.
- **이유(limiter).** base와 head 모두에서 OOS 삽입자가 가장 많이 막히는 곳은 OOS 헤더 페이지 래치다(`oos_find_best_page`가 헤더 페이지를 WRITE로 고정, 그리고 `file_get_sticky_first_page`). 이 직렬화가 growth lock보다 앞에 있어서, growth lock에 동시에 도착하는 대기자가 적다. N=64에서 head의 growth lock 대기는 서버 컨텍스트 스위치 표본의 0.9%, 헤더 페이지 래치 대기(`oos_find_best_page`와 `file_get_sticky_first_page`의 페이지 블록)는 약 18%다.
- **herd 신호 없음.** strace로 센 futex 호출은 삽입 행당 base 16.9회, head 14.9회다(N=64). 서버 전체 컨텍스트 스위치 수도 ±1% 안이다.
- **mixed(삭제와 성장이 겹침)에서는 head가 오히려 낫다.** 처리량 차이는 판단 불가지만, 삽입 문장 p99가 base 231 ms → head 37 ms(N=16), 1876 ms → 84 ms(N=64)로 줄었다(5회씩, 순위합 p=0.008). base의 pending-delete lap이 성장 경로에서 길게 막던 것을 CBRD-27925의 emptied-page set이 없앤 효과로 보인다. 이 개선은 `e01d8d576`(mid)에서 이미 나타난다.
- **수정 권고.** 측정 근거로는 per-file condvar나 "set이 비고 파일이 known이면 lock 생략"을 지금 넣을 이유가 없다. 처리량 이득이 측정 한계 아래다. 리뷰가 지적한 다른 측면, 즉 대기가 interrupt를 보지 않아 query cancel과 shutdown이 `file_alloc`이나 lap을 기다린다는 점은 이 측정이 다루지 않았다. 그쪽 수정(timed wait + interrupt 확인)은 처리량이 아니라 응답성 근거로 따로 판단해야 한다.

## 질문과 범위

리뷰 U-1: `8e139f4db` 이후 모든 OOS 페이지 할당이 파일별 growth lock을 잡고 `file_alloc`까지 유지한다. 모든 파일이 condvar 하나를 공유하고 전역 bestspace mutex 아래에서 broadcast하므로 대기자 N명이면 해제마다 O(N) 깨우기가 생긴다. 이 측정은 "한 OOS 파일에 동시에 성장하는 INSERT가 처리량을 잃는가"만 본다. cancel·shutdown 지연, 여러 OOS 파일이 condvar를 공유할 때의 교차 깨우기, 4096 overflow 뒤 lap 비용은 재지 않았다.

## 비교 대상

| 이름 | 커밋 | 성장 경로 |
| --- | --- | --- |
| base | `c255c7c3bf02eb89ae07d551b36e0e4c09934406` (리뷰한 `3e8072f56`의 rebase) | [`oos_alloc_page_with_reclaim`](https://github.com/CUBRID/cubrid/blob/c255c7c3bf02eb89ae07d551b36e0e4c09934406/src/storage/oos_file.cpp#L1946)이 [`oos_reclaim_sweep_step`](https://github.com/CUBRID/cubrid/blob/c255c7c3bf02eb89ae07d551b36e0e4c09934406/src/storage/oos_file.cpp#L1760)을 부른다. 회수할 것(pending delete)이 없으면 sweep을 claim하지 않고 바로 `file_alloc`. |
| mid | `e01d8d576ccfca0644a39df5fd10ebdaec48d534` (CBRD-27925 첫 커밋) | [`oos_reclaim_sweep_step`](https://github.com/CUBRID/cubrid/blob/e01d8d576ccfca0644a39df5fd10ebdaec48d534/src/storage/oos_file.cpp#L1804): emptied set이 비고 파일이 known이면 claim 없이 통과. 회수할 때만 sweep을 잡는다. `file_alloc`은 lock 밖. |
| head | `8e139f4dbb2635058032d0b9dafd5f624c726754` (PR head) | [`oos_alloc_page_with_reclaim`](https://github.com/CUBRID/cubrid/blob/8e139f4dbb2635058032d0b9dafd5f624c726754/src/storage/oos_file.cpp#L2095)이 매 성장마다 [`oos_reclaim_claim_growth`](https://github.com/CUBRID/cubrid/blob/8e139f4dbb2635058032d0b9dafd5f624c726754/src/storage/oos_file.cpp#L1793)로 lock을 잡고, sweep step과 `file_alloc`이 끝날 때까지 유지. 해제는 [`pthread_cond_broadcast`](https://github.com/CUBRID/cubrid/blob/8e139f4dbb2635058032d0b9dafd5f624c726754/src/storage/oos_file.cpp#L1373). |

세 리비전 모두 성장 직전에 [`oos_find_best_page`](https://github.com/CUBRID/cubrid/blob/8e139f4dbb2635058032d0b9dafd5f624c726754/src/storage/oos_file.cpp#L3116)가 OOS 헤더 페이지를 [WRITE로 고정](https://github.com/CUBRID/cubrid/blob/8e139f4dbb2635058032d0b9dafd5f624c726754/src/storage/oos_file.cpp#L3131-L3132)하고, `file_alloc`은 파일 헤더 페이지를 [WRITE로 고정](https://github.com/CUBRID/cubrid/blob/8e139f4dbb2635058032d0b9dafd5f624c726754/src/storage/file_manager.c#L5424)한다(source 근거). 따라서 base에서도 할당은 이미 파일 헤더 래치로 직렬화된다. head가 새로 직렬화하는 구간은 sweep step(set이 비면 짧다)과 `log_sysop_start/commit`, 그리고 래치 사이의 틈이다(추론).

## 환경

| 항목 | 값 |
| --- | --- |
| 장비 | Xeon Gold 5218R 2소켓, 80 논리 CPU, NUMA 2, Rocky 9 커널 5.14.0-570.30.1.el9_6, 251 GB RAM. 다른 사용자의 CUBRID 서버와 빌드가 함께 도는 공용 장비 |
| 빌드 | 리비전마다 별도 worktree `~/gh/cb/u1perf-{base,mid,head}-<sha>`, preset `release_gcc`(`RelWithDebInfo`, `-O2 -ggdb3 -DNDEBUG`), gcc 11.5.0, ccache. 설치 `~/.cub/install/u1perf-*/release_gcc` |
| `libcubrid.so.11.5` sha256 | base `ab649374…749758`, mid `639fe79b…7f81ce`, head `b8a0ed60…37f7d` |
| 서버 | server mode, 표본마다 새 DB(`createdb --db-volume-size=6G --log-volume-size=1G`, en_US.utf8, 16 KB 페이지), `data_buffer_size=2G`, `log_buffer_size=64M`, `max_clients=200`, 리비전별 포트 35101–35103. 표본이 끝나면 볼륨과 로그를 지움 |
| 클라이언트 | 세션마다 `csql -C -u dba -i <script>`, autocommit. 같은 장비 |
| 도구 | perf 5.14, strace 6.12. `perf_event_paranoid=-1`이지만 tracefs 접근 권한이 없어 `syscalls:sys_enter_futex` tracepoint는 쓸 수 없었다. 그래서 futex는 별도 진단 실행에서 `strace -c`로 셌다 |

## 부하

스크립트: [bench/u1_growth_lock.sh](bench/u1_growth_lock.sh)(표본 하나), [bench/u1_run_all.sh](bench/u1_run_all.sh)(세 리비전, 순서 회전), [bench/u1_run_ab.sh](bench/u1_run_ab.sh)(base/head 엄격 교대), [bench/u1_summarize.py](bench/u1_summarize.py)(중앙값·범위).

- 스키마: `t (id INT AUTO_INCREMENT PRIMARY KEY, sid INT, v BIT VARYING)`. 원본 `src`에 서로 다른 값 200개를 미리 만든다. 값 하나는 MD5 hex 750개를 이어 `BIT VARYING`으로 바꾼 12,000바이트로, 압축이 거의 듣지 않는다. OOS 임계(페이지/4 = 4 KB)를 넘고, 한 페이지에 하나만 들어간다.
- 매 INSERT가 새 OOS 페이지를 할당하는지 확인했다: 모든 표본에서 `SHOW HEAP OOS OF t`의 `Oos_num_user_pages` = 행 수 + 1(예: 51,200행 → 51,201 페이지).
- insert 점: N 세션이 같은 `t`에 합계 51,200행을 나눠 넣는다. 문장 하나가 `INSERT INTO t (sid, v) SELECT sid, v FROM src WHERE id BETWEEN a AND a+9`(10행) 후 commit. 점마다 `DROP TABLE`/`CREATE TABLE`로 새 OOS 파일을 만든다(파일은 known 상태로 시작). 처리량 = 51,200 / (첫 세션 시작부터 마지막 세션 끝까지의 벽시계).
- mixed 점: 한 세션으로 51,200행을 미리 넣고 5초 쉰 뒤, N/2 세션이 그 행을 10행씩 지우고(commit) 나머지 N/2 세션이 25,600행을 새로 넣는다. vacuum이 비운 페이지를 emptied set에 넣고 성장 경로가 그 set을 확인하게 하려는 점이다.
- 웜업: 표본마다 200행 한 세션.
- 오류: 모든 세션 출력에서 `error` 문자열을 세었고 전 표본 0이다. 최종 행 수도 165개 점 모두 기대값과 같다.
- 표본당 기록: 벽시계, rows/s, 삽입 문장 지연(csql이 문장마다 출력하는 실행 시간의 p50·p99), 시작·종료 load average, 서버 프로세스의 `perf stat -e context-switches,cpu-migrations,task-clock`, 서버 스레드 voluntary context switch 합.

## 결과 1: 엄격 교대 base/head 10회씩 (주 근거)

`u1_run_ab.sh`, 반복마다 순서를 뒤집음(AB, BA, …). 측정 중 1분 load average 중앙값 11–13(범위 8–60). 원자료 [bench/u1-results-ab.csv](bench/u1-results-ab.csv).

| N | base rows/s 중앙값 (최소–최대) | head rows/s 중앙값 (최소–최대) | head vs base | 같은 반복 안 head/base 비율 중앙값 | 순열 검정 p |
| --- | --- | --- | --- | --- | --- |
| 16 | 9,564 (6,951–11,973) | 9,531 (6,487–9,737) | −0.4% | 0.997 | 0.88 |
| 32 | 9,178 (6,756–11,936) | 9,080 (8,366–9,171) | −1.1% | 0.982 | 0.45 |
| 64 | 6,814 (5,327–7,673) | 7,062 (3,420–7,755) | +3.6% | 1.020 | 0.72 |

| N | 삽입 문장 p50 ms base / head | p99 ms base / head | 서버 context switch base / head |
| --- | --- | --- | --- |
| 16 | 15.2 / 14.1 | 27.1 / 24.6 | 422,910 / 427,386 (+1.1%) |
| 32 | 35.1 / 35.4 | 50.1 / 44.5 | 438,576 / 442,644 (+0.9%) |
| 64 | 76.1 / 77.1 | 197 / 162 | 461,754 / 460,416 (−0.3%) |

p99는 반복마다 수백 ms 튀는 표본이 양쪽에 다 있다(base N=64 126–525 ms, head 138–829 ms). 차이를 말할 수 없다.

## 결과 2: 세 리비전 5회씩 (회전 순서)

`u1_run_all.sh`, 반복마다 순서를 base-mid-head → head-base-mid → mid-head-base로 회전. load average 중앙값 10–21(범위 7–56). 원자료 [bench/u1-results-main.csv](bench/u1-results-main.csv).

| 점 | N | base rows/s | mid rows/s | head rows/s | head vs base | 순위합 p (head, base) |
| --- | --- | --- | --- | --- | --- | --- |
| insert | 1 | 5,057 (3,091–5,140) | 4,833 (4,576–5,052) | 4,970 (2,352–5,284) | −1.7% | 1.00 |
| insert | 8 | 8,782 (7,773–9,372) | 8,903 (7,865–9,071) | 9,153 (7,201–9,577) | +4.2% | 0.31 |
| insert | 16 | 6,930 (5,998–8,312) | 7,504 (6,933–8,152) | 5,953 (4,427–8,216) | −14.1% | 0.22 |
| insert | 32 | 4,400 (2,852–7,019) | 4,240 (3,852–6,153) | 4,006 (2,943–5,822) | −8.9% | 0.55 |
| insert | 64 | 4,306 (3,051–6,215) | 4,560 (4,005–6,048) | 3,364 (2,950–4,785) | −21.9% | 0.31 |
| mixed | 16 | 4,438 (3,591–5,354) | 3,917 (3,197–5,692) | 3,648 (3,373–4,434) | −17.8% | 0.15 |
| mixed | 64 | 3,138 (1,694–4,827) | 4,678 (4,034–7,249) | 4,574 (4,027–6,646) | +45.8% | 0.22 |

이 시리즈의 head 중앙값은 N=16–64에서 낮지만, 범위가 크게 겹치고 어느 점도 유의하지 않다. 같은 장비에서 load가 더 낮을 때 돌린 결과 1(반복 2배)에서는 그 차이가 사라졌다. 결과 2의 N≥16 처리량(4,000–7,000)이 결과 1(7,000–9,500)보다 낮은 것도 장비 부하 차이로 보인다. 결과 2만으로 회귀를 말할 수 없고, 결과 1이 그것을 반박한다.

mixed 삽입 문장 p99 (ms, 5회 중앙값과 범위):

| N | base | mid | head | 순위합 p (head, base) |
| --- | --- | --- | --- | --- |
| 16 | 231 (183–416) | 31 (20–40) | 37 (33–96) | 0.008 |
| 64 | 1,876 (1,267–2,095) | 103 (48–378) | 84 (62–99) | 0.008 |

base는 다섯 번 모두 head보다 나빴다. 같은 mixed 점에서 서버 context switch도 base가 약 20% 많다(중앙값 546k vs 455k, N=16).

## 결과 3: 어디서 막히는가 (진단 실행, 처리량 보고에는 쓰지 않음)

N=64 insert와 mixed를 base·head에서 한 번씩, 수집기를 붙여 따로 돌렸다. 수집기가 서버를 크게 느리게 하므로 이 실행의 처리량은 쓰지 않는다.

**context switch 콜스택.** `perf record -e context-switches -c 1 --call-graph dwarf,8192 -p <cub_server>`(합계 6,400행). 표본마다 사용자 스택에서 처음 맞는 CUBRID 함수로 분류했다([bench/u1_cs_classify.py](bench/u1_cs_classify.py), 결과 [bench/u1-diag-cs-classified.txt](bench/u1-diag-cs-classified.txt)). frame pointer 기반 `-g`는 glibc에서 끊겨 쓸 수 없었다.

| 분류 (insert N=64) | base | head |
| --- | --- | --- |
| 네트워크 수신·worker 유휴 | 47.8% | 47.1% |
| `oos_find_best_page` 안(헤더 페이지 래치, bestspace) | 21.8% | 21.5% |
| 그 밖의 page buffer 래치(대부분 btree) | 10.9% | 11.3% |
| 로그 flush·commit 대기 | 6.4% | 6.6% |
| `file_alloc` | 1.3% | 1.1% |
| **growth lock 대기 (`oos_reclaim_claim_growth`)** | – | **0.9%** |
| 표본 수 | 48,857 | 51,371 |

page buffer 블록(`pgbuf_block_bcb`) 표본을 호출자로 다시 나누면 head에서 `oos_find_best_page`의 헤더 고정 5,311, `file_get_sticky_first_page` 3,774, `file_alloc` 93이다. base도 5,227 / 3,615 / 101로 같다. 즉 동시 OOS 성장의 직렬화 지점은 base부터 OOS 헤더 페이지이고, head의 growth lock은 그 뒤에서 적은 수의 대기자만 만난다.

mixed N=64에서는 head의 growth lock 대기가 3.9%, base의 sweep 대기(`oos_reclaim_sweep_step`, base의 single-flight sweep도 같은 condvar를 쓴다)가 3.0%다. 둘 다 헤더·page buffer·로그 대기보다 작다.

**futex 호출 수.** `strace -f -c -e trace=futex -p <cub_server>`(합계 12,800행, [bench/u1-diag-strace-futex.txt](bench/u1-diag-strace-futex.txt), [bench/u1-results-diag-strace.csv](bench/u1-results-diag-strace.csv)).

| 점 | base futex 호출 (행·작업당) | head futex 호출 (행·작업당) |
| --- | --- | --- |
| insert N=64 (12,800행) | 216,568 (16.9) | 191,293 (14.9) |
| mixed N=64 (삽입 6,400 + 삭제 12,800) | 242,833 (12.6) | 225,512 (11.7) |

broadcast herd가 의미 있게 일어났다면 head 쪽 futex가 늘었어야 한다. 늘지 않았다.

## 해석과 수정 판단

- U-1이 걱정한 O(N) 깨우기는 대기자가 많을 때만 비용이 된다. 이 부하에서는 OOS 헤더 페이지 래치가 앞에서 삽입자를 줄 세우므로 growth lock에 쌓이는 대기자가 적다(추론, 결과 3의 표본 비율이 근거). 헤더 래치 직렬화가 그대로인 한 growth lock 개선의 처리량 효과는 상한이 작다. N=64 head에서 growth lock 대기 표본이 전체 블록의 0.9%이므로, 그것을 없애도 처리량 이득은 그 정도 크기를 넘기 어렵다.
- per-file condvar: 한 파일만 성장하는 이 부하에서는 효과가 없다. 여러 OOS 파일이 동시에 성장할 때 다른 파일의 해제로 깨어나는 헛깨우기를 줄이지만, 그 경우는 재지 않았다.
- "set이 비고 파일이 known이면 lock 생략": 순수 INSERT 경로에서 lock을 빼는 수정이다. 측정 근거로는 이득이 잡음 아래다. 게다가 head가 lock을 `file_alloc`까지 잡는 이유(다른 성장자가 check와 allocation 사이에 sector를 가져가지 못하게 함)를 다시 증명해야 하므로, 처리량만으로는 권하지 않는다.
- timed wait + interrupt 확인: 처리량과 무관하다. cancel·shutdown 응답성 문제는 실제로 있고(source 근거, 리뷰 U-1), 대기 시간은 한 성장자의 `file_alloc`이나 lap 길이에 묶인다. 이 측정에서 head의 삽입 문장 p99는 N=64에서 수백 ms 수준이므로 정상 부하의 대기는 짧다. 긴 lap(4096 overflow 뒤 전 파일 lap)에서의 대기는 재지 않았다.
- mixed에서 head(와 mid)의 p99 개선은 실재한다(p=0.008, 5/5). 이 PR의 성능 근거로 쓸 수 있다.

## 한계

- 공용 장비다. 측정 중 다른 사용자의 서버와 빌드가 돌았고 1분 load average가 7–60 사이에서 움직였다. 교대·회전 순서로 양쪽에 고르게 나눴지만 반복 간 범위가 ±35%에 이른다. 이보다 작은 차이(대략 5% 미만)는 이 측정으로 판단할 수 없다.
- 클라이언트(csql)와 서버가 같은 장비에 있고, 세션은 closed loop다. 서버 context switch의 절반이 네트워크 수신 대기라 클라이언트 왕복도 처리량을 제한한다. 문장당 10행으로 왕복 비중을 줄였다.
- 한 OOS 파일만 재었다. 여러 테이블(OOS 파일)이 동시에 성장할 때의 condvar 공유 효과, cancel·shutdown 지연, overflow 뒤 lap 비용은 범위 밖이다.
- futex tracepoint를 쓸 수 없어 futex 수는 strace로만 셌다. strace는 서버를 약 8배 느리게 해서(insert N=64 base 776 rows/s) 경합 모양 자체를 바꿀 수 있다. context switch 수(perf stat)는 본 측정에서 함께 기록했다.
- mid(`e01d8d576`)는 결과 2에만 있다. mid는 순수 INSERT에서 base와 같은 경로(lock 없음)인데 결과 2의 insert 처리량도 base와 구별되지 않았다(순위합 p ≥ 0.42).

## 재현

```bash
# 리비전마다 (base 예시)
git -C ~/gh/cb/develop worktree add -b u1perf-base-c255c7c3b ../u1perf-base-c255c7c3b c255c7c3b
cd ~/gh/cb/u1perf-base-c255c7c3b
just -f ~/my-cubrid/cubrid-justfiles/justfile -d . prepare-build
just preset release_gcc
direnv exec . just configure-build-and-install

# 측정 (bench/ 에서)
./u1_run_all.sh ~/.cub/u1perf/main 5      # 결과 2
./u1_run_ab.sh  ~/.cub/u1perf/ab 10       # 결과 1
python3 u1_summarize.py ~/.cub/u1perf/ab/results.csv
# 진단 (결과 3)
DIAG=cs     PORT=35103 CONC=64 MIXED=64 TOTAL=6400  ./u1_growth_lock.sh <install> ~/.cub/u1perf/diag-cs head 1
DIAG=strace PORT=35103 CONC=64 MIXED=64 TOTAL=12800 ./u1_growth_lock.sh <install> ~/.cub/u1perf/diag-strace head 1
perf script -i <run>/ins-64/cs.data -F tid,ip,sym > cs.txt && python3 u1_cs_classify.py cs.txt
```

`perf record` 원자료(표본당 약 400 MB)는 Git에 넣지 않았고 측정 뒤 지웠다.

## 남은 로컬 자료

- 측정 DB의 볼륨과 로그는 표본마다 지웠다. 세 release 빌드 디렉터리와 설치 경로 `~/.cub/install/u1perf-*`도 지웠다.
- `~/.cub/u1perf/`(172 MB): 표본별 세션 스크립트·출력·지연 목록, 진단 strace 출력. 이 문서의 CSV와 요약 파일이 그 내용을 담으므로 지워도 된다.
- 소스 worktree `~/gh/cb/u1perf-{base-c255c7c3b,mid-e01d8d576,head-8e139f4db}`(브랜치 같은 이름): 추적 변경 없음. submodule이 있어 `git worktree remove`가 `--force` 없이는 거부한다. 세 커밋은 `CBRD-27781-postpone-commit`에서 모두 닿는다.
