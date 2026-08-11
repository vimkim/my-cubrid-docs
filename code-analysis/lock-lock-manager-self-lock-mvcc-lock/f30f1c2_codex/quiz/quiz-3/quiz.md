# Quiz 3 — 동시 읽기와 변경 결과 예측하기

## 학습 목표

Snapshot-visible version 선택과 latest-row 변경 권리 획득을 분리하고, wait 뒤 state 재결정이 필요한 이유를 설명한다.

## 선행 지식과 준비물

Bash, sealed CUBRID `debug_gcc` runtime, [7장](../../chapters/07-mvcc-lock-policy.html#mvcc-lock-policy)이 필요하다. PostgreSQL/MySQL server는 필요 없다. `qalockq3f30`은 없어야 하며 Quiz-owned DB에만 권한을 쓴다.

## 예상 시간

25분.

## 실행 전 예측

Session B의 각 statement마다 먼저 채운다.

| statement | visible value | instance mode | can wait | post-wait recheck 필요성 |
|---|---|---|---|---|
| plain SELECT |  |  |  |  |
| SELECT FOR UPDATE |  |  |  |  |
| UPDATE/COMMIT |  |  |  |  |

## 안전한 실행 명령

```bash
cd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/quiz/quiz-3
bash ./run.sh
```

Pre-existing `qalockq3f30`이면 exit 73으로 SQL 전에 멈춘다. Exact csql은 `-C -u dba --no-auto-commit -i <setup.sql|session-a.sql|session-b.sql> -t qalockq3f30`; full/contended dumps는 `cubrid lockdb [ -c ] qalockq3f30`이다. Runtime storage와 marker는 이 Quiz에 귀속된다.

## 관찰할 것

`session-b.out`의 statement-order 결과와 `contention.lockdb.txt`의 target instance block을 함께 읽는다. Plain result가 먼저 출력됐는지, later statement가 어떤 logical resource에서 기다렸는지, final row가 무엇인지 적는다. “100을 읽었다”가 statement 전체의 무잠금을 증명하는지도 판정한다.

## 분석과 teach-back

1. Uncommitted 900 중 plain SELECT가 고르는 version과 locked read가 요구하는 권리를 분리한다.
2. Pre-wait candidate를 그대로 반환하면 어떤 delete/update/predicate race가 생기는가?
3. Holder를 commit하는 사고실험에서는 wake 뒤 무엇을 다시 판정해야 하는가?
4. MVCC snapshot, class intent, row X, page latch를 서로 다른 seam에 둔다.
5. “MVCC lock”이 독립 enum이라기보다 policy composition이라는 뜻을 가르친다.
6. PostgreSQL/InnoDB의 nearest mechanism을 direct equivalent가 아닌 partial analogy로 분류한다.

## Cleanup과 재실행

정상·실패 모두 owner-verified cleanup을 시도하며 raw output은 보존한다. Trap이 못 돈 경우에만 `bash ./cleanup.sh`; marker/registry mismatch면 거부한다. Global stop이나 manual deletedb는 금지한다. 성공 후 안전하게 재실행할 수 있다.

## 연결 장과 Claim

Behavior `mvcc-lock-policy`; [7장](../../chapters/07-mvcc-lock-policy.html#mvcc-lock-policy); Claims `CUBRID-C020`, `CUBRID-C021`, `CUBRID-C022`, `CUBRID-C027`, `CUBRID-C042`.
