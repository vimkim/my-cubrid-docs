# PR #7298 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7298](https://github.com/CUBRID/cubrid/pull/7298)
**제목:** [CBRD-26937] Reject OOS + bigone coexistence with a user error
**작성자:** vimkim
**HEAD SHA:** `879d863eaf724079db7add47147025d06a3c9175`
**리뷰 일시:** 2026-06-29

> **TL;DR** (Non-blocking): OOS (Out-of-row Storage -- 큰 가변 컬럼을 외부 OOS 파일로 분리 저장) demotion (큰 가변 컬럼을 OOS 로 내보내 레코드를 줄이는 과정) 후에도 레코드가 최대 크기를 넘어 bigone (REC_BIGONE -- 레코드 전체를 overflow 페이지에 통째로 저장하는 타입) 으로 빠지는 조합을, 쓰기 전에 사용자 에러로 막는다. 게이트는 정확하고 안전한 방향(거부)이라 머지 가능하다. 다만 게이트 임계값이 실제 bigone 판정보다 더 엄격해 경계 바로 아래의 저장 가능한 OOS 행이 새로 거부되는 점만 의도 확인이 필요하다.

## Summary

- **변경 요약**: `heap_attrinfo_transform_to_disk_internal` 에 `has_oos && heap_is_big_length(expected_size)` 게이트를 추가하고 신규 에러 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (-1377) 를 던진다. 기존 base(`feat/oos`)에서 이 조합은 release 빌드에서도 `abort()` 로 크래시했다.
- **주요 이슈**: 게이트가 `expected_size` (레코드 크기 + 아직 기록되지 않은 MVCC 최대 헤더 예약분) 로 판정하는데, 실제 bigone 결정은 더 작은 `record_size` 로 한다 -> 경계 바로 아래에서 신규 false-positive 거부 (Non-blocking).
- **확인 필요 사항**: 위 과대 거부가 의도된 보수적 설계인지, downstream 경계(`record_size`)에 맞춰야 하는지.

---

## Findings

### Non-blocking (should consider)

- `src/storage/heap_file.c:13079` -- 게이트는 `heap_is_big_length((int) expected_size)` 로 판정한다. 그런데 `expected_size` 는 line 13071 에서 `OR_MVCC_MAX_HEADER_SIZE - OR_MVCC_INSERT_HEADER_SIZE` (32-16 = 16B, 향후 in-place MVCC delete-id/prev-version 을 위한 예약 공간) 만큼 부풀려진 값이다. 반면 실제 REC_BIGONE 결정은 `heap_insert_adjust_recdes_header` (`heap_file.c:21504`) / `heap_update_adjust_recdes_header` (`:21723`) 에서 더 작은 `record_size` (= 빌드된 `recdes` (레코드 디스크 이미지) 길이 + INSID (insert MVCCID), 예약 공간 미포함) 로 한다. 결과: 빌드된 레코드가 `heap_Maxslotted_reclength` (최대 슬롯 레코드 길이, ~16KB) 바로 아래의 좁은 구간(예약분 폭, 최대 ~16B)에 드는 OOS 행은 게이트 없이는 REC_HOME (페이지 내 일반 저장) 으로 정상 저장되지만, 이제 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 로 새로 거부된다. 데이터 손상이 아닌 안전한 방향이고 예약 공간을 고려하면 정당화도 가능하나, 이 PR 이 도입하는 신규 false-positive 다. downstream 경계와 정확히 맞추려면 `record_size` 로 비교해야 한다 -- 보수적 임계값이 의도인지 확인 바란다. (부수: 에러 메시지의 보고 크기 `%1$d` 도 부풀려진 `expected_size` 라 실제 레코드보다 크게 표시된다. 임계값 인자 `%2$d` 는 비교값과 일치.)
- `unit_tests/oos/sql/test_oos_sql_bigone.cpp:96` -- `BIT(140000)`=17500B, `BIT(100000)`=12500B 를 ~16KB `heap_Maxslotted_reclength` 에 맞춰 하드코딩했으나 fixture 페이지 크기를 고정하지 않는다. `heap_Maxslotted_reclength` 는 `DB_PAGESIZE` 에 비례하므로, OOS_DB fixture 의 createdb 가 향후 `--db-page-size=4096` 를 받으면 임계값이 ~3.9KB 로 떨어져 `OosColumnInlineBetween4kAnd16kSucceeds` 자체가 bigone 이 되어 통과->실패로 뒤집힌다(현재 기본 16KB 라 통과). 16KB 회귀 가드의 의도가 코드로 고정되어 있지 않다.
- `docs/CBRD-26937-merge-conflict-resolution-report.ko.md:1` -- 특정 병합 커밋(`5e1150749`)과 날짜를 명시한 일회성 병합 충돌 해결 서사 148줄(diff 의 ~45%)을 추적 대상 `docs/` 트리에 커밋했다. PR 설명/커밋 본문에 둘 내용이며, 에러 번호가 다시 재배정되면 즉시 stale 해진다(이미 -1375->-1377 재배정 한 건을 기록 중). 영속적 설계 문서 사이에 섞여 유지보수 노이즈가 된다.

## JIRA Context

CBRD-26937 (CBRD-26583 의 sub-task) 의 목표는 "bigone + OOS 공존 시 사용자 에러 표시". 본 PR 은 정확히 그 범위 안이며, base 에서 이 조합이 `abort()` (heap_file.c:21508-21516, 기존 `TEMP CBRD-26668 REVERT BEFORE MERGE` 하드 크래시) 로 죽던 것을 쓰기 시점의 결정론적 사용자 에러로 대체한다. `expected_size >= record_size` 이므로 게이트는 항상 이 `abort()` 보다 먼저 발동해 under-rejection (실제 OOS+bigone 누락) 은 없다. 신규 에러 코드는 6곳 룰 (새 에러는 `error_code.h`, en/ko `cubrid.msg`, `ER_LAST_ERROR` 등 갱신) 을 충족한다 -- `dbi_compat.h` 는 `error_code.h` 를 직접 `#include` 하므로 자동 반영되고, 서버 내부 에러라 CCI 는 불필요(직전 sibling OOS 에러도 동일).
