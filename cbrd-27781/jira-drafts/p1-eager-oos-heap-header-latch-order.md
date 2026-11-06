# [OOS] non-MVCC heap UPDATE·DELETE의 OOS 회수 기록이 heap 데이터 페이지를 쥔 채 heap header latch를 기다린다

**한 줄 요약**: [PR #8434 코드 리뷰](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27781/code-review-pr8434-3e8072f/report.md#pre-existing-reported-separately)가 PR 이전부터 있던 문제(P-1)로 따로 보고한 것이다([PR 요약 댓글](https://github.com/CUBRID/cubrid/pull/8434#issuecomment-6680787439)). non-MVCC heap UPDATE·DELETE가 버린 OOS chain을 처리하려고 OOS 파일을 찾을 때, heap 데이터 페이지를 쥔 채 heap header 페이지를 무조건 기다린다. 이 이슈는 그 latch 순서 위반을 다룬다. CBRD-27860이 vacuum에서 고친 것과 같은 종류다.

## Issue Triage

**이슈 수행 목적**: heap 데이터 페이지를 쥔 스레드가 heap header latch를 무조건 기다리지 않게 한다. 그러면 heap 페이지 할당과의 순환 대기가 생기지 않는다. 또는 이 경로가 페이지 할당과 겹칠 수 없음을 근거로 확인하고 그 근거를 남긴다.

**이슈 수행 이유**: non-MVCC 연산의 heap UPDATE·DELETE는 home 페이지(relocation이면 forward 페이지도)를 쥔 채 `heap_oos_delete_unreferenced`를 부른다. 이 함수는 `heap_oos_find_vfid`로 OOS VFID를 찾는다. 이때 heap header 페이지를 `PGBUF_UNCONDITIONAL_LATCH` READ로 fix한다. 반대로 `heap_alloc_new_pages`는 header를 WRITE로 잡은 뒤 마지막 heap 페이지를 잡는다. page latch에는 deadlock 탐지가 없다. 따라서 두 스레드가 서로를 page latch timeout까지 기다릴 수 있다. [CBRD-27860](https://jira.cubrid.org/browse/CBRD-27860)(PR #8350, `d52b1889e`)은 vacuum에 있던 같은 순서 문제를 고쳤지만, 이 경로는 고치지 않았다. PR #8434 base `d52b1889e`와 head `2e32517bb` 모두 같은 경로를 가진다.

**영향**: 순환 대기가 생기면 한쪽이 page latch timeout으로 실패한다. CBRD-27860에서는 삽입 트랜잭션이 abort되었다. 이 경로가 실제로 순환에 들어가려면 SERVER 모드의 non-MVCC 연산이 OOS를 가진 레코드의 chain을 버려야 한다. 동시에 다른 스레드가 같은 heap에 페이지를 할당해야 한다. 이 조합이 실제로 생기는지는 확인하지 않았다. 발생 가능성과 빈도는 알지 못한다.

**이슈 수행 방안**: TBD - ANALYSIS 단계에서 해결 방안과 구현 범위를 결정한다.

---

## AI-Generated Context

## Description

### latch 순서

| 쪽 | 먼저 잡는 latch | 이어서 기다리는 latch |
|---|---|---|
| non-MVCC heap UPDATE·DELETE의 OOS 회수 기록 | heap 데이터 페이지: home, relocation이면 forward도 (WRITE) | heap header (READ, 무조건) |
| `heap_alloc_new_pages` | heap header (WRITE) | 마지막 heap 페이지 |

home 또는 forward 페이지가 마지막 heap 페이지이면 두 스레드가 서로를 기다린다. CBRD-27860의 커밋 메시지와 vacuum 쪽 수정 주석은 "page latch에는 deadlock 탐지가 없다"는 이유로 이 순서를 피한다([vacuum.c:2302-2314](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L2302-L2314)). vacuum은 `heap_oos_find_vfid_nowait`로 header를 조건부로 시도한다. 실패하면 heap 페이지를 놓은 뒤에 header를 기다린다.

### 경로 (두 리비전 모두 소스로 확인)

호출 지점은 `!is_mvcc_op`일 때만 `heap_oos_delete_unreferenced`를 부른다. 각 함수는 호출 직전이나 직후에 같은 home/forward 페이지의 watcher로 slot을 읽거나 `heap_delete_physical`·`heap_update_physical`을 수행한다. 따라서 호출 시점에 그 페이지를 쥐고 있다.

| 호출 함수 | `feature/oos-merge` `d52b1889e` | PR head `2e32517bb` |
|---|---|---|
| `heap_delete_relocation` | [heap_file.c:23983](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/heap_file.c#L23983) | [heap_file.c:23983](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L23983) |
| `heap_delete_home` | [heap_file.c:24329](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/heap_file.c#L24329) | [heap_file.c:24328](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L24328) |
| `heap_update_relocation` | [heap_file.c:24761](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/heap_file.c#L24761) | [heap_file.c:24757](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L24757) |
| `heap_update_home` | [heap_file.c:25246](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/heap_file.c#L25246) | [heap_file.c:25233](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L25233) |

이후 header fix까지의 경로는 다음과 같다.

- base: `heap_oos_delete_unreferenced`([heap_oos.cpp:953](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/heap_oos.cpp#L953))가 [994행](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/heap_oos.cpp#L994)에서 `heap_oos_find_vfid`를 직접 부른다. base는 이 자리에서 chunk도 바로 지웠다.
- PR head: `heap_oos_delete_unreferenced`([heap_oos.cpp:1038-1054](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_oos.cpp#L1038-L1054))가 1048행에서 `heap_oos_resolve_vfid`를 부르고, 이 함수가 [988행](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_oos.cpp#L985-L988)에서 `heap_oos_find_vfid`를 부른다. PR은 chunk 삭제를 commit 뒤 postpone으로 옮겼지만, 회수 의도에 넣을 OOS VFID는 여전히 이 자리에서 찾는다.
- 공통: `heap_oos_find_vfid`([heap_file.c:13350](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L13350-L13353))는 `PGBUF_UNCONDITIONAL_LATCH`로 `heap_oos_find_vfid_internal`을 부른다. 이 함수가 [13258행](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L13237-L13258)에서 header 페이지를 fix한다(docreate false이므로 READ). 이 줄 번호는 두 리비전에서 같다.
- `heap_alloc_new_pages`는 header를 WRITE로 fix하고([heap_file.c:28606](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L28606)) 이어서 마지막 페이지를 잡는다([28656](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L28656)). base에서는 28619, 28669행이다.

리뷰는 이 경로를 `heap_oos.cpp:985/1030` → `heap_file.c:13350`으로 인용했다(리뷰 시점 `3e8072f56`). `3e8072f56`과 `2e32517bb`의 해당 줄 번호는 같다. 985는 `heap_oos_resolve_vfid`의 정의다. 1030은 `heap_oos_delete_unreferenced` 앞 주석 안의 줄이다. 실제 정의는 1038행, 호출은 1048행이다.

header를 미리 잡는 하위 경로도 있다. 새 레코드가 크거나 제자리에 들어가지 않는 UPDATE는 `heap_fix_header_page`로 header를 먼저 잡는다(예: [heap_file.c:24719-24732](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L24719-L24732)). non-MVCC DELETE와, 새 레코드가 제자리에 들어가는 UPDATE는 header를 미리 잡지 않는다. 이 이슈는 그 경우를 다룬다.

### non-MVCC 연산이 되는 조건

SA_MODE에서는 모든 heap UPDATE·DELETE가 non-MVCC 연산이다. SERVER 모드에서 non-MVCC 연산이 되는 조건은 다음과 같다.

- UPDATE: MVCC가 꺼진 클래스이거나 in-place UPDATE(`update_in_place != UPDATE_INPLACE_NONE`)일 때([heap_file.c:169-174](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L169-L174))
- DELETE: MVCC가 꺼진 클래스, `REC_ASSIGN_ADDRESS` 레코드 또는 bulk 연산일 때([heap_file.c:25514-25528](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L25514-L25528))
- MVCC가 꺼진 클래스: root class, serial, collation, ha_apply_info([mvcc.c:683-708](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/transaction/mvcc.c#L683-L708))
- in-place UPDATE를 쓰는 사용자 테이블 경로의 예: `heap_object_upgrade_domain`(컬럼 타입 변경), `redistribute_partition_data`(파티션 재분배). 이 목록이 전부인지는 확인하지 않았다.

### 확인하지 않은 것

- SERVER 모드에서 위 조건의 레코드가 OOS를 가지고, 연산이 그 chain을 버리는 경우가 실제로 있는지. PR #8434 리뷰의 R5도 같은 질문을 남겼다.
- 그 연산이 실행되는 동안, 다른 스레드가 같은 heap에 `heap_alloc_new_pages`를 실행할 수 있는지. 예를 들어 DDL의 class lock이 다른 트랜잭션의 삽입을 막는지 확인해야 한다.
- SA_MODE에서 같은 heap에 동시에 페이지를 할당하는 스레드가 있는지.
- 실행 재현. 순환 대기는 소스로만 확인했다.

### 방향

ANALYSIS에서 검토할 후보는 두 가지다. 어느 쪽을 쓸지는 ANALYSIS에서 정한다.

- MVCC 경로처럼 회수 의도에 HFID만 넣는다(`heap_oos_log_update_drop` → `oos_log_update_drop_intent`). OOS VFID는 heap 페이지를 쥐지 않은 postpone 실행 시점에 찾는다. 리뷰가 제안한 방향이다.
- CBRD-27860처럼 조건부 조회를 먼저 시도하고, 실패하면 heap 페이지를 놓고 기다린다.

## Test Build

소스만 읽었으며, 빌드와 실행은 하지 않았다.

| 기준 | 커밋 | 결과 |
|---|---|---|
| PR #8434 head | `2e32517bb` | 같은 경로 있음 |
| PR #8434 리뷰 시점 head | `3e8072f56` | 같은 경로, 줄 번호도 `2e32517bb`와 같음 |
| `feature/oos-merge` (PR base, CBRD-27860 수정 포함) | `d52b1889e` | 같은 경로 있음 |

## Repro

실행한 재현은 없다. 아래는 제안 절차다.

1. SERVER 모드에서 non-MVCC 연산으로 OOS chain을 버리는 경로를 하나 고른다. 이런 경로가 있는지는 위 "확인하지 않은 것"의 첫 질문이다.
2. 그 레코드가 heap의 마지막 페이지에 있게 만든다.
3. 다른 스레드에서 heap header를 WRITE로 잡고 `heap_alloc_new_pages`가 마지막 페이지를 기다리게 한다. CBRD-27860의 테스트(`unit_tests/oos/test_oos_real_vacuum_server.cpp`)가 header를 점유하는 방식을 참고할 수 있다.
4. 두 스레드가 page latch timeout까지 서로를 기다리는지 확인한다.

## Expected Result

- heap 데이터 페이지를 쥔 스레드는 heap header latch를 무조건 기다리지 않는다.
- 위 조건에서도 non-MVCC UPDATE·DELETE와 heap 페이지 할당이 둘 다 timeout 없이 끝난다.
- 회수 의도가 commit 뒤 같은 chain을 회수하는 동작은 그대로 유지된다.
