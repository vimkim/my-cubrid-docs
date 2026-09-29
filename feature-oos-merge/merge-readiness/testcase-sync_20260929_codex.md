# Testcase 브랜치 갱신과 CI 동기화

**후속 처리 완료:** 사용자 승인 후 두 develop 통합을 실제 merge commit으로 게시했다. public `bdba62aee0fa`, private `c4b9d482fbd4`이며 각각 `feature/oos-merge`와 `tc/pr-7990`의 원격 SHA가 일치한다. 충돌 없이 통합됐고 OOS 전용 파일 5개/19개를 그대로 보존했다. 변경된 shell 16개는 bash 구문 검사에 통과했다. 엔진 `fb567a6` 게시 후 `/run all`을 요청했다. [통합 검증](evidence/tc-merge-validation.json) · [동기화 실행](evidence/tc-sync-publish.log) · [CI 요청](evidence/ci-trigger-receipt.json).

아래는 실행 전 확인 기록이다. 2026-09-29 원격 fetch 후 확인했다. `cubrid-pr-tc-sync-check-oos` 실행 결과 양쪽 저장소에서 `feature/oos-merge`와 `tc/pr-7990`은 이미 같은 커밋이다. 원격 또는 로컬 testcase 브랜치를 이동시키지 않았다.

| 저장소 | feature/oos-merge = tc/pr-7990 | 최신 develop | 아직 통합되지 않은 develop 커밋 |
|---|---|---|---|
| public | 89d4ec2423d9 | 62d4866ef36b | 8 |
| private | 1274a4d6462a | c8880167e176 | 6 |

두 비교 모두 이력이 갈라져 있으므로 develop로 단순 fast-forward하거나 testcase OOS 변경을 덮어쓰면 안 된다. OOS 변경을 보존하는 통합과 충돌 검토가 필요하다. 원본 QA 및 CI에 쓰인 기존 testcase SHA는 역사적 증거로 유지한다.

## 필요한 순서

1. 각 testcase 저장소의 `develop` 추가 변경을 대응 엔진 변경과 비교한다. OOS testcase `feature/oos-merge`에 필요한 최신 변경을 통합하고 논리 검증을 유지한다.
2. 통합한 testcase source branch를 게시한 뒤 `cubrid-pr-tc-sync-check-oos`로 두 저장소의 `tc/pr-7990`을 같은 SHA로 맞춘다. 이 도구는 behind일 때 일반 fast-forward push를 제안하며 target-ahead/diverged이면 중단한다. develop 병합을 대신하지 않는다.
3. source와 target의 원격 SHA 일치를 다시 확인한 뒤 PR #7990 CI를 실행한다. 엔진 커밋뿐 아니라 public/private testcase SHA도 새 결과에 고정한다.
4. PR #7927은 별도의 `tc/pr-7927`이므로 따로 확인한다. OOS wrapper는 이 브랜치를 다루지 않는다. 기존 PR 전용 변경을 살펴보고 유지하며, 일괄 덮어쓰지 않는다.

현재 gha-ci.yml은 PR 번호로 `tc/pr-<번호>`를 선택하고 plan 단계에서 정한 testcase SHA를 shard가 사용한다. 따라서 엔진만 갱신하고 testcase를 오래된 상태로 두면 새 CI도 오래된 corpus를 실행한다.

## 실패 조사에 관련된 새 변경

public에는 CBRD-27365 tuple-format 대응, CCI AUTO_INCREMENT 기대값(CBRD-26983), CCI join/order-by 및 HA catalog 기대값 수정, 새 parallel join 회귀 등이 있다. private에는 CBRD-27365와 DBLink 기대값(CBRD-27363), cbrd_26354 LIMIT-bounded NL join card 기대값, cbrd_24501의 cost/card 자릿수 의존 제거 등이 있다.

이는 기존 Q01·S02·S04 등의 재검토에 직접 관련된다. 커밋 제목 또는 upstream 기대값 변경의 존재만으로 기존 실패가 해결됐다고 확정하지 않는다. 엔진 변경과 testcase 의도를 검토한 뒤 최종 조합에서 원본 논리 조건을 검증해야 한다. 이번 확인에서는 testcase 수정·병합·게시나 추가 실행을 하지 않았다.

PR #7927의 현재 원격 testcase는 public `9fae5aa61a05`, private `44a541c78a3e`로, 보고서의 과거 CI가 실행한 `7fb2278`/`018fc45`와 다르다. 과거 실패 14건은 해당 당시 revision의 증거이며 현재 testcase 조합의 실패 수로 재사용하지 않는다.

[동기화 명령 출력](evidence/tc-sync-check.log) · [정확한 SHA와 추가 커밋 목록](evidence/tc-branch-state.json). 도구 소스: `/home/vimkim/my-cubrid/bin/cubrid-pr-tc-sync-check-oos`, `/home/vimkim/my-cubrid/bin/cubrid-pr-tc-sync-check`.
