# PR #7695 Review Follow-up Progress Report

> **PR:** [[CBRD-26950] Verify OOS chain identity before vacuum delete](https://github.com/CUBRID/cubrid/pull/7695)
>
> **Original review:** [PR-7695-report_01d110e_claude.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26950/PR-7695-report_01d110e_claude.md)
>
> **Original reviewed commit:** [`01d110e8`](https://github.com/CUBRID/cubrid/commit/01d110e8a3ac7659d6421f9c1b54e60520e21df9)
>
> **Follow-up commit:** [`b5d53f04`](https://github.com/CUBRID/cubrid/commit/b5d53f044536369c272d891603d5880fd4d8f061)
>
> **Verified PR HEAD:** [`192127cd`](https://github.com/CUBRID/cubrid/commit/192127cdcc10e772e0f8da1315ce89f82dab80fd)
>
> **Verification date:** 2026-08-14

## Executive Summary

원 리뷰에서 지적한 **Blocking 항목은 해소되었다.** generation mismatch 및 slot reuse 시 stale vacuum delete가 새 OOS chain을 삭제하지 않는다는 테스트가 standalone/server 양쪽에 추가되었고, replication path가 generation을 동일하게 전달하는지도 검증한다.

원 보고서의 10개 항목을 현재 PR HEAD에서 다시 확인한 결과는 다음과 같다.

- **완전 반영:** 8개
- **부분 반영:** 2개
- **미반영 Blocking:** 0개
- **로컬 검증:** debug GCC 빌드 성공, 구성된 OOS CTest **26/26 통과** (112.05초)

따라서 원 리뷰의 merge-blocking 사유는 제거되었다. 다만 page reincarnation 계약의 Jira 반영, `generation_out` API 강제성, generation wrap/zero 정책, OOS 규범 문서 및 인접 테스트 주석 동기화는 후속 조치가 필요하다.

## Verification Baseline

| 항목 | 값 |
|---|---|
| PR | `CUBRID/cubrid#7695` |
| Base branch | `feat/oos` |
| PR branch | `CBRD-26950-oos-vacuum-delete-overlap` |
| 원 리뷰 기준 | `01d110e8a3ac7659d6421f9c1b54e60520e21df9` |
| 재검증 기준 | `192127cdcc10e772e0f8da1315ce89f82dab80fd` |
| 핵심 후속 변경 | `b5d53f044536369c272d891603d5880fd4d8f061` |

재검증 시 로컬 HEAD와 GitHub의 PR head SHA가 정확히 일치하는 것을 확인했다. 소스 변경 없이 빌드와 구성된 OOS CTest 전체를 실행했다.

## Finding Status

| # | 원 리뷰 항목 | 상태 | 현재 근거 |
|---:|---|---|---|
| 1 | generation mismatch/slot reuse 회귀 테스트 부재 (Blocking) | **Fixed** | `unit_tests/oos/test_oos_delete.cpp:459`, `:514`; `unit_tests/oos/test_oos_delete_server.cpp:386`, `:436`에 standalone/server 테스트 추가. `unit_tests/oos/test_oos_server.cpp:652-680`에서 replication generation 전달 검증. |
| 2 | locator에서 published OOS ref 개수의 경계 검사 부재 | **Fixed** | `src/transaction/locator_sr.c:14263-14271`에서 capacity 초과를 검사하고 오류 처리. |
| 3 | `spage_insert` 성공 후 후속 실패 시 rollback 누락 | **Fixed** | `src/storage/oos_file.cpp:1575-1583`에서 unlogged insert를 명시적으로 제거. |
| 4 | generation 확인과 삭제 사이 TOCTOU 가능성 | **Fixed** | `src/storage/oos_file.cpp:2277-2430`에서 동일한 write latch를 보유한 상태로 generation을 확인하고 삭제. |
| 5 | `oos_ref_in_vector` 선형 탐색의 크기 상한 근거 부재 | **Fixed** | `src/storage/oos_util.cpp:31-47`에 bounded vector라는 계약과 비용 근거 추가. |
| 6 | page reincarnation 시 generation seed 보존 계약 | **Partial** | `src/storage/oos_file.cpp:2181-2186`에 소스 주석은 추가되었으나, [CBRD-26786](http://jira.cubrid.org/browse/CBRD-26786)의 생성/재사용 계약에는 아직 명시되지 않음. |
| 7 | generation publication API의 오용 방지 | **Partial** | `oos_get_generation`은 `src/storage/oos_file.hpp:148-152`에서 테스트 전용으로 제한됨. 그러나 `oos_insert::generation_out`은 `:130-136`에서 여전히 optional/default `NULL`이므로 새 호출자가 publication을 빠뜨릴 수 있음. |
| 8 | 미사용 `oos_oid_in_vector` | **Fixed** | dead helper 제거. |
| 9 | `oos_published_ref` 중복 타입의 의도 불명확 | **Fixed** | `src/thread/thread_entry.hpp:322-333`에 transaction-layer ownership과 storage-layer type 분리 이유 추가. |
| 10 | SQL boundary 테스트의 stale 16-byte 주석 | **Fixed** | 원 리뷰가 직접 지목한 `unit_tests/oos/sql/test_oos_sql_boundary.cpp:299-306` 주석을 20-byte stub 기준으로 수정. |

## Blocking Finding Resolution

새 테스트는 다음의 핵심 불변식을 직접 고정한다.

1. vacuum이 수집한 `(OID, generation)`이 현재 slot의 generation과 다르면 삭제는 no-op이다.
2. 동일 slot이 재사용되어 새 OOS chain을 가리키더라도 이전 generation의 vacuum 작업은 새 chain을 삭제하지 않는다.
3. standalone과 server 경로가 같은 의미를 보장한다.
4. replication에서 OOS reference와 함께 generation 값이 전달된다.

이 테스트들이 추가되고 전체 OOS CTest가 통과했으므로, 원 보고서의 유일한 Blocking 지적은 해소된 것으로 판단한다.

## Remaining Follow-ups

### 1. Page reincarnation contract를 CBRD-26786에 명문화

소스 주석만으로는 page deallocation/reallocation 구현이 generation counter를 어떤 값으로 초기화해야 하는지 시스템 경계를 넘어 보장하기 어렵다. CBRD-26786의 수명주기 계약에 다음 내용을 명시하는 것이 필요하다.

- 재사용된 page가 stale OOS reference와 우연히 같은 generation을 발급하지 않아야 한다.
- page header 초기화와 reincarnation 시 generation seed의 출처 및 보존 규칙.
- violation 시 stale vacuum delete가 새 chain을 삭제할 수 있다는 영향.

### 2. `generation_out` publication 계약 강화

현재 경고 주석은 추가되었지만 타입/API가 publication 누락을 막지는 않는다. 다음 중 하나를 명시적으로 선택할 필요가 있다.

- vacuum-visible insert에서는 `generation_out`을 필수 인자로 만든다.
- publication이 필요 없는 별도 API와 필요한 API를 분리한다.
- optional 상태를 유지한다면 허용되는 caller 범위와 검증 책임을 계약으로 고정한다.

### 3. Wrap-around 및 generation zero 정책 정합화

현재 increment는 `src/storage/oos_file.cpp:1545`의 단순 `generation_counter + 1`이고, overflow guard 또는 zero skip은 없다. 반면 `src/storage/oos_file.hpp:133`은 zero를 “never-issued” 값으로 설명한다.

[CBRD-26950](http://jira.cubrid.org/browse/CBRD-26950)은 vacuum retry window 안에 같은 page에서 `2^32`회 insert/delete가 필요하므로 `uint32_t` wrap 충돌 위험을 수용한다고 기록한다. 이는 실무적으로 합리적인 위험 수용일 수 있으나, 다음 중 하나로 코드와 계약을 맞춰야 한다.

- zero를 건너뛰거나 overflow를 방어한다.
- zero가 실제로 발급될 수 있음을 문서화하고 “never-issued” 설명을 수정한다.

### 4. OOS 규범 문서와 인접 테스트 주석 동기화

`/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`는 아직 16-byte OOS inline stub 및 `>16B` eligibility를 설명하지만 현재 구현은 20-byte stub이다 (`src/base/object_representation.h:459`). CBRD-26950 acceptance criteria에도 이 문서 갱신이 포함되어 있다.

원 리뷰가 직접 지적한 boundary 주석은 고쳤지만 인접한 stale 표현도 남아 있다.

- `unit_tests/oos/sql/test_oos_sql_boundary.cpp:324`: `OR_OOS_INLINE_SIZE (16)` 및 raw `DB_PAGESIZE/4`
- `unit_tests/oos/sql/test_oos_sql_bigone.cpp:51`: `OR_OOS_INLINE_SIZE = 16 B`

이 항목들은 현재 삭제 안전성 구현을 무효화하지는 않지만, 이후 구현/테스트 판단의 기준이 갈라지는 것을 막기 위해 병합 전 또는 명시적인 후속 작업으로 정리하는 편이 안전하다.

## Additional Maintainability Notes

다음은 원 보고서의 Blocking 여부와 무관한 비차단 개선점이다.

- standalone/server delete 테스트의 시나리오가 거의 중복되므로 공통 fixture/helper로 의도를 한 곳에 모을 수 있다.
- `(OID, generation)` pair를 보관하는 멤버 이름 `oos_oids`는 실제 데이터 의미를 충분히 드러내지 않는다.

## Verdict

**원 리뷰 기준으로 PR #7695의 Blocking 문제는 해결되었고, 10개 지적 중 8개는 완전히 반영되었다.** 나머지 2개는 방어적 설명은 추가되었지만 시스템 계약 또는 API 수준의 오용 방지가 끝나지 않아 Partial로 유지한다.

현재 구현과 회귀 테스트는 PR의 핵심 목표인 “vacuum delete 전에 OOS chain identity를 검증하여 slot reuse overlap으로 인한 오삭제를 방지”하는 동작을 뒷받침한다. 남은 작업의 중심은 구현 결함보다는 계약 명문화, API 견고성, 문서 정합성이다.
