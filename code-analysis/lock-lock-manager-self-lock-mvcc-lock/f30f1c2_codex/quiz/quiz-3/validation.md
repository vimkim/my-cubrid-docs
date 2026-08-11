# Quiz 3 validation

- Syntax receipt: [quiz3-bash-n-audit](../../evidence/runs/quiz3-bash-n-audit/meta.json).
- Exact runner receipt: [meta](../../evidence/runs/quiz3-run-audit-r1/meta.json), [stdout](../../evidence/runs/quiz3-run-audit-r1/stdout.txt), [stderr](../../evidence/runs/quiz3-run-audit-r1/stderr.txt).
- Preserved raw output: [run.EmsnBp](raw-output/run.EmsnBp/).
- Observed oracle: direct order is first 100, second 100, third 101; contention dump has the target instance's X holder/X waiter.
- Answer check: [answer.md](answer.md) matches the visibility/exclusion split and does not generalize beyond the recorded isolation/case.
- Cleanup check: runner exit 0, `qalockq3f30` registry row absent, marker/runtime paths absent.
