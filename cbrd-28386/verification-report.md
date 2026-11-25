# CBRD-28386 검증 보고서

- 이슈: <https://jira.cubrid.org/browse/CBRD-28386>
- 소스: `CUBRID/cubrid` 브랜치 `CBRD-28386`, 커밋 `d16738b08f7b2a75bce2d23f58d34af6cd33c277`
- 기준: `develop` `ca39c2c6a4` (2026-11-25 기준 `origin/develop` HEAD)
- 빌드: CMake preset `debug_gcc`, SA 모드(`csql -S`). release 빌드와 CS 모드는 실행하지 않았습니다.
- 날짜: 2026-11-25

## Purpose

카탈로그 파일 레코드에서 필드가 아닌 바이트에 이전 서버 메모리가 남는 결함을 수정 전에 재현합니다. 그리고 수정 후 그 바이트가 0인지 확인합니다.

- AS-IS: writer가 필드만 쓰고, 나머지 바이트는 버퍼에 있던 값을 그대로 카탈로그 페이지와 로그에 기록합니다.
- TO-BE: 필드가 아닌 바이트는 항상 0입니다.

## Implementation

### 감사 범위와 결과

`src/storage/system_catalog.c` 에서 레코드를 만드는 writer와 `spage_insert`/`spage_update`/`log_append_*` 로 가는 버퍼를 모두 확인했습니다.

| 레코드 | writer | 수정 전 빈 바이트 | 수정 |
| --- | --- | --- | --- |
| 표현 헤더 (56B) | `catalog_put_disk_representation` | 20-55 | 슬롯 전체 `memset` |
| 컬럼 레코드 (88B) | `catalog_put_disk_attribute` | 32-79 | 슬롯 전체 `memset` |
| B-tree 통계 (120B) | `catalog_put_btree_statistics` | 10-11 | 슬롯 전체 `memset` |
| 디렉터리 항목 (16B × 2) | `catalog_put_repr_item_to_record` | 6-7, 13-15, 새 디렉터리의 두 번째 항목 전체 | 항목 `memset`, 새 디렉터리의 두 번째 항목 `memset` |
| 페이지 헤더 (16B) | `catalog_put_page_header` | 6-7 | 슬롯 전체 `memset` |
| `RVCT_NEWPAGE` 로그 데이터 | `catalog_initialize_new_page` | 구조체 padding 5바이트 | 구조체 `memset` |
| 클래스 정보 (56B) | `catalog_put_class_info_to_record` | 없음(호출부가 예약 영역을 채움) | writer가 슬롯 전체를 채우고 호출부 `memset` 제거 |
| 컬럼 기본값 | `catalog_store_attribute_value` | 없음(`val_length` 만큼 `memcpy`) | 변경 없음 |

- 디렉터리 개수 바이트(`CATALOG_REPR_ITEM_COUNT_OFF`)는 첫 항목 안에 있습니다. `catalog_put_repr_item_to_record` 의 모든 호출부는 항목을 쓴 뒤 개수를 씁니다. 그래서 새 `memset` 이 개수를 지우지 않습니다.
- 표현 레코드는 슬롯 사이에 정렬 빈칸이 없고, overflow 페이지로 나뉠 때도 쓴 길이만 기록합니다.
- 읽는 쪽은 필드 오프셋만 읽습니다. 디스크 형식은 바뀌지 않습니다.
- 추가 비용은 슬롯마다 16-120바이트 `memset` 입니다. 같은 바이트를 `spage_insert` 와 로그가 다시 복사하므로 무시할 만합니다. `catalog_update_class_info` 의 경로에는 새 비용이 없습니다(예약 영역 `memset` 이 슬롯 전체 `memset` 으로 바뀜).

### 회귀 테스트

`unit_tests/system_catalog/test_catalog_record_gaps.cpp` (CMake 옵션 `UNIT_TEST_SYSTEM_CATALOG`, fixture `catalog_setup_db`/`catalog_cleanup_db`).

- `mallopt (M_PERTURB)` 과 `CUBRID_USE_SYSTEM_MALLOC=yes` 로 새 메모리를 `0xA5` 로 채웁니다. debug 빌드에서는 시작할 때 이 조건이 실제로 켜졌는지 확인합니다.
- 기본값과 인덱스가 있는 클래스를 만들고, 통계를 갱신하고, 컬럼을 추가해 표현을 바꾼 뒤 다시 통계를 갱신합니다.
- 디렉터리, 클래스 정보, 표현 레코드를 페이지에서 직접 읽어 필드가 아닌 바이트가 모두 0인지 확인합니다.
- 데이터베이스는 빌드 트리 아래 테스트 전용 registry에 만듭니다. 개발자의 `databases.txt` 를 건드리지 않습니다.

## Remarks

### Test Plan

#### 1. 수정 전 재현 (이슈 절차, 설치본 = `ca39c2c6a4`)

SQL: `create table t (a int, b varchar(10) default 'gap', c bigint); create index i_t_a on t(a); insert ...; update statistics on t with fullscan; alter table t add column d int; update statistics on t;`

| 조건 | 카탈로그 페이지 `0xA5` 구간(4바이트 이상) | 2바이트 이상 | 활성 로그 `0xA5` 구간(4바이트 이상) |
| --- | --- | --- | --- |
| `use_system_malloc=yes`, `MALLOC_PERTURB_=90` | 23 (페이지 577: 36바이트 6개, 48바이트 16개, 4바이트 1개) | 30 | 59 |
| 기본 heap, `MALLOC_PERTURB_=90` | 1 (디렉터리 4바이트) | 4 | 59 |

