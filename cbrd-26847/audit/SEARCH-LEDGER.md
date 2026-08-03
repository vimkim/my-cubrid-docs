# SEARCH-LEDGER — CBRD-26847 raw RECDES / OOS Expand 전수 조사

## 재개 블록 (매 세션 갱신)

```text
current source anchor: 6816023df4ed910687523ab4d34bf667ab32b9cd
current phase: Phase 1·2 완료(merge 완료, freeze 스냅샷 생성) → Phase 3 closure pass 진행 중
last completed inventory id: 전체 261행 closure 완료 (F-001..F-048, F-101..F-129, F-201..F-218, F-301..F-319, R-001..R-025/X-001..X-006, R-101..R-110/X-101..X-107, R-201..R-223/X-201..X-204, R-301..R-314/X-301..X-313, R-401..R-412/X-401..X-407, R-501..R-511/X-501..X-524)
new symbols not yet expanded: (closure pass 1에서 검증 중 — fragments/*-notes.md의 new-symbol 목록)
pending candidate count: 0 (10개 fragment 전부 pending=0 보고)
open findings: FIND-01..FIND-12 (BUG 0, OVER_EXPAND 16 distinct 사이트, 재판정 1), FU-01..FU-05
blocker: (없음)
next exact command: closure pass 1 → pass 2(no-new-path 2회) → Phase 4 수정 (FINDINGS.md의 16개 사이트 CONSUME→DONT)
```

## Phase 0 — 기준점 고정

| 항목 | 값 |
|---|---|
| 조사 시작일 | 2026-07-24 |
| source anchor (HEAD) | `6816023df4ed910687523ab4d34bf667ab32b9cd` (계획의 최초 anchor와 동일) |
| branch | `CBRD-26847-oos-visible-version` |
| CBRD-27029 merge (`de84fa59e`) ancestry | ancestor 확인됨 (`git merge-base --is-ancestor` 성공) |
| dirty worktree | `M cubrid-cci` (submodule), untracked: `.clangd .just .nvim.lua .vscode CMakeUserPresets.json cub_server.gdb i.gdb justfile lefthook.yml local.just` — 모두 사용자 개인 파일, 수정/정리하지 않음 |
| OOS-CONTEXT.md last updated | 2026-07-13 — anchor(2026-07-18경 merge history)보다 오래됨. visible-version census 서술(§3, `_expand_oos` 22곳)은 CBRD-27029 이전 역사적 서술로, 현재 source는 명시적 policy enum 사용. 차이는 정보로만 기록 |
| live CBRD-26847 | Status=Develop, Updated=2026-07-24. 기준 commit `6816023df` 명시 — snapshot 및 현재 source와 일치 |
| live CBRD-27029 | Status=Resolved(Fixed), PR #7416, merge `de84fa59e` — 계획과 일치 |

### Baseline 검색 (Phase 0)

```text
검색 목적: 정책 enum 상수 전체 occurrence 기준 개수 고정
source anchor: 6816023df
명령: rg -n --glob '*.{c,cc,cpp,h,hpp}' 'HEAP_RECDES_CONSUMPTION_POLICY|HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES' src unit_tests
raw candidate 수: 118 라인 (CONSUME=29, DONT_CONSUME=64, POLICY 타입=그 외)
included: TBD (Phase 1에서 분류)
excluded: 비호출 occurrence — enum 정의 heap_file.h:366-369, 유효성 macro heap_file.h:371-372, 내부 비교 heap_oos.cpp:362 / heap_file.c:26218, 주석 heap_file.h:363 / heap_file.c:8176,8205, 함수 선언/정의의 parameter 선언부
duplicate: 0
pending: 0 (Phase 1로 이월)
새로 발견한 symbol/alias/callback: px_scan_index_leaf_slot_walker.cpp, histogram_sampler_sr.cpp, dblink_global_tran_catalog.c, connection_support.cpp, btree_load.c, system_catalog.c 의 호출처 — 계획 seed 목록에 없던 파일
다음 검색어: heap_(first|last|next_1page|next_record_info|prev_record_info), scan range helper
```

실제 호출 인자 수 재검증 결과 (Phase 0):

- `HEAP_RECDES_CONSUME_RAW_BYTES` 호출 인자: **25** (계획 기준값 25와 일치)
- `HEAP_RECDES_DONT_CONSUME_RAW_BYTES` 호출 인자: **59** (계획 기준값 59와 일치)
- 공개 정책 API 7종 존재 확인: heap 4 (`heap_next`, `heap_prev`, `heap_get_visible_version`, `heap_scan_get_visible_version`), locator 3 (`locator_lock_and_get_object`, `locator_lock_and_get_object_with_evaluation`, `locator_get_object`)
- `heap_next_sampling` 부재 확인 (CBRD-26936에서 제거)

```text
검색 목적: CBRD-26847 TODO seed 확인
source anchor: 6816023df
명령: rg -n --glob '*.{c,cc,cpp,h,hpp}' 'CBRD-26847' src unit_tests
raw candidate 수: 3
included: 3 (heap_file.h:363 enum TODO, heap_file.c:8176 heap_first 주석, heap_file.c:8205 heap_last 주석)
excluded: 0
duplicate: 0
pending: 0
새로 발견한 symbol/alias/callback: heap_first/heap_last 내부 고정 정책 주석
다음 검색어: (Phase 1 seed에 포함됨)
```

## Gate 0 판정

- [x] source anchor, branch, dirty files, CBRD-27029 ancestry 기록됨
- [x] 5개 산출물 skeleton 존재, 동일 anchor `6816023df` 명시
- [x] baseline 후보 수 = 계획 기준값과 일치 (25/59), 차이 없음. raw grep 총계(29/64)와의 차이는 비호출 occurrence로 설명됨

