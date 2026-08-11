# CUBRID source-trace packet: flush/AIO frame stability and SX necessity

- Role: CUBRID Source Tracer
- Topic: CUBRID flush와 AIO에서 SX latch가 정말 필요한가 — frame 안정성, READ latch, 사본, 전용 I/O freeze 비교
- Scope digest (SHA-256): `db5ba3f0288fbb966ca5a4a832b420e7b5c582b461dc266ceda80a816c410885`
- CUBRID source root: `/home/vimkim/gh/cb/pgbuf-analysis`
- Revision: `f799e05d77d5300c6ea5753b4a6cc7caee6d8912`
- Source state: provenance가 고정한 dirty baseline. 조사 대상 엔진 파일에는 diff가 없으며 소스는 수정하지 않았다.
- Timestamp: `2026-08-11T13:46:37+09:00`
- Authorized output: 이 파일만 작성했다.

## Executive finding

현재 CUBRID data-page flush에는 SX latch가 필요하지 않다. `pgbuf_bcb_flush_with_wal`은 BCB mutex를 잡은 채 live frame을 stack-local `FILEIO_PAGE`에 복사하거나 TDE 암호문을 별도 buffer에 만들고, DWB를 쓰면 다시 DWB 소유 slot으로 복사한다. 그 뒤 BCB mutex를 풀고 WAL과 blocking write를 수행한다. 따라서 writer는 I/O와 겹칠 수 있고, I/O가 참조하는 바이트는 live frame과 분리되어 있다.

copy-free live-frame write로 바꾸면 필요한 계약은 두 축이다.

1. I/O가 참조하는 page image가 소비 완료까지 바뀌지 않아야 한다(content immutability).
2. 그 주소의 frame이 다른 VPID에 재사용되거나 해제되지 않아야 한다(address/lifetime pin).

현행 `PGBUF_BCB_FLUSHING_TO_DISK_FLAG`는 victim 후보를 무효화하므로 두 번째 축 일부와 single-flusher ordering을 이미 담당하지만 writer를 막지 않아 첫 번째 축은 보장하지 않는다. 반대로 flusher가 소유한 READ fix는 WRITE를 배제하고 fix count로 replacement를 막으므로 **blocking synchronous write의 호출-반환 구간**에는 두 축을 모두 줄 수 있다. 하지만 현행 holder는 thread-owned이고 요청 종료 때 current thread 기준으로 정리되므로, submit thread와 completion thread가 다를 수 있는 true AIO의 request lifetime을 표현하는 소유권 모델은 아니다.

따라서 결론은 다음과 같다.

- synchronous buffered write: 현행 snapshot이면 SX 불필요하다.
- synchronous `O_DIRECT` write: `O_DIRECT` 자체는 async가 아니다. snapshot을 계속 쓰면 SX 불필요하고, live frame을 직접 쓰면 호출 반환까지 READ fix 또는 동등한 writer freeze가 필요하다.
- true AIO live-frame write: completion까지 content와 frame을 pin해야 하지만 SX가 유일한 답은 아니다. request-owned copy, request-owned READ/reference 재설계, SX+async ownership, 전용 `IO_WRITE_FREEZE`가 모두 후보이다.
- TDE page는 암호문 output이 별도로 필요하므로 live-frame direct write가 plain-page copy를 줄이더라도 TDE output buffer lifetime 문제는 사라지지 않는다.

또한 source-confirmed 결함 후보가 하나 있다. `pgbuf_bcb_mark_is_flushing` 뒤 TDE encryption 또는 `dwb_set_data_on_next_slot`이 실패하면 공통 rollback 전에 곧바로 return하여 `FLUSHING`이 남고 기존 `DIRTY`가 지워진 채 flush waiter도 깨우지 않는다.

## Examined files and symbols

| File | SHA-256 | Examined symbols / regions |
|---|---|---|
| `src/storage/page_buffer.h` | `2f052cd4be1df289692990973dcb30f332bd75f5b135ea367a5960e866c9b197` | `PGBUF_LATCH_MODE`, `PGBUF_LATCH_FLUSH` |
| `src/storage/page_buffer.c` | `d1e71931b2a2da569f7e96c8a35eab85ec5bf0b4dac5fa0c3d0ac69adf03c163` | BCB flags/structs, pool allocation/finalize, fix/unfix/holder, lock-free READ, safe flush, checkpoint/victim/neighbor callers, flush funnel, state helpers, post-flush, observability |
| `src/storage/file_io.c` | `3d4f38846aaf9e5f4dc0e753cb95946329429087775dbae3a6ce7c08eb101762` | `fileio_open`, create/mount flags, HPUX positioned-I/O fallback, `fileio_os_write`, `fileio_write`, `fileio_write_pages`, `fileio_synchronize_all` |
| `src/storage/tde.c` | `a013f0133ded67a65fa12f81d602e7de4a9284188aa149711e76fc6c796ed2cc` | `tde_encrypt_data_page` |
| `src/storage/tde.h` | `88c9d536a7a6c6058c6fa6641b5512c96e43346775454b4b321e9e47cffe6db4` | TDE page encryption interface |
| `src/storage/double_write_buffer.hpp` | `b66c18b51bf1776c38ebbfcab6924d8a59d50905b6bd4956358644ee7128f1f3` | `DWB_SLOT`, public DWB interface |
| `src/storage/double_write_buffer.cpp` | `32ae9d886d6ef5d2f3c1b280980eab25172fb74e9bc3e2178153f9122d6b365a` | block/slot ownership, slot acquisition/copy, enqueue, block/home writes, force flush, destroy |
| `src/transaction/log_page_buffer.c` | `98dbfb055d2370ab7a98334de328bebc46c1828c0e04e2ea80a7d14e8472ef9c` | `logpb_flush_log_for_wal`, `logpb_need_wal` |
| `src/transaction/log_manager.c` | `73969c9343765e8affdd44ae7b312aac5243365418df08592be90c3325761975` | `log_final` |
| `src/transaction/boot_sr.c` | `01c1189c162d2d6b6a41dac4d9a52e0cab169c5fd1e6ae2cd003bb5f90343651` | normal shutdown and restart-error teardown |
| `src/base/perf_monitor.c` | `3c23ce773eb1694796ff004af13a0bc3512386ca464f00e91b6f47ed3b4a66a0` | flush/DWB/promote metadata, diff/calc/dump math |
| `src/base/perf_monitor.h` | `fce3513a8e14508e0e667c23d6ce2df50dcbafd38e14e7f270873736212caa59` | statistics IDs/value types |

