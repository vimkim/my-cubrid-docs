# CBRD-26382 stable-PC reproduction handoff

- 작성일: 2026-08-26
- 대상: CUBRID PR [#6636](https://github.com/CUBRID/cubrid/pull/6636), JIRA [CBRD-26382](http://jira.cubrid.org/browse/CBRD-26382)
- 목적: 새 에이전트가 더 안정적인 전용 PC에서 QA의 11.5.0.2029→2031 slowdown을 우선 재현하고, final ELF와
  CPU front-end/cache counter까지 연결해 원인을 판정한다.
- 중요: 이 문서는 완료 보고서가 아니라 실행 handoff다. 현재 공유 host에서 나온 “B가 빠름”을 정답으로
  가정하지 말고 QA가 보고한 반대 방향을 독립적으로 재현해야 한다.

## 1. Mission

다음 세 질문을 서로 분리해 답한다.

1. QA가 사용한 build/package 조건에서 `.2029` 17.58초→`.2031` 19.44초 slowdown을 재현할 수 있는가?
2. 재현된다면 PR #6636 자체(A→B)가 원인인가, `.2029`→A 사이의 CBRD-26266 또는 package 차이인가?
3. conditional destructor `noexcept`를 forced `noexcept`로 바꾼 C가 B의 final code/layout/counter/latency를 실제로
   개선하는가?

최우선 성공 조건은 **QA slowdown 방향 재현**이다. 현재 host의 normalized rebuild 결과만 다시 반복하고 종료하면
안 된다.

### Portability boundary

이 문서가 처음 게시될 때 origin host의 `.scratch`, worktree, result directory와 tracker ID를 portable artifact처럼
표현한 오류가 있었다. 다음을 명확히 구분한다.

- **Git으로 전달됨**: 이 문서, WIP full-server 보고서, Wayfinder map/context/issues, build manifests, container
  metadata/RPM list, C patch, timing/layout evidence, 재현 scripts
- **전달되지 않음**: origin host의 네 worktree directory, 약 160 MiB인 각 unstripped ELF, build tree, raw log,
  container image layer, work-tracker SQLite row
- worktree는 commit에서 재생성하고, ELF/build/raw evidence는 안정 PC에서 새로 만든다. origin host의 대용량
  artifact가 꼭 필요할 때만 별도 전송한다.
- work-tracker ID는 host-local이다. 안정 PC에 item 30이 없는 것이 정상이며 새 local item을 생성한다.

## 2. Read first

Git checkout에서 다음 파일이 portable authoritative state다.

| 경로 | 내용 |
|---|---|
| `cbrd-26382/CBRD-26382-stable-pc-handoff_codex.md` | 이 실행 handoff |
| `cbrd-26382/CBRD-26382-gcc8-full-server-follow-up_codex.md` | WIP 최종 보고서; `TBD`가 남아 있으므로 그대로 최종 게시/JIRA 인용 금지 |
| `cbrd-26382/artifacts/full-server-gcc8/wayfinder/` | Wayfinder map, context, issue 01–04 |
| `cbrd-26382/artifacts/full-server-gcc8/manifests/` | origin build의 네 compact manifest와 CMake cache |
| `cbrd-26382/artifacts/full-server-gcc8/container/` | image metadata/history, RPM NEVRA list, fallback Containerfile |
| `cbrd-26382/artifacts/full-server-gcc8/scripts/` | worktree 준비, build, timing, plan, PMU, 분석 scripts |
| `cbrd-26382/artifacts/full-server-gcc8/*.csv`, `*.json` | compact layout/timing evidence |
| `cbrd-26382/artifacts/full-server-gcc8/SHA256SUMS` | portable artifact 79개의 무결성 목록 |

Origin host에만 있던 `/home/vimkim/gh/cb/cbrd-26382-results`와 `.scratch` 경로는 Git checkout의 전제조건이
아니다. portable copy는 위 artifact directory에 포함됐다.

선행 minimal-binary GCC 8/GCC 11 분석은 commit
`aa9f8d226a9cc2bc6725fd14f92814859cabf2b2`의
[`CBRD-26382-noexcept-binary-layout-analysis_codex.md`](https://github.com/vimkim/my-cubrid-docs/blob/aa9f8d226a9cc2bc6725fd14f92814859cabf2b2/cbrd-26382/CBRD-26382-noexcept-binary-layout-analysis_codex.md)에 있다.

## 3. Source matrix

| label | origin-host worktree 예시 | commit/patch | 의미 |
|---|---|---|---|
| QA-2029 | `/home/vimkim/gh/cb/scope-exit-QA-2029` | `000a465c8fcf164d995aae005390a0af49b53a87` | 11.5.0.2029 source 재구성 |
| A | `/home/vimkim/gh/cb/scope-exit-A` | `6146cdb6aaf8708856f4b8e9f336362bb0843b2c` | PR #6636 직전 parent, original `std::function` scope-exit |
| B | `/home/vimkim/gh/cb/scope-exit-B` | `8fd3ca03e58b342a494a2f5594be23c72a822479` | PR #6636, conditional `noexcept` |
| C | `/home/vimkim/gh/cb/scope-exit-C` | B + `scope-exit-C.patch` | destructor만 unconditional `noexcept` |

C patch SHA-256은 `5334c3ac928329e16c891d8ab491e691c549e36cc448d774755dc555c1bace39`다. C는 새 commit을
만들지 않아 version string이라는 confounder를 추가하지 않았다.

worktree directory 자체는 전달하지 않는다. Canonical CUBRID clone과 artifact root를 인자로 다음 script를 실행해
네 worktree와 submodule을 재생성한다.

```bash
cbrd-26382/artifacts/full-server-gcc8/scripts/prepare-worktrees.sh \
  /path/to/cubrid-clone \
  /path/to/worktree-root \
  /path/to/my-cubrid-docs/cbrd-26382/artifacts/full-server-gcc8
```

비교 축:

- QA-2029↔B: QA numeric version delta 재구성. CBRD-26266과 PR #6636을 모두 포함한다.
- A↔B: PR #6636만 격리한다.
- B↔C: destructor exception specification만 격리한다.

Archived QA package manifest는 아직 없다. `000a465c8`은 build-number mapping에 근거한 source reconstruction이며
QA가 실행한 `.2029` package와 byte-identical하다고 주장하면 안 된다.

## 4. Current build provenance

현재 네 build는 모두 historical repository의 `build.sh` action으로 만들었다. CMake를 직접 호출하거나 `just`를
사용하지 않았다.

```bash
./build.sh -m release -C gcc -g ninja \
  -s /src \
  -b /out/build \
  -p /out/CUBRID \
  -j /usr/lib/jvm/java-1.8.0-openjdk-1.8.0.504.b01-1.1.el8_10.x86_64 \
  -c "-DWITH_CMSERVER=OFF" \
  build
```

`run-build.sh` 전체는 artifact의 `scripts/`에 있다. 네 variant의 cache에서 확인한 실제 값:

| 항목 | 값 |
|---|---|
| container | Rocky Linux 8.10 |
| image | `localhost/cbrd26382-rocky8-gcc8:build-ready` |
| image ID | `c4da6a0898ef11f67c3c45703e4d78d4f52446e6b225004da212a0d587806cbf` |
| GCC/G++ | 8.5.0-28.el8_10 |
| Java | Rocky system OpenJDK/Javac 1.8.0_504; 별도 JDK download 없음 |
| CMake/Ninja/ld | 3.26.5 / 1.8.2 / GNU ld 2.30 |
| build mode | `-m release`가 이 historical tree에서 `RelWithDebInfo`로 구성됨 |
| effective flags | `-O2 -g -DNDEBUG`, C++17 |
| normalized path | source `/src`, build `/out/build`, install `/out/CUBRID` |
| cache | `CCACHE_DISABLE=1` |
| scheduling | variant를 하나씩 clean build; 각 build 내부 compiler 병렬성은 허용 |
| CM server | 네 variant 모두 `WITH_CMSERVER=OFF` |

Origin build의 actual `source.sha`, submodule 상태, toolchain, CMake cache, ELF notes/hash는
`artifacts/full-server-gcc8/manifests/{qa-2029,A,B,C}/`에 전달됐다. 새 build 결과가 이 값과 다르면 차이를 먼저
기록하고 timing을 해석한다.

Prepared image layer는 Git에 포함할 수 없다. 가장 정확한 이동 방법은 origin PC에서 `podman save`, 안정 PC에서
`podman load`하는 것이다. 그것이 불가능하면 `container/Containerfile`과 `rpm-packages.txt`로 재구성하되,
repository snapshot 시점에 따라 byte-identical image가 아님을 명시한다.

### QA-faithful build에서 반드시 확인할 차이

사용자는 QA가 `./build.sh ... build`로 engine을 빌드한다고 확인했다. 현재 build도 같은 action path지만 다음은 QA와
동일하다고 아직 증명하지 못했다.

- QA의 exact command line이 bare `./build.sh build`인지, `-m release`, generator, compiler option을 추가하는지
- QA workspace의 absolute source/build/install path
- build number/version/package metadata 주입 방법
- QA의 environment variables, parallelism, submodule checkout 방식
- `WITH_CMSERVER`, strip/package step, post-link tool 적용 여부
- QA `.2029`/`.2031` package의 actual `libcubrid.so.11.5`, `libcubridcs.so.11.5`, Build ID와 SHA-256

새 PC의 첫 작업은 QA build log 또는 담당자에게서 이 정보를 확보하는 것이다. 가능한 경우 source rebuild 전에
실제 package 두 개를 받아 binary와 SQL을 직접 비교한다. 이 이슈는 16-byte function alignment에도 민감하므로
“대략 같은 release build”로 충분하지 않다.

## 5. Current normalized timing result — reference, not final reproduction

SQL:

```sql
SET TRACE OFF;
SELECT COUNT(*) FROM db_class a, db_class b, db_class c, db_class d, db_class e;
```

`db_class` cardinality는 49이고 모든 유효 run의 결과는 `49^5 = 282,475,249`다. CSQL `;time on`은
`db_compile_statement()` 직전부터 `db_execute_statement()` 직후까지이며 result formatting/commit은 제외한다.

현재 공유 host에서 A/B/C를 12 balanced permutation × 5 series로 실행해 variant별 60개, 총 180개 randomized
sample을 완성했다. server는 물리 CPU 3,4, client는 CPU 5에 고정했지만 host는 다른 사용자와 공유됐다.

| variant | n | mean(s) | median(s) | 10% trimmed mean(s) | CV |
|---|---:|---:|---:|---:|---:|
| A | 60 | 20.565956 | 20.545855 | 20.546418 | 1.55% |
| B | 60 | 18.524187 | 18.434318 | 18.487757 | 1.94% |
| C | 60 | 18.505820 | 18.489819 | 18.489320 | 1.39% |

100,000회 paired bootstrap:

| 비교 | median ratio | 변화 | 95% CI | paired 방향 |
|---|---:|---:|---:|---|
| B/A | 0.897228 | B −10.28% | 0.893466–0.904837 | B faster 60/60 |
| C/A | 0.899929 | C −10.01% | 0.895728–0.902857 | C faster 60/60 |
| C/B | 1.003011 | C +0.30% | 0.994850–1.006438 | C faster 28, slower 32 |

각 series median도 모두 같은 A>B/C 방향이었다. 반면 QA 보고는 `.2031`이 `.2029`보다 +10.56% 느렸다. 따라서
현재 build는 slowdown을 재현하지 못했고 오히려 비슷한 크기의 반대 방향을 보였다.

QA-2029 연속 5회는 mean 20.604356초였다. B 연속 5회 QA-view는 아직 실행하지 않았으며
`scripts/run-qa-five-b.sh`가 준비돼 있다.

Evidence:

- `artifacts/full-server-gcc8/timings.csv`, SHA-256
  `cf224a101cb59270d6355f8d16e41c4a13b17eb3d6d334b71e6024a680fe6ce6`
- `artifacts/full-server-gcc8/timing-summary.json`, SHA-256
  `7cdf7ec9ff2302f193761acd4fe287ea034d0c28500a2dce47ccf61ff306ba1b`

## 6. Shared-host contamination lesson

현재 dev2는 80-CPU shared host다. 다른 사용자들이 70–150개의 `cc1plus`를 띄우면 정상 18–20초 쿼리가
32–37초까지 늘어났다. 예:

| variant/key | contaminated | quiet rerun | 당시 상태 |
|---|---:|---:|---|
| B early pilot | 37.596649s | 약 18.4s | 타 사용자 full CUBRID build, load 80+ |
| C series5/round5 | 33.896587s | 18.380318s | `cc1plus=149`, load 59→120 |
| A series5/round6 | 32.321560s | 20.482354s | `cc1plus=69` |
| A series5/round8 | 36.781637s | 20.465354s | `cc1plus=71` |

harness는 실행 전후 `cc1plus`를 확인하고 오염 run을 CSV에 넣기 전에 차단했다. 해당 raw log는
`*.compiler*-not-recorded.log`로 보존했다. 새 안정 PC에서는 이 gate를 유지하되 가능하면 다른 workload가 전혀
없는 dedicated physical cores와 sibling을 사용한다.

이 오염은 QA의 약 2초 차이보다 훨씬 크다. 안정 PC에서 재현해야 한다는 판단은 옳다.

## 7. Final ELF findings already established

`cub_server` launcher는 네 variant 모두 SHA-256
`53daf314c1196bbad1476b2a40865404480e1805b9061e308178a7e2369e6ecb`로 동일하다. 실제 server engine 분석 대상은
`libcubrid.so.11.5`다.

| variant | DSO bytes | DSO SHA-256 | Build ID |
|---|---:|---|---|
| QA-2029 | 167,446,992 | `41082753538ce970d54fdc211afa993d46ce06dd7e85a2377e8ed354978ce65e` | `4c90a5f6f076d6858386503d99e9f49f986d8ac0` |
| A | 167,446,992 | `f40041b4c2390fa4693073c445d355f445fa9e146c06804e74328410f1ad19d3` | `ecab8534682d72195643ffb39965126f2425c067` |
| B | 167,377,096 | `4236464ad9d75c368c89b29505764d38c3a4d2d33f4c33562cebd4a28b297ee5` | `cf8431c74ffef0975fb93e64bf63c128516c1a0b` |
| C | 167,376,920 | `37da8c432c6f2272167ee595c7888af5336f929bcb27e65bc482b73658b2165a` | `9ae5c236c67c246a8b58d7a5c5e3e56e3939a758` |

### A→B

- `log_recovery_redo_parallel.cpp.o`의 aggregate `.text*`는 44,582→43,274 bytes, `.rodata*`는
  2,412→1,624 bytes로 줄었다.
- final server `.text` 크기는 둘 다 8,314,404 bytes지만 시작은 `0x2f7000`→`0x2f6000`으로 한 page 이동했다.
- query hot function은 모두 −4,080 bytes 이동하고 시작 주소 `%64`가 16 bytes 바뀌었다.

| function | A | B/C | `%64` A→B |
|---|---:|---:|---:|
| `qdata_evaluate_aggregate_list` | `0x495d00` | `0x494d10` | 0→16 |
| `qexec_start_mainblock_iterations` | `0x4bb450` | `0x4ba460` | 16→32 |
| `qexec_execute_mainblock` | `0x4ceb80` | `0x4cdb90` | 0→16 |
| `qexec_execute_query` | `0x4dc830` | `0x4db840` | 48→0 |
| `scan_next_scan_block` | `0x4fbbe0` | `0x4fabf0` | 32→48 |
| `scan_next_scan` | `0x4fcba0` | `0x4fbbb0` | 32→48 |

이것은 GCC 8/GNU ld final layout 변화의 직접 증거다. 주소 이동만으로 cache miss 원인이 증명되지는 않는다.

### B→C forced `noexcept`

- final `.text` 전체 byte-identical
- 위 query function 주소, size, raw SHA-256 모두 동일
- 여섯 concrete scope-exit destructor의 주소/size/disassembly도 동일
- writable data와 `.bss` layout 동일
- 차이는 `.eh_frame` +24 bytes, `.gcc_except_table` −32 bytes뿐

따라서 현재 full build에서 forced `noexcept`는 정상 query machine code/layout을 바꾸지 않으며 성능 수정책이
아니다.

### `log_Gl`

| variant | address | size | `%64` | `%4096` |
|---|---:|---:|---:|---:|
| A | `0x1003cc0` | 1,360 | 0 | `0xcc0` |
| B/C | `0x1002cc0` | 1,360 | 0 | `0xcc0` |

A→B는 정확히 −4,096 bytes 이동했지만 cache-line/page 내부 offset이 보존된다. B/C는 주소와 이웃 global까지
동일하다. 따라서 `log_Gl` unlucky cache-line 가설은 이 build의 B/C 차이를 설명하지 못한다.

Compact tables는 `binary-layout.csv`, `hot-symbols.csv`, `hot-function-hashes.csv`에 있다.

## 8. Most likely interpretation before PMU

현재 evidence가 지지하는 중간 가설:

1. scope-exit logic의 direct runtime overhead가 이 COUNT query를 느리게 한 것은 아니다.
2. PR은 cold object/EH/rodata 크기를 바꾸고, 그 변화가 GNU ld를 통해 unrelated query hot code의
   address/alignment까지 전파되는 trigger가 된다.
3. 이 incidental layout은 build/package마다 유리하거나 불리한 방향이 될 수 있다. 현재 normalized build는 B가
   약 10% 빠르고 QA package는 B에 해당하는 `.2031`이 약 10% 느렸다.
4. 따라서 “GCC 8의 deterministic optimization failure”로 확정하기보다 **package-specific unlucky binary
   layout/front-end effect**를 우선 검증해야 한다.
5. forced destructor `noexcept`와 `log_Gl` cache-line은 현재 evidence상 원인이 아니다.

PMU가 아직 없으므로 2–4는 최종 판정이 아니다.

## 9. Stable-PC execution plan

### Phase A — QA slowdown first

1. QA의 exact build command/log/package를 확보한다.
2. 가능하면 실제 `.2029`/`.2031` package ELF를 그대로 실행하고 hash/Build ID/section/symbol을 저장한다.
3. package가 없으면 같은 absolute workspace, `build.sh` flags, environment, parallelism, submodules, strip/package
   step으로 `.2029`/`.2031`을 다시 빌드한다.
4. trace off, 연속 5회로 먼저 QA 숫자의 방향을 확인한다. 절대시간보다 `.2031/.2029` ratio를 본다.
5. slowdown이 재현되지 않으면 build path, package metadata, linker, CPU model을 한 번에 하나씩 QA와 맞춘다.

### Phase B — causality matrix

1. QA-2029/A/B/C를 동일 조건으로 clean rebuild한다.
2. manifest에 source/submodule SHA, patch digest, toolchain, command, environment, build path, flags, binary hash,
   Build ID를 저장한다.
3. 같은 DB clone을 사용하고 매 sample마다 server/master를 clean start/stop한다.
4. 각 variant warmup 2회, QA-2029/B 연속 5회, A/B/C balanced randomized 60회씩 실행한다.
5. result `282475249`, cardinality 49, plan topology가 다르면 timing을 해석하지 않는다.

`run-timings-single.sh`는 container name/mount와 CPU 3,4,5가 현재 PC에 hard-code돼 있다. 새 PC topology에서
physical core와 sibling을 확인해 수정한다. checkpoint resume와 compiler gate는 유지한다.

### Phase C — plan and PMU

1. `run-plans.sh`로 QA-2029/A/B/C plan을 저장하고 volatile text를 normalize해 hash를 비교한다.
2. `run-pmu.sh`를 먼저 variant 한 개/event group 한 개로 pilot한다.
3. `perf stat`이 server의 모든 thread를 실제로 count하는지 cycles/instructions 규모로 검증한다.
4. 각 event의 time-running이 95% 이상인지 확인한다. multiplex 또는 unsupported event는 group을 더 작게 나눈다.
5. 두 repetition 이상 수집하고 `analyze-pmu.py`로 요약한다.
6. `perf record -F 999 --call-graph fp`와 `render-perf-reports.sh`로 hot symbol 비율을 비교한다.

현재 Cascade Lake host용 group:

- core: task-clock, cycles, instructions, ref-cycles
- branch: branch instructions/misses
- generic cache: cache references/misses, L1D, LLC, iTLB, L1I
- front end: `idq_uops_not_delivered.core`, `icache_64b.iftag_miss/stall`
- uop cache: `idq.dsb_uops`, `idq.mite_uops`, `dsb2mite_switches.penalty_cycles`
- retired front end: `frontend_retired.l1i_miss`, `frontend_retired.dsb_miss`

새 CPU에서 `perf list`로 alias를 확인하고 지원되지 않는 이름을 그대로 강행하지 않는다.

### Phase D — decide

다음을 함께 만족해야 cache/front-end 원인으로 결론 낸다.

- 동일 plan/result/instruction work
- latency ratio가 series마다 같은 방향
- cycles/IPC 또는 front-end stall이 같은 방향
- L1I/DSB/MITE/IDQ event가 해당 방향을 설명
- 실제 final hot-function address/alignment가 그 binary에 존재

address movement만 있거나 cache counter 차이가 noise 범위면 “layout change는 확인, microarchitectural mechanism은
미확정”으로 남긴다.

## 10. Bootstrap checklist on the stable PC

Git handoff에는 이미 Wayfinder, manifests, C patch, scripts, timing/layout evidence가 들어 있다. 안정 PC에서 다음을
수행한다.

1. `my-cubrid-docs`를 handoff 보완 commit까지 pull한다.
2. artifact root에서 `sha256sum -c SHA256SUMS`로 전달 파일을 검증한다.
3. canonical CUBRID clone에 네 commit이 있는지 확인하고 `prepare-worktrees.sh`로 worktree를 재생성한다.
4. `manifests/`의 submodule SHA와 새 worktree를 비교한다.
5. prepared image tar를 별도로 받았다면 `podman load`한다. 없으면 supplied Containerfile/RPM list로 환경을
   재구성하고 그 차이를 새 manifest에 기록한다.
6. origin ELF/build tree/raw log는 없는 것을 정상 상태로 취급하고 새 PC에서 새 evidence root를 만든다.
7. 실제 QA packages를 확보하면 가장 우선해서 별도 read-only evidence directory에 저장한다.
8. 이 PC의 tracker DB에 새 item을 생성하고 handoff URL/commit을 note에 기록한다. origin item 30을 찾지 않는다.

Origin host의 unstripped ELF 또는 raw contamination log가 추가로 필요하다고 판단될 때만 다음을 별도 전송한다.

```text
/home/vimkim/gh/cb/cbrd-26382-results/{qa-2029,A,B,C}/CUBRID/lib/libcubrid.so.11.5
/home/vimkim/gh/cb/cbrd-26382-results/bench/raw/
```

현재 container topology는 참고용이다.

```text
container: cbrd26382-single
image:     localhost/cbrd26382-rocky8-gcc8:build-ready
command:   sleep infinity
/opt/qa-2029, /opt/A, /opt/B, /opt/C  <- 각 install tree
/bench                                <- 한 DB clone/registry
/bench/query.sql                      <- read-only query bind
```

DB registry row:

```text
c26382  /bench/golden  localhost  /bench/golden  file:/bench/golden/lob
```

새 PC에서는 DB를 한 번 만들고 golden copy를 생성한 뒤 variant마다 같은 clone을 사용한다. 현재 DB binary file을
다른 architecture/endianness에 옮기기보다 같은 x86-64 환경에서 새로 만드는 편이 안전하다.

## 11. Hazards — do not repeat

- `objcopy --dump-section SECTION`에 output file을 생략하면 input ELF를 read-only로 읽는 것이 아니라 재작성할 수
  있다. 설치 DSO에 절대 실행하지 않는다. section byte는 `readelf`, `nm`, `objdump` 또는 read-only `dd`로 읽는다.
- 실제로 한 번 설치 DSO가 912 bytes 재작성됐고 hash audit가 이를 발견했다. 해당 timing은 모두 폐기하고
  untouched build tree에서 재install한 뒤 original SHA-256을 확인했다.
- `cub_server` launcher만 비교하면 네 build가 같아서 잘못된 결론이 난다. 실제 engine은
  `libcubrid.so.11.5`다.
- 서버 약 300개 thread를 CPU 한 개에 몰면 watchdog restart가 발생한다.
- 네 container/master를 동시에 실행하면 IPC/master collision이 발생했다. 한 container, 한 server/master만
  사용한다.
- 공유 host의 compile contention은 2초 regression보다 훨씬 크다. stable PC에서도 compiler/process gate와 raw
  log를 유지한다.
- QA-2029 source mapping과 actual QA package를 동일시하지 않는다.
- `just`는 개인 편의 도구다. QA/public reproduction은 repository `build.sh`, CMake cache, project scripts로
  설명한다.

## 12. Remaining deliverables

- QA exact build/package provenance 확보
- 안정 PC에서 QA slowdown 방향 재현
- B 연속 5회 QA-view
- 네 plan capture/normalized hash
- PMU 80 stat runs + 네 profile 또는 새 CPU에 맞춘 동등한 matrix
- PMU summary와 hot profile 해석
- 미완성 full-server 보고서의 모든 `TBD` 제거 및 evidence link audit
- `my-cubrid-docs` commit/push와 immutable report URL 확인
- CBRD-26382에 쉬운 한국어 요약+URL 댓글 게시 후 comment ID/body 재조회
- portable Wayfinder issue 04/map을 최종 evidence로 갱신
- 안정 PC에서 생성한 local work-tracker item을 완료 처리; origin host item 30은 참조만 하고 존재를 요구하지 않음

현재 후속 JIRA 댓글은 아직 게시하지 않았다. 선행 minimal report 댓글만 존재한다. 안정 PC 결과가 QA 방향을
재현하거나, 재현 실패의 조건을 충분히 좁힌 뒤 최종 댓글을 게시한다.

## 13. Suggested first message from the new agent

> CBRD-26382 handoff를 읽었습니다. 먼저 QA의 exact `./build.sh ... build` command와 실제 `.2029/.2031` package
> manifest/ELF를 확보하거나 부재를 명시하겠습니다. 그 다음 안정 PC에서 numeric-version comparison을 먼저
> 재현하고, A/B와 B/C causal controls를 같은 build path로 추가하겠습니다. 현재 dev2의 B −10.28% 결과는
> reference로만 사용하고 최종 원인으로 가정하지 않겠습니다.
