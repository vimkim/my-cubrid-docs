# Declared Scope

Status: FROZEN

## Analysis Topic

CUBRID의 page flush와 향후 write AIO에서 정말 필요한 것이 범용 `SX` page latch인지, 아니면 더 좁은
frame 안정성 계약인지 검토한다. 현재 snapshot-copy flush의 동작을 소스로 재구성하고, buffered
synchronous write, synchronous `O_DIRECT`, copy-based AIO, frame-based zero-copy AIO를 분리해 설명한다.
그 위에서 기존 `READ` latch, 범용 `SX` latch, 전용 `IO_WRITE_FREEZE` 상태, 현행 사본 유지의 정확성·소유권·
동시성·durability·비용을 비교하여 CUBRID에 맞는 경계를 권고한다.

## Audience and Teaching Goal

- 대상: 운영체제의 동기/비동기 I/O와 데이터베이스 buffer pool을 처음 연결해 보는 컴퓨터공학 2학년 수준.
- 목표: “AIO라서 SX가 필요하다”를 외우는 대신, **어느 메모리가 언제까지 살아 있고 누가 바꾸지 못해야
  하는가**라는 불변식에서 필요한 동기화 수단을 스스로 도출하게 한다.
- 모든 핵심 결론은 한국어 본문만으로 이해할 수 있게 하고, source/experiment Claim은 검증 경로로 붙인다.

## Included Interfaces and Dependencies

### CUBRID — pinned `f799e05d77d5300c6ea5753b4a6cc7caee6d8912`

- `src/storage/page_buffer.h`, `src/storage/page_buffer.c`
  - `PGBUF_LATCH_MODE`, BCB latch word, holder/fix lifetime, `FLUSHING_TO_DISK`, dirty/oldest-unflush-LSA 상태.
  - `pgbuf_bcb_flush_with_wal`, `pgbuf_bcb_mark_is_flushing`, 성공/실패 상태 복구, 직접 호출자.
  - `pgbuf_fix`/`pgbuf_unfix`의 READ/WRITE 계약과 victim/invalidation 상호작용.
- `src/storage/file_io.c`/`.h`: 실제 동기 page write 경로와 사용자 buffer 소비 구간.
- `src/storage/double_write_buffer.cpp`/`.hpp`: DWB가 출력 이미지의 수명과 사본 비용에 주는 영향.
- `src/storage/tde.c`/`.h`: 암호화 페이지에서 별도 출력 이미지가 필요한 경계.
- `src/transaction/log_page_buffer.c` 및 직접 연결 지점: WAL-before-data 제출 순서.
- `src/base/perf_monitor.c`/`.h`: flush/checkpoint 관측값. 기존 보고서의 promote summary 산식 오류는
  B-tree 성능 근거를 재사용하지 말아야 하는 교정 사례로만 다룬다.
- 로컬 지식 베이스의 CBRD-27193/27196 문서는 documented intent와 open question의 출처로 사용하되,
  실제 동작의 증거는 pinned source와 이번 Report Run의 runtime evidence로 제한한다.

### PostgreSQL — pinned `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc`

- buffer content lock의 `SHARE`, `SHARE_EXCLUSIVE`, `EXCLUSIVE` 의미와 `FlushBuffer` 계약.
- snapshot-copy/`BM_JUST_DIRTIED` 제거 이유, hint-bit writer와 flush의 관계, AIO write 준비 상태.
- 비교 책임: “flush용 불변 frame을 누가, 어느 상태로, 언제까지 소유하는가”.

### MySQL/InnoDB — pinned `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`

- buffer block의 S/SX/X latch, `io_fix`/write I/O lifetime, flush submission/completion의 소유권.
- doublewrite와 actual datafile write 사이 page image의 수명.
- 비교 책임: 같은 이름의 SX가 아니라 “reader 허용 + writer 금지 + single flusher + eviction 금지” 계약.

### OS I/O Semantics

- 일반 buffered synchronous `write`: 호출이 반환하기 전까지 전달 buffer가 안정해야 한다.
- synchronous `O_DIRECT`: page cache 우회 여부와 비동기 여부를 분리하며, blocking 호출의 반환까지 buffer가
  안정해야 한다.
- AIO: submit 반환이 아니라 completion까지 제출 buffer의 주소·내용 수명이 유지되어야 한다.
- 커널 API 일반론은 이 보고서의 설계 전제이며, CUBRID가 실제 AIO를 사용한다는 주장으로 확장하지 않는다.

## Exclusions and Compatibility Limits

- 실제 CUBRID SX/AIO 구현, benchmark용 prototype, source mutation은 범위 밖이다.
- read AIO/prefetch, scan scheduling, 장치별 queue-depth 튜닝, io_uring API 상세는 범위 밖이다.
- B-tree insert/delete의 SX 설계는 “범용 SX 도입과 flush 전용 상태의 경계”를 설명할 만큼만 언급한다.
- TDE 알고리즘 내부, DWB 복구 알고리즘, WAL record format, 전체 checkpoint 정책은 flush 계약과 만나는
  지점까지만 다룬다.
