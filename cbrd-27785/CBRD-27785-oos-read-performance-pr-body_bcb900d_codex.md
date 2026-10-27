https://jira.cubrid.org/browse/CBRD-27785

## Purpose

- OOS 통합 후 작은 일반 행의 스캔 CPU 비용이 증가한 문제를 줄입니다.
- AS-IS: 행 밖의 큰 값을 읽는 OOS 전용 준비가 일반 heap 읽기에도 포함됩니다.
- TO-BE: 일반 값은 가벼운 공통 경로로 읽고, 실제 OOS 값만 별도 준비를 수행합니다.

## Implementation

- `heap_file.c`에서 OOS Resolve의 임시 버퍼와 grouped prefetch 상태를 일반 읽기 경로 밖으로 옮깁니다.
- 가변값의 시작·끝 offset을 기존 행 layout으로 읽어 중복 header 해석을 줄입니다.
- 기존 NULL·기본값·구 schema 변환과 OOS/pending 값의 복사·해제 처리를 공유합니다.
- 반복 가능한 서버 instructions 하네스와 고정값·가변값·offset·pending 읽기 검증을 추가합니다.

## Remarks

- 재구성한 20만 행 스캔에서 baseline 대비 instructions 증가는 좁은 스캔 약 5.1% → 1.11%, 여러 컬럼 약 8.9% → 1.36%입니다. 역순 측정도 두 쿼리 모두 승인된 2% 기준을 통과했습니다.
- 실제 저장 진단은 양쪽 모두 heap이며 overflow·OOS 행은 0개입니다. 이 기준은 해당 읽기 경로에만 적용합니다.
- heap → OOS 이관의 집적도 trade-off, overflow 대비 OOS, UPDATE와 대용량 I/O 성능은 후속 범위입니다.
- SERVER_MODE·SA_MODE release 빌드, 집중 CTest 15/15, snapshot/vacuum 선택 3/3을 통과했습니다. 전체 회사 CI는 아직 실행하지 않았습니다.
- [원인·측정 조건·검증 범위](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-oos-read-performance_bcb900d_codex.md)
