# CBRD-26950: 신원 스탬프를 generation counter 대신 page LSA 로 — 제안 평가

- **PR**: [CUBRID/cubrid#7695](https://github.com/CUBRID/cubrid/pull/7695) `[CBRD-26950] Verify OOS chain identity before vacuum delete`
- **평가 대상**: [hgryoo 님의 제안 코멘트](https://github.com/CUBRID/cubrid/pull/7695#issuecomment-5325201442) (2026-08-18) — "generation counter 대신 page LSA 를 쓰면 어떨까요"
- **기준 커밋**: PR HEAD `ecebe6288` (feat/oos 파생 브랜치)
- **작성**: 2026-08-20, Claude Code (Fable 5) 분석, dhkim 검수

## TL;DR

제안에 **동의한다.** generation counter 가 필요로 하는 관리 장치 다섯 가지 (slot 0 헤더 레코드, `RVOOS_NEWPAGE` 복구 인덱스, redo 의 MAX 재생, wrap-around 은퇴 로직, 페이지 재활용 시 리셋 계약) 가 page LSA 에서는 **전부 사라진다**는 주장을 코드로 검증했고 모두 사실이다. 제안자가 미확인으로 남긴 두 가지 (LSA 되감기 절차, 배치 삽입) 도 확인 결과 수용 가능하다. 남는 비용은 스탬프가 4B 대신 8B 라는 것 하나다. 후속 작업인 CBRD-27230 (UPDATE 체인 재사용) 은 스탬프를 "삭제 재시도 멱등성 토큰"으로만 사용하므로 이 교체에 영향을 주지도, 받지도 않는다.

---

## 1. 배경 — 이 PR 이 고치는 버그와 "신원 스탬프"

### 1.1 버그: vacuum 이 재사용된 슬롯의 살아있는 데이터를 지운다

OOS 는 큰 가변 컬럼 값을 heap 레코드 밖의 OOS 파일에 저장하고, heap 레코드에는 16B 참조 (OOS inline stub: head OOS OID 8B + 전체 길이 8B) 만 남긴다. 여기서 **OOS OID 는 물리 주소** (volid | pageid | slotid) 라는 점이 문제의 뿌리다.

vacuum 은 죽은 레코드 버전의 OOS 값 체인을 회수하는데, 작업 진행 상황 (`start_lsa`) 이 **블록 단위로만 전진**한다. 블록 처리 중 중단되면 (worker 중단, 중간 오류, crash) 블록 전체를 처음부터 다시 돌린다. 이때:

```
T1  vacuum 이 undo image 에서 head OOS OID (1|50|3) 을 읽어 체인 삭제 → 슬롯 해제
T2  다른 행의 oos_insert 가 같은 슬롯 (1|50|3) 을 재사용            → 새 주인 입주
T3  vacuum 이 중단됐다가 블록 재시도 — 같은 (불변의) undo image 에서
    같은 (1|50|3) 을 다시 도출
T4  oos_delete (1|50|3) → 이번엔 "새 주인"의 살아있는 체인을 삭제    → 조용한 데이터 손실
```

기존 방어였던 `oos_chunk_exists` 는 "슬롯이 점유돼 있는가"만 보지 "**내가 알던 그 주인인가**"는 묻지 못한다 — T4 에서 슬롯은 점유돼 있으므로 (새 주인) 오히려 삭제를 통과시킨다. 체인이 여러 청크면 `next_chunk_oid` 를 따라가며 체인 전체가 증발한다.

### 1.2 현재 PR 의 해법: generation counter

"그 슬롯의 지금 주인이, 내 참조가 만들어졌을 때의 그 주인인가?"를 물을 수 있도록 **점유(occupancy)마다 신원 값을 발급**한다:

- 각 OOS 데이터 페이지의 slot 0 에 `OOS_PAGE_HEADER` 레코드를 두고, 그 안의 `generation_counter` 에서 발급 (`oos_file.cpp:1615`)
- 발급된 generation 을 **청크 헤더** (+4B) 와 **stub** (16B → 20B) 양쪽에 기록
- `oos_delete (oid, expected_generation)` 은 head 청크의 저장값과 대조해 **불일치 (슬롯 재사용됨)·부재 (이미 회수됨) 면 무해한 no-op** (`oos_file.cpp:2524` 주석)

위 T4 에서 새 주인의 generation 은 다른 값이므로 대조가 실패하고, 재시도 삭제는 no-op 이 된다. **이 계약 (no-op on mismatch/absence) 자체는 어떤 스탬프를 쓰든 그대로다** — 이 문서의 주제는 "스탬프 값을 어디서 얻느냐"뿐이다.

---

## 2. 제안 — page LSA 를 스탬프로 쓰자

### 2.1 page LSA 란?

CUBRID 의 모든 데이터 페이지는 헤더에 **LSA (Log Sequence Address)** 를 가지고 있다: *이 페이지에 마지막으로 적용된 로그 레코드의 주소*다. WAL 규칙에 따라 페이지를 수정하는 모든 로깅된 연산이 이 값을 갱신하며, 로그 주소는 전역적으로 단조 증가하므로 **한 페이지의 LSA 는 절대 뒤로 가지 않는다**. 복구(redo) 도 이 값을 기준으로 "이 로그는 이미 적용됐나"를 판단한다 — 즉 LSA 의 유지·복구는 엔진의 기존 기계가 이미 하고 있는 일이다.

레코드 안에 LSA 를 싣는 선례도 있다: MVCC 헤더의 `prev_version_lsa`.

### 2.2 왜 스탬프 자격이 있는가

스탬프에 필요한 성질은 단 하나다: **같은 슬롯의 서로 다른 두 점유가 항상 다른 값을 관측할 것.** 삽입 시점의 페이지 LSA 를 스탬프로 쓰면 이게 공짜로 성립한다. 슬롯이 재사용되려면 먼저 이전 점유를 지운 delete 가 있어야 하고, 그 delete 자체가 이 페이지에 로깅되어 페이지 LSA 를 전진시키기 때문이다:

```
페이지 LSA:  L0 ──[insert A, 스탬프=L0]──▶ L1 ──[delete A]──▶ L2 ──[insert B, 스탬프=L2]──▶ L3

  A 의 참조를 든 재시도 삭제: expected = L0, 현재 청크의 스탬프 = L2 → 불일치 → no-op ✓
```

구현도 드롭인이다: 발급 지점 (`oos_insert_record_in_fixed_page`) 은 이미 페이지 W-latch 를 쥐고 있으므로 (`oos_file.cpp:1595` 주석) counter 증가 대신 `pgbuf_get_lsa (page_ptr)` 한 줄을 읽으면 된다. OOS 파일은 `file_create (..., false /* is_temp */)` 로 만들어지는 영구 파일이라 로깅을 우회하는 삽입 경로도 없다.

한 가지 주의점 (제안 코멘트가 정확히 지적): 스탬프는 반드시 **삽입 직전의** 페이지 LSA 여야 한다. redo 시 `log_rcv` 는 적용 중인 레코드 자신의 LSA 를 갖지 않으므로, "로그를 먼저 쓰고 그 LSN 을 레코드에 덧쓰는" 형태는 복구에서 재유도할 수 없다. 스탬프가 청크 이미지 안에 있으면 redo 는 이미지를 그대로 복원하기만 하면 된다.

---

## 3. counter 가 끌고 다니는 관리 장치들 — 하나씩 뜯어보기

counter 는 "없던 상태를 새로 만드는" 선택이라, 그 상태의 생애 전체 (저장 위치, 복구, 포화, 리셋) 를 우리가 직접 관리해야 한다. 현재 PR 에 실제로 존재하는 장치들이다.

### 3.1 slot 0 헤더 레코드 — counter 의 집

counter 값은 어딘가 내구성 있게 살아야 한다. 현재 설계는 **모든 OOS 데이터 페이지의 slot 0** 에 `OOS_PAGE_HEADER` 레코드를 심는다. 페이지마다 레코드 하나 + 슬롯 엔트리 하나만큼 사용자 데이터 용량이 줄고, 모든 청크 접근 코드가 "slot 0 은 청크가 아님"을 알아야 한다 (`OOS_PAGE_HEADER_SLOT` 특별 취급이 삽입·삭제·체인 순회 곳곳에 있다).

**LSA 라면**: 페이지 헤더의 기존 LSA 를 재사용하므로 이 레코드 자체가 필요 없다.

### 3.2 `RVOOS_NEWPAGE` 는 왜 신설됐나 — 그리고 LSA 면 왜 사라지나

`file_alloc` 이 새 페이지를 내주면 모듈의 init 콜백이 페이지를 포맷한다. WAL 원칙상 이 포맷도 로그로 커버되어야 한다 — crash 후 디스크의 그 페이지는 쓰레기값일 수 있으므로, redo 가 초기화를 재현할 수 있어야 한다.

**PR 이전**: OOS 데이터 페이지 init (`oos_vpid_init_new`) 은 "ptype 설정 + `spage_initialize`" 뿐이었다. 초기화된 페이지가 (ptype, slotted-page 지오메트리) 만으로 완전히 결정되므로, **기존 범용 인덱스 `RVPGBUF_NEW_PAGE`** 로 로깅하면 충분했다 (`oos_file.cpp:2233`) — 그 redo 는 OOS 의 존재를 몰라도 페이지를 재현한다.

**PR 이후**: init 이 slot 0 헤더 레코드 삽입까지 하게 되면서, 갓 초기화된 페이지에 *OOS 고유 내용물*이 생겼다. 이 시점에서 기존 인덱스들이 전부 부적합해진다:

1. `RVPGBUF_NEW_PAGE` 의 redo 는 빈 slotted page 만 재현한다 — crash 후 redo 를 돌리면 페이지는 포맷되지만 slot 0 레코드가 없어서, 이후 모든 헤더 접근이 corruption (`ER_HEAP_OOS_CORRUPTED_RECORD`) 을 본다.
2. `RVOOS_INSERT` 를 재사용할 수도 없다 — 그 redo (`oos_rv_redo_insert`) 는 청크 전용이다: 이미지에서 청크 헤더를 파싱하고, **slot 0 헤더 레코드를 읽어서** counter 를 MAX 재생한다 (`oos_file.cpp:2728`). slot 0 레코드 자신의 replay 에 쓰면 아직 존재하지 않는 slot 0 을 읽으려는 닭-달걀 문제가 생기고, `OOS_PAGE_HEADER` 는 청크가 아니라 파싱 자체가 어긋난다.

그래서 "ptype + `spage_initialize` + slot 0 레코드 삽입"을 **한 로그 레코드의 redo 로 원자적으로 재현**하는 전용 인덱스 `RVOOS_NEWPAGE` 가 신설됐다 (`oos_file.cpp:2284`, `recovery.c:921`). undo 쪽이 비어 있는 건 롤백 시 `file_alloc` 자체의 undo 가 페이지를 dealloc 하기 때문이다.

**LSA 라면**: slot 0 레코드가 없으므로 init 이 다시 평범한 "ptype + spage 초기화"로 돌아가고, 범용 `RVPGBUF_NEW_PAGE` 로 충분해진다. `RVOOS_NEWPAGE` 는 통째로 삭제된다.

### 3.3 redo 의 MAX 재생

counter 의 내구성은 slot 0 레코드가 아니라 사실상 **청크의 `RVOOS_INSERT` 이미지**가 나른다 (발급 시점에 counter 갱신과 청크 삽입이 같은 로그 레코드로 묶임 — `oos_file.cpp:1645` 주석). 그래서 redo 는 청크 이미지의 generation 으로 counter 를 `MAX(counter, chunk.generation)` 재생해야 한다 (`oos_file.cpp:2728`). "단조 증가"라는 불변식을 복구 코드가 능동적으로 지켜줘야 하는 구조다.

**LSA 라면**: 스탬프는 청크 이미지 안의 데이터일 뿐이라 redo·undo 가 그대로 복원하고, 페이지 LSA 의 단조성은 복구 기계 자체가 보장한다. 특별 재생 코드가 없다.

### 3.4 wrap-around 은퇴 로직

counter 는 `uint32` 라 페이지당 2^32 회 발급 후 포화된다. 지난 리뷰 (2026-08-14) 의 질문이 바로 이것이었고, 그 답으로 HEAD 커밋 `ecebe6288` 이 추가됐다: 발급 경로의 포화 가드 (`oos_file.cpp:1607`), bestspace 후보 선정에서 포화 페이지 은퇴 (`oos_file.cpp:660`, `2315`). **즉 counter 의 수명 관리 비용은 가설이 아니라 이 브랜치가 이미 지불한 비용이다.**

**LSA 라면**: 64비트라 현실적 수명 안에서 포화가 없다. 이 커밋의 로직 전체가 삭제된다.

### 3.5 결정타 — 페이지 재활용 (CBRD-26786) 과 counter 리셋

`oos_vpid_init_new_data_page` 는 counter 를 0 으로 초기화한다 (`oos_file.cpp:2269`). 지금은 OOS 페이지를 dealloc 하는 프로덕션 경로가 없어 "새 페이지 = 처음"이 참이지만, **CBRD-26786 (빈 OOS 페이지 회수) 이 들어오면 `file_alloc` 은 재사용 페이지에도 init 을 실행한다.** 그러면 재활용된 페이지가 generation 을 1 부터 다시 발급하고, 그 페이지의 옛 시절을 기억하는 stale stub 의 (OID, generation) 과 새 주인의 값이 충돌할 수 있다 — **CBRD-26950 버그가 페이지 단위로 부활**한다. 현재 코드도 이걸 알고 있어서, 해당 지점에 "페이지 회수는 counter 를 보존하거나 stale stub 이 페이지보다 오래 살 수 없음을 보장해야 한다"는 제약 주석이 달려 있다 (`oos_file.cpp:2264-2268`).

참고로 CBRD-26786 은 이미 별도 브랜치 (`cbrd-26786-oos-page-clean`, `82d6e4bb5`) 에 구현되어 있다. 아직 feat/oos 에 머지되지 않았을 뿐, 이 위험은 "제안 단계"가 아니라 **가까운 미래**다.

**LSA 라면**: 페이지 init 자체가 로깅된 연산이므로, 재할당된 페이지의 LSA 는 그 init 로그 레코드의 주소 — 즉 이 페이지가 과거에 발급했던 **모든 스탬프보다 큰 값**이다. 리셋될 상태가 아예 없으니 "리셋 규칙" 자체가 소멸한다. 제안 코멘트가 이 행을 결정적이라고 본 이유이고, 동의한다.

---

## 4. 제안자가 미확인으로 남긴 두 가지 — 확인 결과

### 4.1 "데이터 페이지 LSA 를 남긴 채 append LSA 를 되돌리는 절차가 있는가?" → 있다, 그러나 안전하다

`log_recreate` (`log_manager.c:8906`) 가 정확히 그런 절차다 — 로그를 파괴하고 새로 만들면서, `fileio_reset_volume` 으로 **영구 볼륨 전 페이지의 LSA 를 NULL 로 리셋**한다 (`log_manager.c:8969`). 청크·stub 데이터 안에 박힌 스탬프는 페이지 데이터라 리셋되지 않는다.

그런데도 안전한 이유: 이 절차는 **로그 자체를 파괴**하므로, undo image 에 기반한 pending vacuum 작업도 함께 소멸한다. 즉 "옛 (OID, 스탬프) 참조를 들고 재시도하는 주체"가 남아 있지 않다 — 위험한 재생 창이 빈다. 남는 것은 리셋 후 로그가 다시 자라서 옛 LSA 구간을 통과하는 동안의 이론적 충돌뿐인데, 그 사이 살아남은 stale 참조가 있어야 성립하므로 제안 코멘트의 표현대로 "설계가 이미 수용한 페이지 재활용 위험과 같은 급"이다.

여기서 나오는 실질 작업 항목 하나: 리셋 직후 아직 아무 로깅 연산이 닿지 않은 페이지에 삽입하면 스탬프가 NULL LSA 가 될 수 있다. **NULL LSA 스탬프의 의미** (현재 "generation 0 = 미발급"의 대응물) 를 정의해 둬야 한다.

### 4.2 "배치 삽입을 한 로그 레코드로 묶으면 유일성이 깨지는가?" → 생각보다 안전하다

신원은 스탬프 단독이 아니라 **(OOS OID, 스탬프) 쌍**이고, OID 에 slotid 가 포함된다. 그래서:

- 서로 다른 슬롯이 같은 스탬프를 갖는 것 (배치 삽입으로 한 페이지에 여러 청크가 같은 pre-append LSA 를 관측) 은 **무해**하다 — 애초에 OID 가 다르다.
- 문제가 되는 건 **같은 슬롯의 두 점유**가 같은 스탬프를 갖는 경우뿐인데, 재점유가 있으려면 그 사이에 슬롯을 비운 delete 가 반드시 이 페이지에 로깅되므로 두 점유는 항상 다른 페이지 LSA 를 관측한다.

즉 지켜야 할 불변식은 "같은 슬롯의 두 점유 사이에 최소 1회의 로깅된 페이지 연산" 하나로 좁혀지고, 이는 현재 구조에서 자동으로 성립한다. 미래의 최적화가 깨지 않도록 주석으로 명문화하면 된다.

---

## 5. CBRD-27230 (UPDATE 체인 재사용) 과의 관계 — 이 선택에 중립

"generation 이 UPDATE dedup 에도 쓰이니 counter 를 유지해야 하지 않나?"라는 의문이 있을 수 있어 정리한다. **아니다** — 잠긴 CBRD-27230 설계에서 역할 분담은 이렇다:

| 질문 | 답하는 주체 |
|---|---|
| 이 UPDATE 가 어떤 체인을 버렸나? (dedup 판단) | **writer 가 UPDATE 시점에** 안다 (어떤 attribute 가 할당됐는지) → 커밋 시 notify 로그 레코드로 vacuum 에 전달 |
| 이 OID 의 청크가 아직 그 체인인가? (재시도 안전) | **신원 스탬프** — notify 레코드도 불변이고 블록 재시도 때 재소비되므로, 멱등성은 전적으로 `oos_delete (expected)` 대조에서 온다 |

vacuum 시점의 스탬프 대조는 dedup 판단에 쓸 수 없다는 것도 분석에서 확인된 사실이다: 재사용은 stub 의 byte-copy 라서 재사용된 체인은 undo image·live stub·청크 헤더 셋 다 같은 (OID, 스탬프) 를 갖는다 — 등가가 성립하는 순간이 정확히 지우면 안 되는 순간이다. 그래서 dedup 판단은 로그 (notify) 로 가고, 스탬프는 멱등성 토큰으로 남았다.

이 토큰 역할은 counter 든 LSA 든 동일하게 수행한다. 바뀌는 것은 notify 레코드의 쌍이 (head OOS OID, 4B generation) 에서 (head OOS OID, 8B LSA) 가 되는 것, 그리고 복제 fixup 이 stub 에 8B 를 쓰게 되는 것뿐이다. **CBRD-27230 은 이 교체의 논거도, 반대 논거도 아니다.**

---

## 6. 장단점 종합

| 항목 | generation counter (현재 PR) | page LSA (제안) |
|---|---|---|
| 스탬프 크기 | 4B — stub 20B, 청크 헤더 +4B | 8B — stub 24B (8B 정렬 회복), 청크 헤더 +8B |
| 발급 상태 | slot 0 헤더 레코드 신설 (§3.1) | 페이지 헤더의 기존 LSA 재사용 — 추가 상태 없음 |
| 복구 | `RVOOS_NEWPAGE` 신설 + MAX 재생 (§3.2, §3.3) | 기존 로깅으로 충분 — 스탬프가 청크 이미지에 실려 그대로 복원 |
| wrap-around | 포화 가드 + 페이지 은퇴 로직 (§3.4) | 64비트 — 해당 없음 |
| 페이지 재활용 (CBRD-26786) | counter 0 리셋 → 결함 페이지 단위 재발, 후속 계약 필요 (§3.5) | 구조적으로 소멸 |
| 미발급 표지 | generation 0 | NULL LSA — 의미 정의 필요 (§4.1) |
| 외부 절차 의존 | 없음 (자기완결) | `log_recreate` 류 LSA 되감기와 상호작용 — 확인 결과 안전 (§4.1) |
| `oos_delete (expected)` 계약 | 불일치·부재 no-op | **동일** — 비교 대상만 교체, 세 삭제 경로·테스트 계약 그대로 |
| CBRD-27230 결합 | 멱등성 토큰 (notify 쌍 4B) | 동일 (notify 쌍 8B) — §5 |
| 부수 코드 | 발급·재생·은퇴·브리지 유지 필요 | 대부분 삭제 — 순삭제에 가까운 재작업 |

정직하게 남는 단점은 두 개다: (1) stub·청크 헤더가 각 4B 더 커진다 — stub 은 OOS inline target 계산에 들어가므로 한 레코드의 stub 개수만큼 누적된다. (2) 자기완결적 카운터 대신 로그/LSA 체계에 의존하게 된다 — 다만 그 의존이 정확히 "이미 검증된 기계를 재사용한다"는 제안의 요지이기도 하다.

---

## 7. 전환 시 고정할 불변식과 재작업 범위

**코드 주석·스펙에 명문화할 불변식 세 가지:**

1. 스탬프는 반드시 **삽입 직전** 페이지 LSA 다 — `log_rcv` 는 자기 LSA 를 모르므로, append 후 덧쓰기는 redo 에서 재유도 불가 (§2.2).
2. 같은 슬롯의 두 점유 사이에는 최소 1회의 로깅된 페이지 연산이 있다 — 배치 삽입류 최적화 가드 (§4.2).
3. NULL LSA 스탬프의 의미 — `log_recreate` 직후 첫 발급 케이스 (§4.1).

**재작업 범위 (보기보다 작다):**

- **그대로**: `oos_delete (expected)` no-op 계약, 세 삭제 경로 (forward-walk·REMOVE·eager), 복제 fixup 의 stub 재기록 구조, 불일치 no-op 테스트 계약.
- **교체**: 발급부 — counter 증가 대신 `pgbuf_get_lsa (page_ptr)` 읽기. 스탬프 폭 4B → 8B (stub·청크 헤더·복제 fixup).
- **삭제**: slot 0 헤더 레코드와 그 특별 취급, `RVOOS_NEWPAGE`, `oos_rv_redo_insert` 의 MAX 재생, wrap 은퇴 로직 (`ecebe6288` 전체), `bridge_oos_set_page_generation_counter` 등 테스트 브리지.

feat/oos 는 미머지 브랜치고 이 PR 이 이미 테스트 DB 재생성을 요구하므로, 포맷을 바꾸는 마지막 값싼 시점이라는 제안자의 판단에도 동의한다.

---

## 8. 참고한 코드 위치 (PR HEAD `ecebe6288` 기준)

| 무엇 | 위치 |
|---|---|
| generation 발급 (W-latch 하 issue+insert 원자화) | `src/storage/oos_file.cpp:1595-1655` |
| 포화 가드 / bestspace 은퇴 | `src/storage/oos_file.cpp:1607, 660, 2315` |
| counter 0 리셋 + CBRD-26786 제약 주석 | `src/storage/oos_file.cpp:2264-2269` |
| `RVOOS_NEWPAGE` 로깅 / 등록 | `src/storage/oos_file.cpp:2284`, `src/transaction/recovery.c:921` |
| PR 이전 방식의 init (범용 `RVPGBUF_NEW_PAGE`) | `src/storage/oos_file.cpp:2225-2239` (`oos_vpid_init_new`, 헤더 페이지용으로 존치) |
| redo 의 MAX 재생 | `src/storage/oos_file.cpp:2728` |
| `oos_delete` 대조 계약 (W-latch 하 대조) | `src/storage/oos_file.cpp:2508-2555` |
| OOS 파일 영구 생성 (`is_temp=false`) | `src/storage/oos_file.cpp:1054` |
| `log_recreate` 의 페이지 LSA 리셋 | `src/transaction/log_manager.c:8906-8970` |
| CBRD-26786 구현 브랜치 | `cbrd-26786-oos-page-clean` @ `82d6e4bb5` (feat/oos 미머지) |
