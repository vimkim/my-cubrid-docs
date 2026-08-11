# MySQL Comparator Evidence Packet

- **Role**: MySQL Comparator — concrete owner: InnoDB
- **Topic**: CUBRID flush/write AIO에 범용 `SX` page latch가 필요한지, frame 안정성·`READ` latch·snapshot copy·전용 I/O freeze의 책임을 비교
- **Declared Scope digest (SHA-256)**: `db5ba3f0288fbb966ca5a4a832b420e7b5c582b461dc266ceda80a816c410885`
- **MySQL root/revision**: `/home/vimkim/gh/mysql/mysql-server` @ `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- **CUBRID comparison root/revision**: `/home/vimkim/gh/cb/pgbuf-analysis` @ `f799e05d77d5300c6ea5753b4a6cc7caee6d8912`
- **Timestamp**: `2026-08-11T04:45:31Z` (`2026-08-11T13:45:31+09:00`)
- **Evidence state**: 아래 MySQL 인용 파일은 모두 pinned revision과 동일한 `COMMIT` bytes이고 MySQL worktree는 clean이다. CUBRID worktree에는 unrelated untracked/submodule 상태가 있으나 인용한 `src/storage/page_buffer.c/.h`는 pinned commit과 동일한 `COMMIT` bytes이다.
- **Execution constraint**: MySQL server/runtime은 실행하지 않았다. MySQL/CUBRID source와 Book/report/claim ledger는 수정하지 않았고, 이 packet만 작성했다.

## 1. 결론 요약

InnoDB의 답은 “flush에 `SX` 하나면 된다”가 아니다. 정상 uncompressed `BUF_BLOCK_FILE_PAGE`의 write flush는 다음 세 책임을 분리해 결합한다.

1. `block->lock`의 `SX`는 content protocol이다. `S` reader와 공존하고, 다른 `SX` 및 `X`를 막는다. flusher 자신이 page LSN/checksum을 준비한 뒤부터 datafile I/O completion까지 다른 updater가 submitted image를 바꾸지 못한다.
2. `BUF_IO_WRITE` (`io_fix`)는 buffer-manager I/O state다. 두 번째 flusher를 거부하고, block relocation/eviction을 막고, flush batch 수와 completion cleanup을 묶는다.
3. callback과 `pass=BUF_IO_WRITE` ownership transfer는 submitter가 아닌 I/O completion thread가 `io_fix`와 `SX`를 끝내게 한다. AIO buffer 주소/내용 lifetime은 submit 반환이 아니라 callback 시작까지다.

따라서 InnoDB를 CUBRID에 대응시키면 `SX ≈ content freeze`, `io_fix ≈ single-flusher + frame pin`, callback/pass protocol `≈ completion-safe owner`다. CUBRID의 현재 `FLUSHING_TO_DISK`는 이미 두 번째 flusher와 victim을 막는 책임을 상당 부분 갖는다. live-frame AIO를 택할 때 새로 필요한 것은 “모든 page modifier를 completion까지 막는 content freeze”와 “completion thread가 해제할 수 있는 request ownership”이다. 이것을 범용 public `SX`로 표현할 수는 있지만 유일한 답은 아니다. `IO_WRITE_FREEZE` 같은 buffer-manager 내부 상태로 writer admission을 막거나, request-owned snapshot을 completion까지 유지하는 copy-AIO도 정확성상 가능하다.

또한 `O_DIRECT`와 AIO를 분리해야 한다. synchronous `O_DIRECT`는 page cache를 우회하지만 blocking call 반환까지가 buffer lifetime이다. AIO만 callback/completion까지 lifetime을 연장한다. InnoDB는 두 모드를 같은 file layer에서 지원하지만, source contract는 동기/비동기 lifetime을 명확히 다르게 적는다.

## 2. 책임 분해: InnoDB가 실제로 보장하는 것

| 책임 | InnoDB 수단 | 보장 구간 | CUBRID에 주는 의미 |
|---|---|---|---|
| reader 허용, updater 금지 | normal page의 `block->lock` `SX` | output image 준비 전부터 datafile completion까지 | strict `READ`나 전용 writer-freeze도 같은 content invariant를 줄 수 있다. 이름이 `SX`일 필요는 없다. |
| 두 번째 flusher 금지 | `io_fix=BUF_IO_WRITE`; ready check는 `io_fix != NONE`을 거부 | flush claim부터 completion/abort cleanup까지 | 현재 `FLUSHING_TO_DISK`가 이미 담당하는 축이다. |
| relocation/eviction 금지 | `io_fix != NONE`이면 `buf_page_can_relocate()` false | 동일 | page latch와 별도인 frame identity/lifetime 계약이다. |
| async completion owner | `fil_io()` callback이 `bpage`를 capture; debug responsibility transfer; latch `pass` 값 | submitter 반환을 넘어 callback까지 | current CUBRID thread holder/fix를 그대로 AIO completion에 넘기는 것은 drop-in이 아니다. request object/owner가 필요하다. |
| WAL-before-data | page의 `newest_lsn`까지 redo를 fully persist한 뒤 `dblwr::write()` | data write submission 전 | CUBRID `logpb_flush_log_for_wal()` 순서와 책임이 대응한다. |
| dirty cleanup | updater가 SX 때문에 겹치지 않으므로 completion에서 flush list 제거 + clean | successful datafile completion | CUBRID snapshot flush처럼 I/O 중 re-dirty branch가 없다. |
| torn-write protection | doublewrite copy를 먼저 동기 write/필요 시 flush한 뒤 datafile write | DWB durable stage → datafile completion | “InnoDB flush가 무복사”라는 표현은 일반화하면 틀린다. DWB batch에는 copy가 있다. |

### 핵심 불변식

정상 uncompressed persistent page의 plain-image datafile AIO를 기준으로 한 불변식은 다음과 같다.

```text
I1. output preparation이 시작된 뒤 datafile callback이 시작될 때까지
    다른 SX/X updater는 block->frame을 변경할 수 없다.

I2. io_fix == BUF_IO_WRITE인 동안
    같은 page의 두 번째 flush claim과 block relocation은 허용되지 않는다.

I3. AIO slot이 보관하는 raw buffer pointer와 그 bytes는
    submit return이 아니라 callback 시작까지 유효하다.

I4. data page submission 전에 page.newest_lsn보다 작은 redo가
    FULLY_PERSISTED 상태에 도달해야 한다.
