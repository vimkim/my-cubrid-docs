# CBRD-26668 — OOS Vacuum 회수(Reclamation) 코드 리뷰 가이드

> 대상 diff: `git diff origin/feat/oos HEAD`
> 브랜치: `oos-vacuum` (base: `origin/feat/oos`)
> 작성 목적: 리뷰어가 변경 전체를 **주제 단위**로 빠르게 이해하고, hunk별 의도와 근거를 확인할 수 있도록 한다.
>
> 변경 규모: 26 files, **+4822 / −78**. 단, 이 중 ~3,500줄은 신규 테스트다. 엔진 코드 자체는 ~1,300줄 수준이며 이 문서의 §3~§8이 그 전부를 다룬다.

---

## 0. 한눈에 보기 (Executive Summary)

`feat/oos`는 **OOS(Out-of-row Overflow Storage)** — 큰 컬럼 값을 별도 파일에 저장하고 heap 레코드의 VOT(Variable Offset Table)에 8바이트 OID로 참조하는 기능 — 의 **저장/읽기**까지를 구현했다. 그러나 레코드가 **삭제/갱신**되면 그 레코드가 참조하던 OOS 청크가 **아무도 가리키지 않는 고아(dangling/leaked)** 상태로 남는다.

본 브랜치(CBRD-26668)는 그 누수를 메우는 **OOS 회수(reclamation)** 를 추가한다. 핵심은 **두 개의 회수 경로**다.

| 경로 | 적용 모드 | 시점 | 진입 함수 |
|---|---|---|---|
| **Eager (즉시)** | `!is_mvcc_op` (SA_MODE + MVCC 비활성 카탈로그 클래스) | DELETE/UPDATE 실행 중 | `heap_oos_delete_unreferenced()` |
| **Deferred (지연/vacuum)** | MVCC (SERVER_MODE) | vacuum 수행 시 | `vacuum_heap_oos_delete()` / `vacuum_forward_walk_reclaim_oos()` |

지연 경로는 다시 **두 하위 경로**로 나뉜다.

- **REMOVE 경로**: vacuum이 죽은 슬롯(REC_HOME/REC_RELOCATION)을 물리적으로 제거할 때, 그 슬롯이 가리키던 OOS를 같은 sysop 안에서 인라인 삭제.
- **Forward-walk 경로**: UPDATE/remove-old-forward 처럼 **갱신 후 슬롯이 더 이상 옛 OID를 가리키지 않는** 경우. 옛 OID는 오직 **undo 로그 이미지**에만 남으므로, vacuum이 로그 블록을 훑으며(undo image) 회수한다.

> **읽는 순서 추천**: §1(큰 그림) → §2(모듈 추출 지도) → §4(신규 로그타입, 가장 리뷰 민감) → §5(eager) → §6(REMOVE) → §7(forward-walk) → §8(버그픽스) → §9(테스트).

---

## 1. 큰 그림: 왜 두 경로인가

OOS OID는 **행마다 새로 할당되며 행 간에 절대 공유되지 않는다**(unique per heap record). 이 불변식이 회수 설계 전체의 근거다.

```
                       레코드가 OOS를 참조 (heap recdes VOT에 8B OID + OR_MVCC_FLAG_HAS_OOS)
                                         │
            ┌────────────────────────────┴────────────────────────────┐
            │                                                          │
     !is_mvcc_op (SA / 카탈로그)                              MVCC (SERVER_MODE)
            │                                                          │
   동시 reader 없음 → 바로 삭제해도 안전                  옛 OOS를 reader가 아직 볼 수 있음
            │                                                  → 살려두고 vacuum이 나중에 회수
   heap_oos_delete_unreferenced()                                     │
   (DELETE: 전부 / UPDATE: new에 없는 것만)          ┌─────────────────┴─────────────────┐
                                                  REMOVE 경로                    Forward-walk 경로
                                              (슬롯이 통째로 죽음)          (슬롯은 살아있으나 옛 OID를
                                                     │                       더 이상 가리키지 않음)
                                          vacuum_heap_oos_delete()        vacuum_forward_walk_reclaim_oos()
                                          (REC_HOME 인라인 sysop /         (undo image에서 옛 OID 추출)
                                           REC_RELOCATION forward와 함께)
```

**왜 UPDATE의 옛 OID는 REMOVE 경로로 못 잡는가?**
`heap_attrinfo_insert_to_oos`는 transform마다 **새 OOS OID**를 할당한다. 따라서 UPDATE 직후의 live 슬롯은 **새 OID만** 참조하고, 옛 OID는 **undo 레코드에만** 존재한다. vacuum의 REMOVE 경로(live 슬롯 기준)는 옛 OID에 영영 도달할 수 없다 → **forward-walk가 유일한 회수 수단**이다.

---

## 2. 모듈 추출 지도 (Refactor)

엔진 로직을 `vacuum.c` / `heap_file.c`에서 전용 모듈로 분리했다. 리뷰 시 "어느 파일을 보면 되는가"의 지도:

