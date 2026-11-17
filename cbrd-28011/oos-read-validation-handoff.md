# PR 8491 OOS 읽기 할당 검사 독립 검증 handoff

새 세션에서 리뷰어의 질문을 독립적으로 분석하고 실행으로 검증한다. 정상 scan에서 무효 OOS 참조가 발생할 수 있는지, 읽기 API의 손상 처리 계약은 무엇인지, 추가 할당 검사가 필요한 범위는 어디인지 각각 판정한다. 이전 세션의 답변을 결론으로 사용하지 않는다.

작성일은 2026-11-17이며 시간대는 Asia/Seoul이다. 이 문서는 조사 지시서이며 기술적 판정 보고서가 아니다.

## 1. 대상과 원문을 고정한다

| 항목 | 2026-11-17 확인값 |
| --- | --- |
| PR | [CUBRID/cubrid #8491](https://github.com/CUBRID/cubrid/pull/8491) |
| 제목 | [CBRD-28011] Show OOS reads separately in SQL trace |
| 리뷰 | [xmilex-git의 리뷰 5914646248](https://github.com/CUBRID/cubrid/pull/8491#pullrequestreview-5914646248) |
| 리뷰 작성 | 2026-11-16 12:16:16 KST. 상태는 APPROVED |
| Head 저장소와 브랜치 | `vimkim/cubrid`, `CBRD-28011-oos-sql-trace` |
| 기준 head | `a4fec6f8e26a36834c3dde4df0ed0af5ecc6d914` |
| Base 저장소와 브랜치 | `CUBRID/cubrid`, `feature/oos-merge` |
| 당시 base | `67220b7e230ff1587ba5940001d72e10477a1fc4` |
| 소스 worktree | `/home/vimkim/gh/cb/CBRD-28011-oos-sql-trace` |
| 기존 Work Item | `876`. 이번 조사와 결과를 note로 연결한다 |

이 PR은 scan의 전체 `fetch`, `ioread`, `time`에 포함된 OOS 몫을 따로 표시한다. 리뷰어는 여러 scan 경로의 trace를 확인하고 PR을 승인했다. 다음 질문은 PR 범위 밖이라고 명시했다.

> scan이 visible로 판정한 heap record의 OOS 참조가 그런 page를 가리키는 경로가 있나요?

여기서 그런 page는 이미 해제되었거나 다른 용도로 재사용된 OOS head page다. 리뷰어는 release 빌드에서 20,000바이트 값 200행을 읽을 때 OOS fetch 800 중 400이 할당 확인이라고 보고했다. 이는 리뷰어가 보고한 값이며 새 세션의 실측이 아니다.

시작 시 PR 메타데이터와 리뷰 원문을 다시 읽는다. 현재 head가 달라졌으면 기준 head의 질문과 최신 head의 결과를 분리한다. 원래 질문을 검사 제거 요청이나 성능 개선 요청으로 바꾸지 않는다.

## 2. 세션의 범위와 환경을 확인한다

작업은 분석, 격리된 검증, 보고서, 한국어 리뷰 답변 초안까지다. 제품 코드 수정과 게시 여부는 분석 결과와 별도 결정이다. 이 handoff 자체는 PR 댓글 게시, source push, CI 실행, merge를 요청하지 않는다.

다음 순서로 환경을 확인한다.

1. `/home/vimkim/my-cubrid/CUBRID.md`와 worktree의 적용 지침을 읽는다. root `AGENTS.md` 대체 지침을 적용하고 `AGENTS.user.md`가 있으면 읽는다. `gh-pr-info`로 PR 신원을 확인한다.
2. `git status`, branch, HEAD, worktree 목록을 확인한다. 기존 작업과 실행 중인 DB를 보존한다. 기준 커밋을 맞추려고 현재 checkout을 reset하거나 rebase하지 않는다.
3. `cubrid-oos-context` skill로 규범 문서를 완독하고 경로와 SHA-256을 기록한다. 명세는 요구 동작의 근거이고 실제 구현의 증거는 아니다. 최신 설계와 기준 head의 구현을 구분한다.
4. 새 세션에 필요한 모델 설정과 관련 skill을 읽는다. 조사에는 `how`, `why`, `diagnosing-bugs` 중 실제로 필요한 절차를 적용한다. 런타임 검증 전에는 `cubrid-build`와 해당 native testkit skill을 적용한다.
5. 빌드와 설치 경로, source SHA, debug 또는 release 모드, 설정, 실제 실행 바이너리의 일치를 확인한다. 기존 보고서의 빌드나 PASS를 새 실행의 증거로 사용하지 않는다.
6. instrumentation이나 검증 코드를 추가할 때는 별도 소스 worktree와 전용 DB를 사용한다. 원래 PR worktree와 다른 세션의 DB를 변경하지 않는다. source 수정, 설치 변경, 실행 결과를 각각 기록한다.

기준 worktree는 handoff 작성 시 clean이었다. `PRESET_MODE=debug_gcc`였으며 build directory에는 `compile_commands.json`이 있었지만 root symlink는 없었다. 이 정보는 관찰값이다. 새 세션에서 다시 확인한다. GUI를 실행하지 않고 daemon의 입출력은 개인 CUBRID 정책에 따라 처리한다.

## 3. 질문을 각각 판정한다

다음 항목마다 답, 적용 범위, 소스 근거, 실행 증거, 미확인 사항을 남긴다.

1. 실제 호출 경로에서 추가 fix 두 번이 발생하는가. 무엇을 확인하는가. sector reservation, page deallocation 상태, `PAGE_OOS`, slot 존재, identity stamp를 구분한다.
2. 정상 SQL scan에서 visible 판정 후 OOS 값을 읽기 전까지 참조 대상이 삭제되거나 재사용되는 합법적인 실행 순서가 있는가. 있다면 실행 순서와 동기화 조건을 제시한다.
3. 정상 scan의 읽기와 무효 참조를 받는 저수준 `oos_read` API는 같은 계약인가. 다른 caller가 다른 수명 보장을 제공하는지 확인한다.
4. 검사가 도입된 직접적인 동기는 무엇인가. 실제 SQL 경합 재현, API에 직접 넘긴 stale 참조, 명세의 손상 처리 요구를 구분한다.
5. 2번에서 정상 경로를 찾지 못해도 1번의 검사를 제거할 수 있는가. 변경 가능한 API 계약, 보존해야 할 오류 처리, 추가 검증이 필요한 범위를 설명한다. 이번 조사에서 제품 코드 최적화를 구현하지 않는다.

리뷰어가 주장한 관찰값과 답을 요청한 질문을 구분한다. 리뷰어는 검사가 불필요하다고 단정하거나 제거를 요구하지 않았다. 서로 반대인 가설을 같은 기준으로 평가한다. 정상 경로에 수명 공백이 있다는 가설에는 구체적인 counterexample을 요구한다. 수명이 보장된다는 가설에는 실제 caller의 보호 시작점과 해제점, 모든 관련 삭제 경로의 차단 조건을 요구한다. 손상 처리만을 위한 검사라는 가설에는 도입 기록과 전체 caller 계약을 요구한다. 어느 가설도 이 문서에서 채택하지 않는다.

## 4. 실행 경로와 수명 조건을 추적한다

먼저 아래 순서로 직접 코드를 읽고 가설과 검증 계획을 기록한다. 이전 보고서는 그 뒤에 누락 확인용으로 읽는다.

1. scan에서 snapshot을 얻는 지점, visible 판정, heap record 복사나 latch 해제, OOS Resolve 또는 Expand의 순서를 연결한다.
2. reader의 oldest visible MVCCID 등록과 vacuum horizon 계산을 연결한다. statement snapshot invalidation, transaction 종료, parallel worker의 보호 해제를 구분한다.
3. OOS 체인을 삭제하는 caller를 조사한다. UPDATE 이전 버전, DELETE의 REMOVE, non-MVCC eager cleanup, in-place UPDATE, abort와 savepoint rollback, recovery에서 각 경로의 조건을 확인한다.
4. chunk 삭제와 빈 페이지 회수, file destroy를 구분한다. heap의 visibility가 OOS chunk와 page 수명까지 보호한다는 주장을 각 단계의 코드로 연결한다.
5. `pgbuf_fix_if_not_deallocated`의 사전 검사와 실제 fix 사이에 무엇이 보호되는지 확인한다. 검사가 참조 수명을 연장하는지, 무효 입력을 감지하는지만 판정한다.

다음 표를 조사 범위와 결과 표로 확장한다. 동일한 보호를 공유하는 경로는 공유 지점을 증명하고 묶을 수 있다. 차이가 없는 경로마다 같은 실험을 반복할 필요는 없다.

| 경로 | 확인할 차이 |
| --- | --- |
| serial heap, index lookup | visible 판정과 attribute 읽기의 순서, reader 보호 |
| page batch, local page copy, lazy attribute 읽기 | latch 해제 후 payload 해석 시점과 보호의 유지 |
| partition, parallel worker, parallel UNION | snapshot 신원, worker 수명, leader와의 종료 순서 |
| UPDATE 이전 버전, DELETE, relocation | undo image에 든 참조의 소유권과 삭제 조건 |
| MVCC-disabled class, SA, in-place UPDATE | snapshot 대신 필요한 lock, latch, 배타 실행 조건 |
| abort, savepoint rollback, restart recovery | 참조 복원 순서와 OOS 삭제 또는 복원의 순서 |
| DROP, TRUNCATE, file destruction | table lock과 file 수명이 reader를 차단하는 지점 |
| stale 참조의 직접 API 호출, vacuum 재처리 | 정상 scan과 다른 입력 계약 및 기대 결과 |

범위 밖인 경로는 이유와 함께 표시한다. `SNAPSHOT_SATISFIED`, all-visible header, snapshot이 없는 경로를 동일하게 취급하지 않는다. 지원되는 isolation level도 해당 revision의 enum과 caller에서 확인한다.

## 5. 필요한 실행 증거를 만든다

먼저 기존 harness가 필요한 interleaving을 제어할 수 있는지 확인한다. 어려우면 격리된 worktree에 최소한의 동기화 hook을 추가한다. 시간만 기다리는 sleep을 순서 보장의 근거로 삼지 않는다.

### 정상 reader와 회수의 관계

UPDATE와 DELETE 중 서로 다른 삭제 경로를 실제로 통과하는 최소 사례를 선택한다.

1. 전용 DB에 내용과 OOS 참조를 확인할 수 있는 행을 준비한다.
2. reader가 정상 SQL 경로로 행을 visible로 판정한 뒤, OOS payload를 읽기 전에 멈추게 한다. 그 시점의 snapshot, transaction, 보호 상태를 기록한다.
3. 다른 transaction이 행을 변경하고 commit하도록 한다. vacuum이 해당 작업을 검사하는 지점까지 진행시킨다. 작업이 단순히 대기 중인지, 아직 vacuum 대상이 되지 못한 것인지, 삭제가 시도됐는지 구분한다.
4. reader를 재개하고 정확한 원본 payload를 확인한다. vacuum이 chunk나 page를 먼저 회수했다면 실행 순서, ID, 반환값을 보존한다.
5. reader의 보호를 해제한 뒤 같은 회수가 실제로 진행되는 양성 대조군을 둔다. 살아 있는 reader 때문에 회수가 막혔다고 판정하려면 vacuum 자체가 동작했다는 증거가 필요하다.

reader가 직접 수정한 행, shared OOS page, parallel 경로를 모두 한 실험에 섞지 않는다. page 회수까지 확인하려면 해당 페이지의 다른 chunk가 실험을 방해하지 않도록 fixture를 구성한다. 기존 테스트의 성공 여부만으로 실제 SQL scan 경로까지 검증했다고 쓰지 않는다.

### 무효 참조를 직접 넘기는 대조군

저장한 OOS 참조의 대상을 직접 회수하거나 재사용한 뒤 `oos_read`와 `oos_read_many`를 호출하는 테스트를 별도로 실행한다. 오류 코드, process 종료 여부, 다른 점유자의 바이트 반환 여부를 확인한다. assertion 동작이 다를 수 있으므로 debug와 release를 각각 확인한다. 이 실험은 API의 무효 입력 처리를 검증한다. 정상 scan에서 그 입력이 만들어진다는 증거로 사용하지 않는다.

### 추가 fix의 구성

동일한 release 바이너리에서 호출 스택이나 counter delta로 추가 fix의 출처를 확인한다. debug 검증용 fix, 실제 OOS data page fix, volume metadata fix, `ioread`를 구분한다. 800 중 400이라는 reviewer의 수치를 재현하면 입력과 설정을 기록한다. fetch의 절반이라는 사실을 실행 시간의 절반이나 2배 속도 개선으로 해석하지 않는다. 속도를 측정한다면 `benchmark-checklist`를 먼저 적용한다.

대기 중인 vacuum, 잘못된 바이너리, 미충족 fixture 때문에 실험이 성립하지 않으면 해당 실험은 `incomplete`다. 결과를 맞추려고 기존 DB, testcase 기대값, 정상 동작 계약을 변경하지 않는다.

## 6. 코드와 도입 기록의 위치를 찾는다

아래 줄 번호는 기준 head의 탐색 시작점이다. 파일과 symbol을 다시 찾아 정확한 호출 관계를 확인한다.

| 대상 | 탐색 시작점 |
| --- | --- |
| scan 시작과 projection | `src/query/scan_manager.c:4031`, `:5477`, `:5723`; batch는 `:8044`, `:8099`, `:8112` |
| visible version 선택 | `src/storage/heap_file.c:28398`; page batch는 `heap_page_collect_visible` |
| OOS attribute 해석 | `heap_file.c:11573`, `:12127`; `src/storage/heap_oos_value_ref.cpp:122` |
| reader horizon | `src/transaction/mvcc_table.cpp:259`, `:367`; snapshot invalidation은 `log_tran_table.c:4075` |
| vacuum 선택과 삭제 | `src/query/vacuum.c:3414`, `:1854`, `:3751`, `:3896`; `src/query/vacuum_oos.cpp` |
| eager cleanup | `src/storage/heap_oos.cpp:957`; caller 조건은 `heap_file.c`에서 전수 검색 |
| page 회수 | `src/storage/oos_file.cpp:1507` 이후 |
| head와 continuation 읽기 | `oos_file.cpp:2552`, `:2667`, `:2827`, `:2889` |
| allocation probe | `src/storage/page_buffer.c:16154`; `src/storage/disk_manager.c:4229` 이후 |
| 무효 참조 fixture | `unit_tests/oos/test_oos_identity_stamp.cpp:924`, `:1051` |
| snapshot과 vacuum fixture | `unit_tests/oos/test_oos_real_vacuum_server.cpp:550`, `:654` |

도입 커밋은 로컬 object `29fc3567fbbc857330acdb649bb47030d0a454b8`에서 찾을 수 있었다. 제목은 `[CBRD-26950] Check page type and identity before touching an OOS chain`이다. `git show`로 메시지, 전체 patch, 테스트를 직접 읽는다. 해당 object가 없으면 공식 PR 이력에서 찾고, 그 부재를 다른 커밋으로 조용히 대체하지 않는다.

참고 문서는 다음과 같다. 작성 revision과 분석 범위를 확인하고 현재 검증과 분리한다.

- [기존 PR 리뷰](code-review.md)는 SQL trace 변경에 대한 리뷰다. 이번 수명 문제의 독립 판정이 아니다.
- [PR 설명](pr-body.md)과 [PR 준비 기록](pr-context.md)은 당시 계측 의미와 source 신원의 단서다.
- `my-cubrid-docs`의 `cbrd-26950/CBRD-26950-oos-identity-stamp-page-lsa_eaf1165_claude.md`는 도입·수정 이력의 단서다.
- 이전 세션에서는 일부 소스와 도입 기록을 읽었지만 이번 질문을 위한 런타임 재현이나 제거 실험을 수행하지 않았다. 이전 답변은 검증 결과로 인용하지 않는다.

## 7. 판정과 답변 초안을 제출한다

보고서는 문서 저장소의 적용 Git 절차에 따라 보존한다. 권장 basename은 `oos-read-validation.md`다. 검증 harness를 유지할 필요가 있으면 실행 방법과 목적을 보고서에 연결한다. raw log와 임시 파일은 repository의 scratch 정책을 적용한다.

보고서에는 다음을 포함한다.

1. 리뷰어가 직접 물은 질문과 새 세션의 직접적인 답. 질문, 전제, 관찰값, 추론을 구분한다.
2. 경로별 판정 표. `정상 경로의 반례 확인`, `추적한 범위에서 보호 확인`, `무효 입력 처리만 확인`, `incomplete`, `범위 밖` 중 실제 증거에 맞는 상태와 근거를 적는다.
3. reader 보호의 시작점과 종료점, 삭제와 page 회수의 선행 조건을 연결한 설명. 반례가 있으면 최소 실행 순서와 재현 방법을 제시한다.
4. source SHA, testcase SHA, binary와 build 설정, instrumentation diff, 실행 명령, 관측 결과, 대조군, 재현 artifact 경로.
5. reviewer의 추가 fix 설명이 코드와 일치하는지, 정상 scan에서 검사 필요성을 뒷받침하는 사례가 있는지, 검사 제거의 안전성을 판단할 증거가 충분한지에 대한 각각의 결론.
6. PR에 붙여 넣을 수 있는 짧은 한국어 답변 초안. 검증한 범위와 남은 질문을 명시한다. 게시하지 않고 사용자에게 제시한다.

소스 조건을 추적한 결과와 직접 실행한 결과를 별도로 표시한다. 반례를 못 찾은 결과를 엔진 전체에 대한 부재 증명으로 확대하지 않는다. 손상 처리가 검사의 목적이라는 사실만으로 검사 비용을 정당화하거나 제거를 승인하지 않는다. 필수 실행 증거가 없으면 그 부분을 `incomplete`로 남기고 정확히 무엇이 부족한지 적는다.

완료 시 Work Item `876`에 보고서, 검증 revision, 핵심 판정, 다음 조치를 note로 연결한다. 기존 PR의 대기 상태와 TC·CI 작업을 이번 조사 완료만으로 변경하지 않는다.
