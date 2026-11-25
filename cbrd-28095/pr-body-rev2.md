https://jira.cubrid.org/browse/CBRD-28095

## Purpose

- `catcls_get_db_collation ()` 은 `_db_collation` 카탈로그의 `coll_name` 과 `checksum` 값을 `LANG_COLL_COMPAT` 구조체의 고정 크기 배열에 복사합니다. 두 복사 모두 배열 크기 안에서 끝난다는 보장이 없습니다.
  - `coll_name`(32바이트): 복사 길이의 상한을 32로 두고 `coll_name[길이]` 에 `'\0'` 을 써서, 이름이 32자이면 배열 바로 뒤에 씁니다.
  - `checksum`(33바이트): 길이를 `assert (str_len == 32)` 로만 확인하므로, release 빌드에서는 길이 제한 없이 복사합니다.
- AS-IS: 32자 이름은 바로 다음 필드 `codeset` 을 덮어, 이미 읽은 값(예: UTF-8 = 5)이 0이 됩니다. 32자보다 긴 checksum은 구조체 끝을 넘어 배열의 다음 원소를 덮습니다.
- TO-BE: 이름은 최대 31자, checksum은 최대 32자로 자르고 `'\0'` 을 배열 안에 씁니다. 다른 필드와 다음 원소는 바뀌지 않습니다.

## Implementation

- `src/storage/catalog_class.c` `catcls_get_db_collation ()`:
  - `coll_name`: 복사 길이의 상한을 `sizeof (coll_name) - 1` 로 바꿉니다. 다른 콜레이션 이름 복사 코드(`COLL_NAME_SIZE - 1`)와 같은 기준입니다.
  - `checksum`: `assert` 뒤에 복사 길이를 `sizeof (checksum) - 1` 로 자릅니다. debug 빌드의 `assert` 는 그대로 둡니다.

## Remarks

- 현재 CUBRID가 만드는 콜레이션 이름은 최대 31자이고 checksum은 항상 32자입니다. 두 컬럼은 `varchar(32)` 이고 SQL로 `_db_collation` 을 고칠 수 없습니다. 그래서 일반 사용 경로에서는 재현되지 않으며, 메모리 경계를 지키는 방어적 수정입니다.
- 확인 방법: debug 빌드의 `csql -S` 에서 gdb로 id 5 콜레이션의 값을 바꿨습니다.
  - 32자 이름: 변경 전 (`develop`)에는 `codeset` 이 5에서 0으로 바뀝니다. 변경 후에는 이름이 31자로 잘리고 `codeset` 은 5 그대로입니다.
  - 40자 checksum (`assert` 는 gdb로 건너뜀): 변경 전에는 40바이트를 복사해 다음 배열 원소의 `coll_id` 를 덮습니다. 변경 후에는 32자로 잘리고 다음 원소는 바뀌지 않습니다.
  - 모든 주입 실험에서 기동은 이름 또는 checksum 불일치 오류로 끝납니다. 주입한 값이 로드된 콜레이션과 다르기 때문이며 예상한 결과입니다. 주입 없이 접속하면 정상 동작합니다.
- 같은 함수의 realloc 실패 검사 문제는 [CBRD-28091](https://jira.cubrid.org/browse/CBRD-28091) PR에서 따로 고칩니다. 두 PR은 서로 충돌하지 않습니다.