| 파일 | 신규/수정 | 역할 |
|---|---|---|
| `src/storage/oos_util.{hpp,cpp}` | **신규** | 모듈 무관 헬퍼(`oos_oid_in_vector`) |
| `src/storage/heap_oos.{hpp,cpp}` | 수정(+104) | Eager 경로 `heap_oos_delete_unreferenced` |
| `src/query/vacuum_oos.{hpp,cpp}` | **신규** | 지연 경로 전부(REMOVE 헬퍼 + forward-walk + VFID 캐시) |
| `src/storage/oos_file.{hpp,cpp}` | 수정(+91) | `oos_chunk_exists`(멱등 probe), `oos_get_stats_by_vfid` |
| `src/storage/heap_file.c` | 수정(+158) | Eager 호출 지점 + `heap_log_delete_physical` rcvindex 인자 + 디버그 VOT 검증 |
| `src/query/vacuum.c` | 수정(+131) | 지연 경로 호출 지점 + spin-loop 픽스 |
| `src/transaction/recovery.{h,c}`, `mvcc.h` | 수정 | 신규 로그타입 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM=136` |
| `cubrid/CMakeLists.txt`, `sa/CMakeLists.txt` | 수정 | `vacuum_oos.cpp`, `oos_util.cpp`를 빌드에 추가 |

> **✅ 리뷰 체크리스트 (모듈/빌드)**
> - [ ] `cubrid/`와 `sa/` 두 CMakeLists 모두에 신규 소스가 추가됐는가 (한쪽만 추가하면 SA 또는 SERVER 빌드가 깨짐).

---

## 3. 기반 헬퍼 (base 브랜치에서 가져다 쓰는 것)

본 diff는 `feat/oos`에 이미 있는 다음 헬퍼에 의존한다. 시그니처를 알아두면 hunk 해석이 쉽다.

```c
// src/storage/heap_file.h (base)
extern bool heap_recdes_contains_oos (const RECDES *record);                 // recdes가 OOS 참조 포함?
extern int  heap_recdes_get_oos_oids (const RECDES *record, OID_VECTOR &);   // recdes에서 OOS OID들 추출
extern bool heap_oos_find_vfid (THREAD_ENTRY *, const HFID *, VFID *, bool docreate); // heap→OOS 파일 VFID
using OID_VECTOR = std::vector<OID>;
```

`heap_recdes_contains_oos`는 레코드 MVCC 헤더의 `OR_MVCC_FLAG_HAS_OOS`를 보고 판정한다. **주의**: 이 함수에 OOS 포맷이 아닌 recdes(예: REC_RELOCATION의 8B forwarding OID)를 넣으면 OID의 pageid를 MVCC 헤더로 오해해 **거짓 양성**이 날 수 있다 — §7에서 record-type 가드가 이래서 필요하다.

---

## 4. 신규 로그타입 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` (5개 파일에 걸친 한 가지 변경)

가장 리뷰가 민감한 부분. MVCC 모드에서 `heap_update_relocation`이 옛 forward(REC_NEWHOME) 슬롯을 **물리적으로 삭제**할 때, 그 옛 레코드는 **이 삭제의 undo 이미지에만** 살아남는다(LSA가 새 버전의 `prev_version_lsa`가 됨). 이 옛 forward가 OOS를 참조했다면 forward-walk가 회수해야 하는데, vacuum이 그 로그 레코드를 "회수 대상"으로 식별하려면 **전용 rcvindex 태그**가 필요하다.

### 4-0. 왜 새 타입이 필요한가 (직관)

> **흔한 오해**: "`RVHF_DELETE`도 어차피 OOS를 검사해서 OID 따라가 회수하지 않나? 왜 새 타입을 만드나?"

핵심은 **회수의 분기점이 rcvindex가 아니라 "OOS를 가리키는 슬롯이 아직 살아 있는가"** 라는 점이다. 회수 경로가 둘인 이유가 여기서 갈린다.

| | 슬롯 상태 | 회수 주체 | OOS를 어디서 읽나 |
|---|---|---|---|
| **REMOVE 경로** | 죽었지만 **아직 존재** | `vacuum_heap_record` | **살아있는 슬롯의 recdes** |
| **Forward-walk 경로** | **물리적으로 사라짐** | `vacuum_forward_walk_reclaim_oos` | **delete 로그의 undo 이미지** |

당신이 떠올린 "OOS 검사 후 OID 따라가 회수"는 **REMOVE 경로**가 하는 일이고, 그건 **읽을 슬롯이 남아 있을 때만** 가능하다. 평범한 `RVHF_DELETE`가 회수를 트리거하는 게 아니다 — vacuum이 죽은 슬롯을 지우면서 그 슬롯을 읽어 회수하는 것뿐이다.

**문제의 시나리오 — REC_NEWHOME 재배치:**

```
[UPDATE 전]
HOME ──(REC_RELOCATION)──▶ forward 슬롯 (REC_NEWHOME, 데이터 + OOS 포인터) ──▶ OOS 파일의 큰 값

[UPDATE 중: remove_old_forward = 옛 forward 슬롯을 "물리 삭제"]
   옛 REC_NEWHOME 슬롯이 heap에서 사라짐
   → 그 OOS를 가리키는 살아있는 슬롯이 0개
   → OOS OID는 오직 이 delete 로그의 undo 이미지에만 남음  (heap_file.c:23684-23695)
```

이 순간 REMOVE 경로는 **읽을 슬롯이 없어서** 이 OOS에 영원히 못 닿는다. 유일한 회수 수단은 delete 로그의 undo 이미지를 보는 forward-walk다. 그래서 emitter가 **"OOS 달린 REC_NEWHOME forward를 MVCC로 삭제하는" 정확히 그 케이스만** 새 태그로 표시한다 (`heap_file.c:23690`):

```c
LOG_RCVINDEX delete_rcvindex = RVHF_DELETE;
if (is_mvcc_op && forward_recdes.type == REC_NEWHOME
    && heap_recdes_contains_oos (&forward_recdes))        // OOS 달린 forward 삭제일 때만
  {
    delete_rcvindex = RVHF_DELETE_NEWHOME_NOTIFY_VACUUM;   // ← vacuum아, 이건 forward-walk 해라
  }
```

**"그럼 모든 `RVHF_DELETE`를 forward-walk하면 되잖아?" → double-delete 때문에 안 된다.**

논리적 MVCC DELETE(`RVHF_MVCC_DELETE_MODIFY_HOME`)는 슬롯이 **살아남고 같은 OOS OID를 그대로 가리킨다**. 이 경우는 REMOVE 경로가 회수한다. 여기에 forward-walk까지 돌리면 **같은 OID를 두 번 삭제**해 `oos_delete_chain`의 `S_DOESNT_EXIST` assert가 터진다(vacuum.c:3546-3550). 따라서 게이트는 넓히는 게 아니라 **REMOVE가 구조적으로 못 닿는 한 케이스로 정확히 좁히는** 방향으로 설계됐다.

| delete 종류 | 슬롯 생존 | 회수 담당 | forward-walk 하면? |
|---|---|---|---|
| 논리적 MVCC DELETE | 살아남음(recdes 동일) | REMOVE 경로 | 💥 double-delete |
| UPDATE 재배치의 옛 forward 물리삭제 | **사라짐** | **forward-walk** | ✅ 유일한 회수 수단 |

> **요약**: 새 타입은 "`RVHF_DELETE`가 못 하는 일"을 위해서가 아니라, **REMOVE 경로가 닿을 수 없는 고아 OOS를 double-delete 없이 정확히 그 케이스만 forward-walk로 라우팅**하기 위한 의미 태그다. 복구 동작은 `RVHF_DELETE`와 동일하다(§4-2).

