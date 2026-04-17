# PR #6986 예상 Q&A

> **PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986) — Vacuum-OOS 연동
>
> 이 문서는 해설서(`PR-6986-explanation.md`)를 읽은 후 나올 수 있는 기술적 질문과 답변을 정리한 것입니다.

---

## Q1. UPDATE 시 prev_version에 있는 구버전 OOS OID는 vacuum이 정리해주나요?

### 질문 상세

UPDATE를 하면 OOS는 항상 "신규 OOS INSERT + heap 레코드에 신규 OOS OID 기록"으로 동작합니다. 구버전 heap 레코드(구버전 OOS OID를 포함)는 undo log에 저장되고 prev_version_lsa로만 접근할 수 있습니다.

나중에 이 레코드의 delete MVCCID가 찍혀서 vacuum이 제거할 때는 현재 heap 레코드의 OOS OID(신버전)를 정리하겠지만, undo log에만 존재하는 구버전 OOS OID는 dangling되는 것 아닌가요?

### 답변

**좋은 질문이며, 실제로 현재 구현의 한계입니다.**

CUBRID의 MVCC UPDATE는 `heap_update_home()`에서 **in-place 방식**으로 동작합니다:

```
[UPDATE 전]
Heap slot 5: [ins=100]          [id=1, data→OOS_A]

[UPDATE 후]
Heap slot 5: [ins=200, prev_ver=L]  [id=1, data→OOS_B]  ← 새 데이터로 덮어씀
Undo log L:  [ins=100]          [id=1, data→OOS_A]  ← 구버전은 log에만 존재
```

Vacuum이 이 레코드를 처리할 때의 동작을 경우별로 보면:

#### 경우 1: `VACUUM_RECORD_DELETE_INSID_PREV_VER` (레코드 살아있음, 메타데이터만 정리)

```
Vacuum 처리:
  1. 현재 heap 레코드 읽기: [ins=200, prev_ver=L] [OOS_B]
  2. ins=200이 충분히 오래됨 → VACUUM_RECORD_DELETE_INSID_PREV_VER
  3. ins를 ALL_VISIBLE로, prev_ver_lsa를 NULL로 설정
  4. OOS_A? → prev_ver_lsa를 따라가서 읽지 않음 → OOS_A 누수!
```

#### 경우 2: `VACUUM_RECORD_REMOVE` (레코드 삭제 후 제거)

```
이후 DELETE 발생 → del=300 설정
Vacuum 처리:
  1. 현재 heap 레코드 읽기: [ins=ALL_VISIBLE, del=300] [OOS_B]
  2. del=300이 충분히 오래됨 → VACUUM_RECORD_REMOVE
  3. vacuum_heap_oos_delete() → OOS_B 삭제 ✓
  4. OOS_A? → 이미 경우 1에서 prev_ver_lsa가 NULL이 됨 → OOS_A 누수!
```

#### 다중 UPDATE의 경우 (더 심각)

```
INSERT(100): slot 5 = [ins=100] [OOS_A]
UPDATE(200): slot 5 = [ins=200, prev_ver=L1] [OOS_B]    ← OOS_A는 L1에만
UPDATE(300): slot 5 = [ins=300, prev_ver=L2] [OOS_C]    ← OOS_B는 L2에만
                                                           L2→L1 체인: OOS_B→OOS_A

Vacuum (VACUUM_RECORD_DELETE_INSID_PREV_VER):
  → prev_ver_lsa 클리어
  → OOS_A, OOS_B 모두 누수!
  → OOS_C만 나중에 DELETE 시 정리됨
```

### 결론 및 향후 계획

**현재 이 PR(M2)에서는 DELETE → Vacuum 경로의 OOS 정리만 구현합니다.** UPDATE 시 prev_version에 있는 구버전 OOS 정리는 M2 범위 밖이며, 향후 개선 사항입니다.

수정 방향: `vacuum_heap_record_insid_and_prev_version()`에서 prev_version_lsa를 클리어하기 전에:
1. prev_version_lsa를 따라 undo log에서 구버전 레코드를 읽는다
2. `heap_recdes_contains_oos()` + `heap_recdes_get_oos_oids()`로 구버전 OOS OID 추출
3. `oos_delete()`로 구버전 OOS 삭제
4. prev_version 체인이 있으면 재귀적으로 처리

