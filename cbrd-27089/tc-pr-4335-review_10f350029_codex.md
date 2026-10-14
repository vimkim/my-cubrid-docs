# TC PR #4335 코드 리뷰: partition loader의 거절과 rollback

작성: **2026-10-14 (Asia/Seoul)**. [비공개 TC PR #4335](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4335)의 변경에서 Standards와 Spec 지적사항은 각각 **0건**이다. 잘못된 child 입력을 성공으로 기대하던 답안 대신 명시적인 거절·rollback·후속 load 검증을 추가했다. 기존 test1/test3 검증은 보존한다.

## 검토 대상과 기준

| 항목 | 고정한 값 |
| --- | --- |
| TC 저장소 / head branch | `CUBRID/cubrid-testcases-private-ex` / `tc/pr-7927` |
| TC head | `10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532` |
| TC base branch / tip | `feature/oos-merge` / `c4b9d482fbd491a68510b2552df2c3cac91911fc` |
| 관련 엔진 PR | [CUBRID/cubrid #7927](https://github.com/CUBRID/cubrid/pull/7927), [CBRD-27089](http://jira.cubrid.org/browse/CBRD-27089) |
| 현재 엔진 head / head repository | `9ba5b9b927e5c1820f2f9d7a6f7d9acfa447e773` / `vimkim/cubrid` |
| 현재 엔진 head / base branch | `feat/oos-deferred-write` / `feature/oos-merge` |
| 검토한 커밋 | `57ed79b21` 초기화, `10f350029` loader 검증 |

현재 PR metadata와 로컬 TC checkout의 head/base가 일치함을 확인했다. 기준 ref는 실제 Git object로 해석되며 diff는 비어 있지 않다.

```sh
git diff c4b9d482fbd491a68510b2552df2c3cac91911fc...10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532
git log c4b9d482fbd491a68510b2552df2c3cac91911fc..10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532 --oneline
```

Spec는 [기존 독립 testcase 평가](testcase-assessment/assessment.md)의 partition 계약을 사용했다. 2026-10-14에 `cubrid-jira search CBRD-27089`로 조회한 이슈는 목적지 heap 선택 이후의 기록을 요구하며 loader도 해당 경로에 포함한다. 이 TC PR은 loader의 partition 검증을 다루며 엔진의 모든 OOS 시나리오를 검증한다고 주장하지 않는다.

매뉴얼 `3b6ae97bfbdc664b010ffa933ded5a05b291ae03`의 [range partition 규칙](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L115), [직접 child 접근 규칙](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L325), [loaddb commit 주기](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/admin/migration.inc#L422)를 대조했다. SQL 규칙을 loader에 적용하는 근거는 매뉴얼만이 아니라 엔진 routing 경로와 기존 독립 loader 실행이다.

OOS 규범은 `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`를 EOF까지 읽었고 읽기 전후 SHA-256은 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`로 동일했다. 이는 설계 기준이며 TC 실행의 증거를 대신하지 않는다.

두 TC 저장소에서 적용할 `AGENTS.md`, `AGENTS.user.md`, `CODING_STANDARDS.md`, `CONTRIBUTING.md`를 찾지 못했다. Standards는 개인 CUBRID 정책의 기존 들여쓰기 보존 규칙과 `code-review`의 Fowler 코드 냄새 기준을 적용했다. Standards와 Spec는 서로 독립적인 에이전트가 검토했다.

## Standards

**지적 0건.** 문서화된 규칙 위반 및 보고할 수준의 Fowler 코드 냄새를 발견하지 못했다. `partition_tbls.sh:131–163`의 공통 검증 함수와 `:189–207`의 시나리오 호출은 반복된 판정 로직을 적절히 묶는다. 기존 스크립트의 들여쓰기를 변경하지 않았으며 새 검증은 `write_ok`/`write_nok` 관례를 따른다. `bash -n` 및 `git diff --check`가 통과했다.

## Spec

**지적 0건.** 기존 평가의 요구인 잘못된 direct-child 입력 거절, 유효 child 입력 수용, root 입력 routing, 기존 commit 보존과 실패 batch rollback을 충족한다.

- [생성 fixture와 실패 검증](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532/shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh#L55): child를 대상으로 하는지 확인하고, 실패 종료 코드·진단·객체 수와 root/child의 rollback을 각각 검사한다. 같은 DB에서 정상 입력의 성공과 정확한 행도 확인한다.
- [두 child 시나리오](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532/shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh#L165): root `1,11` 분배, 유효 child `2`, 잘못된 child batch `3,11` 및 root batch `4,100`의 거절·rollback, 기존 `1,2,11` 보존, 다음 root `12`의 성공을 검사한다. child별 count/min/max는 이 작은 fixture의 정확한 값 집합을 검사하기에 충분하다.
- 서로 다른 실패 진단은 현재 엔진의 [목적지 없음](https://github.com/CUBRID/cubrid/blob/9ba5b9b927e5c1820f2f9d7a6f7d9acfa447e773/src/query/partition.c#L3530)과 [명시한 child 불일치](https://github.com/CUBRID/cubrid/blob/9ba5b9b927e5c1820f2f9d7a6f7d9acfa447e773/src/query/partition.c#L3671) 계약에 맞는다. commit 이후에만 성공 건수를 더하는 [batch 처리](https://github.com/CUBRID/cubrid/blob/9ba5b9b927e5c1820f2f9d7a6f7d9acfa447e773/src/loaddb/load_session.cpp#L175)도 대조했다.
- Linux/Windows 답안에서 test2 성공 transcript만 제거했고 test1/test3 바이트와 기존 실행을 보존했다.

누락·부분 구현, 범위 확장, 잘못 구현한 요구사항을 찾지 못했다. 새 DB 실행과 Windows 실행은 수행하지 않았다. 전체 OOS 동작 검증으로 확대하지 않는다.

## 시나리오와 oracle 확인

| 입력 | 기대 동작과 독립 확인 |
| --- | --- |
| `unloaddb`가 생성한 p0 입력 `1,100` | `-c 100`으로 두 행을 같은 commit 구간에 둔다. 실패 종료 코드, partition 진단, 0 inserted/1 failed와 root/p0의 0행을 모두 검사 |
| 같은 DB의 유효한 p0 입력 `1` | load 성공과 root/p0 각각 정확히 `1` 한 행을 검사 |
| root `1,11`, child p0 `2` | 성공 건수와 root/p0/p1의 분배를 검사 |
| child p0 `3,11` | sibling p1에 속하는 `11`을 직접 p0로 넣으면 거절해야 한다. 앞의 `3`도 rollback되고 기존 행은 보존 |
| root `4,100` | `100`을 받을 child가 없어 거절해야 한다. 앞의 `4`도 rollback되고 기존 행은 보존 |
| 후속 root `12` | 실패 뒤 정상 load가 계속 가능하고 p1에 새 행이 들어감을 검사 |

성공 transcript를 삭제한 자리에 실패 자체만 허용한 것이 아니다. 종료 코드·진단·건수와 실제 저장 결과를 함께 검사하여 조기 실패, 부분 commit 또는 잘못된 routing을 구분한다. 생성 fixture의 진단은 schema/data load를 함께 수행하는 경로의 기존 독립 실행으로 확인했고, 별도의 두-child 입력은 root/child 진단 차이를 직접 검사한다.

## 검증과 실행 증거의 범위

```sh
bash -n shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh
git diff --check c4b9d482fbd491a68510b2552df2c3cac91911fc...10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532
```

이번 리뷰에서 두 명령이 통과했다. 별도의 byte audit는 Linux와 Windows 답안 모두 test2의 19개 newline 구분 행만 제거되었음을 확인했다. 기존 carriage return도 보존했다. 스크립트의 기존 test1 및 test3 이후 부분은 바이트 동일하다. 감사 결과는 `/home/vimkim/tmp/tc-pr7927-review-20261014/static-audit.json`에 보관했다.

기존 native 실행의 [identity](testcase-assessment/evidence/final-partition/identity.json), [JUnit](testcase-assessment/evidence/final-partition/test-shell.xml), [검증 결과](testcase-assessment/evidence/final-partition/verification.txt), [assertion 건수](testcase-assessment/evidence/final-partition/assertion-counts.json)를 이번 리뷰에서 다시 읽었다. 엔진 `f3144ab4b72fc2bf73f115c9da1cf193c756457a`와 정확한 TC 커밋 `10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532`에서 **1/1 PASS, 28 OK, 0 NOK, 0 skip**이다. 이전 [CI 보고서](ci_analysis_report_f3144ab_codex.md)에도 해당 수정 case의 양성 PASS 기록이 있다.

이번 리뷰에서는 DB 테스트와 CI를 새로 실행하지 않았다. 기존 Linux 결과를 Windows 또는 현재 엔진 `9ba5b9b`의 실행 검증으로 확대하지 않는다. fixture는 INT 값만 사용하므로 OOS value chain의 물리적 소유 heap, vacuum 또는 복제까지 검증하는 TC는 아니다. 해당 범위는 엔진 PR의 별도 검증 증거를 확인해야 한다. TC 저장소는 수정하지 않았다.

**집계: Standards 0건(최고 심각도 없음), Spec 0건(최고 심각도 없음).**
