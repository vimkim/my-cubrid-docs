<http://jira.cubrid.org/browse/CUBRIDQA-1693>

### Purpose

- 어떤 범주(디렉토리)에 직접 case 와 하위 범주가 함께 있으면, CTP 의 SQL 결과 요약과 JUnit XML 이 하위 범주의 case 를 빠뜨린다. 실행은 했고 `summary_info` 에도 있는데 JUnit 에는 없다.
- 지금 `develop` testcase 에 이런 case 가 19개 있다. 모두 `sql/_05_plcsql/_01_testspec/_05_bug_fix/cbrd-*/cases/` 아래다. `_05_bug_fix/cases/` 에 직접 case 가 있어서 그 아래 `cbrd-*` 디렉토리 7개가 빠진다.
- 그래서 gha-ci 의 `test_sql` 은 실행할 때마다 shard 01 의 JUnit 이 `summary_info` 보다 19개 적다(3,538 대 3,557). `cubrid-ci collect` 는 이것을 무결성 오류로 보고 `test_sql` 결과 전체를 버린다. 엔진 PR 의 SQL 결과를 검증된 수로 비교할 수 없다.
- 빠진 case 가 실패해도 JUnit 에는 `<failure>` 가 남지 않는다. JUnit 만 읽는 실패 목록과 결과 화면은 그 실패를 놓친다.
- `_05_bug_fix/` 에 `cbrd-*` TC 가 더해질 때마다 빠지는 case 도 는다. 10월 말 2개였고 지금은 19개다.
- AS-IS: 직접 case 가 있는 범주에서 순회가 멈춘다. 하위 범주의 case 가 요약 수와 JUnit 에서 빠진다.
- TO-BE: 실행한 모든 case 가 요약 수와 JUnit 에 정확히 한 번씩 나온다. JUnit 의 `tests` 가 `summary_info` 의 총수와 같다.

### Implementation

운영 코드는 두 파일이다.

- `JunitXmlWriter.walk()`: 범주의 직접 case 를 쓴 뒤 하위 범주도 이어서 돈다. 전에는 두 일이 `if`/`else` 로 갈려 있어서 직접 case 가 있으면 하위 범주를 건너뛰었다. #798 이 writer 를 `common` 으로 옮길 때 이 분기는 그대로 남았다.
- `TestUtil.makeSummary()`: 범주 트리를 한 번 돌며 수 · 시간 · 하위 링크를 새로 계산한다. 범주의 합은 직접 case 와 모든 하위 범주의 합이다. 디렉토리가 직접 가진 case 목록과 그룹 합계를 따로 둔다. 요약을 다시 만들어도 수가 겹쳐 더해지지 않는다.
- `getCatPath()`: 경로를 `/+` 로 나눈다. `//` 가 빈 범주를 만들지 않는다.
- 결과 디렉토리, `summary_info` 의 위치, SQL · medium 의 직렬화 계층은 바뀌지 않는다.
- `tests/sql-summary/`: DB 없이 실제 CTP 클래스로 범주 트리를 만들고 요약 · `summary_info` · JUnit 을 비교하는 회귀 시험이다. 실행: `./tests/sql-summary/run.sh` (Java 8).

### Remarks

#### 왜 지금 다시 요청하는가

- 2026-10-30: PR [#8128](https://github.com/CUBRID/cubrid/pull/8128) · [#8347](https://github.com/CUBRID/cubrid/pull/8347) 의 CI 에서 SQL shard 01 이 `summary_info` 3,533 · JUnit 3,531 이었다([#8128 run 40837919358](https://github.com/CUBRID/cubrid/actions/runs/40837919358), [#8347 run 41048233875](https://github.com/CUBRID/cubrid/actions/runs/41048233875)). 빠진 2개는 `_05_bug_fix/cbrd-27556/cases/` 에 있었다. 원인을 찾아 이 PR 을 draft 로 열고 CUBRIDQA-1693 을 만들었다.
- 이 PR 은 draft 로 남아 리뷰를 받지 못했다. 그사이 2026-11-05 · 11-06 에 #798 · #797 이 JUnit writer 를 `common` 으로 옮겼다. 이 결함이 든 `walk()` 분기도 같이 옮겨졌다.
- 같은 기간 `_05_bug_fix/` 아래 `cbrd-*` TC 가 7개 디렉토리로 늘었다. 2026-11-25 PR #8128 의 [run 45578200568](https://github.com/CUBRID/cubrid/actions/runs/45578200568) 에서 `test_sql` 이 `collection_failed` 였다. shard 01 의 JUnit 이 19개를 빠뜨렸다(`summary_info` 3,557 · JUnit 3,538). 이 PR 이 들어가기 전에는 다음 `test_sql` 도 같은 이유로 수집되지 않는다.
- 2026-11-26: 이 PR 을 현재 `develop`(`3c2e991`) 위로 rebase 했다. 충돌은 없었다. #798 에 맞춰 시험만 고쳤다(`cdb0995`). 새 `write()` 시그니처, build type 이 붙은 파일 이름(`linux_sql_64bit_release.xml`), 정답 없는 case 의 `<skipped>` 를 따른다.

#### 검증 (`cdb0995`, Java 8)

- `./tests/sql-summary/run.sh` 가 통과한다. 직접 case · 하위 · 손자 범주가 섞인 트리, 순서를 뒤집은 트리, 다시 만든 요약, 정답 없는 case, 결과 없는 모드, SQL · medium 직렬화 계층을 본다.
- 음성 대조: 같은 시험을 `develop` 의 `walk()` 로 돌리면 실패한다. 섞인 트리에서 JUnit case 는 5개 기대 · 3개 실제, `<failure>` 는 1개 기대 · 0개 실제다. 하위 범주의 실패가 JUnit 에서 사라진다.
- `CTP/build.xml` 의 전체 Ant 빌드가 성공한다. 새로 만든 `cubridqa-cqt.jar` 로도 같은 시험이 통과한다.
- rebase 전(`4f720bd`)에는 실제 run 에서 보관한 3,533개 경로 · 판정 · 시간으로 보고서를 다시 만들었다. 요약 · JUnit · 판정 행이 모두 3,533개였다. SQL 을 다시 실행한 것은 아니다.

#### 리뷰 포인트와 남은 확인

- SQL 과 medium 이 같은 생성기를 쓴다. 결과 디렉토리와 `summary_info` 위치가 그대로인지 봐 주면 좋겠다.
- 실제 CI 로는 아직 확인하지 않았다. 병합과 runtime jar 배포 뒤 `test_sql` 을 돌려 shard 01 의 JUnit 이 `summary_info` 와 같은 3,557개인지 확인한다.
- runtime jar(`CTP/sql/lib/cubridqa-cqt.jar`)는 이 PR 에서 바꾸지 않는다. 병합 뒤 배포 커밋이 만든다.