### 4-1. `recovery.h` — enum 슬롯 136 (on-disk 고정)

```c
  RVHF_DELETE_NEWHOME_NOTIFY_VACUUM = 136,
  RV_LAST_LOGID = RVHF_DELETE_NEWHOME_NOTIFY_VACUUM,
```

- **append-only, 절대 재번호 금지**: `RV_fun[]`(recovery.c)은 rcvindex로 **위치 인덱싱**된다. 중간 값을 바꾸면 뒤 슬롯이 전부 밀린다.
- 기존 `RVOOS_NOTIFY_VACUUM = 134`에는 **emitter가 없다**(미사용). 그러나 on-disk 로그가 이 값을 참조할 수 있어 134에 **핀 고정**하고, 관련 `TODO` 주석을 enum/매크로 양쪽에 남겼다 — 로그 포맷 bump 시 함께 정리.

### 4-2. `recovery.c` — `RV_fun[]` 핸들러 행

```c
  {RVHF_DELETE_NEWHOME_NOTIFY_VACUUM,
   "RVHF_DELETE_NEWHOME_NOTIFY_VACUUM",
   heap_rv_undo_delete,   // ← RVHF_DELETE와 동일
   heap_rv_redo_delete,   // ← RVHF_DELETE와 동일
   log_rv_dump_hexa, log_rv_dump_hexa}
```

- **크래시 복구는 평범한 RVHF_DELETE와 100% 동일하게 replay** 한다. OOS 회수는 redo/undo의 일부가 **아니라** vacuum-time에 undo 이미지를 보고 하는 **추가 동작**이다. 따라서 핸들러는 반드시 `RVHF_DELETE`의 것을 그대로 미러링.
- 134 슬롯도 `vacuum_rv_es_nop` no-op 스텁으로 유지(위치 인덱싱 보존).

### 4-3. `mvcc.h` — MVCC op으로 분류, 단 heap op은 아님

```c
#define LOG_IS_MVCC_OPERATION(rcvindex) \
  (LOG_IS_MVCC_HEAP_OPERATION (rcvindex) \
   || LOG_IS_MVCC_BTREE_OPERATION (rcvindex) \
   || ((rcvindex) == RVES_NOTIFY_VACUUM) \
   || ((rcvindex) == RVOOS_NOTIFY_VACUUM) \
   || ((rcvindex) == RVHF_DELETE_NEWHOME_NOTIFY_VACUUM))
```

- **분류 의도(미묘함)**: 새 타입은 `LOG_IS_MVCC_OPERATION`(undo가 MVCC undo로 체이닝되어 forward-walk가 따라갈 수 있게) 이지만, `LOG_IS_MVCC_HEAP_OPERATION`은 **아니다**(슬롯은 이미 물리 삭제됐으므로 vacuum이 "collect" 하면 안 됨). 이 구분이 §7의 `vacuum_process_log_block` 분기에서 결정적.

### 4-4. `heap_file.c` — emitter (`heap_update_relocation`)

```c
LOG_RCVINDEX delete_rcvindex = RVHF_DELETE;
if (is_mvcc_op && forward_recdes.type == REC_NEWHOME && heap_recdes_contains_oos (&forward_recdes))
  {
    delete_rcvindex = RVHF_DELETE_NEWHOME_NOTIFY_VACUUM;
  }
heap_log_delete_physical (..., &forward_recdes, true, &prev_version_lsa, delete_rcvindex);
```

- OOS를 가진 MVCC forward 삭제일 때만 새 태그. 그 외(non-OOS, 또는 SA는 §5 eager가 처리)는 평범한 `RVHF_DELETE` → **동작 변화 없음**.

### 4-5. `vacuum.c` — consumer (§7에서 상세)

