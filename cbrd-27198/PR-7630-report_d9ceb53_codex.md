# PR #7630 코드 리뷰 보고서

**PR:** [CUBRID/CUBRID#7630](https://github.com/CUBRID/cubrid/pull/7630)
**제목:** [CBRD-27198] Do not let a no-wait transaction demote the disk manager's page latches
**작성자:** kwangsoochae
**HEAD SHA:** `d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530`
**리뷰 일시:** 2026-08-26

> **TL;DR** (Non-blocking): 현재 HEAD는 이론적으로 ACCEPT 가능하다. `lock_timeout=0`의 공개 계약은 transaction lock 대기 금지이며, 이 변경은 기존 latch 획득 순서나 보유 구간을 바꾸지 않고 disk metadata의 unconditional latch 정책만 복구한다.

## Summary

- **변경 요약**: 디스크 관리자의 volume-header 및 sector allocation-table fix가 transaction의 zero-wait 값 때문에 conditional latch로 강등되지 않도록 thread-local save/restore 범위를 추가
- **주요 이슈**: blocking 및 non-blocking finding 없음
- **확인 필요 사항**: 없음

---

## Findings

없음

## JIRA Context

CBRD-27198은 `lock_timeout=0` 세션의 volume-header latch 요청이 즉시 거절되어 `disk_reserve_sectors`의 debug assert를 유발하는 결함이다. 현재 구현은 사용자 값인 `LK_ZERO_WAIT`와 더 넓은 engine 내부 값인 `LK_FORCE_ZERO_WAIT`를 해당 두 disk-page fix 범위에서 `LK_INFINITE_WAIT` 분류로 바꾸고, 양수 및 기존 infinite 정책은 보존한다.

## Theoretical Acceptability

- [`lock_timeout`](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/admin/config.rst#L1148-L1150)은 transaction lock의 대기 정책이다. 사용자에게 노출된 no-wait 계약이 내부 page latch까지 non-blocking이어야 한다는 의미는 아니다.
- `lock_timeout=0`은 lock deadlock 방지 장치로 한정되지 않는다. 이미 충돌한 lock을 기다리지 않게 하는 fail-fast 정책이며, lock deadlock 탐지와 희생자 선정은 별도 메커니즘이다.
- page latch도 deadlock될 수 있다. 기존 `btree.c:19764-19771`은 B-tree page latch를 보유한 상태의 추가 fix가 `dead latch`를 만들 수 있어 `LK_FORCE_ZERO_WAIT`를 사용하고, `page_buffer.c:7303`은 latch watchdog 만료를 `buffer page deadlock victim by timeout`으로 처리한다.
- scoped override가 `LK_INFINITE_WAIT` 분류를 반환해도 active transaction의 한 번의 `pgbuf_timed_sleep()`은 `page_latch_timeout_in_msecs` watchdog으로 제한되며 기본값은 약 300초다. Inactive transaction은 watchdog 만료 뒤 다시 대기하므로 전체 대기 시간이 항상 300초로 제한되는 것은 아니다.
- 변경 전부터 기본 `lock_timeout=-1` transaction은 동일한 volume-header -> sector-table 순서로 기다렸다. 이번 diff는 새 latch 획득 순서나 lock-manager wait-for-graph edge를 추가하지 않지만, zero-wait request를 즉시 거절하는 대신 기존 BCB latch queue에 참여시키므로 해당 transaction의 runtime wait dependency는 새로 생긴다.
- 역순 가능성도 확인했다. Sector latch를 받은 recovery callback은 `CSECT_DISK_CHECK`를 zero-time으로 시도하고, 실패하면 latch를 unfix한 뒤 critical section을 기다리고 page를 다시 fix하므로 sector latch -> blocking critical-section 순환은 만들지 않는다(`disk_manager.c:3909-3942`, `3992-4025`).
- 가장 강한 잔여 위험은 engine 내부 회피 값인 `LK_FORCE_ZERO_WAIT`도 override한다는 점이다. `bestspace.cpp:680` -> `pgbuf_ordered_fix()` -> debug page validation -> disk helper의 간접 진입은 존재하지만, validator가 helper 진입 전에 transaction wait를 `LK_INFINITE_WAIT`로 바꾸고 종료 뒤 `LK_FORCE_ZERO_WAIT`를 복원한다. 따라서 helper는 force-zero를 관측하지 않으며, PR이 기존 dead-latch 회피를 새로 무력화하는 경로는 확인되지 않았다(`disk_manager.c:4203-4244`).
- 따라서 정책 자체는 수용 가능하다. 300초 watchdog은 active transaction의 개별 latch wait를 끊는 안전망이지 latch deadlock이 불가능하다는 증거는 아니다.

## Verification

- Native Codex review: 현재 diff에서 actionable correctness issue 없음
- [GitHub checks](https://github.com/CUBRID/cubrid/pull/7630/checks): build, build_debug, SQL, medium, shell, code-style, cppcheck, license, memory-monitor-check, pr-style 통과
- Exact HEAD gate: `check-prereqs.sh` 결과 local HEAD와 PR HEAD가 `d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530`으로 일치
