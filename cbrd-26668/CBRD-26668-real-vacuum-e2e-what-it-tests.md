# CBRD-26668 — Real Vacuum E2E 테스트가 *무엇을* 검증하나 (`test_oos_real_vacuum_server.cpp`)

> 대상 파일: `unit_tests/oos/test_oos_real_vacuum_server.cpp`
> 브랜치: `oos-vacuum` (base: `origin/feat/oos`)
> 이 문서의 목적: 이 E2E 테스트가 *무엇을, 왜* 검증하는지 — 형제 테스트들 사이에서의 위치, 테스트 케이스별(TC-R1~R4) 커버리지, 그리고 **무엇은 보장하고 무엇은 아닌지** — 를 정리한다.
> 짝 문서: *어떻게* 동작하는지(파이프라인·인프라·트릭·빌드)는 [`CBRD-26668-real-vacuum-e2e-how-it-works.md`](./CBRD-26668-real-vacuum-e2e-how-it-works.md) 를 보라. 엔진 코드 자체는 [`CBRD-26668-code-review-explanation.md`](./CBRD-26668-code-review-explanation.md).

---

## 0. 한눈에 보기 (Executive Summary)

OOS 회수가 제대로 동작한다는 걸 증명하려면 결국 **"진짜 vacuum이 돌았을 때 죽은 OOS 청크가 사라지는가"** 를 봐야 한다. 그런데 vacuum은 혼자 도는 게 아니라 **여러 층(layer)을 거치는 파이프라인**이다(상세 사슬은 → how-it-works 문서 §1). 그래서 이 디렉터리는 같은 동작("죽은 OOS 청크를 회수한다")을 **3단 피라미드**로 나눠 검증한다. 각 단계는 바로 아랫단보다 "진짜 코드"를 한 겹씩 더 사용한다.

| 테스트 파일 | 무엇을 직접 호출? | 무엇을 가짜로 두나? | 증명하는 것 |
|---|---|---|---|
| `test_oos_mock_vacuum_server.cpp` | `oos_delete()` 를 직접 호출 | vacuum 로직 **전부** (사람이 손으로 delete) | OOS 파일의 삭제·공간 회수 *말단* 동작 |
| `test_oos_vacuum_server.cpp` | `vacuum_heap_oos_delete_within_sysop()` (leaf 함수) | 로그·데몬·워커 (직접 RECDES를 만들어 leaf에 투입) | "heap recdes → OOS OID 추출 → 삭제" *leaf 로직* |
| **`test_oos_real_vacuum_server.cpp`** | **MVCC DML만 호출하고 나머진 진짜 vacuum이 처리** | **아무것도 가짜로 두지 않음 (E2E)** | **MVCC→로그→데몬→워커→회수** 전체 사슬 |

> **비유**: 같은 "쓰레기 수거"를 세 단계로 검증한다. ① 쓰레기를 손으로 직접 소각장에 던져 소각로가 태우는지 본다(mock). ② 수거차의 *압축기* 부품만 떼어내 쓰레기를 직접 넣어보고 압축되는지 본다(leaf). ③ **봉투를 길가에 내놓고, 진짜 수거차가 와서 가져가는지** 본다(real E2E). 이 문서는 ③번에 대한 것이다.

핵심 한 줄: **이 테스트는 vacuum master 데몬이 실제로 깨어나, 닫힌 로그 블록을 찾아내고, 워커를 통해 죽은 heap 슬롯의 OOS를 끝까지(모든 청크·모든 체인) 회수하는지를, 그리고 "아직 보고 있는 트랜잭션이 있으면 회수하지 않는지"를 검증한다.**

---

## 1. 테스트 케이스별 커버리지 (TC-R1 ~ TC-R4)

fixture `OosRealVacuum`는 테스트마다 진짜 heap + 거기 붙은 OOS 파일을 만들고(`xheap_create` → `heap_oos_find_vfid`), 끝나면 `xheap_destroy`한다. 공통 헬퍼: `insert_row_with_oos()`(OOS payload + 그걸 가리키는 heap row를 넣고 commit), `delete_row_and_close_block()`(heap row를 MVCC-delete, commit, 블록을 닫음), `expect_oos_gone()`(OOS OID가 읽기 불가임을 확인).

### TC-R1 — `SingleRowDeleteDrainsCompletely`
- **시나리오**: 4096B OOS 1개를 가진 row 1개 INSERT → DELETE → 블록 닫고 vacuum 대기.
- **검증**: `oos_live_recs() == 0` 이 되고, 해당 OID가 읽기 불가.
- **커버하는 코드 경로**: 가장 기본적인 **REMOVE 경로** — 죽은 REC_HOME 슬롯을 vacuum이 물리적으로 지우면서 그 슬롯이 가리키던 OOS도 함께 회수(`vacuum_heap_oos_delete_within_sysop`).

### TC-R2 — `MultiChunkChainsDrainCompletely`
- **시나리오**: 멀티-청크 2개를 만든다 — (a) `max_chunk + 100`B(2청크 보장), (b) 160KB(16KB 페이지에서 ~10페이지). 둘 다 DELETE.
- **검증**: 삭제 전 `oos_live_recs() >= 3`(2+2 청크 이상), 삭제 후 `== 0`. `oos_live_recs()`가 청크 단위라서 **체인 전체**가 회수됐음을 증명(머리 청크만 지우는 버그를 잡음).
- **커버하는 코드 경로**: REMOVE 경로의 **체인 walk 삭제**(`oos_delete`가 체인을 내부적으로 따라가며 모든 청크 free).

