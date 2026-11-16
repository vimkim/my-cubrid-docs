# PR 8504 로컬 shard 09의 column_name_serial_03.sql cub_cas 크래시 분류

## 결론

- 분류: **로컬 설정이 드러낸 기존 develop 결함**이다. Sidecar 결함이 아니고 JDBC 드라이버 불일치도 아니다.
- 방아쇠: LOG FATAL 조사 때 lf3부터 진단용으로 넣은 `call_stack_dump_on_error=yes`. debug 서버가 vacuum의 -1127 알림 콜스택을 덤프하는 7~11초 동안 서버가 요청을 처리하지 못하고, 그 사이에 보낸 CAS의 `check_cas` ping이 5초 timeout으로 실패한다. CI는 이 설정을 쓰지 않는다.
- 결함: `net_client_ping_server`는 응답을 기다리다 timeout이 나면 큐에 넣은 응답 버퍼(자기 스택 변수)를 빼지 않고 돌아간다. 그 등록은 끝까지 남는다. 16비트 request id가 한 바퀴 돌아 같은 id(6840)가 다시 쓰이면, 그 요청은 이미 사라진 스택 주소로 응답을 받는다. commit 요청이 그 id를 받으면 debug 빌드에서는 그 주소가 `css_net_recv`의 return 주소 자리여서 CAS가 SIGSEGV로 죽는다. 다른 요청이 받으면 `free()` abort나 `-187`로 드러난다.
- 코드: f69816c086과 develop merge base 173d92e454의 해당 코드는 같다. Sidecar PR은 이 코드를 바꾸지 않는다.

## 측정 결과

| 조건 | 결과 |
|---|---|
| head, 진단 설정 켬, 1..122, gdb 감시만 (cc2, cc4, cc5) | 3/3 크래시. 모두 case 122. rid 6840(cc4, cc5에서 측정) |
| head, 진단 설정 켬, case 122만 (cc1) / 120..122 (cc3) | 0/2 |
| head, 진단 설정 끔, 1..122 (cc7, cc10) | 0/2. ping timeout 없음 |
| base 173d92e454, 진단 설정 켬, gdb 감시만 (cc16, cc17) | 0/2. 서버 정지가 `create table` 실행 중에 걸려 ping timeout 없음 |
| base, 진단 설정 켬, 드문 경로 breakpoint (cc8, cc11) | 크래시 0/2. cc11은 ping timeout 발생(rid 6841) |
| base, 진단 설정 끔 (cc12) | 0/1 |
| head, `sidecar_force_external=no`, 진단 설정 켬 (cc9) | 크래시 없음. ping timeout 발생(rid 6841) |
| head, 진단 설정 켬, 1..399, 20M 로그 (cc19, lf4 재현) | NOK 4개: 122(`Error:-187`), 206(CAS abort), 208·211(206이 남긴 `TEST_USER2` 때문) |
| base, 진단 설정 끔, 43번째 ping만 gdb로 timeout 강제 (cc20) | ping은 rid 6840(문장 319). case 122에서 CAS가 `free()` 안에서 abort(gdb 포착, testkit 판정은 OK) |
| head, 같은 강제 (cc21) | cc20과 같음 |

- 측정: lf3, lf4도 진단 설정을 켠 head 실행이었고 둘 다 case 122가 NOK였다. 진단 설정이 없던 lf2(1..399)는 모두 OK였다.
- 측정: CI shard 09(run 43404071059)는 case 122가 OK였다. CI의 CTP `conf/sql.conf`에는 `call_stack_dump_on_error`가 없다.

## 원인

### 1. 서버가 7~11초 멈춘다 (로컬 설정)

- 측정(cc5): 20:45:32.738에 vacuum worker가 `-1127 Delete an empty overflow page`(`i__db_domain_data_type`)를 남기고 콜스택을 덤프했다. 그 뒤 서버 로그는 39.646까지 비어 있다. 그 사이 CAS가 32.742에 보낸 ping은 38.355에 `-186`으로 실패했고 CAS 로그에 `SERVER DOWN`이 남았다.
- 측정(cc7, cc10, cc12): 진단 설정이 없으면 이런 정지가 없고 ping timeout도 없다.
- 추론: debug 서버의 콜스택 덤프가 error log 경로를 7~11초 붙잡고, 로그를 먼저 쓰는 `server_ping`이 그 뒤에서 기다린다.

