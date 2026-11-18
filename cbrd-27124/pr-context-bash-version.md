# CBRD-27124 Bash 빌드 버전 Draft PR 준비 기록

- 이슈는 [CBRD-27124](https://jira.cubrid.org/browse/CBRD-27124)입니다. 2026-11-18 JIRA 조회 당시 상태는 Develop이며 담당자는 인치준입니다.
- Operation은 `create`입니다. 대상은 `CUBRID/cubrid:develop`, 소스는 `vimkim/cubrid:pr-8606-build-time-version-poc`입니다.
- SOURCE_COMMIT은 `5a08fc550c41ffbb00b564f2f6dd5f90c093f1a1`입니다. 로컬 HEAD와 포크 브랜치가 같은 커밋을 가리킵니다. 같은 head와 base의 열린 PR은 2026-11-18 조회 당시 없었습니다.
- 검토한 `origin/develop`은 `cf9ef288818d7bb8059606ae78edffa1dcbe942d`입니다. 공통 조상은 `25b933925529907a9ad092a36de76a0ab944e3f3`입니다. `git merge-tree --write-tree origin/develop HEAD`는 성공했습니다. [GitHub 비교](https://github.com/CUBRID/cubrid/compare/develop...vimkim:pr-8606-build-time-version-poc)
- 같은 이슈의 [PR #8606](https://github.com/CUBRID/cubrid/pull/8606)은 별도 소스 브랜치에서 열려 있으며, 검토한 head는 `85290eb56965d46fc5a00402a01c13c146d271d0`입니다. 이번 Draft는 #8606과 설계를 비교할 별도 PR입니다.
- 제안 제목은 `[CBRD-27124] Keep Linux build and package versions consistent`입니다. PR 상태는 Draft이며 담당자는 `vimkim`입니다.
- 문서 작업 브랜치는 `docs/cbrd-27124-bash-version-pr`, 문서 통합 목적지는 `main`입니다. 공개할 PR 본문은 [pr-body-bash-version.md](pr-body-bash-version.md)에 있습니다. 이 파일이 재개용 문맥 파일입니다.

## 제안한 발행 작업

1. 검토한 소스 커밋과 포크 브랜치의 현재 HEAD가 같은지 재확인합니다. 중복 PR도 다시 확인합니다.
2. 저장한 제목과 본문으로 `vimkim:pr-8606-build-time-version-poc`에서 `CUBRID/cubrid:develop`으로 보내는 Draft PR 한 건을 생성하고 `vimkim`을 담당자로 지정합니다.
3. GitHub에서 PR의 Draft 상태, head 커밋, base, 담당자와 본문을 확인합니다.

발행 대상은 위 Draft PR 한 건입니다. 검토 문서는 문서 작업 브랜치의 로컬 커밋으로 보존합니다. 발행 시점에는 채팅에서 확인한 승인 범위를 따릅니다.

## 검증 근거

- 최종 소스 커밋의 실제 Linux Debug/Ninja 엔진을 빌드하고 설치했습니다. 새 커밋에서 최상위 CMake 재실행 없이 버전이 갱신됐습니다. 같은 버전의 다음 빌드에서 `VERSION-DIST`와 `build_version.h` 수정 시각이 유지됐고 C/C++ 재컴파일이 없었습니다. Debug 프리셋에는 등록된 CTest 테스트가 없었습니다.
- `build.sh dist -z tarball`의 TGZ 이름과 압축을 푼 `cubrid_rel`이 `11.5.0.2966-5a08fc5`로 일치했습니다. 같은 아카이브의 CCI 라이브러리에는 프로토콜에 쓰는 `11.5.0.2966`이 들어 있습니다. CCI 단독 아카이브의 이름에는 CCI 자체 버전 `11.3.0.0055-bd45c0c`가 들어 있습니다.
- 실제 `build.sh dist`의 소스 TGZ와 ZIP, CPack 소스 TGZ를 열어 최상위 `VERSION-DIST`를 확인했습니다. 세 아카이브 모두 파일명과 내부 값이 `11.5.0.2966-5a08fc5`로 일치했습니다.
- 구현의 Bash와 CPack 설정을 사용하는 축소 프로젝트에서 Ninja의 부분 빌드와 A→B→A 회귀, Make의 `preinstall` 중 HEAD 변경, Git 없는 소스 패키지 입력과 in-source clean을 확인했습니다. Make 엔진 전체 빌드, Windows, 원격 CI는 이번 검증에 포함되지 않았습니다.
- #8606의 reftable 감지 누락과 Make 패키지 불일치는 당시 PR head의 CMake 버전 경로를 적용한 Linux 축소 프로젝트에서 재현했습니다. 이 결과는 이번 Draft head의 검증 결과와 별개입니다.

## 발행 기록

- 사용자가 본문과 제안한 발행 범위를 채팅에서 `yes`로 확인했습니다.
- 발행 시도 시각은 2026-11-18T18:25:37+09:00입니다.
- 확인한 본문 SHA-256은 `9484dba3341f0d7c496b8f3f89c0e6bbae9b0fa886a429f707900783f804b2cf`입니다. 포크의 소스 브랜치 HEAD는 `5a08fc550c41ffbb00b564f2f6dd5f90c093f1a1`와 일치했습니다.
- 2026-11-18T09:25:39Z에 [Draft PR #8617](https://github.com/CUBRID/cubrid/pull/8617)을 생성했습니다.
- GitHub에서 Open·Draft 상태, develop base, 포크 source 브랜치와 SOURCE_COMMIT, 제목, 담당자 vimkim을 확인했습니다.
- GitHub 본문과 검토 파일은 바이트 단위로 일치했습니다. SHA-256은 9484dba3341f0d7c496b8f3f89c0e6bbae9b0fa886a429f707900783f804b2cf입니다.
