# OOS 작업 현황

Last modified: 2026-11-04 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [issue-graphs.html](issue-graphs.html) | 남은 OOS 이슈와 PR의 선행·결정·순서 관계 그래프 3장, 근거 위치, 전체 목록 | 2026-11-03 | 2026-11-03 | PR7990 develop 병합까지 무엇이 무엇을 막는지 한 화면에서 보기 위해 |
| [reclaim-redesign.md](reclaim-redesign.md) | 동시성·복구 OOS 결함의 공통 가정, 확정 뒤 회수(D3) 설계, 회수의 redo·undo와 값 전체 로깅 비용, 성능 영향, 사양 §2·§3·§4 개정안, TLA+ 검증 계획과 U1 모델 결과(`reclaim-model/`), 팀장 보고 요약 | 2026-11-03 | 2026-11-03 | 결함을 하나씩 막지 않고 설계 원인을 없애는 개정을 검증 순서와 함께 정리하고 보고하기 위해 |
| [design-contradictions.md](design-contradictions.md) | 주장 A-H, 두 안전성 모순의 정리·반례·증명, 수정 필요조건과 근거의 한계 | 2026-11-04 | 2026-11-04 | 물리 undo·조기 재사용과 undo image 기반 삭제가 데이터 보존 요구와 양립하지 않음을 논문 형식으로 설명하기 위해 |
| [reclaim-decisions.md](reclaim-decisions.md) | 공간 보호(D1-D3), LSA gate, 삭제 결정 근거(현재/B/A/A'/B3/B4), D3 회수기 재시도의 후보별 TLA+ 결과, 고른 조합의 통합 모델 검사, 반례, 통과 이유 불변식, 도달 확인, 추가 대안(B2-B6, C1-C4) 검토와 권고 | 2026-11-03 | 2026-11-04 | 설계 결정마다 어떤 후보가 가능하고 왜 가능한지를 모델 검사로 설명하기 위해 |
| [adr-0008-confirmation.md](adr-0008-confirmation.md) | 팀장 확정을 요청하는 ADR-0008 결정 일곱 개, 추가 대안 검토 결과와 결정 2의 A'/B3 선택, 사양 변경 요약, PR #7990 일정 선택지, 확정 뒤 순서와 한계 | 2026-11-03 | 2026-11-04 | 확정 미팅(2026-11-04)에서 사양 개정안을 항목별로 확정받기 위해 |
| [reclaim-engine-facts.md](reclaim-engine-facts.md) | 대안 B2, B3에 필요한 엔진 사실: vacuum의 commit 판단, vacuum block에 들어가는 로그, 같은 레코드의 중복 job, snapshot 없는 독자, UPDATE의 옛 chain 처리, 재시작 재실행 | 2026-11-04 | 2026-11-04 | 추가 대안 검토의 모델 가정과 판단을 file:line 근거로 뒷받침하기 위해 |

`issue-graphs.html`은 생성 결과입니다. 직접 고치지 말고 `issue-graphs.json`의 노드·관계·그래프 구성을 고친 뒤 다시 만듭니다.

```sh
python3 oos/build-issue-graphs.py
```

생성에는 Graphviz `dot`과 `Noto Sans CJK KR` 글꼴이 필요합니다. 글꼴 폭으로 노드 크기를 계산하므로 다른 글꼴로 만들면 브라우저에서 글자가 상자를 넘을 수 있습니다. `issue-graphs.template.html`은 페이지의 CSS와 선택 동작 스크립트입니다.

생성기는 알 수 없는 상태·관계 유형, 없는 노드를 가리키는 관계, 근거가 빠진 관계를 거부합니다. 한 그래프 안에서 관계가 없는 노드는 그래프 대신 그 아래 목록에 넣습니다.
