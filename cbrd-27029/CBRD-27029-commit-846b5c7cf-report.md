# CBRD-27029 Commit Report — `846b5c7cf`

| 항목 | 값 |
|---|---|
| Commit | `846b5c7cf46370a7b416246bbf6dd640732f3ade` |
| Subject | `[CBRD-27029] Stop expanding attr-layer fetches inherited as WITH and scanrange boundaries` |
| Branch / PR | `cbrd-27029-oos-expand-raw-records` → PR **#7416** (base `feat/oos`) |
| Parent | `c33d0ff84` (compactdb old-record fetch WITHOUT) |
| Date | 2026-07-06 |
| Diff | `src/transaction/locator_sr.c` (6곳 1-line flip), `src/storage/heap_file.c` (2곳 boundary 재작성); +16/−12 |

용어는 CBRD-26847 glossary 를 따른다: **OOS Expand** 는 record 전체의 inline OOS OID 를 실제 값으로
한 번에 치환하는 record-level eager 동작, **OOS Resolve** 는 attribute layer 가 필요한 컬럼 하나만
`oos_read()` 로 읽는 column-level lazy 동작. 선택 기준은 "raw record bytes 를 소비하면 Expand,
아니면 Resolve" 다.

## Summary

이 커밋은 두 가지를 한다.

1. **상속된 attr-layer/header-only WITH 6곳을 WITHOUT 으로 flip** — `locator_sr.c` 의
   `heap_get_visible_version(..., HEAP_WITH_OOS_EXPAND)` 6곳은 base(`origin/feat/oos`)의
   `*_expand_oos` wrapper 를 enum 인자로 기계 치환(rename)하며 들어온 것인데, 소비자 전수 추적 결과
   전부 attribute layer 또는 record header 만 소비한다. record-level Expand 는 불필요한 I/O 였다.
2. **scanrange NULL-OID boundary 를 WITHOUT 계약에 편입** — `heap_scanrange_to_following/prior` 의
   wildcard-OID 분기가 hardcoded-WITH 인 `heap_first()`/`heap_last()` 를 경유해, "scanrange 내부
   fetch 는 전부 WITHOUT" 이라는 블록 주석(`heap_file.c:8693`)과 모순이었다. 두 helper 의 셋업
   2줄을 inline 하고 `heap_next`/`heap_prev` 에 `HEAP_WITHOUT_OOS_EXPAND` 를 직접 전달한다.

## Background — 결정 이력

2026-07-06 correction plan (fable) 은 이 6곳을 "Task 5 — 명시적 out of scope, CBRD-26847 census 로
이연 [DECIDED]" 으로 기록했다. 근거는 base 동작 보존(리뷰 diff 최소화)이었다. 같은 날 correction
report (codex) 가 완성된 구현(`c33d0ff84`)을 감사하면서 이 결정을 뒤집어 Required Code Fix 로
분류했고, 소비자 재검증 결과 report 쪽이 옳았다:

- PR 자신의 정책 규칙("WITH 는 raw-byte 소비자만")을 PR 코드가 위반하는 상태였다. 리뷰어가
  WITH site 를 보면 raw 소비자를 찾게 되는데, 이 6곳에는 없다.
- `locator_update_force` 안에서 같은 old record 를 locking branch(`:5803`)는 WITHOUT, 비잠금
  branch(`:5811`)는 WITH 로 읽는 **비대칭**이 있었다. 두 branch 의 소비자는 동일하므로 어느 한쪽
  정책은 반드시 틀린 표기다.
- CBRD-26847 census 의 결론("visible-version 계열에서 Expand 가 정말 필요한 곳은 정확히 5곳")과도
  일치한다. 이 6곳은 그 5곳에 포함되지 않는다.
- 이연의 근거였던 "base 동작 보존" 은 glossary 의 위험 비대칭 앞에서 약하다: attr-layer 경로에
  Expand 를 남기면 성능만 낭비되지만, 그렇다고 유지할 이유가 되려면 소비자 불확실성이 있어야
  한다. 6곳 모두 소비자가 확정적으로 추적됐다 (아래 표).

## Change 1 — 상속된 WITH 6곳 flip (`locator_sr.c`)

각 site 의 fetch 결과(recdes)가 도달하는 **모든** 소비 지점을 추적했다. "판정" 은 위 선택 기준의
적용 결과다.

