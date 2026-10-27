# CBRD-27788: 최신 PR #7990의 OOS SELECT 성능 실측

작성일: 2026-10-27, Asia/Seoul. 독자: OOS 통합의 성능 이득과 비용을 검토하는 엔진 개발자.
관련 이슈: [CBRD-27788](https://jira.cubrid.org/browse/CBRD-27788),
상위 [CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583),
회귀 대응 [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785).

## 질문과 결론

최신 OOS 구현에서 큰 컬럼을 읽지 않는 SELECT가 기존 heap·overflow 대비 얼마나
개선되는지, 큰 값을 읽을 때 어떤 비용이 생기는지 측정했다.
[PR #7990의 답글 5번](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6441306406)의
후속 실측이며, 7월 비율을 최신 결과로 재사용하지 않았다.

일반 heap 입력의 작은 컬럼 집계 Q1은 재시작 조건에서
0.74초 → 0.38초
(-48.6%), overflow 입력에서는
1.47초 → 0.41초
(-72.1%)였다. 페이지 접근·읽기 감소가 함께 확인됐다.

큰 값 하나를 실제로 비교하는 Q4의 일반 heap 대비 시간 변화는
재시작 +25.9%, warm +17.8%였다.
전체 컬럼을 읽는 Q5의 일반 heap 대비 변화는
재시작 +21.3%, warm +16.4%였다.
작은 값 조회의 이득만으로 전체 workload의 개선을 주장할 수 없다.

기본 200개 표본은 OS 캐시를 유지한 실험이다. 엔진 ioread 감소와 저장장치 읽기를
구분하기 위해 작업 전용 DB 볼륨에만 캐시 해제를 요청한 24개 보조 표본도 수집했다.
파일 캐시 해제 요청 후 일반 heap 입력 Q1의 OS read_bytes는
1,576.6 → 1,640.8MiB로
줄지 않았다. 같은 조건의 시간 변화는 -5.9%였다. 따라서 일반 heap 대비
엔진 읽기 감소를 실제 저장장치 읽기 감소로 일반화할 수 없다. overflow 입력 Q1의
OS read_bytes는 3,146.2 → 1,650.5MiB,
시간 변화는 -50.3%였다. 이 차이를 구분해 해석한다.

특히 파일 캐시 해제 요청 후 overflow 입력의 큰 컬럼 조회 Q4는
2.32초 → 5.72초
(+146.6%)로 느려졌다. OS 캐시 유지 조건의 약 17% 개선과 반대 방향이다.
읽기 바이트가 줄어도 읽는 위치·순서·대기 비용까지 같아지는 것은 아니다.
원인은 확정하지 않았으며 CBRD-27785에서 후속 분석할 후보로 남긴다.
실행 시간은 공유 호스트에서 얻은 결과이며, 정식 장비 인증이나 모든 workload의 보증은 아니다.

## 비교 revision과 빌드

소스 저장소는 `CUBRID/CUBRID`다. 실험 시작 시 GitHub API로 다음 값을 재확인했다.

| 역할 | full SHA |
| --- | --- |
| OOS 통합 전 기준, PR #7990 base | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| 측정한 PR #7990 head | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| 제외한 별도 PR #8299, 현재 출발 checkout | `bcb900d1696756a120ec0a2b7885c212f71ebc07` |

실측 엔진에는 source 수정이나 임계값 조정이 없다. 각각 독립 checkout·release 설치와
새 DB를 사용했다. GCC 11.5.0, RelWithDebInfo, `-O2 -ggdb3 -DNDEBUG -finline-functions`
조건이다. 실제 SERVER_MODE compile command에서 두 엔진 모두
`CUBRID_UNIT_TEST_ENABLED`가 없는 것을 확인했다. 초기 후보 설치에 있던 테스트 계측은
본 측정 전에 끄고 재빌드했다. 그 초기 설치를 실측 결과에 섞지 않았다.

서버·CSQL·로드된 설치 DSO의 경로와 해시는 각 표본에 보존했다. source SHA,
client/server 환경과 프로세스 세대도 검사했다. 선택한 해시는
[기계 요약](measurement-summary_dcbf09e.json)의 `profile`에 있다.

## 입력과 실제 저장 형태

7월 [CBRD-27014 첨부 보고서](https://jira.cubrid.org/secure/attachment/1021347/oos-performance-report.md)와
원본 저장소 `vimkim/cubrid-oos-presentation`의
`88f3297fbf10a2786ed4b2d1dff85bf55aaddc12`에 있는
`oos-select-performance-workload.sql`을 확인했다. 과거 엔진은 develop `e3b1bf0`,
OOS `3173d3b`였으므로 이번 엔진과 구분한다. 첨부 보고서의 과거 16B stub·목표 계산
설명을 현재 사양으로 적용하지 않았다.

양쪽 입력은 layout별 100,000행이다. 고정 컬럼 `id BIGINT`, `lookup_key INT`,
`hot_col INT`와 여러 `BIT VARYING` 컬럼으로 만든다. VARCHAR 압축에 따라 record가
작아지는 문제를 피한다. id에는 인덱스가 없고 lookup_key에만 인덱스가 있다.
key는 `MOD((id-1)*48271,100000)+1`, hot_col은 `MOD(id,1000)`이다.

| 입력 | 큰 값 byte 크기 | 기준 실제 경로 | 기준 평균 길이 | 후보 평균 heap 길이 |
| --- | --- | --- | ---: | ---: |
| heap | 1,300 × 3 + 5,300 + 5,200 | 일반 heap | 14,480B | 4,012B |
| overflow | 1,300 × 3 + 7,000 + 6,000 + 5,000 | 100,000행 모두 overflow | 22,016B | 4,040B |

`SHOW HEAP CAPACITY`, 후보의 `SHOW HEAP OOS`, `spacedb`로 실제 저장을 확인했다.

| 엔진 / 입력 | SHOW Num_pages | overflow 행 | OOS chunk record | OOS user pages |
| --- | ---: | ---: | ---: | ---: |
| 기준 / heap | 100,001 | 0 | 해당 없음 | 해당 없음 |
| 후보 / heap | 33,337 | 0 | 200,000 | 100,001 |
| 기준 / overflow | 200,085 | 100,000 | 해당 없음 | 해당 없음 |
| 후보 / overflow | 33,337 | 0 | 300,000 | 200,001 |

기준 overflow의 `Num_pages`는 overflow가 포함된 SHOW 용량이며, 이를 작은 heap
참조만의 페이지 수라고 해석하지 않는다. 후보의 compact heap은 약 521MiB로 512MiB
버퍼보다 조금 크다. 따라서 warm을 전체 데이터가 메모리에 들어간 조건이라고 부르지 않는다.
이 입력에서는 후보의 전체 heap+OOS 페이지 합계가 줄지는 않았다. 작은 컬럼 조회의
이득은 전체 저장량 절감이 아니라 읽지 않아도 되는 페이지를 건너뛰는 효과다.

## 측정 조건과 검증

- DB와 log 페이지: 16KiB. `data_buffer_size=512M`, `log_buffer_size=16M`,
  `max_clients=20`, query cache entries/pages 모두 0. 전체 설정과 paramdump를 보존했다.
- 서버 CPU 16–19, CSQL CPU 12. 모두 NUMA node 0의 서로 다른 physical core다.
  공유 호스트이므로 해당 core를 독점 예약한 실험은 아니다.
- registry·master port·설정·DB·TMP를 엔진별로 분리하고, 벤치마크 DB 서버는 한 번에
  하나만 실행했다. 관계없는 DB나 서비스는 중단하지 않았다.
- 각 cache·layout·SQL·엔진 조합을 5회 측정했다. restart-only는 표본마다 해당 서버를
  재시작하며 반복 번호에 따라 엔진 순서를 교대했다. warm은 해당 SQL을 한 번 실행한
  뒤 같은 서버에서 5회를 연속 측정하며 인접 SQL 사이의 엔진 순서를 교대했다.
- 모든 표본의 정답·행 수, 예상 TABLE SCAN 또는 non-covering index 계획, 직렬 scan,
  프로세스 identity와 perf 계수를 검사했다. 기본 표본 200개와 warmup 20개가 완료됐다.
- perf hardware event의 최소 running 비율은 100.0%였다.
  측정 중 load average 1분 값 범위는 2.56–8.93였다.

| SQL | 읽는 것 | 정답 |
| --- | --- | --- |
| Q1 | server-side SUM(id), 인덱스 없는 작은 컬럼 | 5,000,050,000 |
| Q2 | id 100,000건 client 반환 | 100,000행, 합계 5,000,050,000 |
| Q3 | 섞인 100-key 범위 1,000회, lookup index + heap | 100,000행, 합계 49,950,000 |
| Q4 | cold_1의 전체 byte 내용과 원본 비교 | 일치 행 수 100,000 |
| Q5 | 모든 scalar와 큰 값의 내용을 읽는 checksum | 10,050,150,000 |

모든 SQL에는 `NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN`을 넣었다.
Q4/Q5는 길이만 읽는 최적화를 피하도록 실제 내용을 비교했다. Q5의 모든 비교가 참인지
최종 checksum으로 확인한다. 큰 결과 전체를 client로 전송하는 SELECT * 측정은 아니다.

시간은 GNU time으로 perf+CSQL의 전체 실행을 잰 값이며 부착·연결·출력 비용을 포함한다.
query trace 시간과 서버 instructions/cycles/task-clock도 별도로 저장했다. 짧은 Q3
개별 질의의 trace 시간은 ms 미만에서 버림될 수 있으므로 그 합계를 경과 시간으로
사용하지 않았다. 아래는 다섯 표본의 중앙값이며 경과 시간 범위는 기계 요약에 있다.
변화율은 `(OOS / 기준 - 1) * 100`이다.

## 기본 결과: 일반 heap → OOS

| SQL | cache 조건 | 기준 / OOS (초) | 시간 변화 | instructions 변화 |
| --- | --- | ---: | ---: | ---: |
| Q1 | restart-only | 0.74 / 0.38 | -48.6% | -42.0% |
| Q1 | warm | 0.30 / 0.09 | -70.0% | -44.2% |
| Q2 | restart-only | 0.78 / 0.45 | -42.3% | -38.8% |
| Q2 | warm | 0.35 / 0.13 | -62.9% | -40.5% |
| Q3 | restart-only | 1.64 / 1.22 | -25.6% | -1.7% |
| Q3 | warm | 1.11 / 0.87 | -21.6% | -2.5% |
| Q4 | restart-only | 1.08 / 1.36 | +25.9% | +8.6% |
| Q4 | warm | 0.73 / 0.86 | +17.8% | +8.7% |
| Q5 | restart-only | 1.83 / 2.22 | +21.3% | +7.4% |
| Q5 | warm | 1.46 / 1.70 | +16.4% | +7.5% |

## 기본 결과: overflow → OOS

| SQL | cache 조건 | 기준 / OOS (초) | 시간 변화 | instructions 변화 |
| --- | --- | ---: | ---: | ---: |
| Q1 | restart-only | 1.47 / 0.41 | -72.1% | -69.3% |
| Q1 | warm | 0.74 / 0.08 | -89.2% | -71.1% |
| Q2 | restart-only | 1.52 / 0.49 | -67.8% | -66.3% |
| Q2 | warm | 0.77 / 0.12 | -84.4% | -67.9% |
| Q3 | restart-only | 2.30 / 1.24 | -46.1% | -34.6% |
| Q3 | warm | 1.55 / 0.88 | -43.2% | -35.2% |
| Q4 | restart-only | 1.84 / 1.53 | -16.8% | +1.4% |
| Q4 | warm | 1.33 / 1.10 | -17.3% | +1.5% |
| Q5 | restart-only | 3.03 / 3.43 | +13.2% | +6.6% |
| Q5 | warm | 2.53 / 2.90 | +14.6% | +6.6% |

## 페이지 접근과 엔진 읽기

| 입력 | SQL | cache 조건 | fetch 기준 → OOS | ioread 기준 → OOS |
| --- | --- | --- | ---: | ---: |
| heap | Q1 | restart-only | 100,008 → 33,344 | 100,003 → 33,339 |
| heap | Q1 | warm | 100,004 → 33,340 | 67,311 → 651 |
| heap | Q4 | restart-only | 100,008 → 333,344 | 100,003 → 133,339 |
| heap | Q4 | warm | 100,004 → 333,340 | 67,311 → 100,651 |
| heap | Q5 | restart-only | 100,008 → 333,344 | 100,003 → 133,339 |
| heap | Q5 | warm | 100,004 → 333,340 | 67,311 → 100,651 |
| overflow | Q1 | restart-only | 300,092 → 33,344 | 200,087 → 33,339 |
| overflow | Q1 | warm | 300,088 → 33,340 | 167,393 → 651 |
| overflow | Q4 | restart-only | 300,092 → 333,344 | 200,087 → 133,339 |
| overflow | Q4 | warm | 300,088 → 333,340 | 167,395 → 100,651 |
| overflow | Q5 | restart-only | 300,092 → 633,344 | 200,087 → 233,339 |
| overflow | Q5 | warm | 300,088 → 633,340 | 167,395 → 200,650 |

`fetch`는 고유 페이지 수가 아니라 접근 횟수다. `ioread`는 엔진 버퍼 미스에 따른
읽기이며 OS 캐시에서 충족될 수 있다. 기본 200개 표본의 서버 `read_bytes` 합계는
0B였다. 이 결과를 저장장치 cache까지 비운 cold
성능으로 해석하지 않는다. SQL profiling 문법과 fetch 정의는 CUBRID 매뉴얼
[질의 프로파일링 정의](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/ko/sql/tuning.rst#L674)에서 확인했다.

## 작업 전용 파일 캐시 해제 요청 후의 보조 측정

기본 실험 종료 후, **정지한 이 작업의 DB에 등록된 permanent volume 파일만** 대상으로
`fsync`와 `POSIX_FADV_DONTNEED`를 호출했다. registry·파일 위치·owner·regular file·
symlink와 hardlink 여부를 확인했다. 전역 drop_caches는 사용하지 않았다.
각 표본 직전에 fincore로 실제 residency를 확인한 뒤 서버를 시작했다.
해제 요청 직후 모든 볼륨의 resident bytes 합계 최댓값은 0B였다.
startup이 일부 페이지를 다시 읽으므로 이를 완전한 cold 장치 조건이라고 단정하지 않는다.
대상 파일의 OS cache는 해제 요청했지만 장치 내부 cache와 공유 호스트 부하는 통제하지 않았다.

Q1과 Q4를 layout·엔진마다 3회, 총 24회 측정했다. 엔진 순서는 반복마다 교대했다.
아래 OS read_bytes는 서버 프로세스에 귀속된 저장장치 읽기 집계이며, 물리 NAND 접근이나
장치 내부 캐시 상태를 뜻하지 않는다. engine ioread와 OS read_bytes를 함께 제시한다.

| 입력 | SQL | 기준 / OOS (초) | 시간 변화 | OS read_bytes 기준 → OOS (MiB) | 엔진 ioread 기준 → OOS |
| --- | --- | ---: | ---: | ---: | ---: |
| heap | Q1 | 1.01 / 0.95 | -5.9% | 1,576.6 → 1,640.8 | 100,003 → 33,339 |
| heap | Q4 | 1.43 / 1.91 | +33.6% | 1,576.6 → 2,095.4 | 100,003 → 133,339 |
| overflow | Q1 | 1.81 / 0.90 | -50.3% | 3,146.2 → 1,650.5 | 200,087 → 33,339 |
| overflow | Q4 | 2.32 / 5.72 | +146.6% | 3,146.2 → 2,793.9 | 200,087 → 133,339 |

두 엔진의 `data_file_os_advise`는 0이었다. 엔진의 ioread 요청과 OS가 실제로 읽은
바이트는 같은 지표가 아니다. 일반 heap 입력 Q1에서는 OOS의 엔진 읽기가 줄어도
OS 읽기 바이트는 줄지 않았다. readahead와 DB 볼륨 내 데이터 배치가 불필요한 페이지를
함께 읽게 했을 가능성은 있지만, 이번 실험으로 그 원인을 확정하지 않았다.
이 보고서는 이 차이를 없애려고 엔진 설정이나 배치를 조정하지 않았다.

## 원인 해석과 범위

작은 값 조회에서 heap 입력은 compact heap의 높은 집적도, overflow 입력은 전체
record overflow 본문을 읽지 않는 효과가 주요 차이다. 기준의
[`heap_get_bigone_content`](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/src/storage/heap_file.c#L20140)는
[`heap_ovf_get`](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/src/storage/heap_file.c#L6313)을
통해 overflow record를 가져온다. 후보의
[`heap_attrinfo_read_dbvalues`](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L11866)와
[`heap_attrvalue_read_oos_inline`](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L11135)은
요청한 속성의 값을 읽고, 실제 OOS 값은
[`oos_read`](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L2793)로
읽는다. 큰 컬럼을 요청하면 별도 Resolve·identity 검증·page fix와 복사 비용이 생긴다.
실측 fetch 증가를 특정 하위 함수의 단독 비용으로 분해한 결과는 아니다.

Q3는 인덱스에서 찾은 행마다 heap lookup이 남는다. heap 집적도가 좋아져도 logical
lookup 횟수가 같은 비율로 줄지는 않는다. 큰 컬럼 조회와 전체 컬럼 조회는
instructions와 시간·읽기 변화가 다를 수 있으므로 각 열을 함께 판단한다.

현재 제품의 OOS 임계값을 변경하지 않았다. 약 16KB 임계값 비교용 빌드, PR #8299의
일반 행 CPU 수정, UPDATE 재사용, DML·HA·장애 복구 성능은 이 실측의 범위 밖이다.
7월에 보고된 heap page당 행 수 문제를 이 결과만으로 현재 버그라고 단정하지 않았다.
현재의 물리 용량 목표는 unfill을 포함한 실제 페이지 선택 결과와 구분해야 한다.

## 재현과 근거 보존

입력 생성·다섯 SQL·개별 표본·요약 명령은 소스의
`contrib/benchmarks/oos-performance/IO_README.md`와 `io_bench.py`에 있다.
하네스 task commit은 `1a8cbefa434564275ce9b1dc10261261672f5251`,
branch는 `CBRD-27788-oos-benchmark`이며 출발점은 `bcb900d`다.
그 branch의 엔진을 측정한 것이 아니라 위 두 별도 exact revision 엔진을 측정했다.

원시 근거는 다음 위치에 보존한다.

```text
/mnt/nvme/data-5/tmp/CBRD-27788-20261027-run1
```

`builds.json`, 최종 CMake cache/preset, SQL·stdout/stderr·perf·프로세스 IO·설정·
저장 진단, `driver.py`, `storage_probe.py`, cache advice 전후 fincore와 파일 identity,
GitHub 조회 결과와 7월 출처를 보존했다. 초기 환경 선택·trace 출력 파싱 실패는
사전 실행 경로에 남겼으며 본 표본에서 제외했다. 결과를 덮어쓰지 않았다.
[선별 기계 요약](measurement-summary_dcbf09e.json)은 보고서 수치를 검증하는 데 필요한
revision·hash·조건·표본 수·중앙값·범위·보조 I/O 결과만 담으며 raw 로그는 Git에 넣지 않는다.

하네스는 native 출력으로 잘못된 checksum·계획·병렬 실행·누락 trace를 거부하는
음성 검증도 통과했다. 엔진 소스 수정 없이 빌드·fixture·benchmark 검증을 수행했으며,
회사 전체 회귀나 기능 인증을 수행했다고 주장하지 않는다. 작업 소유 서버·master는
측정 후 중단하고 DB·설치·로그를 보존한다.