다만, 이 수정은 vacuum이 log를 읽어야 하므로 I/O 비용이 추가되고, 기존 `heap_get_visible_version_from_log()` 같은 API를 vacuum 컨텍스트에서 사용할 수 있는지 검증이 필요합니다.

---

## Q2. OOS가 있는 레코드와 없는 레코드가 같은 페이지에 섞여 있으면 어떻게 되나요?

### 답변

정상 동작합니다. Vacuum은 레코드별로 `has_oos` 판정을 합니다:

```
같은 Heap Page에:
  Slot 3: [id=1, name="Alice"]               → has_oos = false → Bulk 경로
  Slot 5: [id=2, data→OOS_OID]               → has_oos = true  → Sysop 경로
  Slot 7: [id=3, name="Bob"]                 → has_oos = false → Bulk 경로
```

Bulk 경로의 레코드들은 모아뒀다가 한 번에 로그를 기록합니다. Sysop 경로의 레코드를 만나면:
1. 먼저 `vacuum_heap_page_log_and_reset()`으로 Bulk에 쌓인 변경사항을 flush
2. Sysop 시작 → OOS 삭제 → Sysop commit
3. 이후 다시 Bulk 수집 재개

따라서 같은 페이지 내에서 Bulk/Sysop이 자유롭게 전환됩니다.

---

## Q3. oos_delete() 중간에 실패하면 어떻게 되나요? (멀티 청크 체인 부분 삭제)

### 답변

`oos_delete_chain()`은 체인의 각 청크를 순서대로 삭제하며, **각 청크 삭제마다 개별적으로 undo 로그를 기록**합니다.

```
Chunk 0 삭제: undo 로그 기록 ✓ → spage_delete ✓
Chunk 1 삭제: undo 로그 기록 ✓ → spage_delete ✓
Chunk 2 삭제: pgbuf_fix 실패! → error 반환
```

이 시점에서:
- Chunk 0, 1은 삭제됨 (+ undo 로그 존재)
- Chunk 2는 삭제 안 됨
- 호출자(`vacuum_heap_record`)가 `log_sysop_abort()`를 호출
- Sysop abort가 **sysop 내 모든 변경을 롤백**:
  - Heap 레코드 vacuum 롤백
  - Chunk 0, 1 삭제 롤백 (undo 로그 replay)
- 결과: 모든 것이 원래 상태로 복원됨

핵심은 sysop이 heap 레코드 제거와 OOS 삭제를 **하나의 원자 단위**로 묶기 때문에, 부분 실패가 발생해도 일관성이 유지된다는 점입니다.

---

## Q4. 왜 REC_BIGONE은 OOS 처리가 필요 없나요?

### 답변

**OOS와 Overflow는 상호 배타적인 메커니즘입니다.**

| 상황 | 결과 |
|------|------|
| 큰 컬럼이 있지만 레코드 전체는 페이지에 들어감 | OOS 사용 (큰 컬럼만 분리) |
| 레코드 전체가 페이지에 안 들어감 | Overflow 사용 (REC_BIGONE) |

OOS의 목적은 "큰 컬럼만 분리하여 나머지 컬럼의 접근 효율을 높이는 것"입니다. OOS가 큰 컬럼을 분리하면 힙 레코드가 작아지므로, REC_BIGONE이 될 필요가 없습니다.

```
OOS 사용 시:  Heap [id | name | oos_oid(8B)]  = 작은 레코드 → REC_HOME
OOS 미사용:   Heap [id | name | 50KB data]    = 큰 레코드 → REC_BIGONE
```

따라서 OOS 플래그(`OR_MVCC_FLAG_HAS_OOS`)와 REC_BIGONE은 동시에 설정될 수 없고, `has_oos` 판정에서 `REC_BIGONE`은 제외됩니다:

```c
bool has_oos = (!VFID_ISNULL(&helper->oos_vfid)
    && (helper->record_type == REC_HOME || helper->record_type == REC_RELOCATION)
    && heap_recdes_contains_oos(&helper->record));
//  ↑ REC_BIGONE은 여기에 포함되지 않음
```

---

## Q5. 왜 OOS를 DELETE 시 즉시 삭제(eager deletion)하지 않고 Vacuum에 맡기나요?

### 답변

