# Research Packet — PostgreSQL flush/frame stability comparator

- **Role:** PostgreSQL Comparator
- **Topic:** CUBRID flush와 write AIO에서 범용 `SX`가 정말 필요한가 — live frame 안정성, strict `READ`, snapshot copy, 전용 `IO_WRITE_FREEZE` 비교
- **Frozen scope:** `../scope.md`
- **Scope digest (SHA-256):** `db5ba3f0288fbb966ca5a4a832b420e7b5c582b461dc266ceda80a816c410885`
- **PostgreSQL revision:** `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc` (`20devel`, commit time `2026-08-05T11:40:39+02:00`)
- **CUBRID comparison revision:** `f799e05d77d5300c6ea5753b4a6cc7caee6d8912` (commit time `2026-08-06T11:11:22+09:00`)
- **Authored:** `2026-08-11T13:43:52+09:00`
- **Method:** 두 pinned source tree와 해당 PostgreSQL 역사 commit만 읽었다. PostgreSQL 서버는 실행하지 않았다. 두 source tree는 수정하지 않았다.
- **Output boundary:** 이 packet만 작성한다. Book/report/claims/source에는 쓰지 않는다.

## 1. Comparator verdict

짧은 답은 다음과 같다.

1. **필수인 것은 `SX`라는 이름의 공개 latch mode가 아니라, I/O가 실제로 읽는 메모리의 두 불변식이다.**
   - 해당 바이트가 I/O 소비가 끝날 때까지 바뀌지 않는다.
   - 해당 주소의 frame이 그때까지 다른 page로 재사용되지 않는다.
2. PostgreSQL은 live shared-buffer frame을 직접 쓰므로 `pin + SHARE_EXCLUSIVE + BM_IO_IN_PROGRESS`를 사용한다. `SHARE_EXCLUSIVE`는 reader와 공존하지만 hint-bit writer, 일반 writer, 두 번째 flusher를 막는다. 이 계약 덕분에 checksum용 page copy와 `BM_JUST_DIRTIED`를 제거했다.
3. PostgreSQL의 선택을 CUBRID에 이름 그대로 이식할 필요는 없다. **CUBRID의 현행 `READ`는 PostgreSQL의 `SHARE`와 중요한 점에서 다르다.** PostgreSQL `SHARE`는 hint-bit 변경자 `SHARE_EXCLUSIVE`와 호환되므로 frame freeze가 아니지만, CUBRID에는 reader와 공존하는 modifier mode가 없고 모든 정상 변경은 `WRITE` 계약 아래 있으므로 `READ`가 이미 writer를 배제한다.
4. 따라서 CUBRID의 **동기 zero-copy write**에는 `READ` fix를 write 반환까지 유지하는 방법도 내용 불변성과 frame 수명을 제공할 수 있다. 다만 현재 flush는 BCB-internal 작업이고 public fix/holder ownership이 thread에 묶여 있어, 이 방법이 곧 좋은 Interface라는 뜻은 아니다.
5. **frame-based write AIO**에서는 submitter의 stack/fix/thread lifetime을 넘어 completion까지 보호해야 한다. 기존 public `READ` holder를 completion thread로 넘기는 것보다, BCB의 전용 `IO_WRITE_FREEZE`와 I/O-owned reference를 두는 편이 책임이 좁고 오류 복구가 명시적이다. 범용 `SX`도 정확할 수 있으나 유일한 답은 아니다.
6. **copy-based write AIO**는 live frame writer를 막지 않아도 된다. 대신 request-owned output copy가 completion까지 살아 있어야 하고, BCB의 logical flush state/오류 복구 lifetime은 별도로 보호해야 한다.
7. PostgreSQL pinned tree의 buffer write는 아직 AIO가 아니다. 저수준 `PGAIO_OP_WRITEV`와 일부 dormant staging 분기는 존재하지만, `smgrstartwritev`/`mdstartwritev`/`FileStartWriteV`, buffer-write callback과 `pgaio_io_start_writev()` 호출자가 없다. 실제 `FlushBuffer`는 `pg_pwritev()`가 반환할 때까지 호출 thread가 기다린다.
8. 기존 보고서의 “direct I/O는 syscall 반환 후에도 kernel/device가 user buffer를 읽는다”는 표현은 과도하다. **동기 `O_DIRECT`와 AIO는 서로 다른 축이다.** 동기 `O_DIRECT` write의 buffer 안정 구간은 blocking write 호출이 반환할 때까지이고, AIO는 completion까지이다. `O_DIRECT`는 kernel caching 효과를 최소화하도록 요청하는 성격이지 비동기 completion을 뜻하지 않으며, 모든 stack에서 raw-device DMA를 보장한다고 확대해서도 안 된다.

설계상 가장 중요한 분해는 다음과 같다.

```text
내용 불변성          주소/frame 생존          단일 I/O/순서          dirty·오류 상태
content freeze   +  pin/io reference     +  FLUSHING/IO_IN_PROGRESS + completion transition
```

PostgreSQL의 `SHARE_EXCLUSIVE`는 첫 항을, pin/AIO-owned pin은 둘째 항을, `BM_IO_IN_PROGRESS`는 셋째 항을 맡는다. 하나의 “SX latch”가 네 책임을 저절로 모두 제공하는 것은 아니다.

## 2. Source inventory and immutable identities

### PostgreSQL current blobs

| File | Relevant symbols | Blob hash at `fd2b898...` |
|---|---|---|
| `src/include/storage/bufmgr.h` | `BufferLockMode` | `6837b35fc6d0b8a2f016f8604e43ba3415c8ae40` |
| `src/include/storage/buf_internals.h` | lock bits, `BM_IO_IN_PROGRESS`, `BufferDesc.state`, I/O API | `e4ff5619b79ca5f1800a2c36285b6961b01dfc69` |
| `src/backend/storage/buffer/README` | pin/content-lock access rules | `b332e002ba13baabc802930bcc7ace4fa1d09d5c` |
| `src/backend/storage/buffer/bufmgr.c` | `BufferLockAttempt`, `FlushBuffer`, hint-bit helpers, I/O ownership | `169829eb020702062b405c350431cca5dc83f47d` |
| `src/backend/storage/page/bufpage.c` | `PageSetChecksum` | `1fdfda59edd08d91d9dd6eaddb2b5ffdff7a8dc9` |
| `src/include/storage/smgr.h` | inline `smgrwrite` | `09bd42fcf4ba6da5f9650dfa41c1ea285da2ea29` |
| `src/backend/storage/smgr/smgr.c` | `smgrwritev` | `5391640d8613dc87eb13d7f2cd70ac7c7d9dafe5` |
| `src/backend/storage/smgr/md.c` | `_mdfd_open_flags`, `mdwritev`, `mdstartreadv` | `9f96d9cbbfc3e89043bb07dfc2b7f284ac901da9` |
| `src/backend/storage/file/fd.c` | `FileWriteV`, `FileStartReadV`, direct-I/O GUC hook | `190c99744940bc62dfafcfb08c277a10d65b260a` |
| `src/backend/storage/aio/aio_io.c` | `pgaio_io_start_{readv,writev}` | `132868130e7cde86a6d20dc9f25802fabc99b920` |
| `src/include/storage/aio.h` | AIO op/API declarations | `ec543b7840943e2a95ece978fe9689567c2a978d` |
| `doc/src/sgml/config.sgml` | `debug_io_direct` | `236ee067f4005bab17c61423ad827b993514872a` |

