# PR #7416 Greptile Fix Plan

- **PR**: #7416, HEAD `309753de6`, base `feat/oos`
- **입력**: `CBRD-27029-greptile-analysis.md` (4건 분석: P1 ×1 pre-existing gap, P2 ×3 correctness false positive)
- **날짜**: 2026-07-07
- **상태**: DECIDED (2026-07-07 grilling) — **Option A 확정 + P1 flip 은 별도 이슈로 분리.**
  P1 의 실제 flip 작업은 future agent 용 실행 계획서
  `~/gh/my-cubrid-docs/cbrd-26948/CBRD-26948-single-fetch-oos-expand-flip-plan.md` 로 문서화.
  (grilling Q1 의 1차 답변은 "이 PR 에서 flip" 이었으나, 직후 사용자 지시로
  "별도 이슈 + future plan md" 로 최종 변경.)

## 결정 프레임

이 PR 의 계약은 **zero behavior change** 다 (2026-07-07 minimization 결정, commit message 명시).
Greptile 4건은 전부 base 동작을 보존한 site 를 가리키므로, "이 PR 에서 고칠 것"과
"follow-up 으로 보낼 것"의 경계는 계약에서 기계적으로 나온다.

## Recommended: Option A — 코드 변경 없음, reply & defer

이 PR 에는 코드를 추가하지 않는다. 4개 thread 에 근거를 담은 reply 를 달고, 실질 이슈는
기존 follow-up ticket 으로 라우팅한다.

### A-1. Thread replies (4건)

각 reply 는 (1) base 동작 보존 증거, (2) 소비 경로 증거(file:line), (3) follow-up ticket 을 담는다.

| Thread | Reply 골자 |
|--------|-----------|
| P1 `locator_sr.c:2339` | 지적 사실 인정. 단, base 도 expand 하지 않던 pre-existing gap 이고 이 PR 은 무동작변경 계약이라 여기서 flip 하지 않음. call site 바로 위 in-code TODO (`CBRD-26847 analysis needed`) + CBRD-26948 에 `xlocator_fetch` 분석 항목 기등재. 형제 경로 `xlocator_fetch_all`/`xlocator_lock_and_fetch_all` 은 WITH 유지 중. |
| P2 `locator_sr.c:5808` | 비대칭은 base 그대로 (base locking branch 는 getter 내부 `expand_oos=false`, non-locking 은 `_expand_oos`). old record 소비는 `or_mvcc_get_header` + `locator_update_index` → `heap_attrinfo_read_dbvalues` (`:8519`) — attr-layer 가 inline OOS 를 lazy Resolve 하므로 index/FK key 오독 없음. 진짜 결함은 non-locking WITH 의 불필요 Expand 이며 CBRD-26847 에서 WITHOUT 으로 flip 예정. |
| P2 `locator_sr.c:6297` | old record 의 index 제거는 `locator_add_or_remove_index_internal` → `heap_attrinfo_read_dbvalues` (`:7946`) — attr-layer Resolve. FK 는 별도 fetch (`:4442`, census 검증). class-delete branch 의 `or_class_name` raw parse 는 class record 가 OOS 불가라 현재 no-op (latent, CBRD-26847 audit 등재). base 동작 동일. |
| P2 `heap_file.c:8948` | 불일치는 base 그대로 (base 첫 record `_expand_oos`, fallback plain `heap_next`). 유일한 caller 는 grouped scan (`scan_manager.c:5057/5061/5919`) attr-layer 소비라 오독 없음. 해소 방향은 boundary WITH→WITHOUT 통일이며 CBRD-26847 에서 수행 (이전 head `846b5c7cf` 에서 이미 구현했다가 무동작변경 계약으로 revert 된 이력). |

- Reply 언어: 영어 (PR 이 upstream CUBRID/cubrid 공개 repo 이므로) — **확인 필요 (Q2)**.
- Reply 후 thread resolve 는 `resolve-greptile-comments` skill 로 일괄 처리 — **확인 필요 (Q2)**.

