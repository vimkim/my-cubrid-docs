# CBRD-27443: 시작 결과 전달과 백그라운드 프로세스의 출력 수명 분리

Status: ready-for-agent

Issue: [CBRD-27443](http://jira.cubrid.org/browse/CBRD-27443)

이 문서는 2026-10-02 대화에서 합의한 동작을 기존 FD 수명 분석에 연결한다. 사용자가 CLI 통합 검증 중심의 테스트 경계를 확인했으며, 로컬 이슈 트래커에 `ready-for-agent`로 발행한다. 엔진 구현 또는 수정본 검증이 완료됐다는 뜻은 아니다.

## Problem Statement

AI agent와 자동화 도구는 `cubrid server start demodb | cat`, `cubrid server start demodb | rg ...`처럼 시작 명령의 출력을 파이프로 수집한다. 현재는 시작 명령이 성공 또는 실패를 보고하고 종료해도, 그 명령이 만든 master·DB 서버·PL 등의 프로세스가 같은 파이프의 쓰기 연결을 보유해 출력 수집이 끝나지 않을 수 있다. 표준 오류까지 수집하는 호출도 영향을 받는다.

호출자는 시작 결과를 받고 다음 SQL 실행이나 정리 작업으로 넘어가야 한다. 성공한 DB 서버는 계속 실행되어야 하므로, 서버를 종료하거나 출력 수집을 중단하는 우회는 완료 조건을 충족하지 않는다. 출력과 함께 상속된 불필요한 FD는 호출자의 파일 잠금이나 부모의 내부 자원도 유지할 수 있다.

## Solution

시작 명령은 기존 성공·실패 판정, 종료 코드, 결과 메시지와 시작 실패 진단을 호출자에게 전달한다. 백그라운드 프로세스는 호출자 전용 출력 파이프와 불필요하게 상속한 FD를 놓는다. 시작 명령이 종료하고 이미 쓴 데이터가 소비되면 호출자는 stdout·stderr에서 EOF를 받고 다음 작업을 진행할 수 있어야 한다.

기존 서버 오류 로그는 위치와 기록 방식을 유지한다. 오류 로그 체계를 거치지 않고 stdout·stderr에 직접 쓰는 백그라운드 서버의 출력은 별도 로그에 보존한다. 별도 로그는 재시작 시 이어 쓰고, 용량 제한과 회전을 제공한다. 이 방향은 이번 대화에서 채택한 임시 스펙이며 정확한 파일명과 구현 방식은 아직 확정하지 않았다.

성공한 서버는 호출자의 출력 수집이 끝난 뒤에도 SQL과 저장 프로시저 요청을 처리해야 한다. 최초 시작뿐 아니라 master·PL 생성 및 재시작에도 같은 FD 소유 원칙을 적용한다. 직접 `cub_server` 실행은 우선 기존 stdout·stderr 동작을 유지한다.

## User Stories

1. As an AI agent developer, I want a piped server-start command to finish collecting output, so that my agent can proceed to the next task.
2. As an automation author, I want stderr capture and merged stdout/stderr capture to finish too, so that diagnostic collection does not keep my job waiting.
3. As a database user, I want a successfully started server to remain usable after the pipeline finishes, so that output completion does not stop the service.
4. As a script author, I want the existing start success criterion and exit codes preserved, so that existing success/failure handling keeps working.
5. As an operator, I want the existing startup failure messages to reach the terminal or captured stream, so that I can diagnose a failed start.
6. As an operator, I want startup failures reported even before a log file exists, so that failure remains visible when logging cannot initialize.
7. As an operator, I want existing server error logs to keep their current destination and behavior, so that established troubleshooting remains valid.
8. As an operator, I want background stdout/stderr messages retained in a separate log, so that detaching a server does not discard diagnostics.
9. As an operator, I want a restart to append rather than erase prior console output, so that evidence from the previous process survives.
10. As an operator, I want console log storage bounded through rotation, so that a long-running service does not grow that log indefinitely.
11. As an automation author, I want both absent-master and existing-master starts to release caller resources, so that behavior does not depend on earlier commands.
12. As an automation author, I want failed database starts to release caller resources even if master remains alive, so that I can handle the failure and continue.
13. As a caller using file locks, I want descendants to release unnecessary inherited references, so that closing my own lock descriptor releases my lock.
14. As an operator, I want automatically restarted servers to follow the same output and FD policy, so that recovery does not reintroduce the hang.
15. As a stored-procedure user, I want PL start and restart to preserve functionality while dropping unrelated parent descriptors, so that process isolation does not break stored procedures.
16. As a direct executable user, I want direct server invocation to retain its current output behavior for now, so that this fix does not silently change that workflow.
17. As a management-tool user, I want synchronous commands and their redirections preserved, so that changing service startup does not alter unrelated command output.
18. As an HA or broker operator, I want changed process-creation paths to preserve replication or client connectivity, so that descriptor cleanup does not break required communication.
19. As an implementer, I want duplicated and high-numbered inherited descriptors covered, so that closing only the obvious stdout/stderr handles cannot falsely pass verification.
20. As a reviewer, I want baseline and fixed-binary results identified separately, so that an existing reproduction or a successful collector exit is not presented as proof of a fix.

## Implementation Decisions

### 합의된 외부 계약

- **시작 결과:** 성공 판정 시점을 앞당기지 않는다. 기존 서버 등록 확인에 따른 시작 판정과 종료 코드를 유지한다. exec 성공만으로 DB 시작 성공을 보고하지 않는다. SQL·PL 기능 확인은 회귀 검증이며, 시작 명령에 새로운 readiness 조건을 추가하라는 요구는 아니다.
- **출력 완료:** 시작 명령 종료 후 데이터를 모두 읽은 호출자가 stdout·stderr의 EOF를 받는다. 서버 중지, 서비스 중지, 호출자의 강제 연결 종료를 요구하지 않는다. 짧은 실행 시간의 관측을 제품 시작 타임아웃으로 바꾸지 않는다.
- **시작 실패:** 기존 종료 코드, 결과 메시지, 터미널에 나오던 실패 진단을 유지한다. 진단 내용을 새롭게 개선할 필요는 없다. 기존 로그의 위치만 안내하면서 기존 진단을 생략하는 것은 계약을 충족하지 않는다.
- **로그:** 기존 오류 로그와 추가 stdout·stderr 로그는 별도의 출력 대상이다. 재시작으로 기존 내용을 지우지 않으며, 용량 제한과 회전을 제공한다. 파일을 열 수 없는 경우에도 시작 실패를 호출자에게 알려야 한다.
- **직접 실행:** 직접 서버 실행의 출력 방식은 당분간 유지한다. 서비스 관리자용 새 foreground 모드나 시작 방식을 추가하지 않는다. 직접 daemon master를 시작하는 기존 경로는 별도로 확인하며 daemon과 foreground를 혼동하지 않는다.

### 모듈별 책임과 구현 제약

- 서비스 명령 실행부는 호출자에게 시작 결과를 전달하는 책임을 유지한다. 서버 등록 확인과 초기 진단 전달을 함께 다루되, 시작 결과와 장기 실행 프로세스의 출력 수명을 분리한다.
- 프로세스 생성 공통부와 각 생성 경계는 필요한 표준 입출력 대상과 exec 보존 FD를 명시한다. 동기 대기 여부 하나로 자식과 자손의 수명 정책을 추론하지 않는다.
- master 최초 시작, 일반 서버 재시작, HA 관리 경로, PL 최초 시작과 재시작을 조사한다. 동기 관리 명령이 장기 실행 broker 자손을 만드는 경우도 생성 경계별로 분류한다. 공통 도우미 변경이 닿는 경로는 기능 회귀 검사에 포함한다.
- 일반 상속 FD는 필요한 exec 인계 계약에 따라 정리한다. 호출자의 잠금을 명시적으로 해제하는 대신 자식의 불필요한 참조를 닫는다. 실행 중 전달받는 소켓과 exec 때 보존할 FD를 구분한다.
- 표준 FD는 유효한 대상으로 치환한다. stdout·stderr와 같은 파이프를 가리키는 높은 번호의 복제 FD도 정리 대상이다. 닫힌 표준 FD 번호를 다른 파일이 차지해 오기록되는 경우를 방지한다.
- 다중 스레드 부모에서 fork한 자식은 exec 전에 안전한 FD 조작·exec·제한된 오류 통지만 수행하도록 설계한다. 필요한 준비는 부모에서 한다. 생성 실패 자식이 부모의 제어 흐름으로 돌아오지 않게 한다.
- 지원 환경에 맞는 FD 정리 방식과 fallback을 정한다. 낮아진 soft limit보다 높은 기존 FD, 이미 닫힌 표준 FD, 큰 FD 한계에서도 정리 정확성을 확인한다. Linux 실측을 Windows 검증으로 확대하지 않는다.

### 구현 시 확정할 사항

아래는 새 사용자 인터뷰를 시작할 항목이 아니라 소스 조사와 작은 실험으로 구체화할 구현 항목이다. 외부 계약을 바꿔야 하는 경우에만 변경안을 사용자에게 제시한다.

| 항목 | 고정된 요구 | 아직 정하지 않은 부분 |
|---|---|---|
| 별도 로그 | 기존 오류 로그 유지, stdout·stderr 보존, 재시작 이어 쓰기, 용량 제한·회전 | 정확한 이름·권한·크기·보관 개수·회전 담당자, master·PL 등 서비스별 목적지 |
| 초기 실패 진단 | 기존 호출자 진단과 코드 유지, 로그 생성 전 실패도 전달 | 전용 전달 채널 또는 해당 시작 시도 로그 전달 등 구체적 방식 |
| 생성 정책 | 호출자와 부모 내부의 불필요한 FD 정리, 필요한 통신 보존 | 공통 인터페이스 형태, 호출부별 보존 목록, 플랫폼별 API |
| 로그 장애 | 오류를 조용히 버리거나 새 무한 대기를 만들지 않음 | 실행 중 쓰기·회전 실패 시 진단 및 처리, 동시 쓰기와 재시작 중 회전 처리 |

실패 진단 전달 시 이전 시작 시도나 다른 DB의 로그를 이번 실패로 출력하지 않아야 한다. stdout·stderr를 같은 파일로 보내는 경우에도 각각 열면서 로그를 초기화하지 않아야 한다. 파일명을 정하는 것만으로 다중 작성자의 로그 회전이나 초기 진단 전달 문제가 해결됐다고 간주하지 않는다.

## Testing Decisions

### 주 검증 경계

실제 CLI와 호출자의 출력 수집 경계를 주 검증 지점으로 사용한다. 격리된 인스턴스에서 이미 생성되어 있고 중지된 DB를 시작하고, 명령 종료와 두 스트림의 EOF를 독립적으로 관측한다. DB와 필요한 관리 프로세스가 살아 있는 상태에서 SQL·PL 기능을 확인한다. 사용자는 2026-10-02 내부 도우미 중심 대신 이 CLI 통합 검증 경계를 선택했다.

새로운 내부 테스트 인터페이스는 기본 요구가 아니다. 실제 CLI에서 재현하기 어려운 FD 배치, exec 실패, 로그 접근 실패 조건만 가장 가까운 프로세스 생성 경계의 보조 테스트로 다룬다. 특정 함수 호출 순서나 FD 번호 대신 외부에서 관측되는 출력·잠금·프로세스 상태·DB 기능을 판정한다.

### 기존 시험 자산과 실행 원칙

- 기존 격리 probe는 master 없음/있음, 없는 DB, 직접 daemon master, 일반 자동 재시작을 수집한다. 이를 확장해 사용하며 PID-1 reaper와 사설 설정·DB 목록·네트워크·임시 경로 격리를 유지한다.
- probe의 종료 코드 0은 수집·정리 성공이다. 개별 결과의 EOF, 명령 코드, 잠금과 DB 동작을 검사하는 회귀 판정이 추가로 필요하다.
- 빌드 기준 커밋과 실제 설치 바이너리 식별자를 기록하고, 같은 시험으로 baseline 실패와 수정본 통과를 비교한다. 이전 독립 실측은 새 작업 브랜치 빌드의 결과를 대신하지 않는다.
- 정상 시작의 EOF 검사는 서버를 멈추기 전에 수행한다. 시작 명령의 종료 시각과 각 EOF 시각을 기록한다. 시험용 감시 시간은 무한 대기를 회수하기 위한 것이며 제품의 시작 SLA가 아니다.
- 파이프 마지막 명령의 코드와 시작 명령 자체의 코드를 구분한다. `rg`의 일치 여부 때문에 시작 실패를 오판하지 않도록 시작 코드를 별도 수집한다.
- 지속 회귀는 CUBRID shell testcase 체계에 두고 해당 native testkit으로 판정한다. SQL·PL 요청은 이 프로세스 수명 검증의 기능 확인으로 포함한다. 조직 공유 문서의 명령은 프로젝트 스크립트·CMake·ctest·testkit으로 표현한다.

### Acceptance Matrix

다음은 수정본에 요구되는 검증이며 현재 통과 목록이 아니다. 확정한 CLI 통합 검증 경계에서 같은 기준으로 구체적 사례를 작성한다.

| ID | 조건 | 통과 기준 |
|---|---|---|
| A01 | master 없음 + 정상 서버 시작 | 기존 성공 결과/코드, stdout·stderr EOF, DB 생존과 SQL 가능, 호출자 잠금 해제 가능 |
| A02 | master 있음 + 정상 서버 시작 | A01과 동일하며 기존 master 동작 보존 |
| A03 | stdout만, stderr만, 별도 수집, 합친 파이프 | 모든 수집 스트림 종료, 기존 시작 결과 보존; `cat`과 `rg` 호출 확인 |
| A04 | 없는 DB 등 기존 시작 실패 | 기존 실패 코드와 호출자 진단 보존, EOF, 남은 master에도 호출자 FD 없음 |
| A05 | master 시작 실패, exec 실패, 별도 로그 열기 실패 | 실패를 호출자에게 전달, EOF, 실패 자식과 불필요한 FD 정리; 로그 파일 존재에 의존하지 않음 |
| A06 | 일반 FD·잠금 FD·파이프 복제 FD 상속 | 필요한 인계만 유지, 호출자가 자기 잠금 FD를 닫으면 새 호출자가 잠금 획득 가능 |
| A07 | 일반 서버 자동 재시작 | 새 서버·PL에도 호출자/부모의 불필요한 FD 없음, SQL·PL 기능 정상 |
| A08 | PL만 재시작 및 SA의 PL 경로 | 불필요한 내부 로그·볼륨 FD 미상속, PL 호출 성공, 기존 SA 출력 유지 |
| A09 | 별도 로그 최초 생성·재시작·회전 | 직접 stdout·stderr 메시지 보존, 이전 시작 내용 유지, 정한 저장 한도 준수, 기존 오류 로그 정상 |
| A10 | 초기 실패 로그의 호출자 전달 | 이번 시작 시도의 기존 진단 전달; 오래된 로그나 다른 DB의 진단이 섞이지 않음 |
| A11 | 직접 서버 실행, 동기 관리 명령 | 기존 stdout·stderr/리다이렉션/반환 코드 동작 유지 |
| A12 | 직접 daemon master 시작 | daemon 동작 유지, 호출자 파이프와 불필요한 FD 분리 |
| A13 | 높은 FD·낮아진 soft limit·닫힌 표준 FD | 정리 누락 없음, FD 재사용에 의한 오기록 없음 |
| A14 | single-node HA 시작·재시작·heartbeat stop | 수정 경계에서 자원 분리, 기존 HA 상태 전이 유지 |
| A15 | 2-node copylogdb/applylogdb 시작·재시작 | 수정 경계에서 자원 분리와 실제 복제 진척을 함께 확인 |
| A16 | broker/CAS/proxy 최초 실행·재시작 | 공통부 변경 영향 경계별 FD 계약과 클라이언트 접속 유지 |

A14–A16은 실제 변경 영향도를 조사해 적용 여부와 근거를 기록한다. 미변경 경로라는 판단은 공통 도우미의 간접 영향까지 확인해야 한다. 적용 대상인데 실행하지 못한 항목은 미검증으로 남기며 전체 검증 완료를 주장하지 않는다. 로그 장애와 회전의 구체적 기대값은 구현 결정과 함께 회귀 사례에 반영한다.

## Out of Scope

- 기존 시작 오류 메시지의 문구나 상세 원인을 새롭게 개선하는 작업.
- 시작 성공 의미 변경, 새 readiness 프로토콜 도입 자체를 목표로 삼는 작업, 등록 대기나 복구 시간에 새 제품 타임아웃을 부여하는 작업.
- 모든 서버 로그의 형식을 통합하거나 기존 오류 로그 위치를 변경하는 작업.
- 직접 서버 실행의 출력 정책 변경, 새로운 서비스 관리자 연동 방식.
- `NO_DAEMON`의 프로세스 그룹과 timeout 그룹 신호 문제 전반. FD 수명과 별도 후속 이슈로 취급한다.
- Windows 서비스 동작을 새로 설계하는 작업. 공통 소스 변경에 따른 호환성과 빌드 영향은 여전히 확인 대상이다.
- 호스트의 공유 서비스를 멈추는 시험과 전체 QA 통과를 이번 focused 시험만으로 선언하는 것.

## Further Notes

### 근거와 우선순위

동작에 대한 이번 대화의 최신 합의가 이전 분석의 미결정 표시보다 우선한다. 별도 로그 방침과 직접 서버 실행의 임시 유지 방침이 새로 정해졌으며, 나머지 원인 분석과 실측 provenance는 아래 원문을 따른다. 이 스펙의 로컬 발행은 JIRA 본문을 덮어쓰거나 새 댓글을 게시하는 동작이 아니다.

- [기존 분석: Source Analysis / Proposed Implementation / Independent Measurements / Acceptance Matrix](../../cbrd-27443/CBRD-27443-fd-lifecycle-analysis_c63a3b9_codex.md): 생성 경계 조사, 다중 스레드 안전성, 기존 출력 파일 인수의 unlink/truncate 위험을 검토할 때 읽는다.
- [기존 격리 probe](../../cbrd-27443/evidence/run-probe.sh)와 [환경·바이너리 정보](../../cbrd-27443/evidence/environment.json): 재현을 준비할 때 읽는다. 기존 런타임은 `11.5.0.2602-a0026f9`이며 분석 소스 `c63a3b993`의 직접 빌드 시험이 아니다.
- [기존 이슈 문서](/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27443-inherited-fd_c63a3b9_codex.md): 사용자 관점의 Description, Repro, Expected Result, Actual Result를 확인할 때 읽는다.
- [로컬 트래커 규약](../../docs/agents/issue-tracker.md): 후속 구현 티켓을 생성할 때 읽는다.

2026-10-02 확인한 엔진 작업 브랜치는 `CBRD-27443-fd-clean`, HEAD는 `c63a3b993be552ef6ad3ce244c386d5081147958`이며 깨끗하다. 로컬 `develop`은 `30043f492`다. 기존 분석의 생성 경로 7개 파일과 develop의 차이는 master의 Windows 전용 등록 프로토콜 분기 추가이며, 엔진 전체의 동일성을 의미하지 않는다. 구현 착수 시 live 상태를 다시 확인한다.

기존 독립 관측은 일반 시작·실패·직접 daemon master·일반 재시작의 결함을 뒷받침한다. single-node HA는 리뷰어 보고이며 이 작업의 독립 실행이 아니다. 2-node 복제, 수정본 기능 시험과 로그 회전 시험은 아직 수행하지 않았다.

이 스펙은 구현 전에 참조할 계약이다. 후속 티켓은 실행 가능한 동작 단위와 의존성을 기록하고, 구현은 별도 작업으로 등록한다. 본 문서 작성은 엔진 수정·빌드·PR 게시를 수행한 것이 아니다.
