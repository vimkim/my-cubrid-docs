# LOB commit 구간 crash 재현 보고서

- 작성일 2026-11-05 (Asia/Seoul)
- 관련 CBRD-27237 결정 Q5, work-tracker 825, 등록한 결함 CBRD-27964
- 소스 `CUBRID/CUBRID` develop `21c6e635d404cd67a10a25e4f52c17d1cc8deed0`, 로컬 수정 없음
- 빌드 `debug_gcc`, 서버 버전 `11.5.0.2835 (64 debug build)`
- 계측 gdb 14.2 attach, breakpoint와 `logpb_force_flush_pages` 호출, `er_log_vacuum=640`

근거 표시. [실행]은 이번 실행에서 관찰했다. [소스]는 위 commit의 소스를 읽었다. [추론]은 둘에서 끌어낸 판단이다.

## 1. 질문과 결론

**질문.** commit 중 `RVES_NOTIFY_VACUUM` 레코드가 commit 레코드보다 먼저 디스크에 내려간 뒤 서버가 죽으면, 재시작 뒤 vacuum이 rollback된 트랜잭션의 LOB 파일을 지워서 되살아난 행이 없는 파일을 가리키는가?

**결론 1. 의심한 notify 경로로는 데이터 손상이 나지 않는다.** vacuum은 loser 트랜잭션의 notify 레코드를 실제로 처리해 파일을 지운다 [실행]. 그러나 notify가 붙는 LOB는 같은 트랜잭션이 만든 파일뿐이다 [소스]. rollback 뒤 그 파일을 가리키는 행은 없다 [실행]. 브리프의 6단계(되살아난 행이 지워진 파일을 가리킨다)가 틀렸다.

**결론 2. 같은 commit 구간에 더 직접적인 결함이 있고 재현됐다.** 이전에 commit된 LOB를 UPDATE나 DELETE로 버리면, `tx_lob_locator_clear`가 commit 레코드를 쓰기 전에 그 파일을 바로 `unlink`한다 [소스, 실행]. vacuum도 notify도 거치지 않는다. 이 지점과 commit 레코드 flush 사이에 서버가 죽으면 재시작 뒤 행은 옛 locator를 가리키고 파일은 없다 [실행]. log flush 조작이 필요 없다. kill -9만으로 재현된다.

**결론 3. 같은 결함이 crash 없이 런타임에도 보인다.** REPEATABLE READ 트랜잭션이 옛 행을 보는 동안 다른 트랜잭션이 LOB를 UPDATE하고 commit하면, 옛 행의 LOB 파일이 바로 사라진다 [실행]. 브리프 7번(런타임은 `mvcc_table.cpp` 보호로 안전)은 vacuum 경로에만 맞다. 직접 삭제 경로는 그 보호를 받지 않는다.

| 실험 | 경로 | 조작 | 결과 |
| --- | --- | --- | --- |
| E3 | 직접 삭제 | 크래시 없음. RR reader와 writer | reader가 `External file ... was not found` (ERROR -1020) |
| E2a | 직접 삭제 | commit 레코드 직전 kill -9, flush 없음 | 재시작 뒤 행 1이 없는 파일을 가리킨다 |
| E2b | 직접 삭제 | commit 레코드 직전 flush 후 kill -9 | 복구가 1 트랜잭션 undo. 행 2가 없는 파일을 가리킨다 |
| E1 | 서버 측 INSERT+UPDATE | 같은 tx에서 만들고 바꿈 | notify가 생기지 않는다. 직접 삭제로 처리된다 |
| E1' | 클라이언트 측 UPDATE 두 번 | notify 뒤 flush, kill -9 | vacuum이 loser notify를 처리한다. 그 파일을 가리키는 행은 없다 |
| C1 | 대조군 | COMMIT 전 kill -9 | 행 3과 파일 모두 그대로다 |

## 2. 브리프 추론의 줄 번호 재확인

브리프는 `dcbf09e4f` 계열 줄 번호를 썼다. `21c6e635d`에서 순서는 같고 번호만 바뀌었다 [소스].