Local context read before source:

- `/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27193-page-buffer-improvement-roadmap_5cd4f86_codex.md`
- `/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27196-pgbuf-sx-latch-survey_5cd4f86_claude.md`
- prior packet `/home/vimkim/gh/my-cubrid-docs/code-analysis/cbrd-27196-sx-page-latch-aio-direct-i-o-cubrid/f799e05_claude/research/packets/cubrid.md`
- prior audit `/home/vimkim/gh/my-cubrid-docs/code-analysis/cbrd-27196-sx-page-latch-aio-direct-i-o-cubrid/f799e05_claude/evidence/report-audit.md`

## Structured claim candidates

### CUBRID-FLUSH-001

- Korean statement: 현행 data-page flush는 BCB mutex 아래에서 page image를 stack-local aligned buffer로 복사하거나 TDE 암호문을 별도 buffer에 생성한 뒤 mutex를 풀고 WAL/write를 수행한다. I/O는 live frame을 직접 참조하지 않는다.
- Kind: source fact
- Confidence: high
- Source refs: `src/storage/page_buffer.c:10733-10857`, symbol `pgbuf_bcb_flush_with_wal`, revision `f799e05d77d5`, file SHA `d1e71931...`
- Evidence state: verified-source
- Notes: plain page는 `memcpy(..., IO_PAGESIZE)`이고 TDE page는 `tde_encrypt_data_page(plain, ..., iopage)`이다. copy 뒤 `PGBUF_BCB_UNLOCK`이 WAL과 `fileio_write`보다 먼저 실행된다.

### CUBRID-FLUSH-002

- Korean statement: 현행 `FLUSHING_TO_DISK`는 snapshot의 세대를 표시하고 BCB victim/reuse 및 동시 두 번째 flush를 막지만, page content를 freeze하지는 않는다. flush 시작 때 DIRTY를 지우는 이유 자체가 I/O 중 concurrent writer의 재-dirty를 새 세대로 추적하기 위해서다.
- Kind: source fact
- Confidence: high
- Source refs: `src/storage/page_buffer.c:222-262` (flags/victim mask), `8810-8885` (single flusher), `16077-16125` (state helpers), revision/file SHA same as above
- Evidence state: verified-source
- Notes: `pgbuf_bcb_safe_flush_internal`은 이미 flushing이면 두 번째 flush를 막는다. 주석은 old image가 newer image 뒤에 기록될 위험을 명시한다. `FLUSHING`은 invalid-victim mask에 들어가지만 latch mode와 별도 flag이다.

### CUBRID-FLUSH-003

- Korean statement: snapshot flush가 성공하는 동안 writer가 page를 수정하면 DIRTY/새 `oldest_unflush_lsa`가 다시 설정되고, 성공 cleanup은 FLUSHING만 지우므로 새 dirty 세대가 보존된다. checkpoint는 필요한 경우 같은 BCB를 다시 flush한다.
- Kind: source fact
- Confidence: high
- Source refs: `src/storage/page_buffer.c:10836-10952`, `16077-16125`, `4982-5081` (`pgbuf_set_lsa`), `4536-4563` (checkpoint flush-again), revision/file SHA `d1e71931...`
- Evidence state: verified-source
- Notes: success path의 `pgbuf_bcb_mark_was_flushed`는 `PGBUF_BCB_FLUSHING_TO_DISK_FLAG`만 clear한다. checkpoint 주석도 “already flushing → modified again → conservative flush again”을 별도로 처리한다.

### CUBRID-FLUSH-004

- Korean statement: common write/DWB-add 실패는 BCB를 다시 잠가 FLUSHING을 지우고, 원래 dirty였으면 DIRTY를 복원하며, 저장한 `oldest_unflush_lsa`를 복구하고 flush waiter를 깨운다.
- Kind: source fact
- Confidence: high
- Source refs: `src/storage/page_buffer.c:10886-10923`, `16084-16125`, revision/file SHA `d1e71931...`
- Evidence state: verified-source
- Notes: 실패 중 concurrent re-dirty가 있었다면 masked flag update 때문에 DIRTY는 유지된다. old oldest LSA 복원은 더 오래된 LSA를 복구하는 보수적 방향이다.

### CUBRID-FLUSH-005

- Korean statement: TDE encryption 실패와 `dwb_set_data_on_next_slot` 실패는 현재 공통 rollback을 우회한다. 둘 다 `mark_is_flushing` 이후 즉시 return하므로 FLUSHING이 남고 원래 DIRTY는 clear된 상태가 되며 waiter wakeup도 실행되지 않는다.
- Kind: defect candidate / source fact
- Confidence: high
- Source refs: `src/storage/page_buffer.c:10801-10828` versus cleanup `10908-10923`, helper semantics `16084-16125`; TDE failure source `src/storage/tde.c:921-925`
- Evidence state: verified-source, runtime reproduction pending
- Notes: `oldest_unflush_lsa`를 NULL로 만드는 지점(`10836-10839`) 전이라 LSA 자체는 BCB에 남는다. 그러나 dirty generation state와 flush waiters는 손상된다. 이 패킷은 진단만 하며 소스는 수정하지 않았다.

### CUBRID-FLUSH-006

- Korean statement: exact revision의 일반 data-volume write는 blocking `write`/`pwrite`이다. volume create/mount flags에는 `O_DIRECT`가 없고 true asynchronous page-write submit/completion 경로도 없다. HPUX fallback의 `aio_write`는 즉시 `aio_suspend`/`aio_return`으로 완료를 기다려 API 의미가 synchronous이다.
- Kind: source fact + negative search
- Confidence: high
- Source refs: `src/storage/file_io.c:1935-1954`, `2088-2152`, `2923-3005`, `3731-3812`, `4063-4205`, `4286-4373`, revision `f799e05d77d5`, SHA `3d4f3884...`
- Evidence state: verified-source and repo-wide negative search
- Notes: `src/**/*.{c,h,cpp,hpp}`에서 `O_DIRECT|io_uring|libaio|aio_write|aio_read|aio_suspend|aio_return`을 검색했으며 HPUX positioned-I/O fallback만 검출되었다.

