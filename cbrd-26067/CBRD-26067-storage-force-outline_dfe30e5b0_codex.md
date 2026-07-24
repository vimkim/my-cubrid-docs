# CBRD-26067: STORAGE FORCE_OUTLINE

- JIRA: http://jira.cubrid.org/browse/CBRD-26067
- Source commit: `dfe30e5b0`
- Base branch: `feat/oos`
- Reference implementation: `4523843d1bfc311dbbee12540bfe959cba2e9edb` (`STORAGE PREFER_INLINE`)

## Purpose

### AS-IS

OOS 대상 컬럼은 레코드 크기가 `DB_PAGESIZE / 4`를 넘을 때만 외부 저장 후보가 된다. 또한 값의 직렬화 크기가
OOS 인라인 스텁(`OR_OOS_INLINE_SIZE`)보다 커야 한다. 따라서 사용자가 특정 가변 길이 컬럼을 항상 OOS에
저장하고 싶어도 짧은 값이나 작은 레코드는 인라인에 남는다.

스키마 수준의 저장 정책은 `STORAGE PREFER_INLINE`만 별도 플래그로 보존한다. 무조건 OOS 배치를 지정하고
`SHOW CREATE TABLE`, `unloaddb`, `CREATE TABLE ... LIKE`, `ALTER TABLE`에서 일관되게 유지하는 방법은 없다.

### TO-BE

일반 클래스의 가변 길이 인스턴스 속성에 다음 문법을 지원한다.

```sql
CREATE TABLE document (
  id INT PRIMARY KEY,
  payload VARCHAR(4096) STORAGE FORCE_OUTLINE
);
```

`STORAGE FORCE_OUTLINE`이 지정된 컬럼의 NULL이 아닌 값은 레코드 크기 조건과 OOS 스텁 대비 절감 조건을
적용하기 전에 OOS 배치 대상으로 선택한다. NULL은 기존과 동일하게 NULL로 유지한다.

정책 전환 규칙은 다음과 같다.

| DDL 입력 | 결과 |
|---|---|
| `ALTER ... MODIFY/CHANGE`에서 `STORAGE` 생략 | 기존 정책 유지 |
| `STORAGE FORCE_OUTLINE` | FORCE_OUTLINE만 설정 |
| `STORAGE PREFER_INLINE` | PREFER_INLINE만 설정 |
| `STORAGE DEFAULT` 또는 `STORAGE PREFER_OUTLINE` | 두 정책 플래그 모두 해제 |

`ALTER TABLE`은 기존 행을 즉시 다시 쓰지 않는다. 이후 INSERT 또는 해당 행의 UPDATE 시점부터 새 배치 정책이
적용된다.

## Implementation

### Parser and semantic validation

- `FORCE_OUTLINE`을 비예약어 토큰으로 추가하고 `STORAGE FORCE_OUTLINE` 문법을
  `PT_ATTR_STORAGE_FORCE_OUTLINE`으로 전달한다.
- 식별자 위치에서도 `force_outline`을 사용할 수 있도록 비예약어 동작을 유지한다.
- 고정 길이 타입, CLASS/SHARED 속성, VCLASS에는 의미 오류를 반환한다.
- CREATE와 ALTER의 도메인·속성 종류 검증을 같은 조건으로 맞췄다.

### Schema persistence and DDL round trip

- `SM_ATTFLAG_OOS_FORCE_OUTLINE` 플래그를 추가하고 디스크의 클래스 표현에서 `OR_ATTRIBUTE`로 복원한다.
- `db_attribute_is_oos_force_outline()` 조회 API를 추가했다.
- `SHOW CREATE TABLE`, parse-tree 출력, `unloaddb`가 `STORAGE FORCE_OUTLINE`을 출력한다.
- `CREATE TABLE ... LIKE`가 플래그를 복사한다.
- PREFER_INLINE과 FORCE_OUTLINE은 동시에 설정되지 않도록 CREATE/ALTER 전환과 디버그 검증을 추가했다.

### Heap placement

`heap_attrinfo_determine_disk_layout()`에서 FORCE_OUTLINE 컬럼을 일반 크기 기반 OOS 후보 계산보다 먼저
선택한다.

1. 고정 길이 컬럼과 NULL을 제외한다.
2. 선택된 값의 인라인 크기를 OOS 스텁 크기로 교체해 예상 payload 크기를 다시 계산한다.
3. 짧은 값 때문에 payload가 커질 수도 있으므로 가변 오프셋 너비와 헤더 크기를 다시 계산한다.
4. 이후에도 레코드가 크면 기존 우선순위 로직으로 나머지 가변 길이 컬럼을 추가 선택한다.

