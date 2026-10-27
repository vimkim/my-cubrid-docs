# CBRD-27124 버전 헤더 분리와 로컬 ccache 검증

## Purpose

2026-10-27 KST 기준 구현 검토자와 CI 담당자를 위한 기록이다. 커밋 정보만 바뀔 때 공통 헤더 소비자가 다시 컴파일되는지, 새 커밋의 전체 컴파일에서도 수정 후 캐시를 재사용하는지 확인했다.

**로컬 Debug에서는 일반 빌드의 재컴파일이 버전 소비자 11개로 제한되고, 같은 경로·옵션에서 새 커밋의 전체 재빌드 hit율은 99.07%였다. 실제 CI 개선 폭은 아직 확인하지 않았다.**

- 소스: `CUBRID/cubrid`, 기준 `2d925cb8685600135eb1fb1781811f6b45fdecb0`.
- 구현: `0d2a76e60f944be0ababe9c466766c553189fcda`, 소스 tree `7ba3a7225217f9dd7957478a28118973b9ab5aba`.
- 관련 이슈: [CBRD-27124](https://jira.cubrid.org/browse/CBRD-27124).
- [PR #8254](https://github.com/CUBRID/cubrid/pull/8254)는 `e5013d4b881511281a3ba1ad99e4df7b6c402dc6`로 머지되었다. 빌드별 ccache 통계가 제공되지만, 이 변경 자체가 버전 헤더의 캐시 무효화를 없애지는 않는다.

## Implementation

`config.h`는 기존처럼 `version.h`를 포함한다. 이 헤더에는 제품 major/minor/patch와 빌드 모드처럼 커밋마다 바뀌지 않는 값만 남긴다. `EXTRA_VERSION`, `BUILD_NUMBER`, `VERSION_STRING`은 새 `build_version.h`로 옮긴다.

변동 헤더는 `src/base/release_string.c`와 broker의 직접 소비자 7개 소스가 포함한다. 공통 인터페이스인 `release_string.h`는 변동 헤더를 포함하지 않는다. 대신 `rel_version_string()`을 조건 없이 선언한다. 구현도 항상 같은 API를 제공한다. API의 기존 심벌과 반환 형식은 유지한다.

`cmake/TrackGitRevision.cmake`는 Git의 `rev-parse --git-path`로 현재 checkout의 HEAD와 공유 ref 경로를 구한다. HEAD, 존재하는 reflog·packed-refs·reftable 목록, 현재 branch ref를 CMake 구성 의존성으로 등록한다. packed ref라서 loose ref 파일이 없으면 가장 가까운 기존 상위 디렉터리를 감시한다. 새 커밋이 loose ref를 만드는 경우도 이 경로로 감지한다.

CMake 재구성에서 기존 버전 계산을 다시 실행하므로 런타임 헤더와 CPack 메타데이터가 같은 버전을 사용한다. `configure_file()`은 내용이 같은 헤더의 시간을 보존한다. 명시적인 `VERSION`의 네 번째 숫자나 `VERSION-DIST`를 처리하는 기존 우선순위는 변경하지 않았다.

구현 위치는 다음과 같다. 모두 위 구현 커밋 기준이다.

| 파일 | 책임 |
| --- | --- |
| `CMakeLists.txt` | Git 감시 등록과 두 버전 헤더 생성 |
| `cmake/TrackGitRevision.cmake` | checkout별 Git 메타데이터 의존성 |
| `cmake/version.h.cmake` | 공통 제품 버전·빌드 모드 |
| `cmake/build_version.h.cmake` | 커밋 수·해시를 포함한 버전 |
| `src/base/release_string.c`, `src/base/release_string.h` | 버전 문자열 API와 매크로 격리 |
| `src/broker/`의 직접 소비자 | broker/CAS 버전 출력 |
| `cmake/tests/test_build_version.py` | 공통 헤더 캐시와 Git 감지 회귀 검증 |

## Remarks

### 환경과 측정 방법

Rocky Linux 9 계열, x86_64, GCC 11.5.0, CMake 3.26.5, Ninja 1.10.2, ccache 4.5.1을 사용했다. 빌드는 Debug이며 `-O0 -ggdb3 -fno-omit-frame-pointer`와 프로젝트의 기존 Debug 플래그를 적용했다. CCI를 포함하고 JDBC·Manager는 현재 로컬 구성에서 제외했다. 기존 개발 캐시와 별도의 전용 캐시를 사용하고 각 측정은 서로 다른 `CCACHE_STATSLOG`로 집계했다.

기준 소스를 빌드한 뒤 수정본을 재구성·빌드해 수정 후 캐시를 채웠다. 이후 실제 소스 내용이 같은 빈 커밋을 `git commit-tree`로 만들고 같은 linked worktree에서 detached checkout했다. 측정용 커밋은 PR branch의 이력에 넣지 않았다.

일반 증분 빌드는 입력을 그대로 두고 빌드만 실행했다. 전체 컴파일의 캐시 재사용 측정에서는 Ninja dependency DB에서 `version.h`에 의존하는 오브젝트 1,177개만 제거했다. 소스와 헤더의 내용·시간은 그대로 유지했다. 두 경우 모두 별도의 configure 명령 없이 빌드 시스템이 재구성을 수행했다. 일반 CMake 명령으로 표현하면 `cmake --build <build-dir>` 경로이다.

전체 재빌드 전후 `compile_commands.json`의 바이트가 같음을 확인했다. 빌드 로그에서 실제 compile 작업을 세고, 빌드별 ccache 로그에서 hit/miss를 집계했다. `cubrid_rel`은 해당 빌드의 라이브러리를 선택해 실행했다. 설치 뒤에도 설치된 라이브러리와 실행 파일로 현재 버전을 확인했다.

### 실측 결과

| 조건 | compile | hit / miss | hit율 | 빌드 시간 |
| --- | ---: | ---: | ---: | ---: |
| 수정 후 동일 커밋 no-op | 0 | 0 / 0 | 해당 없음 | 1.629초 |
| 빈 커밋 B, 일반 증분 빌드 | 11 | 0 / 11 | 0% | 7.572초 |
| 빈 커밋 D, 오브젝트 1,177개 제거 후 재빌드 | 1,177 | 1,166 / 11 | **99.07%** | 7.820초 |
| 구현 커밋 A로 복귀 | 11 | 8 / 3 | 72.73% | 7.328초 |

A는 구현 커밋이다. B는 `2b27027879e47ab88e3810e8a73cb718ba3599c9`, D는 `6b3aa2384f8cf5810fd808c78581072f4de5a9f5`다. 세 커밋의 Git tree가 같다.

일반 증분 빌드의 0%는 실제로 컴파일한 11개 버전 소비자의 수치다. 관계없는 1,166개는 컴파일 자체를 생략했다. 따라서 이 0%를 전체 캐시 재사용 실패로 해석하면 안 된다. 전체 컴파일을 강제한 D에서 관계없는 오브젝트의 재사용을 별도로 확인했다.

분리 전 Ninja dependency DB에서 변동 `version.h`의 소비자는 1,177개였다. 분리 후 고정 `version.h`의 소비자 수는 같지만, 변동 `build_version.h`는 11개 오브젝트에만 연결된다. 이 숫자는 현재 구성의 관측값이며 모든 플랫폼과 빌드 옵션에 적용되는 상수는 아니다.

B의 `version.h` 내용과 mtime은 모두 보존되었다. `build_version.h`, `cubrid_rel`, `CPACK_PACKAGE_VERSION`은 `11.5.0.2765-2b27027`로 일치했다. D에서도 `11.5.0.2765-6b3aa23`로 일치했다. 마지막에는 named topic branch와 구현 커밋으로 복귀하고 설치된 `cubrid_rel`의 `11.5.0.2764-0d2a76e`를 확인했다.

### 회귀 검증과 제한

`python3 cmake/tests/test_build_version.py`의 두 테스트가 통과했다. 첫 테스트는 실제 헤더 템플릿을 생성하고 공통 헤더만 쓰는 C 파일을 `-ggdb3`로 컴파일한다. 버전 값을 바꾼 뒤 같은 파일이 ccache hit가 되는지 검사한다. 수정 전 템플릿에서는 같은 검사가 cache miss로 실패했다.

두 번째 테스트는 Ninja와 Unix Makefiles, 일반 clone과 linked worktree, 공백이 있는 경로, reflog 비활성 상태의 packed/loose ref, detached HEAD의 새 커밋, 같은 revision의 branch 전환을 확인한다. 최소 fixture가 실제 `TrackGitRevision.cmake`를 사용하며, 버전이 바뀌지 않으면 출력 timestamp도 보존되는지 검사한다.

현재 로컬 구성에서는 ctest가 등록된 테스트를 찾지 못했다. 이를 ctest 통과로 세지 않았다. Windows, reftable 저장소, 실제 소스 배포본 및 전체 SQL·shell·medium 회귀는 실행하지 않았다. 소스 배포본의 버전 우선순위는 변경하지 않았다는 소스 검토 범위에 한정한다.

측정 준비 중 `include/system.h`를 touch해 전체 컴파일을 강제한 별도 실험에서는 0/1,177 hit를 관찰했다. 이 경우 헤더 시간 정보도 바뀌므로 커밋 정보만 달라지는 비교에 사용하지 않았다. 해당 현상의 원인을 이 작업에서 확정하지 않았다. 위 99.07%는 오브젝트만 제거하고 헤더 시간 정보를 보존한 독립 측정의 결과다.

### CI에서 확인할 내용

CI는 Release와 OptDebug를 빌드하며 ccache 3.7.7과 노드별 공유 캐시를 사용한다. PR 빌드는 `CCACHE_READONLY=1 CCACHE_NOSTATS=1`이므로 수정 후 캐시를 공유 저장소에 채우지 않는다. `version.h` 구조가 다른 기존 develop 캐시와 비교하는 첫 PR 빌드에서는 엔진 miss가 많을 수 있다. 이 한 번의 수치만으로 버전 변경 사이의 정상 재사용 여부를 판정하지 않는다.

Draft PR 발행 후 `/run all` 한 번을 실행하고, #8254가 추가한 `ccache, this build:` 줄을 Release/OptDebug 각각 기록할 예정이다. 노드 누적 `ccache -s` 수치를 현재 빌드의 적중률로 사용하지 않는다. 로컬 99.07%를 실제 CI 개선율로 제시하지 않는다. CI의 수정 후 warm-cache 비교에는 같은 경로·옵션의 수정 후 캐시가 먼저 있어야 한다.

SQL·shell·medium TC 변경은 필요하지 않다. 자동 생성된 TC PR은 인간에게 알려 종료하도록 요청하며 agent가 merge/close하지 않는다. CI가 끝나면 결과와 TC Merge Gate를 보고하고 후속 수정이나 재실행 없이 지시를 기다린다.