### A-2. Follow-up 라우팅 (코드 수정이 실제로 일어나는 곳)

| 이슈 | 범위 | 상태 |
|------|------|------|
| **CBRD-26948** | P1 실질 해소: `xlocator_fetch` 단건 경로의 value-level expand (unloaddb `xlocator_fetch_all` 회귀와 동일 계열). 수정 위치는 ANALYSIS 단계에서 결정 (server-side expand vs client-side resolve). | issue 문서에 분석 항목 기등재 |
| **CBRD-26847** | P2 3건의 leftover 정리: non-locking update WITH→WITHOUT (`:5811/:5954`), scanrange boundary WITH→WITHOUT (15 site 통일), delete-force site 최종 분류 (+ class-branch raw parse 등재), `heap_first` 경유 3곳. | flip 커밋 `33b90a444` 이 별도 branch 에 존재 — PR #7416 merge 후 정책 enum 기반으로 rebase 필요 |

### A-3. 문서 동기화

- `~/gh/my-cubrid-docs/cbrd-27029/CBRD-27029-expand-raw-records.md` 는 **stale** (old head `846b5c7cf` 기준,
  flip 이 살아있던 시절 서술). 최소한 머리말에 "HEAD `309753de6` 은 zero-behavior-change 로 minimize 됨,
  Caller Review Table 의 *done* flip 들은 CBRD-26847 branch 로 이동" 배너 추가 — **확인 필요 (Q3)**.
- 본 분석/계획 md 2건을 `~/gh/my-cubrid-docs/cbrd-27029/` 로 복사 (canonical 위치) — **확인 필요 (Q3)**.
- CBRD-26847 local issue 문서에 audit 항목 추가: delete-force class-branch raw parse, scanrange boundary 통일.

## Rejected: Option B — P1 을 이 PR 에서 flip (`:2339` WITHOUT→WITH)

`846b5c7cf` 가 실제로 했던 수정이지만 다음 이유로 기각 (재확인 대상):

1. **계약 위반**: minimization 결정("flips reverted") 을 하루 만에 뒤집어 PR 을 다시 mixed-purpose 로 만든다.
2. **부분 수정**: WITH flip 은 server-side eager expand 일 뿐, CBRD-26948 이 요구하는 분석
   (client decoder `tf_disk_to_mem` 의 OOS 인지 여부, compactdb 재저장 semantics) 을 대체하지 못한다.
3. **리뷰 노이즈**: reviewer 가 "explicit 화 PR" 와 "동작 fix" 를 한 diff 에서 검증해야 한다.

단, reviewer 가 P1 을 merge blocker 로 요구하면 Option B 로 전환할 수 있게 `846b5c7cf` 의 해당 hunk 를
cherry-pick 가능한 형태로 기록해 둔다 (1-line 정책 인자 + TODO 주석 갱신).

## Open Questions (grilling 진행 상황)

- **Q1. Scope**: ✅ **결정** — Option A (이 PR 은 코드 변경 없음). P1 flip 은 별도 이슈로 분리하고,
  future agent 용 실행 계획서를 `my-cubrid-docs/cbrd-26948/` 에 작성 (2026-07-07 사용자 지시).
- **Q2. Reply 실행**: 미결 — 4건 reply 를 영어로 지금 게시하고 resolve 까지 진행? 아니면 reply 초안만 준비?
  — *추천: reply 게시 + resolve 는 reviewer 확인 후.*
- **Q3. 문서 위치/동기화**: 부분 결정 — 분석·계획·flip-plan md 를 my-cubrid-docs 에 commit (2026-07-07 지시).
  stale 문서 (`CBRD-27029-expand-raw-records.md`) 배너 추가 여부는 미결.
- **Q4. CBRD-26948 우선순위**: 미결 — P1 badge 를 받은 만큼 ANALYSIS 착수 시점을 앞당길지?
  — *추천: PR #7416 merge 후 즉시 착수.*
