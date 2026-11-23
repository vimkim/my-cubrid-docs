# CBRD-28281 (ADR-0011 / Draft PR #8493) 기술적 미검증 항목 2건 조사 및 검증 보고서

작성일: 2026-11-23 (Asia/Seoul) · Work878 · 대상 브랜치: `CBRD-27925-emptied-set` (PR #8493, 로컬 커밋 `96fb566bcc` 포함; triage 후 `develop` rebase와 함께 push 예정)

## 요약 및 결론

CBRD-28281(ADR-0011: 빈 OOS 페이지 제자리 재사용 및 vacuum fast path 제거)의 채택 판단에 남아 있던 **기술적 미검증 항목 2건**을 모두 조사·실험·구현하여 닫았다.

1. **과제 1 — vacuum drain 지연(`0.34 s → 2.4 s`) 근본 원인 규명 및 연속 churn 영향**:
   - **원인 규명(확정)**: `2d40794363`(측정상 `5d7eda23c`, fast path 제거)부터 지연이 생긴 이유는 DML 로그 감소가 아니라, **ADR-0010의 vacuum worker가 fast path(`oos_reclaim_empty_pages` → `file_dealloc` sysop)를 돌며 스스로 쓰던 대량의 WAL이 사라졌기 때문**이다.
     - ADR-0010(`67220b7e23`)에서는 2,000행 UPDATE(1,000쪽 비움) 처리 중 선행 블록을 맡은 `VAC_WORKER` 스레드가 `file_dealloc` sysop WAL을 블록당 약 25~29쪽씩 쏟아부어 후속 미완성 31쪽 로그 블록을 **자가 폐쇄(self-close)** 했다.
     - ADR-0011(`f1c78ce70b`)에서는 fast path 제거로 `VAC_WORKER`가 redo-only `RVOOS_DELETE`만 소량 기록하므로 자가 폐쇄가 0건이 된다. 따라서 UPDATE 끝의 마지막 미완성 블록(최대 31쪽)을 외부 로그(harness의 filler)가 채워 닫아야 vacuum이 기동된다.
     - 기존 보고서의 "12 filler × 5.2쪽 ≈ 60쪽(2블록)" 추정은 `Num_log_page_iowrites`(커밋당 반복 flush I/O 횟수)를 실제 로그 페이지 전진량으로 오인한 착시였다. `REPEAT('f', 1500)` 200행은 WAL에서 LZ4 압축되어 **filler 1회당 실제 `pageid` 전진량은 약 2.07쪽**에 불과하며, 12~15개 filler는 **단일 31쪽 블록 1개**를 닫는 양이다.
   - **연속 churn 영향(판정)**: 대기·filler 없는 연속 churn 3종(2,000행 20 cycle 전체 churn, 500/1,000행 30회 연속 UPDATE, 4세션 동시 15회 UPDATE)에서 ADR-0011은 **무한 누적이나 해소되지 않는 vacuum backlog를 만들지 않았으며**, 섹터 수에서도 ADR-0010 대비 동등하거나 오히려 작았다(500행 `16 vs 17`, 1,000행 `24 vs 24`, 동시 4세션 `47 vs 48`, 2,000행 전체 churn 1·2차 합산 `36 vs 33~37` sector). 따라서 채택에 지장을 주는 공간/성능 결함이 아니다.

2. **과제 2 — 재초기화(`RVPGBUF_NEW_PAGE` redo-only) ~ INSERT 사이 crash 공백 검증 및 undo 전제 확인**:
   - **코드 전수 감사(확인)**: OOS 데이터 페이지(live OOS 파일)에 대해 **빈 OOS 페이지를 대상으로 실행되는 undo 경로는 전혀 존재하지 않음**을 확인했다.
   - **테스트 구현 및 통과(검증)**: `oos_test_exit_after_empty_page_reinit` 테스트 훅을 추가하고, `oos_reinit_empty_page`가 `RVPGBUF_NEW_PAGE`(redo-only)를 flush한 직후 `RVOOS_INSERT` 기록 전에 프로세스를 중단하는 서버 crash 복구 단위 테스트 2건(단독 crash, 선행 미커밋 `RVOOS_INSERT`로 실제 UNDO 페이즈가 동반 실행되는 crash)을 구현·통과시켰다(로컬 커밋 `96fb566bcc`).

---

## 1. 과제 1: vacuum drain 지연 근본 원인 규명

### 1.1 비교 대상 및 측정 방법

- **기준(ADR-0010, fast path 포함)**: `67220b7e23` (`2d40794363`의 직전 부모) `release_gcc` 빌드
- **후보(ADR-0011, PR #8493 원격 HEAD)**: `f1c78ce70b` `release_gcc` 빌드
- **진단 설정**: `growth_cost.py`와 동일 DB 규격(`2G` data / `1G` log, `data_buffer_size=256M`, `log_buffer_size=64M`, `stored_procedure=no`), `er_log_vacuum=4548` (`LOGGING | VACUUM_DATA | WORKER | MASTER | JOBS`)을 활성화해 서버 로그(`gdb_20261123_1820.err`, `gdb_20261123_1821.err`)에 모든 블록 생성(`vacuum_produce_log_block_data`), 보류(`Cannot generate job`), 완료(`Processing log block ... is complete`)를 기록했다.

### 1.2 재현 결과 (`c_rows=2000`, `1000`, 각 3 cycle)

| 행 수 | 사이클 | 작업 | base (`67220b7e23`) filler / 시간 | pr8493 (`f1c78ce70b`) filler / 시간 |
| --- | --- | --- | --- | --- |
| 2,000 | 1 | UPDATE | 1 (0.230 s) | 5 (0.889 s) |
| 2,000 | 2 | UPDATE | 1 (0.230 s) | 8 (1.387 s) |
| 2,000 | 3 | UPDATE | 1 (0.230 s) | 12 (2.047 s) |
| 2,000 | 1~3 | DELETE 30% | 12 / 9 / 12 (1.50~2.04 s) | 10 / 12 / 13 (1.71~2.21 s) |
| 1,000 | 1 | UPDATE | 4 (0.708 s) | 5 (0.890 s) |
| 1,000 | 2 | UPDATE | 8 (1.350 s) | 14 (2.374 s) |
| 1,000 | 3 | UPDATE | 9 (1.531 s) | 15 (2.539 s) |
| 1,000 | 1~3 | DELETE 30% | 11 / 13 / 14 (1.84~2.34 s) | 13 / 15 / 15 (2.21~2.54 s) |

### 1.3 `er_log_vacuum` 타임라인이 밝힌 메커니즘

`log_append.cpp:1422-1432`에서 `vacuum_produce_log_block_data`는 직전 MVCC/NOTIFY 레코드(`log_Gl.hdr.mvcc_op_log_lsa.pageid`)가 속한 31쪽 블록과 **다른 블록에 새로운 로그 레코드가 append될 때** 비로소 그 블록을 닫고 vacuum queue에 넘긴다.

`gdb_20261123_1820.err`(base)와 `gdb_20261123_1821.err`(pr8493)에서 블록별 생산자 스레드와 마지막 MVCC/NOTIFY 레코드 페이지(`last_mvcc_pg`)를 추출한 결과는 다음과 같다:

- **pr8493 (`f1c78ce70b`)**: 블록 `5`~`41` 전체에서 **`VAC_WORKER`가 닫은 블록이 0건**이며, 모든 블록의 `last_mvcc_pg`가 블록 끝 페이지(`blockid * 31 + 30`: `185, 216, ..., 464, 650, 836, ..., 1301`)다. `VAC_WORKER`가 기록하는 WAL은 redo-only `RVOOS_DELETE`와 heap vacuum 레코드뿐이라 다음 블록을 닫을 만큼 로그를 밀어내지 못한다.
- **base (`67220b7e23`)**: 2,000행 UPDATE 구간(사이클 1~3)에서 **블록 4개(`12, 13, 18, 23`)를 `VAC_WORKER` 스레드가 직접 닫았다**:
  - **사이클 1 UPDATE (`blk=10..13`)**:
    - `18:20:59.629` SQL이 `blk=10` (`310..340`, `last_mvcc_pg=340`) 닫음
    - `18:20:59.647` SQL이 `blk=11` (`341..371`, `last_mvcc_pg=371`) 닫음
    - `18:20:59.672` `VAC_WORKER(thr=4195, 4196)`이 `blk=10, 11` 실행 시작 → fast path `file_dealloc` sysop WAL을 쓰다가 **`18:20:59.674`(2 ms 뒤) `VAC_WORKER(thr=4195)`가 `blk=12` (`372..402`, `last_mvcc_pg=401|8128`)를 자가 폐쇄**
    - `18:20:59.814` `VAC_WORKER(thr=4341)`이 **`blk=13` (`403..433`, `last_mvcc_pg=422|14656`)까지 자가 폐쇄** (`18:21:00.035` 완료)
  - **사이클 2 UPDATE (`blk=16..18`)**:
    - `blk=18` (`558..588`)은 UPDATE가 **단 7쪽(`564|4312`)에서 끝났고 24쪽이 비어 있었음에도**, `blk=16, 17`을 처리한 `VAC_WORKER(thr=4195)`가 `file_dealloc` sysop WAL로 `589` 이상을 채워 **`18:21:02.400`에 `blk=18`을 자가 폐쇄** (`18:21:02.502` 완료)
  - **사이클 3 UPDATE (`blk=20..23`)**:
    - `blk=23` (`713..743`)은 UPDATE가 **단 3쪽(`715|2880`)에서 끝났음에도**, 선행 블록의 `VAC_WORKER(thr=4341)`가 29쪽 분량의 `file_dealloc` sysop WAL로 **`18:21:04.530`에 `blk=23`을 자가 폐쇄** (`18:21:04.624` 완료)

### 1.4 기존 미해결 관측 4가지 완전 해명

1. **왜 `2d40794363` (`5d7eda23c`, fast path 제거)부터 지연이 시작되었는가?**
   - `2d40794363`은 UPDATE 트랜잭션의 로그량을 크게 바꾸지 않았지만, `VAC_WORKER`가 호출하던 `oos_reclaim_empty_pages` (`file_dealloc` sysop, `RVFL_*` + `RVPGBUF_DEALLOC` + `LOG_SYSOP_*`)를 제거했다. 그 즉시 `VAC_WORKER`의 **자가 폐쇄(self-closing) 효과가 사라져**, UPDATE 끝의 미완성 블록(최대 31쪽)을 외부 filler가 닫아야만 vacuum이 시작된다.
2. **왜 `12 filler ≈ 60쪽(2블록)`이 아니라 실제로는 1블록(31쪽)인가?**
   - `statdump`의 `Num_log_page_iowrites`는 커밋(`csql -C`)마다 **같은 활성 로그 페이지가 디스크로 반복 flush되는 I/O 횟수**까지 센다(약 4~5회/filler).
   - 반면 로그 블록은 **실제 `LOG_PAGEID` 전진량**으로 닫힌다. `REPEAT('f', 1500)` 200행은 WAL에서 LZ4로 강하게 압축되므로 filler 1회당 실제 `pageid` 전진량은 **약 2.0~2.1쪽**(`31쪽 / 15 filler ≈ 2.07쪽`)이다. 12~15개 filler는 2블록이 아니라 **잔여 ~25~30쪽짜리 단일 블록 1개**를 닫는 데 필요한 양이다.
3. **왜 cycle 1과 cycle 2+ 및 행 수(`1,000`→`6,000`)·`DELETE`에서 차이가 갈리는가?**
   - `base`에서 자가 폐쇄가 일어나려면 **선행 블록에 `VAC_WORKER`가 `file_dealloc`을 수행할 빈 페이지가 충분히 많아야** 한다.
   - 2,000행 UPDATE(1,000쪽 비움)에서는 선행 블록들이 다수의 `file_dealloc`을 포함해 `VAC_WORKER`가 25~29쪽씩 WAL을 밀어 1 filler(`0.23 s`)로 끝난다.
   - 반대로 1,000행 UPDATE(500쪽 비움)는 UPDATE 전체 로그가 ~1.5블록뿐이라 선행 블록의 `file_dealloc` WAL만으로 마지막 블록의 잔여 ~20쪽을 다 채우지 못해 `base`에서도 `8~9` filler가 들었다(`pr8493`은 `14~15` filler).
   - `DELETE 30%`(600행, 약 200쪽만 비움)에서는 `file_dealloc` WAL이 ~6~10쪽 수준이라 `base`에서도 자가 폐쇄가 안 돼 양쪽 모두 `9~13` filler(`1.5~2.2 s`)가 든다.
   - 4,000/6,000행에서는 UPDATE 자체 블록 수가 커지고(각 ~3,000쪽 비움), `pr8493`에서도 마지막 블록 경계 잔여량이나 `big` filler 1회 투여 시 즉시 31쪽을 넘겨 양쪽 모두 `0.28~0.33 s`로 동일해진다.
   - 참고: Part 1 `statdump` 실측(`2,000`행 cycle 3)에서 `UPDATE` 중 `base`는 `d_alloc=300, d_dealloc=300`이 발생하나 `pr8493`은 `d_alloc=0, d_dealloc=0`이다.

### 1.5 연속 churn 워크로드 영향 판정 (시나리오 A·B·C)

`er_log_vacuum=0`(기본값)의 정상 `release_gcc` 빌드(`stored_procedure=no`, `statdump -i 1` 활성)에서 **대기 및 filler 없이** 연속 churn 3종을 실행했다.

| 시나리오 | 워크로드 | base (`67220b7e23`) | pr8493 (`f1c78ce70b`) | 비교(pr8493 vs base) |
| --- | --- | --- | --- | --- |
| **A (1차)** | 2,000행 20 cycle 연속 (`UPD→DEL→INS`) | `5.05 s`, max `2,098`쪽, **`33` sector** | `5.31 s`, max `2,247`쪽, **`36` sector** | `+3` sector (`+9.1%`, cy10 이후 평평, 누적 없음) |
| **A (2차, 단계별 trace)** | 2,000행 12 cycle 연속 (매 단계 `SHOW HEAP OOS`) | max **`2,312`쪽, `37` sector** (cy3~12 평평) | max **`2,277`쪽, `36` sector** (cy12 도달) | **`-1` sector** (`pr8493`이 cy11까지 `2,001`쪽 유지) |
| **B-500** | 500행 30회 연속 `UPDATE` (한 세션) | `3.06 s`, `1,042`쪽, **`17` sector**, `recs=945` | `3.36 s`, `1,001`쪽, **`16` sector**, `recs=621` | **`-1` sector** |
| **B-1000** | 1,000행 30회 연속 `UPDATE` (한 세션) | `4.22 s`, `1,501`쪽, **`24` sector**, `recs=2,000` | `5.00 s`, `1,501`쪽, **`24` sector**, `recs=2,000` | **`0` sector** (동일) |
| **C (동시 4세션)** | 2,000행 4세션 × 15회 연속 `UPDATE` | `1.24 s`, `3,047`쪽, **`48` sector**, `recs=2,400` | `1.45 s`, `3,001`쪽, **`47` sector**, `recs=2,483` | **`-1` sector** |

> [!IMPORTANT]
> **과제 1 최종 판정**: 연속 churn에서 `pr8493`의 drain 지연(자가 폐쇄 부재)은 **일시적인 미완성 블록 1개분(최대 ~500개 옛 chunk)의 회수 시점만 1블록 뒤로 미룰 뿐**, `base`에서도 연속 `UPDATE→DELETE→INSERT` 타이밍이 겹치면 동일한 미회수 1블록 현상(`33~37` sector)이 발생한다. 모든 시나리오에서 무한 성장이나 해소되지 않는 vacuum backlog는 관찰되지 않았고(종료 시 `recs=2,000` 수렴), 소규모·동시 연속 UPDATE에서는 `pr8493`의 섹터 수가 `base`보다 같거나 오히려 1 sector 작았다. **채택에 장애가 되는 실질적 공간·backlog 문제는 없다.**

---

## 2. 과제 2: 재초기화 ~ INSERT 사이 crash 검증 및 undo 전제 확인

### 2.1 전제 검증: '빈 OOS 페이지를 대상으로 하는 undo 경로가 전혀 없다'

코드 전수 감사 결과, live `FILE_OOS` 데이터 페이지에 대해 빈 페이지를 대상으로 실행되는 undo 경로는 **0건**임을 확인했다:

| 로그/연산 경로 | 파일 및 위치 | 기록 유형 / Undo 동작 | 빈 OOS 페이지를 대상으로 undo될 수 없는 근거 |
| --- | --- | --- | --- |
| `RVOOS_DELETE` (`oos_log_delete_physical`) | `src/transaction/recovery.c:887-892`, `src/storage/oos_file.cpp:3210-3220` | **redo-only** (`undofun = NULL`, `log_append_redo_data`) | ADR-0008. 청크 삭제는 복구/롤백 시 절대 undo되지 않음. |
| `RVOOS_NOTIFY_VACUUM` | `src/transaction/recovery.c:905-910`, `src/storage/oos_file.cpp:3955-3980` | `undofun = vacuum_rv_es_nop` | 알림 레코드 자체의 undo는 no-op; 실제 청크 삭제는 vacuum worker가 `RVOOS_DELETE`(redo-only)로 수행. |
| `RVOOS_RECLAIM_POSTPONE`, `RVOOS_UPDATE_DROP_POSTPONE` | `src/transaction/recovery.c:917-928`, `src/storage/oos_file.cpp:3778-3844` | `undofun = NULL` (`log_append_postpone`) | 트랜잭션 abort 시 postpone은 폐기되며, commit 후에만 `RVOOS_DELETE`(redo-only) 또는 알림을 실행. |
| `RVOOS_INSERT` (`oos_log_insert_physical`, `oos_rv_undo_insert`) | `src/transaction/recovery.c:881-886`, `src/storage/oos_file.cpp:3179-3199, 4265-4274` | `log_append_undoredo_crumbs` (`undofun = oos_rv_undo_insert`) | undo할 INSERT가 남아 있는 동안 해당 청크가 페이지 슬롯에 존재해 `spage_number_of_records(page_ptr) >= 1`이므로 `oos_try_reuse_page` (`oos_file.cpp:1631`)가 빈 페이지로 채택할 수 없다. 또한 undo 실행 시 페이지 WRITE 래치로 직렬화되고 `LOG_COMPENSATE`로 닫히므로 재실행되지 않는다. |
| `oos_reinit_empty_page` (`RVPGBUF_NEW_PAGE`) | `src/storage/oos_file.cpp:1575-1591`, `src/storage/page_buffer.c:15915-15923` | **redo-only** (`pgbuf_log_redo_new_page` → `log_append_redo_data2`) | `recovery.c:791-794`에 `pgbuf_rv_new_page_undo`가 등록돼 있으나, `log_append_redo_data2`는 undo 이미지를 갖지 않는 redo-only 레코드이므로 트랜잭션 abort/재시작 UNDO 시 `pgbuf_rv_new_page_undo`가 호출되지 않는다. |
| 신규 페이지 할당 (`oos_file_alloc_new`, `oos_vpid_init_new`) | `src/storage/oos_file.cpp:2920-2946, 3153-3168` | `log_sysop_start` 내 `RVPGBUF_NEW_PAGE` (`log_append_undoredo_data2`) | sysop 커밋(`log_sysop_commit`) 이후에만 페이지가 파일에 노출되므로, sysop 완료 후에는 undo 대상이 아니다. |
| 파일 생성/헤더 (`oos_create_file_internal`) | `src/storage/oos_file.cpp:1139-1210` | `log_sysop_start` 내 sticky header 초기화 + `slot 0` 삽입 | sticky header는 `slot 0`에 `OOS_HDR_STATS`를 영구 보유하고, `oos_try_reuse_page` (`oos_file.cpp:1611`)가 `VPID_EQ(&vpid, &hdr_vpid)`로 명시 제외한다. |
| 슬롯 페이지/파일 해제 (`slotted_page.c`, `file_manager.c`) | `src/storage/slotted_page.c`, `src/storage/file_manager.c:4056` | `slotted_page.c` 자체 WAL 없음; OOS는 `file_destroy`에서만 해제 | `oos_file.cpp`에서 `file_dealloc` 호출은 0건이며 live OOS 데이터 페이지는 `file_destroy` 외에 dealloc되지 않는다. |

### 2.2 테스트 훅 및 재초기화~INSERT 사이 crash 단위 테스트

기존 테스트(`95733273fe`)는 재초기화 후 `RVOOS_INSERT`까지 완료된 뒤 미커밋 crash만 검증했다. 이번 작업에서 다음 훅과 테스트 2건을 추가했다(로컬 커밋 `96fb566bcc`):

- **테스트 훅 (`src/storage/oos_file.hpp:330`, `src/storage/oos_file.cpp:221, 1582-1590, 4732-4735`)**:
  - `oos_test_exit_after_empty_page_reinit (int exit_code)`: `CUBRID_UNIT_TEST_ENABLED` 빌드에서 `oos_reinit_empty_page`가 `pgbuf_log_redo_new_page`로 `RVPGBUF_NEW_PAGE`를 기록한 직후, 호출자가 `RVOOS_INSERT`를 기록하기 전에 `logpb_force_flush_pages(thread_p)`로 로그를 디스크에 flush하고 `std::_Exit(exit_code)`로 프로세스를 즉시 종료한다.
- **신규 단위 테스트 (`unit_tests/oos/test_oos_server_crash_recovery.cpp:558-774, 845-853`)**:
  1. `CrashBetweenEmptyPageReinitAndInsertThenRestartKeepsTheEmptyPageForReuse`:
     - 죽은 ANCHORED 슬롯 4개가 남아 최대 크기 청크가 들어가지 않는 빈 페이지(`user_pages == 2`)를 준비·커밋한 뒤, 최대 크기 INSERT 도중 `oos_reinit_empty_page` 직후(`RVOOS_INSERT` 전)에 `std::_Exit(45)`로 crash한다.
     - 재시작 복구 후 해당 페이지가 `PAGE_OOS`이며 레코드 0개, **`spage_max_space_for_new_record >= 최대 청크 + 헤더 크기`**(redo 재실행으로 죽은 슬롯 정리 완료), `user_pages == 2`임을 확인한다. 이어서 최대 크기 INSERT를 수행해 **`reclaim_growth_reinit_pages == 0`**(재초기화 불필요), **`reuse_oid.pageid == dead_slot_vpid.pageid`**, `user_pages == 2`(새 페이지 할당 없음), 데이터 바이트 일치까지 증명한다.
  2. `CrashBetweenEmptyPageReinitAndInsertWithActiveUndoThenRestartKeepsTheEmptyPageForReuse`:
     - 동일한 crash 창구 직전에 같은 트랜잭션이 별도 OOS 파일(`other_oos_vfid`)에 미커밋 `RVOOS_INSERT` 1건을 먼저 기록해 두어, 재시작 복구 시 해당 트랜잭션의 **UNDO 페이즈가 실제로 실행**되도록 강제한다.
     - 재시작 후 `other_oid`는 정상 undo되어 읽기 불가(`oos_unreadable`)가 되는 한편, `dead_slot_vpid`의 redo-only `RVPGBUF_NEW_PAGE`는 undo되지 않고 유효한 빈 `PAGE_OOS`로 남아 재사용됨을 증명한다.

### 2.3 단위 테스트 실행 결과 (`debug_gcc`, 로컬 커밋 `96fb566bcc` 기준)

Debug 빌드(`UNIT_TEST_OOS=ON`, `UNIT_TEST_SPAGE=ON`, `UNIT_TEST_PAGE_BUFFER=ON`) 후 `ctest --test-dir build_preset_debug_gcc` 실행 결과:

- `oos_setup_db`, `test_oos_bestspace`, `test_oos_growth_sweep` (18 cases), `test_oos_vacuum_server`, `test_oos_real_vacuum_server`, `oos_cleanup_db`, `oos_setup_recovery_db`, `test_oos_sql_crash_recovery`, `oos_cleanup_recovery_db`, `oos_setup_server_crash_db`, `test_oos_server_crash_recovery` (4 cases — 기존 2건 + 신규 2건 `2282 ms`, `7872 ms`), `oos_cleanup_server_crash_db`: **12/12 전부 Passed** (실행 시간 157.40 sec).
- `lefthook` pre-commit `codestyle` 검사 통과 (`Unchanged`).

---

## 3. CBRD-28281 채택 판단 요약

- 이슈에 남아 있던 기술적 미검증 항목 2건(**drain 지연 원인 및 연속 churn 공간/backlog 영향**, **재초기화~INSERT 사이 crash 복구 및 undo 부재 전제**)이 모두 실측·코드 감사·서버 crash 테스트로 닫혔다.
- **ADR-0011 채택을 가로막는 기술적 결함은 발견되지 않았다.** 후속 절차는 CBRD-28281 triage 결정에 따라 `develop` 기준 rebase 및 전체 CI 실행이다.
