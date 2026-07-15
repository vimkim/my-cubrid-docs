# CBRD-27074: csql SA 모드 PL 시작의 고정 지연 제거

https://jira.cubrid.org/browse/CBRD-27074

## Purpose

`csql -S`는 `SA`(standalone mode - DB 서버 기능을 `csql` 프로세스 안에서 실행하는 모드)로 DB를 연다. 저장 프로시저를 사용할 수 있도록 별도 `cub_pl` 자식도 만들고, 그 안에서 JVM을 시작한다.

현재 흐름은 실제 준비 상태를 확인하기 전후에 1초씩 고정 대기한다. Linux `cub_pl`도 DB 부모가 끝났는지 1초마다 확인한다. 각 대기는 과거 PL lifecycle 문제를 막기 위해 추가됐지만, 현재 코드에는 같은 조건을 직접 확인할 수 있는 PID, info file, ping, parent-child 관계가 있다.

| 구분 | 동작 |
|---|---|
| **AS-IS** | 이전 PL 확인 실패 뒤 1초, 새 `cub_pl` 생성 뒤 1초를 기다린다. cold PL 함수 실행은 약 2.51초가 걸린다. Linux 자식의 부모 종료 감지도 최대 1초 늦다. |
| **TO-BE** | 현재 자식의 endpoint가 연결 가능한 즉시 진행한다. Linux에서는 커널이 부모 종료를 자식에 알린다. cold PL 함수 실행은 0.50-0.55초 범위로 줄고, 부모 종료 뒤 자식이 즉시 정리된다. |

목표는 단순히 `sleep(1)`을 지우는 것이 아니다. sleep이 대신하던 세 조건을 직접 표현해야 한다.

1. 이전 SA 실행의 PL이 아직 종료 중인지 확인한다.
2. 새로 만든 PL이 자신의 endpoint를 공개하고 ping에 응답할 때까지 기다린다.
3. Linux PL 자식이 DB 부모보다 오래 남지 않게 한다.

SQL 문법, 저장 프로시저 API, 설정 기본값, wire protocol, 디스크 형식은 바꾸지 않는다. JVM 시작 실패를 dummy(실제 JVM 없이 비정상 상태만 유지하는) PL 상태로 두는 기존 정책도 범위 밖이다.

## Implementation

### 기존 지연 경로

```text
csql -S
  |
  | server_monitor_task::do_check_state(STOPPED)
  |   `- do_check_connection(1)
  |        |- 이전 연결 주소 ping 실패
  |        `- 1초 sleep                         [고정 지연 1]
  |
  | server_monitor_task::do_monitor()
  |   |- fork cub_pl
  |   `- 부모 1초 sleep                         [고정 지연 2]
  |
  `- PL info 확인 -> ping -> bootstrap -> SQL 실행

cub_pl
  `- 최초 PPID와 현재 PPID 비교
       `- 1초 sleep 후 반복                     [종료 감지 지연]
```

JVM은 테스트 호스트에서 약 0.39초에 준비됐다. 부모는 그보다 빨리 준비되더라도 post-fork sleep이 끝날 때까지 진행할 수 없었다.

이 동작은 다음 이슈가 순서대로 보완되며 만들어졌다.

| 이슈 | 당시 해결한 문제 | 이번 변경에서 지키는 조건 |
|---|---|---|
| CBRD-25660 | PL 서버를 DB 서버와 함께 시작하고 종료 | PL 자식은 DB 부모에 종속된다. |
| CBRD-25712 | JVM 반복 시작 실패를 abnormal/dummy PL로 표현 | fork 성공과 JVM 준비 실패를 구분한다. |
| CBRD-25796 | 큰 메모리 할당 뒤 `fork()` 실패 | PL 생성 시점과 fork failure state를 유지한다. |
| CBRD-25908 | 실행 중인 DB의 PL을 SA utility가 종료 | server-owned PL과 SA-owned PL을 혼동하지 않는다. |
| CBRD-25925 | 이전 SA PL 종료 중 새 PL 연결 실패 | stale PL을 확인하되 정상 cold start를 막지 않는다. |
| CBRD-25931 | WSL에서 PPID가 1이 아닌 값으로 바뀌는 경우 | 최초 부모가 사라지면 PL이 종료된다. |

