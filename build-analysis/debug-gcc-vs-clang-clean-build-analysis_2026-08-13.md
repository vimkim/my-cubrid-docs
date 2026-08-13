# CUBRID `debug_gcc`와 `debug_clang` 클린 빌드 성능 비교

- 작성일: 2026-08-13
- 대상 소스: CUBRID 11.5.x (`5990b81`, 빌드 버전 `11.5.0.2423-5990b81`)
- 목적: `debug_gcc`의 클린 빌드를 `debug_clang`에 가깝게 단축할 수 있는지 확인
- 변경 제약: 프로젝트 `CMakeLists.txt`나 소스는 수정하지 않고 `CMakeUserPresets.json` 또는 개인용 `justfile`만 변경

## 1. 결론 요약

두 빌드의 약 28초 차이는 링커가 아니라 GCC의 컴파일 단계에서 발생한다.

| 항목 | `debug_clang` | `debug_gcc` | `debug_gcc_fast` |
|---|---:|---:|---:|
| Ninja 로그 기준 전체 시간 | 50.927초 | 78.828초 | 77.270초 |
| 오브젝트 컴파일 누적 작업 시간 | 875.6초 | 1,620.6초 | 1,578.8초 |
| 전체 오브젝트 엣지 | 1,192개 | 1,192개 | 1,192개 |
| 마지막 오브젝트 완료 시점 | 48.718초 | 77.084초 | - |
| 마지막 오브젝트 이후 종료까지 | 2.209초 | 1.744초 | - |

핵심 판단은 다음과 같다.

1. 두 빌드는 같은 수의 오브젝트를 생성하므로 GCC만 더 많은 대상을 빌드하는 문제가 아니다.
2. 대응되는 오브젝트 1,191개 중 1,107개, 즉 92.9%에서 GCC가 더 느렸다.
3. 오브젝트 컴파일 누적 시간은 GCC가 Clang의 약 1.85배였다.
4. 반대로 실행 파일과 공유 라이브러리 링크 작업의 누적 시간은 GCC가 더 짧았다.
5. GCC LTO는 일부 파일의 컴파일을 빠르게 했지만 전체 빌드는 80.888초로 더 느렸고 ODR/type mismatch 경고도 발생했다.
6. 전역 Unity Build는 생성된 lexer/parser 및 명시적 템플릿 특수화 충돌로 컴파일되지 않았다.
7. 전체 디버그 정보 수준을 유지하면서 preset만으로 안전하게 적용할 수 있었던 개선은 `-pipe`였고, 전체 시간은 78.828초에서 77.270초로 약 2.0% 단축되었다.

따라서 현재 제약 안에서는 `debug_gcc_fast`에 `-pipe`만 유지하는 것이 타당하다. GCC 빌드를 Clang의 약 51초 수준까지 줄이려면 선택적 PCH 또는 소스별 제외 규칙을 둔 Unity Build처럼 프로젝트 CMake 타깃을 수정하는 작업이 필요하다.

## 2. 측정 환경과 방법

### 2.1 환경

| 항목 | 값 |
|---|---|
| CPU | Intel Core Ultra 7 270K Plus, 24 physical cores / 24 logical CPUs |
| 메모리 | 14 GiB RAM, 8 GiB swap |
| 병렬도 | `MAKEFLAGS=-j24`; Ninja 로그에서 동시 오브젝트 작업 최대 26개 관찰 |
| GCC | 16.1.1 (Fedora) |
| Clang | 22.1.8 |
| Linker | GNU ld 2.46 |
| Ninja | 1.13.2 |
| CMake | 3.31.12 |
| ccache | 4.13.6 |

### 2.2 클린 빌드 조건

각 최종 비교는 다음 조건으로 수행했다.

1. 해당 build directory 삭제
2. preset으로 다시 configure
3. ccache를 clear하고 통계를 0으로 초기화
4. 동일한 병렬도로 전체 빌드
5. `.ninja_log`, `compile_commands.json`, 개별 컴파일 재실행 결과를 분석

최종 `debug_gcc_fast` 빌드의 ccache 통계는 cacheable call 1,190개 중 hit 42개, miss 1,148개였다. 빌드 시작 시 캐시는 비어 있었지만 같은 소스가 여러 타깃과 모드에서 반복 컴파일되므로 한 빌드 안에서 먼저 생성된 결과가 뒤의 동일한 컴파일에 사용될 수 있다. 기준 빌드에도 20ms 이하 오브젝트 엣지가 37개 있었으므로 비교 조건에 중대한 차이는 없는 것으로 판단했다.

