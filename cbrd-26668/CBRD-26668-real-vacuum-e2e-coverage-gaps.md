# CBRD-26668 — Real Vacuum E2E 테스트가 *놓치고 있는 것* (`test_oos_real_vacuum_server.cpp`)

> 대상 파일: `unit_tests/oos/test_oos_real_vacuum_server.cpp`
> 브랜치: `oos-vacuum` (base: `origin/feat/oos`)
> 이 문서의 목적: 이 E2E 테스트가 **현재 구조상 잡을 수 없는 커버리지 구멍**을 정리하고, 무엇을 추가로 테스트·검증하면 좋은지 우선순위와 함께 제안한다.
> 짝 문서: *무엇을* 검증하는지(TC-R1~R4) → [`CBRD-26668-real-vacuum-e2e-what-it-tests.md`](./CBRD-26668-real-vacuum-e2e-what-it-tests.md), *어떻게* 동작하는지 → [`CBRD-26668-real-vacuum-e2e-how-it-works.md`](./CBRD-26668-real-vacuum-e2e-how-it-works.md), 엔진 코드 → [`CBRD-26668-code-review-explanation.md`](./CBRD-26668-code-review-explanation.md).

---

## 0. 평결 (Verdict)

현재 4개 케이스(TC-R1~R4)가 노리는 4가지 속성 — REMOVE 경로 drain, 체인 완전 회수, UPDATE forward-walk, 스냅샷 게이트 — 의 커버리지는 **탄탄하다**. 구멍은 대부분 **TC-R3/TC-R4의 일반화**와, real-E2E 어떤 케이스도 건드리지 않는 **두 개의 별개 MVCC 로그 경로**에 있다.

> **구현 상태 (2026-06-15, branch `oos-vacuum`, commit `6c97e45e8`)**: 아래 구멍 중 6개를 TC-R5~R10으로 메웠다. `ctest --repeat until-fail:5`로 결정론성(determinism) 확인 완료.
>
> | 구멍 | 테스트 | 상태 |
> |---|---|:--:|
> | §1.1 다중 reader oldest 지평선 | TC-R5 `TwoReadersOldestSnapshotGatesReclaim` | ✅ |
> | §1.2 UPDATE forward-walk 스냅샷 게이트 | TC-R6 `UpdateSnapshotBlocksOldVersionReclaim` | ✅ |
> | §1.3 abort/undo 경로 회수 | — | ⛔ 범위 밖 (하니스의 out-of-band OOS 삽입 한계, prompt §Out of scope) |
> | §2.1 다중 버전 forward 체인 | TC-R8 `MultiVersionForwardChainDrains` | ✅ |
> | §2.2 한 pass에서 다중 dead 슬롯 | — | ⬜ 미구현 |
> | §2.3 음성/유효성 대조군 | TC-R7 `LiveRowNeverReclaimed` | ✅ |
> | §3.1 청크 경계 off-by-one | TC-R9 `ChunkBoundaryExactSizes` | ✅ |
> | §3.2 재-vacuum 멱등성 | TC-R10 `ReVacuumAfterDrainIsIdempotent` | ✅ |
>
> 구현 중 발견한 두 가지 결정론성 함정: (1) `oos_live_recs()`(=`oos_get_stats_by_vfid`)는 CONDITIONAL 래치로 busy 페이지를 건너뛰어 drain 도중 일시적으로 **undercount**할 수 있다 → 0이 아닌 목표 카운트 대기에는 UNCONDITIONAL-래치 read 경로(`oos_unreadable`)로 폴링한다. (2) 살아있는 데몬이 중간 stale 버전을 먼저 회수하면 직후의 `oos_insert`가 그 freed 슬롯을 재사용해 OID가 alias될 수 있다 → TC-R8은 두 교체 payload를 **회수 전에 모두 미리 삽입**해 이 경합을 구조적으로 제거한다.