```

`SX`는 I1을, `io_fix`는 I2를, callback/pass ownership은 I3의 해제를, redo persistence는 I4를 담당한다. 이 분해가 CUBRID 설계 비교의 중심이다.

## 3. S/SX/X와 actor compatibility

`sync0rw.cc`의 명시적 matrix는 `S/SX=compatible`, `SX/SX=incompatible`, `SX/X=incompatible`다. flush는 `pass=BUF_IO_WRITE`로 `SX`를 잡는다. `pass != 0`은 다른 thread가 unlock할 수 있음을 뜻한다.

정상 uncompressed persistent `BUF_BLOCK_FILE_PAGE`가 datafile write 중일 때:

| actor | 요청/검사 | 결과 | 직접 근거 |
|---|---|---|---|
| reader `R` | `Buf_fetch::mtr_add_page()`의 `RW_S_LATCH` | 통과 가능. `S`와 flush `SX`가 호환된다. | `sync0rw.cc:93-97`, `buf0buf.cc:4149-4179` |
| writer `W` | page update용 `SX` 또는 `X` | 대기. 둘 다 기존 flush `SX`와 충돌한다. | `sync0rw.cc:93-97` |
| second flusher `F2` | `buf_flush_ready_for_flush()` | `io_fix != BUF_IO_NONE`이면 false. latch 경쟁에 도달하기 전에 single-flusher가 된다. | `buf0flu.cc:508-570` |
| victim/relocator `V` | `buf_flush_ready_for_replace()` → `buf_page_can_relocate()` | 거부. `io_fix == NONE && buf_fix_count == 0`이 아니기 때문이다. | `buf0flu.cc:476-497`, `buf0buf.ic:501-511` |
| completion thread | `buf_page_io_complete()` | clean/remove, `io_fix=NONE`, `SX` unlock, 정책에 따라 eviction | `buf0buf.cc:5893-5997`, `buf0flu.cc:687-705` |

두 가지 예외를 숨기면 안 된다.

- compressed-only `BUF_BLOCK_ZIP_DIRTY`는 `buf_flush_page()`에서 `rw_lock=nullptr`이고 normal block `SX`를 잡지 않는다. 그 path는 page mutex/io-fix 및 compressed descriptor lifecycle에 의존한다.
- system temporary/intrinsic page는 normal page latch 대신 `buf_fix_count`/`io_fix` 동기화가 추가된다. `Buf_fetch::check_state()`는 temp page가 I/O-fixed이면 unfix 후 sleep/retry한다. 본 packet의 reader-allowed matrix는 normal persistent uncompressed page에 한정한다.

## 4. End-to-end call paths

### 4.1 Doublewrite disabled/skip, asynchronous datafile write

```text
flush-list/LRU caller
  -> buf_flush_page()
       acquire block SX (normal page)
       set io_fix=BUF_IO_WRITE + flush_type + n_flush++
       release page mutex
  -> buf_flush_write_block_low()
       persist redo < newest_lsn (FULLY_PERSISTED)
       buf_flush_init_for_writing(frame): stamp LSN/checksum
  -> dblwr::write()
       skip DWB for temporary/read-only/disabled cases
  -> Double_write::write_to_datafile(sync=false, e_block=null)
       Double_write::prepare() -> bpage->frame
  -> fil_io()
       capture bpage + completion callback
  -> Fil_shard::do_io()
  -> fil_node_t::post_io_async()
  -> Tablespace_node_handle::write_page_async()
  -> os_aio_func()
       AIO::reserve_slot(): store raw buf/ptr + callback
       native AIO io_submit or simulated-AIO queue
  -> I/O handler -> fil_aio_wait() -> callback(err)
  -> buf_page_io_complete()
  -> buf_flush_write_complete()
       remove from flush list, set clean, io_fix=NONE, n_flush--
  -> rw_lock_sx_unlock_gen(pass=BUF_IO_WRITE)
       optional LRU eviction
```

### 4.2 Doublewrite enabled, asynchronous batch

```text
buf_flush_write_block_low()
  -> dblwr::write(sync=false)
       optional get_encrypted_frame() -> e_block
       release debug io responsibility
  -> Double_write::submit()
  -> Double_write::enqueue()
       Buffer::append(frame/e_frame) memcpy into m_buffer       [DWB image copy]
       m_buf_pages.push_back(bpage, e_block)                    [page/request refs]
       if full/forced:
         -> write_pages()
         -> write_dblwr_pages()
              Segment::write(m_buffer) synchronously
              optional DWB file flush
              clear m_buffer
         -> write_data_pages()
              for each bpage: write_to_datafile(sync=false)
                e_block != null: datafile buffer = e_block
                e_block == null: datafile buffer = live bpage->frame
              pre-completion callback frees e_block if present
              normal completion performs io_fix/SX cleanup
```

중요한 구분은 DWB file과 datafile의 source buffer가 다르다는 점이다.

- DWB batch write는 `m_buffer`의 copy를 쓴다.
- plain/untransformed datafile write는 `m_buffer`를 재사용하지 않고 `bpage->frame`을 다시 얻는다.
- encrypted/compressed `e_block`이 있으면 같은 transformed auxiliary block을 DWB copy의 원천과 datafile I/O buffer로 쓰고 datafile pre-completion에서 free한다.
- 따라서 plain frame의 `SX` hold time은 DWB queue 대기, DWB synchronous write/flush, datafile AIO completion을 모두 포함할 수 있다.

### 4.3 Synchronous single-page flush

```text
buf_flush_page(... sync=true)
  -> dblwr::write()
  -> Double_write::sync_page_flush()
       single_write() to DWB segment
       optional DWB flush
       write_to_datafile(sync=true)
         fil_node_t::post_io_sync(): blocking write
         inline callback -> buf_page_io_complete()
         datafile fil_flush()
       return DWB segment
