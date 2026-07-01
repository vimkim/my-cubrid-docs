# [CBRD-26985] origin/develop 에서는 왜 같은 버그가 발생하지 않았나

- JIRA: https://jira.cubrid.org/browse/CBRD-26985
- PR: https://github.com/CUBRID/cubrid/pull/7368
- PR HEAD: `2fe42bd83` (`[CBRD-26985] Fix OOS copyarea packing in lock fetch`)
- 문제 재현 기준: `53e8d6b9a` (`feat/oos` 쪽 pre-fix 상태)
- 비교 대상: `origin/develop` (`23789cbfa`, 2026-07-01 로컬 기준)
- 문서 작성일: 2026-07-01

## 한 줄 결론

같은 버그가 `origin/develop` 에서 발생하지 않은 이유는 `origin/develop` 에는 아직 OOS 확장 fetch 경로가 없기 때문이다.

기존 `origin/develop` 의 `xlocator_lock_and_fetch_all` 은 `heap_next` / `heap_get_visible_version` 으로 레코드를 copyarea 에 직접 복사한다. 반면 `feat/oos` 에서는 raw record 를 클라이언트로 넘기는 경로에서 OOS OID 를 실제 값으로 펼치기 위해 `heap_next_expand_oos` / `heap_get_visible_version_expand_oos` 를 쓰도록 바뀌었다. 이 새 경로는 heap scan-cache 버퍼를 사용할 수 있고, 그 결과 `RECDES.data` 가 더 이상 `LC_COPYAREA` 내부를 가리키지 않을 수 있었다.

즉, 버그는 오래된 copyarea packing 코드가 원래부터 틀렸다기보다, OOS 도입으로 `RECDES.data` 의 소유권과 위치가 바뀔 수 있는 새 조건이 생겼는데 locator 쪽이 그 조건을 매번 검증하지 않아서 발생한 회귀이다.

## 증상

회귀 테스트에서 `function_index_skip_alter_table.sql` 이 실패했고, 그 다음 테스트는 같은 DB 에 계속 접속을 재시도하는 것처럼 보였다.

실제로는 SQL 테스트 자체가 무한 루프를 돈 것이 아니라, 앞선 `ALTER TABLE ... CHANGE` 처리 중 서버가 깨진 뒤 DB 복구가 실패하면서 후속 테스트가 계속 같은 죽은 서버/DB 상태를 만난 것이다.

관찰된 핵심 경로는 다음과 같다.

```text
ALTER TABLE ... CHANGE
  -> do_run_upgrade_instances_domain
    -> locator_upgrade_instances_domain
      -> xlocator_upgrade_instances_domain
        -> xlocator_lock_and_fetch_all
```

유용했던 core 의 값은 다음 성격을 보였다.

```text
mobjs->num_objs = 532
offset = 16992
recdes.length = 32
recdes.area_size = 8672
recdes.data = heap scan-cache 영역
```

여기서 중요한 점은 `recdes.length = 32` 라는 점이다. 이 재현은 큰 OOS 값 하나가 copyarea 를 넘쳐서 난 문제가 아니었다. 작은 record 에서도 `recdes.data` 가 copyarea 가 아니라 scan-cache 영역을 가리키게 되었고, locator 는 여전히 copyarea 안에 record bytes 가 있다고 믿고 descriptor 를 만들었다.

## 배경: LC_COPYAREA 의 약속

`LC_COPYAREA` 는 서버가 여러 object record 를 한 번에 클라이언트로 보내기 위한 버퍼이다.

메모리 배치는 대략 다음과 같다.

```text
copyarea->mem
  |
  | record bytes 는 앞에서 뒤로 증가
  v
  [ rec0 ][ rec1 ][ rec2 ][ free ... ][ obj2 ][ obj1 ][ obj0 ][ LC_COPYAREA_MANYOBJS ]
                                      ^
                                      descriptors 는 뒤에서 앞으로 증가
```

각 object descriptor 인 `LC_COPYAREA_ONEOBJ` 는 실제 record bytes 를 직접 들고 있지 않는다. 대신 다음 metadata 를 기록한다.

```text
obj->offset = copyarea->mem 기준 record 시작 위치
obj->length = record 길이
```

나중에 record 를 다시 꺼낼 때는 `LC_RECDES_TO_GET_ONEOBJ` 매크로가 아래처럼 해석한다.

```text
recdes->data = copyarea->mem + obj->offset
```

