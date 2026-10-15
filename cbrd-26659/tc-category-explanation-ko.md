# OOS TC를 추가한 이유: 5분 설명

작성·갱신: 2026-10-15 (Asia/Seoul). CBRD-26659 / [조정 PR #8128](https://github.com/CUBRID/cubrid/pull/8128).

OOS는 큰 속성 값을 행 밖에 저장합니다. 따라서 복사·수정·취소·복구가 별도 저장 공간을 올바르게 다루는지 확인해야 합니다.

[HTML 설명서 열기](tc-category-guide-ko.html). 각 카테고리의 첫 문단은 테스트가 필요한 이유를 설명합니다. 항목을 펼치면 테스트 흐름·성공 조건·기록된 결과를 볼 수 있습니다. 검색창에서 TC 이름이나 R20 같은 항목 번호를 찾을 수 있습니다.

## 카테고리별로 막으려는 문제

1. **[큰 값을 나누고 다시 읽기](tc-category-guide-ko.html#storage)** — R02–R05, R07–R08.
   값이 청크 경계에 걸리거나 NULL·빈 값이 섞여도 모든 바이트를 보존해야 합니다.
   LOB는 파일 위치 정보와 외부 본문을 따로 확인합니다.
2. **[일반 SQL의 결과 지키기](tc-category-guide-ko.html#sql)** — R01, R09–R13, R30.
   원본을 삭제해도 복사본은 읽혀야 합니다.
   수정·취소·오류·트리거·조회 뒤에도 정확한 값과 행 상태를 유지해야 합니다.
3. **[표 구조와 소유자 지키기](tc-category-guide-ko.html#ownership)** — R06, R14–R16, R24.
   정책·열 구조·파티션이 바뀌어도 값과 OOS 파일의 소유 관계가 맞아야 합니다.
   원본 DROP은 복사본의 파일을 지우면 안 됩니다.
4. **[옛 값을 보관하고 안전해진 뒤 지우기](tc-category-guide-ko.html#lifetime)** — R19–R23.
   다른 사용자가 수정해도 옛 스냅샷은 필요한 값을 계속 읽어야 합니다.
   청크 삭제, 빈 페이지 반환, ROLLBACK 뒤 vacuum은 각각 확인합니다.
5. **[서버 종료 뒤 복구하기](tc-category-guide-ko.html#recovery)** — R17–R18.
   완료 응답을 받은 COMMIT은 서버 강제 종료 뒤에도 남아야 합니다.
   COMMIT하지 않은 변경은 이전 상태로 돌아와야 합니다.
6. **[관리 도구와 암호화 확인하기](tc-category-guide-ko.html#operations)** — R25–R27.
   백업·복원·unload/load·compact 뒤에도 전체 값을 읽어야 합니다.
   별도 OOS 파일과 복구 로그의 암호화도 확인해야 합니다.
7. **[후속 범위 구분하기](tc-category-guide-ko.html#scope)** — R28–R29, R31.
   두 노드 복제는 후속 확인이 필요합니다.
   CDC·flashback 이력과 미채택 제안은 이번 통과 범위와 구분합니다.

## 결과를 읽는 방법

SQL은 전체 값·오류·스키마를 정답과 비교합니다. 별도 shell은 자기 테스트용 DB의 파일·청크·소유 관계를 확인합니다. 두 실행은 서로 다릅니다. shell 결과로 실제 공개 SQL 실행의 물리 배치를 확인했다고 말하지 않습니다.

31개는 검증 항목의 수입니다. TC 파일 수나 통과 건수가 아닙니다. 기존 unit의 존재도 이번 SQL/shell 실행의 통과 기록을 대신하지 않습니다.

부분 확인, 결함 기록, 구현 필요, 확인 수단 필요, 유예 범위를 구분합니다. 예를 들어 [R23](tc-category-guide-ko.html#R23)은 청크 감소를 확인했지만 빈 페이지 반환은 실패했습니다. [R21](tc-category-guide-ko.html#R21)은 채택된 설계의 구현이 남았습니다.

## 근거의 시점

이 설명은 [기존 31개 항목](ci-replan/coverage.md)과 [glossary](ci-replan/GLOSSARY.md)를 바탕으로 작성했습니다. [HTML의 근거 목록](tc-category-guide-ko.html#evidence)에서 소스·TC 리비전과 보고서를 확인할 수 있습니다.

대표 사례는 10월 8일 delivery 기록입니다. [10월 12일 shell 재검증](ci-replan/shell-conversion-results-20261012.md)은 선택 shell 14개 통과와 별도 실패 후보를 기록합니다. [10월 13일 SQL 수리](ci-repair/repair-results.md) 뒤에는 full partition을 포함한 원래 SQL 72개가 통과했습니다.

파티션의 물리 소유권 결함은 별개로 남았습니다. 해당 CI 전체도 shell 7개 실패로 FAILURE였습니다. [수리 추적표](ci-repair/README.md)가 실행별 결과와 한계를 기록합니다. 이 문서 작성 중 새 DB·CI 실행은 하지 않았습니다.

발표에서는 각 카테고리의 이유를 먼저 말합니다. 대표 사례 하나로 테스트 흐름을 설명합니다. 마지막에 확인한 부분과 남은 공백을 구분합니다.