```

동기 path도 같은 `SX + io_fix` protocol을 쓰지만 buffer lifetime은 blocking call return까지다. cross-thread callback lifetime이 본질적으로 필요한 것은 asynchronous path다.

## 5. Doublewrite/datafile image ownership과 lifetime

| image/object | owner | 생성/획득 | 마지막 소비/해제 | frame과의 관계 |
|---|---|---|---|---|
| `buf_block_t::frame` | buffer pool block | page resident lifecycle | completion 후 `io_fix`/SX 해제 뒤에야 relocation 가능 | normal plain datafile AIO가 직접 참조한다. |
| `dblwr::Double_write::m_buffer` | doublewrite instance | `enqueue()`의 `memcpy` | DWB segment synchronous write 후 `clear()` | DWB file 전용 batch copy다. datafile source가 아니다. |
| `file::Block *e_block` | DWB request tuple/callback | compression/encryption transform | datafile pre-completion callback에서 `os_free_block()` | transformed output image. DWB copy 원천이자 datafile buffer다. |
| `m_buf_pages` tuple | doublewrite instance | enqueue | datafile submissions 뒤 `clear()` | `bpage`/`e_block`을 DWB phase에서 datafile phase로 넘긴다. |
| AIO `Slot` | global AIO array | `AIO::reserve_slot()` | handler가 completion을 거둔 뒤 slot release | raw `buf`, actual `ptr`, callback을 completion까지 보관한다. |
| `io_fix=BUF_IO_WRITE` | `buf_page_t` under buffer-manager protocol | flush claim | completion 또는 stale/deleted abort cleanup | frame relocation 및 second flush를 막는다. |
| page `SX(pass=BUF_IO_WRITE)` | rw-lock; unlock permission transferred | flush claim/content prep 전 | completion 또는 stale cleanup | reader를 허용하면서 updater를 막는다. |

## 6. WAL, dirty state, completion, errors

### WAL-before-data

`buf_flush_write_block_low()`는 `bpage->get_newest_lsn()`을 읽고, recovery 중이 아닐 때 `peek_first_nonpersisted_lsn() < flush_to_lsn`이면 `persist_smaller_than(... FULLY_PERSISTED, PAGE_FLUSHING)`을 반드시 성공시킨 뒤 output page를 준비하고 `dblwr::write()`로 내려간다. WAL durability는 kernel data write submission보다 앞선다.

### Dirty state

InnoDB는 flush 시작 때 dirty를 지우지 않는다. `io_fix=WRITE`와 `SX`가 유지되는 동안 page는 dirty/flush-list resident 상태다. successful datafile completion에서만 `buf_flush_write_complete()`가 `buf_flush_remove()`를 호출하고 `set_clean()` 및 `io_fix=NONE`을 수행한다. updater가 `SX`/`X` 충돌로 기다리므로 CUBRID snapshot-copy 방식의 “I/O 중 재더티” branch가 필요하지 않다.

### Error model

terminal write failure는 CUBRID처럼 dirty/oldest-LSA를 복구해 caller에게 재시도 가능한 error를 반환하는 normal branch가 아니다.

- DWB `Segment::write()`는 `os_file_write_retry()` 결과가 `DB_SUCCESS`임을 `ut_a`로 강제한다.
- datafile `Fil_shard::do_io()`는 DWB recovery read가 아닌 일반 I/O result가 `DB_SUCCESS` 또는 normalized `DB_IO_NO_PUNCH_HOLE`임을 `ut_a`로 강제한다.
- `ut_a`는 debug-only assertion이 아니라 실패 시 execution을 abort하는 macro다.
- tablespace stale/deleted는 별도 expected branch다. callback이 `buf_page_free_stale_during_write()`를 호출해 `io_fix`/SX/flush count를 정리하고 stale page를 free한다.
- `Double_write::sync_page_flush()`에는 error handling consistency TODO가 있으며 반환 `err`를 무시하고 `DB_SUCCESS`를 반환한다. 하지만 terminal ordinary I/O errors는 더 아래 `ut_a`에서 먼저 fatal 처리되는 구조다.

따라서 MySQL 비교를 근거로 CUBRID의 recoverable flush failure semantics를 없애면 안 된다. 두 엔진의 failure policy가 다르다.

## 7. `O_DIRECT`와 AIO를 반드시 분리해야 하는 이유

MySQL source의 contract는 명확하다.

- `fil_node_t::post_io_sync()`는 blocking이고 caller-managed buffer가 call return까지 유효해야 한다.
- `fil_node_t::post_io_async()`는 callback이 시작될 때까지 buffer가 유효해야 하며 callback은 다른 thread에서 실행될 수 있다.
- `SRV_UNIX_O_DIRECT`/`SRV_UNIX_O_DIRECT_NO_FSYNC`는 data/DWB file에 OS cache bypass를 설정하는 file-open policy다. 이 enum은 sync/async submission 선택과 별도다.

따라서 네 경우의 lifetime은 다음과 같다.

| API/policy | cache 경유 | call return 후 I/O 가능 | 제출 buffer 안정 구간 |
|---|---:|---:|---|
| synchronous buffered write | 보통 yes | no | blocking call return까지 |
| synchronous `O_DIRECT` | no | no | blocking call return까지 |
| buffered AIO | 정책별 | yes | callback/completion까지 |
| direct AIO | no | yes | callback/completion까지 |

`O_DIRECT` 자체가 `SX` hold를 completion까지 연장시키는 것은 아니다. AIO가 그 lifetime을 연장한다. synchronous zero-copy라면 current thread가 strict `READ` 또는 전용 freeze를 call return까지 유지하는 것으로 content invariant를 충족할 수 있다.

## 8. CUBRID semantic gap

### 8.1 현재 CUBRID snapshot flush

`pgbuf_bcb_flush_with_wal()`은 BCB mutex 아래서 stack-local aligned `page_buf`에 plain page를 `memcpy`하거나 TDE output을 만든다. `FLUSHING_TO_DISK`를 세우면서 dirty를 지우고, live frame의 page LSA와 `oldest_unflush_lsa`를 snapshot한 뒤 mutex를 푼다. 이후 WAL을 먼저 flush하고 동기 `fileio_write()` 또는 DWB에 output image를 넘긴다.

이 구조의 의미는 다음과 같다.

- actual synchronous write가 읽는 것은 live frame이 아니라 snapshot/TDE/DWB image다.
- `FLUSHING_TO_DISK`는 second flusher와 victim을 막지만 live frame writer를 막지 않는다.
- 새 writer는 dirty를 다시 세울 수 있다. source comment가 이 overlap을 의도적으로 명시한다.
- write 실패 시 이전 dirty와 `oldest_unflush_lsa`를 복구하고 flush waiter를 깨운다.
- stack-local `page_buf`는 synchronous call return까지만 살아 있으므로 그대로 AIO에 넘길 수 없다. copy-AIO라면 request-owned buffer로 lifetime을 바꿔야 한다.

### 8.2 같은 이름보다 책임을 비교한 mapping

| InnoDB | CUBRID 현재/후보 | 판정 | semantic gap |
|---|---|---|---|
| page `SX` during flush | current strict `READ` held by flusher | **partial analogy** | 둘 다 reader와 공존하고 writer를 막을 수 있다. 그러나 CUBRID `READ`는 thread holder/fix에 귀속되어 async completion thread handoff가 현재 Interface에 없다. InnoDB `S`는 `SX`와 호환되므로 같은 이름의 READ/S는 동일하지 않다. |
| `BUF_IO_WRITE` | `FLUSHING_TO_DISK` | **partial analogy, responsibility nearly equivalent** | second flusher/victim 방지는 가깝다. dirty timing과 failure policy는 다르다. InnoDB는 completion까지 dirty 유지, CUBRID는 시작 때 clear하고 re-dirty를 추적한다. |
| `SX + io_fix + callback/pass` | proposed `IO_WRITE_FREEZE + FLUSHING + request` | **partial analogy** | 전용 freeze가 모든 modifier admission을 실제로 막고 completion ownership/wakeup을 제공해야 동등하다. 단순 flag 추가만으로는 부족하다. |
| DWB `m_buffer` copy | CUBRID snapshot/DWB copy | **partial analogy** | 둘 다 durable staging copy가 있으나 InnoDB plain datafile phase는 다시 live frame을 쓴다. CUBRID current datafile phase는 snapshot image를 쓴다. |
| AIO Slot callback lifetime | proposed copy-AIO request buffer | **equivalent responsibility** | implementation 위치는 달라도 address/bytes를 completion까지 소유해야 한다. |
| full page `WRITE` latch | CUBRID current `WRITE` | **equivalent content safety, worse concurrency** | reader까지 막으므로 correctness fallback이지 InnoDB `SX`와 같은 concurrency는 아니다. |

### 8.3 design option comparison

| CUBRID option | output bytes owner/lifetime | reader | writer | second flusher/victim | 핵심 비용/위험 |
|---|---|---:|---:|---|---|
| current snapshot + sync write | stack/DWB image, call return까지 | 허용 | 허용; re-dirty | `FLUSHING`이 차단 | page copy/TDE cost; current semantics 검증됨 |
| request-owned snapshot + AIO | request image, completion까지 | 허용 | 허용; re-dirty | `FLUSHING`이 차단 | in-flight memory/copy pressure, cancel/error cleanup |
| live frame + strict `READ`, sync | current thread holder, call return까지 | 허용 | 차단 | 별도 `FLUSHING` 필요 | sync에서 가능하나 thread holder duration과 writer wait 증가 |
| live frame + current `READ`, AIO | holder를 completion까지 넘겨야 함 | 허용 | 차단 | 별도 `FLUSHING` 필요 | current holder/fix ownership에 cross-thread release가 없어 drop-in 불가 |
| live frame + public generic `SX` + I/O request | latch/request, completion까지 | 허용 | 차단 | `FLUSHING` 또는 별도 io-fix 필요 | public latch matrix/wait/fairness/ordered-fix 전체가 넓어짐 |
| live frame + internal `IO_WRITE_FREEZE` + request | BCB/request, completion까지 | 허용 | 차단 | 같은 state machine이 차단 | 좁은 seam. 모든 modifier가 writer gate를 통과하는지 증명 필요 |
| live frame + `WRITE` | request/latch, completion까지 | 차단 | 차단 | 별도 `FLUSHING` 필요 | 가장 단순하지만 read concurrency 손실 |

### 8.4 비교에서 도출되는 bounded recommendation

Source comparison만으로 “CUBRID에 generic `SX`를 도입하라”는 결론은 나오지 않는다. 다음 순서가 더 좁고 검증 가능하다.

1. plain-page live-frame AIO를 실제 목표로 삼을 때만 content freeze를 추가한다. TDE/output transformation은 어차피 별도 image를 요구할 수 있다.
2. existing `FLUSHING_TO_DISK`의 single-flusher/victim-pin 책임을 보존한다.
3. content freeze를 public latch mode가 아니라 BCB-internal `IO_WRITE_FREEZE`로 먼저 모델링할 수 있다. 단, `pgbuf_fix(... WRITE)`와 promotion/unfix의 모든 writer admission point가 이 state를 기다리거나 실패해야 한다.
4. completion-owned request가 BCB/frame reference, output image(있다면), WAL target LSA, dirty snapshot, error/cancel state를 소유하고 exactly-once cleanup을 수행해야 한다.
5. generic `SX`는 flush 외 B-tree promotion 같은 독립 요구까지 같은 Interface가 해결할 때 별도로 정당화한다. InnoDB가 generic `SX`를 쓴 사실은 CUBRID public API 선택의 충분조건이 아니다.

이 recommendation은 design inference다. 아직 CUBRID prototype/runtime evidence가 없으므로 성능·공정성·deadlock 면에서 `INFERRED`이며 falsifier는 아래 suggested tests다.

## 9. Examined files and symbols

### MySQL/InnoDB

| path | symbols/areas | reason |
|---|---|---|
| `storage/innobase/sync/sync0rw.cc` | lock-word model, compatibility matrix, `rw_lock_sx_lock_low` | S/SX/X compatibility와 single-SX 의미 |
| `storage/innobase/include/sync0rw.h`, `sync0rw.ic` | latch enums, pass ownership, unlock | completion-thread unlock contract |
| `storage/innobase/include/buf0types.h` | `buf_io_fix` | `BUF_IO_WRITE`/`BUF_IO_PIN` 의미 |
| `storage/innobase/include/buf0buf.h`, `buf0buf.ic` | `buf_page_t::io_fix`, responsibility debug model, `buf_page_can_relocate` | frame identity/lifetime, relocation gate |
| `storage/innobase/buf/buf0flu.cc` | `buf_flush_ready_for_*`, `buf_flush_page`, `buf_flush_write_block_low`, `buf_flush_write_complete`, `buf_flush_init_for_writing` | selection, WAL, latch/state acquisition, output prep, completion |
| `storage/innobase/buf/buf0buf.cc` | `Buf_fetch::check_state`, `Buf_fetch::mtr_add_page`, `buf_page_io_complete`, `buf_page_free_stale_during_write` | reader/writer access, completion ownership, stale cleanup |
| `storage/innobase/include/buf0dblwr.h` | `dblwr::Buffer` | aligned DWB copy ownership |
| `storage/innobase/buf/buf0dblwr.cc` | `Double_write::enqueue`, `write_dblwr_pages`, `write_data_pages`, `write_to_datafile`, `sync_page_flush`, `dblwr::write` | DWB/datafile phases and e_block lifetime |
| `storage/innobase/include/fil0fil.h` | `fil_node_t::post_io_sync/async` contracts | sync vs async caller buffer lifetime |
| `storage/innobase/fil/fil0fil.cc` | `fil_node_t::post_io_*`, `Fil_shard::do_io`, `fil_io`, `fil_aio_wait` | callback chain and terminal errors |
| `storage/innobase/include/fil0tablespace_node_handle_interface.h` | `write_page`, `write_page_async` | storage-node lifetime contract |
| `storage/innobase/fil/fil0innodb_tablespace_node_handle.cc` | `write_page`, `write_page_async` | `os_file_write` vs `os_aio` seam |
| `storage/innobase/include/os0file.h`, `storage/innobase/os/os0file.cc` | `Slot`, `AIO::reserve_slot`, `os_aio_func`, O_DIRECT open policy | raw buffer/callback retention and direct-I/O policy |
| `storage/innobase/include/srv0srv.h` | `srv_unix_flush_t`, `srv_is_direct_io` | O_DIRECT is orthogonal file policy |
| `storage/innobase/handler/i_s.cc` | `io_fix_str`, `i_s_innodb_buffer_page_get_info` | `IO_WRITE` observability |
| `storage/innobase/srv/srv0mon.cc`, `include/srv0mon.h` | DWB async/sync/wait counters | observability candidates |
| `storage/innobase/include/ut0dbg.h` | `ut_a` | terminal I/O failure policy |

### CUBRID comparison seam

| path | symbols/areas | reason |
|---|---|---|
| `src/storage/page_buffer.h` | `PGBUF_LATCH_MODE` | current public READ/WRITE and internal-only FLUSH mode |
| `src/storage/page_buffer.c` | BCB flags/mask, `pgbuf_latch_bcb_upon_fix`, `pgbuf_bcb_flush_with_wal`, `pgbuf_bcb_mark_is_flushing`, failure cleanup | snapshot image, thread holder, re-dirty, second-flush/victim exclusion, recoverable failure |

## 10. Structured source Claim candidates

통합 시 ID는 main agent가 renumber할 수 있다. 모든 source ref의 `evidence_state`는 `COMMIT`이다.

### MYSQL-C001 — S/SX/X compatibility

```yaml
id: MYSQL-C001
claim_ko: InnoDB rw-lock의 SX는 S와 호환되고 다른 SX 및 X와 배타이므로, page flush가 SX를 잡으면 reader를 허용하면서 updater 후보를 하나로 직렬화할 수 있다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/sync/sync0rw.cc
    symbol: LOCK COMPATIBILITY MATRIX
    line_start: 54
    line_end: 105
    file_sha256: 2e061541ccba8a682461f8601746172a407c0a2cba44b678782483960d053c34
    evidence_state: COMMIT
