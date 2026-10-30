# CBRD-26659 SQL 3개 수정·재활성화 결과

작성일은 2026-10-30, 시간대는 Asia/Seoul이다. 개발·QA 담당자가 원인 분석을 마친 SQL 3개의 수정 범위, 실제 PASS 근거, 정규 실행 복원 상태를 확인하도록 작성했다. 이전 [원본 재현 보고서](CBRD-26659-disabled-sql-reproduction_20261030_e3589ae_codex.md)는 TC `45e21ad`의 원본 답안으로 관측한 3 NOK를 보존한다.

**답안 3개의 오류 번호 총 4곳을 수정한 뒤 실제 native 실행에서 3 PASS·0 FAIL·0 SKIP을 확인했다. 세 SQL 입력을 그대로 정규 경로에 복원했고, 현재 OOS SQL은 28쌍 활성·0쌍 비활성이다.** 기존 25쌍은 바이트와 mode가 같다. 이번 focused 검증에서 그 25개를 다시 실행하지는 않았다.

복원 뒤 한 번 실행한 CI는 별도 shell 1건 실패로 FAILURE다. 보존된 SQL shard 09 자료에서는 OOS 28개와 복원한 세 사례의 PASS가 관측된다. SQL 전체는 shard 01의 건수 불일치 때문에 수집기가 검증을 거부했다. **CI 전체 성공·SQL 전체 PASS·실패의 근본 원인을 확정하는 보고서는 아니다.**

감시 스크립트가 완료 로그부터 시간을 잰다는 이전 설명은 잘못됐다. 실행 중 부분 로그를 관측하고 실제 120초 중단을 시험해 기존 감시가 작동함을 확인했다. 감시 코드·엔진·설치된 testkit은 수정하지 않았다.

## 수정과 실제 실행 결과

Engine은 `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, 설치 산출물은 `11.5.0.2793-e3589ae`, Linux 64bit optdebug다. 현재 소스의 [`ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/base/error_code.h#L1793)는 `-1388`이다. 원본 답안의 `-1384`와 같은 이름의 오류이며, 크기 초과 거부라는 기대는 유지한다.

모든 TC 이름 앞에 `cbrd_26659_oos_`가 붙는다. 시간은 native XML과 `main.info`가 일치하는 TC 실행 시간이다. 성능 비교용 측정은 아니다.

| TC | 답안에서 바꾼 행 | 원본 판정 | 수정 후 판정 | 수정 후 TC 시간 | 실행 시도 |
| --- | --- | --- | --- | ---: | --- |
| `record_boundaries` | 18행 1곳 | NOK | PASS | 0.115초 | `r01` |
| `sql05_bigone` | 28·42행 2곳 | NOK | PASS | 0.117초 | `b01` |
| `sql09_lob_maxcols` | 12행 1곳 | NOK | PASS | 1.074초 | `l01` |

변경은 리터럴 `Error:-1384`를 `Error:-1388`로 바꾼 네 곳뿐이다. 나머지 답안의 공백·줄바꿈·값·행 수와 세 SQL 입력은 바이트 단위로 같다. 실제 `.result`는 수정 답안과 완전히 일치한다. 따라서 오류 기대를 없애거나 성공 출력으로 대체하지 않았다. 오류 거부 뒤의 행·값 유지와 나머지 원래 검사도 그대로 실행했다.

각 시도에서 예상 목록, 완료 로그, XML의 TC가 정확히 1개씩 같다. `main.info`·`summary_info`는 각각 total 1·success 1·fail 0이며, wrapper·native runner·focused 검증기의 종료 코드는 모두 0이다. 준비·정리를 포함한 명령 전체 시간은 각각 102.591초·102.117초·97.233초다.

원본 `rb05/run.log`의 결과 요약은 다음과 같다.

```text
Fail:1
Success:0
Total:1
```

수정 후 `r01/run.log`의 결과 요약은 다음과 같다. 다른 두 수정 후 실행도 같은 건수로 끝났다.

```text
Fail:0
Success:1
Total:1
```

## 커밋과 정규 실행 복원

| 단계 | Public TC 리비전 | 확인한 상태 |
| --- | --- | --- |
| 원본 | `45e21ad799d82ebadc04a93c7d2f69517d53bf39` | 정상 25쌍·비활성 3쌍, 원본 답안으로 3 NOK |
| 답안 수정 | `cb1ba77f0753e99f4a291a54eb0a3a23e1321297` | 비활성 상태에서 답안 네 오류 번호만 수정하고 세 native 실행의 입력으로 고정 |
| 검증 후 복원 | `b038c424b6a8d078671132e2369040493a5fc1f6` | 실제 3 PASS 뒤 정상 28쌍·비활성 0쌍으로 복원하고 PR head에 push |

