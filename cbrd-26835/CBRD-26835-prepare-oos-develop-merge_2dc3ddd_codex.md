# CBRD-26835: feat/oos develop 병합 준비

## Purpose

[CBRD-26835](http://jira.cubrid.org/browse/CBRD-26835)는 OOS(Out-of-row Overflow Storage, 큰 가변 길이 값을 heap 레코드 밖에 저장하는 방식) 기능 브랜치를 `develop`에 통합하기 위한 상위 이슈다. 이 문서는 `develop`의 `95b79e7ed`를 병합한 뒤 cleanup commit `2dc3dddbd`에서 확인한 변경과 잔여 위험을 기록한다.

| 구분 | 상태 |
|------|------|
| AS-IS | 제품 기능, 조사용 강제 종료 코드, 브랜치 전용 CI 설정, 테스트 편의 인터페이스가 한 브랜치에 섞여 있다. 일반 빌드가 OOS 테스트를 기본으로 구성하고 CTest까지 자동 실행하며, 제품에서 제외하기로 한 CSQL 명령이 공개 API와 RPC까지 노출한다. |
| TO-BE | 병합에 필요하지 않은 진단/CI/API 표면을 제거하고 OOS 테스트를 opt-in으로 되돌린다. 저장 정합성 관련 차단 이슈의 구현과 회귀 테스트를 이 기능 브랜치에 통합한 뒤에만 병합 가능 상태로 전환한다. |

이번 cleanup의 목적은 diff를 줄이는 데 그치지 않는다. 개발 중 임시 정책을 제거해 리뷰 대상의 경계를 제품 코드로 좁히고, 빌드 성공과 기능 정확성을 구분한다. 특히 OOS 슬롯 재사용과 `vacuum`(더 이상 보이지 않는 행 버전을 정리하는 백그라운드 작업)의 UPDATE undo image 처리는 잘못된 값을 참조하거나 삭제할 수 있으므로 draft PR의 명시적 차단 조건으로 남긴다.

## Implementation

### 기준 브랜치 동기화

- `cub/develop`의 `95b79e7ed`를 기능 브랜치에 merge했다.
- cleanup 결과는 `2dc3dddbd66c320bff348036300af13f4f57b578` 한 commit에 모았다.
- cleanup commit은 28개 파일에서 69줄을 추가하고 483줄을 제거한다.

### CI와 빌드 경계 복원

- `.github/workflows/check.yml`, `tc-branch-finalize.yml`, `tc-branch-sync.yml`에서 `feat/oos` 전용 branch filter를 제거했다.
- 최상위 `CMakeLists.txt`의 기본 활성 `UNIT_TEST_OOS` 옵션을 제거했다.
- `build.sh`의 일반 build 경로에 추가됐던 자동 CTest 실행과 전용 `test` 처리를 제거했다.
- OOS 테스트가 선택된 경우에만 `unit_tests/oos/CMakeLists.txt`에서 GoogleTest를 준비한다.
- `CUBRID_UNIT_TEST_ENABLED`는 테스트 전용 bridge를 제품 빌드에서 제외하기 위한 compile definition으로 유지한다.

### 개발용 제품 인터페이스 제거

CBRD-26837에서 `;vacuum`과 `;oos_stats`는 테스트 전용이며 `develop`에 포함하지 않기로 정했다. 명령만 제거하면 호출 가능한 하위 인터페이스가 남으므로 다음 경로를 함께 정리했다.

```
CSQL command
  ├ ;vacuum
  └ ;oos_stats
       ↓
public DB API
  ├ db_vacuum()
  └ db_get_oos_stats()
       ↓
client/server network request
  └ NET_SERVER_OOS_STATS 및 handler
```

- `src/compat/db_oos.h`와 관련 선언, 메시지, 전용 오류 코드를 제거했다.
- 기존 standalone vacuum 실행은 제품 내부 함수 `xvacuum()`을 계속 사용한다.
- 제품 기능인 `SHOW HEAP OOS`는 `oos_get_stats_by_vfid()`를 사용하므로 유지한다.
- 테스트가 필요한 `vacuum_wakeup_master_daemon()`과 `xoos_get_stats_by_class_oid()`는 `CUBRID_UNIT_TEST_ENABLED` 안에만 둔다.

### 임시 강제 종료 제거

- `src/query/vacuum.c`, `src/query/vacuum_oos.cpp`, `src/storage/heap_file.c`의 조사용 `fprintf()`/`abort()` 블록을 제거했다.
- 기존 오류 반환, 오류 초기화, assertion 흐름을 복원했다.
- 이 변경은 증상을 숨겨 병합하겠다는 의미가 아니다. 해당 불변식 위반의 원인은 CBRD-27089와 vacuum/rollback 차단 이슈에서 해결해야 한다.

### 메모리 부족 변환 유지

`heap_file.c`의 OOS 이관 준비 단계는 두 `std::vector`에 대해 `reserve()`를 먼저 호출한다. 표준 컨테이너의 용량 확보 실패는 `std::bad_alloc`로만 보고되므로 이 경계의 `try/catch`를 유지한다.

```
payloads.reserve() / requests.reserve()
  ├ 성공 -> OOS 이관 준비 계속
  └ std::bad_alloc
       └ er_set(ER_OUT_OF_VIRTUAL_MEMORY) -> S_ERROR
```

이 처리는 C++ 예외가 엔진 호출자까지 전파되는 것을 막고, 부분적인 OOS 이관을 시작하기 전에 CUBRID 오류 모델로 변환한다. legacy `.c` 파일 안의 C++ 구간은 정확한 `/* *INDENT-OFF* */` / `/* *INDENT-ON* */` 주석으로 보호한다.

## Remarks

### Review Findings

Standards와 Spec 결과를 별도로 판단해야 한다. cleanup은 아래 Standards 항목을 해결했지만 Spec 차단 조건까지 해결하지는 않는다.

| 축 | 결과 |
|----|------|
| Standards | 릴리스 강제 종료, 브랜치 전용 workflow, 자동 테스트 실행, 개발용 CSQL/API/RPC, 잘못된 indent 보호 주석을 정리했다. `std::bad_alloc` catch는 CUBRID 오류 변환 경계이므로 유지한다. |
| Standards 후속 검토 | OOS 전용 logger 중복은 후속 정리 후보이나 이번 제거 범위는 아니다. CBRD-26937에서 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`는 server-internal로 결정했으므로 CCI 오류 코드 사본은 추가하지 않는다. |
| Spec | CBRD-26950, CBRD-27089, CBRD-27230, CBRD-27237이 미해결이다. CBRD-27057은 해결 상태지만 필요한 구현이 source commit `2dc3dddbd`에 없다. |

### 병합 차단 조건

| 이슈 | 현재 PR에 필요한 결과 |
|------|-----------------------|
| [CBRD-26950](http://jira.cubrid.org/browse/CBRD-26950) | 재사용된 OOS 슬롯을 이전 참조와 구분하는 generation stamp(슬롯 세대 값) 구현과 회귀 테스트를 통합한다. |
| [CBRD-27089](http://jira.cubrid.org/browse/CBRD-27089) | `HAS_OOS`인데 OOS file이 없는 상태가 생기는 근본 원인을 해결한다. |
| [CBRD-27230](http://jira.cubrid.org/browse/CBRD-27230) | 현재 forward-walk는 UPDATE undo image의 head OOS OID(OOS value chain의 첫 chunk record를 가리키는 8바이트 물리 식별자)를 commit/abort 구분 없이 소비한다. abort 시 rollback이 이전 chain을 live 상태로 복원한 뒤 vacuum이 그 chain을 삭제할 수 있다. `RVOOS_NOTIFY_VACUUM`을 commit될 때만 내보내고 forward-walk를 제거한다. CBRD-26950이 선행 조건이다. |
| [CBRD-27237](http://jira.cubrid.org/browse/CBRD-27237) | 별도 순서 변경 대신 CBRD-27230의 구조로 rollback 데이터 유실을 해결하고 회귀 테스트를 추가한다. |
| [CBRD-27057](http://jira.cubrid.org/browse/CBRD-27057) | 정렬된 레코드 네 개와 slot 항목이 페이지의 물리 용량 안에 들어가도록 4,060바이트 inline 목표 구현을 통합한다. 실제 페이지에 항상 네 행이 배치된다는 보장은 아니다. |

### Test Plan

- CMake Debug 구성으로 전체 CUBRID compile/link 성공
- CMake RelWithDebInfo 구성으로 전체 CUBRID compile/link 성공
- 구성된 OOS CTest 26개 중 26개 통과
- `git diff --check` 통과
- 임시 `REVERT BEFORE MERGE`, `HEAP ABORT`, `VACUUM ABORT` 표식 없음
- GitHub workflow에 `feat/oos` 전용 조건 없음

이 검증은 cleanup commit의 구조와 회귀를 확인한다. SQL, medium, shell CI와 위 차단 이슈의 데이터 정합성 테스트가 끝나기 전에는 draft를 ready for review로 전환하지 않는다.
