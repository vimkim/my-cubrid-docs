# CUBRID CI의 ccache hit율 표시 확인 요청

- 확인일: 2026-10-21 (Asia/Seoul)
- 수신: 강태우님 / CI 담당
- 확인 대상: `CUBRID/cubrid`의 PR 빌드 로그와 해당 실행의 `.github/workflows/gha-ci.yml`

## 확인을 부탁드리는 내용

PR 빌드 로그에 표시되는 ccache hit율을 해당 빌드의 캐시 재사용 비율로 읽어도 되는지 확인했습니다.

**확인한 PR 빌드들은 `CCACHE_NOSTATS=1`로 통계 기록을 끄고 실행했습니다. 빌드 뒤 출력된 hit율은 공유 캐시에 이미 쌓여 있던 누적 통계였습니다.** 따라서 아래 로그만으로는 각 PR 빌드의 실제 hit율을 알 수 없습니다.

캐시 조회와 재사용은 계속 가능합니다. 이번에 확인한 문제는 캐시의 동작 여부를 판단할 실행별 통계가 이 출력에 기록되지 않는다는 점입니다. 현재 운영 의도와 별도의 실행별 측정 방법이 있는지 확인을 부탁드립니다.

## 1. CI 설정에서 확인한 근거

빌드 단계에는 다음 조건문이 있습니다.

```bash
[ "$CACHE_WRITE" = 'true' ] || export CCACHE_READONLY=1 CCACHE_NOSTATS=1
```

이후 실제 빌드를 실행하고 `ccache -s`로 통계를 출력합니다. 확인한 모든 PR 빌드 로그에는 `CACHE_WRITE: false`가 기록되어 있어 위 환경변수들이 적용됩니다.

| 설정 | 의미 |
| --- | --- |
| `CCACHE_READONLY=1` | 기존 캐시는 조회하지만 새로운 컴파일 결과를 캐시에 저장하지 않습니다. |
| `CCACHE_NOSTATS=1` | 이번 컴파일의 hit·miss 카운터를 갱신하지 않습니다. |
| 빌드 뒤의 `ccache -s` | 캐시에 기록되어 있는 통계를 출력합니다. 이번 빌드의 hit·miss가 추가된 값으로 해석할 수 없습니다. |

