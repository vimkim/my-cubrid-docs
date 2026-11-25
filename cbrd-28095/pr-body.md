https://jira.cubrid.org/browse/CBRD-28095

## Purpose

- `catcls_get_db_collation ()` 은 `_db_collation.coll_name`(`varchar(32)`) 값을 32바이트 배열 `coll_name` 에 복사합니다. 복사 길이의 상한을 32로 두고 `coll_name[길이]` 에 `'\0'` 을 써서, 이름이 32자이면 배열 바로 뒤에 씁니다.
- AS-IS: 32자 이름을 읽으면 `'\0'` 이 구조체의 다음 필드 `codeset` 을 덮어, 이미 읽은 codeset 값(예: UTF-8 = 5)이 0이 됩니다.
- TO-BE: 이름을 최대 31자로 자르고 `'\0'` 을 `coll_name` 안에 씁니다. `codeset` 은 바뀌지 않습니다.

## Implementation

- `src/storage/catalog_class.c` `catcls_get_db_collation ()`: 복사 길이의 상한을 `sizeof (coll_name) - 1` 로 바꿉니다. 다른 콜레이션 이름 복사 코드(`COLL_NAME_SIZE - 1`)와 같은 기준입니다.

## Remarks

- 현재 CUBRID가 만드는 콜레이션 이름은 최대 31자이고, SQL로 `_db_collation` 을 고칠 수 없습니다. 그래서 일반 사용 경로에서는 재현되지 않으며, 메모리 경계를 지키는 방어적 수정입니다.
- 확인 방법: debug 빌드의 `csql -S` 에서 gdb로 id 5 콜레이션 이름을 32자 문자열로 바꿨습니다.
  - 변경 전 (`develop`): 복사 길이가 32가 되고, 다음 행으로 넘어갈 때 `codeset` 이 5에서 0으로 바뀌어 있습니다.
  - 변경 후: 복사 길이가 31이고 `codeset` 은 5 그대로입니다.
  - 두 경우 모두, 주입한 이름이 로드된 콜레이션 이름과 달라서 기동은 이름 불일치 오류로 끝납니다. 이는 예상한 결과입니다. fault injection 없이 접속하면 정상 동작합니다.
- 같은 함수의 `checksum` 복사도 길이를 자르지 않지만, 컬럼이 `varchar(32)` 라 지금은 넘치지 않습니다. 이 PR에서는 바꾸지 않았습니다.
- 같은 함수의 realloc 실패 검사 문제는 [CBRD-28091](https://jira.cubrid.org/browse/CBRD-28091) PR에서 따로 고칩니다. 두 PR은 서로 충돌하지 않습니다.
