# CBRD-27881 담당자가 정할 것

작성일 2026-11-03 (Asia/Seoul). 기준 commit은 `feature/oos-merge` `dcbf09e4f`이다.

CBRD-27881 야간 작업은 OOS 리팩토링 draft PR 7개를 만들고, 조사 결과를 [후보 조사 보고서](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md)에 정리했다. 이 문서는 그중 담당자가 직접 정해야 하는 네 가지만 쉬운 말로 다시 적는다. 리팩토링 항목 7개의 결정은 [결정 필요 리팩토링 항목](CBRD-27881-needs-decision-items_dcbf09e_claude.md)에 따로 있다.

## 한눈에 보기

| 순서 | 정할 것 | 급한 정도 | 추천 |
| --- | --- | --- | --- |
| 1 | CBRD-27237을 어떤 방식으로 고칠지 | 높음. #8347이 이 결정을 기다린다. | 사양 §3 방식(A) |
| 2 | PR 7개를 언제, 누구에게 리뷰 요청할지 | 중간 | 실행 코드 변화가 적은 PR부터 |
| 3 | #8371의 동작 차이를 받아들일지 | 중간. #8371 리뷰 전에 정한다. | 받아들인다 |
| 4 | DF-04를 새 버그 티켓으로 등록할지 | 낮음 | 작은 별도 티켓으로 등록한다 |

이미 정한 것은 다음과 같다.

- #8347은 1번이 정해질 때까지 보류한다. draft 상태이므로 따로 손대지 않았다.
- PR 7개는 draft로 둔다. ready 전환과 리뷰어 지정은 담당자가 한다.
- #8367과 #8368의 commit 메시지는 `[CBRD-27881]`로 둔다. squash merge는 PR 제목(`[CBRD-27882]`, `[CBRD-27883]`)을 쓴다.

## 1. CBRD-27237을 어떤 방식으로 고칠지

**무슨 문제인가.** 행을 UPDATE한 뒤 ROLLBACK하면 그 행은 원래 값으로 돌아가야 한다. 그런데 vacuum이 그 원래 값의 OOS 데이터를 지운다. vacuum은 지워진 데이터를 나중에 치우는 백그라운드 작업이다. 그 뒤 행을 읽으면 `-1389`(`ER_HEAP_OOS_CORRUPTED_RECORD`) 에러가 난다. 데이터 손실이다. 2026-11-03 새벽 `dcbf09e4f`에서 단위 테스트, gdb, SQL로 재현했다.

**원인.** vacuum은 UPDATE 로그의 undo 이미지(바뀌기 전 행)를 따라가서 옛 OOS 값을 지운다. 이 경로는 트랜잭션이 COMMIT했는지 ROLLBACK했는지 보지 않는다. ROLLBACK한 경우 undo 이미지가 가리키는 값은 옛 값이 아니라 다시 살아난 현재 값이다.

**왜 지금 정해야 하나.** 고치는 방식에 따라 #8347(CBRD-27841)을 병합해도 되는지가 달라진다. #8347은 지금 아무 데서도 쓰지 않는 복구 인덱스 `RVOOS_NOTIFY_VACUUM` 하나를 지우는 PR이다. 그런데 사양 §3의 해결책이 바로 그 인덱스를 쓴다.

**선택지.**

| | A. 사양 §3대로 고친다 | B. 지금 경로를 두고 ROLLBACK만 걸러낸다 |
| --- | --- | --- |
| 방법 | COMMIT한 UPDATE만 commit 직전에 `RVOOS_NOTIFY_VACUUM` 로그를 남긴다. 로그에는 지워도 되는 옛 OOS chain 목록이 들어간다. vacuum은 이 목록만 보고 지운다. undo 이미지를 따라가 지우는 지금 경로는 없앤다. | vacuum이 undo 이미지를 따라가는 지금 경로를 두고, ROLLBACK한 트랜잭션의 로그는 건너뛰게 한다. |
| 크기 | 크다(추론). commit hook, 새 로그 기록, vacuum 소비 경로가 필요하다. | 작다(추론). |
| 사양 | 이미 승인된 사양 그대로다. | 사양 §3을 바꿔야 한다. |
| #8347 | 닫거나, `RVOOS_NOTIFY_VACUUM` 삭제를 빼고 다른 미사용 인덱스 `RVREPL_OOS_DELETE` 삭제(R-29)만 담도록 바꾼다. | 그대로 병합해도 된다. |
| 확인하지 않은 것 | 구현 작업량 | 사양 §3이 함께 다루는 공유 chain(여러 행 버전이 같은 OOS chain을 함께 쓰는 경우)도 B로 막히는지 |

**추천은 A다.** 이미 승인된 사양이고, 문제를 만든 경로 자체를 없앤다. B는 ROLLBACK이라는 증상 하나만 막는다. 그리고 사양 변경과 공유 chain 검증이 따로 필요하다. release 전에 급히 막아야 하면 B를 임시로 넣고 A를 이어서 하는 방법도 있다. 다만 이 경우 vacuum 경로를 두 번 고치게 된다.

**정한 뒤 할 일.** A면 #8347의 범위를 바꾸거나 닫는다. B면 #8347 보류를 풀고 사양 §3을 고친다. 어느 쪽이든 회귀 테스트로 `OosRealVacuum.RolledBackUpdateKeepsCommittedOosAfterVacuum`을 쓸 수 있다. 이 테스트를 `dcbf09e4f`로 옮긴 commit은 로컬 브랜치 `CBRD-27881-df03-probe`의 `338b7a1dd`다. 지금은 두 번 모두 실패한다.

## 2. PR 7개를 언제, 누구에게 리뷰 요청할지

