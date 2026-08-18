# PR #7611 리뷰 항목 2 수정 검증

- PR: [CUBRID/cubrid#7611](https://github.com/CUBRID/cubrid/pull/7611)
- 리뷰: [pullrequestreview-4958687037](https://github.com/CUBRID/cubrid/pull/7611#pullrequestreview-4958687037)
- 재현 기준 PR head: [`c47b70596`](https://github.com/CUBRID/cubrid/commit/c47b70596b8e564f203497f0a2f381697fc56f74)
- 항목 2 수정 commit: [`8d8adb7f6`](https://github.com/CUBRID/cubrid/commit/8d8adb7f678a362964ee2ad0ceb7f69fbb4b48fb)
- 최종 검증 PR head: [`ea2439deb`](https://github.com/CUBRID/cubrid/commit/ea2439deb07eb2f2772c24db32c63b48b7a24f60)
- 검증 환경: CUBRID `11.5.0.2529`, GCC debug build, 2026-08-18
- 범위: 리뷰 항목 2만 다룬다. 고정 타입의 `STORAGE DEFAULT` 정책은 후속
  [CBRD-27259](http://jira.cubrid.org/browse/CBRD-27259) 범위다.

## Conclusion

수정 후 `ALTER ... MODIFY CLASS ATTRIBUTE`는 속성이 가변 타입인지와 무관하게 CLASS/SHARED 전용 오류인
메시지 339를 반환한다. 고정 타입 normal attribute는 기존대로 적격성 오류인 메시지 340을 반환한다.
따라서 두 오류 경로가 실제 실패 원인에 맞게 구분된다.

| 실패 원인 | 메시지 ID | 실행 결과의 고유 문구 |
|---|---:|---|
| CLASS 또는 SHARED attribute | 339 | `only normal attributes can set storage options` |
| variable-type normal attribute가 아님 | 340 | `STORAGE options can be set only on variable-type normal attributes` |

두 ID의 정의는 `src/parser/parser_message.h`, 영문 메시지는 `msg/en_US.utf8/cubrid.msg`에 있다.

## Root Cause

`attr_def_one`은 정의를 마무리할 때 `parser_attr_type`을 새 attribute의 namespace로 복사하고,
`STORAGE` 절이 CLASS/SHARED attribute에 사용되었는지 검사한다.

기존 `ALTER ... MODIFY CLASS ATTRIBUTE` 문법은 `attr_def_one`을 모두 파싱한 **뒤에**
`attr_type = PT_META_ATTR`을 덮어썼다. 따라서 parser의 메시지 339 검사를 실행할 때는 새 정의가 normal
attribute로 보였다. 이 검사를 건너뛴 뒤 schema 공통 validator가 부적격 attribute를 발견하면서 더 일반적인
메시지 340을 반환했다.

```text
AS-IS
  parse attr_def_one as PT_NORMAL
    -> CLASS/SHARED check does not fire
  overwrite attr_type with PT_META_ATTR
  schema validator
    -> generic message 340

TO-BE
  set parser_attr_type = PT_META_ATTR
  parse attr_def_one
    -> CLASS/SHARED check emits message 339
  reset parser_attr_type = PT_NORMAL
```

## Fix

`src/parser/csql_grammar.y`의 namespace 설정 시점을 `attr_def_one` 앞으로 옮겼다.

```yacc
| CLASS ATTRIBUTE
  {
    parser_attr_type = PT_META_ATTR;
    allow_attribute_ordering = true;
  }
  attr_def_one
  {
    parser_attr_type = PT_NORMAL;
    allow_attribute_ordering = false;
  }
```

같은 순서 문제를 가진 `ALTER ... CHANGE CLASS ATTRIBUTE`도 기존 attribute 이름의 `meta_class`를
`attr_def_one` 전에 전달하도록 함께 수정했다.

```yacc
: normal_column_or_class_attribute
  {
    parser_attr_type = $1->info.name.meta_class;
    allow_attribute_ordering = true;
  }
  attr_def_one
  {
    parser_attr_type = PT_NORMAL;
    allow_attribute_ordering = false;
  }
```

새 오류 코드나 메시지는 추가하지 않았다. 이미 존재하는 메시지 339가 올바른 parser 단계에서 선택되도록
attribute namespace의 전달 시점만 바로잡았다.

## Executed SQL Proof

다음 스크립트를 수정된 standalone build에서 `csql -S -u dba -e --no-pager`로 실행했다. 첫 ALTER는
가변 타입 CLASS attribute이므로 339가 나와야 한다. 두 번째 ALTER는 normal attribute이지만 고정 타입이므로
340이 나와야 하는 제어군이다.

```sql
DROP TABLE IF EXISTS pr7611_item2;
DROP TABLE IF EXISTS pr7611_control;

CREATE TABLE pr7611_item2 (a INT, CLASS ca VARCHAR(100));
ALTER TABLE pr7611_item2 MODIFY CLASS ATTRIBUTE ca VARCHAR(4096) STORAGE PREFER_INLINE;

CREATE TABLE pr7611_control (c INT);
ALTER TABLE pr7611_control MODIFY c INT STORAGE PREFER_INLINE;

DROP TABLE pr7611_item2;
DROP TABLE pr7611_control;
```

실제 실행 결과는 다음과 같다.

```text
Execute OK. (0.000000 sec) Committed. (0.001000 sec)
Execute OK. (0.000000 sec) Committed. (0.000000 sec)
Execute OK. (0.005000 sec) Committed. (0.000000 sec)

In line 5, column 66,

ERROR: 'ca' is a CLASS or SHARED attribute but only normal attributes can set storage options.

Execute OK. (0.003000 sec) Committed. (0.000000 sec)

In line 8, column 41,

ERROR: before ' ; '
STORAGE options can be set only on variable-type normal attributes of a class: 'c'.

Execute OK. (0.008000 sec) Committed. (0.001000 sec)
Execute OK. (0.002000 sec) Committed. (0.001000 sec)
```

`ca`는 `VARCHAR(4096)`이므로 가변 타입이다. 그런데도 340이 아니라 CLASS/SHARED 원인에 해당하는 339가
나온다. 반대로 normal attribute `c`는 `INT`이므로 namespace가 아니라 물리 타입 조건 때문에 340이 나온다.
이 대조가 두 경로의 우선순위와 선택 결과를 직접 검증한다.

## Regression Proof

기존 `expect_storage_attribute_error()`는 메시지 339와 340 중 어느 하나만 포함하면 성공했다. 그래서
CLASS attribute에 잘못된 340이 나와도 테스트가 통과했다. 수정된 helper는 호출자가 기대하는 오류 종류를
명시하도록 바뀌었고, 두 문구를 `||`로 허용하지 않는다.

```cpp
enum class storage_attribute_error
{
  NON_NORMAL_ATTRIBUTE,
  NON_VARIABLE_NORMAL_ATTRIBUTE
};

expect_storage_attribute_error (storage_attribute_error::NON_NORMAL_ATTRIBUTE);
```

전용 회귀 테스트를 다음 두 경로에 추가했다.

- `ALTER TABLE ... MODIFY CLASS ATTRIBUTE ... STORAGE PREFER_INLINE` -> 메시지 339
- `ALTER TABLE ... CHANGE CLASS ATTRIBUTE ... STORAGE PREFER_INLINE` -> 메시지 339

### Red: parser 수정 전

새 exact-message 테스트를 먼저 추가하고 기존 parser로 실행했을 때, 실제 메시지 340 때문에 두 테스트가
실패했다.

```text
[ RUN      ] OosSqlStorage.AlterModifyClassAttributeReportsNonNormalAttributeError
Expected: error.find("only normal attributes can set storage options") != npos
Execute: STORAGE options can be set only on variable-type normal attributes of a class: 'ca'.
[  FAILED  ] OosSqlStorage.AlterModifyClassAttributeReportsNonNormalAttributeError

[ RUN      ] OosSqlStorage.AlterChangeClassAttributeReportsNonNormalAttributeError
Expected: error.find("only normal attributes can set storage options") != npos
Execute: STORAGE options can be set only on variable-type normal attributes of a class: 'ca'.
[  FAILED  ] OosSqlStorage.AlterChangeClassAttributeReportsNonNormalAttributeError
```

### Green: parser 수정 및 최신 `feat/oos` 병합 후

```text
Internal ctest changing into directory: build_preset_debug_gcc
Test project build_preset_debug_gcc
    Start  1: oos_setup_db
1/3 Test  #1: oos_setup_db .....................   Passed
    Start 24: test_oos_sql_storage
2/3 Test #24: test_oos_sql_storage .............   Passed
    Start  2: oos_cleanup_db
3/3 Test  #2: oos_cleanup_db ...................   Passed

100% tests passed, 0 tests failed out of 3
Total Test time (real) = 9.02 sec
```

전체 등록 OOS 테스트도 통과했다.

```text
100% tests passed, 0 tests failed out of 26
Total Test time (real) = 125.30 sec
```

`git diff --check`도 오류 없이 통과했다. 검증용 `unittestdb`와 두 테스트 테이블은 실행 후 삭제했다.

## What This Proves

이 검증은 다음 세 층을 서로 독립적으로 확인한다.

1. 메시지 catalog에서 339와 340은 서로 다른 실패 원인을 표현한다.
2. 실제 `csql` 실행에서 가변 CLASS attribute는 339, 고정 normal attribute는 340을 반환한다.
3. 회귀 테스트가 더 이상 339와 340을 서로 대체 가능한 결과로 허용하지 않으며, MODIFY와 CHANGE를 모두
   고정한다.

따라서 단순히 ALTER가 실패한다는 사실만 확인한 것이 아니라, **실제 실패 원인에 대응하는 메시지 339가
선택되며 메시지 340으로 회귀하면 테스트가 실패한다는 것**까지 증명한다.
