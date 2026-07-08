# PR #7391 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7391](https://github.com/CUBRID/cubrid/pull/7391)
**제목:** [CBRD-27006] Improve OOS recdes locality
**작성자:** vimkim
**HEAD SHA:** `fb42a24638266509c60a352b54d7ff9d0372919a`
**리뷰 일시:** 2026-07-08

> **TL;DR** (Non-blocking): OOS (큰 가변 길이 값을 `heap record` (테이블 row의 on-disk record) 밖의 `OOS file` (OOS 값을 저장하는 별도 file)에 저장하는 방식) `recdes` (record descriptor bytes) locality 개선은 CBRD-27006 의도와 맞고, 새 batch insert/read 경로에서 머지 차단 이슈는 발견하지 못했다. Native review 과정에서 OOS 대상 빌드와 테스트를 수행했고 모두 통과했다.

## Summary

- **변경 요약**: `oos_insert_many()` / `oos_read_many()` 로 같은 record의 single-chunk OOS 값을 같은 OOS page (OOS file 안의 slotted page)에 모으고 read를 page별로 묶음.
- **주요 이슈**: 없음.
- **확인 필요 사항**: 없음.

---

## Findings

없음

## JIRA Context

CBRD-27006 은 CBRD-26583 의 sub-task이며 목적은 한 heap record 안의 여러 OOS 값이 가능한 같은 OOS page에 모이도록 recdes locality를 개선하는 것이다. PR은 on-disk OOS format, OOS OID 공유 정책, replication log format을 바꾸지 않는다는 범위와 일치한다.

## Verification

- `codex review --base origin/feat/oos` 완료.
- Native review 중 `cmake --build build_preset_debug_gcc --target test_oos_server test_oos_sql_crud -j2` 성공.
- Native review 중 `ctest --test-dir build_preset_debug_gcc -R 'test_oos_server|test_oos_sql_crud' --output-on-failure` 통과: 4/4.
