# CBRD-26382: CUBRID PGO(Profile-Guided Optimization) 실험

- 작성일: 2026-08-28
- 작성자: Claude (Fable 5), 세션 소유자 vimkim
- 소스: CUBRID develop `95b79e7ed` ([CBRD-27245] Improve lexer input handling...) 기준 worktree `cbrd-26382-pgo`
- 선행 문서: [hot-function-alignment-options](CBRD-26382-hot-function-alignment-options_codex.md),
  [gcc8-full-server-follow-up](CBRD-26382-gcc8-full-server-follow-up_codex.md)
- JIRA 근거 comment: [CBRD-26382 comment 4776011](http://jira.cubrid.org/browse/CBRD-26382?focusedCommentId=4776011&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-4776011)

## 1. 왜 PGO인가 (CBRD-26382의 결론과 연결)

CBRD-26382 분석의 최종 결론은 다음과 같았다.

1. `scope_exit` 리팩토링 자체의 실행 비용은 원인이 아니다.
2. PR이 만든 **final-link layout 변화**(hot function의 32-byte phase 이동)가 성능을 움직였다는
   인과가 7-byte padding control로 강하게 확인되었다.
3. non-PGO compiler는 어떤 함수가 hot인지 모르기 때문에, compiler upgrade만으로는
   layout 민감성이 사라지지 않는다. 실제 hotness 기반 배치는 **PGO matrix**로 검증해야 한다.

즉 이 이슈의 병리는 "컴파일러가 hot path를 모른 채 통계적 heuristic으로 배치한 바이너리는
무관한 소스 변화에도 배치가 흔들리고, 그 흔들림이 ±1% 이상의 성능 잡음을 만든다"는 것이다.
PGO는 이 무지(無知)를 실측 profile로 대체하는 컴파일 기법이다.

## 2. PGO compiler란 무엇인가

PGO(Profile-Guided Optimization)는 2-pass 컴파일 기법이다.

1. **Instrumentation pass** (`-fprofile-generate=DIR`): 컴파일러가 모든 branch/call edge에
   카운터를 심은 바이너리를 만든다.
2. **Training run**: 그 바이너리로 대표 workload를 실행한다. 프로세스가 정상 종료할 때
   `.gcda` 파일(카운터 덤프)이 DIR에 기록된다.
3. **Optimization pass** (`-fprofile-use=DIR`): 같은 소스를 다시 컴파일하면서 컴파일러가
   추측 대신 실측 빈도를 사용한다.

profile이 있으면 컴파일러가 바꾸는 것들:

- **Inlining**: 실제로 자주 불리는 call site만 공격적으로 inline.
- **Branch layout**: likely 방향을 fall-through로 배치해 branch 미스와 I-cache 낭비 감소.
- **Hot/cold splitting**: 함수 내부의 cold basic block(에러 처리 등)을 `.cold` clone으로
  분리해 hot 경로를 조밀하게 만듦.
- **Function reordering**: hot 함수끼리 `.text.hot` 부근에 모아 I-cache/iTLB/DSB locality 개선.
- **Unexecuted code는 size 최적화**: 실행되지 않은 코드는 `-Os`처럼 작게 만들어
  hot working set을 더 줄임.
- register allocation, loop unrolling, vectorization 판단에도 빈도 반영.

CBRD-26382가 관측한 "unlucky layout" 문제에 대해 PGO가 갖는 의미: layout이 여전히 소스
변화에 따라 바뀌긴 하지만, **hot 함수 배치가 '우연'이 아니라 '실측 hotness'로 결정**되므로
무관한 cold 코드 변화가 hot 코드의 배치를 흔드는 경로가 구조적으로 줄어든다.

관련 변종: AutoFDO(instrumentation 대신 `perf` sampling으로 profile 수집, 오버헤드 낮음),
LLVM BOLT(링크 후 바이너리를 profile로 재배치하는 post-link optimizer). 이들은
[hot-function-alignment-options](CBRD-26382-hot-function-alignment-options_codex.md) 4장에서
검토했다.

## 3. 실험 설계

| 항목 | 값 |
|---|---|
| Host | Rocky Linux 9.6, 2x Xeon Gold 5218R (Cascade Lake, 40C/80T), 공유 서버(타 사용자 벤치마크 동시 실행 중) |
| Compiler | GCC 11.5.0 (Red Hat 11.5.0-5), binutils 기본, GNU ld |
| Source | develop `95b79e7ed`, worktree `/home/vimkim/gh/cb/cbrd-26382-pgo` |
| Baseline | `release_gcc` preset: `-O2 -ggdb3 -DNDEBUG -finline-functions` (RelWithDebInfo, ccache) |
| PGO preset | `pgo_gcc` (worktree-local `CMakeUserPresets.json`에 추가): baseline과 동일 flag + `$env{CUBRID_PGO_FLAGS}`, ccache 비활성 |
| Instrumentation | `-fprofile-generate=<dir> -fprofile-update=atomic` (compile+link) |
| Use | `-fprofile-use=<dir> -fprofile-correction -Wno-missing-profile -Wno-error=coverage-mismatch -Wno-error=stringop-overflow=` |
| Training | `createdb` + qa49 테이블 생성 + 대상 query 3회 (instrumented 실행 ~258s/query, baseline의 ~6.6배) |
| Profile | `.gcda` 955개, 9.0MB |
| Query | `SELECT COUNT(*) FROM qa49 a, qa49 b, qa49 c, qa49 d, qa49 e;` — 49행 테이블 5-way cartesian = 282,475,249행. QA의 db_class(49행) 쿼리와 동일 규모(이 worktree의 db_class는 74행이라 2.2G행이 되어 부적합) |
| Protocol | 매 sample: `cubrid server start`(taskset 22-29, socket 1) → csql(taskset 32) `;time on` + `SET TRACE OFF;` + query 2회 → server stop → master stop. 변형 A/B를 세션 단위로 interleave, 8 round × 2 query = 변형당 16 측정 |
| Port 격리 | 실험용 install에 `cubrid_port_id=39117` (공유 호스트의 타 사용자 cub_master와 충돌 방지) |

gen/use 두 phase가 **같은 build dir**(`build_preset_pgo_gcc`)을 쓰도록 preset을 하나로 두고
환경변수로 flag만 바꿨다. GCC는 `-fprofile-use=DIR`에서 object 절대경로를 mangle한 이름으로
`.gcda`를 찾기 때문에, build dir이 달라지면 profile을 하나도 못 찾는다.

## 4. 빌드 관찰 (도입 비용의 실측)

1. **Instrumented 빌드는 정상 통과.** full rebuild(ccache 무효) 약 7분/80코어.
2. **`-fprofile-use` 빌드는 1개 파일에서 -Werror 실패**: `src/broker/cas_cgw_odbc.c`에서
   PGO가 바꾼 inlining 결정 때문에 `-Wstringop-overflow=` 경고가 새로 발생 →
   `-Werror`로 실패. `-Wno-error=stringop-overflow=` 추가로 통과.
   PGO 도입 시 경고 위생(warning hygiene) 작업이 필요하다는 실증.
3. **바이너리 크기**: `libcubrid.so` `.text` 8.67MB → 7.09MB (**-18.2%**).
   실행되지 않은 코드의 size 최적화 + hot/cold 분리 효과.
4. **Instrumented 실행 오버헤드**: 대상 query 기준 ~6.6배 (39.4s → ~258s,
   `-fprofile-update=atomic` 포함). production에서 상시 켤 수 있는 수준이 아니며,
   훈련 전용 빌드가 필요하다.

## 5. 배치(layout) 증거

이전 분석에서 hot으로 확인된 함수들의 시작 주소 (`nm`, libcubrid.so):

| 함수 | baseline (release_gcc) | PGO (pgo_gcc) |
|---|---|---|
| qdata_evaluate_aggregate_list | 0x48e9f0 | 0x6092a0 |
| scan_next_scan | 0x4fa600 | 0x609ae0 |
| qexec_execute_query | 0x4d93e0 | 0x63e990 |
| qexec_execute_mainblock | 0x4cbbd0 | 0x63ec50 |
| scan_next_scan_block | 0x4f9690 | 0x642c20 |

- baseline: 5개 함수가 소스/링크 순서대로 ~441KB 구간에 흩어짐.
- PGO: **hot 함수들이 서로 인접 배치됨** (aggregate_list 바로 옆에 scan_next_scan,
  execute_query 바로 옆에 execute_mainblock). 구간 폭 ~236KB로 축소.
- PGO에서 `qexec_execute_query`, `scan_next_scan_block`에도 `.cold` clone이 새로 분리됨.

이것이 CBRD-26382에서 "compiler는 모르는" 것이라고 지적한 실측 hotness 기반 배치다.

## 6. 성능 결과

### 6.1 Timing (변형당 n=16, 세션 interleave, `;time on` 측정값)

| 변형 | mean | median | stdev | min | max |
|---|---|---|---|---|---|
| release_gcc (baseline) | 39.036s | 38.927s | 0.544 | 38.230 | 39.861 |
| pgo_gcc | 35.320s | 35.447s | 0.723 | 33.373 | 36.268 |

- **median 기준 PGO가 −8.94%** (baseline 대비), mean 기준 −9.52%.
- Mann-Whitney U=0 (두 분포가 완전히 분리), two-sided p < 0.00001.
- 두 분포의 최대/최소가 겹치지 않음: PGO 최악(36.27s) < baseline 최선(38.23s).
- 이 개선 폭은 QA가 보고했던 회귀 폭(+10.56%)과 같은 자릿수다. 이 쿼리의 hot loop가
  frontend/layout에 그만큼 민감하다는 방증이기도 하다.

주의: 공유 호스트(타 사용자 워크로드 동시 실행)에서 측정했다. 세션 단위 interleave와
core pinning(socket 1)으로 완화했지만, 전용 호스트에서의 독립 재확인이 바람직하다.

### 6.2 PMU (perf stat, cub_server 프로세스, 세션당 query 2회, 1세션씩)

| counter | baseline | PGO | delta |
|---|---|---|---|
| cycles | 248.21G | 225.20G | **−9.3%** |
| instructions | 673.00G | 624.24G | **−7.2%** |
| IPC | 2.71 | 2.77 | +2.2% |
| branches | 139.25G | 130.89G | −6.0% |
| branch-misses | 115.57M (0.08%) | 41.59M (0.03%) | **−64.0%** |
| L1-icache-load-misses | 223.12M | 124.17M | **−44.3%** |
| iTLB-load-misses | 2.53M | 1.87M | −26.2% |
| idq.dsb_uops | 283.06G | 220.70G | −22.0% |
| idq.mite_uops | 360.44G | 373.36G | +3.6% |

해석:

- 개선의 1차 성분은 **실행 instruction 자체의 감소(−7.2%)** — profile 기반 inlining과
  branch 배치가 hot loop의 명령 수를 줄였다.
- 2차 성분은 **branch-miss 64% 감소, L1I miss 44% 감소** — 실측 빈도 기반 branch
  layout과 hot/cold 분리가 front-end 낭비를 줄였다.
- DSB uops는 오히려 줄고 MITE는 소폭 늘었다. 총 공급 uop이 줄었고 공급 경로 구성이
  달라진 것으로, 기존 보고서의 결론("DSB miss 단독 원인론 기각")과 일관된다 —
  성능을 결정한 것은 공급 경로의 종류가 아니라 일의 총량과 miss율이다.
- counter는 서버 프로세스 세션 전체(시작/종료 포함)를 덮는다. 두 변형 모두 동일
  프로토콜이므로 비교는 공정하다.

## 7. CUBRID에 PGO를 도입할 수 있는가 — 평가

### 7.1 결론

**기술적으로 도입 가능하고, CBRD-26382가 확인한 병리(layout 민감성)에 정확히 대응하는
수단이다.** 이번 실험에서 확인된 사실:

1. 기존 preset 체계에 flag 2세트(`-fprofile-generate` / `-fprofile-use`)를 추가하는
   것만으로 전체 파이프라인이 동작했다. 소스 수정 0건.
2. 훈련 workload와 같은 쿼리에서 **−8.9% (median)**, 완전한 분포 분리.
3. hot 함수들이 실측 hotness로 인접 배치되고 `.text`가 18% 줄었다 — "우연한 배치"가
   만드는 회귀(이 이슈의 근본 원인 후보)의 구조적 완화.
4. 기능 smoke(DDL/DML/index/join/aggregate) 및 16세션 × 결과값 정합(282,475,249)
   확인. 단 develop 브랜치의 이 preset에는 등록된 ctest unit test가 없어(unit test는
   feature 브랜치 소속) 정식 테스트 게이트는 이 실험 범위 밖이다.

### 7.2 이번 실험의 한계 (일반화 주의)

- **Best-case 실험이다.** 훈련 workload = 측정 workload. 제품 도입에서는 대표 훈련
  suite(OLTP/DDL/utility/recovery)를 정의해야 하고, 훈련에 없는 경로는 cold로
  취급되어 느려질 수 있다. `-fprofile-partial-training`(GCC 10+)이 이 trade-off를
  조절한다.
- **공유 호스트에서 측정했다.** interleave + pinning + Mann-Whitney로 완화했지만
  전용 호스트에서 독립 rebuild로 재확인해야 한다.
- **단일 쿼리, 단일 컴파일러(GCC 11.5) 축이다.** comment 4776011의 PGO matrix
  (GCC 8 / 최신 GCC / Clang × non-PGO / PGO)의 한 칸을 채운 것이다.
- PGO는 layout만 바꾸는 것이 아니라 inlining/unrolling 등 codegen 전반을 바꾼다.
  "주소만 바뀐 A/B"로 해석하면 안 된다 (기존 보고서의 경고 그대로).

### 7.3 도입 시 필요한 작업 (실측 근거 포함)

| 작업 | 근거 |
|---|---|
| 경고 위생: PGO inlining이 새 경고를 유발 | `cas_cgw_odbc.c` `-Werror=stringop-overflow=` 실패 실측. `-Wno-error` 임시 조치보다 근본 수정 권장 |
| 2-phase 빌드 파이프라인 (build.sh/CI/CPack 통합) | gen/use가 같은 build dir을 공유해야 profile이 resolve됨 (`-fprofile-use=DIR`은 object 경로 기반) |
| 훈련 workload 정의와 profile 갱신 주기 | stale profile은 이득 감소/역효과. `-Wno-coverage-mismatch`로 덮으면 품질 저하 |
| 훈련 빌드 실행 비용 확보 | instrumented 실행 ~6.6배 느림 (atomic counter). CI에서 훈련 시간 예산 필요 |
| PGO variant 전체 QA (sql/medium/shell/HA) | codegen 전반이 바뀌므로 별도 제품 variant로 검증 |
| 빌드 재현성 정책 | profile을 빌드 아티팩트로 고정·버전 관리해야 reproducible |

### 7.4 권고 단계

1. **단기**: 이 결과를 comment 4776011의 PGO matrix에 GCC 11 축으로 편입.
   전용 호스트에서 독립 rebuild 2회 이상으로 −8.9%를 재확인.
2. **중기**: 대표 훈련 suite 정의(QA sql/medium 부분집합 + OLTP mix) 후
   `-fprofile-partial-training` on/off 비교. 훈련에 없는 workload의 회귀 여부 측정.
3. **장기**: instrumentation 비용이 문제가 되면 **AutoFDO**(perf sampling 기반,
   훈련 전용 빌드 불필요), 최종 단계로 **BOLT**(post-link 재배치) 검토 —
   선행 조건과 위험은 [hot-function-alignment-options](CBRD-26382-hot-function-alignment-options_codex.md) 4장 참조.

## 8. 재현 방법

```bash
# worktree 준비 (presets: 이 worktree의 CMakeUserPresets.json에 pgo_gcc 추가됨)
cd /home/vimkim/gh/cb/cbrd-26382-pgo

# 1) instrumented build
printf 'PRESET_MODE=pgo_gcc\n' > .env && direnv allow
export CUBRID_PGO_FLAGS="-fprofile-generate=$PWD/pgo-profile-data -fprofile-update=atomic"
export CUBRID_PGO_LINK_FLAGS="$CUBRID_PGO_FLAGS"
direnv exec . just configure && direnv exec . just build

# 2) training
bash pgo-bench/train.sh pgo_gcc 3

# 3) optimized build
export CUBRID_PGO_FLAGS="-fprofile-use=$PWD/pgo-profile-data -fprofile-correction \
  -Wno-missing-profile -Wno-error=coverage-mismatch -Wno-error=stringop-overflow="
export CUBRID_PGO_LINK_FLAGS="$CUBRID_PGO_FLAGS"
direnv exec . just configure && direnv exec . just build

# 4) benchmark (release_gcc 설치본과 interleave 비교)
bash pgo-bench/bench.sh release_gcc pgo_gcc 8 2 pgo-bench/results.csv
python3 pgo-bench/analyze.py pgo-bench/results.csv
```

harness 전체: `cbrd-26382-pgo/pgo-bench/` (env.sh, setup-db.sh, run-sample.sh, bench.sh,
train.sh, perf-sample.sh, analyze.py, query.sql).
