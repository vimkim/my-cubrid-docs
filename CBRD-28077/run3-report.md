# CBRD-28077 시나리오별 성능 비교: develop · OOS · Sidecar · Inner Table

- 이슈: [CBRD-28077](https://jira.cubrid.org/browse/CBRD-28077) (상위 CBRD-26978). 관련: CBRD-26357(OOS), CBRD-28053(Sidecar), CBRD-28054(Inner Table), CBRD-27230, CBRD-27872
- 측정: 2026-11-13 02:20 ~ 03:01 (Asia/Seoul), 실행 `run-20261113-0220` (3차 실행). 1차 실행 보고서는 [benchmark-report.md](benchmark-report.md)이고, 1차 결과를 팀장 검토용 논문 형식으로 정리한 글은 [lead-report.md](lead-report.md)다.
- 전체 표: [run3-tables.md](run3-tables.md) (모든 지표, 반복 흔들림, 결과 일치 검사, 저장 공간). 도구: [tools/](tools/)

## 1. 결론

큰 값이 행 밖으로 나가는 4 KB·8 KB·64 KB 값에서 develop 대비 서버 명령어 수(drain 포함)를 비교했다. 작을수록 좋다.

| 무엇을 하는가 | OOS | Sidecar | Inner Table | 한 줄 해석 |
| --- | --- | --- | --- | --- |
| 작은 컬럼만 읽는 scan (S1) | ×0.03~0.85 | ×0.02~0.37 | ×0.02~0.24 | 세 설계 모두 크게 이긴다. IO가 있을 때 OS 읽기가 develop의 0~6%다. |
| 큰 값을 읽는 scan (S2) | ×1.05~3.03 | ×0.98~1.71 | **×2.03~21.95** | Inner Table은 값마다 chunk를 B-tree로 하나씩 찾아 모은다. |
| PK 조회, 작은 컬럼 (S3n) | ×0.74~0.99 | ×0.75~1.01 | **×1.05~1.74** | Inner Table은 index 경로에서 큰 컬럼을 고르지 않아도 chunk를 읽는다(코드 확인). |
| 작은 컬럼 UPDATE (S5) | **×3.90~11.29** | ×0.08~0.65 | ×0.50~1.04 | OOS는 바꾸지 않은 큰 값을 매번 다시 적재한다(CBRD-27230). |
| 큰 값 교체 UPDATE (S6) | **×2.33~597** | ×1.47~2.17 | **×3.01~8.21** | 모두 develop보다 비싸다. OOS는 빈 페이지 회수 sweep이 파일 전체를 훑는 경우가 있다(CBRD-27872). |
| 반복 UPDATE+COMMIT (S7·S8b·S8s) | ×1.00~2.04 | ×0.70~1.27 | ×0.94~1.61 | Sidecar가 develop과 가장 가깝다. |
| DELETE (S9) | ×0.33~1.23 | ×0.35~1.30 | **×1.32~6.08** | OOS·Sidecar는 작은 heap 덕에 싸고, Inner Table은 chunk 행을 모두 지운다. |
| 8 client 동시 UPDATE·INSERT (S11·S12) | ×1.08~2.43 | ×1.01~1.05 | ×1.08~1.54 | 동시 접속에서도 Sidecar가 develop과 가장 가깝다. |
| 기능 미사용 (100 B, 모든 시나리오) | ×0.92~1.12 | ×0.92~1.12 | ×0.96~1.12 | develop끼리의 차이(×0.95~1.16)와 같은 폭이다. |

- **Sidecar**는 작은 컬럼 scan에서 크게 이기고, 작은 컬럼 UPDATE에서도 develop보다 싸다. 대가는 큰 값 교체(×1.5~2.2)와 적재(×1.14~1.26)다. 이번 workload에서 develop보다 나빠지는 폭이 가장 작다.
- **OOS**는 작은 컬럼 scan에서 이기지만, UPDATE 계열에서 손해가 크다. 원인 두 가지를 프로파일로 확인했다. 바꾸지 않은 값의 재적재(CBRD-27230)와, 새 OOS 페이지를 할당할 때 파일 전체를 훑는 빈 페이지 회수 sweep(CBRD-27872)이다. 둘 다 이미 등록된 이슈다.
- **Inner Table**은 작은 컬럼 scan에서 가장 크게 이기지만, 큰 값을 읽거나(S2) 지우거나(S9) 교체할 때(S6) 가장 비싸다. PK 조회의 chunk 읽기는 index scan 경로가 참조 확장 생략 flag를 켜지 않기 때문이다.
- 이 수치는 모두 HA를 끈 조건(`ha_mode=off`)이다. Sidecar와 Inner Table의 HA 지원이 없어서 생긴 차이는 아니다(6.5절).

## 2. 이번 실행에서 신뢰도를 높인 방법

| 1차 실행의 한계 | 3차 실행에서 바꾼 것 |
| --- | --- |
| 변경 시나리오를 1회만 측정 | 모든 변경을 조건마다 3회 측정했다. 반복마다 서로 겹치지 않는 행을 고쳐, 테이블을 다시 적재하지 않고도 반복이 같은 일을 하게 했다. 읽기는 조건마다 3회다. |
| 빌드마다 기준 develop 커밋이 다름 | develop `e64a04a79`(Sidecar의 기준)를 다섯 번째 빌드로 넣어, develop 커밋 사이의 차이를 직접 쟀다. 결과는 대부분 ×0.95~1.10이다. 그래서 develop 기준이 다른 데서 오는 오차는 설계 사이의 차이보다 훨씬 작다. |
| 빌드를 차례로 측정해 서로 다른 부하를 받음 | 다섯 빌드를 동시에 실행했다. 모든 빌드가 같은 시간대의 같은 부하를 받는다. |
| 결과가 맞는지 확인하지 않음 | 측정한 문장 240개의 결과 digest와 영향받은 행 수, 단계별 테이블 checksum 20개를 빌드끼리 비교했다. 모두 일치했다. |
| 값이 의도한 크기인지 확인하지 않음 | 단계마다 `bit_length(big)`가 의도한 크기가 아닌 행을 세었다. 모든 빌드, 모든 단계에서 0행이었다. 이 검사를 넣게 된 계기는 6.4절의 harness 결함이다. |
| 경계 근처 크기가 없음 | 4 KB 값을 넣었다. 행이 행 밖 이동 기준(약 4,060 B)을 막 넘는 크기로, develop은 페이지에 3행을 담는다. |
| 동시 접속이 없음 | 8 client가 동시에 큰 값을 UPDATE+COMMIT(S11)하거나 INSERT+COMMIT(S12)하는 시나리오를 넣었다. |

반복 사이의 흔들림((최대-최소)/중앙값)은 명령어 수가 중앙값 0.05, 상위 10% 0.20이었다. 경과 시간은 중앙값 0.30, 상위 10% 1.77이었다. 그래서 결론은 명령어 수와 page·IO 횟수로 내리고, 경과 시간은 참고로만 둔다.

## 3. 비교 대상과 방법

| 빌드 | 브랜치 | 커밋 | 비고 |
| --- | --- | --- | --- |
| develop | `develop` | `a7f220d5d7` | 비율의 기준 |
| develop e64a | `develop` | `e64a04a79a` | 대조군. Sidecar의 기준 develop |
| OOS | `feature/oos-merge` | `c02f897268` | 행이 약 4,060 B를 넘으면 큰 값부터 OOS 파일로 |
| Sidecar | `sidecar` | `7c5028d5bd` | 기본값(`sidecar_inline_target`=4060) |
| Inner Table | `inner-table` | `fbb4f25057` | `inner_table_threshold`=4060, `t__inner` 생성 |

- 빌드: `release_gcc`(GCC 11.5, RelWithDebInfo). develop `a7f220d5d7`, OOS, Sidecar는 `-Wno-error=return-local-addr`을 더해 빌드했다(경고 처리만 바꾸고 생성 코드는 그대로다). 모든 DB는 `ha_mode=off`, `stored_procedure=no`다.
- 테이블: `t (id INT PRIMARY KEY, k INT NOT NULL, s VARCHAR(50), big BIT VARYING)`. `big`은 압축되지 않는 BIT VARYING 값이다.

| 값 크기 | 행 수 | develop의 저장 | 세 설계의 저장 |
| --- | ---: | --- | --- |
| 100 B | 200,000 | inline | inline (기능 미사용) |
| 4 KB | 80,000 | inline, 페이지당 3행 | 행 밖 |
| 8 KB | 40,000 | inline, 페이지당 1행 | 행 밖 |
| 64 KB | 6,000 | overflow | 행 밖 |

- 조건: **io**는 `data_buffer_size=128M`이고, 측정할 문장마다 서버를 재시작하고 DB 파일의 OS page cache를 비운다. **warm**은 `data_buffer_size=4G`이고, 읽기는 한 번 실행해 데운 뒤 잰다. 데이터는 모든 크기에서 128 MB보다 크다.
- 측정 순서(크기·빌드마다 새 DB): 적재(S4) → 읽기(S1~S3, io 3회, warm 3회) → 변경(S5~S8s, warm 3회, io 3회) → 동시 접속(S11·S12, warm 3회) → 삭제(S9, warm 3회, io 3회). 측정은 서버가 idle(vacuum 종료)이 된 뒤 시작한다. 변경은 문장이 끝난 뒤 다시 idle이 될 때까지의 일(drain)도 더한다.
- 지표: 서버 명령어 수(`perf stat -p <cub_server>`), data page fetch(`cubrid statdump`), OS 읽기·쓰기 바이트(`/proc/<pid>/io`), 경과 시간.

## 4. 한눈에 보기

### 값이 행 밖으로 나가는 크기(4 KB, 8 KB, 64 KB)

서버 명령어 수(drain 포함)의 develop 대비 비율 범위다. 범위는 세 크기와 io·warm 두 조건, 즉 최대 6개 중앙값의 최소~최대다.

| 시나리오 | develop e64a (대조) | OOS | Sidecar | Inner Table |
|---|---|---|---|---|
| S4 적재 INSERT | ×1.03~1.08 | ×1.02~1.06 | ×1.14~1.26 | ×1.48~2.61 |
| S1 작은 컬럼 scan | ×0.96~1.00 | ×0.03~0.85 | ×0.02~0.37 | ×0.02~0.24 |
| S2 큰 값 비교 scan | ×0.98~1.01 | ×1.05~3.03 | ×0.98~1.71 | ×2.03~21.95 |
| S3n PK 조회 5천 회, 작은 컬럼 | ×0.99~1.01 | ×0.74~0.99 | ×0.75~1.01 | ×1.05~1.74 |
| S3w PK 조회 5천 회, 큰 컬럼 | ×0.97~1.01 | ×1.00~1.12 | ×0.99~1.04 | ×1.03~1.63 |
| S5 작은 컬럼 UPDATE 전체 | ×0.98~1.07 | ×3.90~11.29 | ×0.08~0.65 | ×0.50~1.04 |
| S6 큰 컬럼 UPDATE 1/8 | ×0.99~1.06 | ×2.33~597.02 | ×1.47~2.17 | ×3.01~8.21 |
| S7 UPDATE+INSERT+COMMIT 600회 | ×0.99~1.03 | ×1.00~1.41 | ×0.94~1.27 | ×1.16~1.59 |
| S8b 큰 컬럼 UPDATE+COMMIT 600회 | ×0.99~1.10 | ×1.07~1.46 | ×0.95~1.11 | ×1.19~1.61 |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | ×0.97~1.05 | ×1.09~2.04 | ×0.70~1.04 | ×0.94~1.28 |
| S9 DELETE 1/8 | ×0.99~1.25 | ×0.33~1.23 | ×0.35~1.30 | ×1.32~6.08 |
| S11 8 client 큰 컬럼 UPDATE | ×1.00~1.01 | ×1.08~1.24 | ×1.03~1.05 | ×1.22~1.54 |
| S12 8 client 큰 값 INSERT | ×1.00~1.01 | ×1.13~2.43 | ×1.01~1.05 | ×1.08~1.24 |

### 기능 미사용(100 B)

| 시나리오 | develop e64a (대조) | OOS | Sidecar | Inner Table |
|---|---|---|---|---|
| S4 적재 INSERT | ×1.16 | ×0.99 | ×1.06 | ×0.99 |
| S1 작은 컬럼 scan | ×0.99~1.02 | ×1.00~1.03 | ×0.99~1.02 | ×0.99~1.06 |
| S2 큰 값 비교 scan | ×0.99 | ×0.99 | ×1.00 | ×1.11~1.12 |
| S3n PK 조회 5천 회, 작은 컬럼 | ×1.00 | ×0.98~0.98 | ×0.98~1.00 | ×0.98~1.00 |
| S3w PK 조회 5천 회, 큰 컬럼 | ×1.00~1.01 | ×0.97~0.99 | ×1.00~1.01 | ×1.00 |
| S5 작은 컬럼 UPDATE 전체 | ×0.99~1.01 | ×0.99~1.04 | ×1.01~1.02 | ×0.99~1.00 |
| S6 큰 컬럼 UPDATE 1/8 | ×1.01 | ×1.01 | ×1.02 | ×1.03~1.04 |
| S7 UPDATE+INSERT+COMMIT 600회 | ×1.01~1.03 | ×1.00~1.03 | ×1.02~1.02 | ×1.00~1.05 |
| S8b 큰 컬럼 UPDATE+COMMIT 600회 | ×0.95~1.05 | ×0.94~1.03 | ×0.92~1.10 | ×0.97~1.02 |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | ×1.00~1.03 | ×1.00 | ×1.01~1.03 | ×1.00~1.08 |
| S9 DELETE 1/8 | ×0.95~0.99 | ×0.92~1.12 | ×1.11~1.12 | ×1.02~1.11 |
| S11 8 client 큰 컬럼 UPDATE | ×1.01 | ×0.97 | ×0.98 | ×0.96 |
| S12 8 client 큰 값 INSERT | ×1.01 | ×0.96 | ×0.97 | ×0.96 |

## 5. 시나리오별 결과

표의 값은 develop `a7f220d5d7` 대비 서버 명령어 수 비율(3회 중앙값)이다. 읽기의 io 조건과 모든 변경에는 OS 읽기 또는 쓰기 바이트 비율을 함께 적었다. ×1.5 이상이나 ×0.67 이하는 굵게 표시했다. 마지막 열은 develop의 절대값이다. 비율이 커 보여도 develop의 절대값이 작으면 실제 차이는 작을 수 있다.

### S1 작은 컬럼 scan

**무엇을 보나.** 큰 값을 건드리지 않는 집계다. 행 밖 저장이 노리는 가장 대표적인 이득이다.

**결과.** 세 설계 모두 크게 이긴다. io 조건에서 OS 읽기가 develop의 0~6%다. warm 조건에서도 heap 페이지 수가 줄어 명령어가 develop의 0.11~0.85배다. 4 KB warm의 OOS(×0.85)만 이득이 작다. Inner Table과 Sidecar가 OOS보다 조금 더 싸다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 읽기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | **×0.19** / OS 읽기 ×0.06 | **×0.11** / OS 읽기 ×0.06 | **×0.09** / OS 읽기 ×0.06 | 770.2M / 425MiB / 0.87s |
| 4 KB | warm | ×0.85 | **×0.37** | **×0.24** | 135.0M / 0MiB / 0.06s |
| 8 KB | io | **×0.08** / OS 읽기 ×0.02 | **×0.04** / OS 읽기 ×0.02 | **×0.03** / OS 읽기 ×0.02 | 1.09G / 633MiB / 1.22s |
| 8 KB | warm | **×0.37** | **×0.16** | **×0.11** | 179.8M / 0MiB / 0.06s |
| 64 KB | io | **×0.03** / OS 읽기 ×0.00 | **×0.02** / OS 읽기 ×0.00 | **×0.02** / OS 읽기 ×0.00 | 699.3M / 474MiB / 1.02s |
| 64 KB | warm | **×0.23** | **×0.14** | **×0.12** | 73.3M / 0MiB / 0.11s |

### S2 큰 값 비교 scan

**무엇을 보나.** 모든 행의 큰 값을 읽어 비교한다. 행 밖 저장에 불리한 대표 경우다.

**결과.** io 조건의 OS 읽기는 세 설계 모두 develop과 비슷하다(64 KB Inner Table만 ×1.60). 차이는 CPU다. warm 조건에서 Sidecar ×1.32~1.71, OOS ×1.36~3.03, Inner Table ×8.5~22다. Inner Table은 값마다 chunk 행을 B-tree로 하나씩 찾아 모으기 때문이다(6.3절).

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 읽기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | **×1.51** / OS 읽기 ×1.01 | ×1.17 / OS 읽기 ×1.01 | **×2.95** / OS 읽기 ×1.01 | 828.6M / 425MiB / 0.87s |
| 4 KB | warm | **×3.03** | **×1.71** | **×9.55** | 192.2M / 0MiB / 0.06s |
| 8 KB | io | ×1.10 / OS 읽기 ×1.00 | ×0.98 / OS 읽기 ×1.00 | **×2.03** / OS 읽기 ×1.00 | 1.07G / 633MiB / 1.22s |
| 8 KB | warm | **×1.97** | ×1.32 | **×8.52** | 158.6M / 0MiB / 0.06s |
| 64 KB | io | ×1.05 / OS 읽기 ×1.01 | ×1.05 / OS 읽기 ×1.01 | **×3.60** / OS 읽기 ×1.60 | 703.3M / 474MiB / 1.02s |
| 64 KB | warm | ×1.36 | ×1.48 | **×21.95** | 68.7M / 0MiB / 0.11s |

### S3n PK 조회 5천 회, 작은 컬럼

**무엇을 보나.** PK로 한 행을 찾아 작은 컬럼만 읽는 일을 5,000번 한다.

**결과.** OOS와 Sidecar는 develop과 같거나 싸다. 64 KB io 조건에서는 develop이 overflow 페이지까지 읽어(476 MiB) OOS·Sidecar(0~5 MiB)보다 0.74배 비싸다. Inner Table은 64 KB에서 ×1.62~1.74로 비싸고, OS 읽기도 develop보다 많다. index 경로가 큰 컬럼이 필요 없어도 참조를 펼치기 때문이다(6.3절).

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 읽기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | ×0.95 / OS 읽기 ×0.61 | ×0.93 / OS 읽기 ×0.57 | ×1.06 / OS 읽기 ×1.48 | 2.68G / 84MiB / 4.52s |
| 4 KB | warm | ×0.99 | ×1.01 | ×1.05 | 2.45G / 0MiB / 2.12s |
| 8 KB | io | ×0.92 / OS 읽기 ×0.32 | ×0.91 / OS 읽기 ×0.34 | ×1.08 / OS 읽기 ×1.30 | 2.77G / 82MiB / 4.42s |
| 8 KB | warm | ×0.99 | ×1.01 | ×1.06 | 2.48G / 0MiB / 2.22s |
| 64 KB | io | ×0.74 / OS 읽기 ×0.00 | ×0.75 / OS 읽기 ×0.01 | **×1.62** / OS 읽기 ×1.59 | 3.26G / 476MiB / 3.67s |
| 64 KB | warm | ×0.98 | ×0.95 | **×1.74** | 2.57G / 0MiB / 2.27s |

### S3w PK 조회 5천 회, 큰 컬럼

**무엇을 보나.** PK로 한 행을 찾아 큰 값을 읽는 일을 5,000번 한다.

**결과.** OOS와 Sidecar는 develop과 거의 같다(×0.99~1.12). io 조건의 OS 읽기는 4~8 KB에서 1.3~1.5배로, 큰 값을 읽으려면 페이지를 하나 더 읽어야 한다. Inner Table은 64 KB에서 ×1.6이다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 읽기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | ×1.00 / OS 읽기 ×1.44 | ×1.00 / OS 읽기 ×1.46 | ×1.03 / OS 읽기 ×1.55 | 2.81G / 89MiB / 7.23s |
| 4 KB | warm | ×1.04 | ×1.04 | ×1.06 | 2.46G / 0MiB / 2.27s |
| 8 KB | io | ×1.00 / OS 읽기 ×1.28 | ×0.99 / OS 읽기 ×1.34 | ×1.06 / OS 읽기 ×1.29 | 2.81G / 79MiB / 3.77s |
| 8 KB | warm | ×1.01 | ×1.01 | ×1.05 | 2.50G / 0MiB / 2.32s |
| 64 KB | io | ×1.09 / OS 읽기 ×0.86 | ×1.01 / OS 읽기 ×1.00 | **×1.59** / OS 읽기 ×1.59 | 3.29G / 475MiB / 3.57s |
| 64 KB | warm | ×1.12 | ×1.00 | **×1.63** | 2.59G / 0MiB / 2.47s |

### S4 적재 INSERT

**무엇을 보나.** 빈 테이블에 N행을 `INSERT ... SELECT`로 적재한다.

**결과.** OOS는 develop과 거의 같다(×1.02~1.06). Sidecar는 ×1.14~1.26이다. Inner Table은 값마다 chunk 행과 그 PK index를 만드느라 ×1.48~2.61이고, 64 KB에서 OS 쓰기가 1.9배다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 쓰기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | warm | ×1.02 / OS 쓰기 ×1.01 | ×1.26 / OS 쓰기 ×1.03 | ×1.48 / OS 쓰기 ×1.10 | 7.95G / 724MiB / 6.53s |
| 8 KB | warm | ×1.06 / OS 쓰기 ×1.10 | ×1.14 / OS 쓰기 ×1.01 | **×1.51** / OS 쓰기 ×1.06 | 7.62G / 1,233MiB / 16.54s |
| 64 KB | warm | ×1.06 / OS 쓰기 ×1.01 | ×1.16 / OS 쓰기 ×1.17 | **×2.61** / OS 쓰기 ×1.90 | 3.74G / 799MiB / 8.18s |

### S5 작은 컬럼 UPDATE 전체

**무엇을 보나.** 모든 행의 작은 컬럼(`k`)만 바꾼다. 큰 값을 그대로 두는 UPDATE가 큰 값의 비용을 내는지 본다.

**결과.** 세 설계 사이의 차이가 가장 크다. Sidecar는 ×0.08~0.65로, hot 행만 다시 쓰고 store 레코드는 건드리지 않는다. io 조건의 OS 쓰기가 develop의 0~2%다. Inner Table도 참조를 그대로 복사해 ×0.50~1.04다. OOS는 ×3.9~11.3이다. 바꾸지 않은 큰 값을 다시 읽고 새 OOS 레코드로 적재하기 때문이다(6.1절). 4 KB와 8 KB warm 조건에서 OOS의 OS 쓰기가 3.6~6배인 것도 같은 원인이다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 쓰기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | **×3.90** / OS 쓰기 ×1.13 | **×0.44** / OS 쓰기 ×0.02 | ×0.73 / OS 쓰기 ×0.03 | 10.05G / 1,487MiB / 7.03s |
| 4 KB | warm | **×4.13** / OS 쓰기 ×3.61 | **×0.65** / OS 쓰기 ×0.92 | ×1.04 / OS 쓰기 ×0.98 | 6.54G / 39MiB / 1.32s |
| 8 KB | io | **×7.32** / OS 쓰기 ×1.08 | **×0.23** / OS 쓰기 ×0.01 | **×0.50** / OS 쓰기 ×0.01 | 10.05G / 2,408MiB / 9.99s |
| 8 KB | warm | **×10.30** / OS 쓰기 ×6.02 | **×0.50** / OS 쓰기 ×0.85 | ×0.84 / OS 쓰기 ×0.90 | 4.62G / 22MiB / 1.22s |
| 64 KB | io | **×11.29** / OS 쓰기 ×2.88 | **×0.08** / OS 쓰기 ×0.00 | ×0.67 / OS 쓰기 ×0.00 | 6.21G / 1,352MiB / 7.68s |
| 64 KB | warm | **×10.91** / OS 쓰기 ×14.52 | **×0.17** / OS 쓰기 ×0.15 | **×0.67** / OS 쓰기 ×0.14 | 2.53G / 24MiB / 0.82s |

### S6 큰 컬럼 UPDATE 1/8

**무엇을 보나.** 행 1/8의 큰 값을 같은 크기의 새 값으로 바꾼다. develop은 행을 그 자리에서 다시 쓰므로 싸다(0.35~1.07 G 명령어).

**결과.** 세 설계 모두 develop보다 비싸다. 새 값을 다른 곳에 쓰고 옛 값을 은퇴시키기 때문이다. Sidecar가 ×1.47~2.17로 가장 작고, Inner Table이 ×3.0~8.2, OOS가 ×2.3~11이다. OOS의 64 KB warm 조건은 ×597(69~231 G 명령어, 23~71초)이다. 새 OOS 페이지를 할당할 때마다 빈 페이지 회수 sweep이 파일 전체를 훑었다(6.2절). Inner Table은 64 KB io 조건에서 OS 쓰기가 develop의 294배다. develop의 절대값(3 MiB)이 작아 비율이 커 보이는 면도 있다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 쓰기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | **×2.33** / OS 쓰기 ×4.15 | **×1.73** / OS 쓰기 ×31.42 | **×3.06** / OS 쓰기 ×35.79 | 1.03G / 5MiB / 0.36s |
| 4 KB | warm | **×2.64** / OS 쓰기 ×3.52 | **×1.61** / OS 쓰기 ×1.53 | **×3.01** / OS 쓰기 ×2.94 | 913.2M / 8MiB / 0.26s |
| 8 KB | io | **×3.97** / OS 쓰기 ×0.92 | **×1.95** / OS 쓰기 ×2.74 | **×3.42** / OS 쓰기 ×3.86 | 1.07G / 123MiB / 0.47s |
| 8 KB | warm | **×11.23** / OS 쓰기 ×4.64 | **×2.17** / OS 쓰기 ×1.02 | **×3.71** / OS 쓰기 ×21.28 | 667.1M / 7MiB / 0.21s |
| 64 KB | io | **×5.67** / OS 쓰기 ×5.62 | ×1.47 / OS 쓰기 ×20.92 | **×8.21** / OS 쓰기 ×294.48 | 498.5M / 3MiB / 0.32s |
| 64 KB | warm | **×597.02** / OS 쓰기 ×4.50 | **×1.60** / OS 쓰기 ×1.43 | **×6.25** / OS 쓰기 ×81.90 | 347.6M / 3MiB / 0.16s |

### S7 UPDATE+INSERT+COMMIT 600회

**무엇을 보나.** 큰 값 UPDATE 한 건, INSERT 한 건, COMMIT을 600번 반복한다. 짧은 OLTP 트랜잭션의 모양이다.

**결과.** 세 설계 모두 develop보다 조금 비싸다. Sidecar ×0.94~1.27, OOS ×1.00~1.41, Inner Table ×1.16~1.59 순이다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 쓰기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | ×1.20 / OS 쓰기 ×1.09 | ×1.27 / OS 쓰기 ×3.21 | ×1.25 / OS 쓰기 ×1.16 | 1.13G / 11MiB / 1.17s |
| 4 KB | warm | ×1.04 / OS 쓰기 ×1.37 | ×1.07 / OS 쓰기 ×1.08 | ×1.16 / OS 쓰기 ×1.42 | 1.06G / 11MiB / 0.87s |
| 8 KB | io | ×1.41 / OS 쓰기 ×1.16 | ×1.15 / OS 쓰기 ×1.02 | ×1.42 / OS 쓰기 ×3.03 | 1.51G / 11MiB / 1.47s |
| 8 KB | warm | ×1.00 / OS 쓰기 ×1.16 | ×1.03 / OS 쓰기 ×1.03 | ×1.18 / OS 쓰기 ×1.55 | 1.40G / 12MiB / 0.97s |
| 64 KB | io | ×1.25 / OS 쓰기 ×0.19 | ×0.94 / OS 쓰기 ×0.07 | **×1.59** / OS 쓰기 ×1.76 | 6.39G / 270MiB / 2.97s |
| 64 KB | warm | ×1.15 / OS 쓰기 ×1.35 | ×1.00 / OS 쓰기 ×1.52 | ×1.30 / OS 쓰기 ×4.73 | 5.89G / 15MiB / 2.32s |

### S8b 큰 컬럼 UPDATE+COMMIT 600회

**무엇을 보나.** 100개 hot 행 중 하나의 큰 값을 바꾸고 COMMIT하는 일을 600번 반복한다. 같은 행에 버전이 쌓이고 vacuum이 계속 회수해야 한다.

**결과.** Sidecar는 develop과 같다(×0.95~1.11). OOS는 ×1.07~1.46, Inner Table은 ×1.19~1.61이다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 쓰기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | ×1.21 / OS 쓰기 ×1.05 | ×0.96 / OS 쓰기 ×1.00 | ×1.21 / OS 쓰기 ×1.11 | 697.1M / 10MiB / 0.57s |
| 4 KB | warm | ×1.07 / OS 쓰기 ×1.04 | ×1.03 / OS 쓰기 ×1.01 | ×1.19 / OS 쓰기 ×1.09 | 644.1M / 10MiB / 0.47s |
| 8 KB | io | ×1.46 / OS 쓰기 ×1.10 | ×1.11 / OS 쓰기 ×1.01 | ×1.34 / OS 쓰기 ×1.32 | 858.4M / 10MiB / 0.82s |
| 8 KB | warm | ×1.25 / OS 쓰기 ×1.07 | ×0.99 / OS 쓰기 ×1.01 | ×1.26 / OS 쓰기 ×1.26 | 793.8M / 10MiB / 0.52s |
| 64 KB | io | ×1.38 / OS 쓰기 ×3.05 | ×0.97 / OS 쓰기 ×0.91 | **×1.61** / OS 쓰기 ×3.22 | 3.04G / 12MiB / 1.52s |
| 64 KB | warm | ×1.14 / OS 쓰기 ×1.13 | ×0.95 / OS 쓰기 ×0.91 | ×1.43 / OS 쓰기 ×3.15 | 3.04G / 12MiB / 2.32s |

### S8s 작은 컬럼 UPDATE+COMMIT 600회

**무엇을 보나.** 100개 hot 행 중 하나의 작은 컬럼을 바꾸고 COMMIT하는 일을 600번 반복한다.

**결과.** S5와 같은 방향이다. Sidecar는 develop보다 싸고(×0.70~1.04), OOS는 바꾸지 않은 큰 값을 다시 적재해 ×1.09~2.04다. Inner Table은 ×0.94~1.28이다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 쓰기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | ×1.32 / OS 쓰기 ×1.05 | ×1.00 / OS 쓰기 ×1.00 | ×1.09 / OS 쓰기 ×1.01 | 511.6M / 10MiB / 0.47s |
| 4 KB | warm | ×1.09 / OS 쓰기 ×1.06 | ×1.04 / OS 쓰기 ×1.00 | ×1.11 / OS 쓰기 ×1.02 | 498.0M / 10MiB / 0.47s |
| 8 KB | io | **×1.57** / OS 쓰기 ×1.08 | ×0.91 / OS 쓰기 ×1.00 | ×0.94 / OS 쓰기 ×1.00 | 577.9M / 10MiB / 0.92s |
| 8 KB | warm | ×1.32 / OS 쓰기 ×1.06 | ×0.93 / OS 쓰기 ×0.99 | ×1.21 / OS 쓰기 ×1.01 | 511.7M / 10MiB / 0.41s |
| 64 KB | io | **×2.04** / OS 쓰기 ×1.15 | ×0.70 / OS 쓰기 ×0.85 | ×1.28 / OS 쓰기 ×0.86 | 711.7M / 12MiB / 1.02s |
| 64 KB | warm | ×1.23 / OS 쓰기 ×1.04 | ×0.74 / OS 쓰기 ×0.84 | ×1.13 / OS 쓰기 ×0.87 | 657.8M / 12MiB / 0.57s |

### S9 DELETE 1/8

**무엇을 보나.** 행 1/8을 한 트랜잭션으로 지우고, vacuum이 끝날 때까지의 일까지 잰다.

**결과.** OOS와 Sidecar는 heap 레코드가 작아 develop보다 싼 경우가 많다(io 8 KB에서 ×0.33~0.35). Inner Table은 값마다 chunk 행과 그 index를 모두 지워야 해서 ×1.32~6.08이고, 64 KB에서 OS 쓰기가 13~15배다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 쓰기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | io | **×0.65** / OS 쓰기 ×0.22 | ×0.70 / OS 쓰기 ×0.37 | ×1.32 / OS 쓰기 ×0.78 | 2.92G / 588MiB / 1.87s |
| 4 KB | warm | ×1.23 / OS 쓰기 ×1.96 | ×1.30 / OS 쓰기 ×1.28 | **×2.13** / OS 쓰기 ×2.22 | 956.6M / 7MiB / 0.26s |
| 8 KB | io | **×0.33** / OS 쓰기 ×0.01 | **×0.35** / OS 쓰기 ×0.01 | **×1.64** / OS 쓰기 ×1.38 | 2.71G / 377MiB / 3.52s |
| 8 KB | warm | ×0.73 / OS 쓰기 ×0.33 | ×0.95 / OS 쓰기 ×0.21 | **×2.07** / OS 쓰기 ×1.00 | 824.3M / 23MiB / 0.31s |
| 64 KB | io | ×0.70 / OS 쓰기 ×2.83 | **×0.67** / OS 쓰기 ×1.03 | **×3.51** / OS 쓰기 ×15.10 | 2.03G / 86MiB / 3.62s |
| 64 KB | warm | ×0.67 / OS 쓰기 ×0.94 | ×0.89 / OS 쓰기 ×2.42 | **×6.08** / OS 쓰기 ×12.91 | 445.3M / 4MiB / 0.32s |

### S11 8 client 큰 컬럼 UPDATE

**무엇을 보나.** 8 client가 동시에 큰 값을 UPDATE하고 COMMIT하는 일을 250번씩 한다.

**결과.** Sidecar는 develop과 같다(×1.03~1.05). OOS는 ×1.08~1.24, Inner Table은 ×1.22~1.54다. 처리량(경과 시간)은 반복 사이 흔들림이 커서 판단에 쓰지 않는다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 쓰기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | warm | ×1.08 / OS 쓰기 ×1.16 | ×1.05 / OS 쓰기 ×1.27 | ×1.22 / OS 쓰기 ×1.19 | 1.97G / 17MiB / 0.37s |
| 8 KB | warm | ×1.19 / OS 쓰기 ×1.24 | ×1.04 / OS 쓰기 ×2.28 | ×1.27 / OS 쓰기 ×2.76 | 2.68G / 11MiB / 2.07s |
| 64 KB | warm | ×1.24 / OS 쓰기 ×1.17 | ×1.03 / OS 쓰기 ×1.48 | **×1.54** / OS 쓰기 ×4.00 | 9.90G / 29MiB / 1.64s |

### S12 8 client 큰 값 INSERT

**무엇을 보나.** 8 client가 동시에 큰 값을 가진 행을 INSERT하고 COMMIT하는 일을 250번씩 한다. OOS 파일 헤더 경합(CBRD-27827)을 염두에 둔 시나리오다.

**결과.** Sidecar(×1.01~1.05)와 Inner Table(×1.08~1.24)은 develop에 가깝다. OOS는 8 KB ×1.56, 64 KB ×2.43으로 크기가 클수록 비싸다. 명령어 수가 늘어난 위치는 프로파일하지 않았다.

| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / OS 쓰기 / 시간) |
|---|---|---|---|---|---|
| 4 KB | warm | ×1.13 / OS 쓰기 ×1.04 | ×1.05 / OS 쓰기 ×0.93 | ×1.08 / OS 쓰기 ×1.09 | 2.03G / 23MiB / 0.27s |
| 8 KB | warm | **×1.56** / OS 쓰기 ×1.16 | ×1.03 / OS 쓰기 ×1.12 | ×1.10 / OS 쓰기 ×1.32 | 2.70G / 21MiB / 0.82s |
| 64 KB | warm | **×2.43** / OS 쓰기 ×0.18 | ×1.01 / OS 쓰기 ×1.01 | ×1.24 / OS 쓰기 ×1.99 | 10.22G / 286MiB / 2.97s |

