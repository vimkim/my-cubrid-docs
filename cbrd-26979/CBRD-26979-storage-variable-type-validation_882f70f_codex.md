# CBRD-26979 OOS STORAGE 가변 타입 적격성 검사

## Purpose

`OOS`(Out-of-row Overflow Storage — 큰 가변 컬럼 값을 heap 레코드 밖의 전용 파일에 저장하는 방식)의 `STORAGE` 옵션은 OOS 저장 대상이 될 수 있는 컬럼에서만 의미가 있다. 그러나 기존 schema 실행 경로는 옵션마다 다른 조건을 검사해 고정 타입에도 일부 문법을 허용했다.

| 구분 | 동작 |
|---|---|
| `AS-IS` | `FORCE_OUTLINE`만 물리적 가변 타입 여부를 검사한다. `PREFER_INLINE`, `PREFER_OUTLINE`, `DEFAULT`는 고정 타입에 명시해도 일부 CREATE/ALTER 경로에서 성공한다. |
| `TO-BE` | 네 가지 명시적 옵션 모두 클래스의 가변 타입 일반 속성에만 허용한다. 부적격 속성에는 동일한 semantic error를 반환한다. |

이번 변경은 SQL 타입 이름이 아니라 `pr_is_variable_type()`이 제공하는 물리적 fixed/variable 분류를 기준으로 삼는다. 따라서 물리적으로 가변인 `CHAR`와 `BIT VARYING`은 허용하고, 고정 배치인 `INT`와 `BIT(n)`은 거부한다.

## Implementation

`src/query/execute_schema.c`에 두 helper를 추가해 CREATE와 ALTER의 판단 기준을 통합했다.

- `is_oos_storage_eligible_attribute()`는 행별 heap record에 저장되는 일반 속성(`ID_ATTRIBUTE`), VCLASS가 아닌 일반 CLASS(`SM_CLASS_CT`), 디스크 표현의 variable 영역에 저장되는 타입(`pr_is_variable_type()`)의 세 조건을 검사한다.
- `validate_oos_storage_setting()`은 `attr_storage`가 명시된 경우에만 공통 적격성 검사를 실행하고, 실패하면 `ER_PT_SEMANTIC`을 반환한다.

`do_add_attribute()`는 새 domain(컬럼 타입의 내부 표현)과 namespace(일반/CLASS/SHARED 속성 구분)를 구한 뒤, class template(CREATE/ALTER 변경을 누적하는 schema 작업 객체)을 변경하기 전에 공통 검사를 실행한다. 기존 `FORCE_OUTLINE` 전용 검사와 `PREFER_INLINE`의 부분적인 namespace 검사를 제거했기 때문에 옵션 spelling에 따른 차이가 사라진다.

`build_attr_change_map()`도 새 domain을 기준으로 같은 검사를 실행한다. 명시적 `STORAGE`가 부적격이면 ALTER를 거부한다. 절을 생략한 채 기존 정책 보유 컬럼을 부적격 타입으로 변경하면 ALTER는 성공하고, `P_OOS_PREFER_INLINE`과 `P_OOS_FORCE_OUTLINE`에 `ATT_CHG_PROPERTY_LOST`를 표시해 기존 컬럼 flag를 제거한다. 적격 타입 사이의 변경에서는 기존 정책을 그대로 유지한다.

parser semantic message 339를 `FORCE_OUTLINE` 전용 문구에서 모든 `STORAGE` 옵션에 적용되는 문구로 일반화했다. 새 error code나 메시지 슬롯은 추가하지 않았다.

`unit_tests/oos/sql/test_oos_sql_storage.cpp`는 다음 경계를 검증하도록 확장했다.

- `INT` CREATE/ALTER에서 네 가지 명시적 옵션을 모두 거부한다.
- 고정 배치 `BIT(n)`은 거부하고, 물리적으로 가변인 `CHAR`와 `BIT VARYING`은 허용한다.
- VCLASS에서 네 옵션을 모두 거부하며 기존 CLASS/SHARED 거부 동작도 유지한다.
- `STORAGE`를 생략한 variable-to-fixed ALTER는 `PREFER_INLINE`과 `FORCE_OUTLINE`을 제거한다.
- 실패한 명시적 ALTER 뒤에도 기존 schema와 data가 유지된다.

