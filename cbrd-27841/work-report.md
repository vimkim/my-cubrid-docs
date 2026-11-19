# CBRD-27841 보고: `RVREPL_OOS_DELETE` 제거

작성 2026-11-19 (Asia/Seoul). 이 파일은 커밋하지 않는다.

## 목표와 결과

목표: PR #7990이 develop에 병합되기 전에, 로그를 기록하는 코드가 없는 recovery index `RVREPL_OOS_DELETE`(140)를 `feature/oos-merge`에서 지운다. `RVOOS_NOTIFY_VACUUM`은 유지한다. CBRD-27841을 이 범위로 다시 쓰고, draft PR을 열고 CI를 시작한다.

결과:

- Draft PR: https://github.com/CUBRID/cubrid/pull/8646 (base `feature/oos-merge` `d25c9e8d20`, head `1d86f1d31b`, assignee vimkim)
- CI: https://github.com/CUBRID/cubrid/actions/runs/44501180486 (`/run all`, 09:57:40Z UTC, 6개 `gha-ci` context 모두 pending에서 시작. 완료는 기다리지 않음)
- JIRA: https://jira.cubrid.org/browse/CBRD-27841 (description 갱신, read-back 일치)
- 검증 기록: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27841/verification.md

## 변경 요약

`[CBRD-27841] Remove the unused recovery index RVREPL_OOS_DELETE` 커밋 1개. 3개 파일, 8줄 삭제, 4줄 번호 변경.

- `src/transaction/recovery.h`: enum `RVREPL_OOS_DELETE = 140` 삭제, 뒤 4개 번호를 1씩 당김
- `src/transaction/recovery.c`: `RV_fun[]`의 `RVREPL_OOS_DELETE` 항목(덤프 함수만 있음) 삭제
- `src/storage/tde.h`: `LOG_MAY_CONTAIN_USER_DATA`의 조건 한 줄 삭제

| 이름 | 이전 | 이후 |
|---|---|---|
| `RVOOS_INSERT` | 137 | 137 |
| `RVOOS_DELETE` | 138 | 138 |
| `RVREPL_OOS_INSERT` | 139 | 139 |
| `RVREPL_OOS_DELETE` | 140 | 삭제 |
| `RVOOS_NOTIFY_VACUUM` | 141 | 140 |
| `RVREPL_DUMMY_OOS_RECORD` | 142 | 141 |
| `RVOOS_RECLAIM_POSTPONE` | 143 | 142 |
| `RVOOS_UPDATE_DROP_POSTPONE` (`RV_LAST_LOGID`) | 144 | 143 |

`DISK_STORAGE_FORMAT_REVISION`은 ADR-0008대로 1로 둔다. 이전 `feature/oos-merge` 빌드의 DB는 다시 만들어야 한다.

