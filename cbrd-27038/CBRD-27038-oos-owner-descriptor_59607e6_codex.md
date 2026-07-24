# [CBRD-27038] OOS 파일 owner descriptor 및 online checkdb 보호

https://jira.cubrid.org/browse/CBRD-27038

| 구분 | 값 |
|---|---|
| CUBRID engine HEAD | `59607e6075` (`59607e6`) |
| Engine HEAD title | `[CBRD-27038] Use dedicated OOS file descriptor` |
| 기준 branch | `feat/oos` |
| 작업 branch | `CBRD-27038-oos-file-belongs` |

## Purpose

OOS 파일은 테이블 heap 파일과 1:1로 대응하지만, AS-IS에서는 OOS 파일 header의 `FILE_DESCRIPTORS` 가
byte-zero 상태여서 파일 자체만 보고 소유 테이블을 역추적할 수 없었다.

- **AS-IS:** OOS 파일에 owner HFID/class OID가 없어 `diagdb` 가 소유 테이블을 표시하지 못하고, online
  `checkdb` 는 class lock 없이 파일을 검사할 수 없어 OOS file table을 건너뛴다.
- **TO-BE:** 새 OOS 파일에 owner HFID/class OID를 저장하고, 진단 출력에 owner를 표시하며, online
  `checkdb` 는 `SCH_S_LOCK` 으로 보호한 OOS file table을 검사한다.

이 제약은 두 경로에 영향을 주었다.

- `diagdb` 의 file descriptor 출력은 OOS 파일의 테이블명과 부모 HFID를 표시하지 못했다.
- online `checkdb` 의 interruptible file tracker 순회는 `DROP TABLE` 과 겹칠 수 있으므로 mutable file을 class
  lock으로 보호해야 하지만, OOS 파일에는 lock 대상 class OID가 없었다. 따라서 CBRD-27028에서는 OOS 파일을
  무조건 건너뛰어 assertion과 stale VFID 접근을 피했다.

TO-BE에서는 새 OOS 파일이 부모 HFID와 class OID를 descriptor에 저장한다. 진단 출력은 이 owner 정보를
사용하고, online file tracker 순회는 class에 `SCH_S_LOCK` 을 조건부로 획득한 경우에만 OOS VFID를 반환한다.
그 결과 online `checkdb` 가 OOS file table을 안전하게 검사할 수 있다.

이 변경은 OOS 전용 `FILE_OOS_DES` 를 추가하고 `FILE_DESCRIPTORS.heap_oos` 멤버로 접근한다.
`FILE_DESCRIPTORS` union의 고정 크기인 64바이트는 바뀌지 않으므로 descriptor layout 확대나 disk
compatibility version 변경은 없다.

## Implementation

### OOS 생성 시 owner 정보 저장

production `oos_create_file()` 은 부모 `HFID` 와 class `OID` 를 입력받아 다음 정보를
OOS 전용 `descriptor.heap_oos` 에 기록한다.

```text
FILE_OOS descriptor
  ├─ heap_oos.hfid      = 소유 heap의 HFID
  └─ heap_oos.class_oid = 소유 class의 OID
```

OOS 파일의 실제 lazy-create 지점인 `heap_oos_find_vfid()` 는 이미 heap header를 fix한 상태이므로, 호출자가
전달한 HFID와 `heap_hdr->class_oid` 를 `oos_create_file()` 에 넘긴다. 저수준 OOS unit test는 heap 없이 OOS
storage만 독립적으로 시험하므로 `CUBRID_UNIT_TEST_ENABLED` overload가 non-null synthetic owner를
사용한다. production과 test 생성 경로 모두 owner descriptor를 기록한다.

### diagdb descriptor 출력

`file_header_dump_descriptor()` 의 `FILE_OOS` 처리는 새 descriptor의 class OID로 테이블명을 찾고,
class OID/테이블명과 부모 HFID를 다음 형태로 출력한다.

```text
CLASS_OID: <volid>|<pageid>|<slotid> (<table-name>), OOS for HFID: <volid>|<fileid>|<hpgid>
```

이는 기존 heap overflow descriptor가 class name과 `Overflow for HFID` 를 출력하는 방식과 같은 owner
정보를 사용한다.

### online checkdb 보호

`file_tracker_get_and_protect()` 는 `FILE_OOS` 를 더 이상 무조건 skip하지 않는다. OOS file header를 fix해
`descriptor.heap_oos.class_oid` 를 읽은 뒤, 다른 table-owned mutable file과 같은 조건부 class lock
흐름으로 보낸다.

