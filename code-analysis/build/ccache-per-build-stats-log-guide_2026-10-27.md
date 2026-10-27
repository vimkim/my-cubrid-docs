# ccache 빌드별 통계 로그: STATSLOG와 show-log-stats 사용 가이드

- 작성·확인일: 2026-10-27, Asia/Seoul
- 대상 독자: CUBRID CI 담당자와 [PR #8254](https://github.com/CUBRID/cubrid/pull/8254) 리뷰어
- 관련 이슈: CUBRIDQA-1681
- 질문: 공유 캐시와 누적 통계를 보존하면서 각 빌드의 hit·miss를 공식 기능으로 수집할 수 있는가?

**지원 버전에서는 `CCACHE_STATSLOG`로 job별 통계 파일을 지정하고, `ccache --show-log-stats`로 그 파일을 집계할 수 있다.** `CCACHE_NOSTATS=1`을 유지해 공유 통계 파일의 갱신을 막아도 별도 통계 로그는 기록된다. 로컬 ccache 4.5.1에서 이 조합과 병렬 집계를 확인했다.

현재 PR #8254가 대상으로 삼은 3.7.7에는 이 기능이 없다. 따라서 지금의 `CCACHE_LOGFILE + awk`를 승인하는 판단과, 이미지 업그레이드 후 전용 통계 로그로 전환하는 판단은 함께 성립한다. 이 문서는 후자의 기능과 전환 조건을 설명한다. 기존 [2026-10-21 CI 통계 확인 보고서](cubrid-ci-ccache-statistics-note_2026-10-21.md)의 실행별 관찰을 수정하거나 새 버전까지 일반화하지 않는다.

## 1. 기준 버전과 확인 범위

| 대상 | 기준 |
| --- | --- |
| CUBRID PR 소스 | `CUBRID/cubrid`, PR #8254 HEAD `f874120a2ffaa866d868c92b7fb4ea2cebfa0f46`, base `eb88ab4eab3f6ae28040d15606a884e1d3846269` |
| CUBRID 확인 파일 | [gha-ci.yml의 build job](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/.github/workflows/gha-ci.yml#L477-L569) |
| ccache 소스 | `ccache/ccache`, tag `v4.5.1`, commit `764dc83795d9a05c2a9d69f267ed86f61a253d09` |
| 독립 실행 실험 | Rocky Linux 9.6, `ccache-4.5.1-2.el9.x86_64`, `gcc-11.5.0-5.el9_5.x86_64`, 전용 임시 캐시·설정·로그 |
| 범위 밖 | CI 이미지 교체, 실제 develop push 쓰기 모드 실행, 운영 클러스터 배치 변경, 빌드 시간 개선율 측정 |

업스트림 소스 확인과 배포된 로컬 바이너리의 실행 관찰을 구분한다. 특히 오류 처리는 같은 표시 버전에서도 배포 패치나 빌드에 따라 달라질 수 있으므로, 아래의 누락 파일 결과를 모든 4.5.1 환경에 일반화하지 않는다.

### 기능 도입 버전

| 버전 | 이 문서와 관련된 변화 |
| --- | --- |
| 3.7.7 | 일반 동작 로그인 `CCACHE_LOGFILE`은 있으나 `CCACHE_STATSLOG`와 `--show-log-stats`는 없음. PR #8254는 이 환경을 대상으로 함 |
| 4.4, 2021-08-19 | `stats_log` / `CCACHE_STATSLOG`와 `--show-log-stats` 도입 |
| 4.5.1 | 이 문서에서 소스와 로컬 실행을 대조한 버전. 기계 판독용 `--print-log-stats`는 아직 없음 |
| 4.8 | 통계 로그 파일이 없을 때 `--show-log-stats`가 충돌하는 문제 수정이 릴리스 노트에 기록됨 |
| 4.10, 2024-05-29 | `--print-log-stats`와 `--format`의 tab·JSON 출력 도입 |

도입 이력은 공식 [4.4 릴리스 노트](https://ccache.dev/releasenotes.html#_ccache_4_4), [4.8 릴리스 노트](https://ccache.dev/releasenotes.html#_ccache_4_8), [4.10 릴리스 노트](https://ccache.dev/releasenotes.html#_ccache_4_10)에서 확인했다. 기능 도입 최소 버전과 실제 운영에 배포할 버전은 별도 결정이다. 4.5.1을 실험했다는 사실이 그 버전을 새 운영 이미지로 권장한다는 뜻은 아니다.

## 2. 비슷한 이름의 설정과 명령 구분

| 설정·명령 | 대상으로 하는 데이터 | 쓰임새 |
| --- | --- | --- |
| `CCACHE_DIR` | 컴파일 결과와 해당 캐시의 누적 통계 | 캐시 저장·재사용 위치 지정 |
| `CCACHE_LOGFILE` | 동작 과정과 진단 메시지 | cache miss 원인 조사, PR #8254의 `Result:` 집계 |
| `CCACHE_STATSLOG` | ccache가 기록하는 통계 이벤트 ID | 빌드별 통계 수집 |
| `ccache -s` / `--show-stats` | 캐시의 누적 통계 | 노드 캐시 상태 조회 |
| `ccache --print-stats` | 캐시의 누적 통계 | 누적 통계를 기계가 읽을 수 있는 형식으로 조회 |
| `ccache --show-log-stats` | 설정한 stats log 파일 | 그 파일에 모인 통계를 사람이 읽는 형식으로 조회 |
| `ccache --print-log-stats` | 설정한 stats log 파일 | 지원 버전에서 그 파일의 통계를 기계 판독용으로 조회 |

`CCACHE_STATSLOG`를 설정해도 `ccache -s`나 `--print-stats`의 대상이 자동으로 빌드별 로그로 바뀌지는 않는다. 별도 파일을 읽으려면 이름에 **`log`가 들어간 조회 명령**을 사용한다. 4.5.1의 명령 처리에서도 `--show-log-stats`는 `StatsLog`를 읽고, `-s`는 `PrimaryStorage`의 누적 통계를 읽는다. [명령 분기 소스](https://github.com/ccache/ccache/blob/764dc83795d9a05c2a9d69f267ed86f61a253d09/src/core/mainoptions.cpp#L516-L540)

`--show-log-stats`에는 파일 경로를 위치 인자로 붙이지 않는다. 컴파일과 조회 양쪽에서 같은 `CCACHE_STATSLOG` 설정을 사용한다.

```bash
export CCACHE_STATSLOG="$RUNNER_TEMP/ccache-stats.log"
# 이 환경을 상속하는 ccache 컴파일 호출들이 위 파일에 기록한다.
ccache --show-log-stats

# 다른 셸에서 이미 생성한 파일을 읽는 경우
CCACHE_STATSLOG=/path/to/job-stats.log ccache --show-log-stats
```

추가 항목이 필요하면 `ccache --show-log-stats -v` 또는 `-vv`를 사용한다. 설정 의미와 옵션은 [4.5.1 공식 매뉴얼](https://ccache.dev/manual/4.5.1.html#_configuration_options)에 근거한다.

## 3. NOSTATS와 함께 동작하는 이유

현재 CUBRID 워크플로는 같은 노드·모드의 캐시를 공유한다. release와 debug는 각각 `develop-release`, `develop-debug` 디렉터리를 사용한다. PR 빌드는 `CCACHE_READONLY=1 CCACHE_NOSTATS=1`로 공유 캐시의 결과와 통계 갱신을 막는다. develop push는 별도로 쓰기를 허용한다. [모드·캐시 설정](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/.github/workflows/gha-ci.yml#L487-L509), [PR 빌드 설정](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/.github/workflows/gha-ci.yml#L551-L569), [develop 쓰기 허용](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/.github/workflows/gha-ci.yml#L216-L230)

4.5.1 소스에서 컴파일 종료 경로는 다음 순서로 동작한다.

```text
이번 호출의 통계 이벤트를 메모리에 모음
  → 진단 로그에 결과 기록
  → 설정된 stats log에 결과 ID 기록
  → storage.finalize()
       → stats=false이면 공유 통계 파일 갱신을 생략
```

별도 통계 로그 기록은 `stats=false` 검사보다 먼저 일어난다. 근거는 [`log_result_to_stats_log()`와 `finalize_at_exit()`](https://github.com/ccache/ccache/blob/764dc83795d9a05c2a9d69f267ed86f61a253d09/src/ccache.cpp#L1865-L1898), [`PrimaryStorage::finalize()`](https://github.com/ccache/ccache/blob/764dc83795d9a05c2a9d69f267ed86f61a253d09/src/storage/primary/PrimaryStorage.cpp#L107-L112)이다.

따라서 `NOSTATS`를 없애거나 `-z`로 공유 카운터를 초기화할 필요가 없다. **공유 캐시 통계 갱신과 job별 통계 기록은 별개 경로**다. 다만 `CCACHE_DISABLE=1`로 ccache 자체를 우회하면 같은 종료 경로의 통계 기록을 기대할 수 없다. 위 설명은 stats log가 구성되어 있고 컴파일이 실제 ccache를 거친 경우에 적용된다.

`READONLY`만 설정했다고 통계 갱신까지 중단되는 것도 아니다. 공식 read_only 설명은 stats가 켜져 있으면 카운터를 계속 갱신한다고 명시한다. 공유 캐시·통계 쓰기를 모두 막을 때 현재의 `READONLY + NOSTATS` 조합을 유지해야 한다. [4.5.1 read_only 설명](https://ccache.dev/manual/4.5.1.html#_configuration_options)

## 4. 파일의 소유 범위와 수명

**캐시는 공유해도 되지만 stats log 파일은 job마다 달라야 한다.** `CCACHE_STATSLOG`는 파일 경로를 지정하는 기능이지, 같은 파일에 기록된 서로 다른 job을 자동으로 분리하는 기능이 아니다.

4.5.1의 [`StatsLog::log_result()`](https://github.com/ccache/ccache/blob/764dc83795d9a05c2a9d69f267ed86f61a253d09/src/core/StatsLog.cpp#L55-L68)는 파일을 append 모드로 연다. 같은 경로를 다음 빌드에도 사용하면 예전 이벤트가 남는다. 파일을 읽는 [`StatsLog::read()`](https://github.com/ccache/ccache/blob/764dc83795d9a05c2a9d69f267ed86f61a253d09/src/core/StatsLog.cpp#L30-L52)는 누적된 이벤트 ID를 세므로 시간 구간이나 job 이름을 추론해 제외하지 않는다.

운영 규칙은 다음과 같다.

1. job 전용 임시 공간에 경로를 정한다. run·attempt·mode를 이름에 포함하면 실행을 구분하기 쉽다.
2. 모든 컴파일이 시작되기 전에 부모 디렉터리를 만들고 새 파일을 준비한다. 기존 전용 파일을 재사용한다면 이 시점에만 비운다.
3. 그 job의 여러 병렬 ccache 호출에는 같은 경로를 전달한다. 다른 job에는 다른 경로를 전달한다.
4. 모든 컴파일 프로세스가 끝난 뒤 집계한다. 컴파일 중에 파일을 비우거나 회전하지 않는다.
5. 필요하면 로그·요약을 CI artifact로 보존한다. 파일은 캐시 자체가 아니므로 다음 빌드의 warm cache로 복원하지 않는다.

`export`한 환경이 실제 컴파일러 wrapper까지 도달해야 한다. 빌드 스크립트가 환경을 초기화하거나 별도 컨테이너를 띄우면 해당 경계에도 변수를 전달한다. GitHub Actions의 다른 `run` step에서는 이전 step의 셸 `export`가 자동으로 이어지지 않으므로, 경로를 job env·`GITHUB_ENV`·output 등으로 전달해야 한다. 아래 예시는 설정·빌드·집계를 **같은 step**에서 실행하는 경우다.

## 5. CUBRID CI에 적용하는 예시

다음은 지원 버전 이미지로 전환한 뒤 기존 build step에 적용할 수 있는 형태다. 현재 3.7.7 이미지에 그대로 넣는 변경안이 아니다. `CACHE_WRITE`, `BUILD_ARGS`, `MODE`와 `CCACHE_DIR`은 기존 job 설정을 사용한다.

```bash
set -euo pipefail

[ "$CACHE_WRITE" = 'true' ] || export CCACHE_READONLY=1 CCACHE_NOSTATS=1
export CCACHE_TEMPDIR="$RUNNER_TEMP/ccache-tmp"
export CCACHE_STATSLOG="$RUNNER_TEMP/ccache-stats-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${MODE}.log"
mkdir -p "$CCACHE_TEMPDIR"
: > "$CCACHE_STATSLOG"

build_rc=0
# BUILD_ARGS는 기존 workflow가 정의한 인자 문자열이다.
# shellcheck disable=SC2086
/entrypoint.sh build $BUILD_ARGS || build_rc=$?

if [ -s "$CCACHE_STATSLOG" ]; then
  echo 'ccache, this build:'
  ccache --show-log-stats || echo '::warning::could not summarize this build ccache stats log'
else
  echo '::warning::no ccache statistics were recorded for this build'
fi

exit "$build_rc"
```

이 형태는 빌드 실패 후에도 남은 통계를 출력하되 **빌드 종료 코드를 보존**한다. 통계 조회 성공을 빌드 성공으로 사용하지 않는다. `-s` 파일 검사는 아무 이벤트도 기록되지 않은 파일을 걸러 내는 최소 검사다. 파일에 uncacheable 이벤트만 있을 수도 있으므로, 파일 크기만으로 hit율의 분모가 양수라고 판단하지 않는다.

공유 캐시 누적치도 필요하면 별도의 제목 아래 `ccache -s`를 계속 출력할 수 있다. 이 출력은 job별 요약과 이름을 구분한다. 기존 `CCACHE_LOGFILE`은 디버깅이 필요할 때 병행할 수 있지만, 빌드별 집계를 위해 진단 메시지 문구를 다시 파싱할 필요는 없어진다.

### 기계 판독용 출력은 4.10부터 별도 선택

4.10의 지원 옵션은 다음과 같다.

```bash
ccache --print-log-stats
ccache --print-log-stats --format=json
```

첫 명령의 기본 형식은 tab 구분이다. 자동 집계에는 사람이 읽는 `--show-log-stats`의 배치나 공백을 파싱하는 대신 이 인터페이스를 사용한다. 이것을 4.5.1 예시에 섞으면 지원하지 않는 옵션이 된다. `--print-stats`는 이름이 비슷해도 누적 통계를 대상으로 하므로 대체 명령이 아니다. [4.10 기계 판독 옵션](https://ccache.dev/manual/4.10.html#_options_for_scripting_or_debugging)

## 6. 출력에서 무엇을 읽어야 하나

1 direct hit와 1 miss를 발생시킨 4.5.1 실험의 핵심 출력은 다음과 같다.

```text
Summary:
  Hits:           1 / 2 (50.00 %)
    Direct:       1 / 2 (50.00 %)
    Preprocessed: 0 / 1 (0.00 %)
  Misses:         1
    Direct:       1
    Preprocessed: 1
```

빌드 전체 hit율은 위 `Summary`의 `Hits`를 읽는다. `Preprocessed: 0 / 1`은 전체 두 번 중 preprocessed hit가 0이라는 비율과 분모가 다르다. direct hit로 끝난 호출은 전처리 조회 단계로 내려가지 않는다. 따라서 표시된 하위 단계 비율을 더하거나 평균 내어 전체 hit율을 만들면 안 된다.

같은 miss 하나에 `cache_miss`, `direct_cache_miss`, `preprocessed_cache_miss`, `primary_storage_miss`가 함께 기록될 수 있다. 이것을 네 번의 컴파일 miss로 합산해서도 안 된다. 아래는 위 실험의 통계 로그다. `#`로 시작하는 줄은 입력 파일을 설명하는 주석이다.

```text
# hot.c
direct_cache_hit
primary_storage_hit
# cold.c
cache_miss
direct_cache_miss
preprocessed_cache_miss
primary_storage_miss
```

`Primary storage` 같은 저장소 조회 지표와 컴파일 결과 재사용 지표는 목적이 다르다. 빌드의 캐시 재사용률에는 `Summary`의 hit·miss를 사용한다. 또한 이 수치는 ccache 호출에 대한 기록이다. ccache launcher와 ccache를 가리키는 compiler wrapper를 중첩하면 오브젝트 하나에 호출 여러 개가 생길 수 있다. [기존 CBRD-27124 실측의 중첩 구성 관찰](../../cbrd-27124/ccache-commit-change-measurement_2026-10-21.md#카운터와-오브젝트-수의-차이)도 참고할 수 있다.

## 7. 독립 실행으로 확인한 결과

2026-10-27 로컬 ccache 4.5.1과 GCC 11.5.0을 사용했다. 기존 `CCACHE_*` 환경을 제거하고, 전용 설정 파일·캐시·임시 디렉터리를 사용했다. `/usr/bin/gcc`를 직접 지정하여 호스트 PATH의 다른 ccache wrapper가 중첩되지 않게 했다. 운영 캐시를 초기화하거나 CI를 트리거하지 않았다.

공유 stats 보존은 조회 숫자만이 아니라 캐시 내 stats 파일의 수정 시각과 SHA-256, `--print-stats` 사전 전체가 실험 전후 동일한지로 확인했다. 확인 항목과 결과는 다음과 같다.

| 조건 | 관찰 결과 |
| --- | --- |
| `READONLY=1 NOSTATS=1`, hot 1회·cold 1회 | 로그 요약 `Hits 1 / 2 (50.00 %)`, 공유 stats 보존 |
| 같은 로그 경로에 hot 1회 추가 | `Hits 2 / 3 (66.67 %)`. 파일이 append됨을 확인 |
| `NODIRECT=1`, hot 1회 | preprocessed hit `1 / 1 (100.0 %)` |
| 32개 작업자로 총 80회 컴파일, job 로그 2개 | 각 로그가 `20 hit / 20 miss`, 50%. 공유 stats 보존 |
| 빈 로그 파일 | 조회 rc 0, `Hits 0 / 0`. hit율 수치 없음 |
| 설정한 경로에 파일 없음 | 이 로컬 바이너리는 rc 0, 빈 요약 출력. 모든 버전의 보장으로 사용하지 않음 |
| stats log 설정 자체 없음 | rc 1, `No stats log has been configured` |
| `gcc -E`만 실행 | `Uncacheable 1`, `Hits 0 / 0`. 파일이 있어도 hit율 표본이 없을 수 있음 |
| 읽기 전용 설정에서 문법 오류 소스 컴파일 | 컴파일 rc 1, 로그에는 miss 기록. 로그·집계 존재가 빌드 성공을 뜻하지 않음 |
| stats를 켠 읽기 전용 실행 | job 요약은 50%, 공유 누적 카운터도 변경. READONLY 단독은 통계 갱신 금지가 아님 |

이 실험은 별도 파일 집계와 설정 조합을 확인한다. 실제 CUBRID 전체 빌드의 캐시 hit율이나 성능 비용을 측정한 실험은 아니다. 4.10의 JSON 출력도 위 4.5.1 바이너리로 실행 검증한 항목이 아니며, 공식 인터페이스를 설명한 것이다.

아래 최소 재현 절차를 그대로 실행해도 `Hits 1 / 2 (50.00 %)`가 출력됐다. CI 예시의 종료 코드 처리는 빌드·조회 명령을 대역으로 바꾸어 확인했다. 빌드 성공·실패와 집계 성공·실패를 조합했을 때 원래 빌드 종료 코드 0 또는 37이 유지됐다. 이는 예시 셸의 제어 흐름 검증이며 실제 CI 실행 검증과 구분한다.

### 최소 재현 절차

다음은 같은 종류의 hit·miss를 만드는 작은 실험이다. `/usr/bin/ccache`와 `/usr/bin/gcc`가 각각 ccache와 실제 GCC인 Linux 환경을 전제로 한다. 다른 환경에서는 실제 바이너리 경로를 지정한다. 임시 디렉터리는 결과 확인을 위해 남겨 둔다.

```bash
set -euo pipefail

experiment_dir=$(mktemp -d)
mkdir -p "$experiment_dir/tmp"
printf 'compiler_check = content\n' > "$experiment_dir/ccache.conf"
printf 'int hot(void) { return 7; }\n' > "$experiment_dir/hot.c"
printf 'int cold(void) { return 11; }\n' > "$experiment_dir/cold.c"

(
  cd "$experiment_dir"
  env -i PATH=/usr/bin:/bin \
    CCACHE_DIR="$experiment_dir/cache" \
    CCACHE_CONFIGPATH="$experiment_dir/ccache.conf" \
    CCACHE_TEMPDIR="$experiment_dir/tmp" \
    bash --noprofile --norc <<'SH'
set -eu
/usr/bin/ccache --version
# 먼저 hot.c만 캐시에 채운다.
/usr/bin/ccache /usr/bin/gcc -c hot.c -o hot.o

export CCACHE_READONLY=1 CCACHE_NOSTATS=1
export CCACHE_STATSLOG="$PWD/job-stats.log"
: > "$CCACHE_STATSLOG"
/usr/bin/ccache /usr/bin/gcc -c hot.c -o hot.o
/usr/bin/ccache /usr/bin/gcc -c cold.c -o cold.o
/usr/bin/ccache --show-log-stats
SH
)
printf 'Experiment files: %s\n' "$experiment_dir"
```

처음 캐시를 채울 때 발생한 miss는 `CCACHE_STATSLOG`를 설정하기 전이므로 job 요약에 포함되지 않는다.

## 8. 현재 방식과의 비교 및 전환 조건

| 방법 | 현재 구성에서 빌드별 분리가 가능한가 | 주요 제약 |
| --- | --- | --- |
| 공유 `-s`의 전후 차이 | PR 카운터는 증가하지 않으며 다른 빌드의 갱신이 섞일 수 있음 | `NOSTATS`를 없애는 것만으로 동시 실행을 구분할 수 없음 |
| 공유 캐시의 `-z → build → -s` | 불가능 | develop 누적을 초기화하고 다른 빌드와 간섭함 |
| `CCACHE_LOGFILE + awk` | job마다 로그를 분리하면 가능 | 3.7.7에서도 사용 가능하지만 진단 메시지 문구에 의존함 |
| `CCACHE_STATSLOG + --show-log-stats` | job마다 로그를 분리하면 가능 | 4.4 이후 지원 버전이 필요하며 집계는 ccache가 담당함 |

PR #8254는 현재 3.7.7에서 요구사항을 충족하는 작은 변경으로서 타당하다. 이후 전용 기능에 집계를 맡기면 진단 로그 문구 변경을 따라가는 부담을 줄일 수 있다. 다만 이 판단만으로 CI 이미지나 캐시 저장 형식의 호환성까지 확정할 수는 없다.

전환할 때는 다음을 확인한다.

1. 실제 컴파일에 쓰이는 ccache의 버전·경로와 CI 이미지 digest를 고정한다. 조회 명령만 신버전이고 컴파일 wrapper는 구버전인 상태를 피한다.
2. 3.x와 도입 대상 버전의 캐시 형식 호환성, 기존 캐시 재사용·재가열 방침을 확인한다. 운영 캐시를 직접 시험 대상으로 삼지 않는다.
3. PR의 `READONLY + NOSTATS`와 develop의 쓰기 허용이라는 기존 방침을 유지한 채 두 실행 종류의 전용 로그를 확인한다.
4. 동시 job, run 재실행, release/debug를 구분하고 append로 이전 값이 섞이지 않는지 확인한다.
5. 빈 로그, ccache를 거치지 않은 빌드, 실패한 빌드, 집계 실패를 구분한다. 빌드 종료 코드를 보존한다.
6. 같은 호출 집합에서 기존 집계와 전용 집계를 대조하고 필요하면 실행 시간·로그량도 측정한다. 확인 후 수동 awk 집계를 제거한다.

실제 PR·develop 빌드에서 기존 정책과 의도한 측정 범위가 유지되는 것을 확인해야 운영 도입을 마쳤다고 판단할 수 있다.

## 9. 참고 자료

- [ccache 4.5.1 공식 매뉴얼](https://ccache.dev/manual/4.5.1.html): `stats_log`, `read_only`, `stats`와 사람용 집계 옵션.
- [ccache 4.10 공식 매뉴얼](https://ccache.dev/manual/4.10.html): `--print-log-stats`, `--format`.
- [공식 릴리스 노트](https://ccache.dev/releasenotes.html): 4.4 기능 도입, 4.8 누락 파일 오류 수정, 4.10 기계 판독 출력 도입.
- [v4.5.1 / ccache.cpp](https://github.com/ccache/ccache/blob/764dc83795d9a05c2a9d69f267ed86f61a253d09/src/ccache.cpp#L1865-L1898): 전용 로그와 공유 통계의 종료 시 처리 순서.
- [v4.5.1 / StatsLog.cpp](https://github.com/ccache/ccache/blob/764dc83795d9a05c2a9d69f267ed86f61a253d09/src/core/StatsLog.cpp#L30-L68): append와 집계.
- [v4.5.1 / PrimaryStorage.cpp](https://github.com/ccache/ccache/blob/764dc83795d9a05c2a9d69f267ed86f61a253d09/src/storage/primary/PrimaryStorage.cpp#L107-L112): `stats=false`일 때 공유 통계 갱신 생략.
- [PR #8254의 고정 리비전](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/.github/workflows/gha-ci.yml#L551-L569): 현재 3.7.7용 로그 집계.
