# Patch review

Base: 48250d60cf8cece13abaff0f1b29982c59a256c0; working-tree diff, no commits.

## Standards

0 findings. No applicable documented testcase coding standard was found. Adjacent server-side loaddb cases use the same explicit write_ok/write_nok, exit-status checks, and output checks. All twelve Fowler heuristics reviewed; no actionable smell.

## Spec

0 actionable patch findings. Invalid 100 input, test1/test3 and final comparison preserved; test2 failure/error, rollback counts and next valid load asserted; obsolete test2 block removed from both answer variants. No engine changes or scope expansion.

Validation limit: rollback and final-row assertions failed on this engine. The next valid loader command succeeded, but residual invalid-load rows remain. Do not describe rollback as successfully verified. Windows answer consistency reviewed; Windows execution unverified.

Review agents: /root/tc_standards and /root/tc_spec.
