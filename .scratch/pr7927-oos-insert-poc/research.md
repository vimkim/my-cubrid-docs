# OOS insertion at the selected heap — source facts

Source: `feature/oos-merge`, `fb567a629cdb390fff920542173fa36f454c74a0`.
Date: 2026-10-06. 읽기 조사이며 실행으로 검증한 결과는 아니다.

## Main finding

일반 SQL INSERT 경로는 root와 child에 `heap_insert_logical()`을 두 번 호출하지 않는다. locator가 먼저 목적지를 고르고, 선택된 heap으로 한 번 호출한다. 따라서 그 지점에서 partition 여부를 다시 fetch해야만 목적지를 알 수 있는 것은 아니다.

```text
locator_attribute_info_force
  → locator_allocate_copy_area_by_attr_info
    → heap_attrinfo_transform_to_disk
      → heap_attrinfo_insert_to_oos(attr_info의 class)  [현재 기록 지점]
      → RECDES 완성
  → locator_insert_force
    → partition_prune_insert                         [필요할 때 목적지 결정]
    → heap_create_insert_context(real_hfid, real_class_oid, recdes)
    → heap_insert_logical                            [선택된 heap, 한 번]
    → index 및 FK 처리
```

이 순서는 `heap_insert_logical()` 근처로 OOS 쓰기를 늦추는 INSERT POC를 검토할 근거다. 실제 가능한 구현이나 성능 우월성을 증명한 것은 아니다. 기존 writer가 요구하는 값 표현, 헤더, 소유권과 부수 효과를 함께 설계해야 한다.

## Evidence

모든 링크와 줄 번호는 위 고정 커밋 기준이다.

