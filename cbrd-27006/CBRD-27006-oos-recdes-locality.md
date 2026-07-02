# [CBRD-27006] OOS recdes locality

- JIRA: https://jira.cubrid.org/browse/CBRD-27006
- Parent: https://jira.cubrid.org/browse/CBRD-26583
- Code commit: https://github.com/vimkim/cubrid/commit/56e22c15c4ae024c141035b62db9dfb6d17acf6c
- Target branch: `feat/oos`
- Code branch: `CBRD-27006-oos-recdes-locality`

## Purpose

CBRD-27006은 하나의 heap record (`RECDES`) 안에 여러 OOS (큰 가변 길이 컬럼 값을 heap record 밖의 OOS file에 저장하는 방식) 컬럼이 있을 때, 쓰기와 읽기의 page locality를 높이는 작업이다.

- AS-IS: 여러 OOS 컬럼을 저장할 때 `heap_attrinfo_insert_to_oos()` 가 컬럼마다 `oos_insert()` 를 호출했다. 각 호출은 bestspace (빈 공간이 충분한 OOS page 후보를 찾는 힌트) 탐색과 `pgbuf_fix` (page를 buffer pool에 고정하는 작업) 를 따로 수행하므로, 같은 heap record에서 나온 OOS 값들이 서로 다른 OOS page로 흩어질 수 있었다.
- TO-BE: 같은 heap record에서 나온 single-chunk OOS 값들을 logical attribute order 그대로 single-page OOS batch로 묶는다. 읽을 때도 같은 head page에 있는 OOS OID들을 한 번의 page fix로 처리한다.

이 변경은 on-disk OOS format을 바꾸지 않는다. OOS OID는 여전히 OOS 값 하나당 하나이고, multi-chunk chain 구조도 그대로 유지한다. 목적은 OOS record model을 유지하면서 한 record 단위의 placement locality와 read locality를 개선하는 것이다.

## Implementation

`src/storage/oos_file.hpp` 에 `oos_insert_request`, `oos_read_request`, `oos_insert_many()`, `oos_read_many()` 를 추가했다. `oos_insert_many()` 는 요청을 logical order로 받으며, 각 요청의 `oid_out` 에 head OOS OID를 채운다. `oos_read_many()` 는 caller가 heap record의 inline OOS length로 준비한 destination buffer에 정확히 그 길이만큼 읽는다.

`src/storage/oos_file.cpp` 의 insert path는 single-chunk run과 multi-chunk value를 분리한다. single-chunk run은 request order를 보존한 채 page capacity에 맞는 single-page OOS batch로 나뉜다. batch 하나는 한 OOS page에 함께 들어가야 하는 placement unit이다.

Single-page OOS batch 처리 규칙은 다음과 같다.

- 기존 OOS page는 batch 전체가 들어갈 때만 재사용한다.
- conditional latch로 찾은 page는 write latch로 다시 fix한 뒤 실제 free space를 재확인한다.
- refix 사이에 다른 transaction이 page를 채워 batch 전체가 들어가지 않으면, batch를 쪼개지 않고 fresh OOS page를 할당한다.
- batch 안의 각 OOS record는 기존 `RVOOS_INSERT` WAL record로 개별 logging한다.
- bestspace update는 batch insert 후 한 번 수행한다.

Multi-chunk value는 기존 `oos_insert_across_pages()` 경로를 유지한다. single-chunk batch 앞뒤에 multi-chunk value가 섞여 있어도 request order가 유지되며, multi-chunk replication boundary marker도 기존 방식대로 유지된다.

OOS insert publication 책임도 정리했다. `oos_insert()` 와 `oos_insert_many()` 가 `thread_p->oos_oids` publication을 직접 수행한다. 호출자는 OOS write 전에 tracking state를 clear하고, 반환된 OID를 다시 push하지 않는다. `src/transaction/locator_sr.c` 의 scalar caller에서도 중복 push를 제거했다.

