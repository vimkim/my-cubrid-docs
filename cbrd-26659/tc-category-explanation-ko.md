# 추가한 OOS TC 목록과 설명

작성·갱신: 2026-10-15 (Asia/Seoul). CBRD-26659 / [조정 PR #8128](https://github.com/CUBRID/cubrid/pull/8128).

[흰 배경의 HTML 설명서 열기](tc-category-guide-ko.html#tc-list). TC 이름을 누르면 해당 파일의 상세 설명으로 이동합니다. 상세 설명에는 추가한 이유, 확인 순서, 결과와 원본 코드 링크가 있습니다.

추가한 TC 파일은 SQL 17개와 Shell 18개, 총 35개입니다. 실패 재현용 Shell 4개도 포함합니다. helper 파일은 세지 않았습니다.

| 분류 | TC 이름 · 상세 설명 | 무엇을 확인하나 | 왜 추가했나 |
| --- | --- | --- | --- |
| 값 저장·복사 | [cbrd_26659_oos_sql01_insert_select.sql](tc-category-guide-ko.html#tc-sql-sql01-insert-select) | 복사한 뒤 원본을 삭제해도 전체 값이 같은지 확인합니다. | 복사본이 원본의 저장 공간에 잘못 의존하는 오류를 찾습니다. |
| 값 저장·복사 | [cbrd_26659_oos_representation.sql](tc-category-guide-ko.html#tc-sql-representation) | NULL, 빈 값, 작은 값과 큰 값을 정확히 읽는지 확인합니다. | 저장 형태가 달라질 때 값의 의미가 바뀌는 오류를 찾습니다. |
| 값 저장·복사 | [cbrd_26659_oos_chunk_boundaries.sql](tc-category-guide-ko.html#tc-sql-chunk-boundaries) | 조각 수가 바뀌는 크기의 값을 복사·수정한 뒤 읽습니다. | 값의 앞·중간·끝이 빠지거나 겹치는 오류를 찾습니다. |
| 값 저장·복사 | [cbrd_26659_oos_vot_many_attributes.sql](tc-category-guide-ko.html#tc-sql-vot-many-attributes) | 여러 속성과 길이 경계에서 각 값을 정확히 읽는지 확인합니다. | 행 내부의 값 위치 정보가 달라질 때 잘못된 속성을 읽는 오류를 찾습니다. |
| 값 저장·복사 | [cbrd_26659_oos_sql09_lob_copy.sql](tc-category-guide-ko.html#tc-sql-sql09-lob-copy) | BLOB/CLOB 복사 뒤 원본을 지워도 내용을 읽는지 확인합니다. | 복사한 LOB가 삭제된 원본 파일에 의존하는 오류를 찾습니다. |
| 값 저장·복사 | [cbrd_26659_oos_sql09_lob_maxcols.sql](tc-category-guide-ko.html#tc-sql-sql09-lob-maxcols) | 너무 큰 조합은 거부하고 합법적인 이웃 입력은 허용하는지 확인합니다. | 거부된 INSERT가 일부 행을 남기거나 정상 입력까지 거부하는 오류를 찾습니다. |
| 값 저장·복사 | [cbrd_26659_representation_chunks.sh](tc-category-guide-ko.html#tc-shell-representation-chunks) | OOS 파일 유무, 저장 조각 수와 바이트 합을 확인합니다. | 값 조회만으로 알 수 없는 잘못된 저장 선택과 분할을 찾습니다. |
| 값 저장·복사 | [cbrd_26659_lob_locators.sh](tc-category-guide-ko.html#tc-shell-lob-locators) | LOB 위치 정보의 OOS 저장과 복사본 파일의 생존을 확인합니다. | 값과 파일 위치 정보 중 한쪽만 정상인 상태를 놓치지 않게 합니다. |
| 수정·취소·조회 | [cbrd_26659_oos_sql04_update.sql](tc-category-guide-ko.html#tc-sql-sql04-update) | 값을 키우고 줄이거나 일부 속성만 바꾼 뒤 전체 행을 비교합니다. | 수정하지 않은 값이나 다른 행까지 바뀌는 오류를 찾습니다. |
| 수정·취소·조회 | [cbrd_26659_oos_sql04_delete.sql](tc-category-guide-ko.html#tc-sql-sql04-delete) | DELETE·TRUNCATE·재삽입 뒤 남아야 할 행을 확인합니다. | 삭제가 다른 행의 큰 값을 손상시키는 오류를 찾습니다. |
| 수정·취소·조회 | [cbrd_26659_oos_sql05_transactions.sql](tc-category-guide-ko.html#tc-sql-sql05-transactions) | ROLLBACK과 SAVEPOINT가 정해진 범위만 취소하는지 확인합니다. | 큰 값의 변경 취소가 원래 값이나 앞선 정상 작업까지 지우는 오류를 찾습니다. |
| 수정·취소·조회 | [cbrd_26659_oos_sql05_constraints.sql](tc-category-guide-ko.html#tc-sql-sql05-constraints) | UNIQUE·NOT NULL 등으로 쓰기를 거부한 뒤 값을 확인합니다. | 실패한 문장이 일부 변경을 남기거나 앞선 정상 작업을 지우는 오류를 찾습니다. |
| 수정·취소·조회 | [cbrd_26659_oos_sql05_bigone.sql](tc-category-guide-ko.html#tc-sql-sql05-bigone) | OOS와 기존 큰 행 저장 방식의 지원하지 않는 조합을 확인합니다. | 실패가 기존 값을 바꾸거나 합법적인 큰 행까지 거부하는 오류를 찾습니다. |
| 수정·취소·조회 | [cbrd_26659_oos_sql06_triggers.sql](tc-category-guide-ko.html#tc-sql-sql06-triggers) | 트리거의 로그·복사 행과 거부 뒤 원래 값을 확인합니다. | 거부된 변경이 로그나 복사 표에 잘못 남는 오류를 찾습니다. |
| 수정·취소·조회 | [cbrd_26659_oos_sql07_read_paths.sql](tc-category-guide-ko.html#tc-sql-sql07-read-paths) | 인덱스·조인·정렬·집계 등에서 전체 값이 같은지 확인합니다. | 단순 조회는 통과해도 다른 읽기 경로에서 값을 잘못 읽는 오류를 찾습니다. |
| 수정·취소·조회 | [cbrd_26659_dml_transitions.sh](tc-category-guide-ko.html#tc-shell-dml-transitions) | 값 크기가 바뀔 때 OOS 조각 수가 어떻게 바뀌는지 확인합니다. | 값은 맞아도 현재 저장 상태가 잘못된 경우를 찾습니다. |
| 수정·취소·조회 | [cbrd_26659_transactions.sh](tc-category-guide-ko.html#tc-shell-transactions) | 값·오류 결과와 함께 작업 중인 OOS 저장 상태를 확인합니다. | 논리 값 비교만으로 알 수 없는 OOS 사용 상태를 확인하기 위해 추가했습니다. |
| 수정·취소·조회 | [cbrd_26659_read_paths.sh](tc-category-guide-ko.html#tc-shell-read-paths) | 4개 조회 계획, OOS 소유 관계와 복사본 생존을 확인합니다. | 의도한 읽기 경로와 실제 저장 상태를 별도 실행에서 확인하기 위해 추가했습니다. |
| 정책·표 구조 | [cbrd_26659_oos_storage_policy.sql](tc-category-guide-ko.html#tc-sql-storage-policy) | 정책을 지정·변경·생략한 뒤 정책 정보와 값을 확인합니다. | 정책 변경이 잘못 저장되거나 지원하지 않는 자료형에 적용되는 오류를 찾습니다. |
| 정책·표 구조 | [cbrd_26659_oos_schema.sql](tc-category-guide-ko.html#tc-sql-schema) | 열 추가·삭제·순서·길이 변경 뒤 남아야 할 값을 확인합니다. | 행 구조가 바뀌면서 OOS 값을 잘못 읽는 오류를 찾습니다. |
| 정책·표 구조 | [cbrd_26659_oos_partition_routing.sql](tc-category-guide-ko.html#tc-sql-partition-routing) | 행이 올바른 파티션에 들어가고 중복 입력을 거부하는지 확인합니다. | 처음 행을 넣는 동작과 파티션 이동의 문제를 나누어 확인하기 위해 추가했습니다. |
| 정책·표 구조 | [cbrd_26659_oos_partition.sql](tc-category-guide-ko.html#tc-sql-partition) | 파티션 경계를 넘는 UPDATE와 재구성 뒤 값을 확인합니다. | 행을 이동할 때 OOS 값이나 복제 처리 상태가 깨지는 오류를 찾습니다. |
| 정책·표 구조 | [cbrd_26659_schema_policy.sh](tc-category-guide-ko.html#tc-shell-schema-policy) | 저장 정책과 열 변경 뒤 실제 OOS 배치와 소유자를 확인합니다. | 메타데이터가 맞아도 값을 잘못 옮기거나 파일을 잘못 연결하는 오류를 찾습니다. |
| 정책·표 구조 | [cbrd_26659_partition_owner.sh · 실패 기록](tc-category-guide-ko.html#tc-shell-partition-owner) | OOS 파일이 목적지 자식 표에 속하는지 확인합니다. | 값 조회가 맞아도 파일 소유자가 잘못된 오류를 찾습니다. |
| 정책·표 구조 | [cbrd_26659_owner_drop.sh](tc-category-guide-ko.html#tc-shell-owner-drop) | 원본 DROP 때 원본 파일만 사라지는지 확인합니다. | 원본 삭제가 복사본의 저장 파일까지 지우는 오류를 찾습니다. |
| 동시 읽기·정리 | [cbrd_26659_snapshot_visibility.sh](tc-category-guide-ko.html#tc-shell-snapshot-visibility) | 다른 사용자가 수정해도 기존 읽기가 옛 값을 유지하는지 확인합니다. | 아직 필요한 옛 OOS 값을 너무 일찍 지우는 오류를 찾습니다. |
| 동시 읽기·정리 | [cbrd_26659_snapshots_reclaim.sh · 실패 기록](tc-category-guide-ko.html#tc-shell-snapshots-reclaim) | 옛 값 정리 뒤 빈 OOS 페이지가 반환되는지 확인합니다. | 청크는 줄어도 저장 페이지가 계속 남는 문제를 찾습니다. |
| 동시 읽기·정리 | [cbrd_27237_rollback_vacuum.sh · 실패 기록](tc-category-guide-ko.html#tc-shell-rollback-vacuum) | ROLLBACK한 값을 vacuum 이후에도 읽는지 확인합니다. | 취소 직후에는 읽히지만 나중의 정리 작업이 값을 지우는 오류를 찾습니다. |
| 장애 복구 | [cbrd_26659_crash_committed.sh](tc-category-guide-ko.html#tc-shell-crash-committed) | 완료 응답을 받은 변경이 서버 강제 종료 뒤에도 남는지 확인합니다. | 정상 종료에서는 보이지 않는 OOS 복구 로그의 누락을 찾습니다. |
| 장애 복구 | [cbrd_26659_crash_undo.sh](tc-category-guide-ko.html#tc-shell-crash-undo) | COMMIT하지 않은 변경을 복구가 원래 상태로 되돌리는지 확인합니다. | 디스크에 기록된 미커밋 변경을 커밋된 값으로 남기는 오류를 찾습니다. |
| 관리 도구 | [cbrd_26659_utility_cs.sh](tc-category-guide-ko.html#tc-shell-utility-cs) | 내보내기·가져오기·compact 뒤 값과 실제 OOS 배치를 확인합니다. | 관리 도구의 읽기·쓰기 경로가 큰 값을 잘못 다루는 오류를 찾습니다. |
| 관리 도구 | [cbrd_26659_utility_sa.sh](tc-category-guide-ko.html#tc-shell-utility-sa) | SA unload/load·compact 뒤 전체 값과 표 구조를 확인합니다. | 서버를 쓰지 않는 도구 경로에서도 값이 보존되는지 확인하기 위해 추가했습니다. |
| 관리 도구 | [cbrd_26659_utility_sa_physical.sh · 실패 기록](tc-category-guide-ko.html#tc-shell-utility-sa-physical) | SA로 가져온 목적지에도 OOS 파일이 생기는지 확인합니다. | 값만 맞고 의도한 OOS 저장 경로가 실행되지 않는 문제를 찾습니다. |
| 관리 도구 | [cbrd_26659_backup_restore.sh](tc-category-guide-ko.html#tc-shell-backup-restore) | 원본 엔진 파일을 없앤 뒤 백업만으로 값을 복원하는지 확인합니다. | 남아 있는 원본 파일을 읽고 복원 성공으로 착각하는 경우를 막습니다. |
| 암호화 | [cbrd_26659_tde_wal.sh](tc-category-guide-ko.html#tc-shell-tde-wal) | 새 OOS 파일의 암호화와 복구 로그 플래그를 확인합니다. | 표의 암호화 설정만 맞고 별도 파일이나 로그 경로가 빠지는 문제를 찾습니다. |

SQL은 읽은 값과 동작을 확인합니다. Shell은 별도 테스트용 DB의 파일·저장 조각·소유 관계도 확인합니다. 두 실행은 서로 다른 DB를 사용합니다.

목록과 날짜별 결과는 [10월 8일 검증 기록](ci-replan/delivery/14-complete-local-validation.md), [10월 12일 Shell 재검증](ci-replan/shell-conversion-results-20261012.md), [10월 13일 SQL 수리 기록](ci-repair/repair-results.md)을 근거로 작성했습니다. 원본 코드 링크는 HTML의 [리비전 목록](tc-category-guide-ko.html#evidence)에서 확인할 수 있습니다.

10월 13일에는 full partition을 포함한 원래 SQL 72개가 통과했습니다. 파티션의 물리 소유권 결함은 별개로 남았습니다. 전체 CI도 Shell 7개 실패로 FAILURE였습니다. 실행별 한계는 [수리 추적표](ci-repair/README.md)에 있습니다.

기존 R01~R31은 TC 파일 수가 아닌 동작별 검증 번호입니다. [번호별 참고 설명](tc-category-guide-ko.html#behavior-reference)에 구현 공백·확인 수단 공백·유예 범위를 남겼습니다. 이 문서 수정 중 새 DB·CI 실행은 하지 않았습니다.
