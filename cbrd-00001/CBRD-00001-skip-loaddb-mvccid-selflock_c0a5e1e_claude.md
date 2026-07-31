# [CBRD-00001] Skip MVCCID self-lock on loaddb worker threads (PoC)

> PoC 문서입니다. CBRD-00001 은 자리표시용 티켓 번호이며, 정식 JIRA 이슈 발제 전 CI 검증용 draft PR 의 상세 설명으로 작성되었습니다.
> 분석 대상 커밋: `feat/oos` 헤드 `0ad6afc0f` (2026-07-30 develop 머지), 수정 커밋: `c0a5e1ee8`.

## Purpose

`feat/oos` 헤드에서 server-side loaddb (`loaddb -C`) 로 OOS (Out-of-row Overflow Storage; 큰 컬럼 값을 힙 레코드에서 분리해 별도 파일에 저장하는 기능) 대상 행을 적재하면 debug 빌드의 `cub_server` 가 assert 실패로 즉시 종료됩니다. CircleCI test_shell (job 142161, 실패 19건) 중 `cbrd_25481`, `loaddb_CS/itrack_10006`, `loaddb_CS/bug_xdbms_sus880` 3건이 이 원인으로 실패합니다.

- AS-IS: `loaddb -C` 로 OOS 대상 행을 적재하면 OOS 파일 lazy 생성 경로에서 loaddb 워커 스레드가 락 매니저에 진입하여 `assert (thread_p->type != TT_LOADDB)` (src/transaction/lock_manager.c) 로 서버가 abort 됩니다.
- TO-BE: loaddb 워커 스레드는 MVCCID self-lock 을 건너뛰고, 적재가 정상 완료됩니다. 잠금 의미론은 CBRD-26942 이전의 loaddb 동작과 동일하게 유지됩니다.

### Root Cause

서로 독립적으로는 올바른 세 가지 설계가 develop 머지(`0ad6afc0f`)에서 처음 한 무대에 올라 충돌했습니다.

| 규칙 | 도입 | 내용 |
|---|---|---|
| loaddb 워커 락 금지 | CBRD-23375 (2019) | server-side loaddb 워커 스레드(`TT_LOADDB`)는 세션 트랜잭션이 쥔 BU_LOCK (bulk-update 용 클래스 단위 락)에 의존하며 락 매니저에 진입하지 않는다. `lock_internal_perform_lock_object` 의 assert 로 강제 |
| MVCCID self-lock | CBRD-26942 (2026-07-25, develop) | 행마다 걸던 X락을 트랜잭션당 1개로 줄이기 위해, 트랜잭션이 첫 MVCCID (트랜잭션의 MVCC 식별 번호)를 발급받는 시점에 그 MVCCID 에 X self-lock 을 건다. unique/FK 검사자는 미완성 행의 INSID (레코드 헤더에 기록되는 삽입자 MVCCID 도장)를 보고 이 락을 기다린다. 발급 지점은 `logtb_get_current_mvccid` 의 lazy 할당 분기와 `logtb_get_new_subtransaction_mvccid` 두 곳 |
| OOS 파일 lazy 생성 | feat/oos | 클래스의 OOS 파일은 첫 demote (큰 컬럼 값을 OOS 파일로 내려보내는 동작) 시점에 생성된다. `file_create` 는 `FILE_BTREE/FILE_HEAP/FILE_HEAP_REUSE_SLOTS/FILE_OOS` 타입에 한해 vacuum dropped-file 검사를 위해 `logtb_get_current_mvccid` 를 호출하는데 (src/storage/file_manager.c), feat/oos 가 이 목록에 `FILE_OOS` 를 추가했다 |

