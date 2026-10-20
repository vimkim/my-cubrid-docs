## Purpose

[CBRD-27712 — 3rdparty prefix](https://jira.cubrid.org/browse/CBRD-27712)의 합의된 설계, 구현 경계와 로컬 검증 결과입니다. 기준 revision은 `15609d2a779e3082aafe5af576487ebbdc8d70f6`이며 base는 `origin/develop`의 `14b0b1cbd94c26860ea0ed006d8f928a90eec514`입니다. 작성일은 2026-10-21입니다.

- AS-IS: 의존성 준비 상태가 CUBRID build 디렉터리와 함께 사라집니다. 같은 머신에서 worktree를 바꾸거나 clean하면 의존성 준비를 반복합니다.
- TO-BE: 의존성을 별도 prefix에 먼저 준비하고, CUBRID configure에서 그 prefix를 지정합니다. consumer는 준비된 파일만 읽습니다.

기존 PoC의 측정값을 이번 구현의 검증으로 사용하지 않았습니다. 이번 검증은 실행 결과와 산출물의 불변성을 확인하며, cold build 시간이나 CI 병목 개선율을 주장하지 않습니다.

## Implementation

### 합의한 지원 계약

1. 첫 지원 범위는 같은 머신과 같은 C/C++ 컴파일러 환경의 네이티브 Linux 빌드입니다. 배포판·libc 간 이동, 크로스 컴파일, sanitizer·LTO 호환성은 보장하지 않습니다.
2. 사용자가 `bash 3rdparty/build.sh`로 의존성을 준비한 뒤 `CUBRID_3RDPARTY_ROOT`로 prefix를 지정합니다. CUBRID가 producer를 자동 실행하지 않습니다.
3. prefix가 없거나 필수 파일·fingerprint가 맞지 않으면 configure에서 실패합니다. prefix를 지정하지 않은 경로는 기존 빌드·설치 동작을 유지합니다.
4. fingerprint에는 수동 레시피 revision, C/C++ 컴파일러 종류·버전, OS 이름·CPU·포인터 크기를 넣습니다. 전체 ABI 호환성 검사를 위한 manifest 체계는 만들지 않습니다.
5. 완성된 prefix는 consumer가 읽기만 합니다. 의존성 버전·옵션·패치·package 구성이 바뀌면 revision을 올리고 새 상태 경로에 준비합니다. 사용 중인 prefix 덮어쓰기와 producer의 동시 갱신은 지원하지 않습니다.
6. 기존 의존성 8개의 버전·해시·최적화·링크 방식을 유지합니다. Catch2 헤더도 prefix에 준비합니다. Manager·CCI 통합은 기존 구조를 사용합니다.
7. prefix 경로의 설치물은 선택한 unixODBC 드라이버 관리자 라이브러리를 포함합니다. 운영자는 DB별 드라이버와 등록 파일을 제공하고 `ODBCSYSINI`로 등록 디렉터리를 명시합니다.
8. 일반 Linux 경로의 unixODBC 설치 정책은 변경하지 않습니다. [CBRD-27711](https://jira.cubrid.org/browse/CBRD-27711)은 별도 이슈입니다.

### 파일별 책임

| 파일 | 책임 |
| --- | --- |
| `3rdparty/build.sh` | producer의 상태·컴파일러·작업 수를 받아 독립 CMake 빌드를 실행합니다. |
| `3rdparty/CMakeLists.txt` | 기존 의존성 레시피를 공유합니다. prefix를 지정하면 package와 fingerprint를 확인한 뒤 imported target을 상위 빌드에 전달합니다. |
| `3rdparty/standalone/CMakeLists.txt` | dependency producer, 컴파일러 ccache wrapper와 Catch2 준비를 구성합니다. |
| `3rdparty/standalone/Fingerprint.cmake` | 레시피 revision과 로컬 toolchain 식별값을 계산합니다. |
| `3rdparty/standalone/Package.cmake.in` | 헤더·라이브러리·라이선스·unixODBC 소스를 완성된 prefix로 모읍니다. |
| `3rdparty/standalone/CubridThirdPartyConfig.cmake.in` | 필수 입력을 검사하고 imported target 및 기존 CMake 변수를 제공합니다. 다운로드·빌드 규칙은 없습니다. |
| `broker/CMakeLists.txt` | prefix 경로에서 unixODBC 실물·SONAME 링크·소스를 설치하고 Gateway의 RUNPATH를 `$ORIGIN/../lib`로 설정합니다. |
| `unit_tests/CMakeLists.txt` | prefix 경로에서는 준비된 Catch2를 사용합니다. 일반 경로는 기존 준비 방식을 사용합니다. |
| `3rdparty/tests/` | 실제 consumer configure, 8개 의존성 API 실행, prefix·stamp snapshot을 검사합니다. |

공개 사용 예와 지원 한계는 source의 `3rdparty/README.md`에 있습니다. producer는 한 번에 의존성 하나를 빌드하고, 내부 make의 작업 수를 제한합니다. prefix를 사용하는 CUBRID 빌드에는 의존성 download·configure·build target을 추가하지 않습니다.

## Remarks

### Test Plan

로컬 환경은 Rocky Linux 9.6, GCC/G++ 11.5.0, CMake 3.26.5, Ninja입니다. CCI `79d0888c26a2543d31f53eb7b6c9738db110fff4`와 Manager `4ccc2c4107e1728a182a9baf19e9cc2018e50a3d`를 초기화했습니다. 검증 로그는 source checkout의 ignored `.thirdparty/evidence/`에 보존했습니다.

| 검사 | 관찰한 결과 |
| --- | --- |
| 일반 Release | 빌드·설치 성공. JSON builder 21개 사례 / 13,191개 assertion 통과. |
| prefix Release | 빌드·설치 성공. JSON builder 21개 사례 / 13,191개 assertion 통과. |
| 일반 OptDebug | 빌드·설치 성공. JSON builder 21개 사례 / 13,191개 assertion 통과. |
| prefix OptDebug | 빌드·설치 성공. JSON builder 21개 사례 / 13,191개 assertion 통과. |
| 실제 의존성 API | `3rdparty/tests/probe`의 compile·link·run CTest 1/1 통과. Expat, libedit, LZ4, OpenSSL, unixODBC, RapidJSON, RE2, oneTBB API를 호출했습니다. |
| prefix configure | 10/10 통과. 정상 prefix, 없는 경로, `OFF`라는 명시적 경로, 라이브러리·RapidJSON 헤더·ODBC 헤더·SONAME 링크·라이선스·소스 누락, 잘못된 fingerprint를 검사했습니다. |
| clean 재사용 | `build.sh clean`으로 해당 CUBRID build·install을 비운 뒤 producer 없이 configure·build·install·JSON 실행에 성공했습니다. 마지막 재빌드 revision은 `15609d2`입니다. |
| 불변성 | prefix 411개 파일과 producer stamp 151개 파일의 SHA-256·mtime·symlink 대상이 전후 동일했습니다. producer 전용 ccache 통계도 동일했습니다. |
| 의존성 준비 부재 | clean 재빌드의 Ninja target 목록과 로그에 8개 의존성 및 Catch2의 준비 target·실행 단계가 없었습니다. |
| 설치물 실행 | 아래 namespace 격리에서 loader 검사와 등록 이름을 통한 실제 외부 DB 쿼리를 통과했습니다. |

빌드 모드 Release는 프로젝트의 `release` preset에 해당하는 `RelWithDebInfo`입니다. `optdebug`는 `OptDebug`입니다. 각 경로에서 `WITH_CCI=ON`, `WITH_CMSERVER=ON`, `UNIT_TEST_JSON_BUILDER=ON`을 사용했습니다. prefix 경로에만 `CUBRID_3RDPARTY_ROOT`를 지정했습니다. 기존 Release 검증을 마친 뒤 검토 보완을 커밋했고, 최종 revision에서 prefix Release clean 재빌드와 설치물 실행을 다시 확인했습니다.

재현 가능한 집중 검사 진입점은 다음과 같습니다.

```bash
bash 3rdparty/build.sh
python3 3rdparty/tests/check-package.py .thirdparty/prefix
cmake -S 3rdparty/tests/probe -B .thirdparty/probe -G Ninja \
  -DCubridThirdParty_DIR="$PWD/.thirdparty/prefix/lib/cmake/CubridThirdParty"
cmake --build .thirdparty/probe --parallel 2
ctest --test-dir .thirdparty/probe --output-on-failure
```

clean 검증에는 `3rdparty/tests/snapshot.py`로 prefix와 producer stamp를 각각 기록했습니다. CUBRID build·install 경로만 clean한 뒤 같은 prefix로 재빌드했습니다. producer는 실행하지 않았습니다. 의존성 소스 압축파일은 기존에 확보한 해시 검증 파일로 준비했으므로 이 결과는 네트워크 다운로드 성능 측정이 아닙니다.

### 기존 호스트 문제와 검증 보정

stock 설정으로 실행한 일반 Release 빌드는 기존 engine 코드의 `stringop-truncation`과 `maybe-uninitialized` 경고가 오류로 처리되어 실패했습니다. 로컬 검증 설정에서 다음 진단만 경고로 낮췄으며 경고 자체는 로그에 남겼습니다.

```text
-Wno-error=stringop-truncation -Wno-error=maybe-uninitialized
-Wno-error=format-overflow -Wno-error=format-truncation
```

또한 일반·prefix 양쪽에서 기존 Manager의 prebuilt libevent가 `sysctl`을 참조하여 링크가 실패했습니다. 이 호스트의 glibc는 기본 `sysctl` 심벌을 제공하지 않지만 `__sysctl@GLIBC_2.2.5` 호환 심벌은 제공합니다. [glibc의 호환 심벌 변경](https://sourceware.org/pipermail/glibc-cvs/2020q2/069366.html)과 호스트 `readelf` 결과를 확인했습니다.

검증 전용 객체가 `sysctl` 호출을 실제 `__sysctl@GLIBC_2.2.5`로 전달하도록 했습니다. 별도 실행에서 반환값 `-1`, `errno=ENOSYS`를 확인했습니다. 성공값을 위조한 대체 구현은 아닙니다. 이 객체를 네 로컬 검증 preset의 실행 파일 링크에만 넣었습니다. 소스·Manager 변경이나 이 진단·링크 설정은 제품 PR에 포함하지 않았습니다. 따라서 위 빌드 표는 이 공통 호스트 보정 조건에서의 결과이며, stock 설정의 무보정 성공을 의미하지 않습니다.

### Gateway 설치물 독립성

`bwrap` mount namespace에서 원본 prefix, producer build, CUBRID prefix Release build 디렉터리를 빈 mount로 가렸습니다. 원본 파일을 삭제하지 않았습니다. 이 상태에서 다음을 확인했습니다.

- `LD_LIBRARY_PATH`를 제거한 `ldd -r`이 설치물 내부 `lib/libodbc.so.2`를 선택했습니다. 누락된 라이브러리나 unresolved symbol은 없었습니다.
- 설치된 `cub_cas_cgw`의 RUNPATH는 `$ORIGIN/../lib`입니다.
- 운영자 제공 드라이버에 해당하는 Rocky AppStream의 `mariadb-connector-odbc-3.1.12-3.el9.x86_64`를 전용 디렉터리에 추출했습니다. 시스템 패키지를 설치하거나 공유 서비스를 바꾸지 않았습니다.
- `odbcinst.ini`의 `MariaDB_Test_Driver` 이름과 `ODBCSYSINI`를 사용했습니다. Gateway 설정에는 드라이버 절대 경로를 넣지 않았습니다.
- 별도 rootless MariaDB 11.4 컨테이너에 설치된 CCI로 연결했습니다. Gateway 프로토콜의 `__gateway=true`와 `/* DBLINK SELECT */ select 42`로 값 `42`를 읽었습니다.
- 실행 중인 설치물의 `cub_cas_cgw` process map에서 설치물의 `libodbc.so.2.0.0`과 등록된 `libmaodbc.so`를 함께 확인했습니다. 시스템 `libodbc.so.2`는 사용하지 않았습니다.

DB 드라이버 자체의 시스템 의존성은 별도입니다. 이 PR은 unixODBC 드라이버 관리자 `libodbc`를 동봉하며 전체 ODBC 도구·드라이버·의존성을 배포하지 않습니다. 검사에 사용한 Gateway와 전용 DB 컨테이너는 종료했고, 해당 컨테이너와 볼륨을 제거했습니다.

### 라이선스·고지·대응 소스 확인

- 설치물의 `lib/libodbc.so.2`는 상대 링크 `libodbc.so.2.0.0`을 가리킵니다. 링크와 공유 라이브러리 실물이 설치물 안에서 완결됩니다.
- `3rdparty/libodbc_license.txt`가 unixODBC 2.3.14 upstream `COPYING`과 바이트 단위로 동일함을 확인했습니다.
- 설치물에 `3rdparty/unixODBC/unixODBC-2.3.14.tar.gz`와 `README.txt`가 포함됩니다. 압축파일은 upstream `COPYING`, `AUTHORS`, configure 및 libltdl 소스·라이선스를 포함합니다.
- 설치된 소스 압축파일의 SHA-256은 `4e2814de3e01fc30b0b9f75e83bb5aba91ab0384ee951286504bb70205524771`로 기존 레시피의 검증값과 같습니다. upstream 소스 패치는 없습니다.
- `README.txt`에는 LGPL 2.1 안내, 실제 컴파일러 종류·버전, configure·make·install 절차와 호환 공유 라이브러리 교체 안내가 있습니다.

위 결과는 이 구현이 설치한 파일과 재빌드 안내의 확인입니다. 모든 배포 채널에 대한 법률 검토나 별도 DB 드라이버의 재배포 허가를 의미하지 않습니다.

### 독립 코드 리뷰

Standards와 Spec을 별도 agent가 `14b0b1cbd...9eb99f24c` 고정 범위에서 읽기 전용으로 검토했습니다.

- **Standards: 지적 0건.** `CONTRIBUTING.md`, 개인 CUBRID 정책, `unit_tests/AGENTS.md`, codestyle 규칙과 합의된 용어를 확인했습니다. 기존 들여쓰기를 유지했고, 기존 레시피를 재사용하며 추가 추상화는 작은 범위라고 판단했습니다.
- **Spec: 원래 P2 1건, 해결 1건, 미해결 0건.** “필수 파일이 누락되면 configure에서 이유를 알리고 실패한다”는 계약과 달리 `sqltypes.h` 누락이 configure를 통과한다는 지적입니다. 실제 configure 검사에서 실패해야 할 사례가 성공하는 것을 재현했습니다.
- `15609d2a7`에서 `sqltypes.h`, `sqlucode.h`, `unixodbc.h` 검사를 추가하고 누락 사례를 검사에 넣었습니다. 10건 모두 통과했으며 Spec reviewer가 후속 코드를 확인해 원래 지적의 해결을 확인했습니다. reviewer는 빌드·테스트를 직접 실행하지 않았습니다.

source C++ codestyle, shell·Python 구문, Markdown, diff 공백 검사도 통과했습니다. README의 기존 두 semicolon을 baseline으로 둔 영어 문장 검사에서 새 hard finding은 없었습니다.

### 게시와 후속 확인

PR target은 `CUBRID/CUBRID:develop`이고 source는 `vimkim/cubrid:CBRD-27712-thirdparty-reuse`입니다. 아직 PR을 생성하지 않았고 CI도 실행하지 않았습니다. PR 본문 검토 후 draft PR을 생성하고 CUBRID CI를 한 번 실행합니다. 완료 결과·run URL·TC Merge Gate 상태를 보고한 뒤 후속 지시를 기다립니다.

TC 저장소 변경은 필요하지 않습니다. 이 변경의 집중 검사는 source의 `3rdparty/tests/`에 있습니다. 봇이 만드는 두 TC PR은 사람이 확인하여 닫아야 합니다.
