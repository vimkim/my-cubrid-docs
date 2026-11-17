# CBRD-27230 CI 분석 (PR #8559, 2026-11-17)

## 요약

- 결론: 실패 중 CBRD-27230 commit 4개 때문이라고 볼 근거는 없습니다. 모든 실패는 #8434에서도 같거나, #8559가 기반으로 삼은 옛 `feature/oos-merge` (merge base `1f1db1ed11`) 에서 온 것으로 보입니다.
- 근거 1: shell 실패 6개 중 6개가 #8434 run에도 있습니다. sql_by_cci shard 03-07 실패 20개는 #8434 run과 이름이 모두 같습니다.
- 근거 2: 최신 `feature/oos-merge` (`30292700ac`, develop merge 포함) 에서는 shell, sql, medium이 통과합니다. #8559의 sql_by_cci 실패 20개 중 17개도 그곳에서 통과합니다.
- 한계: sql_by_cci shard 09 실패 19개는 비교할 기준이 없습니다. #8434 run에서 이 shard는 취소되어 0건이고, 최신 base run에서는 결과 파일이 없습니다. 실패 모양 (숫자 표기 자릿수, plan 문자열) 이 develop 변경 계열이라 추정할 뿐입니다.
- 다음 할 일: #8434가 최신 `feature/oos-merge` 위로 다시 올라간 뒤 #8559도 그 위로 옮기고 CI를 다시 돌립니다. 그 run에서 shard 09가 통과하면 위 추정이 맞습니다.

## CI snapshot

| Suite | #8559 run 43856436060 (`990c529486`) | #8434 run 43830570907 (`6e4f4c4af5`) | 최신 base run 43870281031 (`30292700ac`) |
| --- | --- | --- | --- |
| medium | 975/975 통과 | 통과 | 통과 |
| shell | 실패 5, 오류 1 / 3592 | 실패 6, 오류 1 / 3593 | 통과 |
| sql | 실패 1 (shard 09) | 실패 1 (shard 09) | 통과 |
| sql_by_cci | 실패 39 / 17803 | 실패 (shard 03-07, 09 취소) | 실패 3 (shard 05, 07) |

- #8559 run: https://github.com/CUBRID/cubrid/actions/runs/43856436060
- #8434 run: https://github.com/CUBRID/cubrid/actions/runs/43830570907
- 최신 base run: https://github.com/CUBRID/cubrid/actions/runs/43870281031

## 증거 범위

- 수집: `cubrid-ci 0.2.0 (961fc3e59494)`, 2026-11-17. #8559 medium, shell, sql_by_cci summary는 `verify` 로 검증되었습니다.
- #8559 test_sql은 collector 무결성 검사에서 멈췄습니다 (shard 01의 JUnit이 summary_info보다 17건 적음, plcsql case). 그래서 sql 실패는 shard 09의 `summary_info` 와 JUnit 원본에서 직접 읽었습니다.
- #8434와 최신 base의 sql, sql_by_cci는 collector가 수집하지 못해 CI 결과 서버의 shard별 `summary_info` 와 JUnit XML을 직접 받아 비교했습니다. 이 비교는 `verify` 검증을 거치지 않았습니다.
- testcase revision: #8559 `tc/pr-8559` 공개 `5325fc1718`.

## 실패 목록과 분류

| Suite | Testcase | #8434 | 최신 base | 관계 |
| --- | --- | --- | --- | --- |
| shell | `_06_issues/_26_2h/cbrd_26915` | 실패 | 통과 | unlikely |
| shell | `_06_issues/_26_2h/cbrd_26916` (오류) | 오류 | 통과 | unlikely |
| shell | `_06_issues/_26_2h/cbrd_26861` | 실패 | 통과 | unlikely |
| shell | `_40_guava/cbrd_27236_merge` | 실패 | 통과 | unlikely |
| shell | `_06_issues/_26_2h/cbrd_25862_cms` | 실패 | 통과 | unlikely |
| shell | `_06_issues/_26_2h/cbrd_26850` | 실패 | 통과 | unlikely |
| sql | `_33_elderberry/cbrd_24042/cbrd_24182/cases/r_outer_join.sql` | 실패 | 통과 | unlikely |
| sql_by_cci | shard 03-07의 20개 | 모두 실패 | 17개 통과, 3개 실패 | unlikely |
| sql_by_cci | shard 09의 19개 (`_36_guava/cbrd_27510/*` 9개, `cbrd_27802` 2개 등) | shard 취소 | 결과 없음 | unknown |

- #8434에만 있는 실패: shell `_06_issues/_23_1h/cbrd_24642` 1개.

## 원인 묶음

### 1. 옛 base의 optimizer, 출력 차이 (shell, sql, sql_by_cci 03-07)

- 관찰: `r_outer_join.sql` 은 plan이 `nl-join (inner join)` 대신 `nl-join (cross join)` 으로 나옵니다. sql_by_cci는 `percentile`, host variable, collation 계열에서 숫자 자릿수가 다릅니다. 둘 다 #8434에서 같고, develop merge 뒤 base에서는 통과합니다.
- 추론: 이 merge base 뒤에 develop에 들어간 optimizer 수정 (CBRD-27993, CBRD-28030 등) 과 CCI submodule 갱신 (APIS-1124) 이 고친 차이입니다. CBRD-27230은 UPDATE의 OOS 저장 경로만 바꾸므로 plan 모양이나 CCI 숫자 표기에 닿지 않습니다.
- 반증 조건: 최신 base 위로 옮긴 #8559에서 이 testcase가 다시 실패하면 추론이 틀립니다.

### 2. sql_by_cci shard 09 (비교 기준 없음)

- 관찰: `cbrd_27510/01_fetch_gate_probes.sql` 은 `102.0000000000000000` 대신 `102.0` 을, `cbrd_27802.sql` 은 `312711468500.00` 대신 `312711468500.0` 을 출력합니다. `cbrd_25447.sql` 은 rewritten query 문자열이 다릅니다.
- 추론: 묶음 1의 sql_by_cci 실패와 같은 숫자 표기 계열입니다. OOS 값이 아닌 집계, 상수 출력이라 CBRD-27230과 관련이 낮습니다.
- 모르는 것: 같은 testcase가 #8434나 최신 base에서 어떻게 끝나는지 아직 증거가 없습니다.
- 반증 조건: 최신 base 위 #8559 run에서 shard 09가 계속 실패하고, 같은 run의 base 비교에서는 통과하는 경우입니다.

## 다음 할 일

1. #8434가 최신 `feature/oos-merge` 위로 다시 올라가면, #8559를 그 위로 옮기고 OOS ctest를 돌린 뒤 CI를 한 번 돌립니다.
2. 그 run의 sql_by_cci shard 09 결과로 묶음 2를 확정합니다.
3. collector의 test_sql 무결성 오류 (plcsql JUnit 누락) 는 CI 도구 문제로 따로 보고할 수 있습니다. PR 판정과는 관계없습니다.
