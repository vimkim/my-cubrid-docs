# PR #7617 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617)
**제목:** [CBRD-26786] Reclaim empty OOS pages in vacuum via file_dealloc
**작성자:** vimkim
**HEAD SHA:** `82d6e4bb5d4bc11189a6c2fb5d945b7d93e25542`
**리뷰 일시:** 2026-08-14

> **TL;DR** (Blocking): `oos_try_reclaim_empty_page` 는 "레코드 0건"만 확인하고 회수하는데, 그 페이지를 함께 비운 다른 vacuum worker 의 sysop (크래시 복구가 all-or-nothing 으로 다루는 작업 단위) 이 아직 열려 있을 수 있다. 그 sysop 이 abort/크래시하면 undo 가 이미 회수(deallocate)된 페이지에 재생돼 debug 는 assert 로 죽고, release 는 페이지가 그새 재할당된 경우 남의 살아 있는 페이지에 undo 를 재삽입해 오염시킨다. 이 판정 한 곳만 보강하면 머지 가능 -- insert 측 latch (페이지 단위 단기 잠금) 연속성, 데드락 부재, sysop/postpone (커밋 시점에 실행되도록 예약해 두는 로그 작업) 순서는 모두 코드로 검증했고 건전하다.

## Summary

- **변경 요약**: vacuum 이 비운 OOS 페이지를 `file_dealloc` 로 partial sector table (파일 헤더에 영구 저장되는 페이지 할당 비트맵) 에 반환. 전제로 `FILE_OOS` non-numerable 전환(sector-bitmap 열거) + insert 경로 latch 연속성 확보.
- **주요 이슈**: 회수 판정이 "빈 페이지"와 "아무 undo 도 참조하지 않는 페이지"를 동일시함 (B1).
- **검증**: 로컬 debug 빌드 성공, OOS 단위 테스트 25/25 통과 재확인. 단 이 테스트들은 `UNIT_TESTS=OFF` 기본값 탓에 CI 게이트가 아니다.
- **확인 필요 사항**: base 인 feat/oos 가 머지베이스 이후 약 50 커밋 전진(OOS 관련 CBRD-26847 포함). GitHub 상태는 MERGEABLE 이지만 최신 feat/oos 위에서 재빌드/재테스트 권장.

---

## Findings

### Blocking (must fix)

- `src/storage/oos_file.cpp:1298-1299` -- 회수 게이트가 "`PAGE_OOS` 타입 + 레코드 0건" 확인뿐이라, 자기 배치의 삭제가 커밋됐다는 것은 보장해도 그 페이지를 비운 **모든** 삭제가 커밋됐다는 것은 보장하지 못한다. `oos_delete_chain` 은 청크마다 페이지를 fix/unfix 하므로(`oos_file.cpp:2390-2401`, 루프 내 `scope_exit`) 삭제자는 자기 sysop 커밋 전까지 latch 를 쥐고 있지 않다 -- 회수기의 conditional fix (대기 없이 즉시 실패로 빠지는 latch 시도) 로는 감지할 수 없다. 시나리오: vacuum worker V1 이 페이지 P 의 청크 B 를 지우고 sysop 이 열린 사이, V2 가 P 의 마지막 청크 A 를 지우고 커밋한 뒤 P 를 회수. 이후 V1 이 에러/인터럽트로 `log_sysop_abort` (`vacuum_oos.cpp:207`) 하거나 서버가 크래시하면, B 의 `RVOOS_DELETE` undo 가 회수된 P 를 plain `OLD_PAGE` 로 fix 하려다 실패한다 (런타임 rollback 은 `log_manager.c:7436`, 크래시 복구는 `log_recovery.c:213`). 결과 -- debug: pgbuf assert 로 vacuum/복구 중단. release: (1) undo 스킵으로 B 뒤의 체인 청크들이 head 에서 도달 불가가 돼 공간 누수, (2) 더 나쁘게는 abort 전에 P 가 `file_alloc` 으로 재할당돼 새 청크로 채워진 경우 `OLD_PAGE` fix 가 성공해 undo 가 낡은 slotid 로 `spage_insert_for_recovery` (`oos_file.cpp:2626` undo 함수 경유) 재삽입 -- 살아 있는 페이지 오염. 이 PR 전에는 OOS 페이지 dealloc 자체가 없어 새로 도입된 결함이며, CBRD-26950(슬롯 재사용 identity)이나 CBRD-27237(forward-walk 커밋 필터 부재)과는 별개다 -- CBRD-26950 의 generation stamp 는 청크 헤더 단위라 페이지 재할당 후 undo 재생 오염은 막지 못한다. 수정 방향: 레코드 0건에 더해 페이지에 미해결 변경이 없음을 보장하는 게이트 -- 예: 페이지 LSA (페이지에 마지막으로 적용된 로그 레코드 위치) 가 가장 오래된 활성 트랜잭션/sysop 시작보다 과거인지 확인, 또는 회수 후보를 "그 페이지의 모든 삭제가 내 배치 소속"인 경우로 제한.

### Non-blocking (should consider)

