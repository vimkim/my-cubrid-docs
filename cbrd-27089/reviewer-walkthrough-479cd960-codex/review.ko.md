[Start here: short English guide](start-here.en.md) · [먼저 읽기: 한국어 안내](start-here.ko.html)

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

## 추가 SQL 테스트 설명

테스트 코드의 계약이다. 32/32는 과거 실행이며 이번 실행 결과가 아니다.

### T01 — PartitionedForceOutlineStoresOosInPrunedHeap

[Source 437–504](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L437). 64바이트 forced 값으로 논리값과 root/p0/p1의 chunk 0/1/0을 확인한다. 일반 크기 gate와 분리하여 policy를 검증한다.

### T02 — PartitionRangeBoundaryAndNullOwnership

[Source 506–529](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L506). 10·9·11·NULL을 한 INSERT에 교차 배치한다. 경계와 child별 2개 chunk를 검사하여 row 사이 context 오염을 찾는다.

### T03 — PartitionListExpressionAndFailedBatchOwnership

[Source 531–565](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L531). ABS(id) LIST routing과 valid row 뒤 실패하는 batch를 검사한다. 명시적 abort 후 기존 값·owner를 확인하고 다음 INSERT 성공으로 state 회복을 검증한다.

### T04 — PartitionHashNullOwnership

[Source 567–587](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L567). 반복 key와 NULL의 HASH 결과 및 owner count를 확인한다. 선택한 정수의 기존 규칙 테스트이며 범용 hash 공식의 증명은 아니다.

### T05 — PartitionRangeExpressionValidationAndMovement

[Source 589–630](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L589). RANGE(id+1)의 목적지 없음과 explicit child mismatch를 INSERT/UPDATE로 검사한 뒤 root UPDATE 이동을 확인한다. Error code와 기존 데이터 보존이 핵심이다.

### T06 — PartitionListRejectsNullWithoutDestination

[Source 632–655](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L632). NULL 목적지가 없는 LIST는 OOS file 생성 전에 거절해야 한다. 이후 정상 write는 p1 file만 만든다.

### T07 — PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement

[Source 657–675](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L657). Non-key INCR, 11→9 ODKU 이동, REPLACE를 결합한다. 최종 값과 root file 부재를 확인하지만 모든 child probe orphan과 server lifecycle을 열거하지는 않는다.

### T08 — PartitionUpdateStringDomains

[Source 677–699](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L677). 대소문자 비구분 VARCHAR와 압축 expression key의 길이 경계 이동을 검사한다. DEFAULT-policy 압축 key 사례에서는 forced payload만 OOS다.

### T09 — PartitionUpdateLegalKeysAndNullMovement

[Source 701–746](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L701). 13개 key 명세로 default INSERT·미변경 UPDATE·NULL 이동·재할당·rollback을 검사한다. CHAR 경계를 padding하여 저장 domain 효과를 드러낸다.

### T10 — PartitionUpdateOldOosKeyAndRepresentation

[Source 748–772](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L748). OOS string key에 schema column을 추가하고 payload 갱신·key 이동·abort를 수행한다. Representation 변경 후 default와 여러 payload 보존을 확인한다.

### T11 — PartitionUpdateLobLifecycle

[Source 774–795](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L774). Inline CLOB와 forced BLOB locator를 가진 row를 이동하고 LOB 변경 뒤 abort한다. 외부 내용과 destination chunk 2개를 확인하며 locator와 외부 payload를 구분한다.

### T12 — PartitionUpdateDedicatedIncrementsAndArithmetic

[Source 797–844](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L797). SMALLINT·INT·BIGINT의 INCR/DECR·일반 산술과 극값에서 0이 되는 전용 연산 의미를 검사한다. Routing key와 실제 저장값이 일치해야 한다.

### T13 — EffectiveUpdateRouteUsesMissingHistoricalKeyDefault

[Source 846–913](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L846). Key 추가 전 직렬화 bytes로 old row를 만들고 missing attribute default를 이용하는 UPDATE routing을 확인한다. 실제 heap row 없이 독립 inline reference와 비교해 ALTER redistribution과 분리한다.

### T14 — EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement

[Source 915–1000](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L915). Old key 10에 미변경·+1·-1·9 할당을 시험한다. 반복 routing 후 원본 state·representation·pending 유지, 실제 transform에서 한 번 적용, final OID/HFID 일치를 검사한다.

### T15 — PartitionPreparationFailuresRollBackAndAllowNextWrite

[Source 1002–1068](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1002). INSERT와 moving UPDATE에 publication 이후·reset 이후·VFID 조회 전·OID allocation 실패를 주입한다. Hook 해제와 abort 뒤 값/count 보존 및 다음 성공을 검사한다. Multi-chunk로 부분 publication을 드러낸다.

### T16 — PartitionLobPreparationAndIndexFailuresPreserveCommittedValues

[Source 1070–1111](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1070). VFID 조회 전 LOB 준비와 새 LOB 할당 유무에 따른 unique-key 이동 실패를 검사한다. Abort 후 LOB 내용·OOS count를 확인하고 다음 write 성공을 증명한다.

### T17 — EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment

[Source 1113–1203](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1113). Private attribute/domain copy에만 codec 실패를 주입한다. Write 실패와 부분 read 실패 모두 output NULL·원본 보존을 확인하고 codec 복원 후 재시도한다. 공유 schema는 바꾸지 않는다.

### T18 — EffectiveRoutingFailurePreservesAssignmentsAndPublication

[Source 1205–1272](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1205). OID/LSA publication container에 marker를 넣고 같은 context에서 valid/missing 목적지를 교차한다. 원본 assignment와 두 marker 보존을 확인한 뒤 marker를 정리한다. Durability 테스트는 아니다.

### T19 — EffectiveInsertRoutePreservesOmittedAssignments

[Source 1274–1340](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1274). Omitted CHAR default를 전체 transform 전에 routing하고 candidate slot 모두 uninitialized·NULL인지 확인한다. 독립 reference가 같은 child/HFID를 고르며 OOS file은 없어야 한다.

### T20 — EffectiveInsertRoutePreservesAssignedChar

[Source 1342–1417](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1342). Padding 전 CHAR를 할당하고 bytes/state를 보관한다. Early routing은 독립 직렬화 reference와 같고 원본 bytes 및 payload slot은 유지되어야 한다.

### T21 — EffectiveInsertRouteLegalKeyDefaults

[Source 1419–1496](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1419). 13개 default key 타입의 effective INSERT를 독립 serialized reference와 비교한다. 원본 slot과 root/child OOS 미생성을 확인한다.

### T22 — PartitionInsertLegalKeySqlMatrix

[Source 1498–1546](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1498). 13개 타입의 assigned·NULL·default HASH INSERT를 수행한다. 논리값과 child row/chunk 대응을 검사하고 별도 reference 실행용 관측값을 출력한다. 자체가 별도 reference 실행은 아니다.

### T23 — PartitionInsertOwnsExternalKeyAndMultiplePayloads

[Source 1548–1573](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1548). OOS expression key와 작은 forced·큰 일반 VARBIT를 두 child에 넣는다. Row당 single-chunk 3개여서 child별 정확히 3개여야 한다.

### T24 — PartitionInsertRetainsBigoneRejectionBeforeOos

[Source 1575–1593](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1575). BIT(140000) 옆 forced OOS를 넣어 정확한 bigone 오류와 abort 후 OOS file 부재를 검사한다. Payload NULL인 일반 whole-record overflow는 성공해야 한다.

### T25 — PartitionInsertGeneratedKeysAndDomainConversion

[Source 1595–1611](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1595). AUTO_INCREMENT 9→10이 경계를 넘고 문자열 '11'이 정수로 변환된다. Child count 1/2와 값을 확인한다.

### T26 — PartitionInsertDynamicDefault

[Source 1613–1630](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1613). CURRENT_DATE default를 같은 INSERT의 명시 CURRENT_DATE와 비교한다. 날짜나 hash 목적지를 고정하지 않고 값과 물리 owner를 확인한다.

### T27 — PartitionInsertUsesColumnCollation

[Source 1632–1647](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1632). utf8_en_ci LIST에 BETA·AlPhA·beta를 섞어 넣는다. 대소문자 비구분 routing에서도 payload identity와 child chunk 합계가 맞아야 한다.

### T28 — PartitionInsertCompressedExpressionKey

[Source 1649–1664](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1649). 길이 2999/3000의 forced compressed VARCHAR expression key와 forced payload를 사용한다. 값과 child별 OOS chunk 2개를 확인한다.


## 전체 diff 부록

H 번호는 unified diff hunk 하나에 대응한다. 삭제한 줄도 포함한다. 설명은 실행 코드와 기록된 결정에 기반하며 작성자의 숨은 의도를 단정하지 않는다.

### H01 — Declare routing seams

[src/query/partition.c old:155 / new:155](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R155)

공통 evaluator, stable key 초기화, INSERT internal을 사용 전에 선언한다. 내부 경계이며 외부 entry point는 partition_sr.h에 따로 선언한다.

```diff
@@ -155,6 +155,13 @@ static MATCH_STATUS partition_prune_list (PRUNING_CONTEXT * pinfo, const DB_VALU
 					  PRUNING_BITSET * pruned);
 static MATCH_STATUS partition_prune_hash (PRUNING_CONTEXT * pinfo, const DB_VALUE * val, const PRUNING_OP op,
 					  PRUNING_BITSET * pruned);
+static int partition_find_partition_for_expr (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pinfo, const OID * class_oid,
+					      OR_PARTITION ** partition);
+static int partition_start_key_attrinfo (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pinfo);
+static int partition_prune_insert_internal (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes,
+					    HEAP_CACHE_ATTRINFO * attr_info, PRUNING_CONTEXT * pcontext,
+					    int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid,
+					    OID * superclass_oid);
 static int partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_oid, RECDES * recdes,
 						OID * partition_oid, HFID * partition_hfid);
 #if defined (ENABLE_UNUSED_FUNCTION)
```

### H02 — Separate evaluation from record decoding

[src/query/partition.c old:3454 / new:3461](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3461)

공통 부분을 partition_find_partition_for_expr로 추출하고 thread와 borrowed destination output을 받는다. Decode는 H05의 record adapter로 옮긴다. Effective key와 record key가 같은 partition 의미를 사용하게 한다.

```diff
@@ -3454,64 +3461,42 @@ error_exit:
 }
 
 /*
- * partition_find_partition_for_record () - find the partition in which a
- *					    record should be placed
+ * partition_find_partition_for_expr () - evaluate the bound partition expression
+ *                                       and find its single destination
  * return : error code or NO_ERROR
- * pinfo (in)	  : pruning context
- * class_oid (in) : OID of the root class
- * recdes (in)	  : record descriptor
- * partition_oid (in/out) : OID of the partition in which the record fits
- * partition_hfid (in/out): HFID of the partition in which the record fits
+ * thread_p (in) : thread entry from the pruning context
+ * pinfo (in/out) : loaded pruning context with a bound, readable key value
+ * class_oid (in) : class OID used for expression evaluation
+ * partition (out) : borrowed destination, valid until the context is cleared;
+ *                   written only on success
+ *
+ * The caller owns the bound attributes and their values, and supplies the
+ * evaluation instance OID in pinfo->attr_info.inst_oid. Evaluation may populate
+ * expression caches; it does not transfer ownership or clear values. Record
+ * decoding, representation changes and explicit-partition validation belong
+ * to callers.
  */
 static int
-partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_oid, RECDES * recdes,
-				     OID * partition_oid, HFID * partition_hfid)
+partition_find_partition_for_expr (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pinfo, const OID * class_oid,
+				   OR_PARTITION ** partition)
 {
   PRUNING_BITSET pruned;
   PRUNING_BITSET_ITERATOR it;
-  bool clear_dbvalues = false;
   DB_VALUE *result = NULL;
   MATCH_STATUS status = MATCH_NOT_FOUND;
   int error = NO_ERROR, count = 0, pos;
   PRUNING_OP op = PO_EQ;
-  REPR_ID repr_id = NULL_REPRID;
 
-  assert (partition_oid != NULL);
-  assert (partition_hfid != NULL);
+  assert (partition != NULL);
 
   pruningset_init (&pruned, PARTITIONS_COUNT (pinfo));
 
-  if (pinfo->is_attr_info_inited == false)
-    {
-      error = heap_attrinfo_start (pinfo->thread_p, &pinfo->root_oid, 1, &pinfo->attr_id, &pinfo->attr_info);
-      if (error != NO_ERROR)
-	{
-	  goto cleanup;
-	}
-
-      partition_set_cache_info_for_expr (pinfo->partition_pred->func_regu, pinfo->attr_id, &pinfo->attr_info);
-      pinfo->is_attr_info_inited = true;
-    }
-
-  /* set root representation id to the recdes so that we can read the value as belonging to the partitioned table */
-  repr_id = or_rep_id (recdes);
-  or_set_rep_id (recdes, pinfo->root_repr_id);
-
-  error = heap_attrinfo_read_dbvalues (pinfo->thread_p, &pinfo->attr_info.inst_oid, recdes, &pinfo->attr_info);
-
-  or_set_rep_id (recdes, repr_id);
-  if (error != NO_ERROR)
-    {
-      goto cleanup;
-    }
-  clear_dbvalues = true;
-
   error =
-    fetch_peek_dbval (pinfo->thread_p, pinfo->partition_pred->func_regu, NULL, (OID *) class_oid,
+    fetch_peek_dbval (thread_p, pinfo->partition_pred->func_regu, NULL, (OID *) class_oid,
 		      &pinfo->attr_info.inst_oid, NULL, &result);
   if (error != NO_ERROR)
     {
-      goto cleanup;
+      return error;
     }
 
   assert (result != NULL);
```

### H03 — Return missing-partition errors directly

[src/query/partition.c old:3527 / new:3512](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3512)

Evaluator가 임시 record value의 정리를 소유하지 않으므로 match 실패를 직접 반환한다. Key를 소유한 adapter가 정리한다.

```diff
@@ -3527,8 +3512,7 @@ partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_
   if (status != MATCH_OK)
     {
       er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_PARTITION_NOT_EXIST, 0);
-      error = ER_PARTITION_NOT_EXIST;
-      goto cleanup;
+      return ER_PARTITION_NOT_EXIST;
     }
 
   if (count != 1)
```

### H04 — Preserve the non-single-result error

[src/query/partition.c old:3546 / new:3530](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3530)

목적지 없음과 internal error를 구별하는 기존 코드는 유지하고 cleanup jump만 직접 return으로 바꾼다. 목적지가 정확히 하나여야 한다는 조건은 유지된다.

```diff
@@ -3546,7 +3530,7 @@ partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_
 	  /* This is an internal *error (allocation, etc). Error was set by the calls above, just set *error code */
 	  error = pinfo->error_code;
 	}
-      goto cleanup;
+      return error;
     }
 
   pruningset_iterator_init (&pruned, &it);
```

### H05 — Stable key slot and two adapters

[src/query/partition.c old:3554 / new:3538](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3538)

Context 소유 OR_PARTITION을 반환하고 one-key slot과 attrinfo adapter를 추가한다. 이전 key를 clear → readable 표시 → 독립 effective key 준비 → 평가 성공 시 OID/HFID 복사 → value 정리 순서다. 기존 record adapter는 root representation으로 읽고 원래 ID를 복원한 뒤 공통 evaluator를 호출하며 destination representation patch를 유지한다.

```diff
@@ -3554,8 +3538,121 @@ partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_
   pos = pruningset_iterator_next (&it);
   assert_release (pos >= 0);
 
-  COPY_OID (partition_oid, &pinfo->partitions[pos + 1].class_oid);
-  HFID_COPY (partition_hfid, &pinfo->partitions[pos + 1].class_hfid);
+  *partition = &pinfo->partitions[pos + 1];
+  return NO_ERROR;
+}
+
+/*
+ * partition_start_key_attrinfo () - bind the expression to the context-owned key slot
+ */
+static int
+partition_start_key_attrinfo (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pinfo)
+{
+  int error;
+
+  if (!pinfo->is_attr_info_inited)
+    {
+      error = heap_attrinfo_start (thread_p, &pinfo->root_oid, 1, &pinfo->attr_id, &pinfo->attr_info);
+      if (error != NO_ERROR)
+	{
+	  return error;
+	}
+      partition_set_cache_info_for_expr (pinfo->partition_pred->func_regu, pinfo->attr_id, &pinfo->attr_info);
+      pinfo->is_attr_info_inited = true;
+    }
+  return NO_ERROR;
+}
+
+/*
+ * partition_find_partition_for_attrinfo () - route one effective key without preparing the source row
+ */
+static int
+partition_find_partition_for_attrinfo (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pcontext, const OID * class_oid,
+				       HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
+				       OID * pruned_class_oid, HFID * pruned_hfid)
+{
+  int error = partition_start_key_attrinfo (thread_p, pcontext);
+  if (error != NO_ERROR)
+    {
+      return error;
+    }
+
+  /* Expression bindings must use the existing stable slot, not a stack DB_VALUE. */
+  HEAP_ATTRVALUE *key = &pcontext->attr_info.values[0];
+  OR_PARTITION *partition = NULL;
+  assert (pcontext->attr_info.num_values == 1 && key->attrid == pcontext->attr_id);
+  /* A duplicate-key index probe can leave its key in this same context. Retain the slot/bindings,
+   * but release that previous value before preparing this write's key. Source assignments are separate. */
+  assert (attr_info != &pcontext->attr_info);
+  error = heap_attrinfo_clear_dbvalues (&pcontext->attr_info);
+  if (error != NO_ERROR)
+    {
+      return error;
+    }
+  key->state = HEAP_READ_ATTRVALUE;
+  error = heap_attrinfo_get_effective_key (thread_p, attr_info, pcontext->attr_id, old_recdes, &key->dbvalue);
+  if (error == NO_ERROR)
+    {
+      error = partition_find_partition_for_expr (thread_p, pcontext, class_oid, &partition);
+    }
+  if (error == NO_ERROR)
+    {
+      COPY_OID (pruned_class_oid, &partition->class_oid);
+      HFID_COPY (pruned_hfid, &partition->class_hfid);
+    }
+  heap_attrinfo_clear_dbvalues (&pcontext->attr_info);
+  return error;
+}
+
+/*
+ * partition_find_partition_for_record () - find the partition in which a
+ *                                        record should be placed
+ * return : error code or NO_ERROR
+ * pinfo (in)     : pruning context
+ * class_oid (in) : OID of the root class or the source partition
+ * recdes (in)    : record descriptor
+ * partition_oid (in/out) : OID of the partition in which the record fits
+ * partition_hfid (in/out): HFID of the partition in which the record fits
+ */
+static int
+partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_oid, RECDES * recdes,
+				     OID * partition_oid, HFID * partition_hfid)
+{
+  bool clear_dbvalues = false;
+  int error = NO_ERROR;
+  REPR_ID repr_id = NULL_REPRID;
+  OR_PARTITION *partition = NULL;
+
+  assert (partition_oid != NULL);
+  assert (partition_hfid != NULL);
+
+  error = partition_start_key_attrinfo (pinfo->thread_p, pinfo);
+  if (error != NO_ERROR)
+    {
+      goto cleanup;
+    }
+
+  /* set root representation id to the recdes so that we can read the value as belonging to the partitioned table */
+  repr_id = or_rep_id (recdes);
+  or_set_rep_id (recdes, pinfo->root_repr_id);
+
+  error = heap_attrinfo_read_dbvalues (pinfo->thread_p, &pinfo->attr_info.inst_oid, recdes, &pinfo->attr_info);
+
+  or_set_rep_id (recdes, repr_id);
+  if (error != NO_ERROR)
+    {
+      goto cleanup;
+    }
+  clear_dbvalues = true;
+
+  error = partition_find_partition_for_expr (pinfo->thread_p, pinfo, class_oid, &partition);
+  if (error != NO_ERROR)
+    {
+      goto cleanup;
+    }
+
+  COPY_OID (partition_oid, &partition->class_oid);
+  HFID_COPY (partition_hfid, &partition->class_hfid);
 
   if (!OID_EQ (class_oid, partition_oid))
     {
```

