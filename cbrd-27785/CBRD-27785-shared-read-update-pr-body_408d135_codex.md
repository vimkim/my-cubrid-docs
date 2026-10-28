https://jira.cubrid.org/browse/CBRD-27785

## Purpose

- OOS 통합 후 일반 테이블의 읽기와 UPDATE에 남은 CPU 비용을 줄입니다.
- AS-IS: 공통 읽기에서 header를 반복 해석하고, 일반 UPDATE에도 OOS 계획과 추가 owner를 미리 만듭니다.
- TO-BE: heap/OOS 공통 reader를 유지하면서 layout을 재사용하고 필요한 경우에만 OOS 상태를 만듭니다.

## Implementation

- 공통 decoder에서 가변값의 시작·끝 offset을 함께 읽고 기존 변환·복사·해제 경로를 유지합니다.
- 작은 요청의 작업 배열을 stack에 두고, 단일 OOS 값은 scalar Resolve를 사용합니다.
- UPDATE의 payload 크기와 강제 OOS 선택을 한 번에 계산하고, writer가 방금 쓴 header와 offset 폭을 재사용합니다.
- 추가 pending owner는 copy-area/workspace 입력일 때만 생성하고 heap/index write와 오류 정리까지 유지합니다.
- 기존 scan 벤치마크와 고정값·가변값·offset·pending 읽기 테스트를 보존합니다.

## Remarks

20만 행, server user-space instructions 중앙값입니다. 단위 M은 100만 instructions이며 괄호는 develop 대비, 마지막 열은 feature 대비 증감률입니다.

| 쿼리 | develop `4781495` | feature/oos-merge `dcbf09e` | HEAD `408d135` | PR 적용 효과 |
| --- | ---: | ---: | ---: | ---: |
| 일반 풀 스캔 | 250.883M | 268.485M (+7.02%) | 252.499M (+0.64%) | -5.95% |
| 일반 조건 스캔 | 531.577M | 575.794M (+8.32%) | 538.800M (+1.36%) | -6.42% |
| 일반 UPDATE, 새 복제본 | 6,472.176M | 6,818.693M (+5.35%) | 6,579.648M (+1.66%) | -3.51% |

- 실제 세 binary를 production test-OFF로 측정했습니다. 정·역순 2라운드, 각 5회 중 첫 회를 제외한 8회 중앙값이며 UPDATE는 매번 새 복제본입니다. 연속 UPDATE 표본은 합치지 않았습니다.
- develop은 기존 회귀 기준 `4781495`로 고정했습니다. 현재 원격 tip `639628d`와의 비교는 별도입니다.
- 동일 엔진 소스 `02df4d9`의 이전 plain UPDATE batch에는 +5.0158%도 있었습니다. 기존 +2% 목표의 전체 통과를 주장하지 않습니다.
- 작성자는 현재 관측된 약 +5%를 수용해 이번 개선을 먼저 제안합니다. 잔여 비용과 변동은 [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816)에서 추적합니다.
- 집중 CTest 15/15를 통과했고 독립 Standards·Spec 검토의 발견사항은 각각 0건입니다. 전체 회사 CI는 아직 실행하지 않았습니다.
- OOS reclaim·allocator 구현·threshold와 기존 기준 2는 별도 범위입니다. MVCC·recovery·ownership·identity 검사와 COPY 의미를 유지합니다.
- [구현·측정 근거와 검증 범위](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-shared-read-update_408d135_codex.md)