7개 모두 `feature/oos-merge` 대상 draft이고 gha-ci 5개 항목을 통과했다. 서로 의존하지 않으므로 어떤 순서로 병합해도 된다. GitHub CI는 OOS 단위 테스트를 돌리지 않는다. 그래서 실행 코드를 바꾼 6개는 로컬에서 OOS ctest 44개를 수정 전후로 돌려 확인했다.

| 추천 순서 | PR | 무엇을 바꾸나 | 크기 | 리뷰어가 볼 곳 |
| --- | --- | --- | --- | --- |
| 1 | [#8367](https://github.com/CUBRID/cubrid/pull/8367) | 쓰이지 않는 매크로와 테스트 함수, 항상 0인 인자를 지운다. | +3/-14 | `oos_stats_update`의 인자를 지운 뒤 남은 `if (freespace > 0)` |
| 2 | [#8368](https://github.com/CUBRID/cubrid/pull/8368) | 두 테스트 header에 복사된 helper를 한 header로 모은다. 엔진 코드는 그대로다. | +165/-272 | 옮긴 helper 9개가 원래와 같은지 |
| 3 | [#8373](https://github.com/CUBRID/cubrid/pull/8373) | 코드와 다른 사실을 적은 주석을 고친다. 실행 코드는 빈 `if` 하나만 사라진다. | +38/-44 | 새 주석이 코드와 맞는지 |
| 4 | [#8370](https://github.com/CUBRID/cubrid/pull/8370) | 네 곳에 반복된 6줄을 helper 하나로 합친다. | +16/-27 | helper 뒤에 남긴 `pgbuf_unfix_and_init` 위치 |
| 5 | [#8369](https://github.com/CUBRID/cubrid/pull/8369) | 두 곳에 복사된 LOB 복사 코드를 helper 하나로 합친다. | +64/-75 | 두 호출부의 에러 처리 |
| 6 | [#8371](https://github.com/CUBRID/cubrid/pull/8371) | heap 삭제 두 경로에 복사된 OOS 파일 정리 코드를 합친다. | +41/-38 | 아래 3번의 동작 차이 |
| 7 | [#8372](https://github.com/CUBRID/cubrid/pull/8372) | ALTER에서 복사된 플래그 판정 블록 세 개를 합친다. | +53/-79 | develop에 원래 있던 INVISIBLE 블록도 바뀐다. |

**추천.** 위 순서로 한두 개씩 ready로 바꾼다. 실행 코드 변화가 적은 PR이 먼저 들어가면, 뒤 PR의 리뷰가 그만큼 가벼워진다. 리뷰어는 담당자가 정한다. ready 전환은 `gh pr ready <번호> --repo CUBRID/cubrid`로 하거나, 말해 주면 대신 한다.

## 3. #8371의 동작 차이를 받아들일지

#8371은 heap 테이블을 지울 때 OOS 파일도 지우는 코드 두 벌을 하나로 합친다. 정상 경로의 동작은 같다. heap header 페이지가 손상된 경우에만 다르다.

| 경우 | 이전 코드 | #8371 |
| --- | --- | --- |
| 정상 | heap 파일과 OOS 파일을 모두 지운다. | 같다. |
| header 손상, debug 빌드 | `ASSERT_ERROR`에서 멈춘다. | 같다. |
| header 손상, release 빌드 | heap 파일과 OOS 파일을 모두 남기고 `NO_ERROR`를 반환한다. | heap 파일은 지우고 OOS 파일만 남긴다. |

**추천은 받아들이는 것이다.** 손상된 header에서만 열리는 경로이고, 새 동작이 남기는 파일이 더 적다. 독립 리뷰도 같은 판단을 했다. 받아들이지 않으면 이전 동작을 그대로 지키도록 PR을 고친다.

## 4. DF-04를 새 버그 티켓으로 등록할지

조사 중 찾은 결함 후보 세 개를 2026-11-03 12:40에 JIRA에서 다시 찾아봤다.

| ID | 내용 | JIRA 상태 |
| --- | --- | --- |
| DF-01 | OOS 빈 공간을 다시 찾는 tier-3 sync가 운영 경로에서 실행되지 않는다. | 이미 등록됨. [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213)(Open, 담당자 없음)이 같은 원인을 적고, sync를 지우고 heap bestspace 재설계 기반으로 바꾸기로 했다. |
| DF-02 | OOS로 옮기는 기준 크기가 사양(4,060 B)과 다르다(4,086 B). | 이미 처리 중. [CBRD-27057](https://jira.cubrid.org/browse/CBRD-27057) 댓글(2026-11-03 01:54)대로 [#8299](https://github.com/CUBRID/cubrid/pull/8299)의 commit `4c3c8d791`이 고친다. |
| DF-04 | `oos_find_best_page`가 앞쪽 실패 경로에서 에러를 버리고 새 페이지를 할당한다. `ER_INTERRUPTED`도 버린다. | 등록된 티켓 없음 |

**DF-04가 왜 문제인가.** 사용자가 INSERT를 중단시켜도 OOS 쪽은 멈추지 않고 페이지를 하나 더 할당할 수 있다. 버려진 에러가 뒤의 판단을 흐릴 수도 있다. 둘 다 코드에서 유도한 추론이고, 실행으로 확인하지 않았다.

**선택지.** (a) 작은 Correct Error 티켓을 새로 만든다. (b) CBRD-27213의 완료 조건에 넣는다. (c) 보고서 기록으로만 둔다.

**추천은 (a)다.** 수정이 한 함수 안에서 끝날 것으로 보인다(추론). CBRD-27213은 담당자가 없는 큰 재설계라 언제 끝날지 모른다. 그리고 리팩토링 R-22(#8330 병합 뒤 `oos_find_best_page` fallback 정리)는 DF-04를 고친 뒤에 해야 한다. 말해 주면 티켓 초안을 쓴다.
