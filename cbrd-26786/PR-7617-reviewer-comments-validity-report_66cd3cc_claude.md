# PR #7617 리뷰어 코멘트 타당성 검증 보고서 (H2SU · InChiJun)

**PR:** [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617) — [CBRD-26786] Reclaim empty OOS pages in vacuum via file_dealloc
**HEAD SHA:** `66cd3ccc564e50107b04cfe60770c00c53756ec3` (검증 시점 로컬 worktree 와 일치)
**작성일:** 2026-08-26
**대상:** H2SU 리뷰 1건 (2026-08-21, **APPROVED**), InChiJun inline 코멘트 2건 (2026-08-24, 미응답)
**제외:** greptile-apps[bot] 의 `std::bad_alloc` 스레드 — 작성자 답변 후 bot 이 지적을 철회하여 종결됨.

> **TL;DR** — 4건 모두 **타당**하며, 코드 레벨에서 재검증했다. 머지 블로커는 없다.
> ① H2SU 의 SA 모드 무한 증가는 실측 + 코드로 확인된 실제 한계지만 이 PR 이 명시적으로 스코프 밖에 둔 (주석으로 문서화한) 경로이므로 **후속 JIRA 티켓**으로 분리하는 것이 맞다.
> ② 관측성 공백은 기존 티켓 **CBRD-26871** 그대로이며 이 PR 이 원인이 아니다 — 다만 회수 검증 A/C 가 이 티켓에 의존하므로 우선순위 상향을 권장한다.
> ③④ InChiJun 의 래치 지적 2건은 모두 코드로 확인된 정확한 지적이고, 제안된 구조 변경 (레코드 루프 밖 배치 회수 + 2단계 빈 페이지 판정) 은 안전성 논증을 훼손하지 않으므로 **이 PR 에서 수용**을 권장한다.

| # | 리뷰어 | 요지 | 타당성 | 심각도 | 권장 조치 |
|---|--------|------|--------|--------|-----------|
| R1 | H2SU | SA/non-MVCC 경로는 회수가 없어 delete+재삽입 반복 시 볼륨 무한 증가 (실측 320→1024MB) | **확인됨** (실측+코드) | 중간 (SA 워크플로 한정) | 후속 티켓 분리; PR 은 현행 유지 |
| R2 | H2SU | `spacedb`/`diagdb` 가 OOS 공간을 못 봐서 R1 누수를 표준 도구로 진단 불가 | **확인됨** (기존 이슈) | 중간 (QA/운영) | CBRD-26871 우선순위 상향 |
| R3 | InChiJun | 회수가 heap home page WRITE latch 를 쥔 채 실행되고, dedupe 가 레코드 단위라 무력 | **확인됨** | 중간~높음 (동시성) | **이 PR 에서 수정** — 배치 hoisting 수용 |
| R4 | InChiJun | 비어 있지 않은 후보에도 OOS 헤더 WRITE latch + 파일 헤더 fix×2 비용을 전부 지불 | **확인됨** | 중간~높음 (insert 회귀 위험) | **이 PR 에서 수정** — 2단계 판정 + per-file 검사 hoisting 수용 |

---

## R1. [H2SU] SA 모드에서 빈 페이지 회수가 전혀 안 됨 — 볼륨 무한 증가

### 주장 요약

동일 바이너리 (`66cd3cc` debug) · 동일 워크로드 (비압축 랜덤 15KB 값 14,000행을 delete→재삽입 반복) 에서 물리 볼륨 크기 (`du`) 실측:

| 사이클 | SA 모드 | 서버 모드 (vacuum) |
|---|---|---|
| 최초 로드 | 320MB | 448MB |
| delete+재삽입 ×1 | **640MB** | 320MB |
| delete+재삽입 ×2 | **768MB** | 320MB |
| delete+재삽입 ×3 | **1024MB** | 320MB |

`heap_oos_delete_unreferenced` 의 non-MVCC 경로는 회수하지 않고 SA 에는 vacuum 이 없어, PR 이 AS-IS 로 지목한 무한 증가가 이 경로에 그대로 남는다는 주장.

### 검증 결과 — 확인됨 (측정과 코드가 일치)

