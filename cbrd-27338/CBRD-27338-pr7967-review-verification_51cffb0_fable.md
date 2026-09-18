# [CBRD-27338] PR #7967 리뷰 검증 노트 — bestspace 파기 시점 이동

- 대상 PR: <https://github.com/CUBRID/cubrid/pull/7967> (head `51cffb0f5`, base `develop`, merge-base `3d7a66b89`)
- 이슈: <http://jira.cubrid.org/browse/CBRD-27338> — debug 빌드 log-flush 데몬의 `cub_free` core. 원인은 DROP TABLE 과 vacuum 워커가 겹칠 때 bestspace 객체의 use-after-free.
- 검증 환경: debug 빌드(gcc, CMake debug preset), SA 모드 `csql`, gdb breakpoint. 문서 내 모든 파일:라인은 PR head `51cffb0f5` 기준.
- 작성: 리뷰 보조 AI 에이전트(Claude Fable)가 수행한 검증을 정리. 리뷰어: dhkim.

## Summary

최종 diff 는 `xheap_destroy ()` / `xheap_destroy_newly_created ()` 의 즉시 `cubstorage::bestspaces.destroy (hfid)` 를 **제거하지 않고** `PRM_ID_DISABLE_VACUUM` 가드로 감싼다(+13/−2). vacuum 활성(기본) 구성에서는 postpone 핸들러 `vacuum_rv_notify_dropped_file ()` 이 워커 배리어 통과 후 파기를 전담하고, vacuum 비활성 구성에서만 종전처럼 즉시 파기한다.

소스 추적과 동작 실험 모두 이 설계가 성립함을 확인했다. 단, `vacuum_disable` 은 hidden 파라미터라 **기본 CI 구성에서는 새로 추가된 분기가 한 번도 실행되지 않는다** — 아래 동작 검증이 그 공백을 메우기 위한 것이다.

## Source verification

수정이 의존하는 명제를 develop 코드에서 하나씩 확인했다.

### 1. postpone 핸들러가 정말 안전한 지점에서 파기하는가

- `RVVAC_NOTIFY_DROPPED_FILE` 의 복구 함수 등록: `vacuum_rv_notify_dropped_file` 이 **undo 와 run-postpone 양쪽**에 등록되어 있다 (`src/transaction/recovery.c:722-727`).
- 핸들러 내부 순서 (`src/query/vacuum.c`):
  1. `vacuum_add_dropped_file (...)`
  2. `vacuum_notify_all_workers_dropped_file (vfid, mvccid)` — 모든 워커가 새 dropped-files 버전을 게시할 때까지 대기
  3. `cubstorage::bestspaces.destroy (&rcv_data->vfid)` (`src/query/vacuum.c:6437`)
- 배리어의 유효성: 워커는 로그 블록 하나를 PROCESS_LOG → EXECUTE 두 단계로 처리하며, dropped-files 버전 게시는 **다음 블록의 PROCESS_LOG 에서만** 일어난다. 따라서 배리어가 풀리는 시점에는 위험 구간(EXECUTE 중 `bestspaces.find()` 반환 포인터 사용)이 끝나 있고, 이후 블록은 dropped 확인에 걸린다. 배리어는 `VACUUM_WORKER_STATE_INACTIVE` 워커를 건너뛴다.

### 2. 변경된 두 경로 모두 그 핸들러에 도달하는가

- `xheap_destroy ()`: `vacuum_log_add_dropped_file ()` 경유로 postpone 기록 (`src/storage/heap_file.c:5447`).
- `xheap_destroy_newly_created ()`: `RVHF_MARK_DELETED` 와 **별도로, 그보다 먼저** `RVVAC_NOTIFY_DROPPED_FILE` postpone 을 직접 기록 (`src/storage/heap_file.c:5501`).
- `log_do_postpone ()` 은 전방 스캔(forward scan, `src/transaction/log_manager.c:8302`)이므로, 두 경로 모두에서 bestspace 파기 postpone 이 파일 파기 postpone(`file_postpone_destroy` / `RVHF_MARK_DELETED`)보다 **먼저 실행**된다 → VFID 가 재사용되기 전에 레지스트리 엔트리가 사라진다.
- `log_can_skip_redo_logging ()` 은 이 기록에 대해 false (`pgptr == NULL`) — postpone 이 실제로 기록된다.

### 3. vacuum 비활성 구성에서 가드가 필요한가 (가드의 전제)

