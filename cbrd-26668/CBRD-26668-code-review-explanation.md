# CBRD-26668 — OOS Vacuum 회수(Reclamation) 코드 리뷰 가이드

> 대상 diff: `git diff origin/feat/oos HEAD`
> 브랜치: `oos-vacuum` (base: `origin/feat/oos`)
> 이 문서의 목적: 리뷰어가 변경 전체를 **주제 단위**로 빠르게 파악하고, 각 hunk가 왜 그렇게 짜였는지 근거까지 확인하도록 돕는다.
>
> 변경 규모: 26개 파일, **+4822 / −78**. 단, 이 중 약 3,500줄은 새로 추가한 테스트다. 실제 엔진 코드는 약 1,300줄이고, 이 문서의 §3~§8이 그 1,300줄 전부를 다룬다.
>
> **리뷰 범위**: **필수 대상은 엔진 코드(§3~§8) 약 1,300줄**이다. **테스트 코드(§9 — unit test, E2E, mock, SQL 등)는 선택적 리뷰 대상**이며 근거 참고용이다(자세한 안내는 §9 상단).
>
> **🚫 리뷰 대상에서 제외**: **OVF(overflow record) 스펙 변경에 따른 부수 수정(§8-4 등)은 리뷰 포인트가 아니다.** CBRD-26668(회수) 본류가 아니라 OVF 스펙 변경에 맞춘 기계적 적응이므로, 리뷰 시 건너뛰어도 무방하다(do not review).

---

## 0. 한눈에 보기 (Executive Summary)

먼저 큰 그림부터 보자.

**OOS(Out-of-row Overflow Storage)** 는 "덩치 큰 컬럼 값을 행 안에 욱여넣지 않고, 별도 파일에 따로 보관하는" 기능이다. 행(heap 레코드)에는 그 큰 값 대신 **8바이트짜리 주소(OID)** 만 남겨서 "값은 저기 OOS 파일에 있어"라고 가리킨다.

> **쉽게 말하면**: 무거운 짐을 가방에 다 넣지 않고 **물품 보관함(locker)** 에 맡긴 뒤, 가방에는 **보관함 열쇠(OID)** 만 넣고 다니는 것과 같다.

`feat/oos` 브랜치는 여기까지 — 즉 **값을 보관함에 넣고(저장), 다시 꺼내 읽는(읽기)** 기능까지 — 구현했다.

문제는 그다음이다. 행이 **삭제되거나 갱신되면**, 그 행이 가리키던 OOS 청크는 **이제 아무도 가리키지 않는 쓰레기**가 된다. 보관함에 짐은 그대로 들어 있는데 열쇠를 가진 사람이 사라진 셈이다. 이런 걸 **고아(dangling/leaked) 청크**라고 부른다. 방치하면 디스크가 계속 새어 나간다(leak).

이 브랜치(CBRD-26668)가 하는 일이 바로 그 **누수를 막는 OOS 회수(reclamation)**, 즉 버려진 보관함을 비우는 청소 작업이다. 핵심은 **청소 경로가 두 개**라는 점이다.

| 경로 | 언제 쓰나 | 청소 시점 | 진입 함수 |
|---|---|---|---|
| **Eager (즉시 청소)** | `!is_mvcc_op` (SA_MODE + MVCC 안 쓰는 카탈로그 클래스) | DELETE/UPDATE 실행 도중 | `heap_oos_delete_unreferenced()` |
| **Deferred (나중에, vacuum이 청소)** | MVCC (SERVER_MODE) | vacuum이 돌 때 | `vacuum_heap_oos_delete_within_sysop()` / `vacuum_forward_walk_reclaim_oos()` |

왜 두 개냐면, 모드에 따라 "지금 당장 지워도 안전한가"가 다르기 때문이다(자세한 이유는 §1).

그리고 **Deferred(지연) 경로는 다시 두 갈래**로 나뉜다.

- **REMOVE 경로**: vacuum이 죽은 슬롯(REC_HOME/REC_RELOCATION)을 물리적으로 지울 때, **그 슬롯을 지우는 김에** 슬롯이 가리키던 OOS도 같은 작업 묶음(sysop) 안에서 함께 지운다.
- **Forward-walk 경로**: UPDATE처럼 **갱신된 뒤 살아있는 슬롯은 더 이상 옛 OID를 가리키지 않는** 경우다. 옛 OID는 오직 **undo 로그 이미지** 안에만 남아 있다. 그래서 vacuum이 로그 블록을 훑으며 그 옛 이미지를 읽어 회수한다.

> **읽는 순서 추천**: §1(큰 그림) → §2(모듈 추출 지도) → §4(신규 로그타입, 리뷰가 가장 민감한 곳) → §5(eager) → §6(REMOVE) → §7(forward-walk) → §8(버그픽스) → §9(테스트).

---

## 1. 큰 그림: 왜 청소 경로가 두 개인가

모든 설계의 출발점이 되는 한 가지 사실부터 기억하자.

> **불변식**: OOS OID는 **행마다 새로 만들어지고, 절대 두 행이 같은 OID를 공유하지 않는다** (unique per heap record).

즉 어떤 OOS 청크는 정확히 한 행만 가리킨다. 그래서 "이 행이 죽었다 = 이 청크는 이제 진짜 아무도 안 쓴다"가 항상 참이다. 이 사실이 회수 설계 전체의 근거다.

이제 핵심 질문: 행이 죽었다고 **지금 당장** 청크를 지워도 될까? 그건 모드에 따라 다르다.

```
                       레코드가 OOS를 참조 (heap recdes VOT에 8B OID + OR_MVCC_FLAG_HAS_OOS)
                                         │
            ┌────────────────────────────┴────────────────────────────┐
            │                                                          │
     !is_mvcc_op (SA / 카탈로그)                              MVCC (SERVER_MODE)
            │                                                          │
   동시에 읽는 사람 없음 → 바로 지워도 안전              옛 OOS를 아직 보고 있는 reader가 있을 수 있음
            │                                                  → 살려두고 vacuum이 나중에 회수
   heap_oos_delete_unreferenced()                                     │
   (DELETE: 전부 / UPDATE: new에 없는 것만)          ┌─────────────────┴─────────────────┐
                                                  REMOVE 경로                    Forward-walk 경로
                                              (슬롯이 통째로 죽음)          (슬롯은 살아있으나 옛 OID를
                                                     │                       더 이상 가리키지 않음)
                                          vacuum_heap_oos_delete_within_sysop()        vacuum_forward_walk_reclaim_oos()
                                          (REC_HOME 인라인 sysop /         (undo image에서 옛 OID 추출)
                                           REC_RELOCATION forward와 함께)
```

- **`!is_mvcc_op` (SA 모드, 또는 MVCC를 안 쓰는 카탈로그 클래스)**: 지금 이 값을 동시에 읽고 있는 다른 사람이 없다. 그러니 바로 지워도 안전하다. → **eager(즉시) 청소**.
- **MVCC (SERVER 모드)**: 다른 트랜잭션이 아직 **옛 버전**을 보고 있을 수 있다(MVCC 가시성). 지금 지우면 그 reader가 사라진 값을 읽으려 한다. 그래서 일단 살려두고, **아무도 안 볼 때가 되면 vacuum이 청소**한다. → **deferred(지연) 청소**.

### 왜 UPDATE의 옛 OID는 REMOVE 경로로 못 잡는가?

지연 경로가 다시 둘로 갈리는 이유가 여기 있다. 한 단계씩 따라가 보자.

`heap_attrinfo_insert_to_oos`는 레코드를 변환(transform)할 때마다 **새 OOS OID**를 새로 만든다. 그래서 UPDATE가 끝난 직후, **살아있는 슬롯은 새 OID만** 가리킨다. 옛 OID는 그 슬롯 어디에도 없다 — 오직 **undo 레코드(되돌리기용 옛 이미지)** 안에만 남는다.

REMOVE 경로는 "살아있는 슬롯을 읽어서 그 안의 OOS를 회수"하는 방식이다. 그런데 옛 OID는 살아있는 슬롯에 없으니, REMOVE 경로는 옛 OID에 **영영 도달할 수 없다**. 그래서 옛 OID를 회수하려면 undo 이미지를 들여다보는 **forward-walk가 유일한 수단**이다.

---

## 2. 모듈 추출 지도 (Refactor)

엔진 로직을 거대한 `vacuum.c` / `heap_file.c` 안에 더 쌓는 대신, 전용 모듈로 떼어냈다. "어느 파일을 보면 되는가"의 지도다.

