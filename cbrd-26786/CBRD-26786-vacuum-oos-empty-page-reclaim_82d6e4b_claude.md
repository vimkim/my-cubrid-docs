# CBRD-26786 — vacuum 의 OOS 빈 페이지 회수

https://jira.cubrid.org/browse/CBRD-26786

## Purpose

vacuum 은 죽은 레코드 버전이 갖고 있던 OOS(Out-of-row Overflow Storage — heap 레코드의 큰 가변 컬럼을 전용 파일로 분리 저장하는 방식) 값을 슬롯 단위로 지우지만, 슬롯이 모두 지워져 완전히 빈 페이지를 파일에 되돌리는 단계가 없었다.

- AS-IS: 빈 페이지 정보를 아는 곳은 bestspace cache(빈 공간 힌트 캐시)뿐인데, 이 캐시는 상한이 `OOS_BESTSPACE_CACHE_CAPACITY`(1000, 모든 OOS 파일 합산)이고 가득 차면 새 항목을 받지 않으며 서버 재시작 시 사라진다. 캐시에서 빠진 빈 페이지는 insert 가 찾지 못해, 재사용 가능한 페이지를 두고 파일이 확장된다.
- TO-BE: vacuum 이 OOS 삭제 배치를 커밋한 직후 빈 페이지를 `file_dealloc` 로 file manager 의 partial sector table(파일 헤더에 디스크로 영구 저장되는 페이지 할당 비트맵)에 반환한다. 이 표는 상한이 없고 재시작에도 남으므로, 다음 `file_alloc` 이 캐시 상태와 무관하게 그 페이지를 재사용한다.

줄어드는 것은 OOS 파일의 확장 빈도다. sector 는 파일 소유로 남으므로 디스크 사용 총량이 줄지는 않는다.

## Implementation

구현은 세 부분이고, 앞의 두 부분은 세 번째(회수)가 안전해지기 위한 전제다.

### 1. FILE_OOS non-numerable 전환 + sector-bitmap 열거 (CBRD-26831 결정 포함)

`file_dealloc` 의 user page table 정리 분기는 `FILE_TYPE_CAN_BE_NUMERABLE` 매크로(src/storage/file_manager.c)로 게이트되는데 `FILE_OOS` 가 목록에 없다. 그래서 numerable(페이지 할당 순서를 user page table 로 기록해 n번째 페이지 조회를 지원하는 파일 속성) 상태로 페이지를 회수하면, sector 비트맵에서는 지워지고 user page table 에는 남아 `file_numerable_find_nth` 가 회수된 페이지를 돌려주게 된다. 회수 도입 전에 전환이 필요한 이유다.

- `oos_create_file_internal` (src/storage/oos_file.cpp): `is_numerable=false` 로 생성.
- `oos_collect_data_page_vpids` 신설: `file_get_all_data_sectors` 의 sector 비트맵 스냅샷을 풀어 데이터 페이지 VPID(볼륨 + 페이지 식별자) 목록을 만든다.
- `oos_stats_sync_bestspace`, `oos_get_stats_by_vfid`: `file_numerable_find_nth` 루프를 위 목록 순회로 교체. 스냅샷은 걷는 동안 낡을 수 있으므로 `OLD_PAGE_MAYBE_DEALLOCATED` fix + `PAGE_OOS` 타입 검사로 샘플링하고, 건너뛴 페이지 수를 oos.log 에 남긴다.
- `file_is_numerable` 신설 (src/storage/file_manager.c): 구버전 빌드가 만든 numerable OOS 파일을 회수에서 제외하는 가드에 사용.

### 2. insert 경로 latch 연속성

회수기의 "비었음" 판정이 쓰기 직전 페이지와 경합하지 않으려면, 쓰기로 향하는 페이지는 검증/할당 시점부터 쓰기 완료까지 WRITE latch(페이지 단위 단기 잠금)가 끊기지 않아야 한다. 기존에는 두 곳에 unfix 후 re-fix 하는 공백이 있었다.

- `oos_find_best_page`: 후보 검증(Phase C)에서 얻은 latch 를 `auto_unfix_page_ptr` 로 그대로 인계 (기존 unfix/re-fix + 재검사 폴백 제거).
- `oos_file_alloc_new`: `file_alloc` 의 `page_out` 인자로 할당 시점 latch 를 받아 인계.
- `oos_stats_find_page_in_bestspace` Phase C: 후보 fix 를 `OLD_PAGE_MAYBE_DEALLOCATED` 로 전환. 회수된 페이지를 가리키는 낡은 힌트는 이제 정상 race 이므로, `ER_PB_BAD_PAGEID` 감지 시 해시/best[] 에서 자가 퇴출하고 다음 후보로 넘어간다.

### 3. 회수 함수와 vacuum 연결

`oos_try_reclaim_empty_page` (src/storage/oos_file.cpp) — 멱등, zero-wait, best-effort. "지금 회수 못 함"(사용 중, 이미 회수됨, 재점유됨, sticky first page(파일의 첫 사용자 페이지로 OOS 통계 헤더가 살아 절대 회수하면 안 된다), legacy numerable 파일)은 모두 NO_ERROR 로 건너뛰고 다음 vacuum 사이클에 맡긴다.

