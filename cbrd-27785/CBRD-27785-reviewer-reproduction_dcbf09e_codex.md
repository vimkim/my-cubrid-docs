# CBRD-27785: 리뷰어 재현 SQL과 잠정 +2% 기준 검증

작성일: 2026-10-28, Asia/Seoul. 독자: PR #7990의 성능 판정을 검토하는 엔진 개발자.
질문: [새 리뷰 답변](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6461744209)의 재현 조건에서 공통 경로 개선으로 현재 우선 기준을 충족할 수 있는가?

## 현재 판단과 범위

일반 테이블의 두 조회는 후보 적용 후 +2% instructions 이내였지만, **일반 UPDATE는 기준을 넘었다.**
따라서 이번 후보만으로 성능 기준 1을 충족해 머지할 수 있다고 결론 내리지 않는다.
기준 3에 필요한 원본 PR·후보의 이득과 손해는 아래에 함께 제시한다.
연속 OOS UPDATE에서는 원본도 큰 비용 증가가 있었고, 후보의 별도 tail profile은 CPU 표본 94.80%가 page growth의 reclaim 경로에 모였다.
새 복제본의 첫 UPDATE 결과만으로 OOS UPDATE 비용을 판단하지 않는다.

2026-10-28 사용자 결정은 다음과 같다. 이는 리뷰어가 기준을 완화하거나 동의했다는 뜻이 아니다.

- **지금 검증:** 기준 1의 일반 테이블 풀 스캔·조건 스캔·UPDATE. 서버 user-space instructions의 증가율 약 +2%를 잠정 기준으로 삼는다.
- **지금 보고:** 기준 3의 현재 PR 이득·손해. 큰 값 전체 읽기와 UPDATE의 손해도 남긴다.
- **후속 작업:** 기준 2의 기본 4–16KB 전체 읽기 비회귀는 현재 판정에서 제외한다. OOS threshold system parameter를 도입해 기존 overflow의 실제 record 전환 경계에 맞춘 뒤 재측정한다. 이번 실험에서는 threshold·저장 정책을 바꾸지 않았다.

이 문서는 성능 조사다. PR의 전체 정합성·HA·release qualification이나 리뷰어의 머지 승인까지 인증하지 않는다.

## 소스와 후보

소스 저장소는 `CUBRID/cubrid`다. 측정 시 PR #7990 head는 `dcbf09e`였다.

| 역할 | 정확한 revision / 변경 |
| --- | --- |
| A, develop 기준 | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| B, 원본 OOS PR | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` 그대로, `src` diff 없음 |
| C, 선택한 로컬 후보 | B + [candidate.patch](reviewer-20261028/candidate.patch) |
| 작업 checkout 출발점 | `CBRD-27785-oos-performance`, `f1b99031c0402d521a785815f107be7a83b27717`; 연결된 PR 없음 |

C는 GCC용 로컬 성능 실험 patch다. 강제 inline annotation은 제품화 전에 기존 compiler별 inline 매크로와 다른 플랫폼 빌드를 확인할 필요가 있다.
C는 #8299의 일반 행 전용 reader 우회를 적용한 결과가 아니다. 일반 값과 OOS 값이 같은 scalar reader·변환을 사용한다.
기존 HAS_OOS 확인과 0/1개 scalar·2개 이상 grouped Resolve 선택은 유지했다.

후보의 추가 변경은 다음과 같다.

1. 이전 [공통 reader 후보](shared-path-20261028/common_loop.patch)를 사용한다. 두 VOT offset의 해석을 합치고 공통 변환·반복문의 호출 비용과 오류 검사 배치를 줄인다.
2. `heap_attrinfo_read_dbvalues`에서 representation 확인에 계산한 header 크기를 같은 호출의 layout 생성에 재사용한다. 짧은 record에 대한 기존 `or_rep_id`의 오류 처리를 유지한다. 별도 캐시 수명이나 공유 상태는 추가하지 않는다.
3. writer의 컬럼 크기 배열은 8개까지 스택, 초과하면 vector를 사용한다. OOS 계획 vector는 첫 컬럼이 실제로 선택될 때 생성한다. 선택이 없으면 같은 가변값 writer에 빈 계획을 전달한다.

기존 [`heap_attrinfo_determine_disk_layout`](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L13145)의 largest-first·hint 순서, FORCE_OUTLINE 처리, OOS+bigone guard를 유지했다.
OOS payload COPY·임시 버퍼 해제·identity stamp·stub 경계·page fix/unfix·pending owner 검사는 유지한다.
페이지 형식·WAL·snapshot 가시성·latch 순서도 이번 후보의 변경 대상이 아니다.

규범은 `cubrid-oos-context/OOS-CONTEXT.md`, SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`를 확인했다.
이 revision의 원래 raw quarter-page 정책은 승인된 physical target 식과 차이가 있다. 후보는 이 정책 차이를 수정하지 않는다.

