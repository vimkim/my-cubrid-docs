# PR #8299 narrow scan cycles 변동의 원인

관련 이슈: [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785).
관련 PR: [draft PR #8299](https://github.com/CUBRID/cubrid/pull/8299).
작성일: 2026-11-03, Asia/Seoul.

## Purpose

- 이 문서는 PR #8299의 리뷰 수정이 cycles를 늘렸는지 판단할 근거를 남긴다. 독자는 PR 리뷰어와 CBRD-27785의 성능 수락을 판단하는 사람이다.
- 지난 측정에서 narrow scan cycles 중앙값은 +12.86%였고 하위 10% 값은 -0.05%였다. 원인은 확인하지 못했다([지난 측정](CBRD-27785-review-fixes_5837393_claude.md#cycles)).
- AS-IS: 공유 호스트의 소음과 서버 시작 사이의 변동이 섞여서 cycles 차이를 판정할 수 없었다.
- TO-BE: 조용한 시간에 서버 시작 단위로 다시 재고, 시작마다 달라지는 원인을 counter와 sample로 확인한다.
- 결론: 측정 전에 정한 회귀 기준은 충족하지 않는다. 다만 리뷰 수정 빌드는 서버 시작의 약 절반에서 narrow scan이 약 14% 느려진다. 원인은 PR이 바꾸지 않은 parallel scan 코드의 분기 하나가 코드 배치에 따라 분기 예측에서 충돌하는 현상이다.

## Implementation

### 대상 revision

| 이름 | commit | 설명 |
|---|---|---|
| head | `f8114e432d3e97cc7a11149ab8ac852de4a1b935` | 리뷰 수정 전 PR head |
| fix | `5837393ffb9d69bccb93271d63b0e38b884e0ed4` | 리뷰 수정 후 PR head |

- 두 빌드는 `release_gcc` preset으로 만들었다. 정규화한 compile command 1,077개가 모두 같다. head 쪽 cache에 켜져 있던 `UNIT_TEST_*` 옵션은 fix와 맞추려고 껐다.
- 현재 PR head `4c3c8d791`은 측정하지 않았다. 이 commit은 OOS로 내보내는 기준을 4,086B에서 4,060B로 바꾼다. 아래 벤치마크 표의 행은 평균 92~108B라서 이 기준에 닿지 않는다. 다만 코드 배치는 바뀌므로 아래의 느린 시작 비율은 그 빌드에서 다를 수 있다.

### 환경

- Intel Xeon Gold 5218R 2 socket, socket당 20 core, core당 2 thread. governor는 performance, turbo는 켜져 있다. kernel은 `5.14.0-570.30.1.el9_6`이다.
- 서버는 CPU 16~19, `csql`은 CPU 12에 고정했다.
- DB는 각 빌드로 따로 만들었다. 측정 테이블의 charset과 collation은 양쪽 모두 `utf8`과 `utf8_bin`이다.
- 다른 사용자가 함께 쓰는 호스트다.

### 작업

| 경우 | 질의 또는 작업 | 한 sample |
|---|---|---|
| narrow | `SELECT SUM(CAST(v AS BIGINT)) FROM n;` | 200,000행 표를 20번 scan |
| wide | `SELECT SUM(CAST(id AS BIGINT)), SUM(CAST(v AS BIGINT)), SUM(LENGTH(payload)) FROM n;` | 200,000행 표를 20번 scan |
| scan, predicate, update | 일반 scan, 조건 scan, UPDATE | 200,000행 표에 한 번 |

- 표 `n`은 `id INTEGER PRIMARY KEY, v INTEGER, payload VARCHAR(80)`이고 payload는 `'x'` 80개다. OOS로 갈 크기의 컬럼은 없다.
- 각 sample은 서버 pid에 붙인 `perf stat -e cycles:u,instructions:u`로 잰다.
- 한 block은 서버를 한 번 시작해 다섯 경우를 모두 잰다. narrow와 wide는 block당 8 sample, 나머지는 block당 4 sample이다. 각 묶음의 첫 실행은 버린다.

### 소음 관리

- 각 block 전에 60초 동안 다른 사용자의 CPU 사용률을 쟀다. 전체 80 CPU 기준 5.0% 이하이고, 고정한 CPU와 그 SMT 짝 10개가 각각 10% 이하일 때만 시작했다.
- block은 자체 systemd user scope에서 돌렸다. 다른 사용자의 사용률은 호스트 전체 busy 시간에서 scope 사용량을 빼서 1초마다 기록했다.
- 측정 중 평균이 5.0%를 넘거나 1초 값의 상위 5%가 10%를 넘으면 그 block을 버렸다. 버린 block이 있는 라운드는 양쪽을 모두 버리고 새로 쟀다.
- 라운드는 ABBA 순서로 12개다. 34 block을 돌려 24 block을 채택했다. 채택한 block은 04:17부터 08:17 사이에 돌았고, block별 다른 사용자 사용률 평균은 3.1~4.9%였다.
- 처음 기준은 3.5%였다. 00:08부터 01:45까지 60초 구간 112개 중 통과한 구간이 없어서, block을 하나도 돌리기 전에 사용자 결정으로 5%로 바꿨다.

### 판정 기준

측정 전에 다음 기준을 정했다.

- fix의 서버 시작 단위 cycles 중앙값이 2% 넘게 높고, rank-sum p가 0.01 미만이고, 라운드 사이에서 방향이 일정하면 회귀로 본다.
- 그렇지 않으면 측정 가능한 cycles 회귀가 없다고 본다.
- 코드 배치 가설이 맞으면, fix가 느린 서버 시작의 비율을 늘리는지 따로 본다.

### 진단

- **서버 시작 단위 counter.** 양쪽을 각각 13번 시작했다. 10번은 보통 방식이고 3번은 `setarch -R`로 주소 무작위 배치(ASLR)를 껐다. 시작마다 narrow 20회를 네 번 재고, 매번 다른 front-end와 분기 counter를 함께 쟀다.
- **분기 예측 실패 위치.** fix를 4번 더 시작해 `perf record -e br_misp_retired.all_branches:upp -c 997`과 `perf record -e baclears.any:u -c 9973`로 sample을 모았다.

## Remarks

### 본 측정 결과

서버 시작 하나에 경우별 중앙값 하나를 쓴다. 양쪽 각 12개다.

| 경우 | 명령어 수 차이 | cycles 중앙값 head | cycles 중앙값 fix | cycles 차이 | rank-sum p | fix가 느린 라운드 |
|---|---:|---:|---:|---:|---:|---:|
| narrow | -1.33% | 2.519e9 | 2.704e9 | +7.37% | 0.011 | 12/12 |
| wide | -1.78% | 4.849e9 | 4.922e9 | +1.50% | 1.000 | 6/12 |
| scan | -1.81% | 9.127e7 | 9.233e7 | +1.15% | 0.011 | 9/12 |
| predicate | -0.81% | 2.018e8 | 2.004e8 | -0.67% | 0.033 | 3/12 |
| update | -0.46% | 3.287e9 | 3.279e9 | -0.25% | 0.817 | 5/12 |

- 명령어 수는 지난 측정과 같다. 다섯 경우 모두 fix가 적다.
- narrow는 두 갈래로 나뉜다. head는 12번 모두 2.50~2.55e9였다. fix는 6번 2.52~2.54e9였고 6번 2.87~2.91e9였다.
- fix가 빠른 상태였던 6개 라운드에서 fix narrow는 같은 라운드의 head보다 0.0~1.0% 높다.
- wide도 같은 시작에서 함께 움직인다. narrow가 느린 fix 시작에서 wide는 +2.7~+6.3%였고, 빠른 시작에서는 -1.4~-2.8%였다.
- 느린 시작 비율의 차이(head 0/12, fix 6/12)는 Fisher 단측 p=0.0069다.

### 진단 결과

| 시작 상태 | narrow cycles (20회) | 명령어 수 | 분기 예측 실패 | BAClear | 해당 시작 |
|---|---:|---:|---:|---:|---|
| fix 빠름 | 2.54~2.56e9 | 6.81~6.83e9 | 5.8e4~7.3e4 | 2.0e5~2.8e5 | 무작위 5/10, ASLR 끔 3/3 |
| fix 느림 | 2.87~2.89e9 | 6.82~6.83e9 | 4.06e6~4.08e6 | 2.3e7~2.5e7 | 무작위 5/10 |
| head 보통 | 2.51~2.58e9 | 6.91~6.94e9 | 5.6e4~8.9e4 | 1.6e5~3.4e5 | 무작위 6/10, ASLR 끔 3/3 |
| head 약한 변형 | 2.54~2.56e9 | 6.90~6.91e9 | 6.5e4~7.7e4 | 8.2e6 | 무작위 4/10 |

- head 보통 행의 범위에서 head `r0`는 뺐다. 이 시작은 소음 구간에서 돌아 2.64e9였다.
- 느린 fix 시작도 명령어 수는 같다. 같은 일을 하면서 분기 예측 실패가 약 65배, BAClear가 약 100배 많다.
- ASLR을 끈 시작에서는 양쪽 모두 3번 모두 빨랐다. fix 2.543~2.553e9, head 2.518~2.578e9다.
- head에도 BAClear만 약 40배 늘어나는 상태가 있다. 이때 cycles 차이는 1% 안쪽이고 분기 예측 실패는 늘지 않는다.
- 본 측정과 합치면 느린 시작은 head 0/22, fix 11/22다. Fisher 단측 p=9.2e-5다.

### 분기 예측 실패 위치

- fix 4번 시작 중 2번이 느렸다. 느린 시작에서 분기 예측 실패 sample의 97.45%가 `parallel_scan::result_handler<RESULT_TYPE::BUILDVALUE_OPT>::write`의 `+0x53` 한 곳에서 나왔다.
- 이 위치는 [`px_scan_result_handler.cpp:2028`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/src/query/parallel/px_scan/px_scan_result_handler.cpp#L2028)의 `if (agg_list->operand_prog_state == 1)`이다. 행마다 실행되고 첫 compile 뒤에는 매번 같은 쪽으로 간다.
- PR #8299는 이 파일을 바꾸지 않는다. PR이 바꾼 파일은 `heap_file.c`, `heap_file.h`, `heap_oos.cpp`, `heap_oos.hpp`, `oos_file.cpp`, `locator_sr.c`다.
- 같은 시작의 BAClear sample은 `tp_value_find_converter`, 위의 `write`, `qdata_sum_acc_add_dbv`에 모였다. 빠른 시작에서는 분기 예측 실패가 한 곳에 몰리지 않았다.

### 해석

- 측정: 느린 상태는 서버 시작마다 정해지고, 한 시작 안에서는 유지된다. ASLR을 끄면 시작마다 같은 상태가 된다.
- 추론: 매번 같은 쪽으로 가는 분기가 매번 틀리려면 분기 예측기가 이 분기의 정보를 잃어야 한다. 다른 분기와 예측기 항목을 다투면 그렇게 된다. 이 충돌 여부가 라이브러리를 메모리 어디에 올리는지에 따라 달라진다.
- 추측: 충돌 상대는 바로 앞에서 호출하는 `__tls_get_addr`(ld-linux)일 수 있다. 4번의 시작에서 libc와 libcubrid 사이 거리는 같았고 ld-linux와 libcubrid 사이 거리는 매번 달랐다. 충돌 상대는 확인하지 않았다.
- 추론: PR의 heap 읽기 로직이 일을 더 하는 것은 아니다. PR이 libcubrid.so 안의 코드 위치를 옮겨서 이 분기가 충돌하는 확률이 바뀌었다. 다른 변경이 들어오면 다시 바뀔 수 있다.

### 판정

- 기준의 세 조건 중 p<0.01과 라운드 사이 일관을 충족하지 않는다. 측정 전에 정한 회귀 기준으로는 회귀가 아니다.
- 추가 확인 항목에서는 차이가 있다. fix 빌드는 이 CPU에서 서버 시작의 약 절반이 느린 상태다. 그 상태에서 narrow scan cycles는 약 14% 높다.
- 사용자 영향: 실제 서버는 ASLR을 켠 채 시작한다. 이 빌드라면 시작에 따라 이 질의가 약 14% 느릴 수 있다. 원인 코드는 OOS와 관계없는 parallel scan 집계 경로다.

### 한계

- CPU 모델 하나(Cascade Lake)에서만 쟀다. 분기 예측기 구조가 다른 CPU에서는 결과가 다를 수 있다.
- `4c3c8d791`과 develop은 이번에 재지 않았다. develop 대비 판단은 [과거 측정](CBRD-27785-common-reader_067aae4_codex.md)에 있다.
- 진단의 head `r0` 시작은 01:41에 다른 사용자 사용률 6.38%에서 돌았다. 나머지 진단은 08:18~08:44에 3.07~3.54%에서 돌았다.
- 충돌 상대와 그 조건은 확인하지 않았다.

### 별도 이슈 후보

- `px_scan_result_handler.cpp`의 행마다 실행되는 상태 확인과 thread-local 접근은 코드 배치에 따라 크게 느려질 수 있다. OOS와 관계없는 parallel query 문제라서 이 PR에서는 다루지 않는다.

### 재현 자료

[pr8299-quiet-20261103/](pr8299-quiet-20261103/)에 요약 출력을 보존한다.

- `pooled.txt`는 채택한 24 block의 모든 sample을 합친 비교다.
- `per-start.txt`는 서버 시작 단위 중앙값, rank-sum, 라운드별 차이다.
- `diag.txt`는 진단 26번 시작의 counter다.
- `misp.txt`는 분기 예측 실패 sample 위치 상위 항목이다.
