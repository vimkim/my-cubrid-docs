# PR #7617 리뷰 대응 보고서 — hornetmj 리뷰 (2026-08-27) 의 문제·수정 코드·검증

- **PR**: [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617) — [CBRD-26786] OOS 빈 페이지 회수
- **리뷰 기준 head**: `66cd3cc` / **본 보고서 기준 head**: `8ba9b5398`
- **작성일**: 2026-09-01 (agent: claude, 저자 검수)

리뷰 항목마다 ① 문제 요약 ② 수정 코드 ③ 그 코드가 왜 문제를 고치는지의 검증 근거를 정리한다. 리뷰가 옛 head 를 기준으로 작성된 뒤 커밋 스택 (`50c18b7de` → `b43950a38` → `ac926cb5b` → `132163dab` → `7f3030a26`) 이 올라갔고, 리뷰 후 신규 수정은 `8ba9b5398` 하나다.

---

## B1. stale bestspace 힌트가 재할당된 비-OOS 페이지를 가리킬 때 쓰기 손상 (blocker)

### Problem

bestspace 힌트 (해시 캐시 / 헤더 best[]) 는 비영속 힌트라서, 힌트가 가리키던 OOS 페이지가 ① 회수 (dealloc) 되고 ② 다른 파일이 다른 용도 (예: `PAGE_FTAB`) 로 재할당한 뒤에도 살아남을 수 있다. 기존 방어는 "죽은 페이지 fix 는 `ER_PB_BAD_PAGEID` 로 실패한다" 하나뿐이었는데, 이 그물은 **페이지가 죽어 있는 동안**만 유효하다 — 재할당되어 다시 유효해진 페이지는 fix 가 성공한다. 그 뒤의 판정 (`spage_max_space_for_new_record`) 은 페이지 타입을 확인하지 않았으므로, FTAB 초기화가 지우지 않은 잔재 바이트가 우연히 그럴듯한 슬롯 헤더로 읽히면 INSERT 가 **남의 파일테이블 페이지에 레코드를 쓰고 WAL 로깅**까지 진행한다. release 빌드에서는 assert 가 서지 않아 redo 로 재현되는 영구 손상이 된다 (리뷰어 실측 재현).

읽기 전용 세 지점 (sync 스캔·통계 수집·회수기) 은 이미 `ptype == PAGE_OOS` 를 확인하고 있었고, **쓰기로 이어지는 유일한 경로인 lookup 만** 확인이 없었다.

### Fix (commit `8ba9b5398`, `src/storage/oos_file.cpp` — `oos_stats_find_page_in_bestspace`)

조건부 fix 성공 직후, 페이지의 다른 어떤 정보도 신뢰하기 전에 타입을 재검증하고, 탈락 시 힌트를 퇴출한다. 퇴출 로직은 기존 `ER_PB_BAD_PAGEID` 분기와 공용 헬퍼로 묶었다 (리뷰 제안 그대로).

```c
/* The hint may point at a page that reclaim deallocated and another file already
 * reallocated for a different purpose (e.g. PAGE_FTAB). The ER_PB_BAD_PAGEID branch above
 * only covers the window while the page STAYS deallocated; once reallocated its fix
 * succeeds again, and only the page type betrays the stale hint. Handing it out would
 * corrupt the new owner — release builds do not stop at the slotted-page asserts — so
 * re-validate the type before trusting anything else on the page. */
if (pgbuf_get_page_ptype (thread_p, *out_pgptr) != PAGE_OOS)
  {
    oos_trace ("stale bestspace hint to reallocated non-OOS page ... — evicting");
    pgbuf_unfix_and_init (thread_p, *out_pgptr);
    oos_stats_evict_stale_hint (thread_p, &candidate_vpid, found_in_hash, bestspace, best_array_index);
    notfound_cnt++;
    continue;
  }
```

```c
/* Drop a hint that turned out not to point at a usable OOS data page — deallocated, or
 * reclaimed and already reallocated for another purpose — from whichever store it came from. */
static void
oos_stats_evict_stale_hint (THREAD_ENTRY *thread_p, VPID *candidate_vpid, bool found_in_hash,
                            OOS_BESTSPACE *bestspace, int best_array_index)
```

### Validation