> 이 문서에서 `just` 명령은 이 로컬 작업공간의 개인 편의 도구를 뜻한다. CUBRID 프로젝트의 공식 빌드 또는 검증 절차를 의미하지 않는다.

## 3. 기준 빌드 비교

### 3.1 Ninja 단계별 시간

아래 누적 시간은 각 작업의 duration을 더한 값이므로 병렬 빌드의 wall-clock 시간보다 크다. 어느 단계가 CPU 시간을 소비했는지 비교하는 용도이다.

| 단계 | Clang 누적 작업 시간 | GCC 누적 작업 시간 | 해석 |
|---|---:|---:|---|
| 오브젝트 컴파일 | 875.6초 | 1,620.6초 | GCC가 745.0초 더 큼 |
| 정적 라이브러리 생성 | 46.7초 | 42.0초 | GCC가 약간 빠름 |
| 공유 라이브러리 링크 | 18.1초 | 13.8초 | GCC가 빠름 |
| 실행 파일 링크 | 17.0초 | 10.4초 | GCC가 빠름 |
| 외부 프로젝트/stamp | 118.1초 | 113.3초 | 유사 |
| 기타 | 22.6초 | 16.3초 | GCC가 빠름 |

GCC의 추가 컴파일 작업 시간 745초를 실제 동시 오브젝트 작업 수 26으로 나누면 약 28.7초이다. 이는 실제 wall-clock 차이인 27.9초와 거의 일치한다.

즉 다음 관계가 성립한다.

```text
GCC의 추가 컴파일 비용 약 745 job-seconds
                 ÷ 동시 작업 약 26개
                 ≈ wall-clock 약 28.7초
```

빌드 종료 직전도 같은 결론을 뒷받침한다. Clang은 마지막 오브젝트가 48.718초에 완료되고 전체 빌드는 50.927초에 끝났다. GCC는 마지막 오브젝트가 77.084초에 완료되고 78.828초에 끝났다. 링크 이후 시간이 늘어난 것이 아니라 컴파일 완료 시점 자체가 늦다.

### 3.2 오브젝트 컴파일 분포

| 지표 | Clang | GCC |
|---|---:|---:|
| median (`p50`) | 720ms | 1,409ms |
| `p90` | 1,383ms | 2,647ms |
| `p95` | 1,625ms | 3,165ms |
| `p99` | 2,170ms | 4,067ms |
| 최댓값 | 2,538ms | 5,449ms |

GCC는 일부 대형 파일만 느린 것이 아니다. 대응되는 1,191개 오브젝트의 누적 시간은 GCC 1,620.5초, Clang 875.5초였고 GCC가 1.85배였다. 92.9%의 오브젝트에서 GCC가 느렸으므로 병목은 소수의 예외적인 파일이 아니라 전반적인 front-end 및 debug code generation 비용이다.

## 4. 링커와 LTO가 주원인이 아닌 이유

### 4.1 링커

두 preset 모두 기본적으로 GNU `ld.bfd`를 사용한다. Clang은 LLD를 사용하지 않으며, GNU linker에 LLVMgold plugin을 연결해 ThinLTO를 수행한다.

공유 라이브러리와 실행 파일 링크 작업을 합친 누적 시간은 다음과 같다.

| 컴파일러 | 공유 라이브러리 + 실행 파일 링크 누적 시간 |
|---|---:|
| Clang | 약 35.1초 |
| GCC | 약 24.2초 |

링크는 오히려 GCC가 약 10.9 job-seconds 빠르다. 따라서 GCC의 전체 빌드가 느린 이유를 linker에서 찾을 수 없다.

### 4.2 Clang ThinLTO

`debug_clang`에는 전역 `-flto=thin`이 설정되어 있지만 `debug_gcc`에는 LTO가 없다. 처음에는 이 차이가 Clang의 속도 우위 원인일 가능성을 검토했다.

대표 파일에서 ccache 없이 정확한 compile command를 반복 실행한 결과는 다음과 같다.

| 오브젝트 | GCC | Clang | Clang에서 ThinLTO 제거 |
|---|---:|---:|---:|
| `object_representation_sr.c.o` | 1.16~1.18초 | 0.59초 | 0.61초 |
| `histogram_sampler_sr.cpp.o` | 2.00~2.01초 | 0.90초 | 0.97초 |
| `query_executor.c.o` | 1.66~1.69초 | 0.83초 | 0.85초 |

