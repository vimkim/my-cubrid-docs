https://jira.cubrid.org/browse/CBRD-26357

## Purpose

- 엔진 PR [CUBRID/cubrid#7990](https://github.com/CUBRID/cubrid/pull/7990)(`feature/oos-merge` → `develop`)과 함께 머지해야 하는 SQL·medium 테스트 변경입니다.
- OOS(Out-of-row Overflow Storage)는 큰 가변 길이 값을 행 밖의 별도 파일에 저장하고, 행에는 값의 위치 정보(stub)만 남기는 기능입니다.
- AS-IS: develop의 기대값으로는 OOS 엔진에서 아래 3개 테스트가 실패합니다.
- TO-BE: OOS 엔진에서 정해진 동작을 기대값에 반영하고, 원래 검증 범위는 유지합니다.

## Implementation

변경된 테스트는 3개(파일 5개)입니다.

| 테스트 | 수정 내용 | 수정 이유 |
|---|---|---|
| `sql/_13_issues/_14_1h/bug_bts_10516` (`cases/*.sql`, `answers/*.answer`) | ① LOB 컬럼 1000개를 모두 채운 INSERT의 결과로 `Error:-1388` 블록을 answer에 추가합니다. ② `b001`, `c001`만 채운 행을 넣는 INSERT를 추가합니다. ③ 파일 끝 줄바꿈을 추가합니다(동작 변화 없음). | ① OOS 엔진에서는 값을 행 밖으로 보내도 행에 남는 stub 1000개가 최대 레코드 크기를 넘습니다. 그래서 이 INSERT는 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`(-1388)로 실패합니다. ② 이 행이 없으면 뒤의 `insert ... select`, SELECT, UPDATE, DELETE가 빈 테이블에서 실행되어 검증 의미가 없어집니다. 추가한 행으로 뒤의 기대값은 그대로 유지됩니다. |
| `sql/_15_fbo/_02_qa_test/fbo_ddl02` (`cases/*.sql`, `answers/*.answer`) | `bug_bts_10516`과 같은 시나리오여서 같은 ①②③ 수정을 합니다. | `bug_bts_10516`과 같습니다. |
| `medium/_02_xtests/7105` (`cases/7105.sql`) | `db_class` 조회에 `order by class_name`을 추가합니다. answer는 바꾸지 않습니다. | ORDER BY가 없는 조회는 행 순서를 보장하지 않습니다. OOS 엔진에서 이 조회의 행 순서가 기존 answer(`eeeoo1`, `eeeoo2`, `subeeeoo`)와 달라져 CI에서 실패했습니다. 정렬을 명시해서 같은 기대값을 순서와 무관하게 검증합니다. |

## Remarks

- 검증: 엔진 `5a70787fe`와 이 TC head `70db22a1c`로 실행한 [gha-ci run 40349442612](https://github.com/CUBRID/cubrid/actions/runs/40349442612)에서 `test_sql`(실패 0)과 `test_medium`(975/975)이 통과했습니다.
- **머지할 때 확인:** `-1388`은 `error_code.h`의 순서로 정해지는 번호입니다. develop에 에러 코드가 추가되면 번호가 바뀝니다. 지금까지 develop 동기화 때마다 -1382에서 -1388까지 갱신했습니다. 엔진 PR을 머지하는 시점의 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 값과 같은지 다시 확인해 주세요.
- **머지 순서:** `Check TC PRs` 검사 때문에 이 PR은 엔진 PR보다 먼저 TC develop에 들어가야 합니다. 그 사이에는 develop 엔진에 OOS가 없으므로 `bug_bts_10516`, `fbo_ddl02`가 develop CI와 daily 회귀에서 실패할 것으로 예상합니다(`7105`는 엔진과 무관합니다). 엔진 PR을 머지하기 직전에 머지해 주세요.
- "LOB 컬럼 1000개를 모두 채운 행은 넣을 수 없다"는 것은 OOS 엔진의 동작입니다. 이 동작에 대한 의견은 엔진 PR #7990에 남겨 주세요.
- 이 브랜치는 2026-10-27 기준 develop을 머지한 상태입니다. 같은 변경을 리뷰한 이전 PR은 #3159(`feat/oos` 시절)입니다.
- 짝 PR: [CUBRID/cubrid-testcases-private-ex#4210](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4210)(shell 테스트).
- 커밋별 이력과 근거: [CBRD-26357-tc-pr-changes_5a70787_claude.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-tc-pr-changes_5a70787_claude.md)
