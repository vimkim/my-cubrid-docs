# [CBRD-27006] PR #7391 publication 상태 리뷰 쉽게 이해하기

- 대상 PR: https://github.com/CUBRID/cubrid/pull/7391
- 대상 리뷰: https://github.com/CUBRID/cubrid/pull/7391#discussion_r3586720978
- 리뷰 작성자: Greptile bot
- 확인한 PR HEAD: `840e5e904d51795560635cbf5d9c46123a927aa3`
- 확인일: 2026-07-16

## 한 문장 결론

리뷰가 발견한 **"새 OOS 작업을 시작하기 전에 이전 작업의 임시 목록을 비워야 한다"** 는 방향은
맞다. 하지만 이를 바로 데이터 손상으로 이어지는 **P1 문제라고 판단할 근거는 부족하고**, 리뷰가
제안한 위치로 초기화 코드를 옮기는 것만으로는 모든 실패 경로를 막지 못한다.

즉, 이 리뷰는 다음과 같이 평가하는 것이 적절하다.

> **문제의 냄새는 제대로 찾았지만, 위험도는 과장했고 수정 범위는 충분히 넓게 보지 못했다.**

## 리뷰가 무슨 말을 하는가?

Greptile 리뷰를 쉬운 말로 바꾸면 다음과 같다.

1. OOS 값을 저장할 때는 나중에 replication에서 사용할 두 개의 임시 목록을 만든다.
2. 새 OOS 저장 작업을 시작하기 전에 이 목록들을 비워야 한다.
3. 그런데 현재 코드는 몇 가지 실패할 수 있는 작업을 먼저 수행한 뒤 목록을 비운다.
4. 앞선 작업에서 오류가 발생하면 목록을 비우는 코드까지 도달하지 못한다.
5. 그러면 이전 OOS 작업의 정보가 목록에 남을 수 있다.

리뷰가 말하는 두 임시 목록은 다음과 같다.

| 임시 상태 | 쉬운 의미 | 실제 용도 |
|---|---|---|
| `thread_p->oos_oids` | 방금 저장한 OOS 값들의 주소 목록 | 어떤 head OOS OID에 대한 replication 기록을 만들지 결정한다. |
| `tdes->oos_insert_lsa_queue` | 각 OOS 저장 로그의 위치 목록 | replication 기록이 원래 OOS WAL 로그를 가리키도록 연결한다. |

이 두 목록을 합쳐서 이 문서에서는 **OOS insert publication 상태**라고 부른다.

여기서 publication은 데이터를 사용자에게 공개하거나 즉시 복제 서버로 보내는 동작을 뜻하지 않는다.
**나중에 replication 기록을 만들 수 있도록, 방금 저장한 OOS 결과를 임시 목록에 등록하는 것**을 뜻한다.

### 코드 용어를 아주 쉽게 풀면

| 코드 용어 | 쉬운 뜻 |
|---|---|
| `thread_p` | 현재 요청을 처리하는 worker thread의 작업 가방이다. `oos_oids` 같은 요청 처리용 임시 상태가 들어 있다. |
| `tdes` | 현재 transaction의 상태를 모아 둔 transaction descriptor다. |
| WAL | 데이터 변경 내용을 먼저 기록하는 database log다. 장애 복구에도 사용한다. |
| LSA | Log Sequence Address의 약자다. WAL 안에서 특정 로그가 있는 위치, 즉 로그 주소다. |
| `clear()` | vector나 queue 안의 항목을 모두 지워 빈 목록으로 만드는 동작이다. OOS 데이터 자체를 삭제하는 동작은 아니다. |
| `S_ERROR` | 해당 작업이 실패했다는 함수 반환값이다. |

특히 `clear()`를 오해하면 안 된다. 다음 두 동작은 전혀 다르다.

```text
oos_oids.clear()
  = 임시 주소 목록만 비움
  = OOS file에 저장된 실제 값을 삭제하는 동작이 아님
```

## OOS insert publication이 왜 필요한가?

### 먼저 OOS란?

