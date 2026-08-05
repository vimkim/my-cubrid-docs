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

### Test Plan

- 수정 전 확장된 `test_oos_sql_storage`에서 6개 테스트가 실패해 고정 타입 및 VCLASS 허용과 `PREFER_INLINE` 잔존을 재현했다.
- 수정 후 focused `test_oos_sql_storage` 21건이 모두 통과했다.
- GCC debug 구성의 build와 해당 구성에 등록된 CTest 25건이 모두 통과했다.
- commit `882f70f9699ef68ee1457e8554178920df9894e1`에 대해 whitespace 검사와 pre-commit code style 검사가 통과했다.

리뷰 시 `do_add_attribute()`와 `build_attr_change_map()`이 동일한 helper를 사용하는지, omitted `STORAGE`와 explicit `STORAGE DEFAULT`가 구분되는지, 실패한 ALTER가 schema 변경 전에 중단되는지를 우선 확인하면 된다.
