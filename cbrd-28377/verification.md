# CBRD-28377 verification: OOS notification reclaim defers on a timed-out wait

## Question and finding

- 질문: vacuum이 UPDATE가 버린 OOS chain(`RVOOS_NOTIFY_VACUUM`)을 회수하다 일시적 오류(-1123 등)를 만나면 왜 서버가 FATAL로 멈추는가? 서버를 멈추지 않고 고칠 수 있는가? 고치면 chain이 새지 않는가?
- 독자: CBRD-28377 수정 PR의 리뷰어, OOS 담당자.
- 결론: 이 경로는 로그 블록을 완료로 표시하지 않으면 vacuum이 블록을 다시 처리한다. 회수기는 다시 실행하면 남은 chain을 끝까지 지운다(OOS-ADR-0008 decision 3). 그래서 page fix 단계의 일시적 오류는 서버를 멈추는 대신 블록을 나중에 다시 처리하게 넘겨도 안전하다. 수정 후 fault injection 시험에서 서버는 멈추지 않았고 chain은 모두 회수되었다.
- 남은 질문: 정규 사양 문구 개정(아래 "Spec conformance"), REMOVE postpone 경로의 정책, 재시도 back-off(CBRD-28276).

## Revisions and environment

| 항목 | 값 |
| --- | --- |
| 기준 소스 | `CUBRID/cubrid` `develop` [`ca39c2c6a4`](https://github.com/CUBRID/cubrid/commit/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e) (2026-11-25 기준 `origin/develop`) |
| 수정 커밋 | 로컬 브랜치 `CBRD-28377` 의 `ebdd0f0462ab32312d897805c09c207dfde550d3` (아직 push하지 않음). 독립 리뷰는 그 이전 버전 `52bf95f21e` 를 보았고, 리뷰 지적 반영분을 합쳐 `ebdd0f0462` 이 되었다 |
| 빌드 | Linux, GCC debug 프리셋(`debug_gcc`), OOS 단위 시험 활성화 |
| 분석 날짜 | 2026-11-25 (Asia/Seoul) |
| 관련 이슈 | [CBRD-28377](https://jira.cubrid.org/browse/CBRD-28377), [CBRD-27933](https://jira.cubrid.org/browse/CBRD-27933), [CBRD-28276](https://jira.cubrid.org/browse/CBRD-28276), [CBRD-28378](https://jira.cubrid.org/browse/CBRD-28378), [CBRD-28379](https://jira.cubrid.org/browse/CBRD-28379) |
| 사양 | OOS-CONTEXT.md §4 "Reclaim error policy", OOS-ADR-0008 (accepted, last_updated 2026-11-12), 허브 [CBRD-28315](https://jira.cubrid.org/browse/CBRD-28315) |

## Cause at the base revision

- `oos_reclaim_notified_chains ()` 는 chain마다 `oos_delete ()` 를 부른다. 오류가 `ER_INTERRUPTED` 면 돌려주고, 손상된 chain 오류(`ER_HEAP_OOS_CORRUPTED_RECORD`, `ER_HEAP_OOS_INVALID_ARGUMENT`)는 보고하고 건너뛴다. 나머지는 모두 `oos_reclaim_fail_stop ()` → `logpb_fatal_error ()` 로 간다([oos_file.cpp:4297](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/oos_file.cpp#L4297), [4379](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/oos_file.cpp#L4379)).
- -1123(`ER_CSS_PTHREAD_COND_TIMEDOUT`)은 `pgbuf_allocate_bcb ()` 가 빈 버퍼 프레임을 `page_latch_timeout_in_msecs` 안에 얻지 못할 때 낸다([page_buffer.c:9049](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/page_buffer.c#L9049)). debug 빌드는 그 직전에 assert로 멈추므로([9042](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/page_buffer.c#L9042)) 실제 -1123은 release 빌드에서만 회수기까지 온다. 그래서 시험은 오류를 주입한다.
- 오류를 돌려주기만 해도 블록은 완료되지 않는다. `vacuum_finished_block_vacuum (..., false)` 가 블록을 interrupted로 표시하고([vacuum.c:4087](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/query/vacuum.c#L4087)), master가 1초 뒤부터 다시 배정한다([8805](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/query/vacuum.c#L8805)). 블록은 vacuum data에 남으므로 crash 뒤 재시작에서도 다시 처리된다.

## Why deferring is safe (error classification)

회수기 `oos_delete_chain ()` 은 head부터 연결된 chunk를 모은 뒤([oos_collect_chain_prefix](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/oos_file.cpp#L3497)), tail부터 지운다. chunk마다 write latch로 stamp를 다시 확인하고 redo-only 레코드를 남긴 뒤 slot을 지운다([3673](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/oos_file.cpp#L3673)).

| 오류 | 생기는 곳 | 수정 후 처리 |
| --- | --- | --- |
| `ER_CSS_PTHREAD_COND_TIMEDOUT`, `ER_PB_ALL_BUFFERS_DIRTY` | page fix의 버퍼 프레임 할당 | 블록 재처리 |
| `ER_PAGE_LATCH_TIMEDOUT`, `ER_LK_PAGE_TIMEOUT`, `ER_LK_UNILATERALLY_ABORTED` | page latch 대기 시간 초과(`pgbuf_timed_sleep`) | 블록 재처리 |
| `ER_OUT_OF_VIRTUAL_MEMORY` | chain 수집 벡터, 알림 payload 복사 | 블록 재처리 |
| `ER_INTERRUPTED` | 종료 | 그대로(블록 재처리) |
| `ER_HEAP_OOS_CORRUPTED_RECORD`, `ER_HEAP_OOS_INVALID_ARGUMENT` | 수정 전 거부 | 그대로(보고하고 건너뜀) |
| 그 밖(`spage_delete` 실패, I/O 오류 등) | 삭제 로그 뒤일 수 있음, 지속될 수 있음 | 그대로 fail-stop |

- 재처리하는 오류는 모두 page fix나 private 복사에서만 생긴다. 삭제 레코드를 로그에 남긴 뒤 slot을 지우기 전 구간에서는 생기지 않는다. 그래서 실패한 실행은 "tail 쪽 일부가 지워지고 head부터 연결된 prefix가 남은" 상태만 남긴다. 다음 실행은 그 prefix를 끝까지 지운다(ADR-0008 decision 3). 독립 리뷰가 이 주장을 코드로 다시 확인했다(아래 "Independent review" F-OK-3).
- `spage_delete` 는 삭제 로그 뒤에 실패할 수 있으므로 fail-stop으로 남겼다.

## Change

- `oos_reclaim_notified_chains ()` 에 `defer_transient` 를 추가했다. 이 값이 참이면 위 표의 일시적 오류에서 새 오류 `ER_VACUUM_OOS_RECLAIM_DEFERRED`(-1423)를 설정하고 돌려준다. 나머지 오류는 이전처럼 멈춘다.
- `vacuum_oos_reclaim_notified_chains ()` 는 vacuum worker일 때만 `defer_transient` 를 켠다. 미룬 heap을 기억해, 같은 실행에서 그 heap의 다음 알림은 다시 기다리지 않고 다음 실행으로 넘긴다(CBRD-27933의 조회 실패와 같은 방식).
- `vacuum_process_log_block ()` 은 새 오류를 `ER_VACUUM_OOS_LOOKUP_DEFERRED` 와 같이 처리한다. 블록의 나머지를 처리하고, 블록은 완료로 표시하지 않는다. 첫 deferral 코드를 변수에 저장해 블록 끝에서 돌려준다. debug assert 세 곳이 새 코드를 허용한다.
- 커밋 postpone 경로(`oos_rv_reclaim_on_postpone ()`, REMOVE sysop 커밋과 SA eager 삭제)는 바꾸지 않았다. 아래 "Postpone path policy" 참고.
- 시험 장치: fault injection 1000000(`FI_TEST_OOS_RECLAIM_HEAD_FIX_TIMEOUT`, debug 전용)은 회수기의 head fix를 -1123으로 실패시킨다. 목록에 있는 동안 매번, 모든 호출자에서 실패한다. 단위 시험 hook `oos_test_fail_reclaim_after_chunk_deletes ()` 는 주입할 오류를 받는다.

## Reproduction

### Unit level (real vacuum worker, SERVER_MODE)

`ctest -R test_oos_real_vacuum_reclaim_fault`. 세 chunk짜리 값을 UPDATE하고, 회수기가 tail을 지운 다음 chunk fix에서 오류를 내게 한다. fail-stop hook이 서버 정지 대신 횟수를 센다.

| 실행 | 결과 |
| --- | --- |
| 수정 전 엔진 + 새 시험 | `stops 1, deferrals 0` — -1123이 fail-stop으로 감. 시험 실패 |
| 수정 후 | `stops 0, deferrals 1`, 세 chunk 모두 회수, 새 버전 chain 유지. 세 사례(-1123, page latch 시간 초과, 그 밖의 오류는 여전히 정지) 모두 통과 |

### Live server (debug `cub_server`, fault injection toggled at runtime)

스크립트 순서: 서버 시작 → `create table t (id int primary key, v varchar)`, 40000자 값 20행 insert(행마다 3 chunk, `Oos_num_recs` 60) → `set system parameters 'fault_injection_ids=1000000'` → `update t set v = repeat('b', 40000)` → 로그 블록을 닫도록 filler insert → 대기 → `fault_injection_ids=0` → 대기 → `show heap oos of t`. 반복 문자 값이 압축되지 않도록 `enable_string_compression=no` 로 실행했다(첫 시도는 압축 때문에 OOS를 쓰지 않아 무효였다).

수정 전:

```text
OOS [ERROR](oos_reclaim_fail_stop): OOS reclaim of committed intent failed (error -1123) for file 1|832 chain oid={vol=1,page=893,slot=0} stamp 415|15648; stopping so restart recovery reruns it
LOG FATAL ERROR: oos_reclaim: committed reclaim failed with error -1123
[16] oos_reclaim_notified_chains(...) at src/storage/oos_file.cpp:4401
[15] vacuum_oos_reclaim_notified_chains(...) at src/query/vacuum_oos.cpp:243
```

서버가 멈추고 cub_master가 다시 띄웠다. QA 보고의 스택과 같다.

수정 후(같은 스크립트, `52bf95f21e` 빌드):

```text
ERROR CODE = -1123 ... pthread_cond_timedwait() timed out.
ERROR CODE = -1423 ... Vacuum could not finish reclaiming the OOS chains that an UPDATE of heap file 1|704 dropped (OOS file 1|832, error -1123). The current log block is left for a later run, which reclaims the rest.
VACUUM ERROR (...): Processing log block 15 is interrupted!
```

| 시점 | `Oos_num_recs` | 서버 |
| --- | --- | --- |
| UPDATE 전 | 60 | 시작 PID 유지 |
| fault injection 켜진 동안(블록 5회 미룸) | 118 (첫 chain의 tail 쪽 2 chunk만 지워짐) | 유지 |
| fault injection 끈 뒤 | 60 (한 버전 20행 × 3 chunk), `count(*)` 20, 총 길이 800000 | 유지, `LOG FATAL ERROR` 없음 |

최종 커밋과 같은 소스(`ebdd0f0462`)로 다시 돌린 결과도 같다: 블록 5회 미룸, fault injection 중 118, 끈 뒤 60, `count(*)` 20, 총 길이 800000, `LOG FATAL ERROR` 없음, 서버 PID 유지. fault injection 없이 같은 스크립트를 돌린 대조 실행에서도 회수는 정상이었다.

### Test suites

- 최종 커밋 `ebdd0f0462` 빌드의 configured ctest 전체: 75개 중 74개 통과. 실패한 1개는 `test_oos_real_vacuum_latch_timeout_retry`(CBRD-27933의 `ImmediateFailureRerunsAtMostOncePerSecond`)의 60초 시간 초과다. 첫 수정 버전에서는 전체 75개가 통과했다.
- 이 시간 초과는 기존 문제다. `test_oos_real_vacuum_latch_timeout` 바로 뒤에 돌릴 때 부하가 높은 기계(load average 10–27)에서 생긴다. 수정하지 않은 기준 소스 `ca39c2c6a4` 로 같은 순서를 3번 돌리면 2번 시간 초과였다. 첫 수정 버전(`52bf95f21e`)은 2번 중 1번, 단독 실행은 3번 모두 16.3초에 통과했다. 멈춘 동안 시험 스레드는 시험 helper `flush_log ()` 의 `logpb_flush_pages ()` group commit 대기에 있었다. 이 사례는 vacuum_heap의 조회 deferral만 지나며, 이 변경은 그 경로를 바꾸지 않는다.
- 정책 경계를 고정하는 시험: `OosReclaimTest.TimedOutWaitInTheReclaimOfACommittedIntentStillFailStops`(postpone 경로는 -1123에도 정지, 남은 prefix 확인), `OosVacuumHeapSeamServer.NotifyConsumerOutsideAVacuumWorkerStillStopsOnATimedOutWait`(vacuum worker가 아니면 정지).
- `git diff --check` 와 GNU indent/astyle 형식 검사 통과. `cubrid-static-check`: 새 cppcheck, clang-tidy, 중복 코드 없음. `oos_reclaim_notified_chains` 의 CCN이 16→21로 늘었다(분기 두 개 추가). 오류 분류 함수를 따로 두어 늘어난 분기를 최소로 했다.

## Postpone path policy (DoD item 2)

- 결정(제안): 커밋 postpone 경로는 이 이슈에서 fail-stop을 유지한다. postpone은 미룰 "다음 실행"이 없다. 이 경로는 이미 page latch 대기를 무한으로 바꾸므로(`pgbuf_force_latch_wait`) 남는 일시적 오류는 버퍼 프레임 대기(-1123)와 메모리 부족이다.
- 남는 위험: 버퍼가 고갈된 동안 vacuum이 DELETE된 OOS 행을 REMOVE하면 같은 -1123 FATAL이 날 수 있다(독립 리뷰 F2).
- 대안: 같은 오류 분류로 `oos_delete ()` 를 그 자리에서 다시 시도한다. 분류가 같으므로 안전성 근거도 같다. 다만 vacuum은 heap page write latch를 쥔 채로, eager 경로는 사용자 커밋 안에서 최대 300초씩 다시 기다린다. 상한을 둘지, 상한 뒤 정지할지는 OOS-ADR-0008(fail-stop은 "first implementation"으로 승인)의 개정이 필요하다. 담당자 결정을 받아 후속 이슈로 다룬다.

## Spec conformance

- OOS-CONTEXT §4와 OOS-ADR-0008 decision 3은 "notification consumer는 `ER_INTERRUPTED` 에서만 블록을 미완료로 남긴다"고 적는다. 이 수정은 일시적 오류에도 블록을 남긴다. CBRD-27933의 조회 실패 deferral도 이미 이 문장과 다르다. 두 경우 모두 사양이 `ER_INTERRUPTED` 에 이미 인정한 성질(블록 재처리 + 회수기 수렴)에 기댄다.
- 제안 문구(사양 저장소 `cubrid-oos-context` 에 반영 필요, JIRA 미러 CBRD-28315 동기화 포함): "Vacuum's notification consumer follows the same rule, except that it leaves the log block unfinished, so vacuum processes it again, on a shutdown interruption (`ER_INTERRUPTED`), on a failed OOS file lookup (CBRD-27933), and on a timed-out page latch or free-buffer wait or a failed allocation in the reclaim (CBRD-28377). These errors arise only before a chunk delete is logged."

## Independent review

리뷰 대상은 첫 커밋 `52bf95f21e`. 별도 Herdr 탭의 리뷰어가 읽기 전용으로 검토했다. 차단 결함과 정확성 결함은 없었다.

| ID | 내용 | 처리 |
| --- | --- | --- |
| F1 | 사양 문구와 다름 | 위 "Spec conformance" 에 개정 문구 제안. 담당자 결정 필요 |
| F2 | REMOVE postpone 경로는 여전히 -1123에 FATAL | 위 "Postpone path policy". 담당자 결정 필요 |
| F3 | 시험 조건이 조건부 latch 통계로 거짓 통과 가능 | 각 chunk를 무조건 latch로 확인하도록 수정. postpone 시험에 남은 prefix 확인 추가 |
| F4 | 블록 끝에서 오류 스택을 다시 읽음 | 첫 deferral 코드를 변수에 저장 |
| F5 | 고갈은 전역인데 건너뛰기는 heap 단위 | 후속 고려(정확성 영향 없음) |
| F6 | 지속되는 "일시적" 오류는 1초 주기 재시도 | CBRD-28276의 back-off 결정에 포함 필요 |
| F7 | fault injection이 한 번만이 아니고 모든 호출자에 적용 | 헤더 주석에 명시 |
| F8, F9 | 시험 카운터 경쟁, hook 인자 안전성, 줄 길이, 헤더 의존 | atomic, release/acquire, 허용 코드 assert, 줄 정리, 오버로드로 include 제거 |
| S1 | 단발 hook을 커밋 전에 설정 | 커밋 뒤, 블록을 닫기 전에 설정 |
| P1 | 시험 hook 모드에서 비일시적 오류가 조회 실패로 표시됨 | 시험에 설명 주석 추가(운영에는 영향 없음) |

## Pre-existing findings

- 재실행이 이미 지워진 continuation slot을 확인할 때 `spage_get_record ()` 가 `ER_SP_UNKNOWN_SLOTID`(-46)를 ERROR로 기록한 뒤 `S_DOESNT_EXIST` 를 돌려준다([slotted_page.c:3817](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/slotted_page.c#L3817)). 회수기는 이를 정상 건너뛰기로 처리하지만, -46은 기본 `call_stack_dump_activation_list` 에 있어 오류 로그 mutex를 쥔 채 스택을 덤프한다. debug 서버에서 첫 덤프가 약 16초 걸려 그동안 로그를 쓰는 다른 스레드가 멈췄다(같은 스크립트를 fault injection 없이 돌리면 지연 없음). ADR-0008 재실행 경로 공통의 문제이며 이 수정이 만든 것은 아니다. slot 존재를 오류 없이 확인하도록 고치는 후속을 제안한다.
- `test_oos_real_vacuum_server` 의 일부 사례(`OosRealVacuumUpdateNotify.*`, `OosRealVacuumHeaderHeld.UpdateNotification*` 등)는 어떤 ctest 필터에도 등록되어 있지 않다.

## Limits

- release 빌드에서 실제 버퍼 고갈로 -1123을 재현하지 않았다. 모든 결과는 오류 주입으로 얻었다.
- HA 환경과 shell/medium 회귀는 돌리지 않았다(CI 미실행).
- 재시도 주기는 기존 interrupted 블록 정책(최소 1초)을 따른다. 실제 -1123은 매 시도에 최대 `page_latch_timeout_in_msecs`(기본 300초)를 기다린다.
