# PR #7298 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7298](https://github.com/CUBRID/cubrid/pull/7298)
**제목:** [CBRD-26937] Reject OOS + bigone coexistence with a user error
**작성자:** vimkim
**HEAD SHA:** `879d863eaf724079db7add47147025d06a3c9175`
**리뷰 일시:** 2026-06-29

> **TL;DR** (Non-blocking): PR diff 기준 머지 전 필수 수정 사항 없음. OOS (큰 가변 컬럼을 OOS file 로 분리하는 저장 방식) + `REC_BIGONE` (한 레코드를 overflow 파일에 저장하는 타입) 거부 위치와 테스트 범위가 CBRD-26937 의도와 맞다.

## Summary

- **변경 요약**: `heap_attrinfo_transform_to_disk_internal` 에 OOS + `REC_BIGONE` 거부 게이트를 추가하고 SQL 단위 테스트와 신규 에러 메시지를 등록
- **주요 이슈**: 없음
- **확인 필요 사항**: 없음

---

## Findings

없음

## JIRA Context

CBRD-26937 의 목표는 OOS demotion (쓰기 시 큰 가변 컬럼을 외부 OOS record 로 내보내는 동작) 후에도 레코드가 `heap_Maxslotted_reclength` (heap slotted page 에 직접 저장 가능한 최대 레코드 길이)를 넘는 조합을 사용자 에러로 거부하는 것이다. 본 PR은 해당 게이트를 OOS record 쓰기 전 공통 변환 경로에 두고, INSERT/UPDATE/일반 bigone/4KB-16KB 허용 케이스를 테스트해 티켓 의도와 일치한다.
