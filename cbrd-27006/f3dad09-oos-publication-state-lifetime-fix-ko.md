# [CBRD-27006] OOS insert publication state lifetime 수정 보고서

## Commit

| 구분 | 값 |
|---|---|
| CUBRID engine commit | `f3dad0946` (`f3dad09`) |
| Engine commit title | `[CBRD-27006] Fix OOS insert publication state lifetime` |
| Testcase commit | `1fdcaf935` |
| 기준 revision | `840e5e904` |
| 작업 branch | `CBRD-27006-oos-recdes-locality` |

이 문서는 `f3dad09` 커밋이 필요한 이유, 커밋이 강제하는 상태 수명과 소유권, 실제 HA 검증에서 추가로 발견한 첫 행 복제 오류의 원인, 그리고 검증 범위를 기록한다. 이 문서는 구현 및 검증 보고서이며 OOS 규격 자체를 대체하지 않는다.

## 요약

OOS-backed heap record 하나를 준비할 때 master 측에는 두 종류의 임시 상태가 생성된다.

| 상태 | 저장 위치 | 생산자 | 소비자 |
|---|---|---|---|
| OOS OID publication | `thread_p->oos_oids` | public OOS insert API | replication log 생성 및 heap-row fixup |
| OOS LSA publication | `tdes->oos_insert_lsa_queue` | OOS WAL append 처리 | `repl_log_insert()` |

Master-side replication tracking이 활성화된 경우 두 컨테이너는 한 logical OOS insert preparation에 속하는 순서가 보존된 쌍이다. 기존 구현은 이 상태를 class/OOS file lookup 뒤에서 초기화했다. 따라서 그보다 앞선 allocation, serialization, class lookup, OOS VFID lookup/create 실패는 이전 logical operation의 상태를 남길 수 있었다.

또한 slave apply 경로에서 같은 heap row에 속한 여러 `LC_FLUSH_INSERT_OOS` item은 slave-local head OOS OID를 누적해야 하지만, 내부 scalar helper가 item마다 누적 상태를 초기화했다. 결과적으로 뒤따르는 heap row가 여러 OOS inline stub을 올바른 slave-local OID로 치환할 수 없었다.

이 커밋은 단순히 기존 두 `clear()` 호출을 위로 이동한 변경이 아니다. 다음 소유권을 함께 확정한다.

1. logical heap boundary가 이전 operation의 publication state를 strict paired reset한다.
2. public scalar/batch OOS insert API가 현재 operation의 partial publication cleanup을 소유한다.
3. slave apply outer group이 replication-apply OID accumulation을 소유한다.
4. OOS file header WAL은 file metadata이며 logical OOS value publication이 아니다.
5. 뒤따르는 INSERT/UPDATE heap row는 누적 OID를 정확한 개수와 attribute 순서로 소비해야 한다.

## 용어와 상태 소유권

### OOS insert publication state

Master-side replication tracking이 활성화된 성공한 OOS insert 결과를 전달하기 위한 임시 상태다. `thread_p->oos_oids`의 OID entry와 `tdes->oos_insert_lsa_queue`의 WAL location entry가 논리 attribute 순서대로 대응해야 한다.

Replication tracking이 비활성화된 경우 public API가 OID를 남기더라도 LSA queue가 비어 있는 것은 정상이다. 이 상태를 완전한 OID/LSA publication pair라고 부르지 않는다.

### Replication-apply OID accumulation

Slave apply에서 연속된 `LC_FLUSH_INSERT_OOS` item이 생성한 slave-local head OOS OID의 순서 있는 목록이다. 다음 heap-row item의 master-side placeholder를 slave-local OID로 치환하기 위해 사용한다.

이 상태에는 LSA side가 없다. Slave는 받은 replication stream을 적용할 뿐 새 OOS replication stream을 만들지 않으므로, master-side strict paired reset을 OOS item마다 호출하면 안 된다.

## AS-IS 문제

### 1. Logical start reset이 너무 늦음

기존 흐름은 다음과 같았다.

