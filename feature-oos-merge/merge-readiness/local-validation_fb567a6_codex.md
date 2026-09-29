# 통합 후보 로컬 검증

대상은 `fb567a629cdb390fff920542173fa36f454c74a0`이다. debug/release를 별도 worktree와 설치 경로로 빌드했다. 빌드와 아래 focused 검증은 완료했지만 전체 Linux QA와 필수 exact-head CI를 대신하지 않는다.

| 검증 | 결과 | 증거 |
|---|---|---|
| debug CTest | 35/35 통과, 160.56초 | [로그](evidence/ctest-configured.log) |
| release CTest | 35/35 통과, 140.40초 | [로그](evidence/release-ctest.log) |
| debug isolation 원본 사례 | 1/1 통과, skip 0 | [실행 로그](evidence/isolation-debug-clean/runner.log), [판정](evidence/isolation-debug-clean/feedback.log), [manifest](evidence/isolation-debug-clean/manifest.json) |
| release isolation 원본 사례 | 1/1 통과, skip 0 | [실행 로그](evidence/isolation-release/runner.log), [판정](evidence/isolation-release/feedback.log), [manifest](evidence/isolation-release/manifest.json) |

사례는 `isolation/_01_ReadCommitted/partition_table/range/dml_ddl/reorganization_select_01.ctl`이다. testcase와 answer는 public corpus `89d4ec2423d94b973b5f9cf0c612c9576b9ccce6`의 원본을 사용했다. native testkit isolation runner, containment, 1 slot, retry 0, timeout 300초, testcase update 비활성 조건이다. CTP는 controller와 assets를 제공하며 native runner를 대체하지 않는다. 실행기·testcase·answer 변경은 없다.

기대 출력의 20개 그룹 각각 5000행과 전체 100000행 비교는 통과했다. 별도 trace 또는 breakpoint로 병렬/hash 경로 진입을 확인하지 않았다. 따라서 과거 QA 서버 종료 원인의 최종 해소 증명이나 전체 isolation qualification으로 표현하지 않는다.

## 준비 실패도 보존

최초 debug CTest는 CMake 구성 당시 비어 있던 CUBRID_DATABASES 때문에 fixture setup에서 실패했다. 초기 빌드가 런타임을 준비한 후 CMake를 다시 구성해 35/35 통과했다. [최초 로그](evidence/ctest.log).

최초 debug isolation은 복사한 설치에 이전 CTest의 의도적 fatal error 로그가 남아 NOK였다. 원본 기록 `/home/vimkim/tmp/oos-readiness-221/isolation-debug`를 보존했다. 새 설치 복사에서는 이전 log/databases를 제외하고 동일 원본 사례를 실행했다. release의 최초 준비는 PATH에 sbin이 없어 ip 명령을 찾지 못해 dispatch 전에 종료했다. 해당 로그 `isolation-release/preparation-missing-ip.log`를 보존하고 PATH를 고쳐 정상 실행했다. 이 두 준비 실패를 엔진 결함이나 runner 수정으로 취급하지 않는다.

전체 원본과 결과 archive는 `/home/vimkim/tmp/oos-readiness-221/`에 있다. 증거 manifest의 runner binary hash는 당시 설치물을 식별하며 깨끗한 upstream 소스 빌드임을 보장하지 않는다. 설치 runner의 Go metadata는 modified=true였고 실행 중 교체하지 않았다.
