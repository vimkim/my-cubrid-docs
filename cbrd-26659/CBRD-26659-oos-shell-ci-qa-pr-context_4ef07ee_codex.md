# CBRD-26659: CUBRID/cubrid-testcases-private-ex PR #4365 QA 설명 갱신 초안

작성: 2026-10-28 (Asia/Seoul). Agent: `codex`.

## 검토 대상

- Ticket: [CBRD-26659](https://jira.cubrid.org/browse/CBRD-26659).
- 대상 PR: [CUBRID/cubrid-testcases-private-ex#4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365). 작업: 기존 본문 `update`.
- 기존 제목: `[CBRD-26659] Draft: TC changes for PR CUBRID/cubrid#8128`. 제목 변경은 제안하지 않는다.
- 관측 상태: OPEN, Ready for review (`draft=false`). 상태를 유지한다.
- Source repository: `CUBRID/cubrid-testcases-private-ex`. Source branch: `tc/pr-8128`.
- SOURCE_COMMIT / 관측 remote HEAD: `4ef07ee34219a7dce7e5c5d84a2f6c6031b10ec3`.
- Base: `feature/oos-merge`, 관측 SHA `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`.
- 기존 GitHub body SHA-256: `7d4a5537bdd04487afc3972c8e14ed93cab48138bffa369a2a828c1cee283354`. API에서 디코딩한 UTF-8 body의 바이트 그대로 계산했으며 줄바꿈을 추가하지 않았다.
- 이번 body 파일 SHA-256: `7af46c51dd40ebf5738bebfb8678365d10d3d1eac74335e4d7f8ec8c26b90bcd`. 게시 시에는 사용자가 검토한 파일의 현재 바이트를 다시 읽고 해시를 확인한다.

## 저장한 문서

- Body: [CBRD-26659-oos-shell-ci-qa-pr-body_4ef07ee_codex.md](CBRD-26659-oos-shell-ci-qa-pr-body_4ef07ee_codex.md). 이 파일 전체가 업로드 대상 본문이다.
- 시간 비교·근거: [CBRD-26659-tc-ci-runtime-comparison_20261028_codex.md](CBRD-26659-tc-ci-runtime-comparison_20261028_codex.md).
- Docs repository: `vimkim/my-cubrid-docs`; task branch: `docs/oos-ci-timing-20261028`; integration branch: `main`.
- 새 상세 설명의 public URL을 본문에 추가하지 않았다. 본문의 근거 링크는 기존 GitHub CI·PR 및 커밋 고정 TC 파일을 사용한다.

## 변경 범위와 사실 확인

- 사용자가 요청한 47분 기준 대비 시간 변화, 일반 CI의 대표 TC 선별, 비활성 실패의 원인 규명·수정·재활성화, 유용한 개별 60초 초과 TC의 QA 장시간 suite 편입 방침을 반영한다.
- 47분 14초와 57분 00초는 서로 다른 리비전·실행 조건의 관측 차이다. 머지 후 고정 비용이나 TC 추가만의 인과적 비용으로 표시하지 않는다.
- PR #7990의 최신 성공 실행은 shell 699개만 재실행했다. 본문의 전체 성공 기준 40349442612와 구분한다.
- 기존 본문의 초기 HEAD·과거 CI·HA 보류 상태는 현재 근거로 갱신한다. SQL/answer와 assertion 보존, 비활성 실패에 PASS를 부여하지 않는 원칙, 성능 비교의 후속 범위는 유지한다.
- Engine `e3589ae`, public TC `45e21ad`, private TC `479035a`에서 전체 CI40643373124가 SUCCESS였다. Private 최신 `4ef07ee`는 이후 HA helper 설명 주석만 수정했다. 새 HEAD에서 CI를 다시 수행했다고 주장하지 않는다.
- Public은 SQL 28쌍(활성25·비활성3), private은 기존 shell133개와 HA6개를 합해139개(활성73·비활성66)다. 기존133개 inventory와 현재139개 보유 수를 구분한다.
- Body 초안 작성은 실제 TC 선별·이전·실패 수정, QA 연락 또는 CI 재실행을 수행하지 않는다. Work543의 QA 협의·실행·리뷰·실제 TC 병합 완료 조건은 남아 있다.

## 검토 후 제안하는 게시 작업

현재는 초안 작성 단계이며 아래 작업의 승인을 기록한 문서가 아니다. 사용자의 대화상 명시적 승인 후에만 수행한다.

1. 원격 PR HEAD·base·제목·본문 fingerprint와 사용자가 검토한 파일을 다시 확인한다. HEAD나 기존 본문이 달라지면 조정 후 다시 검토받는다.
2. 관련 문서 변경 전체를 현재 docs `main`에 rebase하고 검산·링크·선택 파일을 확인한 뒤 fast-forward merge한다. 대상 파일은 아래 목록이며 필요 실행 기록도 같은 문서 워크플로를 따른다. `origin/main`에 push하고 내용 반영을 확인한다.
3. 이 context가 가리키는 PR #4365의 body를 검토된 body 파일 전체로 교체한다. 나머지 두 PR도 각 context의 정확한 대상·파일을 사용한다. Source·TC branch push는 필요하지 않다.
4. 게시 결과를 다시 읽어 body 해시, 기존 제목, OPEN/Ready 상태가 의도대로인지 확인한다. PR merge·close·branch 삭제·CI trigger는 제안 작업에 포함하지 않는다.

함께 검토할 docs 변경:

- `cbrd-26659/README.md`
- `cbrd-26659/CBRD-26659-tc-ci-runtime-comparison_20261028_codex.md`
- `cbrd-26659/CBRD-26659-oos-tc-ci-qa-pr-body_e3589ae_codex.md`
- `cbrd-26659/CBRD-26659-oos-sql-ci-qa-pr-body_45e21ad_codex.md`
- `cbrd-26659/CBRD-26659-oos-shell-ci-qa-pr-body_4ef07ee_codex.md`
- `cbrd-26659/CBRD-26659-oos-tc-ci-qa-pr-context_e3589ae_codex.md`
- `cbrd-26659/CBRD-26659-oos-sql-ci-qa-pr-context_45e21ad_codex.md`
- `cbrd-26659/CBRD-26659-oos-shell-ci-qa-pr-context_4ef07ee_codex.md`