`src/storage/heap_file.c` 의 `heap_attrinfo_insert_to_oos()` 는 OOS-selected attribute들을 `attr_info->values[]` 순서로 수집하고, 각 `DB_VALUE` 를 stable buffer에 serialize한 뒤 `oos_insert_many()` 를 호출한다. 성공하면 batch 결과 OID와 payload length를 각 attribute index에 복사한다. Error path에서는 transient buffer를 모두 해제한다.

Read path는 두 곳에 batching을 연결했다.

- `src/storage/heap_oos.cpp` 의 record-level Expand 경로인 `heap_oos_read_blobs()` 는 inline OOS header들을 먼저 모은 뒤 `oos_read_many()` 를 한 번 호출한다.
- `src/storage/heap_file.c` 의 lazy Resolve 경로인 `heap_attrinfo_read_dbvalues()` 와 `heap_attrinfo_read_dbvalues_without_oid()` 는 `heap_recdes_contains_oos(recdes)` 가 true일 때만 batched wrapper를 사용한다. 이 wrapper는 requested attribute만 검사하고, OOS-marked requested attribute만 읽는다.

`oos_read_many()` 는 head OID의 `(volid, pageid)` 로 request를 group한다. Page group은 first-seen order로 처리하고, 같은 page 안의 slots도 request order로 처리한다. Grouped head page는 read latch로 한 번 fix하고, 같은 page의 requested slots를 모두 읽는다. Multi-chunk value는 head payload와 `next_chunk_oid` 를 읽은 뒤 page를 unfix하고 기존 continuation-chain read logic으로 이어간다.

Unit-test 전용 debug counters도 추가했다. `CUBRID_UNIT_TEST_ENABLED`에서 insert-many call/request 수, single-page batch 수, reused/fresh page 수, fixed page당 insert/read value 수, read-many call/request 수, grouped head page 수를 확인할 수 있다.

Test coverage는 다음 축을 확인한다.

- `unit_tests/oos/test_oos_server.cpp`: single-page locality, whole-batch reuse, fresh page allocation instead of scattering, oversized run splitting, grouped read, mixed single/multi-chunk publication order.
- `unit_tests/oos/sql/test_oos_sql_crud.cpp`: multiple OOS columns select, partial column select, update correctness, mixed single-chunk and multi-chunk row correctness.

## Remarks

### Review focus

Reviewer는 세 부분을 우선 보면 된다.

1. `oos_insert_many()` 가 request order를 바꾸지 않는지 확인한다. OOS replication metadata는 attribute order에 민감하다.
2. Single-page OOS batch가 "reuse if whole batch fits, otherwise fresh page" 정책을 지키는지 확인한다. 기존 page reuse가 locality를 깨면 이 PR의 목적이 사라진다.
3. Lazy Resolve batching이 requested attribute만 읽는지 확인한다. Partial-column select가 unrelated OOS column을 읽으면 read I/O를 줄이려는 목적과 맞지 않는다.

### Limits

이 PR은 phase-1 locality 개선이다. OOS OID sharing 또는 deduplication, inline OOS format 변경, multi-column combined OOS record format, continuation page locality optimization, replication log format 변경은 포함하지 않는다.

`heap_attrinfo_insert_to_oos()` 는 batch call 전에 selected OOS values를 stable memory에 모두 serialize한다. 이는 기존 scalar path보다 peak memory가 늘어나는 선택이지만, request order를 보존하고 batch placement를 결정하기 위한 단순한 phase-1 trade-off이다.

### Verification

이 문서는 PR #7391의 code commit `56e22c15c4ae024c141035b62db9dfb6d17acf6c` diff, JIRA CBRD-27006, OOS 설계 문맥을 기준으로 검토했다. 해당 commit에는 OOS server unit tests와 SQL CRUD tests가 함께 포함되어 있다.

PR body에는 이 문서의 public GitHub URL만 링크하면 된다.
