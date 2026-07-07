# PR #7416 Greptile Comment Analysis

- **PR**: [#7416](https://github.com/CUBRID/cubrid/pull/7416) `[CBRD-27029] Make heap fetch OOS expand policy explicit`
- **HEAD**: `309753de6` (minimized zero-behavior-change squash, 2026-07-07)
- **Base**: `feat/oos` (`5b5ff588f`)
- **Analysis date**: 2026-07-07
- **PR contract**: *No behavior change* — 모든 call site 는 base 의 expand 동작을 그대로 유지한다
  (`*_expand_oos` caller → `HEAP_WITH_OOS_EXPAND`, plain caller → `HEAP_WITHOUT_OOS_EXPAND`).
  Reclassification 은 CBRD-26847 audit 으로 이연 (commit message 명시).

Greptile 은 4건을 남겼다 (P1 ×1, P2 ×3). **4건 모두 base 동작을 그대로 보존한 site** 를 가리킨다 —
즉, 이 PR 이 새로 만든 결함은 0건이다. 아래에 각 comment 의 주장, 코드 증거, 판정을 정리한다.

판정 용어는 CBRD-26847 census 의 glossary 를 따른다:

- **Expand** = record-level eager 치환: `RECDES` 안의 모든 inline OOS OID slot 을 실제 값으로 바꿔 record 를 재조립 (`heap_record_replace_oos_oids`).
- **Resolve** = column-level lazy 읽기: `heap_attrinfo_read_dbvalues()` 가 필요한 컬럼만 `oos_read` (`heap_attrvalue_read_oos_inline`).

---

## Comment 1 — P1, `locator_sr.c:2339` 단건 fetch 의 OOS 미확장 반환 (id 3534467833)

**Greptile 주장**: `xlocator_fetch()` → `locator_lock_and_return_object()` 가 `HEAP_WITHOUT_OOS_EXPAND` 로
채운 recdes 를 `LC_COPYAREA` 에 담아 client 로 보내므로, inline OOS OID slot 이 값으로 치환되지 않은 채
wire boundary 를 넘어가고 client 는 resolve 할 수 없다.

**코드 증거**:

- `locator_sr.c:2336–2339` — 해당 call 바로 위에 이미 in-code TODO 가 있다:
  > `/* TODO (CBRD-26847): analysis needed - this single-object client fetch keeps inline OOS OID slots (pre-policy behavior), while xlocator_fetch_all expands them; CS-mode clients cannot resolve OOS. */`
- **Base 동작 동일**: base 의 `locator_get_object` 는 내부적으로 `heap_init_get_context` 를 쓰고,
  base `heap_init_get_context` 는 `context->expand_oos = false` 로 고정 (base `heap_file.c:27103`).
  즉 base 도 이 경로에서 expand 하지 않았다. 이 PR 은 그 사실을 `HEAP_WITHOUT_OOS_EXPAND` 로 **가시화**했을 뿐이다.
- 이전 head `846b5c7cf` 는 이 site 를 WITH 로 flip 했었지만 (client-fetch gap 부분 해소),
  2026-07-07 minimization 에서 zero-behavior-change 계약을 위해 의도적으로 revert 했다.

**추적 상태**: 이 gap 은 **CBRD-26948** (unloaddb/compactdb OOS 값 손실) 의 ANALYSIS 범위에 이미 명시돼 있다 —
issue 문서에 "단일 객체 fetch `xlocator_fetch` → 워크스페이스 디코드 `tf_disk_to_mem` 도 같은 노출 가능성이
있어 확인 후 결정" 이라고 기재. 형제 경로 `xlocator_fetch_all`(`:2909`) / `xlocator_lock_and_fetch_all`(`:12144/:12159`)
은 census 필수 Expand 5곳에 포함되어 WITH 를 유지 중이다.

**판정**: **지적 자체는 사실 (real pre-existing gap), 그러나 이 PR 의 회귀가 아님.**
OOS 도입 시점부터 존재한 gap 이고, 코드 TODO + CBRD-26948 로 이미 추적 중이며, 이 PR 의 계약(무동작변경)상
여기서 flip 하지 않는 것이 의도된 결정이다. 실제 노출 경로는 CS-mode 의 object-level fetch
(workspace 객체 접근, trigger/method 평가 등)로 제한적이지만, 값 오염 가능성 자체는 인정한다.

**Disposition**: ~~코드 변경 없음. thread 에 TODO/CBRD-26948 근거로 reply 후 follow-up 에서 해소.~~
**UPDATE (2026-07-07)**: flip plan 의 안전성 검증 완료 후 사용자 결정으로 **이 PR 에서 flip 수행** —
커밋 `f59e9b8b2`, `HEAP_WITH_OOS_EXPAND` + 근거 주석. 상세는 fix plan 및
`~/gh/my-cubrid-docs/cbrd-26948/CBRD-26948-single-fetch-oos-expand-flip-plan.md` (EXECUTED) 참고.

---

## Comment 2 — P2, `locator_sr.c:5808` reevaluation 경로의 raw OOS record (id 3534467917)

**Greptile 주장**: `locator_update_force` 에서 `need_locking` branch 는 `HEAP_WITHOUT_OOS_EXPAND`,
non-locking branch 는 `HEAP_WITH_OOS_EXPAND` 로 같은 old record 를 다르게 가져온다. old record 가
index/FK maintenance 에 쓰이는데 OOS 컬럼이 key 라면 inline OOS OID 가 값처럼 해석되어 잘못된
index 갱신/FK 판정을 만들 수 있다.

**코드 증거**:

- **비대칭은 base 그대로**: base `:5797` locking branch = getter (expand 없음, `expand_oos=false`),
  base `:5803` non-locking branch = `heap_get_visible_version_expand_oos` (WITH). 현재 head 는 이를
  정책 인자로 표기만 바꿨다 (`:5805–5813`).
- **correctness 주장은 오류**: old record (`copy_recdes`) 의 소비는
  1. `or_mvcc_get_header()` — MVCC header 는 variable area 밖이라 OOS 무관,
  2. `locator_update_index()` → `heap_attrinfo_read_dbvalues(old_recdes)` (`locator_sr.c:8519`) — **attr-layer**.
  attr-layer 는 inline OOS OID 를 `heap_attrvalue_read_oos_inline` 로 lazy **Resolve** 하므로,
  WITHOUT record 에서 key 추출을 해도 OOS OID 가 값으로 해석되는 일은 없다.
- 검증 이력: `846b5c7cf` 시점 SA-mode spot check 에서 indexed-column UPDATE 가 **양쪽 branch 모두
  WITHOUT** 인 상태로 이 경로를 통과해 round-trip md5 일치를 확인했다 (census 문서 Verification 절).

**판정**: **Correctness false positive.** 실제 결함 방향은 정반대 — non-locking branch 의 WITH 가
불필요한 eager Expand (perf leftover) 이며, CBRD-26847 branch (`33b90a444`) 에서 WITHOUT 으로
flip 하는 것이 예정된 수정이다. locking branch 의 WITHOUT 은 올바르다.

**Disposition**: 코드 변경 없음. attr-layer Resolve 근거 + CBRD-26847 이연 근거로 reply.

---

## Comment 3 — P2, `locator_sr.c:6297` delete 경로 index 제거의 raw OOS record (id 3534467993)

**Greptile 주장**: delete force 경로가 old record 를 `HEAP_WITHOUT_OOS_EXPAND` 로 가져온 뒤 그 record 를
index 제거/FK 처리 기준으로 쓰므로, OOS 컬럼이 index/FK key 에 포함되면 index entry 잔존이나 잘못된
FK 동작이 생길 수 있다.

**코드 증거**:

- **Base 동작 동일**: base `:6288` 도 같은 getter 를 쓰고 getter 는 expand 하지 않았다 (`expand_oos=false`).
- **Instance branch 소비는 attr-layer**: 삭제 old record 는
  `locator_add_or_remove_index (&copy_recdes, ...)` (`:6435`) / `locator_add_or_remove_index_for_moving` (`:6441`)
  → `locator_add_or_remove_index_internal` → `heap_attrinfo_read_dbvalues (inst_oid, recdes, &index_attrinfo)`
  (`:7946`) 로만 key 를 추출한다 — lazy **Resolve** 경로. FK 검사(`locator_check_primary_key_delete` `:4442`)
  는 별도 fetch 를 하며 census 에서 attr-layer 소비로 검증 완료.
- **Class-delete branch 만 raw parse**: `or_class_name (&copy_recdes)` (`:6351`) 는 raw byte 소비지만,
  class record (root class instance) 는 현재 OOS demotion 대상이 아니므로 no-op. 이 잠재 위험 때문에
  `846b5c7cf` census 는 mixed-consumer ambiguity rule 로 이 site 를 WITH 로 분류했었으나, minimization 이
  base 동작(WITHOUT)으로 되돌렸다. class record 가 OOS 가능해지는 날 다시 위험해지는 **latent** 항목.

**판정**: **Correctness false positive (현재 기준).** Index/FK key 추출은 전부 attr-layer Resolve.
잔여 위험은 class-delete branch 의 `or_class_name` raw parse 뿐이며 현재는 도달 불가(no-op).
CBRD-26847 audit 에서 이 site 의 최종 분류(WITH vs WITHOUT + class-record guard)를 확정하는 것이 맞다.

**Disposition**: 코드 변경 없음. attr-layer 근거 + class-record no-op 근거로 reply.
CBRD-26847 audit 항목에 "delete-force class branch raw parse" 를 명시적으로 등재.

---

## Comment 4 — P2, `heap_file.c:8948` scanrange fallback 의 정책 불일치 (id 3534468101)

**Greptile 주장**: `heap_scanrange_next()` 가 첫 boundary record 는 `HEAP_WITH_OOS_EXPAND` 로 읽고,
그 record 가 invisible/deleted 라 다음 record 로 fallback 할 때는 `HEAP_WITHOUT_OOS_EXPAND` 로 반환한다.
같은 API 가 boundary 상태에 따라 expanded/raw 를 다르게 반환하므로 caller 가 잘못된 attribute 값을
받을 수 있다.

**코드 증거**:

- **불일치는 base 그대로**: base `:8941` 첫 record = `heap_get_visible_version_expand_oos` (WITH),
  base fallback / 본경로 = plain `heap_next` (WITHOUT). 현재 head (`:8940–8968`) 는 표기만 바꿨다.
- **Caller 는 attr-layer 뿐**: `heap_scanrange_next` 의 외부 소비자는 grouped scan
  (`scan_manager.c:5057/5061/5919`) 하나이고, recdes 는 filter/val-list attr-layer pipeline 으로만
  소비된다 (census 검증). raw byte 소비자가 없으므로 WITHOUT record 가 반환되어도 값 오독은 없다.
- 이전 head `846b5c7cf` 는 scanrange 15개 site 전부를 WITHOUT 으로 통일했었다 (boundary WITH 가
  불필요한 Expand 라는 판정). minimization 이 base 동작으로 되돌리며 비대칭이 재노출된 것.

**판정**: **Correctness false positive.** "일관성이 없다"는 관찰은 맞지만, 해소 방향은 Greptile 의
암시(WITHOUT→WITH)가 아니라 **boundary WITH→WITHOUT** (불필요 Expand 제거)이며 CBRD-26847 에서 수행 예정.

**Disposition**: 코드 변경 없음. caller 단일성(attr-layer) 근거 + CBRD-26847 통일 계획으로 reply.

---

## Summary

| # | Sev | Site | Greptile 주장 | 판정 | 이 PR 회귀? | Follow-up |
|---|-----|------|--------------|------|------------|-----------|
| 1 | P1 | `locator_sr.c:2339` | 단건 fetch raw OOS 가 client 로 전송 | **사실, pre-existing gap** (in-code TODO 존재) | 아니오 (base 동일) | **CBRD-26948** (xlocator_fetch 분석 항목 기등재) |
| 2 | P2 | `locator_sr.c:5808` | locking/non-locking 비대칭 → index/FK 오동작 | False positive — 소비는 attr-layer Resolve | 아니오 (base 동일) | CBRD-26847 (non-locking WITH→WITHOUT flip) |
| 3 | P2 | `locator_sr.c:6297` | delete old record raw → index 잔존/FK 오동작 | False positive — key 추출은 attr-layer; class branch 는 no-op latent | 아니오 (base 동일) | CBRD-26847 (site 분류 확정 + class branch 등재) |
| 4 | P2 | `heap_file.c:8948` | scanrange boundary/fallback 정책 불일치 | False positive — caller 는 attr-layer 뿐; 해소 방향은 WITH→WITHOUT | 아니오 (base 동일) | CBRD-26847 (scanrange 15 site WITHOUT 통일) |

**핵심 결론**: 4건 모두 base(`feat/oos`) 동작을 그대로 보존한 site 다. 이 PR 의 목적이 바로 이런 암묵적
정책을 컴파일 타임에 보이게 만드는 것이고, Greptile 이 4곳을 지적할 수 있었다는 사실 자체가 정책
가시화의 효용을 보여준다. 유일한 실질 결함(P1)은 CBRD-26948 로 추적 중인 pre-existing gap 이다.
