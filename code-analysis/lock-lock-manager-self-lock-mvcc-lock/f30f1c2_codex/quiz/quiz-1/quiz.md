# Quiz 1 — 한 locked read의 잠금 지도 그리기

## 학습 목표

한 `SELECT ... FOR UPDATE`를 statement가 아니라 typed resource·mode·owner·lifetime의 지도로 복원하고, compatibility를 적용하기 전에 resource identity를 먼저 정한다.

## 선행 지식과 준비물

Bash와 이 보고서의 sealed CUBRID `debug_gcc` runtime이 필요하다. PostgreSQL/MySQL server는 필요 없다. 고정 DB `qalockq1f30`이 없어야 하며, 권한은 Quiz-owned DB에만 쓴다. [3장](../../chapters/03-interface-and-resources.html#resource-mode-hierarchy)의 resource/mode 표를 먼저 읽되 [answer.md](answer.md)는 실행·예측 뒤에 연다.

## 예상 시간

20분.

## 실행 전 예측

다음 빈 표를 먼저 채운다.

| statement | resource type/key | mode | owner | lifetime | wait 가능성 |
|---|---|---|---|---|---|
| `FOR UPDATE id=1` |  |  |  |  |  |

Class와 row가 같은 key인지, 서로 다른 row를 고른 두 transaction이 class 단계에서 충돌할지, rollback 뒤 어떤 entry가 사라질지 예측한다.

## 안전한 실행 명령

```bash
cd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/quiz/quiz-1
bash ./run.sh
```

Runner는 binary SHA를 검사하고 DB 이름이 registry에 있으면 SQL·server mutation 전에 exit 73으로 거부한다. Explicit `runtime-owned/db`와 `runtime-owned/log`, revision-bound `.quiz-owner`를 사용하고 global service를 중지하지 않는다. 내부 exact csql은 `csql -C -u dba --no-auto-commit -i setup.sql -t qalockq1f30`과 같은 형태이며 session input만 `session-a.sql`로 바뀐다. Capture는 `cubrid lockdb qalockq1f30`이다.

## 관찰할 것

성공 메시지의 `raw_output=...` directory에서 `readiness.lockdb.txt`, `session-a.out`, `post-release.lockdb.txt`를 연다. Target class와 instance block의 resource key/OID, holder transaction index, mode, count를 별도 표에 적고 lockdb administrative transaction과 구분한다. OID/transaction index의 구체 숫자는 예측 대상이 아니다.

## 분석과 teach-back

1. Target resource block이 몇 개인가? 두 key가 왜 다른가?
2. 두 holder가 같은 owner임을 어떤 field로 확인했는가?
3. Class intent가 instance lock을 대체하지 않는 이유는 무엇인가?
4. 같은 owner가 class S를 가진 채 IX를 요청하는 사고실험에서 conversion 결과는 무엇이어야 하는가?
5. Instance-lock threshold를 넘기는 사고실험에서 entry 비용과 concurrency trade-off는 무엇인가? 이 Quiz가 실제 conversion/escalation을 실행했는가?
6. “resource identity를 먼저 정하고 compatibility를 적용한다”를 5문장 안에 가르친다.

## Cleanup과 재실행

정상·실패 exit는 owner-verified cleanup을 호출하고 raw output만 보존한다. Shell이 강제 종료되어 trap이 못 돌았다면 같은 directory에서 `bash ./cleanup.sh`를 실행한다. Marker와 registry paths가 정확히 일치하지 않으면 cleanup도 거부한다. `cubrid deletedb`를 수동 shortcut으로 쓰지 않는다. 정상 cleanup 뒤 재실행하면 새 `raw-output/run.XXXXXX`가 만들어진다.

## 연결 장과 Claim

Behavior `resource-mode-hierarchy`; [3장](../../chapters/03-interface-and-resources.html#resource-mode-hierarchy); Claims `CUBRID-C001`, `CUBRID-C002`, `CUBRID-C003`, `CUBRID-C004`, `CUBRID-C040`.
