# PR #7617 리뷰 대응 보고서 — hornetmj 리뷰 (2026-08-27) 의 문제·수정 코드·검증

- **PR**: [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617) — [CBRD-26786] OOS 빈 페이지 회수
- **리뷰 기준 head**: `66cd3cc` / **본 보고서 기준 head**: `8ba9b5398`
- **작성일**: 2026-09-01 (agent: claude, 저자 검수)
- **쉬운 설명 개정**: 2026-09-01 (agent: codex)

리뷰 항목마다 ① 실제로 어떤 일이 벌어지는지 ② 왜 위험한지 ③ 어떻게 고쳤는지 ④ 무엇으로 검증했는지를 순서대로 설명한다. 리뷰가 옛 head 를 기준으로 작성된 뒤 커밋 스택 (`50c18b7de` → `b43950a38` → `ac926cb5b` → `132163dab` → `7f3030a26`) 이 올라갔고, 리뷰 후 신규 수정은 `8ba9b5398` 하나다.

## 먼저 읽기: blocker 두 건을 한눈에

| 항목 | 쉽게 말하면 | 실제 위험 |
|---|---|---|
| **B1** | OOS 가 오래된 "빈 공간 메모"를 믿고, 이제는 다른 용도로 쓰이는 페이지에 데이터를 쓸 수 있었다. | 다른 파일의 메타데이터 손상 |
| **B2** | 빈 페이지 회수를 한 번 시도했다가 실패하면, 그 페이지를 다시 찾는 장치가 없었다. | 빈 공간이 있어도 파일이 계속 커짐 |

두 문제는 성격이 다르다. **B1 은 잘못된 페이지에 쓰는 정확성 문제**이고, **B2 는 빈 페이지를 영원히 잊을 수 있는 공간 회수 문제**다. 둘 다 실제 데이터베이스 손상 또는 반복 가능한 파일 증가로 이어질 수 있으므로 merge blocker 로 분류됐다.

> **문서 범위:** 아래 B1 수정 설명은 보고서 기준 head `8ba9b5398` 의 비-OOS 페이지 타입 방어를 다룬다. 이후 `9d55b4484` 에서 타입이 같은 다른 OOS 파일의 페이지도 소유권 검사로 거부하도록 보강됐고, `bd0766dbb` 에서 그 소유권 검사의 assertion 정책만 정리됐다.

---

## B1. stale bestspace 힌트가 재할당된 비-OOS 페이지를 가리킬 때 쓰기 손상 (blocker)

### 한 문장으로 설명

OOS 가 "이 페이지에는 빈 공간이 있다"는 오래된 힌트를 따라갔는데, 그 페이지가 이미 다른 파일의 메타데이터 페이지로 재사용된 경우에도 OOS 레코드를 써 버릴 수 있었다.

### 어떻게 발생하는가

bestspace 힌트는 정확성을 보장하는 소유권 정보가 아니라, INSERT 를 빠르게 하기 위해 저장해 둔 **페이지 번호 메모**다. 따라서 실제 페이지의 수명과 힌트의 수명이 어긋날 수 있다.

예를 들어 다음 순서가 가능했다.

1. OOS 가 `page 100` 에 빈 공간이 있다고 기록한다.
2. 나중에 `page 100` 이 완전히 비어서 파일 관리자에게 반환된다.
3. 파일 관리자가 같은 물리 페이지를 다른 파일의 파일테이블 페이지 (`PAGE_FTAB`) 로 재사용한다.
4. 오래된 OOS 힌트는 여전히 `page 100` 을 가리킨다.
5. OOS INSERT 가 힌트를 따라 `page 100` 을 fix 한다. 여기서 fix 는 버퍼 풀에서 페이지 접근 권한과 latch 를 얻는 동작이다. 페이지가 현재 존재하므로 fix 는 성공한다.
6. 기존 코드는 "fix 성공"만 확인하고 그 페이지를 OOS 페이지처럼 해석해 레코드를 쓸 수 있었다.

```text
오래된 힌트: "page 100 에 빈 공간 있음"
                       │
page 100: OOS → 반환 → 다른 파일의 PAGE_FTAB 로 재사용
                       │
                       └─ fix 성공 → OOS 레코드 쓰기 → 다른 파일 손상
```

