https://jira.cubrid.org/browse/CBRD-27539

## Purpose

- AI 코딩 도구가 참고하는 루트 `AGENTS.md`와 `src/AGENTS.md`의 오래된 정보, 중복 규칙, 과도한 금지를 실제 코드와 CI 설정에 맞게 바로잡습니다.
- AS-IS: 두 문서에 잘못된 C++ 예외·RAII 전면 금지, 부정확한 `free_and_init` 단일 안내, `c_to_cpp.sh` 오해, `memory_wrapper.hpp` 예외 누락, 오래된 CI·CMake·함수명 설명이 섞여 있고 규칙이 중복 선언되어 있습니다.
- TO-BE: 루트 `AGENTS.md`는 조건부 진입점·공통 원칙·빌드/CI 진입점·보고 기준만 남기고, `src/AGENTS.md`는 빌드 모드 경계·CMake 소스 등록·메모리/예외 처리·포맷/include 검사·모듈 간 영향 확인을 중복 없이 안내합니다.

## Implementation

- `AGENTS.md`: 버전·디렉터리 수·파일 크기·컴파일러 버전·비활성 단위 테스트 목록 등 쉽게 낡는 정보를 제거하고, 작업 영역(`src/`, `unit_tests/`, `pl_engine/`, 서브모듈)별 조건부 읽기 규칙과 `.github/workflows/check.yml`, `.github/workflows/gha-ci.yml` 중심의 검증 진입점으로 재구성했습니다.
- `src/AGENTS.md`: `c_to_cpp.sh`의 실제 역할(`git mv`)과 타깃별 `PROPERTIES LANGUAGE CXX` 컴파일 설정을 구분하고, `SERVER_MODE`/`SA_MODE`/`CS_MODE` 경계 및 예외(`src/optimizer/histogram/`, `cs/CMakeLists.txt`의 클라이언트 부분집합)를 명시했습니다.
- `src/AGENTS.md`: `db_private_free_and_init`·`free_and_init`·`os_free_and_init`·`parser_alloc`의 할당자 짝짓기, C 오류 코드 경계와 호출부 STL 예외 변환(`er_set`) 및 RAII 허용 범위, `/* *INDENT-OFF* */` 보호, `memory_wrapper.hpp` 뒤 `strict_warnings_on.hpp`/`strict_warnings_off.hpp` 허용 예외, 전체 `CMakeLists.txt` 등록 대상, XASL 4단계 및 storage/transaction 영향 확인 경로를 정리했습니다.

## Remarks

- 엔진 소스 코드, SQL 동작, CMake 설정, 하위 디렉터리 `AGENTS.md`(21개)는 수정하지 않았습니다.

### Test Plan

- `git diff --check`: 공백/개행 오류 없음.
- 링크·앵커·경로 정적 검증: 저장소 내 전체 `AGENTS.md` 23개 파일의 상대 링크, 앵커, 본문 인용 경로 존재 여부 통과.
- 시나리오 워크스루(소스 추가, throwing STL 사용, XASL/PRED_EXPR 변경) 및 독립 리뷰 패스로 사실 정확도와 누락 경로 교정 완료.
- 상세 근거와 줄 단위 감사 기록: [audit-report.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27539/audit-report.md)
