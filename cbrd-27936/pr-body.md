https://jira.cubrid.org/browse/CBRD-27936

> **Validation only.** 이 draft PR은 CI로 수정을 검증하려고 올렸다. 정식 PR 여부는 담당자 검토 뒤 정한다.

## Purpose

- 레코드를 지운 트랜잭션은 그 바이트를 undo용으로 예약한다(saved space). `log_commit_local`은 이 예약을 commit 로그보다 먼저 푼다. 그 사이 다른 트랜잭션이 바이트를 쓰고 서버가 중단되면, 재시작 복구가 삭제를 되돌릴 공간을 못 찾을 수 있다.
- AS-IS: saved space를 commit 로그를 쓰기 전에 푼다.
- TO-BE: saved space를 commit 로그를 쓴 뒤에 푼다.

## Implementation

- `src/transaction/log_manager.c`: `log_commit_local`에서 `spage_free_saved_spaces` 호출을 commit 로그 append 뒤로 옮긴다. 2PC 경로에서는 commit 결정 로그가 이미 flush된 상태이므로 그 자리에서 푼다.

## Remarks

- 이 수정과 CBRD-27935 수정을 함께 넣은 PR #8494(Inner Table POC)의 gha-ci run 43022406457에서 CREATE INDEX 중 `btsort_radix_validate` assert와 재시작 복구 중 `spage_find_empty_slot_at` assert가 났다. 같은 base의 develop은 통과했다. 두 수정을 따로 올려 어느 쪽이 원인인지 가린다. CBRD-27935는 별도 draft PR로 검증한다.
- 로컬 확인: 바뀐 파일을 debug와 `-O2 -Werror`로 컴파일했다. 서버 실행 테스트는 CI에 맡겼다.
