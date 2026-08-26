# CBRD-26382: hot function alignment와 code ordering 선택지

- 작성일: 2026-08-27
- 실험 근거: [GCC 8 full-server follow-up](CBRD-26382-gcc8-full-server-follow-up_codex.md)

## 1. 결론부터

CBRD-26382에서 관측한 **최종 ELF의 16-byte 주소 이동**을 재발 방지하려고 모든 함수를 크게 정렬하는 것은 안전한
기본 해법이 아니다. 이 이슈에 맞는 우선순위는 다음과 같다.

1. 동일 GCC 8.3.1/동일 링크 환경의 7-byte padding control D에서 **hot function 주소 phase와 성능이 함께
   복원되는지** 먼저 확인한다. 이번 A/B/D에서는 shared/fresh-DB 두 protocol 모두 그 방향을 확인했다. 다음은
   여러 phase와 독립 rebuild로 주기성과 build-date confound를 제거하는 일이다.
2. 입증된 함수만 `__attribute__((aligned(32)))`로 좁게 고정하는 실험이 가장 작은 개입이다. 이 속성이 보장하는
   것은 **함수 시작 주소의 최소 정렬**이지, 함수 내부 loop의 정렬이나 DSB hit, 성능 향상이 아니다.
3. 전체 프로그램의 hot/cold 배치는 사람이 추측한 `hot` 표식보다 대표 workload로 훈련한
   `-fprofile-generate`/`-fprofile-use`를 우선 검토한다. 다만 PGO는 layout만 바꾸는 옵션이 아니라 inlining,
   unrolling 등 여러 최적화를 함께 바꾸므로 결과를 별도 제품 variant로 검증해야 한다.
4. `-falign-functions=32`의 전역 적용은 빠른 원인 실험에는 쓸 수 있지만, `.text` 증가와 I-cache/iTLB/DSB
   footprint 위험 때문에 바로 제품 기본값으로 삼지 않는다.
5. GNU ld script와 per-function section은 순서를 가장 결정적으로 제어하지만 유지보수 비용과 링크 ABI 영향 범위도
   가장 크다. AutoFDO와 BOLT는 그 다음 단계의 profile-driven 실험 후보이며, 특히 현재 BOLT의 shared-object 지원과
   GCC 8 기본 옵션 충돌을 고려하면 즉시 적용안이 아니다.

“최신 GCC/Clang이면 자동으로 문제가 사라진다”는 결론도 성립하지 않는다. 새 compiler의 inliner,
hot/cold splitting, scheduling, alignment heuristic이 이번 phase를 우연히 피할 수 있고, profile을 주면 실제
hotness를 사용한 더 나은 배치도 가능하다. 그러나 non-PGO compiler는 이 SQL의 hot path를 보지 못하며 정확한
함수 순서·내부 loop phase·DSB hit를 보장하지 않는다. compiler upgrade는 같은 source에서 **다른 ELF 전체를
만드는 변화**이므로, GCC 8/최신 GCC/최신 Clang을 같은 runtime에서 분리 비교해야 한다.

## 2. 현재 CUBRID 증거의 출발점

기존 분석에서 GCC 8.3.1 release build A→B는 앞쪽 cold fragment가 7 bytes 작아진 뒤 8,287개 common symbol을
16 bytes 앞당겼고, hot query-executor 함수들의 32-byte phase를 바꿨다. Intel Core Ultra 7 270K Plus stable
host에서는 B가 평균 `+1.464%` 느렸고, MITE µops/query가 `+12.664%`, host perf가 제공한 DSB→MITE penalty
신호가 `+71.729%` 증가했다. 하지만 Top-down에서 Front-end Bound는 `5.73% → 3.85%`로 줄고 Core Bound는
`10.58% → 13.48%`로 늘었다. 따라서 주소 phase와 공급 경로 변화는 관측됐지만, **DSB/MITE가 slowdown의 단독
원인이라는 증거는 아니다**. 수치와 증거 한계는
[기존 causal-chain 보고서](CBRD-26382-scope-exit-frontend-causal-chain_codex.md)와
[GCC 8 full-server 후속 보고서](CBRD-26382-gcc8-full-server-follow-up_codex.md)에 정리돼 있다.