OOS는 큰 variable column 값을 heap record 밖의 OOS file에 따로 저장하는 기능이다. heap record에는
큰 값 전체 대신 16바이트 OOS inline stub이 들어간다.

```text
heap record
[ id | 작은 값 | OOS inline stub ]
                       |
                       v
                 OOS file의 큰 값
```

OOS inline stub에는 다음 정보가 있다.

```text
[ head OOS OID | 전체 값 길이 ]
```

여기서 head OOS OID는 OOS value chain의 첫 번째 OOS chunk record 위치를 가리킨다.

### replication에는 OOS 정보도 필요하다

원본 서버에서 OOS 값을 저장했다면 복제 서버도 같은 논리 값을 다시 만들어야 한다. 이를 위해 원본
서버는 다음 정보를 replication 기록으로 남긴다.

```text
방금 어떤 OOS 값을 저장했는가?
그 OOS 저장에 대응하는 WAL 위치는 어디인가?
```

이를 위해 코드가 OOS OID와 LSA를 잠시 모아 둔다.

일상적인 비유로 보면 다음과 같다.

```text
oos_oids                 = 배송할 물건의 주소표
oos_insert_lsa_queue     = 각 물건에 대응하는 접수 영수증
replication 처리          = 주소표와 영수증을 순서대로 짝지어 발송
```

주소표와 영수증의 개수와 순서가 맞아야 올바른 OOS 값을 복제할 수 있다.

## 왜 새 작업 전에 목록을 비워야 하는가?

예를 들어 첫 번째 row의 OOS 값을 성공적으로 저장한 직후 목록이 다음과 같다고 하자.

```text
oos_oids             = [row 1의 OOS OID]
oos_insert_lsa_queue = [row 1의 OOS 로그 LSA]
```

이후 두 번째 row의 OOS 저장을 시작한다. 두 번째 작업은 자기 정보만 목록에 남겨야 한다.

```text
clear
  -> oos_oids             = []
  -> oos_insert_lsa_queue = []

row 2 저장
  -> oos_oids             = [row 2의 OOS OID]
  -> oos_insert_lsa_queue = [row 2의 OOS 로그 LSA]
```

초기화하지 않으면 row 1과 row 2의 상태가 섞일 가능성을 계속 생각해야 한다.

```text
초기화하지 않은 상태
  -> oos_oids = [row 1의 OOS OID, row 2의 OOS OID]
```

따라서 각 논리 OOS insert는 깨끗한 publication 상태에서 시작하는 편이 안전하다.

## 현재 코드는 어떤 순서로 실행되는가?

현재 전체 흐름은 두 함수에 나뉘어 있다.

```text
heap_attrinfo_insert_to_oos()                    heap_file.c
  |
  +-- payload/request vector 공간 준비           실패 가능
  +-- OOS 대상 값을 byte payload로 직렬화        실패 가능
  |
  +-> heap_oos_insert_serialized_values()         heap_oos.cpp
        |
        +-- heap_get_class_info()                 실패 가능
        +-- heap_oos_find_vfid(create=true)       실패 가능
        +-- transaction descriptor 찾기
        +-- publication 상태 clear                현재 초기화 위치
        +-- oos_insert_many()
```

핵심은 `clear`보다 앞에 이미 여러 개의 실패 가능한 작업이 있다는 점이다.

## 리뷰가 지적한 구체적인 실패 경로

리뷰는 특히 다음 두 함수를 지적한다.

- `heap_get_class_info()`
- `heap_oos_find_vfid()`

현재 `heap_oos_insert_serialized_values()`의 순서는 다음과 같다.

```text
1. heap_get_class_info()
2. heap_oos_find_vfid()
3. transaction descriptor 찾기
4. oos_insert_lsa_queue.clear()
5. oos_oids.clear()
6. oos_insert_many()
```

1번이나 2번에서 실패하면 함수는 즉시 `S_ERROR`를 반환한다. 따라서 4번과 5번이 실행되지 않는다.

