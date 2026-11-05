# 복구 analysis의 `tran_start_postpone_lsa` assert (CBRD-27781 작업 중 발견, 별도 이슈 후보)

2026-11-05, Work742. 엔진 `CBRD-27781-postpone-commit`(base `feature/oos-merge` `d52b1889e`) debug 빌드에서 관측했다. 같은 코드가 `origin/develop` `e98bdd885`에도 있다. 이 변경의 범위가 아니어서 고치지 않았다.

## 관측

OOS 단위 테스트 프로세스가 rollback 도중 debug assert로 죽은 뒤(테스트 하네스 문제, 이후 수정), 같은 DB를 여는 다음 프로세스가 재시작 복구의 analysis 단계에서 멈췄다.

```
log_recovery.c:1750: log_rv_analysis_sysop_end: Assertion
`LSA_LE (&tdes->rcv.tran_start_postpone_lsa, &sysop_end->lastparent_lsa)' failed.
```

gdb로 analysis가 읽은 해당 트랜잭션(trid 11)의 레코드를 출력했다.

| LSA | 레코드 |
| --- | --- |
| 175\|5200 | `LOG_COMMIT_WITH_POSTPONE` |
| 175\|5336 | `LOG_SYSOP_END` (commit) |
| 175\|5584 | `LOG_POSTPONE` rcvindex 8 (`RVDK_UNRESERVE_SECTORS`) |
| 175\|5640 | `LOG_SYSOP_START_POSTPONE` |
| 175\|5752 | `LOG_RUN_POSTPONE` |
| 175\|5824 | `LOG_SYSOP_END` `LOGICAL_RUN_POSTPONE`, lastparent 175\|5200, run_postpone 174\|13320 (`RVFL_DESTROY`) |

analysis 시점 값: `tdes->rcv.tran_start_postpone_lsa` = 175\|5232, `sysop_end->lastparent_lsa` = 175\|5200.

## 원인 (소스 판독)

- 런타임은 commit-with-postpone 레코드의 시작 LSA를 기록한다(`log_append.cpp` `prior_lsa_next_record_internal`: `tdes->rcv.tran_start_postpone_lsa = start_lsa`).
- analysis는 레코드 헤더를 읽고 `log_lsa`를 데이터 위치로 옮긴 뒤 그 값을 `tail_lsa`와 `tran_start_postpone_lsa`에 넣는다(`log_rv_analysis_commit_with_postpone`: `LOG_READ_ADD_ALIGN` 뒤 `LSA_COPY (&tdes->tail_lsa, log_lsa)`). 그래서 레코드 시작보다 헤더 크기(32B)만큼 뒤를 가리킨다.
- commit 직후 첫 postpone이 논리 postpone(`RVFL_DESTROY`)이고, 그 실행 sysop 안에서 다시 postpone(`RVDK_UNRESERVE_SECTORS`)이 생겨 sysop이 `LOG_SYSOP_START_POSTPONE`을 남기면, 바깥 sysop의 lastparent는 commit 레코드의 시작 LSA(5200)다. analysis의 비교 대상은 5232이므로 assert가 실패한다.

release 빌드는 assert가 없어 상태 전이가 그대로 진행된다. debug 빌드에서 이 형태의 crash 뒤에는 DB를 열 수 없다.

## 이 변경과의 관계

이 PR의 회수 postpone(`RVOOS_RECLAIM_POSTPONE`, `RVOOS_UPDATE_DROP_POSTPONE`)은 실행 sysop 안에서 postpone을 만들지 않으므로 이 경로를 타지 않는다. 테이블 DROP처럼 파일을 지우는 트랜잭션이 postpone 실행 중 죽으면 develop에서도 생길 수 있다. 재현과 수정은 별도 이슈로 다룬다.