후속 diagnostic D는 B의 query object와 제품 실행 로직을 그대로 두고 앞쪽 `.text.unlikely` contribution에
실행 불가능한 NOP 7 bytes만 더했다. D의 주요 query hot-function 시작 주소는 A로 돌아가고 `log_Gl`은 B에
남았다. shared-DB balanced 54회 중앙값은 B/A `+1.336%`, D/B `-1.786%`, D/A `-0.474%`였다. QA 자동
shell처럼 매 sample fresh DB를 만든 27회 round-paired 비교도 B/A `+0.857%`, D/B `-1.520%`, D/A
`-0.676%`로 같은 방향이었다. 이는 **link phase가 timing을 움직인다는 가설을 강하게 지지**하지만, D가 하루 뒤
rebuild여서 release string과 `.rodata`에 잔여 차이가 있고 아직 한 phase만 되돌렸으므로 blanket alignment 제품
변경을 바로 정당화하지 않는다.

balanced PMU 90회도 D에서 cycles/query `-1.446%`, IPC `+1.467%`, core bound `13.714% → 9.865%`로 B의
상태가 A 수준에 돌아왔다. MITE µops/query와 host-perf DSB→MITE penalty도 각각 `-7.048%`, `-24.214%`였다.
그러나 D의 Front-end Bound는 B보다 높으면서 D가 더 빨랐으므로, 이 결과는 layout-aware 완화의 근거이지
“32-byte alignment가 DSB miss를 없애면 무조건 빨라진다”는 근거가 아니다.

이 구분은 아래 권고의 전제다.

- PMU counter가 직접 말하는 것: DSB 또는 MITE가 공급한 µop 수, 특정 조건으로 정의된 DSB miss, Top-down slot
  분류의 변화.
- counter만으로 말할 수 없는 것: 왜 특정 instruction address가 miss를 만들었는지, 그 miss가 wall time을 몇 %
  늘렸는지, 어느 정렬값이 모든 CPU에서 최적인지.

