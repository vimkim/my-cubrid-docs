# cubrid-testcases-private PR #1632 리뷰 요약 (CBRD-26176 HA 테스트케이스)

- 날짜: 2026-08-13
- 대상: https://github.com/CUBRID/cubrid-testcases-private/pull/1632
- 브랜치: `add_CBRD-26176_ha_11.5` → `develop`
- 작성자: swi0110 (Song won-ryong)
- 결론: **Approve with minor comments** (블로킹 이슈 없음)

## PR 내용

Sharded lock-free bestspace index(CBRD-26176/26857) 재설계에 대한 HA shell 테스트케이스 2건 추가. CBRD-26775 인수 조건 "HA replication 이 정상 동작한다"를 검증하는 테스트가 없어서 추가된 것.

| 테스트케이스 | 케이스 수 | 검증 대상 |
|---|---|---|
| `HA/shell/_40_guava/cbrd_26176_ha` | 6 | master에서 bestspace 할당 경로(동시 INSERT, 이동 UPDATE, DELETE+refill, rollback 경합) 구동 후 slave와 대조 |
| `HA/shell/_40_guava/cbrd_26176_ha_failover` | 5 | standby 승격 노드의 bestspace 동작 + 역방향 복제 |

작성자 검증: release/debug 각 10회 × 2 스크립트 = 220건 케이스 판정 전부 OK, 코어/서버 .err 0건.

## 리뷰에서 확인한 사항 (정상)

QA 하네스 헬퍼(`cubrid-testtools`의 `init.sh`, `make_ha.sh`, `make_ha_upper.sh`, `ha_common.sh`) 실제 구현과 대조하여 확인:

- **케이스 수가 결정적**: 성공/실패와 무관하게 스크립트당 `write_ok`/`write_nok` 정확히 6회·5회 발생 (`compare_result_between_files`는 호출당 판정 1회).
- **산술 정확**: `mod(id,2)=0` 삭제 = 세션당 1000행, refill offset으로 PK 충돌 없음, `expected_t1 = 6×3000 = 18000` 등 일치.
- **복제 배리어 사용 올바름**: 노드 간 비교 전 `wait_for_slave`, 역방향은 `wait_for_slave_failover` (demoted 노드 로컬 polling — 헬퍼 실제 동작과 일치).
- **`compare_result_between_files`에 answer 아닌 일반 로그 파일 2개 전달해도 동작** (`get_best_compat_file` 통과), 부산물 `listdrv`도 정리됨.
- **모든 비교가 순서 비의존** (집계, `GROUP BY … ORDER BY`, PK `ORDER BY`) — CBRD-26176 병합이 기존 테스트를 깨뜨린 바로 그 속성.
- **fifo로 write end를 잡아두는 open transaction 패턴**이 csql EOF 자동실행 문제(c9885e87에서 수정한 함정) 회피.
- **승격 실패 시 조기 종료** (NOK 기록 → 정리 → `finish` → `exit 1`) — 기존 패턴(`cbrd_25651_1`, `cbrd_25858`)과 동일, 연쇄 오탐 방지.
- `wait_for_slave_active`는 `make_ha_upper.sh` → `ha_common.sh` 경유로 사용 가능. csql 오류 시 `row_count`/`slave_count`가 빈 값 → NOK (fail-safe 방향).
- 컨벤션 일치: `:<< END` 헤더, `init test` + `set -x`, setup/revert, 표준 `rm -f` 정리, 전 테이블 PK(applylogdb 요건), `csql -udba $dbname@$slaveHostName` slave 조회 — `cbrd_26374_ha` 등 이웃 테스트와 동일.

## 지적 사항 (minor)

1. **vacuum 공간 재사용 커버리지가 기회적(best-effort)** — DELETE와 refill 사이에 배리어가 없어 vacuum이 반납하기 전에 refill이 힙을 그냥 확장할 수 있음. 테스트가 이 때문에 실패하지는 않지만, 주석의 "vacuum이 반납한 공간의 재사용" 커버리지가 결정적으로 보장되지 않음. best-effort임을 주석으로 명시하거나 refill 전 대기 권장.
2. **`cbrd_26176_ha` 케이스 6 실패 시 진단 부족** — NOK에 카운트 3개만 기록. 동시 INSERT 세션이 실패(락 타임아웃 등)하면 케이스 1~5는 통과하고 6만 실패하는데 원인 로그가 없음. failover 스크립트처럼 `ins_t1_*`/`ins_t2_*` 로그를 NOK 파일에 `cat` 하도록 제안.
3. **failover 헤더 주석의 undo 위치 서술 부정확** — applylogdb는 커밋된 트랜잭션만 적용하므로 승격 노드에는 undo할 것이 없음. undo-vs-할당 경합은 케이스 5에서 *demoted* 노드 재시작 시(로컬 recovery가 100k INSERT를 abort하는 동안 applylogdb가 신임 master의 쓰기를 적용) 발생. "승격 노드가 open transaction을 상대로 할당해야 한다"는 인라인 주석도 같은 이유로 수정 권장.
4. **cosmetic**: 두 스크립트의 `insert_sessions` 시그니처가 다름(`<table> <payload> <offset>` vs `<table> <host> <offset>`) — 복붙 함정. 조기 종료 경로의 `rm -f open_tran.pipe` 중복. `sleep 10`은 매직 대기지만 open tran이 단언 대상이 아니므로 허용 가능.

## 배운 점 / 재사용 가치

- HA 테스트에서 **PK 없는 테이블의 DML은 applylogdb가 조용히 건너뜀** — slave에 테이블은 생기지만 비어 있어 복제 실패처럼 보임.
- **`run_on_slave -c "csql ... -c \"...\""`로 다중 문장 SQL을 넘기면 빈 결과** — slave 조회는 `csql -udba $dbname@$slaveHostName` 직접 사용.
- **bestspace_shard_count를 낮추면 debug 빌드에서 CBRD-27147 발현** — 기본값 유지.
- csql이 stdin EOF에서 버퍼를 실행해버리는 문제는 **fifo write end를 fd로 잡아두는 방식**으로 회피 가능.
- `wait_for_slave`(master→slave 배리어) / `wait_for_slave_failover`(failback 후 역방향 배리어) 사용 구분.