```text
heap_attrinfo_insert_to_oos()
  ├─ vector reserve                         실패 가능
  ├─ OOS 대상 attribute serialization       실패 가능
  └─ heap_oos_insert_serialized_values()
       ├─ heap_get_class_info()             실패 가능
       ├─ heap_oos_find_vfid(create=true)   실패 가능
       ├─ LOG_TDES lookup
       ├─ oos_oids.clear()
       ├─ oos_insert_lsa_queue.clear()      reset이 너무 늦음
       └─ oos_insert_many()
```

따라서 late reset보다 먼저 반환하는 모든 실패 경로는 이전 logical operation의 publication state를 유지할 수 있었다. 새 operation이 아직 OOS value를 쓰지 않았다는 사실과, 이전 operation 상태가 계속 유효하다는 것은 별개다. 이 상태가 다음 replication consumer까지 도달하면 서로 다른 logical operation의 OID와 LSA를 같은 publication으로 오인할 수 있다.

### 2. 두 컨테이너를 절반만 초기화할 위험

OID list는 worker가 소유하고 LSA queue는 transaction descriptor가 소유한다. `LOG_TDES`를 확인하기 전에 worker-local OID list부터 지우면 descriptor lookup 실패 시 한쪽만 초기화된 상태가 된다.

Strict reset은 다음 순서를 지켜야 한다.

```text
resolve current tran_index
  -> resolve LOG_TDES
     -> success: clear OID list and LSA queue together
     -> failure: fatal ER_LOG_UNKNOWN_TRANINDEX, change neither side
```

### 3. Physical insert 이후 partial publication cleanup이 불완전함

OID publication과 LSA publication은 서로 다른 코드에서 생성된다. WAL append가 LSA를 queue에 추가한 뒤 OID vector append가 실패할 수도 있고, batch의 앞 request가 publication을 완료한 뒤 다음 request가 실패할 수도 있다.

특히 두 publication container는 `std::vector` 기반이므로 growth가 `std::bad_alloc`을 발생시킬 수 있다. Engine C error boundary 밖으로 C++ allocation exception이 탈출하면 안 되며, 이미 생성된 partial publication도 남겨서는 안 된다.

### 4. Slave OOS item마다 accumulator를 초기화함

한 heap row가 여러 OOS-backed attribute를 가지면 replication apply 입력은 개념적으로 다음 순서를 가진다.

```text
LC_FLUSH_INSERT_OOS(value A)
LC_FLUSH_INSERT_OOS(value B)
LC_FLUSH_INSERT_OOS(value C)
heap INSERT or UPDATE row(A-placeholder, B-placeholder, C-placeholder)
```

각 OOS item 적용이 만든 slave-local head OOS OID는 모두 유지되어야 한다. 그러나 `locator_oos_insert_force()`가 매 item마다 `thread_p->oos_oids`를 지워 마지막 OID만 남길 수 있었다. 이 reset은 master publication 개념을 slave apply accumulator에 잘못 적용한 것이었다.

### 5. Cardinality mismatch를 완전히 검증하지 않음

기존 `locator_fixup_oos_oids_in_recdes()`는 accumulator를 모두 소비한 시점에 attribute walk를 조기에 끝낼 수 있었다. 이 경우 뒤에 OOS placeholder가 더 있어도 부족한 OID를 발견하지 못한다. 반대로 heap row가 요구하는 수보다 accumulator OID가 많아도 남은 OID를 조용히 버릴 수 있었다.

두 경우 모두 heap inline stub에 master-side OID가 남거나, 다른 attribute/row의 OID가 재사용될 수 있으므로 group 전체를 실패시켜야 한다.

## HA 검증에서 발견한 추가 원인

### Lazy OOS file header LSA가 value publication queue에 들어감

Logical start reset을 class/OOS-file lookup보다 앞으로 이동한 뒤 첫 HA 실행에서 slave row가 `ER_HEAP_OOS_CORRUPTED_RECORD`로 읽히지 않았다. OID 순서 자체는 attribute 순서와 일치했지만 첫 row의 OID/LSA pairing이 한 칸 밀려 있었다.

첫 OOS-backed row는 class의 OOS file을 lazy create한다. `oos_create_file()`은 OOS file header record를 `RVOOS_INSERT`로 WAL에 기록한다. Log manager는 당시 모든 `RVOOS_INSERT` LSA를 자동으로 `tdes->oos_insert_lsa_queue`에 추가했다.

