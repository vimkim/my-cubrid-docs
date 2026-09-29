# develop 동기화 커밋 게시 준비

현재 원격 `feature/oos-merge`는 `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21`, develop은 `f1bd99ed43a134383bc0be1d766a6f121601a499`이다. 2026-09-29 21:30 KST에 다시 확인했다.

게시 대상은 로컬 `integration/oos-readiness-221`의 `fb567a629cdb390fff920542173fa36f454c74a0`이다. 두 부모는 위 OOS head와 develop이다. 목적은 develop의 11개 커밋을 기존 OOS 이력을 보존해 통합하는 것이다. 별도 기능 패치와 테스트 실행기 수정은 없다. 새 기능 선행 PR은 이후 정해진 순서로 처리한다.

게시 목적지는 CUBRID 조직 origin의 `refs/heads/feature/oos-merge`다. 원격 head를 다시 확인하고 일반 fast-forward push를 사용한다. force, rebase, amend는 사용하지 않는다. 원격이 달라졌으면 새 이력을 확인해 재통합·검증한다. 게시 후 PR #7990의 exact head와 필요한 CI 상태를 확인하고 해당 head의 필수 검증을 진행한다.

이 동작은 `feature/oos-merge` → `develop` 병합이 아니다. 전체 QA, #7927, CBRD-27057, CBRD-27230/27237 및 비CDC 미확정 실패가 여전히 남아 있다. [통합 검토](integration-review_fb567a6_codex.md), [로컬 검증](local-validation_fb567a6_codex.md).

## 남아 있는 게시 승인 조건

기존 합의 `/home/vimkim/gh/cb/feature-oos-merge/.scratch/oos-develop-merge-repair/review.md:145`는 “Stop before the first push for explicit publication approval.”라고 명시한다. 이번 [실행 계약](execution-contract.md)의 게시 절도 이 조건이 아직 유효하면 구체적인 결과를 준비한 뒤 처리하도록 한다. 따라서 준비된 이 커밋의 첫 source push에 대한 확인을 남긴다. 문서 작성 또는 이전 docs-only 게시 승인을 source 게시 승인으로 바꾸지 않는다.
