https://jira.cubrid.org/browse/CBRD-28046

## Purpose

- postpone(커밋 뒤에 실행할 작업)을 남긴 트랜잭션은 커밋마다 로그를 디스크에 두 번 동기화(flush)하고 기다린다. 한 행씩 자주 커밋하는 부하에서 이 대기가 그대로 지연이 된다.
- AS-IS: `LOG_COMMIT_WITH_POSTPONE`을 기록한 뒤 flush하고, postpone을 실행한 뒤 `LOG_COMMIT`을 기록하고 다시 flush한다.
- TO-BE: 커밋 응답 직전의 `LOG_COMMIT` flush 한 번만 기다린다. 단, 파일 시스템에서 LOB 파일을 지우는 postpone은 지우기 전에 커밋 기록을 디스크에 확정한다.

## Implementation

- `log_append_commit_postpone`에서 `logpb_flush_pages` 호출을 뺐다. sysop 쪽은 이미 flush 없이 동작한다. CUBRIDSUS-17980(`5fe4e4eb97`, 10.0)이 `log_append_topope_commit_postpone`에서 flush를 뺐고, 10.1의 CBRD-20185가 이 함수를 지금의 `log_append_sysop_start_postpone`으로 새로 쓰면서 그 형태를 유지했다.
- 페이지를 바꾸는 postpone은 이 flush가 없어도 안전하다. 로그는 LSA 순서로 디스크에 쓰이고, 페이지는 자기 로그보다 먼저 디스크에 쓰이지 않는다(WAL). 그래서 postpone의 결과가 디스크에 있으면 `LOG_COMMIT_WITH_POSTPONE`도 디스크에 있다.
- 예외는 `RVHF_LOB_REMOVE_DIR` 하나다. 이 postpone은 `fileio_lob_remove_matching_dir`로 LOB 파일을 지우고, 이 동작은 로그로 되돌릴 수 없다. 그래서 `heap_rv_lob_remove_dir`이 파일을 지우기 전에 `logpb_flush_log_for_wal`로 `tran_start_postpone_lsa`까지 로그를 확정한다. 복구 중에는 이미 디스크에 있으므로 아무 일도 하지 않는다.

## Remarks

- `log_append_postpone` 호출 지점을 모두 확인했다. 로그로 보호되지 않는 동작(파일 시스템 변경)을 하는 postpone은 `RVHF_LOB_REMOVE_DIR`뿐이었다.
- 측정: OOS UPDATE + COMMIT 3000번에서 `fdatasync` 횟수가 6006에서 3006으로 줄었고, 지연은 postpone이 없던 수준으로 돌아왔다(CBRD-27781 브랜치 기준, 수치는 이슈에 있다).
- crash 시험(release 빌드):
  - 한 트랜잭션에서 300개 테이블을 DROP하고 커밋하는 도중 서버를 24번 SIGKILL했다. 부분 커밋, 응답받은 커밋의 유실, `checkdb` 실패는 모두 0건이었다(롤백 19번, 커밋 5번).
  - BLOB 테이블 DROP 커밋 중 LOB 파일을 지운 직후 서버를 죽였다. 이 PR은 테이블이 삭제된 상태로 복구됐다. LOB 쪽 보호를 뺀 빌드는 테이블이 되살아나고 BLOB 값이 모두 NULL이 되어, 보호가 필요함을 확인했다.
  - 시험 스크립트: https://github.com/vimkim/my-cubrid-docs/tree/main/cbrd-28046/test
- 리뷰 포인트: 위 전제를 깨는 postpone이 더 있는지, 그리고 CBRD-26885(COMMIT 후처리 분리)의 방향과 맞는지 봐 주세요.
