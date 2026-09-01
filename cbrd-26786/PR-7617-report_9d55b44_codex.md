# PR #7617 전체 범위 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617)

**제목:** [CBRD-26786] Reclaim empty OOS pages in vacuum via file_dealloc

**리뷰 범위:** `origin/feat/oos...9d55b4484` (merge-base `140fc5ef6`, 16 commits)

**HEAD SHA:** `9d55b4484ffb650fd111b6d39efc25a52c19ebc0`

**리뷰 일시:** 2026-09-01

> **TL;DR:** CBRD-26786 동작 스펙은 충족하고 이전의 도달 가능한 blocker 2건도 해결됐습니다. legacy numerable OOS 파일은 지원 범위 밖이며, Standards/Spec 양쪽에 blocking finding이 없어 현재 판정은 `APPROVE` 입니다.

## Summary

- **Spec:** 0 findings. vacuum fast path, 2단계 판정, LSA 게이트, per-VFID reclaim debt/cursor, boot rule, 단일 성장 지점, SA/non-MVCC eager 경로가 빈 페이지 회수 불변식과 일치합니다.
- **Standards:** blocking 0건. `oos_touched_pages.empty ()` 는 의미상 C++ method 호출이지만 문법 자체는 C에서도 유효하므로 GNU indent 보호 규칙 위반이 아닙니다.
- **기존 blocker 정리:** foreign OOS page stale hint와 transient WRITE-latch miss는 `9d55b4484` 에서 각각 소유권 검사와 reclaim debt 보존으로 해결됐습니다.
- **legacy numerable:** 미출시 중간 `feat/oos` 바이너리가 만든 DB를 계속 사용하는 경우에만 도달합니다. 현재 OOS 생성 경로는 항상 non-numerable이며 출시/지원 DB 포맷에는 OOS 자체가 없으므로 이 PR의 지원 범위 밖입니다.
- **검증:** `debug_gcc` 빌드 성공, 구성된 OOS 테스트 27/27 통과 (0 failures, 106.98초). `git diff --check origin/feat/oos...9d55b4484` 도 통과했습니다.

---

## Standards

### Blocking

**0 findings.**

초기 리뷰에서 `src/query/vacuum.c:1945` 의 `!oos_touched_pages.empty ()` 를 C++ 전용 syntax로 분류했으나 철회합니다. `xxx.yyy()` 는 C에서도 `yyy` 가 struct의 function-pointer member일 때 유효한 문법입니다. 여기서는 `VACUUM_OOS_TOUCHED_PAGES` 가 `std::vector<VPID>` 이므로 의미상 C++ method 호출이지만, GNU indent 관점의 문법은 C에서 해석 가능한 member access + call입니다. 따라서 “C++-specific syntax는 `INDENT-OFF/ON` 으로 보호” 규칙의 위반 근거가 되지 않습니다.

### Non-blocking

- `unit_tests/oos/test_oos_remove_file.cpp` / `test_oos_remove_file_server.cpp` — `OosPageReclaimBasic` 및 `OosPageReclaimLsaGateDefersUncommitted` 시나리오가 SA/server harness 사이에서 거의 중복됩니다. 두 fixture의 초기화 차이를 유지해야 하므로 즉시 blocker는 아니지만, 공통 helper로 추출하면 향후 동작 드리프트를 줄일 수 있습니다. **Possible Duplicated Code** 판단입니다.

### Suppressed

- `oos_file.cpp` 의 신규 `try`/`catch (std::bad_alloc &)` 경로는 예외 기반 엔진 제어 흐름으로 보지 않았습니다. STL allocation failure를 `er_set` + CUBRID 오류 코드로 변환하거나 선택적 hint만 버리고, 예외가 엔진 경계 밖으로 전파되지 않습니다. 이는 기존 OOS/engine의 exception-to-C-boundary 패턴과 일치합니다.

---

## Spec

**0 findings.**

CBRD-26786의 핵심 계약은 다음 두 문장입니다.

1. 완전히 빈 OOS 데이터 페이지는 결국 file manager로 반환된다.
2. OOS 파일은 지금 안전하게 회수 가능한 빈 페이지가 없을 때만 새 sector를 예약한다.

전체 PR 범위에서 이 계약을 구성하는 경로를 확인했습니다.

- vacuum은 heap-page batch 동안 touched VPID를 모으고 home page를 unfix한 뒤 `oos_reclaim_empty_pages` 를 호출합니다.
- per-page primitive는 조건부 READ 선판정 후 OOS header 직렬화 아래 조건부 WRITE 재검증을 수행합니다.
- horizon은 활성 regular transaction과 active system tdes 양쪽의 최소 head LSA를 반영합니다.
- 삭제 경로는 per-VFID pending debt를 재무장하고, SA/non-MVCC eager 경로에서 놓친 빈 페이지도 성장 게이트 sweep이 bitmap에서 재발견합니다.
- OOS의 실제 새-page 할당은 `oos_alloc_page_with_reclaim` 단일 지점을 통과합니다.
- sweep cursor, completed-lap 정산, boot rule이 hint 유실과 restart를 흡수합니다.

### 이전 blocker 재검증

1. **Foreign `PAGE_OOS` stale hint — RESOLVED**

   `9d55b4484` 는 page type 확인 뒤 `file_is_vpid_in_file` 로 요청 VFID의 실제 소유권을 검증합니다. 다른 OOS 파일의 데이터 페이지이면 hint를 퇴출하며, `BestspaceStaleHintToForeignOosPageIsRejected` 회귀 테스트가 이 경로를 판별합니다.

2. **Transient phase-2 WRITE miss가 reclaim debt를 소거 — RESOLVED**

   READ phase를 통과한 뒤 WRITE fix가 일시적으로 실패하면 결과를 `OOS_RECLAIM_DEFERRED` 로 분류합니다. full-lap 정산은 deferred 수만큼 debt를 다시 더하므로 다음 growth가 재시도합니다. `TransientWriteLatchMissKeepsReclaimDebt` 테스트가 첫 growth의 일시적 확장과 다음 growth의 회수 재시도를 모두 검증합니다.

3. **Legacy numerable OOS file — OUT OF SCOPE**

   현재 tree에는 OOS 파일 생성자가 하나뿐이고 항상 `is_numerable=false` 로 생성합니다. numerable OOS 파일은 출시되지 않은 중간 experimental/`feat/oos` 바이너리로 만든 DB를 현재 바이너리에 가져오는 경우에만 존재합니다. OOS가 아직 `develop`/출시 포맷에 없으므로 지원되는 upgrade 경로가 아니며, 현재 PR의 reachable correctness blocker로 분류하지 않습니다.

---

## Decision

- **Review points:** 0 blocking, 1 non-blocking
- **Standards:** PASS — 0 blocking findings
- **Spec:** PASS — 0 findings
- **Decision:** **APPROVE**

기존 도달 가능한 blocker 2건은 해결됐고 legacy numerable finding은 지원 범위 밖입니다. 이 판정에 따라 current PR head에 full CI (`/run all`)를 요청합니다.
