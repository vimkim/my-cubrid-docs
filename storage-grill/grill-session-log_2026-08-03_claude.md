# Grill 세션 로그 — CUBRID src/storage × log/vacuum/sysop 접점 (2026-08-03)

> 목적: `/grill-with-docs` 스타일 세션의 진행 상태 기록. **재개 시 이 파일을 읽으면 전체 맥락 복원 가능.**
> 워크트리: `~/gh/cb/cubrid-analysis` (master f30f1c260)
> 선행 세션: `../log-manager/grill-session-log_2026-07-28_claude.md` (로그 매니저 append→flush)

## 세션 설계 (사용자 확정)

- **주제**: src/storage와 log/vacuum/sysop의 **접점** 중심
  - pgbuf ↔ WAL 연동, vacuum이 heap/btree를 청소하는 지점, sysop이 쓰이는 storage 연산
- **형식**: 4지선다 rapid-fire. 매 답변 후 코드 file:line 근거로 채점 + 해설. 흥미 지점만 자유서술 심화.
- **세션 로그**: 이 파일. 진행 중 갱신.

## 사전 확인된 사실 (질문 출제 근거)

- `vacuum.c/.h`는 `src/transaction/`이 아니라 **`src/query/`**에 있음.
- WAL 강제 지점: `pgbuf_bcb_flush_with_wal()` (`src/storage/page_buffer.c:10671`)
  — 페이지 flush 직전 `iopage.prv.lsa`를 복사해 `logpb_flush_log_for_wal()` 호출 (`page_buffer.c:10786`).
- sysop API: `log_sysop_start()` (`src/transaction/log_manager.h:200`) 등.

## 진행 상황 (4/4 정답, 난이도 상향 중)

### Q1. WAL 규칙의 buffer pool 강제 지점 — 정답 ✅

- dirty 페이지 flush 직전 → 해당 페이지 `prv.lsa`까지 로그 먼저 flush.
- 근거: `pgbuf_bcb_flush_with_wal()` (`page_buffer.c:10671`)이 `logpb_flush_log_for_wal()` 호출 (`:10786`, "confirm WAL protocol").

### Q2. vacuum의 대상 탐색 방식 — 정답 ✅

- 테이블 스캔이 아니라 **WAL 로그 블록을 읽음** (log-based vacuum).
- 근거: `vacuum_process_log_block()` (`src/query/vacuum.c:3242`) — "Vacuum heap and b-tree entries using log information found in a block of pages". 메타데이터는 `VACUUM_DATA_ENTRY`.

### Q3. DELETE의 물리적 효과 — 정답 ✅

- 레코드 제거 아님. MVCC 헤더에 delete MVCCID 도장만 (`MVCC_SET_DELID`, `heap_file.c:16370`).
- 실제 슬롯 제거는 `vacuum_heap()` (`vacuum.c:1488`)이 threshold MVCCID 이후 수행.

### Q4. B-tree split 후 트랜잭션 롤백 — 정답 ✅

- 분할은 sysop으로 독립 커밋되어 유지, 키만 logical undo로 제거.
- 근거: `btree.c:9862` `log_sysop_start` → `:9921` `log_sysop_commit` 등 다수 쌍.

### Q5. 페이지 해제(dealloc) 타이밍 — 오답 ❌ (I/O 최적화 선택 → 정답: undo 불가능)

- 정답: **해제는 undo 불가능한 연산** — 해제 즉시 다른 tx가 재사용 가능, 내 롤백 시 되돌릴 수 없음.
  → 롤백 가능성이 사라진 커밋 확정 후 run-postpone에서 실행.
- 근거: `file_manager.c:6151` "we postpone the deallocation after commit, since we don't want anyone to reuse it
  until we are really sure the page is no longer used", `:6194` `log_append_postpone (RVFL_DEALLOC, ...)`,
  파일 파괴도 `file_postpone_destroy()` (`:4411`) → `RVFL_DESTROY` postpone.
- 암기 대칭: **alloc = 즉시 (undo 가능) / dealloc = postpone (undo 불가)**.

### Q6. log_sysop_end_logical_undo의 존재 이유 — 모름 (설명 요청) 📖

- 정답: **물리 커밋 + 논리 undo 등록**. 물리 단계들은 확정하되, 트랜잭션 롤백 시 전체를 논리적으로
  되돌릴 undo 레코드 하나를 얹음 (예: btree 키 삽입 → `RVBT_DELETE_OBJECT_PHYSICAL`, `btree.c:34080`).
- 물리 undo가 안 되는 이유: 커밋~롤백 사이 다른 tx의 split로 키가 이사 가능 — 주석 "cannot be easily located"
  (`log_manager.c:3956`).
- sysop 종료 4종: commit(무조건 유지) / end_logical_undo(유지+논리취소) / abort(물리 undo) / attach_to_outer(흡수).
- 제약: logical undo sysop은 postpone 사용 불가 (주석 명시).