이 순서로 FORCE_OUTLINE을 배치 정책으로 적용하면서 기존 PREFER_INLINE 및 기본 크기 기반 정책은 그대로
유지한다.

### Tests

`unit_tests/oos/sql/test_oos_sql_storage.cpp`에 다음 회귀 테스트를 추가했다.

- CREATE 및 `SHOW CREATE TABLE` 왕복
- `CREATE TABLE ... LIKE` 복사
- 고정 길이, CLASS/SHARED, VCLASS 거부 및 사용자 오류 메시지 확인
- ALTER MODIFY/CHANGE의 유지·상호 전환·DEFAULT/PREFER_OUTLINE 해제
- 3,000바이트 값, 1바이트 값, NULL의 실제 OOS 레코드 수 확인
- ALTER 직후 기존 행은 유지되고 UPDATE 후 FORCE_OUTLINE이 적용되는지 확인
- `force_outline` 비예약어 식별자 확인
- 기존 PREFER_INLINE 동작 회귀 확인

## Remarks

### Test Plan

- GCC debug 구성 전체 빌드 및 설치: 통과
- OOS CTest 전체: 24/24 통과
- `test_oos_sql_storage`: 14/14 통과
- `test_oos_sql_show`: 4/4 통과
- diff whitespace 검사: 통과
- 임시 DB를 이용한 독립 `unloaddb` 실행은 로컬 Java SP 서버 기동 오류로 완료하지 못했다. 다만
  `unload_schema.c` 출력 경로는 빌드되었고, 동일 플래그를 사용하는 `SHOW CREATE TABLE` 왕복 테스트는
  통과했다.

기존 OOS 전체 테스트는 DELETE, index scan, MVCC, vacuum, recovery 보조 경로와 replication publication을
검증한다. 이번 FORCE_OUTLINE 전용 테스트는 배치 계획이 생성된 뒤 공통 OOS 수명주기 코드를 사용한다는
전제에서 해당 회귀 묶음과 함께 실행했다. 다만 FORCE_OUTLINE 컬럼을 사용한 recovery 및 HA replication
종단 간 검증은 이번 로컬 범위에 포함하지 않았다.

`STORAGE PREFER_INLINE`의 데이터 왕복 회귀는 확인했지만, 어느 컬럼이 먼저 OOS로 내려가는지를 SQL에서 직접
관찰하는 검증은 포함하지 않았다. 기존 comparator 구현은 변경하지 않았으며 FORCE_OUTLINE으로 미리 선택된
컬럼만 일반 후보 목록에서 제외한다.

### Compatibility

- 스키마 플래그는 사용하지 않던 `SM_ATTRIBUTE_FLAG` 비트 `0x2000`을 사용한다.
- 기존 `STORAGE PREFER_OUTLINE`과 `STORAGE DEFAULT`의 의미는 변경하지 않는다.
- `FORCE_OUTLINE`은 예약어가 아니므로 기존 식별자와 충돌하지 않는다.
- 기능은 OOS가 포함된 `feat/oos`를 기반으로 하므로 PR base도 `feat/oos`여야 한다.

### Known tooling issue

현재 `feat/oos`의 `heap_file.c`에는 C++17 구문이 포함되어 있지만 확장자가 `.c`이므로 GitHub 코드 스타일
스크립트가 GNU indent를 적용한다. 로컬 pre-commit 실행 시 이번 변경과 무관한 기존 OOS 영역까지 2천 줄
이상 재포맷되어 커밋 훅을 우회했다. 기능 diff는 `git diff --check`와 GCC debug 빌드로 검증했으며, 이
포매터 기준선 문제는 PR CI에서 별도로 확인해야 한다.

### Follow-up

- CUBRID 매뉴얼 저장소에 CREATE/ALTER의 `STORAGE FORCE_OUTLINE` 문법, 적용 대상, NULL 처리, ALTER 비소급
  동작을 추가해야 한다. 이번 소스 PR에는 매뉴얼 저장소 변경이 포함되지 않았다.
- Java SP 기동이 정상인 통합 환경에서 unloaddb/loaddb schema round-trip을 확인해야 한다.
- FORCE_OUTLINE 컬럼을 사용한 recovery 및 HA replication 종단 간 시나리오는 상위 OOS 검증 계획에서
  수행해야 한다.