**MVCC 정합성 때문입니다.**

```
시나리오:
  TX1 (MVCCID=100): SELECT * FROM t WHERE id = 1;  (스냅샷 읽기 진행 중)
  TX2 (MVCCID=200): DELETE FROM t WHERE id = 1;     (삭제 시도)
```

TX2가 DELETE를 실행하면:
- 힙 레코드에 `del=200`만 기록 (MVCC 삭제 표시)
- TX1은 자신의 스냅샷(MVCCID=100 시점)에서 이 레코드가 보여야 함
- TX1이 OOS 컬럼을 읽을 때 OOS 데이터에 접근해야 함

만약 TX2가 DELETE 시 OOS를 즉시 삭제한다면:
- TX1이 OOS 데이터를 읽으려 할 때 → 이미 삭제됨 → 에러!

Vacuum은 **"모든 활성 트랜잭션이 이 레코드를 더 이상 볼 수 없는" 시점**에서만 물리적 삭제를 수행하므로, 동시성 문제가 발생하지 않습니다.

실제로 이 PR의 초기 버전에는 `locator_delete_oos_force()`라는 eager 삭제 함수가 있었으나, 위 MVCC 정합성 문제와 이중 삭제(eager + vacuum) 문제로 인해 제거되었습니다.

---

## Q6. Vacuum이 OOS를 삭제하면 빈 OOS 페이지는 언제 반환되나요?

### 답변

**현재 구현에서는 OOS 페이지 자체의 deallocation은 수행하지 않습니다.** 이는 이 PR의 scope 밖입니다.

`oos_delete_chain()`은 `spage_delete()`로 청크를 삭제하여 페이지 내 공간을 회수하지만, 페이지의 모든 슬롯이 비어도 페이지 자체를 파일에서 제거하지는 않습니다.

대신, 빈 공간은 bestspace 캐시를 통해 **재사용**됩니다:

```
삭제 후: oos_stats_update() → bestspace 캐시에 빈 공간 등록
재삽입 시: oos_find_best_page() → 캐시에서 빈 공간이 있는 페이지를 찾아 재사용
```

TC-08(VerifyOosSpaceReusedAfterVacuum)이 이를 증명합니다:

```
INSERT 10건 → pages = N
DELETE + vacuum
INSERT 10건 → pages = N (새 페이지 할당 없이 기존 페이지의 빈 슬롯 재사용)
```

---

## Q7. `RVOOS_NOTIFY_VACUUM`은 왜 `LOG_IS_MVCC_OPERATION`에 추가해야 하나요?

### 답변

CUBRID의 로그 시스템은 MVCC 연산과 비-MVCC 연산을 구분합니다. Vacuum은 **MVCC 연산의 로그 레코드만** 처리합니다.

```c
#define LOG_IS_MVCC_OPERATION(rcvindex) \
  (LOG_IS_MVCC_HEAP_OPERATION(rcvindex) \
   || LOG_IS_MVCC_BTREE_OPERATION(rcvindex) \
   || ((rcvindex) == RVES_NOTIFY_VACUUM) \
   || ((rcvindex) == RVOOS_NOTIFY_VACUUM))   // ← 추가
```

`RVOOS_NOTIFY_VACUUM`이 이 매크로에 포함되지 않으면:
1. OOS INSERT/DELETE 로그 레코드가 MVCC 연산으로 인식되지 않음
2. Vacuum이 이 로그 레코드를 무시함
3. OOS 레코드를 참조하는 heap 레코드가 vacuum되어도, vacuum data에 OOS 관련 정보가 빠짐

기존에 `RVES_NOTIFY_VACUUM`(외부 저장소, ES)이 같은 이유로 이 매크로에 포함되어 있으며, OOS도 동일한 패턴을 따릅니다.

---

## Q8. Vacuum 중 다른 트랜잭션이 같은 OOS 레코드에 접근하면 어떻게 되나요?

### 답변

**발생하지 않습니다.** Vacuum이 레코드를 제거하는 시점에는 해당 레코드가 **어떤 트랜잭션에도 보이지 않음**이 보장됩니다.

```
Vacuum 판정 기준 (mvcc_satisfies_vacuum):
  VACUUM_RECORD_REMOVE 조건:
    Delete MVCCID가 존재하고
    && 모든 활성 트랜잭션의 MVCCID보다 이전
    ⇒ "삭제된 레코드를 볼 수 있는 트랜잭션이 0개"
```