대상은 [public TC PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688)의 `CUBRID/cubrid-testcases:tc/pr-8128`, base `feature/oos-merge`다. PR은 OPEN 상태이며 제목과 ready 상태는 바꾸지 않았다. Engine [PR #8128](https://github.com/CUBRID/cubrid/pull/8128)의 head `vimkim/cubrid:CBRD-26659-oos-testcases-handover`와 Engine 소스는 그대로다.

세 입력은 `disabled/failing/sql/_36_guava/cbrd_26659/cases/*.sql.disabled`에서 `sql/_36_guava/cbrd_26659/cases/*.sql`로 옮겼다. 대응 답안도 정규 `answers/`로 옮겼다. 정상 경로의 실제 바이트를 실행 복사본과 대조했다. 기존 정상 25쌍의 mode·blob도 원본 커밋과 같다.

`disabled/oos-pr8128.tsv`는 현재 비활성 항목이 없어 헤더만 남긴다. 기존 실패 목록은 [원본 커밋의 manifest](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/oos-pr8128.tsv)와 이전 재현 자료에 보존한다. 두 TC README의 실행 선택·현재 건수·복원 경로 링크도 갱신했다. 과거 CI 실패 기록을 지우지 않았다.

## 120초 감시의 직접 검증과 이전 설명 정정

이전 보고서는 완료된 로그의 `Testing ... [NOK]` 한 줄만 보고 감시 시작이 늦다고 판단했다. 실제 wrapper의 정규식은 `[NOK]`나 줄바꿈을 기다리지 않는다. 아래 제어 실행에서 최종 판정 없이 부분 `Testing` 로그가 먼저 보이고, wrapper가 이를 감시 시작으로 기록하는 것을 확인했다.

소스 설명은 testkit `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`의 `internal/result/sql.go:320`과 `internal/runner/sqlsuite/worker.go:60`에서 확인했다. 단일 slot에서는 `Starting`이 부분 진행 로그를 출력한 다음 SQL executor를 호출한다. 출력은 일반 파일로 직접 전달한다. 설치 바이너리는 dirty 표시가 있으므로 완전한 소스 대응을 인증하지 않는다. 아래 실시간 관측은 실제 설치 바이너리에서 수행했다.

| 제어 시도 | 입력과 실제 관측 | 판정 범위 |
| --- | --- | --- |
| `g01` | 읽기 전용 Cartesian 집계의 정수 SUM이 약 17.943초에 오류 `-458`로 넘쳤다. 실행 중 부분 로그가 보였지만 120초에는 도달하지 않았다. | 시작 신호 관측만 유효하다. 시간 제한·시간 초과 정리는 미검증이다. |
| `g02` | `NUMERIC(38,0)` 합계와 `db_class` 9개 alias를 사용했다. 30초·90초에도 최종 판정 없이 실행 중이었고 같은 `cub_server`의 CPU 누적치도 증가했다. | 부분 시작 신호 관측 후 120.046초에 감시가 작동했다. wrapper 124·native 255로 종료했다. |

`g02`의 종료 사유는 `testcase_timeout_120s`다. 감시 코드의 SHA-256은 `7e9851812e46478541ca05516614cc4f274f66b352b2760f9243f108434b937d`이며, 이전 wrapper를 변경하지 않고 사용했다. 준비 제한 240초와 TC 제한 120초를 구분했다. 제어 TC는 합성 진단 입력이며 원래 SQL 3개의 커버리지나 PASS 건수에 포함하지 않는다.

제어 종료 후 해당 설치 환경을 가진 프로세스와 실행 중 관측한 격리 namespace를 사용하는 프로세스는 모두 0개다. 세 실제 SQL 실행 뒤에도 해당 설치의 프로세스는 0개였다. `b01`·`l01`은 live namespace 식별자도 수집해 종료 뒤 holder가 없음을 확인했다. `r01`은 live 식별자 수집을 놓쳤으므로 native stop/delete 완료와 종료 후 프로세스 확인까지만 증거로 사용한다. 호스트 전체 IPC가 비었다고 주장하지 않는다.

## 실행 환경과 자료 재검증

실행은 기존 `cubrid-test-sql-run` 절차의 native JDBC family를 사용했다. 각 시도에 Engine·CTP·TC·HOME·registry·설정 복사본을 따로 만들었다. source/install 커밋은 일치하며 불일치 허용 옵션을 사용하지 않았다. 원래 HA=yes profile, `parallel_slots=1`, Temurin `8.0.462+8`을 유지했다.

```sh
TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 testkit sql -c <attempt>/conf/sql.conf
```

설치된 testkit SHA-256은 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`다. CTP 자산은 부모 HEAD `9c62858b10005d721546cc007be260844033b9e9`의 기존 수정이 있는 checkout을 복사했다. CQT·JDBC jar hash와 실행 복사본의 주요 Engine 실행 파일·라이브러리를 원본 산출물에 대조했다. 따라서 결과는 이 고정한 환경의 focused 검증이다. 일반 CI와 동일한 실행기라는 뜻은 아니다.

원본 실패 자료는 `/home/vimkim/temp/cbrd-26659-sql-disabled-20261030`에, 이번 실행 자료는 `/home/vimkim/temp/cbrd-26659-sql-restore-20261030`에 보존한다. 새 시도마다 `identity.json`, preflight, expected 목록, 설정, run 로그, 종료 코드, `observation.json`과 판정 파일이 있다. 결과 루트는 해당 실행의 `Result Root Dir:`에서 얻는다. 정상 복원 실행은 `r01`·`b01`·`l01`, 합성 감시 제어는 `g01`·`g02`다.

[복구 재검증 스크립트](tools/verify-sql-restoration.py)는 원본 3 NOK, 수정 후 3 PASS, 변경한 기대값 네 곳, 복원된 Git 객체와 기존 25쌍 보존, manifest, 실제 감시 제어 자료를 읽어서 대조한다. TC나 파일을 수정하지 않는다. 이 분석을 재검증하는 데 필요하므로 스크립트를 Git에 보존하고, 원본 로그·생성한 목록·runtime 복사본은 Git 밖에 둔다.

```sh
python3 cbrd-26659/tools/verify-sql-restoration.py \
  --artifacts /home/vimkim/temp/cbrd-26659-sql-restore-20261030 \
  --testcases /home/vimkim/gh/cubrid-testcases/tc-pr-8128 \
  --engine /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover \
  --reactivated-commit b038c424b6a8d078671132e2369040493a5fc1f6 \
  --producer /home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID
```

실제 출력은 `restored_sql3_pass=true`, `active_pair_count=28`, `disabled_count=0`, `four_expectation_changes=true`, `guard_real120verified=true`, `originalfailurespreserved=true`다.

기존 [원본 재현 스크립트](tools/verify-disabled-sql-results.py)는 복원 뒤 사라진 현재 작업트리의 비활성 경로를 읽어 실패했다. 현재 파일 경로에 의존하는 검사 한 줄을 제거하고, 원본 커밋의 Git 객체와 보존된 입력·답안·NOK 결과를 계속 검증하도록 했다. 수정 전의 `FileNotFoundError`와 수정 후의 정상 대조 결과도 작업 자료에 보존한다. 원본 3 NOK 판정은 바꾸지 않았다.

## CI와 완료 범위

두 testcase 저장소의 최신 `feature/oos-merge` 조상 검사는 PASS다. 기존 완료 CI는 이번 복원 전 TC를 사용했으므로, TC push 뒤 프로젝트 지침에 따라 `/run all`을 한 번 게시했다. [요청](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6519189513)에 대응하는 [CI 41031622190](https://github.com/CUBRID/cubrid/actions/runs/41031622190), attempt 1의 build debug·release와 SQL·shell·medium 다섯 context가 같은 새 실행을 가리킨다. Engine PR head는 `e3589ae`다.

CI는 2026-10-30에 FAILURE로 종료했다. 실패 job은 `shard shell 05`와 최종 `collect`다. 추가 TC 수정·push·CI 재실행은 하지 않았다.

| 대상 | GitHub 상태 | 수집·검증 결과 |
| --- | --- | --- |
| build debug·release | SUCCESS | 같은 run의 두 context가 성공 |
| `test_medium` | SUCCESS | completed, 975 PASS·0 FAIL·0 SKIP |
| `test_shell` | FAILURE | completed, 3,490 PASS·1 FAIL·30 SKIP, 계획 3,521·실행 3,491·미실행 0 |
| `test_sql` | SUCCESS | collection_failed, shard 01의 배정 3,533건과 summary·JUnit 3,531건 불일치 |

`cubrid-ci 0.2.0 (dd290e9f7b9b, release)`로 SQL은 19:34:27 KST, shell·medium은 19:34:56 KST에 수집했다. 두 수집의 request·terminal observation·manifest를 schema와 대조하고 동일 Engine·run·attempt임을 확인했다. Shell·medium은 summary·raw index의 hash와 건수·실패 목록도 일치한다. 모든 SQL 10개·shell 50개·medium 1개 shard의 acquisition 상태는 `retained`다. 이는 원본 자료 확보 상태이며 전체 SQL 판정이 아니다. Binary 다운로드는 요청하지 않았고 소비한 binary budget은 0이다.

SQL 수집의 진단은 `result identity mismatch: shard 01 workflow result and JUnit counts disagree`다. 최종 report-mode 검사는 `warning`, `regression_conclusions_allowed=false`다. 이전 집계 차이와 같은 건수가 보이지만 이번 결과로 원인이나 회귀 여부를 재확정하지 않는다. 정확한 merge-base 비교와 testcase 이력 분석은 이번 복구 단위에서 수행하지 않았다.

실제 CI 산출물의 `build.read`는 Engine `e3589ae`, **debug**, 생산 run `40472072791` attempt 1을 가리킨다. 이는 회귀 실행 run `41031622190`과 구분한다. Public TC는 `b038c424b6a8d078671132e2369040493a5fc1f6`, shell private-ex TC는 `a229e1978abc4cc6c280783703c03f75524c0f05`이며 모두 `tc/pr-8128`이다. 로컬 native의 optdebug 시간과 CI debug 시간을 성능 비교하지 않는다.

### 복원 SQL의 CI 관측 범위

전체 SQL 수집 실패 상태를 유지한 채 보존된 shard 09 원본만 별도로 대조했다. 배정표·`shard.done`·summary·고유 JUnit testcase가 모두 468건이고 FAIL·ERROR·SKIP은 없다. OOS 경로는 summary 28/28·JUnit 28건이며 TC `b038c424`의 정상 SQL 목록과 정확히 같다. 원본 자료의 receipt hash와 Engine·TC 식별도 일치한다.

| 복원 TC | CI shard 09 관측 | JUnit 시간 |
| --- | --- | ---: |
| `record_boundaries` | PASS | 0.047초 |
| `sql05_bigone` | PASS | 0.051초 |
| `sql09_lob_maxcols` | PASS | 0.832초 |

이는 특정 shard에서 확인한 원본 관측이다. 수집기가 발행한 검증 완료 SQL suite summary는 없으며, 이 표로 SQL 전체의 무결성 오류를 해제하지 않는다.

### Shell 실패의 관측과 남은 분석

검증된 실패는 `shell/_40_guava/cbrd_25977/cases/cbrd_25977.sh` 한 건이며 shard 05에서 111.928초 후 FAIL이다. `diff.txt`의 실패 표시는 `cbrd_25977-16 : NOK`다. [고정 TC 소스](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/a229e1978abc4cc6c280783703c03f75524c0f05/shell/_40_guava/cbrd_25977/cases/cbrd_25977.sh)의 16번 검사 로그에서 `run_cte '' 8`은 오류 없이 끝났고 값 검사 두 개도 PASS다. 하지만 정렬한 `parallel workers`는 기대 `2·3·4`와 달리 `2·4`였다. 이 배열 비교가 NOK의 직접 조건이다. 1~15·17~18번은 OK다.

왜 worker 3이 없었는지는 미확정이다. 엔진·TC·환경 원인, PR과의 관계, 과거 재현 여부를 판단하지 않았다. 이번에는 로컬 재현이나 수정·재실행 없이 결과를 인계한다. 사람의 다음 지시 후 별도 실패 분석 단위에서 조사한다.

CI 자료는 이번 작업 자료 아래 `ci-evidence/`와 `ci-other-evidence/`에 보존한다. 각각의 `ci-sql-collector.json`·`ci-other-collector.json`은 수집 결과이며 `ci-final.json`·`ci-final-checks.json`은 종료 상태다. 로컬 `check-ci-evidence.py`의 실제 대조 결과는 `ci-restored-sql-evidence.json`, 보고 범위 제한은 `ci-report-mode.json`이다. 생성 자료·원본 로그는 Git 밖에 둔다.

현재 feature base의 `gh pr checks --required`는 required check가 없다고 보고했다. 확인한 TC Merge Gate workflow의 PR 이벤트 대상은 `develop`이며, 이 feature PR의 화면에 gate 성공이 붙었다고 주장하지 않는다. 두 연결 TC PR의 실제 검토·병합은 여전히 사람의 작업이다. TC PR을 merge·close하거나 브랜치를 삭제하지 않았다.

이번 수정으로 SQL 3개의 복구·재활성화와 1회 CI 결과 기록을 마쳤다. 과거 shell 실패 61개, 이번 `cbrd_25977-16`, 이전 장시간 PASS 3개, HA, 요구사항 전체의 독립 검증·TC 리뷰와 병합은 남아 있다. SQL 전체 수집의 정합성 문제도 이번 focused PASS로 해제하지 않는다. CBRD-26659 전체와 Work456은 미완료다.
