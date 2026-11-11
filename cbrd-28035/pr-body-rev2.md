https://jira.cubrid.org/browse/CBRD-28035

## Purpose

- serial의 comment가 OOS(행 밖에 값을 따로 저장하는 공간)에 있으면, `NEXT VALUE`를 부를 때마다 `_db_serial`의 OOS 레코드가 하나씩 늘어납니다.
- AS-IS: `NEXT VALUE`가 serial 행을 다시 쓸 때 바뀌지 않은 comment도 새 OOS chain에 씁니다. 이전 chain은 지우지 않습니다. 4K page DB에서 50회 호출하면 OOS 레코드 50개가 남고, 재시작해도 줄지 않습니다.
- TO-BE: 바뀌지 않은 comment는 이전 chain을 그대로 씁니다. 새 chain을 만들지 않으므로 지울 것도 없습니다. 호출 횟수와 관계없이 OOS 레코드는 1개입니다.

## Implementation

- `NEXT VALUE`는 고정 길이 counter 열만 바꿉니다. 그래서 다시 쓰는 OOS 값은 모두 이전 행과 같습니다.
- `serial_update_serial_object`가 새 함수 `heap_attrinfo_transform_to_disk_keep_oos`를 부릅니다. 이전 행에서 읽었고 바뀌지 않았으며 이전 행에서 OOS였던 열은, OOS 계획(`heap_oos_column_plan`)에 이전 행의 참조(OID, 길이, identity stamp)를 넣고 삽입을 건너뜁니다(`reused`).
- 처음 설계는 `heap_update`처럼 이전 chain을 바로 지우는 것이었습니다. 이 방식은 경쟁 상태를 만들어서 버렸습니다. join이나 subquery 같은 fixed가 아닌 scan은 행을 복사하고 page latch를 놓은 뒤에 OOS를 읽습니다. `NEXT VALUE`는 행에 instance lock을 잡지 않으므로, 그 사이에 chain을 지울 수 있습니다.
- 회귀 테스트 `unit_tests/oos/sql/test_oos_sql_serial.cpp`를 추가했습니다. comment는 최대 1024 byte라서 작은 page에서만 OOS로 나갑니다. 그래서 이 테스트는 4K page로 만든 전용 DB `oosserialdb`를 씁니다. 이를 위해 `setup_isolated_db.sh`가 `createdb` 옵션을 더 받고, `SqlServerEnv`가 DB 이름을 받습니다.

## Remarks

- 검증 (debug 빌드, 4K page):
  - 새 테스트는 수정 전에 실패하고(OOS 레코드 1 → 50 → 51), 수정 후 통과합니다.
  - 서버 모드 `NEXT VALUE` 50회: OOS 레코드 50개(18 page)가 1개(2 page)로 줄었습니다. 재시작 뒤 값과 comment가 맞고, 다음 값은 51입니다.
  - writer 4개와 join·subquery reader 4개를 동시에 실행했습니다. reader 오류가 수정 전 0건, 바로 지우는 설계에서 354건과 492건, 이 설계에서 0건이었습니다. 절차는 아래 문서에 있습니다.
  - 같은 트랜잭션 안의 CREATE 또는 ALTER SERIAL과 `NEXT VALUE`, 그리고 commit 또는 rollback: OOS 레코드 1개, comment 정상입니다.
  - `NEXT VALUE` 도중 `kill -9`와 복구를 3회 했습니다. comment의 md5가 같고, OOS 레코드는 1개이며, 값이 이어집니다.
  - `ctest -R oos` 52개가 모두 통과합니다.
- CREATE SERIAL 직후에는 comment가 행 안(inline)에 있습니다. `locator_finalize_oos_record`가 system class의 client 행에는 OOS 준비를 건너뛰기 때문입니다. 첫 `NEXT VALUE`에서 OOS로 옮겨지고, 그 뒤로는 같은 chain을 씁니다.
- 기본 16K page에서는 comment가 1024 byte 이하라서 serial 행이 OOS 기준(약 4KB)을 넘지 않는다고 봅니다(코드 기준 추론).
- 남은 위험: 클래스 표현(representation)이 바뀐 행은 재사용하지 않고 새 chain을 씁니다. 이때 이전 chain은 남습니다(코드 기준). `_db_serial`의 표현은 버전 업그레이드에서만 바뀝니다.
- 관련: SA 모드에서 `NEXT VALUE`를 rollback하면 OOS 참조가 깨지는 [CBRD-28052](https://jira.cubrid.org/browse/CBRD-28052)은 별도 PR에서 다룹니다. 이 PR 뒤에는 comment를 처음 OOS로 옮기는 `NEXT VALUE`만 그 범위에 남습니다.
- 경쟁 상태 재현 절차와 결과: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-28035/race-repro.md
