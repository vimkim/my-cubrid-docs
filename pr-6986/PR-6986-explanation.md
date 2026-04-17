# PR #6986 코드 설명서 — 변경 사항 친절 해설

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**제목:** [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE
**베이스:** `feat/oos`
**HEAD:** `6d41132a7`
**대상 독자:** CUBRID 코드베이스에 익숙하지 않은 리뷰어, 신규 합류자, OOS 구현 학습자

이 문서는 PR #6986의 변경 사항을 **파일별/변경 의도별**로 친절하게 설명한다. 단순히 "무엇을 바꿨는가"가 아닌 **"왜 이렇게 바꿨는가"** 에 초점을 둔다.

---

## 목차

1. [한눈에 보기 (TL;DR)](#1-한눈에-보기-tldr)
2. [배경 지식 다지기](#2-배경-지식-다지기)
3. [핵심 변경 1 — Vacuum이 OOS를 인지하도록 만들기](#3-핵심-변경-1--vacuum이-oos를-인지하도록-만들기)
4. [핵심 변경 2 — 현재 레코드의 OOS 정리](#4-핵심-변경-2--현재-레코드의-oos-정리-vacuum_heap_oos_delete)
5. [핵심 변경 3 — 구버전 OOS 정리](#5-핵심-변경-3--구버전-oos-정리-vacuum_cleanup_prev_version_oos)
6. [핵심 변경 4 — `vacuum_heap_record`에 통합](#6-핵심-변경-4--vacuum_heap_record에-통합)
7. [핵심 변경 5 — SA_MODE eager UPDATE 정리](#7-핵심-변경-5--sa_mode-eager-update-정리)
8. [방어적 개선 — 진단용 cross-validation](#8-방어적-개선--진단용-cross-validation)
9. [포맷 관련 변경 — VOT 4-byte 정렬](#9-포맷-관련-변경--vot-4-byte-정렬)
10. [로그 시스템 — `RVOOS_NOTIFY_VACUUM` 등록](#10-로그-시스템--rvoos_notify_vacuum-등록)
11. [테스트 인프라 — SA/SERVER 분리와 새 테스트들](#11-테스트-인프라--saserver-분리와-새-테스트들)
12. [변경 사항 요약표](#12-변경-사항-요약표)

---

## 1. 한눈에 보기 (TL;DR)

### 해결하려는 문제

OOS M1 설계는 DELETE/UPDATE 시 OOS 레코드를 **즉시 삭제하지 않는다.** MVCC 스냅샷이 아직 구버전을 볼 수 있기 때문에 OOS 레코드를 바로 지우면 동시 reader가 깨진다. 대신 "나중에 vacuum이 처리한다"로 미뤄둔 것이 M1의 한계였다.

**문제:** M1 구현에는 **"vacuum이 OOS를 지우는 코드가 아예 존재하지 않았다."**

결과적으로 OOS 파일은 INSERT/UPDATE로 계속 커지기만 하고 DELETE/UPDATE 후에도 회수되지 않았다. **CBRD-26668의 목표는 이 vacuum 연동을 추가하는 것.**

### 핵심 아이디어

```
기존:
  DELETE → heap에 DELID 세팅 → (끝)
                              ↓ vacuum
  vacuum → heap slot 제거 (OOS는 건드리지 않음)      ← 누수

PR #6986:
  DELETE → heap에 DELID 세팅 → (끝)
                              ↓ vacuum
  vacuum → heap slot 제거 + OOS OID 목록 추출
         + prev_version 체인 walk → oos_delete()    ← 회수
```

### 변경되는 파일 (16개)

| 파일 | 역할 |
|---|---|
| `src/query/vacuum.c` | **핵심.** vacuum 경로에 OOS 정리 로직 추가 |
| `src/storage/heap_file.c` | SA_MODE eager cleanup + 진단 도구 |
| `src/transaction/mvcc.h` | 새 로그 레코드 타입 등록 |
| `src/transaction/locator_sr.c` | 빈 줄 추가 (실질 변경 없음) |
| `src/object/transform_cl.c` | VOT offset 4-byte 정렬 (버그 수정) |
| `src/storage/catalog_class.c` | 동일한 정렬 적용 |
| `unit_tests/oos/CMakeLists.txt` | SA/SERVER 모드 테스트 빌드 분리 |
| `unit_tests/oos/sql/*` | SQL 레벨 통합 테스트 추가 |
| `unit_tests/oos/test_oos_*_server.cpp` | SERVER_MODE 테스트 다수 추가 |

---

## 2. 배경 지식 다지기

### 2.1 OOS 레코드는 어디 있는가

```
Heap 파일 (일반 데이터):
  레코드에 MVCC 헤더 + 고정 컬럼 + 가변 컬럼 영역.
  가변 컬럼 중 "큰 것"은 실제 값 대신 OOS OID (16바이트 포인터)를 저장.

OOS 파일 (FILE_OOS, 테이블당 1개):
  OOS OID가 가리키는 "실제 큰 값"이 저장되는 곳.
  이 파일의 레코드를 지워야 진정한 공간 회수.
```

### 2.2 MVCC UPDATE의 핵심 패턴

```sql
UPDATE t SET big_col = '새값' WHERE id = 1;
```

의 내부 동작:

1. 새 OOS 레코드 삽입 → `OOS_new_oid`
2. 새 heap 레코드 생성 (새 `OOS_new_oid` 포함)
3. 기존 heap 슬롯에 `prev_version_lsa` 설정 (undo log를 가리킴)
4. **구 OOS 레코드는 그대로 둠** (구 스냅샷이 볼 수 있으므로)

결과 상태:

```
heap slot (최신):  [MVCC헤더 | ... | OOS_new_oid | ...]   ← 현재 참조
                   prev_version_lsa ─┐
                                      ↓
undo log (구버전):  [MVCC헤더 | ... | OOS_old_oid | ...]   ← 구 스냅샷용
```

**중요:** 구 OOS OID는 **undo log 안에** 살아 있다. 현재 heap 슬롯에서는 보이지 않는다.

### 2.3 Vacuum이 뭘 하는가

Vacuum은 **더 이상 어떤 스냅샷도 볼 수 없게 된 오래된 데이터를 회수**한다:

- `VACUUM_RECORD_REMOVE`: heap 슬롯 자체를 날림 (DELETE 후 아무도 못 보게 된 경우)
- `VACUUM_RECORD_DELETE_INSID_PREV_VER`: 슬롯은 유지하되 헤더의 INSID/prev_version_lsa만 `ALL_VISIBLE`로 치환 (더 이상 undo 체인을 따라갈 필요 없을 때)

이 PR은 두 경로 모두에서 **OOS 레코드까지 함께 회수**하도록 확장한다.

### 2.4 중요한 함수 매핑

| 함수 | 역할 |
|---|---|
| `vacuum_heap_page()` | 페이지 단위 vacuum 진입점 |
| `vacuum_heap_prepare_record()` | 레코드 처리 준비 (heap 읽기) |
| `vacuum_heap_record_insid_and_prev_version()` | INSID/prev_version 정리 |
| `vacuum_heap_record()` | 실제 REMOVE 수행 |
| `oos_delete()` | OOS 파일에서 레코드 물리 삭제 |
| `heap_oos_find_vfid()` | heap 파일의 OOS VFID 조회 |
| `heap_recdes_contains_oos()` | 레코드가 OOS를 참조하는지 빠른 체크 |
| `heap_recdes_get_oos_oids()` | 레코드에서 OOS OID 목록 추출 |

---

## 3. 핵심 변경 1 — Vacuum이 OOS를 인지하도록 만들기

### 3.1 `VACUUM_HEAP_HELPER`에 `oos_vfid` 필드 추가

**파일:** `src/query/vacuum.c`

```c
struct vacuum_heap_helper
{
  ...
  HFID hfid;
  VFID overflow_vfid;     // 기존: overflow 파일 VFID 캐시
  VFID oos_vfid;          // ★ 추가: OOS 파일 VFID 캐시
  bool reusable;
  ...
};
```

**왜 이렇게?**

Vacuum은 한 page 단위로 여러 레코드를 처리한다. 각 레코드마다 OOS 파일 위치를 새로 조회하면 낭비. `VACUUM_HEAP_HELPER`는 "이 page를 처리하는 동안의 컨텍스트"를 들고 있는 구조체이므로 여기에 캐싱한다. `overflow_vfid`가 이미 같은 목적으로 존재하니 **같은 패턴을 따른다**.

### 3.2 헬퍼 함수 — `vacuum_ensure_oos_vfid_for_heap_record`

```c
static int
vacuum_ensure_oos_vfid_for_heap_record (THREAD_ENTRY * thread_p,
                                         VACUUM_HEAP_HELPER * helper,
                                         const char *rectype_label)
{
  // 케이스 1: 현재 레코드에 OOS 플래그 없음 → 할 일 없음
  // 케이스 2: 이미 oos_vfid 캐시됨 → 할 일 없음
  if (!heap_recdes_contains_oos (&helper->record)
      || !VFID_ISNULL (&helper->oos_vfid))
    {
      return NO_ERROR;
    }

  // 케이스 3: OOS 플래그 있음 + VFID 미캐시 → heap 헤더에서 조회
  if (heap_oos_find_vfid (thread_p, &helper->hfid, &helper->oos_vfid, false))
    {
      return NO_ERROR;
    }

  // 케이스 4: OOS 플래그 있는데 heap에 OOS 파일 없음 → 데이터 손상
  vacuum_er_log_error (VACUUM_ER_LOG_HEAP,
                       "OOS flag set but no OOS VFID found for hfid %d|%d ...",
                       ...);
  assert_release (false);
  return ER_FAILED;
}
```

**왜 이렇게?**

- **Lazy 조회**: OOS가 없는 레코드는 heap 헤더 페이지를 fetch하지 않도록. heap 헤더 조회는 buffer pool fix를 의미하므로 비용이 0은 아니다.
- **Fail loud on corruption**: 레코드 플래그는 "OOS 있다"고 하는데 실제로 OOS 파일이 없으면 → 즉각 에러 + `assert_release`로 release 빌드에서도 트랩.
- **`rectype_label` 매개변수**: "RELOC" vs "HOME" 중 어느 경로에서 실패했는지 로그에 찍기 위한 디버그용 문자열. 현업 디버깅에서 매우 유용.

### 3.3 호출 지점 — `vacuum_heap_prepare_record`

```c
// REC_RELOCATION 분기
error_code = vacuum_ensure_oos_vfid_for_heap_record (thread_p, helper, "RELOC");
if (error_code != NO_ERROR) return error_code;

// REC_HOME 분기 (성공 경로)
error_code = vacuum_ensure_oos_vfid_for_heap_record (thread_p, helper, "HOME");
if (error_code != NO_ERROR) return error_code;
```

**왜 이렇게?**

`vacuum_ensure_oos_vfid_for_heap_record`는 `vacuum_heap_prepare_record` **안에서** 레코드를 읽은 직후 호출된다 (vacuum.c:2058 — `REC_RELOCATION` 분기, vacuum.c:2173 — `REC_HOME` 분기). 이 시점에 VFID를 캐시해두면 이후 정리 로직(`vacuum_heap_record`)이 VFID를 참조할 때 이미 준비된 상태.

조회 실패 시 `ER_FAILED`가 상위로 전파되어 호출부(vacuum.c:1715-1731)가 `goto end`로 빠져나가므로, **이후 단계(`vacuum_heap_record`)가 아예 호출되지 않는다** — 그래서 partial state가 남지 않는다. 진짜 원자성 기전(`log_sysop_abort` 등)이 작동하는 것은 아니고, 단순히 "실패하면 뒤 단계 실행 없음" 구조에 의존하는 것이다.

---

## 4. 핵심 변경 2 — 현재 레코드의 OOS 정리 (`vacuum_heap_oos_delete`)

**파일:** `src/query/vacuum.c`

```c
static int
vacuum_heap_oos_delete (THREAD_ENTRY * thread_p, VACUUM_HEAP_HELPER * helper)
{
  assert (!VFID_ISNULL (&helper->oos_vfid));

  // 1. 현재 heap 레코드에서 OOS OID 목록 추출
  OID_VECTOR oos_oids;
  int error_code = heap_recdes_get_oos_oids (&helper->record, oos_oids);
  if (error_code != NO_ERROR) { assert_release (false); return error_code; }

  // 2. 각 OID에 대해 oos_delete 호출
  for (const OID & oos_oid : oos_oids)
    {
      error_code = oos_delete (thread_p, helper->oos_vfid, oos_oid);
      if (error_code != NO_ERROR)
        {
          vacuum_er_log_error (VACUUM_ER_LOG_HEAP,
                               "Failed to delete OOS record %d|%d|%d.",
                               oos_oid.volid, oos_oid.pageid, oos_oid.slotid);
          return error_code;
        }
    }

  return NO_ERROR;
}
```

**왜 이렇게 간단한가?**

이 함수는 **현재 heap 레코드가 참조하는** OOS 레코드들만 처리한다. 한 heap 레코드가 여러 개의 OOS 컬럼을 가질 수 있으므로 OID_VECTOR로 모아서 순회. OOS OID 위치는 `heap_recdes_get_oos_oids`가 VOT를 스캔해서 찾아준다.

**Q: 부분 실패 시 롤백은?**

이 함수를 호출하는 쪽(`vacuum_heap_record`)이 **sysop으로 감싸서** 호출한다. 실패 시 `log_sysop_abort`가 이미 지워진 OOS 레코드까지 포함해 전체 롤백. 함수 자체는 atomicity를 걱정하지 않아도 되는 것이 설계상 깔끔한 부분.

---

## 5. 핵심 변경 3 — 구버전 OOS 정리 (`vacuum_cleanup_prev_version_oos`)

이 부분이 **PR에서 가장 복잡한 함수**이며, MVCC UPDATE 체인을 따라 undo log를 역추적한다.

### 5.1 무엇이 문제인가

§2.2에서 설명한 것처럼, UPDATE로 교체된 **구버전 OOS OID는 undo log 안에** 있다. 현재 heap 레코드만 봐서는 구버전 OOS OID를 알 수 없다.

```
UPDATE 3번 한 row의 상태:
  heap slot: v3 (OOS_C)
       ↓ prev_version_lsa
  undo:      v2 (OOS_B)
       ↓ prev_version_lsa
  undo:      v1 (OOS_A)

v3가 vacuum에서 REMOVE될 때, OOS_A, OOS_B도 함께 지워야 누수 없음.
```

### 5.2 함수 시그니처와 전제조건

```c
/*
 * NOTE: Caller MUST wrap this call in a log_sysop so partial failures
 *       roll back atomically.
 */
static int
vacuum_cleanup_prev_version_oos (THREAD_ENTRY * thread_p,
                                  VACUUM_HEAP_HELPER * helper)
```

**왜 caller가 sysop을 감싸야 하는가?**

체인 순회 중간에 `oos_delete`가 여러 번 호출되는데, 중간에 실패해서 일부만 지워진 채 끝나면 다음 vacuum이 "이미 지운 OOS를 또 지우려고" 시도하는 livelock 발생. sysop으로 감싸면 실패 시 **지금까지 지운 OOS를 전부 되살려** 다음 vacuum이 정상적으로 재시도 가능.

### 5.3 순회 루프

```c
LOG_LSA current_lsa;
LSA_COPY (&current_lsa, &helper->mvcc_header.prev_version_lsa);

while (!LSA_ISNULL (&current_lsa))
  {
    // Step A: prior list flush (아직 기록 안 된 로그가 있을 수 있음)
    LOG_LSA oldest_prior_lsa = *log_get_append_lsa ();
    if (LSA_LT (&oldest_prior_lsa, &current_lsa))
      {
        LOG_CS_ENTER (thread_p);
        logpb_prior_lsa_append_all_list (thread_p);
        LOG_CS_EXIT (thread_p);
      }

    // Step B: log 페이지 fetch
    LOG_PAGE *log_page_p = (LOG_PAGE *) PTR_ALIGN (log_pgbuf, MAX_ALIGNMENT);
    if (logpb_fetch_page (thread_p, &current_lsa, LOG_CS_SAFE_READER,
                          log_page_p) != NO_ERROR)
      { /* 로그 fetch 실패 → 에러 */ }

    // Step C: undo 레코드 읽기 (버퍼 부족 시 heap alloc으로 확장)
    old_recdes.data = PTR_ALIGN (old_rec_buf, MAX_ALIGNMENT);
    old_recdes.area_size = DB_PAGESIZE;
    SCAN_CODE scan = log_get_undo_record (thread_p, log_page_p,
                                          current_lsa, &old_recdes);
    if (scan == S_DOESNT_FIT)
      {
        int needed = -old_recdes.length;
        if (needed <= 0 || needed > MAX_UNDO_RECORD_SIZE)
          { /* 손상된 length 값 탐지 */ }
        alloc_buf = db_private_alloc (thread_p, needed);
        old_recdes.data = alloc_buf;
        old_recdes.area_size = needed;
        scan = log_get_undo_record (thread_p, log_page_p,
                                    current_lsa, &old_recdes);
      }
    if (scan != S_SUCCESS) { /* 에러 */ }

    // Step D: 이 구버전이 OOS를 참조하면 삭제
    if (heap_recdes_contains_oos (&old_recdes))
      {
        if (VFID_ISNULL (&helper->oos_vfid))
          {
            // Lazy VFID 조회 (문서상 존재, 호출자 가드 때문에 실 호출 경로 없음)
            if (!heap_oos_find_vfid (thread_p, &helper->hfid,
                                      &helper->oos_vfid, false))
              { /* 손상 */ }
          }

        OID_VECTOR oos_oids;
        heap_recdes_get_oos_oids (&old_recdes, oos_oids);
        for (const OID & oos_oid : oos_oids)
          {
            oos_delete (thread_p, helper->oos_vfid, oos_oid);
          }
      }

    // Step E: 체인 따라 이전 버전으로 이동
    or_mvcc_get_header (&old_recdes, &old_mvcc_header);
    LSA_COPY (&current_lsa, &MVCC_GET_PREV_VERSION_LSA (&old_mvcc_header));
  }
```

### 5.4 각 단계별 주석

**Step A — prior list flush**

CUBRID 로그 시스템은 두 단계로 동작한다:
1. 메모리 상의 "prior list"에 로그 append
2. 주기적으로 prior list를 실제 로그 페이지로 flush

우리가 읽으려는 LSA가 아직 flush되지 않았다면 prior list에만 존재한다. 먼저 flush해야 `logpb_fetch_page`로 읽을 수 있다. `LOG_CS` critical section 진입은 이 강제 flush를 위한 것.

**Step B — 로그 페이지 fetch**

`LOG_CS_SAFE_READER` 모드로 읽기. "다른 transaction의 append와 안전하게 공존" 가능한 읽기 모드.

**Step C — undo 레코드 확장 버퍼**

스택 버퍼(`IO_MAX_PAGE_SIZE`)가 부족한 경우 `db_private_alloc`으로 힙 확장. `MAX_UNDO_RECORD_SIZE = IO_MAX_PAGE_SIZE * 16` 상한을 두어 **손상된 length 값으로부터 runaway allocation을 방지**. 이 안전장치가 **중요**하다 — 손상된 로그 페이지의 길이 필드가 GB 단위 값으로 읽히면 메모리 고갈이 발생할 수 있다.

**Step D — 현 버전에 OOS 있으면 삭제**

여기서 `heap_recdes_contains_oos`로 **이 undo 레코드 자체에** OOS가 있는지 확인. 있으면 그 OOS OID들을 추출해 `oos_delete`.

**Step E — 체인 다음 버전으로**

`MVCC_GET_PREV_VERSION_LSA`로 이전 버전 LSA를 따라간다. `LSA_ISNULL`이면 체인 끝.

### 5.5 자원 정리

```c
cleanup:
  if (alloc_buf != NULL)
    {
      db_private_free_and_init (thread_p, alloc_buf);
    }
  return error_code;
```

`goto cleanup`은 에러 경로 + 정상 종료 모두에서 공용 사용. CUBRID의 전형적인 자원 해제 패턴.

---

## 6. 핵심 변경 4 — `vacuum_heap_record`에 통합

지금까지 만든 두 함수(`vacuum_heap_oos_delete`, `vacuum_cleanup_prev_version_oos`)를 `vacuum_heap_record`에서 **어느 타이밍에 호출하느냐**가 이 섹션의 요지.

### 6.1 두 개의 판단 변수

```c
bool has_oos = (!VFID_ISNULL (&helper->oos_vfid)
                && (helper->record_type == REC_HOME
                    || helper->record_type == REC_RELOCATION)
                && heap_recdes_contains_oos (&helper->record));

bool need_prev_version_oos_cleanup =
  (MVCC_IS_HEADER_PREV_VERSION_VALID (&helper->mvcc_header)
   && !VFID_ISNULL (&helper->oos_vfid)
   && (helper->record_type == REC_HOME || helper->record_type == REC_RELOCATION));
```

- `has_oos`: **현재 레코드**가 OOS 참조를 가지고 있는가 → §4의 함수 호출 조건
- `need_prev_version_oos_cleanup`: **구버전 체인**을 따라가 정리할 필요가 있는가 → §5의 함수 호출 조건

### 6.2 sysop 진입 조건 확대

```c
if (helper->record_type == REC_RELOCATION
    || helper->record_type == REC_BIGONE
    || has_oos                        // ★ 조건 추가
    || need_prev_version_oos_cleanup) // ★ 조건 추가
  {
    vacuum_heap_page_log_and_reset (thread_p, helper, false, false);
    log_sysop_start (thread_p);
  }
```

**왜 sysop을 필수로 걸어야 하는가?**

- OOS 삭제는 **다른 페이지**(OOS 파일)까지 건드린다 → multi-page 원자 연산 필요.
- prev_version 체인 정리도 여러 `oos_delete`를 호출 → 부분 실패 시 재시도 livelock 방지.

기존에는 REC_RELOCATION/REC_BIGONE만 multi-page여서 sysop을 걸었다. PR은 **REC_HOME이라도 OOS 정리가 수반되면 sysop 진입**하도록 확대.

### 6.3 호출 순서 (REMOVE 경로)

```c
// 1. prev_version 체인 정리를 먼저
if (need_prev_version_oos_cleanup)
  {
    int chain_err = vacuum_cleanup_prev_version_oos (thread_p, helper);
    if (chain_err != NO_ERROR)
      {
        ASSERT_ERROR ();
        log_sysop_abort (thread_p);   // 전체 롤백
        return chain_err;
      }
  }

// 2. heap 슬롯 물리 제거
spage_vacuum_slot (thread_p, helper->home_page, helper->crt_slotid, helper->reusable);

// 3. 레코드 타입별 분기 처리 (REC_HOME / REC_RELOCATION)
switch (helper->record_type)
  {
  case REC_RELOCATION:
    // ... 기존 로직 + 끝에 OOS 정리
    if (has_oos)
      {
        int oos_err = vacuum_heap_oos_delete (thread_p, helper);
        if (oos_err != NO_ERROR) { log_sysop_abort (thread_p); return oos_err; }
      }
    log_sysop_commit (thread_p);
    break;

  case REC_HOME:
    if (has_oos || need_prev_version_oos_cleanup)
      {
        // sysop 활성: 개별 로그 기록 + OOS 삭제 + commit
        pgbuf_set_dirty (thread_p, helper->home_page, DONT_FREE);
        vacuum_log_redoundo_vacuum_record (thread_p, helper->home_page, ...);
        if (has_oos)
          {
            int oos_err = vacuum_heap_oos_delete (thread_p, helper);
            if (oos_err != NO_ERROR) { log_sysop_abort (thread_p); return oos_err; }
          }
        log_sysop_commit (thread_p);
      }
    else
      {
        helper->n_bulk_vacuumed++;   // 기존: bulk 경로
      }
    break;
  }
```

**왜 prev_version 정리를 먼저?**

prev_version 체인을 따라가기 위해서는 현재 레코드의 `prev_version_lsa`가 여전히 유효해야 한다. 만약 heap 슬롯을 먼저 vacuum한다면 `spage_vacuum_slot` 이후 `helper->record`의 접근이 불안정할 수 있다. **읽기 전용 시점에 체인 순회를 마치고, 그 다음 물리적 삭제를 수행**하는 순서가 안전.

### 6.4 `vacuum_heap_record_insid_and_prev_version`에도 동일 패턴

REMOVE 경로 외에 **INSID/PREV_VERSION 클리어 경로**에서도 같은 정리가 필요하다. PR은 여기에도 sysop + `vacuum_cleanup_prev_version_oos` 호출을 추가.

```c
if (MVCC_IS_HEADER_PREV_VERSION_VALID (&helper->mvcc_header)
    && !VFID_ISNULL (&helper->oos_vfid))
  {
    log_sysop_start (thread_p);
    error_code = vacuum_cleanup_prev_version_oos (thread_p, helper);
    if (error_code != NO_ERROR)
      {
        log_sysop_abort (thread_p);
        return error_code;
      }
    log_sysop_commit (thread_p);
  }
```

**왜 여기에도?**

vacuum이 "더 이상 구버전을 볼 일이 없으니 prev_version_lsa를 지우자"로 결정했다면, 그 시점에 **구버전 OOS도 더 이상 쓸 일이 없다**. LSA를 지우기 **전에** OOS를 회수해야 한다 (지우고 나면 체인을 따라갈 수 없음).

---

## 7. 핵심 변경 5 — SA_MODE eager UPDATE 정리

**파일:** `src/storage/heap_file.c`

### 7.1 왜 SA_MODE는 다른가

CUBRID는 같은 소스로 3개의 바이너리를 만든다:
- `SERVER_MODE`: 실제 DB 서버
- `CS_MODE`: 클라이언트
- `SA_MODE`: 스탠드얼론 (loaddb, unloaddb, restoredb 같은 utility들이 사용)

**SA_MODE의 특징:**
- MVCC 비활성화 (`is_mvcc_op = false`)
- UPDATE는 **in-place overwrite** (prev_version_lsa 생성 안 함)
- Vacuum 쓰레드 없음

→ SA_MODE에서 UPDATE 시 OOS 레코드 정리는 **UPDATE 시점에 직접 해야 한다.** vacuum이 처리해주지 않으므로.

### 7.2 `heap_update_home_delete_replaced_oos`

```c
static int
heap_update_home_delete_replaced_oos (THREAD_ENTRY * thread_p,
                                       HEAP_OPERATION_CONTEXT * context)
{
  OID_VECTOR old_oos_oids, new_oos_oids;
  VFID oos_vfid;

  // 1. 구 레코드의 OOS OID 목록 추출
  heap_recdes_get_oos_oids (&context->home_recdes, old_oos_oids);
  if (old_oos_oids.empty ()) return NO_ERROR;

  // 2. 신 레코드의 OOS OID 목록 추출 (있으면)
  if (heap_recdes_contains_oos (context->recdes_p))
    {
      heap_recdes_get_oos_oids (context->recdes_p, new_oos_oids);
    }

  // 3. OOS VFID 조회
  heap_oos_find_vfid (thread_p, &context->hfid, &oos_vfid, false);

  // 4. 구 OID들 중 신 OID에 포함되지 않은 것만 삭제
  for (const OID & old_oid : old_oos_oids)
    {
      bool still_referenced = false;
      for (const OID & new_oid : new_oos_oids)
        {
          if (OID_EQ (&old_oid, &new_oid))
            { still_referenced = true; break; }
        }
      if (still_referenced) continue;

      oos_delete (thread_p, oos_vfid, old_oid);
    }

  return NO_ERROR;
}
```

**핵심 포인트:**

- **집합 차이 (old - new)를 삭제**: UPDATE가 일부 OOS OID만 교체했을 수 있으므로, 교체되지 않은 OID는 그대로 둔다.
- **O(N*M) 비교**: OOS 컬럼 수가 보통 1-2개라 실용적으로는 문제 없음. 많아지면 hash/sort 기반으로 교체 가능.
- **MVCC 안전성 고려 불필요**: SA_MODE에는 concurrent reader가 없으므로 "스냅샷 때문에 구 OOS를 남겨둘" 필요 없음.

### 7.3 호출 지점 — `heap_update_home`

```c
// heap_update_home 내부, 새 레코드 쓰기가 성공한 뒤:
if (!is_mvcc_op
    && context->home_recdes.type == REC_HOME
    && heap_recdes_contains_oos (&context->home_recdes))
  {
    error_code = heap_update_home_delete_replaced_oos (thread_p, context);
    if (error_code != NO_ERROR) goto exit;
  }
```

**조건:**
1. `!is_mvcc_op` — SA_MODE
2. `home_recdes.type == REC_HOME` — 현재는 REC_HOME만 지원 (REC_RELOCATION 등은 별도 경로)
3. `heap_recdes_contains_oos (&context->home_recdes)` — 구 레코드에 OOS 있을 때만

---

## 8. 방어적 개선 — 진단용 cross-validation

PR은 기능 추가 외에 **기존 코드의 진단 품질**도 보강한다.

### 8.1 `heap_recdes_contains_oos`의 debug build 교차 검증

**파일:** `src/storage/heap_file.c`

```c
bool
heap_recdes_contains_oos (const RECDES * record)
{
  int flag = (INT32) OR_GET_MVCC_FLAG (record->data);
  bool flag_has_oos = (flag & OR_MVCC_FLAG_HAS_OOS) != 0;

#if !defined (NDEBUG)
  // MVCC 플래그 vs VOT 스캔 결과 교차 검증
  bool vot_has_oos = heap_recdes_check_has_oos (record);
  if (flag_has_oos != vot_has_oos)
    {
      heap_recdes_log_oos_consistency_mismatch (record, flag_has_oos, vot_has_oos);
    }
#endif

  return flag_has_oos;
}
```

**왜 이렇게?**

OOS 플래그의 정합성은 두 가지 경로로 표현된다:
1. **MVCC 헤더**의 `OR_MVCC_FLAG_HAS_OOS` 비트 (레코드 수준)
2. **VOT 엔트리**의 `OR_VAR_BIT_OOS` 비트 (컬럼 수준)

둘이 **반드시 일치**해야 한다. 불일치는 직렬화 버그 또는 메모리 손상을 시사. Debug build에서 매번 비교하여 조기 탐지.

### 8.2 불일치 덤프 함수

```c
static void
heap_recdes_log_oos_consistency_mismatch (const RECDES * record,
                                           bool flag_has_oos,
                                           bool vot_has_oos)
{
  // VOT 엔트리 최대 10개 덤프
  char vdump[256];
  for (int vi = 0; vi < mvc && vi < 10 && vpos + 1 < sizeof (vdump); vi++)
    {
      int v = /* offset_size에 맞는 VOT element 읽기 */;
      int written = snprintf (vdump + vpos, sizeof (vdump) - vpos, "%d ", v);
      if (written < 0 || (size_t) written >= sizeof (vdump) - vpos) break;
      vpos += written;
      if (v & OR_VAR_BIT_LAST_ELEMENT) break;
    }

  _er_log_debug (ARG_FILE_LINE,
                 "[OOS-CONSISTENCY] MISMATCH: flag=%d, vot=%d, "
                 "repid_and_flags=0x%08x, mvcc_flags=0x%02x, rec_len=%d, "
                 "offset_size=%d, VOT=[%s]",
                 flag_has_oos ? 1 : 0, vot_has_oos ? 1 : 0,
                 repid_and_flags, OR_GET_MVCC_FLAG (record->data),
                 record->length, osz, vdump);

  if (flag_has_oos && !vot_has_oos)
    {
      assert (false && "MVCC flag has OOS but VOT scan finds no OOS");
    }
}
```

**디버거에 도움이 되는 점:**
- 원시 바이트 덤프가 아닌 **해석된 정보**를 제공 (`repid_and_flags`, `mvcc_flags`)
- VOT offset 값들을 사람이 읽을 수 있게 나열
- 문자열 버퍼 overflow 방지 (`snprintf` 반환값 검사)

### 8.3 `heap_recdes_check_has_oos`에 sanity check 추가

```c
// 첫 번째 VOT 엔트리가 유효 범위 내인지 확인
// 클래스/루트 레코드는 내부 포맷이 달라 VOT로 해석하면 쓰레기값이 나올 수 있음
if (max_var_count > 0)
  {
    int first = /* 첫 엔트리 읽기 */;
    int clean = first & ~OR_VAR_FLAG_MASK;
    if (clean < 0 || clean > recdes->length - header_size)
      {
        return false;   // 비정상 offset → OOS 아님으로 간주
      }
  }
```

**왜 이렇게?**

이 함수는 "MVCC 플래그가 OOS라고 주장하는지 확인"이 아니라 **"VOT를 직접 스캔해서 OOS 존재 여부 판정"**을 하는 함수. 즉 cross-validation의 "answer key" 역할.

클래스 메타데이터 레코드 같은 특수 포맷은 VOT로 해석하면 무의미한 숫자가 나온다. 첫 엔트리가 `recdes->length - header_size` 범위를 벗어나면 "이 레코드는 일반 VOT 포맷이 아니다" 판단 → 안전하게 `false` 반환.

또 하나의 변경 — 기존 `assert(false)` 경로 대신 `return false`:

```c
// 기존: LAST_ELEMENT 못 찾으면 assert로 크래시
// 변경: LAST_ELEMENT 못 찾으면 조용히 false 반환 (old-format fallback)
for (int index = 0; index < max_var_count; ++index)
  {
    ...
    if (OR_IS_LAST_ELEMENT (offset))
      {
        return has_oos;
      }
  }

// No LAST_ELEMENT found — old-format VOT without OOS flag support.
return false;
```

**이유:** 이전 버전 포맷 호환성. 구 포맷 VOT는 LAST_ELEMENT 비트 마커가 없을 수 있고, 그 경우 OOS 플래그 비트로 해석되면 false positive. 그래서 LAST_ELEMENT를 찾지 못하면 "old-format이라고 가정하고 OOS 없음 반환".

---

## 9. 포맷 관련 변경 — VOT 4-byte 정렬

**파일:** `src/object/transform_cl.c`, `src/storage/catalog_class.c`

### 9.1 왜 이게 필요한가

VOT 엔트리는 "offset 값"을 저장하는데, CUBRID 매크로 `OR_GET_VAR_OFFSET`이 **하위 2비트를 마스킹**한다 (그 2비트를 OOS 플래그, LAST_ELEMENT 플래그 등으로 사용).

```c
#define OR_GET_VAR_OFFSET(ptr) (OR_GET_INT(ptr) & ~0x03)   // 하위 2비트 제거
#define OR_IS_OOS(offset)      ((offset) & 0x01)            // bit 0 = OOS
#define OR_IS_LAST_ELEMENT(offset) ((offset) & 0x02)        // bit 1 = LAST
```

이 때문에 **실제 offset 값은 4의 배수여야 한다.** 아니면:
- 값 1001 (bit 0 set) → `OR_GET_VAR_OFFSET`은 1000 반환 (데이터 위치 오류)
- 그리고 `OR_IS_OOS`가 **true**로 잘못 판정됨 → 일반 컬럼이 OOS인 줄 알고 잘못 해석

### 9.2 기존 버그 상황

```c
// 기존 코드
offset = OR_VAR_TABLE_SIZE_INTERNAL (variable_count, offset_size)
         + fixed_size + OR_BOUND_BIT_BYTES (fixed_count);
// offset이 4의 배수가 아닐 수 있음!
```

`fixed_size` + `OR_BOUND_BIT_BYTES`의 합이 4의 배수가 아니면 offset이 unaligned 상태로 나간다. OOS 도입 이전에는 `OR_IS_OOS` 체크가 없었으므로 문제가 안 보였지만, 이제는 false positive 발생.

### 9.3 수정

```c
// 초기 offset을 4-byte 정렬
offset = DB_ALIGN (
  OR_VAR_TABLE_SIZE_INTERNAL (variable_count, offset_size)
  + fixed_size + OR_BOUND_BIT_BYTES (fixed_count),
  4);

// 각 variable column을 저장할 때마다 끝을 4-byte 정렬
for (a = fixed_count; a < att_count; a++)
  {
    ...
    or_put_offset_internal (buf, offset, offset_size);
    offset += len;
    offset = DB_ALIGN (offset, 4);  // ★ 추가
  }
```

그리고 **실제 데이터 쓰기** 함수도 동일하게 패딩 추가:

```c
// put_attributes
for (att in variable_attributes)
  {
    att->type->data_writemem (buf, obj + att->offset, att->domain);
    // 각 var attribute 끝에 4-byte 패딩
    int written = (int) (buf->ptr - start);
    int aligned = DB_ALIGN (written, 4);
    if (aligned > written) or_pad (buf, aligned - written);
  }
```

**적용된 함수들 (17+개):**
- `put_varinfo`, `object_size`, `put_attributes`
- `domain_to_disk`, `domain_size`
- `metharg_to_disk`, `metharg_size`
- `methsig_to_disk`, `methsig_size`
- `method_to_disk`, `method_size`
- `methfile_to_disk`, `methfile_size`
- `query_spec_to_disk`, `query_spec_size`
- `attribute_to_disk`, `attribute_size`
- `resolution_to_disk`, `resolution_size`
- `repattribute_to_disk`, `repattribute_size`
- `representation_to_disk`, `representation_size`
- `put_class_varinfo`, `tf_class_size`
- `root_to_disk`, `root_size`
- `partition_info_to_disk`, `partition_info_size`
- `catcls_put_or_value_into_buffer`

**이것들은 시스템 클래스(catalog) 메타데이터 직렬화 함수들**. 모두 VOT 포맷을 사용하므로 일관되게 정렬 적용.

### 9.4 주의: on-disk 포맷 변경 효과

이 정렬 변경은 **기존 catalog 레코드**의 바이너리 표현을 바꾼다:
- 기존 DB를 새 빌드로 열면 catalog offset이 unaligned 상태로 남아 있을 수 있음
- `heap_recdes_check_has_oos`의 sanity check가 이를 감지하여 `false` 반환
- 결과: 기존 catalog는 "OOS 없음"으로 올바르게 판정 (다행히 false positive 안 남)

**feat/oos 브랜치** 내부에서는 dev DB를 재생성하는 것이 일반적이므로 실질적 영향은 제한적이지만, **main으로 머지 시 기존 설치 DB 호환성 검증 필요**.

---

## 10. 로그 시스템 — `RVOOS_NOTIFY_VACUUM` 등록

**파일:** `src/transaction/mvcc.h`

```c
#define LOG_IS_MVCC_OPERATION(rcvindex) \
  (LOG_IS_MVCC_HEAP_OPERATION (rcvindex) \
   || LOG_IS_MVCC_BTREE_OPERATION (rcvindex) \
   || ((rcvindex) == RVES_NOTIFY_VACUUM) \
   || ((rcvindex) == RVOOS_NOTIFY_VACUUM))     // ★ 추가
```

### 왜 이게 필요한가

`LOG_IS_MVCC_OPERATION`은 로그 매니저가 특정 recovery index를 **MVCC 타입 로그로 취급**하도록 하는 매크로. 그러면:
- `LOG_MVCC_UNDO_DATA` 포맷으로 기록됨
- Vacuum 시스템이 이 로그를 인지하고 prev_version_lsa 체인에 포함시킴

**PR에서의 용도:**

`bridge_log_append_undo_for_prev_version_test`라는 유닛 테스트 브릿지가 `RVOOS_NOTIFY_VACUUM`을 사용해 **가짜 prev-version undo 레코드를 log에 append**한다. 이를 통해 `vacuum_cleanup_prev_version_oos`를 격리 테스트 가능.

`RVOOS_NOTIFY_VACUUM`의 특징:
- **MVCC 오퍼레이션으로 분류됨** → log 레코드 타입이 `LOG_MVCC_UNDO_DATA`로 기록
- **undo 핸들러는 `vacuum_rv_es_nop` (no-op)** → 테스트 트랜잭션 종료 시 실제 페이지에 영향 없음
- VFID를 NULL로 허용 → 테스트에서 가짜 heap VFID 없이도 log append 가능

---

## 11. 테스트 인프라 — SA/SERVER 분리와 새 테스트들

### 11.1 CMakeLists.txt 재구성

**파일:** `unit_tests/oos/CMakeLists.txt`

```cmake
# SA_MODE 테스트 (기존 방식)
set(SA_MODE_TESTS
  test_oos
  test_oos_delete
  test_oos_remove_file
  test_oos_bestspace
)
foreach(test_name ${SA_MODE_TESTS})
  add_executable(${test_name} ${test_name}.cpp)
  target_link_libraries(${test_name} PRIVATE ${EP_LIBS} cubridsa GTest::gtest)
  target_compile_definitions(${test_name} PRIVATE ${COMMON_DEFS} SA_MODE)
endforeach()

# SERVER_MODE 테스트 (신규)
set(SERVER_MODE_TESTS
  test_oos_server
  test_oos_delete_server
  test_oos_remove_file_server
  test_oos_mock_vacuum_server
  test_oos_vacuum_server
)
foreach(test_name ${SERVER_MODE_TESTS})
  add_executable(${test_name} ${test_name}.cpp)
  target_link_libraries(${test_name} PRIVATE ${EP_LIBS} cubrid GTest::gtest)
  target_compile_definitions(${test_name} PRIVATE ${COMMON_DEFS} SERVER_MODE)
endforeach()
```

**분리한 이유:**

- `SA_MODE`는 `cubridsa` (client + server in-process)에 링크
- `SERVER_MODE`는 `cubrid` (실제 서버 바이너리)에 링크
- **두 모드의 DB 동시 접근이 불가**하므로 `RUN_SERIAL TRUE`로 직렬 실행 강제
- `FIXTURES_REQUIRED OOS_DB`와 `TIMEOUT 60`으로 안정성 확보

### 11.2 새 테스트 파일들

#### `test_oos_delete_server.cpp` (390 lines)

SERVER_MODE에서 기본 OOS delete 동작 검증:
- `OosDeleteBasic`: 삽입 → 삭제 → free space 증가 확인
- `OosDeleteThenReadFails`: 삭제 후 읽기 실패 확인
- `OosDeleteMultiChunk`: 멀티 청크 chain 삭제 시 head/next 페이지 모두 회수
- `OosUpdatePattern`: insert old → insert new → delete old → new 정상
- `OosDeleteRestoresFreeSpace`: 삭제 후 회수된 공간 ≥ 레코드 크기
- `OosDeleteLarge160KBMultiChunk`: 160KB 대용량 삭제
- `OosDeleteSlotBecomesUnknown`: 삭제 후 slot이 `REC_UNKNOWN`으로 바뀌는지

#### `test_oos_mock_vacuum_server.cpp`

실제 vacuum 코드 경로를 **거치지 않고** `oos_delete()`를 직접 호출하여 "vacuum이 할 일"의 최소 단위를 검증:
- `BasicInsertAndDelete`
- `MultiChunkDelete`
- `LargeMultiPageDelete`
- `MvccUpdateVacuumPattern`: insert → insert new → delete old → new 유지
- `BulkVacuumReclaimAndReuse`: N개 삽입 후 일괄 삭제 + 공간 재사용

#### `test_oos_vacuum_server.cpp`

실제 `vacuum_heap_oos_delete` / `vacuum_cleanup_prev_version_oos` 브릿지를 타고 검증. `bridge_vacuum_heap_oos_delete`, `bridge_vacuum_cleanup_prev_version_oos`, `bridge_log_append_undo_for_prev_version_test`를 활용.

#### `test_oos_sql_eager_cleanup.cpp` (443 lines, SA_MODE)

SA_MODE eager UPDATE 정리 검증:
- `SingleUpdateCleansOldOos`: UPDATE 1회 후 OOS 페이지 수 증가 없음
- `MultipleUpdatesPagesBounded`: 5행 × 3라운드 UPDATE 후 페이지 수 유한
- `MultiOosColumnUpdateCleanup`: 2개 OOS 컬럼 동시 UPDATE
- `UpdateChurnStress`: 10행 × 10라운드 = 100 UPDATE 후 페이지 유한
- `StepByStepLifecycleWithPageCounts`: 단계별 페이지 수 printf로 가시화
- `UpdateVaryingOosSizes`: 4KB → 8KB → 2KB → 64KB (multi-chunk) 크기 변화
- `MixedColumnsUpdateOnlyOos`: OOS 컬럼만 UPDATE, non-OOS 유지 확인

### 11.3 테스트 공용 헬퍼

**파일:** `unit_tests/oos/sql/test_oos_sql_common.hpp`

```cpp
#if defined(SA_MODE)
// Get OOS VFID for a given table name (SA_MODE only)
static bool get_oos_vfid_for_table (const char *table_name, VFID *oos_vfid_out);

// Get number of user pages in OOS file (SA_MODE only)
static int get_oos_page_count (const char *table_name);
#endif

static int run_vacuum ()
{
#if defined(SA_MODE)
  return xvacuum (thread_get_thread_entry_info ());
#else
  return NO_ERROR;   // SERVER_MODE: vacuum은 백그라운드에서
#endif
}
```

**설계 포인트:**
- OOS 파일 페이지 수를 **직접 카운트**할 수 있게 서버 API 노출. "정리가 잘 되고 있는지"를 객관적으로 측정 가능.
- `run_vacuum()`은 SA_MODE에서 `xvacuum`을 동기 호출하여 테스트 안정성 보장.

### 11.4 Bridge 함수들

**파일:** `src/query/vacuum.c` (하단부)

```c
int bridge_vacuum_heap_oos_delete (THREAD_ENTRY * thread_p,
                                    const VFID * oos_vfid,
                                    RECDES * record);

int bridge_vacuum_cleanup_prev_version_oos (THREAD_ENTRY * thread_p,
                                             const HFID * hfid,
                                             const VFID * oos_vfid,
                                             const LOG_LSA * prev_lsa);

void bridge_log_append_undo_for_prev_version_test (THREAD_ENTRY * thread_p,
                                                    const VFID *,
                                                    const RECDES * old_recdes,
                                                    LOG_LSA * out_lsa);
```

**왜 이런 브릿지가 필요한가:**
- `vacuum_heap_oos_delete`, `vacuum_cleanup_prev_version_oos`는 `static` 함수 → 외부에서 직접 호출 불가
- 진짜 서버 환경 없이 `VACUUM_HEAP_HELPER`를 구성하고 싶음
- 테스트 브릿지가 최소한의 설정(VFID, HFID, LSA)만 받아 내부 static 함수를 호출

**`bridge_log_append_undo_for_prev_version_test`의 교묘함:**

```c
log_append_undo_recdes (thread_p, RVES_NOTIFY_VACUUM, &addr, old_recdes);
// flush prior list 즉시 → fetchable 상태 보장
LOG_CS_ENTER (thread_p);
logpb_prior_lsa_append_all_list (thread_p);
LOG_CS_EXIT (thread_p);
```

이 함수 하나로 "가짜 prev-version undo 레코드를 log에 append + 즉시 fetchable하게 만들기"를 수행. 이후 테스트는 이 LSA를 `vacuum_cleanup_prev_version_oos`에 넘겨 **실제 로그 경로를 타는** 검증을 할 수 있다.

---

## 12. 변경 사항 요약표

### 12.1 파일별 변경 목적

| 파일 | 추가 | 수정 | 목적 |
|---|---|---|---|
| `src/query/vacuum.c` | `vacuum_heap_oos_delete`, `vacuum_cleanup_prev_version_oos`, `vacuum_ensure_oos_vfid_for_heap_record` + 3개 bridge | `vacuum_heap_helper` 구조체 확장, `vacuum_heap_record` / `vacuum_heap_record_insid_and_prev_version` 통합 | vacuum 경로 OOS 연동 |
| `src/storage/heap_file.c` | `heap_update_home_delete_replaced_oos`, `heap_recdes_log_oos_consistency_mismatch` | `heap_recdes_contains_oos` (cross-validation), `heap_recdes_check_has_oos` (sanity check) | SA_MODE eager 정리 + 진단 |
| `src/object/transform_cl.c` | 없음 | 17+ 직렬화 함수에 `DB_ALIGN` 적용 | VOT offset 4-byte 정렬 |
| `src/storage/catalog_class.c` | 없음 | `catcls_put_or_value_into_buffer` 패딩 추가 | 동일 |
| `src/transaction/mvcc.h` | 없음 | `LOG_IS_MVCC_OPERATION`에 `RVOOS_NOTIFY_VACUUM` 추가 | 테스트 log append 지원 |
| `src/transaction/locator_sr.c` | 없음 | 빈 줄 1개 | 실질 변경 없음 |
| `unit_tests/oos/CMakeLists.txt` | SERVER_MODE 테스트 5개 등록 | SA/SERVER 분리 | 테스트 인프라 |
| `unit_tests/oos/sql/CMakeLists.txt` | `test_oos_sql_eager_cleanup` 등록 | TIMEOUT 추가 | 테스트 인프라 |
| `unit_tests/oos/sql/test_oos_sql_common.hpp` | `get_oos_vfid_for_table`, `get_oos_page_count`, `run_vacuum` | SERVER_MODE 분기 | 테스트 공용 헬퍼 |
| `unit_tests/oos/sql/test_oos_sql_eager_cleanup.cpp` | 전체 새 파일 (443줄) | — | SA_MODE eager 정리 테스트 |
| `unit_tests/oos/test_oos_delete_server.cpp` | 전체 새 파일 (390줄) | — | SERVER_MODE delete 테스트 |
| `unit_tests/oos/test_oos_mock_vacuum_server.cpp` | 전체 새 파일 (417줄) | — | Mock vacuum 테스트 |
| `unit_tests/oos/test_oos_vacuum_server.cpp` | 전체 새 파일 | — | 실제 vacuum 경로 테스트 |
| `unit_tests/oos/test_oos_server_common.hpp` | SERVER_MODE 공용 설정 | — | SERVER_MODE 테스트 공유 인프라 |

### 12.2 동작 흐름 요약 (MVCC DELETE → Vacuum)

```
1. User: DELETE FROM t WHERE id=1;
   └─ heap_delete_logical: MVCC DELID 설정 (OOS는 건드리지 않음)

2. 시간 경과, 스냅샷 보호 기간 종료

3. Vacuum 쓰레드: heap page 순회
   └─ vacuum_heap_page
       └─ vacuum_heap_prepare_record
           ├─ heap 레코드 읽기
           └─ vacuum_ensure_oos_vfid_for_heap_record  ← OOS VFID 캐싱
       └─ vacuum_heap_record_insid_and_prev_version
           └─ if (prev_version_valid && oos_vfid)
               └─ vacuum_cleanup_prev_version_oos  ← 구버전 OOS 회수
       └─ vacuum_heap_record
           ├─ sysop_start
           ├─ if (need_prev_version_oos_cleanup)
           │   └─ vacuum_cleanup_prev_version_oos  ← 구버전 OOS 회수
           ├─ spage_vacuum_slot  ← heap 슬롯 물리 제거
           ├─ if (has_oos)
           │   └─ vacuum_heap_oos_delete  ← 현재 OOS 회수
           └─ sysop_commit  ← 원자적 commit
```

### 12.3 알려진 한계 (PR 주석에 명시됨)

1. **UPDATE가 모든 OOS 컬럼을 non-OOS로 교체 후 DELETE된 row**: 현재 가드가 chain walk를 차단 → prev-version OOS 누수 (성능 회귀 방지 목적의 의도적 trade-off, `PR-6986-proposal.md` 참조)
2. **REC_BIGONE + OOS 공존**: invariant상 불가하지만 debug `assert`만으로 방어 (release build에서는 silent)
3. **SA_MODE DELETE**: eager 정리 경로 없음 (vacuum이 no-op이므로 처리 안 됨)
4. **OOS 페이지 자체의 deallocation**: 이 PR 범위 외 (추후 vacuum 고도화)

---

## 마치며

이 PR의 핵심은 **vacuum 경로에 OOS 인지 능력을 주입**하는 것. 그 과정에서 발견된 주변 버그(VOT alignment)와 진단 도구(cross-validation)까지 함께 정비했다.

가장 읽기 까다로운 함수는 **`vacuum_cleanup_prev_version_oos`의 로그 chain walk 루프**다. log page fetch, prior list flush, 버퍼 동적 확장, MVCC 헤더 파싱이 모두 엮여 있다. 이해가 필요한 부분이 있다면:

- CUBRID WAL 일반 패턴 (`logpb_fetch_page`, `log_get_undo_record`) 숙지
- `VACUUM_HEAP_HELPER`의 lifecycle 이해
- MVCC 헤더 레이아웃 (OOS-CONTEXT.md §2)

---

**관련 문서:**
- `PR-6986-report.md` — 코드 리뷰 및 누수 경로 분석
- `PR-6986-perf-regression-report.md` — 성능 회귀 분석
- `PR-6986-proposal.md` — 추가 개선 옵션 제안
- `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` — OOS 전반 설계

**작성자:** Claude Opus 4.7 (1M context) via Daehyun Kim
