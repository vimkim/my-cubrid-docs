확인했습니다. PR 8235는 이 경로를 고치지 않습니다. 8235가 바꾼 것은 `heap_remove_page_on_vacuum`의 대기자 처리와 병렬 힙 스캔, 통계 샘플링, 병렬 인덱스 생성의 페이지 순회입니다. `heap_oos_find_vfid`, `vacuum_heap_prepare_record`, `heap_alloc_new_pages`는 그대로이므로 develop을 머지해도 이 교착은 남습니다. 그래서 [CBRD-27860](https://jira.cubrid.org/browse/CBRD-27860)으로 따로 수정해 [#8350](https://github.com/CUBRID/cubrid/pull/8350)에 올렸습니다.

- **재현.** 실제 vacuum 워커를 쓰는 유닛 테스트 `OosRealVacuum.VacuumWaitsForHeapHeaderWithoutHoldingLastPage`로 같은 순환을 재현했습니다. vacuum이 마지막 힙 페이지를 쥔 채 `heap_oos_find_vfid`에서 힙 헤더를 기다렸고, 그동안 `heap_alloc_new_pages`는 약 316초 뒤 `ER_PAGE_LATCH_TIMEDOUT`으로 실패했습니다. debug 빌드는 `pgbuf_timed_sleep`의 assert에서 멈췄습니다.
- **수정.** 제안하신 대로 REC_BIGONE과 같은 방식입니다. 힙 헤더를 조건부로 먼저 시도하고, 바쁘면 힙 페이지를 놓은 뒤 헤더를 기다려 OOS 파일을 찾습니다. 그다음 home 페이지를 다시 잡고 슬롯부터 다시 확인합니다. REC_HOME과 REC_RELOCATION 모두 적용했고, REC_RELOCATION은 forward 페이지도 함께 놓습니다. 다시 시작은 레코드당 한 번으로 제한했습니다.
- **검증.** 수정 후 같은 테스트가 통과했습니다. CTest 전체 44건과 [gha-ci](https://github.com/CUBRID/cubrid/actions/runs/41390306929)(release·debug 빌드, shell·SQL·medium)도 통과했습니다.
- **확인하지 못한 것.** REC_RELOCATION 경로의 경합은 실행으로 재현하지 못했습니다. 두 경로는 같은 함수를 거치고, 차이는 forward 페이지를 놓는 것뿐입니다. SQL INSERT로 하는 종단 재현도 하지 않았습니다.
- **헤더 페이지 자체를 쥔 경우.** 말씀하신 29초 대기는 이 수정으로 줄지 않습니다. vacuum이 헤더 페이지를 WRITE로 쥐고 있으면 같은 스레드의 조건부 조회가 바로 성공해서, 페이지를 놓는 경로를 타지 않습니다. 교착은 아니어서 이번 범위에서는 제외했습니다.
