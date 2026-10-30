# PR 8348 CI 증거 수집 경고와 shell 실패 관찰

R5 작성자와 리뷰어가 [PR 8348](https://github.com/CUBRID/cubrid/pull/8348)의 shell 실패 한 건을 이해하고 다음 검증을 결정하도록 현재 증거를 보존한다. 분석일은 2026-10-30, Asia/Seoul이다.

**전체 증거 수집이 불완전하므로 이 CI 자료만으로 회귀 여부나 근본 원인을 결론 내릴 수 없다.** head와 merge-base 양쪽에서 SQL shard `01`의 workflow 결과와 JUnit 집계가 달라 수집기가 exit `4`로 종료됐다. 같은 오류가 [R6 PR 8347의 분석](../cbrd-27841/ci_analysis_report_eac70c7_codex.md)에도 있다. 이 보고서에는 검증한 medium·shell 결과와 shell 실패의 실제 검사 조건만 기록한다. 과거 이력과 로컬 반복 실행은 별도 문서인 [shell 실패 조사](CBRD-27858-enhance-10010-shell-failure_6288576_claude.md)에 둔다.

## 대상과 관찰 결과

- 엔진 저장소는 `CUBRID/cubrid`, head는 `628857607265880ef7bbdda4973b1b6f06e8b797`이다.
- 대상 브랜치는 `feature/oos-merge`이다. 조회한 target tip과 정확한 merge-base는 모두 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`이다.
- head 실행은 [41050496911, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/41050496911)이다. suite 상태는 2026-10-30 21:57 KST에 보고됐고, 22:28 KST 수집 시점에 전체 실행은 `completed / failure`였다.
- 수집기는 `cubrid-ci 0.2.0 (dd290e9f7b9b, release)`이다. 사전 `doctor` 검사는 정상이다.
- head 수집 시각은 `2026-10-30T13:28:14.614870239Z`, observation은 `20261030T132755.389974820Z-291154-0`이다. 결과는 `incomplete`이다.

| Suite | GitHub 상태 | 수집 상태 | 검증한 집계 |
| --- | --- | --- | --- |
| `test_medium` | SUCCESS | completed | 계획 975, 실행 975, 통과 975, 실패 0, 오류 0, skip 0, 미실행 0 |
| `test_shell` | FAILURE | completed | 계획 3,490, 실행 3,460, 통과 3,459, 실패 1, 오류 0, skip 30, 미실행 0 |
| `test_sql` | SUCCESS | collection_failed | 집계 미검증. GitHub의 SUCCESS를 검증된 testcase 집계로 대체하지 않는다. |

release·debug 빌드는 GitHub 상태에서 모두 SUCCESS이다. 세 테스트 suite는 debug 엔진 `628857607`을 사용했다. 검증한 medium testcase revision은 `683bf41f9747250f615f23577cc62c1a4c4c17cf`이다. shell 50개 shard의 testcase revision은 모두 `a0b3bb729263cee95431542322301505121c3621`(`tc/pr-8348`)이다. 이 revision은 feature 기준 `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`에 자동 생성 커밋 하나를 더한 것이다.

## 완료된 shell 증거에서 확인한 실패

정확한 경로는 `shell/_35_cherry/issue_21654_server_side_loaddb/loaddb_CS/_01_utility/_17_loaddb/_enhance_10010/cases/_enhance_10010.sh`이다. 실패는 [shell shard 46](https://github.com/CUBRID/cubrid/actions/runs/41050496911/job/124048363072)에 있고 실행 시간은 8.581초이다. failure metadata, `message.txt`, 추출된 `diff.txt`가 있다. 10개 검사 중 4번만 NOK이고 나머지는 OK로 기록됐다.

testcase 소스는 `a0b3bb7`의 Git object에서 읽었다. 로컬 소스와 testcase worktree는 변경하지 않았다. testcase는 `bit(6)` 열을 가진 테이블에 loaddb로 행을 넣고, 잘못된 bit 상수를 넣을 때의 오류 메시지를 검사한다. 4번 검사는 닫는 따옴표가 앞에 붙은 `1 Xa0'` 행을 `cubrid loaddb -C`로 넣은 뒤 `err.log`에 `syntax error`가 한 줄 이상 있는지 본다. [실행과 판정 소스](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/a0b3bb729263cee95431542322301505121c3621/shell/_35_cherry/issue_21654_server_side_loaddb/loaddb_CS/_01_utility/_17_loaddb/_enhance_10010/cases/_enhance_10010.sh#L54-L61).

실제 `message.txt` 176~184행은 다음 흐름을 보여준다. 여기서는 로그의 행만 간추렸다.

```text
+ cubrid loaddb --no-user-specified-name -C -d en10_objects3 -udba en10
++ grep 'syntax error' err.log
+ '[' 0 -ge 1 ']'
+ write_nok
_enhance_10010-4 : NOK
```

`err.log`의 실제 내용은 CI 증거에 남아 있지 않다. 그래서 loaddb가 다른 오류를 냈는지, 메시지를 내지 않았는지, 실행 자체가 실패했는지는 이 자료로 구분할 수 없다. 바로 앞의 3번(`domain conflict`)과 바로 뒤의 5번(`syntax error`) 검사는 OK였다.

## 수집 오류와 보존된 자료

head와 merge-base 양쪽의 structured diagnostic은 다음과 같다.

```text
suite: test_sql
kind: integrity
diagnostic: identity_or_integrity
message: result identity mismatch: shard 01 workflow result and JUnit counts disagree
```

이 오류는 원격 응답을 보존한 뒤의 검증 단계에서 발생했다. 재수집이나 다른 경로로 검사를 우회하지 않았다. R6 분석은 같은 merge-base 실행의 SQL shard `01`에서 이 불일치를 조사하기 시작했다. 이번 head 실행의 SQL raw 파일은 따로 대조하지 않았다.

| 요청 | Suite | retained shard | failed acquisition | not_attempted |
| --- | --- | --- | --- | --- |
| head | medium | `00` | 없음 | 없음 |
| head | shell | `00`~`49` | 없음 | 없음 |
| head | SQL | `00`~`09` | 없음 | 없음 |
| merge-base | medium | `00` | 없음 | 없음 |
| merge-base | shell | `00`~`49` | 없음 | 없음 |
| merge-base | SQL | `00`~`09` | 없음 | 없음 |

`retained`는 응답 파일을 보존했다는 뜻이다. SQL suite의 검증 완료나 통과 판정을 뜻하지 않는다. 전송 실패 endpoint나 실패 전 소비 byte 진단은 없다. binary 수집은 요청하지 않았고, 설정된 예산 536,870,912 bytes 중 소비량은 0 bytes이다.

## Merge-base 수집의 범위와 한계

기준 자료는 [40738391553, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/40738391553)에서 선택됐다. `collect-base`는 정확한 merge-base commit에 붙은 status와 check 링크를 페이지 전체에서 조회했다. 저장소 전체 workflow 검색은 하지 않았다. 선택 관계의 PR 번호와 head SHA는 독립적으로 수집한 head와 일치한다. 기준 observation `20261030T133010.109333866Z-396863-0`도 `incomplete`이다.

기준 medium은 975건 통과이다. 기준 shell은 3,459건 통과, 1건 실패, 30건 skip이다. 기준의 유일한 shell 실패는 다른 loaddb testcase인 `shell/_01_utility/_19_loaddb_parameter/parameter_combine/cases/parameter_combine.sh`의 2번 검사이다. 기준 shell testcase revision은 `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`이고, `_enhance_10010` 디렉터리는 head의 `a0b3bb7`과 Git 내용이 같다. 기준 실행에서 `_enhance_10010`은 실패 목록에 없다.

head와 기준 모두 요청한 세 suite의 전체 검증을 마치지 못했다. `report_mode.py`의 결과는 `mode=warning`, `regression_conclusions_allowed=false`, `comparison_scope=none`이다. 따라서 이 보고서는 실패를 공유·추가·기준 전용으로 분류하지 않고 회귀 결론도 내리지 않는다.

## 재현 가능한 검증과 다음 작업

각 수집 명령은 한 번씩 실행했다. `--wait`, CI 재실행, 취소, 답글 게시, 코드 수정은 하지 않았다.

```bash
cubrid-ci status 8348 --json
cubrid-ci collect https://github.com/CUBRID/cubrid/pull/8348 --commit 628857607265880ef7bbdda4973b1b6f06e8b797 --json
cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/8348 --json
```

head의 manifest/command v2와 observation v1, 기준의 manifest/command v3와 observation v2를 schema로 검증했다. 관찰 ID, 저장된 명령 결과와 observation의 일치, build SHA, 실행·attempt, medium·shell summary와 failure schema, 합계를 대조했다. head와 기준에서 medium raw 28개와 shell raw 616개의 길이와 SHA-256이 모두 index와 일치했다.

- [x] CI 종료 상태와 변경되지 않은 head를 확인한다.
- [x] head와 정확한 merge-base를 각 한 번 수집하고 보존한다.
- [x] 완료된 medium·shell 증거와 shell 실패 조건을 검증한다.
- [x] 과거 이력과 로컬 반복 실행은 별도 문서에서 조사한다.
- [ ] SQL shard `01`의 count 불일치를 수집기와 결과 생성기 중 어느 쪽에서 고칠지 확인한다. R6 분석의 후속 작업과 함께 다룬다.
- [ ] 수정 뒤 새 observation에서 요청한 전체 증거를 검증하고, 정확한 기준 비교를 다시 판단한다.

## 로컬 증거 위치

다음 경로는 이 분석 환경의 보존 위치다. 공유 독자는 위 CI 링크와 본문의 관찰값으로 범위를 확인할 수 있다.

- 작업 기록은 `/home/vimkim/temp/pr7990-hornet-review-20261029/r5/ci8348-enhance10010/analysis/`이다. `status.json`, `result.json`, `base.json`, `assessment.json`, `report-mode.json`, `exits.txt`와 Chronicle 조회 결과를 보존했다.
- head bundle은 `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8348/628857607265880ef7bbdda4973b1b6f06e8b797/`이다.
- 기준 bundle은 `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/`이다.
- 각 bundle의 `observations/<위 observation ID>/`가 이번 request/result를 보존한다. 완료된 요약은 `providers/github-actions/runs/<위 run ID>/attempts/1/<suite>/summary.json`이고, raw index와 실패 파일은 같은 suite 디렉터리에 있다.

CI에서 실행된 `CTP/shell/init_path/init.sh`, `shell_utils.sh`, `cubrid` wrapper의 revision은 확정하지 못했다. `diff.txt`는 NOK 행을 추출한 자료이며 모든 출력 차이를 제공하지 않는다.
