# CBRD-28067 OOS 테스트 시간과 병렬 실행 검증

## Purpose

OOS 개발자가 각 ctest 항목의 결과를 1분 안에 받고, 독립적인 workspace 테스트를 함께 실행하도록 한다. 검증 대상은 개별 항목의 시간 제한과 기존 동작의 보존이다.

2026-11-12 Asia/Seoul에 GCC Debug 빌드로 측정했다. 기준 소스는 `67220b7e230ff1587ba5940001d72e10477a1fc4`이고 최종 소스는 `158f80bba0a2b86306044661ca6385ec2cfbc5bd`이다. 최종 변경은 CMake 파일 두 개와 테스트 C++ 파일 두 개이며 `src/` 변경은 없다. 빌드는 최종 커밋과 같은 파일 내용에서 만들었고 커밋 전후 소스 해시를 확인했다.

## Implementation

- CTest 묶음을 나눴다. workspace는 여섯 묶음, SQL deferred write는 네 묶음이다. 일반 vacuum과 래치 실패 케이스의 선택을 분리했다. 동시 INSERT는 8세션·1,500행의 세 라운드를 각각 실행하여 총 36,000건을 유지한다.
- 헤더를 잡은 상태에서 조회 실패와 무관한 행의 회수를 모두 관찰하면 대기를 끝낸다. 두 관찰을 assertion으로 확인한다. 기존 snapshot 관찰 구간과 재시도 간격 검사는 유지했다.
- 예상한 오류마다 스택의 함수·소스 위치를 찾는 비용을 테스트 환경에서 끈다. 오류 코드·메시지와 데이터 검사는 유지한다. SQL 케이스의 쿼리, 실패 경계, 값 크기는 줄이지 않았다.
- workspace의 각 케이스가 DB·등록 파일·설정·로그·임시 경로를 소유한다. 설치의 실행 파일·라이브러리 등은 링크로 읽는다. 공유 DB fixture의 준비·정리와 사용자 테스트는 모두 직렬로 실행한다.

