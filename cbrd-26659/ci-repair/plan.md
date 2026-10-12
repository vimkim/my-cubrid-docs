# PR8128 SQL 14개 정상화 계획

상태: 합의 완료. 확인일: 2026-10-12, Asia/Seoul. 계획 합의 작업: work item 331.
관련 PR: [Engine #8128](https://github.com/CUBRID/cubrid/pull/8128), [public TC #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), [private TC #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

목표는 run38245729674의 실패 전체에서 합의된 두 제외 규칙을 적용한 뒤 남는 SQL 14개를 정상화하는 것이다. 개별 TC의 수리 판정과 실제 검증 상태는 [전체 추적 표](README.md)를 기준으로 갱신한다. 이 계획의 합의와 실제 수리 완료를 구분한다.

## 수리 범위

`feature/oos-merge`의 기존 TC 구성에서 이미 같은 증상으로 실패한 항목과, 이전 delivery에서 알려진 결함의 재현기로 남긴 예상 실패 TC는 이번 필수 수리 대상에서 제외한다. 최신 shell 다섯 실패는 이 범주에 해당하며, 최신 SQL에서는 full partition 한 개가 해당한다. 새 TC를 기준 Engine에서 실행해 실패한다는 사실만으로 제외하지 않는다. 정상적인 오류를 검증하는 SQL 문장과 전체 testcase의 예상 실패를 구분한다.

SQL 14개는 모두 정상화 대상이다. 제외된 partition의 결함이 이 14개의 연쇄 실패 원인으로 입증되면, 대상 TC의 정상화에 필요한 공통 원인 수리를 허용한다. Partition의 모든 기존 결함이나 다른 제외된 shell 결함의 해결로 범위를 넓히지 않는다. 제외된 TC의 올바른 정답과 정상 discovery는 보존한다.

가설 패치를 로컬 진단에 사용할 수 있다. 최종 수리는 올바른 정답과 assertion을 보존하고, 원인을 설명하는 경로 증거 및 패치 전후 대조 결과를 확보해야 한다. 모든 큐 연산의 전체 추적을 의무화하지 않으며, 확인된 가설을 구분하는 데 필요한 증거를 선택한다.

## 착수 시 확인

1. `/home/vimkim/my-cubrid/CUBRID.md`와 관련 worktree 지침을 읽고 PR identity, head repository/ref, base ref와 모든 관련 checkout의 상태를 새로 확인한다. Engine의 기존 CCI 변경과 documentation main의 기존 변경을 보존한다.
2. Engine checkout `/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover`와 authoritative TC checkout의 `tc/pr-8128`을 재사용한다. Public TC에는 이번 인터뷰에서 로컬로 추가한 README 커밋이 있으며, 실제 게시 여부와 live head를 확인한다.
3. 실행을 시작할 때 새로운 work-tracker 항목을 등록한다. 331은 계획 합의와 문서 기록의 작업으로 유지하며, 기존 controller 수리/CI 작업 329·330 및 분석 324의 완료 기록을 변경하지 않는다.
4. 최신 receipt, per-case diff, actual shard order를 확보하고 [추적 표](README.md)의 20개 판정을 확인한다. 최신 실행의 실패 원인을 이전 실행의 관측으로 대신 확정하지 않는다.

## 진단과 검증 순서

1. 원래 partition SQL과 최신 shard 로그에서 첫 divergence와 서버/JDBC 상태 전이를 확인한다. 최신 SQL 실패는 43–57번에 연속하고 뒤 14개는 초기 DDL부터 실패했다. 이것은 연쇄 실패의 가설을 뒷받침하지만 각 TC의 원인 입증은 아니다.
2. `cubrid-test-sql-run`의 native runner로 disposable attempt를 만들고 database 실행은 기존 validation lock 아래에서 직렬 수행한다. Host workenv, 기존 DB, install selection을 보존한다. Runner의 complete discovery/expected-case manifest와 owned cleanup 계약을 따른다.
3. Debug/HA/JDBC 조건, 실제 runner/backend, CTP/JDBC 및 Engine install identity와 charset을 기록한다. 기존 OptDebug reference install과 CI Debug artifact를 구분한다. Native SQL의 요청 charset과 실제 적용 charset도 구분하며, runtime 대응을 증거 없이 CI-equivalent라고 부르지 않는다. Source/install commit 불일치나 필요한 testkit 설치 경계를 우회하지 않는다.
4. Partition을 재현하고 확인된 경로에 필요한 최소 계측, debugger 또는 실제 memory core로 가설을 구분한다. 기존 `.coredump` 텍스트는 호출 스택만 담으며 당시 객체/큐 값을 제공하지 않는다. 현재 소스에서 destination insert 후 source delete도 OOS replication 소비 루프에 들어갈 수 있다는 점은 우선 검증할 가설이다.
5. 대상 SQL 14개를 각각 새 DB에서 독립 실행한다. Case 이름, 실행 입력/정답, 실제 오류, 본래 assertion 도달, runner artifact verdict와 cleanup을 보존한다. 독립 결함이 확인되면 해당 항목 역시 이번 수리 대상으로 진단한다.
6. Partition을 포함한 원래 실행 순서와 독립 실행 결과를 비교한다. 작은 선택으로 진단을 좁힐 수 있지만 최종 순서 검증은 최신 CI가 실제 실행한 `sql/_36_guava` 72개 순서를 유지한다. Expected-case 목록은 임의 순서를 부여하는 API가 아니므로 실제 copied selection/discovery와 fixtures를 보존한다.
7. 입증된 원인을 수리하고, 대상 14개를 각각 새 DB에서 다시 실행해 정답 비교 통과를 확보한다. 원래 72-case 순서에서도 대상 14개가 통과해야 한다. 제외된 partition의 별도 결과와 다른 제외 항목은 해결 여부를 과장하지 않고 기록한다.

Engine 변경에는 `cubrid-build`를 적용하고 실제 설치 리비전을 확인한다. 단언 삭제, error output의 성공 답안 채택, 올바른 golden answer의 약화는 수리로 인정하지 않는다. Transient 진단 계측을 제거하고 필요한 focused checks와 fixed-revision review를 수행한다. 원인이 미확정이거나 검증 조건이 부족하면 필요한 추가 조건과 보존한 attempt를 보고하며 수리 완료로 기록하지 않는다.

## 게시와 한 번의 CI

구현 요청으로 착수한 수리의 focused 검증이 완료되면 scoped 변경을 commit한다. 개인 CUBRID PR 정책에 따라 Engine PR의 live head repository/ref와 필요한 TC PR head branch로 게시하며, TC 변경 게시를 CI보다 먼저 완료한다. TC merge/close와 branch 삭제는 인간이 수행한다.

`cubrid-ci-trigger`로 PR head, 같은 PR의 active run, feature testcase baseline ancestry와 pickup을 확인하고 receipt를 보존한다. Engine head가 바뀌면 한 번의 `/run all`을 사용한다. Engine이 바뀌지 않은 TC 수리라면 source run38245729674의 failure replay가 여전히 유효한지 확인한 뒤 한 번의 `/run rerun 38245729674`를 사용한다. 이미 다른 run이 진행 중이거나 replay가 불완전하면 해당 skill의 판단 경계를 따른다.

그 한 번의 CI가 terminal 상태에 도달할 때까지 기다리고 Engine/TC/build provenance, suite counts, 대상 14개의 실제 결과, 제외된 실패, 추가 실패, run URL 및 TC Merge Gate 상태를 보고한다. 예상된 제외 항목 때문에 전체 CI가 실패하는 경우와 대상 TC의 수리 미완료를 구분한다. 대상 실패가 남으면 완료로 기록하지 않는다. Terminal 보고 뒤에는 다음 인간 지시를 기다린다.

## 기록할 결과

각 대상 행에 독립 실행과 순서 실행의 attempt/run, Engine/TC/runner identity, 실제 artifact verdict, 정답 비교와 근거 위치를 남긴다. 전체 실패 목록의 역사적 run identity를 보존하고, 제외된 항목은 자동으로 해결 상태로 바꾸지 않는다. Public TC의 `sql/_36_guava/cbrd_26659/README.md`에는 합의된 범위와 완료 기준을 요약한다.

## 다음 세션의 실행 요청

> PR8128의 합의된 SQL 정상화 계획 `cbrd-26659/ci-repair/plan.md`를 실행해 주세요. 전체 추적 표의 두 제외 규칙을 유지하고 SQL 14개를 모두 정상화하세요. 제외된 partition이 그 연쇄 실패의 원인으로 입증되면 필요한 공통 원인을 수리할 수 있습니다. 가설 패치로 원인을 검증하되 올바른 정답과 assertion을 보존하고 원인 증거와 패치 전후 결과를 남기세요. 14개 모두 새 DB의 독립 실행 및 partition을 포함한 원래 72-case 순서에서 통과를 확인하세요. Scoped Engine/필요 TC 변경을 게시한 뒤 한 번의 CI를 실행하고 terminal 결과와 제외/잔여 실패 및 TC gate 상태를 보고한 다음 멈추세요.

출발 핸드오프 `/home/vimkim/tmp/handoff-pr8128-sql-partition-repair-20261012-6m9i2c77.md`의 retained artifacts와 환경 보존 계약을 참고한다. 범위와 완료 기준은 이 최종 합의와 [추적 표](README.md)를 적용한다.
