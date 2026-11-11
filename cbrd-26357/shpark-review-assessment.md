# PR 7990 shparkcubrid 리뷰 충족 가능성 검토

작성: 2026-11-11 (Asia/Seoul). Work919. 독자: 작성자와 머지를 결정할 팀.

## 질문과 결론

- 질문: shparkcubrid(4팀 팀장)가 [#7990](https://github.com/CUBRID/cubrid/pull/7990)에 남긴 리뷰를 현재 브랜치로 만족시킬 수 있는가. 무엇이 더 필요한가.
- 결론: 엔진 작업으로 풀 수 있는 항목과 팀 결정이 먼저 필요한 항목이 나뉜다.
  - 데이터 손실 2건은 #8434를 `feature/oos-merge`에 먼저 넣으면 풀린다.
  - 성능 기준 2(4~16KB 행 읽기)는 지금 기본 임계값으로는 만족시킬 수 없다. 임계값을 올리거나 리뷰어와 기준을 다시 정해야 한다.
  - CDC와 구조 검토도 팀 결정이 먼저다.
  - 그래서 CHANGES_REQUESTED는 코드만으로는 해소되지 않는다.

## 기준과 방법

- 엔진 PR head는 `feature/oos-merge` = `67220b7e230f`이고 #8299가 병합된 상태다. 수정 PR #8434 head는 `0d9732a63`이다.
- 리뷰 원문 23개(리뷰 본문 4, inline 스레드 3, 대화 탭)를 수집했다. 범위는 vimkim의 OOS PR(#7990, #3551)이다. #3551은 [tc-review-disposition.md](tc-review-disposition.md)에서 처리했다.
- Herdr 탭 3개에서 `claude-account run 2`(bypass) 에이전트가 항목을 나눠 읽기 전용으로 조사했다. 상세 근거, 파일:줄, 답글 초안은 각 보고서에 있다.
  - [report-A-data-loss.md](shpark-review-20261111/report-A-data-loss.md): 데이터 손실 2건
  - [report-B-perf.md](shpark-review-20261111/report-B-perf.md): 성능 기준 1·2, UPDATE 비용, 측정 계획
  - [report-C-decisions.md](shpark-review-20261111/report-C-decisions.md): CDC, 기준 3, 구조 검토, SQL trace, 해소 체크리스트
- 결론을 지탱하는 주장은 작성자가 직접 다시 확인했다(아래 "직접 확인").
- 이 검토에서 빌드, 벤치마크, 코멘트 게시는 하지 않았다.

## 항목별 판정

| 항목 | 리뷰어 요구 | 67220b7 | 만족시키는 길 | 판정 |
| --- | --- | --- | --- | --- |
| 리뷰 1번, CBRD-27237 | UPDATE rollback 뒤 vacuum이 OOS 값을 지움. 후속에서 "11.5 전 반드시" | 결함 있음 | #8434가 undo 이미지 기반 회수를 없애고 commit 뒤 postpone으로만 회수한다. #8434를 먼저 병합하고 리뷰어 SQL 재현을 다시 돌려 붙인다 | 엔진 작업으로 가능 |
| 리뷰 3번, CBRD-27781 | OOS 삭제 undo가 재사용된 슬롯을 덮어씀 | 결함 있음 | #8434가 `RVOOS_DELETE`를 redo-only로 바꾸고 회수를 commit 뒤로 미룬다. 리뷰어가 제안한 방법과 다르니 이유를 설명한다 | 엔진 작업으로 가능 |
| 리뷰 2번, 넓은 행 | 릴리스 노트 | 처리 완료 | 회신 r4536795579, JIRA CBRD-26357 코멘트 4778347 | 충족 |
| 리뷰 4번, CDC 격리 | 팀 차원 결정을 PR 본문에 | 본문에는 "QA팀과 협의"만 있음 | 결정자, 사용자 영향(rc=-10 중단, 재사용 slot의 조용한 오값, flashback), 11.5 조건을 정해 본문에 적는다. CBRD-26939는 Minor로 남아 있다 | 팀 결정 필요 |
| 성능 기준 1 | OOS 없는 테이블이 develop보다 느리지 않을 것 | 선행 조건(#8299) 충족. 최종 head와 현재 develop의 비교 측정은 없음 | 마지막 측정(`4c3c8d791` 대 `4781495f`)은 스캔 +0.79%, 조건 스캔 −0.83%, UPDATE −1.34%(좋아지면 +). 현재 merge-base `2dd94e32`와 다시 재서 공유한다 | 측정으로 가능성 높음 |
| 성능 기준 2 | 기본 설정에서 4~16KB 행 전체 읽기가 develop보다 느리지 않을 것 | 기본 임계값(4-record 목표, 4,060B)이 정확히 이 구간을 OOS로 보낸다. 값마다 페이지 고정 3번, 복사 2번이 남아 있다 | 최적화만으로는 어렵다. 임계값을 페이지 경계로 올리고 파라미터로 두면 충족할 수 있다. 대가는 4~16KB 좁은 스캔 이득 포기, 4-record 설계 철회, OOS TC 재작업이다 | 팀 결정 필요 |
| 성능 기준 3 | 현재 버전의 이득·손해 공유, CBRD-27788 결과 | `dcbf09e` 기준 SELECT 결과만 있음. PR에 공유하지 않음 | #8434 반영 head에서 리뷰어 세트, CBRD-27788 SELECT, DML을 재측정해 한 표로 공유한다 | 측정으로 가능 |
| UPDATE 재기록 | 바뀌지 않은 OOS 값을 새로 씀(+73.7%) | 그대로 | 값 재사용(CBRD-27230)은 두 버전이 chain을 공유해 27237류 소유권 문제가 생긴다. #8434 뒤 별도로 한다. 리뷰어는 머지 기준이 아니라 의견으로 물었다 | 머지 범위는 팀 결정 |
| 구조 검토 | 11.5 형식이 굳기 전에 큰 값을 heap 안에 두는 방식 검토 | 2주째 무응답 | 원인 진단은 내부 근거(design-contradictions, Sidecar POC)가 대체로 지지한다. 비교 문서와 11.5 구조에 대한 팀 결정으로 답한다 | 팀 결정 필요 |
| SQL trace | OOS 읽기를 trace에서 구분 | #8491 draft | 머지 조건이 아니다. #8491을 feature에 먼저 넣으면 함께 들어간다 | 조건 아님 |

## 직접 확인 (작성자 재확인, 2026-11-11)

- `67220b7:src/query/vacuum.c:3751`, `:3896`이 `vacuum_forward_walk_reclaim_oos`를 부른다. `#8434 0d9732a`의 `src`에는 이 함수와 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`이 없다.
- `67220b7:src/storage/oos_file.cpp:3159`는 `ANCHORED`로 초기화한다. `src/transaction/recovery.c:889`에서 `RVOOS_DELETE`의 undo는 `oos_rv_redo_insert`이고, `0d9732a`에서는 `NULL`이다.
- #8434는 OPEN이고 draft가 아니며 APPROVED 상태다. base는 `feature/oos-merge`다.
- `67220b7:src/storage/heap_file.c:13737`은 `HEAP_OOS_MIN_RECS_PER_PAGE 4`이고, `:13746`은 `heap_oos_inline_target_size`다. `system_parameter.c`에는 OOS 임계값 파라미터가 없다.
- #8491은 draft다. #7990 본문의 CDC 문단은 "QA팀과 협의"만 적었다. CBRD-26939의 Priority는 Minor다.

## 팀이 정할 것

1. **기본 임계값.** 기준 2를 맞추려면 임계값을 올려야 하고, 그러면 4~16KB 구간의 OOS 이득을 포기한다. 이득을 지키려면 리뷰어와 기준 2를 다시 정해야 한다. 임계값은 저장 정책이고 디스크 형식이 아니다. 그래서 보수적으로 출시한 뒤 나중에 낮출 수 있다.
2. **CDC.** 결함을 안고 머지하되 11.5 전에 CBRD-26939를 끝낼지, `supplemental_log`가 켜진 DB에서 OOS를 끌지, 결함을 안고 출시할지 정한다.
3. **11.5 구조.** OOS + ADR-0008로 갈지, heap 레코드 방식과 비교한 뒤 정할지 정한다.

## 엔진 쪽 순서 (결정과 무관하게 할 일)

1. #8434 CI가 끝나면 `feature/oos-merge`에 병합하고 feature CI를 돌린다.
2. 리뷰어 SQL 재현(rollback, savepoint, 작은 컬럼, NULL, kill -9)을 병합본에서 돌려 1·3번 답글에 붙인다.
3. 최종 head와 현재 merge-base로 기준 1·3을 측정해 PR에 공유한다. 측정 계획은 report-B에 있다.
4. 결정이 나면 PR 본문의 CDC 문단과 성능 절을 고치고 재리뷰를 요청한다.

## 한계

- 리뷰어 시나리오가 #8434에서 닫힌다는 판단은 코드 경로와 단위 테스트에 근거한 것이다. 리뷰어 SQL 재현을 #8434 위에서 실행한 기록은 없다.
- 기준 1·2의 현재 수치는 측정하지 않았다. 마지막 측정은 옛 develop 기준이다.
- report-C의 Sidecar 비교 수치는 미공개 scratch 기록을 인용했다. 공유하려면 다시 측정해야 한다.