### 준비 상태를 직접 확인

`src/sp/pl_sr.cpp`의 `do_check_connection()`을 횟수 기반 polling에서 deadline(절대 종료 시각) 기반 polling으로 바꾼다.

```text
10ms -> 20ms -> 40ms -> 80ms -> 160ms -> 320ms -> 500ms -> 500ms ...
                                                        전체 최대 10초
```

각 반복은 다음 순서로 동작한다.

```text
PL_SERVER_INFO를 sentinel 값으로 초기화
  `- info file 읽기
       |- 읽기 실패 또는 disabled PID -> retry
       |- 새 child PID와 다른 PID      -> retry
       `- 현재 PID의 연결 주소
            `- connection pool 생성/갱신
                 |- ping 성공          -> 즉시 완료
                 |- child 종료         -> 즉시 실패
                 `- deadline 안         -> backoff 후 retry
```

PID와 port를 같은 `PL_SERVER_INFO` snapshot(한 번에 읽은 값 묶음)에서 읽는다. `UDS`(Unix domain socket) 또는 TCP mode를 사용할 수 있고, TCP는 PL 시작 때 random port를 선택할 수 있다. 이전 PID가 남긴 port를 새 자식의 연결 주소로 받아들이면 안 되며, `pl_info.pid == m_pid` 조건이 이 혼동을 막는다.

기존에는 1초 간격으로 최대 열 번 확인했다. 새 구현도 총 준비 제한은 10초로 유지한다. 실패 정책은 바꾸지 않고 성공한 시작만 실제 준비 시점에 맞춰 빨라진다.

SA의 첫 stale-process 확인은 timeout 0으로 호출한다. info와 ping을 한 번 확인하지만 실패 뒤 sleep하지 않는다. 이전 PL이 실제로 응답하면 기존 state machine이 처리하고, 일반 cold start는 곧바로 자식을 만든다.

### Linux 부모 종료를 kernel event로 처리

`src/base/process_util.h`와 `src/base/process_util.c`의 `create_child_process()`에 Linux parent-death option을 추가한다. 현재 호출자는 PL monitor 하나뿐이며, 이 호출만 option을 켠다.

```text
DB 부모: parent PID 저장
  `- fork()
       `- 자식
            |- prctl(PR_SET_PDEATHSIG, SIGKILL)
            |- getppid()가 저장한 parent PID와 다른지 확인
            `- exec cub_pl
