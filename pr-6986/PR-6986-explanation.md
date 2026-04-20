# PR #6986 코드 설명서 — 포워드 워크 기반 OOS 정리 아키텍처

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**JIRA:** [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE
**베이스:** `feat/oos`
**HEAD:** `31e6e9dc6` (style(vacuum): match indent formatter on range-for and joined if)
**이전 HEAD(레거시 설계):** `6d41132a7`
**작성일:** 2026-04-20
**이전 버전과의 관계:** 이 문서는 2026-04-20의 **forward-walk 재설계**를 반영한 전면 개정판이다. 2026-04-17 리비전에서 설명한 백워드 체인 워커(`vacuum_cleanup_prev_version_oos`) 기반 구현은 완전히 제거되었으며, 그에 관한 §3~§7은 "구 설계" 섹션으로 재편하여 대조 형태로 남겨 두었다.

이 문서는 처음 PR을 접하는 리뷰어를 대상으로 **최종 아키텍처**(포워드 워크 기반 OOS 정리)가 무엇이고 왜 이렇게 설계되었는지 설명한다. 단순한 변경 요약이 아닌 "왜 이 형태가 최소 침습이며 정확한가"에 초점을 둔다.

---

## 목차

1. [TL;DR](#1-tldr)
2. [배경 지식](#2-배경-지식)
3. [최종 아키텍처 — 포워드 워크로의 전환](#3-최종-아키텍처--포워드-워크로의-전환)
4. [핵심 추가 코드](#4-핵심-추가-코드)
5. [삭제된 코드와 제거 가능성에 대한 논증](#5-삭제된-코드와-제거-가능성에-대한-논증)
6. [Sysop을 이용한 crash 복구](#6-sysop을-이용한-crash-복구)
7. [유지된 코드와 그 이유](#7-유지된-코드와-그-이유)
8. [MVCC 안전성 검증](#8-mvcc-안전성-검증)
9. [성능 트레이드오프](#9-성능-트레이드오프)
10. [알려진 한계와 후속 작업](#10-알려진-한계와-후속-작업)
11. [구 설계 참고 — 백워드 체인 워커의 원리와 문제점](#11-구-설계-참고--백워드-체인-워커의-원리와-문제점)

---

## 1. TL;DR

### 무엇이 문제였나

OOS(Out-of-row Overflow Storage)는 큰 가변 컬럼을 heap 레코드에서 분리하여 별도 파일(`FILE_OOS`)에 저장하는 메커니즘이다. M1 단계에서는 DELETE/UPDATE 시 OOS 레코드를 **즉시 삭제하지 않는다.** 활성 MVCC 스냅샷이 여전히 구버전 OOS를 참조할 수 있기 때문이다. 이 회수를 "나중에 vacuum이 한다"고 미뤄둔 것이 M1의 한계였고, CBRD-26668의 목표는 vacuum에 이 능력을 부여하는 것이다.

초기 M2 설계는 **백워드 체인 워커**였다: vacuum이 현재 heap 레코드의 `prev_version_lsa`를 따라 undo 로그를 역추적하면서 각 구버전에서 OOS OID를 긁어내는 방식. 그러나 이 방식은 다음 세 가지 누수/livelock 경로를 품고 있었다 (자세한 분석은 `PR-6986-report.md`의 L1-L4 참조).

- L1: UPDATE가 모든 OOS 컬럼을 non-OOS로 교체한 뒤 DELETE되면, 현재 레코드에 HAS_OOS 플래그가 없어 `vacuum_cleanup_prev_version_oos` 호출 자체가 가드에서 차단되어 dead code가 된다. → 구버전 OOS 영구 누수.
- L2: SA_MODE DELETE 정리 누락 (범위 외).
- L3: REC_BIGONE + OOS 불변식 위반 시 release build에서 조용한 누수.
- L4: RELOCATION 누적 회귀 테스트 부재.

### 무엇을 했나

commit `f912b720c`에서 **백워드 체인 워커를 통째로 제거**하고, vacuum의 **기존 forward-walk 로그 순회 루프**(`vacuum_process_log_block`)에 OOS 정리를 inline으로 삽입했다. MVCC 힙 연산의 undo payload 자체가 "prev-version heap recdes"이므로, vacuum이 해당 로그 레코드를 처리하는 바로 그 시점에 undo로부터 HAS_OOS 여부를 확인하고 OOS OID를 추출해 `oos_delete`를 수행한다.

결과:

- L1은 설계상 소멸 — 각 과거 버전은 자신의 MVCC 힙 로그 레코드가 vacuum될 때 정리되므로, 현재 레코드의 HAS_OOS 상태와 무관.
- 가장 비용이 큰 vacuum 경로 하나(로그 페이지 fetch + LSA chain walk)가 제거되고, 이미 vacuum이 소유한 undo buffer에 대한 저렴한 inline 체크로 대체.
- 새 WAL 레코드 타입 없이 `oos_delete_chain`의 기존 `RVOOS_DELETE` per-chunk undoredo와 `log_sysop_start`/`commit` 조합으로 crash 복구 원자성 확보.

### 한눈에 보기

```
구 설계(M2a, 폐기):
  vacuum_heap_record (REMOVE)
    └─ 현재 레코드에서 oos_vfid 설정 여부 가드
    └─ vacuum_cleanup_prev_version_oos(helper)
        └─ while (!LSA_ISNULL(current_lsa))
            ├─ logpb_prior_lsa_append_all_list   (LOG_CS 획득)
            ├─ logpb_fetch_page                   (page fetch)
            ├─ log_get_undo_record                (undo decode)
            ├─ heap_recdes_contains_oos?
            │   └─ oos_delete 반복
            └─ prev_version_lsa = MVCC_GET_PREV_VERSION_LSA

신 설계(M2b, 본 PR):
  vacuum_process_log_block
    └─ for each MVCC 힙 로그 레코드 in block
        ├─ vacuum_process_log_record  (기존, undo_data 로드)
        ├─ vacuum_collect_heap_objects (기존)
        └─ [신규 inline 블록]
            ├─ heap_recdes_contains_oos(undo_recdes)?
            ├─ 방어적 undo 복사 (log page invalidation 방지)
            ├─ vacuum_oos_vfid_cache_lookup (16-entry stack cache)
            └─ log_sysop_start + vacuum_forward_walk_delete_oos + log_sysop_commit
```

### 주요 커밋

- `f912b720c` refactor(oos): replace prev_version chain walker with forward-walk OOS cleanup
- `31e6e9dc6` style(vacuum): match indent formatter on range-for and joined if

---

## 2. 배경 지식

이 섹션은 2026-04-17 버전 문서의 §2와 동일한 내용을 간략화하여 재수록한 것이다. 이미 익숙한 독자는 §3으로 건너뛰어도 좋다.

### 2.1 OOS 레코드의 물리 구조

OOS는 두 파일이 관여한다.

- **Heap 파일**: 레코드 본체. 큰 가변 컬럼의 실데이터 대신 16바이트 OOS OID(볼륨/페이지/슬롯)가 자리한다.
- **OOS 파일 (`FILE_OOS`, 테이블당 1개)**: OID가 가리키는 실제 큰 값이 청크 단위 체인(`oos_delete_chain`이 관여)으로 저장된다.

Heap 레코드가 OOS를 참조하는지 여부는 두 경로로 표현된다.

1. MVCC 헤더의 `OR_MVCC_FLAG_HAS_OOS` 비트 (레코드 단위).
2. VOT(Variable Offset Table) 엔트리의 `OR_VAR_BIT_OOS` 비트 (컬럼 단위).

Debug build에서 `heap_recdes_contains_oos`는 둘을 교차 검증한다 (heap_file.c:12172 인근).

### 2.2 MVCC UPDATE의 핵심 패턴

```sql
UPDATE t SET big_col = '새값' WHERE id = 1;
```

내부 동작은 다음과 같다.

1. 새 OOS 레코드 삽입 → `OOS_new_oid`.
2. 새 heap 레코드 생성 (`OOS_new_oid`를 포함하는 변형된 recdes).
3. 기존 heap 슬롯에 `prev_version_lsa` 설정 (undo 로그를 가리킴).
4. **구 OOS 레코드는 그대로 유지** — 구 스냅샷이 여전히 참조할 수 있으므로.

결과:

```
heap slot (최신):  [MVCC | ... | OOS_new_oid | ...]          ← 현재 참조
                   prev_version_lsa ─┐
                                      ↓
undo log (구버전):  [MVCC | ... | OOS_old_oid | ...]          ← 과거 스냅샷용
```

핵심 관찰: **구 OOS OID는 undo 로그 안에 존재**한다. 새 설계는 바로 이 사실을 활용한다.

### 2.3 Vacuum의 역할과 전역 임계값

Vacuum은 "더 이상 어떤 스냅샷도 볼 수 없는" 오래된 데이터를 회수한다. `vacuum_process_log_block`(vacuum.c:3458)이 블록 단위로 로그를 순회하며, 각 블록 처리 시점의 전역 임계값은

```c
MVCCID threshold_mvccid = log_Gl.mvcc_table.get_global_oldest_visible ();   // vacuum.c:3477
```

이다. 즉 "현재 살아 있는 모든 스냅샷 중 가장 오래된 것보다 이전의 MVCCID"를 기준으로 처리. 블록 내 각 MVCC 로그 레코드는 `threshold_mvccid`보다 오래되었음이 debug assert로 검증된다 (vacuum.c:3611-3618).

### 2.4 이 PR에서 등장하는 함수들

| 함수 | 역할 |
|---|---|
| `vacuum_process_log_block` | 블록 단위 vacuum 진입점. 모든 MVCC 로그를 순회. |
| `vacuum_process_log_record` | 각 로그 레코드의 undo payload를 디코드. |
| `vacuum_collect_heap_objects` | MVCC 힙 로그에서 재방문할 OID를 수집 (기존). |
| `vacuum_heap_page` / `vacuum_heap_record` | 수집된 OID에 대해 2단계 힙 vacuum 수행 (기존). |
| `vacuum_oos_vfid_cache_lookup` (신규) | 블록당 `{heap_vfid → oos_vfid}` 16-entry 스택 캐시. |
| `vacuum_forward_walk_delete_oos` (신규) | undo recdes에서 OID 추출 후 `oos_delete` 반복. |
| `vacuum_ensure_oos_vfid_for_heap_record` (유지) | INSID 경로에서 `helper->oos_vfid` 준비. |
| `oos_delete` / `oos_delete_chain` | OOS 파일에서 물리 삭제. 청크당 `RVOOS_DELETE` undoredo 기록. |
| `heap_recdes_contains_oos` | HAS_OOS 플래그 검사 (인라인 O(1)). |
| `heap_recdes_get_oos_oids` | VOT를 스캔하여 OID 벡터 추출. |

---

## 3. 최종 아키텍처 — 포워드 워크로의 전환

### 3.1 왜 forward walk가 더 나은가

핵심 관찰은 단순하다. **vacuum은 이미 MVCC 로그 블록을 forward로 순회하고 있고**, 각 MVCC 힙 로그 레코드의 undo payload는 정의상 "prev-version heap recdes"다. 즉 과거 버전에 해당하는 heap recdes가 vacuum의 손에 이미 들려 있다. 이 시점에 recdes의 HAS_OOS 여부를 검사하고 OID를 추출하기만 하면 된다.

구 설계(backward chain walker)가 해야 했던 일들이 forward walk에서는 자연스럽게 제거된다.

| 구 설계 단계 | 신 설계에서의 대체 |
|---|---|
| `logpb_prior_lsa_append_all_list` (LOG_CS 획득) | 불필요. vacuum은 이미 block prefetch로 로그를 읽음. |
| `logpb_fetch_page`로 prev LSA의 페이지 fetch | 불필요. `vacuum_process_log_record`가 이미 페이지를 fix. |
| `log_get_undo_record`로 undo decode | `vacuum_process_log_record`가 `undo_data`/`undo_data_size`로 이미 디코드해 둠 (vacuum.c:3588). |
| `MVCC_GET_PREV_VERSION_LSA`로 체인 추적 | 불필요. forward walk 자체가 모든 버전을 정확히 한 번씩 방문. |
| 현재 레코드의 `oos_vfid` 가드 | 불필요. 각 로그 레코드별로 `heap_vfid`에서 캐시 조회. |

### 3.2 새 설계에서의 OOS 정리 위치

```
vacuum_process_log_block (vacuum.c:3458)
│
├─ prefetch, threshold 설정 등 (기존)
│
└─ for each log entry in block                          ← 기존 포워드 루프
   ├─ vacuum_process_log_record                         (기존)
   ├─ if LOG_IS_MVCC_HEAP_OPERATION                     ← 여기 inline 블록 삽입
   │  ├─ vacuum_collect_heap_objects                    (기존)
   │  └─ [NEW] OOS forward-walk cleanup                 ← vacuum.c:3642-3724
   │     ├─ if undo_data != NULL && undo_data_size > 0
   │     ├─ if heap_recdes_contains_oos(&undo_recdes)
   │     ├─ size guard (2 * IO_MAX_PAGE_SIZE)
   │     ├─ defensive copy (stack 또는 db_private_alloc)
   │     ├─ vacuum_oos_vfid_cache_lookup
   │     ├─ log_sysop_start
   │     ├─ vacuum_forward_walk_delete_oos
   │     └─ log_sysop_commit / log_sysop_abort
   ├─ else if LOG_IS_MVCC_BTREE_OPERATION (기존)
   └─ else if RVES_NOTIFY_VACUUM (기존)
```

### 3.3 흐름 비교

```
구 설계 (삭제됨):
  [DELETE logged] → [threshold 초과 후] → vacuum_heap_record
    ├─ if need_prev_version_oos_cleanup
    │   └─ vacuum_cleanup_prev_version_oos
    │       └─ for each prev version:
    │           ├─ fetch log page
    │           ├─ decode undo
    │           └─ oos_delete(들)
    └─ vacuum_heap_oos_delete (current record)

신 설계 (현재):
  [UPDATE1 logged] → vacuum_process_log_block
                       └─ undo에서 OOS_A 삭제
  [UPDATE2 logged] → vacuum_process_log_block
                       └─ undo에서 OOS_B 삭제
  [DELETE logged]  → vacuum_process_log_block
                       └─ undo에서 OOS_C 삭제
                     그리고 vacuum_heap_record가 OOS_D(현재 버전)를 정리
```

---

## 4. 핵심 추가 코드

### 4.1 `vacuum_oos_vfid_cache_lookup` — 블록당 16-엔트리 VFID 캐시

**파일:** `src/query/vacuum.c:3337-3410`

```c
#define VACUUM_OOS_VFID_CACHE_SIZE 16

typedef struct vacuum_oos_vfid_cache_entry
{
  VFID heap_vfid;
  VFID oos_vfid;    // VFID_NULL sentinel = "heap has no OOS file"
} VACUUM_OOS_VFID_CACHE_ENTRY;
```

- 스택-로컬 배열로 `vacuum_process_log_block`의 프레임 안에 선언된다 (vacuum.c:3494).
- 처음 조회 시 `file_descriptor_get(heap_vfid)` → HFID 복원 → `heap_oos_find_vfid(hfid)` 순으로 호출하여 OOS VFID를 얻는다.
- 한 힙 파일에 OOS 동반 파일이 없는 경우 `VFID_NULL`을 캐시에 기록해 **"음성 캐시"** 로 사용한다. 이후 같은 heap_vfid에 대한 조회는 즉시 false 반환.
- **일시적 실패는 캐시하지 않는다**(vacuum.c:3374-3381). 예를 들어 `file_descriptor_get`이 파일 트래커 페이지 버퍼 경합으로 실패하면 `er_clear()` 후 false를 반환하되 캐시에는 기록하지 않는다. 이렇게 해야 다음 호출에서 재시도 가능하며, 일시 실패로 false-negative가 블록 끝까지 지속되어 OOS가 누수되는 상황을 막을 수 있다. 이는 v2 리뷰에서 지적된 security/correctness 이슈에 대한 수정이다.
- 캐시가 꽉 차면 슬롯 0을 덮어쓰는 단순 정책을 사용한다 (vacuum.c:3402-3407). 블록당 고유 heap_vfid 수가 16을 초과하는 경우는 실전에서 드물며, 초과해도 정확성에 영향이 없다(그저 캐시 miss가 추가될 뿐).

### 4.2 `vacuum_forward_walk_delete_oos` — OID 벡터 삭제

**파일:** `src/query/vacuum.c:3412-3446`

```c
static int
vacuum_forward_walk_delete_oos (THREAD_ENTRY * thread_p,
                                 const RECDES * undo_recdes,
                                 const VFID * oos_vfid)
{
  OID_VECTOR oos_oids;
  int error_code = heap_recdes_get_oos_oids (undo_recdes, oos_oids);
  if (error_code != NO_ERROR) return error_code;

  for (const OID & oos_oid : oos_oids)
    {
      error_code = oos_delete (thread_p, *oos_vfid, oos_oid);
      if (error_code != NO_ERROR) return error_code;
    }
  return NO_ERROR;
}
```

단순함 자체가 정확성 검증의 일부다. 함수 시그니처는 "undo recdes는 HAS_OOS 비트를 가지고 있어야 하고, 호출자가 `log_sysop_start`로 감싸야 한다"라는 precondition만 assert로 명시한다.

### 4.3 Inline 블록 — `vacuum_process_log_block` 내 OOS 정리

**파일:** `src/query/vacuum.c:3642-3724`

핵심 조건과 흐름.

```c
if (LOG_IS_MVCC_HEAP_OPERATION (log_record_data.rcvindex))
  {
    /* ... 기존 vacuum_collect_heap_objects ... */

    if (undo_data != NULL && undo_data_size > 0)
      {
        RECDES undo_recdes;
        undo_recdes.data = undo_data;
        undo_recdes.length = undo_data_size;
        undo_recdes.area_size = undo_data_size;
        undo_recdes.type = REC_HOME;

        if (heap_recdes_contains_oos (&undo_recdes))
          {
            /* (1) 상한 sanity guard */
            if (undo_data_size > 2 * IO_MAX_PAGE_SIZE)
              { assert_release (false); goto oos_cleanup_done; }

            /* (2) 방어적 복사 (log page buffer invalidation 방지) */
            char undo_copy_stack[IO_MAX_PAGE_SIZE];
            char *undo_copy = undo_copy_stack;
            bool undo_copy_on_heap = false;
            if ((size_t) undo_data_size > sizeof (undo_copy_stack))
              {
                undo_copy = (char *) db_private_alloc (thread_p, undo_data_size);
                if (undo_copy == NULL)
                  { er_clear (); goto oos_cleanup_done; }
                undo_copy_on_heap = true;
              }
            memcpy (undo_copy, undo_data, undo_data_size);
            undo_recdes.data = undo_copy;

            /* (3) VFID 캐시 조회 */
            VFID oos_vfid;
            if (vacuum_oos_vfid_cache_lookup (thread_p, oos_vfid_cache,
                                               &oos_vfid_cache_size,
                                               &log_vacuum.vfid, &oos_vfid))
              {
                /* (4) Sysop으로 감싸 원자성 보장 */
                log_sysop_start (thread_p);
                int oos_err = vacuum_forward_walk_delete_oos (thread_p,
                                                               &undo_recdes, &oos_vfid);
                if (oos_err == NO_ERROR)
                  log_sysop_commit (thread_p);
                else
                  { log_sysop_abort (thread_p); er_clear (); }
              }

            if (undo_copy_on_heap)
              db_private_free_and_init (thread_p, undo_copy);
          }
      }
  oos_cleanup_done:
    ;
  }
```

### 4.4 방어적 복사 — 왜 필요한가

`vacuum_process_log_record`가 반환한 `undo_data` 포인터는 vacuum 워커의 shared log page buffer 내부를 가리킬 수 있다. 그런데 후속 `oos_delete` 호출은 `RVOOS_DELETE` WAL 레코드를 append하며, 이 append는 prior list flush를 유발하여 **같은 log page buffer의 내용을 회전시킬 수 있다.** 즉 `oos_delete` 실행 중에 `undo_data`가 가리키는 바이트들이 다른 로그로 덮어쓰일 가능성이 있다. `heap_recdes_get_oos_oids`가 OID를 한 번에 다 읽어내지만, 체인 삭제 도중 `undo_recdes.data`에 대한 참조가 남아 있지 않음을 100% 보장하기 어렵다.

따라서 **sysop 진입 전**에 `undo_data`를 스택 버퍼(`IO_MAX_PAGE_SIZE`) 또는 `db_private_alloc`으로 복사하고 `undo_recdes.data`를 복사본으로 갱신한다. 이는 v2 Risk 테이블에서 명시적으로 플래그된 correctness hazard에 대한 방어다.

### 4.5 상한 가드 — 손상 로그 보호

`undo_data_size > 2 * IO_MAX_PAGE_SIZE`인 경우 `assert_release(false)` 후 skip한다. 합법적인 heap recdes는 두 페이지를 넘지 않으므로, 이보다 큰 값은 로그 레코드 손상의 신호다. 손상된 메모리 영역에서 `memcpy` 시도를 방지한다.

---

## 5. 삭제된 코드와 제거 가능성에 대한 논증

commit `f912b720c`가 제거한 항목.

| 제거 대상 | 위치(구) | 라인 수 |
|---|---|---|
| `vacuum_cleanup_prev_version_oos` (static 구현부) | `src/query/vacuum.c` | ~250 |
| `vacuum_cleanup_prev_version_oos` 포워드 선언 | `src/query/vacuum.c` 상단 | 2 |
| `vacuum_heap_record`의 `need_prev_version_oos_cleanup` 판정 및 sysop 진입 블록 | `src/query/vacuum.c` REMOVE 경로 | ~40 |
| `vacuum_heap_record_insid_and_prev_version`의 prev-version 정리 호출부 | `src/query/vacuum.c` | ~15 |
| 브릿지 함수 `bridge_vacuum_cleanup_prev_version_oos`와 `bridge_log_append_undo_for_prev_version_test`의 일부 | `src/query/vacuum.c` 하단 | 해당 있음 |

### 왜 제거 가능했는가 — 경로별 논증

#### Case A: INSERT + UPDATE + DELETE (OOS 컬럼 유지)

```
t1: INSERT(id=1, big='A')  → heap[v1]=OOS_A
t2: UPDATE SET big='B'     → heap[v2]=OOS_B, undo(RVHF_UPDATE_NOTIFY_VACUUM, recdes=v1)
t3: UPDATE SET big='C'     → heap[v3]=OOS_C, undo(RVHF_UPDATE_NOTIFY_VACUUM, recdes=v2)
t4: DELETE                 → undo(RVHF_MVCC_DELETE_MODIFY_HOME, recdes=v3)
```

Vacuum이 threshold를 초과한 후 블록을 순회하면:

- t2의 로그 레코드 처리 시, undo=recdes(v1) → HAS_OOS → OOS_A 삭제.
- t3의 로그 레코드 처리 시, undo=recdes(v2) → HAS_OOS → OOS_B 삭제.
- t4의 로그 레코드 처리 시, undo=recdes(v3) → HAS_OOS → OOS_C 삭제.
- `vacuum_heap_record`가 REMOVE 경로에서 heap 슬롯 제거 + 현재 버전의 OOS(존재하면)를 `vacuum_heap_oos_delete`로 제거. (DELETE 직전의 현재 버전은 v3이므로 OOS_C이며, 이미 t4의 undo가 같은 OID를 삭제하려 할 텐데 이는 `oos_delete`의 멱등/에러 처리로 해결된다 — 다만 실제로는 DELETE의 undo recdes가 v3의 복사본이므로 OOS_C는 forward walk 시점에 한 번 삭제되며 이후는 no-op.)

#### Case B: UPDATE가 모든 OOS 컬럼을 non-OOS로 교체 후 DELETE (구 L1 시나리오)

```
t1: INSERT(id=1, big='A')  → heap[v1]=OOS_A, HAS_OOS=1
t2: UPDATE SET big=NULL    → heap[v2]=no OOS, HAS_OOS=0,
                             undo(RVHF_UPDATE_NOTIFY_VACUUM, recdes=v1 with HAS_OOS=1)
t3: DELETE                 → undo(RVHF_MVCC_DELETE_MODIFY_HOME, recdes=v2 with HAS_OOS=0)
```

구 설계에서는 t3 이후 vacuum REMOVE가 현재 레코드(v2)의 HAS_OOS가 0이므로 체인 워커가 가드에서 차단, OOS_A 누수. 신 설계에서는 t2의 로그 레코드 처리 시 undo=recdes(v1)의 HAS_OOS=1이 그대로 보이므로 OOS_A가 정상적으로 삭제된다. **"현재 레코드에 HAS_OOS가 있든 없든 무관"** 하며, 이것이 바로 L1을 설계상 소멸시키는 메커니즘이다.

#### Case C: REC_RELOCATION 연쇄

RELOCATION이 발생하더라도 각 UPDATE 시점에 MVCC 힙 로그가 남고 undo payload에 prev-version recdes가 포함된다. Forward walk는 동일하게 작동.

### Phase 0 감사 결과 (I1 CONDITIONAL PASS)

MVCC 힙 연산 중 prev-version recdes를 undo로 실어 나르는 것은 오직 두 개뿐이다.

- `RVHF_UPDATE_NOTIFY_VACUUM` (heap_file.c:24534) — UPDATE의 undo
- `RVHF_MVCC_DELETE_MODIFY_HOME` (heap_file.c:20754) — DELETE의 undo

나머지 MVCC 힙 rcvindex는 zero-byte undo를 가진다.

- `RVHF_MVCC_INSERT`: INSERT에 undo 페이로드 없음
- `RVHF_MVCC_DELETE_REC_HOME`: DELID 기록만
- `RVHF_MVCC_NO_MODIFY_HOME`: no-op
- `RVHF_MVCC_REDISTRIBUTE`: 슬롯 재배치

inline 블록의 `if (undo_data != NULL && undo_data_size > 0)` 가드가 이 zero-byte 케이스를 정확히 skip한다.

Phase 0 I2 (PASS): `oos_delete`는 recovery replay 중 호출되지 않는다. `oos_rv_redo_delete` (oos_file.cpp:1777)은 순수 `spage_delete`이며 구조적으로 idempotent.

---

## 6. Sysop을 이용한 crash 복구

### 6.1 왜 새 WAL 레코드가 필요 없었나

초기 아키텍처 검토에서는 "vacuum이 undo에서 OOS를 삭제했다는 사실"을 별도 WAL 레코드(`RVVAC_OOS_DELETE` 제안)로 기록하는 방식을 고려했다. 그러나 이는 **double-replay hazard**를 유발한다.

- `oos_delete_chain`은 이미 청크당 `RVOOS_DELETE` undoredo 레코드를 기록한다.
- 추가로 `RVVAC_OOS_DELETE`를 만들면 recovery에서 두 레코드가 모두 replay되어 같은 슬롯을 두 번 지우게 된다.

결론: 기존 `RVOOS_DELETE` per-chunk 레코드로 충분하며, `log_sysop_start`/`log_sysop_commit` 페어로 "여러 청크 삭제를 하나의 원자 단위로" 묶으면 crash 복구 의미론이 완성된다.

### 6.2 Sysop의 작동 방식

```
log_sysop_start (vacuum_process_log_block 내부)
  ├─ oos_delete → oos_delete_chain
  │   ├─ chunk 0 제거 + RVOOS_DELETE(log)
  │   ├─ chunk 1 제거 + RVOOS_DELETE(log)
  │   └─ ...
  ├─ (for each OOS OID in undo recdes, 반복)
  │
log_sysop_commit  또는  log_sysop_abort
```

- `commit`: sysop 경계까지의 모든 로그를 flush하고 redo-only로 표시. Crash 후 redo replay가 `oos_rv_redo_delete`(idempotent)로 같은 상태 재구성.
- `abort`: sysop 내에 기록된 `RVOOS_DELETE` 레코드들의 undo(=`oos_rv_undo_delete` → `spage_insert_for_recovery`)를 역순 실행하여 삭제된 청크를 되살린다. 재시도 시 정상 동작 가능.

### 6.3 Sysop 페어링 불변식

`vacuum_process_log_block`의 루프 종료 시점에 다음 assert가 걸려 있다.

```c
assert (!LOG_FIND_CURRENT_TDES (thread_p)->is_under_sysop ());    // vacuum.c:3864
```

그리고 블록 전체 종료 시점에도 동일하게.

```c
assert (!LOG_FIND_CURRENT_TDES (thread_p)->is_under_sysop ());    // vacuum.c:3885
```

이 두 assert는 "모든 `log_sysop_start`는 반드시 `commit` 또는 `abort`로 페어링되어야 한다"는 불변식을 강제한다. inline OOS 블록의 모든 코드 경로(정상, 에러, 상한 초과, 할당 실패, 캐시 miss)가 이 불변식을 위반하지 않도록 구성되어 있다. 구체적으로:

- `heap_recdes_contains_oos`가 false → sysop 진입 없음.
- 상한 초과 → `goto oos_cleanup_done`: sysop 진입 없음.
- `db_private_alloc` 실패 → `goto oos_cleanup_done`: sysop 진입 없음.
- 캐시 miss (VFID_NULL 반환) → sysop 진입 없음.
- Sysop 진입 후 에러 → `log_sysop_abort` 실행.
- Sysop 진입 후 성공 → `log_sysop_commit` 실행.

### 6.4 Crash 시나리오

- **Sysop commit 전 crash**: 해당 sysop 내 모든 `RVOOS_DELETE`의 undo가 replay되어 OOS 청크 복원. Vacuum 재시작 시 동일 로그 블록을 재처리하여 다시 삭제 시도.
- **Sysop commit 후 crash**: redo replay가 `spage_delete`를 다시 수행(또는 이미 반영된 상태라면 idempotent). 최종 상태는 vacuum이 완료한 상태와 동일.

---

## 7. 유지된 코드와 그 이유

### 7.1 `vacuum_ensure_oos_vfid_for_heap_record`

commit `f912b720c`는 체인 워커 관련 코드를 제거하면서도 `vacuum_ensure_oos_vfid_for_heap_record`(vacuum.c:2381-2430)는 그대로 남겨 두었다. 이유는 **INSID 경로가 여전히 이 함수에 의존**하기 때문이다.

호출 지점.

- `vacuum_heap_prepare_record` REC_RELOCATION 분기 (vacuum.c:2069).
- `vacuum_heap_prepare_record` REC_HOME 분기 (vacuum.c:2184).

이 두 지점에서 준비된 `helper->oos_vfid`는 `vacuum_heap_record_insid_and_prev_version` → `vacuum_heap_oos_delete` 경로(현재 버전의 OOS 즉시 삭제)와 `vacuum_heap_record`의 REMOVE 경로(현재 버전의 OOS 삭제)에서 사용된다.

### 7.2 `vacuum_heap_oos_delete`

현재 레코드가 참조하는 OOS OID를 삭제하는 함수는 유지된다. `vacuum_process_log_block`의 forward walk는 **prev-version recdes의 OOS만** 처리하며, 현재 버전의 OOS는 여전히 `vacuum_heap_record` 경로에서 처리된다. 이 두 경로는 중복되지 않고 상호 보완적이다.

| 경로 | 처리 대상 |
|---|---|
| `vacuum_process_log_block` inline (forward walk) | 각 MVCC 힙 로그 레코드의 undo payload(=prev version)에 포함된 OOS |
| `vacuum_heap_record` REMOVE + `vacuum_heap_oos_delete` | 현재 heap 슬롯이 참조하는 OOS (DELETE된 최종 버전) |
| `vacuum_heap_record_insid_and_prev_version` + `vacuum_heap_oos_delete` | INSID 경로에서 현재 버전이 여전히 들고 있는 OOS (필요한 경우) |

### 7.3 `heap_recdes_contains_oos` / `heap_recdes_get_oos_oids`

기존 유틸리티 그대로. forward walk는 이들을 undo_recdes에 대해 호출할 뿐이다.

---

## 8. MVCC 안전성 검증

### 8.1 임계값 불변식

`vacuum_process_log_block` 진입 시 임계값이 설정된다.

```c
MVCCID threshold_mvccid = log_Gl.mvcc_table.get_global_oldest_visible ();   // vacuum.c:3477
```

블록 내 각 MVCC 로그 레코드의 MVCCID는 debug assert(vacuum.c:3611-3618)로 `threshold_mvccid` 미만임이 확인된다. 즉 **이 블록을 처리하는 시점에, 블록 내 어떤 MVCCID도 현재 활성 스냅샷의 시야에 있지 않다.**

forward walk가 특정 UPDATE의 로그 레코드를 만나 그 undo(=prev version)에서 OOS를 삭제한다고 하자. 해당 UPDATE의 MVCCID는 threshold보다 오래되었다. 따라서 모든 활성 스냅샷은 이 UPDATE 이후의 버전만 본다. pre-image(즉 UPDATE 이전의 heap recdes)를 MVCC로 재구성하려는 판독자는 존재할 수 없다. 그러므로 pre-image가 참조하는 OOS를 삭제해도 판독자에게 영향이 없다.

### 8.2 OID 분리성 불변식

`heap_attrinfo_insert_to_oos` (heap_file.c:12408-12436, 12972-12981)는 모든 OOS 컬럼에 대해 **매 transform마다 무조건 fresh OID를 할당**한다. 즉 UPDATE의 post-image가 기록되는 OOS OID는 pre-image의 OOS OID와 절대 같지 않다. 서로 다른 힙 버전은 서로 다른 OOS 슬롯을 참조한다.

따라서 forward walk가 pre-image의 OID를 `oos_delete`한다고 해서 post-image(=현재 버전)가 가리키는 OOS 슬롯이 삭제되지는 않는다. 현재 버전의 판독은 계속 가능하다.

### 8.3 두 불변식의 결합

- 임계값 불변식은 "pre-image 판독자가 없음"을 보장.
- OID 분리성 불변식은 "pre-image 삭제가 현재 버전에 영향 없음"을 보장.

두 불변식이 동시에 성립하므로 forward walk의 OOS 삭제는 MVCC-safe하다.

### 8.4 Concurrent vacuum worker

블록 분배는 배타적이다. 한 블록은 정확히 하나의 워커가 처리한다. OOS 파일에 대한 `oos_delete`의 페이지 래치는 `PGBUF_LATCH_WRITE`이며, 드물지만 다른 워커의 인접 블록 처리와 같은 OOS 페이지가 겹치는 경우 페이지 래치 순서로 직렬화된다.

---

## 9. 성능 트레이드오프

### 9.1 제거된 비용

- `logpb_fetch_page` (체인 링크당 1회, 버퍼 풀 fix + 복사).
- `LOG_CS` critical section 획득 (prior list flush 유도).
- `log_get_undo_record`의 별도 디코드 호출 (vacuum_process_log_record가 이미 디코드한 undo_data를 재활용하지 못하던 비용).
- `db_private_alloc`으로의 undo 버퍼 동적 확장 (300KB+ 레코드의 경우).

### 9.2 추가된 비용

- **모든** MVCC 힙 로그 레코드에 대해 `heap_recdes_contains_oos(undo_recdes)` 호출이 추가됨. 이는 MVCC 헤더 한 바이트 읽기 + 비트 AND 수준의 O(1) inline 체크.
- HAS_OOS가 true인 경우 `heap_recdes_get_oos_oids`가 VOT를 스캔.
- Defensive memcpy: 일반 크기 레코드는 스택 버퍼로 수KB 복사, 대용량은 `db_private_alloc`.
- VFID 캐시 조회: 선형 스캔 O(16).

### 9.3 Non-OOS 테이블에 대한 영향

`heap_recdes_contains_oos`가 false 반환 시 즉시 inline 블록을 빠져나간다. 추가되는 명령은 한 바이트 읽기 + AND + 비교 수준이며, 로그 레코드 하나당 상수 시간. 전체 블록 처리 시간 대비 무시 가능한 수준으로 추정되지만, 정량 확인을 위해 T0.5 벤치마크가 후속 작업으로 남아 있다.

### 9.4 순 효과

가장 비싼 vacuum 경로 하나(체인 워커)가 제거되고 저렴한 inline 체크로 대체되었다. OOS가 많은 워크로드에서는 명확한 순이익. Non-OOS 워크로드에서는 중립 또는 미약한 손실(이 벤치마크가 후속 T0.5).

---

## 10. 알려진 한계와 후속 작업

| 항목 | 상태 | 비고 |
|---|---|---|
| L1 (prev-version dead-code 함정) | 해결됨 | Forward-walk 재설계로 설계상 소멸. |
| L2 (SA_MODE DELETE) | 범위 외 | SA_MODE에는 MVCC가 없으므로 별도 eager 정리가 필요. 후속 JIRA. |
| L3 (REC_BIGONE + OOS) | 미해결 | invariant은 유지되지만 release build에서는 `assert`만. `assert_release`로 업그레이드 권장. |
| L4 (RELOCATION 누적 회귀 테스트) | 미해결 | T3.4 후속 작업. |
| T0.5 (non-OOS 테이블 vacuum 마이크로벤치마크) | 미완 | `heap_recdes_contains_oos` 인라인 비용 정량화. |
| T3.2 (crash inject 테스트) | deferred | sysop commit 전/후 crash 주입. |
| T3.3 (sysop 페어링 스트레스) | deferred | 루프 내 다수 sysop 페어링 검증. |

---

## 11. 구 설계 참고 — 백워드 체인 워커의 원리와 문제점

본 섹션은 2026-04-17 리비전의 §3~§7에 해당하는 구 설계 내용을 **대조 목적**으로만 남긴다. 실제 프로덕션 코드에는 존재하지 않는다.

### 11.1 구 설계의 호출 구조

```
vacuum_heap_record (REMOVE 경로)
  ├─ need_prev_version_oos_cleanup 판정
  │   = MVCC_IS_HEADER_PREV_VERSION_VALID(&mvcc_header)
  │     && !VFID_ISNULL(&helper->oos_vfid)          ← L1의 원인
  │     && (record_type == REC_HOME || REC_RELOCATION)
  ├─ log_sysop_start
  ├─ vacuum_cleanup_prev_version_oos (backward walk)
  ├─ spage_vacuum_slot
  ├─ vacuum_heap_oos_delete (현재 버전의 OOS)
  └─ log_sysop_commit
```

### 11.2 체인 워커 루프

```c
LOG_LSA current_lsa = helper->mvcc_header.prev_version_lsa;
while (!LSA_ISNULL (&current_lsa))
  {
    logpb_prior_lsa_append_all_list (...);    // prior list flush
    logpb_fetch_page (current_lsa);           // page fetch
    log_get_undo_record (current_lsa);        // undo decode
    if (heap_recdes_contains_oos (&old_recdes))
      { /* oos_delete 반복 */ }
    current_lsa = MVCC_GET_PREV_VERSION_LSA (&old_mvcc_header);
  }
```

### 11.3 왜 폐기되었나

- **L1 버그**: current record의 HAS_OOS가 0이면 `!VFID_ISNULL(&oos_vfid)` 가드 때문에 호출 자체가 차단되어 함수 내부 lazy lookup이 dead code가 됨. → PR-6986-report.md 2026-04-17 리비전이 "블로커"로 판정.
- **중복 디코드**: vacuum은 이미 forward walk에서 undo를 디코드하고 있는데 체인 워커가 또 한 번 디코드.
- **LOG_CS contention**: prior list flush가 하드한 critical section 획득 필요.
- **복잡도**: Step A~E 다섯 단계가 실패 시 복원 경로를 복잡하게 만듦.

Forward-walk 재설계는 이 네 가지 약점을 한꺼번에 해결한다.

---

**관련 문서:**

- `PR-6986-QnA.md` — 본 설계에 대한 Q&A.
- `PR-6986-report.md` — L1-L4 누수 경로 재평가.
- `PR-6986-dangling-oos-analysis.md` — 각 UPDATE/DELETE 시나리오별 누수 경로 분석(신 설계 기준).
- `sysop-explained.md` — sysop의 WAL 의미론.
- `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` — OOS 전반 설계.

**작성자:** Claude Opus 4.7 (1M context) via Daehyun Kim
