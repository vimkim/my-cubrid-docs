# Engine follow-up: CS client/trigger writes leave required OOS values inline

기준일: 2026-10-21, Asia/Seoul. 독자: 후속 엔진 수정을 맡을 개발자. 상태: 재현된 conformance FAIL, 수정 담당 미배정, 원인 attribution under triage. 관련 supplement는 [Work456/06 결과](ticket06-dml-triggers-transactions-20261021.md)다. 새 Work ID, JIRA 이슈 생성, 엔진 수정 또는 원격 게시는 하지 않았다.

CS 트리거를 통과한 실제 target/mirror의 전체 값은 정확하지만, accepted demotion gate를 넘는 값이 REC_HOME 상태에서 HAS_OOS clear로 남는다. 일반 DML의 동일 payload는 같은 설치에서 HAS_OOS set이다. 따라서 logical equality PASS와 저장 형식 FAIL을 분리해야 한다.

## 재현 기준과 증거

- 엔진: `d13aebf6428a68c2852d16df143d1da203d86dea`, Linux 16 KiB optdebug, CS. `1ef86a7` 위의 변경은 C++ 테스트 두 개이며 production 수정이 없다.
- Private TC 구현: `d997311c3` + cleanup `92f9811fd` + form controls `1f867526e`, `task/work456-06-private`, `shell/_40_guava/` 아래 세 case. 공통 코드 `oos_dml/dml_controller.sh`와 `dml_check.py`.
- Final native attempt: `/home/vimkim/temp/work456-implementation/ticket06/final-shell03/`. Exact expected/dispatched/finished 8개, 5 PASS / 3 FAIL / 0 SKIP. Runner exit는 0이며 native feedback/XML이 세 NOK를 판정한다.
- Raw result: `final-shell03/CTP/result/shell/current_runtime_logs/`. `test_local.log`의 `phase=… table=…`, 전체 equality, current slot/flags, error 배열과 owner state를 보존한다. `independent-artifact-audit.json`은 입력을 commit bytes와 대조하고 case/phase/cleanup을 검사한다.

| 실패 native case | 실제 S 의무와 관찰 |
| --- | --- |
| `cbrd_26659_dml_triggers_insert/cases/cbrd_26659_dml_triggers_insert.sh` | actual INSERT target, BEFORE INSERT mirror, AFTER INSERT mirror에서 large id2의 flags=1, HAS_OOS clear: 3개 |
| `cbrd_26659_dml_triggers_update/cases/cbrd_26659_dml_triggers_update.sh` | actual UPDATE target id1 flags=5, AFTER UPDATE mirror id1 flags=1, BEFORE UPDATE old mirror id2 flags=1: 3개 |
| `cbrd_26659_dml_triggers_delete/cases/cbrd_26659_dml_triggers_delete.sh` | BEFORE DELETE old mirror id2와 AFTER STATEMENT DELETE literal id9의 flags=1: 2개 |

총 8개 의무다. 모든 현재 slot은 `REC_HOME=2`; 현재 logical row와 full id/note/payload 모델에 연결했다. Trigger가 변경한 실제 row를 관찰했으며 companion table에서 추정하지 않았다. 세 실패 case의 모든 scheduled stage를 실행했다. DELETE 대상 행 부재에는 clear credit이 없다.

Payload는 5,107 byte의 `a1×1701 + b2×1703 + c3×1703`, 5,407 byte의 `d4×1801 + e5×1803 + f6×1803`이고 hex text를 BIT VARYING으로 cast한다. 각 table의 다른 속성은 int이며 eligible variable 속성은 payload 하나다. Accepted physical target 4,060 byte보다 충분히 크고, 전후 전체 equality도 검사한다. 기대값은 관찰된 clear 출력으로 바꾸지 않았다.

## 실행 방법

유지되는 `cubrid-testkit`의 native shell workflow를 사용한다. 일치하는 설치에서 `cub-workenv init --no-db`를 수행한 뒤, 설치·CTP·HOME·TMP·빈 registry를 attempt별로 복사한다. 위 세 full case paths를 expected list로 만들고 copied `shell_ci.conf`를 one slot, `scenario_disk=on`, exact `testcase_from_file`, retry/continuation/update off로 준비한다. 실행 명령은 다음과 같다.

```bash
TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c "$ATTEMPT/conf/shell.conf"
```

실행 status만 보지 말고 `testkit-focused.py verify --suite shell`에 expected list, run log, runner exit와 해당 copied CTP result root를 전달한다. Supplemental raw reproduction command는 `ticket06/run_attempt.py final-shell03 shell`에 위 세 basename을 전달하는 방식이다. 기존 attempt 이름은 보존하고 새 이름을 사용한다. 스크립트는 source/install mismatch를 우회하지 않는다.

## 조사 경로와 repair acceptance

정적 source 근거: `d13aebf`의 `src/query/execute_statement.c:9596–9650`은 UPDATE trigger에서 client path를 선택한다. `:12308`/`:12446–12460`은 matching INSERT trigger나 `do_Trigger_involved`이면 server INSERT를 허용하지 않는다. `src/object/transform_cl.c:781`의 `tf_mem_to_disk`는 관련 client serialization 경계다. **이 경로가 demotion을 누락한다는 설명은 현재 inference이며 완결된 root-cause 증명이 아니다.** 제품 실행은 위 저장 상태 불일치 자체를 확립한다.

[CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424)는 standalone loaddb/CSQL workspace 배경과 관련이 있다. 그 이슈의 scope를 CS trigger 수정으로 확장하거나 해당 수정이 이 FAIL을 해결한다고 주장하지 않는다.

후속 엔진 수정의 acceptance는 다음과 같다.

1. 위 세 실제 CS case의 8개 S 의무가 모두 올바른 current REC_HOME/HAS_OOS와 전체 값으로 PASS한다. 기존 C controls는 C를 유지한다.
2. BEFORE old/new와 AFTER new 모델, trigger rejection의 문장 원자성, mirror/log rollback, 현재 chain/file 보존을 유지한다.
3. General DML의 assigned/unassigned 전환과 immediate rollback/savepoint를 재검증한다. 전체 24-byte stub와 newest owner 계약은 CBRD-27230/티켓 15의 별도 reachable seam을 유지한다.
4. SA eager 계약을 CS MVCC로 대체하지 않는다. 현재 C++ assertion을 삭제하지 않는다. Correct expected set을 변경하거나 물리 검사만 제거해 통과시키지 않는다.
5. 실제 root cause와 변경 경계, matching install/source, native verdict/cleanup receipt를 후속 보고에 기록한다. 현재 supplement를 엔진 repair 작업으로 바꾸지 않는다.
