# `feat/oos`–`origin/develop` 병합 충돌 해결 기록

## 1. 범위

| 항목 | 값 |
|---|---|
| 작업 브랜치 | `feat/oos` |
| OOS 측 부모 | `b996d4d826113bc060804c381aa6912603a81c70` |
| 병합 대상 | `origin/develop` `dd53b2f2aa0b91aa7a6f6ed471e811e173a4984c` |
| merge base | `f8407ce45e4c90c30500403fc65211478c13ea06` |
| 해결일 | 2026-08-19 |
| 텍스트 충돌 | 3개 파일, 동일한 error-number tail 충돌 |
| merge commit | `465cf53e3878cc36465cbeb36e85894bdd993d7b` |

충돌 파일은 다음 세 개다.

- `src/base/error_code.h`
- `msg/en_US.utf8/cubrid.msg`
- `msg/ko_KR.utf8/cubrid.msg`

## 2. 양쪽 변경의 의도와 근거

`origin/develop` 의 CBRD-27067 (`03779da92`)은 사용자의 LOGIN/NOLOGIN capability를 SQL에서 변경할 수 있게 하면서 `ER_AU_CANT_ALTER_LOGIN` 을 당시 다음 빈 번호 `-1378` 에 추가했다. 영어·한국어 catalog에도 1378 메시지를 추가하고 sentinel을 1379로 이동했다.

`feat/oos` 부모는 같은 위치에 다음 feature 전용 항목을 보유하고 있었다.

| 기존 번호 | 심볼 | 기능 출처 |
|---:|---|---|
| -1378 | `ER_VACUUM_MASTER_DAEMON_NOT_AVAILABLE` | CBRD-26720 vacuum 진단 |
| -1379 | `ER_HEAP_OOS_BAD_INLINE_HEADER` | CBRD-26769 OOS inline stub 검증 |
| -1380 | `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` | CBRD-26937 OOS+bigone 거부 |
| -1381 | `ER_HEAP_OOS_CORRUPTED_RECORD` | CBRD-26792 OOS chunk record/metadata 손상 |
| -1382 | `ER_HEAP_OOS_INVALID_ARGUMENT` | CBRD-26792 OOS API 인자 검증 |
| -1383 | `ER_LAST_ERROR` | engine error sentinel |

직전 병합 기록 `feat-oos/merge-conflict-af56432-codex.md` 에는 다음 정책이 이미 확정돼 있다.

> `develop` 변경의 번호와 순서를 먼저 유지하고, OOS 전용 항목은 그 아래로 이동한다.

이번 충돌은 서로 다른 동작이 같은 새 번호를 독립적으로 점유한 것이며, 어느 한쪽을 버릴 이유가 없다.

## 3. 해결 결정

### 결정 1 — `develop` 오류 번호 보존

`ER_AU_CANT_ALTER_LOGIN` 을 `-1378` 에 유지했다. 이 번호는 CBRD-27067이 `develop` 에 공개한 순서를 그대로 보존한다.

### 결정 2 — vacuum/OOS block을 한 칸 이동

feature 전용 심볼과 동작은 모두 유지하고 번호만 한 칸씩 뒤로 이동했다.

```text
ER_BT_LOAD_NOTIFY_VACUUM_LIMIT              -1377
ER_AU_CANT_ALTER_LOGIN                      -1378
ER_VACUUM_MASTER_DAEMON_NOT_AVAILABLE       -1379
ER_HEAP_OOS_BAD_INLINE_HEADER               -1380
ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE            -1381
ER_HEAP_OOS_CORRUPTED_RECORD                -1382
ER_HEAP_OOS_INVALID_ARGUMENT                -1383
ER_LAST_ERROR                               -1384
```

트레이드오프는 OOS/vacuum의 숫자 error ID가 한 칸 이동한다는 점이다. 호출부와 unit test는 숫자 literal이 아니라 심볼을 사용하므로 기능 의미는 변하지 않는다. `tests/`, `unit_tests/`, `.circleci/` 에서 해당 숫자 literal 기대값도 발견되지 않았다. 다만 외부 SQL/shell answer가 `call_stack_dump_activation_list` 숫자를 고정했다면 이후 CI에서 answer drift로 보일 수 있다.

### 결정 3 — 두 locale을 같은 순서로 동기화

영어와 한국어 engine catalog의 set 5에 동일한 1378~1384 배치를 적용했다. 메시지 문구는 양쪽 부모의 원문을 그대로 유지했고 번역을 새로 만들거나 의미를 바꾸지 않았다.

### 결정 4 — CCI 공개 오류 헤더는 수정하지 않음

이번 충돌의 기존 feature 오류들은 직전 병합 정책상 engine 내부 오류로 유지돼 `cubrid-cci/src/cci/base_error_code.h` 에 복제하지 않았다. CBRD-27067 원본도 engine의 세 파일만 수정했고 CCI 헤더를 변경하지 않았다. 따라서 이번 해결에서 새 client-visible 계약을 만들지 않았다.

### 결정 5 — 자동 병합된 변경은 재작성하지 않음

