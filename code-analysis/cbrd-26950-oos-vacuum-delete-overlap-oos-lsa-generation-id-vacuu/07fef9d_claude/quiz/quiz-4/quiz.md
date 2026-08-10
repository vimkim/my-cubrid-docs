# quiz-4 — 정책·비교: 신원 스탬프 후보 판정 매트릭스를 스스로 채워라

- **학습 목표**: R1–R5 요건을 각 후보에 적용해 **구체적 실패 시나리오**를 스스로 유도하고,
  CUBRID 의 선택을 PostgreSQL TOAST·InnoDB purge 와 나란히 놓는다.
- **선수 지식**: ch09, ch13, ch14, ch16. 실행 환경 불필요(지필) — 단 전제 확인용 스크립트 제공.
- **예상 시간**: 20–25분.
- **연결**: 중심 행동 `identity-stamp-and-dedup-design` · claim `CUBRID-C030~C034` · 챕터 ch16.

## 준비 (선택): 전제 사실을 소스에서 직접 확인

```sh
cd quiz/quiz-4
bash premises.sh /path/to/cubrid-worktree   # 판정의 3대 전제를 pinned 소스에서 grep 으로 확인
```

## 과제 1 — 매트릭스 채우기

아래 표를 채워라. 각 ✗ 칸에는 **구체적 실패 시나리오 한 문장**(누가, 언제, 무엇이 잘못되는지)을 요구한다.

| 후보 | R1 가용성 | R2 오탐 불가 | R3 누수 불가 | R4 비용(stub) | R5 불변식 반경 |
|---|---|---|---|---|---|
| 6a 청크 MVCCID vs undo 헤더 insid | | | | | |
| A 점유자 MVCCID < 현재 oldest visible | | | | | |
| B 점유자 MVCCID < 블록 동결값 | | | | | |
| owner OID | | | | | |
| 6b 청크+stub MVCCID 등가 | | | | | |
| 4B generation 등가 | | | | | |

## 과제 2 — 서술형

- **S1.** R1 과 R2/R3 는 왜 같은 후보(6a)에서 동시에 문제가 되는가?
- **S2.** generation 의 증가 시점이 "행 UPDATE 마다"가 아니라 "페이지에 대한 청크 insert(슬롯
  재할당)마다"여야 하는 이유는?
- **S3.** PostgreSQL 은 왜 이 매트릭스 자체가 필요 없는가? 그 설계의 **대가** 두 가지는?
- **S4.** InnoDB 의 스탬프와 generation 권고안의 차이 세 가지(위치·폭·기록 시점)와, 각 차이의 이유는?
- **S5.** "OOS LSA" 를 등가 스탬프로 해석했을 때 generation 대비 얻는 것과 잃는 것은?

## teach-back

"등가 비교여야 하고 부등호 비교로는 안 되는 이유"를, 두 모집단(재사용 점유자 / 정당한 대상)의
언어로 두 문장 이내로 말하라.

## 정리

없음 (읽기 전용).