### H06 — Use the returned partition representation

[src/query/partition.c old:3566 / new:3663](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3663)

Evaluator 내부의 pos 대신 반환받은 partition에서 rep_id를 읽는다. 같은 descriptor가 OID, HFID, representation ID를 제공한다.

```diff
@@ -3566,7 +3663,7 @@ partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_
        * will be exactly the same. Because of this, we can take a shortcut here and only update the bits from the
        * representation id */
 
-      repr_id = pinfo->partitions[pos + 1].rep_id;
+      repr_id = partition->rep_id;
       error = or_set_rep_id (recdes, repr_id);
     }
 
```

### H07 — Document the dual INSERT input

[src/query/partition.c old:3580 / new:3677](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3677)

INSERT 공통 internal 문서에서 attr_info가 recdes의 대체 입력임을 명시하고 실제 인자가 아닌 scan_cache 설명을 제거한다.

```diff
@@ -3580,12 +3677,12 @@ cleanup:
 }
 
 /*
- * partition_prune_insert () - perform pruning for insert
+ * partition_prune_insert_internal () - shared context and validation contract for INSERT routing
  * return : error code or NO_ERROR
  * thread_p (in)  : thread entry
  * class_oid (in) : OID of the root class
  * recdes (in)	  : Record describing the new object
- * scan_cache (in): Heap scan cache
+ * attr_info (in): source INSERT assignments, or NULL to route recdes instead
  * pcontext (in)  : pruning context
  * pruning_type (in) : pruning type
  * pruned_class_oid (in/out) : partition to insert into
```

### H08 — Share INSERT context management

[src/query/partition.c old:3601 / new:3698](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3698)

구현을 private으로 만들고 recdes와 attr_info를 받는다. Public wrapper가 입력 하나를 선택하고 context 로드·검증·정리는 공유한다.

```diff
@@ -3601,10 +3698,10 @@ cleanup:
  * partition_init_pruning_context) and pass it to this function for each
  * insert operation in the query.
  */
-int
-partition_prune_insert (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes, HEAP_SCANCACHE * scan_cache,
-			PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid,
-			OID * superclass_oid)
+static int
+partition_prune_insert_internal (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes,
+				 HEAP_CACHE_ATTRINFO * attr_info, PRUNING_CONTEXT * pcontext, int pruning_type,
+				 OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
 {
   PRUNING_CONTEXT pinfo;
   bool keep_pruning_context = false;
```

### H09 — Select the INSERT input adapter

[src/query/partition.c old:3657 / new:3754](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3754)

attr_info가 있으면 old_recdes=NULL인 key route를, 없으면 record route를 선택한다. 이후 explicit partition 검증과 cleanup은 동일하다.

```diff
@@ -3657,7 +3754,15 @@ partition_prune_insert (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES *
       goto cleanup;
     }
 
-  error = partition_find_partition_for_record (pcontext, class_oid, recdes, pruned_class_oid, pruned_hfid);
+  if (attr_info != NULL)
+    {
+      error = partition_find_partition_for_attrinfo (thread_p, pcontext, class_oid, attr_info, NULL,
+						     pruned_class_oid, pruned_hfid);
+    }
+  else
+    {
+      error = partition_find_partition_for_record (pcontext, class_oid, recdes, pruned_class_oid, pruned_hfid);
+    }
   if (error != NO_ERROR)
     {
       goto cleanup;
```

### H10 — Preserve public INSERT and expose early routing

[src/query/partition.c old:3689 / new:3794](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3794)

기존 INSERT signature는 NULL attrinfo를 넘기는 wrapper가 된다. 새 by_attrinfo는 NULL recdes와 실제 assignment를 넘긴다. UPDATE 문서도 key routing의 old row와 final routing의 new row를 구별한다.

```diff
@@ -3689,11 +3794,41 @@ cleanup:
 }
 
 /*
- * partition_prune_update () - perform pruning on update statements
+ * partition_prune_insert () - route an already serialized INSERT record
+ */
+int
+partition_prune_insert (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes, HEAP_SCANCACHE * scan_cache,
+			PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid,
+			OID * superclass_oid)
+{
+  return partition_prune_insert_internal (thread_p, class_oid, recdes, NULL, pcontext, pruning_type,
+					  pruned_class_oid, pruned_hfid, superclass_oid);
+}
+
+/*
+ * partition_prune_insert_by_attrinfo () - route an INSERT without changing its assignments
+ *
+ * Context ownership, explicit-partition validation and outputs match partition_prune_insert.
+ * The key is owned by the routing context and cleared before returning; source assignments,
+ * LOB objects, OOS publication and the record representation are untouched.
+ */
+int
+partition_prune_insert_by_attrinfo (THREAD_ENTRY * thread_p, const OID * class_oid, HEAP_CACHE_ATTRINFO * attr_info,
+				    PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid,
+				    HFID * pruned_hfid, OID * superclass_oid)
+{
+  assert (attr_info != NULL);
+  return partition_prune_insert_internal (thread_p, class_oid, NULL, attr_info, pcontext, pruning_type,
+					  pruned_class_oid, pruned_hfid, superclass_oid);
+}
+
+/*
+ * partition_prune_update_internal () - shared context and validation contract for UPDATE routing
  * return : error code or NO_ERROR
  * thread_p (in)  : thread entry
  * class_oid (in) : OID of the root class
- * recdes (in)	  : Record describing the new object
+ * recdes (in)	  : new record for record routing, supplied old record for attribute routing
+ * attr_info (in): source UPDATE assignments, or NULL to route the new record
  * pcontext (in)  : pruning context
  * pruning_type (in) : pruning type
  * pruned_class_oid (in/out) : partition to insert into
```

### H11 — Share UPDATE context management

[src/query/partition.c old:3708 / new:3843](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3843)

UPDATE internal에 optional attrinfo를 추가한다. Source child에서 root를 찾는 로직과 caller context의 조건은 공통 구현에 남긴다.

```diff
@@ -3708,9 +3843,10 @@ cleanup:
  * caller should initialize a PRUNING_CONTEXT object (by calling
  * partition_init_pruning_context) and pass it to this function.
  */
-int
-partition_prune_update (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes, PRUNING_CONTEXT * pcontext,
-			int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
+static int
+partition_prune_update_internal (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes,
+				 HEAP_CACHE_ATTRINFO * attr_info, PRUNING_CONTEXT * pcontext,
+				 int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
 {
   PRUNING_CONTEXT pinfo;
   int error = NO_ERROR;
```

### H12 — Select the UPDATE input adapter

[src/query/partition.c old:3790 / new:3926](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3926)

attrinfo mode의 recdes는 변경하지 않은 key를 읽을 old row이고, record mode에서는 직렬화한 new row다. 이 구분으로 이전 값을 현재 default로 대체하지 않는다.

```diff
@@ -3790,7 +3926,15 @@ partition_prune_update (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES *
       goto cleanup;
     }
 
-  error = partition_find_partition_for_record (pcontext, class_oid, recdes, pruned_class_oid, pruned_hfid);
+  if (attr_info != NULL)
+    {
+      error = partition_find_partition_for_attrinfo (thread_p, pcontext, class_oid, attr_info, recdes,
+						     pruned_class_oid, pruned_hfid);
+    }
+  else
+    {
+      error = partition_find_partition_for_record (pcontext, class_oid, recdes, pruned_class_oid, pruned_hfid);
+    }
   if (error != NO_ERROR)
     {
       goto cleanup;
```

### H13 — Expose early UPDATE without changing final route

[src/query/partition.c old:3823 / new:3967](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3967)

기존 UPDATE wrapper는 NULL attrinfo를 넘긴다. 새 by_attrinfo는 old_recdes를 명시한다. Key 입력만 다르고 검증과 context lifetime은 공유한다.

```diff
@@ -3823,6 +3967,30 @@ cleanup:
   return error;
 }
 
+/*
+ * partition_prune_update () - retain final record routing and representation patching
+ */
+int
+partition_prune_update (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes, PRUNING_CONTEXT * pcontext,
+			int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
+{
+  return partition_prune_update_internal (thread_p, class_oid, recdes, NULL, pcontext, pruning_type,
+					  pruned_class_oid, pruned_hfid, superclass_oid);
+}
+
+/*
+ * partition_prune_update_by_attrinfo () - route assignments and the supplied old row without changing either
+ */
+int
+partition_prune_update_by_attrinfo (THREAD_ENTRY * thread_p, const OID * class_oid, HEAP_CACHE_ATTRINFO * attr_info,
+				    RECDES * old_recdes, PRUNING_CONTEXT * pcontext, int pruning_type,
+				    OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
+{
+  assert (attr_info != NULL);
+  return partition_prune_update_internal (thread_p, class_oid, old_recdes, attr_info, pcontext, pruning_type,
+					  pruned_class_oid, pruned_hfid, superclass_oid);
+}
+
 /*
  * partition_get_scancache () - get scan_cache for a partition
  * return : cached object or NULL
```

### H14 — Declare the early-routing APIs