```
oos_try_reclaim_empty_page
 ├ sticky first page / legacy numerable 파일이면 skip
 ├ OOS stats header page WRITE latch    ★ 이후 전 구간 유지 — insert 측의 모든
 │                                        페이지 발견 경로가 이 fix 에서 시작한다
 ├ 대상 페이지 conditional fix (OLD_PAGE_MAYBE_DEALLOCATED, WRITE)
 │   busy / 이미 회수됨 -> skip
 ├ PAGE_OOS && 레코드 0건 확인
 ├ sysop start; file_dealloc (FILE_OOS)  -- RVFL_DEALLOC postpone 등록
 ├ 대상 페이지 unfix                      -- postpone 의 pgbuf_dealloc_page 가 단독 fixer 요구
 ├ sysop commit                         ★ postpone 이 여기서 실행돼 페이지가 실제 반환됨
 └ (header latch 유지한 채) bestspace 해시 엔트리 퇴출 + best[] 힌트 무효화
```

호출 연결:

- `oos_delete` 에 선택 인자 `touched_vpids` 추가 — 체인이 여러 페이지에 걸쳐도 청크가 지워진 페이지를 모두 수집.
- `vacuum_oos_reclaim_empty_pages` 신설 (src/query/vacuum_oos.cpp): 정렬 + 중복 제거 후 helper 반복 호출, 실패는 경고만 남기고 진행.
- forward-walk 경로: `vacuum_forward_walk_oos_delete_atomic` 이 자기 sysop(system operation — 크래시 복구가 all-or-nothing 으로 다루는 작업 단위) 커밋 직후 호출.
- REMOVE 경로: `vacuum_heap_oos_delete_within_sysop` 이 수집하고, src/query/vacuum.c 의 REC_RELOCATION / REC_HOME 분기가 sysop 커밋 직후 호출.
- 회수가 삭제 커밋 이후여야 하는 이유: `oos_delete` 의 청크별 undo(`RVOOS_DELETE`)는 abort 시 청크를 원래 슬롯에 되살리는데, 페이지가 이미 회수됐으면 되살릴 곳이 없다. 같은 이유로 살아 있는 사용자 트랜잭션 안에서 도는 SA_MODE eager 삭제 경로(`heap_oos_delete_unreferenced`)는 회수 대상에서 의도적으로 제외했다 (src/storage/heap_oos.cpp 주석 참고).

### 부수 정리

- caller 0건 dead 함수 `oos_remove_page` 와 선언, TODO 주석 삭제.
- `oos_get_length` (단위 테스트용 프로브): 회수된 페이지를 assert 없이 "레코드 없음"으로 보고하도록 `pgbuf_fix_if_not_deallocated` 로 전환.
- 단위 테스트 (unit_tests/oos/test_oos_remove_file.cpp, test_oos_remove_file_server.cpp): 비어 있지 않은 페이지 skip / 삭제 커밋 후 회수 / 멱등성 / sticky first page 가드 시나리오.

## Remarks

- 리뷰 포인트 1 — 회수 안전성 논증: `oos_try_reclaim_empty_page` 의 header latch 직렬화가 실제로 모든 insert 측 발견 경로를 막는지. 근거는 `oos_find_best_page` 가 해시/best[]/sync 재시도/alloc 폴백을 전부 header page fix 아래에서 시작한다는 것과, 위 2번의 latch 연속성이다.
- 리뷰 포인트 2 — postpone(커밋 시점에 실행되도록 예약해 두는 로그 작업) 실행 시점: `file_dealloc` 의 `RVFL_DEALLOC` postpone 은 helper 자신의 sysop 커밋에서 실행된다 (`log_append_postpone` 이 sysop 스택에 기록). vacuum worker 는 sysop 커밋이 최종 확정이므로 회수 시점 계약(삭제 커밋 이후)을 만족한다.
- 제한: SA_MODE eager 경로는 회수하지 않는다. eager 가 비운 페이지는 할당된 채 남지만 bestspace 에 계속 보이므로 이후 insert 가 재사용한다.
- 호환성: feat/oos 는 미출시 브랜치라 업그레이드 부담 없음. 구버전 빌드가 만든 numerable OOS 파일은 `file_is_numerable` 가드로 회수만 건너뛰고 나머지 동작은 동일하다. WAL 포맷 변경 없음 (기존 `RVFL_DEALLOC` 재사용).
- 검증: debug 빌드에서 OOS 단위 테스트 25/25 통과 (ctest, `unit_tests/oos`). CTP 회귀 시나리오(insert/delete 사이클 페이지 수 안정, UPDATE-heavy 상한, 동시 워크로드)는 JIRA A/C 로 남아 있다.
- 후속: CBRD-26831 (non-numerable 전환 추적 이슈)과의 범위 정리, disk manager 의 sector 단위 반환이 생기면 "확장 빈도 감소"를 "디스크 사용량 감소"로 확장하는 후속 이슈.
