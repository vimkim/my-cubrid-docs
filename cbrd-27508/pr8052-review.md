# CUBRID/cubrid PR #8052 (`CBRD-27508`) 코드 리뷰 보고서 (OOS 병렬처리 집중 검증)

- **검토 일자 (`Asia/Seoul`)**: `2026-11-24`
- **PR**: [CUBRID/cubrid#8052](https://github.com/CUBRID/cubrid/pull/8052) (`[CBRD-27508] Implement writeset dependency generation for replication`)
- **관련 이슈**: [CBRD-27508](https://jira.cubrid.org/browse/CBRD-27508) · [CBRD-27800](https://jira.cubrid.org/browse/CBRD-27800) · [CBRD-28315](https://jira.cubrid.org/browse/CBRD-28315) (OOS 규격)
- **작성자 / 리뷰 기한**: `youngjun9072` / `2026-11-26 (목)`
- **비교 범위 (`merge-base..head`)**: `79eab331e54349812e98cace6d0aeaeebf123d95` .. `c92079804727715a2a59d3446434d73e94ab23d9` (변경 116개 파일, `+21,302 / -1,287`)
- **이후 PR 이동 참고 (`c84d009b22`)**: 본 보고서의 스냅샷(`c920798047`) 이후 PR #8052 `head` 가 1커밋 이동해 `c84d009b220a9f82a88c801073059d845ddb4f01` (`[CBRD-27508] Leave the row topop of a deadlock victim to exit_on_error`) 이 추가되었습니다. 해당 커밋은 `src/transaction/locator_sr.c` `+2/-2` 만 수정해 기존 `H2SU` 의 데드락 `row_topop` 코멘트만 반영했으며, 아래 `F-01`, `F-02` 및 `U-01`~`U-10` 은 모두 그대로 남아 있으므로 후속 커밋에 대한 델타 재검증이 필요합니다.
- **적용 규격**: OOS 규격 ([CBRD-28315](https://jira.cubrid.org/browse/CBRD-28315), `OOS-ADR-0008` accepted, `last_updated: 2026-11-05`)

---

## 1. 요약 및 판정 (Verdict & Recommendation)

- **최종 판정**: `changes-required` (**수정 요청 / Request Changes 권고**)
- **후속 리뷰 필요 (`Follow-up review required`)**: **`yes` (머지 전 필수)**

### 핵심 결론
1. **확정 결함 2건 (`F-01` P0, `F-02` P2)** 을 `libcubridcs.so` 프로브 및 `cub_server` (`ha_mode=on`) 실행으로 재현·확정했습니다.
   - 특히 **`F-01` (P0)** 은 PR 본문이 "develop 의 CBRD-27800 과 같은 형태"라고 설명한 것과 달리, PR #8052 가 사전 `la_flush_repl_items(false)` 를 제거하고 최대 500개 트랜잭션을 중간 flush 없이 배치 처리하며 `ws_discard_last_repl_objs()` (`a730f692be`) 와 `_db_ha_applied_tx_marker` 를 같은 `recdes_pool` 에 넣으면서 **트랜잭션 경계를 넘는 무음 데이터 손상·해제 후 덮어쓰기 및 신규 트리거** 를 직접 만들어 내는 것을 확인했습니다.
2. **소스 경로가 완전히 증명된 머지 전 수정 필수 미검증 결함 4건 (`U-01` P0/P1, `U-02` P1, `U-03` P1, `U-04` P1)** 과 중·저위험 6건 (`U-05`~`U-10`) 이 존재합니다.
   - `U-01` (`db_find_class == NULL` 오류 삼킴으로 `la_oos_unpaired_count` 가 오염되어 이전 정상 트랜잭션 행 삭제 / OOS 오매칭 / `ER_LK_UNILATERALLY_ABORTED` 가드 우회), `U-02` (다중 OOS 컬럼 부분 실패 시 무한 재시작 루프), `U-03` (`la_apply_log_file` 종료 경로가 치명적 오류를 `NO_ERROR` 로 덮어쓰고 재연결 루프를 무력화) 은 머지 전 반드시 수정이 필요합니다.
3. **기존 리뷰어 코멘트 중복 배제 현황**:
   - `H2SU`: [locator_sr.c:9337](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/locator_sr.c#L9337) 데드락 희생자 `row_topop_active = false` 누락(이중 topop abort, `c84d009b22` 에서 수정), [serial.c:1644](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/query/serial.c#L1644) `wset_add_write_key` 실패 시 redo 전용 `_db_serial` sysop abort 문제.
   - `hgryoo`: `w=1` 백로그 처리량 저하(배치 500 vs 큐 1024), `MULTI_CONN_TO_A_SERVER` 의 `libcubridcs` TLS 비용, 마스터 CPU +4%, 빈 `SYSOP_END` 의 ring 점유, [upgrade/v1_to_v2.sql](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/upgrade/v1_to_v2.sql) 점검.
   - `hornetmj`: `log_dump_record` 의 `LOG_DUMMY_WSET_LABEL` 누락(기존 FK-REF CASCADE 레이스는 11/24 철회).

---

## 2. 확정 결함 (Confirmed Findings — 실행 재현 및 코디네이터 재검증 완료)

### `F-01` [P0 · OOS + 병렬 Applier] Worker `recdes_pool` 순환 링 wraparound 로 인한 미전송 `RECDES` 메모리 해제 및 무음 덮어쓰기 (신규 트리거 포함)

- **핀 위치 (`c920798047`)**:
  - [log_applier_worker_context.cpp#L213-L240](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/applier/log_applier_worker_context.cpp#L213-L240) (`la_assign_recdes_from_pool`)
  - [log_applier.c#L110](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L110), [L1357](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L1357), [L3981](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L3981), [L5624-L5633](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L5624-L5633), [L7675-L7693](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L7675-L7693), [L8102](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8102), [L8342](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8342), [L8558](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8558), [L8634](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8634)
  - [work_space.c#L5550-L5591](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/object/work_space.c#L5550-L5591), [L5650](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/object/work_space.c#L5650)
- **원인 및 변경 귀속 (`79eab331e5` 대비)**:
  - `ws_add_to_repl_obj_list()` 는 `repl_obj->recdes = recdes` 로 포인터만 저장하며 데이터를 복사하지 않습니다.
  - `develop` (`79eab331e5`) 에서는 `la_apply_oos_insert_log()`, `la_apply_insert_log()`, `la_apply_update_log()` 가 풀 할당 전에 `la_flush_repl_items(false)` 를 먼저 호출했고 트랜잭션 커밋마다 flush 했습니다.
  - PR #8052 는 (1) 위 3곳의 사전 flush 를 제거하고 힙 행 적용 끝(`la_apply_insert_log:8634`, `la_apply_update_log:8179`) 에서만 flush 하며, (2) 최대 `LA_WORKER_BATCH_MAX_TASKS` (500) 개 트랜잭션을 중간 flush 없이 한 worker 버퍼에 누적하고, (3) `a730f692be` 에서 추가한 `ws_discard_last_repl_objs()` 가 `m_Repl_objs.num_items` 만 줄이고 `pool->next_idx` 를 되감지 않으며, (4) `la_add_applied_tx_marker()` (`log_applier.c:3981`) 역시 동일 풀을 사용합니다.
- **도달 가능한 트리거**:
  1. **Trigger A (정상 OOS OLTP 배치, 오류 없음)**: 버퍼에 199개 객체(예: slot 0 이 multi-chunk `LC_FLUSH_INSERT_OOS` 로 `area_size > db_page_size`) 가 쌓인 상태에서 다음 트랜잭션의 `RVREPL_OOS_INSERT` 가 slot 199 를 점유(`la_oos_pending_flush = true` 로 flush 보류, `num_items = 200`, `next_idx = 0`) 한 뒤 짝지어진 `RVREPL_DATA_INSERT` / `UPDATE` 가 flush 전에 `la_assign_recdes_from_pool()` 을 호출하면 **아직 flush 되지 않은 slot 0 을 재할당** 하여 기존 `recdes->data` 를 `free_and_init()` 하고 새 힙 레코드로 덮어씁니다. (`locator_oos_insert_force` 는 `length > 32` 만 검사하므로 다른 트랜잭션의 힙 레코드를 첫 행의 OOS 값으로 무음 저장하거나 반대로 non-OOS 행에 OOS 힙 레코드를 덮어씁니다.)
  2. **Trigger B (넓은 행)**: OOS 컬럼이 200개 이상인 단일 행은 `num_items == 0` 에서도 한 행 내부에서 풀을 한 바퀴 감아 덮어씁니다.
  3. **Trigger C (PR #8052 신규 트리거 — `ws_discard_last_repl_objs` / 재시도 drift)**: 195개 버퍼 후 5개 OOS 객체가 적재되었다가 마스터 롤백 업데이트(`LSA_ISNULL(&target_lsa)`) 등으로 `ws_discard_last_repl_objs(5)` 가 호출되면 `num_items` 는 `195 (< 200)` 로 유지되지만 `pool->next_idx` 는 `0` 으로 남아, 다음 일반 행이나 커밋 시점의 `_db_ha_applied_tx_marker` 가 slot 0 을 덮어씁니다.
- **실행 재현 증거 (`debug_gcc`, `libcubridcs.so` 직접 링크 프로브, Evidence Level 4)**:
  - `la_worker_context_init`, `la_assign_recdes_from_pool`, `la_realloc_recdes_data`, `ws_repl::ws_add_to_repl_obj_list`, `ws_repl::ws_discard_last_repl_objs` 실제 호출, 종료 코드 `0`.
  - 실제 출력:
    ```text
    [Before OOS row] num_items=199 next_idx=199 slot0->length=32768 slot0->data[0]='A'
    [Trigger A: OOS deferred flush wrap]
      r_heap == head->recdes (aliased slot 0!): YES (CORRUPTED)
      orig_slot0_ptr=0x1611a20 -> now head->recdes->data=0x7ff4c32df010 (FREED & REPOINTED=YES)
      head->recdes->length=64 (was 32768), head->recdes->data[0]='Z' (was 'A')
    [Trigger C: ws_discard_last_repl_objs drift]
      After discard(5): num_items=195 (<200!), next_idx=0
      marker_or_row == head2->recdes (aliased slot 0!): YES (CORRUPTED)
      head2->recdes->length=32 (was 128), head2->recdes->data[0]='M' (was 'F')
    ```
- **수정 방향**: 맹목적인 `next_idx = (next_idx + 1) % 200` 링 풀 대신 미전송 `WS_REPL_OBJ` 가 참조 중인 `RECDES` 가 재사용되지 않도록 객체별 소유 버퍼 할당 또는 `ws_repl` / 풀 연동 반납 구조로 교체하고, OOS 그룹 시작 전·마커 버퍼링 시 풀 용량 및 넓은 행(`>= 200` 컬럼) 도 함께 처리해야 합니다.

### `F-02` [P2 · Master Writeset FK] `wset_add_ref_key` 의 `tp_value_cast(..., false)` 선행 호출로 넓은 자식 FK 의 오류 코드 변질 (`ER_FK_INVALID` → `ER_TP_CANT_COERCE_OVERFLOW`)

- **핀 위치 (`c920798047`)**:
  - [writeset.cpp#L254-L276](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/writeset/writeset.cpp#L254-L276) (`wset_cast_value_to_domain`)
  - [writeset.cpp#L421-L476](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/writeset/writeset.cpp#L421-L476) (`wset_add_ref_key`)
  - [locator_sr.c#L10229](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/locator_sr.c#L10229) (`locator_wset_collect_fk_ref`)
- **원인**: `smt_check_type_collation_match_4_fk` (`schema_template.c:1602-1627`) 는 부모 PK 와 자식 FK 의 정밀도(precision/scale) 일치를 요구하지 않아 `p(k VARCHAR(10))` 를 `c(k VARCHAR(20))` 가 참조할 수 있습니다. 그러나 `locator_collect_wset_key` 가 `locator_check_foreign_key` 보다 먼저 실행되면서 `tp_value_cast(source, destination, domain, false)` (`TP_EXPLICIT_COERCION`) 를 호출하고, 기본값 `allow_truncated_string=no` 에서 `DOMAIN_TRUNCATED` 가 `DOMAIN_OVERFLOW` (`ER_TP_CANT_COERCE_OVERFLOW`, `-1199`) 로 변환되어 DML 을 즉시 실패시킵니다.
- **실 DB 재현 증거 (`debug_gcc`, `cub_server`, `ha_mode=on`, Evidence Level 5)**:
  - 스키마: `p_vc(k VARCHAR(10) PRIMARY KEY)`, `c_vc(id INT PRIMARY KEY, k VARCHAR(20), FOREIGN KEY (k) REFERENCES p_vc(k))`.
  - `INSERT INTO c_vc VALUES (2, '123456789012345');` 실행 결과:
    - 기대: `ER_FK_INVALID` (`The constraint of the foreign key 'fk_c_vc_k' is invalid...`)
    - 실제: `ERROR: Cannot coerce value of domain "character varying" to domain "character varying" without overflow.` (`exit=1`, `ER_TP_CANT_COERCE_OVERFLOW`)
  - (참고: `CHAR(20)->CHAR(10)` `'abc'` 정상 삽입은 `exit=0` 으로 통과했고, 후행 공백 포함 `VARCHAR(20)` 은 `locator_check_foreign_key` 단에서 실패해 `ER_FK_INVALID` 가 나왔으므로 정상 DML 차단 부분은 부분 기각함. 다만 `dont_check_fk` 또는 기존 초과 자식 행 `DELETE` 경로에서도 `DOMAIN_OVERFLOW` 차단 가능성은 남습니다.)
- **수정 방향**: `wset_cast_value_to_domain` 에서 `DOMAIN_OVERFLOW` 발생 시 DML 을 실패시키지 말고(부모 PK 범위를 초과한 키는 부모 행과 일치할 수 없음) 해당 FK writeset 수집만 건너뛰어 `locator_check_foreign_key` 가 본래 의미 오류를 내도록 처리합니다.

---

## 3. 미검증 리스크 (Unverified Risks — 소스 경로 증명 완료, 실행 재현 대기)

아래 `U-01` ~ `U-04` 는 소스 제어 흐름상 결함이 명확하며 OOS·병렬 적용 안정성에 직접 연결되므로 **머지 전 수정(또는 결정적 반증)이 필수** 입니다.

| ID | 심각도 | 분류 | 핀 위치 (`c920798047`) | 핵심 결함 메커니즘 및 영향 | 가장 싼 검증 / 수정 방향 |
|---|---|---|---|---|---|
| **`U-01`** | **P0/P1** *(머지 필수)* | OOS + 병렬 Applier | [log_applier.c#L8135-L8145](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8135-L8145), [L8330-L8340](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8330-L8340), [L8546-L8556](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8546-L8556), [work_space.c#L5556](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/object/work_space.c#L5556) | `la_apply_oos_insert_log`, `la_apply_insert_log`, `la_apply_update_log` 모두 `db_find_class(...) == NULL` 일 때 `er_errid() == NO_ERROR` 인 경우에만 `error = ER_FAILED` 를 대입해 정상 오류(`ER_LK_UNILATERALLY_ABORTED`, 락 타임아웃, `ER_LC_UNKNOWN_CLASSNAME`) 시 `error == NO_ERROR` 로 `else` 분기를 탑니다 (`develop` 기존 누락). PR #8052 의 `la_oos_unpaired_count++` / `ws_discard_last_repl_objs` / 500-task 배치 / `ER_LK_UNILATERALLY_ABORTED` 가드와 결합하면: (1) OOS 쪽 누락 시 객체는 안 넣고 `la_oos_unpaired_count++` 만 올려 이후 `ws_discard_last_repl_objs` 가 **이전 정상 트랜잭션 행을 무음 삭제**(마커는 커밋)하거나 `work_space.c:5556` `assert` 크래시, (2) 힙 행 쪽 누락 시 `la_oos_unpaired_count = 0` 으로 초기화해 **고아 OOS 가 다음 트랜잭션 행과 오매칭**, (3) `ER_LK_UNILATERALLY_ABORTED` 가드(`9213`) 우회. | 세 함수 모두 `error = er_errid() != NO_ERROR ? er_errid() : ER_FAILED;` 대입 (`la_apply_oos_reuse_log:8494` 와 동일) |
| **`U-02`** | **P1** *(머지 필수)* | OOS 다중 컬럼 부분 실패 | [log_applier.c#L8438-L8442](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8438-L8442), [L8501-L8505](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8501-L8505), [L9243-L9271](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L9243-L9271), [locator_sr.c#L9240-L9246](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/locator_sr.c#L9240-L9246) | `[OOS_1, OOS_2, HEAP_ROW]` 에서 `OOS_1` 성공 후 `OOS_2` 가 비치명/무시 오류(`ER_HA_GENERIC_ERROR` 등)로 건너뛰어지면 `9266` 조건(`!la_is_oos_item(item)`) 이 거짓이라 `OOS_1` 이 버려지지 않습니다. 이어 `HEAP_ROW` 가 flush 되면 서버 `locator_fixup_oos_oids_in_recdes` (`locator_sr.c:17465`) 가 OOS 개수 불일치로 전체 copyarea 를 abort 해 `applylogdb` 가 **무한 재시작 루프** 에 빠지며, SQL 로그의 `la_oos_row_reused` 인덱스도 밀립니다. | 2-OOS-컬럼 행에서 두 번째 OOS 오류 주입 시 재현; OOS 항목 실패 시 행 단위 poison 플래그로 선행 OOS 폐기 및 힙 행 동반 skip 필요 |
| **`U-03`** | **P1** *(머지 필수)* | 병렬 Applier 종료 / 재연결 | [log_applier.c#L804-L807](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L804-L807), [L1409-L1412](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L1409-L1412), [L12688-L12750](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L12688-L12750), [log_applier_worker.cpp#L391-L396](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/applier/log_applier_worker.cpp#L391-L396), [util_cs.c#L3590-L3604](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/executables/util_cs.c#L3590-L3604) | (1) `la_apply_log_file` 중간 루프를 `max_mem_size` 초과 / `TDE` / 페이지 손상 / `check_reinit_copylog` / `la_change_state` 오류로 `break` 한 뒤 `12688` 에서 `error = la_coordinator_collect_and_retire();` 가 `error` 를 **`NO_ERROR` (`EXIT_SUCCESS`)** 로 덮어씁니다. (2) Worker B 가 `dispatch_seq=50` 에서 치명 실패하고 Worker A(`seq=40`) 가 진행 중이면 `la_coordinator_retire_results()` 는 head(`40`) 만 보고 `NO_ERROR` 를 반환해 `applylogdb` 가 `EXIT_SUCCESS` 로 종료됩니다. (3) Worker 실패 시 `la_request_shutdown()` 이 세운 `la_applier_need_shutdown = true` 가 `la_shutdown()` 에서 초기화되지 않아 `util_cs.c:3590` 재연결/재시도(`ER_NET_CANT_CONNECT_SERVER`, `ER_LC_PARTIALLY_FAILED_TO_FLUSH`) 가 영구 무력화됩니다. | `max_mem_size` 초과 또는 worker 비순차 실패 시 exit code `0` 확인; break 전 코디네이터 오류 보존 및 worker/coordinator 오류 구분 전파 필요 |
| **`U-04`** | **P1** *(수정 권장)* | OOS 다중 Copyarea Flush | [locator_cl.c#L7088-L7093](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/locator_cl.c#L7088-L7093), [L7190-L7206](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/locator_cl.c#L7190-L7206) | `locator_repl_mflush` 내부 루프에 `continued_on_error` 래치가 없어, 초기 16KB copyarea 를 넘는 OOS 500-task 배치에서 첫 chunk 가 `ER_LC_PARTIALLY_FAILED_TO_FLUSH`(예: 병렬 적용 중 락 타임아웃) 를 반환해도 두 번째 chunk 가 `NO_ERROR` 이면 오류를 덮어씁니다(`develop` 기원이나 OOS 대용량 + 배치 + 마커 커밋에서 `la_restart_on_bulk_flush_error` 를 건너뛰고 마커를 커밋해 **영구 행 유실** 유발). | 32KB+ OOS 배치의 첫 chunk 실패 + 후속 chunk 성공 테스트; `locator_repl_mflush` 내부에 `continued_on_error` 래치 추가 |
| **`U-05`** | **P2** | 오류 스택 누락 크래시 | [log_applier.c#L7524-L7537](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L7524-L7537), [L8111-L8133](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8111-L8133), [L8386-L8400](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8386-L8400), [L8584-L8605](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L8584-L8605), [L4114](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L4114) | `er_set()` 없이 `ER_FAILED` 를 반환하면 `la_apply_repl_log:9189` (`assert(er_errid() != NO_ERROR)`) 및 `la_ignore_on_error:4114` (`assert_release(errid != NO_ERROR)`) 가 **릴리스 빌드에서도 크래시** 하거나 직전 잔류 `errid` 로 오분류합니다. | `er_set` 보장 또는 `er_errid() == NO_ERROR` fallback |
| **`U-06`** | **P2** | 병렬 SQL 로그 레이스 | [log_applier_sql_log.c#L569](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier_sql_log.c#L569), [error_manager.c#L3402](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/base/error_manager.c#L3402) | `sl_write_sql_locked` 가 `sl_write_mutex` 안에서 비재진입 `localtime()` 을 호출해, 다른 워커/코디네이터의 `er_set` (`localtime()`) 과 전역 `struct tm` 데이터 레이스를 일으킵니다. (부수적으로 `sl_open_next_file:656` 의 `fclose(NULL)` 위험 및 배치 롤백 시 `sql.log` 중복 기록 증가.) | `localtime_r(&curr_time, &tm_buf)` 로 교체 |
| **`U-07`** | **P2** | 재시작 상태 잔존 | [log_applier_wset_label.cpp#L32-L34](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/applier/log_applier_wset_label.cpp#L32-L34) | `la_Wset_label_stored` 등이 `la_init()` / `la_shutdown()` 에서 초기화되지 않아 `util_cs.c:3590` 동일 프로세스 `goto retry` 재시작 시 직전 실행의 미소비 라벨이 남습니다. | `la_init()`/`la_shutdown()` 에서 `la_wset_label_discard()` 호출 |
| **`U-08`** | **P2** | 파티션 FK / 복합 OOS 성능 | [locator_sr.c#L10148-L10237](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/locator_sr.c#L10148-L10237) | 파티션 미일치 시 `partition_prune_unique_btid` 가 `NULL_BTID` 를 돌려주는데 검사 없이 `NULL_VFID` 로 키를 추가하며, 이미 추출된 `key`/`key_domain` 을 두고 `heap_attrvalue_get_key` 를 재호출해 복합 OOS FK 에서 불필요한 `oos_read` 가 추가 발생합니다. | `BTID_IS_NULL` 조기 반환 및 기존 `key` 재사용 |
| **`U-09`** | **P2** *(기존 OOS+HA 결함 노출)* | `_db_serial` OOS 및 stale 방어 | [serial.c#L1583-L1622](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/query/serial.c#L1583-L1622), [locator_sr.c#L9169-L9359](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/locator_sr.c#L9169-L9359) | 4KiB 페이지 DB 에서 `_db_serial.comment` (`VARCHAR(1024)`, 자동 타겟 988B) 가 OOS 화되면 `serial_update_serial_object` 가 `RVREPL_OOS_INSERT` 를 누락(`develop` 기원)해 슬레이브 `locator_fixup_oos_oids_in_recdes` 가 실패합니다. 또한 `xlocator_repl_force` 에서 `serial_repl_image_is_stale` 검사 전에 `locator_fixup_oos_oids_in_recdes` 를 호출하고, stale skip 시 `oneobj_lsa` 를 abort 하지 않아 OOS 청크가 고아로 남으며, `packed_prior_value_len < 0` / 비-OOS 행에 대한 `oos_oids` 방어가 비어 있습니다. | `serial_repl_image_is_stale` 선행 검사 + abort 처리, 비-OOS 행에서 `!oos_oids.empty()` 거부 |
| **`U-10`** | **P3** | 경미 / 경합 | [log_applier.c#L9534-L9613](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L9534-L9613), [locator_sr.c#L7165](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/locator_sr.c#L7165), [log_manager.c#L5077-L5094](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_manager.c#L5077-L5094), [log_applier.c#L2235-L2386](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/log_applier.c#L2235-L2386), [log_applier_worker_context.cpp#L184-L199](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/applier/log_applier_worker_context.cpp#L184-L199) | (a) 독립 sysop 내 `LOG_SYSOP_END_LOGICAL_RUN_POSTPONE` (`RVOOS_UPDATE_DROP_POSTPONE` 등) 가 라벨 없는 fragment 로 조기 분리되어 불필요한 `commit_order` 직렬화 유발(순서 안전성은 gate 로 유지됨), (b) `locator_oos_insert_force` 가 매번 힙 헤더 `PGBUF_LATCH_WRITE` 획득(`develop` 기원, 병렬 OOS 워커 간 직렬화), (c) `log_append_wset_label_with_lock` 의 OOM 시 `/* FIXME */ return;`, (d) `la_get_page` OOM 무한 루프, `la_realloc_recdes_data` OOM 시 `area_size` 불일치, role-change drain 중 로그 반복 출력. | 후속 정리 및 회귀 보강 |

---

## 4. 기각된 후보 (Dropped / Disproven Candidates)

1. **`R2-1` (공유 BTID `FOREIGN KEY` + `PRIMARY KEY`/`UNIQUE` writeset 키 누락)**: **기각**.
   - [class_object.c#L8150-L8229](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/object/class_object.c#L8150-L8229) (`classobj_check_index_compatibility`) 확인 결과 `PK`/`UK` 와 `FK` 는 CUBRID 에서 인덱스 공유가 금지되어 항상 별도 BTID 를 할당받습니다. `cub_server` (`ha_mode=on`, `ha_writeset_trace_level=3`) 에서 `INT` 및 5000B OOS `VARCHAR` 로 `CREATE TABLE` 및 `ALTER TABLE ADD FOREIGN KEY` 모두 실행해 `[WSET] COLLECT kind=REF` 와 `kind=WRITE` 가 모두 수집됨을 실측 확인했습니다.
2. **`R2-3` (`serial_update_serial_object` `lock_mode == X_LOCK` 시 writeset 키 누락)**: **기각**.
   - 실 DB 테스트에서 DBA 의 `SELECT ... FROM _db_serial FOR UPDATE` 는 `ERROR: UPDATE is not authorized on _db_serial.` 로 차단되며, `_db_serial` 을 변경하는 `CREATE/ALTER SERIAL` 은 모두 statement 복제(`wset_fallback=true`) 를 사용함을 확인했습니다.
3. **`R2-2` 중 `CHAR(20)->CHAR(10)` 정상 DML 차단 가설**: **부분 기각**.
   - 실 DB 테스트에서 `INSERT INTO c_ch VALUES (1, 'abc')` (`CHAR(20)` → `CHAR(10)`) 는 `exit=0` 으로 정상 커밋되었습니다. 오류 코드 변질(`F-02`) 만 확정으로 유지합니다.

---

## 5. 안전성 확인 완료 항목 (Cleared OOS & Parallel Replication Safety Facts)

- **마스터 OOS 키 추출 및 `UPDATE` reuse / 롤백 처리 (`OOS-CONTEXT.md` / `CBRD-28315` §3~4)**:
  - `heap_attrvalue_get_key()` 는 OOS-backed 단일/복합(`MIDXKEY`)/prefix 인덱스 키를 24B `OOS inline stub` 이 아닌 실제 값으로 해석하며, 실 DB 테스트에서 5000B OOS `VARCHAR` PK/FK (`INSERT`/`UPDATE`/`DELETE`) 에 대해 정확한 `[WSET] COLLECT` / `PROBE` / `PUBLISH` 를 확인했습니다.
  - `repl_log_abort_after_lsa()` ([replication.c#L1059-L1079](https://github.com/CUBRID/cubrid/blob/c92079804727715a2a59d3446434d73e94ab23d9/src/transaction/replication.c#L1059-L1079)) 및 `repl_oos_items_follow_row()` / `repl_assert_oos_items_follow_row()` 가 OOS 항목(`RVREPL_OOS_INSERT`, `RVREPL_DUMMY_OOS_RECORD`, `RVREPL_OOS_REUSE`) 과 행 항목의 동반 write/drop 불변식을 유지합니다.
  - 내부 OOS sysop (`oos_create_file`, `oos_file_alloc_new`, `RVOOS_NOTIFY_VACUUM`, `RVOOS_RECLAIM_POSTPONE`) 은 `fl_mark_repl_recidx != -1` 또는 `LOG_REPL_COMMIT_NEED_FLUSH` 조건에 의해 `repl_prepare_sysop` / `repl_finish_sysop` 에서 독립 복제 단위로 오인되지 않습니다.
- **슬레이브 OOS `sql.log` 캐시 및 스레드 격리 (`a730f692be`)**:
  - `la_oos_cache_*`, `la_oos_row_reused`, `la_oos_pending_flush`, `la_oos_unpaired_count`, `__gv_loc_repl` (`MULTI_CONN_TO_A_SERVER` 시 `THREAD_LOCAL`, 미활성 시 `run_each_task_alone = true`) 모두 worker 스레드별로 격리되며 task 종료 시 `la_clear_oos_cache()`, 스레드 종료 시 `la_release_oos_thread_state()` 로 정리됩니다. `test_oos_sql_log_cache` 4/4 통과.
  - `la_need_filter_out()` 필터링 및 마스터 롤백 업데이트(`LSA_ISNULL(&target_lsa)`) 시 `la_discard_unpaired_oos_objects()` 가 선행 OOS 객체를 정상 회수합니다(`F-01` 의 `next_idx` drift 및 `U-01` 오류 삼킴 제외).
  - `sl_write_statement_sql` 다중 호출은 `wset_switch_to_commit_order` + `task.has_statement` 단독 실행으로 상호 배제되며, `dbt_create_object_internal` / `Au_user` 는 `CUB_THREAD_LOCAL` 로 안전합니다.
- **슬레이브 서버측 OOS 동시성·MVCC·Vacuum 생명주기**:
  - 동일 테이블 병렬 적용 시 `heap_oos_find_vfid_internal` 의 힙 헤더 `PGBUF_LATCH_WRITE` 직렬화, `oos_stats_find_page_in_bestspace` 의 `bestspace_mutex` + `OLD_PAGE_MAYBE_DEALLOCATED` 검증, `oos_alloc_page_with_reclaim` 의 `sweep_in_progress` 직렬화가 모두 데드락 없이 안전합니다.
  - 동일 키에 의존하는 `INSERT OOS` → `UPDATE (RVREPL_OOS_REUSE)` → `DELETE` task 들은 `la_gate_route()` 에 의해 동일 worker 의 단일 슬레이브 트랜잭션(동일 MVCCID) 으로 순서대로 실행되며, `RVOOS_NOTIFY_VACUUM` 은 `log_sysop_attach_to_outer` 를 통해 배치 커밋 후 MVCC 가시성이 안전해진 뒤에만 vacuum 이 소비합니다(`OOS-ADR-0008` 준수).
- **크래시·재시작·아카이브 보존·Failover·WAL 복구**:
  - `apply->start_lsa` (및 `fragment->start_lsa`) 가 트랜잭션 첫 레코드에 고정되고 `la_find_required_lsa()` 가 `repl_lists`, `la_Inflight`, `la_Pending` 전체 최솟값을 추적해 `RVOOS_INSERT` 청크가 포함된 복사 로그 아카이브가 조기 삭제되지 않습니다.
  - `la_change_state()` 의 `done_deferred` 및 `la_unlock_dbname()` 이 `la_coordinator_drain_complete()` 까지 대기해 failover 시 누락이 없으며, `LOG_DUMMY_WSET_LABEL` 은 `log_recovery.c` / `log_append.cpp` / `log_manager.c` / CDC(`flashback.c`) 에서 안전하게 건너뛰어집니다.

---

## 6. 커버리지 매트릭스, 검증 내역 및 후속 확인 조건

### 서브시스템별 커버리지 요약

| 대상 영역 | 주요 파일 | 핵심 불변식 | 결과 |
|---|---|---|---|
| Applier OOS 파이프라인 & `ws_repl` & SQL log | `log_applier.c`, `work_space.{c,h}`, `log_applier_sql_log.c`, `test_oos_sql_log_cache.cpp` | OOS-행 짝짓기, `ws_discard_last_repl_objs`, `la_oos_cache_*` 격리, `recdes_pool` 안전성 | **`F-01` 확정**, `U-01`, `U-02`, `U-05`, `U-06`; 단위테스트 4/4 통과 |
| Worker 풀 & 컨텍스트 생명주기 | `log_applier_worker.{cpp,hpp}`, `log_applier_worker_context.{cpp,hpp}` | 500-task 배치, `recdes_pool` 200-slot 수명, 종료 정리 | **`F-01` 확정**, `U-03`, `U-10` |
| 마스터 Writeset 키 수집 & 해시 정규화 | `locator_sr.c`, `writeset/*`, `language_support.{c,h}`, `serial.c` | OOS PK/UK/FK 해석 및 해싱, 파티션 FK, `_db_serial`, `history_map` | **`F-02` 확정**, `U-08`, `U-09`; `R2-1`/`R2-3` 기각 |
| 마스터 복제 항목 조립 & Sysop 경계 | `replication.{c,h}`, `log_manager.c`, `log_tran_table.c` | `repl_oos_items_follow_row`, `repl_log_abort_after_lsa`, OOS sysop 비분리 | 안전 확인 (`U-10` 경미 사항만 존재) |
| 슬레이브 서버 OOS force & Vacuum | `locator_sr.c` (`xlocator_repl_force`), `heap_file.c`, `heap_oos.cpp`, `oos_file.cpp` | 동시 `oos_create_file`/`oos_insert`, `RVREPL_OOS_REUSE`, `RVOOS_NOTIFY_VACUUM` | 안전 확인 (`U-09` stale 방어 공백, `U-10` 래치 경합) |
| 슬레이브 클라이언트 Flush | `locator_cl.c` (`locator_repl_mflush`) | 16KB copyarea 분할 flush 오류 전파 | `U-04` (미실행, 수정 권장) |
| Coordinator / Gate / Marker / Crash / Failover | `log_applier_{coordinator,gate,inflight,pending,...}.*`, `log_recovery.c`, `util_sa.c` | `required_lsa` 아카이브 보존, 재시작 마커, failover drain, `LOG_DUMMY_WSET_LABEL` | `U-03`, `U-07`, `U-10`; 복구/failover 안전 확인 |

### 실행된 검증 (모두 편집 없는 깨끗한 `c920798047` 기준)
1. CMake `debug_gcc` (`-DCMAKE_BUILD_TYPE=Debug -DUNIT_TEST_OOS=ON`) 빌드 및 설치 → **성공 (exit 0)**
2. `ctest --test-dir build_preset_debug_gcc -R "test_oos_sql_log_cache" --output-on-failure -V` → **4/4 통과 (exit 0)**
3. 정적 분석 (`cppcheck`, `clang-tidy bugprone-*`, PMD CPD, `lizard` — `79eab331e5..c920798047`) → **incomplete (exit 1)**: cppcheck 0건, CPD 0건, clang-tidy `bugprone-*` 15건(경미한 static 초기화/중복 분기/`atoi` 등; `U-06` 포함 반영), lizard 복잡도 25건(base `util_sa.c` `upgrade_checksums.h:24` 오류로 해당 파일 base 비교 불가).
4. `probe_c1` (`libcubridcs.so` 링크 프로브) → **`F-01` Trigger A, Trigger C 재현 성공 (exit 0)**
5. 실 `cub_server` (`ha_mode=on`, `ha_writeset_trace_level=3`) → **`F-02` 재현 성공**, `R2-1` / `R2-3` / `CHAR` 차단 기각, OOS 5000B `VARCHAR` `[WSET]` 수집 확인.

### 한계 및 후속 확인 조건
- **커버리지 한계**: `debug_gcc` 기본 프리셋에서 `UNIT_TEST_LOG_APPLIER` / `UNIT_TEST_WRITESET` 이 비활성화되어 해당 신규 단위 테스트는 실행하지 못했으며, 2노드 HA (master + slave `applylogdb` 멀티 워커) 종단 간 런타임 스트레스·장애 재시작 테스트는 수행하지 않았습니다.
- **완료 조건**: `F-01`, `U-01`, `U-02`, `U-03` 수정 확인, `U-04` 및 `F-02` 조치 확인, `c84d009b22` 이후 델타 점검, `-DUNIT_TEST_LOG_APPLIER=ON -DUNIT_TEST_WRITESET=ON` 단위 테스트 및 2노드 HA OOS 병렬 적용 통과 확인.
