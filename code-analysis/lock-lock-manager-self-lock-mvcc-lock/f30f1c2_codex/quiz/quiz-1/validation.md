# Quiz 1 validation

- Syntax receipt: [quiz1-bash-n-audit](../../evidence/runs/quiz1-bash-n-audit/meta.json).
- Exact runner receipt: [meta](../../evidence/runs/quiz1-run-audit-r1/meta.json), [stdout](../../evidence/runs/quiz1-run-audit-r1/stdout.txt), [stderr](../../evidence/runs/quiz1-run-audit-r1/stderr.txt).
- Preserved raw output: [run.dwDwnD](raw-output/run.dwDwnD/).
- Observed oracle: full dump contains target class IX and target instance X under transaction index 1; session A returns row 1/100 and rolls back.
- Answer check: [answer.md](answer.md) predicts the observed same-owner hierarchy and does not claim conversion/escalation execution.
- Cleanup check: runner exit 0, `qalockq1f30` registry row absent, `.quiz-owner` and `runtime-owned` absent.
