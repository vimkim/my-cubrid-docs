# PR 8347 CI 증거 수집 경고와 shell 실패 관찰

PR 7990의 R6 작성자와 리뷰어가 [PR 8347](https://github.com/CUBRID/cubrid/pull/8347)의 두 shell 실패를 이해하고 다음 검증을 결정하도록 현재 증거를 보존한다. 분석일은 2026-10-30, Asia/Seoul이다.

**전체 증거 수집이 불완전하므로 이번 자료로 회귀 여부나 근본 원인을 결론 내릴 수 없다.** head와 merge-base 양쪽에서 SQL shard `01`의 workflow 결과와 JUnit 집계가 달라 수집기가 exit `4`로 종료됐다. 검증한 medium·shell 결과와 shell의 실제 실패 조건만 아래에 기록한다. 두 실패를 flaky로 분류하거나 R6과 무관하다고 판단하지 않는다.

2026-10-30 후속 조사에서 SQL 불일치는 CTP의 중첩 범주 집계 누락으로 재현됐고 로컬 수정·검증을 마쳤다. [별도 생성기 조사와 수정 기록](SQL-summary-nested-category_1c6b224_codex.md)을 참고한다. 이 후속 결과는 기존 CI bundle을 완전하게 만들지 않으며 아래 shell 인과관계 판단 제한도 유지한다.

## 대상과 관찰 결과

- 엔진 저장소는 `CUBRID/cubrid`, head는 `eac70c7e740d55b4623b46bb84797e8214dcdcc4`이다.
- 대상 브랜치는 `feature/oos-merge`이다. 조회한 target tip과 정확한 merge-base는 모두 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`이다.
- head 실행은 [41048233875, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/41048233875)이다. 2026-10-30 21:25 KST 확인에서 전체 실행은 `completed / failure`였다.
- 수집기는 `cubrid-ci 0.2.0`, 소스 revision `dd290e9f7b9bb3a5170c38a471d12c2455ddec03`이다. 사전 `doctor` 검사는 정상이다.
- head 수집 시각은 `2026-10-30T13:23:58.826621825Z`, observation은 `20261030T132346.862656940Z-4164307-0`이다. 결과는 `incomplete`이다.

| Suite | GitHub 상태 | 수집 상태 | 검증한 집계 |
| --- | --- | --- | --- |
| `test_medium` | SUCCESS | completed | 계획 975, 실행 975, 통과 975, 실패 0, 오류 0, skip 0, 미실행 0 |
| `test_shell` | FAILURE | completed | 계획 3,490, 실행 3,460, 통과 3,458, 실패 2, 오류 0, skip 30, 미실행 0 |
| `test_sql` | SUCCESS | collection_failed | 집계 미검증. GitHub의 SUCCESS를 검증된 testcase 집계로 대체하지 않는다. |

release·debug 빌드는 GitHub 상태에서 모두 SUCCESS이다. 세 테스트 suite는 debug 엔진을 사용했다. 검증한 medium testcase revision은 `f54abce15d6d21e87a20f47fda2d678d100124fd`이다. shell 50개 shard의 testcase revision은 모두 `8c8aec181e56a12831fc7920fae12a59ae667af3`이다. 게시 사전 검사 때 조회한 private testcase tip `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`과 실행 당시 revision을 구분한다.

## 완료된 shell 증거에서 확인한 두 실패

아래 testcase 소스는 `8c8aec181e56a12831fc7920fae12a59ae667af3`의 Git object를 읽었다. 로컬 소스와 testcase worktree는 변경하지 않았다. 각 실패의 metadata, message, 추출 diff와 raw 파일 digest를 확인했다. 이는 관찰한 검사 조건의 설명이며 원인 분석 결과가 아니다.

### check_option의 44번 연결 제한 검사

정확한 경로는 `shell/_39_fig_cake/cbrd_25282/check_option/cases/check_option.sh`이다. 실패는 [shell shard 04](https://github.com/CUBRID/cubrid/actions/runs/41048233875/job/124040697711)에 있다. 1~43번과 45~47번은 OK로 기록됐다.

testcase는 `max_clients=10`을 설정하고 `-C -t 2 --process=i/12`인 `unloaddb` 12개를 백그라운드로 실행한다. 종료 후 덤프 합계가 30,000 미만이고 연결 실패 메시지가 정확히 1개인지 검사한다. [실행과 판정 소스](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8c8aec181e56a12831fc7920fae12a59ae667af3/shell/_39_fig_cake/cbrd_25282/check_option/cases/check_option.sh#L636-L680).

실제 `message.txt` 8765~8774행에는 다음 값과 NOK 분기가 있다. 여기서는 로그의 값만 간추렸다.

```text
sum_objects=30000
err_cnt=0
[ 30000 -lt 30000 -a 0 -eq 1 ]
write_nok
```

백그라운드 프로세스 수는 동시에 연결된 세션 수의 측정값이 아니다. 이번 실행에서 제한 오류가 발생하지 않은 이유는 확인하지 못했다.

### cbrd_21737의 3번 통계 파일 검사

정확한 경로는 `shell/_06_issues/_18_2h/cbrd_21737/cases/cbrd_21737.sh`이다. 실패는 [shell shard 38](https://github.com/CUBRID/cubrid/actions/runs/41048233875/job/124040698184)에 있다.

testcase는 두 checkpoint 설정을 `max`로 둔 뒤 `statdump -i 1`에서 `checkpoint`가 포함된 행을 `stat.log`에 저장한다. 동시에 Java 프로그램이 INSERT 부하를 실행한다. Java 종료 후 statdump를 종료하고 파일이 비어 있는지 검사한다. [실행과 검사 소스](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8c8aec181e56a12831fc7920fae12a59ae667af3/shell/_06_issues/_18_2h/cbrd_21737/cases/cbrd_21737.sh#L8-L72).

실제 `message.txt` 231~245행은 `[ -s stat.log ]`가 거짓이고 `write_nok 'stat.log is empty'`가 실행됐음을 보여준다. 비어 있었던 이유는 확인하지 못했다.

4번 검사의 OK를 실제 checkpoint 값이 0이었다는 증거로 사용하지 않는다. 소스 56행은 `awk '{print $3}' > stat_t.log /dev/null`이다. 입력은 `/dev/null`이며 이후 루프는 읽을 행이 없으면 `pass_flag=1`을 유지한다. 실행 로그 247~255행도 이 흐름을 보여준다. 이 별도 관찰은 3번 실패의 원인을 설명하지 않는다.

## 수집 오류와 보존된 자료

head와 merge-base 양쪽의 structured diagnostic은 다음과 같다.

```text
suite: test_sql
kind: integrity
diagnostic: identity_or_integrity
message: result identity mismatch: shard 01 workflow result and JUnit counts disagree
```

이 오류는 원격 응답을 보존한 뒤의 검증 단계에서 발생했다. 재수집이나 다른 경로로 검사를 우회하지 않았다. SQL shard `01`의 상대 경로 `shards/01/summary_info`와 `shards/01/linux_sql_64bit.xml`을 확인했다. 양쪽 실행에서 summary header와 JUnit testcase 수는 각각 3,531이었다. 그러나 수집기의 verdict 행 정규식으로 센 `:ok ...ms` 행은 3,533개였다. 어느 자료를 수정해야 하는지는 아직 확인하지 못했다. 이 값은 수집 오류를 조사하기 위한 raw 관찰이며 SQL 통과 집계가 아니다.

| 요청 | Suite | retained shard | failed acquisition | not_attempted |
| --- | --- | --- | --- | --- |
| head | medium | `00` | 없음 | 없음 |
| head | shell | `00`~`49` | 없음 | 없음 |
| head | SQL | `00`~`09` | 없음 | 없음 |
| merge-base | medium | `00` | 없음 | 없음 |
| merge-base | shell | `00`~`49` | 없음 | 없음 |
| merge-base | SQL | `00`~`09` | 없음 | 없음 |

`retained`는 응답 파일을 보존했다는 뜻이다. SQL suite의 검증 완료나 통과 판정을 뜻하지 않는다. acquisition ledger에는 전송 실패 endpoint나 실패 전 소비 byte 진단이 없다. 이번 장애는 위 두 파일의 count 대조 단계이며 전송 실패로 해석하지 않는다. binary 수집은 요청하지 않았고 소비량은 0 bytes이다. 예산 부족 때문에 이후 binary를 놓친 상태도 아니다.

## Merge-base 수집의 범위와 한계

기준 자료는 [40738391553, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/40738391553)에서 선택됐다. `collect-base`는 정확한 merge-base commit에 붙은 status와 check 링크를 페이지 전체에서 조회했다. 저장소 전체 workflow 검색은 하지 않았다. 선택 관계의 PR 번호와 head SHA는 독립적으로 수집한 head와 일치한다. 기준 observation `20261030T132502.902925315Z-5072-0`도 `incomplete`이다.

기준 medium·shell 요약의 schema, 실행 identity, 모든 raw 파일의 길이와 digest는 검증했다. 기준 medium은 975건 통과이고 shell은 3,459건 통과, 1건 실패, 30건 skip이다. public testcase는 `70db22a1c99dbbaa27fa1438c8967effdfcad551`, private testcase는 `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`이다.

head와 기준 모두 요청한 세 suite의 전체 검증을 마치지 못했다. 따라서 이번 보고서에서는 실패의 공유·추가·기준 전용 분류나 회귀 결론을 내리지 않는다. testcase revision과 CI helper 입력의 동등성도 확정하지 않았다. Chronicle 과거 이력 비교는 완전한 head 수집 검증 이후 단계로 남겼다. 과거 발생 여부와 flaky 여부는 미확인이다.

## 재현 가능한 검증과 다음 작업

각 명령은 한 번씩 실행했다. `--wait`, CI 재실행, 취소, 답글 게시, 코드 수정은 하지 않았다.

```bash
cubrid-ci status 8347 --json
cubrid-ci collect https://github.com/CUBRID/cubrid/pull/8347 --commit eac70c7e740d55b4623b46bb84797e8214dcdcc4 --json
cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/8347 --json
```

별도 validator로 head의 manifest/command v2와 observation v1, 기준의 manifest/command v3와 observation v2를 확인했다. medium·shell summary와 failure schema, 관찰 ID, 명령 결과 일치, build SHA, 실행·attempt, summary digest, raw 파일 길이·digest, 실패 파일 존재와 합계를 대조했다. head에서 medium 28개와 shell 616개 raw 파일을 확인했고 기준에서도 각각 같은 수를 확인했다.

`report_mode.py`의 결과는 `mode=warning`, `regression_conclusions_allowed=false`, `comparison_scope=none`이다. `Prove It Works` 원칙을 적용해 상태 표시 외에 실제 검사 조건과 기록된 값을 대조했다.

- [x] CI 종료 상태와 변경되지 않은 head를 확인한다.
- [x] head와 정확한 merge-base를 각 한 번 수집하고 보존한다.
- [x] 완료된 medium·shell 증거와 두 shell 실패 조건을 검증한다.
- [ ] SQL shard `01`의 추가 verdict 행 두 개와 JUnit 누락·필터 규칙을 조사한다. 수집기 parser와 결과 생성기 중 어느 쪽의 문제인지 먼저 확인한다.
- [ ] 별도 수정 절차로 count 불일치를 해결하고, 새 observation에서 요청한 전체 증거를 검증한다.
- [ ] 검증한 head를 바탕으로 testcase 입력 동등성, 정확한 기준 비교와 Chronicle 이력을 조사한다.
- [ ] 필요하면 같은 입력으로 원본과 R6을 비교하는 집중 재현을 별도 절차로 수행한다.

## 로컬 증거 위치

다음 경로는 이 분석 환경의 보존 위치다. 공유 독자는 위 CI 링크와 본문의 실제 관찰값으로 범위를 확인할 수 있다.

- 작업 기록은 `/home/vimkim/temp/pr8347-ci-analysis-20261030/`이다. `status.json`, `collect-result.json`, `base-result.json`, 두 exit 파일, `validation-result.json`, `assessment.json`, `report-mode.json`, `sql-count-diagnostic.json`을 보존했다. validator와 고정 revision 소스 사본도 이 경로에 있다.
- head bundle은 `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8347/eac70c7e740d55b4623b46bb84797e8214dcdcc4/`이다.
- 기준 bundle은 `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/`이다.
- 각 bundle의 `observations/<위 observation ID>/`가 이번 request/result를 보존한다. 완료된 요약은 `providers/github-actions/runs/<위 run ID>/attempts/1/<suite>/summary.json`이고 관련 raw index와 실패 파일은 같은 suite 디렉터리에 있다.

정확한 testcase의 네 소스 blob은 로컬에서 읽혔다. CI에서 실행된 `CTP/shell/init_path/init.sh`, `shell_utils.sh`, `cubrid` wrapper의 revision과 정확한 소스는 확정하지 못했다. `diff.txt`는 NOK 행을 추출한 자료이며 모든 출력 차이를 제공하는 자료는 아니다. 별도 로컬 재현과 binary 분석은 수행하지 않았다.
