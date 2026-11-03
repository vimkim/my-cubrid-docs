https://jira.cubrid.org/browse/CBRD-27887

## Purpose

- 상위 작업 CBRD-27881은 `feature/oos-merge`의 OOS 코드에서 정리할 부분을 찾아, 동작을 바꾸지 않는 작은 PR로 나누어 정리하는 작업입니다.
- 이 PR은 ALTER의 속성 변경 판정에서 같은 모양으로 복사된 블록 세 개를 함수 하나로 합칩니다. 동작은 바뀌지 않습니다.
- AS-IS: `build_attr_change_map`에 INVISIBLE, STORAGE PREFER_INLINE, STORAGE FORCE_OUTLINE 판정 블록이 따로 있습니다. 뒤의 두 블록은 OOS가 STORAGE 옵션을 추가하면서 INVISIBLE 블록을 복사해 만들었습니다.
- TO-BE: 판정 규칙은 `build_attr_flag_change_property` 한 곳에 있습니다. 세 플래그는 이 함수를 한 번씩 호출합니다.

## Implementation

- `build_attr_flag_change_property`는 세 가지 조건을 받습니다: 기존 속성에 플래그가 있었는지, 새 정의가 그 절을 생략했는지, 새 정의가 그 플래그를 요청했는지. 원래 블록과 같은 순서로 `UNCHANGED`, `PRESENT_NEW`, `LOST`를 정합니다.
- 세 호출부는 원래 블록과 같은 비교식을 인자로 넘깁니다. 호출 순서와 위치도 같습니다.
- INVISIBLE 블록은 develop에 원래 있던 코드입니다. 이 PR은 그 블록도 같은 함수로 바꿉니다.

## Remarks

- 변경 규모는 `src/query/execute_schema.c` 한 파일, 53줄 추가, 79줄 삭제입니다.
- 원래 세 블록과 새 함수를 실제 소스에서 그대로 추출해, 가능한 모든 입력 768가지에서 결과가 같은지 비교했습니다. 모두 같았고, 일부러 틀리게 바꾼 경우 8가지는 모두 검사에서 걸렸습니다.
- `UNIT_TEST_OOS=ON` debug 빌드에서 OOS 관련 ctest 44개가 변경 전후 모두 통과했습니다. csql로 INVISIBLE/VISIBLE/STORAGE ALTER 35단계를 실행해, 각 단계의 catalog 상태가 의도와 같음을 확인했습니다.
- OOS 단위 테스트는 INVISIBLE 경로를 다루지 않습니다. CI의 `test_sql`에는 ALTER로 INVISIBLE/VISIBLE을 바꾸는 케이스(`sql/_36_guava/cbrd_26401/cases/09_invisible_extended.sql` 등)가 있고, 이번 CI에서 통과했습니다. 이 케이스들이 바뀐 함수를 실제로 지나는지는 따로 확인하지 않았습니다.
- 진행 중인 PR 중 `execute_schema.c`를 고치는 PR은 없습니다.