`vacuum_process_log_block`에서 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`을 만나면, **MVCC heap-op 블록 밖에서**(수집할 슬롯 없음) `vacuum_forward_walk_reclaim_oos`를 호출.

> **✅ 리뷰 체크리스트 (로그타입)**
> - [ ] 136이 enum 끝에 append됐고 `RV_LAST_LOGID`가 갱신됐는가.
> - [ ] `RV_fun[]` 행이 위치상 정확히 136에 오는가(134 스텁이 사이에 있음).
> - [ ] 핸들러가 `heap_rv_undo_delete`/`heap_rv_redo_delete`인가(복구 동작 동일).
> - [ ] emitter 가드 `is_mvcc_op && REC_NEWHOME && contains_oos` — 셋 다 필요.
>
> **⚠️ 리스크**
> - rcvindex 134/136은 **on-disk 고정값**. 재번호 시 기존 로그/복구가 깨짐.
> - 새 타입을 `LOG_IS_MVCC_HEAP_OPERATION`에 넣으면 vacuum이 이미 삭제된 슬롯을 collect 시도 → 회귀.

---

## 5. Eager 경로 (`!is_mvcc_op`)

동시 reader가 없는 SA_MODE / MVCC 비활성 카탈로그 클래스에서는 DELETE/UPDATE 실행 중 옛 OOS를 **즉시** 삭제한다(이 모드엔 vacuum이 없으므로 여기서 안 하면 영영 누수).

### 5-1. `heap_oos.cpp` — `heap_oos_delete_unreferenced()` (핵심 신규 함수)

시그니처: `(context, old_recdes, new_recdes, op_ctx)` →
`old_recdes`가 참조하지만 `new_recdes`는 참조하지 않는 OOS OID를 삭제.

- `new_recdes == NULL` (DELETE): **old의 모든 OOS OID를 무조건 삭제** — OOS OID는 행 간 비공유라 안전.
- `new_recdes != NULL` (UPDATE): old와 new에 **둘 다 있는** OID(= 물리적으로 동일 OOS를 갱신 전후로 참조)는 **보존**, old에만 있는 것만 삭제. 이 교집합 판정에 `oos_util.cpp`의 `oos_oid_in_vector`를 사용.
- **엄격 실패 처리**: 여기서 OOS 파일/추출 실패는 진짜 손상이므로 `assert_release` 후 에러 전파.
- **호출자 계약(중요)**: 에러 시 **반드시 트랜잭션 abort**. `oos_delete`의 청크별 undo 레코드가 rollback 때 부분 삭제를 replay해야, 살아남은 recdes가 이미 삭제된 청크를 가리키는 불일치를 막는다.
- 진단 태그가 "SA_MODE"라 적혀 있으나, 주석대로 `!is_mvcc_op`는 SERVER_MODE의 MVCC-비활성 클래스(카탈로그)에서도 fire → 서버에서도 실행될 수 있음.

### 5-2. `heap_file.c` — eager 호출 4개 지점

`heap_recdes_contains_oos`로 가드한 뒤 호출. REC_RELOCATION의 경우 데이터(와 OOS)가 forward 페이지에 있으므로 **forward(REC_NEWHOME) recdes를 old로** 넘긴다(home 슬롯은 8B 포인터뿐).

| 함수 | old_recdes | new_recdes | 가드 |
|---|---|---|---|
| `heap_delete_home` | `home_recdes` | NULL | `record_type==REC_HOME` |
| `heap_delete_relocation` | `forward_recdes` | NULL | `forward_recdes.type==REC_NEWHOME` |
| `heap_update_home` | `home_recdes` | `recdes_p` | `home_recdes.type==REC_HOME` |
| `heap_update_relocation` | `forward_recdes` | `recdes_p` | `forward_recdes.type==REC_NEWHOME` |

물리 삭제(파괴적) **이전에** 호출돼야 OOS OID를 읽을 수 있음에 유의(코드 배치가 그렇게 돼 있음).

### 5-3. `heap_log_delete_physical` 시그니처 변경

```c
-  ..., bool mark_reusable, LOG_LSA *undo_lsa);
+  ..., bool mark_reusable, LOG_LSA *undo_lsa, LOG_RCVINDEX rcvindex);
```

- 내부 `log_append_undoredo_recdes(thread_p, RVHF_DELETE, ...)` → `(..., rcvindex, ...)`로 일반화.
- 기존 호출처(`heap_delete_bigone`, `heap_delete_relocation`, `heap_delete_home`)는 모두 `RVHF_DELETE`를 명시 전달 → **동작 변화 없음**. 오직 §4-4의 한 호출만 새 태그 전달.

> **✅ 리뷰 체크리스트 (eager)**
> - [ ] 4개 호출 모두 **물리 삭제 이전**에 위치하는가.
> - [ ] REC_RELOCATION 경로가 home이 아닌 **forward** recdes를 넘기는가.
> - [ ] UPDATE 경로가 `new_recdes`로 `context->recdes_p`(새 이미지)를 넘겨 교집합 보존이 동작하는가.
> - [ ] 에러 반환 시 호출 스택이 트랜잭션 abort로 이어지는가(`ASSERT_ERROR();` + return → 상위에서 abort).
>
> **⚠️ 리스크 / 발견사항**
> - `heap_update_relocation`의 MVCC 두 하위 경로는 **모두 forward-walk로 커버된다**: ① update_old_forward(forward 슬롯 제자리 갱신) → `RVHF_UPDATE_NOTIFY_VACUUM`, ② remove_old_forward(forward 슬롯 삭제) → `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`.
> - **⚑ 소스 주석 stale 발견 → ✅ 본 브랜치에서 수정 완료**: `heap_update_relocation` 함수 상단 주석(line ~23521)이 원래 "remove_old_forward MVCC sub-paths still leak OOS until the forward-walk gate is extended... — separate follow-up"라고 잘못 적혀 있었다. 그러나 이후 커밋의 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` 경로가 이미 회수하고 있어(`vacuum.c`의 `else if (rcvindex == RVHF_DELETE_NEWHOME_NOTIFY_VACUUM)` 분기: "remove_old_forward... its OOS records are reclaimed here") 코드와 모순이었다. **해당 주석을 "두 MVCC 하위 경로 모두 forward-walk로 회수됨"으로 갱신 완료.**

---

## 6. 지연 경로 ① REMOVE (`vacuum.c` + `vacuum_oos.cpp`)

vacuum이 죽은 슬롯을 물리 제거할 때, 그 슬롯이 가리키던 OOS를 **같은 sysop 경계 안에서** 삭제한다.

```
vacuum_heap_record (REC_HOME with OOS)
  ├─ log_sysop_start                       ← multi-page 연산이므로 단일 sysop로 묶음
  ├─ spage_vacuum_slot (슬롯 비우기)
  ├─ vacuum_heap_record_remove_oos_inline
  │     ├─ vacuum_log_redoundo_vacuum_record   (heap 슬롯 제거 로그)
  │     └─ vacuum_heap_oos_delete              (OOS 청크 삭제)
  │           └─ 실패 → log_sysop_abort, return
  └─ log_sysop_commit                      ← heap 슬롯 제거 + OOS 삭제가 원자적
```

> **⚠️ 왜 sysop이 꼭 필요한가 (코드 검증 완료 — 제거하면 안 됨)**
> 흔한 의문: "redo 로그가 남으니 sysop 없어도 복구가 알아서 처리하지 않나?" → **아니다.**
> - 이 연산은 **heap home 페이지 + OOS chunk 페이지(들)** 라는 **2개 이상의 페이지**를 수정한다. 단일 WAL 레코드는 *페이지 하나*에 대해서만 원자적이라, 멀티 페이지 묶음의 원자성은 sysop 없이 보장되지 않는다.
> - **vacuum worker에는 user-transaction commit/abort 경계가 없다.** 복구 undo 단계는 `logtb_is_system_worker_tranid`로 **미완료 vacuum worker txn을 undo 대상에 포함**한다(`log_recovery.c:4596`). sysop을 빼면 이 멀티 페이지 작업을 "묶어서 영속화할 수단 자체가 사라진다".
> - sysop commit 레코드(`LOG_SYSOP_END_COMMIT`)가 디스크에 도달해야만 그 안의 변경이 영구화된다. 도달 전 크래시 시 복구는 `lastparent_lsa`로 점프해(`log_manager.c:7954`) sysop 내부를 **전부 undo**한다 → **all-or-nothing 경계는 오직 sysop만 제공**한다.
> - 제거 시 부분 크래시에서 heap slot redo는 영속화되는데 OOS 삭제는 사라져 → **영구 dangling OOS leak**(slot이 사라지면 그 OOS를 재회수할 트리거가 영영 없음). `vacuum.c:2404` 주석이 경고하는 상황.
> - **선례**: REC_RELOCATION / REC_BIGONE도 OOS 이전부터 동일한 멀티 페이지 sysop 패턴 사용(`vacuum.c:2453,2534,2573`). OOS는 새 발명이 아니라 기존 패턴을 따른 것.

