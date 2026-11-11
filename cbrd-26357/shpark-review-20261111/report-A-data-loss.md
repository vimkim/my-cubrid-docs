# Tab A: shparkcubrid 리뷰 중 데이터 손실 블로킹 2건 검토

| 항목 | 값 |
| --- | --- |
| 대상 | CUBRID/cubrid#7990 리뷰 1번(inline 4385247867, `vacuum.c`, CBRD-27237), 3번(inline 4385247875, `oos_file.cpp`, CBRD-27781) |
| 기준 리비전 | `feature/oos-merge` = `67220b7e230ff1587ba5940001d72e10477a1fc4` (2026-11-11 `git fetch origin` 후 확인) |
| 수정 PR | #8434 `[CBRD-27781] Reclaim OOS chains only after the delete is final`, head `0d9732a6314e`, base `feature/oos-merge`, OPEN, Ready, H2SU APPROVED(2026-11-11), gha-ci build 통과·test 4종 진행 중(2026-11-11 조회) |
| 작성일 | 2026-11-11 (Asia/Seoul) |
| 방법 | 읽기 전용. 빌드·실행 없음. 소스는 `git show <rev>:<path>`로 읽음 |

근거 표시: **[코드 확인]** 고정 리비전 소스를 읽음, **[측정]** 이번에 실행한 결과(이번 조사에서는 없음, 인용만), **[인용-실행]** 기존 문서가 실행으로 확인한 결과, **[추론]** 코드에서 낸 판단.

## 0. 머지 조건으로 무엇을 걸었는가 (원문 확인)

| 시점 | 원문 | 의미 |
| --- | --- | --- |
| review 5662427700, CHANGES_REQUESTED, 2026-10-27 | "블로킹 이슈만 적었습니다. … 1. UPDATE를 rollback하면 … 3. … OOS 삭제의 undo가 다른 트랜잭션이 재사용한 슬롯을 덮어쓸 수 있습니다." | 1·3번 모두 #7990 블로킹으로 지정 |
| inline 4385247867 (1번) | "공간 누수가 아니라 데이터 손실이므로 **머지 전에** 고쳐야 합니다." | 처음 요구는 #7990 머지 전 |
| 후속 4386913472 (1번) | "CBRD-27237에서 별도로 진행하는 것은 좋습니다. 다만 일반 ROLLBACK에서 데이터가 사라지는 문제라서, **11.5 릴리스 전에는 반드시** 반영되어야 한다고 생각합니다. 수정 전까지는 develop을 쓰는 다른 팀 테스트에도 영향이 갈 수 있으니, 가능하면 빠르게 처리 부탁드립니다." | 별도 티켓 진행은 수용. 강제 기한은 11.5 릴리스. develop 영향을 이유로 빠른 반영을 요청 |
| 후속 4386916069 (3번) | "CBRD-27781에서 별도로 진행하는 것은 좋습니다. 다만 커밋된 데이터를 덮어쓸 수 있는 문제라서, **11.5 릴리스 전에는 반드시** 반영되어야 한다고 생각합니다." | 별도 티켓 진행은 수용. 강제 기한은 11.5 릴리스 |
| 비교: 2번 후속 4386842256 | "그래서 이 항목은 **블로킹에서 빼겠습니다**." | 2번은 명시적으로 블로킹 해제 |
| 대화 6461744209 (2026-10-28) | "이번 리뷰에서 나온 데이터 손실 문제(CBRD-27237, CBRD-27781)와 위 읽기 비용은 원인이 같아 보입니다 … 11.5로 나가면 디스크 형식이 굳어서 …" | 두 결함을 구조 검토 요청의 근거로 다시 언급. 머지 기준 3개 목록에는 넣지 않음 |