## Phase 1·2 — 정방향·역방향 조사 (2026-07-24)

조사는 10개 병렬 조사 단위로 수행했다. 각 단위의 검색 블록(검색 목적/명령/raw candidate/
included/excluded/duplicate/pending)은 `fragments/<ID>-notes.md`에 있으며, 모든 단위가
`raw = included + excluded + duplicate + pending` 식과 `pending = 0`을 보고했다.

| 단위 | 범위 | TSV 행 | verdict 요약 |
|---|---|---|---|
| F1 | heap_file.c 내부 사이트 + 고정 정책 wrapper + 정책 plumbing | 43 | CORRECT 다수, OVER_EXPAND 4(→재판정 후 3 사이트), class-record 계열은 병합 시 재판정 |
| F2 | locator_sr.c 26 사이트 + 정책 getter 3종(PROPAGATE) | 29 | CORRECT 21, OVER_EXPAND 5, EXCLUDED 3 |
| F3 | scan_manager/query_executor/serial/dblink/px_scan/histogram | 18 | CORRECT 15, OVER_EXPAND 3 (serial×3) |
| F4 | catalog_class/system_catalog/btree_load/compactdb/sp_code/loaddb/lock_manager/connection | 19 | CORRECT 14, OVER_EXPAND 5 |
| R1 | WAL/recovery/MVCC old-version/vacuum/rollback | 31 | CORRECT 25, EXCLUDED 6 — **BUG 0** |
| R2 | CDC/flashback | 17 | CORRECT 6, FOLLOWUP 4(FU-01), EXCLUDED 7 — **BUG 0** |
| R3 | replication/HA (classic) | 19 | CORRECT 15, FOLLOWUP 1(FU-02), OVER_EXPAND 1, EXCLUDED 4 |
| R4 | copyarea/network/client 전송 + heap raw-reinsert provenance | 27 | CORRECT 13, OVER_EXPAND 1, EXCLUDED 13 |
| R5 | unloaddb/compactdb/loaddb/diagdb/checkdb/backup 등 utility | 19 | CORRECT 9, OVER_EXPAND 3, EXCLUDED 7 |
| R6 | 비-heap-instance RECDES 제외 sweep (82파일 전수 bucket) | 34 | 제외 23, heap-instance 재발견 11 |

병합 후 정규화 (2026-07-24, `AUDIT-INVENTORY.tsv`):

- 어휘 정규화: CONFORMS→CORRECT, GAP→OVER_EXPAND(정방향 행과 cross-link), PROPAGATE(should)→PROPAGATE,
  EXPAND(likely)/FOLLOWUP 분류→재판정.
- 재판정 1건: class-record 계열(F-019, F-039~F-042) — F1의 CONTRACT_GAP 제기를 F2/F4/R6의
  provenance 증거(tf_class_to_disk client 직렬화 + raw force가 demotion을 우회)로 기각,
  STORED_SAFE/CORRECT + FU-05.
- 교차 충돌 해소 1건: compactdb reinsert — offline(compactdb.c disk_update_instance→heap_update_logical,
  re-demote 없음, R-313)과 online(compactdb_sr.c:262 locator_attribute_info_force, re-demote함)은
  서로 다른 바이너리로 둘 다 사실. 직접 소스 확인으로 확정.
- 최종 tally: 261행 = CORRECT 167 / EXCLUDED 64 / OVER_EXPAND 25 / FOLLOWUP 5, TBD 0, ID 중복 0,
  전 행 19열.
- 수정 전 스냅샷: `AUDIT-INVENTORY.freeze-6816023df.tsv`

기준값 대비: CONSUME 25 / DONT 59 호출 인자 전수에 F-행 존재. OVER_EXPAND 25행 = 16개 distinct
사이트(FINDINGS.md). BUG 0.

## Phase 3 — closure (2026-07-24)

no-new-path closure pass 기록 (각 pass의 검색 블록·명령은 `fragments/CLOSURE-PASS-N.md`):

| pass | 일자 | 결과 | 조치 |
|---|---|---|---|
| PASS-1 | 2026-07-24 | 신규 5 call-arg 사이트 (heap_scanrange_prev×2/first/last — dead code, heap_is_object_not_null) | F-044~F-047 행 추가 |
| PASS-2 | 2026-07-24 | 신규 1 (xheap_has_instance, NO_BODY probe) | F-048 행 추가 |
| PASS-3 | 2026-07-24 | **0 new paths** (84 call-arg 전수 재도출, 7-API/wrapper/chokepoint caller 전수, 82파일 census 재확인) | — |
| PASS-4 | 2026-07-24 | **0 new paths** — 연속 두 번째 clean pass | closure 확정 |

Gate 3 판정:

- [x] inventory source anchor 고정 (`6816023df`), 261행, TBD 0
- [x] forward-only / reverse-only unexplained = 0 (PASS-3 S2/S3: 84/84 call-arg, 전 caller 커버; 역방향 소비자는 정책 API·Resolve·physical 보존 중 하나에 도달)
- [x] 전체 검색 pending 합계 0
- [x] 연속 2회 no-new-path pass (PASS-3, PASS-4, 2026-07-24, 명령은 fragment에 기록)
- [x] 수정 전 snapshot: `AUDIT-INVENTORY.freeze-6816023df.tsv` (261행, source 수정 이전 상태)

이 시점까지 source repo는 일절 수정하지 않았다. 이후 Phase 4에서 FINDINGS.md의 16개
OVER_EXPAND 사이트를 수정한다.