```text
FILE_OOS tracker item
  -> descriptor에서 class OID 읽기
  -> class에 SCH_S_LOCK을 LK_COND_LOCK으로 요청
     ├─ 성공: OOS VFID 반환 -> file_table_check()
     └─ 실패: ER_CANNOT_CHECK_FILE notification 후 해당 파일만 skip
```

`file_tracker_check()` 는 `FILE_UNKNOWN_TYPE` 으로 모든 파일을 순회한다. 이 경우 lock mode는
`SCH_S_LOCK` 이며, 다음 iteration이 tracker page를 다시 fix한 뒤 이전 class lock을 해제한다. 따라서
caller가 OOS file table을 검사하고 resume cursor를 사용하는 동안 class drop이 해당 파일을 제거하지
못한다. exact `FILE_OOS` 순회도 같은 보호 계약을 갖도록 기존 unreachable assertion을 제거했다.

### 호환 범위

`feat/oos` 는 아직 릴리스되지 않았으므로 ownerless OOS 파일과의 disk compatibility 경로를 두지 않는다.
모든 `FILE_OOS` descriptor는 `heap_oos.hfid` 와 `heap_oos.class_oid` 를 가진다는 단일 형식만 지원한다.
따라서 byte-zero descriptor 판정, owner-unavailable 진단 출력, ownerless online-scan skip은 구현하지
않는다.

### 테스트

`OosOwnerDescriptorSupportsDiagnosticsAndProtectedIteration` SERVER_MODE test를 추가했다.

1. `_db_user` class에 새 heap을 만들고 lazy OOS 파일 생성을 유도한다.
2. `file_descriptor_get()` 으로 부모 HFID와 class OID가 정확히 저장됐는지 확인한다.
3. file tracker dump에서 class OID, `_db_user` 테이블명, 부모 HFID가 한 줄에 정확히 출력되는지 확인한다.
4. exact `FILE_OOS` interruptible iteration으로 반환되는 모든 OOS 파일에 locked class OID가 있는지
   확인하고, 대상 OOS 파일의 OID가 소유 class와 일치하는지 확인한다.
5. 별도 DDL transaction이 `DROP TABLE` 에서 사용하는 `SCH_M_LOCK` 을 조건부로 요청했을 때, OOS
   iteration의 `SCH_S_LOCK` 이 유지되는 동안 거부되고 iteration 종료 후에는 허용되는지 확인한다.
6. `file_tracker_check()` 가 `DISK_VALID` 로 OOS file table 검사를 완료하는지 확인한다.

## Remarks

### 검증 결과

- debug GCC 전체 build 성공
- focused SERVER_MODE owner descriptor test 성공
- OOS CTest suite: 24/24 성공, 실패 0
- `git diff --check` 성공
- source HEAD와 `origin/feat/oos` 의 기준 관계 확인: base 대비 2 commits

unit test는 online checkdb transaction의 `SCH_S_LOCK` 과 별도 DDL transaction의 `SCH_M_LOCK` 을 직접
충돌시킨다. OOS VFID를 검사하는 동안 schema modification lock이 거부되고, iteration이 보호 lock을
해제한 뒤에는 같은 lock이 획득되는 수명을 검증했다. 별도 client process에서 `DROP TABLE` 명령 자체를
동시에 실행해 wait/완료 순서를 관찰하는 end-to-end scenario는 수행하지 않았으므로 QA 보강 항목으로
남긴다.

### 테스트 계획

```bash
# Standard debug build with unit tests enabled
./build.sh -m debug -c "-DUNIT_TESTS=ON"

# Run the OOS unit/integration tests from the configured build tree
ctest --test-dir <debug-build-directory>/unit_tests/oos --output-on-failure
```

추가 QA 시나리오:

1. OOS value가 저장된 테이블을 만든다.
2. `diagdb` file descriptor 출력에서 테이블명과 부모 HFID를 확인한다.
3. online `checkdb` 를 실행하는 동안 같은 테이블에 `DROP TABLE` 을 시도한다.
4. checkdb가 OOS file table을 검사하는 동안 drop이 class lock 계약에 따라 안전하게 직렬화되는지 확인한다.
### 범위

이번 변경은 OOS owner descriptor, diagnostic owner 출력, online checkdb 보호까지만 포함한다.
`spacedb` 의 별도 `SPACEDB_OOS_FILE` 카테고리와 table별 OOS 공간 표시는 output/protocol 변경이 필요한
별도 범위다. 현재 OOS page는 기존과 같이 heap totals에 합산된다.
