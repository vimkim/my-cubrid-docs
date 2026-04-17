# CUBRID Sysop (System Operation) 완전 해설

> CUBRID의 `log_sysop_start` / `log_sysop_commit` / `log_sysop_abort`가 어떻게 동작하는지, 왜 이걸로 감싸면 partial failure가 문제가 안 되는지에 대한 상세 해설.
>
> **관련 PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986) — Vacuum-OOS 연동
>
> **소스 참조:** `src/transaction/log_manager.c`, `src/transaction/recovery.c`

---

## 목차

1. [Sysop이란 — 개념부터](#1-sysop이란--개념부터)
2. [내부 자료구조 — TDES와 topops 스택](#2-내부-자료구조--tdes와-topops-스택)
3. [`log_sysop_start` — 무엇을 하는가](#3-log_sysop_start--무엇을-하는가)
4. [Sysop 중 발생하는 WAL 기록](#4-sysop-중-발생하는-wal-기록)
5. [`log_sysop_abort` — 마법이 일어나는 곳](#5-log_sysop_abort--마법이-일어나는-곳)
6. [구체적 시나리오 — OOS chain walk](#6-구체적-시나리오--oos-chain-walk)
7. [왜 partial failure가 문제가 안 되는가](#7-왜-partial-failure가-문제가-안-되는가)
8. [Crash 시 안전성](#8-crash-시-안전성)
9. [비용 분석](#9-비용-분석)
10. [다른 DBMS의 비슷한 개념](#10-다른-dbms의-비슷한-개념)
11. [요약](#11-요약)

---

## 1. Sysop이란 — 개념부터

**Sysop (System Operation)** = 사용자 트랜잭션 안에 들어가는 **중첩된 원자 단위(nested atomic unit)**. C의 `try { ... }` 블록과 비슷한 감각:

```c
log_sysop_start(thread_p);          // try {
  // 여러 페이지에 걸친 수정들...
  // 중간 실패 가능
log_sysop_commit(thread_p);         // } 성공
// 또는
log_sysop_abort(thread_p);          // } 실패 → 시작점으로 되돌리기
```

핵심 속성:

- `start`와 `commit/abort` 사이에서 일어난 **모든 WAL 기록을 하나의 논리 단위로 묶는다**.
- `abort`하면 **중간에 기록된 모든 변경이 물리적으로 되돌려진다** — "없었던 일"이 된다.
- 중첩 가능 (stack 구조) — sysop 안에 sysop 가능.

---

## 2. 내부 자료구조 — TDES와 topops 스택

각 트랜잭션은 `LOG_TDES` (Transaction Descriptor)를 갖고, 그 안에 sysop 스택이 있다:

```c
struct log_tdes {
  LOG_LSA tail_lsa;             // 이 트랜잭션이 마지막으로 쓴 log 레코드의 LSA
  LOG_LSA topop_lsa;            // 현재 진행 중 sysop의 시작 LSA
  struct {
    int last;                   // 스택 top index (-1이면 비어 있음)
    int max;
    LOG_TOPOPS_ADDRESSES *stack; // 배열
  } topops;
  ...
};

struct log_topops_addresses {
  LOG_LSA lastparent_lsa;   // ★ sysop 시작 직전의 tail_lsa — "savepoint"
  LOG_LSA posp_lsa;
};
```

각 트랜잭션이 여러 sysop을 동시에 중첩할 수 있기 때문에 **스택 구조**가 필요하다. 가장 최근에 시작한 sysop이 `topops.stack[topops.last]`에 있다.

---

## 3. `log_sysop_start` — 무엇을 하는가

실제 코드 (`src/transaction/log_manager.c:3605-3661`):

```c
void log_sysop_start (THREAD_ENTRY * thread_p)
{
  LOG_TDES *tdes = LOG_FIND_TDES(LOG_FIND_THREAD_TRAN_INDEX(thread_p));
  tdes->lock_topop();                               // 스택 접근 동기화

  // 스택 공간 확보
  if (tdes->topops.max == 0 || (tdes->topops.last + 1) >= tdes->topops.max)
    logtb_realloc_topops_stack (tdes, 1);

  // ★ 핵심: 현재 tail_lsa를 이 sysop의 "시작점(savepoint)"으로 저장
  tdes->topops.last++;
  LSA_COPY (&tdes->topops.stack[tdes->topops.last].lastparent_lsa,
            &tdes->tail_lsa);
  LSA_COPY (&tdes->topop_lsa, &tdes->tail_lsa);
  ...
}
```

**하는 일은 딱 하나:** "지금 이 순간의 `tail_lsa`를 기억해둔다." 이후 이 sysop 안에서 일어나는 모든 WAL append는 이 기억해둔 LSA 이후에 쌓인다.

| 특성 | 값 |
|---|---|
| 실제 디스크 I/O | **없음** (stack 조작만) |
| 비용 | O(1), mutex 1회 |
| WAL 레코드 기록 | 없음 (commit/abort 때만 기록) |

---

## 4. Sysop 중 발생하는 WAL 기록

`log_sysop_start` ~ `log_sysop_commit/abort` 사이에서 예를 들어 `oos_delete(OOS_A)`를 호출하면:

```
oos_delete 내부:
  1. 대상 페이지 fix + latch
  2. spage_delete(page, slotid)
  3. log_append_undoredo_recdes(thread_p, RVOOS_DELETE, &log_addr,
                                 recdes_of_OOS_A, NULL);
                                 ↑ undo data   ↑ redo data
  4. page dirty 표시
  5. unfix
```

`log_append_undoredo_recdes`가 WAL에 **`RVOOS_DELETE` 타입의 undo/redo 레코드**를 append.

중요:
- **undo data = OOS_A의 원본 레코드 내용** (복원용)
- **redo data = NULL** (이미 삭제했으므로 재적용 시 "삭제" 수행하면 됨)
- 이 레코드의 LSA는 `tdes->tail_lsa`에 저장됨 → `tail_lsa` 전진

여러 번의 `oos_delete` 호출은 각각 `RVOOS_DELETE` 레코드를 WAL에 순차적으로 append한다. sysop 입장에서 이 로그들은 "내 소유"로 추적된다 (왜냐하면 `lastparent_lsa`보다 뒤에 있으므로).

---

## 5. `log_sysop_abort` — 마법이 일어나는 곳

실제 코드 (`src/transaction/log_manager.c:4044-4093`):

```c
void log_sysop_abort (THREAD_ENTRY * thread_p)
{
  LOG_TDES *tdes;
  LOG_REC_SYSOP_END sysop_end;
  log_sysop_end_begin (thread_p, &tran_index, &tdes);

  // Case 1: sysop 시작 이후 아무것도 안 썼으면 no-op
  if (LSA_ISNULL (&tdes->tail_lsa)
      || LSA_LE (&tdes->tail_lsa, &LOG_TDES_LAST_SYSOP (tdes)->lastparent_lsa))
    {
      /* No change. */
    }
  else
    {
      // ★ 핵심 1: 변경사항 롤백
      log_rollback (thread_p, tdes, LOG_TDES_LAST_SYSOP_PARENT_LSA (tdes));

      // ★ 핵심 2: abort를 log에 기록 (recovery용 마커)
      sysop_end.type = LOG_SYSOP_END_ABORT;
      sysop_end.lastparent_lsa = *LOG_TDES_LAST_SYSOP_PARENT_LSA (tdes);
      log_append_sysop_end (thread_p, tdes, &sysop_end, 0, NULL);
    }

  log_sysop_end_final (thread_p, tdes);   // 스택 pop
}
```

핵심은 `log_rollback(thread_p, tdes, lastparent_lsa)`. 이 함수가:

```
1. tdes->tail_lsa부터 시작하여 WAL를 역방향으로 순회
2. 각 로그 레코드에 대해:
   a. lastparent_lsa에 도달했으면 루프 종료
   b. 그 로그 레코드의 rcvindex (예: RVOOS_DELETE) 확인
   c. Recovery 테이블에서 해당 rcvindex의 **undo 핸들러** 조회
      (src/transaction/recovery.c의 RV_fun 배열)
   d. undo 핸들러 실행 — 로그에 저장된 undo data를 사용하여 물리적 상태 역전
3. LOG_COMPENSATE 레코드를 WAL에 append — "이 로그는 undo되었음" 마커
4. tail_lsa 갱신
```

`RVOOS_DELETE`의 경우 `recovery.c:845-849`에 등록된 매핑:

```c
{RVOOS_DELETE, "RVOOS_DELETE", oos_rv_redo_insert /* undo */,
                                oos_rv_redo_delete /* redo */},
```

즉 **`RVOOS_DELETE`를 undo하면 `oos_rv_redo_insert`가 실행** → 삭제된 OOS 레코드가 **다시 삽입**된다. 로그에 저장된 undo data(원본 레코드)를 사용해서.

### 참고: `log_sysop_commit`

대칭적으로 commit은 다음을 수행:
1. `LOG_SYSOP_END_COMMIT` 레코드를 WAL에 append
2. 스택 pop

실제 undo는 수행하지 않음 — 단순히 "이 sysop은 논리적으로 완료됨"을 log에 표시. 이후 변경 사항은 유효하게 유지.

---

## 6. 구체적 시나리오 — OOS chain walk

PR #6986의 코드:

```c
log_sysop_start (thread_p);
error_code = vacuum_cleanup_prev_version_oos (thread_p, helper);
  // 내부에서:
  //   oos_delete(OOS_A)  → WAL: RVOOS_DELETE(undo=OOS_A_record, redo=NULL)
  //   oos_delete(OOS_B)  → WAL: RVOOS_DELETE(undo=OOS_B_record, redo=NULL)
  //   oos_delete(OOS_C)  → FAIL (I/O error)
  //   return ER_FAILED;
if (error_code != NO_ERROR)
  {
    log_sysop_abort (thread_p);
    return error_code;
  }
log_sysop_commit (thread_p);
```

### abort 진행 과정

**abort 직전 상태:**

```
heap slot: prev_version_lsa 여전히 유효 (아직 clear 안 됨)
OOS_A: 삭제됨 (REC_UNKNOWN)
OOS_B: 삭제됨 (REC_UNKNOWN)
OOS_C: 원래 상태 (실패로 안 지워짐)
WAL tail: [..., RVOOS_DELETE(B), RVOOS_DELETE(A), ...이전 기록들...]
                                                  ↑ lastparent_lsa (sysop 시작점)
```

**`log_rollback (thread_p, tdes, lastparent_lsa)` 실행:**

```
1. tail_lsa = RVOOS_DELETE(B) 위치
2. undo 핸들러 oos_rv_redo_insert 실행 → OOS_B 물리적으로 재삽입
   compensate 레코드 append
3. 이전 LSA로 이동 → RVOOS_DELETE(A) 위치
4. undo 핸들러 실행 → OOS_A 재삽입
   compensate 레코드 append
5. 이전 LSA = lastparent_lsa → 루프 종료
```

**abort 후 상태:**

```
heap slot: prev_version_lsa 그대로 (건드리지 않음)
OOS_A: 재삽입됨 (원래 상태 복원)
OOS_B: 재삽입됨 (원래 상태 복원)
OOS_C: 원래 상태
→ 완벽하게 sysop 시작 이전 상태
```

### 다음 vacuum 재시도

chain walk가 OOS_A, OOS_B, OOS_C를 정상적으로 발견 → `oos_delete` 재시도 → 이번엔 성공 (I/O 에러가 일시적이었다면).

**중요:** 재시도가 "이미 지워진 것을 또 지우려는" 상황이 발생하지 않는다. Sysop abort로 상태가 시작 이전과 **구별 불가능**하게 복원되므로.

---

## 7. 왜 partial failure가 문제가 안 되는가

### Sysop 없을 때 — Livelock 시나리오

```c
// Sysop 없이 구현하면:
oos_delete(A)  → 성공, A는 이미 사라짐
oos_delete(B)  → 실패
error_code 반환 → 상위에서 처리
```

**문제:** A는 사라졌는데 heap slot의 `prev_version_lsa`는 여전히 A를 가리키는 undo 레코드로 향한다. 다음 vacuum은 A의 undo 레코드를 읽고 "A의 OID로 `oos_delete` 해야지" → A는 이미 없음 → 또 오류 → **영원한 livelock**.

### Sysop 있을 때 — 깨끗한 재시도

```c
log_sysop_start
oos_delete(A)  → 성공
oos_delete(B)  → 실패
log_sysop_abort  → A 재삽입 (마치 안 한 것처럼)
```

**상태:** **"아무것도 안 일어난 것"과 구별 불가**. 다음 vacuum은 깨끗하게 처음부터 재시도 가능.

### 핵심 원칙

Sysop이 제공하는 것은 **"all or nothing" 의미론**:

```
log_sysop_start
  변경1
  변경2
  변경3  ← 여기서 실패해도
log_sysop_abort  → 변경1, 변경2도 모두 되돌려진다
```

이 원자성 덕분에 호출자는 "실패 시 중간 상태를 수습해야 한다"는 고민에서 해방된다. 단순히 `abort` 한 번 호출하면 된다.

---

## 8. Crash 시 안전성

서버가 sysop 중간에 crash하면?

### Crash 시점에 따른 시나리오

| Crash 시점 | 처리 |
|---|---|
| sysop_start 이전 | 문제 없음. sysop 자체가 시작된 적 없음. |
| sysop 중간 (아직 commit 안 됨) | Recovery가 WAL을 읽다가 매칭되는 `LOG_SYSOP_END_COMMIT`이 없음을 확인 → "미완료 sysop"으로 판단 → 해당 범위의 log를 **undo로 roll-forward** 과정에서 되돌림. 사용자 transaction abort와 동일한 메커니즘으로 처리. |
| sysop_commit 직후 | commit 레코드가 WAL에 persist되었으면 이후 redo로 복구. persist 안 되었으면 위 케이스와 동일 처리. |

### WAL 규율의 역할

모든 경우에 **WAL 규율(Write-Ahead Logging)** 덕분에 일관성 유지:

1. **페이지 변경 이전에 log 기록** — "log에 안 보이는 변경"은 존재할 수 없음.
2. **Log는 순차적으로 기록** — tail_lsa 기반 역순 순회가 의미 있음.
3. **각 log 레코드는 자립적(self-contained)** — undo data를 들고 있어 독립적으로 역전 가능.

이 세 가지 속성이 sysop을 가능하게 하는 기반.

---

## 9. 비용 분석

| 작업 | 비용 |
|---|---|
| `log_sysop_start` | O(1), mutex 한 번 |
| sysop 내부 로그 append | 변경 한 건당 log buffer write 한 번 (원래 수행할 작업) |
| `log_sysop_commit` | O(1) + `LOG_SYSOP_END_COMMIT` 레코드 한 번 append |
| `log_sysop_abort` | **O(n)** — sysop 내부 로그 건수 n에 비례. 각 undo 핸들러 실행 + compensate 레코드 append |

### 실전 비용

- **실전에서 abort는 드물다** — 실제 에러 발생 시에만 호출됨.
- **정상 경로는 commit** — `start + commit` = 사실상 O(1) 두 번.
- **기대 비용은 거의 무시할 수준** — log buffer에 작은 마커 레코드 추가하는 것 외 추가 I/O 없음.

PR #6986의 경우 sysop을 거는 곳이 REC_HOME + OOS, REC_RELOCATION + OOS, prev_version 체인 정리 경로뿐이라 정상 vacuum 처리량에 거의 영향 없음.

---

## 10. 다른 DBMS의 비슷한 개념

| DBMS | 대응 개념 | 비교 |
|---|---|---|
| PostgreSQL | **subtransaction** (`SAVEPOINT` + `ROLLBACK TO SAVEPOINT`) | 개념적으로 유사. SQL 레벨 노출. |
| Oracle | **savepoint** | SQL 레벨 노출. 내부적으로는 유사한 스택 + undo 메커니즘. |
| MySQL / InnoDB | **savepoint** + **mini-transaction (mtr)** | **mtr이 CUBRID sysop에 가장 가깝다.** mtr은 여러 페이지 수정을 하나의 원자 단위로 묶고 redo 로그를 batch flush. |

### CUBRID sysop의 특징

**Recovery index별 undo 핸들러**와 결합되어 동작한다는 점이 핵심 — 각 로그 타입이 자기 자신을 되돌릴 방법을 안다 (`recovery.c`의 `RV_fun[]` 테이블).

이 덕분에 sysop abort가 **"그냥 log를 역방향으로 순회 + 각 undo 핸들러 실행"**이라는 단순한 알고리즘으로 구현된다. 복잡한 transaction graph 추적이나 dependency analysis가 불필요.

---

## 11. 요약

### 핵심 아이디어

- **sysop = 중첩 savepoint** — 시작 LSA를 기억하고, abort 시 그 지점까지 물리적 변경을 WAL undo로 되돌린다.

### 구현 핵심

```
TDES의 topops 스택에 lastparent_lsa 저장
  ↓
abort가 log_rollback(..., lastparent_lsa) 호출
  ↓
역방향 순회하며 undo 핸들러 실행
  ↓
시작 이전 상태로 원자적 복원
```

### Partial failure 해결 원리

중간 실패 시 이미 성공한 부분이 자동 복원되어 **"시도 안 한 상태"와 동치**가 됨. 다음 재시도가 깨끗하게 가능.

### 추상화의 가치

**WAL + undo 핸들러 테이블**이 결합되어 복잡성이 프레임워크 안에 숨음 — 호출자는 `log_sysop_start / commit / abort`만 신경 쓰면 됨. 각 operation 개발자는 자기 로직의 undo 핸들러만 정확히 구현하면 sysop 무료로 활용 가능.

### PR #6986에서의 활용

| 호출 지점 | 용도 |
|---|---|
| `vacuum_heap_record` (REC_HOME + OOS) | heap slot 삭제 + 여러 OOS 삭제를 원자 단위로 |
| `vacuum_heap_record` (REC_RELOCATION + OOS) | 기존 sysop 내부에 OOS 삭제 추가 |
| `vacuum_heap_record` (prev-version cleanup) | chain walk 중 연쇄 OOS 삭제를 원자 단위로 |
| `vacuum_heap_record_insid_and_prev_version` | prev-version OOS 정리 + INSID/prev_lsa clear를 원자 단위로 |
| `heap_update_home` (SA_MODE eager cleanup) | 해당 없음 — SA_MODE는 non-MVCC라 sysop 없이 직접 호출 |

모든 호출 지점에서 partial failure 시 `log_sysop_abort`로 깨끗하게 되돌려진다. 이 덕분에 PR의 chain walker는 "중간에 실패하면 상위로 error 전파만 하면 됨"이라는 단순한 계약으로 구현 가능.

---

**관련 문서:**
- [PR-6986-explanation.md](PR-6986-explanation.md) — PR 전체 변경 사항 친절 해설
- [PR-6986-QnA.md](PR-6986-QnA.md) — 예상 Q&A
- CUBRID 소스: `src/transaction/log_manager.c`, `src/transaction/recovery.c`
