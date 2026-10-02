# Combined review — in progress

Fixed point: user-approved engine `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`. Current source-reviewed correction: `0809a480d` (full SHA in engine history); runtime/final integration qualification is pending. Main performs Standards and Spec axes directly under the approved one-worker-per-ticket adaptation; no additional review agents. This checkpoint is not ticket08 acceptance.

## Standards

Reviewed the combined process helper, console relay/logging, build integration, PL, master/HA and broker creation policies against personal CUBRID policy and applicable AGENTS guidance. User-approved enforced formatting applies. New throwing STL preparation lives in `.cpp` and catches exceptions locally into errno. Legacy C++ additions use INDENT guards. The child spawn path performs prepared descriptor mapping, signal disposition, bounded error notification and exec/_exit; parent preparation owns allocation/environment work. Platform-specific source inclusion and Windows call paths were inspected, without claiming a Windows build.

The review keeps the generic synchronous proc_execute unchanged. Intentional direct-server and SA output remain inherited through the stdio helper; absent standard descriptors are reserved before logging. Required broker communication attaches or arrives after exec, verified separately through actual client SQL. No unrelated refactoring is required by the smell heuristics.

## Spec

Earlier per-ticket reviews and their exact-build evidence remain linked in the ticket directories. Final acceptance still requires ticket08's A01–A16 mapping and interaction qualification on one final source/test/install state, particularly rotation combined with server/PL restart, HA and broker activity. Windows build/runtime and external gateway-backend execution remain unverified limits.

Confirmed Spec finding (ticket07 reopened): broker_process_group retains two output descriptors, control and acknowledgement per successful child until outer administration finish. broker_admin_pub's ordinary CAS loop waits for individual readiness but does not release these channels, and the configured CAS limit can exceed the launcher's available descriptors. Investigate a real ordinary-broker startup with several initial CAS and a modest soft RLIMIT_NOFILE, comparing an immutable pre07 baseline with the candidate; require actual client SQL and cleanup. Existing high-FD tests lower the limit to1024 but use only one initial CAS. Do not change readiness or truncate caller diagnostics merely to lower descriptor use. Any confirmed07 correction should return to its original worker after the current owner releases.

Ticket06 corrected final native qualification is accepted: RGZgmT1/0/0,1,843 assertions,11 replicated records and independently verified18 installed/native plus90 actual fixture hashes. Exact local copy/apply baseline output and codes, sibling public codes, and setup-failure precedence pass. Reports and retained failures are archived under ticket06. Fresh08 now investigates the scaling question and remaining interaction coverage. No merge, publication or full-QA claim follows from this draft.


Worker08 reproduced the scaling regression without source/test edits. Evidence [pre07](ticket07/scaling-evidence/pre07.json), [candidate](ticket07/scaling-evidence/current.json), [identity](ticket07/scaling-evidence/identity.json). With32 initial ordinary CAS and soft RLIMIT_NOFILE128, immutable41ac starts32CAS and serves actual CCI SQL27443; currentb0 returns1 with nine EMFILE diagnostics and rolls back. Raising only the candidate limit to256 restores32CAS/SQL plus EOF/lock release. Both fixtures fully clean processes and private IPC. Baseline's expected caller-FD leak is recorded separately from its successful startup; this observation is not a claim that baseline passes the FD specification. Main independently inspected both reports. Route the correction to original07, then resume08 combined qualification; do not mask it by changing test limits or omitting the valid32CAS configuration.


## Scaling correction source review

Candidate0809a480d bounds producer channels by service-log destination within the invocation. Three optional shared-stream entries retain all original outer readiness/diagnostic waits; each producer retains a distinct PID record and explicit environment/SIGCHLD policy. Per-launch log validation and start marker remain. Zero successful producers after first exec failure still leave the prepared relay owned and finished; subsequent setup failure preserves that ownership and propagates failure before existing rollback. Default helper callers do not request shared streams.

Main required resetting exec_failed before potentially throwing parent preparation on reused entries;0809 includes the reset. Normal formatting/hooks and the additive POSIX-only interface were inspected. No outstanding source Standards/Spec finding remains in this correction. Runtime green5 passes147 scaling checks, including32 ordinary/64multi-broker CAS at hard=soft128, validSHARD32 at1024, complete current/late diagnostics and cleanup. Prior fixture NOKs remain documented. Existing broker/base/replication regression results and08 final native still gate final acceptance.
