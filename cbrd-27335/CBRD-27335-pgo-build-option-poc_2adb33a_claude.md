# [CBRD-27335] Add PGO build option for GCC (PoC)

- JIRA: https://jira.cubrid.org/browse/CBRD-27335
- Source commit: `2adb33a37` (base: develop `04620b2ce`)

## Purpose

CUBRID를 PGO(Profile-Guided Optimization, 실행 profile로 컴파일러 최적화를 유도하는 2-pass 빌드 기법)로 빌드할 수 있게 하는 PoC다. 상세 배경과 성능 실측은 CBRD-27335 이슈 본문에 있다.

- AS-IS: CUBRID 빌드 시스템에는 PGO를 켤 방법이 없어, PGO 실험마다 각자 컴파일러 flag를 수동으로 주입해야 한다. hot 함수 배치는 링크 순서의 우연에 좌우된다 (CBRD-26382에서 layout 변화가 성능을 움직인 인과가 확인됨).
- TO-BE: `cmake -DPGO=generate` -> 훈련 workload 실행 -> 같은 디렉터리에서 `cmake -DPGO=use`의 2-pass 절차로 표준화된 PGO 빌드를 만들 수 있다. 이 커밋 이전에 동일한 flag 조합으로 수행한 별도 PoC 빌드에서, 훈련 workload와 같은 질의 기준 median -8.94%의 질의 시간 개선이 측정됐다(조건과 한계는 이슈 본문 참고).

## Implementation

`CMakeLists.txt` 최상위에 cache 변수 2개와 flag 배선을 추가했다. 소스 코드 변경은 없다.

| 변수 | 의미 |
|------|------|
| `PGO` | `OFF`(기본) / `generate` / `use`. 기본값 `OFF`면 아무 flag도 추가하지 않아 기존 빌드에 영향이 없다. `generate`/`use`를 켰을 때만, GCC가 아니면 `FATAL_ERROR`로 막는다 |
| `PGO_PROFILE_DIR` | profile(.gcda) 디렉터리. 기본값 `${CMAKE_BINARY_DIR}/pgo-profile-data`. 두 phase에서 같은 값이어야 한다 |

- `PGO=generate`: `-fprofile-generate=<dir> -fprofile-update=atomic`을 C/C++ 컴파일과 링크 flag에 추가한다. `-fprofile-update=atomic`은 multi-thread 프로세스(cub_server)에서 카운터 경쟁으로 profile이 깨지는 것을 막는다.
- `PGO=use`: `-fprofile-use=<dir> -fprofile-correction -Wno-missing-profile -Wno-error=coverage-mismatch -Wno-error=stringop-overflow=`를 추가한다. `-fprofile-correction`은 남은 카운터 불일치를 보정하고, `-Wno-missing-profile`은 훈련에서 실행되지 않은 object의 경고를 끄며, `-Wno-error=coverage-mismatch`는 살짝 낡은 profile로 인한 에러를 경고로 강등한다(Release/RelWithDebInfo 빌드는 `CMakeLists.txt`에서 `-Werror`가 켜지므로 강등이 필요하다). `-Wno-error=stringop-overflow=`는 profile 기반 inlining이 `src/broker/cas_cgw_odbc.c`에서 새 경고를 만들기 때문이며, 해당 코드를 고칠 때까지의 임시 조치다.

사용 절차 (두 phase가 같은 build 디렉터리를 써야 한다 — GCC는 object 파일 절대경로를 mangle한 이름으로 `.gcda`를 찾는다):

```bash
# 1) instrument
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo \
      -DCMAKE_INSTALL_PREFIX=$HOME/CUBRID -DPGO=generate
cmake --build build --target install
# 2) train: 설치본으로 대표 workload 실행. 프로세스는 정상 종료해야 한다
#    (cubrid service stop 으로 server/broker 를 모두 내린다. kill -9 는 .gcda 를 유실한다)
# 2-1) 확인: profile 이 실제로 쌓였는지 반드시 검사. 0개여도 use 빌드는 조용히
#      성공하고 최적화 효과만 사라진다
find build/pgo-profile-data -name '*.gcda' | wc -l
# 3) optimize: 같은 build 디렉터리를 재구성
cmake -S . -B build -DPGO=use
cmake --build build --target install
```

## Remarks

- 검증: GCC 11.5 / Rocky Linux 9.6에서 `PGO=generate` full build가 성공했고, 이어 같은 디렉터리를 `PGO=use`로 전환한 full build도 성공했다. 단, 이 `use` 빌드는 훈련 단계를 생략해 profile(.gcda)이 없는 상태로 수행한 것이라 flag 배선과 빌드 통과 여부까지만 확인한 결과다(profile이 없으면 `-Wno-missing-profile` 때문에 경고 없이 성공한다). `build.ninja`에서 두 phase의 flag 주입을 확인했다. profile을 실제로 소비한 빌드와 성능 실측은 이 커밋 이전에 동일한 flag 조합으로 만든 별도 PoC 빌드에서 수행했고, 수치와 조건은 CBRD-27335 이슈 본문에 있다.
- 리뷰 포인트: flag를 `CMAKE_<LANG>_FLAGS`와 세 링커 flag 변수에 append하는 방식이 기존 Coverage/Profile build-type 블록과 어울리는지, `-Wno-error=stringop-overflow=`를 임시로 두는 것이 수용 가능한지.
- 한계와 주의:
  - GCC 전용이다(`PGO`를 켠 상태에서 Clang/MSVC면 `FATAL_ERROR`. 기본값 `OFF`에서는 기존 빌드에 영향이 없다). Windows 미지원. 3rdparty external project에는 flag가 전파되지 않는다(PoC와 동일 조건).
  - profile이 비어 있어도 `PGO=use` 빌드는 경고 없이 성공한다. 훈련 후 `.gcda` 개수를 직접 확인해야 한다.
  - `PGO=generate` 바이너리는 카운터 기록 때문에 크게 느리다(PoC 기준 대상 질의 약 6.6배). 벤치마크나 배포에 쓰면 안 되는 훈련 전용 빌드다.
  - 훈련을 반복하면 `.gcda` 카운터가 기존 값에 누적 병합된다. 새 workload로 다시 훈련하려면 `PGO_PROFILE_DIR`를 비우고 시작한다.
  - 비용: full rebuild 2회(PoC 기준 instrumented full rebuild 약 7분/80코어), profile 데이터 약 9MB.
- 후속(CBRD-27335에서 진행): 대표 훈련 workload 정의, `cas_cgw_odbc.c` 경고 근본 수정, `-fprofile-partial-training` 비교, CI/release 파이프라인 통합 방안.
