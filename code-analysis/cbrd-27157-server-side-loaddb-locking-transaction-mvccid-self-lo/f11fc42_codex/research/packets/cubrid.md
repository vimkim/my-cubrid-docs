# CUBRID Source Tracer Evidence Packet

- **role**: Role 1 — CUBRID Source Tracer
- **topic**: CBRD-27157 server-side loaddb locking, transaction MVCCID self-lock, and `BU_LOCK`
- **scope digest**: `f07826ef64e37143f055cdf4814be26d965d9bc531421f21439871475722fa5b`
- **revision**: `f11fc42594732c263d8f10101f9df73a21346ee9`
- **timestamp**: `2026-08-11T16:05:12+09:00`
- **root**: `/home/vimkim/gh/cb/feat-oos-fix-regression`
- **evidence state**: 저장소 전체는 dirty이지만, 아래에서 인용한 CUBRID 파일은 모두 `git diff HEAD -- <path>` 기준 commit-clean이므로 `COMMIT` 증거다. dirty 항목은 `cubrid-cci` submodule과 로컬 보조 파일뿐이다.

## 1. 먼저 붙잡을 결론

이 이슈에는 이름이 비슷해 보이는 두 lock이 있으나, resource와 owner가 완전히 다르다.

```text
session transaction S
  └─ class OID T에 BU_LOCK
       ├─ worker batch transaction B1
       │    └─ 자기 MVCCID M1에 X_LOCK (transaction self-lock)
       └─ worker batch transaction B2
            └─ 자기 MVCCID M2에 X_LOCK (transaction self-lock)
```

- `BU_LOCK`은 **class OID**를 key로 하는 object lock이다. `server_class_installer`가 session request thread에서 얻고, loaddb worker가 object lock을 조회할 때 lock manager가 session transaction으로 조회를 redirect한다.
- MVCCID self-lock은 **64-bit MVCCID**를 key로 하는 `LOCK_RESOURCE_TRANSACTION`이다. worker가 자기 batch transaction의 `tran_index`로 `X_LOCK`을 소유한다.
- 두 resource는 같은 lock hash table과 compatibility machinery를 쓰지만 `LK_RES_KEY.type`이 identity 일부이므로 서로 alias되지 않는다.
- unique/FK 검사자는 레코드의 INSID가 가리키는 MVCCID resource에 `S_LOCK`을 걸어 inserter의 `X_LOCK` 해제를 기다린다. 기다리기 전 page latch와 보유 object lock을 풀고, 깨어난 뒤 B-tree를 다시 읽는다.
- server-side loaddb의 bulk row는 현재 `is_bulk_op`이므로 heap insert에서 INSID를 제거하고 per-row lock도 잡지 않는다. 따라서 현재 bulk row만 놓고 보면 worker MVCCID를 레코드에서 발견할 waiter가 없다는 결론은 **추론**이다. 반면 “모든 active worker의 정상 MVCCID 발급은 self-lock한다”는 현재 구현 규칙은 future path에서도 `observable INSID => held X self-lock` 불변식을 일정하게 유지한다.
- OOS는 새 object lock을 요청하지 않는다. 첫 OOS demotion이 lazy OOS file creation을 열고, `file_create(FILE_OOS)`가 dropped-file VFID 재사용 검사를 위해 `logtb_get_current_mvccid()`를 호출한다. 이 lazy MVCCID 발급의 부수 효과가 transaction self-lock이다.
- 고정 리비전에는 PR 수정이 이미 들어 있다. 현재 assert는 `TT_LOADDB`라도 resource가 transaction이면 허용하고, class/instance object lock이면 여전히 실패한다. 수정 전 부모 `23c0bbae350f8f7c5db187c6176d205bb2079e6f`에는 무조건 `assert(thread_p->type != TT_LOADDB)`가 있어 debug/optdebug가 이 호출 경로에서 abort했다.

## 2. Provenance와 증거 권위

- 고정 provenance: `provenance.json`의 CUBRID root/HEAD/branch와 실제 checkout이 일치했다.
- baseline status hash: `1dee2aa0429cdbdaec8d32c12371d10afa4b191779c969a1ade84c692d42f815`
- baseline worktree diff hash: `3f3e8df89882050c7e774209111200c1f62adbdb3e25d4ecb6484d3e7ed0f202`
- 현 리비전은 CBRD-26942 `741734a8f3785a3e2a678bb52e289000c2261b6f`, CBRD-23375 `1994f0be34e919d3819c92eef39837f00d98827f`, CBRD-27157 `8bcfd7dd278cbe2b16a064bce4105e68cf80d6a1`을 모두 ancestor로 포함한다.
- 구현 동작은 고정 source가 최우선이다. JIRA/local lesson/commit message는 역사와 의도를 설명하는 보조 근거다. 이 role에서는 runtime을 실행하지 않았으므로 runtime claim은 만들지 않는다.

## 3. 용어와 identity

| 이름 | 뜻 | 이 이슈에서의 쓰임 |
|---|---|---|
| `tran_index` | 서버 transaction table의 slot index | lock entry의 owner를 찾는 값. session과 worker batch가 서로 다른 값을 가진다. |
| `TRANID trid` | log transaction identifier | `LOG_TDES`에 `tran_index`와 나란히 존재하지만 MVCCID lock key가 아니다. |
| `MVCCID` | row version의 inserter/deleter를 표시하는 64-bit ID | transaction self-lock의 resource key, row header INSID의 값. |
| INSID | 레코드 MVCC header의 insert MVCCID | unique/FK 검사자가 아직 active인 inserter를 알아내는 표식. |
| `LK_RES` | 하나의 lockable resource | key, holder list, waiter list, resource mutex를 가진다. |
| `LK_ENTRY` | 한 transaction의 요청/보유 상태 | `tran_index`, granted/blocked mode, request count, resource back-pointer를 가진다. |
| mutex/latch | 짧은 critical section 또는 page 접근을 보호 | transaction lock을 기다리기 전에 page latch를 놓아야 한다. transaction 종료까지 보유하는 lock과 lifetime이 다르다. |

`LOG_TDES`는 `mvccinfo`, `tran_index`, `trid`, state, isolation, `wait_msecs`를 별도 필드로 가진다 (`src/transaction/log_impl.h:510-538`). 따라서 “transaction ID”라는 말만 쓰면 `tran_index`, `trid`, MVCCID 중 무엇인지 반드시 다시 물어야 한다.

## 4. 조사한 파일과 symbol

아래 line range는 고정 checkout의 현재 byte 기준이다. 모든 hash는 SHA-256이고 모두 `COMMIT`이다.

