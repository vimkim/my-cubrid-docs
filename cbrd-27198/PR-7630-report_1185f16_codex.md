# PR #7630 코드 리뷰 보고서

**PR:** [CUBRID/CUBRID#7630](https://github.com/CUBRID/cubrid/pull/7630)
**제목:** [CBRD-27198] Do not turn an unconditional latch on a structural page into a conditional one
**작성자:** kwangsoochae
**HEAD SHA:** `1185f16d7e5f540ffdad4509cbd061ef0535f4df`
**리뷰 일시:** 2026-08-21

> **TL;DR** (Blocking): no-wait 구조 페이지 래치 (버퍼 페이지 접근 직렬화)를 기다리게 하는 방향은 타당하지만, 양수 `lock_timeout`까지 무한 대기로 분류해 페이지 래치 타임아웃의 에러 처리 의미를 바꾼다. zero-wait인 경우에만 override하도록 제한해야 한다.

## Summary

- **변경 요약**: 볼륨 헤더와 섹터 테이블 fix 동안 스레드별 플래그로 트랜잭션의 no-wait 설정을 무시
- **주요 이슈**: 양수 `lock_timeout`의 페이지 래치 타임아웃이 debug assert 및 트랜잭션 강제 중단 경로로 바뀜
- **확인 필요 사항**: PR에 남은 `lock_timeout`과 page latch 결합 범위 질문에 작성자 답변 필요

---

## Findings

### Blocking (must fix)

- `src/storage/page_buffer.c:16934` - `force_latch_wait`가 원래 값과 무관하게 `LK_INFINITE_WAIT` (무한 대기 분류 값)을 반환하므로 양수 `lock_timeout`도 무한 대기로 재분류되고, `page_latch_timeout_in_msecs` 만료 시 `pgbuf_timed_sleep` (페이지 래치 대기 함수)이 기존 `ER_LK_PAGE_TIMEOUT` 대신 debug `assert (0)`과 `ER_LK_UNILATERALLY_ABORTED` (트랜잭션 강제 중단) 경로를 선택한다; 원래 값이 `LK_ZERO_WAIT` 또는 `LK_FORCE_ZERO_WAIT`일 때만 override해야 한다.

```c
if (flag_owner_p != NULL && flag_owner_p->force_latch_wait)
  {
    return LK_INFINITE_WAIT;
  }
```

근거: `src/storage/page_buffer.c:7375-7420`은 `old_wait_msecs == LK_INFINITE_WAIT`에서 `assert (0)` 및 unilateral abort를 수행하고, `old_wait_msecs > 0`에서 `ER_LK_PAGE_TIMEOUT`을 반환한다.

## JIRA Context

CBRD-27198은 `lock_timeout=0`이 구조 페이지의 unconditional latch를 즉시 conditional로 강등해 `disk_reserve_sectors`의 debug assert를 유발하는 결함이다. 본 PR은 zero-wait 경로의 직접 원인을 제거하지만 양수 timeout의 기존 에러 분류까지 바꾸는 부분은 티켓 범위를 벗어난다.

## Existing Comments

| Author | Comment | Status |
|---|---|---|
| kangmin5505 | `lock_timeout`이 lock에만 한정된다면 특정 구조 페이지 예외보다 page latch까지 전파되는 근본 원인을 고쳐야 하지 않는지 질문 | 작성자 답변 없음 |