```

Linux는 `PR_SET_PDEATHSIG`를 설정하기 전에 부모가 끝난 경우 신호를 나중에 보내지 않는다. 그래서 child는 설정 직후 PPID를 다시 확인하고, 이미 바뀌었다면 `exec` 전에 끝난다. 설정은 일반 `execve()`를 통과해 유지되므로 `cub_pl` main이 시작된 뒤에도 유효하다.

신호는 `SIGKILL`을 사용한다. PL 자식이 DB 부모보다 오래 남지 않는 조건을 확실히 지키기 위해서다. 기존 `SIGTERM` handler는 info file의 PID가 달라졌을 때 종료하지 않을 수 있다. 기존 PPID-change 경로도 JVM shutdown을 수행하지 않고 `main()`에서 나갔으므로, parent-loss 상황의 graceful cleanup 보장을 제거하는 변경은 아니다.

Linux `cub_pl`은 PPID polling 대신 `pause()`로 대기한다. 부모가 끝나면 커널이 프로세스를 종료하므로 1초마다 깨어날 필요가 없다.

Linux의 parent는 process 전체가 아니라 `fork()`를 호출한 thread라는 점을 주의해야 한다. SERVER mode는 `server_manager::start()`에서 전용 `pl-monitor` daemon thread를 한 번 만들고, 정상적으로는 `server_manager` teardown 때 없앤다. SA mode는 main execution thread가 utility 수명을 소유한다. 향후 server process를 유지한 채 monitor daemon thread를 교체하는 구조가 생기면 PL parent association도 함께 바꿔야 한다.

### 플랫폼별 동작

| 플랫폼 | 부모 종료 처리 |
|---|---|
| Linux/WSL | child가 `exec` 전에 `PR_SET_PDEATHSIG(SIGKILL)` 설정, main은 `pause()` |
| Windows | 기존 parent process handle 대기 유지, `OpenProcess` 또는 wait 실패 시 loop 종료 |
| 비 Linux Unix | 기존 initial PPID 비교와 1초 polling을 fallback으로 유지 |

### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `src/base/process_util.h` | child 생성 API에 parent-death option 추가 |
| `src/base/process_util.c` | Linux child의 `prctl`, fork/prctl race check 구현 |
| `src/sp/pl_sr.cpp` | post-fork sleep 제거, SA immediate probe, readiness backoff와 PID 검증 구현 |
| `src/executables/pl.cpp` | Linux PPID polling을 `pause()`로 변경, Windows wait error 처리 보완 |

## Remarks

### 호환성과 실패 동작

- JVM library를 읽지 못한 child가 abnormal/dummy PL로 남는 CBRD-25712 정책은 그대로다.
- monitor는 child가 polling 중 종료되면 즉시 반환하며, 이후 retry/failure state는 기존 state machine이 결정한다.
- UDS와 TCP 연결 주소를 모두 같은 snapshot 검증 흐름으로 처리한다.
- Linux 외 Unix의 1초 lifetime polling은 이번 범위에서 제거하지 않는다.
- `PR_SET_PDEATHSIG`는 setuid/setgid/capability 변경 exec에서 초기화될 수 있지만 `cub_pl`은 해당 실행 파일이 아니다.
- creating thread가 `fork()` 직후, `prctl()` 전에 끝나고 DB process는 계속 사는 매우 좁은 경우는 `getppid()`로 찾을 수 없다. 현재 persistent monitor thread 구조에서는 관찰되지 않았다.

### Test Plan

| 검증 | 결과 |
|---|---|
| Linux debug GCC에서 SA/CS/SERVER, `cub_pl`, Java PL build | 통과 |
| UDS cold PL 함수 10회 | 0.50-0.55초, 평균 0.527초, 모두 42 반환 |
| `SELECT 1` 뒤 PL 함수 실행 30쌍 | 60개 명령 통과, 잔여 `cub_pl` 없음 |
| TCP random-port SA 실행 10회 | 모두 통과, `AF_INET` 연결 trace 확인 |
| `cubrid pl restart` | PL PID 교체, 함수 실행 통과 |
| 정상 server stop | 반환 시 PL child 없음 |
| server `SIGKILL` | 이전 PL child 12ms 안에 종료, server/PL 자동 복구 뒤 함수 실행 통과 |
| invalid JVM, 15초 external timeout | dummy PL 잔여 없음, 다음 정상 실행 통과 |
| CTP CBRD-25908 | 1/1 통과 |
| formatter, whitespace, build-test smoke gate | 통과 |

`strace`에서는 다음 순서를 확인했다.

```text
child:  prctl(PR_SET_PDEATHSIG, SIGKILL) = 0
child:  execve(.../cub_pl, ["cub_pl", "testdb"], ...)
child:  pause()
parent: exited with 0
child:  killed by SIGKILL
```

trace 기준으로 parent exit와 PL main의 `SIGKILL` 종료 차이는 약 7.2ms였다. 변경한 Linux 경로에는 1초 sleep이 남지 않았다.

### 리뷰 포인트

1. parent-loss 신호로 `SIGKILL`을 선택한 것이 PL ownership 규칙에 맞는지 확인한다.
2. SERVER mode에서 child를 만든 monitor thread가 DB 수명 동안 유지되는지 확인한다.
3. fork와 `prctl` 사이 process-exit race check가 child에서 `exec` 전에 실행되는지 확인한다.
4. PID와 연결 주소를 같은 snapshot으로 검증해 UDS/TCP stale info를 차단하는지 확인한다.
5. readiness의 총 10초 제한과 기존 abnormal/dummy PL 정책이 유지되는지 확인한다.

전체 조사 기록과 원시 측정 요약은 변경 branch의 `CSQL_SA_PL_STARTUP_REPORT.md`에 함께 둔다. Windows runtime과 CUBRID CI는 PR 단계에서 추가 확인이 필요하다.
