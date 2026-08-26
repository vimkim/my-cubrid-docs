# CBRD-26382 GCC 8 전체 CUBRID 바이너리 후속 분석

- 작성일: 2026-08-26
- 대상: CUBRID PR [#6636](https://github.com/CUBRID/cubrid/pull/6636), JIRA [CBRD-26382](http://jira.cubrid.org/browse/CBRD-26382)
- 선행 분석: [`noexcept` 6개 최소 바이너리 분석](CBRD-26382-noexcept-binary-layout-analysis_codex.md)
- 상태: 전체 Rocky 8/GCC 8 빌드 완료, SQL/PMU 최종값 입력 전

## Executive summary

TBD: 최종 SQL 및 PMU 수치 입력 후 갱신한다.

현재까지 최종 ELF에서 확정된 사실은 다음과 같다.

1. `cub_server` 실행 파일 자체는 QA-2029/A/B/C 네 빌드가 SHA-256까지 완전히 같다. 서버 엔진 본체는 동적
   라이브러리 `libcubrid.so.11.5`에 있다. 따라서 이 이슈의 “최종 `cub_server` 바이너리” 분석 대상은 launcher와
   함께 이 DSO여야 한다.
2. PR 직전 A에서 PR 적용 B로 바뀌면 서버 DSO의 query hot function들이 4,080 byte 앞쪽으로 이동하고, 함수 시작의
   64-byte cache-line offset이 모두 16 byte 변한다. 이는 GCC 8 최종 link layout 변화가 실제로 존재한다는 증거다.
3. 그러나 B의 조건부 소멸자 `noexcept`를 강제 `noexcept`로만 바꾼 C는 B와 `.text` 전체, scope-exit 소멸자
   machine code, query hot function의 주소·크기·machine code가 모두 같다. 달라지는 것은 EH metadata뿐이다.
4. `log_Gl`은 A→B에서 정확히 한 page(-4,096 byte) 이동하지만 64-byte cache-line offset과 4 KiB page offset은
   그대로다. B와 C에서는 주소·크기·인접 global까지 완전히 같다. 따라서 forced `noexcept`가 `log_Gl` 배치를
   개선한다는 가설은 최종 ELF에서 성립하지 않는다.

## 1. 질문과 비교 축

QA 보고값은 trace off, CSQL 5회 평균으로 다음과 같았다.

| QA build | 평균(초) |
|---|---:|
| 11.5.0.2029 | 17.5836410 |
| 11.5.0.2031 | 19.4410452 |
| 차이 | +1.8574042 (+10.56%) |

대상 SQL은 다음과 같다.

```sql
SET TRACE OFF;
SELECT COUNT(*) FROM db_class a, db_class b, db_class c, db_class d, db_class e;
```

`.2029`와 `.2031` 사이에는 PR #6636 외에 `query_planner.c`를 바꾼 CBRD-26266도 있다. 버전 비교와 PR 인과효과를
섞지 않기 위해 전체 CUBRID를 네 상태로 빌드했다.

| label | source | 의미 |
|---|---|---|
| QA-2029 | `000a465c8fcf164d995aae005390a0af49b53a87` | 11.5.0.2029 source 재구성 |
| A | `6146cdb6aaf8708856f4b8e9f336362bb0843b2c` | PR #6636의 직전 parent, 11.5.0.2030 |
| B | `8fd3ca03e58b342a494a2f5594be23c72a822479` | PR #6636 merge, conditional destructor `noexcept`, 11.5.0.2031 |
| C | B + patch `5334c3ac...` | 소멸자 한 줄만 forced `noexcept` |

핵심 인과 비교는 다음과 같다.

- QA-2029↔B: QA가 관찰한 version delta의 source 재구성
- A↔B: PR #6636 단독 효과
- B↔C: destructor conditional↔forced `noexcept` 단독 효과

QA 배포 package의 원본 manifest와 ELF는 확보하지 못했다. 따라서 QA-2029은 tag/version source mapping에 근거한
재빌드이며, QA가 실행한 `.2029` package와 byte-identical하다고 주장하지 않는다.

## 2. 재현 환경

| 항목 | 값 |
|---|---|
| container OS | Rocky Linux 8.10 (Green Obsidian) |
| image | `localhost/cbrd26382-rocky8-gcc8:build-ready` |
| image digest | `c4da6a0898ef11f67c3c45703e4d78d4f52446e6b225004da212a0d587806cbf` |
| GCC/G++ | 8.5.0-28.el8_10 |
| linker | GNU ld 2.30-123.el8 |
| CMake/Ninja | 3.26.5 / 1.8.2 |
| Java | Rocky 8 system OpenJDK/Javac 1.8.0_504 |
| build type | `RelWithDebInfo`, `-O2 -g -DNDEBUG`, C++17 |
| host CPU | Intel Xeon Gold 5218R, 2 sockets × 20 cores × 2 threads |
| cache line | L1D/L1I 모두 64 byte |
| host kernel / perf | Rocky 9 kernel 5.14.0-570.30.1.el9_6 / perf 5.14.0 |
| source/output path | 모든 variant에서 `/src`, `/out`로 정규화 |
| compiler cache | `CCACHE_DISABLE=1`; variant 간 cache 공유 없음 |
| install prefix | `/out/CUBRID` |

별도 Temurin JDK를 내려받지 않았다. build tree의 JDK 위치는 Rocky 8 system JDK를 가리키게 했고, 실제 PL/JDBC
빌드도 `java`/`javac 1.8.0_504`로 성공했다. historical worktree에는 개인용 `justfile`이 없으므로 repository의
당시 `build.sh`를 사용했다. CM server submodule은 최종 `cub_server`와 무관하며 네 variant 모두 동일하게
`WITH_CMSERVER=OFF`로 구성했다.

각 variant는 하나씩 순서대로 별도 clean build tree에서 빌드했고, build 내부 compiler 병렬성은 허용했다.
source/submodule SHA, toolchain, CMake cache, ELF hash와 Build ID를 별도 manifest로 남겼다. 네 build의 CCI/JDBC
submodule pin도 동일하다.

## 3. workload와 측정 protocol

- 한 Rocky 8 container와 같은 DB volume을 사용하고 variant를 매회 clean start/stop하여 master/IPC 충돌을
  배제했다.
- 서버의 모든 thread는 host 물리 CPU 3,4에, CSQL은 별도 물리 CPU 5에 고정했다. 세 CPU의 sibling은 사용하지
  않았다. 세 CPU의 governor는 `performance`이고 Intel turbo는 enabled다. PMU에서 `ref-cycles`를 함께 수집해
  run 간 주파수 차이를 확인한다.
- DB는 `en_US.utf8`, 16 KiB page, 최초 128 MiB data/log volume으로 한 번 생성했다.
- 모든 variant에서 `db_class` cardinality는 49, 결과는 `49^5 = 282,475,249`여야 통과한다.
- CSQL `;time on` 값은 `db_compile_statement()` 직전부터 `db_execute_statement()` 직후까지다. 결과 formatting과
  auto-commit 시간은 제외된다.
- warm-up은 variant별 2회다. QA view는 QA-2029과 B 각각 연속 5회 평균을 보존한다.
- A/B/C는 ABC의 여섯 permutation을 두 번 배치한 12 round를 한 series로 하고 5 series를 실행한다. 즉 variant별
  60개, 총 180개의 randomized measurement다.
- 매 실행 전후 host의 `cc1plus` 수와 runnable task 수를 검사한다. 다른 대규모 병렬 빌드가 시작되면 해당
  matrix 전체를 중단·격리하고 host가 조용해진 뒤 처음부터 다시 실행한다.
- 1차 판정은 median ratio 5% 이상, paired bootstrap 95% CI가 1.0을 제외하는지, 분산과 series별 방향이
  일관적인지를 함께 본다.

QA 장비와 이 분석 host의 CPU, package, DB volume 상태는 같지 않으므로 17.58초/19.44초라는 절대시간을 맞추는
실험이 아니다. 같은 host·DB에서 재구성한 version delta의 방향과 크기, 그리고 A/B/C 인과 비교를 판정한다.

초기 pilot에서 서버의 약 300개 thread를 CPU 한 개에 강제로 몰았을 때 watchdog 재시작이 발생했다. 이어 네
container를 동시에 띄운 pilot에서는 네 `cub_master`가 소실됐다. 두 pilot은 correctness gate를 통과하지 못해
결과에서 제외하고 별도 격리했다. 또한 분석 중 출력 파일을 빠뜨린 `objcopy --dump-section`이 설치 DSO를
재작성한 사실을 hash audit로 발견했다. 해당 표본도 폐기하고 untouched build tree에서 설치본을 복원한 후 원래
manifest SHA-256과 일치함을 확인하고 최종 측정을 처음부터 다시 수행했다.

복원 후 첫 장기 측정 도중 같은 host의 다른 사용자가 80-way CUBRID 빌드를 시작해 load average가 80을 넘었고,
B 한 표본이 약 18.5초에서 37.6초로 튀었다. 외부 작업은 건드리지 않았으며 해당 matrix 69개 raw file을 별도
디렉터리에 보존하고 결과에서는 제외했다. 이 사건을 계기로 위 host-contention gate를 추가했다.

## 4. launcher와 실제 server DSO

네 `cub_server` launcher는 모두 다음과 같이 동일하다.

| artifact | 네 variant 공통 값 |
|---|---|
| SHA-256 | `53daf314c1196bbad1476b2a40865404480e1805b9061e308178a7e2369e6ecb` |
| Build ID | `6ce76c680819a8a5884966f6d503f18c56048823` |

반면 서버의 거의 모든 실행 코드는 `libcubrid.so.11.5`에 있다.

| variant | bytes | SHA-256 | Build ID |
|---|---:|---|---|
| QA-2029 | 167,446,992 | `41082753538ce970...` | `4c90a5f6f076d6858386503d99e9f49f986d8ac0` |
| A | 167,446,992 | `f40041b4c2390fa4...` | `ecab8534682d72195643ffb39965126f2425c067` |
| B | 167,377,096 | `4236464ad9d75c36...` | `cf8431c74ffef0975fb93e64bf63c128516c1a0b` |
| C | 167,376,920 | `37da8c432c6f2272...` | `9ae5c236c67c246a8b58d7a5c5e3e56e3939a758` |

QA-2029과 A의 server `.text`는 byte-identical하다. 두 source 사이의 유일한 commit은 client-side optimizer의
`query_planner.c` 변경이므로 예상과 일치한다. QA-2029/A의 DSO 전체 hash 차이는 release string 등 non-code
content를 포함한다.

## 5. PR refactor가 만든 GCC 8 layout 변화

### 5.1 직접 영향 object

`scope_exit.hpp`를 실제 server mode에서 include하는 경로는 `log_recovery_redo_parallel.cpp.o`다.

| object aggregate | A original | B conditional | C forced |
|---|---:|---:|---:|
| `.text*` | 44,582 | 43,274 | 43,274 |
| `.rodata*` | 2,412 | 1,624 | 1,624 |
| `.gcc_except_table*` | 984 | 974 | 956 |
| `.eh_frame*` | 4,696 | 4,536 | 4,560 |
| `.data*` | 604 | 508 | 508 |

A의 `scope_exit<std::function<void()>>` 소멸자는 68 byte 한 개지만 B/C는 여섯 concrete lambda specialization이
각 65 byte다. refactor의 정상 실행 경로 최적화와 object 축소는 명확하다. B→C는 object의 `.text`가 한 byte도
달라지지 않고 EH table의 분배만 달라진다.

### 5.2 최종 server DSO section

| section | A address / bytes | B address / bytes | C address / bytes |
|---|---|---|---|
| `.text` | `0x2f7000` / 8,314,404 | `0x2f6000` / 8,314,404 | B와 동일 |
| `.rodata` | `0xae4e40` / 824,499 | `0xae3e40` / 823,539 | B와 동일 address/size |
| `.eh_frame_hdr` | `0xbae2f4` / 189,052 | `0xbacf34` / 189,004 | B와 동일 |
| `.eh_frame` | `0xbdc570` / 926,768 | `0xbdb180` / 926,656 | `0xbdb180` / 926,680 |
| `.gcc_except_table` | `0xcbe9a0` / 69,014 | `0xcbd540` / 69,046 | `0xcbd558` / 69,014 |
| `.data.rel.ro` | `0xecfdc0` / 250,160 | `0xeceea0` / 250,064 | B와 동일 |
| `.data` | `0xf2c0c0` / 142,656 | `0xf2b0e0` / 142,656 | B와 동일 |
| `.bss` | `0xf4ee80` / 920,280 | `0xf4de80` / 920,280 | B와 동일 |

B→C에서 `.text`, writable data, hot symbol 주소는 동일하다. C는 B보다 `.eh_frame`이 24 byte 크고
`.gcc_except_table`이 32 byte 작아서 read/execute LOAD segment의 file size만 8 byte 작다. 이 차이는 정상 path
machine instruction의 차이가 아니다.

### 5.3 query hot function과 cache-line offset

괄호 안은 함수 시작 주소 `% 64`다.

| symbol | A address (line offset) | B address (line offset) | C |
|---|---|---|---|
| `qdata_evaluate_aggregate_list` | `0x495d00` (0) | `0x494d10` (16) | B와 동일 |
| `qexec_start_mainblock_iterations` | `0x4bb450` (16) | `0x4ba460` (32) | B와 동일 |
| `qexec_execute_mainblock` | `0x4ceb80` (0) | `0x4cdb90` (16) | B와 동일 |
| `qexec_execute_query` | `0x4dc830` (48) | `0x4db840` (0) | B와 동일 |
| `scan_next_scan_block` | `0x4fbbe0` (32) | `0x4fabf0` (48) | B와 동일 |
| `scan_next_scan` | `0x4fcba0` (32) | `0x4fbbb0` (48) | B와 동일 |

A→B에서 이 함수들은 모두 4,080 byte 앞쪽으로 이동한다. `.text` 시작 자체는 4,096 byte 앞쪽으로 이동하고,
함수의 section-relative 위치가 16 byte 뒤로 바뀐 결과다. 반면 B/C의 각 함수는 size뿐 아니라 raw function byte
SHA-256도 동일하다. 여섯 concrete `scope_exit` 소멸자의 주소(`0x732a20`부터), 크기(각 65 byte), disassembly도
B/C에서 완전히 같다.

A/B에서는 위 여섯 hot function의 raw byte SHA-256이 모두 달라진다. source가 같아도 외부 target까지의 상대
변위와 alignment가 바뀌면 instruction encoding byte가 달라질 수 있으므로, hash 차이 자체를 실행 로직 차이로
해석하지는 않는다. 중요한 대조군은 final address와 raw byte가 모두 동일한 B/C다.

runtime mapping의 executable DSO base는 모든 실행에서 2 MiB 정렬이었다. 따라서 ASLR이 바꾼 absolute base를
더해도 위 `% 64` offset은 그대로 유지된다.

## 6. `log_Gl` global-data 가설

| variant | `log_Gl` address | size | `% 64` | `% 4096` |
|---|---:|---:|---:|---:|
| A | `0x1003cc0` | 1,360 (`0x550`) | 0 | `0xcc0` |
| B | `0x1002cc0` | 1,360 (`0x550`) | 0 | `0xcc0` |
| C | `0x1002cc0` | 1,360 (`0x550`) | 0 | `0xcc0` |

A→B에서는 `log_Gl`과 주변 큰 path buffer들이 모두 정확히 -4,096 byte 이동한다. cache line 안 위치와 page 안
위치는 변하지 않는다. B/C에서는 다음 이웃까지 동일하다.

```text
0x1001cc0 log_Path          size 0x1000
0x1002cc0 log_Gl            size 0x0550
0x1003220 log_Clock_msec    size 0x0008
0x1003228 cdc_Logging       size 0x0001
0x1003240 cdc_Gl            size 0x8308
```

`noexcept`는 `log_global` 구조에 field를 추가하지 않는다. B→C가 writable segment와 `.bss` symbol layout을 전혀
바꾸지 않았으므로 “forced `noexcept`가 `log_Gl`의 cache-line miss를 개선한다”는 설명은 이 빌드에서는 기각된다.
A→B의 text hot-function offset 변화는 실제이므로 instruction/front-end layout 가설은 PMU로 별도 검증한다.

## 7. client optimizer 분리

QA-2029→A의 CBRD-26266은 `qo_plan_compute_iscan_sort_list()`만 바꾸며 function-based multi-column index의
ORDER BY skip을 지원한다. 대상 SQL에는 index나 ORDER BY가 없다.

- `libcubridcs.so.11.5`의 `.text` 전체 크기는 QA-2029/A 모두 7,879,988 byte다.
- 변경 함수는 실제 symbol 기준 1,781 (`0x6f5`)→1,672 (`0x688`) byte로 줄었다.
- 뒤의 `qo_planner_search()` 주소는 `0x4890c0`→`0x489050`, 즉 112 byte 이동한다.
- A/B/C의 client `.text`는 서로 byte-identical하다. B/C client DSO의 차이는 build timestamp와 Build ID 등
  non-code byte뿐이다.

CSQL 시간에는 compile과 execute가 모두 포함되므로 최종 SQL 표에서는 QA-2029↔A도 표시한다. 다만 18–20초
server workload에서 이 ORDER BY 전용 client diff를 곧바로 원인으로 해석하지 않고 plan과 server PMU를 확인한다.

## 8. SQL 결과

TBD: QA 5회, A/B/C 60회 요약, bootstrap CI, series 방향, plan hash를 입력한다.

## 9. PMU와 hot profile

TBD: cycles/ref-cycles/instructions/IPC/branches/cache/front-end counters, time-running, perf report를 입력한다.

주소 변화는 cache miss의 증명이 아니다. cache-line 가설은 PMU에서 instruction 수가 같은데 cycle/IPC 및
front-end/cache event가 일관되게 달라지는지까지 확인한 뒤 판정한다.

## 10. 결론

TBD: 최종 수치에 근거해 다음 세 문장을 확정한다.

1. PR #6636이 normalized GCC 8 build에서 SQL을 빠르게/느리게 했는가?
2. forced destructor `noexcept` C가 B를 개선했는가?
3. QA의 2029→2031 +10.56%와 같은 방향을 재현했는가?

현재 ELF만으로는 다음은 이미 확정할 수 있다.

- forced `noexcept`는 B와 C의 query code 배치를 전혀 바꾸지 않았으므로 이 full build의 성능 수정책이 아니다.
- GCC 8에서 PR refactor가 final link layout을 바꾸는 현상은 실제다. 이것은 compiler optimization failure의
  증명이라기보다 object/EH/dynamic symbol 축소가 GNU ld 배치로 전파된 결과다.
- `log_Gl`의 unlucky cache-line 배치는 B/C 차이를 설명하지 못한다.
- QA 원인을 확정하려면 QA가 실제 사용한 `.2029`/`.2031` package의 `libcubrid.so.11.5`, `libcubridcs.so.11.5`,
  Build ID와 CPU counter를 같은 장비에서 비교해야 한다. source 재빌드의 주소 방향은 배포 package와 달라질 수
  있다.

## Reproducibility artifacts

TBD: commit에 포함할 compact artifact 링크를 입력한다.

전체 build tree와 raw ELF는 크기 때문에 Git에 넣지 않는다. local evidence root는
`/home/vimkim/gh/cb/cbrd-26382-results`이며, report artifact에는 source/toolchain manifest, C patch, timing CSV,
PMU CSV, hot-symbol/section summary와 재현 script를 포함한다.
