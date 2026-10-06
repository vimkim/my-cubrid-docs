https://jira.cubrid.org/browse/CBRD-27089

# PR #7927 — 목적지 heap을 정한 뒤 OOS 값을 기록하는 이유와 구현

설명 기준: [PR #7927](https://github.com/CUBRID/cubrid/pull/7927), source commit `9232f111a7e7b6c71dbfa451db2812ae14766041`, base branch `feature/oos-merge`.
이 문서는 해당 커밋의 구현을 설명한다. 설계 대안의 비교는 별도 성능 실험이나 새 구현에 대한 승인으로 해석하지 않는다.

## Purpose

### Problem and ownership

OOS (Out-of-row Overflow Storage)는 큰 컬럼 값을 heap record 밖의 전용 파일에 저장하는 방식이다. 값 하나는 하나 이상의 chunk record로 이루어진 OOS value chain에 저장하고, heap record에는 24바이트 OOS inline stub을 둔다.

| 정보 | 의미와 보관 위치 |
|---|---|
| head OOS OID | chain의 첫 chunk record를 특정하는 주소. volume·page·slot을 포함하며 stub에 저장한다. VPID만으로는 같은 페이지의 여러 chunk를 구분할 수 없다. |
| full length | 직렬화된 값 전체의 바이트 길이. chunk header를 제외하며 stub에 저장한다. |
| identity stamp | head chunk의 삽입 직전 page LSA에서 얻은 식별값. stub에는 packed 형식으로 저장한다. 이후의 현재 page LSA를 계속 따라 갱신하는 값이 아니다. |
| OOS VFID | OOS 파일 식별자. heap header가 보관한다. stub에 든 head OOS OID와 다른 정보다. |

heap마다 OOS 파일은 **최대 하나**이며 필요할 때 생성한다. 지켜야 할 조건은 **행을 저장한 heap의 OOS 파일에 그 행이 참조하는 chain도 속해야 한다**는 것이다. 모든 heap에 OOS 파일이 반드시 하나씩 존재해야 한다는 뜻은 아니다.

- **AS-IS:** 행의 저장 형식을 만드는 중에 root heap의 OOS 파일에 chain을 기록하고, 나중에 파티션을 골라 행만 child heap에 저장한다.
- **TO-BE:** 행의 값을 준비해 보관하고 목적지 heap을 정한 뒤, 그 heap의 OOS 파일에 chain을 기록하고 행의 stub을 완성한다.

SELECT는 stub의 head OOS OID로 chain을 직접 읽으므로 소유 관계가 틀려도 값이 맞을 수 있다. 반면 vacuum은 행이 있는 heap의 header에서 OOS VFID를 얻어 정리한다. child heap에 OOS 파일이 없으면 정리에 실패하고, 불변식 검사 계측이 있는 빌드에서는 서버가 중단된다. 계측이 없으면 chain을 정리하지 못해 공간이 누수된다. child heap에 다른 OOS 파일이 이미 있어도, 그 파일과 stub이 가리키는 chain의 소속이 다르므로 소유 불일치가 해결되지는 않는다.

여러 파티션이 OOS 파일 하나를 공유하는 설계도 이론적으로 가능하다. 다만 파티션별 chain 정리와 공유 파일의 수명을 새로 관리해야 한다. 마지막 파티션에서 파일을 삭제하는 것만으로는 먼저 삭제된 파티션의 chain을 제때 회수하지 못한다. 이 PR은 기존 heap별 소유 구조를 유지한다.

### Why the existing order became a problem

OOS가 없는 일반 서버 INSERT에서는 다음 순서로 처리할 수 있었다.

```text
컬럼별 DB_VALUE
  → 저장 형식의 바이트를 메모리 RECDES로 구성
  → RECDES에서 파티션 키를 읽어 목적지 결정
  → 목적지 heap에 행 저장
```

`DB_VALUE`는 타입과 값을 다루는 메모리 표현이고, `RECDES`는 행 바이트 버퍼와 길이 등을 가리키는 기술자다. `heap_attrinfo_transform_to_disk()`의 이름은 저장 형식으로 변환한다는 뜻이다. 그 이름 자체가 heap 페이지에 행을 삽입한다는 뜻은 아니다.

OOS가 도입된 변환 경로에는 `heap_attrinfo_insert_to_oos()`가 포함되었다. 그 결과 목적지가 정해지기 전에 실제 chain 기록이 발생했다. 이 PR이 바꾸는 핵심은 **컬럼 값을 준비하는 시점과 목적지에 chain을 기록하는 시점의 분리**다.

## Implementation

### Prepare, route, finalize, store

| 단계 | 담당 | 결과 |
|---|---|---|
| 생성 | `heap_prepared_row()` | `m_storage == nullptr`인 빈 객체 |
| 준비 | `prepare(thread, attr_info, old_recdes, copy_lobs)` | 컬럼 값을 한 번 직렬화해 소유하고, OOS 대상과 행 배치를 결정. 일반 값과 stub 자리를 갖춘 행 버퍼 구성. **새 OOS chain은 없음.** |
| 경로 선택 | locator와 partition adapter | 준비된 컬럼 값으로 기존 파티션 식을 평가하고 목적지 class/heap 결정 |
| 완성 | `finalize(thread, destination)` | 목적지의 OOS 파일에 chain을 기록하고 head OOS OID·길이·stamp로 stub 완성 |
| 저장 | locator와 기존 heap/index 처리 | 완성된 행을 저장하고 관련 변경 반영. 실패 시 호출자의 transaction/system operation으로 취소 |

`prepare()`는 파티션을 선택하지 않는다. `finalize()`도 heap record를 직접 삽입하거나 트랜잭션을 commit하지 않는다. `finalize()`의 반환값은 오류 코드이며, 행 버퍼는 별도 `record()`로 얻는다.

`prepare()`가 OOS chain을 만들지 않는다고 해서 모든 I/O나 부수 효과가 없다는 뜻은 아니다. 미설정 UPDATE 속성을 기존 행에서 읽거나, 기존 BLOB/CLOB 의미에 따라 외부 LOB를 복사할 수 있다. `copy_lobs` 인자는 그 동작을 제어한다.

이미 직렬화된 행은 `prepare_serialized()`로 받는다. 입력 바이트를 소유하도록 복사하거나, 기존 OOS 값을 속성별로 Resolve한 버퍼를 넘겨받는다. 필요한 schema 변환을 처리하되 SQL 식을 다시 평가하지 않는다. 모든 입력을 무조건 `DB_VALUE`로 풀었다가 재직렬화하는 경로는 아니다.

### What the object owns

공개 클래스는 `storage *m_storage`를 갖고, 내부 `storage`가 다음 다섯 항목을 관리한다.

| 필드 | 내용 |
|---|---|
| `columns` | 모든 컬럼의 직렬화된 바이트와 속성 ID, 배치 위치, fixed/variable 구분, NULL 여부, 해제 방식 |
| `plans` | 컬럼별 OOS 선택 여부, 길이, 삽입 결과를 받을 head OOS OID와 identity stamp |
| `requests` | 선택된 컬럼의 OOS 삽입 요청. `columns`의 바이트와 `plans`의 결과 필드를 참조 |
| `recdes` | 최종 heap record용 버퍼. 일반 컬럼은 복사되어 있고 OOS 컬럼은 stub 공간 확보 |
| `phase` | `building`, `prepared`, `consumed`, `completed` 상태 |

`columns`의 바이트를 해석하는 타입 정보는 `read_values()`에 전달된 attribute cache나 `read_value()`의 `OR_ATTRIBUTE`에서 얻는다. 준비 객체가 원래 `DB_VALUE`나 attribute cache 전체를 그대로 보관하는 것은 아니다.

예를 들어 `k`, `a`는 inline이고 `b`가 OOS 대상이면 `prepare()` 직후 구조는 다음과 같다.

```text
columns : [k의 바이트] [a의 바이트] [b의 전체 바이트]
plans   : [inline]     [inline]     [selected, 아직 head OOS OID 없음]
requests:                          [b 버퍼 → plans의 OID/stamp 출력 칸]
recdes  : [헤더·VOT | k | a | b의 stub 자리]
```

`requests`는 `b`를 다시 복사하지 않는다. 준비 단계에서 컬럼과 plan 저장소 크기를 확정하므로, 요청이 가리키는 주소를 유지한 채 `finalize()`에 넘긴다. 원래 입력 `DB_VALUE`가 정리되어도 준비 객체가 값을 소유한다. 일반 inline 컬럼은 `columns`와 `recdes` 양쪽에 바이트가 있으므로, 행 전체가 무복사라고 설명해서는 안 된다.

파티션 키 자체가 OOS 대상이어도 `read_values()`는 `columns`에서 값을 복원한다. 아직 head OOS OID가 없는 stub을 따라가려 하지 않는다. `record()`는 `prepared` 상태에서도 버퍼를 반환하므로 **포인터를 얻었다는 것만으로 일반적인 완성 행 소비자에게 넘겨도 된다는 뜻은 아니다.**

### State and rollback

```text
building → prepared → consumed → completed
                       └ 실패: consumed 유지, 같은 준비 데이터의 finalize 재시도 금지
```

`finalize()`는 `prepared` 상태만 허용하고, OOS 삽입을 시작하기 전에 `consumed`로 바꾼다. 첫 chain을 기록한 뒤 다음 삽입에서 실패해도 같은 준비 데이터로 재호출할 수 없게 한다. 동시 재진입만 막는 장치가 아니라 **한 번의 finalization 시도만 허용하는 상태 계약**이다.

`completed`는 요청된 OOS 삽입과 stub 완성이 성공했다는 뜻이다. heap 저장이나 commit의 성공을 뜻하지 않는다. 복사는 금지하고 이동을 허용하여, 소유권과 이 상태를 함께 옮긴다.

OOS 삽입 일부 또는 전부가 성공한 뒤 heap/index 처리에서 실패하면, **이미 기록된 chain까지 포함해 호출자의 롤백 범위에서 되돌려야 한다.** 준비 객체의 소멸자는 메모리만 해제한다. `consumed` 검사와 OOS publication 상태 초기화도 로그에 기록된 저장 변경의 롤백을 대신하지 않는다.

### Why prepare the whole row

버그 수정에 필수인 것은 목적지 선택 뒤 그 heap에 chain을 기록하는 순서다. 모든 컬럼의 바이트를 소유하는 클래스는 그 조건을 구현하기 위해 이 PR이 선택한 방법이다.

| 대안 | 필요한 연결과 수명 관리 |
|---|---|
| `DB_VALUE`를 유지하고 나중에 변환 | 최종 저장할 값과 같은 논리값으로 먼저 파티션을 평가하도록 연결하고, 입력과 참조 메모리의 수명을 보장해야 한다. 이미 직렬화된 입력도 처리해야 한다. |
| OOS 값만 소유하는 `oos_prepared_row` | 일반 행 버퍼/값과 OOS 준비 데이터를 함께 유지하고, 두 위치에서 컬럼을 읽는 공통 어댑터를 제공할 수 있다. 각 호출자에게 분기를 반복시킬 필요는 없다. |
| 현재 `heap_prepared_row` | 모든 컬럼의 바이트와 최종 행 버퍼를 같은 객체가 소유하며, 파티션·중복 키 평가가 같은 값 접근 인터페이스를 사용한다. |

`DB_VALUE`만으로 저장 크기를 구할 수 없어서 현재 설계가 필수인 것은 아니다. 기존 `heap_attrinfo_get_record_payload_size()`는 `pr_data_writeval_disk_size()`를 사용하고, `heap_attrinfo_determine_disk_layout()`이 OOS 대상을 고른다. `heap_attrinfo_insert_to_oos()`는 선택된 값을 직렬화하고 기록한다. 이 판단·기록을 함께 늦추는 대안도 성립할 수 있다.

기존 파티션 인터페이스가 `RECDES`를 받으면 서버에서 만든 행, client copy area, 재분배 중 읽은 행을 공통 경로로 다룰 수 있다. 다만 이미 최종 `DB_VALUE`가 있는 경로에서 직접 읽는 최적화도 가능하다. 기존 코드도 파티션 평가를 위해 행 전체를 복원하지 않고 필요한 속성을 지정해 읽는다. 이 문서는 두 설계의 속도 우열을 측정한 결과를 제시하지 않는다.

현재 클래스는 OOS 값만이 아니라 **heap에 저장할 행 전체**를 소유하며, OOS 대상이 없는 행도 처리한다. `heap_prepared_row`라는 이름은 그 책임에 맞는다. 이는 구현에 근거한 이름의 해석이며 작성자의 명명 의도를 별도로 증명하는 주장은 아니다.

이 PR에서는 비파티션 SQL INSERT·UPDATE도 준비 객체를 사용한다. 비파티션이면 이미 정해진 목적지로 `finalize()`한다. loader와 중복 키 탐색도 같은 준비/접근 계약을 사용한다. 파티션에서만 적용하는 좁은 수정도 가능하지만, 그 경우 다른 입력 경로와 준비 수명을 별도로 설계해야 한다.

이전 PR #7600의 two-pass 접근은 fully-inline probe로 파티션을 고른 뒤 다시 변환했다. 기존 분석에서는 반복 변환과 경로별 suppression, `STORAGE FORCE_OUTLINE`의 suppression 우회가 교체 이유였다. [PR #7600의 좁은 effective-key routing ADR](../docs/adr/0001-pr7600-effective-key-routing.md)은 그 PR 범위의 별도 설계 방향이며, 이 문서는 ADR을 변경하지 않고 PR #7927의 실제 구현을 설명한다.

### Call paths and source map

| 읽을 곳 | 확인할 계약 |
|---|---|
| [`heap_prepared_row.hpp`](https://github.com/CUBRID/cubrid/blob/9232f111a7e7b6c71dbfa451db2812ae14766041/src/storage/heap_prepared_row.hpp) | 소유 객체의 공개 인터페이스, 복사 금지와 이동 |
| [`heap_file.c`](https://github.com/CUBRID/cubrid/blob/9232f111a7e7b6c71dbfa451db2812ae14766041/src/storage/heap_file.c#L13911) | 내부 storage, `prepare_internal`, `read_values`, `read_value`, `finalize` |
| [`partition.c`](https://github.com/CUBRID/cubrid/blob/9232f111a7e7b6c71dbfa451db2812ae14766041/src/query/partition.c#L3472) | 준비 객체가 있으면 `read_values()`, 없으면 기존 `heap_attrinfo_read_dbvalues()` 사용 |
| [`locator_sr.c`](https://github.com/CUBRID/cubrid/blob/9232f111a7e7b6c71dbfa451db2812ae14766041/src/transaction/locator_sr.c#L4956) | INSERT의 pruning 뒤 finalize; UPDATE의 이동 여부 결정 뒤 해당 목적지에서 finalize |
| [`query_executor.c`](https://github.com/CUBRID/cubrid/blob/9232f111a7e7b6c71dbfa451db2812ae14766041/src/query/query_executor.c#L12046) | REPLACE/ON DUPLICATE KEY UPDATE의 probe는 준비된 key를 읽고 새 OOS chain을 기록하지 않음 |
| [`load_server_loader.cpp`](https://github.com/CUBRID/cubrid/blob/9232f111a7e7b6c71dbfa451db2812ae14766041/src/loaddb/load_server_loader.cpp#L732) | 입력값 정리 후에도 준비 객체를 큐에 보유; retained bytes로 flush 판단 |

client row는 `locator_prepare_client_row()` 어댑터를 거친다. 파티션 이동은 같은 준비 객체를 목적지 INSERT로 전달한다. 재분배는 기존 값을 읽어 목적지에서 새 chain을 만든다. replica apply는 이미 전달된 OOS item과 완료 행의 fixup 경로를 유지하면서 롤백 범위를 묶는다. 모든 경로가 무조건 `prepare()`를 호출한다고 일반화하지 않는다. 내부/catalog의 complete-record 경로와 bootstrap 예외도 남아 있다.

## Remarks

### Behavior and cost

현재 PR 본문에 명시된 동작 변경은 다음과 같다.

| 항목 | 변경 또는 제약 |
|---|---|
| server loaddb root 입력 | `%class <root>`의 행을 값에 맞는 파티션으로 배치 |
| server loaddb child 직접 입력 | `PRUNE_VERIFY`로 범위 검사. 잘못된 입력을 허용하던 `issue_21654_server_side_loaddb/partition_tbls`의 기대값 변경 필요 |
| loader lock/통계 | session이 모든 파티션의 BU lock을 먼저 획득하여 worker가 사용. 행이 없는 파티션도 load 동안 잠김. 파티션 행별 경로는 `SINGLE_ROW_INSERT`, 비파티션 HA/filtered-error 경로는 기존 `MULTI_ROW_INSERT` 유지 |
| loader 오류 | `on_failure()` 이후 중단 여부를 `m_session.is_failed()`로 판정. 지워진 error stack만 검사해 치명적 오류 뒤에도 계속 삽입하던 문제 수정 |
| replica apply | OOS item과 뒤따르는 heap row를 한 system operation으로 처리. 일반 row 실패는 해당 group을 롤백하고 다음 항목으로 진행하며, OOS item/fixup 실패나 미완성 group은 force area를 거절 |
| demotion 경계 | 실제 fixed 영역의 정렬 padding을 포함해 크기 계산. 경계 수 바이트 안의 행에서 OOS 선택이 달라질 수 있음 |
| MVCC 할당 재평가 | 호출자가 없는 경로가 목적지 결정 전 chain을 기록하지 못하도록 `assert_release`와 오류로 차단 |

저장/통신 형식과 기존 24바이트 stub 형식을 유지한다. 이 커밋의 record gate는 `DB_PAGESIZE/4`이며 기존 demotion 우선순위를 사용한다. OOS 규범의 four-record physical target과의 차이는 별도 구현 conformance 항목이다. 이 PR이 그 목표까지 도입했다고 설명하지 않는다.

모든 컬럼의 바이트를 소유하고 inline 값은 행 버퍼에도 복사하므로 추가 메모리 비용이 있다. OOS payload는 finalization용으로 다시 복사하지 않지만 목적지가 정해질 때까지 유지된다. 과거 `512b361a7`의 loader 측정에서는 server peak 증가가 약 7~8 MiB였다. 이는 해당 workload의 역사적 측정이며 현재 head의 측정값이 아니다. loader는 retained bytes와 큐 용량을 8 MiB flush 기준에 반영하며, 큰 단일 행은 따로 처리한다. 이 기준은 프로세스 RSS 상한이 아니다.

### Verification and evidence limits

이번 문서 작성에서는 `9232f111a7e7b6c71dbfa451db2812ae14766041`의 코드와 PR diff, 기존 설명/검증 자료를 대조했다. 엔진을 다시 빌드하거나 테스트를 실행하지 않았다.

| 증거 | 해석 범위 |
|---|---|
| `512b361a7`의 CTest 35/35, 실제 loader·복제·MVCC/복구·scoped Valgrind | [기존 해설과 실행 증거](CBRD-27089-deferred-write_bffe13b_claude.md)에 기록된 해당 커밋의 결과. 현재 head 전체 통과의 증거로 옮겨 쓰지 않음 |
| `e6ad82703`의 build와 OOS 테스트, `34a9072a1`의 configured CTest 35/35 | 문서 작성 당시 기존 PR 본문에 보고된 과거 커밋별 결과. 이번 작성에서 재실행하지 않음 |
| `34a9072a1`의 후속 원격 CI 수집 | [분석 보고서](ci_analysis_report_34a9072_codex.md)는 증거 검증의 한계로 회귀 원인 결론을 보류함. 과거 acceptance와 섞어 최신 CI 전체 성공으로 표현하지 않음 |
| 현재 source `9232f111a7e7b6c71dbfa451db2812ae14766041` | 구현 설명의 기준. 이 문서 자체가 현재 head의 새 실행 검증이나 merge 승인 근거는 아님 |

소스에 있는 관련 회귀 테스트는 다음과 같다. 테스트의 존재와 실제 실행 통과를 구분한다.

- `LoaderQueueRetainsClearedInputsAndRollsBackBulkFailure`: 입력 정리 후 값 수명과 bulk 실패 롤백.
- `MovedPreparationOutlivesAttributeCache`: 원래 attribute cache보다 오래 살아 있는 준비 객체.
- `AbandonedDuplicateCandidateDoesNotWriteOos`: 버려지는 중복 키 후보가 chain을 만들지 않는지 확인.
- `UpdateMovementAllocatesOnlyAtDestination`: 이동 목적지에서만 chain을 만드는지 확인.
- `UpdateIndexFailureRollsBackMovementAndNonmovement`: 인덱스 실패 시 이동/비이동 롤백.
- `ReplicaRowFailureRollsBackItsAppliedOosItem`: replica row 실패 시 앞서 적용한 OOS item도 롤백.

테스트 위치: [`test_oos_sql_show.cpp`](https://github.com/CUBRID/cubrid/blob/9232f111a7e7b6c71dbfa451db2812ae14766041/unit_tests/oos/sql/test_oos_sql_show.cpp), [`test_oos_server.cpp`](https://github.com/CUBRID/cubrid/blob/9232f111a7e7b6c71dbfa451db2812ae14766041/unit_tests/oos/test_oos_server.cpp).

### Oral explanation

“기존에는 행을 직렬화하면서 OOS 값도 기록했는데, 파티션은 그 뒤에 골랐습니다. 그래서 행과 OOS 값의 소유 heap이 달라질 수 있었습니다. SELECT는 OID로 직접 읽으므로 성공해도, heap별 OOS 파일을 사용하는 정리 경로에서는 문제가 됩니다.

이 PR은 먼저 행 전체의 바이트를 `heap_prepared_row`가 소유하게 합니다. `prepare()`는 OOS 대상을 고르고 stub 자리를 만들지만 새 chain은 만들지 않습니다. 준비된 값으로 목적지를 고른 뒤 `finalize()`가 그 heap의 OOS 파일에 값을 기록하고 stub을 채웁니다. 실제 heap 저장과 실패 시 롤백은 호출자의 책임입니다. 행 전체를 소유하는 것은 여러 입력 경로의 값 접근과 수명을 통일하기 위한 설계 선택입니다.”

### Questions and model answers

**질문: `prepare()` 성공 뒤 파티션 선택이 실패하면 새 OOS chain이 남는가?**

모범 답안: 아니다. 새 chain을 만드는 작업은 아직 실행하지 않았다. 준비 객체는 소유한 메모리를 해제한다. 이를 외부 LOB 처리까지 포함한 모든 부수 효과가 없다는 뜻으로 확대하지 않는다.

**질문: `finalize()` 성공은 행 저장 성공인가?**

모범 답안: 아니다. OOS 기록과 stub 완성의 성공이다. 뒤따르는 heap/index 처리에서 실패하면 OOS 변경도 호출자의 롤백 범위로 되돌려야 한다.

**질문: 왜 OOS 기록 전에 `consumed`로 바꾸는가?**

모범 답안: 일부 chain만 기록한 뒤 실패해도 같은 준비 데이터로 다시 삽입하지 못하게 하기 위해서다. 상태 검사는 재시도를 막고, 실제 기록의 취소는 트랜잭션 처리가 맡는다.

**질문: 왜 OOS 값만 담는 객체나 `DB_VALUE` 유지 방식을 쓰지 않았는가?**

모범 답안: 두 방식도 가능하다. 현재 구현은 모든 컬럼의 바이트, 값 읽기, 최종 행 버퍼의 수명을 한 객체에 모았다. 필수 조건은 목적지 확정 뒤 OOS 기록이며, 행 전체 소유는 그 조건을 여러 경로에서 구현하기 위한 선택이다. 메모리·복사 비용까지 없애는 설계는 아니다.