### PostgreSQL historical blobs/commits

| Revision | Purpose | Historical blob |
|---|---|---|
| `82467f627bd478569de04f4a3f1993098e80c812^` | SX 적용 직전의 SHARE flush + copy + `BM_JUST_DIRTIED` | `bufmgr.c` `5f3d083e938864701c48482f87b54cfc8c1aefd2` |
| `82467f627bd478569de04f4a3f1993098e80c812` | hint setter와 flush에 `SHARE_EXCLUSIVE` 요구 | commit 자체가 1차 사료 |
| `b0f4ff3c92664e28615e2f885195c803156d47eb` | `BM_JUST_DIRTIED` 제거 | parent `bufmgr.c` `8084858726fddad8ce887c093bd6a7040aa70205` |
| `41d3d64e87af3f16833b095032affe404443659b` | write 시 page copy 제거 | parent `bufmgr.c` `e212f6110f2033f9f63a9d8b58706fbdf512c2c8`; parent `bufpage.c` `de85911e3ac5f1144d84e416b336e19c3c03e31a` |
| `fcb9c977aa5f1eefe7444e423e833ff64a5d1d8f` | buffer content lock을 `BufferDesc.state`에 내장하고 SX 추가 | commit 자체가 1차 사료 |

### CUBRID comparison blobs

| File | Relevant symbols | Blob hash at `f799e05...` |
|---|---|---|
| `src/storage/page_buffer.h` | `PGBUF_LATCH_MODE`, fix/unfix API | `9246370f40a89d274199140a5bd7efa97e6e29d6` |
| `src/storage/page_buffer.c` | strict READ/WRITE, snapshot flush, `FLUSHING_TO_DISK`, victim rules | `369135d519e77d1dbcf7fbcc31c2e58d7ffc2ce7` |
| `src/storage/file_io.c` | blocking page write path | `fe156c0b3ac9d5e3cb9daeaea346447da3fb0af5` |

## 3. Structured source claim candidates

`Evidence state`의 의미는 다음과 같다.

- `VERIFIED_CURRENT`: pinned current source가 직접 보장한다.
- `VERIFIED_HISTORY`: pinned tree가 포함한 과거 commit/parent source가 직접 보장한다.
- `DERIVED`: 둘 이상의 직접 증거를 결합한 설계 해석이다.
- `NEGATIVE_SEARCH`: 명시한 tree 범위에서 symbol/caller가 없음을 검색했다.
- `DOCUMENTED_INTENT`: commit message/TODO가 미래 목적을 말하며 현행 동작 증거로 확대하면 안 된다.