- **회수 미연결은 의도된 설계다**: `heap_oos.cpp:699-704` 주석이 "Empty-page reclaim is deliberately NOT wired here" 라고 명시한다. 근거는 (1) 살아 있는 사용자 트랜잭션 안이라 abort 시 per-chunk undo 가 이미 dealloc 된 페이지에 청크를 되살릴 수 없고, (2) postpone 으로 미뤄도 같은 트랜잭션의 insert 가 커밋 전에 그 페이지를 다시 채울 수 있다는 것. 실제로 이 경로의 `oos_delete` 호출 (`heap_oos.cpp:768`) 은 `touched_vpids` 를 아예 넘기지 않아 회수 후보 수집조차 없다.
- **재사용이 bestspace 캐시에만 의존하는 것도 사실이다**: `oos_delete_chain` 이 청크 삭제 후 `oos_stats_update` 로 빈 공간을 캐시에 올리지만 (`oos_file.cpp:2439`), 캐시 상한은 `OOS_BESTSPACE_CACHE_CAPACITY` = 1000 엔트리 (`oos_file.cpp:110`), 헤더 best[] 는 10개, tier-3 sync scan 은 파일의 20% / 100 페이지 상한이다. 15KB 값은 페이지당 청크 1개꼴이므로 14,000행 삭제 = 약 14,000개의 빈 페이지 — 캐시 용량의 14배라, 재삽입 대부분이 캐시 미스 → `oos_file_alloc_new` 로 파일 확장. 실측 증가 곡선과 정합한다.
- **영향 범위**: SA_MODE 전체 (`csql -S` 관리 스크립트, compactdb 계열) 에 더해, 주석 (`heap_oos.cpp:688-690`) 이 밝히듯 `!is_mvcc_op` 게이트는 **SERVER_MODE 의 MVCC 비활성 클래스 (카탈로그)** 에도 발화한다. 이 삭제들은 vacuum 로그에 잡히지 않으므로 서버 모드에서도 해당 클래스의 빈 페이지는 영구히 회수되지 않는다 (카탈로그 레코드가 4,060B 타깃을 넘는 경우는 드물지만 0은 아니다 — 긴 view 정의 등).

### 판정

**타당한 실제 한계.** 단, 이 PR 이 도입한 회귀가 아니라 AS-IS 동작이 non-vacuum 경로에 잔존하는 것이고, PR Remarks 와 코드 주석에 스코프 제외로 문서화되어 있다. H2SU 도 이를 알고 APPROVED 를 준 것으로 읽는 것이 자연스럽다. **머지 블로커 아님.**

### 권장 해법

1. **후속 JIRA 티켓 분리** (예: "non-MVCC eager delete 경로의 OOS 빈 페이지 회수"). CBRD-26824 는 bestspace 재사용/sync scan 분석 티켓이라 이 건을 커버하지 않고, 별도 티켓이 없는 상태다. 설계 후보:
   - **(a) 커밋 postpone 기반 회수 (권장)**: `heap_oos_delete_unreferenced` 가 `touched_vpids` 를 수집해 트랜잭션 postpone (파일 파괴의 `file_postpone_destroy` 패턴) 으로 등록하고, postpone 실행 시 `oos_try_reclaim_empty_page` 를 호출. 주석의 반론인 "같은 트랜잭션 insert 가 커밋 전 재충전" 은 정확성 문제가 아니라 회수 기회 상실일 뿐이다 — `oos_try_reclaim_empty_page` 는 헤더 latch 아래에서 `spage_number_of_records () == 0` 을 재검증하므로 재충전된 페이지는 그냥 skip 된다 (멱등 + best-effort 계약 그대로). undo 불가 시점 (커밋 이후) 에 실행되므로 함수 주석의 안전성 논증도 그대로 성립한다.
   - **(b) quiesce 지점 일괄 sweep**: 활성 트랜잭션이 없는 시점 (compactdb 종료, SA 유틸리티 종료, boot) 에 `oos_collect_data_page_vpids` (sector-bitmap 순회) 로 전 데이터 페이지를 열거해 `oos_try_reclaim_empty_page` 에 공급. 구현이 가장 단순하고 안전하지만 churn 도중에는 여전히 증가한다.
   - (a) 가 근본 해법, (b) 는 (a) 전의 임시 완화 또는 compactdb 보강으로 병행 가능.
2. **단기 조치**: PR 답글로 실측 결과에 감사를 표하고, 스코프 제외 사실 + 후속 티켓 링크를 남길 것. JIRA CBRD-26786 에도 한계 명시.

