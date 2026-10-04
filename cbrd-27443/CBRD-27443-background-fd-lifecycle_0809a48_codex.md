# CBRD-27443: 백그라운드 프로세스의 파일·출력 연결 수명 정리

https://jira.cubrid.org/browse/CBRD-27443

## Purpose

`cubrid server start testdb | cat`에서 시작 명령이 끝나도 `cat`이 종료되지 않는 문제를 해결한다. FD(file descriptor)는 프로세스가 열린 파일이나 파이프를 가리키는 번호다. master, 서버, PL(저장 프로시저 실행 프로세스)이 호출자의 출력 파이프나 잠금 파일 FD를 물려받으면 호출자가 종료해도 해당 자원이 계속 열린 채 남는다. 처음 시작할 때뿐 아니라 자동 재시작에서도 같은 문제가 발생한다.

- AS-IS: 시작 명령이 성공 코드 0으로 끝나도 서비스 자식이 호출자의 stdout·stderr 파이프와 잠금 파일을 보유하여 출력 수집과 후속 작업이 끝나지 않는다.
- TO-BE: 백그라운드 서비스가 필요한 입출력만 명시적으로 전달받고, 시작 명령은 현재 시도의 진단 출력을 전달한 뒤 호출자의 파이프와 잠금을 해제한다. 실행 중인 서비스의 이후 출력은 크기가 제한된 전용 로그에 남긴다.

검증 기준 엔진은 `0809a480df55ac6767a905d03fa3d31edd40a93c`, 테스트는 `6bdbb89738088948c479a6d85662276126a31bb5`다. 이 문서는 완료된 ticket08 최종 보고서와 엔진 변경을 대조해 작성했다. 아래 결과는 해당 커밋의 완료된 로컬 Linux 검증이며, 새 GitHub CI 결과와 구분한다.

## Implementation

### Process boundaries

- `src/base/background_process.cpp`, `src/base/background_process.hpp`: 실행 전에 경로·인자·환경·FD 연결을 준비한다. 자식은 지정된 표준 입출력만 연결하고 나머지 상속 FD를 닫는다. exec 실패는 전용 파이프로 부모에게 전달하고 자식은 `_exit`로 종료하여 부모 제어 흐름으로 돌아가지 않는다.
- Linux에서는 `close_range`를 먼저 사용하고, 사용할 수 없으면 자식 안에서 raw `getdents64`로 `/proc/self/fd`를 열거한다. 부모의 스냅샷이나 낮아진 soft limit에만 의존하지 않는다. 비 Linux의 hard-limit 순회는 아래 제한을 가진다.
- `background_process_prepare_stdio`는 처음부터 닫혀 있던 0·1·2를 예약하여 내부 로그나 DB 파일이 표준 입출력 번호로 잘못 전달되지 않도록 한다.
- `src/executables/util_service.c`: master·서버 및 로컬 HA 유틸리티 시작 경로에 출력 수집을 연결한다. 기존 준비 완료·실패 판정 중 stdout과 stderr를 함께 비우며, 여러 HA 프로세스의 짧은 진단 문장이 서로 섞이지 않도록 유한 버퍼로 처리한다.
- `src/executables/master.c`: 직접 daemon 실행도 실제 호출된 실행 파일로 다시 실행하여 FD 경계를 적용한다. Linux에서는 실행 파일의 이름 변경·삭제 이후에도 같은 이미지를 사용하고 프로세스 이름을 보존한다. 의도적인 foreground/PID1 동작은 별도 계약으로 유지한다.
- `src/executables/master_server_monitor.cpp`, `src/executables/master_heartbeat.c`, `src/sp/pl_sr.cpp`: 일반 서버·HA·PL 재시작에도 같은 FD 경계를 적용한다. PL은 부모가 의도적으로 선택한 출력만 유지한다. 일반 서버의 동기적인 exec 실패 재시도는 기존 확인 주기에 맞춰 대기한다.
- `src/executables/server.c`, `src/executables/csql_launcher.c` 및 관련 실행 파일 진입점은 내부 파일을 열기 전에 닫힌 표준 FD를 처리한다. 직접 서버 실행, SA(단독 실행), 동기 관리 명령의 출력 계약은 유지한다.

