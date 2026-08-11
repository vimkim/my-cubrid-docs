# Mission: CBRD-27157 loaddb 잠금 설계를 소스로 판단하기

## Why
OOS 회귀 PR #7588의 리뷰와 팀 논의에서 `BU_LOCK`, loaddb worker transaction, MVCCID self-lock, assert의 역할을 남의 결론에 의존하지 않고 설명하고 판단한다. 실제 소스와 불변식을 근거로 질문하고, 설계 선택의 장단점을 팀에 정확히 전달하는 것이 목표다.

## Success looks like
- session transaction과 batch worker transaction의 역할·소유 lock을 그림으로 설명한다.
- object lock과 MVCCID transaction lock을 resource key와 보호 대상 기준으로 구분한다.
- crash stack을 따라 OOS file 생성이 왜 self-lock 경로를 열었는지 설명한다.
- early return과 assert 완화안을 정확성·불변식·release 동작·module seam 기준으로 비교한다.
- 리뷰에서 결론을 가르는 질문을 소스 근거와 함께 제시한다.

## Constraints
- 설명과 lesson은 한국어로 작성한다.
- 데이터베이스 잠금 배경지식이 많지 않다는 전제에서 한 번에 하나의 개념만 학습한다.
- 현재 PR head `f11fc4259`의 소스를 구현 증거로 사용하고, 역사적 의도는 해당 commit으로 구분한다.
- 짧은 설명 뒤 retrieval practice와 즉시 feedback을 제공한다.

## Out of scope
- lock manager 전체 상태 머신과 deadlock detector의 상세 구현
- MVCC snapshot·vacuum 알고리즘 전체
- OOS 저장 형식과 CRUD 전체 설계
- PR #7588의 최종 팀 의사결정을 대신 내리는 일
