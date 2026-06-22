# [CBRD-26818] OOS expansion copyarea ownership

- JIRA: https://jira.cubrid.org/browse/CBRD-26818
- Target branch: `feat/oos`
- Code branch: `CBRD-26818-oos-expansion-buffer-ownership`

## Summary

OOS 확장 경로가 호출자가 미리 배치한 `RECDES.data` 버퍼를 임의로 바꾸지 않도록 수정한다.

`locator` 의 copyarea fetch 경로는 `LC_RECDES_IN_COPYAREA` 로 `recdes.data` 를 copyarea 내부 위치에 맞춰 둔 뒤 heap 에 레코드 복사를 요청한다. 이 상태에서 OOS stub 을 실제 값으로 확장하다가 더 큰 버퍼가 필요하면, 기존 구현은 `scan_cache->assign_recdes_to_area` 로 `RECDES` 를 scan cache 영역에 다시 붙일 수 있었다. 그러면 `locator` 는 copyarea 안에 값이 들어왔다고 믿고 `obj->offset`, `obj->length`, `recdes.data += round_length` 를 계산하지만 실제 데이터는 다른 버퍼에 있으므로 unloaddb, fetch-all, JSON deserialize 같은 raw record 소비 경로가 깨진다.

이번 PR 은 "copyarea 가 소유한 자리에는 heap 이 새 버퍼를 대신 붙이지 않는다"는 규칙을 명시하고, 필요한 경우 `S_DOESNT_FIT` 으로 돌려 copyarea 크기 재시도 루프가 같은 객체를 다시 읽도록 한다.

## Problem

기존 OOS 확장 함수 `heap_oos_build_record` 는 아래 두 상황을 같은 방식으로 처리했다.

- `PEEK`: 결과가 heap page buffer 를 직접 가리킬 수 없으므로 scan cache 버퍼가 필요하다.
- `COPY`: 호출자가 준 `RECDES` 공간보다 확장 후 레코드가 커서 더 큰 공간이 필요하다.

둘 다 `scan_cache->assign_recdes_to_area` 를 호출했기 때문에, `COPY` 이면서 `recdes.data` 가 이미 copyarea 내부 위치를 가리키는 경우에도 결과 버퍼가 scan cache 로 옮겨질 수 있었다.

copyarea fetch 계층의 기대는 다르다. `recdes.data` 는 `mobjs` 뒤의 payload 영역을 순서대로 가리키며, 객체 하나를 채운 뒤 다음 객체 위치로 전진한다. heap 이 이 포인터를 scan cache 로 바꾸면 `locator` 의 offset metadata 와 실제 데이터 위치가 달라진다.

## Design

`HEAP_GET_CONTEXT` 에 `data_externally_positioned` 를 추가한다.

```c
context->data_externally_positioned = (recdes != NULL && recdes->data != NULL);
```

의미는 단순하다. heap 호출 시점에 `recdes->data` 가 이미 있으면 그 주소는 호출자가 정한 출력 위치다. OOS 확장 중 `COPY` 결과가 그 공간보다 커지면 heap 은 scan cache 로 몰래 대체하지 않고 `rec->length = -new_length` 와 함께 `S_DOESNT_FIT` 을 반환한다.

반대로 아래 경로는 기존처럼 scan cache 를 쓴다.

- `PEEK`: 호출자가 copyarea 위치를 요구하지 않는다.
- `COPY` 이지만 `recdes->data == NULL`: scan cache 가 출력 버퍼를 배정해도 호출자 위치 약속이 없다.
- `COPY` 이고 기존 공간에 확장 결과가 들어간다: 버퍼 재배정 없이 그대로 채운다.

## Implementation

### Heap expansion guard

`heap_oos_build_record` 는 확장 결과 길이를 기준으로 `need_copy_realloc` 을 계산한다. `COPY` 경로에서 `need_copy_realloc` 이고 `data_externally_positioned` 가 참이면 다음과 같이 실패를 돌려준다.

```c
rec->length = - (state->new_length);
return S_DOESNT_FIT;
```

이 값은 기존 copyarea 성장 코드가 이미 해석하는 형식이다. `locator` 는 `-recdes.length` 를 기준으로 더 큰 copyarea 를 할당한다.

### Scan-next with OOS expansion

