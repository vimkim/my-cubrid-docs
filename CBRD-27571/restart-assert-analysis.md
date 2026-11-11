# CBRD-27571 볼륨 추가 중단 후 재시작 assertion 분석

`cbrd_27571.sh`의 재시작 실패가 develop의 기존 결함인지 OOS reclaim 변경의 결함인지 판단한다. 독자는 로그·복구·스토리지 담당 개발자와 PR #8434 리뷰어다. 분석일은 2026-11-11, Asia/Seoul이다.

**결론은 develop의 기존 CBRD-27571이다.** 실패한 recovery index는 core에서 확인한 `RVDK_LINK_PERM_VOLEXT`다. 소스에는 정상 temporary LSA 페이지에서 `pgbuf_set_lsa()`가 반환하는 `NULL`을 compensate 경로가 오류로 취급하는 결함이 있다. 이번 실행도 같은 원인이라는 판단은 테스트 조건·소스·기존 이슈에 근거한 강한 추론이다. 실제 core의 page LSA 값은 출력되지 않았다. 최근 develop merge가 이 엔진 결함을 새로 만든 것은 아니다. 수정 전 엔진에 회귀 테스트가 먼저 들어와 오래된 결함을 노출했다.

기존 [CBRD-27571](https://jira.cubrid.org/browse/CBRD-27571)의 조건·index·호출 경로와 일치하므로 새 OOS 하위 이슈를 만들지 않는다. [수정 PR #8284](https://github.com/CUBRID/cubrid/pull/8284)는 확인 시점에 open, 미병합이다. 이 보고서는 엔진 수정이나 새 로컬 재현의 결과가 아니다.

## 검증한 실행과 범위

대상 testcase는 `shell/_06_issues/_26_2h/cbrd_27571/cases/cbrd_27571.sh`다. `test_shell`만 수집했다. `test_sql`, `test_medium`, `test_sql_by_cci`의 전체 상태와 #8434 전체 병합 준비 여부는 이 분석의 범위가 아니다.

| 구분 | Engine commit | Run, attempt 1 | TC commit 및 branch | 수집·검증 결과 |
| --- | --- | --- | --- | --- |
| PR #8434 | `443073283d89e4511b2fa9a5b6a16898770f7e65` | [42962418830](https://github.com/CUBRID/cubrid/actions/runs/42962418830), shard 27 | `7a56421e29ac576a518186dc9b0cc0dc473ae959`, `tc/pr-8434` | complete, manifest·summary validated |
| #8434 exact merge-base | `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f` | [42819814597](https://github.com/CUBRID/cubrid/actions/runs/42819814597), shard 34 | `8ef4f62780971383bbf59c473bfdcf9a93527624`, `tc/pr-7990` | complete, validated_exact |
| develop 대상 PR #8409 | `b7bbbe8266a47abc76109d28282acb721263d276` | [42807018862](https://github.com/CUBRID/cubrid/actions/runs/42807018862), shard 00 | `8c9acb9c53a104c05d767687437658b96026a7c9`, `tc/pr-8409` | complete, manifest·summary·rerun source validated |
| 교차 확인한 PR #8348 | `225375922881fb0f61cc311458078264961eef79` | [42850100191](https://github.com/CUBRID/cubrid/actions/runs/42850100191) | 기존 보관 core 출력만 읽음 | 이번 수집·검증 대상 아님 |

세 검증 실행은 debug 빌드다. 테스트 파일을 각 TC Git object에서 읽어 비교한 SHA-256은 모두 `76a42075cee04766276abd1ef33c7e76796d34dd7c88e5f561f80ab9b6af8227`이다. TC 저장소의 branch 이름이나 현재 checkout으로 동일성을 추정하지 않았다.

#8409는 develop push 실행이 아니라 develop 대상 PR 실행이다. 실제 Engine SHA는 workflow의 `head_sha`와 다르므로 shard의 build provenance로 식별했다. 소스에서는 별도로 OOS merge의 develop parent `2dd94e32ab86a756b0f1ea2123ad7d2ac913321b`에 같은 결함이 있음을 확인했다. 두 근거를 합쳐 develop에도 존재한다고 판단한다.

#8409의 run 42807018862는 partial rerun이다. 28건을 실제 실행해 25건 통과, failure 2건, error 1건이다. 원본 run 42775763898의 3,570건과 합산하지 않는다. 원본은 3,527건 통과, failure 13건, skip 30건이었으며, 이것은 별도 과거 실행이다. Engine build는 이 원본 run에서 재사용했다.

merge-base의 run 42819814597은 summary v2다. 수집기에 기록된 집계는 3,580건 중 통과 3,549건, error 1건, skip 30건이다. build provenance는 run 42785110884다. 이 집계를 모두 새로 실행한 건수로 해석하지 않는다.

### shell 실패 목록과 비교 한계

| 실행 | 대상 및 관찰 | 분류 |
| --- | --- | --- |
| #8434 | `cbrd_27571.sh`, restart assertion, error | `also_observed_on_base`, develop에서도 같은 증상 |
| #8434 | `shell/_06_issues/_26_1h/cbrd_26860/cases/cbrd_26860.sh`, `cubpl::executor::response_callback_command` core, error | 이 merge-base summary에 없는 추가 관찰, 원인·PR 관련성은 분석 범위 밖 |
| exact merge-base | `cbrd_27571.sh` 1건만 error | #8434와 같은 index·호출 경로 |
| #8409 partial rerun | `cbrd_27571.sh` error, `cbrd_27950_cas.sh`와 `cbrd_27950_timeout.sh` failure | 뒤의 두 건은 분석 범위 밖 |

#8434 shell 전체 집계는 3,580건 중 통과 3,548건, error 2건, skip 30건이다. 이 보고서의 원인 결론은 `cbrd_27571.sh` 한 건에만 적용한다. #8434에서 관찰한 error 2건 중 base와 공통인 것은 1건, 추가 관찰은 1건이며 base에만 있는 error는 없다. 추가 관찰의 원인과 다른 suite의 실패를 해소했다고 주장하지 않는다.

## core가 직접 보여 주는 사실

#8434, exact merge-base, #8409의 testcase 출력은 모두 1단계 OK, 2단계 restart NOK, 이어서 3~5단계 NOK다. 연결 후 종료 조건은 충족했고, 재시작 assertion 때문에 볼륨 제거·checkdb·재추가 단계도 실패했다.

세 실행의 core 출력은 공통으로 다음 값을 보여 준다.

```text
log_append_compensate_internal
  rcvindex = RVDK_LINK_PERM_VOLEXT
  pgptr = ... "CUBRID/Volume"
  length = 4
  undo_nxlsa = 0x0
log_append_compensate
log_rv_undo_record:320
log_recovery_undo
```

#8348의 보관 core 출력도 같은 index와 경로다. 따라서 #8434의 OOS reclaim 11개 커밋이 있어야만 발생하는 실패가 아니다.

브리프의 switch `default` 가설은 해당 소스와 다르다. #8434의 [log_manager.c 3253~3256행](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/transaction/log_manager.c#L3253-L3256)은 다음 조건이다.

```c
if (pgptr != NULL && pgbuf_set_lsa (thread_p, pgptr, &start_lsa) == NULL)
  {
    assert (false);
    return;
  }
```

같은 분기는 #8348에서는 3214행, develop parent에서는 [3202행](https://github.com/CUBRID/cubrid/blob/2dd94e32ab86a756b0f1ea2123ad7d2ac913321b/src/transaction/log_manager.c#L3192-L3203)에 있다. 줄 번호 차이는 원인 차이가 아니다.

## 데이터 구조와 복구 계약

`addvoldb -p temp`는 purpose를 지정한다. volume type을 별도로 바꾸지 않으면 permanent volume이다. 이 경우 영구 볼륨 체인의 연결 정보는 복구해야 하지만, 페이지는 temporary LSA를 유지한다. [기본 volume type](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/executables/util_cs.c#L488-L491).

연결 로그 `RVDK_LINK_PERM_VOLEXT`의 undo·redo payload는 `DISK_RECV_LINK_PERM_VOLUME`이다. `INT16 next_volid`와 가변 길이 `next_vol_fullname`을 담는다. 대상은 이전 볼륨의 헤더 page 0이다. OOS 파일이나 heap/OOS 행의 undo payload가 아니다. [구조체](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/disk_manager.c#L118-L123), [대상과 기록](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/disk_manager.c#L1000-L1051).

페이지에 temporary LSA가 이미 있으면 `pgbuf_set_lsa()`가 `NULL`을 반환하는 것은 명시된 동작이다. 정상 append는 `LOG_NEED_TO_SET_LSA`로 이 index와 temporary LSA의 조합을 제외한다. 동시에 `LOG_ISUNSAFE_TO_SKIP_RCVINDEX`는 연결 로그 자체는 생략하지 못하게 한다. 로그를 보존하는 조건과 page LSA를 변경하는 조건은 다르다. [두 조건](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/transaction/log_manager.c#L155-L172), [NULL 반환 조건](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/page_buffer.c#L5621-L5628).

## 실패가 발생하는 순서

1. TC는 temp 용도의 permanent 볼륨 256M을 완성한다. 소스에 따르면 이 볼륨의 헤더를 포함한 시스템 페이지는 temporary LSA를 갖는다. 이어 temp 용도 볼륨 1G를 추가한다. [초기화 경로](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/disk_manager.c#L727-L765).
2. `disk_format()`이 부르는 `disk_set_link()`는 이전 볼륨 헤더를 write latch로 fix한다. 기존 연결을 undo, 새 연결을 redo로 기록하고 링크를 변경·flush한다. 정상 append는 페이지의 temporary LSA를 유지한다. [disk_set_link](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/disk_manager.c#L990-L1084).
3. TC는 새 파일의 실제 할당량이 64M을 넘은 뒤 서버를 kill한다. 이전 볼륨 헤더에 새 볼륨명이 있는지도 검사한다. [테스트의 종료 조건](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/7a56421e29ac576a518186dc9b0cc0dc473ae959/shell/_06_issues/_26_2h/cbrd_27571/cases/cbrd_27571.sh#L44-L68).
4. 재시작 undo의 `log_rv_undo_record()`는 물리 undo 함수에 앞서 CLR을 적기 위해 `log_append_compensate()`를 부른다. [호출 순서](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/transaction/log_recovery.c#L318-L322).
5. 소스의 `log_append_compensate_internal()`은 CLR을 append한 뒤 `LOG_NEED_TO_SET_LSA` 검사 없이 헤더의 LSA를 변경하려고 한다. temporary LSA 때문에 `NULL`이 반환되면 debug assertion이 발생한다. core의 호출 경로와 TC 조건은 이번 실패도 이 분기를 따른다는 강한 근거다. 실제 연결 복원 함수 `disk_rv_undoredo_link()`는 아직 호출 전이다. [CLR 경로](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/transaction/log_manager.c#L3245-L3260), [연결 복원](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/disk_manager.c#L1526-L1539).

소스에서 확인한 결함은 정상 append와 compensate의 page LSA 갱신 조건이 일치하지 않는 것이다. 이 경로에서 temporary LSA는 정상 상태다. 이것을 이번 실행의 원인으로 보는 추론의 신뢰도는 높다. assertion만으로 페이지 손상이나 OOS record 오독을 추정할 근거는 없다.

## 도입 이력과 최근 노출 계기

최초 assertion 도입은 [fd87394ae028e04112ac0e56e0741f5adf1aca67](https://github.com/CUBRID/cubrid/commit/fd87394ae028e04112ac0e56e0741f5adf1aca67)이다. 2011-07-14 Prior_LSA 변경에 CUBRIDSUS-5300이 포함된다. 부모 revision은 `pgbuf_set_lsa() == NULL`이면 `Don't need to log`로 돌아갔다. 이 변경은 CLR append를 먼저 하도록 옮기고 같은 조건에 `assert(false)`를 추가했다. [도입 직후 코드](https://github.com/CUBRID/cubrid/blob/fd87394ae028e04112ac0e56e0741f5adf1aca67/src/transaction/log_manager.c#L3280-L3291).

현재 blame이 가리키는 2014년 `6522201dab2037afe931d8a01ede27fa0af8f31a`는 중간 tree 전환 뒤 CUBRID trunk를 복원한 커밋이다. 최초 도입과 구분했다. 최근 merge `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f`의 develop parent `2dd94e32ab86a756b0f1ea2123ad7d2ac913321b`, #8348 head, #8434 head에서 `log_append_compensate_internal`, `disk_set_link`, `disk_rv_undoredo_link`, `pgbuf_set_lsa_debug` 함수 본문은 동일하다.

| testcase 이력 | commit | 시각, KST |
| --- | --- | --- |
| develop에 회귀 TC 도입, private-ex PR #4582 | [`c8e675d18ad1708d3a47228343f268b7dfd0cc02`](https://github.com/CUBRID/cubrid-testcases-private-ex/commit/c8e675d18ad1708d3a47228343f268b7dfd0cc02) | 11-10 15:14 |
| OOS TC에 develop merge | `e56dfa32a2c0195cda3d9ac65e24aa0a72f57217` | 11-10 17:19 |
| develop에서 TC revert, [private-ex PR #4827](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4827) | `aedb39fab659006b2b0024205c7f047d5c45a9e1` | 11-10 23:45 |
| OOS TC로 revert를 cherry-pick | [`b91e7f6406e27e6666d8bea79f25e88645461e06`](https://github.com/CUBRID/cubrid-testcases-private-ex/commit/b91e7f6406e27e6666d8bea79f25e88645461e06) | 11-11 14:35, committer 기준 |

수정 PR #8284는 아직 미병합이다. 따라서 최근 CI 실패의 가장 직접적인 계기는 수정 전에 테스트가 실행 대상에 들어간 것이다. 브리프의 이전 head `94ed2ea46`에서 shell이 통과했다는 정보만으로 그 엔진에 결함이 없었다고 판단할 수 없다. 이번 조사에서는 그 통과 run의 testcase SHA와 실제 실행 여부를 따로 검증하지 않았다.

## JIRA 중복 판단과 등록 결과

`cubrid-jira search CBRD-27571`로 확인한 기존 summary는 `Debug build core dumps when rolling back a volume added after a temp-purpose permanent volume`이다. 상태는 Develop, resolution은 Unresolved, 유형은 Correct Error, 우선순위는 Minor다. 담당자는 인치준, components는 Disk/File·Transaction, Target Version은 guava·11.4 Patch 8이다. 이 값들은 기존 필드의 관찰이며 새 배정 제안이 아니다.

`cubrid-jira-dup` 기본 후보 20건을 확인했다. schema는 `cubrid-jira-dup/candidates/1`, `complete=true`, errors는 없었다. 인덱스 8,028건의 완전 동기화 시각은 `2026-11-11T08:37:44.917591+00:00`이다. CBRD-27571은 최종 rank 4, lexical rank 1, semantic rank 1이었다. 순위로 중복을 확정하지 않고 live description과 댓글을 비교했다.

| 이슈 | 상태·resolution | 판정과 근거 |
| --- | --- | --- |
| [CBRD-27571](https://jira.cubrid.org/browse/CBRD-27571) | Develop·Unresolved | 동일 결함. temp-purpose permanent 볼륨 뒤의 추가 중단, `RVDK_LINK_PERM_VOLEXT`, compensate의 temporary LSA 예외 누락까지 일치한다. |
| [CBRD-27270](https://jira.cubrid.org/browse/CBRD-27270) | Open·Unresolved | 관련 조사. 복구·종료 시 temp 판정 전반의 안전성을 다루며, 이번 특정 CLR assertion 수정과 범위가 다르다. |
| [CBRD-27562](https://jira.cubrid.org/browse/CBRD-27562) | Confirmed·Unresolved | 관련 개선. temp sector 예약·temp volume 확장에서 sysop을 제거하는 문제다. permanent volume 링크 복구의 예외 누락과 다르다. |
| [CBRD-28013](https://jira.cubrid.org/browse/CBRD-28013) | Open·Unresolved | 관련 CI 추적. develop 공통 `cbrd_27571` 실패를 이미 기록한다. 엔진 결함 자체는 CBRD-27571이 소유한다. |

검색 상위 CBRD-27987의 본문도 읽었다. commit-with-postpone의 LSA를 잘못 기록하여 recovery analysis에서 실패하는 별도 결함이므로 이 중복 후보에서는 제외했다. 관련 이슈의 description과 반환된 댓글을 읽었으며, 이번 조사에서 새 이슈 생성·기존 이슈 변경은 하지 않았다.

OOS 고유 결함이라는 조건이 성립하지 않으므로 CBRD-26978 아래에 Daehyun Kim 담당 Sub-task를 만들지 않는다. 기존 priority와 담당자를 변경할 근거도 추가하지 않는다. 분류는 기존 Correct Error, 문제 범주는 recovery·reliability가 맞다.

### 기존 이슈에 보강할 한국어 초안

다음 문안은 검토용이다. 기존 설명을 대체하거나 게시하지 않았다.

> PR #8434 head `443073283d89e4511b2fa9a5b6a16898770f7e65`의 [run 42962418830](https://github.com/CUBRID/cubrid/actions/runs/42962418830), exact merge-base `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f`의 [run 42819814597](https://github.com/CUBRID/cubrid/actions/runs/42819814597), develop 대상 PR #8409의 [run 42807018862](https://github.com/CUBRID/cubrid/actions/runs/42807018862)에서 같은 `cbrd_27571.sh`가 실패한다. 세 testcase 파일은 동일하다. core의 recovery index는 모두 `RVDK_LINK_PERM_VOLEXT`이며, `log_rv_undo_record()`가 CLR을 기록하다가 `pgbuf_set_lsa()`의 NULL 반환에 대한 assertion으로 종료한다. 실제 core의 page LSA는 미확인이지만, 테스트 조건과 소스는 기존 CBRD-27571의 temporary LSA 예외 누락이 원인이라는 강한 근거다. #8434의 OOS reclaim 변경 때문에 새로 발생한 실패로 분류하지 않는다. 수정 PR #8284는 미병합이며, TC 삭제로 이 실패가 사라지는 경우를 엔진 수정 검증과 구분해야 한다.

## PR #8434 병합 조건에 미치는 영향

이 실패의 #8434 관련성은 `unlikely`, 신뢰도는 높음이다. 근거는 검증된 exact merge-base의 같은 실패, develop 기반 CI의 같은 core, 동일 testcase 내용, 관련 함수의 동일성이다. 이 판단은 `cbrd_27571` 원인 귀속에만 적용한다.

기존 결함이라는 사실은 CI를 자동 통과시키지 않는다. `test_shell` 성공을 요구하는 병합 정책에서는 실패가 남아 있는 동안 성공 조건이 충족되지 않는다. 수정 PR #8284의 반영과 같은 엔진 수정 검증, 또는 담당자가 승인한 테스트 대상 조정이 별도 필요하다. 이 조사에서 CI 예외 승인이나 테스트 변경은 하지 않았다.

이번 세션의 단일 status snapshot에서는 같은 head의 [rerun 42987660428](https://github.com/CUBRID/cubrid/actions/runs/42987660428)이 진행 중이었다. suite status는 2026-11-11 17:31 KST 보고 기준 PENDING이었다. 결과를 기다리거나 재실행·취소하지 않았다. 나중에 통과하더라도 실행 TC revision과 이 case의 포함 여부를 확인해야 엔진 수정과 테스트 제거를 구분할 수 있다.

## 검증 방법과 남은 한계

수집기는 `cubrid-ci 0.2.0 (5141d5bf05ed, release)`다. historical run을 명시해 최신 rerun과 섞지 않았다. 다음 명령은 기존 증거를 읽으며 CI를 시작하지 않는다.

```bash
cubrid-ci collect-commit 443073283d89e4511b2fa9a5b6a16898770f7e65 --run-id 42962418830 --suite test_shell --json
cubrid-ci collect-base 8434 --suite test_shell --json
cubrid-ci collect-commit b7bbbe8266a47abc76109d28282acb721263d276 --run-id 42807018862 --suite test_shell --json
```

각 명령 결과에 `cubrid-ci verify --suite test_shell`을 실행했다. baseline 검증에는 `--pr 8434 --pr-head 443073283d89e4511b2fa9a5b6a16898770f7e65`를 함께 전달했다. 모두 observation complete, manifest validated, requested_summaries validated, result_matches_observation true, requested_suites_reconciled true다. baseline은 validated_exact이고 `report_mode.py` 판정은 full, 비교 허용 범위는 validated_cases_only다.

새 수집의 내구성 있는 증거는 `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/<위 Engine SHA>/` 아래에 있다. 각 `providers/github-actions/runs/<run>/attempts/1/test_shell/summary.json`과 `failures/*cbrd_27571*/message.txt`에서 집계·core를 확인했다. 원래 브리프에 지정된 `pr-8434`·`pr-8348` 증거는 별도로 보존했다.

Chronicle `cubrid-tcc 0.3.0`의 기존 인덱스는 stale·NOT_INDEXED였다. run 42807018862의 shell만 한 번 refresh했다. 그러나 Chronicle은 현재 JUnit 경로를 확보하지 못해 failed.list 기반의 partial observation만 남겼다. 따라서 이력 빈도·flakiness·최초 실패 시점은 Chronicle에서 확정하지 않는다. 위 실행별 결론은 별도로 완전 검증된 `cubrid-ci` 증거에 근거한다.

이번 조사에서 새 빌드·로컬 DB 재현·core binary 다운로드는 하지 않았다. 보관된 텍스트 core는 실제 VPID 수치, page LSA 값, payload bytes를 출력하지 않는다. temporary LSA 상태는 TC와 해당 소스로 설명한 것이며 core에서 직접 읽은 값이 아니다. 최적화된 debug stack의 `log_recovery_undo` 줄 번호만으로 원래 로그 레코드 종류를 추가 단정하지 않았다.

release 빌드에서는 assert가 없어 복구가 정상 완료된다는 검증은 기존 JIRA와 #8284 작성자의 보고다. 이번 세션에서 release 동작을 재현하지 않았다. core 페이지의 실제 LSA가 temporary가 아니거나 동일 파일·조건의 develop 엔진이 이 경로를 통과한다면 원인 판단을 재검토해야 한다. 추가 검증은 실제 VPID·header LSA·volume type/purpose를 확인하거나 #8284 수정 전후에 같은 TC를 실행하는 것이다.

초기 `rg --files` 탐색이 cb 전체를 대상으로 하면서 보호 대상 CBRD-27781 worktree의 파일명도 열거했다. 이후 탐색을 지정 저장소와 Git object로 제한했다. 보호 worktree의 파일 내용·build·install·DB는 읽거나 변경하지 않았다. 엔진·testcase 파일 수정, push, GitHub 댓글, CI trigger, 다른 프로세스 중단은 하지 않았다. 소스용 작업 트리나 install을 새로 만들지 않았으므로 해당 정리는 없다. 문서 task worktree와 task branch는 승인 전 검토를 위해 보관한다.
