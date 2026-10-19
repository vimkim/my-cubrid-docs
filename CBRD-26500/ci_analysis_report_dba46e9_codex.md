# PR #7157 shell CI 분석 — dba46e9

작성·수정: 2026-10-19 (Asia/Seoul), Codex

대상: [CBRD-26500 / PR #7157](https://github.com/CUBRID/cubrid/pull/7157)

Engine: `dba46e965eaa481814922b9e76c30059f057a752`

실행: [39216768822, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39216768822)

## 1. 결론과 판단 범위

shell 실패는 **1건**이며, 오래된 testcase 정답과 새 Engine의 상세 trace 출력이 맞지 않는 경우로 판단한다. 신뢰도는 **높음**, PR 변경과의 관련성은 **unlikely**로 분류한다.

실패한 `_01_show_table.sh`는 `;plan detail`을 켠 뒤 `show tables`의 trace를 정답과 비교한다. 실제 출력에만 `EXPR_COMPILE` 진단 24행이 추가됐다. 이 기능은 merge-base에 이미 포함된 [Engine #7658의 커밋 b8199438](https://github.com/CUBRID/cubrid/commit/b8199438e5fa92b77f71b0ca39004ff286daef8a)에서 도입됐다. 해당 정답은 [private testcase #3869의 커밋 33988522](https://github.com/CUBRID/cubrid-testcases-private-ex/commit/33988522e5d1dec6bbe81a024d4e1ea46b19a048)에서 이미 갱신됐으나, 이 실행의 `tc/pr-7157`에는 반영되지 않았다.

결정적 확인은 다음과 같다. 기록된 구·신 정답에 testcase와 동일한 숫자 제거를 적용하고 `diff -b <신 정답> <구 정답>`을 실행했다. 결과는 CI console에 남은 **전체 normal diff와 바이트 단위로 일치**했다. 이는 보존된 CI 출력 차이에 대한 검증이며, 새 Engine 실행의 PASS를 뜻하지 않는다.

정확한 merge-base CI는 `not_observed`다. 따라서 이 1건의 공식 baseline 분류는 **uncomparable**이며, base PASS 또는 PR 회귀 부재를 확정하지 않는다. 관찰된 실패를 설명하는 정답 불일치와, 미확인인 base CI 결과를 구분한다. SQL 실패와 TC merge gate는 이번 분석 범위 밖이다.

## 2. CI 상태와 실패 전체 목록

2026-10-19 12:37:48 UTC에 PR 상태를 한 번 조회하고, 같은 head의 `test_shell`만 한 번 수집했다.

| 요청 suite | 수집 상태 / verdict | 실행·attempt | 전체 tests | PASS | failure | error | skipped |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `test_shell` | `completed` / `fail` | 39216768822 / 1 | 3308 | 3277 | 1 | 0 | 30 |

집계는 `3308 = 3277 + 1 + 0 + 30`, `planned 3308 = run 3278 + unrun 0 + skipped 30`으로 일치한다. shard 00–49의 증거가 모두 `retained`이며, 실패·오류 레코드 합계는 1이다.

| 항목 | 관찰값 |
| --- | --- |
| 전체 testcase 경로 | `shell/_28_features_844/issue_10984_query_profiling/_03_mixed_test/_01_show_table/cases/_01_show_table.sh` |
| 결과 | `failure`, 6.593초 |
| 실패 job | [shard 18 / job 117944934204](https://github.com/CUBRID/cubrid/actions/runs/39216768822/job/117944934204) |
| 메시지 | `_01_show_table-1 : NOK`, `diff output.temp answer.temp failed` |
| 실제 차이 | actual에만 `EXPR_COMPILE` 및 step listing 24행, 5개 diff 구간 |
| baseline 분류 | `uncomparable` |
| 원인 분류 | testcase expectation / Engine와 testcase 정답의 버전 불일치 |
| PR 관련성·신뢰도 | `unlikely` / 높음 |

head 실패 1건의 비교 집계는 `also_observed_on_base 0 + additional_on_head 0 + uncomparable 1 = 1`이다. 앞의 0은 해당 분류로 검증된 건수가 없다는 뜻이다. **base_only 건수는 미확인**이다.

## 3. 정확한 입력과 증거 검증

| 입력 | 기록된 revision 또는 상태 |
| --- | --- |
| PR head | `dba46e965eaa481814922b9e76c30059f057a752` |
| head repository / ref | `vimkim/cubrid` / `data-pgbuf-hit-ratio-bugfix` |
| target | `develop` |
| shell Engine provenance | 전 shard에서 위 head, `mode=debug`, producing run 39216768822 / attempt 1 |
| 실행 console의 build | `11.5.0.2702-dba46e9`, `64 optdebug build` |
| private testcase | `1cfce1a1bdd4761edbc9d5f34ffbd8ecd0642533`, `tc/pr-7157` |
| public testcase | 이번 shell 수집에서는 확보하지 않음 |
| 관련 설정 | Linux, DB locale `en_US`, `csql -s`, `;plan detail`, text trace와 JSON trace |
| 외부 helper | console에 `/home/cubrid-testtools/CTP/shell/init_path/init.sh`와 `shell_utils.sh`가 기록됨. 정확한 testtools revision과 전체 설정 digest는 미확인 |

collector는 `cubrid-ci 0.2.0 (9536bd3c2867, release)`다. head 수집 시각은 `2026-10-19T12:38:13.603455586Z`, exit는 0이다. red verdict가 있어도 증거 수집은 완료됐다.

선택한 append-only observation은 `20261019T123801.602593658Z-2509046-0`이다. 이 observation의 terminal command는 저장한 결과와 일치한다. request/result, manifest, summary, raw index, failure metadata를 설치 버전의 schema로 검증했다. PR·full SHA·요청 suite·run/attempt가 일치하며, raw 파일 616개의 길이·SHA-256, summary digest, 실패 메시지·diff 경로와 집계도 검증했다. 바이너리는 요청하지 않았으며 소비량은 0이다.

분석 gate는 `mode=full`, `baseline=unavailable`, `comparison_scope=none`, `regression_conclusions_allowed=false`를 반환했다. 완전한 head 실패 목록은 보고할 수 있지만, 검증된 CI baseline 대조로 회귀를 판정할 수는 없다.

## 4. 원인 분석

### 관찰

정확한 private testcase 객체를 `git show <기록된 SHA>:<경로>`로 읽었다. testcase 저장소의 worktree와 index는 변경하지 않았다.

- `_01_show_table.sh:18`은 `show_tables.sql`을 실행한다. 20–21행은 actual·answer 양쪽에서 모든 숫자를 제거하고, 29행은 두 결과를 비교한다.
- `show_tables.sql:2`는 `;plan detail`, 4–8행은 text trace와 JSON trace를 켠 `show tables`다. `trace01.sql`은 `x`, `y`, `z` 테이블과 데이터를 만든다.
- console의 비교 helper는 `dos2unix`와 행 번호 masking 후 `diff -b`를 실행한다. 반환된 normal diff에는 5개 deletion 구간만 있다. 방향은 actual이 왼쪽이므로 `<`가 actual에만 있는 행이다.

| CI normal diff 구간 | actual에만 있는 행 수 | 내용 |
| --- | ---: | --- |
| `284d283` | 1 | data filter의 `EXPR_COMPILE` 상태 |
| `290,296d288` | 7 | 첫 output list의 상태와 step listing |
| `300,306d291` | 7 | 둘째 output list의 상태와 step listing |
| `310,311d294` | 2 | aggregate operands와 data filter의 상태 |
| `315,321d297` | 7 | 하위 output list의 상태와 step listing |

별도의 값 변경, expected에만 있는 행, JSON 출력 차이는 이 normal diff에 없다. 예를 들면 다음 행들이 추가됐다.

```text
EXPR_COMPILE (data filter): interpreted (not covered)
EXPR_COMPILE (output list): active, columns covered /
EXPR_COMPILE (aggregate operands): plain operands (peeked in place, no program)
```

숫자가 비어 있는 것은 testcase의 숫자 제거 결과다. CI console의 `internal_err=0`도 확인했다. init helper의 `Is a directory` 경고와 compatibility 후보 파일 탐색 메시지는 있지만, DB 생성·서버 시작·SQL 실행 후 위 비교 실패까지 진행됐다. 이 경고들이 24행 차이의 원인이라는 증거는 없다.

Engine의 `qdump_print_expr_compile_text()`는 상세 plan이 켜진 세션에서 이 진단을 출력한다. [head의 query_dump.c:4269](https://github.com/CUBRID/cubrid/blob/dba46e965eaa481814922b9e76c30059f057a752/src/query/query_dump.c#L4269)와 4286행의 `trace_plan_detail` 조건이 testcase 설정과 맞는다. 도입 커밋 `b8199438e5fa92b77f71b0ca39004ff286daef8a`는 정확한 merge-base의 조상이다.

private testcase 갱신 `33988522e5d1dec6bbe81a024d4e1ea46b19a048`과 실제 사용된 revision 사이에서 script·두 SQL 파일의 Git blob은 모두 같다. 정답만 다르다.

| 파일 | 사용된 revision의 blob | 갱신 revision의 blob |
| --- | --- | --- |
| `_01_show_table.sh` | `ce124a917b59e0808f87eb3da720712cd127bf3f` | 동일 |
| `show_tables.sql` | `bbc309a78fd747b4d0515b0c909c3c3d11c9dd27` | 동일 |
| `trace01.sql` | `6abca4d6b7cb347433cfabeddf17bbe80cf5c6fa` | 동일 |
| `_01_show_table.answer` | `0c5e99b90bf6a7031d1c16ce4d76e7f838562db8` | `43f545fd8631cf3e58d91747f50eaafba3d5b897` |

숫자를 제거한 두 정답의 `diff -b`는 CI의 5개 구간·24행·전체 문자열과 정확히 같다. CI normal diff와 사용된 정답으로 복원한 actual을 갱신 정답과 비교한 `diff -b`도 exit 0이다. 이는 전체 raw actual 파일의 바이트 동일성을 주장하는 검사가 아니다.

### 추론·미확인·반증 조건

**추론:** 상세 trace 기능이 들어간 Engine에 이전 정답을 사용한 것이 이 실패의 가장 강한 설명이다. PR 고유 변경은 `src/base/perf_monitor.c`의 ratio 계산과 `src/storage/page_buffer.c`의 주석뿐이다. trace 출력 구현은 merge-base와 같다. 수치 차이는 testcase가 제거하며, 남은 차이는 기존 기능의 진단 행과 일치한다. 관찰된 실패를 기존 Engine 결함이나 실행 환경 문제로 분류할 근거는 부족하다.

**미확인:** 정확한 base Engine의 CI verdict, 전체 helper·configuration 일치, 정답 갱신을 적용한 실제 재실행 결과. 로컬 Engine 재현은 이번에 수행하지 않았다. 보존된 normal diff가 기존 정답 변경과 정확히 같아 우선 조사 질문은 해소됐으며, 실행 검증은 후속 작업으로 남긴다.

**반증 조건:** 같은 Engine·script·SQL·설정에서 갱신 정답을 사용해도 다른 diff가 남거나, 동일 입력의 base/head 제어 실험에서 head에만 다른 동작이 나타나면 정답 불일치만으로 설명할 수 없다.

**다음 행동:** 별도 승인된 TC 작업에서 `tc/pr-7157`에 Engine와 맞는 기존 정답 갱신을 반영하고, native focused shell runner로 해당 디렉터리를 검증한다. 최신 testcase tip 전체를 무조건 사용하기보다 Engine 기능과 정답의 대응을 먼저 확인한다. 그 후 TC PR head에만 commit/push하고, 후속 CI는 사용자의 지시에 따라 진행한다.

## 5. 정확한 merge-base 비교

같은 `test_shell` 필터로 `cubrid-ci collect-base`를 한 번 실행했다. v3 manifest/result와 observation v2를 독립 검증했다.

| 관계 | 값 |
| --- | --- |
| PR / pinned head | 7157 / `dba46e965eaa481814922b9e76c30059f057a752` |
| target ref / tip | `develop` / `1dceac8add1801aef564b27624b8fbb5b6f62d59` |
| 정확한 merge-base | `1dceac8add1801aef564b27624b8fbb5b6f62d59` |
| 관계 관찰 시각 | `2026-10-19T12:38:08.228151793Z` |
| discovery 관찰 시각 | `2026-10-19T12:39:07.258838183Z` |
| baseline observation | `20261019T123918.301332378Z-2509781-0`, outcome `incomplete` |
| 수집 결과 | exit 3, `test_shell: not_observed`, candidates 0, 선택된 run/attempt 없음 |

탐색은 해당 exact commit에 연결된 모든 paginated status/check run 링크를 대상으로 했다. 저장소 전체 workflow 검색은 하지 않았다. 따라서 이 결과는 **조회 범위 안에서 정확한 base CI가 확보되지 않았다**는 뜻이며, base가 통과했거나 한 번도 실행되지 않았다는 뜻이 아니다. baseline testcase revision과 configuration도 비교할 수 없다.

정적 소스 비교에서 PR의 두 파일 외에는 base와 head가 같다. 이는 이 trace 구현이 PR에서 추가되지 않았다는 근거이며, 실제 base CI를 대신하지 않는다. 과거 SQL 분석의 `5b1867174`를 이번 baseline으로 사용하지 않았다.

## 6. Chronicle 기록과 서명 구분

`cubrid-tcc 0.3.0`에서 full testcase path를 확인했다. 최초 explain은 `target_failure_not_indexed`였다. 해당 run의 shell만 `--revisit-limit 0`으로 한 번 수집한 뒤 explain/history를 다시 조회했다. 결과는 `SEEN_BEFORE`, 이 testcase의 retained observation 138건은 PASS 130건·FAIL 8건이다. 이 숫자는 보존된 서로 다른 입력의 관찰 수다.

이전 실패 7건 모두의 retained JUnit을 `cubrid-tcc evidence`로 hash 검증 후 읽고, testcase 객체도 비교했다. 모든 기록에서 script와 두 SQL 파일의 blob은 같지만, 정답과 Engine는 서로 다르다.

| 이전 run / PR | Engine SHA | private TC SHA | 관찰된 차이와 현재 실패의 관계 |
| --- | --- | --- | --- |
| [38524253278](https://github.com/CUBRID/cubrid/actions/runs/38524253278) / #7658 | `beead71a383bda4daf96c3c8f4d048eface8f8c9` | `89ec9e85493ec87b2f4db571bf9cb1e49d4dd350` | 동일한 actual 추가 24행. normal diff의 변경 행 전체와 구 정답 blob이 현재와 같다 |
| [38680302759](https://github.com/CUBRID/cubrid/actions/runs/38680302759) / #7658 | `c0a9d2ff3d006ad5b1f6ab7b5dc70dd818ff1f18` | `d9dc379d29cd3006c91c7b5aea220d1182997c97` | 동일한 actual 추가 24행과 구 정답 |
| [38687274058](https://github.com/CUBRID/cubrid/actions/runs/38687274058) / #7157 | `71ae9f3f615cf09025c6a29ed9841b2ad9ecaa43` | `54033447bdbd81126d2b5af6fd5bbc2847f2f6f2` | `db_user`와 `_db_user` 등 catalog 표기 차이. **현재와 다른 서명** |
| [38872612436](https://github.com/CUBRID/cubrid/actions/runs/38872612436) / #8181 | `1e6749ffba8bed269bb590afe443161b9cba5671` | `f666a9c7ff7945ccb7a0aedb525df2a337bec640` | 갱신 정답에만 24행. 현재와 **반대 방향**의 버전 불일치 |
| [38872649124](https://github.com/CUBRID/cubrid/actions/runs/38872649124) / #8191 | `3ff2946fda94c1da15a56bec69fac297e7725062` | `c8ee32674edc03404c9e847682d73f1efd00effa` | 갱신 정답에만 24행. 현재와 반대 방향 |
| [39170168993](https://github.com/CUBRID/cubrid/actions/runs/39170168993) / #8196 | `f09896b3a0667dda2b63d5b4ea461c15fba456d6` | `3b4e6ea8afeaa7bd8686f2a9d6b2f599fe9acd0c` | page batch trace 필드 차이. **현재와 다른 서명**, Chronicle snapshot은 partial |
| [39197032008](https://github.com/CUBRID/cubrid/actions/runs/39197032008) / #8025 | `f997c069b2cf01fcfc6ecc1b76c63aaffd9419b1` | `2bff1baff0f78f943d96d65b48fe981e1622f34e` | 동일한 actual 추가 24행과 구 정답, Chronicle snapshot은 partial |

현재 실행도 Chronicle은 `complete=0`, `runner_error`로 표시한다. 이는 CTP의 성공 종료 표식 부재에 대한 parser 진단이다. 현재 head suite의 완전성은 별도로 검증한 `cubrid-ci`의 50-shard 집계·provenance·JUnit에 근거한다. Chronicle의 partial 표기를 무시하거나 환경 결함으로 해석하지 않는다.

Chronicle coverage는 `complete=false`이며 기록 시작은 2026-10-14다. 현재까지 저장된 execution의 attempt/job 연결 및 helper·platform·configuration digest에는 미확인 항목이 있다. 따라서 같은 서명의 선행 관찰은 설명을 보강하지만, exact baseline 대조나 동일 root cause의 실험 증명이 아니다. 서로 다른 Engine/정답의 PASS·FAIL 혼재를 flakiness로 부르지 않는다.

## 7. 우선순위와 재검증 자료

1. Engine와 맞는 기존 정답 변경을 TC branch에 반영하는 별도 작업을 진행한다. native shell 재검증의 판정 artifact를 확인한다. 이번 조사에서는 source·TC 수정, 게시, CI trigger, merge를 수행하지 않았다.
2. 정답 갱신 뒤에도 실패하면 위 반증 조건에 따라 동일 testcase revision의 base/head 제어 실험을 수행한다. 그 전까지 base verdict는 unknown으로 유지한다.
3. 남은 SQL 실패와 TC merge gate는 상위 작업 368의 별도 미완료 항목이다. 이번 shell 분석 완료로 전체 PR 작업을 완료 처리하지 않는다.

다음 위치는 로컬 재검증용 참조다. raw CI와 중간 산출물은 문서 저장소에 추가하지 않았다.

| 증거 | 위치 |
| --- | --- |
| 이번 조사 디렉터리 | `/home/vimkim/tmp/pr7157-shell-ci-20261019.JbMmWf/` |
| PR 상태·collector 결과 | 위 디렉터리의 `status.json`, `result.json`, `base-result.json` |
| 독립 schema·digest 검증 | `validate_bundle.py`, `head-validation.json`, `base-validation.json`, `head-manifest.snapshot.json`, `base-manifest.snapshot.json` |
| report gate | `assessment.json`, `report-mode.json` |
| 정답 비교 재현 | `audit_answer.py`, `answer-audit.json`, `ci-normal-diff.txt`, `expected-update-normal.diff`, 정규화 정답 파일 |
| Chronicle 조회·서명·객체 비교 | `tcc-find.json`, `tcc-explain-initial.json`, `tcc-sync.json`, `tcc-explain.json`, `tcc-history.json`, `tcc-prior-signatures.json`, `tcc-prior-*.xml`, `testcase-object-comparison.json` |
| head collector root | `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7157/dba46e965eaa481814922b9e76c30059f057a752/` |
| head suite root (head collector root 아래) | `providers/github-actions/runs/39216768822/attempts/1/test_shell/` |
| failure (suite root 아래) | `failures/shell_28_features_844_issue_10984_query_profiling_03_mixed_test_01_show_table_ca-098bb261a9/`의 `metadata.json`, `message.txt`, `diff.txt` |
| baseline collector root | `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/1dceac8add1801aef564b27624b8fbb5b6f62d59/` |

보존된 자료만 재검증하려면 조사 디렉터리에서 다음을 실행한다. 네트워크 수집이나 Engine 실행을 추가하지 않는다.

```bash
/usr/bin/python3 validate_bundle.py result.json
/usr/bin/python3 validate_bundle.py base-result.json
python3 audit_answer.py
python3 /home/vimkim/.agents/skills/cubrid-ci-analyze/scripts/report_mode.py assessment.json
```

`audit_answer.py` 내부의 `diff -b`는 서로 다른 정답이므로 exit 1을 예상하고, 그 diff와 CI 문자열의 일치를 assert한다. 전체 audit script의 성공 exit는 0이다.
