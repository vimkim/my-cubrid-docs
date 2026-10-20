# CBRD-27711: unixODBC 빌드·설치·실행 주장 독립 검증

작성일: 2026-10-21 (Asia/Seoul). 작업 항목: 451. 관련 이슈: [CBRD-27711](https://jira.cubrid.org/browse/CBRD-27711). 검토 대상 소스 브랜치 `thirdparty-reuse-poc`에 연결된 PR은 없다.

**일반 Linux 빌드는 unixODBC를 실제로 빌드하고 Gateway에 연결한다. 설치된 Gateway도 unixODBC 공유 라이브러리를 사용하지만, 이번에 확인한 설치본은 직접 빌드한 2.3.14 대신 시스템 2.3.9를 선택했다.** 따라서 기존 제목 `linux odbc so 사용 안함`을 unixODBC 전체가 미사용이라는 뜻으로 읽으면 사실과 다르다. 관측한 문제는 빌드에서 준비한 라이브러리와 설치 후 선택되는 라이브러리가 다르다는 점이다.

기존 본문은 이 구분과 측정 한계를 대체로 정확히 설명했다. 이번에는 고정 기준 소스를 새로 빌드·설치하고 실제 TGZ를 생성하여 이를 확인했다. 모든 배포 패키지의 구성, CI 절감량, 자동 빌드 제거의 안전성, 외부 DB 연결, 라이선스 준수 완료는 이 검토로 확정하지 않는다.

## 주장별 판정

`confirmed`는 기재한 구성에서 확인, `partly supported`는 일부 범위만 확인, `false`는 그 범위에서 반증, `not verified`는 필요한 증거가 없음을 뜻한다. 미확인을 거짓으로 판정하지 않는다.

| ID | 검증한 주장 | 판정 | 증거·구성·실용 범위 |
| --- | --- | --- | --- |
| T0 | Linux Gateway는 unixODBC 공유 라이브러리를 사용하지 않는다 | false | E2·E4. 기준 소스의 API 호출, 새 Gateway의 미해결 ODBC 심볼 23개와 `NEEDED libodbc.so.2`, 로더의 시스템 DSO 선택으로 반증한다. 기존 제목의 넓은 해석에 대한 판정이다. |
| T1 | 일반 Linux 기본 빌드는 Gateway 사용 여부와 무관하게 unixODBC를 다운로드·컴파일한다 | confirmed | E2. `cc947788d`, `WITH_LIBUNIXODBC=EXTERNAL`, 새 빌드에서 재현했다. 실행 시 기능 사용 여부가 빌드 조건으로 전달되지 않는다. 이미 완료한 증분 빌드마다 재다운로드한다는 뜻은 아니다. |
| T2 | Gateway는 unixODBC 헤더·심볼·공유 라이브러리를 빌드 입력으로 사용한다 | confirmed | E2. 실제 Ninja 헤더 의존성, 링크 명령, ELF 심볼·의존성까지 일치한다. 라이브러리 코드가 사용되지 않는다는 주장은 현재 게시 본문에 없으며 검토 결과와도 맞지 않는다. |
| T3a | 일반 CMake 최종 설치에는 `libodbc.so*`가 없다 | confirmed | E3. 새 기준 빌드의 설치 목록 198개와 설치 디렉터리를 확인했다. Gateway와 라이선스 파일만 관련 항목에 있다. unixODBC 자신의 작업 prefix 설치와 구분한다. |
| T3b | 관련 배포 패키지도 `libodbc.so*`를 동봉하지 않는다 | partly supported | E3. 실제 CPack TGZ에서 확인했다. RPM은 staging·생성 spec까지만 확인했고 완성 RPM 생성은 기존 shebang 검사 오류로 실패했다. STGZ·외부 패키징·이미 배포된 공식 파일 전체는 미검증이다. |
| T4 | 확인한 일반 설치 Gateway는 시스템 unixODBC를 로드한다 | confirmed | E4. 기존 `4adcd40` 설치본과 새 `cc947788d` 설치본 모두, `LD_*` 변수를 제거한 로더 검사에서 `/lib64/libodbc.so.2`를 선택했다. 이 호스트의 패키지는 unixODBC 2.3.9이다. |
| T5 | 링크 때 사용한 라이브러리와 실행 시 선택한 라이브러리가 달라질 수 있다 | confirmed | E4. 같은 빌드에서 build-tree는 2.3.14, installed는 2.3.9를 선택했다. 설치 ELF의 `LD_LIBRARY_PATH`를 바꾸거나 복사본에서 prefix를 숨겨도 선택 경로가 바뀐다. 모든 플랫폼의 결과로 일반화하지 않는다. |
| T6 | unixODBC 준비가 CI의 큰 비중을 차지하는 측정된 병목이다 | not verified | E5. 요청자의 경험 보고와 CI의 실제 준비 단계는 확인했지만 단독 계측·임계 경로·제거 전후 비교가 없다. 로컬 한 번의 27초 관측이나 전체 의존성 PoC 시간으로 이를 대신할 수 없다. |
| T7 | 기본 unixODBC 빌드 규칙을 지금 삭제해도 안전하다 | not verified | E6. 현재 대체 모드는 configure 오류이며 Gateway의 헤더·링크·런타임 입력이 남는다. 기능 선택, 공급 방식, ABI·드라이버·외부 DB 시험을 갖춘 변경을 검증하지 않았다. |
| T8a | 실제 unixODBC 2.3.14의 상위 식별은 라이브러리 LGPL 2.1, 프로그램 GPL 2.0이다 | confirmed | E7. CMake 고정 SHA256과 공식 tarball이 일치하고 README·라이선스 원문에서 구분을 확인했다. 파일별 고지·예외를 하나의 SPDX 조건으로 평탄화하지 않는다. |
| T8b | 라이선스 파일을 설치하므로 동봉 또는 별도 제공 시 준수가 완료된다 | not verified | E7. 실제 배포 구성과 대응 소스·고지·교체/재링크 조건의 이행을 조사하지 않았다. 기존 본문도 이를 완료로 선언하지 않았다. |
| P1 | 기존 바이너리 기준과 소스 기준 사이의 네 관련 파일이 같다 | confirmed | E1. `4adcd409`와 `cc947788d`의 Git blob 내용을 각각 해시하여 일치했다. 기존 설치본 전체가 현재 소스에서 생성되었다는 증명은 아니다. |
| P2 | 기존 PoC의 `installed-gateway-ldd.txt`가 일반 설치의 시스템 로드를 증명한다 | false | E4. 그 파일은 PoC prefix 로드를 기록한다. 일반 설치 증거는 별도로 수집했다. 인계 문서가 경계한 혼동에 대한 판정이다. |

## E1

### 대상과 증거의 출처

검토 대상은 이슈의 2026-10-21 조회 본문과 [게시 보고서 커밋 a399e5f](https://github.com/vimkim/my-cubrid-jira/blob/a399e5f04dc35d7b6b4eb9fc1fe279f290d49ef0/issues/CBRD-27711-unixodbc-build-runtime-policy_ad2182f_codex.md)이다. 해당 파일의 SHA256은 `85ed2eb6daa4637e8f989a1bf8b24c9aafba570a20e8eeec3f7fd5d5b7fd36af`이며 검토 시작 시 로컬 파일과 커밋 내용이 같았다. 이슈 요약은 당시 `linux odbc so 사용 안함`, 유형은 `Correct Error`였다.

| 구분 | 고정 식별자·구성 |
| --- | --- |
| 일반 빌드 소스 | `cc947788d3b7dc402f46192d0f3299ddcc8563ba` |
| PoC 소스 | `ad2182f08d2cb5e1c7b56f1b6b47cef704171aa9`; 일반 빌드의 대체 증거로 사용하지 않는다. |
| 기존 설치본 | `cubrid --version`: `11.5.0.2683-4adcd40`, Linux 64bit debug |
| 새 기준 빌드 | `11.5.0.2704-cc94778`, Linux x86_64 Debug, Ninja |
| 호스트·도구 | Rocky Linux 9.6, kernel `5.14.0-570.30.1.el9_6.x86_64`, GCC 11.5.0, CMake 3.26.5, Ninja 1.10.2 |
| 새 빌드 입력 | CCI `79d0888c26a2543d31f53eb7b6c9738db110fff4`, `WITH_CCI=true`, `WITH_LIBUNIXODBC=EXTERNAL`; CMake compiler launchers `ccache` |
| 기능 범위 | 개인 `debug_gcc` 설정의 O0·디버그·프레임 포인터 옵션, OOS·spage·page buffer 단위 테스트 옵션 ON. JDBC·Manager 하위 저장소는 초기화하지 않았다. 해당 전체 제품 구성의 배포 검증은 아니다. |

일반 Linux 의존성 규칙을 변경하지 않은 격리 worktree에서 구성·전체 빌드·설치를 수행했다. 새 소스에 생산 코드 패치를 넣지 않았다. CCI 빌드가 생성한 추적 헤더 변경은 증거를 남기고 원래 내용으로 복구했다. 기존 develop·PoC worktree의 변경·prefix·설치본은 보존했다.

아래 값은 각 커밋의 `git show <commit>:<path>` 출력에 대한 SHA256이며 두 커밋에서 각각 동일하다.

| 파일 | `4adcd409`와 `cc947788d`의 공통 SHA256 |
| --- | --- |
| `3rdparty/CMakeLists.txt` | `b5db2ebe2a22715bb0cee0475eb81800e3288649114659febc49c05fdf4a3562` |
| `broker/CMakeLists.txt` | `3e7c2e5d4a0e983048d3c5d54b8b741bbc41741557c1b0f0edd2e5512effe2df` |
| `src/broker/cas_cgw_odbc.c` | `6ee0fc49c557a9bf6cb824803c9736ec497c774a82219a910e21fde63aa03498` |
| `CMakeLists.txt` | `cc517d07c145953775d82e24cabfd30f26f2efcb6982baae6891503e95212cdc` |

## E2

### 기본 빌드 의존성과 실제 Gateway 사용

[기본값과 URL/hash](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/3rdparty/CMakeLists.txt#L23-L93)는 unixODBC 2.3.14와 `EXTERNAL`을 선택한다. [외부 프로젝트 규칙](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/3rdparty/CMakeLists.txt#L430-L460)은 configure, make, make install을 실행하고 `libodbc`를 `EP_TARGETS`에 추가한다. 여기에는 실행 중 Gateway/DBLINK를 사용할지 검사하는 조건이 없다. `WITH_LIBUNIXODBC`의 다른 값은 명시적인 configure 오류이다.

`libodbc`는 [cubridcs의 공통 의존성](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/cs/CMakeLists.txt#L637)에도 들어간다. [cubridsa](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/sa/CMakeLists.txt#L803-L820)와 [서버 라이브러리](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/cubrid/CMakeLists.txt#L757)도 공통 외부 프로젝트에 의존한다. 따라서 현재 그래프에서는 Gateway를 실행하지 않더라도 엔진 빌드가 준비 비용을 부담할 수 있다.

[CMake ExternalProject 문서](https://cmake.org/cmake/help/v3.26/module/ExternalProject.html)는 단계 완료 stamp와 다운로드 hash 재사용을 설명한다. 이번 새 빌드에서는 다운로드부터 설치까지 실제로 실행되었다. 이것은 매번의 증분 빌드가 같은 작업을 반복한다는 뜻은 아니다. 한편 [build.sh clean](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/build.sh#L162-L186)은 선택한 별도 빌드 디렉터리의 내용을 지우므로 그 안의 외부 프로젝트 상태도 사라지는 경로이다. 기존 사용자 디렉터리에 clean을 실행하지 않았다.

Gateway 사용은 다음 세 단계로 직접 확인했다.

1. [헤더 include](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/src/broker/cas_cgw_odbc.h#L44-L55)와 새 Ninja 객체 의존성에 `3rdparty/include/{sqltypes.h,sql.h,sqlext.h,sqlucode.h}`가 있다. 시스템 개발 헤더가 우연히 설치되어 있다는 이유만으로 빌드 입력을 추정하지 않았다.
2. [cas_cgw_lib 소스·링크](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/broker/CMakeLists.txt#L282-L302)와 [cub_cas_cgw 연결](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/broker/CMakeLists.txt#L376-L386)이 이어진다. 생성된 실제 명령은 해당 빌드의 `3rdparty/lib`에 대한 `-L`과 `-lodbc`를 포함한다. 소스 변수는 파일 경로지만 생성기가 `-L`/`-l` 형식으로 표현했다.
3. [SQLAllocHandle](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/src/broker/cas_cgw_odbc.c#L128-L149), [SQLDriverConnectW](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/src/broker/cas_cgw_odbc.c#L216-L252) 등의 호출이 있고 새 ELF에는 `SQLAllocHandle`, `SQLDriverConnectW`, `SQLExecute`, `SQLFetchScroll` 등을 포함한 미해결 ODBC 심볼 23개 및 `NEEDED libodbc.so.2`가 있다.

## E3

### CMake 설치와 패키지의 확인 범위

[unixODBC의 make install](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/3rdparty/CMakeLists.txt#L439-L452)은 `<BUILD>/3rdparty`를 채운다. 이것은 CUBRID 최종 설치가 아니다. CUBRID는 [Gateway 설치 대상](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/broker/CMakeLists.txt#L637-L653)과 [서드파티 라이선스 설치](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/CMakeLists.txt#L839-L847)를 별도로 선언한다.

새 최종 설치의 manifest는 198개 항목이었다. 관련 항목은 `bin/cub_cas_cgw`와 `3rdparty/libodbc_license.txt`이며, 설치 디렉터리 전체에서도 `libodbc.so*`는 없었다.

| 경로 | 이번 확인 결과 |
| --- | --- |
| 새 CMake 설치 | Gateway와 라이선스 포함, `libodbc.so*` 없음 |
| 새 CPack TGZ | 생성 성공. archive 237개 항목 중 `CUBRID/bin/cub_cas_cgw`, `CUBRID/3rdparty/libodbc_license.txt` 포함, `libodbc.so*`와 unixODBC 프로그램 6개는 없음 |
| 새 CPack RPM staging·생성 spec | 관련 파일은 `opt/cubrid/3rdparty/libodbc_license.txt`; `libodbc.so*` 없음 |
| 완성 RPM | 생성 실패. `broker_log_top.py`, `brokerstatus_to_csv.py`, `statdump_to_csv.py`의 `#!/usr/bin/python` 계열 shebang을 Rocky 9 RPM 검사가 거부했다. 이 문제를 수정하거나 검사를 끄지 않았다. |
| STGZ·외부 패키징·기존 공식 배포물 | 실제 산출물 미검증. 확인한 소스 설치 규칙만으로 전부 같은 구성이라고 단정하지 않는다. |

생성 TGZ는 `CUBRID-11.5.0.2704-cc94778-Linux.x86_64-debug.tar.gz`이며 SHA256은 `cf3a02fae35c5b69109b97cc80db629d75878aa2741e5ab3d140b05e0e16045b`이다. 이 파일은 이번 로컬 구성의 실험 산출물이며 공식 배포물로 게시하지 않았다.

[CPack archive 문서](https://cmake.org/cmake/help/v3.26/cpack_gen/archive.html)는 binary package가 CMake install 규칙을 사용함을 설명한다. [build.sh 배포 분기](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/build.sh#L435-L475)도 TGZ·STGZ·RPM을 CPack으로 호출한다. 다만 외부 배포 스크립트가 파일을 더할 가능성은 별도 조사해야 한다.

추가로 [RPM 설정](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/cmake/CPackOptions.cmake.in#L33-L54)은 자동 Requires 생성을 끄고, 명시한 목록에도 unixODBC가 없다. 이는 런타임 공급 누락을 점검해야 할 소스 근거이다. 완성 RPM의 메타데이터나 unixODBC가 없는 새 호스트의 기능 실패까지 확인한 결과는 아니다.

## E4

### ELF와 로더 선택 실험

로더 검사 시 기존 `LD_*` 환경 변수는 없었고, 검사 프로세스에서는 모든 `LD_*` 변수를 제거했다. 별도의 override 실험에서만 `LD_LIBRARY_PATH`를 지정했다. `/etc/ld.so.cache` 등 호스트 기본 설정은 유지했다. ELF의 의존성은 모두 SONAME `libodbc.so.2`이며 특정 원본 파일의 절대 경로나 해시가 아니다.

| 검사 대상 | RUNPATH 요약 | 선택한 unixODBC |
| --- | --- | --- |
| 기존 일반 build-tree | 기존 build의 cs·CCI·3rdparty/lib | 그 build의 2.3.14 |
| 기존 일반 설치본 | 기존 설치 prefix/lib | `/lib64/libodbc.so.2`, 시스템 2.3.9 |
| 새 기준 build-tree 복사본 | 새 build의 cs·CCI·3rdparty/lib | 새 build의 2.3.14 |
| 같은 복사본에서 새 3rdparty/lib를 숨김 | ELF는 동일 | 시스템 2.3.9 |
| 새 기준 설치 ELF 복사본 | 새 설치 prefix/lib | 시스템 2.3.9 |
| 같은 설치 복사본에서 새 3rdparty/lib를 숨김 | ELF는 동일 | 시스템 2.3.9 |
| 같은 설치 복사본에 `LD_LIBRARY_PATH=<COPY>/lib` 지정 | ELF는 동일 | 별도 복사한 새 2.3.14 |
| 기존 PoC 설치 ELF 복사본 | PoC 설치 lib 및 외부 prefix | PoC prefix의 2.3.14 |
| 같은 PoC 복사본에서 원본 prefix를 숨김 | ELF는 동일 | 시스템 2.3.9 |

실행 파일은 `copy2`로 복사했고 ELF를 수정하거나 재링크하지 않았다. prefix 제거 효과는 bubblewrap의 읽기 전용 루트 mount namespace 안에서 해당 경로를 빈 tmpfs로 가려 재현했다. 호스트의 원본 파일은 삭제하거나 이동하지 않았다. 새 기준·PoC 복사본의 `ldd -r` 결과는 모두 0이며 `not found`·`undefined symbol` 진단은 없었다.

새 build ELF의 RUNPATH는 `<BUILD>/cs:<BUILD>/cubrid-cci/cci:<BUILD>/3rdparty/lib:`이고, 설치 ELF는 `<INSTALL>/lib`였다. [설치 RPATH 설정](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/CMakeLists.txt#L59-L65)과 맞는다. [glibc 로더 문서](https://sourceware.org/glibc/manual/latest/html_node/Dynamic-Linker-Invocation.html) 및 [glibc 2.34 로더 소스](https://github.com/bminor/glibc/blob/glibc-2.34/elf/dl-load.c)는 동적 로더가 검색 경로와 환경을 해석하는 주체임을 설명한다. 여기서 확정하는 것은 위 호스트에서의 실제 선택 결과이다.

시스템 파일의 소유 RPM은 `unixODBC-2.3.9-4.el9.x86_64`, 실제 파일은 `/usr/lib64/libodbc.so.2.0.0`이었다. 해시는 다음과 같다.

| 파일 | SHA256 |
| --- | --- |
| 기존 일반 설치 `cub_cas_cgw` | `fb1ce9d395da84552ec37e858829443bf2ca858d01e9d7cd93d5e6a1dcff6afc` |
| 새 기준 build `cub_cas_cgw` | `d1210a572816e0f73af205ef633c9a633e81acf1aa55b588f95e9384b176a4a3` |
| 새 기준 설치 `cub_cas_cgw` | `34db32a1aec3eb16c26ed3a6ce4b86dd1f8d3edba11059d70b8a5283d5a6cb75` |
| 새 기준 빌드 `libodbc.so.2.0.0` | `dd35c7ad31198ba99257f9bae522120ea3064ce6e9a8912d38b4874b43b1350b` |
| 시스템 `libodbc.so.2.0.0` | `845811e1e1ad9281d3f7982c89754ff02ec1e6a17f0e655e55522be544f275dd` |
| PoC prefix `libodbc.so.2.0.0` | `348976cb676b9dbedbcfc2b0ee297040bd24da02f75bdb1bbecb0c26e633f9ef` |

ODBC 드라이버와 외부 DB의 연결·조회는 시험하지 않았다. 로더 선택과 relocation 확인은 Gateway/DBLINK 기능 시험을 대체하지 않는다. 시스템 2.3.9가 해당 기능에서 완전히 호환된다는 결론도 내리지 않는다.

## E5

### CI 병목과 로컬 시간의 구분

[기준 커밋의 기존 develop push run 39386422016](https://github.com/CUBRID/cubrid/actions/runs/39386422016)을 읽었다. 로그의 실제 checkout과 `SHA`가 모두 `cc947788d3b7dc402f46192d0f3299ddcc8563ba`임을 확인했다. 새 CI는 실행하지 않았다.

| 기존 CI job | Build step의 API 시각 | 관측 범위 |
| --- | --- | --- |
| [release](https://github.com/CUBRID/cubrid/actions/runs/39386422016/job/118507278113) | 07:26:09–07:29:08 UTC, 약 179초 | step 전체이며 unixODBC 단독 시간이 아니다. |
| [debug](https://github.com/CUBRID/cubrid/actions/runs/39386422016/job/118507278224) | 07:26:17–07:31:54 UTC, 약 337초 | step 전체이며 unixODBC 단독 시간이 아니다. |

두 job 모두 `libodbc`의 download/configure/build/install/complete 메시지가 있다. 여러 단계의 출력 시각이 같은 묶음으로 기록되어 있어 인접 로그 시각을 unixODBC 각 단계의 정확한 소요 시간으로 빼면 안 된다. 외부 프로젝트 전용 계측이나 임계 경로 제거 전후 비교는 확보하지 않았다. 처음 조회한 comment-trigger run `39421851396`은 API head SHA와 달리 실제 PR head `ea0b1c644...`를 빌드했으므로 기준 커밋 시간 근거에서 제외했다.

새 로컬 빌드의 `.ninja_log`에서 libodbc 상대 stamp 출력만 골라 중복된 절대 경로·byproduct 행을 제외하면 다음과 같다.

| 단계 | 시작–종료 (빌드 시작 후 초) | 해당 edge 시간 |
| --- | --- | --- |
| download·verify·extract | 0.028–2.277 | 2.249초 |
| configure | 2.318–19.404 | 17.086초 |
| build | 19.404–25.309 | 5.905초 |
| install | 25.309–27.067 | 1.758초 |
| 전체 libodbc 완료 | 0.007–27.095 | mkdir·빈 단계·완료 처리 포함 27.088초 |
| 전체 Ninja 빌드 | 0–94.269 | CMake configure·최종 설치·패키징 제외 |

새 디렉터리에서 시작했지만 호스트 ccache는 비우지 않았다. compiler wrapper도 ccache 경로이며 `MAKEFLAGS=-j80`, `nproc=80`, Ninja 기본 병렬 설정을 사용했다. 다운로드는 실제 네트워크를 사용했고 네트워크 속도·호스트 부하·캐시 hit를 통제하지 않았다. 따라서 이는 해당 실행의 단계별 관측이지 재현 가능한 성능 벤치마크가 아니다.

이 실행에서 공통 의존성인 OpenSSL은 34.528초에 완료되어 unixODBC의 27.095초보다 늦었다. 이 순서만으로도 unixODBC edge 27초를 제거했을 때 전체 빌드가 27초 줄어든다고 계산할 수 없다. 자원 경합까지 포함한 실제 절감량은 동일 조건의 반복 A/B 시험이 필요하다. 기존 PoC의 전체 의존성 producer 125.28초 역시 unixODBC 단독 시간이 아니다.

## E6

### 제거·분리의 가능성과 남은 결정

엔진 반복 빌드에서 unixODBC 준비를 분리하려는 목표는 현재 공통 빌드 그래프와 부합한다. 그러나 안전하게 제거했다는 구현·검증 결과는 없다. 현재 `WITH_LIBUNIXODBC=SYSTEM`은 지원되는 우회가 아니며, Gateway 전체를 선택적으로 제외하는 옵션도 이 기준 소스에 없다.

후속 변경은 아래 계약을 먼저 갖추어야 한다.

- Gateway를 빌드하는 구성에는 `sqltypes.h`, `sql.h`, `sqlext.h` 등 개발 헤더, 링크 입력과 필요한 종속성을 공급한다. 단순히 런타임 `.so.2` 하나가 있다고 개발용 linker name·헤더가 준비되는 것은 아니다.
- Gateway를 제외하는 구성을 지원한다면 소스·타깃·공통 `EP_TARGETS` 의존성과 설치 항목을 함께 구분하고, 해당 구성의 빌드·설치를 확인한다.
- Gateway가 있는 설치에는 호환 런타임 DSO, ODBC 드라이버, 설정을 공급하고 지원 버전·ABI 및 누락 진단을 정한다.
- 준비 prefix가 사라진 환경, 선택한 공급 방식, 외부 DB 연결·조회, 배포 형식별 설치를 검증한다.

빌드 준비 위치와 런타임 배포 방식은 서로 다른 결정이다. 외부 producer에서 준비하면서 최종 설치물에는 라이브러리를 동봉하는 조합도 가능하다. 따라서 “메인 빌드에서 분리”와 “동봉”을 반드시 둘 중 하나로만 취급할 이유는 없다. 어떤 조합을 지원할지는 미결정이다.

## E7

### 실제 artifact의 라이선스 식별

[CUBRID 고정 URL/hash](https://github.com/CUBRID/cubrid/blob/cc947788d3b7dc402f46192d0f3299ddcc8563ba/3rdparty/CMakeLists.txt#L27-L52)의 unixODBC 2.3.14 tarball SHA256은 `4e2814de3e01fc30b0b9f75e83bb5aba91ab0384ee951286504bb70205524771`이다. 로컬 tarball과 별도로 받은 [공식 tarball](https://www.unixodbc.org/unixODBC-2.3.14.tar.gz)의 크기 1,758,907바이트와 hash가 일치했다. [공식 다운로드 페이지](https://www.unixodbc.org/download.html)의 연결도 확인했다. PoC에 풀린 원본 일반 파일 882개는 archive와 바이트 단위로 같았다. 서명 검증과 모든 빌드 산출물의 전체 provenance 재구성은 수행하지 않았다.

이 해시의 원본 `README:15,17`은 라이브러리 LGPL 2.1, 프로그램 GPL 2.0을 구분한다. 루트 `COPYING`은 LGPL 2.1, `exe/COPYING`은 GPL 2.0, `libltdl/COPYING.LIB`는 LGPL 2.1이다. 원래 보고서의 식별은 맞지만 움직이는 master README 링크만으로 2.3.14의 근거를 고정할 수는 없다.

대표 소스에는 `or later` 문구가 있으며, `libltdl/ltdl.c:10–18`의 특별 예외와 `extras/snprintf.c:1–5`의 Patrick Powell 고지도 있다. 후자는 `extras → ini → DriverManager`로 연결되고 기존 libodbc 산출물에서 `uodbc_snprintf`·`uodbc_vsnprintf` 정의를 확인했다. 전체 tarball 또는 모든 구성 파일에 동일한 `LGPL-2.1-only` 조건을 부여한 결과가 아니다.

원본 빌드 prefix에는 `isql`, `iusql`, `odbcinst`, `odbc_config`, `dltest`, `slencheck`가 있다. 이것은 도구를 포함한 upstream 준비 단계의 결과이며, 이번 최종 CUBRID 설치·TGZ에는 그 프로그램들이 없었다. 공급물 전체를 배포할 때는 라이브러리 하나를 배포하는 경우와 파일 구성이 다르다.

[LGPL 2.1 원문](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)과 [GPL 2.0 원문](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)의 조건 식별과 실제 배포 의무 이행 판단은 구분한다. 최종 배포 파일, 고지, 대응 소스 제공, 연결·교체 조건 등의 충족을 조사하지 않았으므로 준수·위반을 판정하지 않는다.

## 수정 제안

### 버그 보고의 제목과 중심 현상

제목 제안: **빌드한 unixODBC가 설치된 Gateway에서 사용되지 않음**.

본문 제안:

> 일반 Linux 빌드는 unixODBC 2.3.14를 다운로드·컴파일하고 Gateway를 해당 라이브러리에 연결한다. 그러나 기준 커밋의 새 CMake 설치와 CPack TGZ에는 `libodbc.so*`가 포함되지 않는다. 확인한 설치 환경에서 Gateway는 빌드한 2.3.14 대신 시스템 2.3.9를 선택한다. 이는 unixODBC API나 공유 라이브러리 전체가 미사용이라는 뜻이 아니라 빌드와 설치 후 실행의 의존성 선택이 달라지는 현상이다.
>
> 공급·버전 정책을 명시하고 빌드 입력과 설치 후 선택을 일관되게 검증해야 한다. 메인 엔진에서 자동 준비를 분리하는 방안을 우선 검토하되, 시스템 공급·별도 제공·동봉 중 구현 선택과 지원 범위는 아직 정하지 않았다.

CI에 대한 문안은 “요청자가 반복 준비 비용을 병목으로 보고했다. 기존 CI에서 준비 단계는 확인했지만 단독 시간·임계 경로·실제 절감량은 아직 검증하지 않았다”로 유지한다. 패키지는 확인한 CMake 설치·TGZ와 RPM staging으로 범위를 좁힌다. 라이선스는 고정 artifact 식별과 미완료 준수 검토를 분리한다.

기존 본문의 중요한 장점인 API 실제 사용, 기존 바이너리와 소스 기준 구분, 외부 DB 미시험, 공급 방식 TBD는 유지해야 한다. 본문 전체를 허위로 평가할 근거는 없다.

## 재현 명령과 보존 증거

아래는 검토에 사용한 표준 도구 단계이다. 빌드 실행은 로컬 관리 인터페이스를 통해 위에 기록한 설정으로 수행했다. 아래 명령은 동일한 확인을 위한 공개 도구 형태이며, 옵션을 생략하면 그 환경의 기본 구성이 적용된다.

```bash
# 별도 checkout의 고정 기준 소스에서 수행한다.
git rev-parse HEAD
cmake -S . -B build-check -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DCMAKE_INSTALL_PREFIX="$PWD/install-check"
cmake --build build-check --parallel 8
cmake --install build-check
ninja -C build-check -t commands cub_cas_cgw
ninja -C build-check -t deps \
  broker/CMakeFiles/cas_cgw_lib.dir/__/src/broker/cas_cgw_odbc.c.o
readelf -d build-check/bin/cub_cas_cgw
readelf -d install-check/bin/cub_cas_cgw
nm -D install-check/bin/cub_cas_cgw
rpm -qf /lib64/libodbc.so.2
env -u LD_LIBRARY_PATH -u LD_PRELOAD ldd -r install-check/bin/cub_cas_cgw
cpack --config build-check/CPackConfig.cmake -G TGZ -B package-check
```

prefix 제거 실험의 형태는 다음과 같다. 실제 검토에서는 위 E4의 복사본과 절대 경로를 사용했고, 호스트 파일을 변경하지 않았다.

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD \
  bwrap --ro-bind / / --proc /proc --dev /dev \
  --tmpfs "$odbc_prefix_to_hide" -- /usr/bin/ldd -r "$gateway_copy"
```

원시 로그·JSON·archive·복사 ELF는 `/mnt/nvme/data-5/tmp/cbrd27711-review-ontHCk`에 보존한다. 격리 소스 worktree는 `/home/vimkim/gh/cb/CBRD-27711-unixodbc-review`, 설치는 `/home/vimkim/.cub/install/CBRD-27711-unixodbc-review/debug_gcc`이다. 핵심 자료는 `baseline-runtime.json`, `poc-prefix-test.json`, `install_manifest.txt`, `tgz-inventory.json`, `baseline.ninja_log`, `baseline-ci-run.log`, `cpack-rpm.log`이며 이 문서에 판정·식별자·결정적인 결과를 요약했다. 대용량 로그와 생성 inventory는 문서 저장소에 추적하지 않는다.

모든 주요 주장에는 위 표의 판정과 증거 또는 공백을 부여했다. 미완료 실험은 완성 RPM, STGZ·외부 배포물, 통제한 시간 비교, 의존성 제거 구현, 외부 DB 기능 시험 및 실제 배포 라이선스 준수 검증이다. 별도의 소스 수정·CI 실행은 하지 않았다. 검토 도중 사용자가 신규 발견의 JIRA 반영과 버그 보고 형태의 제목·본문 수정을 명시적으로 요청했으므로, 그 후속 게시 작업은 독립 검토 결과와 구분해 진행한다.