## Remarks

SQL grammar, `PT_ATTR_STORAGE` enum, schema flag의 디스크 표현은 바뀌지 않는다. `PREFER_OUTLINE`과 `DEFAULT`는 같은 기본 정책으로 해석되지만, 명시적으로 작성했다면 OOS 정책 지정이므로 동일한 적격성 검사를 받는다.

기존에 부적격 컬럼에 저장된 정책을 일괄 변환하는 catalog migration은 포함하지 않는다. 이후 해당 컬럼을 `STORAGE` 절 없이 부적격 타입으로 변경하는 경로에서는 기존 정책이 정리된다. heap OOS 배치, inline 크기, WAL, replication, vacuum, recovery도 변경 범위 밖이다.

## PostgreSQL 비교와 후속 제안: 고정 타입의 `STORAGE DEFAULT`

> 검토 상태: 이 절은 commit `882f70f9699ef68ee1457e8554178920df9894e1` 의 구현을 설명하는 앞 절과
> 구분되는 **후속 리뷰 제안**이다. 비교 기준은 PostgreSQL 18.6 (`REL_18_6`,
> `724edf9bde9d356724ad384a2e196edc3c9f80f7`)이며, 확인일은 2026-08-14 이다.

### 제기된 사용성 문제

`PREFER_INLINE`, `PREFER_OUTLINE`, `FORCE_OUTLINE` 같은 방향성 옵션은 OOS 배치 지시이므로 고정 타입에서
실패해도 사용자가 이유를 추론할 수 있다. 반면 `STORAGE DEFAULT` 는 문구 자체가 특정 외부 저장 방식을
지시하지 않고 "이 타입의 기본 저장 방식으로 되돌린다"고 읽힌다. 따라서 `INT STORAGE DEFAULT` 까지
"가변 타입이 아니다"라는 이유로 거부하면, 기능 내부의 OOS 분류를 모르는 일반 사용자에게는 뜻밖의
제약으로 보인다는 리뷰 의견이 제기되었다.

이 문제 제기는 타당하다. `DEFAULT` 를 **정책 적용**이 아니라 **정책 해제/타입 기본값 복원**으로 정의하면,
고정 타입에서 성공하는 것이 문법의 자연스러운 의미와 ALTER 복구 작업 모두에 더 잘 맞는다.

### PostgreSQL 18.6의 실제 규칙

