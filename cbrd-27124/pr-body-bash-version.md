https://jira.cubrid.org/browse/CBRD-27124

## Purpose

Linux에서 `ninja`나 `make`로 증분 빌드해도 현재 커밋이 표시되어야 합니다. QA가 테스트한 커밋을 식별할 수 있도록 엔진, 번들 CCI, 패키지 이름에 같은 빌드 버전을 사용합니다.

- 현재(AS-IS) `develop`은 CMake 구성 시점에 버전을 계산합니다. 같은 브랜치에서 커밋하면 `HEAD` 파일의 브랜치 이름이 그대로여서 일반 빌드 후에도 이전 버전이 표시될 수 있습니다.
- [#8606](https://github.com/CUBRID/cubrid/pull/8606)은 Git 참조 파일을 감시해 CMake를 다시 실행합니다. Git 참조 저장 형식인 reftable을 쓰는 연결 작업 트리에서 reflog를 끄면 커밋 변경을 놓치는 사례를 재현했습니다. Unix Makefiles에서는 독립 `cpack`이 버전 A로 이름을 정한 뒤 `preinstall`이 버전 B를 빌드해, A 패키지에 B 실행 파일이 들어갔습니다.
- 변경 후(TO-BE)에는 Linux 빌드가 시작될 때 Git 명령으로 현재 커밋을 읽고, 완성된 빌드의 버전으로 패키지를 만듭니다. Git의 참조 파일 배치에 의존하지 않고, 파일명과 내용이 다른 패키지 생성을 막습니다.

## Implementation

- `cmake/build-version.sh`에서 전체 커밋 ID를 한 번 읽고, 같은 ID로 커밋 수와 짧은 해시를 계산합니다. 빌드 디렉터리의 `VERSION-DIST`와 헤더에 같은 값을 기록합니다. 이 값에서 엔진의 전체 문자열과 번들 CCI의 숫자 버전을 파생합니다. Bash를 사용하면 `build.sh`와 CMake가 버전 계산을 공유합니다. CMake는 라이브러리의 ABI 버전(`SOVERSION`)과 타깃 실행 순서를 정합니다.
- 버전이 바뀌면 패키지 완료 표식부터 지웁니다. 버전을 사용하는 타깃이 모두 끝나면 표식을 다시 만듭니다. A를 전체 빌드한 뒤 B와 A에서 서로 다른 타깃만 빌드하면 버전 문자열은 A로 돌아와도 일부 바이너리는 B에 남을 수 있기 때문입니다.
- `package` 타깃은 빌드를 먼저 끝냅니다. 바이너리를 패키징하는 독립 `cpack`과 `build.sh dist`는 현재 버전의 완료된 빌드를 요구합니다. CPack은 압축 직전에 버전과 표식을 다시 검사해 Make의 `preinstall` 이후에도 처음 선택한 버전이 맞는지 확인합니다.
- 두 소스 패키징 경로는 커밋의 소스를 별도 경로에 펼치고 `VERSION-DIST`를 함께 넣습니다. Git 정보가 없는 배포본에서는 이 파일의 버전을 사용합니다.

## Remarks

- #8606과 설계를 비교하기 위한 Draft입니다. 빌드 시점에 버전을 확정하는 방식과 독립 패키징에서 부분 빌드를 거부하는 정책을 검토해 주세요.
- 실제 Linux Debug/Ninja 빌드에서 TGZ 파일명과 압축을 풀어 실행한 `cubrid_rel`의 전체 버전, 번들 CCI에 포함된 숫자 버전이 일치했습니다. 같은 버전으로 다시 빌드했을 때 C/C++ 재컴파일은 없었습니다.
- 소규모 CPack 재현에서 Ninja의 부분 빌드와 A→B→A를 거부했습니다. Unix Makefiles에서는 `preinstall` 중 버전이 바뀌면 패키징을 거부했습니다. `build.sh`의 소스 TGZ·ZIP과 CPack 소스 TGZ에 고정 `VERSION-DIST`가 들어가는 것도 확인했습니다.
- 전체 엔진 검증은 Linux Debug/Ninja에서 수행했습니다. 이 커밋의 CUBRID CI 결과는 아직 없습니다.
