# PR #7415 Line Review

**PR:** [CUBRID/cubrid#7415](https://github.com/CUBRID/cubrid/pull/7415)  
**Title:** [CBRD-27028] Handle FILE_OOS asserts in utilities  
**Author:** vimkim  
**Base:** `feat/oos`  
**HEAD SHA:** `36c6ffdd8407e447d86d52b88731722f911ac0ce`  
**Review date:** 2026-07-07  
**Status:** Draft PR

> **TL;DR** (결정 반영): 이 PR 은 `FILE_OOS` 를 만났을 때 `diagdb`, `spacedb`, `checkdb` 가 바로 assertion 으로 죽는 문제를 줄이는 안정화 패치로 둔다. `checkdb` 의 generic file tracker 순회에서는 OOS owner descriptor 가 생기기 전까지 OOS file 을 반환하지 않고 건너뛰는 방향으로 정리한다. 즉, 이번 PR 은 "assertion 제거 + 기존 utility 정상 종료"까지이고, OOS file table 자체의 online-safe 검사는 owner metadata 후속 작업으로 넘긴다.

## Summary

- **변경 요약**: `src/storage/file_manager.c` 한 파일에서 `FILE_OOS` utility 경로의 assertion 을 제거한다.
- **주요 이슈**: `file_tracker_get_and_protect()` 가 OOS file 을 보호 없이 반환하면 `checkdb` 와 동시 `DROP TABLE` 사이에 stale VFID 위험이 생긴다.
- **결정 사항**: 이번 PR 에서는 `FILE_UNKNOWN_TYPE` 기반 generic 순회에서 OOS 를 skip 한다. OOS file table 검사는 owner descriptor 후속 작업에서 보호 lock 을 갖춘 뒤 추가한다.

---

## Line-by-Line Review

| Lines | 판단 | 설명 |
|---|---|---|
| `file_manager.c:1431-1433` | OK | `file_header_dump_descriptor()` 가 `FILE_OOS` 에서 `assert (false)` 대신 `OOS file` 을 출력한다. OOS file (큰 컬럼 값을 heap 밖에 따로 저장하는 파일)은 아직 class owner 정보를 header 에 들고 있지 않으므로, 가짜 class 이름을 만들지 않는 판단이 맞다. |
| `file_manager.c:10902-10908` | 되돌림 | `desired_type == FILE_OOS` 필터는 dead code 다 — 유일한 caller 인 `file_tracker_check()` 가 `FILE_UNKNOWN_TYPE` 만 넘기고, 동작도 `default:` (exact type match) 와 같다. base 의 `assert (false)` 는 "OOS-only 순회 미지원" unreachable guard 이므로 hunk 를 되돌린다. |
| `file_manager.c:10933-10935` | 수정 필요 | OOS file 을 찾으면 `*stop = true` 로 바로 반환한다. 이때 class lock (해당 class 가 drop 되지 못하게 잡는 보호 장치)을 잡지 않으므로, tracker latch (file tracker page 를 잠깐 붙잡는 보호 장치)를 놓은 뒤 파일이 사라질 수 있다. 결정: owner descriptor 가 생기기 전까지 generic `FILE_UNKNOWN_TYPE` 순회에서는 OOS 를 skip 한다. |
| `file_manager.c:10976-10978` | 되돌림 | 보호 단계 skip 이후 extraction switch 의 `FILE_OOS` case 는 도달 불가능하다. base 의 `assert (false)` 를 unreachable guard 로 유지하고 hunk 를 되돌린다. |
| `file_manager.c:12235-12239` | OK | `spacedb` 에 새 OOS 행을 만들지 않고 `SPACEDB_HEAP_FILE` 에 합산한다. 새 행을 만들면 `SPACEDB_FILE_COUNT`, network packing, `util_cs.c` 출력 라벨, message catalog, QA answer 까지 바뀌므로 이번 안정화 PR 범위를 넘는다. |

## Findings

### Non-blocking (decision: skip for now)

- `src/storage/file_manager.c:10933-10935` - `FILE_OOS` 를 보호 없이 반환하면 online `checkdb` 가 동시 `DROP TABLE` 과 경합할 때 stale VFID 를 검사할 수 있다.

```c
case FILE_OOS:
  /* owner metadata 가 없으므로 unprotected VFID 를 반환하지 않는다 */
  return NO_ERROR;
```

근거: `file_tracker_get_and_protect()` 주석은 tracker latch 를 오래 잡지 않기 때문에, 밖에서 처리할 파일은 삭제되지 않도록 보호해야 한다고 설명한다 (`file_manager.c:10889-10894`). 실제 caller 인 `file_tracker_check()` 는 `file_tracker_interruptable_iterate()` 로 VFID 를 받은 뒤 `file_table_check()` 를 호출한다 (`file_manager.c:12063-12075`). 그런데 영구 파일 삭제는 먼저 `file_tracker_unregister()` 로 tracker 에서 파일을 제거한다 (`file_manager.c:4168-4171`, `10147-10162`). OOS file 은 heap 과 함께 없어지는 mutable file (실행 중 사라질 수 있는 파일)이므로 (`oos_remove_file()` → `file_postpone_destroy()`), 보호 없이 반환하면 검사 직전에 사라질 수 있다. 추가로, 반환된 VFID 는 다음 순회의 resume cursor 가 되므로 파일이 tracker 에서 사라지면 cursor 탐색이 실패해 `assert_release (false)` + `ER_FAILED` (`file_manager.c:11088-11094`) 로 이어진다 — debug 서버에서는 동시 `DROP TABLE` 이 `cub_server` 를 abort 시킬 수 있다. 즉 unprotected 반환은 이 PR 이 안정화하려는 utility 에 새 assert 경로를 넣는 셈이었다. 반면 offline (SA mode) `checkdb` 는 `file_tracker_map()` + `file_tracker_item_check()` 로 OOS file table 을 latch 아래에서 계속 전수 검사하므로, online skip 으로 잃는 coverage 는 offline 검사로 보완된다.

쉬운 비유로 말하면, `checkdb` 가 "이 파일을 검사하겠다"고 적어 둔 뒤 문을 잠그지 않고 방을 나간다. 그 사이 다른 작업이 그 파일을 지우면, 돌아와서 없는 파일을 검사하려고 한다.

결정은 빠른 안정화 선택이다.

- **적용 방향**: OOS owner descriptor (OOS file 이 어느 heap/class 에 속하는지 저장하는 메타데이터)가 생기기 전까지 `file_tracker_interruptable_iterate(FILE_UNKNOWN_TYPE)` 에서 OOS 를 반환하지 않고 건너뛴다. assertion 은 사라지지만 online `checkdb` 는 OOS file table 까지는 검사하지 않는다. skip 은 로그 없이 조용히 한다 — heap 의 `ER_CANNOT_CHECK_FILE` notification 은 일시적 lock 충돌 신호라 systematic skip 에 재사용하지 않는다.
- **완성도 높은 선택 (후속 umbrella 티켓)**: `FILE_OOS` descriptor 에 owner heap/class 정보를 저장하고, heap/btree 처럼 class lock 을 잡은 뒤 OOS VFID 를 반환한다. 그러면 online `checkdb` 가 OOS file 도 안전하게 검사할 수 있다. owner metadata 는 `FILE_DESCRIPTORS` union 의 64-byte `dummy_align` 안에 들어가므로 descriptor 크기 (disk 호환 버전) 변경은 없다. `SPACEDB_OOS_FILE` 행/테이블 귀속도 같은 티켓으로 묶는다.

### Resolved Question

- 이 PR 을 non-draft 로 바꾸기 전에는 lockless OOS 반환을 제거하고, OOS file table 검사는 owner descriptor 후속 이슈에 명시한다.
- 후속 (owner descriptor, online checkdb 보호, `SPACEDB_OOS_FILE` 행/테이블 귀속) 은 umbrella JIRA 티켓 한 건으로 묶어 추적한다. 코드 반영 후 debug build + utility 검증 재실행이 필요하다.

## JIRA Context

CBRD-27028 의 목표는 OOS file 을 가진 DB 에서 `diagdb`, `spacedb`, `checkdb` 계열 유틸리티가 `FILE_OOS` 단순 assertion 으로 중단되지 않게 하는 것이다. PR 은 이 목표를 만족하되, `checkdb` 의 OOS file table 검사는 owner descriptor 가 들어간 뒤 별도 작업으로 안전하게 추가한다.

## Existing Comments

PR 에는 `/run all` 요청 두 개만 있고, 코드 리뷰 코멘트는 없다.

## Verification Notes

- `scripts/check-prereqs.sh 7415`: local HEAD 와 PR HEAD 일치 확인.
- `gh pr diff 7415 --repo CUBRID/cubrid`: PR diff 는 `src/storage/file_manager.c` 한 파일.
- `cubrid-jira-search CBRD-27028`: JIRA 목표 확인.
- `codex review --base origin/feat/oos`: 위 OOS 보호 누락을 P2 후보로 보고.
- `git diff --check origin/feat/oos...HEAD -- src/storage/file_manager.c`: whitespace 문제 없음.
- 이번 리뷰에서 전체 build/test 는 다시 실행하지 않았다. PR 본문에는 debug GCC preset build, OOS DB utility 확인, targeted CTP `utility_19` 검증이 완료됐다고 적혀 있다.
