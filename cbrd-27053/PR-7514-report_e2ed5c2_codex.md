# PR #7514 코드 리뷰 보고서

**PR:** [CUBRID/CUBRID#7514](https://github.com/CUBRID/cubrid/pull/7514)
**제목:** [CBRD-27053] Fix use-after-free on partitioned table DROP
**작성자:** InChiJun
**HEAD SHA:** `e2ed5c29966b0e5463ab8f27d4fb5e827049e3c7`
**리뷰 일시:** 2026-08-26

> **TL;DR** (Non-blocking): 부모 클래스가 decache (캐시된 클래스 객체 해제) 되어도 안전하도록 `SM_CLASS::users` 목록의 사본을 순회하고, 클래스 이름 삭제 실패를 호출자에게 전파한다. 머지를 막을 결함은 발견하지 못했다.

## Summary

- **변경 요약**: 파티션 테이블 DROP 중 부모 클래스 캐시 해제로 발생하는 use-after-free와 오류 은폐를 함께 수정
- **주요 이슈**: 없음
- **확인 필요 사항**: 기존 선언 위치 관련 리뷰 코멘트 1건

---

## Findings

없음

## JIRA Context

CBRD-27053은 파티션 테이블 DROP 도중 서버 종료 시 `ws_oid`에서 발생하는 클라이언트 crash를 다룬다. PR은 `SM_CLASS::users` (부모 클래스가 소유하는 자식 클래스 목록)의 수명과 `LC_CLASSNAME_ERROR` (클래스 이름 작업 실패 결과) 전파라는 두 원인을 모두 수정해 티켓의 확정된 분석과 일치한다.

## Verification

- `ml_copy`가 새 목록 노드를 만들고 `ml_free`가 그 노드만 해제하므로, 부모 `SM_CLASS`의 decache 이후에도 순회 목록은 유효하다.
- `locator_delete_class_name`의 네트워크 실패가 설정한 서버 종료 오류를 `ASSERT_ERROR_AND_SET`이 `error_code`로 전파한다.
- 로컬 `debug_gcc` 빌드에서 변경된 `execute_schema.c`와 `locator_cl.c`가 SA/CS (standalone/client-server 빌드 모드)로 컴파일됐다. 전체 빌드는 관련 없는 후속 대상 처리 중 signal 2로 종료되어 완료 여부는 확인하지 못했다.

## Existing Comments

| Author | File | Comment |
|---|---|---|
| youngjun9072 | `src/transaction/locator_cl.c:5689` | `class_` 선언을 실제 사용 위치에 가깝게 옮길지 제안한 기존 nit이며 작성자 답변은 없다. |