```text
이전 상태가 남아 있음
       |
       v
heap_get_class_info() 실패
       |
       +-- 즉시 return
       |
       X  clear까지 도달하지 못함
```

여기까지는 리뷰의 사실 판단이 맞다.

## 그렇다면 즉시 잘못된 replication이 발생하는가?

현재 확인한 코드만으로는 그렇다고 보기 어렵다.

publication 상태가 남는 것과 그 상태가 실제로 잘못 소비되는 것은 서로 다른 단계다.

```text
stale 상태가 남음
       |
       |  이것만으로는 아직 데이터 오류가 아님
       v
어떤 후속 경로가 stale 상태를 소비함
       |
       v
잘못된 replication 기록 생성 가능
```

이번 실패 경로에서는 다음 안전 장치가 있다.

1. 오류가 나면 새 OOS heap record 생성까지 진행하지 못한다.
2. 따라서 실패한 새 record에 대한 OOS replication 기록도 만들지 않는다.
3. `oos_insert_lsa_queue`는 `RVREPL_OOS_INSERT` 또는 `RVREPL_DUMMY_OOS_RECORD`를 만들 때만 소비된다.
4. 다음 OOS 작업이 성공 경로에 들어가면 `oos_insert_many()` 호출 전에 두 목록을 다시 비운다.
5. `oos_insert_many()`가 일부 값을 publication한 뒤 실패하면 함수 내부에서 두 목록을 비운다.

따라서 리뷰가 보여 준 것은 **상태 수명 관리가 깔끔하지 않다는 사실**이지, 현재 경로에서 즉시 데이터
손상이나 잘못된 replication이 발생한다는 재현 시나리오는 아니다.

## P1이라는 평가는 타당한가?

### 결론: 현재 근거만으로는 P1이 아니다

P1이라면 일반적으로 다음 중 하나를 보여 줄 수 있어야 한다.

- 데이터 손상
- 잘못된 replication 결과
- 서버 장애 또는 광범위한 기능 중단
- 정상 사용 중 높은 확률로 발생하는 심각한 오류

하지만 이 리뷰는 다음 연결 고리를 제시하지 않았다.

```text
early return
  -> stale publication 상태 잔존
  -> 실제 후속 consumer가 그 상태를 소비
  -> 잘못된 OOS replication 기록 생성
```

첫 번째 화살표는 맞지만, 두 번째와 세 번째 화살표가 현재 코드 흐름에서 증명되지 않았다.

그러므로 이 문제는 다음과 같이 보는 편이 적절하다.

| 관점 | 평가 |
|---|---|
| 방어적 invariant 위반 | 맞음 |
| 유지보수 위험 | 있음 |
| 미래 코드 변경 시 오류 가능성 | 있음 |
| 현재 재현 가능한 데이터 손상 | 확인되지 않음 |
| P1 | 근거 부족 |
| 현실적인 우선순위 | P2 이하, 재현 가능한 consumer 경로가 없으면 P3도 가능 |

## `1a278e978` 커밋과 정말 같은 문제인가?

리뷰는 과거 `1a278e978` 커밋이 같은 문제를 해결했다고 말한다. 방향은 비슷하지만 정확한 설명은 아니다.

그 커밋이 바꾼 내용은 다음과 같다.

```text
변경 전
  request용 메모리 준비/직렬화
  publication 상태 clear
  oos_insert_many()

변경 후
  publication 상태 clear
  request용 메모리 준비/직렬화
  oos_insert_many()
```

즉, `1a278e978`은 clear를 **request 준비와 값 직렬화보다 앞으로** 옮겼다.

하지만 그 당시에도 clear는 다음 함수들보다 뒤에 있었다.

- `heap_get_class_info()`
- `heap_oos_find_vfid()`

따라서 리뷰의 다음 표현은 정확하지 않다.

> 과거 커밋이 transaction descriptor를 얻자마자 clear하여 모든 fallible call보다 앞에 두었다.

정확히 말하면 과거 커밋은 **일부 fallible call, 특히 request 준비와 직렬화보다 앞에** clear를
배치했다.

