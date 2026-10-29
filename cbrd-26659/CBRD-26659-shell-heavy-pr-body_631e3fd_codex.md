https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- PASS한 20초 초과 OOS shell TC를 별도 heavy 실행·검토 대상으로 전달합니다.
- AS-IS: 일반 CI에 장시간 비HA OOS TC 38개가 포함되어 있습니다.
- TO-BE: 일반 shell에는 31개를 남기고, 38개는 `shell_heavy`에서 관리합니다.

## Implementation

- `shell_heavy/_40_guava`에 TC 38개와 의존 파일 34개를 가져왔습니다.
- 원본 `02d023932`와 72개 파일의 내용·mode를 유지하고 경로·hash 대조표를 추가했습니다.
- 공용 helper와 TDE fixture를 heavy 아래에 함께 배치하여 상대 경로를 유지했습니다.
- 기존 [PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)의 대응 변경은 38개 원본 진입점을 `disabled/heavy`로 보존합니다. 나머지 일반 31개와 기존 실패·HA·장시간 비활성 사례는 유지합니다.

## Remarks

- 선정 근거는 [CI 40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124)의 비HA OOS 69개 PASS 중 20초 초과 38개입니다. 한 번의 관측이며 이후 실행 시간을 보장하지 않습니다.
- Engine `e3589ae` optdebug의 native 전체 실행은 **38 PASS·0 FAIL·0 SKIP**입니다. TC당 120초 제한으로 직렬 실행했고 모두 제한 안에 끝났습니다.
- 72개 파일의 원문·mode, heavy 38개·잔여 일반 31개, 기존 비활성 70개 보존과 Bash 55개 문법을 확인했습니다.
- 현재 일반 `gha-ci`는 `shell_heavy`를 실행하지 않습니다. QA와 heavy의 실행 주기·담당을 정해야 합니다.
- 과거 실패 원인 분석, 이전부터 비활성인 PASS 3개와 2분 초과 TC 처리는 별도 후속 작업입니다.