기본 heap에서는 같은 자리에 이전 메모리가 있었습니다. 첫 컬럼 레코드 32-79바이트에 `0000 0242 0028 ... 0000 0b40` 같은 정수, 두 번째 컬럼 레코드의 같은 자리에 ASCII `gger` 가 있습니다. 이슈 보고와 같습니다.

#### 2. 수정 후 재현 (설치본 = `d16738b08f`)

| 조건 | 카탈로그 페이지 `0xA5` 구간(4바이트 이상) | 2바이트 이상 | 활성 로그 `0xA5` 구간(4바이트 이상) |
| --- | --- | --- | --- |
| `use_system_malloc=yes` | 0 | 0 | 28 |
| 기본 heap | 0 | 0 | 28 |

- 로그의 4바이트 이상 구간은 59개에서 28개로 줄었습니다(4바이트 29개, 19바이트 2개 사라짐).
- 남은 28개는 두 allocator에서 똑같습니다. 바이트 모양(가변 길이 오프셋 표 뒤의 8바이트 빈칸)이 카탈로그 클래스 힙 행과 같습니다. 그래서 CBRD-28257(CUBRID/cubrid#8693, 아직 열려 있음)의 경로로 판단했습니다. 이것은 추론입니다. `cubrid diagdb -d 8` 로 로그 레코드 종류를 확인하려 했지만 출력 없이 끝나지 않아 중단했습니다.
- 이 실행에서는 로그에서 36·48바이트 구간이 보이지 않았습니다(수정 전에도). 이슈 보고와 다른 점이며 원인은 확인하지 않았습니다.

#### 3. 회귀 테스트

| 라이브러리 | 결과 |
| --- | --- |
| 수정 전(`ca39c2c6a4`) | 실패. 0이 아닌 바이트 339개: 표현 헤더 36, 컬럼 6개 × 48, B-tree 통계 2개 × 2, 디렉터리 11 |
| 수정 전, 리뷰 반영 후 테스트(전제 확인 추가) | 실패. 같은 339개. poisoning 전제 확인은 통과 |
| 수정 후(`d16738b08f`) | 통과 |

실행: `ctest --test-dir <build> -R '^(catalog_setup_db|catalog_cleanup_db|test_catalog_record_gaps)$'`

#### 4. 설정된 전체 ctest (`debug_gcc` 빌드 트리, OOS unit test 포함)

- 77개 중 76개 통과. `test_oos_real_vacuum_latch_timeout_retry` 가 60초 timeout으로 실패했습니다.
- 같은 테스트를 단독으로 다시 실행하자 17초에 통과했습니다. 병렬 실행 부하에 따른 timeout으로 보며, 카탈로그 변경과 관계없다고 판단합니다(추론).

#### 5. 형식 검사

- `git diff --check` 통과.
- `indent -l120 -lc120` (`.c`), astyle (`.cpp`, `.github/workflows/codestyle.sh` 옵션) 모두 변경 없음. lefthook pre-commit codestyle 통과.

### 독립 리뷰

별도 agent가 읽기 전용으로 리뷰했습니다. must-fix는 없었습니다.

| 항목 | 분류 | 처리 |
| --- | --- | --- |
| release 빌드나 poisoning이 꺼진 상태에서 테스트가 아무것도 못 잡고 통과할 수 있음 | should-fix | debug 빌드에서 `use_system_malloc` 과 `0xA5` 채움을 먼저 확인. release에서는 안내만 출력 |
| 블록 주석과 달리 클래스 정보 writer는 슬롯 전체를 채우지 않음 | should-fix | writer가 슬롯 전체를 채우고 호출부 두 곳의 `memset` 제거 |
| 새 디렉터리에서 첫 항목을 두 번 채움 | nit | 두 번째 항목만 채우도록 변경 |
| SQL 실패 시 오류 메시지가 없음 | nit | `er_msg ()` 출력 추가 |
| 페이지 헤더 검사는 수정 전 결함을 확실히 잡지 못함(stack 버퍼) | nit | 테스트에 주석으로 명시 |
| overflow 페이지 분할 경로는 테스트하지 않음 | nit | 코드 구조로 보장됨. 테스트 추가는 보류 |
| googletest `FetchContent_Declare` 가 `oos/` 와 중복 | nit | 보류(같은 URL) |
| 구조체 padding이 멤버 저장 후 unspecified(C11) | nit | 보류(지원 컴파일러에서 문제 없음) |
| `RVCT_NEW_OVFPAGE_LOGICAL_UNDO` 의 `VPID` padding 2바이트 | 범위 밖 | 결정에 따라 PR Remarks에만 기록 |

### 제한과 후속

- 이미 만들어진 DB의 레코드와 기존 로그에 남은 바이트는 지우지 않습니다(이슈 ANALYSIS 항목 4, 범위에서 제외하기로 결정).
- CS 모드에서 복호화된 TDE 값이 이 자리에 들어가는지(ANALYSIS 항목 3)는 확인하지 않았습니다. 수정 후 새로 쓰는 레코드에는 해당하지 않습니다.
- 새 테스트는 기본 CI에서 실행되지 않습니다.