### Q7. vacuum 지연의 부작용 — 정답 ✅

- 로그 아카이브 삭제 불가 → 디스크 증가.
- 근거: `logpb_remove_archive_logs*`가 `vacuum_min_log_pageid_to_keep()` 확인 (`log_page_buffer.c:6028`, `:6308`, `:8123`;
  구현 `vacuum.c:5723`). vacuum이 밀린 만큼 아카이브가 보존됨.

### Q8. vacuum 후 슬롯 재사용 — 정답 ✅

- 테이블 속성에 따라 다름: 일반 = `REC_MARKDELETED` ("Slot cannot be reused"),
  REUSE_OID 테이블 = `REC_DELETED_WILL_REUSE` ("Slot will be reused") — `storage_common.h:1175`, `:1180`.
- REUSE_OID는 `heap_create_internal(..., reuse_oid)` (`heap_file.c:4667`)로 결정.

### Q9. DWB의 존재 이유 — 정답 ✅

- torn page 복구. WAL redo는 **온전한 이전 페이지 이미지**를 전제로 하므로, 페이지 자체가 반만 쓰이면 redo 불가.
- 근거: `double_write_buffer.cpp:3163` "Corrupted page in data volume. Check DWB.", `:3346` "Replace the corrupted
  pages in data volume with the DWB content." (복구 시점 동작).

### Q10. vacuum의 트랜잭션 신분 — 모름 (설명함) 📖

- 정답: **전용 system transaction (system tdes)**. worker가 `log_system_tdes`를 claim해서 그 신분으로 sysop 열고 로그를 씀.
- 근거: `vacuum.c:3290` `assert (thread_p->get_system_tdes () != NULL)`,
  `log_system_tran.cpp:88` `tdes->trid = systb_Next_tranid`, `log_impl.h:185`
  `LOG_SYSTEM_WORKER_FIRST_TRANID = NULL_TRANID - 1` → **TRANID가 음수 방향으로 감소**(사용자 tx와 번호 공간 분리).
- 복구 시 `rv_simulate_system_tdes(trid)` (`log_system_tran.cpp:174`)로 그 신분을 재현해 미완 sysop을 마무리.

### Q12. MVCC UPDATE에서 새 버전이 home 페이지에 안 맞을 때 — 정답 ✅

- 다른 페이지에 쓰고 home 슬롯에 `REC_RELOCATION` 남김.
- 근거: `heap_update_home` (`heap_file.c:22642`) 3분기 —
  ① big length → `heap_ovf_insert` + forwarding `REC_BIGONE` (`:22720`),
  ② `!spage_is_updatable(...)` → `heap_insert_newhome` + forwarding `REC_RELOCATION` (`:22765`, stat `PSTAT_HEAP_HOME_TO_REL_UPDATES`),
  ③ 맞으면 제자리 `REC_HOME`.
- 심화: 새 위치의 레코드 타입은 `REC_HOME`이 아니라 **`REC_NEWHOME`** — "No the original home of record. part of
  relocation process" (`storage_common.h:1163`). 독립 OID로 주소 지정 불가, home을 통해서만 도달.
- **CUBRID MVCC의 핵심 비대칭**: home 슬롯에는 **새 버전**이 들어가고, 이전 버전은 heap이 아니라 **로그**에서
  `prev_version_lsa`로 도달 (`heap_update_set_prev_version()`, `heap_file.c:861`;
  `or_mvcc_set_log_lsa_to_record` `:22174`). PostgreSQL처럼 heap에 구버전을 쌓지 않음.
  → 그래서 "구버전 읽기"가 로그 보존에 의존하고, 이것이 vacuum·아카이브 정책(Q7)과 직결.

### Q13. vacuum이 btree 항목을 찾아가는 방법 — 정답 ✅

- **키 값으로 루트부터 재탐색**. VPID를 신뢰하지 않음.
- 근거: vacuum은 로그 레코드에서 키를 뽑아 `key_buf`(`OR_BUF`)로 넘김 (`vacuum.c:3467`, `:3501`) →
  `btree_vacuum_object` (`btree.c:30518`)가 `buffered_key`를 그대로 `btree_delete_internal`에 전달
  (`BTREE_OP_DELETE_VACUUM_OBJECT`). 키 파싱은 `btree_rv_read_keyval_info_nocopy` (`btree.c:18298`).
- **왜 이게 sysop 설계와 맞물리는가**: Q6에서 본 logical undo(`RVBT_DELETE_OBJECT_PHYSICAL`)와 **완전히 동일한 이유**.
  split이 항목을 이사시킬 수 있으므로 물리 주소는 무효 — 그래서 btree의 logical undo와 vacuum이 모두 keyval을 로그에
  실어두고 재탐색한다. `log_manager.c:3956` "cannot be easily located" 주석의 실제 소비자가 이 두 경로.
