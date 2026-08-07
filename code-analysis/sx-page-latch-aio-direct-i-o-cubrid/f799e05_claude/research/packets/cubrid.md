# CUBRID Source Tracer Packet

- Role: CUBRID Source Tracer (main agent 직접 수행)
- Topic: SX page latch 도입 효과 — 승격 실패/재시작과 flush frame 안정성
- Scope digest: research/scope.md (FROZEN, sha256 92ff1f0aa7a2...)
- Revision: f799e05d77d5300c6ea5753b4a6cc7caee6d8912 (worktree; 인용 파일은 모두 tracked-clean → COMMIT 상태)
- Timestamp: 2026-08-07T05:25Z
- 비고: 세션 앞부분에서 baseline 5cd4f860e 기준으로 동일 사실을 검증했고(교차 확인), 본 패킷의 라인 번호는 전부 pinned HEAD(f799e05d) 기준으로 재검증했다.

## 1. latch mode 체계

- `src/storage/page_buffer.h:190-197` — `PGBUF_LATCH_MODE` 는 `enum:uint16_t`, 값은 `PGBUF_NO_LATCH(0)`, `PGBUF_LATCH_READ(1)`, `PGBUF_LATCH_WRITE(2)`, `PGBUF_LATCH_FLUSH(3, "this is only used as block mode. page can never be fixed with flush latch mode.")`, `PGBUF_LATCH_INVALID(4)`. content latch는 READ/WRITE 2단계뿐.
- `src/storage/page_buffer.h:198-203` — `PGBUF_LATCH_CONDITION` = `PGBUF_UNCONDITIONAL_LATCH` / `PGBUF_CONDITIONAL_LATCH` (nowait fix 지원).

## 2. 상태어와 holder

- `src/storage/page_buffer.c:499-508` — `union pgbuf_atomic_latch_impl { uint64_t raw; struct { PGBUF_LATCH_MODE latch_mode; uint16_t waiter_exists; int32_t fcnt; } impl; }`. 집계 mode + 전체 fix 수만 저장, holder별 mode 없음.
- `src/storage/page_buffer.c:445-446` — holder 쪽은 `PGBUF_HOLDER_STAT` 의 perf 전용 비트 `hold_has_write_latch:1`, `hold_has_read_latch:1` 뿐(통계용, 권위 없음).

## 3. lock-free READ 경로

- `src/storage/page_buffer.c:7725-7805` — `pgbuf_lockfree_fix_ro`: mutex 없이 CAS로 READ fix. grant 조건(`:7742-7746`): `latch_mode == PGBUF_LATCH_READ && !waiter_exists && fcnt != 0 && vpid 일치` — 하나라도 어긋나면 NULL 반환(느린 mutex 경로로 폴백). `:7747` 에서 `fcnt++` 후 `compare_exchange_weak`.
- `src/storage/page_buffer.c:7807-` — `pgbuf_lockfree_unfix_ro` 역시 같은 word를 CAS. `waiter_exists` 가 서 있으면 느린 경로로 폴백해 대기자 wakeup을 처리.
- 진입점: `:2362` (`pgbuf_fix_internal` 내).

## 4. READ→WRITE 승격 (promote-fail-restart의 핵심)

- `src/storage/page_buffer.c:2842-3060` — `pgbuf_promote_read_latch(_release/_debug)`. 분기:
  - 단독 holder이고 첫 대기자가 promoter가 아니면 제자리 승격(`:2926-2932`, `:2929` 에서 `latch_mode = PGBUF_LATCH_WRITE`).
  - 단독 holder라도 첫 대기자가 다른 promoter면 즉시 `ER_PAGE_LATCH_PROMOTE_FAIL`(`:2916-2925`).
  - 공유 holder + (`PGBUF_PROMOTE_ONLY_READER` 조건 또는 첫 대기자가 promoter)면 즉시 실패(`:2936-2951`). 소스 주석(`:2939-2945`): 두 promoter가 공존하면 "we can't guarantee both will see the same page they initially fixed".
  - 공유 holder + `PGBUF_PROMOTE_SHARED_READER` 조건이면 자기 fix를 전부 빼고(`:2976` `holder->fix_count = 0`, `:2988` "at this point the page is unfixed") WRITE 첫 대기자로 등록(`:2994` `pgbuf_block_bcb(..., as_promote=true)`).
  - SA_MODE는 무조건 제자리 WRITE 전환(`:3057`).
