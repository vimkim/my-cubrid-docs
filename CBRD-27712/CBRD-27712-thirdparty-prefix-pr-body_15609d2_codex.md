https://jira.cubrid.org/browse/CBRD-27712

## Purpose

- AS-IS: CUBRID build 디렉터리를 clean하면 그 안의 서드파티 의존성도 다시 준비해야 합니다.
- TO-BE: 같은 Linux 머신과 컴파일러 환경에서, 별도로 준비한 의존성 prefix를 여러 worktree와 clean 재빌드에 재사용합니다.

## Implementation

- `bash 3rdparty/build.sh`로 기존 레시피의 의존성 8개와 Catch2를 준비합니다. producer의 상태·ccache·prefix를 CUBRID build·install과 분리합니다.
- `CUBRID_3RDPARTY_ROOT`를 지정하면 imported target을 사용하며 의존성 준비 target을 만들지 않습니다. 필수 파일 또는 레시피·컴파일러 fingerprint가 맞지 않으면 configure에서 실패합니다.
- prefix 경로에서는 unixODBC 공유 라이브러리와 SONAME 링크, 대응 소스·재빌드 안내를 설치합니다. Gateway는 설치물 내부의 라이브러리를 사용합니다.
- 외부 DB 드라이버와 등록 파일은 운영자가 제공하고, Gateway 시작 전에 `ODBCSYSINI`를 지정합니다. prefix를 지정하지 않은 기존 경로는 유지합니다.

## Remarks

### Test Plan

- 일반·prefix 경로 각각 Release·OptDebug 빌드와 설치를 확인했습니다. 각 JSON builder 실행은 21개 사례, 13,191개 assertion을 통과했습니다.
- prefix configure 검사 10건과 의존성 API probe CTest 1건을 통과했습니다.
- producer 재실행 없이 clean 재빌드·설치를 통과했습니다. prefix 파일 411개와 producer stamp 파일 151개 및 producer ccache 통계가 변하지 않았습니다.
- 원본 prefix와 producer·CUBRID build를 가린 상태에서, 설치된 Gateway가 등록된 MariaDB 드라이버로 쿼리 결과 `42`를 반환했습니다. 프로세스의 동봉 unixODBC 사용도 확인했습니다.
- 빌드 검증에는 기존 호스트 경고와 Manager/libevent의 `sysctl` 링크 문제를 위한 로컬 보정이 필요했습니다. 보정은 PR에 포함하지 않았으며 상세 문서에 기록했습니다.
- CI는 PR 생성 후 1회 실행합니다. TC 저장소 변경은 없습니다. 일반 Linux unixODBC 설치 문제인 CBRD-27711은 별도 범위입니다.
- [설계·구현·검증 상세](https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-27712/CBRD-27712-thirdparty-prefix_15609d2_codex.md)
