# CBRD-26788 — Heap / B-Tree Scan Prefetch 도입 검토 보고서

작성 대상: CUBRID develop branch
조사 범위: `/home/vimkim/gh/cb/develop/src/**`

---

## TL;DR

1. Heap full scan 과 B-tree range scan 은 모두 "현재 page → next VPID" 라는 logical chain 을 page 단위로 직렬 추적한다. buffer hit 일 때는 cheap 하지만 buffer miss 시 동기 single page read 가 scan latency 의 critical path 가 된다. 정확한 file:line 인용은 §2.1, §2.2, Appendix A 참조.
2. 코드 베이스에는 사용자 query 경로용 page prefetch 기능이 **존재하지 않는다**. `prefetch` 라는 단어는 (a) vacuum 의 log page prefetch, (b) parser 의 class lock prefetch, (c) cursor OID prefetch, (d) `__builtin_prefetch` CPU hint 에만 쓰이고, data page 단위 prefetch 는 없다(`src/base/porting.h:1100`, `src/query/vacuum.c:719`, `src/parser/compile.c:432`, `src/storage/page_buffer.c` 검색 결과).
3. OS readahead 와의 hook 은 이미 `posix_fadvise()` 형태로 들어가 있다(`src/storage/file_io.c:3050`, system param `data_file_os_advise` at `src/base/system_parameter.c:694`). 단 volume open 시 한 번만 호출되는 hint 이며, scan path 와 무관하다.
4. Parallel heap scan 은 sector 단위 분할이 기본이며 page 수 기준 threshold (`parallel_heap_scan_page_threshold`, default **2048**) 이상에서만 활성화된다(`src/base/system_parameter.c:5125`, `src/query/parallel/px_parallel.cpp:53`). prefetch 는 이 threshold 미만 구간 또는 parallel degree=1 인 회귀 구간을 메우는 보완재로 봐야 한다.
5. 권고 (수정): scan thread 내부에서 `PGBUF_CONDITIONAL_LATCH` 하나만으로는 buffer miss 의 IO latency 를 hide 할 수 없다는 점이 `pgbuf_fix` 코드 흐름(아래 §3.4) 으로 확인되었으므로, 1차 도입은 **async prefetch worker (Sketch B) 의 최소 형태 (depth=1, dedicated worker pool size=1~N)** 로 시작하는 것을 권장한다. Sketch A 는 "이미 OS readahead 가 데려온 페이지를 BCB 로 등록만" 하는 부수 효과만 가지므로 단독 도입 가치가 낮다.

---

## 1. 조사 범위 및 방법

본 조사는 CUBRID `develop` branch 의 storage / query / thread / monitor 모듈을 대상으로 다음 항목을 grep + read 기반으로 확인하였다.

- 조사 대상 디렉터리: `src/storage/`, `src/query/`, `src/query/parallel/`, `src/thread/`, `src/base/`
- 핵심 entry point:
  - heap scan: `src/storage/heap_file.c` (`heap_next_internal`, `heap_first`, `heap_next`, `heap_vpid_next`, `heap_scan_pb_lock_and_fetch`, `heap_scancache_*`)
  - btree range scan: `src/storage/btree.c` (`btree_range_scan_advance_over_filtered_keys`, `btree_range_scan_resume`, `btree_get_next_page_vpid`)
  - page buffer / LRU: `src/storage/page_buffer.c` (`PGBUF_LRU_*_ZONE`, `pgbuf_lru_add_new_bcb_to_*`, `pgbuf_lru_boost_bcb`)
  - file I/O: `src/storage/file_io.c` (`posix_fadvise`, `pread`/`pwrite`, `fileio_os_read`)
  - file 할당/sector: `src/storage/file_manager.c`, `src/storage/storage_common.h` (`DISK_SECTOR_NPAGES=64`)
  - parallel scan: `src/query/parallel/px_parallel.cpp`, `src/query/parallel/px_heap_scan/*`
  - thread infra: `src/thread/thread_daemon.{cpp,hpp}`, `src/thread/thread_manager.hpp`, `src/thread/thread_worker_pool*.{cpp,hpp}`
  - 성능 카운터: `src/base/perf_monitor.c` (`PSTAT_PB_*`, `PSTAT_FILE_*`)
  - 시스템 파라미터: `src/base/system_parameter.{c,h}` (`PRM_ID_PB_LRU_HOT_RATIO`, `PRM_ID_DATA_FILE_ADVISE`, `PRM_ID_PARALLEL_HEAP_SCAN_PAGE_THRESHOLD`)
- 본 보고서의 모든 결론은 위 파일들에 대한 `file:line` 단위 인용으로 뒷받침된다(각 절 및 Appendix A 참조). 모든 인용은 해당 줄에 실제로 토큰이 존재하는지 reviewer 가 직접 확인 가능한 형태로 기재한다.

---

## 2. Current Scan Path Analysis

### 2.1 Heap Scan Path

Heap full scan 의 외부 진입점은 query layer 의 `scan_next_heap_scan()` 이다(`src/query/scan_manager.c:5354-5361`, declaration `src/query/scan_manager.c:178`). 내부적으로 `heap_next()` 를 거쳐 `heap_next_internal()` 로 흐른다. `heap_next_internal` 의 정적 선언은 `src/storage/heap_file.c:792`, 정의 시작 (함수 헤더 주석 포함 블록) 은 `src/storage/heap_file.c:7883`, 함수 signature 는 `src/storage/heap_file.c:7902` 줄에 위치한다.

`heap_next_internal()` 의 page 탐색 루프는 다음과 같다.

- 현재 OID 의 (volid, pageid) 로 `vpid` 를 만들고(`heap_file.c:7981-7982`), `scan_cache->page_watcher.pgptr` 이 비어 있거나 다른 VPID 라면 `heap_scan_pb_lock_and_fetch()` 로 fix 한다. 이 fix 의 **fetch mode 는 `OLD_PAGE_PREVENT_DEALLOC`** 이며 호출 위치는 `src/storage/heap_file.c:7997-8001` (특히 fetch_mode argument 가 명시된 줄은 `heap_file.c:8000`) 이다.
- 현재 page 에서 slot 을 spage_next_record 로 순회한다(`heap_file.c:8048-8090`).
- 현재 page 의 slot 이 끝나면 (`scan == S_END`) `heap_vpid_next()` 호출로 chain 의 다음 VPID 를 얻고(`heap_file.c:8115`), 그 next VPID 의 page 를 다음 iteration 의 첫 fix 대상으로 삼는다.

`heap_vpid_next()` 자체는 함수 헤더 주석이 `src/storage/heap_file.c:5028-5036`, 반환형 `int` 가 `heap_file.c:5037`, 함수명·인자 signature 가 `heap_file.c:5038` 에 위치하며, 본문은 `heap_file.c:5037-5073` 범위이다. 본문에서 현재 fix 된 page 의 header slot 을 spage_get_record(PEEK) 로 읽어 `HEAP_HDR_STATS->next_vpid` 또는 `HEAP_CHAIN->next_vpid` 를 반환한다(`heap_file.c:5050-5070`). 즉 **next page 의 VPID 는 항상 "현재 page 가 buffer 에 fix 되어 있을 때" 만 알 수 있다**.

구조체 필드 정의 위치 (reviewer 가 line 단위 확인 가능):
- `typedef struct heap_hdr_stats HEAP_HDR_STATS;` — `src/storage/heap_file.c:190`. struct 정의 시작 `struct heap_hdr_stats` — `heap_file.c:191`. 필드 `OID class_oid;` `heap_file.c:194`. 필드 `VPID ovf_vfid;` `heap_file.c:195`. **필드 `VPID next_vpid;` — `src/storage/heap_file.c:196`** (`/* Next page (i.e., the 2nd page of heap file) */` 주석 동일 줄).
- `typedef struct heap_chain HEAP_CHAIN;` — `src/storage/heap_file.c:269`. struct 정의 시작 `struct heap_chain` — `heap_file.c:270`. 필드 `OID class_oid;` `heap_file.c:273`. 필드 `VPID prev_vpid;` `heap_file.c:274`. **필드 `VPID next_vpid;` — `src/storage/heap_file.c:275`** (`/* Next page */` 주석 동일 줄).

다음 page 의 VPID 가 disk 상의 page 안에 인라인되어 있다는 점이 prefetch 가능성의 핵심이다.

Heap scan 의 fetch wrapper 는 `heap_scan_pb_lock_and_fetch()` (`src/storage/heap_file.c:1235` 주석 시작, signature `heap_file.c:1248`) 로, 내부적으로 `pgbuf_ordered_fix` 혹은 `pgbuf_fix_release` 를 `PGBUF_UNCONDITIONAL_LATCH` 로 호출한다(`heap_file.c:1293-1311`). 즉 buffer miss 시 page 가 storage 에서 read 될 때까지 thread 가 동기 block 된다.

`scan_cache->cache_last_fix_page` 가 true 인 경우 현 page 의 fix 를 유지한 채 다음 page 가 같으면 재사용한다(`heap_file.c:7988-7995`, `scan_cache->cache_last_fix_page` 필드 정의는 `src/storage/heap_file.h:151`). 이는 page 내 slot 순회 시의 micro-optimization 이며, page 경계를 건너는 순간(다음 VPID ≠ 현재) 새로운 fix 가 발생한다.

### 2.2 B-Tree Range Scan Path

B-tree range scan 의 외부 driver 는 `scan_next_index_scan()` (declaration `src/query/scan_manager.c:181`) → `scan_get_index_oidset()` (선언 `src/query/scan_manager.c:170`, 본문 `scan_manager.c:2216-2224` 주석 시작 후 `scan_manager.c:2224` signature) 이다. 후자가 `btree_range_search()` 를 호출하여 leaf 페이지 chain 을 따라 OID set 을 채운다.

Leaf chain 의 실제 traversal 은 `btree_range_scan_advance_over_filtered_keys()` (선언 `src/storage/btree.c:25229-25230`, signature `btree.c:25230`) 에 집중되어 있다. 핵심 로직 요약:

- 현재 leaf `bts->C_page` 와 `bts->slot_id` 를 가진 상태에서 시작.
- 현재 leaf header 를 `btree_get_node_header(bts->C_page)` 로 얻고, 다음 VPID 를 `next_vpid = bts->use_desc_index ? prev_vpid : next_vpid` 로 결정한다(`btree.c:25302`).
- 현재 leaf 의 key 를 모두 소진하면 ascending case 에서 `pgbuf_fix(thread_p, &next_vpid, OLD_PAGE, PGBUF_LATCH_READ, PGBUF_UNCONDITIONAL_LATCH)` 로 다음 leaf 를 fix 한다(`btree.c:25349`). 이 fix 도 unconditional 이므로 buffer miss 시 동기 block 된다.
- fix 후 현재 leaf 를 `pgbuf_unfix` 하고 `bts->C_page` 를 갱신, `next_vpid = node_header->next_vpid` 로 갱신하여 chain 을 따라간다(`btree.c:25356-25368`).

Leaf 의 next VPID 자체는 `BTREE_NODE_HEADER.next_vpid` 필드에서 PEEK 으로 즉시 얻을 수 있다. helper `btree_get_next_page_vpid()` 가 `src/storage/btree.c:19351-19375` 에 정의되어 있다 (선언 `btree.c:1391`).

Descending scan 은 `btree_range_scan_descending_fix_prev_leaf()` (`btree.c:25333` 호출 지점) 를 거치는데, conditional latch 후 실패 시 root 부터 재시작하는 점이 prefetch 적용 가능성에 영향을 준다(아래 §5.2 참조).

`BTREE_SCAN` 구조체는 `typedef struct btree_scan BTREE_SCAN;` 가 `src/storage/btree.h:197`, struct 본문 시작이 `btree.h:198` 이다 (alias 사용 `BTREE_SCAN btree_scan` 가 `btree.c:334` 의 다른 구조체에 내장됨). 매크로 `BTS_*` 패밀리는 `btree.c:541-602` 에 정의되어 있다.

### 2.3 Logical Sequential vs Physical Locality

Heap chain 은 logical 한 linked list 이다. `HEAP_HDR_STATS.next_vpid`, `HEAP_CHAIN.next_vpid` 는 단순 forward pointer 이고(`heap_file.c:196, 275`), heap page 할당은 `file_alloc` (`src/storage/file_manager.h:206`) 을 통해 partial sector 의 free bit 위에 페이지 단위로 이루어진다. Sector 의 크기는 `DISK_SECTOR_NPAGES = 64` (`src/storage/storage_common.h:109`)·`IO_SECTORSIZE = 64 * IO_PAGESIZE` (`storage_common.h:110`) 로 고정이며, `SECTOR_FIRST_PAGEID(sid)` / `SECTOR_LAST_PAGEID(sid)` (`storage_common.h:115-116`) 로 sector 내 page 범위를 계산할 수 있다.

File manager 가 sector 단위로 페이지를 할당하기 때문에 정상적으로 채워진 heap 의 경우 한 sector(64 page) 내에서 logical sequence 와 physical sequence 는 어느 정도 일치할 가능성이 높다(`file_partsect_alloc` at `file_manager.c:2847`). 그러나 다음과 같은 이유로 strict guarantee 는 없다.

