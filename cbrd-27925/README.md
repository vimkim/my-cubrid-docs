# CBRD-27925 조사 기록

Last modified: 2026-11-05 (Asia/Seoul).

[CBRD-27925](https://jira.cubrid.org/browse/CBRD-27925)는 PR [#7990](https://github.com/CUBRID/CUBRID/pull/7990)의 OOS 빈 페이지 반환·재시도 후속 작업이다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [adr0008-scope.md](adr0008-scope.md) | 승인된 ADR-0008과 현재 소스 비교, gate 전용 작업의 축소, 남는 undo·래치·힌트·성장 의무와 최소 재현 범위 | 2026-11-05 | 2026-11-05 | Work816에서 후속 조사와 별도 DB 재현이 여전히 필요한지 판단하기 위해 |
| [adr0008-claude-review.md](adr0008-claude-review.md) | Work816 전제의 독립 재검토: READ 경합의 설계 해소 제안, fast path 후보 재연결 의무, 과거 두 VPID 해석, 무성장 eventual return 결정 | 2026-11-05 | 2026-11-05 | Work818에서 ADR-0008 이후 범위를 더 줄일 수 있는지 독립 확인하기 위해 |
| [explore_sweep_lap.py](explore_sweep_lap.py) | INSERT undo와 sweep lap의 전수 interleaving 순수 모델(소스 SHA 고정) | 2026-11-05 | 2026-11-05 | adr0008-claude-review.md의 모델 근거 |