### TC-R3 — `UpdateStaleVersionDrainsNewSurvives`
- **시나리오**: row INSERT(old OOS) → 새 OOS를 만들고 heap row를 그쪽으로 MVCC UPDATE → 블록 닫고 대기.
- **검증**: `oos_live_recs()`가 **정확히 1 row 분량으로 복귀**(old만 회수, new는 생존). old OID는 읽기 불가, new OID는 여전히 읽기 가능하며 길이도 일치.
- **커버하는 코드 경로**: **Forward-walk 경로**(`RVHF_UPDATE_NOTIFY_VACUUM`). UPDATE된 살아있는 슬롯은 더 이상 old OID를 가리키지 않고, old OID는 undo 로그 이미지에만 남아 있다. vacuum이 그 이미지를 읽어 회수하는지를 검증한다 — REMOVE 경로와 구분되는 **별개의 회수 경로**.

### TC-R4 — `SnapshotBlocksReclaimThenDrains`  ← "stale"의 정의를 검증
- **시나리오**: row INSERT → **delete 이전 시점의 스냅샷을 가진 reader 트랜잭션**을 연다(`logtb_assign_tran_index` + `TRAN_REPEATABLE_READ`, tran index를 worker↔reader로 스위칭) → row DELETE → 블록 닫음.
- **검증 (2단계)**:
  1. **grace window(3초)** 동안 vacuum이 회수하면 **안 됨**(`EXPECT_FALSE(drained_early)`). 살아있는 스냅샷에 보이는 OOS는 여전히 읽기 가능해야 함.
  2. reader를 abort/release한 뒤(`log_abort` + `logtb_release_tran_index`) 다시 폴링하면 **그제야 회수**되어야 함.
- **커버하는 것**: vacuum의 **MVCC 정확성** — "stale(회수 가능)"은 *시간*이 아니라 *가시성*의 문제다. **살아있는 어떤 트랜잭션도 더는 볼 수 없을 때만** 회수해야 한다. 이게 OOS 회수가 데이터 유실을 일으키지 않음을 보장하는 핵심 안전 속성이다.

---

## 2. 커버리지 매트릭스 (무엇을 보장하고, 무엇은 아닌가)

| 검증 축 | TC-R1 | TC-R2 | TC-R3 | TC-R4 |
|---|:--:|:--:|:--:|:--:|
| DELETE 후 REMOVE 경로 회수 | ✅ | ✅ | — | ✅ |
| 멀티-청크 체인 **완전** 회수 | — | ✅ | — | — |
| UPDATE old-version forward-walk 회수 | — | — | ✅ | — |
| 신버전/생존 데이터 보존 | — | — | ✅ | (✅) |
| MVCC 가시성(스냅샷이 회수 차단) | — | — | — | ✅ |
| master 데몬 wake→worker 실제 구동 | ✅ | ✅ | ✅ | ✅ |

**명시적으로 다루지 않는(또는 다른 테스트가 담당하는) 부분:**
- **Eager(즉시) 청소 경로**(`heap_oos_delete_unreferenced`, SA_MODE/non-MVCC) — 이건 SA_MODE 테스트(`test_oos_delete` 등) 영역. real 테스트는 MVCC 지연 경로 전용.
- **REC_RELOCATION forward 슬롯**과 함께 가는 회수의 디스크 레이아웃 세부 — leaf 테스트(`test_oos_vacuum_server`)와 코드 리뷰 가이드 §6/§7이 담당.
- **공간 재사용/페이지 바운드**(누수 없이 free space가 실제로 줄어드는지) — mock/leaf 테스트의 `*ReclaimAndReuse`, `MultiUpdate*` 케이스가 `file_get_num_user_pages`/`spage_get_free_space`로 검증. real 테스트는 "사라졌는가"(`oos_live_recs`/읽기 실패)에 집중.
- **크래시/복구(recovery) 시 회수의 멱등성** — 이 파일 범위 밖(멀티페이지 로깅 설계는 별도).
- **동시 다중 reader/writer 경합** — TC-R4는 단일 reader 1개만 사용.

> 요약: real 테스트는 **"진짜 vacuum이 정말 돈다 + MVCC 의미상 옳게 회수한다"** 를 증명하고, **"회수의 디스크 레벨 정확성/공간 회수"** 는 leaf·mock 테스트가 받친다. 셋이 합쳐져야 회수 동작 전체가 커버된다.

---

## 3. 핵심 요약 (TL;DR — 커버리지)

- `test_oos_real_vacuum_server.cpp`는 OOS 회수의 **유일한 진짜 E2E 테스트**다(형제 mock/leaf 테스트와 3단 피라미드를 이룬다). 진짜 vacuum이 정말 돌고, **MVCC 의미상 옳게** 회수하는지를 본다.
- 4개 케이스가 (R1) 단일 삭제 완전 회수, (R2) 멀티-청크 체인 완전 회수, (R3) UPDATE old-version forward-walk 회수+신버전 보존, (R4) **스냅샷이 회수를 차단했다가 해제 시 회수**(=MVCC "stale" 정의)를 커버한다.
- 핵심 안전 속성: **살아있는 어떤 트랜잭션도 더는 볼 수 없을 때만** 회수한다(TC-R4). "stale"은 시간이 아니라 가시성의 문제 — 이게 OOS 회수가 데이터 유실을 일으키지 않음을 보장한다.
- 다루지 **않는** 것: eager(SA_MODE) 청소, 디스크 레벨 공간 재사용, 크래시 복구 멱등성, 다중 reader/writer 경합. 이것들은 leaf·mock 테스트와 코드 리뷰 가이드가 받친다 — 셋을 함께 읽어야 전체 그림이 보인다.
- *어떻게* 굴러가는지(서버 부팅·블록 닫기·db_user OID 트릭 등)는 [`CBRD-26668-real-vacuum-e2e-how-it-works.md`](./CBRD-26668-real-vacuum-e2e-how-it-works.md).