loaddb 워커의 벌크 삽입은 INSID 스탬프를 생략하므로(`is_bulk_op`, src/storage/heap_file.c) 비-OOS 적재에서는 워커가 MVCCID 를 요구하는 지점이 없습니다. 확인된 범위에서는 OOS 파일 lazy 생성이 TT_LOADDB 스레드가 MVCCID 발급 지점에 도달하는 유일한 진입 경로이며, CBRD-26942 가 그 경로를 assert 위반으로 바꿨습니다. 호출 경로 (로컬 core 4건의 스택과 대조하여 일치 확인):

```text
lock_internal_perform_lock_object     ← assert (thread_p->type != TT_LOADDB)
lock_transaction_mvccid
logtb_acquire_mvccid_self_lock
logtb_self_lock_assigned_mvccid
logtb_get_current_mvccid              ← lazy 할당 분기
file_create                           ← vacuum dropped-file 검사용 MVCCID 요구
oos_create_file
heap_oos_find_vfid (create)
heap_oos_insert_serialized_values
heap_attrinfo_insert_to_oos
heap_attrinfo_transform_to_disk_internal
heap_attrinfo_transform_to_disk_except_lob
cubload::server_object_loader::finish_line
```

## Implementation

`src/transaction/log_tran_table.c` 의 `logtb_acquire_mvccid_self_lock` 에 TT_LOADDB 조기 반환을 추가했습니다 (+17줄, 파일 1개). 기존 boot/recovery/비-워커 트랜잭션 가드 바로 뒤에 위치합니다. 이 중 4줄은 `thread_p == NULL` 일 때 `thread_get_thread_entry_info ()` 로 실제 스레드 엔트리를 얻는 정규화입니다 — 앞선 가드는 NULL 을 허용하는 `LOG_FIND_THREAD_TRAN_INDEX` 매크로만 쓰지만 `thread_p->type` 검사는 NULL 을 허용하지 않기 때문입니다.

건너뛰어도 안전한 근거와 그 한계:

1. **이 self-lock 을 기다릴 관측자가 존재할 수 없습니다.** self-lock 의 유일한 용도는 unique/FK 검사자가 미완성 행의 INSID 를 통해 인서터를 기다리는 것인데, loaddb 워커의 벌크 삽입 행에는 INSID 가 찍히지 않습니다. 단, 이 INSID 미기입은 `is_bulk_op == has_BU_lock` (src/transaction/locator_sr.c) 에 의존하며, loaddb 워커의 BU_LOCK 보유는 src/loaddb/load_server_loader.cpp 의 debug assert 로만 보장됩니다.
2. **워커 트랜잭션은 배치 단위 단일 스레드 소유입니다.** src/loaddb/load_session.cpp 의 `load_task::execute` 가 배치마다 새 tran_index 를 발급받아 같은 스레드에서 삽입과 커밋까지 마치므로(세션 트랜잭션과 별개), 수명 안에 INSID 를 만들 기회 자체가 없고 lazy MVCCID 할당의 동시 접근 레이스도 없습니다.
3. **한계 (정직한 서술)**: heap 삽입 지점의 2차 획득 경로 `logtb_ensure_mvccid_self_lock` 도 이 패치 함수로 위임되므로, TT_LOADDB 스레드에서는 함께 무력화됩니다. 즉 이 가드의 보호는 근거 1·2 가 전부이며, 미래에 어떤 코드가 TT_LOADDB 스레드에서 INSID 를 찍게 되면 self-lock 없이 관측 가능한 INSID 가 생기는데 이를 잡는 assert 는 현재 없습니다. 정식 수정 시 INSID 스탬프 지점에 `assert (thread_p->type != TT_LOADDB)` 성격의 debug 방어를 추가할 것을 권장합니다.

참고로 이 가드는 `logtb_get_current_mvccid` 경유뿐 아니라 `logtb_get_new_subtransaction_mvccid` 의 self-lock 도 loaddb 워커에 대해 함께 건너뛰게 합니다(공유 헬퍼이므로). 락 매니저의 `lock_object` 에 있는 기존 TT_LOADDB 예외와 동일한 전제(워커는 세션 BU_LOCK 에 의존)를 따르되, `lock_object` 쪽은 BU_LOCK 보유를 검증하고 skip 하는 반면 이 가드는 검증 없이 skip 합니다.

