# PR #6986 — Forward-Walk 설계에서의 Dangling OOS 분석

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**JIRA:** [CBRD-26668]
**HEAD:** `31e6e9dc6`
**작성일:** 2026-04-20
**이전 버전과의 관계:** 이 문서는 2026-04-20의 forward-walk 재설계를 반영한 **전면 개정판**이다. 이전 리비전(2026-04-17)은 `vacuum_heap_record`의 REMOVE 경로만 OOS를 정리하므로 prev-version 체인 누수가 발생한다고 결론지었다(P1-P3). 그 결론은 신 설계에서 대부분 해소되었다.

**핵심 질문:** "SERVER_MODE vacuum이 모든 도달 불가능한 OOS를 정리하는가?"

**과거 답변(2026-04-17):** No — 네 가지 누수 경로가 있다(P1 UPDATE→DELETE prev-version 누수, P2 livelock, P3 REC_BIGONE, SA_MODE DELETE 범위 외).

**현재 답변(2026-04-20):** 가장 중요한 두 경로(P1, P2)는 forward-walk 재설계로 **해소되었다.** P3는 상태 유지, SA_MODE DELETE는 여전히 범위 외.

---

## 1. 배경 요약 — 이전 분석의 P1~P3

이전 리비전은 다음과 같이 결론을 내렸다.

- **P1 (Dangling OOS):** `vacuum_heap_record`의 REMOVE 경로가 현재 heap 레코드만 정리하고 `prev_version_lsa` 체인을 따라가지 않는다. UPDATE + DELETE가 같은 vacuum pass에 threshold를 넘으면 구버전 OOS가 orphan.
- **P2 (Livelock):** `vacuum_cleanup_prev_version_oos`가 체인 내 중간 `oos_delete` 실패 시 부분적으로 삭제된 상태로 에러 반환. 재시도 시 "이미 삭제된 슬롯"에 대해 다시 삭제 시도 → 영구 실패.
- **P3 (REC_BIGONE + OOS):** Invariant가 debug assert로만 강제되므로 release build에서 위반 시 조용한 누수.

주된 수정 권장은 "`vacuum_cleanup_prev_version_oos`를 REMOVE 경로에서도 호출하고 sysop으로 감싸라"였다.

이 권장은 초기 M2a 구현(commit `6d41132a7`)에서 부분 채택되었으나, 이후 report(2026-04-17)가 다시 L1 문제를 발견하여 "호출자 가드가 함수 의도를 방해"하는 구조적 결함을 지적했다.

Commit `f912b720c`는 이 모든 문제를 한 번에 해결하는 **근본적 재설계**를 수행했다: 백워드 체인 워커를 완전히 제거하고 forward walk로 전환.

---

## 2. Forward-Walk 설계가 각 누수 경로에 대해 어떻게 동작하는가

### 2.1 P1 (UPDATE → DELETE prev-version 누수): CLOSED BY CONSTRUCTION

#### 구 시나리오

```sql
UPDATE t SET oos_col = 'NEW' WHERE id = 1;   -- heap v2 = OOS_B, undo(v1 = OOS_A)
DELETE FROM t WHERE id = 1;                   -- DELID on v2
COMMIT;
```

가장 오래된 스냅샷이 이 두 작업을 straddle하지 않으면 다음 vacuum에서 `VACUUM_RECORD_REMOVE`가 발동. 구 설계의 REMOVE 경로는 v2의 OOS_B만 삭제하고 v1의 OOS_A는 영구 누수.

#### 신 설계의 동작

`vacuum_process_log_block`이 블록을 forward로 순회하며 각 MVCC 힙 로그 레코드에 대해 다음을 수행:

