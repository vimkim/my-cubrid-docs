# Quiz 2 — 기다리던 UPDATE의 종료 경로

## 학습 목표

One-way incompatible request를 enqueue/suspend → release/grant/wake → operation resume/commit의 상태 전이로 설명하고, 이를 deadlock cycle과 구분한다.

## 선행 지식과 준비물

Bash, sealed CUBRID `debug_gcc` runtime, [6장](../../chapters/06-wait-deadlock-release.html#wait-deadlock-release)이 필요하다. PostgreSQL/MySQL server는 필요 없다. `qalockq2f30`이 기존 registry에 없어야 하고 Quiz-owned DB 외의 삭제·중지는 허용하지 않는다.

## 예상 시간

25분.

## 실행 전 예측

| T1 state | T2 state | resource | holder mode | waiter mode | rollback 뒤 SQL-visible result |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Waiter가 queue에 들어가기 전과 suspend 직전에 publication되어야 할 state, holder rollback 뒤 일어날 순서를 먼저 쓴다.

## 안전한 실행 명령

```bash
cd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/quiz/quiz-2
bash ./run.sh
```

Runner는 pre-existing DB를 exit 73으로 거부하고 explicit owned paths만 사용한다. 내부 csql argv는 `csql -C -u dba --no-auto-commit -i setup.sql -t qalockq2f30`, `... -i session-a.sql ...`, `... -i session-b.sql ...`; capture는 먼저 full `cubrid lockdb qalockq2f30`, 그 뒤 `cubrid lockdb -c qalockq2f30`이다. Global service command는 없다.

## 관찰할 것

`raw_output`의 `contention.lockdb.txt`, `session-a.out`, `session-b.out`, `post-release.lockdb.txt`를 본다. 같은 instance block의 holder/waiter, 두 actor의 state와 최종 row를 기록한다. 이 schedule에는 반대 방향 edge가 없음을 확인한다.

## 분석과 teach-back

1. Enqueue와 suspend 사이에 resource/transaction shared state는 어떤 순서로 준비되어야 하는가?
2. Rollback release, grant publication, wake, update resume, commit을 순서대로 적는다.
3. Timeout, interrupt, deadlock victim은 같은 return인가? 각 cleanup obligation은 무엇인가?
4. Dump file order와 owner/waiter identity 중 무엇으로 wait edge를 복원해야 하는가?
5. Cycle 변형의 안전한 test를 설계하되 실행하지 않는다. Victim identity 대신 exactly-one survivor, victim changes rollback, no residual waiter를 oracle로 쓴다.
6. Leaked waiter와 partial transaction change를 잡는 conformance test를 제안한다.

## Cleanup과 재실행

Runner는 EXIT/INT/TERM에 live child cmdline과 marker/registry path를 검증하고 exact DB만 cleanup한다. 강제 kill로 trap이 사라졌다면 `bash ./cleanup.sh`; marker mismatch면 hard refusal이다. 수동 `deletedb` shortcut은 쓰지 않는다. 성공 뒤 재실행은 새로운 raw directory를 만든다.

## 연결 장과 Claim

Behavior `wait-deadlock-release`; [6장](../../chapters/06-wait-deadlock-release.html#wait-deadlock-release); Claims `CUBRID-C010`, `CUBRID-C011`, `CUBRID-C012`, `CUBRID-C041`.
