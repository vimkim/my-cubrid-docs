# Quiz 2 validation

- Syntax receipt: [quiz2-bash-n-audit](../../evidence/runs/quiz2-bash-n-audit/meta.json).
- Exact runner receipt: [meta](../../evidence/runs/quiz2-run-audit-r1/meta.json), [stdout](../../evidence/runs/quiz2-run-audit-r1/stdout.txt), [stderr](../../evidence/runs/quiz2-run-audit-r1/stderr.txt).
- Preserved raw output: [run.xqlgIq](raw-output/run.xqlgIq/).
- Observed oracle: same `dba.q2_account` instance block has X holder/X waiter; session B ends with row 1 balance 101.
- Answer check: [answer.md](answer.md) matches 101 and explicitly limits the run to one-way wait/release, not a cycle.
- Cleanup check: runner exit 0, `qalockq2f30` registry row absent, marker/runtime paths absent.