---

## R2. [H2SU] 관측성 공백 — `spacedb`/`diagdb` 가 OOS 공간을 못 봄

### 주장 요약

`cubrid spacedb` 의 used 가 OOS 페이지를 반영하지 않고 `cubrid diagdb` 는 OOS 파일을 목록에 띄우지 않아, R1 누수가 발생해도 DBA 가 표준 도구로 진단할 수 없다 (raw 볼륨 크기로만 확인). 릴리스 빌드 진단 로그가 `oos_trace` (NDEBUG no-op) 라는 점과 겹친다.

### 검증 결과 — 확인됨 (기존 이슈, 이 PR 무관)

- OOS-CONTEXT.md 의 Known Bugs 가 동일 내용을 이미 추적 중이다: `FILE_OOS` 는 owner 메타데이터 (`FILE_DESCRIPTORS`) 가 없어 테이블 귀속이 불가하고, `spacedb` 는 heap 으로 뭉뚱그린다. **CBRD-26871** (QA tooling ask) 이 티켓 오브 레코드. 실험 브랜치에는 `SPACEDB_HEAP_FILE` 로 접는 (TOAST 식 "table storage" 회계) 임시 수정 + `FILE_OOS_DES{class_oid}` owner descriptor 후속안이 있다.
- 릴리스 빌드에서 `oos_trace` 가 no-op 인 점은 직전 리뷰 보고서 (PR-7617-report_82d6e4b) 의 non-blocking 항목 ("skip 카운터를 `oos_warn`/perfmon 으로 승격") 과 같은 축의 문제다.

### 판정

**타당하나 이 PR 이 도입한 문제가 아니고 이미 CBRD-26871 로 추적 중.** 부수 발견 (side finding) 이라는 H2SU 의 자체 분류가 정확하다. **머지 블로커 아님, PR 스코프 확장도 불필요.**

### 권장 해법

1. **CBRD-26871 우선순위 상향 요청**. 근거 두 가지: (1) 이 PR 의 A/C 인 CTP 회귀 시나리오가 "회수가 실제로 일어났는가" 를 릴리스 빌드에서 검증할 수단을 요구하고, (2) R1 누수는 표준 도구로 보이지 않는 한 운영 현장에서 조용히 진행된다.
2. 이 PR 범위에서 실현 가능한 최소 보강 (선택): 회수 성공/skip 카운터를 perfmon 스탯 또는 `oos_warn` 레벨로 승격 — 직전 리뷰 보고서 권고와 동일하므로 함께 처리하면 좋다.

---

## R3. [InChiJun] 회수가 heap home page WRITE latch 를 쥔 채 실행됨 (`vacuum.c:2539`)

### 주장 요약

`vacuum.c` 의 두 호출 지점 (REC_RELOCATION 경로 `:2539`, REC_HOME+OOS 경로 `:2618`) 모두 `helper->home_page` 가 fix 된 상태에서 `vacuum_oos_reclaim_empty_pages` 를 호출한다. 회수는 후보 페이지마다 OOS 통계 헤더 페이지에 무조건 WRITE latch + `file_dealloc` + sysop commit 까지 수행하므로 heap 페이지 WRITE latch 보유 시간이 후보 수에 비례해 늘고, OOS 헤더를 인서터와 경합해 insert 지연이 heap latch 로 전이된다. 또 `touched_pages` 가 레코드 단위 지역 변수라 dedupe 가 한 레코드 안에서만 동작한다. 제안: `VACUUM_OOS_TOUCHED_PAGES` 를 레코드 루프 밖으로 올려 누적하고 `home_page` unfix 후 한 번만 회수.

### 검증 결과 — 전 항목 확인됨

