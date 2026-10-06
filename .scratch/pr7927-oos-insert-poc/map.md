# PR #7927 alternative OOS insertion — design interview

Status: Q1–Q3 settled; awaiting concrete POC design agreement

## Objective

PR #7927의 행 전체 소유 방식과 다른 설계를 검토한다. 사용자의 팀장 제안은 일반 heap과 child heap에서 공통 OOS 삽입 경로를 사용하고 parent 단계에서는 OOS 기록을 생략하는 것이다. `heap_insert_logical()`에서 목적지 관련 정보를 이용할 수 있는지 확인하고, 별도 worktree에서 제한된 POC를 통해 가능성을 판단한다.

사용자가 명시한 최우선 목적은 **코드 단순화**다. 성능 향상은 필수가 아니다. 새 타입 제거 자체를 성공으로 보지 않고, 소유권·상태 전이·호출부 분기·중복 정책·오류 처리까지 포함한 전체 복잡도가 줄어드는지 평가한다. 정확성은 전제이며 메모리·복사·시간 비용과 미지원 경로를 함께 보고한다.

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
├─ Q1: 원칙 고정, 함수 위치 유연 [확정: yes yes]
├─ Q2: 핵심 경로의 제한된 POC [확정: yes yes]
├─ Q3: 코드 단순화 우선, 정확성과 비용 확인 [확정]
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

사용자 답변: “yes yes”로 추천 답안 수락.

### Q2 — First executable POC scope

일반 INSERT, root를 통한 INSERT, child 직접 INSERT, 파티션 이동 UPDATE, 실패 롤백을 첫 실행 검증 범위로 삼을 것인가, 아니면 기존 PR 전체 경로까지 첫 구현에 포함할 것인가?

추천 답안: 핵심 경로 POC부터 수행한다. loader·복제·중복 키 경로의 설계 영향은 함께 조사하고, 미검증 경로를 명시한다. 제한된 POC의 성공을 기존 PR 전체 대체 가능성으로 확대하지 않는다.

사용자 답변: “yes yes”로 추천 답안 수락.

## Round 2

### Q3 — Acceptance criterion

사용자는 “정확성·단순화와 비용 비교”를 선택한 뒤 “코드 단순화가 목적”이라고 우선순위를 명시했다. 성능 개선은 채택 필수 조건이 아니다. 명확한 비용 회귀나 정확성 문제가 있으면 이를 보고하고 채택 판단을 보류한다.

### Q4 — Concrete experiment and shared understanding

추천하는 실험은 모든 값을 읽을 수 있는 inline RECDES를 목적지 결정까지 유지한 다음, 확정된 heap에 공통 OOS 기록 함수를 적용하는 것이다. 별도 행 소유 객체를 도입하지 않고 기존 레코드 버퍼의 소유권을 사용한다. DB_VALUE 재변환 대신 이미 직렬화된 바이트를 OOS에 옮기고 stub으로 바꾸는 방향을 먼저 검토한다.

이 방향에는 반대 비용이 있다. VOT·header 재조립과 선택 정책의 공통화가 필요하므로 기존 prepared-row보다 복잡해질 수도 있다. POC가 동작해도 전체 구현이 더 단순해지지 않으면 채택하지 않는 것이 추천이다. 제한된 지원 범위 때문에 짧아 보이는 효과는 단순화로 계산하지 않는다.

사용자 답변: 미응답. 구현 전 이 구체적인 실험 방향의 공통 이해를 확인한다.

## Recording policy

공통 용어는 이 저장소의 기존 정책에 따라 루트 `CONTEXT.md`에 기록한다. 구현 세부 사항은 용어집에 넣지 않는다. 아직 비교 설계를 채택하지 않았으므로 accepted ADR을 만들지 않는다. PR #7600에 한정된 기존 effective-key routing ADR은 그대로 유지하고, 이번 조사로 자동 변경하거나 폐기하지 않는다.

소스 사실과 제약: [research.md](research.md).
