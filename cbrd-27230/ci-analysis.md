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

---

# 추가 분석: run 44087080638 (2026-11-18)

## 요약

- 결론: 이번 실패도 CBRD-27230 때문이라고 볼 근거는 없습니다. testcase branch가 engine보다 한 단계 새 버전이라 생긴 불일치로 보입니다.
- 원인: 2026-11-17에 `tc/pr-8559` 에 최신 TC `feature/oos-merge` 를 merge했습니다 (공개 `a0cbf8f12`, 비공개 `69ef93dc6`). 이 TC는 engine `feature/oos-merge` `3e541fcf67` (두 번째 develop merge) 에 맞춘 것입니다. 그러나 #8559의 engine 기반은 그 이전 `30292700ac` 입니다 (#8434 `b6bcc5ffcf` 가 그 위에 있음).
- 다음 할 일: #8434가 `3e541fcf67` 이후로 다시 올라가면 #8559를 따라 옮기고 CI를 한 번 돌립니다. 그때 engine과 testcase 버전이 맞습니다.

## CI snapshot

- run: https://github.com/CUBRID/cubrid/actions/runs/44087080638 (`b3855b6d12`)
- 이 run은 2026-11-17T12:51:29Z의 `/run all` 로 시작되었습니다. 테스트 shard는 TC push (12:53Z) 뒤에 시작해 새 testcase를 받았습니다.
- 비교 기준: 최신 base run 43870281031 (`30292700ac`, 당시 TC). #8434 `b6bcc5ffcf` 의 run 44042316176은 모든 suite가 error라 쓸 수 없습니다.

| Suite | 결과 | 실패 | base에서 통과 | base에 없음 (새 testcase) |
| --- | --- | --- | --- | --- |
| medium | 통과 | 0 | | |
| shell | 실패 | 21 | 12 | 9 |
| sql | 실패 | 7 (JUnit) / 8 (`summary_info`) | 3 | 4 (+ `cbrd_27500`) |
| sql_by_cci | 실패 (shard 09 취소) | 8 | 3 | 5 |

결과는 CI 결과 서버의 shard별 JUnit XML과 `summary_info` 에서 직접 읽었습니다. `cubrid-ci verify` 검증은 거치지 않았습니다.

## 원인 묶음

### 1. 새 testcase가 아직 없는 engine 수정을 요구함

- 관찰: base에 없던 실패 testcase는 `cbrd_27445`, `cbrd_27571`, `cbrd_27650`, `cbrd_27780`, `cbrd_28002`, `cbrd_28058`, `cbrd_27441_partition_check`, `cbrd_27105_*` (shell), `cbrd_27914`, `cbrd_27948`, `cbrd_28024`, `cbrd_28049`, `cbrd-27500` (sql, sql_by_cci) 입니다.
- 관찰: 이 중 CBRD-27445, 27571, 27650, 28024, 28049의 engine 수정은 `30292700ac..3e541fcf67` 에 있고, #8559 branch에는 없습니다.
- 추론: 나머지 새 testcase도 같은 develop merge의 engine 수정을 기다리는 것으로 봅니다. 하나씩 확인하지는 않았습니다.
- 반증 조건: `3e541fcf67` 이후 기반의 #8559 run에서도 이 testcase가 실패하는 경우입니다.

### 2. OOS 오류 번호 재배치

- 관찰: `bug_bts_10516.sql`, `fbo_ddl02.sql` 은 `Error:-1397` 을 기대하지만 `Error:-1396` 이 나옵니다.
- 관찰: `3e541fcf67` 의 `src/base/error_code.h` 에서 `-1396` 은 `ER_HEAP_OOS_BAD_INLINE_HEADER`, `-1397` 은 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 입니다. #8559 branch에서는 `-1396` 이 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 입니다. TC에는 "Renumber OOS record-size errors after develop merge" commit이 있습니다.
- 결론: 같은 오류가 번호만 다르게 나옵니다. 관련: unlikely, 확신 높음.

### 3. base에서 통과하던 나머지 실패 (확인 안 함)

- 대상: shell 12개 중 대부분 (`bug_bts_7894`, `bug_bts_5398`, `cbrd_20145_*`, `02_normal_ts` 등), sql `_014_repeat.sql` (`Error:-493`, `-581`), sql_by_cci `_016_insert.sql`.
- 관찰: `bug_bts_7894` 는 loaddb 결과에 "2 errors detected" 가 더해졌습니다.
- 추론: 같은 TC 갱신 (develop merge, 오류 번호 재배치) 에서 온 기대값 변화로 봅니다. CBRD-27230은 `locator_attribute_info_force` 의 UPDATE에서만 동작하므로 loaddb와 INSERT 경로에 닿지 않습니다. 개별 diff는 다 확인하지 않았습니다.
- 반증 조건: 맞춘 버전의 run에서도 남는 경우입니다. 그때 하나씩 분석합니다.

## 교훈

- `tc/pr-<n>` 은 engine branch의 기반과 같은 시점의 TC여야 합니다. 이번에는 baseline 검사가 "최신 TC 포함" 을 요구해서 engine보다 앞선 TC를 넣었습니다. stack PR에서는 engine 기반이 따라올 때까지 TC 갱신을 미루는 편이 맞습니다.
