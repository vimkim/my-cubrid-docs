# [CBRD-26985] Preserve caller-owned heap fetch buffers

- JIRA: https://jira.cubrid.org/browse/CBRD-26985
- PR: https://github.com/CUBRID/cubrid/pull/7368
- Base branch: `feat/oos`
- PR HEAD: `e4db120d3` (`[CBRD-26985] Preserve caller-owned heap fetch buffers`)

## Purpose

CBRD-26985 는 OOS expand 가 필요한 대량 fetch 경로에서 `LC_COPYAREA` descriptor 와 실제 record bytes 의 위치가 갈라져 crash 나는 문제를 고친다.

`LC_COPYAREA` 는 여러 object record 를 한 buffer 에 담아 보내는 구조이다. record bytes 는 앞에서 뒤로 쌓이고, 각 object descriptor 는 뒤에서 앞으로 쌓인다.

```text
copyarea->mem
  | record bytes 는 앞에서 뒤로 증가
  v
  [ rec0 ][ rec1 ][ free space ... ][ obj1 ][ obj0 ][ LC_COPYAREA_MANYOBJS ]
                                      ^
                                      descriptor 는 뒤에서 앞으로 증가
```

descriptor 인 `LC_COPYAREA_ONEOBJ` 는 record bytes 를 직접 들고 있지 않고, `copyarea->mem` 기준 `offset` 과 `length` 를 기록한다. 따라서 descriptor 를 publish 할 때 실제 bytes 는 반드시 `copyarea->mem + offset` 에 있어야 한다.

문제는 OOS branch 에서 raw record fetch 가 `heap_next_expand_oos` / `heap_get_visible_version_expand_oos` 로 바뀌면서 드러났다. OOS (Out-of-row Storage, 큰 column 값을 heap record 밖에 저장하고 읽을 때 원래 record 형태로 펼치는 기능) 는 inline OOS OID 를 실제 column bytes 로 바꾸기 위해 record image 를 다시 만들 수 있다. 이때 caller 가 `RECDES.data` 를 copyarea slot 으로 지정했는데도 heap fetch 가 그 pointer 를 scan-cache storage 로 바꿔 성공 반환하면, locator 는 copyarea 기준 descriptor 를 만들고 실제 bytes 는 scan cache 에 남는다.

실패 호출 흐름은 다음과 같다.

```text
ALTER TABLE ... CHANGE
  -> do_run_upgrade_instances_domain
    -> locator_upgrade_instances_domain
      -> xlocator_upgrade_instances_domain
        -> xlocator_lock_and_fetch_all
          -> heap_next / heap_get_visible_version_expand_oos
```

core 에서 보인 값도 "큰 record 하나가 copyarea 를 넘쳤다" 보다는 "copyarea pointer 가 scan cache pointer 로 바뀐 뒤 계속 진행됐다" 는 쪽과 맞다.

```text
mobjs->num_objs = 532
offset = 16992
recdes.length = 32
recdes.area_size = 8672
recdes.data = scan_cache.m_area 내부 주소
```

현재 record 길이가 32 bytes 이므로 직접 원인은 큰 OOS payload 가 아니다. 앞선 fetch 중 `recdes.data` 가 scan cache 내부로 rebind 되었고, locator loop 가 그 pointer 를 계속 전진시킨 상태에서 copyarea descriptor 를 만들었다.

## Implementation

이번 PR 의 실제 diff 는 `src/storage/heap_file.c` 와 `src/storage/heap_file.h` 만 바꾼다. locator 쪽에 새 helper 를 추가하지 않는다.

### 1. `area_size` 로 buffer 소유권을 판단하지 않는다

기존 `heap_init_get_context` 는 `keep_recdes_buffer` 를 아래 조건으로 켰다.

```text
recdes != NULL
&& recdes->data != NULL
&& recdes->area_size >= 0
&& recdes->data 가 scan-cache 시작 주소가 아님
```

`xlocator_fetch_all` 과 `xlocator_lock_and_fetch_all` 은 `LC_RECDES_IN_COPYAREA` 로 `recdes.data` 를 copyarea payload slot 에 맞춘 뒤, object 를 pack 할 때마다 아래처럼 다음 slot 을 준비한다.

```text
offset += DB_ALIGN(recdes.length, MAX_ALIGNMENT)
recdes.data += DB_ALIGN(recdes.length, MAX_ALIGNMENT)
recdes.area_size -= round_length + sizeof(*obj)
```

여기서 `recdes.area_size` 는 "현재 slot 에 남은 writable area" 이다. 이 값이 0 이하가 되어도 `recdes.data` 의 소유자가 바뀌지는 않는다. 여전히 caller 가 지정한 copyarea 위치이다.

pre-fix 에서는 `area_size < 0` 이 되는 순간 heap 이 이 buffer 를 caller-owned 로 보지 않았다. 그 결과 `heap_prepare_recdes_copy_area` 가 `heap_scan_cache_allocate_recdes_data` 를 호출할 수 있고, 이 함수는 `recdes.data` 를 scan cache 로 바꾼다.

```text
heap_prepare_recdes_copy_area
  keep_recdes_buffer == false
    -> heap_scan_cache_allocate_recdes_data
       -> scan_cache->assign_recdes_to_area(*recdes)
          -> recdes.data = scan_cache.m_area
```

새 코드는 `area_size >= 0` 조건을 제거한다.

