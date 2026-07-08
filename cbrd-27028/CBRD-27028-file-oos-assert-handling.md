# CBRD-27028 FILE_OOS assert 처리 개선

https://jira.cubrid.org/browse/CBRD-27028

## 한 줄 요약

OOS 파일이 있는 데이터베이스에서 `diagdb`, `spacedb`, `checkdb` 같은 진단 유틸리티가 `FILE_OOS` 를 만나도 debug assertion 으로 중단되지 않게 한다.

## 먼저 알아야 할 용어

- OOS: 큰 가변 길이 컬럼 값을 heap record 안에 모두 넣지 않고, 별도 OOS file 에 저장하는 기능이다.
- `FILE_OOS`: OOS 데이터를 저장하는 파일 타입이다.
- file tracker: 데이터베이스 안의 파일들을 순회하면서 검사하거나 통계를 내는 경로다.
- owner metadata: 어떤 table/class 가 이 OOS file 을 소유하는지 알려 주는 정보다. 현재 `FILE_OOS` descriptor 에는 이 정보가 없다.

## 왜 고치나

OOS 기능이 생기면서 `FILE_OOS` 파일도 만들어진다. 그런데 기존 파일 관리자 코드의 일부 진단 경로는 `FILE_OOS` 를 아직 제대로 처리하지 못했다.

그래서 OOS 파일이 있는 DB 에서 다음 유틸리티를 실행하면 debug 빌드에서 assertion 으로 멈출 수 있었다.

- `diagdb`: 파일 descriptor 나 capacity 정보를 출력하는 경로
- `spacedb`: 파일별 공간 사용량을 집계하는 경로
- `checkdb`: file tracker 를 순회하면서 파일을 검사하는 경로

이번 변경의 목적은 새 기능을 크게 추가하는 것이 아니다. 진단 유틸리티가 OOS 파일을 만나도 죽지 않게 만드는 안정화 패치다.

## 변경 전과 변경 후

AS-IS:

- `FILE_OOS` 를 만나면 일부 경로에서 `assert (false)` 또는 `assert_release (false)` 로 중단될 수 있었다.
- `checkdb` 의 online file tracker 순회에서 OOS 파일을 일반 파일처럼 반환하면, owner 정보가 없어서 안전하게 lock 을 잡을 수 없었다.

TO-BE:

- `diagdb` 는 `FILE_OOS` 를 간단히 `OOS file` 로 출력한다.
- online `checkdb` 의 보호 단계는 owner 정보가 없는 OOS 항목을 caller 에게 반환하지 않고 건너뛴다.
- `spacedb` 는 OOS 페이지를 일단 heap totals 에 포함해서 집계한다.
- 결과적으로 `FILE_OOS` 때문에 진단 유틸리티가 assertion 으로 종료되지 않는다.

## 이번 PR 의 범위

이번 PR 은 CBRD-27028 의 "FILE_OOS 단순 assert 오류"만 처리한다.

아래 작업은 이번 PR 에 포함하지 않는다.

- `spacedb` 에 `SPACEDB_OOS_FILE` 같은 OOS 전용 출력 행을 추가하는 작업
- `FILE_OOS` descriptor 에 owner heap/class 정보를 저장하는 작업
- OOS 공간 사용량을 table 별로 귀속해서 보여 주는 작업
- online `checkdb` 가 owner lock 을 잡고 OOS file table 자체를 검사하게 만드는 작업

위 항목들은 descriptor 형식, network packing, 출력 라벨, message catalog, QA answer 까지 함께 바뀌는 별도 설계가 필요하다.

## 구현 내용

수정 파일은 `src/storage/file_manager.c` 하나다.

### 1. `file_header_dump_descriptor()`

`FILE_OOS` case 에 있던 `assert (false)` 를 제거한다.

대신 다음처럼 간단한 descriptor 만 출력한다.

```text
OOS file
```

generic file dump 와 capacity dump 는 이미 VFID, page count, file type 을 출력한다. 현재 OOS file header 에는 class owner 정보가 없으므로, 없는 정보를 억지로 만들어 출력하지 않는다.

### 2. `file_tracker_get_and_protect()`

online `checkdb` 에서 file tracker 항목을 보호하는 단계가 있다. 이 단계에서 `FILE_OOS` 는 caller 에게 반환하지 않고 조용히 건너뛴다.

처리는 다음과 같다.

- `NO_ERROR` 를 반환한다.
- `*stop` 은 설정하지 않는다.
- 별도 로그는 남기지 않는다.
- 다음 file tracker 항목으로 계속 진행한다.

이렇게 하는 이유는 현재 `FILE_OOS` descriptor 에 owner class OID 가 없기 때문이다. owner 를 모르면 heap 이나 btree 처럼 class lock 을 잡을 수 없다.

lock 없이 OOS VFID 를 반환하면 다음 문제가 생길 수 있다.

