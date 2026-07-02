# PR #7391 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7391](https://github.com/CUBRID/cubrid/pull/7391)
**제목:** [CBRD-27006] Improve OOS recdes locality
**작성자:** vimkim
**HEAD SHA:** `56e22c15c4ae024c141035b62db9dfb6d17acf6c`
**리뷰 일시:** 2026-07-02

> **TL;DR** (작성자 확인 필요): OOS (큰 가변 길이 컬럼을 heap record 밖 OOS file에 저장하는 방식) batch read/write의 page locality 개선 방향은 PR 범위와 맞지만, lazy Resolve (attribute layer가 필요한 컬럼만 읽는 OOS Resolve 경로)와 insert 경로가 OOS payload를 한 row 단위로 모두 materialize해 peak memory가 커진다. 머지 전 결정이 필요한 관례 이슈는 새 `try/catch` 사용이다.

## Summary

- **변경 요약**: 한 heap record의 OOS OID (OOS 값 하나를 가리키는 16-byte 식별자)들을 batch insert/read로 묶어 OOS page (OOS file 안의 slotted page) locality와 `pgbuf_fix` (buffer pool page pin) 횟수를 개선.
- **주요 이슈**: read/write 양쪽에서 기존 scalar 경로보다 OOS payload raw buffer를 오래, 많이 보유함.
- **확인 필요 사항**: engine code의 no-exceptions 규칙과 새 `try/catch (std::bad_alloc &)` 사용의 합의 여부.

---

## Findings

### Non-blocking (should consider)

- `src/storage/heap_file.c:12765` - insert 경로가 OOS payload를 `malloc` + `memcpy` 로 `pending` 에 모두 보관한 뒤 `oos_insert_many` 를 호출하므로, wide OOS row의 INSERT/UPDATE가 기존 per-column insert/free 경로보다 높은 peak memory에서 `ER_OUT_OF_VIRTUAL_MEMORY` 로 실패할 수 있다.

```c
pending_value.length = recdes.length;
pending_value.data = (char *) malloc ((size_t) pending_value.length);
memcpy (pending_value.data, recdes.data, (size_t) pending_value.length);
pending.push_back (pending_value);
```

- `src/storage/heap_file.c:10907` - batched lazy Resolve가 선택된 모든 OOS 값을 `recdes_allocate_data_area` 로 먼저 읽고 나서 DB_VALUE (CUBRID 값 컨테이너) 변환을 시작하므로, SELECT가 여러 큰 OOS 컬럼을 읽을 때 raw buffer 전체와 변환된 DB_VALUE가 동시에 살아 기존 scalar path보다 OOM 가능성이 커진다.

```c
if (recdes_allocate_data_area (&batched_value->raw, (int) oos_len) != NO_ERROR)
  {
    er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_OUT_OF_VIRTUAL_MEMORY, 1, (size_t) oos_len);
    return ER_OUT_OF_VIRTUAL_MEMORY;
  }
```

### Questions for the author

- `src/storage/heap_file.c:10934`, `src/storage/heap_file.c:12736`, `src/storage/oos_file.cpp:1867` - `try/catch (std::bad_alloc &)` 이 추가되었는데, 프로젝트 규칙은 engine code에서 C++ exceptions 사용을 금지한다. 이 branch에서 `std::vector` OOM 처리를 exception 기반으로 허용하기로 합의된 것인지 확인 필요.

```c
catch (std::bad_alloc &)
```

**작성자 답변 (2026-07-02):** `src` 안에 `catch` 사용례가 이미 있으며, 대부분은 `std::regex_error`, `std::filesystem_error`, locale 변환, parallel/XASL spawner cleanup 같은 표준 라이브러리/경계 레이어 예외를 CUBRID error code로 변환하는 용도다. 이번 PR의 `catch (std::bad_alloc &)` 도 예외를 일반 control flow로 쓰려는 것이 아니라, `std::vector::reserve()`/`resize()`/`push_back()` 실패를 `ER_OUT_OF_VIRTUAL_MEMORY` 로 변환하는 좁은 OOM boundary다.

`std::vector::reserve()` 자체에는 `nothrow` API가 없으므로, `std::vector` 를 유지하는 한 allocation failure를 호출 지점에서 CUBRID error stack으로 바꾸는 표준적인 방법은 `std::bad_alloc` 을 catch하는 것이다. Strict no-exceptions 관례를 더 강하게 적용해야 한다면 대안은 `std::vector` 를 쓰지 않고 `batched_values`, `requests`, `pending`, `groups/continuations` 를 `db_private_alloc()`/`malloc()` 기반의 explicit scratch array + count + `cubbase::span` 으로 바꾸는 것이다. 현재 PR에서는 좁은 `std::bad_alloc` catch를 유지하고, 프로젝트 정책상 engine helper에서 STL allocation exception boundary도 금지한다는 결론이 나면 위 explicit-array 방식으로 치환하겠다.

## JIRA Context

CBRD-27006은 CBRD-26583의 sub-task이며 목적은 한 heap record 안의 여러 OOS 값이 가능한 같은 OOS page에 모이도록 recdes locality를 개선하는 것이다. PR은 on-disk OOS format, OOS OID 공유 정책, replication log format을 바꾸지 않는다는 범위와 일치한다.

## Existing Comments

| User | Path | Summary |
|---|---|---|
| greptile-apps[bot] | `src/storage/heap_file.c` | `batched_values.resize()` 뒤 중복 초기화 루프 제거 제안. |
| greptile-apps[bot] | `src/storage/heap_file.c` | OOS replication publication state clear 시점 이동으로 stale state가 남을 수 있다는 방어적 지적. |
