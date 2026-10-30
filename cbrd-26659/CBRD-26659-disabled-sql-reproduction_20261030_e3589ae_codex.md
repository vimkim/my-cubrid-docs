# CBRD-26659 비활성 SQL TC 3개 재현과 실패 원인

작성일은 2026-10-30, 시간대는 Asia/Seoul이다. 개발·QA 담당자가 과거 실패로 비활성화한 SQL TC 3개의 현재 실패 원인과 다음 수정 범위를 판단하도록 작성했다. 관련 항목은 [TODO checklist](CBRD-26659-todo-checklist_20261029_codex.md)의 SQL 재현 3건이다.

**원본 TC와 답안으로 실행한 결과는 0 PASS·3 NOK다. 세 TC 모두 답안에 남은 오류 번호 `-1384`와 현재 Engine의 `-1388` 차이로 실패했다. 차이는 총 4곳이며 나머지 출력은 바이트 단위로 같다.** 현재·과거 소스에서 같은 오류 상수의 번호 변경을 확인했다. 이 실행에서 별도의 SQL 엔진 결함이나 장시간 실행은 관측하지 않았다. 엔진 전체의 정확성이나 다른 비활성 TC의 원인은 이 결과로 판단할 수 없다.

답안 수정·재활성화·게시·CI 재실행은 수행하지 않았다. 원본 판정은 계속 NOK이며, 오류 번호를 치환한 오프라인 비교는 원인 분석 근거다.

## 실행 결과

모든 이름 앞에 `cbrd_26659_oos_`가 붙는다. TC 시간은 XML과 `main.info`가 일치하는 native 측정값이다. 명령 전체 시간에는 DB 준비, 서버·JDBC 시작, 정리가 포함된다. 성능 비교용 측정은 아니다.

| TC | 시도 | 원본 판정 | TC 시간 | 명령 전체 시간 | 답안에서 다른 행 | 분류 |
| --- | --- | --- | ---: | ---: | --- | --- |
| `record_boundaries` | `rb05` | 1 NOK | 0.093초 | 106.166초 | 18행, 1곳 | TC 답안의 오류 번호 불일치 |
| `sql05_bigone` | `b03` | 1 NOK | 0.122초 | 101.783초 | 28·42행, 2곳 | TC 답안의 오류 번호 불일치 |
| `sql09_lob_maxcols` | `l01` | 1 NOK | 1.079초 | 101.220초 | 12행, 1곳 | TC 답안의 오류 번호 불일치 |

각 시도에서 예상 TC, 완료 로그, XML의 실제 TC가 정확히 1개씩 일치한다. `main.info`와 `summary_info`도 각각 total 1·success 0·fail 1이다. 원본 `.result`가 존재하고 원본 답안과 불일치한다. 세 native 명령의 종료 코드는 모두 0이지만 focused 검증기는 fail 1을 확인하고 모두 1로 종료했다. 종료 코드 0을 PASS로 사용하지 않았다.

TC 시간과 명령 전체 시간이 모두 120초 미만이다. 다만 감시 스크립트의 `Testing ... [NOK]` 신호는 실행 완료 시 출력된다. 이를 시작 신호로 사용한 이번 스크립트는 **TC 시작부터 120초를 강제하는 기능을 검증하지 못했다.** `observation.json`의 `case_dispatch_observed`도 실제로는 이 완료 신호를 관측했다는 뜻이다. 이번 세 건의 완료·시간 판정은 결과 파일과 전체 경과 시간으로 확인한다. 향후 멈춘 TC의 2분 제한 분석에는 실제 시작 이전의 감시 기준이 필요하다.

## 실패 원인과 기대값의 근거

