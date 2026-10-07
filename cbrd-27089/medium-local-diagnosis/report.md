# PR7927 medium 로컬 진단 — f3144ab / fb567a6

2026-10-07 KST. 대상: [CUBRID/cubrid#7927](https://github.com/CUBRID/cubrid/pull/7927), work-tracker **242**.

CI의 세 medium 실패를 native testkit으로 로컬에서 반복 재현했다. **전체 `_02_xtests` 444개만 실행하면 양쪽 모두 PASS지만, CI와 같이 `_01_fixed` 114개를 먼저 실행하면 head는 555 PASS / 3 FAIL, base는 558 PASS다.** 이전 로컬 PASS와 CI FAIL의 차이는 선행 workload를 보존하지 않았던 데서 설명된다.

세 실패는 변환값과 명시적 정렬 결과의 차이가 아니라 **재사용 힙에 행이 배치된 페이지·슬롯의 차이**로 관찰된다. 대상 테스트 직전에 힙 재사용을 끄면 두 리비전 모두 새 페이지의 슬롯 1..5와 입력 순서를 보인다. 이 반례는 재사용 힙의 이력이 현재 증상에 필요하다는 근거다. **어떤 PR 변경이 선행 workload 동안 그 이력을 갈라놓는지는 아직 확정하지 않았다.** 답안·엔진 코드는 수정하지 않았다.

## 고정 입력과 실행 계약

| 구분 | 고정값 |
| --- | --- |
| head | `f3144ab4b72fc2bf73f115c9da1cf193c756457a`, `vimkim/cubrid:feat/oos-deferred-write` |
| base | `fb567a629cdb390fff920542173fa36f454c74a0`, `CUBRID/cubrid:feature/oos-merge` |
| public testcase | `f5e610d91efdeaa9fcf089f47bf4a89c103a4a93`, `tc/pr-7927`, clean |
| medium archive SHA-256 | `63833b7abf965621539bc4216aeb5fc3527c173c7a4d91436bd113a2f4269a06` |
| native testkit SHA-256 | `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, `cubrid-testkit dev` |
| CTP assets | native `9c62858b10005d721546cc007be260844033b9e9`; 기존 사용자 변경 보존 |
| JDBC | 양쪽 disposable install에 같은 `cubrid-jdbc-11.4.0.0081.jar`; SHA-256 `2ecb2fbd0432b825e95c878d8ae9a956ba9a592a8f596145e1df4b9afdd38b9b` |
| JDK | Temurin 8.0.462+8 |
| native 계약 | `medium_dev.conf`, `parallel_slots=1`, `create_table_reuseoid=no`, `TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1` |
| 소유 자원 | 매 attempt마다 새 install/CTP/HOME/registry/TMP, 같은 archive와 testcase copy; namespace containment |

입력 사전 manifest는 [input-manifest.json](evidence/input-manifest.json), 실제 각 실행의 script/config/driver/locale/hash 및 command는 [attempts.json](evidence/attempts.json)에 있다. [environment.json](evidence/environment.json)은 실제 바이너리, Debug CMake 옵션, 컴파일러 경로와 실행 중 캡처한 설정의 해시를 보존한다. 양쪽 unit-test 옵션은 같다. head의 직접 GCC 호출과 base의 ccache wrapper 경로는 기록되어 있으며, 완전히 동일한 빌드 파이프라인을 새로 구성했다고 주장하지 않는다.

초기 head install에는 JDBC 디렉터리가 없었다. `head-native-01`은 `CUBRIDOID` class-load 실패와 CQT 초기화 예외로 testcase verdict를 만들지 못했다. 이후에는 복사된 disposable install에만 동일 JDBC를 공급했다. CQT의 `MyDriverManager`는 install의 JDBC를 별도 classloader로 로드하므로 CTP/lib의 다른 JDBC JAR를 동일 드라이버의 증거로 사용하지 않았다.

초기 실행은 locale을 각각 생성했다. 이후 재현과 대조 실행은 동일한 cached `libcubrid_all_locales.so` 바이트를 사용했다(SHA-256 `5608c54f4a2ebc97d7862de933140e591564550d9aacd43a922feb8e5cb591e4`). 이 통제 뒤에도 전체 558개의 차이가 유지되었다.

실행 중 캡처한 `cubrid.conf`, broker, HA 설정은 두 쪽에서 바이트까지 같았다. [runtime-cubrid.conf](evidence/runtime-cubrid.conf), [runtime-cubrid_broker.conf](evidence/runtime-cubrid_broker.conf), [runtime-cubrid_ha.conf](evidence/runtime-cubrid_ha.conf)를 참고한다. native cleanup 뒤 install/conf는 복원되므로 종료 후 파일을 실행 당시 설정으로 간주하지 않았다.

## 완전 디렉터리 결과와 CI 입력 차이

| workload / attempt | head | base | 해석 |
| --- | --- | --- | --- |
| 전체 `_02_xtests` 444개 (`head-native-02`, `base-native-01`) | 444 PASS | 444 PASS | 기존 로컬 관찰 재확인 |
| 전체 `_01_fixed` + 전체 `_02_xtests` 558개 (`*-predecessors-01`) | 555 PASS / 3 FAIL | 558 PASS | CI의 세 raw diff와 같은 순서 |
| 동일 558개, 동일 cached locale (`*-predecessors-02`) | 555 PASS / 3 FAIL | 558 PASS | fresh DB에서 반복 재현 |

Runner exit는 정상 실행에서 양쪽 모두 0이었다. 이것을 PASS로 사용하지 않았다. 원래 focused verifier는 head의 fail count 3을 보고 exit 1, base에서 exit 0을 반환했다. 이 verifier는 NOK를 먼저 거부하므로, 별도 [retain_evidence.py](retain_evidence.py)가 **기대 목록 = summary 순서 = 실제 실행 순서**, 1..N 실행 번호, 전체 result 존재, main/summary/JUnit count, native 종료 표식을 함께 검증한다. 이 보완 검사는 실패한 testcase를 성공으로 바꾸지 않는다. 모든 순서와 SQL/result 해시는 [ordered-verdicts.tsv](evidence/ordered-verdicts.tsv)에 있다.

기존 head/base CI job 로그에서 추출한 [실제 975개 실행 순서](evidence/ci-executed-order.txt)는 서로 같았다. 세 대상은 CI의 506, 511, 516번째이고, `_02_xtests` 단독 실행에서는 392, 397, 402번째다. 차이는 앞의 `_01_fixed` 114개다. 이번 로컬 검증은 관련 prefix를 포함한 **558개**이며 CI 전체 975개를 새로 실행한 결과가 아니다.

[asset-comparison.json](evidence/asset-comparison.json)은 historical CTP 두 revision을 읽기 전용으로 비교한다. head CI `44e3f97c788ad82091d5b66d728852f3279b1e86`와 base CI `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb`의 tracked 차이는 shell `util_compat_test.sh`뿐이다. 관련 medium config, SQL runner/config와 CQT JAR는 같고, native CQT는 ZIP metadata가 달라도 **모든 압축 해제 entry의 해시가 같다**. 역사적 CTP checkout을 바꾸거나 legacy CTP를 실행하지 않았다. CI Rocky 8.10과 로컬 Rocky 9.6의 환경 차이 전체가 해소된 것은 아니지만, native에서 정확한 증상을 확보했다.

## 세 raw 결과

| 대상 / unordered block | base 원래 답안과 로컬 558 결과 | head 로컬 558 결과 |
| --- | --- | --- |
| `to_char_order_by`: 숫자 | `3,5,1,2,4` | `4,1,2,3,5` |
| `to_char_order_by`: DATE/TIME/TIMESTAMP | 대응값 순서 `3,5,1,2,4` | 대응값 순서 `4,1,2,3,5` |
| `to_number_order_by` | `3,5,1,2,4` | `4,1,2,3,5` |
| `to_timestamp_order_by`: 날짜의 일(day) | `2,5,1,3,4` | `3,5,1,2,4` |

Raw 출력은 정렬하거나 덮어쓰지 않았다. 전체 문자열/공백을 포함한 [head to_char](evidence/head-predecessors-02-to_char_order_by.txt), [base to_char](evidence/base-predecessors-02-to_char_order_by.txt), [head to_number](evidence/head-predecessors-02-to_number_order_by.txt), [base to_number](evidence/base-predecessors-02-to_number_order_by.txt), [head to_timestamp](evidence/head-predecessors-02-to_timestamp_order_by.txt), [base to_timestamp](evidence/base-predecessors-02-to_timestamp_order_by.txt)를 비교할 수 있다. 모든 그룹의 값 multiset, `ORDER BY 1`, `ORDER BY 1 DESC`는 원래 답안과 일치했다.

## 관찰과 반례

### 스캔과 physical OID

`*-observe-02`는 원래 unordered SELECT가 끝난 다음 `select foo, f as probe_value from foo`를 추가했다. CQT 복사본의 `ConsoleDAO.class`에서 동일 길이 UTF-8 method constant `getTableName`을 `getOidString`으로 바꾸어 class 이름 대신 JDBC physical OID를 출력했다. 선행 SQL과 원래 SELECT 결과의 signature가 그대로 유지되는 것을 classifier로 검증했다. 변경은 attempt-local JAR/SQL copy뿐이다. JAR의 object rendering 변경은 prefix의 다른 object 결과에도 적용되므로 관찰 실행의 전체 NOK count를 원래 regression count로 사용하지 않는다. driver의 object-name 조회 경로도 달라질 수 있어 계측이 모든 실행 상태에 무영향이라고 주장하지 않는다. 이 관찰 query의 계획은 양쪽 모두 `sscan`이다.

OID의 `@page|slot|volume` 값과 값의 대응은 다음과 같다. 표는 **실제 출력 순서**다.

| to_number (to_char에서도 같은 배치) | base | head |
| --- | --- | --- |
| 1번째 출력 | 값 3, `@21515\|64\|0` | 값 4, `@21643\|65\|0` |
| 2번째 출력 | 값 5, `@21515\|65\|0` | 값 1, `@21644\|50\|0` |
| 3번째 출력 | 값 1, `@21516\|52\|0` | 값 2, `@21644\|51\|0` |
| 4번째 출력 | 값 2, `@21516\|53\|0` | 값 3, `@21644\|52\|0` |
| 5번째 출력 | 값 4, `@21516\|54\|0` | 값 5, `@21644\|53\|0` |

timestamp에서는 base의 day 2/5가 첫 페이지 슬롯 64/65, day 1/3/4가 다음 페이지 슬롯 52/53/54다. head의 day 3/5는 첫 페이지 슬롯 65/66, day 1/2/4는 다음 페이지 슬롯 50/51/52다. 이 대응이 raw 변환값 순서를 설명한다. 실제 삽입 호출 순서까지 OID 출력만으로 추론하지는 않는다.

원래 변환 SELECT의 계획도 `--@queryplan`으로 별도 캡처했다. 전체 558 prefix를 보존한 `head-plans-full`은 기존 head signature, `base-plans-full`은 원래 답안 순서를 유지했다. 네 to_char 그룹과 to_number/to_timestamp의 원래 unordered SELECT 계획/statement는 양쪽에서 바이트까지 같고 모두 `sscan`이다. 관찰 SELECT의 계획과 원래 변환 SELECT의 계획을 혼동하지 않는다. 원문 계획과 비교 판정은 [plan-comparison.json](evidence/plan-comparison.json)에 보존한다.

### 세 가설과 재사용 통제

실험 전에 다음 예측을 순서대로 제시했다.

1. 재사용 힙의 빈 공간·슬롯 이력이 필요하다면, 대상 직전에 `dont_reuse_heap_file=yes`를 설정했을 때 리비전 간 배치 차이가 사라진다.
2. 클라이언트의 삽입/flush 순서 자체가 다르다면, 새 힙에서도 값과 OID의 대응 순서가 달라진다.
3. 대상 레코드 크기·주소 예약량이 다르다면, 같은 삽입 순서에서도 heap boundary의 길이/페이지 선택이 달라진다.

`*-fresh-heaps`는 같은 전체 558 prefix와 관찰을 유지하고 **대상 파일 맨 앞에만** heap-reuse parameter를 추가했다. 두 리비전 모두 모든 unordered 그룹이 `1,2,3,4,5`이고 to_number는 한 페이지의 슬롯 1..5다(head `@21953`, base `@21825`). 값 multiset과 명시적 정렬은 그대로다. 이는 첫 예측을 지지하고 두 번째 예측의 “새 힙에서도 차이가 남는다” 부분을 반박한다. **원래 답안 기준으로 PASS가 되었다는 뜻은 아니다.** 양쪽 모두 원래 순서와 다르며 답안은 그대로 보존했다. 이 parameter 변경은 진단용이고 제안한 수정이 아니다.

성공한 `head-hp3` / `base-hp3`의 GDB 관찰은 경계를 더 좁힌다. 실제 재사용 HFID는 head `(hpgid=21633,fileid=21632,volid=0)`, base `(21505,21504,0)`다. 두 리비전에서 to_number 값 1..5가 **같은 순서로** `heap_insert_logical` → `heap_insert_physical`에 들어갔다. 입력/저장 길이는 전부 **24바이트**, 실제 저장 record bytes도 행별로 완전히 같았다. to_timestamp 역시 입력 순서, **40바이트** 길이와 record bytes가 같았다. 각 행의 `res_oid`만 앞의 관찰 표와 같이 달랐다. [target-insert-observations.json](evidence/target-insert-observations.json)은 해당 physical 기록과 대응하는 logical 진입 기록, 전체 trace에서의 위치를 보존한다.

따라서 이 두 대상에서 삽입 호출 순서와 대상 row 크기/직렬화 bytes의 차이는 관찰된 배치 차이의 설명이 되지 않는다. 주소 예약·bestspace 후보/free-space 자체는 이 probe에서 계측하지 않았다. 전체 workload 앞부분의 record 크기/파일 생명주기 차이까지 배제한 것은 아니다.

소스에서 이 실험의 경계는 명시적이다. 고정 head의 [heap_create_internal](https://github.com/CUBRID/cubrid/blob/f3144ab4b72fc2bf73f115c9da1cf193c756457a/src/storage/heap_file.c#L4870)은 `dont_reuse_heap_file=false`와 non-reuse-OID heap에서 `file_tracker_reuse_heap` / `heap_reuse`를 시도한다. [heap_reuse](https://github.com/CUBRID/cubrid/blob/f3144ab4b72fc2bf73f115c9da1cf193c756457a/src/storage/heap_file.c#L5232)는 일반 heap의 슬롯을 제거하지 않는 이유를 설명하며, 페이지별 free-space로 후보를 다시 구성한다. [heap_find_bestpage](https://github.com/CUBRID/cubrid/blob/f3144ab4b72fc2bf73f115c9da1cf193c756457a/src/storage/heap_file.c#L4735)는 삽입 길이와 bestspace를 사용한다. 이 코드 읽기는 실험의 효과를 설명하며, 특정 PR 변경의 책임을 증명하지 않는다.

### 축소 입력이 보여 준 한계

전체 baseline 확보 뒤에만 copied workload를 줄였다. head에서는 fixed 앞 57/28/14/7/5/3개와 전체 `_02_xtests`를 남겨도 동일 증상이 나고, 앞 1/2개 또는 `3219.sql`만 선행하면 원래 답안과 같다. `3277.sql` 한 개 + 전체 444개도 head에서 442 PASS / 3 FAIL다. 이 파일은 `foo`에 네 행을 삽입하고 view를 만든 뒤 DROP/COMMIT한다.

하지만 **base에서도 `3277.sql` 단독 선행은 같은 세 실패를 만든다.** base의 fixed 앞 14/28/57개 대조도 같은 CI signature다. 따라서 이를 최소 head/base differential이라고 부를 수 없다. 이는 head의 출력 순서가 base에서도 다른 이력 아래 생길 수 있다는 통제 반례다. 전체 114개에서 base가 원래 답안으로 돌아오는 전이는 57개 뒤의 상태 변화 또는 조합을 더 조사해야 한다. fixed 전체를 보존하고 세 target만 실행한 117개 축소는 raw `1,2,3,4,5`로 바뀌어 CI 증상을 잃었다. `_02_xtests`의 선행 상태도 필요하며 그 부분은 아직 최소화되지 않았다. 모든 축소 목록은 각 attempt identity와 verdict TSV에 보존되어 있다.

## 피드백 명령

아래는 실제로 실행하여 head `CI_SIGNATURE` / exit 1을 얻은 명령이다. original conversion plan을 캡처하면서도 raw 값의 원래 순서를 판정한다. 재실행할 때는 이미 있는 `head-plans-full` 대신 아직 없는 새 attempt 경로를 사용한다. cached locale은 검증된 기존 자원이며 양쪽에 같은 파일을 준다.

```bash
python3 /home/vimkim/gh/my-cubrid-docs-pr7927-medium-local-diagnosis/cbrd-27089/medium-local-diagnosis/differential_loop.py head /home/vimkim/tmp/pr7927-medium-diagnosis-20261007/head-plans-full --locale-library /home/vimkim/tmp/pr7927-medium-diagnosis-20261007/head-predecessors-01/cubrid/lib/libcubrid_all_locales.so --conversion-plans
```

대응 실행 `base-plans-full`은 oracle `ANSWER_EQUAL` / exit 0이었다. exit **1 = 정확한 세 CI 순서 + 값 multiset/ASC/DESC 보존**, **0 = 원래 답안**, **2 = 다른 순서 또는 setup 불충분**이다. plan 출력이 답안에 없는 문자열을 추가하므로 이 두 diagnostic run의 native verifier는 양쪽 모두 exit 1이다. 이를 testcase PASS verdict로 대신 사용하지 않는다. 실제 실행한 command/result는 attempt receipt에 있다. 재현율은 unmodified 전체 558에서 head **2/2**, base **2/2**이며 locale까지 맞춘 반복에서도 동일하다. 실행은 분 단위로, 아직 seconds 수준의 최소 differential loop는 아니다.

## 남은 인과 경계와 다음 실험

확정한 것은 (1) native/CI gap의 missing prefix, (2) 같은 입력에서의 반복 differential, (3) 값을 잃지 않는 physical placement 차이, (4) reusable heap history의 필요성이다. **최초로 어느 파일/페이지/free-space 이력이 달라지는지, 그 차이가 fixture load·선행 SQL·OOS finalization·주소 예약 중 어디서 발생하는지는 미확정**이다. 단순히 “ORDER BY가 없으므로 답안을 바꾸자”로 닫지 않는다.

GDB attempt의 command, exact probe SHA, 원문 로그와 판정은 [heap-boundary.json](evidence/heap-boundary.json)과 [attempts.json](evidence/attempts.json)에 있다. 초기 시도는 잘못된 header 필터 및 namespace target 파일의 symbol 로드 실패 때문에 삽입 기록을 얻지 못했다. broker 연결 단계에서 실패한 두 실행도 별도로 남겼다. 이 시도들을 정상 삽입 추적으로 사용하지 않았다. 이후 로컬 executable/sysroot와 데이터 페이지 필터를 명시한 `*-hp3`에서는 head 3,408 / base 3,413개의 tagged 기록을 얻었고 원래 selected order signature도 유지되었다. trace는 350번째 testcase 뒤부터 대상 두 데이터 페이지와 그 재사용 힙을 관찰한 것이며 전체 workload의 모든 insert를 기록한 자료는 아니다. PID namespace 경고가 있어도 실제 target row bytes/OID 대응이 별도 query 관찰과 일치함을 확인했다. 빈 trace나 debugger thread 목록을 엔진 동작의 음성 증거로 사용하지 않는다.

다음 falsifier는 **전체 558을 유지한 head/base에서 발견된 HFID의 페이지별 슬롯 수/free space와 bestspace 후보/선택 VPID를 target 생성 이전부터 짝지어 기록하는 것**이다. `heap_reuse` 완료와 `heap_find_bestpage` 진입/반환에 probe를 두고 요청 길이, `is_newrec`, 후보의 free-space 및 최종 VPID를 비교한다. target에 들어오기 전에 구조가 이미 다르면 앞선 file lifecycle/fixture load로 경계를 옮긴다. 구조와 요청 길이까지 같고 선택 VPID만 달라지면 bestspace cache/후보 선택을 검증한다. 또는 양쪽을 함께 실행하며 fixed prefix 57..114의 분기점을 찾되, 순서/allocator 상태가 단조롭다고 가정하지 않는다. 진단 patch가 필요하면 별도 exact-source topic worktree/build에만 적용하고 기존 순서 signature가 유지되는지 먼저 확인한다.

## 보존과 상태

전체 disposable evidence root: `/home/vimkim/tmp/pr7927-medium-diagnosis-20261007`. 초기 JDBC/preflight 실패, broker 연결 실패와 debugger 실패도 retained attempt로 남겼다. 별도의 `head-numeric-01..03`은 새 DB의 탐색 실험이며 native medium 시작 상태와 다르고, Java object identity 문자열은 physical OID 증거가 아니므로 인과 판단에 사용하지 않았다. 해당 원본 script는 root의 `exploratory-source`에 보존했다.

원래 엔진 worktree `/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write`의 기존 `cubrid-cci`/`cubrid-jdbc` 변경을 보존했다. exact head/base source와 public testcase도 수정하지 않았다. CTP/testkit 업데이트, production fix, 답안 변경, push, CI trigger, remote comment 또는 engine integration을 수행하지 않았다. 43개의 native attempt 중 38개의 완결 verdict(총 18,334개의 ordered case artifact)를 대조했으며 5개의 harness 불충분 실행을 별도로 구분했다. work-tracker **242는 active**로 유지한다. 본 문서 branch는 `docs/pr7927-medium-local-diagnosis`이며 로컬 review용 commit으로 보관한다.

검증은 모든 완결 attempt의 ordered membership/count/result 존재, 원래 plan 동등성, 두 target의 삽입 bytes/길이 대조, 58개 파일의 개별 index와 새 링크, 7개 Python source의 syntax를 포함한다. 작성한 문서/script의 staged whitespace check는 통과했다. 원본 출력과 실행 설정의 trailing whitespace/EOF blank는 바이트 보존을 위해 그대로 두었고 일반 whitespace check에서 해당 evidence snapshot을 제외했다. 소유한 native 실행 바이너리/process가 남지 않았음을 확인했다.
