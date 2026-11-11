# CBRD-27872 조사 기록

Last modified: 2026-11-11 (Asia/Seoul).

[CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872)는 재시작이나 삭제 뒤 새 OOS 페이지를 할당하는 INSERT가 파일 크기에 비례해 느려지는 문제다(PR [#7990](https://github.com/CUBRID/CUBRID/pull/7990) 리뷰 R3). 설계는 [CBRD-27925 growth-bound-design.md](../cbrd-27925/growth-bound-design.md)와 ADR-0010을 따른다. 측정한 구현은 `CBRD-27925-emptied-set` `076c3e4c6`(PR 미생성, Work742 브랜치 `CBRD-27781-postpone-commit`에 통합 예정)이다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [growth-cost-measurement.md](growth-cost-measurement.md) | 빈 페이지 후보 집합 전후 측정: 재시작·삭제 뒤·비우지 않는 삭제 뒤·동시 INSERT 지연과 fetch 수, churn 뒤 페이지·sector 수, ADR-0010 결정 6 판정(반환형 `076c3e4c6` 기준, C안 재사용 우선은 재측정 필요). harness와 원자료는 `bench/` | 2026-11-06 | 2026-11-09 | Work839에서 ADR-0010을 accepted로 바꿀지 정할 측정 근거를 남기기 위해 |
| [growth-cost-reuse-measurement.md](growth-cost-reuse-measurement.md) | 2단계(재사용 우선, `b8a7e5d74`) 대 1단계(`e8e714dae`, `94ed2ea46`) 측정: 단건 INSERT 지연은 구별되지 않고, 로그 레코드와 dirty 페이지가 줄며, churn 파일 크기는 sector 33 대 32(+1)이고 cycle 2 이후 평평하다. 빈 페이지 집합이 클 때 성장마다 집합을 복사해 6,000행 UPDATE가 372에서 980 ms가 된다. 기준선 base 차이 정정, drain 지연 포함. 같은 날 후속: 집합 복사를 고친 `f8cdfca747`은 6,000행 UPDATE가 1단계와 같아지고, 로그 block 가설은 drain 지연만 확인되고 100쪽(파일의 5%) 증가는 반박됨. 후속 2: 5% 증가의 원인(빈 페이지 항목이 bestspace 캐시 1,000 항목을 채워 반쯤 찬 페이지가 밀려남)을 계측으로 찾고 `b24fe8741e`로 고침. 수정 뒤 peak와 sector가 1단계와 같고 UPDATE 시간은 그대로. harness 확장, 계측 패치, 원자료는 `bench/` | 2026-11-11 | 2026-11-11 | Work878에서 2단계를 진행할지 정할 측정 근거를 남기기 위해 |
