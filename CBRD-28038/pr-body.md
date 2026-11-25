https://jira.cubrid.org/browse/CBRD-28038

## Why

개발자와 에이전트가 storage 코드를 수정할 때 실제 구현에 맞는 문서로 진입점과 안전 조건을 찾게 한다.
기존 문서는 잘못된 정렬 파일과 없는 함수를 안내하고, latch·버퍼 수명·복구의 중요한 조건을 빠뜨린다.

## What changed

- `AGENTS.md`의 중복 fix 예제를 모으고 실제 모듈·CMake·예외 처리 지침을 바로잡는다.
- 분석서 7개에서 B-tree 정렬·삭제, NDV 수집, 조건부 API와 파일 소유권 안내를 수정한다.
- ordered fix 이후 재검증, `RECDES` 소유권, 파일 수명, undo 공간, DWB·TDE와 LOB 정리 조건을 보강한다.

## Scope

- storage 지침과 기존 분석서 8개를 수정한다.
- 런타임 코드, 빌드 설정, 디스크 형식과 테스트 기대값은 변경하지 않는다.

## Blast Radius

개발자가 코드를 탐색하고 변경할 때 읽는 문서에 영향을 준다. 제품 실행 동작에는 변경이 없다.

## Verification

- 소스·헤더·CMake와 대조했다. 독립 검토와 최신 `develop` 대조를 거쳐 파일 소유권과 bulk destroy 조건을 보정했다.
- 파일·절 링크 42개와 함수명 참조 313개를 정적으로 확인했다. 함수명 검사는 정의나 동작의 증명이 아니다.
- `git diff --check`와 문서 해시 확인을 통과했다. 로컬 빌드·SQL 테스트는 실행하지 않았다.

TC 변경은 필요하지 않다. 자동 생성되는 TC PR은 관리자가 닫아야 TC Merge Gate를 해제할 수 있다.