limitations_ko: 일반 rw-lock semantics다. flush path가 실제로 SX를 쓰는 사실은 MYSQL-C002가 별도로 증명한다.
```

### MYSQL-C002 — flush claim combines SX and io_fix

```yaml
id: MYSQL-C002
claim_ko: 정상 uncompressed page flush는 block SX를 획득하고 io_fix를 BUF_IO_WRITE로 바꾼 뒤 page mutex를 놓고 write path로 내려가며, flush-list는 io_fix를 먼저 claim한 뒤 SX를 기다릴 수 있다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/buf/buf0flu.cc
    symbol: buf_flush_page
    line_start: 1051
    line_end: 1166
    file_sha256: 5836c3b49ce1a4798f0af76a01edc91a1c1659ae7b3a268aa300f5de103cc212
    evidence_state: COMMIT
limitations_ko: compressed-only page와 temporary/intrinsic page에는 별도 경로가 있다.
```

### MYSQL-C003 — WAL-before-data and live-frame output preparation

```yaml
id: MYSQL-C003
claim_ko: InnoDB flush는 page newest LSN보다 앞선 redo를 FULLY_PERSISTED로 만든 뒤 live frame에 output LSN/checksum을 준비하고 doublewrite/datafile write로 내려간다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/buf/buf0flu.cc
    symbol: buf_flush_write_block_low
    line_start: 943
    line_end: 1038
    file_sha256: 5836c3b49ce1a4798f0af76a01edc91a1c1659ae7b3a268aa300f5de103cc212
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0flu.cc
    symbol: buf_flush_init_for_writing
    line_start: 758
    line_end: 936
    file_sha256: 5836c3b49ce1a4798f0af76a01edc91a1c1659ae7b3a268aa300f5de103cc212
    evidence_state: COMMIT