코드 위치는 [시간 제한과 등록](https://github.com/vimkim/cubrid/blob/158f80bba0a2b86306044661ca6385ec2cfbc5bd/unit_tests/oos/CMakeLists.txt), [SQL 묶음](https://github.com/vimkim/cubrid/blob/158f80bba0a2b86306044661ca6385ec2cfbc5bd/unit_tests/oos/sql/CMakeLists.txt), [헤더 관찰](https://github.com/vimkim/cubrid/blob/158f80bba0a2b86306044661ca6385ec2cfbc5bd/unit_tests/oos/test_oos_real_vacuum_server.cpp), [workspace 경로 분리](https://github.com/vimkim/cubrid/blob/158f80bba0a2b86306044661ca6385ec2cfbc5bd/unit_tests/oos/test_oos_workspace.cpp)이다.

## Remarks

### Test Plan

같은 설치를 사용하는 `CUBRID`, `CUBRID_DATABASES`, 클라이언트 `PATH`를 선택한 환경에서 실행했다. 실제 실행은 구성된 OOS 빌드 하위 디렉터리를 대상으로 한다.

```sh
ctest --test-dir <build>/unit_tests/oos -j 1 -V --output-on-failure
ctest --test-dir <build>/unit_tests/oos -j 2 -V --output-on-failure
ctest --test-dir <build>/unit_tests/oos -j 6 -V --output-on-failure
ctest --test-dir <build>/unit_tests/oos -R '^test_oos_workspace_' -j 6 --repeat until-fail:5 -V
python3 check-ctest-coverage.py <build>/unit_tests/oos
```

`<build>`는 검증할 GCC Debug 빌드 디렉터리로 바꾼다. 마지막 명령의 [검사 스크립트](check-ctest-coverage.py)는 CTest JSON과 각 바이너리의 실제 GoogleTest 목록을 비교한다. `-R oos` 전체 실행도 1분 제한 변경 단계에서 두 번 통과했다. 이후 workspace 경로 분리를 추가한 최종 코드는 위의 OOS 하위 디렉터리 전체 실행으로 검증했다. 이름에 `oos`가 없는 `test_byte_span_writer`는 그 실행에서 따로 확인했고, 최종 OOS 하위 디렉터리 전체 실행에는 포함했다.

### 전체 실행 관찰값

모든 최종 실행이 62개 항목과 420개 gtest 케이스를 통과했다. 80코어 공유 서버에서 다른 작업이 계속 실행됐다. 부하가 달라 전체 시간의 차이를 일반적인 속도 향상 배수로 해석하지 않는다. 전체 실행 시간은 직렬로 남아 있는 DB 작업과 준비·정리 시간의 영향을 받는다.

| 실행 | ctest 항목 수 | 전체 초 | 최장 항목 초 | 1분 부하 평균 범위 |
| --- | --- | --- | --- | --- |
| 변경 전 | 49 | 663.62 | 174.32 | 12.70~27.06 |
| 최종 직렬 | 62 | 279.42 | 24.96 | 14.65~18.25 |
| 최종 병렬 2 | 62 | 272.37 | 36.32 | 15.96~47.43 |
| 최종 병렬 6 | 62 | 248.31 | 45.26 | 14.28~99.93 |

변경 전 표는 `ctest -R oos`의 49개 항목이다. `test_byte_span_writer` 한 항목은 별도로 통과했다. 최초 원본 제한 실행에서는 identity stamp 묶음이 60초에 종료되어 뒤의 공유 DB 테스트들이 복구 단계에서 연쇄 실패했다. 그 짧은 실패 시간은 비교에서 제외했다. 유효한 기준 측정을 위해 생성된 CTest 파일의 기존 제한만 임시로 840초로 늘렸으며, 테스트 소스와 바이너리는 원본을 유지했다. 재실행 49개는 모두 통과했다.

모든 최종 항목의 시간은 [entry-times.csv](entry-times.csv)에 있다. 새 묶음과 원래 묶음의 대응을 함께 기록했다. 분할한 행에는 원래 묶음의 전체 시간을 반복해서 표시하므로 변경 전 열을 합산하지 않는다. 전체 케이스의 시간은 [case-times.csv](case-times.csv)에 있다. 케이스 시간은 GoogleTest의 정수 ms 출력이며 ctest 항목 시간은 서버 준비·종료도 포함한다.

### 요청한 긴 케이스의 비교

| gtest 케이스 | 변경 전 ms | 최종 직렬 ms | 병렬 2 ms | 병렬 6 ms |
| --- | --- | --- | --- | --- |
| `OosRealVacuumHeaderHeld.UnrelatedHeapVacuumedWhileHeaderLookupKeepsFailing` | 61449 | 1777 | 2780 | 2028 |
| `OosRealVacuumHeaderHeld.UnrelatedRowInSameBlockVacuumedWhileHeaderLookupKeepsFailing` | 62264 | 1932 | 3276 | 2048 |
| `OosSqlDeferredWrite.PendingReferencesResolveAndFinalizeInPlace` | 14661 | 13 | 13 | 22 |
| `OosRealVacuum.UpdateStaleVersionDrainsNewSurvives` | 3249 | 759 | 1593 | 643 |
| `OosSqlDeferredWrite.RedistributionFailurePreservesSourceAndNextOperation` | 12482 | 212 | 350 | 355 |

`UpdateStaleVersionDrainsNewSurvives`의 기존 신고 54초는 이번 기준 실행에서 재현되지 않았다. 임의로 내부 대기 한도를 줄이지 않았다. SQL crash recovery 묶음은 기준 실행에서 2.55초여서 두 기존 케이스를 유지하고 시간 제한만 60초로 맞췄다. PR #8434에만 있는 두 느린 케이스는 변경하지 않았다.

### 병렬 실행의 안전 근거

workspace 여섯 묶음을 각각 다섯 번 실행했다. 30회 항목 실행과 65회 gtest 케이스 실행이 모두 통과했다. 항목별 시간은 13.12~25.02초였고 실제 workspace 부모 프로세스 여섯 개의 중첩을 관찰했다.

별도 진단 실행에서 workspace 두 케이스를 동시에 `strace -ff -tt -yy -e trace=%file,%network,%process`로 추적했다. 두 케이스 모두 통과했고 쓰기용 open은 각각 177건과 140건이었다. 원래 설치에 쓰기를 시도한 기록은 없었고, 쓰기용 open으로 연 일반 파일의 경로도 두 케이스 사이에서 겹치지 않았다. PL 서버 소켓은 서로 다른 케이스의 `tmp/sp_workspace_oos.sock`에 있었다. 시스템 이름 조회 소켓은 일반적인 외부 서비스 접근이다. JVM 성능 정보는 OS 기본 임시 디렉터리의 `hsperfdata_<user>/<pid>`에 서로 다른 PID로 생성됐다. 한 JVM이 이미 종료한 상대 JVM의 성능 파일을 정리한 기록도 있었다. 상대 JVM의 종료와 `kill(pid, 0)`의 `ESRCH` 결과를 확인한 뒤 삭제한 것으로, 테스트 DB·설정·로그의 동시 쓰기와 구분한다. 이 진단 실행 시간은 성능 표에서 제외했다.

공유 자산은 원래 설치의 권한을 유지한다. 현재 테스트 경로에서 공유 자산을 읽기만 했음을 추적으로 확인했다. DB fixture 사용자와 준비·정리 항목에는 모두 `RUN_SERIAL`이 있고, workspace 여섯 묶음에는 그 표시가 없음을 생성된 CTest 속성으로 확인했다.

### 구성 제한과 케이스 보존

- OOS 항목 62개가 모두 `TIMEOUT` 30초 또는 60초를 가진다.
- 부모와 SQL 디렉터리에서 제한 누락, 0, 음수, 60초 초과, 비수치와 빈 값을 거부하는 구성 검사를 확인했다. 유효한 60과 0.5를 포함하여 작은 CMake 구성 10개가 예상대로 성공하거나 실패했다.
- 등록된 바이너리 34개의 목록과 빌드된 OOS 바이너리 집합이 일치한다. gtest 케이스 420개가 각각 한 ctest 항목에만 속한다. 누락·중복·빈 선택을 넣은 검사용 등록은 모두 거부했다.
- 기존 기본 vacuum 등록이 함께 선택하던 헤더 보유 케이스 7개는 이제 전용 환경의 항목에만 속한다. 기존에 기본 환경에서 건너뛰던 중복 선택을 제거한 것이다.
- 코드 스타일과 `git diff --check`를 통과했다. CI는 실행하지 않았다.

Model the Domain 원칙으로 CTest가 가진 등록·fixture 속성에서 규칙을 구했다. Separate Before Serializing Shared State 원칙으로 workspace 쓰기 경로를 먼저 분리했다. Laziness Protocol 원칙으로 공유 DB의 병렬화를 위한 재설계는 추가하지 않았다. Prove It Works 원칙으로 실제 목록·시스템 호출·전체 실행 결과를 확인했다.

### Attention

reviewed by gpt-6-astra

같은 OpenAI 계열의 독립 모델이 결정 기록과 원본 로그·XML을 검토했다. 파일 분리 설명을 쓰기용 open 경로로 한정하고 JVM의 종료 파일 정리 예외를 추가했다. 오류 스택 비용 제거와 헤더 관찰 후 조기 종료를 선택한 이유도 결정 기록에 보충했다. 주요 실행 수치와 엔진 소스 변경이 없는 점은 증거와 일치했다.