### Console output

`src/executables/console_relay.cpp`의 내부 실행 파일 `cub_console`이 백그라운드 stdout·stderr를 받아 기록한다. 시작 중에는 이번 호출의 출력만 호출자에게 전달한다. 기존 시작 판정이 끝나면 그 시점에 쌓인 바이트를 유한하게 수집하고 호출자 측 연결을 닫는다. 이후 서비스 출력은 로그로 계속 전달한다. 지속적으로 출력하는 서비스 때문에 새로운 준비 완료 대기를 추가하지 않는다.

`src/base/console_log.hpp`는 로그별로 활성 파일 최대 1 MiB와 최대 1 MiB인 보관 파일 3개를 유지한다. 파일 권한은 0600이다. 안정된 잠금 파일로 회전을 조정하고, 기록할 때마다 경로를 다시 열어 삭제된 로그 inode를 계속 보유하지 않도록 한다. 기존에 과도하게 큰 파일은 최근 꼬리만 유지한다. 기존 오류 로그도 유지한다.

초기 설정·기록 오류는 시작 경로에서 확인한다. 실행 중 로그 저장에 실패하면 256바이트 오류 기록과 best-effort syslog를 남기고 입력을 계속 비워 서비스 진행을 유지한다. 저장 실패 중 바이트는 버릴 수 있으며, 목적지가 복구되면 이후 기록을 재개한다. 성공한 기록이 과거 실패 기록을 지우지는 않는다.

### Broker lifecycle and installation

`src/broker/broker_process.cpp`, `src/broker/broker_process.hpp`는 broker(접속 중계), CAS(요청 처리), SHARD proxy(분산 접속 중계)의 초기 실행과 재시작에 필요한 환경과 FD를 준비한다. `broker.c`, `broker_admin.c`, `broker_admin_pub.c`, `broker_util.c`, `broker_util.h`가 이를 사용한다. 필요한 실행 후 통신인 `SCM_RIGHTS` 소켓 전달은 유지한다.

초기 자식 수마다 출력 연결을 새로 보유하지 않고, 한 broker 관리 호출에서 broker·CAS·proxy의 최대 세 목적지별로 공유한다. 따라서 자식 수에 비례하던 시작 FD 증가를 막는다. 여러 broker를 시작하는 동안 뒤늦게 나오는 초기 진단도 기존 준비 확인 범위에서 수집한다. 출력 마무리에 실패하면 이미 시작한 broker 묶음까지 되돌리는 처리를 포함한다.

`broker/CMakeLists.txt`, `cubrid/CMakeLists.txt`, `sa/CMakeLists.txt`, `util/CMakeLists.txt`가 공통 구현을 연결한다. `cub_console`은 Application 설치 구성 요소에 포함한다.

## Remarks

### Verified results

최종 설치 및 native 실행 복사본은 `11.5.0.2659-0809a48`, Linux debug 빌드다. CMake `debug_gcc` configure/build/install이 성공했고, 사전 검사에서 소스·설치 일치와 빈 소스·테스트 패치를 확인했다. `UNIT_TESTS=OFF`이므로 CTest 또는 unit test 통과를 주장하지 않는다. 회귀 절차는 native `testkit shell -c <effective config>` 실행과 산출물 검증이다.

`cubrid-testcases-private-ex`의 `shell/_01_utility/cbrd_27443` 아래 네 native case를 한 슬롯에서 재시도·업데이트·이어 실행 없이 수행했다. 총 1,189초, 성공 4건, 실패 0건, skip 0건이다. 기존 case별 1,200초 제한을 바꾸지 않았다.

| Case | 소요 시간(초) | 결과 |
|---|---:|---|
| `broker/cases/broker.sh` | 140.451 | PASS |
| `cases/cbrd_27443.sh` | 389.749 | PASS |
| `ha/cases/ha.sh` | 569.315 | PASS |
| `logging/cases/logging.sh` | 88.382 | PASS |

