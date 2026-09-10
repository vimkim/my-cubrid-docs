https://jira.cubrid.org/browse/CBRD-27403

## Purpose

- AS-IS: OOS 최대 크기 오류의 번호가 develop 병합으로 이동했지만 SQL 정답은 `-1381`을 유지했습니다.
- TO-BE: 현재 `feat/oos`의 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE=-1382`를 검사합니다.

## Implementation

- `bug_bts_10516.answer`와 `fbo_ddl02.answer`의 오류 번호만 갱신했습니다.
- SQL 입력, 나머지 정답, 비교 조건은 유지했습니다.

## Remarks

- 엔진 PR https://github.com/CUBRID/cubrid/pull/6864 의 testcase branch `tc/pr-6864`를 대상으로 합니다.
- `f4299ac` 엔진의 격리 환경에서 원래 두 테스트가 각각 1건 실패하는 것을 재현했습니다.
- 수정 후 CTP SQL에서 두 테스트가 각각 1/1 통과했습니다.
- shell companion: https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4116