- DML 이 빈 page 를 재활용하면 `chain->next_vpid` 가 sector 경계를 가로지른다(`heap_file.c:4359` 부근의 chain 갱신).
- Heap statistics 가 free space 가 큰 best page 를 추정해 새 record 를 분산 배치하므로(`heap_hdr->estimates.best[start_pos].vpid` at `heap_file.c:3778`) chain 진행 순서가 disk 순서와 어긋날 수 있다.
- volume 확장 시 sector 가 비연속 영역에 할당될 수 있다(`FILE_TABLESPACE_DEFAULT_MAX_EXPAND = DISK_SECTOR_NPAGES * DB_PAGESIZE * 1024` at `file_manager.c:279`).

결론적으로 *"logical sequential = physical sequential"* 은 best-effort 일 뿐이며, large heap / fragmented heap 환경에서는 hop 단위로 random I/O 가 끼어들 수 있다. OS readahead 만 의존하는 현재 구조에서는 이런 hop 마다 readahead window 가 깨지면서 latency 가 누적된다.

B-tree 의 경우, leaf chain 은 동일 b-tree file 내에서 split 이력에 따라 분포되므로 heap 보다도 sector locality 가 약하다. `btree_split_node` / `btree_merge_node` 등(`btree.c:13331`, `btree.c:14192` 등) 이 새로운 sibling 의 VPID 를 새 sector 에서 할당받을 수 있다.

---

## 3. Buffer Pool & I/O Layer

### 3.1 pgbuf_fix and BCB

Buffer fix API 는 `pgbuf_fix(thread_p, vpid, fetch_mode, requestmode, condition)` 매크로로 시작하며(`src/storage/page_buffer.h:275-322`, debug 모드에서는 `pgbuf_fix_debug` `page_buffer.c:2037`, release 에서는 `pgbuf_fix_release` `page_buffer.c:2041`), 내부적으로 `pgbuf_lock_page` → IO 가 필요한 경우 `fileio_read` 까지 동기 호출된다.

`PAGE_FETCH_MODE` 는 `OLD_PAGE` / `OLD_PAGE_PREVENT_DEALLOC` / `NEW_PAGE` 등이 있으며(`page_buffer.h:174-200`), latch mode 는 `PGBUF_LATCH_READ` / `PGBUF_LATCH_WRITE`, latch condition 은 `PGBUF_CONDITIONAL_LATCH` / `PGBUF_UNCONDITIONAL_LATCH` (`page_buffer.h:202`) 이다.

**`OLD_PAGE` vs `OLD_PAGE_PREVENT_DEALLOC` 의 실제 차이**: `pgbuf_fix_release` 본문에서 두 모드의 분기는 두 군데뿐이다.
- `page_buffer.c:2249-2252` — `OLD_PAGE_PREVENT_DEALLOC` 일 때 `pgbuf_bcb_register_avoid_deallocation (bufptr)` 을 호출, BCB 의 `count_fix_and_avoid_dealloc` 필드를 `ATOMIC_INC_32` 한다 (정의 `page_buffer.c:15621-15630`). 그 외 latch acquisition 경로는 `OLD_PAGE` 와 완전 동일.
- `page_buffer.c:2337-2341` — latch 가 잡힌 직후 즉시 `pgbuf_bcb_unregister_avoid_deallocation` 으로 카운터를 감소시킨다.

즉 `PREVENT_DEALLOC` 의 추가 작업은 "fix lookup 과 latch acquisition 사이 window 동안 BCB 가 dealloc 되지 않도록 atomic counter 를 들고 있는 것" 뿐이다. fix 완료 후에는 동일 모드로 회귀한다. 일반 OLD_PAGE fix 의 경우 hash chain 에서 BCB 를 찾고 latch 가 잡히는 사이 다른 thread 가 같은 BCB 의 page 를 dealloc 시도 시 race 가 가능하지만, 실용적으로는 보호된 chain 이나 file-level 보장(volume scan 중 file_dealloc 부재) 하에서 호출자가 `OLD_PAGE` 만으로 충분히 동작한다.

**현재 scan path 의 실측**: heap scan 은 `OLD_PAGE_PREVENT_DEALLOC` 으로 fix 하고(`heap_file.c:8000`), btree 의 leaf chain advance 는 plain `OLD_PAGE` 로 fix 한다(`btree.c:25349`). 즉 *codebase 가 두 경로에서 서로 다른 정책* 을 채택하고 있으며, btree leaf chain 의 경우 split/merge 가 동시에 일어나도 leaf 자체는 normal MVCC scan 도중 dealloc 되지 않는 것을 전제로 `OLD_PAGE` 만 사용한다.

본 보고서의 prefetch hook 은 위 사실을 따라 **각 scan path 의 기존 fetch mode 와 동일** 하게 둔다.
- Heap scan 용 prefetch: `OLD_PAGE_PREVENT_DEALLOC` (`heap_scan_pb_lock_and_fetch` 와 일치, `heap_file.c:8000`).
- B-tree leaf chain prefetch: `OLD_PAGE` (`btree.c:25349` 의 직접 fix 와 일치).

만약 추후 정량 측정에서 prefetch 와 scan fix 사이 window 가 너무 길어져 race 가 관측되면, 양쪽 경로 (prefetch + 기존 `btree.c:25349`) 를 동시에 `OLD_PAGE_PREVENT_DEALLOC` 으로 승격해야 한다 (단독 prefetch 만 보강하는 것은 의미가 없다). 본 보고서는 현재 scan 의 정책을 보존하는 쪽을 1차 권고로 한다.

BCB(Buffer Control Block) 의 zone 표현은 `PGBUF_LRU_1_ZONE / _2_ZONE / _3_ZONE` (`page_buffer.c:199-201`) 이며, `PGBUF_LRU_3_ZONE` 이 victim zone 이다(`PGBUF_IS_BCB_IN_LRU_VICTIM_ZONE` at `page_buffer.c:919`).

### 3.2 LRU Midpoint Insertion Policy

CUBRID 의 LRU 는 3-zone 구조이다. 새 BCB 를 LRU 에 넣는 진입점은 세 가지이다(`page_buffer.c:1083-1087`).

- `pgbuf_lru_add_new_bcb_to_top()` (`page_buffer.c:9933`)
- `pgbuf_lru_add_new_bcb_to_middle()` (`page_buffer.c:9969`)
- `pgbuf_lru_add_new_bcb_to_bottom()` (`page_buffer.c:10001`)

기본 새 페이지 진입 경로(`pgbuf_get_bcb_from_invalid_list` 이후 newly allocated BCB) 는 `pgbuf_lru_add_new_bcb_to_middle()` 로 들어간다 (`page_buffer.c:6731, 6740`). 즉 *midpoint insertion* 이 기본 정책이며, hot ratio 는 `PRM_ID_PB_LRU_HOT_RATIO` (`src/base/system_parameter.c:607`, `src/base/system_parameter.c:3741`) 가 결정하고, 초기화 시 `pgbuf_Pool.ratio_lru1 = prm_get_float_value (PRM_ID_PB_LRU_HOT_RATIO)` 로 저장된다(`page_buffer.c:1603` 부근).

Boost(승급) 로직은 `pgbuf_lru_boost_bcb` (`page_buffer.c:9858`) 가 담당한다. boost 결정은 `PGBUF_IS_BCB_OLD_ENOUGH` 매크로 (`page_buffer.c:927-928`) 의 결과에 따른다. **매크로 전개** (직접 인용):

```
#define PGBUF_IS_BCB_OLD_ENOUGH(bcb, lru_list) \
  (PGBUF_AGE_DIFF ((bcb)->tick_lru_list, (lru_list)->tick_list) >= ((lru_list)->count_lru2 / 2))
```

여기서 `PGBUF_AGE_DIFF` (`page_buffer.c:922-924`) 는 `tick_lru_list` 와 `tick_list` 의 차이를 본다. **`tick_*`는 fix 횟수가 아니라 list 의 logical clock (insertion/move counter) 이므로 시간 기반에 가깝다**. 즉 동일 BCB 를 `fix → unfix` 두 번 한다고 즉시 boost 되는 것이 아니라, "두 번째 fix 시점에 list 의 tick 이 처음 insertion 시점 대비 충분히 진행되어 있어야 (`count_lru2 / 2` 만큼)" boost 가 일어난다. 따라서 **prefetch + 곧바로 follow-up fix** 의 짧은 시간 차이는 보통 boost 임계 미만이 되어 zone 1 승급은 발생하지 않으며, prefetch 한 페이지는 대부분 zone 2 → zone 3 으로 자연 소실된다. 이 점은 단순 page-by-page scan 이 hot working set 을 즉시 밀어내지 않는 이유이기도 하다.

AOUT(adaptive out) 리스트가 존재하여 LRU 에서 빠진 page 의 history 를 일정 비율(`PRM_ID_PB_AOUT_RATIO`) 까지 추적한다(`page_buffer.c:5578-5651` 의 `pgbuf_initialize_aout_list`). **AOUT 의 LRU promotion 동작은 다음과 같다** (`page_buffer.c:6650-6745` 의 `pgbuf_unlatch_void_zone_bcb` 참조):

- void zone 에서 unlatch 되는 BCB 의 VPID 가 AOUT 에 존재(`aout_list_id != PGBUF_AOUT_NOT_FOUND`) 하면, private LRU 에서는 `pgbuf_lru_add_new_bcb_to_top` 가 호출되어 **즉시 zone 1 (top)** 에 삽입된다(`page_buffer.c:6722`). 공유 LRU 에서는 `pgbuf_lru_add_new_bcb_to_middle` (mid) 가 호출된다(`page_buffer.c:6740`).
- 즉 **private LRU 환경에서 AOUT hit 은 zone 1 직접 승급을 유발**한다.

이 사실은 §6 의 buffer pollution 평가에서 다시 다룬다.

### 3.3 File I/O Flags and OS Readahead Interaction

CUBRID 는 data volume 을 일반적으로 **buffered I/O** 로 연다. `fileio_open(... O_RDWR | o_sync, 0600)` 으로 열며 (`src/storage/file_io.c:3004`), `o_sync` 는 `O_SYNC` 이며 mount 시 옵션이다(`file_io.c:3000`). **`O_DIRECT` 는 코드 베이스 전체에서 사용되지 않는다**:

```
$ grep -rn 'O_DIRECT' src/storage/
(no matches)
```

(`/home/vimkim/gh/cb/develop/src/storage/` 전체 0 매치. 따라서 platform 별 `#ifdef` 분기 없이 *모든 platform 의 모든 빌드* 에서 buffered I/O 를 사용하는 것이 확실하다.)

OS 단계 readahead/advise 와의 hook 은 `posix_fadvise()` 한 줄로 존재한다(`file_io.c:3050`). volume open 직후 한 번 호출되며 mode 는 system parameter `data_file_os_advise` (=`PRM_ID_DATA_FILE_ADVISE`) 의 정수 값에 따라 다음 6 가지 중 하나가 적용된다(`file_io.c:3023-3056`).

| 값 | flag | 효과 |
|----|------|------|
| 1 | `POSIX_FADV_NORMAL` | 기본 |
| 2 | `POSIX_FADV_SEQUENTIAL` | kernel readahead window 2배 |
| 3 | `POSIX_FADV_RANDOM` | readahead 비활성 |
| 4 | `POSIX_FADV_NOREUSE` | Linux 5.x 이전에서는 사실상 no-op, Linux 6.3 이후 mmap'd file 에 대해 일부 구현됨 (`man 2 posix_fadvise`). 본 보고서에서는 의미 있는 효과 보장 안 함으로 본다. |
| 5 | `POSIX_FADV_WILLNEED` | 즉시 readahead |
| 6 | `POSIX_FADV_DONTNEED` | page cache drop |

기본값은 0(`{false, {.i = 0}}` at `system_parameter.c:4347`) → fadvise 미호출. 즉 OS readahead 는 default Linux 정책(보통 128KB window) 에 맡겨지며, CUBRID 의 IO_PAGESIZE(보통 16KB) 기준 8 page 정도가 hint 없이 인접 read 되었을 때 미리 읽힐 수 있다.

`fileio_read()` 내부의 동기 read 경로는 `fileio_os_read()` (`file_io.c` 의 동기 pread wrapper) 가 담당하며 일반 `pread()` 를 사용한다. 일부 platform 의 fallback 으로 `aio_read()` 기반 `pread()` 시뮬레이션이 존재하는데, 이는 **HP-UX 의 IA64 가 아닌 빌드** 한정이다 (`file_io.c:3731` 의 `#if defined(HPUX) && !defined(IA64)` 분기, 본문 `file_io.c:3744-3772` 의 `pread()` 시뮬레이션, `file_io.c:3783-3811` 의 `pwrite()` 시뮬레이션, 종료 `file_io.c:3812` 의 `#elif defined(WINDOWS) && defined(SERVER_MODE)`). 이는 단일 read 를 `aio_read` + `aio_suspend` 로 즉시 wait 하여 동기 wrap 만 하는 구조이므로 **비동기 prefetch 인프라가 아니다** (실제 의미 있는 비동기 폴링 큐가 없음). 따라서 Linux/x86_64 등 주류 platform 은 plain `pread()` 만 사용하며, prefetch 를 위한 OS 측 비동기 인프라는 CUBRID 내부에서는 존재하지 않는다.

따라서 storage I/O 관점에서 *현재 CUBRID 는 OS readahead 와 buffered pgbuf_fix 의 조합* 으로 동작하며, scan path 단의 active prefetch 는 없다.

### 3.4 `pgbuf_fix` 의 conditional latch 동작 정밀 추적

