# PR 8491 OOS 읽기 할당 검사 독립 검증

이 문서는 PR #8491 리뷰 5914646248의 질문에 대한 독립 검증 결과다. 독자는 리뷰어 xmilex-git과 OOS 읽기 경로를 유지하는 개발자다. 분석일은 2026-11-17(Asia/Seoul)이며, 조사 지시는 [handoff](oos-read-validation-handoff.md)를 따랐다.

## 결론

리뷰어의 질문은 다음과 같다.

> scan이 visible로 판정한 heap record의 OOS 참조가 그런 page를 가리키는 경로가 있나요?

기준 head `a4fec6f8e2`에서 답은 "있다"이다. 정상 SQL만으로 두 경로를 직접 재현했다.

1. **UPDATE rollback 뒤 vacuum (CBRD-27237).** rollback이 원래 OOS 참조를 가진 행을 되돌린다. 그 뒤 vacuum의 forward walk가 같은 chain을 삭제한다. 이후 그 행을 읽는 scan은 삭제되었거나 재사용된 head slot을 만난다. 이 경로에서는 sector 확인이 아니라 slot 확인과 stamp 확인이 오류를 낸다.
2. **SELECT 안의 PL/CSQL COMMIT과 동시 DROP (새로 확인).** SELECT가 호출한 PL/CSQL 함수가 COMMIT하면 class IS lock과 MVCC snapshot 등록이 해제된다. 그래도 query는 계속 진행된다. 그 사이 다른 세션의 DROP TABLE이 OOS file을 파괴한다. scan은 이미 복사한 참조로 sector가 해제된 head page를 읽는다. 이 경로에서는 sector 확인만 오류를 낸다. release 빌드에서 sector 확인을 끄면 client는 오류 없이 파괴된 file의 byte를 받는다.

두 경로 모두 현재 검사 덕분에 -1397(`ER_HEAP_OOS_CORRUPTED_RECORD`)로 끝난다. 잘못된 byte는 반환되지 않는다. 다만 두 경로는 검사의 정당성보다 상위의 결함이다. 첫 경로는 CBRD-27237이며 PR #8434가 해결 방안을 담고 있다. 둘째 경로는 CBRD-27579가 다루는 문제의 한 증상이다. CBRD-27579는 SQL 문 안에서 호출한 SP의 COMMIT과 ROLLBACK을 거부하기로 했고, 구현 PR #8182는 아직 merge되지 않았다. PR #8182 head `13105c1636`의 `callback_handler::end_transaction ()`은 이번 재현이 쓴 COMMIT을 `ER_SP_TCL_DDL_IN_QUERY`로 거부한다 (`src/method/method_callback.cpp:233`, source 확인, 실행하지 않음).

리뷰어가 보고한 수치는 그대로 재현되었다. release 빌드에서 20,000바이트 값 200행을 읽으면 OOS fetch는 800이다. head 200, continuation 200, 할당 확인 400으로 나뉜다. 할당 확인은 head마다 volume header 1번과 sector table page 1번이다.

기준 head에서 검사 제거는 이 근거로 정당화되지 않는다. 정상 SQL scan이 해제된 sector를 실제로 만날 수 있고, release에서 이를 막는 검사는 sector 확인 하나뿐이다. 비용을 줄이려면 위 경로의 근본 원인을 먼저 고치거나, 같은 보장을 더 싸게 제공하는 방법을 별도로 설계하고 검증해야 한다.

## 대상과 환경

