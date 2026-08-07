# Declared Scope

Status: FROZEN

## Analysis Topic

CUBRID page buffer의 latch 체계(READ/WRITE 2단계)와 그 두 가지 구조적 결과 — (1) `pgbuf_promote_read_latch` 의 실패 기반 READ→WRITE 승격이 B-tree 하강에 만드는 재시작 비용, (2) flush가 frame 안정성을 확보하지 못해 매번 페이지 사본을 떠서 쓰는 비용 — 를 소스와 런타임으로 재구성하고, SX(shared-exclusive) latch 도입이 이 두 비용을 어떻게 바꾸는지, 그리고 AIO/direct I/O write 도입 시 frame 안정성이 왜 전제조건이 되는지를 대학교 2학년 눈높이로 설명한다.

## Included Interfaces and Dependencies

- CUBRID (pinned `f799e05d77d5`, worktree): `src/storage/page_buffer.c`/`.h` 중 latch 상태어(`pgbuf_atomic_latch_impl`), fix/unfix, lock-free READ 경로(`pgbuf_lockfree_fix_ro`/`unfix_ro`), 승격(`pgbuf_promote_read_latch`), 대기/wakeup(`pgbuf_block_bcb`, `pgbuf_wakeup_reader_writer`), flush 깔때기(`pgbuf_bcb_flush_with_wal`)와 그 직접 호출자, `PGBUF_LATCH_FLUSH` pseudo-mode. 승격 호출자: `src/storage/btree.c` insert/delete 경로, `src/storage/file_manager.c`. 관측: `src/base/perf_monitor.c` 의 promote/flush 통계.
- PostgreSQL (pinned `fd2b89854d93`, master=20devel): buffer content lock 3-mode 구현(`bufmgr.c` `BufferLockAttempt`/`BufferLockAcquire`), `FlushBuffer` 의 share-exclusive 요구, AIO write 부재. 비교 축: flush 중 frame 안정성 확보 방식.
- MySQL/InnoDB (pinned `06a5c1c99c37`, trunk): `buf0buf.cc` 의 S/SX/X latch 획득, `buf0flu.cc` 의 flush 중 SX 보유, write 완료 시 SX 해제. 비교 축: 동일.
- OS 상호작용: buffered write vs direct I/O/AIO 에서 사용자 버퍼 안정성 요구의 차이(개념 설명 + PG 커밋 메시지 근거).

## Exclusions and Compatibility Limits

- SX latch의 실제 CUBRID 구현(코드 변경)은 범위 밖이다. 이 보고서는 도입 판단 근거와 설계 스케치 수준까지만 다룬다.
- victim 선정/LRU 정책, DWB 내부 구현, TDE 암호화 알고리즘, WAL 포맷, checkpoint 알고리즘 상세는 flush 깔때기와 만나는 지점까지만 다룬다.
- ABI/on-disk/타이밍/성능 수치 호환성은 약속하지 않는다. 성능 주장은 "현행 구조에 이 비용이 존재한다"는 사실과 타 DBMS의 설계 선택까지만 증거로 말하고, "SX 도입 시 X% 개선"은 미래 측정 항목(CBRD-27196)으로 남긴다.
- PostgreSQL/MySQL 서버 실행은 하지 않는다(소스 근거만).

## Shared Three-Database Scenario

"동시에 여러 세션이 읽는 hot page 하나를 (a) 한 스레드가 읽다가 수정해야 할 때(B-tree insert 하강 중 split), (b) flusher가 디스크에 써야 할 때" — 이 두 순간에 각 DBMS가 page latch/lock을 어떤 mode로 잡고, reader가 언제 막히며, 페이지 사본이 언제 필요한지를 같은 축으로 비교한다.

## Central Behaviors

report.json `central_behaviors` 와 1:1 대응:

