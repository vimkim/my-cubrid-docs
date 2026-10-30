# CTP 중첩 범주 집계 수정 게시 기록

2026-10-31, Asia/Seoul. PR 8347의 SQL 증거 수집을 막은 공통 CTP 결함을 별도 회사 리뷰로 넘긴 기록이다. [원인·검증 분석](SQL-summary-nested-category_1c6b224_codex.md)과 [게시한 PR 본문](CTP-nested-summary-pr-body_4f720bd_codex.md)은 승인 당시 내용을 보존한다. 분석에 남은 발급·게시 전 문구는 2026-10-30 시점의 상태이며, 실제 게시 결과는 이 문서를 따른다.

| 항목 | 실제 결과 |
| --- | --- |
| JIRA | [CUBRIDQA-1693](https://jira.cubrid.org/browse/CUBRIDQA-1693), `[CTP] 중첩 SQL 범주의 결과 집계 누락` |
| 유형·관계 | 독립 `Task`, parent 없음, [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841)과 `Relates` |
| 담당자 | 생성 요청에는 지정하지 않았다. 서버가 `hikwon`을 기본 담당자로 지정했으며 변경하지 않았다. |
| 회사 PR | [CUBRID/cubrid-testtools #793](https://github.com/CUBRID/cubrid-testtools/pull/793), draft |
| base | `CUBRID/cubrid-testtools:develop`, 생성 시 `1c6b224d6f48eea01b8b4efa9f64f2521c40f2fd` |
| head | `vimkim/cubrid-testtools:fix/sql-nested-summary-20261030`, `4f720bd2edb9bf8020760f30d4a6a9088dff02b1` |
| 변경 | 4개 커밋, 생성기 소스 2개와 회귀 도구 2개. 추적 중인 runtime JAR은 변경하지 않았다. |
| PR 본문 | 재조회한 본문이 승인 파일과 바이트 단위로 일치한다. SHA-256: `99ded0876d01a8ee47d471ed197059d20cf7875b421a0aa9fb5feaca30b75fda` |

## 게시와 링크 보정

사용자는 문서·티켓 노트의 개인 저장소 `main` 통합·push, 독립 CUBRIDQA Task 발급, 검증한 source의 개인 fork push와 회사 draft PR 생성을 승인했다. 문서는 동시에 진행된 R5 기록을 보존하며 최신 `main` 위로 rebase했고, 첫 게시를 `cb836700a46b6f859e82377b0fe087ba22f490b9`에서 확인했다. PR 생성에는 사용 가능한 GitHub connector를 사용했다.

JIRA 생성 본문은 승인한 분석 파일과 같았다. 이후 노트 저장소의 링크 검사에서 두 상대 링크가 해당 위치에서 열리지 않음을 발견했다. 문장과 검증 결과를 유지하고, PR 본문과 CI 경고 문서의 링크 대상만 위 문서 커밋의 공개 GitHub URL로 바꾸었다. JIRA 설명도 같은 두 URL만 보정하고 재조회로 변환 결과와의 일치를 확인했다.

[티켓별 노트](https://github.com/vimkim/my-cubrid-jira/blob/main/issues/CUBRIDQA-1693-nested-sql-summary_4f720bd_codex.md)를 본문 기록으로 보존한다. 생성 시 원본의 SHA-256은 `7aeb2357235a0a366d46b07c4d6a7c868a046311c95db176798d841f7f8866fe`, 링크를 보정한 노트는 `7d3d24efcba3d0303f3c873931693566268b47ba9221cab4cd3944521a75a8a4`이다. 승인한 분석 원본과 PR 본문 파일은 수정하지 않았다.

## 확인한 범위와 다음 단계

소스·임시 runtime JAR의 회귀 검사, 전체 Ant 컴파일, 보존된 3,533개 경로·판정·시간의 오프라인 보고서 재생을 마쳤다. 수정 전에는 JUnit이 3,531개로 두 경로를 누락했고, 수정 후에는 요약·JUnit·물리 판정 행이 각각 3,533개로 일치했다. 이 재생은 SQL 실행을 다시 수행한 결과가 아니다.

- [x] 승인 문서를 통합하고 공개 원격 커밋과 본문 해시를 확인한다.
- [x] 별도 Task의 본문·유형·parent 없음·Relates 연결을 재조회한다.
- [x] 검증한 source를 개인 fork에 push하고 회사 draft PR의 base·head·본문을 재조회한다.
- [x] 두 문서 링크를 공개 URL로 보정하고 티켓별 노트와 JIRA 설명의 일치를 확인한다.
- [ ] 회사 리뷰를 받고 CTP 변경을 반영한다.
- [ ] 회사 runtime에 반영된 버전을 확인하고 새 CI 산출물의 SQL 집계를 검증한다.
- [ ] 새 head·기준의 전체 증거와 이력을 확보한 뒤 R6의 shell 두 실패를 분석한다.

회사 source merge, runtime 배포와 엔진 CI 재실행은 이번 게시에서 수행하지 않았다. [기존 CI 수집 경고](ci_analysis_report_eac70c7_codex.md)는 유지한다. CTP 보고서 수정만으로 R6의 shell 실패가 회귀인지 flaky인지 판단할 수 없다.
