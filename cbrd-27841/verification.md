# CBRD-27841 검증: `RVREPL_OOS_DELETE` 제거

## Purpose

`RVREPL_OOS_DELETE`(140)를 지우고 141~144를 140~143으로 당긴 변경을 검증한 기록이다. 확인할 것은 세 가지다. 남은 recovery index가 `RV_fun[]` 위치와 맞는지, 기존 테스트가 통과하는지, OOS 작업 중 서버가 강제 종료된 뒤 복구와 vacuum 회수가 정상인지다.

- 대상: `CBRD-27841-drop-repl-oos-delete` `1d86f1d31b`, base `feature/oos-merge` `d25c9e8d20`. 강제 종료 검사는 rebase 전의 같은 패치 `9b366302dc`(base `71993ddb63`)에서 했다. 그 사이 base에 들어온 변경은 [#8638](https://github.com/CUBRID/cubrid/pull/8638)의 diagdb 문자열 한 줄뿐이다.
- 빌드: debug(GCC), 2026-11-19 Asia/Seoul

## Implementation

### `RV_fun[]` 순서

[checks/rv_fun_order.cpp](checks/rv_fun_order.cpp)는 실제 `recovery.h`를 include하고 설치한 서버 라이브러리에 링크한다. `nm -D -S`로 읽은 `RV_fun` 심볼 크기를 인자로 받아 항목 수를 계산하고, 모든 `i`에서 `RV_fun[i].recv_index == i`인지와 항목 수가 `RV_LAST_LOGID + 1`인지 검사한다. `recovery.c`의 `rv_check_rvfuns ()`는 같은 순서 검사를 debug 서버 시작 때 하지만, 항목 수는 검사하지 않는다.

```sh
size=$(nm -D -S "$CUBRID/lib/libcubrid.so" | awk '$4 == "RV_fun" {print "0x" $2}')
g++ <recovery.c의 compile_commands.json include·define 옵션> -x c++ rv_fun_order.cpp \
  -L"$CUBRID/lib" -lcubrid -Wl,-rpath,"$CUBRID/lib" -o rv_fun_order
./rv_fun_order "$size"
```

### 강제 종료 후 복구

[checks/oos_crash_recovery.sh](checks/oos_crash_recovery.sh)는 이 검사 전용 DB 하나로 다음을 한다.

1. `t_upd`, `t_del`에 200행씩 넣는다. 각 행의 두 컬럼은 `md5()` 190개를 이은 6,080바이트 값이다. 문자열 압축으로 줄지 않으므로 OOS로 저장된다.
2. 한 세션이 오래된 snapshot을 잡고 있게 한다. 그동안 vacuum은 그 뒤에 커밋된 변경을 회수할 수 없다.
3. `t_upd`의 한 컬럼을 모두 UPDATE하고 커밋한다. 옛 OOS chain은 `RVOOS_NOTIFY_VACUUM`을 vacuum이 소비해야만 회수된다(ADR-0008, A'). `t_del`의 절반을 DELETE하고 커밋한다.
4. 다른 세션이 `t_upd`에 OOS 값을 UPDATE·INSERT한 채 커밋하지 않고 기다린다.
5. `cub_server`를 `kill -9`로 종료한다. `cub_master`가 서버를 다시 시작하지 않으면 직접 시작한다. debug 빌드는 재시작 때 `rv_check_rvfuns ()`를 실행한다.
6. 커밋된 상태를 담은 참조 테이블을 NULL 행에서 UPDATE로 만든다. 참조 테이블에는 OOS garbage가 없다. 원래 테이블과 join해 행 수와 값이 같은지 확인한다. 미커밋 UPDATE·INSERT는 없어야 한다.
7. 참조 테이블의 `Oos_num_recs`(`SHOW HEAP OOS`)가 vacuum이 도달해야 할 값이다. 로그를 더 써서 vacuum이 마지막 로그 블록까지 처리하게 하고, 원래 테이블의 `Oos_num_recs`가 그 값으로 내려오는지 본다.
8. 서버를 정상 종료하고 `cubrid checkdb -S`를 실행한다.

```sh
oos_crash_recovery.sh <전용 DB 이름> <결과 디렉터리>
```

## Remarks

### Test Plan

| 검사 | 결과 |
| --- | --- |
| 빌드와 설치(debug) | 성공 |
| `RV_fun[]` 순서, `libcubrid.so` | PASS. 144개 항목, `RV_LAST_LOGID` 143, 불일치 0 |
| `RV_fun[]` 순서, `libcubridsa.so` | PASS. 같은 결과. 두 라이브러리 모두 rebase 전후에 검사 |
| 설정한 CTest(`ctest --test-dir <build> --output-on-failure`) | 66/66 통과. rebase 전 `9b366302dc` 384초, rebase 뒤 `1d86f1d31b` 335초 |
| 강제 종료 후 복구 | PASS. 데이터 일치, vacuum 회수, `checkdb -S` 종료 코드 0 |
| HA 복제 smoke test | 하지 않음 |

변경 후 140~143의 이름은 `RVOOS_NOTIFY_VACUUM`, `RVREPL_DUMMY_OOS_RECORD`, `RVOOS_RECLAIM_POSTPONE`, `RVOOS_UPDATE_DROP_POSTPONE`이다.

### 강제 종료 후 복구 결과

`cub_master`는 `kill -9`로 끝난 서버를 1초 안에 스스로 다시 시작했다(`auto_restart_server`). 스크립트는 이 재시작을 받아들이고, 재시작이 없을 때만 직접 시작한다. 재시작 복구는 REDO 6,479개 로그 레코드, UNDO 6개 트랜잭션으로 끝났다.

| 측정 | `t_upd` | `t_del` |
| --- | --- | --- |
| 적재 후 `Oos_num_recs` | 400 | 400 |
| 강제 종료 직전 | 800 | 400 |
| 같은 데이터의 참조 테이블(garbage 없음) | 400 | 200 |
| 재시작 후 첫 확인(약 7초 뒤) | 400 | 200 |
| 행 수와 값 비교 | 200행 모두 일치 | 100행 모두 일치 |

`t_upd`가 800이 되는 이유가 있다. #8559 이전에는 UPDATE가 바뀌지 않은 `w` 컬럼의 OOS 값도 새로 쓴다. 그래서 200행 UPDATE가 새 chain 400개를 만들고 옛 chain 400개를 남긴다. 오래된 snapshot을 잡은 세션 때문에 vacuum은 종료 전에 이것을 회수하지 못했다.

회수가 `RVOOS_NOTIFY_VACUUM` 경로로 일어났는지는 `cubrid diagdb -d 8`로 로그를 덤프해 확인했다. 덤프는 레코드의 recovery index를 `RV_fun[]` 이름으로 출력하므로, 140으로 기록된 레코드가 `RVOOS_NOTIFY_VACUUM`으로 읽히는 것도 함께 확인된다.

- 강제 종료 전: UPDATE commit의 postpone이 `RVOOS_NOTIFY_VACUUM` 200개를 기록했다.
- 재시작(`LOG_DUMMY_CRASH_RECOVERY`) 뒤: `RVOOS_DELETE` 700개, `RVOOS_RECLAIM_POSTPONE` 200개.
- `RVOOS_RECLAIM_POSTPONE` 200개는 삭제된 `t_del` 100행과 filler 100행이다. 이 행들의 chain은 300개다. 나머지 `RVOOS_DELETE` 400개는 `t_upd`의 옛 chain이고, 이를 지우는 경로는 vacuum의 `RVOOS_NOTIFY_VACUUM` 소비자뿐이다.

`diagdb -d 8`은 대화형으로 묻는다. 표준 입력에 `1`, `-1`, `-1`, `-1`, `y`를 차례로 주어야 한다. `/dev/null`을 주면 질문을 무한히 반복해 출력한다.

검사 스크립트를 처음 만들 때 고친 점도 남긴다. `rpad` 값은 압축되어 OOS로 가지 않았다. `SHOW HEAP OOS`는 미커밋 세션이 잡은 테이블 잠금을 기다린다. md5 380개를 이은 WHERE 조건은 csql에서 10분 넘게 끝나지 않아 참조 테이블 join으로 바꿨다. 이 마지막 현상은 이 변경과 관계없는 csql 처리 비용이며, base 빌드에서 같은지 확인하지 않았다.

### 하지 않은 검증

HA 복제는 master와 slave 두 인스턴스, heartbeat, copylogdb와 applylogdb가 필요하다. 복제 로그는 HA가 켜진 서버만 기록한다. 이 변경에서 `RVREPL_OOS_INSERT`(139)는 번호가 그대로이고, `RVREPL_DUMMY_OOS_RECORD`(142 → 141)는 `replication.c`, `log_applier.c`, `log_manager.c`가 모두 이름으로 처리한다. 그래서 같은 빌드끼리의 복제는 영향을 받지 않는다고 판단했다[추론]. 서로 다른 빌드 사이의 복제 로그 호환성은 보장하지 않는다. 이전 `feature/oos-merge` 빌드의 DB와 로그는 다시 만들어야 한다.

release 빌드는 PR CI(`gha-ci: build (release)`)에서 확인한다.