1. `promote-fail-restart` — CUBRID B-tree insert가 READ 하강 중 `pgbuf_promote_read_latch` 로 WRITE 승격을 시도하고, 실패 시 루트부터 WRITE 하강으로 재시작하는 흐름. 승격이 실패 기반인 이유(upgrade deadlock)와, SX가 이 실패 분기를 없애는 원리. 런타임 증거: promote 성공/실패 perfmon 카운터.
2. `flush-frame-stability` — CUBRID flush가 BCB mutex 아래에서 페이지 사본을 뜨고 mutex를 풀어 I/O 동안 writer를 막지 않는 흐름(재더티 추적 포함), buffered write에서 이 방식이 안전한 이유, direct I/O/AIO write에서 frame 안정성(SX 등가 또는 사본)이 필수가 되는 이유, InnoDB/PG 20devel이 SX 보유 + 무복사로 수렴한 설계. 런타임 증거: flush/checkpoint perfmon 카운터.

## Coverage Questions

- orientation: 이 보고서가 답하는 세 질문(현행 CUBRID에서 SX만으로 B-tree 성능이 좋아지나 / AIO 없이 flush 이득이 있나 / AIO 도입 시 SX가 왜 필수인가)과 범위, 세 저장소 revision.
- mental-model: latch란 무엇이고 lock과 어떻게 다른가, READ/WRITE 2단계의 문제를 hot page 시나리오로 설명.
- scope-interface-seams: `pgbuf_fix`/`pgbuf_promote_read_latch`/`pgbuf_bcb_flush_with_wal` 의 caller 계약(허용 mode, 실패 코드, 재시도 의무).
- data-ownership-lifetime: `pgbuf_atomic_latch_impl` 상태어와 BCB/holder의 소유·수명, fcnt와 latch_mode의 의미.
- lifecycle-state-machines: latch 상태 전이(NO_LATCH↔READ↔WRITE, FLUSHING_TO_DISK 플래그), 승격 상태 전이(성공/실패/재시작).
- core-workflows: (1) B-tree insert 하강+승격+실패 재시작 전체 경로, (2) flush 깔때기 전체 경로(사본→WAL→write→재더티 복원).
- concurrency: upgrade deadlock의 사이클 구조, promotion의 포기 규칙, lock-free READ CAS와 waiter_exists 밸브, SX의 교착 회피 전제(blocking READ→SX 금지).
- storage-durability-recovery: WAL 선행 규칙이 flush 순서에 강제하는 것, 사본 flush에서 재더티가 durability를 깨지 않는 이유.
- policies-algorithms: 사본 flush vs SX 직접 flush의 트레이드오프 표, promotion 두 조건(ONLY_READER/SHARED_READER)의 정책.
- errors-resource-pressure: 승격 실패 에러(`ER_PAGE_LATCH_PROMOTE_FAIL`)의 전파와 호출자 의무, latch timeout 방어(교착 감지기 부재).
- performance-observability: promote/flush perfmon 카운터, statdump 사용법, 현행 비용의 관측 지점.
- experimental-validation: 두 실험(promote 카운터, flush 카운터)의 가설/관찰/한계.
- postgresql-analysis: content lock 3-mode(SHARE/SHARE_EXCLUSIVE/EXCLUSIVE), FlushBuffer의 share-exclusive 요구, 출시 버전(2-mode+사본)과의 대비, AIO write 부재.
- mysql-analysis: InnoDB rw_lock S/SX/X, flush 중 SX 보유, WL#6363/6326 맥락.
- cross-database-comparison: "flush 중 frame 안정성 확보 방식"과 "read-then-write 승격 방식" 두 축의 3사 비교표(equivalent/partial analogy/no equivalent).
- reimplementation-blueprint: SX 도입 설계 스케치(상태어 확장, lock-free 경로 조건, 승격 규칙, flusher 소유권, 단계적 도입)와 검증 시나리오.
- glossary-evidence-unknowns: 용어집, claim 색인, 미해결 질문(임계값, DWB 사본 수, 다중 page 승격 순서).
- teaching-map: 장별 claim ID ↔ quiz ↔ grill 개념 매핑.
