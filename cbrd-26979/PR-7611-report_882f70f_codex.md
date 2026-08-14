# PR #7611 Code Review Report

- PR: [CUBRID/cubrid#7611](https://github.com/CUBRID/cubrid/pull/7611)
- Head: `882f70f9699ef68ee1457e8554178920df9894e1`
- Merge-base: `07fef9d48b4776e60c42e8afa25b9f21c54b8226`; review date: 2026-08-14

## TLDR

**Non-blocking** - 기능 정확성을 막는 문제는 찾지 못했다. 현재 head는 draft에서 ready로 전환해도 된다. 명시적
`STORAGE`를 고정 길이/비정상 속성에서 거부하고, 옵션이 생략된 ALTER는 기존 정책을 정리하는 동작이
CBRD-26979의 합의와 일치한다.

## Summary

- `do_is_oos_storage_eligible_attribute()`는 normal attribute, real class, physical variable type의 세 조건을 모두 검사한다.
- CREATE/ALTER 모두 스키마 변경 전에 `do_validate_oos_storage_setting()`을 호출하고 실패 시 `ER_PT_SEMANTIC`을 반환한다.
- ALTER에서 `STORAGE`가 생략되고 새 타입이 부적격이면 상속된 `PREFER_INLINE`/`FORCE_OUTLINE` 플래그를 제거한다.
  반면 명시적 `STORAGE DEFAULT`는 `UNSET`과 구분되어 부적격 타입에서 거부된다.
- 새 단위 테스트는 네 옵션, fixed/variable type, VCLASS, shared/class attribute, ALTER 실패 원자성을 포함한다.

---

## Findings

정확성 finding은 없다.

후속 naming-only 수정으로 static helper에 `do_*` 모듈 접두사를 추가하고 namespace-scope 상수를
`STORAGE_SETTINGS`로 변경하여 비차단 스타일 사항도 해결했다. 이 수정은 아직 로컬 working tree에만 있다.

## Reproduction

동일한 SQL을 merge base와 PR head에서 standalone `csql`로 실행했다. 전체 스크립트는
[PR-7611-repro.sql](./PR-7611-repro.sql)이다.

```sql
CREATE TABLE pr7611_fixed (c INT STORAGE PREFER_INLINE);
SHOW CREATE TABLE pr7611_fixed;

CREATE TABLE pr7611_variable (c VARCHAR(4096) STORAGE PREFER_INLINE);
SHOW CREATE TABLE pr7611_variable;
```

### As-is - `07fef9d48`

```text
TABLE  CREATE TABLE
dba.pr7611_fixed     CREATE TABLE [pr7611_fixed] ([c] INTEGER STORAGE PREFER_INLINE) REUSE_OID, COLLATE utf8_bin

TABLE  CREATE TABLE
dba.pr7611_variable  CREATE TABLE [pr7611_variable] ([c] CHARACTER VARYING(4096) STORAGE PREFER_INLINE) REUSE_OID, COLLATE utf8_bin
```

고정 길이 `INT`에도 STORAGE 정책이 저장되어 문제 동작이 재현된다.

### To-be - `882f70f96`

```text
In line 4, column 34,

ERROR: before ' ); '
STORAGE options can be set only on variable-type normal attributes of a class: 'c'.

In line 5, column 19,

ERROR: before ' ; '
Unknown class "dba.pr7611_fixed".

TABLE  CREATE TABLE
dba.pr7611_variable  CREATE TABLE [pr7611_variable] ([c] CHARACTER VARYING(4096) STORAGE PREFER_INLINE) REUSE_OID, COLLATE utf8_bin
```

`INT` 정의는 semantic error로 거부되고 테이블도 생성되지 않는다. variable type 제어군은 전과 같이 성공한다.

## Verification

- Native Codex review: correctness regression 없음
- `just build`: passed
- `just build-test`: 25/25 passed; `OosSqlStorage` 21/21 passed
- `git diff --check`: PR diff와 후속 working-tree diff 모두 clean
- 임시 재현 DB `pr7611_before`, `pr7611_after`는 실행 후 삭제했다.