| 파일 / SHA-256 | 조사한 symbol과 정확한 line range | 확인한 책임 |
|---|---|---|
| `src/transaction/lock_table.h` / `7daf768467c9b4dc41506376335ade54f33402690a56f54447a1a28269c0c275` | `LOCK` 36-52, `lock_compat` 64-69 | mode 이름과 compatibility lookup interface |
| `src/transaction/lock_table.c` / `833bb45be1b2f278c456f2eb06bbb1e9c7f9ddab5ecef5cb4a3cbe661a8e9953` | `lock_Comp` 30-131, `lock_Conv` 134-224 | 정확한 BU compatibility와 conversion |
| `src/transaction/lock_manager.h` / `d996e4e67bb74f11275c5c3b2f945ad82aa9117eccfa1b7589dce03e5c93b6c3` | `LK_ENTRY` 75-101, `LOCK_RESOURCE_TYPE`/`LK_RES_KEY`/`LK_RES` 151-210 | resource identity, holder/waiter, owner field |
| `src/transaction/lock_manager.c` / `b8d47adef644a8f1642dabf6736d80b7b47df66b467e98324d4c1deee1cab8d3` | `lock_create_search_key` 670-718, `lock_create_mvccid_search_key` 720-740, `lock_res_key_copy/compare/hash` 865-960 | object key와 transaction key 분리 |
| 같은 파일 | `lock_insert_into_tran_hold_list` 1392-1499, `lock_delete_from_tran_hold_list` 1502-1607 | transaction self-lock을 `inst_hold_list`에서 추적 |
| 같은 파일 | `lock_internal_perform_lock_object` 3456-4180, `lock_internal_perform_unlock_object` 4201-4400 | grant/convert/wait/retry/timeout/abort/cleanup 전체 state machine |
| 같은 파일 | `lock_object` 6238-6435 | TT_LOADDB object lock bypass와 session BU 검증 |
| 같은 파일 | `lock_transaction_mvccid` 6437-6493, `lock_unlock_transaction_mvccid` 6495-6553, `lock_has_lock_on_transaction_mvccid` 6556-6613 | MVCCID X/S acquire, full release, debug invariant query |
| 같은 파일 | `lock_unlock_all` 7353-7428 | transaction end의 전체 lock release |
| 같은 파일 | `lock_get_object_lock` 7473-7584, `lock_has_lock_on_object` 7586-7696, `lock_get_class_lock` 7844-7911 | TT_LOADDB object lock lookup을 connection/session `tran_index`로 redirect |
| 같은 파일 | `lock_unlock_object` 7130-7223 | `force=false`일 때 BU 같은 non-S lock을 transaction end까지 유지 |
| 같은 파일 | `lock_dump_resource` 5585-5775, `lock_event_log_lock_info` 10072-10135, timeout message switch 2100-2245 | dump/event log/timeout 관측 |
| `src/transaction/log_impl.h` / `579e04590a6776e1769b47fee886d3e2f417ef09b98975705db00ab4e6a0ff2f` | `LOG_TDES` 510-610 | transaction descriptor ownership와 `wait_msecs` |
| `src/storage/storage_common.h` / `e9593cc2a752970a18e4580bb96b98cd585f61cca1914111958692b1b5d79c50` | `MVCCID` 187, `TRANID`와 MVCCID macros 322-351 | 서로 다른 transaction 식별자와 normal ID 범위 |
| `src/transaction/mvcc.h` / `8233694bf4aad5a2905c8e2134a0aea2a9eb1948b1b935cca50f794a4cba6d4b` | `MVCC_INFO` 197-227 | main/sub MVCCID와 self-lock dedup hint lifetime |
| `src/transaction/mvcc.c` / `53119c2d78b2b6d2899c9f749243ded256c18743b917939aadd66de872ef8c75` | `mvcc_info::{ctor,reset,copy_to}` 690-724 | hint 초기화, reset, copy 시 미상속 |
| `src/transaction/mvcc_table.cpp` / `5dc09351d6bc1f58da7d1a1a9ac68dbf043b14b66c066e14c713ad1baace7b08` | `mvcctable::complete_sub_mvcc` 540-563, `mvcctable::get_new_mvccid` 565-590 | active bit 종료, mutex로 직렬화된 다음 MVCCID 발급 |
| `src/transaction/log_tran_table.c` / `d09d22e98e9d6f897e70f1170ad1c67eb5d887400849676af583a494af2fbc68` | `logtb_find_current_mvccid` 4024-4051, self-lock helpers와 `logtb_get_current_mvccid`/`ensure` 4053-4192 | lazy assignment, best-effort acquire, error-propagating ensure, guard |
| 같은 파일 | `logtb_complete_mvcc` 4388-4463, subtransaction functions 4886-4987 | active 상태 종료와 main/sub self-lock lifetime |
| 같은 파일 | `logtb_find_wait_msecs` 2583-2605 | transaction별 wait policy 조회 |
| `src/transaction/log_manager.c` / `e3a6861d2b8fbf975aa578b2bb10f64132614e8719d1a0531f53a71dbb21f575` | `log_commit_local` 5193-5312, `log_abort_local` 5314-5384 | MVCC complete 후 lock release ordering |
| `src/transaction/transaction_sr.c` / `caf425556e78f76341df76c98c19dcf63238dceb847a21d71d880622db0ea071` | `xtran_server_commit` 47-105, `xtran_server_abort` 107-145 | server transaction boundary interface |
| `src/loaddb/load_session.cpp` / `0eda9a08ee2ffa5e9d485183ece11936f350582f0d3fd13bdd97efac35e88cb9` | `load_task` 90-232, `session` lifecycle 234-452, `session::load_batch` 581-647 | batch transaction 생성/commit/abort/free, ordered commit, interrupt, retry |
| `src/loaddb/load_server_loader.cpp` / `3b187c830a16d6329b88892e0066eb2b0a24decb762f965f330aea66973ddde8` | `server_class_installer::locate_class` 118-181, `server_object_loader::{init,finish_line,flush_records}` 576-825 | session BU 획득, worker-side BU 확인, OOS transform 진입 |
| `src/communication/network_interface_sr.cpp` / `d433da83cfdc72733e1a17e1793859b7fca0394065970718b0b8de34dea19164` | `sloaddb_init/install_class/load_batch/fetch_status/destroy` 10851-11079 | connection session object의 생성, 요청, completion 대기, 삭제 |
| `src/session/session.c` / `188971b4f19dc36650402cb670bf8ab35ffb81978d9045618cc475f37c1b0118` | `session_set/get_load_session` 3230-3284, interrupt/destroy/stop 3318-3390 | disconnect 시 worker interrupt 후 안전한 load session 파괴 |
| `src/connection/connection_worker.cpp` / `29f7a8e393b727e3f0928ccbb062a6abcdedd9f81422af2888a82e81d844b72b` | `handle_connection_close` 810-885 | connection worker drain 뒤 load session destroy와 connection transaction 종료 연결 |
| `src/communication/network_sr.c` / `43222e602b70c29509a10053d9e5621984e6564da5a7eba9447937f5a720a62a` | loaddb request registration 691-711, `net_server_conn_down` 1042-1059 | request handler와 disconnect unregister 연결 |
| `src/transaction/boot_sr.c` / `01c1189c162d2d6b6a41dac4d9a52e0cab169c5fd1e6ae2cd003bb5f90343651` | `xboot_unregister_client` 3317-3412 | disconnect 시 active session transaction abort 및 resource release |
| `src/loaddb/load_db.c` / `a9b9e23ffd3b9defec0452962fe58384ed78c7e9fa5d9f20e1cddef605ef5323` | `ldr_server_load` 1347-1498, `load_object_file` 1553-1610, outer shutdown 740-930 | client batch retry/status/destroy와 최종 shutdown |
| `src/communication/network_interface_cl.c` / `d684a32e5ef88c734c2ec3f4467796d9c3d200489d2d02273cbd0f0efac557a5` | `loaddb_destroy` 11069-11088 | client destroy request는 load session만 종료 |
| `src/compat/db_admin.c` / `a3d5b9677d2d544478b8d9122e47b5a1b9cbc70e65586db910102e06bc03ac2c` | `db_shutdown` 1007-1032 | loaddb outer flow의 최종 client shutdown entry |
| `src/transaction/boot_cl.c` / `b877704826a9642968dacbde6e96a42b4ad73caefd26c2a6bae39ea34a246634` | `boot_shutdown_client` 1360-1423 | shutdown의 commit/abort parameter 처리와 unregister |
| `src/transaction/locator_sr.c` / `c5a71543495c9e1728eb76e3f221cca8a07cf3e9f9250a856de3f47b6cc567e3` | `xlocator_find_class_oid` 1017-1162, `locator_insert_force` 4926-5085 | BU class lock 실제 획득, `has_BU_lock -> context.is_bulk_op` |
| `src/storage/heap_file.c` / `e724454bf25240ec7a8708560ce970fbd6b36cd1c6716f3fff0858534c0ba5ef` | `heap_oos_find_vfid` 12241-12351, `heap_attrinfo_insert_to_oos` 12516-12580, transform entry/internal 12601-12619, 13064-13194 | OOS lazy create, payload cleanup, record transform call path |
| 같은 파일 | `heap_insert_adjust_recdes_header` 21162-21303, `heap_get_insert_location_with_lock` 21570-21742, `heap_insert_logical` 24255-24445, MVCC update ensure 24757-24776 | bulk INSID 제거, NULL row lock, BU 대신 IX 생략, nonbulk self-lock |
| `src/storage/heap_oos.cpp` / `41818579115f4d3be17021de778ed6f6cd3c1ba97cc08061f16df1c7961f4a71` | `heap_oos_begin_insert_publication` 600-620, `heap_oos_insert_serialized_values` 622-659 | per-thread/per-transaction publication reset, create lookup, batch insert |
| `src/storage/oos_file.cpp` / `3c9d63efcec934a6102b2d002c6d2376bf422e0c952aa62ef48380ec713300b5` | `oos_create_file_internal` 968-1066, `oos_create_file` 1068-1078 | `FILE_OOS` 생성과 sticky header sysop |
| `src/storage/file_manager.c` / `e0c8b0b2e7abd869f15f83d6934173acff032b266ac46e2f563a8403b4a645ff` | `file_create` 3320-3923 | sector reserve, current MVCCID 요구, dropped-file 검사, error cleanup |
| `src/storage/btree.c` / `547c44afb9ed2d86eca95744b3118ab5eee566ba48a779690ffe92abc75993b3` | self-lock waiter helpers 24228-24334, unique paths 24336-24920, FK path 27365-27545, debug insert/delete preconditions 37086-37164 | S wait/release/recheck, latch discipline, unique/FK callers |
| `src/base/system_parameter.c` / `3023adca16eea76582387acac93b81d46bc90a8ea34a1ac5b9470958979e87ce` | lock timeout entries 1269-1334, `monitor_waiting_thread` 3154-3164 | lock wait와 warning 관련 설정 |