| 파일 | 신규/수정 | 역할 |
|---|---|---|
| `src/storage/oos_util.{hpp,cpp}` | **신규** | 어느 모듈에도 안 묶이는 헬퍼(`oos_oid_in_vector`) |
| `src/storage/heap_oos.{hpp,cpp}` | 수정(+104) | Eager 경로 `heap_oos_delete_unreferenced` |
| `src/query/vacuum_oos.{hpp,cpp}` | **신규** | 지연 경로 전부(REMOVE 헬퍼 + forward-walk + VFID 캐시) |
| `src/storage/oos_file.{hpp,cpp}` | 수정(+91) | `oos_chunk_exists`(멱등 probe), `oos_get_stats_by_vfid` |
| `src/storage/heap_file.c` | 수정(+158) | Eager 호출 지점 + `heap_log_delete_physical` rcvindex 인자 + 디버그 VOT 검증 |
| `src/query/vacuum.c` | 수정(+131) | 지연 경로 호출 지점 + spin-loop 픽스 |
| `src/transaction/recovery.{h,c}`, `mvcc.h` | 수정 | 신규 로그타입 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM=136` |
| `cubrid/CMakeLists.txt`, `sa/CMakeLists.txt` | 수정 | `vacuum_oos.cpp`, `oos_util.cpp`를 빌드에 추가 |

> **✅ 리뷰 체크리스트 (모듈/빌드)**
> - [ ] `cubrid/`(SERVER)와 `sa/`(SA) **두 CMakeLists 모두에** 신규 소스가 들어갔는가? 한쪽만 넣으면 그쪽 빌드가 깨진다.

---

## 3. 기반 헬퍼 (base 브랜치에서 가져다 쓰는 것)

이 diff는 새로 만든 게 아니라 `feat/oos`에 **이미 있는** 다음 헬퍼들을 가져다 쓴다. 시그니처를 알아두면 hunk가 훨씬 쉽게 읽힌다.

```c
// src/storage/heap_file.h (base)
extern bool heap_recdes_contains_oos (const RECDES *record);                 // recdes가 OOS 참조를 품고 있나?
extern int  heap_recdes_get_oos_oids (const RECDES *record, OID_VECTOR &);   // recdes에서 OOS OID들을 뽑아냄
extern bool heap_oos_find_vfid (THREAD_ENTRY *, const HFID *, VFID *, bool docreate); // heap → OOS 파일 VFID
using OID_VECTOR = std::vector<OID>;
```

`heap_recdes_contains_oos`는 레코드 MVCC 헤더의 `OR_MVCC_FLAG_HAS_OOS` 플래그를 보고 "이 레코드에 OOS가 붙어 있나"를 판정한다.

> **⚠️ 주의 (나중에 §7에서 다시 나옴)**: 이 함수에 OOS 포맷이 **아닌** recdes를 넣으면 안 된다. 예를 들어 REC_RELOCATION의 8바이트 forwarding OID를 넣으면, 그 OID의 pageid 비트를 MVCC 헤더로 **착각**해서 "OOS 있음"이라는 **거짓 양성(false positive)** 을 낼 수 있다. §7에서 record-type 가드가 꼭 필요한 이유가 바로 이것이다.

---

## 4. 신규 로그타입 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` (파일 5개에 걸친 한 가지 변경)

리뷰가 가장 민감한 부분이니 천천히 보자.

**상황**: MVCC 모드에서 `heap_update_relocation`이 옛 forward(REC_NEWHOME) 슬롯을 **물리적으로 삭제**할 때가 있다. 이 옛 레코드는 삭제된 뒤 **이 삭제의 undo 이미지 안에만** 남는다(그 LSA가 새 버전의 `prev_version_lsa`로 연결된다). 만약 이 옛 forward가 OOS를 가리키고 있었다면, forward-walk가 나중에 그 OOS를 회수해야 한다.

**문제**: 그런데 vacuum이 나중에 로그를 훑을 때, 수많은 로그 레코드 중 "이게 회수 대상이다"라고 어떻게 알아볼까? 답은 **전용 표식(rcvindex 태그)** 을 붙여두는 것이다. 그래서 새 로그타입을 하나 만든다.

### 4-0. 왜 굳이 새 타입이 필요한가 (직관)

> **흔한 오해**: "`RVHF_DELETE`도 어차피 삭제 로그인데, 그걸 보고 OOS 검사해서 OID 따라가 회수하면 되지 않나? 왜 새 타입을 만드나?"

여기서 헷갈리기 쉬운 핵심을 정확히 짚자. **회수 경로를 가르는 기준은 "어떤 rcvindex냐"가 아니라, "OOS를 가리키는 슬롯이 아직 살아 있느냐"** 다.

| | 슬롯 상태 | 누가 회수하나 | OOS OID를 어디서 읽나 |
|---|---|---|---|
| **REMOVE 경로** | 죽었지만 **아직 존재함** | `vacuum_heap_record` | **살아있는 슬롯의 recdes** |
| **Forward-walk 경로** | **물리적으로 사라짐** | `vacuum_forward_walk_reclaim_oos` | **delete 로그의 undo 이미지** |

오해 속의 "OOS 검사 후 OID 따라가 회수"는 사실 **REMOVE 경로**가 하는 일이다. 그리고 그건 **읽을 슬롯이 아직 남아 있을 때만** 가능하다. 평범한 `RVHF_DELETE`가 회수를 트리거하는 게 아니다 — vacuum이 죽은 슬롯을 지우는 과정에서 그 슬롯을 읽어 회수하는 것뿐이다.

**문제가 되는 시나리오 — REC_NEWHOME 재배치:**

```
[UPDATE 전]
HOME ──(REC_RELOCATION)──▶ forward 슬롯 (REC_NEWHOME, 데이터 + OOS 포인터) ──▶ OOS 파일의 큰 값

[UPDATE 중: remove_old_forward = 옛 forward 슬롯을 "물리 삭제"]
   옛 REC_NEWHOME 슬롯이 heap에서 사라짐
   → 그 OOS를 가리키는 살아있는 슬롯이 0개가 됨
   → OOS OID는 오직 이 delete 로그의 undo 이미지에만 남음  (heap_file.c:23684-23695)
```

이 순간 REMOVE 경로는 **읽을 슬롯 자체가 없어서** 이 OOS에 영원히 못 닿는다. 유일한 길은 delete 로그의 undo 이미지를 읽는 forward-walk다. 그래서 로그를 남기는 쪽(emitter)이 **"OOS 달린 REC_NEWHOME forward를 MVCC로 삭제하는" 딱 그 경우에만** 새 태그를 붙인다 (`heap_file.c:23690`):

```c
LOG_RCVINDEX delete_rcvindex = RVHF_DELETE;
if (is_mvcc_op && forward_recdes.type == REC_NEWHOME
    && heap_recdes_contains_oos (&forward_recdes))        // OOS 달린 forward 삭제일 때만
  {
    delete_rcvindex = RVHF_DELETE_NEWHOME_NOTIFY_VACUUM;   // ← "vacuum아, 이건 forward-walk 해라"
  }
```

**"그럼 모든 `RVHF_DELETE`를 forward-walk하면 되잖아?" → 안 된다. 이중 삭제(double-delete) 때문이다.**

논리적 MVCC DELETE(`RVHF_MVCC_DELETE_MODIFY_HOME`)를 보자. 이 경우 슬롯은 **죽지 않고 살아남고, 같은 OOS OID를 그대로 계속 가리킨다**. 그러니 이건 REMOVE 경로가 알아서 회수한다. 여기에 forward-walk까지 돌리면 **같은 OID를 두 번 삭제**하게 되고, `oos_delete_chain`이 "어, 이미 없는데?"라며 `S_DOESNT_EXIST` assert를 터뜨린다(vacuum.c:3546-3550).

따라서 게이트(문)는 넓게 열면 안 되고, **REMOVE가 구조적으로 절대 못 닿는 그 한 케이스로 정확히 좁혀야** 한다.

| delete 종류 | 슬롯 생존 | 회수 담당 | forward-walk까지 돌리면? |
|---|---|---|---|
| 논리적 MVCC DELETE | 살아남음(recdes 동일) | REMOVE 경로 | 💥 이중 삭제 |
| UPDATE 재배치의 옛 forward 물리삭제 | **사라짐** | **forward-walk** | ✅ 유일한 회수 수단 |

> **요약**: 새 타입은 "`RVHF_DELETE`가 못 하는 일"을 위해 만든 게 아니다. **REMOVE 경로가 닿을 수 없는 고아 OOS를, 이중 삭제 없이, 딱 그 케이스만 골라 forward-walk로 보내기** 위한 **의미 표식**이다. 크래시 복구 동작 자체는 `RVHF_DELETE`와 완전히 똑같다(§4-2).

### 4-1. `recovery.h` — enum 슬롯 136 (on-disk 고정값)

```c
  RVHF_DELETE_NEWHOME_NOTIFY_VACUUM = 136,
  RV_LAST_LOGID = RVHF_DELETE_NEWHOME_NOTIFY_VACUUM,
```

- **반드시 끝에 추가(append-only), 중간 번호 절대 변경 금지**: `RV_fun[]`(recovery.c)는 rcvindex 값을 **배열 인덱스**로 써서 핸들러를 찾는다. 중간 값을 하나라도 바꾸면 뒤쪽 슬롯이 전부 한 칸씩 밀려 엉뚱한 핸들러가 호출된다.
- 기존 `RVOOS_NOTIFY_VACUUM = 134`는 **로그를 남기는 코드(emitter)가 없는 미사용 값**이다. 그래도 디스크에 이미 기록된 옛 로그가 이 값을 참조할 수 있으므로 134에 **그대로 핀 고정**하고, enum과 매크로 양쪽에 `TODO` 주석을 남겼다 — 나중에 로그 포맷 버전을 올릴(bump) 때 함께 정리한다.

### 4-2. `recovery.c` — `RV_fun[]` 핸들러 행

