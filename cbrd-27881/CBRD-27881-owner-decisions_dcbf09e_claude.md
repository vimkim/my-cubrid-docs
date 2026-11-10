# CBRD-27881 담당자가 정할 것

작성일 2026-11-03 (Asia/Seoul). 같은 날 오후에 1절을 고쳤다. 2026-11-05에 1번과 1-b의 결정을 반영했다. 기준 commit은 `feature/oos-merge` `dcbf09e4f`이다.

CBRD-27881 야간 작업은 OOS 리팩토링 draft PR 7개를 만들고, 조사 결과를 [후보 조사 보고서](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md)에 정리했다. 이 문서는 그중 담당자가 직접 정해야 하는 것만 쉬운 말로 다시 적는다. 리팩토링 항목 7개의 결정은 [결정 필요 리팩토링 항목](CBRD-27881-needs-decision-items_dcbf09e_claude.md)에 따로 있다.

## 한눈에 보기

| 순서 | 정할 것 | 급한 정도 | 추천 | 할 일 |
| --- | --- | --- | --- | --- |
| 1 | CBRD-27237을 어떤 방식으로 고칠지 | 높음. 데이터 손실 결함이고 CBRD-27089의 최종 검증을 막는다. | **결정됨. A'** (2026-11-05) | 742 |
| 1-b | #8347 보류를 1번과 별개로 풀지 | 중간 | **결정됨. 푼다** (2026-11-03) | 677 |
| 2 | PR 7개를 언제, 누구에게 리뷰 요청할지 | 담당자가 직접 한다. | 실행 코드 변화가 적은 PR부터 | 없음 |
| 3 | #8371의 동작 차이를 받아들일지 | 중간. #8371 리뷰 전에 정한다. | 받아들인다 | 712 |
| 4 | DF-04를 새 버그 티켓으로 등록할지 | 낮음 | 작은 별도 티켓으로 등록한다 | 713 |

이미 정한 것은 다음과 같다.

- 1번은 A'로 정했다(2026-11-05, 팀장 승인). 아래 1절의 "결정"을 보라.
- #8347 보류는 1번과 별개로 풀었다(2026-11-03). 리뷰 요청은 677에서 담당자가 한다.
- PR 7개는 draft로 둔다. ready 전환, 리뷰어 지정, 리뷰 요청은 담당자가 직접 한다.
- #8367과 #8368의 commit 메시지는 `[CBRD-27881]`로 둔다. squash merge는 PR 제목(`[CBRD-27882]`, `[CBRD-27883]`)을 쓴다.

## 1. CBRD-27237을 어떤 방식으로 고칠지

**결정 (2026-11-05).** 수정 방식은 A'다. 팀장 승인을 받았다. A'는 UPDATE가 버린 OOS chain 목록을 commit 직전 로그가 아니라 postpone으로 남긴다. 그래서 commit이 디스크에 확정된 뒤에만 vacuum 알림이 생긴다. 아래 A의 "알림을 남긴 뒤 commit 로그를 쓰기 전에 서버가 죽는 경우"를 이 방식이 막는다. 이 절의 나머지는 결정 전 비교로 남겨 둔다. 아래의 "추천은 A다"와 "임시로 B" 판단은 A'로 대체됐다.

- 근거는 [CBRD-27237 수정 방식 deep dive](../cbrd-27237/CBRD-27237-fix-options-deep-dive_dcbf09e_claude.md)다. A의 crash 구간이 있다는 것과 임시 조치로는 B보다 단순 C가 낫다는 것을 여기서 정리했다.
- 임시 조치는 넣지 않는다. A'를 검증한 뒤에 PR #7990을 develop에 병합하기로 했기 때문이다.
- 알림은 CBRD-27237에서 먼저 구현한다. CBRD-27230의 chain 재사용 전체는 develop 병합 뒤에 한다(528).
- 구현과 검증은 742에서 한다. 사양 개정은 747(ADR-0008)에서 한다. 결정 원문은 work-tracker 705에 있다.

**무슨 문제인가.** 행을 UPDATE한 뒤 ROLLBACK하면 그 행은 원래 값으로 돌아가야 한다. 그런데 vacuum이 그 원래 값의 OOS 데이터를 지운다. vacuum은 지워진 데이터를 나중에 치우는 백그라운드 작업이다. 그 뒤 행을 읽으면 `-1389`(`ER_HEAP_OOS_CORRUPTED_RECORD`) 에러가 난다. 데이터 손실이다. 2026-11-03 새벽 `dcbf09e4f`에서 단위 테스트, gdb, SQL로 재현했다.