```text
실제 OID publication:
  [value_A_oid, value_B_oid, value_C_oid]

오염된 LSA queue:
  [file_header_lsa, value_A_lsa, value_B_lsa, value_C_lsa]

consumer pairing:
  value_A_oid <-> file_header_lsa   잘못된 쌍
  value_B_oid <-> value_A_lsa       한 칸 이동
```

이전 late reset은 lazy file creation 뒤에 실행되어 file-header LSA를 우연히 제거했다. 즉, 기존 위치는 논리적으로 틀렸지만 metadata queue pollution을 가리는 부수 효과가 있었다. Reset을 올바른 logical boundary로 이동하려면 file metadata와 logical value publication을 명시적으로 구분해야 했다.

최종 구현은 `oos_create_file()`의 header WAL append 동안 `oos_suppress_insert_lsa_queueing`을 제한적으로 활성화한다. 이미 suppression 상태라면 caller 상태를 보존하고, 이 함수가 직접 변경한 경우에만 `scope_exit`으로 원복한다. OOS file header WAL과 recovery 형식은 그대로 유지되며, publication queue 등록만 억제한다.

### UPDATE heap row도 OID fixup 대상임

HA INSERT를 통과시킨 뒤 mixed OOS UPDATE를 확인하면서 heap-record fixup 조건이 `LC_FLUSH_INSERT`만 처리하는 것도 확인했다. UPDATE replication 역시 새 slave-local OOS value를 먼저 적용하고 뒤따르는 heap row의 placeholder를 치환해야 한다.

최종 조건은 OOS payload item 자체인 `LC_FLUSH_INSERT_OOS`를 제외하고, OOS inline stub을 포함한 모든 INSERT/UPDATE variant에 exact-cardinality fixup을 적용한다.

## TO-BE 상태 수명

```text
heap_attrinfo_insert_to_oos()
  ├─ heap_oos_begin_insert_publication()
  │    ├─ resolve LOG_TDES first
  │    └─ clear OID list + LSA queue together
  ├─ vector reserve / serialization / lookup
  └─ oos_insert_many()
       ├─ validate all requests
       ├─ arm no-throw scope_exit cleanup
       ├─ physical insert + WAL/LSA + OID publication
       ├─ failure: clear current partial publication, return original error
       └─ success: release cleanup, hand publication to consumer
```

Slave apply 흐름은 별도 boundary를 가진다.

```text
xlocator_repl_force() group start
  ├─ clear slave apply accumulator once
  ├─ apply OOS item A -> append slave-local head OID A
  ├─ apply OOS item B -> append slave-local head OID B
  ├─ apply OOS item C -> append slave-local head OID C
  ├─ apply following INSERT/UPDATE heap row
  │    ├─ replace placeholders in attribute order
  │    └─ require consumed_count == accumulated_count exactly
  └─ clear after non-OOS row or any fatal group error
```

## 구현 내용

### `src/storage/heap_file.c`

- `heap_attrinfo_insert_to_oos()`의 첫 meaningful operation으로 strict start reset을 호출한다.
- vector reserve, serialization, class lookup, OOS VFID lookup보다 reset이 먼저 실행된다.
- logical-start 직후 deterministic failure를 발생시키는 unit-test-only one-shot hook을 추가했다.

### `src/storage/heap_oos.cpp` / `heap_oos.hpp`

- `heap_oos_begin_insert_publication()`을 production API로 추가했다.
- `LOG_TDES`를 먼저 resolve하고 성공한 경우에만 OID/LSA container를 함께 비운다.
- descriptor가 없으면 기존 fatal `ER_LOG_UNKNOWN_TRANINDEX` 모델을 유지하고 양쪽 seed를 보존한다.
- `heap_oos_insert_serialized_values()`의 중복 late reset과 descriptor lookup을 제거했다.
- 실제 class lookup 뒤, 실제 `heap_oos_find_vfid(..., true)` 직전의 one-shot failure seam을 추가했다.

### `src/storage/oos_file.cpp` / `oos_file.hpp`

