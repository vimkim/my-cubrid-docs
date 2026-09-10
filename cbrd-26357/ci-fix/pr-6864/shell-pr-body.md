https://jira.cubrid.org/browse/CBRD-27403

## Purpose

- AS-IS: develop 병합으로 OOS 오류 번호가 이동했지만 기본 호출 스택 목록의 정답은 이전 번호를 유지했습니다.
- TO-BE: 현재 `feat/oos`의 기호 오류 정의에 맞는 번호를 검사합니다.

## Implementation

- `bug_bts_9836` 정답 두 파일과 `bug_bts_14120` 정답 한 파일을 갱신했습니다.
- `-1380,-1382,-1383`을 `-1381,-1383,-1384`로 바꿨습니다.
- 테스트 입력과 비교 조건은 유지했습니다.

## Remarks

- 엔진 PR https://github.com/CUBRID/cubrid/pull/6864 의 testcase branch `tc/pr-6864`를 대상으로 합니다.
- `f4299ac` 엔진과 기존 정답으로 같은 실패를 재현했습니다.
- 수정 후 격리 환경에서 `bug_bts_9836` 3/3, `bug_bts_14120` 2/2 검사가 통과했습니다.
- SQL 정답 두 파일은 같은 티켓의 별도 companion PR에서 갱신합니다.