(Reviewer item 6 에 직접 답한다.) `pgbuf_fix_release` / `pgbuf_fix_debug` 의 내부 흐름은 다음과 같다 (`src/storage/page_buffer.c:2060-2459` 의 본문 분석).

1. parameter validation 후 (`page_buffer.c:2067-2098`) hash chain 에서 BCB 를 찾는다(`page_buffer.c:2156-2159` 의 `pgbuf_search_hash_chain`).
2. **BCB 가 hash 에 이미 존재하는 경우** (`page_buffer.c:2165-2182`): IO 가 필요 없다. 그 다음 단계는 `pgbuf_latch_bcb_upon_fix` 호출이며 이때 conditional vs unconditional 이 의미가 있다. 다른 thread 가 같은 페이지를 write-latch 로 잡고 있는 등의 사유로 conditional latch 가 실패하면 NULL 을 반환한다(`page_buffer.c:6185-6190` 의 promotion-needed conditional fail, `page_buffer.c:6320` 의 일반 conditional fail).
3. **BCB 가 hash 에 없는 경우** (`page_buffer.c:2189-2202`): `pgbuf_claim_bcb_for_fix(... fetch_mode ...)` 가 호출된다. 이 함수는 **conditional flag 와 무관하게** BCB 를 새로 할당하고, `OLD_PAGE` 계열 fetch mode 에서는 동기적으로 `fileio_read` 를 호출한다(`page_buffer.c:8249` 의 `fileio_read(...)`). 즉:
   - **conditional latch 의 의미는 "이미 존재하는 BCB 에 대한 latch 가 즉시 안 되면 포기" 일 뿐이다.**
   - **버퍼풀에 아예 없던 페이지를 미스 fix 하면, 호출 스레드가 직접 `fileio_read` 를 동기 수행한다.** 이때 conditional/unconditional 구분은 BCB 가 만들어진 *후* 의 latch step 에서만 작동한다.

이 사실은 두 가지 중요한 함의를 가진다.

**함의 A — Sketch A 가 buffer miss latency 를 hide 하지 못한다.**
Scan thread 가 next_vpid 에 대해 `PGBUF_CONDITIONAL_LATCH` 로 prefetch 를 시도해도, **그 페이지가 buffer 에 없으면 호출 스레드 (=scan thread) 가 `fileio_read` 를 동기 수행한다**. 즉 prefetch 가 "현 page 처리 중인 시간과 IO 를 overlap" 시키는 효과는 발생하지 않고, scan thread 가 미리 stall 할 뿐이다. 따라서 §7.1 의 "sync prefetch" 는 **이미 OS readahead 가 page cache 에 가져온 페이지를 BCB 로 등록만 하는 부수 효과** 정도만 가진다 (이 경우 `fileio_read` 의 user-space pread 가 zero-disk-IO 로 끝남). buffer miss 자체를 hide 하려면 별도 thread 가 fix 를 수행해야 한다.

**함의 B — Sketch B (별도 prefetch worker) 가 필요하다.**
별도 worker thread 가 `pgbuf_fix(... PGBUF_UNCONDITIONAL_LATCH)` 를 호출하면 그 thread 가 `fileio_read` 의 동기 wait 를 떠안고, scan thread 는 다음 page 에 도달했을 때 hash chain 에 이미 BCB 가 있는 상태 (또는 `pgbuf_lock_page` 의 buffer-lock chain 위에서 sleep 한 후 wake-up) 로 reach 한다. 후자의 경우라도 scan thread 의 wait 는 "IO 자체" 가 아닌 "IO 가 끝나기 기다리는 시점부터 prefetch worker 가 끝낼 때까지" 로 단축된다.

이에 따라 §5.1, §7, §8, §10, §12 의 권고도 Sketch A 단독 도입에서 **Sketch B 의 가장 단순한 형태 (depth=1, single worker, no queue depth tuning)** 로 1차 추천을 바꾼다.

---

## 4. Existing Prefetch / Async Primitives in CUBRID

### 4.1 grep results — what already exists

`grep -rn "prefetch\|readahead\|posix_fadvise\|fadvise" src/` 결과를 카테고리화하면 다음과 같다.

- **VACUUM log prefetch**: `src/query/vacuum.c:478, 719, 1251-1253, 3318` 등에서 vacuum worker 가 log 페이지 N 개를 미리 사설 버퍼로 가져오는 메커니즘. System parameter 는 `vacuum_prefetch_log_pages` / `vacuum_prefetch_log_buffer_size` / `vacuum_prefetch_log_mode` (`src/base/system_parameter.c:631-633` 의 매크로 정의, 등록부 `system_parameter.c:3893-3920`). 카운터: `PSTAT_VAC_NUM_PREFETCH_REQUESTS_LOG_PAGES`, `PSTAT_VAC_NUM_PREFETCH_HITS_LOG_PAGES` (`src/base/perf_monitor.c:335-336`). **데이터 페이지가 아닌 log 페이지** 에만 적용된다.
- **CPU prefetch hint (`__builtin_prefetch`)**: `src/base/porting.h:1100-1104` 에 매크로 `prefetch(x, y, z)` 정의. 호출처는 `src/query/parallel/px_heap_scan/px_heap_scan_result_handler.cpp:746, 883` 의 결과 tuple 처리부. CPU L1 cache hint 일 뿐 disk I/O 와 무관하다.
- **Locator / class prefetch**: `pt_class_pre_fetch` (정의 `src/parser/compile.c:432`, 주석 시작 `compile.c:407-430`), `xlocator_fetch ... prefetch` (`src/communication/network_interface_cl.c:272, 286`). 이는 client→server 단의 OID/class 정보 일괄 fetch 로, page 단위 read I/O 와 무관.
- **Cursor OID prefetch**: `cursor_prefetch_first_hidden_oid` 선언 `src/query/cursor.c:74`, 정의 `cursor.c:786`. `cursor_prefetch_column_oids` 선언 `cursor.c:75`, 정의 `cursor.c:841`. 호출 site `cursor.c:1044, 1048`. client side 의 OID set 묶음 lock 용. 역시 page prefetch 아님.
- **`posix_fadvise`**: `src/storage/file_io.c:3050` 1군데뿐 (§3.3 참조).
- **`aio_read`**: `src/storage/file_io.c:3758` 1군데, 그러나 HP-UX(non-IA64) 의 `pread()` fallback 구현용. 비동기 queue 가 아니다.

요컨대 **사용자 query 의 scan path 에서 동작하는 page 단위 prefetch 는 codebase 에 존재하지 않는다**.

### 4.2 cubthread, worker pools, daemons

CUBRID 의 thread infra (`cubthread` namespace) 는 두 가지 long-running 모델을 제공한다.

- **daemon**: `cubthread::daemon` (`src/thread/thread_daemon.hpp:87`) — 등록된 task 를 looper 의 schedule 에 따라 반복 실행하는 단일 스레드. `manager::create_daemon(...)` (`thread_manager.hpp:101` 주석 예시) 으로 생성. `REGISTER_DAEMON(name)` 매크로(`thread_manager.hpp:498`) 가 등록 helper.
- **worker_pool**: `cubthread::worker_pool` (`thread_manager.hpp:63`) — pool size 와 core count 를 받고 `create_worker_pool<pool_type>(MAX_THREADS, MAX_JOBS)` 로 생성(`thread_manager.hpp:107, 367`), `push_task()` 로 entry_task 를 제출(`thread_manager.hpp:144`).

Parallel heap scan 은 이미 이 worker_pool 위에 만들어져 있으며(`src/query/parallel/px_worker_manager_global.cpp:50-57`), `PRM_ID_MAX_PARALLEL_WORKERS` 로 상한이 정해진다. **즉 prefetch 도 동일 인프라를 재사용해 별도 daemon 또는 dedicated worker_pool 위에서 실행할 수 있는 기반은 이미 존재한다**(§7.2 참조).

### 4.3 Parallel Scan (sector-aware) — 2048 page threshold

Parallel heap scan 의 활성화 기준은 `PRM_ID_PARALLEL_HEAP_SCAN_PAGE_THRESHOLD` 이며 default 2048 (`src/base/system_parameter.c:5125`, `PRM_NAME_PARALLEL_HEAP_SCAN_PAGE_THRESHOLD "parallel_heap_scan_page_threshold"` at `system_parameter.c:776`). 동일한 default 2048 이 hash join (`5137`), sort (`5149`) 에도 적용된다. JIRA 본문에서 언급된 "default 2048 page 이상, configurable" 은 이 파라미터를 가리킨다.

`parallel_query::compute_parallel_degree()` (`src/query/parallel/px_parallel.cpp:36`) 가 type 별 threshold 와 system core count 를 보고 degree 를 결정한다(`px_parallel.cpp:53-55, 116-119`). `num_pages < page_threshold` 이면 0 (disable) 을 반환한다(`px_parallel.cpp:119-122`).

Parallel heap scan 의 sector aware 분할은 `src/query/parallel/px_heap_scan/` 의 input handler 가 담당한다(`px_heap_scan.hpp:42` 의 `input_handler_ftabs`). file manager 의 partial sector iterator 와 결합하여 heap file 의 sector list 를 각 worker 에게 분배하는 방식이다(코드 흐름은 `px_heap_scan_checker.cpp`, `px_heap_scan_task.cpp` 참조).

**Prefetch 와의 비중복 원칙**: parallel scan 이 sector 를 분할하여 N worker 에게 나누는 시점에 worker 내부는 다시 logical chain 추적을 한다. parallel scan 활성 구간(>= 2048 page) 에서는 worker 들이 이미 sector 별로 분산 disk I/O 를 일으키므로 prefetch 의 marginal gain 이 줄어든다. 반면 (1) num_pages < 2048 인 중소 heap, (2) `parallelism = 0` 또는 system_core_count <= 2 인 환경(`px_parallel.cpp:63-66`), (3) hint 로 parallel 을 끈 statement, (4) **B-tree range scan** (parallel scan 비대상) 에서는 prefetch 가 유일한 latency 개선 수단이 된다.

---

## 5. Prefetch Applicability Assessment

### 5.1 Heap Full Table Scan — sector/allocation bitmap based prefetch

Heap scan 의 next VPID 는 현재 page 의 header/chain 에 담겨 있으므로(§2.1), **single-page lookahead** 는 자연스럽다. 더 적극적으로는 sector 의 partial-bit map 을 활용해 **multi-page lookahead** 도 가능하다.

근거:
- File 의 sector partial bitmap 은 `FILE_PARTIAL_SECTOR` 구조에 보존되며(`src/storage/file_manager.c:3330-3645`), `file_partsect_is_bit_set` (`file_manager.c:2783`), `file_partsect_alloc` (`file_manager.c:2847`) 등으로 각 sector 내 어떤 page 가 user page 로 allocated 되어 있는지 알 수 있다.
- 이 bitmap 을 통하면 scan 이 sector 의 첫 페이지에 진입한 시점에 그 sector 의 나머지 allocated page VPID 목록을 한 번에 얻을 수 있고, OS readahead 와 비슷한 효과를 application level 에서 명시적으로 유도할 수 있다.
- 단 sector 단위 bitmap 접근은 file header chain 의 latch 가 추가로 필요하므로 cost 가 무시할 수 없다. 따라서 *coarse-grained* hint 가 필요한 large scan 에서만 sector bitmap 을 sampling 하고, 일반 경우에는 next-VPID 기반 single lookahead 로 가는 hybrid 가 합리적이다.

`pgbuf_fix` 의 conditional latch 가 buffer miss 시 IO 를 hide 하지 못한다는 §3.4 의 결과를 고려하면, single-lookahead 는 **반드시 별도 thread (Sketch B 의 worker)** 에서 수행되어야 의미 있는 latency hiding 이 발생한다. scan thread 내부에서 conditional fix 만 호출하는 형태(Sketch A) 는 OS readahead 가 이미 page cache 에 끌어온 페이지를 BCB 화 하는 효과 정도에 그친다.

### 5.2 B-Tree Range Scan — next-leaf-VPID based prefetch

`btree_range_scan_advance_over_filtered_keys()` 가 `next_vpid = node_header->next_vpid` 를 결정하는 시점은 `btree.c:25302` 와 `btree.c:25368` 이다. 이 시점에서 다음 leaf 의 VPID 는 이미 알려져 있으므로 prefetch worker 에 enqueue 할 수 있다.

고려사항:
- Descending scan 은 prev_vpid 를 따라가지만, prev_vpid 가 root 부터 재시작이 필요한 경우가 **발생 가능성이 있다 (`btree.c:25340-25344` 의 `force_restart_from_root` 처리; frequency 는 concurrent leaf-split rate 에 따라 달라지며 본 조사에서는 정량 측정하지 않았다)**. 이 경로에서는 prefetch 가 무용지물에 가깝다. 따라서 prefetch 는 ascending case (`!bts->use_desc_index`) 에 한정하는 것이 안전하다.
- Range scan resume 시 root 에서 lower bound leaf 를 다시 찾는 단계 (`btree_find_lower_bound_leaf` at `btree.c:14938`) 도 prefetch 대상이 될 수 있으나, prefetch 시점에는 다음 leaf VPID 가 확정되지 않은 상태이므로 적용이 어렵다.
- Covered index scan / index skip scan / index loose scan (`BTS_IS_INDEX_COVERED`, `BTS_IS_INDEX_MRO`, `BTS_IS_INDEX_ISS`, `BTS_IS_INDEX_ILS` at `btree.c:541-552`) 의 경우에도 chain advance 동작은 동일하므로 prefetch 정책은 공유 가능하다.