| ID | Candidate claim | Exact source / symbol / lines | Revision / blob hash | Evidence state |
|---|---|---|---|---|
| `PG-SRC-001` | PG `SHARE`는 X만, `SHARE_EXCLUSIVE`는 SX와 X, `EXCLUSIVE`는 모든 mode와 충돌한다. 따라서 SX는 reader를 허용하면서 모든 page modifier와 다른 flusher를 직렬화한다. | `src/include/storage/bufmgr.h:202-223` `BufferLockMode`; `src/backend/storage/buffer/bufmgr.c:6118-6175` `BufferLockAttempt` | `fd2b898...`; blobs `6837b35...`, `169829e...` | `VERIFIED_CURRENT` |
| `PG-SRC-002` | content lock state는 generic LWLock가 아니라 `BufferDesc.state`에 pin/flags와 함께 내장된다. | `src/include/storage/buf_internals.h:76-86`, `:291-310` | `fd2b898...`; `e4ff561...` | `VERIFIED_CURRENT` |
| `PG-SRC-003` | `FlushBuffer`는 caller pin과 SX/X를 요구하고, WAL을 먼저 flush한 뒤 shared frame에 checksum을 제자리 설정하여 같은 `bufBlock`을 `smgrwrite`에 전달한다. 성공 후 dirty와 I/O-in-progress를 끝낸다. | `src/backend/storage/buffer/bufmgr.c:4510-4535`, `:4537-4543`, `:4561-4604`, `:4629-4632` `FlushBuffer` | `fd2b898...`; `169829e...` | `VERIFIED_CURRENT` |
| `PG-SRC-004` | PG에서 content immutability와 single-I/O는 다른 장치다. SX/X가 변경을 막고 `BM_IO_IN_PROGRESS`가 중복 I/O를 막는다. | `bufmgr.c:4587-4592`; `src/include/storage/buf_internals.h:105-116`; `bufmgr.c:7251-7361` `StartSharedBufferIO` | `fd2b898...`; `169829e...`, `e4ff561...` | `VERIFIED_CURRENT` |
| `PG-SRC-005` | pin은 frame/tag 재사용을 막는다. AIO staging은 issuer 오류 처리로 pin이 풀려도 frame이 재사용되지 않도록 AIO subsystem 전용 pin을 추가하고 completion에서 반환한다. | `src/backend/storage/buffer/README:12-26`; `src/include/storage/buf_internals.h:291-301`; `bufmgr.c:8315-8430` `buffer_stage_common`; `:8695-8700` read completion | `fd2b898...`; `b332e00...`, `e4ff561...`, `169829e...` | `VERIFIED_CURRENT` |
| `PG-SRC-006` | 일반 변경은 X가 필요하고, hint-bit 변경은 SX/X가 필요하다. SHARE holder는 조건부로 SX로 upgrade하며 다른 SX/X가 있으면 false로 포기한다. 따라서 flush SX와 hint setter SX가 상호 배타다. | `bufmgr.c:3161-3207` `MarkBufferDirty`; `:6991-7058` `SharedBufferBeginSetHintBits`; `:7061-7108`, `:7110-7175` public helpers | `fd2b898...`; `169829e...` | `VERIFIED_CURRENT` |
| `PG-HIST-001` | SX 직전 PG flush는 SHARE만 보유했고 hint bit가 I/O 중 바뀔 수 있었다. checksum 시 `PageSetChecksumCopy`를 사용하고 `BM_JUST_DIRTIED`로 I/O 중 재오염을 구별했다. | revision `82467f627bd^`, `src/backend/storage/buffer/bufmgr.c:4398-4412`, `:4452-4463`, `:4491-4509`, `:4534-4538`; `FlushBuffer` | `82467f627bd^`; `5f3d083...` | `VERIFIED_HISTORY` |
| `PG-HIST-002` | `BM_JUST_DIRTIED`는 SX가 flush 중 redirty를 불가능하게 만들었기 때문에 제거됐다. current bit 6은 unused이고 successful write는 dirty를 조건 없이 clear할 수 있다. | commit `b0f4ff3c926...`; current `src/include/storage/buf_internals.h:105-119`; `bufmgr.c:7388-7424` `TerminateBufferIO` | historical commit + current blobs `e4ff561...`, `169829e...` | `VERIFIED_HISTORY` |
| `PG-HIST-003` | page snapshot copy는 hint bit가 I/O 중 바뀌지 않게 된 뒤 제거됐다. current `PageSetChecksum`은 shared frame을 제자리 변경한다. | commit `41d3d64e87a...`; parent `src/backend/storage/page/bufpage.c:1494-1532` `PageSetChecksumCopy`; current `bufpage.c:1504-1529` `PageSetChecksum` | historical parent blob `de85911...`; current `1fdfda5...` | `VERIFIED_HISTORY` |
| `PG-SRC-007` | current buffer write call path는 AIO submission이 아니라 blocking `pg_pwritev`이다. `smgrwritev` 주석의 “not synchronous”는 storage durability가 아직 보장되지 않는다는 뜻이지 user-buffer consumption이 submit 뒤로 남는다는 뜻이 아니다. | `src/include/storage/smgr.h:123-135`; `src/backend/storage/smgr/smgr.c:764-798`; `src/backend/storage/smgr/md.c:1063-1121`; `src/backend/storage/file/fd.c:2230-2281` | `fd2b898...`; blobs `09bd42f...`, `5391640...`, `9f96d9c...`, `190c997...` | `VERIFIED_CURRENT` |
| `PG-SRC-008` | direct data I/O는 `debug_io_direct=data`로 켤 수 있지만 기본 off이며 developer testing 전용이다. 파일은 `PG_O_DIRECT`로 열려도 buffer write path는 여전히 `FileWriteV -> pg_pwritev`이다. | `doc/src/sgml/config.sgml:12816-12845`; `src/backend/storage/smgr/md.c:175-184`; `md.c:1063-1121`; `fd.c:2230-2281` | `fd2b898...`; `236ee06...`, `9f96d9c...`, `190c997...` | `VERIFIED_CURRENT` |
| `PG-NEG-001` | current tree에는 buffer write AIO producer/completion path가 없다. 저수준 `pgaio_io_start_writev` 정의는 있지만 호출자가 없고, buffer callbacks는 read만 등록한다. | definition `src/backend/storage/aio/aio_io.c:90-101`; declaration `src/include/storage/aio.h:299-302`; only `buffer_stage_common(... false, ...)` call sites `bufmgr.c:8922-8926`, `:8973-8977`; `bufmgr.c:6705-6710`도 AIO read-only라고 명시 | `fd2b898...`; blobs `1328681...`, `ec543b7...`, `169829e...` | `NEGATIVE_SEARCH` |
| `PG-INTENT-001` | low-level `PGAIO_OP_WRITEV`와 dormant `is_write` staging/lock-disown 분기는 향후 write AIO를 위한 준비이지만 현행 기능 증거가 아니다. | `aio_io.c:90-101`; `bufmgr.c:8315-8430`; `bufmgr.c:6285-6319` `BufferLockDisown`; commit `fcb9c977aa5...` | `fd2b898...` + historical commit | `DOCUMENTED_INTENT` |
| `CUB-CMP-001` | CUBRID public fix는 READ/WRITE만 허용한다. READ/READ는 공존하고 그 밖의 신규 holder는 직렬화되며, dirty 표시는 WRITE latch를 assert한다. 이 조합이 “strict READ” 계약의 핵심이다. | `src/storage/page_buffer.h:189-197`; `src/storage/page_buffer.c:2285-2289`; `:6277-6315`, `:6374-6424` `pgbuf_latch_bcb_upon_fix`; `:11657-11669` `pgbuf_set_dirty_buffer_ptr` | `f799e05...`; blobs `9246370...`, `369135d...` | `VERIFIED_CURRENT` |
| `CUB-CMP-002` | CUBRID flush는 READ/no-latch 상태에서 허용되고 WRITE holder와는 겹치지 않는다. BCB mutex 아래 plain copy 또는 TDE output image를 만든 뒤 mutex를 풀고 WAL flush 및 blocking `fileio_write`를 한다. live writer는 그 뒤 새 DIRTY를 세울 수 있다. | `page_buffer.c:8839-8879` `pgbuf_bcb_safe_flush_internal`; `:10723-10848`, `:10868-10923`, `:10942-10961` `pgbuf_bcb_flush_with_wal`; `:16077-16125` flushing transitions | `f799e05...`; `369135d...` | `VERIFIED_CURRENT` |
| `CUB-CMP-003` | CUBRID `FLUSHING_TO_DISK`는 단일 flush와 victim 금지를 맡지만 writer 배제를 맡지 않는다. 즉 current copy가 content immutability 문제를 제거하고, flag는 BCB lifecycle을 보호한다. | `page_buffer.c:222-262`; `:8839-8879`; `:9287-9312` `pgbuf_is_bcb_victimizable`; `:16077-16137` | `f799e05...`; `369135d...` | `DERIVED` |
| `CMP-DER-001` | CUBRID의 strict `READ` fix를 동기 live-frame write 반환까지 유지하면 내용 불변과 frame 미재사용을 제공할 수 있다. 그러나 현행 flush가 public fix holder 없이 동작하고 holder/unfix가 thread-owned이므로 AIO completion ownership에는 그대로 맞지 않는다. | strict READ evidence `CUB-CMP-001`; holder `page_buffer.c:460-465`; `pgbuf_unfix` `:3062-3110`, `:3161-3169`; victim/fix `:9255-9312` | `f799e05...`; `369135d...` | `DERIVED` |
| `CMP-DER-002` | CUBRID frame-based AIO에 필요한 최소 상태는 “reader 허용, writer/두 번째 flusher 금지, frame 재사용 금지, completion release”이다. 이것은 범용 public SX가 아니라 BCB-internal `IO_WRITE_FREEZE + I/O ref`로도 정확히 표현된다. | PG responsibility split `PG-SRC-003`~`005`; CUBRID current state split `CUB-CMP-002`~`003` | both pinned revisions | `DERIVED` |

## 4. PostgreSQL responsibility reconstruction

### 4.1 Content compatibility is not lifetime ownership

현재 PG의 호환 행렬은 다음과 같다.

| Held \ Request | SHARE | SHARE_EXCLUSIVE | EXCLUSIVE |
|---|---:|---:|---:|
| SHARE | allow | allow | block |
| SHARE_EXCLUSIVE | allow | block | block |
| EXCLUSIVE | block | block | block |

