# PR #7695 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7695](https://github.com/CUBRID/cubrid/pull/7695)
**제목:** [CBRD-26950] Verify OOS chain identity before vacuum delete
**작성자:** vimkim
**HEAD SHA:** `01d110e8a3ac7659d6421f9c1b54e60520e21df9`
**리뷰 일시:** 2026-08-14

> **TL;DR** (Blocking): 4B generation (슬롯의 몇 번째 주인인지 나타내는 세대 번호) 신원 스탬프가 세 삭제 경로, 복구, HA 복제까지 JIRA 확정안대로 구현되었고, 정상 경로에서 로직 결함은 발견하지 못했다. 다만 이 PR 의 핵심 신규 동작인 "generation 불일치 -> 삭제 no-op" 분기를 검증하는 단위 테스트가 하나도 없어 이 한 가지는 머지 전 보강이 필요하며, 오류·손상 경로 결함 2건은 Non-blocking 으로 분류했다.

## Summary

- **변경 요약**: OOS (큰 가변 컬럼 값을 행 밖 별도 페이지에 저장하는 방식) 청크에 generation 을 스탬프하고, vacuum 삭제 전 기대값과 대조해 재사용된 슬롯의 살아있는 데이터를 건드리지 않게 한다.
- **포맷 영향**: 온디스크 포맷 3곳(OOS 데이터 페이지 slot 0 헤더 신설, 청크 헤더 +4B, heap 레코드 안의 stub (OOS 체인을 가리키는 20B 인라인 참조: head OID + 길이 + generation) +4B)이 바뀌고 복구 로그 타입이 신설되므로 기존 feat/oos DB·로그는 그대로 못 읽는다. 리뷰/QA 는 DB 재생성 후 검증할 것 (미출시 브랜치라 마이그레이션 대상은 없음).
- **주요 이슈**: 불일치 no-op 분기 테스트 부재 (Blocking 1건), Non-blocking 9건(오류 경로 결함 2, 동시성 불변식 1, 주석/API 정리 6).
- **확인 필요 사항**: generation wrap-around 분석 범위 (아래 Questions).

---

## Findings

### Blocking (must fix)

- `unit_tests/oos/` 전체 — 이 PR 의 존재 이유인 "기대 generation 불일치 -> no-op, 재사용 체인 보존" 분기를 타는 테스트가 0건. 모든 삭제 테스트가 헬퍼 `oos_delete_current_generation` (`test_oos_common.hpp:110`, `test_oos_server_common.hpp:231`) 를 경유하는데, 이 헬퍼는 저장된 generation 을 읽어와 그대로 전달하므로 항상 일치한다. JIRA 재현 스크립트는 CI 밖이라 회귀 방지가 안 된다 -> 이 분기가 조용히 깨져도 (= 원래의 silent 데이터 손실로 되돌아가도) 아무 테스트도 실패하지 않는다. 최소 2건 추가 필요: (1) 삽입 후 `oos_delete(oid, gen+1)` 이 `NO_ERROR` 를 반환하고 청크가 그대로 읽히는지, (2) 슬롯 재사용 시나리오(삭제 -> 같은 슬롯 재삽입 -> 옛 generation 으로 재삭제)에서 새 체인이 살아남는지. 복제 fixup 테스트(`test_oos_server.cpp:650-656`)도 OID 만 검증하고 stub 의 generation 재기록은 확인하지 않으므로 assert 한 줄 추가를 권함.

### Non-blocking (should consider)

