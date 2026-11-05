# CBRD-27625~27627 송일한 공유 커밋 참고

## 조사 질문과 결론

송일한님이 공유한 `xmilex-git/cubrid`의 `CBRD-27625-27627` 브랜치에서 각 이슈에 해당하는 변경은 무엇이며, 향후 작업에 어떤 조건과 함께 참고해야 하는가?
독자는 세 이슈를 진행할 담당자다. 범위는 JIRA 요구사항, 커밋별 코드 변경, 선행 관계, 향후 TODO 제안이다.
조사일은 **2026-11-05, Asia/Seoul**이며, 빌드·실행·성능 재측정 없이 원격 소스와 JIRA를 대조했다.

공유 브랜치에는 이슈별 커밋이 하나씩 있고, 순서는 **27625 → 27626 → 27627**이다.
27625는 임시 용도 볼륨 생성 시 DWB 쓰기를 줄이고, 27626은 임시 용도 볼륨의 동기화를 줄인다.
27627은 그 조건에서 인덱스 정렬 워커가 run 페이지를 직접 쓰도록 한다.
이 코드는 구현 참고 자료이며, 완료된 수정이나 검증된 적용안으로 취급하지 않는다. [고정 비교][compare-pinned]

## 출처와 확인한 리비전

- 공유 메시지는 "CBRD-27625~27627 이슈별로 커밋 나눠서 작업한거 공유드립니다. 이슈진행할때 참고해주세요"다. 원문은 사용자가 전달했다.
- 메시지의 비교 페이지 제목에서 [공유 비교 URL][compare-live]을 추정했고, 조회 결과 실제로 세 이슈의 커밋을 확인했다.
- 공유 저장소는 `xmilex-git/cubrid`, 브랜치는 `CBRD-27625-27627`, head는 `f045323d9e4bce8178ffdb5470325a0a7915a0a5`다.
- 공통 조상과 조회 당시 fork의 `develop`, upstream `CUBRID/cubrid`의 `develop`은 모두 `2362424f25bcebd1bd9733bddd59a993e2852ac5`다. [upstream 기준 커밋][upstream-base]
- 비교 결과는 `ahead_by=3`, `behind_by=0`, 변경 파일 7개다. 세 커밋은 조회 당시 upstream `develop`에 포함되지 않았다. [고정 비교][compare-pinned]
- `CUBRID/cubrid`에서 세 이슈 키로 PR을 검색했지만 관련 PR을 찾지 못했다. `xmilex-git/cubrid`의 브랜치명 PR 검색도 결과가 없었다. 검색 결과만으로 PR 부재를 단정하지 않는다.

세 이슈 모두 조회 당시 `Analysis`, `Unresolved`, `Minor`, 대상 버전 `guava`다.
담당자는 Daehyun Kim, 보고자는 Il Han, Song이고, 최종 수정일은 2026-10-28이다. [27625][jira25], [27626][jira26], [27627][jira27]

## 이슈와 커밋 대응

| JIRA 문제와 요구사항 | 공유 커밋 | 코드와 선행 관계 |
| --- | --- | --- |
| [CBRD-27625: skip dwb when temp write][jira25]. `addvoldb -p temp`의 전체 볼륨 재기록이 DWB를 거쳐 중복 쓰기와 블록별 대기가 발생한다. | [`3e1aa5a2c28bafd2eb0cc8f939294401dd8a0e76`][commit25], `(1/3)` | 헤더를 제외한 임시 용도 페이지는 직접 쓴다. 재기록 뒤 동기화를 보완하고 임시 용도 판정 함수를 공개한다. 27626이 이 함수를 사용한다. |
| [CBRD-27626: no fsync on temp][jira26]. 임시 용도 볼륨이 보상 동기화, 체크포인트, dismount, 백업에서 불필요하게 동기화된다. | [`e2d69faacffda4818aaf297aa75d8d222711b34a`][commit26], `(2/3)` | 해당 동기화와 임시 페이지의 보상 동기화 집계를 건너뛴다. 영구 임시 볼륨 생성 시 동기화 예외는 유지한다. 27625의 공개 함수를 사용하는 코드 의존성이 있다. |
| [CBRD-27627: btree sort workers write-through the sort run][jira27]. 버퍼보다 큰 인덱스 정렬에서 dirty run 페이지가 쌓여 워커가 빈 버퍼를 기다린다. | [`f045323d9e4bce8178ffdb5470325a0a7915a0a5`][commit27], `(3/3)` | 인덱스 정렬의 run 쓰기만 write-through로 바꾼다. 27626은 이 직접 쓰기가 보상 동기화를 늘리지 않는다는 성능 전제다. |

