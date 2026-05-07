# PR #6986 예상 Q&A — Forward-Walk OOS 정리

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**JIRA:** [CBRD-26668]
**HEAD:** `977cf18a4`
**작성일:** 2026-04-20 (마지막 갱신: 2026-05-08, HEAD `31e6e9dc6` → `977cf18a4`)
**이전 버전과의 관계:** 이 문서는 2026-04-20의 forward-walk 재설계를 반영한 **전면 개정판**이다. 이전 리비전의 Q1-Q14는 다수가 deprecated된 백워드 체인 워커 설계를 전제로 한 답변이었으므로, 설계 변경에 따라 질문과 답변을 재구성했다. 구 설계 기준 답변 중 현재 설계에서도 유효한 것은 업데이트하여 유지하고, 새 질문을 추가했다.

**2026-05-08 갱신 노트:** HEAD `31e6e9dc6` → `977cf18a4`로 이동하면서 다음 정리 커밋들이 반영되었다.

- `fc0e35ced` — **Forward-walk OOS 정리 게이트를 `RVHF_UPDATE_NOTIFY_VACUUM`으로만 제한.** 기존에는 `RVHF_MVCC_DELETE_MODIFY_HOME`까지 처리했으나, DELETE는 슬롯의 recdes 내용을 그대로 두고 `delete_mvccid`만 갱신하므로 vacuum의 REMOVE 경로에서 같은 OID들이 회수된다. forward-walk까지 돌면 double-delete가 일어나 `oos_delete_chain`의 `S_DOESNT_EXIST` assert를 트립시킨다. 이 변화는 Q1, Q3, Q8 본문에 반영됨.
- `8a3d7dbc2` — 작은 헬퍼 추출 + 주석 재배치. `vacuum_ensure_oos_vfid_for_heap_record` → `vacuum_oos_find_vfid_for_heap_record` 이름 변경, `vacuum_forward_walk_delete_old_oos`/`vacuum_heap_record_remove_oos_inline` 도입.
- `00f5a18c2` — (저장소에 부재; 메시지에 언급된 SHA가 갈라져 있음. 정리 항목은 다음 두 커밋에 흡수됨)
- `e158f5177` — 엔진 diff 트리밍. `(INT32)` 중복 캐스트 제거(`heap_recdes_contains_oos`), `VFID_SET_NULL` 중복 초기화 제거(`heap_update_home_delete_replaced_oos`), `vacuum_oos_find_vfid_for_heap_record`의 `rectype_label` 인자 제거.
- `977cf18a4` — `vacuum_forward_walk_delete_old_oos` / `vacuum_heap_record_remove_oos_inline`의 장문 docstring을 줄이고, rcvindex-제외 근거를 호출 지점(`vacuum.c:3674-3689`)에 인라인.
- 그 외: `catalog_class.c`에 `catcls_align_var_data_to_4` 헬퍼 추출 (Q&A 본문과 무관).
- 또한 vacuum.c 경로는 `src/query/vacuum.c`로 통일 (이전 리비전에 `src/transaction/vacuum.c`로 잘못 표기된 경우가 있었음).

이 문서는 `PR-6986-explanation.md`를 먼저 읽은 리뷰어가 떠올릴 기술적 질문과 답변을 정리한다.

---

## 목차