limitations_ko: recovery/read-only branches와 page-type별 checksum 세부는 본 Claim의 범위 밖이다.
```

### MYSQL-C004 — synchronous versus asynchronous buffer lifetime

```yaml
id: MYSQL-C004
claim_ko: InnoDB file interface에서 synchronous I/O buffer는 call return까지, asynchronous I/O buffer는 callback 시작까지 caller가 유효하게 유지해야 한다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/include/fil0fil.h
    symbol: post_io_sync
    line_start: 259
    line_end: 284
    file_sha256: 0b1782a14063c58f15ad49b783017e0443bebd28c12340b15ee1dd59c4fafad2
    evidence_state: COMMIT
  - path: storage/innobase/include/fil0fil.h
    symbol: post_io_async
    line_start: 306
    line_end: 344
    file_sha256: 0b1782a14063c58f15ad49b783017e0443bebd28c12340b15ee1dd59c4fafad2
    evidence_state: COMMIT
  - path: storage/innobase/os/os0file.cc
    symbol: AIO::reserve_slot
    line_start: 6066
    line_end: 6169
    file_sha256: 3c7d6ea4a288278268d8ed975fd90845d389017dac839928fe6de1c4cb1f09f5
    evidence_state: COMMIT
limitations_ko: callback은 일부 immediate failure에서 submitter thread 안에서 실행될 수도 있으므로 exactly-once cleanup은 thread identity가 아니라 request state에 기대야 한다.
```

### MYSQL-C005 — doublewrite copy and datafile buffer are different phases

```yaml
id: MYSQL-C005
claim_ko: regular asynchronous doublewrite batch는 output bytes를 m_buffer에 memcpy해 DWB file에 쓰지만, 이후 plain datafile write는 m_buffer가 아니라 live bpage frame을 다시 참조하며 transformed e_block이 있으면 그 block을 completion 직전까지 유지한다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/include/buf0dblwr.h
    symbol: append
    line_start: 61
    line_end: 140
    file_sha256: 614dc392affe11137760a2753781e7af61a1a1f25a601694ce506eccfff12e79
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0dblwr.cc
    symbol: Double_write::enqueue
    line_start: 655
    line_end: 697
    file_sha256: 3f06ad9d4b1d506c54a2090e0943f10360d5689502cacecc71e1bf8d6c03ff9a
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0dblwr.cc
    symbol: Double_write::write_to_datafile
    line_start: 1668
    line_end: 1710
    file_sha256: 3f06ad9d4b1d506c54a2090e0943f10360d5689502cacecc71e1bf8d6c03ff9a
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0dblwr.cc
    symbol: Double_write::write_data_pages
    line_start: 2297
    line_end: 2355
    file_sha256: 3f06ad9d4b1d506c54a2090e0943f10360d5689502cacecc71e1bf8d6c03ff9a
    evidence_state: COMMIT
limitations_ko: lower file layer의 compression/encryption이 별도 auxiliary block을 만들 수 있으므로 모든 configuration을 zero-copy라고 부르면 안 된다.
```

### MYSQL-C006 — completion releases clean/io_fix/SX

```yaml
id: MYSQL-C006
claim_ko: successful datafile I/O completion은 flush list에서 page를 제거하고 clean 및 io_fix NONE으로 전이한 뒤, 다른 thread가 잡았던 SX를 pass=BUF_IO_WRITE로 해제하고 필요하면 page를 evict한다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/buf/buf0buf.cc
    symbol: buf_page_io_complete
    line_start: 5731
    line_end: 5997
    file_sha256: a3e11712993f0542f1e173d08c047637aaeb63293cdf9b0c139dbb593a38e793
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0flu.cc
    symbol: buf_flush_write_complete
    line_start: 685
    line_end: 706
    file_sha256: 5836c3b49ce1a4798f0af76a01edc91a1c1659ae7b3a268aa300f5de103cc212
    evidence_state: COMMIT
  - path: storage/innobase/include/sync0rw.h
    symbol: rw_lock_sx_unlock_func
    line_start: 192
    line_end: 226
    file_sha256: 5ee7d7ba1e59af9f5f5bf8609c6c7044423717bf35800744abacc0d8fc5aa219
    evidence_state: COMMIT
limitations_ko: ordinary terminal I/O failure는 이 successful completion branch로 들어오지 않고 fatal assertion policy를 따른다.
```

### MYSQL-C007 — io_fix is the single-flusher/relocation gate

```yaml
id: MYSQL-C007
claim_ko: BUF_IO_WRITE는 pending write를 나타내며, non-NONE io_fix는 두 번째 flush readiness를 거부하고 page relocation/ordinary victim replacement를 막는다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/include/buf0types.h
    symbol: buf_io_fix
    line_start: 82
    line_end: 95
    file_sha256: 5d20eeb282fe9197c06a9f3d339c177e6ad24f5f1b9e0df8c323b0b3f7973084
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0flu.cc
    symbol: buf_flush_ready_for_flush_gen
    line_start: 499
    line_end: 570
    file_sha256: 5836c3b49ce1a4798f0af76a01edc91a1c1659ae7b3a268aa300f5de103cc212
    evidence_state: COMMIT
  - path: storage/innobase/include/buf0buf.ic
    symbol: buf_page_can_relocate
    line_start: 501
    line_end: 511
    file_sha256: 22dc77a73fb0a7863d98a15aba0a79966f0433e5e10e392cb4b2b19774861c1d
    evidence_state: COMMIT