- `src/storage/oos_file.cpp:1310` 부근 -- `file_dealloc` 호출 시점에 대상 페이지 P 를 여전히 fix 한 채라, debug 빌드에서 {데이터 페이지 -> 파일 헤더} latch 순서가 생긴다 (`file_manager.c:6179` 의 fhead fix; release 는 `FILE_TYPE_CAN_BE_NUMERABLE` 게이트로 이 fix 를 건너뜀). `file_alloc` 의 {파일 헤더 -> 새 페이지}와 역순이며, 지금은 P 의 비트맵 비트가 set 이라 할당 대상이 될 수 없어 사이클이 없지만, `pgbuf_unfix_and_init (page_ptr)` 를 `file_dealloc` 앞으로 올리면 역전 자체가 사라진다. 비었음 판정은 이미 끝났고 헤더 latch 가 새 writer 를 막으므로 안전성 손실 없음.
- `src/query/vacuum_oos.cpp:250-256` -- `oos_try_reclaim_empty_page` 가 의도적으로 전파한 `ER_INTERRUPTED` (`oos_file.cpp:1290-1293`) 를 루프가 경고 로그 + `er_clear` 로 삼키고 다음 페이지로 진행한다. 셧다운/인터럽트 응답이 늦어지므로 `ER_INTERRUPTED` 는 루프를 끊고 반환할 것.
- `src/storage/oos_file.cpp:950-953` -- ADR-0001 Consequence 3 이 요구한 "스킵된 deallocated 페이지" 관측 카운터가 `oos_trace` 라 release(NDEBUG) 빌드에서 no-op 이다 (`oos_log.hpp:172-179`). tripwire 를 잃는 쪽이 바로 release 이므로 always-on 레벨(`oos_warn`)이나 perfmon 스탯으로 승격 권장. `oos_get_stats_by_vfid` 쪽 스킵은 카운트조차 없다.
- `src/storage/oos_file.cpp:2288` -- Phase C 의 stale 힌트 자가 퇴출은 헤더 페이지 버퍼의 best[] (헤더에 상주하는 빈 공간 힌트 배열) 를 수정하는데, "새 페이지 할당" 출구는 형제 경로와 달리 `log_skip_logging` + `pgbuf_set_dirty` 없이 unfix 한다. 퇴출이 유실될 수 있다 (스테일 힌트 재등장 -- lookup 관용이 흡수하므로 무해하지만 비일관).
- `src/storage/oos_file.cpp:1219-1222` -- 안전성 주석의 "alloc fallback 도 header latch 아래에서 시작"은 사실과 다르다: `oos_find_best_page` 는 `oos_file_alloc_new` 호출 전에 헤더를 unfix 하고(`:2288`), 초기 실패 폴백들(`:2166`, `:2173`, `:2180`)은 헤더 latch 없이 호출한다. 실제 안전성은 파일 헤더 latch 와 비트맵이 담보하므로 주석만 고치면 된다. 같은 맥락으로 `oos_collect_data_page_vpids` 주석(`:715-716`)의 "file-table 페이지는 이미 빼고 준다"는 legacy numerable 파일의 user page table 페이지에는 성립하지 않는다 -- `PAGE_OOS` 타입 검사가 "paranoia"가 아니라 필수 필터임을 명시할 것.
- `src/query/vacuum_oos.cpp:235` -- 주석 "(JIRA Q3 -- vector + sort/unique ...)"는 티켓 번호도 없는 외부 참조라 자립적이지 않다. 이유를 직접 쓰거나 괄호를 삭제.
- `unit_tests/oos/test_oos_remove_file.cpp:221` -- `OosPageReclaimStickyFirstPage` 는 만든 OOS 파일을 제거/커밋하지 않고 끝난다. 형제 테스트 주석(`:203-205`)이 경고한 committed-orphan 위험과 같은 패턴이므로 `oos_remove_file` + 커밋으로 마무리 권장.

### Questions for the author

- eager 삭제 경로(`heap_oos_delete_unreferenced`, non-MVCC 클래스에서 살아 있는 사용자 트랜잭션 안에서 실행)가 비운 페이지를 vacuum 이 회수하는 교차 시나리오가 성립하는가? vacuum 회수는 MVCC 연산에서만 촉발되므로 한 클래스의 OOS 파일이 두 연산을 모두 봐야 하는데, 그런 혼합 경로가 있으면 B1 이 사용자 트랜잭션 rollback 으로도 재현된다.
- `FILE_OOS` non-numerable 전환(`oos_file.cpp:1086`)은 on-disk 동작 변경인데 이 PR 에 포함하는 것이 확정인가? legacy numerable 파일은 회수에서 영구 제외되고 사유는 debug 전용 `oos_trace` 로만 남는다. JIRA Remark 대로 CBRD-26831 과의 스코프 정리를 머지 전에 매듭지을 것인지.
- Phase C(insert 로 이어지는 write 경로)의 `OLD_PAGE_MAYBE_DEALLOCATED` 전환은 ADR-0001 Consequence 2("write 경로는 plain `OLD_PAGE` 유지")와 어긋난다. 정당한 설계 변경으로 보이나 accepted 상태의 ADR 을 개정해 남길 것인지.

## JIRA Context

CBRD-26786 의 목적(빈 OOS 페이지를 partial sector table 로 반환)과 세 가지 결정(non-numerable 전환, latch 연속성, 커밋 후 회수)은 본 PR 과 정확히 일치한다. 체크된 A/C 는 전수 코드 확인 결과 모두 실재한다 (sticky first page (파일의 첫 사용자 페이지, OOS 통계 헤더 상주) 가드, legacy skip, 멱등성, 사용 중 슬롯 게이트, 두 vacuum 경로, 힌트 퇴출, 열거 전환). 미체크 A/C(CTP 회귀 4종, 기존 CI)는 남아 있으며, B1 은 그중 crash-injection A/C 가 잡도록 설계된 바로 그 영역이다.
