# PR #6986 — PR 본문 상세 버전

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**JIRA:** [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE

이 문서는 PR 본문이 너무 길어져 간소화하면서 옮겨 둔 **상세 Implementation/Safety 설명**이다. 본 PR을 가볍게 훑고자 하는 리뷰어는 PR 본문만 읽으면 충분하며, 본 문서는 깊이 파고들 때만 참고하면 된다.

---

## Description

### 무엇이 문제였나

OOS M1 설계는 다음과 같다.

- **DELETE/UPDATE 시점**: heap 레코드에 MVCC delete ID만 표시한다. OOS 레코드는 즉시 안 지운다 — 동시에 다른 트랜잭션이 과거 버전을 읽고 있을 수 있기 때문.
- **vacuum 시점**: 모든 트랜잭션이 더 이상 그 버전을 못 보게 됐을 때, vacuum이 heap 레코드를 슬롯에서 제거한다. **이때 그 레코드가 가리키던 OOS 레코드도 같이 제거되어야 한다.**

그런데 두 번째 단계의 OOS 정리 로직이 vacuum 쪽에 구현되어 있지 않았다. 결과: OOS 레코드는 한 번 만들어지면 영원히 안 지워지고 OOS 파일이 무한 누적.

### 무엇을 고쳤나

vacuum이 heap 정리를 할 때 그 heap 레코드가 참조하던 OOS OID들을 추출해 `oos_delete()`를 호출하도록 두 군데에 정리 훅을 추가했다.

1. **REMOVE 경로** (`vacuum_heap_record`의 REC_HOME+OOS 분기): 죽은 heap 슬롯을 제거할 때, 그 슬롯의 OOS OID들을 같이 삭제.
2. **forward-walk 경로** (`vacuum_process_log_block`): UPDATE 로그를 vacuum이 정방향으로 훑을 때, UPDATE 직전(pre-image) recdes에 들어 있던 OOS OID들을 추출해 삭제. 더 이상 어디서도 참조되지 않는 옛 OOS를 회수.

그리고 SA_MODE 한정 보강 한 군데(다음 §3) 추가.

## Implementation

### 1. REMOVE 경로 — `vacuum_heap_record`

heap 슬롯이 OOS를 갖고 있고 vacuum 대상이면, 새 헬퍼 `vacuum_heap_record_remove_oos_inline()`(vacuum.c:2450)이 다음을 sysop으로 묶어 처리한다.

1. heap 슬롯 vacuum 로그 기록 (`vacuum_log_redoundo_vacuum_record`).
2. 슬롯의 OOS OID들을 `oos_delete`로 일괄 삭제 (`vacuum_heap_oos_delete`).
3. `log_sysop_commit`. 실패 시 `log_sysop_abort`.

> bulk vacuum 경로 대신 inline-log를 쓰는 이유는 헬퍼의 함수 헤더 주석에 정리되어 있다. 핵심: bulk 경로는 heap-slot vacuum 로그가 sysop 밖에서 emit되어, **sysop commit 후 bulk flush 전에 crash가 나면 OOS는 사라졌는데 heap 슬롯은 여전히 그 OOS를 가리키는 상태가 된다**. inline-log는 양쪽을 같은 sysop 경계에 묶어 이를 방지.

### 2. forward-walk 경로 — `vacuum_process_log_block`

vacuum은 어차피 모든 MVCC 로그 레코드를 정방향으로 훑는다. 이 경로에서 `RVHF_UPDATE_NOTIFY_VACUUM` 로그를 만나면 그 undo 페이로드(= UPDATE 직전의 recdes)를 디코드해, OOS 비트가 켜져 있으면 이전 버전이 가리키던 OOS OID들을 `vacuum_forward_walk_delete_old_oos()`(vacuum.c:3456) 헬퍼로 일괄 삭제한다.

#### 핵심 원리: forward-walk는 "REMOVE 경로가 못 닿는 옛 OID"의 *유일한* 청구권자

본 PR의 OOS 회수는 서로 보완하는 두 경로로 구성된다.
- **REMOVE 경로(§1)**: 살아 있는 heap 슬롯이 vacuum 대상이 됐을 때, **그 슬롯이 현재 가리키고 있는** OOS OID를 삭제.
- **forward-walk 경로(§2)**: UPDATE 로그를 정방향으로 만났을 때, **undo 에만 남아 있는 옛 pre-image OID**를 삭제.

두 경로가 같은 OID 를 두 번 보지 않으려면 한 가지 invariant 에 의존한다.

> **UPDATE OID-disjointness invariant**: `heap_attrinfo_insert_to_oos`는 매 transform마다 **새 OOS OID 를 신규 할당**한다. 따라서 UPDATE 직후 heap 슬롯의 recdes는 **새 OID** 만 들고 있고, pre-image 의 옛 OID 는 그 어떤 살아 있는 heap 위치에서도 참조되지 않는다.

이 invariant 덕분에:
- pre-image 옛 OID 들은 REMOVE 경로가 영원히 못 닿는다 → **forward-walk 가 유일한 회수 경로**.
- pre-image 와 post-image OID 가 disjoint 하므로 두 경로가 같은 OID 를 처리할 위험도 없다 (단, DELETE 는 예외 — 아래 §"DELETE_MODIFY_HOME").

#### 왜 다른 MVCC 로그 종류는 모두 제외하나

`LOG_IS_MVCC_HEAP_OPERATION`이 커버하는 6 종 중 어떤 것이 forward-walk 후보인가는 두 질문으로 결정된다.
1. **undo 에 pre-image recdes 가 실려 있는가?** — 없으면 forward-walk 자체가 불가능 (자동 제외).
2. **있다면, 그 recdes 의 OID 들을 다른 경로(REMOVE)가 회수하는가?** — 회수하면 forward-walk는 두 번 삭제를 일으키므로 명시 제외.

| rcvindex | undo 에 pre-image recdes | 같은 OID를 다른 경로가 회수? | 결정 |
|---|---|---|---|
| `RVHF_UPDATE_NOTIFY_VACUUM` | O (`old_recdes`) | **X** (post-image 가 fresh OID) | **포함** |
| `RVHF_MVCC_DELETE_MODIFY_HOME` | O (`old_recdes`) | O (post-DELETE에도 같은 OID 가 heap 안에 살아 있음) | **명시 제외** |
| `RVHF_MVCC_INSERT` | X (`size=0, data=NULL`) | n/a | undo_data 가드로 자동 차단 |
| `RVHF_MVCC_DELETE_REC_HOME` | X (size 0) | n/a | undo_data 가드로 자동 차단 |
| `RVHF_MVCC_NO_MODIFY_HOME` | X (NULL/0) | n/a | undo_data 가드로 자동 차단 |
| `RVHF_MVCC_REDISTRIBUTE` | X (crumbs n=0) | n/a | undo_data 가드로 자동 차단 |

→ **명시적인 `rcvindex == RVHF_UPDATE_NOTIFY_VACUUM` 가드(`vacuum.c:3677`)가 *load-bearing* 한 케이스는 단 하나, `RVHF_MVCC_DELETE_MODIFY_HOME` 차단이다.** 나머지 4 종은 `undo_data != NULL && undo_data_size > 0` 하나만으로도 자연 차단되며, rcvindex 가드는 검증을 명시화하는 역할.

#### `RVHF_MVCC_DELETE_MODIFY_HOME` 가 까다로운 이유

논리 DELETE는 heap 슬롯의 **recdes 본문(=OOS bit + OOS OID들)을 그대로 둔다**. MVCC 헤더의 `delete_mvccid`만 추가될 뿐. 그 결과:
- **pre-image (undo 안의 `old_recdes`)** 가 가리키는 OID
- **post-DELETE 살아 있는 heap (home 또는 relocation 타겟)** 이 가리키는 OID

가 **완전히 같은 집합**이다. 시간이 지나 그 슬롯이 vacuum threshold 를 넘으면 REMOVE 경로(§1)가 그 OID 들을 회수한다. 만약 forward-walk 가 그 사이 같은 OID 들을 보면 다음 시퀀스가 발생한다.

```
REMOVE 경로:    oos_delete(OID_X)  → chunk 첫 번째 삭제 OK
forward-walk:  oos_delete(OID_X)  → 같은 chunk 두 번째 삭제 시도
               → oos_delete_chain assert: S_DOESNT_EXIST
               → vacuum block 실패
```

UPDATE 와 대비하면 — UPDATE 도 undo 에 `old_recdes` 가 실리지만, post-UPDATE 슬롯은 **fresh OID 로 다시 작성**되므로 같은 슬롯 안에서도 옛 OID 는 사라진다. REMOVE 경로가 옛 OID 에 닿을 길 자체가 없다.

이 분석은 vacuum.c:3677 의 가드 위 코드 주석에도 동일하게 정리되어 있다 (커밋 `977cf18a4` 참조).

#### 왜 defensive copy를 안 하나

`oos_delete`는 `RVOOS_DELETE`를 chunk마다 append하면서 log page를 회전시킬 수 있어, 원래 `undo_data` 포인터가 가리키는 페이지가 무효화될 위험이 있다. 본 PR은 그 위험을 다음 방식으로 회피한다.

- 헬퍼 진입 **전에** `heap_recdes_get_oos_oids`가 OID들을 self-owned `OID_VECTOR`로 한 번에 복사해 둔다.
- 이후 `oos_delete` 루프는 그 벡터만 참조하지 `undo_data`는 다시 안 읽는다.

따라서 추가 메모리 할당/copy 없이도 안전하다 (defensive copy를 명시적으로 두던 이전 버전 commit `6738309aa`에서 단순화).

> 사이즈 가드: 현재 코드는 `undo_data != NULL && undo_data_size > 0` 만 검사하고 별도의 `2 * IO_MAX_PAGE_SIZE` 상한 가드는 두지 않는다. 손상 로그에 의한 unbounded memcpy를 막던 그 가드는 위 단순화 때 함께 제거됐다 (memcpy 자체가 사라졌으므로).

### 3. heap_update_home (SA_MODE 즉시 정리)

SA_MODE에서도 vacuum은 동작하지만 — 단일 프로세스이므로 동시 reader는 없다 — UPDATE 시점에 옛 OOS를 즉시 삭제해도 안전하다. SA_MODE에서 forward-walk이 해당 로그까지 진행하기 전에 OOS 파일을 사용하는 후속 작업이 들어올 수 있어, **이는 optimization이 아니라 correctness 보강**이다. `heap_update_home_delete_replaced_oos()`(heap_file.c:24131)가 pre-/post-image OID 차집합을 계산해 `oos_delete`를 즉시 호출. 같은 OID가 양쪽에 있으면(=같은 OOS를 그대로 재참조) 보존.

### 4. block-local OOS VFID 캐시

vacuum block 안에서 같은 heap 파일의 여러 레코드가 처리될 수 있다. heap VFID → OOS VFID 매핑을 매번 file tracker로 조회하면 비싸므로, block 단위로 16-슬롯 stack-local 배열 캐시를 둔다. 캐시 미스 시 `file_descriptor_get` + `heap_oos_find_vfid`. lookup 실패(`HFID_IS_NULL`, `file_descriptor_get` 실패, `heap_oos_find_vfid` 실패)는 캐시에 기록하지 않아 다음 호출에서 재시도된다.

### 5. Crash recovery (새 WAL 타입 없음)

본 PR은 **새 WAL 레코드 타입을 도입하지 않는다**. 복구는 다음 두 메커니즘에 편승한다.

- **per-chunk `RVOOS_DELETE` undoredo**: `oos_delete`가 chunk마다 이미 기록하고 있다. redo 가 정상 replay됨.
- **sysop 원자성**: REMOVE 경로 / forward-walk 경로 모두 `log_sysop_start ~ log_sysop_commit/abort`로 묶여 있어, sysop commit 이전 crash 시 전체 sysop이 자동 롤백 (heap 슬롯 / OOS 청크가 같이 변경 전 상태로 복귀).
- redo handler에서 추가 로그 append를 하지 않으므로 double-replay hazard 없음.

> 단, **crash injection 단위 테스트는 본 PR에 포함되어 있지 않다**. design-level 보장은 위 sysop boundary로 입증되지만 실제 crash 시나리오 자동 테스트는 별도 JIRA로 추적 예정.

## Remarks

### 6. 안전성 논거

**MVCC 가시성**: forward-walk가 UPDATE 로그를 보는 시점은 항상 `mvcc_table.get_global_oldest_visible()` 임계값(vacuum.c:3509) 이전이다. 그 임계값보다 오래된 버전은 어떤 활성 스냅샷에도 보이지 않으므로, pre-image OOS를 지워도 그걸 읽으려는 reader가 존재할 수 없다.

**OID 분리**: UPDATE의 post-image는 pre-image OID를 재사용하지 않는다 (`heap_attrinfo_insert_to_oos`가 매 transform마다 fresh OOS OID 할당). 따라서 forward-walk가 pre-image OID를 지워도 post-image 라이브 버전은 영향 없음.

**Sysop 원자성**: vacuum block forward-walk iteration 끝(`vacuum.c:3537/3858/3862/3871/3879`)에 `assert (!LOG_FIND_CURRENT_TDES (thread_p)->is_under_sysop ())`가 있어, 모든 `log_sysop_start`는 commit 또는 abort로 짝지어졌음을 보장한다.

### 7. 범위 외 / 후속 작업

- `REC_BIGONE` + OOS invariant: 현재 debug-only `assert (!heap_recdes_contains_oos)`. release-build 강화는 후속.
- crash-injection 단위 테스트 (§5): 후속 JIRA.
- forward-walk OID 리스트 정렬 (heap의 buffer-pool locality 패턴 따라하기): 후속 perf 최적화.
- `RVOOS_NOTIFY_VACUUM` rcvindex: 등록은 되어 있으나 emitter 없음. eager-vacuum 신호용 reserve 상태 → 추가/제거 결정은 후속 JIRA.
- forward-walk + `RVHF_MVCC_DELETE_MODIFY_HOME` 더블-삭제 시나리오 직접 재현하는 회귀 테스트: 후속.
