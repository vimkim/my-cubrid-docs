# [OOS] snapshot 없는 OOS reader가 tail-first 회수와 겹칠 수 있는지 조사한다

**한 줄 요약**: [PR #8434 코드 리뷰](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27781/code-review-pr8434-3e8072f/report.md#r7-p3-hardening--readers-never-check-the-link-stamp)의 R7("reader가 chain link의 stamp를 확인하지 않는다", [PR 요약 댓글](https://github.com/CUBRID/cubrid/pull/8434#issuecomment-6680787439)에서 남은 항목으로 분류)에 대응하는 후속 이슈다. MVCC snapshot 없이 OOS chain을 읽는 호출자가 회수 중인 chain과 겹칠 수 있는지 먼저 조사하고, 그 결과에 따라 reader의 연속 chunk 검증을 보강할지 정한다.

## Issue Triage

**이슈 수행 목적**: snapshot 없이(또는 NULL snapshot으로) OOS chain을 읽는 호출자를 모두 찾고, 각 호출자가 OOS 회수와 동시에 실행될 수 있는지 판정한다. 겹칠 수 있는 호출자가 있으면, 그 reader가 다른 chain의 바이트를 값으로 돌려주거나 해제된 페이지에서 멈추지 않고 일관된 오류로 끝나게 한다. 겹칠 수 있는 호출자가 없으면 그 근거를 남긴다.

**이슈 수행 이유**: PR #8434(ADR-0008)는 chain을 tail부터 지우고 head를 마지막에 지운다. 지운 slot은 곧바로 재사용될 수 있고, 빈 페이지는 LSA gate 없이 해제될 수 있다. reader는 head chunk의 identity stamp만 확인한다. 연속 chunk는 링크에 저장된 `next_chunk_stamp`를 비교하지 않고 일반 `pgbuf_fix`로 읽는다. 따라서 회수와 겹친 reader는 head가 남아 있는 동안 이미 지워졌거나 다른 chain이 재사용한 연속 chunk를 읽을 수 있다. MVCC snapshot reader는 A'로 보호된다. snapshot 없는 reader에게는 이 보호가 없다. [조사 결과](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27781/null-snapshot-reader-investigation.md) 회수와 겹칠 수 있는 호출자가 있다. MVCC가 꺼진 catalog(`_db_ha_apply_info`, `_db_serial`)를 join이나 subquery처럼 fixed가 아닌 scan으로 읽는 SELECT는 행을 복사하고 page latch를 놓은 뒤 OOS를 읽는다. 기본 격리 수준(READ COMMITTED)에서는 instance lock도 이 틈을 막지 못한다. 같은 틈은 serial 경로에서 실행으로 재현되었다([CBRD-28035 재현](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-28035/race-repro.md), reader 오류 354건과 492건).

**영향**: 겹치는 호출자가 있으면 그 reader가 만나는 연속 chunk 상태에 따라 결과가 갈린다. slot이 비어 있으면 두 빌드 모두 `ER_HEAP_OOS_CORRUPTED_RECORD`로 실패하며, 이것은 의도한 결과다. slot이 다른 chain에 재사용되었고 그 chunk가 같은 chunk 순번과 전체 길이를 가지면, release 빌드는 다른 chain의 바이트를 오류 없이 컬럼 값으로 돌려준다. 순번이나 길이가 다르면 release 빌드는 `ER_HEAP_OOS_CORRUPTED_RECORD`로 실패하고 debug 빌드는 assert로 중단된다. 페이지가 이미 해제되었으면 release 빌드는 `ER_PB_BAD_PAGEID`로 실패하고 debug 빌드는 assert로 중단된다. 해제된 페이지가 다른 용도로 다시 할당된 경우의 동작은 확인하지 않았다. `_db_ha_apply_info`에서는 applylogdb의 UPDATE가 commit 때 이전 chain을 회수하므로 위 결과가 생길 수 있다. 다만 `copied_log_path`가 page의 1/4을 넘어야 하므로(16K page에서 약 4KB) 실제 발생 가능성은 낮다. 이 경로에서 경합을 직접 재현하지는 않았다.

**이슈 수행 방안**: reader 쪽 확인으로 막는다(2026-11-12 결정). `oos_read_within_page`가 연속 chunk를 읽을 때 앞 chunk 링크의 `next_chunk_stamp`와 읽은 chunk의 identity stamp를 비교하고, 연속 chunk 페이지를 해제 허용 방식으로 fix한다. 불일치나 해제된 페이지를 만나면 다른 chain의 바이트를 돌려주지 않고 일관된 오류로 끝낸다. OOS 읽기 한 곳에서 모든 호출 경로를 덮기 때문에 이 방식을 골랐다. 검토한 다른 후보(cached scan 제외, SELECT instance S lock, latch를 쥔 채 펼치기, 쓰는 쪽 chain 재사용)는 틈을 막지 못하거나 경로마다 따로 적용해야 한다. 오류 뒤 행을 다시 읽어 재시도할지, 오류로 끝낼지와 구현 범위는 ANALYSIS에서 정한다.

---

## AI-Generated Context

## Description

### 회수 순서와 reader의 검사가 어긋나는 지점

OOS chunk header의 `next_chunk_stamp`는 다음 chunk가 가진 identity stamp다. reclaimer는 이 값이 일치할 때만 링크를 따라간다. ([oos_file.hpp:32-51](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/oos_file.hpp#L32-L51))

- **reclaimer**: `oos_collect_chain_prefix`는 링크의 stamp가 맞을 때만 다음 chunk로 간다([oos_file.cpp:3322-3323](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/oos_file.cpp#L3322-L3323)). `oos_delete_chain`은 모은 chunk를 tail부터 지우고 head를 마지막에 지운다([oos_file.cpp:3395](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/oos_file.cpp#L3395)). 연속 chunk 페이지도 해제 허용 방식으로 fix한다(ADR-0008 결정 3).
- **reader**: `oos_read`는 head 페이지를 해제 허용 방식으로 fix하고 head의 stamp를 확인한다. 이어지는 `oos_read_across_pages`는 `oos_read_within_page`로 연속 chunk를 읽는다. 이 함수는 일반 `pgbuf_fix(OLD_PAGE)`를 쓴다. 각 chunk에서는 chunk 순번과 전체 길이만 검사하며, 순번이나 길이가 다르면 debug 빌드는 assert로 중단한다. `next_chunk_stamp`는 비교하지 않는다. ([oos_file.cpp:2600-2666](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/oos_file.cpp#L2600-L2666)) `oos_read_many`도 같은 함수로 연속 chunk를 읽는다([oos_file.cpp:2879](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/oos_file.cpp#L2879)).
- `oos_read_within_page`의 주석은 일반 fix를 쓰는 이유를 이렇게 적는다. "caller가 head의 identity를 확인했으므로 chain은 살아 있고 링크도 온전하다." tail-first 회수에서는 head가 마지막까지 남는다. 따라서 이 전제는 회수와 겹치지 않는 reader에서만 성립한다.
- 해제된 페이지를 `OLD_PAGE`로 fix하면 debug 빌드는 `assert (false)`에서 중단하고, release 빌드는 `ER_PB_BAD_PAGEID`를 설정한다([page_buffer.c:2505-2511](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/page_buffer.c#L2505-L2511)).

PR 전 base `d52b1889e`는 head부터 지우는 forward walk를 썼다([oos_file.cpp:3238-3255](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L3238-L3255)). 빈 페이지 해제도 LSA gate로 늦췄다([oos_file.cpp:1538-1553](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L1538-L1553)). base에서도 head 확인 직후 연속 chunk가 지워지는 경합은 이론상 있었다(아래 이전 조사 Q4, INFERRED). PR 이후에는 회수가 진행되는 동안 head가 계속 남아 있다. 따라서 head 확인을 통과한 뒤 뒤 chunk가 사라졌거나 재사용되었거나 페이지가 해제된 상태를 만날 시간 범위가 회수 전체로 넓어진다. 이 비교는 소스로 추론한 것이며, 실행으로 확인하지 않았다.

### MVCC reader는 A'로 보호된다

vacuum은 UPDATE가 버린 chain의 알림(`RVOOS_NOTIFY_VACUUM`)을 UPDATE의 MVCCID가 모든 활성 snapshot보다 오래된 뒤에만 처리한다([vacuum.c:3814-3819](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/query/vacuum.c#L3814-L3819), [ADR-0008 결정 2](https://github.com/vimkim/cubrid-oos-context/blob/4567c7c4e530a3f0b28f03834b7488ad3eecb82d/docs/adr/0008-reclaim-oos-chains-after-the-delete-is-final.md#decision)). 리뷰는 등록된 snapshot에 대해 A'가 안전하다고 소스 수준에서 판단했다. snapshot이 없는 reader는 이 순서 조건의 보호를 받지 않는다. 그런 reader가 회수 대상 chain을 동시에 읽을 수 있는지가 이 이슈의 질문이다.

### 지금까지 알려진 것

- 리뷰 커버리지 표는 "NULL-snapshot reader 열거"를 끝내지 못한 항목으로 기록했다.
- 이전 조사([reclaim-engine-facts Q4](https://github.com/vimkim/my-cubrid-docs/blob/main/oos/reclaim-engine-facts.md#q4-readers-that-dereference-oos-stubs-without-an-mvcc-snapshot), `feature/oos-merge` `dcbf09e4f` 기준)는 snapshot 없이 OOS를 읽는 경로 후보를 기록했다. 예는 다음과 같다.
  - `btree_load`(CREATE INDEX)
  - unloaddb `--latest-image`가 쓰는 `xlocator_fetch_all`
  - `xlocator_upgrade_instances_domain`과 `redistribute_partition_data`
  - catalog scan, `heap_dump`

  같은 조사는 `btree_load`가 vacuum이 이미 지운 chain의 stub을 읽을 수 있다고 추론했다(INFERRED). 이 목록은 이전 커밋 기준이며, PR head `2e32517bb`에서 다시 확인하지 않았다.
- PR head에서 회수 중인 chain과 실제로 겹칠 수 있다고 확인된 호출자는 아직 없다.

### 조사할 것

1. PR head(또는 조사 시점의 head)에서 snapshot 없이 OOS chain을 읽는 호출자를 모두 찾는다. 위 후보 목록을 출발점으로 쓰되, 새 호출자도 grep으로 확인한다.
2. 각 호출자가 다음 회수 경로와 동시에 실행될 수 있는지 판정한다.
   - (a) vacuum REMOVE sysop의 postpone 회수
   - (b) `RVOOS_NOTIFY_VACUUM` 처리
   - (c) non-MVCC 연산의 commit 시 회수(`oos_rv_reclaim_on_postpone`)

   heap home page latch를 쥔 채 OOS를 읽는지, 아니면 레코드를 복사한 뒤 latch 밖에서 읽는지 확인한다. class lock, instance lock, oldest visible MVCCID pin 같은 보호도 확인한다. (c)에 대해 ADR-0008은 "eager cleanup에는 동시 reader가 없다"고 가정한다(Considered options의 B6 행). 이 가정도 함께 확인한다.
3. 판정 결과를 호출자별 표로 남긴다. 겹칠 수 있는 호출자가 하나라도 있으면 보강 방법을 ANALYSIS에서 정한다.

### 방향

ANALYSIS에서 검토할 후보는 두 가지다.

- reader가 연속 chunk에서도 링크의 stamp를 비교한다. 연속 chunk 페이지는 해제 허용 방식으로 fix한다. 불일치나 해제는 `ER_HEAP_OOS_CORRUPTED_RECORD`로 보고한다.
- 겹치는 호출자 쪽에서 회수와 겹치지 않게 막는다.

두 후보 중 하나를 고르는 일은 조사 결과에 달려 있다.

## Test Build

소스만 읽었으며, 빌드와 실행은 하지 않았다.

| 기준 | 커밋 | 확인 내용 |
|---|---|---|
| PR #8434 head | `2e32517bb` | reader의 연속 chunk 검사, tail-first 삭제, 해제된 페이지 fix 동작 |
| PR #8434 리뷰 시점 head | `3e8072f56` | 리뷰가 인용한 줄 번호(`oos_read_within_page` 2597-2619, `oos_read_across_pages` 2623)는 이 커밋 기준이다. `2e32517bb`에서는 각각 2600-2622, 2626이다. |
| `feature/oos-merge` (PR base) | `d52b1889e` | head부터 지우는 forward walk와 LSA reclaim gate |

## Repro

실행한 재현은 없다. 리뷰 중에 제안된 gtest 초안이 있다([probe_ss3_read_after_tail_reclaim.cpp](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27781/code-review-pr8434-3e8072f/reviewers/systems-storage/probe_ss3_read_after_tail_reclaim.cpp), 실행하지 않음). 이 초안은 실제 사용자 경로를 재현하지 않는다. 회수 도중 head가 남은 상태를 테스트 hook으로 만든다. 그다음 tail 페이지를 해제하고 head로 읽는다. 초안이 예상하는 결과는 debug 빌드의 `pgbuf_fix` assert와 release 빌드의 `ER_PB_BAD_PAGEID`다.

## Definition of done

- snapshot 없이 OOS chain을 읽는 호출자 표가 있다. 표에는 조사 기준 커밋과, 회수 경로 (a)(b)(c) 각각에 대한 겹침 판정과 근거가 들어 있다.
- 겹치는 호출자가 없으면 그 결론과 근거로 이슈를 닫는다. 필요하면 reader 주석의 전제를 실제 근거에 맞게 고친다.
- 겹치는 호출자가 있으면 다음을 보장하는 변경이 들어간다. 회수 도중 head를 확인한 read가 연속 chunk의 삭제, 재사용 또는 페이지 해제를 만나면, debug와 release 빌드 모두 다른 chain의 바이트를 돌려주지 않는다. 대신 `ER_HEAP_OOS_CORRUPTED_RECORD`로 끝난다. 이 동작을 확인하는 테스트도 함께 들어간다.
