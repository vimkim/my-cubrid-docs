<http://jira.cubrid.org/browse/CUBRIDQA-1771>

### Purpose

- #793(CUBRIDQA-1693)은 SQL · medium 결과 요약의 수, `summary_info`, JUnit XML 을 검사하는 오프라인 회귀 시험 `tests/sql-summary/run.sh` 를 더한다. 그러나 이 저장소의 PR CI 는 `code-style` 검사만 돌리고, 이 시험은 아무 CI 도 실행하지 않는다.
- 그래서 #798 이 JUnit writer 를 `common` 으로 옮겨 이 시험의 컴파일을 깨뜨렸을 때 아무 check 도 실패하지 않았다. #793 을 rebase 할 때에야 드러났다.
- 이 PR 은 이 시험을 PR CI 에서 실행한다. CTP 의 결과 요약이나 JUnit 출력을 바꾸는 PR 이 시험을 깨뜨리면 그 PR 의 check 가 실패한다.

### Implementation

- `.github/workflows/check.yml`(`github-checks`)에 `sql-summary` job 을 더한다. `develop` · `feature/**` 대상 PR 에서 Temurin Java 8 로 `bash tests/sql-summary/run.sh` 를 실행한다.
- 새 workflow 파일 대신 기존 workflow 에 job 을 더했다. 트리거가 `code-style` 과 같고, PR check 를 한 workflow 에 모아 두는 편이 찾기 쉽다. job 은 서로 독립이라 `code-style` 의 동작은 바뀌지 않는다.
- action 은 현재 유지되는 major 인 `actions/checkout@v7` · `actions/setup-java@v6` 을 쓴다. `code-style` 이 쓰는 `checkout@v2` · `setup-java@v3` 는 actionlint 가 runner 가 너무 오래되었다고 경고한다. 배포판은 `adopt` 대신 `temurin` 이다. AdoptOpenJDK 는 Eclipse Temurin 으로 옮겨 더 갱신되지 않는다.
- 시험은 데이터베이스 없이 CTP 소스 일부를 컴파일해 돌린다. 배포된 jar 에 기대지 않으므로 PR 의 소스 변경이 바로 검사된다. `timeout-minutes: 10` 을 둔다.
- 시스템 JDK 17 이상에서는 xstream 의 module 접근 제한으로 시험이 실패하므로 Java 8 을 쓴다.

### Remarks

- 이 PR 은 #793 에 의존한다. 시험 파일이 #793 에 있어서, #793 이 머지될 때까지 이 PR 의 diff 에는 #793 의 커밋이 함께 보인다. #793 이 머지되면 `develop` 위로 rebase 하여 이 PR 의 커밋만 남긴다.
- 머지 순서: #793 → 이 PR. 이 PR 을 먼저 머지하면 `develop` 에 시험 파일이 없어 다른 PR 의 `sql-summary` check 가 실패한다.
- jar 는 바뀌지 않는다. workflow 파일만 바뀐다.
- #793 head `cdb0995` 위에서 Java 8(`1.8.0`)로 확인한 결과는 다음과 같다.

| 검사 | 결과 |
| --- | --- |
| 수정하지 않은 소스 | 통과(`All SQL summary checks passed`, 종료 코드 0, 약 11초) |
| `JunitXmlWriter.write()` 에 인자를 더해 #798 과 같은 API 변경을 흉내 냄 | `javac` 컴파일 오류, 종료 코드 1 |
| `Summary.getTotalCount()` 가 1 을 더 돌려주게 바꿈 | 검사 17개 실패, 종료 코드 1 |
| actionlint 1.7.12 | 새 job 에 경고 없음. 기존 `code-style` 의 오래된 action 경고 2건만 남는다 |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
