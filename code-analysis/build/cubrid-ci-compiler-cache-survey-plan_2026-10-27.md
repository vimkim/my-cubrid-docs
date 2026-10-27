# CUBRID CI 컴파일 캐시 대안: 예비 분석과 후속 survey 계획

- 작성·확인일: 2026-10-27, Asia/Seoul
- 대상 독자: CUBRID 빌드·CI 담당자와 PR #8254 리뷰어
- 관련 항목: [CUBRIDQA-1681 / PR #8254](https://github.com/CUBRID/cubrid/pull/8254), [CBRD-27124](https://jira.cubrid.org/browse/CBRD-27124)
- 질문: 현재 공유 ccache와 `NOSTATS` 정책보다 통계·캐시 공유를 관리하기 쉬운 구조가 있는가?
- 범위: 서브에이전트 3개가 현재 설계, sccache, 최신 ccache를 각각 조사하고 결과를 교차 검토했다. 신규 도구 설치·CI 전환·성능 benchmark는 수행하지 않았다.
- 후속 작업: work-tracker #520. 실제 도구 선정과 운영 전환을 완료했다는 보고서는 아니다.

**후속 survey는 sccache와 최신 ccache를 함께 비교하는 것이 적절하다.** 핵심 후보는 job마다 통계·임시 상태를 분리하고, 재사용할 컴파일 결과만 공유하는 구조다. `CCACHE_NOSTATS`는 현재 공유 통계 파일의 쓰기를 막는 정책 선택이며, 모든 컴파일 캐시가 요구하는 제약이 아니다.

다만 통계 분리, 다른 노드에서의 캐시 재사용, 커밋 버전 정보 변경에 따른 입력 무효화는 각각 다른 문제다. 원격 캐시가 더 많은 노드에 같은 결과를 전달할 수는 있어도, 변경된 입력에 이전 결과를 사용해도 되는지는 별도로 판단해야 한다. 현재 자료만으로 sccache가 CBRD-27124를 해결하거나 유지보수 비용을 줄인다고 확정할 수 없다.

## 1. 근거의 기준과 한계

| 대상 | 조사 기준 | 이 보고서에서 확인한 범위 |
| --- | --- | --- |
| CUBRID PR #8254 | `f874120a2ffaa866d868c92b7fb4ea2cebfa0f46` | 워크플로, 캐시 설정, CMake 옵션과 버전 헤더 포함 관계 |
| 작성자 fork 검증 | run `39941778094`, 실제 빌드 소스 `eb88ab4eab3f6ae28040d15606a884e1d3846269` | 두 build job의 소스 SHA와 출력. 커밋 변경 대조 실험은 아님 |
| CBRD-27124 기존 실측 | A `f30f1c26003e5aa8e93182648e06cad76fc77064`, B `d606df3f6c6ef152a8f1ba9a0c2cd4e7232f01ba` | 2026-10-21 로컬 Debug 실험의 기록을 재검토. 새 실험은 아님 |
| ccache | `v4.14.2`, `360543256991b0df7b5ad1822bd08f8d4ae2aa90` | 공식 문서·릴리스 기록에 따른 기능과 구성. 이 버전을 실행 검증하지 않음 |
| sccache | `v0.19.0`, `965c01943a40c9df96264474bbe28ba98f2e1487` | 공식 문서·소스에 따른 기능과 상태 소유 범위. CUBRID 빌드를 실행하지 않음 |

현재 클러스터의 노드 수, pod의 실제 마운트·네트워크, 저장소 권한, 이미지 내부 `/entrypoint.sh`와 compiler wrapper 설정은 실사하지 않았다. CMake launcher 연결을 지원한다는 제품 설명과 현재 CI에 그대로 적용된다는 검증은 구분한다. 아래의 운영 비용 비교도 측정 결과가 아니라 pilot에서 확인할 가설이다.

## 2. PR #8254에서 커밋 변경 후 0%가 관찰됐는가

**제시된 검증에서는 관찰되지 않았고, 해당 조건을 시험하지도 않았다.** 두 job은 같은 `eb88ab4`를 다시 빌드했다. 워크플로 변경을 담은 PR 커밋과 컴파일 대상으로 전달한 `INPUT_SHA`를 구분해야 한다.

| 실제 빌드 | Direct hit | Preprocessed hit | Miss | 이번 빌드의 hit율 |
| --- | ---: | ---: | ---: | ---: |
| [release](https://github.com/tw-kang/cubrid/actions/runs/39941778094/job/120374746329) | 1,919 | 953 | 385 | 88.18% |
| [debug job, 실제 OptDebug](https://github.com/tw-kang/cubrid/actions/runs/39941778094/job/120374746435) | 3,088 | 17 | 152 | 95.33% |

이 실행은 빌드별 수치를 공유 캐시 누적치와 구분할 수 있다는 검증이다. A만 캐시에 채운 다음 새 B로 바꾸고, 생성된 `version.h`의 차이를 확인한 실험은 아니다. 전체 빌드 합계만 있어 엔진과 외부 라이브러리의 hit도 분리되지 않는다. 따라서 이 수치로 CBRD-27124의 커밋 변경 효과를 재현하거나 반증할 수 없다. PR 승인에는 이 계측 로직 검토와 격리 집계 검증이 포함됐지만, CBRD-27124의 CI 재현은 포함되지 않았다. [PR의 검증 설명](https://github.com/CUBRID/cubrid/pull/8254)

CBRD-27124의 로컬 Debug 실측은 소스 tree가 같은 A와 빈 커밋 B 사이에서 CMake를 명시적으로 재구성했다. 버전 매크로가 바뀐 뒤 1,135개 오브젝트가 다시 컴파일됐고 hit 0 / miss 2,270을 기록했다. 이 환경에는 ccache 중첩이 있어 호출 수와 오브젝트 수가 다르다. 현재 이슈 본문은 실제 OptDebug CI의 영향이 아직 미측정임을 명시한다. **OptDebug의 엔진 소스 hit율이 0%에 근접할 수 있다는 예상과, 실제 CI 관측을 구분해야 한다.** [실측 조건과 한계](../../cbrd-27124/ccache-commit-change-measurement_2026-10-21.md)

## 3. 현재 설계에서 분리할 네 가지 질문

| 질문 | 현재 구조 | 대안이 해결해야 할 것 |
| --- | --- | --- |
| 이번 job이 얼마나 재사용했는가? | 공유 `stats`는 job 범위가 아니며 PR은 갱신하지 않음 | job별 로그 또는 통계 상태를 분리 |
| 다른 노드에서도 기존 결과를 읽을 수 있는가? | PR 본문의 운영 설명상 노드별 캐시 | 공통 저장소 접근 범위를 넓히되 지연·전송량 측정 |
| 버전 정보만 바뀌어도 왜 많은 입력이 달라지는가? | `version.h`가 공통 `config.h`에 포함되고 Debug·OptDebug 옵션에 `-ggdb3`가 남음 | 헤더·전처리·디버그 출력의 실제 변경 범위를 확인 |
| 공유 결과를 누가 갱신할 수 있는가? | develop push는 쓰기 허용, PR은 읽기 전용 정책 | job별 통계 분리 후에도 공유 저장소 쓰기 정책 유지 |

현재 `CCACHE_DIR`은 모드별 `develop-release`와 `develop-debug`다. `debug` job의 실제 인자는 `-m optdebug`이며, PR은 `READONLY=1 NOSTATS=1`을 적용한다. concurrency group은 노드·모드의 공유 카운터를 빌드 단위로 잠그는 장치가 아니다. [캐시·모드·빌드 설정](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/.github/workflows/gha-ci.yml#L477-L569), [develop 쓰기 허용](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/.github/workflows/gha-ci.yml#L216-L230), [concurrency](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/.github/workflows/gha-ci.yml#L80-L101)

따라서 PR #8254의 job별 로그 집계는 현재 정책을 보존하는 작은 변경으로 타당하다. 이 선택이 공유 캐시 아키텍처 전체의 장기 최적성을 증명하지는 않는다. [공식 통계 로그 사용법과 기존 검증](ccache-per-build-stats-log-guide_2026-10-27.md)

## 4. 비교할 구조

아래 표는 통계의 소유 범위와 캐시 데이터의 공유 범위를 분리하는 후보의 공통 원칙이다. ccache와 sccache가 같은 형식의 저장소를 함께 사용한다는 뜻은 아니다. 실제 디렉터리·데몬·backend 연결은 도구에 맞게 구성한다.

| 구성 요소 | 접근·갱신 범위 | 수명과 보존 |
| --- | --- | --- |
| job A의 통계·임시 상태 | job A의 실행들만 갱신 | job 종료 전 요약을 남김 |
| job B의 통계·임시 상태 | job B의 실행들만 갱신. A와 별도 디렉터리·데몬 사용 | job 종료 전 요약을 남김 |
| 공유 컴파일 결과 | 여러 job이 조회. 기존 정책상 PR은 읽기, develop은 읽기·쓰기 | job보다 오래 유지하며 용량·만료 정책 관리 |

### 후보 요약

| 후보 | 통계 범위 | 결과 공유 범위 | 유지보수 관점에서 비교할 항목 |
| --- | --- | --- | --- |
| 현행 3.7.7 + PR #8254 | job별 진단 로그 집계 | 노드·모드별 공유 캐시 | 변경은 작지만 진단 로그 문구 추적이 필요. 대조군으로 유지 |
| A. ccache 업그레이드 + STATSLOG | job별 공식 통계 로그 | 기존 노드 캐시 유지 | 파서를 없애는 가장 작은 대안. 공유 stats 쓰기 정책은 유지 가능 |
| B. 최신 ccache + job별 L1 + 읽기 전용 파일 L2 | job별 디렉터리·로그 | 노드의 준비된 캐시를 조회 | 별도 네트워크 서비스 없이 통계 분리 가능. L1 쓰기·공간·재가열 비용 측정 |
| C. 최신 ccache + job별 L1 + 원격 L2 | job별 디렉터리·로그 | 다른 노드도 같은 backend 조회 | 원격 공유와 helper·인증·정리·네트워크 운영 비용을 함께 평가 |
| D. sccache + job별 데몬 + 공통 원격 저장소 | job별 데몬 통계 | S3 등 지원 backend를 통해 공유 | 직접 object-store 지원은 장점 후보. 데몬 수명·설정·권한·장애 처리는 새 운영 항목 |

여기서 `NOSTATS` 하나를 제거하는 것 자체가 개선 기준은 아니다. 결과 정확성, 작업별 관측 가능성, 빌드 시간, 장애 시 동작, 운영자가 관리할 절차를 함께 비교한다.

## 5. 최신 ccache로 가능한 개선

### 공식 통계 로그만 먼저 도입하는 대안

`CCACHE_STATSLOG`와 `--show-log-stats`는 4.4부터 지원한다. 원격화 없이도 job별 파일을 지정하면 수동 `Result:` 문구 파서를 없앨 수 있다. 기계 판독용 `--print-log-stats`와 JSON 출력은 4.10부터다. 다만 기능 도입 최소 버전을 새 운영 버전으로 권장하지 않는다. 4.13.5에는 stats log 동시 쓰기 동기화 수정도 기록돼 있다. 기존 4.5.1에서의 제한된 병렬 실험 성공을 모든 상황의 동시성 보장으로 확대하지 않는다. [4.4](https://ccache.dev/releasenotes.html#_ccache_4_4), [4.10](https://ccache.dev/releasenotes.html#_ccache_4_10), [4.13.5](https://ccache.dev/releasenotes.html#_ccache_4_13_5)

### job별 로컬 상태와 공유 결과 저장소

ccache의 원격 저장소에는 결과와 manifest를 두고 통계 카운터는 로컬 캐시 디렉터리에 남는다. `remote_only=true`로 로컬 결과 저장을 생략해도 통계는 로컬에 남을 수 있다. 각 job에 별도 `CCACHE_DIR`를 주면 통계를 켠 채 공유 카운터 간섭을 피하는 구성이 가능하다. 빌드 단계만 따로 집계하려면 이때도 STATSLOG가 명확하다. [통계 경계](https://github.com/ccache/ccache/blob/360543256991b0df7b5ad1822bd08f8d4ae2aa90/doc/manual.adoc#L1268-L1276), [remote_only](https://github.com/ccache/ccache/blob/360543256991b0df7b5ad1822bd08f8d4ae2aa90/doc/manual.adoc#L1042-L1048)

이 구조에서는 전역 `CCACHE_READONLY=1`을 그대로 복사하지 않는다. 전역 설정은 모든 backend의 새 결과 저장을 막지만, backend의 `read-only=true`는 공유 L2만 제한할 수 있다. private L1 쓰기는 허용하고 공유 L2의 쓰기만 막으려면 클라이언트 설정과 저장소 권한을 같은 정책으로 맞춰야 한다. 실제 기존 mount·ACL 구성을 검증한 것은 아니다. [전역 READONLY](https://github.com/ccache/ccache/blob/360543256991b0df7b5ad1822bd08f8d4ae2aa90/doc/manual.adoc#L1015-L1026), [backend 속성](https://github.com/ccache/ccache/blob/360543256991b0df7b5ad1822bd08f8d4ae2aa90/doc/manual.adoc#L1308-L1318)

4.14의 파일 backend에는 `@layout=local`이 추가됐다. 지원 형식의 로컬 캐시 복사본이나 읽기 전용 mount를 L2로 조회하는 중간 대안이다. self-contained 항목이 필요하고 hard link·file clone 항목에는 제약이 있다. 이는 기존 3.7.7 캐시를 그대로 재사용한다는 뜻이 아니다. 공식 4.0·4.5·4.7 기록에는 형식 호환 변화가 있으므로 새 캐시를 채우는 비용을 별도로 측정한다. [파일 backend](https://github.com/ccache/ccache/blob/360543256991b0df7b5ad1822bd08f8d4ae2aa90/doc/manual.adoc#L1385-L1420), [4.0](https://ccache.dev/releasenotes.html#_ccache_4_0), [4.5](https://ccache.dev/releasenotes.html#_ccache_4_5), [4.7](https://ccache.dev/releasenotes.html#_ccache_4_7)

### 원격 backend도 버전에 따라 운영 구조가 다르다

4.14.2 문서는 파일·HTTP·Redis·CRSH 연결을 설명한다. storage helper는 4.13부터 제공되며, 4.14는 내장 HTTP·Redis 지원을 폐기 예정으로 표시한다. 새 구성은 helper의 설치·버전·연결·수명도 관리해야 한다. 따라서 sccache의 데몬 유무만으로 최신 ccache보다 운영이 복잡하다고 비교하면 부정확하다. [helper 계약](https://github.com/ccache/ccache/blob/360543256991b0df7b5ad1822bd08f8d4ae2aa90/doc/manual.adoc#L1278-L1296), [4.14.2 매뉴얼](https://ccache.dev/manual/4.14.2.html#_remote_storage_backends)

조사일의 공식 helper 목록은 HTTP/HTTPS·Redis 구현을 소개하고, S3·Azure·GCS는 원하는 helper 목록에 둔다. ccache가 이미 sccache와 같은 직접 object-store 연결을 제공한다고 가정하지 않는다. 이미 운영하는 object store를 쓰려는 조직에서는 이 차이가 선택에 영향을 줄 수 있다. [공식 helper 목록](https://ccache.dev/storage-helpers.html)

## 6. sccache의 이점 후보와 전환 제약

sccache는 GCC·C/C++와 CMake compiler launcher 연결을 공식 지원한다. S3 호환 저장소·GCS·Azure·Redis 등 원격 backend를 직접 구성할 수 있어, 그 저장소를 이미 운영하고 있다면 별도 캐시 프로토콜 서버를 줄일 가능성이 있다. 이는 기능에 근거한 가설이며 현재 조직의 실제 운영 비용을 측정한 결론은 아니다. 원격 결과 캐시와 scheduler를 추가하는 분산 컴파일은 별도 기능이므로 첫 비교에서는 캐싱만 대상으로 한다. [공식 README](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/README.md), [backend 설정](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/docs/Configuration.md#cache-configs)

### 통계는 데몬 단위다

sccache의 통계는 원격 버킷의 전체 통계가 아니라 로컬 데몬의 상태다. `GetStats`는 이 상태를 읽고 `ZeroStats`는 같은 상태를 초기화한다. 여러 job이 데몬 하나를 공유하면 현재와 같은 통계 혼합·초기화 간섭이 다시 생긴다. **job별 데몬과 공통 원격 저장소를 조합하는 구조**를 비교해야 한다. [데몬 통계](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/src/server.rs#L810-L830), [조회·초기화](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/src/server.rs#L1184-L1204)

독립 pod의 localhost나 job별 `SCCACHE_SERVER_UDS` 등으로 데몬 접근 범위를 분리하고, job 종료 전 JSON 통계를 보존하는 방안을 시험한다. 다른 GitHub Actions step이나 별도 컨테이너에도 같은 job의 주소·설정이 전달돼야 한다. 현재 pod 격리 설정이 이 조건을 이미 만족한다는 실사 결과는 없다. [주소·수명](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/README.md#usage), [통계 출력 옵션](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/src/cmdline.rs#L25-L42)

### 현재 공유 디스크 경로를 그대로 옮기면 안 된다

공식 Local 문서는 여러 sccache 서버가 같은 로컬 디스크 캐시를 동시에 사용하면 경합·빌드 실패가 생길 수 있다고 명시한다. job별 데몬을 띄우면서 현재 공유 경로를 그대로 `SCCACHE_DIR`로 바꾸는 전환은 피해야 한다. job별 로컬 디렉터리와 공유 원격 저장소를 각각 구성한다. 다중 계층 기능도 있지만 계층별 hit, backfill, 쓰기 오류 정책은 별도 시험 대상이다. [로컬 저장소 제약](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/docs/Local.md), [다중 계층](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/docs/Configuration.md#multi-level-cache)

PR의 읽기 전용 정책은 `SCCACHE_S3_RW_MODE` 같은 backend별 설정과 실제 저장소 권한을 맞춰 유지한다. writer 권한을 가진 공용 데몬에 PR client만 다른 환경변수로 연결하는 방식은 정책 경계가 되지 않는다. namespace 역시 저장소 권한을 대신하지 않는다. 인증·만료·용량·네트워크·데몬 장애가 새 운영 항목이다. `SCCACHE_IGNORE_SERVER_IO_ERROR`에 의한 로컬 컴파일 대체 동작도 모든 원격 GET·PUT 오류에 같은 보장이 적용된다는 뜻으로 확대하지 않는다. [backend별 설정](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/docs/Configuration.md#cache-configs), [S3 권한과 인증](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/docs/S3.md), [장애 옵션](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/README.md#usage)

## 7. 캐시 도구 교체와 CBRD-27124의 관계

현재 소스에도 `version.h → config.h` 포함과 OptDebug의 `-ggdb3` 옵션 문자열이 남아 있다. 로컬 Debug의 원인 설명을 최신 실제 CI 결과로 일반화하려면 최종 compiler argv·전처리 출력·생성 헤더를 대조해야 한다. [버전 계산](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/CMakeLists.txt#L124-L183), [Debug·OptDebug 옵션](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/CMakeLists.txt#L219-L246), [공통 헤더](https://github.com/CUBRID/cubrid/blob/f874120a2ffaa866d868c92b7fb4ea2cebfa0f46/cmake/config.h.cmake#L94-L95)

sccache의 C/C++ 키도 전처리 출력과 컴파일러·인자 등의 영향을 받는다. 원격 저장소 자체는 변경된 입력을 원래 입력으로 되돌리지 않는다. 다만 전처리·해시 방식이 같다고 가정하여 **sccache도 반드시 0%**라고 예측하는 것 역시 현재 근거를 넘는다. 조사한 경로에서 `-ggdb3`의 특수 처리를 입증하지 못했으므로 실제 측정이 필요하다. [키 구성](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/src/compiler/c.rs#L650-L673), [GCC 전처리](https://github.com/mozilla/sccache/blob/965c01943a40c9df96264474bbe28ba98f2e1487/src/compiler/gcc.rs#L840-L878)

높은 hit율이 나와도 이전 커밋의 버전 매크로나 잘못된 디버그 정보가 재생되면 성공으로 판정할 수 없다. 캐시 hit율과 함께 `cubrid_rel`, 산출물, DWARF 매크로·경로를 확인한다. 버전 헤더를 무조건 무시하는 설정으로 수치만 높이는 방안은 정확성 검증을 대신하지 못한다.

## 8. 후속 survey의 실행 계획

### 공통 실험 조건

도구별 새 namespace·별도 저장소를 만들고 A만 warm-up한다. B는 동일 source tree의 새로운 빈 커밋으로 만들며 다른 실행이 먼저 B를 캐시에 채우지 못하게 한다. GCC·옵션·CMake·Ninja·병렬성·CPU quota·용량을 맞추고 wrapper는 정확히 한 번만 거치게 한다. 도구 사이의 기존 캐시 형식 재사용은 가정하지 않는다.

| 실험 | 통제할 조건 | 확인할 질문 |
| --- | --- | --- |
| Cold build | 캐시·오브젝트 모두 없음 | 기록 비용과 최초 빌드 시간은 얼마인가? |
| 동일 A 재빌드 | A 캐시는 유지, 실제 오브젝트는 제거 | 무작업 빌드를 제외한 warm-cache 효과는 얼마인가? |
| A→B, 기존 build directory | B 체크아웃 후 CMake 명시적 재구성, version.h 차이 기록 | 기존 CBRD-27124 조건에서 실제 hit와 재컴파일 수는 얼마인가? |
| A→B, 새 CI workspace | A 캐시만 있는 새 작업 공간 | 실제 CI 형태에서 엔진과 외부 라이브러리가 각각 얼마나 재사용되는가? |
| 다른 pod·노드의 동일 A | 입력은 고정하고 배치만 변경 | 로컬 캐시 편차와 원격 공유 효과는 얼마인가? |
| 동시 job | 같은 공유 backend, job별 상태 분리 | 통계 혼합·초기화 간섭·정책 위반이 없는가? |
| 장애와 재시작 | 캐시 부재, DNS·인증·GET·PUT 실패, helper·데몬 재시작 | 빌드 종료 코드와 fallback·오류 집계가 의도대로 동작하는가? |

각 실험은 Debug·OptDebug·Release를 구분한다. 엔진, CCI, 외부 라이브러리도 분리해 전체 합계로 엔진 문제를 가리지 않는다. CI 산출물 재사용으로 build step이 생략되지 않게 하고, 실제 compiler 호출과 고유 오브젝트 수를 함께 기록한다.

### 선택 기준

1. **정확성:** 버전 표시·산출물·디버그 정보가 원래 컴파일과 일치하고, 실패한 빌드가 통계 출력 때문에 성공으로 바뀌지 않는다.
2. **관측 가능성:** job·빌드 단계·저장소 계층의 수치가 구분되고, 입력이 없거나 측정이 누락된 경우를 0%와 구분한다.
3. **성능:** 벽시계 시간, CPU, 전처리 시간, 실제 컴파일 수, 로컬·원격 hit, 요청 수·전송량을 반복 측정해 중앙값과 변동 폭을 남긴다.
4. **운영 비용:** 이미지·helper·데몬·인증·저장소·보존 정책의 수, 업그레이드 절차, 장애 진단·복구 단계를 비교한다. 기존에 운영하는 저장소 유무도 기록한다.
5. **전환 비용:** 캐시 재가열 시간·공간, 기존 캐시와의 공존, 설정 배포 범위, 되돌릴 절차를 확인한다.

먼저 A→B의 현재 OptDebug 관측 공백을 채우고, 같은 입력 집합으로 후보 A·B·C·D를 비교한다. 원격 저장소가 없는 환경에서는 파일 L2 후보 B를 중간 단계로 시험할 수 있다. 기존 object store가 있다면 sccache 후보 D의 직접 연결 이점을 먼저 측정할 수 있다. 어느 순서가 더 싼지는 환경 조사 후 결정한다.

## 9. 이번 조사에서 정한 범위

PR #8254의 계측 개선은 기존 범위로 유지한다. CBRD-27124에서는 커밋 버전 변경 조건의 실제 OptDebug 측정과 입력 무효화 후속 대응을 이어 간다. 도구·저장소 설계 대안은 별도 survey로 남기며, 이번에 도구를 선정하거나 CI를 변경하지 않는다.

이 보고서는 대안 비교를 위한 예비 자료다. 최신 ccache와 sccache에 대한 서브에이전트 조사는 공식 문서·고정 소스에 근거하지만 실제 CUBRID 성능·유지보수 우위를 입증한 실험은 아니다. 과거 로컬 실측과 PR 로그의 적용 범위도 그대로 유지한다.