## 6. 원인을 확인한 것

### 6.1 OOS: 작은 컬럼 UPDATE가 큰 값을 다시 적재한다 (S5, CBRD-27230)

8 KB 값 30,000행에서 `UPDATE t SET k = k + 1` 앞뒤로 `SHOW HEAP OOS OF t`를 보았다. OOS 페이지가 30,001개에서 60,001개로 늘었고, 레코드 수는 30,000개 그대로였다. 바꾸지 않은 값이 모두 새로 적재되고 옛 값은 vacuum이 지운다. `perf record`에서 누적 비율이 큰 함수는 `oos_insert_many` 19%, `oos_find_best_page` 16%, `oos_alloc_page_with_reclaim` 15%, `oos_read` 9%였다. CBRD-27230(Open)에 적힌 동작과 같다. 3차 실행에서 S5는 반복할 때마다 OOS 파일이 커져, warm 조건의 반복 간 흔들림이 1.1~1.7로 다른 칸보다 컸다. 도구: [tools/oos_s5_probe.py](tools/oos_s5_probe.py)

### 6.2 OOS: 큰 값 교체가 OOS 파일 전체를 훑는다 (S6, CBRD-27872)

64 KB warm 조건의 S6(750행의 큰 값 교체)가 3회에 69~231 G 명령어, page fetch 5,200만~1억 8,000만 회, 23~71초를 썼다. 행 하나당 page fetch가 약 22만 회다. 같은 일을 io 조건에서 하면 2.8~3.3 G 명령어, 1초 안팎이었다. 같은 순서(적재 → S5 → S6)를 따로 재현하자, 750행 교체에 page fetch 1,730만 회와 8.4초가 들었다. `perf record`에서 85%가 `oos_find_best_page` → `oos_alloc_page_with_reclaim` → `oos_try_reclaim_page_internal` → `pgbuf_fix_release`였다. 새 OOS 페이지를 할당할 때마다 빈 페이지를 찾으려고 파일의 데이터 페이지를 고정해 확인하는 sweep이다. 이 sweep은 CBRD-27872(Confirmed)에 "재시작 직후 첫 INSERT가 파일 크기에 비례해 느려진다"로 등록되어 있다. 이번 측정은 S5가 파일을 두 배로 만든 뒤의 UPDATE에서 이 sweep이 문장 하나를 수십 초로 늘릴 수 있음을 보여준다. io 조건에서 sweep 비용이 작은 이유는 확인하지 않았다. 도구: [tools/oos_s6_probe.py](tools/oos_s6_probe.py)

