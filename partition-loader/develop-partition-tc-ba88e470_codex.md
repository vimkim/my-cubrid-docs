# develop partition-loader TC 수정 및 재현 결과

2026-09-15 · Work item 153

## 결론

develop `ba88e4700`에서 **파티션 범위를 벗어난 값의 저장을 재현했다.** `i < 10`인 `t__p__p0`에 server-side loaddb가 `1, 100`을 저장하고 종료 코드 0을 반환한다. SQL INSERT는 같은 `100`을 파티션 오류로 거부한다. 원본 TC의 성공 기대값이 이 동작을 허용하고 있었다.

원본 TC는 1건 실행·1건 통과, 기대값을 바로잡은 TC는 1건 실행·1건 실패했다. 수정본의 정상 test1/test3 출력 비교 및 마지막 스키마·행 수 비교는 통과했다. 엔진은 수정하지 않았다.

## 실행 기준

| 항목 | 확인값 |
|---|---|
| 엔진 worktree / branch | `/home/vimkim/gh/cb/develop` / `develop` |
| 엔진 SHA | `ba88e4700a89526b015bcda9628a1c43b3a52176` |
| 빌드 | GCC debug, `debug_gcc`; configure/build/install 완료 |
| 원본 설치 | `/home/vimkim/.cub/install/develop/debug_gcc` |
| TC SHA | `48250d60cf8cece13abaff0f1b29982c59a256c0` — origin/develop fetch로 확인 |
| 수정 TC worktree / branch | `/home/vimkim/gh/tc/develop-partition-tc` / `fix/develop-partition-tc` |
| CCI / JDBC | CCI `ef5470ffae4aa934425145e393fefc81899c84a7` (기존 상태 보존), JDBC `20aeb347b4d82ae74d89fe263141b044b52eb5b9` |
| 격리 | 별도 HOME·설치 복사본·DB, user/PID/network/IPC/UTS namespace, 외부 파일시스템 읽기 전용 |
| 선택 TC | `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh` 하나 |
| CTP 설정 | `testcase_update_yn=false`, retry 0, 기존 결과 이어 실행 안 함, 삭제 안 함 |

기존 CCI 상태와 `PLAN.md`, `demodb_loaddb.log`, `insert.sql`, `test.sh`를 보존했다. JDBC만 지정 submodule revision으로 초기화했다. CCI가 엔진의 pinned revision과 다른 상태이므로 완전히 pristine한 전체 submodule 조합이라고 표현하지 않는다.

원본 설치와 격리 복사본의 실행 파일·라이브러리 SHA-256을 기록했다. CTP child의 `CUBRID=/home/vimkim/CUBRID` 설정과 최소 재현의 실제 `/proc/.../exe`를 확인했다. 서버 SHA-256은 `ec2df55dcb7d7bfa05d6dfd77d7e9689dfa0ebcaee1e95dc60239dab123aff98`이다. CTP 설치에는 Git metadata가 없어 사용한 runner/helper/JAR hash를 대신 남겼다. [manifest](develop-partition-tc-ba88e470_codex/manifest.json), [빌드 로그](develop-partition-tc-ba88e470_codex/configure-build.log)

## TC 변경

오류 유도 절차(`unloaddb` 후 object 파일에 `100` 추가)는 유지했다. test2 출력은 별도 파일에 남기고 다음 항목을 직접 검증한다.

1. loader 종료 상태가 실패인지 확인.
2. `Appropriate partition does not exist` 오류 확인.
3. 부모 테이블과 파티션의 행 수가 모두 0인지 확인.
4. 같은 DB에서 보존한 정상 object 파일을 다시 load.
5. 부모와 파티션에 `i = 1`인 행 하나만 있는지 확인.

test1/test3와 마지막 별도 비교를 보존하고, Linux/Windows answer에서 test2의 잘못된 성공 기대 블록만 제거했다. Windows 실행은 하지 않았다. 변경은 3개 파일, 55줄 추가·40줄 삭제이며 커밋·push하지 않았다.

[TC patch](develop-partition-tc-ba88e470_codex/testcase.patch) · [수정 스크립트](develop-partition-tc-ba88e470_codex/patched-cases/partition_tbls.sh)

## 원본 / 수정 CTP 결과

| 검증 | 원본 | 수정 |
|---|---|---|
| 실행 / 실패 / skip | 1 / 0 / 0 | 1 / 1 / 0 |
| test2 오류 입력 | 2행 성공 기대값과 일치 | 종료 코드 0, 파티션 오류 없음 → NOK |
| 오류 입력 직후 행 수 | 검사 없음 | 부모 2 / 파티션 2 → NOK |
| 후속 정상 load | 검사 없음 | 종료 코드 0 → OK |
| 후속 load 이후 정확한 한 행 | 검사 없음 | 잔존 행 때문에 NOK |
| test1/test3 성공 출력 비교 | OK | OK |
| 마지막 스키마·10,000행 비교 | OK | OK |

