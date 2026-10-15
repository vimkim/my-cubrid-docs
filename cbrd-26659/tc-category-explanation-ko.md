# OOS TC 카테고리: 5분 설명

작성: 2026-10-15 (Asia/Seoul). CBRD-26659 / [조정 PR #8128](https://github.com/CUBRID/cubrid/pull/8128). 분류 기준: docs `927be36973e73a98d868f6a6bb4d4fd11e0f9352` 의 [coverage](ci-replan/coverage.md).

OOS TC는 큰 값을 행 밖에 저장할 때 **값의 정확성, 저장 형태, 수명과 복구**를 함께 확인한다. 팀원이 검증 목적과 남은 공백을 빠르게 파악하도록 기존 31개 동작 항목을 7개 기능으로 묶었다. 한 TC가 여러 항목을 다룰 수 있다.

**읽는 순서: 동작 → 관찰 → 판정.** 공개 SQL은 전체 값·행 집합·오류·스키마를 정답과 비교한다. 별도 shell은 자기 fixture의 SHOW·diagdb·로그로 OOS 파일·청크·소유 관계를 관찰한다. 두 실행은 인터페이스와 설정이 달라 shell 관찰을 실제 공개 SQL 실행의 물리 배치 증거로 합칠 수 없다. Unit은 내부 동작·기대값의 설계 근거이며, 이번 SQL/shell 실행 통과를 대신하지 않는다.

| 카테고리·목적 | 대응 항목 | 대표 TC와 기록된 증거 | 검증 한계·남은 상태 |
| --- | --- | --- | --- |
| **저장 표현·경계** — 큰 값, NULL/빈 값, 여러 속성, 청크와 [LOB locator](ci-replan/delivery/09-lob-locators.md) | [R02–R05, R07–R08](ci-replan/coverage.md#coverage-table) | [representation_chunks](ci-replan/delivery/03-representation-chunks.md): SQL은 복사 후 전체 값, shell은 1~4청크와 정확한 바이트 합을 확인. LOB는 외부 본문과 locator를 구분 | 4060/4064 목표 경계는 결함 재현. 실제 이진 VOT 폭·넓은 압축 조합은 미검증 |
| **값·조회·쓰기 원자성** — 복사, UPDATE/DELETE, 트랜잭션, 제약·트리거·읽기 경로 | [R01, R09–R13, R30](ci-replan/coverage.md#coverage-table) | [sql05_transactions](ci-replan/delivery/05-transactions-errors.md): ROLLBACK·SAVEPOINT·COMMIT 후 정확한 행과 값 확인 | 즉시 원자성의 부분 검증. 내부 손상·fault 주입·재시도·누수는 미검증 |
| **스키마·정책·소유 파일** — DDL, 파티션, 진단, DROP | [R06, R14–R16, R24](ci-replan/coverage.md#coverage-table) | [schema_policy](ci-replan/delivery/08-schema-storage.md): 정책과 명시적 쓰기 후 배치. [owner_drop](ci-replan/delivery/02-shell-owner-drop.md): 소유 파일 제거와 복사본 생존 | 파티션 목적지 소유권 결함 유지. 비 DBA 권한·진단 중 경합은 미검증 |
| **수명·공간 회수** — 옛 스냅샷과 vacuum 안전성 | [R19–R23](ci-replan/coverage.md#coverage-table) | [snapshot_visibility](ci-replan/delivery/11-snapshots-reclaim.md): 옛 값/새 값과 청크 6→9→4 관찰 | 사용자 페이지는 9→9로 반환 실패. rollback 후 vacuum 실패, 체인 재사용 구현 공백, 동일 슬롯 재시도 미검증 |
| **장애 복구** — 커밋 내구성과 미커밋 undo | [R17–R18](ci-replan/coverage.md#coverage-table) | [crash_committed / crash_undo](ci-replan/delivery/10-crash-recovery.md): 실제 SIGKILL 뒤 확정된 커밋/미커밋 상태와 INSERT REDO/UNDO 확인 | HA off·vacuum disabled 구성의 부분 검증. OOS DELETE replay·일반 수명 안전성은 미검증 |
| **운영 도구·암호화** — unload/load, compact, 백업·복원, TDE | [R25–R27](ci-replan/coverage.md#coverage-table) | [utility_cs / backup_restore](ci-replan/delivery/12-utility-roundtrips.md): 값·스키마·물리 소유자. [tde_wal](ci-replan/delivery/13-tde-wal.md): lazy AES 파일·WAL 플래그·정상 재시작 | SA 목적지 배치·기존 파일 AES 적용·디스크 암호문은 미검증. 백업 실험의 외부 LOB 본문은 별도 보존 |
| **분산·이력·후속 범위** — 두 노드 복제, CDC/flashback, 제안 기능 | [R28–R29, R31](ci-replan/coverage.md#coverage-table) | [인벤토리의 범위 구분](ci-replan/issue-inventory.md): 두 노드 값·큐 정합성은 후속 검증 공백, 이력·제안 기능은 유예 범위로 기록 | 이번 선택의 통과 근거 없음. 유예된 CDC의 기존 실패는 실행·기대값을 유지 |

**상태의 의미.** [부분 검증](ci-replan/GLOSSARY.md)은 보고서가 실행·assertion·정리를 확인한 범위다. **결함 대기**는 올바른 성공 기대를 유지한 재현 실패다. **구현 공백**(R21)과 **관찰 수단 공백**(R22·R30, R27 일부)은 구분한다. **유예·제안**(R29·R31)은 이번 구현 범위 밖이다. 인벤토리의 행 수는 통과 건수가 아니다.

**근거 시점.** 대표 사례는 2026-10-08 Engine `fb567a629cdb390fff920542173fa36f454c74a0` 의 delivery 기록이며, [10월 12일 shell 변환·재검증](ci-replan/shell-conversion-results-20261012.md#qualification-and-evidence)은 같은 소스 트리의 Engine `a5da823b2a84e95b4b22d48abe4a3f9fd601c176` 에서 선택 shell 14/14와 별도 실패 후보를 기록한다. 이후 [10월 13일 SQL 수리](ci-repair/repair-results.md)의 Engine `1ef86a7efa34002e971b1b30bcf5d451e9db441b` 에서는 full partition을 포함한 원래 SQL 72개가 통과했다. 파티션 물리 소유권 결함은 별개이며, 해당 CI 전체는 shell 7개 실패로 FAILURE다. 리비전·실행별 판정은 [수리 추적표](ci-repair/README.md)에 둔다. 이 문서는 새 DB·CI 실행 없이 기존 기록을 요약했다.

**5분 발표 흐름.** 목적과 SQL/shell 구분에 1분, 표의 7개 기능과 대표 사례에 3분, 잔여 상태에 1분을 쓴다. 마무리할 핵심은 “값이 맞는지, 실제 어디에 저장됐는지, 언제까지 안전한지를 따로 확인한다. 통과한 부분과 결함·관찰 공백·유예 범위를 함께 설명한다”이다.
