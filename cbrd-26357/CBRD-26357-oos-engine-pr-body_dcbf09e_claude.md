https://jira.cubrid.org/browse/CBRD-26357

## Purpose

- 큰 가변 길이 값을 행 밖의 테이블별 파일에 저장하는 OOS(Out-of-row Overflow Storage)를 develop에 넣습니다. PostgreSQL TOAST와 비슷한 방식입니다.
- AS-IS: 큰 `VARCHAR`, `BIT VARYING`, LOB locator 값이 행 안에 들어가서 한 페이지에 들어가는 행이 적고, 작은 컬럼만 읽어도 큰 값이 있는 페이지를 읽습니다. 페이지보다 큰 행은 여러 페이지에 걸친 overflow 레코드가 됩니다.
- TO-BE: 행이 페이지의 1/4(16KB 페이지에서 약 4KB)을 넘으면 큰 값부터 하나씩 OOS 파일로 옮기고, 행에는 24바이트 stub(위치·길이·식별 정보)만 남깁니다. 값이 필요한 컬럼만 그때 읽습니다.

## Implementation

- **저장 형식:** 새 파일 종류 `FILE_OOS`(힙마다 최대 1개, 필요할 때 생성)와 `PAGE_OOS`를 추가합니다. 큰 값은 chunk 체인으로 나눠 저장하고, 각 chunk의 식별 stamp로 잘못된 참조를 걸러냅니다(`src/storage/oos_file.cpp`).
- **힙 연동:** 어떤 값을 옮길지 정하고(`heap_attrinfo_determine_disk_layout`), 필요한 컬럼만 읽습니다(Resolve). 행 바이트 전체가 필요한 경우에만 모든 값을 펼칩니다(Expand). 이를 위해 힙 조회 함수에 `HEAP_RECDES_CONSUMPTION_POLICY` 인자를 추가했습니다.
- **DML:** INSERT는 저장할 힙이 정해진 뒤에 OOS 값을 씁니다. UPDATE는 OOS 값을 새로 쓰고, DELETE는 MVCC 독자를 위해 값을 남깁니다. 오래된 값은 vacuum이 지우고, 비게 된 OOS 페이지는 파일 관리자에게 돌려줍니다.
- **복구·복제:** 새 로그 종류(`RVOOS_INSERT`, `RVOOS_DELETE` 등)를 추가하고, HA replica는 자기 OOS 파일에 값을 다시 쓴 뒤 stub을 고칩니다. TDE 테이블의 OOS 파일도 같은 방식으로 암호화합니다.
- **SQL·도구:** 컬럼 옵션 `STORAGE PREFER_INLINE | FORCE_OUTLINE | DEFAULT`, `SHOW HEAP OOS OF <table>`, 오류 코드 -1387~-1391을 추가합니다. unloaddb는 OOS 값을 펼쳐서 내보냅니다.
- **테스트:** `unit_tests/oos/`에 CTest 44개 항목(GoogleTest 약 386개 케이스)을 추가합니다. `UNIT_TEST_OOS` 옵션으로 빌드합니다.

## Remarks

- **검증:** `5a70787` 기준 [gha-ci run 40349442612](https://github.com/CUBRID/cubrid/actions/runs/40349442612)에서 build, `test_sql`(실패 0), `test_medium`(975/975), `test_shell`(3,460 PASS / 0 FAIL / 30 SKIP)이 통과했습니다. 이후 커밋 5개 중 엔진을 바꾼 것은 아래 저장 형식 검사(`1e8701b`, `d8ed97f`)이고, 나머지는 OOS 테스트 스크립트와 CTest 설정만 바꿨습니다. OOS CTest는 `dcbf09e`에서 로컬로 42/42 통과했습니다(저장 형식 검사 테스트 포함, real vacuum, workspace 2개 대상 제외). develop 빌드로 만든 DB를 csql·checkdb·upgradedb·서버 시작이 모두 거부하고, deletedb는 지우는 것도 확인했습니다.
- **호환성:** 디스크 호환성 버전은 11.5 그대로지만 저장 형식이 바뀌어, develop을 포함한 이전 엔진으로 만든 DB는 다시 만들어야 합니다. 이제 DB를 만들 때 첫 볼륨 헤더에 저장 형식 번호를 기록하고, 시작할 때 번호가 다른 DB는 다른 페이지를 읽기 전에 새 오류 -1392(`ER_BO_INCOMPATIBLE_STORAGE_FORMAT`)로 거부합니다. 거부된 DB도 deletedb로 지울 수 있습니다. 한계: 이전 빌드가 새 DB를 여는 것은 막지 못합니다. 이전 형식의 백업은 restoredb가 파일을 복원한 뒤 시작할 때 거부됩니다. client와 server는 같은 빌드여야 합니다.
- **범위 밖(CDC):** CDC·flashback의 OOS 이력(CBRD-26939)은 이번 머지에서 미뤘습니다. 그래서 OOS 엔진에서 실패하는 CDC shell 테스트 `cbrd_27064`, `cbrd_27075`는 QA팀과 협의해 [#4210](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4210)에서 `_25_unstable`로 옮겼습니다. develop CI(gha-ci)에서는 실행하지 않고, QA 회귀 테스트에서는 계속 실행합니다. OOS + CDC 지원은 CBRD-26939에서 따로 구현합니다.
- **Greptile P1:** 테스트 스크립트가 기존 DB를 지우는 문제는 고쳤습니다(테스트가 만든 DB만 지움). develop DB 호환성은 위 정책대로 형식을 유지합니다. develop도 11.5 개발 중에 같은 힙 헤더(`e84a7f6dc`)와 B-tree overflow 헤더(`10a1df3e6`)를 버전 변경 없이 바꿨습니다.
- **미해결:** 삭제 rollback과 슬롯 재사용 충돌(Greptile P1)은 확인된 결함으로, CBRD-27781로 분리했습니다. 오류로 중단된 vacuum의 OOS 삭제가 rollback될 때, 그 사이 다른 트랜잭션이 비워진 슬롯에 값을 넣었으면 생깁니다. CBRD-27237(rollback된 UPDATE의 체인을 vacuum이 지울 수 있음), CBRD-27230(UPDATE 체인 재사용), CBRD-27057(demotion 기준 4,060B)은 구현되지 않았습니다.
- **머지 순서:** testcase PR [#3551](https://github.com/CUBRID/cubrid-testcases/pull/3551)·[#4210](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4210)을 먼저 머지하고 `Check TC PRs`를 다시 실행한 뒤 머지합니다.
- **리뷰 대응:** 2026-10-27 리뷰의 항목별 처리 현황은 [대응 현황 댓글](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6435674702)에 정리했습니다.
- 리뷰 순서, 파일별 설명, 미해결 사항의 근거: [CBRD-26357-oos-engine_5a70787_claude.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-oos-engine_5a70787_claude.md)
