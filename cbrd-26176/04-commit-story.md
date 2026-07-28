# CBRD-26176 Redesign bestspace — 커밋 스토리 / 재구현 청사진

| 항목 | 값 |
|---|---|
| 대상 PR | [CUBRID/CUBRID#7353](https://github.com/CUBRID/CUBRID/pull/7353) `[CBRD-26176] Redesign bestspace` |
| 기준 머지 커밋 | `e84a7f6dcd175e6ce85ceddb9a16036170cbe405` (squash merge, parent `b63fbc5dc`) |
| PR 브랜치 tip | `cc6bd0d6e` — 총 57 커밋 |
| 작성일 | 2026-07-28 |
| 작성 주체 | claude-fable-5 |

> **머지 방식에 대한 주의.** 과제 지시서에는 "squash 없이 merge"라고 되어 있으나, 실제 `e84a7f6dc`는 **parent가 하나뿐인 squash merge 커밋**이다 (`git log -1 --format=%P e84a7f6dc` → `b63fbc5dc` 단일). 따라서 `e84a7f6dc^2`는 존재하지 않으며, 57개 개별 커밋은 `develop` 히스토리에 남아 있지 않다. 이 문서는 `git fetch origin pull/7353/head:refs/remotes/pr/7353` 로 PR head를 별도 fetch해 작성했다. 재현하려면 동일하게 fetch한 뒤 `git log cd2d4718b^..cc6bd0d6e` 를 사용하라.

> 코드 인용의 `file:line`은 모두 **PR tip(`pr/7353`) 시점의 최종 상태** 기준이다. 커밋 인용은 `short hash + subject` 형식이다.

---

## 0. 이 문서를 읽는 법

57개 커밋을 시간순으로 따라가면 "무엇을 만들었는가"는 보이지만 "왜 그 순서였는가"와 "무엇을 몰라서 나중에 고쳤는가"는 보이지 않는다. 이 문서는 커밋을 **의미 단위 마일스톤 6개**로 재그룹핑하고, 후반 수정들을 **재작성 시 미리 알아야 할 함정 18개**로 승격시킨 뒤, 마지막에 **권장 재구현 순서**를 제시한다.

핵심 요약을 먼저 말하면 이렇다. 이 PR은 기능적으로는 다섯 덩어리(인메모리 자료구조 → heap 연결 → 디스크 영속화 → 통계/체크포인트 → 레거시 제거)로 깔끔하게 나뉘지만, **실제 커밋 순서는 이 다섯 덩어리가 서로 인터리브되어 있다.** 그 결과 레거시 제거가 전체 작업의 60% 지점에서야 시작됐고, 그 사이 구/신 bestspace가 공존하면서 온디스크 포맷이 세 번 바뀌었다. 후반 수정 18건 중 상당수는 "새 코드의 버그"가 아니라 **"새 자료구조가 heap 파일 페이지 체인 앞머리에 끼어들면서 기존 서브시스템 전체가 깨진 것"**이다. 재작성한다면 이 순서를 바꾸는 것이 가장 큰 개선이다.

---

## 1. 마일스톤 표

| # | 마일스톤 | 커밋 (시간순) | 한 줄 요약 |
|---|---|---|---|
| **M1** | 인메모리 뼈대 | `cd2d4718b` base for in-memory bestspace<br>`eabbf4bcf` implement the bestspace registry and add stats for debug<br>`a8482a6e6` split the allocating bit and L3<br>`17cdc9c6c` stats<br>`2c7071fd3` adjust the needed size according to unfill space<br>`862accf8b` make the number of shards dynamic<br>`37c8e1a7e` add parameter and make the number of shards dynamic<br>`65d4465a5` implement candidate queue using mutex to sort by free space in ascending order<br>`29b6d62f9` refactoring | `cubstorage::bestspace` 클래스 신설. L1/L2/L3 3단 비트맵 계층, shard 배열, 레지스트리, candidate 큐를 세운다. |
| **M2** | heap 연결 | `3cdcfa482` create bestspace when creating the heap file<br>`77c61edfd` add the function that creates the bestspace<br>`96d938ab8` add heap functions and candidates queue<br>`70d06a092` pick the new bestspaces from the candidates queue<br>`cc40a2a13` pick victim pages and replace them with selected or allocated candidates<br>`9aa2ec434` avoid duplicate replacement pages | heap 파일 생성 훅에 bestspace 생성을 끼우고, victim 선정 → candidate 교체 → 신규 페이지 할당의 3단 폴백을 완성한다. |
| **M3** | 온디스크 영속화 | `c69fcd8e2` skip operation if the page is bestspace and add bestspace recovery index to avoid replication<br>`c0bd88f54` implement updating the bestspace on disk and uses the feature in heap_reuse<br>`0b9d902d8` (disk) insert the candidate page into candidates in heap header page<br>`0927b26a8` move the prototype<br>`018b717a5` take the bestspace pages and candidates from the heap header and shard pages<br>`8a5ac1efc` re-build the in-memory bestspace if there is no bestspace for class_oid<br>`218c9f98a` implement to update the heap header<br>`25c037528` add fallback path to refill the candidates | 전용 shard 페이지를 heap 파일 안에 만들고, 엔트리/candidate/추정치를 디스크에 왕복시킨다. 전용 recovery index를 신설한다. |
| **M4** | 통계·체크포인트·동시성 마감 | `503cb7a6c` uses ordered fix to avoid deadlock in bestspace path<br>`b0ef2eb9d` add estimates logic into shrads<br>`bf060ec80` make estimates path use the atomic variable in in-memory bestspace<br>`00f285506` change the heap_update_bestspace* interface<br>`0918cdeee` add the bestspace update logic<br>`a5281197e` add update path<br>`304f3b0d0` implement a pgbuf helper for calling functions without fixing pages | num_pages/num_recs/recs_sumlen를 shard별 atomic으로 분산하고, 30초 주기 디스크 체크포인트를 건다. 모든 페이지 고정을 ordered fix로 통일한다. |
| **M5** | 레거시 제거 | `dd6561c31` make the parameter PRM_ID_HF_MAX_BESTSPACE_ENTRIES obsolete<br>`0f97b0d7c` change the usage of bestspace<br>`4431d624b` change bestspace interface in heap<br>`6e3428c58` make the compactdb refresh bestspace and candidates. and remove obsolete code<br>`830433756` remove legacy code and modify the show meta<br>`ccb9d8cec` remove the bestspace stats parts<br>`0ba2a3603` uese only hfid as a key<br>`7fff8882d` remove useless code<br>`cc6bd0d6e` remove useless parameter | 구 전역 해시 캐시, second-best 링, PSTAT 카운터, SHOW 컬럼, slotted page 힌트 비트를 걷어낸다. 레지스트리 키를 HFID 단독으로 축소한다. |
| **M6** | 후반 수정 (→ §3 함정 목록) | `1c2ebe547` `f58efc6d5` `5e8a8ce5e` `c82351d2e` `6a05792d8` `b66bf7073` `0f6e9aef0` `70b33a3f0` `690ecc8b7` `7c862d2bc` `69cb51f0b` `e7d28622e` `236780601` `09e01d435` `570ee2677` `026e78a87` `9553c7d38` `6b6111fe9` | 정합성·동시성·통계·운영 4개 축의 사후 수정 18건. 재작성 시 처음부터 반영해야 할 항목들. |

합계 9 + 6 + 8 + 7 + 9 + 18 = **57 커밋**.

---

## 2. 마일스톤별 상세

### M1 — 인메모리 뼈대

#### 도입된 개념

`src/storage/bestspace.hpp` / `bestspace.cpp` 두 파일이 통째로 신설된다 (`cd2d4718b`, 초기 728+267 라인). 전체가 `namespace cubstorage`, 클래스 `bestspace` 안의 중첩 타입으로 구성된다.

핵심은 **"free space 크기를 8단계 tier로 양자화하고, 그 tier 소속 여부만 비트맵으로 요약해 3단 계층으로 쌓는다"**는 아이디어다.

| 계층 | 내용 | 크기 |
|---|---|---|
| `L1` | 실제 힙 페이지 하나. `uint16 m_freespace; short m_volid; int32 m_pageid;` | 정확히 8바이트 → `std::atomic<L1>`이 lock-free |
| `L2` | `std::array<bitmap, 8>` — tier별 8비트 비트맵. tier `t`의 비트 `i` = "내 밑 L1 슬롯 `i`가 tier `t`에 속함" | 8바이트 |
| `L3` | 동일 레이아웃. tier `t`의 비트 `i` = "내 밑 L2 그룹 `i`에 tier `t` 페이지가 하나 이상 있음" | 8바이트 |

tier는 free space 비율 기준으로 잘린다 (`bestspace.cpp:1381`):

```cpp
static constexpr std::int16_t threshold[] = { 7, 15, 24, 34, 45, 57, 70, 84 };
```

`FS0 = -1` (1~7%)은 **인덱싱하지 않는 센티널**이고 `FS1`(8~15%) ~ `FS8`(85~100%)만 L2/L3 비트맵에 올라간다. 이 "FS0은 인덱스에 없다"는 사실이 나중에 함정 T9를 낳는다.

한 shard는 `L3_FANOUT * L2_FANOUT = 8 * 8 = 64`개 페이지를 추적한다 (`bestspace.hpp:78-80`). 탐색은 `shard::find` → `L3_find` → `L2_find` → `L1_find`로 내려가며, 각 단계가 64비트 atomic load 한 번으로 끝난다. 갱신은 역방향으로 `L1_find`가 CAS → `L2_update` → `L3_update`로 올라간다.

#### `a8482a6e6` — allocating 비트를 L3에서 분리 (구조적 전환점)

초기 설계는 "이 shard에서 누군가 페이지 할당 중"이라는 플래그를 **L3 비트맵 워드 안에** 넣었다:

```cpp
static constexpr std::uint64_t FLAG_MASK       = 0x8080808080808080;
static constexpr std::uint64_t FLAG_ALLOCATING = 0x8000000000000000;
```

`operator==`가 8개 바이트 **전부의** 최상위 비트를 마스킹했기 때문에, 모든 tier 비트맵에서 인덱스 7이 사용 불가가 됐다. 그래서 `L3_FANOUT = 7`, shard당 56페이지, `sizeof(shard) == 4160`이었다. 게다가 할당 마킹이 L3 워드 전체에 대한 CAS라서 실제 tier 갱신과 경합했다.

이 커밋이 플래그를 독립 멤버로 빼낸다:

```cpp
atomic_wrapper<bool> m_allocating;   // shard의 첫 멤버로 분리
```

결과: `L3_FANOUT = 8`, shard당 **64페이지**, `sizeof(shard) == 4800`, L3가 L2와 완전히 동일한 형태가 되고 (`memcmp` 비교), 할당 마킹이 bool CAS로 축소된다. 같은 커밋에서 `class_oid`가 탐색 경로 전체에 실려 `L1_find`가 페이지 fix 후 소유권을 재검증하게 되고, `L2_update`/`L3_update`에 ABA 방어용 재확인 루프가 붙는다.

#### 레지스트리

`eabbf4bcf`가 `bestspace_registry`와 전역 `cubstorage::bestspaces`를 추가한다. 흔히 예상하는 해시맵이 **아니다** — 뮤텍스 하나로 보호되는 intrusive 단일 연결 리스트이고, 그 앞에 스레드 로컬 LRU 리스트가 붙는다:

```cpp
registry_entry *m_head;
std::mutex m_mutex;
inline static thread_local registry_entry *TLS_head;   // 초기 20개, 이후 40개
alignas (64) std::atomic<uint64_t> m_generation;       // destroy 시 증가 → TLS 일괄 무효화
```

조회는 TLS 리스트 → 미스 시 뮤텍스 잡고 전역 리스트 → 결과를 TLS에 설치, 2단이다. 드롭된 heap의 stale 엔트리는 `m_generation` 세대 카운터로 무효화한다.

#### 나머지 M1 커밋

- `2c7071fd3` — `size` 하나를 `needed_size`(수용 판정 기준)와 `consume_size`(실제 차감량) **둘로 분리**한다. `needed_size = size + SPAGE_SLOT_SIZE + unfill_space`. `unfill_space`는 CUBRID가 예전부터 갖고 있던 "업데이트용 여유분"(`HEAP_HDR_STATS::unfill_space`, `heap_file.c:195`)인데 구 bestspace는 이를 무시했다. 단, 예약분 때문에 삽입 자체가 불가능해지면 예약을 포기한다 (`bestspace.cpp:1354-1359`).
- `862accf8b` + `37c8e1a7e` — shard 개수를 컴파일 타임 상수에서 런타임 값으로. 새 시스템 파라미터 `bestspace_shard_count` (`PRM_ID_BESTSPACE_SHARD_COUNT`, `system_parameter.h:538`, 기본 8, 범위 1~28)를 추가한다. 컨테이너가 `std::array` → `std::vector` → **`std::deque`**로 두 번 바뀌는데, 마지막 전환은 shard가 `bestspace &m_parent` 참조 멤버를 갖게 되면서 대입 불가 타입이 되었고 vector 재할당이 컴파일되지 않기 때문이다.
- `65d4465a5` — candidate 큐를 `tbb::concurrent_queue`(무순서 FIFO)에서 **뮤텍스 + 고정 배열 정렬 큐**로 교체한다. 128슬롯, free space **오름차순** 유지(꼬리가 최선), 꼬리에서 batch pop, 만원 시 최악 항목 축출, VPID 기준 중복 제거. blocking `push()`와 경합 시 즉시 포기하는 `try_push()` 두 가지를 제공한다.
- `29b6d62f9` — 비대해진 `shard::allocate`에서 `allocate_get_candidates_or_update_residents` / `allocate_verify_actual_space` / `allocate_verify_or_allocate`를 추출. 동작 변화 없음.

#### 이전 단계와의 의존 관계

M1은 진입점이며 외부 의존이 없다. 다만 **내부 순서 의존이 강하다**: `a8482a6e6`(fanout 7→8)이 늦게 오는 바람에 `unit_tests/bestspace/test_bestspace.cpp`가 964라인 규모로 재작성됐고, 곧이어 `cc40a2a13`(M2)에서 **테스트 파일이 통째로 삭제된다.** 이 유닛 테스트는 끝까지 복구되지 않았다. 재작성 시 fanout/레이아웃 상수를 처음부터 확정하면 이 손실을 피할 수 있다.

---

### M2 — heap 연결

#### 도입된 개념

heap 파일이 생성될 때 bestspace도 함께 태어나고, 삽입 경로가 구 `heap_stats_find_best_page` 대신 신 bestspace를 타게 만든다.

`3cdcfa482`가 가장 파괴적이다. `HEAP_HDR_STATS`의 `estimates` 서브구조체 전체(`best[10]`, `second_best[10]`, `head`, `num_high_best`, `num_second_best`, `full_search_vpid` …)를 삭제하고 새 `bestspace` 서브구조체로 대체한다. 동시에 구 전역 캐시 함수군(`heap_stats_add_bestspace`, `heap_stats_sync_bestspace`, `heap_stats_put_second_best` 등 10여 개)을 제거한다. **온디스크 포맷 파괴 변경이 여기서 일어난다** — 이후 M3/M5에서 이 구조체가 두 번 더 바뀐다.

#### 할당 경로의 3단 폴백

`cc40a2a13` + `9aa2ec434`가 `shard::allocate`의 핵심 정책을 확립한다 (최종 `bestspace.cpp:1021-1067`):

1. `allocate_mark()` — shard의 `m_allocating`을 CAS. 실패하면 `ALLOCATING` 반환 → 호출자가 다음 shard로 이동.
2. `allocate_pick_victims()` — 64개 L1 슬롯을 한 번 훑어 free space가 **가장 작은** 4개를 victim으로 삽입 정렬. 동시에 **전체 resident VPID 목록**을 기록한다 (`9aa2ec434`가 추가). 이 목록이 없으면 같은 VPID가 두 L1 슬롯에 중복 설치될 수 있었다.
3. `allocate_pick_candidates()` — candidate 큐에서 최대 4개 pop, resident 목록과 대조해 신규/기존을 분류.
4. `allocate_new_pages()` — 부족분을 `heap_alloc_new_pages`로 실제 할당. **항상 최소 1페이지는 신규**이며, 그 페이지가 호출자에게 fix된 채 반환된다.
5. `allocate_replace_pages()` — 슬롯 0~2는 무조건 교체, 슬롯 3(대상 페이지)은 victim보다 실제로 나을 때만 교체.

`ALLOC_BATCH_SIZE = 4`는 여기서 굳어진다.

#### 이전 단계와의 의존 관계

M2는 M1의 `shard::find` / `allocate` 골격에 전적으로 의존한다. 역으로 M1의 후반 커밋(`2c7071fd3`, `65d4465a5`, `29b6d62f9`)은 M2가 만든 `allocate_pick_candidates`를 수정하므로, **M1과 M2는 실제로는 한 덩어리로 왕복하며 자랐다.** 표에서 시간순이 뒤섞여 보이는 이유다.

---

### M3 — 온디스크 영속화

#### 도입된 개념: shard 페이지

bestspace 엔트리를 담을 **전용 힙 페이지**를 heap 파일 자신의 VFID에서 할당한다. shard 페이지는 슬롯 두 개짜리 일반 힙 페이지다:

- 슬롯 0 (`HEAP_HEADER_AND_CHAIN_SLOTID`) — 평범한 `HEAP_CHAIN`, 단 신규 플래그 비트가 켜짐
- 슬롯 1 (`HEAP_BESTSPACE_ENTRIES_SLOTID`, `heap_file.c:231`) — `bestspace_entry` 평면 배열

플래그는 기존 `HEAP_CHAIN::flags`의 비트 0을 빌린다 (`heap_file.c:220`):

```c
#define HEAP_PAGE_FLAG_BESTSPACE                  0x00000001
```

**이 설계의 대가가 M6 함정 상당수의 근원이다.** shard 페이지는 heap 파일 페이지 체인의 **맨 앞에** 삽입된다 (`heap_file.c:3902-3903`):

```c
heap_hdr->next_vpid = heap_hdr->bestspace.pages[0];
heap_hdr->last_vpid = heap_hdr->bestspace.pages[heap_hdr->bestspace.num_pages - 1];
```

즉 **기존의 모든 힙 스캐너가 이 페이지를 밟는다.** 그래서 `heap_page_is_bestspace()` (`heap_file.c:2750`, `heap_file.h:427`로 export) 가드를 `heap_get_num_objects`, `heap_get_capacity`, `heap_next_internal`, `heap_page_next/prev`, `xheap_reclaim_addresses`, `heap_chkreloc_next` 등 9곳 이상에 뿌려야 했다. 그러고도 M6에서 통계 경로(`9553c7d38`)와 파티션 재구성 경로가 추가로 발견된다.

shard 페이지 개수는 파라미터의 **현재 값이 아니라 상한**으로 산정한다 — `bestspace_shard_count`를 튜닝해도 파일 레이아웃이 안 바뀌게 하기 위함이다 (`heap_file.c:3840-3854`). `MAX_SHARD_PAGE_COUNT = 4`, 상한 28 shard × 64 엔트리 = 1792 엔트리 ≈ 14KB.

#### candidate는 헤더 페이지에

엔트리는 shard 페이지 슬롯 1에, **candidate는 헤더 페이지 안 `HEAP_HDR_STATS::bestspace.candidates[128]` 인라인 배열에** 저장된다 (내림차순). 즉 저장 위치가 둘로 나뉜다:

```
엔트리   → shard 페이지 슬롯 1   (RVHF_UPDATE_BESTSPACE_ENTRIES)
candidate → 헤더 페이지 슬롯 0    (RVHF_STATS 의 일부)
추정치    → 헤더 페이지 슬롯 0    (RVHF_STATS 의 일부)
```

#### 전용 recovery index

`c69fcd8e2`가 `RVHF_UPDATE_BESTSPACE_ENTRIES = 130`을 추가한다 (`recovery.h:187`, 테이블 `recovery.c:844-849`, redo 전용/undo 없음). 커밋 제목의 "to avoid replication"이 핵심이다.

CUBRID HA 로그 어플라이어는 페이지 단위가 아니라 **heap recovery index 화이트리스트를 보고 논리적 행 연산을 역산한다.** 마스터 측 `log_manager.c:2198-2210`이 `RVHF_UPDATE` 등에 대해 `tdes->repl_update_lsa`를 찍고, 슬레이브 측 `log_applier.c:5151-5158`은 화이트리스트 밖 인덱스를 만나면 `ER_FAILED`로 죽는다. shard 페이지 슬롯 1의 레코드는 객체가 아니라 생 바이트 배열이므로, 만약 `RVHF_UPDATE`를 재사용했다면 체크포인트마다 어플라이어가 이를 복제 대상 인스턴스로 해석하려다 실패했을 것이다. 화이트리스트에 없는 새 번호를 쓰면 양쪽이 조용히 무시하면서도 redo 복구는 정상 동작한다.

같은 이유로 초기 삽입은 `RVHF_INSERT`가 아니라 `RVHF_INSERT_NEWHOME`을 쓴다 (`heap_file.c:3959-3964`에 주석으로 명시).

#### 재구축 경로

`8a5ac1efc` — 인메모리 bestspace가 없으면 (`ER_MHT_NOTFOUND`) 헤더를 WRITE 래치로 ordered fix → **래치 아래서 재확인**(다른 스레드가 먼저 만들었을 수 있음) → shard 페이지에서 엔트리 로드 → `bestspaces.create` → 재시도. 최종 형태는 `heap_find_bestspace` (`heap_file.c:4505-4578`) + `heap_build_bestspace` (`:4395-4496`)로 분리되어 있다.

`class_oid` 인자에 의도적 비대칭이 있다 (`heap_file.c:4521-4531`): **NULL 포인터 = 조회만 하고 재구축 금지**, **NULL OID 값 = 부트스트랩 중 root class이므로 재구축**. 이 비대칭이 함정 T15의 해법이 된다.

#### 이전 단계와의 의존 관계

M3는 M2의 `heap_create_internal` 훅과 `heap_reuse` 경로에 얹힌다. 반대로 M3가 도입한 shard 페이지가 M5의 `compactdb` 재작성과 M6의 통계 수정을 강제한다. **M3는 이 PR에서 파급 범위가 가장 넓은 단계다.**

---

### M4 — 통계·체크포인트·동시성 마감

#### estimates의 이주

`num_pages` / `num_recs` / `recs_sumlen` 세 값은 원래 헤더 페이지 래치 아래서만 갱신되는 온디스크 필드였다. M4는 이를 **인메모리 atomic으로 옮기고 shard별로 분산**한다 (핫 캐시라인 회피).

`b0ef2eb9d`가 shard에 원자 카운터를, `bf060ec80`이 owner 레벨 base atomic과 `m_num_pages`를 추가한다 (`bestspace.hpp:267-269`, `:389-392`). 인터페이스는 `add_estimates` / `subtract_estimates` / `get_estimates` / `set_estimates`이며, `get_estimates`가 out 파라미터에 **대입이 아니라 누적**한다는 점이 특이하다 — owner가 base 값을 시드로 넣고 각 shard 델타를 접어 넣는 방식이다.

`set_estimates`는 전체 리셋이다. 각 shard 델타를 읽어 빼서 0으로 만든 뒤 base를 store하는데, 이 순서가 함정 T14에서 문제가 된다.

디스크 헤더는 이제 **체크포인트일 뿐**이며, 살아 있는 값은 인메모리에 있다. `heap_estimate()` (`heap_file.c:9161-9218`)는 인메모리를 먼저 보고, 미상주일 때만 헤더를 fix하는 폴백을 쓴다.

#### 30초 체크포인트

`a5281197e`가 `bestspace::updatable()`을 완성한다 (`bestspace.cpp:1309-1322`):

```cpp
constexpr std::uint64_t UPDATE_TIME_THRESHOLD = 30;
last_updated = m_last_updated.load ();
now = monotonic_seconds ();
if (now >= last_updated && now - last_updated >= UPDATE_TIME_THRESHOLD)
  {
    return m_last_updated.compare_exchange_strong (last_updated, now);
  }
return false;
```

이것은 조회가 아니라 **선점(claim)**이다. CAS 때문에 30초 창마다 정확히 한 스레드만 `true`를 받고 나머지는 그대로 탐색으로 빠진다. 시각 소스는 `steady_clock` (`bestspace.cpp:47-52`) — 벽시계 점프가 체크포인트를 유발하거나 억제하면 안 되기 때문이다.

> **갭:** 30초는 하드코딩 상수다. 튜닝 파라미터가 없다. bestspace 관련 파라미터는 `PRM_ID_BESTSPACE_SHARD_COUNT`와 `PRM_ID_DEBUG_BESTSPACE` 둘뿐이며 어느 쪽도 주기를 바꾸지 않는다. 재작성 시 노출 여부를 결정하라.

#### ordered fix 통일

`503cb7a6c`가 bestspace 경로의 모든 페이지 고정을 생 `pgbuf_fix`에서 `pgbuf_ordered_fix`로 전환하고, 검증까지 묶은 `heap_bestspace_fix_page()` (`heap_file.c:3762`)를 도입한다. CUBRID의 ordered fix는 힙 페이지 래치 순서를 강제해 데드락을 막는 기존 장치인데, 새 코드가 이를 우회하고 있었다.

`304f3b0d0`은 이 장치의 **신규 확장**이다. `pgbuf_ordered_callback()` (`page_buffer.h:290`, 구현 `page_buffer.c:12971`) — "보유 중인 ordered 페이지를 전부 일시 해제하고, 콜백을 실행하고, 순서대로 다시 fix한다". 이것이 함정 T7의 해법이다.

#### 이전 단계와의 의존 관계

M4는 M3의 헤더/shard 페이지 왕복 함수에 의존한다. `00f285506`이 `heap_update_bestspace*`의 시그니처를 `HEAP_HDR_STATS*`에서 `(class_oid, hfid, pages, num_pages)` 평면 인자로 바꾸는데, 이는 `heap_reuse`가 헤더 전체를 스택에 복사해 넘기던 우회를 없애기 위함이다.

---

### M5 — 레거시 제거

전체 작업의 60% 지점에서야 시작된다. 제거 대상:

| 대상 | 커밋 | 내용 |
|---|---|---|
| 전역 해시 캐시 | `830433756` | `heap_Bestspace` (VPID/HFID 두 개의 mht + 뮤텍스), `heap_stats_find_page_in_bestspace`(약 380라인), `heap_stats_put/get_second_best`, `heap_hash_vpid/hfid`, `heap_bestspace_to_string` 등 13개 함수. `heap_check_all_pages`의 검증 블록 83라인 포함. |
| 시스템 파라미터 | `dd6561c31` | `PRM_ID_HF_MAX_BESTSPACE_ENTRIES`에 `PRM_OBSOLETED` 플래그 추가. **이름과 enum은 유지** (`system_parameter.c:1199-1210`) — 제거하면 이후 모든 PRM id가 밀린다. 설정해도 조용히 무시된다. |
| SHOW 컬럼 | `830433756` | `SHOWSTMT_HEAP_HEADER` / `SHOWSTMT_ALL_HEAP_HEADER`에서 `Estimates_*` 14개 컬럼 삭제, `Last_vpid`/`Num_pages`/`Num_recs`/`Avg_rec_len` 4개로 대체 (`show_meta.c:298-311`). |
| PSTAT 카운터 | `ccb9d8cec` | `PSTAT_HEAP_STATS_SYNC_BESTSPACE`, `PSTAT_HF_NUM_STATS_ENTRIES`, `PSTAT_HF_NUM_STATS_MAXED`, `PSTAT_HF_BEST_SPACE_ADD/DEL/FIND`, `PSTAT_HF_HEAP_FIND_PAGE_BEST_SPACE`, `PSTAT_HF_HEAP_FIND_BEST_PAGE` 8개. 파서 쪽 `RESERVED_P_UPDATE_BEST` 예약어와 `HEAP_PAGE_INFO_UPDATE_BEST`도 함께. |
| slotted page 힌트 비트 | `6e3428c58` | `SPAGE_HEADER::need_update_best_hint:1` 비트와 `spage_set_need_update_best_hint()`. `spage_get_free_space_without_saving()`에서 out 파라미터 제거 (`slotted_page.h:98`) → `btree.c` 4곳 호출부 수정. |
| 레지스트리 키 | `0ba2a3603` | 키를 `(class_oid, hfid)` 쌍에서 **HFID 단독**으로 축소. 부수효과로 `destroy`가 단일 제거에서 **드레인 루프**가 된다 (VFID를 class OID로 구분할 수 없으므로 일치하는 노드 전부 제거). `class_oid`는 이제 페이지에서 유도한다. |
| 캐시된 shard VPID | `7fff8882d` | `bestspace::m_header { VPID pages[4]; int page_num; }` 캐시 제거. `heap_update_bestspace`가 매번 갓 fix한 헤더에서 다시 읽는다 (→ 함정 T17). |

`0f97b0d7c` + `4431d624b`는 레지스트리 API를 "일을 대신 해주는" 형태에서 "객체를 넘겨주는" 형태로 뒤집는다: `int find(thread, class_oid, hfid, size, watcher)` → `bestspace *find(hfid)`. 이후 heap 쪽에 얇은 래퍼 `heap_find_bestpage()` / `heap_add_bestpage()`가 생긴다.

> **주의:** `6e3428c58`은 커밋 시점에 **컴파일되지 않는다.** 값 타입 `heap_hdr`에 `heap_hdr->bestspace.candidates`로 접근하고, `int i;`를 두 번 선언하며, `*num_candidates++` 우선순위 버그를 포함한다. 모두 후속 커밋에서 수정된다.

---

## 3. 함정 목록 — 재작성 시 미리 알아야 할 것들

M6의 18개 커밋(및 M4/M5에 섞인 사후 성격 수정)을 4개 축으로 재분류했다. 각 항목은 (a) 증상/문제 (b) 원인 (c) 수정 (d) 재작성 시 반영법 순이다.

### 축 A — 크기·개수 정합성

#### T1. `*num_candidates++` 연산자 우선순위

`1c2ebe547` fix \*num_candidates to (\*num_candidates)

- **(a) 증상** — candidate 개수가 증가하지 않고, 대신 포인터가 배열 밖으로 전진한다. 이후 `*num_candidates` 읽기가 미정의 동작.
- **(b) 원인** — C/C++에서 후위 `++`가 단항 `*`보다 우선순위가 높다. `*num_candidates++`는 `*(num_candidates++)`로 파싱된다. 같은 커밋에서 `assert (*num_candidates >= 0)`도 제거되는데, `std::size_t`는 부호 없는 타입이라 항상 참인 무의미한 단언이었다.
- **(c) 수정** — `(*num_candidates)++`.
- **(d) 재작성** — out 파라미터를 포인터가 아니라 **참조**(`std::size_t &num_candidates`)로 받으면 이 실수 자체가 불가능해진다. 이 파일은 `.c` 확장자지만 C++17로 컴파일되므로 참조를 쓸 수 있다. 부호 없는 타입에 `>= 0` 단언을 쓰지 말 것.

#### T2. 시스템 파라미터 lower/upper 인자 순서 역전

`5e8a8ce5e` change lower and upper

- **(a) 증상** — `bestspace_shard_count`의 범위가 `lower=28, upper=1`로 등록되어 정상 값이 거부되거나 범위 검사가 무의미해진다. 추가로 `sysprm_get_range`에 `std::size_t*`를 `void*`로 캐스팅해 넘기고 있어 **8바이트 변수에 4바이트 int를 쓰는** 타입 불일치가 있었다.
- **(b) 원인** — `prm_Def[]` 항목의 필드 순서는 `{default, value, lower, upper}`인데 lower/upper를 뒤집어 적었다. 캐스팅은 컴파일 에러를 눌러 없앤 결과.
- **(c) 수정** — 두 값 교환. 변수 타입을 `std::size_t` → `int`로 바꾸고 `void*` 캐스팅 제거. `max_entries = max_shards * 64` 매직넘버를 `ENTRIES_PER_SHARD` 상수로 교체.
- **(d) 재작성** — `prm_Def[]` 항목을 추가한 직후 `cubrid paramdump`나 범위 밖 값 설정으로 실제 검증할 것. **`sysprm_get_range`에 `void*` 캐스팅을 넣어야 한다면 타입이 틀린 것이다.**

#### T3. `heap_Maxslotted_reclength` 산정 기준 오류

`6a05792d8` fix max space length calculation to use HEAP_CHAIN

- **(a) 증상** — 일반 힙 페이지에 실제로 들어갈 수 있는 최대 레코드 길이를 과소평가한다.
- **(b) 원인** — `heap_manager_initialize()`가 `spage_max_record_size() - sizeof(HEAP_HDR_STATS)`로 계산했다. 그런데 M2에서 `HEAP_HDR_STATS`에 128슬롯 candidate 배열(1KB)이 인라인으로 들어가면서 이 구조체가 급격히 커졌다. **헤더 페이지가 아닌 일반 페이지의 슬롯 0에는 훨씬 작은 `HEAP_CHAIN`이 들어가므로** 기준 자체가 틀렸고, 게다가 새 필드 때문에 오차가 크게 벌어졌다.
- **(c) 수정** — 기준을 `HEAP_CHAIN`으로 교체. 최종 형태는 `heap_nonheader_page_capacity()` = `spage_max_record_size() - sizeof(HEAP_CHAIN)` (`heap_file.c:26015`).
- **(d) 재작성** — **온디스크 헤더 구조체를 키우는 변경은 그 구조체 크기에 의존하는 모든 상수를 감사하게 만든다.** `sizeof(HEAP_HDR_STATS)`를 참조하는 곳을 먼저 전수 조사한 뒤 필드를 추가하라. "헤더 페이지 용량"과 "일반 페이지 용량"을 별도 함수로 이름 붙여 분리하면 혼동이 없다.

#### T4. 레코드 길이 과대추정 — `SPAGE_SLOT_SIZE` 이중 계상

`b66bf7073` fix overestimate of record length

- **(a) 증상** — `recs_sumlen` 추정치가 실제보다 크게 누적된다. 옵티마이저의 평균 레코드 길이(`recs_sumlen / num_recs`)가 부풀려져 잘못된 플랜을 유발할 수 있다.
- **(b) 원인** — `consume_size = size + SPAGE_SLOT_SIZE`는 **페이지 공간 회계용** 값이다(슬롯 디렉터리 엔트리 포함). 그런데 통계 누적에도 그대로 썼다. `recs_sumlen`은 레코드 본문 길이의 합이어야 하므로 슬롯 오버헤드를 빼야 한다.
- **(c) 수정** — `add_estimates (0, 1, consume_size - SPAGE_SLOT_SIZE)` (`bestspace.cpp:1497`).
- **(d) 재작성** — **"공간 예약량"과 "레코드 길이"는 다른 양이다.** 같은 변수로 옮기지 말고 처음부터 이름을 분리하라 (`consume_size` vs `record_length`). 함정 T5와 짝을 이룬다.

#### T5. relocation 레코드를 신규 레코드로 계상

`70b33a3f0` do not count relocation record as a new record

- **(a) 증상** — `num_recs` 추정치가 실제 객체 수보다 커진다. 업데이트가 많은 테이블에서 오차가 누적된다.
- **(b) 원인** — bestspace 탐색 진입점이 두 개인데 둘 다 똑같이 `num_recs += 1` 했다. 하나는 `heap_get_insert_location_with_lock`(진짜 신규 삽입), 다른 하나는 `heap_find_location_and_insert_rec_newhome`(**기존 레코드가 커져서 다른 페이지로 이사하는 `REC_NEWHOME` 배치**)이다. 후자는 객체 수를 늘리지 않는다.
- **(c) 수정** — 탐색 경로 전체에 `bool is_newrec`를 실어 보낸다 (`bestspace.hpp:368`). 삽입은 `true`, relocation은 `false`. 누적은 `add_estimates (0, is_newrec ? 1 : 0, ...)` (`bestspace.cpp:1497`).
- **(d) 재작성** — **bestspace 탐색 API를 설계할 때 "왜 페이지를 찾는가"를 처음부터 인자로 받아라.** 최소 `INSERT_NEW` / `RELOCATE` 두 가지는 구분되어야 하며, 나중에 vacuum/compactdb가 붙으면 더 늘어난다. `bool`보다 enum이 낫다.

#### T9. FS0 미인덱싱으로 인한 tier 건너뛰기

`026e78a87` find exact size if not FS0

- **(a) 증상** — 요청 크기와 같은 tier에 충분한 페이지가 있는데도 그 tier를 건너뛰고 상위 tier를 찾거나, 못 찾으면 불필요하게 새 페이지를 할당한다. 페이지 사용률이 떨어진다.
- **(b) 원인** — 원래 코드는 `minimum = size_to_tier(needed_size); if (minimum < FS8) minimum++;` 였다. tier는 범위(예: FS3 = 25~34%)이므로 "FS3 페이지가 요청을 반드시 수용한다"는 보장이 없다 — 그래서 안전하게 한 칸 올렸다. 하지만 이건 과잉이다. **`L1_find`가 어차피 정확한 크기 검사를 두 번 한다** (캐시된 freespace 사전 검사 + 페이지 fix 후 재검사, `bestspace.cpp:585`). 같은 tier를 탐색해도 안전하다.
- **(c) 수정** — 같은 tier부터 탐색하되, **인덱싱되지 않는 `FS0`만 `FS1`로 올린다** (`bestspace.cpp:346-353`):
  ```cpp
  // FS0 is not indexed by L2/L3. search the same tier and let L1_find perform the exact size check.
  minimum = size_to_tier (needed_size);
  if (minimum == tier::FS0)
    { minimum = tier::FS1; }
  ```
- **(d) 재작성** — **양자화 계층을 만들 때 "센티널 tier"와 "정상 tier"의 처리를 처음부터 분리하라.** 그리고 "요약 계층은 후보를 좁히기만 하고, 정확성은 리프에서 보장한다"는 계약을 문서화하라. 이 계약이 명시되어 있었다면 tier를 올릴 이유가 없었다.

#### T13. candidate의 실제 free space 미검증

`69cb51f0b` fix / `236780601` ues the candidate only if the free space of candidate is enough to store the record

- **(a) 증상** — candidate 큐에서 꺼낸 페이지를 그대로 L1에 설치했는데, 큐에 들어간 시점 이후 다른 트랜잭션이 그 페이지를 채워버려 실제로는 공간이 없다. 삽입이 실패하거나 즉시 재탐색이 발생한다.
- **(b) 원인** — candidate 엔트리의 `freespace`는 **큐에 넣은 시점의 스냅샷**이다. 큐는 128슬롯이고 체류 시간이 길 수 있으므로 신뢰할 수 없다. 초기 구현은 tier 비교(`size_to_tier(buffer[i].freespace) <= minimum`)만으로 걸렀는데, 이는 stale 값에 대한 tier 비교라 아무것도 보장하지 못했다.
- **(c) 수정** — 2단계로 이뤄졌다. `69cb51f0b`이 tier 기반 필터를 걷어내고 `pop()`에 `(minimum, needed_size)`를 넘겨 큐 내부에서 실제 크기로 거르게 한다. `236780601`이 `allocate_check_actual_space()`를 완성한다 — 후보 페이지를 **실제로 ordered fix해서** 페이지 타입 확인, `class_oid` 소유권 확인, `spage_max_space_for_new_record()`로 **현재 free space를 다시 읽어** `needed_size`와 비교한다. 삭제된 페이지(`ER_PB_BAD_PAGEID`)는 조용히 폐기한다.
- **(d) 재작성** — **캐시된 free space는 힌트일 뿐 사실이 아니다.** 이 원칙을 자료구조 계약에 명시하고, 페이지를 실제로 쓰기 직전에는 항상 fix 후 재검증하는 단일 함수를 통과시켜라. `pop()` 시점의 필터는 최적화이지 정확성 장치가 아니다.

#### T12. resident candidate의 L1 freespace가 stale

`09e01d435` update the L1s when those are updated / `570ee2677` integrate the update L1 with L1_find

- **(a) 증상** — candidate 큐에서 꺼낸 페이지가 **이미 이 shard의 L1 슬롯에 들어 있는** 경우가 있다. 이때 L1에 기록된 freespace는 오래된 작은 값이고, 큐의 값이 더 최신(크다). 그런데 L1을 갱신하지 않고 버려서, 실제로는 쓸 수 있는 페이지를 못 찾고 새 페이지를 할당한다.
- **(b) 원인** — vacuum이나 delete가 페이지를 비우면 `heap_add_bestpage`가 candidate 큐에 최신 freespace를 넣는다. 그런데 그 페이지가 이미 L1 resident이면 `allocate_pick_candidates`의 중복 제거 로직이 "이미 있으니 버림"으로 처리했다. **중복 제거와 값 갱신을 혼동한 것이다.**
- **(c) 수정** — `09e01d435`이 resident 후보를 별도 배열로 분리하고 `allocate_update_resident()`로 L1을 CAS 갱신한 뒤(`L2_update`까지 전파) 즉시 `L1_find`로 재시도한다. `570ee2677`이 이 전용 함수를 없애고 `L1_find`에 `bool force_check` 인자를 추가해 통합한다 (`bestspace.cpp:570`, `:585`) — `force_check=true`면 캐시된 freespace 사전 검사를 건너뛰고 무조건 페이지를 fix해 실제 값을 읽는다.
- **(d) 재작성** — **"이미 추적 중인 페이지"에 대한 갱신 경로를 처음부터 설계하라.** candidate 큐의 의미를 "새로 추적할 페이지 목록"이 아니라 "free space가 변한 페이지 알림"으로 정의하면, resident 여부와 무관하게 갱신이 자연스럽게 처리된다. `force_check` 같은 bool 플래그로 사후 봉합하는 것보다 낫다.

### 축 B — 동시성·교착

#### T7. 페이지 래치를 쥔 채 스핀 → 래치 데드락

`304f3b0d0` implement a pgbuf helper for calling functions without fixing pages / `7c862d2bc` uses ordered callback to avoid page latch deadlock

- **(a) 증상** — shard의 `m_allocating` 비트가 잡혀 있을 때 다른 스레드는 `find_from_shards`에서 `yield()` / `sleep_for(10us)`로 스핀했다. 이 스레드가 **다른 힙 페이지 래치를 이미 보유한 상태**일 수 있고, 할당 중인 스레드가 바로 그 페이지를 필요로 하면 서로 영원히 기다린다.
- **(b) 원인** — CUBRID는 힙 페이지 래치 순서를 `pgbuf_ordered_fix`로 강제해 데드락을 막는다. 그런데 "래치를 쥔 채 임의 시간 대기"는 이 규약 밖의 동작이다. ordered fix 프레임워크는 대기 중인 스레드가 래치를 놓을 것이라고 가정하지 않는다.
- **(c) 수정** — `pgbuf_ordered_callback()` 헬퍼 신설 (`page_buffer.h:290`, 구현 `page_buffer.c:12971`): **보유 중인 ordered 페이지를 전부 일시 해제 → 콜백 실행 → 순서대로 재fix.** 스핀 로직을 `wait_for_shard_allocation()` 콜백으로 추출해 (`bestspace.cpp:56`) 이 헬퍼를 통해 호출한다 (`bestspace.cpp:1510`). 인터럽트 검사도 콜백 안으로 들어갔다.
- **(d) 재작성** — **"래치를 쥔 채 기다리는 코드"를 작성하기 전에 멈춰라.** 대기가 필요하면 (1) 래치를 놓고 재획득하거나 (2) 대기 없이 실패를 반환하고 상위에서 재시도하게 하라. 이 프로젝트에는 `pgbuf_ordered_callback`이 이제 존재하므로 그것을 쓰면 된다. 재fix 후에는 페이지 내용이 바뀌었을 수 있으므로 **콜백 이후 모든 페이지 상태를 재검증**해야 한다는 점도 함께 기억하라.

#### T16. 체크포인트를 탐색 이후에 수행

`0918cdeee` add the bestspace update logic → `a5281197e` add update path

- **(a) 증상** — `heap_update_bestspace()`가 헤더 페이지를 ordered fix하는데, 이 과정에서 **이미 fix된 best page를 unfix했다가 재fix할 수 있다.** 탐색으로 페이지를 찾아 watcher에 물린 뒤에 체크포인트를 돌리면 그 watcher가 무효화된다.
- **(b) 원인** — `0918cdeee`이 기능을 먼저 넣으면서 `bool updatable = false;` 플레이스홀더와 함께 체크포인트를 `bestspace->find()` **뒤에** 배치했다.
- **(c) 수정** — `a5281197e`이 순서를 뒤집어 탐색 **전에** 체크포인트를 돌린다 (`heap_file.c:4600-4610`). 주석이 이유를 명시한다: `/* update may unfix the fixed page (best page) so sync in-memory bestspace with disk first */`.
- **(d) 재작성** — **ordered fix를 쓰는 함수는 "다른 페이지를 unfix할 수 있다"고 가정하라.** 페이지를 잡은 뒤에는 그런 함수를 호출하지 말 것. 체크포인트/유지보수 작업은 항상 리소스 획득 **전에** 배치하라.

#### T17. 캐시된 shard VPID를 신뢰

`7fff8882d` remove useless code

- **(a) 증상** — `bestspace` 객체가 shard 페이지 VPID 목록을 `m_header` 캐시에 들고 있었다. 헤더가 다른 경로(compactdb, heap_reuse)에서 갱신되면 이 캐시가 stale해진다.
- **(b) 원인** — 생성 시점의 값을 복사해 보관하는 흔한 최적화인데, 헤더가 불변이라는 보장이 없다.
- **(c) 수정** — 캐시와 `get_shard_pages()` 접근자를 제거. `heap_update_bestspace`가 매번 갓 fix한 헤더에서 VPID를 다시 읽는다. 생성자와 `bestspace_registry::create()`에서 `shard_pages` 인자도 제거.
- **(d) 재작성** — **온디스크 메타데이터를 인메모리 객체에 복사해 캐시하지 말라.** 어차피 체크포인트마다 헤더를 fix하므로 그때 읽으면 된다. 캐시할 값과 하지 말 값의 기준은 "누가 언제 바꿀 수 있는가"다.

### 축 C — 통계·주변 서브시스템 오염

#### T10. bestspace 메타데이터 페이지가 통계에 포함

`9553c7d38` exclude bestspace metadata pages from statistics

- **(a) 증상** — 옵티마이저가 보는 테이블 페이지 수가 실제보다 최대 4 크다. 작은 테이블에서 비율 오차가 크고, 히스토그램 샘플러가 사용자 레코드가 없는 페이지를 샘플로 잡는다.
- **(b) 원인** — `file_get_num_user_pages()`는 heap 파일 VFID가 할당한 **모든** 페이지를 센다. shard 페이지도 그 VFID에서 할당됐으므로 포함된다. M3에서 `heap_page_is_bestspace()` 가드를 여러 스캐너에 뿌렸지만 **통계 경로 세 곳이 누락**됐다.
- **(c) 수정** — 새 함수 `heap_get_num_data_pages()` (`heap_file.c:9002`)가 `file_get_num_user_pages()` 결과에서 `heap_hdr->bestspace.num_pages`를 뺀다. 헤더 페이지는 사용자 레코드를 담을 수 있으므로 **남긴다.** 호출부 교체: `statistics_sr.c:274` (`stats_update_statistics_internal`), `file_manager.c:6888,6905` (`file_get_num_total_user_pages`, 파티션 합산 포함). 히스토그램 샘플러 두 곳(`histogram_sampler_sr.cpp:749`, `:1119`)에 `heap_page_is_bestspace` 스킵 추가.
- **(d) 재작성** — **"heap 파일 안에 사용자 레코드가 없는 페이지를 넣는다"는 결정을 내리는 순간, `hfid.vfid`로 페이지를 세는 모든 코드가 잠재적 버그다.** 설계 시점에 `grep -rn "file_get_num_user_pages\|heap_vpid_next\|spage_next_record"`로 전수 목록을 만들고 체크리스트로 관리하라. 대안으로 **shard 페이지를 별도 VFID에 두는 설계**를 먼저 검토할 가치가 있다 — 그러면 이 함정 부류 전체가 사라진다.

#### T11. TDE 미로드 상태에서 vacuum job 실행

`6b6111fe9` don't execute the vacuum jobs if the tde is not loaded

- **(a) 증상** — TDE(투명 데이터 암호화) 키가 로드되지 않은 상태로 서버가 뜨면, vacuum 마스터가 TDE 암호화 로그 페이지를 참조하는 블록에 대해 job을 뿌리고 복호화 실패로 죽는다. bestspace가 vacuum 경로에 `heap_add_bestpage`를 새로 걸면서 이 경로가 더 자주 밟히게 됐다.
- **(b) 원인** — vacuum 마스터가 키 가용성을 확인하지 않았다. 추가로 `tde_initialize()`가 `ER_BO_VOLUME_EXISTS`(초기화된 볼륨 재사용 시 정상 상황)를 에러로 남겨두고 있었다.
- **(c) 수정** — `vacuum_master_task::execute()` 앞머리에 `if (!tde_is_loaded ())` 가드를 넣어 커서를 unload하고 즉시 반환한다 (`vacuum.c:3036-3046`). **백로그는 보존되므로 키와 함께 재시작하면 처리된다.** `tde.c:149-152`에서 `ER_BO_VOLUME_EXISTS`를 `er_clear()`로 정리하고 `NO_ERROR`로 되돌린다.
- **(d) 재작성** — 엄밀히는 bestspace 버그가 아니라 **bestspace가 드러낸 기존 결함**이다. 교훈은 이것이다: **기존 백그라운드 작업(vacuum) 경로에 새 훅을 추가하면, 그 경로가 평소보다 훨씬 자주 실행되면서 잠복 버그가 드러난다.** 훅을 추가하기 전에 해당 작업의 전제 조건(키 로드, 부트 단계 등)을 확인하라.

#### T14. compactdb가 CS 모드일 때 인메모리 bestspace 미갱신

`0f6e9aef0` update in-memory bestspace when compactdb works as CS MODE

- **(a) 증상** — `compactdb`(`xheap_reclaim_addresses`)가 SA 모드에서는 문제없지만, **CS 모드에서는 서버가 살아 있고 인메모리 bestspace가 상주 중**이다. compactdb가 디스크만 갱신하면 인메모리 객체가 이미 없어진 페이지를 가리킨 채 남는다.
- **(b) 원인** — compactdb를 SA 전용 유틸리티로 가정하고 디스크 갱신만 구현했다.
- **(c) 수정** — compactdb 종료부에서 `heap_find_bestspace(thread_p, NULL, hfid, NULL)`로 **상주 여부를 조회만** 하고(NULL 포인터 = 재구축 금지, T15 참고), 상주하면 `reset()` + `set_estimates()` + `push_candidates()`로 인메모리를 새 스냅샷으로 덮는다 (`heap_file.c:5867-5895`). `initialize_by_entries`가 `reset`으로 개명되고 candidate 큐에도 `reset()`이 추가된다 — **재초기화이지 최초 초기화가 아님**을 이름으로 드러낸 것이다. 부수적으로 `bestspace_shard_count`에서 `PRM_USER_CHANGE`를 제거해 런타임 변경을 막고, root class는 shard 1개로 고정한다. `set_estimates`의 store/subtract 순서도 뒤집어 **추정치가 실제보다 낮아지지 않게** 한다 (주석: "It's better for the estimates to be higher than the actual values rather than lower").
- **(d) 재작성** — **"인메모리 캐시 + 온디스크 원본" 구조를 만들면, 디스크를 직접 고치는 모든 유틸리티가 캐시 무효화 지점이다.** compactdb, loaddb, unloaddb, 복구 경로를 처음부터 목록화하라. 그리고 **SA 모드 전용이라고 가정하지 말 것** — CUBRID 유틸리티 상당수가 두 모드를 모두 지원한다.

#### T6. supplemental log의 redo LSA를 에러 검사 전에 기록

`c82351d2e` change supplemental redo LSA log point

- **(a) 증상** — `heap_insert_newhome()`이 실패했는데도 `context->supp_redo_lsa`에 `tdes->tail_lsa`를 복사한 뒤 `goto exit`한다. 실패한 연산의 LSA가 supplemental(CDC) 로그에 실려 잘못된 변경 이벤트를 만든다.
- **(b) 원인** — LSA 복사 코드가 반환값 검사보다 **위에** 있었다. 두 곳: `heap_update_relocation()`, `heap_update_home()`.
- **(c) 수정** — 두 곳 모두 LSA 복사를 `if (rc != NO_ERROR) goto exit;` **아래로** 이동.
- **(d) 재작성** — bestspace 고유 문제는 아니지만 이 PR이 relocation 경로를 건드리면서 드러났다. 원칙: **부수효과 기록은 성공 확인 이후에.** 특히 LSA/시퀀스/카운터처럼 외부로 관측되는 값은 더욱.

### 축 D — 생명주기·운영

#### T8. 서버 종료 시 인메모리 bestspace 유실

`e7d28622e` sync in-memory bestspace with heap pages when the server is terminated

- **(a) 증상** — 정상 종료해도 30초 체크포인트 사이에 쌓인 최신 bestspace 정보가 전부 사라진다. 재시작 후 shard 페이지에서 오래된 스냅샷을 읽어 재구축하므로, 워밍업 동안 페이지 사용률이 나쁘고 불필요한 신규 할당이 일어난다.
- **(b) 원인** — 영속화가 **30초 주기 체크포인트에만** 의존했고 종료 훅이 없었다.
- **(c) 수정** — 레지스트리에 `for_each(callback, args)` 순회 API를 추가하고 (`bestspace.hpp:456-457`, 구현 `bestspace.cpp:1467+`), heap 쪽에 `heap_update_all_bestspaces()` (`heap_file.c:4295`)를 만들어 `xboot_shutdown_server()`에서 호출한다 (`boot_sr.c:3085`). 위치가 중요하다 — **로그·버퍼 매니저가 finalize되기 전**이어야 한다. 주석: `/* persist the latest heap bestspace hints before the log and buffer managers are finalized. */`. candidate 큐에도 `to_entries()`를 추가해 함께 저장한다 (내림차순으로 뒤집어서). `for_each`는 콜백 하나가 실패해도 순회를 계속하되 첫 에러를 보존하기 위해 `er_stack_push/pop`을 쓴다.
- **(d) 재작성** — **주기적 체크포인트를 설계하는 순간 종료 훅도 함께 설계하라.** 그리고 종료 훅의 **위치**를 명시적으로 결정하라 — CUBRID의 `xboot_shutdown_server`는 순서에 민감하며, 페이지를 쓰려면 버퍼/로그 매니저가 살아 있어야 한다. 비정상 종료(crash)는 이 훅으로 커버되지 않으므로, 재구축 경로가 항상 정확해야 한다는 점도 잊지 말 것.

#### T15. `heap_add_bestpage`에서 불필요한 재구축

`690ecc8b7` do not rebuild in-memory bestspace when not existing

- **(a) 증상** — vacuum이나 물리적 delete가 페이지를 비울 때마다 `heap_add_bestpage`가 호출되는데, 인메모리 bestspace가 없으면 **전체 재구축**(헤더 fix + shard 페이지 전부 읽기 + `bestspaces.create`)을 유발한다. 아무도 삽입하지 않는 heap에 대해서까지 그렇다. 게다가 모든 물리적 delete마다 `heap_get_class_oid_from_page()` 읽기가 추가된다.
- **(b) 원인** — `heap_add_bestpage`가 `heap_find_bestspace`에 실제 `class_oid`를 넘겼고, `heap_find_bestspace`는 유효한 `class_oid`를 받으면 재구축하는 계약이었다.
- **(c) 수정** — `class_oid`를 `NULL` **포인터**로 넘긴다 (7라인 삭제). `heap_find_bestspace`의 계약이 명시하듯 (`heap_file.c:4521-4526`) NULL 포인터는 조회 전용이다. 재구축은 이제 수요 경로(`heap_find_bestpage`)와 명시적 통계 경로에서만 일어난다.
- **(d) 재작성** — **힌트 제공 경로와 수요 경로를 API 레벨에서 분리하라.** "best-effort 힌트"는 대상이 없으면 조용히 버려야 하고, 절대 무거운 초기화를 유발해서는 안 된다. `NULL` 포인터 vs `NULL` OID 값의 의미 차이로 구분하는 현재 방식은 동작하지만 **읽는 사람을 속이기 쉽다** — 별도 함수나 enum 인자가 낫다.

#### T18. candidate 고갈에 대한 폴백 부재

`25c037528` add fallback path to refill the candidates

- **(a) 증상** — candidate 큐가 비면 항상 신규 페이지 할당으로 떨어진다. 실제로는 재사용 가능한 페이지가 heap에 많이 있어도 그렇다. 파일이 계속 자란다.
- **(b) 원인** — candidate는 delete/vacuum 이벤트로만 채워진다. 서버 재시작 직후나 이벤트가 드문 워크로드에서는 큐가 비어 있다.
- **(c) 수정** — `heap_update_statistics()`의 전수 스캔에 `heap_add_bestpage()` 호출을 끼워 넣어 (`heap_file.c:8959`) 스캔하는 김에 candidate를 재충전한다. `heap_get_num_objects`는 **먼저 bestspace를 만든 뒤** `heap_update_statistics`를 부르도록 순서를 바꿨다 — 그러지 않으면 스캔 중의 `heap_add_bestpage`가 전부 무시된다 (T15와 상호작용).
- **(d) 재작성** — **이벤트 구동 캐시에는 항상 전수 스캔 재충전 경로를 두어라.** 그리고 그 경로가 실제로 효과가 있으려면 캐시 객체가 스캔 **전에** 존재해야 한다는 순서 의존을 명시하라.

### 사소한 항목

`f58efc6d5` fix comments, `0927b26a8` move the prototype — 주석/선언 위치 정리. 함정 아님.

---

## 4. 재작성 시 권장 구현 순서

실제 진행 순서와 권장 순서의 차이를 먼저 요약한다.

| | 실제 (PR #7353) | 권장 |
|---|---|---|
| 레거시 제거 시점 | 전체의 60% 지점 (`dd6561c31`부터) | **1단계** — 신규 코드 작성 전 |
| 온디스크 포맷 확정 | 3회 변경 (`3cdcfa482` → `6e3428c58` → `b66bf7073`) | **2단계에서 1회 확정** |
| 유닛 테스트 | 도입(`eabbf4bcf`) 후 삭제(`cc40a2a13`), 미복구 | **3단계 내내 유지** |
| 주변 서브시스템 스윕 | 발견될 때마다 산발적 (M3, T10, T14) | **7단계에서 체계적 전수** |

### R0 — 계약 동결 (신규 코드 0줄)

먼저 **바꾸지 않을 것들을 확정한다.**

1. **온디스크 레이아웃 최종안 작성.** `HEAP_HDR_STATS`, `HEAP_CHAIN` 플래그 비트, shard 페이지 슬롯 구성, candidate 배열 위치와 크기. 이 문서를 리뷰받고 나서 코드를 쓴다.
2. **`sizeof(HEAP_HDR_STATS)` 의존 지점 전수 조사.** 함정 T3의 근원. `heap_Maxslotted_reclength` 외에 무엇이 있는지 먼저 안다.
3. **recovery index 번호 예약** (`RVHF_UPDATE_BESTSPACE_ENTRIES`) 과 HA 화이트리스트 비침투 확인 (`log_manager.c`, `log_applier.c`).
4. **시스템 파라미터 확정** — `bestspace_shard_count`(범위 포함), 구 `max_bestspace_entries`의 `PRM_OBSOLETED` 처리, 그리고 **체크포인트 주기를 파라미터로 뺄지 결정** (현재는 30초 하드코딩).
5. **shard 페이지를 별도 VFID에 둘지 재검토.** heap VFID 안에 두면 T10 부류(페이지를 세는 모든 코드)가 전부 함정이 된다. 별도 VFID는 파일 관리 비용이 늘지만 오염 반경이 0이다. **이 결정을 R0에서 내려야 한다** — 나중에 바꾸면 전면 재작업이다.

*근거:* 실제 PR에서 온디스크 포맷이 세 번 바뀌었고, 그때마다 파생 상수(T3)와 스캐너 가드(T10)가 깨졌다. 포맷을 먼저 얼리면 이 왕복이 사라진다.

### R1 — 레거시 격리 (제거는 아직 아님)

구 bestspace(`heap_Bestspace` 전역 캐시, second-best 링, `heap_stats_*` 함수군)를 **하나의 인터페이스 뒤로 밀어 넣는다.** 신규 코드는 이 인터페이스만 교체하면 되도록.

동시에 **제거 대상 목록을 미리 확정**한다: PSTAT 카운터 8개, SHOW 컬럼 14개, `SPAGE_HEADER::need_update_best_hint` 비트, `RESERVED_P_UPDATE_BEST` 파서 예약어, `HEAP_PAGE_INFO_UPDATE_BEST`. 목록만 만들고 삭제는 R6에서.

*근거:* 실제 PR은 레거시를 60% 지점에서 걷어냈고, 그전까지 신/구가 공존하며 `heap_stats_find_best_page`가 폴백으로 남아 있었다(`class_oid->pageid == 193` 같은 하드코딩 예외까지 있었다). 인터페이스로 먼저 감싸면 폴백이 명시적이 되고 제거 시점이 자유로워진다.

### R2 — 인메모리 자료구조 + 유닛 테스트

L1/L2/L3 계층, shard, 레지스트리, candidate 큐. **레이아웃 상수(`L3_FANOUT=8`, `ALLOC_BATCH_SIZE=4`, tier 임계값, allocating 비트 분리)를 처음부터 최종값으로 둔다** — 실제 PR은 `a8482a6e6`에서 fanout을 7→8로 바꾸며 테스트 964라인을 재작성했다.

**이 단계의 유닛 테스트를 끝까지 유지한다.** `unit_tests/bestspace/`는 `eabbf4bcf`에서 655라인으로 도입됐다가 `cc40a2a13`에서 통째로 삭제됐고 복구되지 않았다. 순수 인메모리 자료구조는 CUBRID에서 드물게 **단위 테스트하기 쉬운 코드**이므로 버리기 아깝다.

명시할 계약 두 가지:
- **"요약 계층(L2/L3)은 후보를 좁히기만 하고, 정확성은 L1이 페이지를 fix해 보장한다"** (→ T9 예방)
- **"엔트리에 기록된 free space는 힌트이며 사실이 아니다"** (→ T13 예방)

API 시그니처는 처음부터 `is_newrec`(또는 enum `find_purpose`), `needed_size`/`consume_size` 분리, `record_length`(통계용, 슬롯 오버헤드 제외)를 갖춘다 (→ T4, T5 예방).

### R3 — heap 연결

heap 파일 생성 훅, 삽입 경로 전환, victim/candidate/신규할당 3단 폴백. candidate 큐의 의미를 **"free space가 변한 페이지 알림"**으로 정의하면 resident 갱신(T12)이 특수 케이스가 아니라 기본 동작이 된다.

`heap_add_bestpage`류 **힌트 경로와 `heap_find_bestpage`류 수요 경로를 별도 함수로 분리**한다 (→ T15 예방). 힌트 경로는 대상 부재 시 무조건 no-op.

### R4 — 온디스크 영속화

R0에서 확정한 레이아웃대로 구현. 처음부터 `pgbuf_ordered_fix`만 사용한다 (→ T7 기반). 재구축 경로와 그 double-check 락킹을 함께 만든다.

**`heap_page_is_bestspace()` 가드를 여기서 전수 삽입한다.** R0의 조사 목록을 체크리스트로 소진하고, 새 스캐너가 추가될 때 걸리도록 어서션이나 정적 검사를 고민하라.

### R5 — 통계·체크포인트·종료 훅

estimates의 shard별 atomic 분산, 30초(또는 파라미터) 체크포인트, **그리고 같은 단계에서 종료 훅** (`xboot_shutdown_server`, 로그/버퍼 매니저 finalize 이전) (→ T8 예방). 체크포인트는 항상 페이지 획득 **전에** 배치 (→ T16 예방).

*근거:* 실제 PR은 체크포인트(`a5281197e`)와 종료 훅(`e7d28622e`)이 8커밋 떨어져 있었다. 둘은 같은 요구사항("인메모리 상태를 잃지 않는다")의 두 면이므로 함께 설계해야 누락이 없다.

### R6 — 레거시 제거

R1에서 만든 목록을 소진한다. 폴백 인터페이스를 걷어내고 레지스트리 키를 HFID 단독으로 확정한다. 이 시점에는 신규 구현이 완전하므로 삭제가 안전하다.

### R7 — 주변 서브시스템 체계적 스윕

R0에서 "shard 페이지를 heap VFID 안에 둔다"고 결정했다면, **이 단계가 필수이며 가장 지루하다.** 전수 대상:

| 영역 | 확인 항목 |
|---|---|
| 통계 | `stats_update_statistics_internal`, `file_get_num_total_user_pages`, 히스토그램 샘플러 2곳 (→ T10) |
| 유틸리티 | compactdb (SA/**CS 양쪽**, → T14), loaddb, unloaddb, checkdb |
| DDL | `ALTER ... REORGANIZE PARTITION` (`redistribute_partition_data`), TRUNCATE, 인덱스 빌드 |
| 백그라운드 | vacuum (전제 조건 확인 포함, → T11), 병렬 스캔(`px_scan`), external sort |
| 복구/HA | recovery index 화이트리스트, 로그 어플라이어 |

그리고 마지막으로 **supplemental/CDC 로그 경로**를 훑어 LSA 기록이 성공 확인 이후인지 검증한다 (→ T6).

*근거:* 실제 PR에서 이 스윕이 산발적으로 일어났다 — `c69fcd8e2`(M3)에서 파티션 재구성, `9553c7d38`(끝에서 3번째)에서 통계, `0f6e9aef0`에서 compactdb CS 모드. 마지막 세 커밋 중 둘이 이 부류라는 것은 **스윕이 체계적이지 않았다는 신호**다. 체크리스트로 관리하면 한 번에 끝난다.

---

## 5. 한 문단 요약

이 기능을 다시 만든다면 순서는 **계약 동결 → 레거시 격리 → 인메모리(테스트 유지) → heap 연결 → 영속화 → 통계·체크포인트·종료 → 레거시 제거 → 주변 스윕** 이다. 실제 PR과의 결정적 차이는 세 가지다. 첫째, **온디스크 포맷과 "shard 페이지를 어느 VFID에 둘 것인가"를 코드 작성 전에 확정**한다 — 함정 T3와 T10 전체가 여기서 사라진다. 둘째, **레거시 제거를 뒤가 아니라 앞으로 당겨** 신/구 공존 기간을 없앤다. 셋째, **유닛 테스트를 버리지 않는다** — L1/L2/L3 계층은 CUBRID에서 드물게 순수 단위 테스트가 가능한 코드다. 후반 수정 18건 중 상당수(T3, T5, T9, T10, T12, T13, T15)는 자료구조의 계약("요약 계층은 후보만 좁힌다", "기록된 free space는 힌트다", "힌트 경로는 무거운 초기화를 유발하지 않는다")을 처음부터 문서화했다면 애초에 코드로 쓰이지 않았을 것들이다.