## 최종 instructions 비교

각 항목은 5회 중 첫 실행을 버린 4회의 중앙값이다. 일반 테이블 판정 외의 행에는 통과·실패를 붙이지 않는다.
변화율의 분모는 같은 순서의 A다. 원본 PR과 후보를 혼동하지 않도록 둘을 함께 표시한다.

| 작업 | A develop | B 원본 PR | C 후보 | B / A | C / A |
| --- | ---: | ---: | ---: | ---: | ---: |
| 일반 풀 스캔 | 250.88M | 268.50M | 252.49M | +7.02% | +0.64% |
| 일반 조건 스캔 | 531.54M | 575.77M | 538.75M | +8.32% | +1.36% |
| 일반 UPDATE 20만 행 | 6,442.57M | 6,819.40M | 6,645.35M | +5.85% | +3.15% |
| 6KB 행의 작은 컬럼 스캔 | 43.85M | 34.75M | 32.15M | -20.76% | -26.67% |
| 6KB 전체 값 length | 294.13M | 371.23M | 364.31M | +26.21% | +23.86% |
| 6KB 전체 값 substr 조건 | 498.50M | 574.60M | 567.74M | +15.27% | +13.89% |
| 6KB 행의 작은 컬럼 UPDATE 2만 행 | 3,273.14M | 3,080.02M | 3,058.26M | -5.90% | -6.56% |
| 6KB 큰 컬럼 UPDATE 5천 행 | 1,908.84M | 1,875.32M | 1,873.92M | -1.76% | -1.83% |

원본의 일반 테이블 회귀는 재현됐다. 큰 값의 전체 조회는 후보에서도 develop보다 비싸며 기준 2의 후속 비교 자료로 남긴다.
작은 컬럼만 읽는 이득과 큰 값을 읽는 손해를 함께 본다. 큰 값 UPDATE의 instructions·CPU 시간은 서로 다른 지표다.

일반 세 항목은 A→B→C 순서에 이어 C→A 순서로 재확인했다. 각 표본은 새로운 일반 테이블에서 시작하며 UPDATE는 아래의 새 복제본 조건이다.

| 일반 테이블 작업 | 정방향 C / A | 역방향 C / A | 잠정 +2% instructions |
| --- | ---: | ---: | --- |
| 일반 풀 스캔 | +0.64% | +0.64% | 충족 |
| 일반 조건 스캔 | +1.36% | +1.35% | 충족 |
| 일반 UPDATE 20만 행 | +3.15% | +2.54% | 미충족 |

UPDATE의 잔여 비용이 있기 때문에 두 조회의 통과를 일반 테이블 전체의 통과로 확대하지 않는다.

## UPDATE 시작 상태를 분리한 보조 비교

위 표의 UPDATE는 **매 실행마다 seed를 새 테이블에 복제**한 뒤 한 번 UPDATE하고 COMMIT한다.
초기 논리 값·페이지 배치·기존 MVCC version 차이를 줄이는 통제다. 모든 `a` 값과 행 수를 실행 후 검증하고,
큰 값 변경은 전체 길이와 경계 ID 5개의 SHA2를 별도로 검증했다. 검증은 perf 계수 밖이다.