**원인.** vacuum은 UPDATE 로그의 undo 이미지(바뀌기 전 행)를 따라가서 옛 OOS 값을 지운다. 이 경로는 트랜잭션이 COMMIT했는지 ROLLBACK했는지 보지 않는다. ROLLBACK한 경우 undo 이미지가 가리키는 값은 옛 값이 아니라 다시 살아난 현재 값이다. 지금 있는 identity stamp 검사로도 막을 수 없다. 되살아난 행과 undo 이미지가 같은 stamp를 가지기 때문이다.

**왜 지금 정해야 하나.** CBRD-27237은 fix-before-release 결함이다. 2026-09-09 CBRD-27237 댓글은 이 결함을 CBRD-27089(#7600) 최종 검증의 선행 조건으로 정했다. JIRA의 "이슈 수행 방안"은 아직 TBD다.

**선택지.** [CBRD-27237 분석 문서](https://github.com/vimkim/my-cubrid-jira/blob/main/issues/CBRD-27237-oos-forward-walk-rollback-delete_dcbf09e_claude.md)는 후보 세 개를 비교한다. 처음 이 문서에는 A와 B만 적었다. 아래 표의 위험 판단은 그 분석 문서의 소스 추론이며, 실행으로 확인하지 않았다.

| | A. 사양 §3대로 고친다 | B. ROLLBACK한 트랜잭션을 건너뛴다 | C. 지우기 전에 현재 행을 확인한다 |
| --- | --- | --- | --- |
| 방법 | COMMIT한 UPDATE만 commit 직전에 `RVOOS_NOTIFY_VACUUM` 로그를 남긴다. 로그에는 UPDATE가 버린 OOS chain 목록이 들어간다. vacuum은 이 목록만 보고 지운다. undo 이미지를 따라가 지우는 지금 경로는 없앤다. | 지금 경로를 두고, vacuum이 그 경로에 들어가기 전에 트랜잭션이 COMMIT했는지 확인한다. | 지금 경로를 두고, chain을 지우기 전에 현재 행이 그 chain을 아직 가리키는지 확인한다. |
| 크기 | 크다. 새 로그 기록, commit hook, vacuum 처리 경로가 필요하다. | 작다. 다만 vacuum은 끝난 트랜잭션의 COMMIT 여부를 보관하지 않는다. 그 정보를 얻을 방법이 필요하다. | 중간. vacuum이 heap 페이지를 fix해야 하므로 latch 순서와 성능을 봐야 한다. |
| 남는 위험 | 부분 rollback이 있으면 COMMIT 시점에 실제로 버린 chain만 골라야 한다. | savepoint까지 되돌린 뒤 COMMIT한 트랜잭션은 막지 못한다. | 더 새로운 UPDATE가 아직 COMMIT하지 않았다면, 이전 snapshot이 아직 읽는 chain을 지울 수 있다. |
| 사양 | 승인된 사양 그대로다. | 사양 §3을 바꿔야 한다. | 사양 §3을 바꿔야 한다. |
| #8347 | 병합해도 된다. 알림을 구현할 때 실제 복구 인덱스를 새로 정의한다. | 병합해도 된다. | 병합해도 된다. |

**추천은 A다.** 이미 승인된 사양이다. 삭제 근거를 COMMIT한 연산으로만 한정해서, 문제를 만든 경로 자체를 없앤다. CBRD-27230의 chain 재사용과도 맞는다. B와 C는 지금 경로를 두기 때문에 부분 rollback이나 동시 UPDATE 같은 다른 조건에서 같은 손실이 남을 수 있다. release 전에 급히 막아야 하면 B를 임시로 넣고 A를 이어서 하는 방법도 있다. 다만 이 경우 vacuum 경로를 두 번 고치게 된다.

**A를 고르면 함께 정할 것.**

- 알림 부분만 CBRD-27237에서 먼저 구현할지, CBRD-27230의 chain 재사용과 함께 구현할지 정한다. CBRD-27230은 Open이고 담당자가 없다. 재사용이 없으면 UPDATE는 OOS 값을 늘 새 chain에 쓰므로, 버린 chain은 옛 행의 OOS chain 전부가 된다. 그래서 알림 부분만 떼어 구현할 수 있다고 본다. 이것은 설계 문서를 읽고 낸 추론이고 확인하지 않았다.
- 알림을 남긴 뒤 commit 로그를 쓰기 전에 서버가 죽는 경우를 확인한다. 복구는 그 UPDATE를 되돌리지만 알림 로그는 남는다. vacuum이 그 알림을 처리하면 같은 손실이 좁은 구간에 남는다. [CBRD-27230 설계](https://github.com/vimkim/my-cubrid-jira/blob/main/issues/CBRD-27230-oos-update-dedup_725a32c_claude.md)는 commit 전 장애에서 알림이 없다고 가정한다. 이 가정이 위 경우에도 맞는지는 두 문서를 읽고 낸 의문이고, 확인하지 않았다.

**#8347과의 관계.** 처음 이 문서는 "A면 #8347을 닫거나 범위를 줄인다"고 적었다. 그런데 [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841) 설명은 다음과 같이 적는다. 쓰이지 않는 인덱스를 지워도 CBRD-27230의 요구가 끝나거나 취소되지 않는다. 알림을 구현할 때 실제 복구 인덱스를 다시 정의해야 한다. 따라서 어느 선택지를 골라도 #8347은 병합할 수 있다. A를 고르고 #8347을 먼저 병합하면, 지운 인덱스 하나를 나중에 다시 추가하게 된다. CBRD-27841은 병합 뒤 로그 형식이 고정되기 전에 정리하려는 작업이다. 그래서 `feature/oos-merge` 안에서 인덱스를 지웠다가 다시 추가하는 비용은 작다고 본다(추론). **추천은 #8347 보류를 1번과 별개로 푸는 것이다.**

**정한 뒤 할 일.**

- CBRD-27237의 "이슈 수행 방안"에 고른 방식을 적는다.
- A면 알림 로그의 내용과 기록 위치를 정하고 구현한다. 위 장애 구간을 함께 확인한다. B나 C면 사양 §3을 고친 뒤 수정한다.
- 어느 쪽이든 회귀 테스트 `OosRealVacuum.RolledBackUpdateKeepsCommittedOosAfterVacuum`을 켜서 통과시킨다. 이 테스트를 `dcbf09e4f`로 옮긴 commit은 로컬 브랜치 `CBRD-27881-df03-probe`의 `338b7a1dd`다. 지금은 두 번 모두 실패한다.
- CBRD-27237의 Triage Request는 다음도 확인하라고 한다. SQL 재현 시나리오 세 개, 다른 위치로 옮겨진 행, kill -9 뒤 재기동이다. COMMIT한 UPDATE의 옛 chain이 계속 회수되는지도 확인한다.

**자세히 읽을 자료.** 아래 순서로 읽으면 된다.

1. [CBRD-27237 분석 문서](https://github.com/vimkim/my-cubrid-jira/blob/main/issues/CBRD-27237-oos-forward-walk-rollback-delete_dcbf09e_claude.md). 문제, 재현, 후보 세 개의 비교가 한 곳에 있다. JIRA 본문보다 자세하다. 끝의 "Options for Analysis" 표가 핵심이다.
2. [OOS 사양 §3 UPDATE ownership](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f69a7ec0de8a0b97ad8da32b463ecf0e8c/OOS-CONTEXT.md?plain=1#L208-L222). A의 근거다. undo 이미지는 삭제 근거가 될 수 없다는 소유권 규칙과 commit hook 위치가 있다. 같은 파일의 [Vacuum + OOS 절](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f69a7ec0de8a0b97ad8da32b463ecf0e8c/OOS-CONTEXT.md?plain=1#L245-L249)과 [implementation-observations의 CBRD-27237 절](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f69a7ec0de8a0b97ad8da32b463ecf0e8c/docs/reference/implementation-observations.md#cbrd-27237-rollback-and-vacuum)도 함께 본다.
3. [CBRD-27230 이슈 문서](https://github.com/vimkim/my-cubrid-jira/blob/main/issues/CBRD-27230-oos-update-dedup_725a32c_claude.md)의 "2. 알림 레코드"와 "3. 제거 및 불변 항목". A를 실제로 어떻게 만드는지 적었다. 2026-08 문서라 "generation"이라고 쓴 것은 지금의 identity stamp다.
4. [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237) 댓글 두 개와 [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841) 설명.
5. 코드. 삭제 경로 본체는 [vacuum_oos.cpp L248-L369](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum_oos.cpp#L248-L369)이고, 호출하는 곳은 [vacuum.c L3616-L3621](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3616-L3621)과 [vacuum.c L3757-L3765](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3757-L3765)다.

## 2. PR 7개를 언제, 누구에게 리뷰 요청할지

**담당자가 직접 한다.** 아래 표는 참고용 추천 순서다.

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

실행 코드 변화가 적은 PR이 먼저 들어가면, 뒤 PR의 리뷰가 그만큼 가벼워진다. ready 전환은 `gh pr ready <번호> --repo CUBRID/cubrid`로 한다.

## 3. #8371의 동작 차이를 받아들일지

할 일 712번이다. #8371은 heap 테이블을 지울 때 OOS 파일도 지우는 코드 두 벌을 하나로 합친다. 정상 경로의 동작은 같다. heap header 페이지가 손상된 경우에만 다르다.

| 경우 | 이전 코드 | #8371 |
| --- | --- | --- |
| 정상 | heap 파일과 OOS 파일을 모두 지운다. | 같다. |
| header 손상, debug 빌드 | `ASSERT_ERROR`에서 멈춘다. | 같다. |
| header 손상, release 빌드 | heap 파일과 OOS 파일을 모두 남기고 `NO_ERROR`를 반환한다. | heap 파일은 지우고 OOS 파일만 남긴다. |

**추천은 받아들이는 것이다.** 손상된 header에서만 열리는 경로이고, 새 동작이 남기는 파일이 더 적다. 독립 리뷰도 같은 판단을 했다. 받아들이지 않으면 이전 동작을 그대로 지키도록 PR을 고친다.

## 4. DF-04를 새 버그 티켓으로 등록할지

할 일 713번이다. 조사 중 찾은 결함 후보 세 개를 2026-11-03 12:40에 JIRA에서 다시 찾아봤다.

| ID | 내용 | JIRA 상태 |
| --- | --- | --- |
| DF-01 | OOS 빈 공간을 다시 찾는 tier-3 sync가 운영 경로에서 실행되지 않는다. | 이미 등록됨. [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213)(Open, 담당자 없음)이 같은 원인을 적고, sync를 지우고 heap bestspace 재설계 기반으로 바꾸기로 했다. |
| DF-02 | OOS로 옮기는 기준 크기가 사양(4,060 B)과 다르다(4,086 B). | 이미 처리 중. [CBRD-27057](https://jira.cubrid.org/browse/CBRD-27057) 댓글(2026-11-03 01:54)대로 [#8299](https://github.com/CUBRID/cubrid/pull/8299)의 commit `4c3c8d791`이 고친다. |
| DF-04 | `oos_find_best_page`가 앞쪽 실패 경로에서 에러를 버리고 새 페이지를 할당한다. `ER_INTERRUPTED`도 버린다. | 등록된 티켓 없음 |

**DF-04가 왜 문제인가.** 사용자가 INSERT를 중단시켜도 OOS 쪽은 멈추지 않고 페이지를 하나 더 할당할 수 있다. 버려진 에러가 뒤의 판단을 흐릴 수도 있다. 둘 다 코드에서 유도한 추론이고, 실행으로 확인하지 않았다.

**선택지.** (a) 작은 Correct Error 티켓을 새로 만든다. (b) CBRD-27213의 완료 조건에 넣는다. (c) 보고서 기록으로만 둔다.

**추천은 (a)다.** 수정이 한 함수 안에서 끝날 것으로 보인다(추론). CBRD-27213은 담당자가 없는 큰 재설계라 언제 끝날지 모른다. 그리고 리팩토링 R-22(#8330 병합 뒤 `oos_find_best_page` fallback 정리)는 DF-04를 고친 뒤에 해야 한다. 말해 주면 티켓 초안을 쓴다.

**후속 (2026-11-10).** (a)로 정했다. DF-04는 [CBRD-28017](https://jira.cubrid.org/browse/CBRD-28017)로 등록됐다. OOS TODO [CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978)의 Sub-task이고 담당은 Joon Min이다. R-22는 CBRD-28017을 고친 뒤에 한다.
