내부 테스트 중 이 이슈의 "SA assert, release SIGSEGV" 증상을 최신 develop에서 가장 작은 형태로 다시 확인해 공유드립니다. 수정 뒤 SA 모드(csql -S) 검증 케이스로 써 주시면 좋겠습니다.

**재현 (develop `e64a04a79`, 새 DB, 기본 설정)**

``` sql
-- csql -S -u dba <db>
create or replace function cf () return int as
begin
  commit;
  return 1;
end;

select cf () from db_root;
```

| 빌드 / 모드 | 결과 |
|---|---|
| debug, SA (`csql -S`) | csql 종료: `page_buffer.c:3253: void pgbuf_unfix_all(THREAD_ENTRY*): Assertion 'false' failed.` |
| release, SA (`csql -S`) | csql 종료: Segmentation fault (exit 139) |
| debug, CS (`csql -C`) | 정상 결과 1행. 서버 로그에 `query 3 is in progress, including an SP that contains COMMIT or ROLLBACK` 만 남음 |

- 함수 안의 `commit;` 을 `rollback;` 으로 바꿔도 debug/release SA 결과가 같다(측정).
- 행이 여러 개인 테이블에서 `select i, cf () from t where i < 4 order by i;` 를 실행해도 같다(측정).
- 최신 develop `38c931e7d` 에도 `ER_SP_TCL_DDL_IN_QUERY` 는 아직 없어, 이 경로는 그대로 남아 있다(소스 확인).

**콜스택 (debug SA, gdb 측정)**

``` java
pgbuf_unfix_all (page_buffer.c:3253)            assert (false)
lock_unlock_all (lock_manager.c:7779)           SA 분기
log_commit_local (log_manager.c:5333)
log_commit (log_manager.c:5500)
xtran_server_commit (transaction_sr.c:95)
tran_commit (transaction_cl.c:331)
db_commit_transaction (db_admin.c:1507)
cubmethod::callback_handler::end_transaction (method_callback.cpp:234)
method_dispatch (query_method.cpp:181)
xs_callback_send (network_callback_sr.cpp:123)  SA 는 같은 스레드에서 바로 dispatch
cubpl::executor::callback_end_transaction (pl_executor.cpp:1013)
cubpl::executor::execute (pl_executor.cpp:321)
fetch_peek_dbval_slow (fetch.c:1917)
qexec_end_one_iteration (query_executor.c:1384)
qexec_intprt_fnc (query_executor.c:14635)
qexec_execute_query (query_executor.c:22769)
```

- assert 시점에 스레드가 잡은 페이지는 1개(0|769)다. 바깥 SELECT 의 힙 스캔(`S_HEAP_SCAN`)이 `page_watcher` 로 READ 래치를 쥐고 있고(`heap_file.c:7665` 에서 fix), `cache_last_fix_page=true` 다(측정).
- SA 의 `lock_unlock_all` 은 트랜잭션 끝에서 `pgbuf_unfix_all` 을 부른다. 이 함수는 요청이 끝나 잡은 페이지가 없다고 가정하므로, debug 는 assert 로 멈추고 release 는 바깥 스캔이 쓰는 페이지를 unfix 한다. release 의 SIGSEGV 는 바깥 스캔이 그 페이지를 다시 쓰면서 나는 것으로 보인다(코드에서 추론, release 스택은 받지 않음).
- CS 에서는 COMMIT 콜백이 서버의 다른 worker 스레드에서 새 요청으로 처리된다. 그 스레드는 잡은 페이지가 없어 크래시하지 않고, `qmgr_clear_trans_wakeup` (`query_manager.c:2405`)이 실행 중인 질의를 건너뛴다(로그와 코드로 확인).

이 이슈의 수정 방향(SA 빌드에서 쿼리 실행 요청 종류를 적어 두고 콜백의 COMMIT/ROLLBACK 을 `ER_SP_TCL_DDL_IN_QUERY` 로 거부)이 들어가면 위 경로에 들어가지 않을 것으로 봅니다(추론). 수정 확인 때 위 repro 를 debug/release 의 `csql -S` 에서 함께 돌려 주시면 좋겠습니다.
