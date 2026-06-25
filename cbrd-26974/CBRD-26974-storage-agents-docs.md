# CBRD-26974 Storage AGENTS 문서 정리

## Purpose

`CBRD-26974`는 `src/storage`의 `AGENTS.md`를 정리하는 작업이다. 저장소 모듈은 파일 수가 많고 큰 파일도
많아서, 에이전트가 작업 시작점을 빠르게 찾을 수 있는 문서 구조가 필요하다.

기존 `src/storage/AGENTS.md`는 짧고 유용했지만, `btree.c`, `heap_file.c`, `page_buffer.c`처럼 매우 큰 파일의
세부 진입점을 안내하기에는 정보가 부족했다.

반대로 모든 파일마다 별도 문서를 만들면 문서 수가 너무 많아지고, 작은 파일에는 반복 설명만 생길 가능성이
높다. 그래서 상위 문서는 짧은 길이를 유지하고, 세부 내용은 주제별 참고 문서로 나누는 방식을 선택했다.

## Implementation

`src/storage/AGENTS.md`를 저장소 모듈의 인덱스 문서로 다시 작성했다. 이 파일은 모듈 범위, 빌드 모드 경계,
주요 파일, 작업별 시작 지점, 핵심 식별자, 버퍼 풀 사용 규칙, 저장소 전용 주의 사항을 담는다.

기존 문서의 "서버 전용" 설명을 수정했다. `src/storage`의 대부분은 `SERVER_MODE`와 `SA_MODE`에서 동작하지만,
`byte_order.c`, `es.c`, `es_common.c`, `es_posix.c`, `file_io.c`, `oid.c`, `statistics_cl.c`,
`storage_common.c`, `tde.c`는 `cubridcs`에도 포함된다. UNIX 빌드에서는 `es_owfs.c`도 클라이언트 쪽 목록에
추가된다.

세부 문서 7개를 `src/storage/docs/` 아래에 추가했다.

- `src/storage/docs/storage-foundations.md`: `VPID`, `VFID`, `HFID`, `BTID`, `OID`, `RECDES` 같은 공통 식별자와
  레코드 보조 코드를 설명한다.
- `src/storage/docs/buffer-io-durability.md`: `page_buffer.c`, `file_io.c`, double-write buffer, TDE 관련 진입점과
  페이지 fix/unfix 규칙을 설명한다.
- `src/storage/docs/disk-file-space.md`: `disk_manager.c`, `file_manager.c`, `extendible_hash.c`의 볼륨, 섹터, 파일
  할당 흐름을 설명한다.
- `src/storage/docs/heap-record-pages.md`: `heap_file.c`, `slotted_page.c`, `overflow_file.c`의 레코드, 스캔, MVCC
  버전, overflow 흐름을 설명한다.
- `src/storage/docs/btree-indexes.md`: `btree.c`, `btree_load.c`, `btree_unique.cpp`, `external_sort.c`의 인덱스 탐색,
  range scan, insert/delete, bulk load 진입점을 설명한다.
- `src/storage/docs/catalog-statistics-maintenance.md`: `system_catalog.c`, `catalog_class.c`, `statistics_cl.c`,
  `statistics_sr.c`, `compactdb_sr.c`의 catalog 및 statistics 흐름을 설명한다.
- `src/storage/docs/external-storage-lob.md`: `es.c`, `es_posix.c`, `es_owfs.c`의 external storage URI 처리와 LOB
  관련 backend 흐름을 설명한다.

문서 안의 함수명은 실제 코드에서 확인한 이름만 사용했다. 예를 들어 B-tree range scan은 `btree_range_scan()`,
heap visibility는 `heap_get_visible_version()`, page buffer는 `pgbuf_fix*()`, `pgbuf_unfix*()`,
`pgbuf_set_dirty*()`를 기준으로 안내한다.

## Remarks

이 변경은 문서만 수정한다. C/C++ 소스, 빌드 설정, 테스트 코드는 변경하지 않는다.

리뷰할 때는 `src/storage/AGENTS.md`가 너무 길어지지 않았는지, 그리고 새 `src/storage/docs/` 문서들이
실제 파일 구조와 맞는지 먼저 보면 된다. 특히 `SERVER_MODE`, `SA_MODE`, `CS_MODE` 경계가 잘못 적히면
에이전트가 잘못된 API를 사용할 수 있으므로 그 부분을 주의해서 확인해야 한다.

검증은 markdown 링크 존재 여부, trailing whitespace 여부, `git diff --cached --check`로 수행했다. 코드 변경이
없어서 빌드와 SQL 테스트는 실행하지 않았다.