판단 [추론]:
- 리뷰어는 1·3번에 대해 "#7990 머지 전"을 "11.5 릴리스 전"으로 완화했다. 다만 2번처럼 "블로킹에서 빼겠다"고 명시하지 않았고, GitHub 리뷰 상태는 아직 CHANGES_REQUESTED다. 1번에는 "develop을 쓰는 다른 팀 테스트에도 영향"이라는 #7990 머지 시점과 연결된 우려도 남겼다.
- 따라서 "11.5 전이면 된다"를 작성자가 일방적으로 해석해 #7990을 먼저 머지하는 것은 위험하다. #8434가 이미 approve되어 있으므로, **#8434를 `feature/oos-merge`에 먼저 넣고 #7990을 머지하는 순서가 두 해석을 모두 만족시킨다.** 이 순서를 답글로 알리고 리뷰어에게 1·3번 해제를 확인받는다.
- 11.5 릴리스와 #7990의 관계(디스크 형식 고정 시점)도 #8434를 먼저 넣을 이유다. #8434는 chunk header를 32B로 바꾸는 형식 변경이며 `DISK_STORAGE_FORMAT_REVISION`을 올리지 않는다(ADR-0008 decision 6, #8434 본문). #7990이 develop에 먼저 들어가면 develop에서 만든 DB와 이후 형식이 어긋난다 [추론, #8434 본문 근거].

## 1. 리뷰 1번: UPDATE rollback 뒤 vacuum이 OOS 값을 지움 (CBRD-27237)

### 1.1 리뷰어 요구

inline 4385247867. vacuum이 UPDATE의 undo 이미지에 있는 OOS 참조를 commit 여부를 보지 않고 해제하므로, rollback으로 복원된 행이 지워진 chain을 가리킨다. 작은 컬럼만 바꾼 UPDATE, NULL로 바꾼 UPDATE, `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` 분기, kill -9 뒤 복구 undo, deadlock 희생, 연결 끊김 모두 해당. 머지 전 수정 요구(후속에서 11.5 전으로 완화, 0절).

### 1.2 67220b7 현재 상태: 결함이 그대로 있다

- `src/query/vacuum.c:3749-3751` (67220b7): `RVHF_UPDATE_NOTIFY_VACUUM`이면 `vacuum_forward_walk_reclaim_oos (thread_p, undo_data, …)`를 부른다. 이 분기에는 트랜잭션 commit 여부나 현재 행이 그 chain을 아직 가리키는지 보는 조건이 없다 [코드 확인].
- `src/query/vacuum.c:3889-3896` (67220b7): `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`(relocated 행 UPDATE)도 같은 forward-walk를 부른다 [코드 확인].
- `src/storage/heap_file.c:25593-25599` (67220b7): relocation 경로가 이 rcvindex를 남긴다 [코드 확인].
- vacuum은 loser(되돌린 트랜잭션)의 MVCC 레코드를 거르지 않는다. 재현은 `dcbf09e4f`에서 ROLLBACK, savepoint rollback 뒤 COMMIT, statement rollback 뒤 COMMIT, relocated 행, 연결 끊김, deadlock 희생, kill -9 복구 모두 값 손실로 확인됐다 [인용-실행: `my-cubrid-docs/cbrd-27237/CBRD-27237-fix-options-deep-dive_dcbf09e_claude.md` "시나리오별 결과" 표 1~8번].
- `dcbf09e4f` 이후 67220b7까지 `feature/oos-merge`에 들어간 OOS 관련 수정은 #8350(CBRD-27860, vacuum latch cycle), #8417(CBRD-27933, OOS 파일 조회 실패 누수), #8485(test helper), #8299(CBRD-27785, 읽기·UPDATE CPU)다. 어느 것도 forward-walk 분기를 바꾸지 않는다. 위 두 호출이 67220b7에 그대로 있다 [코드 확인: `git log --first-parent 67220b7`, 위 줄 번호].
- 리뷰어 지적처럼 기존 TC-02(`test_oos_sql_txn.cpp`)는 rollback 직후만 보므로 결함을 잡지 못한다 [리뷰어 주장, 이번에 재확인하지 않음].