`BufferLockAttempt()`가 이를 직접 구현한다.

- X request: `BM_LOCK_MASK == 0`일 때만 grant (`bufmgr.c:6137-6142`).
- SX request: X와 SX bit가 모두 없을 때 grant (`:6143-6148`). SHARE count는 무시하므로 readers와 공존한다.
- SHARE request: X bit만 없으면 grant (`:6149-6154`). 따라서 이미 SX가 있어도 reader는 들어간다.

여기서 두 가지를 분리해야 한다.

- **SX content lock:** live page bytes와 LSN이 바뀌지 않게 한다.
- **pin:** buffer tag/frame이 다른 page로 재사용되지 않게 한다.
- **`BM_IO_IN_PROGRESS`:** 한 buffer에 두 writer I/O가 동시에 시작되지 않게 하고 waiter가 completion을 관찰하게 한다.

SX만 있고 pin이 없다면 주소 lifetime이 없다. pin만 있고 SX가 없다면 주소는 살아 있어도 내용이 바뀔 수 있다. `BM_IO_IN_PROGRESS`만으로도 content writer는 막히지 않는다. PostgreSQL이 세 장치를 같이 쓰는 이유다.

### 4.2 Current synchronous live-frame flush path

대표 bgwriter/checkpointer path:

```text
BgBufferSync / CheckPointBuffers
  -> SyncOneBuffer
     -> PinBuffer_Locked
     -> FlushUnlockedBuffer
        -> BufferLockAcquire(SHARE_EXCLUSIVE)
        -> FlushBuffer
           -> StartSharedBufferIO(output, wait=true)
           -> BufferGetLSN
           -> XLogFlush(page LSN)          # WAL-before-data
           -> PageSetChecksum(bufBlock)    # live frame, in place
           -> smgrwrite(bufBlock)
              -> smgrwritev
                 -> mdwritev
                    -> FileWriteV
                       -> pg_pwritev        # calling thread waits for syscall return
           -> TerminateBufferIO(clear_dirty=true)
        -> BufferLockUnlock
     -> UnpinBuffer
```

근거는 `SyncOneBuffer` `bufmgr.c:4137-4211`, `FlushUnlockedBuffer` `:4644-4656`, `FlushBuffer` `:4510-4642`, `smgr.h:123-135`, `smgr.c:764-798`, `md.c:1063-1121`, `fd.c:2230-2281`이다.

victim path는 wait 대신 조건부 SX를 쓴다.

```text
GetVictimBuffer
  -> candidate already pinned by this backend
  -> BufferLockConditional(SHARE_EXCLUSIVE)
     failure: unpin and choose another victim
     success:
       -> FlushBuffer
       -> unlock content lock
       -> InvalidateVictimBuffer rechecks sole pin + clean
```

`bufmgr.c:2565-2638`이 conditional acquisition의 deadlock 회피 이유를 설명하고, `InvalidateVictimBuffer` `:2462-2544`는 최종 refcount/dirty 재검사를 수행한다.

### 4.3 Hint bits explain why PG needs SX where CUBRID READ may suffice

일반 PG page 변경은 X가 필요하다(`MarkBufferDirty`, `bufmgr.c:3161-3188`). 그러나 hint bit는 reader가 얻은 visibility 결과를 page에 cache하는 비핵심 변경이므로 reader와 공존하는 SX로 변경할 수 있다(`README:63-81`).

SHARE holder가 hint를 쓰려 하면:

```text
SHARE scan
  -> BufferBeginSetHintBits / BufferSetHintBits16
     -> if already SX/X: proceed
     -> else atomic SHARE -> SX upgrade
        if another SX/X exists: return false, skip hint
        else: modify hint + mark dirty
```

flush 역시 SX이므로 hint setter와 flush가 동시에 존재하지 않는다. 다만 ordinary SHARE readers는 둘 모두와 공존한다. 과거에는 hint setter가 SHARE 아래에서 직접 수정했으므로 flush SHARE가 이를 막지 못했고, checksum copy가 필요했다.

### 4.4 Copy and `BM_JUST_DIRTIED` were one coherent old protocol

SX 적용 직전 `82467f627bd^`의 `FlushBuffer`는 다음 protocol이었다.

1. caller는 pin + SHARE를 보유한다(`bufmgr.c@82467f^:4408-4412`).
2. I/O 시작 시 `BM_JUST_DIRTIED`를 clear한다(`:4452-4463`).
3. hint setter가 SHARE와 공존하므로 checksum이 깨지지 않게 `PageSetChecksumCopy`를 만든다(`:4491-4509`).
4. I/O 중 누군가 page를 다시 dirty하면 `BM_JUST_DIRTIED`가 set된다.
5. 성공 completion은 “just dirtied가 아니라면” clean으로 만든다(`:4534-4538`).

이 protocol의 두 장치는 다른 문제를 푼다.

- **snapshot copy:** 실제 write bytes를 안정화한다.
- **`BM_JUST_DIRTIED`:** old snapshot을 쓰는 동안 live page에 생긴 새 변경을 잃지 않게 한다.

`82467f627bd`가 hint setter와 flush를 SX로 상호 배제한 뒤, concurrent redirty가 불가능해져 `b0f4ff3c926`이 `BM_JUST_DIRTIED`를 제거했다. 이어 `41d3d64e87a`가 copy를 제거했다. 즉 “SX 한 줄 추가”가 아니라 mutation contract, dirty state machine, checksum API가 함께 바뀐 migration이다.

### 4.5 Current write AIO status: prepared substrate, no buffer-write path

현재 상태를 “AIO write가 있다/없다” 한 단어로 말하면 오해가 생긴다.

있는 것:

- `PGAIO_OP_WRITEV` op type과 sync/io_uring execution substrate.
- `pgaio_io_start_writev()` 정의 (`aio_io.c:90-101`).
- `buffer_stage_common(ioh, is_write, ...)`의 write branch. 이 branch는 AIO-owned pin을 추가하고 content lock ownership을 current backend에서 떼어낸다 (`bufmgr.c:8315-8430`). 이는 completion이 다른 process/backend에서 일어나도 issuer 오류 정리가 frame/lock을 풀지 않게 하기 위한 준비다.
- `fcb9c977aa5` commit의 documented intent: content lock과 I/O state를 같은 atomic word에서 보아 write AIO race를 풀기 쉽게 한다.

없는 것:

- `smgrstartwritev`, `mdstartwritev`, `FileStartWriteV` symbol.
- `pgaio_io_start_writev()` 호출자.
- shared/local buffer write completion callback과 callback registration.
- `buffer_stage_common(..., true, ...)` 호출자. current 두 call site는 모두 `false`인 read path다 (`bufmgr.c:8922-8926`, `:8973-8977`).