- **논증**: 힌트 경로의 위험은 "죽은 페이지" 와 "되살아난 남의 페이지" 두 상태뿐이다. 전자는 기존 `ER_PB_BAD_PAGEID` 분기가, 후자는 신규 ptype 재검증이 막는다. 재검증은 fix 로 latch 를 쥔 상태에서 수행하므로 검사와 사용 사이에 타입이 바뀔 틈이 없다 (타입 변경은 dealloc→realloc 을 거쳐야 하고, 그것은 latch 를 쥔 페이지에는 불가능).
- **회귀 테스트** (`unit_tests/oos/test_oos_bestspace.cpp`, `BestspaceStaleHintToNonOosPageIsRejected`): 파일 **자신의 파일테이블 헤더 페이지** (`PAGE_FTAB`, vpid = {fileid, volid}) 를 가리키는 독 힌트를 캐시에 심고, lookup 이 두 번 연속 그 페이지를 내주지 않으며 (첫 호출에서 퇴출됨) 반환 페이지의 타입이 항상 `PAGE_OOS` 임을 단정한다 — 별도 파일을 만들지 않고 "재할당된 비-OOS 페이지" 를 결정적으로 재현하는 구성이다.
- 부수 수정: 회수가 헤더의 `second_best[]` 링도 함께 청소하도록 하여 (minor `:1336`), 힌트 저장소 어디에도 회수된 페이지가 남지 않는다. lookup 측 재검증은 그와 독립적인 최종 방어선이다.

---

## B2. "next vacuum cycle 에 재시도" 주석이 사실과 다름 (blocker)

### Problem

회수 후보는 "이번 배치가 청크를 지운 페이지" 목록에서만 나오므로, busy 로 한 번 skip 된 페이지·eager 경로 (SA/카탈로그) 가 비운 페이지·PR 이전의 누적 빈 페이지를 다시 후보로 만드는 "다음 사이클" 은 존재하지 않았다. 주석만 재시도를 약속하고 있었다.

### Fix (commit `132163dab` — 성장 게이트 sweep; 주석 정비는 `7f3030a26`)

주석 삭제에 그치지 않고 **약속된 재시도 메커니즘을 실물로 구현**했다. 파일의 새 페이지 할당 지점 전부를 하나의 헬퍼로 단일화하고, 할당 직전에 sector-bitmap 기반 sweep 을 돌린다:

```c
/* oos_alloc_page_with_reclaim () - The single growth point of an OOS file.
 * INVARIANT: every new-page allocation for an OOS file goes through this helper ... */
static auto_unfix_page_ptr
oos_alloc_page_with_reclaim (THREAD_ENTRY *thread_p, const VFID &oos_vfid, VPID &vpid_out)
{
  int err = oos_reclaim_sweep_step (thread_p, oos_vfid);
  if (err == ER_INTERRUPTED)
    {
      return nullptr;
    }
  ...
  return oos_file_alloc_new (thread_p, oos_vfid, vpid_out);
}
```

`oos_reclaim_sweep_step` 은 per-VFID 카운터 (`oos_delete` 체인 1건당 +1) 가 켜져 있거나 boot rule (이번 부팅에 완주한 lap 없음) 이 적용될 때, bitmap 스냅샷을 저장된 커서부터 순회해 **첫 회수 성공에서 중단**한다. 회수된 페이지는 sweep 의 sysop 커밋 시점에 partial sector table 로 돌아가므로, 이어지는 `file_alloc` 이 재시도 루프 없이 그 페이지를 집는다.

리뷰 제안 ① (당시 죽은 필드 `full_search_vpid` 로 재개 지점 구현) 은 side-map 커서로 대체 구현했다 — 동일한 아이디어이되 in-memory 로 두고, 유실은 boot rule 이 흡수하므로 영속화가 불필요하다. 죽은 writer 는 제거했다.

### Validation