> **먼저 알아둘 구조적 한계 (scope by construction)**: `insert_row_with_oos()`(소스 321–339행)는 OOS payload를 `test_oos_utils::oos_insert_from_recdes`로 **별도로** 만든 뒤, 그 OID를 박은 heap 레코드를 **손으로 빌드**(`build_heap_recdes_with_oos`)한다. 즉 이 테스트는 회수(reclaim) **소비자 쪽**을 E2E로 검증하지, 진짜 DML이 큰 컬럼을 OOS로 흘려보내는 **생산자 쪽(overflow-spill)** 은 검증하지 않는다. 카탈로그-프리 트릭의 당연한 귀결이며, 아래 구멍 중 일부가 "이 하니스에서 메울 수 있는가 vs SQL/medium 테스트가 필요한가"를 가른다.

---

## 1. P1 — 우선순위 높음 (별개의 정확성 속성, 진짜 DML로 도달 가능)

### 1.1 다중 reader의 "oldest visible" 지평선 (가장 큰 구멍) — ✅ TC-R5로 구현됨

TC-R4는 reader를 **정확히 1개만** 연다(소스 473행). 그래서 "reader 해제" ≡ "지평선 전진"이 되어버려, vacuum이 **가장 오래된** 스냅샷을 존중하는지 / 아니면 그냥 "스냅샷이 하나라도 사라졌는지"만 보는지 **구분할 수 없다**. 회수 판단은 살아있는 모든 스냅샷의 **전역 최소 active MVCCID**로 게이트된다.

- **제안 테스트**: reader **A**(오래된 스냅샷) → reader **B**(더 최신) 순서로 연다 → DELETE → 블록 닫음. **B**를 해제 → **여전히 회수 안 됨** 단언(A가 아직 본다) → **A** 해제 → 그제야 회수 단언.
- **검증하는 것**: `vacuum_get_global_oldest_visible` / MVCC 테이블의 지평선 계산. TC-R4로는 원리상 불가능한 검증.
- **실현성**: TC-R4가 이미 쓰는 `logtb_assign_tran_index` + tran-index 스위칭 패턴(471–477, 491–494행)을 그대로 reader 2개로 확장하면 됨. **낮은 비용.**

### 1.2 UPDATE forward-walk 경로의 스냅샷 게이트 (TC-R3 × TC-R4) — ✅ TC-R6로 구현됨

TC-R4가 게이트하는 건 DELETE/REMOVE 회수뿐이다. forward-walk 회수(`RVHF_UPDATE_NOTIFY_VACUUM`, TC-R3)는 **자체 가시성 검사를 가진 별개 경로**다. update로 밀려난 old 버전이 "update 이전 스냅샷을 가진 reader가 살아있는 동안" 읽기 가능하게 유지되는지는 **아무도 검증하지 않는다.**

- **제안 테스트**: INSERT(oos1) → update-이전 스냅샷 reader 오픈 → oos2로 UPDATE → 블록 닫음 → grace window 동안 oos1 **생존** 단언 → reader 해제 → oos1 drain·oos2 생존 단언.
- **검증하는 것**: 가시성 게이트가 REMOVE뿐 아니라 forward-walk 경로에도 동일하게 적용되는지.

### 1.3 ABORT된 INSERT/UPDATE → undo 경로 회수 — ⛔ 범위 밖 (하니스 한계)

모든 케이스가 생산자를 `commit`한다(소스 338, 442행). **abort된 insert**는 commit-delete-REMOVE와 **다른 복구 경로(undo)** 로 회수되는 죽은 버전을 만든다.

- **제안 테스트**: INSERT(oos) 후 commit 대신 `xtran_server_abort` → 블록 닫고 vacuum 대기 → OOS 회수 단언.
- **⚠️ 중요한 caveat**: 하니스가 OOS를 out-of-band로 넣기 때문에(위 §0), abort된 `heap_insert_mvcc`는 heap row를 undo하지만 **따로 삽입된 OOS는 production의 결합된 insert/undo와 같은 방식으로 추적되지 않을 수 있다.** 따라서 이 구멍은 의미 있게 메우려면 **하니스 수정**(OOS 생성을 heap op 경로로 태우거나, `oos_insert`가 같은 트랜잭션 하에 transactional한지 확인)이 선행돼야 할 수 있다 — 그리고 이 한계 자체가 검증 대상이다.