이 조건이 만족될 때만 `vacuum_heap_record()`가 호출되므로:
- Heap 레코드를 볼 수 있는 트랜잭션이 없음
- 따라서 heap 레코드를 통해 OOS에 접근할 트랜잭션도 없음
- OOS 삭제가 안전함

페이지 래치 관점에서도:
- `oos_delete_chain()`은 각 OOS 페이지를 `PGBUF_LATCH_WRITE`로 잡음
- 만약 (이론적으로) 다른 스레드가 같은 페이지를 읽으려 하면 래치 대기
- 하지만 위의 MVCC 보장 때문에 이 경우는 발생하지 않음

---

## Q9. 서버 crash 후 recovery에서 OOS는 어떻게 처리되나요?

### 답변

Sysop 내의 모든 연산이 WAL(Write-Ahead Logging)로 보호됩니다.

#### Crash 시나리오 1: Sysop commit 전 crash

```
log_sysop_start()
spage_vacuum_slot(heap)     ← 로그 기록됨
vacuum_heap_oos_delete()    ← 각 청크 삭제가 로그 기록됨
--- CRASH ---
log_sysop_commit()          ← 실행 안 됨
```

Recovery:
- 커밋되지 않은 sysop → **전체 롤백**
- Heap 레코드 복원 (undo)
- OOS 청크 복원 (undo - `oos_rv_undo_delete`가 `spage_insert_for_recovery`로 복원)
- 결과: crash 전 상태로 완전 복원

#### Crash 시나리오 2: Sysop commit 후 crash

```
log_sysop_start()
spage_vacuum_slot(heap)     ← 로그 기록됨
vacuum_heap_oos_delete()    ← 로그 기록됨
log_sysop_commit()          ← 커밋 로그 기록됨
--- CRASH ---
```

Recovery:
- 커밋된 sysop → **redo** (필요시)
- 더티 페이지가 디스크에 안 써졌으면 redo로 재적용
- 결과: vacuum 완료 상태로 복원

---

## Q10. `heap_recdes_get_oos_oids()`는 레코드에서 OOS OID를 어떻게 찾나요?

### 답변

힙 레코드의 **Variable Offset Table (VOT)**을 순회하며 `OR_IS_OOS()` 플래그가 설정된 오프셋을 찾습니다.

```
힙 레코드 내부 구조:

┌──────────────┬──────────────────────────────────┬────────────────────┐
│ MVCC Header  │ Variable Offset Table (VOT)      │ 데이터 영역         │
│              │ [off0] [off1] [off2] ... [LAST]   │ [col0] [col1] ... │
└──────────────┴──────────────────────────────────┴────────────────────┘
```

각 VOT 엔트리의 오프셋 값에는 데이터 위치 외에 플래그 비트가 포함됩니다:
- `OR_IS_OOS(offset)`: 해당 컬럼이 OOS에 저장되었는지
- `OR_VAR_BIT_LAST_ELEMENT`: VOT의 마지막 엔트리인지

```c
// heap_recdes_get_oos_oids() 핵심 로직 (간략화)
for (int index = 0; index < max_var_count; ++index) {
    int offset = read_vot_entry(var_table, index, offset_size);

    if (is_last_element(offset))
        break;  // VOT 끝

    if (!OR_IS_OOS(offset))
        continue;  // OOS가 아닌 일반 컬럼

    // OOS 컬럼 발견 → 데이터 위치에서 OID 읽기
    char *oid_ptr = recdes->data + OR_VAR_OFFSET(recdes->data, index);
    OID oos_oid;
    OR_GET_OID(oid_ptr, &oos_oid);
    oos_oids.push_back(oos_oid);
}
```

이 함수는 테이블의 스키마(class representation)를 참조하지 않고, 레코드의 on-disk 포맷만으로 OOS OID를 추출합니다. 따라서 vacuum 같은 저수준 연산에서 스키마 잠금 없이 사용할 수 있습니다.

---

## Q11. 이 PR의 변경이 기존 non-OOS 테이블의 vacuum 성능에 영향을 주나요?

### 답변

**영향 없습니다.** 추가된 오버헤드는 조건 검사 하나뿐입니다.