기존 `ER_PB_BAD_PAGEID` 검사는 2번과 3번 사이, 즉 페이지가 아직 미할당 상태일 때만 막아 준다. 다른 용도로 재할당된 뒤에는 페이지가 다시 유효하므로 이 오류가 발생하지 않는다.

### 왜 blocker 인가

잘못 쓰는 대상이 단순한 빈 페이지가 아니라 **다른 파일이 사용 중인 페이지**다. 특히 `PAGE_FTAB` 같은 파일 메타데이터를 덮어쓰면 해당 파일 전체가 손상될 수 있다. release 빌드에서는 내부 assert 가 실행을 중단하지 않으며, 잘못된 쓰기가 WAL 에 기록되면 재시작 후 redo 에서도 다시 적용될 수 있다.

읽기 전용 경로들은 이미 페이지 타입을 검사하고 있었다. 실제 OOS INSERT 로 이어지는 bestspace lookup 경로만 이 검사가 빠져 있었다.

### 어떻게 고쳤는가

commit `8ba9b5398` 의 `oos_stats_find_page_in_bestspace` 는 fix 직후, 빈 공간 정보를 읽기 전에 페이지 타입부터 확인한다. `PAGE_OOS` 가 아니면 페이지를 사용하지 않고 오래된 힌트를 삭제한 뒤 다음 후보를 찾는다.

```c
if (pgbuf_get_page_ptype (thread_p, *out_pgptr) != PAGE_OOS)
  {
    pgbuf_unfix_and_init (thread_p, *out_pgptr);
    oos_stats_evict_stale_hint (thread_p, &candidate_vpid, found_in_hash, bestspace, best_array_index);
    notfound_cnt++;
    continue;
  }
```

타입 검사와 이후 사용은 같은 page latch 를 잡은 상태에서 이루어진다. 따라서 검사를 통과한 뒤 사용하기 전에 그 페이지가 회수되고 다른 타입으로 바뀌는 경쟁은 일어날 수 없다.

### 무엇으로 검증했는가

- 회귀 테스트 `BestspaceStaleHintToNonOosPageIsRejected` 가 일부러 `PAGE_FTAB` 을 가리키는 잘못된 힌트를 넣는다.
- lookup 이 해당 페이지를 반환하지 않는지, 첫 실패에서 힌트를 제거하는지, 최종 반환 페이지가 `PAGE_OOS` 인지를 확인한다.
- 회수 시 `second_best[]` 에 남은 같은 페이지도 청소한다. lookup 의 타입 검사는 힌트 청소가 누락되더라도 잘못 쓰지 않게 하는 마지막 방어선이다.

> **후속 보강:** `PAGE_OOS` 타입만으로는 "내 OOS 파일의 페이지"와 "다른 OOS 파일의 페이지"를 구분할 수 없다. 이 경우는 이후 commit `9d55b4484` 의 `file_is_vpid_in_file` 소유권 검사와 `BestspaceStaleHintToForeignOosPageIsRejected` 테스트로 막았다.

---

## B2. "next vacuum cycle 에 재시도" 주석이 사실과 다름 (blocker)

### 한 문장으로 설명

빈 OOS 페이지를 회수하려다가 한 번 실패하면, 나중에 그 페이지를 다시 후보로 올리는 장치가 없어서 빈 페이지가 영구적으로 버려질 수 있었다.

### 어떻게 발생하는가

기존 fast path 는 **이번 vacuum 배치에서 OOS 청크를 삭제한 페이지들만** 회수 후보로 받았다.

예를 들어 다음 순서가 가능했다.

1. vacuum 이 `page 200` 의 마지막 OOS 청크를 지운다. 이제 페이지 전체가 비었다.
2. 같은 배치에서 `page 200` 회수를 시도하지만, 다른 스레드가 잠깐 사용 중이라서 skip 한다.
3. 다음 vacuum 배치는 다른 페이지를 처리한다. `page 200` 에서는 새 삭제가 일어나지 않으므로 후보 목록에 다시 들어오지 않는다.
4. 이후 INSERT 는 `page 200` 이 비어 있다는 사실을 모른 채 새 페이지를 할당한다.

```text
page 200 이 비어짐 → 회수 1회 시도 → 잠깐 busy → skip
                                               │
                                               └─ 재등록 장치 없음 → 영구 미회수
```

