# 07: broker·CAS·proxy 생성 경로 호환성 확보

**What to build:** broker 관리 명령과 그 명령이 만든 장기 실행 broker·CAS·proxy 자손이 호출자의 출력을 무기한 붙잡지 않게 하면서, 기존 관리 명령과 클라이언트 접속을 보존한다.

**Blocked by:** 01: 기존 master 환경에서 서버 시작·실패 후 파이프 종료.

**Status:** resolved

**Parent:** CBRD-27443 — [합의된 스펙](../spec.md). 착수 전에 전체 스펙의 외부 계약·시험 원칙과 이 티켓에 해당하는 근거를 읽는다.

**Acceptance coverage:** A16, A11; A03–A06의 broker 관련 영향 경계.

- [x] broker·CAS·proxy의 최초 생성과 내부 재시작을 별도로 조사하고, 01에서 변경한 공통 생성부의 직접·간접 영향을 기록한다.
- [x] 동기 관리 명령의 대기·출력·리다이렉션·종료 코드는 유지하면서 장기 실행 자손의 불필요한 호출자 FD는 분리한다.
- [x] 필요한 경계에 서비스별 출력 대상과 명시적인 FD 보존 계약을 적용한다. 기존 broker 관련 로그는 보존한다.
- [x] 격리된 인스턴스에서 최초 시작과 재시작 후 시작 결과·stdout/stderr EOF·잠금 해제를 확인하고, broker를 통한 클라이언트 접속과 SQL 성공을 함께 검증한다.
- [x] proxy가 관여하는 지원 구성의 생성·재시작 영향을 확인한다. 사용하지 않은 구성은 시험한 것처럼 보고하지 않는다.
- [x] 관련 실패 경로에서 기존 호출자 진단·실패 코드와 정상적인 출력 수집 종료를 확인한다.
- [x] 코드 변경이 불필요한 경계는 소스 근거와 회귀 결과를 남긴다. 실행하지 못한 적용 대상은 미검증으로 남기고 전체 broker 호환성 확보로 처리하지 않는다.
- [x] 지속 가능한 native shell 회귀 사례와 커밋·바이너리가 식별된 결과를 제공한다.

## Implementation notes

01의 공통 생성 정책과 동기 명령 호환성 계약을 사용한다. master나 HA 정책에 대한 독립적인 제품 의존성이 없는 한 02·05를 선행 조건으로 추가하지 않는다.

## Accepted result

Engine `928e3e503`, tests `b55b16a35`, native `qYsGp8`:1pass/0fail/0skip,1,822 matrix checks including495 broker,9 supplemental checks,18 installed/copied and90 actual fixture hashes. Main independently verified. [Report](../../../cbrd-27443/implementation/ticket07/report.md) and [review](../../../cbrd-27443/implementation/ticket07/review.md) retain gateway/Windows coverage limits and failed attempts.