따라서 이 경로의 핵심 불변식은 단순하다.

```text
descriptor 가 가리키는 위치 == 실제 record bytes 가 들어 있는 위치
```

조금 더 코드에 가깝게 쓰면 다음 두 조건이 descriptor 생성 전에 동시에 참이어야 한다.

```text
obj->offset == offset
recdes.data == (*fetch_area)->mem + offset
```

## origin/develop 의 동작

`origin/develop` 의 `xlocator_fetch_all` 은 일반 heap fetch 를 사용한다.

```c
while ((scan = heap_next (thread_p, hfid, class_oid, &oid, &recdes, &scan_cache, COPY)) == S_SUCCESS)
```

`origin/develop` 의 `xlocator_lock_and_fetch_all` 도 동일한 전제를 갖는다.

```c
scan = heap_next (thread_p, hfid, class_oid, &oid, &recdes, &scan_cache, COPY);
...
scan = heap_get_visible_version (thread_p, &oid, class_oid, &recdes, &scan_cache, COPY, NULL_CHN);
```

이 경로에서는 locator 가 먼저 `LC_RECDES_IN_COPYAREA` 로 `recdes.data` 를 copyarea 시작 위치에 맞춘다.

```c
recdes.data = copy_area_ptr->mem;
recdes.area_size = copy_area_ptr->length - sizeof (LC_COPYAREA_MANYOBJS);
```

그 뒤 각 record 를 읽을 때 다음처럼 처리한다.

```c
obj->offset = offset;
round_length = DB_ALIGN (recdes.length, MAX_ALIGNMENT);
offset += round_length;
recdes.data += round_length;
recdes.area_size -= round_length + sizeof (*obj);
```

이 코드는 암묵적으로 `recdes.data` 가 계속 copyarea 내부를 가리킨다고 가정한다. `origin/develop` 에서는 해당 재현 경로가 이 가정과 충돌하지 않았다.

특히 `origin/develop` 에는 아래 OOS 구성요소가 없다.

- `heap_next_expand_oos`
- `heap_get_visible_version_expand_oos`
- `heap_record_replace_oos_oids`
- `heap_oos.cpp`
- `oos_file.cpp`
- `OR_MVCC_FLAG_HAS_OOS`
- `OR_VAR_BIT_OOS`

즉, 레코드를 읽은 뒤 inline OOS OID slot 을 실제 값으로 재구성하는 단계 자체가 없다.

## feat/oos 에서 바뀐 점

OOS 는 큰 variable column 값을 heap record 밖의 OOS file 에 저장하고, heap record 에는 16-byte OOS OID slot 만 남긴다. 그런데 `LC_COPYAREA` 로 raw record image 를 클라이언트나 unload 계층에 넘기는 경로에서는 OOS OID 를 그대로 보내면 안 된다. 받는 쪽은 OOS 를 모르는 기존 record image 를 기대하기 때문이다.

그래서 `feat/oos` 에서는 일부 raw-byte fetch 경로가 다음 확장형 함수로 바뀌었다.

```text
heap_next
  -> heap_next_expand_oos

heap_get_visible_version
  -> heap_get_visible_version_expand_oos
```

관련 변경은 CBRD-26818 에서 들어왔다.

```diff
- heap_next(...)
+ heap_next_expand_oos(...)

- heap_get_visible_version(...)
+ heap_get_visible_version_expand_oos(...)
```

확장형 함수는 내부적으로 다음 일을 할 수 있다.

1. heap page 에서 원래 record 를 읽는다.
2. record 에 OOS OID slot 이 있으면 `oos_read` 로 실제 값을 읽는다.
3. 기존 record image 를 새 record image 로 재구성한다.
4. 재구성 결과가 현재 `RECDES` 공간보다 크면 scan-cache 영역을 쓰거나 `S_DOESNT_FIT` 으로 돌려보낸다.

이때 locator 입장에서 가장 위험한 변화는 4번이다. OOS 확장 fetch 이후에는 `recdes.data` 가 반드시 원래 copyarea 위치라고 볼 수 없다.

## 실제 버그

pre-fix `feat/oos` 의 `xlocator_lock_and_fetch_all` 은 OOS 확장 fetch 를 호출하면서도 기존 copyarea packing 방식을 그대로 유지했다.

문제의 흐름은 다음과 같다.