limitations_ko: BUF_IO_PIN과 READ I/O의 별도 state transitions는 본 Claim 밖이다.
```

### MYSQL-C008 — terminal write failure is fatal; stale/deleted is cleanup

```yaml
id: MYSQL-C008
claim_ko: traced InnoDB page-write path에서 stale/deleted tablespace는 io_fix/SX cleanup 후 page를 free하는 expected branch지만, retry 후 남은 ordinary terminal write error는 ut_a assertion으로 process execution을 중단하며 dirty state rollback branch가 없다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/fil/fil0fil.cc
    symbol: Fil_shard::do_io
    line_start: 7212
    line_end: 7241
    file_sha256: b13da72923cca48f24506cd74d8ff9eb2898e28bca3dd56cb031ead009ba3b7f
    evidence_state: COMMIT
  - path: storage/innobase/fil/fil0fil.cc
    symbol: fil_io
    line_start: 7277
    line_end: 7331
    file_sha256: b13da72923cca48f24506cd74d8ff9eb2898e28bca3dd56cb031ead009ba3b7f
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0buf.cc
    symbol: buf_page_free_stale_during_write
    line_start: 5542
    line_end: 5595
    file_sha256: a3e11712993f0542f1e173d08c047637aaeb63293cdf9b0c139dbb593a38e793
    evidence_state: COMMIT
  - path: storage/innobase/include/ut0dbg.h
    symbol: ut_a
    line_start: 95
    line_end: 105
    file_sha256: 37ec5c682bfe6977c45a891d34658945ffae8223ab50943f1185b0fb5fd8008b
    evidence_state: COMMIT
limitations_ko: OS helper가 일부 transient error를 retry할 수 있다. Claim은 retry가 끝난 뒤 buffer-pool-level recoverable rollback이 없다는 범위다.
```

### MYSQL-C009 — O_DIRECT is orthogonal to sync/async lifetime

```yaml
id: MYSQL-C009
claim_ko: InnoDB의 O_DIRECT 설정은 data/DWB file open의 cache-bypass policy이고, synchronous와 asynchronous write API 선택 및 buffer lifetime과는 별도 축이다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/include/srv0srv.h
    symbol: srv_unix_flush_t
    line_start: 862
    line_end: 889
    file_sha256: 99860d5ba1b2da249c3065894f47c775abe703bd6ca75d4bbc80bd0b50a04234
    evidence_state: COMMIT
  - path: storage/innobase/os/os0file.cc
    symbol: os_file_create_func
    line_start: 3108
    line_end: 3130
    file_sha256: 3c7d6ea4a288278268d8ed975fd90845d389017dac839928fe6de1c4cb1f09f5
    evidence_state: COMMIT
  - path: storage/innobase/include/fil0fil.h
    symbol: post_io_sync
    line_start: 259
    line_end: 344
    file_sha256: 0b1782a14063c58f15ad49b783017e0443bebd28c12340b15ee1dd59c4fafad2
    evidence_state: COMMIT
limitations_ko: OS-level normative semantics는 Declared Scope의 설계 전제를 따른다. source는 InnoDB의 policy/API 분리를 직접 증명한다.
```

### MYSQL-C010 — io_fix is observable

```yaml
id: MYSQL-C010
claim_ko: InnoDB buffer page information 수집은 io_fix를 읽어 IO_NONE/IO_READ/IO_WRITE/IO_PIN 문자열로 노출할 수 있으며 DWB async/sync/wait counters도 존재한다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/handler/i_s.cc
    symbol: io_fix_str
    line_start: 134
    line_end: 143
    file_sha256: f456c4dd53be09e4096e7e2323005b442fb6bf0289f4eac34392421b9731b758
    evidence_state: COMMIT
  - path: storage/innobase/handler/i_s.cc
    symbol: i_s_innodb_buffer_page_get_info
    line_start: 4606
    line_end: 4668
    file_sha256: f456c4dd53be09e4096e7e2323005b442fb6bf0289f4eac34392421b9731b758
    evidence_state: COMMIT
limitations_ko: 이 source packet은 runtime availability와 sampling cost를 검증하지 않았다.
```

### MYSQL-C011 — compressed/temp exceptions

```yaml
id: MYSQL-C011
claim_ko: InnoDB flush의 page SX 규칙은 normal uncompressed page에 직접 적용되며, compressed-only page는 block SX 없이 io_fix를 쓰고 temporary/intrinsic page fetch는 io_fix/fix-count retry를 추가로 사용한다.
database: mysql
kind: source
confidence: SOURCE-CONFIRMED
revision: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
source_refs:
  - path: storage/innobase/buf/buf0flu.cc
    symbol: buf_flush_page
    line_start: 1073
    line_end: 1102
    file_sha256: 5836c3b49ce1a4798f0af76a01edc91a1c1659ae7b3a268aa300f5de103cc212
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0buf.cc
    symbol: Buf_fetch<T>::check_state
    line_start: 4065
    line_end: 4109
    file_sha256: a3e11712993f0542f1e173d08c047637aaeb63293cdf9b0c139dbb593a38e793
    evidence_state: COMMIT
limitations_ko: compressed descriptor 전체 mutation protocol은 범위 밖이며 normal-page 결론을 이 path에 기계적으로 확장하지 않는다.
```

### CMP-C001 — InnoDB SX alone is not the full contract

```yaml
id: CMP-C001
claim_ko: InnoDB가 live-frame AIO에 사용하는 계약은 SX 단독이 아니라 content SX, buffer-manager io_fix, completion callback/pass ownership의 합성이므로, CUBRID가 같은 책임을 전용 IO_WRITE_FREEZE와 request state로 분해해도 semantic requirement를 충족할 수 있다.
database: comparison
kind: analogy
confidence: INFERRED
analogy_class: partial analogy
revisions:
  mysql: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
  cubrid: f799e05d77d5300c6ea5753b4a6cc7caee6d8912
source_refs:
  - path: storage/innobase/buf/buf0flu.cc
    symbol: buf_flush_page
    line_start: 1051
    line_end: 1166
    file_sha256: 5836c3b49ce1a4798f0af76a01edc91a1c1659ae7b3a268aa300f5de103cc212
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0buf.cc
    symbol: buf_page_io_complete
    line_start: 5893
    line_end: 5987
    file_sha256: a3e11712993f0542f1e173d08c047637aaeb63293cdf9b0c139dbb593a38e793
    evidence_state: COMMIT
  - path: src/storage/page_buffer.c
    symbol: pgbuf_bcb_flush_with_wal
    line_start: 10733
    line_end: 10961
    file_sha256: d1e71931b2a2da569f7e96c8a35eab85ec5bf0b4dac5fa0c3d0ac69adf03c163
    evidence_state: COMMIT
limitations_ko: CUBRID IO_WRITE_FREEZE는 아직 구현되지 않은 설계 inference다. 모든 writer admission과 completion/error/cancel transition을 구현·시험하기 전에는 correctness가 증명되지 않는다.
```

### CMP-C002 — CUBRID current READ is not InnoDB S

```yaml
id: CMP-C002
claim_ko: CUBRID binary READ/WRITE latch에서 READ를 flusher가 잡으면 reader 허용과 writer 금지를 제공할 수 있지만, InnoDB S는 SX와 호환되므로 같은 이름의 S/READ semantics는 동등하지 않으며 current CUBRID READ holder는 thread/fix lifetime에 귀속된다.
database: comparison
kind: analogy
confidence: INFERRED
analogy_class: partial analogy
revisions:
  mysql: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
  cubrid: f799e05d77d5300c6ea5753b4a6cc7caee6d8912