기각한 대안:

- **assert 완화 + 워커가 self-lock 획득**: 방금 발급된 MVCCID 의 X락은 대기하지 않지만, loaddb 워커의 락 매니저 진입 자체가 전례 없는 상태라 안전성 증명 부담이 큽니다. skip 은 CBRD-26942 이전 loaddb 의미론과 동일하여 증명 부담이 없습니다.
- **`file_create` 가 MVCCID 를 lazy 할당하지 않도록 변경**: dropped-file 검사의 MVCCID 는 비교 기준값일 뿐이므로 "할당 없이 현재값만 읽는" getter 로 대체하는 안이 가장 국소적입니다. 다만 현재 그런 비할당 getter API 가 없어 새 API 표면이 필요하고, heap/btree 파일 생성 경로의 의미에도 영향을 줍니다. 정식 수정에서 재검토할 가치는 있습니다.
- **OOS 파일 eager 생성 / 세션 스레드 MVCCID 선발급**: lazy 생성 스펙 위반이거나, loaddb 의 모든 트랜잭션 경계에 누락 없이 심어야 해 재발 여지가 있습니다. 근본 계약(워커는 락 금지)을 코드에 명시하지 못합니다.

## Remarks

- 리뷰 포인트: `logtb_acquire_mvccid_self_lock` 의 가드 순서(기존 가드 → NULL 정규화 → TT_LOADDB 가드 → 락 획득)와, 위 "안전 근거와 한계" 서술이 실제 코드 사실과 일치하는지.
- release 빌드에서는 assert 가 컴파일 아웃되어 크래시하지 않을 것으로 추정되나 검증하지 않았습니다. 실질 영향 범위는 debug/optdebug (assert 활성 최적화 빌드) 빌드, 즉 QA/CI 입니다.
- 이 수정은 `feat/oos` 헤드의 test_shell 실패 19건(CircleCI job 142161 기준) 중 3건(`cbrd_25481`, `loaddb_CS/itrack_10006`, `loaddb_CS/bug_xdbms_sus880`)을 해소합니다.
- 정식 JIRA 이슈 발제 시 티켓 번호 교체, 커밋 메시지 갱신, 그리고 위 한계 항목의 INSID 스탬프 debug assert 추가 및 코드 주석 재정비가 필요합니다 (현재 CBRD-00001 은 자리표시).

### Test Plan

로컬 debug 빌드(`0ad6afc` 기준)에서 CTP shell 러너로 검증했습니다. 세 TC 는 모두 CI 상주 테스트이므로 이번 수정의 자동 회귀 방어선 역할을 하며, 별도 신규 테스트는 추가하지 않았습니다.

| 테스트 | 수정 전 (`0ad6afc`) | 수정 후 |
|---|---|---|
| `shell/_06_issues/_24_2h/cbrd_25481` | 6/13/20/27 NOK, DB 마다 `cub_server` core | 28/28 OK, core 없음 |
| `loaddb_CS/_01_utility/_17_loaddb/itrack_10006` | NOK ×2 + 동일 스택 core (대조 실험으로 확인) | 2/2 OK |
| `loaddb_CS/_05_addition/bug_xdbms_sus880` | NOK ×1 (CI) | 1/1 OK |

수정 전 core 3건(cbrd_25481)과 대조 실험 core 1건(itrack_10006)의 스택이 모두 위 요약 호출 경로와 일치함을 확인했습니다.

추가로 unique/PK 인덱스가 있는 테이블에 대한 `loaddb -C` 스모크 테스트를 수행했습니다: OOS 대상 JSON 행 2건 적재 → 값 동등성 확인, unique/PK 위반 정상 검출, 적재 후 신규 OOS 대상 행 INSERT 정상.