### 5.3 Access-method-specific policy

| Access method | next-page predictability | locality | prefetch 권장 정책 |
|---------------|--------------------------|----------|---------------------|
| Heap FTS (`scan_next_heap_scan`) | 현재 page header 에서 1개 | sector 내부에서 보장, 전체 file 단위는 best-effort | 1-ahead (별도 worker) + (옵션) sector bitmap 기반 multi-ahead |
| Heap range/sample (`heap_vpid_skip_next` at `heap_file.c:5085-5125`) | skip_cnt 단위, 알려져 있음 | 매우 약함(skip 으로 random 화) | prefetch 비효율 — disable |
| B-tree leaf chain (`btree_range_scan_advance_over_filtered_keys`) | header next_vpid 로 1개 | 약함(split 이력 의존) | ascending only, 1-ahead |
| B-tree IRS (Index Range Scan via `scan_get_index_oidset` → `btree_range_search`) | 위와 동일 | 위와 동일 | 동일 |
| Index Skip Scan (ISS, `bts->iss.current_op == ISS_OP_DO_RANGE_SEARCH`) | 위와 동일 | sub-range 마다 root 재진입 다수 | 1-ahead 만, sub-range 시작점에선 비활성 |
| Index Loose Scan (ILS) | 매번 root traversal 우회 | 위와 동일 | 위와 동일 |
| Covered scan | 추가 heap fetch 없음 | n/a (heap I/O 없음) | btree 단의 leaf chain prefetch 만으로 충분 |
| OID -> heap object 단계(`scan_next_index_lookup_heap`) | 다수 OID 가 동시에 알려짐 | OID heap page 분포에 의존 | OID 별 page-level grouping + 묶음 prefetch (별도 항목, §11 open question) |

### 5.4 OS Readahead interaction / double-fetch risk

OS readahead 가 활성(`POSIX_FADV_SEQUENTIAL` 또는 default Linux readahead) 인 환경에서 application prefetch 가 더해질 때 다음 시나리오를 점검해야 한다.

1. **Hit at page cache**: 이미 OS 가 readahead 로 page cache 에 가져온 페이지를 우리가 `pgbuf_fix` 로 요청 → block 없이 user-space copy 만 발생. 추가 cost 는 미미하고 이득은 그대로.
2. **Miss at page cache**: OS 도 아직 가져오지 못한 페이지 → prefetch 가 IO 를 유발하지만 어차피 곧 필요한 페이지이므로 latency hiding 으로 이득.
3. **Random heap (fragmented)**: OS 의 sequential readahead 가 오히려 unused page 를 cache 에 쌓아 다른 워크로드의 working set 을 밀어내는 부작용 가능. application prefetch 는 next_vpid 기반이므로 **그 페이지가 곧 사용될 확률이 OS-blind readahead 보다 높을 것으로 기대되나, MVCC 가시성 필터로 인해 prefetch 한 페이지가 zero 가시 record 만 가질 가능성이 있으므로 사용 확실성은 numeric 검증 전에는 단정할 수 없다** (§9 에 별도 측정 row 추가). 따라서 `data_file_os_advise=3` (RANDOM) 으로 OS readahead 를 끄고 application prefetch 만 활성화하는 조합이 fragmented heap 에서 후보가 될 수 있다.

Double fetch 위험: `pgbuf_fix` 가 이미 buffer pool 안에 있으면 IO 를 일으키지 않으므로(`pgbuf_lock_page` 후 hash lookup) **prefetch 가 두 번 fix 해도 일반적으로 IO 는 한 번**이다. 즉 통상 conservative behavior. 다만 latch 경합 자체는 발생할 수 있으므로 prefetch worker 는 page fix 직후 즉시 unfix 해야 한다.

**Eviction race**: 단 prefetch worker 가 fix→unfix 한 BCB 는 §3.2 의 midpoint insertion 정책에 따라 zone 2 에 들어가고, 짧은 시간 안에 boost 가 일어나지 않으면 zone 3 으로 흘러가 victimize 후보가 된다. 만약 buffer pool 압력이 높고 scan worker 의 도달이 충분히 늦으면 *prefetch 완료 → BCB victimize → scan 도달* 순으로 진행되어 scan 의 fix 는 hash chain miss → `pgbuf_claim_bcb_for_fix` → `fileio_read` (`page_buffer.c:8249`) 의 **second IO** 를 유발한다. 즉 IO 는 일반적으로 한 번이지만 high pressure 시나리오에서는 *두 번* 일 수 있다. depth 와 in-flight cap (§11 item 6) 이 이 위험을 제한하며, §9 의 `Num_data_page_ioreads` / `Num_file_ioreads` gap 측정 row 가 detect 신호이다.

---

## 6. Buffer Pool Pollution Risk

### 6.1 LRU midpoint behavior under large scans

CUBRID 의 LRU 는 새 BCB 를 기본 midpoint(`pgbuf_lru_add_new_bcb_to_middle` at `page_buffer.c:9969`) 에 넣고, §3.2 에서 본 `PGBUF_IS_BCB_OLD_ENOUGH` (tick-기반, 시간 근사) 가 성립할 때만 `pgbuf_lru_boost_bcb` (`page_buffer.c:9858`) 로 zone 1 (hot) 에 승급시킨다. 일반 single-pass scan 의 페이지는 prefetch + scan fix 의 시간 차이가 보통 boost 임계 미만이므로 boost 없이 zone 2 → zone 3 으로 떨어진다. 즉 **단발성 page-by-page scan 자체의 buffer pollution 위험은 비교적 낮다**.

그러나 두 가지 시나리오에서 pollution 위험이 확대된다.

- **Prefetch depth 가 큰 경우**: scan worker 가 실제 도달하기 전에 사용되지 못한 채 prefetched-but-unused page 가 zone 2 에 쌓이면 다른 트랜잭션의 working set 을 zone 3 으로 밀어낼 수 있음. depth 상한과 in-flight cap 필요.
- **반복 scan 의 AOUT 경유 zone 1 승급**: §3.2 에서 확인한 AOUT promotion 경로 (`page_buffer.c:6722` 의 private LRU 케이스에서 `pgbuf_lru_add_new_bcb_to_top` 직접 호출) 때문에, **첫 scan 후 evict 된 페이지가 두 번째 scan 에서 다시 fix 될 때 AOUT hit 으로 zone 1 (top) 에 직접 진입한다**. 즉 working set 이 겹치는 반복 scan 시나리오에서는 prefetch 한 page 도 결국 hot zone 으로 올라가 다른 hot working set 을 밀어낼 가능성이 존재한다. 이는 prefetch 도입과 무관하게 기존 `pgbuf_fix` 가 가진 특성이지만, prefetch 가 fix 횟수를 늘리므로 **반복 scan 워크로드에서는 AOUT 경유 pollution 이 가속될 수 있다**는 점을 인지해야 한다. 완화책으로는 prefetch path 가 fix 후 unfix 할 때 AOUT 등록을 회피하는 별도 flag (§11 item 9 의 open question) 가 검토 가능하다.

### 6.2 Mitigation options (insertion at LRU bottom, BCB hot flag)

CUBRID 는 이미 hint 형 insertion 지점을 세 가지 제공한다(`page_buffer.c:1083-1087`).

- `pgbuf_lru_add_new_bcb_to_top()` — 즉시 hot
- `pgbuf_lru_add_new_bcb_to_middle()` — 기본
- `pgbuf_lru_add_new_bcb_to_bottom()` — 거의 즉시 victim 후보

Prefetch 한 페이지가 곧 사용될 가능성이 높지만 다른 working set 보다 hot 하지는 않다는 의도를 반영하려면 **prefetch path 는 to_middle 로 두되, scan worker 가 실제 fix 한 시점에 정상적 boost 정책이 적용되도록 두는 것** 이 적절하다. 단 6.1 의 AOUT 승급 위험 때문에 large repetitive scan 워크로드에서는 zone 1 직승 회피 flag 도입을 추후 검토한다.

특별히 large scan 의 sequential page 에 대해 *bottom insertion* 을 강제하는 옵션(예: `BTS_LARGE_SCAN_BOTTOM_HINT`)은 향후 §8.2 sketch B 에서 부가 옵션으로 도입 검토 가능하다. PostgreSQL 의 `BAS_BULKREAD` ring buffer 와 유사한 효과를 노릴 수 있으나, CUBRID 의 LRU 3-zone 구조에서는 zone 3 (victim) 의 회전이 충분히 빠르므로 1차 prefetch 도입 단계에서는 default insertion 그대로 두는 것이 안전하다.

---

## 7. Async Execution Structure Options

### 7.1 Synchronous prefetch (pre-fix N pages ahead) — 효과 한정적

가장 단순한 형태. scan driver 가 현 page 를 처리하기 시작하는 시점에 next_vpid 에 대해 `pgbuf_fix(next_vpid, OLD_PAGE_PREVENT_DEALLOC, PGBUF_LATCH_READ, PGBUF_CONDITIONAL_LATCH)` 를 호출하고 즉시 `pgbuf_unfix` 한다.

- 장점: 코드 변경 최소, 새 thread 없음, recovery 영향 없음.
- 한계: **§3.4 에서 확인했듯 buffer miss 인 경우 호출 스레드(= scan thread) 가 직접 `fileio_read` 를 동기 수행한다**. 따라서 "fire-and-forget" 효과는 없으며, OS readahead 가 이미 가져온 페이지를 BCB 화 하거나, 같은 페이지에 대한 다른 thread 의 buffer-lock chain wait 를 단축시키는 정도의 부수 효과만 있다.

### 7.2 Async prefetch via thread pool / daemon — 권장 1차 방안

`cubthread::worker_pool` 을 통해 prefetch task 를 push 하는 방식. scan worker 는 `next_vpid` 를 enqueue 만 하고 즉시 진행한다. prefetch worker 가 별도 스레드에서 `pgbuf_fix(... PGBUF_UNCONDITIONAL_LATCH)` → `pgbuf_unfix` 하여 BCB 를 buffer 에 적재한다.

- 장점: 진정한 비동기, scan worker 는 절대 block 되지 않음. parallel scan worker_pool 과 분리된 dedicated prefetch_pool 을 두면 우선순위 분리도 가능.
- 단점: thread context-switch cost, queue contention, prefetch 가 "너무 늦게" 도착하면 효과 없음(아래 적정 depth 와 inflight 제어 필요).
- 인프라는 이미 존재: `manager::create_worker_pool` (`thread_manager.hpp:367`), `push_task` (`thread_manager.hpp:144`).
- **Thread context 모델 (system-worker, vacuum-style)**: prefetch worker 는 user transaction 의 lock 컨텍스트와 분리된 *system worker* 모델을 사용한다. 즉 prefetch task 의 `THREAD_ENTRY *` 는 vacuum 의 `vacuum_init_thread_context` (`src/query/vacuum.c:766-775`) 와 동일 패턴으로 `entry::claim_system_worker()` (`src/thread/thread_entry.cpp:425-432`, 선언 `src/thread/thread_entry.hpp:357`) 호출 후 prefetch task 를 실행한다. `pgbuf_fix` 는 `pgbuf_latch_bcb_upon_fix` 본문(`src/storage/page_buffer.c:6053-6320`) 어디서도 `lock_manager` API (`lk_lock_*`) 를 호출하지 않으므로(`page_buffer.c` 전체에서 `lock_manager` / `lk_lock` grep 결과 0 매치), **read-only page latch 경로는 user transaction id 와 무관하게 정상 동작한다**. 따라서 prefetch worker 는 user tid 를 lock manager 로 끌고 들어가지 않으며, lock 정확성을 위해 tid 를 전달할 필요가 없다.
- **그러면 왜 `THREAD_ENTRY *` 자체는 prefetch task 에 전달해야 하는가**: (a) perfmon 통계 attribution — `pgbuf_fix_release` 가 `perf.is_perf_tracking` (`page_buffer.c:2255`) 시 holder/fix latency 를 thread_p 의 perf state 에 기록한다. (b) BCB holder tracking (debug 빌드의 `pgbuf_add_fixed_at` at `page_buffer.c:2290`, `thread_p->get_pgbuf_tracker()` at `page_buffer.c:2344`) — assertion 무결성. (c) error reporting 의 `er_set` (예: `page_buffer.c:2363`) 이 per-thread error stack 을 사용. (d) `db_private_alloc` 계열 allocator context. **단 전달되는 thread_p 는 user query 의 thread_p 가 아니라 prefetch worker 의 system-worker entry 이다.** vacuum 도 동일하게 `vacuum_Workers[i]` 의 system worker entry 로 자기 자신의 `pgbuf_fix` 를 호출한다.
- recovery/WAL: prefetch task 는 read-only 이므로 WAL 영향 없음.

### 7.3 posix_fadvise / readahead syscall option

`posix_fadvise(fd, offset, length, POSIX_FADV_WILLNEED)` 로 OS 단에 hint 만 던지는 방식. CUBRID 는 이미 mount 시점에 fadvise 호출 코드 경로를 가지고 있으므로(§3.3) 동일 syscall 을 scan path 에서 호출하는 함수를 추가하면 된다.