ThinLTO를 제거해도 Clang은 GCC보다 약 1.8배 빨랐다. `-fdelayed-template-parsing` 제거 비용도 약 4~8% 수준이었다. 따라서 Clang 전용 플래그가 일부 영향을 주지만 전체 차이를 설명하지는 못한다.

## 5. 컴파일러별 플래그와 메모리 특성

### 5.1 주요 플래그

`debug_clang`의 주요 플래그:

```text
-O0 -ggdb3 -fdebug-macro -fno-inline
-flto=thin -fdelayed-template-parsing
-fno-omit-frame-pointer
-Xclang -fno-validate-pch -Xclang -fno-pch-timestamp
```

`debug_gcc`의 주요 플래그:

```text
-O0 -ggdb3 -fno-omit-frame-pointer
```

GCC command line에는 타깃별 설정과 상속으로 `-ggdb3`, `-Wall`, `-fno-inline` 등이 일부 중복되어 있었다. 중복 플래그를 제거한 개별 실험에서는 유의미한 시간 차이가 없었다. 문자열 길이나 옵션 중복 파싱이 병목은 아니다.

### 5.2 프로세스 메모리와 생성물 크기

대표 컴파일의 peak RSS도 GCC가 더 컸다.

| 오브젝트 | GCC peak RSS | Clang peak RSS |
|---|---:|---:|
| `object_representation_sr.c.o` | 약 416 MiB | 약 217 MiB |
| `histogram_sampler_sr.cpp.o` | 약 516~517 MiB | 약 278 MiB |
| `query_executor.c.o` | 약 496 MiB | 약 270 MiB |

프로젝트 타깃에서 생성된 오브젝트의 합계도 GCC가 약 1,278.1 MiB, Clang이 약 1,019.9 MiB였다. 24개 이상의 컴파일이 동시에 실행되면 GCC 프로세스의 높은 메모리 사용량과 더 큰 debug object 생성 비용이 메모리 대역폭 및 파일 I/O 압력을 높일 수 있다.

다만 병렬도를 낮추는 것은 이 시스템에서 해결책이 아니었다. GCC 컴파일 48개를 실행한 소규모 throughput 실험은 다음과 같았다.

| 병렬도 | 시간 |
|---:|---:|
| 8 | 4.551초 |
| 12 | 3.591초 |
| 16 | 3.241초 |
| 20 | 3.071초 |
| 24 | 2.750초 |

현재 장비에서는 `-j24`가 가장 빨랐다.

## 6. GCC 최적화 실험

### 6.1 디버그 정보 및 GCC 옵션

| 실험 | 결과 | 채택 여부 |
|---|---|---|
| 중복 플래그 제거 | 유의미한 차이 없음 | 제외 |
| `-g2` | 약 2~5% 개선 | `-ggdb3` 대비 디버그 정보 감소 가능성으로 제외 |
| `-g1` | 약 13~18% 개선 | 변수/로컬 디버깅 정보 손실로 제외 |
| `-g0` | `-g1`과 비슷한 수준 | debug preset 목적에 맞지 않아 제외 |
| `-gsplit-dwarf` | 개선 없음 또는 소폭 느림 | 제외 |
| `-fno-var-tracking*` | 효과 없음 | GCC가 `-O0`에서 이미 관련 작업을 제한하므로 제외 |
| `-femit-struct-debug-reduced` | 효과 미미 | 제외 |
| `-pipe` | 전체 빌드 약 2.0% 개선 | 채택 |

`-g1`은 더 큰 효과가 있었지만, 소스 수준 디버깅 품질을 낮추므로 “동일한 debug 빌드”라는 목표와 충돌한다. 속도가 최우선인 별도 preset에는 고려할 수 있지만 `debug_gcc`의 동등한 대체재로 보기는 어렵다.

### 6.2 `-pipe`의 의미

GCC의 일반적인 컴파일 과정은 전처리, 컴파일, 어셈블 단계를 거친다. 기본 동작은 단계 사이의 중간 결과를 임시 파일에 기록할 수 있다. `-pipe`는 가능한 경우 이 중간 결과를 디스크 임시 파일 대신 운영체제 pipe를 통해 다음 프로세스로 직접 전달한다.