- **home_page latch**: `vacuum_heap_page` 가 `PGBUF_LATCH_WRITE` + `PGBUF_UNCONDITIONAL_LATCH` 로 fix (`vacuum.c:1658`, `:1696`) 하고, unfix 는 `vacuum_heap_page`/`vacuum_heap_page_log_and_reset` 쪽 (`:1898`, `:2740`, `:2779`) 에서만 일어난다. `vacuum_heap_record` 내부에는 home_page unfix 가 없으므로 두 회수 호출 (`:2539`, `:2618`) 은 heap home page WRITE latch 보유 중에 실행된다. `forward_page` 만 `:2519` 에서 FREE 된다는 서술도 정확하다.
- **후보당 비용**: `oos_try_reclaim_empty_page` 는 후보마다 OOS 통계 헤더에 무조건 WRITE latch (`oos_file.cpp:1270-1271`) 를 잡고, 빈 페이지면 `log_sysop_start` → `file_dealloc` (RVFL_DEALLOC postpone) → `log_sysop_commit` (`:1307-1321`) 까지 헤더 latch 아래에서 수행한다. 이 헤더는 `oos_find_best_page` 가 **모든 insert** 에서 WRITE latch 로 잡는 discovery choke point 가 맞다.
- **dedupe 무력화**: `oos_touched_pages` 는 `vacuum_heap_record` 의 지역 변수 (`vacuum.c:2460`) 이고 dedupe (`vacuum_oos.cpp:237-246`) 는 그 안에서만 동작한다. 인접 행들이 같은 OOS 페이지를 공유하는 흔한 배치에서 같은 VPID 에 대해 "ftab 헤더 fix ×2 + 헤더 WRITE latch + 조건부 fix" 시퀀스를 레코드 수만큼 반복한다.
- **데드락은 아님 (보충)**: insert 경로는 OOS latch 들 (헤더→데이터, 쓰기 완료까지 연속 보유) 을 **모두 놓은 뒤에** heap 페이지를 fix 하므로 heap→OOS-헤더 순서와 순환이 생기지 않고, 회수기의 후보 페이지 fix 는 conditional 이라 대기 자체가 없다. 즉 이 지적은 정확성(데드락)이 아니라 **latch 보유 시간·경합 전이** 문제다 — 다만 heap latch 를 쥔 채 다른 파일의 choke-point 헤더를 무조건 latch 하는 순서 자체가 향후 변경에 취약한 구조라는 점에서, 회수를 heap latch 밖으로 빼는 것은 그 취약성까지 함께 제거한다.
- **참고**: `vacuum_heap_page` 는 레코드 사이에서 non-vacuum waiter 에게 양보하는 장치 (`:1903-1921`, log_and_reset 후 재-fix) 를 이미 갖고 있다. 그 설계 의도 (heap 페이지 latch 를 오래 쥐지 않는다) 와 현재 회수 위치가 상충한다는 방증이기도 하다.

### 판정

**타당. 제안 수용 권장 (이 PR 에서 수정).** 회수는 멱등 + best-effort 계약이라 "삭제 sysop 커밋 직후" 에서 "heap 페이지 배치 완료 후" 로 **늦추는 것은 안전성을 강화하면 강화했지 훼손하지 않는다** — 커밋 이후라는 회수 전제 (undo 가 dealloc 된 페이지에 재삽입 불가) 는 시점이 늦을수록 더 확실히 성립하고, 커밋~회수 사이에 페이지가 재충전되면 emptiness 재검증이 skip 한다.

### 권장 해법 (구현 노트)

1. `VACUUM_OOS_TOUCHED_PAGES` 를 `vacuum_heap_page` 스코프로 hoisting — `vacuum_heap_record` 에는 out 파라미터 (또는 `VACUUM_HEAP_HELPER` 멤버) 로 전달. typedef (`vacuum_oos.hpp:38`) 가 이미 vacuum.c 용으로 마련돼 있어 GNU indent 제약 없이 선언 가능하다 (`:2460` 이 전례).
2. 회수 호출 지점: 오브젝트 루프 종료 후 최종 `vacuum_heap_page_log_and_reset (…, true, true)` (`:1932`) 다음, 즉 home_page unfix 이후 1회. 페이지 제거 경로 (`:1870-1898`) 도 unfix 후 합류하므로 같은 지점에서 처리된다.
3. 에러 조기 반환 경로는 후보 리스트를 그냥 버려도 된다 (best-effort — 페이지는 다음 vacuum 사이클 후보로 남는다). 원하면 반환 직전 회수를 시도해도 무방하다.
4. 선택 최적화: waiter 양보 지점 (`:1903-1921`, home_page 가 이미 unfix 된 순간) 에서 중간 flush 하면 리스트 크기와 회수 지연을 모두 줄일 수 있다 — 필수는 아니다.
5. 효과: heap latch 보유 구간에서 회수 비용 제거 + dedupe 가 heap 페이지 배치 전체에 걸쳐 실효 (인접 행 공유 페이지 중복 제거) + R4 의 per-file 검사 hoisting 과 자연스럽게 결합.