| 항목 | 코드 근거 | 의미 |
|---|---|---|
| 변환 중 OOS 기록 | [`heap_file.c:13816`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L13816) | 파티션 선택 전에 chain이 만들어짐 |
| OOS 소유 class | [`heap_file.c:13224`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L13224) | 당시 `attr_info->class_oid`를 사용 |
| INSERT routing | [`locator_sr.c:4989`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L4989) | `partition_prune_insert()`가 목적지 결정 |
| 최종 heap context | [`locator_sr.c:5064`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L5064) | `real_class_oid/real_hfid`로 context 구성, 5079에서 heap 호출 |
| context 정보 | [`heap_file.h:274`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.h#L274) | class/HFID/RECDES/scan cache가 있으며 attrinfo나 pruning context는 없음 |
| child 직접 입력 검증 | [`partition.c:3666`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/partition.c#L3666) | `DB_PARTITION_CLASS`이면 지정 child와 선택된 child가 다를 때 오류 |
| 파티션 키 읽기 | [`partition.c:3500`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/partition.c#L3500) | 중간 RECDES에서 실제 값을 읽을 수 있어야 함 |
| INSERT index/FK | [`locator_sr.c:5196`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L5196) | heap 호출 뒤 index, 이어 FK 검사. 일반 INSERT에서 이 순서는 늦은 OOS 기록의 장애물이 아님 |
| UPDATE 목적지 | [`locator_sr.c:5991`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L5991) | source child에서 다른 child로 갈 수 있음 |
| UPDATE index/FK | [`locator_sr.c:6045`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L6045) | 같은 heap의 UPDATE는 index/FK를 먼저 처리하고 이후 heap_update_logical 호출 |
| 주소 선할당 | [`heap_file.c:5693`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L5693) | data가 없는 REC_ASSIGN_ADDRESS도 heap_insert_logical을 호출함 |
| multipage 판정 | [`heap_file.c:25083`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L25083) | heap_insert_handle_multipage_record 전에 최종 compact 크기를 정할 필요 |

## Constraints to resolve before implementation

1. **OOS 함수 호출만 skip하면 충분하지 않다.** 기존 column writer는 OOS plan에 선택된 컬럼을 stub으로 기록한다. chain을 쓰지 않은 채 그 plan을 사용하면 파티션 평가기가 실제 값을 읽을 수 없다. 목적지가 확정될 때까지 모든 값이 inline인 RECDES를 유지하거나, 별도 payload와 그것을 읽는 경로를 제공해야 한다.
2. **class의 종류와 목적지 확정 여부가 다르다.** UPDATE는 source child A에서 destination child B로 이동할 수 있다. “child면 바로 기록”이라는 조건만으로 올바른 소유 heap을 보장하지 못한다. 같은 heap UPDATE는 heap_insert_logical을 거치지 않으므로 별도 위치도 필요하다.
3. **full-inline RECDES는 검토 가능한 대안이다.** 기존 partition/index reader가 실제 값을 계속 읽을 수 있다. 그러나 큰 중간 버퍼를 보유하는 비용과 최종 compaction을 구현해야 한다. 아직 이 대안을 채택하지 않았다.
4. **최종 버퍼를 locator도 보아야 한다.** heap 호출에서 새 버퍼를 할당해 context 포인터만 바꾸면, 이후 원래 RECDES로 읽는 index/FK 처리가 다른 행 표현을 볼 수 있다. in-place 재작성 또는 명시적인 결과 전달·수명 계약을 정해야 한다.
5. **두 번의 변환은 부수 효과를 중복시킬 수 있다.** 기존 header writer는 CHN을 변경하고, column writer는 increment와 외부 LOB copy를 처리한다. 같은 attrinfo로 transform을 두 번 부르는 방식은 이 효과와 MVCC/header 보존을 검토해야 한다. 저장 바이트를 직접 compact하는 방향도 비교 대상이다.
6. **probe와 내부 행을 구분해야 한다.** REPLACE/ODKU는 실제 쓰기 여부가 정해지기 전에 RECDES를 만든다. parent만 skip하면 normal/child의 probe OOS 기록은 남는다. 이미 OOS OID fixup이 끝난 replica 행, 내부/catalog 행, 주소 선할당도 일괄 재외부화하면 안 된다.
7. **loader는 원래 DB_VALUE를 유지하지 않는다.** 기존 loader는 owning record_descriptor를 큐에 넣고 각 입력 행의 DB_VALUE를 정리한다. full-inline RECDES는 수명 관점의 후보지만, OOS 전 길이로 batch page packing을 수행하면 경로와 효율이 달라진다.
8. **publication과 rollback은 저장 시점에 맞춰야 한다.** OOS OID와 replication LSA queue는 함께 관리된다. 늦은 쓰기는 관련 publication 소비 이전이며 실패 롤백 안에 있어야 한다. 상태 초기화가 디스크 변경의 롤백을 대신하지 않는다.

추가 근거:

- REPLACE/ODKU probe: [`query_executor.c:12077`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/query_executor.c#L12077), [`12315`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/query_executor.c#L12315).
- loader 입력 수명: [`load_server_loader.cpp:706`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/loaddb/load_server_loader.cpp#L706); batch packing: [`locator_sr.c:14055`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L14055).
- stub 기록과 LOB 처리: [`heap_file.c:13540`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L13540); CHN/increment: [`13314`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L13314).
- publication reset: [`heap_oos.cpp:611`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_oos.cpp#L611); replication 소비: [`locator_sr.c:8174`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L8174).

## Follow-up: representation and common write boundary

두 번의 DB_VALUE 직렬화는 필수가 아니다. 기존 [`heap_record_replace_oos_oids()`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_oos.cpp#L344)는 VOT와 저장 바이트로 OOS stub을 원래 값으로 확장한다. 반대 방향으로 inline 값 구간을 OOS에 쓰고 stub으로 교체하는 구현을 검토할 수 있다. 기존 함수는 확장 전용이므로 그대로 재사용할 수 있다는 뜻은 아니다.

이 후보는 header의 CHN/MVCC 정보와 fixed/NULL bitmap을 보존하고 VOT 폭·정렬·마지막 entry를 올바르게 재구성해야 한다. [`heap_attrinfo_determine_disk_layout()`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L12800)의 STORAGE 정책과 선택 순서를 복제하면 코드 단순화 목적에 어긋난다. 길이 수집과 선택 정책을 분리해 공유 가능한지 구현량으로 평가할 필요가 있다.

공통 OOS 기록 함수를 부를 후보 지점은 INSERT의 목적지 선택 뒤 heap context 생성 전, 같은 heap UPDATE의 목적지 선택 뒤 index 갱신 전이다. 이동 UPDATE는 목적지 INSERT 경로를 사용한다. UPDATE가 full-inline 행을 유지하면 index reader가 반드시 OOS finalization 뒤에만 동작해야 하는 것은 아니지만, 앞서 완성하는 경계가 소비자 계약을 단순하게 유지하는 후보다.

SQL 호출부의 명시적인 opt-in으로 제한된 실험을 격리할 수 있다. 기존 완성된 replica 행이나 주소 선할당을 pending 행으로 추측해서는 안 된다. 이 opt-in plumbing도 복잡도 비교에 포함한다. 정상 INSERT/UPDATE 일부만 구현하고 loader·복제·REPLACE/ODKU·재평가 경로가 빠진 결과를 PR #7927 전체보다 단순하다고 단정하지 않는다.

## Relationship to earlier designs

기존 PR #7927의 `heap_prepared_row`가 유일한 해결책이라는 결론은 이 조사에서 도출되지 않는다. 새 POC는 root의 초기 기록을 피하면서, 기존 reader를 유지할 수 있는 더 좁은 계약이 가능한지 검토한다.

기존 [PR #7600 ADR](../../docs/adr/0001-pr7600-effective-key-routing.md)은 effective-key routing에 관한 별도 범위의 방향이다. 이 문서로 해당 ADR을 변경하거나 새 대안을 accepted 상태로 만들지 않는다. [현재 설계 질문](map.md)의 응답을 바탕으로 다음 결정을 진행한다.