- scalar `oos_insert()`와 batch `oos_insert_many()`가 입력 validation 뒤 동일한 partial-publication cleanup contract를 가진다.
- 성공 시 cleanup guard를 `release()`하여 consumer가 publication을 사용할 수 있게 한다.
- 실패 시 현재 worker의 OID list를 비우고, current `LOG_TDES`를 resolve할 수 있을 때만 해당 LSA queue를 비운다.
- cleanup은 no-throw best effort이며 기존 insertion error를 덮어쓰지 않는다.
- OID publication 중 `std::bad_alloc`을 `ER_OUT_OF_VIRTUAL_MEMORY`로 변환한다.
- lazy OOS file header WAL의 LSA를 logical value-publication queue에서 제외한다.
- partial batch failure와 publication allocation failure를 위한 unit-test-only one-shot hook을 추가했다.

### `src/transaction/locator_sr.c`

- `locator_oos_insert_force()`의 per-item OID/LSA reset을 제거했다.
- `xlocator_repl_force()`가 apply group 시작과 종료/실패 시점의 accumulator를 소유한다.
- OOS item 하나가 실패하면 pending OOS-plus-heap-row group 전체를 중단한다.
- INSERT 및 UPDATE heap row에 OOS placeholder fixup을 적용한다.
- insufficient/extra OID를 모두 `ER_HA_GENERIC_ERROR`로 거부한다.

### `unit_tests/oos/test_oos_server.cpp`

다음 failure 및 ownership boundary를 직접 검증한다.

| 항목 | 검증 내용 |
|---|---|
| strict reset success | seeded OID와 LSA가 함께 제거됨 |
| missing `LOG_TDES` | fatal failure, 양쪽 seed 유지 |
| preparation/class/VFID failure | 실패 전에 logical-start reset 완료 |
| partial batch failure | 앞 request publication까지 모두 cleanup |
| batch/scalar allocation failure | exception 미유출, OOM 변환, accumulator cleanup |
| tracked single/mixed batch | OID/LSA cardinality와 dummy/head 순서 유지 |
| replica accumulation | 여러 slave-local head OID를 attribute 순서로 소비 |
| insufficient/extra OID | malformed apply group 거부 |
| locality regression | 기존 single-page grouping 정책 유지 |

## 왜 `clear()` 위치 이동만으로 충분하지 않은가

| 단순 이동만 했을 때 남는 문제 | 이 커밋의 처리 |
|---|---|
| `LOG_TDES` 실패 시 half-reset 가능 | descriptor-first strict paired reset |
| physical insert 뒤 current partial state 잔존 | scalar/batch `scope_exit` cleanup |
| OID vector growth의 C++ exception 유출 | public API에서 OOM 변환 |
| scalar 성공마다 slave accumulator reset | outer apply group이 accumulator 소유 |
| 부족/초과 OID의 silent acceptance | exact cardinality 강제 |
| UPDATE placeholder 미치환 | INSERT/UPDATE variant 모두 fixup |
| lazy file header LSA가 첫 value와 pairing | metadata LSA queueing suppression |
| 성공 state가 함수 종료 시 제거될 위험 | success에서 guard `release()` |

따라서 핵심은 reset 위치가 아니라 각 상태의 logical lifetime과 producer/consumer 사이 ownership을 코드 경계로 표현하는 것이다.

## 검증 결과

### Debug build 및 CTest

개인 worktree 편의 명령으로 debug CMake/unit-test build를 수행했다.

```bash
direnv exec . just build
direnv exec . ctest --test-dir build_preset_debug_gcc \
  -R '^test_oos_server$' --output-on-failure
direnv exec . just build-test
```

결과:

- debug build 성공
- focused OOS fixture 3/3 성공
- `test_oos_server` 33/33 성공
- 전체 available OOS CTest 23/23 성공
- local SQL smoke 성공

### Ordinary SQL regression

```bash
CTP_SKIP_UPDATE=1 /home/vimkim/gh/ctp/run-sql/CTP/bin/ctp.sh \
  sql -c /tmp/cbrd_27006_sql.conf
```