```c
  {RVHF_DELETE_NEWHOME_NOTIFY_VACUUM,
   "RVHF_DELETE_NEWHOME_NOTIFY_VACUUM",
   heap_rv_undo_delete,   // ← RVHF_DELETE와 동일
   heap_rv_redo_delete,   // ← RVHF_DELETE와 동일
   log_rv_dump_hexa, log_rv_dump_hexa}
```

- **크래시 복구는 평범한 `RVHF_DELETE`와 100% 똑같이 재생(replay)한다.** OOS 회수는 redo/undo의 일부가 **아니라**, vacuum이 돌 때 undo 이미지를 보고 따로 하는 **추가 작업**이기 때문이다. 그래서 핸들러는 `RVHF_DELETE`의 것을 그대로 거울처럼 복사한다.
- 134 슬롯도 `vacuum_rv_es_nop`(아무것도 안 하는 no-op 스텁)으로 유지한다 — 배열 위치 인덱싱을 깨지 않기 위해서다.

### 4-3. `mvcc.h` — "MVCC op"으로는 분류, 단 "MVCC heap op"으로는 분류 안 함

```c
#define LOG_IS_MVCC_OPERATION(rcvindex) \
  (LOG_IS_MVCC_HEAP_OPERATION (rcvindex) \
   || LOG_IS_MVCC_BTREE_OPERATION (rcvindex) \
   || ((rcvindex) == RVES_NOTIFY_VACUUM) \
   || ((rcvindex) == RVOOS_NOTIFY_VACUUM) \
   || ((rcvindex) == RVHF_DELETE_NEWHOME_NOTIFY_VACUUM))
```

- **여기 분류 의도가 미묘하니 주의**: 새 타입은 `LOG_IS_MVCC_OPERATION`에는 **포함**시킨다(undo가 MVCC undo 사슬로 연결돼서 forward-walk가 따라갈 수 있도록). 하지만 `LOG_IS_MVCC_HEAP_OPERATION`에는 **포함시키지 않는다**(슬롯이 이미 물리 삭제됐으므로 vacuum이 "이 슬롯을 collect(수집)"하려 들면 안 됨). 이 구분이 §7의 `vacuum_process_log_block` 분기에서 결정적으로 작동한다.

### 4-4. `heap_file.c` — emitter (`heap_update_relocation`)

```c
LOG_RCVINDEX delete_rcvindex = RVHF_DELETE;
if (is_mvcc_op && forward_recdes.type == REC_NEWHOME && heap_recdes_contains_oos (&forward_recdes))
  {
    delete_rcvindex = RVHF_DELETE_NEWHOME_NOTIFY_VACUUM;
  }
heap_log_delete_physical (..., &forward_recdes, true, &prev_version_lsa, delete_rcvindex);
```

- OOS를 가진 MVCC forward 삭제일 때만 새 태그를 붙인다. 나머지(OOS 없음, 또는 SA 모드 — 이쪽은 §5 eager가 처리)는 전부 평범한 `RVHF_DELETE`로 간다 → **기존 동작 변화 없음**.

### 4-5. `vacuum.c` — consumer (자세한 건 §7)

`vacuum_process_log_block`이 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`을 만나면, **MVCC heap-op 블록 바깥에서**(수집할 슬롯이 없으니까) `vacuum_forward_walk_reclaim_oos`를 호출한다.

> **✅ 리뷰 체크리스트 (로그타입)**
> - [ ] 136이 enum **맨 끝에** 추가됐고 `RV_LAST_LOGID`도 같이 갱신됐는가.
> - [ ] `RV_fun[]` 행이 배열에서 정확히 136 자리에 오는가(중간에 134 스텁이 끼어 있음에 유의).
> - [ ] 핸들러가 `heap_rv_undo_delete`/`heap_rv_redo_delete`인가(복구 동작이 동일해야 함).
> - [ ] emitter 가드가 `is_mvcc_op && REC_NEWHOME && contains_oos` 세 조건을 **모두** 거치는가.
>
> **⚠️ 리스크**
> - rcvindex 134/136은 **디스크에 고정된 값**이다. 재번호 매기면 기존 로그/복구가 깨진다.
> - 새 타입을 `LOG_IS_MVCC_HEAP_OPERATION`에 넣으면, vacuum이 이미 삭제된 슬롯을 collect하려 들어 회귀(regression)가 난다.

---

## 5. Eager 경로 (`!is_mvcc_op`)

동시에 읽는 reader가 없는 SA_MODE / MVCC 비활성 카탈로그 클래스에서는, DELETE/UPDATE를 실행하는 **그 자리에서 바로** 옛 OOS를 지운다. 이 모드엔 vacuum 자체가 없으므로, 여기서 안 지우면 그 누수는 영원히 남는다.

### 5-1. `heap_oos.cpp` — `heap_oos_delete_unreferenced()` (핵심 신규 함수)

시그니처: `(context, old_recdes, new_recdes, op_ctx)`
역할: `old_recdes`는 가리키지만 `new_recdes`는 안 가리키는 OOS OID를 골라 지운다.

- `new_recdes == NULL` (DELETE인 경우): **old의 모든 OOS OID를 무조건 삭제**. OOS OID는 행 간에 공유되지 않으니 전부 지워도 안전하다.
- `new_recdes != NULL` (UPDATE인 경우): old와 new에 **둘 다 들어 있는** OID(= 갱신 전후로 같은 OOS를 그대로 쓰는 경우)는 **보존**하고, old에만 있는 것만 삭제한다. 이 "둘 다 있나" 교집합 판정에 `oos_util.cpp`의 `oos_oid_in_vector`를 쓴다.
- **실패는 엄격하게 처리**: 여기서 OOS 파일/추출이 실패하면 그건 진짜 손상(corruption)이다. 그래서 `assert_release`로 잡고 에러를 위로 전파한다.
- **호출자와의 계약(중요)**: 에러가 나면 **반드시 트랜잭션을 abort해야 한다.** `oos_delete`는 청크마다 undo 레코드를 남기는데, rollback 때 이 undo가 부분 삭제까지 되돌려줘야, 살아남은 recdes가 "이미 지워진 청크"를 가리키는 모순을 막을 수 있다.
- 진단 태그에는 "SA_MODE"라고 적혀 있지만, 주석에 나오듯 `!is_mvcc_op`는 SERVER_MODE의 MVCC-비활성 클래스(카탈로그)에서도 발동한다 → **서버에서도 이 경로가 실행될 수 있다.**

### 5-2. `heap_file.c` — eager 호출 4개 지점

`heap_recdes_contains_oos`로 먼저 가드한 뒤 호출한다. REC_RELOCATION의 경우 실제 데이터(와 OOS)는 forward 페이지에 있으므로, **forward(REC_NEWHOME) recdes를 old로** 넘긴다(home 슬롯에는 8바이트 포인터밖에 없다).

| 함수 | old_recdes | new_recdes | 가드 |
|---|---|---|---|
| `heap_delete_home` | `home_recdes` | NULL | `record_type==REC_HOME` |
| `heap_delete_relocation` | `forward_recdes` | NULL | `forward_recdes.type==REC_NEWHOME` |
| `heap_update_home` | `home_recdes` | `recdes_p` | `home_recdes.type==REC_HOME` |
| `heap_update_relocation` | `forward_recdes` | `recdes_p` | `forward_recdes.type==REC_NEWHOME` |

**호출 위치가 중요하다**: OOS OID를 읽으려면 슬롯이 아직 살아 있어야 하므로, 이 호출은 반드시 **물리 삭제(파괴) 이전에** 일어나야 한다(코드 배치가 그렇게 돼 있다).

### 5-3. `heap_log_delete_physical` 시그니처 변경

```c
-  ..., bool mark_reusable, LOG_LSA *undo_lsa);
+  ..., bool mark_reusable, LOG_LSA *undo_lsa, LOG_RCVINDEX rcvindex);
```

- 내부에서 하드코딩돼 있던 `log_append_undoredo_recdes(thread_p, RVHF_DELETE, ...)` → 인자로 받은 `(..., rcvindex, ...)`로 일반화했다.
- 기존 호출처(`heap_delete_bigone`, `heap_delete_relocation`, `heap_delete_home`)는 전부 `RVHF_DELETE`를 명시적으로 넘기므로 → **동작 변화 없음**. 오직 §4-4의 호출 하나만 새 태그를 넘긴다.

> **✅ 리뷰 체크리스트 (eager)**
> - [ ] 4개 호출이 모두 **물리 삭제 이전**에 있는가.
> - [ ] REC_RELOCATION 경로가 home이 아니라 **forward** recdes를 넘기는가.
> - [ ] UPDATE 경로가 `new_recdes`로 `context->recdes_p`(새 이미지)를 넘겨서 교집합 보존이 동작하는가.
> - [ ] 에러가 나면 호출 스택이 트랜잭션 abort로 이어지는가(`ASSERT_ERROR();` + return → 상위에서 abort).
>
> **⚠️ 리스크 / 발견사항**
> - `heap_update_relocation`의 MVCC 두 하위 경로는 **둘 다 forward-walk가 커버한다**: ① update_old_forward(forward 슬롯 제자리 갱신) → `RVHF_UPDATE_NOTIFY_VACUUM`, ② remove_old_forward(forward 슬롯 삭제) → `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`.
> - **⚑ 소스 주석이 낡아 있던 것을 발견 → ✅ 본 브랜치에서 수정 완료**: `heap_update_relocation` 함수 상단 주석(line ~23521)이 원래 "remove_old_forward MVCC sub-paths still leak OOS until the forward-walk gate is extended... — separate follow-up"라고 **잘못** 적혀 있었다. 하지만 이후 커밋의 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` 경로가 이미 그걸 회수하고 있어서(`vacuum.c`의 `else if (rcvindex == RVHF_DELETE_NEWHOME_NOTIFY_VACUUM)` 분기: "remove_old_forward... its OOS records are reclaimed here") 코드와 주석이 모순이었다. **그래서 주석을 "두 MVCC 하위 경로 모두 forward-walk로 회수됨"으로 갱신 완료.**

