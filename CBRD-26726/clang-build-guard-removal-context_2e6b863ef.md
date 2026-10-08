# CBRD-26726: clang_build_guard.sh 제거를 제안하는 이유

이번 PR에서 `.github/workflows/clang_build_guard.sh`와 이를 실행하는 `clang-build-guard` CI 잡을 제거할 것을 제안합니다. 최신 Clang으로 기존 컴파일러가 드러내지 못한 문제를 찾아 수정하는 것이 이번 작업의 목적입니다. 모든 PR에서 Clang 관련 변경을 계속 감시하는 정책은 팀에서 별도로 결정할 사안이라고 생각합니다.

작성일: 2026-10-08 · 대상: [CUBRID PR #8087](https://github.com/CUBRID/cubrid/pull/8087) · 검토 소스: `2e6b863ef`

<a id="summary"></a>
## 전달용 3줄 요약

1. 이번 작업의 목적은 최신 Clang의 진단으로 기존 코드의 결함을 찾아 수정하는 것입니다.
2. 모든 PR에 텍스트 기반 guard를 추가하면 공유 실행 자원과 검사·유지보수 부담이 늘어나므로, 스크립트와 CI 잡의 제거를 제안합니다.
3. 상시 Clang 빌드와 sanitizer CI는 지원 범위·담당자·운영 비용을 팀에서 합의한 뒤 별도 작업으로 추진하면 좋겠습니다.

<a id="author-context"></a>
## 작성자 설명은 이해했습니다

[작성자 답변](https://github.com/CUBRID/cubrid/pull/8087#discussion_r4215763236)과 수정된 파일 상단 주석을 보면, 의도는 이해할 수 있습니다. 현재 Clang 빌드 잡이 없으므로 이번에 고친 내용을 되돌리는 편집을 저렴한 텍스트 검사로 잡겠다는 취지입니다. R1·R2 등의 규칙도 각각 무엇을 지키는지 설명하도록 정리되었습니다.

따라서 추가 의견은 규칙 이름이나 설명을 더 고쳐 달라는 요청이 아닙니다. **이번 수정의 재발 방지를 위해 전체 PR에 지속적인 검사를 추가할 필요가 있는지**를 논의하고 싶습니다. 특정 회귀를 주입했을 때 규칙이 실패한다는 검증과, 그 규칙을 공통 CI에서 계속 운영할 필요성은 따로 판단할 수 있습니다.

<a id="scope"></a>
## 이번 작업의 목적과 상시 Clang 지원의 범위

오래된 컴파일러가 놓치는 실수를 최신 Clang의 진단으로 발견하고, 실제 결함을 소스에서 고치는 데 이번 작업의 가치가 있습니다. 그 과정에서 Clang 빌드를 가능하게 하고 경고를 정리하는 변경도 필요합니다.

이 의견의 전제는 **CUBRID를 항상 Clang으로 빌드하고 검증하는 것이 아직 회사의 합의된 정책은 아니라는 것**입니다. 이번 PR을 통해 얻은 수정 결과를 반영하는 것과, 이후 모든 변경에서 Clang 빌드의 정상 동작을 계속 보장하는 것은 책임 범위가 다릅니다.

상시 보장을 목표로 정한다면 실제 Clang 빌드와 필요한 테스트를 계속 실행해야 합니다. 컴파일러 버전, Debug·Release 범위, sanitizer 종류, 실행 주기와 실패 대응 담당자까지 정해야 합니다. 이 결정은 이번 경고 정리 PR에서 공통 guard를 추가하는 것보다 별도 논의가 적절하다고 생각합니다.

<a id="ci-burden"></a>
## 공통 CI에 추가하면 다른 PR에도 부담이 생깁니다

현재 [check.yml](https://github.com/CUBRID/cubrid/blob/2e6b863efc02c8433845f61a4836df0b8fcf67cf/.github/workflows/check.yml#L17-L24)은 `develop`, `release/11.**`, `feature/**`를 대상으로 한 PR에서 실행됩니다. 새 [clang-build-guard 잡](https://github.com/CUBRID/cubrid/blob/2e6b863efc02c8433845f61a4836df0b8fcf67cf/.github/workflows/check.yml#L216-L224)에는 변경 파일에 따른 실행 제한이 없고, 별도 runner에서 서브모듈까지 체크아웃합니다.

이 설정이 반영되면 이번 이슈와 관계없는 PR의 검사 목록에도 잡이 추가됩니다. 스크립트 실행 자체가 짧더라도 runner 준비와 체크아웃이 반복되고, 검사에 문제가 생기면 다른 기여자도 결과를 읽고 원인을 확인해야 합니다. 향후 코드나 빌드 구성이 달라지면 규칙과 예외를 함께 관리할 사람도 필요합니다.

**무료여도 실행 자원에는 제한이 있습니다.** [GitHub Actions 제한 안내](https://docs.github.com/en/actions/reference/limits#job-concurrency-limits-for-github-hosted-runners)에 따르면 표준 runner의 동시 실행 수는 플랜에 따라 제한됩니다. 기본값은 Free 20개, Team 60개이며, GitHub-hosted 잡의 실행 시간에도 최대 6시간 제한이 있습니다. 추가 잡은 실행 중에 동시 실행 슬롯 하나를 사용하므로, 한도에 도달한 상황에서는 다른 GitHub-hosted CI의 대기에 영향을 줄 수 있습니다. 회사의 실제 플랜과 현재 사용량, 이 잡이 만드는 대기 시간은 확인하지 않았습니다.

**실행 제한과 유료 크레딧은 구분해야 합니다.** 현재 `CUBRID/cubrid`는 공개 저장소이고 이 잡은 `ubuntu-24.04`를 사용합니다. [GitHub 표준 runner 안내](https://docs.github.com/en/actions/reference/runners/github-hosted-runners#standard-github-hosted-runners-for-public-repositories)와 [과금 안내](https://docs.github.com/en/billing/concepts/product-billing/github-actions)에 따르면 이 조건의 실행 시간은 무료이며, 비공개 저장소의 월별 무료 실행 시간을 차감하는 방식과 다릅니다. 따라서 이 잡이 회사의 유료 크레딧을 차감한다는 주장은 근거로 쓰기 어렵습니다. 공통 CI를 추가할 때 검토할 비용은 공유 실행 슬롯, 반복되는 준비·체크아웃, 검사 관리와 결과 확인 부담입니다. 향후 유료 runner 등을 도입할 경우 과금은 그 설정에 맞춰 별도로 검토해야 합니다.

<a id="guard-limits"></a>
## 텍스트 검사는 이번 수정의 모양을 지키는 우회책입니다

[스크립트](https://github.com/CUBRID/cubrid/blob/2e6b863efc02c8433845f61a4836df0b8fcf67cf/.github/workflows/clang_build_guard.sh#L43-L68)는 특정 매크로 이름이나 코드 문자열, 빌드 파일의 항목을 찾습니다. 이미 알려진 형태로 되돌아가는 변경을 일부 잡을 수 있습니다. 하지만 코드가 같은 의미를 다른 형태로 표현하거나 새로운 결함이 생기면 그 정상 동작을 일반적으로 판단할 수는 없습니다.

작성자도 [상단 주석](https://github.com/CUBRID/cubrid/blob/2e6b863efc02c8433845f61a4836df0b8fcf67cf/.github/workflows/clang_build_guard.sh#L19-L37)에 이 한계를 명시했습니다. 이 검사를 통과했다고 해서 Clang 빌드나 실행 결과가 계속 올바르다고 보장되는 것은 아닙니다. 이런 한계가 있는 임시 보호 장치를 모든 PR의 공통 검사로 유지할 만큼 필요한지에 대해서는 신중하게 판단하고 싶습니다.

<a id="recurrence"></a>
## -w가 다시 들어갈 가능성은 어떻게 볼 것인가

기존 `-w`는 Clang 빌드를 통과시키기 위한 단순한 우회 설정으로 이해하고 있습니다. 이번에 제거 이유를 코드와 리뷰에 남겼으므로, 같은 옵션을 다시 넣을 가능성은 낮다고 판단합니다. 재발 가능성이 전혀 없다고 보장할 수는 없지만, 이 가능성 하나 때문에 모든 PR에 별도 검사를 영구적으로 둘 필요는 낮다고 생각합니다.

나중에 같은 설정이 다시 들어가 문제가 확인되면 그 변경을 다시 수정하면 됩니다. 이는 이 위험을 리뷰와 필요할 때의 Clang 점검으로 관리하자는 선택입니다. 특히 정수 오버플로처럼 사용자에게 잘못된 결과를 주는 결함은 중요하므로, 해당 동작을 확인하는 회귀 테스트의 필요성은 guard의 존치와 별도로 검토해야 합니다.

<a id="proposal"></a>
## 이번 PR에서 요청하는 변경

1. `.github/workflows/clang_build_guard.sh`를 제거합니다.
2. `.github/workflows/check.yml`에서 `clang-build-guard` 잡을 제거합니다.
3. Clang의 진단으로 확인한 소스 결함 수정과 필요한 빌드 설정 변경은 유지합니다. 새 `memory_wrapper.cpp`에 필요한 기존 `memory-monitor-check` 예외도 유지합니다.
4. 상시 Clang 빌드나 야간 sanitizer CI가 필요하다면 팀의 정책과 운영 범위를 합의한 뒤 별도 이슈에서 검토합니다.

이렇게 범위를 정하면 이번 PR의 결함 수정은 반영하면서, 공통 CI의 지속적인 운영 책임은 팀이 명시적으로 결정할 수 있습니다.

<a id="evidence"></a>
## 확인 기준과 한계

이 문서는 리뷰어의 제안과 그 배경을 설명하는 자료입니다. 회사의 상시 Clang 지원 정책에 관한 전제는 요청자가 공유한 맥락이며, 별도의 사내 정책 문서를 확인한 결과는 아닙니다.

- PR HEAD: `2e6b863efc02c8433845f61a4836df0b8fcf67cf`
- 대상 브랜치 및 조회 시점의 tip: `develop`, `30043f492225c8350aa15455dc329c87227b5fdf`
- 비교 기준 merge-base: `0320a768b09bda9e58e93875398450b0580c8e22`
- 조회: 2026-10-08. `gh-pr-info`, GitHub PR API, 인라인 댓글·리뷰 요약·대화 댓글의 전체 페이지를 확인했습니다.
- 코드 확인: `git show HEAD:<path>` 및 `git diff <merge-base> HEAD -- .github/workflows/check.yml .github/workflows/clang_build_guard.sh`로 실행 대상과 추가된 잡, 검사 방식을 확인했습니다.
- 이번 문서 작업에서는 빌드·회귀 테스트·CI를 실행하지 않았고, 실행 시간이나 회사의 실제 동시 실행 한도·사용량·청구 내역도 확인하지 않았습니다.

찾아보기: [작성자 설명](#author-context) · [작업 범위](#scope) · [CI 부담과 과금](#ci-burden) · [guard의 한계](#guard-limits) · [-w 재발 판단](#recurrence) · [변경 요청](#proposal)
