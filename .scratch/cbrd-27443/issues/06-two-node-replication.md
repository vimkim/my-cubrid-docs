# 06: 2-node 복제 프로세스 시작·재시작 처리

**What to build:** 2-node 환경에서 copylogdb·applylogdb가 시작 및 재시작 후 호출자 자원을 놓고, 실제 변경 내용이 대상 DB에 복제되도록 보장한다.

**Blocked by:** 05: single-node HA 시작·재시작 처리.

**Status:** resolved

**Parent:** CBRD-27443 — [합의된 스펙](../spec.md). 착수 전에 전체 스펙의 외부 계약·시험 원칙과 이 티켓에 해당하는 근거를 읽는다.

**Acceptance coverage:** A15; A03–A06의 복제 프로세스 영향 경계.

- [x] 05에서 정리한 HA 생성·진단 계약을 기준으로 copylogdb·applylogdb의 최초 실행과 재시작 경계를 조사하고 필요한 수정을 적용한다.
- [x] 서로 격리된 두 시험 노드의 설정·DB·로그·통신 대상을 식별하고 호스트 공유 서비스에 영향을 주지 않는 환경을 사용한다.
- [x] 각 시작 요청의 출력 수집이 끝나며 필요한 복제 프로세스가 살아 있음을 확인한다. 호출자 파이프·잠금 및 불필요한 부모 FD가 남지 않는다.
- [x] 시작 후 원본 DB의 변경이 대상 DB에 반영됨을 확인한다. copylogdb와 applylogdb 각각의 재시작 뒤에도 후속 변경이 반영되어야 한다.
- [x] 복제에 필요한 FD와 실행 중 통신을 보존하고, 실패 조건의 기존 호출자 진단·종료 코드를 유지한다.
- [x] 공통 생성 정책의 간접 영향까지 조사한다. 코드 변경이 필요 없다는 결론은 생성 경계 근거와 기능 검증으로 뒷받침한다.
- [x] 독립 실행 결과와 실제 커밋·바이너리 정보를 남긴다. 실행하지 못한 2-node 조건은 미검증으로 기록하며 다른 HA 시험의 통과로 대신하지 않는다.

## Implementation notes

05의 HA 시작·재시작 계약을 두 노드의 복제 도구로 확장하므로 05가 선행한다. 기존 분석에 2-node 독립 검증 결과가 없다는 점을 전제로 시험을 준비한다.

## Verified candidate — acceptance pending

Source `41ac0c2ce`, tests `8c1a1bc79`; exact native FvYAKF passed1/0/0 and1326 checks, including282 replication checks and11 records. Main independently verified the artifact verdict, assertions,10 installed/copied/per-node hashes and clean handoff. [Report](../../../cbrd-27443/implementation/ticket06/report.md) · [Review](../../../cbrd-27443/implementation/ticket06/review.md).

The fifth checkbox remains open: baseline local missing-executable copy/apply starts falsely return0; candidate returns1 while preserving the execv diagnostic. The user was asked to approve this explicit exception to exit-code preservation. No answer yet; status remains claimed, not resolved. Independent07 may proceed because its sole dependency01 is accepted.

## Final result — accepted

The historical pending paragraphs above are superseded by the compatibility correction at engineb0f569011/test26ab88a35. Exact nativeRGZgmT passes1/0/0 with1,843 checks,313 replication checks and11 actual replicated records. Main independently verified all assertions,18 installed/copied identities and90 actual fixture hashes. Baseline local copy/apply output/code match exactly; sibling codes and new setup-error precedence are preserved. [Corrected review](../../../cbrd-27443/implementation/ticket06/review.md#compatibility-correction-accepted). The unanswered exception is not required: the original approved code-preservation contract is implemented.