코드 자체도 `LockBufferForCleanup`에서 “so far, only support doing reads via AIO”라고 명시한다(`bufmgr.c:6705-6710`). 정확한 결론은 **저수준 write op와 일부 lifetime handoff 골격은 있으나, in-tree async buffer write producer/completion protocol은 아직 없다**이다.

### 4.6 Direct I/O is present but does not imply async write

`debug_io_direct=data`를 설정하면 md relation file open flags에 `PG_O_DIRECT`가 붙는다(`md.c:175-184`). 이 GUC는 기본 off이고 현재 성능을 떨어뜨려 developer testing 전용이다(`config.sgml:12816-12845`). 그러나 write call path는 달라지지 않는다.

```text
O_DIRECT file
  -> FlushBuffer
  -> smgrwrite / mdwritev
  -> FileWriteV
  -> pg_pwritev (blocking call)
```

여기서 `smgrwritev` 주석의 “This is not a synchronous write” (`smgr.c:771-773`)는 데이터가 stable storage에 durable하다는 뜻의 synchronous가 아니라는 말이다. syscall 반환 후에도 checkpoint 전 fsync가 필요하다. 이것을 AIO submission semantics와 혼동하면 안 된다.

```text
buffer consumption completion  !=  durability completion

blocking buffered write: user buffer는 syscall 반환까지 안정, durability는 뒤의 fsync
blocking O_DIRECT write: user buffer는 syscall 반환까지 안정, durability는 O_SYNC/O_DSYNC/fsync 계약에 따름
AIO write: request buffer는 submit 반환이 아니라 completion까지 안정, durability는 별도 계약
```

`82467f627bd` commit message도 두 문제를 구별한다.

- AIO: in-flight page마다 copy가 필요하고 worker mode에서는 shared-memory copy가 필요하다.
- direct I/O, independent of AIO: **write가 진행되는 동안** source data가 바뀌면 일부 filesystem/RAID의 내부 checksum이 깨질 수 있다.

commit은 synchronous `O_DIRECT` syscall이 반환한 뒤에도 user buffer를 읽는다고 말하지 않는다.

## 5. Semantic mismatches with CUBRID strict READ

### 5.1 Same word “READ/SHARE”, different freeze power

| Property | PostgreSQL `SHARE` | CUBRID `PGBUF_LATCH_READ` |
|---|---|---|
| Other readers | 허용 | 허용 |
| Ordinary full writer | X와 충돌하여 금지 | WRITE와 충돌하여 금지 |
| Reader-compatible modifier | PG SX hint setter와 **호환** | 현행 mode set에는 없음 |
| As a flush freeze by itself | 불충분: SX hint setter가 바꿀 수 있음 | 정상 변경이 모두 WRITE라면 내용 불변 제공 |
| Frame reuse prevention | 별도 pin 필요 | fix count 또는 별도 BCB I/O 상태 필요 |

PostgreSQL `SHARE_EXCLUSIVE`가 필요했던 직접 원인은 “SHARE 아래 변경을 허용하던 hint-bit 예외”다. CUBRID에서는 `pgbuf_set_dirty_buffer_ptr()`가 global latch mode `WRITE`를 assert하고 (`page_buffer.c:11657-11669`), safe flush는 `NO_LATCH`/`READ`만 즉시 허용하며 다른 thread의 `WRITE`는 기다린다 (`:8839-8879`). 그래서 CUBRID strict READ와 PG SHARE를 단순 동형으로 취급하면 안 된다.

단, 이 packet은 CUBRID 전 page-type의 모든 raw memory write callsite를 전수 감사하지 않았다. “strict READ”는 page-buffer API와 dirty protocol이 요구하는 계약이며, READ 아래 몰래 쓰는 bug까지 불가능하다고 증명하는 의미는 아니다.

### 5.2 Current CUBRID snapshot protocol

현행 CUBRID는 BCB mutex 아래에서 다음을 한다.

1. `FLUSHING_TO_DISK`를 set하고 기존 DIRTY를 clear한다 (`page_buffer.c:10801`, `:16077-16099`).
2. TDE page는 encrypted output image를 만들고, plain page는 stack-aligned `page_buf`에 `IO_PAGESIZE`를 `memcpy`한다 (`:10735-10749`, `:10805-10821`).
3. DWB가 있으면 DWB slot로 image ownership을 넘길 수 있다 (`:10822-10834`).
4. page LSA와 `oldest_unflush_lsa`를 snapshot하고 BCB mutex를 푼다 (`:10836-10842`).
5. WAL을 먼저 flush한다 (`:10844-10849`).
6. DWB 또는 `fileio_write`에 output image를 보낸다 (`:10868-10899`). Linux server release path의 `fileio_write -> fileio_os_write -> pwrite`는 call이 반환될 때까지 기다린다 (`file_io.c:4062-4119`, `:4122-4181`).
7. 실패하면 old dirty/oldest LSA를 복구하고 waiter를 깨운다 (`page_buffer.c:10908-10923`). 성공이면 `FLUSHING_TO_DISK`를 clear한다 (`:10942-10951`).

DIRTY를 먼저 clear하기 때문에 copy 뒤에 들어온 writer가 DIRTY를 다시 set한다. 성공 completion은 `FLUSHING_TO_DISK`만 clear하므로 새 DIRTY는 남는다. PostgreSQL의 옛 `BM_JUST_DIRTIED`와 목적은 비슷하지만 CUBRID는 “DIRTY clear 후 새 DIRTY set”으로 세대를 구별한다.

`FLUSHING_TO_DISK`는 `PGBUF_BCB_INVALID_VICTIM_CANDIDATE_MASK`에 포함돼 victim을 막고 (`page_buffer.c:253-262`), safe flush에서 second flusher를 막는다 (`:8839-8847`). 그러나 flag 자체가 WRITE latch acquisition을 막지는 않는다. live frame이 아니라 copy를 쓰므로 그럴 필요가 없었다.

### 5.3 Why an existing READ can be sufficient for synchronous zero-copy

동기 live-frame write의 필요한 구간은 `fileio_write()` 반환까지다. 그 구간 동안 flush owner가 다음을 유지한다고 가정한다.

```text
CUBRID READ fix held
  -> readers allowed
  -> WRITE latch acquisition blocked
  -> fix count > 0, so ordinary victimization blocked
  -> blocking write returns
  -> unfix/release by same thread
```

이 조건이면 bytes와 address 두 불변식이 모두 성립할 수 있다. 그러므로 **“동기 zero-copy를 위해 새 SX가 반드시 필요하다”는 결론은 성립하지 않는다.**

그러나 이것은 구현 권고와 동일하지 않다.

