# CBRD-26176 Redesign bestspace — 재작성 스펙 (Rewrite Spec)

| 항목 | 값 |
|---|---|
| 대상 기능 | CUBRID heap free-space 관리(bestspace) 전면 재설계 |
| 원본 PR | [CUBRID/cubrid#7353](https://github.com/CUBRID/CUBRID/pull/7353) `[CBRD-26176] Redesign bestspace` |
| 기준 머지 커밋 | `e84a7f6dcd175e6ce85ceddb9a16036170cbe405` (2026-07-22, squash merge, parent `b63fbc5dc`) |
| 검증 기준 워킹 리비전 | `f30f1c260` (`[APIS-1087] Update cubrid-jdbc submodule (#7501)`) — 현재 `develop` HEAD |
| 작성일 | 2026-07-28 |
| 작성 주체 | claude-fable-5 |
| 문서 성격 | **종합 스펙.** 01~04 문서 + JIRA(CBRD-26176 / 26858 / 27120) + 코드리뷰 리포트(PR-7353-report-codex)를 하나로 합치고, 코드로 재검증한 결과를 반영했다. |

## 0. 이 문서를 읽는 법

### 0.1 목표

**이 문서 하나만 읽고, 원본 PR을 보지 않은 CUBRID 엔진 개발자가 동일 기능을 처음부터 구현할 수 있어야 한다.** 단, 원본을 그대로 복제하는 것이 목적이 아니다. §7에 정리한 **알려진 결함 9건은 설계 단계에서 예방**한 상태로 만드는 것이 목표다.

### 0.2 인용 규칙

| 표기 | 의미 |
|---|---|
| `01 §3.5` | 같은 디렉터리의 `01-asis-legacy-bestspace.md` 3.5절 |
| `02 §2.8` | `02-tobe-architecture.md` |
| `03 §6.2` | `03-callflows.md` (실측 트레이스 기반) |
| `04 T9` | `04-commit-story.md`의 함정 T9 |
| `리뷰 F2` | `PR-7353-report-codex.md`의 Finding 2 |
| `file:line@f30f1c260` | **본 문서 작성 중 직접 열어 확인한 코드.** 현재 develop HEAD 기준 |
| `file:line@e84a7f6dc` | 02 문서에서 가져온 인용. 머지 커밋 기준 (heap_file.c는 이후 4개 커밋으로 라인이 밀렸으므로 f30f1c260과 다를 수 있다) |
| `file:line@e84a7f6dc^` | 변경 **전**(legacy) 기준. 01 문서 인용 |
| **[추정]** | 코드/문서에 근거가 없고 저자가 추론한 부분 |

`e84a7f6dc`와 `f30f1c260` 사이에 `src/storage/heap_file.c`가 4개 커밋(`741734a8f`, `58145583a`, `5119004c2`, `dbcfe381c`)으로 +237/−151 변경되었다. `bestspace.cpp` / `bestspace.hpp`는 **한 줄도 바뀌지 않았다**(`git diff --stat e84a7f6dc..f30f1c260` 확인). 따라서 bestspace 파일의 라인 번호는 두 리비전에서 동일하다.

### 0.3 개별 커밋을 참조하는 방법

**`e84a7f6dc`는 parent가 하나뿐인 squash merge 커밋이다** (`git log -1 --format=%P e84a7f6dc` → `b63fbc5dc` 단일, 직접 확인). 따라서 **`e84a7f6dc^2`는 존재하지 않으며, PR의 57개 개별 커밋은 `develop` 히스토리에 남아 있지 않다.** 본 문서와 `04` 문서가 인용하는 커밋 해시(`a8482a6e6`, `0ba2a3603`, `026e78a87` 등)를 조회하려면 PR head를 별도로 fetch해야 한다.

```
git fetch origin pull/7353/head:refs/remotes/pr/7353
git log cd2d4718b^..cc6bd0d6e        # 57개 커밋 (base^..tip)
```

이 로컬 저장소에는 **이미 `refs/remotes/pr/7353`가 존재한다** (`cc6bd0d6e3cb6b2f0d662da36c8049f0a2ad17fa`, 직접 확인). 리뷰 리포트의 HEAD SHA와 동일하다.

---

## 1. 요구사항과 Acceptance

### 1.1 원문 요구사항 (CBRD-26176)

> **Description** — best space를 찾기 위해 대부분의 처리 내내 header page에 대해 WRITE latch를 걸고 있다. 이 구조는 한 번에 하나의 스레드만 insert할 수 있게 하는 병목 지점이 된다. 위 병목을 해결하기 위해 CBRD-26858에서 수행한 설계를 기반으로 작업을 처리한다.
>
> **Implementation** — shard와 lock-free 구조를 도입하여 insert-heavy에서의 병목 해소를 확인한다.
>
> **Acceptance Criteria** — INSERT-heavy에서의 부하 분산과 성능 증가를 확인

(출처: `CBRD-26176` Description, Components=SM, Target=guava, parent=CBRD-26857)

### 1.2 병목의 정량적 정의 (AS-IS)

재작성 전에 "무엇을 없애야 하는가"를 코드 수준으로 못박아 둔다.

| 층 | 경합 대상 | 범위 | 근거 |
|---|---|---|---|
| L1 | heap header page **WRITE latch** | heap 파일당 1개. 모든 INSERT 필수 통과 | `heap_file.c:3568@e84a7f6dc^` (획득) ~ `:3701` (해제), `01 §4.2` |
| L2 | `heap_Bestspace->bestspace_mutex` | **서버 프로세스 전역 1개.** L1 아래에서 중첩 획득 | `heap_file.c:3323@e84a7f6dc^`, `01 §7.1` |
| L3 | 후보 데이터 페이지 X latch (zero-wait) | 실패해도 진행하나 convoy 유발 | `heap_file.c:3391@e84a7f6dc^`, `01 §3.5(c)` |

헤더 WRITE latch 보유 구간의 상한은 **"해시 탐색 2회(각 최대 100 엔트리) + heap 순차 스캔 최대 3회 × 최대 100페이지(디스크 I/O 포함) + `file_alloc` + WAL sysop 커밋"** 이다 (`01 §4.2` 표, `§5.3`). 대기 큐의 N번째 스레드는 앞선 N−1개의 최악 케이스를 누적 대기한다.

### 1.3 헤더 latch 제거 범위 — CBRD-26858 Joon Min 분석

이 요구사항이 **"bestspace만 옮기면 안 된다"** 는 결정을 낳았다. CBRD-26858 코멘트(Joon Min, 2026-06-02) 전문 요지:

> 이번 이슈는 bestspace 중심으로 리포팅되었으나, heap 헤더(`HEAP_HDR_STATS`)에는 bestspace 외에도 **insert/페이지할당 시마다 갱신되는 통계 필드**(`num_recs`, `recs_sumlen`, `last_vpid`, `num_pages`)가 함께 들어 있습니다. (…) 따라서 **bestspace 관련 정보만 헤더 밖으로 옮겨도** 이 함수는 여전히 `num_recs`/`recs_sumlen`를 쓰기 위해 헤더 X-latch를 잡아야 하므로, (…) 헤더 latch에 줄 서는 문제는 **그대로 남을 가능성이 높습니다.**
>
> 2. 목표를 "헤더 fix를 WRITE→READ로 강등(또는 제거)"로 잡으면, 어떤 필드를 옮겨야 하는지 명확해집니다. 현재 `heap_stats_find_best_page`가 WRITE를 잡는 이유는 (i) bestspace 갱신 (ii) num_recs/recs_sumlen 갱신 두 가지이며, **둘 다 제거**해야 READ 강등이 가능합니다.

레거시 코드가 이 분석을 뒷받침한다 — best 페이지를 **즉시 적중해도** 헤더는 WRITE로 잡혀야 했다. `estimates.num_recs += 1`과 `recs_sumlen += needed_space` 두 줄이 read-only fast path를 원천 차단했기 때문이다 (`heap_file.c:3592-3594@e84a7f6dc^`, `01 §7.3(2)`). 게다가 이 두 값은 **어차피 로깅되지 않는 추정치**다.

**따라서 재작성의 이관 범위는 다음 4종을 모두 포함한다.**

1. bestspace 후보 목록 (`estimates.best[10]`, `second_best[10]` 및 부속 인덱스)
2. `num_recs`, `recs_sumlen` (INSERT마다 갱신)
3. `num_pages` (페이지 할당/해제마다 갱신)
4. `last_vpid` (페이지 할당/해제마다 갱신, **유일하게 정확해야 하는 값**)

원본 PR의 처리 결과: 1은 shard 페이지로 이동, 2·3은 shard별 `std::atomic`으로 분산, 4는 `estimates` 중첩에서 `HEAP_HDR_STATS` 최상위로 승격 (`02 §4.5`, 구 코드의 `todo: move out of estimates` 주석 `heap_file.c:223@e84a7f6dc^`을 해소).

### 1.4 Acceptance — 실측 수치

**모두 CBRD-26176 코멘트에서 인용한 실측치다. 재작성 결과는 최소한 이 수준을 재현해야 한다.**

| 워크로드 | AS-IS | TO-BE | 증가율 | 출처 |
|---|---|---|---|---|
| **TPC-C** (BenchmarkSQL 5.0, TF 내부환경, CBRD-26664 병합 상태) tpmC | 54,753.92 | 59,385.19 | **+8.46%** | youngjinj, 2026-07-24 |
| 동 tpmTOTAL | 121,629.04 | 131,996.6 | **+8.52%** | 동일 |
| **YCSB** INSERT 100% | — | — | **약 +80%** | hong yechan, 2026-07-24 |
| **INSERT .. SELECT ..** | — | — | **약 3배** | 동일 |

> 측정자 주석(youngjinj): "BenchmarkSQL 5.0 기반 TPC-C 테스트가 온전하지 않아서 측정 결과가 달라질 여지는 있습니다. 개선 방향성은 변하지 않을 것 같고, 절대 수치만 조금 달라질 수 있습니다. (…) QAHome Performance 탭의 테스트 내용과는 차이가 있습니다. TF 내부 환경에서 테스트한 것으로 FK 생성 조건도 차이가 있습니다."

> **주의 — 초기 오측정.** 같은 담당자가 처음 보고한 "tpmC 54,754 → 2,110, 수많은 abort" 결과는 **성능 회귀가 아니라 구 DB 이미지 호환성 사고**였다 (`d213d0d` 커밋 시점에 만든 DB를 26176 병합 빌드로 열었다). DB 재생성 후 위 수치로 정상화됐다. 이 사고는 §7 D1의 실증 사례다.

### 1.5 부하 분산 Acceptance — 원본이 충족하지 못한 항목

Acceptance Criteria의 "부하 분산"은 **원본 PR에서 검증되지 않았고, 실측 결과 충족되지 않았다.**

- 4,008건의 `find/FOUND` 중 **4,001건이 shard 0**, shard1=6, shard2=1 (`03 §6.2`, 8 커넥션 × 500 INSERT).
- 원인: `bestspace::find`가 `shard = 0; bias = 0;`으로 고정 (`bestspace.cpp:1360-1361@f30f1c260`, 직접 확인).
- 리뷰 F2가 동일 지적: "JIRA의 shard 기반 load distribution acceptance를 충족한다고 보기 어렵다."

**재작성의 Acceptance는 다음을 추가한다.**

> **A5.** N개 worker 스레드가 동일 heap에 INSERT할 때, shard별 `request` / `found` / `allocated` 카운터가 균등 분포해야 한다. 판정 기준: shard 수 S ≥ 2이고 동시 스레드 수 T ≥ S일 때, 최다 shard의 `found` 비율이 `2/S` 이하.

---

## 2. 설계 결정 대장 (Design Decision Ledger)

각 결정은 `[결정 | 근거 | 기각된 대안 | 출처]` 형식이다. **재작성 시 결정을 바꾸려면 "기각된 대안" 칸에 적힌 이유가 여전히 유효한지 먼저 확인하라.**

### D-01. 헤더 latch 제거 범위 = bestspace + estimates(num_recs/recs_sumlen/num_pages) + last_vpid

| | |
|---|---|
| **결정** | 삽입 핫패스에서 heap header page fix를 **완전히 제거**한다. 헤더는 (a) lazy build, (b) 30초 주기 sync, (c) shutdown sync, (d) 새 페이지 할당 시에만 잡는다. 이를 위해 bestspace 힌트뿐 아니라 `num_recs`/`recs_sumlen`/`num_pages`/`last_vpid`를 전부 헤더 밖으로 옮긴다. |
| **근거** | CBRD-26858 Joon Min 분석 — "`heap_stats_find_best_page`가 WRITE를 잡는 이유는 (i) bestspace 갱신 (ii) num_recs/recs_sumlen 갱신 두 가지이며, **둘 다 제거**해야 READ 강등이 가능합니다." 실제로 레거시는 bestspace 완전 적중 시에도 `heap_file.c:3592-3594@e84a7f6dc^` 때문에 WRITE가 강제됐다. |
| **기각된 대안** | ① **bestspace만 이관** → 헤더 X-latch가 그대로 남아 병목 미해소 (CBRD-26858 §2 결론). ② **헤더 fix를 WRITE→READ 강등** → estimates가 헤더에 남는 한 불가. ③ **estimates를 CONDITIONAL latch로 best-effort 갱신** → 레거시 `heap_stats_update_internal`이 이미 그렇게 하는데, INSERT 부하가 높을수록 DELETE 회수분이 반영되지 않는 것으로 판명 (`heap_file.c:3040-3049@e84a7f6dc^`, `01 §6.3`). |
| **출처** | `CBRD-26858` 코멘트(Joon Min, 2026-06-02) §2·§5; `01 §7.3(2)`; `02 §4.5`; `03 §0` |

### D-02. shard 구조 채택 (Oracle ASSM / PostgreSQL FSM 대비)

| | |
|---|---|
| **결정** | HFID당 in-memory 객체 하나를 두고, 그 안을 N개 shard(기본 8, 1~28)로 나눈다. shard는 서로 독립적인 원자 색인이며, 스레드는 자기 shard부터 탐색하고 막히면 다음 shard로 전진한다. |
| **근거** | CBRD-26858의 조사 범위가 "Oracle: freelist / ASSM, PostgreSQL: FSM, 공통 관점: 동시성 처리, 경합 회피 방식, 정확성과 공간 활용률의 트레이드오프"였다. shard는 **Oracle의 다중 freelist(free list group) 개념을 in-memory로 가져오되, PostgreSQL FSM의 tier 양자화 색인을 결합**한 형태다. |
| **기각된 대안** | ① **PostgreSQL FSM 그대로** — 별도 fork 파일에 페이지당 1바이트 양자화 값을 두는 트리. 정확도는 좋으나 갱신이 **페이지 쓰기**라서 CUBRID의 "힌트는 로깅하지 않는다" 전제와 충돌하고, INSERT마다 FSM 페이지를 잡으면 경합 지점이 옮겨갈 뿐이다. ② **Oracle ASSM 비트맵 블록 그대로** — 세그먼트 내부에 L1/L2/L3 비트맵 **블록**을 두는 구조. 온디스크 비트맵을 매 INSERT마다 갱신해야 하므로 동일 문제. **원본 PR은 ASSM의 3단 계층 이름(L1/L2/L3)만 차용하고 실제 자료구조는 in-memory 원자 워드로 대체했다.** ③ **HFID 단위 단일 색인(shard 없음)** — 64슬롯 하나면 동시 스레드가 같은 슬롯에 몰려 page latch convoy가 재현된다. |
| **출처** | `CBRD-26858` Description §3(조사 범위)·§6(완료 기준); `02 §0.3`, `§2.8`; `bestspace.hpp:81@f30f1c260` |

> **[추정]** CBRD-26858의 조사 산출물 문서 자체는 JIRA 본문에 첨부되지 않았다. 위 "기각된 대안"은 조사 범위 항목과 최종 코드 형태의 차이에서 역산한 것이다.

### D-03. L1/L2/L3 3계층 tier 비트맵

| | |
|---|---|
| **결정** | shard 하나가 64개 페이지 슬롯을 추적한다. `L1`(8바이트: freespace + VPID) 64개를 8개씩 묶어 `L2` 8개, 그 8개를 `L3` 1개로 요약한다. L2/L3는 각각 `std::array<bitmap,8>` = 8바이트이며, `m_freespace[t]`의 비트 i가 "하위 i번 항목에 tier t가 존재"를 뜻한다. |
| **근거** | 64개 슬롯 전수 스캔을 **8바이트 원자 load 1회 + 최대 8회**로 줄인다. L2/L3가 정확히 8바이트라 `std::atomic<L2>`가 lock-free이고, tier 8개가 바이트 8개에 1:1 대응해 `clear(index)`가 `val &= ~(0x0101010101010101ULL << index)` 한 줄로 끝난다 (`02 §2.6`). |
| **기각된 대안** | ① **2계층(L1 + 요약 1개)** — 64슬롯을 8바이트로 요약하려면 tier를 버려야 한다. ② **정렬 리스트/힙** — 갱신마다 재정렬이 필요해 lock-free가 불가. ③ **비트 스캔 명령(`__builtin_ctz`) 사용** — 8비트라 분기 예측이 잘 먹어 실익 없음 (`bitmap::find`는 8회 루프, `02 §2.4`). |
| **출처** | `02 §2.4~2.6`; `04 M1`; `bestspace.hpp:78-80@f30f1c260` |

### D-04. `FS0 = -1` 센티널 — "요약 계층은 후보만 좁히고, 정확성은 리프가 보장한다"

| | |
|---|---|
| **결정** | tier를 9단계(`FS0`~`FS8`)로 두되 **`FS0 = -1`은 L2/L3 비트맵에 색인하지 않는다.** 탐색 진입 시 요구 tier가 FS0이면 FS1로 승격하고, **정확한 크기 검사는 `L1_find`가 페이지를 fix한 뒤 `spage_max_space_for_new_record`로 수행**한다. |
| **근거** | 음수라 배열 인덱스가 될 수 없으므로 자연스럽게 배제되고, 그 덕에 8개 tier가 정확히 8바이트에 들어맞는다. "7% 이하만 남은 페이지"는 사실상 사용 불가이므로 색인 대상이 아니다. |
| **기각된 대안** | ① **tier를 한 칸 올려 탐색**(`if (minimum < FS8) minimum++`) — 초기 구현이 이랬다. tier가 범위이므로 "FS3 페이지가 반드시 수용한다"는 보장이 없어 안전하게 올린 것인데, **`L1_find`가 어차피 정확 검사를 두 번 하므로 과잉**이었고 페이지 사용률만 떨어뜨렸다. 커밋 `026e78a87` "find exact size if not FS0"이 되돌렸다 (`04 T9`). ② **tier 없이 실제 크기로 색인** — 8바이트 워드에 담을 수 없다. |
| **출처** | `02 §2.3`, `§2.9`; `04 T9`; `bestspace.cpp:1381@f30f1c260` (임계값 배열) |

### D-05. allocating 비트를 L3에서 분리

| | |
|---|---|
| **결정** | "이 shard에서 누군가 페이지 할당 중"이라는 플래그를 L3 워드가 아닌 **독립 멤버 `atomic_wrapper<bool> m_allocating`** 으로 둔다. shard의 **첫 멤버**이며 64바이트 캐시라인을 독점한다. |
| **근거** | 세 가지를 동시에 얻는다. (1) **fanout 7 → 8**: 플래그를 L3에 넣으려면 8개 tier 바이트 각각의 최상위 비트를 예약(`FLAG_MASK = 0x8080808080808080`)해야 해서 L2 그룹이 7개가 상한이었다. shard당 엔트리 56 → **64개**가 되고 인덱스 산술이 시프트/마스크로 떨어진다. (2) `operator==`가 마스킹 비교에서 8바이트 `memcmp`로 단순화. (3) **경합 분리**: 할당 마킹과 tier 갱신이 같은 워드를 CAS하지 않게 되어, 할당 중인 shard에서도 다른 스레드의 L3 갱신이 실패하지 않는다. |
| **기각된 대안** | **L3 워드에 인라인**(초기 구현) — 위 3가지 손실. 커밋 `a8482a6e6` "split the allocating bit and L3"가 전환점이다. |
| **출처** | `02 §2.8`; `04 M1`(`a8482a6e6`); `bestspace.hpp:78@f30f1c260` |

### D-06. 힌트 소실 허용 — "주기 sync + 힌트는 사실이 아니다"

| | |
|---|---|
| **결정** | bestspace 상태의 영속화는 **30초 주기 sync(HFID 단위)와 shutdown 일괄 sync 두 갈래뿐**이다. checkpoint 훅도, vacuum 주기 훅도, 전용 데몬도 없다. crash 시 최대 30초분의 힌트가 유실되며 이것은 **정합성 문제가 아니다.** |
| **근거** | 레거시가 이미 같은 철학이었다 — "estimates 배열의 값 변경은 로깅하지 않으며, 언제든 부정확할 수 있고, 중복된 페이지가 들어있을 수도 있다" (`heap_file.c:227-230@e84a7f6dc^`). 힌트를 정확히 유지하려면 매 INSERT가 로깅을 유발해 병목을 다시 만든다. 정확성은 "L1을 믿지 않고 fix 후 실측"이 보장한다. |
| **기각된 대안** | ① **전용 백그라운드 데몬** — 스레드 하나가 모든 heap을 순회하면 registry mutex 보유 시간이 길어지고, 실제로 sync가 필요한 시점을 알기 어렵다. ② **매 갱신 로깅** — WAL 부하. ③ **checkpoint 연동** — 체크포인트 주기가 bestspace 수명과 무관. |
| **출처** | `02 §5.3`, `§5.5`; `03 §8.3`; `bestspace.cpp:1312@f30f1c260` |

> **재작성 시 결정 필요.** 30초는 하드코딩 `constexpr`이며 튜닝 파라미터가 없다 (`04 M4 갭`). 노출 여부를 P0에서 결정하라. §7 D5·D6의 개선안이 sync 주기와 상호작용한다.

### D-07. registry 키 = HFID 단독

| | |
|---|---|
| **결정** | 전역 registry의 키는 `HFID` 하나다. `class_oid`는 키가 아니라 **페이지 소유권 검증 용도로만** 쓴다. `destroy`는 `HFID`와 `VFID` 두 오버로드를 갖는다. |
| **근거** | ① **키가 중복이었다** — heap 파일 하나는 정확히 한 클래스에 속하므로 HFID가 정해지면 class_oid는 종속적이다. ② **class_oid를 모르는 호출자가 실재한다** — `vacuum_rv_notify_dropped_file`은 복구 데이터에서 VFID만 얻는다 (`vacuum.c:6424@e84a7f6dc`). `HFID = VFID + hpgid`이므로 VFID만으로 매칭이 가능하다. |
| **기각된 대안** | **`(OID class_oid, HFID hfid)` 복합 키**(초기 구현) — 정보를 더하지 않으면서 호출자에게 부담만 지우고, VFID-only 복구 경로가 성립하지 않는다. 커밋 `0ba2a3603` "uese only hfid as a key"(원문 오타)가 되돌렸다. 부수효과로 `destroy(VFID)`가 단일 제거가 아닌 **드레인 루프**가 된다. |
| **출처** | `02 §3.2`; `04 M5`; `bestspace.hpp:426-432, 451-452@f30f1c260` |

### D-08. thread_local registry 캐시 + generation 무효화

| | |
|---|---|
| **결정** | 전역 registry는 **뮤텍스 하나로 보호되는 단일 연결 리스트**이고(해시맵이 아니다), 그 앞에 **스레드 로컬 LRU 캐시(정원 40)** 를 둔다. 조회는 TLS → 미스 시 전역 뮤텍스 → 결과를 TLS에 설치. `destroy`가 전역 `m_generation`을 1 증가시키면 다른 스레드는 다음 조회 때 세대 불일치를 보고 **자기 TLS 캐시 전체를 버린다.** |
| **근거** | 한 서버가 동시에 여는 heap 수가 많지 않고 TLS가 대부분의 조회를 흡수한다는 가정 **[추정 — 설계 근거 주석 없음]**. generation 방식은 dangling pointer를 원천 차단한다. `m_generation`은 매 조회마다 읽히므로 `alignas(64)`. |
| **기각된 대안** | ① **전역 해시 테이블** — 레거시가 그랬고(`hfid_ht`/`vpid_ht` + 단일 mutex), 그것이 병목의 Layer 2였다 (`01 §7.1`). ② **개별 엔트리 참조 카운팅** — dangling 방지에는 정확하지만 조회마다 원자 증감이 필요. ③ **RCU/hazard pointer** — CUBRID에 기반 인프라가 없다. |
| **한계** | `find_from_global`은 **선형 탐색**이므로 heap 수가 많아지면 mutex 아래 O(n)이 된다. generation 무효화는 heap 하나가 drop되면 **모든 스레드의 모든 캐시**를 날린다(과잉 무효화). |
| **출처** | `02 §3.1`, `§3.3`; `bestspace.hpp:459-466@f30f1c260` (`m_head` 460 / `m_mutex` 461 / `alignas(64) m_generation` 463 / `TLS_MAX_SIZE = 40` 465 / `thread_local registry_cache TLS_cache` 466) |

### D-09. candidate queue — mutex + 정렬 고정 배열, 정원 128, 오름차순

| | |
|---|---|
| **결정** | bestspace 객체당 하나, 모든 shard가 공유. `std::array<bestspace_entry,128>` + `std::mutex`. **free space 오름차순 유지**(`m_array[0]`이 최악, `m_array[m_size-1]`이 최선). pop은 뒤(최선)에서 최대 4개. VPID 중복 제거. 정원이 차면 최악 항목 축출. `try_push`는 `try_to_lock`이고 **실패하면 후보를 그냥 버린다.** |
| **근거** | 정렬 불변식이 모든 연산을 상수 시간 판정으로 만든다 — "최선 후보가 요청을 못 채우면 큐 전체가 못 채운다"를 한 번의 비교로 안다. `try_push`가 포기하는 이유는 **candidate는 힌트일 뿐이므로 vacuum이나 삽입 경로가 이것 때문에 멈춰서는 안 되기 때문**이다. |
| **기각된 대안** | **`tbb::concurrent_queue`**(초기 구현) — 무순서 FIFO라 "가장 여유 큰 후보"를 뽑을 수 없고, 정원 제한과 중복 제거가 불가능하다. 커밋 `65d4465a5`가 교체했다 (`04 M1`). |
| **주의** | in-memory는 **오름차순**, on-disk 배열은 **내림차순**이다. `to_entries`가 역순 복사로 흡수한다 (`02 §2.11`). 이 비대칭을 놓치면 적재 시 순서가 뒤집힌다. |
| **출처** | `02 §2.11`; `04 M1`; `bestspace.hpp:75@f30f1c260` |

### D-10. zero-wait latch — CONTENDED 즉시 포기

| | |
|---|---|
| **결정** | 후보 페이지 fix는 `xlogtb_reset_wait_msecs(LK_FORCE_ZERO_WAIT)` 아래에서 `pgbuf_ordered_fix(OLD_PAGE_MAYBE_DEALLOCATED, PGBUF_LATCH_WRITE)`로 한다. `ER_LK_PAGE_TIMEOUT`이면 `er_clear()` 후 `CONTENDED`를 반환하고 **한순간도 기다리지 않고 다음 후보로 간다.** 함수 종료 시 wait_msecs를 반드시 복원한다. |
| **근거** | 레거시부터 이어진 명시적 트레이드오프다 — "This will improve some contentions on the heap at the expenses of storage" (`heap_file.c:3302-3305@e84a7f6dc^`). `page_buffer.c`가 이 상수를 이름으로 알고 있어 에러를 설정하지 않고 코드만 돌려준다 (`page_buffer.c:12329-12340@e84a7f6dc^`). 실측 555회 CONTENDED에 대해 **대기 0** (`03 §6.2`). |
| **기각된 대안** | ① **대기** — page latch convoy가 곧 병목이므로 목적에 반한다. ② **조건부 latch(`PGBUF_CONDITIONAL_LATCH`)** — ordered fix 프레임워크와 조합이 어렵다. |
| **대가** | 경합을 저장 공간과 맞바꾼다. 여러 스레드가 같은 페이지에서 튕기면 결국 새 페이지를 할당해 heap이 부푼다. **D-02의 shard 분산이 제대로 동작해야 이 대가가 작아진다** — §7 D2가 미해결이면 이 대가가 커진다. |
| **출처** | `01 §4.3`; `02 §2.9`; `03 §4.1`, `§6.2` |

### D-11. 4장 batch 할당 (`ALLOC_BATCH_SIZE = 4`)

| | |
|---|---|
| **결정** | 새 페이지가 필요하면 **항상 4장 단위**로 확보한다. candidate 큐에서 뽑은 개수만큼 차감하고 나머지를 `heap_alloc_new_pages`로 일괄 할당한다. 마지막(4번째) 슬롯의 페이지가 **fix된 채로 호출자에게 반환**되는 것이 규약이다. |
| **근거** | 새 페이지 할당은 헤더 WRITE latch를 필요로 하므로 **latch 왕복을 1/4로 줄인다** (`03 §5`). victim 교체도 같은 배치로 처리해 shard 갱신이 한 번에 끝난다. |
| **기각된 대안** | ① **1장씩** — 헤더 latch 왕복이 4배. ② **더 큰 배치** — 미사용 페이지가 늘어 공간 낭비. |
| **부속 규약** | `candidate_queue::pop`은 **최선 후보가 요청 크기를 만족하면 4개, 아니면 3개만** 꺼낸다. 3개만 꺼내면 `allocate_verify_or_allocate`가 반드시 `allocate_new_pages`를 타게 되어 **최소 한 장의 새 페이지가 확보된다** — 후보가 다 부실할 때 헛돌지 않게 하는 장치다 (`02 §2.11`). `allocate_replace_pages`는 앞 3개를 무조건 교체하고 **마지막 하나만 조건부**로 교체한다(반환 페이지는 이미 `consume_size`만큼 차감되어 victim보다 나쁠 수 있다). |
| **출처** | `02 §2.10~2.11`; `03 §5`; `bestspace.hpp:77@f30f1c260` |

### D-12. on-disk shard 페이지를 heap 파일 내부 체인에 배치

| | |
|---|---|
| **결정** | bestspace 엔트리를 담을 전용 페이지 1~4장을 **같은 `FILE_HEAP` VFID에서** 할당하고, heap 페이지 체인의 **헤더 바로 다음**(2번째~N+1번째)에 끼워 넣는다. 전용 페이지 타입은 없고 `HEAP_CHAIN::flags` 비트 0(`HEAP_PAGE_FLAG_BESTSPACE`)으로만 구별한다. 슬롯 0 = `HEAP_CHAIN`, 슬롯 1 = `bestspace_entry` 평면 배열. |
| **근거** | 별도 파일을 만들지 않으므로 heap 생성/삭제/재사용 경로가 그대로 동작한다. 찾을 때 스캔하지 않고 헤더의 `bestspace.pages[]`로 직접 fix한다. |
| **기각된 대안** | **별도 VFID** — 원본은 이 대안을 **명시적으로 검토한 흔적이 없다.** 재작성 시 정식으로 다시 열어야 하므로 **별도 결정 항목 D-25**로 승격했다. |
| **대가 (매우 큼)** | shard 페이지가 체인에 있으므로 **기존 heap 스캐너 전부가 이를 밟는다.** `heap_page_is_bestspace()` 가드를 `heap_get_num_objects`, `heap_get_capacity`, `heap_next_internal`, `heap_page_next/prev`, `xheap_reclaim_addresses`, `heap_chkreloc_next`, `heap_update_statistics`, `heap_reuse` 등 9곳 이상에 뿌려야 했고, 그러고도 통계 경로 3곳이 뒤늦게 발견됐다(`04 T10`). 페이지 수를 세는 코드도 전부 함정이 되어 `heap_get_num_data_pages`가 신설됐다. |
| **재작성 권고** | **→ D-25에서 정식으로 재결정할 것.** 함정 T3 / T10 / T14가 전부 이 하나의 결정에서 파생되므로, "그대로 간다"를 고르더라도 **판단 근거를 문서로 남겨야 한다.** heap VFID 안에 두기로 결정한다면 §6 P7의 전수 스윕이 **필수**다. |
| **출처** | `02 §4.2~4.3`; `04 M3`, `T10`, `R0-5`; `heap_file.c:220-229@f30f1c260`(플래그 매크로 직접 확인) |

### D-13. shard 페이지 개수를 파라미터 **상한**으로 산정

| | |
|---|---|
| **결정** | shard 페이지 수를 `bestspace_shard_count`의 **현재 값이 아니라 상한(28)** 으로 계산해 heap 생성 시점에 확정한다. `max_entries = 28 × 64 = 1792`. |
| **근거** | 나중에 파라미터를 올려도 **파일 레이아웃을 바꾸지 않아도 된다.** `MAX_SHARD_PAGE_COUNT = 4`는 최소 페이지 크기 4K에서 필요한 값이 정확히 4라서 정해졌다 (`02 §4.3` 표: 4K→4장, 8K→2장, 16K→1장). |
| **기각된 대안** | **현재 값으로 산정** — 파라미터 변경 시 온라인 재배치가 필요. |
| **대가** | 실제 사용량과 무관하게 최대치가 항상 예약된다. 파라미터를 **줄이고** 재기동하면 디스크 shard 수 > 현재 파라미터가 되는데, 남는 엔트리는 버리지 않고 candidate 큐로 흘려보낸다 (`heap_file.c:4477-4479@f30f1c260`). |
| **재구현 함정** | 그 조건식은 `ENTRIES_PER_SHARD`를 쓰는데 본문은 **리터럴 `64`를 두 번** 쓴다 — `bestspace->push_candidates (&entries[num_shards * 64], num_entries - num_shards * 64);` (`heap_file.c:4479@f30f1c260`, 직접 확인). `ENTRIES_PER_SHARD`를 바꾸면 조건과 본문이 어긋나 버퍼 경계를 넘는다. |
| **출처** | `02 §4.3`, `§3.5`; `04 T2` |

### D-14. redo-only 로깅 + 전용 recovery index

| | |
|---|---|
| **결정** | shard 페이지 엔트리 갱신은 신규 `RVHF_UPDATE_BESTSPACE_ENTRIES = 130`으로 **redo만** 로깅한다(undo 함수 없음, redo는 기존 범용 `heap_rv_redo_update` 재사용). 헤더 페이지는 기존 `RVHF_STATS`(redo 로깅), shard 페이지 체인 재작성은 `RVHF_CHAIN`, 생성 시 초기 삽입은 `RVHF_INSERT`가 아니라 **`RVHF_INSERT_NEWHOME`** 을 쓴다. |
| **근거** | **HA 복제 회피가 핵심이다.** CUBRID HA 로그 어플라이어는 heap recovery index **화이트리스트**를 보고 논리적 행 연산을 역산한다. shard 페이지 슬롯 1의 레코드는 객체가 아니라 생 바이트 배열이므로, `RVHF_UPDATE`를 재사용했다면 체크포인트마다 어플라이어가 이를 복제 대상 인스턴스로 해석하려다 `ER_FAILED`로 죽었을 것이다. 화이트리스트에 없는 새 번호를 쓰면 양쪽이 조용히 무시하면서도 redo 복구는 정상 동작한다. `RVHF_INSERT` → `RVHF_INSERT_NEWHOME` 치환도 코드 주석이 같은 이유를 명시한다. |
| **기각된 대안** | ① **`RVHF_UPDATE` 재사용** — 위 사유로 HA 파손. ② **undo/redo 둘 다** — 힌트에 undo는 무의미하고 WAL이 늘어난다. ③ **무로깅** — crash 후 shard 페이지가 찢어진 상태로 남을 수 있다. |
| **출처** | `02 §7`; `04 M3`; `recovery.h:187-189@e84a7f6dc`, `recovery.c:844-849@e84a7f6dc` |

### D-15. root class heap은 shard 1개

| | |
|---|---|
| **결정** | `OID_IS_ROOTOID(class_oid)`이면 shard 수를 **1**로 고정하고, 그 외에는 `PRM_ID_BESTSPACE_SHARD_COUNT`를 쓴다. |
| **근거** | 카탈로그 heap은 INSERT 경합이 적어 shard를 나눌 이유가 없고, shard마다 4,800바이트를 쓰므로 낭비다(8 shard = 38,400바이트). |
| **기각된 대안** | **일괄 파라미터 적용** — 모든 카탈로그 heap이 40KB씩 차지한다. |
| **출처** | `02 §3.5`; `heap_file.c:4446-4452@f30f1c260`(직접 확인) |

### D-16. `bestspace_entry` ≡ `L1` ≡ 디스크 8바이트 — 3중 항등 ABI

| | |
|---|---|
| **결정** | `{uint16_t freespace; short volid; int32_t pageid;}` 8바이트 레이아웃을 in-memory `L1`, 전달용 `bestspace_entry`, on-disk 엔트리 셋이 **완전히 공유**한다. `static_assert`로 크기와 오프셋(0/2/4)을 못 박고, `offsetof` 일치도 검증한다. |
| **근거** | 플러시와 적재가 **`memcpy` 한 번**으로 끝난다. `freespace`가 오프셋 0인 것은 tier 판정이 이 값만 보면 되기 때문이고, 8바이트 전체를 단일 `lock cmpxchg`로 교체할 수 있어야 **free space와 VPID가 찢어지지 않는다** — 이것이 탐색 경로에서 mutex를 없앨 수 있었던 근본 이유다. |
| **기각된 대안** | ① **직렬화 함수 경유** — 매 플러시마다 1,792개를 개별 변환. ② **`int freespace`(레거시 `HEAP_BESTSPACE`는 12바이트)** — 8바이트를 넘어 원자 CAS 불가. `uint16_t`로 줄여도 CUBRID 최대 페이지가 16K라 표현 가능. |
| **출처** | `02 §1`, `§2.2`, `§2.5`; `bestspace.hpp:62-65, 402-407@f30f1c260`(static_assert 직접 확인) |

### D-17. `atomic_wrapper` 64바이트 패딩 — 메모리 8배를 false sharing과 맞바꿈

| | |
|---|---|
| **결정** | 모든 L1/L2/L3 원자 변수를 `alignas(64)` 래퍼에 담아 **캐시라인 하나를 독점**시킨다. `m_allocating`도 마찬가지. |
| **근거** | 8바이트를 64바이트에 담는 8배 낭비지만, **서로 다른 페이지 슬롯을 갱신하는 스레드끼리 false sharing이 완전히 사라진다.** shard 하나가 4,800바이트가 되는 이유다. 이 설계는 "인메모리 bestspace를 작게 유지"하려는 것이 아니라 "경합 없이 유지"하려는 것이다. |
| **기각된 대안** | **패딩 없음** — 64슬롯이 8개 캐시라인에 몰려 인접 슬롯 갱신끼리 라인을 튕긴다. |
| **예외** | `m_num_pages`/`m_recs_num`/`m_recs_sumlen`은 **맨 `std::atomic`** 으로 인접 배치되어 같은 라인을 공유한다. 정확도보다 갱신 비용이 중요한 값이라 패딩을 주지 않았다 **[추정 — 주석 없음]**. |
| **출처** | `02 §2.7~2.8`; `bestspace.hpp:408-413, 415-416@f30f1c260` |

### D-18. `needed_size` / `consume_size` / `record_length` 3분리

| | |
|---|---|
| **결정** | 세 가지 양을 처음부터 다른 이름으로 분리한다. `consume_size = size + SPAGE_SLOT_SIZE`(페이지 공간 회계), `needed_size = consume_size + unfill_space`(수용 판정), 통계용 레코드 길이 = `consume_size - SPAGE_SLOT_SIZE`. **탐색은 `needed_size`로 하고 예약은 `consume_size`로 한다.** 레코드가 커서 `needed_size`가 페이지 용량을 넘으면 unfill 예약을 포기한다. |
| **근거** | `unfill_space`는 후속 UPDATE를 위한 여유분인데, 레거시 bestspace는 이를 무시했다. 예약분 때문에 삽입 자체가 불가능해지면 예약을 포기해야 한다. |
| **기각된 대안** | **단일 `size` 변수** — 실제로 두 건의 버그를 낳았다. `04 T4`: `recs_sumlen`에 `consume_size`(슬롯 오버헤드 포함)를 그대로 누적해 옵티마이저의 평균 레코드 길이가 부풀었다. |
| **출처** | `02 §2.9`; `04 M1`(`2c7071fd3`), `T4`; `bestspace.cpp:1354-1358@f30f1c260`(직접 확인) |

### D-19. `is_newrec` — relocation을 신규 레코드로 계상하지 않음

| | |
|---|---|
| **결정** | 탐색 API에 `bool is_newrec`를 실어 보낸다. `heap_get_insert_location_with_lock`(진짜 신규)은 `true`, `heap_find_location_and_insert_rec_newhome`(`REC_NEWHOME` 재배치)은 `false`. `add_estimates(0, is_newrec ? 1 : 0, ...)`. |
| **근거** | 재배치는 객체 수를 늘리지 않는다. 업데이트가 많은 테이블에서 `num_recs` 오차가 누적된다. |
| **기각된 대안** | **구분 없음**(초기 구현) — `04 T5`. |
| **재작성 권고** | **`bool`보다 enum이 낫다.** `04 T5(d)`: "bestspace 탐색 API를 설계할 때 '왜 페이지를 찾는가'를 처음부터 인자로 받아라. 최소 `INSERT_NEW` / `RELOCATE` 두 가지는 구분되어야 하며, 나중에 vacuum/compactdb가 붙으면 더 늘어난다." |
| **출처** | `04 T5`; `bestspace.hpp:368-369@f30f1c260` |

### D-20. estimates를 shard별 atomic 델타로 분산, 과대추정 선호

| | |
|---|---|
| **결정** | `num_pages`/`num_recs`/`recs_sumlen`을 **객체 베이스값 + Σ(shard 델타)** 구조로 둔다. `get_estimates`는 대입이 아니라 **누산**(`+=`)하고, `set_estimates`는 베이스를 `store`한 뒤 각 shard 누적분을 읽어 그만큼 빼서 0으로 만든다. 세 값 사이의 원자성은 **보장하지 않는다.** |
| **근거** | 핫 캐시라인 회피. 추정치이므로 세 값이 일관된 스냅샷일 필요가 없다. `set_estimates`의 read-then-subtract 사이 race로 남는 증가분은 **의도적으로 허용**한다 — 코드 주석: "It's better for the estimates to be higher than the actual values rather than lower." |
| **기각된 대안** | ① **헤더 필드 유지** — D-01에 반한다. ② **단일 전역 원자 카운터** — 캐시라인 핑퐁. ③ **뮤텍스 보호 스냅샷** — 병목 재도입. |
| **비대칭 주의** | 디스크 플러시에서 `num_pages`만 `MAX(heap_hdr->num_pages, num_pages)`로 **단조 증가** 처리하고 `num_recs`/`recs_sumlen`은 무조건 덮어쓴다. 페이지 할당은 in-memory 델타를 공개하기 전에 헤더를 먼저 갱신하므로, 덮어쓰면 이미 반영된 증가분을 되돌린다 (`02 §5.4` 6번). |
| **출처** | `02 §2.8`, `§5.4`; `04 M4`, `T14`; `bestspace.cpp:367-389, 1396-1431@e84a7f6dc` |

### D-21. `pgbuf_ordered_callback` 신설 — latch를 쥔 채 대기 금지

| | |
|---|---|
| **결정** | 모든 shard가 `ALLOCATING`이라 대기해야 할 때, **보유 중인 모든 ordered 페이지를 일시 해제하고 → 콜백(yield/sleep) 실행 → VPID 순서로 재fix**하는 신규 page_buffer 헬퍼를 도입한다. 대기 콜백은 20회까지 `std::this_thread::yield()`, 이후 10μs sleep, 매회 `logtb_is_interrupted` 확인. |
| **근거** | 스핀하는 스레드가 다른 heap 페이지 latch를 이미 보유했고 할당 중인 스레드가 바로 그 페이지를 필요로 하면 **영원히 서로 기다린다.** CUBRID의 ordered fix 프레임워크는 "대기 중인 스레드가 래치를 놓는다"고 가정하지 않는다. |
| **계약** | ① 현재 스레드의 **모든 fix가 ordered 페이지이고 watcher를 가져야 한다** — watcher 없는 raw fix가 하나라도 있으면 실패한다(재fix 후 포인터를 갱신해줄 대상이 없으므로). ② **콜백은 페이지를 잡은 채 반환하면 안 된다.** ③ 콜백이 에러를 반환해도 페이지는 순서대로 재fix된다. ④ 재fix 실패 시 일부 watcher가 페이지 없이 남을 수 있으므로 **호출자는 watcher 포인터를 반드시 확인해야 한다.** ⑤ 반환값은 콜백의 반환값이다. |
| **기각된 대안** | ① **latch 쥔 채 스핀**(초기 구현) — `04 T7`의 데드락. ② **대기 없이 실패 반환** — 모든 shard가 할당 중일 때 상위에서 무한 재시도. |
| **출처** | `02 §5.2`; `04 T7`(`304f3b0d0`, `7c862d2bc`); `page_buffer.c:13002-13309@e84a7f6dc` |

### D-22. 체크포인트를 탐색 **전에** 배치

| | |
|---|---|
| **결정** | `heap_find_bestpage`에서 `bestspace->updatable()` → `heap_update_bestspace()`를 **`bestspace->find()` 호출 전에** 수행한다. |
| **근거** | `heap_update_bestspace`가 헤더 페이지를 ordered fix하는데, 그 과정에서 **이미 fix된 best page를 unfix했다가 재fix할 수 있다.** 탐색 결과를 watcher에 물린 뒤 체크포인트를 돌리면 그 watcher가 무효화된다. 코드 주석: `/* update may unfix the fixed page (best page) so sync in-memory bestspace with disk first */`. |
| **기각된 대안** | **탐색 후 체크포인트**(초기 구현) — `04 T16`. |
| **일반화된 규칙** | **ordered fix를 쓰는 함수는 "다른 페이지를 unfix할 수 있다"고 가정하라. 유지보수 작업은 항상 리소스 획득 전에 배치하라.** |
| **출처** | `04 T16`; `heap_file.c:4593-4601@f30f1c260`(주석 4593, `updatable()` 4594 — 직접 확인) |

### D-23. 힌트 경로와 수요 경로 API 분리

| | |
|---|---|
| **결정** | `heap_find_bestspace(class_oid = NULL 포인터)`는 **"있으면 달라, 없으면 만들지 말고 NULL"** 이고 **에러가 아니다.** `heap_add_bestpage`(힌트 공급)가 이 모드를 쓴다. 반면 `class_oid`가 유효하면 필요 시 디스크에서 재구축한다. 별도로 **`OID_ISNULL(class_oid)`(NULL OID 값)** 은 부트스트랩 중 root class로 간주해 재구축한다. |
| **근거** | vacuum/물리 delete마다 전체 재구축(헤더 fix + shard 페이지 전부 읽기)이 일어나면, 아무도 삽입하지 않는 heap에까지 무거운 초기화가 걸린다. 게다가 모든 물리 delete마다 `heap_get_class_oid_from_page()` 읽기가 추가된다 (`04 T15`). |
| **기각된 대안** | **힌트 경로도 재구축** (초기 구현) — 위 비용. |
| **재작성 권고** | `04 T15(d)`: "NULL 포인터 vs NULL OID 값의 의미 차이로 구분하는 현재 방식은 동작하지만 **읽는 사람을 속이기 쉽다** — 별도 함수나 enum 인자가 낫다." 그리고 §7 **D3의 근원이 바로 이 결정**이므로, 분리하되 **힌트를 버리지 않는 방법**을 함께 설계해야 한다. |
| **출처** | `02 §3.5`; `04 T15`; `heap_file.c:4625-4629@f30f1c260`(직접 확인) |

### D-24. `max_bestspace_entries`는 제거가 아니라 `PRM_OBSOLETED`

| | |
|---|---|
| **결정** | 구 파라미터 `PRM_ID_HF_MAX_BESTSPACE_ENTRIES`에 `PRM_OBSOLETED` 플래그만 추가하고 **이름 매크로와 enum은 남긴다.** 기존 설정 파일에 있어도 기동이 실패하지 않고 조용히 무시된다. |
| **근거** | enum을 제거하면 **이후 모든 PRM id가 밀린다.** |
| **출처** | `02 §6.2`; `04 M5` |

### D-25. **[재작성 신규 결정 — 원본에서 명시적으로 내려지지 않았음]** shard 페이지를 별도 VFID에 둘 것인가

D-12는 원본 PR이 실제로 내린 결정("heap 자신의 VFID, 페이지 체인 맨 앞")을 기록한 것이다. **이 항목은 그 결정을 재작성 시점에 다시 여는 정식 결정 슬롯이다.** `04` 문서가 "이 결정을 R0에서 내려야 한다 — 나중에 바꾸면 전면 재작업이다"라고 명시하므로, P0-3에서 **문서화된 판단**을 남겨야 한다.

| | |
|---|---|
| **결정해야 할 것** | shard 페이지를 ① heap 자신의 `FILE_HEAP` VFID 안에(= 원본) 둘 것인가, ② **별도 VFID**에 둘 것인가 |
| **①을 고를 때의 비용 — 파생 함정 목록** | `04` 문서의 함정 18건 중 **T3 / T10 / T14가 모두 이 단일 결정에서 파생된다.** ⟨T3⟩ `heap_Maxslotted_reclength`를 `spage_max_record_size() − sizeof(HEAP_HDR_STATS)`로 계산했는데, 데이터/shard 페이지의 슬롯 0에는 훨씬 작은 `HEAP_CHAIN`이 들어가므로 기준 자체가 틀렸다(→ `heap_nonheader_page_capacity()` 신설). ⟨T10⟩ `file_get_num_user_pages()`가 heap VFID의 **모든** 페이지를 세므로 옵티마이저가 보는 페이지 수가 최대 4 크고, 히스토그램 샘플러가 사용자 레코드 없는 페이지를 샘플로 잡는다(→ `heap_get_num_data_pages()` 신설 + 샘플러 2곳 스킵). ⟨T14⟩ compactdb가 디스크만 갱신하면 in-memory 객체가 사라진 페이지를 가리킨 채 남는다. **그리고 `heap_page_is_bestspace()` 가드를 스캐너 9곳 이상에 뿌리고도 통계 경로 3곳이 뒤늦게 발견됐다** — 스윕이 체계적이지 않았다는 신호다. |
| **①의 이득** | 별도 파일을 만들지 않으므로 heap 생성/삭제/재사용/복구 경로가 그대로 동작한다. 파일 관리 비용 0 |
| **②의 이득** | **오염 반경이 0.** `hfid.vfid`로 페이지를 세거나 순회하는 모든 코드가 자동으로 안전해지고, §6 P7의 전수 스윕 분량이 급감한다. `04 T10(d)` 원문: "대안으로 **shard 페이지를 별도 VFID에 두는 설계**를 먼저 검토할 가치가 있다 — 그러면 이 함정 부류 전체가 사라진다." |
| **②의 비용** | 파일 하나가 늘어난다 → heap 생성/삭제/`heap_reuse`/compactdb/복구에서 두 파일의 **원자적 생명주기**를 맞춰야 한다. `vacuum_rv_notify_dropped_file`이 VFID 기준으로 registry를 정리하므로(D-07) 그 경로도 두 VFID를 알아야 한다 |
| **판단 시 참고** | ②를 고르면 D-12의 `HEAP_PAGE_FLAG_BESTSPACE` 플래그와 `heap_page_is_bestspace()`가 **불필요해진다**. 반대로 ①을 고수하면 P7 전수 스윕이 **필수 단계**가 되고, `grep -rn "file_get_num_user_pages\|heap_vpid_next\|spage_next_record" src/` 체크리스트를 소진해야 한다 |
| **출처** | `04 T3`, `T10`, `T14`, `R0-5`, `R7`; `02 §4.2~4.3`; 본 문서 D-12 |

**결정 총계: 25건** (원본이 내린 결정 24건 + 재작성 시 다시 열어야 할 결정 1건).

---

## 3. 불변식 (Invariants)

정확성이 의존하는 명제들이다. **코드에 주석으로 남기고, 가능하면 `static_assert`/`assert`로 강제하라.**

### I-1. L1은 힌트다. 최종 판단은 항상 fix + 실측.

`L1.freespace`에 기록된 값은 **사실이 아니라 힌트**다. 페이지를 실제로 쓰기 직전에는 반드시:

1. `pgbuf_ordered_fix`로 WRITE latch 획득
2. `pgbuf_get_page_ptype(...) == PAGE_HEAP` 확인
3. `heap_get_class_oid_from_page(...)` 결과가 기대 `class_oid`와 일치하는지 확인 (페이지가 재활용되어 다른 클래스로 넘어갔을 수 있다)
4. `spage_max_space_for_new_record(...)`로 **현재 free space를 다시 읽어** 비교

이 4단계를 통과한 값만 신뢰한다. `04 T13(d)`: "캐시된 free space는 힌트일 뿐 사실이 아니다. (…) `pop()` 시점의 필터는 최적화이지 정확성 장치가 아니다."

**따름 정리 I-1a.** 예약 CAS 앞에는 `VPID_EQ(&vpid, &old_vpid)` 가드가 있어야 한다. 내가 페이지를 잡고 있는 동안 다른 스레드가 그 L1 슬롯을 완전히 다른 페이지로 교체했을 수 있고, 그 경우 내 측정값을 쓰면 안 된다 (`02 §2.9`).

**따름 정리 I-1b.** 예약 CAS 실패는 무시하고 진행해도 된다. 페이지는 이미 잡았으므로 삽입은 가능하고, free space 정보는 다음 방문에서 교정된다.

### I-2. bitmap ↔ L1은 eventual consistency다.

L2/L3 비트맵은 L1의 **요약**이며, 갱신 순서가 L1 먼저 · L2/L3 나중이라 항상 한 박자 늦을 수 있다. 이것은 오류가 아니다.

**강제 규약.** `L2_update`/`L3_update`는 **이중 루프**여야 한다 — 안쪽 `do-while`이 표준 CAS 재시도이고, **바깥 `while`은 CAS 성공 직후 하위 레벨을 다시 읽어 값이 그대로인지 확인**한다. 내가 L2를 갱신하는 사이 L1이 또 바뀌었다면 방금 쓴 값은 이미 낡았으므로 처음부터 다시 한다. 이 재확인이 없으면 **낡은 요약이 영구히 남는다** (`02 §2.9`, `04 M1`).

`desired == expected`면 CAS 없이 조기 반환한다 — 대부분의 삽입은 tier를 바꾸지 않으므로 이것이 상시 경로다.

### I-3. `L2::find`/`L3::find`는 "정확히 그 tier"만 반환한다.

"이상(以上)"이 아니다. 상위 tier 탐색은 **호출자의 `for (t = minimum; t <= FS8; ++t)` 루프 책임**이다. 재구현 시 놓치기 쉬운 지점 (`02 §2.6`).

### I-4. crash 시 stale 상태를 허용한다.

마지막 sync 이후의 L1/candidate 변화는 소멸하며, 재시작 후 stale snapshot으로 rebuild된다. **정합성 문제가 아니다** — 모든 항목이 I-1의 검증을 거치기 때문이다.

단, **stale의 방향에 따라 자가치유 가능 여부가 다르다** (`03 §7.3`):

| stale 방향 | 결과 | 자가치유 |
|---|---|---|
| **낙관(과대)** — 기록값 > 실제 | fix 후 실측에서 부족 판정 → CAS로 실제값 반영 | **가능** |
| **비관(과소)** — 기록값 < 실제 | 사전 검사에서 탈락 → 페이지를 fix하지 않음 | **불가능** |

과소-stale은 스스로 고쳐질 계기가 없다. 그 페이지를 fix해볼 이유가 없기 때문이다. **§7 D5의 근원이 이 비대칭이다. 재작성 시 반드시 자가치유 경로를 설계하라.**

### I-5. bestspace 페이지는 사용자 통계·스캔에서 제외된다.

`hfid.vfid`로 페이지를 세거나 순회하는 **모든** 코드가 shard 페이지를 걸러야 한다.

- 순회: `heap_page_is_bestspace(thread_p, page)` 가드
- 계수: `heap_get_num_data_pages()` (= `file_get_num_user_pages()` − `heap_hdr->bestspace.num_pages`)
- **헤더 페이지는 사용자 레코드를 담을 수 있으므로 남긴다.**

판별 방식에 주의: `heap_page_is_bestspace`는 슬롯 0을 PEEK해서 `recdes.length != sizeof(HEAP_CHAIN)`이면 false를 반환한다 — **길이가 다르다는 것은 그 페이지가 heap 헤더 페이지라는 뜻**이다. 타입 태그 없이 레코드 길이로 페이지 종류를 가른다 (`02 §4.2`).

`04 T10(d)`: "'heap 파일 안에 사용자 레코드가 없는 페이지를 넣는다'는 결정을 내리는 순간, `hfid.vfid`로 페이지를 세는 모든 코드가 잠재적 버그다."

### I-6. latch ordering — ordered fix 규약

**모든** bestspace 경로의 페이지 fix는 `pgbuf_ordered_fix`를 쓴다. watcher 랭크는:

| 대상 | 랭크 |
|---|---|
| heap 헤더 페이지 | `PGBUF_ORDERED_HEAP_HDR` (enum 0번, 최상위) |
| 데이터/후보 페이지 | `PGBUF_ORDERED_HEAP_NORMAL` |
| shard 페이지 | `heap_bestspace_fix_page`가 WRITE로 ordered fix |

**절대 금지: 페이지 latch를 쥔 채 임의 시간 대기.** ordered fix 프레임워크의 계약 밖 동작이며 데드락을 만든다. 대기가 필요하면 D-21의 `pgbuf_ordered_callback`을 쓴다. **콜백 이후 모든 페이지 상태를 재검증해야 한다** — 재fix 사이에 내용이 바뀌었을 수 있다.

`xlogtb_reset_wait_msecs(LK_FORCE_ZERO_WAIT)`는 **반드시 짝을 맞춰 복원**한다 (`01 §10-8`).

### I-7. 예약과 통계는 다른 양이다.

`consume_size`(페이지 공간 회계, 슬롯 오버헤드 포함)를 `recs_sumlen`에 누적하면 안 된다. 통계에는 `consume_size - SPAGE_SLOT_SIZE`를 쓴다 (D-18, `04 T4`).

### I-8. in-memory candidate 큐는 오름차순, on-disk candidate 배열은 내림차순.

`to_entries`가 역순 복사로 흡수한다. 적재 시 `push_candidates`가 앞에서부터 넣으면 in-memory 오름차순이 자연스럽게 만들어진다 (`02 §2.11`, `§4.4`).

### I-9. shard당 할당자는 한 명.

`m_allocating`을 CAS(false→true)한 스레드만 `allocate` 경로에 진입한다. 실패한 스레드는 **블로킹 없이** 다음 shard로 전진한다. 모든 shard가 할당 중이면 I-6의 규약에 따라 latch를 놓고 대기한다.

### I-10. 온디스크 레이아웃 불변식 (반드시 `static_assert`)

| 불변식 | 현재 강제 여부 |
|---|---|
| `sizeof(bestspace_entry) == 8`, offset 0/2/4 | ✅ `bestspace.hpp:62-65@f30f1c260` |
| `sizeof(bitmap) == 1` + trivially copyable | ✅ `bestspace.hpp:399-400` |
| `sizeof(L1) == sizeof(L2) == sizeof(L3) == 8` | ✅ `bestspace.hpp:402-404` |
| `std::atomic<L1/L2/L3>::is_always_lock_free` | ✅ `bestspace.hpp:405-407` |
| `sizeof(atomic_wrapper<T>) == 64`, `alignof == 64` | ✅ `bestspace.hpp:408-413` |
| `sizeof(shard) == 4800`, `alignof(shard) == 64` | ✅ `bestspace.hpp:415-416` |
| `offsetof(L1, m_freespace) == offsetof(bestspace_entry, freespace)` 등 3건 | ✅ `bestspace.cpp:139-141@e84a7f6dc` |
| **`sizeof(HEAP_HDR_STATS) == 1152`** | ❌ **없음.** 런타임 `assert(recdes.length == sizeof(HEAP_HDR_STATS))`만 존재 (`heap_file.c:4407@f30f1c260`) |

**재작성 시 마지막 항목의 `static_assert`를 반드시 추가하라.** 이 어서션의 부재가 §7 D1(디스크 호환성)의 조기 발견을 막았다.

---

## 4. 상수 / 파라미터 표

**모든 값은 `f30f1c260`에서 직접 확인했다.**

### 4.1 컴파일 타임 상수

| 상수 | 값 | 선언 | 의미 / 파생 관계 |
|---|---|---|---|
| `BITS_PER_BYTE` | 8 | `bestspace.hpp:74` | `numeric_limits<unsigned char>::digits` |
| `MAX_CANDIDATES_QUEUE_SIZE` | **128** | `bestspace.hpp:75` | candidate 큐 정원 **= on-disk `candidates[]` 크기**. 둘은 반드시 같아야 한다 |
| `MAX_SHARD_PAGE_COUNT` | **4** | `bestspace.hpp:76` | heap 내 shard 페이지 최대 개수. **4K 페이지에서 필요한 값이 정확히 4** (D-13) |
| `ALLOC_BATCH_SIZE` | **4** | `bestspace.hpp:77` | victim/candidate/신규할당 배치 크기 (D-11) |
| `L3_FANOUT` | **8** | `bestspace.hpp:78` | shard당 L2 그룹 수. allocating 비트 분리로 7→8 (D-05) |
| `L2_FANOUT` | **8** | `bestspace.hpp:79` | L2 그룹당 L1 슬롯 수 |
| `ENTRIES_PER_SHARD` | **64** | `bestspace.hpp:80` | `L3_FANOUT × L2_FANOUT`. ⚠ `heap_file.c:4479`에 리터럴 `64` 잔존 (D-13) |
| `DEFAULT_SHARD_COUNT` | **8** | `bestspace.hpp:81` | 파라미터 기본값과 일치 |
| `TLS_MAX_SIZE` | **40** | `bestspace.hpp:465` | thread-local registry 캐시 정원 |
| `UPDATE_TIME_THRESHOLD` | **30** (초) | `bestspace.cpp:1312` | 주기 sync 간격. **함수 지역 `constexpr`, 파라미터 없음** |
| `HEAP_BESTSPACE_ENTRIES_SLOTID` | 1 | `heap_file.c:231@e84a7f6dc` | `HEAP_HEADER_AND_CHAIN_SLOTID + 1` |
| `HEAP_PAGE_FLAG_BESTSPACE` | `0x00000001` | `heap_file.c:220@f30f1c260` | vacuum 상태(`0xC0000000`)와 비트 충돌 없음 |
| `SPAGE_SLOT_SIZE` | 4 | `slotted_page.h` | `consume_size` 계산에 사용 |

### 4.2 tier 경계

임계값 배열: `static constexpr std::int16_t threshold[] = { 7, 15, 24, 34, 45, 57, 70, 84 };` (`bestspace.cpp:1381@f30f1c260`, 직접 확인)

판정: `percentage = size * 100 / DB_PAGESIZE;` 후 `percentage <= threshold[i]`인 첫 `i`에 대해 `tier(i - 1)` 반환. 전부 초과하면 `FS8`.

| tier | enum | 백분율 | 16K 기준 바이트(**계산값**) | 비트맵 색인 |
|---|---|---|---|---|
| `FS0` | **−1** | ≤ 7% | 0 – 1310 | **안 됨** (센티널, D-04) |
| `FS1` | 0 | 8 – 15% | 1311 – 2621 | 인덱스 0 |
| `FS2` | 1 | 16 – 24% | 2622 – 4095 | 인덱스 1 |
| `FS3` | 2 | 25 – 34% | 4096 – 5734 | 인덱스 2 |
| `FS4` | 3 | 35 – 45% | 5735 – 7536 | 인덱스 3 |
| `FS5` | 4 | 46 – 57% | 7537 – 9502 | 인덱스 4 |
| `FS6` | 5 | 58 – 70% | 9503 – 11632 | 인덱스 5 |
| `FS7` | 6 | 71 – 84% | 11633 – 13926 | 인덱스 6 |
| `FS8` | 7 | 85 – 100% | 13927 – 16384 | 인덱스 7 |
| `FSEND` | 8 | — | — | 루프 종료 감시값 |

**`FS3`(25%)은 별도의 의미를 갖는다** — `heap_add_bestpage`가 candidate 큐에 페이지를 넣을지 결정하는 문턱값이다:

```c
freespace = spage_get_free_space_without_saving (thread_p, pgptr);
if (cubstorage::bestspace::size_to_tier (freespace) >= cubstorage::bestspace::tier::FS3)
```
(`heap_file.c:4631-4632@f30f1c260`, 직접 확인)

> **비교 참고.** 레거시의 대응 문턱은 `HEAP_DROP_FREE_SPACE = (int)(DB_PAGESIZE * 0.3)` = **30%** 였다 (`heap_file.h:103@e84a7f6dc^`). 신 설계는 25%로 낮췄지만 **`prm_get_integer_value(PRM_ID_HF_MAX_BESTSPACE_ENTRIES) > 0` 게이트를 없애면서 문턱 판정을 `heap_add_bestpage` 안으로 옮겼다** (`02 §5.6`). 이 FS3 게이트가 §7 D5(vacuum 페이지 미재사용)의 직접 원인으로 지목됐다.

### 4.3 크기

| 대상 | 크기 | 근거 |
|---|---|---|
| `bestspace_entry` / `L1` / `L2` / `L3` | **8 B** | `static_assert` |
| `atomic_wrapper<T>` | **64 B** (align 64) | `static_assert` |
| `shard` | **4,800 B** (align 64) | `static_assert`. 내역: allocating 64 + L3 64 + L2 512 + L1 4096 + parent 8 + estimates 20 + stats 32 + 패딩 = 64 × 75 |
| bestspace 객체의 shard 영역 (기본 8) | **38,400 B** | 계산값 |
| `HEAP_HDR_STATS` | **1,152 B** (계산값) | AS-IS 296 B 대비 **3.9배**. `static_assert` 없음 (I-10) |
| ↳ `bestspace.candidates[128]` | 1,024 B | 오프셋 64 |
| ↳ `bestspace.pages[4]` | 32 B | 오프셋 1104 |
| `HEAP_CHAIN` | 40 B | |
| `heap_nonheader_page_capacity()` | `spage_max_record_size() - sizeof(HEAP_CHAIN)` = `DB_PAGESIZE - 36 - 40` | `heap_file.c:26101-26104@f30f1c260`, 직접 확인 |
| shard 페이지 엔트리 용량 | `(spage_max_record_size() − DB_ALIGN(sizeof(HEAP_CHAIN),4) − SPAGE_SLOT_SIZE) / 8` | 4K→502, 8K→1014, 16K→2038 |

### 4.4 시스템 파라미터

| 파라미터 | 값 | 정의 | 비고 |
|---|---|---|---|
| **`bestspace_shard_count`** (`PRM_ID_BESTSPACE_SHARD_COUNT`) | 기본 **8**, 범위 **1 ~ 28** | `system_parameter.h:538`, `system_parameter.c:5389-5399@e84a7f6dc` | 플래그 **`PRM_FOR_SERVER`만.** `PRM_USER_CHANGE` 없음 → 세션 중 변경 불가, 서버 기동 시에만 반영. 상한 28 = 4K 페이지 4장(502×4=2008)에 28×64=1792 엔트리가 들어가는 최대치 |
| `max_bestspace_entries` (`PRM_ID_HF_MAX_BESTSPACE_ENTRIES`) | 1,000,000 (무시됨) | `system_parameter.c:1199-1210@e84a7f6dc` | **`PRM_OBSOLETED` 추가.** 이름·enum 유지 (D-24) |
| `hf_unfill_factor` (`PRM_ID_HF_UNFILL_FACTOR`) | 기본 **0.10**, 범위 0.0 ~ 0.3 | `system_parameter.c:1188-1198@e84a7f6dc` | **변경 없음.** 소비 방식만 변경: `heap_hdr.unfill_space = (int)(DB_PAGESIZE × factor)` → `bestspace::m_unfill_space` → `needed_size` |
| `debug_heap_bestspace` (`PRM_ID_DEBUG_BESTSPACE`) | bool | `system_parameter.c:702` | PR 이전부터 존재, 변경 없음 |
| **sync 주기** | 30초 | **파라미터 없음** (`bestspace.cpp:1312`) | 재작성 시 노출 여부 결정 필요 |

> `prm_Def[]` 항목의 필드 순서는 `{id, name, static_flag, datatype, dynamic_flag, default, value, **upper**, **lower**, force, set_dup, get_dup}` 이다 — **상한이 하한보다 먼저 온다.** 실제로 원본 PR이 이 순서를 뒤집어 적어 커밋 `5e8a8ce5e`로 고쳤다 (`04 T2`).

### 4.5 복구 인덱스 / 에러 코드 / 호환성

| 항목 | 값 | 위치 |
|---|---|---|
| `RVHF_UPDATE_BESTSPACE_ENTRIES` | **130** (redo 전용, undo NULL) | `recovery.h:187@e84a7f6dc` |
| `RV_LAST_LOGID` | 129 → **130** | `recovery.h:189@e84a7f6dc` |
| redo 핸들러 | `heap_rv_redo_update` (기존 재사용) | `recovery.c:844-849@e84a7f6dc` |
| shard 페이지 생성 시 로그 | `RVHF_INSERT_NEWHOME` (HA 회피용) | `heap_file.c:3959-3964@e84a7f6dc` |
| shard 페이지 체인 재작성 | `RVHF_CHAIN` | `heap_file.c:4032@e84a7f6dc` |
| 헤더 페이지 갱신 | `RVHF_STATS` (redo 로깅) | `heap_file.c:4266@e84a7f6dc` |
| **`disk_compatibility_level`** | **`11.5f` — 변경되지 않음** | `release_string.c:105@f30f1c260`, **직접 확인** |
| `ER_HF_MAX_BESTSPACE_ENTRIES` | −1089 (사용처 소멸) | `error_code.h:1371@e84a7f6dc^` |

**마지막에서 두 번째 줄이 §7 D1의 핵심 증거다** — 온디스크 `HEAP_HDR_STATS`가 296 B에서 1,152 B로 바뀌었는데 disk compatibility level은 `11.5f` 그대로다.

---

## 5. 인터페이스 계약

### 5.1 heap → bestspace (수요 경로)

#### `heap_find_bestpage` — 삽입 경로 단일 진입점

```c
STATIC_INLINE int
heap_find_bestpage (THREAD_ENTRY *thread_p, OID *class_oid, HFID *hfid, std::uint16_t size,
                    bool is_newrec, PGBUF_WATCHER *page_watcher);
```
(`heap_file.c:4576-4605@f30f1c260`, 직접 확인)

| 항목 | 계약 |
|---|---|
| **동작** | ① `heap_find_bestspace(class_oid, hfid, NULL)` — 없으면 **재구축** ② `updatable()`이면 `heap_update_bestspace()`로 **디스크 sync (탐색 전, D-22)** ③ `bestspace->find(...)` |
| **`size`** | 레코드 본문 길이. `0 < size < DB_PAGESIZE`이고 `!heap_is_big_length(size)`가 성립해야 한다 (`bestspace.cpp:1332-1333`의 assert) |
| **`is_newrec`** | `true` = 신규 삽입, `false` = `REC_NEWHOME` 재배치 (D-19) |
| **`page_watcher`** | **진입 시 `pgptr`/`next`/`prev`가 모두 NULL이어야 한다.** 아니면 `ER_FAILED`. 성공 시 **대상 페이지에 WRITE latch를 잡은 채** 반환된다 — 호출자가 해제 책임을 진다 |
| **반환** | `NO_ERROR` 또는 에러 코드 |
| **호출자** | `heap_get_insert_location_with_lock`(`is_newrec=true`), `heap_find_location_and_insert_rec_newhome`(`false`) |

#### `heap_find_bestspace` — registry 조회 / lazy 재구축

```c
static cubstorage::bestspace *
heap_find_bestspace (THREAD_ENTRY *thread_p, OID *class_oid, HFID *hfid, PGBUF_WATCHER *header_watcher);
```
(`heap_file.c:4497@f30f1c260`)

| `class_oid` | 의미 |
|---|---|
| **NULL 포인터** | **lookup-only.** 없으면 `NULL` 반환, **에러 아님.** 재구축 금지 (D-23) |
| `OID_ISNULL(...)`인 유효 포인터 | 부트스트랩 중 root class → `oid_Root_class_oid`로 치환 후 재구축 |
| 유효 OID | 없으면 헤더 WRITE latch → **latch 아래 재확인(double-checked locking)** → `heap_build_bestspace` |

`header_watcher != NULL`이면 호출자가 이미 헤더를 잡고 있다는 뜻이며, 다시 잡지 않는다.

#### `bestspace::find` — 탐색 본체

```cpp
int bestspace::find (cubthread::entry &thread_ref, OID *class_oid, HFID *hfid,
                     std::uint16_t size, bool is_newrec, PGBUF_WATCHER &page_watcher);
```
(`bestspace.hpp:368-369`, 구현 `bestspace.cpp:1324-1365@f30f1c260`)

동작 순서:
1. **stale error 방어** — 진입 시 `er_errid_if_has_error()`가 에러면 즉시 반환, 아니면 `er_clear()`. 이 경로가 `er_errid()`로 상태를 판별하는 곳이 많아 오염을 막아야 한다.
2. 인자 검증 (`hfid` 유효, watcher 비어 있음).
3. `PGBUF_INIT_WATCHER(&page_watcher, PGBUF_ORDERED_HEAP_NORMAL, hfid)`.
4. `consume_size = size + SPAGE_SLOT_SIZE`; `needed_size = consume_size + m_unfill_space`; **`needed_size > heap_nonheader_page_capacity()`이면 `needed_size = consume_size`** (unfill 포기).
5. **`shard = 0; bias = 0;`** ← **§7 D2. 재작성 시 여기를 thread/tran 기반으로 바꿔야 한다.**
6. `find_from_shards(...)`.

`find_from_shards`의 반환 상태는 **`FOUND` / `ALLOCATING` / `FAILURE` 셋뿐**이다 — `shard::find`가 내부에서 `NOT_FOUND`/`CONTENDED`를 `allocate()`로 흡수하기 때문이다.

### 5.2 heap → bestspace (힌트 경로)

#### `heap_add_bestpage` — free space 회수 알림

```c
extern void heap_add_bestpage (THREAD_ENTRY *thread_p, HFID *hfid, PAGE_PTR pgptr,
                               std::uint16_t prev_freespace = 0,
                               PGBUF_WATCHER *header_watcher = NULL);
```
(`heap_file.h:675-676@f30f1c260`, 직접 확인)

| 항목 | 계약 |
|---|---|
| **동작** | `heap_find_bestspace(NULL, hfid, header_watcher)` → **없으면 조용히 return** → `spage_get_free_space_without_saving`로 실측 → **tier ≥ FS3(25%)** 이면 `try_push_candidates` |
| **반환값 없음** | best-effort. `try_push`가 mutex 경합으로 실패해도 그냥 버린다 |
| **`prev_freespace`** | **받기만 하고 사용하지 않는다.** 주석: `/* prev_freespace is not used but leave this for future feature */` (`heap_file.c:4622-4623@f30f1c260`) |
| **호출자 (5곳, 직접 확인)** | `vacuum.c:2422` (vacuum forward page), `vacuum.c:2603` (vacuum home page, `initial_home_free_space` 전달), `heap_file.c:8954` (`heap_update_statistics` 전수 스캔, header_watcher 전달), `heap_file.c:16158` (`heap_rv_undo_insert`), `heap_file.c:22020` (`heap_delete_physical`) |

> 레거시 대비: 구 코드에서 vacuum은 `PRM_ID_HF_MAX_BESTSPACE_ENTRIES > 0` 게이트와 `HEAP_DROP_FREE_SPACE`(30%) 문턱을 통과해야 `heap_stats_update`를 불렀다. 신 코드는 두 게이트를 없애고 이 함수 한 줄로 대체하면서 문턱을 FS3(25%)로 옮겼다.
>
> **레거시 정리 항목 (재작성 스코프에 반드시 포함).** 레거시 `vacuum.c`의 forward page 경로에는 **bestspace_mutex 경합 회피용 임시방편**이 코드에 명시적으로 남아 있고, 그 정리를 CBRD-26176에 예약해 두었다. **`e84a7f6dc^:src/query/vacuum.c` 2419-2435 (주석 2425-2432, 호출 2433)** — 직접 확인한 원문:
>
> ```c
> if (prm_get_integer_value (PRM_ID_HF_MAX_BESTSPACE_ENTRIES) > 0)      /* 2419 */
>   {
>     int freespace = spage_get_free_space_without_saving (thread_p, helper->forward_page, NULL);
>
>     if (freespace > HEAP_DROP_FREE_SPACE)                             /* 2423 */
>       {
>         /*
>          * NOTE:
>          * By checking the freespace > HEAP_DROP_FREE_SPACE condition, heap_Bestspace->bestspace_mutex contention is reduced
>          * and the unnecessarily frequent extraction from heap_Bestspace->vpid_ht due to small free space is prevented in heap_stats_find_page_in_bestspace().
>          * And Passing the prev_freespace argument to 0 is a trick to get heap_stats_add_bestspace() called from heap_stats_update().
>          *
>          * This part will be refactored right away in the related issue, at which time this comment will be removed.
>          */
>         heap_stats_update (thread_p, helper->forward_page, &helper->hfid, 0);   /* 2433 — prev_freespace = 0 트릭 */
>       }
>   }
> ```
>
> **"the related issue"가 곧 CBRD-26176이다.** 재작성 시 다음 셋을 모두 해소해야 스코프가 닫힌다.
> 1. `prev_freespace = 0` **트릭 제거** — 신 설계의 `heap_add_bestpage`는 `prev_freespace`를 아예 쓰지 않으므로(S7) 트릭의 존재 이유가 사라진다.
> 2. **`PRM_ID_HF_MAX_BESTSPACE_ENTRIES > 0` 게이트 제거** — 파라미터가 `PRM_OBSOLETED`가 되므로(D-24) 이 조건은 죽은 분기다.
> 3. **주석 삭제** — 주석 자체가 "이 이슈에서 지운다"고 약속하고 있다.
>
> (`01 §6.3`, `§10-12`. 신 코드는 이 블록을 `heap_add_bestpage (thread_p, &helper->hfid, helper->forward_page);` 한 줄로 대체했고 문턱 판정을 FS3로 옮겼다 — `vacuum.c:2422@f30f1c260`, 직접 확인.)

### 5.3 bestspace 클래스 공개 API

(`bestspace.hpp:355-380@f30f1c260`, 직접 확인)

```cpp
explicit bestspace (std::size_t shard_count, int num_pages, std::uint64_t recs_num,
                    std::uint64_t recs_sumlen, std::uint16_t unfill_space);

void reset (const bestspace_entry *entries, std::size_t num_entries);

void try_push_candidates (bestspace_entry *candidates, std::size_t num_candidates);
void push_candidates     (bestspace_entry *candidates, std::size_t num_candidates);
std::size_t pop_candidates (bestspace_entry *candidates, std::uint16_t minimum,
                            std::uint16_t needed_size);

bool updatable ();

int find (cubthread::entry &thread_ref, OID *class_oid, HFID *hfid, std::uint16_t size,
          bool is_newrec, PGBUF_WATCHER &page_watcher);

static tier size_to_tier (std::uint16_t size);

void set_estimates (int num_pages, std::uint64_t recs_num, std::uint64_t recs_sumlen);
void get_estimates (int &num_pages, std::uint64_t &recs_num, std::uint64_t &recs_sumlen);
void get_stats (std::uint32_t &request, std::uint32_t &advanced_shard, std::uint32_t &fetch_L3,
                std::uint32_t &fetch_L2, std::uint32_t &fetch_L1, std::uint32_t &found,
                std::uint32_t &allocated);

std::size_t get_num_shards ();

void to_entries (bestspace_entry *entries, bestspace_entry *candidates, std::size_t &num_candidates);
```

| 함수 | 의미론 |
|---|---|
| `reset` | **재초기화이지 최초 초기화가 아니다.** compactdb/heap_reuse가 새 스냅샷으로 덮을 때 사용. 이름이 `initialize_by_entries`에서 개명된 것이 이 의도를 드러낸다 (`04 T14`) |
| `try_push_candidates` | `try_to_lock`. 실패하면 **후보를 버리고** 조용히 반환 |
| `push_candidates` | 블로킹 lock. 재구축/compactdb 경로용 |
| `pop_candidates` | 뒤(최선)에서 최대 `ALLOC_BATCH_SIZE`개. `minimum`(최악 victim의 free space)보다 나쁜 후보는 꺼내지 않는다. **최선 후보가 `needed_size` 미만이면 3개만** 꺼내 신규 할당을 강제 (D-11) |
| `updatable` | **조회가 아니라 선점(claim).** 30초 경과 시 `m_last_updated`에 CAS. **승자 한 명만 `true`**, 나머지는 `false`를 받고 그대로 탐색 진행. 시계는 `steady_clock` 기반 `monotonic_seconds()` |
| `get_estimates` | out 파라미터에 **대입이 아니라 누산(`+=`)**. 최종값 = 객체 베이스 + Σ(shard 델타) (D-20) |
| `to_entries` | L1 전체 스냅샷 + candidate 큐 스냅샷(**역순 = 내림차순**). 버퍼 크기는 호출자가 `get_num_shards() × 64`로 계산 |

### 5.4 registry 공개 API

(`bestspace.hpp:444-457@f30f1c260`, 직접 확인)

```cpp
void create (HFID *hfid, std::size_t shard_count, bestspace_entry *entries, std::size_t num_entries,
             bestspace_entry *candidates, std::size_t num_candidates, int num_pages,
             std::uint64_t recs_num, std::uint64_t recs_sumlen, std::uint16_t unfill_space);
void destroy (const VFID *vfid);
void destroy (const HFID *hfid);
bestspace *find (HFID *hfid);

using callback = int (*) (const HFID *hfid, bestspace *entry, void *args);
int for_each (callback function, void *args);
```

| 함수 | 계약 |
|---|---|
| `create` | **`bestspace *`를 반환하지 않는다.** 호출자가 곧바로 `find`를 다시 불러 포인터를 얻는다. 객체 구성은 **락 밖에서** 끝내고 링크만 락 안에서 한다. 중복 방지는 릴리스에서 사라지는 `assert`가 아니라 **호출자의 double-checked locking**에 의존한다 |
| `destroy` | `m_generation`을 1 증가 → 다른 스레드의 TLS 캐시 **전체** 무효화. `VFID` 오버로드는 매칭 노드 전부를 제거하는 **드레인 루프** |
| `find` | TLS → 전역 2단. 없으면 `nullptr` (에러 아님) |
| `for_each` | registry mutex를 **잡은 채** 순회한다. **첫 번째 에러만 보존**하고 이후 호출은 `er_stack_push/pop`으로 감싼다. ⚠ shutdown 단일 스레드 전제 — Greptile 리뷰 지적사항(§7 보조표) |

### 5.5 heap 측 신규 공개 함수

(`heap_file.h@f30f1c260`, 직접 확인)

| 시그니처 | 줄 | 역할 |
|---|---|---|
| `int heap_update_all_bestspaces (THREAD_ENTRY *)` | 398 | 전 registry 일괄 디스크 sync. **호출 지점이 트리 전체에서 딱 하나** — `xboot_shutdown_server`(`boot_sr.c:3087-3088@e84a7f6dc`), `vacuum_stop_workers` 이후 / `pgbuf_daemons_destroy` 이전 |
| `bool heap_page_is_bestspace (THREAD_ENTRY *, PAGE_PTR)` | 427 | shard 페이지 판별 (I-5) |
| `int heap_get_num_data_pages (THREAD_ENTRY *, const HFID *, int *)` | 457 | `file_get_num_user_pages()` − `bestspace.num_pages` |
| `int heap_estimate (THREAD_ENTRY *, const HFID *, int *npages, int *nobjs, int *avg_length)` | 460 | in-memory 우선, 미상주 시 헤더 fix 폴백 |
| `void heap_add_bestpage (...)` | 675 | §5.2 |
| `int heap_alloc_new_pages (THREAD_ENTRY *, HFID *, int npages, VPID *new_page_vpids, PGBUF_WATCHER *new_pg_watcher)` | 707 | 헤더 WRITE latch → `file_alloc_multiple`. **마지막 페이지는 fix된 채 반환** |
| `int heap_nonheader_page_capacity ()` | 710 | `spage_max_record_size() - sizeof(HEAP_CHAIN)`. ⚠ 이름에 "nonheader"가 들어간 이유는 `04 T3`(헤더 기준으로 계산해 과소평가한 버그) 때문이다 |

### 5.6 page_buffer 신규 헬퍼

```c
typedef int (*PGBUF_ORDERED_CALLBACK_FUNC) (THREAD_ENTRY *thread_p, void *args);

#define pgbuf_ordered_callback(thread_p, callback_func, callback_args) \
        pgbuf_ordered_callback_release(thread_p, callback_func, callback_args)
```
(`page_buffer.h:251, 290-294, 340-343@e84a7f6dc`; 구현 `page_buffer.c:13002-13309`)

동작 7단계와 계약은 D-21 참조. **트리 전체에서 유일한 호출자가 `bestspace::find_from_shards`** (`bestspace.cpp:1510`)다.

### 5.7 관측 인터페이스

| 수단 | 상태 |
|---|---|
| `SHOW HEAP HEADER` / `SHOW ALL HEAP HEADER` | 컬럼 22개 → **12개**. `Estimates_*` 14개 삭제, `Last_vpid`/`Num_pages`/`Num_recs`/`Avg_rec_len` 4개 추가 (`show_meta.c:299-311@e84a7f6dc`) |
| `SHOW SLOTTED PAGE HEADER` | `Need_update_best_hint` 컬럼 삭제 (`SPAGE_HEADER::need_update_best_hint:1` 비트 제거, `reserved_bits` 30→31, **온디스크 크기 불변**) |
| PSTAT 카운터 | **8개 전부 삭제** — `PSTAT_HEAP_STATS_SYNC_BESTSPACE`, `PSTAT_HF_NUM_STATS_ENTRIES`, `PSTAT_HF_NUM_STATS_MAXED`, `PSTAT_HF_BEST_SPACE_ADD/DEL/FIND`, `PSTAT_HF_HEAP_FIND_PAGE_BEST_SPACE`, `PSTAT_HF_HEAP_FIND_BEST_PAGE` |
| `shard::m_stats` | `request`/`advance_shard`/`fetch_L3`/`fetch_L2`/`fetch_L1`/`found`/`allocated` 7개 원자 카운터 + `enabled` 게이트. **`get_stats()`로만 읽을 수 있고 SHOW/PSTAT 노출 경로가 없다** |

> **재작성 필수 개선.** PSTAT 8개를 지우고 대체 관측 수단을 노출하지 않은 것은 운영 관점에서 후퇴다. Acceptance A5(§1.5)를 검증하려면 `shard::m_stats`를 **`SHOW HEAP HEADER` 또는 신규 PSTAT으로 반드시 노출해야 한다.** 리뷰 F2도 "shard별 request/found/allocated 분포를 검증해야 한다"고 요구한다.

---

## 6. 구현 순서 제안

`04 §4`의 R0~R7을 기반으로 하되, **§7의 결함 9건과 `04`의 함정 18건을 처음부터 반영하도록 재배열**했다. 실제 PR과의 차이를 먼저 요약한다.

| | 실제 (PR #7353) | 본 스펙 |
|---|---|---|
| 온디스크 포맷 확정 | 3회 변경 | **P0에서 1회 확정 + 버전 필드 + `static_assert`** |
| 디스크 호환성 정책 | **결정하지 않음** (§7 D1) | **P0의 게이트 항목** |
| shard 시작점 분산 | 초기에 있었다가 `2c7071fd` 이후 소실 (§7 D2) | **P2에서 도입 + P8에서 계측 검증** |
| 과소-stale 자가치유 | 없음 (§7 D5) | **P0에서 정책 결정, P3에서 구현** |
| 페이지 유효성 판정 | 없음 → CBRD-27120 (§7 D9) | **P0에서 규약 결정, P4에서 구현** |
| 레거시 제거 시점 | 전체의 60% 지점 | **P1에서 격리, P6에서 제거** |
| 유닛 테스트 | 도입 후 삭제, 미복구 | **P2부터 끝까지 유지** |
| 주변 서브시스템 스윕 | 산발적 | **P7에서 체크리스트 전수** |

### P0 — 계약·포맷·호환성 동결 (신규 코드 0줄)

**이 단계를 리뷰받기 전에 코드를 쓰지 않는다.** 여기서 내리지 않으면 나중에 전면 재작업이 되는 결정들이다.

| # | 결정 항목 | 예방 대상 |
|---|---|---|
| 0-1 | **온디스크 레이아웃 최종안** — `HEAP_HDR_STATS` 필드·오프셋, `HEAP_CHAIN` 플래그 비트 배분, shard 페이지 슬롯 구성, candidate 배열 위치/크기. **버전 필드를 넣을 것.** | D1, `04 T3` |
| 0-2 | **디스크 호환성 정책** — `rel_disk_compatible()` bump(11.5f → 11.6f)로 구 DB를 명시적으로 거부할 것인가, 아니면 헤더 버전 필드 + 마이그레이션을 제공할 것인가. **셋 중 하나를 반드시 고른다.** | **D1** |
| 0-3 | **shard 페이지를 heap VFID에 둘 것인가, 별도 VFID에 둘 것인가** — **D-25의 표를 채워 문서로 남긴다.** 함정 **T3 / T10 / T14가 전부 이 하나의 결정에서 파생**되므로, ①(원본대로)을 고르더라도 근거를 명시하고 P7 스윕을 필수 단계로 승격시킨다 | `04 T3` / `T10` / `T14` 부류 전체 |
| 0-4 | **`sizeof(HEAP_HDR_STATS)` 의존 지점 전수 조사.** 최소한 `heap_Maxslotted_reclength` 산정 | `04 T3` |
| 0-5 | **페이지 유효성(allocated) 판정 규약** — `MAYBE_DEALLOCATED` fix만으로는 rollback postpone 중인 페이지를 걸러낼 수 없다. `HEAP_CHAIN` 플래그를 추가할 것인가? | **D9 (CBRD-27120)** |
| 0-6 | **과소-stale L1 자가치유 정책** — FS3 게이트를 유지할 것인가, epoch 기반 강제 재검증을 넣을 것인가, resident 페이지의 L1을 직접 갱신할 것인가 | **D5** |
| 0-7 | **shard 시작점 분산 규약** — `thread_ref.index % num_shards` + `tran_index % L2_FANOUT`. **API 시그니처에 명시적으로 넣는다** | **D2** |
| 0-8 | **recovery index 번호 예약** + HA 화이트리스트 비침투 확인 (`log_manager.c`, `log_applier.c`) | D-14 |
| 0-9 | **시스템 파라미터 확정** — `bestspace_shard_count` 범위, sync 주기 파라미터화 여부, `max_bestspace_entries` obsolete 처리 | `04 T2` |
| 0-10 | **estimates 감소 경로 유무** — DELETE/vacuum이 `num_recs`를 줄일 것인가, 아니면 full-scan만이 재설정할 것인가 | **D6** |
| 0-11 | **레코드 배치 변경의 QA 영향 사전 공지** — 헤더 크기 증가 + shard 페이지 삽입으로 페이지 오프셋과 OID 배치가 바뀐다 | **D8** |

*근거:* 실제 PR에서 온디스크 포맷이 3번 바뀌었고 그때마다 파생 상수(T3)와 스캐너 가드(T10)가 깨졌다. 그리고 0-2·0-5·0-6은 **PR에서 아예 결정되지 않아 머지 후 회귀로 터졌다.**

### P1 — 레거시 격리 (제거는 아직 아님)

구 bestspace(`heap_Bestspace` 전역 캐시, second-best 링, `heap_stats_*` 함수군)를 **하나의 인터페이스 뒤로 밀어 넣는다.** 신규 구현은 이 인터페이스만 교체하면 되도록.

동시에 **제거 대상 목록만 확정한다**(삭제는 P6):

- PSTAT 카운터 8개 (§5.7) — **단, 대체 관측 수단을 P5에서 넣기로 함께 확정한다**
- SHOW 컬럼 14개
- `SPAGE_HEADER::need_update_best_hint` 비트와 `spage_set_need_update_best_hint()`
- 파서 예약어 `RESERVED_P_UPDATE_BEST`, `HEAP_PAGE_INFO_UPDATE_BEST`
- 죽은 코드: `heap_stats_get_bestspace_by_vpid`, `heap_stats_quick_num_fit_in_bestspace` (`ENABLE_UNUSED_FUNCTION`)
- `HEAP_STATS_PREV_BEST_INDEX` 매크로 끝의 세미콜론 (`01 §2.3`)
- `vacuum.c`의 `prev_freespace = 0` 트릭과 "will be refactored right away" 주석 (`01 §10-12`)

### P2 — 인메모리 자료구조 + 유닛 테스트

L1/L2/L3 계층, shard, registry, candidate 큐.

**레이아웃 상수를 처음부터 최종값으로 둔다** — `L3_FANOUT=8`, `L2_FANOUT=8`, `ALLOC_BATCH_SIZE=4`, tier 임계값, **allocating 비트를 L3에서 분리한 상태로 시작**. 실제 PR은 `a8482a6e6`에서 fanout 7→8로 바꾸며 유닛 테스트 964라인을 재작성했고 그 테스트는 곧 삭제되어 복구되지 않았다.

**이 단계의 유닛 테스트를 끝까지 유지한다.** L1/L2/L3 계층은 CUBRID에서 드물게 순수 단위 테스트가 가능한 코드다.

API 시그니처를 처음부터 갖춘다:
- **`enum find_purpose { INSERT_NEW, RELOCATE, ... }`** (bool `is_newrec`보다 낫다 — D-19 권고)
- `needed_size` / `consume_size` / `record_length` 3분리 (D-18)
- **`shard`/`bias` 시작점을 인자로 받는다** (P0-7) — 기본값 0으로 두지 말 것

계약을 **코드 주석에 명시**한다:
- **"요약 계층(L2/L3)은 후보를 좁히기만 하고, 정확성은 L1이 페이지를 fix해 보장한다"** (I-1, → `04 T9` 예방)
- **"엔트리에 기록된 free space는 힌트이며 사실이 아니다"** (I-1, → `04 T13` 예방)
- **"`L2::find`/`L3::find`는 정확히 그 tier만 반환한다"** (I-3)

### P3 — heap 연결

heap 파일 생성 훅, 삽입 경로 전환, victim/candidate/신규할당 3단 폴백.

**candidate 큐의 의미를 "새로 추적할 페이지 목록"이 아니라 "free space가 변한 페이지 알림"으로 정의한다.** 그러면 resident 갱신(`04 T12`)이 특수 케이스가 아니라 기본 동작이 되고, **§7 D5의 자가치유 경로가 자연스럽게 생긴다.**

`heap_add_bestpage`류 **힌트 경로**와 `heap_find_bestpage`류 **수요 경로**를 별도 함수로 분리한다 (`04 T15` 예방). 힌트 경로는 대상 부재 시 무거운 초기화를 유발하지 않되, **P0-6에서 정한 방식으로 힌트를 보존한다** (§7 D3).

### P4 — 온디스크 영속화

P0-1에서 확정한 레이아웃대로 구현. **처음부터 `pgbuf_ordered_fix`만 사용한다** (`04 T7` 기반). 재구축 경로와 그 double-checked locking을 함께 만든다.

- **버전 필드 검사 + P0-2의 호환성 정책 구현** (§7 D1)
- **P0-5의 페이지 유효성 플래그 구현** (§7 D9)
- **`heap_page_is_bestspace()` 가드를 여기서 전수 삽입**하고 P0-4의 조사 목록을 체크리스트로 소진한다
- `static_assert(sizeof(HEAP_HDR_STATS) == ...)` 추가 (I-10)

### P5 — 통계·체크포인트·종료 훅 (한 단계로)

estimates의 shard별 atomic 분산, 주기 체크포인트, **그리고 같은 단계에서 종료 훅**(`xboot_shutdown_server`, 로그/버퍼 매니저 finalize **이전**). 실제 PR은 둘이 8커밋 떨어져 있었지만, 둘은 같은 요구사항("인메모리 상태를 잃지 않는다")의 두 면이다 (`04 T8`).

- 체크포인트는 **항상 페이지 획득 전에** 배치 (D-22, `04 T16`)
- **P0-10의 estimates 감소 경로 구현** (§7 D6)
- **§5.7의 shard 통계 노출** — `SHOW HEAP HEADER` 또는 신규 PSTAT. Acceptance A5의 전제
- **registry lifecycle 훅** — `heap_manager_finalize()`에 전체 registry reset + generation 증가를 추가한다 (§7 D4). 현재 `heap_manager_finalize`는 `heap_chnguess_finalize` / `heap_classrepr_finalize_cache` / `heap_finalize_hfid_table`만 부르고 **bestspace를 전혀 건드리지 않는다** (`heap_file.c@f30f1c260`, 직접 확인)

### P6 — 레거시 제거

P1의 목록을 소진한다. 폴백 인터페이스를 걷어내고 registry 키를 HFID 단독으로 확정한다.

### P7 — 주변 서브시스템 체계적 스윕

**P0-3에서 "heap VFID 안"을 골랐다면 필수이며 가장 지루하다.**

| 영역 | 확인 항목 |
|---|---|
| 통계 | `stats_update_statistics_internal`, `file_get_num_total_user_pages`(파티션 합산 포함), 히스토그램 샘플러 2곳 (`04 T10`) |
| 유틸리티 | compactdb (**SA / CS 양쪽**, `04 T14`), loaddb, unloaddb, checkdb, diagdb |
| DDL | `ALTER ... REORGANIZE PARTITION`(`redistribute_partition_data`), TRUNCATE(`heap_reuse`), 인덱스 빌드 |
| 백그라운드 | vacuum (**전제 조건 확인 포함** — TDE 키 로드 여부, `04 T11`), 병렬 스캔(`px_scan`), external sort |
| 복구/HA | recovery index 화이트리스트, 로그 어플라이어, **supplemental/CDC 로그의 LSA 기록이 성공 확인 이후인지** (`04 T6`) |
| 스캔 | `heap_get_num_objects`, `heap_get_capacity`, `heap_next_internal`, `heap_page_next/prev`, `heap_chkreloc_next` |

전수 목록 생성 명령: `grep -rn "file_get_num_user_pages\|heap_vpid_next\|spage_next_record" src/`

### P8 — 회귀·성능 검증 게이트

§8 전체. **여기를 통과하지 못하면 머지하지 않는다.** 실제 PR은 이 게이트 없이 머지되어 §7의 9건이 머지 후에 발견됐다.

---

## 7. 알려진 결함과 개선 요구

리뷰 Findings 4건 + `03` 실측 이슈 5건 + JIRA 머지 후 회귀 4건 = **원시 13건**을 중복 병합해 **9건**으로 통합했다.

### 7.1 통합 결함 표

| ID | 결함 | 원시 출처 (병합) | 증거 | 심각도 | 재작성 시 예방 설계 |
|---|---|---|---|---|---|
| **D1** | **구 DB 이미지 비호환** — `HEAP_HDR_STATS`가 296 B → 1,152 B로 바뀌었는데 `disk_compatibility_level`은 `11.5f` 그대로. `heap_build_bestspace`가 `assert(recdes.length == sizeof(HEAP_HDR_STATS))` 후 그대로 cast한다. 릴리스 빌드에서는 짧은 레코드 **밖의** 값을 `num_shards`, metadata VPID로 읽는다 | 리뷰 **F1** + JIRA 호환성 사고 (youngjinj, 2026-07-24) | `release_string.c:105@f30f1c260`(직접 확인). TPC-C에서 `ERROR CODE = -13 … reading page 1634 of volume "(null)" … Bad file descriptor`, 콜스택 `heap_alloc_new_pages ← allocate_new_pages ← allocate_verify_or_allocate`. tpmC 54,754 → **2,110**. 작성자 확인: "bestspace도 디스크 이미지를 변경하였기 때문에 재생성이 필요합니다" | **Blocking** | **P0-2에서 세 정책 중 하나를 확정.** ① `rel_disk_compatible()` bump(11.5f→11.6f) → 구 DB를 명시적 에러로 거부 ② `HEAP_HDR_STATS`에 **버전 필드**를 두고 구 레이아웃을 읽어 마이그레이션 ③ 별도 마이그레이션 유틸. **어느 쪽이든 `static_assert(sizeof(HEAP_HDR_STATS)==N)`과 런타임 버전 검사를 함께 넣는다.** 현재의 `assert(recdes.length == ...)`는 디버그에서만 잡히고 릴리스는 그대로 읽는다 |
| **D2** | **shard/bias 시작점 고정** — 모든 요청이 `shard = 0; bias = 0;`에서 출발해 분산 설계가 무력화된다. 초기 구현은 `thread_ref.index % SHARD_COUNT`와 transaction index를 썼는데 커밋 `2c7071fd`(unfill 계산 추가) 때 둘 다 0이 되었다 | 리뷰 **F2** + `03` 실측 **#1** | `bestspace.cpp:1360-1361@f30f1c260`(직접 확인). 실측: `find/FOUND` 4,008건 중 **shard0=4,001 / shard1=6 / shard2=1**. `L1/probe` 76,314회(≈19회/INSERT) — bias 고정이라 모두가 같은 순서로 같은 stale 엔트리를 재확인 | **Blocking** — Acceptance("부하 분산") 직접 위반 | **P0-7에서 규약 확정, P2에서 API 인자로 도입.** `shard = thread_ref.index % m_shards.size()`, `bias = tran_index % L2_FANOUT`. **`find()` 내부에서 0으로 하드코딩할 수 없도록 시그니처에서 강제한다.** 그리고 §5.7의 shard 통계를 노출해 **P8에서 분포를 수치로 검증**(A5) |
| **D3** | **registry 미등록 시 힌트 전량 유실** — `heap_add_bestpage`가 lookup-only(`class_oid=NULL`)로 조회하므로, in-memory bestspace가 없으면 후보를 조용히 버린다. 재시작 직후 INSERT보다 vacuum/DELETE가 먼저 오면 회수 정보가 전부 사라진다 | 리뷰 **F3** + `03` 실측 **#2** | `heap_file.c:4625-4629@f30f1c260`(직접 확인). 실측: 서버 재시작 후 VACUUM 실행 시 `reg/miss` 37회, `heap/add_bestpage`·`cq/push` **0회** — **37건 전부 유실** (`03 §7.2`) | High | **P0-6/P3.** ① **seed 보존**: registry에 HFID별 소형 pending 링버퍼를 두고 bestspace 생성 시 흡수 ② **헤더 fallback**: 레거시 `heap_stats_update_internal`처럼 헤더를 **CONDITIONAL** latch로 잡아 on-disk `candidates[]`에 직접 append(실패 시 포기) ③ **rebuild 시 부분 스캔**: shard 페이지 스냅샷만 믿지 말고 `last_vpid` 부근을 조금 훑는다. **②가 가장 적은 코드로 가장 확실하다** — 조건부이므로 INSERT 핫패스를 막지 않고, on-disk candidate 배열은 이미 존재한다 |
| **D4** | **registry lifecycle 훅 부재** — `bestspaces`는 프로세스 전역이고 destructor는 프로세스 종료에서만 실행된다. `heap_manager_finalize()`에 reset/destroy-all 훅이 없다. SA_MODE에서 DB A를 닫고 같은 프로세스가 DB B를 열어 **숫자 HFID를 재사용**하면 `find()`가 이전 DB의 객체를 반환할 수 있다(stale VPID / estimates / unfill / shard 구성이 넘어간다) | 리뷰 **F4** | `heap_manager_finalize` 본문 직접 확인 — `heap_chnguess_finalize` / `heap_classrepr_finalize_cache` / `heap_finalize_hfid_table`만 호출, bestspace 언급 없음 | Medium (SA_MODE 다중 DB 시 High) | **P5.** `heap_manager_finalize()`에 **registry 전체 reset + `m_generation` 증가**를 추가한다(generation 증가가 있어야 TLS 엔트리도 무효화된다). 또는 **"SA_MODE 다중 DB lifecycle 미지원"을 명시적 불변식으로 문서화**하고 `assert`로 강제. 리뷰 Question 3이 정확히 이 선택을 묻는다 |
| **D5** | **과소-stale L1 자가치유 불가 → freed 공간 미재사용(heap bloat) + 반복 헛 probe** — I-4의 비대칭. 기록값이 실제보다 **작으면** 사전 검사에서 탈락해 페이지를 fix하지 않으므로 교정 계기가 없다. 30초 sync는 in-memory→disk 방향이라 도움이 안 된다. vacuum이 회수한 공간은 `heap_add_bestpage`의 **FS3(25%) 게이트**를 통과해야만 후보가 되는데, D3와 겹치면 아예 등록조차 안 된다 | `03` 실측 **#3** + JIRA heap bloat 회귀 (Won-ryong song, 2026-07-23) | 실측: vacuum 직후 60행 INSERT에서 매번 stale 엔트리 6개(`rec_fs=1688/1744 < needed=1766`)를 헛 probe한 뒤 꼬리 페이지 사용 (`03 §7.3`). **`repro_clean.sh` 결과: 정상 `init=41, delta ≤ 13` → 회귀 빌드 `init=41, latest≈100~118, delta≈60~80`.** **작성자가 버그로 인정:** "vacuum이 작업한 페이지를 모두 재사용하지 않고 조건에 따라 재사용하게 하였는데, 이 과정에서 발생한 버그로 확인하였습니다. 수정하겠습니다." (hong yechan, 2026-07-23) | **Blocking** — 원본 TC 허용치(+13)를 5배 초과 | **P0-6에서 정책 결정, P3에서 구현.** 후보 조합: ① **FS3 게이트 재검토** — 25%는 레거시 30%보다 낮지만 여전히 "조금 비운 페이지"를 버린다. 게이트를 낮추거나 **"L1에 이미 resident인 페이지는 게이트 무관 무조건 갱신"** 으로 예외 ② **candidate 큐의 의미를 "free space가 변한 페이지 알림"으로 재정의**(P3) — resident면 pop 없이 즉시 L1 CAS 갱신 ③ **L1 슬롯에 last-verified epoch를 두고**, tier 탐색에서 연속 실패한 슬롯을 주기적으로 강제 재검증(`force_check=true` 경로 재활용). **②가 근본 해법이고 ①이 즉효약이다** |
| **D6** | **estimates 단조 증가** — DELETE/vacuum이 `num_recs`/`recs_sumlen`을 줄이지 않는다. `subtract_estimates`는 rebuild 시 `set_estimates` 외에 호출자가 없다. 옵티마이저가 보는 값은 "삽입 누계" 힌트가 된다 | `03` 실측 **#4** | 2,000행 DELETE 후에도 `est(recs=4000)` 유지, 30초 sync가 그 값을 그대로 디스크에 기록: `heap/disk-sync … est(pages=48 recs=4000 sumlen=524832)` (`03 §7.4`) | Medium | **P0-10에서 정책 결정, P5에서 구현.** ① **감소 경로 추가** — `heap_delete_physical`이 `add_estimates(0, -1, -len)`을 호출(원자 `fetch_sub`이므로 비용은 무시할 수준). 단 D-20의 "과대추정 선호" 원칙과 충돌하지 않게 **하한 0 클램프**를 둔다 ② **full-scan 재설정 주기 명시** — `heap_update_statistics`/`UPDATE STATISTICS`만이 재설정한다면 그 사실을 문서화하고 옵티마이저 측 기대치를 맞춘다. **①을 권장한다** — 레거시도 감소 경로가 없었지만 `heap_stats_sync_bestspace`가 스캔 중 실측으로 덮어써서 자연 보정됐는데, 신 설계에는 그 스캔 자체가 없다 |
| **D7** | **tier 경계 낭비** — 같은 tier 안에서 "요청보다 약간 작은" 페이지들을 매번 probe한다. tier가 범위이므로 색인만으로는 걸러지지 않는다 | `03` 실측 **#5** | `needed=1766`(FS1) vs `rec_fs=1688`(FS1)이 반복 probe (`03 §7.3`) | Low (D5와 함께 나타나면 증폭) | **P2.** ① `L1_find`의 사전 검사는 이미 존재하므로 **페이지 fix는 발생하지 않는다** — 낭비는 원자 load 수준이고 실측 19회/INSERT는 대부분 D2(bias 고정) 탓이다. **D2를 고치면 대부분 해소된다** ② 추가 개선: L2 비트맵 갱신 시 "이 tier 안에서 하위 절반"을 별도 비트로 두는 것은 **비용 대비 효과가 낮다**(8바이트 제약). ③ 실용적 대안: **연속 실패 슬롯을 bias에서 잠시 제외**하는 per-thread 소형 negative cache. **[추정]** 측정 없이는 도입하지 말 것 |
| **D8** | **레코드 물리 배치 변경으로 HA/shell TC 다수 실패** — 헤더 레코드가 커지고(296→1,152 B) shard 페이지가 체인 앞머리에 삽입되면서 페이지 오프셋과 OID 배치가 전부 밀렸다. 순서에 의존하는 TC가 깨진다 | JIRA HA TC 실패 (sion yun, 2026-07-23 / hong yechan, 2026-07-24·25) | 실패 TC: `issue_6214_6`, `issue_6214_7`, `bug_bts_17256`(checksum 동일, **순서 변경**), `cbrd_26374_ha`(**헤더 레코드 크기가 커지며 offset이 일정 간격 밀림**), `issue_6214_3`(t0가 마지막 페이지로 밀려 제한 시간 내 checksum 미생성 — `diagdb` 확인 결과 `0|208: t5,t6,t7,t9 / 0|209: t1,t2,t3,t4,t8 / 0|210: t0`), `cbrd_25837`(3,000행 SELECT 결과 순서 변경 — 작성자 확인 "bestspace 재설계로 인한 것이 맞습니다. 전체적인 데이터 layout이 변경되었습니다") | Medium — **기능 결함이 아니라 TC 계약 위반** | **P0-11에서 사전 공지 + P8에서 TC 수정 PR을 본 PR과 동시 진행.** 순서 의존 TC는 **본질적으로 잘못된 TC**이므로 `ORDER BY` 추가로 고쳐야 하지만, **레이아웃을 바꾸는 쪽이 목록을 만들 책임이 있다.** 추가로 `cbrd_26374_ha`처럼 **오프셋에 의존하는 TC**는 헤더 크기 증가폭을 미리 알려야 수정 가능하다. **헤더를 1,152 B까지 키우는 대신 candidate 배열을 shard 페이지로 옮겨 헤더 증가를 최소화하는 대안을 P0-1에서 검토하라** — 그러면 이 부류가 크게 줄어든다 |
| **D9** | **rollback deallocate 경합 → vacuum 무한루프 (CBRD-27120)** — T1이 INSERT로 페이지를 할당하고 bestspace에 등록한 뒤 rollback하면 페이지 dealloc이 postpone으로 등록된다. 그 사이 T2가 bestspace에서 그 페이지를 찾아 `OLD_PAGE_MAYBE_DEALLOCATED`로 fix하는데 **아직 dealloc 전이라 정상 fix되고 내용도 멀쩡해 보인다.** T2가 INSERT한 뒤 T1의 rollback이 완료되어 페이지가 dealloc되면, vacuum이 그 페이지를 처리하려다 실패하고 **무한 재시도**한다 | JIRA vacuum 무한루프 (sungjoon kim, 2026-07-24) + **CBRD-27120** | pstack: `vacuum_heap() → vacuum_heap_page() → pgbuf_fix_release()`에서 `ERROR CODE = -17: Internal error: fetching deallocated pageid 8195 of volume db_4523` 무한 반복. **CPU 100% 지속, 5초 사이 에러로그 47,691줄 증가(파일 360MB+)**, 다른 트랜잭션의 postpone 처리까지 지연되어 테스트 전체 hang. 실패 TC: `longcase/shell/other/bug_bts_4523/cases/bug_bts_4523.sh`. **`f30f1c260` 시점에 수정이 아직 반영되지 않았다** — `heap_file.c:220-229@f30f1c260`에 `HEAP_PAGE_FLAG_BESTSPACE`와 vacuum 상태 비트만 존재(직접 확인) | **Blocking** | **P0-5에서 규약 결정, P4에서 구현.** CBRD-27120의 계획된 해법: **"`HEAP_CHAIN`에 flag를 추가하여, page fix 시 flag로 유효한 페이지인지 검사한다."** 재작성 시 이를 **처음부터** 넣는다. 설계 원칙: **`OLD_PAGE_MAYBE_DEALLOCATED` fix 성공은 "페이지가 유효하다"를 뜻하지 않는다** — I-1의 소유권 검증 단계(`ptype == PAGE_HEAP` + `class_oid` 일치)에 **"현재 allocated 상태인가"를 반드시 추가**해야 한다. 대안: bestspace 등록을 **커밋 이후로 지연**(postpone-safe)하는 방법도 있으나 신규 페이지 즉시 재사용 이득이 사라진다 |

**병합 내역:** F1 ≡ JIRA 호환성 사고 → D1 · F2 ≡ 03#1 → D2 · F3 ≡ 03#2 → D3 · F4 → D4 · 03#3 ≡ JIRA heap bloat → D5 · 03#4 → D6 · 03#5 → D7 · JIRA HA TC → D8 · JIRA vacuum 무한루프 ≡ CBRD-27120 → D9.

### 7.2 보조 개선 후보 (비차단)

리뷰·Greptile 스레드·`02`/`04`에서 나온 "거친 부분"이다. 재작성 시 함께 정리한다.

| # | 항목 | 근거 | 조치 |
|---|---|---|---|
| S1 | `heap_file.c:4479`가 `ENTRIES_PER_SHARD` 대신 **리터럴 `64`를 두 번** 사용. 조건식은 상수를 쓴다 → 상수를 바꾸면 버퍼 경계 초과 | `f30f1c260` 직접 확인 | 상수로 교체. `grep -n "\* 64"` 를 CI 체크에 추가 검토 |
| S2 | `HEAP_HDR_STATS`에 크기 `static_assert`가 **없다.** `heap_file.c`/`.h` 전체에 `static_assert`가 하나도 없다 | `02 §4.1` | 추가 (I-10). D1의 조기 발견 수단 |
| S3 | on-disk 구조체에 `std::size_t` 사용 — 플랫폼 이식성 | Greptile (작성자는 동일 플랫폼 전제로 답변, bot 철회) | **고정 폭 타입(`uint64_t`)으로 교체 권장.** on-disk 구조체에 `size_t`를 쓸 이유가 없다 |
| S4 | `for_each`가 registry mutex를 **잡은 채 page I/O** 수행 | Greptile (shutdown-only precondition 설명 후 철회, **precondition 문서화 권장**) | 함수 주석에 "shutdown 단일 스레드 전제"를 명시하고 `assert`로 강제 |
| S5 | **체크포인트 주기 30초가 하드코딩 `constexpr`** — `UPDATE_TIME_THRESHOLD`, 함수 지역 상수(`bestspace.cpp:1312@f30f1c260` = 커밋 시점 `:1312`, 직접 확인). **튜닝 파라미터가 없다.** bestspace 관련 파라미터는 `PRM_ID_BESTSPACE_SHARD_COUNT`와 `PRM_ID_DEBUG_BESTSPACE` 둘뿐이며 어느 쪽도 주기를 바꾸지 않는다. 워크로드에 따라 30초는 너무 길거나(crash 시 유실 폭) 너무 짧다(헤더 latch 왕복 빈도) | `04 M4 갭`; 직접 확인 | **P0-9에서 노출 여부를 결정한다.** 노출한다면 `PRM_FOR_SERVER`, 하한을 0(비활성)이 아닌 양수로 두고 shutdown 훅과의 관계를 문서화. 노출하지 않는다면 **30초를 고른 근거를 주석으로 남길 것** — 현재는 근거 주석조차 없다 |
| S6 | **유닛 테스트가 도입 후 삭제되어 복구되지 않음** — `unit_tests/bestspace/`가 `eabbf4bcf`에서 655줄로 도입 → `a8482a6e6`에서 964줄로 재작성 → **`cc40a2a13`에서 통째로 삭제**. 현재 트리에 디렉터리가 **존재하지 않음**(직접 확인) | `04 M1`, `R2`; 직접 확인 | **§8.2 U0 — P2에서 새로 쓰고 끝까지 유지.** G2 게이트가 디렉터리 부재를 실패로 판정 |
| S7 | `heap_add_bestpage`의 `prev_freespace`가 **받기만 하고 쓰이지 않음** ("leave this for future feature") | `f30f1c260` 직접 확인 | 제거하거나 D5의 자가치유에 실제로 활용 |
| S8 | `heap_update_bestspace`에서 `num_pages`만 `MAX()`, 나머지는 덮어쓰기(비대칭) | `02 §5.4` | 주석으로 근거 명시(현재도 있음). 유지 가능 |
| S9 | `set_estimates`의 read-then-subtract race로 **과대추정 잔존** | `02 §2.8` | 의도된 것. 주석 유지 |
| S10 | 슬롯 오버헤드 이중 계산 후보 — `consume_size = size + SPAGE_SLOT_SIZE`를 `spage_max_space_for_new_record()`(이미 슬롯 공간 차감) 결과와 비교 | 리뷰 Review Notes (`origin/develop`도 동일해 회귀로 분류 안 함) | tier 경계/페이지 성장 테스트로 별도 검증할 개선 후보 |
| S11 | `heap_get_num_objects`가 `scan_all=true`로 **제한 없는 전체 스캔** (레거시) | `01 §10-17` | 신 설계에서 `heap_update_statistics` 경로로 대체됐는지 P7에서 확인 |
| S12 | PSTAT 8개 삭제 후 **대체 관측 수단 미노출** | §5.7 | P5에서 `shard::m_stats` 노출 (A5 전제) |

---

## 8. 검증 계획

### 8.1 게이트 구조

| 게이트 | 내용 | 통과 기준 |
|---|---|---|
| **G1 정적** | 빌드(debug/release), `static_assert` 세트, 코드 스타일, cppcheck, memory_wrapper 검사 | 무경고 |
| **G2 단위** | `unit_tests/bestspace/` **복원 + P2부터 유지** (§8.2) | 전항목 pass. **디렉터리가 존재하지 않으면 게이트 실패로 간주** |
| **G3 기능 회귀** | CircleCI sql / medium / shell + HA shell | 신규 실패 0. **D8 관련 TC는 사전 수정 PR과 동시 머지** |
| **G4 결함 재현** | §8.3의 D1~D9 재현 테스트 | 전항목 pass |
| **G5 성능** | §8.4 | §1.4 수치 재현 + A5 분포 |

### 8.2 단위 테스트 (G2) — **`unit_tests/bestspace/` 복원**, P2부터 끝까지 유지

> **선행 작업 U0 — 삭제된 유닛 테스트 복원.** `unit_tests/bestspace/test_bestspace.cpp`는 커밋 **`eabbf4bcf`("implement the bestspace registry and add stats for debug")에서 655줄로 도입**됐다가, `a8482a6e6`(fanout 7→8)에서 964줄 규모로 재작성됐고, **커밋 `cc40a2a13`("pick victim pages and replace them with selected or allocated candidates")에서 통째로 삭제된 뒤 PR 종료까지 복구되지 않았다.** 현재 트리에 bestspace 유닛 테스트는 존재하지 않는다.
>
> 재작성에서는 이것을 **되살리는 것이 아니라 P2에서 처음부터 다시 쓰고 끝까지 유지한다.** 근거 두 가지:
> - `04 R2`: "순수 인메모리 자료구조는 CUBRID에서 드물게 **단위 테스트하기 쉬운 코드**이므로 버리기 아깝다."
> - 삭제의 직접 원인은 **레이아웃 상수가 늦게 확정된 것**(fanout 7→8)이었다. §6 P2가 상수를 최종값으로 못 박으므로 이 재작성 압력이 사라진다.
>
> CUBRID 유닛 테스트는 Catch2 v2.11.3 기반이며 `./build.sh -m debug -c "-DUNIT_TESTS=ON"`로 활성화한다. `unit_tests/AGENTS.md` 참조. 일부 모듈(`LOCKFREE`, `LOADDB`, `MEMORY_MONITOR`)이 컴파일 문제로 비활성화되어 있으므로, **신규 `BESTSPACE` 모듈이 그 전철을 밟지 않도록 CI에 실제로 등록됐는지 확인하라** — 리뷰 리포트는 "로컬 ctest에는 등록된 test가 없었다"고 기록하고 있다.

| # | 대상 | 검증 내용 |
|---|---|---|
| U1 | `size_to_tier` | 경계값 전수 — `{0, 1310, 1311, 2621, 2622, …, 13926, 13927, DB_PAGESIZE}`. `FS0 = -1` 확인. `DB_PAGESIZE` 4K/8K/16K 세 값에서 |
| U2 | `bitmap` | `set`/`clear`/`empty`/`find` 8비트 전수 |
| U3 | `L2::clear(index)` | `0x0101010101010101ULL << index` 마스크가 **모든 tier에서** 해당 비트를 지우는지 |
| U4 | `L2::find`/`L3::find` | **"정확히 그 tier만"** 반환 확인 (I-3). 이상(以上)을 반환하면 실패 |
| U5 | `L2_update`/`L3_update` 재확인 루프 | L1을 CAS 도중 바꾸는 스레드를 붙여 **낡은 요약이 남지 않는지** (I-2) |
| U6 | `candidate_queue` | 오름차순 불변식, 중복 VPID 제거, 정원 초과 시 최악 축출, `pop`의 3/4개 분기, `to_entries` **역순** |
| U7 | `registry` | TLS 캐시 히트/미스, generation 무효화, LRU 40개 초과 시 꼬리 재활용, `destroy(VFID)` 드레인 |
| U8 | estimates | `add`/`subtract`/`get`(누산)/`set`(store-then-subtract) 조합. **감소 경로(D6) 도입 시 하한 0 클램프** |
| U9 | 레이아웃 | 모든 `static_assert`가 4K/8K/16K, 32/64비트 빌드에서 성립 |
| U10 | **shard 시작점 분산 (D2)** | 서로 다른 `thread_ref.index`가 서로 다른 shard로 매핑되는지 |

### 8.3 결함 재현 테스트 (G4) — **리뷰 Test Gaps 5건 전부 포함**

| ID | 시나리오 | 절차 | 통과 기준 | 출처 |
|---|---|---|---|---|
| **T-D1** | **업그레이드/호환성** | 구 바이너리(`b63fbc5dc`)로 DB 생성 + 데이터 적재 → **새 바이너리로 기동** → 첫 INSERT / `UPDATE STATISTICS` / `compactdb` | P0-2 정책대로: **거부 정책이면 명확한 에러**, **마이그레이션 정책이면 정상 동작**. 릴리스 빌드에서 **쓰레기 값을 읽지 않을 것** | 리뷰 Test Gap 1, Question 1 |
| **T-D2** | **shard 분포** | N(=8,16,32) 커넥션 × M행 동시 INSERT. `shard::m_stats`의 `request`/`found`/`allocated` 수집 | **A5**: 최다 shard의 `found` 비율 ≤ `2/S`. 참고 실측(원본): 4001/6/1 → **실패** | 리뷰 Test Gap 2, F2, `03 §6.2` |
| **T-D3** | **재시작 후 vacuum 우선** | 서버 재시작 → **INSERT 전에** DELETE + VACUUM으로 공간 회수 → 그 다음 INSERT | 회수된 페이지가 재사용되어야 한다. 원본: **후보 37건 전부 유실** | 리뷰 Test Gap 3, `03 §7.2` |
| **T-D4** | **SA_MODE 다중 DB lifecycle** | 한 프로세스에서 DB A 종료 → DB B 시작, **동일 numeric HFID 재사용 강제** | 이전 DB의 bestspace 객체가 반환되지 않을 것. 또는 "미지원" 불변식이 `assert`로 걸릴 것 | 리뷰 Test Gap 4, Question 3 |
| **T-D5** | **heap bloat 회귀 — `repro_clean.sh`** | **CBRD-26176 코멘트(Won-ryong song, 2026-07-23)의 스크립트를 그대로 사용.** 10,000행 적재 후 `(DELETE 1000 / INSERT 1000) × 50`, 각 회차를 별도 csql 커넥션/트랜잭션에서. 반복 중 통계 조회를 넣지 말 것(증가폭이 완화된다) | **`delta = latest − init ≤ 13`** (원본 TC 허용치). 회귀 빌드 실측: `init=41, latest≈100~118, delta≈60~80` → **실패** | JIRA, `01`/`03` |
| **T-D6** | **estimates 감소** | 4,000행 INSERT → 2,000행 DELETE → 30초 대기 → `SHOW HEAP HEADER` / `heap_estimate` | P0-10 정책대로. 감소 경로를 도입했다면 `num_recs ≈ 2000` | `03 §7.4` |
| **T-D7** | **tier 경계 / 페이지 성장** | 각 tier 경계 ±1 바이트 크기의 레코드를 반복 INSERT하며 페이지 수 추이 관측 | 불필요한 신규 할당이 없을 것. S10(슬롯 오버헤드 이중 계산)도 여기서 검증 | 리뷰 Review Notes |
| **T-D8** | **레이아웃 의존 TC** | `issue_6214_3/6/7`, `bug_bts_17256`, `cbrd_26374_ha`, `cbrd_25837`, `cbrd_26486` | TC 수정 PR과 함께 pass. **수정 없이 pass하면 레이아웃이 안 바뀐 것이므로 별도 확인** | JIRA |
| **T-D9** | **rollback dealloc 경합 (CBRD-27120)** | `longcase/shell/other/bug_bts_4523/cases/bug_bts_4523.sh`. 수동 재현: T1이 INSERT로 페이지 할당(bestspace 등록) → rollback 개시 → T2가 그 페이지를 bestspace로 찾아 INSERT → T1 rollback 완료 → VACUUM | **vacuum 무한루프 없음.** 서버 에러로그가 폭증하지 않을 것(원본: 5초에 47,691줄) | JIRA, CBRD-27120 |
| **T-D10** | **crash 후 stale 힌트 정합성** | INSERT 중 `kill -9` → 재기동 → INSERT 계속 | 데이터 정합성 문제 없음. **불변식 I-1/I-4를 실제로 검증하는 테스트가 원본에 없었다** | 리뷰 Question 4 |

### 8.4 성능 검증 (G5)

| 워크로드 | 목표 | 비교 기준 | 비고 |
|---|---|---|---|
| **TPC-C** (BenchmarkSQL 5.0) | tpmC **+8% 이상** | AS-IS 대비 동일 환경 | §1.4. 측정자 주석대로 절대 수치는 환경 의존. **DB를 반드시 새로 생성할 것**(D1 사고 재발 방지) |
| **YCSB** INSERT 100% | **+80% 수준** | 동일 | §1.4 |
| **INSERT .. SELECT ..** | **약 3배** | 동일 | §1.4 |
| **동일 테이블 동시 INSERT** | 헤더 페이지 page-fix 대기 시간 **소멸** | CBRD-26858 §5-3의 검증 제언: "`PSTAT_HF_HEAP_FIND_PAGE_BEST_SPACE` 시간과 헤더 페이지 page-fix 대기 통계를 before/after로 비교" | 신 설계에서 해당 PSTAT은 삭제됐으므로 **대체 지표를 P5에서 노출**(S12) |
| **shard 분포** | A5 (§1.5) | — | T-D2와 동일 |
| **heap 성장률** | `delta ≤ 13` | — | T-D5와 동일. **성능과 공간을 함께 봐야 한다** — D-10(zero-wait)이 경합을 공간과 맞바꾸므로 |

### 8.5 계측 재현 절차

`03 §11`의 방법을 그대로 쓸 수 있다.

```
# 1) 계측 패치 (BSTRACE) 적용 — 원본은 f30f1c260 기준
git apply evidence/bstrace-instrumentation.patch     # BSTRACE_DIR 경로는 환경에 맞게 수정
# 2) 빌드/설치 (release 무방)
# 3) SA 단일:  csql -S -u dba <db> 로 create table + insert  → bstrace.<pid>.log
# 4) CS 동시:  cubrid server start <db>
bash evidence/gen_workload.sh 8 500 && bash evidence/run_multi.sh 8
#    → 서버 pid의 bstrace.<pid>.log에서 find/FOUND의 shard 분포, CONTENDED 집계
# 5) delete → (SA에서) vacuum → insert 로 D3/D5 재현
# 6) gdb 스택: 비계측 빌드에서 break heap_insert_logical / cubstorage::bestspace::find
```

계측 없이 관찰만 할 때: `SHOW HEAP HEADER OF <table>`, gdb로 `cubstorage::bestspaces` 전역 덤프, `diagdb`로 페이지별 OID 배치 확인(D8 진단에 사용된 방법).

### 8.6 머지 게이트 체크리스트

- [ ] G1~G5 전부 통과
- [ ] **D1~D9 9건 전부 해소 또는 명시적 wontfix + 근거 문서화**
- [ ] S1~S12 검토 완료
- [ ] **D-25(shard 페이지 VFID 배치) 결정이 문서로 남아 있고, ①을 골랐다면 P7 스윕 체크리스트가 소진됐다**
- [ ] **`unit_tests/bestspace/`가 존재하고 CI(ctest)에 실제로 등록되어 실행된다** — 원본은 테스트가 삭제된 채 머지됐고, 리뷰는 "로컬 ctest에는 등록된 test가 없었다"고 기록했다
- [ ] **레거시 정리 완료** — `vacuum.c`의 `prev_freespace = 0` 트릭 · `PRM_ID_HF_MAX_BESTSPACE_ENTRIES > 0` 게이트 · "will be refactored right away" 주석이 트리에 남아 있지 않다 (§5.2)
- [ ] testcase PR (`cubrid-testcases` / `cubrid-testcases-private`)이 **함께 머지 가능한 상태** — 원본 PR은 TC PR #2969·#3529가 open이라 `Check TC PRs`가 실패 상태에서 머지됐다 (리뷰 Merge gate)
- [ ] 성능 수치를 PR 본문에 첨부 — 리뷰 Test Gap 5: "JIRA acceptance인 다중 transaction INSERT 부하 분산과 성능 향상을 수치로 증명하는 신규 benchmark 결과가 PR에 없다"
- [ ] 디스크 호환성 정책이 릴리스 노트에 반영

---

## 부록 A. 원본 대비 변경 권고 요약

재작성이 원본과 **의도적으로 달라야 하는** 지점만 모았다.

| # | 원본 | 재작성 | 근거 |
|---|---|---|---|
| 1 | `shard = 0; bias = 0;` | `shard = thread_ref.index % N`, `bias = tran_index % 8`, **API 인자로 강제** | D2 |
| 2 | disk compat `11.5f` 유지 | **bump 또는 버전 필드 + 마이그레이션** | D1 |
| 3 | 힌트 경로에서 registry 미상주 시 **버림** | **seed 보존 또는 헤더 CONDITIONAL fallback** | D3 |
| 4 | `heap_manager_finalize`에 registry 훅 없음 | **reset + generation 증가 추가** | D4 |
| 5 | FS3 게이트 + 자가치유 없음 | **candidate = "free space 변경 알림"으로 재정의, resident L1 직접 갱신** | D5 |
| 6 | estimates 단조 증가 | **감소 경로 추가(하한 0 클램프)** | D6 |
| 7 | `MAYBE_DEALLOCATED` fix 성공 = 유효 | **`HEAP_CHAIN`에 allocated 플래그 추가, fix 후 검사** | D9 |
| 8 | PSTAT 8개 삭제, 대체 없음 | **`shard::m_stats`를 SHOW/PSTAT으로 노출** | S12, A5 |
| 9 | `bool is_newrec` | **`enum find_purpose`** | `04 T5(d)` |
| 10 | `class_oid == NULL 포인터` = lookup-only | **별도 함수 또는 enum 인자** | `04 T15(d)` |
| 11 | `HEAP_HDR_STATS` 크기 `static_assert` 없음 | **추가** | I-10, S2 |
| 12 | `heap_file.c`에 리터럴 `64` | **`ENTRIES_PER_SHARD`** | S1 |
| 13 | on-disk `std::size_t` | **`uint64_t`** | S3 |
| 14 | shard 페이지를 heap VFID 내부 체인에 (대안 미검토) | **D-25를 정식 결정 항목으로 채울 것** — T3/T10/T14의 공통 근원 | **D-25**, D-12, `04 T10(d)` |
| 15 | 30초 하드코딩 | **파라미터 노출 여부를 P0에서 결정** | S5 |
| 16 | 유닛 테스트 삭제됨 | **P2부터 유지** | S6 |
| 17 | 헤더 1,152 B (candidate 1KB 인라인) | **candidate를 shard 페이지로 옮겨 헤더 증가 최소화 검토** | D8 |

## 부록 B. 출처 인벤토리

| 출처 | 경로 / 식별자 | 이 문서에서의 역할 |
|---|---|---|
| 01 | `my-cubrid-docs/cbrd-26176/01-asis-legacy-bestspace.md` | AS-IS 구조, 병목 3층, 레거시 정리 대상 |
| 02 | `my-cubrid-docs/cbrd-26176/02-tobe-architecture.md` | TO-BE 자료구조/온디스크/동기화 상세, 상수 |
| 03 | `my-cubrid-docs/cbrd-26176/03-callflows.md` | 실측 call flow, 동시성 트레이스, 미해결 이슈 5건 |
| 04 | `my-cubrid-docs/cbrd-26176/04-commit-story.md` | 커밋 57개의 마일스톤 재구성, 함정 18건, 권장 순서 |
| 리뷰 | `my-cubrid-docs/cbrd-26176/PR-7353-report-codex.md` | Findings 1-4, Test Gaps 5건, Review Questions 4건, Greptile 스레드 |
| JIRA-1 | `CBRD-26176` | 요구사항, Acceptance, 머지 후 회귀 코멘트 19건, `repro_clean.sh`, 성능 수치 |
| JIRA-2 | `CBRD-26858` | 설계 티켓. Oracle/PG 조사 범위, **Joon Min의 헤더 X-latch 분석** |
| JIRA-3 | `CBRD-27120` | vacuum 무한루프 후속 이슈, 계획된 해법 |
| 코드 | `f30f1c260` 워킹트리 | 상수/시그니처/라인 번호 재검증 (본문의 `@f30f1c260` 표기) |
