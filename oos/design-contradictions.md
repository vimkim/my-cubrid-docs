# OOS 회수 프로토콜의 설계 주장과 안전성 모순

작성일: 2026-11-04 (Asia/Seoul).

## 초록

이 글은 현재 OOS 회수 규칙이 데이터 보존 요구와 양립하는지 묻는다. 독자는 OOS 설계 담당자와 저장 엔진 검토자다. 분석 대상은 `feature/oos-merge`의 `dcbf09e4f`이며, 기존 redesign 문서의 소스 분석과 실행·모델 검사 기록을 재구성한다.

구현 사실과 안전 요구를 주장 A부터 H까지로 나누고, 두 주장 집합이 동시에 성립할 수 없음을 반례 실행으로 보인다. 첫째, 원래 주소로 돌아오는 물리 undo, 확정 전 공간 재사용, 그 사이의 다른 트랜잭션 commit은 commit된 레코드 보존과 충돌한다. 둘째, rollback으로 살아난 chain, 남아 있는 UPDATE undo image, 그 image에 근거한 삭제는 현재 값 보존과 충돌한다.

결론은 회수 프로토콜의 일부 규칙을 바꿔야 한다는 것이다. 이 논증만으로 D3가 유일한 해법이 되지는 않는다. 기존 모델은 공간 예약과 page 제외 방식도 대안으로 남긴다. D3의 실제 구현 정확성과 성능은 별도 검증 대상이다.

## 1. 분석 범위와 근거

OOS는 큰 속성값을 별도 value chain에 저장하고, heap 레코드에는 chain의 head OOS OID, 길이, identity stamp를 담은 stub을 둔다. 회수기는 필요 없어진 chain의 chunk를 삭제한다. 이 글은 이 회수 과정의 소유권, 공간 수명, 복구 경계를 다룬다. 값 분리 정책이나 SELECT의 일반적인 성능을 평가하지 않는다.

