# 새 통합 조합 CI 시작

2026-09-29 사용자 승인에 따라 엔진과 testcase를 게시하고 `/run all`을 한 번 요청했다.

| 구분 | 커밋 |
|---|---|
| 엔진 PR #7990 | fb567a629cdb390fff920542173fa36f454c74a0 |
| public testcase feature/oos-merge = tc/pr-7990 | bdba62aee0faec05abdd861518824c69b6c1b3c5 |
| private testcase feature/oos-merge = tc/pr-7990 | c4b9d482fbd491a68510b2552df2c3cac91911fc |

[실행 36570256001](https://github.com/CUBRID/cubrid/actions/runs/36570256001) · [요청 댓글](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-5890577215).

두 빌드와 medium/sql/shell의 `gha-ci:` 상태 5개가 모두 위 run에서 PENDING인 것을 확인했다. 필수 gha-ci context 4개 중 누락은 없다. 결과는 아직 대기 중이며 testcase SHA는 요청 시 원격 값이다. plan 및 최종 artifact가 실제 사용한 SHA는 후속 결과 수집에서 확인한다.

실시간 required 체크는 [기록](evidence/ci-pickup-required.json)에 보존했다. `Check TC PRs`는 testcase develop에 OOS testcase 변경이 아직 없어 실패한다. 새 CI의 필수 상태는 pending이다. 이는 기술적 준비나 최종 병합 가능 판정이 아니다.

소스 push 자동 빌드 run 36570061594도 별도로 있다. 현행 workflow의 push-SHA 그룹과 PR-7990-run 그룹은 분리되어 있어 새 PR CI 요청이 자동 빌드를 취소하지 않는다. 요청 직전 PR #7990의 다른 chatops run과 현재 head gha-ci 상태가 없음을 확인했다.

[요청 영수증](evidence/ci-trigger-receipt.json) · [접수 상태](evidence/ci-pickup-checks.json) · [testcase 통합 검증](evidence/tc-merge-validation.json).
