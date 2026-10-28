# CBRD-27800과 CBRD-27801 OOS HA 문제 설명

작성: 2026-10-28 (Asia/Seoul).

**CBRD-27800은 slave에 잘못된 값이 저장되는 문제이고, CBRD-27801은 UPDATE 하나 때문에 slave의 복제가 멈추는 문제다.** OOS HA 테스트에서 발견한 두 문제의 처리 흐름과 확인된 범위를 이해하려는 개발자를 위한 설명이다. 27800의 버퍼 재사용 설명은 코드와 기존 재현 결과가 강하게 지지한다. 27801에서 PK 전달 조건이 깨지는 근본 원인은 아직 미확정이다.

기준 소스는 [CUBRID/cubrid PR #8128](https://github.com/CUBRID/cubrid/pull/8128)의 head인 `e3589ae42d42b04eb020e1ae43e165b01d31b12a`다. 당시 head branch는 `vimkim/cubrid:CBRD-26659-oos-testcases-handover`, base branch는 `feature/oos-merge`다. 아래 코드 링크는 이 커밋에 고정했다.

## OOS 값과 heap 행을 함께 보내는 이유

OOS 행을 복제할 때는 OOS 값 항목들이 먼저 오고, heap 행 항목이 뒤따른다. slave는 OOS 값을 저장해서 얻은 자기 OID를 heap 행의 stub에 넣어야 한다. master의 OOS OID를 slave에서 그대로 사용할 수 없기 때문이다.

그래서 OOS 값 항목들과 뒤따르는 heap 행을 같은 `xlocator_repl_force` 호출로 보내도록 구현돼 있다. 이 요구는 [locator_cl.c의 주석](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/locator_cl.c#L7065-L7071)에 명시돼 있다. slave 서버도 이 항목들을 하나의 atomic apply operation으로 처리한다. [locator_sr.c](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/locator_sr.c#L7230-L7256)

여기서 **flush는 applylogdb가 모아 둔 복제 항목을 slave 서버에 보내 반영하는 작업**이다. 이 설명에서 다루는 flush는 디스크의 `fsync`를 뜻하지 않는다. [la_flush_repl_items](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/log_applier.c#L5656-L5663)

## CBRD-27800 전송하기 전의 버퍼를 다시 사용한다

[CBRD-27800](https://jira.cubrid.org/browse/CBRD-27800)은 OOS 항목과 heap 행을 묶는 처리가 버퍼 수명과 충돌하는 문제다.

applylogdb는 레코드 버퍼 200개를 순환해서 사용한다. 끝까지 쓰면 첫 버퍼로 돌아간다. [200개 제한과 pool 초기화](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/log_applier.c#L9336), [버퍼 할당과 인덱스 순환](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/log_applier.c#L2431-L2454)

대기열에는 레코드를 복사하지 않고 **그 버퍼의 `RECDES` 포인터를 보관**한다. 따라서 전송하기 전까지는 같은 버퍼를 다시 쓰면 안 된다. [포인터를 보관하는 코드](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/object/work_space.c#L5409)

보통은 200개가 쌓이면 다음 버퍼를 사용하기 전에 flush한다. 그런데 마지막 항목이 OOS이면 heap 행까지 기다리려고 flush를 미룬다. `pending_oos_flush` 검사가 200개 제한 검사보다 먼저 실행되기 때문이다. [flush를 미루는 조건](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/log_applier.c#L5656-L5663)

단일 chunk OOS 값 두 개와 heap 행 하나를 가진 행들을 연속 처리하면 다음 경계에 도달한다.

| 처리한 내용 | 누적 버퍼 사용 |
| --- | --- |
| 66행 × OOS 두 개와 heap 행 하나 | 198개 |
| 67번째 행의 OOS 두 개 | 200개 |
| 67번째 행의 heap 행 | 201개 |

200번째가 OOS 항목이므로 flush를 미룬다. 그다음 201번째 항목이 첫 버퍼를 다시 쓴다. **첫 행의 OOS 항목이 여전히 가리키는 버퍼에, 67번째 행의 heap record가 들어가는 것이다.** `RECDES` 자체와 그 레코드 데이터가 재사용되므로, 앞선 항목도 바뀐 내용을 보게 된다.

나중에 flush하면 그 heap record를 OOS 값으로 저장하게 된다. 기존 최소 재현에서는 66행은 정상이고 67행부터 slave의 첫 행을 읽을 수 없다. 읽기는 `ER_HEAP_OOS_CORRUPTED_RECORD`로 실패한다. master의 행들은 정상이다. [CBRD-27800의 재현 SQL과 관찰 결과](https://jira.cubrid.org/browse/CBRD-27800)

이 산술과 포인터 공유는 소스에서 확인된다. 기존 경계 재현 결과도 같은 설명을 강하게 지지한다. **버퍼 덮어쓰기 자체를 디버거로 직접 관찰한 상태는 아니다.**

## CBRD-27801 복합 PK 행의 UPDATE에서 applylogdb가 종료한다

[CBRD-27801](https://jira.cubrid.org/browse/CBRD-27801)은 많은 행이 필요하지 않다. 다음 조건의 행 하나로 재현된다.

- 기본 키가 `(id, k)`처럼 두 컬럼이다.
- 행에 OOS로 저장된 값이 있다.
- 그 행을 UPDATE한다.

OOS 컬럼을 그대로 두고 `tag`만 바꿔도 발생한다. 현재 UPDATE 구현은 변경하지 않은 OOS 값도 새 chain으로 다시 쓰므로, 이 경우에도 OOS 복제 항목을 처리하게 된다. master의 UPDATE 경로는 heap 행 항목 앞에 OOS 복제 항목을 남기며, 이때 `new_key`를 전달한다. [locator_update_force의 OOS 복제 로그 생성](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/locator_sr.c#L9163-L9200), [CBRD-27801의 동작 설명](https://jira.cubrid.org/browse/CBRD-27801)

slave의 applylogdb는 그 OOS 항목을 대기열에 넣다가 다음 검사에서 종료한다.

```cpp
assert (packed_pkey_value != NULL && 0 < packed_pkey_value_length);
```

호출은 `la_apply_oos_insert_log`에서 `la_repl_add_object`를 거쳐 `ws_add_to_repl_obj_list`로 이어진다. 마지막 함수가 전달받은 packed PK를 검사한다. [OOS 항목 추가](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/log_applier.c#L6349), [PK 포인터와 길이 전달](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/log_applier.c#L5834-L5837), [실패하는 assertion](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/object/work_space.c#L5378-L5379)

이것은 **그 시점에 전달된 PK 포인터나 길이가 필요한 조건을 충족하지 못했다**는 뜻이다. heartbeat가 applylogdb를 다시 띄워도 같은 항목에서 종료하므로, 뒤의 transaction도 반영되지 않는다. 기존 관찰에서는 slave 서버가 `standby` 상태를 유지하면서 복제만 진행하지 못했다. [CBRD-27801의 관찰 결과](https://jira.cubrid.org/browse/CBRD-27801)

대조 실험은 실패 조건을 다음처럼 좁힌다.

| 기본 키와 행의 저장 상태 | 연산 | 기존 실행 결과 |
| --- | --- | --- |
| 복합 PK, OOS 값 있음 | OOS 컬럼 UPDATE | assertion으로 종료 |
| 복합 PK, OOS 값 있음 | `tag`만 UPDATE | assertion으로 종료 |
| 단일 PK, OOS 값 있음 | OOS 컬럼 UPDATE | 정상 반영 |
| 복합 PK, inline 값 | `tag`만 UPDATE | 정상 반영 |
| 복합 PK, OOS 값 있음 | INSERT | 정상 반영 |

**왜 PK 전달 조건이 깨지는지는 아직 미확정이다.** master가 로그에 기록할 때 문제인지, applylogdb가 읽거나 전달하는 과정의 문제인지 구분하지 못했다. assertion 위치만으로 어느 쪽이 원인이라고 결론 내릴 수 없다.

## 확인 범위

기존 재현은 `11.5.0.2793-e3589ae` optdebug build와 두 노드 HA 환경을 사용했다. 두 문제 모두 release build의 결과는 확인되지 않았다. 27800은 sync 모드에서 확인됐고 async 모드는 미확인이다. 27801은 sync 모드에서 위 대조 실험을 수행했으며, async 모드의 파티션 UPDATE에서도 같은 assertion을 한 번 관찰한 기록이 있다. 해당 장애가 남은 상태의 실제 failover 결과는 미확인이다.

이 설명은 기존 실행 결과와 기준 커밋의 코드를 정리한 것이다. 재현 SQL과 상세 실행 조건은 [CBRD-27800](https://jira.cubrid.org/browse/CBRD-27800)과 [CBRD-27801](https://jira.cubrid.org/browse/CBRD-27801)에 있다. 설명을 저장하면서 새로운 DB 실험이나 엔진 수정을 수행하지 않았다.

기존 정상 HA 테스트의 구성은 [두 노드 OOS HA 복제 기록](ci-replan/ha-replication.md), 정상 경로의 장애 전환 테스트는 [failover 기록](ci-replan/ha-failover.md)에서 확인할 수 있다. 그 테스트들의 성공은 여기서 다룬 버퍼 경계와 복합 PK UPDATE 조건의 정상 동작을 뜻하지 않는다.
