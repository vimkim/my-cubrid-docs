# CBRD-27230 상세 설계: A' 위에서 미할당 OOS chain 재사용

- 작성: 2026-11-13. 기준 revision `b049fa155c` (PR #8434 head, `vk/CBRD-27781-postpone-commit`). 엔진 코드 변경 없음.
- 범위: 확정된 A' 아키텍처 안의 세부 선택(Stage 1). TLA+ 검증(Stage 2) 결과는 [§9](#9-tla-검증-결과)와 [모델 디렉터리](../oos/reclaim-model/)에 있다.
- 다시 열지 않는 결정: 알림 로그 아키텍처, commit 뒤 postpone 발행(A', 2026-11-05), ADR-0008 회수기, forward-walk 제거.
- 근거 표기: **[V]** 는 기준 revision 소스에서 확인, **[I]** 는 추론, **[M]** 은 TLA+ 모델 결과다.

## 0. 목표와 결론 요약

UPDATE가 할당하지 않은 OOS 컬럼은 옛 버전의 24B stub을 새 버전에 그대로 복사한다. `oos_read` 와 `oos_insert` 를 하지 않는다. 버려진 chain만 PR #8434의 A' postpone이 commit 뒤 vacuum에 알린다.

기준 revision에서 이미 끝난 것과 남은 것은 다음과 같다.

| 항목 | 상태 (b049fa155c) |
|---|---|
| `RVOOS_UPDATE_DROP_POSTPONE` → `RVOOS_NOTIFY_VACUUM` (명시적 MVCCID), vacuum 소비자 | 구현됨 [V] `oos_file.cpp:3963`, `:4102`, `vacuum_oos.cpp:236` |
| 버린 chain 계산 = 옛 stub − 새 stub (head OID 비교) | 구현됨, 재사용에 안전 [V] `heap_oos.cpp:965-969`, `oos_util.cpp:38` |
| forward-walk (`vacuum_forward_walk_reclaim_oos`) | 제거됨 [V] (unit test 주석 1곳만 남음) |
| 미할당 컬럼 stub 보존 (쓰기 경로) | **미구현**: `heap_attrinfo_set_uninitialized` 가 `oos_read` 로 값을 읽는다 [V] `heap_file.c:13765` → `heap_oos_value_ref.cpp:111` |
| 복제 marker, replica fixup, applylogdb | **미구현** |
| 재사용 금지 경로(partition 이동, representation 변경) 처리 | **미구현** |

따라서 CBRD-27230의 남은 구현은 쓰기 경로와 복제다. 회수 쪽은 #8434의 set-difference가 이미 재사용을 견딘다. 이 문서는 그 전제를 TLA+로 확인한다([§9](#9-tla-검증-결과)).

## 1. 미할당 신호를 디스크 writer까지 전달하는 방법

**문제 [V].** `qexec_execute_update` 는 행마다 모든 slot을 `HEAP_UNINIT_ATTRVALUE` 로 되돌리고, 할당한 값만 `WRITTEN` 으로 만든다 (`query_executor.c:16265`, `:16373`). `heap_attrinfo_transform_to_disk_internal` (`heap_file.c:15001`) 은 맨 먼저 `set_uninitialized` (`:15025`) 를 불러 UNINIT slot을 읽어 `READ` 로 바꾼다. 이때 OOS 값을 Resolve한다. 그 뒤 `determine_disk_layout` (`:15037`) 시점에는 `READ` 가 "미할당"인지 "호출자가 미리 읽은 값"(예: `serial.c:1575`)인지 구분할 수 없다. 따라서 결정은 `set_uninitialized` 이전이나 그 안에서 해야 한다.

| 후보 | 내용 | 판정 |
|---|---|---|
| A. 새 `HEAP_ATTRVALUE` 상태 + 24B 보관 | slot 상태에 "재사용 stub"을 추가 | 기각. `HEAP_ATTRVALUE` 는 query 모듈과 공유되고 상태 참조가 42곳이다 (`fetch.c:1673`, `btree.c:21604`, `partition.c:4962` 등). 빈 dbvalue를 가진 non-UNINIT slot은 조용히 NULL로 읽힌다 |
| **B. column plan이 운반 (채택)** | `heap_oos_column_plan` (`heap_file.c:756`) 에 `reused` 플래그와 24B stub. `set_uninitialized` 이전에 한 predicate가 정하고, `set_uninitialized` 는 해당 slot의 read를 건너뛴다 | 채택. plan은 이미 지역 변수로 layout, writer, finalize를 지난다 (`:15003`, `:15037`, `:15132`). 값의 종류(inline / 새 chain / 재사용 stub)는 닫힌 variant이고 plan이 이미 그것을 담는다 |
| C. lazy resolve (`HEAP_LAZY_ATTRVALUE`) | 읽기를 지연 | 기각. attr_info 전체 단위이고 scan용으로 맞춰져 있다. `locator_update_force` 의 partition 이동 지점에는 attr_info가 없어 resolve를 걸 수 없다 |

**B의 세부 [V/I].**

- `set_uninitialized` 는 계속 호출한다. `inst_chn` 을 옛 레코드에서 복사하는 일(`heap_file.c:13749-13760`)이 남아 있기 때문이다. 재사용 slot만 `heap_attrvalue_read` 를 건너뛴다.
- stub은 `heap_recdes_get_oos_inline_stub` (`:11644`) 로 24B를 그대로 복사한다. OID, 길이, stamp를 다시 pack하지 않는다 (stamp pack/unpack이 무손실이어도 raw copy가 더 단순하다).
- layout (`heap_attrinfo_determine_disk_layout`): 재사용 컬럼은 `column_size = OR_OOS_INLINE_SIZE`, `selected = true`, `has_oos = true` 이다. FORCE_OUTLINE 선택(`:13941`)과 demotion 후보(`:13983`)에서 빠지고, gate(`:13966`)와 bigone guard(`:15063`)에는 24B로 계산된다. 재사용 stub은 다시 inline으로 돌아가지 않는다(사양 §3이 허용).
- writer는 기존 stub writer 경로(`:14801-14804`)에서 plan의 24B를 쓴다. `:14775` 의 assert를 완화한다.
- insert 요청 수집(`:14299`)과 pending retain(`:15083`)은 재사용 항목을 건너뛴다.
- finalize(`heap_oos.cpp:229`)는 현재 memory가 아닌 stub을 만나면 오류를 낸다. 같은 heap이면 재사용 stub을 건너뛰고, 다른 heap이면 §3의 materialize를 한다.

## 2. 재사용 자격 (한 predicate)

재사용은 아래를 모두 만족할 때만 한다. 하나라도 어긋나면 오늘의 경로(Resolve 후 새 chain)로 간다. 오늘의 경로는 이미 정확하므로 보수적인 거절은 성능만 잃는다.

| 조건 | 이유 |
|---|---|
| `transform_to_disk_internal` 의 `pending != nullptr` 경로 (`locator_attribute_info_force` 만) | serial.c 와 재평가 copy-area(`locator_sr.c:14805`)를 그대로 둔다 [V] |
| slot이 UNINIT이고 `do_increment == 0` | `qexec_execute_increment` 가 UNINIT slot에 증가를 건다 (`query_executor.c:20322`) [V] |
| 옛 레코드의 해당 속성이 OOS stub (VOT `IS_OOS`) | inline 값은 재사용할 것이 없다 |
| 옛 레코드가 **잠긴 최신 버전**이다 | `locator_attribute_info_force` 는 `heap_get_last_version` 계열로 최신 버전을 `DONT_CONSUME_RAW_BYTES` 로 가져온다 (`locator_sr.c:8416-8440`) [V]. snapshot으로 보이는 옛 버전의 stub은 동시 commit UPDATE가 이미 버린 chain을 되살린다 [M: `snapshot_source` 통제] |
| 옛 레코드의 repid = `last_classrepr->id` 이고 속성 domain이 같다 | header는 항상 최신 repr id를 쓴다 (`heap_file.c:14548`). 옛 stub 위치는 `read_attrepr->location`, 새 위치는 `last_attrepr->location` 이다 [V]. 1차 구현은 repr 변경 시 재사용하지 않는다 (후보 B': attr id로 remap 은 후속) |

`STORAGE FORCE_INLINE` 미결 사항 (사양 §1): 정책 변경 전에 demote된 stub은 **재사용한다**(stub을 바꾸지 않음). 2026-11-05 성향("가능한 한 적게 바꾼다")과 맞고, 그 컬럼을 건드리지 않은 UPDATE가 실패하지 않으며 read도 없다. ALTER 사전 검사의 목적은 약해지지만 unload/load가 inline으로 돌리므로 없어지지 않는다. 기준 revision에는 `FORCE_INLINE` 심볼이 아직 없다 [V] (CBRD-27259 진행 중). 이 결정을 바꿀 지점은 위 predicate 하나다.

## 3. 재사용하면 안 되는 경로

| 경로 | 처리 |
|---|---|
| partition 이동 (`locator_move_record`, `locator_sr.c:5909`) | 새 heap, 새 OOS 파일이다. 옛 stub은 원본 OOS 파일의 chain이고 옛 행의 REMOVE가 회수한다 (`vacuum.c:2696`). **후보**: (a) partitioned class는 재사용 금지, (b) 이동 시 재사용 stub만 `oos_read` 후 대상 파일에 insert (materialize), (c) 이동 여부를 transform 전에 결정. **채택 (b)**: 이동은 드물고, finalize의 기존 오류 지점(`heap_oos.cpp:229`)이 바로 그 hook이다. (c)는 pruning 순서를 바꾼다 (`partition_prune_update` 는 transform 뒤 `:6547`) |
| representation 변경 | §2 predicate가 거절 |
| CS 클라이언트 flush (`LC_COPYAREA`) | 레코드가 이미 Expand되어 stub이 없다. 재사용 없음, 오늘과 같다 [V] |
| class 객체, system class | ROOTOID 분기는 OOS가 없다 (`heap_oos.cpp:60`). serial.c는 `pending == NULL` [V] |
| REPLACE | delete + insert, 재사용할 옛 레코드 없음 [V] |
| MERGE update, ODKU | `qexec_execute_update` / 잠긴 `rec_descriptor` 로 같은 경로. 재사용 가능 [V] |

**in-place / non-MVCC update style [V/I].** `!HEAP_UPDATE_IS_MVCC_OP` 경로는 `heap_oos_delete_unreferenced` (`heap_oos.cpp:1042`) 로 commit 때 snapshot 대기 없이 회수한다. 이것도 old − new 차집합이라 새 버전이 재사용한 chain은 남는다. 위험은 다른 곳에 있다. 앞선 MVCC UPDATE가 chain A를 v0과 v1에 공유시킨 뒤, in-place UPDATE가 A를 버리면 eager 회수가 v0을 읽는 snapshot보다 먼저 A를 지울 수 있다. 재사용 전에는 A가 최신 버전 전용이라 이 문제가 없었다. in-place style은 class 수준 배타 잠금 아래에서만 쓰이므로 동시 snapshot이 없다는 것이 현재 판단이다 [I]. **구현 단계 확인 항목**: in-place style 호출자를 전수 조사한다. 배타성이 보장되지 않는 호출자가 있으면 그 경로는 재사용 대상에서 빼거나 vacuum 경유로 바꾼다. 모델의 `no_horizon` 통제가 이 위험의 형태를 보인다.

## 4. 버린 chain 계산과 알림 레코드

**계산 후보.**

| 후보 | 판정 |
|---|---|
| 컬럼별 비교 (`old.c != new.c` 이면 old.c 버림) | 기각. 같은 chain을 두 컬럼이 가리키는 상태를 허용하지 않을 근거가 없다 |
| **old − new 집합, head OID 비교 (채택, #8434에 있음)** | byte copy이므로 OID가 같으면 같은 chain이다 [V] `oos_util.cpp:38-48` |
| old − new 집합, (OID, stamp) 비교 | OID 비교와 결과가 같다. 다르면 버그이므로 assert로 둔다 |

추가할 것:

- debug assert: OID가 같은 두 stub은 stamp도 같다. 새 레코드의 모든 stub은 옛 레코드에 있거나 이번 UPDATE가 새로 만든 것이다. 두 번째 assert가 §2 "잠긴 최신 버전" 조건을 지킨다.
- `heap_oos.cpp:915` 주석 "never shared across rows"를 "새 이미지가 이름을 가진 chain은 남긴다"로 고친다.

**`RVOOS_NOTIFY_VACUUM` 내용과 MVCCID 전달 [V].** 바꿀 것이 없다.

- payload: `oos_update_drop_prefix{mvccid}` + `oos_reclaim_intent_header{oos_vfid=NULL, heap_hfid, owner_oid, flags, n_refs, op_ctx}` + `oos_chain_ref[n]` (head OID, stamp) (`oos_file.cpp:3807-3822`).
- MVCCID: UPDATE 시점의 `logtb_get_current_mvccid` 를 postpone에 실어 둔다 (`:3971`). heap header가 받는 값과 같다 (`heap_update_adjust_recdes_header`, `heap_file.c:23214`).
- commit 순서: `logtb_complete_mvcc` (`log_manager.c:5326`) → `LOG_COMMIT_WITH_POSTPONE` flush (`:4532`, `:4552`) → postpone마다 `log_append_mvcc_undo_data_with_mvccid` (`log_manager.c:2336`, 명시적 MVCCID `log_append.cpp:975-980`) → `LOG_COMMIT` (`:5371`).
- `complete_mvcc` 는 commit 중인 트랜잭션 항목을 `LOG_COMMIT` 까지 자기 MVCCID로 고정한다 (`mvcc_table.cpp:495-507`). 그래서 알림 block은 `LOG_COMMIT` 전에 소비될 수 없다.
- 재사용이 바꾸는 것: 미할당 OOS 컬럼만 있는 UPDATE는 버린 chain이 없어 postpone 자체가 없다 (`heap_oos.cpp:1076-1080`). commit-with-postpone 경로(이중 flush, ADR-0008 결과 8의 복제 손실 창)에 들어가는 트랜잭션이 줄어든다.

**공유 chain에 대한 vacuum 조건 [V/I/M].** chain A를 v0(T0)과 v1(T1, 재사용)이 공유하고 T2(MVCCID m2)가 A를 버린다고 하자. v0이나 v1을 읽을 수 있는 snapshot S는 T2의 commit을 보지 못한다. 그러면 m2가 S의 active 집합에 있거나 S의 next id 이상이므로 `S.lowest_active ≤ m2` 이다. oldest visible은 그 최솟값이므로 m2를 담은 block은 기다린다 (`vacuum.c:3421`, `mvcc_table.cpp:355-418`). 이 논증은 잠금 순서 인과만 쓴다. MVCCID 순서(m1 < m2)는 쓰지 않는다. MVCCID는 첫 쓰기에서 할당되므로 m2 < m1도 가능하다. 모델은 이를 "모든 active snapshot이 T2를 본다"로 추상화한다.

## 5. 부분 rollback에서 postpone 취소

**메커니즘 [V].**

- `log_abort_partial` (`log_manager.c:5708`) 는 savepoint LSA를 `lastparent_lsa` 로 하는 sysop을 만들어 abort한다.
- commit 때 `log_do_postpone` (`:8406`) 은 `[lastparent, END_ABORT]` 범위 안의 postpone을 건너뛴다.
- savepoint 이전의 postpone은 범위 밖이라 실행된다. 경계 포함 버그는 `b7abf652bc` 가 고쳤다 (`:8435-8438`).
- 재시작 쪽 `log_recovery_find_first_postpone` 은 아직 `LSA_LT` 를 쓴다 (`log_recovery.c:6055`). 시작점에만 영향을 주고 `log_do_postpone` 이 다시 거르므로 무해하다고 판단한다 [I].

재사용이 더하는 경우는 하나다. 같은 트랜잭션의 두 statement가 같은 chain을 다룬다. 예: stmt1이 c1을 재사용하고 stmt2가 c1을 할당해 A를 버린 뒤 stmt2만 rollback한다. stmt2의 postpone은 범위 안이라 취소되고 A는 복원된 버전에 남는다 [M: `no_cancel` 통제].

**규칙 (추가).** UPDATE-drop postpone은 transaction보다 먼저 commit하는 nested sysop 안에서 append되면 안 된다. 그런 sysop은 자기 postpone을 즉시 실행한다 (`log_sysop_do_postpone`, `:8359`). 그러면 transaction이 abort해도 알림이 이미 나가 있다. 현재 heap update 경로는 sysop을 열지 않는다 [I]. `oos_log_update_drop_intent` 에 "열린 sysop 없음 또는 attach-to-outer" assert를 둔다. 모델의 `publish_before_commit` 통제가 같은 실패 형태를 보인다.

**테스트 공백 [V].** savepoint 이전에 postpone이 있는 UPDATE-drop 테스트가 없다. 그 경우는 cache가 miss하고 log scan 경로를 탄다. 첫 postpone 이전 crash, 마지막 END와 `LOG_COMMIT` 사이 crash, 중복 알림 개수 검사도 없다.

## 6. commit과 postpone 사이 crash, 복구 재실행

**메커니즘 [V].**

- 재시작 analysis는 `posp_nxlsa` 를 `LOG_COMMIT_WITH_POSTPONE` 에서 잡고, 각 run-postpone END의 `postpone_lsa` 로 옮긴다 (`log_recovery.c:1319`, `:1713-1718`).
- `log_recovery_finish_postpone` (`:4347`) 은 중단된 run sysop을 abort하고, 마지막 END 뒤의 첫 postpone부터 다시 실행한 뒤 `LOG_COMMIT` 을 쓴다.
- 알림 append 뒤, END 전에 crash가 나면 알림이 두 번 남는다. `RVOOS_NOTIFY_VACUUM` 의 undo/redo는 no-op이고 CLR이 없다 (`recovery.c:905-910`).
- 두 번째 회수는 identity stamp 검사로 no-op이 된다 (`oos_fix_expected_chunk`, `oos_file.cpp:3422`). 그 사이 slot이 재사용되었어도 stamp가 다르다. 이 보장은 logging이 켜져 있을 때만 성립한다 (`:2556-2570`).

재사용이 바꾸는 것은 없다. 알림은 새 버전이 이름을 가진 chain을 포함하지 않으므로, 중복 알림이 살아 있는 공유 chain을 가리킬 수 없다 [M: `WitnessDuplicateNotify` 도달, `NoWrongDelete` 통과, `no_identity` 통제에서 실패].

## 7. 복제 (HA applier, applylogdb)

**현재 계약 [V].**

- master는 OOS 값마다 `RVREPL_OOS_INSERT` 아이템을 낸다. 내용은 master `RVOOS_INSERT` WAL의 LSA다. head OID는 wire에 없다 (`replication.c:476-489`, `log_record.hpp:232-237`).
- UPDATE 데이터 아이템은 heap 로그 레코드에 묶이고, applier는 전체 새 레코드(master stub 포함)를 복원한다 (`log_applier.c:4376-4392`).
- replica의 `xlocator_repl_force` (`locator_sr.c:7740`) 는 아이템마다 자기 `oos_insert` 를 한다. 그 뒤 `locator_fixup_oos_oids_in_recdes` (`:15226-15335`) 가 OOS 속성을 위치 순서로 돌며 OID와 stamp를 바꾼다. 개수 불일치는 오류다 (`:15239`, `:15294`, `:15327`).
- replica는 `locator_update_force` 로 MVCC UPDATE를 하므로 `heap_oos_log_update_drop` 과 자기 vacuum이 돈다 (`heap_file.c:26031`, `boot_sr.c:2457`). 따라서 fixup이 replica 자기 OID를 넣지 않으면 replica는 자기 chain을 버리고 외부 OID를 가리킨다. fixup은 정확성에 필수다.

**후보.**

| 후보 | 장점 | 단점 |
|---|---|---|
| **(a) 재사용 marker 아이템 (채택, 이슈 확정 사항)** | 위치·개수 계약 유지. 재사용 시 복제 트래픽도 준다 | 새 rcvindex, 새 `oos_published_ref` 종류, 새 `LC_FLUSH_*`, applier/서버 처리 |
| (a') 데이터 아이템 꼬리에 컬럼 bitmap | 아이템 수 불변 | serial 선례(`replication.c:395-410`)뿐이고 위치 계약이 둘로 나뉜다 |
| (b) 아이템 없이 master 새 stub과 옛 stub 비교 | wire 변경 없음 | relocation과 `RVHF_INSERT_NEWHOME` 은 옛 이미지가 없다 [I]. 서버 쪽 per-slot 플래그가 결국 필요하다 |
| (c) 값을 계속 보냄 | replica 이전 버전에 의존하지 않는다. 불일치가 다음 UPDATE에서 치유된다 | master가 `oos_read` 와 복제 전용 값 레코드를 다시 해야 해서 이슈 목적의 절반을 잃는다 |

**(a) 세부.**

- master: 재사용 컬럼마다 `thread_p->oos_oids` 에 `reused` 종류 항목을 넣는다. 데이터 아이템 앞에 LSA 없는 `RVREPL_OOS_REUSE` 를 낸다. queue pop은 하지 않는다 (`replication.c:476-489` 의 빈 queue assert 회피).
- replica: marker 위치에서 `oos_insert` 없이 "재사용" 표시를 vector에 넣는다. fixup은 그 속성의 stub을 replica **최신** 버전에서 **attr id로** 찾아 복사한다. 위치 순서가 아니다. `heap_attrinfo_set_uninitialized` 가 옛 representation을 다루는 방식이 본보기다.
- 이전 버전 fetch: `locator_repl_prepare_force` 는 이미 비확장 fetch다 (`locator_sr.c:7653`). 이슈의 "비확장 fetch로 전환" 단계는 이미 끝났다 [V]. 지금은 CHN만 쓰므로, 그 레코드를 fixup까지 넘긴다.
- 실패: 행 없음은 기존 `ER_OBJ_OBJECT_NOT_FOUND` (`:7637-7651`) 로 멈춘다. 속성이 NULL이거나 inline이면 오류다. stub의 8B 전체 길이가 master stub과 다르면 오류다(부분 불일치 탐지).
- **잔여 위험 [I].** replica가 이미 갈라져 있으면 (`ha_applylogdb_ignore_error_list` 등) 재사용은 낡은 값을 계속 유지한다. 오늘은 매 UPDATE가 전 값을 다시 보내 치유한다. 길이 검사로 일부만 잡는다. 갈라진 replica는 이미 재구축 대상이므로 수용한다. 이 판단은 checkpoint의 확인 항목이다.

**applylogdb (sql.log) [V/I].** 현재 OOS stub은 master head OID를 키로 하는 트랜잭션 범위 cache에서 값을 찾는다 (`log_applier.c:3878`, `:3949`, `:4155-4185`). 재사용 컬럼은 아이템이 없어 miss가 나고 `ER_FAILED` 가 된다. 그 행은 적용되고 오류만 sql.log에 남는다 (`:6084-6089`).

| 후보 | 판정 |
|---|---|
| **1. 재사용 컬럼을 SET에서 뺀다 (채택)** | `sl_print_update_att_set` 은 할당된 컬럼만 출력한다. 재사용 컬럼은 정의상 미할당이므로 의미가 같다 (`log_applier_sql_log.c:101-113`) |
| 2. replica DB에서 값을 읽는다 | sql.log는 flush 전에 쓰이고 최대 200 아이템이 미flush다 (`log_applier.c:85`). 같은 batch 앞 UPDATE가 안 보여 강제 flush가 필요하다 |
| 3. 트랜잭션 간 cache | applier 재시작 시 잃는다 |

## 8. 다른 작업과의 상호작용

| 작업 | 상호작용 |
|---|---|
| CBRD-27237 | undo image는 더 이상 삭제 근거가 아니고, drop은 rollback이 취소하는 postpone이다 [V]. 재사용은 그 위에서 공유 chain을 head OID 차집합으로 지킨다 |
| CBRD-27781 / ADR-0008 | `RVOOS_DELETE` redo-only의 전제는 "결정이 최종이다"이다. 공유 chain에서 최종은 할당 UPDATE의 commit과 vacuum horizon이다 (§4) |
| PR #8493 / CBRD-27925 | emptied-page 집합과 growth lock은 페이지가 비었는지만 본다. 재사용 UPDATE는 `RVOOS_INSERT` 를 만들지 않아 rollback 시 insert undo도 없다. 배타성 가정을 찾지 못했다 [I] |
| PR #8495 (CBRD-28046) | 이 tree에 없다. commit-with-postpone의 이중 flush를 없앤다. 재사용은 postpone이 필요한 UPDATE 수를 줄여 같은 방향이다. #8495가 들어오면 §6 순서를 다시 확인한다 |
| ADR-0008 결과 8 (commit postpone 창의 복제 손실) | 재사용은 창에 들어가는 트랜잭션을 줄인다. 반면 잃은 트랜잭션이 남긴 낡은 OOS 값은 이후 재사용 UPDATE가 고치지 않는다 (§7 잔여 위험과 같은 뿌리) |

## 9. TLA+ 검증 결과

모델: [`OosChainReuse.tla`](../oos/reclaim-model/OosChainReuse.tla), 실행기 [`check_reuse.py`](../oos/reclaim-model/check_reuse.py). 기존 `OosReclaim*.tla` 는 바꾸지 않았다. chunk 단위 회수 순서, link stamp, 회수기 재실행은 `OosReclaimDesign`, `OosReclaimRetry` 가 이미 검사하므로 이 모델은 chain을 `<<slot, stamp>>` 하나로 추상화한다.

모델 범위: 한 행, OOS 속성 c1과 c2, 행 잠금으로 직렬화된 UPDATE 트랜잭션 T1과 T2(각 최대 2 statement), statement rollback(반복하면 savepoint rollback), 트랜잭션 rollback, snapshot reader, A' commit(`logtb_complete_mvcc` → `COMMIT_WITH_POSTPONE` → 알림 append → run 표시 → `LOG_COMMIT`), vacuum 알림 소비와 REMOVE, 임의 시점 crash 1회(알림 append 뒤 run 표시 전 crash면 중복 알림), vacuum block 재처리, 해제된 slot의 즉시 재사용.

**속성.**

| 속성 | 종류 | 뜻 |
|---|---|---|
| `NeededChainsLive` | 안전 | heap 레코드(REMOVE 전까지), rollback이나 crash 복구가 되돌릴 수 있는 모든 pre-image, active snapshot이 읽는 버전이 가리키는 chain은 살아 있다 |
| `NoWrongDelete` | 안전 | 회수는 알림이 이름을 가진 chain만 지운다 (중복 알림이 재사용된 slot을 지우지 않는다) |
| `NotifyOnlyForCommittedDrop` | 안전 | 알림은 commit한 트랜잭션의 것이고, 그 트랜잭션이 commit한 버전이 가진 chain을 이름에 넣지 않는다 (statement, savepoint, 트랜잭션, commit 전 crash rollback의 알림 없음) |
| `GarbageReclaimed` | liveness (WF: postpone 실행, run 표시, `LOG_COMMIT`, vacuum 소비, block 완료, REMOVE, snapshot 종료) | 아무것도 가리키지 않는 살아 있는 chain은 결국 회수된다 |

**실행.** `python3 check_reuse.py --out <새 디렉터리> --jobs 5 --workers 10`. TLC 2.19 (`tla2tools-1.7.4.jar`), 2026-11-13. 결과 전체는 [`results-reuse/summary.md`](../oos/reclaim-model/results-reuse/summary.md) 와 `results.json` 에 있다. 모델 sha256 `acf940a2…`. **44개 결과가 모두 기대와 일치했다.**

- 안전 경계: T1·T2, reader 1, slot 4, 트랜잭션당 statement 2, stamp 6.
- liveness 경계: slot 3, statement 1, stamp 5. liveness 검사는 VIEW를 쓸 수 없어 trace 변수가 상태에 남기 때문이다.

| 설정 | NeededChainsLive | NoWrongDelete | NotifyOnly… | GarbageReclaimed | 무엇을 되돌렸나 |
|---|---|---|---|---|---|
| **design** | PASS (9,649,400) | PASS | PASS | PASS (189,483) | 없음 |
| `publish_before_commit` | FAIL | PASS | FAIL | PASS | A': commit hook이 commit 레코드 전에 알림 (결정 A) |
| `no_horizon` | FAIL | PASS | PASS | PASS | vacuum이 snapshot을 무시 |
| `no_cancel` | FAIL | PASS | FAIL | 검사 안 함 | statement rollback이 postpone을 남김 |
| `undo_image_drop` | FAIL | PASS | FAIL | PASS | 옛 레코드의 모든 chain을 버림 (forward-walk) |
| `no_identity` | FAIL | FAIL | PASS | PASS | 회수기가 stamp를 비교하지 않음 |
| `no_rerun` | PASS | PASS | PASS | FAIL | 재시작이 남은 postpone을 다시 돌리지 않음 |
| `restamp` | FAIL | PASS | PASS | FAIL | 재사용 stub에 새 stamp (head chunk도 갱신) |
| `snapshot_source` | FAIL | PASS | FAIL | PASS | 잠긴 최신 버전 대신 그 이전 commit 버전에서 stub 복사 |
| `undo_frees_reused` | FAIL | PASS | PASS | PASS | UPDATE undo가 새 레코드의 모든 chain(재사용 포함)을 해제 |

통제마다 자기가 지키는 속성에서만 실패하고, 나머지는 통과한다 (state 수는 summary 참조).

**반례에서 읽는 것.**

- `publish_before_commit`: c1 할당 → commit hook이 알림을 flush → crash로 T1이 loser가 되어 A가 복원된다 → vacuum이 알림을 소비해 A를 지운다. A'가 필요한 이유가 공유 chain에서도 그대로다.
- `no_horizon`: T1이 c1을 할당하고 c2를 재사용한다. 그 commit 전에 R1이 snapshot을 잡는다. vacuum이 R1을 기다리지 않고 옛 c1을 지운다.
- `no_cancel`: c1 할당을 statement rollback한 뒤 commit하면, 남은 postpone이 복원된 chain을 지운다.
- `undo_image_drop`: c1과 c2를 모두 재사용하는 UPDATE만으로 forward-walk는 살아 있는 두 chain을 지운다. 재사용이 forward-walk를 제거하게 만든 이유다.
- `no_identity`: vacuum이 알림을 처리한 뒤 block 완료 전에 crash가 난다. 그 사이 T2가 해제된 slot에 새 chain을 넣고, 재처리가 그 chain을 지운다. stamp 검사가 재처리와 중복 알림을 안전하게 만든다.
- `no_rerun`: `LOG_COMMIT_WITH_POSTPONE` 뒤 crash에서 postpone이 사라져 버린 chain이 영원히 남는다.
- `snapshot_source`: stmt1이 c1을 할당해 A를 버리고, stmt2가 이전 버전에서 c1 stub(A)을 복사해 A를 되살린다. commit 뒤 알림이 A를 지운다. §2의 "잠긴 최신 버전" 조건과 §4 assert의 근거다.
- `undo_frees_reused`: 재사용 UPDATE를 rollback하면서 재사용 chain을 해제하면 복원된 버전이 끊어진다. undo는 실제 `oos_insert` 만 되돌려야 한다 (현재 물리 undo가 그렇다).
- `restamp`: 재사용 stub에 새 stamp를 주면 옛 버전 stub의 identity가 깨진다. rollback이 head stamp를 되돌리지 않으면 chain이 샌다. 이슈의 "generation도 그대로 복사" 규칙의 근거다.

**도달 확인 (witness, 설계 설정에서 FAIL = 도달).**

- `WitnessSharedChainReclaimed`: 재사용으로 유지된 chain이 이후 할당 UPDATE의 알림으로 회수된다.
- `WitnessSnapshotHoldsReclaim`: snapshot이 commit된 drop의 회수를 붙잡는다.
- `WitnessDuplicateNotify`: 재시작 재실행이 같은 알림을 두 번 남긴다.
- `WitnessCrashInPostponeThenReclaim`: postpone 중 crash 뒤에도 회수가 끝난다.
- `WitnessPartialRollbackThenCommit`: drop을 rollback하고 다른 drop을 commit한다.

**모델의 한계.**

- 작은 경계의 설계 모델이다. 코드 일치를 보이지 않는다.
- chain은 head 하나로 추상화한다. chunk 순서와 회수기 재실행은 기존 모델이 검사한다.
- MVCC horizon은 "active snapshot이 T의 commit을 본다"로 추상화한다. MVCCID 수치 순서는 §4의 논증에 맡긴다.
- 복제, partition 이동, representation 변경, in-place update style은 모델 밖이다. §3과 §7이 다룬다.
- liveness는 작은 경계에서만 검사했다. `no_cancel` 은 안전 경계 상태가 25 GB를 넘어 작은 경계로 안전 속성만 검사했다.

## 10. 구현 계획 (승인 후)

CHECKPOINT 보고에서 정한다. 이 문서의 결론을 그대로 따르는 초안:

1. **준비 (inert)**: `heap_oos_collect_dropped_refs` 의 assert 2개와 주석 정정. unit test.
2. **복제 프로토콜 (inert)**: `RVREPL_OOS_REUSE`, `oos_published_ref` reused 종류, applier 처리, `xlocator_repl_force` 의 attr id fixup과 길이 검사, applylogdb의 SET 생략. producer가 아직 없으므로 동작 변화가 없다. 테스트 harness로 marker를 주입해 검사한다.
3. **쓰기 경로 재사용 (활성화)**: plan `reused`, §2 predicate, `set_uninitialized` skip, layout, writer, finalize, marker 발행, partition 이동 materialize, `oos_log_update_drop_intent` 의 sysop assert.
4. **테스트**: §11.
5. **재측정**: CBRD-28077 도구(`oosbench2.py`, S5와 S8s).

## 11. 테스트 계획

| 영역 | 시나리오 | 기대 |
|---|---|---|
| 재사용 | inline 컬럼만 SET | head OID와 stamp 동일 (debug oos.log), 값 정상, OOS 페이지 수 불변, `oos_read`/`oos_insert` 0 |
| 혼합 | c1 할당, c2 미할당 | c1만 새 chain, 알림은 옛 c1만 |
| 회수 | 할당 UPDATE commit → vacuum | 옛 chain 회수, 재사용 chain 유지 |
| snapshot | T1 재사용 commit 뒤 S가 v1을 읽는 중 T2가 할당 commit | S 종료 전 회수 없음, 종료 뒤 회수 |
| rollback | statement, savepoint(postpone 이전/이후), transaction | 원래 chain 보존, 알림 없음 |
| crash | 첫 postpone 이전, 알림 append 뒤 END 이전, 마지막 END 뒤 `LOG_COMMIT` 이전, UPDATE 미commit | 알림 손실 없음, 중복 알림 회수는 skip, 미commit은 원래 chain |
| 금지 경로 | partition 이동, representation 변경, CS flush, `do_increment` | 재사용 없음 또는 materialize, 값 정상 |
| HA | 재사용 UPDATE, 혼합 UPDATE, replica 행 불일치 | 값 동등, replica OID는 replica 자신의 것, 불일치는 명시적 오류, applylogdb sql.log 정상 |
| 회귀 | 비 OOS UPDATE | 로그 볼륨 증가 없음 |
| 성능 | S5, S8s (`UPDATE t SET k = k + 1`) | develop 대비 server instruction 비율과 OOS 파일 크기 (30,000행에서 30,001 → 60,001 페이지가 되던 증가가 없어야 함) |
