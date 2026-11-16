https://jira.cubrid.org/browse/CBRD-28102

## Purpose

- 커밋된 트랜잭션의 postpone(커밋 뒤에 실행하도록 미뤄 둔 작업)이 커밋 시점과 재시작 복구 시점 모두에서 빠짐없이 실행되게 한다.
- AS-IS: `log_do_postpone`은 system operation(sysop)의 로그 범위를 last parent(sysop 바로 앞 레코드)부터 건너뛴다. 탐색이 정확히 last parent에서 시작하면 그 레코드도 범위 안으로 본다. 그래서 postpone 바로 뒤에 commit되는 sysop이 시작되면 그 postpone은 실행되지 않는다.
- TO-BE: last parent는 sysop 바깥 레코드로 처리된다. 그 자리의 postpone도 실행된다.

## Implementation

- `log_do_postpone`의 범위 비교를 `LSA_LT`에서 `LSA_LE`로 바꿨다. 탐색 시작이 범위 시작과 같으면, 그 레코드 하나를 먼저 처리한 뒤 범위를 건너뛴다.
- 같아지는 다른 경우는 앞 sysop의 `LOG_SYSOP_END` 바로 뒤에 다음 sysop이 시작될 때다. 이때 처리되는 레코드는 그 `LOG_SYSOP_END` 하나이고, `log_do_postpone`은 이 레코드에서 아무것도 하지 않는다.
- `log_recovery_find_first_postpone`의 같은 비교는 그대로 두었다. 이 함수에서 같을 때 건너뛰는 레코드는 시작 postpone 자신인데, 이 함수는 그 레코드를 원래 제외한다. 아래 복구 시험은 이 함수를 바꾸지 않고 통과했다.

## Remarks

- develop에서 확인한 경로: relocation된 행을 줄이는 UPDATE는 `RVHF_MARK_REUSABLE_SLOT` postpone으로 끝난다. 다음 INSERT가 heap 페이지를 할당하면 그 sysop의 last parent가 이 postpone이 된다. 결과는 `DONT_REUSE_OID` 테이블의 slot 하나가 `MARKDELETED`로 남는 작은 공간 누수다. `checkdb`는 이를 보고하지 않는다.
- OOS 브랜치(#8434, CBRD-27781)에도 같은 수정이 있다. 병합할 때 같은 hunk이다.
- sysop 안의 postpone을 실행하는 `log_sysop_do_postpone`도 이 함수를 쓰므로 같이 고쳐진다. 이 경로는 재현하지 않았다.

### Test Plan

debug 빌드, develop `666bb10ae6` 기준. 판정은 로그 덤프(`cubrid diagdb -d 8`)에서 시험 트랜잭션의 `LOG_POSTPONE`마다 `LOG_RUN_POSTPONE`이 있는지로 했다.

| 경우 | 수정 전 | 수정 후 |
|---|---|---|
| 커밋, `postpone_cache_size=4`로 캐시 초과 | 10/11 | 11/11 |
| 재시작 복구, postpone 실행 전에 서버 kill | 10/11 | 11/11 |
| 재시작 복구, 첫 postpone 실행 뒤 kill (두 번째 postpone이 sysop의 last parent) | 10/11 | 11/11 |
| 건너뛴 forward slot 상태 | `MARKDELETED` | `DELETED_WILL_REUSE` |
| shell TC `_40_guava/cbrd_28102` | NOK | OK |