### CUBRID-FLUSH-007

- Korean statement: flusher가 READ fix를 소유한 채 blocking live-frame write를 호출하고 반환 후 unfix한다면, 현행 계약상 READ latch는 WRITE를 배제해 content를 고정하고 fix count는 replacement를 막는다. 이 경우 SX는 correctness의 필수 조건이 아니다.
- Kind: design inference grounded in source
- Confidence: high for synchronous call interval
- Source refs: `src/storage/page_buffer.c:6298-6537` (READ compatibility/WRITE exclusion), `3062-3203` (unfix/replacement), `9255-9312` (fixed BCB not victimizable), `11656-11675` (dirty requires WRITE holder), `src/storage/page_buffer.h:189-203`
- Evidence state: source-grounded inference; no prototype
- Notes: 이 결론은 “모든 page mutation이 WRITE latch 계약을 지킨다”는 page-buffer API invariant를 전제로 한다. 현행 flush는 READ fix를 새로 얻지 않으며 snapshot을 이용해 writer overlap을 의도한다.

### CUBRID-FLUSH-008

- Korean statement: 현행 READ fix holder는 thread-owned이므로 true AIO request의 ownership으로 그대로 넘길 수 없다. holder는 submit thread의 anchor에 연결되고 unfix는 current thread holder를 찾으며 request 종료의 `pgbuf_unfix_all`도 current thread 목록을 정리한다.
- Kind: source fact + design inference
- Confidence: high
- Source refs: `src/storage/page_buffer.c:460-488`, `6000-6086`, `6090-6184`, `3062-3203`, `3277-3349`, `7725-7829`, revision/file SHA `d1e71931...`
- Evidence state: verified-source for ownership; source-grounded inference for AIO consequence
- Notes: completion이 다른 worker에서 일어나면 그 worker가 submitter의 holder를 정상 `pgbuf_unfix`할 수 없다. 같은 submit thread에서만 completion 처리하더라도 cancellation, timeout, request teardown, shutdown에서 정확히 한 번 release하는 lifecycle이 추가로 필요하다.

### CUBRID-FLUSH-009

- Korean statement: true AIO live-frame write에 필요한 것은 “SX라는 이름”이 아니라 completion까지 유지되는 writer exclusion + frame pin + one-completion cleanup이다. 전용 request-owned `IO_WRITE_FREEZE`는 이 계약을 latch holder와 분리해 표현할 수 있고, 기존 FLUSHING과 결합하면 single-flusher/order/victim 보호를 재사용할 수 있다.
- Kind: design inference / recommendation candidate
- Confidence: medium-high
- Source refs: existing state split at `src/storage/page_buffer.c:499-543`, flags `222-262`, safe flush `8810-8902`, state cleanup `10908-10952`, holder ownership `6000-6184`
- Evidence state: proposed design, not implemented
- Notes: 최소 상태 예시는 `{VPID/generation, refcount 또는 request pointer, IO_WRITE_FREEZE, FLUSHING, completion result}`이다. completion은 success/failed/cancelled 모두에서 freeze와 FLUSHING을 clear하고 waiter를 깨워야 한다. shutdown은 모든 request drain 후 page pool free를 보장해야 한다.

### CUBRID-FLUSH-010

- Korean statement: DWB-enabled flush가 page-buffer call보다 늦게 home volume에 기록될 수 있어도 live frame lifetime은 필요하지 않다. page snapshot을 DWB block-owned heap buffer의 slot로 복사한 뒤 daemon이 그 소유 buffer를 write한다.
- Kind: source fact
- Confidence: high
- Source refs: `src/storage/double_write_buffer.cpp:214-232`, `1000-1151`, `2469-2634`, `2677-2829`, `1995-2179`, `2182-2457`; `src/storage/page_buffer.c:10822-10885`
- Evidence state: verified-source
- Notes: `dwb_set_slot_data`가 `IO_PAGESIZE`를 `dwb_slot->io_page`로 memcpy한다. block buffer는 DWB create에서 heap allocation되고 block finalize에서 해제된다. page-buffer stack snapshot은 `dwb_add_page` 반환 뒤 살아 있을 필요가 없다.

### CUBRID-FLUSH-011

- Korean statement: TDE page의 disk image는 plain live frame과 동일하지 않다. 암호화 함수가 caller-provided cipher page에 header/watermark를 복사하고 encrypted payload를 출력하므로, copy-free plain-frame write를 도입해도 TDE는 별도 output buffer와 그 I/O lifetime을 필요로 한다.
- Kind: source fact + design consequence
- Confidence: high
- Source refs: `src/storage/tde.c:902-954`, `src/storage/page_buffer.c:10805-10820`, revision `f799e05d77d5`, SHAs `a013f013...`, `d1e71931...`
- Evidence state: verified-source
- Notes: AIO TDE라면 stack-local `page_buf`는 submit 반환 후 사용할 수 없으므로 request-owned cipher buffer나 DWB-owned copy가 필요하다.

### CUBRID-FLUSH-012

- Korean statement: WAL은 snapshot page LSA를 기준으로 data/DWB write보다 앞서 강제된다. DWB block flush도 debug build에서 각 page LSA가 WAL을 더 요구하지 않는지 검증한다.
- Kind: source fact
- Confidence: high
- Source refs: `src/storage/page_buffer.c:10836-10857`; `src/transaction/log_page_buffer.c:4151-4189`, `11252-11267`; `src/storage/double_write_buffer.cpp:2256-2264`
- Evidence state: verified-source
- Notes: future AIO submit은 WAL durability가 만족된 뒤 허용하거나 dependency를 명시적으로 걸어야 한다. completion 순서만으로 WAL을 대신할 수 없다.

