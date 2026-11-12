https://jira.cubrid.org/browse/CBRD-28053

## Purpose

- OOS(CBRD-26357)를 대체할 수 있는 대안 설계 Sidecar의 POC다. 병합용이 아니라, 설계를 코드와 측정으로 검토받기 위한 draft PR이다.
- AS-IS: OOS는 큰 값마다 별도 주소와 별도 생명주기 프로토콜을 두었고, 그 프로토콜에서 슬롯 재사용·undo·vacuum 결함이 반복해서 나왔다.
- TO-BE: 큰 값은 테이블별 store heap의 일반 MVCC 레코드로 옮기고, 생성·삭제·undo·redo·vacuum은 기존 heap 코드가 그대로 처리한다.

## Implementation

- `src/storage/sidecar.cpp`: 쓰기 계획(store insert, DELID stamp, KEEP)과 적용, fetch 출구의 값 복원, 한 페이지 store cursor, 검증기 `sidecar_verify_class`.
- `src/base/sidecar_format.c`: hot record의 16바이트 ref와 trailer codec. 단위 테스트는 `unit_tests/sidecar/`.
- `src/storage/heap_file.c`: `heap_insert_logical`, `heap_update_logical`, `heap_delete_logical`의 쓰기 hook과 fetch 출구 hook, 새 recovery index `RVHF_SIDECAR_LINK`.
- `locator_sr.c`, `scan_manager.c`, `expr_batch.c`, `page_buffer.c`: lock fallback, scan의 지연 읽기, store cursor 해제 지점.
- 시스템 파라미터, 성능 카운터, `SHOW HEAP SIDECAR OF t`, 단방향 디스크 호환 레벨.
- 처음 세 커밋은 `develop` 결함 수정(CBRD-27937, CBRD-27935, CBRD-27936)이다. Sidecar가 heap의 슬롯 보호를 물려받으므로 전제 조건이다.
- 검증 중 찾은 `develop` 결함의 로컬 수정 세 개도 들어 있다. 온라인 인덱스 생성의 overflow key 누수(CBRD-27635, `6d39a9a7f5`), 커밋 레코드가 디스크에 쓰이기 전에 커밋 응답이 나가는 경우(`d514d5ea18`), committed snapshot 버전 탐색이 커밋되지 않은 중간 버전을 반환하는 경우(`7c5028d5bd`). 뒤의 둘은 JIRA 등록을 진행 중이다.
- 마지막 커밋은 CI 전용이다. `sidecar_force_external` 기본값을 yes로 바꿔 회귀 테스트의 모든 대상 값이 store를 거치게 한다. 병합 대상이 아니다.

## Remarks

- 기능 미사용 비용(A1): instructions 최대 +0.69%, wall은 모든 경우 중앙값 기준 5% 이내.
- 작은 컬럼만 읽는 scan(A2): `develop` 대비 page fetch 10.9배/47.4배/426배 감소(1 KB/4 KB/16 KB 값).
- recovery(A3): `kill -9` 140회에서 값 손실·고아 레코드·끊긴 참조 0건. MVCC·vacuum(A4) 시나리오 통과. 코드 수준 TLA+ 모델(A7) 통과.
- 회귀(A6, 로컬): `test_sql` 1,740개 off/on에서 1개 차이(레이아웃 효과). `test_medium`은 Sidecar 고유 실패 없음. `test_shell`은 일부만 돌렸다. 이 PR의 CI가 전체를 돌린다.
- 아직 없는 것: HA 복제(HA가 켜지면 값을 밖으로 옮기지 않는다), CDC·flashback, `STORAGE` DDL 절. 24시간 stress는 진행 중이다.
- 설계 문서: https://github.com/vimkim/my-cubrid-docs/tree/main/sidecar