---

## 6. 지연 경로 ① REMOVE (`vacuum.c` + `vacuum_oos.cpp`)

vacuum이 죽은 슬롯을 물리적으로 지울 때, 그 슬롯이 가리키던 OOS도 **같은 작업 묶음(sysop) 안에서** 함께 지운다.

```
vacuum_heap_record (REC_HOME with OOS)
  ├─ log_sysop_start                       ← 여러 페이지를 건드리는 연산이라 하나의 sysop로 묶음
  ├─ spage_vacuum_slot (슬롯 비우기)
  ├─ vacuum_heap_record_remove_oos_inline
  │     ├─ vacuum_log_redoundo_vacuum_record   (heap 슬롯 제거 로그)
  │     └─ vacuum_heap_oos_delete_within_sysop              (OOS 청크 삭제)
  │           └─ 실패 → log_sysop_abort, return
  └─ log_sysop_commit                      ← heap 슬롯 제거 + OOS 삭제가 한 덩어리로 원자적
```

> **⚠️ 왜 sysop이 꼭 필요한가 (코드로 검증 완료 — 빼면 안 됨)**
> 흔한 의문: "redo 로그가 남으니까 sysop 없어도 복구가 알아서 해주지 않나?" → **아니다.** 이유를 하나씩 보자.
> - 이 연산은 **heap home 페이지 + OOS chunk 페이지(들)** 라는 **2개 이상의 페이지**를 고친다. 단일 WAL 레코드는 **페이지 하나**에 대해서만 원자성을 보장한다. 여러 페이지를 한 덩어리로 묶는 원자성은 sysop 없이는 보장되지 않는다.
> - **vacuum worker에는 일반 사용자 트랜잭션 같은 commit/abort 경계가 없다.** 복구의 undo 단계는 `logtb_is_system_worker_tranid`로 **끝나지 않은 vacuum worker 트랜잭션을 undo 대상에 포함**시킨다(`log_recovery.c:4596`). sysop을 빼면, 이 멀티 페이지 작업을 "한 덩어리로 영속화할 수단 자체"가 없어진다.
> - sysop commit 레코드(`LOG_SYSOP_END_COMMIT`)가 디스크에 도달해야만 그 안의 변경이 영구화된다. 도달하기 전에 크래시가 나면, 복구는 `lastparent_lsa`로 점프해서(`log_manager.c:7954`) sysop 내부를 **전부 undo**한다 → **all-or-nothing(전부 또는 전무) 경계를 제공하는 건 오직 sysop뿐이다.**
> - sysop을 빼면, 부분 크래시에서 heap slot 제거는 영속화되는데 OOS 삭제만 사라질 수 있다 → **영구 dangling OOS leak**. 슬롯이 이미 사라졌으니 그 OOS를 다시 회수할 트리거가 영영 없다. `vacuum.c:2404` 주석이 경고하는 바로 그 상황이다.
> - **선례**: REC_RELOCATION / REC_BIGONE도 OOS가 생기기 전부터 똑같은 멀티 페이지 sysop 패턴을 써 왔다(`vacuum.c:2453,2534,2573`). 즉 OOS는 새 발명이 아니라 기존 패턴을 그대로 따른 것이다.

### 6-0. 케이스별 "왜 이 record는 sysop이 필요한가" (직교하는 두 축)

위 callout이 "왜 sysop이 필요한가"의 **일반 원리**(멀티 페이지 원자성)를 설명했다면, 여기서는 그 원리를 **record 종류별로** 적용해 "어떤 경우엔 sysop을 열고, 어떤 경우엔 안 여는가"를 한 장으로 정리한다. PR #6986 리뷰(discussion r3121789826)에서 반복적으로 나온 질문이다.

핵심은 sysop 필요 여부를 **`record_type` 하나로 판단하면 안 된다**는 것이다. 진짜 기준은 **연산이 건드리는 전체 페이지 수**이고, 그건 서로 **직교(orthogonal)하는 두 축**의 합으로 정해진다:

```
body footprint (record_type)        OOS footprint (heap_recdes_contains_oos)
────────────────────────────        ───────────────────────────────────────
REC_HOME       : home 1장            no OOS  : 0장
REC_RELOCATION : home + fwd 2장      has OOS : N장 (N≥1; multi-chunk면 더 많음)
REC_BIGONE     : home + ovf 체인

total footprint = body + OOS  ⇒  total이 home page를 벗어나면(> 1장) sysop 필요
```

| record_type | OOS? | 건드리는 페이지 | 경로 | sysop |
|---|---|---|---|---|
| `REC_HOME` | 없음 | home 1장 | bulk 로그 누적 (`n_bulk_vacuumed++`) | **불필요** |
| `REC_HOME` | 있음 | home + OOS N장 | `case REC_HOME`의 `if (has_oos)` 인라인 분기 | **필요** (`has_oos`) |
| `REC_RELOCATION` | 무관 | home + fwd (+ OOS) | forward 비우고 commit 직전 OOS 삭제 | **필요** |
| `REC_BIGONE` | 비공존 | home + overflow 체인 | overflow 삭제 | **필요** (OOS는 §6-5 assert) |

**왜 평범한 REC_HOME만 sysop을 안 여는가 (이게 표의 핵심):**

`REC_HOME` + OOS 없음은 **유일하게 single-page** 연산이다. heap 슬롯 하나를 비우는 게 전부고, 그건 **단일 WAL 레코드 하나**로 로깅된다. 단일 페이지에 대한 단일 로그 레코드는 **그 자체로 원자적**이다(크래시는 그 페이지를 그 LSA까지 반영했거나 안 했거나 둘 중 하나) → 묶을 게 없으니 sysop이 필요 없고, 그래서 성능을 위해 여러 슬롯을 모아 한 번에 로깅하는 **bulk 경로**를 탄다.

나머지 세 경우는 전부 **2장 이상**을 건드린다. 페이지마다 디스크 flush 시점이 제각각이라, sysop 없이는 "일부 페이지만 반영된 찢어진 상태"가 가능하다. sysop이 그 여러 per-page 로그를 **all-or-nothing 한 덩어리**로 묶어준다(상세 원리는 위 §6 callout).

> **요점**: `record_type`은 페이지 수를 **부분적으로만** 알려주는 proxy다. OOS는 그것과 **직교하는 별도 축**이라, body가 1장인 `REC_HOME`도 OOS가 붙는 순간 멀티 페이지가 되어 sysop 경로로 승격된다 — 그래서 `case REC_HOME: if (has_oos)` 분기가 존재한다.

> **쉽게 말하면**: 짐이 한 칸(home page)에 다 들어가면 그 칸만 잠그면 된다(sysop 불필요). 짐이 여러 칸에 걸치면(forward / overflow / OOS locker), "전부 한꺼번에, 아니면 아무것도 안" 을 보장하는 한 장의 운송장(sysop)으로 묶어야 한다.

> **🔗 코드/문서 동기화**: 이 판단 매트릭스는 엔진 코드에도 박아두었다 — `src/query/vacuum.c`의 `has_oos` 계산 바로 위 주석, 그리고 ADR `docs/adr/0001-synchronous-oos-reclaim-in-vacuum-sysop.md`(동기 OOS 회수 결정 + deferred 대안 비교). 세 곳(코드 주석 / ADR / 이 가이드)이 같은 표를 공유한다.

### 6-1. `vacuum_heap_helper`에 `oos_vfid` 필드 추가

```c
  VFID overflow_vfid;
+ VFID oos_vfid;          /* OOS file identifier (if any). */
```

`vacuum_heap_page`에 진입할 때 `VFID_SET_NULL(&helper.oos_vfid)`로 초기화한다.

### 6-2. prepare 단계에서 OOS VFID를 지연 조회

`vacuum_heap_prepare_record`의 REC_HOME / REC_RELOCATION 케이스에서 `vacuum_oos_find_vfid_for_heap_record(...)`를 호출해 `helper->oos_vfid`를 채운다.

### 6-3. `vacuum_heap_record` — `has_oos` 판정과 sysop 묶기

```c
bool has_oos = (!VFID_ISNULL (&helper->oos_vfid)
                && (helper->record_type == REC_HOME || helper->record_type == REC_RELOCATION)
                && heap_recdes_contains_oos (&helper->record));

if (record_type == REC_RELOCATION || record_type == REC_BIGONE || has_oos)
  { vacuum_heap_page_log_and_reset (...); log_sysop_start (...); }
```

