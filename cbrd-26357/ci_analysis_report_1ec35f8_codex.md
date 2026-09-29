# PR #7990 CI 수집 경고 — 1ec35f8

2026-09-29 최초 수집. 정확한 커밋: `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21`.

**이 수집 자료는 회귀 또는 원인 결론을 지원하지 않는다.** 설치된 수집기 0.2.0 (31bd609fda78)는 현재 규격의 observation 기록을 만들지 않았고, 세 suite의 raw index에 필수 summary_sha256이 없다. 보고 모드는 warning이다.

| Suite | 자료가 보고한 상태 | 통과 / 실패 / skip |
|---|---|---|
| test_medium | completed / pass | 975 / 0 / 0 |
| test_sql | completed / pass | 17470 / 0 / 0 |
| test_shell | completed / fail | 3256 / 2 / 30 |

원격 실행은 [36104247286 / attempt 1](https://github.com/CUBRID/cubrid/actions/runs/36104247286)이다. 식별된 실패명은 cbrd_27064와 cbrd_27075이다. 이 명칭만으로 원인을 확정하지 않는다. command/manifest의 PR·commit 식별과 schema는 일치하며 개별 summary schema와 숫자 합은 확인했다. 전체 bundle 검증은 위 누락으로 실패했다.

관측 원장 부재로 shard 획득을 retained/failed/not_attempted로 판정할 수 없다. 바이너리 수집은 요청하지 않았다. 어떤 누락도 테스트 통과로 바꾸지 않는다.

증거: `/home/vimkim/tmp/oos-readiness-221/evidence/ci-result.json`, `ci-validation.json`, `ci-assessment.json`.

다음 조치: 이미 로컬에 있는 증거 검증 강화 커밋 4594401의 수집기를 별도 빌드하여 새 수집을 수행한다. 테스트 실행기 코드 변경이나 CI 재실행은 하지 않는다. 최초 자료와 한계는 보존한다.

## 후속 검증 — 2026-09-29

위 최초 수집의 warning을 보존한다. 기존 collector 소스 45944012aaaa를 수정 없이 빌드하고 별도 빈 data-dir에 재수집한 결과는 full 검증을 통과했다. 현재 exact-head의 상세 결과는 [후속 보고서](/home/vimkim/gh/my-cubrid-docs-oos-readiness-221/feature-oos-merge/merge-readiness/ci-verified-pr7990_1ec35f8_codex.md)에 있다. 이 후속 검증은 새 통합 후보 fb567a6의 CI가 아니다.