## 5. Interface와 호출 경로

### 5.1 Session이 `BU_LOCK`을 얻고 worker가 빌려 보는 경로

```text
client loaddb
  -> NET_SERVER_LD_INSTALL_CLASS
  -> sloaddb_install_class(thread = connection request worker)
  -> load_session::install_class
  -> server_class_installer::locate_class
  -> xlocator_find_class_oid(classname, class_oid, BU_LOCK)
  -> lock_object(class_oid, root_class_oid, BU_LOCK, UNCOND)
  -> LK_RES_KEY { type=CLASS, oid=class_oid }
  -> session transaction의 class hold list
```

여기서 request thread는 `TT_LOADDB` batch worker가 아니라 connection/session transaction 문맥이다. `xlocator_find_class_oid`는 class name race가 있으면 lock을 잡고 classname table을 다시 읽으며, 최종적으로 요청 mode를 class OID에 획득한다 (`locator_sr.c:1044-1147`). `lock_unlock_object(..., force=false)` 호출은 transaction isolation/2PL 규칙을 따르므로 최종 class lock의 transaction lifetime을 즉시 끝내는 의미가 아니다.

batch worker가 `server_object_loader::init` 또는 heap/btree 내부에서 class/instance lock을 조회하면:

```text
TT_LOADDB worker
  -> lock_has_lock_on_object(class_oid, root, BU_LOCK)
  -> thread_p->conn_entry->get_tran_index()
  -> session transaction의 class BU entry 조회
```

instance에 대한 `lock_object()` 요청은 실제 instance `LK_ENTRY`를 만들지 않고 session class BU가 보이면 `LK_GRANTED`를 반환한다. class request도 `SCH_S_LOCK`/`BU_LOCK`만 허용하고 session BU를 확인한다 (`lock_manager.c:6281-6317`). 따라서 worker의 object-lock “성공”은 worker batch가 그 object lock을 소유했다는 뜻이 아니다.

### 5.2 `BU_LOCK` compatibility를 그대로 읽기

`BU_LOCK`은 `Bulk Update Lock`이다. 요청 BU row와 현재 mode column을 읽으면 다음과 같다.

| 현재 holder mode | BU request |
|---|---|
| `NULL_LOCK` | compatible |
| `SCH_S_LOCK` | compatible |
| `BU_LOCK` | compatible |
| `IS_LOCK`, `S_LOCK`, `IX_LOCK`, `SIX_LOCK`, `X_LOCK`, `SCH_M_LOCK` | incompatible |

따라서 “BU는 모든 다른 접근을 막는다”는 과장이다. schema stability와 다른 BU는 공존한다. 반대로 일반 class/row data access가 요구하는 intent/data mode와는 충돌한다. conversion table에서는 이미 `IS/S/IX/SIX`를 가진 같은 transaction이 BU를 추가 요청하면 경우에 따라 `BU` 또는 `X`로 합성되므로 compatibility와 conversion을 섞어 읽으면 안 된다.

### 5.3 Worker batch transaction lifecycle

```text
accepted batch
  -> load_task::execute(TT_LOADDB thread)
  -> conn_entry 부착
  -> logtb_assign_tran_index(... TRAN_ACTIVE, INFINITE_WAIT)
  -> session active transaction set에 worker tran_index 등록
  -> session transaction에서 client identity만 복사
  -> parse + transform + insert
     success: 이전 batch commit 완료를 기다림
              -> xtran_server_commit(false)
     failure/session failed: session::fail()
              -> xtran_server_abort()
  -> client identity reset
  -> logtb_free_tran_index()
  -> active set에서 제거, completion notify
```

