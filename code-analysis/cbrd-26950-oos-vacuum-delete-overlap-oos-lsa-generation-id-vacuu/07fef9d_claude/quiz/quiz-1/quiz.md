# quiz-1 — 정상 흐름: UPDATE 된 OOS 행의 옛 값은 누가, 언제, 무엇을 보고 지우는가

- **학습 목표**: 대체된 OOS value chain 의 유일한 참조가 어디에 남는지, 그것을 누가 소비하는지,
  그리고 oos.log 관측 채널의 비대칭(함정 하나 포함)을 직접 관찰한다.
- **선수 지식**: ch02(멘탈 모델), ch04(소유권), ch06(워크플로). debug 빌드 필요(oos.log).
- **예상 시간**: 읽기 5분 + 실행 ~2분.
- **연결**: 중심 행동 `oos-forward-walk-reclaim` ·
  claim `CUBRID-C001, C002, C003, C043` · 챕터 ch06 §1, ch11 §2.

## 실행 전 예측 (봉인하고 시작)

- **P1.** `UPDATE` 직후, 옛 OOS 체인을 가리키는 참조는 어디에 남아 있는가?
  ① 살아있는 heap 레코드 ② 로그의 undo image ③ OOS 청크 헤더 ④ bestspace 캐시 — 고르고 이유를 쓰라.
- **P2.** vacuum 이 옛 체인을 회수하는 동안·후에, `SELECT` 로 읽는 값은 어떻게 되는가? 왜?
- **P3.** 이 실험(2,000행 INSERT 후 전체 UPDATE)에서 `oos.log` 에는 insert 기록이 몇 건,
  delete 기록이 몇 건 남을 것 같은가?

## 절차

```sh
cd quiz/quiz-1
bash run.sh          # 전용 DB(oos26950q1) 생성 → 2,000행 OOS INSERT → 전체 UPDATE
                     # → vacuum 완주 대기 → 값 검증 → oos.log 두 채널 카운트 출력 → 정리
```

스크립트는 자기 소유 DB 만 만들고 지운다. 실패 시 0 이 아닌 코드로 종료한다.

## 관찰할 것

1. `verify: total=2000 mismatch=0` — 회수가 끝난 뒤에도 살아있는 값은 온전하다.
2. `oos.log deletes since update: 2000` — 옛 체인 2,000개가 실제로 회수되었다.
3. `oos.log inserts since update: ?` — P3 의 답과 비교하라. 여기가 함정이다.

## 분석·teach-back 질문

- **T1.** 이 실험에서 재사용된 슬롯이 하나도 없었던 이유는? 스크립트의 어떤 설계가 그것을 보장하나?
- **T2.** 스크립트에서 "필러(filler)" 배치를 빼면 무엇이 실패하고, 왜 그런가? (힌트: ch05 §블록의 탄생)
- **T3.** oos.log 의 insert/delete 비대칭은 CBRD-26950 재현 스크립트의 증거 설계를 어떻게 바꿨나?

## 정리

`run.sh` 가 끝에서 자체 정리한다(서버 stop + deletedb). 중단했다면 `bash run.sh cleanup` 으로 재정리.
