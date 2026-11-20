https://jira.cubrid.org/browse/CBRD-28073

## Purpose

- serial NEXT VALUE가 OOS(out-of-row 저장소)에 아무것도 쓰지 않게 해서 CBRD-28035와 CBRD-28052를 함께 해결한다.
- AS-IS: NEXT VALUE는 `_db_serial` 행을 롤백되지 않는 redo 전용 로그로 쓰면서, 행을 다시 인코딩하는 과정에서 긴 comment를 롤백되는 새 OOS chain으로 옮긴다. 4K page DB에서는 NEXT VALUE마다 chain이 하나씩 남고(CBRD-28035), SA 모드에서 롤백하면 행이 지워진 chain을 가리켜 -1398(`ER_HEAP_OOS_CORRUPTED_RECORD`)이 난다(CBRD-28052).
- TO-BE: NEXT VALUE는 각 열의 저장 형태를 그대로 둔다. inline comment는 inline으로 남고, 이미 OOS에 있는 comment는 기존 chain을 그대로 가리킨다. DDL이 serial 행을 쓸 때 동시 NEXT VALUE 값을 보존하는 병합 경로도 같은 방식으로 쓴다.

## Implementation

- `heap_attrinfo_transform_to_disk_keep_form`을 추가했다. 일반 인코딩과 같지만, 가변 열마다 기존 레코드의 형태를 따른다. OOS로 내보내는 결정과 OOS 삽입을 하지 않는다.
  - OOS에 있는 열은 CBRD-27230(#8559)의 `heap_oos_column_plan::reused`/`reused_stub`을 그대로 써서, 기존 stub 24바이트를 검증한 뒤 바이트 그대로 복사한다.
  - `heap_attrinfo_transform_to_disk_internal`의 인자는 `(…, pending, reuse_oos_stubs, keep_form)` 순서다. keep-form은 `reuse_oos_stubs`를 쓰지 않는다.
  - 대체할 레코드가 없으면 release 빌드에서도 오류를 반환한다. 레코드 없이 진행하면 OOS로 내보낸 열을 아무도 삽입하지 않기 때문이다.
- `serial_update_serial_object`(NEXT VALUE, cache 기록)가 이 함수를 쓴다. 바뀌는 값(`current_val`, `started`)은 평소처럼 인코딩된다. NUMERIC은 값이 커지면 저장 바이트가 늘어나므로(최대 +16바이트), 제자리 패치 대신 인코딩을 다시 하는 방식을 택했다.
- `serial_row_write_keep_value`(DDL 병합)도 이 함수를 쓴다. 시스템 class의 클라이언트 행은 inline이므로 병합한 행도 inline으로 남는다. 이전에는 이 경로가 4K page에서 긴 comment를 OOS로 옮길 수 있었고, 그 행의 NEXT VALUE 이미지는 HA slave가 적용하지 못한다(`-1040 missing OOS OID`).
- 기존 행에 OOS 열이 없으면 모든 열이 inline이므로 열 위치를 읽지 않는다. OOS 열이 있을 때만 `or_rep_id()`로 표현 ID가 같은지 확인하고 참조를 읽는다. `OR_GET_REPID`는 HAS_OOS 플래그 비트를 지우지 않으므로 쓰지 않는다.
- 로그 형식은 바뀌지 않는다. serial 행은 `RVREPL_OOS_REUSE`를 만들지 않는다.

## Remarks

- 이 PR은 #8492(CBRD-28035)와 #8496(CBRD-28052)을 대체한다. 두 PR은 "NEXT VALUE가 OOS chain을 쓴다"는 결과를 각각 수습하는 방식이었다. #8434(CBRD-27781)에 의존하지 않는다.
- 첫 커밋은 테스트만 담는다. 수정 전 소스에서 chain 수 테스트와 롤백 테스트가 실패하는 것을 확인했다.
- 이 PR 이후 새 DB에서는 `_db_serial` 행이 OOS를 갖지 않는다. 이전 `feature/oos-merge` 빌드로 NEXT VALUE를 실행해 comment가 OOS로 옮겨진 DB에서는 그 행이 OOS 참조를 유지하고, 그 행의 NEXT VALUE는 HA에서 이전과 같이 적용되지 않는다(이 PR 전에도 같음). 해당 serial에 첫 NEXT VALUE 전에 `ALTER SERIAL <name> COMMENT '<기존 comment>'`를 실행하면 행이 inline으로 바뀌고 이전 chain은 회수된다. 양쪽 노드에서 확인했다.
- 알려진 한계: 4K page에서 행이 약 1008바이트를 넘는 serial(긴 comment)은 이제 inline으로 남으므로, `_db_serial` heap이 `unfill_factor≈0`으로 만들어졌거나 page 예비 공간이 소진된 경우 `current_val`이 커질 때 같은 슬롯에 들어가지 못해 NEXT VALUE가 실패할 수 있다. 이전 코드는 이 경우를 redo 전용 로그 아래 새 OOS chain으로 옮겨 피했는데, 그것이 이 PR이 고치는 버그다. 같은 슬롯 갱신의 공간 부족 실패 자체는 작은 행에서도 develop부터 있던 문제다.
- 리뷰에서 함께 발견한, 이 PR과 무관한 기존 결함은 별도 이슈로 다룬다.
  - [CBRD-28271](https://jira.cubrid.org/browse/CBRD-28271): NEXT VALUE가 공간 확인 전에 redo를 기록한다. release 빌드에서 갱신이 실패한 뒤 크래시가 나면 재시작 시 redo가 실패한다. develop에도 있다.
  - [CBRD-28272](https://jira.cubrid.org/browse/CBRD-28272): relocated 상태의 serial 행을 NEXT VALUE가 home 슬롯에 덮어쓴다. release/11.4에도 있다.
- 새 테스트는 inline comment에서 시작하므로 keep-form의 OOS stub 유지 분기와 DDL 병합 분기는 수동 시험(이전 빌드 DB, gdb로 병합 강제)으로만 확인했다. 두 분기의 자동 테스트는 [CBRD-28273](https://jira.cubrid.org/browse/CBRD-28273)에서 다룬다.
- 검증은 debug 빌드에서 했다. release 빌드는 CI로 확인한다.

### Test Plan

debug 빌드, `--db-page-size=4K` DB 기준. base `feature/oos-merge` `8c478d8559` 위의 head에서 확인했다. 이후 OOS가 `develop`에 머지되어(#7990) 이 PR을 `develop` 위로 rebase했다. 그 develop의 빌드 오류가 #8662로 고쳐진 뒤 `030b650ff7` 위로 다시 rebase했다(head `b6de23c3f9`). 커밋 5개의 내용은 바뀌지 않았다(`git range-diff`에서 모두 동일). 이전 빌드 DB는 이전 base `71993ddb63` 빌드로 만들었다. HA는 한 호스트에서 namespace로 분리한 2노드(heartbeat, copylogdb, applylogdb)로 돌렸다.

| 경우 | 수정 전 | 수정 후 |
|---|---|---|
| `test_oos_sql_serial` (chain 수, `current_val` 크기 증가) | chain 1개, 10개, 10개 남음 | 통과 |
| `test_oos_sql_serial_rollback` (첫/이후 NEXT VALUE, ALTER, CREATE 롤백, 종료 시 cache 기록) | -1398 | 통과 |
| SA와 서버 모드의 롤백, `kill -9` 뒤 복구, 다른 serial의 ALTER/DROP과 섞인 롤백 | SA에서 -1398 | 정상, OOS 레코드 0개, `checkdb` 통과 |
| 15세션 서버 모드 혼합 부하(NEXT VALUE, ALTER, DROP/CREATE, ROLLBACK), `kill -9` 뒤 재시작 | | 중복 값 없음, chain 누수 없음, `checkdb` 통과 |
| 이전 빌드 DB에서 NEXT VALUE 반복(커밋, 롤백, cache 기록) | NEXT VALUE마다 chain 1개 누수 | comment stub 24바이트 동일, OOS 레코드 수 유지 |
| 이전 빌드 DB에서 ALTER SERIAL(커밋/롤백), DDL 병합 경로 강제 실행 | | 커밋 시 inline으로 바뀌고 chain 회수, 롤백 시 원래 행과 chain 복원 |
| HA: 새 DB, 긴 comment serial의 NEXT VALUE | slave `-1040`으로 복제 정지 | 정상 복제 |
| HA: ALTER COMMENT 60회와 NEXT VALUE 20000회 동시 실행 | 5회 중 1회 `_db_serial` OOS 발생, 복제 정지 | 8회 모두 OOS 없음, 정상 복제 |
| HA: DDL 병합 경로를 gdb로 고정 재현 | 병합 행이 OOS, 복제 정지 | 병합 행 inline, 정상 복제 |
| 4K page를 채운 serial 24개의 값을 1에서 2×10^30으로 증가(기본 `unfill_factor`) | | 오류 없음, comment 정상 |
| OOS ctest | | 74개 모두 통과 |
| gha-ci | | head `b6de23c3f9`에서 [run 44705649588](https://github.com/CUBRID/cubrid/actions/runs/44705649588) 진행 중 |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