- current flush는 이미 찾은 BCB를 내부적으로 처리하며 public `pgbuf_fix()` caller처럼 holder를 만들지 않는다.
- `PGBUF_HOLDER`는 thread holder list에 연결되고 (`page_buffer.c:460-465`), `pgbuf_unfix(thread_p, page)`는 해당 thread의 holder를 찾아 해제한다 (`:3062-3110`, `:3161-3169`).
- flush 전체 동안 public READ latch를 오래 잡으면 existing waiter fairness와 holder accounting에 I/O lifetime을 끼워 넣는다.
- TDE/DWB는 anyway 별도 output image가 필요한 경우가 있어 live-frame zero-copy의 적용 범위가 제한된다.

따라서 sync-only prototype에서는 READ+fix가 정확성 baseline이 될 수 있지만, production boundary는 전용 internal state와 비교해야 한다.

### 5.4 Why READ holder alone is awkward for frame AIO

AIO에서는 submit call이 끝나도 request가 frame을 계속 읽는다. issuer thread가 다음 중 하나를 할 수 있다.

- 정상적으로 query를 계속하고 page를 unfix한다.
- ERROR/interrupt로 resource cleanup을 한다.
- 다른 backend/worker가 completion callback을 실행한다.

READ holder가 issuer thread 소유라면 completion까지 유지하려면 “disown/transfer/reown 없이 타 thread가 어떻게 release하는가”라는 새 계약이 필요하다. PostgreSQL의 dormant write staging이 content lock을 `BufferLockDisown()`하고 AIO-owned pin을 별도로 추가하는 이유가 바로 이 lifetime handoff다 (`bufmgr.c:6285-6319`, `:8315-8430`).

CUBRID에서는 다음처럼 BCB-internal request ownership을 두는 편이 더 직접적이다.

```text
prepare under BCB mutex
  -> set IO_WRITE_FREEZE + FLUSHING
  -> capture page LSA / oldest_unflush_lsa
  -> acquire io_ref owned by request, not issuer thread
  -> release BCB mutex
  -> WAL-before-data
  -> submit live frame

completion (any permitted thread)
  -> on success: clean generation / clear freeze+flushing
  -> on error: restore dirty/oldest LSA / clear freeze+flushing
  -> release io_ref
  -> wake writer, second flusher, victim waiter
```

`IO_WRITE_FREEZE` acquire 후에는 reader는 들어가도 되지만 WRITE latch grant는 막혀야 한다. second flusher는 join/wait/skip 중 하나의 명시된 policy를 따라야 한다. victim은 I/O-owned ref 또는 freeze flag 때문에 거절돼야 한다.

## 6. Responsibility-equivalence table

| Design | I/O buffer | Stable until | Reader | Writer | Second flusher | Victim/reuse | Assessment |
|---|---|---|---|---|---|---|---|
| CUBRID current sync snapshot | stack/TDE/DWB output copy | blocking call/DWB ownership 종료 | allow | copy 뒤 allow | `FLUSHING`으로 block/join | `FLUSHING`으로 금지 | current baseline; copy cost, writer concurrency 좋음 |
| PostgreSQL current sync live frame | shared frame | `pg_pwritev` return | allow via SHARE+SX coexistence | block | SX + `BM_IO_IN_PROGRESS` | pin | verified no-copy precedent |
| CUBRID sync live frame + READ fix | live frame | blocking write return | allow | block | 별도 `FLUSHING` 필요 | fix count/flag | correctness candidate; public holder seam이 어색할 수 있음 |
| CUBRID copy-based AIO | request-owned copy | completion | allow | allow | logical generation/state 필요 | frame은 재사용 가능해도 BCB completion metadata lifetime은 보호 필요 | SX 불필요; in-flight memory pressure 증가 |
| CUBRID frame AIO + public READ | live frame | completion | allow | block | 별도 I/O state | transferred fix/ref 필요 | ownership transfer를 새로 설계해야 함 |
| CUBRID frame AIO + general SX | live frame | completion | allow | block | SX self-conflict | pin/io ref 필요 | 정확할 수 있으나 public latch surface 확대 |
| CUBRID frame AIO + `IO_WRITE_FREEZE` | live frame | completion | allow | block via internal grant check | freeze self-conflict | request-owned io ref/freeze | flush 책임에 가장 좁은 후보 |
| CUBRID frame AIO + WRITE | live frame | completion | block | block | block | fix/ref | 정확하지만 긴 I/O 동안 reader까지 막아 과도함 |

“Equivalent” 판정은 mode 이름이 아니라 다음 responsibility tuple로 해야 한다.

```text
(reader allowed,
 modifier blocked,
 single flush,
 frame cannot be reused,
 completion can release ownership,
 dirty/error generation is preserved)
```

PG의 `(SX, BM_IO_IN_PROGRESS, pin/AIO pin)`과 제안 CUBRID의 `(IO_WRITE_FREEZE, FLUSHING, io_ref)`는 이 tuple에서는 equivalent가 될 수 있다. CUBRID current `(snapshot copy, FLUSHING)`은 bytes 안정성을 copy가 대신하므로 partial analogy다.

## 7. Corrections to overbroad prior statements

### Correction A — `O_DIRECT` does not mean asynchronous completion

기존 표현:

> direct I/O/AIO는 시스템콜 반환 후에도 kernel/device가 사용자 버퍼를 읽는다.

교정:

> AIO는 submission 반환 후 completion까지 request buffer를 유지해야 한다. 동기 `O_DIRECT` write는 cache-bypass와 alignment 성격을 바꾸지만 호출 자체는 blocking일 수 있으며, 이 경우 buffer는 write 호출이 반환할 때까지만 변경하지 않으면 된다. directness와 asynchrony는 독립 축이다.

PG current source가 이를 실증한다. relation file에 `PG_O_DIRECT`가 붙어도 `FlushBuffer -> FileWriteV -> pg_pwritev`의 blocking path를 그대로 쓴다. PG migration commit도 direct-I/O 문제를 “during the write”의 concurrent mutation으로 기술한다.

또한 “`O_DIRECT`이면 user buffer에서 장치로 반드시 직접 DMA하고 어떤 cache/copy도 없다”는 표현도 피해야 한다. PG 공식 설정 문구 자체가 direct I/O를 “ask the kernel to minimize caching effects”라고 제한해서 설명하고, Unix `O_DIRECT`, macOS `F_NOCACHE`, Windows `FILE_FLAG_NO_BUFFERING`을 platform별 대응물로 둔다 (`config.sgml:12816-12840`). 이 packet에서 보장할 수 있는 것은 PG가 aligned shared frame을 direct-data file의 blocking write 입력으로 사용한다는 사실이지, 모든 filesystem/device stack의 물리 DMA 경로가 동일하다는 주장이 아니다.

### Correction B — AIO/direct I/O requires stability, not necessarily SX

기존 표현:

> AIO/direct I/O write ⇒ SX 등가 latch 또는 사본, 둘뿐이다.

교정:

> I/O가 읽는 메모리의 안정성과 lifetime이 필요하다. 가능한 수단에는 request-owned copy, existing strict READ+transferred ref, general SX, dedicated I/O freeze, 과도하지만 WRITE latch도 포함된다.