중요한 ownership 사실은 client IDs만 복사한다는 점이다. `session_tdes`와 `worker_tdes`는 다른 transaction descriptor다 (`load_session.cpp:151-159`). commit 순서는 batch ID 순서로 직렬화하지만 parsing/insertion은 worker pool에서 겹칠 수 있다. pool이 batch를 받지 못한 경우에만 client가 같은 임시 batch를 다시 요청하고, accepted batch를 중복 queue하지 않는다 (`load_session.cpp:581-647`, `load_db.c:1566-1586`).

실패와 interrupt:

- 한 batch가 parser/insert error를 만나면 `session::fail`로 전체 load session을 failed로 만들고 자기 worker transaction을 abort한다.
- `session::interrupt`는 현재 등록된 모든 worker `tran_index`에 interrupt flag를 세우고 waiters를 깨운다.
- `sloaddb_destroy`는 모든 worker completion을 기다린 후 load session object를 지운다.
- connection이 먼저 끊기면 connection close가 session을 interrupt하고 active request/worker를 drain한 뒤 load session을 지운다. 마지막 `net_server_conn_down -> xboot_unregister_client`는 남은 active connection/session transaction을 abort해 BU 등 session-owned resource를 해제한다.

### 5.4 MVCCID self-lock acquisition

```text
logtb_get_current_mvccid(worker)
  -> mvccinfo.id가 없으면 mvcctable::get_new_mvccid()
  -> logtb_self_lock_assigned_mvccid(best effort)
  -> logtb_acquire_mvccid_self_lock
       guard: server restarted + active worker transaction만
       dedup: self_locked_mvccid == mvccid이면 no-op
       -> lock_transaction_mvccid(mvccid, X_LOCK, UNCOND)
            owner = LOG_FIND_THREAD_TRAN_INDEX(thread_p)
            key = { type=TRANSACTION, mvccid }
       -> 성공 시 self_locked_mvccid = mvccid
```

assignment API는 error를 반환할 수 없어서 첫 acquire 실패를 debug log에 남기는 best-effort다. row INSID가 실제로 observable해지기 전 insert/update path는 `logtb_ensure_mvccid_self_lock()`을 다시 호출하고 error를 전달한다. ensure는 정상 문맥인지 먼저 검사하고 필요하면 lazy ID를 발급한 뒤 같은 helper를 호출한다.

boot/recovery/system/vacuum transaction은 self-lock을 만들지 않는다. 이 문맥은 `lock_unlock_all`을 통과하지 않아 entry가 남을 수 있고 concurrent waiter가 없다는 것이 source의 guard 이유다 (`log_tran_table.c:4084-4090, 4175-4188`).

subtransaction은 main ID가 없으면 main/sub ID를 함께 발급하고 둘을 self-lock한다. subtransaction 종료는 active bit를 먼저 내린 뒤 해당 sub-MVCCID lock을 full release하고 stack에서 pop한다 (`log_tran_table.c:4886-4987`).

### 5.5 Inserter/waiter rendezvous

```text
T1: MVCCID=M 발급
T1: resource {TRANSACTION, M}에 X_LOCK
T1: row header INSID=M 공개

T2: unique/FK scan이 INSERT_IN_PROGRESS + active other M을 발견
T2: 보유 object lock과 leaf/overflow page latch를 먼저 해제
T2: resource {TRANSACTION, M}에 S_LOCK 요청
    -> X와 incompatible이므로 T1 종료까지 wait
T1: complete_mvcc(M) -> active=false
T1: lock_unlock_all() -> X release, T2 wakeup
T2: S grant 직후 full release
T2: is_active(M)을 다시 확인
T2: B-tree root/key를 다시 읽음
```

`btree_wait_for_inserter_end`는 S lock이 grant되었는데 MVCC table에서 M이 여전히 active면 불변식 위반으로 `ER_CANNOT_GET_LOCK`을 반환하고 debug assert한다. 같은 wait를 반복해 spin하지 않는다. unique path는 `restart=true`, FK path는 `stop=true`로 상위 scan이 stale page 결과를 소비하지 않고 재검사하게 한다.

이 ordering은 우연이 아니다. commit/abort는 `logtb_complete_mvcc`로 active 상태를 먼저 종료한 뒤 `lock_unlock_all`로 X lock을 푼다 (`log_manager.c:5224-5228, 5275-5278, 5355-5359, 5373-5376`). 따라서 정상 경로에서는 깨어난 waiter의 active 재검사가 false여야 한다.

### 5.6 Bulk insert는 self-lock protocol과 어떻게 만나는가

`locator_insert_force`는 session BU 확인 결과를 `context.is_bulk_op`에 전달한다 (`locator_sr.c:5062-5066`). 물리 heap insert에서 bulk이면:

1. `is_mvcc_op=false`가 된다.
2. `heap_insert_adjust_recdes_header`는 INSID를 넣지 않고 MVCC flag를 지운다.
3. class `IX_LOCK`을 새로 잡지 않고 session BU 보유를 assert한다.
4. insert location의 mode가 `NULL_LOCK`이 되어 per-row object lock도 잡지 않는다.

하지만 OOS transform은 이 locator/heap bulk context를 만들기 **전에** `server_object_loader::finish_line`에서 실행된다. 즉 crash path에서 아직 `context.is_bulk_op`을 검사한 것이 아니라, TT_LOADDB worker transaction 안에서 OOS file metadata를 준비하는 중 MVCCID가 처음 필요해진 것이다.

### 5.7 OOS lazy-create에서 CBRD-27157까지

전체 reachable path:

```text
server_object_loader::finish_line                         load_server_loader.cpp:692
  -> heap_attrinfo_transform_to_disk_except_lob          heap_file.c:12615
  -> heap_attrinfo_transform_to_disk_internal            heap_file.c:13079
     -> disk layout에서 has_oos=true
     -> heap_attrinfo_insert_to_oos                      heap_file.c:12526
        -> heap_oos_begin_insert_publication
        -> serialize request payloads
        -> heap_oos_insert_serialized_values             heap_oos.cpp:631
           -> heap_get_class_info
           -> heap_oos_find_vfid(..., docreate=true)     heap_file.c:12255
              -> heap header WRITE latch
              -> oos_vfid가 NULL이면 outer sysop start
              -> oos_create_file                        oos_file.cpp:1069
                 -> oos_create_file_internal             oos_file.cpp:969
                    -> file_create(FILE_OOS)             file_manager.c:3333
                       -> permanent sysop start
                       -> disk_reserve_sectors
                       -> FILE_OOS도 dropped-file 검사 대상
                       -> logtb_get_current_mvccid        log_tran_table.c:4135
                          -> lazy MVCCID assignment
                          -> transaction X self-lock
                          -> lock_internal_perform_lock_object
                       -> vacuum_is_file_dropped(vfid, tran_mvccid)
                    -> sticky OOS header page를 nested sysop에서 생성
              -> TDE 적용
              -> heap header에 oos_vfid undo/redo publication
```

