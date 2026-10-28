# CBRD-27785: 공통 reader와 일반 UPDATE 비용 개선

작성일: 2026-10-28, Asia/Seoul. 독자: [PR #8299](https://github.com/CUBRID/cubrid/pull/8299)를 검토하는 엔진 개발자.
질문: 지금까지 확보한 일반 읽기·UPDATE 개선을 하나의 PR로 제안할 때 무엇을 검증했고 무엇이 남았는가?

공통 heap/OOS reader를 유지하면서 반복 layout 해석과 불필요한 준비를 줄였다. 통제한 측정의 일반 UPDATE는 약 +1.67%였으나 뒤의 유효한 batch는 +5.0158%였다. **전체 +2% 목표는 미충족**이며 작성자는 현재 관측된 약 +5%를 수용해 개선분을 먼저 제안하기로 했다. 이 작성자 결정과 리뷰어의 수락은 구분한다.

## Scope and revisions

| 역할 | CUBRID revision |
| --- | --- |
| 고정 develop 기준 | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| OOS 통합 출발점, PR 대상 | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, `feature/oos-merge` |
| 현재 원격 PR head | `bcb900d1696756a120ec0a2b7885c212f71ebc07` |
| 실측한 개선 소스 | `02df4d9fe2d1f24168a18eda8d8be216e2c4ed99` |
| 이번 게시 제안 revision | `408d1352941e9d28a88b4d5c899bacf34e2ec1a0` |

게시 제안 revision은 기존 PR head에 이어지는 한 commit이다. 원격 PR의 benchmark와 추가 테스트를 보존하고 엔진 파일 4개를 실측 소스와 바이트 단위로 같게 맞췄다. `git diff 02df4d9 408d135 -- src`는 비어 있다. 두 revision 사이의 전체 차이는 benchmark 2개와 OOS SQL 테스트 3개뿐이다. 소스 일치는 새 binary의 실측 결과를 뜻하지 않으며, 아래 성능 수치는 `02df4d9` 구현을 측정한 기록이다.

reader·UPDATE 개선은 [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785)와 기존 PR #8299 하나로 검토한다. 별도 후속 [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816)은 [CBRD-26978 [OOS] [EPIC] TODO](https://jira.cubrid.org/browse/CBRD-26978)의 Sub-task이며 CBRD-27785와 `relates to`로 연결했다. OOS reclaim tail, allocator 구현, threshold parameter 및 기존 기준 2는 이번 변경에 포함하지 않는다.

## Implementation

### 공통 읽기와 값의 수명

`src/storage/heap_file.c:11205`의 `heap_attrvalue_point_variable`은 record에서 이미 구한 `HEAP_REC_LAYOUT`으로 가변값의 경계 offset 두 개를 같은 폭으로 읽는다. 기존 header·entry 범위 검사를 유지한다. OOS bit가 있으면 scalar Resolve가 값을 준비하고 같은 `heap_attrvalue_transform_to_dbvalue`가 타입 변환과 COPY·정리를 수행한다. 일반 heap 값을 위한 별도 변환 reader를 만들지 않는다.

`heap_attrinfo_read_dbvalues:11910`은 확인한 header 크기를 공통 layout에 전달한다. 공통 루프는 첫 오류를 즉시 반환한다. NULL, 기본값, 구 representation, collection 및 pending 값도 공통 변환을 사용한다. 다섯 helper의 inline 선언은 GNU indent 보호 안에 있으며 GCC에서 검증했다. 다른 compiler/platform은 검증하지 않았다.

`src/storage/heap_oos.cpp:742`는 요청 속성이 2개 미만이면 grouped 준비를 건너뛰고 기존 scalar Resolve로 진행한다. `src/storage/oos_file.cpp:2880`의 작은 완료 배열은 8개까지 stack을 사용하고 더 큰 요청은 vector를 사용한다. 외부 값의 주소·소유권 검사를 생략하지 않는다.

### 쓰기 layout과 pending owner

`heap_attrinfo_determine_disk_layout:13156`은 payload 크기와 FORCE_OUTLINE 선택을 한 순회에서 계산한 뒤 header를 구한다. 작은 크기 배열은 stack을 사용하며 더 많은 속성은 vector로 처리한다. OOS 계획은 처음 외부 저장 속성이 선택될 때 만든다. largest-first와 PREFER_INLINE 순서, 외부화가 값을 줄여야 하는 조건, OOS와 bigone의 동시 사용 거부는 기존 흐름을 유지한다. 실패한 STL allocation은 CUBRID 오류로 변환한다.

fixed/variable/columns writer (`heap_file.c:13856`, `13950`, `14136`)는 방금 기록한 header 크기와 offset 폭으로 VOT와 bound bitmap 위치를 구한다. 컬럼마다 header를 다시 해석하지 않는다. 기존 buffer 검사와 grow-and-retry를 유지한다.

`src/transaction/locator_sr.c:5534`의 `locator_update_force`는 native UPDATE가 가진 pending owner를 사용한다. copy-area/workspace 입력에 필요한 별도 owner는 `std::optional`로 늦게 생성한다. owner는 heap/index write와 오류 정리를 마칠 때까지 함수 scope에 남는다. finalization과 ownership·identity 검사, MVCC 및 WAL 처리 순서는 바꾸지 않는다.

## Performance evidence

재현 SQL의 출처는 [PR #7990 리뷰 답변](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6461744209)이다. 일반 테이블은 200,000행이며 두 SELECT와 `UPDATE ... SET a=a+1`을 비교했다. 성능 계수는 전체 서버의 user-space instructions이며 elapsed time이나 특정 worker만의 값으로 대체하지 않았다.

| 작업 | develop 중앙값 | 개선 구현 중앙값 | 변화율 |
| --- | ---: | ---: | ---: |
| 일반 풀 스캔 | 250.917M | 252.547M | +0.6498% |
| 일반 조건 스캔 | 531.611M | 538.854M | +1.3624% |
| 일반 UPDATE, 매번 새 복제본 | 6,472.427M | 6,580.235M | +1.6656% |
| 일반 UPDATE, 연속 COMMIT 별도 표본 | 6,457.729M | 6,565.068M | +1.6622% |
| 뒤의 별도 plain UPDATE batch | 6,463.624M | 6,787.826M | **+5.0158%** |

새 복제본의 네 라운드는 A→D, D→A, A→D, D→A 순서이며 라운드마다 5회 중 첫 회를 버렸다. 각 UPDATE 비율은 +1.6580%, +1.6669%, +1.6717%, +1.6692%였다. 연속 UPDATE 두 라운드 +1.7878%, +1.6468%는 별도 집합으로 유지했다. 유효한 실패를 버리거나 두 종류의 표본을 합쳐 통과시키지 않았다.

성능 빌드는 GCC 11.5.0, RelWithDebInfo, 실제 `-O2`·`-DNDEBUG`·frame pointer를 확인했고 UNIT_TEST 옵션은 모두 OFF였다. binary/DSO identity와 live config를 확인했다. 양쪽 4G data buffer, 256M log buffer, 16M sort, max_clients 50, physical active log 1,073,741,824B를 맞췄다. 서버는 같은 core 16–19에서 직렬 실행하고 CSQL은 core 12를 사용했다.

+5.0158% batch의 대응 테이블도 OID/HFID, 1,429 heap pages, 200,000행, 평균 92B가 같았다. 별도 탐색 DB의 이력 불일치에서 나온 +2.4612%/+2.4156%도 보존했다. 새 DB의 늦은 실패까지 앞선 물리 이력 차이로 설명할 수는 없다.

matched profile은 새 복제본 20개의 첫 UPDATE를 `cycles:u`, 499Hz, frame pointer로 수집했다. 반복 header 처리와 초기화가 개선 후보의 근거였다. 뒤 profile의 writer self 표본은 기준 1.35%, 개선 0.85%였으나 절대 instructions 절감율로 환산하지 않는다. **이 profile은 +5.0158% 실패 batch와 다른 실행**이다. 별도 진단에서 관측한 기준 서버의 약 103M vacuum instructions도 후보 실패의 직접 원인으로 확정하지 않는다.

## Correctness and limits

게시 제안 소스에서 `UNIT_TEST_OOS=ON`으로 빌드·설치한 뒤 집중 CTest **15/15**, **26.38초**를 통과했다. 기존 PR의 고정값/NULL/구 representation, 가변값/collection/1·2·4B offset, scalar·grouped OOS/pending COPY 검증도 포함한다. 기존 테스트와 assertion을 그대로 사용했다.

기존 OOS CMake/fixture 설정에 따라 설치 경로인 `CUBRID`와 격리된 registry 디렉터리인 `CUBRID_DATABASES`를 설정하고 구성한다. 실행한 선택식은 다음과 같다.

```sh
ctest --test-dir build --output-on-failure \
  -R '^(test_oos|test_oos_identity_stamp|test_oos_server|test_oos_sql_(crud|ddl|boundary|txn|bigone|deferred_write|visible_version|workspace_bytes)|test_oos_record_flags|test_oos_reference_errors)$'
```

`build`는 해당 설치를 대상으로 구성한 CMake build 디렉터리다. 이번 첫 실행은 초기화 전 CMake가 빈 `CUBRID_DATABASES`를 저장해 setup에서 실패했다. 환경 초기화 뒤 재구성한 동일 소스가 위 15/15를 통과했다. addr2line은 local PATH prefix로 `/usr/bin/addr2line`을 선택했으며 테스트 timeout과 assertion은 바꾸지 않았다.

그 뒤 게시 제안 commit으로 production 빌드·설치를 마쳤다. CMake cache의 모든 UNIT_TEST 옵션은 OFF이며 해당 엔진 파일의 SERVER_MODE/SA_MODE compile command 8개에서 `-O2`, `-DNDEBUG`, `-fno-omit-frame-pointer`와 test hook macro 부재를 확인했다. 설치한 `cub_server`, `csql`, `libcubrid.so.11.5`의 SHA-256과 build ID를 기록했다. 이 binary로 새 성능 측정을 실행하지는 않았다.

기존 snapshot/vacuum 선택 3/3은 예전 PR head의 결과이며 이번 revision의 재검증으로 집계하지 않는다. 전체 회사 CI, 다른 compiler/platform, 새 PR binary의 성능 측정은 아직 실행하지 않았다. 이번 수정의 국소 검증으로 crash recovery·HA·전체 회귀 corpus를 모두 통과했다고 주장하지 않는다.

현재 미충족 항목은 전체 plain 반복에서 일반 UPDATE를 기존 +2% 이내로 보장하는 것이다. 잔여 원인 규명과 재검증은 CBRD-27816에서 수행한다. OOS reclaim은 독립 재현과 correctness 검증을 갖춘 별도 작업으로 남긴다.