따라서 코드 주석의 "next vacuum cycle 에 재시도"는 실제 동작이 아니었다. 다음 cycle 이 같은 페이지를 다시 발견할 근거가 없었기 때문이다. SA_MODE 같은 eager 삭제 경로가 비운 페이지와 PR 적용 전부터 존재하던 빈 페이지는 처음부터 vacuum 후보 목록에 들어오지도 않았다.

### 왜 blocker 인가

빈 페이지가 실제로 존재해도 OOS 파일은 계속 새 페이지와 새 sector 를 할당할 수 있다. INSERT/DELETE 를 반복할수록 데이터 양은 같아도 파일 크기가 계속 증가하므로, "완전히 빈 OOS 페이지는 결국 파일 관리자에게 반환된다"는 CBRD-26786 의 핵심 요구를 만족하지 못한다.

### 어떻게 고쳤는가

commit `132163dab` 는 새 페이지를 할당하려는 순간에 마지막 확인을 하는 **growth-gate sweep** 을 추가했다. 주석만 바꾼 것이 아니라, 놓친 빈 페이지를 다시 찾는 실제 경로를 만들었다.

동작은 다음과 같다.

1. `oos_delete` 가 실행되면 해당 OOS 파일에 "회수할 것이 있을 수 있음"을 나타내는 카운터를 올린다. 이 카운터는 정확한 페이지 목록이 아니라 sweep 을 켜는 힌트다.
2. 모든 OOS 새 페이지 할당은 `oos_alloc_page_with_reclaim` 한 곳을 통과한다.
3. 정말 새 페이지를 할당하기 전에 `oos_reclaim_sweep_step` 이 파일 관리자의 페이지 할당 지도인 sector bitmap 에 있는 실제 페이지들을 저장된 커서부터 확인한다.
4. 안전하게 회수할 수 있는 빈 페이지 하나를 찾으면 반환하고 sweep 을 멈춘다. 바로 뒤의 `file_alloc` 이 방금 반환된 공간을 재사용한다.
5. 아직 활성 트랜잭션의 rollback 에 필요할 수 있는 페이지는 LSA gate 로 보류하고, 다음 성장 시 다시 확인한다.
6. 재시작으로 메모리 카운터를 잃어도, boot rule 이 부팅 후 최소 한 바퀴를 강제로 돌려 오래된 빈 페이지를 다시 찾는다.

핵심은 **vacuum 후보 목록을 놓쳐도, 파일이 커지기 직전에 디스크의 sector bitmap 을 다시 확인한다**는 점이다.

```c
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

저장된 커서는 매번 파일 전체를 처음부터 훑는 비용을 피한다. 커서는 메모리에만 있지만, 유실 시 boot rule 이 다시 한 바퀴 돌기 때문에 정확성에는 영향을 주지 않는다.

### 무엇으로 검증했는가

- 이번 vacuum 배치의 fast path 에서 회수되지 않은 빈 페이지를 다음 성장 sweep 이 다시 발견하는지 확인한다.
- 커밋된 삭제 후 같은 양을 재삽입해도 페이지 수가 증가하지 않는지 확인한다.
- 미커밋 삭제 페이지는 회수하지 않되 INSERT 자체는 계속 가능한지 확인한다.
- 중단한 위치의 다음 페이지부터 이어서 확인하는지, 카운터가 완료 후 리셋되고 새 삭제에서 다시 켜지는지 확인한다.
- 재부팅을 모사해 메모리 힌트가 없어도 boot rule 이 빈 페이지를 찾는지 확인한다.
- sticky first page 는 어떤 경우에도 회수하지 않는지 확인한다.
- 리뷰어의 15KB × 14,000행 delete/reinsert 반복 절차에서 SA 데이터 볼륨이 **321MB로 유지**됐다. 수정 전에는 같은 절차에서 320MB → 640MB → 768MB → 1024MB로 계속 증가했다. 서버 모드도 vacuum 정착 후 같은 크기로 유지됐다.

> **후속 보강:** 두 단계 검사 사이에서 phase-2 WRITE fix 가 일시적으로 실패한 경우에도 회수 부채를 유지하도록 commit `9d55b4484` 에서 보강했고, `TransientWriteLatchMissKeepsReclaimDebt` 테스트를 추가했다.

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
