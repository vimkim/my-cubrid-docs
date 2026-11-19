https://jira.cubrid.org/browse/CBRD-28065

## Purpose

- develop의 CBRD-28065 수정(develop PR #8642)을 release/11.3에 백포트한다. 클라이언트가 COMMIT 성공을 받은 트랜잭션은 직후 서버가 비정상 종료되어도 재시작 뒤 커밋된 상태로 남아야 한다.
- AS-IS: 커밋은 `logpb_flush_pages()`에서 `nxio_lsa`(아직 디스크에 쓰지 않은 가장 낮은 LSA)가 커밋 레코드 시작 LSA보다 작은 동안만 기다린다. 두 값이 같으면 커밋 레코드가 메모리에만 있는데도 응답하고, 직후 `kill -9` 하면 재시작 복구가 이 트랜잭션을 롤백한다.
- TO-BE: 커밋은 자기 커밋 레코드가 디스크에 쓰인 뒤에만 응답한다.

## Implementation

- develop 변경을 충돌 없이 그대로 적용했다. `logpb_flush_pages()`의 대기 조건 두 곳을 `logpb_need_wal (flush_lsa)`(`nxio_lsa <= flush_lsa`)로 바꾸고, 쓰지 않게 된 지역 변수 `nxio_lsa`를 지웠다.
- 이 라인의 호출자도 develop과 같이 방금 prior list에 넣은 레코드의 시작 LSA를 넘긴다. develop에 없는 호출자는 `log_append_commit_postpone` 하나이며, 이것도 `LOG_COMMIT_WITH_POSTPONE` 레코드의 시작 LSA로 기다린다.

## Remarks

- 재현(debug, release/11.3 `15360995b5` 기준): 세션 A가 UPDATE만 하고, 세션 B가 UPDATE와 COMMIT으로 A의 UPDATE까지 flush 한 뒤, A가 COMMIT 하고 응답 직후 서버를 SIGKILL 한다. 수정 전 20번 중 20번 A의 커밋이 사라졌고, 수정 후 0번이다.
- 성능 영향은 develop PR과 같다. 단일 세션 커밋 지연은 그대로이고, 동시 커밋에서는 그동안 디스크에 쓰이기 전에 응답하던 커밋이 flush를 기다린다.
- 상세 검증과 스크립트: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-28065/verification.md
