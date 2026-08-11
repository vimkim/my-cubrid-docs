# Quiz 1 — runtime 숫자가 말하는 것과 말하지 않는 것

## 학습 목표와 준비

현행 CUBRID에서 dirty page 활동을 재현하고, runtime counter가 직접 증명하는 사실과 pinned source가
필요한 사실을 구분한다. `cubrid`, `csql`이 PATH에 있고 전용 이름 `sxq1codex`가 등록되어 있지 않아야 한다.
예상 시간은 15분이다.

관련 장/Claim: `chapters/04-current-flush.html#snapshot-copy-flush`,
`chapters/07-experiment.html#experimental-validation`, `CUBRID-C006`.

## 먼저 예측하기

실행 전에 다음 세 값을 예상해 적는다.

1. 최종 row 수는 얼마인가?
2. `Num_data_page_dirties`는 0인가, 0보다 큰가?
3. 이 출력만 보고 `memcpy`가 실행됐다고 결론 내릴 수 있는가?

## 실행 절차

```bash
bash run.sh
```

스크립트는 quiz-owned DB `sxq1codex`가 이미 있으면 아무것도 삭제하지 않고 실패한다. DB가 없을 때만
생성하고, `observe.sql`을 standalone `csql`로 실행한 뒤 자신이 만든 DB를 삭제한다.

## 관찰할 것

- `quiz_rows` 값
- histogram의 `Num_data_page_dirties`
- 명령 종료 뒤 database registry에 `sxq1codex`가 남는지

## 분석과 teach-back

1. dirty counter 증가가 설명하는 causal event를 한 문장으로 말해 보라.
2. snapshot `memcpy`, BCB unlock, WAL, data write의 exact ordering은 왜 이 출력만으로 알 수 없는가?
3. report experiment의 `Num_data_page_iowrites`가 증가해도 그 값을 unique page 수로 보면 안 되는 이유를
   DWB 관점에서 설명하라.
4. 현행 copy가 I/O 중 live frame writer를 허용하는 원리를 `image A`와 `live frame B`라는 두 memory
   object로 설명하라.

## failure와 crash 변형

다음 지점에서 process가 멈췄다고 가정한다. 각 경우 restart가 신뢰할 durable object와, volatile
`DIRTY`/`FLUSHING`을 그대로 복원하면 안 되는 이유를 적는다.

1. snapshot 뒤, WAL flush 전
2. WAL flush 뒤, data write 전
3. DWB image는 durable하지만 home page write 중
4. home write 성공 뒤, BCB의 clean/FLUSHING 종료 전

마지막으로 TDE encryption이 `mark_is_flushing` 뒤 실패했는데 common rollback을 타지 않는다면 어떤
state와 waiter가 고아가 되는지 예측하라. 실제 fault injection을 실행하지 말고 source reasoning으로만
답한다.

## 안전한 정리

정상/실패 종료 모두 스크립트가 자신이 생성한 DB만 삭제한다. 실행 전에 같은 이름의 DB가 있으면
중단하므로 기존 DB를 덮어쓰지 않는다. 비정상 종료 뒤 `cubrid server status`와
`$CUBRID_DATABASES/databases.txt`를 확인하고, 본인이 이번 실행에서 만들었다는 사실을 확인한 경우에만
`cubrid deletedb sxq1codex`를 사용한다.