| Site | Function | 소비 체인 (전수) | 판정 |
|---|---|---|---|
| `:3496` | `locator_all_reference_lockset` | `peek_recdes` → `heap_get_referenced_by()` (`:3591`) → `heap_attrinfo_start_refoids` + `heap_attrinfo_read_dbvalues()` (`heap_file.c:14870`). 다른 사용처 없음. | attr-layer. 이전 판 문서의 "reference 추출 raw parse" 는 **오판정**이었다. |
| `:5811` | `locator_update_force` 비잠금 MVCC branch | `oldrecdes` = `&copy_recdes` → ① `or_mvcc_get_header()` (`:5869`, `:5883` — MVCC header 는 fixed area, variable area 밖) ② `locator_update_index()` (`:6054`) → old/new 모두 `heap_attrinfo_read_dbvalues()` (`:8512`, `:8517`). 함수 전체(5478–6198)에서 `oldrecdes` 사용처는 이 둘뿐. | header-only + attr-layer. locking branch `:5803`(이미 WITHOUT)과 대칭 회복. |
| `:5954` | `locator_update_force` MVCC-disabled class branch (`has_index && oldrecdes == NULL`) | `:5811` 과 동일한 `oldrecdes` 소비 체인. | 동일. |
| `:6592` | `locator_delete_lob_force` | `recdes` → `heap_attrinfo_delete_lob()` (`:6600`, 정의 `heap_file.c:11134`) → LOB 컬럼만 `heap_attrvalue_read()`. attr-layer 는 inline-OOS 값을 `heap_attrvalue_read_oos_inline()` → `oos_read()` 로 Resolve 한다. | attr-layer. |
| `:6956` | `locator_repl_prepare_force` (HA/repl apply update 준비) | `old_recdes` (PEEK) → `or_chn()` (`:6971`) 하나. 호출자 `xlocator_repl_force` 는 이후 `locator_update_force` 에 `oldrecdes=NULL` 을 전달(`:7135`)하므로 재사용 없음. | header-only (chn 은 fixed area). |
| `:13800` | `locator_mvcc_reeval_scan_filters` (동시 update 시 filter 재평가) | `recdesp` = `&temp_recdes` (PEEK) → `heap_attrinfo_read_dbvalues()` (`:13816`) + regu/filter 평가. | attr-layer. |

**안전 논거** — WITHOUT 이 안전하려면 두 조건이면 충분하다: (a) attribute layer 는 inline OOS
슬롯을 스스로 Resolve 한다 (`heap_attrvalue_read_oos_inline`, CBRD-26769 에서 오류 전파까지 검증),
(b) header 판독(`or_chn`, `or_mvcc_get_header`)은 variable area 를 보지 않으므로 Expand 여부와
무관하다. 6곳 모두 (a) 또는 (b) 에 해당한다.

**동작 변화** — base 는 이 6곳에서 record-level Expand 를 수행했으므로 이 flip 은 base 대비
**의도된 실효 동작 변경**이다 (base 동작 보존 아님). 정확성은 동일하고, OOS row 에 대한 UPDATE
old-record fetch / LOB delete / repl apply 준비 / MVCC 재평가 / referenced-by 순회에서 record 재조립
+ OOS 컬럼 전체 `oos_read` 비용이 사라진다. wide-row(OOS) 테이블의 갱신 경로에서 row 당 비용이므로
누적 효과가 있다.

## Change 2 — scanrange NULL-OID boundary inline (`heap_file.c`)

| | Before | After |
|---|---|---|
| `heap_scanrange_to_following` (`:8735`) | `heap_first(...)` — 내부 hardcoded `HEAP_WITH_OOS_EXPAND` | `OID_SET_NULL` + volid 셋업 inline 후 `heap_next(..., HEAP_WITHOUT_OOS_EXPAND)` |
| `heap_scanrange_to_prior` (`:8844`) | `heap_last(...)` — 동일 hardcoded WITH | 동일 inline 후 `heap_prev(..., HEAP_WITHOUT_OOS_EXPAND)` |

- **왜 inline 인가**: 대안은 `heap_first`/`heap_last` 에 정책 인자를 스레딩하는 것인데, 그러면
  raw 소비자(`tde.c:584` memcpy, `boot_sr.c:310` `BOOT_DB_PARM` raw COPY)와 attr-layer 호출자
  (`dblink_global_tran_catalog.c:198/:421`, 존재-확인 `heap_file.c:18080`)까지 전부 손대야 한다.
  그 스레딩은 CBRD-26847 census 로 이연된 결정이다. helper 의 셋업은 2줄(OID reset + volid)이라
  inline 비용이 낮고, scanrange 표면 전체가 단일 정책(WITHOUT)으로 수렴한다.
