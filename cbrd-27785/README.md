# CBRD-27785: OOS 통합 후 일반 행 읽기와 UPDATE 성능

관련 이슈: [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785).
관련 PR: [OOS 통합 PR #7990](https://github.com/CUBRID/cubrid/pull/7990).
성능 수정: [draft PR #8299](https://github.com/CUBRID/cubrid/pull/8299).
대상은 `feature/oos-merge`다.
작성일: 2026-10-27. 수정일: 2026-10-31, Asia/Seoul.

성능을 비교할 때 DB 생성 locale과 실제 테이블·컬럼의 charset·collation을 확인한다.
기존 기록에서 누락된 조건은 미확인으로 두며, 다른 문자셋에 수치를 일반화하지 않는다.
필수 기록은 [문자셋을 포함한 비교 조건](CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md#charset-conditions)에 있다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [TODO 체크리스트](CBRD-27785-todo-checklist.md) | 구현·CI·본문 초안 준비 완료와 남은 게시·사람의 TC 종료·성능 수락 | 2026-10-29 | 2026-10-31 | CBRD-27785의 남은 작업과 완료 조건을 한곳에서 추적하기 위해 |
| [현재 공통 reader 구현·CI와 과거 성능](CBRD-27785-common-reader_067aae4_codex.md) | 067aae4 구현·CI, fd8624c 선택 계수와 문자셋·UPDATE·재현 한계 | 2026-10-31 | 2026-10-31 | 현재 head와 실제 측정 revision을 구분해 PR 본문을 정리하기 위해 |
| [현재 head의 PR 본문 초안](CBRD-27785-common-reader-pr-body_067aae4_codex.md) | PR8299에 게시할 구현·CI·과거 성능 범위와 남은 TC 처리 | 2026-10-31 | 2026-10-31 | 변경된 본문을 사용자 검토 후 정확히 게시하기 위해 |
| [현재 head의 게시 context](CBRD-27785-common-reader-pr-context_067aae4_codex.md) | source·본문 fingerprint, 선택 자료와 docs·본문 게시 제안 | 2026-10-31 | 2026-10-31 | 게시 승인 범위와 실제 실행 결과를 추적하기 위해 |
| [읽기 최적화 코드 해설서](CBRD-27785-code-walkthrough_f1b99031c_codex.md) | f1b99031c 읽기 diff·COPY·버퍼 수명과 성능 수치를 설명할 때의 문자셋 조건 | 2026-10-29 | 2026-10-31 | 팀원이 읽기 변경을 이해하고 코드 리뷰 질문에 답하도록 돕기 위해 |
| [보고서 학습 진행표](CBRD-27785-teaching-progress_f1b99031c_codex.md) | 질문 없이 T01부터 T11까지 설명 제공 완료, 발표 원고 연결과 원댓글 재현의 한계 | 2026-10-30 | 2026-10-31 | 설명 진도를 유지하고 다음 대화에서 남은 범위부터 이어가기 위해 |
| [읽기 최적화 발표 원고와 예상 답변](CBRD-27785-presentation_f1b99031c_codex.md) | f1b99031c의 5분 가안 원고, 예상 팀원 질문 12개와 코드·측정·재현 범위 구분 | 2026-10-31 | 2026-10-31 | 학습한 읽기 최적화를 팀원에게 설명할 발표와 답변을 준비하기 위해 |
| [원댓글 4라운드 재현과 문자셋 비교](CBRD-27785-reviewer-reproduction_4408135c_20261031_codex.md) | 원문 SQL의 UTF-8·ISO-8859-1 640회 실행, 실제 계수·범위와 전체 수치 재현 미확인 판정 | 2026-10-31 | 2026-10-31 | 재구성 실험과 원문 절차 재실행을 구분하고 수치 불일치를 검증하기 위해 |
| [발표 연습 질문 모음](CBRD-27785-learning-questions_f1b99031c_codex.md) | 이전 질문형 진행의 첫 답변·재답변, 접힌 교정·발표용 답변·근거와 진행표 연결 | 2026-10-29 | 2026-10-30 | 좋은 질문을 다시 풀고 팀원 설명에 필요한 근거 구분을 연습하기 위해 |
| [공통 reader·UPDATE 개선](CBRD-27785-shared-read-update_408d135_codex.md) | develop·feature·HEAD 3-way와 개별 counter, 문자셋 검증 한계·잔여 비용과 CBRD-27816 후속 | 2026-10-28 | 2026-10-31 | 지금까지 확보한 개선을 PR #8299 하나로 검토하기 위해 |
| [통합 PR 본문](CBRD-27785-shared-read-update-pr-body_408d135_codex.md) | 기존 #8299에 반영할 한국어 본문과 3-way 전후 수치 | 2026-10-28 | 2026-10-28 | 게시 전 변경 범위와 미달 기준을 검토하기 위해 |
| [통합 게시 context](CBRD-27785-shared-read-update-pr-context_408d135_codex.md) | source SHA와 승인 본문 fingerprint, 게시·전체 CI 성공 및 남은 TC gate | 2026-10-28 | 2026-10-28 | 검토한 자료만 승인 후 게시하기 위해 |
| [두 축 코드 검토](CBRD-27785-pr8299-review_408d135_codex.md) | Standards·Spec 독립 검토와 각 0건의 발견사항, 정적 검토의 한계 | 2026-10-28 | 2026-10-28 | 게시할 최종 diff를 규칙과 요구사항 양쪽에서 검토하기 위해 |
| [PR7990 성능 수락 기준](CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md) | 1·3번 우선·잠정 +2% 기준, 문자셋·초기 상태·계수 경계와 AC | 2026-10-28 | 2026-10-31 | 최신 성능 요구를 CBRD-27785의 수락 조건으로 추적하기 위해 |
| [분석과 검증](CBRD-27785-oos-read-performance_bcb900d_codex.md) | 원인·읽기 계약·저장 경로와 당시 측정 결과, 문자셋 조건의 검증 한계 | 2026-10-27 | 2026-10-31 | 일반 heap 읽기 수정의 근거와 범위를 검토하기 위해 |
| [PR 본문](CBRD-27785-oos-read-performance-pr-body_bcb900d_codex.md) | 게시할 한국어 PR 설명 | 2026-10-27 | 2026-10-27 | GitHub 게시 전 본문을 검토하기 위해 |
| [게시 context](CBRD-27785-oos-read-performance-pr-context_bcb900d_codex.md) | source SHA, branch, 승인 범위와 검증한 게시 결과 | 2026-10-27 | 2026-10-27 | 승인 후 정확한 revision과 작업으로 이어가기 위해 |
