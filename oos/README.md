# OOS 작업 현황

Last modified: 2026-11-03 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [issue-graphs.html](issue-graphs.html) | 남은 OOS 이슈와 PR의 선행·결정·순서 관계 그래프 3장, 근거 위치, 전체 목록 | 2026-11-03 | 2026-11-03 | PR7990 develop 병합까지 무엇이 무엇을 막는지 한 화면에서 보기 위해 |
| [reclaim-redesign.md](reclaim-redesign.md) | 동시성·복구 OOS 결함의 공통 가정, 확정 뒤 회수(D3) 설계, 성능 영향, 사양 §2·§3·§4 개정안, TLA+ 검증 계획, 팀장 보고 요약 | 2026-11-03 | 2026-11-03 | 결함을 하나씩 막지 않고 설계 원인을 없애는 개정을 검증 순서와 함께 정리하고 보고하기 위해 |

`issue-graphs.html`은 생성 결과입니다. 직접 고치지 말고 `issue-graphs.json`의 노드·관계·그래프 구성을 고친 뒤 다시 만듭니다.

```sh
python3 oos/build-issue-graphs.py
```

생성에는 Graphviz `dot`과 `Noto Sans CJK KR` 글꼴이 필요합니다. 글꼴 폭으로 노드 크기를 계산하므로 다른 글꼴로 만들면 브라우저에서 글자가 상자를 넘을 수 있습니다. `issue-graphs.template.html`은 페이지의 CSS와 선택 동작 스크립트입니다.

생성기는 알 수 없는 상태·관계 유형, 없는 노드를 가리키는 관계, 근거가 빠진 관계를 거부합니다. 한 그래프 안에서 관계가 없는 노드는 그래프 대신 그 아래 목록에 넣습니다.