source_refs:
  - path: storage/innobase/sync/sync0rw.cc
    symbol: LOCK COMPATIBILITY MATRIX
    line_start: 93
    line_end: 97
    file_sha256: 2e061541ccba8a682461f8601746172a407c0a2cba44b678782483960d053c34
    evidence_state: COMMIT
  - path: src/storage/page_buffer.h
    symbol: PGBUF_LATCH_MODE
    line_start: 189
    line_end: 197
    file_sha256: 2f052cd4be1df289692990973dcb30f332bd75f5b135ea367a5960e866c9b197
    evidence_state: COMMIT
  - path: src/storage/page_buffer.c
    symbol: pgbuf_latch_bcb_upon_fix
    line_start: 6298
    line_end: 6525
    file_sha256: d1e71931b2a2da569f7e96c8a35eab85ec5bf0b4dac5fa0c3d0ac69adf03c163
    evidence_state: COMMIT
limitations_ko: READ를 AIO completion까지 넘기는 API는 current source에 없다. sync zero-copy 가능성과 async handoff 가능성을 구분해야 한다.
```

### CMP-C003 — `io_fix` and `FLUSHING_TO_DISK`

```yaml
id: CMP-C003
claim_ko: InnoDB BUF_IO_WRITE와 CUBRID FLUSHING_TO_DISK는 single-flusher와 victim/relocation 금지 책임에서 가깝지만, InnoDB는 writer를 SX로 막고 completion에서 clean 처리하는 반면 CUBRID는 snapshot 뒤 writer overlap과 re-dirty를 허용하고 failure에 dirty/LSA를 복구한다.
database: comparison
kind: analogy
confidence: SOURCE-CONFIRMED
analogy_class: partial analogy
revisions:
  mysql: 06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8
  cubrid: f799e05d77d5300c6ea5753b4a6cc7caee6d8912
source_refs:
  - path: storage/innobase/buf/buf0flu.cc
    symbol: buf_flush_ready_for_flush_gen
    line_start: 499
    line_end: 570
    file_sha256: 5836c3b49ce1a4798f0af76a01edc91a1c1659ae7b3a268aa300f5de103cc212
    evidence_state: COMMIT
  - path: storage/innobase/buf/buf0flu.cc
    symbol: buf_flush_write_complete
    line_start: 573
    line_end: 705
    file_sha256: 5836c3b49ce1a4798f0af76a01edc91a1c1659ae7b3a268aa300f5de103cc212
    evidence_state: COMMIT
  - path: src/storage/page_buffer.c
    symbol: PGBUF_BCB_INVALID_VICTIM_CANDIDATE_MASK
    line_start: 222
    line_end: 262
    file_sha256: d1e71931b2a2da569f7e96c8a35eab85ec5bf0b4dac5fa0c3d0ac69adf03c163
    evidence_state: COMMIT
  - path: src/storage/page_buffer.c
    symbol: pgbuf_bcb_mark_is_flushing
    line_start: 16077
    line_end: 16125
    file_sha256: d1e71931b2a2da569f7e96c8a35eab85ec5bf0b4dac5fa0c3d0ac69adf03c163
    evidence_state: COMMIT