- `vacuum_log_add_dropped_file ()` 이 `PRM_ID_DISABLE_VACUUM` 에서 early-return (`src/query/vacuum.c:6140`) → postpone 자체가 안 남는다.
- `vacuum_initialize ()` 자체가 스킵 (`src/base/boot_sr.c:2392` 부근) → 핸들러를 대신 실행할 주체가 없다.
- 즉 가드 없이 두 즉시 파기를 제거만 하면, vacuum 비활성 구성에서 bestspace 엔트리가 leak 되고 VFID 재사용 시 stale 엔트리 위험이 생긴다. 이 구성에는 경쟁할 vacuum 워커도 없으므로 즉시 파기가 안전하다 — 가드의 논리가 성립.

### 4. 파라미터 특성

- `vacuum_disable`: `PRM_FOR_SERVER | PRM_HIDDEN`, `PRM_CLEAR_DYNAMIC_FLAG` (`src/base/system_parameter.c:3863-3872`). 런타임 변경 불가이므로 가드 판정의 torn-read 우려 없음. hidden 이므로 기본 CI 구성/일반 사용자 구성에서는 항상 false.

## Behavioral verification (smoke test)

### 방법

- debug 빌드에 gdb breakpoint 를 걸어 새 분기의 실행 여부를 직접 관측:
  - `src/storage/heap_file.c:5465` — `xheap_destroy ()` 의 가드 내 즉시 파기
  - `src/storage/heap_file.c:5513` — `xheap_destroy_newly_created ()` 의 가드 내 즉시 파기
- SA 모드 `csql -S` 로 세 가지 시나리오를, 기본 구성과 `cubrid.conf` 에 `vacuum_disable=yes` 를 준 구성에서 각각 실행:
  1. **commit leg**: `CREATE TABLE` → `INSERT` → `DROP TABLE` (autocommit)
  2. **newly-created leg**: autocommit off, 같은 트랜잭션에서 `CREATE` → `DROP` → `COMMIT`
  3. **rollback leg**: `CREATE`+`INSERT`+`COMMIT` → `DROP` → `ROLLBACK` → `INSERT` → `SELECT COUNT(*)` → `COMMIT` → `DROP`+`COMMIT`

### 결과

| 시나리오 | 기본 구성 (vacuum on) | `vacuum_disable=yes` |
|---|---|---|
| commit leg | 정상 완료, **BPHIT 없음** | DROP 시 **BPHIT 5465**, 정상 완료 |
| newly-created leg | 정상 완료, BPHIT 없음 | DROP 시 **BPHIT 5465**, 정상 완료 |
| rollback leg | 정상 완료, BPHIT 없음 | DROP 시 **BPHIT 5465** ×2 (rollback 된 DROP + 마지막 DROP), 정상 완료 |

- 기본 구성에서는 새 분기가 **한 번도 실행되지 않는다**. 파기는 전부 postpone 핸들러 소관 — 설계 의도와 일치.
- `vacuum_disable=yes` 에서는 모든 DROP 이 즉시 파기 분기를 실행하며 기능 이상 없음. rollback leg 에서 DROP→ROLLBACK 후 테이블은 살아 있고(`INSERT`/`SELECT` 정상), bestspace 는 이미 파기됐다가 다음 INSERT 에서 재구축되는 종전 동작이 이 구성에서 유지됨을 확인.
- 실행 후 서버/CSQL 에러 로그에 assert/에러 없음.

### 관측 사항

- `heap_file.c:5513` (`xheap_destroy_newly_created`) 분기는 위 SQL 시나리오로는 도달하지 않았다. 같은 트랜잭션에서 생성·삭제해도 `xheap_destroy` (5465) 로 라우팅된다. 가드 모양이 5465 와 동일하므로 기능상 우려는 없으나, 이 분기는 간접 검증에 그친다.
- 이 스모크는 **기능 경로 검증**이다. 원 이슈의 레이스(vacuum EXECUTE 단계와 DROP 의 경합, `bug_bts_12632`) 자체의 재현/비재현 확인은 포함하지 않는다.

## Remaining notes (pre-existing, out of scope)

- `vacuum_disable=yes` 에서 **CREATE 롤백** undo 경로(`src/storage/heap_file.c:4977` 부근)는 postpone 핸들러도, 즉시 파기 대응도 없어 bestspace 엔트리가 leak 될 수 있다(heap 재사용 시 `heap_file.c:4822` 가 부분 완화). 이 PR 이전부터 있던 비대칭.
- mark-deleted 경로는 `heap_delete_hfid_from_cache (class_oid)` 에 `class_oid = NULL` 을 전달해 해당 캐시 정리가 스킵된다. bestspace 파기는 VFID 키라 이 수정과는 무관. 역시 pre-existing.
- 배리어의 버전 비교가 wraparound-unsafe 한 raw 비교라는 점도 pre-existing 이며 이 diff 밖.
