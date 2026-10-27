https://jira.cubrid.org/browse/CBRD-27124

## Purpose

- 커밋 버전만 바뀌어도 엔진 전체를 다시 컴파일하고 ccache를 재사용하지 못하는 문제를 줄입니다.
- AS-IS: `config.h`가 포함하는 `version.h`에 커밋 수와 해시가 있어 Debug 매크로 정보까지 바뀝니다. 일반 커밋을 감지하지 못해 이전 버전을 표시할 수도 있습니다.
- TO-BE: 커밋 정보는 사용하는 소스에만 전달하고, 일반 빌드로 실행 파일과 패키지 버전을 함께 갱신합니다.

## Implementation

- `EXTRA_VERSION`, `BUILD_NUMBER`, `VERSION_STRING`을 `build_version.h`로 옮깁니다. `release_string.c`와 broker의 직접 소비자만 포함합니다.
- `rel_version_string()` 선언을 버전 매크로의 포함 순서와 무관하게 제공합니다.
- Git이 알려 주는 HEAD·ref·reflog 경로를 CMake 재구성 의존성으로 등록합니다. packed ref에 loose ref 파일이 생기는 경우도 감지합니다.
- 공통 헤더의 캐시 재사용과 Git 버전 갱신을 확인하는 독립 회귀 검증을 추가합니다.

## Remarks

- 로컬 GCC 11.5 Debug(`-ggdb3`) 빌드·설치 및 `python3 cmake/tests/test_build_version.py` 검증을 통과했습니다.
- 버전 헤더 의존 범위는 1,177개 → 11개입니다. 빈 커밋 뒤 11개만 컴파일하고, no-op 빌드는 0개입니다. `cubrid_rel`과 CPack 해시도 일치했습니다.
- 수정 후 캐시를 유지하고 새 빈 커밋에서 오브젝트만 제거한 재빌드: 1,166 hit / 11 miss, **99.07%**. 같은 경로·옵션의 로컬 결과입니다.
- CI 실측은 아직 수행하지 않았습니다. #8254의 빌드별 통계로 확인할 예정입니다. PR 빌드는 공유 캐시에 쓰지 않으므로 첫 빌드는 기존 헤더 구조의 캐시와 맞지 않을 수 있습니다.
- SQL·shell·medium TC 변경은 없습니다. Windows 빌드와 reftable 저장소는 실측하지 않았습니다. 현재 로컬 구성의 ctest에는 등록된 테스트가 없습니다.
