# CBRD-27785: OOS 통합 후 일반 행 읽기와 UPDATE 성능

관련 이슈: [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785).
관련 PR: [OOS 통합 PR #7990](https://github.com/CUBRID/cubrid/pull/7990).
성능 수정: [draft PR #8299](https://github.com/CUBRID/cubrid/pull/8299).
대상은 `feature/oos-merge`다.
작성일: 2026-10-27. 수정일: 2026-10-29, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [TODO 체크리스트](CBRD-27785-todo-checklist.md) | 완료한 구현·CI와 남은 문서·TC gate·성능 수락·후속 작업 | 2026-10-29 | 2026-10-29 | CBRD-27785의 남은 작업과 완료 조건을 한곳에서 추적하기 위해 |
| [읽기 최적화 코드 해설서](CBRD-27785-code-walkthrough_f1b99031c_codex.md) | f1b99031c 읽기 diff의 전후 흐름도, 함수 책임, COPY·버퍼 수명, 테스트와 예상 질문 | 2026-10-29 | 2026-10-29 | 팀원이 읽기 변경을 이해하고 코드 리뷰 질문에 답하도록 돕기 위해 |
| [발표 연습 질문 모음](CBRD-27785-learning-questions_f1b99031c_codex.md) | 선택한 질문과 첫 답변·재답변, 접힌 교정·발표용 답변·근거, 학습 상태 | 2026-10-29 | 2026-10-29 | 좋은 질문을 다시 풀고 팀원 설명에 필요한 근거 구분을 연습하기 위해 |
| [공통 reader·UPDATE 개선](CBRD-27785-shared-read-update_408d135_codex.md) | 실제 develop·feature·HEAD 3-way 측정과 개별 counter, 약 +5% 수용 결정과 CBRD-27816 후속, 검증과 한계 | 2026-10-28 | 2026-10-28 | 지금까지 확보한 개선을 PR #8299 하나로 검토하기 위해 |
| [통합 PR 본문](CBRD-27785-shared-read-update-pr-body_408d135_codex.md) | 기존 #8299에 반영할 한국어 본문과 3-way 전후 수치 | 2026-10-28 | 2026-10-28 | 게시 전 변경 범위와 미달 기준을 검토하기 위해 |
| [통합 게시 context](CBRD-27785-shared-read-update-pr-context_408d135_codex.md) | source SHA와 승인 본문 fingerprint, 게시·전체 CI 성공 및 남은 TC gate | 2026-10-28 | 2026-10-28 | 검토한 자료만 승인 후 게시하기 위해 |
| [두 축 코드 검토](CBRD-27785-pr8299-review_408d135_codex.md) | Standards·Spec 독립 검토와 각 0건의 발견사항, 정적 검토의 한계 | 2026-10-28 | 2026-10-28 | 게시할 최종 diff를 규칙과 요구사항 양쪽에서 검토하기 위해 |
| [PR7990 성능 수락 기준](CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md) | 1·3번 우선·잠정 +2% 기준, 2번 threshold 설정 후 재측정 방향과 AC | 2026-10-28 | 2026-10-28 | 최신 성능 요구를 CBRD-27785의 수락 조건으로 추적하기 위해 |
| [분석과 검증](CBRD-27785-oos-read-performance_bcb900d_codex.md) | 원인, 읽기 계약, 세 저장 경로 구분과 최종 측정·검증 | 2026-10-27 | 2026-10-27 | 일반 heap 읽기 수정의 근거와 범위를 검토하기 위해 |
| [PR 본문](CBRD-27785-oos-read-performance-pr-body_bcb900d_codex.md) | 게시할 한국어 PR 설명 | 2026-10-27 | 2026-10-27 | GitHub 게시 전 본문을 검토하기 위해 |
| [게시 context](CBRD-27785-oos-read-performance-pr-context_bcb900d_codex.md) | source SHA, branch, 승인 범위와 검증한 게시 결과 | 2026-10-27 | 2026-10-27 | 승인 후 정확한 revision과 작업으로 이어가기 위해 |