리뷰어는 질의당 5회·4라운드 반복을 제시했다. 이전 UPDATE가 남긴 상태의 영향을 확인하기 위해
별도 새 테이블에서 **같은 UPDATE를 5회 연속 COMMIT**하고 첫 회를 버리는 보조 비교도 했다.
작은 컬럼의 `a` 증가 횟수와 큰 컬럼의 누적 회전 횟수를 매번 검증했다. 새 복제본과 연속 실행의 표본을 합치지 않는다.

| 연속 UPDATE | A develop | B 원본 PR | C 후보 | B / A | C / A |
| --- | ---: | ---: | ---: | ---: | ---: |
| 일반 UPDATE 20만 행 | 6,506.06M | 6,815.73M | 6,638.86M | +4.76% | +2.04% |
| 6KB 행의 작은 컬럼 UPDATE 2만 행 | 3,266.68M | 7,692.82M | 32,590.24M | +135.49% | +897.65% |
| 6KB 큰 컬럼 UPDATE 5천 행 | 1,916.04M | 6,725.51M | 6,175.23M | +251.01% | +222.29% |

연속 실행의 OOS 결과에는 큰 변동과 tail이 있었다. 위 중앙값을 안정 상태의 보편적 비용이나 후보의 인과적 배율로 해석하지 않는다.
실행 순서는 다음과 같다. 1회차도 버리기 전 값으로 보존한다.

| OOS UPDATE instructions | 1회차, 버림 | 2회차 | 3회차 | 4회차 | 5회차 |
| --- | ---: | ---: | ---: | ---: | ---: |
| B 원본 작은 컬럼 | 2.84G | 134.35G | 6.26G | 8.26G | 7.13G |
| C 후보 작은 컬럼 | 2.82G | 134.28G | 57.10G | 7.89G | 8.08G |
| B 원본 큰 컬럼 | 1.86G | 117.66G | 3.50G | 7.11G | 6.34G |
| C 후보 큰 컬럼 | 1.96G | 119.70G | 3.48G | 5.86G | 6.49G |

후보의 작은 컬럼 UPDATE는 OOS live chunk가 약 20,000개로 돌아온 상태에서도 file page 수가 10,001→20,001→26,496→28,592로 늘었다.
보존된 DB에서 새 테이블을 사용한 결과이며, 원본과 후보의 vacuum 진행·공간 힌트가 완전히 같은 물리 상태라고 가정하지 않는다.
계수 전 idle 확인으로 실행 중 새로 발생하는 background maintenance를 제거할 수는 없다. 원본과 후보의 instructions 감소를 모든 UPDATE에 일반화하지 않는다.

큰 값 UPDATE에 대한 리뷰어의 +73.7%·+34.6%와 이 로컬 결과를 동일한 재현이라고 주장하지 않는다.
리뷰어 댓글에는 DB locale·모든 실행 사이의 유지 상태가 명시되지 않았다. 로컬은 `en_US.utf8`이며 위 두 시작 상태를 명시적으로 분리했다.
차이의 원인을 locale나 MVCC 하나로 확정하지도 않는다. 일반 테이블의 회귀 방향과 조회 개선은 별도로 확인된 결과다.

## 연속 OOS UPDATE tail의 호출 경로

별도 새 테이블에서 첫 UPDATE를 COMMIT한 뒤 두 번째 UPDATE를 production 후보로 profile했다.
`cycles:u`, 499Hz, FP, 80,286개 표본이며 기존 성능 계수와 다른 실행이다.

```text
locator_update_force
  → heap_oos_finalize_record → oos_insert_many → oos_find_best_page
  → oos_alloc_page_with_reclaim                    94.80% children
    → oos_try_reclaim_page_internal               90.36% children
      → pgbuf_fix_release / pgbuf_unfix
```

