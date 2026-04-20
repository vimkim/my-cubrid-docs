# CUBRID Sysop (System Operation) 완전 해설

> CUBRID의 `log_sysop_start` / `log_sysop_commit` / `log_sysop_abort`가 어떻게 동작하는지, 왜 이걸로 감싸면 partial failure가 문제가 안 되는지에 대한 상세 해설.
>
> **관련 PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986) — Vacuum-OOS 연동
>
> **HEAD commit:** `31e6e9dc6`
>
> **재작성일:** 2026-04-20 (§11의 PR #6986 활용 테이블을 forward-walk 재설계 기준으로 전면 갱신)
>
> **이전 버전과의 관계:** §1~§10의 sysop 원리 해설은 변동 없음. §11 호출 지점 표와 §12 새 호출 지점의 sysop 불변식 분석이 신설/갱신됐다.
>
> **소스 참조:** `src/transaction/log_manager.c`, `src/transaction/recovery.c`, `src/query/vacuum.c`

---

## 목차

1. [Sysop이란 — 개념부터](#1-sysop이란--개념부터)
2. [내부 자료구조 — TDES와 topops 스택](#2-내부-자료구조--tdes와-topops-스택)
3. [`log_sysop_start` — 무엇을 하는가](#3-log_sysop_start--무엇을-하는가)
4. [Sysop 중 발생하는 WAL 기록](#4-sysop-중-발생하는-wal-기록)
5. [`log_sysop_abort` — 마법이 일어나는 곳](#5-log_sysop_abort--마법이-일어나는-곳)
6. [구체적 시나리오 — OOS forward-walk 삭제](#6-구체적-시나리오--oos-forward-walk-삭제)
7. [왜 partial failure가 문제가 안 되는가](#7-왜-partial-failure가-문제가-안-되는가)
8. [Crash 시 안전성](#8-crash-시-안전성)
9. [비용 분석](#9-비용-분석)
10. [다른 DBMS의 비슷한 개념](#10-다른-dbms의-비슷한-개념)
11. [PR #6986에서의 활용](#11-pr-6986에서의-활용)
12. [Forward-walk sysop 불변식 유지 방식](#12-forward-walk-sysop-불변식-유지-방식)
13. [요약](#13-요약)

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
  LOG_LSA lastparent_lsa;   // sysop 시작 직전의 tail_lsa — "savepoint"
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

  // 핵심: 현재 tail_lsa를 이 sysop의 "시작점(savepoint)"으로 저장
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
                                 // undo data    // redo data
  4. page dirty 표시
  5. unfix
```

`log_append_undoredo_recdes`가 WAL에 **`RVOOS_DELETE` 타입의 undo/redo 레코드**를 append.

중요:
- **undo data = OOS_A의 원본 레코드 내용** (복원용)
- **redo data = NULL** (이미 삭제했으므로 재적용 시 "삭제" 수행하면 됨)
- 이 레코드의 LSA는 `tdes->tail_lsa`에 저장됨 → `tail_lsa` 전진

여러 번의 `oos_delete` 호출은 각각 `RVOOS_DELETE` 레코드를 WAL에 순차적으로 append한다. 다중 청크 OOS 레코드라면 청크당 한 개씩. sysop 입장에서 이 로그들은 "내 소유"로 추적된다 (왜냐하면 `lastparent_lsa`보다 뒤에 있으므로).

---

## 5. `log_sysop_abort` — 마법이 일어나는 곳

실제 코드 (`src/transaction/log_manager.c:4044-4093`):

```c
void log_sysop_abort (THREAD_ENTRY * thread_p)
{
  LOG_TDES *tdes;
  LOG_REC_SYSOP_END sysop_end;
  log_sysop_end_begin (thread_p, &tran_index, &tdes);

  if (LSA_ISNULL (&tdes->tail_lsa)
      || LSA_LE (&tdes->tail_lsa, &LOG_TDES_LAST_SYSOP (tdes)->lastparent_lsa))
    {
      /* No change. */
    }
  else
    {
      log_rollback (thread_p, tdes, LOG_TDES_LAST_SYSOP_PARENT_LSA (tdes));
      sysop_end.type = LOG_SYSOP_END_ABORT;
      sysop_end.lastparent_lsa = *LOG_TDES_LAST_SYSOP_PARENT_LSA (tdes);
      log_append_sysop_end (thread_p, tdes, &sysop_end, 0, NULL);
    }

  log_sysop_end_final (thread_p, tdes);
}
```

핵심은 `log_rollback(thread_p, tdes, lastparent_lsa)`. 이 함수가:

```
1. tdes->tail_lsa부터 시작하여 WAL를 역방향으로 순회
2. 각 로그 레코드에 대해:
   a. lastparent_lsa에 도달했으면 루프 종료
   b. 그 로그 레코드의 rcvindex (예: RVOOS_DELETE) 확인
   c. Recovery 테이블에서 해당 rcvindex의 undo 핸들러 조회
   d. undo 핸들러 실행
3. LOG_COMPENSATE 레코드를 WAL에 append
4. tail_lsa 갱신
```

`RVOOS_DELETE`의 경우 `recovery.c:845-849`에 등록된 매핑:

```c
{RVOOS_DELETE, "RVOOS_DELETE", oos_rv_redo_insert /* undo */,
                                oos_rv_redo_delete /* redo */},
```

즉 **`RVOOS_DELETE`를 undo하면 `oos_rv_redo_insert`가 실행** → 삭제된 OOS 레코드가 **다시 삽입**된다.

### 참고: `log_sysop_commit`

대칭적으로 commit은 다음을 수행:
1. `LOG_SYSOP_END_COMMIT` 레코드를 WAL에 append
2. 스택 pop

---

## 6. 구체적 시나리오 — OOS forward-walk 삭제

PR #6986 (재설계 이후)의 코드 — `src/query/vacuum.c:3697-3714`:

```c
log_sysop_start (thread_p);

int oos_err = vacuum_forward_walk_delete_oos (thread_p, &undo_recdes, &oos_vfid);
  // 내부에서 다중 청크 OOS 레코드일 경우:
  //   oos_delete(OOS_A)  → WAL: RVOOS_DELETE(undo=OOS_A_chunk, redo=NULL)
  //   oos_delete(OOS_B)  → WAL: RVOOS_DELETE(undo=OOS_B_chunk, redo=NULL)
  //   oos_delete(OOS_C)  → FAIL (I/O error)
  //   return error_code;

if (oos_err == NO_ERROR)
  {
    log_sysop_commit (thread_p);
  }
else
  {
    log_sysop_abort (thread_p);
    ...
    er_clear ();
    /* Do not fail the vacuum block; continue processing. */
  }
```

### abort 진행 과정

**abort 직전 상태:**

```
OOS_A: 삭제됨 (REC_UNKNOWN)
OOS_B: 삭제됨 (REC_UNKNOWN)
OOS_C: 원래 상태 (실패로 안 지워짐)
WAL tail: [..., RVOOS_DELETE(B), RVOOS_DELETE(A), ...이전 기록들...]
                                                  // lastparent_lsa (sysop 시작점)
```

**`log_rollback` 실행:**

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
OOS_A: 재삽입됨
OOS_B: 재삽입됨
OOS_C: 원래 상태
→ sysop 시작 이전 상태로 완전 복원
```

### 다음 vacuum 재시도

동일 MVCC 힙 로그 레코드를 다시 방문하면(또는 다음 vacuum cycle에서 해당 로그가 다시 순회되면) forward walk가 다시 undo payload의 HAS_OOS를 발견하고 재시도한다. 재시도 시 "이미 지워진 것을 또 지우려는" 상황이 발생하지 않는다. Sysop abort로 상태가 시작 이전과 구별 불가능하게 복원되므로.

---

## 7. 왜 partial failure가 문제가 안 되는가

### Sysop 없을 때 — 누수 시나리오

```c
oos_delete(A)  → 성공, A는 이미 사라짐
oos_delete(B)  → 실패
error_code 반환 → 상위에서 처리
```

**문제:** A의 물리적 삭제는 되었지만 실패 후 재시도 시 A를 다시 삭제하려 하면 `S_DOESNT_EXIST`. 더구나 B는 여전히 남아있어 누수.

### Sysop 있을 때 — 깨끗한 재시도

```c
log_sysop_start
oos_delete(A)  → 성공
oos_delete(B)  → 실패
log_sysop_abort  → A 재삽입
```

"아무것도 안 일어난 것"과 구별 불가. 다음 vacuum cycle에서 깨끗하게 처음부터 재시도.

---

## 8. Crash 시 안전성

| Crash 시점 | 처리 |
|---|---|
| sysop_start 이전 | 문제 없음. sysop 자체가 시작된 적 없음. |
| sysop 중간 (아직 commit 안 됨) | Recovery가 WAL을 읽다가 매칭되는 `LOG_SYSOP_END_COMMIT`이 없음을 확인 → 해당 범위의 log를 undo로 roll-forward 과정에서 되돌림. |
| sysop_commit 직후 | commit 레코드가 WAL에 persist되었으면 이후 redo로 복구. |

WAL 규율(페이지 변경 이전에 log 기록, log 순차 기록, 각 로그는 자립적)이 sysop을 가능하게 하는 기반.

---

## 9. 비용 분석

| 작업 | 비용 |
|---|---|
| `log_sysop_start` | O(1), mutex 한 번 |
| sysop 내부 로그 append | 변경 한 건당 log buffer write 한 번 |
| `log_sysop_commit` | O(1) + `LOG_SYSOP_END_COMMIT` 레코드 한 번 append |
| `log_sysop_abort` | **O(n)** — sysop 내부 로그 건수 n에 비례 |

실전에서 abort는 드물고, 정상 경로는 `start + commit` = 사실상 O(1) 두 번. PR #6986의 forward-walk inline 정리는 HAS_OOS가 참일 때만 sysop에 진입하므로 OOS-less 테이블에서 아예 발동하지 않는다.

---

## 10. 다른 DBMS의 비슷한 개념

| DBMS | 대응 개념 | 비교 |
|---|---|---|
| PostgreSQL | subtransaction (`SAVEPOINT` + `ROLLBACK TO SAVEPOINT`) | 개념적으로 유사. SQL 레벨 노출. |
| Oracle | savepoint | SQL 레벨 노출. 내부적으로 유사한 스택 + undo 메커니즘. |
| MySQL / InnoDB | savepoint + mini-transaction (mtr) | mtr이 CUBRID sysop에 가장 가깝다. |

CUBRID sysop의 특징은 **Recovery index별 undo 핸들러**와 결합되어 동작한다는 점이다. 각 로그 타입이 자기 자신을 되돌릴 방법을 안다 (`recovery.c`의 `RV_fun[]` 테이블).

---

## 11. PR #6986에서의 활용

### 11.1 제거된 호출 지점

다음 지점의 sysop은 `f912b720c`에서 관련 함수와 함께 완전히 제거됐다.

| 과거 호출 지점 | 상태 | 비고 |
|---|---|---|
| `vacuum_heap_record` REMOVE 경로 안쪽의 `vacuum_cleanup_prev_version_oos` 호출용 sysop | 제거됨 | 함수 자체가 사라짐 |
| `vacuum_heap_record_insid_and_prev_version`의 prev-version cleanup sysop | 제거됨 | 이 함수의 chain-walk 책임 자체 사라짐. 현재는 현재 레코드의 INSID/prev_lsa clear만 수행(`src/query/vacuum.c:2213-2378`), sysop 진입 없음 |
| `need_prev_version_oos_cleanup` 트리거 블록 | 제거됨 | 조건식 포함 전체 삭제 |

### 11.2 신규 호출 지점

| 위치 | 용도 |
|---|---|
| `vacuum_process_log_block` forward-walk inline block (`src/query/vacuum.c:3697-3714`) | MVCC 힙 연산(`RVHF_UPDATE_NOTIFY_VACUUM`, `RVHF_MVCC_DELETE_MODIFY_HOME`) undo payload가 HAS_OOS를 담고 있고 블록 VFID 캐시가 OOS file의 존재를 확인한 경우, 다중 청크 `oos_delete` 시퀀스를 단일 sysop으로 묶어 원자화 |

### 11.3 유지된 호출 지점

| 위치 | 용도 |
|---|---|
| `vacuum_heap_record` (REC_HOME + 현재 OOS) (`src/query/vacuum.c:2464-2612`) | 현재 레코드의 OOS 슬롯 삭제를 heap slot 삭제와 원자 단위로 묶음 |
| `vacuum_heap_record` (REC_RELOCATION + OOS) (`src/query/vacuum.c:2496-2550`) | 동일. forward_page 슬롯 삭제 + OOS 삭제를 원자 단위 |
| `vacuum_heap_record` (REC_BIGONE) (`src/query/vacuum.c:2557-2591`) | overflow 레코드 삭제 원자화. OOS와 공존 불가(invariant, `src/query/vacuum.c:2564` assert) |
| `heap_update_home` (SA_MODE eager cleanup) | 해당 없음 — SA_MODE는 non-MVCC라 sysop 없이 직접 호출 |

---

## 12. Forward-walk sysop 불변식 유지 방식

### 12.1 `is_under_sysop` 경계 보증

`vacuum_process_log_block`는 블록 진입 시와 종료 시 모두 `assert(!LOG_FIND_CURRENT_TDES (thread_p)->is_under_sysop())`를 유지한다. 주요 assert 지점:

- `src/query/vacuum.c:3505` — 함수 진입 직후.
- `src/query/vacuum.c:3864, 3868, 3877, 3885` — 루프 및 함수 종료 경계.

forward-walk inline 정리 블록은 이 불변식을 지키도록 **sysop을 시작하자마자 동일 iteration 내에서 commit 또는 abort하고 종료**한다(`src/query/vacuum.c:3698-3714`). 다음 iteration은 sysop-free 상태에서 시작된다.

### 12.2 오류 경로의 sysop 누설 방지

`vacuum_forward_walk_delete_oos`가 에러를 반환하면 즉시 `log_sysop_abort`가 호출되고(`src/query/vacuum.c:3708`), 이후 `er_clear()`로 error stack을 비운 뒤 현재 로그 레코드에 대한 cleanup만 포기한다. 블록 처리는 계속되며, 다음 iteration 진입 전에 sysop은 반드시 닫혀 있다.

### 12.3 방어적 undo 복사와 sysop 경계의 순서

defensive copy는 `log_sysop_start` **이전에** 수행된다(`src/query/vacuum.c:3672-3691`). 이는 sysop 내부에서 `oos_delete`가 WAL append를 일으킬 때 `undo_data`가 가리키는 공유 로그 페이지가 롤오버되어 무효화되는 위험을 차단한다. sysop에 진입한 시점에는 undo_recdes.data가 독립적인 메모리(스택 또는 `db_private_alloc` heap)를 가리키므로 안전하다.

### 12.4 undo 복사 메모리의 수명

`undo_copy_on_heap`이 true일 때 `db_private_free_and_init`은 sysop **이후**에 호출된다(`src/query/vacuum.c:3717-3720`). sysop 중간 실패/성공 어느 경우에도 도달하므로 메모리 누수 없음. `log_sysop_abort`가 호출되어도 heap 메모리는 sysop 복구 범위 밖이므로 영향 없음.

### 12.5 MVCC 임계값 보증

sysop 내부에서 삭제되는 OOS OID는 모두 이미 `threshold_mvccid = log_Gl.mvcc_table.get_global_oldest_visible()` 미만인 MVCC 힙 연산의 undo payload에서 유래한다(`src/query/vacuum.c:3477`, debug assert `src/query/vacuum.c:3611-3618`). 즉 어떤 활성 스냅샷도 해당 OID를 참조하지 않는다. sysop commit 후 재삽입 필요가 없는 정당한 이유다.

### 12.6 OID 분리성

`heap_attrinfo_insert_to_oos`가 OOS 레코드 생성 시 항상 fresh OID를 할당하므로, forward walk가 undo payload에서 꺼내는 pre-image OOS OID 집합은 동일 슬롯의 post-image OOS OID 집합과 disjoint하다. 즉 sysop 내부 `oos_delete`가 현재 살아있는 다른 버전의 OOS 슬롯을 건드리는 일이 없다.

---

## 13. 요약

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

중간 실패 시 이미 성공한 부분이 자동 복원되어 **"시도 안 한 상태"와 동치**가 됨.

### PR #6986에서의 변화 요지

- 백워드 체인 워커가 사용하던 여러 sysop 지점이 사라졌다.
- 새 유일한 신규 sysop 지점은 `vacuum_process_log_block`의 forward-walk inline 정리 블록이다.
- 현재 레코드 정리용 sysop(REC_HOME + OOS, REC_RELOCATION + OOS)은 유지된다.
- sysop 불변식(`is_under_sysop == false` at iteration boundary)은 명시적 assert로 보호된다.
- defensive undo copy, size upper-bound, 일시 실패 시 non-cache 정책이 모두 sysop 경계와 상호작용하면서 L1 누수 해소와 성능 회귀 방지를 동시에 달성한다.

---

**관련 문서:**
- `PR-6986-perf-regression-report.md` — 성능 회귀 재설계 경과
- `PR-6986-proposal.md` — 옵션 제안서 (이력 보존판)
- `PR-6986-response.md` — 누적 리뷰 대응 기록
- CUBRID 소스: `src/transaction/log_manager.c`, `src/transaction/recovery.c`, `src/query/vacuum.c`
