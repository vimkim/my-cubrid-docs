# PR #7617 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617)
**제목:** [CBRD-26786] Reclaim empty OOS pages in vacuum via file_dealloc
**작성자:** vimkim
**HEAD SHA:** `8ba9b53989245bb1e73ebc821d0421fd6b291feb`
**리뷰 일시:** 2026-09-01

> **TL;DR** (Blocking): OOS(Out-of-row Overflow Storage, 큰 속성 값을 힙 레코드 밖에 저장하는 구조)의 청크 삽입 복구 로그인 `RVOOS_INSERT`의 undo가 페이지를 비워도 성장 게이트 sweep(파일 확장 직전 빈 페이지를 탐색해 회수하는 절차)을 재무장하지 않습니다. 반복 rollback이 회수 가능한 페이지를 남겨 파일을 계속 확장시킬 수 있습니다.

## Summary

- **변경 요약:** vacuum 삭제 배치가 건드린 페이지를 즉시 회수하는 경로와 성장 게이트 sweep을 추가해 비어 있는 OOS 페이지를 `file_dealloc`로 반환합니다.
- **주요 이슈:** INSERT rollback으로 비어진 페이지는 삭제 카운터를 올리지 않으므로 성장 게이트가 실행되지 않습니다.
- **확인 필요 사항:** `RVOOS_INSERT` undo 경로에서 파일의 회수 상태를 재무장하고, rollback 반복 시 OOS 파일 페이지 수가 증가하지 않는 회귀 테스트가 필요합니다.
- **검증:** 로컬 빌드가 성공했고, 구성된 OOS 단위 테스트 27개가 모두 통과했습니다. 별도 집중 재현에서는 페이지 수가 기대값 3이 아니라 4로 증가했습니다.

---

## Findings

### Blocking (must fix)

- `src/storage/oos_file.cpp:1931-1932` -- 새 파일은 `swept_this_boot = true`로 등록되지만(`src/storage/oos_file.cpp:1404`), `RVOOS_INSERT` undo가 호출하는 `oos_rv_redo_delete`는 bestspace hint(재사용 후보 메모리 힌트)만 제거하고(`src/transaction/recovery.c:875-878`, `src/storage/oos_file.cpp:3370-3373`) `pending_deletes`를 올리지 않습니다. 재무장 함수는 정상 `oos_delete`에서만 호출되므로(`src/storage/oos_file.cpp:3316-3322`), 페이지를 채운 INSERT와 rollback을 반복하면 성장 sweep이 실행되지 않은 채 새 페이지가 계속 할당됩니다.

```cpp
else if (!it->second.sweep_in_progress
         && (it->second.pending_deletes > 0 || !it->second.swept_this_boot))
```

## JIRA Context

CBRD-26786의 핵심 불변식은 안전하게 회수 가능한 빈 OOS 페이지가 남아 있는 동안 새 섹터를 예약하지 않는 것입니다. 현재 구현은 INSERT rollback으로 생긴 빈 페이지를 다음 부팅이나 무관한 OOS 삭제 전까지 탐색하지 않으므로 이 불변식을 충족하지 못합니다.
