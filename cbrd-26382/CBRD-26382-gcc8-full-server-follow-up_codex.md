# CBRD-26382 GCC 8 전체 CUBRID 바이너리 후속 분석

- 작성일: 2026-08-26
- 대상: CUBRID PR [#6636](https://github.com/CUBRID/cubrid/pull/6636), JIRA [CBRD-26382](http://jira.cubrid.org/browse/CBRD-26382)
- 선행 분석: [`noexcept` 6개 최소 바이너리 분석](CBRD-26382-noexcept-binary-layout-analysis_codex.md)
- 상태: stable-PC 재현·PMU·final ELF 분석 완료

## Executive summary

QA와 같은 build 계열을 복원하자 slowdown 방향이 재현됐다. 최신 `cubridci/cubridci:develop`의 CentOS 6.10 +
devtoolset-8 GCC 8.3.1에서 repository `./build.sh -m release ... build`를 명시 실행했고, 네 CMake cache 모두
`RelWithDebInfo`와 `-O2 -g -DNDEBUG`를 확인했다. 이 바이너리를 Rocky 8에서 실행한 stable-PC 결과는 다음과 같다.

1. QA-2029과 B 각 20개 표본을 합치면 B는 평균 `+1.464%` 느렸고 100,000회 bootstrap 95% CI는
   `+1.039% ~ +1.899%`다. QA 장비의 `+10.56%`보다 작지만 방향과 통계적 분리는 재현했다.
2. query 구간의 physical `read_bytes`와 major fault는 40/40 모두 0이었다. 시간과 server migration 횟수의 상관도
   `r=0.085`에 불과하다. 이 workload의 stable-PC 차이는 disk나 CPU migration이 아니라 CPU 실행 쪽이다.
3. A/B PMU central group을 5회로 늘리자 IPC는 B에서 매번 낮았고 평균 `-1.519%`, core-group query time은
   `+1.832%`였다. MITE µop/query는 `+12.664%`, host perf의 DSB→MITE penalty 신호는 `+71.729%`로 공급 경로가
   바뀌었다. 그러나 Top-down은 front-end bound가 `5.73%→3.85%`로 감소하고 core bound가
   `10.58%→13.48%`로 증가했다고 분류한다. 따라서 DSB/MITE 변화는 관찰된 동반 현상이지 slowdown 단독 원인으로
   확정할 수 없다.
4. 실제 cycle profile의 최대 hot function은 `qexec_execute_scan`(약 25–27%)이다. A→B에서 이 함수와 다른 query
   hot function은 모두 16 byte 앞쪽으로 이동해 시작 주소 `%64`가 바뀐다. B와 C의 hot 주소와 raw bytes는 같다.
5. forced destructor `noexcept` C는 B의 hot-code layout을 되돌리지 못했고 B/C timing 방향도 일관되지 않았다.
   조건부 `noexcept` 한 줄과 `log_Gl` 배치는 수정점이 아니다. PR 전체 refactor가 만든 final-link phase 변화가
   현재 가장 강한 원인 후보이며, 더 오래된 QA CPU/RAM 계층에서 비용이 크게 증폭됐다는 해석이 증거에 맞는다.

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
| build image | `docker.io/cubridci/cubridci:develop` |
| resolved image ID | `3f5731ae2f0b...f94168ba` |
| repository digest | `sha256:3a6f53a2...63a157` |
| build container OS | CentOS 6.10 (Final), glibc 2.12 |
| GCC/G++ | devtoolset-8 8.3.1-3 |
| linker | GNU ld 2.30-55.el6.2 |
| CMake/Ninja | 3.26.3 / 1.11.1 |
| Java | Temurin OpenJDK/Javac 1.8.0_442 |
| build type | `RelWithDebInfo`, `-O2 -g -DNDEBUG`, C++17 |
| build command | `./build.sh -m release -s /src -b /out/build -p /out/CUBRID -j /opt/jdk8 build` |
| runtime OS | Rocky Linux 8.10 container |
| stable host CPU | Intel Core Ultra 7 270K Plus, 1 socket, 24 physical cores, SMT 없음 |
| measured CPU set | P-core `0-7`; 단일 CPU 고정 없이 migration 허용 |
| stable host storage | SHPP41-1000GM NVMe, XFS |
| host kernel / perf | Fedora 44 kernel 7.1.8 / perf 7.1.10 |
| source/output path | 모든 variant에서 `/src`, `/out` |
| compiler cache | image의 `ccache gcc` wrapper, `CCACHE_DISABLE=1` |
| install prefix | `/out/CUBRID` |

2025년 11월 대상 source의 CircleCI와 Jenkinsfile은 모두 `cubridci/cubridci:develop`과
`scl enable devtoolset-8 -- /entrypoint.sh build`를 사용한다. 현재 `develop` tag는 mutable이므로 당시 image digest와
같다고 주장하지 않는다. 다만 현재 image를 직접 검사한 OS/compiler/userspace와 repository build 경로는 QA CI
계열과 일치한다. image entrypoint의 최근 default mode 변경 가능성을 피하려고 `-m release`를 명시했으며,
`CMakeCache.txt`로 `RelWithDebInfo`를 사후 검증했다.

CM server source가 없는 warning은 있었지만 DB engine/JDBC/PL/CCI build와 install은 정상 완료됐다. QA/A/B/C의
CCI/JDBC submodule pin은 같고, `cubrid-cci/win/cci_version.h`가 build number로 바뀌는 것은 `build.sh`의 정상 생성
동작으로 취급했다. 빌드 입력과 결과는 [`stable-pc-cubridci/manifests/`](artifacts/full-server-gcc8/stable-pc-cubridci/manifests/)에
남겼다.

## 3. workload와 측정 protocol

- SQL은 `SELECT COUNT(*) FROM db_class a, ... db_class e`이며 결과 `49^5 = 282,475,249`를 매번 검사했다.
- 한 Rocky 8 runtime container, 한 DB volume을 공유하되 variant를 매회 clean start/stop했다.
- QA가 CPU pinning을 쓰지 않았다는 조건을 반영해 단일 CPU pinned matrix를 중단했다. 다만 stable host는 P/E
  hybrid이므로 E-core 성능 차이를 섞지 않기 위해 server의 모든 thread와 CSQL이 P-core `0-7` 안에서 자유롭게
  migrate하도록 했다.
- 첫 QA/B 교차는 QA 5회→B 5회→B 5회→QA 5회다. 이어 QA/A/B/C forward와 C/B/A/QA reverse를 다섯 번
  반복해 variant별 10개를 수집했다.
- 두 번째 matrix는 query 전후 `/proc/<pid>/task/*/sched`, `/proc/<pid>/io`, `/proc/<pid>/stat`을 읽어 migration,
  context switch, physical I/O, fault, CPU tick을 함께 기록했다.
- PMU는 variant마다 core/branch/cache/L1D/LLC/iTLB/L1I/front-end/DSB-MITE 그룹을 별도 실행했다. 최초에는
  central group 2회, 나머지 1회였고, 결론 검증을 위해 A/B central group을 5회로 늘리고 Top-down L1/L2도
  A/B 각 5회 추가했다. 최종 raw matrix는 110 run이다. counter multiplexing을 줄이기 위해 group별 query를
  분리했고 `perf record -F 999` cycle profile도 각 variant 한 번 수집했다.
- 네 variant의 normalized plan hash는 모두 `fdfb8ef0a1e966dae644de819aaffbca74602dc028f0262729e07a55d8d77844`다.

이 stable PC는 QA 장비보다 CPU/RAM/storage가 훨씬 새롭다. 따라서 17.58초/19.44초라는 절대시간을 맞추는 것이
아니라 같은 host·DB에서 version delta의 방향, PR 인과 비교, microarchitectural counter 방향을 판정한다.
앞선 shared host의 Rocky 8/GCC 8.5 single-CPU 180개 matrix는 B/A가 10.28% 빠른 반대 방향이었고 외부 compiler
오염도 반복됐다. 그 결과는 환경 민감성을 보여주는 control로만 보존하고 최종 판정에는 사용하지 않는다.

## 4. launcher와 실제 server DSO

네 `cub_server` launcher는 모두 다음과 같이 동일하다.

| artifact | 네 variant 공통 값 |
|---|---|
| `cub_server` SHA-256 | `0cbcf122985652fde4ec8584798fca532efa33fabbbe35f63d4ea1b7603f1309` |
| `cub_server` Build ID | `d101e3d560f2f0fda7856779616a1e07997a15e9` |
| `csql` SHA-256 | `c8cdf3dc23c45b31db1b347ffdb5fef47cf953b9609aeb6980bc93c962691405` |

반면 서버의 거의 모든 실행 코드는 `libcubrid.so.11.5`에 있다.

| variant | bytes | SHA-256 | Build ID |
|---|---:|---|---|
| QA-2029 | 177,505,504 | `b20aec6c76dd06b1...` | `8b84c6421a03b613a577e9becf1c39bcc371f406` |
| A | 177,505,504 | `1da0f882f69e5577...` | `6050500a42714e509d280db079852b78bb4e919a` |
| B | 177,432,760 | `a0d109bd4b288d04...` | `b6a93b756c7686a45ce61afcd989d9f499d7847d` |
| C | 177,432,896 | `6cfa8b0cf56b2e29...` | `ffd17fbe49c230539a23af96bc35e9d2d922f6a7` |

QA-2029과 A의 server `.text`는 byte-identical하다. 두 source 사이의 유일한 commit은 client-side optimizer의
`query_planner.c` 변경이므로 예상과 일치한다. QA-2029/A의 DSO 전체 hash 차이는 release string 등 non-code
content를 포함한다.

## 5. PR refactor가 만든 GCC 8 layout 변화

### 5.1 직접 영향 object

`scope_exit.hpp`를 실제 server mode에서 include하는 경로는 `log_recovery_redo_parallel.cpp.o`다.
다음 object aggregate는 선행 Rocky 8/GCC 8.5 control에서 얻은 값이며, refactor가 축소하는 section의 종류를
설명하기 위해 보존한다.

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
| `.text` | `0x2f4000` / `0x80c310` | A와 동일 | A와 동일 |
| `.rodata` | `0xb00340` / `0xc8475` | `0xb00340` / `0xc80b5` | B와 동일 |
| `.eh_frame_hdr` | `0xbc87b8` / `0x2edbc` | `0xbc83f8` / `0x2ed84` | B와 동일 |
| `.eh_frame` | `0xbf7578` / `0xe6408` | `0xbf7180` / `0xe6360` | `0xbf7180` / `0xe6378` |
| `.gcc_except_table` | `0xcdd980` / `0x1155d` | `0xcdd4e0` / `0x11579` | `0xcdd4f8` / `0x11555` |
| `.data.rel.ro` | `0xeefa40` / `0x3d470` | `0xeefb20` / `0x3d410` | B와 동일 |
| `.data` | `0xf4c5a0` / `0x22a60` | `0xf4c5e0` / `0x22a60` | B와 동일 |
| `.bss` | `0xf6f080` / `0xe09f8` | `0xf6f100` / `0xe09f8` | B와 동일 |

B→C에서 `.text`, `.rodata`, writable data, hot symbol 주소는 동일하다. C는 B보다 `.eh_frame`이 24 byte 크고
`.gcc_except_table`이 36 byte 작다. 이 차이는 정상 path machine instruction의 차이가 아니다.

### 5.3 query hot function과 cache-line offset

괄호 안은 함수 시작 주소 `% 64`다.

| symbol | A address (line offset) | B address (line offset) | C |
|---|---|---|---|
| `qexec_execute_scan` | `0x4db580` (0) | `0x4db570` (48) | B와 동일 |
| `fetch_val_list` | `0x47aa10` (16) | `0x47aa00` (0) | B와 동일 |
| `qdata_evaluate_aggregate_list` | `0x49aee0` (32) | `0x49aed0` (16) | B와 동일 |
| `qexec_start_mainblock_iterations` | `0x4c0670` (48) | `0x4c0660` (32) | B와 동일 |
| `qexec_execute_mainblock` | `0x4d3f20` (32) | `0x4d3f10` (16) | B와 동일 |
| `qexec_execute_query` | `0x4e1b40` (0) | `0x4e1b30` (48) | B와 동일 |
| `scan_next_scan_block` | `0x500f30` (48) | `0x500f20` (32) | B와 동일 |
| `scan_next_scan` | `0x501ef0` (48) | `0x501ee0` (32) | B와 동일 |

stable `cubridci` build에서는 `.text` section 시작과 크기는 같지만 A→B의 query hot function들이 모두 16 byte
앞쪽으로 이동한다. B/C의 각 함수는 size뿐 아니라 raw function byte SHA-256도 동일하다. 앞선 Rocky control은
4,080 byte 이동이었으므로 이동량 자체는 toolchain/build graph에 민감하지만, 두 build 모두 hot 시작의 `%64`가
정확히 16 byte 변한다.

A/B에서는 위 hot function의 raw byte SHA-256이 모두 달라진다. source가 같아도 외부 target까지의 상대
변위와 alignment가 바뀌면 instruction encoding byte가 달라질 수 있으므로, hash 차이 자체를 실행 로직 차이로
해석하지는 않는다. 중요한 대조군은 final address와 raw byte가 모두 동일한 B/C다.

runtime mapping의 executable DSO base는 모든 실행에서 2 MiB 정렬이었다. 따라서 ASLR이 바꾼 absolute base를
더해도 위 `% 64` offset은 그대로 유지된다.

## 6. `log_Gl` global-data 가설

| variant | `log_Gl` address | size | `% 64` | `% 4096` |
|---|---:|---:|---:|---:|
| A | `0x1023e80` | 1,360 (`0x550`) | 0 | `0xe80` |
| B | `0x1023f00` | 1,360 (`0x550`) | 0 | `0xf00` |
| C | `0x1023f00` | 1,360 (`0x550`) | 0 | `0xf00` |

A→B에서는 `log_Gl`과 주변 global이 모두 128 byte 이동하지만 cache-line 시작 위치 `%64=0`은 유지된다.
B/C에서는 다음 이웃까지 동일하다.

```text
0x1022f00 log_Path          size 0x1000
0x1023f00 log_Gl            size 0x0550
0x1024460 log_Clock_msec    size 0x0008
0x1024468 cdc_Logging       size 0x0001
0x1024480 cdc_Gl            size 0x8308
```

`noexcept`는 `log_global` 구조에 field를 추가하지 않는다. B→C가 writable segment와 `.bss` symbol layout을 전혀
바꾸지 않았으므로 “forced `noexcept`가 `log_Gl`의 cache-line miss를 개선한다”는 설명은 이 빌드에서는 기각된다.
A→B의 text hot-function offset과 CPU pipeline 통계가 함께 변하고 B/C hot code는 동일하므로 final-code layout이
data-global 가설보다 우선한다. 다만 확장 Top-down은 slowdown 증가분을 front-end가 아닌 core-bound로 분류하므로
DSB/MITE만을 원인으로 단정하지 않는다.

## 7. client optimizer 분리

QA-2029→A의 CBRD-26266은 `qo_plan_compute_iscan_sort_list()`만 바꾸며 function-based multi-column index의
ORDER BY skip을 지원한다. 대상 SQL에는 index나 ORDER BY가 없다.

- `libcubridcs.so.11.5`의 `.text` 전체 크기는 네 variant 모두 8,028,992 byte다.
- 변경 함수는 실제 symbol 기준 1,781 (`0x6f5`)→1,672 (`0x688`) byte로 줄었다.
- 뒤의 `qo_planner_search()` 주소는 `0x4890c0`→`0x489050`, 즉 112 byte 이동한다.
- A/B/C의 client `.text`는 서로 byte-identical하다. B/C client DSO의 차이는 Build ID/EH/debug 등
  non-code byte뿐이다.

CSQL 시간에는 compile과 execute가 모두 포함되므로 최종 SQL 표에서는 QA-2029↔A도 표시한다. 다만 이 ORDER BY
전용 client diff를 대상 SQL의 원인으로 해석하지 않으며, 실제 plan과 server PMU도 같은 결론을 지지한다.

## 8. SQL 결과

QA/B 전용 교차와 QA/A/B/C I/O matrix를 합친 값이다.

| variant | n | mean (s) | median (s) | stdev (s) |
|---|---:|---:|---:|---:|
| QA-2029 | 20 | 4.756998 | 4.742648 | 0.033418 |
| B | 20 | 4.826650 | 4.808150 | 0.034005 |

B/QA mean ratio는 `1.014642` (`+1.464%`)이고 100,000회 unpaired bootstrap 95% CI는
`[1.010386, 1.018989]`, 즉 `+1.039% ~ +1.899%`다. QA의 `+10.56%`보다 작지만 slowdown 방향과 1.0을 넘는
구간을 stable PC에서 재현했다.

네 variant I/O matrix의 10개 표본은 다음과 같다.

| variant | mean (s) | median (s) | min–max (s) |
|---|---:|---:|---:|
| QA-2029 | 4.764648 | 4.760149 | 4.722147–4.821150 |
| A | 4.847351 | 4.727647 | 4.718147–5.840182 |
| B | 4.837151 | 4.810650 | 4.799150–4.894152 |
| C | 4.867651 | 4.881652 | 4.803150–4.893152 |

A의 5.840182초 한 건은 CPU tick도 590으로 같이 증가한 명백한 host/frequency outlier여서 raw mean을 오염시킨다.
raw file은 삭제하지 않았다. median 기준 B/A는 `+1.756%`, C/A는 `+3.258%`다. 반면 C/B는 이 matrix에서
`+1.476%`, 별도 PMU core 2회 평균에서는 `-0.723%`로 방향이 뒤집힌다. B/C의 hot `.text`가 동일하다는 ELF
증거까지 합치면 forced `noexcept`가 개선한다는 근거는 없다.

I/O matrix 40/40에서 `read_bytes=0`, major fault=0이었다. 시간과 migration 횟수의 Pearson 상관은 `0.085`다.
context-switch count와 시간은 함께 늘지만 이는 더 오래 실행된 process가 더 많은 switch를 누적하는 관계다.
NVMe와 QA의 오래된 SATA/HDD 차이는 server 시작 절대시간에는 영향을 줄 수 있어도 측정된 query regression의
직접 원인은 아니다. 네 normalized plan hash와 cardinality도 같다.

## 9. PMU와 hot profile

초기 2회에서 크게 보인 DSB miss를 재검증하기 위해 A/B central group을 5회까지 늘렸다. 횟수 자체가 같은
workload이므로 공급량은 `/s`가 아니라 query당 raw count로 비교했다.

| metric | A | B | B/A |
|---|---:|---:|---:|
| query seconds (core group) | 4.780355 | 4.867951 | +1.832% |
| IPC | 7.018736 | 6.912118 | **-1.519%** |
| effective GHz | 5.428241 | 5.412624 | -0.288% |
| L1I load misses/query | 5.302M | 5.503M | +3.783% |
| retired DSB misses/query | 3.462M | 3.841M | +10.923% |
| DSB uops/query | 173.433B | 173.365B | -0.039% |
| MITE uops/query | 37.231M | 41.946M | **+12.664%** |
| host-perf DSB→MITE penalty cycles/query | 9.577M | 16.446M | **+71.729%** |

IPC는 A 최저값도 B 최고값보다 높아 5/5로 분리됐다. 반면 retired DSB miss는 A 한 run의 큰 outlier 때문에 최초
2회 `+52.819%`에서 5회 `+10.923%`로 줄었고 분산도 크다. 현재 host perf가 노출한
`DSB2MITE_SWITCHES.PENALTY_CYCLES`는 count됐지만 Intel Arrow Lake P-core online event 표에 같은 이름이 없어
보조 신호로만 사용한다.

전체 pipeline의 병목 위치를 확인하기 위해 Top-down L1/L2도 A/B 각 5회 수집했다.

| Top-down slot ratio | A | B | B-A |
|---|---:|---:|---:|
| Retiring | 82.27% | 81.02% | -1.25%p |
| Front-end bound | 5.73% | 3.85% | -1.88%p |
| Back-end bound | 11.14% | 14.27% | **+3.13%p** |
| Bad speculation | 0.87% | 0.94% | +0.08%p |
| Memory bound | 0.792% | 0.791% | 거의 동일 |
| Core bound | 10.58% | 13.48% | **+2.90%p** |

B의 front-end bound는 오히려 줄고 core bound가 증가했다. 따라서 16-byte phase와 DSB/MITE 공급 변화는 실제지만
그 변화만으로 slowdown을 설명하지 않는다. 현재의 정확한 분류는 memory가 아닌 execution-core pressure 증가다.
주소 phase가 공급 timing과 downstream port/scheduler 압력까지 어떻게 바꿨는지는 padding sweep과 instruction-IP
귀속이 필요한 마지막 가설이다.

일반 branch miss, cache miss, L1D/LLC miss는 1회씩만 수집했고 A/B 차이가 작은 run noise 범위였다. P-core에서
`cpu_core` event가 count됐고 `cpu_atom` event의 not-counted 표시는 의도한 affinity의 결과다. 전체 counter
time-running 중앙값은 100%다.

cycle profile에서 0.5% 이상 address point를 source symbol로 다시 합산한 상위 경로는 다음과 같다.

| function | QA-2029 | A | B | C |
|---|---:|---:|---:|---:|
| `qexec_execute_scan` | 26.70% | 25.70% | 25.12% | 26.29% |
| `fetch_val_list` | 12.33% | 12.73% | 13.82% | 13.40% |
| `scan_next_list_scan` | 9.13% | 8.95% | 8.18% | 8.99% |
| `qdata_evaluate_aggregate_list` | 7.43% | 7.75% | 7.16% | 8.11% |

profile은 workload가 실제로 16-byte phase가 바뀐 query executor/scan loop에서 시간을 쓴다는 연결 증거다.
PMU와 layout을 합치면 final-link phase가 CPU pipeline balance를 바꾼다는 설명은 지지되지만, DSB/MITE가 wall
time의 단독 원인이라는 설명은 확장 측정으로 기각된다. 현재 CPU는 QA CPU가 아니므로 정확한 `+10.56%` 배율까지
외삽하지 않는다. 쉬운 인과 설명과 증거 경계는
[`scope_exit`→CPU pipeline 문서](CBRD-26382-scope-exit-frontend-causal-chain_codex.md)에 별도로 정리했다.

## 10. 결론

1. 최신 `cubridci` CentOS 6/devtoolset-8 release build를 Rocky 8에서 실행하면 B/QA slowdown 방향이 재현된다.
   stable PC의 크기는 `+1.464%`이고 QA의 `+10.56%`보다는 작다.
2. A→B PR 단독 비교도 timing과 PMU에서 느린 방향이다. IPC 하락과 MITE 공급 증가는 관찰됐지만 Top-down은
   손실 증가분을 front-end가 아닌 execution core bound로 분류했다.
3. forced destructor `noexcept`는 B와 C의 hot code 주소·bytes를 바꾸지 않고 성능 개선 방향도 일관되지 않다.
   이 한 줄은 수정책이 아니다.
4. `log_Gl`은 size와 cache-line offset이 유지되고 B/C가 동일하다. data-global 배치 가설보다 query `.text`의
   16-byte phase 변화가 증거에 맞는다.
5. query physical I/O는 0이므로 QA의 느린 storage는 이번 SQL delta의 직접 설명이 아니다. 더 오래된 CPU의
   address-sensitive pipeline/cache 구조가 같은 layout 차이를 크게 증폭했을 가능성은 있지만 아직 측정하지 않았다.
6. historical `cubridci:develop` digest와 QA 원본 package ELF/PMU가 없으므로 정확한 `+10.56%`의 전부를 단정하지
   않는다. 다만 “재현 불가” 상태에서는 벗어났고, slowdown 방향과 final-link/pipeline 변화는 stable PC에서
   연결했다. 마지막 hardware resource의 인과 확정에는 padding sweep과 PEBS가 필요하다.

## Reproducibility artifacts

compact evidence는 [`stable-pc-cubridci/`](artifacts/full-server-gcc8/stable-pc-cubridci/)에 있다. build provenance,
네 manifest, raw timing/I/O CSV, bootstrap summary, 110 PMU run의 counter와 query time, hot symbol/hash, normalized
plan hash, address-resolved profile summary를 포함한다. 실행 script는
[`scripts/`](artifacts/full-server-gcc8/scripts/)에 있다.

전체 build tree, raw ELF, `perf.data`는 크기 때문에 Git에 넣지 않는다. local evidence root는
`/home/vimkim/gh/cb/cbrd-26382-results-cubridci`다. installed ELF에는 `objcopy`를 적용하지 않았고 section byte
hash는 `dd`로 읽기만 했다.