limitations_ko: CUBRID DWB post-flush direct-victim handoff의 전체 lifecycle은 CUBRID tracer packet이 보강해야 한다.
```

## 11. Negative searches and search gaps

### Negative searches performed

1. `rg -n "buf_page_set_io_fix\(bpage, BUF_IO_WRITE|rw_lock_sx_unlock_gen.*BUF_IO_WRITE" storage/innobase`
   - `BUF_IO_WRITE` setting은 traced normal flush의 `buf0flu.cc:1108`에 집중되어 있다.
   - write `SX` unlock은 successful completion (`buf0buf.cc:5972`)과 stale/deleted abort cleanup (`buf0buf.cc:5560`) 두 곳이다. submit return 직후 unlock하는 path는 찾지 못했다.
2. `rg -n "buf_page_io_complete\(" storage/innobase`
   - operational caller는 `fil0fil.cc:7328`의 I/O postprocess callback이다. 나머지는 declaration/comment/definition이다. completion state change가 callback seam에 모인다.
3. `rg -n "m_buffer|write_to_datafile|write_data_pages" storage/innobase/buf/buf0dblwr.cc`
   - `m_buffer`는 DWB segment write에 쓰고 clear된다. plain datafile write는 `bpage`에서 frame을 다시 준비한다. `m_buffer`를 datafile `fil_io()`에 넘기는 call은 찾지 못했다.
4. `rg -n "PGBUF_LATCH_SX|PGBUF_SX|SX_LATCH" src/storage/page_buffer.[ch]`
   - current CUBRID page-buffer public latch enum에는 SX가 없다. `PGBUF_LATCH_FLUSH`는 page fix mode가 아니라 block/wait mode라고 enum comment가 명시한다.
5. `rg -n "cancel.*aio|io_cancel|cancel.*I/O|cancel.*IO" storage/innobase/{os,fil,buf}`
   - traced page-write path에서 per-request cancel state machine을 찾지 못했다. 정상 durability seams은 pending writes가 없어질 때까지 wait한다. 이는 “cancel이 절대 없다”는 전역 Claim이 아니라 searched scope의 negative result다.

### Material gaps/unknowns

- MySQL runtime을 금지한 역할이므로 actual writer wait, reader throughput, DWB queue residence, AIO completion latency는 측정하지 않았다.
- compressed-only `BUF_BLOCK_ZIP_DIRTY`의 모든 mutation path와 temporary/intrinsic no-latch path를 완전 추적하지 않았다. main compatibility conclusion은 normal persistent uncompressed frame에 한정한다.
- native AIO의 compression/encryption lower-layer auxiliary block combinations은 대표 path만 확인했다. configuration별 실제 copied bytes를 정량화하지 않았다.
- shutdown 전체 순서를 end-to-end 증명하지 않았다. source에는 `os_aio_wait_until_no_pending_writes()`와 AIO thread wake/free가 있으나, 모든 shutdown mode에서 page-level `SX/io_fix`가 언제 zero가 되는지는 별도 shutdown tracer가 필요하다.
- InnoDB terminal I/O error가 process abort 이후 restart/recovery에서 어떻게 보고/복구되는지는 recovery scope 밖이다. 본 packet은 flush call의 in-memory rollback 부재만 말한다.
- CUBRID `IO_WRITE_FREEZE` fairness, timeout, ordered-fix interaction, completion-thread ownership은 아직 구현되지 않아 unknown이다.

## 12. Contradictions and corrections

### 12.1 `O_DIRECT`와 AIO를 합친 기존 설명은 교정 필요

기존 local artifacts의 다음 설명은 synchronous direct I/O까지 “syscall 반환 후 buffer를 계속 읽는다”고 일반화한다.

- `f799e05_claude/chapters/02-mental-model.html:58`
- `f799e05_claude/chapters/01-orientation.html:33`

이는 frozen scope 및 MySQL source API contract와 충돌한다. 교정 문장은 다음과 같아야 한다.

> synchronous `O_DIRECT`는 page cache를 우회하지만 blocking call return까지 buffer가 안정하면 된다. AIO는 buffered/direct 여부와 별개로 callback/completion까지 buffer lifetime을 요구한다.

### 12.2 “InnoDB flush는 무복사”는 configuration/phase를 붙여야 한다

plain datafile phase가 live frame을 쓰는 것은 맞다. 그러나 regular doublewrite batch는 `Buffer::append()`로 page image를 copy하고, encryption/compression은 `e_block`을 만들 수 있다. 정확한 표현은 다음과 같다.

> InnoDB는 normal plain datafile AIO에서 별도 snapshot을 쓰지 않고 live frame을 SX로 고정하지만, DWB durable stage와 transformed output에는 별도 copy/image가 존재할 수 있다.

### 12.3 InnoDB header consistency comment is stale

`storage/innobase/include/buf0buf.h:2687-2703`의 consistency comment는 `io_fix == BUF_IO_WRITE`일 때 page가 “s-locked”라고 적는다. 그러나 executable code는 `buf_flush_page()`에서 `rw_lock_sx_lock_*`을 호출하고 completion에서 `rw_lock_sx_unlock_gen()`을 호출한다. 이 packet은 executable call path를 authoritative evidence로 택한다. 문서 comment를 근거로 write I/O가 plain S를 잡는다고 쓰면 안 된다.

### 12.4 Error policies are not equivalent

CUBRID current flush failure는 dirty/oldest-unflush-LSA를 복구한다. InnoDB traced ordinary terminal write failure는 fatal assertion이고 stale/deleted만 cleanup한다. 두 엔진의 success path만 보고 “completion에서 동일하게 rollback”한다고 비교하면 틀린다.

## 13. Suggested CUBRID tests/experiments (not executed here)

### T1. Controlled completion compatibility test

mockable write backend가 submit 후 completion을 test thread가 지연시키게 한다.

```text
1. dirty page P를 frame-AIO로 submit하고 completion을 hold한다.
2. reader fix(READ)가 성공해 consistent bytes를 읽는지 확인한다.
3. writer fix/promotion(WRITE)은 completion 전까지 진행하지 못해야 한다.
4. second flush와 victim selection은 P를 거부해야 한다.
5. completion을 release하면 exactly one cleanup 후 writer가 진행해야 한다.
```

oracle: reader allowed, writer blocked, second flusher/victim blocked, completion 후 state zero, stuck waiter 없음.

### T2. Copy-AIO re-dirty test

request-owned snapshot을 submit하고 completion을 hold한다. live frame writer가 새 LSA로 변경/dirty set할 수 있어야 하고, disk sink가 받은 bytes는 original snapshot이어야 한다. completion 후 dirty와 `oldest_unflush_lsa`가 새 modification을 보존해야 한다.

### T3. Stack-lifetime poison test

current `pgbuf_bcb_flush_with_wal()`의 stack `page_buf`를 naive async backend에 넘기는 잘못된 prototype을 ASAN/poison oracle로 재현한다. 함수가 return한 뒤 completion을 지연해 UAF/changed bytes가 검출되어야 한다. 올바른 copy-AIO request-owned buffer에서는 동일 test가 통과해야 한다.

### T4. Exactly-once error/cancel matrix

다음 지점별 failure를 주입한다.

- snapshot allocation
- DWB enqueue/full queue
- AIO submit immediate failure
- datafile completion failure
- tablespace invalidation/stale page
- shutdown drain/timeout

각 경우에 dirty/oldest LSA, `FLUSHING`/`IO_WRITE_FREEZE`, frame ref, waiter wakeup, buffer free가 정확히 한 번 수행되는지 확인한다.

### T5. Synchronous `O_DIRECT` separation test

blocking direct-write shim이 buffer consumption을 call 내부에서 지연하게 한다. `READ`/freeze를 call return까지만 유지해도 bytes가 안정함을 확인하고, return 뒤 즉시 writer를 허용한다. AIO test와 hold interval이 다름을 명시적으로 검증한다.

### T6. DWB/TDE image ownership matrix

plain × TDE × DWB on/off 조합에서 actual submitted pointer가 live frame인지 request image인지 기록한다. 각 image가 completion 전 free/reuse되지 않고 completion 후 leak 없이 해제되는지 확인한다.

### T7. Fairness/performance gate

같은 dirty hot page에 reader/writer/flusher를 배치하고 다음을 측정한다.

- copy bytes/sec와 in-flight copy memory
- writer wait p50/p95/p99/max
- reader throughput/latency
- flush throughput/latency
- second-flush skips, victim skips
- freeze hold time을 queue wait / DWB / kernel I/O로 분해

snapshot-AIO, internal freeze-AIO, public SX-AIO, full WRITE-AIO를 같은 durability oracle로 비교한다. 성능 결론은 이 test 전까지 `UNKNOWN`이다.

### T8. Writer-admission completeness test

plain page를 변경하는 모든 CUBRID path가 `WRITE` latch 또는 새 writer gate를 통과하는지 debug assertion으로 검증한다. recovery, vacuum, allocation metadata, TDE metadata, direct pointer helper를 포함한다. 하나라도 우회하면 internal freeze만으로 live-frame AIO correctness를 주장할 수 없다.

## 14. Handoff notes for the main report writer

- MySQL chapter의 핵심 문장은 “InnoDB는 `SX`를 쓴다”보다 “InnoDB는 `SX + io_fix + callback/pass`로 세 책임을 나눈다”여야 한다.
- comparison table에서 reader/writer/second flusher/victim 네 actor를 한 열에 합치지 말고 별도 열로 둔다.
- doublewrite를 “datafile snapshot”으로 오해하지 않는다. DWB batch copy와 datafile live-frame/e_block phase를 분리한다.
- direct I/O와 AIO의 lifetime timeline을 분리한다. `O_DIRECT`는 비동기의 동의어가 아니다.
- CUBRID current `READ`가 content freeze 후보라는 점과, current thread-holder/fix lifetime 때문에 AIO completion handoff가 별도 문제라는 점을 동시에 적는다.
- 범용 `SX` 도입 권고는 source fact가 아니라 design choice다. 좁은 `IO_WRITE_FREEZE`와 copy-AIO가 같은 invariants를 충족할 수 있음을 보여 주고, 구현/측정 전 성능은 unknown으로 남긴다.

## 2026-08-11 addendum — secondary duplicate와 SX의 비교 한계

- InnoDB non-clustered index는 user secondary fields에 clustered-key columns를 더해 row를 구별한다
  (`dict0dict.cc:3227-3321`). insert는 그 entry를 B-tree leaf record로 넣는다
  (`row0ins.cc:2806-3082`). CUBRID처럼 key 하나가 overflow OID chain head를 갖는 구조가 아니다.
- record 수정 leaf는 `BTR_MODIFY_LEAF = RW_X_LATCH`다. tree/block SX는 structural modification
  coordination에 쓰이며 CUBRID first-fit chain traversal과 동형이 아니다 (`btr0btr.h:64-83`).
- generic rw-lock의 S/SX/X compatibility와 same-thread SX→X escalation은 좁은 partial analogy다. escalation은
  기존 S reader가 빠질 때까지 기다리므로 “즉시 성공”이 아니며, CUBRID에 같은 fairness/admission semantics가
  생긴다는 증거도 아니다 (`sync0rw.cc:55-106,445-507`).

결론적으로 InnoDB는 SX 호환성 참고 사례이고 CUBRID overflow-only SX 성능의 검증 사례는 아니다.