Intel도 DSB-to-MITE switch를 전환 penalty가 생기는 상황으로 정의하면서, 큰 hot code region과 code layout을
함께 살펴보라고 안내한다. I-cache 문제에는 hot/cold code의 분리와 PGO를, iTLB overhead에는 hot region 축소와
재배치를 권한다. 이는 방향을 제시하는 일반 지침이지 CUBRID B의 원인을 자동으로 확정하는 판정식은 아니다.
([Intel VTune CPU Metrics Reference](https://www.intel.com/content/www/us/en/docs/vtune-profiler/user-guide/2024-2/cpu-metrics-reference.html))

## 3. GCC 8에서 사용할 수 있는 수단

### 3.1 현재 `-O2`가 이미 하는 일

CUBRID의 해당 release build는 `-O2`다. GCC 8.5 공식 문서상 `-O2`는 이미 `-falign-functions`와
`-freorder-functions`를 켠다. 따라서 “그 옵션 이름을 추가한다”만으로 새 보장이 생기지는 않는다. 명시적인
정렬값, profile, section 구성처럼 현재 기본 동작과 실제로 다른 입력이 있어야 한다.
([GCC 8.5 Optimize Options](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Optimize-Options.html))

| 수단 | GCC 8이 직접 보장하는 것 | 보장하지 않는 것 / CUBRID 주의점 | 판단 |
|---|---|---|---|
| `__attribute__((aligned(32)))` | 해당 함수의 최소 alignment를 bytes 단위로 지정한다. 정렬을 늘릴 수만 있고 그 함수에서는 `-falign-functions`보다 우선한다. | linker의 최대 정렬 지원에 제한될 수 있다. 내부 loop/branch 정렬, DSB residency, 성능은 보장하지 않는다. | phase 영향이 입증된 소수 함수에 가장 좁게 시험 |
| `__attribute__((hot))` | 더 공격적으로 최적화하고, 많은 target에서 특별한 text subsection에 두어 hot 함수끼리 가깝게 배치한다. | 정확한 함수 순서·시작 주소는 보장하지 않는다. `-fprofile-use`가 있으면 자동 검출되고 수동 속성은 무시된다. codegen도 함께 바뀐다. | profile이 없고 hotness가 확실할 때 제한적으로 |
| `-falign-functions=32` | 함수 시작을 32-byte 경계로 맞추기 위해 필요한 만큼 skip/padding한다. GCC 8의 문서화된 형식은 단일 `=n`이다. | assembler/target 제약과 skip 한도가 있다. 모든 함수에 padding을 만들 수 있고, 최신 GCC의 `n:m:n2:m2` 구문을 GCC 8에 소급하면 안 된다. | 전역 production 기본값보다 원인 탐색용 |
| `-flimit-function-alignment` | 함수 크기보다 많은 정렬 padding을 assembler에 요청하지 않도록 제한한다. | footprint 증가를 없애지는 않고 CPU 성능을 보장하지 않는다. | 전역 정렬 실험 시 함께 비교 |
| `-freorder-functions` | `.text.hot`/`.text.unlikely` 같은 subsection을 사용하고 linker가 재배치할 수 있게 한다. | 효과적이려면 profile feedback과 linker의 합리적인 section 배치가 필요하다. `-O2`에서 이미 켜져 있다. | 단독 추가보다 PGO와 함께 확인 |
| `-freorder-blocks-and-partition` | hot/cold basic block을 별도 section으로 나눠 paging/cache locality 개선을 시도한다. GCC 8 x86 `-O2`에서 활성화된다. | EH/unwind, user section 등 조건에 따라 자동 비활성화될 수 있다. BOLT와는 현재 공식적으로 호환되지 않는다. | 현재 build/후처리 도구와 조합 점검 |
| `-fprofile-generate` → workload → `-fprofile-use` | 실행 profile로 branch probability와 hot function을 찾고, function order를 포함한 여러 최적화를 켠다. | layout-only 변화가 아니다. 대표성 없는 profile과 source/profile mismatch가 새 regression을 만들 수 있다. | 전체 배치 개선의 우선 후보 |
| `-fprofile-reorder-functions` | instrumentation profile이 기록한 함수의 최초 실행 시각을 기준으로 오름차순 배치한다. `-fprofile-use`가 활성화한다. | “호출 빈도가 높은 순”이나 최적 call-graph order를 보장하는 옵션은 아니다. | PGO 결과의 실제 order를 link map으로 확인 |
| `-fauto-profile` | Linux `perf` sample을 AutoFDO 형식으로 변환한 profile을 소비한다. 여러 profile 기반 최적화를 켠다. | GCC 8 문서는 unstripped binary와 `create_gcov` 절차를 요구한다. sample 편향/낡은 profile 및 넓은 codegen 변화 검증 필요. | instrumentation PGO 이후 후보 |
| `-ffunction-sections` | 각 함수를 별도 section에 둬 linker가 함수를 개별 배치할 수 있게 한다. | GCC 문서도 object/executable 크기 증가와 상대 주소 계산 제약, 성능 영향의 불확실성을 경고하며 유의미한 이득이 있을 때만 쓰라고 한다. | linker ordering 실험의 기반, 단독 해법 아님 |

`aligned`와 `hot`의 정확한 정의 및 linker 한계는
[GCC 8.5 Common Function Attributes](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Common-Function-Attributes.html),
나머지 최적화 옵션의 정의와 `-O2` 포함 여부는
[GCC 8.5 Optimize Options](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Optimize-Options.html), profile 생성 절차는
[GCC 8.5 Instrumentation Options](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Instrumentation-Options.html)에 직접
기술돼 있다.

### 3.2 어떤 수단이 “시작 주소”와 “순서”를 실제로 고정하는가

서로 다른 문제를 분리해야 한다.

- `aligned(32)`는 **한 함수 시작 주소의 최소 정렬**을 표현한다.
- `hot`과 `-freorder-functions`는 **유사한 온도의 함수를 묶도록 힌트를 준다**. 정확한 최종 순서는 linker까지
  포함하지 않으면 고정되지 않는다.
- [`section(".text.hot.qexec_execute_scan")`](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Common-Function-Attributes.html)
  또는 `-ffunction-sections`로 별도 input section을 만든 뒤 linker
  script에서 그 section을 명시 순서로 소비하면 **최종 링크 순서에 가장 강한 통제**를 갖는다.

GCC의 `no_reorder` 속성도 marked symbol 상호 간 compiler 재배치를 막을 뿐, 실제 프로그램 순서는 linker command
line에 달렸다고 공식 문서가 명시한다. 따라서 이것을 final DSO ordering 보장으로 사용하면 안 된다.
([GCC 8.5 Common Function Attributes](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Common-Function-Attributes.html))

### 3.3 GNU ld 2.30 linker script

GNU ld script는 input section이 어느 output section에 어떤 순서로 들어가는지 직접 제어한다.
`SORT_BY_NAME`은 section 이름순, `SORT_BY_ALIGNMENT`는 큰 alignment부터 배치한다. 후자는 필요한 padding을 줄이기
위한 기능이며 **hotness 순서 기능은 아니다**. `-M` map file은 input-to-output 매핑을 검증하는 공식 수단이다.
([GNU ld 2.30 Input Section Wildcards](https://sourceware.org/binutils/docs-2.30/ld/Input-Section-Wildcards.html))

`ALIGN(0x20)`은 output section의 주소를 32-byte 경계로 올릴 수 있다. 이것만으로 그 안의 모든 함수 시작 주소가
32-byte aligned가 되는 것은 아니다.
([GNU ld 2.30 Output Section Address](https://sourceware.org/binutils/docs-2.30/ld/Output-Section-Address.html))

전체 default script를 복제·교체하는 `-T`는 동적 링크, unwind, relocation, RELRO 등 기존 배치를 실수로 바꿀 위험이
크다. GNU ld 2.30의 `INSERT BEFORE/AFTER`는 추가 script를 default `SECTIONS`에 삽입하고 `-T`가 default script를
대체하지 않게 해 준다. 따라서 CUBRID 실험에는 가능한 한 작은 보조 script가 낫다.
([GNU ld 2.30 Other Linker Script Commands](https://sourceware.org/binutils/docs-2.30/ld/Miscellaneous-Commands.html))

개념 예시는 다음과 같다. 실제 section 명과 wildcard 소비 순서는 반드시 link map으로 확인해야 한다.

```ld
SECTIONS
{
  .text.cubrid_hot ALIGN(32) :
  {
    *(.text.cubrid_hot.001_qexec_execute_scan)
    *(.text.cubrid_hot.002_fetch_val_list)
    *(.text.cubrid_hot.*)
  }
}
INSERT BEFORE .text;
```

이 방식은 순서를 명시적으로 만들지만 안전성이 자동으로 따라오지는 않는다. exported symbol/ABI, relocation,
exception/unwind, debug symbol, split DWARF, stripping, packaging 및 ASLR 적용 후 상대 주소를 검증해야 한다.

## 4. Profile-driven 선택지

### 4.1 GCC instrumentation PGO

GCC 8 공식 절차는 compile과 link에 `-fprofile-generate`를 적용하고, 대표 workload를 실행해 profile을 만든 다음,
동일 source에 `-fprofile-use`를 적용하는 것이다.
([GCC 8.5 Instrumentation Options](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Instrumentation-Options.html))

이것이 수동 hot list보다 나은 점은 실제 call/branch 빈도로 전체 layout과 codegen을 함께 최적화한다는 것이다.
반대로 CUBRID에서는 한 종류의 query만 훈련하면 OLTP, DDL, recovery, utility, broker/server 경로가 왜곡될 수 있다.
`-fprofile-use`는 inlining, unrolling, vectorization, block/function reordering 등 여러 pass를 활성화하므로 “주소만
바뀐 A/B”로 해석할 수 없다. profile checksum/mismatch 경고를 억지로 무시하지 말고, 훈련 workload와 제품
workload를 분리해서 평가해야 한다.
([GCC 8.5 Optimize Options](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Optimize-Options.html))

### 4.2 AutoFDO

GCC 8의 `-fauto-profile[=path]`는 Linux `perf record`로 모은 sample을 AutoFDO의 `create_gcov` 도구로 변환한
profile을 사용한다. GCC 문서는 unstripped executable을 요구하고 기본 profile 이름을 `fbdata.afdo`로 정의한다.
([GCC 8.5 Optimize Options](https://gcc.gnu.org/onlinedocs/gcc-8.5.0/gcc/Optimize-Options.html),
[Google AutoFDO project](https://github.com/google/autofdo))

instrumentation overhead를 피할 수 있지만, sample이 어느 binary/source에 대응하는지와 production workload의
대표성이 핵심이다. CUBRID에서 적용하려면 shared library symbolization, build-id, ASLR 주소 보정, inline frame
복원을 먼저 재현해야 한다.

### 4.3 LLVM BOLT

BOLT는 이미 링크된 ELF binary를 `perf` profile로 최적화해 basic block과 function layout을 바꾸는 post-link
optimizer다. 공식 README상 x86-64/AArch64 ELF를 지원하며, symbol table이 있어야 하고 최대 효과에는
`--emit-relocs`로 보존한 relocations가 권장된다.
([LLVM BOLT README](https://github.com/llvm/llvm-project/blob/main/bolt/README.md?plain=1))

현재 CUBRID/GCC 8에 바로 넣지 말아야 할 이유도 같은 README에 있다.

- BOLT는 `-freorder-blocks-and-partition`과 호환되지 않으므로 이 옵션을 끄고 빌드해야 한다. GCC 8 x86 `-O2`가
  기본으로 켜는 최적화와 충돌한다.
- shared-object 지원은 최근 추가된 기능으로 공식 문서가 bug report를 요청하고 있다.
- function pointer 차이처럼 code layout 속성에 의존하는 프로그램은 안전하지 않다.
- stale profile은 이득을 줄이거나 성능을 악화시킬 수 있어 release profile 갱신이 필요하다.

따라서 BOLT는 별도 prototype에서 `libcubrid.so`의 relocation/symbol/unwind/debug/packaging과 전체 QA를 통과한 뒤에만
고려한다. “링크 후에 순서를 바꿔 주므로 더 안전하다”는 주장은 공식 자료가 보장하지 않는다.

## 5. 과도한 alignment와 padding의 trade-off

Intel front-end에는 서로 반대인 두 힘이 작용한다.

1. **경계 배치의 이득 가능성:** Intel Optimization Reference Manual은 DSB가 legacy decode보다 높은 µop
   bandwidth를 제공하고 DSB↔MITE 전환에 overhead가 있다고 설명한다. 문서화된 관련 Intel core의 DSB는 aligned
   32-byte 영역 단위 제약을 가지므로, dense hot block의 배치를 조절해 더 적은 영역에 맞추는 것이 이득일 수 있다.
2. **footprint 증가의 손실 가능성:** padding은 `.text`의 cache line과 page 수를 늘린다. 더 큰 hot working set은
   L1I miss, iTLB pressure, DSB capacity/conflict pressure를 키울 수 있다. Intel VTune도 큰 code working set과
   hot/cold fragmentation을 instruction-cache 문제의 원인으로 들고 PGO와 hot-code 재배치를 권한다.

근거:
[Intel 64 and IA-32 Architectures Optimization Reference Manual, Vol. 1, §3.4.2.5](https://cdrdv2-public.intel.com/821612/248966-Optimization-Reference-Manual-V1-050.pdf),
[Intel Optimization Reference Manual, Vol. 2, Sandy Bridge front end](https://cdrdv2-public.intel.com/821614/356477-Optimization-Reference-Manual-V2-050.pdf),
[Intel VTune CPU Metrics Reference](https://www.intel.com/content/www/us/en/docs/vtune-profiler/user-guide/2024-2/cpu-metrics-reference.html).

`-falign-functions=32`가 각 함수 앞에 만들 수 있는 padding의 단순 수학적 상한은 31 bytes이고, 시작 phase가
균등하다는 가정 아래 평균은 15.5 bytes다. 이는 GCC나 Intel의 성능 보장이 아니라 **정렬 산술에 불과한 추정치**다.
실제 증가는 기존 정렬, 함수 순서, assembler skip, linker relaxation에 따라 달라지므로 최종 ELF에서 재야 한다.

또한 함수 사이 padding은 보통 함수 호출 시 실행되지 않지만 code footprint를 차지한다. 반면 loop/label/branch
정렬을 위해 hot path 안에 삽입된 NOP는 fall-through 경로에서 실행될 수도 있다. Intel 매뉴얼도 NOP 추가가 실행
µop와 code size를 늘릴 수 있으므로 신중히 적용하라고 한다.
([Intel Optimization Reference Manual, Vol. 1](https://cdrdv2-public.intel.com/821612/248966-Optimization-Reference-Manual-V1-050.pdf))

그러므로 “32 bytes가 DSB 단위이므로 모든 함수를 32 bytes에 맞추면 항상 좋다”는 결론은 틀리다. 정확한 DSB 구조와
제약은 세대별로 다르고, branch placement, µop 수, set/way conflict, code working set, frontend flush가 함께
작용한다. CUBRID에서는 다음을 모두 비교해야 한다.

- `.text`/hot text bytes, mapped executable pages
- L1I miss와 iTLB walk
- DSB/MITE supplied µops와 공식적으로 해당 CPU에 정의된 DSB miss 이벤트
- Top-down Front-end Bound뿐 아니라 Core/Memory Bound
- query time, IPC, binary/package size

## 6. 최신 GCC/Clang이면 자동으로 나아지는가

### 6.1 짧은 답

**자동 보장은 없지만, profile을 주면 GCC 8보다 더 직접적인 code-locality 수단을 사용할 수 있다.** compiler
버전을 올리기만 한 non-PGO build도 inliner, hot/cold splitting, scheduling, 기본 alignment heuristic이 달라져
이번 16-byte phase를 우연히 피할 수 있다. 그러나 compiler는 실제 CUBRID workload를 보지 않았으므로 어느
함수가 얼마나 hot한지, 어느 `%32` phase가 이 CPU에서 좋은지를 알 수 없다. unrelated source가 다시 바뀌면
새 layout도 흔들릴 수 있다.

즉 “새 compiler에서 현상이 안 보인다”는 것은 **그 compiler가 만든 이번 ELF가 덜 불리했다**는 관측이지,
“새 compiler가 hot-path alignment 문제를 일반적으로 해결한다”는 보장이 아니다.

### 6.2 최신 GCC에서 GCC 8보다 나아진 수단

작성일 기준 공식 최신 stable release는 [GCC 16.2](https://gcc.gnu.org/gcc-16/)와
[LLVM/Clang 22.1.8](https://www.llvm.org/)이다. 아래 “최신 compiler” 비교는 재현성을 위해 이 버전을 뜻하며,
moving `latest` tag를 뜻하지 않는다.

GCC 16.2 공식 문서의 `-O2`도 GCC 8처럼 `-falign-functions`, `-freorder-functions`,
`-freorder-blocks-and-partition`을 켠다. 중요한 점은 다음과 같다.

- profile 또는 `hot`/`cold` annotation이 없으면 `-freorder-functions`는 효과적이지 않다고 여전히 명시한다.
- `-falign-functions=n:m:n2:m2`로 primary/secondary alignment와 허용 padding을 GCC 8의 단일 `n`보다 세밀하게
  지정할 수 있다. 예를 들어 `64:7:32:3`은 padding budget 안에서만 두 단계 정렬을 시도한다.
- `-fmin-function-alignment`는 cold 판단과 관계없이 최소 정렬이 필요한 경우를 분리하지만, 성능 최적값을
  알아내는 기능은 아니다.
- `-fipa-reorder-for-locality`는 단순히 hot/normal/cold bucket을 모으는 대신 **자주 연결된 call chain을 가까이
  묶는** pass다. GCC는 profile feedback과 함께 쓰기를 권하지만 profile 없이는 기본 활성화하지 않는다.
- `-fprofile-use`/`-fauto-profile`은 branch probability, inlining, block/function reordering 등 넓은 최적화를
  함께 켠다. 따라서 layout-only fix가 아니라 별도 제품 variant로 검증해야 한다.

근거: [GCC 16.2 Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html).

### 6.3 최신 Clang/LLVM에서 가능한 수단

Clang 공식 문서는 PGO가 function call frequency를 inliner에, branch frequency를 basic-block ordering에 사용한다고
설명한다. instrumentation PGO와 sampling PGO를 모두 지원하지만, 대표하지 못한 훈련 입력은 잘못된 최적화를
만들 수 있다고 경고한다.
([Clang User's Manual: Profile Guided Optimization](https://clang.llvm.org/docs/UsersManual.html#profile-guided-optimization))

LLVM의 Machine Function Splitter는 profile로 cold machine basic block을 찾아 `.text.unlikely.*`로 분리하고,
linker가 여러 함수의 cold part를 함께 모을 수 있게 한다. 이는 hot footprint를 줄이는 데 유용할 수 있지만
profile이 있어야 하고, 특정 함수 시작의 DSB 최적 phase를 보장하지 않는다.
([LLVM MachineFunctionSplitter source documentation](https://www.llvm.org/docs/doxygen/MachineFunctionSplitter_8cpp_source.html))

최신 LLVM에는 temporal profile에서 startup page fault를 줄이는 function order를 만들고 LLD의
`--symbol-ordering-file`로 넘기는 절차도 있다. 문서가 명시한 목표는 **startup text page fault**이므로, 이번
steady-state 5중 Cartesian loop의 DSB/core-bound 문제를 자동 해결하는 기능으로 혼동하면 안 된다.
([LLVM `llvm-profdata order`](https://llvm.org/docs/CommandGuide/llvm-profdata.html#profdata-order),
[Clang temporal profile](https://clang.llvm.org/docs/UsersManual.html#f-temporal-profile))

### 6.4 CUBRID에서 답을 내는 compiler matrix

compiler 효과는 같은 stable host에서 다음을 분리해 봐야 한다.

| 축 | 목적 |
|---|---|
| GCC 8 A/B/D | 현재 7-byte→16-byte phase 인과 기준선 |
| GCC 16.2 A/B | 새 heuristic만으로 B/A 방향이 사라지는지 확인 |
| GCC 16.2 + representative PGO A/B | workload-aware ordering이 non-PGO보다 안정적인지 확인 |
| Clang 22.1.8 + GNU ld A/B | compiler backend 효과 확인 |
| Clang 22.1.8 + LLD A/B | linker ordering 효과까지 포함한 별도 조합 확인 |

각 조합에서 source, release flags, JDK/submodule, runtime DB/CPU set을 고정하고 final `.text`/symbol address, plan,
timing, IPC, L1I/iTLB, DSB/MITE, Top-down을 다시 기록한다. compiler와 linker를 동시에 바꾼 결과만 비교하면 어느
쪽이 phase를 바꿨는지 알 수 없다. 최신 compiler에서 B/A가 사라져도 D처럼 controlled padding phase를 한 번 더
움직여 layout 민감성 자체가 사라졌는지 확인해야 한다.

## 7. CUBRID에 권하는 단계별 실험

### 단계 A — 원인 확인, 제품 변경 없음

1. GCC 8.3.1, binutils 2.30, source, link input order를 고정한다.
2. 검증 대상 hot function 앞에만 0/8/16/24/32-byte 상당의 controlled padding variant를 만든다.
3. `nm`/`objdump`와 link map으로 function start 및 내부 hot IP의 `%32`, section 순서를 기록한다.
4. 동일 core pinning과 workload로 반복 측정하고 위의 time/PMU/Top-down/size 지표를 함께 비교한다.
5. 정렬값과 성능이 여러 재빌드에서 반복되지 않으면 alignment fix를 채택하지 않는다.

### 단계 B — 가장 좁은 완화

특정 함수 시작 phase의 효과가 재현될 때만 definition에 `aligned(32)`를 시험한다. CUBRID의 legacy `.c`가 C++로
컴파일되는 형식과 기존 GNU indent 경계를 보존하고, 함수가 inline/clone되어 별도 symbol이 사라지지 않았는지
최종 DSO에서 확인한다. 32는 관측한 DSB phase를 검증하기 위한 초기값일 뿐 universal optimum이 아니다.

### 단계 C — profile-driven 전체 배치

대표 workload 묶음을 정의할 수 있다면 instrumentation PGO를 별도 variant로 만든다. baseline과 기능/성능 QA,
`.text` 크기, exported symbols, stack/unwind/debuggability를 비교한다. AutoFDO는 production-like sample을 안정적으로
symbolize할 수 있을 때 후속 비교한다.

### 단계 D — deterministic linker layout 또는 BOLT prototype

불가피하게 특정 순서가 필요할 때만 per-function sections와 작은 `INSERT` linker script를 사용한다. 모든 명시
section 뒤에는 누락 방지 wildcard를 두고 link map에서 중복/누락을 검증한다. BOLT는 별도 prototype에서 먼저
`-fno-reorder-blocks-and-partition`, `--emit-relocs`, symbols, shared-object 지원을 검증한다.

## 8. 채택 기준

어떤 방법도 아래 조건을 모두 통과하기 전에는 “CPU-friendly 보장”으로 표현하지 않는다.

- 성능 개선이 독립 build와 반복 run에서 재현되고 confidence interval이 0을 넘는다.
- 한 microbenchmark만이 아니라 CUBRID의 대표 query/transaction/recovery workload에서 regression이 없다.
- `.text`, executable pages, L1I/iTLB, DSB/MITE, Top-down이 개선 원인과 부작용을 함께 설명한다.
- GCC/linker update 또는 unrelated source-size 변화 뒤에도 의도한 start/order가 link map과 disassembly에서 유지된다.
- release binary의 ABI, relocation, unwind, debug, strip/package 및 전체 test가 동일하게 유효하다.

현재 증거에 맞는 가장 정확한 표현은 다음이다.

> CBRD-26382에서는 작은 source 변화가 최종 hot-code 주소 phase와 CPU pipeline balance를 바꾸는 현상이 관측됐다.
> 좁은 function alignment 또는 profile-driven ordering은 이를 완화할 후보지만, 어느 것도 성능을 정적으로
> 보장하지 않는다. 최신 GCC/Clang의 profile-driven 배치 기능은 더 좋은 후보를 제공하지만, compiler 버전만
> 올렸다고 layout 민감도가 소멸하거나 historical QA slowdown이 자동 해결된다고 볼 수는 없다.
