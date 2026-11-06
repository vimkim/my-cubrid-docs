# CBRD-27872 조사 기록

Last modified: 2026-11-06 (Asia/Seoul).

[CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872)는 재시작이나 삭제 뒤 새 OOS 페이지를 할당하는 INSERT가 파일 크기에 비례해 느려지는 문제다(PR [#7990](https://github.com/CUBRID/CUBRID/pull/7990) 리뷰 R3). 설계는 [CBRD-27925 growth-bound-design.md](../cbrd-27925/growth-bound-design.md)와 ADR-0010을 따른다. 측정한 구현은 `CBRD-27925-emptied-set` `076c3e4c6`(PR 미생성, Work742 브랜치 `CBRD-27781-postpone-commit`에 통합 예정)이다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [growth-cost-measurement.md](growth-cost-measurement.md) | 빈 페이지 후보 집합 전후 측정: 재시작·삭제 뒤·비우지 않는 삭제 뒤·동시 INSERT 지연과 fetch 수, churn 뒤 페이지·sector 수, ADR-0010 결정 6 판정. harness와 원자료는 `bench/` | 2026-11-06 | 2026-11-06 | Work839에서 ADR-0010을 accepted로 바꿀지 정할 측정 근거를 남기기 위해 |