`file_create`가 MVCCID를 원하는 목적은 row INSERT stamp가 아니라, 후보 VFID가 vacuum의 dropped-file list와 겹치는지 transaction-relative하게 검사하는 기준값이다 (`file_manager.c:3448-3470`). OOS가 object lock을 요청했다는 해석은 틀리다.

수정 전 부모 source에서는 `lock_internal_perform_lock_object`가 resource 종류와 무관하게 `TT_LOADDB`를 assert했다. CBRD-26942가 MVCCID assignment에 self-lock side effect를 붙인 뒤 OOS lazy create가 이 숨은 진입점을 열어 debug/optdebug server abort를 만들었다. 현재 고정 source는:

```c
assert (thread_p->type != TT_LOADDB || is_transaction_lock);
```

로 transaction key만 허용한다 (`lock_manager.c:3484, 3539-3543`). `lock_object`의 TT_LOADDB branch와 세 object-lock lookup redirect는 그대로이므로 CBRD-23375의 class/instance object-lock 금지는 유지된다.

## 6. Success, wait, retry, error, abort, shutdown

### Generic lock state machine

- 빈 resource: holder entry를 만들고 즉시 grant한다.
- 기존 resource, 다른 transaction과 compatible: holder list와 transaction hold list에 넣고 grant한다.
- incompatible conditional/zero wait: timeout/no-grant를 반환하고 임시 entry를 정리한다.
- incompatible unconditional: waiter entry를 queue하고 resource mutex를 놓은 뒤 suspend한다.
- 같은 transaction의 다른 thread가 이미 기다리면 wait train에 연결한 뒤 처음부터 재평가한다.
- wakeup이 timeout/deadlock victim/interrupt이면 waiter 또는 blocked holder 정보를 제거하고 각각 timeout/aborted/error로 반환한다.
- 정상 wakeup은 post-grant를 거쳐 caller에게 entry를 돌려준다.
- unlock은 holder/waiter를 제거하고 compatibility를 다시 계산하여 blocked holder/waiter를 grant하며, holder/waiter/non2pl이 모두 비면 resource를 hash에서 제거한다.

### Self-lock-specific success/error

- 정상 main MVCCID X self-lock은 transaction end까지 `inst_hold_list`에 있다.
- 동일 transaction이 같은 key를 다시 요청하면 entry count가 늘 수 있다. waiter의 짧은 S lock과 subtransaction X lock을 명시 해제할 때는 decrement가 아니라 full release한다.
- assignment choke point의 X acquire 실패는 log만 남기고, heap ensure가 error를 statement에 전달한다.
- unique/FK waiter는 transaction의 `wait_msecs`를 따른다. timeout/deadlock/interrupt는 generic lock error path를 그대로 탄다.
- worker batch는 `TRAN_LOCK_INFINITE_WAIT`로 생성되지만 자기 fresh MVCCID X 요청이 실제로 기다리지 않는다는 보장은 source의 fresh/unique ID 전제에 기댄다. `get_new_mvccid`는 mutex 아래 `mvcc_next_id`를 한 번씩 전진시킨다. “현실적 lifetime에서 다른 transaction이 fresh key를 먼저 알 수 없다”는 강한 source inference이며 runtime contention 측정은 없다.

### OOS/file error cleanup

- `heap_attrinfo_insert_to_oos`의 일반 실패는 준비한 payload를 cleanup한다.
- `heap_oos_find_vfid`의 create/TDE/publication 실패는 outer sysop을 abort하고 heap header page를 unfix한다.
- `oos_create_file_internal`의 sticky header 생성 실패는 nested sysop을 abort하고 page를 unfix한다.
- `file_create`의 ordinary error는 fixed page를 unfix하고, 시작한 permanent sysop을 abort하고, output VFID를 NULL로 만들고, allocation buffer를 해제한다.
- 역사적 debug assert의 `SIGABRT`는 C control-flow의 `goto exit`를 실행하지 않는다. crash recovery가 permanent sysop/disk reservation을 어떻게 정리하는지 전체 recovery path는 이번 범위에서 완전 추적하지 않았다.

### Session shutdown

정상 `loaddb_destroy`는 worker만 모두 끝내고 load session object를 삭제한다. class BU는 load session object가 아니라 connection/session transaction의 lock table entry다. 이후 명시 commit/abort 또는 client shutdown/connection unregister가 session transaction을 끝낼 때 해제된다. object-only loaddb의 outer flow는 최종 `db_shutdown()`으로 간다. `db_shutdown`은 설정과 transaction update 상태를 고려한 client shutdown 후 unregister를 수행하고, server의 `xboot_unregister_client`는 남은 active transaction을 abort한다. 따라서 “`sloaddb_destroy`가 BU를 직접 푼다”는 설명은 틀리다.

## 7. Configuration과 observability

### Configuration

- `lock_transaction_mvccid(..., UNCOND)`는 caller transaction descriptor의 `wait_msecs`를 쓴다 (`lock_manager.c:6478-6489`, `log_tran_table.c:2583-2605`). client/session parameter `lock_timeout`의 기본값은 infinite이며 deprecated `lock_timeout_in_secs`도 존재한다 (`system_parameter.c:1303-1324`).
- loaddb worker batch는 생성 시 `TRAN_LOCK_INFINITE_WAIT`를 직접 받는다 (`load_session.cpp:151-153`).
- `monitor_waiting_thread`는 generic object APIs 주위의 경고를 켜지만, `lock_transaction_mvccid` wrapper 자체에는 같은 elapsed warning wrapper가 없다. internal perf counter는 transaction resource에도 공통 적용된다.
- BU compatibility나 “TT_LOADDB transaction self-lock 허용”을 runtime parameter로 바꾸는 설정은 조사 범위에서 찾지 못했다. 둘은 compile-time table/assert policy다.

### Observability

- `xlock_dump`/lock dump는 transaction resource를 `Transaction self-lock (inserter MVCCID = ...)`로 표시한다 (`lock_manager.c:5611-5616, 5734-5736`).
- event log의 blocked/blocker lock info도 transaction resource를 `(transaction self-lock, mvccid=...)`로 표시한다 (`lock_manager.c:10090-10095`).
- `LK_DUMP` build의 internal acquire trace는 object OID 대신 MVCCID를 출력한다 (`lock_manager.c:3548-3568`).
- SystemTap acquire marker는 transaction resource의 OID가 없어서 null OID marker를 사용한다. marker만 보면 object/transaction을 구분하기 어렵다.
- perf counters `PSTAT_LK_NUM_ACQUIRED_ON_OBJECTS`, `...WAITED_ON_OBJECTS`와 mode별 wait time은 transaction resource도 generic internal function을 통과하므로 함께 증가한다. 별도 “self-lock count” counter는 찾지 못했다.
- **관측 한계/현재 source 결함 후보**: timeout error switch는 transaction resource case에서도 union의 OID member를 simple object timeout message 인자로 넘긴다 (`lock_manager.c:2215-2222`). dump/event log는 MVCCID를 정확히 쓰지만 user timeout message의 OID 숫자는 의미가 없을 수 있다. 고정 branch 밖의 `f3e7f8595 [CBRD-27155]`가 이 계열 개선을 가리키지만 현재 pinned source에는 반영되지 않았다.