- **hot-path 아님**: 현재 호출자(`scan_manager.c:5057/:5061` grouped scan)는 `start_oid/last_oid` 에
  `NULL` 포인터를 넘겨 이 분기(포인터 non-NULL && OID_ISNULL)를 타지 않는다. 이 변경은 잠재
  호출자에 대한 계약 정합성 수정이다.
- **부수 효과**: `heap_last()` 는 이 분기가 유일한 호출자였으므로 현재 **호출자 0곳**이다.
  `heap_first` 와의 대칭 API 로 유지한다 (develop merge 시 새 호출자 유입 가능).

## Deliberately NOT changed

- **Raw-byte WITH sites 전부 유지** — `LC_COPYAREA` 전송 (`locator_sr.c:2337/:2909/:12144/:12159`),
  partition 재삽입 (`:13039`), class record `or_*` parse (`:303/:1976/:6295/:10780`,
  `system_catalog.c`, `heap_get_class_record`), catalog raw parse (`catalog_class.c:4014/:4180/:4504`).
- **`heap_first`/`heap_last` hardcoded WITH 유지** — 위 Change 2 참고 (census 이연).
- **disabled `ENABLE_UNUSED_FUNCTION` 블록의 legacy `heap_get()` 6곳** (`heap_file.c:8600/9029/9095/9140`,
  `system_catalog.c:3770/4066`) — `heap_get()` 자체가 제거된 API 라 활성화해도 컴파일 불가한 죽은
  코드. 변환하지 않고 설계 문서 Verification 절에 out-of-scope 로 명시했다.

## Verification (at `846b5c7cf`)

- `just build-test` (debug_gcc): build/install + unit tests **23/23**.
- `git diff --check` + pre-commit codestyle hook 통과.
- 전수 grep: 정책 API 6종 + locator getter 3종의 활성 호출부 전부 정책 인자 명시;
  `_expand_oos`/`_skip_oos_expand` 잔존 0건; `HEAP_OOS_EXPAND_POLICY_INVALID` 전달 0건;
  `locator_sr.c` 잔여 WITH = raw 소비자 9곳뿐.
- SA-mode spot check: index 포함 OOS row (`BIT VARYING` 10000B) 에 INSERT → indexed-column UPDATE
  (flip 된 `locator_update_force` old-record fetch + `locator_update_index` attr-layer 디코드 통과)
  → SELECT md5 round-trip → `cubrid compactdb -S` 후 md5 불변 → `cubrid checkdb -S` exit 0.
  별도 2500B row 로 UPDATE/DELETE round-trip 도 통과.
- **커버되지 않은 flip 경로 (정직한 gap)**: `:6956` 은 HA repl apply, `:13800` 은 동시 UPDATE 의
  MVCC 재평가라 SA spot check 로는 실행되지 않는다. 신뢰 근거는 소비자 추적(위 표)과, 동일한
  attr-layer Resolve 경로가 다른 flip site 들 및 기존 테스트로 이미 검증됐다는 점이다.
  후속으로 CTP isolation `.ctl` (2-session UPDATE 재평가 시나리오)이 `:13800` 을 직접 칠 수 있다.

## Rollback

단일 커밋 revert 로 보수적 WITH 로 복귀한다. on-disk/WAL format, catalog, SQL 표면 변화 없음 —
server-side C 코드의 fetch 정책 표기만 바뀐다.

## References

- 설계 문서 (caller review table 전체): `CBRD-27029-expand-raw-records.md` (같은 디렉터리, `846b5c7cf` 기준으로 재anchor)
- Correction report (감사 원문): worktree `CBRD-27029-correction-report-codex.md` (비 커밋 로컬 아티팩트)
- Correction plan Task 5 (뒤집힌 이연 결정): worktree `CBRD-27029-correction-plan-fable.md`
- 용어/census: `../cbrd-26847/CBRD-26847-oos-visible-version-expansion.md`
- JIRA: <http://jira.cubrid.org/browse/CBRD-27029> (draft: `~/gh/my-cubrid-jira/issues/CBRD-27029-oos-expand-raw-records.md`)
- 커밋 체인: `e1ff2fb9d` → `c5186d168` → `3b4b90f40` → `400a0e791` → `c33d0ff84` → **`846b5c7cf`**