---

## 2. P2 — 중간 (견고성 / 배치 처리)

### 2.1 다중 버전 forward 체인 — ✅ TC-R8로 구현됨

TC-R3는 update를 **1번**만 해서 stale 버전이 1개다. INSERT(oos1)→UPDATE(oos2)→UPDATE(oos3)은 stale 버전이 **2개**(oos1, oos2)다. oos1·oos2 **모두** drain되고 oos3는 생존하는지 단언 → forward-walk가 직전 버전만이 아니라 **stale 계보 전체**를 회수하는지 확인.

### 2.2 한 번의 pass에서 다중 dead 슬롯 회수

TC-R2는 row 2개를 지우지만 **각각 별도** `delete_row_and_close_block` 호출(소스 403–404행)이라 별도 블록이다. 죽은 OOS-보유 row 여러 개를 **같은 heap 페이지/같은 블록**에 두고 한 번의 `vacuum_heap_page` sysop에서 전부 회수되는지 단언 → 배치 순회·부분 실패 처리 검증.

### 2.3 음성/유효성 대조군 (negative control) — ✅ TC-R7로 구현됨

회수가 **vacuum 때문에** 일어났음을 증명하는 게 없다. **살아있는(삭제 안 된) row**의 OOS는 블록을 아무리 닫고 데몬을 아무리 깨워도 **절대 읽기 불가가 되면 안 된다**는 대조 테스트 추가 → 어떤 우발적 eager 경로가 청소해버린 false-green을 막는다.

---

## 3. P3 — 저비용 핀(pin)

### 3.1 청크 경계 off-by-one — ✅ TC-R9로 구현됨

TC-R2는 `max_chunk+100`과 160KB를 쓴다. **정확히 `max_chunk`**(1청크)와 **`max_chunk+1`**(막 2청크로 넘어감)을 추가해 insert와 reclaim walk 양쪽의 청크 개수 산술을 핀한다.

### 3.2 in-process 재-vacuum 멱등성 — ✅ TC-R10로 구현됨

drain 이후 데몬을 **다시** 명시적으로 깨우고 `oos_live_recs()`가 0으로 유지되며 크래시가 없음을 단언 → no-crash double-pass 가드(크래시-복구와는 별개이며, 크래시-복구는 정당하게 범위 밖).

---

## 4. 요약 (TL;DR)

- **[완료]** 가장 메울 가치가 큰 **§1.1(다중 reader 지평선 → TC-R5)** 과 **§1.2(UPDATE 경로 스냅샷 게이트 → TC-R6)** 를 구현했다. 둘 다 기존 4개 케이스가 **구조상 잡을 수 없던** 진짜 정확성 속성(MVCC 지평선, 경로별 가시성 게이트)이며, TC-R4의 index-스위칭 패턴을 그대로 확장했다.
- **[완료]** §2.1(다중 버전 forward 체인 → TC-R8), §2.3(음성 대조군 → TC-R7), §3.1(청크 경계 → TC-R9), §3.2(재-vacuum 멱등성 → TC-R10) 도 구현. 총 6개 케이스, `ctest --repeat until-fail:5` 로 결정론성 확인.
- **[보류]** **§1.3(abort/undo 경로)** 는 하니스의 out-of-band OOS 삽입 한계 때문에 하니스 수정이 선행돼야 한다 — prompt의 *Out of scope* 와 일치하게 이번 범위에서 제외(그 한계 자체가 추후 검증 포인트). **§2.2(한 pass 다중 dead 슬롯)** 는 미구현으로 남겨둠.
- §2~§3의 디스크 레벨 공간 회수·crash recovery·생산자 overflow-spill은 여전히 **이 파일 범위 밖**이며 leaf/mock 테스트와 SQL/medium 테스트가 담당(→ what-it-tests §2의 비-목표 참고).