위 의미는 [ccache 3.7.7 공식 문서의 read_only·stats 설명](https://ccache.dev/manual/3.7.7.html#_configuration)에서도 확인할 수 있습니다. 실제 CI의 도구 버전과 추가 설정은 실행별 측정 방식을 정할 때 함께 확인할 필요가 있습니다.

확인한 설정은 다음 두 커밋에 고정하여 비교했습니다. 두 커밋 모두 같은 조건문과 통계 출력 흐름입니다.

- PR #8217 실행 기준: [`c966fabc6b4c8ac86aa4b5abb0a4cbefae01bf5b`, 빌드 단계](https://github.com/CUBRID/cubrid/blob/c966fabc6b4c8ac86aa4b5abb0a4cbefae01bf5b/.github/workflows/gha-ci.yml#L550-L562).
- 추가 PR 4개 실행 기준: [`959314906ee65a3deac43a7ff056a012dbb4d2f7`, 빌드 단계](https://github.com/CUBRID/cubrid/blob/959314906ee65a3deac43a7ff056a012dbb4d2f7/.github/workflows/gha-ci.yml#L550-L562).

확인한 workflow에서는 `cache_write`를 기본 false로 두고, develop 브랜치의 push 실행에서 true로 바꿉니다. 따라서 이 문서의 결론은 확인한 PR 실행에 관한 것입니다. 모든 CI 실행에서 통계 기록이 꺼져 있다고 일반화하지 않습니다. [실행 종류별 설정](https://github.com/CUBRID/cubrid/blob/c966fabc6b4c8ac86aa4b5abb0a4cbefae01bf5b/.github/workflows/gha-ci.yml#L215-L230)

## 2. PR #8217: 다른 커밋의 빌드에서 같은 통계가 출력됨

2026-10-20의 두 OptDebug 빌드는 실제 소스 커밋이 다르지만, 같은 카운터와 같은 갱신 시각을 출력했습니다.

| 작업 로그 | 실제 빌드한 소스 커밋 | direct hit | preprocessed hit | miss | 표시된 hit율 |
| --- | --- | ---: | ---: | ---: | ---: |
| [첫 번째 실행](https://github.com/CUBRID/cubrid/actions/runs/39377825558/job/118479884072) | [be5e8fc](https://github.com/CUBRID/cubrid/commit/be5e8fc50a745215ec65a80e2ce6e57bf1972c9f) | 100948 | 1296 | 68689 | 59.82% |
| [두 번째 실행](https://github.com/CUBRID/cubrid/actions/runs/39383918389/job/118499169707) | [5c2586f](https://github.com/CUBRID/cubrid/commit/5c2586fef889f2ab504a1fe82eb073f10ee7f7a1) | 100948 | 1296 | 68689 | 59.82% |

두 로그에 공통으로 나온 통계 부분은 다음과 같습니다.

```text
cache directory                     /home/ci/cache/ccache/develop-debug
stats updated                       Tue Oct 20 12:58:24 2026
cache hit (direct)                100948
cache hit (preprocessed)            1296
cache miss                         68689
cache hit rate                     59.82 %
```

59.82%는 기존 카운터 `(100948 + 1296) / (100948 + 1296 + 68689)`의 비율입니다. 이 두 빌드가 각각 59.82%를 달성했다는 뜻으로 사용할 수는 없습니다.

실행 화면에 보이는 workflow 기준 커밋 `c966fab`와 실제 빌드한 PR 소스 커밋도 구분해야 합니다. 위 표의 소스 커밋은 각 작업 로그의 `INPUT_SHA`·`SHA`에서 확인했습니다.

## 3. 다른 PR에서도 같은 설정을 확인함

2026-10-21에 실제 빌드 단계가 수행된 PR 4개, 총 8개 작업을 추가 확인했습니다. 아래 비율은 모두 **로그에 표시된 공유 캐시 누적 비율**입니다.

| PR | 실제 빌드한 소스 커밋 | OptDebug의 표시 값 | Release 작업의 표시 값 |
| --- | --- | ---: | ---: |
| #7943 | [1100de3](https://github.com/CUBRID/cubrid/commit/1100de36c83c3cc9aee37971c952632d971f9e97) | [59.85%](https://github.com/CUBRID/cubrid/actions/runs/39569305898/job/119119243691) | [88.11%](https://github.com/CUBRID/cubrid/actions/runs/39569305898/job/119119243638) |
| #8211 | [d15b771](https://github.com/CUBRID/cubrid/commit/d15b7716f031898968936442456ca642bedf19c0) | [59.85%](https://github.com/CUBRID/cubrid/actions/runs/39570342523/job/119122690824) | [88.51%](https://github.com/CUBRID/cubrid/actions/runs/39570342523/job/119122690804) |
| #8213 | [cdc5deb](https://github.com/CUBRID/cubrid/commit/cdc5deb349e3579edd07a6001ed13796cf8ba1e8) | [59.85%](https://github.com/CUBRID/cubrid/actions/runs/39578754076/job/119150924781) | [88.51%](https://github.com/CUBRID/cubrid/actions/runs/39578754076/job/119150924699) |
| #8232 | [c9e05bf](https://github.com/CUBRID/cubrid/commit/c9e05bf9121879d92e1ed1a1b40b3b48e2e6e0c6) | [59.91%](https://github.com/CUBRID/cubrid/actions/runs/39576130495/job/119142069418) | [88.11%](https://github.com/CUBRID/cubrid/actions/runs/39576130495/job/119142069682) |

8개 작업 모두 `CACHE_WRITE: false`와 `CCACHE_NOSTATS=1`을 적용하는 조건문을 확인했습니다. CI 작업 이름의 `debug`는 `BUILD_ARGS: -m optdebug`로 실행되었습니다. [빌드 모드 설정](https://github.com/CUBRID/cubrid/blob/959314906ee65a3deac43a7ff056a012dbb4d2f7/.github/workflows/gha-ci.yml#L487-L491)

특히 #7943·#8211·#8213의 OptDebug 로그는 hit율뿐 아니라 direct hit `104832`, preprocessed hit `1294`, miss `71194`, 갱신 시각 `Wed Oct 21 16:52:29 2026`까지 같았습니다. 위 표의 차이를 PR별 캐시 성능 차이로 해석할 수 없습니다.

## 4. 여기까지 판단할 수 있는 범위

확인한 로그로 판단할 수 있는 것은 **해당 출력으로 PR별 hit율을 측정할 수 없다는 점**입니다. 실제 hit가 0이라는 결론이나 ccache가 효과가 없다는 결론은 내릴 수 없습니다.

관련 [CBRD-25560의 실험 댓글](https://jira.cubrid.org/browse/CBRD-25560?focusedCommentId=4777097&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-4777097)은 버전 헤더 변경 후 Debug의 CUBRID 소스 구간에서 hit가 `0/1170`이었다고 보고합니다. 위 누적 통계만으로 그 실험의 옳고 그름을 판정할 수도 없습니다. 실제 CI의 커밋 변경 전후 결과를 같은 조건으로 측정해야 합니다.

이 확인은 [CBRD-27124](https://jira.cubrid.org/browse/CBRD-27124)의 버전 갱신·재빌드 문제와 [CBRD-25560](https://jira.cubrid.org/browse/CBRD-25560)의 캐시 효과를 구분해 평가하기 위한 자료입니다. CI 설정을 변경하거나 빌드를 새로 실행한 것은 아닙니다.

## 5. 확인 요청

1. PR 빌드의 읽기 전용 캐시 사용과 통계 기록 중지가 의도된 운영 정책인지 확인 부탁드립니다.
2. 각 PR 빌드의 실제 hit·miss를 확인할 수 있는 별도 로그나 집계 방법이 이미 있는지 알려주시면 좋겠습니다.
3. 별도 방법이 없다면, 공유 캐시와 누적 통계를 보존하면서 실행별 hit·miss를 기록하는 방법을 검토 부탁드립니다. 현재 ccache 버전이 지원하는 방법을 확인한 뒤 결정하면 좋겠습니다.

실행별 통계를 확보하면 CUBRID 소스와 외부 라이브러리, 동일 커밋 재빌드와 커밋 변경 후 빌드를 구분하여 측정하고자 합니다. 이를 통해 버전 헤더 변경이 실제 CI의 캐시 재사용과 빌드 시간에 미치는 영향을 확인할 수 있습니다.

## 원문 재확인 방법

GitHub CLI로 해당 저장소에 접근할 수 있는 환경에서 다음 명령으로 대표 로그를 다시 읽을 수 있습니다. 원문 전체 대신 필요한 부분만 발췌하여 위에 기록했습니다.

```bash
gh api repos/CUBRID/cubrid/actions/jobs/118499169707/logs |
  rg 'INPUT_SHA:|CACHE_WRITE:|CCACHE_NOSTATS|stats updated|cache hit|cache miss'
```

workflow는 위에 연결한 커밋 고정 링크에서 같은 조건문을 확인할 수 있습니다. 향후 workflow가 바뀌면 변경 후 실행은 별도로 확인해야 합니다.