## 8. Claim candidates

아래는 `claims.jsonl`로 승격할 수 있는 후보다. `source_refs`의 file hash는 4절 표와 같다.

공통 field는 `database="cubrid"`, `revision="f11fc42594732c263d8f10101f9df73a21346ee9"`, `runtime_run_ids=[]`다. 각 source ref는 4절의 정확한 `path`, `symbol`, `line_start`, `line_end`, `file_sha256`를 사용하고 `evidence_state="COMMIT"`로 확장한다. `report_locations`는 아직 Book anchor가 없으므로 packet 단계에서는 비워 둔다. 역사적 parent blob을 사용하는 CUBRID-C012만 pinned-source JSON claim과 분리한다.

### CUBRID-C001 — resource identity와 owner

- **claim_ko**: CUBRID lock resource는 type이 identity 일부이며 object resource는 OID, transaction self-lock은 full MVCCID를 key로 쓴다. 각 holder/waiter entry의 owner는 `tran_index`다.
- **database**: `cubrid`
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `lock-resource-owner-lifecycle`
- **source_refs**: `lock_manager.h:75-101 (LK_ENTRY)`, `lock_manager.h:151-210 (LK_RES_KEY)`, `lock_manager.c:865-960 (lock_res_key_compare/hash)`
- **limitations_ko**: hash bucket collision이 없다는 주장이 아니다. collision은 compare가 구분한다.

### CUBRID-C002 — BU compatibility

- **claim_ko**: `BU_LOCK`은 같은 BU 및 `SCH_S_LOCK`과 호환되고 일반 data access의 `IS/S/IX/SIX/X` 및 `SCH_M_LOCK`과 충돌하는 class-level bulk update mode다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `lock-resource-owner-lifecycle`
- **source_refs**: `lock_table.h:36-52 (LOCK)`, `lock_table.c:30-131 (lock_Comp)`
- **limitations_ko**: mode table만으로 SQL operation마다 실제 요청하는 mode 전체를 증명하지는 않는다.

### CUBRID-C003 — loaddb session BU와 worker object-lock redirect

- **claim_ko**: server-side loaddb는 class install request의 session transaction이 class BU를 얻고, TT_LOADDB batch worker의 object lock acquire/query는 실제 worker object entry 대신 session BU를 확인하도록 우회된다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `lock-resource-owner-lifecycle`
- **source_refs**: `load_server_loader.cpp:118-181 (server_class_installer::locate_class)`, `locator_sr.c:1017-1162 (xlocator_find_class_oid)`, `lock_manager.c:6238-6435 (lock_object)`, `lock_manager.c:7473-7696 (lock_get_object_lock, lock_has_lock_on_object)`
- **limitations_ko**: transaction self-lock은 object query redirect 대상이 아니다.

### CUBRID-C004 — worker batch transaction lifetime

- **claim_ko**: accepted loaddb batch는 별도 active transaction index를 얻고, 성공 시 batch 순서대로 commit하며 실패 시 abort한 뒤 transaction index를 free한다. client identity 복사는 transaction/lock ownership 공유가 아니다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `lock-resource-owner-lifecycle`, `loaddb-oos-regression`
- **source_refs**: `load_session.cpp:90-232 (load_task)`, `load_session.cpp:306-452 (session completion/interrupt)`
- **limitations_ko**: worker pool scheduling의 모든 interleaving은 runtime으로 검증하지 않았다.

### CUBRID-C005 — MVCCID X self-lock invariant

- **claim_ko**: active worker가 main/sub MVCCID를 발급받을 때 같은 MVCCID transaction resource에 X self-lock을 시도하고, heap의 observable INSID producer는 error-propagating ensure를 거쳐 stamp 전에 lock 실패를 드러낸다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `mvccid-self-lock-rendezvous`
- **source_refs**: `log_tran_table.c:4053-4192 (self-lock helpers)`, `log_tran_table.c:4886-4927 (sub ID assignment)`, `heap_file.c:21570-21665 (heap_get_insert_location_with_lock)`, `heap_file.c:24757-24776 (update ensure)`
- **limitations_ko**: assignment choke point 자체는 best-effort이고, 안전한 error propagation은 observable heap path의 ensure에 의존한다.

### CUBRID-C006 — unique/FK waiter rendezvous

- **claim_ko**: unique/FK 검사자가 active other INSID를 만나면 page latch와 보유 object lock을 놓고 MVCCID resource에 S lock으로 기다린 후, lock을 즉시 풀고 active 상태와 B-tree 결과를 다시 검사한다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `mvccid-self-lock-rendezvous`
- **source_refs**: `btree.c:24228-24334 (wait helpers)`, `btree.c:24451-24476 (unique caller)`, `btree.c:24774-24799 (nonunique-system-index caller)`, `btree.c:27365-27475 (FK caller)`
- **limitations_ko**: SQL-level runtime은 별도 experiment가 필요하다.

### CUBRID-C007 — complete-before-unlock ordering

- **claim_ko**: main transaction commit/abort와 subtransaction end는 MVCCID를 inactive로 만든 뒤 self-lock을 해제하므로, 정상 wakeup 뒤 waiter의 active recheck는 false여야 한다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `mvccid-self-lock-rendezvous`
- **source_refs**: `log_manager.c:5193-5312 (log_commit_local)`, `log_manager.c:5314-5384 (log_abort_local)`, `log_tran_table.c:4945-4987 (logtb_complete_sub_mvcc)`, `lock_manager.c:7353-7428 (lock_unlock_all)`
- **limitations_ko**: crash recovery의 모든 timing을 포함한 보장은 아니다.

### CUBRID-C008 — bulk row의 current source behavior

- **claim_ko**: session BU를 가진 loaddb bulk insert는 `is_bulk_op`으로 전달되어 heap record INSID를 제거하고 class IX 및 per-row object lock을 생략한다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `mvccid-self-lock-rendezvous`, `loaddb-oos-regression`
- **source_refs**: `locator_sr.c:5058-5066 (locator_insert_force)`, `heap_file.c:21162-21303 (heap_insert_adjust_recdes_header)`, `heap_file.c:21570-21685 (heap_get_insert_location_with_lock)`, `heap_file.c:24278-24386 (heap_insert_logical)`
- **limitations_ko**: 모든 loaddb operation이 bulk row insert라는 뜻은 아니다. OOS transform/file metadata는 physical bulk context 전에도 실행된다.

### CUBRID-C009 — current bulk path의 observer 부재

- **claim_ko**: 현재 bulk row는 INSID를 기록하지 않으므로 unique/FK scan이 그 row metadata에서 loaddb worker MVCCID를 발견해 self-lock을 기다리는 경로는 형성되지 않는다.
- **kind/confidence**: `inference` / `INFERRED`
- **central behavior**: `mvccid-self-lock-rendezvous`
- **premises**: CUBRID-C006, CUBRID-C008
- **falsifier**: bulk row/index representation 또는 다른 shared metadata에 worker MVCCID가 노출되어 unique/FK waiter가 이를 입력으로 쓰는 reachable path를 발견하는 경우.
- **limitations_ko**: repository 전체의 미래/플러그인 경로 부재를 증명하지 않는다.

