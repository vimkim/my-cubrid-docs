https://jira.cubrid.org/browse/CBRD-28091

## Purpose

- `catcls_get_db_collation ()` 은 `_db_collation` 카탈로그의 행을 배열로 읽고, 행이 많으면 `db_private_realloc ()` 으로 배열을 늘립니다. 이때 realloc 결과가 아니라 항상 NULL이 아닌 인자 `db_collations` 를 검사해서, 확장 실패를 놓칩니다.
- AS-IS: 확장이 실패하면 NULL 주소에 `memset` 을 해 서버 기동이나 SA 모드 유틸리티가 SIGSEGV로 종료됩니다. 또 기존 배열의 유일한 포인터를 NULL로 덮어서 기존 배열을 해제할 수 없습니다.
- TO-BE: 확장이 실패하면 `ER_OUT_OF_VIRTUAL_MEMORY` 를 반환하고, 기존 배열은 호출자(`boot_restart_server ()`, `synccoll_check ()`)가 해제합니다.

## Implementation

- `src/storage/catalog_class.c` `catcls_get_db_collation ()`:
  - realloc 결과를 지역 변수 `new_collations` 에 받아 검사하고, 성공했을 때만 `*db_collations` 에 대입합니다.
  - 실패하면 `ER_OUT_OF_VIRTUAL_MEMORY` 를 `er_set` 합니다. `db_private_realloc ()` 의 lea heap 경로는 실패할 때 오류를 설정하지 않고 NULL만 반환하기 때문입니다.

## Remarks

- 확장 분기는 `_db_collation` 행이 256개(`LANG_MAX_COLLATIONS`)를 넘을 때만 실행됩니다. 정상 운영에서 이 분기에 도달하는 경로는 찾지 못했습니다.
- 확인 방법: debug 빌드의 `csql -S` 에서 gdb로 두 조건을 강제했습니다(fault injection). 배열 크기를 256에서 2로 낮추고, realloc 결과를 NULL로 바꿨습니다.
  - 변경 전 (`develop`): `memset` 에서 SIGSEGV가 발생합니다(`curr_coll = 0x98`). 기존 배열의 포인터도 사라집니다.
  - 변경 후: 함수가 `ER_OUT_OF_VIRTUAL_MEMORY` 를 반환하고 `*db_collations` 는 기존 배열을 그대로 가리킵니다. 호출자가 이 배열을 해제하고, 기동은 "Out of virtual memory" 오류로 끝납니다.
  - fault injection 없이 접속하면 정상 동작합니다(`_db_collation` 10행).
- 같은 함수의 `coll_name` 복사 경계 문제는 [CBRD-28095](https://jira.cubrid.org/browse/CBRD-28095) PR에서 따로 고칩니다. 두 PR은 서로 충돌하지 않습니다.