- **t_update**: UPDATE의 `RVHF_UPDATE_NOTIFY_VACUUM` 로그 레코드. undo payload = v1 recdes(HAS_OOS=1, OOS_A). Forward walk가 inline 블록 진입 → `heap_recdes_contains_oos(&undo)` = true → `vacuum_forward_walk_delete_oos` → OOS_A 삭제.
- **t_delete**: DELETE의 `RVHF_MVCC_DELETE_MODIFY_HOME` 로그 레코드. undo payload = v2 recdes(HAS_OOS=1, OOS_B). Forward walk → OOS_B 삭제.
- 이후 `vacuum_heap` 단계에서 `vacuum_heap_record` REMOVE 경로가 heap 슬롯을 제거. 현재 버전의 OOS는 이미 forward walk에서 삭제되었을 수 있고, 현재 `vacuum_heap_oos_delete`가 다시 시도하면 `oos_delete`가 `S_DOESNT_EXIST`를 반환(수용 가능 경로) 또는 현재 버전의 다른 OOS(있다면)를 정상 삭제.

**판정: CLOSED.** 각 과거 버전은 자신의 MVCC 힙 로그 레코드 처리 시점에 정리된다. 현재 레코드의 HAS_OOS 상태가 무관해지므로 이전의 L1 엣지 케이스도 동시에 해소.

### 2.2 P2 (Livelock on partial chain cleanup): CLOSED

#### 구 시나리오

체인 `{OOS_A, OOS_B, OOS_C}` 처리 중 OOS_B에서 실패 → partial 삭제 → 재시도 시 이미 없는 OOS_A에 대해 `spage_get_record`가 `S_DOESNT_EXIST` → 영구 실패.

#### 신 설계의 동작

신 설계에는 더 이상 "체인 순회"가 없다. 각 로그 레코드에 대한 sysop 범위는 **"undo 1개의 OOS OID들을 하나의 단위로 삭제"**이며, 실패 시 `log_sysop_abort`가 그 undo 내의 부분 삭제를 깨끗이 롤백한다.

```c
log_sysop_start (thread_p);
int oos_err = vacuum_forward_walk_delete_oos (thread_p, &undo_recdes, &oos_vfid);
if (oos_err == NO_ERROR)
  log_sysop_commit (thread_p);
else
  log_sysop_abort (thread_p);
```

부분 실패가 발생하면:

- `log_sysop_abort`가 `RVOOS_DELETE`의 undo를 역순 적용 → 이미 삭제된 청크들을 복원.
- `er_clear()` 후 vacuum block 처리는 계속 진행 (해당 undo에 대한 OOS 정리만 skip).
- 다음 vacuum 사이클에서 해당 로그 블록이 재처리될 수 있으며, 같은 상태에서 재시도되므로 livelock 없이 정상 진행 가능.

핵심 차이: 구 설계는 `oos_delete`별로 개별 로깅되어 sysop 밖에 "half-committed" 상태가 남았으나, 신 설계는 sysop 경계 안에서만 변경이 일어나므로 all-or-nothing.

**판정: CLOSED.**

### 2.3 P3 (REC_BIGONE + OOS 불변식): 상태 유지

#### 구 시나리오

`vacuum_heap_record`의 REC_BIGONE 분기가 OOS를 처리하지 않으며 debug `assert`만 존재. 불변식 위반 시 release build에서 조용한 누수.

#### 신 설계의 동작

Forward walk는 MVCC 힙 로그 레코드의 undo payload를 REC_HOME 형식으로 해석한다(vacuum.c:3654: `undo_recdes.type = REC_HOME`). REC_BIGONE 관련 경로는 `vacuum_heap_record` 내부에 있으며 신 설계 변경사항에서 건드리지 않았다.

**판정: 상태 유지.** 신 설계는 REC_BIGONE 불변식 방어를 개선하지 않았지만 악화시키지도 않았다.

**권장 조치(PR-6986-report.md L3):** `assert`를 `assert_release`로 업그레이드하거나 `ER_FAILED` 반환. non-blocker.

---

## 3. 새 설계의 MVCC 안전성 증명

`PR-6986-explanation.md` §8과 동일한 내용을 누수 분석 관점에서 재구성한다.