## CBRD-27625의 변경과 확인점

`fileio_reset_volume()`은 볼륨의 각 페이지에 임시 LSA를 설정하고 다시 쓴다.
공유 변경은 `fileio_write_or_add_to_dwb()`에서 영구 볼륨인지뿐 아니라 임시 용도인지도 검사한다.
임시 용도 볼륨에서는 `DISK_VOLHEADER_PAGE`만 DWB에 넣고, 나머지는 `fileio_write()`로 보낸다.
DWB를 건너뛰는 페이지에도 `volid`, `pageid`를 설정한다. [재기록과 쓰기 분기][source25]

DWB 동기화만으로 직접 쓴 모든 페이지의 동기화를 보장할 수 없다는 이유로, 재기록 뒤 `fileio_synchronize(..., true)` 호출을 추가한다.
해당 동기화가 실패하면 `ER_FAILED`를 반환한다. 이 변경은 생성 시 동기화 예외를 유지하는 코드다.
실제 생성 작업에서 fsync 계열 시스템 호출이 정확히 한 번 발생한다는 뜻은 아니다. [재기록 종료 처리][source-reset]

`pgbuf_is_temporary_purpose_volume()`은 기존 `pgbuf_is_temporary_volume()`을 공개하는 함수다.
기존 판정은 `LOG_ISRESTARTED()`가 false이면 false를 반환한다.
따라서 시작·복구 중에도 모든 볼륨을 같은 방식으로 분류한다고 확대 해석하면 안 된다. [판정 함수][source-purpose]

JIRA의 완료 조건은 DWB 블록 flush가 볼륨 크기에 비례하지 않는 것과 비정상 종료 뒤 재시작·`checkdb` 성공이다.
debug 빌드의 볼륨 추가 도중 종료에는 별도 결함 [CBRD-27571][jira27571]이 알려져 있다.
그 이슈는 조회 당시 `Develop`, `Unresolved`다. 이 세 커밋에는 그 결함을 수정하는 `log_manager.c` 변경이 없다. [27625 요구사항][jira25], [전체 변경 파일][compare-pinned]

## CBRD-27626의 변경과 확인점

볼륨 단위 판정은 자동 임시 볼륨 목록과 27625의 임시 용도 판정을 함께 사용한다.
시스템 볼륨과 미확인 descriptor에 해당하는 ID는 임시로 분류하지 않는다.
`fileio_dismount()`, `fileio_dismount_volume()`, `fileio_synchronize_volume()`에 이 판정을 적용한다. [커밋 전체 변경][commit26]

페이지 버퍼와 `fileio_write_or_add_to_dwb()`의 임시 쓰기는 `FILEIO_WRITE_NO_COMPENSATE_WRITE`를 사용한다.
이는 DWB를 껐을 때도 임시 페이지 쓰기를 보상 동기화 집계에서 빼는 변경이다. [페이지 쓰기][source-pb-write], [직접 쓰기][source25]

체크포인트는 `disk_set_checkpoint()`를 수행한 뒤 임시 용도 볼륨의 동기화만 건너뛴다.
백업은 dirty 페이지를 먼저 내리지만, 임시 용도 볼륨에 대한 `dwb_synchronize()`는 호출하지 않는다.
기존처럼 임시 용도 볼륨의 시스템 페이지만 백업하는 경로다. [체크포인트][source-checkpoint], [백업][source-backup]

`disk_format()`은 자동 임시 볼륨 생성 시 마지막 동기화를 생략하고, 영구 볼륨에는 유지한다.
27625의 영구 임시 볼륨 재기록 후 동기화도 남아 있다. [볼륨 생성][source-format], [재기록 종료 처리][source-reset]

