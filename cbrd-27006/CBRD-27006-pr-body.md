https://jira.cubrid.org/browse/CBRD-27006

## Purpose

- OOS (큰 가변 길이 컬럼 값을 heap record 밖의 OOS file에 저장하는 방식)에서 한 record의 여러 OOS 값이 서로 다른 page로 흩어지고, 읽을 때도 값마다 page fix가 반복될 수 있었습니다.
- AS-IS: OOS 값마다 insert/read를 따로 처리해서 같은 record의 값도 page 배치와 read가 독립적으로 움직였습니다.
- TO-BE: 같은 record의 single-chunk OOS 값은 가능한 한 같은 OOS page에 넣고, 읽을 때는 같은 head page의 OOS 값을 묶어서 읽습니다.

## Implementation

- `src/storage/oos_file.cpp` 에 `oos_insert_many()` 와 `oos_read_many()` 를 추가했습니다.
- `oos_insert_many()` 는 attribute order를 유지하며 single-chunk 값을 page capacity 안의 greedy run으로 묶고, multi-chunk 값은 기존 chain insert를 유지합니다.
- `oos_read_many()` 는 같은 `(volid,pageid)` head page를 가리키는 요청을 한 read latch에서 처리하고, multi-chunk tail은 page를 놓은 뒤 기존 경로로 이어 읽습니다.
- OOS inline reference 파싱, grouped prefetch, OOS-side insert delegation, record Expand read를 `heap_oos.cpp` 로 모아 `heap_file.c` 의 OOS 결합도를 줄였습니다.
- Public OOS insert API가 replication용 OOS OID publication을 직접 맡도록 정리하고, 실패 시 partial publication state를 지웁니다.
- OOS unit test와 SQL CRUD test에 locality, grouped read, mixed single/multi-chunk, dispatch gating case를 추가했습니다.

## Remarks

- On-disk OOS format, inline slot layout, OOS OID 공유 정책, multi-chunk chain, replication log format은 바꾸지 않습니다.
- 리뷰 시 `oos_insert_many()` 의 placement 단위, publication 책임 이동, `oos_read_many()` 의 head-page grouping, lazy Resolve dispatch 조건을 먼저 보면 됩니다.
- 자세한 설명: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27006/CBRD-27006-oos-recdes-locality.md
