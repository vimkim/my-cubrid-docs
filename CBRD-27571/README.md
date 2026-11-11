# CBRD-27571

볼륨 추가 중 서버가 중단된 뒤 재시작 복구가 `log_append_compensate_internal` assertion으로 멈추는 기존 develop 결함을 추적한다. 관련 엔진 수정은 PR #8284이고, 이번 CI 귀속 조사는 PR #8434·#8348과 develop 대상 PR #8409를 대조한다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [restart-assert-analysis.md](restart-assert-analysis.md) | 검증된 shell 증거, temp LSA·CLR 원인, 최초 도입, 기존 JIRA 및 병합 조건 판단 | 2026-11-11 | 2026-11-11 | #8434의 실패를 OOS 회귀와 develop 기존 결함으로 구분 |
