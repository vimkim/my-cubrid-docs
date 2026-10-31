# CBRD-27785 TODO 체크리스트

작성일은 2026-10-29, 현재 PR·TC 상태 확인일은 2026-10-31, Asia/Seoul이다.
대상은 [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785)의 구현 반영, 성능 수락, performance TC 편입이다.
현재 구현·CI와 최신 문서·PR 본문 게시를 완료했다. 사람의 TC 종료 처리와 PR 리뷰·병합 판단이 남았다.

확인한 소스는 `vimkim/cubrid:CBRD-27785-oos-read-performance`의 `067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65`다.
[PR #8299](https://github.com/CUBRID/cubrid/pull/8299)는 OPEN draft이며 대상은 `feature/oos-merge`다.
구현·CI 완료를 이슈 전체 수락 완료로 표시하지 않는다.

## 완료한 항목

- [x] 공통 reader·경계 검사 개선 및 `067aae4e4` push.
- [x] 엄격한 GCC 8.5 컴파일 검증과 집중 테스트 통과.
- [x] [전체 CI run 40827634555](https://github.com/CUBRID/cubrid/actions/runs/40827634555) 통과. Release·debug 빌드, shell 50개, SQL 10개, medium 1개 shard가 통과했다.
- [x] 기존 성능 측정 결과·원시 자료·보고서 초안 보존.

## 지금 처리할 항목

- [x] PR 본문과 보고서의 새 초안을 `067aae4e4` 및 CI 성공 상태에 맞춰 준비한다. 성능 수치는 실제 측정 revision을 유지한다.
- [x] 갱신한 문서·본문의 검토 및 게시 승인을 받는다.
- [x] 승인받은 보고서를 게시한 뒤 PR #8299 본문을 업데이트한다.
- [ ] TC 변경이 불필요한 [공개 TC PR #3898](https://github.com/CUBRID/cubrid-testcases/pull/3898)과 [비공개 TC PR #4589](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4589)를 사람이 닫아 TC gate를 해소한다.
- [ ] PR 리뷰를 요청하고 승인을 확보한다.
- [ ] 승인 후 PR #8299를 `feature/oos-merge`에 반영한다.

2026-10-31 조회에서 TC PR 두 개는 모두 OPEN draft이며 diff가 없다.
Engine PR은 OPEN draft, MERGEABLE/CLEAN이고 현재 head의 CI 10개가 모두 성공했다.
이 GitHub mergeState가 사람의 TC 처리나 리뷰어 승인을 대신하지 않는다.
[게시한 본문](CBRD-27785-common-reader-pr-body_067aae4_codex.md),
[근거 보고서](CBRD-27785-common-reader_067aae4_codex.md),
[게시 context](CBRD-27785-common-reader-pr-context_067aae4_codex.md)를 검토할 수 있다.
본문과 보고서의 게시·일치 검증은 context의 실행 기록에 있다.
PR의 title·base·draft 상태는 유지했으며 TC PR 종료나 engine PR 병합은 수행하지 않았다.

## 성능 수락 항목

- [ ] 최종 통합 head에서 **AC-P1 일반 테이블 성능**을 확인하고 충족·미달 판정을 기록한다.
- [ ] **AC-P3 이득·손해 보고**에 overflow→OOS 비교와 [CBRD-27788](https://jira.cubrid.org/browse/CBRD-27788) 결과를 연결하고 리뷰어 수락을 확인한다.
- [ ] 성능 regression TC의 시나리오·지표·판정 기준·runner 승인을 받는다. 작업 544에서 추적한다.
- [ ] 승인한 TC를 구현·검증하고 performance 영역에 리뷰·병합한다. 일반 SQL·shell·medium CI 및 기본 PR CI 자동 선택에서는 제외한다.
- [ ] JIRA에 최신 구현·CI·성능 판정·리뷰어 수락 근거를 반영하고 완료 여부를 판단한다.

AC-P1·P3의 비교 범위와 판정은 [성능 수락 기준](CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md)을 참고한다.
기존 SELECT 개선이나 CI 통과만으로 나머지 CRUD와 현재 통합 head까지 통과했다고 기록하지 않는다.
추가 CRUD의 조사·검증 범위는 합의한 범위로 관리한다.

## 후속으로 분리해 유지할 항목

- [ ] [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816), 작업 571에서 UPDATE 잔여 비용과 변동을 분석한다. 엄격한 +2% 목표는 완료 처리하지 않는다.
- [ ] **AC-P2**의 threshold 지원·저장 경계를 확인한 뒤 동일 저장 정책으로 재측정한다. 현재 단계의 필수 조건으로 다시 추가하지 않는다.

AC-P2는 기존 overflow처럼 행이 페이지 크기를 넘을 때 OOS로 보내는 설정을 확인한 뒤 측정한다.
Parameter의 실제 이름·지원 상태·필요 구현을 먼저 확인한다.
[CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791)의 읽기 지역성 개선은 별도 이슈 범위를 유지한다.

## 연결된 작업 기록

| 작업 | 용도 | 확인한 상태 |
| --- | --- | --- |
| 584 | PR #8299 검증과 문서·게시 인계 | 컴파일 수정·CI·문서·본문 게시 완료. 사람의 TC 종료 및 리뷰·병합 판단 대기. |
| 544 | 성능 regression TC 승인·performance 편입 | Pending. |
| 571 | CBRD-27816 UPDATE 잔여 비용·변동 분석 | Pending. |

2026-10-29에 기록한 JIRA 상태는 Develop, Resolution은 Unresolved였다.
2026-10-31의 실시간 조회는 DNS 오류로 실패했으므로 현재 상태는 미확인이다.
실제 리뷰어 답변이나 승인 근거가 생겼을 때 해당 항목을 완료 표시한다.