### 3.1 불변식 1 — 임계값 불변식

`vacuum_process_log_block` 진입 시 설정:

```c
MVCCID threshold_mvccid = log_Gl.mvcc_table.get_global_oldest_visible ();   // vacuum.c:3477
```

블록 내 모든 MVCC 로그 레코드의 MVCCID는 이 임계값보다 오래됨이 debug assert로 검증(vacuum.c:3611-3618).

**의미:** forward walk가 UPDATE_i의 로그 레코드를 처리할 때, UPDATE_i의 MVCCID는 threshold 이전. 모든 활성 스냅샷은 UPDATE_i 이후의 상태만 본다. UPDATE_i 직전의 pre-image(= undo recdes)를 MVCC로 재구성하려는 판독자는 존재할 수 없다.

### 3.2 불변식 2 — OID 분리성 불변식

`heap_attrinfo_insert_to_oos` (heap_file.c:12408-12436, 12972-12981)는 모든 OOS 컬럼에 대해 **매 transform마다 무조건 fresh OID를 할당**한다. 따라서:

- UPDATE의 pre-image가 참조하는 OOS OID (예: OOS_A)
- UPDATE의 post-image가 참조하는 OOS OID (예: OOS_B)

는 **절대 같지 않다.** 서로 다른 힙 버전은 서로 다른 OOS 슬롯을 참조.

**의미:** pre-image의 OID 삭제가 post-image(현재 살아있는 버전)가 참조하는 OOS 슬롯을 건드리지 않는다.

### 3.3 두 불변식의 결합

- 불변식 1: "pre-image를 볼 수 있는 판독자 = 0명."
- 불변식 2: "pre-image OID 삭제 = 현재 버전에 영향 없음."

두 조건이 동시에 성립하므로 forward walk의 `oos_delete`는 안전하다. 판독자는 pre-image를 필요로 하지 않고, 현재 버전의 무결성은 OID 분리성으로 보호된다.

### 3.4 Concurrent vacuum worker

Vacuum 블록은 배타적으로 배분된다(한 블록을 정확히 한 워커가 처리). 서로 다른 블록의 워커가 같은 OOS 페이지에 접근할 가능성은 존재하나, `oos_delete`의 `PGBUF_LATCH_WRITE`가 페이지 단위 직렬화를 보장한다.

### 3.5 Recovery concurrent

`oos_delete`는 vacuum 런타임 경로. recovery replay는 `oos_rv_redo_delete`를 호출하며 이는 `spage_delete`의 idempotent redo. 두 경로는 절대 동시에 실행되지 않는다(recovery 중 vacuum 비활성).

---

## 4. 케이스별 누수 경로 커버 확인

### Case A — INSERT + UPDATE + DELETE (짧은 간격, long reader 없음)

```sql
INSERT INTO t VALUES (1, 'A');    -- heap v1 = OOS_A (HAS_OOS=1)
UPDATE t SET c = 'B' WHERE id=1;  -- heap v2 = OOS_B, undo(v1 = OOS_A)
DELETE FROM t WHERE id=1;         -- undo(v2 = OOS_B)
COMMIT;
```

이전 (long reader 없이) INSID, UPDATE MVCCID, DELETE MVCCID가 동일 vacuum pass에 threshold를 초과.

Vacuum 동작:

- Forward walk:
  - INSERT 로그(`RVHF_MVCC_INSERT`): zero-byte undo → skip.
  - UPDATE 로그(`RVHF_UPDATE_NOTIFY_VACUUM`): undo = v1, HAS_OOS=1 → OOS_A 삭제.
  - DELETE 로그(`RVHF_MVCC_DELETE_MODIFY_HOME`): undo = v2, HAS_OOS=1 → OOS_B 삭제.
- `vacuum_heap` → `vacuum_heap_record` REMOVE: 현재 heap 슬롯 제거. (현재 버전의 OOS는 이미 forward walk에서 처리되었거나, `vacuum_heap_oos_delete`가 재시도 시 no-op/에러 처리.)

