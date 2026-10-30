# CBRD-26659 SQL 결과 2건 집계 누락 분석

작성일: 2026-10-30, Asia/Seoul. 분석 대상은 [PR #8128](https://github.com/CUBRID/cubrid/pull/8128)의 [CI 40837919358](https://github.com/CUBRID/cubrid/actions/runs/40837919358), attempt 1이다. 독자는 TC 검토자와 CI·CTP 담당자다.

## 결론과 판정 범위

SQL shard 01의 workflow 3,533개와 JUnit 3,531개 차이는 **CTP의 중첩 디렉터리 결과 집계 누락으로 재현된다.** 직접 TC와 하위 TC 디렉터리가 함께 있는 경로에서 합계 순회가 하위 TC를 건너뛴다. 텍스트 저장은 하위 TC까지 방문하므로 workflow의 행 단위 집계와 합계·JUnit이 달라진다.

실제 CTP 리비전의 클래스로 DB 없이 같은 차이를 재현했다. 디렉터리 배치만 바꾼 대조군은 모든 결과를 집계했다. 이는 CTP 집계 결함의 증거이며, Engine 회귀나 원래 두 TC의 실행 누락을 입증한 결과는 아니다.

**기존 SQL 수집 결과는 여전히 `collection_failed`다.** 수집기의 무결성 검사를 완화하지 않았고 SQL 전체 PASS를 인증하지 않는다. 원래 두 TC의 전체 실행·답안 비교·정상 종료를 독립적으로 대조할 상세 로그도 이번 분석에는 없다. CI 재실행이나 엔진·TC·CTP 수정은 하지 않았다.

## 리비전과 보관 자료

| 대상 | 고정 리비전 |
| --- | --- |
| 분석한 Engine | `e3589ae42d42b04eb020e1ae43e165b01d31b12a` |
| 실행된 workflow | `4f1a68c1ebec12f29bc8ba98b5ce8cacb1fc8735` |
| SQL testcase | `45e21ad799d82ebadc04a93c7d2f69517d53bf39` |
| 실행된 CTP | `ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2` |

보관한 run metadata와 `collect.log`로 workflow와 CTP 리비전을 확인했다. Workflow는 `develop`의 정의이며 테스트한 Engine SHA와 구분한다. `cubrid-ci 0.2.0 (dd290e9f7b9b, release)`의 수집 관측 `20261029T093825.454621843Z-1423871-0`을 사용했다. 현재 상태 조회에서도 PR head는 같은 Engine SHA다. 새 수집으로 과거 자료를 대체하지 않았다.

수집 결과·manifest·관측 request·관측 result의 네 JSON schema와 결과·관측 일치를 검사했다. SQL 10개 shard의 acquisition 상태는 모두 `retained`이며, 50개 저장 파일의 크기와 SHA-256이 receipt와 일치한다. SQL summary와 raw index는 무결성 실패로 생성되지 않았다. `retained`는 자료 보관을 뜻하며 suite 판정 완료를 뜻하지 않는다.

## XML에 빠진 두 경로

두 경로의 공통 디렉터리는 `sql/_05_plcsql/_01_testspec/_05_bug_fix/cbrd-27556/cases/`다.

| 파일 | 보관된 텍스트 결과 | XML |
| --- | --- | --- |
| `33_static_sql_group_by_having_alias.sql` | `:ok 503ms` | 없음 |
| `33_static_sql_group_by_having_alias_error.sql` | `:ok 34ms` | 없음 |

`summary_info` 974–980행에는 `total:0`, `success:0`, `fail:0`, `totalTime:0ms`, `SiteRunTimes:0times` 다음에 위 두 `:ok` 행이 있다. Shard 전체에는 중복 없는 텍스트 결과 3,533개와 XML testcase 3,531개가 있다. XML에 없는 텍스트 경로는 위 두 개뿐이며 XML에만 있는 경로는 없다. 다른 9개 shard는 행 수와 XML 수가 일치한다. 전체 할당 합계는 17,655개, XML testcase 합계는 17,653개다. 인증된 전체 PASS 건수로 사용하지 않는다.

고정 TC 트리에는 두 SQL과 답안이 있고 상위 `_05_bug_fix/cases`에도 직접 TC가 있다. 해당 `cbrd-27556` Git 트리에는 과거 결과 파일이 없다. 이것만으로 호스트의 모든 과거 파일을 배제할 수는 없지만, 과거 결과나 수집 시점 혼합 없이 같은 증상이 생김을 다음 재현에서 확인했다.

## 합계와 텍스트 저장의 순회가 다르다

`ConsoleBO.build()`는 TC가 있는 각 디렉터리에 `Summary.TYPE_BOTTOM`을 만든다. `TestUtil.getCatMap()`이 구성한 중첩 map에서 `_05_bug_fix`에는 직접 TC의 `Summary`와 `cbrd-27556` 하위 map이 함께 존재한다. [ConsoleBO.java 400–427행](https://github.com/CUBRID/cubrid-testtools/blob/ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2/CTP/sql/src/com/navercorp/cubridqa/cqt/console/bo/ConsoleBO.java#L400-L427), [TestUtil.java 877–894행](https://github.com/CUBRID/cubrid-testtools/blob/ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2/CTP/sql/src/com/navercorp/cubridqa/cqt/console/util/TestUtil.java#L877-L894).

`TestUtil.makeSummary()`는 현재 map에 `SUMMARY_KEY`가 없을 때만 하위 map을 재귀 방문한다. 직접 TC의 `Summary`가 있으면 자체 case list만 더하고 하위 map은 방문하지 않는다. 이 지점에서 하위 TC 합계와 aggregate tree 연결이 빠진다. [TestUtil.java 490–601행](https://github.com/CUBRID/cubrid-testtools/blob/ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2/CTP/sql/src/com/navercorp/cubridqa/cqt/console/util/TestUtil.java#L490-L601).

이후 출력이 갈린다.

- `saveResult()`는 원래 category map을 재귀 방문한다. 하위 합계가 0이어도 `Summary.toString()`은 개별 case list를 기록한다. [TestUtil.java 679–706행](https://github.com/CUBRID/cubrid-testtools/blob/ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2/CTP/sql/src/com/navercorp/cubridqa/cqt/console/util/TestUtil.java#L679-L706), [Summary.java 99–143행](https://github.com/CUBRID/cubrid-testtools/blob/ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2/CTP/sql/src/com/navercorp/cubridqa/cqt/console/bean/Summary.java#L99-L143).
- `JunitXmlWriter.walk()`는 aggregate tree를 순회한다. `TYPE_BOTTOM`에서는 직접 case list만 내보내므로 하위 TC가 XML에 나타나지 않는다. [JunitXmlWriter.java 122–173행](https://github.com/CUBRID/cubrid-testtools/blob/ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2/CTP/sql/src/com/navercorp/cubridqa/cqt/console/util/JunitXmlWriter.java#L122-L173).
- Workflow `COUNT_RESULTS`는 `summary_info`의 `:ok`, `:nok` 행을 센다. `total:` 합계나 XML을 사용하지 않아 하위 두 행도 포함한다. 실제 함수를 보관 자료에 적용하면 `exec=3533 pass=3533`이 재현된다. [gha-ci.yml 116–128행](https://github.com/CUBRID/cubrid/blob/4f1a68c1ebec12f29bc8ba98b5ce8cacb1fc8735/.github/workflows/gha-ci.yml#L116-L128).

## 실제 클래스의 재현과 대조군

격리한 Git cache에 정확한 CTP commit을 받고 임시 archive에서 실제 클래스를 컴파일했다. Bundled library, `ant compile`, JDK `1.8.0_462`를 사용했다. 기존 CTP checkout의 다른 HEAD나 미커밋 변경은 사용하지 않았다.

실험은 실제 `Test`, `CaseResult`, `Summary`, `TestUtil.getCatMap()`, `makeSummary()`와 `JunitXmlWriter.walk()`를 호출한다. Writer의 private 순회는 reflection으로 호출한다. 입력은 결과를 가정해 넣은 메모리 객체다. DB를 시작하거나 SQL을 실행하지 않는다.

| 입력 구조 | 결과 객체 | aggregate 합계 | JUnit 대상 | 하위 합계 | 3개 보존 검사 |
| --- | --- | --- | --- | --- | --- |
| `parent/cases` 1개와 `parent/nested/cases` 2개 | PASS 3개 | 1 | 1 | 0 | exit 1 |
| `parent/direct/cases` 1개와 `parent/nested/cases` 2개 | 동일 PASS 3개 | 3 | 3 | 2 | exit 0 |

혼합 구조의 하위 `Summary.toString()`에는 원본처럼 합계 0과 두 `:ok` 행이 함께 나온다. 디렉터리 배치만 바꾼 대조군은 모두 집계된다. 하위 객체를 FAIL 2개로 바꾼 대조에서도 aggregate와 JUnit의 같은 누락을 확인했다. 이는 보고서 순회 실험이며 workflow가 FAIL을 우회한다는 주장은 아니다. Workflow는 텍스트의 `:nok`도 별도로 센다.

[analyze-sql-count-discrepancy.py](tools/analyze-sql-count-discrepancy.py)는 관측·receipt 검증, 실제 workflow 함수 재실행, 10개 shard 경로 대조와 네 Java 대조 실험을 수행한다. [NestedSummaryProbe.java](tools/NestedSummaryProbe.java)는 CTP 알고리즘을 복제하지 않고 실제 클래스를 호출한다. 두 파일은 본 분석을 다시 확인하는 데 필요하므로 Git에 보존한다. 원본 자료·source archive·build·로그는 Git 밖에 둔다.

Python 3.12 이상, `jsonschema`, Git, Ant와 JDK가 필요하다. 문서 repository 루트에서 실행한다.

```bash
python3 -B cbrd-26659/tools/analyze-sql-count-discrepancy.py \
  --bundle /home/vimkim/temp/cbrd-26659-heavy-20261029/publication-01/ci-evidence-full/github-actions/CUBRID-cubrid/pr-8128/e3589ae42d42b04eb020e1ae43e165b01d31b12a \
  --collector-result /home/vimkim/temp/cbrd-26659-heavy-20261029/publication-01/ci-evidence-full-result.json \
  --engine-git /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover \
  --testcase-git /home/vimkim/gh/cubrid-testcases/develop \
  --ctp-git /home/vimkim/temp/cbrd-26659-sql-count-20261030/ctp.git
```

도구의 exit 0은 **집계 결함과 대조군의 재현 성공**을 뜻한다. `collector_sql_state`는 `collection_failed`, `suite_success_certified`는 `false`로 유지된다. Compilation은 임시 archive에서만 수행하며 제공한 Git repository와 보관 자료를 수정하지 않는다.

## 남은 확인과 후속 작업

집계 결함 자체의 확신도는 높다. 실제 리비전의 코드와 독립된 새 객체에서 증상을 재현했고 원본의 경로 구조·두 개의 차이·하위 합계 0이 일치한다. 다른 구조에서도 누락이 생기거나 혼합 구조 대조가 누락 없이 통과하면 현재 원인 설명을 재검토한다.

`shouldRun`은 실행 대상 여부이며 완료 증표가 아니다. `CaseResult`의 성공·실행 대상 기본값은 모두 true다. 원본의 503ms·34ms는 실행을 뒷받침하지만 개별 완료·답안 비교 로그를 대조하지 않았으므로 두 TC의 완전한 PASS를 새로 인증하지 않는다. [CaseResult.java 61–65행](https://github.com/CUBRID/cubrid-testtools/blob/ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2/CTP/sql/src/com/navercorp/cubridqa/cqt/console/bean/CaseResult.java#L61-L65), [ConsoleBO.java 1283–1294행](https://github.com/CUBRID/cubrid-testtools/blob/ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2/CTP/sql/src/com/navercorp/cubridqa/cqt/console/bo/ConsoleBO.java#L1283-L1294).

이번 자료로 Engine PR의 회귀·원인을 귀속하지 않는다. Engine merge-base 비교와 TC 실패 역사 조회는 집계 결함 재현의 범위 밖이다. `/entrypoint.sh results`의 원본 결합 구현과 호스트의 과거 파일 잔존 여부도 이번에 검증하지 않았다.

별도 CTP 수정에서 직접 TC와 하위 TC를 모두 순회하도록 요약 구조의 계약을 고치고 aggregate·텍스트·JUnit의 경로와 개수를 함께 검증해야 한다. 합계 숫자만 보정하거나 수집기 검사를 완화하면 누락을 가린다. 수정 후 해당 두 TC의 실행 근거와 SQL 전체 자료 정합성을 확인해야 한다. 수리와 새 CI 실행은 아직 수행하지 않았다.

[TODO checklist](CBRD-26659-todo-checklist_20261029_codex.md)에 원인 조사 완료와 CTP 수리·SQL 증거 재검증 미완료를 구분한다. 다음 TC 분류 작업은 비활성 SQL 3개의 120초 제한 재현이다.
