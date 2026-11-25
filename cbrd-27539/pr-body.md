https://jira.cubrid.org/browse/CBRD-27539

## Purpose

- AI 코딩 도구가 참고하는 루트 `AGENTS.md`와 `src/AGENTS.md`의 오래된 정보, 중복 규칙, 과도한 금지를 실제 코드와 CI 설정에 맞게 바로잡습니다.
- AS-IS: 두 문서에 잘못된 C++ 예외·RAII 전면 금지, 부정확한 `free_and_init` 단일 안내, `c_to_cpp.sh` 오해, `memory_wrapper.hpp` 예외 누락, 오래된 CI·CMake·함수명 설명이 섞여 있고 규칙이 중복 선언되어 있습니다.
- TO-BE: 루트 `AGENTS.md`는 조건부 진입점·공통 원칙·빌드/CI 진입점·보고 기준만 남기고, `src/AGENTS.md`는 빌드 모드 경계·CMake 소스 등록·메모리/예외 처리·포맷/include 검사·모듈 간 영향 확인을 중복 없이 안내합니다.

## Implementation

- `AGENTS.md`: 버전·디렉터리 수·파일 크기·컴파일러 버전·비활성 단위 테스트 목록 등 쉽게 낡는 정보를 제거하고, 작업 영역(`src/`, `unit_tests/`, `pl_engine/`, 서브모듈)별 조건부 읽기 규칙, 빌드 모드 차이(`release` `-Werror`/`-DNDEBUG` vs `debug`/`optdebug`), `UNIT_TESTS`의 CI 미실행, CTP 정리(`pkill cub`/`kill -9`) 주의, `.github/workflows/check.yml`·`.github/workflows/gha-ci.yml` 중심 검증 진입점으로 재구성했습니다.
- `src/AGENTS.md`: `c_to_cpp.sh`의 실제 역할(`git mv`)과 타깃별 `PROPERTIES LANGUAGE CXX` 컴파일 설정을 구분하고, `SERVER_MODE`/`SA_MODE`/`CS_MODE` 경계 및 예외(`src/optimizer/histogram/`, `cs/CMakeLists.txt` 클라이언트 부분집합)를 명시했습니다.
- `src/AGENTS.md`: 할당자 짝짓기(`db_private_free_and_init` 스레드 힙 소유권·`PEEK` 비소유 계약 포함), C 오류 코드 경계와 스레드 간 에러 전달(`move_top_error_message_to_this ()`)·호출부 STL 예외 변환(`er_set`)·RAII 허용 범위, `/* *INDENT-OFF* */` 보호, `memory_wrapper.hpp` 예외, 전체 `CMakeLists.txt` 등록 대상, XASL 4단계 및 캐시/디스크 스트림·`LOG_RCVINDEX`/`disk_compatibility_level`·성능 민감 경로(`ALWAYS_INLINE`, `m_px_stats`) 지침을 정리했습니다.
- `src/base/AGENTS.md`: 본 PR에서 `src/AGENTS.md`로 이동한 코딩 스타일·오류 코드 절차를 가리키도록 3곳(5·41·169행)의 참조 링크를 갱신했습니다.

## Remarks

- 엔진 소스 코드, CMake 설정, SQL 동작은 수정하지 않았습니다(`AGENTS.md`, `src/AGENTS.md`, `src/base/AGENTS.md`만 갱신).
- Greptile P2(`AGENTS.md` 단위 테스트 `ctest` 누락 타깃 지적)는 후속 이슈 [CBRD-28388](https://jira.cubrid.org/browse/CBRD-28388)에서 대응합니다.

### Test Plan

- `git diff --check`: 공백/개행 오류 없음.
- 링크·앵커·경로 정적 검증: 저장소 내 전체 `AGENTS.md` 23개 파일의 상대 링크, 앵커, 본문 인용 경로 존재 여부 통과.
- 시나리오 워크스루(소스 추가, throwing STL 사용, XASL/PRED_EXPR 변경), 독립 리뷰 패스, PR `#8751` 리뷰 피드백 9건 검증 반영 완료.
- 상세 근거와 줄 단위 감사 기록: [audit-report.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27539/audit-report.md)