### CUBRID-C010 — OOS lazy-create trigger

- **claim_ko**: 첫 OOS demotion은 heap header에 OOS VFID가 없을 때 `FILE_OOS`를 lazy create하며, `file_create`의 dropped-file VFID 안전 검사가 current MVCCID를 요구해 loaddb worker의 lazy self-lock을 촉발한다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `loaddb-oos-regression`
- **source_refs**: `load_server_loader.cpp:691-734 (finish_line)`, `heap_file.c:13064-13194 (transform internal)`, `heap_oos.cpp:622-659 (heap_oos_insert_serialized_values)`, `heap_file.c:12241-12351 (heap_oos_find_vfid)`, `oos_file.cpp:968-1078 (oos_create_file)`, `file_manager.c:3320-3483 (file_create)`
- **limitations_ko**: OOS value CRUD/vacuum 전체 설계를 설명하는 claim이 아니다.

### CUBRID-C011 — current fix boundary

- **claim_ko**: 고정 리비전은 TT_LOADDB가 `LOCK_RESOURCE_TRANSACTION`을 획득하는 것만 internal assert에서 허용하고, class/instance object lock의 session-BU 우회 계약은 유지한다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `loaddb-oos-regression`
- **source_refs**: `lock_manager.c:3484-3543 (lock_internal_perform_lock_object)`, `lock_manager.c:6238-6317 (lock_object)`, `lock_manager.c:7473-7696 (object lookup redirect)`
- **limitations_ko**: 수정 전 crash는 historical parent blob/기존 runtime evidence로 별도 증명해야 한다.

### CUBRID-C012 — historical regression reconstruction

- **claim_ko**: CBRD-26942의 assignment-time self-lock과 OOS `FILE_OOS` lazy creation이 합쳐져 수정 전 무조건 TT_LOADDB assert를 통과하면서 debug/optdebug abort 경로가 되었다.
- **kind/confidence**: `documented-intent` 또는 history-source 별도 분류 / `DOCUMENTED`
- **history refs**: `741734a8f3785a3e2a678bb52e289000c2261b6f`, CBRD-27157 fix `8bcfd7dd278cbe2b16a064bce4105e68cf80d6a1`, fix parent `23c0bbae350f8f7c5db187c6176d205bb2079e6f`의 `lock_manager.c:3539`, local JIRA issue file lines 29-55.
- **limitations_ko**: pinned current source만으로 “실제로 SIGABRT가 관찰됐다”는 runtime claim을 만들 수 없다. 기존 CI/core 기록을 frozen run에 import하거나 A/B experiment가 필요하다.

### CUBRID-C013 — ordinary error와 transaction cleanup

- **claim_ko**: worker success/abort는 standard transaction boundary에서 self-lock을 포함한 hold list를 해제하고, ordinary OOS/file creation error는 sysop abort, page unfix, payload/allocation free 경로를 가진다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **central behavior**: `lock-resource-owner-lifecycle`, `loaddb-oos-regression`
- **source_refs**: `load_session.cpp:175-225 (load_task end)`, `log_manager.c:5193-5384 (commit/abort)`, `lock_manager.c:7353-7428 (lock_unlock_all)`, `heap_file.c:12241-12351,12516-12580`, `file_manager.c:3867-3923 (file_create exit)`
- **limitations_ko**: process abort 뒤 crash recovery의 sector/file cleanup은 별도 trace/experiment가 필요하다.

### CUBRID-C014 — diagnostics

- **claim_ko**: lock dump와 event log는 transaction self-lock의 MVCCID를 출력하고 generic lock acquire/wait counters는 이를 포함하지만 별도 self-lock counter는 없다.
- **kind/confidence**: `source` / `SOURCE-CONFIRMED`
- **source_refs**: `lock_manager.c:3548-3568`, `lock_manager.c:5585-5775 (lock_dump_resource)`, `lock_manager.c:4057-4083 (wait perf)`, `lock_manager.c:10072-10135 (lock_event_log_lock_info)`
- **limitations_ko**: timeout user message는 현재 transaction key를 OID 형태로 잘못 표현할 수 있다.

## 9. Unknowns와 central runtime evidence gaps

1. **수정 전/후 A/B runtime**: 고정 run에는 parent debug binary 실행과 core stack artifact가 없다. JIRA/commit message에는 기존 CTP와 CI 결과가 있으나 이 run의 `runtime_run_id`가 아니다.
2. **OOS physical placement 확인**: 큰 값의 logical round-trip만으로 OOS demotion과 first-file create를 직접 증명할 수 없다. OOS stats/heap header 또는 trace를 함께 캡처해야 한다.
3. **fresh self-X가 정말 0 wait인지**: ID allocator와 key visibility로 강하게 추론되지만 wait counter/trace를 수집하지 않았다.
4. **session BU의 정확한 정상 release 순간**: object-only loaddb는 최종 shutdown/unregister에서 끝나고, 뒤이어 index/trigger transaction commit이 있으면 더 일찍 끝날 수 있다. 전체 option 조합별 timeline runtime은 없다.
5. **historical SIGABRT 뒤 recovery**: ordinary error cleanup은 source-confirmed지만 process abort 뒤 reserved sector, partial file tracker, heap OOS VFID가 restart recovery에서 어떻게 정리되는지 end-to-end trace하지 않았다.
6. **모든 TT_LOADDB MVCCID 요구 경로**: `logtb_get_current_mvccid`의 static callers와 loaddb reachable path를 조사했지만, function pointer/macro/미래 module까지 포함해 OOS lazy create가 유일하다는 절대 negative는 확정하지 않는다.
7. **2PC/XA 특수 경로**: current self-lock code에는 prepare-time fallback/reacquire가 있으나 CBRD-27157의 local batch commit 중심 범위를 넘어 완전 추적하지 않았다.
8. **timeout message 품질**: transaction resource timeout case가 OID union을 출력하는 실제 사용자 메시지를 runtime에서 재현하지 않았다.

이 중 1, 2, 3은 central behavior readiness에 직접 영향을 준다. source만으로 책을 설명할 수는 있지만 concurrency/crash claim을 `SOURCE+RUNTIME-CONFIRMED`로 올릴 수 없다.

## 10. Negative searches