- **REC_HOME + OOS** 도 이제 멀티 페이지 연산으로 취급한다 → 그동안 쌓아둔 bulk vacuum 슬롯을 먼저 flush하고, 단독 sysop를 시작한다. 이렇게 안 하면 "heap 슬롯 제거 로그"와 "OOS 삭제"가 서로 다른 sysop로 쪼개져, 그 둘 사이에서 크래시가 나면 **dangling OOS**가 생긴다.
- REC_HOME 분기: `has_oos`면 `vacuum_heap_record_remove_oos_inline` 호출, 아니면 기존대로 `n_bulk_vacuumed++`.
- REC_RELOCATION 분기: forward 페이지를 비운 뒤, commit **직전**에 `has_oos`면 `vacuum_heap_oos_delete_within_sysop`를 호출.

### 6-4. `vacuum_heap_record_remove_oos_inline()` (신규 헬퍼)

REC_HOME 전용이다. 순서는 `pgbuf_set_dirty` → `vacuum_log_redoundo_vacuum_record` → `vacuum_heap_oos_delete_within_sysop` → 성공하면 `log_sysop_commit`, 실패하면 `log_sysop_abort`. **호출 전제(주석 계약)**: 호출자가 이미 sysop을 연 상태여야 하고, 슬롯도 `spage_vacuum_slot`로 비워둔 상태여야 한다.

### 6-5. REC_BIGONE 불변식 assert (2곳)

```c
/* Invariant: OOS does not coexist with REC_BIGONE. */
assert (!(MVCC_GET_FLAG (&helper->mvcc_header) & OR_MVCC_FLAG_HAS_OOS));
```

- REC_BIGONE은 본문이 overflow 페이지에 있어서 `helper->record`가 **채워지지 않는다.** 그래서 OOS 플래그를 `helper->record`가 아니라 **`helper->mvcc_header`** 에서 읽어야 한다(채워지지 않은 record를 잘못 dereference하는 것을 막기 위함).
- 지금은 "OOS와 REC_BIGONE은 공존하지 않는다"는 가정이 깔려 있다. 만약 이 assert가 발동하면, REMOVE 경로에 overflow OOS 회수 루프를 추가해야 한다는 신호다 → 디버그에서 시끄럽게(loud) 터뜨려 알린다.

> **✅ 리뷰 체크리스트 (REMOVE)**
> - [ ] `has_oos`의 세 조건(VFID non-null && REC_HOME|REC_RELOCATION && contains_oos)이 모두 필요한가.
> - [ ] REC_HOME+OOS가 sysop 분기 조건에 들어가서 bulk 슬롯이 먼저 flush되는가.
> - [ ] inline 헬퍼의 commit/abort가 모든 경로에서 정확히 한 번씩 짝이 맞는가.
> - [ ] REC_BIGONE assert가 `record`가 아니라 `mvcc_header` 기준인가.

---

## 7. 지연 경로 ② Forward-walk (`vacuum.c` + `vacuum_oos.cpp`)

가장 정교한 부분이다. UPDATE/remove-old-forward에서 옛 OOS OID는 **살아있는 슬롯에는 없고 undo 이미지에만** 있다. 그래서 vacuum이 로그 블록을 훑으며 undo 이미지를 파싱해서 회수한다.

```
heap_update_relocation / heap_update_home  (MVCC)
  └─ log RVHF_UPDATE_NOTIFY_VACUUM  (undo = 옛 REC_HOME/REC_NEWHOME, OOS 포함)
        │   또는 RVHF_DELETE_NEWHOME_NOTIFY_VACUUM (remove_old_forward)
        ▼  (나중에, vacuum worker가 처리)
  vacuum_process_log_block
   ├─ (rcvindex == RVHF_UPDATE_NOTIFY_VACUUM)            ← MVCC heap-op 블록 안
   │     └─ vacuum_forward_walk_reclaim_oos(...)
   └─ (rcvindex == RVHF_DELETE_NEWHOME_NOTIFY_VACUUM)    ← MVCC heap-op 블록 밖 (수집할 슬롯 없음)
         └─ vacuum_forward_walk_reclaim_oos(...)
               ├─ undo image를 private buffer로 snapshot   ← 로그 페이지가 회전하는 것에 대비 (필수)
               ├─ vacuum_oos_vfid_cache_lookup            ← heap VFID → OOS VFID (블록 단위 캐시)
               ├─ heap_recdes_get_oos_oids                ← undo recdes에서 옛 OID 추출
               └─ vacuum_forward_walk_oos_delete_atomic      ← 정렬 + 멱등 probe + sysop 삭제
```

### 7-1. `vacuum_process_log_block` — rcvindex 게이트 (★ 가장 리뷰 민감)

```c
if (log_record_data.rcvindex == RVHF_UPDATE_NOTIFY_VACUUM)
  { vacuum_forward_walk_reclaim_oos (...); }
```

주석이 길게 설명하는 **"받아들일 것(admit) / 거를 것(exclude)" 규칙**:

- **admit `RVHF_UPDATE_NOTIFY_VACUUM`**: UPDATE는 변환할 때마다 새 OID를 만든다 → undo의 옛 OID는 살아있는 슬롯과 겹치지 않는다(disjoint). 그러니 forward-walk만이 회수할 수 있다.
- **exclude `RVHF_MVCC_DELETE_MODIFY_HOME`**: 논리 DELETE는 recdes 내용을 그대로 두고 `delete_mvccid`만 바꾼다. 삭제 후에도 슬롯이 **같은 OID**를 계속 가리킨다 → 이건 REMOVE 경로가 회수한다. 여기에 forward-walk까지 돌리면 **이중 삭제**가 되어 `oos_delete_chain`의 `S_DOESNT_EXIST` assert를 친다. **이 rcvindex 게이트 한 줄이 그 배제를 떠받치는 핵심(load-bearing) 라인**이다.
- INSERT / DELETE_REC_HOME / NO_MODIFY_HOME / REDISTRIBUTE는 undo에 pre-image recdes가 없어서 `undo_data_size > sizeof(INT16)` 조건에 자연스럽게 걸러진다.

따로, MVCC heap-op 블록 **바깥**에서 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`도 같은 헬퍼를 호출한다(§4-5). 일부러 바깥에 둔 이유: 슬롯이 이미 물리 삭제돼서 collect할 게 없기 때문이다.

### 7-2. `vacuum_process_log_record` — undo unpack 게이트 확장

```c
if (!LOG_IS_MVCC_BTREE_OPERATION (...)
    && rcvindex != RVHF_UPDATE_NOTIFY_VACUUM
    && rcvindex != RVES_NOTIFY_VACUUM
    && rcvindex != RVHF_DELETE_NEWHOME_NOTIFY_VACUUM)
  { return NO_ERROR; /* undo unpack 불필요 */ }
