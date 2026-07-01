## Purpose

CBRD-26822 는 `feat/oos` 브랜치에서 LOB INSERT 경로가 테이블별 LOB 디렉터리 prefix 를 잃어버린 회귀를 다룬다. `CREATE TABLE t (c CLOB)` 후 `CHAR_TO_CLOB('hello')` 를 INSERT 하면 row 안의 locator 는 저장되지만, 실제 LOB 파일이 디스크에 만들어지지 않아 `CLOB_FROM_FILE` 이 `ER_ES_INVALID_PATH` 로 실패했다.

정상 경로에서는 `CREATE TABLE` 시점에 `src/transaction/locator_sr.c` 의 `locator_lob_make_dir_path` 가 HFID 와 attrid 로 `lob/<HFID-attrid>/` 디렉터리를 만든다. INSERT 시점도 같은 prefix 를 사용해 임시 LOB 파일을 그 디렉터리 아래로 옮겨야 한다. merge conflict 처리 과정에서 이 prefix 생성과 `db_elo_copy_with_prefix` 호출이 빠지면서 row locator 가 prefix 없는 `file:ces_NNN/...` 형태가 되었다.

이 변경의 목적은 OOS (큰 컬럼 값을 따로 저장하는 기능) 브랜치에서 CLOB/BLOB INSERT 후 같은 locator 로 `CLOB_FROM_FILE` 과 `BLOB_FROM_FILE` 이 원래 값을 읽을 수 있게 하는 것이다.

## Implementation

변경 범위는 `src/storage/heap_file.c` 한 파일이다.

`heap_attrinfo_dbvalue_to_recdes` 의 LOB 분기에서 `heap_hfid_cache_get` 으로 class OID 의 HFID 를 가져오고, `value->attrid` 와 함께 `"%d%d%d%d"` 형식의 `lob_path_prefix` 를 만든다. 이후 prefix 없는 `db_elo_copy` 대신 `db_elo_copy_with_prefix` 를 호출한다.

`heap_attrinfo_transform_variable_to_disk` 의 LOB 분기도 같은 방식으로 수정했다. `origin/develop` 의 같은 함수는 `attrid` 인자를 직접 받지만, 현재 `feat/oos` 함수는 컬럼 위치를 나타내는 `index` 인자를 받고 실제 attribute id 는 `HEAP_ATTRVALUE` 의 `value->attrid` 에 보관한다. 그래서 prefix 생성에는 `value->attrid` 를 사용한다.

두 경로 모두 기존 `heap_get_class_name`, `meta_data` 교체, `free_and_init`, `HEAP_WRITTEN_LOB_ATTRVALUE` 상태 전환 흐름은 유지했다. ES, ELO, `locator_sr`, OOS expand, index, WAL 경로는 변경하지 않았다.

## Remarks

`origin/develop` 의 canonical LOB write 경로는 HFID 와 attrid 로 `"%d%d%d%d"` prefix 를 만들고 `db_elo_copy_with_prefix` 를 호출한다. `feat/oos` 의 함수 형태와 지역 변수 배치는 develop 과 완전히 같지 않지만, prefix 포맷과 `_with_prefix` 호출 의미는 동일하게 맞췄다.

`heap_attrinfo_dbvalue_to_recdes` 는 OOS 브랜치에서 새로 추가된 경로라 develop 에 직접 대응되는 함수가 없다. 그래서 같은 prefix 규칙을 `class_oid` 와 `value->attrid` 에 적용했다.

### Test Plan

- `cmake --build --preset debug_gcc --target install` 이 성공했다.
- CLOB 단일 row 재현 테스트에서 locator 가 `file:<HFID-attrid>/ces_NNN/...` 형태로 저장되는 것을 확인했다.
- 같은 locator 로 `select cast(clob_from_file(...) as varchar)` 를 실행해 `'hello'` 가 반환되는 것을 확인했다.
- LOB 디렉터리 아래 실제 파일이 1개 생성되는 것을 확인했다.

리뷰어는 `src/storage/heap_file.c` 의 두 LOB 분기만 보면 된다. `heap_hfid_cache_get` 반환값을 별도로 검사하지 않는 점은 develop 의 기존 LOB INSERT 경로와 같은 전제다.
