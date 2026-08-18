# T2 — 변동 버전 의존성 경계 잠금

- label: `wayfinder:grilling`
- status: open
- assignee: (none)
- blocked-by: (none)
- map: [CBRD-27124 CMake build version refresh](../map.md)

## Question

revision 값이 바뀔 때 광범위한 `config.h` 소비자가 다시 컴파일되지 않도록 변동 버전 정보의 경계를 어디에 둘 것인가?

최소한 다음 내용을 결정한다.

- `EXTRA_VERSION`, `BUILD_NUMBER`, `VERSION_STRING` 중 무엇을 정적 설정과 분리할지
- 별도 generated header, generated source, target property 또는 다른 표현 중 선택
- generated artifact를 만드는 target과 이를 소비하는 target의 dependency 방향
- `release_string.c`/`release_string.h`와 broker 직접 소비자 7곳의 include 및 API 경계
- `SERVER_MODE`, `SA_MODE`, `CS_MODE`에서 동일한 값과 ABI를 유지하는 방법
- public/generated header 여부, header guard, include order와 C/C++17 호환성
- Windows `version.rc`와 packaging consumer가 같은 값을 안전하게 사용하는 방법
- 나머지 정적 제품 버전 값이 기존 `version.h`에 남아야 하는 범위

완료 조건은 파일 또는 인터페이스 단위의 ownership, 직접 consumer 목록, compile dependency 방향, 플랫폼별 예외가 확정되는 것이다. 구현은 하지 않는다.