---

## R4. [InChiJun] 비어 있지 않은 후보에도 배타 latch 비용 전부 지불 (`oos_file.cpp:1299`)

### 주장 요약

`touched_vpids` 에는 "청크가 하나라도 빠진 페이지" 가 전부 들어오는데 실제 완전히 비는 페이지는 일부다. 그런데 판정 순서가 파일 헤더 fix ×2 (`file_get_sticky_first_page`, `file_is_numerable`) → OOS 헤더 무조건 WRITE latch → 후보 조건부 WRITE fix → **그제서야** 빈 페이지 판정이라, 삭제된 청크마다 insert 의 choke point 인 통계 헤더 WRITE latch 에 직렬화된다. CBRD-26824 전례를 감안하면 blob-heavy 워크로드에서 vacuum 중 insert 지연 회귀 여지가 있다. 제안: (1) 후보를 조건부 READ 로 먼저 fix 해 `PAGE_OOS` + 레코드 0건을 확인, 아니면 헤더를 안 건드리고 skip; (2) 비어 있을 때만 헤더 WRITE latch → 조건부 WRITE fix → 재검증 → `file_dealloc`. 그리고 `file_is_numerable`/`file_get_sticky_first_page` 는 파일 단위 불변이므로 배치 진입 시 1회로 hoisting.

### 검증 결과 — 전 항목 확인됨

- **판정 순서**: 코드 순서가 주장 그대로다 — `file_get_sticky_first_page` (`oos_file.cpp:1238`) 와 `file_is_numerable` (`:1257`) 이 각각 파일 테이블 헤더 페이지를 READ fix (`file_manager.c:5810`, `:6852` 확인), 이어 통계 헤더 무조건 WRITE latch (`:1270`), 후보 조건부 WRITE fix (`:1285`), 빈 페이지 판정은 마지막 (`:1298-1299`). 즉 대다수 (non-empty) 후보가 "ftab 헤더 fix ×2 + 헤더 WRITE 직렬화 + 후보 WRITE fix" 비용을 전부 낸다.
- **insert 경합 회귀 우려의 실증 전례**: CBRD-26824 는 바로 이 통계 헤더/bestspace 경로의 sync scan 조건 문제로 3MB 값 후반 INSERT 가 164ms → 890ms 로 늘었던 실측 회귀다 (`my-cubrid-docs/cbrd-26824` 분석 문서). vacuum 이 같은 헤더에 delete 청크 수 비례의 WRITE latch 트래픽을 추가하는 것은 같은 계열의 위험이 맞다.
- **불변 속성 hoisting 의 정당성**: numerable 여부는 파일 생성 시 고정, sticky first page (OOS 통계 헤더 VPID) 도 파일 수명 동안 불변이므로 후보마다 재조회할 이유가 없다.
- **2단계 판정의 안전성**: 1단계 READ fix 는 힌트일 뿐이고 최종 판정·dealloc 은 여전히 헤더 WRITE latch 아래에서 재검증 후 수행되므로, 함수 주석 (`oos_file.cpp:1218-1230`) 의 안전성 논증 3항 (헤더 latch 직렬화 / insert latch 연속성 / sysop-postpone 순서) 이 그대로 유지된다. 1단계 조건부 READ 실패 (writer 보유 중) → skip 은 어차피 재충전 중인 페이지라 올바르고, 1↔2단계 사이 재충전은 2단계 재검증이 잡는다. 유일한 추가 비용은 진짜 빈 페이지에 한한 fix 1회 (READ→unfix→WRITE) 인데, 빈 페이지는 소수이고 dealloc 비용 대비 무시 가능하다.

### 판정

**타당. 두 하위 제안 모두 수용 권장 (이 PR 에서 수정).** R3 과 독립적이면서 상보적이다 — R3 (배치 hoisting + dedupe 실효화) 가 헤더 latch 획득 횟수를 줄이고, R4 1단계 필터가 그 나머지를 "진짜 빈 페이지" 로 한정한다.

### 권장 해법 (구현 노트)

