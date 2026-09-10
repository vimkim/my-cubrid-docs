# PR #7600 — 레코드를 보낼 곳을 먼저 결정한다

## 읽는 순서와 근거

이 문서는 `feat/oos` 의 `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` 를 base와 merge-base로 하여, HEAD `479cd960ec04196c92bf9789b1fc340af9046c2c` 의 변경을 설명한다. 변경은 10개 파일, 추가 2,003줄, 삭제 101줄, 63개 diff hunk다. 작업 디렉터리의 기존 CCI 차이와 학습 자료는 이 committed diff에 포함하지 않는다.

먼저 작은 INSERT로 소유권 문제를 이해하고, effective key → partition 선택 → OOS 기록 → 최종 검증 순서로 읽는다. 발표할 때는 네 가지 관점의 interactive walkthrough를 사용하고, 구체적인 줄에 대한 질문은 이 문서의 전체 diff 부록에서 확인한다. 영문 Markdown이 설명의 원본이며 이 페이지는 한국어 독자용으로 구성했다.

**소스 근거**는 고정한 revision의 실행 코드, **과거 실행 근거**는 별도 revision과 환경에서 보관된 실행 결과를 뜻한다. **설계 이유**는 기록된 결정 또는 명시한 추론이다. **미검증**은 근거가 부족한 상태다. 이번 문서 작성에서는 엔진 테스트를 실행하지 않았다. 브라우저 검증은 문서와 상호작용이 동작하는지 확인하는 것이며 DBMS의 정확성을 증명하지 않는다.

## 작은 INSERT에서 시작하는 소유권 문제

OOS-backed attribute는 heap record에 작은 inline stub을 남기고, 직렬화한 실제 값을 별도의 OOS value chain에 저장한다. Heap 하나에는 OOS file이 최대 하나 연결되며, heap header가 그 VFID를 보관한다. Partition root와 child의 heap은 서로 다른 소유자다. 따라서 chain을 기록할 때 선택한 OOS file과 최종 heap record의 저장 위치가 같은 heap 단위로 일치해야 한다.

이전 locator의 순서는 **레코드 변환 → partition 결정 → child에 삽입**이었다. 변환 중 `heap_attrinfo_insert_to_oos` 는 `attr_info->class_oid` 를 사용했다. Root를 대상으로 INSERT하면 이 시점의 class는 root다. 이후 pruning이 `p0` 를 고르면 stub이 들어 있는 record는 child로 가지만, chain은 root OOS file에 남는다. [이전 locator 소스](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7695).

```sql
CREATE TABLE t_oos_show_part (
  id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE
) PARTITION BY RANGE (id) (
  PARTITION p0 VALUES LESS THAN (10),
  PARTITION p1 VALUES LESS THAN MAXVALUE
);
INSERT INTO t_oos_show_part VALUES (1, REPEAT(X'EE', 64));
COMMIT;
SELECT data_col = CAST(REPEAT(X'EE', 64) AS BIT VARYING)
  FROM t_oos_show_part WHERE id = 1;
SHOW ALL HEAP OOS OF t_oos_show_part;
```

SELECT가 1을 반환하는 것만으로는 충분하지 않다. 읽기는 stub의 head OOS OID를 따라갈 수 있기 때문이다. 이 테스트의 물리적 oracle은 **root: file 없음·chunk 0, p0: file 있음·chunk 1, p1: file 없음·chunk 0**이다. 64바이트 FORCE_OUTLINE 값은 일반 크기 gate 아래에서도 문제를 드러낸다. 이는 테스트 코드에 정의된 기대값이며 이번에 새로 실행한 결과가 아니다. [회귀 테스트](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L437).