**결과: OOS_A, OOS_B 모두 회수. 누수 없음.**

### Case B — 여러 UPDATE 연쇄 + DELETE

```sql
INSERT INTO t VALUES (1, 'v0');
UPDATE t SET c = 'v1' WHERE id=1;  -- OOS_1
UPDATE t SET c = 'v2' WHERE id=1;  -- OOS_2
UPDATE t SET c = 'v3' WHERE id=1;  -- OOS_3
DELETE FROM t WHERE id=1;          -- undo(OOS_3)
```

Forward walk:

- UPDATE1 로그 → undo=v0 (HAS_OOS? 원래 'v0'가 inline 크기라면 HAS_OOS=0, 크다면 1). HAS_OOS=1이면 OOS_0 삭제.
- UPDATE2 로그 → undo=v1, OOS_1 삭제.
- UPDATE3 로그 → undo=v2, OOS_2 삭제.
- DELETE 로그 → undo=v3, OOS_3 삭제.

모든 과거 버전이 각자의 로그 처리 시점에 정리된다. 이 경우가 구 설계에서 가장 누수가 심했던 시나리오(2026-04-17 보고서의 "The leak scales linearly with UPDATE churn before the DELETE" 섹션)인데, 신 설계는 **선형 스케일 누수가 0으로 환원**됨을 보여준다.

**결과: 모든 OOS 회수. 누수 없음.**

### Case C — UPDATE가 모든 OOS 컬럼을 non-OOS로 교체 후 DELETE (구 L1)

```sql
INSERT INTO t VALUES (1, REPEAT(X'AA', 4096));   -- HAS_OOS=1, OOS_A
UPDATE t SET oos_col = NULL WHERE id = 1;         -- HAS_OOS=0 (new)
DELETE FROM t WHERE id = 1;                       -- undo(post-UPDATE = HAS_OOS=0)
```

구 설계: 현재 레코드 HAS_OOS=0 → 가드 차단 → OOS_A 누수.

신 설계 Forward walk:

- UPDATE 로그 → undo = v1 (HAS_OOS=1, OOS_A) → OOS_A 삭제.
- DELETE 로그 → undo = v2 (HAS_OOS=0) → `heap_recdes_contains_oos(undo)` = false → inline 블록 skip.
- `vacuum_heap_record` REMOVE: 현재 레코드 HAS_OOS=0이므로 `vacuum_heap_oos_delete` 호출 안 됨. 정상.

**결과: OOS_A 회수. 구 L1 누수 완전 해소.**

### Case D — REC_RELOCATION 연쇄

heap page fragmentation으로 UPDATE가 원래 slot에 들어가지 못해 RELOCATION 발생. 이 경우 heap 레이아웃은 다음과 같이 변한다.

```
slot 5 (home): REC_RELOCATION → slot 10 (newhome)
slot 10: REC_NEWHOME with OOS_B
```

UPDATE는 여전히 `RVHF_UPDATE_NOTIFY_VACUUM` 로그를 기록하며, undo payload에는 원래 slot의 recdes가 담긴다. Forward walk는 record_type에 민감하지 않고 HAS_OOS 플래그만 본다 (undo_recdes.type = REC_HOME으로 해석).

**결과: RELOCATION 발생 여부와 무관하게 OOS 회수. 단 이 시나리오에 대한 스트레스 회귀 테스트는 L4로 여전히 추가 필요.**

---

## 5. 여전히 남은 범위 외 경로

### 5.1 SA_MODE DELETE (L2)

#### 설명

SA_MODE는 `is_mvcc_op=false`로 DML을 수행하며, DELETE는 heap 슬롯을 즉시 제거하되 OOS는 건드리지 않는다. SA_MODE에서는 vacuum이 no-op(standalone utility에 vacuum 워커 없음).

