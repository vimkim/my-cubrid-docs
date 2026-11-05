https://jira.cubrid.org/browse/CBRD-27259

## Purpose

- OOS는 큰 컬럼 값을 행 밖의 별도 파일로 옮겨 저장하는 기능입니다. 행이 커도 특정 컬럼 값은 옮기지 않도록 지정하는 방법이 필요합니다.
- 고정 길이 컬럼에도 타입 기본값을 뜻하는 `STORAGE DEFAULT` 를 쓸 수 있어야 합니다.
- AS-IS: `STORAGE PREFER_INLINE` 은 옮기는 순서만 뒤로 미룹니다. 그래서 행이 크면 그 컬럼도 OOS로 옮겨집니다. 고정 길이 컬럼은 `STORAGE DEFAULT` 도 거부합니다.
- TO-BE: `STORAGE FORCE_INLINE` 컬럼의 값은 OOS로 옮기지 않습니다. 고정 길이 일반 컬럼은 `STORAGE DEFAULT` 와 `STORAGE FORCE_INLINE` 을 받고, 별도 정책을 저장하지 않습니다. OOS 값 없이 여러 페이지에 걸친 큰 레코드(`REC_BIGONE`)가 되는 쓰기는 경고를 남깁니다.

## Implementation

- 문법에 `STORAGE FORCE_INLINE` 을 추가했습니다. `FORCE_INLINE` 은 예약어가 아니므로 식별자로 계속 쓸 수 있습니다.
- 가변 길이 컬럼의 `FORCE_INLINE` 은 속성 flag `SM_ATTFLAG_OOS_FORCE_INLINE` 로 저장합니다. 한 컬럼에는 OOS 정책 flag가 최대 하나만 있습니다.
- `heap_attrinfo_determine_disk_layout` 은 `FORCE_INLINE` 컬럼의 값을 OOS 후보에서 제외합니다.
- 고정 길이 컬럼은 `DEFAULT` 와 `FORCE_INLINE` 만 받습니다. `PREFER_INLINE`, `PREFER_OUTLINE`, `FORCE_OUTLINE` 은 계속 거부합니다. 이를 위해 parser가 `DEFAULT` 와 `PREFER_OUTLINE` 을 서로 다른 값으로 구분합니다.
- CLASS 속성, SHARED 속성, VCLASS 속성은 계속 모든 STORAGE 절을 거부합니다.
- CREATE, ADD, MODIFY, CHANGE는 한 함수(`do_resolve_oos_storage_flag`)로 절과 타입에서 저장할 flag를 정합니다. ALTER에서 절을 생략하면 새 타입이 가변 길이일 때만 기존 정책을 유지합니다.
- `SHOW CREATE TABLE`, `unloaddb`, `CREATE TABLE ... LIKE` 가 새 정책을 보존합니다. 메시지 340을 고정 길이 규칙에 맞게 고쳤습니다.
- OOS 값이 하나도 없는데 `REC_BIGONE` 이 되는 쓰기는 그대로 저장하고, 새 경고 `ER_HEAP_BIGONE_WITHOUT_OOS` 를 남깁니다. `FORCE_INLINE` 값, 큰 고정 길이 값, 작은 가변 길이 값이 많은 행이 이에 해당합니다. 경고는 호출한 쪽의 오류 상태를 바꾸지 않으므로 쓰기는 성공합니다.

## Remarks

- ALTER는 이미 OOS에 있는 값을 옮기지 않습니다. 새 정책은 행을 다시 쓸 때부터 적용됩니다.
- 다른 컬럼이 OOS로 옮겨졌는데도 `REC_BIGONE` 이 필요하면 기존 규칙대로 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 로 거부합니다. 이때 OOS 값은 쓰지 않습니다.
- 새 경고는 다른 경고처럼 `error_log_warning=yes` 일 때만 error log에 남습니다. 기본값은 `no` 입니다. 임시 DB에서 기본 설정일 때는 남지 않고, 켰을 때 한 번 남는 것을 확인했습니다.
- debug 빌드에서 OOS SQL GoogleTest 13개 실행 파일의 178개 테스트가 모두 통과했습니다. `test_oos_sql_storage` 는 25개에서 43개로 늘었고, 값의 저장 위치는 OOS 통계로 확인합니다.
- 임시 DB에서 `unloaddb` 와 `loaddb` 를 실행했습니다. 정책과 값의 저장 위치가 그대로 유지되었습니다.
- HA 복제와 crash recovery 테스트는 실행하지 않았습니다. DDL은 사용자 SQL 문장으로 복제되고, 새 로그 레코드는 없습니다.
- CBRD-27230의 UPDATE chain 재사용이 들어오면, ALTER 전에 OOS로 옮겨진 `FORCE_INLINE` 값의 처리를 정해야 합니다.
- TC 변경은 없습니다. 두 TC 저장소의 `feature/oos-merge` 에 STORAGE 정책 절이나 메시지 340 문구를 쓰는 파일이 없습니다.