`heap_next` 는 원래 visible version 을 찾을 때 `heap_scan_get_visible_version` 을 사용했다. 이 공개 함수는 OOS 확장을 하지 않는다. raw copyarea fetch 가 OOS stub 대신 실제 값을 받아야 하므로 `heap_next_expand_oos` 를 추가했다.

`heap_next_expand_oos` 는 내부 구현에 `expand_oos = true` 를 넘긴다. 이때 중요한 점은 `heap_next_internal` 이 성공한 뒤에만 `*next_oid = oid` 를 갱신한다는 것이다. OOS 확장 중 `S_DOESNT_FIT` 이 발생하면 caller 의 cursor 는 이전 OID 에 남아 있고, copyarea 를 키운 뒤 같은 객체를 다시 읽을 수 있다.

또한 `PEEK` fast path 는 OOS 확장이 필요한 호출에서는 OOS stub 이 들어있는 record 를 그대로 반환하지 않도록 건너뛴다.

### Locator fetch callers

`xlocator_fetch_all` 과 `xlocator_lock_and_fetch_all` 의 non-lock scan 은 `heap_next_expand_oos` 를 사용한다. 이 두 경로는 copyarea 에 raw record 를 담아 클라이언트나 unload 쪽으로 넘기기 때문에 OOS stub 이 아니라 확장된 값을 받아야 한다.

`xlocator_lock_and_fetch_all` 의 instance-lock 경로는 lock 을 먼저 잡기 위해 기존처럼 `heap_next` 로 OID 를 찾은 뒤 `heap_get_visible_version_expand_oos` 로 다시 읽는다. 이 두 번째 읽기에서 첫 객체가 `S_DOESNT_FIT` 이면 copyarea 를 키우고 같은 객체를 재시도해야 하므로, `mobjs->num_objs == 0` 일 때만 `oid` 를 이전 cursor 로 되돌린다.

이미 하나 이상의 객체를 copyarea 에 담은 뒤 다음 객체에서 `S_DOESNT_FIT` 이 나면 기존 fetch-all 계약대로 partial copyarea 를 반환한다. 이 경우 `last_oid` 는 마지막으로 담은 객체로 설정되므로 다음 호출이 실패한 객체부터 다시 시도한다.

## Review Notes

### Why not always let scan_cache own the buffer?

copyarea fetch 는 결과 레코드의 bytes 와 metadata 를 같은 copyarea 안에 놓는 계약을 갖고 있다. scan cache 로 옮기면 lifetime 은 살아 있어도 copyarea serialization 계약이 깨진다. 따라서 copyarea 쪽이 더 큰 영역으로 재시도하는 것이 맞다.

### Why add `heap_next_expand_oos` instead of changing `heap_next`?

일반 heap scan 은 inline OOS OID slot 을 그대로 보존해야 하는 호출자가 있을 수 있다. 특히 기존 scan 동작 전체를 확장형으로 바꾸면 불필요한 OOS read 와 buffer growth 가 생긴다. raw fetch-all 처럼 "copyarea 에 완성된 record image 를 담아야 하는" 호출자만 확장형 함수를 선택하게 했다.

### Cursor safety

`heap_next_internal` 은 `S_SUCCESS` 에서만 caller 의 `next_oid` 를 갱신한다. 따라서 `heap_next_expand_oos` 가 `S_DOESNT_FIT` 을 돌려도 outer copyarea retry loop 는 같은 객체에서 재시도한다. instance-lock 경로는 OID fetch 와 expanded read 가 분리되어 있으므로, 첫 객체 실패일 때 별도로 이전 cursor 를 복원했다.

## Test Plan

debug build:

```sh
just build
```

통과했다.

CBRD-26818 direct online repro:

1. `cbrd_23430` 의 `init_data.tar.gz` 를 새 임시 DB 에 load.
2. `alter table t add column i int; update t set i = 1;`
3. `select json_length(j) from t;`

결과:

```text
1 row affected.
json_length(j) = 50000
```

predefined JSON unloaddb repro:

1. `cbrd_25481` 의 `40000.sql` 로 1.1MB JSON row 생성.
2. standalone `cubrid unloaddb -S`.
3. 새 DB 에 schema/object reload.
4. reload 전후 `select id, length(a)` 비교.

결과:

```text
id = 1
char_length(a) = 1108895
```

기존 실패 지점이던 `db_json_deserialize_doc_internal` assertion 없이 dump/reload 가 완료됐고, reload 전후 JSON 길이가 일치했다.
