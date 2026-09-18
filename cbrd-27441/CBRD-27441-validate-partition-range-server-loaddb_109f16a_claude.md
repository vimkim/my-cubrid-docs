# [CBRD-27441] Validate partition range in server-side loaddb

- JIRA: https://jira.cubrid.org/browse/CBRD-27441
- Source commit: `109f16a` (branch `CBRD-27441-cs-loaddb-bugfix`)
- Base: `develop`

## Purpose

`loaddb` 는 대량의 데이터를 테이블에 넣는 도구다. `unloaddb` 가 만든 object 파일은 `%class` 줄로 행을 넣을 테이블을 지정하는데, 여기에는 부모 테이블뿐 아니라 `t__p__p0` 처럼 실제 행을 보관하는 개별 파티션도 올 수 있다.

client-server 방식(`loaddb -C`)에서 개별 파티션을 대상으로 행을 넣을 때, 그 행의 값이 해당 파티션의 범위에 맞는지 검사하지 않았다. 그래서 범위를 벗어난 값도 그대로 저장·커밋됐다.

- **AS-IS**: `i < 10` 범위의 파티션 `t__p__p0` 에 값 `100` 을 load하면 오류 없이 성공 커밋된다. 같은 값을 일반 SQL `INSERT` 로 넣으면 `Appropriate partition does not exist` 오류로 거부된다. 즉 loaddb 경로만 파티션 정의를 위반한 데이터를 허용했다.
- **TO-BE**: 범위를 벗어난 행은 파티션 오류로 거부하고(종료 코드 0이 아님), 중간 커밋이 없는 실패 배치의 행은 남기지 않는다(부모·개별 파티션 모두 0행). 이후 정상 데이터 load는 정상 동작한다.

## Implementation

서버 로더는 일반 SQL `INSERT` 와 다른 삽입 경로를 쓴다. 근본 원인은 `server_object_loader::flush_records` 가 `pruning_type` (삽입 시 파티션 라우팅·검증 방식을 정하는 값) 을 `DB_NOT_PARTITIONED_CLASS`(=0) 로 고정해 넘긴 데 있다. 그 결과 `locator_insert_force` 의 파티션 검증 분기(`src/transaction/locator_sr.c` 의 `pruning_type != DB_NOT_PARTITIONED_CLASS` 조건)가 건너뛰어지고, 행은 `%class` 가 지정한 힙에 검증 없이 그대로 들어갔다.

### `src/loaddb/load_server_loader.cpp` / `.hpp`

- 정적 헬퍼 `get_class_pruning_type()` 를 추가했다. `%class` 대상 클래스가 실제로 어떤 partitioned 클래스의 파티션이면 `DB_PARTITION_CLASS`, 아니면 `DB_NOT_PARTITIONED_CLASS` 를 돌려준다.
  - `partition_find_root_class_oid()` 로 상위(root) 클래스를 찾는다. 상위가 없거나(자기 자신) 여러 개면 파티션이 아니므로 그대로 `DB_NOT_PARTITIONED_CLASS` 를 유지한다.
  - `heap_get_class_partitions()` 로 root의 파티션 목록을 가져온다. 배열의 0번은 partitioned 클래스 자신이고 1번부터가 실제 파티션이므로, 대상 OID가 그 중 하나와 같을 때만 `DB_PARTITION_CLASS` 로 판정한다.
  - 목록은 `heap_clear_partition_info()` 로 항상 정리한다.
- 멤버 `m_pruning_type` 를 추가하고, `init()` 에서 배치 시작 시 한 번 계산해 저장, `destroy()` 에서 초기화한다.
- `flush_records()` 는 고정 `0` 대신 `m_pruning_type` 를 `locator_insert_force` / `locator_multi_insert_force` 에 넘긴다. 이제 유효하지 않은 행은 `ER_PARTITION_NOT_EXIST`(범위 밖) 또는 `ER_INVALID_DATA_FOR_PARTITION`(다른 파티션에 속함) 로 거부되고, 실패한 배치는 sysop/트랜잭션 abort 로 되돌려진다.

### `src/transaction/lock_manager.c`

- 검증을 켜자 서버가 assert 로 죽는 문제가 드러났다. loaddb 워커 스레드(`TT_LOADDB`)는 락 매니저를 거치지 않고, 배치 시작 시 클래스에 건 BU 락(bulk-update, 대량 적재용 상위 락)에 의존한다. 이 우회는 `lock_object` 에는 있었지만 `lock_subclass` 에는 없었다. 파티션 검증 성공 경로가 `lock_subclass` 를 호출하면서 `lock_internal_perform_lock_object` 의 `assert (thread_p->type != TT_LOADDB)` 를 건드렸다.
- `lock_subclass` 에 `lock_object` 와 같은 형태의 `TT_LOADDB` 우회를 추가했다. 대상 subclass에 이미 BU 락을 보유하면 `LK_GRANTED` 를 돌려주고, 아니면 기존 방어 패턴대로 `assert (false)` + `LK_NOTGRANTED` 로 fail-closed 처리한다. 조건이 `TT_LOADDB` 로 한정되어 일반 트랜잭션에는 영향이 없다.

## Remarks

### 리뷰어가 먼저 볼 곳

- `src/loaddb/load_server_loader.cpp` 의 `get_class_pruning_type()` 판정 로직(상위 클래스 탐색, index 1부터의 루프, 메모리 정리).
- `src/transaction/lock_manager.c` 의 새 `lock_subclass` 우회가 기존 `lock_object` 우회와 일관되는지.

### 범위와 한계

- 확인 범위는 Linux의 client-server 방식(`loaddb -C`) 과 range 파티션이다. `%class` 로 개별 파티션을 지정하는 경우를 다룬다.
- `%class` 로 부모 partitioned 테이블 자체를 지정하는 경우는 이번 변경 대상이 아니다. 이때 `get_class_pruning_type()` 는 `DB_NOT_PARTITIONED_CLASS` 를 유지하므로 기존 동작과 동일하다. 부모 지정 시 행 저장 위치 문제는 별도 분석이 필요하다.
- 성능: 현재 구현은 행마다 `partition_prune_insert` 를 호출하고, 그 안에서 상위 클래스 조회가 매 행 일어난다. 대량 파티션 적재에서 오버헤드가 될 수 있다. 배치 동안 `PRUNING_CONTEXT` 를 하나 유지해 넘기는 최적화는 로더의 scancache/페이지 배치 관리와 상호작용하므로, 정확성 수정과 분리해 후속 작업으로 다루기를 권장한다.

### Test Plan

- 최소 재현: `i < 10` 파티션에 값 `100` load → 종료 코드 0 아님, `Appropriate partition does not exist`, 부모·개별 파티션 0행. 수정 후 통과.
- 회귀 스크립트: 비파티션 테이블 load, 여러 파티션에 유효 행 분배 load, 잘못된 파티션에 속하는 행(범위 안이지만 다른 파티션) 거부 — 모두 통과, core 없음.
- CTP shell test `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls` : 패치된 `partition_tbls.sh` 의 9개 검사 모두 통과(수정 전 6개 실패). 테스트 변경은 `cubrid-testcases-private-ex` 의 동반 PR로 관리한다.
- 2축 코드 리뷰(Standards / Spec) 모두 승인, 차단 지적 없음.