[src/query/partition_sr.h old:119 / new:119](https://github.com/CUBRID/cubrid/pull/7600/files#diff-867d8cafbd04828c54bbe2f2bb3b25eaef8781ac2fb5fd4648c5139a2f5de245R119)

Locator가 호출할 by_attrinfo API를 선언한다. UPDATE는 old record를 받으며 OID/HFID와 optional superclass output은 기존 routing 형태를 따른다.

```diff
@@ -119,6 +119,16 @@ extern int partition_prune_update (THREAD_ENTRY * thread_p, const OID * class_oi
 				   PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid,
 				   HFID * pruned_hfid, OID * superclass_oid);
 
+extern int partition_prune_insert_by_attrinfo (THREAD_ENTRY * thread_p, const OID * class_oid,
+					       HEAP_CACHE_ATTRINFO * attr_info, PRUNING_CONTEXT * pcontext,
+					       int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid,
+					       OID * superclass_oid);
+
+extern int partition_prune_update_by_attrinfo (THREAD_ENTRY * thread_p, const OID * class_oid,
+					       HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
+					       PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid,
+					       HFID * pruned_hfid, OID * superclass_oid);
+
 extern int partition_prune_unique_btid (PRUNING_CONTEXT * pcontext, DB_VALUE * key, OID * class_oid, HFID * class_hfid,
 					BTID * btid);
 
```

### H15 — REPLACE probe mode storage

[src/query/query_executor.c old:11937 / new:11937](https://github.com/CUBRID/cubrid/pull/7600/files#diff-9bedce9f6f01d1dd366be206555b8f76561e570ccaba901b4cdda27cdc231768R11937)

주소를 넘겨 suppression을 선택할 Boolean을 추가한다. 초기 false는 결과 초기값이며 suppression 비활성화가 아니다.

```diff
@@ -11937,6 +11937,7 @@ qexec_remove_duplicates_for_replace (THREAD_ENTRY * thread_p, HEAP_SCANCACHE * s
   OID class_oid, pruned_oid;
   BTID btid;
   bool is_global_index;
+  bool probe_would_demote_oos = false;
   HFID class_hfid, pruned_hfid;
   int local_op_type = SINGLE_ROW_DELETE;
   HEAP_SCANCACHE *local_scan_cache = NULL;
```

### H16 — Suppress REPLACE probe publication

[src/query/query_executor.c old:11951 / new:11952](https://github.com/CUBRID/cubrid/pull/7600/files#diff-9bedce9f6f01d1dd366be206555b8f76561e570ccaba901b4cdda27cdc231768R11952)

Duplicate-search image에 NULL owner와 non-NULL verdict pointer를 넘긴다. EXCLUDE_LOB는 유지한다. 저장하지 않는 image이므로 OOS chain을 생성하지 않아야 한다.

```diff
@@ -11951,7 +11952,11 @@ qexec_remove_duplicates_for_replace (THREAD_ENTRY * thread_p, HEAP_SCANCACHE * s
       goto error_exit;
     }
 
-  copyarea = locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &new_recdes, -1, LOB_FLAG_EXCLUDE_LOB);
+  /* This record image is only probed for duplicate keys, never inserted: suppress OOS demotion so
+   * no OOS value chain is written (and later orphaned) for it. */
+  copyarea =
+    locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &new_recdes, -1, LOB_FLAG_EXCLUDE_LOB, NULL,
+					     &probe_would_demote_oos);
   if (copyarea == NULL)
     {
       goto error_exit;
```

### H17 — ODKU probe mode storage

[src/query/query_executor.c old:12170 / new:12175](https://github.com/CUBRID/cubrid/pull/7600/files#diff-9bedce9f6f01d1dd366be206555b8f76561e570ccaba901b4cdda27cdc231768R12175)

ODKU lookup에도 verdict storage를 추가한다. Pointer 존재로 mode를 선택하며 caller는 반환 Boolean을 이후 사용하지 않는다.

```diff
@@ -12170,6 +12175,7 @@ qexec_oid_of_duplicate_key_update (THREAD_ENTRY * thread_p, HEAP_SCANCACHE ** pr
   OID class_oid;
   HFID class_hfid;
   bool is_global_index = false;
+  bool probe_would_demote_oos = false;
   int local_op_type = SINGLE_ROW_UPDATE;
   BTREE_SEARCH r;
 
```

### H18 — Suppress ODKU probe publication

[src/query/query_executor.c old:12189 / new:12195](https://github.com/CUBRID/cubrid/pull/7600/files#diff-9bedce9f6f01d1dd366be206555b8f76561e570ccaba901b4cdda27cdc231768R12195)

ODKU 임시 image의 OOS publication을 억제하면서 INCLUDE_LOB는 유지한다. OOS 생성 방지이며 LOB 준비까지 side effect가 없다는 뜻은 아니다.

```diff
@@ -12189,7 +12195,11 @@ qexec_oid_of_duplicate_key_update (THREAD_ENTRY * thread_p, HEAP_SCANCACHE ** pr
       goto error_exit;
     }
 
-  copyarea = locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &recdes, -1, LOB_FLAG_INCLUDE_LOB);
+  /* This record image is only probed for unique-index duplicates, never inserted: suppress OOS
+   * demotion so no OOS value chain is written (and later orphaned) for it. */
+  copyarea =
+    locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &recdes, -1, LOB_FLAG_INCLUDE_LOB, NULL,
+					     &probe_would_demote_oos);
   if (copyarea == NULL)
     {
       goto error_exit;
```

### H19 — Extend layout planning contract

[src/storage/heap_file.c old:694 / new:694](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R694)

Layout planner에 suppress_oos와 would_demote_oos를 추가한다. 실제 배치와 정상 mode에서의 demotion 예상은 다른 output이다.

```diff
@@ -694,9 +694,10 @@ struct heap_oos_column_plan
   DB_BIGINT length = 0;
 };
 static int heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class,
-						size_t * offset_size_ptr,
+						bool suppress_oos, size_t * offset_size_ptr,
 						std::vector<heap_oos_column_plan> * oos_plan,
-						bool * has_oos, size_t * inline_size_after_oos_ptr);
+						bool * has_oos, bool * would_demote_oos,
+						size_t * inline_size_after_oos_ptr);
 // *INDENT-ON*
 
 static void heap_attrvalue_point_fixed (RECDES * recdes, HEAP_CACHE_ATTRINFO * attr_info, OR_ATTRIBUTE * attrepr,
```

### H20 — Extend the common transform contract

[src/storage/heap_file.c old:782 / new:783](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R783)

공통 변환에 owner, suppression output, second-pass increment state를 추가한다. Wrapper가 조합을 정하며 기본은 정상 first pass다.

```diff
@@ -782,7 +783,8 @@ static SCAN_CODE heap_attrinfo_transform_columns_to_disk (THREAD_ENTRY * thread_
 
 static SCAN_CODE heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 							   RECDES * old_recdes, record_descriptor * new_recdes,
-							   int lob_create_flag);
+							   int lob_create_flag, const OID * oos_class_oid,
+							   bool * would_demote_oos, bool increments_already_applied);
 
 static int heap_update_statistics (THREAD_ENTRY * thread_p, const HFID * hfid, HEAP_HDR_STATS * heap_hdr,
 				   PGBUF_WATCHER * header_watcher);
```

### H21 — Compute an owned effective key

[src/storage/heap_file.c old:12095 / new:12097](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12097)

UPDATE의 미지정 key는 supplied old row의 독립 reader로 읽고, INSERT default는 복사 metadata에서 읽으며, 주어진 값은 clone한다. 복사본에만 increment를 적용하고 NULL을 보존한 뒤 domain codec으로 size/write/read한다. 작은 값은 aligned scratch, 큰 값은 별도 할당을 쓴다. 실패 시 부분 output도 clear한다. 본문의 블록 표와 direct reference 테스트가 각 분기를 설명한다.

```diff
@@ -12095,6 +12097,132 @@ exit_on_error:
   return (ret == NO_ERROR && (ret = er_errid ()) == NO_ERROR) ? ER_FAILED : ret;
 }
 
+/*
+ * heap_attrinfo_get_effective_key () - obtain the stored-value equivalent of a write's partition key
+ *   return: NO_ERROR or an error code
+ *   attr_info(in): source assignments; never initialized or otherwise modified here
+ *   attrid(in): a schema-validated partition-key attribute
+ *   old_recdes(in): the write path's old row, or NULL for INSERT
+ *   key(out): owned value, initially NULL; caller clears it
+ *
+ * Only the key is prepared. Omitted values use the same representation default
+ * reader as a normal INSERT. Unchanged UPDATE keys use an independent one-key
+ * reader of the supplied old representation. Pending increments affect only
+ * the owned key; the normal row transformer still applies the real mutation.
+ * The scalar codec operates on an owned copy because sizing/writing may
+ * normalize CHAR padding or cache string compression.
+ * No row image, LOB lifecycle operation, or OOS publication is performed.
+ */
+int
+heap_attrinfo_get_effective_key (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, ATTR_ID attrid,
+				 RECDES * old_recdes, DB_VALUE * key)
+{
+  HEAP_ATTRVALUE *value;
+  HEAP_ATTRVALUE omitted;
+  DB_VALUE prepared;
+  const PR_TYPE *pr_type;
+  OR_BUF buf;
+  char scratch[64 + MAX_ALIGNMENT];
+  char *data = PTR_ALIGN (scratch, MAX_ALIGNMENT);
+  char *allocated = NULL;
+  int length;
+  int error = NO_ERROR;
+
+  assert (DB_IS_NULL (key));
+  db_make_null (&prepared);
+  value = heap_attrvalue_locate (attrid, attr_info);
+  if (value == NULL)
+    {
+      return er_errid () != NO_ERROR ? er_errid () : ER_FAILED;
+    }
+  if (value->state == HEAP_UNINIT_ATTRVALUE && old_recdes != NULL && old_recdes->data != NULL)
+    {
+      HEAP_CACHE_ATTRINFO old_key;
+
+      error = heap_attrinfo_start (thread_p, &attr_info->class_oid, 1, &attrid, &old_key);
+      if (error != NO_ERROR)
+	{
+	  goto cleanup;
+	}
+      error = heap_attrinfo_read_dbvalues_without_oid (thread_p, old_recdes, &old_key);
+      if (error == NO_ERROR)
+	{
+	  error = pr_clone_value (&old_key.values[0].dbvalue, &prepared);
+	}
+      heap_attrinfo_end (thread_p, &old_key);
+    }
+  else if (value->state == HEAP_UNINIT_ATTRVALUE)
+    {
+      omitted = *value;
+      db_make_null (&omitted.dbvalue);
+      error = heap_attrvalue_read (NULL, &omitted, attr_info);
+      if (error == NO_ERROR)
+	{
+	  error = pr_clone_value (&omitted.dbvalue, &prepared);
+	}
+      pr_clear_value (&omitted.dbvalue);
+    }
+  else
+    {
+      error = pr_clone_value (&value->dbvalue, &prepared);
+    }
+  if (error != NO_ERROR)
+    {
+      goto cleanup;
+    }
+  if (value->do_increment != 0)
+    {
+      error = qdata_increment_dbval (&prepared, &prepared, value->do_increment);
+      if (error != NO_ERROR)
+	{
+	  goto cleanup;
+	}
+    }
+  if (DB_IS_NULL (&prepared))
+    {
+      error = pr_clone_value (&prepared, key);
+      goto cleanup;
+    }
+
+  pr_type = value->last_attrepr->domain->type;
+  length = pr_type->get_disk_size_of_value (&prepared);
+  if (length <= 0)
+    {
+      error = er_errid () != NO_ERROR ? er_errid () : ER_FAILED;
+      goto cleanup;
+    }
+  if (length > 64)
+    {
+      allocated = (char *) db_private_alloc (thread_p, length);
+      if (allocated == NULL)
+	{
+	  error = ER_OUT_OF_VIRTUAL_MEMORY;
+	  goto cleanup;
+	}
+      data = allocated;
+    }
+  or_init (&buf, data, length);
+  error = pr_type->data_writeval (&buf, &prepared);
+  if (error == NO_ERROR)
+    {
+      length = CAST_BUFLEN (buf.ptr - data);
+      or_init (&buf, data, length);
+      error = pr_type->data_readval (&buf, key, value->last_attrepr->domain, length, true, NULL, 0);
+    }
+
+cleanup:
+  pr_clear_value (&prepared);
+  if (allocated != NULL)
+    {
+      db_private_free_and_init (thread_p, allocated);
+    }
+  if (error != NO_ERROR)
+    {
+      pr_clear_value (key);
+    }
+  return error;
+}
+
 /*
  * heap_attrinfo_set_uninitialized () - Read unitialized attributes
  *   return: NO_ERROR
```

### H22 — Document suppression outputs

[src/storage/heap_file.c old:12297 / new:12425](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12425)

Suppression은 inline을 유지하고 would_demote는 가정 결과임을 설명한다. has_oos는 실제 layout을 뜻한다.

```diff
@@ -12297,9 +12425,11 @@ heap_attrinfo_get_record_header_size (HEAP_CACHE_ATTRINFO * attr_info, int paylo
  *   return: NO_ERROR, or error code
  *   attr_info(in/out): The attribute information structure
  *   is_mvcc_class(in): true, if MVCC class
+ *   suppress_oos(in): true to keep every column inline even when the record exceeds the OOS trigger
  *   offset_size_ptr(out): offset size
  *   oos_plan(out): selected columns are demoted to OOS
  *   has_oos(out): true if any column is demoted to OOS
+ *   would_demote_oos(out): with suppress_oos, true if a normal layout would have demoted a column
  *   inline_size_after_oos_ptr(out): inline heap record size after OOS demotion
  *
  * Note: Choose the OOS layout and compute the inline heap record size. This size is not the logical
```

### H23 — Implement the extended planner signature

[src/storage/heap_file.c old:12307 / new:12437](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12437)

선언·정의·호출을 일치시킨다. Mode를 받아 OOS plan entry를 선택하기 전에 suppression을 처리한다.

```diff
@@ -12307,9 +12437,10 @@ heap_attrinfo_get_record_header_size (HEAP_CACHE_ATTRINFO * attr_info, int paylo
  */
 // *INDENT-OFF*
 static int
-heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class, size_t * offset_size_ptr,
+heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class, bool suppress_oos,
+					     size_t * offset_size_ptr,
 					     std::vector<heap_oos_column_plan> * oos_plan, bool * has_oos,
-					     size_t * inline_size_after_oos_ptr)
+					     bool * would_demote_oos, size_t * inline_size_after_oos_ptr)
 // *INDENT-ON*
 {
 // *INDENT-OFF*
```

### H24 — Reset the per-call verdict

[src/storage/heap_file.c old:12320 / new:12451](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12451)

Column 순회 전에 has_oos와 optional verdict를 false로 초기화한다. 이전 row의 결과가 재사용 Boolean에 남지 않게 한다.

```diff
@@ -12320,6 +12451,10 @@ heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mv
   int i;
 
   *has_oos = false;
+  if (would_demote_oos != NULL)
+    {
+      *would_demote_oos = false;
+    }
 
   /* calcuate the entire size of columns */
   payload_size = heap_attrinfo_get_record_payload_size (attr_info, &column_size);
```

### H25 — Suppress the forced policy before selection

[src/storage/heap_file.c old:12334 / new:12469](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12469)

FORCE_OUTLINE은 일반 크기 gate보다 먼저 실행된다. Suppression에서는 verdict만 설정하고 selected·payload 축소·has_oos 설정 전에 continue한다. 작은 forced 값 회귀의 핵심 분기다.

```diff
@@ -12334,6 +12469,15 @@ heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mv
 	  && attr_info->values[i].last_attrepr->oos_storage == OR_ATTRIBUTE_OOS_STORAGE_FORCE_OUTLINE
 	  && !db_value_is_null (&attr_info->values[i].dbvalue) && column_size[i] > OR_OOS_INLINE_SIZE)
 	{
+	  if (suppress_oos)
+	    {
+	      if (would_demote_oos != NULL)
+		{
+		  *would_demote_oos = true;
+		}
+	      continue;
+	    }
+
 	  (*oos_plan)[i].selected = true;
 	  payload_size -= column_size[i];
 	  payload_size += OR_OOS_INLINE_SIZE;
```

### H26 — Suppress ordinary demotion

[src/storage/heap_file.c old:12369 / new:12513](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12513)

일반 candidate 수집 뒤 존재 여부를 verdict로 기록하고 정렬·선택·demotion 없이 fully-inline 크기를 반환한다. 임시 image는 heap slot보다 클 수 있다.

```diff
@@ -12369,6 +12513,19 @@ heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mv
 	    }
 	}
 
+      if (suppress_oos)
+	{
+	  /* The caller only wants a fully-inline image plus the demotion verdict (e.g. to route a
+	   * partitioned write before the target heap of its OOS value chains is known). */
+	  if (would_demote_oos != NULL && !oos_candidates.empty ())
+	    {
+	      *would_demote_oos = true;
+	    }
+
+	  *inline_size_after_oos_ptr = header_size + payload_size;
+	  return NO_ERROR;
+	}
+
       // *INDENT-OFF*
       /* Demote order: columns flagged STORAGE PREFER_INLINE sink to the tail and are externalized
        * only as a last resort; within each priority class, largest first. The idx-descending
```

### H27 — Add explicit OOS owner at insertion boundary

[src/storage/heap_file.c old:12680 / new:12837](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12837)

OOS insert 경계에 optional class OID를 추가하고 heap 단위 소유권을 문서화한다. Payload와 LOB 준비에는 source attrinfo를 유지한다.

```diff
@@ -12680,11 +12837,15 @@ static std::atomic<bool> heap_Test_fail_after_oos_publication_reset { false };
  * the BLOB/CLOB ELO-locator copy step, with the inline record writer. This logical heap boundary
  * begins OOS insert publication before any fallible preparation; heap_oos.cpp owns the paired-reset
  * internals, OOS file lookup, and the batched OOS insert call.
+ *
+ * oos_class_oid designates the class whose heap receives the OOS value chains; NULL means
+ * attr_info->class_oid. A partitioned write must pass the pruned partition class, because the
+ * value chains must live in the OOS file of the heap that stores the record (CBRD-27089).
  */
 // *INDENT-OFF*
 static SCAN_CODE
 heap_attrinfo_insert_to_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, int lob_create_flag,
-			     std::vector<heap_oos_column_plan> * oos_plan)
+			     const OID * oos_class_oid, std::vector<heap_oos_column_plan> * oos_plan)
 // *INDENT-ON*
 
 {
```

### H28 — Apply the selected owner

[src/storage/heap_file.c old:12724 / new:12885](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12885)

Override가 있으면 해당 class를 storage helper에 넘기고 없으면 기존 attrinfo class를 쓴다. Early destination이 물리적 OOS file 선택으로 연결되는 줄이다.

```diff
@@ -12724,7 +12885,7 @@ heap_attrinfo_insert_to_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr
       goto cleanup;
     }
 
-  if (heap_oos_insert_serialized_values (thread_p, &attr_info->class_oid,
+  if (heap_oos_insert_serialized_values (thread_p, oos_class_oid != NULL ? oos_class_oid : &attr_info->class_oid,
 					 cubbase::span < oos_insert_request > (requests.data (), requests.size ()))
       != S_SUCCESS)
     {
```

### H29 — Separate transform modes explicitly

[src/storage/heap_file.c old:12755 / new:12916](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12916)

Normal은 NULL/NULL/false, owner first pass는 owner/NULL/false, probe는 NULL/verdict/false, 잔존 second pass는 owner/NULL/true를 넘긴다. 마지막 true는 이전 probe가 적용한 increment를 건너뛰므로 새 main first transform에 쓰면 안 된다.

```diff
@@ -12755,7 +12916,61 @@ SCAN_CODE
 heap_attrinfo_transform_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
 				 record_descriptor * new_recdes)
 {
-  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_INCLUDE_LOB);
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_INCLUDE_LOB,
+						   NULL, NULL, false);
+}
+
+/*
+ * heap_attrinfo_transform_to_disk_with_oos_owner () - normal first-pass transformation with a destination OOS heap
+ *
+ * Source representation and assignment identity stay in attr_info. Only OOS ownership is overridden;
+ * value preparation, LOB handling and pending increments use the normal first-pass contract.
+ */
+SCAN_CODE
+heap_attrinfo_transform_to_disk_with_oos_owner (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+						RECDES * old_recdes, record_descriptor * new_recdes,
+						int lob_create_flag, const OID * oos_class_oid)
+{
+  assert (oos_class_oid != NULL);
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, lob_create_flag,
+						   oos_class_oid, NULL, false);
+}
+
+/*
+ * heap_attrinfo_transform_to_disk_probe_oos () - Transform to disk with OOS demotion suppressed.
+ *
+ *   would_demote_oos(out): true if a normal transform would have demoted at least one column
+ *
+ * Note: Every column stays inline, so the resulting recdes can be larger than a slotted-page
+ * record allows; it is meant for record routing and key extraction, not for direct insertion.
+ * No OOS value chain is written. Side effects on attr_info (LOB copy, INCR/DECR application)
+ * still happen exactly once, so a subsequent heap_attrinfo_transform_to_disk_oos_class call
+ * completes the write without repeating them.
+ */
+SCAN_CODE
+heap_attrinfo_transform_to_disk_probe_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+					   RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag,
+					   bool * would_demote_oos)
+{
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, lob_create_flag,
+						   NULL, would_demote_oos, false);
+}
+
+/*
+ * heap_attrinfo_transform_to_disk_oos_class () - Transform to disk, writing OOS value chains to the
+ *                                                heap of oos_class_oid instead of attr_info->class_oid.
+ *
+ * Note: This is the second pass of a two-pass partitioned write; it assumes
+ * heap_attrinfo_transform_to_disk_probe_oos already ran on the same attr_info, so pending
+ * INCR/DECR assignments were already applied and are not applied again here.
+ */
+SCAN_CODE
+heap_attrinfo_transform_to_disk_oos_class (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+					   RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag,
+					   const OID * oos_class_oid)
+{
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, lob_create_flag,
+						   oos_class_oid, NULL, true);
 }
 
 /*
```

### H30 — Preserve non-LOB normal transformation

[src/storage/heap_file.c old:12775 / new:12990](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12990)

except_lob는 EXCLUDE_LOB와 기본 owner, suppression 없음, first-pass increment를 지정한다. 기존 계약을 유지하는 signature 변경이다.

```diff
@@ -12775,7 +12990,8 @@ SCAN_CODE
 heap_attrinfo_transform_to_disk_except_lob (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 					    RECDES * old_recdes, record_descriptor * new_recdes)
 {
-  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_EXCLUDE_LOB);
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_EXCLUDE_LOB,
+						   NULL, NULL, false);
 }
 
 /*
```

### H31 — Document and receive transform modes

[src/storage/heap_file.c old:13232 / new:13448](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13448)

Common transformer에 pointer 기반 suppression, owner override, 잔존 second-pass flag를 명시하고 정의를 선언과 맞춘다.

```diff
@@ -13232,12 +13448,17 @@ heap_attrinfo_transform_columns_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_ATT
  *   old_recdes(in): where the object's disk format is deposited
  *   new_recdes(in):
  *   lob_create_flag(in):
+ *   oos_class_oid(in): class whose heap receives the OOS value chains; NULL means attr_info->class_oid
+ *   would_demote_oos(out): non-NULL suppresses OOS demotion and reports whether it would have happened
+ *   increments_already_applied(in): true if a previous probe pass already applied INCR/DECR assignments
  *
  * Note: Transform the object represented by attr_info to disk format
  */
 static SCAN_CODE
 heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
-					  RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag)
+					  RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag,
+					  const OID * oos_class_oid, bool * would_demote_oos,
+					  bool increments_already_applied)
 {
   OR_BUF buf;
   size_t inline_size_after_oos, mvcc_extra;
```

### H32 — Derive suppression from the pointer

[src/storage/heap_file.c old:13245 / new:13466](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13466)

would_demote_oos != NULL로 suppression을 정한다. Index 변수는 잔존 second-pass premark loop용이며 early key routing 알고리즘이 아니다.

```diff
@@ -13245,6 +13466,8 @@ heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_AT
   SCAN_CODE status;
   bool is_mvcc_class, is_update;
   bool has_oos;
+  bool suppress_oos = would_demote_oos != NULL;
+  int i;
   // *INDENT-OFF*
   std::vector<heap_oos_column_plan> oos_plan (attr_info->num_values);
   std::set<int> incremented_attrids;
```

### H33 — Retain second-pass increment protection

[src/storage/heap_file.c old:13258 / new:13481](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13481)

increments_already_applied가 true면 fixed writer가 확인하는 set을 미리 채운다. 현재 owner first pass는 false를 넘긴다. 정상 writer의 buffer retry 중복 방지는 별도로 필요하다.

```diff
@@ -13258,6 +13481,19 @@ heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_AT
       return S_ERROR;
     }
 
+  if (increments_already_applied)
+    {
+      /* a probe pass already applied the pending INCR/DECR assignments to the dbvalues; pre-mark
+       * them so the column writer below does not apply them a second time */
+      for (i = 0; i < attr_info->num_values; i++)
+	{
+	  if (attr_info->values[i].do_increment != 0)
+	    {
+	      incremented_attrids.insert (i);
+	    }
+	}
+    }
+
   /* get any of the values that have not been set/read */
   if (heap_attrinfo_set_uninitialized (thread_p, &attr_info->inst_oid, old_recdes, attr_info) != NO_ERROR)
     {
```

### H34 — Forward mode into layout planning

[src/storage/heap_file.c old:13271 / new:13507](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13507)

Suppression과 verdict를 planner에 전달하고 실제 has_oos와 inline size도 받는다. 이후 OOS 쓰기는 실제 has_oos가 제어한다.

```diff
@@ -13271,8 +13507,8 @@ heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_AT
   is_mvcc_class = !mvcc_is_mvcc_disabled_class (&(attr_info->class_oid));
 
   /* determine the layout and the size */
-  if (heap_attrinfo_determine_disk_layout (attr_info, is_mvcc_class, &offset_size, &oos_plan, &has_oos,
-					   &inline_size_after_oos) != NO_ERROR)
+  if (heap_attrinfo_determine_disk_layout (attr_info, is_mvcc_class, suppress_oos, &offset_size, &oos_plan, &has_oos,
+					   would_demote_oos, &inline_size_after_oos) != NO_ERROR)
     {
       return S_ERROR;
     }
```

### H35 — Forward owner into OOS publication

[src/storage/heap_file.c old:13307 / new:13543](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13543)

기존 bigone 거절 이후 OOS insertion 경계에 owner를 전달한다. Attrinfo identity를 바꾸지 않고 locator의 선택을 연결한다.

```diff
@@ -13307,7 +13543,7 @@ heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_AT
   if (has_oos)
     {
       /* insert big columns to OOS */
-      status = heap_attrinfo_insert_to_oos (thread_p, attr_info, lob_create_flag, &oos_plan);
+      status = heap_attrinfo_insert_to_oos (thread_p, attr_info, lob_create_flag, oos_class_oid, &oos_plan);
       if (status != S_SUCCESS)
 	{
 	  return S_ERROR;
```

### H36 — Keep unit-test bridge default ownership

[src/storage/heap_file.c old:28431 / new:28667](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R28667)

기존 unit-test bridge는 새 owner 인자에 NULL을 넣어 synthetic attrinfo class의 기존 소유권을 유지한다.

```diff
@@ -28431,6 +28667,6 @@ bridge_heap_attrinfo_insert_to_oos (THREAD_ENTRY * thread_p, const OID * class_o
 
   COPY_OID (&attr_info.class_oid, class_oid);
   attr_info.num_values = 0;
-  return heap_attrinfo_insert_to_oos (thread_p, &attr_info, LOB_FLAG_INCLUDE_LOB, &oos_plan);
+  return heap_attrinfo_insert_to_oos (thread_p, &attr_info, LOB_FLAG_INCLUDE_LOB, NULL, &oos_plan);
 }
 #endif /* CUBRID_UNIT_TEST_ENABLED */
```

### H37 — Expose key and transform APIs

[src/storage/heap_file.h old:503 / new:503](https://github.com/CUBRID/cubrid/pull/7600/files#diff-97b72d043d15b8fe701fcee25ec78c565308941aa7e3d2bf0fbb37664fafa9d3R503)

Effective key와 owner first pass·probe·잔존 rebuild를 선언한다. 기존 선언은 유지된다. 내부 engine header 변경이며 client protocol 변경이 아니다.

```diff
@@ -503,10 +503,22 @@ extern int heap_attrinfo_delete_lob (THREAD_ENTRY * thread_p, RECDES * recdes, H
 extern DB_VALUE *heap_attrinfo_access (ATTR_ID attrid, HEAP_CACHE_ATTRINFO * attr_info);
 extern int heap_attrinfo_set (const OID * inst_oid, ATTR_ID attrid, DB_VALUE * attr_val,
 			      HEAP_CACHE_ATTRINFO * attr_info);
+extern int heap_attrinfo_get_effective_key (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, ATTR_ID attrid,
+					    RECDES * old_recdes, DB_VALUE * key);
 extern SCAN_CODE heap_attrinfo_transform_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 						  RECDES * old_recdes, record_descriptor * new_recdes);
+extern SCAN_CODE heap_attrinfo_transform_to_disk_with_oos_owner (THREAD_ENTRY * thread_p,
+								 HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
+								 record_descriptor * new_recdes, int lob_create_flag,
+								 const OID * oos_class_oid);
 extern SCAN_CODE heap_attrinfo_transform_to_disk_except_lob (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 							     RECDES * old_recdes, record_descriptor * new_recdes);
+extern SCAN_CODE heap_attrinfo_transform_to_disk_probe_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+							    RECDES * old_recdes, record_descriptor * new_recdes,
+							    int lob_create_flag, bool * would_demote_oos);
+extern SCAN_CODE heap_attrinfo_transform_to_disk_oos_class (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+							    RECDES * old_recdes, record_descriptor * new_recdes,
+							    int lob_create_flag, const OID * oos_class_oid);
 
 extern DB_VALUE *heap_attrinfo_generate_key (THREAD_ENTRY * thread_p, int n_atts, int *att_ids, int *atts_prefix_length,
 					     HEAP_CACHE_ATTRINFO * attr_info, RECDES * recdes, DB_VALUE * dbvalue,
```

### H38 — Declare UPDATE's expected owner

[src/transaction/locator_sr.c old:152 / new:152](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R152)

Private UPDATE force 선언에 expected destination을 추가한다. Caller마다 검증할 early decision이 있는지 명시해야 한다.

```diff
@@ -152,7 +152,7 @@ static int locator_update_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * cla
 				 HEAP_SCANCACHE * scan_cache, int *force_count, bool not_check_fk,
 				 REPL_INFO_TYPE repl_info_type, int pruning_type, PRUNING_CONTEXT * pcontext,
 				 MVCC_REEV_DATA * mvcc_reev_data, UPDATE_INPLACE_STYLE force_in_place,
-				 bool need_locking);
+				 bool need_locking, const OID * expected_class_oid);
 static int locator_move_record (THREAD_ENTRY * thread_p, HFID * old_hfid, OID * old_class_oid, OID * obj_oid,
 				OID * new_class_oid, HFID * new_class_hfid, RECDES * recdes,
 				HEAP_SCANCACHE * scan_cache, int op_type, int has_index, int *force_count,
```

### H39 — Name the INSERT implementation

[src/transaction/locator_sr.c old:4924 / new:4924](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R4924)

새 private internal 이름에 맞춰 주석 이름을 바꾼다. 동작 변화는 인접 signature와 agreement check에 있다.

```diff
@@ -4924,7 +4924,7 @@ error3:
 }
 
 /*
- * locator_insert_force () - Insert the given object on this heap
+ * locator_insert_force_internal () - Insert the given object on this heap
  *
  * return: NO_ERROR if all OK, ER_ status otherwise
  *
```

### H40 — Introduce private INSERT with expected destination

[src/transaction/locator_sr.c old:4944 / new:4944](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R4944)

Expected class를 받는 INSERT internal을 만들고 H42에서 기존 public API를 유지한다. 관련 없는 caller에게 early destination 생성을 강요하지 않는다.

```diff
@@ -4944,16 +4944,17 @@ error3:
  *   pcontext(in): partition pruning context
  *   func_preds(in): cached function index expressions
  *   force_in_place:
+ *   expected_class_oid(in): optional early destination; final routing must agree before inserting
  *
  * Note: The given object is inserted on this heap and all appropriate
  *              index entries are inserted.
  */
-int
-locator_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * recdes, int has_index,
-		      int op_type, HEAP_SCANCACHE * scan_cache, int *force_count, int pruning_type,
-		      PRUNING_CONTEXT * pcontext, FUNC_PRED_UNPACK_INFO * func_preds,
-		      UPDATE_INPLACE_STYLE force_in_place, PGBUF_WATCHER * home_hint_p, bool has_BU_lock,
-		      bool dont_check_fk, bool use_bulk_logging)
+static int
+locator_insert_force_internal (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * recdes,
+			       int has_index, int op_type, HEAP_SCANCACHE * scan_cache, int *force_count,
+			       int pruning_type, PRUNING_CONTEXT * pcontext, FUNC_PRED_UNPACK_INFO * func_preds,
+			       UPDATE_INPLACE_STYLE force_in_place, PGBUF_WATCHER * home_hint_p, bool has_BU_lock,
+			       bool dont_check_fk, bool use_bulk_logging, const OID * expected_class_oid)
 {
 #if 0				/* TODO - dead code; do not delete me */
   OID rep_dir = { NULL_PAGEID, NULL_SLOTID, NULL_VOLID };
```

### H41 — Reject INSERT destination disagreement

[src/transaction/locator_sr.c old:4992 / new:4993](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R4993)

최종 record pruning 뒤 early owner와 비교한다. 다르면 기존 error 경로로 ER_GENERIC_ERROR를 반환해 이후 subclass/heap insert로 가지 않는다. 준비한 chain을 둔 채 record만 다른 곳으로 보내지 않는다.

```diff
@@ -4992,6 +4993,14 @@ locator_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID
 	{
 	  goto error2;
 	}
+      if (expected_class_oid != NULL && !OID_EQ (expected_class_oid, &real_class_oid))
+	{
+	  /* OOS chains may already belong to the early destination. Never redirect them to another heap.
+	   * Return through the ordinary statement-error path so logged OOS inserts are rolled back. */
+	  er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);
+	  error_code = ER_GENERIC_ERROR;
+	  goto error2;
+	}
       if (!OID_ISNULL (&superclass_oid))
 	{
 	  granted = lock_subclass (thread_p, &real_class_oid, &superclass_oid, IX_LOCK, LK_UNCOND_LOCK);
```

### H42 — Preserve legacy INSERT callers

[src/transaction/locator_sr.c old:5283 / new:5292](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R5292)

기존 public locator_insert_force는 모든 인자와 NULL expected owner를 넘긴다. Main attribute write만 guarded internal을 직접 호출한다.

```diff
@@ -5283,6 +5292,21 @@ error2:
   return error_code;
 }
 
+/*
+ * locator_insert_force () - retain the existing force interface for callers without an early destination
+ */
+int
+locator_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * recdes, int has_index,
+		      int op_type, HEAP_SCANCACHE * scan_cache, int *force_count, int pruning_type,
+		      PRUNING_CONTEXT * pcontext, FUNC_PRED_UNPACK_INFO * func_preds,
+		      UPDATE_INPLACE_STYLE force_in_place, PGBUF_WATCHER * home_hint_p, bool has_BU_lock,
+		      bool dont_check_fk, bool use_bulk_logging)
+{
+  return locator_insert_force_internal (thread_p, hfid, class_oid, oid, recdes, has_index, op_type, scan_cache,
+					force_count, pruning_type, pcontext, func_preds, force_in_place, home_hint_p,
+					has_BU_lock, dont_check_fk, use_bulk_logging, NULL);
+}
+
 int
 locator_oos_insert_force (THREAD_ENTRY * thread_p, OID * class_oid, RECDES * recdes)
 {
```

### H43 — Document UPDATE agreement

[src/transaction/locator_sr.c old:5457 / new:5481](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R5481)

Optional early class와 final routing의 일치를 이후 row heap/index 변경 전에 확인한다고 문서화한다. 비교 계약이며 transaction abort 구현은 아니다.

```diff
@@ -5457,6 +5481,7 @@ locator_move_record (THREAD_ENTRY * thread_p, HFID * old_hfid, OID * old_class_o
  *			 and the update style will be decided in this function.
  *			 Otherwise the update of the instance will be made in
  *			 place and according to provided style.
+ *   expected_class_oid(in): optional early destination; final routing must agree before heap/index mutation
  *
  * Note: The given object is updated on this heap and all appropriate
  *              index entries are updated.
```

### H44 — Receive UPDATE agreement input

[src/transaction/locator_sr.c old:5466 / new:5491](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R5491)

Private 정의에 expected_class_oid를 추가한다. H45가 final routing 후 사용하며 다른 caller는 NULL을 넘긴다.

```diff
@@ -5466,7 +5491,7 @@ locator_update_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID
 		      RECDES * recdes, int has_index, ATTR_ID * att_id, int n_att_id, int op_type,
 		      HEAP_SCANCACHE * scan_cache, int *force_count, bool not_check_fk, REPL_INFO_TYPE repl_info_type,
 		      int pruning_type, PRUNING_CONTEXT * pcontext, MVCC_REEV_DATA * mvcc_reev_data,
-		      UPDATE_INPLACE_STYLE force_in_place, bool need_locking)
+		      UPDATE_INPLACE_STYLE force_in_place, bool need_locking, const OID * expected_class_oid)
 {
   OID rep_dir = { NULL_PAGEID, NULL_SLOTID, NULL_VOLID };
   char *rep_dir_offset;
```

### H45 — Reject UPDATE destination disagreement

[src/transaction/locator_sr.c old:5993 / new:6018](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R6018)

Source class 재확인과 partition 이동 전에 final class와 early OOS owner를 비교한다. 실패는 기존 error cleanup으로 가며 logged OOS 작업은 caller rollback에 의존한다.

```diff
@@ -5993,6 +6018,14 @@ locator_update_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID
 	      goto error;
 	    }
 
+	  /* Final record routing must agree with the heap chosen for OOS preparation. */
+	  if (expected_class_oid != NULL && !OID_EQ (&real_class_oid, expected_class_oid))
+	    {
+	      er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);
+	      error_code = ER_GENERIC_ERROR;
+	      goto error;
+	    }
+
 	  /* make sure we use the correct class oid - we could be dealing with a classoid resulted from a unique btid
 	   * pruning */
 	  if (heap_get_class_oid (thread_p, oid, class_oid) != S_SUCCESS)
```

### H46 — Adapt multi-update force

[src/transaction/locator_sr.c old:6749 / new:6782](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R6782)

기존 nonpartitioned multi-update caller에 NULL expected class를 추가한다. 인증할 early attrinfo routing 결과가 없다.

```diff
@@ -6749,7 +6782,7 @@ locator_force_for_multi_update (THREAD_ENTRY * thread_p, LC_COPYAREA * force_are
 	  error_code =
 	    locator_update_force (thread_p, &obj->hfid, &obj->class_oid, &obj->oid, NULL, &recdes,
 				  has_index, NULL, 0, MULTI_ROW_UPDATE, &scan_cache, &force_count, false, repl_info,
-				  DB_NOT_PARTITIONED_CLASS, NULL, NULL, UPDATE_INPLACE_NONE, true);
+				  DB_NOT_PARTITIONED_CLASS, NULL, NULL, UPDATE_INPLACE_NONE, true, NULL);
 	  if (error_code != NO_ERROR)
 	    {
 	      /*
```

### H47 — Adapt replication force

[src/transaction/locator_sr.c old:7139 / new:7172](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7172)

Replication의 기존 record-based UPDATE 호출에 NULL을 추가한다. Replication에 effective-key 준비를 새로 도입한 것이 아니다.

```diff
@@ -7139,7 +7172,8 @@ xlocator_repl_force (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area, LC_COPYA
 	      error_code =
 		locator_update_force (thread_p, &obj->hfid, &obj->class_oid, &obj->oid, NULL, &recdes, has_index,
 				      NULL, 0, SINGLE_ROW_UPDATE, force_scancache, &force_count, false,
-				      REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true);
+				      REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true,
+				      NULL);
 
 	      if (error_code == NO_ERROR)
 		{
```

### H48 — Adapt generic force

[src/transaction/locator_sr.c old:7349 / new:7383](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7383)

xlocator_force의 기존 UPDATE에 NULL을 추가한다. 이미 직렬화한 record를 주는 caller의 동작을 유지한다.

```diff
@@ -7349,7 +7383,7 @@ xlocator_force (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area, int num_ignor
 	  error_code =
 	    locator_update_force (thread_p, &obj->hfid, &obj->class_oid, &obj->oid, NULL, &recdes,
 				  has_index, NULL, 0, SINGLE_ROW_UPDATE, force_scancache, &force_count, false,
-				  REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true);
+				  REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true, NULL);
 
 	  if (error_code == NO_ERROR)
 	    {
```

### H49 — Name the internal copy-area builder

[src/transaction/locator_sr.c old:7461 / new:7495](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7495)

Implementation 주석 이름을 internal로 바꾸고 public wrapper를 아래에 다시 둔다. Allocation 소유권은 기존 copy-area API를 따른다.

```diff
@@ -7461,7 +7495,7 @@ error:
 }
 
 /*
- * locator_allocate_copy_area_by_attr_info () - Transforms attribute
+ * locator_allocate_copy_area_by_attr_info_internal () - Transforms attribute
  *              information into a disk representation and allocates a
  *              LC_COPYAREA big enough to fit the representation
  *
```

### H50 — Add first-pass owner mode

[src/transaction/locator_sr.c old:7475 / new:7509](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7509)

Builder가 owner, probe verdict, oos_first_pass를 받는다. Private flag로 실제 첫 변환과 잔존 probe 후 rebuild 계약을 구분한다.

```diff
@@ -7475,12 +7509,21 @@ error:
  *   copyarea_length_hint(in): An estimated size for the LC_COPYAREA or -1 if
  *                             an estimated size is not known.
  *   lob_create_flag(in) :
+ *   oos_class_oid(in): class whose heap receives the OOS value chains; NULL means
+ *                      attr_info->class_oid. A partitioned write passes the pruned partition.
+ *   probe_would_demote_oos(out): when non-NULL, suppress OOS demotion (build a fully-inline
+ *                                image, write no OOS value chain) and report whether a normal
+ *                                transform would have demoted a column.
+ *   oos_first_pass(in): use normal preparation with the selected OOS owner, without a preceding probe
  *
  * Note: The allocated should be freed by using locator_free_copy_area ()
  */
-LC_COPYAREA *
-locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
-					 RECDES * new_recdes, const int copyarea_length_hint, int lob_create_flag)
+static LC_COPYAREA *
+locator_allocate_copy_area_by_attr_info_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+						  RECDES * old_recdes, RECDES * new_recdes,
+						  const int copyarea_length_hint, int lob_create_flag,
+						  const OID * oos_class_oid, bool * probe_would_demote_oos,
+						  bool oos_first_pass)
 {
   LC_COPYAREA *copyarea = NULL;
   int copyarea_length = copyarea_length_hint <= 0 ? DB_PAGESIZE : copyarea_length_hint;
```

### H51 — Dispatch copy-area transformation

[src/transaction/locator_sr.c old:7504 / new:7547](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7547)

분기 우선순위는 owner first pass → probe → 잔존 owner rebuild → except LOB → normal이다. First pass는 owner 존재와 probe output 부재를 assert한다. 아래 buffer 성장·해제는 기존대로이며 mode 선택 자체가 rollback은 아니다.

```diff
@@ -7504,7 +7547,23 @@ locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATT
   new_recdes->data = copyarea->mem;
   new_recdes->area_size = copyarea->length;
 
-  if (lob_create_flag == LOB_FLAG_EXCLUDE_LOB)
+  if (oos_first_pass)
+    {
+      assert (oos_class_oid != NULL && probe_would_demote_oos == NULL);
+      scan = heap_attrinfo_transform_to_disk_with_oos_owner (thread_p, attr_info, old_recdes, &build_record,
+							     lob_create_flag, oos_class_oid);
+    }
+  else if (probe_would_demote_oos != NULL)
+    {
+      scan = heap_attrinfo_transform_to_disk_probe_oos (thread_p, attr_info, old_recdes, &build_record,
+							lob_create_flag, probe_would_demote_oos);
+    }
+  else if (oos_class_oid != NULL)
+    {
+      scan = heap_attrinfo_transform_to_disk_oos_class (thread_p, attr_info, old_recdes, &build_record,
+							lob_create_flag, oos_class_oid);
+    }
+  else if (lob_create_flag == LOB_FLAG_EXCLUDE_LOB)
     {
       scan = heap_attrinfo_transform_to_disk_except_lob (thread_p, attr_info, old_recdes, &build_record);
     }
```

### H52 — Expose normal/probe/rebuild wrapper

[src/transaction/locator_sr.c old:7545 / new:7604](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7604)

Public builder는 확장 인자와 oos_first_pass=false를 넘긴다. 새 main write는 private owner first-pass mode를 직접 사용한다.

```diff
@@ -7545,6 +7604,19 @@ locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATT
   return copyarea;
 }
 
+/*
+ * locator_allocate_copy_area_by_attr_info () - preserve the existing normal/probe/rebuild interface
+ */
+LC_COPYAREA *
+locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
+					 RECDES * new_recdes, const int copyarea_length_hint, int lob_create_flag,
+					 const OID * oos_class_oid, bool * probe_would_demote_oos)
+{
+  return locator_allocate_copy_area_by_attr_info_internal (thread_p, attr_info, old_recdes, new_recdes,
+							   copyarea_length_hint, lob_create_flag, oos_class_oid,
+							   probe_would_demote_oos, false);
+}
+
 /*
  * locator_attribute_info_force () - Force an object represented by attribute
  *                                   information structure
```

### H53 — Keep destination independent

[src/transaction/locator_sr.c old:7595 / new:7667](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7667)

write_destination을 NULL로 초기화하여 nonpartitioned 호출은 expected destination이 없게 한다. 기존 source class/HFID 복사본은 유지한다.

```diff
@@ -7595,6 +7667,7 @@ locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID *
   int error_code = NO_ERROR;
   HFID class_hfid;
   OID class_oid;
+  OID write_destination = OID_INITIALIZER;
   MVCC_SNAPSHOT *saved_mvcc_snapshot = NULL;
 
   /*
```

### H54 — Route before the first full transform

[src/transaction/locator_sr.c old:7692 / new:7765](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7765)

Partitioned write는 destination 식별자를 초기화하고 INSERT/UPDATE key routing을 선택하며 오류면 중단한다. 성공 뒤 INCLUDE_LOB·선택 owner·oos_first_pass=true로 row를 한 번 준비한다. Source class는 final 검증과 이동을 위해 유지하고 nonpartitioned는 기본 mode를 명시한다.

```diff
@@ -7692,9 +7765,40 @@ locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID *
     case LC_FLUSH_INSERT:
     case LC_FLUSH_INSERT_PRUNE:
     case LC_FLUSH_INSERT_PRUNE_VERIFY:
-      copyarea =
-	locator_allocate_copy_area_by_attr_info (thread_p, attr_info, old_recdes, &new_recdes, -1,
-						 LOB_FLAG_INCLUDE_LOB);
+      if (pruning_type != DB_NOT_PARTITIONED_CLASS)
+	{
+	  HFID pruned_hfid;
+
+	  COPY_OID (&write_destination, &class_oid);
+	  HFID_COPY (&pruned_hfid, &class_hfid);
+	  if (LC_IS_FLUSH_INSERT (operation))
+	    {
+	      error_code = partition_prune_insert_by_attrinfo (thread_p, &class_oid, attr_info, pcontext, pruning_type,
+							       &write_destination, &pruned_hfid, NULL);
+	    }
+	  else
+	    {
+	      assert (LC_IS_FLUSH_UPDATE (operation));
+	      error_code = partition_prune_update_by_attrinfo (thread_p, &class_oid, attr_info, old_recdes, pcontext,
+							       pruning_type, &write_destination, &pruned_hfid, NULL);
+	    }
+	  if (error_code != NO_ERROR)
+	    {
+	      break;
+	    }
+
+	  /* Prepare the full row once, writing OOS values to the selected heap. Keep the source class
+	   * unchanged: final force still performs routing, validation, representation patching and movement. */
+	  copyarea = locator_allocate_copy_area_by_attr_info_internal (thread_p, attr_info, old_recdes, &new_recdes, -1,
+								       LOB_FLAG_INCLUDE_LOB, &write_destination, NULL,
+								       true);
+	}
+      else
+	{
+	  copyarea =
+	    locator_allocate_copy_area_by_attr_info (thread_p, attr_info, old_recdes, &new_recdes, -1,
+						     LOB_FLAG_INCLUDE_LOB, NULL, NULL);
+	}
       if (copyarea == NULL)
 	{
 	  error_code = ER_FAILED;
```

### H55 — Carry expected owner into INSERT force

[src/transaction/locator_sr.c old:7705 / new:7809](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7809)

Private INSERT variant에 선택 destination을 넘긴다. NULL이면 expected owner도 NULL이다. 기존 기본값 use_bulk_logging=false와 나머지 flag를 명시한다.

```diff
@@ -7705,9 +7809,10 @@ locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID *
       if (LC_IS_FLUSH_INSERT (operation))
 	{
 	  error_code =
-	    locator_insert_force (thread_p, &class_hfid, &class_oid, oid, &new_recdes, true, op_type, scan_cache,
-				  force_count, pruning_type, pcontext, func_preds, UPDATE_INPLACE_NONE, NULL, false,
-				  false);
+	    locator_insert_force_internal (thread_p, &class_hfid, &class_oid, oid, &new_recdes, true, op_type,
+					   scan_cache, force_count, pruning_type, pcontext, func_preds,
+					   UPDATE_INPLACE_NONE, NULL, false, false, false,
+					   OID_ISNULL (&write_destination) ? NULL : &write_destination);
 	}
       else
 	{
```

### H56 — Carry expected owner into UPDATE force

[src/transaction/locator_sr.c old:7725 / new:7830](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7830)

선택 destination을 final UPDATE에도 전달한다. Key가 유지되든 이동하든 변환 전에 고른 OOS owner와 일치해야 한다.

```diff
@@ -7725,7 +7830,8 @@ locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID *
 	  error_code =
 	    locator_update_force (thread_p, &class_hfid, &class_oid, oid, old_recdes, &new_recdes, has_index,
 				  att_id, n_att_id, op_type, scan_cache, force_count, not_check_fk, repl_info,
-				  pruning_type, pcontext, mvcc_reev_data, force_update_inplace, need_locking);
+				  pruning_type, pcontext, mvcc_reev_data, force_update_inplace, need_locking,
+				  OID_ISNULL (&write_destination) ? NULL : &write_destination);
 	  if (error_code != NO_ERROR)
 	    {
 	      ASSERT_ERROR ();
```

### H57 — Retain reevaluation defaults

[src/transaction/locator_sr.c old:13781 / new:13887](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R13887)

MVCC reevaluation 호출에 NULL owner와 NULL probe를 추가한다. Signature 변경이며 새 standalone 테스트가 모든 동시 reevaluation 경로를 검증했다는 의미는 아니다.

```diff
@@ -13781,7 +13887,7 @@ locator_mvcc_reev_cond_assigns (THREAD_ENTRY * thread_p, OID * class_oid, const
 	}
       mvcc_reev_data->copyarea =
 	locator_allocate_copy_area_by_attr_info (thread_p, mvcc_reev_data->curr_attrinfo, recdes,
-						 mvcc_reev_data->new_recdes, -1, LOB_FLAG_INCLUDE_LOB);
+						 mvcc_reev_data->new_recdes, -1, LOB_FLAG_INCLUDE_LOB, NULL, NULL);
       if (mvcc_reev_data->copyarea == NULL)
 	{
 	  ev_res = V_ERROR;
```

### H58 — Update the copy-area declaration

[src/transaction/locator_sr.h old:83 / new:83](https://github.com/CUBRID/cubrid/pull/7600/files#diff-5195f47502d54541ddfe3f6dc3c658a3c8ea02c5cf39348d8775a4f46c7099d7R83)

모든 caller와 맞게 owner·suppression output을 선언한다. Private first-pass flag는 이 public engine 선언에 노출하지 않는다.

```diff
@@ -83,7 +83,8 @@ extern int locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * h
 					 bool need_locking);
 extern LC_COPYAREA *locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 							     RECDES * old_recdes, RECDES * new_recdes,
-							     const int copyarea_length_hint, int lob_create_flag);
+							     const int copyarea_length_hint, int lob_create_flag,
+							     const OID * oos_class_oid, bool * probe_would_demote_oos);
 extern int locator_other_insert_delete (THREAD_ENTRY * thread_p, HFID * hfid, OID * oid, BTID * btid,
 					bool btid_dup_key_locked, HFID * newhfid, OID * newoid,
 					HEAP_CACHE_ATTRINFO * attr_info, HEAP_SCANCACHE * scan_cache, int *force_count,
```

### H59 — Allow diagnostic-heavy test execution

[unit_tests/oos/sql/CMakeLists.txt old:54 / new:54](https://github.com/CUBRID/cubrid/pull/7600/files#diff-3275cf29164ab3fd22b8f905a3bf3fb643804e52b44926cf725e5897598cf408R54)

test_oos_sql_show의 timeout만 300초로 바꾼다. Fault injection과 routing 오류가 debug stack을 수집하며 fixture 조건과 직렬 실행은 유지된다.

```diff
@@ -54,3 +54,6 @@ set_tests_properties(
   test_oos_sql_visible_version
   PROPERTIES FIXTURES_REQUIRED OOS_DB RUN_SERIAL TRUE TIMEOUT 30
 )
+
+# Routing rejection and injected cleanup failures collect diagnostic stacks in debug builds.
+set_tests_properties(test_oos_sql_show PROPERTIES TIMEOUT 300)
```

### H60 — Provide direct-interface test infrastructure

[unit_tests/oos/sql/test_oos_sql_show.cpp old:21 / new:21](https://github.com/CUBRID/cubrid/pull/7600/files#diff-7fdae0e381b6e45764169b71c10fbf166556914aac1c9afb4e4ba9aab483aa38R21)

Routing·locator·OOS·logging·record·primitive API와 string을 include하고 기존 failure hook을 선언한다. scoped_sa_server는 db_on_server를 증감해 SA direct 호출의 allocator를 맞춘다. SERVER_MODE process를 시작하지는 않는다.

```diff
@@ -21,11 +21,36 @@
  */
 
 #include <algorithm>
+#include <string>
 
+#include "partition_sr.h"
+#include "locator_sr.h"
+#include "heap_oos.hpp"
+#include "log_impl.h"
+#include "record_descriptor.hpp"
+#include "object_primitive.h"
 #include "test_oos_sql_common.hpp"
 
+// Direct server interfaces in SA must use server allocation, just like network_interface_cl.c.
+extern unsigned int db_on_server;
+void bridge_heap_attrinfo_fail_after_oos_publication_reset_once ();
+void bridge_heap_attrinfo_disarm_publication_reset_failure ();
+
 namespace
 {
+  class scoped_sa_server
+  {
+    public:
+      scoped_sa_server ()
+      {
+	db_on_server++;
+      }
+      ~scoped_sa_server ()
+      {
+	db_on_server--;
+      }
+  };
+
   enum show_heap_oos_column
   {
     COL_TABLE_NAME = 0,
```

### H61 — Assert logical values and physical owners

[unit_tests/oos/sql/test_oos_sql_show.cpp old:154 / new:179](https://github.com/CUBRID/cubrid/pull/7600/files#diff-7fdae0e381b6e45764169b71c10fbf166556914aac1c9afb4e4ba9aab483aa38R179)

DB_VALUE 정리를 포함한 문자열 추출, schema prefix 제거, SQL count와 OOS file/chunk 검사 helper를 추가한다. 물리 helper는 결과 한 행을 확인하고 닫는다. 논리·물리 oracle을 나눠 SELECT만으로 놓친 원래 버그를 잡는다.

```diff
@@ -154,6 +179,64 @@ namespace
     db_value_clear (&val);
     return rc;
   }
+
+  static int
+  get_string_column (DB_QUERY_RESULT *result, int column, std::string *out_val)
+  {
+    DB_VALUE val;
+    int rc;
+
+    db_make_null (&val);
+    rc = db_query_get_tuple_value (result, column, &val);
+    if (rc == NO_ERROR)
+      {
+	const char *str = db_get_string (&val);
+	if (str == nullptr)
+	  {
+	    rc = ER_FAILED;
+	  }
+	else
+	  {
+	    *out_val = str;
+	  }
+      }
+
+    db_value_clear (&val);
+    return rc;
+  }
+
+  static std::string
+  unqualified_table_name (const std::string &table_name)
+  {
+    std::string::size_type separator = table_name.rfind ('.');
+    return separator == std::string::npos ? table_name : table_name.substr (separator + 1);
+  }
+
+  static void
+  expect_sql_count (const char *sql, int expected)
+  {
+    SCOPED_TRACE (sql);
+    int count = -1;
+    ASSERT_EQ (fetch_single_int (sql, &count), NO_ERROR);
+    EXPECT_EQ (count, expected);
+  }
+
+  static void
+  expect_oos_records (const char *table, int has_file, int expected_records)
+  {
+    SCOPED_TRACE (table);
+    std::string sql = std::string ("SHOW HEAP OOS OF ") + table;
+    DB_QUERY_RESULT *result = nullptr;
+    ASSERT_EQ (show_heap_oos_query (sql.c_str (), &result), NO_ERROR);
+    int actual_has_file = -1;
+    int actual_records = -1;
+    EXPECT_EQ (get_int_column (result, COL_HAS_OOS_FILE, &actual_has_file), NO_ERROR);
+    EXPECT_EQ (get_int_column (result, COL_OOS_NUM_RECS, &actual_records), NO_ERROR);
+    EXPECT_EQ (actual_has_file, has_file);
+    EXPECT_EQ (actual_records, expected_records);
+    EXPECT_EQ (db_query_next_tuple (result), DB_CURSOR_END);
+    db_query_end (result);
+  }
 }
 
 class OosSqlShow : public ::testing::Test
```

### H62 — Add 28 discriminating SQL tests

[unit_tests/oos/sql/test_oos_sql_show.cpp old:351 / new:434](https://github.com/CUBRID/cubrid/pull/7600/files#diff-7fdae0e381b6e45764169b71c10fbf166556914aac1c9afb4e4ba9aab483aa38R434)

이 큰 hunk는 28개 새 테스트로 구성된다. 아래 test catalog가 각 함수와 구별력 있는 assertion·독립 reference·한계를 연결한다. 기존 SHOW 테스트 4개는 유지된다.

```diff
@@ -351,6 +434,1235 @@ TEST_F (OosSqlShow, ShowAllHeapOosReportsPartitionRows)
   db_query_end (result);
 }
 
+TEST_F (OosSqlShow, PartitionedForceOutlineStoresOosInPrunedHeap)
+{
+  int rc = exec_sql ("CREATE TABLE t_oos_show_part ("
+		     "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		     "PARTITION BY RANGE (id) ("
+		     "PARTITION p0 VALUES LESS THAN (10), "
+		     "PARTITION p1 VALUES LESS THAN MAXVALUE)");
+  ASSERT_GE (rc, 0);
+  rc = exec_sql ("INSERT INTO t_oos_show_part VALUES (1, REPEAT(X'EE', 64))");
+  ASSERT_GE (rc, 0);
+  db_commit_transaction ();
+
+  int value_matches = 0;
+  rc = fetch_single_int ("SELECT data_col = CAST(REPEAT(X'EE', 64) AS BIT VARYING) "
+			 "FROM t_oos_show_part WHERE id = 1", &value_matches);
+  ASSERT_EQ (rc, NO_ERROR);
+  EXPECT_EQ (value_matches, 1);
+
+  DB_QUERY_RESULT *result = nullptr;
+  rc = show_heap_oos_query ("SHOW ALL HEAP OOS OF t_oos_show_part", &result);
+  ASSERT_EQ (rc, NO_ERROR);
+  ASSERT_NE (result, nullptr);
+
+  bool saw_root = false;
+  bool saw_p0 = false;
+  bool saw_p1 = false;
+  do
+    {
+      std::string table_name;
+      int has_oos = -1;
+      int num_recs = -1;
+
+      rc = get_string_column (result, COL_TABLE_NAME, &table_name);
+      ASSERT_EQ (rc, NO_ERROR);
+      rc = get_int_column (result, COL_HAS_OOS_FILE, &has_oos);
+      ASSERT_EQ (rc, NO_ERROR);
+      rc = get_int_column (result, COL_OOS_NUM_RECS, &num_recs);
+      ASSERT_EQ (rc, NO_ERROR);
+
+      table_name = unqualified_table_name (table_name);
+      if (table_name == "t_oos_show_part")
+	{
+	  saw_root = true;
+	  EXPECT_EQ (has_oos, 0);
+	  EXPECT_EQ (num_recs, 0);
+	}
+      else if (table_name == "t_oos_show_part__p__p0")
+	{
+	  saw_p0 = true;
+	  EXPECT_EQ (has_oos, 1);
+	  EXPECT_EQ (num_recs, 1);
+	}
+      else if (table_name == "t_oos_show_part__p__p1")
+	{
+	  saw_p1 = true;
+	  EXPECT_EQ (has_oos, 0);
+	  EXPECT_EQ (num_recs, 0);
+	}
+    }
+  while ((rc = db_query_next_tuple (result)) == DB_CURSOR_SUCCESS);
+
+  EXPECT_EQ (rc, DB_CURSOR_END);
+  EXPECT_TRUE (saw_root);
+  EXPECT_TRUE (saw_p0);
+  EXPECT_TRUE (saw_p1);
+
+  db_query_end (result);
+}
+
+TEST_F (OosSqlShow, PartitionRangeBoundaryAndNullOwnership)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id) ("
+		       "PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  // Alternating destinations and NULL in one statement exercise reusable routing state.
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(10, REPEAT(X'AA', 64)), (9, REPEAT(X'BB', 64)), "
+		       "(11, REPEAT(X'CC', 64)), (NULL, REPEAT(X'DD', 64))"), 4);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 4);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "(id = 9 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)) OR "
+		    "(id IS NULL AND data_col = CAST(REPEAT(X'DD', 64) AS BIT VARYING))", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id = 10 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)) OR "
+		    "(id = 11 AND data_col = CAST(REPEAT(X'CC', 64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionListExpressionAndFailedBatchOwnership)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY LIST (ABS(id)) ("
+		       "PARTITION p0 VALUES IN (1, 3), "
+		       "PARTITION p1 VALUES IN (2, NULL))"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(-1, REPEAT(X'AA', 64)), (-2, REPEAT(X'BB', 64)), "
+		       "(-3, REPEAT(X'CC', 64)), (NULL, REPEAT(X'DD', 64))"), 4);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  // A valid first row followed by a missing destination must leave no durable partial write.
+  EXPECT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(-1, REPEAT(X'EE', 64)), (4, REPEAT(X'FF', 64))"), ER_PARTITION_NOT_EXIST);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 4);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (-2, REPEAT(X'EE', 64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 5);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "(id = -1 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)) OR "
+		    "(id = -3 AND data_col = CAST(REPEAT(X'CC', 64) AS BIT VARYING))", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id = -2 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)) OR "
+		    "(id IS NULL AND data_col = CAST(REPEAT(X'DD', 64) AS BIT VARYING)) OR "
+		    "(id = -2 AND data_col = CAST(REPEAT(X'EE', 64) AS BIT VARYING))", 3);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 3);
+}
+
+TEST_F (OosSqlShow, PartitionHashNullOwnership)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY HASH (id) PARTITIONS 2"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(1, REPEAT(X'AA', 64)), (0, REPEAT(X'BB', 64)), "
+		       "(1, REPEAT(X'CC', 64)), (NULL, REPEAT(X'DD', 64))"), 4);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 4);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "(id = 0 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)) OR "
+		    "(id IS NULL AND data_col = CAST(REPEAT(X'DD', 64) AS BIT VARYING))", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id = 1 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)) OR "
+		    "(id = 1 AND data_col = CAST(REPEAT(X'CC', 64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionRangeExpressionValidationAndMovement)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id + 1) ("
+		       "PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN (20))"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part__p__p0 VALUES (8, REPEAT(X'AA', 64))"), 1);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (9, REPEAT(X'BB', 64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  EXPECT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (19, REPEAT(X'CC', 64))"), ER_PARTITION_NOT_EXIST);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  EXPECT_EQ (exec_sql ("INSERT INTO t_oos_show_part__p__p0 VALUES (9, REPEAT(X'CC', 64))"),
+	     ER_INVALID_DATA_FOR_PARTITION);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  EXPECT_EQ (exec_sql ("UPDATE t_oos_show_part__p__p0 SET id = 9"), ER_INVALID_DATA_FOR_PARTITION);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  EXPECT_EQ (exec_sql ("UPDATE t_oos_show_part SET id = 19 WHERE id = 8"), ER_PARTITION_NOT_EXIST);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "id = 8 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "id = 9 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+
+  // Root-targeted UPDATE may move a row; the sibling row stays in its existing heap.
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id = id + 1"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0", 0);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id = 9 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)) OR "
+		    "(id = 10 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionListRejectsNullWithoutDestination)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY LIST (id) ("
+		       "PARTITION p0 VALUES IN (1), PARTITION p1 VALUES IN (2))"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  EXPECT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (NULL, REPEAT(X'AA', 64))"),
+	     ER_PARTITION_NOT_EXIST);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (2, REPEAT(X'BB', 64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "id = 2 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+}
+
+TEST_F (OosSqlShow, PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT PRIMARY KEY, counter INT DEFAULT 0, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) "
+		       "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES(11,0,REPEAT(X'AA',64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  ASSERT_EQ (exec_sql ("SELECT INCR(counter) FROM t_oos_show_part WHERE id=11"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=11 AND counter=1", 1);
+  ASSERT_GE (exec_sql ("INSERT INTO t_oos_show_part VALUES(11,0,REPEAT(X'BB',64)) "
+		       "ON DUPLICATE KEY UPDATE id=9,data_col=REPEAT(X'CC',64)"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=9 AND counter=1 "
+		    "AND data_col=CAST(REPEAT(X'CC',64) AS BIT VARYING)", 1);
+  ASSERT_GE (exec_sql ("REPLACE INTO t_oos_show_part VALUES(9,2,REPEAT(X'DD',64))"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=9 AND counter=2 "
+		    "AND data_col=CAST(REPEAT(X'DD',64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+}
+
+TEST_F (OosSqlShow, PartitionUpdateStringDomains)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(128) COLLATE utf8_en_ci, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY LIST(id) "
+		       "(PARTITION p0 VALUES IN('alpha'), PARTITION p1 VALUES IN('beta'))"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES('ALPHA',REPEAT(X'AA',64))"), 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'BB',64)"), 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id='BETA'"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id='beta'", 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+  ASSERT_GE (exec_sql ("DROP TABLE t_oos_show_part"), 0);
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(4000), "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(CHAR_LENGTH(id)) "
+		       "(PARTITION p0 VALUES LESS THAN(3000), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES(REPEAT('a',2999),REPEAT(X'AA',64))"), 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'BB',64)"), 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=REPEAT('b',3000)"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=REPEAT('b',3000) "
+		    "AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  // The compressed DEFAULT-policy key remains inline; only the forced VARBIT owns an OOS chunk.
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+}
+
+TEST_F (OosSqlShow, PartitionUpdateLegalKeysAndNullMovement)
+{
+  const char *columns[] =
+  {
+    "SMALLINT DEFAULT 11", "INTEGER DEFAULT 11", "BIGINT DEFAULT 2147483648",
+    "DATE DEFAULT DATE '2024-02-29'", "TIME DEFAULT TIME '12:34:56'",
+    "TIMESTAMP DEFAULT TIMESTAMP '2024-02-29 12:34:56'",
+    "TIMESTAMPTZ DEFAULT TIMESTAMPTZ '2024-02-29 12:34:56 +09:00'",
+    "TIMESTAMPLTZ DEFAULT TIMESTAMPLTZ '2024-02-29 12:34:56 +09:00'",
+    "DATETIME DEFAULT DATETIME '2024-02-29 12:34:56.789'",
+    "DATETIMETZ DEFAULT DATETIMETZ '2024-02-29 12:34:56.789 +09:00'",
+    "DATETIMELTZ DEFAULT DATETIMELTZ '2024-02-29 12:34:56.789 +09:00'",
+    "CHAR(8) DEFAULT 'b'", "VARCHAR(128) DEFAULT '한글 partition key'"
+  };
+  for (const char *column : columns)
+    {
+      SCOPED_TRACE (column);
+      ASSERT_GE (exec_sql ("DROP TABLE IF EXISTS t_oos_show_part"), 0);
+      std::string spec = column;
+      std::string bound = spec.substr (spec.find (" DEFAULT ") + 9);
+      if (spec.find ("CHAR(8)") == 0)
+	{
+	  bound = "'b       '";
+	}
+      std::string ddl = std::string ("CREATE TABLE t_oos_show_part (id ") + column
+			+ ", data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY LIST(id) "
+			+ "(PARTITION p0 VALUES IN (" + bound + "), PARTITION p1 VALUES IN(NULL))";
+      ASSERT_GE (exec_sql (ddl.c_str ()), 0);
+      ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part(data_col) VALUES(REPEAT(X'AA',64))"), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'BB',64)"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+			"id IS NOT NULL AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=NULL"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+			"id IS NULL AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+      std::string assignment = std::string ("UPDATE t_oos_show_part SET id=") + bound;
+      ASSERT_EQ (exec_sql (assignment.c_str ()), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id IS NOT NULL", 1);
+      ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+			"data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+    }
+}
+
+TEST_F (OosSqlShow, PartitionUpdateOldOosKeyAndRepresentation)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(128) STORAGE FORCE_OUTLINE, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE, big_col BIT VARYING) "
+		       "PARTITION BY RANGE(LOWER(SUBSTRING(id,1,1))) "
+		       "(PARTITION p0 VALUES LESS THAN('b'), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "('A123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-', "
+		       "REPEAT(X'AA',64), REPEAT(X'BB',6000))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  ASSERT_GE (exec_sql ("ALTER TABLE t_oos_show_part ADD COLUMN added INT DEFAULT 77"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'CC',64)"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE added=77 "
+		    "AND data_col=CAST(REPEAT(X'CC',64) AS BIT VARYING)", 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part "
+		       "SET id='B123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-'"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE added=77 "
+		    "AND big_col=CAST(REPEAT(X'BB',6000) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 3);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE added=77 "
+		    "AND data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+}
+
+TEST_F (OosSqlShow, PartitionUpdateLobLifecycle)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE, "
+		       "text_lob CLOB, binary_lob BLOB STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) "
+		       "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(9,REPEAT(X'AA',64),CHAR_TO_CLOB('old text'),BIT_TO_BLOB(X'AABB'))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=id+1"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE CLOB_TO_CHAR(text_lob)='old text' "
+		    "AND BLOB_TO_BIT(binary_lob)=X'AABB'", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  // One forced VARBIT and one forced BLOB locator; the ordinary CLOB locator stays inline.
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET text_lob=CHAR_TO_CLOB('new text'), "
+		       "binary_lob=BIT_TO_BLOB(X'CCDD')"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE CLOB_TO_CHAR(text_lob)='new text' "
+		    "AND BLOB_TO_BIT(binary_lob)=X'CCDD'", 1);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE CLOB_TO_CHAR(text_lob)='old text' "
+		    "AND BLOB_TO_BIT(binary_lob)=X'AABB'", 1);
+}
+
+TEST_F (OosSqlShow, PartitionUpdateDedicatedIncrementsAndArithmetic)
+{
+  struct integer_case
+  {
+    const char *type;
+    const char *maximum;
+    const char *minimum;
+  };
+  const integer_case cases[] =
+  {
+    { "SMALLINT", "32767", "-32768" },
+    { "INTEGER", "2147483647", "-2147483648" },
+    { "BIGINT", "9223372036854775807", "-9223372036854775808" }
+  };
+  for (const auto &key : cases)
+    {
+      SCOPED_TRACE (key.type);
+      ASSERT_GE (exec_sql ("DROP TABLE IF EXISTS t_oos_show_part"), 0);
+      std::string ddl = std::string ("CREATE TABLE t_oos_show_part (id ") + key.type
+			+ ", data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) "
+			+ "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)";
+      ASSERT_GE (exec_sql (ddl.c_str ()), 0);
+      ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (9,REPEAT(X'AA',64))"), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      ASSERT_EQ (exec_sql ("SELECT INCR(id) FROM t_oos_show_part WHERE id=9"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=10 "
+			"AND data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+      ASSERT_EQ (exec_sql ("SELECT DECR(id) FROM t_oos_show_part WHERE id=10"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=9", 1);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=id+1"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=10", 1);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'BB',64)"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=10 "
+			"AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+      std::string set_max = std::string ("UPDATE t_oos_show_part SET id=") + key.maximum;
+      ASSERT_EQ (exec_sql (set_max.c_str ()), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      ASSERT_EQ (exec_sql ("SELECT INCR(id) FROM t_oos_show_part"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=0", 1);
+      std::string set_min = std::string ("UPDATE t_oos_show_part SET id=") + key.minimum;
+      ASSERT_EQ (exec_sql (set_min.c_str ()), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      ASSERT_EQ (exec_sql ("SELECT DECR(id) FROM t_oos_show_part"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=0", 1);
+    }
+}
+
+TEST_F (OosSqlShow, EffectiveUpdateRouteUsesMissingHistoricalKeyDefault)
+{
+  // Retain a real serialized representation from before this class acquired its partition key.
+  // No heap row is installed: this isolates the supplied-old-record contract from ALTER redistribution.
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (data_col INT DEFAULT 42)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  OID root_oid = *db_identifier (db_find_class ("t_oos_show_part"));
+  std::string historical_bytes;
+  RECDES historical = RECDES_INITIALIZER;
+  REPR_ID historical_repr;
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO old_values;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &old_values), NO_ERROR);
+    historical_repr = old_values.last_classrepr->id;
+    record_descriptor old_record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+    bool demote = false;
+    EXPECT_EQ (heap_attrinfo_transform_to_disk_probe_oos (thread_p, &old_values, NULL, &old_record,
+	       LOB_FLAG_INCLUDE_LOB, &demote), S_SUCCESS);
+    historical = old_record.get_recdes ();
+    historical_bytes.assign (historical.data, historical.length);
+    heap_attrinfo_end (thread_p, &old_values);
+  }
+  ASSERT_GE (exec_sql ("ALTER TABLE t_oos_show_part ADD COLUMN id INT DEFAULT 11"), 0);
+  ASSERT_GE (exec_sql ("ALTER TABLE t_oos_show_part PARTITION BY RANGE(id) "
+		       "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  OID expected = *db_identifier (db_find_class ("t_oos_show_part__p__p1"));
+  historical.data = &historical_bytes[0];
+  historical.area_size = historical.length;
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO candidate, reference;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &candidate), NO_ERROR);
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &reference), NO_ERROR);
+    EXPECT_NE (candidate.last_classrepr->id, historical_repr);
+    PRUNING_CONTEXT context;
+    ASSERT_EQ (partition_load_pruning_context (thread_p, &root_oid, DB_PARTITIONED_CLASS, &context), NO_ERROR);
+    OID selected = OID_INITIALIZER, reference_oid = OID_INITIALIZER;
+    HFID selected_hfid, reference_hfid;
+    int error = partition_prune_update_by_attrinfo (thread_p, &root_oid, &candidate, &historical, &context,
+		DB_PARTITIONED_CLASS, &selected, &selected_hfid, NULL);
+    EXPECT_EQ (error, NO_ERROR);
+    if (error == NO_ERROR)
+      {
+	EXPECT_TRUE (OID_EQ (&selected, &expected));
+	for (int i = 0; i < candidate.num_values; i++)
+	  {
+	    EXPECT_EQ (candidate.values[i].state, HEAP_UNINIT_ATTRVALUE);
+	    EXPECT_TRUE (DB_IS_NULL (&candidate.values[i].dbvalue));
+	  }
+	record_descriptor record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+	bool demote = false;
+	EXPECT_EQ (heap_attrinfo_transform_to_disk_probe_oos (thread_p, &reference, &historical, &record,
+		   LOB_FLAG_INCLUDE_LOB, &demote), S_SUCCESS);
+	RECDES reference_recdes = record.get_recdes ();
+	EXPECT_EQ (partition_prune_update (thread_p, &root_oid, &reference_recdes, &context, DB_PARTITIONED_CLASS,
+					   &reference_oid, &reference_hfid, NULL), NO_ERROR);
+	EXPECT_TRUE (OID_EQ (&selected, &reference_oid));
+	EXPECT_TRUE (HFID_EQ (&selected_hfid, &reference_hfid));
+	partition_clear_pruning_context (&context);
+      }
+    heap_attrinfo_end (thread_p, &reference);
+    heap_attrinfo_end (thread_p, &candidate);
+  }
+}
+
+TEST_F (OosSqlShow, EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT DEFAULT 2, data_col BIT VARYING "
+		       "STORAGE FORCE_OUTLINE) PARTITION BY RANGE (id) "
+		       "(PARTITION p0 VALUES LESS THAN (10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *child = db_find_class ("t_oos_show_part__p__p1");
+  ASSERT_NE (child, nullptr);
+  OID child_oid = *db_identifier (child);
+  ATTR_ID id = db_attribute_id (db_get_attribute (child, "id"));
+  OID p0_oid = *db_identifier (db_find_class ("t_oos_show_part__p__p0"));
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO old_values;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &child_oid, -1, NULL, &old_values), NO_ERROR);
+    DB_VALUE old_key;
+    db_make_int (&old_key, 10);
+    EXPECT_EQ (heap_attrinfo_set (NULL, id, &old_key, &old_values), NO_ERROR);
+    record_descriptor old_record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+    bool demote = false;
+    EXPECT_EQ (heap_attrinfo_transform_to_disk_probe_oos (thread_p, &old_values, NULL, &old_record,
+	       LOB_FLAG_INCLUDE_LOB, &demote), S_SUCCESS);
+    RECDES old_recdes = old_record.get_recdes ();
+    // Unchanged, pending INCR, pending DECR, and an already evaluated ordinary assignment.
+    for (int mode = 0; mode < 4; mode++)
+      {
+	SCOPED_TRACE (mode);
+	HEAP_CACHE_ATTRINFO candidate;
+	EXPECT_EQ (heap_attrinfo_start (thread_p, &child_oid, -1, NULL, &candidate), NO_ERROR);
+	HEAP_ATTRVALUE *key = heap_attrvalue_locate (id, &candidate);
+	key->do_increment = mode == 1 ? 1 : mode == 2 ? -1 : 0;
+	if (mode == 3)
+	  {
+	    DB_VALUE assigned;
+	    db_make_int (&assigned, 9);
+	    EXPECT_EQ (heap_attrinfo_set (NULL, id, &assigned, &candidate), NO_ERROR);
+	  }
+	const auto state = key->state;
+	auto *read_repr = candidate.read_classrepr;
+	OID selected = OID_INITIALIZER;
+	HFID selected_hfid;
+	int error = partition_prune_update_by_attrinfo (thread_p, &child_oid, &candidate, &old_recdes, NULL,
+		    DB_PARTITIONED_CLASS, &selected, &selected_hfid, NULL);
+	EXPECT_EQ (error, NO_ERROR);
+	if (error == NO_ERROR)
+	  {
+	    EXPECT_TRUE (OID_EQ (&selected, mode < 2 ? &child_oid : &p0_oid));
+	  }
+	EXPECT_EQ (candidate.read_classrepr, read_repr);
+	EXPECT_EQ (key->state, state);
+	EXPECT_EQ (key->do_increment, mode == 1 ? 1 : mode == 2 ? -1 : 0);
+	if (mode == 3)
+	  {
+	    EXPECT_EQ (db_get_int (&key->dbvalue), 9);
+	  }
+	else
+	  {
+	    EXPECT_TRUE (DB_IS_NULL (&key->dbvalue));
+	  }
+	if (error == NO_ERROR)
+	  {
+	    // Repeating selection must not consume the pending operation. The first real transform must.
+	    EXPECT_EQ (partition_prune_update_by_attrinfo (thread_p, &child_oid, &candidate, &old_recdes, NULL,
+		       DB_PARTITIONED_CLASS, &selected, &selected_hfid, NULL), NO_ERROR);
+	    record_descriptor actual_record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+	    EXPECT_EQ (heap_attrinfo_transform_to_disk_with_oos_owner (thread_p, &candidate, &old_recdes,
+		       &actual_record, LOB_FLAG_INCLUDE_LOB,
+		       &selected), S_SUCCESS);
+	    EXPECT_EQ (db_get_int (&key->dbvalue), mode == 0 ? 10 : mode == 1 ? 11 : 9);
+	    OID final_oid = OID_INITIALIZER;
+	    HFID final_hfid;
+	    RECDES actual = actual_record.get_recdes ();
+	    EXPECT_EQ (partition_prune_update (thread_p, &child_oid, &actual, NULL, DB_PARTITIONED_CLASS,
+					       &final_oid, &final_hfid, NULL), NO_ERROR);
+	    EXPECT_TRUE (OID_EQ (&selected, &final_oid));
+	    EXPECT_TRUE (HFID_EQ (&selected_hfid, &final_hfid));
+	  }
+	heap_attrinfo_end (thread_p, &candidate);
+      }
+    heap_attrinfo_end (thread_p, &old_values);
+  }
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, PartitionPreparationFailuresRollBackAndAllowNextWrite)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT, "
+		       "a BIT VARYING STORAGE FORCE_OUTLINE, b BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_GE (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(1, REPEAT(X'AA',64), REPEAT(X'BB',64)), "
+		       "(11, REPEAT(X'AA',64), REPEAT(X'BB',64))"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+
+  for (bool update :
+       {
+	       false, true
+       })
+    {
+      for (int failure = 0; failure < 4; failure++)
+	{
+	  SCOPED_TRACE (failure);
+	  SCOPED_TRACE (update ? "moving UPDATE" : "INSERT");
+	  // A multi-chunk second value prevents both values publishing in one small-page batch.
+	  if (failure == 0)
+	    {
+	      oos_test_fail_insert_many_after_publications (1);
+	    }
+	  else if (failure == 1)
+	    {
+	      bridge_heap_attrinfo_fail_after_oos_publication_reset_once ();
+	    }
+	  else if (failure == 2)
+	    {
+	      heap_oos_test_fail_before_vfid_lookup_once ();
+	    }
+	  else
+	    {
+	      oos_test_throw_bad_alloc_on_next_oid_publication ();
+	    }
+	  int error = exec_sql (update
+				? "UPDATE t_oos_show_part SET id=12, a=REPEAT(X'CC',64), "
+				"b=REPEAT(X'DD',20000) WHERE id=1"
+				: "INSERT INTO t_oos_show_part VALUES (12, REPEAT(X'CC',64), REPEAT(X'DD',20000))");
+	  oos_test_disarm_insert_publication_failures ();
+	  bridge_heap_attrinfo_disarm_publication_reset_failure ();
+	  heap_oos_test_disarm_fail_before_vfid_lookup ();
+	  EXPECT_EQ (error, failure == 3 ? ER_OUT_OF_VIRTUAL_MEMORY : ER_GENERIC_ERROR);
+	  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+
+	  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id IN (1,11) "
+			    "AND a=CAST(REPEAT(X'AA',64) AS BIT VARYING) "
+			    "AND b=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 2);
+	  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id=12", 0);
+	  expect_oos_records ("t_oos_show_part", 0, 0);
+	  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+	  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+
+	  ASSERT_GE (exec_sql ("INSERT INTO t_oos_show_part VALUES (12, REPEAT(X'CC',64), REPEAT(X'DD',64))"), 0);
+	  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=12 "
+			    "AND a=CAST(REPEAT(X'CC',64) AS BIT VARYING) "
+			    "AND b=CAST(REPEAT(X'DD',64) AS BIT VARYING)", 1);
+	  expect_oos_records ("t_oos_show_part__p__p1", 1, 4);
+	  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+	  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+	}
+    }
+}
+
+TEST_F (OosSqlShow, PartitionLobPreparationAndIndexFailuresPreserveCommittedValues)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT PRIMARY KEY, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE, text_lob CLOB, "
+		       "binary_lob BLOB STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) "
+		       "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(1,REPEAT(X'AA',64),CHAR_TO_CLOB('old text'),BIT_TO_BLOB(X'AABB')), "
+		       "(11,REPEAT(X'AA',64),CHAR_TO_CLOB('old text'),BIT_TO_BLOB(X'AABB'))"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  for (int failure = 0; failure < 3; failure++)
+    {
+      SCOPED_TRACE (failure);
+      if (failure == 0)
+	{
+	  // Fail after OOS payload preparation, which copies the written BLOB locator.
+	  heap_oos_test_fail_before_vfid_lookup_once ();
+	}
+      int error = exec_sql (failure == 0
+			    ? "UPDATE t_oos_show_part SET id=12, text_lob=CHAR_TO_CLOB('new text'), "
+			    "binary_lob=BIT_TO_BLOB(X'CCDD') WHERE id=1"
+			    : failure == 1
+			    ? "UPDATE t_oos_show_part SET id=11, text_lob=CHAR_TO_CLOB('new text'), "
+			    "binary_lob=BIT_TO_BLOB(X'CCDD') WHERE id=1"
+			    : "UPDATE t_oos_show_part SET id=11 WHERE id=1");
+      heap_oos_test_disarm_fail_before_vfid_lookup ();
+      EXPECT_EQ (error, failure == 0 ? ER_GENERIC_ERROR : ER_BTREE_UNIQUE_FAILED);
+      ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id IN (1,11) "
+			"AND CLOB_TO_CHAR(text_lob)='old text' AND BLOB_TO_BIT(binary_lob)=X'AABB'", 2);
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+      expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=12, text_lob=CHAR_TO_CLOB('next text'), "
+			   "binary_lob=BIT_TO_BLOB(X'EEFF') WHERE id=1"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=12 "
+			"AND CLOB_TO_CHAR(text_lob)='next text' AND BLOB_TO_BIT(binary_lob)=X'EEFF'", 1);
+      expect_oos_records ("t_oos_show_part__p__p1", 1, 4);
+      ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+    }
+}
+
+TEST_F (OosSqlShow, EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment)
+{
+  // Fault only the codec on a private attribute/domain copy; never mutate cached schema metadata.
+  class failing_codec : public PR_TYPE
+  {
+    public:
+      failing_codec (const PR_TYPE &original, bool fail_read) : PR_TYPE (original)
+      {
+	if (fail_read)
+	  {
+	    f_data_readval = [] (struct or_buf *, DB_VALUE *out, TP_DOMAIN *, int, bool, char *, int)
+	    {
+	      DB_VALUE partial;
+	      db_make_string (&partial, "partially decoded key");
+	      pr_clone_value (&partial, out);
+	      return ER_FAILED;
+	    };
+	  }
+	else
+	  {
+	    f_data_writeval = [] (struct or_buf *, DB_VALUE *)
+	    {
+	      return ER_FAILED;
+	    };
+	  }
+      }
+  };
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(512), data_col INT) "
+		       "PARTITION BY RANGE(LENGTH(id)) (PARTITION p0 VALUES LESS THAN(10), "
+		       "PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *root = db_find_class ("t_oos_show_part");
+  ASSERT_NE (root, nullptr);
+  OID root_oid = *db_identifier (root);
+  DB_ATTRIBUTE *attribute = db_get_attribute (root, "id");
+  ASSERT_NE (attribute, nullptr);
+  ATTR_ID key_id = db_attribute_id (attribute);
+  std::string text;
+  unsigned int random = 12345;
+  for (int i = 0; i < 300; i++)
+    {
+      random = random * 1664525U + 1013904223U;
+      text.push_back ('!' + ((random >> 16) % 90));
+    }
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO cache;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &cache), NO_ERROR);
+    DB_VALUE assigned;
+    db_make_string (&assigned, text.c_str ());
+    EXPECT_EQ (heap_attrinfo_set (NULL, key_id, &assigned, &cache), NO_ERROR);
+    HEAP_ATTRVALUE *slot = heap_attrvalue_locate (key_id, &cache);
+    OR_ATTRIBUTE *original = slot->last_attrepr;
+    for (bool fail_read :
+	 {
+		 false, true
+	 })
+      {
+	OR_ATTRIBUTE local_attribute {};
+	local_attribute.id = original->id;
+	local_attribute.type = original->type;
+	local_attribute.is_fixed = original->is_fixed;
+	TP_DOMAIN local_domain = *original->domain;
+	failing_codec codec (*original->domain->type, fail_read);
+	local_domain.type = &codec;
+	local_attribute.domain = &local_domain;
+	slot->last_attrepr = &local_attribute;
+	DB_VALUE key;
+	db_make_null (&key);
+	int error = heap_attrinfo_get_effective_key (thread_p, &cache, key_id, NULL, &key);
+	slot->last_attrepr = original;
+	EXPECT_EQ (error, ER_FAILED);
+	EXPECT_TRUE (DB_IS_NULL (&key));
+	pr_clear_value (&key);
+	EXPECT_EQ (slot->state, HEAP_WRITTEN_ATTRVALUE);
+	EXPECT_EQ (std::string (db_get_string (&slot->dbvalue), db_get_string_size (&slot->dbvalue)), text);
+	db_make_null (&key);
+	EXPECT_EQ (heap_attrinfo_get_effective_key (thread_p, &cache, key_id, NULL, &key), NO_ERROR);
+	if (!DB_IS_NULL (&key))
+	  {
+	    EXPECT_EQ (std::string (db_get_string (&key), db_get_string_size (&key)), text);
+	  }
+	pr_clear_value (&key);
+      }
+    heap_attrinfo_end (thread_p, &cache);
+  }
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, EffectiveRoutingFailurePreservesAssignmentsAndPublication)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN (20))"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *root = db_find_class ("t_oos_show_part");
+  ASSERT_NE (root, nullptr);
+  OID root_oid = *db_identifier (root);
+  ATTR_ID key_id = db_attribute_id (db_get_attribute (root, "id"));
+  ATTR_ID payload_id = db_attribute_id (db_get_attribute (root, "data_col"));
+  OID p0_oid = *db_identifier (db_find_class ("t_oos_show_part__p__p0"));
+  OID p1_oid = *db_identifier (db_find_class ("t_oos_show_part__p__p1"));
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO cache;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &cache), NO_ERROR);
+    PRUNING_CONTEXT context;
+    partition_init_pruning_context (&context);
+    LOG_TDES *tdes = LOG_FIND_TDES (LOG_FIND_THREAD_TRAN_INDEX (thread_p));
+    ASSERT_NE (tdes, nullptr);
+    const LOG_LSA marker { 876543, 123 };
+    thread_p->oos_oids.clear ();
+    tdes->oos_insert_lsa_queue.clear ();
+    thread_p->oos_oids.push_back (root_oid);
+    tdes->oos_insert_lsa_queue.push (marker);
+    for (int input :
+	 {
+		 11, 21, 1, 21, 11
+	 })
+      {
+	DB_VALUE assigned;
+	db_make_int (&assigned, input);
+	EXPECT_EQ (heap_attrinfo_set (NULL, key_id, &assigned, &cache), NO_ERROR);
+	OID destination = OID_INITIALIZER;
+	HFID hfid;
+	int error = partition_prune_insert_by_attrinfo (thread_p, &root_oid, &cache, &context,
+		    DB_PARTITIONED_CLASS, &destination, &hfid, NULL);
+	EXPECT_EQ (error, input == 21 ? ER_PARTITION_NOT_EXIST : NO_ERROR);
+	if (error == NO_ERROR)
+	  {
+	    EXPECT_TRUE (OID_EQ (&destination, input < 10 ? &p0_oid : &p1_oid));
+	  }
+	EXPECT_EQ (db_get_int (&heap_attrvalue_locate (key_id, &cache)->dbvalue), input);
+	EXPECT_EQ (heap_attrvalue_locate (key_id, &cache)->state, HEAP_WRITTEN_ATTRVALUE);
+	EXPECT_EQ (heap_attrvalue_locate (payload_id, &cache)->state, HEAP_UNINIT_ATTRVALUE);
+	EXPECT_EQ (thread_p->oos_oids.size (), 1U);
+	if (!thread_p->oos_oids.empty ())
+	  {
+	    EXPECT_TRUE (OID_EQ (&thread_p->oos_oids.front (), &root_oid));
+	  }
+	EXPECT_EQ (tdes->oos_insert_lsa_queue.size (), 1U);
+	if (!tdes->oos_insert_lsa_queue.is_empty ())
+	  {
+	    EXPECT_TRUE (LSA_EQ (&tdes->oos_insert_lsa_queue.front (), &marker));
+	  }
+	er_clear ();
+      }
+    EXPECT_EQ (heap_oos_begin_insert_publication (thread_p), S_SUCCESS);
+    partition_clear_pruning_context (&context);
+    heap_attrinfo_end (thread_p, &cache);
+  }
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, EffectiveInsertRoutePreservesOmittedAssignments)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT DEFAULT 11, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *root = db_find_class ("t_oos_show_part");
+  ASSERT_NE (root, nullptr);
+  OID root_oid = *db_identifier (root);
+  DB_OBJECT *child = db_find_class ("t_oos_show_part__p__p1");
+  ASSERT_NE (child, nullptr);
+  OID expected_oid = *db_identifier (child);
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO candidate;
+    HEAP_CACHE_ATTRINFO reference;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &candidate), NO_ERROR);
+    int reference_error = heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &reference);
+    if (reference_error != NO_ERROR)
+      {
+	heap_attrinfo_end (thread_p, &candidate);
+	FAIL () << reference_error;
+      }
+
+    OID selected_oid = OID_INITIALIZER, reference_oid = OID_INITIALIZER;
+    HFID selected_hfid, reference_hfid;
+    int error = partition_prune_insert_by_attrinfo (thread_p, &root_oid, &candidate, NULL, DB_PARTITIONED_CLASS,
+		&selected_oid, &selected_hfid, NULL);
+    EXPECT_EQ (error, NO_ERROR);
+    if (error == NO_ERROR)
+      {
+	EXPECT_TRUE (OID_EQ (&selected_oid, &expected_oid));
+      }
+    for (int i = 0; i < candidate.num_values; i++)
+      {
+	EXPECT_EQ (candidate.values[i].state, HEAP_UNINIT_ATTRVALUE);
+	EXPECT_TRUE (DB_IS_NULL (&candidate.values[i].dbvalue));
+      }
+
+    // The reference owns separate values: the inline probe may initialize and mutate them.
+    record_descriptor record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+    bool would_demote = false;
+    SCAN_CODE scan = heap_attrinfo_transform_to_disk_probe_oos (thread_p, &reference, NULL, &record,
+		     LOB_FLAG_INCLUDE_LOB, &would_demote);
+    EXPECT_EQ (scan, S_SUCCESS);
+    if (scan == S_SUCCESS)
+      {
+	RECDES recdes = record.get_recdes ();
+	EXPECT_EQ (partition_prune_insert (thread_p, &root_oid, &recdes, NULL, NULL, DB_PARTITIONED_CLASS,
+					   &reference_oid, &reference_hfid, NULL), NO_ERROR);
+	EXPECT_TRUE (OID_EQ (&reference_oid, &expected_oid));
+	if (error == NO_ERROR)
+	  {
+	    EXPECT_TRUE (OID_EQ (&selected_oid, &reference_oid));
+	    EXPECT_TRUE (HFID_EQ (&selected_hfid, &reference_hfid));
+	  }
+      }
+    heap_attrinfo_end (thread_p, &reference);
+    heap_attrinfo_end (thread_p, &candidate);
+  }
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, EffectiveInsertRoutePreservesAssignedChar)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id CHAR(8), data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY LIST (id) (PARTITION p0 VALUES IN ('a       '), "
+		       "PARTITION p1 VALUES IN ('b       '))"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *root = db_find_class ("t_oos_show_part");
+  ASSERT_NE (root, nullptr);
+  OID root_oid = *db_identifier (root);
+  DB_ATTRIBUTE *key_attribute = db_get_attribute (root, "id");
+  ASSERT_NE (key_attribute, nullptr);
+  ATTR_ID key_id = db_attribute_id (key_attribute);
+  DB_OBJECT *child = db_find_class ("t_oos_show_part__p__p1");
+  ASSERT_NE (child, nullptr);
+  OID expected_oid = *db_identifier (child);
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO candidate;
+    HEAP_CACHE_ATTRINFO reference;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &candidate), NO_ERROR);
+    int error = heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &reference);
+    if (error != NO_ERROR)
+      {
+	heap_attrinfo_end (thread_p, &candidate);
+	FAIL () << error;
+      }
+    DB_VALUE assigned;
+    db_make_string (&assigned, "b");
+    EXPECT_EQ (heap_attrinfo_set (NULL, key_id, &assigned, &candidate), NO_ERROR);
+    EXPECT_EQ (heap_attrinfo_set (NULL, key_id, &assigned, &reference), NO_ERROR);
+    int key_index = candidate.values[0].attrid == key_id ? 0 : 1;
+    const HEAP_ATTRVALUE &source = candidate.values[key_index];
+    int source_size = db_get_string_size (&source.dbvalue);
+    std::string source_bytes (db_get_string (&source.dbvalue), source_size);
+    auto source_state = source.state;
+
+    OID selected_oid = OID_INITIALIZER, reference_oid = OID_INITIALIZER;
+    HFID selected_hfid, reference_hfid;
+    error = partition_prune_insert_by_attrinfo (thread_p, &root_oid, &candidate, NULL, DB_PARTITIONED_CLASS,
+	    &selected_oid, &selected_hfid, NULL);
+    EXPECT_EQ (error, NO_ERROR);
+    if (error == NO_ERROR)
+      {
+	EXPECT_TRUE (OID_EQ (&selected_oid, &expected_oid));
+      }
+    EXPECT_EQ (source.state, source_state);
+    EXPECT_EQ (db_get_string_size (&source.dbvalue), source_size);
+    EXPECT_EQ (std::string (db_get_string (&source.dbvalue), db_get_string_size (&source.dbvalue)), source_bytes);
+    EXPECT_EQ (candidate.values[1 - key_index].state, HEAP_UNINIT_ATTRVALUE);
+
+    record_descriptor record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+    bool would_demote = false;
+    SCAN_CODE scan = heap_attrinfo_transform_to_disk_probe_oos (thread_p, &reference, NULL, &record,
+		     LOB_FLAG_INCLUDE_LOB, &would_demote);
+    EXPECT_EQ (scan, S_SUCCESS);
+    if (scan == S_SUCCESS)
+      {
+	RECDES recdes = record.get_recdes ();
+	EXPECT_EQ (partition_prune_insert (thread_p, &root_oid, &recdes, NULL, NULL, DB_PARTITIONED_CLASS,
+					   &reference_oid, &reference_hfid, NULL), NO_ERROR);
+	EXPECT_TRUE (OID_EQ (&reference_oid, &expected_oid));
+	if (error == NO_ERROR)
+	  {
+	    EXPECT_TRUE (OID_EQ (&selected_oid, &reference_oid));
+	    EXPECT_TRUE (HFID_EQ (&selected_hfid, &reference_hfid));
+	  }
+      }
+    heap_attrinfo_end (thread_p, &reference);
+    heap_attrinfo_end (thread_p, &candidate);
+  }
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, EffectiveInsertRouteLegalKeyDefaults)
+{
+  const char *columns[] =
+  {
+    "SMALLINT DEFAULT 11", "INTEGER DEFAULT 11", "BIGINT DEFAULT 2147483648",
+    "DATE DEFAULT DATE '2024-02-29'", "TIME DEFAULT TIME '12:34:56'",
+    "TIMESTAMP DEFAULT TIMESTAMP '2024-02-29 12:34:56'",
+    "TIMESTAMPTZ DEFAULT TIMESTAMPTZ '2024-02-29 12:34:56 +09:00'",
+    "TIMESTAMPLTZ DEFAULT TIMESTAMPLTZ '2024-02-29 12:34:56 +09:00'",
+    "DATETIME DEFAULT DATETIME '2024-02-29 12:34:56.789'",
+    "DATETIMETZ DEFAULT DATETIMETZ '2024-02-29 12:34:56.789 +09:00'",
+    "DATETIMELTZ DEFAULT DATETIMELTZ '2024-02-29 12:34:56.789 +09:00'",
+    "CHAR(8) DEFAULT 'b'", "VARCHAR(128) DEFAULT '한글 partition key'"
+  };
+  for (const char *column : columns)
+    {
+      SCOPED_TRACE (column);
+      ASSERT_GE (exec_sql ("DROP TABLE IF EXISTS t_oos_show_part"), 0);
+      std::string column_spec = column;
+      std::string bound = column_spec.substr (column_spec.find (" DEFAULT ") + 9);
+      if (column_spec.find ("CHAR(8)") == 0)
+	{
+	  bound = "'b       '";
+	}
+      std::string ddl = std::string ("CREATE TABLE t_oos_show_part (id ") + column
+			+ ", data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY LIST (id) ("
+			+ "PARTITION p0 VALUES IN (" + bound + "), PARTITION p1 VALUES IN (NULL))";
+      ASSERT_GE (exec_sql (ddl.c_str ()), 0);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      DB_OBJECT *root = db_find_class ("t_oos_show_part");
+      ASSERT_NE (root, nullptr);
+      OID root_oid = *db_identifier (root);
+      {
+	scoped_sa_server server_scope;
+	THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+	HEAP_CACHE_ATTRINFO candidate;
+	HEAP_CACHE_ATTRINFO reference;
+	ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &candidate), NO_ERROR);
+	int error = heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &reference);
+	if (error != NO_ERROR)
+	  {
+	    heap_attrinfo_end (thread_p, &candidate);
+	    FAIL () << error;
+	  }
+	OID selected_oid = OID_INITIALIZER, reference_oid = OID_INITIALIZER;
+	HFID selected_hfid, reference_hfid;
+	error = partition_prune_insert_by_attrinfo (thread_p, &root_oid, &candidate, NULL, DB_PARTITIONED_CLASS,
+		&selected_oid, &selected_hfid, NULL);
+	EXPECT_EQ (error, NO_ERROR);
+	for (int i = 0; i < candidate.num_values; i++)
+	  {
+	    EXPECT_EQ (candidate.values[i].state, HEAP_UNINIT_ATTRVALUE);
+	    EXPECT_TRUE (DB_IS_NULL (&candidate.values[i].dbvalue));
+	  }
+	record_descriptor record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+	bool would_demote = false;
+	SCAN_CODE scan = heap_attrinfo_transform_to_disk_probe_oos (thread_p, &reference, NULL, &record,
+			 LOB_FLAG_INCLUDE_LOB, &would_demote);
+	EXPECT_EQ (scan, S_SUCCESS);
+	if (scan == S_SUCCESS)
+	  {
+	    RECDES recdes = record.get_recdes ();
+	    EXPECT_EQ (partition_prune_insert (thread_p, &root_oid, &recdes, NULL, NULL, DB_PARTITIONED_CLASS,
+					       &reference_oid, &reference_hfid, NULL), NO_ERROR);
+	    if (error == NO_ERROR)
+	      {
+		EXPECT_TRUE (OID_EQ (&selected_oid, &reference_oid));
+		EXPECT_TRUE (HFID_EQ (&selected_hfid, &reference_hfid));
+	      }
+	  }
+	heap_attrinfo_end (thread_p, &reference);
+	heap_attrinfo_end (thread_p, &candidate);
+      }
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+    }
+}
+
+TEST_F (OosSqlShow, PartitionInsertLegalKeySqlMatrix)
+{
+  struct key_case
+  {
+    const char *type;
+    const char *value;
+  };
+  const key_case cases[] =
+  {
+    { "SMALLINT", "11" }, { "INTEGER", "11" }, { "BIGINT", "2147483648" },
+    { "DATE", "DATE '2024-02-29'" }, { "TIME", "TIME '12:34:56'" },
+    { "TIMESTAMP", "TIMESTAMP '2024-02-29 12:34:56'" },
+    { "TIMESTAMPTZ", "TIMESTAMPTZ '2024-02-29 12:34:56 +09:00'" },
+    { "TIMESTAMPLTZ", "TIMESTAMPLTZ '2024-02-29 12:34:56 +09:00'" },
+    { "DATETIME", "DATETIME '2024-02-29 12:34:56.789'" },
+    { "DATETIMETZ", "DATETIMETZ '2024-02-29 12:34:56.789 +09:00'" },
+    { "DATETIMELTZ", "DATETIMELTZ '2024-02-29 12:34:56.789 +09:00'" },
+    { "CHAR(8)", "'b'" }, { "VARCHAR(128)", "'한글 partition key'" }
+  };
+  for (const key_case &key : cases)
+    {
+      SCOPED_TRACE (key.type);
+      ASSERT_GE (exec_sql ("DROP TABLE IF EXISTS t_oos_show_part"), 0);
+      std::string ddl = std::string ("CREATE TABLE t_oos_show_part (id ") + key.type + " DEFAULT " + key.value
+			+ ", data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY HASH (id) PARTITIONS 2";
+      ASSERT_GE (exec_sql (ddl.c_str ()), 0);
+      std::string insert = std::string ("INSERT INTO t_oos_show_part VALUES (") + key.value
+			   + ", REPEAT(X'AA', 64)), (NULL, REPEAT(X'BB', 64)), (" + key.value
+			   + ", REPEAT(X'CC', 64))";
+      ASSERT_EQ (exec_sql (insert.c_str ()), 3);
+      ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part (data_col) VALUES (REPEAT(X'DD', 64))"), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      std::string matching = std::string ("SELECT COUNT(*) FROM t_oos_show_part WHERE id = CAST(") + key.value
+			     + " AS " + key.type + ") AND data_col IN (CAST(REPEAT(X'AA', 64) AS BIT VARYING), "
+			     + "CAST(REPEAT(X'CC', 64) AS BIT VARYING), CAST(REPEAT(X'DD', 64) AS BIT VARYING))";
+      expect_sql_count (matching.c_str (), 3);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id IS NULL "
+			"AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)", 1);
+      int p0_count = -1, p1_count = -1;
+      ASSERT_EQ (fetch_single_int ("SELECT COUNT(*) FROM t_oos_show_part__p__p0", &p0_count), NO_ERROR);
+      ASSERT_EQ (fetch_single_int ("SELECT COUNT(*) FROM t_oos_show_part__p__p1", &p1_count), NO_ERROR);
+      EXPECT_EQ (p0_count + p1_count, 4);
+      // Retain literal partition observations for the independent pinned-library run.
+      printf ("LEGAL_KEY %s p0=%d p1=%d\n", key.type, p0_count, p1_count);
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p0", p0_count > 0 ? 1 : 0, p0_count);
+      expect_oos_records ("t_oos_show_part__p__p1", p1_count > 0 ? 1 : 0, p1_count);
+    }
+}
+
+TEST_F (OosSqlShow, PartitionInsertOwnsExternalKeyAndMultiplePayloads)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id VARCHAR(128) STORAGE FORCE_OUTLINE, "
+		       "small_col BIT VARYING STORAGE FORCE_OUTLINE, large_col BIT VARYING) "
+		       "PARTITION BY RANGE (LOWER(SUBSTRING(id, 1, 1))) ("
+		       "PARTITION p0 VALUES LESS THAN ('b'), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "('A123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-', "
+		       "REPEAT(X'AA',64), REPEAT(X'BB',6000)), "
+		       "('B123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-', "
+		       "REPEAT(X'CC',64), REPEAT(X'DD',6000))"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "id = 'A123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-' AND "
+		    "small_col = CAST(REPEAT(X'AA',64) AS BIT VARYING) AND "
+		    "large_col = CAST(REPEAT(X'BB',6000) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "id = 'B123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-' AND "
+		    "small_col = CAST(REPEAT(X'CC',64) AS BIT VARYING) AND "
+		    "large_col = CAST(REPEAT(X'DD',6000) AS BIT VARYING)", 1);
+  // The key and both payloads each fit one OOS chunk; the ordinary VARBIT cannot be compressed.
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 3);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 3);
+}
+
+TEST_F (OosSqlShow, PartitionInsertRetainsBigoneRejectionBeforeOos)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT, fixed_col BIT(140000), "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) ("
+		       "PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  EXPECT_LT (exec_sql ("INSERT INTO t_oos_show_part VALUES(11,B'1',REPEAT(X'AA',64))"), 0);
+  EXPECT_EQ (er_errid (), ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+  // Without an OOS value the existing whole-record overflow path remains supported.
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES(11,B'1',NULL)"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=11 AND data_col IS NULL", 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, PartitionInsertGeneratedKeysAndDomainConversion)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT AUTO_INCREMENT(9,1), "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) ("
+		       "PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part(data_col) VALUES(REPEAT(X'AA',64)),(REPEAT(X'BB',64))"), 2);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES('11',REPEAT(X'CC',64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "id=9 AND data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id=10 AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)) OR "
+		    "(id=11 AND data_col=CAST(REPEAT(X'CC',64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionInsertDynamicDefault)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id DATE DEFAULT CURRENT_DATE, "
+		       "expected_date DATE, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY HASH(id) PARTITIONS 2"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part(expected_date,data_col) VALUES"
+		       "(CURRENT_DATE,REPEAT(X'AA',64)),(CURRENT_DATE,REPEAT(X'BB',64))"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id=expected_date AND "
+		    "data_col IN (CAST(REPEAT(X'AA',64) AS BIT VARYING),CAST(REPEAT(X'BB',64) AS BIT VARYING))", 2);
+  int p0_count = -1, p1_count = -1;
+  ASSERT_EQ (fetch_single_int ("SELECT COUNT(*) FROM t_oos_show_part__p__p0", &p0_count), NO_ERROR);
+  ASSERT_EQ (fetch_single_int ("SELECT COUNT(*) FROM t_oos_show_part__p__p1", &p1_count), NO_ERROR);
+  EXPECT_EQ (p0_count + p1_count, 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", p0_count > 0 ? 1 : 0, p0_count);
+  expect_oos_records ("t_oos_show_part__p__p1", p1_count > 0 ? 1 : 0, p1_count);
+}
+
+TEST_F (OosSqlShow, PartitionInsertUsesColumnCollation)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(20) COLLATE utf8_en_ci, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY LIST(id) ("
+		       "PARTITION p0 VALUES IN('alpha'), PARTITION p1 VALUES IN('beta'))"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES('BETA',REPEAT(X'AA',64)),"
+		       "('AlPhA',REPEAT(X'BB',64)),('beta',REPEAT(X'CC',64))"), 3);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id='alpha' AND "
+		    "data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id='beta' AND "
+		    "data_col IN (CAST(REPEAT(X'AA',64) AS BIT VARYING),CAST(REPEAT(X'CC',64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionInsertCompressedExpressionKey)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(4096) STORAGE FORCE_OUTLINE, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(CHAR_LENGTH(id)) ("
+		       "PARTITION p0 VALUES LESS THAN(3000), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES(REPEAT('b',3000),REPEAT(X'AA',64)),"
+		       "(REPEAT('a',2999),REPEAT(X'BB',64))"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=REPEAT('a',2999) "
+		    "AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=REPEAT('b',3000) "
+		    "AND data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
 int
 main (int argc, char **argv)
 {
```

### H63 — Preserve the unresolved real-vacuum regression

[unit_tests/oos/test_oos_real_vacuum_server.cpp old:825 / new:825](https://github.com/CUBRID/cubrid/pull/7600/files#diff-e2892f2dbab3c1bae4d87c4fa1b9f7d0cdc5463a2fa1ba9ee94983c13c26b0eeR825)

DISABLED_ 테스트는 committed 원본과 witness → replacement UPDATE와 abort → vacuum 전 read → committed witness delete와 실제 진행 확인 → 원본 재읽기 순서다. Witness를 먼저 할당해 재사용 slot alias를 피한다. 과거 마지막 read가 실패했으며 CBRD-27237까지 기본 실행에서 제외한다. Partition 전용 테스트나 lifecycle 통과가 아니다.

```diff
@@ -825,6 +825,50 @@ TEST_F (OosRealVacuum, ReVacuumAfterDrainIsIdempotent)
   expect_oos_gone (oos_oid, "drained OOS after re-vacuum");
 }
 
+/* A rolled-back replacement does not supersede the committed version. A
+ * separate committed delete witnesses real vacuum progress before readback;
+ * waking a daemon or freeing the replacement buffer alone proves nothing. */
+/* TODO (CBRD-27237): Remove DISABLED_ after the rollback/vacuum fix lands and
+ * this regression passes with real vacuum progress. */
+TEST_F (OosRealVacuum, DISABLED_RolledBackUpdateKeepsCommittedOosAfterVacuum)
+{
+  const std::string original (4096, 'a');
+  OID heap_oid, original_oid;
+  insert_row_with_oos (original, heap_oid, original_oid);
+
+  /* Allocate the progress witness before creating any reclaimable version,
+   * so a recycled OOS slot cannot alias the original OID in this test. */
+  OID witness_heap_oid, witness_oos_oid;
+  insert_row_with_oos (std::string (4096, 'w'), witness_heap_oid, witness_oos_oid);
+
+  RECDES replacement {};
+  ASSERT_EQ (test_oos_utils::from_string_into_recdes (std::string (4096, 'b'), replacement), NO_ERROR);
+  test_oos_utils::auto_freed_recdes_ptr defer_replacement (&replacement, recdes_free_data_area);
+  OID replacement_oid = OID_INITIALIZER;
+  ASSERT_EQ (test_oos_utils::oos_insert_from_recdes (thread_p, oos_vfid, replacement, replacement_oid), NO_ERROR);
+
+  RECDES new_heap_rec {};
+  ASSERT_EQ (build_heap_recdes_with_oos ({replacement_oid}, { (INT64) replacement.length}, new_heap_rec), NO_ERROR);
+  test_oos_utils::auto_freed_recdes_ptr defer_heap (&new_heap_rec, recdes_free_data_area);
+  ASSERT_EQ (heap_update_mvcc (hfid, class_oid, scan_cache, heap_oid, new_heap_rec), NO_ERROR);
+  ASSERT_EQ (xtran_server_abort (thread_p), TRAN_UNACTIVE_ABORTED);
+
+  RECDES before_vacuum {};
+  ASSERT_EQ (test_oos_utils::oos_read_with_alloc (thread_p, original_oid, before_vacuum), NO_ERROR);
+  test_oos_utils::auto_freed_recdes_ptr defer_before (&before_vacuum, recdes_free_data_area);
+  ASSERT_EQ (std::string (before_vacuum.data, before_vacuum.length - 1), original);
+
+  delete_row_and_close_block (witness_heap_oid);
+  ASSERT_TRUE (wait_for_vacuum ([this, &witness_oos_oid] { return oos_unreadable (witness_oos_oid); }, 60))
+      << "committed-delete witness did not establish vacuum progress";
+
+  RECDES after_vacuum {};
+  ASSERT_EQ (test_oos_utils::oos_read_with_alloc (thread_p, original_oid, after_vacuum), NO_ERROR)
+      << "rolled-back UPDATE must not make the committed OOS value reclaimable";
+  test_oos_utils::auto_freed_recdes_ptr defer_after (&after_vacuum, recdes_free_data_area);
+  EXPECT_EQ (std::string (after_vacuum.data, after_vacuum.length - 1), original);
+}
+
 int
 main (int argc, char **argv)
 {
```
