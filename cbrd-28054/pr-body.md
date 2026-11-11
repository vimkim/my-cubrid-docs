https://jira.cubrid.org/browse/CBRD-28054

## Purpose

- OOS(CBRD-26357)의 대안 설계 후보인 Inner Table을 실제 엔진에서 검증하는 POC입니다. 병합 대상이 아니며, 설계 비교를 위한 draft PR입니다.
- AS-IS: 큰 값을 행 밖에 두려면 OOS처럼 전용 파일과 전용 삭제·회수·복구 경로가 필요합니다.
- TO-BE: 큰 VARCHAR·VARBIT 값을 숨은 companion 테이블(`<T>__inner`)의 일반 MVCC 행(chunk 행)으로 저장합니다. 원래 행에는 논리 값 ID를 가리키는 28바이트 참조만 남습니다. 삭제·회수·복구는 기존 heap, B-tree, vacuum 경로가 맡습니다.

## Implementation

- `src/storage/inner_table.cpp`: 쓰기 시 큰 값을 chunk 행으로 옮기고(`inner_table_rewrite`), 읽기 시 참조를 값으로 펼칩니다(`inner_table_expand`). 덮어쓰기와 DELETE는 이전 chunk 행을 MVCC DELETE로 은퇴시킵니다.
- 쓰기 hook은 `locator_sr.c`, 읽기 hook은 `heap_file.c`의 fetch 출구에 있습니다. 큰 값 컬럼을 읽지 않는 스캔은 참조를 펼치지 않습니다(`scan_manager.c`).
- `schema_manager.c`: DROP, TRUNCATE, RENAME이 companion으로 같은 savepoint 안에서 전파됩니다. companion에 직접 거는 같은 DDL은 거부합니다. unloaddb는 companion의 데이터를 건너뛰고, loaddb는 BU lock으로 chunk 행을 씁니다.
- 기능은 숨은 파라미터 `inner_table_threshold`가 0보다 클 때만 켜집니다.
- 이 브랜치는 POC의 전제로 CBRD-27935, CBRD-27936의 수정 커밋을 포함합니다. 두 수정의 upstream 반영은 별도로 진행됩니다.

## Remarks

- 수락 driver는 `contrib/benchmarks/inner_table/`에 있습니다. 각 driver에는 일부러 틀린 입력을 넣었을 때 실패하는지 보는 대조군이 있습니다.
- VERIFIED: storage(2개 case), recovery(8개 crash 시점, 두 번씩 restart), reclamation, transport(인덱스, trigger, DDL, unloaddb/loaddb), projection.
- projection: 작은 컬럼 집계가 읽는 데이터 페이지는 6~10개입니다. 기준 테이블은 802~1004개입니다.
- unused(release 빌드, 20만 행): 기능을 쓰지 않거나 큰 값이 없는 테이블의 INSERT, SELECT, UPDATE, DELETE에서 명령어 수 비율이 모두 0.958 이상입니다.
- 시간 기준 비용은 공용 서버 부하 때문에 아직 확정하지 못했습니다. 큰 값이 없는 테이블의 UPDATE는 시간 비율이 0.84로 나왔습니다. 이것이 실제 비용인지 서버 부하 때문인지는 아직 가르지 못했습니다.
- 남은 일: CDC·flashback, HA, TDE, 이전 바이너리 호환성, SQL·shell·medium 회귀.
- 알려진 한계: companion이 `db_class`에 보이고 직접 DML할 수 있습니다. FK cascade TRUNCATE는 자식의 companion에 전파되지 않습니다.
