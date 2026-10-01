# CBRD-27443: 시작 명령 종료와 백그라운드 프로세스의 FD 수명 분리

## Conclusion

`cubrid server start`의 반환과 호출 도구의 출력 수집 완료는 서로 다른 사건이다. 백그라운드 프로세스가 호출자의 파이프 쓰기 FD(파일 디스크립터)를 보유하면, 시작 명령이 종료 코드 0 또는 1로 끝나도 호출 도구는 EOF를 받지 못한다. 로그를 계속 출력해야 발생하는 문제가 아니다.

수정 대상은 서버 한 곳의 잠금 FD가 아니라 **master·서버·PL 생성 및 재기동 경계의 자원 인계**다. 일반 상속 FD 정리와 표준 입출력 전환을 함께 설계해야 한다. 이번 작업은 분석과 문서 개정이며 엔진 수정본을 구현하거나 검증한 작업은 아니다.

## Evidence Basis

| 구분 | 기준과 검증 범위 |
|---|---|
| 검토 댓글 | Joon Min, 2026-09-23, [댓글 4776522](http://jira.cubrid.org/browse/CBRD-27443?focusedCommentId=4776522&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-4776522). 2026-10-01 조회본은 [별도 보존](evidence/comment-4776522.md)한다. |
| 소스 분석 | develop 및 작업 브랜치 HEAD `c63a3b993be552ef6ad3ce244c386d5081147958` |
| 댓글의 실측 | 댓글 작성자가 위 develop/debug에서 수행했다고 보고한 일반 시작, 파이프, single-node HA 재기동 시험. 원시 실행 로그는 댓글에 첨부되어 있지 않다. |
| 이번 독립 실측 | 설치 바이너리 버전 `11.5.0.2602-a0026f9`, Linux debug. `a0026f9293523bed2af4c52d8c7299c6ce9b14d0`에 해당하는 버전 표기이며, `c63a3b993` 재빌드 시험으로 간주하지 않는다. |
| 버전 간 연결 | 생성 경로 7개 파일의 diff는 `util_service.c` 관리 명령 목록에 `upgradedb` 한 줄을 추가한 것뿐이다. 비교 대상 밖의 엔진 전체가 같다는 뜻은 아니다. [diff](evidence/spawn-path-source-comparison.patch), [환경·바이너리 해시](evidence/environment.json) |
| 이전 자료 | `my-cubrid-jira/issues/CBRD-27443-inherited-fd_38093ea_codex.md`. feat/oos의 이전 재현과 이번 develop 계열 결과를 섞지 않는다. 기존 파일의 미커밋 Q&A 변경도 보존한다. |

## Review Corrections

| 기존 설명 | 댓글 및 재검토 결과 | 문서에 반영할 수정 |
|---|---|---|
| master에는 정리 코드가 있으므로 서버·PL만 누락됐다 | 서비스 실행부가 `NO_DAEMON`을 설정해 master의 정리 함수를 건너뛴다 | 정리 함수의 존재와 실제 실행 경로를 구별한다 |
| 출력 파이프 대기는 아직 가능한 설명이다 | 댓글에 재현 보고가 있고 이번 독립 시험에서도 stdout·stderr EOF 부재를 확인했다 | 일반 FD 잠금과 함께 핵심 결함으로 다룬다 |
| master가 부모인 재기동은 호출 셸 FD 시험과 조건이 다르다 | 부모는 다르지만 master가 원래 FD를 보유하면 같은 참조가 재전달된다 | 최초 생성부터 재기동까지 자원 계보를 추적한다 |
| FD 3 이상을 닫는 master 방식을 재사용하면 된다 | 직접 실행한 daemon master도 FD 1·2를 남긴다 | 표준 입출력 처리를 수정 범위에 포함한다 |
| stop이 hang하므로 stop에서도 같은 유출이 있다 | 댓글은 stop 파이프의 정상 종료를 보고했다. 이번 독립 시험에서도 stop 명령은 0으로 종료했다 | 이전 start 출력/잠금 대기와 stop 본체 실행을 별도로 관측한다 |
| 모든 사례가 같은 원인의 무한 대기다 | 서버 등록 대기·복구·호출자 잠금·출력 수집이 서로 다르다 | 사용자 경험 전체를 FD 결함 하나로 단정하지 않는다 |
| SCM_RIGHTS 전달 때문에 exec 전 FD를 보존해야 한다 | 실행 중 소켓 전달과 fork/exec 상속은 다른 경계다 | 실제 exec 인계 계약을 따로 조사해 보존 목록을 정한다 |

## Failure Model

### 종료 코드와 EOF의 독립성

```text
호출 도구 ── 실행 ──> cubrid server start DB
    ^                       |
    | stdout/stderr         +─> cub_master (필요할 때 생성)
    | 파이프                +─> cub_server ──> cub_pl
    +--------------------------- 각 프로세스가 쓰기 FD를 상속

시작 명령 종료: waitpid로 코드 확인 가능
출력 수집 완료: 같은 파이프의 모든 쓰기 FD가 닫히고 남은 데이터를 읽어야 EOF
```

`waitpid()`는 자식 종료 상태를 알려주며, `read()`의 EOF는 파이프 쓰기 참조가 사라졌음을 알려준다. EOF가 성공을 뜻하지도 않고, 종료 코드가 출력 수집 완료를 뜻하지도 않는다. 따라서 호출 도구가 두 조건을 모두 기다리는 것은 정상적인 동작이다. [wait(2)](https://man7.org/linux/man-pages/man2/wait.2.html), [pipe(7)](https://man7.org/linux/man-pages/man7/pipe.7.html)

`fork()`는 같은 열린 파일 상태를 참조하는 FD를 자식에게 복사한다. `exec` 때 `FD_CLOEXEC`가 설정된 FD만 자동으로 닫힌다. 프로세스 종료는 자기 FD만 닫으므로 살아 있는 다른 프로세스의 복사본에는 영향을 주지 않는다. [fork(2)](https://man7.org/linux/man-pages/man2/fork.2.html), [execve(2)](https://man7.org/linux/man-pages/man2/execve.2.html)

`flock`도 같은 열린 파일 상태에 연결된다. 이번 시험은 명시적인 `LOCK_UN` 없이 호출자가 FD를 닫는 조건이므로, 상속한 복사본이 남으면 잠금이 유지된다. 자식이 `LOCK_UN`을 실행하는 방식은 호출자의 잠금까지 해제할 수 있어 해결책으로 사용해서는 안 된다. 자식에게 불필요한 참조를 닫는 것이 필요한 동작이다. [flock(2)](https://man7.org/linux/man-pages/man2/flock.2.html)

### 측정해야 할 세 종류의 대기

| 관측 | 가능한 대기 위치 | 이번 결함과의 관계 |
|---|---|---|
| 명령을 실행하기 전 잠금 획득 실패 | 호출 래퍼의 `flock` | 이전 start가 남긴 FD에 의해 발생할 수 있다 |
| 시작 명령 PID가 여전히 살아 있음 | master 기동, DB 복구, 서버 등록 확인 | EOF 유출과 별도로 진단한다 |
| 시작 명령 PID는 종료했지만 reader가 기다림 | stdout/stderr의 EOF | 이번 독립 시험이 직접 확인한 상태다 |

사용자의 “보통 3초, 1분 이상 대기”는 관측 경험이다. 3초를 모든 DB 복구에 적용할 제품 SLA로 바꾸지 않는다. 수정본 시험에서는 명령 종료 시각과 EOF 시각의 차이를 기록하고, DB가 계속 실행되는 동안 EOF가 오는지를 확인한다.

## Source Analysis

아래 위치와 링크는 모두 `c63a3b993be552ef6ad3ce244c386d5081147958` 기준이다.

### 최초 실행과 master의 우회 경로

```text
process_server(START)                       util_service.c:1727
  +─ master가 없으면 process_master(START)
  |    +─ envvar_set("NO_DAEMON", "true")    :1017
  |    +─ proc_execute(... false,false,false)
  |         +─ fork / execv(cub_master)       :891 / :911
  |              +─ NO_DAEMON 존재           master.c:1313
  |              |    -> css_daemon_start 생략
  |              +─ 일반/HA 재기동의 부모
  +─ proc_execute(cub_server, ..., &pid)      util_service.c:1778
       +─ fork / execv
            +─ setsid()                     server.c:322
            +─ net_server_start()           server.c:325
                 +─ boot_restart_server()
                      +─ pl_server_init()   boot_sr.c:2248
                           +─ pl-monitor 작업
                                +─ create_child_process(cub_pl)
                                     -> fork / execv
```

[`proc_execute_internal()`](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/util_service.c#L868)는 `close_output`·`close_err`가 참일 때 해당 표준 FD만 닫는다. master와 서버 호출부는 둘 다 거짓을 전달하고, 일반 FD 정리도 없다. `envvar_set`의 실제 환경변수 접두사는 `CUBRID_`이므로 코드의 `NO_DAEMON`은 `CUBRID_NO_DAEMON`으로 전달된다.

[`css_daemon_start()`](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/master.c#L1589)는 별도 fork와 세션 분리 후 FD 3부터 `css_get_max_socket_fds()` 미만까지 닫는다. 하지만 [서비스 명령으로 생성한 master](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/master.c#L1313)는 함수 전체를 건너뛴다. 직접 daemon 모드로 실행해도 0·1·2는 명시적으로 남긴다. 두 경로는 각각 다른 이유로 호출자 파이프를 유지한다.

### 시작 결과를 알리는 주체

[`process_server()`](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/util_service.c#L1775)는 fork 성공만 보고 성공을 출력하지 않는다. `is_server_running()`이 master에 `commdb`로 등록 상태를 조회한 뒤 `print_result()`를 실행한다. 그러므로 백그라운드 서버의 stdout을 유지하는 것이 시작 결과 전달의 필수 조건은 아니다.

다만 [서버 진입부](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/server.c#L305)는 복구 안내를 stdout에 출력하고, [초기화 오류 경로](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/communication/network_sr.c#L1066)는 stderr에도 진단을 출력한다. 이를 무조건 `/dev/null`로 버리는 변경은 실패 원인 진단을 약화시킨다. 성공·실패 요약은 시작 명령이 유지하고, 서버의 초기 오류가 남을 위치와 호출자에게 알릴 방법을 함께 정해야 한다.

[`is_server_running()`](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/util_service.c#L1570)는 자식 PID가 살아 있으나 등록되지 않은 동안 반복하며 자체 시간 상한이 없다. master 시작에는 180회, 회당 1초의 대기 구조가 있다(`:1009`). 이 차이는 별도 대기 원인 후보이지 이번 EOF 실측의 원인이 아니다. 또한 등록 확인을 SQL 및 모든 PL 초기화의 완전한 준비 보증으로 확대해서는 안 된다.

### PL이 서버 내부 FD까지 받는 이유

[`server_manager::start()`](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/sp/pl_sr.cpp#L262)는 SERVER_MODE에서 모니터 작업을 별도 스레드로 시작한다. [`do_monitor()`](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/sp/pl_sr.cpp#L356)는 표준 입출력 파일 인수를 모두 `nullptr`로 주어 [`create_child_process()`](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/base/process_util.c#L262)를 호출한다. 이 도우미는 지정된 입출력만 바꾸며 다른 FD를 제거하지 않는다.

`boot_sr.c:2232`의 주석과 호출 순서는 PL 초기화를 `log_initialize()`보다 먼저 요청한다. 그러나 SERVER_MODE에서는 요청 시점과 모니터 스레드의 실제 fork 시점이 같지 않다. 따라서 호출 위치가 앞이라는 사실만으로 로그 볼륨 FD가 전달되지 않는다고 결론 내릴 수 없다. 이번 `/proc` 관측에서도 PL이 서버 오류 로그와 `fdtest_lgat`를 보유했다. FD 번호가 서버와 PL에서 다를 수 있으므로 번호만 대조하지 않고 대상을 기록했다. 이 관측은 유지 사실을 입증하며 각 파일의 정확한 open/dup 이력까지 추적한 것은 아니다.

PL 재시작은 이미 많은 파일을 연 서버에서 실행되므로 시작 순서 조정만으로 내부 FD 전파를 막을 수도 없다. SA_MODE에서는 같은 모듈이 동기 초기화 경로를 사용하므로, 서버 모드 수정으로 SA 동작까지 검증했다고 주장하지 않는다.

### master에서 다시 전달되는 경로

| 경로 | 소스 근거 | 판정 |
|---|---|---|
| 일반 서버 자동 재기동 | [master_server_monitor.cpp:262](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/master_server_monitor.cpp#L262) | 자식에서 바로 execv한다. 이번 일반 재기동 실측으로 재전파를 확인했다 |
| HA 프로세스 재기동 | [master_heartbeat.c:3137](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/master_heartbeat.c#L3137) | 일반 FD 정리 없이 execv한다. single-node HA는 댓글의 실측 근거다 |
| master가 관리 유틸리티 실행 | [master_heartbeat.c:6678](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/master_heartbeat.c#L6678) | 별도 fork/exec 경계도 검토해야 한다 |
| log copy/apply 직접 실행 | [util_service.c:3317](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/util_service.c#L3317), [:3598](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/util_service.c#L3598) | 같은 도우미로 FD가 전달된다. 2-node에서 최종 유지 여부와 수정본 정상 동작은 미실측이다 |

master가 최초 호출자 FD를 놓더라도 이후 자신이 연 내부 FD는 다시 생긴다. 따라서 master 진입점 정리만으로 모든 재기동의 FD 격리가 완성되는 것은 아니다.

### 실행 중 소켓 전달과 exec 인계

[`tcp.c:1095`](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/connection/tcp.c#L1095)의 `SCM_RIGHTS`는 실행 중인 프로세스 간 메시지로 FD를 전달하는 방식이다. exec 전 정리가 이 미래의 전달 자체를 없애지는 않는다. master 접속 소켓도 서버 실행 후 [연결 절차](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/connection/master_connector.cpp#L760)에서 만들어진다.

반면 실행 준비용 오류 통지 파이프나 실제로 exec를 넘겨야 하는 FD가 있다면 보존해야 한다. 보존 목록의 근거는 해당 생성 경계의 계약이어야 하며, 다른 곳에 `sendmsg`가 있다는 이유로 모든 FD를 남겨서는 안 된다. master 리슨 소켓에는 이미 close-on-exec 처리가 있다([tcp.c:730](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/connection/tcp.c#L730)). 이를 모든 내부 파일에도 적용됐다는 근거로 확대하지 않는다.

### 공통 도우미의 wait 인수만으로 분류할 수 없는 이유

`wait_child=false`인 서버·master·HA 도구는 직접적인 분리 대상이다. 그러나 [`cubrid broker start`](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/executables/util_service.c#L1970)는 `wait_child=true`로 관리 명령을 실행하고, 그 관리 명령이 다시 장수 프로세스를 만든다([broker_admin_pub.c:3158](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/broker/broker_admin_pub.c#L3158)). 동기 실행 여부는 자손까지 포함한 수명 정책이 아니다.

broker 내부 CAS 생성에는 FD 3 이상 정리가 이미 있다([broker.c:1552](https://github.com/CUBRID/cubrid/blob/c63a3b993be552ef6ad3ce244c386d5081147958/src/broker/broker.c#L1552)). 최초 실행과 내부 재시작을 동일하게 분류하면 안 된다. 이번 broker 경로는 소스 조사만 수행했으며 재현을 주장하지 않는다.

## Independent Measurements

[실행 스크립트](evidence/run-probe.sh)는 별도 user·PID·network·mount namespace, private `/tmp`, 별도 `$CUBRID` 설정·DB 목록·로그를 사용한다. 호스트 master에는 종료 신호를 보내지 않는다. 프로세스 종료 감지와 두 출력 파이프 drain을 독립적으로 수행하고, 잠금 FD만 명시적으로 상속시킨다. Python의 기본 `close_fds`가 시험용 잠금을 없애지 않도록 `pass_fds`를 지정했다.

최초 관측창은 명령 종료 후 2초다. 이는 EOF 부재를 표본화하기 위한 시험값이며 제품의 허용 지연을 정한 것이 아니다. 이후 서버 또는 서비스 종료와 EOF/잠금 해제를 대조했다. 아래 수치는 각각 1회 실행 결과이며 성능 통계가 아니다.

| 조건 | 시작 명령 종료 | 종료 후 stdout / stderr EOF | 호출자 잠금 획득 | 서버만 종료한 뒤 |
|---|---|---|---|---|
| master 없음 | 0 / 3.107초 | 없음 / 없음 | 실패 | master가 세 자원을 계속 유지 |
| master 미리 실행 | 0 / 2.106초 | 없음 / 없음 | 실패 | EOF 둘 다 수신, 잠금 획득 성공 |
| master 없음 + 존재하지 않는 DB | 1 / 2.105초 | 없음 / 없음 | 실패 | DB 서버가 없어도 master가 유지 |
| `cub_master` 직접 daemon 실행 | 0 / 0.101초 | 없음 / 없음 | 성공 | 일반 FD 정리와 파이프 처리가 다름을 보여줌 |
| master 없음 + 일반 서버 강제 종료 후 자동 재기동 | 최초 0 / 3.108초 | 재기동 후에도 없음 / 없음 | 재기동 후에도 실패 | master가 계속 유지 |

다섯 시험 모두 전용 인스턴스의 `service stop` 뒤에는 EOF 둘 다 수신하고 잠금을 획득했다. 정상 DB 생성·삭제 및 종료 명령의 반환도 JSON에 기록했다. 직접 master 실행의 0은 daemon화 부모의 종료 코드이며 master 준비 완료 확인과 동일하지 않다.

이슈 본문의 간단 재현 코드도 같은 격리 환경에서 실행해 종료 코드 0, 서버 stop 뒤 EOF 부재, service stop 뒤 EOF 수신을 확인했다. [실행 출력](evidence/issue-repro.txt)을 보존한다.

원시 결과: [absent](evidence/absent.json), [present](evidence/present.json), [missingdb](evidence/missingdb.json), [direct-master](evidence/direct-master.json), [revive](evidence/revive.json).

`absent`에서 같은 stdout 파이프 `pipe:[420134347]`와 stderr 파이프 `pipe:[420134348]`를 namespace PID 26(master), 29(server), 32(PL)가 보유했다. 서버를 종료한 뒤 PID 26만 남아 두 파이프와 잠금을 유지했다. stderr 출력은 빈 문자열이었는데도 EOF가 오지 않았다.

`revive`에서는 서버 PID 29를 종료한 뒤 PID 276이 생성됐고, PL은 PID 278이었다. 새 프로세스에도 원래 파이프와 잠금이 남았다. 새 서버·PL에서 master 오류 로그까지 보인 점은 내부 FD도 재기동 경계를 넘는다는 추가 관측이다. PID와 파이프 번호는 해당 실행 안에서만 의미가 있다.

### 재실행

Linux에서 user namespace, `unshare`, `mount`, `ip`, Python 3 및 동작하는 CUBRID 설치가 필요하다. 아래 `CUBRID_INSTALL`은 시험할 설치 경로로 지정한다. 스크립트와 결과 경로는 private mount로 가려지는 `/tmp` 밖에 둔다.

```bash
export CUBRID_INSTALL=/absolute/path/to/cubrid-install
cd my-cubrid-docs/cbrd-27443/evidence
bash run-probe.sh "$CUBRID_INSTALL" "$PWD/results" absent
bash run-probe.sh "$CUBRID_INSTALL" "$PWD/results" present
bash run-probe.sh "$CUBRID_INSTALL" "$PWD/results" missingdb
bash run-probe.sh "$CUBRID_INSTALL" "$PWD/results" direct-master
bash run-probe.sh "$CUBRID_INSTALL" "$PWD/results" revive
```

`run-probe.sh`의 0은 증거 수집 및 정리 성공이지 결함 수정 통과가 아니다. 수정본 판정은 JSON의 EOF·잠금·보유자·명령 결과를 아래 Acceptance Matrix와 대조한다. runtime 디렉터리는 출력된 `$HOME/.cache/cbrd27443-*`에 남으며 DB는 정상 시험 종료 시 삭제한다. 실패한 시험은 namespace 종료로 프로세스를 회수하지만 DB 파일이 남을 수 있다.

초기 환경 점검에서 설정 키를 `master_port_id`로 잘못 지정한 실행은 설정 오류로 실패했다. 올바른 키는 `cubrid_port_id`다. 또 첫 namespace 구성이 고아 프로세스를 수거하지 않아 stop 대기에 영향을 주었다. PID 1 전용 reaper를 추가한 뒤 위 다섯 결과를 수집했다. 이 두 초기 실행은 제품 재현 결과에 포함하지 않는다. [namespace-init.py](evidence/namespace-init.py)는 이러한 시험환경 오류를 방지한다.

## Proposed Implementation

### 합의된 요구와 구현 제안의 구분

사용자는 정상 완료에 “종료 코드 반환”뿐 아니라 출력 수집이 끝나 다음 작업으로 진행할 수 있다는 조건을 포함한다고 확인했다. 또한 “정상 성공 실패를 알리고 난 뒤, 출력 통로를 놓는다”라고 설명했다. 이는 외부 완료 계약이다. 어떤 프로세스가 직접 출력할지, 정확한 로그 목적지와 새 API 형태까지 결정한 것은 아니다.

댓글은 표준 입출력 정책을 이번 수정 범위에 넣도록 요청했다. 그러므로 **파이프 문제를 범위 밖 또는 미재현 후보로 남겨두지 않는다.** 아래 설계는 그 요구를 충족하기 위한 AI 제안이며 최종 구현 합의는 아니다.

### 권장 구조

```text
호출자 전용 stdout/stderr/lock
   |
   +─ 시작 명령: 결과 출력과 반환 코드 소유
         |
         +─ 명시적인 백그라운드 생성 정책
              +─ stdin: 입력 없는 대상으로 연결
              +─ stdout/stderr: 서버 소유 진단 대상으로 연결
              +─ 그 외 FD: 명시적 exec 보존 목록만 남김
              +─ exec 실패: 짧은 오류 전달 경로 + 자식 _exit
              +─ 준비 여부: 기존 master 등록 확인 계약 유지·검증

서버/PL/master 재기동도 동일한 인계 원칙 적용
```

| 우선순위 | 후보 | 장점과 남는 과제 |
|---|---|---|
| 1 | 생성 경계에 명시적인 상속 정책을 두고 서비스별로 선택 | 자식이 exec하기 전에 호출자·부모 내부 FD를 제거한다. 공통 도우미의 동기 명령 동작을 보존할 수 있다. 직접 실행 진입점과 broker 자손은 별도 적용이 필요하다 |
| 2 | 각 daemon 진입점에서 자체 자원을 열기 전에 정리 | 직접 `cub_master`·`cub_server`·`cub_pl` 실행도 포괄한다. 이미 초기화한 로그·메시지 파일을 닫지 않도록 순서를 설계해야 한다 |
| 보완 | 내부 open/socket 시 원자적인 close-on-exec | 서버 로그·볼륨·소켓의 PL 전파를 줄인다. 외부에서 받은 호출자 FD와 이미 상속된 표준 FD를 이것만으로 처리할 수는 없다 |

1과 2를 조합하더라도 정책은 한 곳에서 정의하고 적용 경계를 명시해야 한다. `wait_child`에서 정책을 암묵적으로 추론하거나 모든 호출을 일괄 정리하는 변경은 피한다. 감독자가 출력을 수집하는 명시적 foreground 모드는 별도 계약으로 보존한다. `NO_DAEMON`의 현재 서비스 내부 사용을 곧바로 “사용자가 foreground 상속을 요청함”으로 해석하지 않는다.

### 표준 입출력과 초기 실패

단순 `close(1)`·`close(2)` 대신 새 대상으로 `dup2` 등으로 치환하는 방향을 검토한다. 빈 1·2 번호를 이후 open이 차지하면 로그 출력이 예상하지 않은 파일에 기록될 수 있다. 같은 파이프를 가리키는 FD 1·2 또는 더 높은 번호의 복사본을 모두 놓아야 EOF가 온다. [dup(2)](https://man7.org/linux/man-pages/man2/dup.2.html)

시작 명령은 기존 결과 요약과 성공·실패 코드를 유지한다. 서버의 초기화 실패는 파일이나 전용 진단 채널로 보존하고, 필요하면 시작 명령이 위치 또는 내용을 알려준다. 로그 파일을 열지 못했을 때도 호출자가 실패를 확인할 수 있어야 한다. stderr를 버려 EOF만 맞추는 것은 충분하지 않다.

`create_child_process()`의 현재 stdout/stderr 파일 인수는 `unlink()` 후 `fopen("w")`를 수행한다(`process_util.c:297`, `:324`). 여기에 기존 운영 로그 경로를 그대로 넣으면 재시작 때 이전 로그를 지울 수 있다. 이 인수를 즉시 새 로그 정책으로 재사용하기보다 append·권한·회전·파일 생성 실패 처리를 별도로 정해야 한다.

exec 성공 여부를 알리는 close-on-exec 오류 파이프를 도입하더라도 그 EOF는 **exec 성공**만 의미한다. DB 준비 완료는 기존 등록 확인 또는 별도 준비 프로토콜로 판단해야 한다. 실패 자식은 부모 제어 흐름으로 return하지 않고 제한된 오류 통지 후 `_exit`하도록 검토한다. 현재 도우미들에는 exec 실패 후 return/상위 정리 경로가 있으므로 생성 정책 변경 시 함께 점검할 사항이다.

### 다중 스레드와 이식성

PL 및 master 재기동은 다중 스레드 프로세스에서 fork한다. 자식의 exec 이전에는 async-signal-safe한 동작만 사용해야 하므로, 그 구간에 STL·malloc·stdio·일반 로거·`opendir/readdir`를 새로 넣는 설계는 피한다. 필요한 경로·보존 목록·정리 범위를 부모에서 준비하고, 자식은 FD 조작·exec·제한된 오류 전달만 수행하는 방향으로 검토한다. [fork(2)](https://man7.org/linux/man-pages/man2/fork.2.html)

Linux `close_range()`는 Linux 5.9/glibc 2.34부터 지원하며 `CLOSE_RANGE_CLOEXEC`는 Linux 5.11부터다. 빌드·실행 환경별 fallback과 보존 FD 구간 처리가 필요하다. 단순 루프를 쓰면 큰 FD 한계에서 비용이 커지고, 현재 soft limit만 상한으로 삼으면 limit을 낮추기 전에 연 높은 FD를 놓칠 수 있다. [close_range(2)](https://man7.org/linux/man-pages/man2/close_range.2.html)

부모에서 FD 생성 후 `fcntl(FD_CLOEXEC)`를 뒤늦게 적용하면 다른 스레드의 fork와 경쟁할 수 있으므로, 가능하면 `O_CLOEXEC`·`SOCK_CLOEXEC` 같은 생성 시 설정을 사용한다. 다만 의도적인 exec 전달은 명시적으로 예외 처리해야 한다. [open(2)](https://man7.org/linux/man-pages/man2/open.2.html)

## Acceptance Matrix

아래는 향후 엔진 수정본에 대한 검증 요구다. 이번 문서 작업에서 통과한 회귀 테스트 목록이 아니다.

| 조건 | 판정 기준 | 현재 근거 |
|---|---|---|
| master 없음/있음 + 정상 server start | start 코드 0, 서버 실행 유지, stdout·stderr EOF, 호출자 잠금 획득 | 이번 두 조건 모두 결함 재현 |
| master 없음 + DB 시작 실패 | nonzero와 진단 보존, EOF 수신, 잠금 획득. 살아남은 master도 호출자 자원을 보유하지 않음 | missingdb 독립 재현 |
| master 자체의 시작 실패 | 실패 응답과 EOF, 잔존 자식 및 잠금 없음 | 수정본 검증 필요 |
| 직접 daemon master | daemon 동작 유지, 일반 FD 및 호출자 파이프 분리 | 일반 FD만 해제되는 대조 결과 확보 |
| 일반 자동 서버 재기동 | 새 서버·PL에서 호출자 FD 없음, 등록·SQL·PL 동작 정상 | 이번 재전파 실측, 수정본 기능 검증 필요 |
| PL만 재시작 및 SA PL | 부모 내부 로그·볼륨 FD 미상속, 저장 프로시저 성공, 기존 SA 출력 보존 | 소스상 대상, 독립 기능 시험 미수행 |
| single-node HA 시작·재기동·heartbeat stop | master 포함 잠금·출력 분리, HA 상태 전이 정상 | 댓글의 결함 실측; 이번 재실행 아님 |
| 2-node copylogdb/applylogdb 시작·재시작 | 자원 분리와 실제 복제 진척을 함께 확인 | 양쪽 모두 미실측 |
| stdout만/ stderr만/ `2>&1`/ 높은 번호 복제 FD | 파이프의 모든 쓰기 참조 해제 | 이번에는 stdout·stderr 별도 파이프만 실측 |
| 높은 FD, 낮아진 soft limit, 이미 닫힌 0·1·2 | 정리 누락과 FD 번호 재사용에 의한 오기록 없음 | 수정본 경계값 시험 필요 |
| 동기 관리 유틸리티·foreground 모드 | 출력·리다이렉션·반환 코드 계약 보존 | 변경 시 회귀 검증 필요 |
| 로그 파일 접근 실패·exec 실패 | 오류를 잃지 않고 nonzero 반환, 자식 종료 및 FD 정리 | 수정본 오류 경로 시험 필요 |
| broker/CAS/proxy 최초 실행과 재시작 | 각 생성 경계별 FD 정책 및 클라이언트 접속 정상 | 이번에는 소스 조사만 수행 |

“hang하지 않음”만 검사하면 출력 버림, 부모의 조기 성공 반환, 서버 기동 실패가 모두 통과할 수 있다. 명령 상태·EOF·FD 보유자·DB 기능을 함께 판정한다.

## Separate Follow-ups

`NO_DAEMON` master가 호출자 프로세스 그룹에 남는 문제는 FD 수명과 별도다. 이번 namespace 관측에서도 master의 PGID/SID가 관측자의 그룹과 같고 서버·PL은 별도 세션이었다. 댓글은 timeout의 그룹 신호에 의해 master가 종료되는 실측을 보고했다. 이번에는 timeout 신호 시험을 재실행하지 않았으며, 감독 방식에 따라 신호 전달 범위가 달라진다. `setsid`를 추가해도 EOF 문제는 해결되지 않고 FD 정리를 해도 그룹 신호 문제는 남는다.

등록 대기 루프의 상한, readiness 정의, foreground 서비스 관리자와의 계약은 별도 설계 항목이다. 이번 결함을 해결하기 위해 이 모든 정책 변경을 한 패치에 묶을 필요는 없지만, FD 정책의 적용 모드를 정할 때는 검토해야 한다.

## Open Decisions

합의가 필요한 부분은 서비스별 stdout/stderr의 최종 목적지, 초기 오류의 호출자 전달 방식, 명시적 foreground 예외, 지원 OS별 정리 API다. 표준 입출력 문제를 수정 범위에 포함한다는 요구와, 이 세부 구현 결정이 미정이라는 사실은 함께 유지한다. Windows 동작은 이번 분석·실측에서 검증하지 않았다.