특히 CUBRID strict READ가 PG SHARE보다 강한 freeze power를 갖는다는 점 때문에 “PG가 SX를 썼으니 CUBRID도 SX만 가능”이라는 유추는 성립하지 않는다.

### Correction C — PG current write AIO must not be claimed

PG는 AIO read와 저수준 WRITEV substrate를 갖고 있고 share-exclusive migration은 미래 write AIO를 준비한다. 그러나 pinned revision에서 buffer writes는 blocking `pg_pwritev`이다. `pgaio_io_start_writev()`의 정의만 보고 current write AIO라고 서술하면 안 된다.

### Correction D — “system call return” and “durable” are different

buffered `pwritev` 반환은 kernel이 user buffer를 더 소비하지 않는 경계로 쓸 수 있지만 datafile durability는 아니다. PG는 이후 checkpoint의 fsync를 요구한다 (`FlushBuffer:4513-4517`, `smgrwritev:771-780`). `O_DIRECT`도 `O_SYNC`/`O_DSYNC`가 없으면 stable storage completion을 자동 보장한다는 뜻이 아니다. frame latch lifetime과 WAL/checkpoint durability lifetime을 섞지 말아야 한다.

## 8. Contradictions and stale text found

1. **PostgreSQL README internal contradiction:** `src/backend/storage/buffer/README:157-160`은 각 buffer header가 content-lock LWLock를 가진다고 아직 말한다. current authoritative implementation은 `buf_internals.h:303-310`과 `BufferLockAttempt()`이며 content lock은 `BufferDesc.state` 내 전용 bit/count다. `fcb9c977aa5` commit도 LWLock 제거를 명시한다. 보고서에서는 stale README 문장을 구현 근거로 사용하지 말아야 한다.
2. **“No current direct I/O”라고 쓰면 부정확:** PG에는 developer-only `debug_io_direct=data`가 있다. 정확한 표현은 “기본 off이고 developer testing 전용이며, current buffer write는 direct 설정에서도 blocking”이다.
3. **“CUBRID에는 AIO symbol이 전혀 없다”도 너무 넓다:** HPUX non-IA64 compatibility `pwrite()` wrapper는 POSIX `aio_write` 후 즉시 `aio_suspend`하여 completion을 기다린다 (`file_io.c:3731-3812`). 이것은 page-buffer 관점의 in-flight asynchronous ownership을 제공하지 않는 synchronous wrapper다. Linux server release path는 plain `pwrite`다 (`:4113-4118`).
4. **CUBRID `PGBUF_BCB_ASYNC_FLUSH_REQ`는 asynchronous device I/O가 아니다:** WRITE holder에게 나중에 flush하도록 요청하는 BCB scheduling flag다 (`page_buffer.c:8839-8897`, `:6860-6875`). 이를 write AIO 증거로 읽으면 안 된다.
5. **PG `smgrwritev`의 “not synchronous” 주석은 AIO 의미가 아니다:** 같은 call path가 `pg_pwritev`를 직접 호출한다. 주석은 return 시 stable storage durability가 아직 없다는 뜻이다.

## 9. Negative searches

### PostgreSQL `fd2b898...`

- `BM_JUST_DIRTIED`: current `src/`에서 0건. `buf_internals.h:117`의 “flag bit 6 is not used anymore”만 흔적이다.
- `PageSetChecksumCopy`: current `src/`에서 0건.
- `smgrstartwritev`, `mdstartwritev`, `FileStartWriteV`: tree 전체 0건.
- `pgaio_io_start_writev`: 선언 1건 + 정의 1건, 호출 0건.
- `buffer_stage_common(..., true, ...)`: 0건. 두 caller는 read용 `false`.
- buffer-write AIO completion callback registration: 0건. current registered shared/local buffer callbacks는 readv뿐이다.

### CUBRID `f799e05...`

- `O_DIRECT`: `src/storage`, `src/transaction`, `src/base` C/C++ source에서 0건.
- `io_uring`: 같은 범위 0건.
- page-buffer write submission/completion object: 확인되지 않음.
- `aio_write`: HPUX compatibility wrapper에만 있고 같은 함수에서 `aio_suspend`로 즉시 completion을 기다린다.

Negative search는 out-of-tree patch, 지원되지 않은 platform code, 미래 branch 부재를 증명하지 않는다.

## 10. Unknowns and boundaries

- PostgreSQL write AIO가 어느 release/commit에 완성될지, 어떤 completion/error protocol을 최종 채택할지는 unknown이다.
- dormant `buffer_stage_common(is_write=true)`는 lock을 disown하지만 이 revision에는 대응 write completion release path가 없으므로 완성된 design으로 해석할 수 없다.
- CUBRID `IO_WRITE_FREEZE`의 bit layout, owner token, wait queue fairness, cancellation semantics는 미결정이다.
- CUBRID의 모든 page mutation callsite가 strict READ 계약을 지키는지는 이 packet에서 전수 감사하지 않았다.
- TDE output은 encryption 때문에 별도 image가 필요하다. DWB slot lifetime과 final datafile write 사이 ownership은 해당 packet의 상세 분석이 필요하다. “plain page zero-copy”의 이득을 TDE/DWB 전체에 일반화할 수 없다.
- copy-based AIO와 frame-based AIO의 실제 CPU/throughput/fairness 차이는 측정 전 unknown이다.
- synchronous direct I/O의 filesystem/RAID별 behavior, alignment, partial-write behavior는 이 source-only 비교로 일반화하지 않는다.
- PG의 current developer direct I/O가 production suitability를 뜻하지 않는다. 문서가 오히려 현재 성능 저하와 testing-only를 명시한다.

## 11. Suggested CUBRID tests (no PostgreSQL runtime)

아래는 구현 전 contract test 또는 prototype acceptance test 후보다. PG 서버 실행은 필요하지 않다.

### T1. Synchronous live-frame freeze

- dirty plain page P를 준비한다.
- flusher가 READ+fix 또는 `IO_WRITE_FREEZE`를 잡고 blocking write hook에서 멈춘다.
- R은 동일 page READ를 성공해야 한다.
- W의 WRITE 획득은 write hook release 전까지 성공하면 안 된다.
- victimizer는 P frame을 재사용하면 안 된다.
- write 반환 뒤 freeze/ref를 풀면 W가 진행해야 한다.
- captured bytes/checksum/LSA가 write 시작 시 image와 일치해야 한다.

목적: “reader 허용 + writer 금지 + frame 생존”을 general SX 없이도 만들 수 있는지 검증한다.

### T2. Copy-based AIO redirty generation

- BCB mutex 아래 output copy와 LSA generation을 만든 뒤 AIO submit을 멈춘다.
- live P를 W가 변경하고 새 DIRTY/oldest LSA를 세운다.
- old-copy completion success가 새 DIRTY/oldest LSA를 clear하면 실패다.
- old-copy failure는 old generation의 dirty obligation을 복원하되 새 generation을 덮어쓰면 안 된다.

