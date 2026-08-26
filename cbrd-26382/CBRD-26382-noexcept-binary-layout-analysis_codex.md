# CBRD-26382 `scope_exit` `noexcept` 바이너리 배치 분석

- 작성일: 2026-08-26
- 대상: CUBRID PR [#6636](https://github.com/CUBRID/cubrid/pull/6636), merge commit [`8fd3ca03e`](https://github.com/CUBRID/cubrid/commit/8fd3ca03e58b342a494a2f5594be23c72a822479)
- 상태: **6개 최소 바이너리 실험 및 cache-layout 측정 완료**
- 비교 축: Rocky Linux 8 / GCC 8, Rocky Linux 9 / GCC 11 × original / refactored-conditional / refactored-forced

## Executive summary

6개 최소 바이너리와 고정 CPU 반복 측정에서 내린 결론은 다음과 같다.

1. `~scope_exit() noexcept`와
   `~scope_exit() noexcept(noexcept(f_()))`는 저장된 callable이 명시적으로 non-throwing이 아닐 때 서로 다른
   예외 계약이다. 전자는 예외가 함수 밖으로 나가면 `std::terminate`를 호출하고, 후자는 예외 전파를 허용할 수 있다.
   따라서 GCC가 서로 다른 machine code와 EH metadata를 만드는 것은 정상적인 최적화 결과일 수 있다.
2. refactor는 representative guard의 크기를 40 byte에서 16 byte로 줄이고 `std::function` 경로를 제거했다.
   `released_work`는 GCC 8에서 78→5 byte, GCC 11에서 95→5 byte가 됐다. refactor 자체의 normal-path codegen은
   악화가 아니라 명확한 개선이다.
3. conditional→forced에서 `guarded_work`, `released_work`, `hot_count`의 실제 명령열은 각 compiler 안에서
   동일했다. 달라진 것은 forced가 요구한 terminate용 EH metadata와 그것이 만든 link layout이었다.
4. GCC 8에서는 이 layout perturbation이 `.text` 시작 이후의 함수들을 112 byte 이동시켜 `hot_count`의 64-byte
   cache-line offset을 16→0으로 바꿨다. 2억 iteration, CPU 0 고정, 50회 평균에서 instruction 수는 같지만
   forced가 conditional보다 cycle이 **9.61% 적었다**. 반대로 GCC 11에서는 두 refactored 함수 주소가 같았고
   cycle 차이는 **0.16%**뿐이었다. 즉 GCC 8 전용 code-placement sensitivity는 최소 프로브에서 실제 관찰됐다.
5. 그러나 실제 PR 비교인 original→conditional은 GCC 8 프로브에서 `hot_count` offset이 둘 다 16이었고 cycle도
   0.04% 차이에 불과했다. 따라서 이 실험은 QA의 10.56% SQL 지연을 재현하거나 PR #6636의 책임을 입증하지 않는다.
   forced `noexcept`가 빨라진 것은 semantic optimization이라기보다 이 작은 ELF에서 우연히 유리해진 배치다.
6. `log_Gl`의 type/field/definition은 PR에서 바뀌지 않았다. conditional `noexcept`도 runtime field를 추가하지 않는다.
   최소 ELF에서는 forced가 `DW.ref.__gxx_personality_v0` 8 byte를 `.data`에 추가해 뒤의 작은 global을 8 byte
   밀었지만, 이는 `log_Gl` 크기 증가가 아니다. CUBRID 전체 바이너리의 `log_Gl` cache-line 가설은 우선순위가 낮다.

QA가 제공한 5회 평균은 17.583641초에서 19.4410452초로 1.8574042초, 약 **10.56%** 증가한 값이다. 이 수치는
비교 대상 빌드 전체의 관측값이지, PR #6636의 단독 효과를 분리한 값은 아니다.

## 1. 비교할 세 구현의 정확한 의미

PR #6636은 기존 `std::function<void(void)>` type erasure를 concrete callable member로 교체하고, 생성자·move
생성자·소멸자의 `noexcept`를 type trait 또는 `noexcept` expression에 따라 조건부로 바꿨다. 실제 merge diff에서
소멸자는 다음과 같이 바뀌었다.

```cpp
// original
~scope_exit() noexcept;

// refactored-conditional
~scope_exit() noexcept (noexcept (std::declval<fun_t &>()()));

// refactored-forced: 실험 patch의 정확한 범위를 반드시 기록
~scope_exit() noexcept;
```

6개 결과를 합칠 때 아래 provenance를 확정한다.

| variant | 기준 source/patch | 생성자 | move 생성자 | 소멸자 | 비고 |
|---|---|---|---|---|---|
| original | `8fd3ca03e^` 또는 최소 재현의 old class | `noexcept` | `noexcept` | `noexcept` | `std::function` 보유 |
| refactored-conditional | merge commit 구현 | conditional | conditional | conditional | concrete callable 보유 |
| refactored-forced | probe `PROBE_VARIANT=3` | `noexcept` | `noexcept` | `noexcept` | 세 specification을 모두 강제 |

probe의 `cleanup_functor`는 trivially movable이어서 constructor/move의 conditional 식은 이미 true다. 반면
`operator()`는 명시적 `noexcept`가 없고 별도 C translation unit의 함수를 호출하므로 destructor의 conditional 식만
false다. 따라서 소스상 forced variant는 세 곳을 모두 강제하지만, 이 실험에서 conditional→forced의 실질적인
exception-contract 차이는 destructor 하나다.

## 2. C++ 언어 의미

표준 초안 `[except.spec]`에 따르면 `noexcept`는 `noexcept(true)`와 같고, 조건식이 false이면 potentially-throwing,
true이면 non-throwing exception specification이다. `noexcept(expression)` 연산자는 operand를 실행하지 않고 해당
full-expression이 potentially-throwing인지 평가한다. 명시적 `noexcept`가 없는 일반 함수 호출은 원칙적으로
potentially-throwing이므로, 일반적인 unannotated lambda의 `operator()`를 담으면 conditional 소멸자는
`noexcept(false)`가 될 수 있다. [C++ draft: exception specifications](https://eel.is/c++draft/except.spec),
[C++ draft: `noexcept` operator](https://eel.is/c++draft/expr.unary.noexcept)

non-throwing 함수의 body 밖으로 예외가 전파되면 `std::terminate`가 호출된다. 반대로 conditional 식이 false인
소멸자는 정상 scope exit 중 발생한 예외를 caller 쪽으로 전파할 수 있다. 단, 이미 stack unwinding 중인 객체의
소멸에서 다시 예외가 나오면 별도 규칙으로 `std::terminate`가 호출된다.
[C++ draft: exception handling](https://eel.is/c++draft/except.handle),
[C++ draft: `std::terminate`](https://eel.is/c++draft/except.terminate)

따라서 forced와 conditional-false는 단순한 optimization hint 차이가 아니다. 실험은 callback을 최소한 아래 둘로
나누어야 한다.

```cpp
[] () noexcept { cleanup(); } // conditional == forced
[] ()          { cleanup(); } // 선언상 conditional은 보통 potentially-throwing
```

두 callable을 섞으면 `noexcept` 의미 차이와 compiler의 callable 분석 능력 차이가 동시에 측정된다.

## 3. GCC가 `noexcept`에서 얻을 수 있는 정보

GCC 8.5와 11.5 문서는 exception specification을 바탕으로 compiler가 최적화한다고 명시한다.
`-fnothrow-opt` 설명은 non-throwing 명세가 text size overhead를 줄이고 non-trivial local destructor의 EH cleanup을
제거할 수 있다고 설명한다. `-fexceptions`는 예외 전파를 위한 추가 code를 생성하며, target에 따라 unwind 정보가
상당한 data-size overhead를 낼 수 있다고 설명한다.

- [GCC 8.5 C++ dialect options](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/C_002b_002b-Dialect-Options.html):
  `-fno-enforce-eh-specs`, `-fnothrow-opt`, `-Wnoexcept`, `-Wnoexcept-type`
- [GCC 11.5 C++ dialect options](https://gcc.gnu.org/onlinedocs/gcc-11.5.0/gcc/C_002b_002b-Dialect-Options.html):
  동일 항목
- [GCC 8.5 code-generation options](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Code-Gen-Options.html):
  `-fexceptions`, `-funwind-tables`, `-fasynchronous-unwind-tables`
- [GCC 11.5 code-generation options](https://gcc.gnu.org/onlinedocs/gcc-11.5.0/gcc/Code-Gen-Options.html):
  동일 항목

따라서 conditional/forced 차이가 다음 중 일부를 바꾸는 것은 원칙상 가능하지만, 모든 호출 지점에서 반드시
바뀐다는 뜻은 아니다.

- normal path의 instruction 수와 branch 배치
- throw 시 landing pad 또는 terminate 경로
- caller가 보유한 cleanup edge
- `.gcc_except_table`의 LSDA/call-site 정보
- `.eh_frame` FDE의 PC range와 간접적인 byte 변화
- inline 및 hot/cold basic-block 결정
- 그 결과 뒤따르는 함수와 read-only section의 주소/정렬

Itanium C++ ABI의 EH 모델은 personality routine, search/cleanup의 두 단계 unwind, landing pad 및
language-specific data를 사용한다. 이것이 Linux/x86-64 GNU toolchain에서 관찰할 EH 구조를 해석하는 기준이다.
[Itanium C++ ABI: Exception Handling](https://itanium-cxx-abi.github.io/cxx-abi/abi-eh.html)

Itanium EH working draft는 LSDA의 call-site table과 action record 구조를 설명한다. 이는 `.gcc_except_table`을
해석할 때 유용한 설계 근거이지만, 실제 GCC/x86-64 encoding과 section 존재 여부는 생성된 ELF에서 확인해야 한다.
[Itanium C++ ABI EH working draft, section 7.3](https://itanium-cxx-abi.github.io/cxx-abi/exceptions.pdf)

C++17 function type에 들어간 non-throwing specification은 Itanium ABI에서 `Do`로 encode될 수 있다. 그러나
scope-exit 소멸자의 top-level symbol 이름이 `noexcept` 하나만으로 반드시 달라진다고 단정하면 안 된다. 해당
encoding은 함수 타입이 template argument, 함수 포인터 등 nested type으로 나타날 때 특히 직접적이다.
[Itanium C++ ABI: function types](https://itanium-cxx-abi.github.io/cxx-abi/abi.html#mangle.function-type)

## 4. GCC 8과 GCC 11 비교 시 주의점

같은 `-O2` 문자열은 같은 pass 집합 또는 heuristic을 의미하지 않는다.

| 항목 | GCC 8.5 | GCC 11.5 | 해석 |
|---|---|---|---|
| `-O2`의 `-finline-functions` | 목록에 없음 | 포함 | refactored concrete callable의 inline 결과가 달라질 수 있음 |
| `-fipa-modref` | 없음 | `-O` 계열에 포함 | call side-effect 분석 정밀도가 다름 |
| hot/cold 및 inliner 변화 | 기준 | GCC 9/10에서 tuning 변경 | layout perturbation이 같은 방향일 필요 없음 |
| `-freorder-blocks(-and-partition)` | 존재 | 존재 | EH/unwind 유무가 partition 가능성에 관여할 수 있음 |

근거:

- [GCC 8.5 optimize options](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Optimize-Options.html)
- [GCC 11.5 optimize options](https://gcc.gnu.org/onlinedocs/gcc-11.5.0/gcc/Optimize-Options.html)
- [GCC 9 release notes](https://gcc.gnu.org/gcc-9/changes.html): modern C++ inliner tuning, hot/cold partitioning 개선
- [GCC 10 release notes](https://gcc.gnu.org/gcc-10/changes.html): `-finline-functions`의 `-O2` 활성화와 retuning
- [GCC 11 release notes](https://gcc.gnu.org/gcc-11/changes.html): IPA modref 및 ICF 개선

따라서 GCC 8에서만 관측되는 결과는 다음과 같이 표현하는 편이 정확하다.

> 동일한 source-level exception contract 차이가 GCC 8과 GCC 11의 서로 다른 inliner·IPA·hot/cold 배치
> 결정에 의해 서로 다른 최종 layout perturbation으로 증폭될 수 있다. GCC 8에서만 나타난다는 사실은 GCC 8
> code generation을 조사할 이유가 되지만 compiler bug의 증명은 아니다.

또한 Rocky 8과 Rocky 9 container 비교에는 GCC뿐 아니라 binutils, linker, libstdc++, glibc 차이도 들어간다.
compiler 세대 효과를 분리하려면 **각 compiler 내부의 세 variant 비교를 먼저** 하고 GCC 8 대 GCC 11은 두 번째
비교 축으로 다뤄야 한다.

## 5. 6개 최소 바이너리 실험 결과

### 5.1 환경과 재현성

| 항목 | Rocky 8 / GCC 8 | Rocky 9 / GCC 11 |
|---|---|---|
| 실행 환경 | Podman `rockylinux:8` | 현재 host, Rocky Linux 9.6 |
| image digest | `sha256:f5529992e67440c1a4ae7788244d4381c6909159a88eacd95b7523ae47ced82e` | 해당 없음(host) |
| `gcc/g++` | 8.5.0-28.el8_10 | 11.5.0-5.el9_5 |
| 실제 linker | GNU ld 2.30-128.el8_10 | `/usr/bin` GNU ld 2.35.2-63.el9 |
| target | ELF64 x86-64, GNU/Linux | ELF64 x86-64, GNU/Linux |
| compile flags | `-std=c++17 -O2 -DNDEBUG -finline-functions -ggdb -fno-omit-frame-pointer -fPIE -fno-ident`, no LTO | 왼쪽과 동일 |
| 재현성 flags | 동일 source path, `-ffile-prefix-map`, 고정 `-frandom-seed`; PIE와 GNU build-id는 유지 | 왼쪽과 동일 |
| 비교 artifact | debug 포함 ELF와 `strip --strip-debug` ELF, map/readelf/size/nm/objdump/section dump | 왼쪽과 동일 |

Rocky 9 host의 기본 `PATH`에는 Linuxbrew linker가 먼저 있었으므로 사용하지 않았다. 시스템 GCC 11과 binutils를
짝지으려고 `PATH=/usr/bin:/bin`으로 다시 빌드했다. CUBRID release flag에 GCC 버전과 무관하게
`-finline-functions`가 명시되어 있으므로 probe도 이를 그대로 사용했다.

소스와 실행 명령은 [`artifacts/noexcept-binary-layout/`](artifacts/noexcept-binary-layout/)에 있다.

- probe source SHA-256: `9a31a0719268efb405fc848fc761299a0779ae464543cbc109e8b838e473e944`
- common C cleanup source SHA-256: `5c9a824609d073f1cca4a2a01bf2a0495501991c83ba7c4d21767e25d1d0d5aa`
- 핵심 명령: `build_and_capture.sh <toolchain-label> <output-dir>`
- callback은 별도 C object에 두고 C++ 선언에는 `noexcept`를 붙이지 않았다. link-time optimization도 끄므로 C++
  compiler가 callback body를 보고 임의로 non-throwing이라고 증명하지 못한다.
- 여섯 실행 파일은 모두 같은 result `5818400090295774291`을 냈다.
- representative guard는 original에서 40 byte, 두 refactored variant에서 16 byte다.

### 5.2 핵심 크기와 section layout

`file bytes`는 debug section이 compiler별로 크게 달라지는 unstripped 크기가 아니라 stripped ELF 크기다.

| compiler | variant | file bytes | `.text` | `.eh_frame` | `.gcc_except_table` | `.rodata` | `.data` | `.bss` |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| GCC 8 | original | 12,040 | 853 | 432 | 4 | 98 | 136 | 16 |
| GCC 8 | conditional | 11,320 | 645 | 336 | 없음 | 80 | 128 | 16 |
| GCC 8 | forced | 11,544 | 645 | 368 | 4 | 80 | 136 | 16 |
| GCC 11 | original | 18,392 | 760 | 336 | 4 | 98 | 136 | 16 |
| GCC 11 | conditional | 17,680 | 520 | 240 | 없음 | 78 | 128 | 16 |
| GCC 11 | forced | 17,904 | 520 | 272 | 4 | 78 | 136 | 16 |

conditional→forced는 두 compiler 모두 `.text` 크기는 바꾸지 않고 `.eh_frame`을 32 byte,
`.gcc_except_table`을 4 byte, `.data`를 8 byte 늘렸다. 추가된 data symbol은 정확히 8-byte
`DW.ref.__gxx_personality_v0`이고 forced/original만 `__gxx_personality_v0`를 import한다. 이는 potentially-throwing
callback이 forced-non-throwing destructor 밖으로 빠질 경우 terminate해야 하는 EH 경로와 일치한다.

original→conditional은 `std::function` 제거 효과가 크다. `guarded_work` symbol 크기는 GCC 8에서 119→56 byte,
GCC 11에서 138→56 byte로 줄었고, guard를 `release()`하는 `released_work`는 각각 78→5, 95→5 byte로 줄었다.

### 5.3 symbol, instruction, EH 차이

측정 host의 L1I/L1D cache line은 모두 64 byte다. 아래 괄호는 함수 시작 주소의 `% 64`다.

| compiler | variant | `guarded_work` address (offset), size | `released_work` address (offset), size | `hot_count` address (offset), size |
|---|---|---|---|---|
| GCC 8 | original | `0x400740` (0), 119 | `0x4007c0` (0), 78 | `0x400810` (16), 51 |
| GCC 8 | conditional | `0x400680` (0), 56 | `0x4006c0` (0), 5 | `0x4006d0` (16), 51 |
| GCC 8 | forced | `0x4006f0` (48), 56 | `0x400730` (48), 5 | `0x400740` (0), 51 |
| GCC 11 | original | `0x4011b0` (48), 138 | `0x401240` (0), 95 | `0x4012a0` (32), 63 |
| GCC 11 | conditional | `0x4011b0` (48), 56 | `0x4011f0` (48), 5 | `0x401200` (0), 63 |
| GCC 11 | forced | `0x4011b0` (48), 56 | `0x4011f0` (48), 5 | `0x401200` (0), 63 |

section-relative disassembly를 비교하면 conditional과 forced의 세 관찰 대상 함수 instruction sequence는 compiler별로
같다. GCC 8 diff에는 함수 전체가 112 byte 이동한 address와 PC-relative operand 변화만 나타난다. GCC 11에서는
세 함수의 address까지 같다. 따라서 아래 timing 차이는 `scope_exit` destructor normal-path 명령의 차이가 아니라
후속 hot loop의 배치 차이를 측정하도록 의도된 결과다.

### 5.4 raw binary diff 요약

| compiler | pair | left/right stripped bytes | 서로 다른 overlapping bytes |
|---|---|---:|---:|
| GCC 8 | original / conditional | 12,040 / 11,320 | 6,239 |
| GCC 8 | conditional / forced | 11,320 / 11,544 | 5,562 |
| GCC 8 | original / forced | 12,040 / 11,544 | 4,795 |
| GCC 11 | original / conditional | 18,392 / 17,680 | 4,142 |
| GCC 11 | conditional / forced | 17,680 / 17,904 | 3,194 |
| GCC 11 | original / forced | 18,392 / 17,904 | 3,158 |

full-file SHA-256는 각 toolchain의 [`sha256.txt`](artifacts/noexcept-binary-layout/rocky8-gcc8/sha256.txt)와
[`sha256.txt`](artifacts/noexcept-binary-layout/rocky9-gcc11/sha256.txt)에 보관했다. raw byte count는 address,
ELF table, build-id 등의 연쇄 변화를 포함하므로 실행 비용과 비례하지 않는다.

conditional/forced의 runtime section만 좁히면 다음과 같다.

| compiler | `.text` | `.rodata` | `.eh_frame` | `.gcc_except_table` | `.data` |
|---|---|---|---|---|---|
| GCC 8 | 645/645 byte, 64 byte 다름 | 80/80, 동일 | 336/368 | 없음/4 | 128/136, 공통 128 byte 동일 |
| GCC 11 | 520/520 byte, 49 byte 다름 | 78/78, 동일 | 240/272 | 없음/4 | 128/136, 공통 128 byte 동일 |

full-file diff에는 `.debug_*`, `.comment`, `.note.gnu.build-id`, symbol/string table 및 주소가 연쇄 이동한 EH table이
섞일 수 있다. 따라서 "몇 byte가 다르다"만으로 실행 code의 차이량을 말하지 말고, runtime-allocated section과
section-relative disassembly를 별도로 비교한다.

### 5.5 CPU/cache-layout 측정

여섯 ELF를 같은 Rocky 9 host의 Intel Xeon Gold 5218R에서 실행했다. `taskset -c 0`, `hot_count(200000000)`,
50회 반복, `perf stat -e cycles,instructions,L1-icache-load-misses`이며 event time-running은 100%다. 프로세스
startup과 guard 호출은 iteration당 한 번뿐이므로 측정값은 사실상 동일한 hot loop의 배치 영향을 본다.

| build compiler | variant | cycles mean (CV) | instructions mean (CV) | IPC | L1I event mean (CV) |
|---|---|---:|---:|---:|---:|
| GCC 8 | original | 412,376,338 (0.10%) | 1,605,279,361 (0.00%) | 3.89 | 129,262 (2.11%) |
| GCC 8 | conditional | 412,207,301 (0.07%) | 1,605,327,333 (0.00%) | 3.89 | 135,210 (2.48%) |
| GCC 8 | forced | 372,607,681 (0.08%) | 1,605,146,053 (0.00%) | 4.31 | 125,668 (1.39%) |
| GCC 11 | original | 411,042,716 (0.08%) | 1,605,406,997 (0.00%) | 3.91 | 139,746 (1.81%) |
| GCC 11 | conditional | 409,910,621 (0.07%) | 1,605,496,604 (0.00%) | 3.92 | 137,365 (1.99%) |
| GCC 11 | forced | 409,267,826 (0.06%) | 1,605,185,237 (0.00%) | 3.92 | 114,475 (0.84%) |

GCC 8 conditional→forced는 instructions가 0.02% 이내인데 cycles가 9.61% 줄고 IPC가 3.89→4.31로 증가했다.
GCC 11에서는 동일 비교가 0.16% cycle 차이에 그쳤다. GCC 8의 `hot_count` 시작점만 64-byte line의 +16에서
+0으로 바뀐 결과와 강하게 상관한다. L1I event도 GCC 8 forced가 conditional보다 약 7.1% 낮았지만 absolute
count가 작고 CV가 있으므로, 이를 단독으로 "L1I miss가 원인"이라고 단정하지 않는다. 32-byte fetch/decoded-stream
경계, loop alignment 등 더 넓은 front-end placement 효과가 후보다.

반대로 실제 PR 방향인 GCC 8 original→conditional은 `hot_count`가 모두 cache-line +16에서 시작하고 cycle 차이가
약 0.04%다. 이 최소 실험은 QA 회귀를 재현하지 않았다. raw counter는 각 binary 옆의 `*.perf-stat-focused.txt`에
보관했다.

## 6. ELF layout에서 무엇을 확인해야 하는가

ELF section header는 address, file offset, byte size, alignment를 각각 기록하며 `sh_addralign`의 power-of-two
제약을 따른다. `.text`는 executable instruction, `.data/.bss`는 writable data에 해당한다.
[System V ELF gABI: Sections](https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.sheader.html)

GNU `ld`는 linker script에 따라 input section을 output section과 memory 위치에 배치한다. 일반적으로 wildcard로
매칭한 section은 link에서 만난 순서대로 들어가며 alignment와 orphan-section 규칙이 padding/후속 주소에 영향을
줄 수 있다. `-Map` 결과는 input section이 output section에 정확히 어떻게 배치됐는지 보여 준다.
[GNU ld: SECTIONS](https://sourceware.org/binutils/docs/ld/SECTIONS.html),
[GNU ld manual](https://sourceware.org/binutils/docs/ld.html)

6개 각각에서 최소한 다음을 보관한다.

```bash
sha256sum binary
size -A binary
readelf -hW binary
readelf -lW binary
readelf -SW binary
readelf -sW binary
readelf --debug-dump=frames-interp binary
readelf -x .gcc_except_table binary
nm -nS -C binary
nm -S --size-sort -C binary
objdump -drwC binary
```

`readelf -u`는 x86 unwind table을 지원하지 않을 수 있으므로 공식 문서가 안내하는
`--debug-dump=frames[-interp]`를 사용한다. 각 command의 의미는
[GNU readelf](https://sourceware.org/binutils/docs/binutils/readelf.html),
[GNU objdump](https://sourceware.org/binutils/docs/binutils/objdump.html),
[GNU size](https://sourceware.org/binutils/docs/binutils/size.html),
[GNU nm](https://sourceware.org/binutils/docs/binutils/nm.html)에 근거한다.

## 7. `log_Gl`/global-data cache-line 가설

### 7.1 사전 판단

conditional `noexcept`는 compile-time 명세이므로 그 자체가 runtime storage를 만들지 않는다. 또한 이 PR의 핵심은
automatic `scope_exit` 객체가 들고 있던 `std::function`을 concrete callable로 바꾸는 것이다. 따라서 먼저
확인해야 할 직접 효과는 local object/stack, machine code와 EH metadata이지, `log_Gl`의 type/field 증가가 아니다.

merge commit의 실제 source diff는 `src/base/scope_exit.hpp`와 `src/transaction/log_recovery_redo.hpp` 두 파일뿐이다.
`LOG_GLOBAL log_Gl`의 definition은 변경되지 않은 `src/transaction/log_global.c:84`이고, `LOG_GLOBAL`의 field도
바뀌지 않았다. 해당 commit에서 source-wide `scope_exit` 사용은 redo recovery의 page-unfix guard 한 곳뿐이며
질의/parser/executor 경로에는 없다. 따라서 읽기 전용 `COUNT(*)`가 guard 실행 비용을 직접 지불한다는 설명은
source evidence와 맞지 않는다.

최소 ELF에서는 더 미묘한 간접 효과가 실제 나타났다. original/forced는 8-byte
`DW.ref.__gxx_personality_v0`를 가지지만 conditional은 가지지 않아, 64-byte `g_hot_data`의 주소는 여섯 경우 모두
그대로인 반면 뒤의 `g_cleanup_count`는 conditional에서 8 byte 앞당겨졌다. 즉 **global의 크기가 바뀌지 않아도**
앞선 linker-generated data 때문에 주소와 cache-line offset이 바뀔 수는 있다. 다만 큰 CUBRID executable은 다른
EH 사용자 때문에 `DW.ref.__gxx_personality_v0`가 세 build에 이미 공통으로 존재할 가능성이 높다. 실제
`cub_server`에서 `sizeof(LOG_GLOBAL)`, `log_Gl`의 section-relative address와 `% 64`를 비교하기 전에는 이 8-byte
probe 현상을 `log_Gl`에 적용할 수 없다.

다만 다음 간접 경로는 실측 대상이다.

```text
exception contract / callable representation 변화
  -> inlining, landing pad, .text, EH read-only section 크기 변화
  -> linker padding/section 또는 LOAD-segment 경계 변화
  -> 뒤쪽 symbol의 VMA 및 cache-line/page 내 offset 변화 가능
```

이 가능성은 "전역 데이터 크기가 늘었다"는 주장과 구분해야 한다. 아래 표로 판단한다.

| 관측 | global-data 가설에 미치는 영향 |
|---|---|
| `.data/.bss` size와 `log_Gl` symbol size/section-relative offset이 모두 동일 | 강하게 약화 |
| 절대 VMA만 바뀌고 section-relative offset 및 `% 64`가 동일 | layout 이동은 있으나 해당 cache-line 경계 가설은 약함 |
| `log_Gl` 또는 hot field가 다른 64-byte line 경계를 가름 | 후보로 유지; PMU/field-access evidence 필요 |
| `.text` hot function 주소·크기·32/64-byte offset만 바뀜 | I-cache/front-end 가설이 data-cache 가설보다 우선 |
| `.eh_frame/.gcc_except_table`만 바뀌고 hot path code/layout은 동일 | 정상 질의 hot-path 지연 설명은 약함 |

PIE/ASLR이 켜진 실행 파일에서 runtime 절대주소만 비교하지 않는다. 먼저 section-relative offset과 symbol `% 64`,
그리고 load segment mapping을 비교한다. 실제 CPU의 cache line과 PMU event는 `lscpu`, CPUID 및 `perf list`로
확인한다.

### 7.2 I-cache/front-end 가설

Intel Optimization Reference Manual은 code size/working set이 instruction cache를 넘거나 hot code가 잘못
정렬되면 front-end 문제가 발생할 수 있고, Decoded ICache가 32-byte aligned chunk 단위의 제약을 가진다고
설명한다. 또한 I-cache miss는 front-end fetch latency로 분류된다.
[Intel 64 and IA-32 Optimization Reference Manual Volume 1, sections 3.4.2.5 and 22.1.2](https://www.intel.com/content/www/us/en/content-details/821612/intel-64-and-ia-32-architectures-optimization-reference-manual-volume-1.html)

따라서 hot function의 시작 주소, size, 32/64-byte 경계 변화는 현실적인 가설 생성 근거다. 그러나 binary layout만
보고 miss가 실제 늘었다고 말할 수는 없다. Intel 문서도 I-cache issue 판단에 miss와 retired instruction을 같은
granularity로 비교하라고 설명한다.

### 7.3 runtime counter로 가설을 구분하는 기준

| 관측 | 우선 해석 |
|---|---|
| `instructions` 증가 + `cycles` 증가 | codegen/inlining/path-length 차이 후보 |
| `instructions` 유사 + front-end/I-cache/ITLB event 증가 | code alignment/working-set 가설 강화 |
| L1D/LLC miss 증가 + 의심 global line 배치 변화 | data-layout/cache conflict 가설 강화 |
| generic `cache-misses`만 증가 | I-cache/D-cache/LLC 원인 구분 불가 |
| wall time만 변화, PMU와 code/layout 차이 불명확 | scheduler/frequency/noise 또는 다른 subsystem 배제 불가 |

Linux `perf_event_open` 문서는 generic hardware event도 platform마다 지원 여부와 의미가 다를 수 있고,
`cache-references`/`cache-misses`가 보통 LLC를 뜻하지만 CPU 설계에 따라 달라질 수 있다고 경고한다. L1I처럼
구체적인 event도 실행 CPU가 지원하는지 먼저 확인해야 한다.
[Linux `perf_event_open(2)`](https://man7.org/linux/man-pages/man2/perf_event_open.2.html)

최소 측정 항목은 `cycles`, `ref-cycles`, `instructions`, `branches`, `branch-misses`, task migration/context switch이며,
`perf list`가 제공하는 CPU-specific I-cache/ITLB/front-end 및 L1D/LLC event를 별도 추가한다. 동일 host CPU에서
process를 같은 CPU에 고정하고 충분한 warm-up과 반복 분포를 기록한다. container OS만 다르고 host CPU가 같다면
microarchitecture는 같지만 compiler/linker/userspace library가 다르며, host가 다르면 CPU 차이까지 섞인다.

## 8. 인과성 판정 순서

1. 각 compiler에서 `conditional` 대 `forced`를 비교해 exception specification의 증분 효과를 분리한다.
2. 각 compiler에서 `original` 대 `forced`를 비교해 예외 계약을 같게 유지한 refactor 구현 효과를 본다.
3. minimal binary에서 차이가 발생한 함수/EH section을 CUBRID final binary의 실제 instantiation/caller까지 추적한다.
4. CUBRID final binary에서 hot query path 함수의 주소, 크기, disassembly, FDE/LSDA, `log_Gl` layout을 비교한다.
5. wall time과 PMU counter를 같은 실행에서 수집한다.
6. 의심 layout을 padding/alignment/link-order perturbation으로 의도적으로 앞뒤로 움직여 성능이 함께 움직이는지 본다.
7. 결과가 안정적이면 compiler dump/optimization record로 GCC 8의 pass 결정을 추적하고, 이때에만 compiler bug
   가능성을 평가한다.

마지막 6번은 cache-layout 인과성을 확인하는 중요한 falsification 단계다. 특정 한 배치가 느렸다는 사실은 우연한
layout sensitivity와 변경 자체의 본질적 비용을 구분하지 못한다.

## 9. 최종 결론

### 확인된 것

- original→refactored는 guard 40→16 byte, `guarded_work`/`released_work` code 축소라는 의도한 최적화를 달성했다.
- conditional-false→forced-true는 normal-path instruction sequence를 바꾸지 않았지만, 두 compiler 모두 EH
  metadata와 8-byte personality reference를 추가했다.
- GCC 8 linker layout은 그 차이를 `.text` 함수 주소 112-byte 이동으로 증폭했고, 독립 hot loop의 cache-line
  offset을 +16→+0으로 바꿨다. 동일 instruction 수에서 cycle -9.61%가 반복됐다.
- GCC 11은 두 refactored variant의 관찰 함수 주소가 같았고 cycle은 사실상 같았다(-0.16%). GCC 8만의
  code-placement sensitivity라는 사용자 가설은 **메커니즘 수준에서는 성립한다**.
- minimal ELF에서 global address가 linker-generated 8 byte 때문에 이동할 수 있음도 확인했다. 그러나
  `log_Gl` 자체의 size가 변한다는 증거는 없고 PR source상 그 type은 변경되지 않았다.

### 확인되지 않은 것

- QA의 17.583641→19.4410452초(+10.56%)가 PR #6636 때문에 발생했다는 인과성.
- 실제 11.5.0.2029/2031 `cub_server`에서 query hot function 또는 `log_Gl`이 불리한 cache-line으로 이동했다는 사실.
- GCC 8 compiler bug. 관찰된 ELF는 C++ exception contract와 ABI에 맞으며, 주소 민감 성능 cliff 자체는
  compiler 오동작의 증거가 아니다.

특히 microbenchmark의 실제 PR 방향인 GCC 8 original→conditional은 cycle 차이가 0.04%이고 두 `hot_count`가
같은 cache-line +16에서 시작했다. 그러므로 이 결과를 "PR 회귀 재현"으로 읽으면 안 된다. 반면 forced variant가
빨라진 사실은 `noexcept`를 되돌리면 전체 CUBRID binary도 우연히 빨라질 가능성을 보여 주지만, 그것은 원인 수정이
아니라 layout workaround일 수 있다.

### 권고

generic `scope_exit` destructor를 다시 무조건 `noexcept`로 바꾸는 것은 성능 힌트가 아니라 예외 의미 변경이다.
callback이 던지면 terminate하므로, binary layout만을 이유로 적용하지 않는 편이 맞다. 특정 CUBRID cleanup이 실제로
no-throw 계약이라면 해당 lambda/callable을 `noexcept`로 명시하여 conditional destructor가 자연스럽게 true가
되도록 하는 방식이 의미상 더 정확하다.

실제 이슈를 종결하려면 11.5.0.2029/2031의 GCC 8 final binaries에서 다음 한 번의 differential 실험이 필요하다.

1. `cub_server`/standalone 실행 파일의 build-id와 전체 commit을 고정한다.
2. `nm -nS -C`, link map, disassembly로 `log_Gl`, query executor/scan/count hot symbols의 size·address·`% 32/% 64`를
   비교한다.
3. 같은 DB와 query를 CPU 고정으로 반복하며 cycles/instructions와 CPU-specific front-end/L1I/ITLB event를 얻는다.
4. 의심 함수 앞 padding 또는 alignment만 변화시켜 10.56% 지연도 함께 이동하는지 확인한다.

이 결과가 있어야 "GCC 8의 unlucky layout"을 CBRD-26382 성능 회귀의 원인으로 승격할 수 있다. 현재 판정은
**가능한 GCC 8 전용 layout 메커니즘은 확인, 실제 SQL 회귀와의 연결은 미확인, `log_Gl` size 증가는 부정**이다.

## Sources

- CUBRID [PR #6636](https://github.com/CUBRID/cubrid/pull/6636) 및
  [merge commit](https://github.com/CUBRID/cubrid/commit/8fd3ca03e58b342a494a2f5594be23c72a822479)
- C++ draft: [`[except.spec]`](https://eel.is/c++draft/except.spec),
  [`[expr.unary.noexcept]`](https://eel.is/c++draft/expr.unary.noexcept),
  [`[except.handle]`](https://eel.is/c++draft/except.handle),
  [`[except.terminate]`](https://eel.is/c++draft/except.terminate)
- GCC 8.5: [C++ dialect](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/C_002b_002b-Dialect-Options.html),
  [code generation](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Code-Gen-Options.html),
  [optimization](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Optimize-Options.html)
- GCC 11.5: [C++ dialect](https://gcc.gnu.org/onlinedocs/gcc-11.5.0/gcc/C_002b_002b-Dialect-Options.html),
  [code generation](https://gcc.gnu.org/onlinedocs/gcc-11.5.0/gcc/Code-Gen-Options.html),
  [optimization](https://gcc.gnu.org/onlinedocs/gcc-11.5.0/gcc/Optimize-Options.html)
- GCC [9](https://gcc.gnu.org/gcc-9/changes.html), [10](https://gcc.gnu.org/gcc-10/changes.html),
  [11](https://gcc.gnu.org/gcc-11/changes.html) release notes
- [Itanium C++ ABI](https://itanium-cxx-abi.github.io/cxx-abi/abi.html) 및
  [Exception Handling ABI](https://itanium-cxx-abi.github.io/cxx-abi/abi-eh.html),
  [EH working draft](https://itanium-cxx-abi.github.io/cxx-abi/exceptions.pdf)
- [System V ELF gABI — Sections](https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.sheader.html)
- GNU binutils: [readelf](https://sourceware.org/binutils/docs/binutils/readelf.html),
  [objdump](https://sourceware.org/binutils/docs/binutils/objdump.html),
  [size](https://sourceware.org/binutils/docs/binutils/size.html),
  [nm](https://sourceware.org/binutils/docs/binutils/nm.html),
  [ld](https://sourceware.org/binutils/docs/ld.html)
- [Intel 64 and IA-32 Architectures Optimization Reference Manual Volume 1](https://www.intel.com/content/www/us/en/content-details/821612/intel-64-and-ia-32-architectures-optimization-reference-manual-volume-1.html)
- [Linux `perf_event_open(2)`](https://man7.org/linux/man-pages/man2/perf_event_open.2.html)