```

forward-walk는 undo 이미지를 들여다봐야 한다. 그래서 두 신규 rcvindex에 대해서는 undo unpack을 **켜준다**. 안 켜면 `undo_data`가 NULL이라 회수가 **조용히 누락**된다.

### 7-3. `vacuum_oos.cpp` — VFID 캐시 (`VACUUM_OOS_VFID_CACHE`)

- heap VFID → OOS VFID 매핑을 **블록 단위**로 캐싱한다(`file_descriptor_get` + `heap_oos_find_vfid`를 매번 반복하는 비용을 피함). 16개 엔트리 라운드로빈.
- **`VFID_NULL` 음성 sentinel**: "이 heap에는 OOS 파일이 없다"도 캐시한다 → OOS 없는 heap이면 반복 조회를 건너뛴다.
- **3-상태 결과** `FOUND / NONE / ERROR`: transient 실패(`file_descriptor_get` 실패 등)는 **캐시하지 않는다.** 잘못 캐시된 `VFID_NULL`은 그 블록의 이후 모든 레코드 회수를 건너뛰게 만드는 독(poison)이 되기 때문이다. 오직 "정당하게 OOS가 없는 경우"(false 반환 + 에러 없음)만 캐시한다.
- **스레드 안전**: 캐시를 `vacuum_process_log_block`의 스택에 선언한다 → worker마다, 블록마다 따로. **static으로 바꾸면 worker 간 레이스**가 난다(주석 경고).

### 7-4. `vacuum_forward_walk_reclaim_oos` — undo image snapshot (비직관적 버그 방지)

```c
RECDES parse_recdes = undo_recdes;
char *stable_copy = db_private_alloc (thread_p, undo_recdes.length);
memcpy (stable_copy, undo_recdes.data, undo_recdes.length);
parse_recdes.data = stable_copy;
```

왜 굳이 복사부터 할까?

- undo 이미지는 보통 worker의 **현재 로그 페이지 버퍼**를 직접 가리킨다. 그런데 이후 `vacuum_oos_vfid_cache_lookup` 안에서 page fix가 일어나면, 그게 로그 활동을 유발해 **그 버퍼를 다른 내용으로 회전(rotate)** 시킬 수 있다. 회전된 뒤에 파싱하면 0이나 엉뚱한 바이트를 읽어서, **아무 OID도 못 뽑고 조용히 지나간다**(실측: flags 워드가 0x69 → 0x00으로 바뀜). 그래서 **page fix가 일어나기 전에** private buffer로 미리 복사해 둔다.
  > **쉽게 말하면**: 화이트보드에 적힌 메모를 그대로 두면 잠시 후 누가 지워버릴 수 있다. 그러니 먼저 **사진을 찍어(복사)** 두고, 사진을 보고 작업하는 것이다.
- 복사하면 **정렬(alignment)도 덤으로 교정**된다. 정렬이란 "여러 바이트짜리 값은 그 크기의 배수 주소에서 읽어야 한다"는 규칙이다(8바이트 OID는 8의 배수 주소에서). 그런데 로그의 undo 데이터는 `[INT16 타입(2바이트)][본문...]` 구조라(`log_manager.c:2525-2528`), 본문은 항상 `undo_data + 2`에서 시작한다. `undo_data`는 8의 배수인데 거기에 2를 더했으니 본문은 **8의 배수가 아니다(2바이트 어긋남)**. 이 어긋난 주소에서 OR_BUF 리더(`or_get_oid`)가 OID를 읽으려 하면 디버그 빌드에서 정렬 assert가 터진다. 새로 할당한 버퍼(`db_private_alloc`)는 항상 정렬돼 있으므로, 본문을 그 맨 앞으로 복사하면 정렬이 저절로 맞는다.
  > **쉽게 말하면**: 큰 물건은 선반 칸 경계(8칸마다)에 맞춰 놓기로 약속했는데, 원본은 칸 중간(+2)에 걸쳐 있다. 복사본은 새 선반의 칸 경계(0)에서 다시 시작하니 규칙에 맞는다.
  >
  > **"그럼 복사 말고, `undo_recdes.data`를 만들 때 정렬을 맞추면 안 되나?" → 안 된다.**
  > - **포인터만 옮기는 건 불가능**: 본문 바이트가 물리적으로 `undo_data + 2`에 박혀 있다. 포인터를 8경계로 올리거나 내리면 엉뚱한 바이트를 가리킬 뿐, 데이터를 안 옮기고 정렬을 맞출 수는 없다. 정렬을 맞추려면 결국 바이트를 옮겨야 하고, 그게 바로 이 `memcpy`다.
  > - **로그를 쓰는 쪽(writer)에서 본문을 8정렬로 만드는 것도 안 된다**: 그 `[INT16][본문]` 패킹은 `RVHF_INSERT`, `MVCC_DELETE`, `UPDATE_NOTIFY_VACUUM` 등 **모든 heap recdes 로깅이 공유**하는 공용 경로다. 건드리면 **on-disk 로그 포맷 변경**이라 복구 호환성·기존 로그 재생이 다 깨진다(§4의 "로그 포맷 동결" 원칙 위반). 이 PR 범위가 아니다.
  > - **결정타**: 정렬을 어떻게 고치든 **복사 자체는 못 없앤다**. 복사의 1순위 이유는 정렬이 아니라 위의 **버퍼 회전 방지**(release 빌드에서도 실제 데이터 손실)이기 때문이다. 어차피 private buffer로 떠와야 하니, 정렬 교정은 그 복사에 **공짜로 딸려오는 보너스**다 — 그래서 "덤으로"라고 적었다.
- **record-type 가드**: `(REC_HOME || REC_NEWHOME) && heap_recdes_contains_oos`를 통과한 것만 처리한다. forwarding 포인터(8B OID)를 `heap_recdes_contains_oos`에 넣으면, pageid의 bit 27이 `OR_MVCC_FLAG_HAS_OOS`로 오인돼서 엉터리 VOT를 walk하다 `assert_release`를 친다 → §3 경고 참조.

### 7-5. `vacuum_forward_walk_oos_delete_atomic` — 정렬 + 멱등 probe

```c
std::sort(oos_oids ...);            // (volid,pageid,slotid) 순 → 버퍼 풀 지역성(locality) 향상
log_sysop_start;
for (oid : oos_oids) {
   oos_chunk_exists(oid, &exists);  // ← 멱등성: 블록 재시도에 대비
   if (!exists) continue;           //    이미 사라진 청크는 skip (S_DOESNT_EXIST assert 회피)
   oos_delete(oos_vfid, oid);
}
log_sysop_commit / abort;
```

- **OID를 값으로(by-value vector) 받는다**: `oos_delete`가 undo_data가 가리키던 로그 페이지를 회전시킬 수 있으므로, 호출자가 자기 소유 벡터를 `std::move`로 넘기고 그 위에서 정렬/삭제한다.
- **멱등성(idempotency)**: 블록을 재시도하면, 같은 블록의 앞선 forward-walk가 이미 sysop commit을 했을 수 있다. 그 경우 그 OID의 청크는 이미 사라졌으니, `oos_chunk_exists`로 확인해 skip한다 — `oos_delete_chain`의 `S_DOESNT_EXIST` hard error를 피하려는 것이다. 단, **진짜 probe 실패(I/O 등)는 그대로 전파**한다.

### 7-6. 실패 정책: 제한적이고 기록되는 누수(bounded, logged leak)

`vacuum_forward_walk_reclaim_oos`의 모든 실패(VFID lookup ERROR, alloc 실패, delete 실패)는 **에러를 위로 전파하지 않는다.** 대신 `vacuum_er_log_error`로 시끄럽게(loud) 로그를 남긴 뒤 `er_clear`하고 그냥 반환한다.

이유: forward-walk 실패로 블록 전체를 실패시키면, `vacuum_finished_block_vacuum`의 shutdown-only assert를 쳐서 **vacuum이 멈춰버릴(wedge)** 위험이 있다. 반면 여기서 생기는 누수는 **제한적**(해당 레코드의 OOS 청크들로 한정)이고, 로그로 추적할 수 있다. 그래서 "전체를 멈추느니, 한정된 누수를 로그로 남기고 진행"을 택한다.

### 7-7. `vacuum_oos_find_vfid_for_heap_record` (REMOVE 경로용 lazy lookup, §6에서 사용)

레코드가 HAS_OOS 플래그를 갖고 있는데 OOS 파일을 못 찾는 경우를 생각해 보자. 이건 lazy-creation 아티팩트가 **아니다**(파일은 청크를 쓸 때 `docreate=true`로 먼저 만들어진다). 대신 **거짓 플래그 / 드롭된 파일 / 복구 순서 edge case** 중 하나를 뜻한다. 그래서:

- **디버그**: `assert_release`로 즉시 실패시킨다(플래그를 잘못 심는 버그를 첫 vacuum에서 바로 잡으려고).
- **릴리스**: log + er_clear + skip(제한적 누수로 넘어감).

여기서 만약 `ER_FAILED`를 반환하면 `vacuum_heap_page` 루프의 release-only spin(§8-1)이 다시 무장되므로, **절대 에러를 반환하지 않는다.**

### 7-8. 두 OOS 삭제 함수는 왜 sysop 처리가 다른가 (`_within_sysop` vs `_atomic`)

리뷰 중 자주 나오는 질문: "둘 다 OOS를 지우는 거의 똑같은 함수인데, 왜 하나(`vacuum_forward_walk_oos_delete_atomic`)는 `log_sysop_start`를 하고, 다른 하나(`vacuum_heap_oos_delete_within_sysop`)는 안 하나? 일관성이 없는 것 아닌가?"

결론부터: **버그가 아니라 의도된 설계다.** 두 함수의 호출자를 끝까지 추적해서 검증했다.

**먼저, 둘 다에 공통으로 깔린 규칙 하나:**

> **규칙: OOS 삭제는 "정확히 하나의 sysop" 안에서 일어나야 한다.**
> - **0개(sysop 없음)는 안 됨**: OOS 삭제는 여러 OOS chunk 페이지를 건드리는데, 단일 WAL 레코드는 페이지 하나만 원자적으로 보장한다. 게다가 vacuum worker에는 일반 트랜잭션 같은 commit 경계가 없다. sysop이 없으면 부분 크래시에서 일부만 영속화돼 dangling OOS leak이 생긴다(§6 callout 참조).
> - **2개(중첩 sysop)도 안 됨**: 안쪽 sysop이 따로 commit되면 바깥 작업과 **따로** 영속화되어 원자성이 쪼개진다.

그러니 진짜 질문은 "sysop을 쓰냐 마냐"가 아니라 **"그 하나뿐인 sysop을 누가 여느냐"** 다. 답은 **호출자가 어떤 상황이냐**에 따라 갈린다.

| | `vacuum_heap_oos_delete_within_sysop` | `vacuum_forward_walk_oos_delete_atomic` |
|---|---|---|
| 호출자 | `vacuum_heap_record` (REMOVE 경로) | `vacuum_process_log_block` (forward-walk) |
| 호출 시점 호출자 상태 | **이미 sysop을 연 상태** (`vacuum.c:2439`) | **연 sysop이 전혀 없음** (이 함수·그 호출자 어디에도 `log_sysop_start`가 없음 — 검증 완료) |
| 그래서 이 함수는 | sysop을 **열지 않는다** (호출자 것에 올라탐) | sysop을 **직접 연다** (commit/abort까지 자기 책임) |
| 이름의 의미 | `_within_sysop` = 호출자의 sysop **안에서** 실행 (자기 sysop을 안 엶) | `_atomic` = 그 자체로 **원자적 단위** (자기 sysop을 엶) |

**왜 `_within_sysop`은 자기 sysop을 열면 안 되나 (핵심):**

REMOVE 경로에서 `vacuum_heap_record`는 **"heap 슬롯 제거 로그 + OOS 삭제"를 한 덩어리로** 묶으려고 sysop을 미리 연다(`vacuum.c:2439`). OOS 삭제는 그 묶음의 한 조각일 뿐이다. 만약 `vacuum_heap_oos_delete_within_sysop`이 **자기만의 sysop을 열어서 commit**해 버리면, OOS 삭제가 heap 슬롯 제거와 **따로** 영속화된다 → 그 둘 사이에서 크래시가 나면 슬롯은 사라졌는데 OOS는 남는(혹은 그 반대) dangling 상태가 된다. 바로 §6에서 막으려던 그 사고다. 그래서 이 함수는 **반드시 호출자의 sysop을 공유**해야 하고, 자기 sysop을 열어선 안 된다.

> 코드의 전제 조건(이번 브랜치에서 주석으로 명시): "호출자가 이미 sysop을 연 상태여야 한다. 이 함수는 일부러 sysop을 시작하지 않는다."

**왜 `_atomic`은 자기 sysop을 꼭 열어야 하나:**

forward-walk 경로의 `vacuum_process_log_block`은 sysop을 전혀 열지 않은 채로 이 함수를 부른다(코드 확인: 이 함수 전체와 그 호출자 `vacuum_worker_task::execute` / `vacuum_sa_run_job` 어디에도 `log_sysop_start`가 없다). 그러니 멀티 청크 OOS 삭제를 원자적으로 만들어 줄 주체가 **이 함수 자신밖에 없다.** 그래서 자기가 직접 열고 닫는다.

**쉽게 말하면:**
> 두 사람 모두 "상자 여러 개를 한 번에 옮긴다(= 한 번에 commit)"는 같은 규칙을 지켜야 한다.
> - `_within_sysop`은 **이미 출발 준비된 이삿짐 트럭(호출자의 sysop)에 자기 상자를 같이 싣는** 사람이다. 자기가 따로 택배(별도 sysop)를 부르면 그 상자만 다른 시간에 도착해서 "세트로 함께 도착" 약속이 깨진다.
> - `_atomic`은 **자기 짐을 옮겨 줄 트럭이 아예 없는** 사람이다. 그래서 자기가 트럭(sysop)을 직접 부른다.

**한 줄 더 — 이 차이를 뒷받침하는 독립 증거(멱등성):**

`_atomic`에만 `oos_chunk_exists` 멱등 probe가 있다(§7-5). 이유가 sysop 구조와 정확히 맞물린다: `_atomic`은 자기 sysop을 **독립적으로** commit하므로, 블록이 재시도되면 앞서 commit된 삭제가 이미 영속화돼 있을 수 있다 → "이미 사라진 청크"를 만날 수 있어 skip이 필요하다. 반대로 `_within_sysop`은 호출자의 단일 sysop을 공유하므로, 실패 시 호출자가 abort하면 **전부 함께 롤백**된다 → 재시도해도 늘 깨끗한 상태에서 시작하니 멱등 probe가 애초에 필요 없다. **sysop 소유 차이와 멱등성 유무는 같은 설계 결정의 양면이다.**

> **요약**: 두 함수는 "OOS 삭제는 하나의 sysop 안에서"라는 **같은 불변식**을 지키되, **호출자가 이미 sysop을 열었는지**가 달라서 한쪽은 올라타고(`_within_sysop`) 한쪽은 직접 연다(`_atomic`). 그 역할이 이름에 드러나도록 이번 브랜치에서 개명했다(이전 이름: `vacuum_heap_oos_delete` / `vacuum_forward_walk_delete_old_oos`).

> **✅ 리뷰 체크리스트 (forward-walk)**
> - [ ] rcvindex 게이트가 `RVHF_UPDATE_NOTIFY_VACUUM`만 admit하고 `RVHF_MVCC_DELETE_MODIFY_HOME`은 **배제**하는가(이중 삭제 방지).
> - [ ] `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`이 MVCC heap-op 블록 **바깥**에서 처리되는가.
> - [ ] §7-2 undo unpack 게이트에 두 신규 rcvindex가 추가됐는가(빠지면 회수가 조용히 누락됨).
> - [ ] page fix **이전에** undo image를 snapshot하는가(버퍼 회전 버그).
> - [ ] record-type 가드(REC_HOME/REC_NEWHOME)가 contains_oos **앞에** 있는가(거짓 양성 assert).
> - [ ] VFID 캐시가 stack-local(블록 단위)인가 — static은 금지.
> - [ ] 모든 실패가 제한적 누수로 degrade하고 블록 전체를 실패시키지는 않는가.

---

## 8. 버그픽스 (회수와 직접 엮인 안정화)

### 8-1. `vacuum.c` — release-only spin-loop 픽스 (★ 중요)

```c
      er_clear ();
      error_code = NO_ERROR;
