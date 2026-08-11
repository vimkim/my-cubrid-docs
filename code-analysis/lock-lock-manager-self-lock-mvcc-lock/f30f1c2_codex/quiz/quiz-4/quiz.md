# Quiz 4 — 끝나지 않은 inserter를 만났을 때

## 학습 목표

Same-key unique observer의 wait target을 여러 identity 후보 중 예측하고, completion rendezvous·재검사·publication ordering·entry trade-off를 스스로 유도한다.

## 선행 지식과 준비물

Bash, sealed CUBRID `debug_gcc` runtime, [8장](../../chapters/08-mvccid-self-lock.html#mvccid-self-lock-rendezvous)이 필요하다. PostgreSQL/MySQL server는 필요 없다. `qalockq4f30`이 기존 DB가 아니어야 하며 이 Quiz-owned DB 외의 resource는 건드리지 않는다. 실행 전에 answer와 runner source를 열지 않는다.

## 예상 시간

30분.

## 실행 전 예측

Wait target 후보 `row OID`, `class OID`, `tran_index`, `TRANID`, `MVCCID` 중 하나를 고른다. Holder mode, waiter mode, 그 예측을 반증할 dump label을 따로 쓴다. Different-key insert가 block될지도 예측한다.

## 안전한 실행 명령

```bash
cd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/quiz/quiz-4
bash ./run.sh
```

Runner는 `qalockq4f30` collision을 exit 73으로 거부한다. Exact session argv는 `csql -C -u dba --no-auto-commit -i <file> -t qalockq4f30`; raw full/contended dumps와 session outputs를 unique directory에 저장하고 exact owner cleanup을 한다. Procedure는 answer-bearing resource/mode를 파싱하거나 출력하지 않는다.

## 관찰할 것

`readiness.lockdb.txt`, `contention.lockdb.txt`, `session-a.out`, `session-b.out`, `post-release.lockdb.txt`를 연다. Resource label과 identity, holder/waiter transaction indices, modes, final rows를 서로 다른 칼럼에 적는다. Different-key result를 negative control로 쓴다. 숫자 identity가 서로 같다고 가정하지 않는다.

## 분석과 teach-back

1. 왜 이름의 “self”가 자기-deadlock을 뜻하지 않는가?
2. 별도 mode 없이 ordinary compatibility가 충분하려면 resource identity가 어떻게 typed되어야 하는가?
3. Wait grant만으로 same-key insert를 확정할 수 없는 이유와 full-release/re-read 순서를 적는다.
4. `observable INSID ⇒ matching X held`와 `inactive publication → X release → wake/recheck` ordering을 깨는 반례를 각각 만든다.
5. Per-row X와 per-owner completion resource를 entry 수, fan-in, fallback, cleanup, prepared 2PC 관점에서 비교한다.
6. PostgreSQL XID/speculative token과 InnoDB implicit record X를 direct/partial/no-equivalent 중 분류한다.
7. Source를 열지 않고 ensure/wait/transaction-end의 total pseudocode를 쓴다.

## Cleanup과 재실행

정상·오류 exit 모두 child cmdline과 owner marker를 확인한 뒤 exact DB만 정리한다. 강제 kill 뒤에는 `bash ./cleanup.sh`; marker/registry path가 다르면 hard refusal이다. 수동 global stop/deletedb는 쓰지 않는다. Raw output은 보존되고 다음 run은 새 directory를 쓴다.

## 연결 장과 Claim

Behavior `mvccid-self-lock-rendezvous`; [8장](../../chapters/08-mvccid-self-lock.html#mvccid-self-lock-rendezvous); Claims `CUBRID-C030`, `CUBRID-C031`, `CUBRID-C032`, `CUBRID-C043`.
