https://jira.cubrid.org/browse/CBRD-27539

## Purpose

- AI 코딩 도구가 참고하는 루트 `AGENTS.md`와 `src/AGENTS.md`의 오래된 정보, 중복 규칙, 과도하거나 위험한 지침을 실제 코드와 CI 설정에 맞게 바로잡습니다.
- AS-IS: 두 문서에 잘못된 C++ 예외·RAII 전면 금지, 부정확한 `free_and_init` 단일 안내, `c_to_cpp.sh` 오해, `memory_wrapper.hpp` 예외 누락, 오래된 CI·CMake·함수명 설명이 섞여 있고 규칙이 중복 선언되어 있습니다.
- TO-BE: 루트 `AGENTS.md`는 조건부 진입점·공통 원칙·빌드/CI 진입점·보고 기준만 남기고, `src/AGENTS.md`는 빌드 모드 경계·CMake 소스 등록·메모리/예외 처리·포맷/include 검사·모듈 간 영향 확인을 중복과 오해 없이 안내합니다.

## Implementation

- `AGENTS.md`: 버전·디렉터리 수·파일 크기·컴파일러 버전·비활성 단위 테스트 목록 등 쉽게 낡는 정보를 제거하고, 작업 영역(`src/`, `unit_tests/`, `pl_engine/`, 서브모듈)별 조건부 읽기 규칙, 빌드 주의사항(`build.sh` 명시 타깃 및 `$CUBRID` 보호, `Release`/`RelWithDebInfo` `-Werror`/`-DNDEBUG` vs `debug`/`optdebug` 2단계 검증 시점), `UNIT_TESTS`의 CI 미실행, `/run` 취소 및 `cubrid-testcases-private-ex`·CTP(`pkill cub`/`kill -9`) 격리 주의, `.github/workflows/check.yml`·`gha-ci.yml` 중심 진입점으로 재구성했습니다.
- `src/AGENTS.md`: `c_to_cpp.sh`(`git mv`)와 디렉터리 단위 `PROPERTIES LANGUAGE CXX`(및 `cm_broker_jni.c`/`gencat.c` C 예외)를 구분하고, `SERVER_MODE`/`SA_MODE`/`CS_MODE` 경계 및 예외(`src/optimizer/histogram/`, `cs/CMakeLists.txt` 클라이언트 부분집합)를 명시했습니다.
- `src/AGENTS.md`: 할당자 짝짓기(`db_private_alloc` 호출 인자 `thread_p` 소유권·`PEEK` 비소유 계약 포함), C 오류 코드 경계·워커→요청 스레드 에러 전달·호출부 STL 예외 변환(`er_set`)·RAII 허용 범위, 실제 오류 코드 절차(`error_code.h` + `msg/*/cubrid.msg` `$set 5 MSGCAT_SET_ERROR`; 낡은 `dbi_compat.h` 제외 및 `cubrid-cci` 서브모듈 별도 PR 분리), GNU `indent` 2.2.11 주의와 `/* *INDENT-OFF* */`·`memory_wrapper.hpp` 규칙, 전체 `CMakeLists.txt` 등록, XASL 4단계 및 클론/디스크 스트림, `LOG_RCVINDEX`+`RV_LAST_LOGID`+`RV_fun[]`+`RCV_IS_*`, `disk_compatibility_level` 비변경(릴리스 단위 관리), `release` 측정 및 `STATIC_INLINE` `ALWAYS_INLINE`(`NDEBUG` 전용·`nm -C`) 지침을 정리했습니다.
- `src/base/AGENTS.md`: `src/AGENTS.md`로 이동한 코딩 스타일·오류 코드 절차를 가리키도록 3곳(5·41·169행)의 링크와 표현을 갱신했습니다.

## Remarks

- 엔진 소스 코드, CMake 설정, SQL 동작은 수정하지 않았습니다(`AGENTS.md`, `src/AGENTS.md`, `src/base/AGENTS.md`만 갱신).
- Greptile P2(`AGENTS.md` 단위 테스트 `ctest` 누락 타깃 지적)는 후속 이슈 [CBRD-28388](https://jira.cubrid.org/browse/CBRD-28388)에서 대응합니다.

### Test Plan

- `git diff --check`: 공백/개행 오류 없음.
- 링크·앵커·경로 정적 검증: 저장소 내 전체 `AGENTS.md` 23개 파일의 상대 링크, 앵커, 본문 인용 경로 존재 여부 통과.
- 시나리오 워크스루(소스 추가, throwing STL 사용, XASL/PRED_EXPR 변경), PR `#8751` 리뷰 피드백 9건, 3자 교차 재검토(`ai-agent` + `ay` + 주관 리뷰) P0/P1/P2 보정까지 모두 검증·반영 완료.
- 상세 근거와 줄 단위 감사 기록: [audit-report.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27539/audit-report.md)
