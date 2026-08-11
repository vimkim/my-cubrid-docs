# Smoke test

- ownership 수정 후 정상 실행: [`f04-quiz1-smoke-v2`](../../evidence/runs/f04-quiz1-smoke-v2/meta.json)
- 정상 raw stdout: [`stdout.txt`](../../evidence/runs/f04-quiz1-smoke-v2/stdout.txt)
- 동명 DB/server 보존 negative test: [`f04-quiz1-collision-v2`](../../evidence/runs/f04-quiz1-collision-v2/meta.json)
- collision raw stdout: [`stdout.txt`](../../evidence/runs/f04-quiz1-collision-v2/stdout.txt)
- 결과: exit 0, predicate 성공, stderr empty, cleanup verified

collision test는 launcher exit 30 뒤 registry line과 `cub_server` PID/cmdline이 그대로임을 확인한 다음, test harness가 자신이 만든 DB만 정리한다. 정상 smoke는 launcher의 predicate와 owned cleanup을 확인한다. 한 번의 scheduler timing은 일반화하지 않는다.