Vacuum은 정리 중인 heap의 header에서 OOS VFID를 찾는다. 현재 `vacuum_oos_find_vfid_for_heap_record` 는 HAS_OOS record의 heap에 OOS file이 없으면 명시적인 `abort()` 를 실행한다. 주변 주석에는 오류를 지우고 건너뛴다는 설명도 있지만, 실행 코드는 그 전에 종료한다. 진단 코드를 없애도 소유권 오류 자체는 고쳐지지 않는다. [Vacuum 소스](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/vacuum_oos.cpp#L401).

## 용어와 revision 경계

| 용어 | 여기서 뜻하는 것 |
|---|---|
| Source class | Assignment와 old representation을 읽고 기존 LOB 준비를 수행하는 기준. Moving UPDATE가 끝나기 전에 잃으면 안 된다. |
| Destination class | 새 record가 들어갈 partition. OOS file을 선택하는 데 사용한다. |
| HFID / VFID / OID | Heap 식별자 / 논리적 file 식별자 / object 주소. 소유권과 물리적 주소를 혼동하지 않는다. |
| Effective key | 정상 직렬화 뒤 저장될 partition key와 동등한 값. Default, 이전 값, pending increment, scalar codec 효과를 반영한 독립 소유 복사본이다. |
| Resolve | OOS-backed attribute의 논리값 읽기. I/O가 일어날 수 있으므로 early routing을 I/O 없는 작업이라고 설명하면 안 된다. |
| Probe image | Key 추출용 fully-inline 임시 record. OOS 쓰기는 억제하지만 모든 DB_VALUE·LOB 부수 효과를 금지하지는 않는다. |
| HAS_OOS | Record에 OOS inline stub이 있음을 나타내는 metadata. 올바른 file 소유권까지 증명하지 않는다. |

현재 소스의 `OR_OOS_INLINE_SIZE` 는 `OR_OID_SIZE + OR_BIGINT_SIZE`, 즉 **16바이트**다. 최신 OOS normative context의 24바이트 identity-stamp 설계는 별도 변경이다. 이 PR은 그 layout을 도입하지 않는다. 명세의 최신 설계와 여기서 설명하는 구현 revision을 구분해야 한다. [현재 상수](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/base/object_representation.h#L466).

## 현재 경로를 끝까지 따라가기

`locator_attribute_info_force` 는 UPDATE라면 먼저 전달받거나 잠금으로 확보한 old record를 준비한다. Partitioned INSERT/UPDATE는 `partition_prune_insert_by_attrinfo` 또는 `partition_prune_update_by_attrinfo` 로 목적지를 구한다. 성공한 뒤에만 `write_destination` 을 OOS owner로 넘겨 정상 first-pass 전체 record 변환을 수행한다. 마지막 force 단계에서 직렬화된 record를 다시 pruning하고 목적지를 검증한 다음 heap/index 작업을 진행한다. Nonpartitioned 호출은 기존 변환 경로를 사용한다. [오케스트레이션 소스](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7655).

핵심은 **routing 두 번, 전체 record 변환 한 번**이다. 변환 내부의 기존 buffer-growth retry는 별개다. PR body와 JIRA에 남아 있는 fully-inline probe + 전체 rebuild 방식은 이전 구현 설명이다. Accepted ADR은 전체 row 준비를 분해하여 LOB lifecycle까지 재설계하는 대신, key만 먼저 준비하여 중복 전체-row 작업을 줄이도록 결정했다. 특정 타입만 조용히 옛 방식으로 돌아가는 fallback도 채택하지 않았다. [설계 결정](https://github.com/vimkim/my-cubrid-docs/blob/08870b103aea34148f08bb9e5d9d9c496d4a4e11/docs/adr/0001-pr7600-effective-key-routing.md).

## Effective key를 만드는 줄들의 의미

`heap_attrinfo_get_effective_key` 는 caller가 소유할 NULL output에서 시작한다. 전체 row를 준비하지 않고 partition key만 만든다. [함수 소스](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12115).

| 코드 블록 | 왜 필요한가 |
|---|---|
| NULL output, source slot 조회, aligned scratch | 소유권을 명확히 한다. 64바이트 scratch는 작은 key의 allocation을 줄이는 장치이며 row 크기 제한이 아니다. |
| Uninitialized + old record | 별도의 one-key reader로 전달된 old representation을 읽고 clone한 뒤 reader를 종료한다. 변경하지 않은 UPDATE key는 현재 default가 아니라 이전 row의 값이어야 한다. |
| Uninitialized + INSERT | Attribute metadata를 복사하되 DB_VALUE는 별도로 NULL 초기화한다. 기존 default reader를 재사용하고 clone한다. 원본 assignment는 실제 변환까지 uninitialized 상태로 남긴다. |
| 이미 주어진 값 | `pr_clone_value` 로 복사한다. 최종 key가 원본 memory를 빌려 쓰지 않게 한다. |
| `do_increment` | Pending INCR/DECR를 복사본에만 적용한다. 같은 row를 두 번 routing해도 원본 pending 연산을 소비하지 않는다. |
| NULL 분기 | NULL을 보존해 기존 pruning의 NULL 처리로 보낸다. 불필요한 codec 왕복은 하지 않는다. |
| Domain codec 크기 계산과 할당 | 현재 attribute domain의 scalar codec을 사용한다. 잘못된 크기와 할당 실패를 전파한다. |
| `data_writeval` → `data_readval` | CHAR padding 등 저장 형식의 효과를 독립 복사본에 반영한다. Assignment를 그대로 비교하면 저장 후 routing과 달라질 수 있다. Read는 copy semantics를 사용한다. |
| `cleanup` | Prepared value와 임시 buffer를 정리한다. 부분 decode 뒤 실패한 output도 clear하여 caller가 불완전한 key를 받지 않게 한다. |

Direct routing 테스트의 reference는 별도의 attrinfo를 사용해 inline probe를 수행한다. Reference 변환은 자신의 assignment를 초기화하거나 바꿀 수 있으므로 candidate와 같은 값을 공유하면 원본 보존을 검증할 수 없다. 정확한 old/new line 번호는 아래 diff 부록에서 바로 확인할 수 있다.

## Partition expression을 어디에 묶는가

`partition_start_key_attrinfo` 는 pruning context가 소유한 한 개 key slot을 만들고 expression cache를 그 주소에 바인딩한다. Stack의 임시 DB_VALUE에 묶으면 context 재사용 시 lifetime 문제가 생긴다. `partition_find_partition_for_attrinfo` 는 이전 duplicate probe가 남긴 값을 먼저 clear하고, slot을 readable로 표시한 뒤 effective key와 expression 결과를 구한다. 성공한 경우에만 destination OID/HFID를 복사하고, 끝에서 값은 clear한다. Slot과 binding은 성공한 context 재사용을 위해 유지된다. [바인딩 소스](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3548).

`partition_find_partition_for_expr` 는 이전 record router에서 공통 evaluator를 추출한 것이다. 두 경로가 같은 expression 평가, NULL 분기, partition matching을 사용하며 결과가 정확히 하나여야 한다. 반환하는 `OR_PARTITION` 은 context 소유 객체를 빌린 pointer다. Record decode와 representation ID 변경은 `partition_find_partition_for_record` 에 남는다. Diff에서 삭제된 decode 코드는 final routing에서 사라진 것이 아니라 adapter로 옮겨졌다. [공통 evaluator](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3479).

INSERT/UPDATE 공통 internal 함수는 기존 context lifetime과 명시적 child 검증을 보존한다. Root 대상 UPDATE는 child 간 이동이 가능하지만 child를 명시한 문장은 그 child 밖의 key를 거절해야 한다. Context 없는 UPDATE는 source child에서 root를 찾고, 전달받은 UPDATE context는 이미 로드되어 있어야 한다. [공통 wrapper](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3698).

## Source identity를 유지하며 OOS owner만 바꾼다

`heap_attrinfo_transform_to_disk_with_oos_owner` 는 destination OID와 `increments_already_applied=false` 를 common transformer에 넘긴다. Suppression output은 NULL이다. Transformer는 기존대로 source row를 준비하고 demotion을 계획한다. OOS와 bigone의 지원하지 않는 조합은 OOS 쓰기 전에 거절한다. 이후 payload를 직렬화하고 최종 record를 만든다. [Owner wrapper](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12927).

Destination을 실제로 사용하는 경계는 `heap_oos_insert_serialized_values` 호출이다. 이 기존 함수가 class → HFID → OOS VFID를 찾고 `oos_insert_many` 를 호출한다. Payload 직렬화와 LOB locator 준비는 source attrinfo를 계속 사용한다. 따라서 `attr_info->class_oid` 자체를 destination으로 덮어쓰는 것은 이 PR보다 훨씬 넓은 의미 변경이다. [Owner 전달](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12885), [기존 storage 경계](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_oos.cpp#L631).

Moving UPDATE의 final record routing은 destination representation ID를 반영한다. `locator_update_force` 는 실제 source identity를 유지하거나 다시 확인하고, source와 destination이 다를 때 `locator_move_record` 를 호출한다. 기존 move helper의 실행 순서는 **destination에 insert한 뒤 source를 delete**하는 것이다. 중간 실패는 transaction error handling이 처리해야 한다. [Move 소스](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5402).

## 최종 routing을 남기는 이유

Early routing은 OOS를 어느 heap에 쓸지 정한다. Final routing은 직렬화된 record의 검증, representation patching, 기존 force 동작과의 결합을 계속 담당한다. INSERT/UPDATE에 추가된 optional `expected_class_oid` 는 두 판단을 연결한다. 최종 pruning 결과가 다르면 이후 destination heap/index 변경 전에 `ER_GENERIC_ERROR` 로 실패한다. 이미 기록한 chain을 그대로 둔 채 record만 다른 heap으로 보내면 처음의 소유권 오류를 다시 만들기 때문이다. [INSERT 검사](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L4996), [UPDATE 검사](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6021).

이 검사는 error를 반환하는 경계이며 그 자리에서 모든 chain을 rollback하는 함수가 아니다. OOS 쓰기가 이미 발생했을 수 있고, 기존 statement/transaction rollback에 의존한다. SQL failure 테스트는 명시적 abort 뒤 물리적 count를 검사한다. 그 abort 경로의 증거를 모든 caller의 자동 statement rollback 보장으로 확대하면 안 된다. Early destination이 없는 기존 caller는 NULL을 넘긴다.

## Probe·FORCE_OUTLINE·INCR·LOB

REPLACE와 ON DUPLICATE KEY UPDATE는 unique-key 검색용 임시 record를 만든다. 실제 삽입되지 않는 image가 chain을 만들면 orphan이 된다. Non-NULL `probe_would_demote_oos` pointer를 넘겨 suppression을 선택한다. Boolean 초기값이 false여도 **pointer가 존재한다는 것**이 mode 선택이다. Would-demote는 true일 수 있어도 `has_oos` 는 false이고 image는 fully-inline이다. [Duplicate probe](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11955).

FORCE_OUTLINE loop는 일반 record-size gate보다 먼저 실행된다. 추가한 suppression 분기는 would-demote만 설정하고 `continue` 하여 candidate 선택과 payload 축소를 하지 않는다. 일반 candidate 경로도 demotion 전에 inline size를 반환한다. 크기 gate 내부만 막으면 작은 forced 값이 여전히 chain을 생성한다. [FORCE_OUTLINE 분기](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12469).

옛 second-pass API인 `heap_attrinfo_transform_to_disk_oos_class` 도 남아 있다. 이 경로는 increment를 이미 적용한 것으로 표시한다. 현재 main write는 first-pass owner wrapper를 사용한다. Probe 자체는 duplicate lookup과 테스트 reference에 계속 사용된다. Public copy-area wrapper에 non-NULL owner를 넘기는 production call은 소스 검색에서 발견하지 못했다. Rebuild branch는 active main path가 아닌 잔존 API/state다. 기존 review도 선택적 정리 항목으로 지적한다.

Main path에서 early key의 increment는 복사본에만 적용된다. 실제 fixed-column writer는 source에 한 번 적용하고 buffer retry 동안 적용 여부를 기억한다. 기존 LOB writer는 `HEAP_WRITTEN_LOB_ATTRVALUE` 로 ELO 중복 copy를 막는다. Probe가 모든 side effect를 제거하는 것은 아니다. Caller의 LOB flag를 유지하며 REPLACE는 EXCLUDE_LOB, ODKU는 INCLUDE_LOB를 사용한다. [Increment guard](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13131), [LOB 준비](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12692).

## 테스트가 증명하는 범위

SQL 파일에는 기존 4개에 28개 테스트가 추가된다. 부록은 각 테스트의 구성, 실패를 구별하는 assertion, 한계를 설명한다. Direct routing 테스트의 `scoped_sa_server` 는 standalone에서 server interface를 호출할 때 allocator context를 맞춘다. Timeout 300초는 debug stack 수집을 수반하는 rejection·fault-injection 테스트를 위한 것이며 성능 향상의 증거가 아니다.

과거 review는 `988a4d2` 에서 SQL **32/32 통과**를 기록한다. 당시 local CCI는 pinned dependency와 달랐다. `479cd960` 은 vacuum regression을 DISABLED 상태로 보관하며, 직전 reviewed parent의 production/SQL 파일을 바꾸지 않는다. 관련 근거지만 현재 환경 전체를 새로 검증한 것은 아니다. [과거 실행 기록](https://github.com/vimkim/my-cubrid-docs/blob/08870b103aea34148f08bb9e5d9d9c496d4a4e11/cbrd-27089/review-988a4d2-codex/verification.md).

Disabled regression은 committed 원본과 별도의 witness를 만든다. UPDATE 뒤 rollback하고 vacuum 전 원본을 읽는다. Witness를 committed delete하여 실제 vacuum 진행을 확인한 뒤 원본을 다시 읽는다. 과거 실행은 마지막 readback에서 실패했다. Witness가 있어야 단순 daemon wakeup을 실제 정리 성공으로 오해하지 않는다. 이 테스트는 lower-layer 테스트이며 partition 전용 테스트는 아니다. 기존 review는 CBRD-27237과 연관 짓고 있고, 이 PR은 vacuum 구현을 바꾸지 않는다. **DISABLED는 재현 코드를 보존한다는 의미이지 lifecycle gate 통과가 아니다.** [Disabled regression](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_real_vacuum_server.cpp#L828).

이번에 가져온 PR discussion에는 CI trigger 6건과 substantive review summary 1건이 있다. Inline comment와 top-level review record는 없었다. Summary의 미완료 항목은 SERVER_MODE lifecycle 전체, control workload 성능 수용, 최종 통합 근거의 세 가지다. 이번 문서는 새 CI 상태를 주장하지 않는다. [기존 review](https://github.com/CUBRID/cubrid/pull/7600#issuecomment-5599750448).

**검토 판단:** Routing과 owner 선택은 아래 소스 근거로 설명하되 최종 acceptance는 위 gate가 해결되는 조건으로 남긴다. Standalone 성공을 MVCC·vacuum·crash·동시성·성능 전체의 성공으로 확대하지 않는다. Accepted ADR은 여러 오류가 동시에 있는 문장에서 error precedence가 달라질 수 있음을 허용하지만, 단일 오류의 동작과 transactional cleanup은 계속 보존해야 한다.

## 발표 연습 질문

1. SELECT는 성공하는데 vacuum은 왜 종료할 수 있는가? OID 기반 읽기와 heap 기반 file 탐색을 비교한다.
2. Assignment의 DB_VALUE를 바로 routing하면 왜 부족한가? Omitted/default와 CHAR codec을 설명한다.
3. INCR 전에 key를 clone하는 이유는? Routing을 두 번 호출해도 원본 연산을 소비하지 않아야 한다.
4. Moving UPDATE에서 source class를 유지하는 이유는? Old representation·LOB 준비와 OOS 목적지를 나누어 설명한다.
5. 직렬화 뒤 routing을 다시 하는 이유는? Representation patch와 disagreement guard를 연결한다.
6. Error 반환은 즉시 모든 chain 회수를 뜻하는가? Caller의 rollback 의무를 설명한다.
7. 64바이트 forced 값이 왜 중요한가? 일반 size gate보다 앞선 policy loop를 찾는다.
8. 어느 assertion이 물리적 owner를 검증하는가? Logical count만으로는 부족한 이유를 설명한다.
9. Disabled vacuum test가 지금 증명하는 것은? Oracle의 보존과 runtime 통과를 구분한다.
10. 성능 trade-off는? 전체-row probe 비용은 줄지만 scalar 준비와 final routing 비용은 남고, 측정 수용은 아직 열려 있다.
