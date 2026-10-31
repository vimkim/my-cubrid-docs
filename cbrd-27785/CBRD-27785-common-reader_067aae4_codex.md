# PR #8299 현재 구현·CI와 과거 공통 reader 측정

작성일과 확인일은 2026-10-31, Asia/Seoul이다. 독자는 CUBRID Engine PR 리뷰어다.
관련 이슈는 [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785), 대상 PR은 [#8299](https://github.com/CUBRID/cubrid/pull/8299)다.
현재 구현과 CI를 설명하면서 과거 측정 수치를 최신 head의 결과로 옮겨 쓰지 않기 위한 보고서다.

## Purpose

현재 head `067aae4e4`는 공통 속성 reader와 offset 경계 검사를 포함하며 해당 head의 CI는 성공했다.
성능 비교는 이전 `fd8624c`의 기록으로 보존한다. 최신 head의 성능을 새로 측정한 것은 아니다.
UPDATE의 높은 유효 표본, 과거 측정의 문자셋 누락과 원댓글 전체 수치의 동일 재현 미확인도 유지한다.

- AS-IS: 기존 공개 본문은 `408d135`를 HEAD로 표시하고 전체 CI 미실행으로 설명한다.
- TO-BE: 구현·CI는 `067aae4e4`, 성능은 실제 측정 revision과 조건을 명시한다.

소스 저장소는 `CUBRID/CUBRID`, PR head 저장소는 `vimkim/cubrid`다.
현재 head의 로컬 확인 브랜치는 `CBRD-27785-unified-reader`이며 tracked 변경은 없다.

| 역할 | 고정 commit |
| --- | --- |
| PR의 코드 diff 기준인 feature | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| 현재 원격 PR head | `067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65` |
| 직전 공통 reader 성능 측정 후보 | `fd8624c83f1f3c05b32d3fffb6ee4a1c9306c8b0` |
| 이전 PR 비교본 | `408d1352941e9d28a88b4d5c899bacf34e2ec1a0` |
| 성능 증가율의 분모인 통합 전 develop | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |

코드 diff의 기준과 성능 증가율의 분모는 서로 다른 역할이다.

## Implementation

### grouped는 묶음 읽기를 유지하고 값 변환은 공통 reader로 보낸다

[공통 eager 루프](https://github.com/vimkim/cubrid/blob/067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65/src/storage/heap_file.c#L11650)는
요청 속성 순서의 `cubbase::span<const RECDES>`를 받는다. 비어 있는 span이면 scalar 읽기를 사용한다.
grouped로 준비한 payload가 있으면 해당 descriptor를 [공통 속성 reader](https://github.com/vimkim/cubrid/blob/067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65/src/storage/heap_file.c#L11560)에 빌려 준다.
reader가 representation과 decode plan을 준비하고 변환과 COPY를 처리한다.
별도의 grouped 속성 변환 루프는 제거했다.

grouped payload는 dispatcher가 소유한다. 공통 reader는 빌린 payload를 해제하지 않는다.
scalar Resolve가 만든 heap buffer는 scalar 경로에서 정리하고, grouped buffer는 공통 loop 종료 뒤 dispatcher가 정리한다.
[dispatcher](https://github.com/vimkim/cubrid/blob/067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65/src/storage/heap_file.c#L11686)는
일반 record를 grouped vector 생성 전에 반환한다.
요청 OOS 속성이 2개 이상일 때만 [기존 grouped Resolve](https://github.com/vimkim/cubrid/blob/067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65/src/storage/heap_oos.cpp#L734)를 적용한다.

현재 공통 reader에는 scalar OOS용 지역 scratch가 있다.
학습 snapshot `f1b99031c`의 별도 scratch helper 구조를 현재 PR의 구조로 설명하지 않는다.
stack 배열 선언만으로 malloc이나 전체 초기화 비용을 주장하지 않는다.
UPDATE의 크기·강제 OOS 선택 계산, writer의 header·offset 폭 재사용과 필요한 입력에서만 pending owner를 추가하는 변경은
[408d135 보고서](CBRD-27785-shared-read-update_408d135_codex.md)의 범위를 유지한다.

### 두 offset의 존재 경계와 release 컴파일 경로를 명시한다

[paired-offset helper](https://github.com/vimkim/cubrid/blob/067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65/src/storage/heap_file.c#L11003)는
시작·끝 entry가 모두 record 안에 있는지 검사한 뒤 읽는다.
[grouped 분류](https://github.com/vimkim/cubrid/blob/067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65/src/storage/heap_oos.cpp#L706)도
검사된 기존 accessor로 두 entry를 읽는다. 검사 전에 `OR_VAR_IS_NULL`로 읽던 경로를 대체한다.
이 검증은 offset entry의 존재 경계에 관한 것이며 모든 손상 record의 안전성을 증명한 것은 아니다.

`fd8624c`에서 `067aae4e4`로의 엔진 변경은 paired-offset switch에 추가한 세 줄이다.
`default`에서 `assert_release(false)` 뒤 `ER_GENERIC_ERROR`를 반환한다.
성공 반환이면 두 출력을 모두 썼다는 제어 흐름을 명시해 strict release 컴파일을 통과시킨다.
직접 호출자는 오류를 먼저 검사한다. 유효 offset 폭의 decode·COPY·소유권 계약은 바꾸지 않는다.
관측한 문제는 strict 컴파일 실패이며 runtime의 미초기화 읽기를 입증한 것은 아니다.

`ALWAYS_INLINE`의 기존 release·debug 정책을 사용한다.
벤치마크 preflight는 설치본·설정뿐 아니라 서버 PID의 정확한 DB 인자를 검증한다.
실행 절차와 fixture의 구분은 [현재 source README](https://github.com/vimkim/cubrid/blob/067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65/contrib/benchmarks/oos-performance/README.md)에 있다.

## Remarks

### 성능 표는 fd8624c의 과거 측정이다

2026-10-29의 production test-OFF 기록에서 선택한 두 JSON을 그대로 보존했다.
[일반 쿼리 표본](common-reader-20261029/ordinary-results.json)과
[grouped 표본](common-reader-20261029/oos-results.json)의 중앙값·최솟값·최댓값·spread를 이번에 다시 계산해 저장 값과 대조했다.
이는 저장된 표본의 산술 확인이다. 새 benchmark 실행이나 전체 raw 로그 재감사가 아니다.

아래 단위 M은 100만 서버 user-space instructions다.
괄호는 고정 develop 대비 증가율이다. 현재 head `067aae4e4`를 표에 추가하지 않는다.

| 쿼리 | develop `4781495` | feature `dcbf09e` | 이전 PR `408d135` | 측정 후보 `fd8624c` |
| --- | ---: | ---: | ---: | ---: |
| 일반 풀 스캔 | 250.914M | 268.521M (+7.02%) | 252.492M (+0.63%) | 253.502M (+1.03%) |
| 일반 조건 스캔 | 531.572M | 575.801M (+8.32%) | 538.778M (+1.36%) | 541.378M (+1.84%) |
| 일반 UPDATE, 새 복제본 | 6,471.755M | 6,818.375M (+5.36%) | 6,579.950M (+1.67%) | 6,586.598M (+1.77%) |

정순은 develop, feature, 이전 PR, 후보 순이며 역순도 실행했다.
쿼리별 각 라운드 5회에서 첫 회를 제외한 총 8회 중앙값이다.
UPDATE는 매번 새 복제본이며 COMMIT을 계수에 포함한다. 연속 UPDATE 표본과 합치지 않았다.
SELECT 두 쿼리의 후보 spread는 각각 0.0135%, 0.0189%다.
후보 UPDATE의 보존 표본 범위는 6,586.256M부터 6,720.545M까지이며 spread는 2.0388%다.
spread는 최대·최소 차이를 중앙값으로 나눈 값이며 신뢰구간이 아니다.
높은 UPDATE 표본은 develop 중앙값 대비 +3.84%이고 제외하지 않았다.
이전 동일 엔진 소스 `02df4d9`의 +5.0158% 관측도 [후속 보고서](CBRD-27785-shared-read-update_408d135_codex.md)에 남아 있다.

엄격한 +2% 전체 통과는 미충족이며 중앙값만으로 통과를 선언하지 않는다.
작성자의 약 +5% 수용은 이번 개선을 먼저 통합하려는 결정이며 리뷰어 승인이나 기준 달성과 다르다.
잔여 UPDATE 비용·변동은 [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816), Work 571로 분리한다.

grouped 영향은 기존 PR `408d135`와 측정 후보 `fd8624c`를 비교했다.
아래 증감의 분모는 develop이 아니라 기존 PR이다.
각 표본은 같은 쿼리 20회이고, 정·역순 각 5회 중 첫 회를 제외한 8회 중앙값이다.

| 행 구성 | 요청 OOS 속성 수 | 기존 PR | 측정 후보 | 증감 |
| --- | ---: | ---: | ---: | ---: |
| 4,500B 두 값, 5,000행 | 0 | 160.043M | 162.955M | +1.82% |
| 4,500B 두 값, 5,000행 | 1 | 706.229M | 694.483M | -1.66% |
| 4,500B 두 값, 5,000행 | 2 | 1,206.279M | 1,191.311M | -1.24% |
| 4,500B·20,000B, 1,000행 | 0 | 35.666M | 36.284M | +1.73% |
| 4,500B·20,000B, 1,000행 | 1 | 144.838M | 142.507M | -1.61% |
| 4,500B·20,000B, 1,000행 | 2 | 318.569M | 315.834M | -0.86% |

OOS 속성을 요청하지 않은 경우의 증가도 함께 기록한다.

### 과거 측정의 조건과 한계

- GCC 11.5.0, RelWithDebInfo, O2·NDEBUG, frame pointer 유지 조건이며 UNIT_TEST 관련 옵션은 모두 OFF였다.
- 네 설치본의 동일 compiler 설정에 maybe-uninitialized 경고 downgrade가 있었다. fd8624c 성능 표는 strict release CI 성공의 증거가 아니다.
- 각 일반 DB는 data volume 2 GiB, 물리 active log 1 GiB, heap 1,429페이지, 평균 record 92B였다. 매 UPDATE clone의 OID·HFID·행 수·내용을 검증했다고 과거 기록에 있다.
- 같은 NUMA node의 CPU를 사용했고 server는 16부터 19까지, CSQL은 12에 배치했다. data buffer 4 GiB, log buffer 256 MiB, query cache 0을 유지했다.
- 과거 기록상 counter running은 95% 이상이고 계수 중 server background 작업도 포함한다. 높은 UPDATE 표본의 원인을 vacuum·allocator·reclaim으로 확정하지 않았다.
- DB 생성 locale과 실제 table·column의 charset·collation은 과거 표에 기록되지 않았다. [비교 조건](CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md#charset-conditions)에 따라 미확인으로 남긴다.
- 별도의 [원문 SQL 재실행](CBRD-27785-reviewer-reproduction_4408135c_20261031_codex.md)은 문자셋 영향을 관측했지만 fd8624c나 067aae4e4의 재측정은 아니다. 리뷰어의 locale이나 원댓글 전체 수치의 동일 재현도 미확인이다.

### Test Plan

아래는 보존한 실행 기록과 이번 GitHub 상태 확인을 구분한 결과다. 이번에 테스트를 새로 실행하지 않았다.

| 소스와 검증 | 결과와 범위 |
| --- | --- |
| fd8624c의 과거 기능 확인 | focused CTest 15/15, crash recovery 선택 3/3, Python 5/5가 통과했다. setup·cleanup fixture를 포함한다. Linux guard page 시험에서 경계 초과를 재현하고 수정 뒤 통과했다. |
| 067aae4e4의 strict compiler 확인 | 보존한 release CI 명령을 GCC 8.5, O2·NDEBUG·Wall·Werror로 재실행했다. SA_MODE·SERVER_MODE 모두 수정 전 exit 1, 수정 후 exit 0이었다. warning downgrade는 포함하지 않았다. production 생성 header를 재사용한 제한적 번역 단위 확인이며 container 안의 새 full build가 아니다. |
| 067aae4e4의 재빌드 후 기능 확인 | 격리한 GCC 11.5의 RelWithDebInfo·OOS 테스트 활성 환경에서 focused CTest 15/15와 crash recovery 3/3이 통과했다. source·test copy·strict-green의 hash 일치를 확인한 기록이 있다. |
| 067aae4e4에 붙은 현재 gha-ci 상태 | [run 40827634555](https://github.com/CUBRID/cubrid/actions/runs/40827634555)의 release·debug·shell·SQL·medium이 SUCCESS다. shell 50/50, SQL 10/10, medium 1/1 shard 통과라는 과거 완료 기록과 일치했다. |

run metadata의 headSha는 `4f1a68c1ebec12f29bc8ba98b5ce8cacb1fc8735`로 PR head와 다르다.
engine head는 PR의 `067aae4e4`와 그 SHA에 붙은 gha-ci status 5개로 대응했다.
run metadata의 headSha를 engine revision으로 대신 기록하지 않는다.
이전 fd8624c run에서 실패한 shell 07·16이 다음 run에서 통과한 사실만으로 이전 원인이나 flake 판정을 확정하지 않는다.
이전 CI 조사에서 남은 SQL 집계 불일치의 재감사도 이번 범위에 포함하지 않는다.

### 2026-10-31에 확인한 공개 상태와 남은 조치

GitHub의 현재 PR head는 067aae4e4, base는 feature/oos-merge이며 OPEN draft였다.
watch-pr의 status-only 결과는 MERGEABLE/CLEAN이고 미해결 review thread는 0개, CI 실패·pending도 0개였다.
draft 상태와 리뷰어 승인 미취득을 포함해 merge-ready나 성능 수락 완료로 판정하지 않는다.

공개 TC [#3898](https://github.com/CUBRID/cubrid-testcases/pull/3898)과 비공개 TC [#4589](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4589)는 OPEN draft이며 diff가 비어 있었다.
이번 source·native test 변경에는 TC 변경이 불필요하므로 제공된 프로젝트 지침에 따라 사람이 닫는다.
현재 GitHub mergeState가 CLEAN이어도 이 사람의 TC 처리 조건이 없어졌다고 취급하지 않는다.
이번에 TC PR을 merge·close하거나 branch를 삭제하지 않았다.

이번에 준비한 [본문](CBRD-27785-common-reader-pr-body_067aae4_codex.md)과
[게시 context](CBRD-27785-common-reader-pr-context_067aae4_codex.md)는 별도의 검토·확인 뒤 게시한다.
source push, CI 재실행, engine PR 병합, JIRA 갱신은 이번 작업에 포함하지 않는다.
JIRA 실시간 조회는 DNS의 `Name or service not known` 오류로 실패했다. 로컬 이슈 초안을 참조했으며 현재 JIRA 상태는 단정하지 않는다.