수정본 assertion은 9개 중 3개 OK, 6개 NOK이다. CTP launcher 자체는 양쪽 모두 exit 0이어서 이를 통과 근거로 사용하지 않았다. 최종 요약과 정확한 testcase, assertion 결과를 판정 기준으로 삼았다.

[원본 runner](develop-partition-tc-ba88e470_codex/baseline/runner.log) · [수정 runner](develop-partition-tc-ba88e470_codex/patched/runner.log) · [수정 assertion](develop-partition-tc-ba88e470_codex/patched/partition_tbls.result) · [실제 loader 출력](develop-partition-tc-ba88e470_codex/patched/test2_invalid.output)

## 실제 저장값을 확인한 최소 재현

```sql
create table t(i int)
partition by range(i) (partition p0 values less than (10));
```

object 입력:

```text
%class t__p__p0 (i)
1
100
```

서버를 실행한 DB에서 다음과 같이 수행했다.

```bash
cubrid loaddb -C -v -u dba -d t__p__p0.objects partition_probe
csql -u dba -t -N -c 'select i from t order by i;' partition_probe
csql -u dba -t -N -c 'select i from t__p__p0 order by i;' partition_probe
```

| 관측 | 결과 |
|---|---|
| loaddb | 종료 코드 0, `Total 2 object(s) inserted, 0 object(s) failed.` |
| 부모 SELECT | `1`, `100` |
| 파티션 SELECT | `1`, `100` |
| 다음 정상 `1` load 이후 | `1`, `1`, `100` |
| SQL `insert into t values (100)` | 종료 코드 1, 파티션 오류 |
| SQL `insert into t__p__p0 values (100)` | 종료 코드 1, 파티션 오류 |

**판정:** 실제 범위 위반 행 저장을 확인했다. 실패를 기대한 batch가 성공 커밋되어 rollback 기대 검사가 실패한 것이며, rollback 구현 자체의 고장까지 입증한 것은 아니다. 다음 정상 load 명령은 성공하지만 앞서 저장한 잘못된 행은 남는다.

보조 관찰: `%class t (i)`로 입력 대상을 부모로 바꾼 별도 probe에서는 loader가 성공 및 2행 삽입을 보고했지만 부모/파티션 SELECT는 0행이었다. 이를 정상 rollback으로 해석하지 않는다. 이 경로의 저장 위치·원인 분석은 수행하지 않았으며 이번 TC의 직접 근거는 `%class t__p__p0` 입력 결과이다.

[probe 코드](develop-partition-tc-ba88e470_codex/probe/probe.py) · [모든 명령·종료 코드·출력·실제 서버 identity](develop-partition-tc-ba88e470_codex/probe/result.json)

초기 보조 probe는 서버 시작 출력 수집에서 멈춰 해당 namespace만 종료했다. 출력 수집을 파일로 바꾸고 loopback을 활성화한 새 probe는 완료됐다. 실패한 초기 시도도 cache의 `probe-initial`에 보존했다. 원본/수정 CTP 결과와 구분한다.

## 검증 및 한계

- `bash -n`, `git diff --check` 통과.
- 독립 Standards review: 0 findings. 독립 Spec review: 0 actionable findings. [review](develop-partition-tc-ba88e470_codex/review.md)
- Linux GCC debug에서 실행했다. Windows 및 release 빌드는 미실행.
- 엔진 원인 코드 분석·수정, PR/JIRA 게시, 메시지 전송은 수행하지 않았다.
- 원본 실행 환경과 초기 시도를 포함한 전체 자료: `/home/vimkim/.cache/codex/develop-partition-ba88e470`.

## QA 전달용 문구

> develop(ba88e4700)에서 partition_tbls test2를 재검증했습니다. `i < 10` 파티션에 loaddb가 `100`을 포함한 2행을 성공 저장하는 현상을 확인했습니다. 기존 answer도 이를 성공으로 기대해 원본 TC는 통과했습니다. TC를 오류 반환·실패 후 0행·후속 정상 load 결과를 검사하도록 수정하자 해당 검사가 실패했고, 정상 test1/test3 및 마지막 비교는 통과했습니다. TC 기대값 정정과 함께 server-side loaddb의 파티션 범위 검증 문제를 확인할 필요가 있습니다.
