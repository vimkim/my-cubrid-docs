https://jira.cubrid.org/browse/CBRD-27230

> **#8434 merge 후에만 merge 가능.** 이 PR은 #8434 (CBRD-27781, OOS chain을 commit 뒤에 회수) 위에 쌓은 변경입니다. #8434가 `feature/oos-merge` 에 들어가기 전까지는 이 PR의 diff에 #8434의 commit 17개가 함께 보입니다. 이 PR의 리뷰 대상은 마지막 4개 commit입니다.

## Purpose

- UPDATE가 OOS (큰 값을 heap 밖 별도 파일에 두는 저장 방식) 컬럼을 건드리지 않아도, 그 값을 다시 읽고 새로 저장했습니다.
- AS-IS: `UPDATE t SET k = k + 1` 이 바꾸지 않은 8 KB OOS 값까지 `oos_read` 후 `oos_insert` 합니다. OOS 파일이 한때 두 배로 커지고, vacuum이 옛 값을 회수합니다.
- TO-BE: UPDATE가 할당하지 않은 OOS 컬럼은 옛 버전의 24 B stub (값의 위치와 identity를 담은 참조) 을 그대로 복사해 기존 chain을 재사용합니다.

## Implementation

- `heap_oos_column_plan` 에 재사용 표시와 stub 사본을 둡니다. 재사용 컬럼은 `heap_attrinfo_set_uninitialized` 에서 읽지 않고, layout은 24 B stub으로 계산하며, writer는 stub을 그대로 씁니다.
- 재사용 조건: `locator_attribute_info_force` 의 UPDATE (잠근 최신 버전), MVCC update, partition이 아닌 class, 할당·증가하지 않은 컬럼, 현재 representation의 record. 그 밖에는 기존 경로입니다.
- 버린 chain 계산은 #8434의 "옛 stub − 새 stub" 그대로이므로, 재사용 chain은 알림에 오르지 않습니다. 이를 debug assert로 확인합니다.
- 복제: 재사용 컬럼 자리에 `RVREPL_OOS_REUSE` marker를 보냅니다. replica는 자기 최신 버전에서 같은 attribute의 stub을 가져오고, 값 길이가 다르면 오류로 멈춥니다. applylogdb sql.log는 재사용 컬럼을 SET에서 뺍니다.

## Remarks

- 검증: OOS ctest 69/69 통과 (debug). 새 `test_oos_update_reuse_server` 는 재사용, 혼합 UPDATE, vacuum 회수, snapshot 대기, statement/savepoint/transaction rollback, 재사용 제외 경우를 확인합니다. crash recovery test는 재사용 chain을 포함합니다.
- 재사용 뒤 in-place 재작성 (ALTER ... CHANGE) 이 공유 chain을 commit 때 회수해도, 그보다 오래된 snapshot은 그 chain을 읽지 못합니다. in-place 재작성이 이전 버전 링크를 지워 그 snapshot은 재사용 여부와 관계없이 행을 보지 못하기 때문입니다 (`OldSnapshotAcrossInPlaceRewriteOfReusedChainMatchesNewChains`, 재사용 없는 경우와 같은 결과로 통과). partition 이동은 MVCC delete라 vacuum이 snapshot을 기다립니다 (`OldSnapshotReadsTheReusedChainAfterTheRowIsDeleted` 통과).
- 성능 (release, 서버 instruction, 8 KB S5 `UPDATE t SET k = k + 1`): #8434 대비 x0.15 (io) / x0.28 (warm). UPDATE 뒤 OOS 페이지 수는 그대로입니다. 결과 digest와 checksum은 develop과 일치합니다.
- 설계는 TLA+ 모델로 확인했습니다. 안전 속성 3개와 liveness가 통과했고, 결정을 하나씩 되돌린 통제 9개는 각자 지키는 속성에서 실패합니다.
- 미검증: 실제 HA 2대 구성, applylogdb 실행. 내용이 이미 어긋난 replica는 재사용 컬럼의 낡은 값을 유지합니다 (매뉴얼은 불일치 시 replica 재구축을 요구합니다).
- 상세 설계와 측정: [design-a-prime-detail.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27230/design-a-prime-detail.md), [perf/report.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27230/perf/report.md)