리뷰어 지적은 타당하다. 작은 컬럼 UPDATE가 해당한다는 주장도 맞다. 67220b7의 UPDATE는 바뀌지 않은 OOS 값도 새 chain으로 다시 쓰고(CBRD-27230 미구현, PR 대화 6441306406의 작성자 답변), 그 결과 옛 chain OID는 undo 이미지에만 남아 forward-walk 대상이 된다 [추론].

### 1.3 수정 PR: 별도 PR은 없고 #8434가 함께 고친다

`my-cubrid-docs/cbrd-27237/README.md`는 "No PR exists yet"(2026-11-03)이지만, 이후 `cbrd-27781/README.md`가 "CBRD-27781 … and the companion CBRD-27237 … implemented together under ADR-0008. PR: CUBRID/cubrid#8434"로 바꿨다. #8434 본문 Purpose 첫 줄도 두 티켓을 함께 적는다.

#8434(head `0d9732a`)의 처리 [코드 확인]:
- forward-walk와 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`이 소스에서 사라졌다. `git grep "vacuum_forward_walk_reclaim_oos\|RVHF_DELETE_NEWHOME_NOTIFY_VACUUM" 0d9732a -- src` 결과 0건.
- UPDATE는 버린 chain을 `RVOOS_UPDATE_DROP_POSTPONE` postpone으로 남긴다. 일반 경로와 relocation 경로 모두 `heap_oos_log_update_drop`을 부른다(`src/storage/heap_file.c:25359`, `:25835` @`0d9732a`). postpone 등록은 `src/storage/oos_file.cpp:3984` @`0d9732a`.
- commit의 postpone 실행이 UPDATE의 MVCCID로 `RVOOS_NOTIFY_VACUUM`을 남기고, vacuum은 이 알림만 소비한다(`src/query/vacuum.c:3878` @`0d9732a`).

리뷰어 시나리오를 이 코드 경로로 따라가면 [추론, 일부 단위 테스트로 확인]:

| 리뷰어 시나리오 | 67220b7 | #8434 (`0d9732a`) | 근거 |
| --- | --- | --- | --- |
| UPDATE big 뒤 ROLLBACK | 손실 | 보존. postpone이 실행되지 않아 알림이 없음 | 단위 테스트 `OosRealVacuumUpdateNotify.RolledBackUpdateKeepsTheRestoredVersionsChainThroughVacuum`(storage API 수준, real vacuum) |
| UPDATE k(작은 컬럼) 뒤 ROLLBACK | 손실 | 보존. heap 수준에서는 위와 같은 경로(새 chain 쓰기 + 옛 chain drop postpone) | 추론. 같은 `heap_update` 경로라 별도 분기 없음 |
| UPDATE big=NULL 뒤 ROLLBACK | 손실 | 보존. 새 chain만 없고 drop postpone은 같음 | 추론 |
| savepoint/statement rollback 뒤 COMMIT | 손실 | 보존. 되돌린 범위의 postpone은 실행되지 않음 | 단위 테스트 `SavepointRolledBackUpdateKeepsItsChainAndLaterCommitDoesNotReclaimIt` |
| relocated 행 UPDATE 뒤 ROLLBACK | 손실 | 보존. relocation도 drop postpone 사용 | `heap_file.c:25835` @`0d9732a` [코드 확인], 실행 테스트는 확인 못 함 |
| 미커밋 UPDATE 중 kill -9 → 복구 undo → vacuum | 손실 | 보존. `LOG_COMMIT_WITH_POSTPONE`이 없으면 복구가 postpone을 실행하지 않음 | 추론. SQL crash 테스트는 commit 도중 crash(`test_oos_server_crash_recovery`)와 회수 실패(`FailedCommitReclaimStopsAndRestartRecoveryFinishesIt`)만 있음 |
| deadlock 희생, 연결 끊김 | 손실 | 보존. abort 경로라 위와 같음 | 추론 |
| UPDATE 뒤 COMMIT(누수 확인) | 회수 | 회수 | `CommittedUpdateReturnsThePageItsDroppedChainEmptied` |

### 1.4 판정

- 67220b7(#7990 현재 head): **미충족** [코드 확인].
- #8434 머지 후: **충족 예상**. 설계가 리뷰어가 지적한 두 원인(commit 확인 없음, undo 이미지 기반 회수)을 모두 제거한다 [코드 확인 + 추론]. 다만 리뷰어가 쓴 SQL 재현 자체를 #8434 head에서 돌린 기록은 찾지 못했다(`my-cubrid-docs` 검색, 2026-11-11).

### 1.5 남은 일

1. #8434 gha-ci(test_medium/shell/sql/sql_by_cci 진행 중) 완료 확인 후 `feature/oos-merge`에 머지. `git merge-tree 67220b7 0d9732a`는 충돌 없음 [측정: 이번 조사에서 실행한 `git merge-tree`]. 크기: `src/` 아래 21 files, +2227/−1459(`git diff --stat 67220b7 0d9732a -- src`), 테스트 변경은 별도. 위험: 큰 recovery·vacuum 변경이라 머지 뒤 feature 브랜치 CI 한 번은 필수.
2. 리뷰어 SQL 재현을 #8434가 반영된 `feature/oos-merge`에서 한 번 실행해 답글에 붙인다(작은 공수, 1시간 안팎). 표의 네 행과 kill -9 행을 그대로 쓴다. 30,000자 무작위 문자열, 다른 테이블 commit 몇 번 뒤 `vacuumdb` 또는 vacuum 대기 → `select length(big)`이 30000인지 확인. 이번 조사는 실행하지 않았다(읽기 전용 규칙).
3. (선택) 작은 컬럼·NULL UPDATE rollback과 미커밋 kill -9 경우를 SQL 단위 테스트로 남기면 리뷰어의 "TC-02가 못 잡는다" 지적도 닫힌다. 작은 크기.

### 1.6 답글 초안 (게시하지 않음)

> CBRD-27237은 CBRD-27781과 같은 설계(ADR-0008)로 [#8434](https://github.com/CUBRID/cubrid/pull/8434)에서 함께 고쳤습니다. vacuum이 UPDATE의 undo 이미지를 따라 OOS chain을 지우던 forward-walk와 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` 분기를 없앴습니다. UPDATE는 버린 chain을 postpone으로만 남기고, commit이 확정된 뒤에만 그 UPDATE의 MVCCID로 vacuum 알림을 기록합니다. 그래서 명시적 ROLLBACK, savepoint/statement rollback, deadlock 희생, 연결 끊김, 미커밋 상태의 서버 장애 뒤 복구 undo에서는 알림이 남지 않고 chain도 지워지지 않습니다. 작은 컬럼이나 NULL로 바꾸는 UPDATE, relocated 행도 같은 경로를 탑니다.
>
> #8434는 approve를 받았고 CI가 끝나는 대로 `feature/oos-merge`에 먼저 넣은 뒤 이 PR을 머지하려고 합니다. 반영 후 주신 SQL 재현(표의 네 경우와 kill -9 경우)을 그대로 돌려 결과를 여기에 붙이겠습니다. 이 순서로 1번 블로킹을 해제해 주실 수 있을지 확인 부탁드립니다.