**후속(4차 실행).** draft PR #8493(CBRD-27925)을 적용하면 이 sweep이 사라진다. 64 KB warm S6가 develop 대비 ×60.7에서 ×1.23으로 줄었다. 자세한 내용은 [run4-report.md](run4-report.md)에 있다.

### 6.3 Inner Table: index 경로는 참조를 항상 펼친다 (S3n, S2)

`inner-table` `fbb4f25057`에서 heap scan을 여는 경로([scan_manager.c:4073-4079](https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/query/scan_manager.c#L4073-L4079))는 VARCHAR·VARBIT 컬럼을 읽지 않을 때 `inner_table_skip_expand`를 켠다. index scan을 여는 경로([scan_manager.c:4172](https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/query/scan_manager.c#L4172))는 이 flag를 켜지 않는다. 그래서 PK 조회는 `k`만 골라도 [`inner_table_expand`](https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L940)가 [`read_chunks`](https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L519)로 모든 chunk를 읽는다. `read_chunks`는 chunk마다 `btree_find_unique_visible`과 `heap_get_visible_version`(COPY)을 호출한다([inner_table.cpp:550](https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L550), [:562](https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L562)). S2의 ×2~22는 이 chunk별 B-tree 탐색, heap fetch, 복사 비용으로 보이며, 함수별 비용은 프로파일하지 않은 추론이다.

### 6.4 측정 중 발견한 develop 결함: 재사용된 plan이 다른 값을 저장한다

2차 실행에서 Sidecar의 100 B 테이블 checksum이 다른 빌드와 600 bit 달랐다. 원인을 좇다가 develop `a7f220d5d7`에서 다음을 재현했다.

```sql
create table rb (id int primary key, b bit varying);
insert into rb select rownum, REPEAT(X'AB', 100) from db_class limit 4;
update rb set b = REPEAT(X'D1', 100) where id = 1;   -- 800 bit, D1D1...      (처음 실행: 맞다)
update rb set b = REPEAT(X'D1', 100) where id = 2;   -- 200 bit, 6431... ("d1") (plan 재사용: 틀리다)
update rb set b = REPEAT(X'D1', 100) where id = 3;   -- 200 bit, 6431...
```

같은 형태의 UPDATE가 처음 compile될 때는 의도한 값을 저장하고, XASL cache의 plan을 재사용하면 16진 문자열 텍스트를 1/4 길이로 저장한다. `CAST(REPEAT(...) AS BIT VARYING)`, scalar subquery, `/*+ RECOMPILE */`로는 재현되지 않는다. Sidecar의 checksum 차이도 Sidecar 결함이 아니었다. 8 client 중 몇 개가 plan을 처음 compile했는지에 따라 달라졌고, develop에서도 기대보다 4행이 덜 바뀌었다. 3차 실행은 모든 값을 `CAST(... AS BIT VARYING)`으로 만들고, 단계마다 값 길이를 검사했다. 별도 이슈 등록이 필요하다. 도구: [tools/repeat_bit_probe.py](tools/repeat_bit_probe.py), [tools/concurrent_len_probe.py](tools/concurrent_len_probe.py)

### 6.5 HA를 지원하지 않아서 생긴 차이인가

아니다. 네 DB 모두 `ha_mode=off`로 측정했다. CUBRID는 HA가 켜져 있을 때만 복제 로그를 만든다. OOS S5 프로파일에서 복제 관련 코드는 `log_does_allow_replication` 0.05%뿐이었다. 다만 이 수치는 HA를 끈 조건에서만 성립한다. Sidecar와 Inner Table이 HA를 구현하면 HA를 켠 쓰기 비용은 늘 수 있다. Sidecar는 현재 HA가 켜진 DB에서 값을 행 밖으로 옮기지 않는다. Inner Table은 CDC, flashback, TDE도 아직 없다.

## 7. 1차 실행 결과의 정정

1차 실행의 S7(UPDATE+INSERT 반복)과 S8b(큰 컬럼 UPDATE 반복)는 한 csql 세션에서 같은 UPDATE를 3,000회 실행했다. 6.4절의 결함 때문에 첫 실행만 의도한 크기의 값을 썼고, 나머지는 1/4 크기의 값을 썼다. 따라서 1차 보고서의 S7·S8b 수치는 "큰 값을 1/4 크기 값으로 바꾸는 일"의 비용이다. 3차 실행의 S7·S8b가 이를 대체한다. 1차 실행의 S6는 모드마다 서버가 새로 시작된 뒤 한 번만 실행되어 의도한 크기로 썼다. 다만 1차 실행의 S8s, S9와 io 조건의 변경은 그 앞의 S7·S8b가 남긴 작은 값 위에서 측정되었다. 1차 결론 중 S1, S2, S3, S5의 방향과 OOS 재적재 확인은 3차 실행에서도 그대로 재현되었다.

## 8. 한계

- 경과 시간은 공용 서버 부하로 흔들린다(반복 간 흔들림 중앙값 0.30). 동시 접속 시나리오의 처리량도 같은 이유로 판단에 쓰지 않았다.
- 다섯 빌드를 동시에 실행했으므로 디스크와 CPU를 서로 나눠 썼다. 명령어 수에는 영향이 작지만 경과 시간과 IO 대기에는 영향이 있다.
- 행 수는 1차 실행의 1/2~1/5다. 데이터가 128 MB buffer보다 커서 io 조건의 실제 읽기는 일어나지만, 더 큰 테이블에서 OOS 회수 sweep처럼 파일 크기에 비례하는 비용은 더 커질 수 있다.
- 결과는 HA를 끈 조건이다. HA·CDC·TDE를 켠 비교는 POC가 해당 기능을 구현한 뒤에야 가능하다.
- 저장 공간은 볼륨 파일 합계라 정밀하지 않다(전체 표의 "저장 공간" 참조).

## 9. 재현 방법

```sh
# 빌드마다 worktree를 만들고 release_gcc로 빌드·설치한 뒤(1차 보고서의 재현 방법 참조) 환경을 준비한다.
for v in develop develop-e64a oos sidecar inner; do
  OOSBENCH_WORKTREES=/path/to/parent python3 tools/oosbench2.py --root runs --tag T --variant $v &
done; wait
python3 tools/analyze2.py runs/run-T --out run3-tables.md
python3 tools/glance3.py runs/run-T     # 4절과 5절의 표
```
