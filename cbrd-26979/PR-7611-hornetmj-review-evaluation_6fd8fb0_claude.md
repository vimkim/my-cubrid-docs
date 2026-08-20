# PR #7611 hornetmj 리뷰 코멘트 평가

- PR: [CUBRID/cubrid#7611](https://github.com/CUBRID/cubrid/pull/7611) — [CBRD-26979] Reject STORAGE options for fixed types
- 평가 기준 PR head: [`6fd8fb0e5`](https://github.com/CUBRID/cubrid/commit/6fd8fb0e52966e14c3e92d94d6f34f5e479f7844) (base: `feat/oos`)
- 리뷰어: hornetmj — inline 코멘트 2건 + APPROVED 리뷰 1건 (2026-08-20). 두 코멘트 모두 "검토" 요청 형태의 soft ask이며 approve 를 막지 않았다.
- 평가 방법: 정적 코드 분석 + git 이력 추적. 별도 실행 재현은 하지 않았다(두 건 모두 코드 경로가 명확해 실행 없이 판정 가능).

## Conclusion

| # | 코멘트 | 위치 | 판정 | 대응 |
|---|---|---|---|---|
| 1 | 중복 컬럼 오류가 신규 340 오류에 가려짐 — OOS 검사를 기존 오류 처리 뒤로 이동 검토 | `execute_schema.c:8275` | **타당** | 수용 — `do_add_attribute` 의 검사 호출을 `smt_add_attribute_w_dflt_w_order` 이후로 이동 |
| 2 | `pr_is_variable_type` 의 주석이 stale — CHAR/NUMERIC 은 가변 영역 저장, OOS 대상 | `execute_schema.c:8129` | **타당** | 수용 — 이 PR 에서 `object_primitive.c` 주석 갱신 (주석-only, 무위험) |

---

## Comment 1 — 검증 순서로 인한 오류 우선순위 변화 (id 3818605769)

### 원문

> ```sql
> CREATE TABLE r1 (c INT);
> ALTER TABLE r1 ADD ATTRIBUTE c INT STORAGE PREFER_INLINE;
> -- AS-IS: 컬럼 중복 오류 (smt_add_attribute_w_dflt_w_order)
> -- TO-BE: 340
> ```
> 리그레션 이슈 최소화를 위해 기존 에러 처리 뒤에 oos 체크 검토

### 사실 검증 — 지적한 동작 변화는 실제로 발생한다

- PR head 에서 `do_validate_oos_storage_setting` 호출은 `execute_schema.c:8275`, 즉
  `smt_add_attribute_w_dflt_w_order` (`execute_schema.c:8286`) **이전**이다.
- 중복 컬럼 검출은 `smt_add_attribute_any` → `check_namespace` (`schema_template.c:1053`,
  오류는 `ER_SM_NAME_RESERVED_BY_ATT`, `schema_template.c:493`) 내부에서 일어난다.
- 따라서 재현 SQL 은 PR 적용 후 중복 오류 대신 semantic 오류 340
  (`STORAGE options can be set only on variable-type normal attributes of a class`)을 먼저 보고한다.
- base(`feat/oos`) 에서는 `PREFER_INLINE` 검사가 `smt_add` **이후** 블록에만 있었고
  (namespace 339 검사뿐, 고정 타입 거부는 존재하지 않음), 중복 오류가 먼저 보고되었다.
  리뷰어의 AS-IS/TO-BE 서술은 정확하다.

### 유효성 평가 — 타당 (뉘앙스 2개)

1. **엄밀히는 develop 대비 리그레션이 아니다.** `STORAGE` 는 `feat/oos` 신규 문법이라 해당 문장은
   develop 에서 syntax error 로 파싱조차 되지 않는다. 실질 쟁점은 릴리스 회귀가 아니라
   **오류 우선순위의 일관성/안정성**이다: 신규 옵션 검증이 기존의 더 근본적인 오류(중복 컬럼)를
   가리는 것은 QA answer file 안정성과 사용자 관점 모두에서 바람직하지 않다. 이 PR 자체도 리뷰 항목 2
   대응에서 "다른 constraint 의 기존 검증 순서와 오류 코드 보존"을 원칙으로 삼았으므로
   (PR 본문, `PR-7611-review-item-2-storage-error-proof_c47b70596_codex.md`), 같은 원칙을 ADD 경로에도
   적용하는 것이 일관적이다.
2. **base 자체가 옵션 간 비일관 상태였다.** base 에서 `FORCE_OUTLINE` 적격성 검사는 `smt_add` **이전**
   (이 PR 이 리팩터링한 그 코드), `PREFER_INLINE` 은 이후였다. 이 PR 은 "이전"으로 통일했고, 리뷰어
   제안은 "이후"로 통일하자는 것이다. 제안 수용 시 `FORCE_OUTLINE` 의 우선순위는 base 대비 바뀌지만
   `feat/oos` 는 미출시 브랜치라 사용자 비용이 없고, "기존 검증 먼저, OOS 검증 마지막" 쪽이
   develop 의 기존 오류 우선순위를 그대로 보존하는 보수적 규칙이다.

### 대응 방안

1. `do_add_attribute` 에서 `do_validate_oos_storage_setting` 호출을 `smt_add_attribute_w_dflt_w_order`
   이후, STORAGE flag 적용 블록(`execute_schema.c:8323` 부근) 직전으로 이동한다
   (`error == NO_ERROR` guard 하에서 실행).
2. 이동 시 해당 오류 경로의 `tp_domain_free (attr_db_domain)` 를 **제거**해야 한다.
   `smt_add_attribute_any` 성공 후에는 domain 소유권이 template attribute 로 넘어가므로
   (`att->domain = domain`), 이후 실패는 template abort 가 정리한다. 이는 base 의 339 검사(smt_add
   이후, free 없음)와 같은 패턴이다.
3. `build_attr_change_map` (ALTER CHANGE/MODIFY 경로, `execute_schema.c:12571`) 호출 위치는 base 의
   `FORCE_OUTLINE` 검사 위치를 그대로 물려받아 base 대비 순서 변화가 없으므로 유지한다.
   같은 처리가 필요한지는 리뷰어에게 확인한다.
4. 우선순위 고정 unit test 추가: 중복 컬럼 + `STORAGE PREFER_INLINE`/`FORCE_OUTLINE` 조합에서
   중복 오류가 보고되는지 `unit_tests/oos/sql/test_oos_sql_storage.cpp` 에 검증 케이스를 넣는다.

### 답글 초안

> 동의합니다. 지적하신 대로 현재 head 에서는 `do_validate_oos_storage_setting` 이
> `smt_add_attribute_w_dflt_w_order` 보다 먼저 실행되어 중복 컬럼 오류가 340 에 가려집니다.
> 제안대로 ADD 경로의 OOS 검사를 기존 오류 처리 뒤(STORAGE flag 적용 직전)로 이동해 "기존 검증 먼저,
> OOS 검증 마지막"으로 통일하고, 중복 컬럼 + STORAGE 조합의 오류 우선순위를 unit test 로 고정하겠습니다.
> 참고로 base 에서는 FORCE_OUTLINE 검사만 smt_add 이전에 있어 옵션 간 순서가 달랐는데, 이번 수정으로
> FORCE_OUTLINE 도 중복 오류가 우선하게 됩니다. CHANGE/MODIFY 경로(build_attr_change_map)의 검사 위치는
> 기존 FORCE_OUTLINE 검사 위치 그대로라 순서 변화가 없어 유지할 생각인데, 같은 처리가 필요하면 말씀
> 부탁드립니다.

---

## Comment 2 — `pr_is_variable_type` 주석 stale (id 3818676944)

### 원문

> pr_is_variable_type 주석 "With the advent of parameterized types like CHAR(n), NUMERIC(p,s) etc. …
> the value will be stored in the 'fixed' region of the disk representation." 수정 검토.
> char, numeric은 가변 영역에 저장되고 oos 대상 - by ai

### 사실 검증 — 주석은 실제로 stale 하다

- 문제의 주석: `object_primitive.c:9004-9014`. "고정 타입" 의 의미를 설명하며 CHAR(n), NUMERIC(p,s)를
  fixed region 저장의 예로 든다.
- 디스크 표현의 fixed/variable 영역 분류는 `type->variable_p` 로 결정된다 (`class_object.c:7424`,
  `classobj_install_template` 계열).
- `tp_Char.variable_p` 는 0 → 1 로 전환됨: commit `83b29b02c`
  ([CBRD-26663] CHAR/VARCHAR unified variable-length storage, PR #7164). PR head 의 ancestor.
- `tp_Numeric.variable_p` 도 0 → 1 로 전환됨: commit `de7bc5ec2`
  ([CBRD-26006] Scale Range Expansion and Floating-Point NUMERIC, PR #6486). PR head 의 ancestor.
- NCHAR 는 `#define tp_NChar tp_Char` (`object_primitive.c:1696`) 이므로 함께 가변으로 전환됐다.
- 남은 고정 파라미터 타입은 `BIT(n)` 뿐 (`tp_Bit.variable_p == 0`, `object_primitive.c:13457`).
- 결과: CHAR(n)/NUMERIC(p,s) 값은 현재 디스크 표현의 **가변 영역**에 저장되며, 이 PR 기준으로 STORAGE
  옵션 허용 대상이고, 직렬화 크기가 `OR_OOS_INLINE_SIZE` (16B)를 넘으면 OOS demotion 후보다.
  (CHAR 는 흔히 해당, NUMERIC 은 크기가 작아 실무상 demotion 될 일은 드물지만 형식적으로 후보 맞음.)
  리뷰어(AI 보조) 주장 그대로 확인된다.

### 유효성 평가 — 타당 (범위 뉘앙스 1개)

- 주석이 stale 해진 원인은 이 PR 이 아니라 선행 커밋(CBRD-26663, CBRD-26006)이다. 즉 develop 에도 같은
  stale 주석이 있다. 다만 이 PR 이 `pr_is_variable_type` 을 사용자 가시적인 STORAGE 적격성 판정자로
  승격시켰으므로, 이 PR 에서 함께 고치는 것이 자연스럽고 비용도 주석-only 로 0에 가깝다.
  (feat/oos 에만 반영되어도 OOS merge 시 develop 으로 함께 들어간다.)

### 대응 방안 — 주석 갱신안

```c
/*
 * pr_is_variable_type - determine whether or not a type is fixed or variable
 * width on disk.
 *    return: non-zero if this is a variable width type
 *    id(in): type id
 * Note:
 *    A variable width value is stored in the "variable" region of the disk
 *    representation.  Parameterized types such as CHAR(n) (CBRD-26663) and
 *    NUMERIC(p,s) (CBRD-26006), which used to be fixed width, are now stored
 *    as variable width.  For the remaining fixed width types (e.g. BIT(n)),
 *    all values of any particular attribute of a class have the same size
 *    and are stored in the "fixed" region.
 */
```

`.c` 파일이므로 C 주석 유지, GNU indent 무해(주석-only).

### 답글 초안

> 확인 결과 맞는 지적입니다. `tp_Char` 는 CBRD-26663(#7164, CHAR/VARCHAR 가변 길이 저장 통합)에서,
> `tp_Numeric` 은 CBRD-26006(#6486)에서 `variable_p = 1` 로 전환되어 현재 둘 다 디스크 표현의 가변
> 영역에 저장됩니다(고정 파라미터 타입으로는 BIT(n)만 남음). 따라서 이 PR 기준으로 둘 다 STORAGE 옵션
> 대상이고 16B 초과 시 OOS demotion 후보이기도 합니다. 주석은 전환 이전 시점 기준이라 stale 하므로 이
> PR 에서 함께 갱신하겠습니다.

---

## 부수 관찰 (이 PR 범위 밖)

- `OOS-CONTEXT.md` 의 CBRD-26937 설명("a huge fixed-length `BIT(n)`/`CHAR` attribute")에서 CHAR 를
  고정 길이 예시로 드는 부분도 같은 이유(CBRD-26663)로 stale 하다. 컨텍스트 저장소
  (`cubrid-oos-context`)에서 별도 수정 필요.
