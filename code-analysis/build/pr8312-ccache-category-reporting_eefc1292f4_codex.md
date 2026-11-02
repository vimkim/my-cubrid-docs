# PR #8312의 ccache 범주별 집계와 검토 결과

- 작성일과 검토일은 2026-11-02, Asia/Seoul이다.
- 독자는 CUBRID CI 담당자와 PR 리뷰어다.
- 관련 변경은 [CUBRID/cubrid PR #8312](https://github.com/CUBRID/cubrid/pull/8312)와 CUBRIDQA-1681이다.
- 질문은 전체 hit율의 해석 문제를 어떻게 해결했으며, 어떤 유지보수 과제가 남는가이다.

**이 PR은 전체 hit율에 가려졌던 CUBRID 소스의 캐시 재사용률을 따로 보여주고, 파일별 결과를 빌드 종료 후에도 보존한다.** 검토한 리비전에서 승인을 막을 결함은 발견하지 못했다. 후속 개선으로는 대표 로그를 이용한 자동 회귀 테스트와 경로 정보 누락의 구분을 우선한다. 실제 CI의 재실행과 다운로드 서버 검증은 이번 검토 범위에 포함하지 않았다.

## 검토 대상과 근거의 범위

| 항목 | 검토 대상 |
| --- | --- |
| 소스 저장소 | `CUBRID/cubrid` |
| PR head | `eefc1292f4e65cb6c505c2965591873e3bf2300f` |
| PR base | `4ddf3b1550cae1ed82d65b5a9a6182912acd237f`, `develop` |
| PR head 저장소와 브랜치 | `tw-kang/cubrid`, `cubridqa-1501-ccache-split` |
| 변경 파일 | `.github/workflows/gha-ci.yml` 한 개, 47줄 추가와 4줄 삭제 |
| 빌드 대상 | `build (release)`와 `build (debug)`, 후자는 `-m optdebug` |
| 작성자가 명시한 환경 | ccache 3.7.7, CMake 3.26.5, 로컬 경계 검증의 gawk 4.2.1 |
| 이번 로컬 검증 환경 | GNU Awk 5.1.0, Bash 5.3.20, Python 3.14.6, ShellCheck 0.11.0 |

파일 수와 diff는 다음 명령으로 확인했다. 소스 수정, 빌드 계측, CI 트리거는 수행하지 않았다.

```bash
git diff --stat 4ddf3b1550cae1ed82d65b5a9a6182912acd237f...eefc1292f4e65cb6c505c2965591873e3bf2300f
git diff --check 4ddf3b1550cae1ed82d65b5a9a6182912acd237f...eefc1292f4e65cb6c505c2965591873e3bf2300f
```

이 문서는 소스에서 확인한 동작, 작성자의 실행 보고, 로컬 합성 로그 관찰, 후속 제안을 구분한다. 작성자의 실행 보고를 이번 검토에서 재측정한 결과로 취급하지 않는다.

## 전체 hit율로는 CUBRID 소스의 상태를 구분하기 어려웠다

이전 PR #8254는 빌드별 hit와 miss 합계를 출력했다. 외부 라이브러리의 hit가 많으면 CUBRID 소스를 대부분 다시 컴파일해도 전체 hit율은 높게 보일 수 있다. PR #8312는 기존 합계 아래에 범주별 통계를 추가한다.

작성자가 [PR 본문](https://github.com/CUBRID/cubrid/pull/8312)에 제시한 fork run 40664476761의 debug 예는 다음과 같다.

| 집계 대상 | direct hit | preprocessed hit | miss | hit율 |
| --- | ---: | ---: | ---: | ---: |
| 전체 | 1,916 | 16 | 1,329 | 59.25% |
| CUBRID source | 72 | 0 | 1,180 | 5.75% |
| external libraries | 1,842 | 16 | 85 | 95.63% |
| CMake checks | 2 | 0 | 64 | 3.03% |

세 범주의 건수를 더하면 전체 합계가 된다. 전체 비율은 컴파일 결과 건수로 계산하므로 세 범주의 hit율을 단순 평균한 값과 다르다. 개선 효과는 통계의 가시성과 사후 조사 자료에 있다. 빌드 시간 개선을 측정한 변경은 아니다.

## PID별 경로 정보를 결과에 연결한다

빌드 step은 job 전용 `CCACHE_LOGFILE`을 지정하고 빌드 종료 뒤 그 로그를 읽는다. 공유 캐시의 누적 통계와 구분하며, PR 빌드의 `CCACHE_READONLY=1`과 `CCACHE_NOSTATS=1` 설정을 유지한다. [빌드와 로그 설정](https://github.com/CUBRID/cubrid/blob/eefc1292f4e65cb6c505c2965591873e3bf2300f/.github/workflows/gha-ci.yml#L551)

집계기가 복원하는 데이터는 `PID`, 작업 디렉터리, 소스 파일, 결과다. 작업 디렉터리와 소스 파일은 PID별 배열에 보관한다. 같은 PID의 `Result:`가 나오면 해당 경로와 결과를 연결한다. 새 ccache 실행의 시작 메시지에서는 그 PID의 경로 정보를 지워 PID 재사용에 대응한다. 배열의 수명은 각 AWK 실행 안으로 제한된다. [PID별 상태와 이벤트 처리](https://github.com/CUBRID/cubrid/blob/eefc1292f4e65cb6c505c2965591873e3bf2300f/.github/workflows/gha-ci.yml#L569)

병렬 컴파일은 같은 로그 파일에 기록한다. 작성자는 긴 `Command line:` 중간에 다른 프로세스의 메시지가 들어간 실제 사례를 보고했다. 집계기는 줄 안의 `[시각 PID]` 헤더마다 나눠 읽는다. `entry()`의 `match()`가 AWK의 `RSTART`를 바꾸므로 호출 전에 현재 조각과 나머지를 잘라 둔다. 이 처리는 이미 섞인 로그를 읽는 방법이며, 로그 쓰기를 직렬화하는 변경은 아니다. [메시지 분할](https://github.com/CUBRID/cubrid/blob/eefc1292f4e65cb6c505c2965591873e3bf2300f/.github/workflows/gha-ci.yml#L588)

범주는 다음 순서로 해석한다. 코드에서는 CMake 규칙 적용 뒤 외부 라이브러리 규칙으로 덮어쓸 수 있으므로 외부 라이브러리 규칙이 우선한다. [분류와 집계](https://github.com/CUBRID/cubrid/blob/eefc1292f4e65cb6c505c2965591873e3bf2300f/.github/workflows/gha-ci.yml#L578)

| 범주 | 규칙 |
| --- | --- |
| external libraries | 작업 디렉터리나 소스 경로에 `/3rdparty/`가 있다. |
| CMake checks | 외부 라이브러리 조건에 해당하지 않고, 작업 디렉터리에 `/CMakeFiles/CMakeScratch/`가 있다. |
| CUBRID source | 나머지 결과다. |

상대 소스 경로에는 작업 디렉터리를 붙여 외부 라이브러리 여부를 검사한다. hit율의 분모에는 direct hit, preprocessed hit, cache miss만 포함한다. `multiple source files`와 `cache file missing` 같은 다른 결과도 TSV에는 남긴다.

## 파일 저장 실패와 통계 출력을 분리한다

같은 AWK 집계기를 두 번 실행한다. 첫 번째 실행은 결과 파일을 열지 않고 합계와 범주별 통계를 출력한다. 두 번째 실행이 결과, 작업 디렉터리, 소스 파일을 탭으로 구분해 TSV로 저장한다. 이어서 `ccache-results.tsv.gz`를 run별 빌드 로그 디렉터리에 쓰고 URL을 출력한다. [두 번의 집계와 저장](https://github.com/CUBRID/cubrid/blob/eefc1292f4e65cb6c505c2965591873e3bf2300f/.github/workflows/gha-ci.yml#L603)

이 구조는 파일을 쓸 수 없어도 첫 번째 실행의 통계를 남긴다. 집계 실패나 파일 저장 실패는 경고로 처리한다. 성공 URL은 압축 파일 저장 명령이 성공한 뒤에 출력한다. ccache의 캐시 정책을 바꾸지 않고 부가 통계 수집을 추가한 선택이다.

## 후속 개선과 해석상 한계

1. **대표 로그를 저장소 테스트로 남길 필요가 있다.** 이번 PR의 단일 파일 diff에는 자동 회귀 테스트가 없다. PID별 상태, 병렬 메시지 혼입, PID 재사용을 처리하는 파서이므로 대표 입력과 기대 통계, 기대 TSV를 고정하면 도구 버전 변경 때 회귀를 확인하기 쉽다. 이 문서의 검증 스크립트는 리뷰 근거이며 CUBRID CI에 연결된 테스트가 아니다.
2. **경로 정보 누락을 기본 범주와 구분하지 않는다.** `Result: cache miss`만 있는 입력도 경고 없이 CUBRID miss 1건으로 집계됐다. 이는 로컬에서 관찰한 기본 분류 동작이다. 실제 CI 로그에서 경로 누락이 발생했다는 증거는 없다. 후속으로 누락 경고와 `unknown` 범주를 검토할 수 있다.
3. **범주는 경로에 따른 근사치다.** `CUBRID source`에는 CCI, manager, 생성 파일도 포함된다. 외부 라이브러리 범주에는 그 디렉터리에서 수행한 설정 검사도 포함된다. 엔진 소스만의 캐시 재사용률로 읽으면 범위를 잘못 해석하게 된다.
4. **결과 표만으로 miss 원인과 시간 효과를 판단할 수 없다.** TSV에는 결과와 두 경로가 있다. 캐시 키의 차이, 컴파일 시간, miss 원인에 대한 상세 로그는 저장하지 않는다. 결과 이벤트의 건수와 고유 소스 파일의 개수도 같다고 가정하지 않는다.
5. **문구와 디렉터리 규칙에 의존한다.** 집계기는 작성자가 명시한 ccache 3.7.7의 로그 형식과 CMake의 `CMakeScratch` 경로를 전제로 한다. 빌드 이미지의 도구 버전을 바꿀 때 해당 입력 계약도 함께 확인해야 한다. 공식 빌드별 통계 기능의 버전별 차이는 [기존 STATSLOG 가이드](ccache-per-build-stats-log-guide_2026-10-27.md)에 정리했다. 공식 통계 기능만으로 파일별 범주 연결까지 자동 대체된다고 가정하지 않는다.

위 항목은 후속 개선과 수치 해석의 범위다. 검토한 입력에서 확인된 빌드 장애나 PR의 필수 수정 사항으로 보고하지 않았다.

## 로컬 검증과 재현 방법

최초 리뷰의 합성 로그 검증은 62개 assertion을 통과했다. 이 문서에 보존한 스크립트는 같은 검증에 경로 누락의 기본 분류 확인 1개를 추가했고, 2026-11-02 실행에서 63개 모두 통과했다. 생성 로그와 결과 파일은 임시 디렉터리에만 기록하고, 마지막 JSON 출력으로 위치를 알린다. 유지하는 지원 파일은 [검증 스크립트](pr8312-ccache-category-reporting_eefc1292f4_codex-assets/verify.py) 한 개다. 실행 근거를 재현하기 위해 보존한다.

Python 3, Bash, Git, GNU Awk를 가리키는 `awk`, gzip, ShellCheck가 필요하다. CUBRID 소스 checkout을 정확히 위 PR head에 맞춘 뒤 문서 저장소 루트에서 실행한다. `SOURCE_WORKTREE`에는 해당 checkout 경로를 지정한다.

```bash
python3 code-analysis/build/pr8312-ccache-category-reporting_eefc1292f4_codex-assets/verify.py "$SOURCE_WORKTREE"
```

스크립트는 `git show`로 검토한 커밋의 빌드 step을 읽고 집계 부분을 그대로 추출한다. ccache 형식의 합성 입력을 주고, 실제 AWK와 Bash 명령의 표준 출력과 생성된 압축 파일을 검사한다. 무작위 혼입 순서는 seed `8312`로 고정했다.

| 입력 또는 검사 | 관찰한 결과 |
| --- | --- |
| 범주별 direct hit, preprocessed hit, miss | 합계와 범주별 수치가 기대값과 일치한다. |
| 20가지 PID 순서 혼합과 긴 command line 안의 메시지 | 통계와 TSV의 결과·경로 연결이 유지된다. |
| PID 재사용과 새 실행 시작 | 이전 작업 디렉터리와 소스 경로가 남지 않는다. |
| hit와 miss 이외의 결과 | TSV에는 남고 hit율에는 포함되지 않는다. |
| 절대 경로, 상대 경로, 외부 라이브러리 안의 CMake 검사 | 외부 라이브러리 분류와 우선순위가 유지된다. |
| 임시 출력 경로와 최종 출력 경로에 디렉터리 대신 일반 파일 배치 | 경고와 통계가 출력되고 종료 코드는 0이다. 성공 URL은 출력하지 않는다. |
| 로그 누락, 빈 로그, hit와 miss가 없는 로그 | 경고를 출력하고 종료 코드는 0이다. |
| 경로 없이 `Result: cache miss`만 제공 | 경고 없이 CUBRID miss 1건으로 집계된다. |
| `bash -n`과 ShellCheck | 구문 검사 통과. ShellCheck는 AWK의 `$0`를 리터럴로 유지하기 위한 `SC2016`만 제외한다. |

이 검증은 합성 로그의 파싱과 출력 동작을 확인한다. 실제 ccache 3.7.7로 컴파일하지 않았고, CI의 gawk 4.2.1에서 실행하지 않았다. 전체 워크플로의 actionlint, 새 CI 실행, 운영 다운로드 URL의 도달성도 확인하지 않았다. 작성자가 보고한 fork 실행과 실제 빌드 로그 검증은 PR 본문의 별도 증거로 남긴다.

## 승인 리뷰 초안

게시 전에 사용자 검토를 받을 [승인 리뷰 초안](pr8312-approval-review_eefc1292f4_codex.md)을 별도 파일에 준비했다. 승인 요약은 확인한 동작과 검증 범위를 설명한다. 자동 테스트, 경로 누락의 구분, 범주 해석 안내는 승인의 조건으로 요구하지 않는 `nit`으로 분리했다. 이 문서 작성 시점에는 GitHub 승인 리뷰와 요약 댓글을 제출하지 않았다.
