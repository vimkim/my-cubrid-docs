https://jira.cubrid.org/browse/CBRD-27785

## Purpose

- OOS 통합 후 일반 테이블의 읽기와 UPDATE에 남은 CPU 비용을 줄입니다.
- AS-IS: header를 반복 해석하고 일반 UPDATE에도 OOS 계획과 추가 owner를 미리 만듭니다. grouped 읽기는 별도 변환 루프를 사용합니다.
- TO-BE: 일반 값과 미리 읽은 OOS 값을 공통 속성 reader에서 변환합니다. layout과 writer 정보를 재사용하고 OOS 상태는 필요한 경우에만 만듭니다.

## Implementation

- grouped 읽기는 여러 OOS 값을 미리 가져오고, 공통 eager 루프와 속성 reader가 값 변환·COPY를 처리합니다. 임시 버퍼는 소유한 경로에서 해제합니다.
- 가변 필드의 시작·끝 offset을 읽기 전에 함께 검사합니다. grouped 분류도 검사된 accessor를 사용하며, offset 폭 switch의 실패 분기를 명시해 strict release 컴파일 오류를 해결합니다.
- 작은 작업 배열의 stack 경로, 단일 OOS의 scalar Resolve, UPDATE 크기·강제 OOS 선택 계산과 writer의 header·offset 폭 재사용을 유지합니다.
- 추가 pending owner는 copy-area/workspace 입력일 때 생성합니다. release와 debug의 기존 inline 매크로 정책을 따릅니다.
- 벤치마크의 서버 PID·DB·설치본을 검증하고, 일반 스캔·조건 스캔·새 복제본 UPDATE의 재현 스크립트를 보존합니다.

## Remarks

- 현재 head는 `067aae4e4`입니다. 해당 head의 [전체 CI](https://github.com/CUBRID/cubrid/actions/runs/40827634555)에서 release·debug·shell·SQL·medium이 모두 성공했습니다.
- strict GCC 8.5 컴파일을 수정 전후로 검증했고, 수정본의 집중 CTest 15/15와 crash recovery 선택 3/3이 통과했습니다. fixture를 포함한 선택 실행이며 전체 검증을 뜻하지는 않습니다.
- 성능 표는 이전 `fd8624c`의 production test-OFF 측정으로 보존합니다. `067aae4e4`의 새 성능 측정은 아닙니다. DB locale·실제 charset·collation 누락도 미확인 조건으로 유지합니다.
- 작성자는 관측된 약 +5% 수준을 수용해 먼저 통합을 제안합니다. 엄격한 +2% 전체 통과는 미충족이며 이 수용을 리뷰어 승인으로 해석하지 않습니다. UPDATE 잔여 비용·변동은 [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816)에서 추적합니다.
- TC 변경은 없습니다. [공개 TC PR #3898](https://github.com/CUBRID/cubrid-testcases/pull/3898)과 [비공개 TC PR #4589](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4589)는 사람이 닫아야 합니다.
- OOS reclaim·allocator 구현·threshold와 기존 기준 2는 별도 범위입니다. MVCC·recovery·ownership·identity 검사와 COPY 의미를 유지합니다.
- [현재 구현·CI와 과거 성능 측정의 근거](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-common-reader_067aae4_codex.md)