- 정밀 매칭: `match_mvccinfo`에 delete MVCCID를 세팅 — 같은 키에 여러 OID/버전이 붙어 있어도 그 MVCCID를 가진 항목만 제거.

### Q14. checkpoint의 정체 — 오답 ❌ (1번 "전부 flush + 로그 절단" → 정답 2번)

- 함수 헤더가 곧 정답: `logpb_checkpoint - Execute a **fuzzy** checkpoint` (`log_page_buffer.c:6895`).
  반환값도 "pageid where a redo will start".
- 1번이 틀린 두 지점:
  - **전부 flush 아님**: `pgbuf_flush_checkpoint`는 "flushes any dirty unfixed page whose LSA is smaller than the
    last_chkpt_lsa, it returns the **smallest_lsa from the remaining dirty buffers which were not flushed**"
    (`page_buffer.c:4122-4131`). 남은 dirty가 있는 게 정상이고, 그 최소 LSA가 다음 redo 시작점.
  - **로그 절단(truncate) 아님**: 아카이브 삭제는 별개 경로이며 vacuum·CDC·활성 tx가 막을 수 있음 (Q7).
- 실제로 기록하는 것: 활성 트랜잭션 목록 (`logpb_checkpoint_trans`, `:6808` / 수집 루프 `:7061`)과
  **commit-postpone 상태의 sysop 목록** (`LOG_INFO_CHKPT_SYSOP`, `chkpt_topops`, `:6857`).
- **Q5·Q6 회수**: postpone 중인 sysop을 체크포인트가 따로 기록하는 이유 = run-postpone(dealloc 등)이 미완인 채
  크래시하면 복구가 그 지점을 이어받아야 하기 때문. Q5의 "dealloc은 postpone된다"가 체크포인트 레코드 구조에까지 흔적을 남김.
- fuzzy가 가능한 근거는 Q1: 모든 페이지가 WAL 규칙을 지키므로, 안 내려간 dirty 페이지는 redo로 복원 가능.
  체크포인트는 "일관 상태 만들기"가 아니라 **"redo 시작점을 앞으로 당겨 복구 시간을 줄이기"**.

## 형식 변경 (Q10 시점 사용자 요청)

- AskUserQuestion 프롬프트는 가독성이 떨어짐 → **평문 4지선다**로 출제, 사용자가 번호로 답변.
- Q11부터: **한 번에 한 문제만** 출제 (사용자 요청). 한꺼번에 여러 개 내지 않는다.

### Q11. REC_BIGONE 레코드 UPDATE 시 OID 유지 — 오답 ❌ (1번 선택 → 정답 2번)

- 사용자 논리: "overflow 페이지는 크기 변화와 무관, relocation이 아니니까 새로 쓰이고 **새 vpid가 recdes에 쓰일 뿐**" → 1번.
  - **논리 자체가 결론과 모순**: "recdes에 vpid를 쓴다"는 건 home 슬롯이 그대로 남아 포인터만 갱신된다는 뜻 = OID 유지 = 2번.
- 코드 사실 (사용자 모델보다 더 강함): overflow → overflow UPDATE는 **home recdes조차 안 건드림**.
  - `heap_update_bigone` (`heap_file.c:22096`) → `heap_is_big_length(new)` 참이면 `is_old_home_updated = false` (`:22181`),
    `heap_ovf_update`에 **기존 `context->ovf_oid`를 그대로 전달** (`:22183`). 첫 overflow 페이지 VPID도 불변.
  - 크기 변화는 체인 **뒷부분**에서만 흡수: `overflow_update`가 `file_alloc` (`overflow_file.c:523`) /
    `file_dealloc` (`:594`)로 페이지 추가·반납. 주석: "may allocate or deallocate several overflow pages if the
    multipage data increase/decrease in length" (`:368`).
- 설계 불변식: **heap OID = home 슬롯 주소, 절대 안 변함.** 인덱스가 OID를 저장하므로 OID가 변하면 전 인덱스 갱신이 필요.
  `REC_RELOCATION`/`REC_BIGONE`은 바로 그걸 피하기 위한 forwarding 장치
  (`heap_build_forwarding_recdes (..., REC_BIGONE, &context->ovf_oid)`, `heap_file.c:20434`).
  → 사용자의 "relocation 이런 게 아니니까"가 거꾸로: REC_BIGONE이 곧 forwarding 방식.
- **Q5와의 연결 (같은 함수 안에서!)**: `heap_file.c` 주석 "Page deallocation may append LOG_POSTPONE records,
  so do not use the transaction tail LSA here" — overflow 축소 시 `file_dealloc`이 postpone을 남기므로
  supplemental log가 tail LSA를 쓸 수 없음. `overflow_file.c:559`에도 동일 취지 주석.

## 미해결 / 후속 의문

(누적 예정)
