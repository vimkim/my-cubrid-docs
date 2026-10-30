# PR 8348 shell 실패 `_enhance_10010`의 이력과 로컬 반복 실행

R5 작성자가 [PR 8348](https://github.com/CUBRID/cubrid/pull/8348)의 유일한 shell 실패를 R5 수정과 연결해야 하는지 판단하도록 CI 밖의 근거를 정리한다. 분석일은 2026-10-30, Asia/Seoul이다. 대상 head는 `628857607265880ef7bbdda4973b1b6f06e8b797`이다.

CI 증거 자체는 [CI 분석 경고 보고서](ci_analysis_report_6288576_claude.md)에 있다. 그 보고서는 SQL 수집의 무결성 오류 때문에 회귀 결론을 허용하지 않는다. 이 문서의 판단은 그 제한을 우회하지 않는다. 과거 이력, 로컬 반복 실행, 변경 범위라는 별도 근거에서 나온 잠정 판단이며, 아래의 반증 조건이 나오면 다시 검토한다.

## 결론

R5 수정이 이 실패를 일으켰을 가능성은 **낮다**(PR relation `unlikely`, 신뢰도 중간). 근거는 다음 네 가지다.

- 같은 testcase의 같은 4번 검사가 OOS 코드가 없는 develop 기반 PR에서도 한 번 실패했다.
- 정확한 merge-base, R1 PR 8330, R6 PR 8347의 CI 실행에서는 같은 testcase가 통과했다.
- R5 빌드에서 3~5번 검사를 50회 반복했을 때 모두 기대한 오류 메시지가 나왔다.
- testcase는 `bit(6)` 행을 몇 개 INSERT할 뿐이며, R5가 바꾼 relocation 레코드 vacuum 경로를 거칠 UPDATE가 없다.

이 판단은 CI 요구 사항을 면제하지 않는다. shell 상태를 통과로 바꾸려면 별도 승인으로 재실행해야 한다.

## 실패한 검사

정확한 경로는 `shell/_35_cherry/issue_21654_server_side_loaddb/loaddb_CS/_01_utility/_17_loaddb/_enhance_10010/cases/_enhance_10010.sh`이다. 4번 검사는 닫는 따옴표가 앞에 붙은 `1 Xa0'` 행을 `cubrid loaddb -C`로 넣고, `err.log`에 `syntax error`가 있는지 본다. CI에서는 이 줄이 없어서 NOK였다. `err.log`의 실제 내용은 CI 증거에 남지 않았다. 세부 조건은 CI 분석 경고 보고서에 있다.

## 과거 이력

Chronicle(`cubrid-tcc 0.3.0`)로 같은 경로와 shell suite의 보존 이력을 조회했다. 조회 전 색인은 2026-10-29까지만 갱신돼 있었다. 그래서 이번 실행 41050496911, merge-base 40738391553, R1 40853451200, R6 41048233875의 shell 결과만 `--revisit-limit 0`으로 추가 수집했다. R6 실행은 첫 수집에서 GitHub HTTP 502로 실패했고, 한 번 다시 수집해 성공했다.

| 실행 | shard | 엔진 | testcase | 결과 |
| --- | --- | --- | --- | --- |
| [38537553742](https://github.com/CUBRID/cubrid/actions/runs/38537553742) (PR 8054) | 49 | `d9dd652f3` | `93cdb552d` (`tc/pr-8054`) | FAIL, 4번만 NOK |
| [40738391553](https://github.com/CUBRID/cubrid/actions/runs/40738391553) (merge-base) | 17 | `dcbf09e4f` | `75a02020e` | PASS |
| [40853451200](https://github.com/CUBRID/cubrid/actions/runs/40853451200) (R1, PR 8330) | 48 | `4db11c5f1` | `3512cebb8` | PASS |
| [41048233875](https://github.com/CUBRID/cubrid/actions/runs/41048233875) (R6, PR 8347) | 27 | `eac70c7e7` | `8c8aec181` | PASS |
| [41050496911](https://github.com/CUBRID/cubrid/actions/runs/41050496911) (R5, PR 8348) | 46 | `628857607` | `a0b3bb729` | FAIL, 4번만 NOK |

보존된 실행은 모두 195건이고 그중 PASS가 193건, FAIL이 2건이다. Chronicle의 결과는 `SEEN_BEFORE`이다.

이전 실패는 [PR 8054](https://github.com/CUBRID/cubrid/pull/8054)의 실행이다. 그 PR은 `develop` 대상의 CBRD-27516(DESC 열이 있는 기본 키의 외래 키 검사)이다. 엔진 `d9dd652f31f810e456d98c91bcc3694cc1ae7ab3`은 `feature/oos-merge` 기준 `dcbf09e`를 포함하지 않는다. 그 revision의 `src/query/vacuum.c`에는 OOS vacuum 함수 `vacuum_heap_oos_delete_within_sysop`이 없다. Chronicle이 보존한 그 실행의 JUnit에도 이번과 같이 1~3번과 5~10번이 OK, 4번만 NOK로 기록됐다.

Chronicle의 flakiness 판단은 `UNKNOWN`이다. 같은 엔진과 testcase 조건에서 PASS와 FAIL이 모두 관찰된 사례가 없기 때문이다. 서로 다른 PR의 결과가 섞인 것만으로는 flaky를 증명하지 않는다. 색인은 여전히 `STALE`이고 기간 coverage도 완전하지 않다. 따라서 실패 빈도는 195건 중 2건이라는 보존 범위의 관찰일 뿐이다.

## 로컬 반복 실행

### 격리 testkit 실행은 판정을 내지 못했다

먼저 native testkit 격리 실행으로 이 testcase 하나를 돌렸다. 엔진은 R5 debug 설치본 `11.5.0.2782-6288576`이다. 커밋 표기를 맞추려고 같은 트리를 다시 configure하고 설치했다. testcase는 local checkout `dfb7da19`이며, 이 디렉터리 내용은 CI의 `a0b3bb7`과 같다.

namespace 안에서 시작한 `cub_server en10`이 master 접속을 반복하며 `Datagram socket error.... Too many open files`와 `Communication error during connect`를 반복 기록했다. 오류 ID는 10분 동안 1,227만을 넘었다. 그래서 `cubrid server start en10`이 돌아오지 않았다. 625초 뒤 중단했고 testcase 판정은 나오지 않았다. 이 실행을 NOK로 세지 않는다.

사용자 파일 한도는 131072였다. 같은 설치본은 격리하지 않은 작업 환경에서는 정상적으로 시작됐다. 따라서 이 현상은 격리 실행 환경과 관련된 것으로 보이지만 원인은 확인하지 않았다.

### 작업 환경에서 3~5번 검사를 50회 반복했다

같은 설치본으로 R5 작업 환경에 새 DB `r5en10`을 만들었다. 데이터 볼륨은 64MB, 로캘은 `en_US.utf8`이다. 서버는 CS 모드로 시작했다. testcase 압축 파일의 입력으로 1·2번 단계를 한 번 실행한 뒤, 3번(`en10_objects2`) → 4번(`en10_objects3`) → 5번(`en10_objects4`) 순서를 50회 반복했다.

50회 모두 3번 로그에 `domain conflict`, 4번과 5번 로그에 `syntax error`가 있었다. 4번 로그의 예는 다음과 같다.

```text
Start object loading.
Line 3:Missing attribute values.  Expected 2, found 1.
line 3: syntax error at "Xa0"
Total 0 object(s) inserted, 2 object(s) failed.
```

이 반복은 CI와 조건이 다르다. 격리 실행이 아니고, testcase의 `cubrid_createdb -r`과 shell CI 설정을 쓰지 않았다. merge-base 빌드로 같은 반복을 하지는 않았다. 따라서 50회 통과는 R5 빌드에서 이 검사가 항상 실패하지는 않는다는 근거이며, 실패 확률을 비교한 결과는 아니다. 테스트 DB는 종료 후 삭제했고 서버도 중지했다.

## R5 변경 범위와의 관계

R5 커밋은 `src/query/vacuum.c`의 `vacuum_heap_record`에서 `REC_RELOCATION` 분기만 바꾼다. forward 페이지를 sysop이 끝날 때까지 고정하는 6줄 추가와 2줄 삭제이다. 이 분기는 UPDATE로 다른 페이지에 옮겨진 행을 vacuum할 때만 실행된다.

이 testcase는 `bit1` 테이블에 행을 넣기만 하고 UPDATE하지 않는다. 4번 검사의 입력은 파싱 단계에서 거부된다. 따라서 이 검사의 오류 메시지가 R5 분기를 거친다고 볼 근거는 찾지 못했다. loaddb와 함께 바뀌는 시스템 catalog 레코드가 이 시점에 relocation vacuum을 일으키는지는 확인하지 않았다.

| 항목 | 내용 |
| --- | --- |
| PR relation | `unlikely` |
| 신뢰도 | 중간. 같은 4번 NOK의 OOS 이전 사례와 R5 빌드의 50회 통과가 근거이다. 같은 조건의 merge-base 대조와 CI `err.log`는 없다. |
| 반증 조건 | R5 head에서만 같은 조건의 반복 실행 중 4번 NOK가 재현되고 merge-base에서는 재현되지 않는 경우. 또는 실패 시점의 `err.log`와 서버 로그가 vacuum 대기, 래치 시간 초과, 서버 장애를 보여주는 경우. |
| 미확인 | CI 실패 시점 `err.log`의 내용, 메시지가 빠진 원인, 서버 측 loaddb 오류 전달 경로의 경쟁 여부 |

## 다음 작업

- PR 8348의 shell 상태를 통과로 만들려면 `/run rerun 41050496911`로 실패한 shell testcase만 다시 실행한다. CI 실행은 사용자 승인이 필요하다.
- 같은 NOK가 다시 나오면 다음을 확인한다.
  - 실패 shard의 `err.log`를 보존할 방법을 찾는다.
  - 같은 조건에서 merge-base와 R5를 번갈아 반복 실행한다.
- 4번 메시지가 가끔 빠지는 원인은 R5와 별개의 loaddb 후속 조사 후보이다. 이 문서로 새 티켓을 만들지 않았다.
- 격리 testkit 실행의 `Too many open files` 반복은 로컬 실행 환경 문제로 따로 기록한다. 원인은 확인하지 않았다.

## 로컬 증거 위치

- Chronicle 조회와 수집 결과: `/home/vimkim/temp/pr7990-hornet-review-20261029/r5/ci8348-enhance10010/analysis/`의 `tcc-*.json`, `tcc-*.err`
- 격리 testkit 시도: `/home/vimkim/temp/pr7990-hornet-review-20261029/r5/ci8348-enhance10010/attempt-01/`. 실행 스크립트는 같은 디렉터리의 `run_attempts.sh`이다. 실행 slot의 서버 로그는 testkit이 정리해 남아 있지 않다.
- 50회 반복: `/home/vimkim/temp/pr7990-hornet-review-20261029/r5/ci8348-enhance10010/manual/run-20261030T225123/`의 `rounds.txt`와 회차별 로그. 실행 스크립트는 상위 디렉터리의 `repeat_check4.sh`이다.