merge base 이후 `origin/develop` 의 여섯 커밋(CBRD-26921 DBLink DELETE, CCI/JDBC submodule bump, submodule PR-link workflow 수정, CBRD-27067 LOGIN/NOLOGIN, CBRD-27273 SHOW COLUMNS crash fix)은 conflict marker 없이 적용됐다. OOS 측 유일 커밋 `e1e651deb` 의 `src/query/serial.c` OOS recdes consumption policy 변경은 별도 파일에 있어 그대로 유지됐다. 자동 병합된 코드는 이번 error-number 충돌 해결 범위에서 재작성하지 않았다.

### 결정 6 — 사용자 로컬 상태 보존

작업 전부터 있던 `cubrid-cci` submodule의 unstaged 변경과 개인용 untracked 설정/디버깅 파일은 수정하거나 stage하지 않는다. merge가 가져온 submodule gitlink 변경만 merge index에 유지한다.

## 4. 정합성 감사

| 감사 항목 | 결과 |
|---|---|
| Git unmerged index | 없음 |
| conflict marker | 없음 |
| `git diff --cached --check` | 통과 |
| `error_code.h` 숫자 중복 | 0개 |
| 영어 engine catalog set 5 중복 | 0개, 마지막 ID 1384 |
| 한국어 engine catalog set 5 중복 | 0개, 마지막 ID 1384 |
| 영어/한국어 최종 배치 | 동일 |
| OOS symbolic test assertions | 유지 |
| OOS normative behavior 영향 | 없음; error 숫자 배치만 변경 |

OOS normative context는 2026-08-13 기준이며 일부 예시의 숫자 error ID는 현재 source보다 오래된 값이다. 이 병합은 심볼 기반 OOS+bigone rejection, inline-stub 검증, corrupted-record 검증, invalid-argument 검증의 동작을 바꾸지 않는다.

## 5. 빌드·테스트 및 병합 완료

`debug_gcc` preset의 개인용 local build workflow로 다음을 검증했다. 이 명령은 로컬 검증 편의용이며 CUBRID 조직의 공개 workflow로 제시하지 않는다.

| 검증 | 결과 |
|---|---|
| compile + install | 성공 (`just build`, 1093 build steps 및 install 완료) |
| configured CTest | 26/26 성공, 0 실패 |
| CTest 시간 | 60.82초 |
| OOS symbolic error-path tests | 성공 |
| OOS SQL bigone rejection | 성공 |
| OOS SQL/DDL/UPDATE/DELETE/transaction/storage/show | 성공 |
| OOS mock/real vacuum 및 SERVER_MODE | 성공 |
| record flag 및 TDE gate | 성공 |

검증된 tree는 `LEFTHOOK=0 git commit --no-edit` 로 merge commit `465cf53e3` 에 기록했다. 이 merge에서 hook을 끈 이유는 conflict 해결과 무관한 incoming C/C++ 전체를 local hook이 다시 포맷하지 않도록 하고, 이미 build/test한 index를 그대로 commit하기 위해서다.

최종 merge commit의 부모는 다음과 같다.

```text
parent 1: b996d4d826113bc060804c381aa6912603a81c70  (feat/oos)
parent 2: dd53b2f2aa0b91aa7a6f6ed471e811e173a4984c  (origin/develop)
```

이후 사용자 요청에 따라 merge commit `465cf53e3` 을 `origin/feat/oos` 에 push했다.

## 6. 첫 CI 실행 후 testcase follow-up

merge commit `465cf53e3878cc36465cbeb36e85894bdd993d7b` 에서 실행한 첫 `/run all` 의 exact-commit 결과는 다음과 같았다.

| suite | CircleCI job | 결과 |
|---|---:|---|
| `test_medium` | 147307 | 975/975 성공 |
| `test_sql` | 147308 | 17,449개 중 2개 실패 |
| `test_shell` | 147311 | 실패; 이번 SQL answer follow-up의 분석 범위 밖 |

`test_sql` 의 두 실패는 모두 testcase revision `b0129c05791a1b18781494c8aea08a6445821b3d` 의 answer가 OOS+bigone 거부를 `Error:-1380` 으로 기대하지만, 병합 후 엔진이 의도한 심볼 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 의 새 번호 `-1381` 을 반환한 동일한 1-line drift였다.

### 결정 7 — 엔진 심볼 배치를 되돌리지 않고 두 SQL answer를 갱신

`-1381` 은 결정 1~3에서 확정한 merged error-number 배치와 일치한다. 따라서 엔진 번호를 다시 바꾸지 않고 `tc/pr-6864` 의 다음 answer 두 곳만 `Error:-1380` 에서 `Error:-1381` 로 갱신했다.

- `sql/_13_issues/_14_1h/answers/bug_bts_10516.answer`
- `sql/_15_fbo/_02_qa_test/answers/fbo_ddl02.answer`

testcase commit은 `bcc5774f2a579b20555553c78ff8412b47c31ce8` 이며 `origin/tc/pr-6864` 에 push했다. 두 CI diff가 가리킨 기대값만 변경했고 SQL case 본문이나 engine source는 변경하지 않았다.

재검증으로 merged engine의 `debug_gcc` compile/install과 configured CTest 26/26이 다시 성공했다. 사용자 요청에 따라 같은 source head에서 testcase branch 갱신을 반영하도록 PR #6864에 새 `/run all` 을 한 번 게시했다: <https://github.com/CUBRID/cubrid/pull/6864#issuecomment-5345301955>.
