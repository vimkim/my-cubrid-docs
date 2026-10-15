# PR7925 현재 HEAD CI 분석: b755678cd / run 37747856853

작성·검증: **2026-10-15 (Asia/Seoul)**. 대상은 [PR #7925](https://github.com/CUBRID/cubrid/pull/7925), CBRD-27424, 엔진 `b755678cd9a3ab465215228d5664f7f1edf24846` 이다. Work Item **386**의 분석 결과이며, **371의 10월 16일 실제 OOS 병합 목표**를 위한 후속 작업을 제시한다.

## 판정과 결정 범위

현재 check가 가리키는 [run 37747856853, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/37747856853)은 **medium 3건·shell 4건 실패, SQL 실패 0건**이다. 보관된 head/base 수집은 모두 완결되어 있다. 이번에 각 780개 raw 파일의 크기·해시와 schema, observation, provenance, 실패 메타데이터, 집계를 다시 검증했다. 수집 중단 경고였던 [과거 28b65 보고서](ci_analysis_report_28b65d18a_codex.md)와 별개인 현재 HEAD의 정식 분석이다.

- **Medium 3건:** 보고된 여섯 불일치 조회는 모두 정렬 없는 조회이고, 다섯 변환값의 multiset이 보존된다. 공개 TC `0d9f5b448`의 여섯 `ORDER BY f` 추가가 정확히 해당 조회를 안정화한다. 기존 `ORDER BY 1`/`DESC` 검증과 나머지 답안은 보존된다. 적용 근거는 높지만, 수정 TC의 `b755` 실행 PASS 및 물리적 배치 변화의 최초 원인은 미확인이다.
- **Partition 1건:** 원래 TC는 `<10`인 p0에 `1,100`을 적재하고 성공을 기대한다. 현재의 partition 거절과 `0 inserted / 1 failed`는 잘못된 기대를 드러낸다. 비공개 TC `10f350029`의 거절·rollback·정상 후속 load 검증이 적용 대상이다. 현재 CI만으로 실제 rollback 또는 후속 load 성공까지 입증하지는 못한다.
- **나머지 shell 3건:** `bug_bts_15156`, `cbrd_27064`, `cbrd_27075`는 정확한 base에서도 대응하는 실패 서명이 관찰된다. 이를 무해함이나 PR 영향 없음으로 확대하지 않는다. CDC 두 건은 ADR-0005의 후속 설계 범위로 남기고 활성 상태와 실패를 보존한다.

비교 집계는 head 7건 = **`also_observed_on_base` 3 + `additional_on_head` 1 + `uncomparable` 3**이다. Base 5건 = 공유 3 + **`base_only` 2**이다. Medium은 base의 양성 PASS를 확인했지만, 현재 보관 증거로 실제 실행 선행 상태를 맞춘 인과 비교를 완성할 수 없어 보수적으로 `uncomparable`로 둔다. 이는 head 실패 목록의 유효성을 낮추지 않는다.

이 보고서는 필요한 TC 수정과 검증을 식별한다. 엔진 수리 완료, PR7927 최신 구현 적응, shared partition acceptance, CI 통과 또는 병합 준비 완료를 선언하지 않는다. 소스·TC 편집, DB 재현, CI 실행, 원격 게시와 병합은 수행하지 않았다.

## 고정한 실행과 집계

2026-10-15 20:56 KST 관찰에서 PR은 OPEN, non-draft, APPROVED이며 head repository는 `vimkim/cubrid`, head branch는 `CBRD-27424-oos-loaddb-sa`, target은 `feature/oos-merge` 이다. `cubrid-ci status`의 단일 새 snapshot도 동일 head를 확인했다. 새로운 collect/collect-base는 실행하지 않고 10월 8일의 완결된 수집을 재사용했다.

| Suite | Head 상태·판정 | Head planned / run / passed / failures / skipped | Base 상태·판정 | Base planned / run / passed / failures / skipped |
| --- | --- | --- | --- | --- |
| `test_medium` | completed / FAIL | 975 / 975 / 972 / 3 / 0 | completed / PASS | 975 / 975 / 975 / 0 / 0 |
| `test_shell` | completed / FAIL | 3289 / 3259 / 3255 / 4 / 30 | completed / FAIL | 3289 / 3259 / 3254 / 5 / 30 |
| `test_sql` | completed / PASS | 17471 / 17471 / 17471 / 0 / 0 | completed / PASS | 17471 / 17471 / 17471 / 0 / 0 |

모든 행에서 `tests = planned`, `errors = 0`, `unrun = 0` 이다. `tests = passed + failures + errors + skipped`, `planned = run + unrun + skipped` 를 각각 대조했다. Head 전체는 21735 tests / 21705 run / 21698 passed / 7 failures / 30 skipped다. Shell의 skip 30건은 기존 runner 집계이며 이번 분석에서 제외를 추가한 것이 아니다. 같은 head의 debug/release build status는 모두 SUCCESS지만, 이 회귀 테스트들의 build provenance는 **debug**다.

| 실행 identity | Head | 정확한 merge-base |
| --- | --- | --- |
| 엔진 SHA | `b755678cd9a3ab465215228d5664f7f1edf24846` | `fb567a629cdb390fff920542173fa36f454c74a0` |
| suite run / attempt | [37747856853 / 1](https://github.com/CUBRID/cubrid/actions/runs/37747856853) | [36570256001 / 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001) |
| 소비한 build run / attempt | 37747856853 / 1 | 36570061594 / 1 |
| 수집 완료 시각 UTC | 2026-10-08 09:07:52 | 2026-10-08 08:12:40 |
| 공개 TC SHA: medium·SQL | `bdba62aee0faec05abdd861518824c69b6c1b3c5` | 동일 |
| 비공개 TC SHA: shell | `c4b9d482fbd491a68510b2552df2c3cac91911fc` | 동일 |
| TC provenance branch | `tc/pr-7925` | `tc/pr-7990` |
| CTP SHA | `44e3f97c788ad82091d5b66d728852f3279b1e86` | `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` |

엔진 identity는 workflow의 `head_sha`나 run 제목이 아니라 각 shard의 `build.read`와 summary의 소비 build 정보로 검증했다. Base가 다른 PR 제목으로 실행되었어도 이 엔진 identity가 맞으면 비교 증거가 된다.

## 실패별 목록

`관찰 높음 / 원인 낮음`은 실패와 입력을 확인했지만 그 최초 발생 원인은 확정하지 못했다는 뜻이다. 모든 경로는 summary에 기록된 suite-relative 전체 경로다.

| ID | Suite / testcase 전체 경로 | Head 관찰 / base 관찰 | 비교 분류 | 범주·PR 관계·신뢰도 | 다음 조치·담당 |
| --- | --- | --- | --- | --- | --- |
| M1 | `test_medium`: `medium/_02_xtests/cases/to_char_order_by.sql` | 숫자·date·time·timestamp 네 무정렬 조회의 값 순서 변화 / base case PASS | `uncomparable` | TC 결정성 + 실행 상태 검증 공백; `plausible`; 관찰·수정 적용성 높음, 최초 원인 낮음 | PR7925 작성자와 공개 TC 담당: 정렬 수정 포함 후 선행 workload를 보존해 재검증 |
| M2 | `test_medium`: `medium/_02_xtests/cases/to_number_order_by.sql` | `3,5,1,2,4` 기대에 `4,1,2,3,5` / base case PASS | `uncomparable` | TC 결정성 + 실행 상태 검증 공백; `plausible`; 관찰·수정 적용성 높음, 최초 원인 낮음 | M1과 같은 공개 TC 검증에 포함; 기존 ASC/DESC 유지 |
| M3 | `test_medium`: `medium/_02_xtests/cases/to_timestamp_order_by.sql` | 날짜 day 순서 `2,5,1,3,4` 기대에 `3,5,1,2,4` / base case PASS | `uncomparable` | TC 결정성 + 실행 상태 검증 공백; `plausible`; 관찰·수정 적용성 높음, 최초 원인 낮음 | M1과 같은 공개 TC 검증에 포함; 날짜·시각의 정확한 쌍 유지 |
| S1 | `test_shell`: `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh` | test2 partition 거절·0 inserted/1 failed 대 2 inserted 성공 답안; 마지막 count 비교는 OK / base case PASS | `additional_on_head` | TC 기대 수정 + rollback 검증 공백; 공유 loader 변경과 `direct`; 기대 오류·적용성 높음, 현재 전체 계약 충족은 미검증 | PR7925/PR7927 담당: 수정 TC로 거절·rollback·root/child routing·후속 load 검증 |
| S2 | `test_shell`: `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh` | master 재시작 조건 성공 뒤 server-stop 성공문구 count=0, 최종 assertion NOK / base도 동일 조건 실패 | `also_observed_on_base` | service lifecycle 진단; `unlikely`; 서명 높음, 서비스 실패 원인 낮음 | QA/service 담당: server.log·service.log·PID와 종료 상태를 보존한 격리 재현; CI 해결 또는 명시적 처리 필요 |
| S3 | `test_shell`: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | INSERT OK; DELETE·UPDATE extract rc=-10, 부족한 target count / base도 같은 추출 실패 유형 | `also_observed_on_base` | CDC/OOS-history 후속 설계; `unknown`; 선재 서명 높음, 개별 오류 인과 낮음 | CDC/OOS-history 담당: 활성 실패 보존, ADR-0005 후속 설계에서 추출·값 보존 검증 |
| S4 | `test_shell`: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | 4K/8K/16K 모두 EXTRACT_ERR>0, CONFIGS_OK=0 / base도 동일 유형 | `also_observed_on_base` | CDC/OOS-history 후속 설계; `unknown`; 선재 서명 높음, 수치 변화의 원인 낮음 | CDC/OOS-history 담당: 페이지별 extract 오류·LSA를 보존; 성공 기대 완화 없이 후속 수리 |

Base-only 두 건은 head 총계에 포함하지 않는다.

| Base-only testcase 전체 경로 | Base 서명 / head 양성 증거 | 후속 조치 |
| --- | --- | --- |
| `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh` | qa9 process-argument masking 비교에서 `******` 누락; assertion 7 NOK / head shard 07의 명시적 PASS testcase record | QA/process 담당: process sampling과 실제 masking을 구분. head PASS 한 번을 보안 문제 해결로 해석하지 않는다 |
| `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh` | assertion 2·3의 DB-link 인증/응답 기대 불일치 / head shard 27의 명시적 PASS testcase record | DB-link/QA 담당: 잘못된 인증 실패와 정상 암호 변경 후 접근을 각각 대조. OOS 수정 효과로 귀속하지 않는다 |

S2/S3/S4의 추출된 `diff.txt`는 각각 base와 SHA-256까지 같다. 다만 diff는 NOK 표식만 포함하는 경우가 있어, 같은 diff만으로 분류하지 않았다. 아래의 실제 message 조건과 exact TC도 읽었다. Base-only 분류도 단순 실패 목록 부재 대신 JUnit의 양성 PASS를 확인했다.

## Medium: 정렬 수정 적용성과 원인 경계

### 관찰한 값과 assertion

Exact 공개 TC의 SQL은 M1에 네 개, M2/M3에 각각 한 개의 무정렬 조회를 갖는다. 각 조회 뒤의 `ORDER BY 1`과 `ORDER BY 1 DESC`는 별도 변환 결과 정렬 검증이다. 모든 fixture는 서로 다른 다섯 `f` 값을 사용한다. 현재 failure message에 보고된 여섯 조회는 전부 무정렬 조회와 대응한다.

M1의 date/time diff는 표시 중간에서 `02/0`과 나머지 문자열이 나뉘므로 개별 diff 줄을 값으로 취급하지 않았다. 문맥·삭제·추가 fragment를 복원하여 다섯 값을 대조했다. 숫자, date, time, timestamp 네 그룹 및 M2/M3 모두 **기대·실제 multiset이 같고 다섯 값이 한 번씩 존재**한다. M3는 날짜와 시각을 한 값으로 비교했다. 값 변경·행 누락 또는 중복은 이 여섯 mismatch에서 관찰되지 않았다. 전체 DB 무결성을 검증했다는 의미는 아니다.

[ORDER BY 매뉴얼](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/query/select.rst#L561)은 정렬 없는 조회 순서가 달라질 수 있음을 명시한다. 이를 근거로 기존 변환 결과의 정렬 검증을 지우거나 답안을 실제 출력에 맞추지는 않는다.

[검토된 공개 TC 변경](../cbrd-27089/tc-pr-3664-review_0d9f5b448_codex.md)의 base는 이번 CI 공개 TC SHA와 정확히 같다. `git show`로 여섯 SQL/답안 Git object를 다시 대조했다. 변경은 무정렬 조회 여섯 곳의 `ORDER BY f` 추가와 대응 답안의 행 재배열뿐이다. 답안의 변경 블록은 행의 바이트 multiset이 같고, 나머지 SQL·답안 블록은 바이트 동일하다. 현재 fixture에는 정렬 동률이 없다. **따라서 M1–M3의 TC 수정 적용성은 높다.**

### 추론·모르는 점·반증 조건

관계는 공유 PR7927 구현에 의한 배치 차이일 가능성이 있는 `plausible`로 둔다. [후속 medium 진단](../cbrd-27089/medium-local-diagnosis/report.md)은 `f3144ab`/`fb567a6`에서 `_01_fixed` 114개를 앞에 두면 558개 workload의 head 세 실패/base 통과를 반복 재현했고, 대상 값·저장 bytes·삽입 순서가 같은 상태에서 physical OID 배치가 달라졌음을 보였다. `_02_xtests` 444개만 실행한 초기 PASS보다 이 후속 증거가 더 구체적이다. Heap 재사용 통제와 base에서 다른 prefix로 같은 서명이 나온 반례도 있다. [bestspace 분석](../cbrd-27089/PR7927-medium-bestspace-divergence-ko.md)의 경계와 함께 읽어야 한다.

이번 `b755`의 관련 `heap_file.c`, `heap_oos.cpp`, pending-record/value-ref, partition/query 소스는 `f3144ab`과 동일하지만 loader·locator에는 추가 차이가 있다. 위 진단을 현재 HEAD의 직접 재현으로 바꾸어 쓰지 않는다. 공개 TC의 `medium/files/mdb.tar.gz`는 양쪽 동일 Git object이고 SHA-256은 `63833b7abf965621539bc4216aeb5fc3527c173c7a4d91436bd113a2f4269a06` 이다. CTP revision 차이의 tracked 파일은 compatibility용 `util_compat_test.sh` 하나뿐이며 medium config·runner·CQT JAR는 같다. 따라서 CTP revision이 다르다는 이유만으로 medium 원인을 도구에 돌릴 근거도 없다.

현재 수집에 남은 `summary_info`의 목록은 디렉터리 역순으로 묶이며, JUnit의 case 나열 순서도 head/base에서 다르다. 이 목록을 실제 dispatch 순서로 취급하지 않았다. PR7927 진단이 다른 실행의 job log에서 확인한 975개 실행 순서를 현재 `b755` 실행으로 전용하지도 않았다. 현재 retained bundle만으로는 실행 당시 archive/config override·JDBC/locale bytes·heap 상태·실제 prefix의 완전한 동등성을 입증하지 못하므로 M1–M3의 인과 비교 분류는 `uncomparable`다. Base의 해당 세 case PASS 자체는 검증된 관찰이다.

**반증 조건:** 값 multiset 변화나 명시적 정렬 조회 불일치가 나오면 “현재 여섯 mismatch는 순서만 다름”의 적용 범위를 벗어난다. 같은 TC·config·prefix에서 base도 같은 서명을 보이면 head 고유 엔진 결함 가설은 약해진다. 정렬 수정 후에도 값·ASC/DESC가 틀리면 TC 결정성 수정만으로 해결할 수 없다.

**다음 조치:** 공개 TC 담당과 PR 작성자는 `0d9f5b448`의 검토된 변경이 통합 후 실제 선택될 TC 입력에 포함되는지 확인하고, 실제 통합 엔진에서 선행 workload를 보존한 medium 검증을 남긴다. 세 파일만 단독 PASS인 결과로 닫지 않는다. 기존 PR7927 실행의 975/975 PASS는 `f3144ab` + 수정 TC의 근거이며 `b755`의 결과가 아니다. 엔진 repair는 이 관찰만으로 특정하지 않는다.

## Partition: 실패 기대가 잘못되었는가

### 관찰과 소스 연결

Exact `partition_tbls.sh`의 test2는 `t(i int) partition by range(i) (partition p0 values less than(10))`에 `1`을 넣고 unloaddb한 뒤 객체 파일에 `100`을 추가한다. Linux 답안은 test2에 `dba.t__p__p0 2 instances committed`와 `Total 2 object(s) inserted, 0 object(s) failed.`를 기대한다. 스크립트의 “generate an error” 설명과 성공 답안도 서로 맞지 않는다.

현재 message/diff는 `Line 6:Appropriate partition does not exist.`와 `Total 0 object(s) inserted, 1 object(s) failed.`를 보인다. test1의 40행, test3의 10000행 성공 transcript는 비교의 공통 부분이며, 두 번째 count/schema assertion은 `partition_tbls-2 : OK`다. 실패를 모든 partition load 실패 또는 OOS 값 손상으로 확대할 근거가 없다.

[Range 규칙](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L115)과 [direct-child 규칙](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L325)은 범위 밖 값을 거절한다. SQL 매뉴얼만으로 loader 구현을 증명하지 않고, 현재 소스도 대조했다. `server_object_loader::start_attrinfo`는 root/child에 따라 pruning 종류를 정하고, [flush_records](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/loaddb/load_server_loader.cpp#L815)는 partition 레코드를 `locator_insert_force`로 전달한다. [partition_find_partition_for_record](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/query/partition.c#L3530)는 목적지가 없으면 `ER_PARTITION_NOT_EXIST`, [직접 child 검사](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/query/partition.c#L3671)는 선택한 child와 다르면 `ER_INVALID_DATA_FOR_PARTITION`을 반환한다. `100`을 받을 다른 child도 없는 현재 fixture의 진단과 일치한다.

이 경로는 base 대비 변경되고 PR7927의 공유 구현에 포함된다. `f3144ab` 대비 `b755` loader 차이는 force-flag 인터페이스 적응이며 partition pruning 선택은 유지된다. 따라서 S1은 공유 loader 경로와 `direct` 관계, base PASS 대비 추가 관찰이다. 현재 CI는 생성 object 파일의 `%class` 원문을 보존하지 않아 target header를 직접 확인할 수 없지만, 원래 답안·생성 절차·현재 진단과 기존 독립 probe가 같은 잘못된 입력 문제를 지지한다.

### 적용할 수정과 남은 acceptance

[비공개 TC 리뷰](../cbrd-27089/tc-pr-4335-review_10f350029_codex.md)와 [독립 partition 평가](../cbrd-27089/testcase-assessment/assessment.md)는 현재 CI와 **같은 비공개 TC base**에서 `10f350029`를 만들었다. 변경은 원래 세 파일의 잘못된 test2 성공 transcript를 제거하고 다음 계약을 검증한다.

1. 생성 객체 header가 child 입력인지 검사한다. `-c 100`으로 두 행을 같은 commit 구간에 두고 실패 exit·진단·0 inserted/1 failed를 확인한다.
2. root와 p0를 직접 조회하여 failed batch의 0행 rollback을 확인하고, 같은 DB에서 유효한 `1`의 후속 load와 정확한 행을 확인한다.
3. 두-child fixture에서 root `1,11` routing, 유효 p0 `2`, 잘못된 p0 `3,11` 및 root `4,100`의 거절·batch rollback, 기존 committed `1,2,11` 보존, 후속 root `12`를 검사한다.

기존 `f3144ab` + `10f350029` native 검증은 1 case / 28 OK / 0 NOK / 0 skip이다. 이 근거는 TC oracle의 타당성을 지지한다. 현재 `b755`와 수정 TC의 실행 결과를 대신하지 않는다. INT fixture이므로 OOS value chain의 목적지 heap 소유권·vacuum·복제까지 검증하지도 않는다.

**미확인:** 현재 원래 TC는 test2의 failed batch 이후 root/child를 조회하지 않으므로, `0 inserted` 출력만으로 rollback을 확정할 수 없다. Windows 답안은 검토되었지만 Windows 실행은 별도다.

**반증 조건:** 수정 TC에서 유효 child 입력도 거절되거나, 실패 batch의 앞 행이 남거나, 기존 commit이 사라지거나, root routing이 틀리면 TC 기대 오류만으로 설명할 수 없다. 이때 PR7925/PR7927 담당은 해당 locator/pruning/transaction 경로의 엔진 수리로 전환해야 한다.

**다음 조치:** 실제 통합 엔진과 수정 TC로 위 계약을 검증한다. TC를 적용하고 실제 acceptance가 통과하기 전까지 S1을 해결 완료로 표시하지 않는다. PR7927의 실제 통합 결과와 이후 변경에 대한 workspace 적응은 [별도 의존성 설명](PR7925-PR7927-dependency_b755678cd_ko.md)의 범위이며, 현재 브랜치에 오래된 `f3144ab`이 포함된 것만으로 완료되지 않는다.

## 기존 shell 서명의 처리

### S2: master 재시작 뒤 server-stop assertion

양쪽 exact message에서 master 시작 성공문구 count는 1, master 프로세스 count는 1이다. 이후 `cubrid server stop 15156`의 성공문구 count가 반복해서 0이며, 21회 시도 뒤 최종 조건이 NOK다. CPU 상한 assertion 실패로 잘못 분류하지 않았다. 두 실행 모두 표시 duration 228초이며 message 안의 Internal Error 집계는 0이다.

**추론:** 서비스 재연결·종료 상태 또는 runner 환경의 문제일 가능성이 있고 workspace OOS 변경과 관계는 `unlikely`다. **미확인:** 실패한 `server.log` 원문과 PID/프로세스 상태가 독립 artifact로 남아 있지 않아 실제 서버 부재·종료 실패·진단문구 차이를 구분할 수 없다. Internal Error 0은 crash나 오류 전체의 부재 증명이 아니다.

**반증·조치:** matched 서비스 환경에서 base는 정상 stop하고 head만 실패하거나 engine stack 차이가 나오면 낮은 PR 관련성을 재검토한다. QA/service 담당은 해당 로그·exit·PID를 보존한 격리 재현을 수행해야 한다. assertion을 지우거나 시간만 늘리는 변경은 현재 증거로 정당화하지 않는다. Pre-existing 분류는 CI 요구를 면제하지 않는다.

### S3/S4: CDC 추출 오류와 허용된 후속 범위

S3은 양쪽 모두 INSERT regression OK, DELETE와 UPDATE round 1/3에서 extract rc=-10·extractor exit 1이다. DELETE target count는 head **1/700**, base **23/700**이고 UPDATE는 모두 **0/2400**이다. 표시된 corruption count는 모두 0이다. rc=124 timeout 서명이 아니며, corruption 0도 정상 추출을 뜻하지 않는다.

S4는 다음 차이가 있다. 세 설정 모두 FINAL_SEQ=2000, FIND_OK=30, FIND_NOTFOUND=0, FIND_ERR=0, CORRUPTION=0이고 전체 CONFIGS_OK=0이다.

| 페이지 | Head EXTRACT_ERR / TOTAL_ITEMS | Base EXTRACT_ERR / TOTAL_ITEMS |
| --- | --- | --- |
| 4K | 2 / 285 | 4 / 295 |
| 8K | 4 / 296 | 4 / 304 |
| 16K | 4 / 300 | 4 / 300 |

Exact 스크립트·C driver는 양쪽 같은 Git object다. S3은 4K DB/log, supplemental logging, 비압축 로그를 사용하며 random payload를 생성한다. S4도 `/dev/urandom` payload, archive rollover, 시간 기반 LSA probe를 사용한다. Shard와 host·실행 시각·payload·LSA·관찰 건수가 다르므로 **같은 추출 실패 유형의 선재성**만 판단한다. 감소한 오류 수를 개선, 감소한 target count를 퇴행으로 수치 비교할 수 없다. 다른 최초 원인이나 PR의 추가 영향도 배제하지 않는다.

[OOS 규범 §5](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md)와 [ADR-0005](/home/vimkim/gh/cubrid-oos-context/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md)는 complete OOS-history 변경을 11.5 병합에서 유보하고 이 두 테스트를 활성·가시적 실패 상태로 유지하도록 정한다. 읽은 규범은 2026-10-08 수정본, SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65` 이다. ADR은 개별 rc=-10의 stack 원인을 증명하지 않는다. 이전 durable-image 설계를 즉시 적용할 승인으로도 사용하지 않는다.

**반증·조치:** payload·시간/LSA·설정을 고정한 paired 실행에서 head 고유의 다른 오류/stack이 나오면 별도 regression을 추가한다. CDC/OOS-history 담당은 deferred redesign의 추출 계약·이미지 수명·오류 처리를 검토하고 양성 성공을 재검증해야 한다. 지금은 테스트나 답안을 완화하지 않고 남긴다. 프로젝트 CI의 최종 허용 판정은 별도 결정이며, 이 문서가 CI green을 대신하지 않는다.

## Baseline 유효성과 비교 제한

10월 8일 baseline selection은 PR7925 head `b755…`, target `feature/oos-merge` tip `fb567a6…`, 유일한 merge-base `fb567a6…`를 고정한다. 관계 관찰 시각은 `2026-10-08T08:09:45.475399145Z` 이다. 로컬의 pinned 두 commit으로 `git merge-base --all`도 같은 결과를 확인했다. Discovery는 exact-commit statuses/check-runs 전체 페이지이며 repository-wide workflow scan이 아니다. 선택된 실행만 사용했고 과거 green 실행으로 바꾸지 않았다.

Base root는 같은 엔진 commit을 여러 PR이 공유하므로 현재 `manifest.json`에 10월 12일 PR8128 selection이 들어 있다. 현재 포인터를 PR7925 자료로 사용하지 않았다. 당시 저장된 `base-result-manifest.json`을 선택하여 schema-v3 command/manifest와 observation-v2 request/result를 검증했다. 이 manifest의 JSON 내용은 당시 terminal observation의 `.command`와 정확히 같고, observation ID·PR7925/head·target·merge-base·요청 suite와 옵션이 맞는다. Head는 schema-v2/observation-v1이다.

원래 base root manifest의 byte hash `488f2579…`와 저장 manifest의 `a61a6fad…`는 직렬화가 달라 같지 않다. 이를 동일 byte라고 주장하지 않았다. 선택한 저장 manifest의 내용 일치, 당시 observation, 모든 summary·raw index의 digest와 **780개 raw 파일**, 실패 message/diff digest를 별도로 검증했다. 재검증 receipt는 manifest 직렬화 hash를 제외한 모든 필드가 10월 8일 receipt와 같다. 이후 root selection 교체가 PR7925의 immutable observation을 바꾼 증거는 없다.

Report gate는 초기 head validation에서 `full / comparison_scope:none`, baseline 검증 후 `full / validated_cases_only`다. 이 gate는 보고 가능한 범위를 정하며 인과성을 증명하지 않는다. 각 suite는 complete이고 binary 수집은 요청하지 않아 소비 binary budget은 0이다. Binary/core가 없어 stack을 확정할 수 있는 근거도 없다.

TC SHA가 양쪽 각각 같아 위 실패의 SQL·answers·fixtures·C driver 및 관련 디렉터리 tree는 동일하다. CTP 전체 tracked 차이는 `CTP/common/script/util_compat_test.sh`의 CCI compatibility 라이브러리/헤더 배치다. 읽은 대상 case에는 해당 compatibility 설정 호출이 없고 `init.sh`, `shell_utils.sh`, `shell_ci.conf`도 byte-identical이다. 이것은 관련 tracked helper 차이를 좁힐 뿐, 외부 runtime·실행 상태 전체의 동등성을 주장하지 않는다. Medium은 앞서 적은 이유로 인과 비교를 유보하고, shell은 작은 deterministic partition 입력 및 실제 공유 실패 조건 수준에서만 비교한다.

## 통합 전 조치와 담당

| 우선순위 | 조치 / 담당 | 완료 판단에 필요한 증거 |
| --- | --- | --- |
| 1 | PR7925/PR7927 담당: 검토된 공개 `0d9f5b448`·비공개 `10f350029` 수정의 실제 TC 포함 방식 확정 | PR7927 TC가 target에 통합되는 경로 또는 적절한 TC PR head에 반영된 exact commit; 중복 이식 금지 |
| 1 | PR7925 작성자: PR7927의 실제 통합 결과·후속 변경에 workspace 적응 | 새 엔진 head의 소스 비교·focused checks·shared partition acceptance. 현재 b755 분석만으로 완료하지 않음 |
| 1 | TC/PR 담당: medium 전체 선행 workload와 partition 강화 oracle 재검증 | 실제 통합 엔진 + 선택 TC의 provenance·case artifact; 세 medium 값/ASC/DESC 보존과 partition 거절·rollback·routing·후속 load 성공 |
| 2 | QA/service 담당: S2 별도 진단 및 CI 처리 | base/head service/server 로그·exit·PID에 기반한 원인/수리 또는 명시적 처리 결정 |
| 2 | CDC/OOS-history 담당·통합 담당: S3/S4의 유보 범위와 CI 판정 유지 | 활성 실패와 ADR-0005 후속 작업을 연결하고 다른 regression과 구별; 추출 오류를 기대 성공으로 바꾸지 않음 |
| 2 | 사람: PR7925의 공개 TC [#3679](https://github.com/CUBRID/cubrid-testcases/pull/3679)·비공개 TC [#4360](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4360) 처리 | 2026-10-15 20:56 KST 둘 다 OPEN. 필요한 변경은 해당 head에서 검토 후 사람이 merge, 변경 불필요 시 사람이 close. TC Merge Gate 정책상 둘 다 처리 전 병합 blocker |
| 3 | PR 작성자·통합 담당: source/TC 준비 후 별도 CI workflow 실행 | 새 head의 full suite 결과와 남은 blocker, run URL. 이번 세션은 trigger 권한을 사용하지 않음 |

현재 공개/비공개 TC PR head는 각각 `002bf2993b36032d45db1b7474406f4046cf060d`, `2107db997be84691d4233bb881b00a7dd1fb1f9f` 이다. 분석에 사용한 과거 CI TC SHA 및 그대로 보존한 로컬 `tc-pr-7925` checkout과 다르다. 새 head에 수정이 포함되었는지는 이 보고서의 판정 대상이 아니다. 과거 TC PR #3556/#4222는 CLOSED이며 현재 OPEN 두 PR과 구분해야 한다. 관찰한 check rollup에는 `TC Merge Gate` 이름의 결과가 없었으므로 check PASS를 추정하지 않았다. 위 blocker는 현재 OPEN 상태와 사용자 workflow 정책에 근거한다.

Work Item386은 실패별 평가·검증·보고서/index·로컬 task commit을 마치면 완료할 수 있다. **371의 실제 병합 완료, 기존 267/292, 다른 세션의 383/372 완료와는 별개**다. 문서의 `main` 통합에는 사용자 지침의 별도 로컬 병합 승인이 남고, 원격 publication은 별도 작업이다.

## 증거 위치와 재검증

Collector는 수집 당시와 이번 검증 모두 `cubrid-ci 0.2.0 (16d7252122d1, release)` 이다. `cubrid-ci doctor --json`은 healthy다. 기본 `python3`에는 jsonschema가 없어 처음 검증이 실행되지 않았고, 설치된 `uv`의 jsonschema 환경으로 재실행하여 통과했다. 이 도구 의존성 문제를 CI/collection 실패로 분류하지 않았다.

- 원래 [head receipt](/home/vimkim/tmp/pr7925-ci-b755678cd.4zpT1X/result-validation.json), [base receipt](/home/vimkim/tmp/pr7925-ci-b755678cd.4zpT1X/base-result-validation.json), [terminal summary](/home/vimkim/tmp/pr7925-ci-b755678cd.4zpT1X/terminal-summary.json), [선택한 base manifest](/home/vimkim/tmp/pr7925-ci-b755678cd.4zpT1X/base-result-manifest.json).
- 이번 [head validation](/mnt/nvme/data-5/tmp/pr7925-analysis-20261015.8oI2Cd/result-validation.json), [base validation](/mnt/nvme/data-5/tmp/pr7925-analysis-20261015.8oI2Cd/base-result-validation.json), [static audit](/mnt/nvme/data-5/tmp/pr7925-analysis-20261015.8oI2Cd/static-audit.json), [case comparison](/mnt/nvme/data-5/tmp/pr7925-analysis-20261015.8oI2Cd/case-comparison.json), [보존 확인](/mnt/nvme/data-5/tmp/pr7925-analysis-20261015.8oI2Cd/preservation-after.json).
- Head root `H`: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846`.
- Base root `B`: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0`.
- Head observation: `H/observations/20261008T090707.614914501Z-2599668-0/{request,result}.json`.
- Base observation: `B/observations/20261008T081240.683427628Z-2606534-0/{request,result}.json`.
- 각 suite directory는 head `H/providers/github-actions/runs/37747856853/attempts/1/<suite>`, base `B/providers/github-actions/runs/36570256001/attempts/1/<suite>` 이다. Base의 S2–S4는 head와 같은 stable_id를 사용하며 base-only stable_id는 `shell_06_issues_17_1h_cbrd_20759_hide_cubrid_replay_cases_hide_cubrid_replay_sh-28fe0a99ca`, `shell_40_guava_cbrd_26349_cases_cbrd_26349_sh-40d6a70f14`다. 그 아래 `summary.json`, `raw/index.json`, `raw/shards/<idx>/{build.read,tc.read,*.xml}`가 verdict·identity의 원본이다. `raw/github/collect.log`에는 CTP SHA가, medium `raw/shards/00/summary_info`에는 집계·case 결과가 있다.

| 현재 실패 증거 | 메타데이터·메시지·diff 위치 |
| --- | --- |
| to_char_order_by.sql / shard 00 | [metadata](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_medium/failures/medium_02_xtests_cases_to_char_order_by_sql-81a7176eb9/metadata.json), [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_medium/failures/medium_02_xtests_cases_to_char_order_by_sql-81a7176eb9/message.txt), [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_medium/failures/medium_02_xtests_cases_to_char_order_by_sql-81a7176eb9/diff.txt) |
| to_number_order_by.sql / shard 00 | [metadata](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_medium/failures/medium_02_xtests_cases_to_number_order_by_sql-2914e2cc1a/metadata.json), [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_medium/failures/medium_02_xtests_cases_to_number_order_by_sql-2914e2cc1a/message.txt), [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_medium/failures/medium_02_xtests_cases_to_number_order_by_sql-2914e2cc1a/diff.txt) |
| to_timestamp_order_by.sql / shard 00 | [metadata](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_medium/failures/medium_02_xtests_cases_to_timestamp_order_by_sql-f88d9035bb/metadata.json), [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_medium/failures/medium_02_xtests_cases_to_timestamp_order_by_sql-f88d9035bb/message.txt), [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_medium/failures/medium_02_xtests_cases_to_timestamp_order_by_sql-f88d9035bb/diff.txt) |
| partition_tbls.sh / shard 02 | [metadata](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_35_cherry_issue_21654_server_side_loaddb_partition_tbls_cases_partition_tb-9e01a2a475/metadata.json), [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_35_cherry_issue_21654_server_side_loaddb_partition_tbls_cases_partition_tb-9e01a2a475/message.txt), [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_35_cherry_issue_21654_server_side_loaddb_partition_tbls_cases_partition_tb-9e01a2a475/diff.txt) |
| bug_bts_15156.sh / shard 36 | [metadata](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_06_issues_15_1h_bug_bts_15156_cases_bug_bts_15156_sh-c83c869cd0/metadata.json), [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_06_issues_15_1h_bug_bts_15156_cases_bug_bts_15156_sh-c83c869cd0/message.txt), [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_06_issues_15_1h_bug_bts_15156_cases_bug_bts_15156_sh-c83c869cd0/diff.txt) |
| cbrd_27064.sh / shard 44 | [metadata](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/metadata.json), [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt), [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/diff.txt) |
| cbrd_27075.sh / shard 46 | [metadata](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/metadata.json), [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/message.txt), [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/b755678cd9a3ab465215228d5664f7f1edf24846/providers/github-actions/runs/37747856853/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/diff.txt) |

이번 검증은 schema/identity·count·raw digest 대조, exact Git object 읽기, 여섯 mismatch의 값 대조, 수정 SQL/답안의 byte 보존 검사, JUnit 양성 coverage 대조, 링크/index/diff 검사다. Raw bundle·다운로드·중간 JSON·검증 script는 docs Git history에 넣지 않는다. 보고서와 ticket README만 curated task 변경이다.

소스 checkout은 `CBRD-27424-oos-loaddb-sa`의 b755이고 기존 `cubrid-cci/win/cci_version.h` 변경을 보존한다. 소스·CCI와 읽은 공개/비공개 develop·tc-pr-7925 checkout의 HEAD·staged/unstaged diff·index 항목을 전후 대조하여 동일함을 확인했다. 문서는 별도 `/home/vimkim/gh/my-cubrid-docs-pr7925-current-ci`, `docs/pr7925-current-ci`에서 작성하고 merge destination은 docs `main` 이다. 다른 세션의 CDC untracked 문서/디렉터리와 PR8128 docs worktree는 건드리지 않는다.

OOS environment 검사에는 preset/build 디렉터리 부재와 broken compile_commands symlink가 보고되었다. 따라서 local build·LSP·DB 검증 완료를 주장하지 않는다. 필요 시 `just build` 후 `ln -sf build_preset_${PRESET_MODE}/compile_commands.json .`로 개발환경을 복구해야 하지만, Git object/retained CI 분석은 그 도구에 의존하지 않아 범위 내에서 계속했다.
