https://jira.cubrid.org/browse/CBRD-XXXXX

## Purpose

- vacuum이 다른 페이지로 옮겨진 행을 지우다 실패하거나 서버가 중단되면, 그 사이 다른 트랜잭션이 commit한 행을 덮어써 DB가 손상되는 문제를 고칩니다.
- AS-IS: vacuum은 옮겨진 행의 데이터 슬롯(forward 슬롯)을 비운 직후 그 페이지를 놓고, 같은 내부 작업(sysop) 안에서 OOS 값을 지웁니다. 그 사이 다른 트랜잭션이 슬롯을 재사용한 뒤 sysop이 취소되면, 취소 처리가 옛 행을 그 슬롯에 다시 씁니다.
- TO-BE: sysop이 끝날 때까지 forward 페이지를 잡아 두므로, 취소 처리가 되돌릴 슬롯을 다른 트랜잭션이 쓰지 못합니다.

## Implementation

- `vacuum_heap_record`의 `REC_RELOCATION` 경로에서 forward 페이지를 `log_sysop_commit` 뒤에 놓습니다. `pgbuf_set_dirty`의 `FREE`를 `DONT_FREE`로 바꾸고, commit 뒤에 `pgbuf_unfix_and_init`을 호출합니다.
- OOS 삭제가 실패하면 기존처럼 sysop을 abort하고 반환합니다. 호출자가 이미 forward 페이지를 놓으므로 오류 처리는 바꾸지 않았습니다.
- 페이지를 잡는 순서는 `REC_HOME`의 OOS 경로와 같습니다. heap 페이지를 잡은 채 OOS 페이지를 잡으며, OOS 삭제는 heap 페이지나 heap 헤더를 잡지 않습니다.

## Remarks

- PR 7990의 [hornetmj 리뷰 R5](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409499688)에 대응합니다.
- 수정 전 소스에 재현 전용 계측을 넣어 이 구간을 넓혔습니다. commit된 INSERT가 그 슬롯에 들어간 뒤 실패를 주입하자, debug는 `spage_insert_for_recovery`의 assertion으로 종료했고 재시작 복구도 같은 assertion에서 실패했습니다. release는 페이지의 레코드 수가 어긋나 `spage_compact` FATAL로 종료했습니다. OOS 삭제 실패 없이 서버를 `kill -9`해도 재시작 복구가 같은 손상을 냈습니다.
- 수정 후 같은 계측으로 debug와 release에서 실패 주입과 서버 강제 종료를 각각 실행했습니다. INSERT는 forward 페이지를 기다린 뒤 진행했습니다. commit된 행이 인덱스와 heap에서 모두 조회됐고, vacuum 재시도가 OOS 값을 정리했으며, `checkdb`가 통과했습니다.
- 계측이 없는 이 커밋의 debug 빌드에서 구성된 CTest 44개가 모두 통과했습니다.
- 비용은 OOS 삭제 동안 forward 페이지를 더 오래 잡는 것입니다.
- 계측은 서버 코드에 환경 변수 검사를 넣으므로 이 PR에 포함하지 않았고, 자동 회귀 테스트도 추가하지 않았습니다. 재현 절차와 계측 원문은 JIRA에 있습니다.
- 실제 발생 빈도, 여러 조각(chunk)으로 나뉜 OOS 값의 삭제 도중 실패, DONT_REUSE_OID 테이블, HA 복제는 확인하지 않았습니다. OOS chunk 슬롯의 같은 부류 문제는 [CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781)에서 따로 다룹니다.
