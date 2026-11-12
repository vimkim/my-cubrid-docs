https://jira.cubrid.org/browse/CBRD-28073

## Purpose

- serial NEXT VALUE가 OOS(out-of-row 저장소)에 아무것도 쓰지 않게 해서 CBRD-28035와 CBRD-28052를 함께 해결한다.
- AS-IS: NEXT VALUE는 `_db_serial` 행을 롤백되지 않는 redo 전용 로그로 쓰면서, 행을 다시 인코딩하는 과정에서 긴 comment를 롤백되는 새 OOS chain으로 옮긴다. 4K page DB에서는 NEXT VALUE마다 chain이 하나씩 남고(CBRD-28035), SA 모드에서 롤백하면 행이 지워진 chain을 가리켜 -1397이 난다(CBRD-28052).
- TO-BE: NEXT VALUE는 각 열의 저장 형태를 그대로 둔다. inline comment는 inline으로 남고, 이미 OOS에 있는 comment는 기존 chain을 그대로 가리킨다.

## Implementation

- `heap_attrinfo_transform_to_disk_keep_form`을 추가했다. 일반 인코딩과 같지만, 가변 열마다 기존 레코드의 형태를 따른다. OOS로 내보내는 결정과 OOS 삽입을 하지 않는다.
- `serial_update_serial_object`가 이 함수를 쓴다. 바뀌는 값(`current_val`, `started`)은 평소처럼 인코딩된다. NUMERIC은 값이 커지면 저장 바이트가 늘어나므로, 제자리 패치 대신 인코딩을 다시 하는 방식을 택했다.
- 기존 OOS 열의 참조를 읽을 때 `or_rep_id()`로 표현 ID를 비교한다. `OR_GET_REPID`는 HAS_OOS 플래그 비트를 지우지 않는다.
- 로그 형식은 바뀌지 않는다. HA applier는 이전처럼 RVHF_UPDATE의 전체 레코드 이미지를 읽는다.

## Remarks

- 이 PR은 #8492(CBRD-28035)와 #8496(CBRD-28052)을 대체한다. 두 PR은 "NEXT VALUE가 OOS chain을 쓴다"는 결과를 각각 수습하는 방식이었다. #8434(CBRD-27781)에 의존하지 않는다.
- 첫 커밋은 테스트만 담는다. 수정 전 소스에서 chain 수 테스트와 롤백 테스트가 실패하는 것을 확인했다.
- HA 복제는 실행하지 않았다. 로그 형식이 같다는 점과 applier 코드를 읽은 결과에 근거한다.
- serial을 ALTER하면 클라이언트가 행을 일반 update로 다시 쓰므로, comment의 OOS 배치는 그때 정상 경로로 정해진다.

### Test Plan

debug 빌드, `--db-page-size=4K` DB, `feature/oos-merge` `67220b7e23` 기준.

| 경우 | 수정 전 | 수정 후 |
|---|---|---|
| `test_oos_sql_serial` (chain 수, `current_val` 크기 증가) | chain 1개, 10개, 10개 남음 | 통과 |
| `test_oos_sql_serial_rollback` (첫/이후 NEXT VALUE, ALTER, CREATE 롤백, 종료 시 cache 기록) | -1397 | 통과 |
| SA와 서버 모드의 롤백, `kill -9` 뒤 복구, 다른 serial의 ALTER/DROP과 섞인 롤백 | SA에서 -1397 | 정상, OOS 레코드 0개, `checkdb` 통과 |
| 이전 빌드에서 comment가 OOS로 옮겨진 DB | | 기존 chain 3개 재사용, 값과 comment 정상 |
| `ctest -R oos` | | 전체 통과 |