12개 matrix의 2,566개 검사와 별도 보조 검사 9개가 모두 통과했다. 보조 검사는 native case 수에 더하지 않는다. native 종료 코드는 0이며 상태 파일·XML·feedback·dispatch·실행 로그의 case 식별자가 일치한다. 독립 산출물 감사도 통과했다.

- 180개 출력 수집 중 179개 백그라운드 실행에서 독립적인 stdout·stderr EOF(더 읽을 출력이 없다는 신호), 호출자 FD 미보유, 서비스를 멈추기 전 잠금 해제를 확인했다. 나머지 1개는 의도적인 PID1 foreground master이며 감독자의 stdout·stderr만 유지하고 일반 호출자 파일·잠금은 해제함을 별도로 확인했다.
- master 존재·부재, 시작 실패, 개별/합친 stdout·stderr, `cat`·`rg` 수집, 일반/PL/HA 재시작, 두 노드 복제, ordinary/SHARD broker·CAS·proxy를 확인했다. 호출 명령과 수집기의 종료 코드는 따로 기록했다.
- 실제 SQL·PL·CCI의 prepare/execute/fetch와 두 노드의 1~15행 복제 진행을 확인했다. 네 출력 집합의 정확한 4,000행 보존과 다섯 내부 재시작의 전용 stdio 보유는 보조 검사로 확인했다.
- 12회의 실행 중 로그 장애에서 pipe 용량보다 많은 출력을 발생시켰다. 새 오류 기록의 timestamp를 확인하고, 장애 중 SQL·PL·CCI 또는 복제가 계속 진행되며 같은 서비스와 relay가 살아 있음을 확인했다. 목적지 복구 후 새 marker와 후속 동작도 확인했다.
- ordinary 32-CAS와 두 broker 64-CAS는 hard=soft 128에서 성공했고 최종 표본의 최대 launcher FD 수는 21이었다. SHARD 32-CAS는 기존 구성에 필요한 hard=soft 1,024에서 성공했고 최대 표본은 33이었다. 초기 4,096행 출력, 늦은 출력, 실패 rollback도 검사했다.
- FD 65535를 열고 soft limit을 256으로 낮춘 경우, 닫힌 0·1·2, 강제 `close_range` ENOSYS 이후 raw `/proc` 경로를 Linux에서 확인했다.
- 18개 설치/복사 실행 파일·라이브러리 쌍과 252개 fixture 파일의 실제 해시를 독립 재검증했다. 모든 fixture namespace의 알려지지 않은 이름을 포함한 자식 프로세스와 broker 전용 공유 메모리 정리를 확인했다.

### Compatibility and limitations