### 6-1. `vacuum_heap_helper`에 `oos_vfid` 필드 추가

```c
  VFID overflow_vfid;
+ VFID oos_vfid;          /* OOS file identifier (if any). */
```

`vacuum_heap_page` 진입 시 `VFID_SET_NULL(&helper.oos_vfid)`로 초기화.

### 6-2. prepare 단계에서 OOS VFID 지연 조회

`vacuum_heap_prepare_record`의 REC_HOME / REC_RELOCATION 케이스에서 `vacuum_oos_find_vfid_for_heap_record(...)` 호출로 `helper->oos_vfid`를 채운다.

### 6-3. `vacuum_heap_record` — `has_oos` 판정과 sysop 묶기

```c
bool has_oos = (!VFID_ISNULL (&helper->oos_vfid)
                && (helper->record_type == REC_HOME || helper->record_type == REC_RELOCATION)
                && heap_recdes_contains_oos (&helper->record));

if (record_type == REC_RELOCATION || record_type == REC_BIGONE || has_oos)
  { vacuum_heap_page_log_and_reset (...); log_sysop_start (...); }
```

- **REC_HOME + OOS** 도 이제 multi-page 연산으로 취급 → 기존 누적된 bulk vacuum 슬롯을 flush하고 단독 sysop 시작. 이렇게 안 하면 heap 슬롯 제거 로그와 OOS 삭제가 서로 다른 sysop로 쪼개져, 둘 사이 크래시 시 **dangling OOS** 발생.
- REC_HOME 분기: `has_oos`면 `vacuum_heap_record_remove_oos_inline`, 아니면 기존대로 `n_bulk_vacuumed++`.
- REC_RELOCATION 분기: forward 페이지 비운 뒤, commit **직전** `has_oos`면 `vacuum_heap_oos_delete` 호출.

### 6-4. `vacuum_heap_record_remove_oos_inline()` (신규 헬퍼)

REC_HOME 전용. `pgbuf_set_dirty` → `vacuum_log_redoundo_vacuum_record` → `vacuum_heap_oos_delete` → 성공 시 `log_sysop_commit`, 실패 시 `log_sysop_abort`. **호출자는 sysop을 이미 연 상태이고 슬롯도 `spage_vacuum_slot`로 비운 상태여야 함**(주석 계약).

### 6-5. REC_BIGONE 불변식 assert (2곳)

```c
/* Invariant: OOS does not coexist with REC_BIGONE. */
assert (!(MVCC_GET_FLAG (&helper->mvcc_header) & OR_MVCC_FLAG_HAS_OOS));
```

- REC_BIGONE은 본문이 overflow 페이지에 있어 `helper->record`가 **채워지지 않는다**. 그래서 OOS 플래그를 `helper->record`가 아니라 **`helper->mvcc_header`** 에서 읽어야 한다(잘못 dereference 방지).
- 현재 OOS는 REC_BIGONE과 공존하지 않는다는 가정. 만약 fire하면 REMOVE 경로에 overflow OOS 회수 루프를 추가해야 한다는 신호 → 디버그에서 loud fail.

> **✅ 리뷰 체크리스트 (REMOVE)**
> - [ ] `has_oos` 3-조건(VFID non-null && REC_HOME|REC_RELOCATION && contains_oos)이 모두 필요한가.
> - [ ] REC_HOME+OOS가 sysop 분기 조건에 포함돼 bulk 슬롯이 먼저 flush되는가.
> - [ ] inline 헬퍼의 commit/abort가 모든 경로에서 정확히 한 번 짝 맞는가.
> - [ ] REC_BIGONE assert가 `mvcc_header` 기준인가(`record` 아님).

---

## 7. 지연 경로 ② Forward-walk (`vacuum.c` + `vacuum_oos.cpp`)

가장 정교한 부분. UPDATE/remove-old-forward에서 옛 OOS OID는 **live 슬롯에 없고 undo 이미지에만** 있다. vacuum이 로그 블록을 훑으며 undo 이미지를 파싱해 회수한다.

```
heap_update_relocation / heap_update_home  (MVCC)
  └─ log RVHF_UPDATE_NOTIFY_VACUUM  (undo = 옛 REC_HOME/REC_NEWHOME, OOS 포함)
        │   또는 RVHF_DELETE_NEWHOME_NOTIFY_VACUUM (remove_old_forward)
        ▼  (나중에, vacuum worker)
  vacuum_process_log_block
   ├─ (rcvindex == RVHF_UPDATE_NOTIFY_VACUUM)            ← MVCC heap-op 블록 안
   │     └─ vacuum_forward_walk_reclaim_oos(...)
   └─ (rcvindex == RVHF_DELETE_NEWHOME_NOTIFY_VACUUM)    ← MVCC heap-op 블록 밖 (수집할 슬롯 없음)
         └─ vacuum_forward_walk_reclaim_oos(...)
               ├─ undo image를 private buffer로 snapshot   ← 로그 페이지 회전 대비 (필수)
               ├─ vacuum_oos_vfid_cache_lookup            ← heap VFID → OOS VFID (per-block 캐시)
               ├─ heap_recdes_get_oos_oids                ← undo recdes에서 옛 OID 추출
               └─ vacuum_forward_walk_delete_old_oos      ← 정렬 + 멱등 probe + sysop 삭제
```

### 7-1. `vacuum_process_log_block` — rcvindex 게이트 (★ 가장 리뷰 민감)

```c
if (log_record_data.rcvindex == RVHF_UPDATE_NOTIFY_VACUUM)
  { vacuum_forward_walk_reclaim_oos (...); }
```

주석이 길게 설명하는 **admit/exclude 규칙**:

- **admit `RVHF_UPDATE_NOTIFY_VACUUM`**: UPDATE는 transform마다 새 OID 할당 → undo의 옛 OID는 live와 disjoint. forward-walk만이 회수 가능.
- **exclude `RVHF_MVCC_DELETE_MODIFY_HOME`**: 논리 DELETE는 recdes 내용을 그대로 두고 `delete_mvccid`만 바꾼다. 삭제 후 슬롯이 **동일 OID**를 계속 참조 → REMOVE 경로가 회수. forward-walk까지 돌리면 **이중 삭제**로 `oos_delete_chain`의 `S_DOESNT_EXIST` assert를 친다. **이 rcvindex 게이트가 그 배제를 떠받치는 load-bearing 라인**이다.
- INSERT/DELETE_REC_HOME/NO_MODIFY_HOME/REDISTRIBUTE는 undo에 pre-image recdes가 없어 `undo_data_size > sizeof(INT16)` 조건으로 자연 필터됨.