작업 중 `origin/feature/oos-merge`가 `71993ddb63`에서 `d25c9e8d20`(#8638, CBRD-28023, `file_manager.c` 문자열 한 줄)로 움직였다. 같은 패치로 rebase했다(range-diff `=`). 로컬 커밋 `9b366302dc`이 `1d86f1d31b`가 되었다.

## 확인한 곳

- `git grep`: `RVREPL_OOS_DELETE`는 정의 세 곳뿐이고, 이 인덱스로 로그를 쓰는 코드가 없다. 두 base(`71993ddb63`, `d25c9e8d20`)에서 같다.
- 번호 대신 이름으로 비교하는 곳이라 수정이 필요 없는 곳: `mvcc.h` `LOG_IS_MVCC_OPERATION`, `recovery.h` `RCV_IS_NOTHING_TO_UNDO`·`RCV_IS_LOGICAL_LOG`, `log_manager.c` 복제 덤프 switch, `log_applier.c`, `replication.c`, `locator_sr.c`(INSERT·UPDATE만 `RVREPL_OOS_INSERT`/`RVREPL_DUMMY_OOS_RECORD`를 씀), `vacuum.c`, `log_append.cpp`, `oos_file.cpp`, unit test(`test_oos_tde_gate.cpp` 등).
- 숫자 리터럴 검색: `unit_tests/oos/scripts/test_storage_format_guard.sh`의 `stamp_offset=140`은 volume 파일 offset이고 recovery index와 무관하다.
- `rv_check_rvfuns ()`는 debug 서버 시작 때 순서만 검사하고 `RV_fun[]` 항목 수는 검사하지 않는다. 그래서 별도 검사 프로그램으로 항목 수까지 확인했다.

## TC 영향

없음. 두 저장소(`cubrid-testcases`, `cubrid-testcases-private-ex`)의 `origin/feature/oos-merge`에서 OOS recovery index 이름과 140~145 번호를 검색했다. 이름이 나오는 곳은 `shell/_36_damson/cbrd_23608_tde/log_enc_04`의 `RVOOS_INSERT`, `RVOOS_DELETE`뿐이다. 이 테스트는 이름으로 비교하고, 두 인덱스는 번호도 그대로다.

- #8347 때의 TC draft PR(cubrid-testcases#3962, cubrid-testcases-private-ex#4673)은 둘 다 파일 변경 없이 2026-11-05에 닫혔다.
- TC Branch Sync가 이번 PR용 빈 draft TC PR을 만들었다: cubrid-testcases#4342, cubrid-testcases-private-ex#5033. `cubrid-pr-tc-base-check --pr 8646`은 두 저장소 모두 PASS였다.

## 검증

모두 debug(GCC) 빌드에서 했다.

| 검사 | 결과 |
|---|---|
| 빌드·설치 | 성공 (`9b366302dc`, rebase 뒤 `1d86f1d31b` 재빌드·설치) |
| `RV_fun[i].recv_index == i`, 항목 수 = `RV_LAST_LOGID + 1` | PASS. `libcubrid.so`, `libcubridsa.so` 모두 144개 항목, `RV_LAST_LOGID` 143, 불일치 0. rebase 전후 모두 확인 |
| 설정한 CTest | 66/66 통과. rebase 전 384초, rebase 뒤 335초 |
| OOS 강제 종료 복구 | PASS (아래) |
| HA·log applier smoke test | 하지 않음 (아래) |

강제 종료 복구 (`oos_crash_recovery.sh`, 전용 DB `oos27841`):

- 6,080바이트 압축되지 않는 값으로 `t_upd`, `t_del`에 200행씩 넣었다. 오래된 snapshot을 잡은 세션 때문에 vacuum이 종료 전에 회수하지 못하게 했다.
- `t_upd` UPDATE와 `t_del` 절반 DELETE를 커밋했다. 다른 세션의 UPDATE·INSERT는 커밋하지 않은 채로 `kill -9`했다.
- `cub_master`가 1초 안에 서버를 다시 시작했다. 복구는 REDO 6,479개 레코드, UNDO 6개 트랜잭션으로 끝났다.
- 데이터: 커밋 상태와 200행·100행 모두 일치. 미커밋 변경은 없어짐.
- `Oos_num_recs`: `t_upd` 800 → 400, `t_del` 400 → 200. garbage 없는 참조 테이블과 같다.
- `checkdb -S`: 종료 코드 0.
- 로그 덤프(`diagdb -d 8`): 강제 종료 전 `RVOOS_NOTIFY_VACUUM` 200개(140번이 이 이름으로 읽힘). 재시작 뒤 `RVOOS_DELETE` 700개와 `RVOOS_RECLAIM_POSTPONE` 200개. 회수 의도 200개는 DELETE 행 100개와 filler 100행이다. 나머지 `RVOOS_DELETE` 400개는 `t_upd`의 옛 chain이며, 이를 지우는 경로는 `RVOOS_NOTIFY_VACUUM` 소비자뿐이다.

HA smoke test를 하지 않은 이유: 복제 로그는 HA가 켜진 서버만 쓴다. 확인하려면 master·slave 두 인스턴스와 heartbeat, copylogdb, applylogdb가 필요하다. 저장소의 관찰 스크립트(`observe_fk_oos_publication.py`)도 HA 서버와 gdb attach를 요구한다. `RVREPL_OOS_INSERT`(139)는 번호가 그대로이고, `RVREPL_DUMMY_OOS_RECORD`는 복제 코드가 이름으로만 처리한다[추론]. 서로 다른 빌드 사이의 복제는 보장하지 않는다.

## JIRA

- https://jira.cubrid.org/browse/CBRD-27841
- `my-cubrid-jira`의 `issues/CBRD-27841-oos-recovery-index-cleanup_eac70c7_codex.md`를 새 범위로 다시 썼다. `main` `2ae28ed`로 통합하고 push했다.
- 담은 내용: 범위 변경 경위(r4409612618, #8347, #8434, r4613840763의 번호 착오), 현재 상태, 번호 표, 형식 정책, #8559 영향, PR #8646과 검증, Acceptance Criteria.
- 중복 검사(`cubrid-jira-dup`): 중복 없음. 관련 이슈 CBRD-27230(#8559)만 본문에 연결했다.
- dry-run 대상은 `PUT /issue/CBRD-27841`의 `description` 필드 하나였다. live 갱신 뒤 read-back이 dry-run payload와 정확히 같았다(5,781자).
- live summary "[OOS] 미사용 복구 인덱스 제거와 로그 번호 정리"는 옛 대상을 이름으로 쓰지 않는다. 그래서 바꾸지 않았다. 상태(Analysis)와 담당자도 그대로다.

## PR

- https://github.com/CUBRID/cubrid/pull/8646, draft, 제목 `[CBRD-27841] Remove the unused recovery index RVREPL_OOS_DELETE`
- 본문은 `my-cubrid-docs/cbrd-27841/pr-body.md`이고, live 본문과 같다. 본문에 #8347 이력과 #8559 영향을 적었다.
- `my-cubrid-docs` `main`에 `pr-body.md`, `pr-context.md`, `verification.md`, `checks/`(검사 스크립트 2개)를 넣고 push했다(`93b6772`).

## CI

- `/run all` 댓글: https://github.com/CUBRID/cubrid/pull/8646#issuecomment-7005770190
- Run: https://github.com/CUBRID/cubrid/actions/runs/44501180486. 시작 시점에 `build (debug)`, `build (release)`, `test_shell`, `test_sql`, `test_medium`, `test_sql_by_cci`가 모두 pending이었다.
- `gh pr checks --required`는 이 base에서 required check를 돌려주지 않았다.
- 감시: `cubrid-ci-watch` request 77(run 44501180486, attempt 1). 이미 돌고 있는 공용 poller의 registry에 들어간 것을 확인했다.

## r4613840763 정정 답글 초안 (운영자가 게시)

> 번호를 정정합니다. 위 답글에서 "140번은 그대로 유지합니다"라고 썼는데, 답글을 쓴 시점(`71993ddb63`)에 `RVOOS_NOTIFY_VACUUM`은 141번이었고 140번은 `RVREPL_OOS_DELETE`였습니다.
>
> `RVREPL_OOS_DELETE`는 이 인덱스로 로그를 기록하는 코드가 없습니다(enum, `RV_fun[]`의 덤프 전용 항목, `tde.h` 조건 한 줄뿐). 말씀하신 원칙대로 #8646에서 이 인덱스를 지우고 뒤 번호를 하나씩 당겼습니다. 그래서 `RVOOS_NOTIFY_VACUUM`은 140번, `RVREPL_DUMMY_OOS_RECORD`는 141번, `RVOOS_RECLAIM_POSTPONE`은 142번, `RVOOS_UPDATE_DROP_POSTPONE`(`RV_LAST_LOGID`)은 143번이 됩니다.

## #8559 후속 (CBRD-27230)

#8559는 `RVREPL_OOS_REUSE = 145`와 `RV_LAST_LOGID = RVREPL_OOS_REUSE`를 더한다. #8646이 들어간 뒤 #8559는 다음을 해야 한다.

- `RVREPL_OOS_REUSE`를 144로 바꾼다.
- `recovery.h`의 `RV_LAST_LOGID` 줄과 `tde.h` 마지막 조건 줄에서 rebase 충돌을 푼다. 둘 다 이번에 바뀐 줄과 붙어 있다.

#8559는 건드리지 않았다.

## 운영자에게 남은 병합 단계

1. PR #8646의 CI가 green인지 확인한다(run 44501180486, 또는 watcher request 77의 이벤트).
2. r4613840763 스레드에 위 정정 답글을 게시한다.
3. PR을 ready로 바꾸고 리뷰를 받는다.
4. 병합 직전에 승인 gate를 실행하고 결과를 확인한다: `"$CUBRID_COMMON_DIR/scripts/cubrid-pr-approval-check" --repo CUBRID/cubrid --pr 8646` (`CUBRID_COMMON_DIR`는 `my-cubrid-skills/cubrid-common`).
5. 병합 순서: CBRD-28023(#8638)은 이미 `feature/oos-merge`에 들어갔고(`d25c9e8d20`), 이 PR은 그 위로 rebase되어 있다. 남은 순서는 #8646을 #7990보다 먼저 `feature/oos-merge`에 넣는 것이다. 그 사이 base가 또 움직이면 rebase하고 CI를 다시 돈다.
6. TC PR(#4342, #5033)은 비어 있다. testcase lifecycle에 따라 엔진 병합 직전의 마지막 handoff에서 정리한다.
7. #8646이 들어가면 #7990의 head가 바뀐다. 따라서 #7990의 `/run all`, 최종 리뷰 대상 head, TC gate를 다시 거쳐야 한다(work-tracker 1008·508의 순서).

## 사고와 관찰

- 디스크 가득 참(내 실수): `cubrid diagdb -d 8`은 대화형으로 묻는데, stdin을 `/dev/null`로 주자 질문을 반복 출력해 scratchpad에 57.7GB 파일을 만들었다. `/mnt/nvme/data-5`가 잠시 가득 찼다. 다른 세션의 CBRD-28062 perf sweep io driver가 이때 죽었다고 그 세션이 기록했다(work-tracker 982). 파일은 18:43에 지웠고, 982에 원인과 삭제 사실을 적었다. 그 세션은 이미 다시 시작했다. 두 번째 덤프는 질문에 대한 답을 stdin으로 주고 `ulimit -f`로 크기를 제한했다.
- `cub_master`는 `kill -9`로 끝난 서버를 1초 안에 자동으로 다시 시작했다. 검사 스크립트가 이를 처리하도록 고쳤다.
- md5 380개를 이은 WHERE 조건 하나가 csql에서 10분 넘게 끝나지 않았다(클라이언트 프로세스가 CPU 사용). 이 변경과 무관하다. base 빌드에서 같은지는 확인하지 않았다.

## 작업 위치와 남은 상태

- 엔진 worktree: `/home/vimkim/gh/cb/CBRD-27841-drop-repl-oos-delete`, branch `CBRD-27841-drop-repl-oos-delete` = `vk`의 같은 branch = `1d86f1d31b`. PR이 열려 있어 유지한다. `.cub-workenv`(testdb, oos27841 DB)도 남아 있고, 서버와 master는 멈췄다.
- `my-cubrid-docs`, `my-cubrid-jira`의 task worktree와 branch는 병합한 뒤 지웠다.
- 관련 없는 dirt: `my-cubrid-docs` main checkout의 `cbrd-27259/review-20261111/heap-bigone-assert.md` 수정과 `csql.access`, `csql.err`. 내가 만든 것이 아니라 그대로 두었다.
- work-tracker: 1037은 `waiting`(CI 대기). 677(#8347 검토 milestone)은 대체되어 `cancelled`로 바꿨다.
- 검사 스크립트 사본: `my-cubrid-docs/cbrd-27841/checks/rv_fun_order.cpp`, `oos_crash_recovery.sh`.

## 갱신: 병합 완료 (2026-11-19 19:59 KST)

- 정정 답글 게시: https://github.com/CUBRID/cubrid/pull/7990#discussion_r4627146076
- #8559가 먼저 병합되었다(`b43275e944`). 이 tree는 hornetmj가 승인한 `4d6eeb345e`를 base에 합친 결과와 같아 재리뷰가 필요 없었다. 계획했던 #8559 rebase는 하지 않았다.
- #8646을 `b43275e944` 위로 rebase했다(head `4ee2bc4ebb`). 충돌은 `recovery.h`와 `tde.h`뿐이었고, `RVREPL_OOS_REUSE`도 145에서 144로 당겼다. 결과 tree는 반대 방향 시험 rebase와 같다.
- 새 head 검증: `RV_fun[]` 145개 항목·`RV_LAST_LOGID` 144 PASS(서버·SA), CTest 70/70, kill -9 복구 PASS(종료 전 `RVOOS_NOTIFY_VACUUM` 200개, 재시작 뒤 `RVOOS_DELETE` 500개와 `RVOOS_RECLAIM_POSTPONE` 200개). github-checks 5개 통과.
- 사용자 결정으로 승인 gate(BLOCKED: H2SU, hornetmj 리뷰 없음)를 건너뛰고 trivial refactoring 댓글(issuecomment-7007152760)을 단 뒤 squash 병합했다: `8c478d8559` = `feature/oos-merge` tip, tree는 검증한 head와 같다.
- 이전 head의 CI run 44501180486은 병합 뒤 취소했다(build 두 개와 `test_medium`은 통과한 상태였다). TC Branch Finalize가 빈 TC PR #4342, #5033을 닫았다.
- JIRA description을 병합 상태로 다시 게시했다(`my-cubrid-jira` `fcccd67`, read-back 일치). 상태는 Analysis 그대로다.
- 다음: #7990은 head가 `8c478d8559`로 바뀌었으므로 `/run all`, 최종 리뷰 대상 head, TC gate를 다시 거쳐야 한다.

## 갱신: 작업 흔적 정리 (2026-11-19)

이 보고서는 엔진 worktree의 `.report-CBRD-27841.md`에서 옮겼다. 그 worktree는 지웠다.

- 엔진 worktree `/home/vimkim/gh/cb/CBRD-27841-drop-repl-oos-delete`를 지웠다. submodule(`cubrid-cci`, 고정 commit, 변경 없음)이 있어 `git worktree remove --force`를 썼다. 지운 내용은 stow 링크, debug 빌드 디렉터리(2.9G), 테스트 DB(`testdb`, `oos27841`, 494M), 로그 파일뿐이다.
- 로컬 branch와 `vk/CBRD-27841-drop-repl-oos-delete`를 지웠다. squash 병합이라 `git branch -d`가 거부해 `-D`를 썼다. squash commit `8c478d8559`의 tree가 branch tree와 같음을 확인했고, commit `4ee2bc4ebb`는 `refs/pull/8646/head`로 남아 있다.
- 남긴 것:
  - `cub-workenv` 할당 기록 1건(TCP 41426/41431, SHM 0x620001ae/0x620001af). `cub-workenv reset --worktree /home/vimkim/gh/cb/CBRD-27841-drop-repl-oos-delete`가 다른 프로세스(PID 3028, `sd-pam`)의 environ을 읽지 못해 안전 검사에서 멈췄다. 포트와 SHM은 실제로 쓰이지 않는다. 번호만 예약된 상태다.
  - 설치 디렉터리 `/home/vimkim/.cub/install/CBRD-27841-drop-repl-oos-delete`(435M)와 `/tmp/cwe-1000/bd29a89a1f35`. 정리 범위에 넣지 않았다.
