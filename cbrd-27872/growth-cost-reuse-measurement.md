# OOS 성장 비용 측정: 2단계(재사용 우선) 대 1단계

2026-11-11, Asia/Seoul. Work878. [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872), [CBRD-27925](https://jira.cubrid.org/browse/CBRD-27925).

목표는 OOS 파일이 churn에서 한없이 커지지 않으면서 INSERT와 UPDATE가 느려지지 않는 것이다. 이 보고서는 2단계(재사용 우선)가 이 목표를 해치지 않는지 잰다. 독자는 2단계(`b8a7e5d74`)를 진행할지 정할 사용자와, 2단계 구현을 리뷰할 사람이다. 1단계 측정과 harness는 [growth-cost-measurement.md](growth-cost-measurement.md)에 있다. 이 보고서는 같은 harness로 2단계를 1단계와 비교한다.

## 질문과 결론

질문은 둘이다. 2단계는 INSERT와 UPDATE가 1단계보다 느리지 않은가. churn 뒤 파일 크기(sector 수와 cycle별 peak 페이지)는 1단계만큼 유지되는가.

**결론: 단건 INSERT와 파일 크기는 통과했다. 빈 페이지가 수천 개 쌓이는 대량 UPDATE는 통과하지 못했다. 이 구현 그대로는 진행을 권하지 않는다. 느려지는 원인은 좁고 국소적인 코드(성장마다 집합 복사)로 보인다.** 모든 수치는 측정함이고, 원인 설명에는 측정함, 코드를 읽어서 안 것, 추정을 따로 표시했다.

1. **단건 INSERT 지연은 1단계와 구별되지 않는다 (측정함).** 재시작 첫 INSERT, 삭제 뒤 INSERT, 일반 INSERT, 동시 8 세션 INSERT 모두 중앙값 차이가 서버 실행 사이 변동(2~4 ms) 안에 있다. 두 run을 합친 짝지은 비교에서 어느 항목도 부호 검정 p가 0.21보다 작지 않았다(아래 표). 1 ms 이하의 차이는 이 장비에서 가릴 수 없다. 2단계는 삭제 뒤 INSERT가 dirty 페이지를 18개에서 9개로 줄이고, 로그 레코드를 INSERT 1000건당 약 10,200개에서 6,200개로 줄였다.
2. **대량 UPDATE는 emptied 페이지 집합이 클수록 느려진다 (측정함).** 이 비용은 fast path를 없앤 첫 커밋(`5d7eda23c`)에서 이미 생기고, 제자리 재사용(`b8a7e5d74`)이 만든 것이 아니다. churn 테이블을 6,000행으로 키우면 cycle 2 이후 UPDATE 문장이 1단계 372 ms, 2단계 980 ms였다(2.6배, 범위가 겹치지 않음). `perf`로 보면 2단계 서버 CPU의 22%가 `std::set<VPID>` 삽입과 순회이고, 1단계에는 이 심볼이 없다. 원인은 `oos_reclaim_check_emptied`가 성장 한 번마다 emptied 집합 전체를 `examined`와 `batch`에 복사하는 것이다(코드를 읽어서 안 것). 성장 횟수와 집합 크기가 함께 커지므로 문장 비용의 증가분은 둘의 곱에 가깝다는 것이 코드가 주는 예측이다. 집합 상한은 4,096쪽이다.
3. **파일 크기는 유지되지만 1단계와 같지는 않다 (측정함).** `5d7eda23c`부터 나타난다. 2단계의 cycle별 peak는 cycle 1이 2,001쪽, cycle 2부터 20까지 2,101쪽이다(+100쪽, +5.0%). 허용치 max(2쪽, 10%) = 201쪽 안이고 누적되지 않는다. sector는 1단계 32, 2단계 33으로 한 개 많다(1 sector = 64쪽). ADR-0009 결정 4의 sector 조항을 허용치 없이 읽으면 33은 첫 peak(2,001쪽 = 32 sector)를 1 sector 넘는다.
4. **drain이 오래 걸린다 (측정함, 원인 모름).** `5d7eda23c`부터 나타난다. cycle 2 이후 UPDATE 뒤 vacuum이 옛 chunk를 모두 지울 때까지 1단계는 0.34 s, 2단계는 2.4 s가 걸렸다. 같은 로그를 큰 filler 한 번으로 밀면 두 빌드 모두 즉시 끝난다.
5. **요청서의 기준선 가정이 틀렸다 (측정함).** `e8e714dae`와 `94ed2ea46`은 같은 동작이 아니다. 그래서 run을 둘 돌렸다. 아래 "기준선 정정"을 먼저 읽을 것.

**후속 (같은 날 저녁):** 부모 세션이 `f8cdfca747`로 복사를 고쳤고 같은 시험으로 다시 쟀다. 6,000행 UPDATE는 1단계와 같아졌고(339 대 379 ms) `perf`의 set 연산은 22%에서 0.4%로 줄었으며 단건 INSERT 수치는 그대로다. 로그 block 가설도 시험했다. drain 지연이 로그 완료에 의존한다는 부분은 확인되고, 100쪽과 1 sector가 늦은 vacuum 때문이라는 부분은 반박됐다. 아래 "수정판 `f8cdfca747`"와 "로그 block 가설 시험" 절을 볼 것. 이 위의 결론 문장은 `b8a7e5d74` 기준이다.

복사를 고친 뒤 같은 시험(`churn_scale.py`, 6,000행)으로 다시 재고 진행하기를 권했다(수정은 부모 세션이 했다). 사용자가 정할 일은 셋이다. 집합 복사를 고친 뒤에 진행할지. sector 조항을 허용치 안에서 읽을지. drain 지연의 원인을 확인할지.

## 기준선 정정

요청서는 1단계를 `e8e714dae`로 재고, 이후 head `94ed2ea46`이 "busy 페이지 경로의 error stack 격리만 더하므로 이 harness에서는 같은 동작"이라고 가정했다. 이 가정은 `8e139f4db`에서 `94ed2ea46`까지는 맞고(`oos_file.cpp` 15줄과 단위 테스트), `e8e714dae`에서 `94ed2ea46`까지는 맞지 않다. `e8e714dae`는 옛 CBRD-27781 줄 위에 있고, 2단계(`b8a7e5d74`)는 다시 쓴 줄 위에 있다.

| 비교 | `src/` 차이 | 확인 |
| --- | --- | --- |
| `e8e714dae` 대 `8e139f4db` (같은 1단계 내용, 다른 base) | 8 파일: `vacuum.c` 181줄, `vacuum_oos.cpp` 130줄, `oos_file.cpp`, `error_code.h`, `fault_injection.c` 등 | `git diff --stat e8e714dae 8e139f4db -- src` |
| `8e139f4db` 대 `94ed2ea46` | `oos_file.cpp` 15줄과 `test_oos_growth_sweep.cpp` | `git diff --stat 8e139f4db 94ed2ea46` |
| `e8e714dae` 대 `b8a7e5d74` | 9 파일, 723줄 추가, 772줄 삭제 | `git diff --stat e8e714dae b8a7e5d74 -- src` |

그래서 `94ed2ea46`을 따로 빌드해(`stage1h`) 2단계와 같은 base에서 비교했다. 결론은 `stage1h` 대 `stage2` 비교(run 2)를 기준으로 하고, 요청한 `e8e714dae` 대 `stage2`(run 1)는 같은 harness의 두 번째 표본으로 함께 싣는다. 두 비교에서 2단계가 두 번 측정된 셈이다. 두 run의 결과는 같은 방향이다.

## 비교 대상

| 이름 | 커밋 | `cubrid --version` | worktree | 설치 |
| --- | --- | --- | --- | --- |
| stage1 | `e8e714dae` (1단계, 옛 base. run 1) | 11.5.0.2797-e8e714d, 2026-11-09 16:40 | `/home/vimkim/gh/cb/CBRD-27872-after2` | `~/.cub/install/CBRD-27872-after2/release_gcc` |
| stage1h | `94ed2ea46` (1단계 head, 2단계의 base. run 2) | 11.5.0.2801-94ed2ea, 2026-11-11 15:49 | `/home/vimkim/gh/cb/CBRD-27872-after2h` | `~/.cub/install/CBRD-27872-after2h/release_gcc` |
| stage2a | `5d7eda23c` (fast path 제거, 아직 dealloc 기반 성장. 귀속용) | 11.5.0.2802-5d7eda2, 2026-11-11 16:42 | `/home/vimkim/gh/cb/CBRD-27872-after2m` | `~/.cub/install/CBRD-27872-after2m/release_gcc` |
| stage2 | `b8a7e5d74` (2단계, 재사용 우선) | 11.5.0.2803-b8a7e5d, 2026-11-11 15:01 | `/home/vimkim/gh/cb/CBRD-27872-after3` (수정판 측정 때 아래 행으로 옮김) | 복사본 `~/.cub/install/CBRD-27872-after3-b8a7e5d74/release_gcc` |
| stage2fix | `f8cdfca747` (`b8a7e5d74` 위에 집합 복사 제거) | 11.5.0.2804-f8cdfca, 2026-11-11 17:10 | `/home/vimkim/gh/cb/CBRD-27872-after3` (detached, 위 행의 같은 worktree) | `~/.cub/install/CBRD-27872-after3/release_gcc` |

네 빌드 모두 detached worktree에 로컬 수정이 없고, `release_gcc` preset(RelWithDebInfo, `-O2 -ggdb3 -DNDEBUG`), `/usr/bin/g++` 11.5.0(ccache 경유)이다. 빌드는 `just prepare-build`, `just preset release_gcc`, `direnv exec . just configure`, `direnv exec . just build-and-install` 순서로 했고 3rdparty 다운로드는 실패하지 않았다. `git diff --stat`는 `e8e714dae`와 `94ed2ea46` 사이에서 `3rdparty`, `cmake`, `CMakeLists.txt`가 같음을 보였다. 빌드가 올바른 소스인지 `libcubridsa.so`의 심볼로 확인했다. 2단계가 지우는 함수 세 개(`oos_reclaim_empty_pages`, `oos_try_reclaim_page_internal`, `oos_alloc_page_with_reclaim`)의 이름과 일치하는 심볼 수가 `e8e714dae` 10개, `94ed2ea46` 6개, `5d7eda23c` 4개(fast path 함수만 없음), `b8a7e5d74` 0개다.

장비는 1단계 보고서와 같다(Xeon Gold 5218R 80코어, 커널 5.14.0-570.30.1, DB는 NVMe XFS `/mnt/nvme/data-5`). 다른 사용자의 작업이 함께 돌았다. 셸에 있던 디버그 worktree의 `CUBRID_*` 환경 변수(`CUBRID_CUBRID_PORT_ID=41272` 포함)는 모두 지우고 돌렸다. 지우지 않으면 서버가 디버그 worktree의 포트로 올라간다.

## 방법

harness는 [bench/growth_cost.py](bench/growth_cost.py), 요약은 [bench/summarize.py](bench/summarize.py)다. 1단계 보고서의 DB(t 20,000행, u 40,000행, p, c)와 설정(버퍼 256M, 볼륨 2G)과 항목 정의를 바꾸지 않았다. 파라미터도 같다. 두 빌드를 round마다 번갈아 돌았고(A B, B A, ...) 서버는 한 번에 하나만 떴다. 이번에는 두 빌드라서 포트 충돌이 없었고 중단 없이 끝났다.

```sh
# run 2 (기준). run 1은 stage1=...after2...=e8e714dae, 출력 /mnt/nvme/data-5/tmp/w878/measure
python3 -I -B cbrd-27872/bench/growth_cost.py --out /mnt/nvme/data-5/tmp/w878/measure-h \
  --build stage1h=$HOME/.cub/install/CBRD-27872-after2h/release_gcc=94ed2ea46 \
  --build stage2=$HOME/.cub/install/CBRD-27872-after3/release_gcc=b8a7e5d74 \
  --create --rounds 8 --iters 5 --conc-iters 2 --churn-reps 4 --churn-cycles 6
python3 -I -B cbrd-27872/bench/growth_cost.py --out ... --build ... --build ... --rounds 10 --iters 0 --plain 30
python3 -I -B cbrd-27872/bench/summarize.py results.csv
python3 -I -B cbrd-27872/bench/paired_rounds.py r1.csv stage1 stage2 r2.csv stage1h stage2
python3 -I -B cbrd-27872/bench/churn_peak.py results.csv
```

표본 수는 1단계 재측정과 같다. 삭제 항목 40회(8 round × 5), 동시 INSERT 16회 × 8 세션, 재시작 18회, 일반 INSERT 10 round × 30, churn 4회 × 6 cycle이다. 줄인 것이 없다.

추가로 돌린 측정은 다음과 같다. 모두 같은 DB 파일 위에서 한 번에 서버 하나로 돌았다.

| 측정 | 명령 | 목적 |
| --- | --- | --- |
| cycle 수별 sector | `growth_cost.py --skip-rounds --churn-reps 2 --churn-cycles {1,2,20}` | sector는 줄지 않으므로 peak의 정확한 상한이다 |
| 서버 카운터 | [bench/churn_counters.py](bench/churn_counters.py) | churn 중 로그 레코드, 로그 쪽 쓰기, `file_alloc`/`file_dealloc` 호출 수 |
| 집합 크기 의존 | [bench/churn_scale.py](bench/churn_scale.py) `--rows 2000 6000` | UPDATE, DELETE, 재INSERT 문장 시간이 행 수에 따라 어떻게 변하는가 |
| CPU 프로파일 | [bench/perf_churn.py](bench/perf_churn.py) | `perf record -F 4000 -p <cub_server>`, 호출 그래프 없음 |
| 최종 상태 | 서버를 올려 행 수와 `SHOW HEAP OOS` 확인 | 모든 INSERT, DELETE가 성공했는지 |

load average(1분)는 `/proc/loadavg`를 30초마다 기록했다([bench/loadavg-reuse-run1.txt](bench/loadavg-reuse-run1.txt), [bench/loadavg-reuse-run2.txt](bench/loadavg-reuse-run2.txt), [bench/loadavg-reuse-attrib.txt](bench/loadavg-reuse-attrib.txt)). nproc는 80이다. `perf` 프로파일과 첫 집합 크기 시험(16:31-16:44)에는 load를 기록하지 않았다.

| 구간 | 시각 | 표본 | 최소 | 중앙값 | 최대 |
| --- | --- | --- | --- | --- | --- |
| run 1 본 측정 | 15:04:52-15:26:55 (22분) | 45 | 33.0 | 41.5 | 98.8 |
| run 1 cycle 수별 sector | 15:33-15:39 | 12 | 17.5 | 25.1 | 42.1 |
| run 2 본 측정 | 15:52:00-16:17:16 (25분) | 51 | 36.2 | 80.2 | 138.4 |
| run 2 후속(카운터, cycle 수별 sector) | 16:17-16:31 | 28 | 40.5 | 100.2 | 207.3 |
| 귀속 시험(stage2a 생성, 카운터, 집합 크기) | 16:44-16:54 | 20 | 24.6 | 35.2 | 74.7 |

run 2는 부하가 run 1의 두 배였고 두 빌드의 값이 모두 커졌다. 빌드 사이 비교는 같은 시간대에 번갈아 돌았으므로 유효하다. 절대값 비교는 유효하지 않다.

## 결과

중앙값(p95; 최소-최대)이고 시간은 ms다. run 1은 stage1 대 stage2, run 2는 stage1h 대 stage2이다. 원자료는 [results-reuse-b8a7e5d74-vs-e8e714dae.csv](bench/results-reuse-b8a7e5d74-vs-e8e714dae.csv)와 [results-reuse-b8a7e5d74-vs-94ed2ea46.csv](bench/results-reuse-b8a7e5d74-vs-94ed2ea46.csv)다.

| 지표 | run 1 stage1 | run 1 stage2 | run 2 stage1h | run 2 stage2 |
| --- | --- | --- | --- | --- |
| 재시작 첫 INSERT ms (n=18) | 270 (321; 213-433) | 258 (574; 227-968) | 242 (396; 223-421) | 269 (333; 205-395) |
| 재시작 첫 INSERT fetch | 20,271 | 20,270 | 20,271 | 20,270 |
| 재시작 첫 INSERT 디스크 읽기 | 20,202 | 20,202 | 20,202 | 20,202 |
| 재시작 둘째 INSERT ms | 3.53 (5.38; 2.03-88.2) | 3.39 (10.1; 1.98-72.4) | 3.09 (26.6; 2.25-102) | 3.63 (22.5; 2.41-78.1) |
| 비우는 삭제 뒤 INSERT ms (n=40) | 3.26 (5.63; 2.27-6.18) | 3.72 (6.55; 2.32-9.62) | 4.94 (16.9; 2.44-72.9) | 4.95 (18.9; 2.31-64.7) |
| 같은 INSERT의 fetch | 42 | 42 | 42 | 42 |
| 같은 INSERT의 dirty 페이지 | **18** | **9** (9-14) | **18** (18-23) | **9** (9-14) |
| 이어진 INSERT ms (삭제 없음) | 3.21 (5.25; 1.88-5.92) | 3.33 (6.11; 1.94-13.6) | 4.17 (44.6; 2.08-77.6) | 4.94 (11.8; 2.08-68.6) |
| 이어진 INSERT fetch | 32 | **34** | 32 | **34** |
| 비우지 않는 삭제 뒤 INSERT ms (n=40) | 3.46 (6.19; 2.40-6.72) | 3.41 (7.25; 2.39-7.98) | 3.93 (69.7; 2.28-84.7) | 4.67 (18.4; 2.56-41.9) |
| 같은 INSERT의 fetch, 디스크 읽기 | 42, 1 | 42, 1 | 42, 1 | 42, 1 |
| 이어진 INSERT ms | 2.77 (5.87; 1.98-6.78) | 3.42 (5.58; 1.97-7.06) | 3.43 (63.2; 1.87-84.7) | 4.96 (49.1; 2.03-74.8) |
| 동시 8 세션, 회당 가장 느린 세션 ms (n=16) | 6.32 (11.6; 4.26-21.0) | 5.48 (9.23; 3.87-95.4) | 10.4 (19.4; 3.99-19.6) | 8.73 (22.1; 4.22-25.1) |
| 동시 세션 INSERT ms (n=128) | 5.70 (11.6; 2.89-21.0) | 5.10 (95.3; 2.64-95.4) | 7.62 (16.9; 2.71-19.6) | 7.84 (18.2; 2.63-25.1) |
| 동시 세션 fetch | 59 | 59 (59-63) | 59 | 59 |
| 일반 INSERT ms (n=300) | 3.15 (7.42; 1.86-117) | 3.23 (6.89; 1.79-95.3) | 2.85 (7.01; 2.15-101) | 3.37 (7.60; 1.83-98.0) |
| 일반 INSERT fetch | 32 | 32 | 32 | 32 |

두 빌드의 lap과 fetch 수는 1단계 보고서와 같은 모양이다. 삭제 뒤 INSERT는 fetch 42회로 lap이 없고, 재시작 첫 INSERT만 파일 전체(약 20,270쪽)를 읽는다.

### 같은 시간대의 짝지은 비교

서버 한 번 실행(round)이 독립 단위다. 실행마다 중앙값을 내고, 시간상 가까운 두 빌드의 실행을 짝지어 차이(stage2 - 기준)의 중앙값을 냈다. 두 run의 짝을 합쳐 부호 검정을 했다. 스크립트는 [bench/paired_rounds.py](bench/paired_rounds.py)다.

| 항목 | 합친 짝 | 차이의 중앙값 ms | stage2가 느린 짝 | 부호 검정 p |
| --- | --- | --- | --- | --- |
| 재시작 첫 INSERT | 36 | -0.12 | 18/36 | 1.00 |
| 재시작 둘째 INSERT | 36 | +0.35 | 20/36 | 0.62 |
| 비우는 삭제 뒤 INSERT | 16 | -0.07 | 8/16 | 1.00 |
| 이어진 INSERT (비우는 삭제) | 16 | -0.24 | 6/16 | 0.45 |
| 비우지 않는 삭제 뒤 INSERT | 16 | +0.48 | 10/16 | 0.45 |
| 이어진 INSERT (비우지 않는 삭제) | 16 | +0.93 | 11/16 | 0.21 |
| 일반 INSERT | 20 | +0.15 | 11/20 | 0.82 |
| 동시 8 세션 가장 느린 세션 | 16 | -1.13 | 7/16 | 0.80 |
| 동시 세션 INSERT | 16 | +0.07 | 9/16 | 0.80 |

유의한 차이가 있는 항목이 없다. 비우지 않는 삭제 항목의 두 행은 두 run에서 같은 부호(run 1 +0.74, run 2 +1.67 ms)이고 같은 종류의 일반 INSERT는 부호가 섞인다(-0.18, +0.45). 최대 1 ms 안팎의 느려짐이 있어도 이 표본으로는 가릴 수 없다.

### 설명

- **재시작 첫 INSERT는 lap이 정한다.** 258 ms를 fetch 20,270으로 나누면 쪽당 12.7 µs다. fetch(20,270-20,271)와 디스크 읽기(20,202)가 네 빌드에서 같다(측정함). 디스크 읽기는 파일(330 MB)이 버퍼(256 MB)보다 커서 OS page cache에서 읽는 것으로 보인다(추정). lap 코드는 2단계가 바꾸지 않았다. stage2의 최대 968 ms와 574 ms는 run 1에서만 나왔고 같은 시각의 load는 43과 38이었다. 원인은 조사하지 않았다.
- **삭제 뒤 INSERT는 문장 고정 비용이 정한다.** 같은 서버 실행에서 바로 이어 잰 일반 INSERT(3.2~5.0 ms)와 차이가 없다(측정함). 두 빌드 모두 이미 그 바닥에 있어서 2단계가 더 빨라질 여지가 없다. 이 항목은 느려졌는지만 판정한다. 바닥을 이루는 일은 fetch 32회, dirty 14쪽, 10 KB 값을 만드는 CPU다(churn profile의 1위 심볼이 값 생성 `qstr_hex_to_bin`이다).
- **dirty 페이지 18에서 9는 dealloc과 alloc 한 쌍이 하던 일이다 (측정함).** 어느 페이지인지는 확인하지 않았다. file table 페이지로 보이지만 추정이다. 이어진 INSERT의 fetch가 32에서 34로 늘어난 이유도 확인하지 않았다. 시간은 늘지 않았다.
- **동시 8 세션은 직렬 구간이 작다.** 회마다 (가장 느린 세션 - 가장 빠른 세션) / 7은 stage1 0.32 ms, stage2 0.31 ms(run 1), stage1h 0.63 ms, stage2 0.47 ms(run 2)다. 직렬 구간의 상한이고 growth lock 대기를 직접 잰 것이 아니다. stage2의 95.4 ms는 한 회(16회 중 1회)이고, 8개 세션 중 7개가 0.1 ms 안(95.30-95.39 ms)에서 끝났고 나머지 한 개는 40.4 ms였다. 성장 lock이 만드는 계단 모양이 아니라, 모두 같은 일을 기다렸다 같이 풀린 모양이다. fetch는 59-61이라 성장과 무관하다. 원인은 조사하지 않았다.

## 파일 크기 (churn)

`c` 2,000행(1,001쪽), 6 cycle, 빌드당 4회. cycle마다 전체 UPDATE, drain, 30% DELETE, drain, 재INSERT 뒤 페이지 수를 쟀다.

| 지표 (cycle 24개) | stage1 | stage2 (run 1) | stage1h | stage2 (run 2) |
| --- | --- | --- | --- | --- |
| UPDATE drain 뒤 페이지 | 1,001 | 2,101 (2,001-2,101) | 1,001 | 2,101 (2,001-2,101) |
| DELETE drain 뒤 페이지 | 720 (716-801) | 2,101 (2,001-2,101) | 721.5 (716-801) | 2,101 (2,001-2,101) |
| 재INSERT 뒤 페이지 | 1,001 | 2,101 (2,001-2,101) | 1,001 | 2,101 (2,001-2,101) |
| UPDATE commit 직후 스냅샷 | 1,779 (1,056-1,940) | 2,101 (2,001-2,101) | 1,764 (1,051-2,001) | 2,101 (2,001-2,101) |
| 최종 sector c / t / u / p | 32 / 318 / 315 / 1 | **33** / 318 / 315 / 1 | 32 / 318 / 315 / 1 | **33** / 318 / 315 / 1 |

2단계는 페이지를 반환하지 않으므로 drain 뒤 페이지 수가 줄지 않는다. 설계한 동작이다(ADR-0009 결과 1). 그래서 1단계 보고서의 "drain 뒤 페이지 수가 같다" 판정은 쓰지 않고 sector 수와 cycle별 peak로 본다.

**1단계의 스냅샷 peak는 믿을 수 없다.** UPDATE commit 직후 별도 csql로 찍는 사이에 vacuum의 fast path가 이미 페이지를 반환하기 시작한다. 1단계 cycle 1의 스냅샷은 1,051-1,094쪽인 경우와 1,935-2,001쪽인 경우가 섞인다. 이 스냅샷으로 ADR-0009 결정 4를 계산하면 1단계가 허위로 탈락한다(`churn_peak.py`가 이를 보여 준다). 2단계는 페이지가 줄지 않으므로 스냅샷이 정확하다. 1단계의 정확한 상한은 sector 수다. sector는 줄지 않는다.

### cycle별 peak와 sector (ADR-0009 결정 4)

| 빌드 | cycle 1 peak | cycle 2-20 peak | 허용치 max(2쪽, 10%) | 첫 peak 대비 최대 증가 | sector 1 / 2 / 20 cycle 뒤 |
| --- | --- | --- | --- | --- | --- |
| stage2 (run 1, 2) | 2,001 | 2,101 (cycle 2-20 전부) | 201 | +100 (+5.0%) | 32 / 33 / 33 |
| stage1, stage1h | 스냅샷 신뢰 불가 | 스냅샷 신뢰 불가 | | | 32 / 32 / 32 |

- cycle 수별 sector는 빌드당 2회씩, 두 run에서 같은 값이 나왔다([results-reuse-churn-cycles.csv](bench/results-reuse-churn-cycles.csv)). 2단계는 cycle 1에서 32 sector(2,001쪽), cycle 2에서 33 sector(2,101쪽)가 되고 cycle 20까지 그대로다. 1단계는 20 cycle까지 32 sector다.
- 페이지 조항(첫 cycle peak + max(2쪽, 10%))은 2단계가 충족한다. cycle 2에서 100쪽 한 번 늘고 18 cycle 동안 평평하다. 쪽당 한 쪽씩 쌓이는 증가라면 5 cycle 안에 허용치 201쪽을 넘었을 것이다.
- sector 조항("재INSERT 뒤 예약 sector가 첫 peak를 넘지 않는다")은 허용치 없이 읽으면 2단계가 1 sector 넘는다(33 sector = 2,112쪽, 첫 peak 2,001쪽은 32 sector). 허용치 10%를 이 조항에도 적용하면 충족한다(2,112쪽은 첫 peak의 105.5%). ADR 문장은 어느 쪽인지 말하지 않는다. 사용자가 정할 일이다.
- 1 sector는 64쪽이므로 2단계는 c 파일에서 디스크를 약 1 MiB(64쪽 × 16 KiB) 더 쓴다.
- **100쪽이 왜 늘어나는가는 모른다.** 2단계에서는 cycle 2의 UPDATE가 살아 있는 2,000개 chunk 위에 새 2,000개를 놓아야 한다. 1단계는 페이지를 반환해 살아 있는 chunk가 1,001쪽에 촘촘히 모여 있다. 2단계는 살아 있는 chunk가 처음 놓인 자리에 흩어져 있다. 반쯤 찬 페이지를 bestspace hint가 모두 알려 주지 못해 약 5%가 더 필요하다는 것이 내 추정이다. 페이지를 chunk 수별로 세어 확인하지는 않았다. 후속 행 수 시험에서 이 증가가 파일의 5%에 비례함을 확인했고 늦은 vacuum 가설은 반박됐다("로그 block 가설 시험" 절).

### 최종 상태

세 DB 쌍 모두 같은 최종 상태다. `t` 20,488행, OOS 레코드 20,488, 페이지 20,489. `u` 40,058행, 레코드 40,058, 페이지 20,099. `c` 2,000행, 레코드 2,000. 모든 INSERT와 DELETE가 성공했고 vacuum이 모두 처리했다는 확인이다. `p`는 2단계가 3쪽, 1단계가 2쪽이다(반환하지 않는 설계). `c`의 페이지는 stage1 1,001, stage2 2,101이다. `cubrid checkdb -S`는 두 DB에서 출력 없이 rc 0으로 1초 만에 끝났다. 이 속도로는 깊이 검사했는지 알 수 없다. 증거로 쓰지 않았다.

## 로그와 sysop

`Num_log_append_records`, `Num_log_page_iowrites`, `Num_file_page_allocs`, `Num_file_page_deallocs`를 churn의 단계마다 `cubrid statdump` 차이로 쟀다([bench/churn_counters.py](bench/churn_counters.py), [results-reuse-counters.csv](bench/results-reuse-counters.csv)). `file_alloc`과 `file_dealloc`은 각각 sysop 하나로 도므로 호출 수를 sysop의 대리 값으로 쓴다. 서버는 누가 통계를 보고 있을 때만 세므로 `cubrid statdump -i 1`을 churn 동안 띄워 두었다(csql 세션에 `@collect_exec_stats`를 켜면 트랜잭션 snapshot이 vacuum을 막는다). 처음 시도는 이 감시자가 없어 모든 값이 0이었고 버렸다.

한 cycle의 DML 두 문장(UPDATE 2,000행과 재INSERT 600행)은 OOS chunk를 2,600개 INSERT한다. 이 구간에는 filler가 없어서 값이 정확하다. cycle 2-6의 중앙값이다.

| 지표 | stage1 | stage1h | stage2 (run 1) | stage2 (run 2) |
| --- | --- | --- | --- | --- |
| UPDATE 로그 레코드 | 16,066 | 16,066 | 10,203 | 10,220 |
| 재INSERT 로그 레코드 | 10,276 | 10,296 | 6,024 | 6,024 |
| **INSERT 1000건당 로그 레코드** | **10,166** | **10,177** | **6,241** | **6,249** |
| UPDATE와 재INSERT 로그 쪽 쓰기 | 183 | 184 | 134 | 134 |
| 이 두 문장 중 `file_alloc` 호출 | 1,283 | 1,284 | 0 (cycle 2만 +100) | 0 (cycle 2만 +100) |
| 이 두 문장 중 `file_dealloc` 호출 | 240 | 237 | 0 | 0 |

- INSERT 1000건당 로그 레코드가 39% 줄었다(10.2K에서 6.2K). 줄어든 3.9K는 피한 `file_alloc` 한 번당 약 15개(재INSERT: 4,253/283), UPDATE 쪽은 호출당 약 5개(5,863/1,240)다. 두 값이 같지 않은 이유는 확인하지 않았다.
- 한 cycle 전체(vacuum 포함)의 `file_alloc` 1,288회와 `file_dealloc` 1,283회가 1단계, 2단계는 두 값 모두 0에 가깝다(`file_alloc`은 cycle 2에서만 100회). 합 2,571회를 INSERT 2,600건으로 나누면 INSERT 1000건당 sysop 약 989개와 0개다. cycle 2는 38개다.
- 한 cycle 전체의 로그 레코드는 원값이 1단계 41.1K, 2단계 25.1K다. 이 값에는 drain의 filler가 들어 있고 2단계는 filler가 cycle마다 25개로 1단계의 9개보다 많다(아래 drain 절). filler 하나의 비용(약 560-620 레코드)을 빼면 1단계 약 35.6K, 2단계 약 11.1K이다. 2단계는 단계별 값이 음수가 되어 과하게 빼는 것을 알 수 있다. 그래서 전체 cycle 값은 "2단계가 1단계의 절반 이하"까지만 말한다.

## 집합 크기에 비례하는 성장 비용

churn의 UPDATE, DELETE, 재INSERT 문장 시간(csql 자체 타이머)을 cycle 1과 cycle 2 이후로 나누었다. cycle 1에서는 빈 페이지가 아직 집합에 없고 DELETE는 성장하지 않으므로 둘 다 대조군이다. 표본은 watcher 없이 돈 churn 전부를 합친 cycle 2 이후 문장이다. run 1은 80회(본 측정 20, 카운터 첫 시도 20, cycle 수별 sector 시험 40), run 2는 60회(본 측정 20, 시험 40)다.

| 문장 (2,000행) | run 1 stage1 | run 1 stage2 | run 2 stage1h | run 2 stage2 |
| --- | --- | --- | --- | --- |
| UPDATE ms, cycle 2 이후 | 125.4 | 134.8 (+7%) | 157.7 | 189.4 (+20%) |
| 재INSERT ms, cycle 2 이후 | 51.4 | 57.9 (+13%) | 58.5 | 72.7 (+24%) |
| DELETE ms, cycle 2 이후 (대조군) | 15.5 | 12.1 | 15.8 | 16.5 |
| UPDATE ms, cycle 1 (대조군, n=14 / 7-8) | 132.0 | 136.5 (+3%) | 153.4 | 179.7 (+17%) |
| 재INSERT ms, cycle 1 (대조군) | 48.0 | 49.8 | 73.6 | 74.4 |

2,000행에서는 cycle 2 이후의 +7%, +20%가 cycle 1 대조군의 +3%, +17%와 구별되지 않는다. 이 크기에서 문장 시간으로는 집합 복사 비용을 확인하지 못했다. 아래 6,000행 시험과 `perf`가 증거다.

행 수를 키워 집합을 크게 한 시험은 [bench/churn_scale.py](bench/churn_scale.py)이고 결과는 [perf-reuse/](bench/perf-reuse/)에 있다. 시험 A는 stage1h와 stage2, 시험 B는 stage1h, stage2a, stage2를 돌렸다. 각 칸은 서버 실행 2회 × cycle 2-3 = 4회의 중앙값(cycle 1은 2회)이고 A / B 순서로 적었다.

| 행 수 | 문장 | cycle | stage1h | stage2a (`5d7eda23c`) | stage2 |
| --- | --- | --- | --- | --- | --- |
| 6,000 | UPDATE ms | 1 | 412 / 408 | 376 | 387 / 397 |
| 6,000 | UPDATE ms | **2 이후** | **372 / 386** (363-401) | **1,051** (919-1,153) | **980 / 1,000** (885-1,119) |
| 6,000 | 재INSERT ms | 2 이후 | 134 / 125 | 121 | 126 / 125 |
| 6,000 | DELETE ms (대조군) | 2 이후 | 31 / 32 | 25 | 22 / 24 |
| 2,000 | UPDATE ms | 2 이후 | 148 / 131 | 132 | 120 / 126 |

6,000행 UPDATE는 cycle 1에서 같고 cycle 2 이후에서만 2.6배가 된다. 시험 두 번이 같은 값을 냈다. 6,000행의 재INSERT와 DELETE는 차이가 없다. 2,000행에서는 이 소규모 시험도 차이를 보이지 않았다. 2,000행 대 6,000행에서 UPDATE 증가분은 차이가 없는 수준에서 약 610-665 ms로 늘었다. 크기가 두 가지뿐이라 증가 곡선의 모양은 말할 수 없다.

**원인은 성장마다 emptied 집합 전체를 복사하는 것이다.** 근거 셋이다.

1. 코드를 읽어서 안 것 (`b8a7e5d74`): `oos_reclaim_check_emptied`(`oos_file.cpp` 1708-1763, 복사 반복은 1722-1727)는 bestspace mutex를 잡고 집합의 모든 VPID를 `examined`(`std::set`)에 넣고 `batch`(`std::vector`)에 넣는다. 그 뒤에야 `batch`의 첫 후보를 시도하고, 후보 하나를 얻으면 반환한다. 후보가 첫 번째에서 잡혀도 집합 전체를 복사한다. 1단계에서는 vacuum의 fast path가 emptied 페이지를 집합에서 빼므로 집합이 작았다.
2. `perf`(측정함, [perf-reuse/](bench/perf-reuse/)): 6,000행 churn(3 cycle)에서 서버 CPU 표본의 `std::_Rb_tree<vpid, ..., oos_vpid_order>::_M_insert_unique` 13.0%, `_Rb_tree_increment` 4.1%, `_Rb_tree_insert_and_rebalance` 3.8%, `_M_erase` 1.1%로 합 22%였다. 1단계(`94ed2ea46`)에는 이 심볼이 없다. `malloc`/`free` 계열 심볼은 stage2 16.4%, stage1h 6.0%이다. 이 10%p 차이가 set 노드의 할당과 해제인지는 호출 그래프를 뜨지 않아 확인하지 않았다. 2,000행 churn에서는 set 심볼이 stage2 0.5-0.7%이고 stage1h 0이다.
3. 크기 환산(추정): UPDATE 증가분 약 610 ms를 UPDATE의 성장 약 3,000회(chunk 6,000개를 쪽당 2개씩)로 나누면 성장당 약 200 µs이다. 성장마다 평균 약 1,500개를 복사했다면 원소당 약 135 ns로, `std::set` 삽입과 `malloc`의 비용 범위다. 상한 4,096개에서는 성장당 약 0.55 ms(추정)이고, 이 시간 동안 모든 OOS 파일이 공유하는 bestspace mutex를 쥔다. 동시 INSERT에 미치는 영향은 재지 않았다.

한 번에 많은 페이지를 비우는 DELETE 뒤에 대량 INSERT나 UPDATE를 하면 이 비용을 만난다. 단건 INSERT 항목은 집합이 한두 개라서 보이지 않았다. 고치는 방향은 복사 없이 집합을 순회하는 것이다(예: mutex 아래에서 `examined`에 없는 첫 원소 하나만 꺼내 처리하고 다시 반복). 이 수정은 시도하지 않았고 수정 뒤에 같은 시험으로 다시 재야 한다.

## 귀속: 두 커밋 중 어느 쪽인가

2단계는 두 커밋이다. `5d7eda23c`는 vacuum fast path를 없앤다(성장은 아직 emptied 페이지를 dealloc하고 다시 alloc한다). `b8a7e5d74`는 빈 페이지를 제자리에서 재사용한다. 중간 커밋 `5d7eda23c`(stage2a)를 따로 빌드해 같은 시험을 돌렸다. 카운터와 drain은 stage1h, stage2a, stage2를 한 번에 돌린 값이고, 집합 크기 시험은 위 시험 B다.

| 항목 | stage1h `94ed2ea46` | stage2a `5d7eda23c` (fast path 제거) | stage2 `b8a7e5d74` (제자리 재사용) |
| --- | --- | --- | --- |
| cycle 2 이후 페이지, sector | 1,001 (drain 뒤), 32 | 2,101, 33 | 2,101, 33 |
| 6,000행 UPDATE cycle 2 이후 ms | 386 | **1,051** | **1,000** |
| UPDATE 뒤 drain의 filler 수 (cycle 2-6) | 1 | **13.5** | **12** |
| DELETE 뒤 drain의 filler 수 | 8 | 13 | 13 |
| INSERT 1000건당 로그 레코드 (DML 구간) | 10,190 | 8,216 | **6,243** |
| UPDATE 문장 중 `file_alloc` / `file_dealloc` | 1,000 / 249 | 300 / 300 | **0 / 0** |

(측정함) 파일이 1단계보다 크게 남는 것(+100쪽, +1 sector), 집합 복사 비용, drain 지연은 모두 fast path를 없앤 `5d7eda23c`에서 이미 나타난다. 제자리 재사용 `b8a7e5d74`가 더하는 것은 로그 레코드와 sysop 감소다. 제자리 재사용 자체는 느려짐도 파일 증가도 만들지 않았다. 코드로는 fast path가 없으면 vacuum이 비운 페이지가 emptied 집합에 남고 반환되지 않아 파일에 남는다. 그래서 집합이 커지고 복사 비용이 커진다. 100쪽 증가와 drain 지연이 이 구조에서 나오는 이유는 확인하지 않았다.

## drain이 오래 걸린다 (원인 모름)

churn의 `drain`은 vacuum이 옛 chunk를 모두 지울 때까지 로그를 밀고(filler INSERT) `SHOW HEAP OOS`로 확인하는 반복이다. filler 수는 카운터 시험(감시자가 도는 churn)의 값이다. 시간은 csql 로그 파일 시각으로 잰 것이고(UPDATE 문장이 끝난 때부터 다음 DELETE 문장이 시작하기까지), 감시자 유무와 관계없이 모든 churn을 합쳤다.

| 구간 (cycle 2 이후) | stage1 | stage1h | stage2 (run 1) | stage2 (run 2) |
| --- | --- | --- | --- | --- |
| UPDATE 뒤 drain 시간 s | 0.33 (n=100) | 0.34 (n=80) | 2.35 (n=100) | 2.49 (n=80) |
| UPDATE 뒤 filler 수 | 1 | 1 | 12 | 12 |
| DELETE 뒤 drain 시간 s | 1.49 | 1.48 | 2.52 | 2.61 |
| DELETE 뒤 filler 수 | 8 | 7 | 13 | 13 |

cycle 1에서는 UPDATE 뒤 filler가 모두 1개다(중앙값. stage2 drain 1.05 s, stage1 0.40 s). 두 run에서 같고 `94ed2ea46`과도 다르므로 base 차이가 아니다. 중간 커밋 `5d7eda23c`도 같다. 큰 filler 하나(데이터 약 9 MB)로 밀면 세 빌드 모두 첫 poll에서 끝났고 UPDATE부터 0.1-0.15 s가 걸렸다(빌드당 8회, [bench/drain_probe.py](bench/drain_probe.py)). 시간이 아니라 vacuum이 끝나기까지 필요한 로그 양이 다른 것으로 보인다(추정). 2단계는 UPDATE 뒤 약 60쪽(12 filler × 5.2쪽)을 더 밀어야 끝난다. 왜 그런지는 조사하지 않았다. vacuum 지연이므로 INSERT와 UPDATE 문장 시간에는 들어가지 않는다. 다만 옛 chunk가 늦게 지워지는 시간은 파일에 더 큰 공간이 필요한 시간과 겹칠 수 있다.

이 harness에서 2단계의 서버 CPU(`perf`의 cycles)가 1단계의 1.7-1.8배인 것도 이 filler와 poll(2,101쪽 파일 전체를 읽는 `SHOW HEAP OOS`) 때문으로 보인다(`nums` 전체를 읽는 `heap_next_internal`, `eval_data_filter`가 stage2 상위에 있다). 엔진의 비용이라고 보지 않는다(추정).

## 수정판 `f8cdfca747`

부모 세션이 `b8a7e5d74` 위에 `f8cdfca747`을 올렸다. `oos_reclaim_check_emptied`가 집합 전체를 `examined`와 `batch`에 복사하지 않고 아직 보지 않은 원소 하나씩 고른다(`git diff --stat b8a7e5d74 f8cdfca747`는 `oos_file.cpp` 1파일, 29줄 추가 28줄 삭제). `CBRD-27872-after3`를 이 커밋으로 detached 이동하고 `release_gcc`를 다시 빌드해 설치했다(11.5.0.2804-f8cdfca, 소스 상태 깨끗함). 이전 `b8a7e5d74` 설치는 `~/.cub/install/CBRD-27872-after3-b8a7e5d74`로 복사해 두었다(가설 시험에서 쓴다). `libcubridsa.so`에 `oos_reclaim_check_emptied`가 있고 제거된 함수는 없다. 결과 label은 `stage2fix`이고 기준은 `stage1h`(`94ed2ea46`)다. 새 DB(`/mnt/nvme/data-5/tmp/w878/fix`)를 만들어 run 2와 같은 파라미터로 돌렸다. 두 빌드를 번갈아 돌렸고 서버는 한 번에 하나였다.

load average(1분): 집합 크기 시험, perf, 가설 시험 17:12-17:24는 중앙값 71.7(29-187), 본 측정 17:24-17:47은 47개 표본, 중앙값 66.2(37-117), 후속 17:47-18:00은 중앙값 77.0(39-125)이다([bench/loadavg-reuse-fix.txt](bench/loadavg-reuse-fix.txt)).

### (a) 집합 크기 시험 (측정함)

[churn_scale.py](bench/churn_scale.py), 서버 실행 3회 × cycle 2-3 = 6회(cycle 1은 3회)의 중앙값(범위)이다. 이전 시험(`b8a7e5d74`)의 칸은 같은 표에서 가져왔다.

| 행 수 | 문장 | cycle | stage1h | stage2fix | 이전 stage2 (`b8a7e5d74`) |
| --- | --- | --- | --- | --- | --- |
| 6,000 | UPDATE ms | 1 | 429 | 388 | 387 / 397 |
| 6,000 | UPDATE ms | **2 이후** | **378.5** (359-387) | **338.8** (333-620) | **980 / 1,000** |
| 6,000 | 재INSERT ms | 2 이후 | 136.5 | 113.2 | 126 / 125 |
| 6,000 | DELETE ms (대조군) | 2 이후 | 31.3 | 22.4 | 22 / 24 |
| 2,000 | UPDATE ms | 2 이후 | 138.6 | 112.0 | 120 / 126 |

6,000행 UPDATE의 cycle 2 이후 중앙값이 1단계와 같은 수준(10% 빠름)으로 돌아왔다. stage2fix 6회는 333, 336, 338, 340, 385, 620 ms이고 stage1h 6회는 359-387 ms다. 620 ms는 한 번의 이상치로 보인다. 본 측정 churn(2,000행)의 문장 시간도 같다. 수정판 대 stage1h는 UPDATE cycle 2 이후 133.7 대 148.6 ms(n=60), 재INSERT 63.9 대 58.4 ms(cycle 1 대조군도 63.1 대 52.1 ms라서 구별되지 않음), DELETE 15.4 대 18.0 ms이다.

### (b) perf 프로파일 (측정함)

6,000행 churn 3 cycle의 서버 CPU 표본이다([perf-reuse/](bench/perf-reuse/)의 `*-fixrun.txt`와 `perf-6000rows-stage2fix-f8cdfca747.txt`). 같은 심볼(`std::_Rb_tree<vpid, ..., oos_vpid_order>`와 `_Rb_tree_insert_and_rebalance`, `_Rb_tree_increment`, `_Rb_tree_rebalance_for_erase`) 합이다.

| 빌드 | set 연산 CPU 표본 비중 | `malloc`/`free` 계열 | 서버 cycles |
| --- | --- | --- | --- |
| stage1h (`94ed2ea46`) | 0.09% | 6.0% | 6.0 G |
| 이전 stage2 (`b8a7e5d74`, 이전 프로파일) | **22.0%** | 16.4% | 15.0 G |
| stage2fix (`f8cdfca747`) | **0.44%** (`equal_range` 0.17, `rebalance_for_erase` 0.15, `_M_insert_unique` 0.10) | 4.6% | 6.7 G |

set 연산이 사라졌다. 남은 0.44%는 집합의 조회, 삽입, 삭제로 보인다(추정). 서버 cycles는 stage1h의 1.12배다(이전 1.77배).

### (c) growth_cost (run 2 파라미터) (측정함)

8 round, 삭제 항목 40회, 동시 8 세션 16회, 재시작 18회, 일반 INSERT 10 round × 30, churn 4회 × 6 cycle이다. 원자료는 [results-reuse-f8cdfca747-vs-94ed2ea46.csv](bench/results-reuse-f8cdfca747-vs-94ed2ea46.csv)이다. 오류 없이 끝났다(모든 단계 rc 0).

| 지표 | stage1h | stage2fix | 이전 stage2 / stage1h (run 2) |
| --- | --- | --- | --- |
| 재시작 첫 INSERT ms | 298 (394; 236-399) | 289 (509; 216-510) | 269 / 242 |
| 재시작 첫 INSERT fetch | 20,271 | 20,270 | 20,270 / 20,271 |
| 재시작 둘째 INSERT ms | 3.47 (4.38; 2.30-4.51) | 3.07 (4.70; 2.21-5.59) | 3.63 / 3.09 |
| 비우는 삭제 뒤 INSERT ms | 4.00 (5.55; 2.63-10.7) | 4.06 (11.3; 2.43-41.5) | 4.95 / 4.94 |
| 같은 INSERT의 fetch, dirty 페이지 | 42, **18** | 42, **9** | 42, 9 / 42, 18 |
| 이어진 INSERT ms | 3.26 (4.48; 2.05-5.95) | 2.85 (6.78; 2.02-8.67) | 4.94 / 4.17 |
| 이어진 INSERT fetch | 32 | **34** | 34 / 32 |
| 비우지 않는 삭제 뒤 INSERT ms | 3.70 (5.48; 2.35-5.96) | 3.81 (7.24; 2.39-10.7) | 4.67 / 3.93 |
| 동시 8 세션, 회당 가장 느린 ms | 6.26 (15.6; 4.80-16.9) | 5.84 (15.3; 4.83-17.3) | 8.73 / 10.4 |
| 동시 세션 INSERT ms (n=128) | 5.46 (10.8; 2.63-16.9) | 5.53 (15.3; 2.57-17.3) | 7.84 / 7.62 |
| 일반 INSERT ms (n=300) | 3.63 (10.8; 1.90-195) | 3.87 (7.71; 2.08-200) | 3.37 / 2.85 |

이 run은 부하 중앙값이 66으로 run 2(80)보다 낮고 값이 전반적으로 작다. 같은 서버 실행 짝의 비교다(stage2fix - stage1h, [paired_rounds.py](bench/paired_rounds.py), 부호 검정 p는 정확 이항 검정).

| 항목 | 짝 | 차이의 중앙값 ms | stage2fix가 느린 짝 | p |
| --- | --- | --- | --- | --- |
| 재시작 첫 INSERT | 18 | -14.1 | 8/18 | 0.81 |
| 재시작 둘째 INSERT | 18 | -0.19 | 7/18 | 0.48 |
| 비우는 삭제 뒤 INSERT | 8 | -0.13 | 4/8 | 1.00 |
| 이어진 INSERT (비우는 삭제) | 8 | -0.38 | 3/8 | 0.73 |
| 비우지 않는 삭제 뒤 INSERT | 8 | +0.30 | 6/8 | 0.29 |
| 이어진 INSERT (비우지 않는 삭제) | 8 | +0.28 | 5/8 | 0.73 |
| 일반 INSERT | 10 | -0.01 | 5/10 | 1.00 |
| 동시 8 세션 가장 느린 세션 | 8 | -0.05 | 4/8 | 1.00 |
| 동시 세션 INSERT | 8 | +0.05 | 6/8 | 0.29 |

모든 항목이 노이즈 안이다. 이전 `b8a7e5d74`에서 보이던 비우지 않는 삭제 항목의 +0.5, +0.9 ms 경향은 +0.3 ms로 줄었다. 동시 세션의 직렬 구간 상한 (가장 느린 - 가장 빠른) / 7은 stage1h 0.39 ms, stage2fix 0.34 ms다.

파일 크기와 로그는 `b8a7e5d74`와 같다. 복사 수정은 둘을 건드리지 않는다.

| 지표 | stage1h | stage2fix |
| --- | --- | --- |
| cycle별 peak (2,000행, cycle 1 / cycle 2-20) | 스냅샷 신뢰 불가 | 2,001 / 2,101 |
| sector, 6 cycle 뒤 (c) | 32 | 33 |
| sector, 1 / 2 / 20 cycle 뒤 | 32 / 32 / 32 | 32 / 33 / 33 |
| INSERT 1000건당 로그 레코드 (DML 구간) | 10,177 | 6,253 |
| UPDATE 문장 중 `file_alloc` / `file_dealloc` | 1,000 / 240 | 0 / 0 (cycle 2만 +100) |
| UPDATE 뒤 drain의 filler 수 (cycle 2-6) | 1 | 12 |
| DELETE 뒤 drain의 filler 수 | 7.5 | 13 |

### 수정판의 판정 변화

| 조건 | 이전 (`b8a7e5d74`) | 수정판 (`f8cdfca747`) |
| --- | --- | --- |
| ADR-0010 결정 7: INSERT 시간이 1단계보다 나빠지지 않는다 | 일부 미충족 | **충족**. 단건 INSERT 5개 항목은 구별 불가(p ≥ 0.29), 6,000행 UPDATE는 339 대 379 ms |
| ADR-0010 결정 7: churn 뒤 파일 크기 | 충족(조건부) | 변화 없음. sector 33 대 32 |
| ADR-0009 결정 4 peak 조항 | 충족 | 변화 없음 |
| ADR-0009 결정 4 sector 조항 | 해석에 따라 다름 | 변화 없음. 아래 가설 시험에서 이 차이가 파일 크기에 비례함을 확인했다 |

## 로그 block 가설 시험

시험한 가설은 이렇다(추론이고 측정이 아니었다). vacuum은 가득 찬 로그 block만 처리한다. 2단계는 로그 레코드를 약 40% 적게 쓰므로 cycle 끝의 마지막 block이 늦게 차고, 옛 chunk가 늦게 vacuum되며, 다음 cycle의 UPDATE가 페이지를 100쪽 더 필요로 한다. 한 block은 31 로그 페이지다(`vacuum.h`의 `VACUUM_LOG_BLOCK_PAGES_DEFAULT`. 이 DB에서 파라미터를 바꾸지 않았다).

### 설계

[bench/log_traffic_churn.py](bench/log_traffic_churn.py)는 harness의 churn을 그대로 돌리되 drain의 filler 크기만 바꾼다.

- `small`: 지금까지의 filler(200행 INSERT, 로그 약 5쪽)를 poll마다 한 번.
- `big`: 같은 poll인데 filler가 6,000행(`small`의 30배)이다. UPDATE나 DELETE의 마지막 로그 block이 filler 하나로 완성된다.

빌드는 stage1h, stage2(`b8a7e5d74`의 보존한 설치), stage2fix이고, 모드당 3회 × 6 cycle이다. 요약은 [bench/logtraffic_summary.py](bench/logtraffic_summary.py), 원자료는 [results-reuse-logtraffic.csv](bench/results-reuse-logtraffic.csv)다. 중앙값(범위)이고, stage1h의 peak는 스냅샷이라 하한이다.

| 빌드 | 모드 | cycle 1 peak | cycle 2+ peak | sector c | UPDATE drain s | UPDATE drain filler 수 | DELETE drain s | DELETE drain filler 수 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stage1h | small | 1,527 (1,077-1,582) | 1,782 (1,689-1,828) | 32 | 0.34 | 1 | 1.89 | 7 |
| stage1h | big | 1,084 (1,083-1,665) | 1,657 (1,178-1,981) | 32 | 0.33 | 1 | 0.39 | 1 |
| stage2 | small | 2,001 | 2,101 | 33 | **2.45** | **12** | 2.62 | 13 |
| stage2 | big | 2,001 | **2,101** | **33** | **0.33** | **1** | 0.39 | 1 |
| stage2fix | small | 2,001 | 2,101 | 33 | 2.44 | 12 | 2.78 | 13 |
| stage2fix | big | 2,001 | **2,101** | **33** | **0.31** | **1** | 0.41 | 1 |

### 행 수 시험

UPDATE 크기를 바꾸면 로그 양도 바뀐다. `--rows`를 바꿔 같은 `small` 모드를 stage1h와 stage2fix에 돌렸다(서버 실행 2회 × 4 cycle, 2,000행은 위 표의 3회 × 6 cycle). 이 시험은 load 중앙값이 137(108-180)로 높았다([bench/loadavg-reuse-rows.txt](bench/loadavg-reuse-rows.txt)).

| 행 수 | 빌드 | cycle 1 peak | cycle 2+ peak | sector c | UPDATE drain s | UPDATE drain filler 수 | DELETE drain filler 수 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1,000 | stage1h | 1,001 | 1,001 (896-1,001) | 16 | 0.88 | 2 | 2 |
| 1,000 | stage2fix | 1,001 | **1,001** | **16** | **5.49** | **15** | 15 |
| 2,000 | stage1h | 1,527 | 1,782 | 32 | 0.34 | 1 | 7 |
| 2,000 | stage2fix | 2,001 | **2,101** (+100, +5.0%) | **33** | 2.44 | 12 | 13 |
| 4,000 | stage1h | 2,482 | 2,802 | 63 | 0.50 | 1 | 1.5 |
| 4,000 | stage2fix | 4,001 | **4,202** (+201, +5.0%) | **66** | 1.20 | 3 | 8 |
| 6,000 | stage1h | 4,060 | 3,873 | 94 | 0.27 | 1 | 1 |
| 6,000 | stage2fix | 6,001 | **6,302** (+301, +5.0%) | **99** | 0.28 | 1 | 1 |

### 판정

1. **drain 지연은 로그 완료에 의존한다: 확인.** `big`에서 stage2와 stage2fix의 UPDATE drain이 2.45 s와 12 filler에서 0.33 s와 1 filler로 줄어 stage1h(0.33 s, 1 filler)와 같다. DELETE drain도 2.62 s와 13 filler에서 0.39 s와 1 filler다. 행 수가 늘수록 UPDATE가 스스로 쓰는 로그가 많아져 지연이 줄어든다(filler 15, 12, 3, 1). 이전의 큰 filler 시험([bench/drain_probe.py](bench/drain_probe.py), 세 빌드 24회)과 같은 결론이다.
2. **그 원인이 "2단계가 로그 레코드를 40% 적게 쓴다"는 것: 반박.** 근거는 둘이다.
   - 중간 커밋 `5d7eda23c`(stage2a)는 UPDATE 로그를 stage1h와 거의 같게 쓴다(레코드 15,338 대 16,066, 로그 118쪽 대 123쪽, 위 귀속 절). 그런데 drain 지연은 stage2와 같다(filler 13.5 대 12, stage1h는 1).
   - 비슷한 UPDATE 로그에서 두 빌드가 다르게 행동한다. stage1h는 1,000행(로그는 2,000행의 약 절반인 8K 레코드로 가정한다. 선형 가정이고 이 행 수에서는 재지 않았다)에서 filler 2개로 끝난다. stage2fix는 그보다 많은 UPDATE 로그(2,000행, 10.2K 레코드, 93쪽)에서 filler 12개가 필요하다. 필요한 추가 로그가 약 60쪽(12 filler × 5.2쪽, 두 block)이다. 이는 두 빌드의 UPDATE 로그 차이(2,000행에서 123쪽 대 93쪽, 30쪽)보다 크고 cycle마다 같다.
   - 따라서 UPDATE의 로그 양이 지연을 정하지 않는다. vacuum이 옛 chunk를 지우려면 UPDATE 뒤 로그가 두 block쯤 더 필요한 어떤 이유가 `5d7eda23c`부터 생겼고, 그 이유는 찾지 못했다.
3. **그래서 다음 cycle의 UPDATE가 100쪽 더 필요하다: 반박.** 근거는 셋이다.
   - `big`에서 drain이 1 filler로 끝나 stage1h와 같은 속도가 되었는데 stage2와 stage2fix의 cycle별 peak는 그대로 2,001에서 2,101이고 sector는 33이다(3회 × 6 cycle, 두 빌드 모두 변함없음).
   - 지연과 페이지 증가가 같이 움직이지 않는다. 1,000행에서는 drain이 가장 늦는데(filler 15, 5.5 s) 페이지 증가가 0이다(1,001에서 1,001, sector 16 대 16). 6,000행에서는 drain이 stage1h와 같은데(filler 1) 증가가 +301쪽(+5.0%)이다.
   - harness의 drain은 `Oos_num_recs`가 목표에 도달할 때까지 기다린 뒤에 다음 단계로 간다. 모든 모드에서 옛 chunk는 다음 UPDATE 전에 이미 지워져 있다.
4. **새로 알게 된 것: 파일 크기 증가는 파일에 비례하는 약 5%다 (측정함).** 2,000행의 +1 sector는 일회성이 아니었다. +100쪽, +201쪽, +301쪽이 첫 cycle peak의 정확히 5.0%이고, sector 증가는 +1, +3, +5개(32에서 33, 63에서 66, 94에서 99: 각 +3%, +4.8%, +5.3%)다. 1,000행에서는 0이다. 원인은 모른다. 이 비례 관계가 더 큰 파일에서도 유지되는지는 재지 않았다. ADR-0009 결정 4의 페이지 조항은 10% 허용치 안이므로 충족하지만, sector 조항을 허용치 없이 읽으면 파일이 클수록 초과 sector가 늘어난다.

### 한계

- 행 수 시험은 서버 실행 2회, 부하가 높았다(중앙값 137). filler 수의 범위가 넓은 칸(4,000행 stage1h 1-9 등)이 있다.
- 1,000행의 stage1h UPDATE 로그 양은 선형 가정이다.
- 가설 시험에서 stage2는 `b8a7e5d74`의 복사본 설치를 썼다. 복사한 설치가 원본과 같은 동작인지 `cubrid --version`(11.5.0.2803-b8a7e5d)과 결과 일치(stage2와 stage2fix의 모든 행)로만 확인했다.
- 5% 증가와 drain 지연의 원인은 모른다. `5d7eda23c`(fast path 제거)에서 시작되었다는 것까지만 안다.

## 한계

- 공용 서버에서 load average 13-207 아래 측정했다(본 측정은 33-138). 1 ms 이하의 차이는 가릴 수 없다. 단건 INSERT에서 2단계가 최대 1 ms 느려졌을 가능성은 배제하지 못한다.
- 단일 OOS 크기(10 KB, 7 KB), 파일 약 2만 쪽, 단일 세션 churn만 쟀다. 집합 상한(4,096쪽)에 닿는 경우, 동시 쓰기와 rollback이 섞인 churn, 다중 chunk 값은 재지 않았다.
- 6,000행 시험은 서버 실행 2회, 칸당 4회다. 차이가 크고 범위가 겹치지 않지만 표본이 작다. 2,000행의 소규모 시험은 본 측정과 부호가 달랐다.
- 원인 설명 중 측정한 것은 로그 레코드, 호출 수, `perf` 점유, 문장 시간이다. set 복사가 비용의 전부인지는 수정 후 재측정으로만 알 수 있다. 100쪽 증가, drain 지연, dirty 페이지 감소의 구체 원인은 확인하지 않았다.
- 서버 카운터는 filler 보정을 써서 단계별 값이 근사다. DML 구간(filler 없음)의 값만 정확하다.
- 파일 크기의 sector 조항 해석은 ADR 문장이 정하지 않는다. 1 sector 차이의 판정은 사용자 몫이다.
- 동시 INSERT에서 bestspace mutex 점유(집합 복사 구간)가 다른 OOS 파일에 미치는 영향은 재지 않았다.
- 단위 테스트(`unit_tests/oos`)는 실행하지 않았다. 수정판의 단위 테스트는 부모 세션이 통과(debug, 10/10)했다고 전했고 여기서 재실행하지 않았다.
- 수정판에서도 집합이 4,096쪽에 닿는 경우와 동시 INSERT에서 bestspace mutex 점유 영향은 재지 않았다. 6,000행 churn의 집합은 약 3,000쪽이다.

## ADR 판정

| 조건 | 판정 | 근거 |
| --- | --- | --- |
| ADR-0010 결정 7: INSERT 시간이 1단계보다 나빠지지 않는다 (`b8a7e5d74` 기준. 수정판 `f8cdfca747`은 충족, 위 절) | **일부 미충족** | 단건 INSERT 5개 항목은 충족(차이 구별 불가, 짝 검정 p ≥ 0.21). 집합이 큰 대량 UPDATE는 미충족(6,000행 UPDATE, cycle 2 이후 372-386 ms에서 980-1,000 ms. 시험 두 번) |
| ADR-0010 결정 7: churn 뒤 파일 크기가 커지지 않는다 | 충족(조건부) | sector 33 대 32. 2,000행에서 증가는 cycle 2에서 한 번이고 20 cycle 동안 누적되지 않음. 단 행 수 시험에서 증가가 파일의 약 5%(4,000행 +3, 6,000행 +5 sector)임이 드러났다("로그 block 가설 시험" 절) |
| ADR-0009 결정 4: cycle별 peak가 첫 cycle peak + max(2쪽, 10%) 이내 | 충족 | 2,001, 2,101(+100, 허용 201), 20 cycle 평평 |
| ADR-0009 결정 4: 재INSERT 뒤 예약 sector가 첫 peak를 넘지 않는다 | 해석에 따라 다름 | 33 sector(2,112쪽) 대 첫 peak 2,001쪽(32 sector). 허용치 없이 읽으면 1 sector 초과 |

## 산출물

- 소스: `CBRD-27925-emptied-set` `b8a7e5d74`와 `f8cdfca747`, 측정용 detached worktree `/home/vimkim/gh/cb/CBRD-27872-after3`(지금 `f8cdfca747`), `CBRD-27872-after2h`(`94ed2ea46`), `CBRD-27872-after2m`(`5d7eda23c`). 설치는 `~/.cub/install/CBRD-27872-after3`(`f8cdfca747`), `-after3-b8a7e5d74`(이전 2단계의 복사본), `-after2h`, `-after2m`의 `release_gcc`. 정리하지 않았다.
- 출력 디렉터리: `/mnt/nvme/data-5/tmp/w878/measure`(run 1), `measure-h`(run 2), `measure-counters`, `measure-h-counters`, `attrib-counters`, `measure-h-perf`, `measure-h-perf6000`, `attrib-create`(stage2a DB), `fix`(수정판 DB와 본 측정), `fix-counters`, `fix-perf6000`, `hyp`, `hyp-rows1000`, `hyp-rows4000`, `hyp-rows6000`. 처음 시도한 감시자 없는 카운터(전부 0)는 `measure-counters-nowatcher-all-zero`에 남겼다.
- 원자료: [bench/](bench/) 아래 `results-reuse-*.csv`(카운터 CSV의 run 3이 귀속 시험, run 4가 수정판. cycle 수별 CSV의 run 3이 수정판. 가설 시험은 `results-reuse-logtraffic.csv`), `loadavg-reuse-*.txt`, `perf-reuse/`(`perf report` 텍스트, 집합 크기 시험, drain 시험).
- 스크립트: [growth_cost.py](bench/growth_cost.py)(변경 없음), [summarize.py](bench/summarize.py)(변경 없음), [paired_rounds.py](bench/paired_rounds.py), [churn_peak.py](bench/churn_peak.py), [churn_counters.py](bench/churn_counters.py), [churn_scale.py](bench/churn_scale.py), [perf_churn.py](bench/perf_churn.py), [drain_probe.py](bench/drain_probe.py), [log_traffic_churn.py](bench/log_traffic_churn.py), [logtraffic_summary.py](bench/logtraffic_summary.py).
