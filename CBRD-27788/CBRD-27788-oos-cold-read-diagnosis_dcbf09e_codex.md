# CBRD-27788: OOS의 캐시 해제 후 큰 컬럼 조회가 느린 원인

작성일: 2026-10-28, Asia/Seoul. 독자: OOS 성능을 검토하는 엔진 개발자.
관련 이슈: [CBRD-27788](https://jira.cubrid.org/browse/CBRD-27788),
후속 성능 대응 [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785).
[2026-10-27 전체 실측](CBRD-27788-oos-select-performance_dcbf09e_codex.md)의 후속 원인 진단이다.
Work Item 536으로 수행했다.

## 질문과 결론

질문은 파일 캐시 해제 후 overflow 입력의 큰 컬럼 하나를 읽는 Q4가 왜 OOS에서
약 2.4배 느려지는가다. **이 fixture의 주요 원인은 OOS 조회가 만드는 불연속적인
16KiB 읽기 순서와 그 요청 방식이 파일 읽기 대기를 늘리는 데 있다.** CPU 계산 증가나
더 많은 요청이 주된 원인이라는 설명은 이번 관측과 맞지 않는다.

원래 SQL은 기준 2.32초, OOS 5.67초였다. 엔진 밖에서
그때의 읽기 주소·크기·순서만 그대로 재생해도 1.102초 대
4.396초로 약 3.29초의 차이가 재현됐다.
SQL 처리나 OOS 값 해석을 수행하지 않는 재생에서도 추가 지연이 남았다.

같은 OOS 페이지들을 주소순으로 읽으면 2.825초,
인접 요청까지 묶으면 1.445초였다. 정렬은 주소·크기·횟수를 보존했고,
인접 요청 병합은 필요한 페이지 집합과 총 요청 바이트를 보존했다. 따라서 읽기 순서와
요청 방식의 영향은 반사실적 대조로 확인했다. 이 수치를 엔진 수정 후 SQL 성능이라고
표현하지 않는다.

이 결과로 장치 내부 cache·queue·SSD 동작 각각의 기여율까지 분해한 것은 아니다.
OS readahead를 끈 경우에도 순서의 영향이 남으므로 이를 readahead 하나의 문제로
단정하지 않는다. 후속 엔진 최적화는 별도 설계와 검증이 필요하다.

## 정확한 비교 대상과 유지한 조건

| 역할 | CUBRID/CUBRID source SHA |
| --- | --- |
| 기준 | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| OOS | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |

기존 실험의 source·release 설치·DB를 그대로 사용했다. 엔진 source 수정이나 재빌드,
DB 재적재·재배치를 하지 않았다. GCC 11.5.0, O2, 테스트 계측 없음,
16KiB DB/log page, 512MiB DB buffer, query cache 0 조건을 유지했다.
원래 실측과 동일한 server·CSQL fingerprint를 16개 native trial 모두에서 확인했다.

대상은 `perf_overflow_22000`의 100,000행이다. 기준은 평균 22,016B의 전체 record overflow,
후보는 평균 4,040B의 heap과 OOS 값으로 나뉜다. SQL은 다음 하나로 좁혔다.

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ COUNT(*)
FROM perf_overflow_22000
WHERE cold_1 = CAST(REPEAT(X'AA', 7000) AS BIT VARYING);
```

정답은 100,000이며 전체 값 비교를 수행한다. 원래 다른 컬럼과 테이블도 DB 안에
보존했다. 물리 배치가 조사 대상이므로 새로운 작은 DB로 바꾸거나 행을 삭제하는
최소화는 하지 않았다. 단일 SQL과 그 쿼리 스레드의 실제 읽기로 실행 범위를 좁혔다.

실측 호스트는 Linux `5.14.0-570.30.1.el9_6.x86_64`, XFS, NVMe 볼륨이다.
서버 CPU 16–19, client 12, 관측 도구 13, 저수준 재생 16을 사용했다. NUMA node 0이며
전용 core를 예약한 것은 아니다. 서버는 한 번에 하나만 실행했다.
각 cold trial 전에 정지한 작업 전용 DB의 등록된 permanent volume만 `fsync`와
`POSIX_FADV_DONTNEED`로 해제 요청하고 fincore로 확인했다. 전역 cache 초기화는 하지 않았다.

## 1. 같은 증상 재현과 대기 위치

기본 설정의 최초 두 번과 마지막 재확인 한 번을 합친 엔진별 3회 중앙값이다.
마지막 재확인에서도 기준 2.33초, OOS 5.74초로 원래 증상이 유지됐다.

| 지표 | 기준 | OOS |
| --- | ---: | ---: |
| 전체 시간 | 2.32s | 5.67s |
| 전체 시간 범위 | 2.29–2.33s | 5.67–5.74s |
| 서버 CPU task-clock | 2271.41ms | 2208.35ms |
| 서버 instructions | 7,945,429,758 | 8,063,383,998 |
| 엔진 ioread | 200,087 | 133,339 |
| trace fetch 시간 | 1,561ms | 4,944ms |

한 차례씩 별도로 실행한 `/proc/PID/task/TID` 관측에서 가장 많은 CPU를 쓴 쿼리
스레드의 runqueue 대기는 기준 0.079ms, OOS 0.805ms였다. CPU 배정을 기다린 시간은
추가 약 3.3초를 설명하지 못한다. 10ms 간격의 wchan 표본에서는
`filemap_update_page`가 기준 3회, OOS 284회 관측됐고 `futex_wait_queue`는 각각 6회·5회였다.
표본 수를 정확한 대기 시간으로 환산하지 않았다.

이 symbol은 DB latch가 아닌 Linux 파일 page cache 경로다.
[upstream Linux 5.14의 구현](https://github.com/torvalds/linux/blob/v5.14/mm/filemap.c#L2365)은
page lock을 기다리거나 파일 페이지 읽기로 이어진다. 호스트는 EL9 backport 커널이므로
이 upstream source를 호스트 binary의 정확한 line mapping으로 취급하지 않는다.

## 2. 실제 읽기 주소와 크기

각 엔진에서 단일 Q4 실행 동안 `strace`로 `pread64`를 기록했다. raw argument 모드로
buffer 내용은 출력하지 않았다. file descriptor의 경로를 전후에 확인하고, 이 작업의
DB data volume만 골랐다. 요청이 가장 많은 쿼리 스레드의 결과는 다음과 같다.

| 지표 | 기준 | OOS |
| --- | ---: | ---: |
| pread 요청 | 200,089 | 133,341 |
| 요청 크기 | 모두 16,384B | 모두 16,384B |
| 동일 파일에서 바로 다음 위치인 읽기 | 199,994 | 1,348 |
| 그 비율 / 전체 요청 | 99.95% | 1.01% |
| 파일별 이전 요청보다 뒤로 되돌아간 경우 | 43 | 32,585 |
| 연속 요청 run 최댓값 | 2,438 | 3 |
| 요청 바이트 | 3,126.39MiB | 2,083.45MiB |

OOS가 더 많은 syscall이나 더 작은 요청을 보내서 느린 것은 아니다. **요청은 적지만
연속성이 크게 나빠졌다.** OOS 요청을 파일·offset 순으로 정렬해도 99,994곳에서
16KiB를 건너뛴다. 요청한 페이지의 시작점이 32KiB 간격인 패턴이다.

```text
기준의 주된 패턴: [읽음][읽음][읽음][읽음] ...
OOS의 주소 정렬 후에도 남는 패턴: [읽음][건너뜀][읽음][건너뜀] ...
원래 OOS 순서에는 heap과 값 페이지 사이의 앞뒤 이동도 포함된다.
```

[OOS read](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L2793)는
heap에서 얻은 참조로 값의 head page를 찾아간다. 반면
[기준 overflow read](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/src/storage/overflow_file.c#L751)는
record의 overflow chain을 따라간다. 실제 16KiB `pread`는
[fileio_read](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_io.c#L3945) 아래에서 수행된다.
코드만으로 물리적 연속성을 가정하지 않고 위 주소 기록으로 확인했다.

각 trace는 쿼리 스레드의 CSQL 연결 준비에 필요한 소량의 읽기도 포함한다. 따라서
SQL trace ioread와 정확히 같은 수는 아니다. 별도 background 스레드의 12개 data read는
재생에서 제외했다. strace가 실행 시간을 바꾸므로 traced 경과 시간을 원래 SQL의
성능 수치로 사용하지 않았다.

## 3. 동일한 읽기 집합의 순서·요청 크기 대조

DB 서버를 정지하고, 기록한 파일 주소를 읽기 전용 `os.pread`로 재생했다.
여기서 주소는 OS volume 파일의 offset이며 NVMe LBA를 직접 측정한 것은 아니다.
각 trial 전 동일 파일 cache 해제 절차를 적용했다. 같은 physical core에서 실행하고
3회 반복하며 실행 순서를 교대했다. SQL·heap·OOS 코드가 없는 I/O 재생 실험이다.

- 주소 정렬은 원래 `(file, offset, size)` multiset을 정확히 보존한다.
- 인접 요청 병합은 정렬된 목록에서 서로 붙은 구간만 최대 1MiB로 묶는다.
  16KiB 페이지로 다시 풀어 원래 집합과 정확히 일치하는지 검사했다. 요청 바이트도 같다.
- 한 페이지 간격까지 병합하는 별도 대조군은 필요한 페이지를 모두 포함하지만,
  건너뛰던 데이터까지 추가로 읽는다. 앞의 두 대조군과 구분한다.
- source FD map의 전후 일치, short read 부재, 원래 선택 집합의 hash도 검사했다.

| 엔진 / 재생 방식 | 요청 수 | 요청 MiB | OS read_bytes MiB | 시간 중앙값 (범위) |
| --- | ---: | ---: | ---: | ---: |
| 기준 / 원래 순서 | 200,089 | 3,126.39 | 3,145.47 | 1.102s (1.102–1.102) |
| 기준 / 주소 정렬 | 200,089 | 3,126.39 | 3,143.84 | 1.051s (1.051–1.051) |
| OOS / 원래 순서 | 133,341 | 2,083.45 | 2,793.11 | 4.396s (4.396–4.396) |
| OOS / 주소 정렬 | 133,341 | 2,083.45 | 2,765.25 | 2.825s (2.821–2.826) |
| OOS / 정렬 + 인접 요청 병합 | 100,522 | 2,083.45 | 3,579.64 | 1.445s (1.444–1.446) |
| OOS / 정렬 + 한 페이지 간격까지 병합 | 3,649 | 3,597.12 | 3,657.59 | 1.278s (1.277–1.278) |

원래 읽기 순서에서 기준과 후보 사이에 생긴 약 3.3초 차이가 SQL 밖에서도 남는다.
OOS는 순서만 바꿔도 약 35.7% 빨라지고,
인접 요청 병합까지 하면 원래 재생보다 약 67.1% 빨라졌다.
필요한 페이지 집합과 총 요청량을 유지한 대조이므로 순서·요청 방식이 지연에 영향을
준다는 인과 근거다. 원래 SQL에 이 전략을 적용·검증한 것은 아니다.

빠른 대조군의 OS read_bytes가 더 크다는 점도 중요하다. readahead로 더 읽더라도
대기가 줄면 시간이 짧아질 수 있다. 이번 조건에서는 읽기 바이트의 감소만으로 시간 개선을 예측할 수 없다.

## 4. readahead만의 문제인가

`data_file_os_advise=3`은 source에서 `POSIX_FADV_RANDOM`으로 전달된다.
[설정 적용 코드](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_io.c#L3033)를
확인하고 각 trial의 paramdump로 실제 적용을 검증했다. 이 설정 하나만 바꾼 SQL 대조는
엔진별 3회 중앙값에서 다음과 같았다.

| 설정 | 기준 SQL | OOS SQL |
| --- | ---: | ---: |
| 기본값 0 | 2.32s | 5.67s |
| RANDOM 3 | 5.69s | 8.73s |

양쪽 모두 느려졌다. **readahead를 끄는 설정을 해결책으로 제안하지 않는다.**
RANDOM 상태의 저수준 재생도 OOS의 원래 순서 7.141초,
정렬 4.158초였다. 두 경우 OS read_bytes는 요청 바이트와
같았지만 순서 효과는 남았다. 따라서 OS readahead가 유일한 원인은 아니다. 더 아래의
I/O 지역성·장치 cache·요청 처리 중 각각 무엇이 얼마만큼 기여하는지는 미분리 상태다.

## 판정과 후속 범위

관측과 대조로 확인한 것은 다음 범위다.

1. 이 fixture에서 추가 지연은 계산량보다 파일 페이지를 기다리는 경로에 집중된다.
2. 현재 OOS 조회는 대부분 비연속적인 16KiB 요청을 만든다. 큰 값이 없는 작은 컬럼
   조회에서 얻는 compact heap의 이득과, 큰 값을 다시 읽는 경로의 비용이 다르다.
3. 동일한 요청 집합의 순서와 묶음을 바꿔 지연을 줄였으므로 읽기 패턴의 인과 영향은
   확인했다.
4. 특정 저장 layout·Q4·호스트에서 얻은 결론이다. 모든 OOS workload나 모든 storage에서
   같은 비율을 보장하지 않는다.

후속 최적화는 필요한 OOS 페이지의 선행 읽기·batch read·배치 지역성 중 무엇을
개선할지 검토할 수 있다. 이번 재생은 그 후보를 판별하는 근거이며, MVCC·동시성·
복구 계약을 만족하는 엔진 구현이나 개선 후 회귀 검증은 수행하지 않았다.
실험 종료 후 원래 설정을 복원했고 마지막 원래 SQL도 여전히 느리게 재현됐다.

## 재현과 증거

[선별 수치와 fingerprint](cold-read-diagnostic-summary_dcbf09e.json)에 native 16 trial,
저수준 30 trial의 조건·중앙값·범위, 스레드 관측, 주소 패턴과 script hash를 남겼다.
기존 200개 기본 표본과 24개 보조 표본은 수정하지 않았다.
원시 SQL·stdout/stderr·perf·strace·FD map·요청 목록·대기 표본과 진단 코드는 다음에 있다.

```text
/mnt/nvme/data-5/tmp/CBRD-27788-io-diagnosis-20261028-run1
```

현 호스트의 재현 entry point는 `diagnose.py`이며 이전 DB·설치 경로를 검증해 사용한다.
기존 결과 디렉터리를 덮어쓰지 않는다. 아래 명령은 진단 script들을 새 디렉터리로 복사해
그 디렉터리를 artifact root로 사용하는 경우의 예다. 원본 DB와 설치는 보존된 환경을 사용한다.

```sh
python3 -B diagnose.py repro --name new-repro --repeats 2
python3 -B diagnose.py trial --name strace-default-base --label base --trace
python3 -B diagnose.py trial --name strace-default-head --label head --trace
python3 -B read_pattern.py
python3 -B run_controls.py
```

`repro`의 exit 1은 이 증상이 재현됐다는 RED 판정이다. 진단 marker는
OOS wall > 기준 1.5배, CPU < 1.2배, engine reads < 0.8배이며 제품의 합격 예산이 아니다.
처음과 마지막에 실제로 이 판정을 얻었다. query 정답·직렬 TABLE SCAN·client/server
identity·source SHA·perf 계수 검증도 통과했다.

`read_pattern.py`는 보존된 두 trace를 해석하고 `requests.tsv`를 만든다.
`replay.py`는 서버가 정지한 작업 DB의 해당 주소만 읽기 전용으로 재생한다.
초기 재현·wchan·strace·RANDOM·원래 설정 재확인을 각각 구분해 보존했다.
시스템 tracepoint 디렉터리는 접근 권한이 없어 사용하지 못했으며 strace와 `/proc`
관측으로 대체했다. tracer와 관측 thread를 종료하고 작업 서버·master를 정지했다.
DB·설치와 원시 근거는 보존했다.