별도로 MVCC heap-op 블록 **밖**에서 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`도 같은 헬퍼 호출(§4-5). 의도적으로 밖에 둔 이유: 슬롯이 이미 물리 삭제돼 collect할 게 없음.

### 7-2. `vacuum_process_log_record` — undo unpack 게이트 확장

```c
if (!LOG_IS_MVCC_BTREE_OPERATION (...)
    && rcvindex != RVHF_UPDATE_NOTIFY_VACUUM
    && rcvindex != RVES_NOTIFY_VACUUM
    && rcvindex != RVHF_DELETE_NEWHOME_NOTIFY_VACUUM)
  { return NO_ERROR; /* undo unpack 불필요 */ }
```

forward-walk가 undo 이미지를 봐야 하므로, 두 신규 rcvindex에 대해 undo unpack을 **켜준다**. 안 켜면 `undo_data`가 NULL이라 회수가 조용히 누락됨.

### 7-3. `vacuum_oos.cpp` — VFID 캐시 (`VACUUM_OOS_VFID_CACHE`)

- heap VFID → OOS VFID 매핑을 **블록 단위**로 캐싱(`file_descriptor_get` + `heap_oos_find_vfid` 반복 회피). 16-엔트리 라운드로빈.
- **`VFID_NULL` 음성 sentinel**: "이 heap엔 OOS 파일 없음"을 캐시 → non-OOS heap이 반복 조회를 건너뜀.
- **tri-state 결과** `FOUND / NONE / ERROR`: transient 실패(`file_descriptor_get` 실패 등)는 **캐시하지 않는다** — 잘못 캐시된 `VFID_NULL`은 그 블록의 이후 모든 레코드 회수를 건너뛰게 만들기 때문(poison). 오직 "정당하게 OOS 없음"(false 반환 + 에러 없음)만 캐시.
- **스레드 안전**: `vacuum_process_log_block` 스택에 선언 → per-worker-per-block. **static으로 바꾸면 worker 간 레이스** (주석 경고).

### 7-4. `vacuum_forward_walk_reclaim_oos` — undo image snapshot (미묘한 버그 방지)

```c
RECDES parse_recdes = undo_recdes;
char *stable_copy = db_private_alloc (thread_p, undo_recdes.length);
memcpy (stable_copy, undo_recdes.data, undo_recdes.length);
parse_recdes.data = stable_copy;
```

- undo 이미지는 보통 worker의 **현재 로그 페이지 버퍼**를 직접 가리킨다. 이후 `vacuum_oos_vfid_cache_lookup` 안의 page fix가 로그 활동을 유발해 그 버퍼를 **회전**시킬 수 있다 → 회전 후 파싱하면 0/foreign 바이트를 읽어 **조용히 아무것도 추출 못 함**(실측: flags 워드가 0x69→0x00). 그래서 **page fix 이전에** private buffer로 복사.
- 부수효과로 **정렬도 교정**: 이미지는 `undo_data + sizeof(INT16)`에서 시작해 misaligned → OR_BUF 리더(`or_get_oid`)가 디버그에서 assert. 복사본은 정렬됨.
- **record-type 가드**: `(REC_HOME || REC_NEWHOME) && heap_recdes_contains_oos`만 통과. forwarding 포인터(8B OID)를 `heap_recdes_contains_oos`에 넣으면 pageid의 bit 27이 `OR_MVCC_FLAG_HAS_OOS`로 오인돼 bogus VOT를 walk하다 `assert_release` → §3 경고 참조.

### 7-5. `vacuum_forward_walk_delete_old_oos` — 정렬 + 멱등 probe

```c
std::sort(oos_oids ...);            // (volid,pageid,slotid) 순 → 버퍼 풀 locality
log_sysop_start;
for (oid : oos_oids) {
   oos_chunk_exists(oid, &exists);  // ← 멱등성: 블록 재시도 대비
   if (!exists) continue;           //    이미 사라진 청크는 skip (S_DOESNT_EXIST assert 회피)
   oos_delete(oos_vfid, oid);
}
log_sysop_commit / abort;
```

- **OID를 값으로(by-value vector) 받는다**: `oos_delete`가 undo_data가 가리키던 로그 페이지를 회전시킬 수 있으므로, 호출자가 self-owned 벡터를 `std::move`로 넘긴 뒤 그 위에서 정렬/삭제.
- **멱등성**: 블록 재시도 시, 같은 블록의 앞선 forward-walk가 이미 sysop commit했을 수 있다. 그 OID의 청크는 이미 물리적으로 사라졌으므로 `oos_chunk_exists`로 skip — `oos_delete_chain`의 `S_DOESNT_EXIST` hard error 회피. **진짜 probe 실패(I/O 등)는 전파**.

### 7-6. 실패 정책: bounded, logged leak (전체 forward-walk 공통)

`vacuum_forward_walk_reclaim_oos`의 모든 실패(VFID lookup ERROR, alloc 실패, delete 실패)는 **에러를 전파하지 않는다**. 대신 `vacuum_er_log_error`로 loud 로깅 후 `er_clear`하고 반환. 이유: forward-walk 실패로 블록을 fail시키면 `vacuum_finished_block_vacuum`의 shutdown-only assert를 쳐서 **vacuum이 wedge**될 위험. 누수는 bounded(해당 레코드의 OOS 청크들)이고 로그로 추적 가능.

### 7-7. `vacuum_oos_find_vfid_for_heap_record` (REMOVE 경로용 lazy lookup, §6에서 사용)

레코드가 HAS_OOS 플래그를 갖는데 OOS 파일을 못 찾는 경우: 이는 lazy-creation 아티팩트가 아니라(파일은 청크 쓸 때 `docreate=true`로 먼저 생성됨) **거짓 플래그/드롭된 파일/복구 순서 edge**를 의미. **디버그는 `assert_release`로 즉시 fail**(플래그 심는 버그를 첫 vacuum에서 포착), **릴리스는 log + er_clear + skip**(bounded leak). 여기서 `ER_FAILED`를 반환하면 `vacuum_heap_page` 루프의 release-only spin(§8-1)이 재무장되므로 절대 에러 반환 안 함.

> **✅ 리뷰 체크리스트 (forward-walk)**
> - [ ] rcvindex 게이트가 `RVHF_UPDATE_NOTIFY_VACUUM`만 admit하고 `RVHF_MVCC_DELETE_MODIFY_HOME`을 **배제**하는가(이중 삭제 방지).
> - [ ] `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`이 MVCC heap-op 블록 **밖**에서 처리되는가.
> - [ ] §7-2 undo unpack 게이트에 두 신규 rcvindex가 추가됐는가(빠지면 회수 조용히 누락).
> - [ ] page fix **이전에** undo image를 snapshot하는가(버퍼 회전 버그).
> - [ ] record-type 가드(REC_HOME/REC_NEWHOME)가 contains_oos 앞에 있는가(거짓 양성 assert).
> - [ ] VFID 캐시가 stack-local(per-block)인가 — static 금지.
> - [ ] 모든 실패가 bounded-leak로 degrade하고 블록을 fail시키지 않는가.

---

## 8. 버그픽스 (회수와 직접 연관된 안정화)

### 8-1. `vacuum.c` — release-only spin-loop 픽스 (★ 중요)

```c
      er_clear ();
      error_code = NO_ERROR;
