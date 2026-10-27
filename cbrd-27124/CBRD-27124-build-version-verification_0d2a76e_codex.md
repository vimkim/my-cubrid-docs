# CBRD-27124 버전 헤더 분리와 로컬 ccache 검증

## Purpose

2026-10-27 KST 기준 구현 검토자와 CI 담당자를 위한 기록이다. 커밋 정보만 바뀔 때 공통 헤더 소비자가 다시 컴파일되는지, 새 커밋의 전체 컴파일에서도 수정 후 캐시를 재사용하는지 확인했다.

**로컬 Debug에서는 일반 빌드의 재컴파일이 버전 소비자 11개로 제한되고, 같은 경로·옵션에서 새 커밋의 전체 재빌드 hit율은 99.07%였다. 최초 실제 CI의 hit율은 Release 80.28%, OptDebug 59.25%였으며 상승은 확인되지 않았다. CI 빌드·shell·medium은 통과했고 SQL 3개 실패로 전체 run은 실패했다.**

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

### 실제 CI 빌드 결과

[Draft PR #8298](https://github.com/CUBRID/cubrid/pull/8298)을 발행하고, 승인한 소스 SHA 그대로 `/run all`을 한 번 실행했다. [Run 40487586838](https://github.com/CUBRID/cubrid/actions/runs/40487586838)은 **failure로 종료**했다. API 최종 갱신 시각은 2026-10-27T11:44:36Z이며, 요청한 10분 주기 감시에서 20:52 KST에 완료를 확인했다.

| 검증 | 최종 결과 |
| --- | --- |
| Release 빌드 | 통과 |
| OptDebug 빌드 | 통과 |
| shell | 50개 shard 모두 성공, suite 상태 통과 |
| medium | 975개 실행, 실패 0, skip 0, suite 상태 통과 |
| SQL | 8개 shard 성공, 2개 shard 실패, 실패 testcase 3개 |

SQL 실패 목록은 다음과 같다. 각 shard가 배정된 testcase를 모두 실행한 뒤 실패 수를 보고했음을 로그에서 확인했다. 이번 변경과의 관련성이나 원인은 분석하지 않았다.

- [SQL shard 03](https://github.com/CUBRID/cubrid/actions/runs/40487586838/job/122136912412): `sql/_13_issues/_24_1h/cases/cbrd_25238.sql` — 2,842개 실행 중 1개 실패, skip 0.
- [SQL shard 09](https://github.com/CUBRID/cubrid/actions/runs/40487586838/job/122136912437): `sql/_36_guava/cbrd_27657/cases/cbrd_27657.sql`, `sql/_36_guava/cbrd_27644/cases/cbrd_27644.sql` — 455개 실행 중 2개 실패, skip 0.

최종 `gh pr checks --required`에서 9개 필수 검사 중 7개가 통과하고 `gha-ci: test_sql`과 `Check TC PRs`가 실패했다. `code-style`, `pr-style`, `license`, `cppcheck`와 나머지 필수 gha-ci 검사들은 통과했다. OptDebug 빌드 상태도 통과했다.

비교 대상은 PR의 기준 소스 `2d925cb8685600135eb1fb1781811f6b45fdecb0`의 [develop push run 40481418559](https://github.com/CUBRID/cubrid/actions/runs/40481418559)이다. 아래 값은 #8254가 추가한 **빌드별 합계**이며, 엔진 외에 3rdparty 컴파일도 포함한다. 노드 누적 `ccache -s` 수치는 사용하지 않았다.

| 빌드 | 소스 | direct hit | preprocessed hit | miss | hit율 |
| --- | --- | ---: | ---: | ---: | ---: |
| [기준 Release](https://github.com/CUBRID/cubrid/actions/runs/40481418559/job/122112434651) | `2d925cb` | 1,919 | 1,175 | 83 | 97.39% |
| [PR Release](https://github.com/CUBRID/cubrid/actions/runs/40487586838/job/122133226817) | `0d2a76e` | 1,919 | 699 | 643 | 80.28% |
| [기준 OptDebug](https://github.com/CUBRID/cubrid/actions/runs/40481418559/job/122112434693) | `2d925cb` | 1,916 | 16 | 1,245 | 60.81% |
| [PR OptDebug](https://github.com/CUBRID/cubrid/actions/runs/40487586838/job/122133226809) | `0d2a76e` | 1,916 | 16 | 1,329 | 59.25% |

**이번 최초 PR 빌드에서 CI 적중률 상승은 확인되지 않았다.** 기준과 PR의 hit/miss 집계 대상 수도 3,177개와 3,261개로 다르다. 이 합계만으로 엔진과 3rdparty 각각의 적중률 또는 추가 miss 84개의 원인을 확정할 수 없다. OptDebug의 hit 수는 두 빌드 모두 1,932개로 같다. 60.81% → 59.25%의 수치 변화는 miss가 84개 늘어 분모가 커진 결과다. 바깥 Ninja 로그의 C/C++ 오브젝트 컴파일 작업은 두 빌드 모두 1,251개였다. 따라서 빌드 전체 hit/miss 집계 수를 그대로 엔진 오브젝트 수로 읽지 않는다.

CI의 PR 빌드는 `CCACHE_READONLY=1 CCACHE_NOSTATS=1`이다. 현재 공유 캐시는 수정 전 공통 버전 매크로가 있던 컴파일 결과를 담고 있다. 이번 변경은 매크로 정의를 제거하여 첫 전처리 입력을 바꾸므로, 수정 전 캐시와의 비교에서 바로 높은 적중률을 기대할 수 없다. 새 구조로 만든 결과도 PR 빌드에서는 공유 캐시에 저장하지 않는다. 로컬 99.07%는 수정 후 캐시를 먼저 채웠으므로 비교 조건이 다르다. 수정 후 커밋 사이의 CI 재사용을 검증하려면 같은 CI 경로·옵션에서 수정본 A로 전용 캐시를 채우고 수정본 B로 비교해야 한다. 이 실험은 아직 하지 않았다.

### GCC 8에서도 매크로 변경은 miss를 만드는가

사용자의 후속 질문에 따라, 로컬에 있던 Rocky Linux 8.10 컨테이너에서 GCC 8.5.0 (`Red Hat 8.5.0-28`)과 ccache 3.7.7로 최소 실험을 추가했다. 새 CI 실행은 하지 않았다. 별도 임시 캐시에서 첫 컴파일을 저장하고, 사용하지 않는 `VERSION_STRING` 정의만 A에서 B로 바꾼 뒤 같은 소스를 다시 컴파일했다. 비교용 라이브러리 소스는 이 버전 헤더를 포함하지 않는다.

| 옵션과 입력 | 두 번째 컴파일 | 전처리 A/B |
| --- | --- | --- |
| `-ggdb3`, 버전 헤더를 포함하는 소스의 매크로 A → B | hit 0 / miss 1 | 다름 |
| `-ggdb3`, 버전 헤더를 포함하지 않는 독립 라이브러리 소스 | direct hit 1 / miss 0 | 입력 동일 |
| `-ggdb`, 버전 헤더를 포함하는 소스의 매크로 A → B | preprocessed hit 1 / miss 0 | 같음 |
| `-ggdb`, 독립 라이브러리 소스 | direct hit 1 / miss 0 | 입력 동일 |

추가로 G++ 8.5.0에 CUBRID OptDebug의 주요 옵션 순서인 `-O2 -finline-functions -ggdb3 -Wall -DCUBRID_OPTDEBUG -ggdb -fno-omit-frame-pointer -fPIE -std=c++17`를 적용해 같은 실험을 반복했다. 뒤에 `-ggdb`가 있어도 전처리 출력에 버전 매크로가 남았고, 버전 매크로 변경 소스는 hit 0 / miss 1, 독립 라이브러리는 direct hit 1 / miss 0이었다.

이는 GCC 8의 동작이 달라서 CI 전체 hit가 약 60%가 된다는 설명을 지지하지 않는다. [GCC 8 문서](https://gcc.gnu.org/onlinedocs/gcc-8.1.0/gcc/Debugging-Options.html)도 디버그 레벨 3이 매크로 정의를 포함한다고 설명한다. `-ggdb3`인 모든 컴파일이 항상 miss인 것이 아니라, 해당 소스의 전처리 입력에 포함된 매크로 정의가 달라지는 조건이 문제다.

이슈의 “CUBRID 소스 구간 0%”와 CI의 “빌드 전체 60.81%”는 분모가 다르다. 기준 OptDebug는 `(1916 + 16) / (1916 + 16 + 1245) = 60.81%`다. 독립적으로 빌드하는 3rdparty가 CUBRID 버전 헤더의 영향을 받지 않아 hit를 유지하면, 엔진이 miss여도 전체 hit율은 높게 남을 수 있다. 현재 로그는 파일별 cache 결과를 보존하지 않아 1,932개 hit의 정확한 소속은 확정하지 않았다. 원래 이슈가 실제 CI 엔진 구간에서도 정확히 0%인지까지 이번 합계로 검증한 것은 아니다.

### clean build와 3rdparty의 관계

사용자가 제시한 `./build.sh clean build` 경로도 확인했다. `CUBRID/cubridci`의 `build_rl8.10` 브랜치 소스 `4ea4e8a714078e11002d9402b9011e647c473bea`에서 [entrypoint](https://github.com/CUBRID/cubridci/blob/4ea4e8a714078e11002d9402b9011e647c473bea/docker/ci/docker-entrypoint.sh)는 `./build.sh -p $CUBRID $@ clean build`를 실행한다. [Dockerfile](https://github.com/CUBRID/cubridci/blob/4ea4e8a714078e11002d9402b9011e647c473bea/docker/ci/Dockerfile)은 `CC="ccache gcc"`, `CXX="ccache g++"`를 설정한다. 실제 workflow는 `cubridci/cubridci:build_rl8.10` 태그를 사용하며 이미지 빌드 commit/digest는 이번 작업에서 확정하지 않았다.

구현 커밋의 `build.sh:162`부터 시작하는 `build_clean()`은 선택한 빌드 디렉터리의 내용을 제거한다. `3rdparty/CMakeLists.txt:103`은 ExternalProject 상태를 그 아래에 둔다. 따라서 clean 뒤에는 3rdparty의 download/configure/build/install 단계도 다시 실행된다. 이번 실제 PR 로그에도 libedit와 OpenSSL 등의 단계가 다시 나온다.

그러나 ccache 저장소는 workflow가 지정한 `/home/ci/cache/ccache/develop-<mode>`로 빌드 디렉터리 밖에 있다. clean이 이 저장소를 지우지는 않는다. 따라서 **3rdparty를 다시 빌드 대상으로 삼는 것과 컴파일 캐시가 miss가 되는 것은 별개**다. 캐시가 있으면 컴파일은 재사용할 수 있지만 configure, 링크, 설치 등의 비용은 남는다. direct hit 수도 기준과 PR에서 각각 1,919/1,916으로 같았다. 이 숫자를 파일별 근거 없이 모두 3rdparty hit라고 단정하지 않는다.

CI는 매번 clean하므로 로컬 증분 빌드의 “11개만 컴파일” 효과는 직접 적용되지 않는다. CI에서는 전체 컴파일 명령이 실행되는 조건에서도 수정 후 캐시를 다른 커밋에서 재사용하는 효과를 검증해야 한다.

SQL·shell·medium TC 변경은 없다. 자동 생성된 [공개 TC PR #3897](https://github.com/CUBRID/cubrid-testcases/pull/3897), [비공개 TC PR #4588](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4588)은 모두 OPEN/DRAFT이며 실제 changedFiles/additions/deletions가 0/0/0이다. 최종 [TC Merge Gate](https://github.com/CUBRID/cubrid/pull/8298#issuecomment-6439286293)는 이 두 PR이 열려 있어 차단 상태다. 인간이 빈 TC PR을 닫고 TC Merge Gate 검사를 다시 실행해야 한다. Agent는 TC PR merge/close나 gate 재실행을 하지 않았다.

이 한 번의 gha-ci 실행 결과를 기록하고 감시를 종료했다. 소스·TC 후속 수정, 추가 push, CI 재실행은 하지 않았다. 소스 checkout은 `CBRD-27124-isolate-build-version`의 `0d2a76e60f944be0ababe9c466766c553189fcda`로 깨끗하며 원격 head도 같다. 기존 develop과 이전 분석 worktree의 변경은 보존했다. 문서는 별도 docs task branch에 로컬 커밋으로 남기고 main 통합·push는 하지 않았다.
