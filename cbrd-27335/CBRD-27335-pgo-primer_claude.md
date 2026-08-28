# CBRD-27335: PGO 입문 — 개념, 원리, 도입 사례

- 작성일: 2026-08-28
- 관련: [CBRD-27335 PGO build 도입](http://jira.cubrid.org/browse/CBRD-27335),
  [CUBRID PGO 실측 보고서](../cbrd-26382/CBRD-26382-pgo-experiment_95b79e7ed_claude.md),
  [PoC draft PR CUBRID/cubrid#7823](https://github.com/CUBRID/cubrid/pull/7823)
- 성격: 배경 지식 참고 자료. CUBRID 실측 수치와 도입 계획은 위 이슈/보고서가 원본이다.

## 1. PGO란 무엇인가

PGO(Profile-Guided Optimization)는 컴파일러 최적화의 입력을 **정적 추측에서 실행 실측으로
바꾸는** 기법이다. 보통의 AOT(ahead-of-time) 컴파일러는 프로그램이 실제로 어떻게 실행될지
모른 채, 소스 구조에서 유도한 heuristic만으로 최적화 결정을 내린다. PGO는 대표 workload를
실제로 실행해 얻은 branch/call 빈도 통계(profile)를 2차 컴파일에 공급해, 그 결정들을
실측 기반으로 바꾼다.

컴파일러 계열마다 이름과 옵션이 다르지만 개념은 같다: GCC `-fprofile-generate`/`-fprofile-use`,
Clang `-fprofile-instr-generate`/`-fprofile-use`, MSVC는 PGO(옛 이름 POGO,
[공식 문서](https://learn.microsoft.com/en-us/cpp/build/profile-guided-optimizations)).
FDO(Feedback-Directed Optimization)라고도 부른다.

## 2. 컴파일러는 무엇을 추측하고 있었나

profile이 없을 때 컴파일러가 heuristic으로 때우는 대표적인 결정들:

| 결정 | profile 없이 (추측) | profile 있으면 (실측) |
|------|--------------------|----------------------|
| branch 방향 | 정적 규칙(예: 에러 경로는 unlikely, backward branch는 taken)과 `__builtin_expect` 같은 수동 힌트 | edge별 실행 횟수. likely 방향을 fall-through로 배치 |
| inlining | 함수 크기·호출 구조 기반 예산 배분 | 실제로 뜨거운 call site에만 예산 집중 |
| 코드 배치 | 소스/링크 순서의 우연 | hot 함수끼리 인접 배치(`.text.hot`), cold 블록 분리(`.cold` clone, `.text.unlikely`) |
| 간접 호출 | 대상 미상 | 최빈 대상을 실측해 speculative devirtualization(간접 호출을 조건부 직접 호출로 승격) |
| loop 최적화 | trip count 미상 | 실측 반복 횟수로 unroll/vectorize 판단 |
| 실행 안 되는 코드 | 다른 코드와 동일하게 속도 최적화 | 크기 위주로 최적화해 hot working set 축소 |

CBRD-26382가 보여준 "layout 운" 문제는 셋째 줄의 추측이 만든 병리다. 무관한 소스 변화가
링크 순서를 흔들면 hot 함수의 캐시 배치가 우연히 좋아지거나 나빠진다. PGO는 그 배치를
실측 hotness로 고정한다.

## 3. 원리: instrumentation PGO의 동작

### 3.1 1차 컴파일 — 계측(instrument)

`-fprofile-generate`로 컴파일하면 컴파일러가 함수의 제어 흐름 그래프(CFG) edge에 카운터를
심는다. 모든 edge를 세지 않고, spanning tree를 제외한 최소 edge 집합만 계측해도 나머지
빈도가 산술적으로 복원되므로(고전적 arc-profiling 기법) 오버헤드를 줄인다. 단순 빈도 외에
value profiling(간접 호출의 최빈 대상, 자주 나오는 피연산자 값 등)도 수집한다.
multi-thread 프로세스에서는 카운터 경쟁으로 profile이 깨질 수 있어 GCC는
`-fprofile-update=atomic`을 제공한다.

### 3.2 훈련(train) — profile 기록

계측 바이너리로 대표 workload를 실행하면, 프로세스가 **정상 종료할 때** 카운터가 `.gcda`
파일로 덤프된다. 같은 object를 공유하는 여러 프로세스(CUBRID라면 cub_server, csql,
createdb 등)와 반복 실행은 파일 잠금 후 기존 카운터에 누적 병합된다. `kill -9`로 죽은
프로세스의 카운터는 사라진다.

### 3.3 2차 컴파일 — 소비(use)

`-fprofile-use`로 같은 소스를 다시 컴파일하면 2장의 표 오른쪽 열이 전부 실측으로 바뀐다.
GCC는 object 파일 절대경로를 mangle한 이름으로 `.gcda`를 찾기 때문에 1차와 2차가 같은
build 디렉터리를 써야 한다. 소스가 바뀌어 CFG가 달라지면 coverage mismatch로 해당 함수의
profile이 버려진다 — profile에는 수명이 있고, 갱신 주기가 필요하다.

### 3.4 왜 빨라지는가

효과는 두 성분으로 분해된다.

1. **일의 총량 감소**: hot call site 위주의 inlining이 호출 오버헤드와 명령 수 자체를 줄인다.
2. **micro-architecture 효율**: likely 방향 fall-through 배치가 branch misprediction을 줄이고,
   hot/cold 분리와 hot 함수 인접 배치가 I-cache·iTLB·µop cache의 locality를 높인다.

CUBRID GCC 11 실측([보고서](../cbrd-26382/CBRD-26382-pgo-experiment_95b79e7ed_claude.md))에서도
정확히 이 두 성분이 관측됐다: instructions -7.2%(성분 1), branch-misses -64%와
L1-icache miss -44%(성분 2), 합쳐서 질의 시간 median -8.9%.

### 3.5 비용과 한계

훈련 실행은 느리고(CUBRID 실측 약 6.6배), 빌드가 2회 필요하며, 훈련에 없는 경로는 cold로
취급돼 오히려 느려질 수 있다. 대표 workload 정의가 도입의 관건이다. 상세는
[CBRD-27335 이슈](http://jira.cubrid.org/browse/CBRD-27335)의 도입 비용/한계 절 참고.

## 4. PGO의 계보: 네 가지 방식

| 방식 | 수집 방법 | 대표 구현 | 특징 |
|------|-----------|-----------|------|
| instrumentation PGO | 카운터를 심은 훈련 빌드 | GCC/Clang `-fprofile-*`, [MSVC PGO](https://learn.microsoft.com/en-us/cpp/build/profile-guided-optimizations) | 정확한 빈도. 훈련 빌드·시간 필요 |
| sampling PGO | 하드웨어 PMU 샘플링(perf/LBR)으로 production 바이너리에서 수집 | [AutoFDO](https://docs.kernel.org/dev-tools/autofdo.html), [MSVC SPGO](https://devblogs.microsoft.com/cppblog/introducing-sample-profile-guided-optimization-in-msvc/) | 훈련 전용 빌드 불필요, 오버헤드 낮음. 정밀도는 낮음 |
| post-link 최적화 | 링크가 끝난 바이너리를 profile로 재배치 | [LLVM BOLT](https://github.com/llvm/llvm-project/tree/main/bolt), [Propeller](https://docs.kernel.org/dev-tools/propeller.html) | 컴파일러 최적화 위에 추가로 배치만 더 최적화 |
| runtime PGO (JIT) | 실행 중 profile을 모아 즉시 재컴파일 | Java HotSpot, V8, .NET Dynamic PGO | JIT 언어에는 이미 내장된 개념. AOT 세계의 PGO는 이것을 빌드 파이프라인으로 옮긴 것 |

## 5. 도입 사례 — system software

성숙한 시스템 소프트웨어들이 공식 빌드/문서 수준에서 PGO를 채택하고 있다.

| 소프트웨어 | 적용 | 공개된 내용 |
|-----------|------|------------|
| Google Chrome | 공식 release 빌드에 PGO 적용 (2016 Windows/MSVC부터, Chrome 85부터 Clang PGO로 Win/Mac) | [2016 블로그](https://blog.chromium.org/2016/10/making-chrome-on-windows-faster-with-pgo.html): 시작 16.8%, 페이지 로드 14.8% 개선. [2020 블로그](https://blog.chromium.org/2020/08/chrome-just-got-faster-with-profile.html), [빌드 문서](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/pgo.md) |
| Mozilla Firefox | 공식 release가 PGO 빌드 | [빌드 문서](https://firefox-source-docs.mozilla.org/build/buildsystem/pgo.html): 런타임 최대 ~20% 개선 |
| Linux kernel | Clang AutoFDO + Propeller 공식 지원 (6.13 병합). Google이 자사 데이터센터 커널에 적용해 온 sampling 방식 | [autofdo 문서](https://docs.kernel.org/dev-tools/autofdo.html), [propeller 문서](https://docs.kernel.org/dev-tools/propeller.html), [LWN](https://lwn.net/Articles/995397/) |
| CPython | `./configure --enable-optimizations`가 PGO를 켜는 공식 권장 구성(+LTO). 실험적 `--enable-bolt`도 제공 | [configure 문서](https://docs.python.org/3/using/configure.html) |
| Clang/LLVM | 자기 자신을 PGO로 빌드하는 공식 절차 제공 | [HowToBuildWithPGO](https://releases.llvm.org/19.1.0/docs/HowToBuildWithPGO.html): 컴파일 시간 ~20% 감소 보고 |
| GCC | 자기 자신을 profile feedback으로 빌드하는 표준 타깃 `make profiledbootstrap` | [GCC 빌드 문서](https://gcc.gnu.org/install/build.html) |
| rustc (Rust 컴파일러) | Linux/Windows 배포 빌드에 PGO 적용, 이후 BOLT까지 추가 | [inside-rust 블로그](https://blog.rust-lang.org/inside-rust/2020/11/11/exploring-pgo-for-the-rust-compiler/), [rust#80262](https://github.com/rust-lang/rust/pull/80262) |
| Go | 언어 차원에서 사용자 프로그램 PGO를 정식 지원(1.21~). `default.pgo`가 있으면 자동 적용 | [공식 가이드](https://go.dev/doc/pgo), [1.21 블로그](https://go.dev/blog/pgo): 대표 워크로드 약 2~7% 개선 |
| ClickHouse (DB) | 공식 문서에 PGO 빌드 가이드. 자사 clang 툴체인도 PGO+BOLT로 빌드 | [PGO 문서](https://clickhouse.com/docs/operations/optimizing-performance/profile-guided-optimization), [CI PR #96991](https://github.com/ClickHouse/ClickHouse/pull/96991) |
| Microsoft MsQuic (Windows QUIC 스택) | profile 파일을 리포지토리에 두고 release 빌드에 상시 적용 | [PGO 운영 문서](https://microsoft.github.io/msquic/msquicdocs/docs/PGO.html) |

그 외 다수 프로젝트의 PGO 적용 벤치마크를 모은 조사 저장소로
[awesome-pgo](https://github.com/zamazan4ik/awesome-pgo)가 있다(데이터베이스 사례 다수 포함).

## 6. CUBRID 관점의 시사점

1. **채택 패턴이 CUBRID와 같은 부류다.** 위 사례는 모두 "CPU-bound이고 대표 workload를
   정의할 수 있는" 시스템 소프트웨어다. DB 중에서는 ClickHouse가 공식 문서 수준으로
   채택했고, MSVC PGO의 고전적 대상도 서버 소프트웨어였다.
2. **운영 패턴도 수렴한다.** profile을 빌드 아티팩트로 버전 관리(MsQuic, Chrome),
   훈련 workload의 표준화(CPython의 `PROFILE_TASK`, Firefox의 profileserver), 성숙하면
   sampling 방식으로 이행(kernel AutoFDO, MSVC SPGO) — CBRD-27335의 단계 제안(재검증 ->
   훈련 suite -> sampling 대안)과 같은 궤적이다.
3. **JIT 세계에서는 이미 상식이다.** HotSpot/V8은 실행 중 profile로 재컴파일하는 runtime
   PGO를 내장한다. AOT로 배포되는 C/C++ 서버가 같은 이득을 얻는 경로가 빌드 타임 PGO다.

## 7. 관련 문서

- CUBRID 실측: [CBRD-26382-pgo-experiment_95b79e7ed_claude.md](../cbrd-26382/CBRD-26382-pgo-experiment_95b79e7ed_claude.md)
- 도입 이슈: [CBRD-27335](http://jira.cubrid.org/browse/CBRD-27335) · PoC PR: [CUBRID/cubrid#7823](https://github.com/CUBRID/cubrid/pull/7823)
- layout 민감성의 발단: [CBRD-26382 hot-function-alignment-options](../cbrd-26382/CBRD-26382-hot-function-alignment-options_codex.md)
- GCC 옵션 정의: [GCC Instrumentation Options](https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html)
- Clang PGO: [Clang User's Manual — Profile Guided Optimization](https://clang.llvm.org/docs/UsersManual.html#profile-guided-optimization)