| 브리프 | `21c6e635d` | 내용 |
| --- | --- | --- |
| `log_manager.c:5262` | [`log_manager.c:5250`](https://github.com/CUBRID/CUBRID/blob/21c6e635d404cd67a10a25e4f52c17d1cc8deed0/src/transaction/log_manager.c#L5250) | `tx_lob_locator_clear (thread_p, tdes, true, NULL)` |
| `:5267` | [`:5255`](https://github.com/CUBRID/CUBRID/blob/21c6e635d404cd67a10a25e4f52c17d1cc8deed0/src/transaction/log_manager.c#L5255) | `logtb_complete_mvcc` |
| `:5312` | [`:5300`](https://github.com/CUBRID/CUBRID/blob/21c6e635d404cd67a10a25e4f52c17d1cc8deed0/src/transaction/log_manager.c#L5300) | `log_append_commit_log` |
| `:5321` | [`:5309`](https://github.com/CUBRID/CUBRID/blob/21c6e635d404cd67a10a25e4f52c17d1cc8deed0/src/transaction/log_manager.c#L5309) | `log_change_tran_as_completed` 안에서 `logpb_flush_pages` (`:4807`) |
| `transaction_transient.cpp:444-446` | 같음 | `PERMANENT_DELETED`면 `vacuum_notify_es_deleted` |
| `vacuum.c:3742-3756` | [`vacuum.c:3567-3581`](https://github.com/CUBRID/CUBRID/blob/21c6e635d404cd67a10a25e4f52c17d1cc8deed0/src/query/vacuum.c#L3567-L3581) | notify 레코드를 만나면 `es_delete_file` |
| `log_recovery.c:1956-1963` | [`log_recovery.c:1957-1964`](https://github.com/CUBRID/CUBRID/blob/21c6e635d404cd67a10a25e4f52c17d1cc8deed0/src/transaction/log_recovery.c#L1957-L1964) | checkpoint의 활성 트랜잭션을 `TRAN_UNACTIVE_UNILATERALLY_ABORTED`로 둔다 |

브리프 5번의 vacuum loser 미필터 줄 번호(`vacuum.c:4243-4283`, `:5843-5880`)는 다시 읽지 않았다. 대신 E1'에서 그 동작을 실행으로 확인했다.

## 3. 소스 구조

### 3.1 트랜잭션 LOB 목록

각 트랜잭션은 `tdes->lob_locator_root`에 red-black tree를 둔다 ([`log_impl.h:533`](https://github.com/CUBRID/CUBRID/blob/21c6e635d404cd67a10a25e4f52c17d1cc8deed0/src/transaction/log_impl.h#L533)). 항목의 키는 locator 문자열에서 마지막 `.` 뒤 부분이다(`lob_locator_key`). 키는 항목을 넣을 때 한 번 정한다(`transaction_transient.cpp:195`). 상태 변경(`xtx_change_state_of_locator`)은 `entry->top->locator`만 새 locator로 바꾸고 키는 그대로 둔다(`:288`) [소스].

상태는 `lob_locator.hpp:26-61`에 있다. 이번 결함에 관련된 것은 셋이다.

- `LOB_PERMANENT_CREATED`. 이 트랜잭션이 만들어 행에 묶은 파일.
- `LOB_PERMANENT_DELETED`. 위 파일을 같은 트랜잭션이 다시 버렸다.
- `LOB_TRANSIENT_DELETED`. 목록에 없는 locator(이전 트랜잭션이 commit한 파일)를 이 트랜잭션이 버렸다.

`elo_delete`는 목록에서 locator를 찾는다. 없으면(`LOB_NOT_FOUND`) `LOB_TRANSIENT_DELETED`로 넣는다 ([`elo.c:548-549`](https://github.com/CUBRID/CUBRID/blob/21c6e635d404cd67a10a25e4f52c17d1cc8deed0/src/object/elo.c#L548-L549)). 찾았고 `PERMANENT_CREATED`면 `PERMANENT_DELETED`로 바꾼다(`:540-542`) [소스].

### 3.2 commit 처리

`tx_lob_locator_clear (at_commit=true)`는 `PERMANENT_CREATED`가 아닌 모든 항목을 지울 대상으로 본다(`transaction_transient.cpp:391-396`). 그 뒤 처리가 갈린다 ([`transaction_transient.cpp:440-456`](https://github.com/CUBRID/CUBRID/blob/21c6e635d404cd67a10a25e4f52c17d1cc8deed0/src/transaction/transaction_transient.cpp#L440-L456)) [소스].

- `PERMANENT_DELETED`면 `vacuum_notify_es_deleted`로 `RVES_NOTIFY_VACUUM` undo 레코드를 붙인다. 파일은 vacuum이 지운다.
- 그 밖(`TRANSIENT_DELETED` 포함)이면 `es_delete_file`로 바로 지운다. 주석은 "만들었다가 rollback되어 아무도 못 보는 파일"이라고 적지만, commit 경로의 `TRANSIENT_DELETED`는 다른 트랜잭션이 commit한 파일이다.

이 함수는 `log_commit_local`에서 commit 레코드 append(`:5300`)와 flush(`:5309`)보다 먼저 불린다(`:5250`). 주석(`:5242-5249`)은 로그를 남기기 위해 이 순서가 필요하다고 설명한다. 직접 삭제에는 로그가 없고 되돌릴 방법도 없다 [소스].

이 분기는 2019년 `773153460` (CBRD-22822 Lob locator)에서 지금 모양이 됐다 [실행, git log].

### 3.3 서버 측 DML에서 notify가 생기지 않는 이유

E1 추적에서 서버 측 INSERT는 이렇게 흘렀다 [실행].

```text
ADD    file:ces_609/ces_temp.00001793880829987805_6038 state=LOB_TRANSIENT_CREATED
CHANGE file:ces_609/ces_temp.00001793880829987805_6038 -> file:70517040/ces_639/dba.t.00001793880830075557_7718 state=LOB_PERMANENT_CREATED
FIND   file:70517040/ces_639/dba.t.00001793880830075557_7718
ADD    file:70517040/ces_639/dba.t.00001793880830075557_7718 state=LOB_TRANSIENT_DELETED
UNLINK 70517040/ces_639/dba.t.00001793880830075557_7718   (tx_lob_locator_clear, transaction_transient.cpp:452)
```

`heap_attrinfo_transform_to_disk`가 `elo_copy_with_prefix`로 temp 파일을 클래스 디렉터리로 옮긴다(`heap_file.c:13487`). 새 이름은 키가 다르다. 목록 항목의 키는 temp 이름(`..._6038`)으로 남는다. 그래서 같은 트랜잭션의 UPDATE가 새 locator(`..._7718`)를 찾지 못하고 `TRANSIENT_DELETED`로 다시 넣는다. 결과적으로 같은 트랜잭션이 만든 파일도 commit 때 바로 지워진다 [실행]. 이 경우는 무해하다. rollback되면 그 행 자체가 없어지기 때문이다 [추론].

`PERMANENT_DELETED`와 notify는 클라이언트 측 DML 경로에서만 관찰했다. 트리거가 있는 테이블의 UPDATE는 서버 측 update를 쓰지 않는다(`execute_statement.c:9956`). 이 경로의 `elo_copy`(`elo.c:276`)는 같은 디렉터리에서 이름만 바꾸므로 키가 유지된다 [소스, 실행].

```text
CHANGE file:ces_047/ces_temp.00001793880881560687_4214 -> file:ces_047/dba.t2.00001793880881560687_4214 state=LOB_PERMANENT_CREATED
FIND   file:ces_047/dba.t2.00001793880881560687_4214
CHANGE file:ces_047/dba.t2.00001793880881560687_4214 -> NULL state=LOB_PERMANENT_DELETED
UNLINK ces_495/dba.t2.00001793880769592598_6314           (이전 commit LOB, 직접 삭제)
NOTIFY file:ces_047/dba.t2.00001793880881560687_4214      (같은 tx가 만든 LOB)
```

## 4. 실험 절차

### 4.1 환경

- worktree `/home/vimkim/gh/cb/CBRD-LOB-notify-crash-repro`, DB `testdb`(이 worktree 전용). `cubrid.conf`에 `er_log_vacuum=640`(WORKER와 RECOVERY)을 더했다.
- 서버 시작은 CUBRID.md 규칙대로 stdin `/dev/null`, 출력은 일반 파일로 했다.
- 준비 SQL

```sql
create table t (id int primary key, b blob);
insert into t values (1, bit_to_blob(X'aaaa'));  -- 2..4도 같은 꼴, 각각 auto commit
```

### 4.2 gdb 드라이버

`cub_server`에 attach하고 Python breakpoint 세 개를 건다.

1. `xes_posix_delete_file`. 경로와 backtrace를 찍고 멈추지 않는다.
2. `tx_lob_locator_clear`. `at_commit`이 참이고 목록이 비어 있지 않으면, 그 thread에만 `log_append_commit_log` breakpoint를 새로 건다.
3. `log_append_commit_log`. 여기서 멈춘다. `tdes->tail_lsa`, `posp_nxlsa`, `log_Gl.prior_info.prior_lsa`, `log_Gl.append.get_nxio_lsa()`를 찍는다. flush 모드면 `call logpb_force_flush_pages(thread_p)` 뒤 nxio를 다시 찍는다. 그 뒤 `kill`(SIGKILL)한다.

멈춘 지점에서 `tdes->state`는 `TRAN_UNACTIVE_WILL_COMMIT`, `posp_nxlsa`는 `-1|-1`이었다. postpone이 없으므로 `LOG_COMMIT_WITH_POSTPONE`도 없다. 이 트랜잭션은 재시작 때 loser가 된다 [실행].

### 4.3 E3. 런타임 RR reader

```sh
# reader (--no-auto-commit)
set transaction isolation level repeatable read;
select id, b from t where id=4;   # 옛 locator ...ces_067/dba.t.00001793880423322744_2726
select sleep(6);
select id, b, blob_to_bit(b) from t where id=4;
# writer (2초 뒤, auto commit)
update t set b = bit_to_blob(X'd1d1') where id=4;
```

writer commit 직후 `lob/70517040/ces_067/`는 비어 있었다. reader의 마지막 SELECT는 `ERROR: External file "70517040/ces_067/dba.t.00001793880423322744_2726" was not found.`로 실패했다. server log에는 `Query execution error. ERROR_CODE = -1020`이 남았고 vacuum의 `Delete lob` 기록은 없었다 [실행].

### 4.4 E2a. flush 없이 kill

```sh
update t set b = bit_to_blob(X'a2a2') where id=1;   # auto commit
```

```text
=== xes_posix_delete_file path=70517040/ces_423/dba.t.00001793880423317176_4477
#2 tx_lob_locator_clear (... at_commit=true ...) at transaction_transient.cpp:452
#3 log_commit_local (...) at log_manager.c:5250
=== stopped at log_append_commit_log
tdes->trid=28 tail_lsa=175|3344 posp_nxlsa=-1|-1 state=TRAN_UNACTIVE_WILL_COMMIT
before: prior_lsa=175|3672 nxio_lsa=175|3344
=== SIGKILL
```

master가 서버를 다시 띄웠다. 복구 로그는 `transactions to undo: 0`이었다. UPDATE 레코드도 디스크에 없었으므로 UPDATE 자체가 사라졌다. 행 1은 `file:70517040/ces_423/dba.t.00001793880423317176_4477`를 가리키고 `blob_to_bit(b)`는 `External file ... was not found`로 실패했다 [실행].

### 4.5 E2b. flush 후 kill

```sh
update t set b = bit_to_blob(X'b2b2') where id=2;   # auto commit
```

```text
=== xes_posix_delete_file path=70517040/ces_606/dba.t.00001793880423319308_6314   (transaction_transient.cpp:452)
tdes->trid=31 tail_lsa=175|3504
before:      prior_lsa=175|3832 nxio_lsa=175|3504
after flush: prior_lsa=175|3832 nxio_lsa=175|3832
=== SIGKILL
```

flush 뒤 nxio가 prior_lsa와 같아졌다. 이 트랜잭션의 모든 레코드는 디스크에 있고 commit 레코드는 없다. 이번에는 master가 서버를 다시 띄우지 않아 직접 시작했다. 복구는 `transactions to undo: 1`로 UPDATE를 되돌렸다. 행 2는 옛 locator `...ces_606/dba.t.00001793880423319308_6314`를 가리키고 파일은 없다 [실행].

### 4.6 E1'. notify 경로

트리거가 있는 테이블 `t2`(`create trigger t2_trg before update on t2 execute print 'x'`)에서 같은 행을 두 번 UPDATE했다.

```sh
update t2 set b = bit_to_blob(X'21') where id=1;
update t2 set b = bit_to_blob(X'22') where id=1;
commit;
```

```text
=== UNLINK ces_338/dba.t2.00001793880882178111_4057                 (이전 commit LOB, 직접 삭제)
=== NOTIFY uri=file:ces_169/dba.t2.00001793880926500803_5403 prior_lsa=176|11360
trid=86 tail_lsa=176|11360 posp_nxlsa=-1|-1
before:      prior_lsa=176|11488 nxio_lsa=176|10608
after flush: nxio_lsa=176|11488
=== SIGKILL
```

notify 레코드는 `176|11360`에 있다. flush된 끝(`176|11488`)은 notify 뒤, commit 레코드 앞이다. 재시작 복구는 `transactions to undo: 1`이었다. vacuum은 `vacuum_recover_lost_block_data, start recovering from 176|11360`을 남겼다. 로그를 더 쌓자(60000행 insert와 delete) vacuum worker가 이 레코드를 처리했다 [실행].

```text
VACUUM (thr=4314, ...): Delete lob file:ces_169/dba.t2.00001793880926500803_5403 based on 176|11360
#1 es_delete_file (uri="file:ces_169/dba.t2.00001793880926500803_5403") at es.c:333
#2 vacuum_process_log_block (...) at vacuum.c:3572
```

이것으로 브리프 3~5단계(vacuum이 commit 여부를 보지 않고 loser의 notify를 처리한다)가 실행으로 맞다. 그러나 `..._5403`은 rollback된 첫 UPDATE가 만든 파일이다. rollback 뒤 행은 그 앞 값 `..._4057`로 돌아간다. `..._5403`을 가리키는 행은 없다. 행이 가리키는 `..._4057`은 notify가 아니라 직접 삭제로 사라졌다 [실행].

### 4.7 C1. 대조군

```sh
update t set b = bit_to_blob(X'c2c2') where id=3; select sleep(20); commit;   # --no-auto-commit
```

sleep 중에 kill -9했다. commit 경로에 들어가지 않았으므로 직접 삭제가 없다. 복구 로그는 `Log pages to undo: 775, transactions to undo: 11`이었다. 직전에 auto commit으로 끝낸 60000행 insert와 delete 외에 undo할 트랜잭션이 11개인 이유는 보지 않았다 [실행, 원인 미확인]. 재시작 뒤 `lob/70517040/ces_226/dba.t.00001793880423321067_5341`이 남아 있고 행 3은 `X'cccc'`로 읽혔다 [실행].

## 5. 영향

- crash 구간. `tx_lob_locator_clear`부터 commit 레코드 flush까지 서버가 죽으면, 그 트랜잭션이 UPDATE나 DELETE로 버린 이전 commit LOB 파일이 사라진 채로 행이 되살아난다. 일반 SQL UPDATE와 DELETE가 모두 이 경로를 쓴다(`heap_file.c:13043`, `query_executor.c:16831`) [소스, E2 실행].
- 런타임. commit 직후 옛 snapshot을 가진 reader가 그 LOB를 읽으면 실패한다. REPEATABLE READ에서 재현했다. READ COMMITTED에서도 한 문장이 실행되는 동안 같은 창이 있을 수 있다 [추론, 실행 안 함].
- HA나 백업 복원에서의 영향은 보지 않았다.

## 6. 남은 질문

- E1' 재시작 직후 lob 루트의 `ces_*` 디렉터리(클라이언트 측 경로가 만든 파일, `ces_047`, `ces_169` 등)가 vacuum 처리 전에 이미 없었다. lob 루트 디렉터리 mtime은 재시작 시각 `21:15:54`였다. 보고서를 쓴 뒤 찾은 [CBRD-27892](http://jira.cubrid.org/browse/CBRD-27892)가 이를 설명한다. 서버는 부팅할 때 lob 루트 바로 아래 `ces_xxx`를 임시 파일 자리로 보고 지운다(CBRD-23700). 트리거가 있는 테이블의 UPDATE는 새 LOB를 클래스 디렉터리로 옮기지 않아 그 자리에 남는다. E1'의 `t2`가 바로 이 경우다 [JIRA 기록과 일치, 부팅 정리 코드는 직접 읽지 않음]. 클래스 디렉터리(`70517040/`) 아래 파일은 남아 있었다. 결론 1과 2에는 영향이 없다.
- 직접 삭제를 notify로 바꾸면 런타임 문제는 vacuum의 MVCC 보호로 풀린다 [추론]. crash 구간은 notify 경로가 그대로 이어받는다. 다만 이전 commit LOB에 대한 notify는 rollback 뒤 행이 다시 가리키는 파일이므로, 그때는 브리프가 걱정한 손상이 실제로 생긴다 [추론]. 고칠 때는 notify를 commit 레코드 뒤로 미루거나 loser notify를 vacuum이 건너뛰게 해야 한다. CBRD-27237의 OOS 알림 설계와 같은 문제다.
- 서버 측 경로에서 목록 키가 temp 이름으로 남는 동작(3.3절)이 의도인지 확인하지 않았다.

## 7. 관련 이슈

- [CBRD-27964](http://jira.cubrid.org/browse/CBRD-27964). 이 보고서의 결론 2와 3을 등록한 결함.
- [CBRD-20009](http://jira.cubrid.org/browse/CBRD-20009). 2016년 RQG(READ COMMITTED, DELETE와 LOB 조회 동시 실행)에서 같은 `External file ... was not found`가 났다. 원인 분석 없이 열려 있다. 결론 3과 같은 증상이다 [추론, 그 테스트는 실행하지 않음].
- [CBRD-27892](http://jira.cubrid.org/browse/CBRD-27892). 트리거 테이블 LOB가 부팅 정리로 사라지는 다른 결함. 6절 첫 항목을 설명한다.

## 8. 재현 자료

gdb 드라이버와 원시 로그는 세션 scratchpad(`/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-LOB-notify-crash-repro/21213b5e-31f7-4f39-b8ec-53e6acd6bc26/scratchpad/`)에 있다. 저장소에는 넣지 않았다. 필요한 발췌는 이 보고서에 옮겼다.