```text
기본:  cc1plus -> 임시 assembly 파일 -> assembler
-pipe: cc1plus -> OS pipe             -> assembler
```

`-pipe`는 최적화 수준, 생성 코드의 의미, 디버그 정보 수준을 바꾸지 않는다. 중간 파일 I/O만 줄이므로 비교적 안전한 로컬 빌드 속도 옵션이다. 효과는 저장장치, 메모리 압력, 파일 크기에 따라 달라지며 이 측정에서는 wall-clock 기준 1.558초, 약 2.0%였다.

### 6.3 GCC LTO

대표 파일에서는 `-flto=auto`가 컴파일 시간을 약 10~25% 단축했다.

| 오브젝트 | GCC 기준 | GCC `-flto=auto` |
|---|---:|---:|
| `object_representation_sr.c.o` | 1.18초 | 1.05초 |
| `histogram_sampler_sr.cpp.o` | 2.01초 | 1.50초 |
| `query_executor.c.o` | 1.66초 | 1.38초 |

하지만 첫 전체 빌드는 `cubrid-cci/cci/libcascci.so.11.2` 링크에서 다음 오류로 실패했다.

```text
R_X86_64_PC32 against symbol cci_free cannot be used when making a shared object;
recompile with -fPIC
```

컴파일 command 끝에는 이미 `-fPIC`가 있었지만, GCC LTO의 link-time code generation에도 PIC를 명시하도록 preset의 shared/module linker flags에 `-fPIC`를 추가해야 했다. 이 우회 후 전체 빌드는 성공했으나 80.888초로 기준 GCC 78.828초보다 느렸다.

또한 LTO 빌드에서 다음 경고가 발생했다.

- `struct find_id_info`의 ODR 위반 (`cnf.c`와 `view_transform.c`)
- `this_parser`, `parent_parser`의 type mismatch
- 엄격한 aliasing 관련 잠재적 misoptimization 경고

따라서 GCC LTO는 전체 빌드 속도 목표를 달성하지 못했고, 기존 비-LTO debug 빌드에는 노출되지 않던 정확성 위험까지 드러냈으므로 채택하지 않았다.

### 6.4 Unity Build

`CMAKE_UNITY_BUILD=ON`과 `CMAKE_UNITY_BUILD_BATCH_SIZE=2`를 preset에 설정하면 Ninja edge 수는 1,355개에서 783개로 크게 줄었다. 그러나 약 127/783 지점에서 컴파일이 실패했다.

주요 충돌은 다음과 같다.

1. 생성된 `load_grammar.cpp`와 `load_lexer.cpp`가 같은 unity translation unit에 합쳐지면서 `yyFlexLexer` 재정의와 `yylex` macro 충돌 발생
2. histogram 소스가 합쳐지면서 `HistogramReader::bucket_hi<std::string_view>`와 `mcv_hi`에서 instantiation 이후 explicit specialization 오류 발생

Unity Build를 안전하게 적용하려면 문제가 되는 생성 소스와 일부 C++ 소스에 `SKIP_UNITY_BUILD_INCLUSION` 속성을 지정해야 한다. 이는 `CMakeUserPresets.json`이나 `justfile`만으로는 표현할 수 없고 프로젝트 `CMakeLists.txt` 변경이 필요하다. 따라서 실패한 unity preset과 build directory는 제거했다.

## 7. PCH 가능성

PCH(Precompiled Header)는 여러 translation unit이 반복해서 파싱하는 공통 헤더를 한 번 미리 컴파일해 재사용하는 방식이다.

CUBRID 빌드는 같은 소스를 `SERVER_MODE`, `SA_MODE`, `CS_MODE` 등 서로 다른 전처리 정의로 반복 컴파일한다. 실제로 149개 소스가 세 번 이상 컴파일되며, 큰 세 타깃이 전체 compile command의 대부분을 차지한다.

| 타깃 | compile command 수 |
|---|---:|
| `cubridsa` | 362 |
| `cubrid` | 299 |
| `cubridcs` | 262 |
| 합계 | 923 / 1,190 |

따라서 공통 헤더 파싱을 줄이는 PCH는 다음 단계의 유력한 최적화 후보이다. 다만 각 mode의 macro 상태가 다르므로 하나의 PCH를 무분별하게 공유하면 안 된다. `target_precompile_headers()`를 mode별 타깃에 적용하고 PCH가 해당 타깃과 동일한 compile definitions/options로 생성되도록 해야 한다.