| 항목 | 값 |
| --- | --- |
| PR | [CUBRID/cubrid#8491](https://github.com/CUBRID/cubrid/pull/8491), head `vimkim/cubrid:CBRD-28011-oos-sql-trace`, base `feature/oos-merge` |
| 기준 source | `a4fec6f8e26a36834c3dde4df0ed0af5ecc6d914`. 원래 PR worktree는 변경하지 않았다 |
| OOS 명세 | `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`, SHA-256 `0e9622a8e702b282e0fdd32cf8324c5454a22d6f97f93d7c7ab54d5e3be29a71` |
| debug 실행 | worktree `verify-oos-read-scan-20261117`, source 변경 없음. `debug_gcc`, `cub_server` SHA-256 `6b455ca6aa3447b213c837976d121e501a35345f04088e80308dd05cc202f5c4` |
| debug 민감도 | worktree `verify-oos-read-probe-dbg-20261117`, commit `32ef23f629` (기준 head + 검증 전용 toggle과 test) |
| release 민감도와 PL 재현 | worktree `verify-oos-read-probe-rel-20261117`, commit `0905793f6e` (기준 head + 검증 전용 toggle과 test). `release_gcc_unit`, `-O2 -DNDEBUG`, `cub_server` SHA-256 `a697dc54fdff3c9d66b8cfc0a8cb014ee922037b9db724feecc4f3d78686b8eb` |

검증 전용 commit은 `oos_fix_page_if_oos`에 환경 변수 `CUBRID_OOS_SKIP_SECTOR_PROBE`를 추가한다. 이 변수가 있으면 sector 확인만 건너뛰고 나머지 해제 허용 fix는 그대로 수행한다. 변수가 없으면 기준 head와 같은 경로를 실행한다. toggle을 쓴 모든 server 실행에서 `/proc/<pid>/environ`으로 변수 유무를 확인했다. release commit의 전체 diff는 [verification.patch](oos-read-validation/verification.patch)에 있다. debug commit은 그중 toggle과 첫 file 파괴 test만 담는다.

모든 동시성 실험은 gdb non-stop 모드의 읽기 전용 관찰로 순서를 맞췄다. 관찰한 event를 기다렸으며 sleep을 순서의 근거로 쓰지 않았다. inferior 함수 호출과 memory 쓰기는 하지 않았다.

## 할당 검사가 확인하는 것

OOS head는 `oos_fix_page_if_oos`가 `pgbuf_fix_if_not_deallocated`로 fix한다 (`src/storage/oos_file.cpp:2552-2580`). 이 함수는 순서대로 다음을 확인한다.

1. `disk_is_page_sector_reserved`가 volume header와 sector table page를 fix하여 page의 sector가 예약되어 있는지 확인한다 (`src/storage/page_buffer.c:16172`, `src/storage/disk_manager.c:4244-4316`). 리뷰어가 말한 추가 fix 2번이 이것이다. 예약되지 않았으면 page 없이 성공을 반환한다.
2. `OLD_PAGE_MAYBE_DEALLOCATED`로 대상 page를 fix한다. page가 `PAGE_UNKNOWN`이면 `ER_PB_BAD_PAGEID`를 지우고 page 없이 성공을 반환한다 (`page_buffer.c:2574-2606`, `:16187-16200`).
3. `oos_fix_page_if_oos`가 page type이 `PAGE_OOS`가 아니면 page를 놓는다 (`oos_file.cpp:2570`).
4. head chunk를 읽을 때 slot 존재, header 크기, identity stamp, chunk index, 전체 길이를 확인한다 (`oos_file.cpp:2601-2767`).

1번은 page 하나의 할당 여부가 아니라 sector의 예약 여부만 본다. file 안에서 해제된 page는 sector가 예약된 채 남으므로 2번이 잡는다. 1번만 결정하는 경우는 file 전체가 파괴되어 sector가 반환된 경우다.

debug와 release에서 1번의 역할이 다르다.

- debug 빌드는 모든 fix 전에 page validation을 실행한다 (`page_buffer.c:2309`). 기본 수준은 FETCH(1)이며, 예약되지 않은 sector의 page를 fix하면 assert로 종료한다 (`page_buffer.c:11797-11816`, `disk_manager.c:4328`). 1번은 해제 허용 fix가 이 assert에 닿지 않게 한다.
- release 빌드는 page validation이 컴파일되지 않는다 (`page_buffer.c:11776-11783`). 1번이 없으면 파괴된 file의 page를 그대로 fix한다. 그 page의 이전 image가 disk에 남아 있으면 type, slot, stamp가 모두 일치한다. 따라서 오류 없이 이전 byte를 반환한다.

### 추가 fix의 구성을 재현했다

release 빌드(`release_gcc_unit`, warm buffer)에서 20,000바이트 값 200행을 full scan으로 읽고 SQL trace를 기록했다. 문자열 압축은 꺼서 값이 OOS에 저장되게 했다. `SHOW HEAP OOS`는 200행에 대해 400 record, 401 page를 보고했으므로 값 하나가 OOS page 2개를 쓴다.

| server 환경 | scan fetch | OOS fetch | `disk_is_page_sector_reserved` 호출 |
| --- | --- | --- | --- |
| 기준 (확인 수행) | 802 | 800 | 200, 전부 `oos_fix_page_if_oos` 아래 |
| `CUBRID_OOS_SKIP_SECTOR_PROBE=1` | 402 | 400 | 0 |

각 환경에서 4번씩 실행했고 모든 실행의 값이 같았다. OOS fetch는 `oos_read`와 `oos_read_many` 안에서 일어난 모든 `pgbuf_fix`를 센다. 따라서 800은 head 200, continuation 200, volume header 200, sector table 200이다. fetch는 buffer 접근 횟수이며 I/O나 시간이 아니다. OOS time은 모든 warm 실행에서 0 ms로 출력되었다. 이번 조사는 실행 시간을 측정하지 않았으므로 속도 개선 폭을 주장하지 않는다.

## 정상 SQL 경로 판정

판정 상태는 handoff의 다섯 가지를 쓴다. "실행 확인"은 기준 head의 실제 SQL로 재현했다는 뜻이다. "source 확인"은 코드만 추적했다는 뜻이다.

| 경로 | 판정 | 근거 |
| --- | --- | --- |
| serial cached heap scan과 committed UPDATE 또는 DELETE의 vacuum | 추적한 범위에서 보호 확인 (실행 확인) | reader가 등록한 oldest visible MVCCID가 vacuum block을 거부했다. reader commit 뒤 같은 block이 통과하고 같은 head가 회수되었다 |
| UPDATE의 ROLLBACK, ROLLBACK TO SAVEPOINT | 정상 경로의 반례 확인 (실행 확인) | 아래 반례 1 |
| SELECT 안의 PL/CSQL COMMIT과 동시 DROP TABLE | 정상 경로의 반례 확인 (실행 확인) | 아래 반례 2 |
| SELECT 안의 PL/CSQL COMMIT과 committed UPDATE의 vacuum | 정상 경로의 반례 확인 (실행 확인) | 반례 2의 변형. vacuum이 chain을 회수한 뒤 slot 확인이 -1397을 냈다. 삭제된 head가 같은 chain이라는 점은 slot 부재로 추론했다 |
| DROP, TRUNCATE와 transaction 끝까지 진행하는 SELECT | 추적한 범위에서 보호 확인 (source 확인) | SELECT는 실행 시 IS lock을 얻어 transaction 끝까지 유지한다 (`src/query/xasl_cache.c:1112-1141`, `src/transaction/lock_manager.c:7707-7712`). DROP과 TRUNCATE는 SCH-M이 필요하다. 반례 2의 대조군에서 DROP이 SCH-M 대기로 막힌 것을 실행으로 확인했다 |
| 같은 transaction의 후속 DML | 추적한 범위에서 보호 확인 (source 확인) | MVCC UPDATE는 새 version에 새 chain을 쓴다. 이전 chain은 vacuum만 지운다 (`src/storage/heap_file.c:14161-14193`) |
| 자기 INSERT의 rollback | 추적한 범위에서 보호 확인 (source 확인) | transaction이 끝날 때 진행 중인 query가 없어야 한다 (`src/query/query_manager.c:2407-2420`). PL 세션은 예외이며 반례 2와 같은 범주다 |
| parallel heap, index, UNION worker의 정상, 오류, 중단 종료 | 추적한 범위에서 보호 확인 (source 확인) | leader가 scan을 닫기 전에 worker를 기다린다 (`src/query/parallel/px_scan/px_scan.cpp:1953-2015`, `px_task_manager.cpp:69-74`) |
| parallel heap scan의 출력 목록에서 COMMIT하는 SP | incomplete | worker가 scan하는 동안 leader의 SP가 transaction을 끝낼 수 있다 (`px_scan_checker.cpp:285-293`). 실행하지 않았다 |
| partition, page batch, local page copy, lazy 속성 읽기 | 추적한 범위에서 보호 확인 (source 확인) | 복사본과 `lazy_recdes`는 scan 안에서만 산다. partition은 같은 transaction descriptor의 snapshot을 쓴다 |
| query 결과 list file과 holdable cursor | 추적한 범위에서 보호 확인 (source 확인) | list file은 참조가 아니라 풀린 값을 저장한다 (`src/query/query_opfunc.c:666-712`) |
| in-place UPDATE (ALTER domain 변경, partition 재분배) | 추적한 범위에서 보호 확인 (source 확인) | SCH-M으로 reader를 배제한다. 다른 in-place caller는 OOS 참조가 없는 record를 쓴다 |
| MVCC 비활성 class `_db_ha_apply_info`의 비고정 scan | incomplete (source 반례 후보) | `copied_log_path`가 약 3.8 KB 이상이면 OOS로 갈 수 있다. index scan이나 join의 바깥 scan은 page latch를 놓은 뒤 값을 읽는다. HA applier의 UPDATE는 commit 전에 이전 chain을 즉시 지운다 (`heap_oos.cpp:957-1037`). 실행하지 않았다. snapshot 없는 OOS reader와 회수의 겹침은 CBRD-27981이 조사 중이다 |
| SA 모드에서 stored function이 같은 table을 DML | incomplete (source 반례 후보) | SA에서는 eager delete가 바깥 scan이 가진 참조의 chain을 즉시 지울 수 있다. `heap_oos.cpp:923-929`의 "SA에는 reader가 없다"는 설명이 이 경우를 다루지 않는다. 실행하지 않았다 |
| restart recovery, sysop abort 뒤 slot 재사용 | 범위 밖 | 이번 질문의 reader 수명과 별개인 slot undo 안전성 문제다 |

### 반례 1. UPDATE rollback 뒤 vacuum이 살아 있는 chain을 지운다

rollback은 UPDATE 이전 image를 원래 OOS 참조와 함께 되돌린다 (`heap_file.c:19326-19352`). 그러나 rollback된 UPDATE의 `RVHF_UPDATE_NOTIFY_VACUUM` log record는 vacuum 대상으로 남는다. vacuum은 dropped file 여부와 rcvindex만 확인하고 undo image를 푼다 (`src/query/vacuum.c:4409-4418`). commit 여부는 확인하지 않는다. 그 다음 undo image의 모든 chain을 삭제한다 (`vacuum.c:3748-3751`, `src/query/vacuum_oos.cpp:155-206`). 되돌아온 행의 참조와 vacuum이 지우는 참조는 head OID와 stamp가 같으므로 delete 쪽 identity 확인도 이를 막지 못한다.

```sql
CREATE TABLE rb_t (id INT PRIMARY KEY, v VARCHAR);
INSERT INTO rb_t VALUES (1, <20000바이트 값 A>);
COMMIT;
UPDATE rb_t SET v = <20000바이트 값 B> WHERE id = 1;
ROLLBACK;   -- 또는 SAVEPOINT s; UPDATE ...; ROLLBACK TO SAVEPOINT s; COMMIT;
-- WAL을 진행시켜 vacuum이 rollback된 UPDATE의 block을 처리하게 한다
SELECT v FROM rb_t WHERE id = 1;
```

debug 빌드에서 세 번 실행했다. 관찰 순서는 다음과 같다.

1. rollback 직후 행은 원래 값 20,000바이트를 정확히 반환했다. head OID와 stamp도 UPDATE 이전과 같았다.
2. vacuum이 해당 block에서 `vacuum.c:3751`을 실행했다. `oos_delete`는 저장해 둔 원래 head와 stamp에 대해 `OOS_DELETE_RECLAIMED`를 반환했다.
3. 같은 SELECT가 -1397로 실패했다. slot 부재 확인(`oos_file.cpp:2611`)이 오류를 냈다. head page는 여전히 `PAGE_OOS`였고 sector는 예약 상태였다.
4. 새 20,000바이트 INSERT가 같은 head page의 slot 0을 재사용했다. 이후 읽기는 stamp 불일치 확인(`oos_file.cpp:2751`)으로 실패했다. 새 chain의 chunk index와 전체 길이는 원래 참조와 같았으므로 stamp만 둘을 구분했다. 새 chain의 byte는 반환되지 않았다.
5. 대조군인 committed UPDATE 행은 모든 단계에서 새 값을 정확히 반환했다.

이번 실행에서 vacuum의 page 회수는 32번 모두 `OOS_RECLAIM_DEFERRED`였다. 따라서 이 경로로 head page가 해제되는 경우는 실행으로 확인하지 못했다. 이 결함은 조상 `dcbf09e`에서 기록된 CBRD-27237과 같은 기전이며, 기준 head에서 다시 재현되었다. 해결 방안인 postponed notification과 forward walk 제거는 PR #8434에 있고 아직 merge되지 않았다.

### 반례 2. PL/CSQL COMMIT 뒤 DROP이 reader가 참조하는 file을 파괴한다

PL 세션이 transaction을 끝내면 query manager는 진행 중인 query를 그대로 둔다 (`src/query/query_manager.c:2407-2431`). 이 동작은 의도된 것이다. 그러나 COMMIT은 transaction의 lock과 MVCC 등록을 해제한다 (`src/transaction/log_tran_table.c:4483-4504`). 바깥 scan은 이미 복사한 heap record의 OOS 참조를 이후에 읽는다.

```sql
CREATE OR REPLACE FUNCTION f_commit (p INT) RETURN INT AS LANGUAGE PLCSQL
BEGIN
  COMMIT;
  RETURN 1;
END;

-- 세션 1
SELECT id, v FROM t WHERE f_commit (id) = 1;
-- 또는 index scan: SELECT id, v FROM t WHERE id > 0 AND f_commit (id) = 1 USING INDEX pk_t_id;

-- 세션 2, 세션 1이 v를 읽기 전에
DROP TABLE t;
COMMIT;
```

release 빌드에서 세션 1을 `oos_read` 진입에서 멈추고 다음을 관찰했다.

1. PL 함수가 `log_commit`을 실행했다. 멈춘 동안 `cubrid lockdb`는 세션 1의 lock을 0개로 보고했다. snapshot도 무효였다.
2. 대조군 함수 `f_nocommit`에서는 IS lock이 유지되었고 DROP은 SCH-M lock 대기로 막혔다.
3. index scan에서는 DROP이 세션 1이 멈춘 동안 끝났다. table scan에서는 OOS file 파괴가 실행된 뒤 DROP이 scan이 잡은 heap page latch에서 기다렸다. 두 경우 모두 head page의 sector가 반환되었다.
4. 확인을 수행하는 server에서 세션 1을 재개하자 `disk_is_page_sector_reserved`가 `DISK_INVALID`를 반환했다. 이어서 `oos_stale_head_page_read_error`가 -1397을 설정했다. client는 행 없이 오류를 받았다.
5. `CUBRID_OOS_SKIP_SECTOR_PROBE=1` server에서 DROP 전에 checkpoint로 head page를 disk에 기록했다. 그 상태에서 재개하자 client는 오류 없이 두 행을 받았다. 두 값은 파괴된 table의 원래 20,000바이트와 byte 단위로 같았다. table scan과 index scan 모두 같았다.

5번에서 반환된 byte는 scan 시작 시 보였던 값과 같다. 그러나 그 byte는 이미 반환된 storage에서 왔다. sector가 다른 file에 다시 예약되면 같은 위치에 다른 file의 page가 올 수 있다. 이 경우는 실행하지 않았다. 새 page가 OOS page가 아니면 type 확인이, 같은 slot의 OOS chain이면 stamp 확인이 잡는다. 이는 source에서 추론한 결과다. continuation page는 head 확인 뒤 일반 `OLD_PAGE`로 fix하며 stamp를 비교하지 않는다 (`oos_file.cpp:2663-2705`). head 확인이 먼저 실패하므로 이번 실행에서는 continuation page를 읽지 않았다.

## 저수준 API의 계약

`oos_read`와 `oos_read_many`는 무효 참조를 받을 수 있다는 계약으로 작성되었다. 정상 scan의 읽기도 같은 API를 쓰며, 반례 1과 2는 정상 scan이 실제로 무효 참조를 넘길 수 있음을 보인다. 따라서 "정상 scan에는 무효 참조가 오지 않는다"는 가정으로 두 계약을 분리할 근거는 기준 head에 없다.

직접 무효 참조를 넘기는 unit test로 두 빌드의 계약을 확인했다.

| 실험 | debug, 확인 수행 | debug, 확인 생략 | release, 확인 수행 | release, 확인 생략 |
| --- | --- | --- | --- | --- |
| 기존 identity stamp test 33개(fixture 27, pure 6)와 `test_oos_remove_file` 8개 | 전부 통과 | 전부 통과 | 전부 통과 | 전부 통과 |
| file 파괴 뒤 stale 읽기, head page가 buffer에만 있음 | -1397 | SIGABRT, `disk_manager.c:4328` assert | -1397 | -1397 |
| file 파괴 뒤 stale 읽기, head page를 disk에 기록 | 실행하지 않음 | 실행하지 않음 | -1397 | 성공 반환, 원래 byte 전달 |

기존 test는 file 안에서 page만 해제하므로 sector가 예약된 채 남는다. 그래서 확인을 생략해도 결과가 같다. debug test binary에서 "sector 미예약" 반환은 새로 추가한 file 파괴 test에서만 일어났다. release의 buffer-only 경우는 file 파괴가 buffer page를 disk에 기록하지 않고 버리기 때문에 확인 없이도 실패한 것으로 추론한다. 정확한 분기는 증명하지 않았다.

이 결과는 API의 무효 입력 처리를 보인다. 정상 scan이 그 입력을 만든다는 증거는 위의 반례 1과 2다.

## 검사가 도입된 동기

검사는 `29fc3567fb` "[CBRD-26950] Check page type and identity before touching an OOS chain"에서 도입되었다. commit message는 stale 물리 참조, `OLD_PAGE`의 debug abort, slotted page로 잘못 해석되는 retyped metadata, 거부 전 payload 복사, head가 아닌 chunk의 삭제를 문제로 든다. 같은 message가 head page마다 cached volume page fix 2번이 추가된다고 밝히며, 비용은 측정하지 않았다고 적는다. 추가된 test는 참조를 직접 보관한 뒤 slot 부재, page 해제, head 재사용, continuation 재사용, head가 아닌 일치, metadata 재사용, 중단을 실행한다.

따라서 도입 동기는 실제 SQL 경합의 재현이 아니라 API에 직접 넘긴 stale 참조와 명세의 손상 처리 요구였다. 이번 조사는 그 뒤에 정상 SQL 경로 두 개를 찾았다.

## 검사를 제거할 수 있는가

기준 head에서는 제거할 수 없다고 판단한다. 근거는 다음과 같다.

- 반례 2에서 release 빌드의 sector 확인은 정상 SQL scan이 반환된 storage를 읽는 것을 막는 유일한 검사였다.
- debug 빌드에서 sector 확인을 빼면 같은 입력이 assert로 server를 종료한다.
- 반례 1은 sector 확인이 아니라 slot과 stamp 확인에 의존한다. 이 확인들도 정상 scan에 필요하다.

비용을 줄이는 방향은 두 가지가 있다. 어느 쪽도 이번 조사에서 구현하거나 측정하지 않았다.

1. 근본 원인을 고친다. PR #8434가 반례 1을 제거한다. 반례 2는 PL COMMIT 뒤 진행 중인 query가 class lock과 snapshot 없이 계속 실행되는 문제이며, CBRD-27579의 규칙 1(문장 안 TCL 거부)이 막는다. 구현 PR #8182가 merge되면 이 경로는 닫힌다 (source 확인). 이 사례는 CBRD-27579에 추가 사례로 보고한다. 두 PR이 merge되고 나머지 incomplete 경로를 닫은 뒤에야 scan 전용 빠른 경로를 논의할 수 있다.
2. 같은 보장을 더 싸게 제공한다. 예를 들어 OOS file 파괴를 file 단위 incarnation으로 감지하거나, transaction이 class lock을 보유한 동안 sector 확인을 생략하는 방법이 있다. 후자는 `pgbuf_fix_if_not_deallocated`의 기존 주석이 제안한 방향이다 (`page_buffer.c:16168-16171`). 다만 반례 2에서는 PL COMMIT이 lock을 해제했으므로 lock 보유 판단이 실제 보유 상태를 따라야 한다.

어느 방향이든 debug와 release에서 직접 stale 입력, 다중 page 읽기, grouped 읽기의 부분 출력, 실제 회수와 함께 동작하는 SQL reader를 다시 검증해야 한다.

## 증거와 재실행

원시 log와 script는 저장소 밖 `/home/vimkim/temp/cbrd-28011-read-validation-20261117/`에 있다.

| 증거 | 위치 | 내용 |
| --- | --- | --- |
| reader 수명 source 추적 | `scan-lifetime.md` | snapshot 등록, 해제, vacuum horizon |
| 정상 scan 실행 | `normal-runtime.md`, `normal-runtime/` | committed UPDATE와 DELETE 보호, 양성 대조군 |
| API와 도입 이력 | `api-history.md` | 검사 항목, caller 목록, 도입 commit |
| 삭제 경로 목록 | `alternate-deleters.md` | eager, vacuum, rollback, page 회수, file 파괴 |
| lock 경로 추적 | `lock-paths.md` | DROP, TRUNCATE, MVCC 비활성 class, in-place, SA |
| transaction과 parallel 추적 | `txn-parallel-paths.md` | 같은 transaction, rollback, parallel worker |
| 반례 1 실행 | `rollback-runtime.md`, `rollback-runtime/` | debug 세 번 실행, 단계별 확인 위치 |
| 반례 2 실행 | `plcommit-runtime.md`, `plcommit-runtime/` | release, 확인 수행과 생략 비교 |
| debug 민감도 | `probe-debug.md`, `probe-debug/` | unit test 결과와 assert backtrace |
| release 민감도와 fetch | `probe-release.md`, `probe-release/` | unit test 결과, trace, gdb 호출 횟수 |
| 판단 기록 | `decisions.tsv` | 조사 중 내린 판단과 근거 |

각 보고서에 실행 명령, 설정, 관찰 event, 한계가 있다. 각 검증 worktree와 전용 DB는 재실행을 위해 남겼다.

## 남은 확인

- 반례 1에서 vacuum이 head page를 실제로 해제하는 경우와 release 빌드 실행.
- 반례 2에서 해제된 sector를 다른 file이 다시 예약하는 경우, PL ROLLBACK 변형, debug 빌드 실행.
- PR #8182를 적용한 빌드에서 반례 2가 `ER_SP_TCL_DDL_IN_QUERY`로 끝나는지 실행 확인.
- parallel heap scan의 출력 목록에서 COMMIT하는 SP.
- `_db_ha_apply_info`와 SA 모드 stored function의 실행 재현.
- 할당 확인의 실행 시간 비중. 측정하려면 benchmark 절차를 따로 적용해야 한다.

## PR 답변 초안

아래 초안은 게시하지 않았다.

> 질문 감사합니다. 기준 head `a4fec6f8e2`에서 따로 확인해 보니, scan이 visible로 판정한 행의 OOS 참조가 삭제되었거나 반환된 page를 가리키는 정상 SQL 경로가 두 개 있었습니다. 둘 다 실제 SQL로 재현했습니다.
>
> 1. UPDATE를 ROLLBACK(또는 ROLLBACK TO SAVEPOINT)하면 행이 원래 OOS 참조로 돌아옵니다. 그런데 vacuum의 forward walk가 rollback된 UPDATE의 log record도 처리해서 그 chain을 지웁니다(CBRD-27237, PR #8434가 해결 방안). 이후 같은 행을 읽으면 slot 부재나 stamp 불일치로 -1397이 납니다. 이 경로는 sector 확인이 아니라 slot과 stamp 확인이 막습니다.
> 2. SELECT가 호출한 PL/CSQL 함수가 COMMIT하면 IS lock과 snapshot 등록이 풀리지만 query는 계속 진행됩니다. 그 사이 다른 세션의 DROP TABLE이 OOS file을 파괴하면, scan은 이미 복사한 참조로 sector가 반환된 head page를 읽습니다. 지금은 `disk_is_page_sector_reserved`가 `DISK_INVALID`를 돌려 -1397로 끝납니다. release 빌드에서 이 확인만 끄고 같은 순서를 실행하면 client가 오류 없이 파괴된 table의 byte를 받았습니다. debug 빌드에서는 page validation assert로 종료됩니다.
>
> 말씀하신 수치도 재현됐습니다. release에서 20000바이트 200행이면 OOS fetch 800이 head 200, continuation 200, volume header 200, sector table 200으로 나뉩니다. 실행 시간은 측정하지 않았습니다.
>
> 그래서 지금은 확인을 빼기 어렵다고 봅니다. 비용을 줄이려면 위 두 경로를 먼저 막거나, file 파괴를 더 싸게 감지하는 방법을 따로 설계하고 검증해야 할 것 같습니다. 두 번째 경로는 SQL 문 안의 SP COMMIT을 거부하는 CBRD-27579(PR #8182)가 막을 것으로 봅니다. 코드로만 확인했고, CBRD-27579에 추가 사례로 남기려고 합니다. #8434와 #8182가 들어간 뒤 남는 경로를 다시 보고 확인 생략 여부를 판단하면 좋겠습니다. parallel scan 안의 SP COMMIT, HA apply info, SA 모드 같은 경로는 아직 source로만 봤습니다. 자세한 내용은 검증 보고서에 정리했습니다.
