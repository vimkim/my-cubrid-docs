# CBRD-27933 vacuum의 OOS 파일 조회 실패 재현과 원인 분석

- 분석일은 2026-11-04 (Asia/Seoul)이다. 선택지 B prototype은 2026-11-05에 추가했다.
- 대상 이슈는 [CBRD-27933](https://jira.cubrid.org/browse/CBRD-27933)이다. 요구사항 출처는 [PR #8350 리뷰 댓글](https://github.com/CUBRID/cubrid/pull/8350#discussion_r4452180248)이다. 작업 추적은 Work 781이다.
- 소스 기준은 `CUBRID/cubrid` 의 `1ef6ed6125eb6028c06b0e05282dc0041bde3f48` (PR #8350 head)이다. 엔진 소스는 수정하지 않았다. 재현 테스트는 로컬 브랜치 `CBRD-27933-vacuum-oos-vfid-lookup-error` 의 커밋 `ec3edd1ab` 와 `a8065e5fe` 에만 있고, 원격에는 게시하지 않았다.
- 빌드는 `debug_gcc` (Debug, `-O0`)와 `release_gcc` (RelWithDebInfo, `-O2 -DNDEBUG`)를 사용했다.
- 같은 날 `origin/feature/oos-merge` 는 `f67f2f692a7ad9f9efada2178759ca713e596b9d` 였고 PR head와의 merge-base는 `dcbf09e4f` 다. 이 보고서의 런타임 결과는 PR head에서만 얻었다.

## 질문과 결론

질문은 두 가지다. vacuum이 heap 헤더에서 OOS 파일 식별자(VFID)를 읽지 못하면, 삭제 행의 heap 슬롯만 지우고 OOS 값을 남기는가. 남긴다면, 리뷰어가 제안한 대로 오류를 반환하는 것만으로 일시 오류, 지속 오류, 셧다운을 모두 처리할 수 있는가. 독자는 CBRD-27933 수리를 설계할 엔진 개발자다.

1. release 빌드에서 누수를 재현했다. vacuum 워커의 헤더 대기가 page latch timeout을 넘기면 `vacuum_oos_find_vfid_for_heap_record` 가 오류를 지운다. vacuum은 삭제 행의 슬롯을 제거하고 OOS 값은 지우지 않는다. 로그 블록은 `complete` 로 끝나므로 그 OOS 값을 회수할 경로가 남지 않는다. `REC_HOME`, `REC_RELOCATION`, 셧다운 중 실패의 세 조건 모두 같았다.
2. 리뷰어가 제시한 트리거는 실제로 발생한다. vacuum 워커는 infinite wait인 `TRAN_ACTIVE` system tdes로 헤더를 기다리고, `pgbuf_timed_sleep` 은 timeout 오류를 반환한다.
3. debug 빌드는 helper에 도달하기 전에 `pgbuf_timed_sleep` 의 `assert (0)` 에서 중단한다. debug에서 관측되는 증상은 누수가 아니라 서버 중단이다.
4. helper가 오류를 반환하게만 바꾼 prototype은 일시 오류와 셧다운을 해결했다. 일시 오류 뒤에는 OOS 값이 회수되었다. 셧다운 중 실패는 블록을 `interrupted` 로 남겼다. 지속 오류에서는 워커가 같은 페이지를 latch timeout 주기로 끝없이 재시도했다.
5. 지속 오류에서는 B가 낫다. B는 오류를 반환한 뒤 블록을 `interrupted` 로 넘겨 나중에 다시 실행한다. vacuum 워커가 하나일 때 A는 60초 동안 다른 heap의 블록을 처리하지 못했고, B는 14.6초에 처리했다. 일시 오류와 셧다운에서는 B와 A의 결과가 같았다.
6. 수리는 오류 반환 한 줄로 끝나지 않는다. debug assertion 세 곳, 대기 없이 바로 실패하는 오류의 재시도 간격, 회귀 테스트를 돌릴 빌드를 함께 정해야 한다.

## 실패 경로

이 절은 `1ef6ed612` 소스에서 확인한 내용이다. 각 단계 아래의 런타임 관측은 [관측 결과](#관측-결과)에 있다.

**조회 계약.** [`heap_oos_find_vfid`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/storage/heap_file.c#L13234-L13350) 는 헤더를 읽었고 OOS 파일이 없으면 `true` 와 NULL VFID를 반환한다. 헤더 페이지를 fix하지 못하거나 헤더 레코드를 읽지 못하면 `false` 를 반환한다. `false` 는 항상 실제 오류다.

**대기 전 페이지 해제.** PR #8350의 [`vacuum_heap_prepare_oos_vfid`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2302-L2352) 는 먼저 conditional latch로 헤더를 읽는다. 헤더가 바쁘면 heap 페이지를 놓고 helper를 호출한다. helper는 unconditional latch로 헤더를 기다린다.

**오류 삭제.** [helper](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum_oos.cpp#L389-L425) 는 `false` 를 받으면 로그를 남기고 `assert_release (false)` 를 거친 뒤 `er_clear ()` 를 호출한다. 그리고 VFID를 비우고 `NO_ERROR` 를 반환한다. 그래서 `vacuum_heap_prepare_oos_vfid` 의 `error_code != NO_ERROR` 검사는 실행될 수 없다.

**재조회 없음.** 대기 뒤 [`oos_header_waited`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2016-L2018) 가 설정된다. 레코드를 다시 준비할 때 [`REC_HOME`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2266-L2277) 과 [`REC_RELOCATION`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2144-L2156) 모두 VFID를 다시 조회하지 않는다. 흡수된 실패가 최종 답이 된다.

**슬롯만 제거.** [`vacuum_heap_record`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2565-L2567) 의 `has_oos` 는 VFID가 있어야 참이다. `REC_HOME` 은 bulk 경로로 슬롯을 비우고 [OOS 삭제](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2681-L2705)를 건너뛴다. `REC_RELOCATION` 은 home과 new home 슬롯을 모두 비우고 [OOS 삭제](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2629-L2639)를 건너뛴다. 페이지 처리는 `NO_ERROR` 로 끝나고 블록은 완료된다.

**timeout이 나는 이유.** [`pgbuf_timed_sleep`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/storage/page_buffer.c#L7321-L7392) 은 대기 스레드의 트랜잭션이 활성이면 timeout을 오류로 바꾼다. 활성이 아니면 다시 기다린다. 대기 모드가 `LK_INFINITE_WAIT` 이면 `ER_PAGE_LATCH_TIMEDOUT` (-836)을 설정하고, debug에서는 `FIXME` 주석이 붙은 `assert (0)` 으로 중단한다. release에서는 이어서 `ER_LK_UNILATERALLY_ABORTED` (-72)를 설정한다. 런타임에서 debug의 assert와 release의 -72가 모두 나왔다. 따라서 vacuum 워커의 대기는 infinite wait이고 트랜잭션은 활성이다.

**오류를 반환하면 일어나는 일.** release [`vacuum_heap`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L1593-L1621) 은 셧다운이 아닌 페이지 오류를 지우고 같은 페이지를 다시 처리한다. 셧다운 중이거나 debug이면 오류를 반환한다. [`vacuum_process_log_block`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L3854-L3862) 은 그 오류로 [`vacuum_finished_block_vacuum (..., false)`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L4008-L4053) 를 호출하고, 블록은 `interrupted` 로 남아 나중에 다시 실행된다. `ER_OUT_OF_VIRTUAL_MEMORY` 는 release에서도 페이지 재시도 없이 이 경로로 간다. 오류 종류 하나를 미완료 블록으로 넘기는 선례다.

**debug의 제약.** debug에서는 vacuum 워커의 오류가 셧다운 중의 `ER_INTERRUPTED` 가 아니면 [`vacuum_check_shutdown_interruption`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L8270-L8277) 이 assert로 중단한다. `vacuum_finished_block_vacuum` 도 미완료 블록에 대해 셧다운이나 메모리 부족만 허용한다.

**셧다운은 latch 대기를 깨우지 않는다.** [`vacuum_stop_workers`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L1418-L1444) 는 워커 풀을 멈춘다. 워커 컨텍스트에는 [`shutdown = true`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/thread/thread_entry_task.cpp#L118-L121) 만 설정된다. 헤더를 기다리는 워커는 latch를 받거나 timeout이 날 때까지 계속 기다린다. `vacuum_heap_page` 안에는 별도의 셧다운 검사가 없다.

## 재현 장치

재현기는 `unit_tests/oos/test_oos_real_vacuum_server.cpp` 의 `OosRealVacuumHeaderHeld` fixture다. 세 case가 있다.

| Case | 조건 |
| --- | --- |
| `HomeRowOosReclaimedAfterHeaderLookupFailure` | OOS 값을 가진 `REC_HOME` 행을 삭제하고 헤더 조회를 실패시킨다 |
| `RelocatedRowOosReclaimedAfterHeaderLookupFailure` | 같은 조건을 `REC_RELOCATION` 행에 적용한다 |
| `ShutdownDuringHeaderLookupFailureLeavesHomeRowToVacuum` | 헤더를 쥔 채 `vacuum_stop_workers` 를 호출해 셧다운과 조회 실패를 겹친다 |

각 case의 동작은 다음과 같다.

1. 새 heap 페이지에 OOS 값을 가진 행과 OOS 없는 고정 행을 넣는다. heap 헤더 페이지에도 행이 저장되므로, 헤더 페이지에 넣으면 vacuum이 조회 전에 home 페이지 fix에서 막힌다. 고정 행은 페이지가 비어 제거되는 경로를 막는다.
2. 행을 MVCC 삭제하고 커밋한다. 테스트 스레드가 헤더 페이지를 WRITE로 잡는다. OOS insert와 로그 flush로 삭제의 로그 블록을 닫는다. 이 방법은 기존 TC-R11의 방법이다.
3. vacuum이 헤더에 대기하면, 테스트는 latch timeout의 세 배 동안 헤더를 쥔다. `OOS_TEST_HEADER_HOLD_MSECS` 로 이 시간을 바꿀 수 있다. 셧다운 case는 `vacuum_stop_workers` 가 반환할 때까지 쥔다.
4. 헤더를 쥔 상태의 슬롯 종류와 OOS 읽기 가능 여부를 기록한다. 헤더를 놓고 최대 30초 동안 OOS 회수를 기다린다.
5. 통과 조건은 두 가지다. 슬롯이 제거되었는데 OOS 값이 남은 상태가 없어야 하고, 헤더를 놓은 뒤 둘 다 사라져야 한다. 셧다운 case는 워커가 멈춘 시점에 슬롯이 제거되었는데 OOS 값이 남아 있으면 실패한다.

`REC_RELOCATION` case는 헤더 페이지를 먼저 채운다. 첫 시도에서는 relocated 행의 forward record가 헤더 페이지 1|641에 놓였다. 그러자 vacuum은 OOS 조회가 아니라 forward 페이지 fix에서 timeout 됐다 (`Failed to fix page 1|641`, `vacuum.c:2106`). 오류는 `vacuum_heap` 까지 전파되었고, release가 페이지를 다시 처리해 OOS 값을 회수했다. 이 관측은 헤더 대기 timeout을 오류로 전파하는 기존 경로가 release에서 누수 없이 재시도한다는 사례이기도 하다. 현재 case는 forward record가 헤더 페이지에 있지 않음을 assert한다.

짧은 latch timeout은 환경 변수로 준다. 서버는 parameter를 읽을 때마다 [`CUBRID_<PARAMETER>`](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/base/system_parameter.c#L7475-L7501) 를 적용한다. 부팅 전에 `prm_set_integer_value` 로 바꾼 값은 [`boot_restart_server` 의 재로딩](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/transaction/boot_sr.c#L2030)으로 사라졌다. 이 시도에서는 vacuum이 20초 동안 헤더를 기다렸다. CTest 항목 `test_oos_real_vacuum_latch_timeout` 은 `CUBRID_PAGE_LATCH_TIMEOUT_IN_MSECS=2000` 으로 이 fixture만 실행한다. 기본 timeout(300초)에서는 case를 건너뛴다.

[`run-repro.sh`](run-repro.sh) 는 이 CTest 항목과 같은 일을 case마다 별도 프로세스로 실행한다. 테스트 binary가 첫 실패에서 SIGTRAP으로 멈추기 때문이다. 이 스크립트는 fixture DB를 scratch registry에 만들고, 서버 로그에서 그 case의 부팅 이후 부분만 보존한다. 그리고 `CUBRID_ER_LOG_VACUUM=4099` (error, warning, job)로 블록의 `complete` 또는 `interrupted` 판정을 기록한다. release 실행에서는 host workenv가 debug preset으로 초기화되어 있었다. 그래서 스크립트가 같은 worktree의 `CUBRID_TMP`, port, JDK를 빌렸다. 두 preset을 동시에 실행하지 않았다.

## 관측 결과

모든 실행은 1회씩이다. 결과는 통과와 실패로 갈리는 이진 관측이고, 같은 조건을 반복한 실행(E2의 첫 실행과 최종 실행)은 같은 결과를 냈다.

| 실행 | 빌드와 엔진 | Case | 헤더를 쥔 동안 | 헤더를 놓은 뒤 | 삭제 블록 판정 |
| --- | --- | --- | --- | --- | --- |
| E1 | debug, 수정 없음 | 세 case 모두 | vacuum이 대기한 뒤 프로세스 중단 | 없음 | 없음 |
| E2 | release, 수정 없음 | `REC_HOME` | 슬롯 2 (`REC_HOME`), OOS 있음 | 슬롯 6 (`REC_MARKDELETED`), 30초 동안 OOS 남음 | `complete` |
| E2 | release, 수정 없음 | `REC_RELOCATION` | 슬롯 4 (`REC_RELOCATION`), OOS 있음 | 슬롯 6, 30초 동안 OOS 남음 | `complete` |
| E2 | release, 수정 없음 | 셧다운 | 워커 정지 시 슬롯 6, OOS 있음 | 슬롯 6, OOS 남음 | `complete` |
| E3 | release, prototype | `REC_HOME` | 슬롯 2, OOS 있음 | 슬롯 6, OOS 회수 | 기록 안 함 |
| E3 | release, prototype | `REC_RELOCATION` | 슬롯 4, OOS 있음 | 슬롯 6, OOS 회수 | 기록 안 함 |
| E4 | release, prototype, 60초 유지 | `REC_HOME` | 60초 끝에도 vacuum 대기 중, 슬롯 2, OOS 있음 | 슬롯 6, OOS 회수 | `complete` |
| E5 | release, prototype | 셧다운 | 워커가 17.4초 뒤 정지, 슬롯 2, OOS 있음 | 슬롯 2, OOS 남음 | `interrupted` |

E1의 중단 지점은 `page_buffer.c:7365` 의 `Assertion '0' failed` 다. gdb로 잡은 중단 스레드는 `vacuum` 이다. 그 스택은 `vacuum_heap_page`, `vacuum_heap_prepare_record` (`REC_HOME`, `vacuum.c:2268`), `vacuum_heap_prepare_oos_vfid`, `vacuum_oos_find_vfid_for_heap_record`, `heap_oos_find_vfid` 를 지나 헤더 1|641의 unconditional READ fix에서 `pgbuf_timed_sleep` 으로 끝났다. [`gdb-debug-abort.sh`](gdb-debug-abort.sh) 가 이 실행을 다시 만든다. debug에서 기존 `test_oos_real_vacuum_server` CTest 항목은 통과했다 (43.9초). 이 항목에서 새 case는 기본 timeout 때문에 건너뛴다.

E2의 서버 로그는 case마다 latch timeout 1회와 helper의 로그 1회를 담고 있다. helper 로그는 다음과 같다.

```text
VACUUM ERROR (...): OOS flag set but no OOS VFID for hfid 1|640 slotid=1 rectype=2 rec_len=76 ... - skipping OOS cleanup (bounded leak)
```

이 문구는 OOS 플래그가 잘못 설정된 경우를 가정한다. 실제로는 헤더 latch timeout에서 나왔다. 그 가정의 경우인 OOS 파일이 없는 경우는 이제 `heap_oos_find_vfid` 의 `true` 와 NULL VFID로 성공 경로를 지나간다. 이 경로는 로그 없이 OOS 정리를 건너뛴다 (소스 확인, 런타임 미확인).

E2와 E3에서 헤더를 쥔 6초 동안 슬롯이 그대로였던 이유는 release의 오류 로깅이다. 기본 `call_stack_dump_activation_list` 가 이 오류 코드들에 대해 심볼을 해석한 call stack을 기록한다. E2 `REC_HOME` 에서는 `ER_PAGE_LATCH_TIMEDOUT` 기록이 22:02:21.480에 시작해 다음 오류가 22:02:57.372에 나왔다. 그래서 helper의 오류 삭제와 슬롯 제거가 헤더를 놓은 뒤에 일어났다. 결과는 같다. 조회는 이미 실패했고, 헤더가 풀린 뒤에도 vacuum은 다시 조회하지 않았다.

E3과 E4에서는 prototype의 오류가 `Could not prepare vacuum for object 1|643|1` 과 `Vacuum heap page 1|643, error_code=-72` 로 기록되었다. 이 두 줄은 수정 없는 엔진에서는 나오지 않았다. 이 차이로 prototype 코드가 실행되었음을 확인했다.

E4에서 latch timeout은 57.2초 동안 22회 기록되었다. 간격의 중앙값은 2.00초이고 최댓값은 17.13초였다. 중앙값은 latch timeout과 같다. 워커는 실패 직후 다시 헤더에 줄을 섰다. 최댓값은 첫 call stack 기록이다. 이 실행의 서버 로그는 54,529줄, 약 3.9 MB였다. 그 대부분은 테스트가 켠 `CUBRID_ER_LOG_VACUUM=4099` 의 job 로그다. 기본값 1에서도 남는 오류 기록만 따로 세면 증가 속도는 1.7 KiB/s였다 (P-A-persistent60에서 측정).

## 분석 질문에 대한 답

**일시 오류.** 현재 코드에서는 한 번의 timeout이 영구 누수가 된다 (E2). 오류를 반환하면 release의 페이지 재시도가 헤더가 풀린 뒤 OOS 값을 회수한다 (E3). `REC_HOME` 과 `REC_RELOCATION` 모두 같다.

**지속 오류.** 현재 코드에서는 실패한 레코드마다 OOS 값이 새고, vacuum은 계속 진행한다. 오류를 반환하고 페이지를 재시도하면(A) 그 페이지를 맡은 워커가 다음 페이지로 가지 못하고 블록은 끝나지 않는다 (E4). 오류를 반환하고 블록을 넘기면(B) 워커가 다른 블록을 처리한다 ([선택지 B prototype 결과](#선택지-b-prototype-결과)). 재시도 주기는 latch timeout이 정한다. 기본값 300초에서는 워커 하나가 5분마다 오류 하나와 call stack 하나를 남기며 그 페이지에 묶인다 (추론, 측정 안 함). 헤더 페이지 읽기 오류처럼 대기 없이 바로 실패하는 오류는 이 주기의 제한을 받지 않고 바로 반복될 수 있다 (추론, 실행 안 함).

**셧다운.** 셧다운은 헤더를 기다리는 워커를 깨우지 않는다. 대기는 timeout으로 끝난다 (E5에서 17.4초, 그중 대부분은 call stack 기록). 현재 코드에서는 그 실패가 누수가 되고 블록은 `complete` 로 끝나므로, 재기동해도 다시 처리하지 않는다 (E2 셧다운). 오류를 반환하면 블록이 `interrupted` 로 남는다 (E5). 재기동 뒤 그 블록을 다시 실행해 회수하는 단계는 실행하지 않았다. 근거는 `interrupted` 판정과 `was_interrupted` 재실행 경로의 소스다.

**debug와 release.** debug는 latch timeout에서 `pgbuf_timed_sleep` 의 `FIXME` assert로 중단하므로 helper에 도달하지 않는다. 이 assert를 지워도, 오류를 반환하는 수리는 `vacuum_check_shutdown_interruption` 과 `vacuum_finished_block_vacuum` 의 assert에 걸린다 (소스 확인). release는 위 표와 같다.

**PR #8350의 latch 순환.** prototype은 conditional 조회, 페이지 해제, 대기의 순서를 바꾸지 않는다. 오류 경로는 home 페이지를 다시 fix하기 전에 반환하므로, 헤더를 기다리는 동안 heap 페이지를 쥐지 않는다 (소스 확인). TC-R11을 prototype에서 실행하지는 않았다.

## 구현 선택지

세 선택지 모두 helper가 실패를 오류로 반환하고, `vacuum_heap_prepare_oos_vfid` 의 대기한 답을 최종으로 쓰는 처리를 성공한 조회에만 적용하는 것으로 시작한다. 차이는 vacuum이 그 오류를 어디서 다시 시도하느냐다.

| 선택지 | 일시 오류 | 지속 오류 | 셧다운 | 근거 |
| --- | --- | --- | --- | --- |
| A. 현재 release의 페이지 재시도에 맡긴다 | 회수 | 워커가 그 페이지에 묶이고 오류 로그가 계속 쌓인다 | 블록 `interrupted` | E3, E4, E5에서 실행 |
| B. 이 오류를 `ER_OUT_OF_VIRTUAL_MEMORY` 처럼 미완료 블록으로 넘긴다 | 블록 재실행으로 회수 | 워커는 다른 블록으로 가고, 같은 블록이 반복 실행된다 | 블록 `interrupted` | P 실행에서 확인 |
| C. helper 안에서 정해진 횟수만큼 다시 기다린다 | 대부분 그 자리에서 회수 | 해결하지 못하므로 A나 B가 필요하다 | A나 B를 따른다 | 실행 안 함 |

B를 택한다. 근거는 다음 절의 prototype 실행이다. A는 워커 하나를 무기한 그 페이지에 묶고, 워커가 하나뿐이면 vacuum 전체가 멈춘다. B는 그 비용을 블록 재실행 간격으로 옮긴다. B의 남은 질문은 대기 없이 바로 실패하는 오류에서 같은 블록을 얼마나 자주 다시 실행할지와, 끝까지 실패할 때 무엇을 진단으로 남길지다.

선택지와 별개로 두 가지를 정해야 한다.

- debug 정책. 헤더 조회 실패를 vacuum 워커에서 예상 가능한 오류로 볼지 정한다. 예상 가능한 오류로 보면 `vacuum_check_shutdown_interruption` 과 `vacuum_finished_block_vacuum` 이 메모리 부족처럼 이 오류를 받아들여야 한다.
- 회귀 테스트의 빌드. 이번 재현기는 release에서만 판정이 난다. debug CI에서 쓰려면 `pgbuf_timed_sleep` 의 `FIXME` assert를 지우거나 (모든 infinite wait timeout에 영향), debug에서 이 case를 건너뛰거나, `heap_oos_find_vfid` 에 debug 전용 장애 주입점을 둔다.

## 선택지 B prototype 결과

B prototype은 A의 helper 변경 위에 다음을 더했다 ([`retry-block-later-prototype.patch`](retry-block-later-prototype.patch), `a8065e5fe` 에 적용). `VACUUM_WORKER` 에 `retry_block_later` 를 두고, `vacuum_heap_prepare_oos_vfid` 가 helper 실패에서만 이 값을 켠다. `vacuum_heap` 은 job마다 값을 끄고, 값이 켜진 오류를 `ER_OUT_OF_VIRTUAL_MEMORY` 처럼 반환한다. 그래서 forward 페이지 timeout 같은 다른 -72 오류는 지금처럼 페이지를 재시도한다. debug assertion은 고치지 않았다. throwaway prototype이며 수리 코드가 아니다.

A와 B를 가르는 case를 추가했다 (`UnrelatedHeapVacuumedWhileHeaderLookupKeepsFailing`, 커밋 `a8065e5fe`). 한 트랜잭션이 OOS 행(블록 44)과 두 번째 heap의 OOS 없는 행(블록 45)을 삭제한다. 테스트는 첫 heap의 헤더를 60초 동안 쥐고, 두 번째 heap의 행이 언제 vacuum되는지 기록한다. 헤더를 놓은 뒤에는 OOS 회수를 요구한다. 이 커밋은 헤더를 쥐는 helper가 vacuum 워커 수와 페이지 vacuum 상태도 출력하게 했다.

모든 실행은 release, latch timeout 2초, 1회씩이다. `i` 는 `interrupted`, `c` 는 `complete` 판정이다.

| 실행 | 변형 | Case | 관측 | 판정 |
| --- | --- | --- | --- | --- |
| P-base-unrelated-w1 | 수정 없음, 워커 1 | 다른 heap | 다른 행은 14.9초에 처리, OOS 회수 안 됨, 블록 44 `c` | 누수 |
| P-A-unrelated-w1 | A, 워커 1 | 다른 heap | 60초 동안 다른 행을 처리하지 못함, 헤더를 놓은 뒤 처리, 블록 45 `c` | 정체 |
| P-B-unrelated-w1 | B, 워커 1 | 다른 heap | 다른 행은 14.6초에 처리, 블록 44 `i` 23회 뒤 `c`, OOS 회수 | 통과 |
| P-B-unrelated-w10 | B, 워커 10 | 다른 heap | 다른 행은 즉시 처리, 판정 순서는 위와 같음 | 통과 |
| P-A-transient-shutdown | A | 일시 오류 두 case, 셧다운 | 일시 오류는 OOS 회수, 셧다운은 블록 `i` 와 슬롯 유지 | 통과 |
| P-B-transient-shutdown | B | 같은 세 case | 일시 오류는 블록 `i` 뒤 `c` 와 OOS 회수, 셧다운은 블록 `i` 와 슬롯 유지 | 통과 |
| P-A-persistent60 | A | `REC_HOME`, 60초 | timeout 23회, 간격 중앙값 2.00초, 블록 42 `c` 1회, OOS 회수 | 통과 |
| P-B-persistent60 | B | `REC_HOME`, 60초 | timeout 23회, 간격 중앙값 2.00초, 블록 42 `i` 23회 뒤 `c`, OOS 회수 | 통과 |

판정 기준은 실행 전에 정했다. 워커가 하나이고 조회가 계속 실패할 때, 다른 heap의 다음 블록이 B에서만 처리되어야 한다. 그리고 일시 오류와 셧다운에서 B가 A와 같아야 한다. 결과는 기준을 모두 만족했다. B는 블록 44를 23번 다시 실행하는 사이에 블록 45를 처리했으므로 재실행이 다른 블록을 굶기지 않았다. B의 모든 실행에서 OOS 값이 회수되었고, 알려진 테스트 probe 잡음 밖의 assertion 알림은 없었다.

B는 페이지 vacuum 상태를 ONCE로 남겼다. A는 NONE으로 끝났다 (측정). 이것은 `was_interrupted` 재실행이 원래 따르는 경로다. `vacuum_heap_page` 의 주석은 재실행에서 ONCE를 NONE으로 바꾸는 것이 안전하지 않다고 설명한다. NONE은 페이지를 해제해도 된다는 뜻이기 때문이다 (소스 확인). 셧다운과 메모리 부족 뒤의 재실행도 같은 결과를 낸다. ONCE는 남은 vacuum을 과대 표시하는 안전한 쪽이다. 그 비용은 그 실행에서 페이지 제거를 고려하지 않는 것이다 (소스 추론).

재시도 비용은 A와 B가 비슷했다. 둘 다 latch timeout마다 한 번 재시도했고, job 로그를 뺀 오류 기록은 1.7 KiB/s로 늘었다. B는 재시도마다 "Processing log block N is interrupted!" 한 줄을 더 남겨, 분당 약 4.7 KB가 더 늘었다 (측정).

실행하지 않은 조건은 다음과 같다. 헤더 읽기 I/O 오류처럼 대기 없이 바로 실패하는 오류에서는, B의 master가 같은 블록을 master 주기(`vacuum_master_interval_in_msecs`)마다 다시 실행할 수 있다 (소스 추론). 수리에는 이 경우의 재실행 간격이나 진단 기준이 필요하다. 재기동 뒤의 `interrupted` 블록 재실행, TC-R11, debug 빌드, 기본 latch timeout, 반복 실행도 하지 않았다.

## 실행하지 못한 조건과 한계

- 헤더 페이지 읽기 오류(I/O)는 주입하지 않았다. latch timeout만 실행했다. 두 실패는 같은 `pgbuf_fix` 의 NULL 반환으로 helper에 들어간다 (소스 확인).
- `interrupted` 블록을 재기동 뒤 다시 실행해 회수하는 단계는 실행하지 않았다. fixture는 한 프로세스에서 한 번만 부팅한다.
- 기본 latch timeout(300초)에서의 재시도 주기는 측정하지 않았다.
- 각 조건은 1회씩 실행했다. E2는 첫 실행과 최종 실행이 같았다.
- E3, E4, E5는 중간 테스트 revision으로 실행했다. 판정 논리는 커밋된 revision과 같고, case 이름과 주석이 달랐다. E3에는 삭제 블록 출력과 셧다운 옵션이 아직 없었다.
- `origin/feature/oos-merge` 의 현재 tip에서는 실행하지 않았다.
- `REC_BIGONE` 은 OOS를 가질 수 없으므로 범위 밖이다.

## 다시 실행하는 방법

CUBRID worktree 루트에서 재현 커밋을 checkout하고 preset을 고른 뒤 빌드와 설치를 한다.

```sh
just preset release_gcc
direnv exec . just configure
direnv exec . just build-and-install
```

초기화된 workenv가 없으면 [`run-repro.sh`](run-repro.sh) 를 사용한다. 이 스크립트는 `OUT` 아래 `<label>/summary.txt` 에 위 표의 값을 남긴다.

```sh
bash run-repro.sh E2-release-baseline
EXTRA_ENV="CUBRID_ER_LOG_VACUUM=4099 OOS_TEST_HEADER_HOLD_MSECS=60000" \
  bash run-repro.sh E4-persistent HomeRowOosReclaimedAfterHeaderLookupFailure
```

workenv가 초기화되어 `CUBRID_DATABASES` 가 configure 시점에 잡혀 있으면 CTest로도 실행할 수 있다.

```sh
direnv exec . ctest --test-dir "$CUBRID_BUILD_DIR" -R '^test_oos_real_vacuum_latch_timeout$' --output-on-failure
```

prototype A는 [`return-lookup-error-prototype.patch`](return-lookup-error-prototype.patch), B는 [`retry-block-later-prototype.patch`](retry-block-later-prototype.patch) 를 `git apply -p1` 로 적용한 뒤 다시 빌드하고 설치한다. B 패치는 A의 변경을 포함한다. 워커 수를 바꾸려면 `EXTRA_ENV` 에 `CUBRID_VACUUM_WORKER_COUNT=1` 을 넣는다. `EXTRA_ENV` 를 주면 `CUBRID_ER_LOG_VACUUM=4099` 도 직접 넣어야 블록 판정이 기록된다. 테스트 binary는 `LD_LIBRARY_PATH` 의 설치본 `libcubrid` 를 먼저 읽으므로 설치를 빠뜨리면 이전 엔진이 실행된다.

이미 구성된 build tree에서 `just configure` 를 다시 실행하면 CMake가 compiler 변경으로 cache를 지운다. 이때 `UNIT_TEST_OOS` 가 사라져 OOS 테스트가 빌드에서 빠진다. 이 문제를 만나면 build tree의 `CMakeCache.txt` 를 지우고 configure를 다시 실행한다.