PCH는 타깃의 CMake 정의가 필요하므로 이번 “preset 또는 justfile만 변경” 제약에서는 구현할 수 없다.

## 8. 최종 유지 설정

기존 `debug_gcc`는 비교 및 호환성을 위해 변경하지 않고, 이를 상속하는 `debug_gcc_fast`를 `CMakeUserPresets.json`에 추가했다.

```json
{
  "name": "debug_gcc_fast",
  "inherits": "debug_gcc",
  "cacheVariables": {
    "CMAKE_C_FLAGS": "-fdiagnostics-color=always -pipe",
    "CMAKE_CXX_FLAGS": "-fdiagnostics-color=always -Wno-template-body -isystem ${sourceDir}/.just/include -pipe"
  }
}
```

동일한 이름의 build preset도 추가했다. 기존 개인용 `justfile`은 임의의 preset 이름을 받을 수 있으므로 수정할 필요가 없었다. 로컬 `.env`에서는 다음을 선택했다.

```dotenv
PRESET_MODE=debug_gcc_fast
```

표준 CMake 명령으로는 다음과 같이 사용할 수 있다.

```bash
cmake --preset debug_gcc_fast
cmake --build --preset debug_gcc_fast
```

로컬 개인 편의 명령을 사용하는 경우에는 기존 generic preset/build recipe가 `debug_gcc_fast`를 그대로 처리한다.

## 9. 최종 검증

최종 preset은 build directory를 삭제하고 ccache를 비운 상태에서 다시 configure/build하여 검증했다.

| 항목 | 결과 |
|---|---|
| 전체 빌드 | 성공 |
| 기준 `debug_gcc` | 78.828초 |
| 최종 `debug_gcc_fast` | 77.270초 |
| 단축 | 1.558초, 약 2.0% |
| 오브젝트 누적 작업 시간 | 1,620.6초 → 1,578.8초, 약 2.6% 감소 |
| `cubrid_rel` 실행 | 성공, 64-bit debug build 확인 |
| `ldd bin/cub_server` | `not found` 없음 |
| `ctest --test-dir build_preset_debug_gcc_fast` | 테스트가 구성되지 않아 `No tests were found` |

`ctest`에서 실행된 테스트가 없었으므로 “테스트 통과”로 해석해서는 안 된다. 이 검증은 빌드 성공, 실행 파일 버전 확인, 동적 라이브러리 해석 확인까지의 smoke check이다.

## 10. 최종 판단과 다음 단계

현재 장비와 소스에서 GCC와 Clang의 일반적인 벤치마크 성능이 비슷하다는 사실은 이 빌드의 결과와 모순되지 않는다. 컴파일러 성능은 코드베이스의 헤더 구조, template 사용, debug information 생성량, translation unit 크기, compiler version 및 플래그 조합에 크게 의존한다. CUBRID의 이 debug 구성에서는 GCC 16이 `-O0 -ggdb3` C++ compilation에 더 많은 CPU 시간과 메모리를 사용했다.

제약별 권장안은 다음과 같다.

1. **preset/justfile만 변경하고 전체 디버그 정보를 유지:** 현재의 `debug_gcc_fast`와 `-pipe`를 사용한다. 기대 개선은 약 2%이다.
2. **일부 디버그 정보 손실 허용:** 별도의 `-g1` preset을 만들어 추가로 약 13~18%의 compile-time 개선을 검토할 수 있다. 그래도 Clang의 50.927초에 도달할 가능성은 낮다.
3. **프로젝트 CMake 변경 허용:** `cubrid`, `cubridsa`, `cubridcs`에 mode별 PCH를 적용하고 성능 및 정확성을 측정한다.
4. **더 공격적인 프로젝트 CMake 변경 허용:** Unity Build를 타깃별로 적용하되 generated lexer/parser와 specialization 충돌 소스를 명시적으로 제외한다.
5. **GCC LTO:** 현재 상태에서는 전체 시간이 더 느리고 진단된 ODR/type 위험이 있으므로 빌드 가속 목적으로 사용하지 않는다.

요약하면, preset만으로 Clang과 같은 속도를 만드는 숨은 linker 또는 LTO switch는 발견되지 않았다. 안전하고 의미 보존적인 preset-only 개선은 `-pipe`이며, 남은 약 26초의 차이를 줄일 현실적인 경로는 타깃별 PCH나 선택적 Unity Build이다.