```c
// test_oos_sql_eager_cleanup.cpp 라인 19-22
// "SA_MODE sets is_mvcc_op=false for all DML. DELETE physically removes the heap
//  slot without cleaning OOS data. Vacuum is a no-op in SA_MODE."
```

본 PR은 UPDATE eager cleanup(`heap_update_home_delete_replaced_oos`)은 추가했으나 DELETE eager cleanup은 없다. `oos_delete`의 grep 결과 SA_MODE DELETE 경로에서의 호출은 존재하지 않는다.

#### 영향

loaddb, unloaddb, restoredb 등 standalone utility에서 DELETE를 수행하면 OOS 파일이 지속 증가.

#### 권장

후속 JIRA로 분리. `heap_delete_logical`의 non-MVCC branch에 eager OOS cleanup 추가 필요. PR 설명서에 "SA_MODE DELETE는 범위 외" 명시 권장.

### 5.2 REC_BIGONE + OOS 공존 (L3)

§2.3 및 `PR-6986-report.md` L3 참조. invariant 위반 시 release build에서 조용한 누수. `assert_release` 업그레이드 권장.

### 5.3 테스트 갭 (L4)

RELOCATION 누적 워크로드에 대한 직접 회귀 테스트 부재. §4 Case D의 이론적 커버리지는 있으나 실측 회귀 테스트가 없다. T3.4 후속 작업.

---

## 6. Scenarios that are clean (변경 없음)

구 리비전과 동일하게 다음 경로는 clean.

| 시나리오 | 경로 | OOS cleanup |
|---|---|---|
| INSERT + DELETE + vacuum | `VACUUM_RECORD_REMOVE` → `vacuum_heap_record` + forward walk | 현재/과거 모두 회수 |
| INSERT + UPDATE + rollback | heap undo가 v1 복원, `oos_insert` undo가 OOS_B 롤백 | OOS_A 보존, OOS_B 롤백 |
| INSERT + UPDATE + vacuum (INSID pass만 먼저) | forward walk가 UPDATE undo에서 OOS_A 삭제 | OOS_A 회수 |
| Crash mid-vacuum sysop | Recovery undo가 sysop 내 `RVOOS_DELETE` 레코드 역순 실행 | Atomic |
| REC_RELOCATION + OOS (REMOVE) | forward walk + `vacuum_heap_record` REMOVE | 현재/과거 모두 회수 |

---

## 7. 요약

| 경로 | 2026-04-17 판정 | 2026-04-20 판정 |
|---|---|---|
| UPDATE → DELETE prev-version (P1) | ❌ 누수 | **CLOSED** (forward walk) |
| Livelock on partial chain (P2) | ⚠ 가능 | **CLOSED** (단일 sysop per undo) |
| UPDATE-drops-all-OOS → DELETE (구 L1) | ❌ 누수 (블로커) | **CLOSED** (forward walk) |
| REC_BIGONE + OOS (P3/L3) | ⚠ 조용한 누수 가능 | 상태 유지 (non-blocker) |
| SA_MODE DELETE (L2) | ❌ 범위 외 | 상태 유지 (범위 외) |
| RELOCATION 누적 (L4) | ⚠ 테스트 갭 | 상태 유지 (non-blocker) |

**짧은 답변:** 주요 경로의 OOS 누수는 forward-walk 재설계로 해결되었다. 남은 이슈는 범위 외(L2) 또는 방어 강화 수준(L3/L4).

**사용자 질문 "SERVER_MODE vacuum이 모든 도달 불가능한 OOS를 정리하는가?"에 대한 갱신 답변:** SERVER_MODE MVCC 경로에 대해서는 YES. SA_MODE는 여전히 범위 외.

---

**관련 문서:**

- `PR-6986-explanation.md` — 신 설계 전체 설명.
- `PR-6986-QnA.md` — 설계 상세에 대한 Q&A.
- `PR-6986-report.md` — L1-L4 재평가.

**작성자:** Claude Opus 4.7 (1M context) via Daehyun Kim
