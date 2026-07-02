# CBRD-26937: OOS + bigone 공존 거부 (상세 설명)

- JIRA: <https://jira.cubrid.org/browse/CBRD-26937>
- PR: <https://github.com/CUBRID/cubrid/pull/7298>
- base 브랜치: `feat/oos`

> **한 줄 요약**: OOS 컬럼이 있는 행이, 큰 컬럼을 OOS 로 빼낸 뒤에도 너무 커서 bigone 으로 저장돼야 하는 경우를, 디스크에 쓰기 전에 사용자 에러로 막습니다.

## 먼저 알아둘 용어

- **OOS (Out-of-row Storage)**: 큰 가변 길이 컬럼 값을 행 안에 두지 않고, 별도의 OOS 파일로 빼서 저장하는 방식. 행 안에는 작은 토큰(OID + 길이, 16바이트)만 남깁니다.
- **demotion**: 행이 너무 커지면, 큰 가변 컬럼을 OOS 로 빼내서 행 크기를 줄이는 동작.
- **bigone (REC_BIGONE)**: 한 행이 한 페이지에 안 들어갈 만큼 크면, 행 전체를 overflow 페이지에 통째로 저장하는 방식.

이 PR 이 다루는 문제는 위 두 가지가 **한 행에서 동시에** 일어나는 경우(OOS + bigone)입니다. 이 조합은 아직 검증/지원되지 않습니다.

## 무엇이 문제였나

1. demotion 은 **가변** 컬럼만 OOS 로 뺄 수 있습니다. `BIT(n)` 같은 **고정 길이** 컬럼은 못 뺍니다.
2. 그래서 고정 컬럼이 크면, 가변 컬럼을 전부 OOS 로 빼내도 행이 여전히 너무 큽니다.
3. 이런 행은 bigone 으로 저장되는데, 이미 OOS 토큰을 들고 있으므로 "OOS + bigone" 상태가 됩니다.
4. 이 조합을 **저장 시점에 막는 코드가 없었습니다.** 행이 일단 만들어진 뒤 read 경로의 진단(assert) 이나 임시 `abort()` 에 걸렸고, release 빌드에서는 서버가 죽거나 잘못된 결과가 나왔습니다.

## 무엇을 바꿨나

행을 디스크 형식으로 만들기 직전, OOS 데이터를 쓰기 전에 검사를 추가했습니다. OOS 가 있고(`has_oos`) 행이 여전히 최대 크기를 넘으면, 새 사용자 에러 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (-1377) 로 거부합니다.

- 위치: `src/storage/heap_file.c` 의 `heap_attrinfo_transform_to_disk_internal`. INSERT 와 UPDATE 가 모두 이 한 곳을 지나갑니다.
- OOS 데이터를 **쓰기 전에** 막으므로, 버려질 OOS 조각이 남지 않습니다.

```c
if (has_oos && heap_is_big_length ((int) expected_size))
  {
    er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE, 2,
            (int) expected_size, heap_Maxslotted_reclength);
    return S_ERROR;
  }
```

기준 크기는 `DB_PAGESIZE/4` (~4KB) 가 아니라 bigone 한계인 `heap_Maxslotted_reclength` (16KB 페이지에서 약 16KB) 입니다. 따라서 4~16KB 로 남는 일반 OOS 행과, OOS 없는 일반 bigone 행은 영향받지 않습니다.

## 재현 방법 (test.sql)

전제: `feat/oos` 기반 빌드 + 기본 16KB 페이지 DB. OOS 는 별도 설정 없이 항상 동작합니다.

```sql
-- test.sql
DROP TABLE IF EXISTS t_oos_big;

-- a: 고정 길이 BIT(140000) = 17500 바이트. OOS 로 못 뺍니다.
-- b: 가변 길이 VARCHAR. 16바이트보다 큰 값은 OOS 로 빠집니다(has_oos 설정).
CREATE TABLE t_oos_big (a BIT(140000), b VARCHAR(2000));

-- 큰 가변 컬럼 b 를 OOS 로 빼내도, 고정 컬럼 a 때문에 행이 ~17.5KB 라
-- 16KB 한계를 넘습니다 -> OOS + bigone 조합.
INSERT INTO t_oos_big VALUES (B'1', REPEAT('x', 1000));

SELECT COUNT(*) FROM t_oos_big;  -- 기대: 0 (행이 저장되지 않음)
```

실행:

```bash
csql -u dba <your_db> -i test.sql
```

## AS-IS / TO-BE (리뷰어 재현용)

위 `INSERT` 를 같은 DB 에 실행했을 때 차이입니다.

| 구분 | AS-IS (이 PR 전, `feat/oos`) | TO-BE (이 PR 후) |
| --- | --- | --- |
| INSERT 동작 | 검증 안 된 OOS+bigone 행을 만들다가 임시 `abort()` 로 서버 크래시 (그 진단이 없으면 release 에서 잘못된 결과/크래시) | 저장 전에 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 로 거부 |
| 사용자 메시지 | 없음 또는 내부 에러 | "레코드 크기(N 바이트)가 최대 크기(M 바이트)를 초과..." 라는 명확한 안내 |
| 저장된 행 수 | 0 또는 손상 위험 | 0 (행 미저장, 깨끗하게 롤백) |

UPDATE 도 같은 게이트로 막힙니다. `b` 를 `NULL` 로 넣어 행을 만든 뒤(이 때는 OOS 가 없어 정상), `UPDATE ... SET b = REPEAT('x', 1000)` 로 키우면 같은 에러가 납니다.

## 바뀐 파일

- `src/storage/heap_file.c`: OOS + bigone 거부 게이트 추가.
- `src/base/error_code.h`: `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (-1377) 추가, `ER_LAST_ERROR` -> -1378.
- `msg/en_US.utf8/cubrid.msg`, `msg/ko_KR.utf8/cubrid.msg`: 새 에러 메시지(실제 크기와 최대 크기를 바이트로 안내).
- `unit_tests/oos/sql/test_oos_sql_bigone.cpp` (+ `CMakeLists.txt`): SA_MODE SQL 단위 테스트 4종.

## 단위 테스트

`ctest -R test_oos_sql_bigone` 로 4종 모두 통과 (debug_gcc):

- `OosColumnWithBigoneRejected`: `BIT(140000)` + OOS varchar INSERT -> 거부, 행 미저장.
- `UpdateIntoOosBigoneRejected`: NULL 로 insert 후 OOS 값으로 UPDATE -> 거부, 행 불변.
- `BigoneWithoutOosColumnSucceeds`: `BIT(140000)` 단독 -> 일반 bigone 정상 (게이트 미발동).
- `OosColumnInlineBetween4kAnd16kSucceeds`: `BIT(100000)` + OOS varchar -> 잔여 ~12.5KB 정상 insert (16KB 임계값 회귀 가드).

## 참고

- 게이트에 `NDEBUG` 가드가 없어 release 빌드에서도 동작합니다.
- 큰 고정 컬럼은 `BIT(n)` 으로 만듭니다. `BIT` 는 `BIT VARYING` 과 달리 고정 길이라 OOS 로 demotion 되지 않습니다(`CHAR` 는 이제 가변이라 OOS 로 빠지므로 트리거에 못 씁니다).
- release 런타임 확인과 CTP shell 시나리오는 CBRD-26659 에서 보강합니다.
