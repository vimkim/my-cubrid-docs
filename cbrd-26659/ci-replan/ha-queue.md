# CBRD-26659: 여러 OOS 값을 함께 복제하는 HA TC와 찾은 결함

작성: 2026-10-28 (Asia/Seoul). Work545. 이 문서는 실행 증거와 남은 범위를 기록한다. 새 spec이나 승인된 테스트 행렬이 아니다. 두 노드 구성은 [두 노드 OOS HA 복제](ha-replication.md), 장애 전환은 [장애 전환 TC](ha-failover.md)에 있다.

## 결론

한 번에 많은 OOS 값을 slave에 복제하는 경로를 진입점 두 개로 검증한다. `cbrd_26659_ha_queue`는 `ha_copy_sync_mode=sync`, `cbrd_26659_ha_async`는 `async`로 같은 쓰기를 한다. 각 노드의 모든 OOS 값을 그 행의 SQL 모델과 비교한다.

- **실제 PR CI에서 통과했다.** PR #8128의 `/run all` run [40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124)에서 두 진입점이 `[OK]`다. 같은 run에서 SQL, shell, medium이 모두 PASS다. 입력은 engine `e3589ae`, public TC `45e21ad`, private TC `479035a45`로 하나다.
- **TC를 쓰는 중 엔진 결함 두 개를 찾았다.** 둘 다 slave의 applylogdb에서 일어난다.
  - [CBRD-27800](http://jira.cubrid.org/browse/CBRD-27800): flush를 미루는 동안 record buffer를 재사용해, slave에 다른 행의 레코드를 OOS 값으로 저장한다.
  - [CBRD-27801](http://jira.cubrid.org/browse/CBRD-27801): 복합 기본 키 테이블에서 OOS 값이 있는 행을 UPDATE하면 applylogdb가 assertion으로 반복 종료한다.
- 활성 TC는 두 결함의 조건을 피한다. 각 결함을 재현하는 진입점은 `disabled/failing/`에 둔다.
- harness를 바꿔 HA 진입점 네 개가 모두 60초 안에 끝난다. 장애 전환 TC는 69초에서 51초가 되었다.

## 범위 결정

2026-10-28 사용자가 앞서 고르지 않은 두 항목, `async` 모드의 정상 복제와 대량·동시 쓰기의 queue alignment를 하기로 했다. 결함을 찾은 뒤에는 다음을 골랐다.

- TC: 결함을 피하는 활성 TC와 결함을 재현하는 비활성 TC로 나눈다. CI는 green을 유지한다.
- JIRA: 결함마다 버그 이슈를 쓴다. 이슈는 OOS TODO epic [CBRD-26978](http://jira.cubrid.org/browse/CBRD-26978)의 Sub-task로 만들고 CBRD-26659와 Relates로 연결했다.

## 입력 revision

| 항목 | 값 |
|---|---|
| Engine | `e3589ae42d42b04eb020e1ae43e165b01d31b12a` (PR #8128 head), `11.5.0.2793-e3589ae` optdebug |
| Test image | `cubridci/cubridci:test_rl8.10` `sha256:54e1835de00fa38c2539d268023ab1d34e653f0558f32f5f450e8b6b2721a15d` |
| CTP | `cubrid-testtools` develop `7dc9f4192bb96988d1bab78df3e45df88628b814` |
| Testcase | `cubrid-testcases-private-ex` `tc/pr-8128` `479035a45f06545db1974e1369e88000fb98a89a`, `cubrid-testcases` `tc/pr-8128` `45e21ad799d82ebadc04a93c7d2f69517d53bf39` |

## OOS 값이 slave에 도착하는 경로

OOS 값은 행보다 먼저 별도 복제 항목으로 slave에 도착한다. 짝이 하나라도 어긋나면 slave의 행은 다른 열이나 다른 행의 값을 가지거나, 반영되지 않는다. TC는 이 경로의 각 단계가 어긋날 수 있는 조건을 고른다.

| 단계 | 동작 | 근거 |
|---|---|---|
| master: 짝 맞추기 | OOS insert log record의 LSA를 transaction별 queue에 넣고, OOS 복제 항목마다 하나씩 꺼낸다. chunk chain은 `RVREPL_DUMMY_OOS_RECORD` 하나를 앞에 둔다 | `src/transaction/log_manager.c:2290`, `src/transaction/replication.c:476`, `src/storage/oos_file.cpp:2320` |
| master: 행 단위 초기화 | heap record 하나의 OOS 삽입을 시작할 때 queue를 비운다 | `src/storage/heap_oos.cpp:850` |
| master: 부분 rollback | savepoint와 문장 rollback은 그 뒤 LSA의 복제 항목을 보내지 않게 표시한다 | `replication.c:759` (`repl_log_abort_after_lsa`), `log_manager.c:4151` |
| master: FK action | 부모 키 UPDATE 중 자식 행을 고칠 때 queue를 통째로 바꿔 둔다 | `src/transaction/locator_sr.c:9064` |
| applylogdb | 항목마다 200개짜리 RECDES pool에서 버퍼를 받는다. 200개마다 flush하지만, 마지막 항목이 OOS 항목이면 행 항목이 올 때까지 미룬다. 자체 commit 때 flush한다 | `src/transaction/log_applier.c:85`, `:5656`, `:7699`, `:9336` |
| slave server | OOS 항목을 먼저 저장하고, 새 OID를 행의 stub에 속성 순서대로 써 넣는다 | `locator_sr.c:7256`, `:14425` (`locator_fixup_oos_oids_in_recdes`) |

## TC 내용과 판정 기준

`shell/_40_guava/oos_common/oos_ha_queue_case.sh`가 단계를 담고, 두 진입점은 `hp_sync_mode`만 정해 이 파일을 읽는다.

값 모델(`oos_common/oos_ha_values.sh`): 열 a, b, c, d의 크기 등급을 행의 모델 키로 정한다. 등급은 NULL, 120 B(inline), 5200 B와 9000 B(chunk 하나), 17000 B와 20000 B(chain)이다. 그래서 이웃한 행마다 OOS 값 수와 chain 수가 다르다. 값은 열 tag, 행 키, 다음 tag 순서라 다른 모든 값과 앞·가운데·끝이 다르다. 각 노드는 `count(*)`, 모델과 같은 행 수, `HAS_OOS` 행 수를 TC에 적은 기대값과 비교한다.

단계마다 applylogdb의 record buffer를 쓰는 항목(OOS 값 하나와 행 하나에 하나씩)을 200개 아래로 두고 barrier를 지난다. barrier가 보이면 applylogdb가 commit하면서 flush를 마친 것이다.

| 단계 | 동작 | 항목 수 | 노드별 검사 |
|---|---|---:|---|
| bulk.insert | INSERT ... SELECT 한 문장으로 40행 | 147 | 40행 모두 모델과 같음, `HAS_OOS` 40행 |
| bulk.change | 13행의 b를 새 값으로 UPDATE, 5행 DELETE | 51 | 바뀐 행과 남은 행 각각 |
| partial | 한 transaction에서 5행 insert, savepoint 뒤 5행 insert와 UPDATE, DELETE를 rollback, UPDATE 1건, 마지막 행이 기본 키와 겹치는 INSERT ... SELECT, 두 번째 unique index와 겹치는 INSERT, insert 1건 후 commit | 23 | 오류가 정확히 두 개(unique constraint), 남은 행과 바뀐 행, 사라진 행 0 |
| cascade | 부모 6행·자식 12행(OOS 값). 부모 3행의 기본 키와 OOS 값을 한 문장으로 UPDATE해 자식 FK가 `ON UPDATE SET NULL`로 바뀜. 부모 1행 DELETE로 자식 2행 `ON DELETE CASCADE` | 42, 21 | 부모와 자식의 값, 자식의 FK 값 |
| partition | 기본 키가 파티션 키인 range 파티션 12행. 4행 이동, 4행 이동과 새 OOS 값, 1행 OOS 값만 UPDATE | 44, 32 | 파티션별로 값 |
| concurrent | 세션 다섯 개가 동시에 8행씩 한 문장에 한 행으로 insert하고 2행을 UPDATE. 넷은 commit, 하나는 rollback | 149 | commit한 32행의 값, rollback한 세션의 행 0 |

## harness 변경

모든 HA 진입점이 쓰는 `oos_common/oos_ha_pair.sh`와 `oos_ha_checks.sh`를 다음과 같이 바꿨다.

| 변경 | 이유와 근거 |
|---|---|
| heartbeat 타이머 5개를 1000 ms로 줄임 | 기본값은 init 10 s, score와 failover 대기 3 s, process start 확인 3 s, changemode 5 s다(`src/connection/heartbeat.h`). 장애 전환이 7초에서 2–3초가 되었다 |
| `cubrid heartbeat start`를 background로 실행하고 `hp_join`으로 결과를 받음 | 이 utility는 copylogdb와 applylogdb를 띄운 뒤 10초를 기다리고 그 process가 살아 있는지만 본다(`HB_START_WAITING_TIME_IN_SECS`, `src/executables/util_service.c:3956`). 노드는 그 전에 HA mode에 이른다. 역할을 바꾸기 전에는 반드시 join한다 |
| setup이 두 노드의 `db_ha_apply_info` 행을 기다림 | 새 slave는 copylogdb가 처음 연결한 뒤 master가 기록한 것만 받는다. 그 시점이 applylogdb의 시작점이 되고, applylogdb는 시작하면서 그 행을 기록한다(`la_get_last_ha_applied_info`). standby mode는 그보다 먼저 보인다. 기다리지 않은 실행 두 번에서 setup 직후의 `create table`이 slave에 오지 않았다(slave applier 시작 LSA `175\|10232`가 그 commit보다 뒤였다) |
| barrier가 반영될 때까지 10초마다 update를 다시 함 | 처음에는 copylogdb가 따라잡는 중에 한 commit이 늦게 전달된다고 보고 넣었다. 실제 원인은 위 applylogdb 시작점이었고, 늦은 전달은 확인하지 않았다. 다시 하는 update는 결과를 바꾸지 않아 남겨 두었다 |
| `hp_sync_mode`, createdb 병렬 실행, barrier 제한 시간 인자 | async 진입점과 짧은 실패 판정을 위해 |

변경 뒤 로컬(CI 이미지, CTP)의 진입점 시간은 failover 51 s(이전 69 s), replication 27 s(이전 42 s), queue 33 s, async 24 s다. failover와 replication은 setup의 heartbeat start 결과를 검사 두 개로 추가해 각각 39개, 83개를 검사한다.

## 찾은 결함

### CBRD-27800: record buffer 재사용

- **결과**: slave가 나중 행의 heap record를 앞선 행의 OOS 값으로 저장한다. slave에서 그 행을 읽으면 `ER_HEAP_OOS_CORRUPTED_RECORD`(-1389)이고, slave server log에는 `OOS length mismatch: caller=<stub 길이> header=<heap record 길이>`(`oos_file.cpp:2778`)가 남는다.
- **원인**: RECDES pool은 200칸이고 차례로 재사용된다. `pending_oos_flush`가 200번째 항목에서 flush를 미루면, 그 뒤 항목이 같은 묶음에서 아직 flush하지 않은 항목의 버퍼를 받는다.
- **최소 재현**: 9000 B OOS 열 두 개인 행을 INSERT ... SELECT로 넣는다. 66행(버퍼 198개)은 정상이고, 67행이면 slave의 행 1을 읽을 수 없다(`caller=9008 header=52`).
- **근거**: 120행 모델(버퍼 440개)에서 slave의 행 1과 56이 깨진다. pool 모델로 계산하면 행 55와 110이 그 버퍼를 덮는다. 깨진 값의 길이는 heap record 크기를 따라 변한다(inline 값 +10 B면 196→204, varchar +10자면 208). `SHOW HEAP OOS`의 바이트 합 차이 13,824 B는 (5,208 − 196) + (9,008 − 196)과 같다. 행 하나와 `log_compress=no`는 결과를 바꾸지 않는다.
- **재현 진입점**: `disabled/failing/shell/_40_guava/cbrd_26659_ha_flush_boundary` (로컬 33 s, slave 행 1과 56 실패)

### CBRD-27801: 복합 기본 키 UPDATE

- **결과**: slave의 applylogdb가 `ws_add_to_repl_obj_list`의 `packed_pkey_value` assertion(`src/object/work_space.c:5379`, `la_apply_oos_insert_log`에서 호출)으로 종료한다. heartbeat가 약 3초마다 다시 띄우고, 같은 항목에서 다시 종료한다(30초에 37회에서 47회). slave는 standby로 남지만 그 뒤 아무것도 반영하지 않는다.
- **조건**: 행 하나, 9000 B OOS 값 하나로 확인했다.

| 실행 | 기본 키 | 행의 값 | UPDATE | slave |
|---|---|---|---|---|
| m1 | `(id, k)` | OOS | OOS 열 | assertion |
| m2 | `(id, k)` | OOS | `tag`만 | assertion |
| m3 | `id` | OOS | OOS 열 | 1초 안에 반영 |
| m5 | `(id, k)` | inline 10 B | `tag`만 | 1초 안에 반영 |

- async 모드에서도 같은 assertion이 났다. 처음 찾은 것은 파티션 키를 포함한 복합 기본 키의 파티션 테이블 UPDATE다.
- 이 assertion 직후 standby 서버가 멈춘 실행도 있었다. standby의 `heartbeat start` utility가 아직 10초를 기다리던 중이었기 때문이다. utility가 끝난 뒤에는 서버가 남았다.
- **재현 진입점**: `disabled/failing/shell/_40_guava/cbrd_26659_ha_composite_key` (로컬 42 s, 30초 barrier 실패)

## 실행 결과

모든 로컬 run은 `podman run --privileged`에서 `/entrypoint.sh test shell`, `TEST_SCENARIO=<case dir>`로 실행했다.

| Run | 입력 | 결과 | case 시간 |
|---|---|---|---:|
| q1 | 초안(bulk 120행) | NOK: slave의 행 읽기 -1389. CBRD-27800 발견 | 22 s |
| q2, as1 | 파티션 테이블의 기본 키 `(id, k)` | NOK: partition barrier. slave applylogdb assertion. CBRD-27801 발견 | 140 s, 138 s |
| q3, as2 | 파티션 키를 기본 키로 바꾼 TC | PASS 53/53 | 23 s, 28 s |
| f_queue, f_async | 커밋 `479035a45`와 같은 파일 | PASS 53/53 | 33 s, 24 s |
| f_failover, f_replication | 같은 커밋 | PASS 39/39, 83/83 | 51 s, 27 s |
| f_flush_boundary, f_composite_key | 같은 커밋의 비활성 진입점을 원래 위치로 복원 | 의도대로 NOK | 33 s, 42 s |

TC가 아닌 probe(`podman` 안의 harness 직접 실행)로 결함 조건을 좁혔다. 120행 재현 5회(p1–p5, 값 크기 변형 2회 포함), 단일 행(p6), 66행과 67행(s66, s67), 파티션 문장 단위(pp1, pp2), 복합 키 단일 행(m1–m5)이다.

## 실제 PR CI 실행

입력: PR #8128 head `e3589ae`, private `tc/pr-8128` `479035a45`, public `tc/pr-8128` `45e21ad`, CTP `7dc9f41`. 2026-10-28 06:21:39Z(UTC)에 `/run all`을 게시했다([comment](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6462236645)). 그때 PR #8128의 진행 중 run은 없었다. 진행 중이던 run 네 개는 다른 PR(#8308, #8213, #7799, #8268)의 것이었다.

| 대상 | 결과 |
|---|---|
| run [40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124) | success. job 72개 중 71개 success, 1개(nightly batch) skipped. head `e3589ae`의 `gha-ci` context 다섯 개가 모두 이 run을 가리킨다 |
| HA 진입점 | `cbrd_26659_ha_failover` shard 24(약 50 s), `cbrd_26659_ha_replication` shard 08(약 27 s), `cbrd_26659_ha_queue` shard 46(약 25 s), `cbrd_26659_ha_async` shard 01(약 27 s), 모두 `[OK]`. 시간은 앞 case가 끝난 시각부터 잰 값이다 |
| shell | 3,563건 중 3,533건 OK, 실패 0, skip 30. OOS shell 진입점 73개(이전 69개와 HA 4개)가 모두 OK |
| SQL | 17,653건 성공, 실패 0 |
| medium | 975건 실행, 실패 0 |
| provenance | private `479035a45` checkout 50회, public `45e21ad` checkout 11회 |

## 한계와 미실행

- 활성 TC는 두 결함의 조건을 피한다. 200개를 넘는 묶음과 OOS 값이 있는 복합 기본 키 테이블의 UPDATE는 결함이 고쳐질 때까지 비활성 진입점만 다룬다.
- release build는 실행하지 않았다. CBRD-27800은 async 모드와, applylogdb commit 간격 안에 작은 transaction이 쌓여 200개를 넘는 경우를 확인하지 않았다.
- 동시 세션 단계는 log record가 섞이는 것을 기대하지만, 실제로 섞였는지는 측정하지 않았다.
- 첫 단계 뒤의 chunk 수와 회수, 노드 장애 중의 대량 쓰기는 다루지 않는다.
- heartbeat 타이머는 기본값이 아니다. 두 노드는 같은 host의 namespace다.

## 다음 단계

1. CBRD-27800과 CBRD-27801을 ANALYSIS하고 고친 뒤, 비활성 진입점을 `disabled/README.md`의 절차대로 다시 켠다.
2. JIRA CBRD-26659 설명의 HA 범위와 최신 CI를 갱신한다.
