# CBRD-27124: 커밋 변경과 재구성 후 Debug 빌드의 ccache 실측

- 측정일: 2026-10-21, Asia/Seoul
- 대상 독자: CBRD-27124의 재빌드 비용과 캐시 효과를 검토하는 개발자
- 관련 이슈: [CBRD-27124](https://jira.cubrid.org/browse/CBRD-27124), [CBRD-25560](https://jira.cubrid.org/browse/CBRD-25560)
- 기존 설계 맥락: [버전 갱신 분석 지도](wayfinder/map.md)

## 확인한 질문과 결론

소스 내용은 그대로 두고 커밋만 바꾼 뒤 CMake를 재구성하면, 이미 채워 둔 ccache가 재컴파일 결과를 재사용하는지 측정하였다.

측정한 로컬 Debug 구성에서는 **1,135개 오브젝트가 다시 컴파일되었고, 빌드 구간의 ccache 결과는 hit 0 / miss 2,270, hit율 0.00%, 소요 시간 152.8초**였다. 같은 커밋을 전체 재빌드한 대조군은 hit율 99.43%였다. 원래 커밋으로 돌아가 재구성한 뒤 빌드하면 99.47%로 다시 높아졌다.

이 결과는 동일 커밋의 재빌드에서 캐시가 작동하더라도, 커밋 버전 값이 바뀌면 이번 Debug 구성의 캐시를 재사용하지 못한다는 근거이다. CI의 실행별 hit율, OptDebug, 다른 소스 리비전의 결과는 이 실험으로 확정하지 않는다.

## 소스와 측정 환경

| 항목 | 값 |
| --- | --- |
| 소스 저장소 | `CUBRID/CUBRID` |
| 기준 커밋 A | `f30f1c26003e5aa8e93182648e06cad76fc77064` |
| 시험 커밋 B | `d606df3f6c6ef152a8f1ba9a0c2cd4e7232f01ba` |
| 두 커밋의 Git tree | `7513717b0474014493e47b1717cf2d8453af3040`으로 동일 |
| B의 parent | A. `git commit-tree`로 만든 빈 커밋을 detached HEAD에서 사용 |
| 원래 브랜치 | `CBRD-27124-cubrid-rel-hash` |
| OS | Rocky Linux 9.6, Linux x86_64 |
| 도구 | GCC 11.5.0, ccache 4.5.1, CMake 3.26.5, Ninja 1.10.2 |
| 빌드 구성 | `debug_gcc`, `CMAKE_BUILD_TYPE=Debug`, 병렬 작업 16개 |
| 확인한 Debug 옵션 | `-O0 -ggdb3 -ggdb3 -ggdb` 및 `-fno-omit-frame-pointer`. 동일한 로컬 추가 include 설정도 두 커밋에서 유지 |
| 캐시 | 새 전용 디렉터리, 최대 20G, `stats=true`, `direct_mode=true` |
| 통계 구간 | 각 빌드 직전 카운터 초기화. 커밋 변경 실험은 재구성 후 초기화하여 구성 단계의 호출을 제외 |
| 빌드 범위 | 구성된 기본 빌드 대상과 CCI, 외부 라이브러리. JDBC와 Manager 서브모듈은 초기화되지 않아 제외 |

원래 체크아웃에는 CCI의 생성된 `win/cci_version.h` 변경과 추적되지 않은 분석 문서 3개가 있었다. 이를 보존하였고, CUBRID 엔진 소스를 수정하지 않았다. B를 측정하는 동안 원래 브랜치의 tip도 변경하지 않았다.

전역 개발 캐시는 비우지 않았다. 첫 빌드 전에 전용 캐시를 비웠고, 이후에는 캐시 내용은 유지하면서 통계만 초기화하였다. 캐시는 측정 종료 시 약 1.84GB로 20G 한도보다 작았다.

## 실측 결과

| 조건 | 실제 compile 작업 수 | Direct hit | Preprocessed hit | Miss | Hit율 | 빌드 시간 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A, 빈 캐시에서 최초 빌드 | 1,189 | 30 | 7 | 3,999 | 0.92% | 275.1초 |
| A, 오브젝트 제거 후 같은 커밋 전체 재빌드 | 1,189 | 1,493 | 72 | 9 | 99.43% | 23.4초 |
| B, 캐시 유지 및 재구성 후 증분 빌드 | **1,135** | **0** | **0** | **2,270** | **0.00%** | **152.8초** |
| A로 복귀, 캐시 유지 및 재구성 후 빌드 | 1,135 | 1,132 | 0 | 6 | 99.47% | 31.2초 |

모든 빌드는 성공하였다. 시간은 빌드 명령의 벽시계 시간이다. B의 재구성에는 별도로 1.35초가 걸렸다. 각 조건을 한 번씩 실행했으며, 공유 서버의 부하를 통제한 반복 성능 실험은 아니다. 최초 두 빌드에는 외부 라이브러리의 구성·빌드 작업이 포함되며, B의 빌드는 기존 산출물에서 버전 변경으로 무효화된 대상을 갱신한다. 시간 차이를 동일 작업량의 순수 ccache 비용으로 해석하지 않는다.

### 카운터와 오브젝트 수의 차이

Hit율의 분모는 `direct hit + preprocessed hit + miss`이다. 링크와 전처리 전용 호출 등 uncacheable 결과는 분모에서 제외한다. 빈 캐시의 첫 빌드에도 같은 빌드 안에서 반복되는 작업의 hit가 발생할 수 있다.

이번 Ninja 규칙은 `ccache /usr/lib64/ccache/g++ ...` 또는 `ccache /usr/lib64/ccache/gcc ...` 형태였다. launcher와 compiler 경로에 ccache가 함께 있었고, B의 1,135개 compile 작업에 대해 카운터에는 2,270개 miss가 기록되었다. **2,270은 오브젝트 수가 아닌 ccache 호출 카운터**이다. 이 중첩 구성을 이번 측정에서 변경하지 않았으며, 중첩 유무에 따른 성능 비교는 수행하지 않았다.

같은 출력의 primary storage hit는 `2264 / 4534 (49.93%)`였다. 이는 저장소 조회 통계이며, 컴파일 결과를 재사용한 hit율 0.00%와 구분한다. B의 uncacheable 1,175건은 전처리 전용 호출 1,135건과 링크 40건이었다.

### 같은 커밋의 전체 재빌드 확인

두 번째 빌드 전에 Ninja clean을 실행하였다. 1,373개 파일을 정리한 뒤 RapidJSON의 비어 있지 않은 include 디렉터리를 제거하지 못해 종료 코드 1을 반환하였다. 이 오류를 성공으로 처리하지 않았다.

정리 후 `compile_commands.json`의 출력 경로를 모두 확인하여 **구성된 1,189개 오브젝트가 전부 없어진 것**을 검증하였다. 이어진 빌드 로그에서도 1,189개 compile 작업을 확인하였다. 따라서 99.43%는 아무 작업도 하지 않은 빌드의 수치가 아니다. 외부 프로젝트의 정리 범위는 엔진 오브젝트 정리와 같다고 가정하지 않는다.

## 커밋 변경으로 바뀐 입력

A와 B의 Git tree는 같았다. 재구성 전후 `compile_commands.json`의 SHA-256도 같았다. `version.h`에서는 다음 세 매크로만 바뀌었다.

```diff
-#define EXTRA_VERSION 2374
+#define EXTRA_VERSION 2375
-#define BUILD_NUMBER 11.5.0.2374
+#define BUILD_NUMBER 11.5.0.2375
-#define VERSION_STRING "11.5.0.2374-f30f1c2"
+#define VERSION_STRING "11.5.0.2375-d606df3"
```

재구성 후 Ninja dry-run은 compile 작업 1,135개를 예약했다. 실제 빌드 로그의 compile 작업 수도 1,135개였다. `cubrid_rel`은 B 빌드에서 `11.5.0.2375-d606df3`을 출력하였다.

이 경로의 소스 근거는 기준 커밋에 고정한다.

- [CMakeLists.txt의 커밋 수·해시 계산과 HEAD 감시](https://github.com/CUBRID/CUBRID/blob/f30f1c26003e5aa8e93182648e06cad76fc77064/CMakeLists.txt#L102-L183)
- [config.h가 version.h를 포함하는 경로](https://github.com/CUBRID/CUBRID/blob/f30f1c26003e5aa8e93182648e06cad76fc77064/cmake/config.h.cmake#L95)
- [version.h의 변동 매크로 정의](https://github.com/CUBRID/CUBRID/blob/f30f1c26003e5aa8e93182648e06cad76fc77064/cmake/version.h.cmake)
- [Debug·OptDebug의 -ggdb3 설정](https://github.com/CUBRID/CUBRID/blob/f30f1c26003e5aa8e93182648e06cad76fc77064/CMakeLists.txt#L220-L246)

## 재현 절차

아래는 실제 측정 순서를 표준 Git·CMake·ccache 명령으로 표현한 절차이다. 먼저 기준 커밋 A와 환경 표의 옵션으로 Debug/Ninja 빌드 디렉터리를 구성한다. `build_dir`은 그 디렉터리이다. 컴파일러 launcher와 PATH의 compiler wrapper 구성도 환경 표에 맞춘다. 다른 옵션·대상 구성에서는 작업 수와 시간이 달라질 수 있다.

1. 새 전용 캐시를 지정한다. 최대 20G, `stats=true`, `direct_mode=true`를 설정한다. 기존 개발 캐시와 분리한다.
2. 캐시와 카운터를 비우고 A를 빌드한다. 빌드 로그, 벽시계 시간, `ccache --print-stats`, `ccache --show-stats --verbose`를 저장한다.
3. 빌드 오브젝트를 정리한다. `compile_commands.json`에 있는 출력 파일이 모두 없는지 확인한다. 캐시는 유지하고 카운터만 초기화하여 A를 다시 빌드한다.
4. A와 동일한 tree를 갖는 빈 커밋 B를 만들고, B를 체크아웃한다. 원래 브랜치는 보존한다.
5. CMake를 재구성하고 전후 `version.h`와 `compile_commands.json`을 비교한다. Ninja dry-run으로 예정된 compile 작업을 센다.
6. 캐시는 유지하고 카운터만 초기화한다. 정리 명령 없이 B를 빌드하여 버전 변경으로 발생한 재컴파일만 측정한다.
7. 원래 브랜치로 복귀한다. 재구성·빌드 후 헤더와 `cubrid_rel`의 원래 버전, 기존 Git 상태의 보존을 확인한다.

핵심인 4~6단계는 다음과 같다. `build_dir`과 `CCACHE_DIR`은 앞 단계에서 사용한 값을 유지한다.

```bash
original_branch=$(git symbolic-ref --short HEAD)
original_commit=$(git rev-parse HEAD)
original_tree=$(git rev-parse 'HEAD^{tree}')
probe_commit=$(git -c commit.gpgsign=false commit-tree "$original_tree" \
  -p "$original_commit" -m "Measure version-only commit cache invalidation")
git -c submodule.recurse=false switch --detach "$probe_commit"

cmake -S . -B "$build_dir"
ninja -C "$build_dir" -n > planned-build.log
ccache --zero-stats
export CCACHE_STATSLOG="$evidence_dir/build-ccache.log"
/usr/bin/time -p cmake --build "$build_dir" --parallel 16 \
  > "$evidence_dir/build.log" 2>&1
ccache --print-stats > "$evidence_dir/build-stats.tsv"
ccache --show-stats --verbose > "$evidence_dir/build-stats.txt"
"$build_dir/bin/cubrid_rel"

git -c submodule.recurse=false switch "$original_branch"
```

`evidence_dir`은 미리 만든 로그 디렉터리이다. 통계 기록을 끄는 `CCACHE_NOSTATS`와 읽기 전용·강제 재컴파일 설정은 적용하지 않는다. 실제 측정에서는 구성 단계와 빌드 단계에 별도 stats log를 지정하였다. 위 코드 블록은 재현 절차이며 원시 실행 스크립트의 전문은 아니다.

## 해석과 남은 검증

이번 관측은 공통 헤더에 들어 있는 변동 버전 값이 넓은 재빌드를 유발하고, 현재 Debug 옵션에서는 캐시 재사용도 막는다는 기존 설명을 실제 CUBRID 빌드로 보강한다. 같은 설정의 작은 C++ 예제에서도 미사용 `VERSION_STRING`을 A에서 B로 바꾸면 현재 Debug 옵션은 miss 1, `-ggdb` 대조군은 preprocessed hit 1이었다. 같은 매크로 값에서는 두 옵션 모두 hit였다.

원래 A로 복귀한 뒤 `version.h`가 측정 전 내용과 바이트 단위로 같아졌고, 원래 브랜치·커밋·Git 상태도 복구되었다. 재빌드의 hit율은 99.47%였다. 설치나 DB 실행은 수행하지 않았다.

이 측정은 다음 항목을 검증하지 않았다.

- 현재 `origin/develop`에서의 실제 재빌드 수와 시간. A는 2026-07-27 커밋이며 측정 시점의 `origin/develop`보다 343개 커밋 뒤에 있었다.
- OptDebug·Release, 다른 GCC·ccache 버전, Windows, 다른 generator의 결과.
- CI의 실행별 hit율. 기존 59.82% 표시 문제는 [CI 통계 확인 문서](../code-analysis/build/cubrid-ci-ccache-statistics-note_2026-10-21.md)에 별도로 기록되어 있다.
- 캐시를 사용하지 않는 동일 조건 대조군, ccache 중첩 제거의 효과, 반복 실행의 중앙값.
- 빈 커밋 뒤 명시적 재구성 없이 빌드하는 경로. 이번 B 측정은 명시적으로 재구성했으며 detached HEAD를 사용했다.
- broker 버전 출력과 패키지의 버전 일관성. 이번 실행에서는 `cubrid_rel`만 확인했다.

따라서 확인된 결론은 이 기준 리비전과 로컬 Debug 구성의 결과로 제한한다. 다음 검증에서는 최신 기준 소스의 Debug·OptDebug를 각각 측정하고, 실제 compile 작업 수와 캐시 호출 카운터를 계속 분리해야 한다.

## 원시 근거 위치

실행 로그와 캐시는 Git에 넣지 않았다. 아래는 측정 서버에 보존한 원시 자료의 위치이며 공개 재현에 필요한 저장소 파일로 간주하지 않는다.

- 근거 디렉터리: `/home/vimkim/tmp/CBRD-27124-ccache-wetkan1_`
- 최초·동일 커밋 빌드: `build-1.log`, `build-2.log`, 각 `build-*-stats.tsv`·`build-*-stats.txt`, `clean-verification.json`, `summary.json`
- 커밋 변경: `commit-change/state.json`, `version.diff`, `planned-build.log`, `build.log`, `build-stats.tsv`, `build-ccache.log`, `summary.json`
- 복구: `commit-change/restore-build.log`, `restore-build-stats.tsv`, `restoration.json`

이 문서에는 위 자료에서 검토에 필요한 값과 한계를 추려 기록했다. 카운터의 의미는 [ccache 4.5.1 문서](https://ccache.dev/manual/4.5.1.html#_cache_statistics), 매크로 디버그 정보는 [GCC Debugging Options](https://gcc.gnu.org/onlinedocs/gcc/Debugging-Options.html)를 참고한다.
