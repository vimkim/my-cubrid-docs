# CBRD-28046 변경 코드의 이력 보고

- 질문. PR #8495가 고친 코드는 원래 어떤 형태였고, 누가 어떤 이슈 때문에 그렇게 만들었는가.
- 대상 PR. https://github.com/CUBRID/cubrid/pull/8495 (head `6a7ca6b4a8`, base develop)
- 조사 기준. `CUBRID/cubrid` 커밋 `6a7ca6b4a8`과 그 부모 `2d1513a8af`의 git 이력, CUBRID Jira, 이 저장소의 문서
- 조사 일자. 2026-11-12 (Asia/Seoul)

## 한 줄 보고

commit-with-postpone 시점의 로그 flush는 2008년 최초 코드부터 이유 기록 없이 있었습니다. 같은 성격의 sysop 쪽 flush는 2015년 CUBRIDSUS-17980(Remzi Ibram)에서 성능 때문에 이미 제거되었습니다. 이번에 트랜잭션 commit 쪽도 제거하고, WAL로 보호되지 않는 LOB 디렉터리 삭제(CBRD-23700, 인치준)에만 flush를 옮겨서 postpone commit의 로그 flush를 2회에서 1회로 줄였습니다.

## 세 줄 보고

1. `log_append_commit_postpone()`의 flush는 2008년 최초 import 코드부터 있었습니다. 이후 CUBRIDSUS-1371(오이석), CUBRIDSUS-5300(서경식, Prior_LSA), CUBRIDSUS-5824/6230/5393(김갑영)이 형태를 바꿨지만 모두 merge나 성능 작업이었습니다. 이 flush가 왜 필요한지 적은 커밋, 티켓, 문서는 없습니다.
2. sysop 쪽 같은 flush는 2015-12 CUBRIDSUS-17980(Remzi Ibram, 10.0)에서 "flush 동기화를 하지 않는다"는 성능 개선으로 제거되었고, 10.1 파일 매니저 재설계(CBRD-20185)도 flush 없는 형태를 유지했습니다. 이번 PR은 트랜잭션 commit 쪽도 제거했습니다. 로그는 LSA 순서로 쓰이고 페이지는 WAL을 따르므로, postpone 결과가 디스크에 있으면 `LOG_COMMIT_WITH_POSTPONE`도 이미 디스크에 있다는 논리입니다.
3. 예외는 로그로 되돌릴 수 없는 LOB 파일 삭제(`RVHF_LOB_REMOVE_DIR`)입니다. 이 postpone은 2026-02 CBRD-23700(#6833, 인치준, git 이름 Daniel)에서 생겼고, 이번 PR은 이 함수 안에서만 삭제 전에 로그를 flush합니다. 1행 UPDATE+COMMIT 3000회 기준 fdatasync가 6006회에서 3006회로 줄었습니다(CBRD-27781 브랜치에서 측정).

## 세부 보고

### 1. 배경

postpone을 남긴 트랜잭션은 commit할 때 로그를 두 번 flush하고 기다렸습니다.

- AS-IS. `LOG_COMMIT_WITH_POSTPONE` 기록 후 flush, postpone 실행, `LOG_COMMIT` 기록 후 다시 flush.
- TO-BE. `LOG_COMMIT` 기록 후 한 번만 flush. 단, LOB 디렉터리 삭제 postpone은 실행 직전에 `LOG_COMMIT_WITH_POSTPONE`까지 flush.

이 문제가 드러난 계기는 OOS 작업(PR #8434)입니다. OOS reclaim이 commit postpone으로 옮겨지면서 OOS 컬럼이 있는 UPDATE commit이 모두 postpone commit이 되었습니다. Work841 측정에서 1행 UPDATE+COMMIT 3000회가 18.83초에서 31.09초로 느려졌고, fdatasync는 3011회에서 6006회로 늘었습니다(CBRD-28046 본문, `CBRD-27788/final-perf-handoff.md:30`).

### 2. 변경 1. `log_append_commit_postpone()`의 flush 제거 (`src/transaction/log_manager.c`)

이 PR 직전 형태:

```c
  start_lsa = prior_lsa_next_record (thread_p, node, tdes);

  tdes->state = TRAN_UNACTIVE_COMMITTED_WITH_POSTPONE;

  logpb_flush_pages (thread_p, &start_lsa);
```

변경 후:

```c
  (void) prior_lsa_next_record (thread_p, node, tdes);

  tdes->state = TRAN_UNACTIVE_COMMITTED_WITH_POSTPONE;
```

flush 줄의 이력과 각 변경의 이유:

| 시점 | 커밋 | 이슈 | 작성자 | 변화 | 티켓에 적힌 이유 |
|---|---|---|---|---|---|
| 2008-11-24 | `a3e0ef5634` | merge RB-8.1.1 (최초 import) | 김시완 (merge 수행자) | `logpb_end_append (thread_p, LOG_NEED_FLUSH, true)`. append할 때 바로 flush | 티켓 없음 |
| 2009-08-14 | `f14525914c` | CUBRIDSUS-1371 | 오이석 | `logpb_end_append()`와 `logpb_flush_all_append_pages (LOG_FLUSH_FORCE)`로 분리 | RB-8.2.0 branch merge. 설계 설명 없음 |
| 2011-07-14 | `fd87394ae0` | CUBRIDSUS-5300 외 | 서경식 | prior LSA list 구조로 전환. flush는 유지 | "LOG_CS 구간 줄이기 - introduce prior_LSN" |
| 2011-08-19 | `4aad793cc6` | CUBRIDSUS-5824 | 김갑영 | `LOG_FLUSH_DIRECT`를 `LOG_FLUSH_NORMAL`로 변경 | "async commit에서 working thread가 log를 direct로 flush해야 하는 경우는 WAL이외에는 없습니다." |
| 2012-01-05 | `5f45629b6a` | CUBRIDSUS-6230 | 김갑영 | `start_lsa` 변수 추가. 해당 LSA까지만 flush | YCSB update 성능 퇴행. "불필요하게 LFT를 wake-up 시키지 않도록 함" |
| 2012-12-18 | `54b8fd9509` | CUBRIDSUS-5393 | 김갑영 | `logpb_flush_pages (thread_p, &start_lsa)`로 교체. 이 PR 직전 형태 | LFT signal 전달 방식 교체 |
| 2022-08-22 | `29624f2b7f` | CBRD-24378 (#3664) | Jaeeun Kim | `at_time` 필드 추가, `_obsolete` 함수 분리. flush 의미는 그대로 | restoredb `-d` 시점 복원 수정 |
| 2026-11-11 | `6a7ca6b4a8` | CBRD-28046 (#8495) | 김대현 | flush와 `start_lsa` 삭제 | commit당 동기 flush 2회를 1회로 |

blame 해석 시 주의할 점:

- `git blame`은 flush 줄을 CBRD-24378(Jaeeun Kim, 2022)로 보여줍니다. 이 커밋은 기존 함수를 `log_append_commit_postpone_obsolete()`로 복사하면서 diff상 줄이 다시 쓰인 것일 뿐, flush를 새로 넣은 커밋이 아닙니다. 티켓에도 flush 언급이 없습니다.
- `start_lsa` 선언은 blame상 `6522201dab`(2014 "revert cubrid trunk", 남창우)로 나오지만, 실제로 처음 들어온 것은 2012-01 CUBRIDSUS-6230입니다.
- `a3e0ef5634`는 branch merge 커밋이므로 김시완은 merge 수행자이고, 코드를 처음 쓴 사람은 이 이력에서 알 수 없습니다. 그 이전 커밋(`cba60decb8`, "2008 R1.0")에는 `log_manager.c`가 없습니다.
- 이 flush가 왜 필요한지 적은 기록은 커밋 메시지, 코드 주석, Jira, my-cubrid-docs 어디에도 없습니다. 2009~2012년 티켓들은 모두 merge나 성능 이유로 형태만 바꿨습니다.
- CBRD-24378 티켓은 이 PR이 기대는 의미를 적어 두었습니다. "it writes the LOG_COMMIT_WITH_POSTPONE log record before executing postpone operations, and this guarantees that the transaction will commit."

### 3. 선례. sysop의 flush 제거 (CUBRIDSUS-17980, CBRD-20097)

- 실제 제거 커밋은 `5fe4e4eb97`, Remzi Ibram, 2015-12-03, "[CUBRIDSUS-17980][CR] Optimize commit top operation with postpone for vacuum."입니다. `log_append_topope_commit_postpone()`에서 `logpb_flush_pages (thread_p, &start_lsa);`를 제거했습니다.
- CUBRIDSUS-17980 티켓 본문. "1. Do not synchronize with flushing log when append log record for commit top operation with postpone 2. Use cached log postpone records to avoid accessing log pages and requirements for log critical section." 안전성 논증은 없고, "daily regression test"로 검증한다는 코멘트만 있습니다.
- 같은 문제를 다룬 조사 티켓이 따로 있습니다. CUBRIDSUS-17074(2015-06)와 그 복제본 CBRD-20097(Razvan Radulescu, 2016-03, Fix Version 10.1)입니다. 본문은 "Most system operations commits are performed during transaction, while locks and page latches are hold and any synchronous IO job will affect performance. Investigate if log flush is required during log_append_topope_commit_postpone function."입니다.
- CBRD-20097은 2017-03 Remzi Ibram의 코멘트 "log is no longer flushed when system operation is committed with postpone. it was removed along with file manager redesign."와 함께 닫혔습니다.
- 이후 Remzi Ibram의 `cc368329d0` "[CBRD-20185] File manager redesign (#197)"(2016-11-23)이 지금의 `log_append_sysop_start_postpone()`을 만들었고, 역시 flush가 없습니다. CBRD-20097 종료 코멘트의 "file manager redesign"은 이 커밋을 가리키는 것으로 보입니다.
- 정리하면, 코드에서 flush를 처음 뺀 것은 CUBRIDSUS-17980(`git describe` 기준 v10.0에 포함)입니다. 10.1의 CBRD-20185가 함수를 새로 쓰면서 그 형태를 유지했고, CBRD-20097은 그 결과를 확인하고 닫은 조사 티켓입니다. 세 티켓은 서로를 언급하지 않으므로 이 연결은 추정입니다. PR 본문의 선례 표기는 2026-11-12에 CUBRIDSUS-17980과 CBRD-20185로 고쳤습니다.
- 같은 시기 vacuum postpone 작업이 이어졌습니다. CUBRIDSUS-17890(Alexandru Stan, vacuum이 postpone으로 page dealloc), CUBRIDSUS-17689(Remzi Ibram, recovery 중 top op commit postpone 수정). 이 커밋들도 flush의 안전성은 논하지 않습니다.
- 현재 `log_append_sysop_start_postpone()`은 `prior_lsa_next_record()`만 호출하고 flush하지 않습니다. 트랜잭션 쪽 flush는 그 뒤에도 남아 있었습니다(2016 CBRD-20214의 backtrace에 `log_append_commit_postpone`의 `logpb_flush_pages` 호출이 나옵니다).

### 4. 변경 2. `heap_rv_lob_remove_dir()`에 WAL flush 추가 (`src/storage/heap_file.c`)

이 PR 직전 형태:

```c
int
heap_rv_lob_remove_dir (THREAD_ENTRY * thread_p, LOG_RCV * rcv)
{
  return fileio_lob_remove_matching_dir (rcv->data);
}
```

- 이 함수와 `RVHF_LOB_REMOVE_DIR` postpone은 커밋 `a59899038b`, 2026-02-11, "[CBRD-23700] After executing the DROP table, LOB objects are not removed (#6833)"에서 생겼습니다. PR 작성자는 인치준(git 이름 Daniel), 승인자는 hornetmj입니다. 티켓은 SungRyong Cho가 2020-07에 등록했습니다.
- PR #6833의 본문과 리뷰에도 LOB 삭제와 commit durability 순서에 대한 논의는 없습니다. `locator_sr.c:14826` 주석은 삭제가 "executed at commit time"이라고만 적었습니다.
- CBRD-23700은 테이블 DROP/TRUNCATE와 LOB 컬럼 DROP 때 LOB 파일과 디렉터리를 지우도록 한 변경입니다. 티켓의 규칙은 "COMMIT - 삭제 / ROLLBACK - 삭제 안 함"이고, postpone, WAL, flush 순서에 대한 논의는 없습니다.
- 파일 삭제는 로그로 되돌릴 수 없습니다. 기존에는 commit-with-postpone flush가 "삭제 전에 commit이 디스크에 있다"는 것을 암묵적으로 보장했습니다.
- 이번 PR은 그 보장을 이 함수로 옮겼습니다. 삭제 전에 `logpb_flush_log_for_wal (thread_p, &tdes->rcv.tran_start_postpone_lsa)`를 호출합니다.
- 비슷한 선례. `file_destroy`는 page를 버리기 전에 `pgbuf_flush_with_wal`로 dirty page를 WAL에 맞춰 내립니다(`063d84e537`, CBRD-27151, Yunjun Lee). `vacuum_flush_data`도 `logpb_flush_log_for_wal`을 씁니다(CUBRIDSUS-17704). 다만 postpone 실행 중에 CWP LSA까지 로그를 flush하는 경우는 이번 LOB 가드가 처음입니다.
- sysop postpone에서는 `tran_start_postpone_lsa`가 설정되지 않아 가드가 flush를 건너뜁니다. `RVHF_LOB_REMOVE_DIR` postpone을 등록하는 곳은 `xlob_remove_dir`(`locator_sr.c:14844`) 하나이고, 이 함수는 서버 요청 핸들러(`network_interface_sr.cpp:13302`)에서만 불리므로 sysop 안에서 등록되지 않습니다.
- `log_append_postpone` 호출 지점을 모두 확인한 결과, 로그로 보호되지 않는 효과를 가진 postpone은 `RVHF_LOB_REMOVE_DIR`(`locator_sr.c` `xlob_remove_dir`) 하나였습니다(`cbrd-28046/pr-context.md:26`).

### 5. 검증 근거

- 300개 테이블 DROP commit 중 SIGKILL 24회. 부분 commit 0, 응답한 commit 유실 0, `checkdb` 24/24 통과(`cbrd-28046/pr-context.md:27`).
- LOB 가드를 뺀 변형으로 crash 테스트를 했을 때 테이블은 남고 LOB 파일만 사라졌습니다(`BLOB_LENGTH` NULL). 가드가 필요하다는 음성 대조 결과입니다(`cbrd-28046/pr-context.md:28`).
- fdatasync 6006회에서 3006회로 감소. CBRD-27781 브랜치 기준이며 develop에서는 측정하지 않았습니다.
- 코드 리뷰 결과는 확정 결함 0건, 판정 incomplete입니다(`cbrd-28046/code-review-pr8495-6a7ca6b/report.md`). 미결 항목은 아래와 같습니다.
  - R-1. 기존 결함 CBRD-27964(commit 전 LOB 직접 삭제)의 창이 `LOG_COMMIT` flush 시점까지 넓어짐.
  - R-2. 기존 `nxio_lsa` 대기 비교의 `<`와 `<=` 문제.
  - R-3. `file_destroy`가 dirty page를 버리는 상황에서 `LOG_COMMIT_WITH_POSTPONE`이 유실되는 조합. 새로 도달 가능해졌으나 실행 근거 없음.

### 6. 함께 알릴 사항

- 이 flush를 전제로 쓴 기존 기록이 있습니다. PR이 merge되면 문구를 고쳐야 합니다.
  - CBRD-27936 본문. "postpone이 하나라도 있는 트랜잭션은 안전하다. `log_tran_do_postpone`이 `log_append_commit_postpone` 으로 `LOG_COMMIT_WITH_POSTPONE` 을 기록하고 flush한 뒤에 saved space가 풀리기 때문이다." 현재 코드에서도 saved space는 postpone 실행 직후, `LOG_COMMIT` 기록 전에 풀립니다(`log_manager.c:5270-5277`). 다른 트랜잭션이 그 공간을 재사용한 로그는 CWP보다 뒤 LSA라서, 그 로그가 디스크에 있으면 CWP도 디스크에 있습니다. 그래서 안전성은 유지된다고 봅니다. 이 판단은 코드 읽기에 기반한 추론이고 실행으로 확인하지 않았습니다.
  - CBRD-26885 코드 맵은 `log_append_commit_postpone`을 "내구성 경계(여기서 커밋 확정/flush)"로 표시합니다.
  - 내 모델 문서. `sidecar/model/recovery/README.md:127`(`path776-postpone`), `oos/reclaim-model/OosReclaimDesign.tla:168`, `oos/reclaim-model/OosDropDecision.tla:140`.
- `log_append_commit_postpone_obsolete()`는 아직 flush를 호출하지만, 선언만 있고 호출하는 곳이 없는 함수입니다(`log_manager.c:4496`).
- HA 관련 기존 이슈 CBRD-20019(commit 로그 전 crash 시 복제 누락)와 CBRD-28034(COMMIT_WITH_POSTPONE 전후 복제 순서)는 이 PR로 해결되지 않습니다.
- 2015년 이전 작성자는 이메일이 `no-reply@cubrid.org`라서 이름만 적었습니다.

### 7. 조사 범위

- 확인한 곳. git 이력과 blame, `git describe`, Jira(CUBRIDSUS-1371, -5300, -5393, -5824, -6230, -17074, -17980, CBRD-20097, -23700, -24378, -26885, -27936, -28046 외), my-cubrid-docs.
- 찾지 못한 것. 2008년 최초 flush의 이유, sysop flush 제거의 안전성 논증, CBRD-23700에서 LOB 삭제와 commit durability 순서에 대한 논의.
- GitHub PR(#6833, #3664, #8495)의 본문, 리뷰, 코멘트도 확인했습니다. 2016년 이전 SVN 시기 커밋은 GitHub PR과 연결되어 있지 않습니다.
