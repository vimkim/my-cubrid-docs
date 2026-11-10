# PR #8299 새 base 기준 CPU 회귀 재측정

- 작성일: 2026-11-10, Asia/Seoul. 작성: Claude Code 세션.
- 관련: [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785), [PR #8299](https://github.com/CUBRID/cubrid/pull/8299).
- 집계: [`pr8299-newbase-20261110/analysis.txt`](pr8299-newbase-20261110/analysis.txt)와 집계 스크립트 `analyze.py`. 원시 출력과 로그는 작성자 로컬에만 보존했다.

## 결론

- **회귀 없음.** 판정 규칙(후보 명령어 수가 base보다 2% 넘게 많고 spread가 효과보다 작으면 회귀)에 걸리는 경우가 없다.
- 5개 경우 중 4개는 후보가 명령어를 3.8~9.6% 덜 쓴다. `ordinary scan` 하나는 차이가 0.05%라서 차이 없음이다.
- `bench.py compare`는 3쌍 모두 exit 0. 후보와 base를 맞바꾼 대조 실행은 exit 1이라서 비교기가 5~10% 차이를 잡아낸다.
- 단, 후보는 워크트리의 설치본이 아니라 별도 prefix에서 실행했다. 아래 "이상 사항"을 본다.

## 대상과 설정

| 역할 | commit | 빌드 | 실행 환경 |
|---|---|---|---|
| baseline (feature/oos-merge 끝) | `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f` | release_gcc, 이번에 새로 빌드 | `CBRD-27785-feature-base` workenv, port 41162, DB `b8299` |
| candidate (PR head) | `855f220d532e222f2a266a0883c94a40bed3a388` | release_gcc, 이번에 다시 빌드(19:47) | 별도 prefix(아래), port 41205, DB `c8299` |

- 두 DB 모두 `cubrid createdb --db-volume-size=64M --log-volume-size=32M ... en_US.utf8`로 새로 만들었다.
- 두 설정 모두 `[@DB]` 절에 `data_buffer_size=4G`, `log_buffer_size=256M`, `sort_buffer_size=16M`, `max_clients=50`, `max_query_cache_entries=0`, `query_cache_size_in_pages=0`. 나머지는 workenv 기본값이다. 하니스가 서버의 실제 값도 읽어 두 번 확인했다(`bench/conditions-*.json`).
- 하니스는 후보 워크트리의 `contrib/benchmarks/oos-performance/` 사본 하나를 양쪽에 썼다(`harness_sha256`이 같다).
- 호스트: 80 core, CPU affinity는 제한하지 않았다. 측정 중 load average는 6~25였다. 판정 지표가 명령어 수라서 영향이 작다.

## 방법

- 판정 지표는 서버 프로세스 user 명령어 수(`instructions:u`)의 retained 중앙값이다. cycles는 참고다.
- 서버를 시작할 때마다 하나의 "start"로 센다. start마다 `bench.py measure`(2 round x 5 run, run 0 버림, 20 scan/run)와 `ordinary.py measure`(5 sample, 첫 sample 버림, UPDATE는 매번 새 clone)를 돌렸다.
- 실행 순서는 B1 B2 C1 C2 B3 C3 B4. base 4 start, candidate 3 start다. 엄밀한 ABBA는 아니고 서로 끼워 넣은 순서다. 명령어 수는 시간 drift에 거의 안 흔들려서 판정에는 영향이 없다고 본다. 이 부분은 추론이다.
- 값: start별 retained 중앙값을 구하고, 그 start 중앙값들의 중앙값을 비교했다. 변화율은 (base - cand) / base이고 +가 좋아짐이다.

## 결과 (명령어 수)

| 경우 | base 중앙값 (4 start) | cand 중앙값 (3 start) | cand 대비 변화 | start 사이 spread base / cand | start 내 최대 spread base / cand | 판정 |
|---|---:|---:|---:|---|---|---|
| bench narrow | 7,063,865,215 | 6,679,710,983 | +5.44% | 0.012% / 0.001% | 0.009% / 0.008% | 회귀 없음, 좋아짐 |
| bench wide | 13,286,109,644 | 12,005,722,312 | +9.64% | 0.005% / 0.001% | 0.025% / 0.017% | 회귀 없음, 좋아짐 |
| ordinary scan (COUNT, SUM) | 65,975,494 | 65,940,532 | +0.05% | 0.061% / 0.091% | 4.27% / 2.66% | 차이 없음 |
| ordinary predicate | 545,086,496 | 505,498,896 | +7.26% | 0.013% / 0.014% | 0.022% / 0.044% | 회귀 없음, 좋아짐 |
| ordinary update | 6,809,826,466 | 6,548,299,633 | +3.84% | 0.026% / 0.021% | 0.687% / 0.248% | 회귀 없음, 좋아짐 |

- `bench` 값은 20 scan 합계, `ordinary scan`과 `predicate`는 1 scan, `update`는 UPDATE 1회와 commit이다.
- start 단위 중앙값은 `analysis.txt`에 있다. 후보의 모든 start가 base의 모든 start보다 낮다(`ordinary scan` 제외).
- **2% 규칙을 넘는 경우는 없다.** 가장 나쁜 쪽도 +0.05%(좋아짐)이다.
- **ordinary scan의 start 내 spread가 2.5~4.3%인 이유.** 매 start에서 retained 첫 sample(run 1)만 약 67.8M으로 2.8% 높고 나머지 셋은 65.9~66.0M이다. base와 후보 모두 같은 패턴이다. 중앙값은 이 튀는 값에 영향받지 않고, start 사이 spread(0.06~0.09%)가 효과(0.05%)와 같은 크기다. 그래서 "차이 없음"이다. `ordinary.py`에는 spread 게이트가 없다.

## bench.py compare

| 쌍 | 인자 | exit | narrow | wide |
|---|---|---:|---:|---:|
| B1 vs C1 | `--max-overhead-percent 2` | 0 | -5.438% | -9.637% |
| B2 vs C2 | 동일 | 0 | -5.439% | -9.637% |
| B3 vs C3 | 동일 | 0 | -5.447% | -9.641% |
| C1을 baseline, B1을 candidate로 맞바꿈 | 동일 | 1 | | |

- 비교기의 부호는 overhead다. 음수가 후보가 적게 쓴다는 뜻이다(이 문서의 변화율과 반대 부호).
- exit 2(invalid 증거)는 없었다. 모든 summary가 `complete: true`다.

## cycles (참고)

| 경우 | base 중앙값 | cand 중앙값 | cand 대비 변화 | start 사이 spread base / cand |
|---|---:|---:|---:|---|
| bench narrow | 2,742,361,871 | 2,551,094,248 | +6.97% | 4.9% / 1.4% |
| bench wide | 5,020,275,456 | 4,538,332,679 | +9.60% | 0.9% / 2.2% |
| ordinary scan | 34,502,937 | 36,124,640 | -4.70% | 18.9% / 9.0% |
| ordinary predicate | 212,375,032 | 197,477,006 | +7.01% | 2.1% / 4.6% |
| ordinary update | 3,651,894,840 | 3,387,051,167 | +7.25% | 19.5% / 4.5% |

- cycles는 명령어 수와 방향이 같다(`ordinary scan` 제외). `ordinary scan`의 -4.7%는 start 사이 spread(9~19%)가 효과보다 커서 결론을 낼 수 없다. 이 sample은 약 10 ms라서 cycles가 흔들린다. 명령어 수가 판정이다.

## 한계와 limiter

- **왜 5~10%나 줄었는지는 이 측정으로 설명하지 않았다.** profile을 뜨지 않았다. PR 변경(공통 reader, grouped read)이 per-row 속성 읽기 명령어를 줄였다는 것은 추론이다. 이 측정은 "새 base에서 회귀가 없다"까지만 증명한다. 속도 개선 주장의 근거로 쓰려면 perf record가 필요하다.
- 실행한 SQL이 같은 일을 했는지는 하니스가 확인했다. scan checksum, 행 검증, UPDATE 후 전 행 검증을 통과했고(`complete: true`), 오류는 없었다.
- 후보가 base보다 5~10% 낮은 것이 새 base의 #8196(page batch) 때문인지 PR 때문인지는 구분하지 않았다. 후보는 base를 merge한 것이라 #8196은 양쪽에 모두 들어 있다.
- 측정은 모두 데이터가 buffer(4G)에 올라 있는 warm 상태이다. cold I/O는 범위 밖이다.
- OOS 크기 행, 개별 OOS 경로는 이 하니스의 범위가 아니다.

## 이상 사항

1. **후보를 다시 빌드했다.** 워크트리 설치본의 빌드 시각(19:33)이 merge commit(`855f220d5`, 19:43)보다 앞서서 다시 빌드했다(빌드 성공). 나중에 확인한 결과, 19:33 빌드는 충돌을 푼 merge 결과를 commit 직전에 빌드한 것이라 source가 `855f220d5`와 같다. 다시 빌드한 것은 결과에 영향이 없다.
2. **워크트리 설치 경로에는 설치하지 못했다.** 이 워크트리의 OOS CTest가 남긴 `cub_master` 하나가 설치 lock을 잡고 있어서, 설치가 exit 75로 실패했다. 그 master는 측정 뒤에 정리했고, 설치본은 지금 최신 빌드다.
3. **그래서 후보를 별도 환경에서 실행했다.** 같은 빌드 디렉터리에서 `cmake --install --prefix`로 작성자 로컬의 임시 디렉터리에 설치하고, 별도 databases 디렉터리, port 41205, 별도 `CUBRID_TMP`, `LD_LIBRARY_PATH`를 지정했다(`cand-alt-env.sh`, `cand-alt-conf/`). 서버가 실제로 이 prefix의 `libcubrid.so.11.5`를 로드했음을 `/proc/<pid>/maps`로 확인했다. 설치본과 빌드 산출물은 RUNPATH만 다르다(base의 설치본과 빌드 산출물도 같은 방식으로 다르다). base와 후보의 workenv를 섞지는 않았다. 다만 후보는 공식 workenv가 아니라서 이 점을 감안해야 한다. 이 prefix는 port 말고는 후보 workenv 설정을 복사한 것이다.
4. 첫 `ordinary.py` 호출은 prefix `B1_`가 대문자라서 거부됐다(rc=2). 소문자 prefix로 같은 서버에서 다시 실행했다. 측정 값에는 영향이 없다. `B1/bench`는 그 서버에서 이미 정상 완료된 값이다.
5. 후보 워크트리에서 내가 만든 `__pycache__`는 지웠고, 이후 `PYTHONDONTWRITEBYTECODE=1`로 실행했다. 후보 워크트리의 git 상태는 clean이고 HEAD는 `855f220d5`다.

## 정리 상태

- 측정에서 시작한 서버 `b8299`와 `c8299`는 start마다 `cubrid server stop`으로 멈췄다. 두 `cub_master`(base 41162, 후보 41205)는 `cubrid service stop`으로 멈췄다. 다른 사용자나 세션의 서비스는 건드리지 않았다.
- DB와 로그는 작성자 로컬에 보존했다.

## 산출물

- Git에 있는 것: 이 보고서, [`analysis.txt`](pr8299-newbase-20261110/analysis.txt)(start별 중앙값과 집계), `analyze.py`(원시 출력 디렉터리를 인자로 받아 집계를 다시 만든다).
- 작성자 로컬에만 있는 것: `base/B1..B4/`, `cand/C1..C3/`의 SQL·원시 출력·`summary.json`·`env.txt`, `bench.py compare` 출력, 빌드·설치 로그, 실행 스크립트.