## 현재 리팩터링이 만든 더 넓은 문제

현재 코드는 값 직렬화를 `heap_oos_insert_serialized_values()` 밖으로 옮겼다.

```text
heap_attrinfo_insert_to_oos()
  +-- reserve()                         실패 가능
  +-- serialize values                  실패 가능
  +-> heap_oos_insert_serialized_values()
        +-- class/VFID lookup           실패 가능
        +-- clear
        +-- insert
```

따라서 Greptile이 제안한 것처럼 `heap_oos_insert_serialized_values()` 안에서 clear를 class lookup보다
앞으로 옮겨도 다음 실패 경로는 여전히 남는다.

```text
reserve 실패
  -> helper를 호출하지 못함
  -> helper 안의 clear도 실행되지 않음

직렬화 실패
  -> helper를 호출하지 못함
  -> helper 안의 clear도 실행되지 않음
```

이것이 리뷰 제안만 그대로 적용해서는 부족한 이유다.

## 더 완전한 수정 원칙

권장 invariant는 다음과 같다.

> **하나의 논리 OOS insert 준비를 시작할 때, 첫 번째 실패 가능한 단계보다 먼저 기존 publication 상태를
> 비운다.**

원하는 흐름은 다음과 같다.

```text
논리 OOS insert 시작
  |
  +-- transaction descriptor 확인
  +-- publication 상태 clear
  |
  +-- vector reserve                    실패해도 상태는 깨끗함
  +-- 값 직렬화                         실패해도 상태는 깨끗함
  +-- class 정보 조회                   실패해도 상태는 깨끗함
  +-- OOS VFID 조회/생성                실패해도 상태는 깨끗함
  +-- oos_insert_many()
```

중요한 것은 단순히 코드 두 줄을 몇 줄 위로 옮기는 것이 아니다. **논리 작업의 시작 경계가 어디인지**를
정하고, 그 경계에서 상태를 초기화해야 한다.

구현 구조는 다음 선택지 중 하나로 정리할 수 있다.

1. OOS 모듈이 publication 상태 초기화 helper를 제공하고, `heap_attrinfo_insert_to_oos()`가 직렬화 전에
   호출한다.
2. OOS insert 준비를 더 높은 수준의 OOS helper가 모두 소유하도록 API 경계를 다시 묶는다.
3. 모든 consumer가 성공과 실패 뒤 상태를 반드시 비우도록 바꾼다.

이 중에서는 **1번이 가장 작고 명시적인 수정**이다. `heap_file.c`가 transaction 내부 구조를 직접 더
많이 알게 만들지 않으면서도 전체 실패 구간을 덮을 수 있기 때문이다.

또한 `oos_insert_many()`가 일부 OOS OID를 publication한 뒤 실패할 때 수행하는 내부 clear는 그대로
유지해야 한다. 시작 시점 초기화와 부분 성공 후 실패 정리는 서로 다른 책임이다.

## 수정 후 어떤 테스트가 필요한가?

단순 성공 테스트만으로는 이 문제를 잡을 수 없다. 실패를 의도적으로 주입하고 두 임시 목록을 확인해야
한다.

### 1. class 정보 조회 실패

```text
초기 상태에 가짜 OOS OID/LSA를 넣음
-> heap_get_class_info() 실패 유도
-> 두 목록이 비었는지 확인
```

### 2. OOS VFID 조회 또는 생성 실패

```text
초기 상태에 가짜 OOS OID/LSA를 넣음
-> heap_oos_find_vfid() 실패 유도
-> 두 목록이 비었는지 확인
```

### 3. request 메모리 준비 실패

```text
초기 상태에 가짜 OOS OID/LSA를 넣음
-> vector reserve의 bad_alloc 유도
-> 두 목록이 비었는지 확인
```

### 4. 값 직렬화 실패

```text
초기 상태에 가짜 OOS OID/LSA를 넣음
-> heap_attrinfo_prepare_oos_insert_requests() 실패 유도
-> 두 목록이 비었는지 확인
```

### 5. 일부 OOS insert 후 실패

