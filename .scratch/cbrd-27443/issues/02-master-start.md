# 02: master가 없는 환경과 직접 daemon master 시작 처리

**What to build:** 새 master를 생성하는 시작 요청에서도 호출자가 결과를 수집하고 종료할 수 있게 한다. 직접 daemon master를 시작하는 기존 경로도 호출자 자원을 분리하면서 daemon 기능을 유지한다.

**Blocked by:** 01: 기존 master 환경에서 서버 시작·실패 후 파이프 종료.

**Status:** claimed

**Parent:** CBRD-27443 — [합의된 스펙](../spec.md). 착수 전에 전체 스펙의 외부 계약·시험 원칙과 이 티켓에 해당하는 근거를 읽는다.

**Acceptance coverage:** A01, A03, A04(master 없음), A05(master 시작 실패), A06(master 생성), A12; A02 회귀.

- [ ] 01의 출력·FD 인계 계약을 master 생성 경계에 적용한다. 서비스 내부에서 daemon 초기화를 건너뛰는 경로와 직접 daemon master 시작을 각각 확인한다.
- [ ] master가 없는 상태에서 정상 DB 시작 후 기존 성공 결과와 종료 코드, stdout·stderr EOF, SQL·PL 기능을 함께 확인한다. EOF를 얻기 위해 서버나 master를 종료하지 않는다.
- [ ] 새 master를 만든 뒤 DB 시작이 실패해도 기존 진단과 실패 코드가 전달되고 두 출력 스트림이 종료된다. 살아남은 master는 호출자의 파이프·잠금 FD를 보유하지 않는다.
- [ ] master 자체의 실행·초기화 실패에서 호출자 진단, 실패 코드, EOF, 실패 자식과 불필요한 FD 정리를 검증한다.
- [ ] 직접 daemon master의 호출자는 출력 수집을 마칠 수 있고, daemon화된 master는 실제로 연결·서버 등록을 처리한다. daemon 부모의 종료 코드만으로 준비 완료를 판정하지 않는다.
- [ ] master의 직접 stdout·stderr 메시지에 사용할 진단 대상을 기록하고 기존 오류 로그를 보존한다. foreground 출력 계약과 직접 서버 실행은 유지한다.
- [ ] 일반 상속 FD·잠금 FD와 각 출력 수집 형태를 검사하고, master가 이미 있는 01의 경로를 회귀 검증한다.
- [ ] 격리된 CLI 회귀 사례와 native testkit 판정에 baseline·수정본의 커밋/바이너리, 종료/EOF 관측, 살아 있는 프로세스를 기록한다.

## Implementation notes

01이 제공하는 별도 로그와 실패 진단 전달 계약을 재사용하므로 01 완료가 선행 조건이다. 프로세스 그룹이나 timeout 그룹 신호 정책을 바꾸는 작업은 포함하지 않는다.
