# CBRD-27237 수정 방식 deep dive (A/B/C)

| 항목 | 값 |
| --- | --- |
| 질문 | CBRD-27237을 A, B, C 중 어느 방식으로 고쳐야 하는가. 각 방식에 남는 손실 시나리오와 비용은 무엇인가. |
| 독자 | CBRD-27237 담당자. 결정은 담당자가 한다. 이 문서는 근거와 추천만 낸다. |
| 기준 source | CUBRID/cubrid `feature/oos-merge` `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`. 아래 `path:line`은 모두 이 commit 기준이다. |
| 로컬 probe | `dcbf09e4f` 위의 로컬 commit 3개. 원격에 올리지 않았다. 내용은 [probes/](probes/)의 patch 파일에 있다. |
| 빌드 | `debug_gcc` preset, `UNIT_TEST_OOS=ON`. release 빌드는 돌리지 않았다. |
| 작성일 | 2026-11-03 (Asia/Seoul) |
| 관련 | [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237), [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230), [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841) (#8347), [CBRD-27089](https://jira.cubrid.org/browse/CBRD-27089), work-tracker 705 |

근거 표시는 세 가지다. **[실행]** 은 이번에 돌려서 본 결과다. **[소스]** 는 위 commit의 code를 읽어 확인한 것이다. **[추론]** 은 code를 읽고 낸 판단이며 실행으로 확인하지 않았다.

결함 자체의 설명과 이전 재현은 [CBRD-27237 분석 문서](https://github.com/vimkim/my-cubrid-jira/blob/main/issues/CBRD-27237-oos-forward-walk-rollback-delete_dcbf09e_claude.md)에 있다. 이 문서에는 다시 적지 않는다. 결정 항목의 쉬운 요약은 [CBRD-27881 owner decisions 1절](../cbrd-27881/CBRD-27881-owner-decisions_dcbf09e_claude.md#1-cbrd-27237을-어떤-방식으로-고칠지)에 있다. 이 문서는 그 1절의 근거를 보강하고 몇 가지 판단을 고친다.

## 결론

**추천은 A다. 다만 사양 §3이 정한 발행 위치는 그대로 쓰면 안 된다.** 사양은 알림을 commit hook에서 `logtb_complete_mvcc` 앞에 남기라고 한다. 이 위치의 알림은 commit 레코드보다 먼저 디스크에 남을 수 있다. 그 사이에 서버가 죽으면 복구는 UPDATE를 되돌리지만 알림은 남는다 [소스]. vacuum은 그 알림으로 되살아난 행의 chain을 지울 것이다 [추론. 알림 consumer는 아직 없다. 같은 stream에 있는 loser의 레코드를 vacuum이 처리하는 것은 실행으로 확인했다]. 같은 손실이 좁은 구간에 남는다.

그래서 알림을 postpone 레코드에 실어 commit이 durable할 때만 실행되게 하는 A'를 추천한다. CUBRID는 vacuum dropped-file 알림을 이미 postpone으로 남긴다(`src/query/vacuum.c:6381`) [소스]. 다만 이 선례는 durability 쪽만 뒷받침한다. dropped-file 처리는 실행 시점의 `mvcc_next_id`를 목록에 적을 뿐 MVCC 로그 레코드를 append하지 않는다(`vacuum.c:6641-6644`) [소스]. 이미 끝난 MVCCID로 vacuum용 레코드를 append하는 일은 새로 만들어야 한다. savepoint rollback은 그 뒤의 postpone 범위를 abort할 sysop으로 넘긴다(`src/transaction/log_manager.c:5703-5708`) [소스]. commit의 postpone 실행은 중첩 top operation 범위를 건너뛴다(`log_get_next_nested_top`, `:8133`) [소스]. 그래서 savepoint rollback과 statement rollback의 postpone은 실행되지 않고, 부분 rollback 처리도 같이 풀린다 [추론].

결함의 범위도 넓혀 확인했다. 연결 끊김, deadlock 희생, server kill -9 뒤 복구, 두 번의 kill -9, statement rollback 뒤 COMMIT, savepoint rollback 뒤 COMMIT, relocated 행이 모두 vacuum 뒤 값을 잃었다 [실행]. 복구 뒤 vacuum이 되돌린 트랜잭션의 UPDATE 레코드를 처리하는 것도 server log로 확인했다 [실행].

C를 추천하지 않는 이유는 prototype 실행으로 확인했다. B는 만들지 않았다. B를 추천하지 않는 이유는 현재 code의 실행 결과와 B의 정의를 맞춰 본 판단이다.

- **B는 savepoint로 되돌린 뒤 COMMIT한 트랜잭션을 막지 못한다.** probe P1에서 현재 code는 원래 값을 잃었다. SQL에서도 unique 위반으로 실패한 UPDATE 문 뒤 COMMIT, `rollback work to savepoint` 뒤 COMMIT이 모두 값을 잃었다. 그 UPDATE 레코드의 트랜잭션은 COMMIT했으므로 B도 건너뛰지 않는다 [실행, B 판단은 추론]. 이 경로는 드물지 않다. server 쪽 UPDATE는 모두 topop 안에서 돌고, 실패하면 그 topop만 되돌린 뒤 트랜잭션이 계속된다(`src/query/query_executor.c:11237`, `:11836`) [소스].
- **단순 C는 T1 ROLLBACK 뒤 T2가 아직 COMMIT하지 않은 UPDATE를 한 경우 원래 값을 잃는다.** C를 prototype으로 만들어 돌렸다. 기존 regression, P1, P3는 통과했고 P2는 실패했다 [실행]. 안전한 C는 현재 행뿐 아니라 `prev_version_lsa`로 이어진 이전 버전도 모두 봐야 한다. 그러려면 사양, 로그 형식, vacuum 비용을 모두 바꿔야 한다 [추론].

release 전에 임시 조치가 꼭 필요하다면 B보다 단순 C가 낫다. 단순 C는 이번 probe 4건 중 3건을 막았고, B가 놓치는 부분 rollback도 막았다 [실행]. 다만 단순 C에도 조용한 손실이 남는다. P2(시나리오 8)에서 값을 잃었고 [실행], 오래된 snapshot의 읽기 실패(시나리오 9)도 남는다 [추론]. `REC_BIGONE` 처리와 latch를 놓은 뒤의 창은 시험하지 않았다. 그래서 추천은 임시 조치 없이 A'로 바로 가는 것이다. 임시 조치를 넣으면 vacuum 경로를 두 번 고치고 사양에서도 잠시 벗어난다.

## 시나리오별 결과

현재 code 칸은 `dcbf09e4f` 실행 결과다. 단순 C 칸은 prototype `28280aa19` 실행 결과다. 나머지 칸은 설계를 읽고 낸 판단이다.

| # | 시나리오 | 현재 code | B | 단순 C | A (사양 그대로) | A' (postpone) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | UPDATE 뒤 ROLLBACK | 손실 [실행] | 막음 [추론] | 막음 [실행] | 막음 [추론] | 막음 [추론] |
| 2 | savepoint로 되돌린 뒤 COMMIT (P1) | 손실 [실행] | 손실 [추론] | 막음 [실행] | 막음. 목록 trim이 필요하다 [추론] | 막음 [추론] |
| 3 | 실패한 UPDATE 문을 statement rollback한 뒤 COMMIT | 손실 [실행] | 손실 [추론] | 막음 [추론] | 막음. trim이 필요하다 [추론] | 막음 [추론] |
| 4 | relocated 행 UPDATE 뒤 ROLLBACK (P3, `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`) | 손실 [실행] | 막음 [추론] | 막음 [실행] | 막음 [추론] | 막음 [추론] |
| 5 | 연결 끊김으로 abort | 손실 [실행] | 막음 [추론] | 막음 [추론] | 막음 [추론] | 막음 [추론] |
| 6 | deadlock 희생자 abort | 손실 [실행] | 막음 [추론] | 막음 [추론] | 막음 [추론] | 막음 [추론] |
| 7 | 미커밋 UPDATE 중 kill -9, 복구 undo | 손실 [실행] | log scan이면 막음 [추론] | 막음 [추론] | 막음 [추론] | 막음 [추론] |
| 8 | T1 ROLLBACK 뒤 T2 미커밋 UPDATE, 그 뒤 T2 ROLLBACK (P2) | 손실 [실행] | 막음 [추론] | 손실 [실행] | 막음 [추론] | 막음 [추론] |
| 9 | T1 ROLLBACK 뒤 T2 COMMIT, T2 commit 전 snapshot이 옛 버전을 읽음 | 읽기 실패 [추론] | 막음 [추론] | 읽기 실패 [추론] | 막음 [추론] | 막음 [추론] |
| 10 | 알림이 commit 레코드보다 먼저 durable해진 뒤 crash | 해당 없음 | 해당 없음 | 해당 없음 | 손실 [추론] | 막음 [추론] |
| 11 | COMMIT한 UPDATE의 옛 chain 회수 (누수 확인) | 회수 [실행] | 회수 [추론] | 회수 [실행] | 회수 [추론] | 회수 [추론] |
| 12 | CBRD-27230 재사용을 넣은 뒤 COMMIT한 UPDATE | 해당 없음 | 손실 [추론] | 막음 [추론] | 막음 [추론] | 막음 [추론] |

12번은 재사용된 chain이 undo image와 새 행에 함께 남는 경우다. forward-walk는 COMMIT한 UPDATE에서도 그 chain을 지운다. B는 COMMIT한 트랜잭션을 건너뛰지 않으므로 막지 못한다 [추론].

## 질문별 근거

### 1. A의 commit 직전 장애 구간

**결론. 구간이 있다 [소스]. 사양대로 만든 A는 이 구간에서 같은 손실을 낸다 [추론].**

1. 알림의 위치는 고정된다. MVCC 레코드를 append하려면 `tdes->mvccinfo.id`가 유효해야 한다(`src/transaction/log_append.cpp:967`). `logtb_complete_mvcc`(`log_manager.c:5267`)가 이 값을 지우므로 알림은 그 앞에 와야 한다. 이 위치는 postpone 실행(`:5284`)과 commit 레코드 append(`:5312`)보다 앞이다 [소스].
2. 두 레코드를 함께 durable하게 만드는 장치가 없다. 알림과 commit 레코드는 prior list의 별개 node다. flush는 그 순간의 prior list를 모두 옮겨 쓴다(`src/transaction/log_page_buffer.c:3163-3185`, `:4024-4038`). 다른 트랜잭션의 commit, log flush daemon(`log_manager.c:10789`), data page를 쓰기 전 WAL flush(`log_page_buffer.c:4239`)가 두 레코드 사이에 끼어들 수 있다 [소스].
3. 복구는 그 트랜잭션을 loser로 본다. checkpoint에 `TRAN_ACTIVE`로 남았으면 `TRAN_UNACTIVE_UNILATERALLY_ABORTED`가 된다(`src/transaction/log_recovery.c:1956-1963`). checkpoint가 `TRAN_UNACTIVE_WILL_COMMIT`을 기록했다면 commit 레코드가 없어도 commit으로 끝낸다(`:4356`, `log_manager.c:5254-5260`의 주석). 그러나 사양의 알림은 `:5267` 앞에 오고 상태는 `:5269`에서야 `WILL_COMMIT`이 된다. 그래서 알림만 durable하고 상태는 `TRAN_ACTIVE`인 구간이 남는다. 알림 계열 레코드의 undo는 아무것도 하지 않는다(`log_recovery.c:280`) [소스].
4. vacuum은 loser의 MVCC 레코드를 거르지 않는다. redo가 loser의 레코드로도 `mvcc_op_log_lsa`를 갱신한다(`log_recovery.c:3966`). 잃어버린 block은 이 사슬을 따라 다시 만든다(`vacuum.c:5843-5880`). `vacuum_process_log_block`과 `vacuum_process_log_record`는 dropped file만 거른다(`vacuum.c:4243-4283`) [소스].
5. identity stamp로도 막을 수 없다. 복원된 행의 stub과 알림에 담긴 `(head OID, stamp)`가 같다. `oos_delete`는 stamp가 같으면 지운다(`src/storage/oos_file.cpp:3490-3498`) [소스, 알림 consumer는 아직 없으므로 consumer 동작은 추론].

runtime에서는 이 구간이 열리지 않는다. commit하는 트랜잭션은 commit 레코드를 쓸 때까지 자기 MVCCID를 oldest visible 아래로 붙잡는다(`src/transaction/mvcc_table.cpp:490-505`). 이 주석은 바로 이 위험을 적고 있다. 위험은 restart 뒤에만 남는다 [소스].

**같은 구간을 가진 기존 code가 있다.** LOB 외부 파일 삭제 알림 `RVES_NOTIFY_VACUUM`은 같은 commit 위치(`tx_lob_locator_clear`, `src/transaction/transaction_transient.cpp:444-446`)에서 append된다. vacuum은 조건 없이 `es_delete_file`을 부른다(`vacuum.c:3742-3756`). 이 동작은 2014년 `4bbe6fd6c`(CUBRIDSUS-14695)부터 develop에 있다. 2019년 `773153460a`는 이 code를 지금 위치로 옮겼다. 같은 crash 구간에서 되살아난 행이 지워진 LOB 파일을 가리킬 수 있다 [소스, 재현하지 않음]. CBRD-27230 설계 문서는 이 선례를 근거로 들었지만, 선례가 같은 결함을 공유한다.

**닫는 방법.** 위 source 분석을 바탕으로 추천 순서대로 적는다.

| 방법 | 내용 | 비용과 남는 일 |
| --- | --- | --- |
| A'. postpone에 실어 나른다 (추천) | UPDATE 시점에 버린 chain 목록을 `LOG_POSTPONE`으로 남긴다. commit은 `LOG_COMMIT_WITH_POSTPONE`을 쓰고 postpone을 실행한다. 그 실행이 vacuum용 MVCC 알림을 append한다. `LOG_COMMIT_WITH_POSTPONE`이 durable하지 않으면 복구는 postpone을 실행하지 않는다. durable하면 복구가 postpone을 다시 실행한다. 중복 실행은 identity 검사 덕분에 no-op이다 | MVCCID를 명시적으로 받는 append 경로가 새로 필요하다. 지금 API는 `tdes`의 MVCCID만 읽는다(`log_append.cpp:958-981`). 아래 MVCCID 불변식을 지켜야 한다 |
| 취소 목록을 영속 구조로 둔다 | 복구 undo가 알림을 취소 목록에 등록하고 vacuum이 건너뛴다. dropped file 목록과 같은 꼴이다 | 새 영속 구조와 정리 수명 주기가 필요하다. 등록도 로그로 남겨야 두 번째 crash를 견딘다 |
| consumer가 현재 행을 다시 읽는다 | 알림에 row OID를 넣고 vacuum이 확인한다 | C와 같은 반례(8번 시나리오)가 남는다 |
| commit 레코드 뒤에 append한다 | | MVCCID가 이미 없다. 손실 대신 누수가 된다. 쓸 수 없다 |

**A'의 설계 의무 [소스 + 추론].** `prior_update_header_mvcc_info`는 block의 oldest visible MVCCID가 레코드의 MVCCID보다 크지 않다고 assert한다(`log_append.cpp:1347-1356`). vacuum의 debug 검사도 같은 조건을 본다(`vacuum.c:3577-3584`). runtime의 postpone 실행 시점에는 위 `mvcc_table.cpp:490-505` 보호가 이 조건을 지킨다 [추론]. 복구가 postpone을 다시 실행할 때는 restart 뒤라 옛 MVCCID가 이 조건을 어길 수 있다 [추론]. 이때는 옛 버전을 읽을 snapshot이 하나도 없다. 그래서 복구 중 재실행은 알림을 남기지 않고 chain을 바로 지워도 된다 [추론]. 다만 복구는 postpone 재실행(`log_recovery_finish_all_postpone`, `log_recovery.c:4082`, redo 안)을 loser undo(`:894`)보다 먼저 한다 [소스]. 바로 지운 뒤 빈 page를 회수한다면 사양 §4의 LSA reclaim gate를 따라야 한다. 이 선택은 구현 때 정한다.

**sysop commit에서 실행되는 postpone [소스 + 추론].** `log_sysop_commit`은 그 sysop의 postpone을 그 자리에서 실행한다(`log_manager.c:3985`). instant-lock 모드의 click counter UPDATE(`qexec_execute_selupd_list`)는 sub-MVCCID를 받아 sysop 안에서 실제 MVCC heap UPDATE를 하고 `log_sysop_commit`으로 끝낸다(`query_executor.c:15617`, `:15633`, `:15675`, `:15692`) [소스]. A'에서는 이 UPDATE의 알림이 트랜잭션 commit 전에 남는다. 이 sysop commit은 영구적이므로 맞는 동작이다. 이때 vacuum gate를 지키는 것은 `:15692`까지 활성인 sub-MVCCID다 [추론]. 복구는 이 경우를 `LOG_COMMIT_WITH_POSTPONE`이 아니라 `LOG_SYSOP_START_POSTPONE`으로 처리한다 [추론].

### 2. A를 CBRD-27230 재사용과 떼어 구현할 수 있는가

**결론. 그렇다 [소스].** 지금 MVCC UPDATE 경로는 모두 OOS 값을 새 chain에 쓴다. 옛 stub을 새 행으로 복사하는 경로는 없다.

| 경로 | 결과 |
| --- | --- |
| attr_info 경로 (`locator_attribute_info_force`, `src/transaction/locator_sr.c:7772`, `heap_attrinfo_prepare_record`, `src/storage/heap_file.c:13585`) | `heap_attrinfo_set_uninitialized`(`:12933`)가 지정하지 않은 컬럼도 값으로 읽는다. `heap_attrinfo_determine_disk_layout`(`:13137`)이 전체를 다시 배치하고 새 chain을 쓴다 |
| client copy-area 레코드 (`locator_update_force`) | `locator_finalize_oos_record`(`src/transaction/locator_sr.c:4924`)가 값을 다시 읽어 새 chain으로 만든다 |
| 복제 적용 (`xlocator_repl_force`) | replica가 자기 chain을 넣고 stub을 고친다(`locator_sr.c:14423`) |
| 파티션 이동 | INSERT와 DELETE다. UPDATE 로그가 없다 |
| in-place 갱신 (ALTER, compactdb, catalog) | MVCC가 아니다(`heap_file.c:170-174`). eager 경로를 탄다 |
| `heap_update_bigone` | 옛 레코드가 BIGONE이라 OOS를 가질 수 없다(`heap_file.c:14228-14237`) |

그래서 버린 chain은 지금은 옛 레코드의 stub 전부다. 그래도 A는 `old - new`로 계산하는 것이 좋다 [추론]. non-MVCC eager 경로도 이미 두 이미지에 같이 있는 head를 남긴다(`src/storage/heap_oos.cpp:908-914`). 그러면 CBRD-27230 재사용이 들어와도 A를 다시 고치지 않는다.

목록을 만들 지점은 세 곳이다 [소스].

- `heap_update_home`. 옛 이미지는 `context->home_recdes`다(`heap_file.c:25159`). undo는 `:25169`에서 남긴다.
- `heap_update_relocation`. 옛 stub은 `forward_recdes`(`:24709`)에 있다. `home_recdes`는 8 byte forwarding OID다. `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`은 `:24887-24896`, `update_old_forward`는 `:24930`에서 남긴다.
- `heap_update_bigone`. 목록이 늘 비어 있다.

복제는 재사용이 없으면 바꿀 것이 없다. replica는 자기 commit에서 자기 알림을 남긴다 [추론].

### 3. 부분 rollback

**결론. 지금 code에서 결함이 난다 [실행].** probe P1(`ProbeP1SavepointRollbackThenCommitKeepsOriginalOos`, patch 0002의 `test_oos_real_vacuum_server.cpp:1024`)의 순서는 다음과 같다.

1. 원래 값 A를 가진 행과 진행 확인용 witness 행을 COMMIT한다.
2. `xtran_server_savepoint`를 남기고 실제 MVCC heap UPDATE로 A를 B로 바꾼다.
3. `xtran_server_partial_abort`로 savepoint까지 되돌린다. 행은 다시 A의 head OID(`1|706|0`)를 가리킨다.
4. COMMIT한다. A는 정상으로 읽힌다.
5. witness를 DELETE하고 COMMIT한 뒤, witness chain이 실제로 회수될 때까지 기다린다.
6. A를 읽는다. `-2`로 실패했다(`:1066`).

gdb batch trace는 이 삭제가 `RVHF_UPDATE_NOTIFY_VACUUM` 분기에서 `vacuum_forward_walk_oos_delete_atomic`을 거쳐 일어남을 보였다. 그 트랜잭션은 COMMIT했다(MVCCID 7). B는 이 레코드를 건너뛰지 않는다 [실행, B 판단은 추론].

부분 rollback이 흔한 경로라는 근거 [소스]:

- server 쪽 UPDATE는 statement atomicity를 위해 늘 topop을 연다(`query_executor.c:11237`). 오류로 끝나면 `LOG_RESULT_TOPOP_ABORT`로 그 topop만 되돌린다(`:11836`). 여러 행을 바꾸는 UPDATE의 뒤 행이 실패하면, 앞 행이 이미 쓴 heap 레코드를 이 abort가 되돌린다. 행 하나의 unique 위반은 heap UPDATE보다 앞선 index 단계에서 나므로 해당하지 않는다(`locator_sr.c:6114`, `:6127`, `:6185`).
- client 쪽 여러 행 UPDATE는 `tran_system_savepoint`를 남기고, 실패하면 `tran_abort_upto_system_savepoint`로 되돌린다(`src/query/execute_statement.c:8805-8809`, `:8910`, `:8938`, `:9715-9733`).
- 어느 쪽이든 트랜잭션은 계속되고 사용자는 COMMIT할 수 있다.

**A에서 목록을 둘 곳.** 사양 그대로의 A라면 트랜잭션마다 버린 chain 목록을 들고 있다가, 부분 rollback에서 savepoint 뒤 항목을 빼야 한다. 기존 선례는 LOB locator 목록이다. 항목마다 savepoint LSA를 붙이고 부분 abort에서 그 뒤 상태를 지운다(`transaction_transient.cpp:199`, `:270`, `:374-455`) [소스]. A의 목록도 `LOG_TDES`에 LSA를 붙여 두고 `log_sysop_abort`(`log_manager.c:4159-4160`)에서 자르면 된다. 이 함수는 `log_abort_partial`과 topop abort가 함께 지나는 곳이다 [추론].

A'는 이 목록이 따로 필요 없다. postpone 레코드는 그 자체로 savepoint를 따른다. `log_abort_partial`은 savepoint 뒤에 시작한 postpone 범위를 abort할 sysop으로 넘긴다(`log_manager.c:5703-5708`). commit의 `log_do_postpone`은 중첩 top operation 범위를 건너뛴다(`log_get_next_nested_top`, `:8133`) [소스]. commit은 보통 이 range 경로가 아니라 postpone cache로 실행한다(`log_manager.c:8278`). cache의 `do_postpone`은 시작 위치 뒤의 항목을 모두 실행하고 건너뛰지 않는다(`log_postpone_cache.cpp`). cache 경로가 맞는 것은 `log_rollback`이 끝에서 cache 전체를 비우기 때문이다(`log_manager.c:8114`) [소스]. 그래서 버려진 statement의 postpone은 실행되지 않는다 [추론]. 구현 뒤에는 P1을 두 번 돌려야 한다. 한 번은 cache 경로이고, 한 번은 cache 크기 한도(`log_postpone_cache.hpp:54`, `:77`)를 넘겨 `log_do_postpone` 경로를 타게 한다.

### 4. B의 실현 가능성

**결론. 만들 수는 있지만 부분 rollback 때문에 충분하지 않다.**

- MVCC table은 MVCCID별 COMMIT과 ROLLBACK 이력을 남기지 않는다. 활성 집합과, 마지막으로 끝난 한 건의 종류만 갖는다(`mvcc_table.cpp:465-538`, `:485`). restart 뒤에는 옛 MVCCID가 모두 비활성으로 보인다(`log_recovery.c:2724`, `:3155`) [소스].
- heap vacuum은 commit 여부를 알 필요가 없다. rollback이 레코드를 물리적으로 되돌리고, vacuum은 현재 레코드의 MVCC header로 판정한다(`vacuum.c:1805`). "rollbacked and reused" 분기(`:1855`)는 사라졌거나 재사용된 slot을 건너뛸 뿐이다 [소스].
- 그래서 B는 새 정보원이 필요하다. 하나는 UPDATE 레코드부터 그 트랜잭션의 `LOG_COMMIT` 또는 `LOG_ABORT`까지 log를 앞으로 읽는 방법이다. 레코드 header에는 trid별 앞 방향 포인터가 없다(`src/transaction/log_record.hpp:150-157`). 그래서 비용이 트랜잭션 길이에 비례하고 상한이 없다. 복구가 loser에게 `LOG_ABORT`를 남기므로 판정 자체는 된다(`log_recovery.c:4634`) [소스, 비용은 추론]. 다른 하나는 abort한 MVCCID 집합을 영속 구조로 두는 방법이다. 둘 다 사양 §3을 바꿔야 한다.
- 시나리오 2, 3, 12는 B로 막을 수 없다. 앞 절의 P1이 실행 근거다.

### 5. C의 반례와 비용

**결론. 단순 C는 반례가 실제로 일어난다 [실행]. 안전한 C는 크고, 실행으로 확인하지 않았다.**

prototype `28280aa19`(patch 0003, `src/query/vacuum_oos.cpp` +94/-1, `vacuum.c` +7/-2, `vacuum_oos.hpp` +1/-1)는 다음과 같다.

- forward-walk가 로그 레코드의 slot에 지금 있는 레코드를 읽는다. `REC_RELOCATION`이면 `REC_NEWHOME`을 따라간다. 그 레코드가 아직 가리키는 head OID의 chain은 지우지 않는다.
- heap page는 read latch로 하나씩 잡고, 다음 fix와 `log_sysop_start` 전에 놓는다. heap latch와 OOS latch를 함께 잡지 않는다. deadlock, hang, assert는 보지 못했다 [실행].

| case | 현재 code | 단순 C |
| --- | --- | --- |
| 기존 10개 (drain, snapshot gate, live row, 멱등 등) | OK | OK |
| `RolledBackUpdateKeepsCommittedOosAfterVacuum` | FAIL -2 | OK |
| P1 savepoint 뒤 COMMIT | FAIL -2 | OK |
| P2 T1 ROLLBACK 뒤 T2 미커밋 UPDATE | FAIL -2 | FAIL -2 |
| P3 relocated 행 | FAIL -2 | OK |

P2(`ProbeP2ConcurrentActiveUpdateThenRollbackKeepsOriginalOos`, `:1078`)의 순서는 다음과 같다.

1. 원래 값 A를 가진 행과 witness 행을 COMMIT한다.
2. 다른 tran index에서 reader snapshot을 연다.
3. T1이 A를 B로 UPDATE하고 ROLLBACK한다. 행은 다시 A를 가리킨다.
4. witness를 DELETE하고 COMMIT한 뒤 block을 닫는다.
5. T2(다른 tran index)가 행을 C로 UPDATE하고 COMMIT하지 않는다. 현재 레코드는 C(`1|707|0`)만 가리킨다.
6. reader를 놓고 witness 회수를 기다린다. T1의 block(5)은 T2(block 7)가 활성인 동안 회수됐다.
7. 이 시점에 A는 이미 읽히지 않았다. T2를 ROLLBACK하면 행은 A를 가리키지만 A를 읽으면 `-2`다(`:1147`).

reader snapshot은 T2의 UPDATE가 자리를 잡기 전에 T1의 block이 회수되지 않게 막는다. 이것이 없으면 C가 우연히 통과할 수 있다. gdb log는 단순 C가 P2에서 `undo_refs=1 kept=0`을 남긴 뒤 `1|706|0`을 지웠음을 보였다 [실행].

**안전한 C의 조건 [추론].** 지우려는 chain을 현재 레코드와, 현재 레코드부터 처리 중인 레코드 다음 버전까지 `prev_version_lsa`로 이어진 모든 undo image가 가리키지 않을 때만 지운다. 비교는 `(head OID, stamp)`로 한다. 비용은 다음과 같다.

- 레코드마다 heap page fix가 필요하다. relocated 행이면 forward page도 fix한다.
- 버전 사슬을 따라 log를 읽어야 한다.
- `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`과 `update_old_forward`는 forward slot만 남기고 home OID를 남기지 않는다(`heap_file.c:24895`, `:24930`) [소스]. COMMIT 뒤 그 slot은 다른 레코드가 쓸 수 있다. CBRD-27230 재사용이 들어오면 forward slot만 보는 확인은 틀린다. 그래서 로그 형식을 바꿔야 한다 [추론].
- 사양 §3과 §4는 "undo image는 삭제 근거가 아니다"라고 정한다(`OOS-CONTEXT.md` §3, §4 Recovery 2, 3). C는 이 규칙을 바꿔야 한다.

latch 순서 위험은 낮다. vacuum의 기존 순서가 heap home page 다음 OOS page다(`vacuum.c:2561-2572`). forward-walk 시점의 worker는 heap latch를 잡고 있지 않다. `vacuum_process_log_block`의 record loop에는 page fix가 없고, 첫 heap 작업은 loop 뒤 `vacuum_heap`(`vacuum.c:3785`)이다 [소스].

### 6. 확인하지 않았던 abort 경로

**결론. 시도한 abort 경로는 모두 vacuum 뒤 COMMIT된 OOS 값을 잃었다 [실행].** SQL로 서버 모드에서 돌렸다. 방법은 실험 기록에 있다.

| 경로 | 실행 횟수 | abort 근거 | vacuum 뒤 결과 |
| --- | --- | --- | --- |
| S1. 미커밋 UPDATE 중인 csql client를 SIGKILL | 2 | `cubrid tranlist`가 kill 전 `1(ACTIVE) ... csql`, kill 뒤 1초 안에 트랜잭션 없음 | -1389 |
| S2. deadlock 희생자 | 유효 4 (설계 오류 1회 제외) | 희생자에게 "unilaterally aborted by the system"(-72). server log에 직전 -1021 | 희생자 행은 4회 모두 -1389. 생존자가 COMMIT한 변형(2회)에서 생존자 행은 30000. 생존자가 ROLLBACK한 변형(2회)에서는 생존자 행도 -1389로, 명시적 ROLLBACK과 같은 결과다 |
| S3. 미커밋 UPDATE 중 `cub_server` kill -9, 재기동 | 3 | 복구 log "UNDO Phase is started ... transactions to undo: 3" | -1389 |
| S4. S3 뒤 vacuum 전에 한 번 더 kill -9 | 2 | 두 번의 재기동 모두 정상 | -1389. 손실이 두 번째 재기동 뒤에도 남는다 |
| S5a. 여러 행 UPDATE가 unique 위반(-670)으로 실패한 뒤 COMMIT | 2 | 실패 직후 같은 session에서 두 행 모두 원래 값 | 두 행 모두 -1389 |
| S5b. `savepoint sp1; update ...; rollback work to savepoint sp1; commit;` | 2 | 다른 session에서 vacuum 전 30000 | -1389 |

S5는 B를 실행으로 반박한다. 두 경우 모두 트랜잭션은 COMMIT했다. B는 COMMIT한 트랜잭션의 forward-walk를 그대로 둔다 [실행, B 판단은 추론].

**S3에서 vacuum이 복구로 되돌린 트랜잭션의 레코드를 처리했다 [실행].** S3 첫 실행의 server error log에서 "Server status is UP"(2524행) 뒤에 vacuum worker가 `process log entry at log_lsa 1069|8624`, `collected oid 1|3649|1, in file 1|3648, based on 1069|8624`를 남겼다(3692-3695행). `1069|8624`는 kill 전 미커밋 UPDATE의 레코드다. 이것은 1절 4단계의 전제(vacuum이 loser의 MVCC 레코드를 거르지 않는다)를 실행으로 뒷받침한다. 사양대로 만든 A의 알림도 같은 stream에 들어가므로 같은 처리를 받는다 [추론].

vacuum 전 기준값은 일부 실행에만 있다. S3의 둘째, 셋째 실행과 S5의 둘째 실행에서는 harness의 "vacuum 전" 읽기보다 vacuum이 먼저 해당 block을 처리했다. 그래서 그 실행들의 "vacuum 전 30000"은 관찰하지 못했다. 이 기준값은 S3 첫 실행과 S5 첫 실행에 있다. S4에서는 master가 첫 kill 뒤 server를 다시 띄우지 않아 직접 띄웠다. 원인은 모른다.

DF-30(재기동 복구 중 `log_rv_analysis_sysop_end` assert)은 재기동 8회에서 나오지 않았다. 이 8회에는 vacuum이 바쁜 중에 kill한 추가 실행 1회가 들어 있다. kill 시점이 다양하지 않으므로 위험이 없다는 증거는 아니다.

### 7. 관련 결함과의 상호작용

- **CBRD-26950.** identity 검사는 이 결함을 구분하지 못한다. 되살아난 stub과 undo image가 같은 stamp를 갖는다. A'에서도 vacuum 재시도와 postpone 재실행의 멱등성을 이 검사가 맡는다 [소스].
- **CBRD-26786.** A'의 consumer는 `vacuum_forward_walk_oos_delete_atomic`(`vacuum_oos.cpp:153`)을 다시 쓰면 된다. 이 함수는 sysop commit 뒤 `vacuum_oos_reclaim_empty_pages`로 빈 page를 넘긴다(`:194`). `oos_delete` 자체가 growth-gate sweep을 켠다(`oos_file.cpp:3535-3538`). B와 C는 이 helper의 호출 여부만 바꾼다 [소스].
- **CBRD-27781.** TLA+ 모델(`cubrid-verify-vacuum-slot-undo` skill)의 `covers`는 `oos_delete`, `oos_delete_chain`, `vacuum_heap_oos_delete_within_sysop`, vacuum heap 함수, `spage_*`를 든다. forward-walk의 sysop wrapper `vacuum_forward_walk_oos_delete_atomic`은 들지 않는다 [소스]. 이 wrapper는 한 sysop 안에서 `oos_delete`를 여러 번 부르고, 호출마다 OOS page를 fix했다가 놓는다. 하나가 실패하면 sysop을 abort한다(`vacuum_oos.cpp:171-201`) [소스]. 빈 page 회수는 sysop commit 뒤에만 한다(`:190-194`). 그래서 abort undo가 그 사이 다른 트랜잭션이 쓴 slot과 부딪히는 CBRD-27781 꼴의 위험이 있을 수 있다 [추론]. A'의 consumer가 이 wrapper를 다시 쓰면 모델의 `covers`에 wrapper를 넣고 검사를 다시 돌려야 한다.
- **CBRD-27089.** 2026-09-09 댓글은 이 결함의 수정을 최종 검증의 선행 조건으로 정했다. 수정의 acceptance test로 기존 regression과 P1, P2, P3를 함께 켜는 것을 제안한다.

### 8. 방식별 변경 범위

**A' (추천).**

| 항목 | 위치 | 상태 |
| --- | --- | --- |
| 예약된 `RVOOS_NOTIFY_VACUUM`을 실제로 쓴다. A'는 postpone용 index가 하나 더 필요하다 | `src/transaction/recovery.h:206-209`, `:298-312`, `recovery.c:905-908`, `src/transaction/mvcc.h:268-275` | 위치는 소스. A'의 index 수는 추론 |
| 알림 undo의 no-op 분기 | `log_manager.c:7565`, `log_recovery.c:280` | 추론 |
| UPDATE 시점의 postpone 기록 | `heap_update_home`, `heap_update_relocation`. `heap_recdes_get_oos_refs` 재사용 | 추론 |
| postpone 실행 handler와 MVCCID를 명시하는 append | `log_append.cpp:958-1010`. heap VFID를 넘기거나 `RVES_NOTIFY_VACUUM`처럼 예외를 둔다 | 필요성은 소스 |
| vacuum consumer 분기와 unpack whitelist | `vacuum.c:3742` 근처, `:4276-4281` | 위치는 소스 |
| forward-walk 삭제 | `vacuum.c:3608-3624`, `:3757-3770`, `vacuum_oos.cpp:248-369`, `vacuum_oos.hpp:57`, `unit_tests/oos/test_oos_vacuum_server.cpp`의 직접 호출 | 소스 |
| 유지하고 재사용 | `vacuum_forward_walk_oos_delete_atomic`, `vacuum_oos_reclaim_empty_pages`, `vacuum_oos_vfid_lookup` | 소스 |
| 로그 page 회전 대비 사본 | 알림 ref도 log page 안에 있으므로 consumer가 page fix 전에 사본을 만들어야 한다(`vacuum_oos.cpp:296-304` 사고 기록) | 위험은 소스, 결론은 추론 |
| 사양 | `OOS-CONTEXT.md` §3 step 3의 발행 위치, §4 Recovery 3, §4 Vacuum + OOS | 소스 |
| 선택. 142 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`을 일반 레코드로 돌림 | `recovery.h:216-217`, `recovery.c:918-924`, `heap_file.c:24887-24896` | 소스 |

**B, 단순 C, 안전한 C.**

| 항목 | B | 단순 C | 안전한 C |
| --- | --- | --- | --- |
| 판정 지점 | `vacuum.c:3619`, `:3764` 앞 | `vacuum_forward_walk_reclaim_oos`(`vacuum_oos.cpp:266`) 안 | 단순 C와 같다 |
| 새 함수 | 트랜잭션 끝 레코드를 찾는 log scan(선례 `cdc_find_user`, `log_manager.c:14013-14084`), 또는 abort MVCCID 영속 구조 | 현재 레코드의 head 목록을 읽는 함수. prototype의 `vacuum_forward_walk_current_heads` | 단순 C에 `prev_version_lsa` 사슬을 따라 undo image를 읽는 함수 |
| 함수 signature | forward-walk에 trid나 MVCCID 전달 | forward-walk에 row OID 전달(prototype은 기본값 인자) | 같다 |
| 로그 형식 | 바꾸지 않는다(log scan). 영속 구조면 새 레코드 | 바꾸지 않는다 | `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`, `update_old_forward`에 home OID 추가(`heap_file.c:24895`, `:24930`) |
| 사양 | §3 소유권 규칙, §4 Recovery 2와 3, §4 Vacuum + OOS | 같다 | 같다 |
| 테스트 | `test_oos_vacuum_server.cpp`의 직접 호출 갱신 | heap row fixture 필요(prototype은 기본값으로 피함) | 같다 |
| 남는 손실 | 시나리오 2, 3, 12 | 시나리오 8, 9 | 확인하지 않음 |
| 크기 | 중간. scan 비용은 트랜잭션 길이에 비례 | 3 files, +102/-4 (prototype) | 큼 |

모든 칸은 소스와 추론이다. 단순 C의 크기만 prototype 실측이다.

## 담당자가 정할 것

work-tracker 705의 항목 순서를 따른다. 이전 owner decisions 1절과 다른 곳은 굵게 표시했다.

1. **수정 방식.** 추천은 A다. **단, 사양 §3 step 3의 발행 위치를 commit hook에서 postpone으로 바꾼 A'로 한다.** 사양의 소유권 규칙과 "삭제 근거는 commit한 연산뿐"이라는 원칙은 그대로다. 바뀌는 것은 알림이 언제 durable해지는가다.
2. **1-b. #8347 보류.** 추천은 1번과 별개로 보류를 푸는 것이다(이전과 같다). #8347이 먼저 들어가면 A'는 새 index를 뒤에 추가한다. 기능이 출시되지 않았으므로 index 번호가 바뀌어도 호환성 비용은 test DB 재생성뿐이다(`recovery.h:197-201`) [소스].
3. **A를 고르면 함께 정할 것.**
   - 알림 부분만 CBRD-27237에서 먼저 구현할지. 추천은 먼저 구현하는 것이다. 지금 MVCC UPDATE 경로는 모두 새 chain을 쓴다 [소스]. 버린 chain은 `old - new`로 계산해 CBRD-27230 재사용과도 맞춘다.
   - commit 직전 장애 구간. **구간은 실제로 있다 [소스].** 추천은 A'로 닫는 것이다. 복구 중 postpone 재실행의 MVCCID 처리는 구현 때 정한다.
4. **새 항목. 임시 조치.** release 일정 때문에 임시 조치가 필요하면 **B가 아니라 단순 C**를 넣는다. 추천은 임시 조치 없이 A'로 가는 것이다.
5. **새 항목. `RVES_NOTIFY_VACUUM`의 같은 구간.** develop에 있는 기존 code다. 별도 이슈로 등록할지 정한다. 재현하지 않았다.

## 실험 기록

**환경.** worktree `/home/vimkim/gh/cb/CBRD-27237-oos-rollback-vacuum-delete`. `debug_gcc` 빌드와 설치 뒤 `cub-workenv init --no-db`를 했다. ctest의 환경 변수는 configure 시점에 고정되므로 init 뒤 다시 configure했다.

**commit.** 모두 로컬이다.

| commit | 브랜치 | 내용 | patch |
| --- | --- | --- | --- |
| `60a202960` | `CBRD-27237-oos-rollback-vacuum-delete` | `338b7a1dd`를 cherry-pick. 보존된 regression에서 `DISABLED_`를 뗐다 | [0001](probes/0001-enable-rolled-back-update-regression.patch) |
| `164db2081` | 같은 브랜치 | probe P1, P2, P3 | [0002](probes/0002-probe-savepoint-concurrent-relocated.patch) |
| `28280aa19` | `CBRD-27237-probe-c-guard` | 단순 C prototype. 병합 대상이 아니다 | [0003](probes/0003-probe-option-c-current-record-guard.patch) |

**실행 방법.** test binary의 `main()`이 `break_on_failure`를 켜므로 첫 실패가 뒤 case를 모두 멈춘다. 그래서 case마다 새 DB에서 따로 실행했다. fixture 준비와 정리는 ctest로, binary는 `GTEST_FILTER`로 직접 돌렸다. 단순 C는 설치하지 않고 build tree의 `libcubrid.so`를 `LD_LIBRARY_PATH`로 앞세웠다. 어느 library가 돌았는지는 guard 함수의 gdb breakpoint hit로 확인했다. log의 `ldd` 줄은 두 경우 모두 같은 build 경로라 이것만으로는 구분하지 못한다.

```sh
# 기준선 (current code). 60a202960에서
direnv exec . sh -c '"${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-build-coordinator.sh" installation-use 300 -- \
  ctest --test-dir "$CUBRID_BUILD_DIR" -R "^test_oos_real_vacuum_server$" --output-on-failure'
# 결과: RolledBackUpdateKeepsCommittedOosAfterVacuum 실패 (:901, -2), 나머지 10개 OK
```

**SQL 재현.** 설치한 `debug_gcc`(`11.5.0.2782-60a2029`)로 별도 DB `cbrd27237db`를 만들어 돌렸다. 실행마다 새 table `t(id int primary key, k int, big varchar(200000))`를 만들고 압축되지 않는 30,000자 무작위 문자열을 넣었다. 실행마다 세 행을 둔다.

- 시험 행. 시나리오대로 abort한다.
- 대조 행. `update ... set k = k + 1` 뒤 COMMIT한다. vacuum 뒤에도 30000이어야 한다. vacuum이 돌았고 COMMIT한 UPDATE를 건드리지 않았다는 증거다.
- 보정 행. 명시적 ROLLBACK을 한다. vacuum 뒤 -1389여야 한다. harness가 결함을 볼 수 있다는 증거다.

vacuum은 filler table에 3,000자 행 500개를 COMMIT한 뒤 30초 기다려 돌렸다. `cubrid vacuumdb`는 `--dump -C`만 썼다. vacuum 처리 기록은 DB section에 `er_log_vacuum=724`를 잠시 넣어 남겼고, 끝난 뒤 `cubrid.conf`를 되돌렸다. 대조 행은 모든 실행에서 30000, 보정 행은 모든 실행에서 -1389였다. S2 첫 실행은 생존자가 희생자 행을 다시 UPDATE해 결과를 덮었으므로 버렸다. 이후 deadlock 순환은 OOS가 없는 별도 table에서 만들었다. harness와 실행별 log는 로컬 scratch에 있고 commit하지 않았다.

**한계.**

- release 빌드는 돌리지 않았다.
- B와 안전한 C, A'는 만들지 않았다. 표의 해당 칸은 추론이다.
- 단순 C의 `REC_BIGONE` 처리와 latch를 놓은 뒤의 창은 시험하지 않았다.
- 1절의 crash 구간은 소스 분석이다. 알림이 없으므로 그 구간을 실행으로 만들 수 없다. 7번 시나리오의 실행은 "vacuum이 복구로 되돌린 트랜잭션의 레코드를 처리한다"는 전제를 확인한다.
- HA와 replica는 실행하지 않았다. A'의 2PC와 replica 적용 경로도 source로 따로 확인하지 않았다.
- P3는 첫 실행이 probe 자체의 문제로 -1387에서 멈췄다. VOT offset이 정렬되지 않아 OOS flag bit를 건드렸다. padding을 8의 배수로 고친 뒤 다시 돌린 결과를 실었다.
- 1절의 crash 구간은 기존 `RVES_NOTIFY_VACUUM`으로 실행해 볼 수 있다. commit 레코드 append 직전에 gdb로 멈추고 log를 flush한 뒤 kill -9하면 된다. 이번에는 하지 않았다.

## 열린 질문

- A'에서 복구 중 postpone을 다시 실행할 때 알림을 남길지, chain을 바로 지울지.
- A'의 postpone이 statement rollback에서 실제로 버려지는지. 구현 뒤 P1과 SQL 시나리오 3으로 확인한다.
- 버린 chain이 많은 큰 트랜잭션에서 postpone 레코드를 어떤 단위로 나눌지.
- `RVES_NOTIFY_VACUUM`의 같은 구간을 재현할 수 있는지.