`pgbuf_fix_release` self는 63.90%, `pgbuf_unfix` self는 10.06%였다. 대부분 transaction thread에서 발생했다.
이 tail의 지배 비용은 OOS page growth 때 reclaim 후보를 반복 검사하는 경로다. allocator가 지배한 이전 32KB 비교와 구분한다.
표본 비율은 이 한 실행 안에서의 비율이며, 모든 UPDATE가 같은 절대 시간이나 배율을 갖는다는 뜻은 아니다.

[`oos_reclaim_sweep_step`](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L1823)은
pending deletes 또는 boot 상태에 따라 sector bitmap을 얻고 후보 페이지를 검사한다.
[`oos_alloc_page_with_reclaim`](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L2019)은
새 page 할당 때 이 sweep을 호출한다. 프로파일은 이 반복 검사가 해당 tail의 우선 조사 지점임을 뒷받침한다.
같은 reclaim horizon·deferred page 집합의 재방문이 증폭 원인이라는 설명은 다음 통제 실험으로 확인할 가설이다.

후속 개선은 같은 horizon·lap의 중복 검사를 줄이는 방향으로 검토하되, 새 삭제·rollback·horizon 변화와 boot 이후의 재검증 계약을 보존해야 한다.
빈 페이지 회수·LSA reclaim gate·identity 검사를 생략한 성능 수치는 이번 후보에 포함하지 않았다.

## CPU 시간과 판정의 한계

아래는 정방향 실행의 서버 task-clock 중앙값(ms)이다. 원본 PR과 후보 모두 같은 방법으로 측정했다.

| 작업 | A develop ms | B 원본 PR ms | C 후보 ms |
| --- | ---: | ---: | ---: |
| 일반 풀 스캔 | 38.02 | 40.88 | 40.39 |
| 일반 조건 스캔 | 74.15 | 83.62 | 77.88 |
| 일반 UPDATE 20만 행 | 1,402.76 | 1,457.45 | 1,446.44 |
| 6KB 행의 작은 컬럼 스캔 | 17.32 | 7.22 | 7.08 |
| 6KB 전체 값 length | 73.80 | 84.16 | 81.58 |
| 6KB 전체 값 substr 조건 | 107.98 | 107.36 | 98.34 |
| 6KB 행의 작은 컬럼 UPDATE 2만 행 | 1,194.95 | 2,193.57 | 2,763.16 |
| 6KB 큰 컬럼 UPDATE 5천 행 | 454.41 | 879.08 | 872.59 |

공유 호스트에서 CPU 시간·cycles는 실행 순서에 따른 변동이 있었다. 2%는 이번 **instructions 판정**에 적용한다.
이 결과로 2% 이내의 응답시간·throughput 비회귀까지 인증하지 않는다. 계수별 중앙값·범위·유효 표본과 실제 경과시간은
[results.json](reviewer-20261028/results.json)에 보존했다. OOS가 포함된 UPDATE에서 instructions가 줄어도 CPU 시간이 늘 수 있으므로 둘을 함께 보고한다.

## 입력·저장 형태·설정

리뷰어 DDL과 데이터 생성 SQL을 사용하되 기존 자료와 충돌하지 않도록 테이블 이름만 접두사로 바꿨다.

- 일반 `n`: `id INT PRIMARY KEY, a INT, s VARCHAR(100)`, 200,000행. `s`는 `SHA2(n||'',256)`이다.
- 큰 값 `w`: `id INT PRIMARY KEY, a INT, s VARCHAR(40), big VARCHAR(20000)`, 20,000행. SHA2 512-bit 결과 47개를 이어 붙여 값 길이는 6,016자다.
- 매 clone의 행 수·ID 범위·`a=MOD(id,100)`·문자열 길이를 검증했다. 큰 값 길이 합계는 120,320,000이다.
- 이 엔진의 SHA2 hex는 대문자다. 댓글의 소문자 `'a'` 조건을 그대로 실행했으며 두 substring COUNT의 기대 결과는 0이다. 조건 자체를 바꾸지 않았다.

