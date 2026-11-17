# 형식 검증 도구 평가

Created: 2026-11-17. Last modified: 2026-11-18 (Asia/Seoul).

CUBRID 코드에 적용할 형식 검증 도구(SMT, bounded model checker, TLA+)를 실험하고 도입 여부를 판정한 문서를 모은다. 특정 설계를 TLA+로 검증한 결과는 각 ticket이나 topic 디렉터리(예: [SP DML guard](../sp-dml-guard/README.md))에 둔다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [z3-adoption.md](z3-adoption.md) | Z3로 slotted page·overflow·MVCC header 산술을 모델링한 결과, CBMC·TLA+ 비교, 조건부 go 판정과 독립 리뷰 반영 | 2026-11-17 | 2026-11-18 | Z3 도입 가치 판정 (work-tracker #991) |