- **리뷰의 "영구 미회수" 4행이 전부 닫힘**: busy-skip 페이지 → 다음 성장 sweep 이 재발견 / eager 경로 → 카운터가 게이트를 무장 / 누적 부채 → boot rule 의 무조건 1바퀴 / 이번 배치분 → fast path 그대로.
- **단위 테스트** (`test_oos_growth_sweep.cpp`, 7종): 커밋된 삭제 burst 후 재삽입 시 페이지 수 불변 (회수·재사용), abort 복원 불간섭, incremental 중단 + 커서 연속 (full sweep 과 net 페이지 수로 구분), 카운터 리셋·재무장, 미커밋 삭제 deferred + 성장 허용, 재부팅 모사 후 무조건 sweep, 재충전 skip + sticky first page 절대 비회수.
- **실측** (리뷰어 H2SU 절차): 비압축 15KB × 14,000행 delete+재삽입 ×3 — SA 데이터 볼륨 **321MB ×4 flat** (AS-IS 320→640→768→1024MB), 서버 (vacuum 정착 후) 동일 footprint flat. 매 라운드 COUNT/값 등치 14,000.

---

## M1. record 단위 회수 + heap latch 보유 중 무조건 헤더 latch (major)

### Problem

회수가 heap home page WRITE latch 를 쥔 채 record 단위로 실행됐고, 후보마다 fhead fix ×2 + OOS 통계 헤더 (모든 INSERT 의 관문) 무조건 WRITE latch 를 지불했다.

### Fix (commits `b43950a38`, `50c18b7de`)

- 후보 누적을 heap 페이지 배치 (`vacuum_heap_page` 스코프의 `VACUUM_OOS_TOUCHED_PAGES`) 로 상향, 회수 호출은 **home page unfix 후** 배치당 1회 (`vacuum.c` 의 `end:` 합류 지점).
- 2단계 판정: 1단계 — 후보를 조건부 READ 로 fix 해 타입·emptiness·LSA 게이트를 선검사, 탈락하면 헤더를 건드리지 않음. 2단계 — 통과분만 헤더 WRITE latch 아래 재검증 후 dealloc.
- `file_get_sticky_first_page` / `file_is_numerable` 은 배치 진입 시 1회로 hoisting.

제안 (a) "헤더를 CONDITIONAL 로" 는 부분 채택이다: 헤더 latch 는 UNCONDITIONAL 을 유지하되, 그것을 잡는 주체가 "빈 페이지 확정분 + heap latch 무보유" 로 한정되어 원지적 (경합이 heap 대기로 전이) 이 소멸한다. 빈 페이지는 소수이고 어차피 dealloc 이라는 큰 작업을 동반하므로, CONDITIONAL 화로 얻을 추가 이득보다 재시도 경로의 복잡성이 크다고 판단했다.

### Validation

- 회수를 뒤로 미루는 변경의 안전성: 회수의 전제는 "삭제 커밋 이후" 뿐이고 멱등이므로, 시점 지연은 항상 안전 방향이다 (재충전된 페이지는 재검증이 skip).
- 1단계는 힌트, 구속력 있는 판정은 항상 헤더 latch 아래 2단계 — 기존 안전성 논증 (헤더 직렬화 / insert latch 연속성 / sysop-postpone 순서) 이 그대로 유지되고, LSA 게이트가 4항으로 추가됐다 (`oos_try_reclaim_page_internal` 주석).

---

## M3. `ER_INTERRUPTED` 를 삼키고 루프 계속 (major)

### Problem / Fix / Validation

회수 루프가 인터럽트를 warning + `er_clear()` 후 계속 진행했다. → 배치·sweep 루프 모두 인터럽트는 즉시 전파·중단으로 수정 (`50c18b7de`); vacuum 래퍼는 인터럽트만 반환하고 그 외 실패는 흡수한다. 셧다운 요청이 후보 목록 길이만큼 지연되는 일이 없어졌고, 중단 시 버려진 후보는 디스크에 남아 성장 sweep 이 재발견한다 (드롭이 안전한 이유).

---

## M4. 실효 검증 테스트 부재 — "회수 0회로도 통과" (major)

### Problem

페이지 수 상한 단정 (`+2`, `×2`) 은 회수가 한 번도 실행되지 않아도 bestspace 재사용만으로 통과했다 (리뷰어 계측: 관련 TC 전부 통과하는 동안 회수 호출 0회).

### Fix (commit `8ba9b5398`, `test_oos_vacuum_server.cpp` TC-V8/V9)