### 2. timeout 난 ping이 스택 버퍼 등록을 남긴다 (develop 결함)

- 측정(코드): `net_client_ping_server`(network_cl.c)는 `css_send_request_to_server_with_buffer`로 스택 변수 `reply_buf`를 `conn->buffer_queue`에 등록한다. 수신이 실패하면 그 등록을 빼지 않고 반환한다.
- 측정(cc8 bt): `tran_server_commit`마다 부르는 `css_remove_all_unexpected_packets`는 data, request, abort, error 큐만 비우고 `buffer_queue`는 일부러 남긴다(주석: "DO NOT REMOVE THE DATA BUFFERS QUEUED BY THE USER").
- 측정(코드): `css_is_valid_request_id`는 `buffer_queue`를 보지 않는다. 그래서 request id가 한 바퀴 돌면 같은 id가 다시 나간다. `css_get_data_buffer`는 같은 key의 첫 항목, 즉 죽은 ping 버퍼를 돌려준다.
- 측정(코드): 같은 상황에서 접속 경로(`connection_cl.cpp`의 `error_receive_data`)와 CDC 클라이언트(`cubrid_log.c`의 `css_queue_find_and_remove_header_entry_ptr`)는 등록을 뺀다. ping 경로만 빠져 있다.

### 3. 같은 id가 다시 쓰일 때 깨진다

- 측정(cc4, cc5): 크래시는 `tran_server_commit` → `net_client_request` → `css_receive_data` 안에서 났다. request id는 6840이었다. `css_receive_data`가 받은 버퍼는 크기 4의 스택 주소였고, 큐에는 commit 자신의 8바이트 버퍼가 그대로 남아 있었다. `css_net_recv`가 4바이트 응답을 자기 return 주소 위에 써서 pc가 0x7f..02000000으로 튀었다.
- 측정(cc6): 첫 바퀴의 rid 6840은 case 18의 `check_cas` ping이었다. 추론(프레임 계산): 그 `reply_buf` 위치는 `process_request` rbp − 0x3f8로, cc4와 cc5에서 쓰인 stale 주소와 같은 자리다.
- 측정(cc19, 코드): 같은 id를 다시 쓰는 요청에 따라 증상이 다르다. 응답이 등록한 버퍼가 아닌 곳으로 오면 `-187 Communications buffer not used`가 난다. 이때 그 요청의 정상 `replybuf`가 같은 id로 큐에 남아 새 stale 항목이 된다. 다음 바퀴(case 206)에서는 그 스택 주소를 `free()`해서 CAS가 abort했다.

## 자연 실행에서 head만 크래시가 난 이유

- 측정(`tools/race.py`): 서버 정지는 두 head 모두 case 18의 거의 같은 지점에서 시작한다. f69816c086에서는 CAS가 문장 317~319를 막 끝내고 ping을 보내려던 때였다(cc4, cc5, cc9). 173d92e454에서는 대개 문장 324(`create table t3`, timeout 없음)를 실행하던 때였다(cc8, cc16, cc17). cc11은 base에서도 문장 318에서 걸려 ping이 timeout됐다.
- 추론: 비동기 vacuum 알림과 ping 사이의 타이밍 경쟁이다. head가 그 구간에 몇 문장 일찍 도달해 ping이 더 자주 진다. 결함 자체는 두 head에 똑같이 있다.
- 측정(cc20, cc21): 진단 설정을 끄고 43번째 ping(자연 timeout이 난 바로 그 ping)만 gdb로 timeout을 돌려주게 하면, base와 head 모두 rid 6840을 받고 case 122에서 CAS가 abort한다. 위치는 `tran_server_abort` → `net_client_request_internal`의 `COMPARE_AND_FREE_BUFFER (replybuf, reply)`(network_cl.c:544)이고, free하는 포인터가 stale 스택 버퍼다. Sidecar 코드도 진단 설정도 없이 ping timeout 하나로 같은 결함이 드러난다.
- 비율(측정): 진단 설정을 켜고 CAS를 제 속도로 돌렸을 때 자연 ping timeout은 f69816c086 3/3(cc4, cc5, cc19. cc2도 같은 크래시였지만 broker 로그를 남기기 전 실행이다), 173d92e454 0/2(cc16, cc17)이다. 문장 319의 ping이 제 속도에서 timeout된 실행은 6/6 모두 case 122에서 크래시, abort 또는 NOK였다(자연 cc2, cc4, cc5, cc19, 강제 cc20, cc21). request id 6840은 cc4, cc5, cc20, cc21에서 측정했다.