### CUBRID-FLUSH-013

- Korean statement: 정상 shutdown은 page-buffer daemons를 먼저 중지하고 `log_final`에서 log flush → all dirty pages flush → `fileio_synchronize_all`의 DWB force/drain을 수행한 뒤 DWB를 destroy한다. page pool finalize는 자체적으로 outstanding I/O를 기다리는 기능이 없다.
- Kind: source fact + AIO design consequence
- Confidence: high
- Source refs: `src/transaction/boot_sr.c:3055-3132`; `src/transaction/log_manager.c:1742-1855`; `src/storage/file_io.c:4621-4664`; `src/storage/double_write_buffer.cpp:3516-3767`, `3405-3441`; `src/storage/page_buffer.c:1921-1971`, `17146-17255`
- Evidence state: verified-source
- Notes: true AIO를 추가하면 normal shutdown뿐 아니라 restart-error teardown(`boot_sr.c:2767-2794`)에서 submit 차단, cancel/drain, completion quiescence를 page pool free보다 앞에 두는 명시적 contract가 필요하다.

### CUBRID-FLUSH-014

- Korean statement: 기존 flush 관측값은 logical page write/skip/wait/DWB duration을 볼 수 있지만 copy bytes/time, live-frame freeze wait, in-flight AIO request 수/bytes/age, completion latency, cancellation/error cleanup을 직접 관측하지 못한다.
- Kind: source fact + observability gap
- Confidence: high
- Source refs: `src/base/perf_monitor.c:212`, `479-544`, `550-559`; `src/storage/page_buffer.c:10859-10906`, `10954-10959`, `17330-17562`
- Evidence state: verified-source plus named-counter negative search
- Notes: SystemTap `CUBRID_IO_WRITE_START/END`, `Num_data_page_iowrites`, `Num_data_page_writes`, flush timers, DWB timers는 존재한다. 제안 실험에는 copy/freeze/AIO lifecycle counter를 임시 계측해야 한다.

### CUBRID-FLUSH-015

- Korean statement: 이전 보고서가 `Data_page_total_promote_success=89,587`을 실제 promotion count로 읽고 20,000 insert당 약 4.4회라고 계산한 것은 이 revision의 perfmon 산식 버그에 오염된 값이다. 같은 stdout의 raw `Num_data_page_promote_ext` 합은 887이며 summary 89,587은 약 `887 × 101`이다.
- Kind: correction / source fact + recorded runtime artifact
- Confidence: high
- Source refs: `src/base/perf_monitor.c:436-448`, `1393-1447`, `1788-1971`, `1666-1723`; prior artifact `f799e05_claude/evidence/runs/exp1-obs-1/stdout.txt:444-445,677-679`
- Evidence state: source + pre-existing runtime artifact, arithmetic reproduced
- Notes: `PSTAT_PB_PAGE_PROMOTE_SUCCESS`가 `COMPUTED_RATIO`인데 diff 단계가 기존 computed slot도 먼저 복사하고(`1421-1432`) `perfmon_server_calc_stats`가 raw complex counter를 다시 더한 뒤 `*=100`한다(`1951-1971`). dump는 `/100`한다(`1720-1723`). artifact는 summary `89587.00`, raw complex `887`; exp1 obs-2/3도 summary `88779.00`, raw `879`로 동일한 `×101` 패턴이다. 따라서 이전 B-tree 성능 결론에는 이 수치를 재사용하면 안 된다.

## Current flush call paths

### 1. Explicit page/all flush

```text
pgbuf_flush / pgbuf_flush_with_wal                       page_buffer.c:3600-3617
  -> pgbuf_bcb_safe_flush_force_unlock
     -> pgbuf_bcb_safe_flush_internal                    :8810-8902
        -> pgbuf_bcb_flush_with_wal                      :10724-10962

pgbuf_flush_all / pgbuf_flush_all_unfixed
  -> pgbuf_flush_all_helper                              :3662-3702
     -> pgbuf_bcb_safe_flush_force_unlock
        -> pgbuf_bcb_safe_flush_internal
           -> pgbuf_bcb_flush_with_wal
```

Safe flush가 WRITE-latched page를 만났을 때는 `PGBUF_BCB_ASYNC_FLUSH_REQ`를 세우고, synchronous caller는 pseudo-mode `PGBUF_LATCH_FLUSH`로 wait한다. 이것은 fix 가능한 content latch가 아니라 block/wakeup mode이다 (`page_buffer.h:189-197`, `page_buffer.c:8839-8897`). WRITE holder의 `pgbuf_flush_if_requested` 또는 unfix 경로가 요청을 실제 flush로 바꾼다 (`page_buffer.c:3621-3657`, `6860-6875`). 이름에 “ASYNC”가 있어도 OS AIO가 아니라 deferred flush request다.

### 2. Victim flush and neighbor batching

```text
pgbuf_flush_victim_candidates                            :3869-4120
  -> (neighbor enabled) pgbuf_flush_page_and_neighbors_fb:11804-12100
       -> pgbuf_flush_neighbor_safe                      :12134-12184
          -> pgbuf_bcb_flush_with_wal
  -> (neighbor disabled) pgbuf_bcb_flush_with_wal        :4088
```

Victim path는 VPID, DIRTY, not-FLUSHING, victim zone, unfixed 상태를 재확인하고 WAL이 부족하면 먼저 log flush를 유도한다 (`4043-4089`). Neighbor safe는 VPID가 그대로이고 latch가 NO/READ이며 not-FLUSHING일 때만 core funnel을 호출한다 (`12156-12170`).

### 3. Checkpoint

```text
pgbuf_flush_checkpoint                                   :4173-4315
  -> pgbuf_flush_chkpt_seq_list                          :4326-4412
     -> pgbuf_flush_seq_list                             :4415-4625+
        -> pgbuf_bcb_safe_flush_force_lock
           -> pgbuf_bcb_safe_flush_internal
              -> pgbuf_bcb_flush_with_wal
        -> if re-dirtied under checkpoint horizon:
           pgbuf_bcb_safe_flush_internal again           :4536-4563
```