```text
recdes != NULL
&& recdes->data != NULL
&& recdes->data 가 scan-cache area 밖에 있음
```

즉, caller 가 위치시킨 non-scan-cache `RECDES.data` 는 남은 공간이 부족해도 caller-owned 로 유지한다. 공간 부족은 buffer ownership 변경이 아니라 `S_DOESNT_FIT` 으로 표현되어야 한다.

### 2. scan-cache 소유 여부를 시작 주소가 아니라 range 로 판단한다

기존 `heap_scancache::is_recdes_assigned_to_area` 는 아래처럼 scan-cache 시작 주소만 비교했다.

```text
recdes.data == m_area->get_ptr()
```

하지만 locator loop 는 record 하나를 pack 한 뒤 `recdes.data += round_length` 를 수행한다. 만약 `recdes.data` 가 이미 scan cache 로 rebind 된 상태라면 pointer 는 scan-cache block 의 시작 주소가 아니라 중간 주소를 가리킬 수 있다.

pre-fix 판정은 이 중간 pointer 를 scan-cache-owned 로 인식하지 못했다. 그러면 다음 `heap_init_get_context` 가 scan-cache 내부 pointer 를 caller-owned 로 오판할 수 있다.

새 코드는 `m_area` 가 있고 `recdes.data` 가 scan-cache block 내부에 있으면 scan-cache-owned 로 본다.

```text
area_start = m_area->get_ptr()
area_end = area_start + m_area->get_size()

area_start <= recdes.data && recdes.data <= area_end
```

`recdes.data == area_end` 는 writable byte 를 가리키지 않더라도 같은 allocation 의 끝 위치이므로 scan-cache-owned 로 분류하는 쪽이 안전하다.

### 3. 기존 `S_DOESNT_FIT` grow/retry 계약을 다시 살린다

`heap_prepare_recdes_copy_area` 는 `keep_recdes_buffer` 가 true 이면 scan cache area 만 reserve 하고 `recdes.data` 를 바꾸지 않는다. 이후 OOS expand 결과가 caller buffer 에 들어가지 않으면 heap fetch 는 `S_DOESNT_FIT` 을 반환한다.

```text
caller-owned RECDES.data 에 record 가 들어감
  -> S_SUCCESS, recdes.data 유지

caller-owned RECDES.data 에 record 가 안 들어감
  -> S_DOESNT_FIT, caller 가 buffer 를 키워 재시도

empty 또는 scan-cache-owned RECDES.data
  -> heap 이 scan-cache area 를 할당하거나 키울 수 있음
```

locator copyarea fetch 경로는 이미 `S_DOESNT_FIT` 일 때 copyarea 를 키워 재시도한다. lock fetch 경로는 `heap_get_visible_version_expand_oos` 에서 `S_DOESNT_FIT` 이 나면 `retry_current_oid` 를 세우고 `prev_oid` 로 되돌리는 보정도 갖고 있다.

따라서 이번 PR 은 locator 를 새로 감싸지 않고 heap layer 의 ownership 판정만 바로잡는다. 이것이 새 접근 방식의 핵심이다.

### Diff 요약

| 파일 | 변경 | 리뷰 포인트 |
|------|------|-------------|
| `src/storage/heap_file.c` | `heap_init_get_context` 의 `keep_recdes_buffer` 판정에서 `area_size >= 0` 제거 | `area_size` 는 capacity 상태이지 ownership 이 아니다. |
| `src/storage/heap_file.c` | `heap_scancache::is_recdes_assigned_to_area` 를 scan-cache block range 검사로 변경 | scan-cache 내부로 전진한 pointer 도 scan-cache-owned 로 분류한다. |
| `src/storage/heap_file.h` | `keep_recdes_buffer` 주석 갱신 | field 의미를 caller-positioned buffer 보존으로 명확히 한다. |

## Remarks

### Review focus

- `keep_recdes_buffer` 에서 `area_size >= 0` 을 제거하는 것이 맞는지 확인한다. `area_size` 가 부족하다는 사실은 `S_DOESNT_FIT` 으로 흘러야지, heap 이 caller buffer 를 scan cache 로 바꿔 성공 반환하는 근거가 되면 안 된다.
- `is_recdes_assigned_to_area` 의 range check 가 scan-cache-owned pointer 를 충분히 포착하는지 확인한다.
- locator 쪽 새 helper 가 없는 점은 의도적이다. 기존 locator grow/retry 를 재사용하는 방식이 이 PR 의 범위이다.

### Verification

- `git diff --check`
- 기존 확인: `locator_sr.c` server-mode single-file compile
- 기존 확인: `locator_sr.c` SA-mode single-file compile
- 기존 확인: `release_gcc` build
- 재현 SQL 의 핵심 statement 인 `alter table t change i a int` 는 새 heap-side approach 후 crash 없이 종료했다.
- 뒤따르는 `function_index_skip_bit.sql` 도 recovery cascade 없이 통과했다.

### Limits

CircleCI 의 insert-side `OOS+REC_BIGONE` abort 는 별도 문제이다. stack 이 `locator_insert_force` 아래 insert path 이고 `heap_insert_adjust_recdes_header` 의 임시 guard 와 맞는다. 이 PR 은 fetch-side caller-owned buffer 보존만 다룬다.

관련 follow-up 은 CBRD-26937 이다.
