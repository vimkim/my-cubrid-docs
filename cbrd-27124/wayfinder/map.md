# Wayfinder Map — CBRD-27124 CMake build version refresh

- label: `wayfinder:map`
- ticket: [CBRD-27124 [BUILD] cubrid_rel 커밋 버전 갱신 누락과 광범위한 재컴파일 문제](http://jira.cubrid.org/browse/CBRD-27124)
- tracker: local markdown — 결정 티켓은 [`tickets/`](./tickets/)에 둔다. 각 티켓은 `blocked-by`와 `assignee`를 기록하며, 열린 티켓 중 담당자가 없고 모든 blocker가 해결된 티켓을 frontier로 본다.
- charted: 2026-08-18, `CBRD-27124-cubrid-rel-hash` @ `f30f1c260`

## Destination

구현자가 추가 설계 질문 없이 CBRD-27124 작업을 시작할 수 있도록 다음 산출물을 확정한다.

1. 일반적인 CMake 증분 빌드가 현재 Git `HEAD`를 정확히 반영하는 버전 갱신 계약
2. 버전 정보만 바뀔 때 재컴파일되는 대상을 직접 소비자로 제한하는 의존성 경계
3. `cubrid_rel`, broker build number, CPack 및 패키지 파일 이름이 같은 revision을 나타내는 일관성 계약
4. no-op 빌드와 revision-only 빌드의 허용 작업량을 판정할 수 있는 정량적 검증 기준
5. 파일별 변경 계획, 구현 순서, acceptance criteria, 자동화할 테스트와 수동 검증 항목

마지막 티켓인 [구현 가능한 명세와 JIRA handoff 조립](./tickets/T6-assemble-implementation-ready-spec.md)이 검토를 통과하고 그 결과가 JIRA 본문에 반영되면 charting은 끝난다. 실제 CUBRID 소스 변경과 PR 생성은 이 map의 범위 밖이다.

## Notes

### Standing user decision

이번 이슈는 두 결과를 함께 달성해야 한다.

- 커밋 후 다시 configure하지 않고 정상적인 CMake build만 실행해도 `cubrid_rel`이 현재 commit hash를 표시해야 한다.
- 빈 커밋처럼 소스 영향이 없는 revision 변경에서는 전체 오브젝트를 다시 컴파일하지 않고, 변동 버전 값을 직접 소비하는 최소 대상만 갱신해야 한다.

둘 중 하나만 해결한 설계는 목적지에 도달한 것으로 보지 않는다.

### Evidence anchor

- 기준 소스: `CBRD-27124-cubrid-rel-hash` @ `f30f1c26003e5aa8e93182648e06cad76fc77064`
- CMake configure 단계에서 `git rev-list`와 `git rev-parse`로 revision 값을 계산한다.
- 현재 감시 대상은 symbolic `.git/HEAD` 또는 worktree `HEAD`에 치우쳐 있다. 일반 commit은 branch ref를 이동시키므로 build-only 경로에서 configure가 다시 실행되지 않고 `version.h`와 `cubrid_rel`이 이전 값을 유지할 수 있다.
- configure가 다시 실행되어 `version.h`가 바뀌면 이를 포함하는 `config.h`를 통해 Debug/Ninja 기준 1,135개 object output이 영향을 받는 것으로 측정되었다.
- 변동 값은 `EXTRA_VERSION`, `BUILD_NUMBER`, `VERSION_STRING`이다. 런타임 버전 문자열은 주로 `release_string.c`를 통해 제공되고, `BUILD_NUMBER`는 broker 소스 7곳에서도 직접 소비한다.
- `cubrid_rel`은 자기 소스에 버전 값을 직접 갖지 않고 `release_string.c`가 포함된 `cubridsa`의 결과를 사용한다.

### Working rules

- 사람의 판단이 필요한 티켓은 grilling 방식으로 질문과 trade-off를 잠근다.
- 결정된 용어와 계약은 구현 명세에서 일관되게 사용한다.
- CUBRID 조직에 공개되는 문서에는 표준 CMake build/test 개념만 사용한다. 개인용 `just` 명령은 검증 절차나 reviewer 지침으로 노출하지 않는다.
- map은 결정 순서와 blocker만 관리한다. 열린 child ticket의 세부 질문과 답을 map에 복제하지 않는다.
- 조사 전용 티켓은 만들지 않는다. 현재 source trace와 기존 분석으로 의사결정에 필요한 사실 기반이 확보되어 있으며, 남은 일은 선택과 계약 확정이다.

### Planned decision flow

```text
Git revision 갱신 계약 ─────┐
                            ├─> 버전 정체성 계약 ─> 최소 재빌드 예산 ─> 검증/CI 행렬 ─> 구현 명세와 JIRA handoff
변동 버전 의존성 경계 ─────┘
```

초기 frontier는 [Git 커밋 갱신 계약 잠금](./tickets/T1-lock-git-revision-refresh-contract.md)과 [변동 버전 의존성 경계 잠금](./tickets/T2-lock-volatile-version-dependency-boundary.md)이다. 두 티켓은 독립적으로 논의할 수 있지만, 후속 계약은 두 결정의 조합을 전제로 한다.

## Decisions so far

아직 해결된 child ticket은 없다. 위의 두 사용자 요구는 destination의 acceptance constraint이며 구현 방식에 대한 결정은 아니다.

## Not yet specified

- Git revision 변화를 감지하는 정확한 CMake primitive와 fallback/error 정책
- 변동 버전 산출물의 파일 형태, 생성 시점, target ownership 및 정적 `version.h`와의 경계
- branch switch, detached `HEAD`, linked worktree, packed refs/reftable, reflog 비활성 환경의 지원 수준
- source distribution의 `VERSION-DIST`와 Git checkout 사이의 truth-source 우선순위
- Windows `version.rc`와 기타 플랫폼별 버전 소비자의 최종 연결 방식
- no-op 및 revision-only build에서 허용할 정확한 compile/relink/reinstall 개수
- 자동 검증 harness의 위치와 CI 필수 범위
- release branch 또는 이전 유지보수 branch로의 backport 요구 여부

각 항목은 연결된 child ticket에서만 해결한다.

## Out of scope

- CUBRID engine, CMake, packaging 소스의 실제 구현과 commit
- GitHub PR 생성, 코드 리뷰, CI 실행 및 실패 수정
- compiler, PCH, LTO, ccache 등 일반적인 clean-build 가속화
- 제품 semantic version 정책 변경 또는 commit hash 표시 제거
- 개인용 `just`/로컬 convenience tooling을 공식 workflow로 만드는 작업
- 올바른 산출물을 갱신하는 데 필요한 최소 relink, reinstall 또는 package regeneration까지 제거하는 작업