Checkpoint는 시작 시 `flush_upto_lsa`까지 log를 force하고, BCB별 flush core도 자기 snapshot LSA에 대해 WAL을 확인한다. concurrent re-dirty의 oldest LSA가 여전히 checkpoint horizon 이하면 보수적으로 두 번째 flush를 수행한다.

### 4. Normal shutdown and DWB drain

```text
xboot_shutdown_server                                    boot_sr.c:3055-3132
  -> pgbuf_daemons_destroy
  -> log_final                                           log_manager.c:1742-1855
     -> logpb_flush_pages_direct
     -> pgbuf_flush_all
     -> fileio_synchronize_all                           file_io.c:4621-4664
        -> dwb_flush_force
  -> dwb_destroy
```

## Memory ownership and lifetime

| Object/address | Owner | Created/linked | Required lifetime | Released/reused |
|---|---|---|---|---|
| live page frame `bufptr->iopage_buffer->iopage` | page buffer pool | BCB/iopage tables allocated for whole pool and one-to-one linked at `page_buffer.c:5558-5667` | while resident; reuse prohibited by fix/victim state | pool finalize frees table at `1921-1971`; victim may reassign BCB after eligibility |
| BCB/fix holder | current thread holder anchor | `6000-6086`; holder links BCB and thread | until same thread decrements all fixes | `6090-6184`, `3062-3203`; request termination audits current thread at `3277-3349` |
| flush stack snapshot `page_buf` | `pgbuf_bcb_flush_with_wal` stack | `10735`, aligned at `10806`, filled `10805-10820` | through blocking `fileio_write` or until copied into DWB slot | function return |
| TDE cipher image | same stack snapshot in current path | `tde_encrypt_data_page` output | through blocking write/DWB copy | function return; future AIO requires request-owned output |
| DWB block `write_buffer` / slot image | DWB global blocks | heap allocation/link at `double_write_buffer.cpp:1000-1091`; copy at `2603-2634` | through DWB file write, home writes and block sync | block count reset/version advance `2412-2441`; allocation freed in block finalize `1125-1151` |
| hypothetical AIO live-frame request | absent | absent | submit through completion/cancel | must be designed before AIO/live-frame integration |

## BCB/latch state analysis

### Current snapshot state machine

```text
resident dirty
  flags: DIRTY, !FLUSHING
  latch: NO / READ / caller-owned WRITE allowed
            |
            | BCB mutex; mark_is_flushing
            v
snapshot generation in flight
  flags: !old-DIRTY, FLUSHING
  image: stack copy or DWB-owned copy
  live frame: writers may acquire WRITE after BCB unlock
            |
     +------+--------------------------+
     | concurrent writer               | no writer
     | sets DIRTY + new oldest LSA      |
     v                                  v
  DIRTY + FLUSHING                  !DIRTY + FLUSHING
     |                                  |
     +---------------+------------------+
                     |
            completion success
                     v
              clear FLUSHING only
          DIRTY survives iff re-dirtied

completion failure after common I/O path:
  clear FLUSHING; restore original DIRTY if needed;
  restore old oldest_unflush_lsa; wake flush waiters
```

`FLUSHING`은 다음 두 역할을 한다.

- invalid victim candidate mask에 들어가 frame/BCB reuse를 막는다 (`page_buffer.c:253-262`, `9255-9312`).
- second flusher가 old snapshot을 newer snapshot 뒤에 write하지 못하도록 serializes flush generations (`8839-8847`).

하지만 writer exclusion은 latch가 담당하므로 `FLUSHING`만으로 live-frame I/O의 content immutability는 얻지 못한다. 현재는 이것이 결함이 아니라 snapshot overlap 설계의 핵심이다 (`16077-16079`).

### What a READ latch does and does not guarantee

| Question | READ fix held by flusher | Evidence/qualification |
|---|---|---|
| Other readers may proceed? | Yes | READ+READ increments aggregate fcnt when no waiter; `6376-6399`, lock-free path `7740-7750` |
| Writer may modify page? | No, until READ release | WRITE request is incompatible unless caller is sole current holder/promotes; dirty operation asserts WRITE holder `11656-11675` |
| Frame may be victimized/reused? | No, while fcnt > 0 | `9255-9312`; unfix note `3062-3068` |
| Prevent a second flusher? | Not by READ alone | multiple readers are compatible; current `FLUSHING` check provides single-flusher rule `8839-8865` |
| Mark which dirty generation completed? | No | DIRTY/FLUSHING/oldest LSA state machine still needed |
| Synchronous buffered/direct live-frame write safe? | Yes, if flusher owns READ continuously through blocking return and cleanup is correct | source-grounded inference |
| True AIO safe after submit thread releases READ? | No | kernel/request may still reference frame until completion |
| Can another completion worker simply unfix submitter's READ? | No under current holder ownership | holder lookup/removal is current-thread anchored `6000-6184` |
| Does READ make TDE plain frame itself writable as disk cipher image? | No | TDE emits distinct cipher output `tde.c:902-954` |

### Why synchronous `O_DIRECT` and AIO must not be conflated

For a blocking `pwrite`, the caller's buffer-use interval ends when the syscall returns, whether the file descriptor is buffered or `O_DIRECT`. `O_DIRECT` changes cache/alignment/transfer constraints; it does not by itself make the call asynchronous. Therefore:

- snapshot + blocking `O_DIRECT`: keep aligned snapshot valid through return; no live-frame latch required.
- live frame + blocking `O_DIRECT`: keep READ/freeze through return; no post-return frame pin is required by that I/O.
- AIO submit: submit return is not completion. buffer content/address must stay valid until completion/cancel has been reaped.

The first two are design conclusions about a future configuration because this revision does not open data volumes with `O_DIRECT` (`file_io.c:2088-2152`, `2923-3005`).

## Protection strategy comparison

