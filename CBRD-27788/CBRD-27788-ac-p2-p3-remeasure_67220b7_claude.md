# CBRD-27788 후속: AC-P2·AC-P3 재측정 (`67220b7e2`)

작성일 2026-11-12, Asia/Seoul. 작성: Claude Code 세션(Work920).
관련: [CBRD-27788](https://jira.cubrid.org/browse/CBRD-27788) 후속 범위(2026-11-11 추가), [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785) AC-P2·AC-P3, [PR #7990](https://github.com/CUBRID/cubrid/pull/7990).

PR #7990(OOS 통합)을 develop에 병합하기 전에, 리뷰어가 요구한 성능 근거 두 가지를 잰다.
AC-P2는 4~16KB 값 전체 읽기, AC-P3은 PR #8299 병합본 `67220b7e2`에서 heap→heap과 overflow→OOS의 성능 저하다.

## 수치를 읽는 법

- 변화율은 `(base − X) / base`다. 좋아지면 +, 나빠지면 −다. CBRD-27785와 같은 부호다.
- 판정 지표는 서버 프로세스의 `instructions:u` 중앙값이다. 잠정 목표는 −2%보다 나쁘지 않은 것이다.
- cycles와 실행 시간은 참고다. 공유 호스트의 load average가 측정 중 9.6~83.2(1분, io 표본 기준)였다. 아래 [cycles](#cycles)를 본다.

## 결론

- **AC-P2, 기본 임계값: 목표 밖.** `67220b7e2`의 4~16KB 값 전체 읽기는 develop보다 명령어를 2.8~69.5% 더 쓴다. 값이 작을수록 나쁘다. 리뷰어 병합 기준 ②("기본 설정에서 4~16KB 행의 전체 읽기가 develop보다 느려지지 않을 것")를 충족하지 못한다.
- **AC-P2, threshold 파라미터: 존재하지 않는다.** `67220b7e2`에 OOS threshold 시스템 파라미터가 없다. 임계값은 [`heap_oos_inline_target_size()`](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/src/storage/heap_file.c#L13746)가 계산하는 고정값이다. 한 페이지에 행 4개(`HEAP_OOS_MIN_RECS_PER_PAGE 4`)가 들어가는 크기라서 16KiB 페이지에서 약 4KB다. 그래서 브리프의 "설정한다" 단계는 할 수 없었다.
- **AC-P2, 임계값을 overflow 경계로 올린 sketch: 목표 안.** 측정 전용 커밋 `9a304a9d04`(push하지 않음)는 임계값을 develop의 overflow 경계 `heap_Maxslotted_reclength`로 바꾼다. 4~16KB 값이 develop처럼 heap에 남고, 같은 12개 전체 읽기가 −0.24%~+0.08%다. 파라미터나 기본값을 이렇게 바꾸면 기준 ②를 충족할 수 있다는 근거다. 제품 코드 변경은 아니다.
- **AC-P3, heap→heap(일반 작은 행): 목표 안.** scan −0.55%, 조건 scan +0.03%, UPDATE −1.06%, `bench.py compare` narrow·wide는 명령어가 1.53%·2.05% 적다(두 라운드 모두 `within_budget`).
- **AC-P3, overflow→OOS(22KB 행): 부분 목표 밖.** 큰 값 하나를 읽는 Q4는 −0.40%(restart-only)·−0.49%(warm)로 목표 안이다. 모든 컬럼을 읽는 Q5는 −6.05%·−6.07%로 목표 밖이다. `dcbf09e`의 Q5 −6.6%와 거의 같다. 작은 컬럼 조회 Q1~Q3은 +38~72%다.

## 측정 조건

| 항목 | 값 |
| --- | --- |
| base | develop merge-base `2dd94e32ab86a756b0f1ea2123ad7d2ac913321b` (worktree `oos-perf-27788r-dev`) |
| head | `feature/oos-merge` `67220b7e230ff1587ba5940001d72e10477a1fc4` (PR #8299 squash) |
| sketch | `9a304a9d043e47be4bd0494ceedd754cc5ab70a6` = head + [threshold-sketch.patch](remeasure-20261111/threshold-sketch.patch). 로컬 전용 |
| 빌드 | GCC 11.5.0, RelWithDebInfo, `-O2 -ggdb3 -DNDEBUG -finline-functions`, preset `release_gcc_nounit`. 세 빌드 모두 `compile_commands.json`에 `CUBRID_UNIT_TEST_ENABLED`가 0건 |
| 서버 | `cub_server` SHA-256 앞 16자리: base `b53446a48bc9eaf7`, head `b8917c39c2dc763d`, sketch `5b0a2026ac8572ab`. 서버 CPU 16–19 고정, 한 번에 서버 하나 |
| conf | 공통 `data_buffer_size=512M`, `log_buffer_size=16M`, `max_clients=20`, `max_query_cache_entries=0`, `query_cache_size_in_pages=0`. `[@sw27788]`는 `data_buffer_size=4G`, `log_buffer_size=256M`. page 16KiB |
| locale | DB `en_US`, charset utf8(5), 모든 테이블 `COLLATE utf8_bin`. 서버·client `LANG=en_US.UTF-8` |
| UPDATE 시작 상태 | `ordinary.py` 그대로 매 표본 새 복제본 |
| 장비 | Intel Xeon Gold 5218R, 80 cores, 공유 호스트 |

`release_gcc` preset으로 처음 만든 세 빌드는 서버 코드에 `-DCUBRID_UNIT_TEST_ENABLED`가 들어가 있어 폐기했다. preset 자체는 별도 작업으로 고쳤다.

## 실제 저장 위치

`SHOW HEAP CAPACITY`와 `SHOW HEAP OOS`로 확인했다.

| 입력 | base | head | sketch |
| --- | --- | --- | --- |
| sweep 4.6/6.0/9.9/13.8KB, 각 20,000행 | heap (avg 4,646/6,032/9,872/13,763B) | heap→OOS. heap 55B, OOS 값 20,000개/표 | heap, base와 같은 pages |
| io heap 14.5KB, 100,000행 | heap 14,480B, 100,001 pages | heap→OOS. heap 4,012B, 33,337 pages, OOS 값 200,000 | heap 14,480B, 100,001 pages |
| io overflow 22KB, 100,000행 | overflow 100,000행, 200,085 pages | overflow→OOS. heap 2,756B, 20,001 pages, OOS 값 400,000 | overflow→OOS. heap 15,008B, 100,001 pages, OOS 값 100,000 (`cold_1` 7,000B) |
| 일반 `r*_seed`·`n` | heap 92B·108B | 같음 | 같음 |

같은 overflow 입력에서 head는 값 4개, sketch는 1개, 10/27의 `dcbf09e`는 3개를 OOS로 보낸다. 같은 overflow→OOS라도 읽는 OOS 값의 수가 다르다.

## AC-P2: 4~16KB 값 전체 읽기 (4G 버퍼)

[`sweep.py`](remeasure-20261111/sweep.py). 20,000행, `big VARCHAR(20000)`은 SHA2-512 hex 연결이다. 6.0KB가 리뷰어 `w` 표와 같은 크기다.
질의는 `SUM(LENGTH(big))`, `SUBSTR(big,4000,1)='a'`, `big LIKE '%G%'`(hex에 없는 문자라 모든 byte를 읽는다), 작은 컬럼 `COUNT(*), SUM(a)`다.
엔진마다 2라운드(순서 base→head→sketch, sketch→head→base), 라운드마다 질의별 6회 중 첫 회 제외, 유지 표본 10개다.

| 값 | 질의 | base 명령어 | head | sketch | 세 엔진 중 최대 spread |
|---|---|---:|---:|---:|---:|
| 4.6KB | length | 183.1M | −42.20% | +0.08% | 0.58% |
| 4.6KB | substr | 344.4M | −21.98% | −0.06% | 0.26% |
| 4.6KB | LIKE 전체 | 104.6M | −69.50% | −0.24% | 0.63% |
| 4.6KB | 작은 컬럼 | 30.3M | −4.70% | −0.10% | 0.69% |
| 6.0KB | length | 292.5M | −23.63% | −0.02% | 0.62% |
| 6.0KB | substr | 478.4M | −13.97% | −0.03% | 0.19% |
| 6.0KB | LIKE 전체 | 192.5M | −33.27% | +0.05% | 0.11% |
| 6.0KB | 작은 컬럼 | 41.9M | +24.31% | −0.46% | 0.69% |
| 9.9KB | length | 576.0M | −6.48% | −0.05% | 0.76% |
| 9.9KB | substr | 831.5M | −4.18% | −0.11% | 0.27% |
| 9.9KB | LIKE 전체 | 415.7M | −7.33% | −0.10% | 0.41% |
| 9.9KB | 작은 컬럼 | 76.6M | +58.64% | −0.09% | 0.86% |
| 13.8KB | length | 892.0M | −4.12% | +0.07% | 0.51% |
| 13.8KB | substr | 1,219.7M | −2.77% | +0.00% | 0.02% |
| 13.8KB | LIKE 전체 | 667.4M | −4.55% | +0.03% | 0.06% |
| 13.8KB | 작은 컬럼 | 76.6M | +58.65% | −0.41% | 0.82% |

- 라운드별 변화율은 모두 0.15%p 안에서 같다([cpu-summary.json](remeasure-20261111/cpu-summary.json)의 `cpu_per_start`).
- 값이 작을수록 나쁜 이유는 값마다 붙는 고정 비용(OOS 페이지 고정과 복사)이 값의 크기에 비해 커지기 때문으로 본다(추론, 프로파일로 확인하지 않았다). 4.6KB 작은 컬럼 조회의 −4.70%도 이득이 아니다. heap이 97 pages로 줄었는데도 명령어가 늘었다. 원인은 미확인이다.
- io_bench의 heap 입력(14.5KB, heap→OOS)도 같은 방향이다. Q4 −8.14%, Q5 −6.18%이고 sketch는 −0.02%·+0.08%다.

## AC-P3: heap→heap (일반 작은 행, 4G 버퍼)

[`ordinary.py`](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/contrib/benchmarks/oos-performance/ordinary.py)와 `bench.py`(`67220b7e2`의 하네스, 양쪽 같은 사본)다. 200,000행.

| 질의 | base 명령어 | head 명령어 | head | sketch | 유지 표본 | spread base / head |
|---|---:|---:|---:|---:|---:|---:|
| scan `COUNT(*), SUM(a)` | 65.3M | 65.7M | −0.55% | −0.55% | 8 | 0.13% / 0.15% |
| 조건 scan `SUBSTR(s,30,1)='a'` | 505.4M | 505.2M | +0.03% | +0.04% | 8 | 0.01% / 0.04% |
| UPDATE + COMMIT, 새 복제본 | 6,475.2M | 6,543.6M | −1.06% | −0.88% | 8 | 0.35% / 6.24% |

- `bench.py compare --max-overhead-percent 2`: narrow −1.53%, wide −2.05~−2.06% overhead(명령어가 적다), 두 라운드·두 엔진 모두 exit 0 `within_budget`.
- head UPDATE의 spread 6.24%는 라운드 1의 표본 하나(6,940.6M, −7.2%) 때문이다. 나머지 유지 표본 7개는 6,532.3~6,556.4M이다. [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816)의 vacuum이 계수 구간에 들어온 패턴으로 본다(추론, 이 표본에서 확인하지 않았다). 중앙값은 두 라운드 모두 −1.09%다.

## AC-P3: overflow→OOS와 이득 (512M 버퍼, io_bench)

10/27과 같은 하네스(`io_bench.py` SHA-256 `cebf4d37…`, fixture 동일)다. cache·layout·질의·엔진마다 5개 표본이다. restart-only는 표본마다 서버 재시작, warm은 같은 서버에서 warmup 1회 뒤 5회다. 엔진 순서는 반복마다 바꿨다.
시간은 base / head / sketch 초 단위 중앙값, ioread는 엔진 페이지 읽기다.

| cache | 입력 | 질의 | base 명령어 | head | sketch | 시간 (초) | ioread |
|---|---|---|---:|---:|---:|---|---|
| restart-only | overflow | Q1 | 897.6M | +71.57% | +26.19% | 1.50 / 0.29 / 0.79 | 200,087 / 20,003 / 100,003 |
| restart-only | overflow | Q2 | 950.9M | +71.85% | +44.32% | 1.57 / 0.37 / 0.87 | 200,094 / 20,003 / 100,007 |
| restart-only | overflow | Q3 | 1,506.7M | +38.00% | +33.27% | 2.61 / 1.22 / 1.92 | 200,903 / 20,258 / 100,274 |
| restart-only | overflow | **Q4** | 7,952.7M | **−0.40%** | −2.68% | 2.24 / 1.90 / 1.86 | 200,087 / 120,003 / 150,003 |
| restart-only | overflow | **Q5** | 23,406.4M | **−6.05%** | −1.31% | 3.43 / 4.37 / 3.25 | 200,087 / 220,003 / 150,003 |
| warm | overflow | Q1 | 858.3M | +72.27% | +23.80% | 0.78 / 0.09 / 0.36 | 167,397 / 0 / 67,309 |
| warm | overflow | Q2 | 907.4M | +72.46% | +45.29% | 0.82 / 0.15 / 0.43 | 167,494 / 0 / 67,406 |
| warm | overflow | Q3 | 1,462.6M | +38.51% | +33.40% | 1.74 / 1.43 / 3.07 | 167,903 / 0 / 67,524 |
| warm | overflow | **Q4** | 7,913.4M | **−0.49%** | −3.24% | 1.43 / 1.26 / 1.26 | 167,397 / 87,315 / 136,860 |
| warm | overflow | **Q5** | 23,367.6M | **−6.07%** | −1.49% | 2.80 / 3.46 / 2.65 | 167,397 / 187,315 / 136,860 |
| restart-only | heap | Q1 | 510.5M | +37.65% | +0.01% | 0.80 / 0.43 / 0.77 | 100,003 / 33,339 / 100,003 |
| restart-only | heap | Q4 | 5,825.1M | −8.14% | −0.02% | 1.27 / 1.71 / 1.23 | 100,003 / 133,339 / 100,003 |
| restart-only | heap | Q5 | 15,401.7M | −6.18% | +0.08% | 2.10 / 2.89 / 2.09 | 100,003 / 133,339 / 100,003 |
| warm | heap | Q1 | 479.3M | +39.46% | −0.03% | 0.37 / 0.10 / 0.37 | 67,313 / 651 / 67,309 |
| warm | heap | Q4 | 5,794.0M | −8.16% | −0.02% | 0.77 / 1.14 / 0.77 | 67,313 / 100,651 / 67,309 |
| warm | heap | Q5 | 15,370.8M | −6.18% | +0.08% | 1.66 / 2.27 / 1.62 | 67,313 / 100,651 / 67,309 |

Q2·Q3 heap 행과 spread는 [io-summary.json](remeasure-20261111/io-summary.json)에 있다. 표본 spread는 warm heap Q3(2.31%) 말고 모두 2% 미만이다.

- **overflow→OOS 판정.** Q4는 목표 안, Q5는 목표 밖(−6.05%)이다. 한 행에서 OOS 값 4개를 읽는 Q5의 비용이 남아 있다. `dcbf09e` 대비 Q5 −6.6% → −6.05%로 거의 그대로다.
- **sketch의 overflow→OOS.** 큰 값 하나만 OOS로 보내므로 Q5는 −1.31%로 목표 안이고, Q4(그 값 `cold_1`을 읽는다)는 −2.68%로 목표 밖이다. 작은 컬럼 이득은 head보다 작다(Q1 +26%).
- head의 실행 시간은 overflow Q4에서 빨라졌고(2.24 → 1.90초), Q5에서 느려졌다(3.43 → 4.37초). 공유 호스트라 판정에 쓰지 않는다.

<a id="cycles"></a>
## cycles

명령어 수가 같은 경우에도 cycles가 크게 흔들렸다. 예를 들어 sweep 4.6KB substr의 sketch는 명령어 −0.06%인데 cycles −54.6%다. sketch는 이 질의에서 base와 같은 코드 경로를 탄다(같은 heap 저장, 명령어 동일). 따라서 이 cycles 차이는 엔진 비용이 아니라 측정 중 호스트 간섭으로 본다(추론). 이 실행의 cycles로는 판정하지 않는다. 값은 요약 JSON에 남겼다.

## 하지 않은 것

- 파일 캐시 해제 후(`file-evict`) 표본은 이번에 재지 않았다. 큰 값 cold read 지연은 [CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791) 범위다.
- threshold 파라미터 구현, 기본값 변경, PR·JIRA 갱신은 하지 않았다.
- 조용한 장비에서 실행 시간을 판정하지 않았다. CPU 프로파일로 4.6KB의 원인을 확인하지 않았다.
- 리뷰어 원문 `reproduce.py`(`w` 표 연속 UPDATE 포함)는 돌리지 않았다. 6KB 전체 읽기는 sweep의 w47로 대신했다.

## 재현과 원시 근거

- 측정 도구: [driver.py](remeasure-20261111/driver.py), [sweep.py](remeasure-20261111/sweep.py), [summarize.py](remeasure-20261111/summarize.py), [tables.py](remeasure-20261111/tables.py). io_bench는 commit `1a8cbefa4`의 `io_bench.py`·`bench.py`다.
- 순서: `driver.py prepare --label {base,head,thr}` → `driver.py smoke` → `driver.py cpu --rounds 2` → `driver.py io` → `summarize.py cpu`, `summarize.py io`.
- 원시 산출물(작성자 로컬): `/mnt/nvme/data-5/tmp/CBRD-27788-20261111-remeasure`. 표본별 SQL, stdout, stderr, perf, `/proc/PID/io`, 저장 진단, paramdump, spacedb, conf, 빌드 로그가 있다. 폐기한 unit-test 빌드의 산출물은 `discarded-unit-test-build/`, `base-unit-test-discarded/`에 따로 두었다.
