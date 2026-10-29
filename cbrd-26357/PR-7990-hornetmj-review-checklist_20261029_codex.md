# PR 7990 hornetmj 리뷰 대응 체크리스트

팀장님 리뷰를 하나씩 이해하고 결정한 뒤, 필요한 수정과 검증을 마친다. 이 문서는 OOS 작성자와 리뷰어가 다음 작업을 이어갈 수 있도록 진행 상태와 근거를 보존한다.

분석일은 2026-10-29, Asia/Seoul이다. 대상은 [CUBRID/cubrid PR 7990](https://github.com/CUBRID/cubrid/pull/7990)이다. 검토 기준 소스는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, 브랜치는 `feature/oos-merge`이다. 수집 당시 hornetmj님의 inline 리뷰 6개는 모두 미해결이며 outdated가 아니다. 빈 COMMENTED 리뷰 요약은 별도 작업으로 세지 않는다.

리뷰 원문의 재현 결과는 리뷰어의 관찰이다. 이 작업에서 직접 실행한 결과와 구분한다. 아래의 각 완료 표시는 해당 단계의 근거를 확보한 경우에만 바꾼다.

## 작업 범위와 재개 위치

- 기존 Work Item `508`에 이 체크리스트와 단계별 결과를 연결한다. 전체 PR 머지 완료를 이 문서의 초기 작성 완료와 혼동하지 않는다.
- 엔진 수정 작업은 `/home/vimkim/gh/cb/pr7990-hornet-r1`, `review/pr7990-hornet-r1`에서 시작한다. 로컬 통합 대상은 `feature/oos-merge`이다.
- 문서 작업은 `/home/vimkim/gh/my-cubrid-docs-pr7990-hornet-review`, `docs/pr7990-hornet-review-20261029`에서 진행한다. 로컬 통합 대상은 문서 저장소 `main`이다.
- 각 항목의 순서는 검토, 이해, 결정, 수정, 검증, 기록이다. 하나의 수정과 검증을 마친 뒤 다음 수정을 시작한다.
- 현재 단계는 R1의 소스 확인과 재현 준비이다. R2부터 R6까지는 검토 대기이다.
- 현재 실행 모드는 `Babysit / threads-only`이다. 기존 PR의 충돌 해결, CI 재실행, 원격 push, 리뷰 답글 게시, thread resolve, PR 머지는 이 단계의 작업에 포함하지 않는다.

## 처리 순서

R1은 사용자가 지정한 링크이므로 먼저 다룬다. 이후에는 커밋된 행을 손상시킬 수 있는 R5, 교착 R2, 미사용 복구 인덱스 R6, 스윕 비용 R3 순서로 검토한다. R4는 리뷰어가 명시한 bestspace redesign 안정화 후 적용 계획을 먼저 확인한다. 이 순서는 작업 제안이며 아직 각 항목의 수정안을 승인한 것은 아니다.

| 순서 | 항목 | 사용자 영향 | 첫 확인 사항 | 상태 |
| --- | --- | --- | --- | --- |
| 1 | [R1. 동시 INSERT의 파일 소유 확인 실패](#r1-동시-insert의-파일-소유-확인-실패) | INSERT 실패, debug abort | zero-wait 범위와 파일 헤더 경합 | 소스 검토 중 |
| 2 | [R5. relocation undo가 재사용 슬롯을 덮어씀](#r5-relocation-undo가-재사용-슬롯을-덮어씀) | 커밋 행 손실, 힙 손상 | forward 페이지 공개와 sysop 경계 | 대기 |
| 3 | [R2. vacuum과 새 힙 페이지 할당의 교착](#r2-vacuum과-새-힙-페이지-할당의-교착) | INSERT 장시간 대기와 abort | PR 8235의 처리 범위와 미통합 변경 | 대기 |
| 4 | [R6. 미사용 복구 인덱스 제거](#r6-미사용-복구-인덱스-제거) | 불필요한 로그 형식 번호 고정 | 로그 생산자 존재 여부 | 대기 |
| 5 | [R3. 페이지 할당 시 전체 파일 스윕](#r3-페이지-할당-시-전체-파일-스윕) | 큰 파일의 INSERT 지연 | 스윕 발동 조건과 진행 위치 | 대기 |
| 6 | [R4. 재시작 후 bestspace 복원](#r4-재시작-후-bestspace-복원) | 빈 공간 미사용, 파일 증가 | redesign 후 적용 계획과 R3 의존성 | 후속 계획 확인 대기 |

## 진행 점검

- [x] **Blocking first steps.** 개인 정책, 두 저장소의 작업 상태, PR head, 세 종류의 댓글과 thread 상태를 확인한다.
- [x] **Independent workstreams.** 수정은 R1부터 순서대로 진행한다. R1의 호출 흐름 설명만 읽기 전용으로 독립 검토한다.
- [x] **Shared mutable state.** 원래 source와 docs checkout을 보존한다. 각 task worktree의 작성자는 한 명으로 유지한다.
- [x] **Smallest safe decomposition.** R1의 최소 수정과 동시성 검증을 한 단위로 한다. R2와 R5는 같은 vacuum 경로를 다루므로 이후 순서를 조정할 때 기존 변경을 다시 확인한다.

## 공통 완료 조건

1. 원문과 현재 코드가 같은 문제를 가리키는지 확인한다.
2. 호출자 계약, 보유 래치, 대기 순서, 실패 처리와 복구 경계를 설명한다.
3. 수용, 대안, 후속 작업, 반박 중 하나를 근거와 함께 결정한다.
4. 필요한 최소 수정을 task branch에 작성한다.
5. 문제를 보여 주는 실행과 수정 후 실행을 남긴다. 실행하지 못했으면 검증 미완료로 표시한다.
6. diff를 검토하고 task 파일만 커밋한다. 결과와 다음 단계를 이 문서에 갱신한다.
7. 로컬 통합은 완성된 변경을 검토한 뒤 사용자 승인을 받는다. 원격 동작은 해당 동작의 권한을 별도로 확인한다.

## R1. 동시 INSERT의 파일 소유 확인 실패

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4398825716). 대상은 `src/storage/oos_file.cpp`의 `oos_stats_find_page_in_bestspace`이다.

- [x] 원문을 수집한다.
- [x] 현재 함수에 `old_wait_msecs`, `LK_FORCE_ZERO_WAIT` 설정, 종료 시 복원이 있음을 확인한다.
- [x] 후보 페이지는 이미 `PGBUF_CONDITIONAL_LATCH`로 고정함을 확인한다.
- [ ] `file_is_vpid_in_file`의 헤더 읽기와 zero-wait 실패 전파를 확인한다.
- [ ] 할당 및 회수 경로의 래치 순서를 비교하고 수정 시 교착 가능성을 판단한다.
- [ ] 동일 테이블에 여러 세션이 OOS 값을 넣는 회귀 테스트를 준비하고 수정 전 실패를 확인한다.
- [ ] 함수 전체의 대기 시간 변경을 제거하는 안을 결정하고 수정한다.
- [ ] 수정 후 테스트, 빌드, 관련 bestspace 검증을 통과한다.
- [ ] 근거, 커밋, 검증 한계와 답글 초안을 기록한다.

소스에서 확인한 사실은 [대기 시간 변경](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L560-L582), [조건부 후보 래치와 소유 확인](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L654-L706), [대기 시간 복원](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L768-L772)이다. 오류 코드를 추가하는 것만으로는 경합으로 인한 INSERT 실패가 없어지지 않는다는 판단은 이 호출 흐름에 근거한다. 직접 재현 결과는 아직 없다.

검토 중인 최소 수정은 `old_wait_msecs`와 설정·복원 호출을 제거하는 것이다. 후보 페이지의 조건부 래치는 유지한다. 새 대기 모드나 재시도 계층은 추가하지 않는다.

## R5. relocation undo가 재사용 슬롯을 덮어씀

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409499688). 대상은 `vacuum_heap_record`의 `REC_RELOCATION` 경로이다.

- [x] 원문을 수집한다.
- [ ] forward 슬롯을 비우는 시점, bestpage 공개, 래치 해제, OOS 삭제, sysop abort 순서를 확인한다.
- [ ] 기존 CBRD-27781의 OOS 슬롯 충돌과 이번 힙 forward 슬롯 충돌의 차이를 확인한다.
- [ ] OOS 삭제 실패를 주입하고 동시 INSERT로 슬롯 재사용을 재현한다.
- [ ] 슬롯을 공개해도 되는 복구 경계를 결정하고 최소 수정한다.
- [ ] debug와 release의 오류 경로, 행 보존, 인덱스와 힙 일치, `checkdb`를 확인한다.
- [ ] 결과와 답글 초안을 기록한다.

리뷰어는 debug abort와 release의 커밋 행 손실을 보고했다. 이 작업에서 독립 재현하거나 기존 티켓과 동일한 결함이라고 판단한 상태는 아니다.

## R2. vacuum과 새 힙 페이지 할당의 교착

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399323155). 대상은 `vacuum_heap_oos_delete_within_sysop`과 `REC_RELOCATION` 호출자이다.

- [x] 원문을 수집한다.
- [ ] PR 8235의 현재 변경과 PR 7990에 포함된 범위를 확인한다.
- [ ] `REC_HOME`, `REC_BIGONE`, `REC_RELOCATION`의 래치 순서와 재시작 처리를 비교한다.
- [ ] 마지막 힙 페이지를 vacuum이 보유하고 INSERT가 새 페이지를 할당하는 실행을 재현한다.
- [ ] 조건부 헤더 조회, 페이지 해제, 대기, 레코드 재확인 구조를 결정한다.
- [ ] R5의 sysop 경계를 보존하면서 필요한 수정을 적용한다.
- [ ] 교착 재현과 일반 INSERT·DELETE·vacuum 실행을 검증하고 결과를 기록한다.

PR 8235가 고쳤을 수 있다는 원문의 설명은 확인할 대상이다. 이미 해결된 항목으로 표시하지 않는다.

## R6. 미사용 복구 인덱스 제거

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409612618). 대상은 `RVOOS_NOTIFY_VACUUM`이다.

- [x] 원문을 수집한다.
- [ ] 전체 소스에서 해당 로그의 생산자와 소비자를 검색한다.
- [ ] `recovery.h`, `recovery.c`, `mvcc.h`의 네 참조와 후속 번호를 확인한다.
- [ ] 현재 저장 형식 정책과 번호 재배치의 영향을 판단한다.
- [ ] 불필요한 참조를 제거하고 후속 인덱스를 조정한다.
- [ ] `rv_check_rvfuns`, OOS 변경 중 강제 종료와 복구, `checkdb`를 확인한다.
- [ ] 결과와 답글 초안을 기록한다.

## R3. 페이지 할당 시 전체 파일 스윕

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399899312). 대상은 `oos_alloc_page_with_reclaim`과 `oos_reclaim_sweep_step`이다.

- [x] 원문을 수집한다.
- [ ] `pending_deletes`, `swept_this_boot`, sweep cursor의 실제 상태 전이를 확인한다.
- [ ] vacuum 즉시 회수와 LSA 지연, non-MVCC 삭제, SA 즉시 삭제를 구분한다.
- [ ] 스윕 발동 조건 개선과 할당당 검사 상한을 각각 검토한다.
- [ ] 할당당 검사 페이지 수와 빈 페이지 회수의 진행 보장을 검증할 방법을 정한다.
- [ ] R4의 힌트 복원 계획과 충돌하지 않는 최소 수정을 결정한다.
- [ ] 실제 부하로 지연과 재사용을 검증한다. 리뷰어 수치를 자신의 측정으로 쓰지 않는다.
- [ ] 결과와 답글 초안을 기록한다.

## R4. 재시작 후 bestspace 복원

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409283403). 원문은 bestspace redesign 안정화 후 OOS에 적용할 계획을 먼저 밝힌다.

- [x] 원문과 후속 적용 계획을 수집한다.
- [ ] redesign의 소유 작업과 적용 시점을 확인한다.
- [ ] `num_pages`와 `num_other_high_best`의 기록 위치, 임시 헤더 갱신, scan cursor를 확인한다.
- [ ] 재시작 전후 동일한 빈 공간과 입력으로 페이지 재사용을 비교한다.
- [ ] 지금 수정할 부분과 redesign에서 처리할 부분을 결정한다.
- [ ] 지금 수정하는 경우 R3의 bounded sweep과 함께 회수·힌트 등록을 검증한다.
- [ ] 후속 처리라면 추적 위치와 완료 조건을 기록하고 원문을 해결 처리하지 않는다.

## 결정과 검증 기록

| 날짜 | 항목 | 결정 또는 결과 | 근거 | 남은 일 |
| --- | --- | --- | --- | --- |
| 2026-10-29 | 전체 | R1부터 한 항목씩 수정하고 검증한다. R5는 그다음 우선 검토 대상으로 둔다. | 사용자의 단계별 진행 요청, R5의 커밋 행 손실 보고 | R1 독립 재현과 최소 수정 |
| 2026-10-29 | R4 | 후속 적용 계획을 보존하고 즉시 수정 대상으로 확정하지 않는다. | 리뷰 원문의 redesign 안정화 후 적용 설명 | 소유 작업과 적용 시점 확인 |

수집 원본은 `/home/vimkim/temp/pr7990-hornet-review-20261029/review-snapshot.json`에 보관한다. 원본 JSON, 빌드 로그, 중간 산출물은 문서 저장소에 커밋하지 않는다.