`vacuum_heap_prepare_record()`에 추가된 코드:
```c
if (heap_recdes_contains_oos(&helper->record)     // OR_GET_MVCC_FLAG + 비트 AND
    && VFID_ISNULL(&helper->oos_vfid))             // VFID null 체크
```

- `heap_recdes_contains_oos()`는 MVCC 헤더의 플래그 비트 1개를 확인하는 inline 함수 (O(1))
- OOS 플래그가 없으면 (`false`) 즉시 반환 — 추가 작업 없음
- `VFID_ISNULL()`도 이미 단락 평가(short-circuit)로 실행되지 않음

`vacuum_heap_record()`의 `has_oos` 판정도 동일:
```c
bool has_oos = (!VFID_ISNULL(&helper->oos_vfid)    // false (OOS 없는 테이블)
    && ...);                                         // 단락 평가 → 나머지 실행 안 함
```

OOS 파일이 없는 테이블에서는 `oos_vfid`가 항상 NULL이므로, 첫 번째 조건에서 `false`가 되어 기존 코드 경로와 동일하게 실행됩니다.

---

## Q12. Bulk 경로와 Sysop 경로가 성능에 어떤 차이가 있나요?

### 답변

| 항목 | Bulk 경로 (REC_HOME, OOS 없음) | Sysop 경로 (OOS 있음) |
|------|------|------|
| 로그 기록 횟수 | N개 슬롯 → **1번** 로그 | 슬롯당 **1번** + OOS 청크당 **1번** |
| Sysop 오버헤드 | 없음 | start/commit 로그 2건 추가 |
| 적용 시나리오 | 같은 페이지의 작은 레코드들 | OOS가 있는 레코드, 또는 REC_RELOCATION/BIGONE |

Bulk 경로는 같은 페이지의 여러 REC_HOME 삭제를 **하나의 로그 레코드**로 묶어 I/O를 절약합니다:

```
Bulk: [Slot 3 삭제, Slot 7 삭제, Slot 12 삭제] → 로그 1건

Sysop: log_sysop_start
       [Slot 5 삭제] → 로그 1건
       [OOS chunk 0 삭제] → 로그 1건
       [OOS chunk 1 삭제] → 로그 1건
       log_sysop_commit → 로그 1건
       합계: 로그 4건
```

OOS가 있는 레코드가 Sysop 경로를 사용하는 이유는 **원자성 보장** 때문입니다. Heap 레코드만 삭제되고 OOS가 남으면 공간 누수이고, OOS만 삭제되고 heap이 남으면 dangling pointer입니다. Sysop은 이 두 연산을 하나의 원자 단위로 묶습니다.

단, OOS가 있는 레코드는 대형 데이터를 가진 레코드이므로 비율이 낮고, 대부분의 레코드는 여전히 효율적인 Bulk 경로를 사용합니다.

---

## Q13. OOS 파일이 아직 생성되지 않은 테이블에서 vacuum이 실행되면 어떻게 되나요?

### 답변

OOS 파일이 없으면 `heap_oos_find_vfid()`가 `false`를 반환하고, `oos_vfid`가 NULL로 남습니다.

```c
// vacuum_heap_prepare_record() 내
if (heap_recdes_contains_oos(&helper->record) && VFID_ISNULL(&helper->oos_vfid))
{
    if (!heap_oos_find_vfid(...))  // OOS 파일 없으면 false
    {
        assert_release(false);     // OOS 플래그는 있는데 OOS 파일이 없음 = 비정상
        return ER_FAILED;
    }
}
```

이 경우는 **비정상 상태**입니다. `OR_MVCC_FLAG_HAS_OOS` 플래그가 설정된 레코드가 존재한다는 것은 OOS INSERT가 성공적으로 수행되었다는 뜻이고, 그렇다면 OOS 파일이 반드시 존재해야 합니다. OOS 파일 없이 OOS 플래그가 설정될 수 없으므로, 이 상황은 데이터 손상을 의미합니다.

반면, OOS 플래그가 없는 레코드만 있는 테이블(OOS 컬럼이 없거나, 모든 값이 inline 저장 가능한 크기)에서는 `heap_recdes_contains_oos()`가 `false`를 반환하여 OOS 관련 코드가 실행되지 않습니다.