`SHOW HEAP CAPACITY` / `SHOW HEAP OOS`에서 일반 행은 양쪽 모두 1,429 heap pages·평균 92B이고 OOS가 없었다.
큰 값은 develop에서 10,001 heap pages·평균 6,032B, OOS에서 97 heap pages·평균 55B와 10,001 OOS pages·20,000 chunks였다.
따라서 일반 비교는 heap→heap, 큰 값 비교는 heap→OOS다. 이 6KB 입력은 기존 overflow 비교가 아니다.
UPDATE 직전의 물리 저장 상태도 별도로 보존했다.

```ini
[common]
data_buffer_size=4G
log_buffer_size=256M
sort_buffer_size=16M
max_clients=50
db_volume_size=2G
log_volume_size=1G
log_max_archives=0
```

충돌 방지를 위해 master port는 각 workenv의 할당값 41138/41140을 유지했다. 성능 관련 위 설정은 양쪽 동일하다.
새 `rv27785` DB의 최초 data volume은 실제 2,147,483,648B, active log는 1,073,741,824B였다.
기존 `oos27785` DB의 active log가 32MB여서 conf만 1GB로 바꾼 앞선 scout는 최종 비교에서 제외했다.
새 DB는 task-local `cub-workenv` 복사본에서 native createdb의 볼륨 크기 인수 두 개만 2G/1G로 바꾸어 생성했다.
기존 등록 보존·새 DB provenance 절차는 그대로 사용했고 전역 도구는 바꾸지 않았다.

RelWithDebInfo/GCC 11.5.0, SERVER_MODE·SA_MODE, `-O2 -DNDEBUG -fno-omit-frame-pointer`를 확인했다.
성능 빌드에서는 모든 UNIT_TEST 옵션을 끄고 실제 compile command에 `CUBRID_UNIT_TEST_ENABLED`가 없는 것을 확인했다.
서버 core 16–19, CSQL core 12로 고정하고 서버를 하나씩 실행했다. 계수 전 idle을 확인했다.
최종 측정과 빌드는 직렬이다. 서버 PID·시작 시각·maps·실행 파일 및 DSO hash를 확인했다.

조회에는 PARALLEL 힌트를 넣지 않았다. TRACE에서 일반 테이블과 develop의 큰 heap은 worker 4개를 썼고,
compact OOS heap은 직렬이었다. 측정 조회의 TRACE `ioread`는 0이었다. 이는 기본 query policy를 포함한 비교다.
CPU reader 자체만의 비용 비교를 원하면 양쪽을 직렬로 맞춘 기존 보고서의 별도 결과를 사용한다.

## 진단과 검증

새 재현 SQL의 기존 공통 reader는 일반 조회 두 개가 약 +2.2%/+2.1%였고 UPDATE도 남았다.
작은 배열·지연 계획은 UPDATE의 명령 수를 줄였고, header 재사용은 두 조회를 +2% 안으로 내렸다.
writer helper 강제 inlining은 UPDATE를 더 줄이지 못해 제외했다. 최종 후보에는 이 변경이 없다.
표본 상대비율을 단순히 더해 독립 원인별 기여율로 해석하지 않는다.

`perf record -m 16 --call-graph fp`의 matched profile에서 공통 decode·행 스캔 비용과 UPDATE의 직렬화·page buffer·locking·log 작업이 확인됐다.
초기 기본 buffer 크기의 perf record 실패는 빈 data로 발견해 제외했다. instructions sampling 보조 실험은 host sample-rate 제한을 받으므로
절대 명령 수나 세부 함수별 정확한 기여율의 근거로 쓰지 않았다. 위 판정은 별도 `perf stat` 계수다.

대표 수집 명령은 다음과 같다. 실제 SQL·PID·파일 경로는 원본 artifact에 있다.

```bash
perf stat -x ';' -e instructions:u,cycles:u,task-clock,context-switches,cpu-migrations,page-faults \
  -p "$DBPID" -o counters.perf -- taskset -c 12 \
  csql -C -u dba --no-pager -t -N -i queries.sql rv27785
perf record -m 16 -e cycles:u -F 499 --call-graph fp -p "$DBPID" -o cpu.data -- \
  taskset -c 12 csql -C -u dba --no-pager -t -N -i profile.sql rv27785
```

