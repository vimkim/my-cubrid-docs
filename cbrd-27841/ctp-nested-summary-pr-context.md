# CUBRIDQA-1693 PR 793 본문 개정 context

작성일: 2026-11-26, Asia/Seoul. PR 793 의 본문을 한국어로 다시 쓰고, QA 리뷰를 다시 요청하기 전에 검토받기 위한 기록이다. 게시할 본문은 [ctp-nested-summary-pr-body.md](ctp-nested-summary-pr-body.md) 다. 2026-10-30 승인본은 [CTP-nested-summary-pr-body_4f720bd_codex.md](CTP-nested-summary-pr-body_4f720bd_codex.md) 로 보존한다.

## Source와 대상

| 항목 | 값 |
| --- | --- |
| JIRA | [CUBRIDQA-1693](https://jira.cubrid.org/browse/CUBRIDQA-1693) (Task, Open, 담당 Daehyun Kim), [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841)과 Relates |
| 대상 PR | [CUBRID/cubrid-testtools#793](https://github.com/CUBRID/cubrid-testtools/pull/793), OPEN, draft |
| 작업 | 기존 PR 본문 update |
| 현재 제목 | `[CUBRIDQA-1693] Include nested SQL cases in result summaries` (변경 제안 없음) |
| head | `vimkim/cubrid-testtools:fix/sql-nested-summary-20261030`, `SOURCE_COMMIT` = `cdb0995fe2b6a45512e8d9dfc16ec3b43be3e95e` |
| 관측한 원격 head | `cdb0995fe2b6a45512e8d9dfc16ec3b43be3e95e` (2026-11-26 force-push 뒤, 사용자 승인) |
| base | `CUBRID/cubrid-testtools:develop`, `3c2e991` |
| 원래 본문 SHA-256 | `99ded0876d01a8ee47d471ed197059d20cf7875b421a0aa9fb5feaca30b75fda` (2026-10-30 승인본과 같음) |
| docs 브랜치 | `docs/cubridqa-1693-pr793-body` → `main` |

## 오늘 한 일 (2026-11-26)

- `4f720bd` 의 4개 커밋을 `origin/develop` `3c2e991` 위로 rebase 했다. 충돌은 없었다.
- #798 에 맞춰 `tests/sql-summary/` 만 고친 `cdb0995` 를 더했다. `write(Test, String, long, long)`, `linux_<type>_64bit_<buildtype>.xml`, `cubrid_rel` stub 배너, 정답 없는 case 의 `<skipped>` 기대.
- 사용자 승인 뒤 `git push --force-with-lease=...:4f720bd vk fix/sql-nested-summary-20261030` 를 했다. `code-style` run [45749697341](https://github.com/CUBRID/cubrid-testtools/actions/runs/45749697341) 성공.
- 사용자 승인 뒤 PR 에 rebase 설명 댓글을 올렸다: [issuecomment-7182200880](https://github.com/CUBRID/cubrid-testtools/pull/793#issuecomment-7182200880).

## 본문 주장의 근거

| 주장 | 근거 |
| --- | --- |
| `develop` testcase 의 중첩 case 19개, `cbrd-*` 디렉토리 7개 | `cubrid-testcases` `origin/develop` `ddd400460` (2026-11-26) 의 `git ls-tree`. `_05_bug_fix/cases/` 직접 `.sql` 42개, `cbrd-*/cases/` 아래 19개 |
| 3,557 대 3,538, `collection_failed` | [ci-analysis.md](../cbrd-26659/ci-analysis.md) 2026-11-25 snapshot, run 45578200568 |
| 3,533 대 3,531 | [SQL-summary-nested-category_1c6b224_codex.md](SQL-summary-nested-category_1c6b224_codex.md), [CBRD-26659 분석](../cbrd-26659/CBRD-26659-sql-count-discrepancy_20261030_run40837919358_codex.md) |
| #797 · #798 병합일 | GitHub `mergedAt`: #798 2026-11-05T18:14Z, #797 2026-11-06T07:22Z |
| `develop` writer 에 같은 분기 | `origin/develop` `JunitXmlWriter.walk()` 의 `if (TYPE_BOTTOM) ... else` |
| 시험 · 음성 대조 · Ant | 아래 검증 기록 |

## 검증 기록 (Java 8, `/usr/lib/jvm/java-1.8.0`)

| 대상 | 결과 |
| --- | --- |
| 원래 head `4f720bd` + 원래 시험 | 통과 |
| `cdb0995` source 모드 `./tests/sql-summary/run.sh` | `All SQL summary checks passed` |
| `cdb0995` 의 시험 + PR 의 `TestUtil` + `develop` 의 `walk()` | 실패: mixed JUnit 5 기대 · 3 실제, failures 1 · 0, skipped 1 · 0 |
| `cdb0995` 의 `CTP/build.xml` 전체 Ant 빌드 | `BUILD SUCCESSFUL` (임시 worktree, jar 는 커밋하지 않음) |
| 새로 만든 `cubridqa-cqt.jar` 로 `CTP_SQL_RUNTIME_JAR` 모드 | `All SQL summary checks passed` |
| `google-java-format` 1.7 (`.github/workflows/codestyle.sh`) | 한 줄 재배치만, 커밋에 포함 |

JDK 27 에서는 xstream 이 `java.util` 모듈 접근에 막혀 시험이 돌지 않는다. CI 는 Java 8 이다.

## 제안하는 게시 작업

1. PR 793 본문을 `ctp-nested-summary-pr-body.md` 내용으로 바꾼다. 제목과 draft 상태는 바꾸지 않는다.
2. (선택, 따로 승인 필요) PR 을 Ready for review 로 바꾸고 리뷰어를 요청한다. 후보: #797 · #798 작성자 `tw-kang`.

docs 통합(`main` rebase · fast-forward · push)은 Tier 1 규칙으로 이미 승인되어 있다.

## 게시 결과 (2026-11-26)

사용자 승인("1로 가자 ... 필요하면 다 진행해줘")으로 다음을 실행하고 재조회로 확인했다.

| 작업 | 결과 |
| --- | --- |
| CUBRIDQA-1693 을 [CUBRIDQA-1501](https://jira.cubrid.org/browse/CUBRIDQA-1501) 의 Sub-task 로 변환 | Type `Sub-task`, parent CUBRIDQA-1501, 담당자 유지 |
| CUBRIDQA-1693 설명 교체 | [my-cubrid-jira `issues/CUBRIDQA-1693-nested-sql-summary.md`](https://github.com/vimkim/my-cubrid-jira/blob/main/issues/CUBRIDQA-1693-nested-sql-summary.md) (`2e72f61`) 를 올림. 재조회 일치. 10-31 원본은 `issues/CUBRIDQA-1693-nested-sql-summary_4f720bd_codex.md` 로 보존 |
| CUBRIDQA-1693 Relates [CBRD-26659](https://jira.cubrid.org/browse/CBRD-26659) | 연결됨 |
| PR 793 본문 교체 | 원래 본문 SHA-256 이 기록값과 같음을 확인한 뒤 교체. 재조회 본문 SHA-256 `8daafb00c08cd6e88468331ba53d17aa85c8e3b69a891d2760826def57972f39` = 본문 파일 |
| PR 793 Ready for review, 리뷰 요청 | draft 해제, `tw-kang` 리뷰 요청. 제목은 바꾸지 않음 |

남은 일: 리뷰 · 병합 · runtime jar 배포 뒤 `test_sql` 재실행과 `cubrid-ci collect` 로 shard 01 이 3,557개로 맞는지 확인한다(work-tracker #879).
