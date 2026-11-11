https://jira.cubrid.org/browse/CBRD-28035

## Purpose

- serial의 comment가 OOS(행 밖에 값을 따로 저장하는 공간)에 있으면, `NEXT VALUE`를 부를 때마다 `_db_serial`의 OOS 레코드가 하나씩 늘어납니다.
- AS-IS: `NEXT VALUE`가 serial 행을 다시 쓸 때 comment를 새 OOS chain에 씁니다. 이전 chain은 지우지 않습니다. 4K page DB에서 50회 호출하면 OOS 레코드 50개가 남고, 재시작해도 줄지 않습니다.
- TO-BE: 같은 갱신 안에서 이전 chain을 회수합니다. 호출 횟수와 관계없이 OOS 레코드는 1개입니다.

## Implementation

- `serial_update_serial_object`는 `heap_update`를 거치지 않고 `spage_update`로 행을 직접 덮어씁니다. 그래서 `heap_update`의 non-MVCC 분기가 하는 OOS 회수가 이 경로에는 없었습니다.
- 행을 덮어쓰기 전에 `heap_oos_delete_unreferenced`를 호출합니다. `heap_update`가 쓰는 함수와 같고, 이전 행만 가리키는 chain만 지웁니다.
- 이 함수가 OOS 파일을 찾을 수 있도록, 두 호출자가 `_db_serial`의 heap file(`HFID`)을 scan cache에서 넘깁니다.
- 회귀 테스트 `unit_tests/oos/sql/test_oos_sql_serial.cpp`를 추가했습니다. comment는 최대 1024 byte라서 작은 page에서만 OOS로 나갑니다. 그래서 이 테스트는 4K page로 만든 전용 DB `oosserialdb`를 씁니다. 이를 위해 `setup_isolated_db.sh`가 `createdb` 옵션을 더 받고, `SqlServerEnv`가 DB 이름을 받습니다.

## Remarks

- 검증 (debug 빌드):
  - 새 테스트는 수정 전에 실패하고(OOS 레코드 1 → 50 → 51), 수정 후 통과합니다.
  - 서버 모드, 4K page, `NEXT VALUE` 50회: OOS 레코드 50개(18 page)가 1개(2 page)로 줄었습니다. 재시작 뒤 값과 comment가 맞고, 다음 값은 51입니다.
  - writer 4개와 comment reader 2개를 동시에 실행했습니다. 오류와 값 불일치가 없었습니다.
  - 같은 트랜잭션 안에서 CREATE 또는 ALTER SERIAL 뒤 `NEXT VALUE`를 하고 commit 또는 rollback했습니다. OOS 레코드는 1개이고 comment는 정상입니다.
  - `NEXT VALUE` 도중 서버를 `kill -9`하고 복구하기를 3회 했습니다. comment의 md5가 같고, OOS 레코드는 1개이며, 값이 이어집니다.
  - `ctest -R oos` (52개): 51개 통과. `test_oos`는 부하가 큰 호스트에서 60초 제한을 넘었고, 단독 재실행에서 13초에 통과했습니다.
- CREATE SERIAL 직후에는 comment가 행 안(inline)에 있습니다. `locator_finalize_oos_record`가 system class의 client 행에는 OOS 준비를 건너뛰기 때문입니다. 첫 `NEXT VALUE`에서 OOS로 옮겨집니다. 이 PR은 그 동작을 바꾸지 않습니다.
- 기본 16K page에서는 comment가 1024 byte 이하라서 serial 행이 OOS 기준(약 4KB)을 넘지 않는다고 봅니다(코드 기준 추론). 영향은 4K page DB와, 이름이 긴 경우의 8K page DB에 한정된다고 봅니다.
- 검토한 대안: 바뀌지 않은 OOS 열은 기존 chain을 그대로 두는 방식입니다. 이 방식은 UPDATE chain 재사용(CBRD-27230)과 같은 transform 변경과 replication 표시가 필요해서 이 PR 범위를 넘습니다.
- ADR-0008(PR #8434)이 병합되면 `heap_oos_delete_unreferenced`는 바로 지우지 않고 commit 때 회수할 intent를 남깁니다. 이 호출은 serial의 system operation 안에 있습니다. 병합 뒤에는, 그 system operation이 commit된 다음 트랜잭션이 rollback되어도 intent가 실행되는지 확인해야 합니다.
