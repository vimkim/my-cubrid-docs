# PR7990 R4의 추적 단위 분석

2026-11-02 Asia/Seoul 작성. 대상은 hornetmj의 PR7990 리뷰 R4 [r4409283403](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409283403)이다. 이 문서는 R4를 새 CBRD Sub-task로 추적할지, 기존 CBRD-27213에 편입할지 판단한다. 읽기 전용 분석이며 JIRA, GitHub, 소스 checkout은 바꾸지 않았다. 다른 agent의 R3 보고서는 읽지 않았다.

**후속 결정.** 2026-11-02 R3는 [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872)로 발급됐다. 이 문서의 "R3 추적 이슈"는 CBRD-27872를 가리킨다. 아래 CBRD-27213 보강 제안의 완료 조건 4번은 CBRD-27872와 겹치므로 [R3·R4 추적 단위 종합](PR-7990-R3-R4-tracking-decision_dcbf09e_claude.md#중복-제안을-조정한다)에서 범위를 나눴다. 아래 분석은 작성 당시 그대로 둔다.

## 결론은 기존 이슈 확장·연결이다

**결론은 `기존 이슈 확장·연결`이다.** R4를 [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213)에 명시적으로 편입한다. 지금 새 Sub-task를 만들지 않는다.

다만 CBRD-27213의 현재 본문만으로는 R4가 추적되지 않는다. 편입이 성립하려면 CBRD-27213에 다음 네 가지를 보강해야 한다. 보강 문안은 [CBRD-27213 보강 제안](#cbrd-27213-보강-제안)에 있다.

1. 현재 legacy 경로의 결함을 기록한다. 3단계 sync의 발동 조건이 쓰는 `estimates.num_pages`가 실제 헤더에 기록되지 않아, 운영 경로에서 sync가 실행되지 않는다.
2. R4 재현 시나리오를 완료 조건에 넣는다. 부분적으로 빈 페이지가 힌트 용량보다 많은 경우와 비정상 종료 뒤 재시작도 포함한다.
3. 설계 기준을 다시 정한다. CBRD-27213은 CBRD-26176의 candidate queue와 30초 snapshot을 기준으로 하지만, heap의 후속 재설계 [CBRD-27761](https://jira.cubrid.org/browse/CBRD-27761)은 바로 그 구조가 재시작 뒤 빈 공간을 잊는다고 보고 제거하려 한다.
4. OOS 병합 시점의 legacy 경로가 이 결함을 가진 채 들어간다는 점을 알려진 제약으로 명시한다.

이 결론을 고른 근거는 다음과 같다.

- 리뷰어가 처리 방향을 정했다. 원댓글 첫 문장은 "bestspace redesign 안정화 후 oos에 적용 계획"이다 [리뷰어 보고]. 이번 검색 범위에서 heap의 bestspace 구조를 OOS에 적용하는 live 이슈는 CBRD-27213 하나다 [관찰].
- legacy 수정은 버려진다. CBRD-27213의 정리 목록은 전역 해시, `best[10]`, sync scan을 모두 삭제한다 [관찰, CBRD-27213 Lifecycle and cleanup]. 그 전에 같은 경로를 고치면 재설계 때 함께 지운다.
- legacy 수정의 유력한 방법은 R3에 묶인다. 리뷰어가 검증한 방법은 회수 sweep이 방문하는 페이지를 힌트로 등록하는 것이다. 이 방법은 R3이 바꾸려는 sweep의 발동 조건과 순회량에 그대로 의존한다 [소스 추론].
- 영향은 공간 효율이다. 완전히 빈 페이지는 CBRD-26786의 sweep이 재시작 뒤에도 회수하고, 데이터 정합성은 영향받지 않는다 [소스 추론]. 리뷰어도 정합성 문제를 보고하지 않았다.

**새 Sub-task로 바꿀 조건.** 팀이 OOS develop 병합이나 11.5(guava) 릴리스에서 이 결함을 허용하지 않기로 정하면, legacy 경로의 결함 수정이 독립된 완료 경계를 갖는다. 그때는 CBRD-27213 밑이 아니라 CBRD-26583(Development Subject) 밑에 새 Sub-task를 만든다. CBRD-27213은 이미 Sub-task이므로 중첩 Sub-task를 만들 수 없다. 초안은 [조건부 대안인 신규 Sub-task 초안](#조건부-대안인-신규-sub-task-초안)에 있다.

## 조사 기준과 근거 표시

| 항목 | 값 |
| --- | --- |
| source checkout | `/home/vimkim/gh/cb/feature-oos-merge`, branch `feature/oos-merge` |
| source HEAD | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`. coordinator가 준 값과 같다. GraphQL로 조회한 PR7990 `headRefOid`도 같다. |
| checkout 상태 | 시작과 끝 모두 untracked `review.log` 하나뿐이다. 어떤 파일도 바꾸지 않았다. |
| GitHub 댓글 조회 | 2026-11-02 19:28:45 KST. `gh-pr-comments-all` 방식으로 inline 39건, review 25건, issue 39건을 받았다. thread 상태는 같은 시각 GraphQL로 조회했다. |
| JIRA 조회 | 2026-11-02 19:29:04 ~ 19:41:11 KST. `cubrid-jira search`, `comment-list`, `jql`을 썼다. |
| GitHub PR 검색 | 2026-11-02 19:32:22 KST |
| OOS 명세 | `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`, SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`, Last updated 2026-10-27. 저장소 HEAD `3462a7f`. 전체를 읽었다. |
| 보조 문서 | 리뷰 체크리스트(my-cubrid-docs `f1710851c`), 일정 저장소 main `ed28fb38a`, my-cubrid-jira HEAD `52577be` |

각 주장 뒤에 근거 종류를 붙인다.

- **[관찰]** 이번 조사에서 직접 본 소스 텍스트, JIRA·GitHub 조회 결과다.
- **[리뷰어 보고]** 원댓글에 적힌 리뷰어의 측정과 주장이다. 이번 조사에서 다시 측정하지 않았다.
- **[소스 추론]** 소스를 읽고 도출한 동작이다. 실행으로 확인하지 않았다.
- **[미확인]** 근거를 찾지 못했거나 확인하지 않은 사항이다.

## 원댓글의 요구

원댓글은 `src/storage/oos_file.cpp:3081`, commit `dcbf09e4f`에 달렸다. 2026-10-29 06:19 UTC에 작성되고 07:13 UTC에 수정됐다. thread는 미해결이고 outdated가 아니며 답글은 없다 [관찰].

- **처리 계획.** "bestspace redesign 안정화 후 oos에 적용 계획이지만, 문제 공유를 위해 커멘트는 남깁니다." [리뷰어 보고]. 어느 redesign 이슈인지는 적지 않았다.
- **증상.** 서버를 재시작하면 빈 공간이 넉넉한 OOS 페이지를 두고 새 페이지를 할당해 OOS 파일이 커진다 [리뷰어 보고].
- **측정 (release).** 7KB 값 400행 입력, 홀수 행 삭제, vacuum으로 절반쯤 빈 페이지 201개를 만든 뒤 100행을 넣었다. 재시작 없이는 201에서 201, 재시작 뒤에는 201에서 246 페이지가 됐고 쓰지 않는 공간은 1.17MB에서 1.91MB가 됐다. 재시작 뒤 발동 조건 검사 45번에서 `num_pages`와 `num_other_high_best`가 모두 0이었고 sync는 호출되지 않았다(gdb) [리뷰어 보고]. 측정한 build revision은 적혀 있지 않다 [미확인].
- **수정 방향.** 재시작 뒤 첫 할당의 회수 sweep이 부분적으로 빈 페이지를 bestspace 힌트로 등록한다. 리뷰어의 수정 빌드에서 재시작 뒤 100행 입력 시 201에서 202 페이지, 쓰지 않는 공간 1.19MB였다 [리뷰어 보고].
- **추가 지적.** 비율 조건을 살려도 부족하다. sync가 매번 파일 앞쪽 20%(최대 100페이지)만 읽고 이어 읽을 위치(`full_search_vpid`)를 기록하지 않는다 [리뷰어 보고].

리뷰어 주장을 현재 코드와 대조한 결과다.

| 리뷰어 주장 | `dcbf09e4f`의 코드 | 구분 |
| --- | --- | --- |
| `num_pages`는 파일 생성 때 0 | `oos_create_file_internal`이 `OOS_HDR_STATS`를 `memset 0`으로 초기화한다 (`oos_file.cpp:1164-1172`) | 관찰 |
| `num_pages`를 기록하는 함수는 sync뿐 | 쓰기는 `oos_stats_sync_bestspace`의 `oos_file.cpp:985`, `1001` 두 곳뿐이다 | 관찰 |
| 그마저 임시 복사본에 써서 버림 | 운영 호출은 `oos_find_best_page`의 `oos_file.cpp:3103-3105` 한 곳이고 `tmp_hdr`를 넘긴다. 다른 호출자 `bridge_oos_stats_sync_bestspace`는 `CUBRID_UNIT_TEST_ENABLED` 구간(`oos_file.cpp:3913-4083`)에만 있다 | 관찰 |
| 그래서 sync가 실행되지 않음 | 실제 헤더의 `num_pages`가 늘 0이라 `ratio`는 0이고 `oos_file.cpp:3086` 조건이 거짓이다 | 소스 추론. 리뷰어는 gdb로 확인했다고 보고 |
| 재시작 뒤 `best[10]`만 쓰고 나머지는 새 페이지 | 전역 해시는 서버 시작 때 새로 만들어진다. `best[]`는 헤더에 로그 없이 남는 힌트다 | 소스 추론 |
| 재시작 뒤 첫 할당의 sweep이 모든 페이지를 고정해 확인 | 부팅 규칙(`oos_file.cpp:1840-1849`, `1868`)으로 첫 성장 때 순회한다. 단 첫 회수 성공에서 멈추고 바쁜 페이지는 건너뛴다 | 관찰(코드), 소스 추론(동작) |
| sync는 앞쪽 20%(최대 100)만 읽고 이어 읽지 않음 | `oos_file.cpp:869-877`, 루프가 항상 0부터 시작(`892`), `full_search_vpid`는 쓰지 않는다는 주석(`960-961`) | 관찰 |

## 현재 코드의 재시작 후 bestspace 경로

`how` skill의 출력 형식으로 정리한다. 범위가 한 모듈이라 직접 읽었고 별도 explorer는 쓰지 않았다.

### Overview

OOS는 청크를 넣을 페이지를 세 단계 힌트로 찾고, 모두 실패하면 회수 sweep을 거쳐 새 페이지를 할당한다. 재시작은 메모리 힌트를 지우고, 헤더 힌트 10개만 남긴다. 이를 다시 채워야 할 3단계 sync는 발동 조건이 쓰는 값이 실제 헤더에 기록되지 않아 운영 경로에서 실행되지 않는다 [소스 추론]. 회수 sweep은 재시작 뒤 파일을 순회하지만 완전히 빈 페이지만 회수하고, 부분적으로 빈 페이지의 여유 공간은 기록하지 않는다 [관찰].

### Key concepts

| 이름 | 위치 | 재시작 뒤 상태 |
| --- | --- | --- |
| 전역 해시 캐시 `oos_Bestspace` | 메모리. `heap_manager_initialize`(`heap_file.c:3796`, `3819`)가 `oos_bestspace_initialize`(`oos_file.cpp:266`)로 만든다 | 비어 있다 [소스 추론] |
| 해시 용량 `OOS_BESTSPACE_CACHE_CAPACITY` | `oos_file.cpp:130`, 모든 OOS 파일 합계 1000개 | 가득 차면 `oos_stats_add_bestspace`가 등록을 거부한다(`oos_file.cpp:373-377`). 축출은 없다 [관찰] |
| 헤더 힌트 `best[10]`, `second_best[10]` | 각 OOS 파일의 sticky 첫 페이지 `OOS_HDR_STATS` (`oos_file.hpp:132-152`) | 로그 없이 dirty로 표시한다. 정상 종료 때 flush되면 남는다. 비정상 종료 뒤에는 미확인 [미확인] |
| `estimates.num_pages`, `num_other_high_best` | 같은 헤더 | 운영 경로에서 `num_pages`는 생성 이후 계속 0이다 [소스 추론]. `num_other_high_best`는 `best[]`에서 밀려날 때만 증가한다(`oos_file.cpp:1058`) [관찰] |
| `estimates.full_search_vpid` | 같은 헤더 | 쓰지 않는다. 레이아웃 유지를 위해 필드만 남았다(`oos_file.cpp:960-961`) [관찰] |
| 회수 side map `oos_Reclaim_states` | 메모리 `{pending_deletes, swept_this_boot, sweep_in_progress, sweep_cursor}` (`oos_file.cpp:1291-1301`) | 비어 있다. 항목이 없으면 부팅 규칙으로 첫 성장 때 sweep을 한다 [관찰] |
| 여유 공간 기준 `OOS_DROP_FREE_SPACE` | `oos_file.cpp:131`, 페이지의 30% | 이 값보다 여유가 크면 힌트 대상이다 [관찰] |

### How it works

재시작 뒤 새 OOS 값을 넣을 때의 흐름이다. 줄 번호는 `dcbf09e4f`의 `src/storage/oos_file.cpp`다.

```text
oos_insert / oos_insert_many
  oos_find_best_page (3017)
    헤더 페이지 WRITE latch (3033)
    oos_stats_find_page_in_bestspace (559)
      Phase A: 전역 해시 조회 (589-628)       재시작 뒤 비어 있음
      Phase B: 헤더 best[] 조회 (630-648)     최대 10개
      Phase C: 후보 conditional fix, 소유·여유 공간 실측 (655-745)
    miss이면 ratio = num_other_high_best / num_pages (3080-3084)
      num_pages == 0 이라 ratio == 0, sync 분기에 들어가지 않음 (3086)
      [들어가더라도] tmp_hdr로 oos_stats_sync_bestspace 호출 후 버림 (3103-3105)
    헤더 unfix (3150)
    oos_alloc_page_with_reclaim (2019)
      oos_reclaim_sweep_step (1823)
        side map 항목 없음, 또는 pending_deletes > 0, 또는 !swept_this_boot 이면 순회 (1840-1874)
        섹터 비트맵의 데이터 페이지마다 oos_try_reclaim_page_internal (1945-1995)
          Phase 1: READ conditional fix로 비었는지만 확인 (1583-1602)
            비어 있지 않으면 여유 공간을 버리고 SKIPPED
        첫 회수 성공에서 중단, 한 바퀴를 다 돌면 swept_this_boot = true (1975-1998)
      oos_file_alloc_new → file_alloc (2988)
    새 페이지의 여유 공간을 해시에 등록 (3154-3159)
```

삭제 쪽은 `oos_delete_chain`(`oos_file.cpp:3260`)이 슬롯을 지운 뒤 `oos_stats_update`(`oos_file.cpp:3392`)를 부른다. 이 함수는 여유 공간이 늘면 해시에 등록하고, 30%를 넘으면 헤더 `best[]`를 조건부 latch로 갱신한다(`oos_file.cpp:1066-1117`) [관찰]. 그래서 재시작 전에는 삭제로 생긴 여유 공간을 해시로 재사용한다. 재시작은 이 해시를 지우고, 이후 그 페이지에 다시 삭제가 일어나기 전까지 되살릴 경로가 없다 [소스 추론].

### Where things live

| 책임 | 위치 |
| --- | --- |
| 페이지 선택과 sync 발동 조건 | `oos_find_best_page`, `oos_file.cpp:3017-3166` |
| 해시·`best[]` 조회와 후보 검증 | `oos_stats_find_page_in_bestspace`, `oos_file.cpp:559-760` |
| 3단계 sync | `oos_stats_sync_bestspace`, `oos_file.cpp:836-1015` |
| 삭제 뒤 힌트 갱신 | `oos_stats_update`, `oos_stats_update_internal`, `oos_file.cpp:1021-1117` |
| 회수 sweep과 단일 성장 지점 | `oos_reclaim_sweep_step`, `oos_alloc_page_with_reclaim`, `oos_file.cpp:1822-2034` |
| 페이지 단위 회수 판정 | `oos_try_reclaim_page_internal`, `oos_file.cpp:1567-1707` |
| 헤더 형식 | `OOS_HDR_STATS`, `oos_file.hpp:132-152` |
| 재시작 모사 테스트 | `simulate_hint_loss`, `unit_tests/oos/test_oos_growth_sweep.cpp:58-90`. side map 초기화 hook `oos_test_reclaim_reset_side_map`, `oos_file.cpp:4027-4035` |

### Gotchas

- **sync가 멈춘 시점.** CBRD-26824 수정(PR #7297, `feat/oos` merge `03133632`, 2026-06-29)이 `|| try_find == 0`을 지웠다. 그 부모 `53e8d6b9a`도 이미 `tmp_hdr`로 sync를 불렀다 [관찰]. 따라서 수정 전에는 첫 miss마다 sync가 돌며 해시를 채웠고, 수정 뒤에는 늘 0인 비율 조건만 남아 sync가 멈췄다 [소스 추론]. R4는 CBRD-26824 수정의 부작용이다.
- **명세와 다르다.** OOS 명세 §2는 "on miss, `oos_stats_sync_bestspace()` ... recharge hints/cache"와 "Recovery rediscovers free space through sync"를 요구한다. 같은 절과 ADR-0001은 sync에 "VPID-based resume"을 요구한다. 현재 코드는 두 요구 모두 따르지 않는다 [소스 추론]. 명세 규칙상 구현 정합성 격차다. 명세의 implementation observations에는 이 격차가 기록돼 있지 않다 [관찰].
- **비율 조건만 고쳐도 부족하다.** `num_pages`를 실제 헤더에 남겨도 `num_other_high_best`는 `best[]`에서 밀려날 때만 증가한다(`oos_file.cpp:1058`). 여유 공간이 비슷한 페이지가 많으면 밀려남이 없어 0에 머문다 [소스 추론]. 리뷰어가 본 두 값 모두 0인 상태와 맞는다.
- **스윕 편승 수정도 용량에 막힌다.** 힌트를 해시에 넣는 방식은 모든 OOS 파일 합계 1000개에서 멈춘다(`oos_file.cpp:373-377`). 그보다 많은 부분 여유 페이지는 다시 잊힌다 [소스 추론]. CBRD-27761이 heap에서 지적한 "유한 캐시와 재발견 수단 부재"와 같은 형태다.
- **테스트가 운영 발동 조건을 거치지 않는다.** `simulate_hint_loss`의 주석은 `num_other_high_best`를 0으로 만들어야 sync가 힌트를 다시 채우지 않는다고 설명한다(`test_oos_growth_sweep.cpp:58-59`). 운영 경로에서는 `num_pages`가 0이라 원래 sync가 돌지 않는다. sync 테스트는 `bridge_oos_stats_sync_bestspace`를 실제 헤더와 `scan_all=true`로 직접 부른다(`test_oos_bestspace.cpp:1099`) [관찰]. 그래서 발동 조건이 죽은 상태를 테스트가 잡지 못했다 [소스 추론].
- **R4는 부분 여유 페이지만의 문제다.** 완전히 빈 페이지는 부팅 규칙의 sweep이 회수해 `file_alloc`이 재사용한다(`oos_file.cpp:1809-1821`) [관찰].

## 확인한 이슈와 검색 범위

### live로 읽은 이슈

| 이슈 | 유형 / 상태 | 부모 | 확인 내용 |
| --- | --- | --- | --- |
| [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213) | Sub-task / Open, Unassigned, Minor | CBRD-26978 | 본문·완료 조건 전체. 댓글 0건. 2026-09-18 이후 갱신 없음. 연결 PR 없음 |
| [CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978) | Task / Confirmed | 없음 | OOS 후속 TODO 묶음. 하위 13건. 댓글 0건 |
| [CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583) | Development Subject / Handover | 없음 | R1·R2·R5·R6 대응 이슈(CBRD-27827, 27860, 27858, 27841)의 부모 |
| [CBRD-26176](https://jira.cubrid.org/browse/CBRD-26176) | Sub-task / Closed, Fixed | CBRD-26857 | heap shard bestspace. OOS 언급 없음. 회귀 이슈 27120, 27325, 27122, 27576 |
| [CBRD-26857](https://jira.cubrid.org/browse/CBRD-26857) | Improve Function/Performance / Closed | 없음 | heap bestspace 재설계 Epic. 하위 5건 모두 heap. CBRD-27761과 relates |
| [CBRD-27761](https://jira.cubrid.org/browse/CBRD-27761) | Improve Function/Performance / Develop | 없음 | heap 전수 맵 도입. 재시작 뒤 재삽입 재사용이 완료 조건. OOS 언급 없음. draft [PR 8251](https://github.com/CUBRID/cubrid/pull/8251) OPEN. 댓글 0건 |
| [CBRD-27325](https://jira.cubrid.org/browse/CBRD-27325) | Correct Error / Resolved | 없음 | heap에서 sync 재발견 경로 제거 뒤 빈 페이지 미재사용 회귀 |
| [CBRD-26786](https://jira.cubrid.org/browse/CBRD-26786) | Sub-task / Resolved | CBRD-26583 | 빈 페이지 회수와 부팅 규칙 sweep. 부분 여유 페이지는 범위 밖. 댓글 1건(PostgreSQL VACUUM 참고) |
| [CBRD-26950](https://jira.cubrid.org/browse/CBRD-26950) | Sub-task / Closed | CBRD-26583 | CBRD-27213의 선행 조건 |
| [CBRD-26824](https://jira.cubrid.org/browse/CBRD-26824) | Sub-task / Resolved | CBRD-26835 | 첫 시도의 무조건 sync 조건(`try_find == 0`)을 제거했다. 발동 조건이 죽은 원인 |
| [CBRD-27827](https://jira.cubrid.org/browse/CBRD-27827) | Sub-task / Open | CBRD-26583 | R1. 같은 `oos_stats_find_page_in_bestspace`의 대기 설정 문제. 재시작과 무관 |
| [CBRD-26517](https://jira.cubrid.org/browse/CBRD-26517), [CBRD-27788](https://jira.cubrid.org/browse/CBRD-27788) | Sub-task / Open | CBRD-26978, CBRD-26583 | 재시작 뒤 bestspace 언급 없음. 27788의 restart는 조회 성능 측정 조건 |

### 검색어와 범위

JIRA는 `project = CBRD`에서 다음 JQL을 실행했다. q1~q6은 19:29:45 KST, q7~q8은 19:32:16 KST, q9는 19:34:54 KST, q10은 19:41:11 KST에 실행했다.

| # | JQL | 결과 |
| --- | --- | --- |
| q1 | `text ~ "bestspace" ORDER BY updated DESC` | 118건 중 최근 60건 확인 |
| q2 | `summary ~ "OOS" AND (text ~ "재시작" OR text ~ "restart")` | 15건 |
| q3 | `parent = CBRD-26978` | 13건 |
| q4 | `text ~ "num_other_high_best"` | 16건 |
| q5 | `text ~ "oos_stats_sync_bestspace"` | 6건 |
| q6 | `summary ~ "best space"` | 4건 |
| q7 | `parent = CBRD-26857` | 5건 |
| q8 | `text ~ "bestspace" AND text ~ "OOS" AND updated >= -30d` | 1건(CBRD-27827) |
| q9 | `key in (CBRD-26583, 27827, 27858, 27860, 27841, 26978, 27213)` | 유형·부모 확인 |
| q10 | `key in (CBRD-26824, 27788, 26517, 26658)` | 유형·부모 확인 |

q1은 갱신일 순 최근 60건만 봤다. 나머지 58건은 마지막으로 본 항목(2023-04-11 갱신)보다 오래된 갱신분이라 2026년에 도입한 OOS와 무관하다고 판단했다 [미확인, 개별 열람하지 않음]. 어느 검색에서도 R4의 결함, 원댓글, 재시작 뒤 OOS 부분 여유 페이지 재사용을 다루는 별도 이슈는 나오지 않았다 [관찰].

GitHub는 `CBRD-27761 in:title`(PR 8251 한 건)과 `CBRD-27213`(0건)으로 PR을 검색했다.

로컬 초안은 `~/gh/my-cubrid-jira`(HEAD `52577be`) 전체에서 `CBRD-27213`, `num_other_high_best|oos_stats_sync_bestspace`, `4409283403|CBRD-27761`을 검색했다. CBRD-27213 초안은 `issues/CBRD-27213-oos-bestspace-shared-module_725a32c_codex.md` 하나이고, live 본문과 표 정렬·대시 표기만 다르다 [관찰]. R4 원댓글이나 CBRD-27761을 언급한 로컬 초안은 없었다 [관찰].

## 중복 후보 비교

| 후보 | R4와 겹치는 범위 | 빠진 범위 | 판단 |
| --- | --- | --- | --- |
| CBRD-27213 | 완료 조건에 "OOS snapshot을 저장한 뒤 restart하면 ... 기존 data page를 재사용한다", "점진 rebuild가 모든 data page를 한 번 방문", "rebuild cursor가 청크마다 초기화되지 않고", "partial free page를 candidate로 즉시 공급"이 있다. R4의 결과 요구와 추가 지적(이어 읽기)을 결과 수준에서 덮는다 [관찰] | 현재 결함을 모른다. AS-IS가 sync를 정상 동작으로 서술한다. R4 재현 시나리오가 없다. 재설계 기준인 128칸 candidate queue와 snapshot은 CBRD-27761이 heap에서 재시작 뒤 공간을 잊는 원인으로 지목한 구조다. 담당자·target version·PR이 없다 [관찰] | 편입 대상. 보강 필요 |
| CBRD-27761 | 재시작 뒤 재삽입에서 새 페이지를 할당하지 않는 것이 완료 조건이다 [관찰] | heap 전용이다. OOS, `FILE_OOS`, `oos_*` 언급이 없다 [관찰] | R4를 직접 추적하지 않는다. 리뷰어가 말한 redesign일 가능성이 높으나 미확인이다. CBRD-27213의 설계 기준으로 연결한다 |
| CBRD-26857, CBRD-26176 | heap bestspace 구조 | heap 전용이고 둘 다 Closed다 | 무관 |
| CBRD-26786 | 재시작 뒤 부팅 규칙 sweep으로 빈 페이지를 회수한다 [관찰] | 부분 여유 페이지는 범위 밖이다. Resolved다 | R4 미포함 |
| CBRD-26658, CBRD-26824 | 3단계 bestspace를 만들고, 발동 조건을 바꿨다 | 둘 다 Closed 또는 Resolved다. 재시작 재발견을 검증하지 않았다 | 원인 이력으로만 연결한다 |
| CBRD-27325 | sync 재발견 경로 제거 뒤 빈 공간 미재사용이라는 같은 형태 | heap 전용, Resolved | 유사 사례로만 인용한다 |
| CBRD-27827 (R1) | 같은 후보 탐색 함수 | 대기 설정 문제다 | 무관 |
| CBRD-26517 | OOS TODO 기록 | 재시작 bestspace 언급 없음 | 무관 |

CBRD-27213은 관련만 있는 것이 아니라 R4의 결과 요구를 완료 조건에 이미 담고 있다. 그러나 결함 자체와 재현 기준은 담지 않았고, 설계 기준은 같은 결함을 heap에서 만든 구조다. 그래서 "이미 추적됨"이 아니라 "보강하면 추적됨"으로 판단한다.

## 추적 단위 비교

| 기준 | (a) legacy 경로의 별도 결함 수정 | (b) CBRD-27213에 편입 |
| --- | --- | --- |
| 리뷰어 계획 | 원댓글의 수정 방향과는 맞지만 "redesign 안정화 후 적용" 계획과 다르다 | 원댓글의 계획과 같다 |
| 해결 시점 | OOS 병합 전후 곧바로 가능하다 | heap 재설계 안정화와 CBRD-27213 착수 뒤다. 일정이 없다 |
| 작업의 수명 | CBRD-27213이 legacy 구현을 지우면 함께 지운다 | 최종 구조에 남는다 |
| R3 의존 | 스윕 편승 방식이면 R3의 발동 조건·순회 상한 결정 뒤에야 설계할 수 있다 | 재설계의 rebuild 순회와 CBRD-26786 sweep의 중복만 ANALYSIS에서 정하면 된다 |
| 근본 원인 처리 | 스윕 편승만 하면 죽은 3단계 sync가 남는다. 근본 처리를 하려면 발동 조건 복구와 이어 읽기 구현, 또는 3단계 삭제와 명세 수정 중 하나를 골라야 한다 | 3단계 sync 자체를 삭제한다 |
| 명세 정합 | 수정하면 §2의 재시작 재발견 요구를 충족한다 | 병합 시점부터 재설계 완료까지 격차가 남는다. 알려진 제약으로 선언해야 한다 |
| 완료 경계 | 재시작 시나리오 하나로 독립 검증할 수 있다 | 큰 재설계의 완료 조건 중 하나가 된다 |
| 사용자 영향 | 재시작 뒤 OOS 파일 증가가 곧 사라진다 | 재설계 전까지 재시작마다 부분 여유 공간이 버려질 수 있다 |

(b)를 고른다. (a)의 장점은 빠른 해결과 명세 정합이다. 그러나 리뷰어가 처리 방향을 이미 정했고, 사용자가 2026-11-02 R3·R4를 차주 계획에서 보류했다. 영향은 공간이고 정합성이 아니다. (a)는 R3의 sweep 결정에 묶이고, 결국 재설계 때 지운다. 이 조건에서 (a)를 지금 새 이슈로 여는 것은 아무도 요청하지 않은 임시 작업을 추적 항목으로 만드는 일이다.

(b)의 비용은 명세 격차가 병합 뒤까지 남는다는 점이다. 이 비용은 숨기지 않고 선언해야 한다. CBRD-27213의 Remarks, PR7990의 알려진 제약, OOS 명세의 implementation observation에 기록한다.

## CBRD-27213 보강 제안

`cubrid-jira-issue-write` 형식에 맞춘 로컬 제안이다. live에 게시하지 않았다. 기존 본문의 나머지는 유지하고, 아래 부분만 바꾸거나 더한다.

### 대상과 관계

- 대상은 CBRD-27213(Sub-task, Open)이다. 부모 CBRD-26978(Task, Confirmed)은 유지한다. CBRD-27213 자체가 Sub-task이므로 R4를 그 밑의 중첩 Sub-task로 만들지 않는다.
- 링크를 더한다. CBRD-27761과 relates(설계 기준), CBRD-26824와 relates(발동 조건이 멈춘 변경), 원댓글 URL을 References에 넣는다.
- 유형 제안은 바꾸지 않는다. 기존 Remarks대로 Sub-task를 유지하고 성격은 기능·성능 개선이다. 문제 범주에 자원 효율(공간)을 더한다.

### 제안 제목

```text
[OOS] [TODO] 재시작 뒤에도 OOS 빈 공간을 재사용하도록 bestspace를 heap 재설계 기반으로 전환
```

### Issue Triage 변경안

```markdown
**이슈 수행 목적**: OOS 페이지 선택을 heap bestspace 재설계(CBRD-26857과 후속 CBRD-27761)와 같은 공통 모듈로 전환한다. 서버 재시작이나 비정상 종료 뒤에도 기존 OOS 페이지의 부분 여유 공간을 다시 찾아 재사용하게 하고, OOS 전용 legacy bestspace는 제거한다.

**이슈 수행 이유**: 현재 OOS는 페이지 선택마다 헤더 WRITE latch와 전역 mutex를 거친다. 또한 재시작 뒤 빈 공간을 다시 찾지 못한다. 3단계 sync의 발동 조건이 쓰는 `estimates.num_pages`가 실제 헤더에 기록되지 않아 운영 경로에서 sync가 실행되지 않는다. PR7990 리뷰가 이 결함을 재현과 함께 보고했고, 리뷰어는 bestspace 재설계가 안정된 뒤 OOS에 적용하는 계획을 밝혔다.

**영향**: 동시 INSERT의 성능 저하에 더해 공간 낭비가 생긴다. 리뷰어 측정(release)에서 절반쯤 빈 OOS 페이지 201개가 있는 파일에 같은 크기 값 100행을 넣으면, 재시작 없이는 페이지가 늘지 않았고 재시작 뒤에는 246개로 늘었다. 데이터 정합성에는 영향이 없다. 완전히 빈 페이지는 CBRD-26786의 회수 sweep이 재시작 뒤에도 회수한다. 실제 운영 부하에서의 증가 폭은 측정하지 않았다.

**이슈 수행 방안**: TBD - heap 재설계(CBRD-27761)가 안정된 뒤 ANALYSIS 단계에서 공통 모듈의 기준 구조와 구현 범위를 다시 확정한다. 기존 합의 방안 표의 candidate queue와 30초 snapshot은 CBRD-27761이 heap에서 제거하려는 구조이므로 재검토 대상이다. 그 표는 재확정 전까지 참고안으로 남긴다. 확정 전까지 OOS legacy 경로는 고치지 않고, 재시작 뒤 부분 여유 페이지 미재사용을 알려진 제약으로 둔다.
```

### Description에 더할 절

```markdown
### 재시작 뒤 빈 공간을 다시 찾지 못한다 (PR7990 리뷰)

OOS는 빈 공간 힌트를 세 곳에 둔다. 전역 해시 캐시는 메모리에만 있어 서버가 시작될 때 비어 있다. 헤더의 `best[10]`은 로그 없이 갱신하는 힌트이므로 재시작 뒤 남아도 10개다. 이를 보충하는 수단이 3단계 sync다.

`oos_find_best_page`는 `num_other_high_best / num_pages`가 0.1 이상일 때만 `oos_stats_sync_bestspace`를 부른다. `num_pages`를 쓰는 코드는 이 sync 함수뿐이고, 운영 경로는 sync에 임시 헤더를 넘긴 뒤 버린다. 파일 생성 때 0으로 초기화된 `num_pages`는 계속 0이므로 비율도 0이고, sync는 실행되지 않는다. CBRD-26824가 매 INSERT 첫 시도의 무조건 sync(`|| try_find == 0`)를 제거한 뒤부터의 동작이다.

sync가 실행되더라도 매번 파일 앞쪽 20%(최대 100페이지)만 읽고 이어 읽을 위치를 기록하지 않는다. `num_other_high_best`도 `best[]`에서 밀려난 페이지만 센다. 재시작 뒤 첫 성장 때 CBRD-26786의 회수 sweep이 데이터 페이지를 순회하지만, 완전히 빈 페이지만 회수하고 부분 여유 페이지의 여유 공간은 기록하지 않는다.

리뷰어 재현 결과(release 빌드)는 다음과 같다. 7KB 값 400행을 넣고 홀수 행을 삭제한 뒤 vacuum해 절반쯤 빈 OOS 페이지 201개를 만들고, 같은 크기 값 100행을 넣었다.

| 조건 | OOS 페이지 | 쓰지 않는 공간 |
| --- | --- | --- |
| 재시작 없음 | 201 → 201 | 기록 없음 |
| 재시작 뒤 | 201 → 246 | 1.17MB → 1.91MB |
| 리뷰어 수정 빌드(회수 sweep이 부분 여유 페이지를 힌트로 등록), 재시작 뒤 | 201 → 202 | 1.19MB |

원 보고는 https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409283403 이다.

heap에서도 같은 형태의 문제가 CBRD-27325로 보고됐고, CBRD-27761은 유한 캐시와 snapshot 대신 모든 페이지를 덮는 맵으로 해결하려 한다. OOS의 재설계 기준도 이 결론을 따라야 같은 결함을 다시 만들지 않는다.
```

### Acceptance Criteria에 더할 항목

```markdown
- [ ] 부분 여유 OOS 페이지가 있는 파일에서 서버를 정상 재시작한 뒤 같은 크기 값을 넣으면, 재시작하지 않은 대조군과 같은 수준으로 기존 페이지를 재사용한다. PR7990 리뷰의 재현 시나리오를 포함하며, 허용 차이는 ANALYSIS에서 정한다.
- [ ] 부분 여유 페이지 수가 메모리 힌트 용량보다 많은 파일과, OOS 파일이 여러 개인 DB에서도 위 결과가 성립한다.
- [ ] 비정상 종료 뒤 재시작해도 부분 여유 페이지의 재사용이 회복된다. 회복까지 허용하는 지연은 ANALYSIS에서 정한다.
- [ ] 재시작 뒤 재발견 순회와 CBRD-26786의 성장 게이트 sweep이 같은 섹터 비트맵을 중복 순회하지 않거나, 중복을 허용하는 근거를 기록한다. INSERT 한 건이 떠안는 순회량의 상한을 정한다.
- [ ] 재시작 재사용 테스트는 운영 경로의 발동 조건을 거친다. 내부 sync 함수를 직접 호출하는 테스트만으로 대신하지 않는다.
```

### Remarks에 더할 항목

```markdown
- 이 이슈가 끝나기 전에 develop에 병합되는 OOS legacy 경로는 재시작 뒤 부분 여유 페이지를 재사용하지 못한다. 병합 PR 설명 또는 QA 노트에 알려진 제약으로 기록한다.
- 재설계 착수가 늦어져 이 제약을 받아들일 수 없게 되면, legacy 경로의 결함 수정을 별도 Sub-task로 분리한다.
```

## 조건부 대안인 신규 Sub-task 초안

팀이 OOS develop 병합이나 11.5 릴리스에서 R4를 허용하지 않기로 정할 때만 쓴다. 지금 만들 것을 권하지 않는다.

- **제목.** `[OOS] 서버 재시작 뒤 부분적으로 빈 OOS 페이지를 재사용하지 못해 OOS 파일이 커진다`
- **유형.** Sub-task. 문제 범주는 자원 효율과 명세 정합이다.
- **부모.** 병합 전 처리라면 CBRD-26583(Development Subject, Handover)이다. R1·R2·R5·R6 대응 이슈가 같은 부모다. 병합 뒤 처리라면 CBRD-26978(Task, Confirmed)이다. CBRD-27213은 Sub-task라 부모가 될 수 없다.
- **관계.** CBRD-27213과 relates. 재설계가 이 수정과 legacy 구현을 함께 지운다. CBRD-26824와 relates. R3 추적 이슈가 생기면 sweep 계약 의존으로 연결한다.
- **이슈 수행 목적.** 서버 재시작 뒤에도 기존 OOS 페이지의 부분 여유 공간을 다시 찾아, 재시작 여부와 관계없이 같은 수준으로 페이지를 재사용한다.
- **이슈 수행 이유.** 3단계 sync의 발동 조건이 실제 헤더에 기록되지 않는 값을 읽어 운영 경로에서 실행되지 않는다. 명세가 요구하는 재시작 뒤 재발견이 없다.
- **영향.** 리뷰어 측정에서 재시작 뒤 100행 입력에 페이지가 201에서 246으로 늘었다. 정합성 영향은 없다.
- **이슈 수행 방안.** TBD - ANALYSIS 단계에서 해결 방안과 구현 범위를 결정한다.
- **최소 범위.** 재시작 뒤 부분 여유 페이지의 재발견. 죽은 발동 조건을 남기지 않는다.

ANALYSIS가 비교할 후보다. 확정한 설계가 아니다.

| 후보 | 기대 효과 | 한계와 실패 조건 | 비용·위험 | 근거와 확인 사항 |
| --- | --- | --- | --- | --- |
| 회수 sweep의 Phase 1에서 부분 여유 페이지를 힌트로 등록 | 추가 페이지 읽기 없이 첫 성장 한 번으로 힌트를 되살린다 | 해시 용량 1000개(전체 OOS 파일 합계)를 넘으면 다시 잊는다. 부팅 규칙이 바뀌거나 순회량에 상한이 생기면 회복이 늦어진다. 죽은 sync가 그대로 남는다 | 변경이 작다. R3 결정에 의존한다 | 리뷰어 수정 빌드에서 201에서 202 페이지 [리뷰어 보고]. R3 확정 뒤 같은 시나리오 재측정 필요 |
| 3단계 sync 발동 조건 복구 | 명세 §2와 ADR-0001에 맞춘다 | `num_pages`, `num_other_high_best`를 실제 헤더에 유지하고 `full_search_vpid` 이어 읽기를 구현해야 한다. `num_other_high_best` 집계 방식도 바꿔야 한다. sync 중 헤더 latch를 다시 잡는 비용이 있다 | 변경이 크고 CBRD-26824 같은 INSERT 지연 회귀 위험이 있다 | 발동 빈도와 INSERT 지연을 측정해야 한다 |
| 3단계 sync 삭제와 sweep 기반 재발견으로 대체 | 죽은 코드와 명세 격차를 함께 없앤다 | 첫 후보와 같은 용량 한계가 있다. 명세 §2를 고쳐야 한다 | 중간 | 명세 소유자의 합의가 필요하다 |

완료 조건 초안이다.

- [ ] PR7990 리뷰의 재현 시나리오에서 재시작 뒤 페이지 증가가 재시작하지 않은 대조군과 같은 수준이다.
- [ ] 부분 여유 페이지가 힌트 용량을 넘는 경우의 동작을 측정하고 기록한다.
- [ ] 운영 경로의 발동 조건을 거치는 단위 테스트를 둔다. 기존 `simulate_hint_loss`와 side map 초기화로 재시작을 모사하고, 부분 여유 페이지의 재사용을 확인한다.
- [ ] 3단계 sync는 실제로 동작하거나 삭제된다. 어떤 운영 경로로도 실행되지 않는 분기를 남기지 않는다.

## R3·R4의 겹침과 의존성

- **같은 순회를 공유한다.** R3은 `oos_reclaim_sweep_step`의 발동 조건(`oos_file.cpp:1868`)과 할당당 순회량을 문제 삼는다. R4의 리뷰어 수정안은 같은 순회의 Phase 1에 힌트 등록을 더한다 [관찰]. 원댓글 기준으로 R3은 부팅 규칙을 없애자고 하지 않는다. 삭제마다 sweep을 켜는 조건을 vacuum 즉시 회수가 처리하지 못한 경우로 좁히고, 할당당 상한(측정 빌드 64페이지)과 이어 읽기를 두자고 제안한다 [리뷰어 보고].
- **legacy 수정이면 R3이 먼저다.** R3의 상한이 들어가면 R4의 힌트 복원은 할당마다 최대 상한만큼만 진행한다. 그 사이 할당은 새 페이지를 쓴다. 리뷰어의 201에서 202 결과는 상한 없는 한 바퀴를 전제로 한다 [소스 추론]. R3이 부팅 규칙을 바꾸면 R4 편승 수정은 발동 지점을 잃는다. 두 legacy 수정을 모두 한다면 R3의 sweep 계약을 먼저 정하고, R4는 같은 시나리오로 함께 검증해야 한다. 체크리스트의 기존 항목 "지금 수정하는 경우 R3의 bounded sweep과 함께 회수·힌트 등록을 검증한다"와 같다.
- **CBRD-27213 편입이면 필수 의존은 없다.** 재설계는 해시, `best[]`, sync를 지운다. 남는 겹침은 재시작 뒤 재발견 순회와 CBRD-26786 sweep이 같은 섹터 비트맵을 각각 도는 문제다. 이는 R3이 지적한 순회 비용과 같은 성격이라, CBRD-27213의 완료 조건에 상한을 정하는 항목으로 넣었다.
- **R3을 R4의 선행 조건으로 만들지 않는다.** R3은 INSERT 지연, R4는 공간 재사용이다. 결과와 검증 시나리오가 다르다. R4를 CBRD-27213에 넣으면 R3은 독립적으로 결정할 수 있다.

## 병합 전 처리인지 후속인지

후속 처리로 본다. 근거는 다음과 같다.

- 리뷰어가 redesign 안정화 후 적용을 밝혔다 [리뷰어 보고].
- 사용자가 2026-11-02 차주 계획에서 R3·R4를 보류했고, 보류는 해결이나 면제가 아니라고 기록했다 [관찰, 일정 보고서와 week-2026-11-09].
- 영향은 공간이고 정합성이 아니다. 완전히 빈 페이지는 재시작 뒤에도 회수된다 [소스 추론].

후속 처리에는 조건이 있다.

- 원댓글 thread는 CBRD-27213 보강 뒤 그 링크로 답하고, 미해결로 둔다. 해결 처리는 재설계 반영 뒤다.
- PR7990 설명 또는 QA 노트에 legacy 경로의 알려진 제약을 적는다.
- OOS 명세 §2의 "Recovery rediscovers free space through sync"는 `dcbf09e4f`에서 성립하지 않는다. 명세 저장소의 implementation observations에 이 격차와 추적 이슈를 기록할지 명세 소유자가 정한다.

## 남은 불확실성과 해소할 증거

| 불확실성 | 결론에 주는 영향 | 해소할 증거 |
| --- | --- | --- |
| 리뷰어가 말한 "bestspace redesign"이 CBRD-27761인지, OOS 적용을 따로 계획했는지 | 다른 이슈라면 편입 대상이나 설계 기준 링크가 바뀐다 | 원댓글 thread에서 리뷰어 확인. 또는 해당 redesign 이슈와 CBRD-27213의 링크 |
| 11.5(guava) 릴리스가 OOS legacy bestspace로 나가는지, CBRD-27213의 target version | 릴리스에 포함되고 재설계가 늦으면 신규 Sub-task 조건이 된다 | CBRD-27213 triage 결과와 target version. OOS 병합·릴리스 범위 합의 |
| 리뷰어 측정의 build revision | 수치가 `dcbf09e4f`와 다른 코드에서 나왔을 수 있다 | 격리 환경에서 `dcbf09e4f` release 빌드로 같은 시나리오를 재현한다. 400행 입력, 홀수 행 삭제, vacuum, 정상 재시작, 100행 입력 전후의 OOS 데이터 페이지 수를 비교하고, `oos_find_best_page`의 sync 분기 진입 횟수를 trace로 센다. 실행 중인 서버와 이 checkout은 쓰지 않고 `benchmark-checklist`를 따른다 |
| 비정상 종료 뒤 `best[10]`이 남는지 | 크래시 뒤 손실 폭이 정상 재시작보다 클 수 있다 | 같은 시나리오에서 정상 종료 대신 서버 강제 종료 후 재시작 |
| 실제 부하에서의 공간 증가 폭 | 병합 전 처리 여부 판단에 쓸 수 있다 | 부분 여유 페이지가 1000개를 넘는 파일, OOS 파일 여러 개, 삭제·삽입이 반복되는 부하에서 재시작 전후 페이지 수 |
| R3의 최종 sweep 계약 | legacy 수정을 고를 때만 영향이 있다 | R3 결정 기록 |

리뷰어 수치는 모두 원댓글의 관찰이다. 이번 조사에서 재시작 재현이나 성능 측정은 하지 않았다. 추적 단위 판단에 실측이 꼭 필요하지 않았기 때문이다. 위 실측은 CBRD-27213의 ANALYSIS나 신규 Sub-task 전환 판단 때 필요하다.

## 참고한 자료

- R4 원댓글 https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409283403
- 의존성 평가에 쓴 R3 원댓글 https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399899312
- 리뷰 체크리스트 `/home/vimkim/gh/my-cubrid-docs/cbrd-26357/PR-7990-hornetmj-review-checklist_20261029_codex.md`의 "R4. 재시작 후 bestspace 복원", "확정한 전달 방식", "PR 방식 검토 이력과 의존 관계"
- 일정 `/home/vimkim/temp/my-cubrid-schedule/reports/2026-11-02-oos-merge-schedule.md`의 "PR7990 리뷰 누락 점검", `/home/vimkim/temp/my-cubrid-schedule/weekly/week-2026-11-09.md`
- 로컬 초안 `/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27213-oos-bestspace-shared-module_725a32c_codex.md`
- OOS 명세 `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` §2 Best Page Policy, §4 Empty-Page Reclaim Invariant, `docs/adr/0001-oos-page-enumeration-non-numerable.md`
- 원인 이력은 `feat/oos` merge `03133632701441320886f756ed4af902779d2c01`(CBRD-26824, PR #7297)과 부모 `53e8d6b9a41b14a091932625b72601ac7e80cfd1`의 `src/storage/oos_file.cpp`이다.
