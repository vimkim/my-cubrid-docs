# CBRD-27230 리뷰에서 나온 복제 marker 분리 버그를 왜 놓쳤고 어떻게 미리 찾을까

- 작성 2026-11-18. 대상 PR [#8559](https://github.com/CUBRID/cubrid/pull/8559), 수정 전 head `86045b2b4d`, 수정 커밋 `7e73eafc63`, base `2c38bef05b` (`feature/oos-merge`).
- 리뷰 원문: [discussion_r4612636698](https://github.com/CUBRID/cubrid/pull/8559#discussion_r4612636698) (hornetmj).
- 방법: 읽기 전용 소스 분석. 빌드나 테스트는 돌리지 않았다. 근거 표기는 **[확인]** 소스나 grep 결과로 확인, **[추론]** 소스에서 추론, **[추측]** 보지 않은 가설이다.

## 1. 요약

- 버그의 원인은 새 레코드 종류 `RVREPL_OOS_REUSE` 가 `lsa` 와 `inst_oid` 를 NULL로 둔 것이다. 이 두 필드로 결정을 내리는 기존 코드는 수정 전 `replication.c` 에 세 곳뿐이었다. 그중 두 곳이 리뷰가 지적한 두 경로다 [확인].
- 기존 검증이 놓친 공통 이유는 세 가지다. 복제 레코드는 HA가 켜져야 생기는데, HA를 켠 테스트는 savepoint나 flush mark를 거치지 않았다. TLA+ 모델은 복제를 범위 밖에 두었다. 실제 HA 실행은 하지 않았다.
- 가장 싸고 이번 버그에 확실히 걸렸을 방법은 **필드 독자 열거**다. 새 레코드가 NULL이나 기본값으로 두는 필드마다, 그 필드를 읽고 분기하는 코드를 grep으로 모두 찾는다. 몇 분이면 끝난다.
- 다음은 **생명주기 매트릭스 테스트**다. 이미 있는 `replication_tracking_guard` 로 OOS 항목 종류와 `must_flush` 를 바꾸는 경로의 모든 조합을 시험한다. 수정 커밋의 테스트 두 개가 이 표의 두 칸이다.
- 남은 같은 계열 버그를 짧게 찾았다. PR이 만든 것은 찾지 못했다. base에 있던 것으로 보이는 문제 하나를 plausible로 남긴다 (§4).
- 구조로 남길 것은 두 가지다. debug invariant `repl_assert_oos_items_follow_row` 와 기존 OOS 롤백 테스트를 HA 추적을 켠 채로 한 번 더 돌리는 fixture다. 그리고 `cubrid-code-review` 의 HA 리뷰어에 "새 레코드의 NULL 필드 독자 열거" 항목을 넣는다.

## 2. 버그 한 줄 정리

slave는 행의 OOS 항목(`RVREPL_OOS_INSERT`, `RVREPL_DUMMY_OOS_RECORD`, `RVREPL_OOS_REUSE`)을 바로 뒤 행과 한 묶음으로 반영한다. 그래서 master는 이 항목들을 행과 같은 `must_flush` 로 기록하거나 버려야 한다. 수정 전에는 각 항목의 `lsa` 와 `inst_oid` 가 그 결정을 내렸다.

| 경로 | 결정 코드 (수정 전 `86045b2b4d`) | marker에서 일어난 일 |
|---|---|---|
| savepoint 롤백, 문장 롤백 | `repl_log_abort_after_lsa`: `LSA_GT (&repl_rec_arr[i].lsa, start_lsa)` (`replication.c:771`) | NULL lsa는 항상 거짓이다. 행만 버려지고 marker는 commit 때 기록된다 |
| flush mark (`SELECT ... INCR`, `qexec_execute_selupd_list`) | `OID_EQ (&recsp[i].inst_oid, &repl_rec->inst_oid)` (`replication.c:508`) | 앞서 남은 marker의 NULL OID와 같다고 본다. marker는 commit까지 미뤄지고 행만 먼저 기록된다 |

marker의 NULL OID는 `heap_oos_publish_reused_in_order` 가 넣는다 (`heap_oos.cpp:175`, `{ oid_Null_oid, NULL_LSA, true }`). NULL lsa는 `repl_log_insert_internal` 이 넣는다 (`replication.c:488-491` at `86045b2b4d`).

## 3. 기존 검증이 놓친 이유

| 검증 | 실제로 확인한 것 | 놓친 이유 |
|---|---|---|
| OOS ctest 69/69 | OOS chain, 회수, 스냅샷, 롤백 | 복제 레코드는 HA가 켜져야 생긴다 (`log_does_allow_replication`, `log_comm.c:297` 의 `HA_DISABLED ()`). HA 추적을 켠 테스트는 셋뿐이다. `test_oos_server.cpp:631`, `:660` 과 reuse 테스트의 `ReplicatesAReusedColumnAsAMarkerInAttributeOrder` 다. 셋 다 savepoint나 flush mark를 거치지 않는다 [확인] |
| `ReplicatesAReusedColumnAsAMarkerInAttributeOrder` | 항목의 rcvindex 순서와 marker의 NULL lsa | marker의 NULL lsa를 맞는 동작으로 assert했다 (`test_oos_update_reuse_server.cpp:739` at `86045b2b4d`, "a marker points at no OOS insert"). 버그의 원인이 테스트 기대값이었다. `must_flush` 는 보지 않았다. 트랜잭션은 `scope_exit` 의 abort로 끝나서 commit 때 기록하는 경로도 돌지 않았다 [확인] |
| `PartialRollbackCancelsOnlyTheLaterDrop` | savepoint 뒤 UPDATE의 알림 취소, chain 생존 | 리뷰의 경우 1과 같은 동작을 한다. savepoint 뒤 `update_row (oid, &k, nullptr, nullptr)` 가 c1과 c2를 재사용한다 (`:651`). 그러나 HA가 꺼져 있어 복제 레코드가 없었다 [확인] |
| `IncrementReusesTheOtherColumnsChains` | increment가 다른 열의 chain을 재사용 | `locator_force` 를 직접 부른다. flush mark는 `qexec_execute_selupd_list` 가 건다 (`query_executor.c:20803`). 테스트는 이 경로를 거치지 않고 HA도 꺼져 있다 [확인] |
| crash recovery 테스트 | 재시작 뒤 chain과 행 | `tdes->repl_records` 는 메모리에만 있다. crash가 나면 사라지므로 확인할 대상이 없다 [추론] |
| TLA+ `OosChainReuse.tla` (안전 3, liveness 1, 통제 9) | chain 생존, 잘못된 회수, 알림 | chain을 `<<slot, stamp>>` 하나로 추상화했다. design §9 한계에 "복제 ... 은 모델 밖이다"라고 적었다. 통제 9개는 작성자가 고른 결정을 하나씩 되돌린다. 모델에 없는 규칙(`LSA_GT`, `OID_EQ`)은 통제로 찾을 수 없다 [확인] |
| 실제 HA, applylogdb | 없음 | PR body에 "미검증"이라 적었다 (`pr-body.md:22`). design §10의 HA 계획 시나리오(재사용 UPDATE, 혼합 UPDATE, replica 불일치)에는 savepoint 롤백, 문장 롤백, `SELECT INCR` 이 없다. 계획대로 돌렸어도 걸리지 않았을 것이다 [추론] |

공통 원인. design은 marker의 NULL lsa를 일부러 골랐다 (`design-a-prime-detail.md:142`, "LSA 없는 `RVREPL_OOS_REUSE`"). 그러면서 replica 쪽 소비자(위치 계약, fixup)는 자세히 따졌다. master 쪽에서 메모리 레코드의 `lsa` 와 `inst_oid` 를 읽는 코드는 따지지 않았다.

## 4. 미리 찾는 방법, 비용 대비 효과 순

"이번 버그에 걸렸나"는 수정 전 `86045b2b4d` 기준이다.

| 순위 | 방법 | 비용 | 이번 버그에 걸렸나 | 근거 |
|---|---|---|---|---|
| 1 | 필드 독자 열거. 새 레코드 종류가 NULL이나 기본값으로 두는 필드를 적는다. 그 필드를 읽고 분기하는 코드를 모두 grep으로 찾는다 | 몇 분 | 예, 두 경로 모두 [확인] | 아래 grep 결과는 결정 독자 3곳이다. `:255` 는 행 OID로만 찾으므로 안전하다. `:508` 이 경우 2, `:771` 이 경우 1이다 |
| 2 | 생명주기 매트릭스 테스트. 행은 OOS 항목 종류 셋, 열은 `must_flush` 나 `cur_repl_record` 를 바꾸는 경로다. 칸마다 `replication_tracking_guard` 로 시험한다 | 몇 시간. harness가 이미 있다 | 예 [확인] | 수정 커밋의 `SavepointRollbackDropsTheMarkersWithTheirRow` 와 `FlushMarkWritesTheOosItemsWithTheirRow` 가 이 표의 두 칸이다. 리뷰어도 같은 harness로 확인했다 |
| 3 | debug invariant. OOS 항목마다 바로 뒤 행과 `must_flush` 가 같아야 한다 | 30줄 안팎, debug 빌드만 | 기존 테스트만으로는 아니오. HA 추적을 켠 `PartialRollbackCancelsOnlyTheLaterDrop` 이 있었다면 예 [추론] | HA를 켠 기존 테스트는 savepoint도 flush mark도 거치지 않는다. invariant는 시나리오를 대신하지 못한다. 대신 앞으로 돌리는 모든 HA 테스트와 shell 테스트를 검사기로 만든다 |
| 4 | 리뷰 checklist나 prompt. HA 리뷰어에게 "새 레코드의 NULL 필드마다 그 필드를 읽는 코드"를 묻는다 | 리뷰마다 적음 | 리뷰어가 grep을 하면 예 | 방법 1을 사람이나 agent에게 맡기는 것이다. 지금 `cubrid-code-review` HA 리뷰어 항목(`references/reviewers.md:102-113`)에는 ordering과 partial application은 있지만 이 질문은 없다 [확인] |
| 5 | HA 2대 shell 테스트, applylogdb 실행 | 하루. 2노드 구성, `cubrid-test-shell-run` | 시나리오에 savepoint 롤백, 문장 롤백, `SELECT INCR` 가 있을 때만 예 [추론] | slave가 멈추는 것은 실제 증상이다. 하지만 어떤 시나리오를 넣을지는 방법 1, 2가 알려 준다 |
| 6 | TLA+ 모델을 복제 레코드 배열까지 확장 | 하루 이상 | `LSA_GT` 와 `OID_EQ` 규칙을 그대로 모델링하면 예 [추론] | 모델러가 그 두 규칙이 중요하다는 것을 먼저 알아야 한다. 그 지식은 방법 1의 결과다. 방법 1, 2보다 비싸고 더 찾는 것이 없다 |

방법 1을 그대로 다시 돌리는 명령. 수정 전 소스에서 결정을 내리는 독자는 `:255`, `:508`, `:771` 이다.

```sh
git show 86045b2b4d:src/transaction/replication.c | grep -n "inst_oid\|\.lsa\|->lsa"
grep -n "repl_rec->lsa\|repl_rec->inst_oid" src/transaction/log_manager.c   # :4778, wire로 복사만 한다
```

방법 2의 열을 뽑는 명령. 나온 쓰기마다 칸이 하나다.

```sh
grep -n "must_flush =\|cur_repl_record = \|append_repl_recidx" src/transaction/replication.c src/transaction/log_manager.c
```

이 명령으로 나오는 경로: 레코드 추가와 flush mark (`replication.c:501-524`), sysop abort를 거치는 savepoint와 문장 롤백 (`log_manager.c:4242`, `log_abort_partial` 에서 `log_sysop_abort`, `:5839`), `repl_end_flush_mark (need_undo)` 의 잘라내기 (`replication.c:744-753`), sysop commit 때 일부 기록 (`log_manager.c:4069`, `:4732-4797`), commit 때 전부 기록 (`log_append_repl_info_and_commit_log`), 트랜잭션 abort.

## 5. 같은 계열 버그 찾기 (제한된 범위)

방법 1과 2의 열거를 HEAD `7e73eafc63` 에 다시 적용했다. 범위는 이 PR이 더한 레코드 종류(`RVREPL_OOS_REUSE` 하나, `recovery.h:212`)와 같은 묶음 계약을 따르는 `RVREPL_DUMMY_OOS_RECORD` 다.

1. **[확인] PR이 만든 남은 결정 독자는 없다.** `replication.c:257` (`repl_add_update_lsa`) 는 행 OID로만 찾는다. marker의 NULL OID는 행 OID와 같을 수 없고, 같으면 그 자리 assert가 터진다. flush mark 루프는 OOS 항목을 건너뛴다 (`replication.c:501`). abort는 행을 따라간다 (`:784-796`).
2. **[확인] 소비자 짝이 맞다.** `RVREPL_OOS_INSERT` 나 `RVREPL_DUMMY_OOS_RECORD` 를 처리하는 switch마다 `RVREPL_OOS_REUSE` 도 있다. `tde.h:149`, `log_manager.c:6851`, `log_applier.c:5879`, `:7040`, `recovery.c` 의 `RV_fun` 이다. applier의 복제 filter는 항목과 행에 같은 class 이름을 쓰므로 함께 거른다 (`la_need_filter_out`, `log_applier.c:9021`).
3. **[plausible, base 문제] 행 레코드 자신이 NULL lsa로 롤백을 살아남을 수 있다.** `RVREPL_DATA_UPDATE` 는 `locator_update_index` 에서 NULL lsa로 남는다 (`locator_sr.c:10593`, `replication.c:462`). lsa는 그 뒤 `repl_add_update_lsa` 에서 채워진다 (`locator_sr.c:7439`). 그 사이 외래 키 검사가 실패하면 (`locator_sr.c:7417`) 행 레코드는 NULL lsa로 남는다. 그러면 `LSA_GT` 를 빠져나가 commit 때 기록된다. 이 순서는 base `2c38bef05b` 에도 있다 (CBRD-27463, #8198). 수정 전에는 OOS 항목(진짜 LSA)만 버려지고 행이 남았다. 수정 후에는 항목이 행을 따라 함께 남는다. 어느 쪽이든 원인은 행의 NULL lsa이고 이 PR이 만든 것은 아니다. 확인 방법: 같은 harness에서 savepoint 뒤 외래 키를 어기는 UPDATE를 하고 롤백 뒤 `must_flush` 를 본다. develop은 보지 않았다.
4. **[추측] applier 진행 위치.** `committed_rep_lsa` 는 OOS 항목마다 앞으로 간다 (`log_applier.c:7070`). marker와 행 사이에서 applier가 멈추고 다시 시작하면 marker를 건너뛸 수 있다. `RVREPL_OOS_INSERT` 에도 있던 문제다. 보지 않았다.
5. **[추측] applier의 즉시 flush.** `la_flush_repl_items (true)` 는 `pending_oos_flush` 를 무시한다 (`log_applier.c:5707`). 항목과 행 사이에 즉시 flush가 끼면 행 없이 flush될 수 있다. master가 이제 둘을 같은 묶음에 쓰므로 그 사이에 경계가 생기는지가 관건이다. 보지 않았다.

## 6. 구조로 남길 것 (제안, 만들지 않음)

### 6.1 debug invariant와 HA 추적 fixture

`replication.c` 에 debug 빌드 전용 검사를 둔다.

```c
#if !defined (NDEBUG)
/* Every OOS item takes the must_flush of the next non-OOS record (its row). Only trailing items of a row being
 * logged may lack a row. */
static void repl_assert_oos_items_follow_row (const LOG_TDES * tdes, bool allow_trailing);
#endif
```

부르는 곳은 `repl_log_insert_internal` 끝, `repl_log_abort_after_lsa` 끝, `repl_end_flush_mark` 끝, `log_append_repl_info_internal` 시작이다. 레코드가 바뀌는 곳에서 검사하므로 commit까지 가지 않아도 터진다.

invariant만으로는 이번 버그를 잡지 못했다. HA를 켠 테스트가 그 경로를 거치지 않았기 때문이다 (§4 방법 3). 그래서 `replication_tracking_guard` 를 OOS 테스트 공용 fixture로 옮긴다. 롤백, increment, 파티션 이동 테스트를 HA 추적을 켠 채로 한 번 더 돌린다. 그러면 `PartialRollbackCancelsOnlyTheLaterDrop` 이 수정 전 코드에서 invariant를 터뜨렸을 것이다 [추론]. 테스트를 새로 짜지 않고 기존 시나리오가 검사기를 얻는다.

### 6.2 새 레코드 종류 checklist를 `cubrid-code-review` HA 리뷰어에

`references/reviewers.md` 의 HA 리뷰어 항목에 한 줄을 더한다.

> 새 log 레코드나 복제 레코드 종류마다, 그것이 NULL이나 기본값으로 두는 필드를 적어라. 그 필드를 읽고 분기하는 코드를 모두 grep으로 찾아 file:line으로 보고하라. 그리고 그 종류가 `must_flush` 를 바꾸는 모든 경로(레코드 추가, flush mark, sysop abort와 savepoint, sysop commit, commit, abort)를 거칠 때 짝 레코드와 함께 움직이는지 표로 보여라.

리뷰 판단이 필요한 부분이라 lint로 만들 수는 없다. 그래서 실패 예(이 버그)를 함께 적는다.

## 7. 한계

- 빌드와 테스트를 돌리지 않았다. §4와 §6의 "걸렸을 것이다"는 소스 추론이다. 수정 커밋의 테스트 두 개가 방법 2의 실측 대리 증거다.
- §5는 제한된 범위의 탐색이다. 복제 외 경로(CDC, flashback)는 보지 않았다.