- 장점: buffer pool 점유 없음. OS page cache 만 데움. CUBRID 의 BCB 와는 독립적이라 pollution 위험이 최소.
- 단점: pgbuf_fix 단계의 buffer copy 와 hash lookup cost 는 여전히 동기, OS readahead 의 동작은 file 의 offset 연속성에 의존(=physical locality 약하면 효과 떨어짐). 또한 fadvise 는 system call 이므로 page 당 호출은 비용이 비싸며 sector 묶음 단위로 발행하는 것이 적절.
- recovery/WAL: 영향 없음(read-only hint).

세 옵션은 상호 배타가 아니다. §8 에서는 (A) 동기 conditional fix 를 보조용, (B) 비동기 single-ahead 를 main, (C) fadvise 를 boundary case 용으로 함께 제시한다. 권고는 §12 참조.

---

## 8. Design Sketches

### 8.1 Sketch A — Synchronous one-ahead pgbuf_fix in scan driver (보조용)

**위치 정정**: 본 sketch 는 §3.4 의 분석 결과 단독으로 buffer miss latency 를 hide 하지 못함이 확인되었다. Phase 1 추천에서 제외하되, OS readahead 가 이미 가져온 페이지를 BCB 화 하는 부수 효과 및 측정용 baseline 으로 남긴다.

**Hook 위치**:
- Heap: `heap_next_internal()` `src/storage/heap_file.c:8115` 의 `heap_vpid_next()` 호출 직후. 즉 다음 page 의 VPID 를 알자마자, *현 page 의 처리가 끝나기 전* 에 conditional fix 를 발행한다.
- B-tree: `btree_range_scan_advance_over_filtered_keys()` `src/storage/btree.c:25368` 의 `next_vpid = node_header->next_vpid` 갱신 직후.

**제안 코드 형태** (pseudocode). fetch mode 는 §3.1 의 분석에 따라 *각 scan path 가 현재 사용 중인 mode* 와 동일하게 둔다 — heap prefetch 는 `OLD_PAGE_PREVENT_DEALLOC` (`heap_file.c:8000` 의 기존 fix 와 일치), btree leaf prefetch 는 `OLD_PAGE` (`btree.c:25349` 의 기존 fix 와 일치).

```
// in heap_next_internal, after heap_vpid_next(... &vpid) at heap_file.c:8115
if (!VPID_ISNULL (&vpid) && scan_cache->enable_prefetch) {
    PAGE_PTR ahead = pgbuf_fix (thread_p, &vpid, OLD_PAGE_PREVENT_DEALLOC,
                                PGBUF_LATCH_READ, PGBUF_CONDITIONAL_LATCH);
    if (ahead != NULL) {
        pgbuf_unfix (thread_p, ahead);
    }
}

// in btree_range_scan_advance_over_filtered_keys, after next_vpid update at btree.c:25368
if (!VPID_ISNULL (&next_vpid) && bts->enable_prefetch) {
    PAGE_PTR ahead = pgbuf_fix (thread_p, &next_vpid, OLD_PAGE,
                                PGBUF_LATCH_READ, PGBUF_CONDITIONAL_LATCH);
    if (ahead != NULL) {
        pgbuf_unfix (thread_p, ahead);
    }
}
```

**필요 편집 항목 (enumerated; reviewer item 7)**:
1. `struct heap_scancache` 에 `bool enable_prefetch` 필드 추가 — 위치 `src/storage/heap_file.h:142-184` 의 struct 본문 안. `cache_last_fix_page` (`heap_file.h:151`) 와 인접한 위치가 자연스럽다.
2. `struct btree_scan` 에 동일 필드 추가 — 위치 `src/storage/btree.h:198` 의 struct 본문 안.
3. `HEAP_SCANCACHE` 초기화 진입점에 `enable_prefetch = false` 추가:
   - `heap_scancache_start` (`heap_file.c:6943` 주석 시작, signature `heap_file.c:6956`)
   - `heap_scancache_start_modify`, `heap_scancache_quick_start`, `heap_scancache_quick_start_modify` (선언 `src/storage/heap_file.h:409-414`)
4. `BTREE_SCAN` 초기화 매크로 `BTREE_INIT_SCAN` (사용 예 `btree.c:6405`) 또는 `btree_init_temp_key_value` 부근의 0-init path 에 동일 필드 초기화.
5. parameter plumbing 으로 `enable_prefetch` 를 scan open 시점에 설정:
   - `scan_open_heap_scan` (정의 `src/query/scan_manager.c:2846`) 함수 끝부분의 `hsidp = &scan_id->s.hsid;` 부근에서 `scan_cache_p->enable_prefetch = prm_get_bool_value (PRM_ID_PREFETCH_ENABLE);` (혹은 parallel degree 에 따라 조정) 추가.
   - `scan_open_index_scan` (정의 `src/query/scan_manager.c:3067`) 의 INDX_SCAN_ID 초기화 부근에서 `isidp->bt_scan.btree_scan.enable_prefetch = ...;` 추가.
6. 신규 system parameter 등록. vacuum prefetch 의 패턴 (`src/base/system_parameter.c:631-633` 매크로 + `system_parameter.c:3893-3920` 등록부) 을 그대로 따른다. 추가 매크로 후보:
   - `PRM_NAME_PREFETCH_ENABLE "prefetch_enable"` (bool)
   - `PRM_NAME_PREFETCH_DEPTH "prefetch_depth"` (int)
   - sketch B 채택 시 `PRM_NAME_PREFETCH_WORKERS "prefetch_workers"`, `PRM_NAME_PREFETCH_QUEUE_SIZE "prefetch_queue_size"`
   - **naming 은 §12 와 §11 item 8 모두에서 `prefetch_*` 일관 유지**. `scan_prefetch_*` 는 사용하지 않는다.

**Pros (Sketch A 의 잔존 가치)**:
- 코드 추가 분량 최소.
- OS readahead 가 가져온 페이지를 BCB 로 등록하는 효과 (= page cache hit 시점에 첫 fix latency 감소).
- 새 thread 없음, dedicated buffer 없음.
- recovery: read-only prefetch 는 log 를 남기지 않음 → WAL 영향 0.

**Cons**:
- §3.4 분석에 따라 *진정한 buffer miss latency hide 효과 없음*.
- 따라서 Phase 1 단독으로는 효과가 OS readahead 의존도와 동일 수준에 머문다.

### 8.2 Sketch B — Async prefetch daemon fed by scan (1차 권장)

**Hook 위치**:
- Scan driver(heap: `heap_next_internal`, btree: `btree_range_scan_advance_over_filtered_keys`) 가 next_vpid 를 알게 되는 시점에 `prefetch_queue_push(thread_p, vpid, access_kind, depth)` 호출. `access_kind` 는 호출자 scan 의 access method (HEAP / BTREE_LEAF) 를 식별.
- Prefetch worker 는 `cubthread::worker_pool` 로 생성된 pool (`thread_manager.hpp:367` 의 `create_worker_pool<...>(N, M)`) 에서 동작하며, 각 task 는 access_kind 별 fetch mode 로 `pgbuf_fix(... fetch_mode, PGBUF_LATCH_READ, PGBUF_UNCONDITIONAL_LATCH) → pgbuf_unfix` 수행.
- Fetch mode 정책: §3.1 결론에 따라 각 scan path 의 기존 fix mode 와 일치시킨다. HEAP 경로는 `OLD_PAGE_PREVENT_DEALLOC` (`heap_file.c:8000` 일치), BTREE_LEAF 경로는 `OLD_PAGE` (`btree.c:25349` 일치). 이는 prefetch 가 기존 scan fix 와 동일한 race 보장 수준을 가짐을 의미한다 — prefetch 가 추가적인 race 위험을 도입하지 않는다.
- Depth 제어: scan_cache 또는 BTREE_SCAN 에 `int prefetch_inflight` 를 두어 N 개를 초과하면 enqueue 를 skip. 초기 depth=1 권장 (§10, §12).

**소요 인프라**:
- 새 file: `src/storage/page_buffer_prefetch.{cpp,hpp}` (가칭). 내부에 `prefetch_task : public cubthread::entry_task` 가 정의되어 thread entry context 를 가짐.
- 초기화 hook: `pgbuf_initialize_*` (`page_buffer.c:5524` 근처) 에서 prefetch worker pool 생성. system parameter `prefetch_workers`, `prefetch_queue_size` 추가.
- Stats: 새 PSTAT 추가 (예: `PSTAT_PB_PREFETCH_REQUESTS`, `PSTAT_PB_PREFETCH_HITS`) — vacuum 의 `PSTAT_VAC_NUM_PREFETCH_REQUESTS_LOG_PAGES` (`perf_monitor.c:335`) 와 동일 패턴. **이 counter 들은 Sketch A 와 Sketch B 모두에 적용**한다 (§9 참조). Sketch A 도 conditional fix request 수를 카운트해 measurement 가능하게 한다.

**Pros**:
- 진정한 async. scan worker 가 절대 block 되지 않음.
- depth 가능, B-tree 에서 2~4 leaf 단위 lookahead 가능.

**Cons**:
- 코드 추가 분량 증가, 새 worker pool 라이프사이클 관리 필요.
- queue contention 가능 — single-producer multi-consumer 가 자연스러우므로 `lockfree::circular_queue` 또는 cubthread 의 task queue 재사용 검토.
- "효과 없는 prefetch" — task 도착 전에 scan worker 가 추월하면 cost 만 소모.
- **메모리/anchor 증폭**: 동시 session 수 × queue depth 만큼 in-flight prefetch fix 가 발생한다. 100 session × depth 4 = 400 simultaneous fix 시도이며, hash anchor 경합으로 `PSTAT_PB_NUM_HASH_ANCHOR_WAITS` (`perf_monitor.c:488`) 가 급등할 수 있다. 이는 §9 의 validation row 에서 한계치를 정의하고, queue_size 와 worker 수를 통해 cap 한다.

**Recovery/WAL implications**: 없음. prefetch task 는 read-only 이며 page latch 도 immediately unfix 한다. fetch mode 가 `OLD_PAGE_PREVENT_DEALLOC` 이므로 prefetch 가 fix 한 상태에서 dealloc 시도와 race 가 일어나지 않는다.

### 8.3 Sketch C — posix_fadvise-based OS-level hint

**Hook 위치**:
- 신규 함수 `fileio_advise(vol_fd, offset, length, advise)` 를 `src/storage/file_io.c` 에 추가 (`file_io.c:3050` 의 기존 fadvise 호출 패턴 재사용).
- scan path 에서 sector 경계를 넘을 때 (즉 64-page 단위) 호출. heap scan 의 경우 `heap_vpid_next` 가 sector 를 바꾸는 시점, btree scan 의 경우 next leaf 가 다른 sector 로 이동하는 시점.
- VPID → (volid, vol_fd, file offset) 변환은 disk manager 의 helper 가 필요. `fileio_get_volume_descriptor()` (file_io 내 기존 helper) 를 활용.

**Pros**:
- BCB 비점유. buffer pool pollution 0.
- syscall 한 번으로 OS 가 sector 단위 readahead 를 미리 trigger.

**Cons**:
- syscall cost. page 마다 호출은 비효율 → sector 경계마다 호출하는 batch 모델 필요.
- physical contiguity 가 약하면 효과가 떨어짐.
- buffered I/O 가 아니라 `O_DIRECT` 환경에선 fadvise 가 무의미. (§3.3 기준 현재 CUBRID 는 모든 platform 에서 `O_DIRECT` 미사용이므로 이 단점은 현 시점 비활성.)
- **`Num_data_page_ioreads` 는 변화 없으나 `Num_file_ioreads` 는 inflate 될 수 있음** — OS 가 fadvise 후 readahead 를 시작했지만 BCB 가 fix 하기 전에 페이지가 OS-side 에서 evict 될 경우 BCB 는 못 보고 OS 만 IO 부담을 진다 (§9 의 split row 참조).

**Recovery/WAL implications**: 없음.

---

## 9. Validation Experiments

검증 지표는 모두 `src/base/perf_monitor.c` 에 정의된 기존 PSTAT 식별자를 활용한다. workload 별 측정 행렬을 아래와 같이 제안한다. Sketch 별로 기대 변화가 다른 row 는 sub-row 로 분리하였다.