- `src/transaction/locator_sr.c:14253-14254` — 복제 fixup 이 stub 에 generation 을 덮어쓰기 전 길이 검증이 없다. `or_advance`/`or_put_int` 는 assert 로만 경계를 확인하고 무조건 쓰므로 (`object_representation.h:1508, 1714`), 손상된 복제 레코드에서 release 빌드는 레코드 끝 너머 4B 를 쓴다. 같은 커밋의 읽기 쪽 `heap_recdes_get_oos_refs` (`heap_file.c:28150`) 는 `OR_OOS_INLINE_SIZE` 로 경계 검사를 강화해 두어 쓰기 쪽만 비는 비대칭이 생겼다. stub 시작 오프셋에 `OR_OOS_INLINE_SIZE` 를 더한 위치가 레코드 끝을 넘지 않는지 명시 검사를 추가할 것.
- `src/storage/oos_file.cpp:1575` — `oos_insert_record_in_fixed_page` 에서 `spage_insert` 성공 후 페이지 헤더 재조회가 실패하면 청크가 페이지에 남은 채 로그 없이 에러 반환한다 (메모리상 변경이 RVOOS_INSERT (청크 삽입의 물리 복구 로그 레코드) 에 실리지 않음). 페이지 손상 전제의 assert 방어 경로이긴 하나, 반환 전 `spage_delete` 로 방금 넣은 슬롯을 되돌리면 상태 일관성이 지켜진다.
- `src/storage/oos_file.cpp:2365, 2272` — `oos_chain_head_matches` 가 읽기 래치 (페이지 동시 접근을 막는 잠금의 공유 모드) 로 generation 을 대조하고 unfix 한 뒤 `oos_delete_chain` 이 쓰기 래치로 다시 fix 한다. 대조 시점과 삭제 시점 사이에 다른 삭제 주체가 끼어들면 검증이 무효가 되는 구조인데, 현재는 "체인 1개당 삭제 주체 1개" 불변식(한 undo image (행이 바뀌기 전 모습을 로그에 남긴 불변 스냅샷) 는 한 vacuum worker 가 처리, SA_MODE (클라이언트와 서버가 한 프로세스로 도는 단독 실행 모드) 는 단일 프로세스) 덕에 안전하다. CBRD-27230 (UPDATE 체인 재사용 + notify 로그) 이 삭제 주체를 늘리기 전에, 대조를 `oos_delete_chain` 의 첫 쓰기 래치 아래로 옮기거나 불변식을 `oos_delete` 주석에 명문화할 것.
- `src/storage/oos_util.cpp:48` — `oos_ref_in_vector` 주석의 "vector is small by design" 은 근거 미기재. 이 vector 는 heap 레코드 1건의 stub 목록이고, stub 을 가진 heap 레코드는 REC_BIGONE (한 페이지를 넘는 레코드의 overflow 저장 형식) 이 금지되어 약 16KB 를 넘지 못하므로(CBRD-26937) stub 1개당 22B (stub 20B + 2B 오프셋 테이블 엔트리) 기준 상한 약 740개다. 유일한 호출처 `heap_oos_delete_unreferenced` (`src/storage/heap_oos.cpp:758`) 의 old x new 이중 루프도 최악 약 55만 회 OID 비교(SA_MODE UPDATE 1회당)로 유한하다. 주석에 "한 레코드의 stub 개수만큼이며 레코드 크기 상한으로 유계" 라고 근거를 명시할 것.
- `src/storage/oos_file.cpp:2178` + `RVOOS_NEWPAGE` (OOS 데이터 페이지 초기화 복구 로그 레코드, 본 PR 신설) — 페이지 초기화가 counter 를 0 으로 리셋한다. 지금은 `oos_remove_page` 의 프로덕션 호출자가 없어 안전하지만, CBRD-26786 (빈 OOS 페이지 회수) 이 dealloc/realloc 을 도입하면 재할당된 페이지가 generation 을 처음부터 다시 발급해 이 버그가 페이지 단위로 재발한다. 해당 제약("페이지 재활용 시 counter 를 보존하거나 stale stub 이 남지 않음을 보장")을 JIRA 후속 계약과 이 지점 주석에 기록할 것.
- `src/storage/oos_file.hpp:132-133, 147` — API 표면 2건: `oos_get_generation` 은 주석부터 "For tests and diagnostics" 인데 같은 헤더의 테스트 전용 API 와 달리 `CUBRID_UNIT_TEST_ENABLED` 가드 없이 공개되어 있고, `oos_insert` 의 `generation_out` 은 기본값 NULL 이라 stub 을 쓰는 새 호출자가 이를 빠뜨리면 generation 0 stub (0 은 미발급 값) 이 되어 해당 체인이 영원히 회수되지 않는다(누수). 가드 추가와 필수 인자화를 각각 검토할 것.
- `src/storage/oos_util.cpp:35` + `oos_util.hpp:34` — `oos_oid_in_vector` 는 유일한 호출자가 `oos_ref_in_vector` 로 교체되어 죽은 코드가 되었다. 선언과 함께 제거할 것.
- `src/thread/thread_entry.hpp:322-331` — `oos_published_ref` 는 `oos_chain_ref` (`oos_file.hpp:56-60`) 와 레이아웃이 동일한 중복 정의이고, 멤버 이름 `oos_oids` 는 이제 (OID, generation) 쌍을 담는데도 이름이 OID 목록을 시사한다. 헤더 의존성 때문에 의도적으로 중복시킨 것이라면 주석 한 줄, 아니라면 타입 재사용과 개명을 권함.
- `unit_tests/oos/sql/test_oos_sql_boundary.cpp:302` — "OR_OOS_INLINE_SIZE = 16 B" 주석이 이 PR 로 낡았다 (단언 자체는 유효).

### Questions for the author

- generation 은 unsigned int 라 페이지당 2^32 회 발급 후 wrap 되어 0 (미발급 표지) 을 거쳐 그 페이지의 초기 stub 들과 충돌할 수 있다. 발급부 `oos_file.cpp:1545` 는 `generation_counter + 1` 에 wrap 가드나 0 스킵이 없고 페이지 초기값이 0 이다 (`oos_file.cpp:2178`). JIRA 의 4B 채택 근거는 비용(R4)과 불변식 국소화(R5)이며 wrap 분석은 포함되어 있지 않은데, 페이지 수명 전체 기준으로도 수용 가능한지 확인 부탁드립니다.

## JIRA Context

CBRD-26950 (상태: Analysis) 확정안 -- 페이지 slot 0 카운터에서 generation 발급, 청크 헤더(16->20B)와 stub(16->20B) 양쪽 기록, `oos_delete` 대조 후 불일치/부재 no-op, slave 로컬 발급 -- 과 구현이 일치한다. 세 삭제 경로(forward-walk (vacuum 이 undo 로그의 옛 버전 이미지를 훑어 OOS 체인을 회수하는 경로) `vacuum_oos.cpp:180`, REMOVE `vacuum_oos.cpp:408`, eager `heap_oos.cpp:763`), 복구 단조 증가 재생(`oos_file.cpp:2658`), 복제 fixup(`locator_sr.c:14243`) 모두 계약을 따른다. 계획 밖 요소 1건: JIRA 는 "복구 핸들러 변경 없음"이라 했으나 slot 0 헤더 레코드 초기화를 복구에서 재생하기 위해 `RVOOS_NEWPAGE` 가 신설되었다 -- 설계상 불가피한 파생으로 판단되며, JIRA 구현 노트에 반영해 두면 된다. WAL 순서(카운터 바이트는 청크의 RVOOS_INSERT 가 유일한 내구성 운반자, 쓰기 래치가 발급+삽입+로그를 원자화)와 롤백/크래시 인터리빙을 추적했으나 counter 역행 시나리오는 구성되지 않았다.
