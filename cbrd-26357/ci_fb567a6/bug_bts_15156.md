# Why bug_bts_15156 failed after restarting the master

**The test restarted the master successfully, but all 21 attempts to stop database `15156` failed its success check. The underlying reason remains unproven.** This is an open server-lifecycle failure, not a confirmed CPU-threshold flake and not a failure that can safely be dismissed because retries were disabled.

## What the test intended to check

The testcase starts a database, deliberately kills `cub_master`, samples server CPU usage, restarts the service, and expects the existing database server to reconnect so it can be stopped normally. The Linux CPU threshold is 18 percent. Its [final checks](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/c4b9d482fbd491a68510b2552df2c3cac91911fc/shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh#L46-L90) require a successful master start, exactly one master process, and a successful database stop.

## What the retained trace establishes

| Stage | Observed result | Meaning |
| --- | --- | --- |
| Initial database startup | `cubrid server start: success` | Initial startup passed |
| Deliberate master kill | `kill -9 27617` | The intended disruption occurred |
| CPU sampling | No loop iteration or CPU assertion is emitted | No matching CPU sample reached the check; this is not a measured CPU excess |
| Service restart | Master-start success count is 1; `master=1` | Both master assertions passed |
| Database stop | Success-message count is 0 on all 21 iterations | The stop assertion failed for approximately 210 seconds of sleeps |
| Final verdict | `bug_bts_15156-1 : NOK` | The first recorded assertion is the final lifecycle assertion |

The total testcase duration was 229.654 seconds (its own shell timer prints 228). This is consistent with the 21 ten-second sleeps plus setup. The logged `top` process being killed is intentional cleanup by the test, not evidence of a database crash. [Shard log](https://github.com/CUBRID/cubrid/actions/runs/36570256001/job/109416879787).

## What remains unknown

The log does not print the contents of `server.log`, `service.log`, or `top.log`. `write_nok` is called without a log filename, so the failure message loses the diagnostic that would distinguish an exited server, a live server that did not re-register, or another stop-command error. Each stop attempt also overwrites `server.log`, losing earlier responses.

The absent CPU sample is consistent with the server having exited, but can also result from the broad `top | grep` sampling. It is not proof of process death. Likewise, a failed stop-message check alone cannot distinguish a dead server from a live but unreachable server. The trace's `internal_err=0` only means that the helper found no literal `Internal Error`; it is not proof that no crash or other error occurred.

## Source investigation and PR relation

At the exact engine revision, [`master_connector.cpp`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/connection/master_connector.cpp#L1285-L1374) has two materially different paths: with HA enabled, master disconnection sets the server to stop; with HA disabled, it attempts reconnection and retries while its state is closed. These are candidates to distinguish with runtime evidence, not diagnoses of which path this run took. The effective HA setting and process lifetime are not established by the retained testcase message.

The entire master connector file is identical to engine develop `f1bd99ed43a134383bc0be1d766a6f121601a499`. The PR's `server_support.c` change adds an OOS thread-field clear in request cleanup, outside the connector loop. This narrows direct source attribution but does not exclude indirect behavior elsewhere in the engine. Historical cached runs contain passes, including September 25, but are not controlled comparisons with this engine and environment.

**Category:** unresolved server lifecycle or test environment failure. **PR relation:** unknown; there is no direct connector change, but no matched runtime baseline. **Confidence:** high for the failed stop condition; low for a specific underlying cause. Automatic retry removal explains why one failure remains visible, not why the stop failed.

## How to resolve the remaining cause

First recover this shard's diagnostic archive if it retained `server.log`, `top.log`, server error logs or a core. The current collector invocation requested text evidence only, so archive contents and core presence were not established. Do not infer that unavailable local files are absent on the CI server.

If those files are unavailable, perform a contained comparison using the same testcase on this PR head and its develop parent. Capture the server PID and exit status before and after killing the master, the effective HA mode, every stop response, and server registration state. Require a nonempty CPU sample. Keep retries disabled so the original event is preserved.

**Falsifiers for the leading alternatives:** a live server PID excludes simple server exit; successful re-registration excludes failure to reconnect; a core or explicit exit reason identifies a different failure path; an identical baseline failure weakens OOS-specific attribution. A repeatable PR-only failure would strengthen it.

No database execution, configuration edit, or source fix was performed in this investigation. The correct decision today is to retain this failure as unresolved.

## Evidence scope

This report concerns [PR 7990](https://github.com/CUBRID/cubrid/actions/runs/36570256001), engine `fb567a629cdb390fff920542173fa36f454c74a0`, September 29, 2026, run `36570256001`, attempt `1`, shell shard `35`. The testcase is `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh` at private testcase revision `c4b9d482fbd491a68510b2552df2c3cac91911fc`. The debug build reports `11.5.0.2637-fb567a6`.

Evidence was collected on October 1 with `cubrid-ci 0.2.0 (45944012aaaa, release)` and validated against the collector schemas, observation, checksums, identities and counts. [Evidence excerpts](evidence.md) preserve the relevant assertions. This is log and source analysis; no database testcase was rerun. [Main report](../ci_analysis_report_fb567a6_codex.md).
