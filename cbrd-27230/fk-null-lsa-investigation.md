# FK 검사 실패로 롤백된 UPDATE의 복제 레코드가 NULL lsa로 commit 때 기록되는지 조사

- 날짜: 2026-11-18
- 대상: `origin/develop` `2e67e1d948` ([CBRD-27463] #8198 merge 직후)
- 출발점: [review-miss-analysis.md](review-miss-analysis.md) §4의 "plausible, base 문제" 항목 3
- 결론: **confirmed**. develop debug 빌드의 단일 노드 HA master에서 재현했다. 롤백된 UPDATE가 commit 때 `RVREPL_DATA_UPDATE, Target log lsa = -1|-1` 로 기록된다. slave(applylogdb) 쪽 동작은 코드 추적으로만 확인했다.

## 1. develop의 코드 순서

링크는 모두 `2e67e1d948` 기준이다.

`locator_update_force` 의 행 UPDATE 경로:

| 순서 | 위치 | 동작 |
|---|---|---|
| 1 | [`locator_sr.c:7145`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/locator_sr.c#L7145) | `heap_update_logical`. heap 로그를 쓰면서 `tdes->repl_update_lsa` 를 그 LSA로 둔다 ([`log_manager.c:2302`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/log_manager.c#L2302)) |
| 2 | [`locator_sr.c:7170`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/locator_sr.c#L7170) → [`:10195`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/locator_sr.c#L10195) / [`:10205`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/locator_sr.c#L10205) | `locator_update_index` 의 마지막에서 `repl_log_insert (..., RVREPL_DATA_UPDATE, ...)`. 레코드는 `lsa = NULL` ([`replication.c:460`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/replication.c#L460)), `must_flush = LOG_REPL_COMMIT_NEED_FLUSH` ([`:443`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/replication.c#L443)) 로 `tdes->repl_records` 에 들어간다 |
| 3 | [`locator_sr.c:7214-7225`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/locator_sr.c#L7214-L7225) | `locator_check_foreign_key`. 실패하면 `goto error` |
| 4 | [`locator_sr.c:7235-7240`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/locator_sr.c#L7235-L7240) | `repl_add_update_lsa`. 2의 레코드에 1의 LSA를 채운다 ([`replication.c:252-265`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/replication.c#L252-L265)) |

3에서 실패하면 4를 건너뛰므로 2의 레코드는 NULL lsa로 남는다. 2와 3 사이에 실패할 수 있는 지점은 develop에서 3뿐이다. `repl_log_insert` 는 `locator_update_index` 의 마지막 동작이다.

이 순서는 #8198 이전에도 있었다. #8198 직전 `cf9ef28881` 에서는 `locator_update_index`(:6428) → FK 검사(:6471) → `heap_update_logical`(:6486) → `repl_add_update_lsa`(:6513) 순이었다. 그때는 heap 갱신 실패도 같은 창을 만들었다. `release/10.2`, `release/11.0`, `release/11.4` 도 `locator_update_index` → FK 검사 → `repl_add_update_lsa` 순서다. #8198이나 OOS가 만든 문제가 아니다.

## 2. 롤백 경로가 이 레코드를 지우지 않는다

1. 서버 측 UPDATE는 문장 원자성을 위해 sysop을 연다 ([`query_executor.c:16052`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/query/query_executor.c#L16052)). 오류가 나면 `xtran_server_end_topop (LOG_RESULT_TOPOP_ABORT)` 를 부른다 ([`:16667`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/query/query_executor.c#L16667)). 이 함수는 `log_sysop_abort` 를 부른다 ([`transaction_sr.c:304`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/transaction_sr.c#L304)). 클라이언트 savepoint 롤백(`log_abort_partial`)도 `log_sysop_abort` 로 끝난다 ([`log_manager.c:5772`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/log_manager.c#L5772)).
2. `log_sysop_abort` 가 복제 레코드에 하는 일은 `repl_log_abort_after_lsa (tdes, 부모 LSA)` 하나다 ([`log_manager.c:4175`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/log_manager.c#L4175)).
3. `repl_log_abort_after_lsa` 는 `LSA_GT (&rec.lsa, start_lsa)` 인 레코드만 `LOG_REPL_DONT_NEED_FLUSH` 로 바꾼다 ([`replication.c:753-758`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/replication.c#L753-L758)). NULL lsa는 `pageid = -1` 이고 비교는 부호 있는 정수 비교다 ([`log_lsa.hpp:180-189`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/log_lsa.hpp#L180-L189)). 그래서 어떤 실제 LSA보다도 작고, 레코드는 `COMMIT_NEED_FLUSH` 로 남는다.
4. 레코드를 지우는 다른 코드는 `repl_end_flush_mark (need_undo = true)` 뿐이다 ([`replication.c:719-731`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/replication.c#L719-L731)). 이 함수는 `SELECT ... INCR` 류의 flush mark 경로에서만 불린다(`query_executor.c:20913`). 일반 UPDATE 오류 경로는 이 함수를 거치지 않는다.
5. 같은 행을 나중에 다시 UPDATE해도 이 레코드는 채워지지 않는다. `repl_add_update_lsa` 는 배열 끝에서부터 찾으므로 새 레코드를 먼저 찾는다.
6. commit 때 `log_append_repl_info_internal` 은 `must_flush != DONT_NEED_FLUSH` 인 레코드를 모두 쓴다. UPDATE 레코드는 `repl_rec->lsa` 를 그대로 복사한다 ([`log_manager.c:4682-4704`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/log_manager.c#L4682-L4704)).

트랜잭션 전체가 abort되면 복제 로그를 쓰지 않으므로 문제가 없다. 문제가 되는 것은 FK 오류가 난 문장만 롤백되고 같은 트랜잭션이 commit되는 경우다. autocommit을 끈 애플리케이션이 FK 예외를 잡고 계속 진행한 뒤 commit하는 패턴이 여기에 해당한다.

## 3. 재현 (develop debug 빌드, 단일 노드 HA master)

환경: `CUBRID 11.5.0 (11.5.0.2967-2e67e1d) (64bit debug build for Linux)`. 한 가지 차이가 있다. 이 빌드는 develop의 `src/broker/cas_cgw_odbc.c` 가 `<ctype.h>` 를 include하지 않아 gcc에서 컴파일되지 않았다(`toupper` 미선언, #7723에서 들어옴). 빌드할 때만 `#include <ctype.h>` 한 줄을 넣었다가 되돌렸다. broker 코드라서 서버 동작과는 관계없다.

설정:

```ini
# cubrid.conf [common]
ha_mode=on
# cubrid_ha.conf [common]
ha_port_id=<빈 포트>
ha_node_list=fkgrp@<hostname>
ha_db_list=fkdb
```

```sh
cubrid createdb fkdb en_US.utf8
cubrid heartbeat start        # 단일 노드라 master(active)가 된다
csql -u dba --no-auto-commit -e -i setup.sql fkdb@localhost
csql -u dba --no-auto-commit -e -i repro.sql fkdb@localhost
cubrid heartbeat stop
printf '1\n-1\n-1\n-1\ny\n' | cubrid diagdb -d 8 -o logdump.txt fkdb
grep -a -n -A1 'Target log lsa' logdump.txt
```

```sql
-- setup.sql
create table p (id int primary key);
create table c (id int primary key, pid int, v int, foreign key (pid) references p(id));
insert into p values (1);
insert into c values (1, 1, 0);
insert into c values (2, 1, 0);
commit;

-- repro.sql
update c set v = 10 where id = 2;               -- 성공
update c set pid = 999, v = 20 where id = 1;    -- FK 위반, 문장 롤백
commit;
select * from c order by id;                    -- (1,1,0), (2,1,10)
```

결과. 두 번째 UPDATE는 `ERROR: The constraint of the foreign key 'fk_c_pid' is invalid, due to value '999'.` 로 실패한다. 행 1은 바뀌지 않았다. 그런데 commit 직전 로그에 행 1의 UPDATE 복제 레코드가 있다.

```text
LSA = 177|3904 ... Trid = 22  Type = LOG_MVCC_UNDOREDO_DATA, Recv_index = RVHF_UPDATE_NOTIFY_VACUUM   # 행 1 heap 갱신
...                                                                                                     # btree, compensate
LSA = 177|4600 ... Type = LOG_SYSOP_END, Prev parent LSA = 177|3736, LOG_SYSOP_END_ABORT               # 문장 롤백
LSA = 177|4704 ... Type = LOG_REPLICATION_DATA, Target log lsa = 177|3736
T[RVREPL_DATA_UPDATE] C[] K[2]                                                                          # 정상 (행 2)
LSA = 177|4784 ... Type = LOG_REPLICATION_DATA, Target log lsa = -1|-1
T[RVREPL_DATA_UPDATE] C[] K[1]                                                                          # 롤백된 UPDATE
LSA = 177|4864 ... Type = LOG_COMMIT
```

## 4. slave 영향 (코드 추적, 실행 확인 안 함)

applylogdb는 UPDATE 항목의 target lsa에서 after image를 읽는다. `la_apply_update_log` 는 `la_get_page (item->target_lsa.pageid)` 를 부른다 ([`log_applier.c:5196-5202`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/log_applier.c#L5196-L5202)).

- debug 빌드: `la_get_page` 의 `assert (pageid != NULL_PAGEID)` 에서 applylogdb가 죽는다 ([`log_applier.c:1345`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/log_applier.c#L1345)). 재시작하면 마지막으로 적용한 commit 뒤부터 다시 읽으므로 같은 레코드에서 또 죽을 것으로 본다. 그러면 복제가 멈춘다 [추론].
- release 빌드: `la_get_page` 는 NULL을 돌려준다. `la_apply_update_log` 는 `er_errid ()` 를 그대로 돌려준다. 남아 있는 오류가 없으면 NO_ERROR라서 항목을 조용히 건너뛴다. 결과 데이터는 우연히 맞다. 남은 오류가 있으면 "Internal system failure" 로 기록하고 실패 건수를 올린다. 그 오류가 `la_retry_on_error` 대상이면 같은 항목을 10초마다 계속 재시도한다 ([`log_applier.c:5929-5945`](https://github.com/CUBRID/cubrid/blob/2e67e1d9482714f077b554dec5b17a64d167393f/src/transaction/log_applier.c#L5929-L5945)). 어느 쪽이 될지는 직전 오류 상태에 달려 있다 [추론].
- 잘못된 행 값이 slave에 적용되지는 않는다. 읽을 after image가 없기 때문이다.

실제 slave에서 실행하려면 2노드 HA가 필요하다. 이 호스트는 공유 서버라서 두 번째 노드 이름을 둘 수 없어 돌리지 않았다. 2노드 HA에서 3절 시나리오를 돌린 뒤 debug applylogdb의 core와 `cubrid applyinfo` 의 실패 건수를 보면 확인할 수 있다.

## 5. 판정

- **confirmed** (master 쪽, 실행 확인): FK 검사 실패로 문장 롤백된 UPDATE의 `RVREPL_DATA_UPDATE` 가 NULL target lsa로 commit 때 기록된다.
- slave 영향은 코드상 debug에서는 applylogdb assert, release에서는 오류 상태에 따라 건너뜀·실패 기록·무한 재시도다 [추론].
- 원인은 `repl_log_insert` 가 FK 검사보다 먼저 레코드를 만들고, 롤백 정리가 lsa로만 레코드를 고른다는 점이다. CBRD-27230(PR #8559)과 무관한 오래된 문제다. 다만 그 PR의 OOS 항목은 행 레코드와 함께 남거나 버려지므로, 이 문제가 고쳐질 때 같이 버려져야 한다.
- 중복 확인: `cubrid-jira-dup candidate-find` 결과에 같은 원인의 이슈는 없었다. CBRD-27801(OOS 복합 PK UPDATE에서 applylogdb assert 반복 종료)은 증상이 비슷하지만 원인이 다르다.

## 6. JIRA 이슈 초안

# [HA] 외래 키 검사로 롤백된 UPDATE가 NULL target lsa 복제 로그로 commit 때 기록된다

**한 줄 요약**: 외래 키 위반으로 문장만 롤백된 UPDATE의 복제 레코드가 지워지지 않고, 같은 트랜잭션의 commit 때 대상 LSA가 없는 UPDATE 복제 로그로 기록되는 문제다.

## Issue Triage

**이슈 수행 목적**: 롤백된 문장의 복제 레코드가 commit 때 기록되지 않고, slave가 해당 트랜잭션을 정상적으로 적용한다.

**이슈 수행 이유**: develop debug 빌드의 HA master에서 재현했다. autocommit을 끈 트랜잭션에서 UPDATE가 외래 키 위반으로 실패한 뒤 commit하면 `RVREPL_DATA_UPDATE, Target log lsa = -1|-1` 레코드가 기록된다. 같은 코드 순서가 10.2부터 있다.

**영향**: HA를 쓰고, FK 오류 뒤에도 트랜잭션을 계속해 commit하는 애플리케이션이 영향을 받는다. debug applylogdb는 NULL 페이지 assert로 종료될 것으로 본다. release applylogdb는 직전 오류 상태에 따라 항목을 건너뛰거나, 실패로 기록하거나, 계속 재시도할 것으로 본다. slave 쪽은 코드 분석이며 실행 확인은 하지 않았다.

**이슈 수행 방안**: TBD - ANALYSIS 단계에서 해결 방안과 구현 범위를 결정한다.

---

## AI-Generated Context

## Description

`locator_update_force` 는 `locator_update_index` 안에서 `repl_log_insert (RVREPL_DATA_UPDATE)` 로 lsa가 비어 있는 복제 레코드를 만든다. 그다음 외래 키를 검사하고, 마지막에 `repl_add_update_lsa` 로 lsa를 채운다. 외래 키 검사가 실패하면 lsa가 비어 있는 채로 남는다. 문장 롤백(`log_sysop_abort`)은 `repl_log_abort_after_lsa` 로 레코드를 버리는데, 이 함수는 `LSA_GT (rec.lsa, 부모 LSA)` 로만 고른다. NULL lsa는 모든 LSA보다 작으므로 버려지지 않는다. 그래서 같은 트랜잭션이 commit하면 레코드가 기록된다.

## Test Build

`CUBRID 11.5.0 (11.5.0.2967-2e67e1d) (64bit debug build for Linux)`, develop `2e67e1d948`

## Repro

단일 노드 HA(`ha_mode=on`, `cubrid heartbeat start` 로 master)에서 실행한다. 아래는 최소화한 형태다. 실제로 실행한 것은 이 앞에 성공하는 UPDATE 한 건이 더 있는 시나리오이고, 그 결과가 Actual Result다.

```sql
create table p (id int primary key);
create table c (id int primary key, pid int, v int, foreign key (pid) references p(id));
insert into p values (1);
insert into c values (1, 1, 0);
commit;
-- csql --no-auto-commit
update c set pid = 999 where id = 1;   -- ERROR: foreign key 'fk_c_pid' invalid
commit;
```

`cubrid heartbeat stop` 후 `cubrid diagdb -d 8` 로 로그를 덤프한다(대화형 입력 `1, -1, -1, -1, y`).

## Expected Result

FK 오류로 롤백된 UPDATE의 `LOG_REPLICATION_DATA` 레코드가 commit 로그 앞에 없다.

## Actual Result

```text
Type = LOG_REPLICATION_DATA, Target log lsa = -1|-1
T[RVREPL_DATA_UPDATE] C[] K[1]
Type = LOG_COMMIT
```

## Additional Information

- slave 영향의 실행 확인(2노드 HA에서 debug applylogdb core 여부와 release applylogdb 실패 건수)은 ANALYSIS에서 한다.
- 같은 순서가 `release/10.2`, `release/11.0`, `release/11.4` 에 있다. 이 버전들에서 실행 확인은 하지 않았다.
