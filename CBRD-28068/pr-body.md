https://jira.cubrid.org/browse/CBRD-28068

## Purpose

GCC 11.5에서 경고를 완화하지 않고 develop의 release 빌드를 완료하도록 합니다.

- AS-IS: `qo_node_partition_key()`가 지역 `DB_VALUE`의 문자열 포인터를 반환하여 `-O2 -Werror` 빌드가 `return-local-addr` 오류로 중단됩니다.
- TO-BE: 파티션 메타데이터가 소유한 값에서 문자열을 읽어 반환합니다.

## Implementation

`setobj_get_element_ptr()`로 컬렉션의 실제 `DB_VALUE`를 참조합니다. 문자열이 값 내부에 저장되어도 지역 복사본을 가리키지 않습니다. 함수 시그니처, 두 호출부, 파티션 수 계산은 유지합니다.

## Remarks

- GCC 11.5.0의 release 빌드와 debug 빌드 및 설치를 통과했습니다.
- Debug의 파티션 키 NL 조인과 상수 키 조건을 검증했습니다. GDB에서 변경 함수의 호출 6회를 확인했습니다.
- 기존 `sql/_36_guava/cbrd_27866`을 native testkit으로 실행하여 1건 성공, 실패 0건을 확인했습니다.
- TC 변경은 없습니다. 전체 CI는 PR 생성 후 실행합니다.
