# Combined review — in progress

Fixed point: user-approved engine `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`. Current reviewed candidate: `b0f569011731d37516f2f62dad9d3d4c76312291`. Main performs Standards and Spec axes directly under the approved one-worker-per-ticket adaptation; no additional review agents. This checkpoint is not ticket08 acceptance.

## Standards

Reviewed the combined process helper, console relay/logging, build integration, PL, master/HA and broker creation policies against personal CUBRID policy and applicable AGENTS guidance. User-approved enforced formatting applies. New throwing STL preparation lives in `.cpp` and catches exceptions locally into errno. Legacy C++ additions use INDENT guards. The child spawn path performs prepared descriptor mapping, signal disposition, bounded error notification and exec/_exit; parent preparation owns allocation/environment work. Platform-specific source inclusion and Windows call paths were inspected, without claiming a Windows build.

The review keeps the generic synchronous proc_execute unchanged. Intentional direct-server and SA output remain inherited through the stdio helper; absent standard descriptors are reserved before logging. Required broker communication attaches or arrives after exec, verified separately through actual client SQL. No unrelated refactoring is required by the smell heuristics.

## Spec

Earlier per-ticket reviews and their exact-build evidence remain linked in the ticket directories. Final acceptance still requires ticket08's A01–A16 mapping and interaction qualification on one final source/test/install state, particularly rotation combined with server/PL restart, HA and broker activity. Windows build/runtime and external gateway-backend execution remain unverified limits.

Read-only review question, not yet a reproduced defect: broker_process_group retains two output descriptors, control and acknowledgement per successful child until outer administration finish. broker_admin_pub's ordinary CAS loop waits for individual readiness but does not release these channels, and the configured CAS limit can exceed the launcher's available descriptors. Investigate a real ordinary-broker startup with several initial CAS and a modest soft RLIMIT_NOFILE, comparing an immutable pre07 baseline with the candidate; require actual client SQL and cleanup. Existing high-FD tests lower the limit to1024 but use only one initial CAS. Do not change readiness or truncate caller diagnostics merely to lower descriptor use. Any confirmed07 correction should return to its original worker after the current owner releases.

Ticket06 corrected final native qualification is accepted: RGZgmT1/0/0,1,843 assertions,11 replicated records and independently verified18 installed/native plus90 actual fixture hashes. Exact local copy/apply baseline output and codes, sibling public codes, and setup-failure precedence pass. Reports and retained failures are archived under ticket06. Fresh08 now investigates the scaling question and remaining interaction coverage. No merge, publication or full-QA claim follows from this draft.
