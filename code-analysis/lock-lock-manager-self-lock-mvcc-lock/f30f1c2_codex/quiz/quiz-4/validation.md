# Quiz 4 validation

- Syntax receipt: [quiz4-bash-n-audit](../../evidence/runs/quiz4-bash-n-audit/meta.json).
- Exact runner receipt: [meta](../../evidence/runs/quiz4-run-audit-r1/meta.json), [stdout](../../evidence/runs/quiz4-run-audit-r1/stdout.txt), [stderr](../../evidence/runs/quiz4-run-audit-r1/stderr.txt).
- Preserved raw output: [run.qRZFBn](raw-output/run.qRZFBn/).
- Observed oracle: literal inserter transaction resource with MVCCID 5 has X holder/S waiter; final rows are `(100,'c')` and `(101,'b')`.
- Answer check: [answer.md](answer.md) matches the resource/mode relation, different-key control, recheck need, and declared limits.
- Cleanup check: runner exit 0, `qalockq4f30` registry row absent, marker/runtime paths absent.