+     // for-헤더에 증가식이 없다 — page_ptr은 성공 경로에서만 전진한다.
+     // 여기서 그냥 continue하면 같은 page_ptr을 영원히 재시도 (release 빌드에서 CPU spin).
+     page_ptr = obj_ptr;
      continue;
```

- `vacuum_heap_page`의 for 루프는 헤더에 증가식이 없고, `page_ptr`은 성공 경로에서만 전진한다. 그래서 릴리스 빌드에서 에러를 삼키고 `continue`하면 **같은 페이지를 무한히 재시도**하는 CPU spin이 된다(이전 PR 6986에서 관측된 회귀). `page_ptr = obj_ptr`로 다음 페이지 그룹으로 강제 전진시켜, 영구 실패 페이지를 skip한다. forward-walk / VFID-lookup이 절대 에러를 전파하지 않는 설계(§7-6, §7-7)와 짝을 이룬다.

### 8-2. `oos_file.cpp` — `oos_get_stats_by_vfid` 추출 + slot-0 언더카운트 픽스

```c
- spage_collect_statistics (page_ptr, ...);   // slot 0을 건너뜀(heap 페이지로 가정)
+ PGSLOTID slotid = -1;  RECDES slot_recdes;
+ while (spage_next_record (page_ptr, &slotid, &slot_recdes, PEEK) == S_SUCCESS)
+   { total_recs++; total_sumlen += slot_recdes.length; }
```

- `xoos_get_stats_by_class_oid`의 핵심 로직을 `oos_get_stats_by_vfid`로 추출했다(카탈로그에 안 붙은 OOS 파일 — 유닛테스트용 heap — 에도 쓸 수 있게). 테스트가 OOS 통계를 VFID로 직접 검증할 수 있게 하는 **테스트 가능성(testability)** 개선이다.
- **버그**: `spage_collect_statistics`는 slot 0을 heap 헤더로 가정하고 건너뛴다. 그런데 OOS 데이터 페이지는 slot 0부터 레코드를 둔다 → **페이지당 레코드 1개씩 적게 셈(언더카운트)**. `spage_next_record`로 명시적으로 walk해서 바로잡았다.

### 8-3. `oos_file.cpp` — `oos_chunk_exists` (멱등 probe, §7-5에서 사용)

`oos_delete`의 읽기 전용 짝꿍이다. "이미 사라짐"을 **좁게** 정의한다: (a) `pgbuf_fix_if_not_deallocated`가 NO_ERROR이면서 page==NULL인 경우(페이지가 deallocate됨), 또는 (b) `spage_get_record`가 `S_DOESNT_EXIST`인 경우(슬롯이 제거됨). **그 외 모든 실패(진짜 I/O 에러, S_ERROR)는 전파**한다 — 호출자가 그걸 "gone"으로 오인하면 안 되기 때문이다.

### 8-4. `oos_util.cpp` — `heap_recdes_compute_oos_flag_debug` VOT 검증 강화 (디버그 전용)

> **🚫 리뷰 대상 아님 (do not review)**: 이 §8-4 변경과 그 밖의 **OVF(overflow record) 스펙 변경에 따른 부수 수정**들은 CBRD-26668(회수)의 본류가 아니라 OVF 스펙 변경에 맞춘 기계적 적응이다. **리뷰 포인트가 아니므로 줄 단위 검토는 불필요**하며, 아래 설명은 배경 참고용이다.
> (참고: 이 디버그 헬퍼는 `heap_file.c`에서 `oos_util.cpp`로 옮겼고, 릴리스 빌드에는 호출자가 없다 — `#if !defined(NDEBUG)` 전용이라 런타임 영향 0.)

- 클래스/루트 레코드는 내부 포맷이 달라서 VOT로 해석하면 garbage가 나온다. 그래서 루프 전 가드에서 **첫 VOT 엔트리가 합리적인 offset인지**(`[0, length - header_size]` 범위) 검사한다. 또한 offset 기준을 **end-of-header 상대**로 교정했다(기존 `recdes->length` 기준은 버그였고, `header_size`를 빼야 맞다).
- 루프 로직도 재구성: `has_oos`를 누적한 뒤 `LAST_ELEMENT`에서 결과를 반환한다. `LAST_ELEMENT`가 없으면(구포맷 VOT) 홀수 offset이 만드는 거짓 양성을 막기 위해 `false`로 처리한다. **디버그 전용**(`#if !defined(NDEBUG)`)이라 런타임 영향은 없다.

