# PR #7927 alternative OOS insertion — design interview

Status: awaiting Round 1 decisions

## Objective

PR #7927의 행 전체 소유 방식과 다른 설계를 검토한다. 사용자의 팀장 제안은 일반 heap과 child heap에서 공통 OOS 삽입 경로를 사용하고 parent 단계에서는 OOS 기록을 생략하는 것이다. `heap_insert_logical()`에서 목적지 관련 정보를 이용할 수 있는지 확인하고, 별도 worktree에서 제한된 POC를 통해 가능성을 판단한다.

Work item: 271. 기존 PR #7927의 CI 분석 item 242와 다른 작업이다. 기존 PR의 본문·브랜치는 이 검토로 변경하지 않는다.

## Established scope

- 사용자가 `feature/oos-merge` 기반의 새 worktree에서 POC를 검토하도록 요청했다.
- source worktree/branch: `CBRD-27089-oos-insert-poc`.
- 정확한 base: `fb567a629cdb390fff920542173fa36f454c74a0`. 생성 시 로컬 `feature/oos-merge`와 fetch한 `origin/feature/oos-merge`가 일치했다.
- docs worktree/branch: `my-cubrid-docs-pr7927-insert-poc` / `docs/pr7927-insert-poc`.
- `grill-with-docs`를 사용한다. 사실 조사는 agent가 수행하고, 설계 선택은 질문과 추천 답안을 함께 제시한다. 구현 경계가 합의될 때까지 코드 구현을 시작하지 않는다.
- 현재 수행한 것은 소스 조사와 worktree 생성이다. 빌드·DB 초기화·엔진 수정·실행 검증은 아직 없다.

## Design tree

```text
별도 POC로 대안 검토 [사용자 요청으로 확정]
├─ 정확한 기준 source/worktree [확정: fb567a629]
├─ 실제 호출 순서 [조사 완료: 부모/자식 heap_insert_logical 두 번 호출 아님]
├─ Q1: 고정할 원칙과 함수 위치 [Round 1, 미응답]
├─ Q2: 첫 POC의 구현/실행 검증 범위 [Round 1, 미응답]
└─ Q1/Q2에 따른 다음 결정
   ├─ 목적지 확정 전 값의 표현과 수명
   ├─ normal/root/child 및 UPDATE 이동의 분기 기준
   ├─ 완료된 OOS 행·주소 선할당·내부 행의 처리
   ├─ 기존 부수 효과와 오류/롤백 경계 유지
   ├─ 검증 oracle, 비교 대상과 POC 수용 기준
   └─ 공유된 설계 이해 확인 → 구현 및 실행 검증
```

## Round 1

### Q1 — Fixed principle or fixed function

필수 조건을 “목적지 heap 확정 뒤 normal/child가 공통 경로로 OOS를 기록한다”로 둘 것인가, 기록 위치를 반드시 `heap_insert_logical()` 내부로 제한할 것인가?

추천 답안: 원칙을 고정하고 함수 위치는 소스 조사에 맞춰 결정한다. 기존 `heap_prepared_row` 없이 가능한 경계를 먼저 찾고, 불가피하게 필요한 상태만 추가한다.

사용자 답변: 미응답. 추천은 결정으로 간주하지 않는다.

### Q2 — First executable POC scope

일반 INSERT, root를 통한 INSERT, child 직접 INSERT, 파티션 이동 UPDATE, 실패 롤백을 첫 실행 검증 범위로 삼을 것인가, 아니면 기존 PR 전체 경로까지 첫 구현에 포함할 것인가?

추천 답안: 핵심 경로 POC부터 수행한다. loader·복제·중복 키 경로의 설계 영향은 함께 조사하고, 미검증 경로를 명시한다. 제한된 POC의 성공을 기존 PR 전체 대체 가능성으로 확대하지 않는다.

사용자 답변: 미응답. 이후 범위 결정에 따라 테스트 목록을 확정한다.

## Recording policy

공통 용어는 이 저장소의 기존 정책에 따라 루트 `CONTEXT.md`에 기록한다. 구현 세부 사항은 용어집에 넣지 않는다. 아직 비교 설계를 채택하지 않았으므로 accepted ADR을 만들지 않는다. PR #7600에 한정된 기존 effective-key routing ADR은 그대로 유지하고, 이번 조사로 자동 변경하거나 폐기하지 않는다.

소스 사실과 제약: [research.md](research.md).