+     // for-header에 증가식이 없다 — page_ptr은 성공 경로에서만 전진한다.
+     // 여기서 bare continue는 같은 page_ptr을 영원히 재시도 (release CPU spin).
+     page_ptr = obj_ptr;
      continue;
```

- `vacuum_heap_page`의 for 루프는 헤더에 증가식이 없고 성공 경로에서만 `page_ptr`이 전진한다. 릴리스 빌드에서 에러를 삼키고 `continue`하면 **같은 페이지를 무한 재시도**하는 CPU spin(이전 PR 6986에서 관측된 회귀). `page_ptr = obj_ptr`로 다음 페이지 그룹으로 강제 전진 → 영구 실패 페이지를 skip. forward-walk/VFID-lookup이 절대 에러를 전파하지 않는 설계(§7-6,7-7)와 짝을 이룬다.

### 8-2. `oos_file.cpp` — `oos_get_stats_by_vfid` 추출 + slot-0 언더카운트 픽스

```c
- spage_collect_statistics (page_ptr, ...);   // slot 0을 건너뜀(heap 페이지 가정)
+ PGSLOTID slotid = -1;  RECDES slot_recdes;
+ while (spage_next_record (page_ptr, &slotid, &slot_recdes, PEEK) == S_SUCCESS)
+   { total_recs++; total_sumlen += slot_recdes.length; }
```

- `xoos_get_stats_by_class_oid`의 코어를 `oos_get_stats_by_vfid`로 추출(카탈로그에 안 붙은 OOS 파일 — 유닛테스트 heap — 에도 사용 가능). 테스트가 OOS 통계를 VFID로 직접 검증할 수 있게 하는 **테스트 가능성** 변경.
- **버그**: `spage_collect_statistics`는 slot 0을 heap 헤더로 가정해 건너뛴다. 그러나 OOS 데이터 페이지는 slot 0부터 레코드를 둔다 → **페이지당 1 레코드 언더카운트**. `spage_next_record`로 명시적 walk해 교정.

### 8-3. `oos_file.cpp` — `oos_chunk_exists` (멱등 probe, §7-5에서 사용)

`oos_delete`의 read-only 동반자. "이미 사라짐"을 좁게 정의: (a) `pgbuf_fix_if_not_deallocated`가 NO_ERROR + page==NULL(페이지 deallocated), 또는 (b) `spage_get_record`가 `S_DOESNT_EXIST`(슬롯 제거됨). **그 외 모든 실패(진짜 I/O 에러, S_ERROR)는 전파** — 호출자가 "gone"으로 오인하면 안 됨.

### 8-4. `heap_file.c` — `heap_recdes_compute_oos_flag_debug` VOT 검증 강화 (디버그 전용)

- 클래스/루트 레코드는 내부 포맷이 달라 VOT로 해석하면 garbage. 루프 전 가드에서 **첫 VOT 엔트리가 합리적 offset인지**(`[0, length - header_size]`) 검사하고, offset 기준을 **end-of-header 상대**(기존 `recdes->length`는 버그, `header_size`를 빼야 함)로 교정.
- 루프 로직 재구성: `has_oos` 누적 후 `LAST_ELEMENT`에서 결과 반환. `LAST_ELEMENT`가 없으면(구포맷 VOT) 홀수 offset의 거짓 양성을 막기 위해 `false`. **디버그 전용**(`#if !defined(NDEBUG)`)이라 런타임 영향 없음.

> **✅ 리뷰 체크리스트 (버그픽스)**
> - [ ] spin-loop 픽스: `page_ptr = obj_ptr`가 release-only 경로에만 있고 디버그 경로 의미를 안 바꾸는가.
> - [ ] stats: slot 0 포함이 의도대로이고 기존 `xoos_get_stats_by_class_oid` 호출 결과가 1만큼 늘어나는 게 정상인가(회귀 아닌 교정).
> - [ ] `oos_chunk_exists`가 "gone"을 좁게만 인정하고 나머지를 전파하는가.

---

## 9. 테스트 커버리지

### 9-1. 신규 테스트 파일 지도

| 테스트 파일 (줄수) | Fixture | 검증 대상 | 경로 |
|---|---|---|---|
| `test_oos_server.cpp` (471) | `OosVacuumCodePathServer` | `heap_recdes_contains_oos`, `heap_recdes_get_oos_oids`, `vacuum_heap_oos_delete` 직접 단위 + bulk reclaim | deferred(헬퍼) |
| `test_oos_vacuum_server.cpp` (656) | `OosVacuumServer` | REMOVE 경로: insert/delete, multi-chunk, large multi-page, MVCC update, bulk reclaim+reuse, churn | deferred(REMOVE) |
| `test_oos_real_vacuum_server.cpp` (509) | `OosRealVacuum` | **실제 vacuum 데몬 E2E**: single-row drain, multi-chunk chain drain, update stale 회수+new 생존, snapshot이 회수 차단 후 drain | deferred(E2E) |
| `test_oos_mock_vacuum_server.cpp` (417) | (mock) | forward-walk 로직을 데몬 없이 단위 검증 | deferred(forward-walk) |
| `test_oos_delete_server.cpp` (390) | `OosDeleteServerTest` | SERVER 모드 DELETE 즉시 회수, multi-chunk, update pattern, free space 복원, 160KB | eager/REMOVE |
| `test_oos_remove_file_server.cpp` (202) | `OosFileDestroyServerTest` | OOS 파일/페이지 destroy, 캐시 클리어, 다중 파일 | 파일 수명 |
| `test_oos_sql_eager_cleanup.cpp` (720) | (SQL) | SQL 레벨 eager cleanup(SA) 종단 검증 | eager |
| `test_oos_server_common.hpp` (269) | — | SERVER 모드 공용 fixture(부팅/통계 헬퍼) | — |