테스트가 실제 배치 회수를 통과하도록 배선하고, 단정을 실효 감지형으로 교체했다:

```c
/* TC-V9: 전부 삭제 → 커밋 → 배치 회수 → 페이지 수가 실제로 줄었는지 */
ASSERT_EQ (xtran_server_commit (thread_p, false), TRAN_UNACTIVE_COMMITTED);
err = vacuum_oos_reclaim_empty_pages (thread_p, &oos_vfid, &touched_pages);
...
EXPECT_LT (pages_after_reclaim, pages_after_insert);
EXPECT_EQ (pages_after_reclaim, 1);   /* sticky first page 만 남아야 한다 */
```

또한 `vacuum_heap_oos_delete_within_sysop` 의 `touched_pages_out = NULL` 기본 인자를 제거해, 회수 생략이 **호출자의 명시적 선택** (nullptr 전달) 이 되도록 했다 — "조용한 생략" 재발 방지.

### Validation

회수가 실행되지 않으면 `pages_after_reclaim == pages_after_insert` 가 되어 두 단정이 모두 실패한다 — 실효 미실행이 더는 통과할 수 없다. 전체 OOS 단위 스위트 28/28 (debug).

---

## 제안: `OLD_PAGE_PREVENT_DEALLOC` 미채택 근거

리더가 OOS 체인 페이지에 도달하는 유일한 경로는 살아 있는 레코드 버전 (또는 그 undo 이미지) 의 head OOS OID 이고, vacuum 은 **모든 활성 스냅샷에 불가시한 버전**의 체인만 삭제한다. 따라서 "리더가 순회 중인 체인의 페이지가 비어 회수되는" 시나리오가 성립하지 않는다 (heap 스캔과 달리 OOS 에는 임의 페이지 순회가 없다). 기존 dealloc 내성 (probe, `OLD_PAGE_MAYBE_DEALLOCATED`, 이번 ptype 재검증) 은 stale 힌트에 대한 심층 방어이며, PREVENT_DEALLOC 은 zero-wait 로 설계된 경로에 대기 간선을 되들이는 비용만 추가한다 — 이 근거를 `oos_try_reclaim_page_internal` 주석에 명시했다 (`8ba9b5398`).

---

## Minor 14건 처리 요약

| 처리 | 항목 |
|---|---|
| 반영 (8) | second_best 링 청소 · `full_search_vpid` 죽은 writer 제거 · 후보 수집 OOM 비치명화 (배치 롤백 제거) · 해시 후보의 best[] 슬롯 오염 · `oos_find_best_page` nullptr 검사 · fhead 조회 배치 1회 hoist · 레코드당 vector 생성 제거 · sync 추월 힌트 (ptype 재검증이 최종 방어선) |
| 후속 (6) | `log_skip_logging` no-op 정리 · 성장 경로 set_dirty · `oos_get_length` gone 보고 방식 · read/delete 경로 dealloc 내성 비대칭 명시 · ADR 문서 인리포 반영 · M2 (bitmap 컬렉터 상한/lazy iterator — insert 경로 sync 와 sweep 이 공유) |
| 의견 차 명시 (1) | `oos_delete` 의 `touched_vpids = NULL` 기본 인자 유지 — eager/forward-walk 호출자는 후보 리스트 부재가 정당하고 성장 sweep 이 backstop. 위험했던 vacuum 쪽 (`within_sysop`) 기본값만 제거 |

## 종합 검증 상태

- 단위: OOS 스위트 28/28 (debug, `UNIT_TEST_OOS=ON`) — 성장 sweep 7종 + B1 회귀 + 실효 감지형 TC-V8/V9 포함.
- 실측: H2SU 절차 재현 — SA flat 321MB ×4, 서버 (vacuum 정착 후) flat. vacuum 과 경주 시 유계 성장 후 flat (LSA 게이트의 의도된 보수성).
- 계약: 회수 모듈 배너가 불변식 ("모든 빈 OOS 데이터 페이지는 결국 파일 관리자로 반환; 새 섹터 예약은 안전하게 회수 가능한 빈 페이지가 없을 때만") 과 유계 보류 (LSA 게이트 / 동시 성장 skip / sweep 실패 흡수 / 비-`oos_delete` 비움) 를 명시.
