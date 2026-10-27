# PR #8298: develop 캐시를 지워야 올바른 적중률을 측정할 수 있는가

- 분석일: 2026-10-27, Asia/Seoul
- 대상: CBRD-27124 구현 검토자와 CI 담당자
- 관련: [CBRD-27124](https://jira.cubrid.org/browse/CBRD-27124), [PR #8298](https://github.com/CUBRID/cubrid/pull/8298), 빌드별 계측 [PR #8254](https://github.com/CUBRID/cubrid/pull/8254), work-tracker #520의 A→B 측정 단계

**운영 develop 캐시를 지울 필요는 없다.** #8254의 빌드별 수치는 해당 빌드의 실제 ccache hit/miss를 기록한다. 다만 기존 캐시의 초기 상태를 통제하지 않았고, PR은 수정 후 결과를 저장하지 않으므로 이 수치만으로 헤더 분리의 개선 효과를 판정할 수 없다. 수정 전후에 각각 새 전용 캐시를 만들고, A를 저장한 뒤 캐시를 유지한 채 처음 보는 동일-tree 커밋 B를 측정해야 한다.

이 문서는 원인 분석과 그 실험의 실행 초안을 제공한다. 이번에 수행한 것은 소스·공식 문서·기존 CI 로그의 재확인과 문서 검증이다. **아래 전체 빌드 실험은 실행하지 않았다.** 운영 캐시·카운터, CI 정책, 소스·TC 및 원격 게시를 변경하지 않았다. SQL 실패 분석 #533과 캐시 도구 교체 survey는 별도 범위다.

## 1. 근거의 revision과 적용 범위

| 대상 | 확인한 revision 또는 원본 |
| --- | --- |
| 수정 전 A | `CUBRID/cubrid`의 `2d925cb8685600135eb1fb1781811f6b45fdecb0` |
| 수정 후 A | `0d2a76e60f944be0ababe9c466766c553189fcda`, tree `7ba3a7225217f9dd7957478a28118973b9ab5aba`. 부모가 위 수정 전 A |
| 현재 PR 조회 | head 저장소 `vimkim/cubrid`, branch `CBRD-27124-isolate-build-version`, base `develop`. 조회 시 head도 위 수정 후 A |
| PR 실행 | [run 40487586838](https://github.com/CUBRID/cubrid/actions/runs/40487586838), attempt 1, `issue_comment`, 완료/failure. 실제 checkout은 수정 후 A |
| 실행 workflow | run API의 `head_sha`는 수정 전 A. 현재 원격 develop도 같은 SHA. PR 소스 SHA와 구분 |
| workflow 원문 | 해당 revision의 `.github/workflows/gha-ci.yml` blob `1bdbdad43428ecf9a356b4345027fcdf53584491`. 수정 후 A에서도 동일 blob이며 실제 job의 명령·env와 대조 |
| 이미지 소스 | `CUBRID/cubridci`, `build_rl8.10`의 `4ea4e8a714078e11002d9402b9011e647c473bea` |
| ccache 구현 | 공식 tag `v3.7.7`, commit `26912b280b839e102482db8c9e63f00a95b58486` |

workflow는 `cubridci/cubridci:build_rl8.10`이라는 mutable 태그를 지정한다. 기존 GCC8 최소 실험은 GCC 8.5.0/ccache 3.7.7이었지만, 이것이 PR 실행 이미지와 같은 digest라는 근거는 없다. 이번에 다시 읽은 네 job 로그에는 `ccache -V`, `ccache -p`, 이미지 digest가 없다. 따라서 **3.7.7의 소스 동작과 당시 PR 바이너리의 정확한 배포 버전·전체 설정을 구분한다.** 현재 로컬 이미지나 태그 조회만으로 과거 실행의 digest를 확정하지 않는다. [workflow 이미지 지정](https://github.com/CUBRID/cubrid/blob/2d925cb8685600135eb1fb1781811f6b45fdecb0/.github/workflows/gha-ci.yml#L477-L509), [기존 GCC8 실험](CBRD-27124-build-version-verification_0d2a76e_codex.md#gcc-8에서도-매크로-변경은-miss를-만드는가)

## 2. clear가 바꾸는 상태부터 구분한다

사용자의 표현은 결과 캐시, 누적 카운터, 기존 오브젝트 중 어느 것을 뜻할 수 있다. 각각의 목적과 효과가 달라 이 분석에서는 다음과 같이 구분한다.

| 조작 | 바꾸는 상태 | 그대로 남는 상태와 측정상의 의미 |
| --- | --- | --- |
| `ccache -C` / `--clear` | 결과·manifest를 삭제하고 캐시 사용량을 재계산 | **3.7.7에서는 누적 hit/miss를 유지**한다. cold 초기 상태를 만드는 조작이지 job별 통계 분리 수단이 아님 |
| `ccache -z` / `--zero-stats` | 초기화 가능한 누적 카운터와 초기화 시각 | 결과·manifest 및 사용량 유지. 공유 writer가 있으면 이후 수치에도 다른 빌드가 섞임 |
| `./build.sh … clean build` | 선택한 설치·빌드 디렉터리 정리 후 재구성·빌드 | 빌드 밖의 `CCACHE_DIR` 유지. 컴파일 명령을 다시 실행시키는 역할 |
| 새 단계별 `CCACHE_LOGFILE` | 그 단계에서 기록할 이벤트의 경계 | 결과 캐시와 누적 카운터를 변경하지 않음. 기존 파일은 append되므로 새 경로 필요 |

3.7.7의 [`wipe_fn()`](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/cleanup.c#L223-L269)은 `stats` 파일을 보존한다. 사용량 갱신은 기존 통계에서 파일 수·크기만 바꾼다. [`stats_zero()`](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/stats.c#L639-L715)는 초기화 제외 항목을 유지한다. 따라서 `-C`와 `-z`를 같은 의미로 사용하면 안 된다.

실제 CI entrypoint의 소스 계약은 `./build.sh -p $CUBRID $@ clean build`다. `build.sh`는 빌드·설치 디렉터리를 지우고, ExternalProject의 상태도 빌드 디렉터리 아래에 있으므로 외부 라이브러리 작업이 다시 필요하다. 그러나 ccache는 별도 `/home/ci/cache/ccache/develop-{release,debug}`에 있다. 외부 라이브러리도 컴파일 명령은 실행하면서 기존 결과를 hit할 수 있다. configure·링크·설치 비용은 별도로 남는다. [entrypoint](https://github.com/CUBRID/cubridci/blob/4ea4e8a714078e11002d9402b9011e647c473bea/docker/ci/docker-entrypoint.sh#L124-L143), [clean 구현](https://github.com/CUBRID/cubrid/blob/0d2a76e60f944be0ababe9c466766c553189fcda/build.sh#L162-L195), [ExternalProject 위치](https://github.com/CUBRID/cubrid/blob/0d2a76e60f944be0ababe9c466766c553189fcda/3rdparty/CMakeLists.txt#L93-L104)

## 3. 기존 CI 수치는 정확한가, 공정한 비교인가

### 해당 빌드의 재사용률이라는 의미는 있다

#8254 이후 build step은 job 임시 경로의 `CCACHE_LOGFILE`에서 direct hit, preprocessed hit, miss를 센다. 공유 `ccache -s`와 별도의 출력이다. 3.7.7의 [`stats_flush_to_file()`](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/stats.c#L439-L495)은 이번 호출의 `Result:`를 기록한 다음 `stats=false`를 검사한다. 그러므로 `NOSTATS=1`이어도 빌드별 로그에 결과가 남으며 과거 공유 카운터가 합산되는 구조가 아니다. [실제 집계 코드](https://github.com/CUBRID/cubrid/blob/2d925cb8685600135eb1fb1781811f6b45fdecb0/.github/workflows/gha-ci.yml#L551-L569)

원본 네 job을 다시 조회해 아래 결과와 각각 바깥 Ninja의 C/C++ object compile 작업 1,251개를 확인했다. hit율의 분모는 `direct + preprocessed + miss`이며 uncacheable 호출을 제외한다.

이는 계측의 입력 경계와 출력된 집계를 확인한 것이다. 원시 `CCACHE_LOGFILE`은 보존된 job 출력에 없으므로 모든 병렬 이벤트가 누락 없이 파싱되었는지까지 재검증한 것은 아니다. 이후 실험은 아래 호출별 로그를 보존해 이 한계도 해소한다.

| 빌드 | 실제 소스 | direct | preprocessed | miss | 호출 분모 | 이번 빌드 hit율 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| [기준 Release](https://github.com/CUBRID/cubrid/actions/runs/40481418559/job/122112434651) | `2d925cb` | 1,919 | 1,175 | 83 | 3,177 | 97.39% |
| [PR Release](https://github.com/CUBRID/cubrid/actions/runs/40487586838/job/122133226817) | `0d2a76e` | 1,919 | 699 | 643 | 3,261 | 80.28% |
| [기준 OptDebug](https://github.com/CUBRID/cubrid/actions/runs/40481418559/job/122112434693) | `2d925cb` | 1,916 | 16 | 1,245 | 3,177 | 60.81% |
| [PR OptDebug](https://github.com/CUBRID/cubrid/actions/runs/40487586838/job/122133226809) | `0d2a76e` | 1,916 | 16 | 1,329 | 3,261 | 59.25% |

대조적으로 `ccache -s`의 누적 hit율은 기준/PR에서 Release가 모두 89.21%, OptDebug가 모두 60.19%였다. PR OptDebug 로그의 누적 카운터는 `164133 / 1838 / 109756`이지만 같은 job의 빌드별 카운터는 `1916 / 16 / 1329`다. 전자를 이번 PR의 수치로 읽으면 틀리며, 후자가 이번 분석 대상이다.

### 헤더 분리의 개선율은 아직 증명하지 못했다

기준은 수정 전 develop writer의 빌드이고 PR은 수정 후 구조를 처음 읽는 readonly 빌드다. 캐시 내용·배치 노드·입력 이력의 동일성이 통제되지 않았다. 헤더 분리는 이전 구조에서 정의하던 매크로를 제거하므로 수정 전 결과와 수정 후 최초 입력이 달라질 수 있다. 이를 수정 후 A→B의 재사용 실패로 해석할 수 없다.

현재 OptDebug의 hit 수는 양쪽 모두 1,932이며 miss가 84개 늘었다. 바깥 compile 작업 수가 같다는 사실만으로 추가 84 miss의 소속이나 원인을 확정할 수 없다. 전체 hit는 엔진, CCI, Manager, 3rdparty, configure probe 및 가능한 wrapper 중첩의 영향을 함께 받는다. 현재 보존된 합계에는 이 구분이 없으므로 **1,932 hit를 모두 3rdparty라고 배정하거나 엔진 hit율을 역산하지 않는다.** 과거 로컬 구성의 중첩은 관측됐지만 이번 CI의 중첩 여부는 최종 compiler argv와 실행 경로로 추가 확인해야 한다. [과거 호출 수와 오브젝트 수 차이](ccache-commit-change-measurement_2026-10-21.md#카운터와-오브젝트-수의-차이)

로컬 수정 후 99.07%는 GCC11/ccache4.5.1/Debug에서 수정 후 A 캐시를 채운 뒤 동일-tree 커밋의 오브젝트를 제거한 결과다. CI의 GCC·경로·빌드 범위·초기 캐시 조건과 달라 CI 59.25%와 직접 뺄 수 없다. [기존 실측과 한계](CBRD-27124-build-version-verification_0d2a76e_codex.md)

## 4. 이전 develop 결과가 남으면 false hit가 되는가

**캐시 항목이 오래됐다는 사실만으로 잘못된 결과를 반환하지는 않는다.** 디렉터리 이름 `develop-debug`나 Git branch가 correctness key를 대신하지 않는다. 3.7.7은 다음 경로로 실제 입력을 검증한다.

| 입력 | 검증 경로 |
| --- | --- |
| 컴파일러·옵션·경로 | 공통 키에 compiler 식별, 관련 인자, debug CWD 등을 반영. CI는 `CCACHE_COMPILERCHECK=content`를 지정 |
| 소스·포함 헤더 | direct key로 manifest 후보를 찾고 현재 include 내용 등을 검증 |
| direct 불일치 | 전처리 결과와 관련 입력이 같으면 preprocessed hit 가능. 다르면 실제 컴파일 |

근거는 [`calculate_common_hash()`](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/ccache.c#L1854-L1945), [`calculate_object_hash()`](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/ccache.c#L2214-L2284), [`verify_object()`](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/manifest.c#L364-L444), [lookup 모드 설명](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/doc/MANUAL.adoc#L825-L895)이다. 따라서 이전 항목 중 입력이 같은 결과를 재사용하는 것은 유효한 hit다. 변경된 매크로가 전처리에서 사라지는 경우와 매크로 디버그 정보에 남는 경우도 구분한다. 기존 GCC8 최소 실험은 후자를 지지하지만 이번 CI 전체 hit의 소속을 증명하지 않는다.

false hit 자체가 불가능하다는 결론도 아니다. 실제 `sloppiness`, 무시하는 헤더 설정, compiler wrapper 식별, hardlink·저장소 손상 등이 입력 검증을 약화할 수 있다. 현재 실행에서 이 문제가 발생했다는 증거는 없다. 의심되는 hit는 **같은 B·최종 argv·경로에서 cache 결과와 `CCACHE_DISABLE=1` 결과를 비교**해야 한다. 삭제 후 문제가 사라지는 것만으로 누락된 key나 손상 원인을 구분할 수 없다. [공식 corruption 조사 범위](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/doc/MANUAL.adoc#L1237-L1256)

## 5. PR 재실행으로 수정 후 캐시를 데울 수 있는가

실제 PR job env는 `CACHE_WRITE: false`, `CCACHE_COMPILERCHECK: content`, `CCACHE_MAXSIZE: 10G`였다. workflow가 여기에 `READONLY=1 NOSTATS=1`을 더한다. develop push는 쓰기를 허용하지만 이 PR의 최초 빌드나 단순 재실행은 수정 후 결과와 manifest를 저장하지 않는다. readonly miss는 실제 컴파일로 우회한다. [writer 선택](https://github.com/CUBRID/cubrid/blob/2d925cb8685600135eb1fb1781811f6b45fdecb0/.github/workflows/gha-ci.yml#L215-L230), [readonly miss](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/ccache.c#L4107-L4126), [manifest 쓰기 제한](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/ccache.c#L1372-L1381)

같은 SHA는 `$CI_BUILD_ROOT/$BUILD_NS/$SHA/$MODE/$BUILD_SENTINEL`이 있고 `force_build`가 아니면 source/build step을 생략한다. 따라서 단순 rerun은 컴파일 표본조차 없을 수 있다. 강제로 빌드를 실행하더라도 readonly 정책이 A를 저장해 주지는 않는다. 강제 재실행만으로 통제된 warm-cache 비교가 완성되지 않는다. [reuse 조건과 build 생략](https://github.com/CUBRID/cubrid/blob/2d925cb8685600135eb1fb1781811f6b45fdecb0/.github/workflows/gha-ci.yml#L530-L555)

## 6. 운영 캐시를 보존하는 최소 실험

### 실행 전 고정할 환경

우선 OptDebug 한 모드에 한정한다. Release·Debug 확대와 반복 시간 측정은 별도 단계다. 실제 사용 이미지의 digest, `/entrypoint.sh` 해시, compiler/ccache의 경로·버전·해시, `ccache -p`, CMake·Ninja 버전, cgroup CPU·병렬성, submodule SHA를 기록한다. 과거 digest를 확보하지 못하면 선택한 새 digest에서의 통제 실험으로 보고하며 과거 실행의 동일 환경 재현이라고 부르지 않는다.

이미지 소스는 `CC="ccache gcc"`, `CXX="ccache g++"`를 설정하지만 이것만으로 최종 실행 경로를 확정할 수 없다. `type -a`, `readlink -f`, `CMakeCache.txt`의 compiler/launcher, `compile_commands.json` 및 ccache의 argv를 대조한다. 현재 CUBRID의 GCC OptDebug 옵션에는 `-O2 -finline-functions -ggdb3 … -ggdb`가 들어간다. 아래의 명시적 compiler 경로와 단일 wrapper 구성이 실환경과 다르면 그 차이를 먼저 기록한다. `-ggdb3`를 빼서 수치만 높이지 않는다. [Dockerfile](https://github.com/CUBRID/cubridci/blob/4ea4e8a714078e11002d9402b9011e647c473bea/docker/ci/Dockerfile#L70-L94), [OptDebug 옵션](https://github.com/CUBRID/cubrid/blob/0d2a76e60f944be0ababe9c466766c553189fcda/CMakeLists.txt#L201-L232)

3.7.7에는 `CCACHE_NAMESPACE`, `CCACHE_STATSLOG`, `--show-log-stats`가 없다. 이 실험은 새 `CCACHE_DIR`로 격리한다. 지원 버전의 공식 통계 기능과 혼합하지 않는다. [3.7.7 옵션](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/ccache.c#L4138-L4167), [설정 목록](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/conf.c#L397-L438), [버전별 계측 가이드](../code-analysis/build/ccache-per-build-stats-log-guide_2026-10-27.md)

### 단계와 판정 대상

| 각 arm의 단계 | 캐시·산출물 상태 | 쓰기 정책 | 무엇을 판정하는가 |
| --- | --- | --- | --- |
| A cold | 새 빈 전용 캐시, clean build | writable | A 저장과 최초 비용. 빌드 내부 중복으로 hit가 생길 수 있음 |
| 같은 A warm | A 캐시 유지, 다시 clean build | readonly + nostats | 컴파일이 실제 실행될 때의 동일 A 재사용 대조군 |
| 처음 보는 B | A와 같은 Git tree, A 캐시 유지, clean build | readonly + nostats | 커밋 identity만 바뀐 입력의 재사용 |

수정 전과 수정 후는 캐시를 공유하지 않는다. **각 arm의 A→B 사이에는 캐시를 지우지 않는다.** 각 단계 로그를 분리하고 B 적중률에 cold miss를 합산하지 않는다. B가 이전에 들어갈 기회가 없는 새 디렉터리만 사용한다. eviction이 발생해 A 결과가 사라지면 입력 무효화와 구분해야 하므로 사용량·cleanup도 기록한다.

### 실행용 셸 초안

아래는 이후 실험용이며 이번에 실행한 명령이 아니다. 선택·기록한 이미지 안에서 `/measurement`에 **새 실험 디렉터리만** 마운트한다. source를 `/measurement/cubrid`에 전체 이력으로 복제하고 두 A commit이 존재하는지 확인한다. 운영 캐시, 개발 checkout, 실제 CI artifact 경로는 마운트하지 않는다. 두 arm 모두 같은 컨테이너 내부 경로를 사용한다. host에서 새 디렉터리를 준비하는 예시는 다음과 같다.

```bash
set -euo pipefail
experiment_dir=$(mktemp -d /mnt/nvme/data-5/tmp/cbrd27124-isolated-XXXXXXXX)
git clone --no-hardlinks --no-checkout \
  /home/vimkim/gh/cb/CBRD-27124-isolate-build-version "$experiment_dir/cubrid"
printf '%s\n' "$experiment_dir"
# 기록한 image@sha256 digest로 실행하고 이 디렉터리만 /measurement에 연결한다.
# 아래 본문을 /measurement/run.sh로 저장한다. 기존 CI workflow는 실행하지 않는다.
```

본문은 native `build.sh`의 clean/configure/build/install 경로를 사용한다. `-c`의 compile database 출력은 계측용이다. 타이밍·CPU 비교를 주장하는 실험은 아니며 두 arm에 같은 계측을 적용한다.

```bash
set -euo pipefail
cd /measurement/cubrid
test -d .git
git switch --detach 2d925cb8685600135eb1fb1781811f6b45fdecb0
test ! -e VERSION-DIST
test "$(cat VERSION)" = 11.5.0
test "$(/usr/bin/ccache --version | head -n 1)" = 'ccache version 3.7.7'
# /usr/bin/gcc와 g++는 ccache symlink가 아닌 실제 compiler여야 한다.
test "$(readlink -f /usr/bin/gcc)" != "$(readlink -f /usr/bin/ccache)"
test "$(readlink -f /usr/bin/g++)" != "$(readlink -f /usr/bin/ccache)"
while IFS= read -r variable; do unset "$variable"; done < <(compgen -A variable CCACHE_)
mkdir -p /measurement/tools /measurement/cache /measurement/evidence
{
  /usr/bin/ccache --version
  /usr/bin/gcc --version
  /usr/bin/g++ --version
  cmake --version
  ninja --version
  sha256sum /usr/bin/ccache /usr/bin/gcc /usr/bin/g++ /entrypoint.sh
  type -a ccache gcc g++
} > /measurement/evidence/toolchain.txt 2>&1
cat > /measurement/ccache.conf <<'CONF'
compiler_check = content
max_size = 10G
direct_mode = true
read_only = false
stats = true
hard_link = false
sloppiness =
CONF
cat > /measurement/tools/ccache <<'WRAPPER'
#!/bin/bash
set -euo pipefail
call_log=$(mktemp "$MEASUREMENT_CALLS/call.XXXXXXXX.log")
printf '%s\0' "$PWD" "$@" > "$call_log.argv0"
exec env CCACHE_LOGFILE="$call_log" /usr/bin/ccache "$@"
WRAPPER
chmod +x /measurement/tools/ccache
export PATH="/measurement/tools:$PATH"
export CC='ccache /usr/bin/gcc' CXX='ccache /usr/bin/g++'
unset CMAKE_C_COMPILER_LAUNCHER CMAKE_CXX_COMPILER_LAUNCHER
export CCACHE_CONFIGPATH=/measurement/ccache.conf
export GIT_AUTHOR_NAME='Cache measurement' GIT_COMMITTER_NAME='Cache measurement'
export GIT_AUTHOR_EMAIL=cache@example.invalid GIT_COMMITTER_EMAIL=cache@example.invalid

measure() {
  local name=$1 policy=$2 build_rc=0
  local stage="/measurement/evidence/$arm/$name"
  mkdir -p "$stage/calls"
  export MEASUREMENT_CALLS="$stage/calls"
  export CCACHE_TEMPDIR="$stage/tmp"
  mkdir -p "$CCACHE_TEMPDIR"
  unset CCACHE_READONLY CCACHE_NOSTATS
  if [ "$policy" = readonly ]; then export CCACHE_READONLY=1 CCACHE_NOSTATS=1; fi
  /usr/bin/ccache -p > "$stage/ccache-config.txt"
  /usr/bin/ccache --print-stats > "$stage/counters-before.tsv"
  git rev-parse HEAD 'HEAD^{tree}' > "$stage/source.txt"
  git submodule status --recursive > "$stage/submodules.txt"
  ./build.sh -m optdebug -b /measurement/build -p /measurement/install \
    -c '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON' clean build > "$stage/build.log" 2>&1 || build_rc=$?
  printf '%s\n' "$build_rc" > "$stage/build.rc"
  /usr/bin/ccache --print-stats > "$stage/counters-after.tsv"
  # 호출 파일에 원본 Result, cwd, argv와 소스 정보를 보존한다.
  awk '/Result: cache hit \(direct\)/ {d++}
       /Result: cache hit \(preprocessed\)/ {p++}
       /Result: cache miss/ {m++}
       END {t=d+p+m; if(t) printf "direct=%d preprocessed=%d miss=%d rate=%.2f%%\n",d,p,m,100*(d+p)/t;
            else print "NO_HIT_MISS_SAMPLE"}' "$stage"/calls/call.*.log > "$stage/summary.txt"
  [ "$build_rc" -eq 0 ] || return "$build_rc"
  cp /measurement/build/CMakeCache.txt /measurement/build/compile_commands.json "$stage/"
  cp /measurement/build/version.h "$stage/"
  if [ -f /measurement/build/build_version.h ]; then cp /measurement/build/build_version.h "$stage/"; fi
  CUBRID=/measurement/install \
    LD_LIBRARY_PATH=/measurement/install/lib:/measurement/install/cci/lib \
    /measurement/install/bin/cubrid_rel > "$stage/cubrid_rel.txt"
}

for arm in before after; do
  case "$arm" in
    before) a=2d925cb8685600135eb1fb1781811f6b45fdecb0 ;;
    after)  a=0d2a76e60f944be0ababe9c466766c553189fcda ;;
  esac
  git switch --detach "$a"
  git submodule update --init --recursive
  b=$(printf 'measurement %s, same tree\n' "$arm" | git commit-tree "$a^{tree}" -p "$a")
  test "$(git rev-parse "$a^{tree}")" = "$(git rev-parse "$b^{tree}")"
  # mktemp는 이 arm만의 빈 캐시를 만든다. -C와 -z는 사용하지 않는다.
  export CCACHE_DIR
  CCACHE_DIR=$(mktemp -d "/measurement/cache/$arm.XXXXXXXX")
  test -z "$(ls -A "$CCACHE_DIR")"
  measure cold-a writable
  measure same-a readonly
  git switch --detach "$b"
  measure unseen-b readonly
done
```

본문을 저장하고 사전 환경 기록을 준비한 뒤 host에서 실행하는 명령은 다음과 같다. `MEASUREMENT_IMAGE`에는 선택한 실제 digest를 설정한다. 과거 CI digest가 확인되지 않았다면 그 사실을 함께 기록한다.

```bash
set -euo pipefail
: "${experiment_dir:?먼저 새 실험 디렉터리를 준비한다}"
: "${MEASUREMENT_IMAGE:?저장소@sha256:digest 형태로 실제 이미지를 지정한다}"
[[ "$MEASUREMENT_IMAGE" =~ @sha256:[0-9a-f]{64}$ ]]
printf '%s\n' "$MEASUREMENT_IMAGE" > "$experiment_dir/image.txt"
podman run --rm --entrypoint /bin/bash \
  -v "$experiment_dir:/measurement" -w /measurement/cubrid \
  "$MEASUREMENT_IMAGE" /measurement/run.sh
```

설정 파일로 system/user 설정의 개입을 제한했으므로 이것은 **명시한 설정에서의 통제 실험**이다. 실 CI의 `-p`에 이와 다른 설정이 있으면 그 차이를 검토한 뒤 별도 조건으로 재현한다. writable 단계의 bool은 `CCACHE_READONLY=0`으로 끄지 않는다. 3.7.7은 그런 문자열을 오류로 처리하므로 unset과 명시적 설정을 사용한다. [boolean·설정 우선순위](https://ccache.dev/manual/3.7.7.html#_configuration)

호출별 파일은 병렬 `Result:`의 인접 행만 보고 소속을 정하는 오류를 피하기 위한 계측이다. 3.7.7의 공용 logger는 prefix·본문·개행을 별도 stdio 호출로 기록하므로 공용 로그의 모든 행이 원자적으로 기록된다고 가정하지 않는다. 호출 파일 안의 PID·command·CWD·source·object와 `.argv0`를 함께 사용한다. 절대 경로 launcher나 compiler symlink가 wrapper를 우회하면 계측 누락으로 판정한다. [logger](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/util.c#L55-L115), [호출 정보 기록](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/src/ccache.c#L3943-L3994)

### 파일별 집계와 correctness 검증

1. 각 단계의 호출을 source·CWD·object 경로로 엔진, `cubrid-cci`, `cubridmanager`, `build/3rdparty`, configure probe, 기타/미확정으로 나눈다. 각 그룹의 direct/preprocessed/miss, 기타 Result, ccache 호출 수, 고유 오브젝트 수를 함께 기록한다. 경로가 확인되지 않은 호출은 임의로 외부 라이브러리에 배정하지 않는다.
2. `compile_commands.json`과 실제 명령을 대조하여 A/B의 compiler·옵션·include·출력 경로가 같음을 확인한다. 바깥 Ninja 작업 수는 외부 make와 probe를 포함한 전체 ccache 호출 수를 대신하지 않는다. 중첩 PID나 wrapper가 보이면 호출별 수치와 고유 object를 분리한다.
3. B가 실제 다른 버전을 생성했는지 확인한다. 수정 전에는 `version.h`, 수정 후에는 `build_version.h`의 커밋 수·해시가 B여야 한다. 수정 후 공통 `version.h`는 A와 같아야 한다. 설치된 `cubrid_rel`, CPack 버전, broker/CAS 버전도 같은 B를 가리키는지 확인한다. tree만 같고 생성 버전이 안 바뀌었다면 무효 실험이다.
4. B의 hit 산출물을 다음 clean 전에 별도 evidence 경로에 보존한다. 같은 B·경로·환경에서 `CCACHE_DISABLE=1`로 clean build를 추가해 해당 오브젝트·바이너리·DWARF 매크로와 경로를 비교한다. 먼저 `cmp`/해시를 확인하고 시간·build-id 등 재현성 변수로 차이가 나면 section별로 원인을 분리한다. `cubrid_rel` 하나의 일치만으로 모든 오브젝트가 정확하다고 판정하지 않는다.
5. 예상 밖 miss/hit의 대표 object는 A/B에서 `CCACHE_DEBUG=1`로 `.ccache-input-text`와 `.ccache-log`를 보존해 비교한다. clean 전에 보존하며 이 추가 진단은 원래 측정과 별도 단계로 기록한다. [3.7.7 per-object debug](https://github.com/ccache/ccache/blob/26912b280b839e102482db8c9e63f00a95b58486/doc/MANUAL.adoc#L933-L980)

최소 성공 기준은 두 arm의 같은 A warm 대조군이 정상적으로 캐시를 재사용하고, 수정 후 B의 관계없는 엔진 object가 수정 전 B보다 재사용을 유지하며, 실제 B 산출물의 correctness도 통과하는 것이다. 수치 목표를 기존 로컬 99.07%로 고정하지 않는다. configure probe나 버전 소비자 등 정당한 miss는 남을 수 있다. 시간 개선율은 이 1회 진단으로 주장하지 않는다.

## 7. 이번에 확인한 것과 남은 검증

이번에 공식 3.7.7 소스의 초기화·키·readonly·로그 경로, 현재 원격 workflow와 PR metadata, 원본 네 CI job의 집계·env·바깥 compile 수를 확인했다. 기존 로컬 측정은 재실행하지 않았고 과거 보고서의 revision 한계를 유지했다. 작성한 Markdown과 셸 초안의 문법·상대 링크를 검증하며, 이것을 빌드 성공이나 계측의 실행 검증으로 세지 않는다.

남은 것은 실제 사용할 이미지의 digest·도구·설정을 기록한 뒤 위 전용 캐시 실험을 실행하고 파일별 결과와 uncached 대조군을 확인하는 일이다. 과거 job의 정확한 파일별 hit 소속과 추가 84 miss의 원인은 아직 열려 있다. 공유 캐시 삭제는 이 공백을 채우는 필요조건이 아니며, 빈 캐시 첫 빌드만으로 A→B 효과나 false hit를 판정하는 것도 충분하지 않다.

운영 캐시를 purge하면 다른 develop/PR 작업도 유효한 결과를 잃고 재가열 비용을 부담한다. 특히 현재 PR은 readonly이므로 purge 후 PR을 반복 실행해도 해당 PR이 공유 캐시를 채우지 않는다. 운영 초기화 대신 전용 디렉터리에서 원하는 초기 상태를 만들면 목적을 달성할 수 있다.
