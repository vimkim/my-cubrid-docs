# PR #7990 성능 평가: develop 머지 판단 근거

작성일 2026-11-19, Asia/Seoul. 대상 [PR #7990](https://github.com/CUBRID/cubrid/pull/7990)(`feature/oos-merge` → develop).
독자는 팀장과 PR #7990 리뷰어(shparkcubrid, hornetmj)다. OOS 내부 구조를 몰라도 읽을 수 있게 썼다.
관련 이슈: [CBRD-26357](https://jira.cubrid.org/browse/CBRD-26357), [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785), [CBRD-27788](https://jira.cubrid.org/browse/CBRD-27788), [CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781).

**이 문서는 새 측정이 아니다.** 기존 측정 보고서를 모아 머지 판단에 필요한 것만 정리했다. 인용한 수치는 원 보고서와 원시 산출물(요약 JSON, CSV)에서 다시 확인했다. 숫자마다 측정한 revision과 출처를 적었다.

## 1. 결론

**성능 면에서 develop 머지를 막을 근거는 없다.** 근거는 다음과 같다.

- **OOS 값이 없는 일반 테이블은 느려지지 않았다.** 최종 측정 head `2c38bef05b`에서 scan, 조건 scan, UPDATE의 서버 명령어 수는 develop 대비 −2.0%~+1.2%다. 잠정 목표(+2% 이내)를 모두 지켰다. 리뷰어가 처음 보고한 +7~10% 증가는 PR #8299로 없어졌다.
- **OOS의 이득과 손해를 모두 쟀고 공개했다.** 큰 값이 있는 행에서 작은 컬럼만 읽으면 명령어 수가 38~72% 줄고 페이지 읽기가 최대 90% 줄어든다. 반면 큰 값까지 모두 읽으면 명령어가 약 6~8% 늘고, 파일 캐시가 비어 있는 조건에서는 큰 값 조회가 2.5배 느려진 경우가 있다.
- **리뷰어의 병합 기준 2(4~16KB 행 전체 읽기)는 리뷰어가 바꾼 조건으로 받았다.** 기본 임계값에서는 2.8~69.5% 더 쓰지만, 임계값을 한 페이지로 올리면 develop과 차이가 없다(−0.08%~+0.24%). shparkcubrid는 2026-11-17에 "임계값을 시스템 파라미터로 제공하고(CBRD-28062) 기본값은 11.5 전에 조정"하는 조건으로 승인했다.
- **#8434가 처음에 만든 커밋 지연은 해결됐다.** 행 하나 UPDATE+COMMIT 3000회에서 동기 로그 flush(`fdatasync`)는 develop 3011회, 최종 측정 head 3006회로 같다.
- **남은 손해는 후속 이슈로 추적한다.** 바뀌지 않은 큰 값을 UPDATE 때 다시 쓰는 비용([CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230), #8559)과 OOS 값 읽기의 CPU 비용([CBRD-28064](https://jira.cubrid.org/browse/CBRD-28064))이다. CBRD-27230은 리뷰어가 guava(11.5) 포함을 요구했다.

## 2. 용어와 수치 읽는 법

| 용어 | 뜻 |
| --- | --- |
| heap | 테이블 행이 저장되는 기본 페이지(16KiB)다. |
| overflow | develop에서 한 페이지에 들어가지 않는 큰 행을 여러 페이지에 이어서 저장하는 방식이다. 행 전체가 overflow로 간다. |
| OOS | Out-of-row Overflow Storage. 이 PR이 추가한 저장 방식이다. 행의 큰 가변 길이 값만 별도 파일로 옮기고, 행에는 그 위치만 남긴다. 작은 컬럼만 읽는 질의는 큰 값을 읽지 않아도 된다. |
| OOS 임계값 | 행이 이 크기를 넘으면 큰 값부터 OOS로 옮긴다. 지금은 한 페이지에 행 4개가 들어가는 크기(16KiB 페이지에서 4,060B)로 고정이다. 그래서 develop에서 heap에 있던 4~16KB 행도 OOS로 간다. |
| 명령어 수 | DB 서버 프로세스(`cub_server`)가 질의를 처리하는 동안 실행한 사용자 공간 CPU 명령어 수(`perf stat`의 `instructions:u`)다. 같은 일을 하면 같은 값이 나오고 호스트 부하에 거의 흔들리지 않는다. 판정은 이 값으로 한다. |
| 실행 시간 | 경과 시간(wall-clock)이다. 측정 장비가 여러 사람이 함께 쓰는 서버라서 크게 흔들린다. 참고로만 쓴다. |
| AC-P1, AC-P2, AC-P3 | [성능 수락 기준](../cbrd-27785/CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md)의 세 항목이다. 아래 3절에서 설명한다. |
| 잠정 2% | 명령어 수가 develop보다 2% 넘게 늘지 않으면 목표 충족으로 본다. 작성자 측이 정한 잠정 목표이며 리뷰어가 이 수치를 승인한 기록은 없다. |

**부호.** 이 문서의 %는 모두 **(PR − develop) ÷ develop**이다. **+이면 PR이 명령어나 시간을 더 쓴다(나빠짐). −이면 덜 쓴다(좋아짐).** 리뷰어의 PR 댓글과 같은 방향이다. 링크한 CBRD-27785·CBRD-27788 보고서는 반대 부호(좋아지면 +)를 쓰므로, 거기서 가져온 값은 부호를 바꿔 적었다.

## 3. 무엇을 쟀나

shparkcubrid의 [2026-10-28 성능 의견](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6461744209)은 머지 기준 세 가지를 제시했다. 수락 기준서는 이를 AC-P1~P3로 옮겼다.

| 기준 | 쉬운 말로 | 판정 방법 |
| --- | --- | --- |
| **AC-P1** 일반 테이블 회귀 없음 | OOS 값이 하나도 없는 보통 테이블이 PR 때문에 느려지면 안 된다. 모든 사용자가 영향을 받는 경로다. | 명령어 수 +2% 이내 |
| **AC-P2** 기본 임계값의 4~16KB 행 | develop에서 heap에 있던 4~16KB 행이 기본 설정에서 OOS로 옮겨진다. 이 행을 통째로 읽을 때 develop보다 느려지면 안 된다는 리뷰어 기준이다. | 이번 수락에서 제외하고 임계값 파라미터 후속으로 옮겼다. 리뷰어가 2026-11-17 동의했다. |
| **AC-P3** OOS의 이득과 손해 공개 | 큰 값이 있는 테이블에서 무엇이 빨라지고 무엇이 느려지는지 숫자로 보여야 한다. 같은 저장 방식끼리의 비교(develop overflow → PR OOS)는 +2% 목표로 평가한다. | 이득·손해 보고. overflow→OOS 비교에 2% 적용 |

| 측정 | 측정 revision (PR / develop) | 날짜 | 덮는 기준 | 출처 |
| --- | --- | --- | --- | --- |
| 최종 가벼운 확인 P1-a, P1-b | `2c38bef05b` / `2e67e1d948` | 2026-11-19 | AC-P1 | [final light check](../CBRD-27788/CBRD-27788-pr7990-final-light-perf_2c38bef.md) |
| 최종 가벼운 확인 P3-d (행 단위 UPDATE+COMMIT) | `2c38bef05b` / `2e67e1d948` | 2026-11-19 | AC-P3 (UPDATE 지연) | 같은 문서 |
| AC-P2·AC-P3 재측정 (sweep, 일반 테이블, io_bench Q1~Q5) | `67220b7e2` / `2dd94e32` (merge-base) | 2026-11-12 | AC-P1, AC-P2, AC-P3 | [AC-P2·AC-P3 재측정](../CBRD-27788/CBRD-27788-ac-p2-p3-remeasure_67220b7_claude.md) |
| OOS SELECT 실측과 파일 캐시 해제 진단 | `dcbf09e` / `4781495f` | 2026-10-27~28 | AC-P3 (I/O) | [OOS SELECT 실측](../CBRD-27788/CBRD-27788-oos-select-performance_dcbf09e_codex.md), [지연 진단](../CBRD-27788/CBRD-27788-oos-cold-read-diagnosis_dcbf09e_codex.md) |
| #8434 지연·churn 재측정 | `ca1c1176fc` / `3e541fcf67` | 2026-11-17 | AC-P3 (UPDATE churn) | [latency-merged](../cbrd-27781/latency-merged/README.md) |
| PR #8299 일반 행 CPU 개선 | `4c3c8d791` / `4781495f`, `855f220d5` / `50619ce53` | 2026-11-03, 11-10 | AC-P1 (이력) | [CBRD-27816 1단계](../cbrd-27785/CBRD-27816-ordinary-update-phase1.md), [새 base 재측정](../cbrd-27785/pr8299-newbase-perf.md) |

공통 조건: GCC 11.5.0 release 빌드(RelWithDebInfo, `-O2`), 16KiB 페이지, locale `en_US.utf8`. 장비는 Intel Xeon Gold 5218R 80 CPU 공유 서버다. 서버는 한 번에 하나만 띄우고 develop과 PR을 교대로 쟀다.

## 4. 결과

### 4.1 AC-P1: 일반 테이블은 느려지지 않았다

최종 측정 head `2c38bef05b` 대 develop `2e67e1d948`이다. develop `2e67e1d948`은 이 head가 마지막으로 합친 develop이다. 데이터는 4G 버퍼에 모두 올라간 상태다. PR 쪽 테이블에 OOS 파일이 없음을 `SHOW HEAP OOS`로 확인했다.

| 작업 | develop 명령어 | PR 명령어 | 증감 | 판정 |
| --- | ---: | ---: | ---: | --- |
| 200,000행 80B 행 scan, narrow (`bench.py`, scan 20회 합) | 6,785.3M | 6,689.4M | **−1.41%** | 목표 충족 |
| 같은 표 wide scan | 12,260.9M | 12,017.2M | **−1.99%** | 목표 충족 |
| 리뷰어 질의 `COUNT(*), SUM(a)` (200,000행) | 65.80M | 66.21M | **+0.62%** | 목표 충족 |
| 리뷰어 질의 `SUBSTR(s,30,1)='a'` | 505.8M | 505.6M | **−0.04%** | 목표 충족 |
| 리뷰어 질의 `UPDATE ... SET a=a+1; COMMIT` | 6,366.7M | 6,444.2M | **+1.22%** | 목표 충족 |

- 표본: `bench.py`는 빌드·case마다 24개, 리뷰어 질의는 12개다. 호출 3번의 중앙값끼리 차이(호출 간 spread)는 0.23% 이하다.
- `bench.py compare --max-overhead-percent 2`는 세 라운드 모두 `within_budget`(exit 0)이다.
- 실행 시간 차이도 작다(scan −0.07%~+0.14%, UPDATE +1.43%). 다만 판정에는 쓰지 않는다.

이전 측정과의 흐름은 다음과 같다. 모두 명령어 수다.

| 시점 | PR / develop | scan | 조건 scan | UPDATE | 출처 |
| --- | --- | ---: | ---: | ---: | --- |
| 리뷰어 측정, PR #8299 전 | `4408135c` / `4781495f` | +8.0% | +9.9% | +7.0% | [리뷰어 댓글](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6461744209) |
| PR #8299 적용 후 | `4c3c8d791` / `4781495f` | −0.79% | +0.83% | +1.34% | [PR #8299 본문](../cbrd-27785/pr8299-sign-rule-pr-body.md) |
| PR #8299 병합 후 | `67220b7e2` / `2dd94e32` | +0.55% | −0.03% | +1.06% | [재측정](../CBRD-27788/CBRD-27788-ac-p2-p3-remeasure_67220b7_claude.md) |
| 최종 측정 head | `2c38bef05b` / `2e67e1d948` | +0.62% | −0.04% | +1.22% | [final light check](../CBRD-27788/CBRD-27788-pr7990-final-light-perf_2c38bef.md) |

**UPDATE의 남은 약 1%.** [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816) 1단계에서 원인을 나눴다. 늘어난 몫 중 하나는 OOS 열이 없는 행에서도 도는 OOS 처리(약 61M 명령어)다. 이를 줄이는 빠른 경로는 효과가 약 0.3~0.4%p로 추정되어 구현하지 않기로 했고, CBRD-27816은 2026-11-11 종결됐다. 또 UPDATE 뒤 비동기 vacuum이 측정 구간에 들어온 표본은 develop 중앙값 대비 최대 약 +7.9%(계산값)까지 나올 수 있다. 중앙값 판정은 이 표본에 흔들리지 않는다.

### 4.2 AC-P3 이득: 큰 값이 있는 행에서 작은 컬럼만 읽는 질의

`67220b7e2` 대 merge-base `2dd94e32`, 100,000행, 버퍼 512M다([재측정](../CBRD-27788/CBRD-27788-ac-p2-p3-remeasure_67220b7_claude.md)).
"overflow 입력"은 develop에서 행 전체(약 22KB)가 overflow로 저장되는 테이블이다. "heap 입력"은 develop에서 14.5KB 행이 heap에 들어가는 테이블이다. PR에서는 둘 다 큰 값이 OOS로 간다.
Q1은 작은 컬럼 합계, Q2는 id 100,000건 반환, Q3은 인덱스로 범위 조회 1,000회다. restart-only는 표본마다 서버를 재시작한 조건, warm은 버퍼에 데이터가 올라온 조건이다.

| 입력 | 질의 | cache | 명령어 증감 | 실행 시간 (develop → PR) | 엔진 페이지 읽기 (develop → PR) |
| --- | --- | --- | ---: | --- | --- |
| overflow | Q1 | restart-only | **−71.6%** | 1.50 → 0.29 s | 200,087 → 20,003 |
| overflow | Q2 | restart-only | −71.9% | 1.57 → 0.37 s | 200,094 → 20,003 |
| overflow | Q3 | restart-only | −38.0% | 2.61 → 1.22 s | 200,903 → 20,258 |
| overflow | Q1 | warm | −72.3% | 0.78 → 0.09 s | 167,397 → 0 |
| heap | Q1 | restart-only | **−37.7%** | 0.80 → 0.43 s | 100,003 → 33,339 |
| heap | Q1 | warm | −39.5% | 0.37 → 0.10 s | 67,313 → 651 |

- 이득의 이유: heap에는 작은 컬럼만 남아 페이지 수가 줄어든다. overflow 입력에서는 heap 페이지가 200,085개에서 20,001개로 줄었다.
- 저장장치까지 읽는 조건: `dcbf09e` 측정에서 OS 파일 캐시를 비운 뒤 overflow 입력 Q1의 실행 시간은 1.81 → 0.90 s(−50%), OS 읽기 바이트는 3,146 → 1,650 MiB였다([OOS SELECT 실측](../CBRD-27788/CBRD-27788-oos-select-performance_dcbf09e_codex.md)). 반면 heap 입력 Q1은 OS 읽기 바이트가 줄지 않았다(1,577 → 1,641 MiB). heap 입력의 엔진 페이지 읽기 감소를 저장장치 읽기 감소로 일반화할 수 없다.

### 4.3 AC-P3 손해: 큰 값까지 읽거나 바꾸는 작업

같은 재측정에서 Q4는 큰 값 하나(7,000B 컬럼 `cold_1`)의 내용을 모두 비교하고, Q5는 모든 컬럼을 읽는다.

| 입력 | 질의 | cache | 명령어 증감 | 실행 시간 (develop → PR) | 2% 평가 |
| --- | --- | --- | ---: | --- | --- |
| overflow → OOS | Q4 | restart-only | +0.40% | 2.24 → 1.90 s | 목표 충족 |
| overflow → OOS | Q4 | warm | +0.49% | 1.43 → 1.26 s | 목표 충족 |
| overflow → OOS | **Q5** | restart-only | **+6.05%** | 3.43 → 4.37 s | **목표 밖** |
| overflow → OOS | **Q5** | warm | **+6.07%** | 2.80 → 3.46 s | **목표 밖** |
| heap → OOS | Q4 | restart-only | +8.14% | 1.27 → 1.71 s | 관측값 (AC-P2 영역) |
| heap → OOS | Q5 | restart-only | +6.18% | 2.10 → 2.89 s | 관측값 (AC-P2 영역) |

- **Q5 +6%는 수락 기준에서 통과로 표시하지 않는다.** 행 하나에서 OOS 값 4개를 읽는 비용이다. 값마다 페이지를 고정하고 복사하는 비용이 붙는다. 이 경로는 임계값 파라미터로 피할 수 없다. 한 페이지를 넘는 행은 OOS를 써야 하기 때문이다. [CBRD-28064](https://jira.cubrid.org/browse/CBRD-28064)(guava)에서 값당 CPU 비용을 줄인다. OOS 읽기마다 붙는 head page sector 확인은 [CBRD-28187](https://jira.cubrid.org/browse/CBRD-28187)에서 다룬다.
- **파일 캐시를 비운 큰 값 조회.** `dcbf09e`에서 OS 파일 캐시를 비운 뒤 overflow 입력 Q4는 2.32 → 5.72 s로 약 2.5배 느려졌다. CPU와 엔진 페이지 읽기 수는 늘지 않았고 파일 읽기 대기가 늘었다. 읽는 위치와 순서가 흩어진 것이 원인이다([지연 진단](../CBRD-27788/CBRD-27788-oos-cold-read-diagnosis_dcbf09e_codex.md)). 개선은 [CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791)에서 추적한다. 이 조건은 `67220b7e2` 이후 다시 재지 않았다.
- **작은 컬럼만 바꾸는 UPDATE.** 지금은 UPDATE가 바꾸지 않은 OOS 값도 새로 쓴다. 리뷰어는 `4408135c`에서 6KB 값 테이블의 `update w set a=a+1`이 +73.7%, 큰 값 UPDATE가 +34.6%라고 보고했다([댓글](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6461744209)). 승인 때는 6KB 값 행에서 정수 컬럼 하나만 바꾸고 바로 커밋하는 UPDATE 3000번이 develop보다 실행 시간이 45~90% 더 걸렸다고 적었다([승인 리뷰](https://github.com/CUBRID/cubrid/pull/7990#pullrequestreview-5932172762)). 작성자 측은 이 경우를 최종 head에서 다시 재지 않았다. 바뀌지 않은 값을 재사용하는 [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)([#8559](https://github.com/CUBRID/cubrid/pull/8559), OPEN)으로 줄인다. 리뷰어는 이를 후속으로 미루지 말고 guava(11.5)에 포함하라고 요구했다.

### 4.4 AC-P3: UPDATE+COMMIT 지연과 UPDATE churn

OOS 값을 회수하는 시점을 삭제 확정 뒤로 바꾼 [#8434](https://github.com/CUBRID/cubrid/pull/8434)(CBRD-27781, CBRD-27237)는 처음에 커밋마다 동기 로그 flush를 하나 더 붙였다. 2026-11-11 측정에서 행 하나 UPDATE+COMMIT 3000회가 18.83 → 31.09 s(+65%)였고 `fdatasync`는 3011 → 6006회였다. develop 대상 [#8495](https://github.com/CUBRID/cubrid/pull/8495)(CBRD-28046)가 이 flush를 없앴다. 두 PR 모두 최종 측정 head `2c38bef05b`에 들어 있다.

| 측정 | 지표 | develop | PR | 출처 |
| --- | --- | --- | --- | --- |
| 최종 head, 행 하나 6,000B 값 UPDATE+COMMIT 3000회 | `fdatasync` (3번씩) | 3011 | 3006 | [final light check](../CBRD-27788/CBRD-27788-pr7990-final-light-perf_2c38bef.md) |
| 같은 작업 | 실행 시간 중앙값 (9번씩) | 4.66 s | 3.99 s | 같은 문서 |
| #8434 대 `feature/oos-merge`, 3000행 UPDATE churn | 두 번째 UPDATE 로그 | 38.10 MB | 22.36 MB (−41%) | [latency-merged](../cbrd-27781/latency-merged/README.md) |
| 같은 측정 | UPDATE와 vacuum 뒤 OOS 페이지 | 3,513 | 1,502 | 같은 문서 |

- P3-d의 실행 시간 −14.4%는 속도 향상의 근거로 쓰지 않는다. 두 빌드의 사분위 범위(develop 3.21~5.73 s, PR 3.62~5.51 s)가 겹친다. "느려지지 않음"의 근거로만 쓴다.
- P3-d는 develop에서는 heap, PR에서는 OOS에 저장되는 값이다. 같은 저장 정책끼리의 비교가 아니라 사용자가 보는 커밋 지연의 관측값이다.
- churn 측정의 기준은 develop이 아니라 #8434 직전의 `feature/oos-merge`다. 회수 방식 변경의 효과를 보여 준다.

### 4.5 AC-P2: 기본 임계값의 4~16KB 행 전체 읽기 (후속으로 넘김)

`67220b7e2` 대 `2dd94e32`, 20,000행, 4G 버퍼다. 같은 입력을 세 엔진으로 쟀다. "임계값 sketch"는 임계값만 한 페이지(`heap_Maxslotted_reclength`)로 올린 측정 전용 빌드(`9a304a9d04`, push하지 않음)다.

| 값 크기 | 큰 값 전체 읽기 (3개 질의) 명령어 증감: 기본 임계값 | 같은 질의: 임계값 sketch | 작은 컬럼만 읽기: 기본 / sketch |
| --- | --- | --- | --- |
| 4.6KB | +22.0% ~ +69.5% | −0.08% ~ +0.24% | +4.70% / +0.10% |
| 6.0KB | +14.0% ~ +33.3% | −0.05% ~ +0.03% | −24.3% / +0.46% |
| 9.9KB | +4.2% ~ +7.3% | +0.05% ~ +0.11% | −58.6% / +0.09% |
| 13.8KB | +2.8% ~ +4.6% | −0.07% ~ +0.00% | −58.7% / +0.41% |

- 기본 임계값에서는 4~16KB 값 12개 경우 모두 develop보다 명령어를 더 쓴다(+2.8~+69.5%). 값이 작을수록 나쁘다. 리뷰어 원래 기준 ②를 충족하지 못한다.
- 임계값을 한 페이지로 올리면 값이 develop처럼 heap에 남고 차이가 없다. 대신 작은 컬럼 조회의 이득도 사라진다.
- 그래서 임계값을 서버 파라미터 `oos_trigger_threshold`로 제공하기로 했다([CBRD-28062](https://jira.cubrid.org/browse/CBRD-28062), draft [#8632](https://github.com/CUBRID/cubrid/pull/8632)). 기본값은 지금과 같고, 값별 측정 뒤 11.5 전에 정한다. 리뷰어는 [이 제안](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6912604550)을 [2026-11-17 승인](https://github.com/CUBRID/cubrid/pull/7990#pullrequestreview-5932172762)에서 받았다.
- **AC-P2는 통과가 아니다.** 기본 설정의 손해는 남아 있고, 파라미터는 아직 병합되지 않았다.

## 5. 리뷰어가 제기한 성능 문제와 처리

| 제기 | 내용 | 처리 | 상태 |
| --- | --- | --- | --- |
| shparkcubrid [10/27](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6434778190), [10/28](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6461744209) | 일반 테이블 +7~10%, 큰 값 scan +39~41%, 작은 컬럼 UPDATE +73.7%, 머지 기준 1~3 | [10/27 답변](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6441306406)에서 CBRD-27785로 분리. 기준 1은 PR #8299(병합 2026-11-11), 기준 2는 파라미터 조건으로 변경, 기준 3은 CBRD-27788 측정 | 4.1, 4.5, 4.2~4.4절 |
| shparkcubrid [승인 리뷰 11/17](https://github.com/CUBRID/cubrid/pull/7990#pullrequestreview-5932172762) | 기준 2 변경 수락. CBRD-27237 반영과 CBRD-27230 guava 포함 요구 | CBRD-27237은 #8434로 병합(2026-11-18). CBRD-27230은 #8559 OPEN | CBRD-27230 남음 |
| hornetmj [R3](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399899312) | 새 OOS 페이지가 필요한 INSERT가 파일 전체를 훑는 sweep. 재시작 직후 첫 INSERT 0.23~0.25 s | [답글](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4585762624)에서 [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872)로 추적. #8434 병합 뒤에는 빈 페이지 후보 집합을 먼저 보고, 파일이 "모름"으로 표시된 경우에만 순회한다(코드 주석 기준). 순회 자체를 없애는 [#8493](https://github.com/CUBRID/cubrid/pull/8493)(CBRD-27925)은 draft | 측정하지 않음 |
| hornetmj [R4](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409283403) | 재시작 뒤 빈 공간 정보(bestspace)가 사라져 OOS 파일이 커짐 | 리뷰어가 "bestspace redesign 안정화 후 적용"을 밝혔다. [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213)에서 추적 | 후속 |

hornetmj의 리뷰 상태는 COMMENTED이며 승인 기록은 없다. PR의 reviewDecision은 APPROVED다(2026-11-19 조회).

## 6. 측정 head와 현재 head의 차이

최종 측정 head는 `2c38bef05b`다. 여기에는 PR #8299(일반 행 CPU), #8348, #8416(STORAGE FORCE_INLINE), #8434, develop을 거친 #8495, 그리고 CBRD-28194 vacuum 수정(`2c38bef05b` 자체)이 들어 있다. 4.1절과 4.4절의 결론은 이 head의 측정이다. 그 뒤의 변경은 다음과 같다.

- **현재 PR head `e262e79fab`**(2026-11-19 조회): `2c38bef05b`에 develop `2e66081fd2`를 합친 것이다. 들어온 develop 커밋 4개는 broker CAS의 schema info, IN 서브쿼리 rewrite 조건, memmon 합계, cubridmanager submodule이다. heap, OOS, vacuum, 로그 코드는 바꾸지 않았다(diffstat 확인).
- **아직 push하지 않은 로컬 커밋**: CBRD-28254 수정 `6be0dc083e`와 develop `86b3c49c10` 재동기화 `71993ddb63`이다. CBRD-28254는 다중 컬럼 인덱스 키를 만들 때 행이 옛 representation이면 그 속성 위치로 찾도록 고친다. 행이 현재 representation이면 representation id 비교 한 번만 더한다. 측정한 테이블은 단일 컬럼 PK만 있어서 이 경로를 지나지 않는다. 재동기화로 들어온 develop 변경은 restoredb 페이지 포맷, SA compactdb, `NTH_VALUE`다.
- **판단(추정, 재측정하지 않음):** 위 변경은 측정한 scan·UPDATE·OOS 읽기 경로를 바꾸지 않으므로 성능 결론을 바꾸지 않는다고 본다. 다중 컬럼 인덱스가 있는 테이블의 INSERT·UPDATE·DELETE는 재지 않았다.
- **4.2·4.3·4.5절은 `67220b7e2`의 측정이다.** 그 뒤에 들어온 #8348, #8434, CBRD-28194는 vacuum과 회수 경로를 바꿨고, #8416은 컬럼 STORAGE 선택지를 더했다. 이 변경들은 OOS 값을 읽는 경로를 바꾸지 않으므로 Q1~Q5와 sweep 결론은 유지된다고 본다(추정, 최종 head에서 재측정하지 않음. #8416이 기본 저장 위치를 바꾸지 않는지도 따로 확인하지 않았다).

## 7. 한계와 후속

**측정의 한계**

- 모든 측정은 여러 사람이 함께 쓰는 80코어 서버에서 했다. 최종 확인 중 1분 load는 15~39였다. 명령어 수는 거의 흔들리지 않았지만 실행 시간은 판정에 쓸 수 없다.
- 최종 확인은 사용자가 요청한 가벼운 확인이다. 인계 문서의 반복 수보다 적다(P1-b 3라운드, 4라운드 ABBA 아님). develop 빌드는 broker 파일 하나에 `#include <ctype.h>`를 로컬로 더해 빌드했다(`cub_server`와 무관).
- 최종 head에서 재지 않은 시나리오: 연속 UPDATE와 vacuum 비용(P1-c), OOS SELECT Q1~Q5(P3-a), 리뷰어 6KB `w` 표(P3-b), INSERT·UPDATE churn(P3-c). 4.2~4.5절은 `67220b7e2`의 값이다.
- 리뷰어의 "작은 컬럼 UPDATE 45~90% 느림"은 작성자 측이 재현하지 않았다.
- 파일 캐시를 비운 조건은 `dcbf09e` 이후 재지 않았다. 동시 세션 부하와 다중 chunk 값은 재지 않았다.
- 잠정 2% 목표는 작성자 측의 기준이다. 리뷰어가 이 수치를 승인한 기록은 없다. 리뷰어 원래 기준 1은 "측정 노이즈 제외, 느려지지 않을 것"이다.

**통과로 표시하지 않은 항목**

| 항목 | 상태 | 후속 |
| --- | --- | --- |
| AC-P2 기본 임계값 4~16KB 전체 읽기 | +2.8~+69.5%, 목표 밖 | [CBRD-28062](https://jira.cubrid.org/browse/CBRD-28062) 파라미터(#8632 draft), 기본값은 측정 후 11.5 전 결정 |
| AC-P3 overflow→OOS Q5 | +6.05%, 목표 밖 | [CBRD-28064](https://jira.cubrid.org/browse/CBRD-28064) OOS 값 읽기 CPU, [CBRD-28187](https://jira.cubrid.org/browse/CBRD-28187) head page 확인 |
| 작은 컬럼 UPDATE의 OOS 값 재기록 | 리뷰어 측정 +45~90%(시간) | [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230) #8559, guava 필수 |
| 파일 캐시를 비운 큰 값 조회 | 2.32 → 5.72 s | [CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791) 읽기 지역성 |
| OOS 페이지 할당 sweep, 재시작 뒤 공간 정보 | 미측정 | [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872), [CBRD-27925](https://jira.cubrid.org/browse/CBRD-27925) #8493 draft, [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213) |

## 8. 출처와 원시 산출물

- 수락 기준: [CBRD-27785 성능 수락 기준](../cbrd-27785/CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md)
- 최종 가벼운 확인: [CBRD-27788 final light check](../CBRD-27788/CBRD-27788-pr7990-final-light-perf_2c38bef.md). 원시 산출물은 Git 밖의 작성자 로컬(`/home/vimkim/tk/perf-7990/`, `summary.json`, `runs/`)에 있다. 이 문서의 4.1·4.4절 값은 그 `summary.json`과 `runs/P1a/compare-r*.txt`에서 다시 확인했다.
- AC-P2·AC-P3 재측정: [보고서](../CBRD-27788/CBRD-27788-ac-p2-p3-remeasure_67220b7_claude.md), [cpu-summary.json](../CBRD-27788/remeasure-20261111/cpu-summary.json), [io-summary.json](../CBRD-27788/remeasure-20261111/io-summary.json)
- OOS SELECT와 I/O: [실측](../CBRD-27788/CBRD-27788-oos-select-performance_dcbf09e_codex.md), [지연 진단](../CBRD-27788/CBRD-27788-oos-cold-read-diagnosis_dcbf09e_codex.md), [measurement-summary_dcbf09e.json](../CBRD-27788/measurement-summary_dcbf09e.json)
- 일반 행 CPU: [CBRD-27816 1단계](../cbrd-27785/CBRD-27816-ordinary-update-phase1.md), [PR #8299 새 base 재측정](../cbrd-27785/pr8299-newbase-perf.md)
- #8434 지연: [#8495 적용 재측정](../cbrd-27781/latency-8495/README.md), [병합 base 재측정](../cbrd-27781/latency-merged/README.md), [churn 로그·페이지](../cbrd-27781/perf.md)
- PR #7990 본문과 리뷰: `gh pr view 7990`, `gh api repos/CUBRID/cubrid/pulls/7990/reviews`, 2026-11-19 조회