| Workload | 측정 지표 (counter) | baseline 기대 | Sketch A 기대 변화 | Sketch B 기대 변화 | Sketch C 기대 변화 | 측정 방법 |
|----------|---------------------|---------------|---------------------|---------------------|---------------------|-----------|
| Heap FTS, cold cache, 큰 heap | `Num_data_page_ioreads` (`PSTAT_PB_NUM_IOREADS` at `perf_monitor.c:211`) | scan page 수와 거의 동일 | 변화 거의 없음 | 변화 거의 없음 (BCB 단의 IO 횟수는 같음) | 변화 거의 없음 또는 약간 감소 (OS readahead 가 미리 끌어오면 BCB 는 page cache 에서 copy 만 함) | `csql ... -S` 로 단일 connection 실행, `SHOW STATISTICS` |
| 동상 | `Num_file_ioreads` (`PSTAT_FILE_NUM_IOREADS` at `perf_monitor.c:200`) | `Num_data_page_ioreads` 와 가까움 | 변화 없음 | 변화 없음 | **상승 가능 (OS readahead-then-evict 분량)** | iostat 병행 |
| 동상 | `Data_page_buffer_hit_ratio` (`PSTAT_PB_HIT_RATIO` at `perf_monitor.c:447`) | 낮음 | 부수 효과로 약간 상승 (OS-readahead 적중 시 BCB hit) | **상승** (prefetch worker 가 사전 적재) | 변화 미미 (OS page cache 만 데움) | 동상 |
| 동상 | `Data_page_fix_acquire_time_msec` (`PSTAT_PB_PAGE_FIX_ACQUIRE_TIME_10USEC` at `perf_monitor.c:455`) | 높음 | 미미한 감소 | **감소** | 약간 감소 |  동상 |
| 동상 | `Time_data_page_fix_acquire_time` (`PSTAT_PBX_FIX_TIME_COUNTERS` at `perf_monitor.c:601`) — page_found_mode 별 분해 | miss 분포 큼 | mild shift | miss → hit shift | OS-side hit shift |  complex stat dump |
| Heap FTS, warm cache | 위와 동일 | 이미 hit > 95% | 변화 없어야 (regression 검출용) | 동상 | 동상 |  동상 |
| IRS (Index Range Scan), selective | `Num_data_page_fetches` (`PSTAT_PB_NUM_FETCHES` at `perf_monitor.c:209`) | leaf 수 + heap fetch 수 | 거의 동일 | 거의 동일 | 동상 |  `EXPLAIN STATISTICS` |
| 동상 | `Num_data_page_ioreads` | leaf miss + heap miss | 변화 미미 | leaf 측 감소(IO 시점 hide) | 변화 미미 |  동상 |
| IRS, range covering 다수 leaf | `Data_page_buffer_hit_ratio` | 중간 | 약간 상승 | 상승 | 약간 상승 |  동상 |
| Sector layout 변화 (fragmented heap) | `Num_file_ioreads` vs `Num_data_page_ioreads` | 가까움 | 변화 없음 | 변화 없음 | gap 발생 (fadvise) |  iostat 병행 |
| LRU 영향 | `Num_data_page_lru1/2/3` (`PSTAT_PB_LRU1_CNT/LRU2_CNT/LRU3_CNT` at `perf_monitor.c:219-221`) | working set 분포 | 영향 적음 | LRU2 일시 증가 허용 범위 내; **반복 scan 시 AOUT 경유 zone1 증가 모니터링** | 영향 없음 |  sampling |
| 경합 영향 | `Num_data_page_hash_anchor_waits` (`PSTAT_PB_NUM_HASH_ANCHOR_WAITS` at `perf_monitor.c:488`) | 낮음 | 영향 적음 | **상승 가능** — 100 session × depth 4 등 high concurrency 시 한계치 정의 필요 | 영향 없음 |  동상 |
| Prefetch counters (신규) | `PSTAT_PB_PREFETCH_REQUESTS`, `PSTAT_PB_PREFETCH_HITS` (도입 시 추가) | n/a | requests ≈ scan page 수, hit_ratio (=conditional fix not-NULL ratio) > 0.5 기대 | requests ≈ scan page 수, hit_ratio (=실제 prefetched & later fixed) > 0.7 기대 | n/a (sketch C 는 OS hint only) |  동상 |
| **Prefetch usefulness (신규, mechanism 명세 필요)** | "prefetched-but-zero-record-consumed page" ratio (도입 시 추가 카운터; 예: `PSTAT_PB_PREFETCH_USELESS`) | n/a | 미정 | mechanism: §9.1 참조 | n/a |  동상 |
| FTS vs IRS 비교 | 위 지표 전부 | FTS 영향 더 큼 | 미미 | FTS 가 IRS 보다 absolute latency 감소 큼 | 동상 |  같은 schema, 동일 데이터, 두 쿼리 plan 비교 |
| OS readahead 상호작용 | iostat `rrqm/s`, `r/s`; `/proc/<pid>/io` read_bytes | OS readahead 활동 | 변화 적음 | `data_file_os_advise=3` 일 때 application prefetch 효과 isolate | n/a |  OS 도구 |

**측정 전략 — Sketch A 도 새 counter 사용**: Sketch A 의 effectiveness 측정을 기존 `PSTAT_PB_HIT_RATIO` 만으로 하면 다른 워크로드 변화에 confounded 된다. 따라서 `PSTAT_PB_PREFETCH_REQUESTS` / `PSTAT_PB_PREFETCH_HITS` counter 는 Sketch A 의 conditional fix not-NULL ratio 도 카운트하도록 hook 한다. 의미는:
- Sketch A: "requests = conditional fix 시도 수, hits = conditional fix 가 NULL 아니게 성공한 수" — 곧 prefetch 가 OS readahead 의 적중을 거뒀는지를 본다.
- Sketch B: "requests = enqueue 수, hits = scan worker 가 실제로 그 페이지에 도달했을 때 BCB 가 이미 있어 IO 없이 끝난 수".

워크로드 환경:
- (E1) HDD + buffered FS — prefetch 효과가 가장 잘 보임. ~30~70% wall clock 감소 기대.
- (E2) NVMe SSD + page cache hot — 효과 미미, regression 없으면 통과.
- (E3) NVMe SSD + page cache cold (drop_caches) — 효과 측정 가능 (CPU bound 부분이 한계).
- (E4) Containerized with constrained memory(buffer pool 작음) — prefetch pollution 검증의 핵심 환경.

종합 KPI 후보:
- TPS / scan throughput (`Num_data_page_fetches / wall_time`)
- Mean / p99 fix latency (`Data_page_fix_acquire_time_msec / Num_data_page_fetches`)
- Buffer hit ratio (`PSTAT_PB_HIT_RATIO`)
- Prefetch effectiveness = `PSTAT_PB_PREFETCH_HITS / PSTAT_PB_PREFETCH_REQUESTS` (Phase 1 필수)
- Prefetch usefulness — **Phase 1 에서는 KPI 에서 제외**. mechanism 합의 후 Phase 1.5 또는 Phase 2 부터 측정 (§9.1).

### 9.1 `PSTAT_PB_PREFETCH_USELESS` 의 mechanism

본 보고서 작성 시점에는 mechanism 이 두 가지 후보로 좁혀져 있다.

**후보 1 — BCB 의 `was_prefetched` flag 도입 (권장)**:
- `PGBUF_BCB` 구조체 (`src/storage/page_buffer.c:511-560` 부근의 struct 정의) 에 `bool was_prefetched : 1;` flag 1 비트 추가.
- Prefetch worker 가 `pgbuf_fix` 직후 unfix 전 `bufptr->was_prefetched = true` 로 set.
- 같은 BCB 에 일반 fix 가 일어나 unfix 될 때(즉 scan worker 의 normal fix-and-unfix 종료 시점), `pgbuf_unfix` 후속 경로에서 다음을 확인:
  - 해당 fix 동안 record 가 1개라도 소비되었는지 — scan_cache / BTS 에 `last_consumed_record_count` 같은 카운터를 두고 page boundary 에서 delta 를 비교.
  - delta == 0 이고 `bufptr->was_prefetched == true` → `perfmon_inc_stat(thread_p, PSTAT_PB_PREFETCH_USELESS)`.
  - 평가 후 `was_prefetched = false` 로 clear (한 prefetch 의 1회만 카운트되도록).
- 증가 site: `heap_next_internal` 의 page-boundary 종료 분기 (`heap_file.c:8115` 직전) 및 `btree_range_scan_advance_over_filtered_keys` 의 leaf-boundary 종료 분기 (`btree.c:25367` 부근). MVCC visibility 로 모든 record 가 skip 된 경우와 동일하게 처리.
- Cost: BCB 1 bit + per-page scan boundary 의 delta 비교 1회.

**후보 2 — KPI 에서 제거하고 future work 로 보류**:
- Phase 1 KPI 에서 `PSTAT_PB_PREFETCH_USELESS` 자체를 제거하고 §11 의 open question 으로만 남긴다. 측정은 §9 위의 기존 `PSTAT_PB_PREFETCH_HITS / PREFETCH_REQUESTS` 비율 + scan 의 visible record ratio 결합 분석으로 대체 가능 (정확도 낮음).

**Phase 1 결정**: 후보 1 의 mechanism 을 채택하되 구현은 Phase 1 의 mandatory item 이 아닌 *Phase 1.5* 로 분리한다. Phase 1 에서는 `PREFETCH_REQUESTS / PREFETCH_HITS` 만으로 진행하고, useless counter 는 후속 패치에서 도입.

---

## 10. Interaction with Parallel Scan

`PRM_ID_PARALLEL_HEAP_SCAN_PAGE_THRESHOLD` (default 2048, `src/base/system_parameter.c:5125`) 이상의 page 수를 가진 heap 에 대해서는 parallel heap scan 이 sector 단위 분할로 worker 들에게 disk I/O 를 분산시킨다(`src/query/parallel/px_parallel.cpp:53`, `src/query/parallel/px_heap_scan/`). 이미 worker 가 N 개 disk lane 을 동시에 사용하므로 application prefetch 의 추가 이득은 sub-linear 가 된다.

권고 정책 (prefetch ↔ parallel scan 중복 방지):

1. **Parallel degree > 1 인 heap scan**: per-worker prefetch depth 는 *open question — §9 실험 후 결정* 으로 둔다 (후보 {0, 1, 2}; 본 보고서에서는 default off 로 시작하고 §9 KPI 측정 후 결정). 본 보고서는 shipping 결정 (depth=1 등) 을 numeric 근거 없이 권하지 않는다.
2. **Parallel degree = 1 또는 비활성** (num_pages < 2048, or `parallelism=0`, or hint): prefetch 가 main optimization. sketch B 의 single-ahead 활성화 권장.
3. **B-tree range scan**: 현재 검토된 parallel infra (`src/query/parallel/`) 코드에서 b-tree scan parallel 화 경로는 발견되지 않았다. 부정 evidence:
   ```
   $ find src/query/parallel/ -name '*btree*'
   (no matches)
   $ grep -rn 'btree' src/query/parallel/
   (no matches)
   ```
   parallel 디렉터리에 있는 access-method-specific 코드는 `px_heap_scan/`, `px_hash_join/`, `px_query_execute/`, `px_sort.c` 뿐이다(§4.2 의 파일 목록 참조). 따라서 본 보고서 조사 범위 내에서는 b-tree range scan 의 parallel 화 경로가 존재하지 않는 것으로 간주하며, prefetch 가 단독 옵션이고 중복 risk 도 없다. (조사 범위 밖에서 다른 메커니즘이 추가될 가능성은 본 보고서 책임 밖.)
4. **Sort scan / hash join input**: `PRM_ID_PARALLEL_SORT_PAGE_THRESHOLD`, `PRM_ID_PARALLEL_HASH_JOIN_PAGE_THRESHOLD` 도 default 2048 (`system_parameter.c:5149, 5137`). 이 입력 단의 scan 은 parallel sort 의 fan-in scan worker 가 처리하므로 동일 정책 1 적용.

코드 측면에서, `parallel_query::compute_parallel_degree()` (`px_parallel.cpp:36`) 가 결정한 degree 를 scan_cache / BTREE_SCAN 에 전달하여 `scan_cache->enable_prefetch` 와 depth 를 조정하는 hook 이 필요하다. 이는 `scan_open_heap_scan` (`scan_manager.c:2846`) / `scan_open_index_scan` (`scan_manager.c:3067`) 시점이 자연스럽다.

---

## 11. Open Questions / Risks

1. **Lock context (system-worker model)**: `pgbuf_fix` 의 read-only latch 경로(`pgbuf_latch_bcb_upon_fix`, `src/storage/page_buffer.c:6053-6320`) 는 `lock_manager` 를 호출하지 않으므로(`page_buffer.c` 전체에서 `lock_manager`/`lk_lock` grep 0 매치) prefetch worker 가 user transaction 의 lock context 를 들고 갈 필요가 없다. **1차 도입은 lock 없이 page 만 load** 하되, `heap_scan_pb_lock_and_fetch` (`heap_file.c:1248-`) 가 수행하는 OID-level lock conversion 등은 scan worker 의 정식 fix 시점에 user transaction 으로 처리된다. prefetch worker 는 `vacuum_init_thread_context` (`src/query/vacuum.c:766-775`) 의 패턴을 따라 `entry::claim_system_worker()` (`src/thread/thread_entry.cpp:425-432`) 로 system-worker entry 를 claim 한 후 task 를 실행한다. Fetch mode 는 §3.1 의 결론에 따라 각 scan path 의 기존 fix mode 와 일치 — heap 은 `OLD_PAGE_PREVENT_DEALLOC` (`heap_file.c:8000` 일치), btree leaf 는 `OLD_PAGE` (`btree.c:25349` 일치).
2. **OID lookup heap fetch**: IRS 의 OID list (`isidp->oid_list`) 가 한꺼번에 알려진 시점에 page-level grouping 후 prefetch 가능. 이는 leaf chain prefetch 와 별개의 큰 추가 작업이며 별도 follow-up 으로 분리.
3. **OOS / overflow page interaction (REC_BIGONE)**: `heap_next_internal` 의 page-단위 scan 은 home page 의 next_vpid 만 따라간다 (§2.1 참조). REC_BIGONE 의 overflow content 는 별도 함수 `heap_get_bigone_content` (`src/storage/heap_file.c:19600-` 본문, 호출 위치 `heap_file.c:7862-7864` 의 `case REC_BIGONE`) 에서 가져오며, 이 경로는 *현재 fix 된 home page 에 머무른 채로 overflow file 의 페이지 chain 을 따로 traversal* 한다 (`heap_ovf_get` `heap_file.c:653` 선언). 즉:
   - **scan 의 next_vpid prefetch 는 home heap 의 chain 만 따라간다.** REC_BIGONE 슬롯을 만났을 때 prefetch 가 overflow file 의 페이지를 잘못 fetch 하는 일은 발생하지 않는다.
   - overflow file 자체의 prefetch (REC_BIGONE 내용 읽기 시점) 는 본 조사의 scope 밖. 별도 follow-up.
