# [CBRD-27539] 루트 `AGENTS.md` 및 `src/AGENTS.md` 전수 감사 및 재작성 보고서

- 분석 및 작성 일시: 2026-11-25 (`Asia/Seoul`)
- 관련 이슈: [CBRD-27539](https://jira.cubrid.org/browse/CBRD-27539) (상위 EPIC: [CBRD-27537](https://jira.cubrid.org/browse/CBRD-27537))
- 기준 저장소 및 커밋: `CUBRID/CUBRID` `origin/develop` `cbed1d5707`
- 재작성 로컬 커밋: `e4da2c73ea03d079973526171a2129b2dc97cc21` (브랜치 `CBRD-27539`, 미푸시)
- 변경 범위: `AGENTS.md` (216줄 → 32줄), `src/AGENTS.md` (46줄 → 76줄). 엔진 소스, CMake 설정, SQL 동작, 하위 21개 `AGENTS.md` 파일은 변경하지 않았습니다.

## Purpose

- 목적: 기존 `AGENTS.md`와 `src/AGENTS.md`의 모든 지침을 현재 코드·CMake·CI 워크플로우와 줄 단위로 대조해 유지·수정·삭제 판단 근거를 남기고, 두 문서의 역할 분담과 검증 결과를 기록합니다.
- AS-IS: `630fdc4118` (`#6861`) 이후 일부만 수정(`d93145bdba`, `#8234`)된 두 문서에 부정확한 금지 규칙(C++ 예외·RAII 전면 금지), 단일 해제 API(`free_and_init`) 안내, 잘못된 `c_to_cpp.sh` 해석, `memory_wrapper.hpp` 예외 누락, 오래된 CI·CMake·함수명·정적 수치 캐시가 남아 있고 규칙이 중복되어 있었습니다.
- TO-BE: 루트 `AGENTS.md`는 조건부 읽기 트리거·공통 원칙·빌드/CI 진입점·결과 보고 규칙에 집중하고, `src/AGENTS.md`는 빌드 모드 경계·CMake 소스 등록·메모리/예외 처리·포맷팅 및 include 검사·모듈 간 영향 확인을 단일 출처로 제공합니다.

## Implementation

### 1. JIRA 7대 핵심 점검 항목 검증 결과

| # | 점검 항목 | 기존 지침 위치 | 라이브 코드·설정 근거 (`origin/develop` `cbed1d5707`) | 반영 결과 |
| --- | --- | --- | --- | --- |
| 1 | `c_to_cpp.sh` vs 실제 C++ 컴파일 근거 | `AGENTS.md:9`, `src/AGENTS.md:3` | `c_to_cpp.sh:1-12`는 `git mv "${fullpath}" "${base}.cpp"`로 확장자만 바꿉니다. 실제 `.c` 파일의 C++17 컴파일은 `CMakeLists.txt:221`(`-std=c++17`)과 각 타깃 CMake의 `set_source_files_properties(... PROPERTIES LANGUAGE CXX)`(`cubrid/CMakeLists.txt:689`, `cs/CMakeLists.txt:485,562`, `sa/CMakeLists.txt:725`, `util/CMakeLists.txt:28-294`, `broker/CMakeLists.txt:41-625`, `cm_common/CMakeLists.txt:31-96`, `timezones/CMakeLists.txt:29`, `unit_tests/*/CMakeLists.txt`)에서 결정됩니다. | `src/AGENTS.md:5`에 두 사실을 분리해 명시하고 루트 중복을 제거했습니다. |
| 2 | C++ 예외 및 RAII 처리 | `AGENTS.md:196-197`, `src/AGENTS.md:3` | 엔진 공용 API는 `src/base/error_code.h` 음수 오류 코드(`NO_ERROR = 0`)와 `er_set()`을 유지하며 C 인터페이스로 예외를 넘기지 않습니다. 반면 `src/` 내 26개 파일(`.c` 포함)은 STL 예외를 호출부나 C 인터페이스 경계에서 잡아 `er_set()` + 오류 코드로 즉시 변환합니다(`src/storage/heap_file.c:14482`, `src/optimizer/histogram/histogram_sampler_sr.cpp:1259,1396`, `src/query/string_regex_std.cpp:126`, `src/query/vacuum_oos.cpp:260`, `src/base/lockfree_hashmap.hpp:278`). `src/base/scope_exit.hpp`, `src/base/mem_block.hpp`, `std::unique_ptr`, `std::lock_guard` 등 RAII도 사용 중입니다. | 전면 금지를 삭제하고, `src/AGENTS.md:38-46`에 C 오류 코드 경계 유지 + STL 예외 포착/변환 + 모듈 관례에 따른 RAII 사용 원칙을 명시했습니다. |
| 3 | 메모리 해제 API 짝짓기 | `AGENTS.md:165,189` | `src/base/memory_alloc.h:124-165`는 `db_private_free_and_init(thrd, ptr)`, `free_and_init(ptr)`, `os_free_and_init(ptr)`를 각각 정의하며 `db_private_alloc`, `malloc`/`calloc`/`realloc`, `os_malloc`/`os_calloc`와 대응합니다. `src/parser/parser.h:127`·`src/parser/parse_tree.c:957`의 `parser_alloc`은 파서 컨텍스트 수명을 따르므로 수동 해제하지 않습니다. | `src/AGENTS.md:38-43`에 4종 할당자-해제자 짝과 수명·정리 경로 검증을 정리했습니다. |
| 4 | `memory_wrapper.hpp` include 검사 | `AGENTS.md:148,191-192` | `.github/workflows/check.yml:216-292`(`memory-monitor-check`)는 `cubrid/CMakeLists.txt`에 파일명이 포함된 `.c`/`.cpp` 파일을 검사합니다. `#include "memory_wrapper.hpp"`가 마지막 `#include`이고 직전 줄이 `// XXX: SHOULD BE THE LAST INCLUDE HEADER`여야 하나, `strict_warnings_on.hpp`·`strict_warnings_off.hpp`가 뒤에 오는 것은 허용됩니다(`.github/workflows/check.yml:252-259`, CBRD-25966). `src/heaplayers/lea_heap.c:39-40`은 위치·주석 검사가 면제되며(`.github/workflows/check.yml:251`), `src/base/memory_monitor_sr.cpp`, `src/base/memory_monitor_api.cpp`, `src/base/memory_wrapper.cpp`는 전체 검사에서 제외됩니다(`.github/workflows/check.yml:274-277`). `src/base/memory_wrapper.hpp:38-47`에 따라 헤더 파일에는 `memory_wrapper.hpp` 대신 `memory_cwrapper.h`를 사용합니다. | `src/AGENTS.md:60-64`에 검사 대상, 주석, `strict_warnings_*` 허용 예외, 면제 파일, 헤더 금지 규칙을 정확히 기술했습니다. |
| 5 | 빌드 및 CI 안내 | `AGENTS.md:95-115,179-185` | `.github/workflows/check.yml`이 PR 정적 검사(`license`, `pr-style`, `code-style`, `cppcheck`, `memory-monitor-check`)를 실행하며, `.github/workflows/gha-ci.yml`(+ `gha-ci-suite.yml`, `tc-branch-sync.yml`, `tc-merge-gate.yml`)이 `develop` push, PR `/run` 코멘트, 야간 `schedule`, `workflow_dispatch`에서 release/debug 빌드와 `shell`·`sql`·`medium`·`sql_by_cci` 회귀 스위트를 실행합니다. `Jenkinsfile`과 `.circleci/config.yml`도 보조·레거시 설정으로 저장소에 남아 있습니다. 또한 `./build.sh -h`와 `CMakePresets.json`은 `optdebug` 모드를 포함합니다. | `AGENTS.md:21-28`에 GitHub Actions 중심 진입점과 보조·레거시 파일 확인 주의사항을 배치하고, volatile 옵션 표·병렬도 수치를 삭제했습니다. |
| 6 | CMake 소스 등록 위치 | `src/AGENTS.md:33-35` | `src/` 아래에는 모듈별 `CMakeLists.txt`가 없으나, 상위 소스 목록은 3개 라이브러리(`cubrid/`, `sa/`, `cs/`)에 그치지 않습니다. `CMakeLists.txt:387-422`의 `*_DIR` 변수는 `util/CMakeLists.txt`(`cub_server`, `csql`, `cub_master` 등), `broker/CMakeLists.txt`, `cm_common/CMakeLists.txt`, `timezones/CMakeLists.txt`, `win/CMakeLists.txt`, `unit_tests/*/CMakeLists.txt`에서도 참조됩니다. | `src/AGENTS.md:22-34`에 모든 타깃 범주와 4단계 소스 등록 절차를 명시했습니다. |
| 7 | 문서 간 링크와 섹션 앵커 | `src/AGENTS.md:7`, 하위 `AGENTS.md` | 기존 `src/AGENTS.md:7`은 `[AGENTS.md](../AGENTS.md#structure)`를 참조했으나, 개편된 루트 `AGENTS.md`는 `## Structure` 절을 두지 않습니다. `src/base/AGENTS.md:5`는 `[AGENTS.md](../../AGENTS.md)`(앵커 없음), `src/storage/AGENTS.md:9`는 `[src/AGENTS.md](../AGENTS.md)`(앵커 없음)를 링크합니다. | `src/AGENTS.md:3` 링크를 `[the root AGENTS.md](../AGENTS.md)`로 수정해 깨진 `#structure` 앵커를 제거했습니다. |

---

### 2. 줄 단위 감사 기록 (Keep / Modify / Delete)

#### A. 루트 `AGENTS.md` (기존 216줄 → 재작성 32줄)

| 기존 줄 | 기존 내용 요약 | 판정 | 라이브 근거 및 판단 이유 |
| --- | --- | --- | --- |
| 1 | `# AGENTS.md — CUBRID Database Engine` | Keep | 문서 제목 유지 (`AGENTS.md:1`). |
| 3–7 | `## Overview`: C/C++17 + Java PL, Apache 2.0, `Version 11.5.x` | Modify | `Version 11.5.x` 하드코딩 삭제(`VERSION`은 `11.5.0`이며 릴리스마다 변함). 대신 `VERSION`과 `.gitmodules`를 조회하도록 안내하고 `## Overview` 제목 없이 상단 1문단으로 압축 (`AGENTS.md:3`). |
| 9 | `.c` 파일 C++17 컴파일(`c_to_cpp.sh` 인용) 및 대형 파일 유지 | Split / Modify | `c_to_cpp.sh` 오해 교정 및 컴파일 언어 규칙은 `src/AGENTS.md:5`로 이동. 대형 파일 분할 금지 원칙은 `AGENTS.md:17`에 유지. |
| 11–60 | `## Structure`: 24개 `src/` 하위 디렉터리와 루트 디렉터리 트리, `.gitmodules` 참고 | Modify / Delete | 디렉터리 트리 전체 나열은 환경 조회(`ls`)의 중복 캐시이며 volatile 수치 위험이 큼. 대신 `## Read First`(`AGENTS.md:5-12`)에서 `src/`, `unit_tests/`, `pl_engine/`, 서브모듈(`.gitmodules`) 조건부 진입점만 남김. |
| 62–79 | `## Where to Look`: 14개 작업별 파일·함수 매핑 표 (PR `#8234`에서 68줄 수정 포함) | Delete | 기존 70줄 `btree_find()`·`btree_range_search()`가 존재하지 않음(실제 함수는 `src/storage/btree.c:24603` `btree_find_key()`, `btree.c:31437` `btree_range_scan()`). 68줄(`schema_information_schema_install.cpp`)처럼 개별 모듈 내 위치 안내는 각 `src/<module>/AGENTS.md`의 역할이므로 루트에서 제거하고 `src/<module>/AGENTS.md` 읽기로 위임 (`AGENTS.md:9`). |
| 81–93 | `## Query Processing Pipeline`: SQL → Lexer → Parser → XASL → Execution 흐름도 | Move / Modify | 엔진 내부 파이프라인이므로 루트에서 제거하고 `src/AGENTS.md:69`의 XASL 4단계 변경 영향 확인과 `src/xasl/AGENTS.md`·`src/parser/AGENTS.md`·`src/query/AGENTS.md` 연결로 통합. |
| 95–115 | `## Build Commands` & `### build.sh Options` 표 | Modify / Delete | `build.sh` 옵션 표에서 `optdebug`가 빠져 있고(`build.sh -h`와 불일치), `-C` 값 `clang14` 등 예시도 실제 스크립트(`gcc, clang`)와 다름. CLI 명령 1줄과 `./build.sh -h`, `CMakePresets.json` 참조만 남기고 옵션 표 삭제 (`AGENTS.md:24`). |
| 117–127 | `## Build Modes & Preprocessor Guards` (`SERVER_MODE`/`SA_MODE`/`CS_MODE`) | Move / Modify | 엔진 빌드 모드 상세는 `src/AGENTS.md:7-20`으로 이전(단일 출처)하고, `cubrid/`가 `cub_server`가 아닌 `libcubrid`를 빌드한다는 점과 `#if !defined(SERVER_MODE)`의 부정확한 일반화를 교정. |
| 129–150 | `## Code Style` (Formatting, Naming, Includes) | Move / Delete | 포맷터·include 순서·`memory_wrapper.hpp`·`"config.h"`·헤더 가드 규칙은 `src/` 코드 규칙이므로 `src/AGENTS.md:49-65`로 일원화. 명명 규칙 예시(`PT_NODE` 등)는 코드베이스 관례로 조회 가능해 삭제, Apache 2.0 라이선스 헤더 요건은 PR 정적 검사 원칙으로 `AGENTS.md:19`에 유지. |
| 151–162 | `## Error Handling` (`error_code.h`, `er_set`, 6곳 갱신 절차) | Move / Modify | `src/AGENTS.md:44-47`로 이전해 단일 출처화. `cubrid-cci` 실제 경로를 `cubrid-cci/src/cci/base_error_code.h`로 교정(기존 표기 `base_error_code.h`는 경로 불명확). `src/base/AGENTS.md:41,169`가 루트를 언급하는 점은 후속 과제로 별도 기록. |
| 163–165 | `## Memory Management` (`free_and_init`, `db_private_alloc`, `parser_alloc`) | Move / Modify | `src/AGENTS.md:38-43`로 이전하고 `db_private_free_and_init`, `os_free_and_init`, `parser_alloc` 수명을 추가. |
| 167–177 | `## Key Data Structures` 표 (7개 구조체) | Delete | 각 모듈 `AGENTS.md`(`src/parser/AGENTS.md`, `src/xasl/AGENTS.md`, `src/storage/AGENTS.md`, `src/transaction/AGENTS.md`)가 더 정확히 다루므로 루트에서 삭제. |
| 179–185 | `## CI` (GitHub Actions, Jenkins, CircleCI, PR 제목 regex, CLA) | Modify | `.github/workflows/check.yml`과 `.github/workflows/gha-ci.yml`(및 `gha-ci-suite.yml`, `tc-branch-sync.yml`, `tc-merge-gate.yml`) 중심으로 재정리하고 `Jenkinsfile`·`.circleci/config.yml`을 보조·레거시로 표기 (`AGENTS.md:26-27`). PR 제목 정규식은 `.github/actions/check-pr-title/action.yml:16`과 일치하는 `^\[[A-Z]+-[0-9]+\] .+`와 CLA 요건으로 `AGENTS.md:19`에 통합. |
| 187–198 | `## Anti-Patterns (This Project)` | Delete / Rewrite | 본문 규칙과 중복되고 부정 명령으로 구성됨. 189(`free` 금지)→`src/AGENTS.md:40`, 190(`#pragma once` 금지, 실제 `src/query/parallel/`과 `src/win_tools/`에 존재)→긍정 지침 `src/AGENTS.md:65`, 191-192(`memory_wrapper.hpp`)→`src/AGENTS.md:60-64`, 193-195(`src/heaplayers/`·`lea_heap.c`·`cppcheck`)→`AGENTS.md:18` 및 `src/AGENTS.md:65`, 196-197(예외·RAII 전면 금지)→삭제 후 `src/AGENTS.md:43-46`으로 교정, 198(대형 파일 분할 금지)→`AGENTS.md:17`로 통합. |
| 200–208 | `## Gotchas` | Delete / Move | 202(클라이언트 전용 파서/옵티마이저)→`src/AGENTS.md:17`에서 예외 포함 교정. 203(`src/broker/` vs `broker/`)→`src/AGENTS.md:27` CMake 등록으로 흡수. 204(LOB)→`src/AGENTS.md:74`. 205(`csql_grammar.y` 646KB)·206(`.c~`/`.cpp.orig` 추적 파일 없음)·207(비활성 테스트 중 `LOCKFREE`는 이미 활성화됨, `unit_tests/CMakeLists.txt:48`)·208(GCC/JDK/CMake 버전 중복)→삭제. |
| 210–215 | `## Important References` | Delete / Merge | `docs/install_build_requirements.md`는 `AGENTS.md:23`에 유지, `error_code.h`는 `src/AGENTS.md:45,47`에 유지, 나머지 단편 경로는 각 모듈 `AGENTS.md`에 있으므로 삭제. |

#### B. `src/AGENTS.md` (기존 46줄 → 재작성 76줄)

| 기존 줄 | 기존 내용 요약 | 판정 | 라이브 근거 및 판단 이유 |
| --- | --- | --- | --- |
| 1 | `# src/ — CUBRID Engine Source` | Keep | 제목 유지 (`src/AGENTS.md:1`). |
| 3 | `.c` 파일 C++17 컴파일(`c_to_cpp.sh`), `No C++ exceptions` | Modify | `c_to_cpp.sh` 오해 제거 및 타깃 CMake `PROPERTIES LANGUAGE CXX` 명시(`src/AGENTS.md:5`). 전면 예외 금지를 삭제하고 C 오류 코드 경계 + STL 예외 포착/변환으로 교체(`src/AGENTS.md:44-46`). |
| 5 | `24 modules. Same source → 3 binaries via SERVER_MODE/SA_MODE/CS_MODE` | Modify | 모듈 개수(`24`) 삭제. `3 binaries` 대신 공유 라이브러리(`libcubrid`, `libcubridsa`, `libcubridcs`)와 실행 파일(`cub_server`, 유틸리티)을 구분하는 `## Build-Mode Boundaries`로 확장 (`src/AGENTS.md:7-13`). |
| 7 | `For the full module list, see the root [AGENTS.md](../AGENTS.md#structure).` | Modify | 깨진 `#structure` 앵커 제거 후 `[the root AGENTS.md](../AGENTS.md)` 및 대상 모듈 `AGENTS.md`/`src/storage/docs/` 연결로 변경 (`src/AGENTS.md:3`). |
| 9–29 | `## Cross-Module Dependencies` ASCII 다이어그램 및 5개 bullet | Modify | 헤더 의존성과 실행 흐름이 뒤섞인 ASCII 다이어그램 제거. 대신 `## Cross-Module Impact Checks`에서 XASL 4단계(`xasl_generation.c`, `xasl_regu_alloc.cpp`, `xasl_to_stream.c`, `stream_to_xasl.c`, `xasl_unpack_info.*`, `query_executor.c`, `scan_manager.c`, `fetch.c`, `expr_compile.c`, `query_evaluator.c`, `query_dump.c`), storage/transaction 점검(`storage/AGENTS.md`, `transaction/AGENTS.md`, `vacuum.c`, `vacuum_oos.cpp`), 그리고 전체 그래프가 아닌 체크리스트 성격의 결합 지점만 유지 (`src/AGENTS.md:67-76`). |
| 31–35 | `## Build Integration`: 소스 목록이 `cubrid/`, `cs/`, `sa/` 3개에만 있다고 단정 | Modify | `util/`, `broker/`, `cm_common/`, `timezones/`, `win/`, `unit_tests/<module>/` CMakeLists를 포함하고 4단계 소스 추가 체크리스트 제공 (`src/AGENTS.md:22-34`). |
| 37–46 | `## Preprocessor Mode Boundaries` 표 | Modify | 표를 검증 기반 서술 목록으로 교체해 `src/optimizer/histogram/`(3모드 공통 빌더/리더 + 서버/SA 샘플러), `src/query/`·`src/storage/`·`src/transaction/`의 `cs/CMakeLists.txt` 클라이언트 부분집합, `src/compat/`·`src/connection/` 규칙, `#error Belongs to server module` 보존을 정확히 반영 (`src/AGENTS.md:15-20`). |

---

### 3. 전체 23개 `AGENTS.md` 파일 교차 점검 및 범위 외 후속 과제

저장소 내 모든 `AGENTS.md` 23개 파일을 전수 점검한 결과, 재작성된 루트 `AGENTS.md` 및 `src/AGENTS.md`와 충돌하거나 깨지는 링크·앵커는 없습니다. 다만 이번 이슈 범위 밖(수정 제외 대상)의 하위 파일에서 아래 기존 부정확성이 관찰되어 별도 후속 정리 대상으로 남깁니다.

- `src/base/AGENTS.md:41,169`: 새 오류 코드 추가 시 `(see root AGENTS.md)` / `(see root AGENTS.md for 6-place procedure)`를 평문으로 참조합니다. 현재 루트 `AGENTS.md:9`가 `src/` 오류 코드 지침으로 `src/AGENTS.md`를 가리키므로 탐색 경로는 이어지지만, 추후 `src/base/AGENTS.md` 개편 시 `src/AGENTS.md` 참조로 직접 연결하면 더 명확합니다.
- `src/executables/AGENTS.md:39-43`: `cub_server`(`server.c`)를 `cubrid/CMakeLists.txt`, `csql_launcher.c`를 `cs/CMakeLists.txt`, `unloaddb.c`를 `sa/CMakeLists.txt`로만 표기하고 `cub_master` 등을 `"top-level CMake"`로 묶어 실제 `util/CMakeLists.txt`(및 `cs/CMakeLists.txt`의 `unloaddb.c`)와 다릅니다.
- `src/communication/AGENTS.md:52`: `memory_wrapper.hpp` 마지막 include 규칙만 적혀 있고 `strict_warnings_on.hpp`/`strict_warnings_off.hpp` 허용 예외는 생략되어 있습니다.
- `unit_tests/AGENTS.md:37,58`: `lockfree/`를 비활성 상태로 표기하나, `unit_tests/CMakeLists.txt:48`에서는 이미 주석이 해제되어 있습니다.

---

### 4. 시나리오 워크스루 검증 (재작성 문서 기준)

재작성된 `AGENTS.md`와 `src/AGENTS.md`, 그리고 두 문서가 가리키는 파일만으로 아래 3가지 시나리오를 추적했습니다.

1. **시나리오 A — `src/storage/` 또는 `src/executables/`에 새 `.c`/`.cpp` 파일 추가**: **PASS**
   - 경로: `AGENTS.md:9` → `src/AGENTS.md:22-34` (형제 파일 grep으로 모든 소유 `CMakeLists.txt` 확인 → 등록 및 `.c`의 `PROPERTIES LANGUAGE CXX` 확인 → `cubrid/CMakeLists.txt` 포함 시 `src/AGENTS.md:60-64` `memory_wrapper.hpp` 규칙 적용 → 영향 타깃 빌드) + `AGENTS.md:19`(Apache 2.0 헤더) + `src/AGENTS.md:51`(`.github/workflows/codestyle.sh` 포맷터).
   - `src/executables/AGENTS.md:39`의 오래된 표가 있더라도 `src/AGENTS.md:31`의 형제 파일 검색 지침이 `util/CMakeLists.txt`를 정확히 찾게 보완합니다.
2. **시나리오 B — `src/`에서 예외를 던지는 STL(`std::vector`, `std::regex` 등) 사용**: **PASS**
   - 경로: `AGENTS.md:9` → `src/AGENTS.md:44-46` (새 STL 코드는 `.cpp` 권장, 호출부 또는 C 인터페이스 경계에서 예외 포착 후 `er_set()` + 오류 코드 반환, 실례 `src/storage/heap_file.c`, `src/optimizer/histogram/histogram_sampler_sr.cpp`, `src/query/string_regex_std.cpp`) + `src/AGENTS.md:52-58` (`.c`/`.h` 내 C++ 구문은 `/* *INDENT-OFF* */` ... `/* *INDENT-ON* */` 보호) + `src/AGENTS.md:43` (RAII 도우미 활용 가능).
3. **시나리오 C — `XASL_NODE` 또는 `PRED_EXPR` 구조 수정**: **PASS** (초기 리뷰에서 발견한 `PRED_EXPR` 누락 보완 완료)
   - 경로: `AGENTS.md:9` → `src/AGENTS.md:69` (생성 `xasl_generation.c`·`xasl_regu_alloc.cpp`, 직렬화 `xasl_to_stream.c`, 역직렬화 `stream_to_xasl.c`·`xasl_unpack_info.hpp/.cpp`, 실행·평가 `query_executor.c`·`scan_manager.c`·`fetch.c`·`expr_compile.c`·`query_evaluator.c`·`query_dump.c`, 공용 정의 `src/xasl/`·`src/query/xasl.h`) → `src/xasl/AGENTS.md`, `src/parser/AGENTS.md`, `src/query/AGENTS.md`.

## Remarks

### Test Plan

- `git diff --check` (`CBRD-27539` 워크트리): exit code `0`, 공백/개행 오류 없음.
- 전체 23개 `AGENTS.md` 링크·앵커·경로·개인정보 검증 스크립트: `ALL CHECKS PASSED across 23 AGENTS.md files.` (깨진 상대 링크·앵커 0건, 존재하지 않는 인용 경로 0건, 개인 경로/별칭 혼입 0건).
- Herdr 서브탭(`review`, Opus 5.5) 독립 리뷰 수행 후 5건의 사실 정밀화(`lea_heap.c` 부분 면제 정확화, `query_executor.c` 비대표 예제 제거, `src/optimizer/histogram/` 3모드 빌드 구분, `gha-ci.yml` 야간 스케줄·`workflow_call` 보완, `expr_compile.c`·`query_evaluator.c`·`query_dump.c` XASL 목록 추가)을 모두 반영하고 정적 검증을 재통과한 뒤 로컬 커밋(`e4da2c73ea03d079973526171a2129b2dc97cc21`)을 완료했습니다.
- 문서 전용 변경이므로 전체 엔진 빌드 및 회귀 테스트(`shell`, `sql`, `medium`)는 생략했습니다.