- online `checkdb` 와 `DROP TABLE` 이 동시에 실행될 때 stale VFID 를 검사할 위험이 있다.
- 반환된 VFID 가 다음 순회의 resume cursor 로 쓰이는데, 그 사이 파일이 tracker 에서 사라지면 다음 재개 지점에서 `assert_release (false)` 로 실패할 수 있다.

skip 로그도 남기지 않는다. heap 경로의 `ER_CANNOT_CHECK_FILE` notification 은 일시적인 lock 충돌을 알리는 용도다. OOS 처럼 owner 정보가 없어서 항상 건너뛰는 경우에 재사용하면 의미가 맞지 않는다.

추가로, `FILE_UNKNOWN_TYPE` 순회 중 OOS 항목을 만나도 assertion 없이 지나간다.

offline, 즉 SA mode `checkdb` 는 `file_tracker_map()` 경로를 사용한다. 이 경로에서는 OOS file table 을 계속 전수 검사한다.

### 3. unreachable guard 는 유지

desired type 필터와 class OID extraction switch 에 있는 `FILE_OOS` 의 `assert (false)` 는 그대로 둔다.

이 두 곳은 현재 crash 경로가 아니라 도달하면 안 되는 방어 코드다.

이유는 다음과 같다.

- 유일한 caller 인 `file_tracker_check()` 는 desired type 으로 `FILE_UNKNOWN_TYPE` 만 넘긴다.
- 보호 단계에서 `FILE_OOS` 를 먼저 skip 하므로, 이후 class OID extraction switch 에 도달하지 않는다.

따라서 이 assert 들은 실제 유틸리티 중단 원인이 아니라 unreachable guard 로 남긴다.

### 4. `file_tracker_item_spacedb()`

`FILE_OOS` 를 만나면 발생하던 `assert_release (false)` 를 제거한다.

현재는 OOS 공간을 `SPACEDB_HEAP_FILE` 에 포함해서 집계한다.

이유는 OOS 가 table-owned storage 이기 때문이다. 하지만 현재 `SPACEDB_FILE_TYPE` 에는 OOS 전용 카테고리가 없다.

OOS 전용 카테고리를 추가하려면 다음을 모두 같이 바꿔야 한다.

- `SPACEDB_FILE_TYPE`
- `SPACEDB_FILE_COUNT` packing
- `util_cs.c` 출력 라벨
- message catalog
- QA answer

이번 PR 은 assertion 안정화가 목적이므로, 출력 protocol 을 바꾸지 않고 heap totals 에 임시 포함한다.

### 5. heap 전용 dump helper 는 건드리지 않음

`file_tracker_dump_all_heap()` 와 `file_tracker_dump_all_heap_capacities()` 는 heap 전용 helper 를 호출한다.

이 함수들은 이름과 역할이 heap 전용이므로, 여기에 OOS 를 억지로 끼워 넣지 않는다.

## 리뷰할 때 볼 점

리뷰에서는 아래 세 가지를 보면 된다.

- `FILE_OOS` 를 heap 으로 가장하지 않고, 각 utility path 에서 명시적으로 처리하는가?
- owner descriptor 가 없는 현재 형식에서 OOS file tracker 항목을 lock 없이 caller 에게 반환하지 않는가?
- `spacedb` 에 새 출력 카테고리를 만들지 않고 heap totals 에 임시 포함하는 판단이 이번 안정화 범위에 맞는가?

## 테스트 계획과 결과

커밋 기록 기준으로 다음 검증을 완료했다.

- `git diff --check` 통과
- debug GCC preset 빌드 성공
- OOS 행이 있는 DB 를 만든 뒤 다음 유틸리티가 `FILE_OOS` assertion 없이 끝나는 것을 확인
  - `diagdb` file table 출력
  - `diagdb` capacity 출력
  - `spacedb` file accounting
  - `checkdb` file tracker iteration
- targeted CTP `utility_19` 성공

주의할 점:

- online `checkdb` 의 OOS file table 검사는 owner descriptor 후속 작업 전까지 의도적으로 수행하지 않는다.
- offline SA mode `checkdb` 는 OOS file table 을 검사한다.
- `cbrd_26527`, `tbl_enc_14` 는 아직 실패하지만, 원인은 `FILE_OOS` assertion 또는 fatal 오류가 아니라 별도 expected-output 가정 차이다.

## 남은 제한 사항

이번 PR 이후에도 다음 제한은 남는다. 모두 이번 범위 밖이다.

- `spacedb` 에 OOS 전용 행을 추가하려면 `SPACEDB_FILE_TYPE`, network packing, 출력 라벨, message catalog, QA answer 를 함께 바꿔야 한다.
- OOS 공간을 table 별로 보여 주려면 `FILE_OOS` descriptor 에 owner heap/class metadata 를 저장해야 한다.
- owner metadata 가 들어가기 전까지 online `checkdb` 는 OOS file table 자체를 검사하지 않는다.
- owner descriptor, online checkdb 보호, `SPACEDB_OOS_FILE` 출력 행과 table 귀속 표시는 umbrella JIRA 티켓 한 건으로 묶어 추적한다.
