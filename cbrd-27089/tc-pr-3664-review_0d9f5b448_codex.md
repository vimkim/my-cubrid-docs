# TC PR #3664 코드 리뷰: medium 변환 쿼리의 출력 순서

작성: **2026-10-14 (Asia/Seoul)**. [공개 TC PR #3664](https://github.com/CUBRID/cubrid-testcases/pull/3664)의 변경에서 Standards와 Spec 지적사항은 각각 **0건**이다. 여섯 baseline 조회에 정렬을 추가하고 대응하는 답안 행만 재배열했다. 기존 변환값과 변환 결과를 기준으로 하는 ASC/DESC 검증을 보존한다.

## 검토 대상과 기준

| 항목 | 고정한 값 |
| --- | --- |
| TC 저장소 / head branch | `CUBRID/cubrid-testcases` / `tc/pr-7927` |
| TC head | `0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b` |
| TC base branch / tip | `feature/oos-merge` / `bdba62aee0faec05abdd861518824c69b6c1b3c5` |
| 관련 엔진 PR | [CUBRID/cubrid #7927](https://github.com/CUBRID/cubrid/pull/7927), CBRD-27089 |
| 현재 엔진 head / head repository | `9ba5b9b927e5c1820f2f9d7a6f7d9acfa447e773` / `vimkim/cubrid` |
| 현재 엔진 head / base branch | `feat/oos-deferred-write` / `feature/oos-merge` |
| 검토한 커밋 | `f5e610d91` 초기화, `0d9f5b448` 변환 쿼리 정렬 |

현재 PR metadata와 로컬 TC checkout의 head/base가 일치함을 확인했다. 기준 ref는 실제 Git object로 해석되며 diff는 비어 있지 않다.

```sh
git diff bdba62aee0faec05abdd861518824c69b6c1b3c5...0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b
git log bdba62aee0faec05abdd861518824c69b6c1b3c5..0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b --oneline
```

Spec는 [TC 변경 커밋](https://github.com/CUBRID/cubrid-testcases/commit/0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b)의 목적과 [기존 medium 진단](medium-local-diagnosis/report.md)을 기준으로 삼았다. 매뉴얼 `3b6ae97bfbdc664b010ffa933ded5a05b291ae03`의 [ORDER BY 계약](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/query/select.rst#L561)은 정렬 없는 출력 순서가 달라질 수 있고, SELECT 목록에 없는 원본 컬럼으로 정렬할 수 있음을 설명한다.

두 TC 저장소에서 적용할 `AGENTS.md`, `AGENTS.user.md`, `CODING_STANDARDS.md`, `CONTRIBUTING.md`를 찾지 못했다. Standards는 개인 CUBRID 정책의 기존 들여쓰기 보존 규칙과 `code-review`의 Fowler 코드 냄새 기준을 적용했다. 코드 냄새는 판단 기준이며 문서화된 강제 규칙으로 취급하지 않았다. Standards와 Spec는 서로 독립적인 에이전트가 검토했다.

## Standards

**지적 0건.** 문서화된 규칙 위반 및 보고할 수준의 Fowler 코드 냄새를 발견하지 못했다. `to_char_order_by.sql:8,18,28,38`, `to_number_order_by.sql:8`, `to_timestamp_order_by.sql:8`에서 정렬만 추가했으며 기존 변환 결과 검증과 일치한다.

답안 파일의 기본 `git diff --check` 경고 12건은 순서가 이동한 기존 출력 행의 공백 패딩이다. 바이트 비교로 기존 행의 패딩이 그대로 보존됨을 확인했으며 새 공백 규칙 위반으로 판정하지 않는다.

## Spec

**지적 0건.** 커밋 명세의 원본 컬럼 `f`를 통한 여섯 baseline 조회 정렬과 기존 변환값·ASC/DESC 블록 보존 요구를 충족한다.

- [TO_CHAR 쿼리](https://github.com/CUBRID/cubrid-testcases/blob/0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b/medium/_02_xtests/cases/to_char_order_by.sql#L8)의 네 조회와 [TO_NUMBER](https://github.com/CUBRID/cubrid-testcases/blob/0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b/medium/_02_xtests/cases/to_number_order_by.sql#L8), [TO_TIMESTAMP](https://github.com/CUBRID/cubrid-testcases/blob/0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b/medium/_02_xtests/cases/to_timestamp_order_by.sql#L8)의 조회만 `ORDER BY f`를 추가했다.
- 여섯 변경 답안 블록은 원래 행의 바이트 단위 multiset을 보존한다. 기존 `ORDER BY 1` 및 `ORDER BY 1 DESC` SQL/답안 블록은 그대로다.
- 현재 fixture의 `f` 값은 서로 달라 정렬 동률로 인한 비결정성도 없다.

누락·부분 구현, 요구하지 않은 동작, 잘못 구현한 요구사항을 찾지 못했다. 판정 범위는 testcase 출력의 결정성이다. 재사용 heap/bestspace 차이의 원인을 해결하거나 엔진 무결성을 검증한다는 의미는 아니다.

## 검증과 실행 증거의 범위

이번 리뷰에서 SQL 전체 diff를 비교하여 변경이 여섯 `ORDER BY f` 추가에 한정됨을 확인했다. 답안을 delimiter별로 나누어 변경 블록의 행 multiset과 공백을 비교했고, 나머지 답안 블록은 바이트가 동일했다. 예상 source 순서도 현재 fixture와 대조했다.

```sh
git -c core.whitespace=-blank-at-eol diff --check bdba62aee0faec05abdd861518824c69b6c1b3c5...0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b
```

위 공백 검사와 별도로 바이트 보존을 검사했다. 정적 감사 결과는 `/home/vimkim/tmp/tc-pr7927-review-20261014/static-audit.json`에 보관했다.

| 기존 실행 | 리비전과 확인 결과 |
| --- | --- |
| 2026-10-08 native medium head/base | 엔진 `f3144ab4b72fc2bf73f115c9da1cf193c756457a`와 `fb567a629cdb390fff920542173fa36f454c74a0`; `_01_fixed` 114개 후 `_02_xtests` 444개를 실행하여 양쪽 모두 558/558 PASS. 세 대상 result는 답안과 바이트 동일 |
| native 입력의 동일성 | 실행 당시에는 초기화 커밋 위의 수정 상태였다. 이번 리뷰에서 양쪽 실행 디렉터리의 변경 파일 6개가 커밋 `0d9f5b448`의 Git blob과 바이트 동일함을 재확인 |
| [CI run 37760791030](https://github.com/CUBRID/cubrid/actions/runs/37760791030) | 엔진 `f3144ab4b72fc2bf73f115c9da1cf193c756457a`, TC `0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b`; medium 975/975 PASS, 세 대상 case 모두 OK. 현재 API도 run의 완료/success를 확인 |

native 근거는 `/home/vimkim/tmp/pr7927-medium-order-fix-20261008.BhPiQA/paired-verification.json`과 head/base `identity.json` 및 scenario 파일이다. native archive 소유권 warning은 원본 기록에 남아 있으며 testcase 실패로 바꾸어 해석하지 않았다. CI 건수·대상 case·build/TC provenance 근거는 `/home/vimkim/tmp/pr7927-medium-trigger-20261008.JgmXBF/medium-audit.json`과 `receipt.json`이다.

이번 리뷰에서는 DB 테스트와 CI를 새로 실행하지 않았다. 기존 PASS는 엔진 `f3144ab` 결과이며 현재 head `9ba5b9b`의 실행 결과가 아니다. [bestspace 분석](PR7927-medium-bestspace-divergence-ko.md)의 원인 확정 한계도 유지한다. TC 저장소는 수정하지 않았다.

## PR 게시 결과

2026-10-14에 검토한 head/base가 그대로임을 다시 확인한 뒤 [리뷰 요약](https://github.com/CUBRID/cubrid-testcases/pull/3664#pullrequestreview-5514039030)을 `COMMENT` 이벤트로 게시했다. API readback으로 본문, `COMMENTED` 상태와 검토 커밋 `0d9f5b448c36d6f0a33d9a62bd4048de02e6bd5b`가 일치함을 확인했다.

**집계: Standards 0건(최고 심각도 없음), Spec 0건(최고 심각도 없음).**