- [Q1. 기존 L1 (UPDATE-drops-all-OOS → DELETE) 누수는 forward-walk 전환으로 어떻게 해결되었나?](#q1-기존-l1-update-drops-all-oos--delete-누수는-forward-walk-전환으로-어떻게-해결되었나)
- [Q2. 왜 `RVVAC_OOS_DELETE` 같은 새 WAL 레코드를 도입하지 않았나?](#q2-왜-rvvac_oos_delete-같은-새-wal-레코드를-도입하지-않았나)
- [Q3. Forward walk가 MVCC 활성 판독자와 경쟁하지 않음을 어떻게 보장하나? 그리고 왜 DELETE rcvindex는 제외되나?](#q3-forward-walk가-mvcc-활성-판독자와-경쟁하지-않음을-어떻게-보장하나-그리고-왜-delete-rcvindex는-제외되나)
- [Q4. Non-OOS 테이블의 vacuum 성능에 미치는 영향은?](#q4-non-oos-테이블의-vacuum-성능에-미치는-영향은)
- [Q5. VFID 캐시가 크기 16으로 충분한가? 일시 실패 시 어떻게 처리하나?](#q5-vfid-캐시가-크기-16으로-충분한가-일시-실패-시-어떻게-처리하나)
- [Q6. Sysop 페어링 불변식이 깨지면 어떻게 되는가?](#q6-sysop-페어링-불변식이-깨지면-어떻게-되는가)
- [Q7. 왜 `vacuum_oos_find_vfid_for_heap_record`는 유지되었나?](#q7-왜-vacuum_oos_find_vfid_for_heap_record는-유지되었나)
- [Q8. Phase 0 I1 감사에서 CONDITIONAL PASS가 나온 의미는?](#q8-phase-0-i1-감사에서-conditional-pass가-나온-의미는)
- [Q9. Bulk 경로와 Sysop 경로가 성능에 어떤 차이가 있나? (구 Q12 업데이트)](#q9-bulk-경로와-sysop-경로가-성능에-어떤-차이가-있나-구-q12-업데이트)
- [Q10. 왜 REC_BIGONE은 OOS 처리가 필요 없나? (구 Q4 유지)](#q10-왜-rec_bigone은-oos-처리가-필요-없나-구-q4-유지)
- [Q11. 왜 OOS를 DELETE 시 즉시 삭제하지 않고 Vacuum에 맡기나? (구 Q5 유지)](#q11-왜-oos를-delete-시-즉시-삭제하지-않고-vacuum에-맡기나-구-q5-유지)
- [Q12. `RVOOS_NOTIFY_VACUUM`이 여전히 필요한가? (구 Q7 업데이트)](#q12-rvoos_notify_vacuum이-여전히-필요한가-구-q7-업데이트)
- [Q13. 서버 crash 후 recovery에서 OOS는 어떻게 처리되나? (구 Q9 업데이트)](#q13-서버-crash-후-recovery에서-oos는-어떻게-처리되나-구-q9-업데이트)
- [Q14. `heap_recdes_get_oos_oids()`는 어떻게 OID를 추출하나? (구 Q10 유지)](#q14-heap_recdes_get_oos_oids는-어떻게-oid를-추출하나-구-q10-유지)
- [Q15. 구 Q14의 DELETE_INSID_PREV_VER 경로는 이제 어떻게 되나?](#q15-구-q14의-delete_insid_prev_ver-경로는-이제-어떻게-되나)

---

## Q1. 기존 L1 (UPDATE-drops-all-OOS → DELETE) 누수는 forward-walk 전환으로 어떻게 해결되었나?

### 질문 상세

이전 리비전의 report.md는 L1을 "머지 블로커"로 지적했다. 시나리오는 다음과 같다.

```sql
INSERT INTO t (id, oos_col) VALUES (1, REPEAT(X'AA', 4096));  -- HAS_OOS=1
UPDATE t SET oos_col = NULL WHERE id = 1;                      -- HAS_OOS=0
DELETE FROM t WHERE id = 1;
```

구 설계에서는 현재 레코드의 HAS_OOS=0이므로 `vacuum_cleanup_prev_version_oos`가 호출자 가드(`!VFID_ISNULL(&helper->oos_vfid)`)에서 차단되어 호출 자체가 이루어지지 않았다. 내부 lazy lookup 로직은 도달 불가능한 dead code였다.

### 답변

**Forward-walk 재설계로 L1은 설계상 소멸했다.**

새 설계에서 prev-version OOS 정리는 `vacuum_heap_record`가 아니라 `vacuum_process_log_block` 내부의 forward walk에서 이루어진다(`src/query/vacuum.c:3674-3718`). 정확히는 `RVHF_UPDATE_NOTIFY_VACUUM` 로그 레코드의 undo payload(=UPDATE의 pre-image heap recdes)만이 forward-walk 대상이다. **DELETE의 undo(`RVHF_MVCC_DELETE_MODIFY_HOME`)는 의도적으로 제외된다** — 자세한 이유는 Q3에서 다룬다.

이 게이트로 인해 동작은 다음과 같다.

- UPDATE 시점의 undo recdes가 v1(HAS_OOS=1, OOS_A 참조)이면 forward walk가 HAS_OOS를 감지하고 OOS_A를 삭제.
- UPDATE-drops-all-OOS 시나리오: v1(HAS_OOS=1) → v2(HAS_OOS=0) → DELETE. v1을 만드는 UPDATE의 후속 UPDATE가 기록한 undo(=v1)의 HAS_OOS=1이므로 OOS_A는 그 시점에 회수된다. v2(HAS_OOS=0)을 보는 후속 DELETE의 undo는 forward-walk에서 무시되지만, v2 자체는 OOS를 참조하지 않으므로 누수가 발생할 게 없다.
- **현재 레코드의 HAS_OOS가 0인지 1인지는 무관**하다. 각 과거 버전의 OOS는 그 다음 UPDATE를 만드는 시점에 기록된 `RVHF_UPDATE_NOTIFY_VACUUM` undo가 vacuum될 때 회수된다. 구 설계의 호출자 가드 조건은 새 설계에는 존재하지 않는다.

핵심 차이를 표로 정리.

| 국면 | 구 설계 | 신 설계 |
|---|---|---|
| 진입 조건 | 현재 레코드 HAS_OOS (`!VFID_ISNULL(&helper->oos_vfid)`) | 각 로그 레코드 undo의 HAS_OOS |
| 체인 순회 | `prev_version_lsa` 따라 LSA chain walk | 없음 — forward log scan이 본질적으로 모든 버전 방문 |
| dead code 위험 | 있음 (L1) | 없음 |

---

## Q2. 왜 `RVVAC_OOS_DELETE` 같은 새 WAL 레코드를 도입하지 않았나?

### 질문 상세

아키텍처 초기 검토에서는 "vacuum이 undo에서 OOS를 지웠다"는 사실을 나타내는 별도 WAL 레코드 타입(`RVVAC_OOS_DELETE`)을 도입하는 안이 논의되었다. 왜 최종적으로 도입하지 않았나?

### 답변

**Double-replay hazard 때문에 거부되었다.**

`oos_delete` → `oos_delete_chain`은 이미 **청크당 `RVOOS_DELETE` undoredo 레코드**를 기록한다. recovery replay가 이 레코드를 보면 `oos_rv_redo_delete`(`src/storage/oos_file.cpp:1853`)가 `spage_delete`를 수행하거나 이미 반영된 경우 idempotent로 동작한다.

만약 추가로 `RVVAC_OOS_DELETE`를 도입하면:

1. Vacuum이 실행 중 `log_sysop_start` → `oos_delete` → N개의 `RVOOS_DELETE` 기록 → `RVVAC_OOS_DELETE` 마커 기록 → `log_sysop_commit`.
2. Crash 후 recovery가 redo pass에서 `RVOOS_DELETE` N개를 replay → 삭제 완료.
3. 이어서 `RVVAC_OOS_DELETE`를 replay하면 **같은 슬롯을 다시 삭제** 시도. 이미 삭제된 슬롯에 대한 delete는 `S_DOESNT_EXIST` 에러 또는 silent no-op을 요구하는데, 이는 `oos_delete_chain`의 정확성 의미론을 약화시킨다.
4. 또한 두 레코드가 "같은 의미를 두 번 로깅"하여 WAL 볼륨이 불필요하게 증가.

결론: 새 WAL 레코드 없이도 **`log_sysop_start` / `log_sysop_commit` 페어가 "여러 청크 삭제를 하나의 원자 단위로" 묶기에 충분**하다. 기존 `RVOOS_DELETE` per-chunk 레코드가 crash 복구에 필요한 모든 정보를 이미 담고 있다. 자세한 논증은 `PR-6986-explanation.md` §6 참조.

---

## Q3. Forward walk가 MVCC 활성 판독자와 경쟁하지 않음을 어떻게 보장하나? 그리고 왜 DELETE rcvindex는 제외되나?

### 질문 상세

Forward walk가 과거 버전의 OOS를 삭제하는 동안 다른 트랜잭션이 해당 OOS를 참조하려고 하면 어떻게 되는가? 그리고 `RVHF_MVCC_DELETE_MODIFY_HOME` undo도 OOS-bearing pre-image를 담을 수 있는데, 왜 forward-walk 게이트는 `RVHF_UPDATE_NOTIFY_VACUUM`만 허용하는가?

### 답변

**두 개의 불변식이 결합하여 MVCC 안전성을 보장한다.** 자세한 논증은 `PR-6986-explanation.md` §8에 있으며, 여기서는 Q&A 형식으로 요약한다.

#### 불변식 1: 임계값 불변식

Vacuum이 블록 진입 시 설정하는 임계값:

```c
MVCCID threshold_mvccid = log_Gl.mvcc_table.get_global_oldest_visible ();   // src/query/vacuum.c:3509
```

그리고 debug assert(`src/query/vacuum.c:3643-3648`)가 블록 내 모든 MVCCID가 이 임계값보다 오래됨을 검증.

Forward walk가 UPDATE 로그 레코드를 만나 그 undo(pre-image)에서 OOS_X를 삭제할 때, 해당 UPDATE의 MVCCID는 threshold보다 오래되었다. 따라서 모든 활성 스냅샷은 post-UPDATE 버전만 본다. **pre-image를 MVCC로 재구성하려는 판독자는 존재할 수 없다.**

#### 불변식 2: OID 분리성 불변식 (UPDATE 한정)

`heap_attrinfo_insert_to_oos`(`src/storage/heap_file.c:12368, 12976`)는 **UPDATE의 매 transform마다 무조건 fresh OOS OID를 할당한다.** UPDATE의 post-image가 참조하는 OOS OID는 pre-image의 OOS OID와 절대 겹치지 않는다.

즉 UPDATE pre-image의 OOS_X를 삭제해도 post-image(=현재 살아있는 버전)가 참조하는 OOS_Y는 건드리지 않는다.

#### 두 불변식의 결합 (UPDATE 경로)

- 임계값 불변식: "pre-image를 볼 수 있는 판독자가 0명."
- OID 분리성: "pre-image 삭제가 현재 버전의 OOS에 영향 없음."

두 조건이 동시에 성립하므로 UPDATE undo에 대한 forward walk의 `oos_delete`는 어떤 활성 트랜잭션도 방해하지 않는다.

#### 왜 DELETE rcvindex는 제외되나? (commit `fc0e35ced`)

DELETE의 본질이 다르다. `RVHF_MVCC_DELETE_MODIFY_HOME`은 슬롯의 **recdes 내용을 그대로 두고 `delete_mvccid`만 갱신**한다. 그 결과 post-DELETE 슬롯이 참조하는 OOS OID는 pre-image의 OOS OID와 **동일**하다. OID 분리성 불변식이 성립하지 않는다.

이 상태에서 forward-walk가 DELETE undo의 OOS를 회수하고, 이어서 vacuum의 `vacuum_heap_record` REMOVE 경로가 같은 슬롯을 처리하면 같은 OOS OID에 대해 `oos_delete`가 두 번 호출된다. 두 번째 호출은 `oos_delete_chain` 내부에서 `S_DOESNT_EXIST` assert를 트립시킨다.

따라서 게이트는 다음과 같다:

```c
/* src/query/vacuum.c:3690 */
if (log_record_data.rcvindex == RVHF_UPDATE_NOTIFY_VACUUM && undo_data != NULL && undo_data_size > 0)
```

DELETE pre-image의 OOS는 누수되지 않는다 — `vacuum_heap_record` REMOVE 경로가 현재 슬롯의 OOS 참조를 통해 회수한다(Q7 참조). 이 분담이 forward-walk와 REMOVE 경로 사이의 중복 없는 커버리지를 만든다.

---

## Q4. Non-OOS 테이블의 vacuum 성능에 미치는 영향은?

### 질문 상세

새 설계는 `vacuum_process_log_block` 내부의 모든 MVCC 힙 로그 레코드에 대해 undo decode와 `heap_recdes_contains_oos` 체크를 수행한다. OOS를 쓰지 않는 테이블에 대한 vacuum에도 이 비용이 추가되는가?

### 답변

**예, 추가된다. 다만 비용은 상수 시간에 근접하며 무시 가능한 수준으로 설계되었다.**

각 MVCC 힙 로그 레코드에 대해 추가되는 작업(`src/query/vacuum.c:3690-3717`).

1. **rcvindex 게이트** — `log_record_data.rcvindex == RVHF_UPDATE_NOTIFY_VACUUM`. UPDATE가 아닌 모든 rcvindex(INSERT, DELETE, REC_HOME 변경, REDISTRIBUTE, BTREE 연산 등)는 여기서 즉시 skip. UPDATE는 단일 정수 비교 한 번 추가일 뿐.
2. `undo_data != NULL && undo_data_size > 0` 체크 — UPDATE는 항상 undo가 있으므로 사실상 통과.
3. `heap_recdes_contains_oos(&undo_recdes)` — MVCC 헤더 한 바이트 읽고 `OR_MVCC_FLAG_HAS_OOS` 비트 AND. 인라인 O(1).
4. HAS_OOS가 false → inline 블록 종료.

Non-OOS 테이블의 UPDATE는 HAS_OOS 플래그가 전혀 설정되지 않으므로 3번에서 항상 false가 반환된다. UPDATE가 아닌 rcvindex는 1번에서 차단된다. 실질 비용은 **로그 레코드당 1-2개 명령어** 수준.

대조적으로 구 설계는 "OOS 있는 레코드만" 체인 워크를 하므로 non-OOS 테이블에는 영향이 없었다. 즉 이것은 설계 변경에 따른 트레이드오프 포인트다.

**정량 확인 후속 작업:** T0.5 마이크로벤치마크가 계획되어 있으며, 백만 단위 MVCC UPDATE를 vacuum 처리하는 워크로드에서 regression이 측정 가능한지 확인 예정.

---

## Q5. VFID 캐시가 크기 16으로 충분한가? 일시 실패 시 어떻게 처리하나?

### 답변

#### 크기 16의 근거

`vacuum_process_log_block`은 보통 하나의 로그 블록(~64 pages)을 처리한다. 이 블록 내에서 등장하는 고유한 heap VFID 수는 워크로드에 따라 다르지만, 대부분의 경우 몇 개 수준이다. 많은 테이블에 분산된 워크로드라 해도 16은 실용적으로 충분하다는 가정.

```c
#define VACUUM_OOS_VFID_CACHE_SIZE 16         // src/query/vacuum.c:714
```

블록당 고유 heap_vfid 수가 16을 초과하면 17번째부터는 **슬롯 0을 덮어쓰는** 정책이 발동(`src/query/vacuum.c:3440`). 이는 순환 교체 비슷한 단순 휴리스틱이다. 캐시 miss가 발생해도 정확성에는 영향이 없고 성능 영향만 있다. 실제 워크로드에서 16 초과 시나리오가 드물다는 가정이며, 통계로 확인되는 경우 크기 상향을 고려할 수 있다.

#### 캐시 정책: 양성만 캐싱

현재 구현(`src/query/vacuum.c:3399-3445`)은 **음성 결과를 캐싱하지 않는다**. 모든 false 반환 경로가 슬롯 기록 없이 즉시 return하고, `cache[slot]` 적재는 양성(heap이 OOS 파일을 가진다) 결과 직전에만 실행된다. 따라서 "음성 캐시" 개념은 현재 설계에 존재하지 않으며, OOS-미사용 heap에 대한 조회는 같은 블록 내에서 매번 `file_descriptor_get` + `heap_oos_find_vfid`를 다시 수행한다. (성능 영향: 한 블록 내 OOS-미사용 heap의 등장 빈도가 높지 않다는 가정. 핫스팟이 측정되면 향후 양성/확정음성 두 종류 슬롯을 구분하는 변형이 가능.)

#### 일시 실패 처리 (security fix)

`file_descriptor_get`이 실패하는 경우 두 가지로 나뉜다.

- "heap 파일이 존재하지 않는다"는 확정적 결과 (`HFID_IS_NULL`): 정말로 드물며, false 반환 + 캐시 기록 안 함.
- **일시적 실패** (예: 파일 트래커 페이지 버퍼 경합): 이 경우가 관건.

구 구현은 실패 시 `VFID_NULL`을 캐시에 기록했다. 이는 보안/정확성 이슈였다. 일시 실패로 false-negative가 캐시에 박히면 그 블록 처리가 끝날 때까지 같은 heap에 대해 OOS 정리가 skip되어 **OOS 누수**가 발생한다.

수정된 구현은 일시 실패 시 `er_clear()` 후 false를 반환하지만 **캐시에는 기록하지 않는다**(`src/query/vacuum.c:3417-3432`):

```c
/* On any failure below, do NOT cache: a cached VFID_NULL would falsely negative-cache for the
 * rest of the block and leak OOS records. The next call retries. */
VFID_SET_NULL (out_oos_vfid);

if (file_descriptor_get (thread_p, heap_vfid, &file_descriptor) != NO_ERROR)
  {
    er_clear ();
    return false;
  }

hfid = file_descriptor.heap.hfid;
if (HFID_IS_NULL (&hfid))
  {
    er_clear ();
    return false;
  }
```

이렇게 하면 같은 heap_vfid에 대한 다음 조회가 다시 시도되어 transient failure가 해소되면 정상적으로 VFID를 얻을 수 있다.

`heap_oos_find_vfid`가 false를 반환하는 경로(`src/query/vacuum.c:3434-3438`) 역시 동일하게 캐시 기록 없이 false를 반환한다. 즉 현재 설계는 **양성 결과만 캐싱**하는 보수적 정책으로, 어떤 종류의 false도 false-negative caching 위험을 발생시키지 않는다.

---

## Q6. Sysop 페어링 불변식이 깨지면 어떻게 되는가?

### 질문 상세

`vacuum_process_log_block`에는 다음 assert가 있다.

```c
assert (!LOG_FIND_CURRENT_TDES (thread_p)->is_under_sysop ());   // src/query/vacuum.c:3858, 3862, 3871, 3879
```

"현재 tdes가 sysop 안에 있으면 안 된다"는 불변식이다. inline OOS 블록에 sysop이 있으면 이 불변식이 순간적으로 깨질 수 있는데, 어떻게 보장되는가?

### 답변

**모든 코드 경로에서 `log_sysop_start` 직후 `log_sysop_commit` 또는 `log_sysop_abort`가 반드시 호출되도록 구성했다.** 루프의 다음 반복이나 블록 종료 시점에 이미 tdes가 sysop 상태를 빠져나와 있다.

inline 블록의 각 분기를 따져 보자.

| 분기 | sysop 상태 |
|---|---|
| `rcvindex != RVHF_UPDATE_NOTIFY_VACUUM` (게이트 차단) | 진입 없음 |
| `undo_data == NULL` 또는 `undo_data_size == 0` | 진입 없음 |
| `heap_recdes_contains_oos == false` | 진입 없음 |
| `vacuum_oos_vfid_cache_lookup`이 false | 진입 없음 |
| `heap_recdes_get_oos_oids` 실패 | 진입 없음 (sysop은 그 다음 줄에서 시작) |
| Sysop 진입 후 `vacuum_forward_walk_delete_old_oos` 성공 | `log_sysop_commit` (`src/query/vacuum.c:3471`) |
| Sysop 진입 후 실패 | `log_sysop_abort` (`src/query/vacuum.c:3475`) |

따라서 assert가 fire하는 유일한 경로는 코드 변경으로 위 표의 항목 중 하나가 깨진 경우. 이 assert는 미래 리그레션을 잡는 방어선 역할을 한다.

만약 어떤 버그로 인해 assert가 fire한다면:

- **Debug build**: `assert`가 abort를 유발하여 개발자에게 즉시 알림.
- **Release build**: assert는 no-op. 미해제된 sysop이 남아 있으면 다음 sysop을 시도하는 코드가 중첩 에러를 발생시키거나, tdes가 잘못된 상태로 다른 트랜잭션 처리를 오염시킬 수 있다. 이 경우 현실적으로 로그에 이상이 남지만 복구는 쉽지 않다. 따라서 debug build에서 assert가 fire하지 않도록 유지하는 것이 중요하다.

추가 방어로 `assert_release`로 업그레이드하는 옵션도 있으나, 성능/안정성 영향 분석이 필요하여 현재는 `assert`로 둔다.

---

## Q7. 왜 `vacuum_oos_find_vfid_for_heap_record`는 유지되었나?

### 질문 상세

Commit `f912b720c`가 체인 워커(`vacuum_cleanup_prev_version_oos`)를 제거했다면, 그것을 준비하기 위한 헬퍼(현재 이름 `vacuum_oos_find_vfid_for_heap_record`, 구 이름 `vacuum_ensure_oos_vfid_for_heap_record`)도 제거 대상 아닌가?

### 답변

**유지된다. 현재 슬롯의 OOS 정리 경로가 여전히 `helper->oos_vfid`에 의존하며, 특히 DELETE pre-image의 OOS는 forward-walk가 처리하지 않으므로 이 경로가 누수 없는 회수의 핵심이다.**

호출 지점 두 곳(`src/query/vacuum.c`):

- `vacuum_heap_prepare_record` REC_RELOCATION 분기 (`src/query/vacuum.c:2074`).
- `vacuum_heap_prepare_record` REC_HOME 분기 (`src/query/vacuum.c:2189`).

함수 정의는 `src/query/vacuum.c:2391` (구 이름 `vacuum_ensure_oos_vfid_for_heap_record`에서 8a3d7dbc2 + e158f5177로 이름 단순화 + `rectype_label` 인자 제거).

여기서 준비된 `helper->oos_vfid`는 다음 경로에서 사용된다.

1. `vacuum_heap_record` REMOVE 경로 → `vacuum_heap_oos_delete(helper)` 호출(`src/query/vacuum.c:2456, 2565`). 현재 heap 슬롯이 참조하는 OOS OID를 삭제. **DELETE된 슬롯의 OOS가 회수되는 유일한 경로**다(Q3 참조).
2. `vacuum_heap_record_remove_oos_inline` — 새로 추출된 헬퍼(`src/query/vacuum.c:2450`). REMOVE 경로에서 OOS-bearing REC_HOME 슬롯을 sysop 안에서 정리.

Forward walk는 **`RVHF_UPDATE_NOTIFY_VACUUM`의 pre-image OOS만** 처리하며, **현재 버전의 OOS와 DELETE pre-image의 OOS는 모두 `vacuum_heap_record` 경로**에서 처리한다. 이 두 처리는 중복되지 않고 상호 보완적이다.

따라서:

- 체인 워커와 그 전용 가드(`need_prev_version_oos_cleanup`)는 제거됨.
- 현재 버전 + DELETE pre-image의 OOS 정리를 위한 `oos_vfid` 준비는 유지됨.

---

## Q8. Phase 0 I1 감사에서 CONDITIONAL PASS가 나온 의미는?

### 답변

Phase 0 감사는 "MVCC 힙 연산 중 prev-version recdes를 undo로 실어 나르는 rcvindex가 무엇인가"를 식별하는 작업이었다.

#### 결과

**prev-version recdes를 undo payload로 가지는 rcvindex는 두 개뿐이다.**

- `RVHF_UPDATE_NOTIFY_VACUUM` (`src/storage/heap_file.c:23744, 23956`) — UPDATE의 undo
- `RVHF_MVCC_DELETE_MODIFY_HOME` (`src/storage/heap_file.c:20750, 20754`) — DELETE의 undo

나머지는 모두 zero-byte undo:

- `RVHF_MVCC_INSERT`
- `RVHF_MVCC_DELETE_REC_HOME`
- `RVHF_MVCC_NO_MODIFY_HOME`
- `RVHF_MVCC_REDISTRIBUTE`

#### CONDITIONAL의 의미

이 감사는 forward-walk 정리 게이트의 **잠재적 입력 집합**을 식별한 것으로, 실제 게이트는 둘 중 하나(`RVHF_UPDATE_NOTIFY_VACUUM`)만 채택한다(commit `fc0e35ced`, Q3 참조).

"PASS"인 이유: 채택된 `RVHF_UPDATE_NOTIFY_VACUUM`에서 forward walk는 올바르게 동작한다. UPDATE는 transform마다 fresh OOS OID를 할당하므로 pre-image OID와 post-image OID가 disjoint하고, 따라서 pre-image OOS 회수가 살아 있는 슬롯에 영향을 주지 않는다.

"CONDITIONAL"인 이유 1: zero-byte undo 케이스를 **반드시 skip**해야 한다. undo_data_size가 0이면 `RECDES`로 해석할 수 없으며 `heap_recdes_contains_oos`가 undefined behavior를 일으킬 수 있다.

"CONDITIONAL"인 이유 2: `RVHF_MVCC_DELETE_MODIFY_HOME`을 게이트에서 **반드시 제외**해야 한다. DELETE는 슬롯 recdes를 그대로 두므로 pre-image OID와 post-image OID가 동일하고, forward-walk가 회수하면 그 다음 `vacuum_heap_record` REMOVE 경로가 같은 OID를 재차 회수하려 시도하여 `oos_delete_chain`의 `S_DOESNT_EXIST` assert를 트립시킨다.

inline 블록의 게이트(`src/query/vacuum.c:3690`):

```c
if (log_record_data.rcvindex == RVHF_UPDATE_NOTIFY_VACUUM && undo_data != NULL && undo_data_size > 0)
```

`rcvindex` 비교가 CONDITIONAL 2를, `undo_data_size > 0`이 CONDITIONAL 1을 충족시킨다. 둘 중 하나가 빠지면 감사 통과가 무효가 된다.

#### Phase 0 I2 (PASS, conditions 없음)

`oos_delete`가 recovery replay 중 호출되는지 확인. 결과: 호출되지 않는다. recovery는 `oos_rv_redo_delete`(physical `spage_delete`, idempotent; `src/storage/oos_file.cpp:1853`)를 호출한다. 따라서 forward walk의 `oos_delete` 호출이 recovery와 충돌할 위험이 없다.

---

## Q9. Bulk 경로와 Sysop 경로가 성능에 어떤 차이가 있나? (구 Q12 업데이트)

### 답변

Bulk 경로는 **현재 설계에서도** `vacuum_heap_record`의 기존 최적화로 유지된다(OOS 없는 REC_HOME 다수를 하나의 로그로 묶음). 그러나 forward-walk 설계에서는 **OOS 정리의 대부분이 bulk 경로와 독립적으로** 이루어진다. forward walk의 sysop은 `vacuum_process_log_block`의 inline 블록에 있으며, `vacuum_heap_record`가 나중에 호출될 때는 이미 prev-version OOS가 회수된 상태이므로 힙 vacuum은 기존 bulk 경로를 그대로 탈 수 있다.

| 항목 | Bulk 경로 (non-OOS REC_HOME) | Sysop 경로 (현재 버전 OOS) | Forward-walk Sysop (prev OOS) |
|---|---|---|---|
| 위치 | `vacuum_heap_record` | `vacuum_heap_record` (REMOVE + has_oos) | `vacuum_process_log_block` inline |
| 한 번에 처리 | 페이지 내 여러 슬롯 | 슬롯 1개 + 그 OOS | undo 1개의 OOS OID들 |
| 로그 | 페이지당 1건 | slot 1 + OOS 청크 N + sysop 2건 | OOS 청크 N + sysop 2건 |
| 원자성 | page-local | multi-page (sysop) | multi-page (sysop) |

Non-OOS 워크로드에서는 Bulk 경로 비율이 높고, OOS 워크로드에서는 Forward-walk Sysop이 추가된다. Non-OOS 테이블은 `heap_recdes_contains_oos`에서 false가 반환되어 sysop 진입이 아예 없으므로 추가 sysop 비용은 OOS 있는 테이블에만 발생.

---

## Q10. 왜 REC_BIGONE은 OOS 처리가 필요 없나? (구 Q4 유지)

### 답변

이전 리비전의 답과 동일하다.

**OOS와 Overflow(REC_BIGONE)는 설계상 상호 배타적**이다.

- OOS의 목적: 큰 가변 컬럼을 분리하여 heap 레코드를 작게 유지.
- REC_BIGONE의 조건: heap 레코드가 한 페이지에 들어가지 않을 정도로 큼.

OOS를 쓰면 heap 레코드가 작아지므로 REC_BIGONE이 될 수 없다. 따라서 `OR_MVCC_FLAG_HAS_OOS`와 REC_BIGONE은 동시에 설정되지 않는다.

**현재 상태 (L3 권장):** 이 불변식은 debug `assert`로만 강제된다. Release build에서 불변식이 깨지면 조용한 OOS 누수가 발생할 수 있다. 권장 수정은 `assert_release`로 업그레이드 또는 `ER_FAILED` 반환 + 에러 로깅. (이 권장 조치는 L3으로 PR-6986-report.md에 기록됨.)

---

## Q11. 왜 OOS를 DELETE 시 즉시 삭제하지 않고 Vacuum에 맡기나? (구 Q5 유지)

### 답변

MVCC 정합성 때문이다. 자세한 답은 구 리비전과 동일하므로 핵심만 요약.

```
TX1 (MVCCID=100): SELECT * FROM t WHERE id=1;   (스냅샷 읽기 진행)
TX2 (MVCCID=200): DELETE FROM t WHERE id=1;
```

TX2가 DELETE 시 OOS를 즉시 삭제하면, TX1의 스냅샷(=100 시점)에서 이 레코드가 여전히 보이는데 OOS 데이터 접근이 실패한다.

Vacuum은 **모든 활성 트랜잭션이 이 레코드를 더 이상 볼 수 없는** 시점까지 기다린 후 물리 삭제를 수행하므로 문제가 발생하지 않는다. 이 "모두가 못 보는 시점"을 보장하는 장치가 `threshold_mvccid = log_Gl.mvcc_table.get_global_oldest_visible()`이다.

**SA_MODE는 예외** (MVCC 없음). 따라서 SA_MODE의 UPDATE는 eager 정리(`heap_update_home_delete_replaced_oos` — `src/storage/heap_file.c:24131, 호출 지점 24418`)가 별도로 필요하며, SA_MODE DELETE의 eager 정리는 현재 범위 외(L2, 후속 JIRA).

---

## Q12. `RVOOS_NOTIFY_VACUUM`이 여전히 필요한가? (구 Q7 업데이트)

### 답변

**현재 설계에서는 테스트 인프라 전용이며, 프로덕션 코드에서의 역할은 제한적이다.**

초기 설계에서는 `RVOOS_NOTIFY_VACUUM`을 vacuum의 OOS 인식 경로로 통합하려 했으나, forward-walk 재설계에서는 vacuum이 이미 MVCC 힙 로그의 undo payload만으로 OOS를 식별하므로 별도 notify 레코드가 프로덕션 경로에 필요하지 않다.

그러나 다음 이유로 `LOG_IS_MVCC_OPERATION` 매크로에 유지된다.

- `bridge_log_append_undo_for_prev_version_test`와 같은 테스트 브릿지가 가짜 prev-version undo를 append하기 위해 사용.
- Undo 핸들러는 `vacuum_rv_es_nop` (no-op)이어서 recovery 부작용 없음.
- 향후 설계 변화에서 독립적인 OOS notification 경로가 필요해질 가능성에 대비.

프로덕션 vacuum은 이 rcvindex에 의존하지 않지만, 매크로에 포함되어 있음으로써 "MVCC 로그 블록에 포함 가능"한 상태로 유지된다.

---

## Q13. 서버 crash 후 recovery에서 OOS는 어떻게 처리되나? (구 Q9 업데이트)

### 답변

현재 설계의 crash 복구 의미론.

#### Sysop commit 전 crash

```
log_sysop_start
oos_delete chunk 0 → RVOOS_DELETE(log)
oos_delete chunk 1 → RVOOS_DELETE(log)
--- CRASH ---
log_sysop_commit (실행 안 됨)
```

Recovery:

- 커밋되지 않은 sysop → **전체 undo**.
- 각 `RVOOS_DELETE` 레코드의 undo(`oos_rv_undo_delete` → `spage_insert_for_recovery`)가 청크를 복원.
- Vacuum 재시작 시 동일 로그 블록이 다시 처리되어 정상 삭제.

#### Sysop commit 후 crash

```
log_sysop_start
oos_delete chunk 0 → RVOOS_DELETE(log)
oos_delete chunk 1 → RVOOS_DELETE(log)
log_sysop_commit
--- CRASH ---
```

Recovery:

- 커밋된 sysop → redo replay.
- 각 `RVOOS_DELETE`의 redo(`oos_rv_redo_delete` → `spage_delete`)는 idempotent (이미 삭제되어 있으면 no-op).
- 최종 상태는 crash 직전과 동일.

#### 구 설계와의 차이

구 설계는 체인 워커가 자체적으로 LSA 순회를 하며 중간 실패 시 livelock 위험(P2)이 있었다. 신 설계는 단일 sysop 범위가 "undo 1개의 모든 OOS OID"에 국한되므로 체인 처리 단위가 단순하고, 실패 시 부분 진행 없이 atomic하게 롤백.

---

## Q14. `heap_recdes_get_oos_oids()`는 어떻게 OID를 추출하나? (구 Q10 유지)

### 답변

이전 리비전의 답과 동일. 힙 레코드의 VOT를 순회하며 `OR_IS_OOS()` 플래그가 설정된 엔트리의 데이터 위치에서 OID를 읽는다.

```
힙 레코드 내부 구조:
┌──────────────┬──────────────────────────────────┬────────────────────┐
│ MVCC Header  │ Variable Offset Table (VOT)      │ 데이터 영역         │
│              │ [off0] [off1] ... [LAST]          │ [col0] [col1] ...  │
└──────────────┴──────────────────────────────────┴────────────────────┘
```

각 VOT 엔트리는 하위 2비트에 플래그를 담는다.

- `OR_IS_OOS(offset)`: 해당 컬럼이 OOS인지.
- `OR_VAR_BIT_LAST_ELEMENT`: VOT의 마지막 엔트리 마커.

forward-walk 설계의 요점은 이 함수를 **undo recdes**(=pre-image heap recdes)에 대해 호출한다는 점이다. VOT 구조는 on-disk 포맷이므로 undo payload가 그대로 이 함수의 입력이 될 수 있다.

---

## Q15. 구 Q14의 DELETE_INSID_PREV_VER 경로는 이제 어떻게 되나?

### 질문 상세

구 리비전의 Q14는 "`VACUUM_RECORD_DELETE_INSID_PREV_VER` 경로에서도 prev-version OOS 정리를 왜 추가했는가"에 대한 답변이었다. Forward-walk 재설계에서는 이 경로가 어떻게 바뀌었나?

### 답변

**`vacuum_heap_record_insid_and_prev_version` 안의 `vacuum_cleanup_prev_version_oos` 호출은 제거되었다.** `vacuum_cleanup_prev_version_oos` 자체가 삭제되었기 때문.

그러나 문제는 여전히 해결된다.

구 설계에서 `DELETE_INSID_PREV_VER` 경로가 prev-version 정리를 수행한 이유는 "prev_version_lsa를 clear하기 전에 구버전 OOS를 회수해야 한다"는 것이었다. `prev_version_lsa`가 한 번 clear되면 구버전 OOS에 도달할 방법이 없어지므로 "마지막 기회"를 잡아야 했다.

신 설계에서는:

- 각 UPDATE의 `RVHF_UPDATE_NOTIFY_VACUUM` 로그 레코드가 이미 vacuum block 처리 시점에 `vacuum_process_log_block`의 forward walk에 의해 방문된다.
- 해당 시점에 undo payload의 HAS_OOS 여부가 확인되어 prev-image OOS는 이미 삭제되어 있다.
- 그 다음 `vacuum_heap_record_insid_and_prev_version`이 실행되어 INSID 치환과 `prev_version_lsa` clear를 수행하더라도, 해당 prev 체인의 OOS는 이미 회수된 상태.

즉 forward walk와 INSID 경로의 순서가:

1. (먼저) Forward walk → 블록 내 `RVHF_UPDATE_NOTIFY_VACUUM` 로그의 undo에서 OOS 삭제.
2. (나중에) `vacuum_heap` → `vacuum_heap_record_insid_and_prev_version` 또는 `vacuum_heap_record`.

이 순서는 `vacuum_process_log_block` 안에서 이미 보장된다. forward walk는 블록 로그 순회(`src/query/vacuum.c:3583-3859`의 for 루프) 안에 있고, `vacuum_heap`은 그 루프가 끝난 후 `src/query/vacuum.c:3864`에서 호출된다. 따라서 INSID 경로가 `prev_version_lsa`를 clear할 시점에는 이미 prev-image OOS가 회수되어 있다.

**결론:** 구 Q14의 문제("마지막 기회를 놓치면 누수")는 forward-walk 재설계로 자연스럽게 해결되었다. 별도 호출 코드 없이도 "prev_version_lsa clear 이전에 OOS가 회수된다"는 순서 불변식이 블록 내 제어 흐름에 의해 유지된다.

---

**관련 문서:**

- `PR-6986-explanation.md` — 신 설계 전체 설명.
- `PR-6986-report.md` — L1-L4 재평가 및 신규 위험.
- `PR-6986-dangling-oos-analysis.md` — 시나리오별 누수 경로 분석.

**작성자:** Claude Opus 4.7 (1M context) via Daehyun Kim
