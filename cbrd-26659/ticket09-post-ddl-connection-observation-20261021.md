# Work456/09: post-DDL connection observation

Date: 2026-10-21, Asia/Seoul. Reader: the Work456 coordinator and a later connection/DDL investigator. Related context: [ticket 09 functional receipt](ticket09-large-indexed-oos-keys-20261021.md), [engine PR 8128](https://github.com/CUBRID/cubrid/pull/8128).

Two fresh native attempts rejected a new CSQL connection immediately after a successful PK recreation. A third complete attempt passed that scenario and every later combination. The cause remains unknown. The observations establish no engine crash, wrong key, wrong flag or damaged owner. This observation has no assigned JIRA attribution or production repair.

## Exact trigger and evidence

Source/install: `CUBRID/cubrid@1ef86a7efa34002e971b1b30bcf5d451e9db441b`, Linux 16 KiB OptDebug. Private test input: `e7320251c0109a202c8ffcb7ce4f24b2534fee0b`. Raw root: `/home/vimkim/temp/work456-implementation/ticket09/`.

The first cell is VARBIT/DEFAULT/PK/maintenance/single. Only the indexed `k` can demote. Fixed integers identify rows. The independent input has a short key and two 5107-byte keys with equal prefixes and distinct tails. The controller checks ordinary/index reads, expected constraint errors, rollback, committed UPDATE, DELETE and reinsertion before the DDL sequence.

1. `ALTER TABLE keys_rows DROP CONSTRAINT keys_idx` commits.
2. The complete three-row model passes. Named index metadata reports zero. Actual surviving records retain the required C/S flags.
3. `ALTER TABLE keys_rows ADD CONSTRAINT keys_idx PRIMARY KEY(k)` commits successfully.
4. The next independent `csql -C -udba --line-output w456keys` fails to connect before it can inspect the full row model.

Both `final02` (22.359 s) and `final03` (20.863 s) have native shell 1 FAIL. Their `keys.first-failure.log` identifies `constraint_recreate_model`. CSQL reports:

```text
ERROR: Failed to connect to database server, 'w456keys', on the following host(s): localhost
```

Their `keys.*.constraint_recreate.stdout.log` records successful execution and commit. Owned cleanup later notifies the server and stops it successfully. `keys.database_server_1.exit.log` reports exit status 0. Server stdout contains no assertion. These observations do not establish a server crash. The original attempts did not preserve an informative client/server error-log snapshot before teardown.

Artifacts reside in each attempt's `CTP/result/shell/large_keys_evidence.tar.gz`. Native failure XML, case log, expected selection and strict verifier output remain in `CTP/result/shell/current_runtime_logs/` and `verify.log`. The runner itself returned 0, while the strict verifier rejected the actual NOK.

## Passing comparison and next investigation

Input `91fc999e9ef60c9532299b3614b8f060864845ad` adds only failure-time diagnostics and process capture. That branch does not execute on a passing path. `final04` passed all 108 phases in 395.474 s. All 72 core cells and two aliases executed constraint DROP/recreate with complete models, current flags, metadata and rebuilt-index lookup. The final independent audit checks these assertions. This passing comparison supplies no causal explanation or repair credit for the earlier failures.

A later investigator can use a fresh approved native slot and the same isolated attempt helper. First reproduce the connection rejection without changing expected values. Capture owned client/server error logs, the live owned master/server identities, and connection status before cleanup. Then reduce the first cell while retaining the actual DDL and full model. Distinguish connection admission or runtime conditions from a DDL/storage failure before choosing a repair target. Do not replace full-value/flag assertions with a connection-success assertion or a retry that hides the observation.

The required ticket 09 scenarios all executed successfully in `final04`. This follow-up preserves the unexplained prior runtime observation. It does not assign failing coverage to a guessed existing OOS defect.