```text
여러 request 중 일부만 성공한 뒤 실패 유도
-> oos_insert_many()의 내부 cleanup 확인
-> OOS OID/LSA 목록이 모두 비었는지 확인
-> transaction abort로 이미 기록한 OOS chunk가 rollback되는지 확인
```

## 리뷰의 각 주장 판정표

| 리뷰 주장 | 판정 | 이유 |
|---|---|---|
| class/VFID lookup 실패가 clear보다 먼저 발생할 수 있다 | 맞음 | 현재 코드 순서가 실제로 그렇다. |
| 그 경우 이전 publication 상태가 남을 수 있다 | 맞음 | early return 전에 별도 clear가 없다. |
| `1a278e978`과 완전히 같은 패턴이다 | 일부만 맞음 | 과거 수정은 clear를 직렬화보다 앞으로 옮겼지만 class/VFID lookup보다 앞에 두지는 않았다. |
| helper 안에서 clear를 line 607 앞으로 옮기면 충분하다 | 틀림 | helper 호출 전의 reserve/직렬화 실패를 처리하지 못한다. |
| 현재 즉시 잘못된 replication이 발생한다 | 증명되지 않음 | 실패 후 stale 상태를 실제 소비하는 경로가 제시되지 않았다. |
| P1이다 | 근거 부족 | 재현 가능한 데이터 손상이나 replication 오류 경로가 없다. |
| 방어적으로 수정할 가치가 있다 | 맞음 | 상태 소유권과 실패 계약이 더 명확해진다. |

## 권장 리뷰 답변 초안

```text
지적하신 것처럼 현재 helper의 class/VFID lookup 실패 경로에서는 publication 상태가 clear되지
않습니다. 새 논리 OOS insert가 깨끗한 publication 상태에서 시작해야 한다는 방어적 invariant
관점에서 수정 가치가 있습니다.

다만 1a278e978은 clear를 class/VFID lookup보다 앞으로 옮긴 커밋이 아니라, request 준비와
직렬화보다 앞으로 옮긴 커밋입니다. 현재 리팩터링에서는 request reserve와 직렬화가 helper 호출보다
앞에 있으므로, helper 내부에서 clear를 line 607 앞으로 옮기는 것만으로는 해당 실패 경로를 모두
처리하지 못합니다.

따라서 논리 OOS insert 준비의 시작점에서, reserve/직렬화/class lookup/VFID lookup보다 먼저
publication 상태를 초기화하는 방향으로 정리하는 것이 더 완전합니다. 한편 현재 실패 경로에서 stale
상태가 실제 replication consumer까지 도달하는 재현 경로는 확인되지 않아 P1로 보기는 어렵습니다.
```

## 최종 정리

이 리뷰를 이해할 때 가장 중요한 구분은 다음 두 문장이다.

```text
1. 이전 작업의 임시 상태가 남을 수 있다.             -> 맞음
2. 그 상태가 현재 즉시 잘못된 replication을 만든다.  -> 증명되지 않음
```

따라서 리뷰를 무시할 필요는 없다. publication 상태의 수명과 소유권을 명확히 만들기 위해 수정하는 것이
좋다. 다만 P1로 급하게 처리하기보다는, 전체 논리 OOS insert의 시작 경계를 기준으로 실패 경로를 모두
덮는 수정과 fault-injection 테스트를 함께 준비하는 편이 정확하다.

## 근거

- `src/storage/heap_oos.cpp`: `heap_oos_insert_serialized_values()`의 class/VFID lookup과 clear 순서
- `src/storage/heap_file.c`: helper 호출 전 reserve 및 OOS payload 직렬화
- `src/storage/oos_file.cpp`: `oos_insert_many()` 부분 실패 시 publication 상태 정리
- `src/transaction/replication.c`: OOS replication record에서만 OOS LSA queue 소비
- commit `1a278e978`: clear를 request 준비/직렬화보다 앞으로 이동
- `CBRD-27006-oos-insert-publication-owned-by-api.md`: OOS insert publication 소유권과 실패 경로 계약