## lf4의 나머지 NOK 3개

- 측정(cc19): lf4와 같은 설정(head, 진단 설정, 1..399, 20M 로그)으로 다시 돌리니 lf4와 같은 4개가 NOK였다.
  - 122 `column_name_serial_03.sql`: 마지막 문장이 `Error:-187`.
  - 206 `cbrd_25147_3.sql`: CAS가 `net_client_request_with_callback`의 `free()`에서 abort.
  - 208 `02_system_method.sql`, 211 `06_javasp_with_trigger.sql`: 206이 지우지 못한 `TEST_USER2`가 결과에 섞임.
- 추론: 122의 -187로 그 요청의 `replybuf`가 같은 id로 새 stale 항목이 되고, 다음 바퀴인 206에서 터졌다. 208과 211은 206의 여파다. lf4의 로그는 지워져서 case 이름은 비교하지 못했고, 같은 설정에서 같은 개수라는 점으로 맞췄다.

## 다른 가설 확인

- JDBC jar: 측정. 로컬에서 쓰던 `cubrid-jdbc-11.4.0.0088.jar`는 f69816c086과 173d92e454가 고정한 cubrid-jdbc c3933fc로 빌드한 jar와 sha1이 같다. 맞는 드라이버다.
- `sidecar_force_external`: 측정. debug 설치본 conf는 이 값을 정하지 않고 기본값이 yes라 CI와 같다. `no`로 바꾼 cc9에서도 ping timeout이 그대로 났다.
- 빈 core 파일: 측정. 커널 core가 아니라 `cas_sig_handler`가 쓰는 `$CUBRID/log/coredump/*.coredump`이다. 이번에는 gdb를 CAS에 붙여 스택을 얻었다.

## 하지 않은 것

- 수정: 하지 않았다. 결함은 Sidecar PR이 건드리지 않는 develop의 클라이언트 네트워크 코드에 있다. f69816c086 위 branch에서 고치면 Sidecar 작업에 develop 수정이 섞인다. 고친다면 ping처럼 사용자 버퍼를 큐에 넣고 응답을 포기하는 경로에서 그 등록을 빼야 한다(접속 경로와 `cubrid_log.c`가 이미 그렇게 한다). 또는 `css_is_valid_request_id`가 살아 있는 사용자 버퍼가 있는 id를 거르게 해야 한다. 별도 develop 이슈로 다루는 편이 맞다. 수정의 확인은 `NO_STACKDUMP=1 GDB_PRE=tools/force-ping-43.gdb tools/one.sh <이름> <설치본> <워크트리> 1 122`로 한다. 지금은 case 122에서 CAS가 abort하고(cc20, cc21), 고친 뒤에는 abort하지 않아야 한다.
- PR 댓글, JIRA 쓰기, CI 실행, engine branch push는 하지 않았다.

## 증거

- 결정 기록과 시도별 상세: `my-cubrid-docs/.scratch/sidecar/ci-fix/cascrash/decisions.md`
- 발췌: `.scratch/sidecar/ci-fix/cascrash/evidence/` (크래시 시점 상태, rid 6840 ping, ping timeout, commit의 큐 정리, 서버 정지와 CAS 활동, lf4 재현, base 강제 timeout, JDBC jar, 시도 요약)
- 도구: `.scratch/sidecar/ci-fix/cascrash/tools/` (`mkattempt.sh`, `runattempt.sh`, `one.sh`, `caswatch.sh`, `atcrash.gdb`, `force-ping-*.gdb`, `gaps.py`, `caslog-gap.py`, `race.py`)