| Strategy | Writer overlap | Reader overlap | Output/address lifetime | Single flusher/order | AIO suitability | Main cost/risk |
|---|---:|---:|---|---|---|---|
| Current stack snapshot | Yes | Yes | stack valid through blocking call; DWB copies again | existing FLUSHING | Not as-is: async needs heap/request-owned snapshot | `IO_PAGESIZE` copy per plain flush; TDE transform already required |
| Request-owned copy AIO | Yes | Yes | request owns copy until completion | existing FLUSHING plus request completion | Strong/simple | memory bandwidth + in-flight memory pressure |
| Live frame + READ fix, synchronous | No writers until return | Yes | fcnt pins frame through return | must retain existing FLUSHING | Strong for blocking I/O | write latency becomes writer stall; thread holder acquisition/release |
| Live frame + current READ holder across AIO | No writers until completion | Yes | conceptually sufficient, operationally thread-affine | retain FLUSHING | Weak without ownership redesign | cross-thread unfix, cancellation, shutdown, leaked holder |
| Live frame + SX | No writers; readers compatible, assuming intended matrix | Yes | SX alone does not prove frame lifetime unless it carries/refers to a fix; completion ownership still needed | an exclusive SX owner may help, but FLUSHING generation state remains needed | Viable only with request lifecycle design | new public/internal latch semantics, owner/count/wakeup complexity, writer stalls |
| Live frame + dedicated `IO_WRITE_FREEZE` | No writers while request active | Yes by policy | request ref explicitly pins frame/VPID generation | combine with FLUSHING or fold generation state into request | Best semantic fit for internal AIO | new state transition integration with fix/promote/wakeup/victim/shutdown |
| DWB-owned copy | Yes | Yes | DWB block heap owns image until home write/sync | DWB block ordering + pgbuf FLUSHING | Already supports deferred daemon write safely | second copy and DWB memory/I/O |

The table's central distinction is that SX can combine “readers allowed, writers excluded, one special owner,” but **it does not automatically solve asynchronous ownership, cancellation, buffer pool teardown, WAL dependency or TDE output lifetime**. Those are separate state-machine obligations.

## WAL, DWB, TDE, and shutdown invariants for a future AIO path

1. Snapshot generation: capture page LSA and `oldest_unflush_lsa` consistently with output bytes. Current code does this under BCB mutex before unlock (`page_buffer.c:10801-10842`).
2. WAL: do not submit home-page write before `logpb_flush_log_for_wal(snapshot_lsa)` is satisfied (`10844-10849`, `log_page_buffer.c:4162-4179`).
3. DWB: if durability design retains DWB, the stable async source should normally be DWB-owned slot/block memory, not the page frame. DWB must still write+sync its file before home location (`double_write_buffer.cpp:2328-2357`).
4. TDE: allocate request-owned cipher output or copy it into DWB before submit; never submit current stack buffer and return.
5. Completion success: atomically associate result with the same `{VPID, flush generation}`; clear freeze and FLUSHING without clearing a concurrent DIRTY generation; wake waiters.
6. Completion failure/cancel: restore dirty eligibility/oldest LSA conservatively, clear freeze/FLUSHING, wake waiters, retain retriable data.
7. Shutdown: stop submitters, flush or cancel and reap all requests, drain DWB, then free BCB/iopage/DWB buffers. `pgbuf_finalize` itself only frees pool storage and is not an AIO barrier (`page_buffer.c:1921-1971`).

## Error and pressure paths

| Path | Current behavior | AIO/freeze implication |
|---|---|---|
| Normal direct write success | blocking call returns, clear FLUSHING; possible re-DIRTY survives | completion callback must do equivalent masked transition |
| DWB slot accepted | page-buffer flush may return before home write; DWB owns bytes | this is a working example of decoupling schedule lifetime from live frame |
| Concurrent re-dirty | writer sets new DIRTY/oldest LSA while old snapshot writes | live-frame freeze would eliminate this overlap during I/O and change checkpoint/write latency behavior |
| Common write/DWB-add error | restore dirty/oldest, clear FLUSHING, wake waiters | request must preserve same rollback on every terminal result |
| TDE encryption error | early return leaks FLUSHING/clears old DIRTY | fix before relying on state machine for new I/O modes |
| Early DWB slot error | same early-return leak | same |
| Writer already owns page | flusher sets deferred ASYNC_FLUSH_REQ; sync caller waits with pseudo FLUSH mode | freeze acquisition must avoid waiting while holding incompatible per-page state |
| Flush already active | second flusher waits/returns to avoid old-over-new disk order | one in-flight generation per BCB remains simplest contract |
| Checkpoint sees re-dirty below horizon | flushes again | live-frame freeze may reduce repeat flush but increase foreground writer wait |
| Shutdown/error teardown | daemons stopped, sync flush/drain, then buffers freed | AIO adds submit-stop/drain/cancel/reap gate before memory teardown |

## Observability inventory and missing measurements

Existing useful signals:

- `Num_data_page_iowrites` (`PSTAT_PB_NUM_IOWRITES`) at `perf_monitor.c:212`.
- `Num_data_page_writes`, flush collect/flush/sleep timers, skip causes, post-flush count and wake-flush-waiter timer at `perf_monitor.c:479-493`.
- DWB flush/sort/decache/wait/force timers at `perf_monitor.c:537-544`.
- `show_status->num_pages_written` and flusher waiting thread count in `page_buffer.c:398-421`, updated at `10888`, aggregated at `17437-17555`.
- SystemTap `CUBRID_IO_WRITE_START/END` around the flush funnel at `page_buffer.c:10859-10906`.
- WAL count via `PSTAT_LOG_NUM_WALS` at `log_page_buffer.c:4164-4167`.

Missing for a meaningful snapshot-vs-freeze/AIO experiment:

- page-copy calls, bytes and CPU time split by plain/TDE/DWB;
- writer wait count/time attributable specifically to flush READ/SX/freeze;
- in-flight request count/bytes, high-water mark and age;
- submit-to-completion latency histogram and queue depth;
- completion outcome: success, partial/error, cancelled, shutdown-drained;
- re-dirty-during-flush count and checkpoint reflush count;
- freeze acquisition collision/single-flusher collision;
- request-owned buffer allocation failure and fallback-to-copy/fallback-to-sync count.

## Contradictions and corrections

### 1. “AIO/direct I/O이면 SX가 필수” is too strong and joins unlike mechanisms