- testcase 1/1 성공
- committed `.answer`와 일치
- result: `schedule_linux_sql_64bit_2018220920_11.5.0.2427-840e5e9`

### Real two-node HA replication

동일 debug build를 두 격리 node에 설치하고 CTP `ha_repl` runner로 ACTIVE/STANDBY topology를 구성했다.

```bash
CTP_SKIP_UPDATE=1 /home/vimkim/gh/ctp/run-sql/CTP/bin/ctp.sh \
  ha_repl -c /tmp/cbrd27006-ha/ha_repl.conf
```

결과:

- master ACTIVE, slave STANDBY 확인
- focused testcase 1/1 `[OK]`
- INSERT 첫 row: single/multi/single OOS value 일치
- INSERT 둘째 row: row group 사이 accumulator reset 확인
- UPDATE 첫 row: 변경된 세 OOS value 일치, 둘째 row 불변 확인
- master/slave dump 각각 2,264,029 bytes이며 byte-identical
- testcase diff allowance 없음
- core 0, fatal error 0

Version-controlled testcase:

- `sql/_36_guava/cbrd_27006/cases/cbrd_27006_oos_ha_repl.sql`
- `sql/_36_guava/cbrd_27006/answers/cbrd_27006_oos_ha_repl.answer`

CTP-generated `.test`, master/slave dump, result는 hand-maintained source로 commit하지 않고 local execution evidence로 보존했다.

## 변경하지 않은 계약

이 커밋은 다음을 변경하지 않는다.

- OOS on-disk format
- 16-byte OOS inline stub
- OOS value chain의 reverse chunk insertion 및 ownership
- OOS WAL/recovery record format
- OOS replication log format
- logical attribute/request order와 multi-chunk dummy/head pairing
- locality placement 및 single-page batch 정책
- transaction abort/WAL undo가 partial physical OOS record를 회수하는 계약
- OOS Resolve/Expand 동작
- PG-style four-record heap target 및 largest-first demotion 정책

Slave promotion/failover도 이 focused gate의 범위가 아니다. 이 커밋은 ACTIVE master에서 생성한 OOS replication record가 copylogdb/applylogdb를 거쳐 STANDBY slave의 local OOS value와 heap inline stub으로 정확히 연결되는지를 검증한다.

## Reviewer 확인 지점

1. `heap_oos_begin_insert_publication()`이 `LOG_TDES` 확인 전에 어느 container도 변경하지 않는지 확인한다.
2. `heap_attrinfo_insert_to_oos()`에서 reset보다 앞선 fallible preparation이 없는지 확인한다.
3. scalar/batch validation failure가 current publication 시작으로 잘못 분류되지 않는지 확인한다.
4. physical insert 이후 모든 error return에서 cleanup guard가 유지되는지 확인한다.
5. 성공 경로가 guard를 release하여 replication consumer까지 state를 보존하는지 확인한다.
6. OOS file header WAL suppression이 metadata record에만 제한되고 기존 caller suppression 상태를 보존하는지 확인한다.
7. slave apply가 `LC_FLUSH_INSERT_OOS` 사이에서 OID를 지우지 않고, 뒤따르는 INSERT/UPDATE row에서 정확한 수를 소비하는지 확인한다.
8. insufficient/extra OID 또는 OOS item failure가 pending group 전체를 중단하는지 확인한다.
9. multi-chunk dummy/head publication order와 replication format이 변하지 않았는지 확인한다.

## 결론

`f3dad09`는 OOS insert publication state를 우연한 container 내용이 아니라 명시적인 logical-operation 자원으로 다룬다. 이전 operation state의 폐기는 heap logical start가, current partial state의 폐기는 public OOS insert API가, slave-local OID 누적은 replication apply group이 각각 소유한다.

이 분리로 early preparation failure, partial publication, allocation failure, multi-OOS slave apply, 첫 lazy-created OOS file, 그리고 OOS UPDATE가 같은 lifetime 규칙 아래 동작한다. 실제 two-node HA에서 master/slave logical row와 전체 dump가 일치했으므로, 수정은 내부 queue 단위 테스트에 그치지 않고 copylogdb/applylogdb와 slave-local heap fixup까지 end-to-end로 검증되었다.
