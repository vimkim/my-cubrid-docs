https://jira.cubrid.org/browse/CBRD-28065

## Purpose

- 클라이언트가 COMMIT 성공을 받은 트랜잭션은 직후 서버가 비정상 종료되어도 재시작 뒤 커밋된 상태로 남아야 한다(내구성).
- AS-IS: 커밋은 `logpb_flush_pages()`에서 `nxio_lsa`(아직 디스크에 쓰지 않은 가장 낮은 LSA)가 커밋 레코드 시작 LSA보다 작은 동안만 기다린다. 다른 트랜잭션의 flush가 `nxio_lsa`를 커밋 레코드 시작과 같게 만들어 두면 커밋 레코드가 메모리에만 있는데도 응답하고, 직후 `kill -9` 하면 재시작 복구가 이 트랜잭션을 롤백한다.
- TO-BE: 커밋은 자기 커밋 레코드가 디스크에 쓰인 뒤에만 응답한다.

## Implementation

- `logpb_flush_pages()`의 대기 조건 두 곳(루프 조건과 `gc_mutex` 안의 재확인)을 `logpb_need_wal (flush_lsa)`(`nxio_lsa <= flush_lsa`)로 바꿨다. WAL 검사가 같은 경계를 이미 이 함수로 판정하므로, "이 LSA의 레코드가 디스크에 있는가"를 한 곳에서만 정한다. 쓰지 않게 된 지역 변수 `nxio_lsa`는 지웠다.
- 달라지는 경우는 `nxio_lsa == flush_lsa` 하나다. 예전에는 바로 응답했고, 이제는 flush 한 번을 기다린다.
- 모든 호출자는 방금 prior list에 넣은 레코드의 시작 LSA를 넘긴다(커밋, 체크포인트 중 abort, 2PC, HA 서버 상태). 대기자가 요청한 flush가 prior list를 모두 쓰고 `nxio_lsa`를 그 레코드 뒤로 옮기므로 대기는 끝난다.

## Remarks

- 재현(서버 SIGKILL 뒤 재시작): 세션 A가 UPDATE만 하고, 세션 B가 UPDATE와 COMMIT으로 A의 UPDATE까지 flush 한 뒤, A가 COMMIT 하고 응답 직후 서버를 죽인다. 수정 전에는 debug와 release 빌드 모두 20번 중 20번 A의 커밋이 사라졌고, 수정 후 0번이다.
- 8개 세션이 UPDATE와 COMMIT을 반복하는 중 무작위로 20번 죽이면 수정 전 1건, 수정 후 0건 손실이다. JIRA 댓글의 2PC attach 시나리오(C API)는 수정 전 5번 중 5번 커밋한 트랜잭션이 준비 상태로 되살아났고, 수정 후 0번이다.
- 성능(release, 수정 전후를 6라운드 번갈아 측정): 커밋당 fsync 횟수는 같다(1세션 0.999, 8세션 약 0.255). 커밋 지연과 처리량은 같은 빌드의 라운드 간 차이가 더 커서(8세션 처리량 868~2752커밋/초) 두 빌드를 구분하지 못했다.
- 동작이 바뀌는 커밋을 계측으로 세면 1세션은 0%, 8세션 INSERT/COMMIT 부하는 2.3~2.9%다. 이 커밋들은 수정 전에는 커밋 레코드가 디스크에 쓰이기 전에 응답했고, 이제 flush 한 번을 더 기다린다.
- 리뷰 포인트: `logpb_flush_pages()` 호출자 가운데 prior list에 넣지 않은 LSA를 넘기는 곳이 있으면 대기가 끝나지 않는다. 호출자 점검과 대기가 멈추지 않는 이유는 상세 문서에 있다.
- 같은 결함이 release/11.4, 11.3, 10.2에도 있어 백포트 PR을 따로 연다. 11.2에도 있지만 대상 버전이 아니다.
- 상세 검증과 스크립트: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-28065/verification.md