PostgreSQL 문서는 `SET STORAGE` 가 컬럼을 inline 또는 TOAST 테이블에 둘 수 있는지와 압축 허용 여부를
정한다고 설명한다. `PLAIN` 은 inline·비압축, `MAIN` 은 inline 선호·압축 허용, `EXTERNAL` 은 외부 저장
허용·비압축, `EXTENDED` 는 외부 저장·압축 허용이며, `DEFAULT` 는 컬럼 타입의 기본 모드로 되돌린다.
이 명령은 기존 행을 즉시 재작성하지 않고 이후 갱신에 사용할 전략만 바꾼다.
([PostgreSQL 18 ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html#SQL-ALTERTABLE-DESC-SET-STORAGE),
[PostgreSQL 18 TOAST](https://www.postgresql.org/docs/18/storage-toast.html))

구현도 `DEFAULT` 를 별도 OOS/TOAST 정책으로 취급하지 않는다. `GetAttributeStorage()` 는 `DEFAULT` 를
`get_typstorage(atttypid)` 로 먼저 해석한 뒤, 해석 결과가 `PLAIN` 이거나 타입이 TOAST-aware이면 허용한다.
따라서 타입 기본값이 `PLAIN` 인 고정 타입의 `DEFAULT` 는 안전 검사에서 정상 통과한다.
([`GetAttributeStorage()`](https://github.com/postgres/postgres/blob/724edf9bde9d356724ad384a2e196edc3c9f80f7/src/backend/commands/tablecmds.c#L22136-L22170),
[`TYPSTORAGE_*`](https://github.com/postgres/postgres/blob/724edf9bde9d356724ad384a2e196edc3c9f80f7/src/include/catalog/pg_type.h#L307-L310))

공식 `postgres:18` 이미지의 PostgreSQL 18.6 서버에서 각 문장을 독립적으로 실행하고
`pg_attribute.attstorage` 를 조회한 결과는 다음과 같다.

| PostgreSQL 타입 | 물리 분류와 타입 기본값 | `PLAIN` | `EXTERNAL` | `EXTENDED` | `MAIN` | `DEFAULT` |
|---|---|---:|---:|---:|---:|---:|
| `integer` (`int4`) | `typlen=4`, `typstorage=p` | 성공 (`p`) | 실패 | 실패 | 실패 | **성공 (`p`)** |
| `char(10000)` (`bpchar`) | `typlen=-1`, `typstorage=x` | 성공 (`p`) | 성공 (`e`) | 성공 (`x`) | 성공 (`m`) | **성공 (`x`)** |

`integer` 의 세 실패는 모두 SQLSTATE `0A000`, `column data type integer can only have storage PLAIN` 을
반환했다. `DEFAULT` 는 성공하지만 이미 타입 기본값인 `PLAIN` 으로 돌아갈 뿐이므로 물리 동작은 바뀌지 않는다.
`int4` 는 4바이트 타입이며 `typstorage` 를 생략해 catalog 기본값 `p` 를 사용한다.
([`int4` catalog entry](https://github.com/postgres/postgres/blob/724edf9bde9d356724ad384a2e196edc3c9f80f7/src/include/catalog/pg_type.dat#L72-L76),
[`typstorage` default](https://github.com/postgres/postgres/blob/724edf9bde9d356724ad384a2e196edc3c9f80f7/src/include/catalog/pg_type.h#L179-L192))

`CHAR(n)` 은 SQL 의미상 blank-padded 고정 길이처럼 보이지만, PostgreSQL의 물리 타입 `bpchar` 는
`typlen=-1`, `typstorage=x` 인 TOAST-aware varlena다. 그러므로 다섯 모드를 모두 받아들인다.
([`bpchar` catalog entry](https://github.com/postgres/postgres/blob/724edf9bde9d356724ad384a2e196edc3c9f80f7/src/include/catalog/pg_type.dat#L274-L280))
이는 CUBRID에서도 타입 이름의 인상보다 `pr_is_variable_type()` 에 따른 물리 분류를 사용해야 한다는 기존
CBRD-26979 방향을 뒷받침한다. PostgreSQL에서 `DEFAULT` 문법은 16부터 지원되며, 15의 `SET STORAGE` 문법에는
네 방향성 모드만 있었다.
([PostgreSQL 15 ALTER TABLE](https://www.postgresql.org/docs/15/sql-altertable.html),
[PostgreSQL 16 ALTER TABLE](https://www.postgresql.org/docs/16/sql-altertable.html))

### PostgreSQL과 CUBRID 옵션의 대응 범위

두 제품의 옵션은 이름의 출발점은 같아도 일대일 대응은 아니다. PostgreSQL은 TOAST 압축과 외부 저장 허용을
함께 표현하지만, CUBRID OOS에는 압축 정책이 없고 컬럼 값의 demotion 순서 또는 강제 여부만 표현한다.

| PostgreSQL | 의미 | 가장 가까운 CUBRID 개념 | 차이 |
|---|---|---|---|
| `PLAIN` | inline 고정, 압축/외부 저장 금지 | `FORCE_INLINE` 개념 | 현재 CBRD-26979 worktree에는 `FORCE_INLINE` 문법이 없고, OOS+overflow 상호작용을 다루는 별도 범위다. |
| `MAIN` | 압축을 허용하되 inline 선호 | `PREFER_INLINE` | inline 선호는 비슷하지만 CUBRID 옵션에는 압축 의미가 없다. |
| `EXTERNAL` | 비압축 외부 저장 허용 | `PREFER_OUTLINE` 과 일부 유사 | PostgreSQL도 row가 작으면 inline일 수 있어 강제가 아니다. |
| `EXTENDED` | 압축 후 필요하면 외부 저장; 일반적인 기본값 | `DEFAULT`/`PREFER_OUTLINE` 과 일부 유사 | CUBRID 기본값은 압축이 아니라 PG-style four-record heap target에서의 기본 demotion 순서다. |
| `DEFAULT` | 타입의 `typstorage` 기본값 복원 | `DEFAULT` | 두 제품 모두 방향성 정책을 새로 강제하기보다 기본 정책으로 복귀한다는 의미가 가장 가깝다. |
| 직접 대응 없음 | row 크기와 무관한 외부 배치 강제 없음 | `FORCE_OUTLINE` | CUBRID 고유의 hard policy다. |

### CBRD-26979 계약 수정 제안

고정 타입에 대한 예외는 `STORAGE DEFAULT` 에만 좁게 둔다.

| CUBRID DDL | 고정 타입의 제안 결과 | 이유 |
|---|---|---|
| `INT STORAGE DEFAULT` | **성공** | 타입의 기본 저장 정책으로 복귀하는 중립적 no-op |
| 기존 정책 컬럼을 `INT STORAGE DEFAULT` 로 ALTER | **성공하고 기존 OOS 정책 제거** | 명시적 reset으로 사용 가능 |
| `INT STORAGE PREFER_INLINE` | 실패 | OOS demotion 방향을 지정하지만 고정 타입은 후보가 아님 |
| `INT STORAGE PREFER_OUTLINE` | 실패 | 현재 내부적으로 DEFAULT와 같더라도 문구는 outline 방향을 명시함 |
| `INT STORAGE FORCE_OUTLINE` | 실패 | 고정 타입에 적용할 수 없는 hard OOS 정책 |
| 향후 `INT STORAGE FORCE_INLINE` | **기능 추가 시 성공** | 고정 타입의 내재된 no-OOS 동작을 명시한다. 현재 CBRD-26979 worktree에는 이 문법이 없다. |

이 예외는 **물리 타입 조건만 완화**한다. CLASS/SHARED 속성이나 VCLASS 컬럼은 일반 CLASS의 행별 저장
정책 대상이 아니므로, `STORAGE DEFAULT` 도 계속 거부해야 한다. 즉 허용 조건은 다음처럼 정리된다.

```text
절 생략
OR (일반 CLASS의 normal attribute AND 물리적 가변 타입)
OR (일반 CLASS의 normal attribute AND 명시적 STORAGE DEFAULT)
```

### `FORCE_INLINE` 추가 여부 검토

`FORCE_INLINE` 은 추가할 가치가 있다. 다만 CBRD-26979의 `DEFAULT` 사용성 수정에 끼워 넣지 않고 별도
기능으로 다루는 편이 안전하다. 가변 타입의 hard inline 정책은 grammar 한 줄을 더하는 데서 끝나지 않고,
catalog flag, ALTER 전환, heap 배치 계획, `SHOW CREATE TABLE` 라운드트립, overflow 상호작용을 모두 바꾼다.

먼저 `INLINE` 의 범위를 다음처럼 좁혀야 한다.

> `FORCE_INLINE` 은 새 디스크 배치를 정할 때 해당 속성 값을 OOS inline stub 으로 바꾸지 않는다는 뜻이다.
> 속성을 포함한 전체 heap 레코드가 반드시 home page 안에 남는다는 뜻은 아니다.

CUBRID는 한 레코드가 최대 slotted-record 길이를 넘으면 전체 레코드를 overflow page에 두는 `REC_BIGONE`
경로를 이미 지원한다. PostgreSQL은 tuple 자체가 page를 가로지를 수 없으므로 `PLAIN` 과 CUBRID의
`FORCE_INLINE` 은 이 지점에서 다르다. `FORCE_INLINE` 만 있는 큰 CUBRID 레코드는 OOS-backed attribute가
없으므로 기존과 같이 `REC_BIGONE` 이 될 수 있다.

반면 다른 속성이 OOS로 demote된 뒤 `FORCE_INLINE` 속성 때문에 남은 레코드가 여전히 `REC_BIGONE` 을
요구하면, 현재의 OOS+bigone 금지 규칙에 따라 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 로 실패해야 한다. 이 검사는
OOS value chain을 쓰기 전에 실행되므로 실패 시 orphan chain을 만들지 않는다. 정책을 무시하고
`FORCE_INLINE` 값을 OOS로 보내는 fallback은 두지 않는다.

고정 타입의 기본값은 **효과상 `FORCE_INLINE`** 으로 해석하되, 이를 schema 정책 비트로 저장하거나
`SHOW CREATE TABLE` 에 자동 출력하지 않는다. 고정 타입은 `is_fixed`/`pr_is_variable_type()` 분류만으로 이미
OOS 후보가 될 수 없기 때문이다. 타입 능력에서 자동으로 따라오는 사실을 사용자 override로 중복 저장하면,
나중에 고정→가변 ALTER에서 의미 없던 flag가 갑자기 hard 정책으로 살아나는 문제가 생긴다.

| 고정 타입 DDL | 후속 `FORCE_INLINE` 기능의 권장 결과 | catalog / 출력 |
|---|---|---|
| `INT` | 성공, 내재된 no-OOS 기본값 | flag 없음, 절 출력 없음 |
| `INT STORAGE DEFAULT` | 성공, 타입 기본값으로 reset | flag 없음, 절 출력 없음 |
| `INT STORAGE FORCE_INLINE` | 성공, 내재된 기본값과 같은 결과 | flag 없음, canonical DDL에서는 절 생략 |
| `INT STORAGE PREFER_INLINE` | 실패 | OOS demotion 순서를 지정할 수 없음 |
| `INT STORAGE PREFER_OUTLINE` | 실패 | outline 방향을 지정할 수 없음 |
| `INT STORAGE FORCE_OUTLINE` | 실패 | OOS demotion을 강제할 수 없음 |

가변 타입에서는 `FORCE_INLINE` 이 실제 override이므로 flag를 저장하고 출력한다. ALTER에서 `STORAGE` 절을
생략했을 때는 가변→가변 변경에서만 호환되는 override를 보존한다. 가변→고정은 기존 OOS 정책을 지우고
내재된 fixed 기본값을 적용하며, 고정→가변은 새 가변 타입의 기본값을 적용한다. hard inline 의도를 타입
변경 뒤에도 유지하려면 해당 ALTER에 `STORAGE FORCE_INLINE` 을 명시해야 한다.

이 규칙은 타입의 **OOS 적격성**과 사용자가 요청한 **OOS 배치 정책**을 분리한다. CREATE/ADD/MODIFY/CHANGE가
각자 분기하지 않도록 schema seam에 단일 resolver를 두는 것이 적합하다.

```text
resolve_oos_storage_policy(attribute_kind, physical_layout,
                           requested_clause, old_override, ddl_operation)
  -> effective_policy + persisted_override
  -> or semantic error
```

resolver가 `DEFAULT` reset, 타입별 기본값, 호환되지 않는 ALTER policy 정리, one-hot flag 전환을 숨기면
호출자는 같은 interface 하나만 사용한다. heap 배치 모듈은 정규화된 정책만 받아 `FORCE_INLINE` 을 후보에서
제외하고, 기존 `FORCE_OUTLINE` 강제 대상 우선 선택과 `PREFER_INLINE` 후순위 정렬을 그대로 수행한다.

> **권고**: CBRD-26979에서는 고정 타입의 `STORAGE DEFAULT` 만 먼저 허용한다. `FORCE_INLINE` 은 위 의미와
> `REC_BIGONE` 계약, ALTER 전환, 라운드트립 및 recovery/replication 회귀를 갖춘 별도 기능으로 추가한다.
> 고정 타입의 효과상 기본값은 지금도 no-OOS이므로, 별도 기능이 들어오기 전까지 새 flag는 필요 없다.

### 구현 영향

현재 parse tree는 `PT_ATTR_STORAGE_PREFER_OUTLINE = PT_ATTR_STORAGE_DEFAULT` 로 두 spelling을 같은 enum 값에
합치고 `attr_storage` 를 2비트로 저장한다. 이 상태에서는 고정 타입에서 `DEFAULT` 만 허용하고
`PREFER_OUTLINE` 은 거부할 수 없다.
([current parse-tree representation](https://github.com/CUBRID/cubrid/blob/882f70f9699ef68ee1457e8554178920df9894e1/src/parser/parse_tree.h#L1941-L1964))

따라서 parser 단계에서는 두 spelling을 분리해야 한다.

- `PT_ATTR_STORAGE_DEFAULT` 와 `PT_ATTR_STORAGE_PREFER_OUTLINE` 에 서로 다른 enum 값을 부여한다.
- `UNSET`, `DEFAULT`, `PREFER_OUTLINE`, `PREFER_INLINE`, `FORCE_OUTLINE` 다섯 상태를 담도록
  `attr_storage:2` 를 `attr_storage:3` 으로 넓힌다. 향후 `FORCE_INLINE` 을 추가해도 3비트면 충분하다.
- `do_validate_oos_storage_setting()` 은 일반 CLASS의 normal attribute인지 먼저 확인하고, 물리적으로 고정인
  경우 `DEFAULT` 만 통과시킨다.
- catalog flag는 변경할 필요가 없다. `DEFAULT` 와 현재의 `PREFER_OUTLINE` 은 적격 가변 타입에서 모두 기존
  정책 비트를 해제하므로, spelling 구분은 semantic validation이 끝나는 parse tree 수명 동안만 필요하다.
- CREATE, ADD, MODIFY, CHANGE에서 `INT STORAGE DEFAULT` 성공과 나머지 방향성 옵션 실패를 각각 검증하고,
  variable-to-fixed ALTER에서 명시적 `DEFAULT` 가 기존 `PREFER_INLINE`/`FORCE_OUTLINE` 정책을 제거하는지
  확인한다. CLASS/SHARED/VCLASS 거부 회귀도 유지한다.

후속 `FORCE_INLINE` 기능은 위 CBRD-26979 수정과 달리 persisted policy를 하나 늘린다. 그때는
`SM_ATTFLAG_OOS_FORCE_INLINE`, `OR_ATTRIBUTE_OOS_STORAGE_FORCE_INLINE`, heap 후보 제외, schema flag one-hot
전환을 함께 추가해야 한다. 다만 고정 타입의 내재된 기본값에는 이 flag를 쓰지 않는다.

이 변경은 `DEFAULT` 의 사용자 의미를 PostgreSQL과 맞추면서도 OOS와 무관한 고정 타입에 방향성 정책이
남는 문제는 다시 만들지 않는다. 따라서 리뷰 의견대로 **고정 타입에서도 `STORAGE DEFAULT` 는 허용하는
것을 권고**한다.

### Test Plan

- 수정 전 확장된 `test_oos_sql_storage`에서 6개 테스트가 실패해 고정 타입 및 VCLASS 허용과 `PREFER_INLINE` 잔존을 재현했다.
- 수정 후 focused `test_oos_sql_storage` 21건이 모두 통과했다.
- GCC debug 구성의 build와 해당 구성에 등록된 CTest 25건이 모두 통과했다.
- commit `882f70f9699ef68ee1457e8554178920df9894e1`에 대해 whitespace 검사와 pre-commit code style 검사가 통과했다.

리뷰 시 `do_add_attribute()`와 `build_attr_change_map()`이 동일한 helper를 사용하는지, omitted `STORAGE`와 explicit `STORAGE DEFAULT`가 구분되는지, 실패한 ALTER가 schema 변경 전에 중단되는지를 우선 확인하면 된다.