## 2. 리뷰 3번: OOS 삭제 undo가 재사용된 슬롯을 덮어씀 (CBRD-27781)

### 2.1 리뷰어 요구

inline 4385247875(코드로만 확인). OOS 페이지가 `ANCHORED`, `is_saving=false`로 초기화되어 `oos_delete_chain`이 지운 슬롯·공간을 다른 트랜잭션이 바로 가져갈 수 있고, `oos_stats_update`가 bestspace에 즉시 공개한다. `RVOOS_DELETE`의 undo(`oos_rv_redo_insert`)는 슬롯이 비었다고 가정하므로 vacuum sysop abort, sysop 도중 crash 뒤 복구 undo, 비 MVCC 즉시 삭제(SA, in-place update)에서 다른 트랜잭션이 커밋한 값을 덮거나 rollback이 실패한다. `ANCHORED_DONT_REUSE_SLOTS` 또는 삭제 트랜잭션 종료까지 공간 예약을 요구.

### 2.2 67220b7 현재 상태: 결함이 그대로 있다

- `src/storage/oos_file.cpp:3159` (67220b7): `spage_initialize (thread_p, page, ANCHORED, OOS_ALIGNMENT, false)`. heap은 `ANCHORED_DONT_REUSE_SLOTS`(`heap_file.c:1144`)인데 OOS는 아니다 [코드 확인].
- `src/storage/oos_file.cpp:3206` (67220b7): 삭제가 `log_append_undoredo_recdes (thread_p, RVOOS_DELETE, …, recdes_p, NULL)`로 전체 레코드를 undo 데이터로 남긴다 [코드 확인].
- `src/transaction/recovery.c:887-890` (67220b7): `RVOOS_DELETE`의 undo 함수가 `oos_rv_redo_insert`다 [코드 확인].
- `src/storage/oos_file.cpp:3377` (67220b7): `oos_delete_chain` 안에서 `oos_stats_update`를 부른다 [코드 확인].
- 67220b7의 LSA reclaim gate(`oos_file.cpp:1555` 주석 근처, `OOS_RECLAIM_DEFERRED`)는 빈 **페이지** 반환만 미루고 슬롯 재사용은 막지 않는다. 주석이 직접 "abort replays RVOOS_DELETE undo"를 적는다 [코드 확인].
- 67220b7까지 들어간 수정 중 #8350(CBRD-27860)은 latch cycle, #8417(CBRD-27933)은 OOS 파일 조회 실패 누수를 다룬다. 둘 다 위 undo 경로를 바꾸지 않는다 [코드 확인: 위 줄이 67220b7에 그대로 있음].
- 같은 종류의 heap 쪽 결함(relocation forward slot, CBRD-27858, #8348)은 OPEN이며 hornetmj 리뷰 R5 항목이다. shpark 3번의 범위 밖이지만 같은 "vacuum undo가 재사용 슬롯에 씀" 계열이다 [`gh pr view 8348`: OPEN].

리뷰어 지적은 타당하다. 재현은 리뷰어도 하지 않았고 이번에도 하지 않았지만, 코드상 undo가 빈 슬롯을 가정하는 경로가 명확하다 [추론].

### 2.3 #8434가 리뷰어 시나리오를 덮는가

#8434(head `0d9732a`)는 리뷰어가 제안한 두 방법(DONT_REUSE_SLOTS, 공간 예약) 대신 **되돌릴 삭제를 없애는** 방법을 택했다 [코드 확인]:
- `src/transaction/recovery.c:887-890` @`0d9732a`: `RVOOS_DELETE`의 undo 함수가 `NULL`. redo-only.
- `src/storage/oos_file.cpp:3326` @`0d9732a`: `log_append_redo_data (thread_p, RVOOS_DELETE, …)`. undo 이미지를 남기지 않는다.
- `src/storage/oos_file.cpp` @`0d9732a`에 남은 undo 가능한 OOS 레코드는 `RVOOS_INSERT`(`:3306`) 하나다. 그 undo는 자기가 넣은 슬롯을 지우는 것이라 재사용 슬롯에 쓰지 않는다 [코드 확인].
- 삭제 결정은 `RVOOS_RECLAIM_POSTPONE`(`:3936`) 회수 의도로만 남고, 결정한 단위(vacuum sysop 또는 트랜잭션)가 commit한 뒤 postpone에서 tail→head 순서로 지운다. 페이지 초기화는 여전히 `ANCHORED`(`:3268`)지만, commit 뒤 지운 슬롯은 되돌릴 일이 없으므로 재사용해도 된다 [코드 확인 + 추론].

리뷰어 시나리오별 [추론, 일부 단위 테스트로 확인]:

| 시나리오 | 67220b7 | #8434 | 근거 |
| --- | --- | --- | --- |
| vacuum sysop 중간 abort(shutdown 인터럽트, I/O 오류) | 재사용 슬롯 덮어쓰기 가능 | 의도 폐기. chunk는 아직 안 지워졌으므로 복원할 것이 없음 | `OosIdentityStampTest.SysopAbortDiscardsTheReclaimIntentEvenWhenTheTransactionCommits`, `OosReclaimTest.EnclosingAbortRestoresNoReclaimedChunkEvenAfterSlotReuse` |
| vacuum sysop 도중 crash → 복구 undo | 같음 | sysop commit 전이면 의도 폐기. commit 뒤 postpone 도중이면 복구가 남은 prefix를 다시 회수하고 재사용 슬롯 링크는 따라가지 않음 | `RerunAfterAReclaimInterruptedPartWayFinishesTheChain`, `RerunDoesNotFollowALinkIntoASlotALaterInsertReused` |
| SA/비 MVCC 즉시 삭제, in-place update | 같음 | DML 때 의도만 남기고 commit에서 회수. abort는 의도 폐기 | #8434 본문 Implementation "회수 의도", `IntentOfAnAbortedUnitIsDiscardedAndOfACommittedUnitReclaims` |
| 회수 자체가 실패 | — | fail-stop(`logpb_fatal_error`) 후 재시작 복구가 재실행 | `FailedCommitReclaimStopsAndRestartRecoveryFinishesIt` |

추가로 TLA+ 모델(`cubrid-verify-vacuum-slot-undo` 갱신본)에서 OOS chunk undo 성질은 undo 가능한 chunk 삭제가 없어 공허하게 통과, `OosReclaimDeletesOnlyItsChain`·`OosReclaimFinishesChain` 통과로 기록돼 있다 [인용, #8434 본문 Remarks. 모델 범위 한정].

#8434의 리뷰 이력: 3e8072f 5인 리뷰 R1~R10 처리, 8e139f4 후속 리뷰 "확인된 결함 없음", 남은 U-1(growth lock 처리량)은 측정으로 회귀 없음(`my-cubrid-docs/cbrd-27781/perf-growth-lock.md`) [인용]. 분리된 후속 이슈 CBRD-27981(NULL snapshot reader, 낮은 실제 위험), CBRD-27982, CBRD-28012, CBRD-28035, CBRD-28036은 리뷰어 3번 시나리오와 다른 결함이다 [인용, `cbrd-27781/README.md`].

### 2.4 판정

- 67220b7: **미충족** [코드 확인].
- #8434 머지 후: **충족 예상**. 리뷰어가 든 세 경로가 모두 "되돌릴 OOS 삭제 없음"으로 닫힌다 [코드 확인 + 단위 테스트 인용].

### 2.5 남은 일

1. 1.5의 1번과 같다(#8434 CI 완료 → `feature/oos-merge` 머지 → feature CI).
2. 리뷰어가 제안한 방법과 다른 방법을 썼으므로, 답글에 "왜 DONT_REUSE_SLOTS가 아니라 redo-only + commit 후 회수인가"를 짧게 설명한다. 크기 없음.
3. 리뷰어에게 #8434 리뷰를 직접 요청할지 결정(선택). 리뷰어가 "코드로만 확인"한 항목이므로 코드로 확인받는 것이 가장 확실하다. 위험: #8434 머지가 늦어질 수 있음.

### 2.6 답글 초안 (게시하지 않음)

> CBRD-27781은 [#8434](https://github.com/CUBRID/cubrid/pull/8434)에서 고쳤습니다(ADR-0008). 슬롯 재사용을 막거나 공간을 예약하는 대신, 되돌릴 수 있는 OOS 삭제 자체를 없앴습니다.
>
> - vacuum REMOVE와 SA/비 MVCC 즉시 정리는 chunk를 바로 지우지 않고 회수 의도(`RVOOS_RECLAIM_POSTPONE`)만 남깁니다. 삭제를 결정한 sysop이나 트랜잭션이 commit한 뒤 postpone에서 chunk를 지웁니다. abort하면 의도만 버려지고 chunk는 원래 자리에 그대로 있습니다.
> - `RVOOS_DELETE`는 redo-only가 되어 undo가 없습니다. 그래서 sysop abort, 복구 undo, in-place update 경로 모두 재사용된 슬롯에 옛 chunk를 다시 쓰지 않습니다.
> - commit 뒤 회수가 중간에 멈추면 재시작 복구가 남은 부분을 다시 회수하며, 그 사이 재사용된 슬롯으로 이어진 링크는 next-chunk stamp로 걸러 따라가지 않습니다. 회수가 실패하면 서버를 멈추고 재시작에서 마무리합니다.
>
> 재사용된 슬롯이 있는 상태에서 바깥 abort를 해도 복원이 일어나지 않는지, 중단 후 재실행이 재사용 슬롯을 건드리지 않는지는 `test_oos_reclaim`에 테스트로 넣었습니다. #8434를 `feature/oos-merge`에 먼저 반영한 뒤 이 PR을 머지하려고 합니다. 3번도 이 순서로 해제해 주실 수 있을지 확인 부탁드립니다. 코드로 직접 보시려면 #8434 리뷰도 환영합니다.

## 3. 항목 요약

| 항목 | 67220b7 | #8434 반영 후 | 판정(#7990 현재) | 남은 일 |
| --- | --- | --- | --- | --- |
| 1번 CBRD-27237 | 결함 있음 [코드 확인] | 해결 예상 [코드 확인 + 추론] | 미충족 | #8434 머지, 리뷰어 SQL 재현 재실행, 리뷰어 해제 확인 |
| 3번 CBRD-27781 | 결함 있음 [코드 확인] | 해결 예상 [코드 확인 + 단위 테스트 인용] | 미충족 | #8434 머지, 설계 선택 설명, 리뷰어 해제 확인 |
| 머지 조건 해석 | — | — | 팀 결정 필요 | 리뷰어 원문은 "11.5 전 반드시"로 완화했으나 블로킹 해제를 명시하지 않음. #8434를 먼저 넣으면 해석 차이가 사라짐 |

## 가장 중요한 결론 3줄

1. 두 데이터 손실 결함은 #7990 현재 head `67220b7`에 그대로 있다(`vacuum.c:3751`·`:3896` forward-walk, `oos_file.cpp:3206` + `recovery.c:889` undo가 있는 `RVOOS_DELETE`). 이미 들어간 #8350·#8417·#8299는 이 경로를 바꾸지 않는다.
2. 별도 CBRD-27237 PR은 없고, approve된 #8434(head `0d9732a`, 충돌 없음, CI 진행 중)가 forward-walk 제거 + commit 후 postpone 회수 + redo-only 삭제로 두 결함을 함께 닫는다. 리뷰어 시나리오는 코드 경로와 단위 테스트로 덮이지만, 리뷰어 SQL 재현을 #8434 위에서 돌린 기록은 아직 없다.
3. 리뷰어는 기한을 "#7990 머지 전"에서 "11.5 릴리스 전"으로 완화했지만 블로킹 해제를 명시하지 않았다. #8434를 `feature/oos-merge`에 먼저 넣고 SQL 재현 결과와 함께 해제를 요청하는 순서가 가장 안전하다.