JIRA는 [CBRD-27093][jira27093] 이후 DWB를 끈 서버에서 영구 임시 볼륨의 동기화 비용이 드러났다고 설명한다.
향후 적용 시 영구 데이터 볼륨의 동기화를 보존하는 것이 조건이다.
이는 JIRA가 명시한 배경이며, 이번 조사는 CBRD-27093의 코드와 백포트 전체를 별도로 검증하지 않았다. [27626의 관계 설명][jira26]

## CBRD-27627의 변경과 확인점

`pgbuf_copy_from_area()`는 페이지를 write latch로 fix하고 내용을 복사한 뒤 dirty로 표시한다.
새 `write_through` 인자가 true이면 페이지를 놓기 전에 `pgbuf_flush_with_wal()`을 호출하고 unfix한다.
기존 WAL·TDE 처리 경로를 사용하며, 새 비동기 쓰기나 버퍼 소유권 전달을 추가하지 않는다. [복사와 flush 순서][source-copy], [기존 flush 경로][source-pb-write]

`btsort_write_area()`는 true, 일반 질의 정렬의 `sort_write_area()`는 false를 전달한다.
요구사항의 대상은 온라인이 아닌 인덱스 생성, 제약 추가, `loaddb` 인덱스 적재다.
온라인 인덱스와 질의 정렬 제외는 JIRA의 범위이며, 이번 조사는 모든 상위 호출 경로를 실행해서 확인하지 않았다. [호출부 변경][commit27], [27627 요구사항][jira27]

flush 반환값은 버리고 `er_stack_push()`와 `er_stack_pop()`으로 호출자 오류 상태를 보존한다.
실제 페이지 쓰기 실패 시 기존 flush 경로가 dirty 상태와 `oldest_unflush_lsa`를 복원하므로, 페이지를 dirty로 남겨 이후 flush에 맡기는 의도다.
이를 디스크 쓰기 실패가 인덱스 생성 오류로 즉시 전달된다는 뜻으로 해석하면 안 된다. [새 호출부][source-copy], [쓰기 실패 복원][source-failure]

작은 인덱스는 run 페이지가 버퍼에 머물 수 있어도 먼저 쓰므로 쓰기량이 늘 수 있다.
JIRA에도 이 비용이 기록돼 있다. 성능 개선 수치는 공유자의 기존 측정이며, 이번 조사에서 재현하거나 새로 측정하지 않았다. [27627 요구사항과 측정][jira27]

## 향후 TODO 문안: 사용자 확인 전 제안

아래는 일정이 없는 대기 항목 제안이다. TODO·일정·JIRA·소스·원격 브랜치에는 등록하거나 반영하지 않았다.
진행 순서는 JIRA의 Blocks 관계와 공유 코드의 의존 관계를 함께 반영했다. 코드 적용 방식은 정하지 않았다.

1. **CBRD-27625 진행 시 송일한님 DWB 우회 커밋 검토·참고.** [3e1aa5a2][commit25]의 헤더 보호, 재기록 후 동기화, 27626과의 관계를 참고한다. 실제 이슈 진행 시 확인할 조건은 DWB 블록 flush, 비정상 종료 후 재시작·`checkdb`, debug 검증에 영향을 주는 CBRD-27571이다.
2. **CBRD-27626 진행 시 송일한님 임시 볼륨 동기화 제거 커밋 검토·참고.** [e2d69faa][commit26]와 27625의 선행 변경을 참고한다. 실제 이슈 진행 시 DWB 켬·끔, 체크포인트·dismount, 온라인 백업·복원, 생성 시 동기화 예외, CBRD-27093의 영구 데이터 볼륨 동기화 보존을 확인한다.
3. **CBRD-27627 진행 시 송일한님 인덱스 정렬 write-through 커밋 검토·참고.** [f045323d][commit27]와 27626의 동기화 조건을 참고한다. 실제 이슈 진행 시 큰 인덱스의 빈 버퍼 대기와 생성 시간, 조회 결과·`checkdb`, 작은 인덱스의 추가 I/O, 쓰기 실패 시 dirty 유지 동작을 확인한다. 온라인 인덱스와 일반 질의 정렬은 요구사항의 제외 범위다.

## 조회 방법과 한계

