# [OOS][VACUUM] 재사용된 heap 파일에서 DROP 전 MVCCID를 가진 UPDATE의 OOS 회수를 vacuum이 건너뛴다

**한 줄 요약**: [PR #8434 코드 리뷰](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27781/code-review-pr8434-3e8072f/report.md#pre-existing-reported-separately)가 PR 이전부터 있던 문제(P-2)로 따로 보고한 것이다([PR 요약 댓글](https://github.com/CUBRID/cubrid/pull/8434#issuecomment-6680787439)). DROP된 테이블의 heap 파일을 새 테이블이 재사용한 뒤, DROP 전에 MVCCID를 받은 트랜잭션이 새 테이블에서 OOS 컬럼을 UPDATE하는 경우를 다룬다. vacuum은 그 UPDATE가 버린 chain을 DROP된 파일의 것으로 분류해 건너뛰고, chain은 회수되지 않는다.

## Issue Triage

**이슈 수행 목적**: heap 파일이 재사용된 뒤에도, 새 테이블에서 버려진 OOS chain은 그 UPDATE를 한 트랜잭션의 MVCCID와 관계없이 vacuum이 회수한다.

**이슈 수행 이유**: vacuum은 로그 레코드의 VFID가 DROP된 파일 목록에 있고, 레코드의 MVCCID가 DROP 시점에 기록한 MVCCID보다 작으면 그 레코드를 DROP된 파일의 것으로 보고 건너뛴다. 이 판정은 "재사용된 파일을 바꾸는 트랜잭션은 DROP 뒤에 MVCCID를 받는다"는 가정에 기댄다. DROP 전에 MVCCID를 받고 아직 활성인 트랜잭션은 이 가정을 깬다. 그 트랜잭션이 새 테이블의 OOS 컬럼을 UPDATE하면 회수 알림이 DROP된 파일의 것으로 분류된다. 이 경로는 DROP할 때 heap 파일을 지우지 않고 재사용하는 FILE_HEAP 테이블(`DONT_REUSE_OID`)에서 소스로 확인했다. PR #8434 base에서는 이 회수를 heap UPDATE 로그(`RVHF_UPDATE_NOTIFY_VACUUM`)가 맡았는데, 그 로그도 같은 판정을 받아 건너뛰었다.

**영향**: 건너뛴 chain은 새 테이블의 OOS 파일에 남는다. 레코드는 이미 새 chain을 가리키므로 조회 결과는 틀리지 않는다. 대신 버려진 값의 크기만큼 OOS 공간이 회수되지 않는다. 누수는 그 테이블이 DROP되어 OOS 파일이 함께 제거될 때까지 남는다. 다른 회수 경로가 있는지는 확인하지 않았다. 발생 빈도는 알지 못한다.

**이슈 수행 방안**: TBD - ANALYSIS 단계에서 해결 방안과 구현 범위를 결정한다.

---

## AI-Generated Context

## Description

### 발생 조건

다음 조건이 모두 성립하면 누수가 생긴다. 1-3은 설정과 순서, 4-5는 그 결과다.

1. DROP되는 테이블 X와 새로 만드는 테이블 Y가 모두 FILE_HEAP이다. 즉 `DONT_REUSE_OID`로 만들었거나 `create_table_reuseoid=no`인 세션에서 만들었다. 기본값은 `create_table_reuseoid=yes`이므로 기본 테이블은 해당하지 않는다([system_parameter.c:4689-4695](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/base/system_parameter.c#L4689-L4695)). 서버 파라미터는 `dont_reuse_heap_file=no`(기본값)이다([system_parameter.c:1767-1773](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/base/system_parameter.c#L1767-L1773)).
2. 트랜잭션 T가 X의 DROP이 커밋되기 전에 MVCCID m을 받았고, 그 뒤에도 활성 상태로 남는다.
3. 다른 트랜잭션이 X를 DROP하고 커밋한다. 이 커밋은 dropped-file 항목 (F, Dm)을 남긴다. F는 X의 heap VFID이고, Dm은 그 시점의 다음 MVCCID이므로 m보다 크다. 그 뒤 Y가 X의 heap 파일(VFID F)을 재사용하여 만들어진다. 그 뒤 T가 Y의 행에서 OOS 컬럼을 MVCC UPDATE하여 기존 chain을 버리고 커밋한다.
4. 회수 알림 `RVOOS_NOTIFY_VACUUM`은 VFID F와 MVCCID m을 가진다.
5. vacuum은 dropped-file 항목 (F, Dm)을 찾는다. m < Dm이므로 알림을 건너뛴다.

### 경로 (PR head `2e32517bb`)

- **DROP**: `locator_remove_class`는 `heap_destroy_newly_created`를 `force=false`로 부른다([locator_cl.c:5725-5728](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/transaction/locator_cl.c#L5725-L5728)). `xheap_destroy_newly_created`의 동작은 파일 종류에 따라 다르다([heap_file.c:5596-5628](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L5596-L5628)).
  - FILE_HEAP_REUSE_SLOTS: 파일을 없앤다(`xheap_destroy`).
  - FILE_HEAP: 파일을 없애지 않는다. dropped-file 알림을 postpone으로 기록하고(5615), OOS 파일을 제거하고, `RVHF_MARK_DELETED` postpone으로 heap 파일을 삭제 표시한다(5628).
- **dropped-file 항목**: DROP의 commit postpone에서 항목 (F, Dm)이 추가된다. Dm은 그 시점의 `log_Gl.hdr.mvcc_next_id`다([vacuum.c:6743-6749](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/query/vacuum.c#L6743-L6749)). 같은 자리의 주석은 판정이 기대는 두 가정을 적는다. 첫째, DROP된 파일을 바꾼 트랜잭션은 이미 커밋했으므로 MVCCID가 Dm보다 작다. 둘째, 같은 VFID를 재사용한 새 파일은 "이 호출 뒤에 시작한 트랜잭션"만 바꾸므로 MVCCID가 Dm 이상이다. 조건 2의 T는 둘째 가정을 깬다.
- **재사용**: `heap_create_internal`은 새 테이블이 FILE_HEAP이고 `dont_reuse_heap_file`이 꺼져 있으면, 삭제 표시된 heap 파일을 `file_tracker_reuse_heap`으로 가져와 재사용한다([heap_file.c:4890-4914](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/heap_file.c#L4890-L4914)).
- **알림 기록**:
  - UPDATE는 회수 의도에 자기 MVCCID를 넣는다([oos_file.cpp:3783](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/oos_file.cpp#L3783)).
  - commit 뒤 postpone에서 `RVOOS_NOTIFY_VACUUM`이 기록된다. 이때 `vacuum_info.vfid`는 heap VFID이고, MVCCID는 그 UPDATE의 것이다([oos_file.cpp:3934-3937](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/storage/oos_file.cpp#L3934-L3937)). 3934행 주석은 이 VFID를 쓰는 이유를 "테이블이 DROP되면 vacuum이 알림을 건너뛰게 하려고"라고 적는다.
  - `vacuum_info.vfid`는 로그 주소의 VFID에서 복사된다([log_append.cpp:1003-1006](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/transaction/log_append.cpp#L1003-L1006)).
- **vacuum 판정**:
  - `vacuum_process_log_record`가 VFID가 있는 MVCC 레코드마다 `vacuum_is_file_dropped`를 부른다([vacuum.c:4316-4326](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/query/vacuum.c#L4316-L4326)).
  - `vacuum_find_dropped_file`은 같은 VFID의 항목을 찾고, `MVCC_ID_PRECEDES (mvccid, dropped_file->mvccid)`이면 DROP된 파일로 판정한다([vacuum.c:7017](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/query/vacuum.c#L7017)).
  - 판정된 레코드는 처리 루프에서 `continue`로 건너뛴다([vacuum.c:3636-3643](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/query/vacuum.c#L3636-L3643)). 따라서 `RVOOS_NOTIFY_VACUUM` 처리([3814-3819](https://github.com/CUBRID/cubrid/blob/2e32517bb9ee4690f49907a1c0a4b90786917008/src/query/vacuum.c#L3814-L3819))에 도달하지 않는다.

### PR 이전(base `d52b1889e`)에도 있었다

base에는 `RVOOS_NOTIFY_VACUUM`을 기록하는 코드가 없다. UPDATE가 버린 chain은 heap UPDATE의 MVCC 로그(`RVHF_UPDATE_NOTIFY_VACUUM`)를 vacuum이 처리하면서 undo image를 따라가 지웠다([vacuum.c:3686-3689](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L3686-L3689)). 이 로그도 heap VFID와 UPDATE의 MVCCID를 가진다. 이 로그도 같은 dropped-file 판정을 먼저 받는다([vacuum.c:4332-4338](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L4332-L4338), 비교는 6979행, Dm은 6711행). 판정되면 같은 `continue`로 건너뛴다([vacuum.c:3635-3642](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L3635-L3642)). 따라서 같은 조건에서 base도 chain을 회수하지 않는다. PR은 회수를 기록하는 레코드를 바꿨을 뿐, 판정은 바꾸지 않았다.

### 확인하지 않은 것

- **REUSE_OID 테이블**: 리뷰는 이 문제를 "reuse-OID가 없는 FILE_HEAP 테이블만"으로 한정했다. 소스로 확인한 재사용 경로(삭제 표시 후 재사용)는 FILE_HEAP에만 있다. REUSE_OID 테이블(FILE_HEAP_REUSE_SLOTS)은 DROP 때 파일을 없앤다. 없어진 파일의 VFID를 `file_create`가 새 파일에 다시 줄 수 있는지는 확인하지 않았다. 다시 줄 수 있다면 같은 판정이 REUSE_OID 테이블에도 적용될 수 있다.
- **다른 트랜잭션이 Y를 만든 경우**: T가 그 Y의 행을 UPDATE할 수 있는지 격리 수준별로 확인하지 않았다. T가 Y를 직접 만드는 경우는 아래 재현 절차처럼 가능해 보인다.
- **heap MVCC 레코드**: 같은 판정은 같은 VFID와 MVCCID를 가진 heap MVCC 레코드에도 적용된다. 예를 들어 T가 Y에서 한 DELETE의 정리도 건너뛰어, heap 레코드와 그 chain이 함께 남는지는 확인하지 않았다. 남는다면 문제는 OOS에 한정되지 않는다.
- **다른 정리 경로**: TRUNCATE나 compactdb 같은 경로가 남은 chain을 정리하는지 확인하지 않았다.
- **실행 재현**: 위 내용은 소스로만 확인했다.

### 방향

ANALYSIS에서 검토할 방향은 두 가지다.

- dropped-file 판정이 MVCCID 외의 정보로 파일 세대(generation)를 구분하게 한다.
- 재사용된 파일에서는 판정이 이 경우를 놓치지 않게 한다.

이 판정은 vacuum의 모든 MVCC 레코드에 쓰이므로, 변경 범위는 OOS 회수 알림에 한정되지 않을 수 있다.

## Test Build

소스만 읽었으며, 빌드와 실행은 하지 않았다.

| 기준 | 커밋 | 결과 |
|---|---|---|
| PR #8434 head | `2e32517bb` | `RVOOS_NOTIFY_VACUUM`이 heap VFID와 UPDATE의 MVCCID로 기록되고, dropped-file 판정을 받는다 |
| `feature/oos-merge` (PR base) | `d52b1889e` | `RVHF_UPDATE_NOTIFY_VACUUM`이 같은 판정을 받고, 판정되면 undo image를 따라가는 회수를 하지 않는다 |

## Repro

실행한 재현은 없다. 아래는 제안 절차다. 값 크기는 OOS로 저장될 만큼 커야 한다. 정확한 기준은 ANALYSIS에서 정한다.

```sql
-- 세션 B: X를 만든다
CREATE TABLE x (id INT, v VARCHAR) DONT_REUSE_OID;
COMMIT;

-- 세션 A (autocommit off): DROP 전에 MVCCID를 받는다
INSERT INTO a_other VALUES (1);   -- a_other는 미리 만들어 둔 일반 테이블

-- 세션 B: X를 DROP하고 커밋한다
DROP TABLE x;
COMMIT;

-- 세션 A (같은 트랜잭션 계속): Y를 만들고 OOS 값을 갱신한다
CREATE TABLE y (id INT, v VARCHAR) DONT_REUSE_OID;
INSERT INTO y VALUES (1, REPEAT('a', 20000));
UPDATE y SET v = REPEAT('b', 20000) WHERE id = 1;
COMMIT;
```

1. DROP 전에 `SHOW HEAP HEADER OF x`, Y 생성 뒤에 `SHOW HEAP HEADER OF y`로 `Volid`와 `File_id`를 본다. Y가 X의 heap 파일을 재사용했는지 확인한다. 삭제 표시된 다른 heap 파일이 있으면 다른 파일을 재사용할 수 있다.
2. vacuum이 해당 로그 블록을 처리할 때까지 기다린다. 서버 파라미터 `er_log_vacuum`에 dropped-file 비트(`VACUUM_ER_LOG_DROPPED_FILES`, 32)를 켜 두면, 서버 에러 로그에 dropped-file 판정이 남는다. 그 로그에서 알림이 DROP된 파일로 판정되었는지 확인한다. 이 로그는 `_er_log_debug`로 출력되므로, release 빌드에서 추가 설정이 필요한지는 확인하지 않았다.
3. Y의 OOS 파일에 'a' 값의 chain이 남아 있는지 확인한다. 확인 방법은 정하지 않았다. 예를 들어 OOS 레코드 수를 세는 진단 도구나 단위 테스트 API를 쓸 수 있다.

같은 상황을 `unit_tests/oos/`의 SERVER 모드 테스트로 만들 수도 있다. 그 경우 dropped-file 항목과 재사용을 직접 구성한다.

## Expected Result

- 재사용된 heap 파일에서 MVCC UPDATE가 버린 OOS chain은, UPDATE한 트랜잭션의 MVCCID가 DROP보다 오래되었어도 vacuum이 회수한다.
- DROP된 파일에 속한 레코드는 지금처럼 건너뛴다.

## Actual Result

소스 분석 기준으로 vacuum은 알림을 DROP된 파일의 것으로 판정하고 건너뛴다. 버려진 chain은 Y의 OOS 파일에 남는다. 실행으로 관찰하지 않았다.
