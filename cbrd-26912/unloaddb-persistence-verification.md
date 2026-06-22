# CBRD-26912 - STORAGE PREFER_INLINE unloaddb/loaddb 영속성 검증

`STORAGE PREFER_INLINE` 컬럼 옵션이 `cubrid unloaddb` 스키마 덤프와 `cubrid loaddb`
재적재(reload)를 거쳐도 사라지지 않는지 확인하는 end-to-end 스크립트다.

배경: 이 옵션은 처음 구현에서 파서/스키마/디스크표현/heap demote(레코드가 페이지에 안
들어갈 때 큰 가변 컬럼을 OOS 파일로 떼어내는 동작)까지만 배선되어 있었고, 기존 `INVISIBLE`
옵션이 처리되는 일부 지점에는 플래그(`SM_ATTFLAG_OOS_PREFER_INLINE`)가 전파되지 않아
스키마 덤프/복제 시 힌트가 조용히 사라졌다. 그 갭을 메운 뒤 회귀를 막기 위한 검증이다.

## What it verifies

세 가지 경로로 옵션을 지정하고, 각각이 unloaddb 덤프 텍스트에 살아남는지 + reload 후에도
유지되는지 확인한다.

| 지정 경로 | 옵션을 들고 있어야 하는 코드 지점 |
|---|---|
| `CREATE TABLE ... STORAGE PREFER_INLINE` | unloaddb emit (`emit_attribute_def`, `src/executables/unload_schema.c`) |
| `CREATE TABLE ... LIKE` | `classobj_copy_attribute_like` (`src/object/class_object.c`) |
| `ALTER TABLE ... MODIFY ... STORAGE PREFER_INLINE` | `build_attr_change_map` GAINED 경로 (`src/query/execute_schema.c`) |

unloaddb 덤프 텍스트 자체를 만드는 emit 은 `emit_attribute_def` 이고, reload 후
`SHOW CREATE TABLE` 출력은 `object_printer::describe_attribute` 가 만든다. 즉 이 한
스크립트가 덤프 emit, LIKE 복사, ALTER 반영, 그리고 reload 라운드트립까지 한 번에 커버한다.

## How to run

CUBRID 설치본이 PATH 에 있어야 한다(보통 direnv 로 `.envrc` 로드). 스크립트는 임시
디렉터리에 자체 `CUBRID_DATABASES` 를 만들어 쓰므로 실제 DB 를 건드리지 않는다.

```bash
bash cbrd-26912/test_prefer_inline_unloaddb.sh
```

스크립트: [`test_prefer_inline_unloaddb.sh`](./test_prefer_inline_unloaddb.sh)
(exit 0 = PASS, non-zero = FAIL).

## Verified output

```
## 1. create source database
## 2. define STORAGE PREFER_INLINE three ways (CREATE / LIKE / ALTER MODIFY)
## 3. cubrid unloaddb (schema only, standalone)
## 4. assert the option is present in the unloaddb schema dump
--- STORAGE PREFER_INLINE lines in dump_schema ---
10:       [hot] character varying(4096) COLLATE utf8_bin STORAGE PREFER_INLINE,
17:       [hot] character varying(4096) COLLATE utf8_bin STORAGE PREFER_INLINE,
24:       [c] character varying(4096) COLLATE utf8_bin STORAGE PREFER_INLINE;
ok: found 3 STORAGE PREFER_INLINE column(s), none on the default column
## 5. reload the dumped schema into a fresh database
## 6. confirm the option survived the round-trip (SHOW CREATE TABLE on reloaded db)
ok: STORAGE PREFER_INLINE present on all 3 reloaded tables

PASS: STORAGE PREFER_INLINE survives cubrid unloaddb dump and cubrid loaddb reload
```

줄 10/17/24 가 각각 `prefer_inline_t.hot`(CREATE), `prefer_inline_like.hot`(LIKE),
`prefer_inline_alter.c`(ALTER MODIFY)이며, 기본 컬럼 `cold` 에는 절이 붙지 않는다.

## Related coverage

- 단위 테스트(in-process SA harness): `unit_tests/oos/sql/test_oos_sql_storage.cpp` 가
  `SHOW CREATE TABLE` / `CREATE TABLE LIKE` / `ALTER TABLE MODIFY` 영속성과 대용량 값
  round-trip 을 검증한다. unloaddb 는 별도 유틸리티 바이너리라 in-process 하네스에서
  닿지 않으므로, 이 셸 스크립트가 그 경로를 보완한다.
