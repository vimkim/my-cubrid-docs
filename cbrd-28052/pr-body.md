https://jira.cubrid.org/browse/CBRD-28052

## Purpose

- SA 모드(`csql -S`와 standalone 유틸리티)에서 NEXT VALUE를 롤백해도 serial의 comment를 읽을 수 있게 한다.
- AS-IS: comment가 OOS(out-of-row 저장소)로 나가는 serial에서, SA 모드로 첫 NEXT VALUE를 실행하고 롤백하면 `_db_serial` 행이 롤백으로 지워진 OOS chain을 가리킨다. 그 뒤 comment를 읽으면 `ER_HEAP_OOS_CORRUPTED_RECORD`(-1397)가 난다. 비정상 종료 뒤 복구에서도 같다.
- TO-BE: SA 모드에서도 서버 모드처럼 행 갱신과 새 OOS chain이 한 topop(시스템 연산)으로 함께 커밋된다. 롤백이나 복구 뒤에도 행과 chain이 맞는다.

## Implementation

- `serial_update_serial_object`는 serial에 X_LOCK이 없을 때만 topop을 연다. X_LOCK은 같은 트랜잭션이 serial을 만들거나 고쳤다는 뜻이고, 그때는 DDL의 undo가 행 전체를 되돌린다.
- 그런데 SA 빌드의 `lock_get_object_lock`은 모든 객체에 X_LOCK을 돌려준다. 그래서 SA 모드의 NEXT VALUE는 topop 없이 행을 redo 전용으로 쓰고, chain은 undo가 있게 썼다. 롤백은 chain만 지웠다.
- SA 빌드에서는 사용자 트랜잭션이면 serial을 잠기지 않은 것으로 보고 topop을 연다. 종료 때 serial cache를 기록하는 시스템 트랜잭션은 topop을 열 수 없고 롤백되지도 않으므로 이전 경로를 그대로 쓴다. 서버 모드 코드는 바뀌지 않는다.
- `unit_tests/oos/sql/test_oos_sql_serial_rollback.cpp`(SA gtest)를 추가했다. #8492가 만드는 4K page `oosserialdb` fixture를 함께 쓴다.

## Remarks

- 병합 순서: #8492와 #8434가 병합된 뒤에 병합한다. 이 브랜치는 #8492 위에 있어서 diff에 #8492 커밋 3개가 함께 보인다. 리뷰 대상은 마지막 두 커밋이다.
  - #8492가 있으면 NEXT VALUE는 이미 OOS에 있는 comment에 chain을 새로 쓰지 않는다. 남는 결함 구간은 inline comment를 처음 OOS로 옮기는 NEXT VALUE다.
  - #8434가 없으면 같은 트랜잭션에서 serial DDL이 지운 OOS slot을 topop이 재사용해 커밋할 수 있다. 그러면 롤백이 그 slot에 옛 chain을 되살리다 debug 빌드에서 `spage_insert_for_recovery` assert로 멈춘다(`RolledBackAlterAndNextValueRestoreTheCommittedRow`). #8434(CBRD-27781)가 이 slot 재사용을 막는다.
- 남는 영향: SA 모드에서 CREATE 또는 ALTER SERIAL과 첫 NEXT VALUE를 한 트랜잭션에서 실행하고 롤백하면, topop이 커밋한 chain 하나가 참조 없이 남는다. 손상은 아니다. 서버 모드는 이때 topop을 쓰지 않으므로 남지 않는다.
- serial 값은 SA 모드에서도 롤백으로 되돌아가지 않는다. 서버 모드와 같고, 수정 전에도 같았다.

### Test Plan

debug 빌드, 4K page DB, `feature/oos-merge`에 #8434와 #8492를 합친 빌드에서 확인했다.

| 경우 | 수정 전 | 수정 후 |
|---|---|---|
| SA, 첫 NEXT VALUE 3회 후 롤백 | -1397 | 정상 |
| SA, 첫 NEXT VALUE 5회 뒤 `kill -9`, 복구 | -1397 | 정상 |
| SA, 다른 serial의 ALTER/DROP과 첫 NEXT VALUE 후 롤백 | -1397 | 정상 |
| 서버 모드, 같은 경우들과 서버 `kill -9` 후 복구 | 정상 | 정상 |
| SA, CACHE serial 사용 뒤 종료(cache 기록) | 정상 | 정상 |
| `test_oos_sql_serial_rollback` (ctest, 5개) | 1개 실패 | 5개 통과 |

- OOS ctest 전체(`ctest -R oos`): #8434와 #8492를 합친 빌드에서 57개 모두 통과. #8434가 없는 이 브랜치 단독에서는 53개 중 52개 통과, 실패 1개는 위의 ALTER 경우다.