| 항목 | 기준 |
| --- | --- |
| 엔진 저장소 | `CUBRID/cubrid` |
| 엔진 revision | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, `feature/oos-merge` |
| 재사용한 분석 문서 | 이 저장소 `a9644b8`의 [설계 개정안][R1], [결정별 검증][R2], [확정 요청서][R3] |
| 기존 정규 사양 | `vimkim/cubrid-oos-context`의 `281a940eafb5db507bce8e75a51de0ea94b4bfde`, [OOS-CONTEXT.md][N1] |
| 사양 내용 확인 | SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63` |
| 관련 결함 | CBRD-27781, CBRD-27858, CBRD-27237. page 수명은 CBRD-26786, identity는 CBRD-26950과 관련된다. |

이 글에서 "현재 구현"은 위 엔진 revision을 뜻한다. 원격 브랜치나 JIRA의 최신 상태를 뜻하지 않는다. 소스 링크와 실행 결과는 기존 보고서에서 재인용했으며, 이 글을 작성하면서 엔진이나 TLA+ 검사를 다시 실행하지 않았다.

근거의 종류는 다음과 같이 구분한다.

- **구현 사실**은 기존 보고서가 해당 revision의 소스에서 확인한 동작이다.
- **안전 요구**는 구현이 만족해야 하는 데이터 보존 조건이다.
- **논증**은 구현 사실이 허용하는 실행을 구성해 안전 요구 위반을 도출한다.
- **모델 결과**와 **실행 관찰**은 기존 기록에서 가져온 증거다. 논증 전체를 새로 실행 검증했다는 뜻은 아니다.
- **설계 제안**은 현재 구현이나 채택 완료된 사양과 구분한다.

## 2. 정의와 논증 방법

물리 주소 $r=(p,s)$ 는 page $p$ 의 slot $s$ 다. 하나의 주소에는 한 시점에 하나의 레코드만 있을 수 있다. $x$ 와 $y$ 는 내용과 소유자가 다른 레코드다. $V$ 는 vacuum의 회수 sysop, $T$ 는 별도의 사용자 트랜잭션이다. chain은 $c$, UPDATE 연산은 $u$ 로 쓴다.

`UndoPending(V, r)`은 $V$ 가 실패하면 삭제한 레코드를 $r$ 에 복원해야 하는 상태다. `Reusable(r)`은 다른 INSERT가 $r$ 을 할당받을 수 있는 상태다. `Needed(c)`는 현재 row, 유효한 snapshot, 또는 정당한 rollback·복구가 chain $c$ 를 필요로 하는 상태다. `Intact(c)`는 그 값을 읽는 데 필요한 chunk가 온전히 남아 있는 상태다.

회수와 관련된 안전 요구 두 개를 사용한다. $P_1$ 은 다른 트랜잭션의 undo가 commit된 레코드와 그 참조를 훼손하지 않아야 한다는 요구다. 보존 대상에는 해당 소유자의 정당한 후속 UPDATE나 DELETE가 없다고 둔다. $P_2$ 는 회수기가 아직 필요한 값을 삭제하지 않아야 한다는 요구다.

$$
P_2:\quad \operatorname{Needed}(c) \Rightarrow \operatorname{Intact}(c).
$$

두 요구는 기존 정규 사양 §3과 §4의 rollback·snapshot 보존 요구에 근거한다. [N1]

안전한 프로토콜은 자신이 허용하는 모든 실행에서 안전 요구를 지켜야 한다. 허용 실행 하나가 요구를 깨면 그 보장은 성립하지 않는다. 따라서 아래의 "모순"은 매 실행마다 손상이 난다는 뜻이 아니다. 구현 규칙과 보편적인 안전 보장을 동시에 유지할 수 없다는 뜻이다. 주장 집합이 최소 모순 집합이라는 주장은 하지 않는다.

## 3. 논증에 사용하는 주장 A부터 H

| 주장 | 종류 | 내용 | 근거 |
| --- | --- | --- | --- |
| **A** | 구현의 복구 계약 | chunk를 지운 회수 sysop $V$ 는 아직 abort될 수 있다. abort나 열린 sysop의 재시작 undo는 삭제 전 레코드의 복원 주소로 원래 $r$ 을 사용하며, undo 완료에는 그 레코드의 복원이 필요하다. | [복구 함수 연결][S1], [chunk 복원 함수][S2], [sysop의 성공·실패 처리][S3] |
| **B** | 구현 사실 | OOS의 `spage_delete`는 sysop 확정 전에도 지운 slot과 바이트 공간을 재사용 가능하게 한다. vacuum worker는 일반적인 undo 공간 예약에서 제외된다. | [OOS page 초기화][S4], [slot 재사용과 공간 예약에 대한 분석][R1] §가정 1, [바이트 반환 분석][R2] §결정 1 |
| **C** | 허용 실행 | chunk page의 latch를 놓은 뒤 $V$ 가 끝나기 전, $T$ 가 그 slot을 할당받아 다른 레코드를 넣고 commit할 수 있다. 그 뒤 해당 레코드를 변경하는 연산 없이도 $V$ 의 다음 단계 실패나 crash에 의한 undo가 가능하다. | [현재 코드의 반례][R2] §결정 1, [U1의 모델 동작][R1] §U1 결과 |
| **D** | 안전 요구 | $V$ 의 undo를 완료하면서도 $T$ 가 commit한 다른 레코드의 내용과 물리 참조를 보존해야 한다. | $P_1$, 기존 사양의 복구 요구 [N1] §4 |
| **E** | 구현 사실 | UPDATE $u$ 의 undo image에는 변경 전 chain $c$ 의 stub이 남는다. | [기존 사양][N1] §3 UPDATE, [undo image 분석][R1] §가정 2 |
| **F** | 구현 사실·반례 조건 | $u$ 를 rollback하면 row는 다시 $c$ 를 참조하며, 해당 vacuum 실행까지 $c$ 를 버리는 다른 연산은 없다. UPDATE undo image는 조사할 로그에 남을 수 있고, rollback으로 끝난 트랜잭션도 block 처리 조건을 만족할 수 있다. | [rollback 반례][R1] §U1 결과, [삭제 판단 모델][R2] §결정 2 |
| **G** | 구현 사실·허용 실행 | 처리 대상 block의 해당 UPDATE undo image에서 $c$ 를 찾으면, forward-walk는 그 UPDATE가 최종적으로 살아남았는지 확인하지 않고 삭제를 실행한다. $c$ 가 존재하고 identity 검사와 삭제가 성공하는 실행이 허용된다. | [forward-walk 호출 지점][S5], [삭제 실행 지점][S6], [현재 판단 규칙 분석][R1] §가정 2 |
| **H** | 안전 요구 | rollback 뒤 현재 row가 참조하는 $c$ 는 온전히 남아 있어야 한다. | $P_2$ 의 특수한 경우, [기존 사양][N1] §4 undo correctness |

A와 B는 서로 다른 계층의 동작이다. 복구 계층은 원래 위치에 다시 쓸 권한을 유지한다. 공간 관리 계층은 그 위치를 새 INSERT에 내준다. C는 이 두 권한이 충돌하는 실행 순서를 연결한다.

E와 F는 undo와 rollback을 위한 정상 동작이다. 문제가 되는 조합은 여기에 G의 삭제 판단을 적용하면서 H까지 보장하려는 경우다.

## 4. 정리 1. 물리 undo와 조기 재사용의 모순

**정리 1.** 2절의 실행 모형에서 A, B, C를 유지하면 D를 모든 허용 실행에 대해 보장할 수 없다.

**증명.** 다음 실행을 택한다. 처음 주소 $r$ 에는 회수할 chunk $x$ 가 있다. $x$ 와 $y$ 는 서로 다른 레코드다.

| 시점 | 행위 | 주소 $r$ 의 내용 | 복구 의무 |
| --- | --- | --- | --- |
| $t_0$ | $V$ 가 sysop을 시작한다. | $x$ | 아직 삭제 없음 |
| $t_1$ | $V$ 가 $x$ 를 삭제하고 page latch를 놓는다. | 빈 slot | A에 따라 $x$ 를 $r$ 에 복원할 수 있어야 함 |
| $t_2$ | $T$ 가 $r$ 에 $y$ 를 넣고 commit한다. | $y$ | $V$ 의 undo 의무가 남음 |
| $t_3$ | $V$ 의 다음 삭제가 실패해 sysop이 abort된다. | $y$ | $x$ 를 $r$ 에 복원해야 함 |

$t_2$ 는 B와 C가 허용한다. $t_3$ 는 A와 C가 허용한다. $t_3$ 이후 undo를 완료하려면 A에 의해 $r$ 에 $x$ 를 복원해야 한다. D에 의하면 $y$ 와 그 물리 참조도 유효하게 보존해야 한다. 그러나 동일한 slot $r$ 이 서로 다른 $x$ 와 $y$ 를 동시에 담을 수는 없다.

$x$ 를 그대로 쓰면 D를 위반한다. $y$ 를 유지하면서 복원을 거부하면 A가 요구하는 undo를 완료하지 못한다. 따라서 A, B, C가 허용하는 실행에서 A의 복원과 D의 보존을 함께 완료할 수 없다. 증명 끝.

$$
\begin{gathered}
A \land B \land C
\Rightarrow
\exists e\in\mathcal{E}_{ABC}:\\
\neg\bigl(\operatorname{UndoCompletes}(e)\land\operatorname{PreservesCommitted}(e)\bigr).
\end{gathered}
$$

$\mathcal{E}_{ABC}$ 는 A부터 C까지가 허용하는 실행 집합이다. 이 식은 모든 실행이 실패한다는 주장이 아니라, 안전한 undo 완료를 보장할 수 없는 실행이 존재한다는 주장이다.

### 4.1. 코드와 관찰의 대응

`spage_insert_for_recovery`는 대상 slot이 비어 있다고 assert한다. 따라서 이 실행에서는 복구 함수가 요구하는 전제부터 깨진다. debug assert 발생과 release에서 다른 레코드를 덮어쓸 수 있다는 소스 추론은 구분해야 한다. [복원 함수 전제에 대한 분석][R1] §가정 1

기존 보고서는 CBRD-27781에 대해 `224104a36` debug 테스트의 재현 기록을 인용한다. U1 설계 모델도 chunk undo와 heap forward slot undo에서 각각 같은 충돌을 찾았다. 이 글은 그 결과를 재인용하며 새 실행 결과를 주장하지 않는다. [기존 재현 근거와 U1 결과][R1]

### 4.2. 보조명제 1. slot 번호 예약만으로는 undo를 보장할 수 없다

slot $s$ 를 예약해 $T$ 가 다른 slot $s'$ 를 쓰게 하더라도, $T$ 가 같은 page의 빈 바이트를 소비할 수 있다. page의 유효 용량을 $C_p$, 현재 레코드가 차지하는 공간을 $L_p$, 복원할 레코드에 추가로 필요한 공간을 $U_p$ 라고 하자. 각 항은 slot 비용을 포함해 같은 기준으로 센다. 정상적인 물리 undo에는 다음 조건도 필요하다.

$$
L_p+U_p\le C_p.
$$

slot 번호만 예약하는 방식은 이 부등식을 보장하지 않는다. 기존 모델의 D2a는 `UndoFindsEmptySlot`을 통과했지만 `UndoFindsRoom`에서 반례가 나왔다. page 자체가 먼저 반납되지 않는다는 조건도 별도로 필요하다. D2b의 바이트 예약이 LSA gate까지 대체하지는 못한 이유다. [slot·바이트·page 검사][R2] §결정 1, §결정 4

따라서 정리 1의 수정은 slot 번호만의 문제가 아니다. undo를 유지하는 설계는 slot, 바이트, page의 수명을 복원 의무와 함께 관리해야 한다.

## 5. 정리 2. UPDATE undo image와 현재 값 삭제의 모순

**정리 2.** E, F, G를 유지하면 H를 모든 허용 실행에 대해 보장할 수 없다.

**증명.** 초기 row가 chain $c_a$ 를 참조한다고 하자. UPDATE $u$ 는 다른 chain $c_b$ 를 만드는 변경이다.

| 시점 | 행위 | 현재 row의 참조 | 로그에 남은 UPDATE undo image |
| --- | --- | --- | --- |
| $t_0$ | 변경 전 상태다. | $c_a$ | 없음 |
| $t_1$ | $u$ 가 새 버전을 쓴다. | $c_b$ | E에 따라 $c_a$ 의 stub |
| $t_2$ | 트랜잭션이 rollback한다. | F에 따라 $c_a$ | $c_a$ 의 stub이 남음 |
| $t_3$ | vacuum이 해당 block의 undo image를 조사한다. | $c_a$ | $c_a$ 의 stub |
| $t_4$ | forward-walk가 $c_a$ 를 삭제한다. | $c_a$ | 삭제 판단에 사용된 image |

F에 의해 $t_2$ 이후 $c_a$ 는 현재 row가 필요로 하는 값이다. G에 의해 $t_4$ 의 삭제가 허용된다. 그러면 `Needed(c_a)`가 참인데 `Intact(c_a)`는 거짓이 되어 H를 위반한다. 증명 끝.

$$
E\land F\land G
\Rightarrow
\exists e\in\mathcal{E}_{EFG},t:
\operatorname{Needed}(c_a,t)\land\neg\operatorname{Intact}(c_a,t).
$$

이 반례는 아직 읽는 사람이 있을지 모른다는 추측에 의존하지 않는다. rollback으로 복원된 현재 row가 직접 그 chain을 참조한다. CBRD-27237의 `dcbf09e4f` 실행 재현과 U1 반례가 이 순서를 뒷받침한다. [rollback 뒤 삭제 반례][R1] §U1 결과

### 5.1. 보조명제 2. identity 일치는 회수 자격을 함의하지 않는다

정리 2에서 undo image의 stub과 복원된 row의 stub은 같은 $c_a$ 를 가리킨다. head identity stamp도 같다. 따라서 identity 검사가 성공해도 H 위반을 막지 못한다.

$$
\operatorname{IdentityMatches}(c_a)
\nRightarrow
\operatorname{ReclamationEligible}(c_a).
$$

identity 검사는 주소가 재사용되어 다른 값으로 바뀌었는지 구별한다. 회수 자격은 해당 값이 가시성, rollback, 복구에 더 이상 필요 없는지 판단한다. 두 조건은 [프로젝트 용어][V1]에서도 구분한다.

CBRD-26950 이전의 주소 재사용 문제는 별도의 역사적 결함이다. 기준 구현에는 head stamp 검사가 있으므로, 이를 현재 미해결 결함으로 다시 세지 않는다. 정리 2는 올바른 identity가 일치하는 상황에서도 성립한다. [세 번째 가정과 기존 대응][R1] §가정 3

### 5.2. 보조명제 3. 트랜잭션 commit은 특정 UPDATE의 생존을 함의하지 않는다

$u$ 를 실행한 뒤 그 statement만 rollback하고, 나머지 트랜잭션은 commit하는 실행을 택할 수 있다. 이때 트랜잭션의 commit 기록과 $u$ 의 undo image는 있지만, row는 여전히 $c_a$ 를 필요로 한다. 따라서 G에 "트랜잭션의 commit 기록이 있다"를 추가해도 정리 2의 반례가 남는다.

기존 결정 모델의 `commit_filter` 후보가 이 반례를 냈다. 필요한 증거는 트랜잭션 종료 자체가 아니라, 최종적으로 살아남은 변경이 그 chain을 실제로 버렸다는 사실이다. [statement rollback 뒤 commit][R2] §결정 2

## 6. 회수 알림에도 필요한 두 가지 조건

이 절은 현재 forward-walk 구현에 대한 정리 2에서 도출한 수정 조건이다. 현재 구현에 commit hook emitter가 있다는 주장이 아니다. 기존 사양은 commit 조건부 알림을 요구하지만, 기준 revision에는 emitter가 없다고 원문이 기록한다. [기존 구현과 사양의 차이][R1] §가정 2

### 6.1. 알림의 영속성은 commit 결정의 영속성을 전제해야 한다

기존 사양 §3의 commit 직전 hook 알림을 모델링한 후보에는 다음 실행이 허용된다. 알림을 로그에 쓴다. WAL flush로 알림이 durable해진다. commit 결정이 durable해지기 전에 crash가 난다. 복구가 트랜잭션을 rollback하지만 알림은 남는다.

알림만으로 삭제한다면 정리 2와 같은 H 위반이 발생한다. 이 후보의 반례를 배제하려면 최소한 다음 조건이 필요하다.

$$
\operatorname{DurableNotify}(u,c)
\Rightarrow
\operatorname{DurableCommitDecision}(\operatorname{Txn}(u)).
$$

statement rollback으로 취소된 $u$ 에는 알림이 없어야 한다는 조건도 함께 필요하다. 제안 A'는 취소 가능한 postpone 의도를 남기고, durable한 commit 결정 뒤에 알림을 발행해 이 두 조건을 만족시키려는 방식이다. 이 결과는 기존 hook 후보의 모델 반례와 A' 모델 결과에 근거한다. [hook의 crash 구간과 postpone 조건][R2] §결정 2

### 6.2. 폐기 확정은 즉시 회수 가능을 함의하지 않는다

UPDATE가 확실히 commit해도, 그 commit보다 오래된 snapshot은 $c_a$ 를 볼 수 있다. 이때 `Needed(c_a)`는 여전히 참이다. 따라서 알림이 확정된 폐기를 나타내더라도, 회수는 기존 독자의 가시성 범위를 벗어날 때까지 기다려야 한다.

기존 조합 모델에서 snapshot horizon을 제거하면 `ReaderSeesIntactChain`이 깨졌다. 또한 사양대로 미대입 OOS 속성의 stub을 재사용하는 UPDATE를 넣었을 때, undo image를 삭제 근거로 삼는 변형은 commit된 UPDATE에서도 살아 있는 chain을 지웠다. 이는 재사용 정책을 현재 구현에 추가 완료했다는 주장이 아니라, 그 정책과 forward-walk를 결합한 모델의 반례다. [snapshot과 chain 재사용 반례][R2] §고른 조합을 하나의 모델로 검사

## 7. 두 모순이 요구하는 설계 변경

정리 1에서 D를 유지하려면 A부터 C까지의 구현 규칙 중 적어도 하나를 바꿔야 한다. 정리 2에서 H를 유지하려면 E부터 G까지를 함께 유지할 수 없다. E와 F는 정상적인 undo·rollback 계약이므로, 제안은 G의 삭제 판단을 바꾼다.

| 문제 | 유지할 안전 요구 | 변경 가능한 규칙 | 기존 후보 |
| --- | --- | --- | --- |
| undo와 재사용의 충돌 | D | 복원 의무가 끝날 때까지 slot·바이트·page를 보호한다. | D2b의 예약, D2c의 page 제외 |
| undo와 재사용의 충돌 | D | 실제 chunk 삭제를 확정 뒤에 실행하고, 그 삭제의 undo를 없앤다. | D3 |
| 이전 image와 현재 값의 충돌 | H | undo image 대신 최종적으로 살아남은 폐기 결정을 전달하고, snapshot horizon을 기다린다. | A' 알림과 MVCC 대기 |

모든 관련 page의 latch를 끝까지 보유하는 D1도 공간 충돌 자체는 막지만, 기존 모델에서는 worker 둘이 반대 순서로 page를 방문할 때 교착했다. 이것이 모든 latch 기반 설계가 불가능하다는 증명은 아니다. 해당 후보의 latch 순서에는 별도 해결이 필요하다는 뜻이다. [후보별 결과][R2] §결정 1

D3는 회수 의도를 먼저 확정하고, 실패하면 삭제를 되돌리는 대신 남은 회수를 재시도한다. 이 선택에는 새로운 증명 의무가 있다. head를 먼저 지우면 crash 뒤 남은 chunk를 찾지 못한다. 꼬리부터 지워도 next 링크의 stamp가 없으면 재시도가 이미 재사용된 다른 slot을 지울 수 있다. 따라서 제안은 head를 마지막에 삭제하고, 링크 stamp를 확인하며, 실패한 회수를 다시 실행한다. [재시도 후보의 반례][R2] §결정 3

이 글의 두 정리는 D3가 유일하거나 가장 빠르다고 증명하지 않는다. D2b와 D2c도 기존 공간 보호 모델을 통과했다. D3는 chunk 본문을 복원용 undo로 다시 기록하는 비용을 없애는 대신, 24B에서 32B로 커지는 chunk header, 새 recovery index, 부분 회수의 재시도와 오류 처리 책임을 도입한다. 실제 성능은 측정 전이다. [대안과 로그 비용][R1], [확정할 항목][R3]

D3를 적용해도 heap forward slot의 undo 문제는 별도다. CBRD-27858의 대응과 latch 순서가 원인인 CBRD-27860까지 이 개정 하나로 해결된다고 해석하지 않는다. [남는 문제의 범위][R1] §남는 것

## 8. 모델 증거와 타당성의 한계

기존 U1 모델은 재사용 시점, 삭제 판단 근거, head identity 검사를 각각 설정으로 나눴다. 재사용을 즉시 허용하면 undo 관련 반례가, 종료 사실만으로 삭제를 정하면 현재 chain 삭제 반례가 나타났다. 이 결과는 서로 다른 결함을 두 논증으로 분리한 근거다. [U1의 가정별 검사][R1]

후속 조합 모델은 D3, postpone 알림, snapshot horizon, 꼬리부터 삭제, 링크 stamp를 함께 검사했다. 문서는 설계 조합이 2,960개 상태에서 다섯 성질을 통과했다고 기록한다. 전체 137개 검사는 통과할 설계뿐 아니라 의도된 반례와 도달 확인도 포함하며, 모두 기대값과 같았다는 뜻이다. 137개 후보가 모두 안전하다는 뜻은 아니다. [조합 검사와 도달 확인][R2]

이 증거에는 다음 한계가 있다.

- 이 글은 기존 증거를 재구성한 논증이다. 모든 엔진 실행에 대한 기계 검증 증명이 아니다.
- 조합 모델은 row 하나, vacuum worker 하나, 방해 한 번을 다룬다. 여러 회수기, 반복 crash, eager 정리, HA, prepared 2PC는 그 조합 모델의 범위 밖이다.
- 공간 보호 모델의 바이트는 레코드당 한 단위로 단순화했다. 실제 공간 예약의 해제 시점과 모델의 대응은 구현 검증이 필요하다.
- D3의 코드 적합성, postpone 실패 정책, 복구 중 MVCCID 처리, 성능은 이 논증으로 확정하지 않는다.
- 기존 설계 개정안 앞부분에는 U2가 다음 단계라는 초기 요약이 남아 있다. 이 글은 후속 결정별·조합 검사 결과를 사용하지만, 그것으로 원래 U2 계획의 모든 범위를 완료했다고 주장하지 않는다.

재현 명령과 모델별 입력, 설정, 결과, 해시는 [결정별 검증 문서][R2]의 "기준과 실행"에 있다. 모델을 다시 검사하려면 저장소 루트에서 다음 명령을 실행한다. 출력 경로는 새 디렉터리여야 한다. 이 글에서는 재실행하지 않았다.

```sh
python3 oos/reclaim-model/check_decisions.py --out .scratch/oos-contradictions-model-check
```

ADR-0008의 상태는 2026-11-03 확정 요청서에서 `proposed`다. 이 글은 그 문서의 제안 상태를 인용하며, 2026-11-04의 승인 여부를 새로 확인하지 않았다. [확정 요청의 범위][R3]

## 9. 결론

현재 회수 규칙에는 두 개의 안전성 모순이 있다. A, B, C가 허용하는 실행에서는 원래 주소로의 undo 완료와 D의 commit 데이터 보존을 함께 보장할 수 없다. E, F, G가 허용하는 실행에서는 rollback된 현재 chain이 삭제되어 H를 위반한다.

$$
\begin{aligned}
A\land B\land C &\Rightarrow \neg D,\\
E\land F\land G &\Rightarrow \neg H.
\end{aligned}
$$

따라서 안전 요구 D와 H를 유지하려면 공간 재사용·복구 계약과 삭제 판단 근거를 바꿔야 한다. 필요한 것은 어떤 chain인지를 확인하는 것에 더해, 그 chain을 더 이상 필요로 하지 않는다는 근거와 그 공간을 넘겨도 되는 복구 경계다. 이 결론은 회수 프로토콜의 개정을 요구한다. 특정 대안의 최종 채택과 성능 우위는 별도의 검증 문제로 남는다.

## 참고문헌

- [R1] [OOS 삭제를 확정 뒤 회수로 바꾸는 설계 개정안](reclaim-redesign.md). 이 저장소 `a9644b8`, 2026-11-03. 소스 분석, 기존 실행 기록, U1 결과, D3 제안.
- [R2] [OOS 회수 설계 결정의 TLA+ 검증](reclaim-decisions.md). 같은 revision, 2026-11-03. 후보별·조합 모델, 반례와 한계.
- [R3] [ADR-0008 확정 요청](adr-0008-confirmation.md). 같은 revision, 2026-11-03. 제안 상태와 구현·성능의 미확인 범위.
- [N1] [기존 OOS 정규 사양](https://github.com/vimkim/cubrid-oos-context/blob/281a940eafb5db507bce8e75a51de0ea94b4bfde/OOS-CONTEXT.md). §3 UPDATE, §4 Recovery & MVCC.
- [V1] [프로젝트 용어](../CONTEXT.md). OOS chain identity와 OOS reclamation eligibility.
- [S1] [recovery.c의 `RVOOS_DELETE` undo·redo 연결](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/transaction/recovery.c#L887-L890).
- [S2] [oos_file.cpp의 chunk 복원·삭제 recovery 함수](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3672-L3712).
- [S3] [vacuum_oos.cpp의 원자적 삭제 wrapper](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum_oos.cpp#L172-L207).
- [S4] [oos_file.cpp의 `ANCHORED` page 초기화](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3174).
- [S5] [vacuum.c의 forward-walk 진입](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3619).
- [S6] [vacuum.c의 UPDATE undo image 기반 OOS 처리](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3764).

[R1]: reclaim-redesign.md
[R2]: reclaim-decisions.md
[R3]: adr-0008-confirmation.md
[N1]: https://github.com/vimkim/cubrid-oos-context/blob/281a940eafb5db507bce8e75a51de0ea94b4bfde/OOS-CONTEXT.md
[V1]: ../CONTEXT.md
[S1]: https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/transaction/recovery.c#L887-L890
[S2]: https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3672-L3712
[S3]: https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum_oos.cpp#L172-L207
[S4]: https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3174
[S5]: https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3619
[S6]: https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3764
