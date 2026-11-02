# PR 7990 R3 분석, 성장 게이트 sweep 비용의 추적 단위

2026-11-02 Asia/Seoul 작성. hornetmj의 PR 7990 리뷰 R3를 별도 CBRD Sub-task로 추적할지 판단한 읽기 전용 분석이다. JIRA 생성·수정, 리뷰 답글, 소스 수정, 빌드, 측정은 하지 않았다. 이슈 문안은 이 문서 안의 로컬 제안이다.

**후속 결정.** 2026-11-02 사용자가 R3를 [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872)(Sub-task, 부모 CBRD-26583, 제목 `[OOS] [M2] sweep cost`)로 발급했다. 이 문서가 후속 처리 기준으로 제안한 부모 CBRD-26978과 다르다. 아래 분석은 작성 당시 그대로 둔다. 종합과 이후 결정은 [R3·R4 추적 단위 종합](PR-7990-R3-R4-tracking-decision_dcbf09e_claude.md)에 있다.

## 결론

**신규 Sub-task.** R3의 두 요구인 sweep 발동 조건 축소와 할당 1회당 작업량 상한을 범위로 가진 live 이슈는 없다. 리뷰가 지적한 동작은 현재 코드에 그대로 있고, 그 동작 자체가 Resolved된 CBRD-26786의 완료 범위이자 OOS 명세 §4가 승인한 설계다. 그래서 동작을 바꾸려면 명세 결정과 독립 검증이 함께 필요하다. 이미 완료·병합된 CBRD-26786을 다시 여는 것보다 새 Sub-task가 맞다.

핵심 근거는 다음과 같다.

