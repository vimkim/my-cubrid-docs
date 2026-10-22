# PR #7925: 기준 브랜치 동기화 후 CI 시간 초과와 로컬 빌드 확인

작성·검증: 2026-10-22, Asia/Seoul. 대상 독자는 PR 작성자와 리뷰어다. 질문은 기준 브랜치 동기화 후 CI가 왜 종료됐으며, 같은 엔진이 로컬에서 빌드되는지다.

**증거 제한:** 이번 CI는 두 빌드의 30분 제한 초과로 종료됐다. SQL·medium·shell은 모두 `job_level_failure`이며, 검증된 testcase 요약이 없다. 이 스냅샷으로 테스트 회귀나 CI 지연의 근본 원인을 판정할 수 없다. 17:42 KST에 추가 확보한 원본 release 빌드 로그는 OpenSSL 다운로드의 시간 초과를 직접 기록한다. 사용자가 보고한 20% 초과 패킷 손실은 별도 정보이며, 다운로드 시간 초과의 원인으로 직접 측정·입증한 사실은 아니다.

## 정확한 입력과 관측

| 항목 | 값 |
| --- | --- |
| 엔진 PR | [CUBRID/cubrid #7925](https://github.com/CUBRID/cubrid/pull/7925), `vimkim/cubrid:CBRD-27424-oos-loaddb-sa` → `CUBRID/cubrid:feature/oos-merge` |
| 엔진 HEAD | `925232529e5406c0fe595fd8fd5123636069ea9b` |
| 병합한 엔진 기준점 | `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2` |
| private TC | `7509f5caa7540b0a2b5079153ca5d22d30e8a56b`, [PR #4360](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4360) |
| public TC | `e33b09e2885fe3a6d2cf8300fb53babf2b1d9665`, [PR #3679](https://github.com/CUBRID/cubrid-testcases/pull/3679) |
| CI 요청 | [`/run all`](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-6334655471), 2026-10-22 15:50:40 KST |
| 실행 | [39736508190, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39736508190), `completed / cancelled` |
| 수집기 | `cubrid-ci 0.2.0 (9536bd3c2867, release)` |
| head 수집 관측 ID | `20261022T072945.290945407Z-2465386-0`, exit 3, `incomplete` |

TC 두 브랜치는 각 저장소의 `feature/oos-merge`를 포함하도록 동기화해 게시했다. 실행 전 testcase 기준점 검사는 통과했다. 위 TC SHA는 요청 당시 브랜치 입력이다. 이번 실행에는 shard의 `tc.read`가 없으므로 실제 testcase 실행 provenance로 주장하지 않는다. TC PR의 병합·종료는 사람이 처리해야 한다.

로컬 조사 후 GitHub를 재확인했으며 엔진 HEAD와 두 TC HEAD는 위 SHA 그대로다. 두 TC PR은 모두 OPEN이므로 개인 CUBRID 정책의 TC Merge Gate 해제 조건은 아직 충족하지 않았다. `gh pr checks --required`는 이 feature 대상 PR에 required check가 없다고 보고했지만, 전체 check 목록은 build 두 개 `FAILURE`, suite 세 개 `ERROR`를 표시한다. required view가 비어 있다는 이유로 CI 자격을 통과했다고 해석하지 않는다.

## CI가 확정한 종료 사유

두 job의 GitHub annotation은 모두 `The job has exceeded the maximum execution time of 30m0s`를 기록한다.

| 빌드 | job | 관측 결과 |
| --- | --- | --- |
| debug | [119683377602](https://github.com/CUBRID/cubrid/actions/runs/39736508190/job/119683377602) | 15:51:30 KST 시작, 약 16:21:50 KST에 취소 처리·잔여 로그 출력 |
| release | [119683377455](https://github.com/CUBRID/cubrid/actions/runs/39736508190/job/119683377455) | 15:52:33 KST 시작, 약 16:22:57 KST에 취소 처리 |

debug 로그의 `BUILD_ARGS`는 `-m optdebug`다. 일반 `Debug` 빌드와 구분해야 한다. release는 기본 release 모드다. 처음 확보한 GitHub job 로그에서는 컴파일러 오류나 다운로드 오류 진단을 확인하지 못했다. debug는 취소 처리 시점에 `[1411/1411] Linking ... cub_manager`까지 출력하지만, 성공한 build artifact의 게시나 성공 job을 의미하지 않는다. Java 하위 빌드의 `BUILD SUCCESSFUL`도 엔진 전체 성공을 뜻하지 않는다.

debug 로그에는 rapidjson configure 출력인 15:52:41 KST부터 다음 progress 출력인 16:13:40 KST까지 약 21분의 공백이 있다. release는 libtbb 관련 출력 뒤 긴 공백을 두고 취소 시점에 잘린 progress를 남긴다. 병렬 빌드와 출력 버퍼링 때문에 이 공백을 특정 라이브러리의 다운로드 소요 시간으로 해석할 수 없다. 이 GitHub 출력 공백만으로는 실패한 URL이나 네트워크 인과관계를 식별할 수 없다.

### 추가 확보한 원본 build.log: release 다운로드 시간 초과

17:42 KST에 workflow가 별도로 보존한 `/runs/39736508190/build/{debug,release}/build.log`를 읽었다. 기존 collector 결과는 job-level 상태만 제공해 build log를 포함하지 않았다. 따라서 이 파일들은 별도의 제한된 읽기 전용 API 증거로 저장했으며 collector schema 출력에 합치지 않았다. testcase summary나 baseline 검증을 대신하지 않는다.

release 원본 로그 639행은 `FAILED: 3rdparty/Stamp/libopenssl/libopenssl-download`를 기록한다. 649~651행에는 공개 의존성 URL `https://github.com/CUBRID/3rdparty/raw/develop/openssl/openssl-3.5.7.tar.gz` 다운로드 실패, `status_code: 28`, `status_string: "Timeout was reached"`가 있다. 643~644행의 다운로드 제한은 전체 1,800초·비활성 60초이며, 21,755행은 최근 60초간 전송량이 초당 1 byte 미만이었다는 진단을 기록한다. **release의 third-party 다운로드 실패와 전송 정체는 이제 직접 관측됐다.** 이 추가 관측은 앞 문단의 GitHub 출력 공백에서 실패 URL을 식별할 수 없었던 한계를 보완한다. 패킷 손실률, 대역폭 제한과의 인과관계, debug job의 지연 원인은 여전히 미확인이다.

debug 원본 로그에는 컴파일러 오류를 확인하지 못했다. 전체 1,411개 build progress와 후속 JDBC 출력이 있지만 artifact 게시 성공을 입증하지 않는다. 두 job의 네트워크 계측 출력은 각각 수신량 200 MB·124 MB다. 이 계측은 `/proc/net/dev`에서 loopback 이외 인터페이스의 수신 byte를 합산하므로 외부 다운로드만의 전송량이나 패킷 손실률을 측정한 값이 아니다.

두 GET은 HTTP 200이었다. debug 파일은 172,589 bytes, SHA-256 `fa7e8997396605db1d7d78a63879454d9bef121f5fc80ba55400dc9edeebfbd9`이고 release는 316,030 bytes, SHA-256 `8bd001bcf437b03e7720178c1caff35289b01df491af80be76cee8289c2d94eb`다. 원본·수집 사유·endpoint·시각·길이·digest·진단 행 번호는 `/mnt/nvme/data-5/tmp/pr7925-retry-20261022.0li9k39h/old-build-fallback/`에 보존했다.

## suite 상태와 수집 한계

head command result·manifest·일치하는 observation request/result는 해당 JSON schema와 입력 identity 검사를 통과했다. 모든 suite의 run/attempt는 `39736508190 / 1`이다. 완전한 suite summary와 testcase inventory는 없다. report-mode gate 결과는 `warning`, `comparison_scope: none`, `regression_conclusions_allowed: false`다.

| suite | 수집 상태 | 테스트 판정·건수 | acquisition |
| --- | --- | --- | --- |
| `test_medium` | `job_level_failure`, commit status `ERROR` | 확인 불가 | `plan_metadata` 단계 실패, 0 response bytes, shard 요청 전 |
| `test_sql` | `job_level_failure`, commit status `ERROR` | 확인 불가 | `plan_metadata` 단계 실패, 0 response bytes, shard 요청 전 |
| `test_shell` | `job_level_failure`, commit status `ERROR` | 확인 불가 | `plan_metadata` 단계 실패, 0 response bytes, shard 요청 전 |

각 suite의 `/runs/39736508190/{medium,sql,shell}/plan/split.meta` 요청은 내부 artifact 서비스에서 HTTP 404를 반환했다. 수집기는 취소된 build jobs와 실패한 plan job을 함께 기록했다. acquisition ledger의 shard map은 모두 비어 있다. 개별 shard 파일의 확보·실패 기록은 없으며, 요청되지 않은 shard 증거는 unknown이다. 실패 목록이 비었다는 이유로 테스트가 통과했다고 해석할 수 없다. `bug_bts_13242` 역시 이번 CI 판정이 없다. CDC는 요청에 따라 분석에서 제외했다.

binary 수집은 요청하지 않았다. 예산 536,870,912 bytes 중 소비 0, 잔여 536,870,912 bytes이며, 예산 부족으로 사라진 binary는 없다.

exact merge-base 수집은 한 번 시도했으나 Git fetch가 42분 이상 진행 중이었다. 네트워크 장애 보고 후 이 작업 소유의 collector process group만 종료하고 중단 기록을 보존했다. base command result와 검증된 base CI bundle이 없어 baseline 비교는 unavailable이다. collector 중단 자체를 base CI 실패로 해석하지 않는다. 검증된 head testcase 실패가 없으므로 Chronicle 실패 이력 조회도 해당 없음이다.

## 요청받은 로컬 빌드 재실행

원래 소스·설치·DB 환경을 보존하기 위해 `/home/vimkim/gh/cb/pr7925-build-check-925232529`, branch `verify/pr7925-build-925232529`에서 동일한 엔진 HEAD를 사용했다. 호스트는 GCC 11.5.0, glibc 2.34다. 추가 확보한 이전 CI 원본 로그는 두 모드 모두 C/C++ compiler identification을 GNU 8.5.0으로 기록한다. 이번 로컬 검증은 같은 소스와 build mode를 사용했지만 CI 컨테이너·toolchain 전체를 재현한 실험은 아니다. CCI/JDBC/Manager는 각각 정확한 gitlink `79d0888c26a2543d31f53eb7b6c9738db110fff4`, `57d2c75d73ee820c26ac049b7ba758f5e646519a`, `4ccc2c4107e1728a182a9baf19e9cc2018e50a3d`로 로컬 Git 객체에서 초기화했다.

새 build directory 두 개에 기존 다운로드 압축 파일 8개만 복사했다. 이전 object·build stamp·완성된 third-party prefix는 복사하지 않았다. CMake 다운로드 단계가 모든 압축 파일의 해시를 확인해 다운로드를 생략했다. 컴파일러 캐시는 사용했으므로 아래 시간은 cold build 성능 측정이 아니다. 로컬 캐시 사용은 CI 네트워크 경로를 재현하지 않는다.

실제 실행은 기존 preset 지원 로컬 빌드 인터페이스를 사용했다. 동등한 프로젝트 빌드 명령은 설치 경로 환경을 선택한 뒤 `cmake --preset <mode>`와 `cmake --build --preset <mode>`이며, 소스나 경고 정책을 수정하지 않았다.

| preset / 범위 | configure | build 결과 |
| --- | --- | --- |
| `optdebug`, 전체 기본 target | 성공, 8.960초 | 실패, 111.708초: `cub_manager` 링크의 `libevent.a(evutil_rand.o): undefined reference to sysctl` |
| `optdebug`, `cub_server` target | 위 구성 유지 | 성공, 0.486초: 남은 엔진 library symlink와 서버 링크 완료 |
| `release`, 전체 기본 target | 성공, 7.465초 | 실패, 59.343초: `src/object/object_representation.c:6284`, `-Werror=stringop-truncation` |

`optdebug`의 엔진 컴파일과 서버 링크는 통과했지만 전체 빌드를 성공이라고 보고할 수 없다. Manager는 저장소에 포함된 prebuilt libevent archive가 요구하는 `sysctl` 참조에서 실패했다. 해당 archive SHA-256은 `49229e4d6d5d4c2433c52f3ccbe9ef68da13fbefa93982b99e95e0141a4d4aca`다. 호스트 libc에는 이 이름의 과거 버전 심볼이 있지만 이번 링크는 해결되지 않았다. Manager gitlink와 루트 `CMakeLists.txt`, `CMakePresets.json`, `3rdparty/`는 기준점 `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2`와 같다. 이는 로컬 링크 환경 문제를 구분하는 증거이며, CI가 같은 오류로 종료됐다는 증거는 없다.

release는 [동일 HEAD의 `object_representation.c:6284`](https://github.com/CUBRID/cubrid/blob/925232529e5406c0fe595fd8fd5123636069ea9b/src/object/object_representation.c#L6284)의 `strncpy`에서 복사 길이 4096이 목적지 크기와 같다는 GCC 진단을 냈다. release compile command에는 `-O2 -DNDEBUG`와 `-Werror`가 있다. `optdebug`에는 전체 `-Werror`가 없고 `-O2 -DCUBRID_OPTDEBUG`가 있다. 경고 정책은 [동일 HEAD의 CMake 설정](https://github.com/CUBRID/cubrid/blob/925232529e5406c0fe595fd8fd5123636069ea9b/CMakeLists.txt#L613)에서 확인할 수 있다. `object_representation.c` 전체 내용도 위 기준점과 byte-identical이다. 해당 파일 SHA-256은 `3a6e820a706e4b172a4dffe8440f4e5dd315bd3a62ffa19e6f99491e54792535`다. 이 로컬 실패를 이번 PR의 신규 변경이나 CI 시간 초과 원인으로 판정하지 않는다. 별도의 기준점 전체 release 빌드는 수행하지 않았다.

동기화 직후 동일 엔진의 기존 `debug_gcc` configure/build/install은 이미 통과했고 CTest 38/38, GTest 374개가 통과했다. `bug_bts_13242`와 partition loader의 native shell 실행도 각각 두 번 통과했다. `13242`는 28.023초·26.229초, partition은 62.537초·59.614초이며 artifact 검증 결과가 모두 성공이다. 이는 해당 로컬 입력에서의 결과이며 이번 CI의 테스트 판정을 대신하지 않는다. 이번 빌드 조사에서는 이 테스트들을 반복하지 않았다.

## 다음 증거를 얻기 위한 조치

사용자가 로컬 결과를 검토하고 `/run all` 한 번을 승인했다. HEAD·TC 기준점·새 `/run` 댓글·활성 실행을 재확인한 뒤 [17:02:33 KST에 한 번 요청](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-6335843415)했다. 새 [run 39744814589, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39744814589)에 다섯 gha-ci context가 모두 연결됐다. 엔진과 TC 입력은 위와 같다. 이전 workflow는 전체 취소됐고 테스트가 실행되지 않아 failure-only testcase 목록을 사용하지 않았다.

새 debug job은 17:30:27 KST, release는 17:32:52 KST에 runner를 배정받았다. 그전에는 두 job이 `queued`였고, 이전에 요청된 PR #7927의 두 빌드도 같은 대기를 보였다. 이 관측은 runner 대기 지연을 보여 주지만 원인을 특정하지 않는다. 이전 workflow commit `2646be1cbe159db119d7da51354c5c156c5cd3f0`와 새 `60ad770f0f84c54cf9fdf8ee213d543bb36a6906`의 `.github/workflows/gha-ci.yml`은 동일하다. 이는 실행 환경 전체의 동일성이나 CI 호스트의 네트워크 복구를 입증하지 않는다. 17:47 KST 관측에서는 두 빌드가 진행 중이고 새 테스트 판정은 아직 없다.

같은 입력이 네트워크 복구 후에도 동일 단계에서 30분을 넘는다면 네트워크만으로 설명하는 가설은 약해진다. 그때 CI 컨테이너의 실제 compiler·dependency 단계 로그·자원 제한을 수집해야 한다. 로컬 Manager와 release 오류는 별도 후속 항목이며, 이번 조사에서는 소스 수정·경고 비활성화·추가 push를 하지 않았다. TC PR 병합·종료도 수행하지 않았다.

## 보존한 증거

collector bundle은 `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/925232529e5406c0fe595fd8fd5123636069ea9b`에 있다. 아래 작업 증거의 공통 루트는 `/mnt/nvme/data-5/tmp/pr7925-13242-fix.qmvkyB`다. raw 로그·캐시는 문서 Git에 추가하지 않았다.

| 파일 | 확인할 내용 |
| --- | --- |
| `sync-ci-result.json`, `validated-sync-head.json` | exact-head 수집 결과와 schema/observation identity 검증 |
| `sync-report-assessment.json` | warning report-mode 입력 |
| `ci-debug-annotations.json`, `ci-release-annotations.json` | 두 build job의 30분 제한 annotation |
| `ci-debug-build.clean.log`, `ci-release-build.clean.log` | ANSI를 제거한 보존 job 로그 |
| `base-collection-interruption.json` | 이 작업 소유 baseline collector의 중단 identity와 사유 |
| `local-ci-flavor-builds.json`, `local-{optdebug,release}-{configure,build}.log` | 정확한 local 입력, 압축 파일 해시, 명령별 시간·exit·첫 오류 |
| `local-optdebug-engine-target.json`, `.log` | optdebug 서버 target의 성공 결과 |
| `local-manager-environment.json`, `local-release-base-comparison.json` | Manager와 release 오류 지점의 기준점 동일성, 로컬 compiler/flags |
| `synced-ctest-summary.json`, `synced-native-summary.json` | 같은 엔진에서 이미 완료한 focused 검증 |

원래 PR worktree의 기존 `cubrid-cci/win/cci_version.h` 수정은 보존했다. 확인한 SHA-256은 `f9766b68dab0c3f615a02cf29368396a43e887b8bc052e0fba321add407259a3`로 조사 전과 같다. 새 검증 worktree의 CCI version header도 빌드 중 생성 변경이 남아 있으며, 별도의 소스 수정으로 게시하지 않았다.