> **✅ 리뷰 체크리스트 (버그픽스)**
> - [ ] spin-loop 픽스: `page_ptr = obj_ptr`가 release-only 경로에만 있고 디버그 경로 의미를 바꾸지 않는가.
> - [ ] stats: slot 0을 포함하는 게 의도대로이고, 기존 `xoos_get_stats_by_class_oid` 결과가 1만큼 늘어나는 게 정상인가(회귀가 아니라 교정인가).
> - [ ] `oos_chunk_exists`가 "gone"을 좁게만 인정하고 나머지는 전파하는가.

---

## 9. 테스트 커버리지

> **🔎 리뷰 범위 안내 (필독)**: 이 섹션이 다루는 **테스트 코드(unit test, E2E, mock, SQL 종단 테스트 등)는 선택적(optional) 리뷰 대상**이다. 본 PR의 +4822줄 중 약 3,500줄이 테스트이지만, **필수 리뷰 대상은 §3~§8이 다루는 실제 엔진 코드 약 1,300줄**이다. 테스트는 그 엔진 코드의 주장을 뒷받침하는 **근거(evidence)**로서 참고용이며, 시간이 빠듯하면 §9-2의 핵심 시나리오 4개만 훑고 넘어가도 무방하다. 테스트의 정확성·스타일을 줄 단위로 검토할 필요는 없다.

### 9-1. 신규 테스트 파일 지도

| 테스트 파일 (줄수) | Fixture | 검증 대상 | 경로 |
|---|---|---|---|
| `test_oos_server.cpp` (471) | `OosVacuumCodePathServer` | `heap_recdes_contains_oos`, `heap_recdes_get_oos_oids`, `vacuum_heap_oos_delete_within_sysop` 직접 단위 + bulk reclaim | deferred(헬퍼) |
| `test_oos_vacuum_server.cpp` (656) | `OosVacuumServer` | REMOVE 경로: insert/delete, multi-chunk, large multi-page, MVCC update, bulk reclaim+reuse, churn | deferred(REMOVE) |
| `test_oos_real_vacuum_server.cpp` (509) | `OosRealVacuum` | **실제 vacuum 데몬 E2E**: single-row drain, multi-chunk chain drain, update stale 회수+new 생존, snapshot이 회수 차단 후 drain | deferred(E2E) |
| `test_oos_mock_vacuum_server.cpp` (417) | (mock) | forward-walk 로직을 데몬 없이 단위 검증 | deferred(forward-walk) |
| `test_oos_delete_server.cpp` (390) | `OosDeleteServerTest` | SERVER 모드 DELETE 즉시 회수, multi-chunk, update pattern, free space 복원, 160KB | eager/REMOVE |
| `test_oos_remove_file_server.cpp` (202) | `OosFileDestroyServerTest` | OOS 파일/페이지 destroy, 캐시 클리어, 다중 파일 | 파일 수명 |
| `test_oos_sql_eager_cleanup.cpp` (720) | (SQL) | SQL 레벨 eager cleanup(SA) 종단 검증 | eager |
| `test_oos_server_common.hpp` (269) | — | SERVER 모드 공용 fixture(부팅/통계 헬퍼) | — |

### 9-2. 핵심 시나리오 (리뷰 시 꼭 볼 것)

- **`OosRealVacuum.UpdateStaleVersionDrainsNewSurvives`**: forward-walk 정확성의 핵심. UPDATE 후 옛 OOS는 drain(청소)되고 **새 OOS는 살아남아야** 한다 — §7의 admit/exclude 규칙을 살아있는 형태로 검증한다.
- **`OosRealVacuum.SnapshotBlocksReclaimThenDrains`**: 활성 snapshot이 회수를 막다가(MVCC 가시성), snapshot이 풀리면 drain된다 — 지연 회수가 왜 정당한지를 보여주는 테스트.
- **`OosVacuumServer.BulkVacuumReclaimAndReuse`** / **`MultiUpdateChurnVacuum`**: REMOVE 경로의 sysop 묶기(§6-3)와 free space 재사용 검증.
- **`OosDeleteServerTest.OosUpdatePattern`**: eager UPDATE의 교집합 보존(§5-1) 검증.

### 9-3. CMake/픽스처 변경 (리뷰 시 주의)

- `unit_tests/oos/CMakeLists.txt`: GLOB 자동수집을 **명시적 `SA_MODE_TESTS` / `SERVER_MODE_TESTS` 리스트**로 교체. SERVER 테스트는 `cubrid`+`SERVER_MODE`, SA 테스트는 `cubridsa`+`SA_MODE`로 링크. SERVER 테스트는 `RUN_SERIAL TRUE`(in-process 서버끼리 충돌 방지) + TIMEOUT 60/120.
- **`vacuum_log_block_pages=4`** 를 `[@unittestdb]` 섹션에 createdb **이전에** 주입한다(기본값 31). real-vacuum 테스트가 로그 블록을 빨리 닫아서 회수를 트리거하기 위함이다. 이 값은 createdb 시 DB에 freeze되므로 **순서가 중요**하다. append는 idempotent하고, scope는 unittestdb로만 한정된다.

> **✅ 리뷰 체크리스트 (테스트)**
> - [ ] real-vacuum E2E가 실제 데몬을 polling하면서 TIMEOUT 120/RUN_SERIAL로 격리되는가.
> - [ ] `vacuum_log_block_pages=4` 주입이 createdb 이전이고, 다른 DB에는 영향이 없는가.
> - [ ] 새 라이선스 헤더가 CUBRID 단독 Apache(2016)인가(테스트 파일 포함).

---

## 10. 핵심 불변식 & 리스크 요약 (consolidated)

| # | 불변식 / 리스크 | 위치 | 깨지면 |
|---|---|---|---|
| 1 | OOS OID는 행 간 비공유, 변환마다 새로 할당 | 설계 전제 | eager 무조건 삭제·forward-walk 분리의 근거가 무너짐 |
| 2 | rcvindex 134/136은 **on-disk 고정**, append-only | `recovery.h` | 기존 로그/복구 깨짐, `RV_fun[]` 슬롯 밀림 |
| 3 | forward-walk 게이트는 `UPDATE_NOTIFY_VACUUM`만 admit, `MVCC_DELETE_MODIFY_HOME` 배제 | `vacuum.c` §7-1 | 이중 삭제 → `S_DOESNT_EXIST` assert |
| 4 | page fix **이전**에 undo image snapshot | `vacuum_oos.cpp` §7-4 | 버퍼 회전 → 조용한 회수 누락 |
| 5 | forward-walk/lazy-lookup은 **에러 전파 금지**(제한적 누수) | §7-6, §7-7, §8-1 | vacuum이 멈춤(wedge) / release CPU spin |
| 6 | REC_BIGONE은 OOS와 비공존, 플래그는 `mvcc_header`에서 읽기 | `vacuum.c` §6-5 | 미초기화 `record` dereference |
| 7 | record-type 가드가 `contains_oos`보다 앞에 | §7-4, §5-2 | forwarding OID 오인 → 엉터리 VOT assert |
| 8 | eager 에러 시 트랜잭션 abort 필수 | `heap_oos.cpp` §5-1 | 살아남은 recdes가 삭제된 청크를 참조 |

### 발견된 stale 주석 / 미해결
- **⚑ stale 주석 → ✅ 수정 완료**: `heap_update_relocation` 상단 주석이 "remove_old_forward가 여전히 누수한다"고 잘못 적혀 있었으나, 이후 추가된 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` 경로가 이미 회수한다(`vacuum.c` else-if 분기). 본 브랜치에서 주석을 "두 MVCC 하위 경로 모두 forward-walk로 회수됨"으로 **갱신 완료**(§5 발견사항 참조).
- `RVOOS_NOTIFY_VACUUM=134`는 emitter 없는 dead 슬롯 — 로그 포맷 bump 시 enum과 함께 정리 예정.

---

## 11. 추천 리뷰 순서

1. **§4 신규 로그타입** — 파일 5개를 가로지르고 on-disk에 영향을 준다. 여기를 통과하면 나머지가 쉬워진다.
2. **§7-1 rcvindex 게이트** — admit/exclude 규칙이 정확성의 심장. 이중 삭제/누락 여부를 본다.
3. **§6 REMOVE sysop 묶기** — 원자성(크래시 시 dangling OOS) 경계.
4. **§7-4 undo snapshot** — 버퍼 회전이라는 비직관적 버그 방지.
5. **§5 eager + abort 계약** — 단순하지만 트랜잭션 계약이 중요하다.
6. **§8 버그픽스** — spin-loop와 stats는 독립적으로 검증 가능.
7. **§9 테스트 (선택적/optional)** — 필수 아님. 위 주장들을 실제로 묶어주는 E2E 시나리오를 근거로 참고. 시간이 빠듯하면 §9-2 핵심 시나리오 4개만 확인하고 넘어가도 된다.

---

*(생성: 리뷰 보조용. 코드가 진실의 원천이며, 인용된 주석/라인은 `git diff origin/feat/oos HEAD` 시점 기준이다.)*
