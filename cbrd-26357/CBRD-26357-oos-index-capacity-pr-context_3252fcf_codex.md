# PR 7990 본문 수정 검토 기록

검토일: 2026-10-22, Asia/Seoul. 작성 에이전트: `codex`.

## 대상과 식별 정보

- Ticket: `CBRD-26357`.
- Operation: existing PR body `update`.
- Target: [CUBRID/cubrid#7990](https://github.com/CUBRID/cubrid/pull/7990).
- Source repository: `CUBRID/cubrid`.
- Source branch: `feature/oos-merge`. Base: `develop`.
- SOURCE_COMMIT / observed remote head: `3252fcffce9762641fb9ae6f4a5d8ae89affc738`.
- 기존 제목: `[CBRD-26357] Add out-of-row overflow storage`. 제목 변경 제안 없음.
- 기존 상태: open, draft. 상태 변경 제안 없음.
- 원본 GitHub 본문 SHA-256: `48766466d29d76f7cf38f2db52b8af6d70e03f99be9d41be056e6440ef41df24`.
- 지문은 JSON에서 복원한 원본 body 문자열의 UTF-8 바이트로 계산했습니다. 줄바꿈을 추가하지 않았습니다.
- 원래 분석 head `1a8c705` 뒤에 PR #7927의 지연 OOS 쓰기 커밋이 추가됐습니다. 현재 head를 별도로 빌드해 수정 전후 TC를 재검증했습니다.

## 로컬 검토 자료

- Docs task branch: `docs/pr7990-index-capacity-20261022`.
- Docs integration branch: `main`.
- Body: `cbrd-26357/CBRD-26357-oos-index-capacity-pr-body_3252fcf_codex.md`.
- Context: `cbrd-26357/CBRD-26357-oos-index-capacity-pr-context_3252fcf_codex.md`.
- Detail: `cbrd-26357/CBRD-26357-oos-index-capacity_3252fcf_codex.md`.
- Index: `cbrd-26357/README.md`.
- Public explanation URL: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-oos-index-capacity_3252fcf_codex.md
- 기존 GitHub 본문은 그대로 두고 `Remarks`에 TC 변경 이유와 검증 결과를 추가합니다.
- TC repository: `CUBRID/cubrid-testcases-private-ex`.
- TC task branch: `fix/pr7990-oos-index-capacity-20261022`.
- TC task commit: `046d0e2f81e117df0592387983c978acaa411c68`.
- TC integration branch: `tc/pr-7990`.
- TC local destination before integration: `73e2b2f44f5ed79e1fad15bfaf55731959121a3d`.
- 기존 원격 TC tip `28ffb7365` 뒤에 로컬 default 보완 커밋 `73e2b2f44`가 있습니다. 아래 push는 default 보완과 이번 인덱스 기대값 보완을 모두 게시합니다.

## 검토 후 제안하는 작업

1. TC 작업 브랜치를 현재 로컬 `tc/pr-7990` 위로 rebase합니다. diff와 필요한 검증 후 fast-forward 병합합니다.
2. private TC 원격 `origin`의 `tc/pr-7990`으로 push합니다. 원격 변경이 있으면 먼저 차이를 확인합니다.
3. docs 작업 브랜치의 위 4개 파일을 현재 로컬 `main` 위로 rebase합니다. 전체 유입 이력과 링크를 확인한 뒤 fast-forward 병합하고 `origin/main`에 push합니다. 게시 결과 기록을 추가하는 최종 문서 커밋도 이 범위입니다.
4. 근거 문서의 공개 URL을 확인한 뒤 PR #7990 본문을 body 파일의 내용으로 갱신합니다. 제목과 draft 상태는 유지합니다.
5. 결과를 확인하고 위 TC/docs 작업 브랜치와 작업 트리만 정리합니다. 원격 브랜치를 삭제하지 않습니다.

엔진 소스 push, PR merge, CI 실행, JIRA 게시를 제안하지 않습니다.

## 게시 전 확인

이 문서는 승인 기록이 아닙니다. 준비된 파일과 위 작업 목록에 대한 사용자의 확인이 필요합니다.
PR head 또는 기존 본문이 바뀌면 차이를 반영해 다시 검토합니다. 승인 후 본문이 수정되면 새 본문도 다시 검토합니다.
검증 원본과 로컬 실행 경로는 work item `490`에 기록했습니다.
