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

- 동일 엔진 소스 `02df4d9`의 production test-OFF 측정에서 두 SELECT는 +0.6498%/+1.3624%, 새 복제본 UPDATE는 +1.6656%, 별도 연속 UPDATE는 +1.6622%였습니다.
- 뒤의 유효한 plain UPDATE batch는 +5.0158%였습니다. 기존 +2% 목표의 전체 통과를 주장하지 않습니다.
- 작성자는 현재 관측된 약 +5%를 수용해 이번 개선을 먼저 제안합니다. 잔여 비용과 변동은 [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816)에서 추적합니다.
- 이 PR revision의 엔진 파일은 `02df4d9`와 같으며 집중 CTest 15/15를 통과했습니다. PR용 새 binary의 성능 측정과 전체 회사 CI는 아직 실행하지 않았습니다.
- OOS reclaim·allocator 구현·threshold와 기존 기준 2는 별도 범위입니다. MVCC·recovery·ownership·identity 검사와 COPY 의미를 유지합니다.
- [구현·측정 근거와 검증 범위](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-shared-read-update_408d135_codex.md)
