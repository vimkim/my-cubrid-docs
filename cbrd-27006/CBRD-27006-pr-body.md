https://jira.cubrid.org/browse/CBRD-27006

## Purpose

- OOS (큰 가변 길이 컬럼 값을 heap record 밖에 저장하는 방식)에서 한 record 안의 여러 OOS 컬럼이 서로 다른 OOS page로 흩어질 수 있었습니다.
- AS-IS: OOS 컬럼마다 insert/read를 따로 처리해서 `pgbuf_fix`와 bestspace 탐색이 반복되었습니다.
- TO-BE: 같은 record의 single-chunk OOS 값은 가능한 한 같은 OOS page에 넣고, 읽을 때도 같은 page의 OOS 값들을 묶어서 읽습니다.

## Implementation

- `src/storage/oos_file.cpp` 에 `oos_insert_many()` 와 `oos_read_many()` 를 추가했습니다.
- `heap_attrinfo_insert_to_oos()` 는 OOS 대상 컬럼을 attribute order로 모아 batch insert를 호출합니다.
- OOS read 경로(inline reference 파싱 `heap_oos_parse_inline_ref()`, OOS attribute 판별 `heap_oos_attr_inline_ptr()`, grouped read `heap_oos_read_dbvalues_grouped()`)를 `heap_oos.cpp` 로 옮겨 `heap_file.c` diff를 좁혔습니다. `heap_attrinfo_read_dbvalues()` 는 한 record에서 OOS 값이 2개 이상 요청될 때만 grouped 경로로 dispatch합니다.
- Public OOS insert API가 replication용 OOS OID publication을 직접 맡도록 정리했습니다.
- OOS unit test와 SQL CRUD test에 locality, grouped read, mixed single/multi-chunk case를 추가했습니다.

## Remarks

- On-disk OOS format, OOS OID 공유 정책, replication log format은 바꾸지 않습니다.
- 자세한 설명: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27006/CBRD-27006-oos-recdes-locality.md
