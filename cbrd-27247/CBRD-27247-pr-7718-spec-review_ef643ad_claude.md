# CBRD-27247 / PR #7718 Spec Review

- PR: https://github.com/CUBRID/cubrid/pull/7718 — Reuse the previous insert page before searching bestspace
- JIRA: http://jira.cubrid.org/browse/CBRD-27247
- 리뷰 대상: `origin/develop` (`453da49c8`) ... PR head `ef643ad15`
  - 비머지 커밋: `e307a900d` (Reuse the previous insert page before searching bestspace), `a124f6296` (Make the insert page hint follow the search's space rule and bookkeeping)
  - 파일: `src/storage/bestspace.cpp`, `src/storage/bestspace.hpp`, `src/storage/heap_file.c`, `src/storage/heap_file.h`
- 리뷰 축: **Spec** — JIRA 설명과 PR 본문(Purpose / Implementation / Remarks)이 요구한 동작을 코드가 그대로 구현하는지. 코딩 표준 축은 이 문서 범위 밖이다.
- 방법: 정적 코드 리딩. 빌드·테스트는 돌리지 않았다.
- 작성: Claude Opus 5.5 (AI-assisted review, 사람 검토 전 초안)

## Verdict

**COMMENT.** 스펙이 요구한 항목은 모두 구현되어 있고, 누락이나 잘못된 구현으로 볼 만한 HIGH 신뢰도 항목은 없다. 아래 7개 항목은 MED 1개, LOW 6개다.

## Requirements coverage

라인 번호는 PR head `ef643ad15` 기준이다.

| 스펙 요구 | 구현 위치 | 판정 |
|---|---|---|
| `HEAP_SCANCACHE` 에 `insert_hint_vpid`, `insert_hint_l1_pos` 추가 | `heap_file.h:162-166` | OK |
| `heap_insert_logical` 이 성공한 페이지 VPID 기록 | `heap_file.c:23622-23631` | OK |
| `heap_scancache_reset_modify` 가 끝에서 힌트를 지움 | `heap_file.c:6700` | 부분 (F1) |
| bestspace 를 힌트 페이지 fix 전에 조회 전용(`class_oid` = NULL)으로 찾음, 없으면 힌트 건너뜀 | `heap_file.c:20735-20736` | OK |
| `LK_FORCE_ZERO_WAIT` 로 `pgbuf_ordered_fix` | `heap_file.c:20742-20746` | OK |
| 네 가지 확인 (`PAGE_HEAP`, `heap_page_is_not_in_heap`, class OID, `spage_max_space_for_new_record >= get_needed_size`) | `heap_file.c:20754-20764` | OK |
| 실패 세 갈래 (timeout 유지 / bad pageid·탈락 제거 / 그 외 전달) | `heap_file.c:20789-20831` | OK (F7 참고) |
| `bestspace::add_estimates` (+1 레코드, +길이) | `heap_file.c:20771`, `bestspace.cpp` | OK |
| `bestspace::update_freespace (vpid, freespace, &l1_pos)`: 후보 큐는 이미 있는 항목만, L1 은 VPID 검증 + CAS | `bestspace.cpp` `update_freespace`, `candidate_queue::update_if_exist`, `shard::update_freespace_at` | OK |
| 티어 경계를 넘을 때와 힌트 미스 때 한 번만 반영 | `heap_file.c:20776-20802` | OK |
| 첫 반영 때 전 shard 를 훑어 같은 VPID 를 모두 갱신하고 위치 캐시 | `bestspace.cpp` `update_freespace` | 부분 (F2) |

힌트가 낡는 경로도 확인했고 문제는 없었다.

- multi-insert·loaddb 가 새로 할당한 페이지: `heap_alloc_new_page` 가 NOT_IN_HEAP 을 표시하므로 `heap_page_is_not_in_heap` 에서 걸러진다.
- 다른 힙에 재사용하는 스캔 캐시: `heap_scancache_check_with_hfid` 에서 `reset_modify` 로 간다.
- 다른 클래스 소속이 된 페이지: class OID 확인에서 걸러진다.

## Findings

### (a) Missing or partial

**F1 [LOW] `reset_modify` 오류 반환 경로에서 힌트가 남는다**

> 스펙: "스캔 캐시를 다른 힙에 재사용하는 `heap_scancache_reset_modify` 는 끝에서 힌트를 지운다."

- `heap_scancache_reset_insert_hint` 는 함수 끝(`heap_file.c:6700`)에서만 부른다.
- 조기 반환 경로에서는 힌트가 그대로 남는다: `:6655` (`heap_scancache_force_modify` 실패), `:6666` (`heap_get_class_info` 실패), `:6689` (`file_get_type` 실패), `:6694` (`FILE_UNKNOWN_TYPE`).
- `:6666` 은 `heap_get_class_info` 가 `node.hfid` 에 직접 쓰고, `:6689`/`:6694` 는 `node.hfid` 를 이미 새 값으로 바꾼 뒤에 반환한다. 그래서 새 힙과 옛 힌트가 섞인 상태가 남을 수 있다.
- class OID 확인이 잘못된 페이지 사용을 막으므로 실제 위험은 낮다.
- 제안: `heap_scancache_force_modify` 가 성공한 직후에 힌트를 지운다.

**F2 [LOW] 캐시된 `l1_pos` 가 있으면 한 항목만 갱신한다**

> 스펙: "L1 에는 VPID 역인덱스가 없어 첫 반영 때 전 shard 를 훑어 같은 VPID 의 항목을 모두 갱신하고, 마지막으로 찾은 위치를 `insert_hint_l1_pos` 에 캐시한다."

- 첫 반영만 전 shard 를 훑는다.
- 이후에는 `l1_pos` 가 가리키는 한 항목만 갱신하고, 성공하면 바로 반환한다.
- 같은 VPID 가 L1 에 두 번 이상 있으면 두 번째 이후 항목은 첫 반영 뒤로 갱신되지 않는다.
- 게다가 `shard::update_freespace` 는 여러 개가 맞으면 마지막 항목을 `entry_index` 로 돌려준다.
- 중복이 구조상 불가능하다면 그 불변식을 주석으로 남기고, 가능하다면 항상 훑거나 스펙 문구를 고치는 것을 제안한다.

### (b) Behaviour not in the spec

**F3 [MED] 힌트 적중 경로가 bestspace 의 주기적 디스크 동기화를 건너뛴다**

- `heap_find_bestpage` 는 페이지를 찾기 전에 `bestspace->updatable ()` 이면 `heap_update_bestspace` 를 부른다 (`heap_file.c:4629-4636`).
- 힌트가 적중하면 `heap_find_bestpage` 를 부르지 않으므로 이 동기화도 다음 힌트 미스까지 미뤄진다.
- 페이지가 찰 때마다 미스가 최소 한 번 생기므로 실제 지연은 작을 것으로 보인다.
- 그러나 JIRA 와 PR 본문 모두 이 동작 변화를 언급하지 않는다. 의도한 것이면 PR 본문에 적고, 아니면 힌트 경로에도 같은 `updatable ()` 확인을 넣는 것을 제안한다.

**F4 [LOW] 힌트 적중은 bestspace 통계 카운터에 잡히지 않는다**

- 힌트가 적중하면 `bestspace::find` 가 올리던 `STATS_INC` (request/found 등) 가 증가하지 않는다.
- 그래서 `get_stats` 가 요청 수를 실제보다 적게 보고한다.
- 추정 통계(`add_estimates`)는 맞췄지만 이 진단용 카운터는 맞추지 않았다. 의도한 것인지 확인이 필요하다.

**F5 [LOW] L1 에 없는 힌트 페이지는 반영할 때마다 전 shard 를 훑는다**

- explicit home hint 로 들어간 페이지처럼 L1 에 항목이 없는 페이지가 힌트가 될 수 있다.
- 그러면 `update_freespace` 가 찾지 못해 `l1_pos` 가 계속 -1 로 남는다.
- 결과적으로 티어 경계를 넘을 때와 미스가 날 때마다 전 shard 전 항목을 훑는다.
- 결과는 맞고 비용만 든다. 경계 횟수가 페이지당 최대 9회 수준이라 크지 않을 가능성이 높다.
- 필요하면 "찾지 못함"도 캐시하는 것을 제안한다 (예: -2).

### (c) Implemented but questionable

**F6 [LOW] `bestspace::find` 와의 사전 조건 차이**

> PR 본문: "`bestspace::shard::L1_fix`/`L1_find` 가 후보 페이지에 적용하는 것과 같은 항목"

- `bestspace::find` 는 남아 있는 오류가 있으면(`er_errid_if_has_error`) 바로 반환하고, watcher 가 비어 있는지 assert 한다.
- 힌트 경로는 `pgbuf_ordered_fix` (`heap_file.c:20743`) 전에 둘 다 하지 않는다.
- 두 경로를 확실히 같게 하려면 `assert (PGBUF_IS_CLEAN_WATCHER (context->home_page_watcher_p))` 를 추가하는 것을 제안한다.

**F7 [LOW] 힌트 미스 분기의 `er_clear ()` 가 조건 없이 실행된다**

> PR 본문: "중단 요청과 입출력 오류는 그대로 전달한다."

- 미스 분기(`heap_file.c:20792`)는 `er_clear ()` 를 항상 부른다.
- 이것이 필요한 경우는 `heap_get_class_oid_from_page` 가 실패했을 때뿐이다.
- 네 확인을 모두 통과하고 공간만 모자란 경우에도 부르므로, 이 함수에 들어오기 전부터 남아 있던 무관한 오류까지 지울 수 있다.
- 제안: header 읽기가 실패한 경우에만 `er_clear ()` 를 부른다.

## Positive observations

- 네 가지 확인과 unfill 규칙이 탐색 경로와 같다. `get_needed_size` 를 `find` 와 공유하도록 추출했고, 페이지 fix 오류 처리도 `L1_fix`/`L1_find` 를 그대로 따른다. 그래서 힌트가 적중했다면 bestspace 탐색이 골랐어도 통과했을 페이지다.
- bestspace 조회를 힌트 페이지 fix 전에, 조회 전용으로 하도록 순서를 잡았다. 그래서 힌트 페이지 래치를 쥔 채 랭크가 높은 힙 헤더 페이지를 ordered fix 하는 역순 구간이 없다.
- 확인과 슬롯 확보가 같은 쓰기 래치 구간 안에서 끝나므로 확인과 사용 사이에 경쟁 구간(TOCTOU)이 없다.
