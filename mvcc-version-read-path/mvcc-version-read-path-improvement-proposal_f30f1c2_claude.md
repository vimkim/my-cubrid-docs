# MVCC 구버전 읽기 경로 개선 제안

> 기준 소스: cubrid/cubrid `master` (f30f1c260, 11.5.x 개발 브랜치)
> 파일 경로는 리포지토리 루트 기준. 행 번호는 위 커밋 기준이다.
> 작성: Claude (소스 근거 기반 설계 제안)
> 상태: **초안 — 계측 선행 필요**. 아래 제안은 모두 "예상 효과"이며, §5의 계측으로 검증되기 전에는 구현 착수를 권하지 않는다.

---

## 목차

1. [요약](#1-요약)
2. [배경: 구버전 읽기 경로](#2-배경-구버전-읽기-경로)
3. [문제 진단](#3-문제-진단)
4. [제안](#4-제안)
   - [제안 1 — 구버전용 로그 페이지 읽기 캐시](#제안-1--구버전용-로그-페이지-읽기-캐시)
   - [제안 2 — 읽기 경로의 LOG_CS 강제 flush 제거](#제안-2--읽기-경로의-log_cs-강제-flush-제거)
   - [제안 3 — 홉당 전체 페이지 복사와 스택 버퍼 제거](#제안-3--홉당-전체-페이지-복사와-스택-버퍼-제거)
   - [제안 4 — 스캔 캐시에 재구성된 가시 버전 캐싱](#제안-4--스캔-캐시에-재구성된-가시-버전-캐싱)
5. [우선순위와 단계](#5-우선순위와-단계)
6. [선행 작업: 계측](#6-선행-작업-계측)
7. [범위 밖](#7-범위-밖)
8. [부록 A — 코드 위치 색인](#부록-a--코드-위치-색인)
9. [부록 B — 안전성 근거: 로그 페이지 불변성](#부록-b--안전성-근거-로그-페이지-불변성)

---

## 1. 요약

CUBRID는 MVCC 구버전을 힙이 아니라 **트랜잭션 로그에서 재구성**한다. 힙 레코드의
`MVCC_REC_HEADER.prev_version_lsa`(`src/transaction/mvcc.h:45`)가 이전 버전의 로그 주소를
가리키고, 스냅샷이 현재 버전을 볼 수 없는 리더는 이 링크를 따라 로그에서 undo 레코드를 읽어
옛 이미지를 복원한다. InnoDB의 `DB_ROLL_PTR` → undo log 추적과 구조적으로 같은 발상이다.

이 읽기 경로에는 **버전 저장소를 새로 만들지 않고도 고칠 수 있는 비효율 네 가지**가 있다.

| # | 문제 | 핵심 근거 | 위험도 | 예상 효과 |
|---|------|----------|--------|----------|
| 1 | 파일에서 읽은 로그 페이지를 **정상 운영 중 캐시하지 않음** | `log_page_buffer.c:1954` | 중 | **큼** |
| 2 | 읽기 경로가 전역 `LOG_CS`를 잡고 prior list를 강제 flush | `heap_file.c:24965-24975` | 중~높 | 조건부 |
| 3 | 홉마다 16KB 스택 버퍼 2개 + 페이지 전체 memcpy | `heap_file.c:24949`, `log_manager.c:9812` | 낮 | 중 |
| 4 | 같은 행을 다시 읽을 때 체인을 재순회 | `heap_file.h:142-172` | 낮 | 워크로드 의존 |

네 항목 모두 **국소 변경**이며 온디스크 포맷을 바꾸지 않는다. 제안 1이 단일 최대 효과이고
위험도 대비 회수가 가장 좋다. 제안 2는 복잡도가 가장 높아 계측 결과가 정당화할 때만 진행한다.

> **비목표**: 구버전을 전용 slotted undo page로 옮기고 `prev_version_lsa`를 OID로 대체하는
> version store 전환은 이 문서의 범위가 아니다. 근거는 §7 참조.

---

## 2. 배경: 구버전 읽기 경로

### 2.1 왜 로그를 읽는가

`MVCC_REC_HEADER`(`src/transaction/mvcc.h:38-46`)는 다음을 담는다.

```c
struct mvcc_rec_header
{
  INT32 mvcc_flag:8;
  INT32 repid:24;
  int chn;
  MVCCID mvcc_ins_id;         /* 삽입 트랜잭션 */
  MVCCID mvcc_del_id;         /* 삭제 트랜잭션 */
  LOG_LSA prev_version_lsa;   /* log address of previous version */
};
```

힙 페이지에는 **최신 버전만** 존재한다. 가시성 판정(`mvcc_ins_id` / `mvcc_del_id` vs 스냅샷)에서
현재 버전이 탈락하면, `prev_version_lsa`를 따라 로그로 내려가
`heap_get_visible_version_from_log()`(`src/storage/heap_file.c:24943`)가 가시 버전이 나올 때까지
체인을 거슬러 올라간다.

### 2.2 전체 호출 흐름

```
heap_get_visible_version_internal
  │  (현재 버전이 스냅샷에 비가시)
  ▼
heap_get_visible_version_from_log            heap_file.c:24943
  │
  ├─ [24949]  char log_pgbuf[IO_MAX_PAGE_SIZE + MAX_ALIGNMENT]   ← 16KB 스택 버퍼 #1
  │
  ├─ [24965-24975]  요청 LSA가 아직 prior list에 있으면:
  │                   LOG_CS_ENTER → logpb_prior_lsa_append_all_list() → LOG_CS_EXIT
  │
  └─ [24983] for (prev_version_lsa 체인 순회)
       │
       ├─ [24989] logpb_fetch_page (process_lsa, LOG_CS_SAFE_READER, log_page_p)
       │            │                                    log_page_buffer.c:1739
       │            ├─ [1762-1779] 필요 시 LOG_CS_ENTER + prior_lsa_append_all_list
       │            └─ logpb_copy_page
       │                 ├─ [1922] index = pageid % num_buffers        ← direct-mapped
       │                 ├─ [1934-1942] 히트: memcpy(LOG_PAGESIZE) + pageid 재확인
       │                 ├─ [1945] 미스: logpb_read_page_from_file
       │                 │            ├─ [2021] LOG_CS_ENTER_READ_MODE (SAFE_READER)
       │                 │            └─ [2042-2045] 필요 시 logpb_fetch_from_archive
       │                 └─ [1952-1962] 읽은 페이지 캐싱 — 단, !LOG_ISRESTARTED() 일 때만
       │
       └─ [24996] log_get_undo_record (log_page_p, process_lsa, recdes)
                    │                                    log_manager.c:9799
                    ├─ [9812] char log_buf[IO_MAX_PAGE_SIZE + MAX_ALIGNMENT] ← 스택 버퍼 #2
                    ├─ [9820] assert (process_lsa < oldest_prior_lsa)
                    │           → 위 강제 flush가 존재하는 이유
                    └─ [9822-9856] LOG_READ_ADVANCE_WHEN_DOESNT_FIT
                                → 레코드가 페이지를 걸치면 log_page_p에 다음 페이지를 덮어씀
```

핵심 관찰: **체인 한 홉당 로그 페이지 fetch 1회 이상 + 페이지 전체 복사 1회 이상**이며,
fetch가 미스하면 디스크(또는 아카이브)를 때린다.

---

## 3. 문제 진단

### P1. 로그 페이지 버퍼가 direct-mapped

`src/transaction/log_page_buffer.c:381-384`:

```c
logpb_get_log_buffer_index (LOG_PAGEID log_pageid)
{
  return log_pageid % log_Pb.num_buffers;
}
```

연관성이 전혀 없다. 슬롯이 pageid로 고정되므로, 구버전이 있는 옛 페이지와 현재 append 중인
뜨거운 페이지가 같은 슬롯에 매핑되면 옛 페이지는 상주할 수 없다. 구버전은 정의상 옛 페이지에
있으므로 이 구조에서 체계적으로 불리하다.

### P2. 파일에서 읽은 페이지를 정상 운영 중 캐시하지 않음 — **최대 문제**

`log_page_buffer.c:1952-1962`:

```c
  // Optimize log page fetching by caching
  // for now, only used to optimize recovery phase
  if (log_bufptr->pageid < pageid && !LOG_ISRESTARTED ())
    {
      /* ... 캐싱 ... */
    }
```

주석이 명시한다 — *"for now, only used to optimize recovery phase."* `LOG_ISRESTARTED()`가
참인 정상 운영 중에는 이 블록이 실행되지 않는다. 즉 **구버전 읽기로 디스크에서 읽어온 로그
페이지는 호출자 버퍼로 복사된 뒤 그냥 버려진다.** 같은 버전 체인을 N번 읽으면 디스크를 N번
읽는다.

가드가 존재하는 이유는 (추정) 로그 페이지 버퍼 슬롯이 **append 스테이징 영역과 공용**이기
때문이다. `log_page_buffer.c:851-870`에 dirty 로그 페이지를 축출하려는 상황을
`assert_release(false)` + *"should not happen"* 으로 막아 둔 코드가 있어, dirty 슬롯을
읽기 캐싱으로 덮는 것이 금지 사항임을 확인할 수 있다. → **제안 1은 이 공용 구조를 건드리지
않는 방향으로 설계한다.**

### P3. 홉마다 16KB 스택 버퍼 2개 + 페이지 전체 복사

- `heap_file.c:24949` — `char log_pgbuf[IO_MAX_PAGE_SIZE + MAX_ALIGNMENT]`
- `log_manager.c:9812` — `char log_buf[IO_MAX_PAGE_SIZE + MAX_ALIGNMENT]` (압축 해제용,
  `log_manager.c:9903`에서 `PTR_ALIGN`으로 사용)
- `log_page_buffer.c:1937` — 버퍼 히트 시에도 `memcpy (log_pgptr, log_bufptr->logpage, LOG_PAGESIZE)`

한 호출에 최대 32KB를 스택에 잡고, 홉마다 최대 16KB를 복사한다. 실제로 필요한 것은 그 안의
undo 레코드 하나(보통 수십~수백 바이트)다.

복사가 존재하는 이유는 명확하다 — `LOG_BUFFER`(`log_page_buffer.c:193-200`)에는
**핀 카운트도 래치도 없다.**

```c
struct log_buffer
{
  volatile LOG_PAGEID pageid;
  volatile LOG_PHY_PAGEID phy_pageid;
  bool dirty;
  LOG_PAGE *logpage;
};
```

그래서 공유 버퍼를 가리키는 포인터를 그대로 넘기는 것은 안전하지 않고, 현재 코드는
`log_page_buffer.c:1934-1942`의 **복사 후 pageid 재확인** 패턴으로 대응한다.

### P4. 읽기 경로가 전역 LOG_CS를 최대 3곳에서 잡는다

| 위치 | 조건 |
|------|------|
| `heap_file.c:24969` | 요청 버전이 아직 prior list에 있을 때 (`LOG_CS_ENTER`, 배타) |
| `log_page_buffer.c:1765` | 위와 동일 조건을 `logpb_fetch_page`에서 재확인 (`LOG_CS_ENTER`, 배타) |
| `log_page_buffer.c:2021` | 파일 읽기가 필요할 때마다 (`LOG_CS_ENTER_READ_MODE`, 공유) |

세 번째는 공유 모드지만 **모든 파일 읽기마다** 발생한다. 주석(`2017-2020`)에 따르면 아카이브
생성/마운트와의 경쟁을 막기 위한 것이다.

### P5. 지역성 부재와 아카이브 접근

구버전은 그것을 쓴 트랜잭션이 append한 자리에 흩어져 있으므로 체인 순회는 로그 공간 전역에
걸친 랜덤 리드다. 충분히 오래된 버전은 아카이브에 있어
`logpb_fetch_from_archive()`(`log_page_buffer.c:2045`)로 아카이브 볼륨 접근까지 간다.

P5는 구조적 문제이며 §7의 version store 전환 없이는 근본적으로 해결되지 않는다. 다만 **제안 1이
반복 접근을 캐시로 흡수**하면 실질 영향은 크게 줄어든다.

---

## 4. 제안

### 제안 1 — 구버전용 로그 페이지 읽기 캐시

**대상**: `src/transaction/log_page_buffer.c:1952-1962`, `logpb_copy_page` 경로

**현상**: P2 — 정상 운영 중 파일에서 읽은 로그 페이지가 캐시되지 않아, 동일 페이지를 반복
디스크에서 읽는다. P1(direct-mapped)이 이를 악화시킨다.

**변경안 (권장)**: append용 슬롯 배열과 **분리된 읽기 전용 캐시**를 신설한다.

- 신규 파라미터(가칭 `log_version_read_cache_size`)로 크기 지정, 기본값은 보수적으로 소량.
- 해시 또는 세트 연관 구조로 pageid를 색인 — direct-mapped 충돌 문제를 함께 해소.
- `dirty` 개념 없음. append 경로가 절대 이 캐시를 쓰지 않으므로 P2의 가드 사유(dirty 슬롯 보호)와
  충돌하지 않는다.
- 진입점: `logpb_copy_page`가 기존 `log_Pb.buffers` 미스 시, 파일을 읽기 **전에** 이 캐시를
  조회하고, 읽은 뒤 채운다.

**대안 (더 작은 변경)**: 기존 슬롯에 캐싱하되 조건을 `!log_bufptr->dirty` 이고 해당 페이지가
현재 append 윈도우 밖일 때로 한정. 변경량은 작지만 flush 경로와의 경합을 새로 증명해야 하므로
권장하지 않는다.

**안전성**: 부록 B 참조. 요약하면 — **현재 append 페이지보다 엄격히 이전인 로그 페이지는
불변(append-only)이므로 무기한 캐시해도 stale 될 수 없다.** 단 부분적으로 채워지는 마지막
페이지는 변할 수 있으므로 **반드시 제외**해야 한다. 이 경계 판정이 이 제안의 유일한 정합성
논점이다.

**위험**
- (중) 경계 조건 오류로 append 중인 페이지를 캐시하면 오래된 내용을 반환할 수 있다. →
  캐시 삽입 시 `pageid < append_lsa.pageid` 를 엄격 부등호로 검사하고, 디버그 빌드에 assert 추가.
- (낮) 메모리 증가. 파라미터로 상한이 명확하므로 관리 가능.
- (낮) TDE 암호화 로그(`log_append.hpp:96` `tde_encrypted`) 처리 — 캐시가 복호화 전/후 중
  어느 형태를 담는지 결정 필요. 기존 파일 읽기 경로가 반환하는 형태를 그대로 담으면 중립.

**검증·계측**
- 기존 통계: `PSTAT_LOG_NUM_IOREADS`(`src/base/perf_monitor.h:303`),
  `PSTAT_LOG_NUM_REPLACEMENTS`(동 `:311`).
- 신규 통계(§6): 버전 경로 전용 fetch 수 / 히트 / 미스 / 아카이브 fetch 수.
- 회귀: `ctest`로 기존 MVCC·복구 스위트 전부. 특히 복구 경로는 `LOG_ISRESTARTED()` 분기를
  건드리므로 crash recovery 테스트가 필수다.

**예상 효과**: 반복되는 버전 체인 읽기에서 디스크 I/O 제거. 네 항목 중 단일 최대 효과로 판단하며,
효과 크기는 §6 계측의 "동일 페이지 재요청 비율"에 비례한다.

---

### 제안 2 — 읽기 경로의 LOG_CS 강제 flush 제거

**대상**: `src/storage/heap_file.c:24965-24975`

**현상**:

```c
  /* make sure prev_version_lsa is flushed from prior lsa list - wake up log flush thread if it's not flushed */
  oldest_prior_lsa = *log_get_append_lsa ();
  if (LSA_LT (&oldest_prior_lsa, previous_version_lsa))
    {
      LOG_CS_ENTER (thread_p);
      logpb_prior_lsa_append_all_list (thread_p);
      LOG_CS_EXIT (thread_p);
      ...
    }
```

읽으려는 버전이 아직 prior list에 있으면 **전역 로그 크리티컬 섹션을 배타 모드로 잡고** 전체
prior list를 append한다. 존재 이유는 `log_get_undo_record`가 prior list를 읽을 수 없기
때문이다 — `log_manager.c:9818-9820`에 그 전제가 assert로 박혀 있다.

**문제의 성질**: 원하는 데이터는 **이미 메모리에 있다.** `LOG_PRIOR_NODE`(`log_append.hpp:91-109`)는
undo 데이터를 별도 버퍼로 들고 있다.

```c
struct log_prior_node
{
  LOG_RECORD_HEADER log_header;
  LOG_LSA start_lsa;
  bool tde_encrypted;
  int data_header_length;
  char *data_header;
  int ulength;
  char *udata;        /* ← undo 데이터 */
  int rlength;
  char *rdata;
  LOG_PRIOR_NODE *next;
};
```

즉 메모리에 있는 값을 읽기 위해 전역 락을 잡고 디스크 파이프라인으로 밀어낸 뒤 버퍼를 거쳐
되읽는 구조다. 순서가 거꾸로다.

**변경안**: prior list 직접 조회 경로를 추가한다.

- `log_Gl.prior_info.prior_lsa_mutex`(`log_append.hpp:126`) 하에
  `prior_list_header`부터 순회하여 `start_lsa == previous_version_lsa` 인 노드를 찾는다.
- 찾으면 `node->udata` / `node->ulength`에서 undo 데이터를 직접 추출하고 `LOG_CS`와 페이지 fetch를
  모두 건너뛴다.
- 못 찾으면(이미 append됨) 기존 경로로 진행. 이때 강제 flush는 불필요하므로 제거 가능.

**위험 — 이 제안이 네 항목 중 가장 높다**
- (높) `node->udata`의 해석이 레코드 타입별로 다르고, 압축(`log_manager.c:9882` `is_zipped`)과
  TDE 암호화가 개입한다. prior list 단계에서 udata가 이미 압축된 형태인지 확인이 필요하며,
  그렇다면 `log_get_undo_record`의 파싱·해제 로직을 **다른 입력 소스에 대해 사실상 두 번째로
  구현**하는 셈이 된다. 중복 구현은 두 경로가 어긋날 때 조용한 오독을 낳는다.
- (중) `prior_lsa_mutex`는 `LOG_CS`보다 좁지만 여전히 전역이고, prior list는 LSA 색인이 없어
  선형 순회다. 리스트는 짧게 유지되도록 설계되어 있으나, 잦은 순회가 append 경로와 경합하면
  **개선이 아니라 악화**가 될 수 있다.

**더 작은 대안 (권장 시작점)**: 강제 flush를 없애지 말고 **범위를 좁힌다.** 현재는 전체 prior
list를 append하는데, 필요한 것은 요청 LSA까지다. 부분 append API가 없다면 신설을 검토한다.
효과는 작지만 위험도 훨씬 낮다.

**계측·전제**: 이 제안은 **"버전 읽기 중 요청 LSA가 prior list에 있는 비율"이 유의미하게 높을
때만** 정당화된다. 구버전 읽기는 대개 오래된 버전을 향하므로 이 비율이 낮을 가능성이 있다.
§6에서 이 비율을 먼저 측정하고, 낮으면 **본 제안을 폐기**한다.

---

### 제안 3 — 홉당 전체 페이지 복사와 스택 버퍼 제거

**대상**: `heap_file.c:24949`, `log_manager.c:9812`, `log_page_buffer.c:1937`

**현상**: P3 — 호출당 최대 32KB 스택, 홉당 최대 16KB memcpy. 실제 필요량은 undo 레코드 하나.

**제약**: `LOG_BUFFER`에 핀/래치가 없어(P3 근거) 진정한 zero-copy는 핀 기구 신설을 요구한다.
따라서 아래 3-A / 3-B만 제안하고, 핀 도입은 범위에서 제외한다.

**변경안 3-A — 스택 버퍼를 스캔 캐시 영역으로 이동 (위험 최소)**

`HEAP_SCANCACHE`에는 이미 재사용 가능한 작업 영역 API가 있다 —
`reserve_area()` / `assign_recdes_to_area()`(`src/storage/heap_file.h:166-167`).
`heap_file.c:24949`의 스택 배열을 이 영역으로 옮기면 호출당 16KB 스택 압박이 사라지고, 스캔 내
반복 호출에서 재할당도 없다. `log_manager.c:9812`는 호출자가 버퍼를 넘기도록 시그니처를 바꾸면
같은 처리가 가능하다.

- 복사량은 줄지 않는다. 스택 사용량과 할당 횟수만 개선된다.
- 위험: 낮음. 순수 리팩터링이며 동작 변화 없음.

**변경안 3-B — 필요한 만큼만 복사**

페이지 전체 대신 undo 레코드 바이트만 복사한다.

1. 레코드 헤더 위치는 LSA offset으로 확정되므로, 먼저 헤더만 복사해 길이를 얻는다.
2. 길이만큼만 2차 복사한다.

- 복잡성: 레코드가 페이지를 걸칠 수 있다(`LOG_READ_ADVANCE_WHEN_DOESNT_FIT`,
  `log_manager.c:9823-9855`). 현재 로직은 "전체 페이지 버퍼"를 전제로 다음 페이지를 같은 버퍼에
  덮어쓰며 진행하므로, 부분 복사로 바꾸면 **걸침 처리 경로를 재작성**해야 한다.
- 위험: 중. 걸침 경계에서 잘못 읽으면 조용한 데이터 오독이다. 페이지 경계에 정확히 걸치는
  레코드를 만드는 단위 테스트가 선행 조건.
- 권장: 3-A를 먼저 넣고, §6 계측에서 memcpy가 유의한 비용으로 확인될 때만 3-B를 진행한다.

**검증**: `unit_tests/` 하위에 로그 레코드 파싱 단위 테스트 추가. 특히 페이지 경계 걸침과
압축 레코드 조합.

---

### 제안 4 — 스캔 캐시에 재구성된 가시 버전 캐싱

**대상**: `HEAP_SCANCACHE`(`src/storage/heap_file.h:142-172`)

**현상**: 같은 OID의 가시 버전을 한 스캔 안에서 여러 번 요구하는 패턴(인덱스 스캔의 재방문,
중첩 루프 조인의 내부 릴레이션, 다중 인덱스 경로)에서 체인을 매번 재순회한다.

**설계 선례**: 이 구조체는 이미 스캔 로컬 캐시를 갖고 있다 —
`local_cache_handle` / `local_cache_vpid`(`heap_file.h:160-161`), `read_mode`(`:162`).
따라서 스캔 캐시에 소형 캐시를 추가하는 것은 기존 설계 방향과 일관된다.

**변경안**: 단일 엔트리 캐시로 시작한다.

- `HEAP_SCANCACHE`에 `(OID, RECDES)` 1쌍 + 유효 플래그를 추가.
- `heap_get_visible_version_from_log()` 진입 시 OID가 일치하면 즉시 반환, 성공 시 갱신.
- 저장 공간은 기존 `reserve_area()` 영역을 재사용(제안 3-A와 자연히 결합).

**정합성 — 가장 중요한 제약**: 캐시는 **하나의 스냅샷 안에서만** 유효하다. 스캔 캐시는
`mvcc_snapshot`(`heap_file.h:157`) 하나를 보유하므로 스캔 캐시 수명으로 스코프를 한정하면
충분하다. 단 스캔 캐시가 스냅샷을 바꿔 재사용되는 경로가 있는지 확인하고, 있다면 그 지점에서
반드시 무효화해야 한다(`heap_scancache_start` / `heap_scancache_end` 계열 점검 필요).

**위험**
- (낮) 단일 엔트리이므로 메모리 증가 무시 가능.
- (중) 스냅샷 스코프 위반 시 **잘못된 버전을 반환**한다 — 기능 버그. 무효화 지점 누락이
  유일한 실질 위험이므로, 스냅샷 교체 경로를 코드로 전수 확인한 뒤 착수한다.

**검증·계측**: 신규 통계로 히트율 측정. 히트율이 낮으면 다중 엔트리로 확장하지 않고 그대로 둔다
(단일 엔트리는 비용이 거의 없으므로 유지해도 무해).

---

## 5. 우선순위와 단계

| 순서 | 항목 | 근거 |
|------|------|------|
| 0 | **계측 (§6)** | 아래 모든 판단의 전제 |
| 1 | 제안 3-A (스택 버퍼 이동) | 위험 최소, 순수 리팩터링, 제안 4의 기반 |
| 2 | 제안 1 (읽기 캐시) | 최대 효과. 단 §6에서 재요청 비율 확인 후 |
| 3 | 제안 4 (단일 엔트리 캐시) | 저비용. 스냅샷 무효화 지점 전수 확인 선행 |
| 4 | 제안 3-B (부분 복사) | §6에서 memcpy 비용이 유의할 때만 |
| 5 | 제안 2 (LOG_CS) | prior list 히트 비율이 높을 때만. 낮으면 폐기 |

각 단계는 독립적으로 되돌릴 수 있고, 온디스크 포맷을 바꾸지 않으므로 업그레이드/다운그레이드
호환성 문제가 없다.

---

## 6. 선행 작업: 계측

**어떤 항목이 실제 비용인지 확인되기 전에는 구현하지 않는다.** 위 §3의 다섯 문제는 코드로
확인된 사실이지만, 각각이 실제 워크로드에서 차지하는 비중은 측정되지 않았다.

### 6.1 추가할 카운터

구버전 읽기 경로 전용으로 다음을 계측한다.

| 지표 | 측정 지점 | 어떤 판단에 쓰이는가 |
|------|----------|---------------------|
| 버전 체인 순회 횟수 | `heap_file.c:24983` 루프 진입 | 이 경로 자체의 빈도 |
| 체인 깊이 분포 | 같은 루프의 반복 수 | 제안 4의 기대 효과 |
| 로그 페이지 fetch 수 (버전 경로) | `heap_file.c:24989` | 제안 1의 분모 |
| 그중 버퍼 히트 / 파일 읽기 / 아카이브 읽기 | `log_page_buffer.c:1934` / `:1945` / `:2045` | **제안 1의 핵심 근거** |
| 동일 pageid 재요청 비율 | 신규 (샘플링) | 제안 1의 효과 상한 |
| prior list 히트 비율 | `heap_file.c:24967` 조건 성립 횟수 | **제안 2의 존폐** |
| memcpy 바이트 총량 | `log_page_buffer.c:1937` | 제안 3-B의 정당성 |

기존 통계 `PSTAT_LOG_NUM_IOREADS` / `PSTAT_LOG_NUM_REPLACEMENTS`
(`src/base/perf_monitor.h:303, 311`)는 전체 로그 I/O를 합산하므로 버전 경로를 분리할 수 없다.
따라서 별도 지표가 필요하다. `log_page_buffer.c:1964`가 이미
`PERF_PAGE_MODE_OLD_LOCK_WAIT`를 세팅하고 있어 계측 훅 자체는 익숙한 패턴으로 추가 가능하다.

### 6.2 재현 워크로드

구버전 체인을 강제로 깊게 만드는 형태가 필요하다.

1. 소수의 행을 반복 UPDATE하여 체인을 깊게 만든다(체인 깊이를 파라미터로).
2. 동시에 오래 유지되는 스냅샷으로 그 행들을 반복 조회한다 —
   구버전 읽기가 실제로 발생하도록 강제.
3. 체인 깊이, 동시 리더 수, 로그 버퍼 크기(`log_buffer_size`)를 축으로 변화시킨다.
4. 아카이브 접근을 유발하는 변형(활성 로그를 넘길 만큼 로그를 생성)을 별도로 둔다.

측정: 조회 지연(p50/p99), §6.1 카운터, 그리고 아카이브 읽기 발생 여부.

### 6.3 빌드·테스트

- 빌드: 프로젝트 표준 경로(CMake 프리셋 또는 `build.sh`)로 debug 구성.
- 회귀: `ctest` 기반 기존 스위트 전체. 제안 1은 `LOG_ISRESTARTED()` 분기에 인접하므로
  **크래시 복구 테스트를 반드시 포함**한다.
- 신규 단위 테스트: 제안 3-B 진행 시 로그 레코드 파싱(페이지 경계 걸침 · 압축 조합).

---

## 7. 범위 밖

**구버전을 전용 slotted undo page로 이전하고 `prev_version_lsa`를 OID로 대체하는 방안**은
읽기 경로 문제 P1~P5를 한 번에 제거한다. version 페이지가 `pgbuf`를 타면 해시 조회, LRU,
private LRU quota를 그대로 얻고, LOG_CS도 아카이브 접근도 사라진다. 방향 자체는 옳다.

그럼에도 이 문서에서 제외하는 이유:

1. **쓰기 증폭이 구조적으로 발생한다.** 현재 설계에서 undo 로그 레코드는 롤백과 복구를 위해
   어차피 기록된다. 그것을 버전 저장소로 재사용하므로 **추가 쓰기 비용이 0**이다. version
   페이지로 옮기면 그 페이지는 영속 데이터 페이지이므로 변경이 WAL 로깅되어야 하고, 옛 이미지를
   version 페이지와 redo 로그에 **두 번** 쓰게 된다. InnoDB가 지불하는 비용이 정확히 이것이다.
   즉 읽기 이득을 쓰기 손실로 사는 거래이며, 쓰기 위주 OLTP에서는 순손실일 수 있다.
2. **범위가 크다.** version 페이지 할당·회수 기구(사실상 rollback segment + purge 재구현),
   복구 경로 추가, DWB 트래픽 증가, 버퍼풀 경쟁이 따라온다. 롤백·undo 복구를 version 페이지
   기준으로 재작성하면 `log_recovery.c`와 `log_rollback` 규모의 변경이 된다.
3. **본 문서의 네 항목이 읽기 이득의 상당 부분을 선취할 가능성이 있다.** 특히 제안 1이
   반복 접근을 흡수하면 P1·P2·P5의 실질 영향이 크게 줄어든다. 그 결과를 보고 전환의 잔여 이득을
   판단하는 것이 합리적 순서다.

따라서 version store 전환은 **§6 계측과 제안 1 적용 이후에 잔여 이득을 근거로 별도 검토**한다.

참고 선례: PostgreSQL의 `zheap`이 반대 방향(힙 내 버전 → undo 기반 version store) 전환을
시도했고 수년의 작업 끝에 사실상 정체됐다. 세부 사정은 다르지만 "버전 저장소를 옮기는 일"의
규모를 보여주는 사례다. 검증된 구현은 InnoDB와 Oracle의 undo tablespace이며, 둘 다 그 대가로
쓰기 증폭과 purge 지연 문제를 안고 운영된다.

---

## 부록 A — 코드 위치 색인

### 읽기 경로

| 위치 | 내용 |
|------|------|
| `src/transaction/mvcc.h:38-46` | `MVCC_REC_HEADER`, `prev_version_lsa`(`:45`) |
| `src/storage/heap_file.c:24943` | `heap_get_visible_version_from_log()` |
| `src/storage/heap_file.c:24949` | 스택 버퍼 #1 (16KB) |
| `src/storage/heap_file.c:24965-24975` | LOG_CS 강제 prior flush |
| `src/storage/heap_file.c:24983` | `prev_version_lsa` 체인 루프 |
| `src/storage/heap_file.c:24989` | `logpb_fetch_page()` 호출 |
| `src/storage/heap_file.c:24996` | `log_get_undo_record()` 호출 |
| `src/storage/heap_file.c:25071` | `heap_get_visible_version()` 진입점 |

### 로그 페이지 버퍼

| 위치 | 내용 |
|------|------|
| `src/transaction/log_page_buffer.c:193-200` | `LOG_BUFFER` — 핀/래치 없음 |
| `src/transaction/log_page_buffer.c:243-253` | `LOG_PB_GLOBAL_DATA` |
| `src/transaction/log_page_buffer.c:381-384` | `logpb_get_log_buffer_index()` — direct-mapped |
| `src/transaction/log_page_buffer.c:851-870` | dirty 로그 페이지 축출 금지 assert |
| `src/transaction/log_page_buffer.c:1739` | `logpb_fetch_page()` |
| `src/transaction/log_page_buffer.c:1762-1779` | LOG_CS + prior append |
| `src/transaction/log_page_buffer.c:1922` | 슬롯 색인 계산 |
| `src/transaction/log_page_buffer.c:1934-1942` | 히트: memcpy + pageid 재확인 |
| `src/transaction/log_page_buffer.c:1945` | 미스: 파일 읽기 |
| `src/transaction/log_page_buffer.c:1952-1962` | **캐싱 가드 (`!LOG_ISRESTARTED()`)** |
| `src/transaction/log_page_buffer.c:2015-2023` | `LOG_CS_ENTER_READ_MODE` |
| `src/transaction/log_page_buffer.c:2030-2056` | 아카이브 fetch 분기 |

### 로그 레코드 · prior list

| 위치 | 내용 |
|------|------|
| `src/transaction/log_manager.c:9799` | `log_get_undo_record()` |
| `src/transaction/log_manager.c:9812` | 스택 버퍼 #2 (16KB) |
| `src/transaction/log_manager.c:9818-9820` | "prior list에 없어야 함" assert |
| `src/transaction/log_manager.c:9822-9856` | 레코드 타입별 파싱, 걸침 처리 |
| `src/transaction/log_manager.c:9882, 9903` | 압축 해제 경로 |
| `src/transaction/log_append.hpp:91-109` | `LOG_PRIOR_NODE` (`udata`, `ulength`) |
| `src/transaction/log_append.hpp:112-129` | `log_prior_lsa_info`, `prior_lsa_mutex` |
| `src/transaction/log_impl.h:121` | `LOGAREA_SIZE` |

### 스캔 캐시 · 통계

| 위치 | 내용 |
|------|------|
| `src/storage/heap_file.h:142-172` | `heap_scancache` |
| `src/storage/heap_file.h:157` | `mvcc_snapshot` |
| `src/storage/heap_file.h:160-162` | `local_cache_handle`, `local_cache_vpid`, `read_mode` |
| `src/storage/heap_file.h:166-167` | `reserve_area()`, `assign_recdes_to_area()` |
| `src/base/perf_monitor.h:303-311` | `PSTAT_LOG_NUM_IOREADS`, `..._REPLACEMENTS` 등 |

---

## 부록 B — 안전성 근거: 로그 페이지 불변성

제안 1(읽기 캐시)의 정합성은 다음 성질에 의존한다.

**주장**: 현재 append 페이지보다 엄격히 이전인 로그 페이지의 내용은 변하지 않는다.

**근거**: 로그는 append-only다. 이미 다 채워져 다음 페이지로 넘어간 페이지에는 더 이상 레코드가
추가되지 않는다. 로그 페이지 버퍼에서 dirty 페이지 축출을 금지하는 코드
(`log_page_buffer.c:851-870`, *"should not happen"* + `assert_release(false)`)도 "쓰기 중인
페이지"와 "완료된 페이지"가 구분되어 다뤄진다는 점을 뒷받침한다.

**반례이자 유일한 예외**: **현재 append 중인 마지막 페이지는 계속 변한다.** 부분적으로 채워진
상태로 flush될 수 있고 이후 같은 페이지에 레코드가 더 붙는다. 또한
`LOGPB_APPENDREC_PARTIAL_FLUSHED_END_OF_LOG` 계열 상태 전이(`log_page_buffer.c:202-210` 주석)에서
EOL 레코드가 임시로 기록되고 나중에 덮이는 경우가 있다.

**따라서 캐시 삽입 조건**:

```
pageid < log_Gl.hdr.append_lsa.pageid    (엄격 부등호)
```

를 만족할 때만 캐시하고, 등호나 그 이상은 절대 캐시하지 않는다. `logpb_fetch_page`가 이미
`append_lsa` / `append.prev_lsa`를 읽어 유사한 경계 판정을 수행하므로(`log_page_buffer.c:1751-1763`),
같은 값을 근거로 판정할 수 있다. 다만 `append_lsa` 읽기의 원자성에 대해 코드에 이미
`/* TODO: fix atomicity issue on x86 */`(`heap_file.c:24966`)라는 주석이 있으므로, 경계 판정에
사용하기 전에 이 값의 읽기 안전성을 별도로 확인해야 한다.

**아카이브 페이지**: 아카이브로 넘어간 페이지는 정의상 완료된 페이지이므로 위 조건을 항상
만족한다. 아카이브 읽기는 비용이 가장 큰 경로이므로 캐시 이득도 가장 크다.