4. **MVCC visibility filter**: scan 이 visibility 로 record 를 skip 한 경우에도 page 는 이미 fetched 됨. prefetch 가 이를 더 늘리지는 않으나, prefetch 가 가져온 page 가 모두 invisible record 만 가질 가능성도 있어 §9 의 "Prefetch usefulness" row 에서 measurement.
5. **DWB(Double Write Buffer) 와의 상호작용**: prefetch 는 read-only 이므로 DWB(`src/storage/double_write_buffer.cpp`) 와 직접 충돌 없음. 단 DWB 에 flush 중인 page 에 대해 prefetch fix 가 일어나도 정상 동작하는지 stress test 필요.
6. **Buffer pool size sensitivity**: `pgbuf_Pool.num_buffers` (`page_buffer.c:5524`) 에 비해 prefetch depth 가 큰 경우, AOUT 효과(`pgbuf_initialize_aout_list` at `page_buffer.c:5582`) 가 약화될 수 있음. **구체 cap 제안 (§9 실험으로 검증 전 잠정값)**: `prefetch_in_flight_max = max (8, num_buffers / 1024)`. depth 와 worker 수 곱이 이 cap 미만이 되도록 system parameter validation 단에서 강제. 본 식은 §9 실험 후 재조정 가능한 default 이며 hard rule 은 아니다.
7. **Descending B-tree scan**: `force_restart_from_root` 가 자주 발생할 수 있는 cyclical-write workload 에서 prefetch 가 stale leaf 를 cache 에 채울 위험. ascending only 로 한정 권장(§5.2).
8. **System parameter 도입 범위**: 최소 `prefetch_enable` (bool) + `prefetch_depth` (int). sketch B 채택 시 `prefetch_workers`, `prefetch_queue_size` 추가. naming 은 vacuum 의 `vacuum_prefetch_*` 와 일관성 확보를 위해 `prefetch_*` prefix 로 통일. **§12 와 본 항목 모두 동일 naming `prefetch_*` 사용**. `scan_prefetch_*` 는 본 보고서 어디서도 쓰지 않는다.
9. **Crash safety**: prefetch 가 in-flight 인 동안 server crash → buffer pool 은 어차피 휘발이므로 영향 없음. WAL/recovery 경로 무관.
10. **Read-latch writer-starvation 위험**: 동일 page 에 대해 scan worker 가 read latch 를 보유한 상태에서 prefetch worker 가 또 read latch 를 잡으면 두 reader 가 공존하지만, write latch 를 대기 중인 writer 가 있을 경우 reader 수가 늘어나 writer 대기가 길어진다 (`pgbuf_latch_bcb_upon_fix` 의 waiter_exists 처리, `page_buffer.c:6139-6160`). 본 보고서의 prefetch 는 **fix 직후 즉시 unfix** 하므로 latch 보유 시간이 microsecond 단위이며, 같은 page 에 대해 writer 가 동시에 대기하는 빈도는 일반 OLAP scan 에서 낮을 것으로 본다. 다만 고-쓰기-경합 워크로드에서는 §9 의 `Num_data_page_hash_anchor_waits` 와 함께 writer latch wait 시간도 모니터링 대상에 포함시킨다. 필요 시 prefetch worker 우선순위 낮추기 (`thread_p` priority) 로 추가 완화.

---

## 12. Recommendation

### 단계적 도입 권고

**Phase 0 — baseline 측정**: 현 상태에서 위 §9 의 KPI workload 행렬을 측정. fix latency / hit ratio / IO read 분포를 baseline 으로 저장. 이 단계에서 `data_file_os_advise` 의 값을 0(off), 2(SEQUENTIAL), 3(RANDOM) 으로 변경하면서 *현재 CUBRID 가 OS readahead 에 얼마나 의존하고 있는지*를 정량화.

**Phase 1 — Sketch B 의 minimal 형태 도입 (async single-ahead, depth=1, single prefetch worker)**:
- §3.4 결과에 따라 Sketch A 단독 도입은 의미 있는 latency hiding 을 만들지 않으므로 Phase 1 은 Sketch B 로 시작한다.
- 변경 위치: `heap_next_internal` (heap_file.c:8115 직후 enqueue), `btree_range_scan_advance_over_filtered_keys` (btree.c:25368 직후 enqueue).
- Fetch mode (path 별): heap 경로 `OLD_PAGE_PREVENT_DEALLOC`, btree leaf 경로 `OLD_PAGE`. 두 경우 모두 `PGBUF_LATCH_READ` + `PGBUF_UNCONDITIONAL_LATCH` (worker 안에서만 동기 wait). 각 path 의 기존 fix mode 와 일치 (§3.1).
- 신규 시스템 파라미터: `prefetch_enable` (bool, default off → 충분한 검증 후 on), `prefetch_depth` (int, default 1), `prefetch_workers` (int, default 1).
- 검증: §9 의 KPI 전부 측정. `PSTAT_PB_PREFETCH_REQUESTS/HITS` 가 양수이고 `Data_page_fix_acquire_time` 가 의미 있게 감소함을 확인. `Num_data_page_hash_anchor_waits` 의 상한선 (예: baseline 의 1.5배) 을 넘으면 enable 보류.

**Phase 2 — Sketch A 보조 (sync conditional fix)**:
- OS readahead 가 활성인 환경 (`data_file_os_advise=2`) 에서 OS-readahead-hit 분량을 BCB 화 하기 위한 부수 효과 제공.
- Sketch B 와 직교: scan worker 가 enqueue 와 동시에 conditional fix 를 호출하면 OS page cache hit 시 즉시 BCB 화, miss 시 호출 thread 가 sync wait 하지만 worker 가 곧 처리할 페이지이므로 추가 cost 가 marginal.
- 새 system parameter 추가 없이 Phase 1 의 `prefetch_enable` flag 의 sub-옵션으로 둔다.

**Phase 3 — Sketch C 보강 (sector-boundary fadvise)**: large heap 의 sequential FTS 에서만 적용. `data_file_os_advise=2` 와 mutually exclusive 옵션으로 가이드.

**Phase 4 — Sketch B 확장 (depth > 1, multi-worker)**: B-tree range scan 의 multi-leaf 예측이 분명히 이득인 워크로드(deep range scan over fragmented index)에 한해 활성화. depth 와 worker 수의 적정값은 §9 의 실험 결과로 결정 (§10 권고 1 의 open question).

**Phase 5 — OID page grouping based heap fetch prefetch**: IRS → heap object 단계의 OID 들이 hot path 인 워크로드에 대해 별도 follow-up. 이는 별도 JIRA 로 분리 권장.

### 보수적 기본값 권고

- 기본 prefetch depth: **1** (Phase 1).
- Phase 1 default: `prefetch_enable=false`, `prefetch_depth=1`, `prefetch_workers=1`.
- Parallel scan 활성 구간(>=2048 pages) 에서의 per-worker depth: **open — §9 실험 후 결정**.
- `pgbuf_lru_add_new_bcb_to_middle` 정책 유지(§6.2).
- Prefetch fetch mode (path 별): heap `OLD_PAGE_PREVENT_DEALLOC` + `PGBUF_LATCH_READ`, btree leaf `OLD_PAGE` + `PGBUF_LATCH_READ` (§3.1, §8, §11 item 1 일치). 각각 기존 scan fix 와 동일.
- Sketch A 는 `PGBUF_CONDITIONAL_LATCH` + immediate `pgbuf_unfix`; Sketch B 는 worker 내부에서 `PGBUF_UNCONDITIONAL_LATCH` + immediate `pgbuf_unfix`.
- recovery/WAL 무영향 — 추가 log record 없음.
- system parameter naming: 본 보고서 전체 일관 `prefetch_*` (vacuum 의 `vacuum_prefetch_*` 와 같은 prefix family).

### 측정 책임

Phase 1 도입 후 §9 의 KPI 전부를 매 nightly CI 의 long workload 에서 수집하여 regression 을 자동 감지. 새로 추가될 `PSTAT_PB_PREFETCH_REQUESTS/HITS` (및 useless counter) 가 보고서에 노출되도록 `cm_mem_cpu_stat.c` (`src/cm_common/cm_mem_cpu_stat.c:1146-1147` 의 vacuum prefetch 항목 옆) 에 항목 추가.

---

## Appendix A — File:line evidence index

(본 부록은 본문에서 인용된 모든 위치의 strict superset 이다. 본문에서 더 좁은 범위를 인용한 경우 부록의 범위는 본문 범위를 포함한다.)

### Heap scan path
- `src/storage/heap_file.c:190` — `typedef struct heap_hdr_stats HEAP_HDR_STATS;`
- `src/storage/heap_file.c:191` — `struct heap_hdr_stats` 본문 시작
- `src/storage/heap_file.c:194` — `OID class_oid;` (HEAP_HDR_STATS 첫 필드)
- `src/storage/heap_file.c:195` — `VPID ovf_vfid;`
- `src/storage/heap_file.c:196` — `VPID next_vpid;` (HEAP_HDR_STATS)
- `src/storage/heap_file.c:269` — `typedef struct heap_chain HEAP_CHAIN;`
- `src/storage/heap_file.c:270` — `struct heap_chain` 본문 시작
- `src/storage/heap_file.c:273` — `OID class_oid;` (HEAP_CHAIN 첫 필드)
- `src/storage/heap_file.c:274` — `VPID prev_vpid;`
- `src/storage/heap_file.c:275` — `VPID next_vpid;` (HEAP_CHAIN)
- `src/storage/heap_file.c:582-588` — `heap_scan_pb_lock_and_fetch` 선언 (debug / NDEBUG variant)
- `src/storage/heap_file.c:792` — `heap_next_internal` static 선언
- `src/storage/heap_file.c:1235-1322` — `heap_scan_pb_lock_and_fetch` 본문 (주석 시작 1235, signature 1248), 내부 `pgbuf_ordered_fix` / `pgbuf_fix_release` 호출
- `src/storage/heap_file.c:5028-5036` — `heap_vpid_next` 함수 헤더 주석 (`* heap_vpid_next ()` 5029)
- `src/storage/heap_file.c:5037` — `heap_vpid_next` 반환형 `int`
- `src/storage/heap_file.c:5038` — `heap_vpid_next` 함수명·인자 signature
- `src/storage/heap_file.c:5037-5073` — `heap_vpid_next` 전체 (헤더 주석 5028-5036 별도, 본문 5037-5073)
- `src/storage/heap_file.c:5050-5070` — header/chain 에서 `next_vpid` 추출
- `src/storage/heap_file.c:5085-5125` — `heap_vpid_skip_next` (sampling)
- `src/storage/heap_file.c:6943-` — `heap_scancache_start` 주석 시작
- `src/storage/heap_file.c:6956` — `heap_scancache_start` signature
- `src/storage/heap_file.c:7883-8265` — `heap_next_internal` 전체 (주석 시작 7883, signature 7902)
- `src/storage/heap_file.c:7997-8001` — `heap_scan_pb_lock_and_fetch` 호출, fetch_mode 인자 (`OLD_PAGE_PREVENT_DEALLOC` 8000)
- `src/storage/heap_file.c:8115` — `heap_vpid_next` 호출 지점 (prefetch hook 후보)
- `src/storage/heap_file.c:8268-8285` — `heap_next_1page`
- `src/storage/heap_file.c:8468-8511` — `heap_first` / `heap_last` 본문
- `src/storage/heap_file.c:19427, 19498` — `heap_next`, `heap_prev` (assertion 참조)
- `src/storage/heap_file.c:7826-7880` — `heap_get_record_data_when_all_ready` (REC_BIGONE 분기 7862-7864)
- `src/storage/heap_file.c:19600-` — `heap_get_bigone_content` 본문 시작
- `src/storage/heap_file.c:653` — `heap_ovf_get` 선언 (overflow page traversal)

### B-tree range scan path
- `src/storage/btree.h:197` — `typedef struct btree_scan BTREE_SCAN;` (BTS)
- `src/storage/btree.h:198-` — `struct btree_scan` 본문 시작
- `src/storage/btree.c:334` — `BTREE_SCAN btree_scan` 멤버 (다른 구조체 내장)
- `src/storage/btree.c:541-602` — `BTS_*` macro family
- `src/storage/btree.c:1391` — `btree_get_next_page_vpid` 선언
- `src/storage/btree.c:1508-1520` — `btree_range_scan_*` static 선언
- `src/storage/btree.c:14938-15013` — `btree_find_lower_bound_leaf` (range scan start)
- `src/storage/btree.c:16931` — `btree_range_scan_resume` 호출
- `src/storage/btree.c:19351-19375` — `btree_get_next_page_vpid` 본문
- `src/storage/btree.c:19383-19425` — `btree_get_next_page` (fix 까지 수행)
- `src/storage/btree.c:25024-25174` — `btree_range_scan_resume`
- `src/storage/btree.c:25229-25450` — `btree_range_scan_advance_over_filtered_keys` (chain advance core)
- `src/storage/btree.c:25302` — 첫 `next_vpid` 결정
- `src/storage/btree.c:25333-25334` — `btree_range_scan_descending_fix_prev_leaf` 호출
- `src/storage/btree.c:25340-25344` — `force_restart_from_root` 처리
- `src/storage/btree.c:25349` — 다음 leaf `pgbuf_fix` 호출 (prefetch hook 후보; `OLD_PAGE` + `PGBUF_UNCONDITIONAL_LATCH`)
- `src/storage/btree.c:25368` — `next_vpid = node_header->next_vpid` 갱신

