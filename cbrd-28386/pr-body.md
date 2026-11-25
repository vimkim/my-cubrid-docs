https://jira.cubrid.org/browse/CBRD-28386

## Purpose

- 서버는 클래스의 디스크 표현과 통계를 카탈로그 파일에 고정 레이아웃 레코드로 저장합니다. 이 레코드에는 어떤 필드에도 속하지 않는 바이트(정렬 빈칸, 예약 공간, 쓰지 않는 항목)가 있습니다.
- AS-IS: `src/storage/system_catalog.c` 의 writer가 필드만 쓰고 나머지 바이트는 버퍼에 있던 값을 그대로 둡니다. 그래서 이전 서버 메모리가 TDE로 암호화하지 않는 카탈로그 페이지와 `RVCT_INSERT`/`RVCT_UPDATE` 로그에 기록됩니다.
- TO-BE: 카탈로그 파일 레코드에서 필드가 아닌 바이트는 항상 0입니다.

## Implementation

- 각 `catalog_put_*` writer가 필드를 쓰기 전에 슬롯 전체를 0으로 채웁니다.
  - 표현 헤더(`DISK_REPR`, 20-55바이트), 컬럼 레코드(`DISK_ATTR`, 32-79바이트), B-tree 통계(10-11바이트), 표현 디렉터리 항목(6-7, 13-15바이트), 카탈로그 페이지 헤더(6-7바이트)
- 클래스 정보 writer는 예약 영역을 호출부에 맡기지 않고 직접 0으로 채웁니다.
- 새 디렉터리를 만들 때 아직 쓰지 않는 두 번째 항목을 0으로 채웁니다.
- `RVCT_NEWPAGE` 가 로그에 남기는 페이지 헤더 구조체의 padding을 0으로 채웁니다.
- 디스크 형식과 읽는 쪽 코드는 바뀌지 않습니다.
- 회귀 테스트 `unit_tests/system_catalog/` 를 추가합니다(CMake 옵션 `UNIT_TEST_SYSTEM_CATALOG`). 새 메모리를 `0xA5` 로 채운 뒤, 기본값과 인덱스가 있는 클래스를 만들고 표현을 하나 더 추가합니다. 그다음 카탈로그 레코드에서 필드가 아닌 바이트가 모두 0인지 확인합니다.

## Remarks

- 검증(debug 빌드, SA 모드):
  - 새 테스트는 수정 전 339바이트를 찾아 실패하고, 수정 후 통과합니다. `ctest -R test_catalog_record_gaps`
  - 이슈의 재현 절차: 수정 전 카탈로그 페이지에 `0xA5` 구간 23개 → 수정 후 0개(`use_system_malloc=yes`, 기본 heap 모두)
- 새 테스트는 debug 빌드에서만 수정 전 결함을 확실히 잡습니다. release 빌드는 `use_system_malloc` 을 무시합니다. 기본 CI 설정은 unit test를 빌드하지 않습니다.
- 제한: 이미 만들어진 DB의 레코드와 기존 로그에 남은 바이트는 지우지 않습니다. 해당 레코드를 다시 쓸 때 0이 됩니다.
- 범위 밖: `RVCT_NEW_OVFPAGE_LOGICAL_UNDO` 가 로그에 남기는 `VPID` 구조체의 padding 2바이트. 같은 형태가 엔진 여러 곳에 있습니다.
- 수정 후 로그에 남은 `0xA5` 구간은 카탈로그 클래스 힙 행 쪽 경로(CBRD-28257, CUBRID/cubrid#8693)로 보입니다.
- TC 변경은 필요 없습니다.
