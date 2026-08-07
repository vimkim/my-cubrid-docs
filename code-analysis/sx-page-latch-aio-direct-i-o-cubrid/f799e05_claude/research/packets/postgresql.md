# PostgreSQL Comparator Packet

- Role: PostgreSQL Comparator (main agent 직접 수행; 별도 스폰한 에이전트가 지연되어 자체 검증으로 대체, 도착 시 교차확인 예정)
- Topic: SX page latch 도입 분석을 위한 PostgreSQL 비교
- Scope digest: research/scope.md (FROZEN)
- Revision: fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc (master, 20devel), clean 여부는 provenance 참조
- Timestamp: 2026-08-07T06:30Z

## 1. content lock 3-mode

- `src/include/storage/bufmgr.h:205-223` — `typedef enum BufferLockMode`: `BUFFER_LOCK_UNLOCK`, `BUFFER_LOCK_SHARE`("conflicts with exclusive locks"), `BUFFER_LOCK_SHARE_EXCLUSIVE`("conflicts with itself and exclusive locks"), `BUFFER_LOCK_EXCLUSIVE`("conflicts with every other lock type").

## 2. 충돌 행렬 구현

- `src/backend/storage/buffer/bufmgr.c:6118-6160` — `BufferLockAttempt`: EXCLUSIVE는 `BM_LOCK_MASK == 0`일 때만, SHARE_EXCLUSIVE는 `(EXCLUSIVE|SHARE_EXCLUSIVE) bits == 0`일 때(:6143-6147), SHARE는 `EXCLUSIVE bit == 0`일 때 grant.

## 3. FlushBuffer

- `src/backend/storage/buffer/bufmgr.c:4526-4545` — 진입부에서 `Assert(BufferLockHeldByMeInMode(buf, BUFFER_LOCK_EXCLUSIVE) || BufferLockHeldByMeInMode(buf, BUFFER_LOCK_SHARE_EXCLUSIVE))` (:4534-4535).
- `:4595-4605` — `PageSetChecksum((Page) bufBlock, ...)` 을 **공유 buffer 에 제자리로** 수행하고 `smgrwrite(..., bufBlock, ...)` 로 공유 buffer 를 직접 쓴다. 사본 없음.
- 음성 탐색: `rg PageSetChecksumCopy src/` 0건 — 사본 함수 자체가 트리에서 제거됨.
- `:4649-4660` — `FlushUnlockedBuffer` 는 잠기지 않은 buffer 를 flush 할 때 `BufferLockAcquire(..., BUFFER_LOCK_SHARE_EXCLUSIVE)` 로 SX 등가 lock 을 얻는다(:4654).

## 4. hint bit 경로

- `src/backend/storage/buffer/bufmgr.c:5710-5732` — `MarkSharedBufferDirtyHint` 가 EXCLUSIVE 또는 SHARE_EXCLUSIVE 보유를 Assert.
- `:7000-7050` — `SharedBufferBeginSetHintBits`: 이미 EXCLUSIVE/SHARE_EXCLUSIVE 면 통과, SHARE 만 쥔 경우 "try to upgrade it to SHARE_EXCLUSIVE" — 다른 EXCLUSIVE/SHARE_EXCLUSIVE 가 있으면 **즉시 false 반환(nowait)**. 즉 PostgreSQL 의 유일한 lock 승격은 SHARE→SHARE_EXCLUSIVE **조건부(nowait)** 승격이다. blocking 승격은 없다.

## 5. write 는 아직 동기 I/O

- `FlushBuffer` → `smgrwrite` (bufmgr.c:4600-4604).
- `pgaio_io_start_writev` 는 선언(`src/include/storage/aio.h:301`)과 정의(`src/backend/storage/aio/aio_io.c:91`)만 있고 호출자가 없다. 음성 탐색 범위: `rg pgaio_io_start_writev src/backend src/include -g '*.[ch]'` — 정의/선언 2건 외 0건. `mdstartwritev` 는 `md.c` 에 존재하지 않음(rg 0건).

## 6. 커밋 근거 (pinned repo 의 git 이력)

- `82467f627bd` "Require share-exclusive lock to set hint bits and to flush" — 메시지 전문 요지:
  - 종전에는 share lock 아래에서 hint bit 를 세울 수 있어 "we need to copy pages while writing them out, as otherwise the checksum could be corrupted".
  - "The need to copy the page is problematic to implement AIO writes: (1) Instead of just needing a single buffer for a copied page we need one for each page that's potentially undergoing I/O (2) To be able to use the worker AIO implementation the copied page needs to reside in shared memory".
  - "It also causes problems for using unbuffered/direct-IO, independent of AIO: Some filesystems, raid implementations, ... do not tolerate the data being written out to change during the write. E.g. they may compute internal checksums that can be invalidated by concurrent modifications, leading e.g. to filesystem errors (as the case with btrfs)".
  - 해결: share 아래 수정 금지, share-exclusive 도입(fcb9c977aa5 에서 구현), hint bit 는 조건부 승격 API 사용.
- `fcb9c977aa5` "bufmgr: Implement buffer content locks independently of lwlocks".

## 7. 옛 방식의 트리 내 흔적

- `src/include/storage/buf_internals.h:115-118` — flag 정의 목록에 `/* flag bit 6 is not used anymore */` — BM_JUST_DIRTIED 가 있던 자리.

## 8. nbtree insert 의 latch 규율

- `src/backend/access/nbtree/nbtsearch.c:100-190` — `_bt_search`: `page_access = BT_READ` 로 시작(:106), 하강 중 internal page 는 전부 read lock, leaf 에 도달할 때만 `page_access = BT_WRITE` (:182). 즉 insert 도 internal 은 read, **write lock 은 leaf 한 장**뿐이며, content lock 의 blocking in-place 승격 API 는 존재하지 않는다(유일한 승격은 위 4의 nowait share→share-exclusive). split 상향 전파는 부모-자식 lock coupling 으로 진행한다(nbtree README :125-157).

## Unknowns

- 20devel 은 미출시 개발 브랜치다. 여기 기술한 3-mode content lock 이 최종 릴리스에 그대로 남을지는 보장할 수 없다(출시 버전 18 이하는 SHARE/EXCLUSIVE 2-mode + flush 시 사본 방식).
- read 쪽 AIO(read stream)는 이 패킷 범위 밖이다.

## 교차확인 (독립 에이전트 패킷)

별도 스폰한 PostgreSQL comparator 에이전트가 지연 후 완전한 패킷을 반환했다(2026-08-07T06:03Z). 본 패킷의 8개 항목 전부와 결론이 일치하며 모순이 없었다. 추가로 확인된 세부:

- `MarkBufferDirtyHint`(bufmgr.c:5829-5862)의 주석이 share-exclusive 보유 호출자를 명시.
- nbtree 하강에서 leaf write lock 전환은 "trade in our read lock for a write lock"(nbtsearch.c:195-199) — unlock 후 재획득이지 제자리 승격이 아님을 재확인.
- 관련 커밋 확인: `b0f4ff3c926` "Remove the, now obsolete, BM_JUST_DIRTIED", `41d3d64e87a` "Don't copy pages while writing out".
- 커밋 82467f627bd가 "hint bit 설정이 한 번에 한 backend로 직렬화된다"는 트레이드오프를 수치 없이 인정함 — 정량 근거 부재 서술과 일치.