- `unit_tests`, `src`, top-level tracked tree에서 `CBRD-27157`, `lock_transaction_mvccid`, `self_locked_mvccid`, `TT_LOADDB`, `LOCK_RESOURCE_TRANSACTION`, `BU_LOCK`, `loaddb.*OOS`를 검색했다. self-lock/CBRD-27157 전용 unit test는 찾지 못했다. OOS unit test는 `heap_oos_find_vfid` create path를 다루지만 loaddb transaction ownership/assert regression을 직접 다루지 않는다.
- tracked tree에서 기존 CTP 이름 `cbrd_25481`, `itrack_10006`, `bug_xdbms_sus880`를 검색했으나 testcases는 이 source repository에 없었다. local JIRA가 private CTP/CI evidence를 가리킨다.
- `BU_LOCK` call sites를 `src`의 C/C++ 파일에서 모두 검색했다. loaddb acquisition은 `load_server_loader.cpp`의 `xlocator_find_class_oid(..., BU_LOCK)`이고, worker-side use는 lock manager redirect 및 heap/btree assertions였다. transaction self-lock API에 BU를 전달하는 caller는 없었다.
- `FILE_OOS`, `file_create`, `heap_oos_find_vfid`를 source와 unit tests에서 검색했다. CBRD-27157 경로는 `heap_oos_find_vfid(docreate=true) -> oos_create_file -> file_create(FILE_OOS)`로 확인되었고, OOS가 `lock_object`를 직접 호출하는 경로는 찾지 못했다.
- `lock_timeout`, `monitor_waiting_thread`, lock dump/event log/perf symbol을 검색했다. self-lock 전용 runtime parameter나 전용 perf statistic은 찾지 못했다.
- `session_destroy_load_session`, connection close, `net_server_conn_down`, `xboot_unregister_client`를 따라 shutdown을 확인했다. `sloaddb_destroy` 자체가 BU lock을 명시 해제하는 call은 찾지 못했다.
- `git log/blame/show`로 CBRD-23375, CBRD-26942, CBRD-27157 도입 commit을 확인했다. current source 설명과 역사적 parent assert를 구분했다.

## 11. Contradictions와 주의할 기존 설명

1. local lesson `0001-loaddb-bu-lock-and-mvccid-self-lock.html:172-180`은 두 설계 중 maintainer 정책이 아직 결정되지 않았다고 적었다. 이후 local JIRA triage lines 5-13과 fix commit은 “skip 대신 uniform transaction self-lock”이 합의/적용되었다고 기록한다. 새 책은 lesson의 설계 질문을 역사로 소개하되 현재 미결정처럼 쓰면 안 된다.
2. JIRA/commit message는 release에서 assert가 compile-out되어 이미 동작했다고 말하지만 release runtime은 검증하지 않았다고 스스로 한정한다. “release에서 실측 성공”이라고 바꾸면 안 된다.
3. 기존 문서는 “확인된 범위에서 OOS lazy create가 유일한 TT_LOADDB MVCCID entry”라고 쓴다. 이 표현은 유지할 수 있으나 “repository 전체에서 절대 유일”로 강화하면 안 된다.
4. 기존 lesson의 “BU 때문에 observer가 없다”는 설명은 shorthand다. 정확한 mechanism은 (a) BU가 IS/S/IX/SIX/X와 충돌하고, (b) current bulk heap row가 INSID를 제거하며, (c) unique/FK self-lock wait는 active other INSID에서 시작한다는 세 전제를 함께 써야 한다. BU는 `SCH_S`와 다른 BU를 막지 않는다.
5. `lock_internal_perform_lock_object`라는 옛 function name 때문에 모든 resource를 “object lock”이라 부르기 쉽다. 현재 interface는 `LK_RES_KEY`를 받아 transaction resource도 처리한다. 책에서는 engine 이름과 conceptual resource를 분리해야 한다.
6. current timeout error switch는 transaction resource를 simple OID message로 표현하지만 dump/event log는 MVCCID를 표현한다. “모든 diagnostics가 MVCCID를 정확히 표시한다”는 주장은 틀리다.

## 12. Suggested experiments

기존 scaffold 3개를 다음 방식으로 강화하면 central behavior를 직접 검증하기 좋다.

### Experiment A — 일반 transaction lock lifetime 입문

- T1이 row update 후 sleep, T2가 same row update.
- T1 rollback 전 T2가 block되고 이후 진행하는지 elapsed time과 결과를 캡처한다.
- 이 실험은 lock lifetime 입문용이며 BU/MVCCID resource identity를 직접 증명하지 않는다고 명시한다.

### Experiment B — unique MVCCID rendezvous

- T1이 unique key insert 후 sleep/rollback, T2가 같은 key insert.
- T2가 wait 뒤 성공하고 최종 row가 T2 것인지 확인한다.
- 동시에 `xlock_dump` 또는 event log를 캡처하여 `(Transaction self-lock, MVCCID=M)`, T1 X holder, T2 S waiter를 source claim과 연결한다.
- waiter가 page latch를 놓았는지는 SQL만으로 볼 수 없으므로 source evidence로 남긴다.

### Experiment C — pinned debug OOS loaddb

- compressibility 영향을 줄이기 위해 큰 `BIT VARYING` 값을 source DB에서 만들고 `unloaddb`, 새 DB에 `loaddb -C`한다.
- loaddb 성공, server 생존, row/value 동일성을 확인한다.
- OOS stats나 heap header의 non-null OOS VFID를 추가 확인하여 실제 lazy create를 증명한다.
- 첫 load와 두 번째 load를 나눠 첫 create에서만 경로를 밟는지 비교한다.

### Experiment D — 수정 전/후 debug A/B

- parent `23c0bbae...`와 fix `8bcfd7dd...`를 같은 debug preset/config/input으로 별도 격리 build한다.
- parent는 assert stack과 core, fix는 success를 캡처한다.
- source/DB 디렉터리를 별도로 두고 cleanup manifest를 사용한다.
- release build 비교는 “assert compile-out”을 확인하는 보조 실험이며 debug 결과와 섞지 않는다.

### Experiment E — abort cleanup과 lock leak

- OOS request preparation 또는 insert failure를 안전한 test hook으로 유발해 worker batch abort를 만든다.
- abort 뒤 lock dump에서 worker MVCCID resource가 사라지고, 다음 transaction이 같은 unique key를 무한 대기하지 않는지 확인한다.
- file create ordinary error와 process SIGABRT는 cleanup semantics가 다르므로 두 실험을 분리한다.

### Experiment F — fresh X self-lock non-wait

- `LK_DUMP`/perf activation으로 여러 loaddb batch가 동시에 처음 MVCCID를 받게 한다.
- 각 worker X acquire가 unique MVCCID이고 wait counter를 올리지 않는지 캡처한다.
- 이 결과가 있어야 “fresh X never waits”를 source inference에서 source+runtime으로 올릴 수 있다.

## 13. Book 저자에게 권하는 설명 순서

1. mutex/latch/transaction lock lifetime 차이
2. resource key, mode, owner, holder/waiter, lifetime 다섯 질문
3. class/instance hierarchy와 BU compatibility
4. session transaction과 worker batch transaction 분리
5. MVCCID/INSID와 X/S rendezvous
6. bulk row의 INSID/per-row-lock 생략
7. OOS lazy create가 숨은 MVCCID allocation을 연 call path
8. 수정 전 broad assert와 현재 transaction-only exception
9. commit/abort ordering, timeout, dump, runtime evidence 한계

각 그림의 화살표에는 최소한 `resource`, `owner`, `mode`, `release point` 네 가지를 표시해야 한다. 특히 “BU가 self-lock을 대신한다” 또는 “worker가 session lock을 소유한다”는 문장을 사용하지 않는다.