- `cubrid-jira search CBRD-27625`, `CBRD-27626`, `CBRD-27627`, `CBRD-27571`로 실제 JIRA와 댓글·연결 이슈를 조회했다.
- GitHub 플러그인 `github_compare_commits`에 `{repo_full_name: "xmilex-git/cubrid", base: "develop", head: "CBRD-27625-27627"}`를 전달했다. 이어서 양 끝을 위의 고정 SHA로 비교했다.
- `github_fetch_commit`으로 공유 head와 `~1`, `~2`, `~3`, upstream `develop`을 확인했다. `github_fetch_file`에 head SHA를 지정해 관련 코드와 실패 처리를 읽었다.
- `github_search_prs`로 upstream의 각 이슈 키와 fork의 브랜치명을 검색했다. 읽기 도구가 충분해 `gh` 대체 조회는 사용하지 않았다.
- CUBRID 소스 작업 트리와 브랜치를 바꾸거나 fetch하지 않았다. 빌드·테스트·CI, 시스템 호출 수, crash recovery 및 백업·복원 결과는 이번 조사로 검증하지 않았다.
- 관련 PR 미발견과 JIRA 상태는 조회 시점의 결과다. 적용 전에는 대상 브랜치, 이슈 상태, 공유 브랜치의 변경 여부를 다시 확인할 필요가 있다.

[compare-live]: https://github.com/xmilex-git/cubrid/compare/develop...CBRD-27625-27627
[compare-pinned]: https://github.com/xmilex-git/cubrid/compare/2362424f25bcebd1bd9733bddd59a993e2852ac5...f045323d9e4bce8178ffdb5470325a0a7915a0a5
[upstream-base]: https://github.com/CUBRID/cubrid/commit/2362424f25bcebd1bd9733bddd59a993e2852ac5
[jira25]: https://jira.cubrid.org/browse/CBRD-27625
[jira26]: https://jira.cubrid.org/browse/CBRD-27626
[jira27]: https://jira.cubrid.org/browse/CBRD-27627
[jira27571]: https://jira.cubrid.org/browse/CBRD-27571
[jira27093]: https://jira.cubrid.org/browse/CBRD-27093
[commit25]: https://github.com/xmilex-git/cubrid/commit/3e1aa5a2c28bafd2eb0cc8f939294401dd8a0e76
[commit26]: https://github.com/xmilex-git/cubrid/commit/e2d69faacffda4818aaf297aa75d8d222711b34a
[commit27]: https://github.com/xmilex-git/cubrid/commit/f045323d9e4bce8178ffdb5470325a0a7915a0a5
[source25]: https://github.com/xmilex-git/cubrid/blob/f045323d9e4bce8178ffdb5470325a0a7915a0a5/src/storage/file_io.c#L4058-L4116
[source-reset]: https://github.com/xmilex-git/cubrid/blob/f045323d9e4bce8178ffdb5470325a0a7915a0a5/src/storage/file_io.c#L2887-L2942
[source-purpose]: https://github.com/xmilex-git/cubrid/blob/f045323d9e4bce8178ffdb5470325a0a7915a0a5/src/storage/page_buffer.c#L5631-L5652
[source-format]: https://github.com/xmilex-git/cubrid/blob/f045323d9e4bce8178ffdb5470325a0a7915a0a5/src/storage/disk_manager.c#L753-L784
[source-pb-write]: https://github.com/xmilex-git/cubrid/blob/f045323d9e4bce8178ffdb5470325a0a7915a0a5/src/storage/page_buffer.c#L10934-L11115
[source-checkpoint]: https://github.com/xmilex-git/cubrid/blob/f045323d9e4bce8178ffdb5470325a0a7915a0a5/src/transaction/log_page_buffer.c#L7677-L7713
[source-backup]: https://github.com/xmilex-git/cubrid/blob/f045323d9e4bce8178ffdb5470325a0a7915a0a5/src/transaction/log_page_buffer.c#L7933-L7998
[source-copy]: https://github.com/xmilex-git/cubrid/blob/f045323d9e4bce8178ffdb5470325a0a7915a0a5/src/storage/page_buffer.c#L4871-L4962
[source-failure]: https://github.com/xmilex-git/cubrid/blob/f045323d9e4bce8178ffdb5470325a0a7915a0a5/src/storage/page_buffer.c#L11084-L11122
