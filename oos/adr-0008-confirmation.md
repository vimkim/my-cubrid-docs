# ADR-0008 확정 요청: OOS 삭제를 확정 뒤 회수로 바꾸는 사양 개정

작성 2026-11-03 (Asia/Seoul). 확정 미팅 요청일 2026-11-04.

## 요청

OOS 정규 사양 개정안을 확정해 주시기를 요청한다. 개정안은 `cubrid-oos-context` 저장소의 ADR-0008(상태 `proposed`)과, 그에 맞춘 `OOS-CONTEXT.md` §2, §3, §4 수정이다. 브랜치는 `docs/adr-0008-reclaim-after-finality`, commit은 `591638b`이다. 이 브랜치는 로컬에만 있고 원격에 올리지 않았다. 확정 전까지는 기존 사양(context commit `281a940`)이 유효하다.

아래 일곱 항목을 하나씩 확정, 수정, 보류 중 하나로 정해 주면 된다. 근거의 수준은 다음과 같다.

- **결함.** 소스와 실행 기록으로 확인했다.
- **원인과 설계.** TLA+ 설계 모델로 확인했다.
- **구현과 성능.** 아직 없다.

## 왜 바꾸는가

`feature/oos-merge` `dcbf09e4f`에는 commit된 데이터를 잃거나 page를 손상시킬 수 있는 결함 세 개가 열려 있다.

- **CBRD-27858, CBRD-27781.** vacuum이 지운 slot을 다른 INSERT가 가져간 뒤, vacuum의 abort나 재시작 undo가 그 slot에 옛 레코드를 덮어쓴다.
- **CBRD-27237.** vacuum이 rollback된 UPDATE의 원래 chain을 지운다. 이 결함은 `dcbf09e4f`에서 실행으로 재현되었다.

TLA+ 모델은 이 결함들이 현재 설계의 가정에서 나온다는 것을 보였다. 첫째 가정은 "지운 공간은 되돌려지지 않는다"이다. 둘째 가정은 "확정되지 않은 정보로 chain 삭제를 정해도 된다"이다. 결함 하나하나를 막는 대신 이 두 가정을 없애는 것이 개정의 목적이다. 자세한 근거는 [설계 개정안](reclaim-redesign.md)과 [설계 결정의 TLA+ 검증](reclaim-decisions.md)에 있다.

## 확정할 항목

