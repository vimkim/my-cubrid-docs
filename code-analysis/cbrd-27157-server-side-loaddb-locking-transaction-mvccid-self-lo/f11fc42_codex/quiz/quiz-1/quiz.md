# Quiz 1 — BU 잠금의 다섯 칸

## 먼저 예측하세요

server-side `loaddb -C`가 `bu_target` class 입력을 열고 다음 데이터를 기다립니다. 그 사이 별도 csql이 `bu_control`을 갱신한 뒤 `bu_target`의 schema를 바꾸려 합니다. 실행 전에 아래 칸을 채우세요.

| 질문 | 내 답 |
|---|---|
| resource는 무엇인가? | |
| loader와 csql의 mode는 무엇인가? | |
| holder와 waiter는 누구인가? | |
| lock owner는 thread인가 transaction인가? | |
| 언제 waiter가 다시 진행할 수 있는가? | |

## 안전한 실행

예상 시간은 약 10초다. 이 launcher는 전용 DB `ca27157q1buf11`만 만들며 `trap`으로 종료 시 삭제한다. 같은 이름의 DB가 이미 있으면 실행하지 않는다.

```bash
./run.sh
```

성공 조건은 unrelated update 성공, 같은 class resource의 `BU_LOCK` holder와 `SCH_M_LOCK` waiter 동시 관찰, loader 종료 뒤 ALTER 성공, registry/process 정리다. 실제 출력이 권위이며 `sample-output.txt`는 형식 예시뿐이다.

## 답안 공백

lockdb의 mode 이름만 보지 말고 resource, owner, lifetime을 한 문장으로 연결해 쓰세요: `__________`.

이 한 번의 실행이 전체 호환표와 모든 scheduler timing까지 증명하는지도 답하세요: `__________`.

연결: `lock-resource-owner-lifecycle`, `CUBRID-C001`, 2·3·4장.