```text
1. locator 가 copyarea 를 할당한다.
2. LC_RECDES_IN_COPYAREA 로 recdes.data 를 copyarea->mem 에 맞춘다.
3. heap_next_expand_oos 또는 heap_get_visible_version_expand_oos 를 호출한다.
4. fetch 결과로 recdes.data 가 scan-cache 영역을 가리킬 수 있다.
5. locator 는 이 사실을 확인하지 않고 obj->offset = offset 을 기록한다.
6. offset 과 descriptor 는 copyarea 기준인데, 실제 bytes 는 copyarea 밖에 있다.
7. 루프가 계속 돌면서 recdes.area_size 와 descriptor 위치 계산이 현실의 copyarea 여유 공간과 어긋난다.
8. descriptor 영역 또는 allocator metadata 를 침범하고, 나중에 SIGSEGV/malloc abort/redo fatal 로 이어진다.
```

핵심은 metadata 와 payload 의 기준 주소가 달라졌다는 점이다.

```text
descriptor:
  obj->offset = copyarea 기준 offset

actual payload:
  recdes.data = scan-cache 내부 주소
```

이 상태에서는 `obj->offset` 이 아무리 맞아도 copyarea 안의 그 위치에는 올바른 record bytes 가 없다.

## 왜 origin/develop 에서는 같은 문제가 없었나

### 1. OOS 확장 fetch 함수가 없다

`origin/develop` 은 OOS 기능 자체가 없다. 따라서 해당 branch 에서는 `heap_next_expand_oos` 나 `heap_get_visible_version_expand_oos` 를 호출할 수 없다.

결과적으로 record 를 읽은 뒤 OOS OID 를 실제 column bytes 로 펼치기 위해 record image 를 다시 만드는 단계도 없다.

### 2. xlocator_lock_and_fetch_all 이 일반 fetch 계약 안에 머문다

`origin/develop` 의 lock-fetch 경로는 다음 두 함수만 쓴다.

```text
heap_next
heap_get_visible_version
```

이 경로에서는 locator 가 준비한 `recdes.data` 위치, 즉 copyarea 내부 위치가 record 복사 위치로 유지된다. copyarea loop 는 그 전제를 바탕으로 `offset`, `recdes.data`, `recdes.area_size`, `obj` descriptor 를 함께 전진시킨다.

즉, 기존 코드는 취약한 암묵적 가정을 갖고 있었지만 `origin/develop` 의 실제 fetch 구현은 그 가정을 깨지 않았다.

### 3. origin/develop 에는 OOS raw-record 호환성 요구가 없다

OOS branch 에서는 raw record 소비자가 OOS 를 모르기 때문에 OOS OID slot 을 실제 값으로 바꿔 보내야 한다.

대표 소비자는 다음 계열이다.

- `ALTER TABLE ... CHANGE` 중 instance domain upgrade
- `unloaddb`
- `compactdb`
- 클라이언트로 raw `LC_COPYAREA` record 를 보내는 fetch-all 계열

`origin/develop` 에서는 heap record 자체가 이미 완성된 record image 이다. 별도 OOS file 에 있는 값을 읽어 붙일 필요가 없으므로, fetch 중 record size 와 buffer ownership 이 크게 바뀌는 조건이 없다.

### 4. 재현 SQL 이 작은 record 여도 OOS branch 에서만 실패한 이유

이번 core 에서 `recdes.length` 는 32 byte 수준이었다. 따라서 "큰 OOS value 가 copyarea 를 넘쳤기 때문" 이라고 보면 틀리다.

실패의 직접 조건은 OOS value 의 크기 자체가 아니라, OOS 지원을 위해 도입된 `_expand_oos` fetch wrapper 가 locator 의 기존 copyarea packing 계약보다 넓은 buffer ownership 모델을 갖게 된 것이다.

그래서 작은 record 로 구성된 `ALTER TABLE ... CHANGE` 테스트도 `feat/oos` 에서는 실패할 수 있었고, OOS 코드가 없는 `origin/develop` 에서는 같은 실패 조건이 만들어지지 않았다.

## CBRD-26818 과 CBRD-26985 의 차이

CBRD-26818 은 이미 한 차례 비슷한 문제를 다뤘다. 그때의 핵심은 "caller 가 `RECDES.data` 를 미리 copyarea 로 지정한 경우, heap OOS 확장이 임의로 scan-cache 로 갈아끼우지 않게 하자" 였다.