오류 번호는 [현재 Engine `e3589ae`의 `error_code.h` 1793행](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/base/error_code.h#L1793)에서 다음과 같다.

```c
#define ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE -1388
```

TC 주석이 기준으로 기록한 [과거 Engine `fb567a6`의 같은 상수](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/base/error_code.h#L1785)는 `-1384`다. 따라서 실제 출력만 보고 새 기대값을 정한 것이 아니다. 같은 이름의 오류 상수가 소스 리비전 변경으로 다른 번호를 가진다.

현재 소스의 [`heap_file.c` 14233행](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/heap_file.c#L14233)은 OOS를 포함한 인라인 레코드가 bigone 크기가 되면 이 상수를 설정하고 `S_ERROR`로 반환한다. 이 검사는 뒤의 OOS 값 기록 처리보다 앞에 있다. 아래 기대 오류들의 종류를 확인하는 소스 근거이며, 이번 실행에서 내부 함수를 계측했다는 뜻은 아니다.

| TC | 최초 불일치와 추가 확인 | 판단 |
| --- | --- | --- |
| `record_boundaries` | `r12_next` 경계 초과 INSERT가 `Error:-1388`을 반환한다. 원본 답안은 `-1384`다. 다른 경계·키 조회 출력은 모두 원본 답안과 같다. | 오류 종류와 거부 기대는 유지되며 번호만 오래됐다. |
| `sql05_bigone` | OOS와 큰 고정 길이 payload가 공존하는 INSERT·UPDATE의 오류 2개가 다르다. 일반 bigone, 허용되는 후속 연산, 실패 뒤 행 값의 출력은 모두 같다. | 실패 원인은 답안의 두 오류 번호다. |
| `sql09_lob_maxcols` | LOB locator 열이 조밀한 행의 INSERT 오류 1개가 다르다. 희소 행 복사·원본 삭제 뒤 값 확인·정리 출력은 모두 같다. | 실패 원인은 답안의 한 오류 번호다. |

각 원본 답안에서 리터럴 `Error:-1384`만 `Error:-1388`로 치환한 바이트열이 실제 `.result`와 정확히 같다. 공백·줄바꿈·행 수·다른 출력은 정규화하지 않았다. 원본 파일에는 치환을 적용하지 않았다.

| TC | 원본 답안 SHA-256 | 실제 `.result` SHA-256 |
| --- | --- | --- |
| `record_boundaries` | `4a0b10cb67833336e3c59794b94d97fddb7bf75d638bd7d549d80abcea0be961` | `1cbd9870939870d5788ff5550640be7ff44258bb352952679e451de496d23a78` |
| `sql05_bigone` | `4761267db422dbd2dbff4426b5504ff3504854c8b97deeb43a07d918a392fc4b` | `c47344577e009e5812cc806562ed6dccbdb8ccd9dee4934ec36c59659f06036f` |
| `sql09_lob_maxcols` | `00f4e228e5085a885bedc22209e961181f784c3e82e728c651eeaed5ec79c373` | `984d0af3a6d18b4c6c34176ff3852ce5ec8ea6bd4e85246b41926d6efdfb06ff` |

## 리비전과 실행 환경

| 대상 | 고정한 값과 변경 범위 |
| --- | --- |
| Engine | `CUBRID/cubrid`의 `e3589ae42d42b04eb020e1ae43e165b01d31b12a`. [PR #8128](https://github.com/CUBRID/cubrid/pull/8128), head `vimkim/cubrid:CBRD-26659-oos-testcases-handover`, base `feature/oos-merge`. |
| 설치 산출물 | 보존된 `11.5.0.2793-e3589ae`, Linux 64bit optdebug. `/home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID`를 시도별로 복사했다. |
| TC | `CUBRID/cubrid-testcases`의 `45e21ad799d82ebadc04a93c7d2f69517d53bf39`, `tc/pr-8128`, [PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688). |
| 원본 경로 | `disabled/failing/sql/_36_guava/cbrd_26659/cases/<TC>.sql.disabled`와 대응 `answers/<TC>.answer`. 복사본에서만 `.sql` 확장자를 복구했다. 두 파일의 바이트는 원본 커밋과 같다. |
| Native 실행기 | 설치된 `testkit`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. VCS `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, dirty 표시가 있어 소스 checkout과 바이너리의 완전한 대응은 인증하지 않는다. 업그레이드·교체하지 않았다. |
| CTP 자산 | `/home/vimkim/gh/ctp/run-sql/CTP`의 복사본. 부모 Git HEAD `9c62858b10005d721546cc007be260844033b9e9`, 기존 수정이 있는 자산이다. legacy CTP runner는 실행하지 않았다. |
| Java·SQL 방식 | Temurin `8.0.462+8`, JDBC, `parallel_slots=1`. 원래 SQL profile의 `ha_mode=yes`를 최종 세 시도에서 유지했다. |

원래 source checkout의 기존 `cubrid-cci`·`cubrid-jdbc` 수정은 보존했다. TC checkout은 실행 전후 clean이며 원본 답안·비활성 상태를 유지한다. 설치 원본과 세 실행 복사본의 `cub_master`, `cub_server`, `csql`, `cubrid`, `cubrid_rel`, `libcubrid.so.11.5`를 비교해 18개 파일의 hash 일치를 확인했다. 실행용 registry·HOME·TMP·설정·결과는 시도별 복사본 안에 둔다.

CQT jar SHA-256은 `926a1a6c3d73f91344a3e4a2446b51c7fe7329be5de413d90979ba8209052f0f`, JDBC jar는 `17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98`다. CTP 원본의 기존 수정은 `util_compat_test.sh`, `shell/init_path/cubrid`, `shell_config.xml`, `sql/bin/interactive.sh`, `run_memory.sh`와 미추적 JDBC jar 등을 포함한다. 따라서 이 결과는 자산 hash까지 기록한 이번 native 환경에 한정한다.

## TC 실행 전에 실패한 준비 시도

작업 자료의 공통 루트는 `/home/vimkim/temp/cbrd-26659-sql-disabled-20261030`이다. 아래 준비 실패는 실제 SQL TC의 NOK 3개에 합산하지 않는다. 결과를 얻기까지의 재시도는 모두 이 루트와 append-only `decisions.tsv`에 보존한다.

| 시도 | 관측 결과 | 분류와 후속 관측 |
| --- | --- | --- |
| `preflight-loaded-01` | 기존 설치가 `1ef86a7`이어서 source `e3589ae`와 불일치했다. | 실행 전 거부했다. 불일치 허용 옵션을 사용하지 않고 보존된 일치 산출물을 선택했다. |
| `record-boundaries-01` | 긴 경로에서 HA 서버 등록 대기 중 90초 준비 제한으로 중단했다. TC 완료 로그와 결과 루트가 없다. | 준비 실패다. TC 실패·120초 초과로 판정하지 않는다. |
| `record-boundaries-02` | HA를 끈 진단 시도도 같은 등록 단계에서 반복했고 240초 준비 제한으로 중단했다. | 단순한 HA 설정 문제라는 가정을 배제하는 관측이다. |
| `rb03` | 설치 경로를 줄인 뒤 서버 등록을 통과했지만 JDBC 연결에 실패했다. | 준비 스크립트의 HA-off 설정 writer가 key를 소문자로 바꾼 오류를 확인했다. 원래 대문자 key를 보존하도록 준비 스크립트를 고쳤다. |
| `rb04` | 짧은 경로와 원래 HA profile에서 서버·copylog·applylog가 시작됐지만 JDBC 연결은 실패했다. | 복사 환경에 `CUBRID_BROKER_CONF_FILE` 재지정을 빠뜨려 broker가 기존 호스트 설정을 읽었다. 복사본 설정을 가리키도록 준비 환경을 고쳤다. |
| `b01`, `b02` | 디렉터리만 준비했다. | 실행하지 않았으므로 결과 건수에 넣지 않는다. |
| `rb05`, `b03`, `l01` | 위 문제를 제거한 원래 HA profile로 TC를 각각 실행·완료했다. | 본문의 현재 NOK 3개다. |

긴 경로 문제의 소스 근거는 [`master_connector.cpp` 451행](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/connection/master_connector.cpp#L451)과 [`tcp.c` 893행](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/connection/tcp.c#L893)이다. 서버 등록은 TMP 경로에 `/cubrid_tcp_setup_server<PID>`를 붙인다. 긴 경로를 `sun_path`에 복사할 때는 잘라내지만 `bind` 길이는 원래 전체 경로로 계산한다.

같은 sockaddr 생성 방식을 쓴 Linux `bind` 대조 실험에서 pathname 108바이트·주소 길이 111바이트는 구조체 용량 110바이트를 초과해 errno 22로 실패했다. 짧은 경로의 주소 길이 66바이트는 성공했다. 실제 긴 시도의 syscall을 추적하지는 않았다. 따라서 이 원인은 소스·대조 실험·짧은 경로에서 등록 통과를 합친 근거로 판단하며, 해당 시도의 실패한 syscall을 직접 포착한 것은 아니다. 준비 환경의 별도 제약으로 기록하고 SQL 3개의 실패 원인과 구분한다.

## 명령과 결과 자료 재검증

시도별 `preflight.log`의 source/install 일치를 확인한 뒤 다음 native 명령을 직렬 실행했다. `CUBRID`, `CUBRID_CONF_FILE`, `CUBRID_BROKER_CONF_FILE`, `CUBRID_DATABASES`, `CUBRID_TMP`, `CTP_HOME`, `HOME`, `TMPDIR`, PATH·library path를 해당 시도 복사본으로 지정했다. 기존 `CUBRID_CUBRID_PORT_ID`, `CUBRID_RUNTIME_READY`, `CUBRID_BUILD_DIR` override는 제거했다. stdin은 `/dev/null`, stdout·stderr는 시도별 일반 파일 `run.log`로 연결했다.

```sh
TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 testkit sql -c <attempt>/conf/sql.conf
```

각 실행의 `Result Root Dir:`에서 얻은 실제 결과 루트는 다음과 같다. 경로 앞에는 위 작업 자료 공통 루트가 붙는다.

| 시도 | 결과 루트 |
| --- | --- |
| `rb05` | `rb05/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_301635375_11.5.0.2793-e3589ae` |
| `b03` | `b03/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_301637497_11.5.0.2793-e3589ae` |
| `l01` | `l01/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_3016423340_11.5.0.2793-e3589ae` |

각 디렉터리에는 `main.info`, `summary_info`, `linux_sql_64bit.xml`이 있다. 시도 루트에는 `identity.json`, `expected-cases.txt`, `observation.json`, `exit.status`, `verify.log`, 복사된 입력·답안과 실제 `.result`가 있다. 마지막 소유 프로세스 확인 자료 `owned-processes-after-all-runs.json`은 빈 목록이다.

[재검증 스크립트](tools/verify-disabled-sql-results.py)는 이 보고서의 판정 근거를 다시 대조하므로 Git에 보존한다. 원본 커밋의 입력·답안, 실행 복사본과 설치 원본의 hash, 정확히 1개씩의 실제 완료·NOK 자료, 네 오류 번호 차이를 읽어서 검증한다. 파일을 수정하거나 TC를 실행하지 않는다. 결과 자료와 준비 스크립트·원본 로그는 공통 루트에 보존하며 docs Git에는 넣지 않는다.

```sh
python3 cbrd-26659/tools/verify-disabled-sql-results.py \
  --artifacts /home/vimkim/temp/cbrd-26659-sql-disabled-20261030 \
  --testcases /home/vimkim/gh/cubrid-testcases/tc-pr-8128 \
  --engine /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover \
  --producer /home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID
```

관측 출력은 `diagnosis_verified=true`, `original_pass=0`, `original_nok=3`, `error_number_differences=4`다. 스크립트의 성공은 분석 근거가 일치한다는 뜻이다. TC PASS를 인증하지 않는다. `timeout_limit_enforcement_verified=false`를 명시해 감시 한계도 유지한다.

## 다음 작업과 남은 범위

다음 수정 후보는 원본 답안 3개에서 해당 오류 번호 총 4곳만 현재 오류 상수에 맞추는 것이다. 수정 후 실제 native 실행으로 PASS와 정리를 확인하고 정상 `.sql` 위치 복구를 검토해야 한다. 실제 PASS 확인 전에는 비활성 상태를 해제하지 않는다. 재실행 전에 TC 시작을 포함하는 120초 감시 기준을 먼저 검증한다.

이번 작업은 재현·원인 분석까지다. shell 61개, 기존 장시간 PASS 3개, HA 실패, TC PR 검토·병합은 남아 있다. 이전 [SQL 집계 차이](CBRD-26659-sql-count-discrepancy_20261030_run40837919358_codex.md)의 CTP 수리와 SQL 전체 자료 정합성 확인도 별도 미완료다. 이 focused 결과로 기존 SQL 수집 실패를 해제하거나 CBRD-26659 전체를 완료 처리하지 않는다.