### 9-2. 핵심 시나리오 (리뷰 시 꼭 볼 것)

- **`OosRealVacuum.UpdateStaleVersionDrainsNewSurvives`**: forward-walk 정확성의 핵심. UPDATE 후 옛 OOS는 drain되고 **새 OOS는 생존**해야 함 — §7 admit/exclude 규칙의 살아있는 검증.
- **`OosRealVacuum.SnapshotBlocksReclaimThenDrains`**: 활성 snapshot이 회수를 막다가(MVCC 가시성) snapshot 해제 후 drain — 지연 회수의 정당성.
- **`OosVacuumServer.BulkVacuumReclaimAndReuse`** / **`MultiUpdateChurnVacuum`**: REMOVE 경로의 sysop 묶기(§6-3)와 free space 재사용.
- **`OosDeleteServerTest.OosUpdatePattern`**: eager UPDATE의 교집합 보존(§5-1) 검증.

### 9-3. CMake/픽스처 변경 (리뷰 시 주의)

- `unit_tests/oos/CMakeLists.txt`: GLOB 자동수집을 **명시적 `SA_MODE_TESTS` / `SERVER_MODE_TESTS` 리스트**로 교체. SERVER 테스트는 `cubrid`+`SERVER_MODE`, SA 테스트는 `cubridsa`+`SA_MODE` 링크. SERVER 테스트는 `RUN_SERIAL TRUE`(in-process 서버 충돌 방지) + TIMEOUT 60/120.
- **`vacuum_log_block_pages=4`** 를 `[@unittestdb]` 섹션에 createdb **전에** 주입(기본 31). real-vacuum 테스트가 로그 블록을 빨리 닫아 회수를 트리거하기 위함. createdb 시 DB에 freeze되므로 순서가 중요. idempotent append, unittestdb에만 scope.

> **✅ 리뷰 체크리스트 (테스트)**
> - [ ] real-vacuum E2E가 실제 데몬을 polling하며 TIMEOUT 120/RUN_SERIAL로 격리되는가.
> - [ ] `vacuum_log_block_pages=4` 주입이 createdb 이전이고 다른 DB에 영향 없는가.
> - [ ] 새 라이선스 헤더가 CUBRID 단독 Apache(2016)인가(테스트 파일 포함).

---

## 10. 핵심 불변식 & 리스크 요약 (consolidated)

| # | 불변식 / 리스크 | 위치 | 깨지면 |
|---|---|---|---|
| 1 | OOS OID는 행 간 비공유, transform마다 새로 할당 | 설계 전제 | eager 무조건 삭제·forward-walk 분리의 근거 붕괴 |
| 2 | rcvindex 134/136은 **on-disk 고정**, append-only | `recovery.h` | 기존 로그/복구 깨짐, `RV_fun[]` 슬롯 밀림 |
| 3 | forward-walk 게이트는 `UPDATE_NOTIFY_VACUUM`만 admit, `MVCC_DELETE_MODIFY_HOME` 배제 | `vacuum.c` §7-1 | 이중 삭제 → `S_DOESNT_EXIST` assert |
| 4 | page fix **이전** undo image snapshot | `vacuum_oos.cpp` §7-4 | 버퍼 회전 → 조용한 회수 누락 |
| 5 | forward-walk/lazy-lookup은 **에러 전파 금지**(bounded leak) | §7-6, §7-7, §8-1 | vacuum wedge / release CPU spin |
| 6 | REC_BIGONE은 OOS와 비공존, 플래그는 `mvcc_header`에서 읽기 | `vacuum.c` §6-5 | 미초기화 `record` dereference |
| 7 | record-type 가드가 `contains_oos` 앞에 | §7-4, §5-2 | forwarding OID 오인 → bogus VOT assert |
| 8 | eager 에러 시 트랜잭션 abort 필수 | `heap_oos.cpp` §5-1 | 살아남은 recdes가 삭제된 청크 참조 |

### 발견된 stale 주석 / 미해결
- **⚑ stale 주석 → ✅ 수정 완료**: `heap_update_relocation` 상단 주석이 remove_old_forward가 여전히 누수한다고 잘못 적혀 있었으나, 이후 추가된 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` 경로가 이미 회수한다(`vacuum.c` else-if 분기). 본 브랜치에서 주석을 "두 MVCC 하위 경로 모두 forward-walk로 회수됨"으로 **갱신 완료**(§5 발견사항 참조).
- `RVOOS_NOTIFY_VACUUM=134`는 emitter 없는 dead 슬롯 — 로그 포맷 bump 시 enum과 함께 정리 예정.

---

## 11. 추천 리뷰 순서

1. **§4 신규 로그타입** — 5파일 교차, on-disk 영향. 여기가 통과하면 나머지가 쉬워진다.
2. **§7-1 rcvindex 게이트** — admit/exclude 규칙이 정확성의 심장. 이중 삭제/누락 여부.
3. **§6 REMOVE sysop 묶기** — 원자성(크래시 시 dangling OOS) 경계.
4. **§7-4 undo snapshot** — 버퍼 회전이라는 비직관적 버그 방지.
5. **§5 eager + abort 계약** — 단순하나 트랜잭션 계약이 중요.
6. **§8 버그픽스** — spin-loop와 stats는 독립적으로 검증 가능.
7. **§9 테스트** — 위 주장들을 실제로 묶어주는 E2E 시나리오 확인.

---

*(생성: 리뷰 보조용. 코드가 진실의 원천이며, 인용된 주석/라인은 `git diff origin/feat/oos HEAD` 시점 기준이다.)*