그 수정으로 OOS 확장 결과가 caller buffer 보다 큰 경우에는 `S_DOESNT_FIT` 을 반환하고 copyarea 를 키워 재시도할 수 있게 되었다.

하지만 CBRD-26985 에서는 locator loop 자체에도 방어가 필요했다.

이유는 다음과 같다.

- `xlocator_lock_and_fetch_all` 은 한 copyarea 안에 수백 개 object 를 반복 packing 한다.
- 각 iteration 마다 현재 record slot 과 descriptor 영역 사이의 남은 공간을 새로 계산해야 한다.
- instance-lock 경로는 `heap_next` 로 OID 를 찾은 뒤, 같은 OID 를 `heap_get_visible_version_expand_oos` 로 다시 읽는다.
- 두 번째 fetch 전에 `recdes.data` / `recdes.area_size` 를 현재 copyarea slot 으로 다시 맞추지 않으면 이전 fetch 결과나 scan-cache 상태를 그대로 사용할 수 있다.
- fetch 성공 후에도 `recdes.data` 가 정말 copyarea slot 인지 확인하지 않으면 descriptor 와 payload 의 위치가 갈라질 수 있다.

따라서 CBRD-26818 이 heap 쪽의 "버퍼를 함부로 바꾸지 말라"는 규칙을 추가한 수정이라면, CBRD-26985 는 locator 쪽의 "descriptor 를 만들기 전에 실제 bytes 를 copyarea 에 pack 하라"는 규칙을 추가한 수정이다.

## PR #7368 의 수정 내용

PR #7368 은 `src/transaction/locator_sr.c` 에 두 helper 를 추가했다.

### `locator_copyarea_prepare_fetch_recdes`

각 object 를 fetch 하기 직전에 현재 copyarea slot 을 다시 계산한다.

```text
copyarea_data = copyarea->mem + offset
copyarea_area_size =
  copyarea->length
  - sizeof(LC_COPYAREA_MANYOBJS)
  - offset
  - num_objs * sizeof(LC_COPYAREA_ONEOBJ)
```

그리고 `recdes` 를 이 slot 에 맞춘다.

```text
recdes.data = copyarea_data
recdes.area_size = copyarea_area_size
```

이렇게 하면 매 iteration 이 항상 현재 copyarea layout 에서 출발한다.

### `locator_copyarea_pack_fetch_recdes`

heap fetch 가 끝난 뒤 다음을 확인한다.

1. `DB_ALIGN(recdes.length, MAX_ALIGNMENT)` 이 현재 copyarea slot 에 들어가는가?
2. `recdes.data` 가 현재 copyarea slot 과 같은 주소인가?

만약 record 가 slot 보다 크면 `S_DOESNT_FIT` 으로 빠져 기존 copyarea 확장 재시도 흐름을 탄다.

만약 record 는 들어가지만 `recdes.data` 가 scan-cache 등 다른 곳을 가리키면 descriptor 를 만들기 전에 bytes 를 copyarea slot 으로 복사한다.

```c
if (recdes->data != copyarea_data)
  {
    memcpy (copyarea_data, recdes->data, recdes->length);
    recdes->data = copyarea_data;
  }
```

이후에만 `obj->offset = offset` 을 기록한다.

## 수정 후 불변식

수정 후 `xlocator_fetch_all` 과 `xlocator_lock_and_fetch_all` 은 descriptor 를 publish 하기 전에 아래 불변식을 강제로 맞춘다.

```text
recdes.data == copyarea->mem + offset
recdes.length <= 현재 payload slot 크기
obj->offset == offset
obj->length == recdes.length
```

따라서 heap fetch 가 내부적으로 scan-cache 를 사용하더라도 `LC_COPYAREA` 의 외부 계약은 유지된다.

## S_DOESNT_FIT 과 cursor 복원

copyarea 첫 object 부터 들어가지 않는 경우 기존 로직은 copyarea 를 키워 같은 object 를 다시 읽어야 한다.

`heap_next_expand_oos` 는 성공했을 때만 caller 의 `next_oid` 를 갱신하므로 일반 scan 경로는 비교적 안전하다.

하지만 `xlocator_lock_and_fetch_all` 의 instance-lock 경로는 다르다.

```text
heap_next 로 OID 를 찾음
  -> instance lock 획득
    -> heap_get_visible_version_expand_oos 로 같은 OID 를 다시 fetch
```

