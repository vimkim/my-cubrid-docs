# Smoke test

- ownership 재점검 후 정상 실행: [`f04-quiz3-smoke-v2`](../../evidence/runs/f04-quiz3-smoke-v2/meta.json)
- 정상 raw stdout: [`stdout.txt`](../../evidence/runs/f04-quiz3-smoke-v2/stdout.txt)
- source 동명 DB/server 보존 negative test: [`f04-quiz3-collision-v2`](../../evidence/runs/f04-quiz3-collision-v2/meta.json)
- source collision raw stdout: [`stdout.txt`](../../evidence/runs/f04-quiz3-collision-v2/stdout.txt)
- destination 동명 DB/server 보존 negative test: [`f04-quiz3-dst-collision-v2`](../../evidence/runs/f04-quiz3-dst-collision-v2/meta.json)
- destination collision raw stdout: [`stdout.txt`](../../evidence/runs/f04-quiz3-dst-collision-v2/stdout.txt)
- 결과: exit 0, predicate 성공, stderr empty, cleanup verified

두 collision test는 launcher exit 30 뒤 registry line과 source 또는 destination `cub_server` PID/cmdline이 그대로임을 확인한다. 정상 smoke는 fixed build의 한 입력과 두 owned DB cleanup을 확인한다. pre-fix A/B나 모든 OOS 크기 조합을 일반화하지 않는다.