선택한 후보 그대로 correctness용 UNIT_TEST_OOS=ON으로 재빌드해 집중 CTest **15/15**, **43.97초**를 통과했다.
범위는 native·identity·SERVER_MODE, SQL CRUD·DDL·경계·transaction·bigone·deferred write·visible version·workspace bytes·record flags·reference errors다.
workspace bytes 검사는 FORCE_OUTLINE/PREFER_INLINE, offset width, 70개 이상의 컬럼도 포함해 작은 배열의 vector fallback을 함께 검사한다.
이 검증은 성능용 test-OFF DSO의 측정과 분리했다. 전체 CI·HA 검증은 실행하지 않았다.

첫 집중 실행은 13/15였으며 `test_oos_identity_stamp`와 `test_oos_server`가 각각 원래 60초 제한에 걸렸다.
예상 오류 하나를 선택한 native 재현은 통과했지만 오류 검사 자체가 4,214ms 걸렸고, 별도 profile에서 `addr2line`의 libbfd DWARF/line-info 해석 비용이 확인됐다.
현재 PATH의 Homebrew addr2line 대신 task-local PATH prefix로 `/usr/bin/addr2line`만 선택해 같은 집중 suite를 재실행했다.
엔진 source·binaries·suite 선택·시간 제한·오류 검사·callstack 출력을 유지한 재실행의 결과가 위 통과 결과다.
최초 timeout 기록은 제거하지 않았다. 이 도구 선택을 제품 코드의 성능 개선이나 원래 환경에서의 15/15 통과로 해석하지 않는다.

기존 [공통 reader·allocator 조사](CBRD-27785-shared-read-path_f1b9903_codex.md)의 32KB free-tree 폭 결함은 별도 수정 근거다.
이번 후보에는 allocator 수정이 없으며 그 큰 값 개선을 이번 6KB UPDATE의 설명으로 쓰지 않는다.
[CBRD-27788의 기존 측정](../CBRD-27788/CBRD-27788-oos-select-performance_dcbf09e_codex.md)은 14.48KB heap→OOS 및 22KB overflow→OOS,
100,000행·512MB buffer 조건의 원본 PR 손익을 다룬다. 이 문서의 6KB·4GB buffer 결과와 합치지 않는다.

현재 원본 UPDATE는 UPDATE에서 값을 지정하지 않은 OOS 컬럼도 읽고 새 chain으로 쓰는 경로를 가진다. 승인된 CBRD-27230의 해당 chain 재사용은 별도 구현 범위다.
이번 일반 UPDATE 개선은 그 소유권·vacuum·복제 설계를 구현하거나 인증한 결과가 아니다.

## 보존과 다음 작업

원본 artifact root는 다음과 같다. DB·로그·정확한 DSO·compile commands·source patch·perf.data와 단계별 결과를 보존했다.

```text
/mnt/nvme/data-5/tmp/CBRD-27785-reviewer-20261028
```

저장소에는 검토에 필요한 최종 [patch](reviewer-20261028/candidate.patch)와 [선별 계수·provenance](reviewer-20261028/results.json)만 추가한다.
raw 로그·다운로드·임시 orchestration은 위 root에 남긴다.

조사 후 source는 시작 HEAD `f1b9903`, baseline은 `4781495`로 복구하고 다시 빌드·설치했다.
설정과 원래 preset symlink를 복구했으며 공유 preset hash는 같았다. task-owned DB daemon은 종료했고 두 DB와 모든 fixture는 보존했다.
현재 설치가 실험 후보라고 가정하지 않는다. 제품 branch 통합·원격 push·PR/JIRA 게시·CI trigger는 수행하지 않았다.

다음 성능 작업은 일반 UPDATE의 잔여 증가분을 +2% 이내로 낮추고 같은 순서 교환 비교로 확인하는 것이다.
기준 2는 위 사용자 결정대로 threshold parameter와 기존 overflow 경계의 비교 실험으로 이어간다.