두 번째 fetch 에서 `S_DOESNT_FIT` 이 나면 이미 `oid` 는 현재 object 로 전진해 있다. 그래서 PR #7368 은 fetch 전에 `prev_oid` 를 저장하고, 첫 object 가 copyarea 에 들어가지 않은 경우 `oid` 를 되돌린다.

```text
retry_current_oid == true
  -> oid = prev_oid
  -> copyarea 확장
  -> 같은 object 재시도
```

이 처리가 없으면 copyarea 를 키워도 실패한 object 를 건너뛰거나, 반대로 cursor 상태가 꼬일 수 있다.

## 코드 비교 요약

| 구분 | `origin/develop` | pre-fix `feat/oos` | PR #7368 |
|------|------------------|--------------------|----------|
| fetch 함수 | `heap_next`, `heap_get_visible_version` | `heap_next_expand_oos`, `heap_get_visible_version_expand_oos` | 동일 |
| OOS record 재구성 | 없음 | 있음 | 있음 |
| `recdes.data` 위치 확인 | 필요 조건이 약함 | 확인하지 않음 | 매 fetch 후 확인 |
| copyarea 남은 공간 계산 | 초기 `recdes.area_size` 에 의존 | 기존 방식 유지 | 매 object 마다 copyarea layout 로 재계산 |
| scan-cache-backed 결과 | 해당 재현 경로에서 문제 조건 없음 | descriptor 와 payload 불일치 가능 | copyarea 로 복사 후 descriptor 생성 |
| 첫 object `S_DOESNT_FIT` | 기존 copyarea 확장 | 일부 OOS path 에서 cursor 주의 필요 | `prev_oid` 복원 후 재시도 |

## 왜 이 수정이 origin/develop 에 필요 없었나

`origin/develop` 에도 copyarea packing 코드는 비슷하게 보인다. 그래서 겉으로 보면 "왜 develop 에서도 같은 식으로 descriptor 가 깨지지 않았나?" 라는 질문이 생긴다.

답은 이렇다.

`origin/develop` 의 코드는 `recdes.data` 가 copyarea 내부라는 전제를 깔고 있고, 해당 재현 경로에서는 heap fetch 가 그 전제를 깨지 않았다. 반면 OOS branch 는 raw record 를 OOS-expanded image 로 바꾸는 과정이 추가되면서 `recdes.data` 가 scan-cache-backed 결과가 될 수 있었다. 같은 locator 코드를 사용하더라도 heap 계층의 반환 계약이 넓어진 순간부터 기존 전제는 더 이상 충분하지 않았다.

따라서 PR #7368 의 수정은 `origin/develop` 의 기존 버그를 고친 것이 아니라, OOS branch 가 도입한 새 fetch 계약에 맞춰 locator 의 copyarea packing 계약을 명시적으로 보강한 것이다.

## 검증 기록

수정 당시 확인된 항목은 다음과 같다.

- `git diff --check`
- `locator_sr.c` server-mode single-file compile
- `locator_sr.c` SA mode single-file compile
- `release_gcc` build
- SA mode 재현 SQL 실행

재현 SQL 의 핵심 statement 는 다음이다.

```sql
alter table t change i a int;
```

패치 전에는 `xlocator_upgrade_instances_domain` 경로에서 `SIGSEGV` 가 발생했다. 패치 후에는 같은 SQL 이 정상 종료했고, `function_index_skip_alter_table.result` 와 line-for-line 으로 일치했다. 이어서 실행한 `function_index_skip_bit.sql` 도 새 core 없이 통과했다.

## 최종 정리

`origin/develop` 에서 같은 버그가 발생하지 않은 직접적인 이유는 OOS 확장 fetch 경로가 없기 때문이다.

pre-fix `feat/oos` 에서는 raw record 를 OOS-expanded form 으로 만들어야 했고, 이 과정에서 heap fetch 결과가 scan-cache 버퍼를 가리킬 수 있었다. locator 는 여전히 record bytes 가 copyarea 에 있다고 가정하고 descriptor 를 만들었기 때문에 metadata 와 payload 위치가 분리되었다.

PR #7368 은 이 분리를 막기 위해 fetch 전에는 현재 copyarea slot 을 명확히 준비하고, fetch 후에는 record bytes 가 실제로 그 slot 에 있는지 확인하며, 필요하면 copyarea 로 복사한 뒤 descriptor 를 만든다. 그래서 OOS branch 의 새 buffer ownership 조건에서도 `LC_COPYAREA` 의 기존 외부 계약이 다시 유지된다.