- 교착 방어: `src/storage/page_buffer.c:7148-7152` 주석 — "We do not guarantee that there is no deadlock between page latches... block the request with timed sleep method". 페이지 latch에는 교착 감지기가 없다.

## 5. 승격 호출자 (전수)

- `src/storage/btree.c` insert 경로 4곳: `:28079`(root, SHARED_READER), `:28372`, `:28645`(ONLY_READER), `:28675`. 실패 fallback: `:28645-28654` — unfix 후 `insert_helper->nonleaf_latch_mode = PGBUF_LATCH_WRITE` 로 루트부터 재시작(`*restart = true`).
- `src/storage/btree.c` delete/merge 경로 7곳: `:31715`, `:31829`, `:31834`, `:31838`, `:32076`, `:32082`, `:32086` — `crt_page` → `left_page`/`child_page` → `right_page` 3-page 연속 승격.
- `src/storage/file_manager.c:8251` 1곳.
- 재시작 하강은 latch coupling(자식 잡고 부모 해제)으로 경로의 각 non-leaf를 WRITE로 잡는다 — `btree_search_key_and_apply_functions` 의 advance 루프.

## 6. flush 깔때기 (flush-frame-stability의 핵심)

- `src/storage/page_buffer.c:10733-10960` — `pgbuf_bcb_flush_with_wal`:
  - `:10801` `pgbuf_bcb_mark_is_flushing` — `FLUSHING_TO_DISK` 설정 + `DIRTY` 해제(재더티 추적 준비; 함수 정의 쪽 주석: flush 중 다른 스레드가 fix/수정할 수 있으므로 새 변경을 추적해야 한다).
  - `:10811` TDE page는 `tde_encrypt_data_page` 로 암호화 출력 사본 생성.
  - `:10820` plain page는 `memcpy(iopage, &bufptr->iopage_buffer->iopage, IO_PAGESIZE)` 로 사본 생성 — **매 flush마다 IO_PAGESIZE(기본 16KiB) 복사**.
  - `:10841` BCB mutex 해제 — 이후 writer는 frame을 자유롭게 수정 가능(사본이 있어 안전).
  - `:10848` `logpb_flush_log_for_wal(&lsa)` — WAL 선행 규칙(page LSA까지 로그를 먼저 디스크에).
  - 이후 사본을 DWB slot 또는 디스크에 write. 실패 시 `pgbuf_bcb_mark_was_not_flushed` + `oldest_unflush_lsa` 복원 경로.
- 직접 호출자: page flush thread(`:4098` 부근), victim 경로 `pgbuf_bcb_safe_flush_internal`(호출 `:8884` 부근), neighbor flush `pgbuf_flush_neighbor_safe`(`:12167` 부근), checkpoint는 순차 flusher 경유. (호출자 라인은 ±수십 행 오차 허용 — 함수명 기준으로 인용.)
- content latch와의 관계: flush는 page 를 fix하지 않고(BCB mutex + FLUSHING 플래그로 보호) I/O 동안 READ/WRITE 어느 쪽도 막지 않는다. WRITE holder가 자기 page를 직접 flush하는 것도 허용(진입부 latch 검사, `:10758-10779` 부근 assert).

## 7. 관측 지점

- `src/base/perf_monitor.c:446-448` — `Data_page_total_promote_success` / `Data_page_total_promote_fail` / `Data_page_total_promote_time_msec` (computed ratio 계열).
- `src/base/perf_monitor.c:572-575` — `Num_data_page_promote_ext` / `Num_data_page_promote_time_ext` (확장 복합 카운터).
- flush 계열: `Num_data_page_flushed` 등 (statdump 로 노출).
- 노출 경로: `cubrid statdump <db>` (SERVER_MODE 전용; SA_MODE 승격은 `:3057` 분기라 perfmon을 타지 않음).

## 8. Unknowns

- DWB 사용 시 사본 수가 1회로 줄어드는지(SX 직접 flush 가정 시)는 `dwb_set_data_on_next_slot` 의 slot 보관 방식 확인 필요 — 이 보고서 범위 밖(JIRA CBRD-27196 OQ5).
- promote 실패를 결정적으로 재현하는 단일-머신 시나리오(두 세션 타이밍 의존)는 실험 범위에서 제외 — 성공 카운터 관측으로 대체.
