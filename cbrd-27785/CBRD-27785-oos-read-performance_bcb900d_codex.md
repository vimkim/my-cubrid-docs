# CBRD-27785: 일반 heap 읽기의 OOS 통합 후 CPU 회귀 개선

작성일: 2026-10-27. 수정일: 2026-10-31, Asia/Seoul. 대상 독자: OOS 성능 변경을 검토하는 엔진 개발자.
관련 이슈: [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785).
출발점: [PR #7990 성능 보고](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6434778190).

## Purpose

질문은 OOS 값을 갖지 않는 일반 행도 통합 후 더 비싸게 읽는지, 그 비용을
기존 값 해석·소유권 계약을 유지하면서 줄일 수 있는지다. 재구성한 메모리 상주
스캔에서 회귀를 재현했고, 두 구현 티켓으로 좁은 스캔과 여러 컬럼 스캔의 증가분을
각각 약 1.11%, 1.36%로 낮췄다. 실행 순서를 뒤집어도 승인된 2% 기준을 통과했다.

- AS-IS: 일반 값 읽기에도 OOS Resolve의 큰 stack frame과 행별 준비 비용이 포함됐다.
- TO-BE: 일반 값은 작은 읽기 경로를 사용하며, 실제 OOS 값만 Resolve 준비를 수행한다.

이 결론은 양쪽 모두 heap인 작은 행의 읽기에 한정한다. 2026-10-27 조사 당시에는 원본
리뷰어의 전체 SQL과 하네스가 제공되지 않아 보고된 조건을 토대로 새로 구성했다.
10월 28일에는 상세 DDL·SQL이 제공됐고, 10월 31일의
[별도 원문 재현](CBRD-27785-reviewer-reproduction_4408135c_20261031_codex.md)에서 실행했다.
본문의 재구성 실험을 원댓글 전체 수치의 동일 재현으로 해석하지 않는다.

### 저장 경로에 따른 판정

| 경우 | 실제 develop / 적용본 저장 경로 | 판정 원칙 |
| --- | --- | --- |
| 1 | heap / heap | 비용 차이가 거의 없어야 한다. 이번 두 스캔의 +2% 기준은 여기에만 적용한다. |
| 2 | heap / OOS | 페이지당 여러 행을 유지하는 집적도의 trade-off다. warm CPU 증가만으로 결함을 판정하지 않고 I/O 조건의 이득도 측정한다. |
| 3 | overflow / OOS | 비슷하거나 빠른 성능을 기대하되 여러 OOS 컬럼의 분산으로 늘어나는 fetch 비용을 함께 설명한다. |

이는 사용자가 지정한 성능 해석 기준이다. 후속 UPDATE는 변경 전후 경로, 변경한 값과
유지한 OOS 값, 경계 이동을 구분한다. 선언 길이가 아닌 압축·header·offset을 포함한
실제 저장 크기와 heap/OOS/overflow 진단을 기록한다. heap 집적도, buffer hit/miss,
page fetch, storage I/O, 로그 양과 vacuum 상태를 함께 측정해야 한다.

### 검토한 소스

저장소는 `CUBRID/CUBRID`이며, 게시용 브랜치는 `vimkim/cubrid`의
`CBRD-27785-oos-read-performance`, 대상은 `feature/oos-merge`다.

| 역할 | 정확한 revision |
| --- | --- |
| 통합 전 기준 | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| 리뷰 보고 당시 head | `4408135c0833ec959da3590f12c14efa69610c7e` |
| 수정 전 feature 및 PR base | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| 빌드·정확성·최종 성능을 검증한 엔진 | `e77ffbf0e3c4a2dcf1f3a918bafcabf91ac136cd` |
| 최종 게시용 소스 | `bcb900d1696756a120ec0a2b7885c212f71ebc07` |

게시용 history는 private 작업 기록을 제외한 네 커밋이다. 엔진·C++ 테스트 blob은
검증한 엔진 revision과 동일하다. 마지막 커밋은 Python 하네스와 README만 고친다.
따라서 게시용 tip을 별도로 컴파일했다고 표현하지 않는다. 아래 소스 링크는 해당
게시용 SHA로 고정하며, 브랜치 게시 후 접근할 수 있다.

## Implementation

### 읽기 책임과 수명

`heap_attrinfo_read_dbvalues` 계열은 disk representation에 맞는 속성을 선택하고
요청한 `DB_VALUE`를 채운다. inline 값은 행의 bytes를 참조할 수 있지만, OOS Resolve가
반환한 임시 bytes는 conversion이 끝난 뒤 사라지므로 COPY가 필요하다. pending record는
아직 최종 저장 전인 값의 소유자다. 이를 전달하던 계약과 기존 형 변환·기본값 처리를
변경하지 않는다. 이 수정은 저장 형식, WAL, 이관 기준, locking이나 복구 절차를 바꾸지 않는다.

| 변경 위치 | 책임과 유지하는 조건 |
| --- | --- |
| [`heap_attrvalue_read_oos`, line 11566](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/storage/heap_file.c#L11566) | OOS Resolve scratch를 conversion까지 살려 두고, heap으로 할당한 임시 bytes는 기존 COPY 변환 후 해제한다. 오류는 기존 CUBRID error 경로로 반환한다. |
| [`heap_attrvalue_read`, line 11591](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/storage/heap_file.c#L11591) | 고정·기본값·inline 가변값을 작은 공통 reader로 읽는다. 실제 OOS 필드만 별도 helper로 보낸다. |
| [`heap_attrinfo_read_oos_dbvalues`, line 11737](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/storage/heap_file.c#L11737) | grouped Resolve vector와 준비 상태를 OOS 행 전용 helper에 둔다. 일반 행 loop는 이 상태를 준비하지 않는다. |
| [`heap_attrvalue_point_variable`, line 11206](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/storage/heap_file.c#L11206) | 기존 layout으로 header·entry 검사를 하고 BYTE/SHORT/INT 한 분기에서 두 offset을 읽는다. raw IS_OOS bit를 보존한다. |
| [`heap_midxkey_get_value`, line 11825](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/storage/heap_file.c#L11825) | 같은 필드 분류 helper를 사용하되 기존 index-key Resolve scratch와 복사·해제 수명을 유지한다. |

행 layout은 수정 전에도 행당 한 번 계산했다. 새 cache를 도입한 것이 아니다.
일반 reader와 loop의 작은 경로는 inline 처리하고, Resolve와 grouped 상태는 별도 함수에
둔다. 가변값의 길이가 0이면 기존처럼 NULL로 처리한다. collection/LOB의 물리 배치가
offset table 순서와 다를 수 있어 가장 가까운 더 큰 offset을 찾는 기존 탐색도 유지한다.
행의 요약 flag가 없어도 필드의 raw IS_OOS bit는 검사한다.

### 원인 분석과 진단 코드의 경계

원래 feature의 release assembly에서 공통 scalar reader의 stack 예약은 `0x4088`,
기준은 `0x58`바이트였다. 큰 frame 자체가 16KB 전체 초기화나 heap allocation을 뜻하지는
않는다. sampling에는 variable offset·분리된 conversion 경로의 비용도 나타났다.
sampling 비중을 instructions 증가량으로 해석하지 않았다.

같은 하네스의 진단 실험에서 일반 행에 기준 reader만 대입하면 약 +4.43% / +2.76%,
일반 행의 loop까지 기준 형태로 바꾸면 +1.81% / +0.96%였다. 원상 복구 후에는
약 +5.14% / +8.90%로 돌아왔다. 이는 공통 읽기의 OOS 대응 준비·dispatch가 주요 비용임을
뒷받침한다. scratch, inlining과 코드 배치 각각의 기여율까지 분해한 결과는 아니다.
진단용 기준 reader 복사본은 최종 코드와 설치에서 제거했다.

### 추가한 정확성 검증

| 위치 | 검증 내용 |
| --- | --- |
| [`test_oos_sql_crud.cpp`, line 328](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/unit_tests/oos/sql/test_oos_sql_crud.cpp#L328) | 고정값, NULL, 기본값과 구 schema 표현 읽기 |
| [`test_oos_sql_workspace_bytes.cpp`, line 303](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L303) | NULL·빈 값·큰 inline 값의 내용/길이, 여러 가변값·inline/OOS 혼합, 구 표현과 새 기본값 |
| [`test_oos_sql_workspace_bytes.cpp`, line 361](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L361) | 실제 SQL bytes를 기존 native heap API로 읽으며 BYTE/SHORT/INT offset, collection 물리 순서, eager/without-OID/lazy 읽기, 광고된 길이 오류를 확인 |
| [`test_oos_sql_deferred_write.cpp`, line 864](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/unit_tests/oos/sql/test_oos_sql_deferred_write.cpp#L864) | source 값 소멸 후 pending grouped/scalar Resolve 내용과 scratch/heap 크기별 수명 |

새 public 테스트 API를 만들지 않고 기존 fixture와 native API를 사용했다.

## Remarks

### Test Plan

서버를 직렬로 실행하고 각 설치에 새 DB를 만들었다. Linux x86_64, GCC 11.5.0,
RelWithDebInfo의 `-O2 -ggdb3 -DNDEBUG -finline-functions` 조건이다. feature 빌드에는
기존 OOS native 테스트용 `CUBRID_UNIT_TEST_ENABLED`가 포함되며, baseline에는 이 OOS
테스트 코드가 없다. compiler와 최적화 설정은 맞췄다.

이 기록에는 DB 생성 locale과 실제 테이블·컬럼의 charset·collation이 측정 조건으로
명시되지 않았다. 원댓글과 이 조건이 같은지는 미확인이다. 아래 수치는 당시 고정 입력의
비교 결과로 보존하며 다른 문자셋에 적용하거나 새 실험의 locale을 소급해 붙이지 않는다.
후속 비교에는 [문자셋을 포함한 측정 조건](CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md#charset-conditions)을 기록한다.

`data_buffer_size=4G`, `log_buffer_size=16M`, `max_clients=20`, query cache entries/pages는
모두 0이다. registry·master port·TMP는 분리했다. 서버 CPU는 같은 NUMA node의 서로
다른 physical core 16–19, CSQL은 core 12를 사용했다. 공유 호스트이며 전용 CPU 예약은 아니다.

입력은 `(id INTEGER PRIMARY KEY, v INTEGER, payload VARCHAR(80))` 20만 행이다.
`payload`는 `x` 80개이고, `v`는 id의 100 나머지다. 쿼리는 다음과 같다.

```sql
SELECT SUM(CAST(v AS BIGINT)) FROM n;
SELECT SUM(CAST(id AS BIGINT)), SUM(CAST(v AS BIGINT)), SUM(LENGTH(payload)) FROM n;
```

실행당 20회 스캔, 쿼리별 2라운드 × 5회에서 각 라운드의 run 0을 버린다.
`perf stat`을 서버에 붙여 `instructions:u`, `cycles:u`, task-clock을 보존한다.
결과 checksum·문장 수·프로세스 identity·counter 유효성을 검사한다.
hardware event running은 100%, 최종 표본의 instructions 범위는 중앙값의 0.009% 미만이었다.
warm trace는 TABLE SCAN·worker 4개·I/O read 0이었다. wall time은 CPU 합격 판정에 쓰지 않았다.

실제 저장 진단은 세 설치 모두 heap 200,000행, overflow 0행, heap 1,653페이지,
평균 행 길이 108바이트다. report/candidate에는 연결된 OOS 파일과 OOS 행·페이지가 없다.
측정과 별도로 native `SHOW HEAP CAPACITY OF n`, feature의 `SHOW HEAP OOS OF n`으로
경우 1임을 확인했다. 마지막 하네스 측정에서도 같은 입력을 DML 없이 유지했다.

| 단계와 순서 | 좁은 스캔 / 기준 | 여러 컬럼 스캔 / 기준 |
| --- | ---: | ---: |
| 초기 수정 전 feature, 정순 | +5.1249% | +8.8904% |
| 티켓 01 완료, 정순 | +1.1052% | +5.7577% |
| 최종 하네스의 report 음성 대조군, 정순 | +5.127452% | +8.886182% |
| 최종 하네스의 수정본, base → report → candidate | **+1.106605%** | **+1.362198%** |
| 최종 하네스의 수정본, candidate → report → base | **+1.107484%** | **+1.362450%** |

티켓 01은 좁은 스캔만 통과했고, 티켓 02가 여러 컬럼 스캔을 완료했다.
최종 두 쿼리 모두 +2% 기준을 통과했다. 보고 당시 head를 같은 기준으로 검사하면
회귀 판정이 유지된다. 최종 하네스 변경 전후의 raw 결과를 덮어쓰지 않았다.

정확성 결과는 집중 CTest **15/15**(149.87초), snapshot/vacuum 선택 **3/3**(23.92초),
formatter 후 새 characterization **4/4**(27.43초) 통과다. SERVER_MODE·SA_MODE를 빌드·설치했다.
집중 범위에는 native OOS·identity/header/stub 오류, server, SQL CRUD·DDL·transaction·boundary·
bigone·visible version·workspace bytes·deferred write와 fixture setup/cleanup이 포함된다.

준비된 동일 설치 환경에서 실행한 CTest 선택을 프로젝트 명령으로 나타내면 다음과 같다.
`build`는 OOS 테스트가 설정된 빌드 디렉터리다.

```sh
ctest --test-dir build -R '^(test_oos|test_oos_identity_stamp|test_oos_record_flags|test_oos_reference_errors|test_oos_server|test_oos_sql_(crud|ddl|txn|bigone|boundary|workspace_bytes|deferred_write|visible_version))$' --output-on-failure -j 1
GTEST_FILTER='OosRealVacuum.*Snapshot*' ctest --test-dir build -R '^test_oos_real_vacuum_server$' --output-on-failure -j 1
```

하네스 재현은 [소스 README](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/contrib/benchmarks/oos-performance/README.md)를 따른다.
동일한 최종 `bench.py`로 독립 baseline/candidate DB를 한 번에 하나씩 측정하고, 최종 판정은
`compare --max-overhead-percent 2`를 명시한다. fixture는 기존 테이블을 삭제하지 않는다.

### 하네스 provenance와 최종 리뷰

리뷰에서 PATH의 CSQL이 선택한 `$CUBRID/bin/csql`과 같은지 검사하지 않는 문제가 나왔다.
기존 하네스는 실제 다른 설치의 client로도 완료했으나, 수정 후에는 SQL·counter 실행과
결과 디렉터리 생성 전에 exit 2로 거부한다. 이후 모든 SQL은 검사한 절대 경로를 사용하고,
summary에 client 경로·SHA-256을 저장한다. 이 동작을 실제 native CLI로 확인하고,
맞는 client를 선택하여 정순·역순 전체 측정을 새로 실행했다.

| 최종 근거 fingerprint | SHA-256 |
| --- | --- |
| 측정한 최종 `bench.py` | `57c344a47a70bbdc1b91d01634c31a29d0c106a0b3d9d6dc40424662d51f679b` |
| candidate CSQL | `6cf8e3812a6129de22395257e5e7d2ae8697dd89b7f496503d10687383275079` |
| 로드된 candidate engine DSO | `041c7c07b74e7cb69c3fdab3cbdb9c60c44d71c033c91c33fdba273fa95902ec` |

Standards와 Spec의 독립 리뷰 및 이 수정의 delta 리뷰를 완료했다. 남은 규칙 위반과
명세 불일치 지적은 0개다. Python·README만 바뀐 마지막 수정에서 C++를 다시 빌드하거나
같은 정확성 검사를 반복하지 않았으며, 동일한 소스 blob과 설치 DSO를 확인했다.

raw SQL·counter·출력·설정·실행 파일 identity·저장 진단과 판정 JSON은 작업 근거 저장소에
보존했다. 대표 기록은 `ticket02-verdict.json`, `actual-storage.json`,
`correctness-contract.json`, `review-fixes-verdict.json`이다. 공개 문서는 이 요약을 보존하며
기계별 raw 로그를 Git에 추가하지 않는다. 작업 소유 native 프로세스는 중단했고 DB·로그와
설치는 보존했다.

이 결과는 전체 회사 CI, ASAN, HA·복구 인증 또는 OOS 전체 성능 인증이 아니다.
CBRD-27230의 UPDATE 재사용, OOS 설정, 경우 2·3과 buffer보다 큰 데이터는 후속 범위다.
