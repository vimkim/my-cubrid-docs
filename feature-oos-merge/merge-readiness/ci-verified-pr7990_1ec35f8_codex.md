# PR #7990 CI 검증 결과 — 1ec35f8

2026-09-29 수집. 정확한 엔진 커밋: `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21`. 수집기 0.2.0 (45944012aaaa). 최초 구버전 수집의 한계는 보존하고, 별도 깨끗한 증거 디렉터리의 새 수집을 검증했다.

command/manifest/observation 식별, 모든 schema, raw 파일의 크기·SHA256, summary 연결 hash, 실행·판정 집계, failure metadata를 검증했다. 분석 모드 full. 바이너리 수집은 요청하지 않았다. 이 검증은 CI 자료의 진위를 확인하며 실패 원인을 자동으로 확정하지 않는다.

| Suite | 실행 / 통과 / 실패 / skip | Run / attempt | 테스트 리비전 |
|---|---|---|---|
| test_medium | 975 / 975 / 0 / 0 | [36104247286/1](https://github.com/CUBRID/cubrid/actions/runs/36104247286) | 89d4ec2423d94b973b5f9cf0c612c9576b9ccce6 |
| test_shell | 3258 / 3256 / 2 / 30 | [36104247286/1](https://github.com/CUBRID/cubrid/actions/runs/36104247286) | 1274a4d6462a3d5ae5daeb004e042f89496991d8 |
| test_sql | 17470 / 17470 / 0 / 0 | [36104247286/1](https://github.com/CUBRID/cubrid/actions/runs/36104247286) | 89d4ec2423d94b973b5f9cf0c612c9576b9ccce6 |

## 실패 목록

| Suite | 테스트 | 판단 | 증거 |
|---|---|---|---|
| test_shell | shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh | 합의된 CDC 연기 범위. 추출 실패 관측; 이 수집만으로 내부 원인 확정 안 함 | [message 원본(gzip)](evidence/pr7990-failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/message.txt.gz) · [diff](evidence/pr7990-failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/diff.txt) |
| test_shell | shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh | 합의된 CDC 연기 범위. 추출 실패 관측; 이 수집만으로 내부 원인 확정 안 함 | [message 원본(gzip)](evidence/pr7990-failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt.gz) · [diff](evidence/pr7990-failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/diff.txt) |

## 원인 판단과 다음 검증

관측: 실패 목록과 diff는 위 exact revision의 자료다. PR 관계는 내부 원인 기준 unknown, 관측 신뢰도는 높지만 인과 신뢰도는 미확정이다. CDC 두 건은 ADR-0005의 명시적 연기 범위에 해당한다. 동일 증상이 develop 또는 부모에서 재현되는지는 별도 비교가 필요하다.

현재 head의 실패 2건 외에 추가 CI 실패는 없다. 과거 bug_bts_13242는 현재 CI 실패 목록에 없다. cbrd_27064는 rc=-10 추출 오류, cbrd_27075는 추출 검증 NOK가 관측됐다. 기존 CDC 예외와 증상을 대조하고 다른 원인이 확인되면 연기 분류를 재검토한다. 새 통합 후보 fb567a6는 아직 이 CI 결과의 대상이 아니다.

증거 디렉터리: `/home/vimkim/tmp/oos-readiness-221/ci-clean/github-actions/CUBRID-cubrid/pr-7990/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21`. Observation: `/home/vimkim/tmp/oos-readiness-221/ci-clean/github-actions/CUBRID-cubrid/pr-7990/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/observations/20260929T121735.027974637Z-3597887-0/result.json`. 원본 testcase는 각 summary shard의 SHA로 로컬 git show를 통해 존재를 확인했다.