Prior report statement:

- `f799e05_claude/index.html:16`: “AIO/direct I/O write ⇒ frame 안정성(SX 등가 또는 상시 사본) 필수”, 이어서 “AIO 도입 시 SX 필수? 그렇다.”

Correction:

- stable I/O memory is required, not SX specifically.
- blocking direct I/O only extends the buffer-use interval through syscall return, like blocking buffered I/O; snapshot remains sufficient.
- true AIO extends it through completion, but a request-owned copy is sufficient and preserves writer overlap.
- live-frame AIO needs a writer freeze plus address pin, yet current thread-owned READ, a redesigned request-owned read reference, SX+request lifecycle, or dedicated `IO_WRITE_FREEZE` can each implement that contract.
- exact CUBRID revision uses neither `O_DIRECT` nor true async page write, so the report must label all such paths as future designs.

### 2. “89,587 promotions / 20,000 inserts ≈ 4.4 per insert” is a perfmon summary artifact

Prior report locations include:

- `f799e05_claude/index.html:16`
- `f799e05_claude/chapters/05-core-workflows.html:63`
- `f799e05_claude/quiz/quiz-1/answer.md:5`

Source and artifact reconciliation:

```text
exp1-obs-1 summary: Data_page_total_promote_success = 89587.00
exp1-obs-1 raw:     Num_data_page_promote_ext ... SUCCESS = 887

exp1-obs-2/3 summary: 88779.00
exp1-obs-2/3 raw:      879
```

The repeated identity is:

```text
89587 = 887 * 101
88779 = 879 * 101
```

Explanation at source level:

1. promote summary slots are declared `PSTAT_COMPUTED_RATIO_VALUE` (`perf_monitor.c:446-448`).
2. `perfmon_calc_diff_stats` copies/differences those already computed slots along with raw complex counters (`1414-1432`).
3. `perfmon_server_calc_stats` then adds raw promote counters into the non-zero summary slot and multiplies it by 100 (`1932-1971`).
4. dump divides computed values by 100 (`1700-1723`).

Thus the summary double-computation turns a raw delta `N` into `101N` in this observation path. The source-trace-supported count in the recorded artifact is 887/879, not 89,587/88,779. Even the corrected raw count is page-buffer-wide (`PAGE_UNKNOWN`, module aggregation), not proof that every event came from B-tree insert. The old performance conclusion and per-insert ratio must not be reused.

## Negative searches

All searches used the pinned CUBRID root and did not mutate it.

| Search | Scope | Result |
|---|---|---|
| `rg '\b(O_DIRECT|io_uring|libaio|aio_write|aio_read|aio_suspend|aio_return)\b'` | `src/**/*.{c,h,cpp,hpp}` | only HPUX `pread`/`pwrite` fallback uses `aio_*`, and it immediately waits with `aio_suspend` then reaps with `aio_return`; no `O_DIRECT`, io_uring, or libaio path |
| data-volume open flags | `src/storage/file_io.c` create/mount paths | `O_RDWR`, optional `O_CREAT`/`O_SYNC`; no `O_DIRECT` |
| `pgbuf_bcb_flush_with_wal` callers | `src/storage/page_buffer.c` | victim direct call, safe-flush funnel, neighbor safe; checkpoint reaches it through safe-flush |
| public fix latch modes | `src/storage/page_buffer.h`, `page_buffer.c` | READ/WRITE only; FLUSH is pseudo block mode; no SX/IO freeze mode |
| AIO request/completion ownership in page buffer | page buffer/file I/O/DWB symbols and async terms | no page-write submit/completion object; `ASYNC_FLUSH_REQ` is deferred request flag, not OS AIO |
| copy/freeze/AIO lifecycle counters | `src/base/perf_monitor.*`, `page_buffer.c` | no counters for copy bytes/time, IO-freeze writer wait, in-flight AIO depth/bytes, completion/cancel outcome |

## Unknowns and boundaries

1. No prototype or runtime mutation was authorized. READ-held live-frame sync correctness is source-grounded but not fault-injection-tested.
2. The exact intended SX compatibility/ownership model is not implemented at this revision. Any statement that SX is compatible with READ but excludes WRITE is a proposed contract, not current CUBRID behavior.
3. No OS-specific direct-I/O alignment or filesystem behavior was tested. The source revision does not open data volumes with `O_DIRECT`.
4. It remains a policy decision whether future async durability completion means kernel write completion, DWB durability, home-volume sync, or a higher-level checkpoint guarantee. The page state must name this boundary.
5. TDE and DWB early-return state leaks are source-confirmed control-flow findings, but reachability/frequency of `dwb_set_data_on_next_slot` hard errors was not quantified.
6. Error-path teardown order outside normal shutdown needs a full system lifecycle review before adding AIO. `boot_sr.c:2767-2794` stops page/DWB daemons before `log_final`, but no outstanding kernel AIO exists today.
7. READ latches normally imply thread holders and debug tracking. A request-owned pin could reuse lower-level fcnt only if it does not violate holder/debug/statistics invariants; no safe hidden increment API exists today.
8. Current BCB `FLUSHING` protects against victimization but a future completion must also validate VPID/generation to defend against lifecycle bugs rather than rely solely on “should never be reused.”

## Suggested runtime experiments

### EXP-CUBRID-FLUSH-01: prove current snapshot overlap and re-dirty preservation

- Add test-only barriers immediately after snapshot/BCB unlock and before `fileio_write`.
- Thread A starts flush; thread B acquires WRITE, mutates page, advances LSA, marks dirty while A is paused.
- Resume A and assert:
  - written image equals pre-B snapshot;
  - BCB remains DIRTY after A success;
  - `oldest_unflush_lsa` belongs to B's generation;
  - a second flush writes B's image.
- Run with DWB off/on and TDE off/on.

### EXP-CUBRID-FLUSH-02: reproduce early TDE/DWB failure cleanup defect

- Inject deterministic failure from `tde_encrypt_data_page` and separately `dwb_set_data_on_next_slot` after `mark_is_flushing`.
- Observe BCB flags, oldest LSA, waiter list and victim eligibility after return.
- Expected from present source: FLUSHING remains set, original DIRTY is clear, waiter is not woken.
- This should be a targeted test before any latch/AIO redesign, because new paths would amplify stuck state.