1. Windows와 비 Linux는 빌드·실행 미검증이다. 비 Linux hard-limit 순회는 소스 검토만 했으며, hard limit을 나중에 낮췄을 때 그보다 높은 열린 FD가 남지 않는다고 가정한다. 최종 high-FD 실행은 soft limit만 낮췄으므로 이 가정을 실측 검증한 결과가 아니다.
2. 외부 ODBC/CAS_CGW gateway backend는 구성하지 않아 기능 미검증이다. 공유 코드가 Linux에서 컴파일됐다는 사실을 gateway 동작 검증으로 취급하지 않는다. legacy non-CAS 관리 재시작은 허용된 CAS/CAS_CGW 유형이 앞선 분기로 들어가 실행되지 않는 경로로 소스 검토만 했다. `shard_admin_pub.c`의 raw fork는 `UNDEFINED` 아래 비활성 경로다.
3. 의도적인 foreground/PID1 master와 직접·동기 실행은 호출자 출력을 유지하는 예외다. 직접 daemon 부모의 성공 코드도 새 준비 완료 보장을 뜻하지 않는다.
4. 기존 공개 종료 코드를 보존한다. 로컬 copy/apply/replication exec 누락과 ordinary CAS 누락은 역사적인 공개 코드 0을 유지하며 원래 진단을 전달한다. heartbeat start 실패와 SHARD CAS 누락은 1이다. 관리 대상 raw `cub_commdb` exec 누락의 0→255 수정은 이 공개 인터페이스들과 구분한다.
5. 초기 SHARD 실패가 다른 생산자의 모든 예정 출력을 기다리지는 않는다. 성공 실행에서는 전체 계획 출력을 확인했지만 조기 실패에는 현재 시도의 진단·회전·EOF를 확인하며 새로운 준비 대기를 도입하지 않는다.
6. 실행 중 저장 장애에서는 출력의 무손실 보존을 보장하지 않는다. 일반적인 파일 작업 오류는 검증했지만 무기한 멈춘 파일시스템 작업에 새로운 시간 상한을 보장하지 않는다.
7. 전체 플랫폼·구성 명세, 전체 QA corpus 또는 외부 CI 완료를 주장하지 않는다. 이 게시 작업에서는 완료된 로컬 결과를 재실행 결과로 바꾸어 표현하지 않는다.
8. 엔진 전체 변경의 `git diff --check`는 통과했다. 전체 테스트 변경에는 이전 `4a201c38cf`에서 생긴 `cases/cli_fixture.py:163`의 EOF 빈 줄 경고가 남아 있다. 승인된 커밋 상태를 보존했고, 테스트 전체 범위가 스타일 검사까지 깨끗하다고 주장하지 않는다.

### Review history and CI handoff

기준 엔진 `15e7dc8`은 호출 명령의 코드가 0인데도 두 EOF가 오지 않고 호출자 잠금이 유지되는 현상을 재현했다. 중간 broker 구현의 soft limit 128 확장 실패는 최종 `0809a480`에서 수정한 뒤 네 case 전체로 재검증했다. fixture의 조기 SQL 실행, PL 관리 호출에 잘못 주입한 출력, 여러 CAS의 marker 덮어쓰기, 조기 SHARD 실패의 과도한 출력 기대, HA 관리 argv[0] 불일치도 수정했다. 이전 실패 시도나 개별 green 결과를 최종 성공 수에 더하지 않았다. 최종 독립 Standards/Spec 검토는 위 Linux 범위와 제한을 명시한 상태로 수락했다.

[Engine Draft PR #8094](https://github.com/CUBRID/cubrid/pull/8094)를 `develop` 대상으로 게시했다. [TC Branch Sync](https://github.com/CUBRID/cubrid/actions/runs/37181849529)가 두 테스트 저장소에 `tc/pr-8094`와 Draft PR을 자동 생성했다. 기존 테스트 27개 커밋을 최신 테스트 develop 위에 충돌 없이 cherry-pick하여 [Tests PR #4306](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4306)에 게시했다. 새 tip은 `bb9412a8ca1b87b1aa28add8a55fb36160b119ed`이며 각 커밋 메시지에 원본 SHA를 남겼다. 원본 `6bdbb8973`과 새 tip의 `shell/_01_utility/cbrd_27443` tree는 모두 `115e5da4972ffa7057ab45106bd1d50ddfce7da1`로, 25개 파일의 내용과 모드가 같다. 변경하지 않은 public 테스트 저장소의 [자동 생성 PR #3637](https://github.com/CUBRID/cubrid-testcases/pull/3637)도 유지했다.

[한 번의 `/run all` 요청](https://github.com/CUBRID/cubrid/pull/8094#issuecomment-5977194317)으로 [gha-ci #37182000341](https://github.com/CUBRID/cubrid/actions/runs/37182000341)을 시작했다. 최초 접수에서 release/debug 빌드와 shell·SQL·medium 다섯 상태가 같은 실행에 pending으로 연결됨을 확인했다. CI는 `tc/pr-8094`에서 테스트를 선택한다. 실제 실행의 테스트 SHA 고정은 빌드 이후 준비 단계에서 이루어지므로, 원격 브랜치 반영 확인을 전체 CI 통과로 표현하지 않는다. Engine과 Tests의 로컬 merge 및 수동 Tests PR 생성은 수행하지 않았다.