1. [관찰] `src/storage/oos_file.cpp:1868` 의 발동 조건 `pending_deletes > 0 || !swept_this_boot` 와 `:1939-1998` 의 lap 순회, `:3535-3537` 의 체인 삭제마다의 카운터 증가가 source HEAD `dcbf09e4f` 에 그대로 있다. `feature/oos-merge` 대상 열린 PR 6건(8350, 8348, 8347, 8330, 8299, 8128)의 diff에도 sweep 관련 변경 줄은 없다.
2. [관찰] CBRD-26786(Resolved, Fixed, Sub-task, 부모 CBRD-26583)의 live 본문은 이 sweep을 수행 방안 5번과 A/C로 완료 처리했다. Remarks에는 "장수 트랜잭션이 페이지를 계속 defer 시키는 동안의 반복 lap은 후속 최적화 후보"와 PR 7617 리뷰 M2(컬렉터 상한·iterator)의 "후속 분리 예정"이 있지만, JQL로 찾은 대응 티켓은 없다.
3. [관찰] OOS 명세 `OOS-CONTEXT.md` §4 "Empty-Page Reclaim Invariant (CBRD-26786; accepted 2026-08-28)" 는 "An OOS file reserves a new sector only when no safely reclaimable empty page exists **right now**" 를 불변식으로 정하고, 모든 삭제가 카운터를 올리는 현재 sweep 규칙을 기술한다. 리뷰어의 상한안은 이 "right now" 를 완화한다(리뷰어도 일시적 페이지 증가를 인정했다).
4. [관찰] 성능 후보 CBRD-27785·27816은 reclaim을 범위에서 명시적으로 제외했고, CBRD-27788은 SELECT 측정이다. CBRD-27213은 부분 여유 페이지 힌트(bestspace)의 재설계이며 빈 페이지 회수 sweep의 발동·상한을 다루지 않는다.
5. 제안 부모는 후속 성능·기능 과제를 모으는 CBRD-26978(Task)이다. 병합 전 처리 여부는 후속을 권고하되 리뷰어 합의가 필요하다. 근거는 아래 [병합 전 처리인지 후속인지](#병합-전-처리인지-후속인지) 절에 있다.

## 기준과 표기

- Source checkout은 `/home/vimkim/gh/cb/feature-oos-merge`, branch `feature/oos-merge`, HEAD `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` 이다. coordinator가 준 값과 같다. untracked `review.log` 외에 변경은 없다.
- PR 7990의 `headRefOid` 도 같은 SHA다(GraphQL, 2026-11-02 19:28 KST). R3 댓글의 `commit_id` 와 `original_commit_id` 도 같은 SHA이므로 댓글의 줄 번호 1868은 현재 파일과 일치한다.
- OOS 명세는 `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`, SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`, 저장소 HEAD `3462a7f`, "Last updated: 2026-10-27" 이다. 전문을 읽었다.
- 일정 저장소 main은 `ed28fb38aa55130ee920ed4654abf0fef1114582` 로 handoff 값과 같다. `my-cubrid-jira` HEAD는 `52577be` 이다.

각 주장에는 다음 표지를 붙인다.

| 표지 | 뜻 |
| --- | --- |
| [관찰] | 이번 세션에서 직접 읽거나 조회한 사실 |
| [리뷰어 보고] | 원댓글에 적힌 측정·주장. 이 분석에서 재현하지 않았다 |
| [소스 추론] | 코드에서 추론했지만 실행으로 확인하지 않은 내용 |
| [미확인] | 근거를 찾지 못한 내용 |

새 측정은 하지 않았다. 별도 Sub-task로 추적할지는 현재 코드와 이슈 범위만으로 판단할 수 있다. 측정은 우선순위와 병합 전 처리 여부를 바꿀 수 있으므로, 필요한 측정을 [남은 불확실성](#남은-불확실성과-해소할-증거) 절에 구체적으로 적었다.

## 원댓글 요구

원댓글은 [r4399899312](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399899312)다. 작성자 hornetmj, 2026-10-28T11:16:54Z, `src/storage/oos_file.cpp:1868` 이다. 2026-11-02 19:28:15 KST에 세 REST endpoint로 PR의 모든 댓글을 다시 조회했다(inline 39, review 25, issue 39). [관찰] R3 thread는 답글이 0개이고, GraphQL 기준 `isResolved=false`, `isOutdated=false` 다.

리뷰어의 문제 제기는 "이 조건이 참이면, 새 OOS 페이지가 필요한 INSERT가 페이지를 할당하기 전에 OOS 파일의 모든 페이지를 하나씩 확인합니다" 이다. 발동 경우로는 재시작 뒤 파일별 첫 할당과 체인 삭제 뒤의 할당을 들었다.

요구는 두 개로 나뉜다. 이 분석은 둘을 이미 채택한 설계로 보지 않는다.

| 구분 | 리뷰어 요구 (짧은 인용) | 해결하려는 경우 |
| --- | --- | --- |
| (a) 발동 조건 | "체인을 지울 때마다 스윕을 켜지 말고, vacuum의 즉시 회수가 처리하지 못한 페이지가 있을 때만 켜 주시면 좋겠습니다" | 삭제 뒤 할당에서 회수할 페이지가 없는 lap |
| (b) 할당당 작업량 상한 | "한 번의 할당에서 확인하는 페이지 수에 상한을 두고, 다음 할당이 이어서 확인하게 해 주시면 좋겠습니다" | 재시작 뒤 첫 할당, 그리고 남은 모든 lap의 최악 지연 |

[리뷰어 보고] 측정 조건은 release 빌드, OOS 페이지 약 2만 개(320MB), 버퍼 256MB다.

| 경우 | 리뷰어가 보고한 값 |
| --- | --- |
| 재시작 직후 새 페이지가 필요한 첫 INSERT | 0.23~0.25초, 이후 INSERT는 1.4~2.7ms. 이 INSERT가 페이지 20,524개를 확인 |
| 1행 DELETE와 vacuum 뒤 새 페이지가 필요한 INSERT | 약 12ms. DELETE가 없으면 약 1.4ms |
| (a)와 (b)를 넣은 빌드, 상한 64페이지 | 재시작 직후 첫 INSERT 14~33ms |
| 같은 빌드, 400행 삭제 뒤 400행 재삽입 | OOS 페이지 501개로 원래 코드와 같음 |

리뷰어는 "페이지 100만 개면 수 초 이상, 할당마다 수백 ms" 를 비례 추정으로 표시했고, (a)만의 효과는 분리하지 못했다고 밝혔다. [관찰] R3 본문에는 "머지", "병합", "블로킹" 같은 표현이 없다. 같은 리뷰어의 R6은 "머지 전에 모두 제거해 주시면 좋겠습니다" 라고 명시했다.

## 현재 코드의 동작

`how` skill의 관점으로 정리했다. 대상이 한 파일의 한 기능이어서 explainer subagent 없이 직접 읽었다.

### Overview

빈 OOS 페이지 회수는 두 경로로 이뤄진다. vacuum fast path는 삭제 배치를 커밋한 직후, 그 배치가 비운 페이지 목록만 회수한다. 성장 게이트 sweep은 OOS 파일에 새 페이지가 필요할 때마다 `oos_alloc_page_with_reclaim` 에서 먼저 실행되어, fast path가 놓친 빈 페이지를 sector bitmap에서 다시 찾아 회수한다. R3는 이 sweep이 회수할 페이지가 없는데도 파일 전체를 한 번에 검사하는 경우를 지적한다.

### Key concepts

| 개념 | 위치 | 의미 |
| --- | --- | --- |
| `pending_deletes` | `oos_file.cpp:1293` | 완료된 lap이 아직 정산하지 않은 삭제 수. 0인지 아닌지만 의미가 있다 |
| `swept_this_boot` | `oos_file.cpp:1295` | 이번 부팅에 lap 하나를 완주했는지. false이면 boot rule로 무조건 sweep |
| `sweep_in_progress` | `oos_file.cpp:1298` | 파일당 sweep 하나만 돌게 하는 single-flight 표시 |
| `sweep_cursor` | `oos_file.cpp:1299` | 마지막으로 회수한 페이지. 다음 lap은 그 다음 VPID부터 시작 |
| LSA 게이트 | `oos_file.cpp:1453-1473`, `:1516-1522` | 활성 쓰기 트랜잭션과 system tdes의 최소 head LSA보다 page LSA가 새 빈 페이지는 회수하지 않고 deferred로 둔다 |
| lap | `oos_file.cpp:1939-1998` | cursor 다음부터 한 바퀴 돌아 cursor까지 모든 데이터 페이지를 검사하는 순회 |

side map 전체는 `oos_Bestspace->bestspace_mutex` 로 보호하는 메모리 전용 힌트다(`:1315-1317`). 재시작하면 비워진다(`:343`).

### How it works

1. `oos_find_best_page` 가 bestspace 힌트에서 맞는 페이지를 못 찾으면 `oos_alloc_page_with_reclaim` 을 부른다(`:3030`, `:3037`, `:3044`, `:3116`, `:3122`, `:3152`). 새 페이지 할당은 모두 이 함수를 지난다(`:2006-2034`).
2. `oos_reclaim_sweep_step` 은 mutex 아래에서 파일 상태를 본다(`:1835-1886`). 항목이 없으면 boot rule로 sweep을 맡는다(`:1841-1849`). 다른 스레드가 같은 파일을 sweep 중이면 condition variable에서 기다린다(`:1850-1867`). `pending_deletes > 0 || !swept_this_boot` 이면 sweep을 맡는다(`:1868-1874`).
3. 맡은 스레드는 `file_get_all_data_sectors` 로 partial·full sector 표 전체를 private memory로 복사하고 정렬한다(`:1912-1933`). LSA horizon을 한 번 표본으로 잡는다(`:1935-1936`).
4. cursor 다음 VPID부터 모든 할당 비트를 돌며 `oos_try_reclaim_page_internal` 을 부른다(`:1939-1996`). 이 함수는 페이지마다 조건부 READ fix를 하고, 비어 있고 LSA 게이트를 통과한 페이지만 헤더 WRITE latch 아래에서 다시 확인해 `file_dealloc` 한다(`:1568-1707`).
5. 첫 페이지를 회수하면 cursor를 저장하고 즉시 반환한다(`:1975-1989`). 호출자의 `file_alloc` 이 그 페이지를 재사용한다.
6. 회수 없이 한 바퀴를 마치면 `oos_reclaim_settle_lap` 이 lap 시작 때의 카운터만 빼고, deferred 페이지 수를 다시 더하고, `swept_this_boot=true` 로 둔다(`:1790-1806`, `:1998`).

카운터는 다음 경로에서 올라간다.

- `oos_delete` 가 체인을 실제로 지운 경우, 호출자와 무관하게 +1이다(`:3535-3537`). vacuum의 두 경로(`vacuum_oos.cpp:182`, `:469`)와 SA·non-MVCC eager 경로(`heap_oos.cpp:1033`)가 모두 여기를 지난다.
- 런타임 INSERT rollback과 복구 redo의 `oos_rv_redo_delete` 는 `oos_stats_del_bestspace_by_vpid(..., true, ...)` 로 카운터를 올린다(`:3694`, `:422-436`). VFID를 모르면 알려진 모든 파일을 올린다(`:1379-1382`).
- 이번 부팅에 만든 파일은 `swept_this_boot=true` 로 등록해 첫 할당에서 sweep하지 않는다(`:1400-1418`).

vacuum fast path는 커밋 뒤 `vacuum_oos_reclaim_empty_pages` 를 거쳐 `oos_reclaim_empty_pages` 를 부른다(`vacuum_oos.cpp:188-194`, `vacuum.c:1978-1982`, `oos_file.cpp:1730-1782`). eager 경로는 살아 있는 사용자 트랜잭션 안에서 실행되므로 fast path를 쓰지 않는다(`heap_oos.cpp:946-948`).

### Where things live

| 책임 | 파일·함수 |
| --- | --- |
| 회수 불변식 배너 | `src/storage/oos_file.cpp:1261-1275` |
| side map과 정산 | `oos_reclaim_file_state`, `oos_reclaim_note_delete_locked`, `oos_reclaim_settle_lap` (`oos_file.cpp:1291-1436`, `:1790-1806`) |
| 페이지 하나의 회수 판정 | `oos_try_reclaim_page_internal` (`oos_file.cpp:1568-1707`) |
| fast path | `oos_reclaim_empty_pages` (`oos_file.cpp:1730-1782`), `vacuum_oos_reclaim_empty_pages` (`src/query/vacuum_oos.cpp:223-245`) |
| 성장 게이트 sweep | `oos_reclaim_sweep_step` (`oos_file.cpp:1823-2003`) |
| 단일 성장 지점 | `oos_alloc_page_with_reclaim` (`oos_file.cpp:2019-2034`) |
| 파일 확장 조건 | `file_perm_alloc` 은 `n_page_free == 0` 일 때만 `file_perm_expand` 로 sector를 예약한다 (`src/storage/file_manager.c:5197-5206`) |
| 동작 고정 테스트 | `unit_tests/oos/test_oos_growth_sweep.cpp` 의 11개 TEST. 예를 들어 `:191` 동시 grower 대기, `:251` INSERT rollback 재무장, `:413` deferred 유지, `:448` boot rule |

### Gotchas

- lap은 첫 회수에서 멈춘다. 리뷰어의 "모든 페이지" 는 회수할 페이지가 하나도 없는 경우에 맞다. 리뷰어가 측정한 두 경우가 그 경우다.
- cursor는 회수했을 때만 움직인다. 회수 없는 lap은 cursor를 그대로 두므로, 다음 lap도 같은 위치에서 한 바퀴를 돈다.
- [소스 추론] deferred 페이지가 남으면 정산 뒤에도 카운터가 0보다 크다(`:1802`). 오래 열린 쓰기 트랜잭션이 horizon을 붙잡는 동안에는 새 페이지 할당마다 lap 전체를 다시 돈다. CBRD-26786 Remarks도 이 경우를 후속 최적화 후보로 적었다.
- [소스 추론] sweep은 sector 예약이 필요할 때만이 아니라 모든 새 페이지 할당에서 실행된다. `file_perm_alloc` 은 기존 sector에 빈 비트가 있으면(`n_page_free > 0`) sector를 예약하지 않는데, 명세 불변식은 sector 예약에 관한 것이다.
- [소스 추론] fast path의 phase 1 조건부 READ fix가 실패한 페이지는 DEFERRED가 아니라 SKIPPED다(`:1590-1593`). fast path의 non-interrupt 오류는 흡수되고(`vacuum_oos.cpp:236-244`), 후보 목록이 메모리 부족이면 목록을 버린다(`oos_file.cpp:3397-3411`). 지금은 `oos_delete` 가 이미 카운터를 올렸으므로 sweep이 이 페이지들을 다시 찾는다. (a)처럼 vacuum 삭제의 무장을 빼면 이 경우마다 따로 무장해야 한다.
- [소스 추론] (b)로 페이지 검사 수를 제한해도, 지금 구조에서는 단계마다 `file_get_all_data_sectors` 가 sector 표 전체를 복사·정렬한다(`:1912-1933`). 이 비용은 sector 수에 비례한다.
- [소스 추론] 같은 파일에 새 페이지가 필요한 다른 INSERT는 진행 중인 lap이 끝날 때까지 기다린다(`:1850-1867`). 리뷰어가 측정한 단일 세션 지연보다 동시 부하의 꼬리 지연이 클 수 있다.

## 원댓글 주장과 소스 대조

| 리뷰어 주장 | 표지 | 소스 근거와 보정 |
| --- | --- | --- |
| 재시작 뒤 파일별 첫 할당은 `swept_this_boot=false` 라 sweep한다 | [관찰] 맞음 | `:1841-1849`, `:1868`. 이번 부팅에 만든 파일은 예외다(`:1400-1418`) |
| 체인을 지울 때마다 `pending_deletes` 를 올린다 | [관찰] 맞음 | `:3535-3537`. stale skip 결과는 올리지 않는다 |
| vacuum이 비운 페이지는 커밋 직후 fast path가 이미 회수한다 | [소스 추론] 조건부로 맞음 | fast path는 LSA 게이트로 보류하고(`:1603-1607`), READ 경합은 건너뛰고, 오류를 흡수한다. 동시 쓰기 트랜잭션이 vacuum 삭제보다 먼저 로그를 남기고 아직 활성이면 보류된다. 리뷰어 측정은 단일 세션이다. 동시 부하에서의 보류 비율은 [미확인] |
| 회수할 페이지가 없으면 파일의 모든 페이지를 고정해 확인한다 | [관찰] 맞음 | `:1939-1998`. 페이지마다 조건부 READ fix |
| 버퍼에 없으면 디스크 읽기 | [소스 추론] 맞음 | 조건부 latch는 대기만 피하고 I/O는 피하지 않는다. 다른 작업의 버퍼 페이지를 밀어내는 영향은 [미확인] |
| 상한 64페이지로 재시작 직후 첫 INSERT 14~33ms | [리뷰어 보고] | 프로토타입 코드는 공개되지 않아 무장 경로 처리 범위는 [미확인] |
| 개선안 (a)의 무장 대상은 LSA 보류와 fast path 없는 삭제 | [소스 추론] 일부 누락 | phase 2 WRITE 미획득, phase 1 READ 경합, fast path 오류·중단, 후보 목록 메모리 부족, INSERT rollback도 무장이 필요하다 |

## 중복 후보 비교

live JIRA 조회는 2026-11-02 19:30:21~19:31:37 KST다. 후보 이슈는 `cubrid-jira search` 로 본문·댓글·상태·유형·부모를 읽었다. `my-cubrid-jira` 와 `my-cubrid-docs` 의 로컬 자료는 먼저 검색했고, 현재 상태는 live 값으로 정했다.

| 이슈 | live 상태·유형·부모 | 포함된 범위 | 빠진 범위 | 판단 |
| --- | --- | --- | --- | --- |
| [CBRD-26786](https://jira.cubrid.org/browse/CBRD-26786) | Resolved, Fixed, Sub-task, 부모 CBRD-26583, 갱신 2026-09-04, 댓글 1건(PG 참고) | fast path, LSA 게이트, 성장 게이트 sweep 전체 설계와 구현(PR 7617, 병합 커밋 `0d994560c`) | 발동 조건 축소와 할당당 상한이 없다. Remarks의 후속 후보 2건은 티켓이 없다. 미완 A/C는 CTP 공간 회귀와 crash injection이며 성능이 아니다 | 출처로 연결한다. 완료·병합된 이슈라 확장하지 않는다 |
| [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213) | Open, Sub-task, 부모 CBRD-26978, 미할당, 댓글 없음 | OOS bestspace를 heap 공통 shard 모듈로 전환, 재시작 snapshot과 sector bitmap 점진 재검증 순회 | 빈 페이지 회수 sweep의 발동·상한을 다루지 않는다. CBRD-26786의 회수 생애 주기를 전제로 둔다 | 중복 아님. 재시작 순회의 공유 가능성으로 연결한다 |
| [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785) | Develop, Sub-task, 부모 CBRD-26835, 댓글 없음 | shparkcubrid 성능 댓글 1·3번, 일반 테이블과 overflow 대체 경로의 CRUD 비교 | 관련 문서와 PR 8299 본문이 "OOS reclaim·allocator 구현·threshold" 를 별도 범위로 명시한다 | 중복 아님 |
| [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816) | Open, Sub-task, 부모 CBRD-26978 | 일반 UPDATE의 잔여 CPU 비용 | 본문이 "OOS reclaim tail은 독립 재현·정합성 검증이 필요한 별도 작업이다" 라고 적었으나 대응 티켓은 없다. "reclaim tail" 이 정확히 무엇을 가리키는지는 [미확인] | 중복 아님 |
| [CBRD-27788](https://jira.cubrid.org/browse/CBRD-27788) | Open, Sub-task, 부모 CBRD-26583 | 작은 컬럼 조회 이득과 큰 값 조회 비용 측정 | INSERT 할당 경로와 재시작 뒤 할당을 측정하지 않는다 | 중복 아님 |
| [CBRD-26824](https://jira.cubrid.org/browse/CBRD-26824) | Resolved, Sub-task, 부모 CBRD-26835 | 매 INSERT가 헛된 bestspace sync를 돌아 파일이 커질수록 느려지던 회귀 | sweep은 그 뒤에 도입되어 대상이 아니다 | 같은 형태의 문제를 별도 Sub-task로 고친 전례다 |
| [CBRD-26517](https://jira.cubrid.org/browse/CBRD-26517) | Open, Sub-task, 부모 CBRD-26978 | 과거 기능·성능 TODO 기록 | sweep 항목이 없다 | 중복 아님 |
| [CBRD-27350](https://jira.cubrid.org/browse/CBRD-27350), [CBRD-26950](https://jira.cubrid.org/browse/CBRD-26950) | Open / Closed | spacedb OOS 분류, identity stamp | "growth gate" 와 "성장 게이트" 는 관측성과 회수 계약 맥락의 언급이다 | 중복 아님 |

검색 범위와 검색어는 다음과 같다.

- `my-cubrid-jira` 전체(HEAD `52577be`)에서 `sweep`, `스윕`, `growth-gate`, `growth gate`, `oos_reclaim_sweep_step`, `oos_alloc_page_with_reclaim`, `pending_deletes`, `swept_this_boot`, `reclaim tail` 을 검색했다. sweep을 다룬 이슈 초안은 없었다. CBRD-26786 로컬 초안 2개는 sweep 도입 전 내용이다.
- `my-cubrid-docs` 에서 sweep 심볼을 검색해 PR 7617 응답 보고서와 CBRD-27785 문서를 읽었다.
- JQL은 [부록](#부록-조회-기록)에 적었다. 19:31:08과 19:31:22 KST에 실행했다.
- GitHub는 PR 7990의 세 endpoint와 thread 상태(19:28:15 KST), PR 7617의 모든 댓글(19:30:44 KST), sweep 검색과 `feature/oos-merge` 대상 열린 PR diff(19:36:23 KST)를 조회했다.

## 결론의 근거

**현재 코드에서 해결되지 않았다.** [관찰] 위 소스 근거와 열린 PR diff 검사 결과다. R3 thread에도 답글이 없다.

**기존 이슈 확장은 맞지 않다.** CBRD-26786은 Resolved이고 PR이 병합됐다. 다시 열면 완료한 회수 보장과 새 성능 변경이 한 기록에 섞인다. CBRD-27213은 부분 여유 페이지 힌트를 다루고, 리뷰어가 R4에서 밝힌 대로 bestspace redesign 안정화 뒤에 적용할 미할당 TODO다. R3를 여기에 넣으면 회수 sweep의 지연 문제가 redesign 일정에 묶인다. CBRD-27785와 27816은 reclaim을 명시적으로 뺐다.

**판단 보류 사유도 아니다.** 추적 필요성은 코드와 리뷰어 측정만으로 성립한다. 남은 불확실성은 지연의 크기와 동시 부하에서의 빈도이며, 이것은 우선순위와 처리 시점을 정하는 근거다.

**명세 결정이 필요하다.** [관찰] 현재 동작은 명세 §4를 따른다. 따라서 R3는 결함 수정(Correct Error)이 아니라 승인된 설계를 바꾸는 성능 개선이다. (b)는 "right now" 불변식을 완화하고, (a)는 "모든 삭제가 카운터를 올린다" 는 규칙을 바꾼다. 결정 기록과 테스트 갱신을 한 작업 단위로 추적해야 한다.

**CBRD-26786이 남긴 후속을 받을 곳이 없다.** [관찰] PR 7617 응답에서 M2를 "후속 티켓으로 분리하겠습니다" 라고 했고, CBRD-26786 Remarks도 후속 후보를 적었다. JQL `컬렉터`, `lazy iterator`, `backoff`, `horizon` 검색은 CBRD-26786과 무관한 이슈만 찾았다. 새 Sub-task는 sweep 쪽 후속 두 가지(deferred 반복 lap, sweep의 sector 수집 비용)를 함께 받을 수 있다. M2의 다른 절반인 Tier-3 sync의 VPID 목록 생성(`oos_stats_sync_bestspace`, `oos_file.cpp:850-855`)은 sync를 대체하는 CBRD-27213 쪽에 가깝다. 이 부분은 R3 범위에 넣지 않는다.

## 병합 전 처리인지 후속인지

권고는 **후속 처리**다. 다만 R3 thread가 미해결이므로 리뷰어가 후속으로 동의해야 한다.

후속을 지지하는 근거는 다음과 같다.

- [리뷰어 보고] 공간과 정확성 영향이 없다. 리뷰어의 재삽입 시험에서 페이지 수가 같았고, 지적은 지연에 한정된다.
- [관찰] side map은 메모리 전용이다. 고치는 시점이 병합 뒤여도 디스크 형식이나 로그 형식을 바꿀 필요가 없다. R6처럼 "머지되면 로그 형식으로 굳는다" 는 이유가 없다.
- [관찰] R3 본문에는 병합 전 요구 표현이 없다. 같은 리뷰어의 R4는 후속 적용 계획을 명시했다.
- [관찰] 2026-11-02 사용자 결정으로 R3는 차주 구현 대상에서 빠졌다(`week-2026-11-09.md:37`). 일정 문서도 보류를 해결이나 면제로 표시하지 않는다.

병합 전으로 바꿀 수 있는 근거는 다음과 같다.

- [리뷰어 보고] 지연이 파일 크기에 비례한다. 리뷰어는 100만 페이지에서 첫 INSERT 수 초 이상을 추정했다.
- [소스 추론] 오래 열린 쓰기 트랜잭션이 있으면 새 페이지 할당마다 lap 전체를 반복하고, 같은 파일의 동시 INSERT는 그 lap을 기다린다. 이 경우의 크기는 측정되지 않았다.
- 이전 체크리스트의 전달 순서는 R3를 다섯 번째 수정 PR로 두었다(`PR-7990-hornetmj-review-checklist_20261029_codex.md:38`). 그 뒤 차주 범위에서 보류됐다.

위 두 번째 근거의 측정 결과가 운영에서 받아들일 수 없는 지연이면 병합 전 처리로 바꾼다. 그렇지 않으면 후속으로 두고, R3 thread에 새 이슈 번호와 후속 계획을 답한다. 병합 전 처리로 바꾸면 부모는 R1·R2·R5·R6과 같은 CBRD-26583이 자연스럽고, 체크리스트의 "확정한 전달 방식" 대로 `feature/oos-merge` 를 대상으로 한 독립 PR이 된다.

## R3와 R4의 겹침과 의존성

R4 원댓글([r4409283403](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409283403))만 읽었다. 다른 agent의 `r4-analysis.md` 는 읽지 않았다.

- **같은 경로를 쓰는 수정 가능성.** [리뷰어 보고] R4의 수정 방향은 "재시작 뒤 첫 할당 때 회수 스윕이 어차피 OOS 페이지를 모두 한 번씩 고정해서 확인합니다" 를 이용해, 빈 공간이 충분한 페이지를 bestspace 힌트로 등록하는 것이다. R4의 이 안은 R3가 줄이려는 boot rule lap에 기대어 있다.
- **필수 의존성은 없다.** [소스 추론] R3의 결과인 회수 검사량 상한과 무장 조건은 R4 없이 구현하고 검증할 수 있다. R4는 CBRD-27213의 snapshot과 재시작 순회로도 풀 수 있으므로 R3를 필요로 하지 않는다.
- **조건부 순서 제약.** R4를 sweep hook으로 구현하면 (b)를 적용한 뒤에는 힌트가 한 번에 복원되지 않고 여러 할당에 걸쳐 복원된다. 이것은 동작 차이일 뿐 충돌은 아니다. 반면 R3에서 "sector 예약이 필요할 때만 sweep" 안(아래 후보 C)을 고르면, 재시작 뒤 빈 비트가 남은 파일에서는 boot rule lap이 늦게 돌아 R4 hook의 실행 시점도 늦어진다. 두 결정은 서로의 선택지를 좁힌다.
- **(a)는 R4와 충돌하지 않는다.** (a)는 boot rule을 건드리지 않는다.
- **같은 순회 코드를 나눌 가능성.** CBRD-27213의 재시작 순회는 "cursor를 청크마다 처음으로 되돌리지 않는" 점진 순회다. (b)를 cursor 기반 단계 순회로 만들면 두 순회가 같은 iterator를 쓸 수 있다. 이것은 설계 기회이며, 한쪽이 다른 쪽을 막지는 않는다.

권고는 R3와 R4를 별개 추적 단위로 두고, 새 R3 Sub-task의 ANALYSIS가 R4의 sweep hook 안과 CBRD-27213의 재시작 순회를 같이 검토하는 것이다. R4를 R3 이슈에 묶지 않는다.

## 신규 Sub-task 로컬 제안

`cubrid-jira-issue-write` 형식으로 작성했다. live에 게시하지 않았다. 사용자의 이번 지시에 따라 `my-cubrid-jira` 에 파일을 만들거나 커밋하지 않았다. 나중에 저장한다면 이슈 번호가 없으므로 `issues/oos-growth-sweep-allocation-cost_dcbf09e_claude.md` 가 규칙에 맞는 이름이다.

- **JIRA 유형.** Sub-task. 작업 성격은 Improve Function/Performance다. 현재 동작이 승인된 명세를 따르므로 Correct Error가 아니다.
- **문제 분류.** 성능·자원 효율. 명세 일관성(§4 갱신).
- **컴포넌트.** storage(`src/storage/oos_file.cpp`), vacuum(`src/query/vacuum_oos.cpp`).
- **제안 부모.** [CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978) "[OOS] [EPIC] TODO". [관찰] 유형은 Task, 상태 Confirmed다. 본문은 "OOS 도입 Epic에서 파생된 후속 이슈들을 모아 관리한다. 성능 개선, 기능 확장, 남은 결함 및 검증 과제를 하위 이슈로 추적" 한다고 적었다. 부모가 Sub-task가 아니므로 중첩 문제가 없다. CBRD-27816이 같은 방식으로 이 부모 아래 만들어졌다. 병합 전 처리로 정하면 부모를 [CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583)(Development Subject)으로 바꾸고 제목의 `[TODO]` 를 뺀다.
- **관계.** CBRD-26786과 `relates to`(원 설계와 미분리 후속 후보). CBRD-27213과 `relates to`(재시작 순회 공유 가능성). 출처는 PR 7990 r4399899312다.

~~~~markdown
# [OOS] [TODO] 재시작이나 삭제 뒤 새 OOS 페이지를 할당하는 INSERT가 파일 크기에 비례해 느려진다

## Issue Triage

**이슈 수행 목적**: 새 OOS 페이지를 할당하는 INSERT 한 건이 수행하는 빈 페이지 회수 검사량을 OOS 파일 크기와 무관한 상한 안에 둔다. vacuum이 이미 회수를 마친 삭제가 불필요한 검사를 시작하지 않게 한다. 빈 OOS 페이지가 결국 파일 관리자로 반환된다는 보장은 유지한다.

**이슈 수행 이유**: 성장 게이트 sweep은 서버 재시작 뒤 파일별 첫 페이지 할당과, OOS 체인 삭제가 한 건이라도 있은 뒤의 페이지 할당에서 실행된다. 회수할 빈 페이지가 없으면 할당 한 번이 파일의 모든 데이터 페이지를 고정해 검사한다. PR #7990 리뷰(hornetmj)는 OOS 페이지 약 2만 개 파일에서 재시작 직후 첫 INSERT 0.23~0.25초, 1행 삭제와 vacuum 뒤 INSERT 약 12ms(삭제가 없으면 약 1.4ms)를 보고했다. 이 동작은 CBRD-26786에서 승인한 설계 그대로이므로, 바꾸려면 OOS 명세의 빈 페이지 회수 불변식도 함께 결정해야 한다.

**영향**: 큰 OOS 테이블에 큰 값을 넣는 응용은 재시작 직후와 삭제가 이어지는 동안 일부 INSERT의 지연이 파일 크기에 비례해 늘어난다. 같은 파일에 새 페이지가 필요한 다른 INSERT는 진행 중인 검사가 끝날 때까지 기다린다. 공간 사용과 결과 정확성에는 영향이 보고되지 않았다. 실제 규모의 지연과 동시 쓰기 부하에서의 발생 빈도는 미확인이다.

**이슈 수행 방안**: TBD - ANALYSIS 단계에서 해결 방안과 구현 범위를 결정한다. 리뷰어가 제안한 발동 조건 축소와 할당당 검사 페이지 상한은 검토할 후보다.

---

## AI-Generated Context

> 아래는 PR #7990 리뷰, CBRD-26786, OOS 명세, `feature/oos-merge` HEAD `dcbf09e4f` 의 소스를 바탕으로 작성한 상세 맥락이다. 리뷰어 측정은 리뷰어의 보고이며 이 이슈 작성 중에 재현하지 않았다. 소스 추론과 미확인 사항은 본문에 구분한다.

## Description

### 무엇이 문제인가

OOS 파일의 빈 페이지 회수는 두 경로로 이뤄진다(CBRD-26786). vacuum fast path는 삭제 배치를 커밋한 직후 그 배치가 비운 페이지를 회수한다. 성장 게이트 sweep은 파일에 새 페이지가 필요할 때마다 `oos_alloc_page_with_reclaim` 에서 먼저 실행되어, fast path가 놓친 빈 페이지를 sector bitmap에서 다시 찾는다.

sweep의 발동 조건은 `pending_deletes > 0 || !swept_this_boot` 다(`src/storage/oos_file.cpp:1868`). `oos_delete` 가 체인을 지울 때마다 `pending_deletes` 가 오른다(`oos_file.cpp:3535-3537`). vacuum이 지운 체인도 같고, fast path가 그 페이지를 이미 회수했어도 같다. 재시작하면 `swept_this_boot` 가 false가 되어 파일별 첫 할당이 sweep을 실행한다.

sweep은 저장된 cursor 다음부터 파일의 데이터 페이지를 차례로 조건부 고정해 검사하고, 첫 페이지를 회수하면 멈춘다(`oos_file.cpp:1939-1989`). 회수할 페이지가 없으면 할당 한 번 안에서 모든 데이터 페이지를 검사한 뒤에야 끝난다. 버퍼에 없는 페이지는 디스크에서 읽는다.

발생 경우는 세 가지다.

1. 재시작 뒤 파일별로 새 페이지가 필요한 첫 INSERT. 리뷰어 보고로 0.23~0.25초, 검사 페이지 20,524개다.
2. 체인 삭제 뒤 새 페이지가 필요한 INSERT. 리뷰어 보고로 약 12ms이고 삭제가 없으면 약 1.4ms다.
3. 소스 추론. 활성 쓰기 트랜잭션 때문에 LSA 게이트가 빈 페이지를 보류하면, lap을 마쳐도 보류한 수만큼 카운터가 남는다(`oos_file.cpp:1802`). 그 트랜잭션이 끝날 때까지 새 페이지 할당마다 lap 전체를 다시 돈다. CBRD-26786 Remarks가 후속 최적화 후보로 적은 경우이며 측정은 없다.

필요한 상태는 할당 한 번이 하는 회수 검사량이 파일 크기와 무관하게 제한되고, 이미 회수가 끝난 삭제가 검사를 시작하지 않는 것이다.

### 왜 문제인가

큰 값을 OOS에 저장하는 테이블에 INSERT하는 응용은 INSERT 지연이 일정하기를 기대한다. 운영자는 정기 재시작 뒤에도 같은 응답 시간을 기대한다.

지금은 재시작 직후 각 OOS 테이블에서 새 OOS 페이지가 필요한 첫 INSERT가 파일 전체 검사 비용을 떠안는다. 같은 테이블에 동시에 새 페이지가 필요한 INSERT는 그 검사가 끝날 때까지 기다린다(`oos_file.cpp:1850-1867`). UPDATE나 DELETE가 계속되어 vacuum이 OOS 체인을 지우는 테이블에서는, 삭제 뒤 새 페이지 할당마다 회수할 것이 없는 검사가 반복될 수 있다. 검사 비용은 파일 크기에 비례하므로 데이터가 커질수록 지연이 커진다.

확인된 영향은 리뷰어의 단일 세션 측정이다. 리뷰어는 100만 페이지 파일에서 재시작 뒤 첫 INSERT가 수 초 이상 걸리고, 삭제가 이어지면 할당마다 수백 ms가 든다고 비례 추정했다. 이 값은 추정이다. 동시 쓰기 부하에서의 빈도, 오래 열린 쓰기 트랜잭션이 있을 때의 반복 검사 비용, 검사가 버퍼 풀의 다른 페이지를 밀어내는 영향은 측정되지 않았다. 운영자가 이 지연을 다른 원인과 구분할 전용 지표도 없다.

### 왜 해결해야 하는가

방치하면 OOS 테이블이 클수록 재시작 직후와 삭제가 많은 구간의 INSERT 지연이 커진다. 사용자가 쓸 우회책은 없다. sweep을 끄는 설정이 없고, 재시작은 운영상 피할 수 없다.

sweep 상태는 메모리 전용이어서 이 개선에는 디스크나 로그 형식 변경이 필요 없다. 따라서 develop 병합 뒤 후속으로 처리해도 호환성 부담이 생기지 않는다. 다만 현재 동작은 OOS 명세 §4가 승인한 설계이므로 회수 보장을 어떤 형태로 유지할지 결정과 검증이 함께 필요하다.

같은 형태의 문제는 별도 이슈로 고친 전례가 있다. CBRD-26824는 매 INSERT가 헛된 bestspace sync를 돌아 파일이 커질수록 느려지던 회귀였다. CBRD-26786이 남긴 sweep 관련 후속 후보(LSA 보류가 남은 동안의 반복 lap, PR 7617 리뷰 M2의 순회 상한)도 아직 추적 이슈가 없다. 이 이슈가 그 후보를 함께 받는다.

## Specification Changes

사용자 가시 SQL 동작은 바뀌지 않는다.

OOS 명세 §4 "Empty-Page Reclaim Invariant" 는 "OOS 파일은 지금 안전하게 회수할 수 있는 빈 페이지가 없을 때만 새 sector를 예약한다" 와 "모든 삭제가 카운터를 올린다" 는 sweep 규칙을 정한다. 할당당 검사량을 제한하면 아직 검사하지 않은 위치에 빈 페이지가 남은 채 파일이 커질 수 있다. ANALYSIS는 불변식을 제한된 형태로 고칠지, 불변식을 유지하는 다른 설계를 고를지 결정하고 명세에 기록한다.

## Implementation

TBD - ANALYSIS 단계에서 결정한다.

## Options for Analysis

아래는 후보이며 선택한 설계가 아니다.

| 후보 방안 | 기대 효과와 장점 | 한계·단점과 실패 조건 | 비용·위험·호환성 | 근거와 ANALYSIS 확인 사항 |
|---|---|---|---|---|
| 현재 동작 | 회수 가능한 빈 페이지가 있으면 sector를 예약하지 않는다 | 회수할 것이 없을 때 할당 한 번이 파일 전체를 검사한다 | 변경 없음 | 리뷰어 측정 |
| A. 무장 조건 축소 (리뷰어 개선안 1) | fast path가 모두 회수한 삭제 뒤의 헛된 lap을 없앤다 | 재시작 뒤 첫 할당과 LSA 보류 반복은 그대로다. 동시 쓰기 부하에서 fast path 보류가 잦으면 효과가 작다 | fast path가 회수하지 못한 모든 경우를 따로 무장해야 한다. 하나라도 빠지면 다음 부팅까지 빈 페이지가 남는다 | 동시 부하에서 fast path의 회수·보류 비율 |
| B. 할당당 검사 상한과 cursor 이어 가기 (리뷰어 개선안 2) | 세 경우 모두 할당당 지연을 제한한다 | 빈 페이지가 남은 채 파일이 일시적으로 커질 수 있다. 단계마다 sector 표 전체를 다시 읽으면 sector 수 비례 비용이 남는다 | lap 정산을 여러 단계에 걸쳐 다시 설계해야 한다. 명세 불변식 완화가 필요하다 | 상한 크기, 일시 증가량, sector 수집 비용 |
| C. sector 예약이 필요할 때만 sweep | 기존 sector에 빈 비트가 남은 동안(`n_page_free > 0`)의 할당에서 sweep을 생략한다. 명세 불변식의 문장과 맞는다 | sweep이 실행되는 순간의 비용은 그대로다. 확인과 `file_alloc` 사이에 다른 스레드가 빈 비트를 쓰면 검사 없이 확장할 수 있다 | 파일 헤더 조회가 추가된다. R4의 sweep hook 안을 쓰면 힌트 복원이 늦어진다 | `file_perm_alloc` 의 확장 조건(`file_manager.c:5197-5206`)과 경합 처리 |
| D. LSA 보류 페이지의 backoff | 보류가 풀리기 전의 반복 lap을 생략한다 | 다른 경우에는 효과가 없다 | horizon 전진 감지가 필요하다 | CBRD-26786 Remarks의 후속 후보 |

B는 지연 상한을 직접 보장하는 유일한 후보다. A, C, D는 lap 횟수를 줄이지만 lap 한 번의 비용은 그대로 둔다. 리뷰어는 A와 B를 함께 넣은 빌드만 측정했다. 동시 부하에서 fast path가 얼마나 자주 보류하는지 측정하면 A의 가치를 판별할 수 있다. 명세 결정이 B의 일시 증가를 받아들이는지가 B 채택을 좌우한다.

## Acceptance Criteria

- 재시작 직후 새 페이지가 필요한 첫 INSERT가 검사하는 페이지 수가 ANALYSIS에서 정한 상한 이하다. 서로 다른 두 파일 크기에서 같은 상한이 유지됨을 계측으로 확인한다.
- vacuum fast path가 삭제 배치의 빈 페이지를 모두 회수했으면 다음 새 페이지 할당은 회수 검사를 시작하지 않는다.
- 활성 쓰기 트랜잭션 때문에 빈 페이지가 LSA 게이트로 보류된 동안에도 새 페이지 할당 한 번의 검사량이 같은 상한 이하다.
- 다음 경우의 빈 페이지가 이후 할당 과정에서 회수된다. LSA 보류의 원인이 끝난 경우, fast path의 WRITE fix 미획득, fast path의 READ 경합으로 건너뛴 페이지, fast path 오류와 중단, 후보 목록 메모리 부족, SA·non-MVCC eager 삭제, INSERT rollback, 이전 부팅에서 남은 빈 페이지. `unit_tests/oos/test_oos_growth_sweep.cpp` 를 새 동작에 맞게 갱신하고 빠진 경우를 추가한다.
- 리뷰어의 400행 삭제·재삽입 시나리오와 CBRD-26786의 반복 삭제·재삽입 절차에서 OOS 사용 페이지가 현재 코드와 같은 수준으로 수렴한다. 허용하는 일시 증가량은 ANALYSIS에서 정한다.
- 재시작 직후 첫 INSERT와 1행 삭제·vacuum 뒤 INSERT의 지연을 현재 코드와 같은 release 빌드와 설정에서 반복 측정해 분포와 조건을 보고한다. 목표치는 ANALYSIS에서 정한다.
- OOS 명세 §4의 불변식과 sweep 규칙을 새 동작에 맞게 갱신하거나, 현재 불변식을 유지하는 설계임을 근거와 함께 기록한다.

## Definition of done

- `UNIT_TEST_OOS=ON` 으로 구성한 빌드에서 OOS 단위 테스트가 모두 통과한다.
- 지연 측정 보고서에 실행 횟수, 분산, 제한 요인을 적는다.
- OOS 명세 갱신이 반영된다.
- PR #7990 R3 리뷰 thread에 이 이슈와 처리 결과를 연결한다.

## Triage Request

이 문제를 확인하고 작성자 측에 ANALYSIS 배정을 요청한다. 부모는 CBRD-26978로 제안하고 CBRD-26786, CBRD-27213과 관련 이슈로 연결한다. ANALYSIS에서는 다음을 확인한다.

- 동시 쓰기 부하에서 fast path의 회수·보류 비율과 lap 발생 빈도.
- 오래 열린 쓰기 트랜잭션이 있을 때 할당마다의 검사량과 지연.
- 명세 §4 불변식의 수정 여부와 허용하는 일시 증가량.
- 할당당 상한의 크기와 sector 수집 비용의 처리.
- R4(PR #7990 r4409283403)의 sweep hook 안, CBRD-27213의 재시작 순회와의 순회 코드 공유 여부. R4 자체는 이 이슈 범위가 아니다.
~~~~

## 남은 불확실성과 해소할 증거

| 불확실성 | 판단에 주는 영향 | 해소할 증거 |
| --- | --- | --- |
| 동시 쓰기 부하에서 fast path가 빈 페이지를 얼마나 자주 보류하는가 | (a)의 효과 크기. 보류가 잦으면 (a)만으로는 lap이 줄지 않는다 | 격리 환경의 server mode에서 쓰기 세션 여러 개와 OOS 테이블 UPDATE·DELETE 부하를 함께 돌린다. `oos_reclaim_empty_pages` 의 "reclaimed, deferred" trace와 lap당 검사 페이지 수를 같은 구간에서 수집한다 |
| 오래 열린 쓰기 트랜잭션이 있을 때 할당마다 lap을 반복하는가, 그 비용은 얼마인가 | 병합 전 처리 여부. 지연이 크면 병합 전으로 바꾼다 | 한 세션이 쓰기 트랜잭션을 연 채 두고, 다른 세션이 삭제·vacuum 뒤 새 페이지가 필요한 INSERT를 반복한다. 두 파일 크기에서 INSERT 지연과 lap 횟수를 잰다 |
| 리뷰어의 100만 페이지 추정 | 우선순위 | 리뷰어 시나리오를 두 파일 크기 이상에서 재현해 크기 비례를 확인한다. `benchmark-checklist` 와 격리 환경을 쓴다 |
| hornetmj가 R3를 병합 조건으로 보는가 | 부모(CBRD-26978 대 CBRD-26583)와 처리 시점 | R3 thread에서 리뷰어 답을 받는다 |
| CBRD-27816의 "OOS reclaim tail" 이 무엇을 가리키는가 | 같은 문제를 다른 이름으로 기록했을 가능성 | CBRD-27785 작업 기록이나 작성자에게 확인한다. live 이슈와 로컬 문서에는 정의가 없다 |
| lap이 버퍼 풀의 다른 페이지를 밀어내는 영향 | 영향 범위 | lap 전후의 버퍼 적중률과 다른 테이블 질의 지연을 비교한다 |
| 리뷰어 프로토타입이 무장 경로를 어디까지 처리했는가 | (a)의 정확성 위험 | 리뷰어에게 프로토타입 diff를 요청한다 |

## 부록. 조회 기록

GitHub 조회는 다음과 같다.

- 2026-11-02 19:28:15 KST. `gh api repos/CUBRID/cubrid/pulls/7990/comments`, `.../pulls/7990/reviews`, `.../issues/7990/comments`, 모두 `--paginate`. GraphQL `reviewThreads` 와 `headRefOid`.
- 19:30:44 KST. PR 7617의 같은 세 endpoint.
- 19:36:23 KST. `gh pr list --repo CUBRID/cubrid --state all --search "sweep in:title,body OOS"` 결과는 PR 7617 하나였다. `feature/oos-merge` 대상 열린 PR 6건의 `gh pr diff` 에서 `oos_reclaim_sweep_step|swept_this_boot|pending_deletes|oos_alloc_page_with_reclaim|oos_reclaim_note_delete` 를 바꾸는 줄은 0개였다.

live 이슈 조회(`cubrid-jira search KEY --no-recurse`)는 다음과 같다.

- 19:30:21 KST. CBRD-26786, 27213, 27785, 26583, 26357.
- 19:31:37 KST 전후. CBRD-26517, 27788, 27350, 26950, 27816, 26659, 26824, 26978, 26835.

JQL은 19:31:08 KST와 19:31:22 KST에 실행했다.

```text
project = CBRD AND text ~ "sweep" ORDER BY updated DESC
project = CBRD AND text ~ "스윕" ORDER BY updated DESC
project = CBRD AND text ~ "oos_reclaim_sweep_step" ORDER BY updated DESC
project = CBRD AND text ~ "oos_alloc_page_with_reclaim" ORDER BY updated DESC
project = CBRD AND text ~ "growth gate" ORDER BY updated DESC
project = CBRD AND text ~ "성장 게이트" ORDER BY updated DESC
project = CBRD AND text ~ "pending_deletes" ORDER BY updated DESC
project = CBRD AND text ~ "swept_this_boot" ORDER BY updated DESC
project = CBRD AND text ~ "file_get_all_data_sectors" ORDER BY updated DESC
project = CBRD AND text ~ "lazy iterator" ORDER BY updated DESC
project = CBRD AND text ~ "OOS" AND text ~ "회수" ORDER BY updated DESC
project = CBRD AND text ~ "7990" AND text ~ "hornetmj" ORDER BY updated DESC
project = CBRD AND parent = CBRD-26583 ORDER BY created DESC
project = CBRD AND parent = CBRD-26357 ORDER BY created DESC
project = CBRD AND parent = CBRD-26978 ORDER BY created DESC
project = CBRD AND parent = CBRD-26835 ORDER BY created DESC
project = CBRD AND text ~ "reclaim" AND text ~ "OOS" ORDER BY updated DESC
project = CBRD AND text ~ "materialize" ORDER BY updated DESC
project = CBRD AND text ~ "컬렉터" ORDER BY updated DESC
project = CBRD AND text ~ "backoff" AND text ~ "OOS" ORDER BY updated DESC
project = CBRD AND text ~ "horizon" AND text ~ "OOS" ORDER BY updated DESC
project = CBRD AND summary ~ "OOS" AND (summary ~ "성능" OR summary ~ "performance" OR summary ~ "perf") ORDER BY updated DESC
project = CBRD AND created >= "2026-10-28" AND summary ~ "OOS" ORDER BY created DESC
```

`issuetype = "Improve Function/Performance"` 조건은 JIRA가 HTTP 400으로 거부해 결과가 없다. sweep 심볼 검색은 CBRD-26786만 찾았다. `컬렉터`, `backoff`, `horizon` 검색은 CBRD-26786과 무관한 이슈만 찾았고, `lazy iterator` 는 0건이다.

이 분석은 OOS 명세 §4, CBRD-26786 live 본문, PR 7617 응답 보고서(`my-cubrid-docs/cbrd-26786/PR-7617-hornetmj-response-report_8ba9b5398_claude.md`), 기존 체크리스트의 R3 절과 "확정한 전달 방식" 절, 일정 보고서의 리뷰 누락 점검 절을 근거로 했다.