### EXP-CUBRID-FLUSH-03: snapshot versus READ-held synchronous live-frame write

- Prototype test-only modes:
  1. current snapshot;
  2. flusher-owned READ fix held through existing blocking `fileio_write`.
- Workloads: read-heavy, update-hot-page, checkpoint pressure, victim pressure; DWB off initially, then on.
- Measure copy cycles/bytes, writer wait attributable to flush, throughput/p99, re-dirty count, checkpoint reflush, victim waits.
- Correctness: hash image at submit/return; inject slow write and concurrent writers.
- Expected trade-off: READ removes memcpy but converts I/O latency into writer stall; no assumption that it wins without measurement.

### EXP-CUBRID-FLUSH-04: blocking `O_DIRECT` lifetime boundary

- In an isolated prototype only, allocate page-aligned request buffer and use a blocking `O_DIRECT` descriptor.
- Compare snapshot buffer versus READ-held live frame.
- Pause writers during syscall and immediately after return to establish that no post-return pin is needed for blocking I/O.
- Validate alignment/size/filesystem prerequisites separately; do not infer AIO behavior from this test.

### EXP-CUBRID-FLUSH-05: AIO copy versus dedicated freeze

- Throwaway prototype with two modes:
  1. heap/request-owned snapshot submitted asynchronously;
  2. live frame with request-owned `IO_WRITE_FREEZE` + FLUSHING generation.
- Inject completion on a different worker, delayed completion, cancellation, submit failure, completion failure and shutdown during in-flight request.
- Invariants:
  - no writer modifies frozen image;
  - no victim/reuse before completion;
  - every terminal path releases exactly once and wakes waiters;
  - concurrent re-dirty is preserved in copy mode;
  - WAL precedes submit;
  - TDE uses request-owned cipher memory.
- Compare writer stall, memory high-water, completion latency and throughput.

### EXP-CUBRID-FLUSH-06: DWB ownership and shutdown drain

- Pause DWB daemon after `dwb_add_page` returns, mutate/evict original page, then resume.
- Verify home write bytes equal DWB slot snapshot, demonstrating existing safe deferred-copy ownership.
- Trigger shutdown with partial DWB block and confirm `dwb_flush_force` completes before DWB destroy.

### EXP-CUBRID-FLUSH-07: correct promote counter oracle

- Collect both summary and raw `Num_data_page_promote_ext` in one interval.
- Sum raw dimensions independently and assert the present summary exhibits the `×101` artifact.
- Use raw counters only, broken down by module/page type if instrumentation can identify callers; do not attribute `PAGE_UNKNOWN` aggregate directly to B-tree.

## Recommended decision framing

Do not ask “AIO이면 SX가 필요한가?” as a single yes/no question. Split it into four decisions:

1. What exact bytes are submitted: plain live frame, TDE cipher buffer, or DWB copy?
2. Is the I/O blocking through completion or asynchronously completed later?
3. If live frame, which mechanism supplies writer exclusion and frame/generation pin?
4. Who owns completion/error/cancel/shutdown cleanup?

For the current synchronous CUBRID path, snapshot-copy is correct and SX is unnecessary. For a copy-free synchronous path, READ fix plus existing FLUSHING is sufficient in principle and is the smallest prototype. For true AIO, a request-owned copy is the lowest-risk first implementation; if memory/copy cost justifies live-frame AIO, a dedicated internal `IO_WRITE_FREEZE` is semantically cleaner than stretching the current thread-owned READ holder. SX should be justified by broader page-latch use cases (for example deterministic promotion), not declared mandatory solely because AIO or direct I/O is mentioned.

## 2026-08-11 addendum — low-cardinality overflow OID와 SX 후보

고정 source `f799e05d…`에서 확인한 경계는 다음과 같다.

- leaf overflow flag는 별도 header가 아니라 첫 OID slotid 상위 bit `0x2000`에 pack되고, leaf record 끝은
  chain head VPID를 가진다. overflow header는 `next_vpid` 하나뿐이다.
- literal `CREATE INDEX` bulk loader는 current tail을 알고 O(1)로 tail append한다
  (`btree_load.c:2746-2842`). 이후 DML만 `btree_find_free_overflow_oids_page`에서 head부터 first-fit한다.
- DML helper는 각 overflow page를 WRITE로 fix하고, full이면 next VPID를 읽은 뒤 unfix한다. helper가 동시에
  잡는 overflow latch는 최대 1장이지만 caller의 leaf WRITE는 계속 남는다. 공간 page는 WRITE-latched로
  반환되어 같은 latch 아래 insert하므로 재검증 race는 없다 (`btree.c:12137-12179,30069-30112`).
- runtime 새 page는 leaf 직후의 head에 들어가므로 보통 새 head가 찰 때까지 첫 page에서 끝난다. 한 호출의
  worst case는 O(K)이지만 모든 insert가 O(K)는 아니다. bulk-built partial tail, head-full 증설, 깊은
  fragmentation에서 긴 scan이 나타날 수 있다.
- unique+overflow는 금지되지 않는다. assertion은 CLASS_OID flag를 요구하며 unique relocation path가 실제
  overflow insert를 호출한다 (`btree.c:29784-29948,3005-3008`).
- overflow-only SX는 이미 진행 중인 overflow READ와의 충돌을 줄일 후보일 뿐 O(K), fix/unfix, leaf WRITE,
  same-leaf writer serialization을 제거하지 않는다. 표준 range scan도 leaf READ를 유지해 이득이 가릴 수 있다.
- SX→WRITE는 “즉시 항상 성공”이 아니다. single SX, promotion 중 신규 reader gate, finite reader drain,
  latch-order 무교착 조건에서 competitor-promotion failure/restart 없이 eventual 획득하는 설계 약속이다.

파일 hash: `btree.c` `547c44…c1593`, `btree_load.c` `10df7d…c202`, `btree_load.h`
`903399…23c5`, `page_buffer.h` `2f052c…197`.
