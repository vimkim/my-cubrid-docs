# CBRD-27925 조사 기록

Last modified: 2026-11-10 (Asia/Seoul).

[CBRD-27925](https://jira.cubrid.org/browse/CBRD-27925)는 PR [#7990](https://github.com/CUBRID/CUBRID/pull/7990)의 OOS 빈 페이지 반환·재시도 후속 작업이다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [adr0008-scope.md](adr0008-scope.md) | 승인된 ADR-0008과 현재 소스 비교, gate 전용 작업의 축소, 남는 undo·래치·힌트·성장 의무와 최소 재현 범위 | 2026-11-05 | 2026-11-05 | Work816에서 후속 조사와 별도 DB 재현이 여전히 필요한지 판단하기 위해 |
| [adr0008-claude-review.md](adr0008-claude-review.md) | Work816 전제의 독립 재검토: READ 경합의 설계 해소 제안, fast path 후보 재연결 의무, 과거 두 VPID 해석, 무성장 eventual return 결정 | 2026-11-05 | 2026-11-05 | Work818에서 ADR-0008 이후 범위를 더 줄일 수 있는지 독립 확인하기 위해 |
| [explore_sweep_lap.py](explore_sweep_lap.py) | INSERT undo와 sweep lap의 전수 interleaving 순수 모델(소스 SHA 고정) | 2026-11-05 | 2026-11-05 | adr0008-claude-review.md의 모델 근거 |
| [growth-bound-design.md](growth-bound-design.md) | 성장 전 회수 규칙의 비용 원인, 다섯 설계의 TLA+ 비교(현재 규칙·유계 성장·헛된 검사), 빈 페이지 후보 집합 권고, READ 경합 (a)/(b) 결정, TC 여유분 판정과 a01 관측 | 2026-11-05 | 2026-11-05 | Work821에서 강한 회수 규칙이 INSERT/UPDATE 성능을 해치는지와 더 약한 유계 성장 보장을 검토하기 위해 |
| [jira-growth-bound-drafts.md](jira-growth-bound-drafts.md) | CBRD-27925·CBRD-26659 보충 댓글 초안과 게시 기록(4778015, 4778016) | 2026-11-05 | 2026-11-06 | 위 결론을 JIRA에 알린 기록 |
| [growth-gate-guide.md](growth-gate-guide.md) | 성장 게이트 입문: 옛 삭제 카운터·전체 sweep의 비용과 rollback 경합, 빈 페이지 후보 집합(ADR-0010, PR #8434 head `8e139f4db`)의 넣기·빼기·unknown 규칙, 성장 lock과 재확인 보강, C안 재사용 우선과의 차이, 점검 문제 | 2026-11-09 | 2026-11-10 | Work840 작업의 배경을 처음 보는 독자에게 설명하기 위해 |