목적: copy가 content concurrency를 허용해도 logical completion state는 generation-aware여야 함을 검증한다.

### T3. Frame AIO issuer-abort lifetime

- issuer가 live P를 submit한 직후 강제 ERROR/interrupt cleanup으로 자신의 normal fix/holder를 모두 해제한다.
- completion 전 P frame 주소/tag가 유지돼야 하고 W/victim이 접근하지 못해야 한다.
- 다른 completion thread가 success/error transition과 wakeup을 완료해야 한다.

목적: request-owned `io_ref`와 thread-owned holder를 구별한다.

### T4. Single flusher and completion ordering

- F1 old generation을 submit하고 completion을 지연한다.
- F2가 같은 BCB flush를 시도한다.
- policy가 wait/join/skip 중 무엇이든 old/new disk write가 역순으로 clean state를 확정하면 안 된다.
- F1 completion이 늦게 와도 F2가 표현하는 더 새 변경을 clean으로 잘못 지우면 안 된다.

목적: `FLUSHING`/freeze가 content latch와 별개로 필요한 이유를 검증한다.

### T5. Write error rollback and wakeup

- WAL flush success 후 data write completion을 failure로 만든다.
- DIRTY와 `oldest_unflush_lsa`가 복구돼야 한다.
- freeze/flushing/io_ref가 정확히 한 번 해제돼야 한다.
- 대기 중 reader/writer/flusher/victim 중 policy상 깨어나야 할 대상이 모두 깨어나야 한다.
- retry success 후 stale error state가 남으면 실패다.

### T6. WAL-before-submit ordering

- data I/O submit hook과 WAL durable hook을 기록한다.
- permanent page에서 WAL durable event가 data submit보다 반드시 앞서야 한다.
- temporary/unlogged 예외는 기존 CUBRID 규칙대로 별도 assertion한다.

목적: AIO가 ordering을 “completion 전 WAL”로 느슨하게 바꾸지 못하도록 한다. data submit 자체가 WAL보다 앞서면 안 된다.

### T7. TDE/DWB lifetime matrix

- plain/no-DWB, TDE/no-DWB, plain/DWB, TDE/DWB 네 조합을 분리한다.
- 각 조합에서 실제 I/O buffer 주소가 live frame인지 encrypted copy인지 DWB slot인지 기록한다.
- request completion/DWB transfer 전 source image가 해제·재사용되지 않는지 검증한다.

목적: zero-copy 정책을 암호화/DWB path에 거짓 일반화하지 않는다.

### T8. Shutdown/cancel/stuck completion

- queued-but-not-submitted, submitted, device-complete-but-callback-pending 세 단계에서 shutdown/cancel을 주입한다.
- freeze/ref 누수, 영구 writer starvation, victim pool 고갈이 없어야 한다.
- timeout/diagnostic에 in-flight page, age, owner/request id가 보여야 한다.

### T9. Fairness and observability gate

다음 counter/timer를 prototype에서 수집한다.

- copy bytes/page count
- in-flight copy bytes와 in-flight live frames
- freeze acquisition wait, writer wait, reader admission
- second-flusher join/wait/skip count
- completion latency, oldest in-flight age
- error rollback/cancel count
- victim rejected-by-freeze count

read-heavy, write-heavy, flush-pressure workload에서 current copy baseline과 비교한다. 성능 개선을 correctness claim과 섞지 않는다.

## 12. Report-ready synthesis

보고서 본문에 옮길 수 있는 가장 안전한 요약은 다음과 같다.

> PostgreSQL 20devel의 `FlushBuffer`는 pin과 `SHARE_EXCLUSIVE` content lock을 잡은 채 shared frame을 직접 `pg_pwritev` 경로로 쓰며, `BM_IO_IN_PROGRESS`로 단일 I/O를 보장한다. `SHARE_EXCLUSIVE`는 readers와 공존하지만 hint-bit setter, 일반 writer, 다른 flusher와 충돌한다. 이 때문에 flush 중 page redirty가 불가능해져 `BM_JUST_DIRTIED`와 checksum snapshot copy가 제거됐다. 다만 pinned revision의 buffer write는 아직 AIO가 아니고, 저수준 WRITEV 골격만 존재한다.
>
> 이 선례가 CUBRID에 증명하는 것은 “SX라는 새 공개 mode가 필수”가 아니라 “live-frame I/O에는 내용 불변, frame 수명, 단일 I/O, completion state가 각각 필요”하다는 점이다. PostgreSQL `SHARE`는 reader-compatible hint modifier와 공존하므로 freeze가 아니지만, CUBRID의 strict `READ`는 현행 유일한 modifier인 `WRITE`를 막는다. 동기 zero-copy에서는 READ+fix도 정확성 후보가 될 수 있고, frame-based AIO에서는 thread-owned fix보다 BCB-internal `IO_WRITE_FREEZE + request-owned io_ref`가 더 좁은 책임 경계다. copy-based AIO를 택하면 content freeze는 불필요하지만 output copy와 logical flush generation을 completion까지 소유해야 한다.
>
> 또한 direct I/O와 AIO는 분리해야 한다. 동기 `O_DIRECT`는 blocking write 반환까지, AIO는 completion까지 buffer 안정성을 요구한다. `O_DIRECT` 자체가 syscall 반환 이후의 buffer lifetime을 뜻하지 않는다.

## 2026-08-11 addendum — nbtree duplicate와 SX의 비교 한계

- PostgreSQL nbtree는 heap TID를 tiebreaker로 써 logical duplicate를 물리 정렬한다
  (`nbtree/README:42-49`). page가 찰 때 bounded, page-local posting-list tuple로 dedup한다
  (`nbtree.h:433-458`, `nbtdedup.c:34-99`). CUBRID의 key→overflow OID chain과 직접 대응하지 않는다.
- insert target leaf는 EXCLUSIVE로 반환되고 nbtree tree에는 `BUFFER_LOCK_SHARE_EXCLUSIVE` 사용이 없다
  (`nbtinsert.c:163-170`, `nbtree.h:725-731`).
- buffer SHARE_EXCLUSIVE의 S-compatible/SX-X-exclusive 호환성만 제안 SX와 partial analogy다. pinned buffer
  API에는 SX→X promotion이 없다. 일반 acquire는 기존 lock 보유를 금지하고, 유일한 upgrade helper는 hint
  bit용 S→SX이며 competing SX/X에서 false다 (`bufmgr.c:5921-5935,6992-7058`).

따라서 PostgreSQL을 근거로 “CUBRID overflow insert의 SX→X가 항상 성공한다”거나 “동일한 duplicate storage
algorithm이 검증됐다”고 쓰지 않는다.
