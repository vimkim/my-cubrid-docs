https://jira.cubrid.org/browse/CBRD-28271

## Purpose

- serial 값을 받는 `NEXT VALUE` 가 페이지 공간이 부족해 실패하면, 장애 뒤 DB를 다시 시작할 수 없게 됩니다.
- AS-IS: `serial_update_serial_object` 는 새 serial 행을 redo 전용 로그(`RVHF_UPDATE`)로 먼저 남기고, 그다음에 행을 같은 slot에 덮어씁니다. 공간 확인은 debug 빌드의 `assert` 뿐이라, release 빌드에서 행이 들어가지 않으면 갱신은 실패하는데 redo 로그는 남습니다. 장애 뒤 restart recovery가 이 로그를 적용하다 같은 이유로 실패해, 재시작과 `checkdb` 가 매번 `LOG FATAL ERROR` 로 멈춥니다.
- TO-BE: 행이 들어가지 않으면 로그를 남기지 않고 `ER_QPROC_CANNOT_UPDATE_SERIAL` 로 실패합니다. 장애 뒤에도 재시작과 `checkdb` 가 정상으로 끝나고, serial 값은 마지막으로 커밋된 값입니다.
- redo 전용 로그: 되돌리는(undo) 기록 없이, 다시 적용할(redo) 내용만 남기는 로그입니다. 트랜잭션이 취소되어도 지워지지 않습니다.

## Implementation

- `src/query/serial.c` `serial_update_serial_object`: `assert (spage_is_updatable (...))` 를 release에서도 동작하는 확인으로 바꾸고, redo 로그를 쓰기 **전에** 실행합니다. 일반 heap 갱신(`heap_update_home`)과 같은 순서입니다.
- 확인에 실패하면 오류를 설정하고 기존 `exit_on_error` 경로(flush mark 종료, sysop abort)로 나갑니다. 로그와 페이지 모두 바뀌지 않습니다.

## Remarks

- 행이 커지는 이유: NUMERIC 값의 디스크 크기가 값에 따라 4~20바이트로 달라서(CBRD-26006), `current_val` 이 커지면 serial 행도 커집니다.
- 행이 들어가지 않을 때 `NEXT VALUE` 와 serial cache write-back은 이전처럼 실패합니다. 이 경우에도 성공하게 하는 폴백과 relocation된 serial 행 처리(CBRD-28272)는 CBRD-28292에서 다룹니다.
- 검증: JIRA 재현 절차(4K 페이지, `unfill_factor=0`, 실패한 `NEXT VALUE` 뒤 커밋하고 프로세스 강제 종료)를 release 빌드에서 실행했습니다.
  - 수정 전: SA 모드와 server 모드 모두 재시작과 `checkdb` 가 `LOG FATAL ERROR: log_rv_redo_record_sync ... data_length = 766` 으로 실패했습니다.
  - 수정 후: 두 모드 모두 재시작과 `checkdb` 가 성공했고, serial의 `current_val` 은 커밋된 값 1입니다.
- 회귀 테스트: `cubrid-testcases-private-ex` 의 `shell/_06_issues/_26_2h/cbrd_28271` 를 추가합니다. SA 모드와 server 모드에서 위 절차를 실행하고, 수정된 debug 빌드와 release 빌드에서 통과했습니다.