1. **배치 API 로 재구성**: per-file 검사 (sticky first page, is_numerable — numerable 이면 배치 전체 skip) 를 배치 진입 시 1회 수행하도록, 후보 루프를 `oos_file.cpp` 쪽 배치 함수 (예: `oos_reclaim_empty_pages (thread_p, vfid, const std::vector<VPID> &)`) 로 내리는 것을 권장. hoisting 된 상태 (hdr_vpid, is_numerable) 가 모듈 내부에 머물고, `oos_try_reclaim_empty_page` 는 단위 테스트가 있는 단일 페이지 프리미티브로 유지하거나 internal 변형으로 흡수한다. dedupe 는 지금처럼 vacuum 쪽에 둬도, 배치 함수로 옮겨도 무방하다.
2. **2단계 판정**: 1단계 — `OLD_PAGE_MAYBE_DEALLOCATED` + `PGBUF_LATCH_READ` + `PGBUF_CONDITIONAL_LATCH` 로 후보 fix, `pgbuf_get_page_ptype () == PAGE_OOS && spage_number_of_records () == 0` 아니면 즉시 skip. 2단계 — unfix 후 기존 경로 그대로 (헤더 WRITE latch → 조건부 WRITE fix → 재검증 → sysop + `file_dealloc`). 함수 주석의 안전성 논증에 "1단계는 힌트, 최종 판정은 헤더 latch 아래" 한 줄을 추가해 불변식을 명시할 것.
3. R3 과 함께 적용 시 순서: R3 의 배치 위치 이동 → R4 의 배치 함수화가 자연스러운 한 커밋 흐름이다.

---

## Overall Recommendation

1. **이 PR 에서 수정**: R3 + R4 (InChiJun 제안 수용). 둘 다 안전성 계약을 건드리지 않는 구조 개선이고, 이 PR 이 새로 도입한 경로의 동시성 비용이므로 후속 티켓으로 미룰 명분이 약하다. InChiJun 코멘트 2건은 현재 미응답 상태 — 수용 의사와 반영 커밋을 답글로 남길 것.
2. **후속 티켓 분리**: R1 (non-MVCC eager 경로 회수 — 커밋 postpone 설계 권장) 신규 발행, R2 는 CBRD-26871 우선순위 상향 코멘트. H2SU 리뷰에는 실측 재현 조건이 그대로 티켓 재료가 되므로 티켓 본문에 표를 인용할 것.
3. **참고**: 직전 리뷰 보고서 (PR-7617-report_82d6e4b) 의 blocking 이슈 (타 worker 미커밋 sysop 과의 emptiness 판정 경합) 는 본 보고서 스코프 밖이다 — R3/R4 반영으로 판정 코드를 재구성할 때 해당 게이트 보강과 충돌하지 않도록 함께 검토 권장.

## Evidence Index

| 근거 | 위치 |
|---|---|
| 회수 미연결 (SA/non-MVCC) 주석 및 `touched_vpids` 미전달 | `heap_oos.cpp:699-704`, `:768` |
| bestspace 캐시 상한 / 삭제 시 캐시 갱신 | `oos_file.cpp:110`, `:2439` |
| home_page WRITE·UNCONDITIONAL fix / unfix 지점 | `vacuum.c:1658`, `:1696` / `:1898`, `:2740`, `:2779` |
| 회수 호출 2개소 (home_page 보유 중) | `vacuum.c:2539`, `:2618` |
| `oos_touched_pages` 레코드 지역 변수 / dedupe | `vacuum.c:2460` / `vacuum_oos.cpp:237-246` |
| 후보당 판정 순서 (ftab fix ×2 → 헤더 WRITE → 조건부 fix → 빈 판정) | `oos_file.cpp:1238`, `:1257`, `:1270`, `:1285`, `:1298-1299`; `file_manager.c:5810`, `:6852` |
| waiter 양보 장치 (레코드 사이) | `vacuum.c:1903-1921` |
| CBRD-26824 insert 회귀 전례 (164ms→890ms) | `my-cubrid-docs/cbrd-26824/2026-08-10-…-analysis_2017daabf_codex.html` |
| 관측성 공백 추적 티켓 | CBRD-26871, OOS-CONTEXT.md Known Bugs |

---

*본 보고서는 PR head `66cd3cc` 로컬 worktree 에서 코드 레벨 재검증을 거쳐 작성되었다. (agent: claude)*