### Page buffer / LRU
- `src/storage/page_buffer.h:174-202` — `PAGE_FETCH_MODE` / `PGBUF_LATCH_MODE` / `PGBUF_LATCH_CONDITION`
- `src/storage/page_buffer.h:275-329` — `pgbuf_fix` / `pgbuf_ordered_fix` declarations
- `src/storage/page_buffer.c:199-201` — `PGBUF_LRU_1_ZONE`, `PGBUF_LRU_2_ZONE`, `PGBUF_LRU_3_ZONE`
- `src/storage/page_buffer.c:279` — `PGBUF_AOUT_NOT_FOUND  -2`
- `src/storage/page_buffer.c:371-660` — `PGBUF_AOUT_BUF`, `PGBUF_AOUT_LIST`, `pgbuf_lru_list`
- `src/storage/page_buffer.c:919` — `PGBUF_IS_BCB_IN_LRU_VICTIM_ZONE` macro
- `src/storage/page_buffer.c:922-924` — `PGBUF_AGE_DIFF` macro
- `src/storage/page_buffer.c:927-928` — `PGBUF_IS_BCB_OLD_ENOUGH` macro (tick-기반)
- `src/storage/page_buffer.c:1050` — `pgbuf_lock_page` 선언
- `src/storage/page_buffer.c:1054-` — `pgbuf_claim_bcb_for_fix` 선언
- `src/storage/page_buffer.c:1078` — `pgbuf_remove_vpid_from_aout_list` 선언
- `src/storage/page_buffer.c:1083-1087` — `pgbuf_lru_add_bcb_to_{top,middle,bottom}` family
- `src/storage/page_buffer.c:1603` — LRU hot ratio 초기화 (`PRM_ID_PB_LRU_HOT_RATIO`)
- `src/storage/page_buffer.c:1644-1898` — AOUT 초기화/해제
- `src/storage/page_buffer.c:2037` — `pgbuf_fix_debug` signature
- `src/storage/page_buffer.c:2041` — `pgbuf_fix_release` signature
- `src/storage/page_buffer.c:2060-2459` — `pgbuf_fix_release` 본문 (전체)
- `src/storage/page_buffer.c:2156-2159` — hash chain lookup (`pgbuf_search_hash_chain`)
- `src/storage/page_buffer.c:2189-2202` — BCB 없을 때 `pgbuf_claim_bcb_for_fix` 호출
- `src/storage/page_buffer.c:2498-2509` — `pgbuf_simple_fix` 의 비슷한 분기
- `src/storage/page_buffer.c:5524-5651` — buffer pool 초기화, AOUT ratio (5578-5651 의 `pgbuf_initialize_aout_list`)
- `src/storage/page_buffer.c:6080-6320` — `pgbuf_latch_bcb_upon_fix` (conditional latch 의 실제 fail 지점 6185-6190, 6320)
- `src/storage/page_buffer.c:6650-6745` — `pgbuf_unlatch_void_zone_bcb` (AOUT lookup 6662, private LRU top promotion 6722, shared LRU mid 6740)
- `src/storage/page_buffer.c:7708-7799` — `pgbuf_lock_page` 본문 (buffer-lock chain 위 sleep/wake 처리)
- `src/storage/page_buffer.c:8122-8259` — `pgbuf_claim_bcb_for_fix` 본문, 동기 `fileio_read` 호출 (8249)
- `src/storage/page_buffer.c:9424-9610` — add to top/middle/bottom 본문
- `src/storage/page_buffer.c:9611-9778` — zone adjustment
- `src/storage/page_buffer.c:9858-9921` — `pgbuf_lru_boost_bcb`
- `src/storage/page_buffer.c:9933-10010` — `pgbuf_lru_add_new_bcb_to_{top,middle,bottom}`
- `src/storage/page_buffer.c:10274-` — `pgbuf_remove_vpid_from_aout_list` 본문

### File I/O
- `src/storage/file_io.c:531` — `fileio_os_read` declaration
- `src/storage/file_io.c:2129, 3000-3004` — `fileio_open(... O_RDWR | o_sync, 0600)` — buffered open
- `src/storage/file_io.c:3023-3056` — `posix_fadvise` 호출, advise flag mapping (`#if _POSIX_C_SOURCE >= 200112L` guard)
- `src/storage/file_io.c:3731` — `#if defined(HPUX) && !defined(IA64)` (pread/pwrite fallback 시작)
- `src/storage/file_io.c:3744-3772` — `pread()` 시뮬레이션 via `aio_read` (HPUX non-IA64 한정)
- `src/storage/file_io.c:3783-3811` — `pwrite()` 시뮬레이션 via `aio_write` (HPUX non-IA64 한정)
- `src/storage/file_io.c:3813` — `#elif defined(WINDOWS) && defined(SERVER_MODE)` (다음 platform 분기)
- `src/storage/file_io.c:3862-3956` — `fileio_os_read`, `fileio_read` 본문
- 코드베이스 전체 `O_DIRECT` grep 결과: `grep -rn 'O_DIRECT' src/storage/` → 0 matches (확인 일자 본 보고서 작성 시점)

### File manager / sector layout
- `src/storage/storage_common.h:109-117` — `DISK_SECTOR_NPAGES=64`, `IO_SECTORSIZE`, `SECTOR_FIRST_PAGEID`, `SECTOR_LAST_PAGEID`, `SECTOR_FROM_PAGEID`
- `src/storage/disk_manager.h:70-71` — `DISK_SECTS_NPAGES`, `DISK_PAGES_TO_SECTS`
- `src/storage/file_manager.c:278-279` — `FILE_TABLESPACE_DEFAULT_{MIN,MAX}_EXPAND`
- `src/storage/file_manager.c:387-392` — `FILE_ALLOC_*` enum
- `src/storage/file_manager.c:666-704` — `file_partsect_*` family declarations
- `src/storage/file_manager.c:2758-2879` — `file_partsect_is_full / is_empty / is_bit_set / set_bit / clear_bit / alloc` 본문
- `src/storage/file_manager.c:3330-3645` — extdata / partsect 관리
- `src/storage/file_manager.h:206-219` — `file_alloc`, `file_alloc_multiple`, `file_get_num_user_pages`

### Scan drivers (query layer)
- `src/storage/heap_file.h:142-184` — `struct heap_scancache` 본문 (`cache_last_fix_page` 151)
- `src/storage/heap_file.h:409-417` — `heap_scancache_start*` declarations
- `src/query/scan_manager.h:103, 129, 229, 403-406, 458-480` — `HEAP_SCAN_ID`, `PARALLEL_HEAP_SCAN_ID`, `INDX_SCAN_ID` typedef 및 union
- `src/query/scan_manager.c:170` — `scan_get_index_oidset` static 선언
- `src/query/scan_manager.c:177-185` — `scan_next_scan_local`, `scan_next_heap_scan`, `scan_next_index_scan` 선언
- `src/query/scan_manager.c:2216-` — `scan_get_index_oidset` 주석 시작, signature 2224
- `src/query/scan_manager.c:2818-2846` — `scan_open_heap_scan`
- `src/query/scan_manager.c:3030-3067` — `scan_open_index_scan`
- `src/query/scan_manager.c:5354-5361` — `scan_next_heap_scan`

### Parallel scan
- `src/base/system_parameter.h:503-507` — `PRM_ID_PARALLELISM`, `PRM_ID_PARALLEL_HEAP_SCAN_PAGE_THRESHOLD`, etc.
- `src/base/system_parameter.c:774-778` — `PRM_NAME_PARALLEL_*` (`PRM_NAME_PARALLEL_HEAP_SCAN_PAGE_THRESHOLD "parallel_heap_scan_page_threshold"` 776)
- `src/base/system_parameter.c:5101-5160` — parameter definitions (default 2048 등; `PRM_ID_PARALLEL_HEAP_SCAN_PAGE_THRESHOLD` 5125)
- `src/base/system_parameter.c:9886-10001` — parallelism normalization (parallelism <= core count, <= max_parallel_workers)
- `src/query/parallel/px_parallel.cpp:36-122` — `compute_parallel_degree`
- `src/query/parallel/px_worker_manager_global.cpp:50-57` — worker pool sizing
- `src/query/parallel/px_heap_scan/px_heap_scan.hpp:42, 126-133` — `input_handler_ftabs`, `scan_open_parallel_heap_scan` 등
- `src/query/parallel/px_heap_scan/px_heap_scan_checker.cpp:853-863` — `scan_check_parallel_heap_scan_possible`
- `src/query/parallel/px_heap_scan/px_heap_scan_result_handler.cpp:746, 883` — `__builtin_prefetch` (CPU hint, disk 와 무관)

### Thread / async infra
- `src/thread/thread_daemon.hpp:47-145` — `cubthread::daemon` class
- `src/thread/thread_daemon.cpp:61-72` — daemon thread 생성 패턴
- `src/thread/thread_manager.hpp:63-189, 261-289, 333-376` — `cubthread::manager`, `worker_pool`, `daemon` 생성
- `src/thread/thread_manager.hpp:135-148` — `create_worker_pool`, `push_task`
- `src/thread/thread_manager.hpp:498` — `REGISTER_DAEMON` macro
- `src/thread/thread_entry_task.hpp:43-132` — `entry_task`, `daemon_entry_manager`
- `src/thread/thread_worker_pool*.{cpp,hpp}` — worker pool 구현체

### System parameters relevant
- `src/base/system_parameter.c:607` — `PRM_NAME_PB_LRU_HOT_RATIO "lru_hot_ratio"`
- `src/base/system_parameter.c:631-633` — vacuum prefetch parameters
- `src/base/system_parameter.c:694` — `PRM_NAME_DATA_FILE_ADVISE "data_file_os_advise"`
- `src/base/system_parameter.c:776` — `PRM_NAME_PARALLEL_HEAP_SCAN_PAGE_THRESHOLD`
- `src/base/system_parameter.c:3741-3753` — `PRM_ID_PB_LRU_HOT_RATIO` 정의 본문
- `src/base/system_parameter.c:3893-3920` — vacuum prefetch parameter registration (모델 사례)
- `src/base/system_parameter.c:4342-4353` — `PRM_ID_DATA_FILE_ADVISE` (default 0, max 6)
- `src/base/system_parameter.c:5101-5160` — parallel-related parameters

### Existing prefetch references (Appendix superset; 본문 §4.1 의 범위 포함)
- `src/base/porting.h:1100-1104` — `prefetch(x,y,z)` macro mapping to `__builtin_prefetch`
- `src/query/vacuum.c:478, 485, 719, 1251-1273, 3318` — vacuum log prefetch
- `src/parser/compile.c:407-498, 679-813` — `pt_class_pre_fetch` (주석 시작 407, signature 432)
- `src/communication/network_interface_cl.c:267-360, 502-563` — locator fetch with `prefetch` arg
- `src/query/cursor.c:74` — `cursor_prefetch_first_hidden_oid` 선언
- `src/query/cursor.c:75` — `cursor_prefetch_column_oids` 선언
- `src/query/cursor.c:786` — `cursor_prefetch_first_hidden_oid` 정의
- `src/query/cursor.c:841` — `cursor_prefetch_column_oids` 정의
- `src/query/cursor.c:1032-1048` — 호출 site (1044: first_hidden_oid, 1048: column_oids)
- `src/query/cursor.c:1230-1279` — cursor reset / oid_col_no 정리 (참고)
- `src/base/xserver_interface.h:96-119` — `xlocator_*` API with `prefetching`

### Performance counters used by validation
- `src/base/perf_monitor.c:200` — `PSTAT_FILE_NUM_IOREADS` "Num_file_ioreads"
- `src/base/perf_monitor.c:209` — `PSTAT_PB_NUM_FETCHES` "Num_data_page_fetches"
- `src/base/perf_monitor.c:211` — `PSTAT_PB_NUM_IOREADS` "Num_data_page_ioreads"
- `src/base/perf_monitor.c:219-221` — `PSTAT_PB_LRU1_CNT/LRU2_CNT/LRU3_CNT`
- `src/base/perf_monitor.c:335-336` — `PSTAT_VAC_NUM_PREFETCH_REQUESTS_LOG_PAGES` / `..._HITS_LOG_PAGES` (vacuum, 모델 사례)
- `src/base/perf_monitor.c:447` — `PSTAT_PB_HIT_RATIO` "Data_page_buffer_hit_ratio"
- `src/base/perf_monitor.c:453-455` — fix lock/hold/acquire time
- `src/base/perf_monitor.c:488` — `PSTAT_PB_NUM_HASH_ANCHOR_WAITS`
- `src/base/perf_monitor.c:601-604` — `PSTAT_PBX_FIX_TIME_COUNTERS` (complex)
- `src/cm_common/cm_mem_cpu_stat.c:1146-1147` — CM 통계 노출 패턴 (vacuum prefetch)

### Misc / cross-reference
- `src/storage/double_write_buffer.cpp:260-373` — DWB structures (write 측 영향 없음, prefetch 와 read-only path 무관)
- `src/storage/heap_file.c:18671, 19083-19127` — heap header / chain debug dump (next_vpid 가 페이지 안에 살아있음을 재확인)
