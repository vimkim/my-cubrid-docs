# CBRD-26659: OOS HA 장애 전환, 재합류, failback TC

작성: 2026-10-28 (Asia/Seoul). Work540. 이 문서는 실행 증거와 남은 범위를 기록한다. 새 spec이나 승인된 테스트 행렬이 아니다. 두 노드 구성과 정상 복제 TC는 [두 노드 OOS HA 복제](ha-replication.md)에 있다.

## 결론

같은 두 노드 harness로 master 노드 장애 전환, 이전 master의 slave 재합류, 수동 failback을 shell case 하나(`cbrd_26659_ha_failover`)에서 검증한다. 역할이 바뀔 때마다 살아 있는 각 노드의 OOS 값, 크기, `HAS_OOS`가 TC에 적은 기대값과 같다.

- **실제 PR CI에서 통과했다.** PR #8128의 `/run shell` run [40594246823](https://github.com/CUBRID/cubrid/actions/runs/40594246823) shard 10에서 `[OK]`다. 정상 복제 TC도 같은 run의 shard 49에서 `[OK]`다. `test_shell` 전체는 3,561건 중 3,531건 OK, 실패 0, skip 30이다.
- CI와 같은 이미지·entrypoint·CTP로 로컬에서도 실행했다. 결과는 37 OK, 0 NOK다. A가 죽고 7초 뒤 B가 active가 되었다.
- 장애 직전 commit 앞에서 B의 applylogdb를 멈춘 변형은 의도대로 NOK다. B가 `to-be-active`에서 멈추고 TC가 120초 뒤 실패를 보고한다.
- 복제 모드는 `sync`만 실행했다. 노드 장애는 같은 kernel 위의 process 종료다. 범위 밖 항목은 [한계](#한계와-미실행)에 있다.

## 범위 결정

2026-10-28 사용자가 두 항목을 골랐다.

1. 장애 전환과 재합류: master 노드 장애, slave 승격, 승격 후 OOS 읽기·쓰기, 이전 master의 slave 재합류.
2. 수동 failback: 매뉴얼의 절차대로 원래 master를 다시 master로 되돌린다.

고르지 않은 항목은 `async` 모드의 정상 복제와 대량·동시 쓰기의 queue alignment다. 두 항목은 아직 정하지 않았다.

## 입력 revision

| 항목 | 값 |
|---|---|
| Engine | `e3589ae42d42b04eb020e1ae43e165b01d31b12a` (PR #8128 head), `11.5.0.2793-e3589ae` optdebug |
| Test image | `cubridci/cubridci:test_rl8.10` `sha256:54e1835de00fa38c2539d268023ab1d34e653f0558f32f5f450e8b6b2721a15d` |
| CTP | `cubrid-testtools` develop `7dc9f4192bb96988d1bab78df3e45df88628b814` |
| Workflow | `CUBRID/cubrid` develop `2d925cb8685600135eb1fb1781811f6b45fdecb0` `.github/workflows/gha-ci.yml` |
| Testcase | `cubrid-testcases-private-ex` `tc/pr-8128` `c0400c8f2222262dbeffca99b4ee66a7d2165444`. `task/oos-ha-failover`를 `3bba57e1f` 위에 fast-forward merge하고 2026-10-28에 push |

## TC 설계가 기대는 엔진 동작

| 동작 | 근거 | TC에서 쓰는 곳 |
|---|---|---|
| slave는 master의 heartbeat를 받지 못하면 `ha_failover_wait_time` 뒤 failover job을 실행한다 | `src/executables/master_heartbeat.c:986-996` (`hb_cluster_job_calc_score`) | A의 모든 process를 죽이면 B가 승격한다 |
| 승격하는 server는 모든 log applier가 끝난 뒤에만 active가 되고 update를 허용한다 | `src/connection/server_support.c:1702` (`css_check_ha_log_applier_done`) | barrier 없이 장애 직전에 commit한 변경도 B에 있어야 한다 |
| SYNC 모드의 commit은 slave가 log를 저장했다는 응답을 받은 뒤 끝난다. failover 뒤에도 복사된 log가 standby에 반영된다 | 매뉴얼 `ha.rst:242` | 위와 같다 |
| 자동 failback은 없다. 이전 master를 slave로 복구하고, 새 master를 멈춰 역할을 되돌린다 | 매뉴얼 `ha.rst:104`, `ha.rst:192` | failback 단계의 절차 |

## harness 변경

`oos_common/oos_ha_pair.sh`에 세 함수를 추가했다. 정상 복제 TC의 검사 함수는 `oos_common/oos_ha_checks.sh`로 옮겼다. 두 TC가 이 파일을 같이 쓴다. master와 slave는 역할 변수(`master`, `slave`)로 바꿨다.

| 함수 | 동작 | 이렇게 만든 이유 |
|---|---|---|
| `hp_crash` | node의 PID namespace 안에서 `kill -s KILL -- -1`을 실행한다. holder(PID 1)를 뺀 모든 process가 한꺼번에 죽는다. holder만 남을 때까지 최대 10초 확인한다 | holder를 죽이면 network namespace와 veth가 사라진다. 그러면 B도 자기 주소를 잃고 `Network is unreachable`이 된다(탐색 f1) |
| `hp_stop` | `cubrid heartbeat stop` | 매뉴얼의 failback 절차. cub_master는 남는다 |
| `hp_restart` | node 안에 cub_master가 없을 때만 `CUBRID_TMP`의 socket file을 지우고 `cubrid heartbeat start` | SIGKILL 뒤에는 오래된 socket이 남는다. 반대로 `heartbeat stop` 뒤 살아 있는 cub_master의 socket을 지우면 재시작이 `Address already in use`로 실패했다(탐색 f3) |

## TC 단계와 판정 기준

`shell/_40_guava/cbrd_26659_ha_failover/cases/cbrd_26659_ha_failover.sh`. 표 `oos_ha_fo(id int primary key, tag varchar(32), payload bit varying)`를 쓴다. 값은 5107 B(chunk 1개)와 36009 B(chunk chain)이고, 값마다 앞·가운데·끝 중 한 곳이 다르다.

```mermaid
flowchart LR
    P1["before: A master, B slave"] -->|"A의 모든 process SIGKILL"| P2["crash: B master"]
    P2 -->|"A heartbeat start"| P3["rejoin: B master, A slave"]
    P3 -->|"B heartbeat stop, start"| P4["failback: A master, B slave"]
```

검사 방식은 정상 복제 TC와 같다. 각 노드를 TC에 적은 기대값 식과 따로 비교하고, 두 노드를 서로 비교하지 않는다. OOS OID는 비교하지 않는다. 역할이 바뀌는 단계는 `cubrid changemode`가 기대 mode를 보고할 때까지 기다리고, 시간 안에 안 되면 case를 끝낸다.

| 단계 | 동작 | 노드별 검사 |
|---|---|---|
| before | A에서 id 1(5107 B), 2(36009 B), 3(5107 B) insert | 두 노드의 값 전체 equality, `octet_length`, `HAS_OOS`, `SHOW HEAP OOS` chunk 5개 |
| crash | (1) 열린 transaction: id 9 insert, id 3 update, id 2 delete 뒤 `sleep(600)`. `cubrid tranlist`로 DML이 끝나고 commit 전임을 확인 (2) barrier 없이 commit: id 5(36009 B) insert, id 1을 5108 B로 update (3) A의 모든 process SIGKILL | B가 120초 안에 active. B에 commit한 변경이 모두 있고, 열린 transaction의 변경은 없음 |
| B 쓰기 | id 4 insert, id 2를 36010 B로 update, id 3은 tag만 update, id 1 delete | rejoin 단계에서 두 노드 검사 |
| rejoin | A `heartbeat start`: recovery 뒤 slave로 합류 | A standby, B active, A의 쓰기 거부, barrier 뒤 두 노드 값과 `HAS_OOS` |
| failback | B `heartbeat stop` → A active. B `heartbeat start` → standby. A에서 id 4를 36009 B로 update, id 3 tag update, id 2 delete, id 6 insert | B standby, B의 쓰기 거부, 두 노드 값과 `HAS_OOS` |

설계상 주의할 점:

- **barrier 없는 commit**: commit 뒤 barrier로 B 적용을 기다리면, 장애 전환에서 commit을 잃어도 TC가 알아채지 못한다. 그래서 장애 직전 commit은 기다리지 않는다. SYNC 모드와 applier 완료 조건 때문에 B에 있어야 한다.
- **열린 transaction**: insert, OOS update, delete를 모두 끝낸 상태에서 죽인다. B에 그 변경이 없어야 하고, A는 재기동 recovery에서 그 변경을 undo한 뒤 B의 변경을 받아야 한다.
- **승격 후 쓰기**: B는 자기 applylogdb가 만든 chain 위에서 쓴다. failback 뒤 A는 B가 master로 쓴 chain(id 4)과 A의 applylogdb가 B의 update로 다시 만든 chain(id 2)을 고친다.
- **chunk 수는 before에서만 검사한다.** 첫 UPDATE 뒤에는 vacuum이 언제 도느냐에 따라 노드가 가진 이전 chain 수가 달라진다.

## 실행 결과

### 사전 탐색 (TC가 아님)

`failover_probe.sh`로 CI 이미지에서 같은 흐름을 네 번 실행했다. 결과는 TC 설계의 근거로만 쓴다.

| Run | 결과 |
|---|---|
| f1 | holder를 죽여서 B가 주소를 잃음. `hp_crash`를 PID namespace 안의 SIGKILL로 바꿈. B 승격 8초, A 재합류 12초 |
| f2 | `SELECT_RECORD_INFO`가 삭제 대기 version도 보여줌. `HAS_OOS` 검사에서 `t_delid`로 제외하도록 바꿈. B 승격 6초 |
| f3 | 재합류 뒤 두 노드의 `SHOW HEAP OOS`가 같음(13 recs, 128,808 B). failback에서 살아 있는 cub_master의 socket을 지워 B 재시작 실패 |
| f4 | socket을 cub_master가 없을 때만 지움. 승격 7초, 재합류 12초, failback 성공. failback 뒤 두 노드 `SHOW HEAP OOS`가 같음(15 recs, 139,080 B) |

### TC 실행

모든 run은 `podman run --privileged`(rootless podman)에서 `/entrypoint.sh test shell`, `TEST_SCENARIO=<case dir>`로 실행했다.

| Run | 입력 | 결과 | 시간 |
|---|---|---|---|
| fo1 | 커밋 `c0400c8f2`와 같은 파일(sha256 일치) | PASS, `[OK]`, 37 OK, 0 NOK. B 승격 7초 | case 69 s, container 78 s |
| rep1 | helper 이동 후의 정상 복제 TC | PASS, `[OK]`, 81 OK, 0 NOK. 검사 label이 이동 전 run r6과 같음 | case 42 s |
| sabfo1 | barrier 없는 commit 직전에 B의 applylogdb를 `SIGSTOP`하는 사본 | 의도대로 NOK: `crash.failover: oos-ha-node-b not active within 120s, it reports 'to-be-active'`. cleanup OK | case 151 s |

fo1 단계별 시간(harness trace): setup 26 s, before와 열린 transaction 3 s, 승격 7 s, A 재합류 12 s, B `heartbeat stop` 2 s 뒤 A active, B 재합류 11 s, 정리 5 s.

## 실제 PR CI 실행

입력: PR #8128 head `e3589ae`, `tc/pr-8128` `c0400c8f2`, CTP `7dc9f41`. 2026-10-27 22:21:53Z(UTC)에 `/run shell`을 게시했다([comment](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6455055694)). 그때 PR에 진행 중인 run은 없었다.

| 대상 | 결과 |
|---|---|
| shard 10 (job 122506695132) | `cbrd_26659_ha_failover` `[OK]`, case 약 71 s. provenance: engine `11.5.0.2793-e3589ae` optdebug, private-ex `c0400c8f2`, CTP `7dc9f41`. shard: assigned 70 / run 70 / failed 0 / skipped 0 |
| shard 49 (job 122506695321) | `cbrd_26659_ha_replication` `[OK]`. shard: assigned 72 / run 71 / failed 0 / skipped 1 |
| shell 전체 | `test_shell` success. 3,561건 중 3,531건 OK, 실패 0, skip 30. 이전 `/run all` run 40557885817은 OK 3,530건이었다. 늘어난 1건이 이 TC다 |

이 run 뒤 head `e3589ae`의 build 두 개와 `test_shell` context는 run 40594246823을, `test_sql`과 `test_medium`은 run 40557885817을 가리킨다. 두 run의 private testcase 입력이 다르다(`c0400c8f2`, `3bba57e1f`). 바뀐 파일은 shell의 HA case와 `oos_common`뿐이다.

## 한계와 미실행

- 노드 장애는 같은 kernel 위에서 node의 process를 모두 죽이는 방식이다. OS page cache는 남는다. OS crash, 전원 장애, 디스크 유실은 재현하지 않는다.
- server process만 죽는 장애는 다루지 않는다. 이 경우 cub_master가 server를 다시 띄우거나, 시작 직후의 반복 장애이면 master를 내린다(`ha_unacceptable_proc_restart_timediff`).
- 네트워크 단절, split brain, `ha_ping_hosts` 판정은 다루지 않는다.
- 복제 모드는 `sync:sync`만 실행했다. `async`는 실행하지 않았다. 매뉴얼은 `SEMISYNC`가 deprecated이고 SYNC와 같다고 쓴다(`ha.rst:252`).
- 열린 transaction은 하나다. 동시 쓰기 중 장애 전환과 queue alignment는 검증하지 않았다.
- 첫 UPDATE 뒤의 chunk 수는 검사하지 않는다. 장애 전환 뒤 새 master에서 이전 chain이 회수되는지는 확인하지 않았다.
- 실제 CI에서 통과한 것은 한 번이다. 로컬도 PASS run은 한 번이다. 반복 실행 안정성은 측정하지 않았다.

## 다음 단계

1. JIRA CBRD-26659의 HA 범위와 Remaining Work에 이 결과를 반영한다.
2. 고르지 않은 범위(`async` 정상 복제, 대량·동시 쓰기의 queue alignment)를 할지 정한다.