- ABI, on-disk 형식, 모든 crash interleaving, 성능 향상률을 약속하지 않는다.
- PostgreSQL/MySQL 서버는 실행하지 않으며 pinned source 비교만 한다.

## Shared Three-Database Scenario

dirty page `P`를 reader `R`, writer `W`, flusher `F`가 공유한다. `F`는 `P`의 특정 시점 이미지를 datafile에
기록하려 한다. 같은 축으로 다음을 묻는다.

1. 디스크 write가 읽는 메모리는 live frame인가 snapshot copy인가?
2. 그 메모리의 owner와 lifetime은 submitter thread까지인가 completion까지인가?
3. I/O 중 reader, writer, 두 번째 flusher, victimizer는 각각 통과하는가?
4. WAL은 어느 시점까지 durable해야 하며 write 실패 시 dirty/LSA 상태는 어떻게 복구되는가?
5. 공개 page latch mode와 buffer-manager 내부 I/O 상태 중 어느 Module이 책임을 갖는가?

## Central Behaviors

`report.json.central_behaviors`와 1:1 대응한다.

1. `snapshot-copy-flush` — 현행 CUBRID가 BCB mutex 아래에서 plain/TDE 출력 이미지를 별도 memory에 만들고,
   `FLUSHING_TO_DISK`와 dirty 상태를 전이한 뒤 mutex를 풀어 WAL을 먼저 flush하고 동기 write하는 흐름.
   live frame writer는 I/O와 겹칠 수 있고, 성공·재더티·write 실패 분기가 이를 안전하게 정리한다.
   Runtime Experiment는 pinned build에서 SQL로 dirty-page/flush 활동을 만들고 flush 관련 statdump invariant와
   cleanup을 관찰한다. 소스만이 snapshot `memcpy`와 실제 overlap 가능성을 직접 증명하며, runtime은 그
   메커니즘이 실행되는 workload라는 사실만 보강한다.
2. `stable-frame-io-contract` — 사본 없이 live frame을 write buffer로 쓸 때 필요한 두 불변식(내용 불변,
   frame 재사용 금지)을 synchronous buffered/direct와 AIO completion lifetime에 맞춰 도출한다. CUBRID의
   strict READ latch도 동기 zero-copy의 내용 불변성은 제공하지만, AIO completion이 thread/fix lifetime을
   넘을 수 있고 single-flusher/victim 금지까지 묶지 못하므로 범용 SX가 유일한 답은 아니다. 전용
   `IO_WRITE_FREEZE`를 BCB에 두는 안, copy-based AIO, 범용 SX, WRITE latch를 비교한다. 같은 Runtime
   Experiment가 현재 CUBRID의 copy-based baseline을 제공하고, 아직 구현되지 않은 대안의 성능·공정성은
   명시적으로 unknown으로 남긴다.

## Coverage Questions

- `orientation`: “flush/AIO에 SX가 왜 필요한가”에 대한 짧은 답, 가장 중요한 정정, pinned revisions와 한계.
- `mental-model`: frame, page image, latch, transaction lock, buffered/direct/async/zero-copy를 한 시나리오로 설명.
- `scope-interface-seams`: caller→page buffer→WAL→DWB/TDE→file I/O seam과 각 Interface 의무.
- `data-ownership-lifetime`: live frame, snapshot/encrypted/DWB image, BCB, I/O request의 owner와 lifetime.
- `lifecycle-state-machines`: dirty→flushing→clean/re-dirty/error와 제안 `IO_WRITE_FREEZE` 상태 전이.
- `core-workflows`: 현행 flush 성공/재더티/실패와 sync/copy-AIO/frame-AIO의 전체 흐름.
- `concurrency`: reader/writer/flusher/victim compatibility, wakeup/fairness, completion-thread ownership.
- `storage-durability-recovery`: WAL-before-data, page LSA snapshot, torn write/DWB, write-error rollback.
- `policies-algorithms`: 사본·READ·SX·전용 freeze·WRITE의 선택표와 권고 조건.
- `errors-resource-pressure`: I/O error, copy allocation/queue pressure, shutdown/cancel, stuck completion.
- `performance-observability`: copy bytes, in-flight pages, writer wait, flush latency/throughput, decision gate.
- `experimental-validation`: 이번 Report Run의 build/runtime identity, SQL workload, statdump 관찰과 한계.
- `postgresql-analysis`: SHARE_EXCLUSIVE의 실제 의미와 CUBRID strict READ와 다른 이유.
- `mysql-analysis`: InnoDB SX/io-fix의 실제 소유권과 completion release.
- `cross-database-comparison`: 같은 책임 축의 equivalent/partial analogy/no equivalent 판정.
- `reimplementation-blueprint`: CUBRID 전용 freeze Interface/상태/순서/오류/관측/테스트 blueprint.
- `glossary-evidence-unknowns`: 용어, Claim 색인, 아직 측정하지 못한 성능·AIO API·DWB/TDE 제한.
- `teaching-map`: central behavior↔chapter anchor↔Claim↔Experiment↔Quiz↔Live Grill 매핑.