| # | 결정 | 고른 이유(모델 결과) | 영향 |
| --- | --- | --- | --- |
| 1 | OOS chunk 삭제는 undo하지 않는다. 삭제를 정한 트랜잭션이나 sysop은 회수 의도를 postpone으로 남기고, commit 뒤 회수기가 redo-only로 지운다. | 다른 후보와 비교했다. latch 유지는 vacuum worker끼리 교착한다. slot만 예약하면 바이트를 다른 INSERT가 가져간다. 바이트 예약과 page 제외는 가능하지만, 값 전체를 undo로 쓰는 비용이 남고 page 공간이 묶인다. | 새 recovery index가 필요하다. vacuum REMOVE와 eager 정리 경로를 바꾼다. |
| 2 | UPDATE가 버린 chain은 postpone이 commit 뒤에 남기는 `RVOOS_NOTIFY_VACUUM`으로만 vacuum에 알린다(A'). vacuum은 그 commit보다 오래된 snapshot이 끝난 뒤에 회수한다. | 다른 방식은 모두 반례가 나왔다. 지금의 undo image 판단은 rollback된 UPDATE에서 깨진다. commit 레코드 확인은 statement rollback 뒤 commit에서 깨진다. 사양의 commit hook 알림은 commit 레코드 전 crash에서 깨진다. snapshot을 기다리지 않으면 독자가 회수된 chain을 읽는다. | `RVOOS_NOTIFY_VACUUM`의 발행과 소비를 새로 구현한다. forward-walk 삭제를 지운다. |
| 3 | 회수기는 head부터 chain을 읽고 꼬리부터 지우며 head를 마지막에 지운다. 오류나 crash 뒤에는 끝날 때까지 다시 실행한다. | 다른 방식은 반례가 나왔다. head부터 지우면 나머지 chunk가 고아가 된다. 오류를 버리면 회수가 멈춘다. | 오류 시 서버를 멈출지(fail-stop), 회수 의도를 다시 쌓을지는 구현 때 정한다. |
| 4 | chunk header의 next 링크에 다음 chunk의 identity stamp를 둔다. header가 24B에서 32B가 된다. | stamp가 없으면, 재실행이 이미 지운 slot을 재사용한 다른 레코드를 지운다. | OOS 레코드 형식이 바뀐다. |
| 5 | LSA reclaim gate를 없앤다. | gate의 유일한 이유는 "끝나지 않은 삭제가 그 page로 undo될 수 있다"였다. 1번 결정으로 그런 undo가 없어지므로, 모델에서 gate 없이도 안전했다. | gate 코드를 지운다. 빈 page를 더 빨리 반납한다. |
| 6 | PR #7990 병합 전의 형식 변경은 storage-format revision 1을 유지한다. | 담당자 판단이다. 출시 전이고 ADR-0005가 개발 DB 재생성을 요구한다. | 이전 개발 빌드로 만든 DB는 다시 만들어야 한다. stamp로는 이 DB를 검출하지 못한다. |
| 7 | 엔진 반영은 성능 개선을 측정한 뒤에 한다. | 담당자 조건이다. | 측정 항목은 네 가지다. 회수한 값당 로그 바이트, OOS UPDATE 부하에서 vacuum의 log block 처리 시간, UPDATE와 DELETE 반복 뒤 OOS 파일 크기, INSERT와 UPDATE 지연(나빠지지 않아야 함)이다. |

1번부터 5번까지를 함께 쓴 조합은 하나의 모델로 다시 검사했다. 이 모델에는 오래된 snapshot을 쥔 독자, chain을 재사용하는 UPDATE(CBRD-27230), gate 없는 page 회수, crash가 함께 들어 있다. 조합은 모든 성질을 통과했다. 결정을 하나씩 되돌린 변형은 각자 반례를 냈다. 전체 검사는 137개이고 모두 기대값과 같았다.

## 사양에서 바뀌는 곳

- **§2 chunk 형식과 identity 검사.** 32B header로 바꾸고 next 링크에 stamp를 둔다. 회수기는 head stamp와 링크 stamp를 비교한다. continuation page도 회수되었을 수 있는 page로 고정한다. eager 정리는 회수 의도를 남긴다.
- **§3 UPDATE 소유권.** step 3은 postpone 알림과 snapshot horizon으로 바꾼다. step 4는 회수기의 identity 검사가 재실행을 멱등하게 만든다는 내용으로 바꾼다. REMOVE와 eager 경로는 chunk를 직접 지우지 않고 회수 의도를 남긴다.
- **§4 복구 불변식과 vacuum.** 불변식 7 "OOS 회수에는 undo가 없다"를 추가한다. Vacuum + OOS 절을 회수기 기준으로 다시 쓰고, 빈 page 회수에서 LSA gate를 지운다.
- **용어.** "LSA reclaim gate"를 빼고 "Reclaim intent(회수 의도)"와 "OOS reclaimer(회수기)"를 넣는다.

대체되는 기존 규칙의 원문은 설계 이력 문서의 "Reclaim before ADR-0008" 절에 보존했다.

## PR #7990에 미치는 영향

확정되면 지금의 OOS 삭제 코드는 사양과 맞지 않게 된다. 맞지 않는 곳은 다음과 같다.

- `RVOOS_DELETE`가 레코드 전체를 undo로 쓴다.
- forward-walk 삭제가 남아 있다.
- `RVOOS_NOTIFY_VACUUM`을 발행하는 코드가 없다.
- chunk header가 24B다.
- continuation page를 회수되었을 수 있는 page로 고정하지 않는다.
- LSA gate가 있다.

이 차이는 구현 관찰 문서에 줄 번호와 함께 기록했다. 2026-10-27 리뷰는 CBRD-27781을 병합 차단 항목으로 지적했다. 확정되면 CBRD-27781과 CBRD-27237의 해결 방식이 이 설계로 정해진다. CBRD-27858의 heap forward slot은 이 개정과 별개이며, draft PR #8348로 다룬다.

정해 주셔야 할 일정 선택지는 두 가지다.

| 선택 | 형식 변경 비용 | 일정 |
| --- | --- | --- |
| A. PR #7990 병합 전에 구현 | revision 1을 그대로 쓴다(6번). 개발 DB만 다시 만든다. | #7990 병합이 구현과 측정만큼 늦어진다. |
| B. #7990을 지금 구현으로 병합하고 뒤이어 구현 | 출시 전이면 ADR-0006에 따라 revision을 올리고 개발 DB를 다시 만든다. 출시 뒤에는 호환성 문제가 된다. | #7990은 먼저 병합한다. 그동안 CBRD-27781과 CBRD-27237은 열린 결함으로 남는다. |

## 확정 뒤 진행 순서

1. ADR-0008의 상태를 `accepted`로 바꾸고, 확정자와 날짜를 적은 뒤 사양 브랜치를 병합한다.
2. 구현을 PR 여러 개로 나눈다. 32B header와 링크 stamp, 회수 의도와 회수기, A' 알림과 snapshot horizon, forward-walk와 LSA gate 제거 순서를 제안한다.
3. PR마다 `cubrid-verify-vacuum-slot-undo` 같은 적합성 모델과 오류 주입 테스트를 갱신한다.
4. 7번의 성능 측정을 한 뒤 엔진에 반영한다.

## 확정 전에 알아야 할 한계

- 모델은 설계 모델이고 규모가 작다. 조합 모델은 row 하나, vacuum worker 하나, 방해 한 번으로 검사했다. 코드가 설계를 따르는지는 아직 검사하지 않았다.
- 성능은 측정하지 않았다. 지금 회수는 값 내용을 undo로 남기지만, undo 데이터는 압축될 수 있다. 그래서 실제 로그 감소량은 측정으로만 알 수 있다.
- HA replica, prepared 2PC, 여러 vacuum worker, eager 정리는 모델에 없다.
- postpone 재실행이 옛 MVCCID를 어떻게 다룰지는 구현 때 정해야 한다. CBRD-27237 심층 분석이 이 문제를 열린 항목으로 남겼다.

## 근거

- [설계 개정안](reclaim-redesign.md): 가정과 결함의 대응, D3 설계, 회수 로그 비용, 사양 개정안, U1 모델 결과.
- [설계 결정의 TLA+ 검증](reclaim-decisions.md): 결정별 후보, 반례, 통과 이유 불변식, 조합 모델.
- 모델과 실행 도구: `reclaim-model/` 디렉터리. `python3 oos/reclaim-model/check_decisions.py --out <새 디렉터리>`로 다시 실행할 수 있다.
- [CBRD-27237 수정 후보 심층 분석](../cbrd-27237/CBRD-27237-fix-options-deep-dive_dcbf09e_claude.md): A' 추천과 commit hook 장애 구간.
- 사양 개정안 원문: `cubrid-oos-context` 브랜치 `docs/adr-0008-reclaim-after-finality`, commit `591638b`.
