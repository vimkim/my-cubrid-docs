# PR #7353 (CBRD-26176) Redesign bestspace — 실증 Call Flow 분석

- **기준 커밋**: develop `f30f1c260` (PR #7353 merge commit `e84a7f6dc` 포함)
- **작성일**: 2026-07-28 / **작성 주체**: claude-fable-5 (vimkim 세션)
- **방법론**: ① 순정(비계측) release_gcc 바이너리에 gdb breakpoint를 걸어 콜스택 채증 → ② `bestspace.cpp`/`heap_file.c`에 printf 계측(BSTRACE)을 삽입해 재빌드 → SA 단일 커넥션, CS 8-커넥션 동시 INSERT, DELETE+VACUUM, 재시작 rebuild, 30초/shutdown sync 시나리오를 실행하고 트레이스를 분석. 계측 패치와 원본 로그는 `evidence/` 디렉터리에 보존.
- **환경**: 신규 생성 DB `bsdb`(16K page), 계측 지점의 코드 라인 번호는 **비계측 원본**(`f30f1c260`) 기준. CS 스택 캡처(gdb attach)만 계측 빌드에서 수행되어 heap_file.c 라인이 +55가량 시프트되어 있음(evidence 파일 참조 시 주의).

---

## 0. 한 장 요약

```
[클라이언트/CS worker]
INSERT 실행 (qexec_execute_insert)
  → locator_attribute_info_force → locator_insert_force
    → heap_insert_logical                          heap_file.c:23076
      → heap_get_insert_location_with_lock        heap_file.c:20459
        → heap_find_bestpage                      heap_file.c:4576 (STATIC_INLINE)
          ├─ heap_find_bestspace                  heap_file.c:4497
          │    ├─ registry TLS 캐시 → 전역 registry 조회 (lock-free 우선)
          │    └─ miss 시: heap header WRITE latch → heap_build_bestspace (디스크에서 lazy 재구축)
          ├─ bestspace->updatable()? (30초 경과 CAS) → heap_update_bestspace (디스크 sync)
          └─ bestspace::find                      bestspace.cpp:1325
               └─ find_from_shards (shard 0부터 순회)  bestspace.cpp:1472
                    └─ shard::find                bestspace.cpp:341
                         ├─ L3_find → L2_find → L1_find (원자적 bitmap/entry 스캔)
                         │    └─ L1_fix: 무대기(zero-wait) ordered WRITE fix
                         │       성공 → 실측 free space 재검증 → L1 CAS로 소비량 선차감 → FOUND
                         │       latch 경합 → CONTENDED (대기하지 않고 다음 후보로)
                         └─ 실패 시 allocate: allocating bit 선점
                              → victim 4개 선정 → candidate queue pop → 검증
                              → 부족분 heap_alloc_new_pages(4장 일괄) → L1 교체 → FOUND
      → (페이지 WRITE latch 보유 상태로) slot 확보 + lock → heap_insert_physical + WAL
```

기존 구조와의 본질적 차이: **heap header page WRITE latch가 best page 탐색 경로에서 사라졌다.**
탐색은 shard별 원자 변수(L1/L2/L3)와 대상 데이터 페이지 latch만 사용하고, header page는
lazy build/30초 sync/shutdown sync/새 페이지 할당 시에만 잡는다.

---

## 1. 진입 경로: INSERT가 bestspace에 도달하기까지

### 1.1 SA 모드 (gdb 실측 스택, evidence/gdb_run1.log)

```
#0 cubstorage::bestspace::find            bestspace.cpp:1336
#1 heap_find_bestpage                     heap_file.c:4604   (inline)
#2 heap_get_insert_location_with_lock     heap_file.c:20477
#3 heap_insert_logical                    heap_file.c:23180
#4 locator_insert_force                   locator_sr.c:5065
#5 locator_attribute_info_force           locator_sr.c:7584
#6 qexec_execute_insert                   query_executor.c:13522
#7 qexec_execute_mainblock(_internal)     query_executor.c:15778
#8 qexec_execute_query                    query_executor.c:17070
#9 qmgr_process_query → xqmgr_execute_query
#10 (SA: network_interface_cl.c 경유 직결) → do_execute_insert → csql
```

### 1.2 CS 모드 서버 측 (gdb attach 실측 스택, evidence/gdb_cs_stack.log)

```
cubthread::worker_pool worker 스레드
  → css_server_task::execute             server_support.c:2094
  → css_internal_request_handler         server_support.c:486
  → net_server_request                   network_sr.c:905
  → sqmgr_execute_query                  network_interface_sr.cpp:5788
  → xqmgr_execute_query → qexec_execute_insert → locator_* → heap_insert_logical → … → bestspace::find
```

**커넥션-스레드 매핑 실측**: 8개 csql 커넥션 × 500 INSERT 실행 시 서버 트레이스에는
정확히 8개의 worker tid가 나타나고 각 tid가 자기 커넥션의 요청만 처리했다
(tid별 이벤트 수 12,499~12,751로 균등). 즉 이 워크로드에서 "커넥션 = worker 스레드 = 트랜잭션"이
1:1:1로 대응하며, bestspace 동시성 = worker 스레드 동시성이다.

### 1.3 CREATE TABLE 시 bestspace 페이지 생성 (gdb 실측)

```
do_create_entity → locator_create_heap_if_needed → heap_create (client)
  → xheap_create → heap_create_internal   heap_file.c:4810
    → heap_create_bestspace               heap_file.c:3789
```

`heap_create_bestspace`가 하는 일 (heap_file.c:3789-3967):
1. header의 `bestspace.num_shards`에 `PRM_ID_BESTSPACE_SHARD_COUNT`(기본 8, 범위 1~28) 기록
2. 필요한 shard(metadata) 페이지 수 계산: `max_shards(28) × 64 entry × 8B`를 페이지 용량으로 나눔
   → 16K 페이지에서 **1장** (`MAX_SHARD_PAGE_COUNT`는 4)
3. `file_alloc_multiple`로 shard 페이지 할당, chain 연결(`header ↔ bestspace pages ↔ …`),
   HEAP_CHAIN flags에 `HEAP_PAGE_FLAG_BESTSPACE` 설정 → user 페이지와 구별
4. 각 shard 페이지 slot 2(`HEAP_BESTSPACE_ENTRIES_SLOTID`)에 entry 배열 초기 기록
   (첫 entry = header page 자신의 free space)
5. `heap_hdr->next_vpid`가 bestspace 페이지를 가리키도록 chain 재배선

트레이스 실측: `heap/create_bestspace hfid=1|768|769 shards=8 bs_pages=1 p0=1|770`
— bt_multi의 heap은 header 1|769 + bestspace 페이지 1|770으로 시작.

---

## 2. heap_find_bestspace: registry 조회와 lazy 재구축

코드: heap_file.c:4497-4569, bestspace.cpp:1616-1720(registry)

```
bestspaces.find(hfid)                      ← ① thread-local 캐시 (TLS_cache, 최대 40개, LRU)
                                              generation 불일치 시 TLS 전체 무효화
                                           ← ② 전역 연결 리스트 (mutex 보호, 찾으면 TLS에 등록)
miss & class_oid 있음:
  heap header page WRITE latch 획득 (pgbuf_ordered_fix)
  → 재확인 find (다른 스레드가 먼저 만들었을 수 있음)     heap_file.c:4550
  → heap_build_bestspace                                  heap_file.c:4387
       header의 HEAP_HDR_STATS 해석 (record length == sizeof(HEAP_HDR_STATS) assert)
       → heap_load_bestspace: shard 페이지들을 ordered fix로 순회하며 entry 배열 로드
       → header의 candidates(최대 128) 로드
       → bestspaces.create(hfid, shards, entries, candidates, est_pages/recs/sumlen, unfill)
       (root class heap이면 shard 1개 강제)               heap_file.c:4450
miss & class_oid == NULL (vacuum/recovery 경로):
  즉시 NULL 반환 — 재구축하지 않음                        heap_file.c:4507-4510
```

**실측 (SA 첫 INSERT, evidence/trace-sA-sa-single.log)**:
```
reg/miss hfid=1|704|705 ×2       ← find → miss, latch 획득 후 재확인 → miss
heap/build hfid=1|704|705 hdr(shards=8 bs_pages=1 cands=0 est_pages=1 est_recs=0)
reg/create … entries=512 cands=0 unfill=1634
reg/global-hit->tls …            ← 생성 직후 재조회로 TLS 캐시 채움
```
- 키는 **HFID 단독** (class_oid는 키가 아님 — 페이지 검증 용도로만 사용)
- registry는 프로세스 전역 `cubstorage::bestspaces` (bestspace.cpp:1846 부근 정의)
- 카탈로그 heap들도 첫 INSERT 시점에 각각 lazy build됨 (create table 문 실행 중에 관찰됨)

---

## 3. bestspace::find 내부: 탐색 파라미터 계산

코드: bestspace.cpp:1325-1365

```
consume_size = record size + SPAGE_SLOT_SIZE(4)
needed_size  = consume_size + m_unfill_space          ← unfill 예약분까지 요구
               (needed > heap_nonheader_page_capacity() 이면 needed = consume)
shard = 0, bias = 0                                    ← ★ 항상 고정 (아래 §6.2)
```

실측 예: 628B 레코드 → consume 632, needed 632+1634=2266 (unfill_factor 0.1 × 16K ≈ 1634).

**tier 매핑** (bestspace.cpp:1367-1395): 페이지 대비 free space 비율로 9단계.
경계 {7,15,24,34,45,57,70,84}% → FS0(1-7%)…FS8(85-100%). FS0은 L2/L3 bitmap에
인덱싱되지 않으며, 요구 tier가 FS0이면 FS1로 승격해서 탐색한다(shard::find, bestspace.cpp:350-355).

## 4. shard 내부 탐색: L3 → L2 → L1

구조 (bestspace.hpp:237-328): shard당
- `m_L1[64]`: (freespace u16, vpid) 8B entry, 각각 64B-정렬 `std::atomic` — lock-free 보장 static_assert
- `m_L2[8]`: 8개 L1 묶음의 tier bitmap (tier별 8bit × 8 tier = 8B)
- `m_L3`: 8개 L2 묶음의 tier bitmap
- `m_allocating`: shard당 1개의 allocating bit
- shard 크기 4800B/64B 정렬 (false sharing 방지)

### 4.1 정상 경로 (L1 hit)

```
L3_find (bestspace.cpp:417): tier=minimum부터 FS8까지 L3 bitmap 스캔
  → 후보 L2들을 (i + bias) % length 순으로 L2_find
L2_find (491): 동일 방식으로 후보 L1 선택 → L1_find
L1_find (567):
  1) L1 원자 load → 기록된 freespace < needed면 즉시 NOT_FOUND (fix 없이 탈락)
  2) L1_fix (652): xlogtb_reset_wait_msecs(LK_FORCE_ZERO_WAIT) 후
     pgbuf_ordered_fix(OLD_PAGE_MAYBE_DEALLOCATED, WRITE latch)
     - ER_LK_PAGE_TIMEOUT → CONTENDED (한순간도 기다리지 않고 포기)
     - ER_PB_BAD_PAGEID  → 페이지가 회수됨: L1_remove(CAS로 null화) 후 NOT_FOUND
  3) 페이지 타입/소속 class 검증 (PAGE_HEAP? class_oid 일치?)
     불일치 → L1_remove + unfix + NOT_FOUND  (다른 테이블로 재할당된 stale entry 제거)
  4) 실측 spage_max_space_for_new_record < needed
     → L1 freespace를 실측값으로 CAS 축소(L2/L3 전파) + unfix + NOT_FOUND
  5) 충분 → L1 = (실측 - consume)으로 CAS 선차감 → L2_update → L3_update → FOUND
     (페이지는 WRITE latch가 잡힌 채 page_watcher로 caller에 반환된다)
```

L2_update/L3_update (529/455)는 "L1 실제값 ↔ bitmap" 정합을 CAS 루프로 재수렴시키는
best-effort 전파다. bitmap은 힌트일 뿐이며 최종 판단은 항상 L1 fix + 실측으로 한다.

**실측 (2번째 INSERT, 정상 hit)**:
```
find/enter hfid=1|704|705 size=24 consume=28 needed=1662
shard/find sh=0x…9a00 needed=1662 tier_min=0(FS1)
L1/probe l2=0 l1=0 rec_fs=15124 vpid=1|705
L1/FOUND vpid=1|705 actual=15124 newL1=15096        ← CAS 선차감
find/FOUND shard=0 tried=1 vpid=1|705
heap/insert-location page=1|705 (WRITE latch 보유)
```

### 4.2 estimates 갱신 — INSERT마다 원자 증가

find_from_shards가 FOUND를 받으면 그 shard에
`add_estimates(0, is_newrec?1:0, consume-4)` (bestspace.cpp:1497) — `num_recs`, `recs_sumlen`이
shard별 `std::atomic` fetch_add로 흩어져 갱신된다. `num_pages`는 allocate_new_pages에서만 +.
읽기(`get_estimates`)는 전 shard 합산. **감소 경로는 런타임에 없다** (§7.4).
relocation(REC_NEWHOME) 레코드는 `is_newrec=false`로 들어와 레코드 수에 계상되지 않는다
(커밋 "do not count relocation record as a new record").

## 5. allocate: 후보 교체와 새 페이지 할당

트리거: L3_find가 NOT_FOUND(공간 없음) 또는 CONTENDED(모든 후보가 latch 경합)로 끝났을 때.
코드: bestspace.cpp:1021-1067 및 하위 함수들.

```
allocate_mark (698): m_allocating CAS 선점 실패 → 즉시 ALLOCATING 반환
                     → find_from_shards가 다음 shard로 전진
allocate_pick_victims (724): 64개 L1 중 freespace 최소 4개(ALLOC_BATCH_SIZE)를 victim으로
allocate_pick_candidates (758): candidate queue에서 pop
    pop 조건: freespace > victim 최소값 && (최상위가 needed 이상이면 4개, 아니면 3개까지)
    이미 이 shard L1에 상주하는 후보는 resident로 분리
allocate_get_candidates_or_update_residents (804):
    resident 후보는 L1_find(force_check=true)로 강제 재실측 → FOUND면 그 페이지 즉시 사용
allocate_verify_or_allocate (917):
    fresh 후보 4개가 다 모였으면 최대 후보를 실제 fix해 검증(verify_actual_space, 854)
    - 페이지 회수됨/타 클래스 → 폐기, 부족 → 검증 실패한 유효 후보는 queue로 반납
    후보가 4개 미만이면 heap_alloc_new_pages로 부족분만큼 신규 할당
allocate_new_pages (965): heap_alloc_new_pages(heap_file.c:25920)
    - header WRITE latch → file_alloc_multiple로 4-n장 일괄 할당
      (batch 할당으로 header latch 왕복을 1/4로 절약)
    - 마지막 페이지는 fix된 채 반환 → 이 페이지가 INSERT 대상
allocate_replace_pages (995): victim L1 슬롯에 새 후보들을 store (마지막 victim은
    후보 fs > victim fs일 때만 교체) → L2/L3 전파
반환 직전 candidates[3].freespace -= consume  (반환 페이지 선차감)
allocate_unmark → FOUND
```

**대기 경로**: 모든 shard가 ALLOCATING이면 find_from_shards는
`pgbuf_ordered_callback(wait_for_shard_allocation)` (bestspace.cpp:1510, page_buffer.c:13002)
— **보유한 ordered page를 전부 unfix한 뒤** yield/10µs sleep 하고 처음부터 재시도.
latch를 쥔 채 spin하지 않으므로 deadlock이 없다. (pgbuf 신규 helper가 이 PR에서 추가된 이유)

## 6. 다중 커넥션 동시 INSERT — 실측 인터리빙

시나리오: CS 모드, 8 커넥션 × 500행(126B payload) 동시 INSERT. 4000행 / 0.41초 완료.
전체 트레이스 101,157줄 (evidence/trace-sB-cs-server-full.log.gz).

### 6.1 콜드스타트 버스트 (evidence/trace-sB-cs-coldstart-excerpt.log, 주석 추가)

빈 테이블( L1엔 header page 하나)에 6개 스레드가 동시 진입한 90µs 구간:

```
t=…5077  tid 313292  shard0 진입, L1[0][0]=header(15152) probe
t=…5097  tid 313292  L1/fix-CONTENDED  ← 313298이 latch 선점
t=…5103  tid 313292  alloc/begin shard0        ← CONTENDED → allocate로 전환
t=…5114  tid 313298  L1/FOUND header 15152→15020  ← latch 승자는 그냥 삽입
t=…5121  tid 313292  pop-candidates=0 → heap_alloc_new_pages 4장 (1|771~774)
t=…5141  tid 313294  alloc/busy shard0 → ALLOCATING  ← allocating bit에 막힘
t=…5143  tid 313294  shard1로 전진 → NOT_FOUND → alloc/begin shard1 → 4장 (1|775~778)
t=…5206  tid 313300  shard0 busy → shard1 busy → shard2에서 alloc/begin → 4장 (1|779~782)
t=…5232  tid 313292  alloc/replace L1[1..3] ← 772/773/774, 자신은 1|771 사용
t=…5261  tid 313302  313292가 게시한 L1[0][1]=1|774(16264) 발견 → FOUND  ← 편승
t=…5301  tid 313295  같은 페이지 1|774 16132→16000 FOUND               ← 편승
```

관찰 포인트:
- latch 경합 시 **누구도 기다리지 않는다**: 승자 1명 삽입, 패자는 allocate 또는 다음 shard.
- allocating bit이 "동시 다발 할당 폭주"를 shard당 1건으로 직렬화하되, 다른 스레드는
  블로킹 없이 다른 shard로 빠진다 — 그 결과 순간적으로 shard 0/1/2가 각각 4장씩 할당.
- 한 스레드가 게시한 새 L1은 수 µs 내에 다른 스레드들이 lock-free로 집어간다.

### 6.2 정상상태 수치 (4000 INSERT 전체)

| 지표 | 값 | 해석 |
|---|---|---|
| find/FOUND shard 분포 | **shard0=4001, shard1=6, shard2=1** | `find()`가 shard=0, bias=0 고정(bestspace.cpp:1361-1362) → 분산 설계 무력화. shard1/2는 shard0이 ALLOCATING인 순간(alloc/busy 8회)에만 사용됨. 리뷰 리포트 Blocking Finding #2의 실측 확증 |
| L1/probe | 76,314 (≈19회/INSERT) | bias 고정 → 모두가 같은 순서로 같은 stale 엔트리를 재확인 |
| L1/fix-CONTENDED | 555 | 무대기 스킵이 실제로 작동 (555회 중 대기 0) |
| L1/actual-small (stale 보정) | 2 | 선차감 모델 덕에 낙관치가 대체로 정확 |
| alloc/begin / busy | 13 / 8 | |
| 신규 페이지 | 48장 (12회 × 4) | 4000행 × 130B ≈ 508KB ≈ 46페이지와 정합 |
| candidate pop 성공 | 0 (전부 빈 큐) | 순수 성장 워크로드라 후보 공급원(delete/vacuum)이 없음 |

**동시성 모델 요약**: 같은 L1 entry를 두 스레드가 동시에 잡으려 하면 (a) page latch가
1차 중재(zero-wait), (b) L1 CAS가 2차 중재(선차감은 fix 성공자만 수행), (c) 패자는
같은 tier의 다른 L1 → 다음 tier → allocate → 다음 shard 순으로 우회한다. 공유 상태에
대한 blocking 대기는 오직 candidate queue mutex(짧은 임계구역)와 "전 shard ALLOCATING"
상황의 yield 루프뿐이다.

## 7. free space 피드백 경로 (누가 bestspace를 채우나)

### 7.1 heap_add_bestpage (heap_file.c:4612)

유입 지점 3곳:
- `heap_delete_physical` (heap_file.c:22020) — DELETE의 물리 삭제 직후
- `heap_rv_undo_insert` (heap_file.c:16158) — INSERT undo 복구
- `heap_update_statistics` (heap_file.c:8954) — 전체 페이지 스캔 통계 재수집(compactdb 등),
  bestspace 페이지는 `heap_page_is_bestspace`로 제외

동작: `heap_find_bestspace(thread_p, NULL, hfid, …)` — **class_oid 없이 lookup-only**.
등록된 bestspace가 있으면 free space가 **FS3(25%) 이상**일 때만 `try_push_candidates`
(try_to_lock — mutex 경합 시 그냥 버림). 없으면 **아무 일도 하지 않고 버린다**.

candidate queue (bestspace.cpp:1069-1226): 128칸 고정 배열, free space **오름차순** 정렬,
중복 vpid 제거, 가득 차면 최소값 축출. pop은 큰 것부터 최대 4개.

### 7.2 vacuum 경로 실측 — 유실 확인 (리뷰 Finding #3 재현)

서버 재시작 후 SA에서 `VACUUM` 실행 (2000행 삭제분 처리):
```
evidence/trace-sD-sa-vacuum.log:
  reg/miss hfid=1|768|769 (not in global registry)   × 37회
  … heap/add_bestpage, cq/push 이벤트 0회
```
vacuum이 37개 페이지의 공간을 회수하며 후보 등록을 시도했지만, 새 프로세스의 registry에
bt_multi entry가 없어 **37건 전부 유실**됐다. in-memory bestspace는 INSERT가 처음 올 때
디스크의 (vacuum 이전) snapshot으로 만들어지므로 이 정보는 복구되지 않는다.

### 7.3 유실의 결과 — page bloat 실측

vacuum 직후 SA에서 60행 INSERT (evidence/trace-sE-sa-postvacuum-insert-excerpt.log):
```
heap/build hdr(cands=0 est_pages=48 est_recs=4001)   ← 후보 0개, estimates도 삭제 미반영
L1/probe l1=0 rec_fs=1688 vpid=1|769   ┐
L1/probe l1=1 rec_fs=1688 vpid=1|774   │ shutdown 시점의 stale freespace.
… (l1=2~5, rec_fs=1744)               │ 실제로는 vacuum으로 대부분 빈 페이지지만
                                       ┘ 기록값 1688/1744 < needed 1766 → 전부 skip
find/FOUND vpid=1|817                  ← 꼬리의 (마침 기록값이 큰) 페이지만 사용
```
매 INSERT마다 같은 stale 엔트리 6개를 헛 probe한 뒤 꼬리 페이지로 간다. 회수된 공간은
사용되지 않는다 — L1 기록값이 낙관(과대)일 때는 fix-실측-보정으로 자가치유되지만,
**비관(과소)일 때는 스스로 고쳐질 계기가 없다**(해당 페이지를 fix해볼 이유가 없으므로).
30초 sync는 in-memory→disk 방향이라 도움이 안 되고, compactdb/heap_update_statistics 같은
전체 스캔만이 복구 수단이다.

### 7.4 estimates는 단조 증가

2000행 DELETE 후에도 `est(recs=4000)`이 유지되고 30초 sync가 그 값을 디스크에 그대로
기록하는 것을 실측했다 (`heap/disk-sync … est(pages=48 recs=4000 sumlen=524832)`).
`subtract_estimates`는 rebuild 시 `set_estimates`(bestspace.cpp:1397, shard0에 몰아넣고
나머지에서 빼는 방식) 외에는 호출자가 없다. 정확한 값은 full-scan 계열
(`heap_update_statistics` → `set_estimates`, heap_file.c:9125 / heap_reuse 5883)에서만 재설정된다.
→ optimizer가 보는 `num_recs`/`recs_sumlen`은 "삽입 누계" 힌트로 이해해야 한다.

## 8. 영속화: 30초 주기 sync와 shutdown sync

### 8.1 30초 주기 (inserting 스레드가 수행)

`heap_find_bestpage`(heap_file.c:4593-4601)에서 `bestspace->updatable()`
(bestspace.cpp:1310: `m_last_updated`에 30초 경과 CAS — 승자 1명만 true) →
`heap_update_bestspace`(heap_file.c:4156):

```
to_entries: 전 shard L1 스냅샷 + candidate queue 스냅샷
get_estimates: shard 합산
→ header WRITE latch: bestspace 페이지 vpid 목록 획득
→ heap_update_bestspace_entries (heap_file.c:4053):
     각 shard 페이지 ordered fix → slot 2 spage_update
     + RVHF_UPDATE_BESTSPACE_ENTRIES(=130, recovery.h:187) redo 로그
→ header에 candidates/estimates/num_shards 기록
```

실측: 4000행 burst 39초 뒤 단발 INSERT 한 건이 sync를 트리거하고 이어서 자기 탐색을 계속했다:
```
heap/30s-sync-trigger hfid=1|768|769
heap/disk-sync … entries=512 cands=0 est(pages=48 recs=4000 …)
find/enter … → find/FOUND
```
sync 시점이 "타이머 스레드"가 아니라 **다음 INSERT 요청 스레드**라는 점이 재작성 시 중요하다.
(find 직전에 하는 이유: 코드 주석대로 update가 fix 페이지를 unfix할 수 있어 find 결과 페이지를
쥔 채로는 못 하기 때문.)

### 8.2 shutdown sync (gdb + 트레이스 실측)

```
xboot_shutdown_server (boot_sr.c:3088)
  → heap_update_all_bestspaces (heap_file.c:4287)
    → cubstorage::bestspaces.for_each(heap_update_bestspace_registry_entry)
```
서버 stop 시 등록된 5개 heap 전부가 순서대로 disk-sync 됐다(카탈로그 4 + bt_multi).
registry mutex를 쥔 채 page I/O를 하지만 shutdown 단일 스레드 상황이라 성립하는 전제다
(Greptile 리뷰 스레드에서 지적된 사항).

crash 시에는 이 sync가 없다 — 마지막 주기 sync 이후의 L1/candidate 변화는 사라지고,
재시작 후 stale snapshot으로 rebuild된다. bestspace는 힌트이므로 정합성 문제는 없다는 것이
설계 전제이고, §7.3의 bloat이 그 대가다.

### 8.3 복구/복제 관점

- shard 페이지 갱신은 redo-only(RVHF_UPDATE_BESTSPACE_ENTRIES)로 기록되어 crash redo 시
  마지막 checkpoint 상태로 복원된다.
- `heap_rv_undo_insert`가 undo 중 add_bestpage를 호출해 후보를 되살린다(heap_file.c:16158).
- supplemental log(CDC)와 replication이 bestspace 페이지 변경을 데이터 변경으로 오인하지
  않도록 recovery index 분리 및 redo LSA 지점 조정이 커밋 히스토리에 포함되어 있다
  ("skip operation if the page is bestspace …", "change supplemental redo LSA log point").

## 9. 재시작 후 rebuild (시나리오 실측 종합)

```
서버 기동 → registry 비어 있음
첫 INSERT → reg/miss ×2 → header latch → heap_build_bestspace
  entries 512개(shard 페이지에서), candidates(헤더에서), estimates(헤더에서) 로드
  → 이후 통상 경로
```
단, §7에서 본 것처럼 "첫 INSERT 이전"에 vacuum/delete가 회수한 공간은 이 snapshot에 없다.
`heap_reuse`(TRUNCATE 계열, heap_file.c:5013-5210)는 예외적으로 페이지를 걷어 후보를
헤더에 직접 다시 채우고 registry를 destroy하여 다음 조회 때 재구축시킨다.

## 10. 실측으로 확인된 미해결 이슈 정리 (재작성 시 개선 목표)

| # | 이슈 | 실측 증거 |
|---|---|---|
| 1 | shard 0/bias 0 고정 시작 → 분산 무력화 | 4008 FOUND 중 4001이 shard0 (§6.2) |
| 2 | registry 미등록 시 add_bestpage 전량 유실 | vacuum 37건 유실, boot/delete 경로에서도 산발 유실 (§7.2) |
| 3 | 과소-stale L1은 자가치유 불가 → freed 공간 미재사용(bloat) + 반복 헛 probe | §7.3 |
| 4 | estimates 단조 증가 (delete 미반영) | recs=4000 유지 (§7.4) |
| 5 | tier 경계 낭비: 같은 tier 안의 "약간 작은" 페이지들을 매번 probe | needed=1766(FS1) vs rec_fs=1688(FS1) 반복 probe (§7.3) |

(1,2는 리뷰 리포트의 Finding #2/#3와 일치. 디스크 호환성 이슈(Finding #1)는 본 실험이 신규
DB 기준이라 재현 대상이 아니었음 — 05-rewrite-spec에서 다룸.)

## 11. 재현 방법

```
# 1) 계측 패치 적용 (원본은 f30f1c260 기준)
git apply evidence/bstrace-instrumentation.patch     # BSTRACE_DIR 경로는 환경에 맞게 수정
# 2) 빌드/설치 후 (release 모드 무방)
# 3) SA 단일: csql -S -u dba <db> 로 create table + insert → bstrace.<pid>.log
# 4) CS 동시: cubrid server start <db>
bash evidence/gen_workload.sh 8 500 && bash evidence/run_multi.sh 8
#    → 서버 pid의 bstrace.<pid>.log 분석 (find/FOUND의 shard 분포, CONTENDED 등)
# 5) delete → (SA에서) vacuum → insert 로 §7 재현
# 6) gdb 스택: evidence/gdb_run1.log 생성에 쓴 스크립트는 scratchpad 참조,
#    비계측 빌드에서 break heap_insert_logical / cubstorage::bestspace::find 등
```

계측 없이 관찰만 할 때: `SHOW HEAP HEADER OF <table>`(show_meta 갱신됨), gdb로
`cubstorage::bestspaces` 전역을 직접 덤프하는 방법도 있다.
