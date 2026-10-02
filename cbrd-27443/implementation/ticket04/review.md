# Ticket 04 main review

Accepted at engine `731b39e0f976a97f0dac62374aba976b9dca37f9`, shell `28d75755d9dd69ef61a1d80a80a37aabade3a7ab`. Dispatch fixed points: engine `74ee7520a76dd5c1635bed9e75a06c233026115a`, shell `8b00d634cfb36d654c88d747114aa126efa866c6`. Main performed Standards and Spec review directly under the approved one-worker-per-ticket topology.

## Standards

No outstanding finding within the reviewed scope. The shared console helper coordinates markers and relay appends through independently opened flock descriptions, covering separate processes and threads. The child-before-exec path remains preparation-free; logging and signal masking occur in the parent or executed relay. Legacy C++ declarations have indent guards. Normal formatting hooks, build/install and diff checks passed; source/tests are clean. Non-Linux socket setup has a fallback, but no non-Linux build/runtime is claimed.

## Spec

All seven ticket criteria accepted. Permanent retention is active plus three archives, each at most 1 MiB; existing oversized files retain their newest 1 MiB under lock. Private regular files use mode0600. Reopening under the same lock avoids writing deleted archives. A fixed256-byte latest-failure record and nonblocking syslog expose logging errors; success does not clear another writer's failure. Failed bytes are discarded while draining continues, with later writes retried. Reporting cannot be guaranteed if neither filesystem nor logger accepts data.

Bounded startup pipes replace unbounded spools. Existing readiness waits pump both streams fairly and finish drains them before acknowledgement; registration criteria are unchanged. Exact current-attempt stdout/stderr token counts beyond archive retention survive concurrent successful/failed starts without contamination. Startup SIGXFSZ is handled in the calling thread while preserving caller signal policy; runtime handling belongs to the relay.

Resolved review findings: process-associated locks failed thread exclusion; oversized existing archives violated the size policy; startup file limits terminated the launcher; initial endpoint injection needed actual executable producers; fault capture depended on host syslog. Each was corrected by worker04. The final fixture creates a private device tree with real bound character devices and its own initially absent syslog endpoint. Caller-crash tests require an actual producer before terminating its launcher.

## Evidence and limits

Final exact native `cbrd27443-04-731b39e.S8CNvN`: 1 success, 0 failures/skips, 889 checks (121 original +216 master +76 restart +380 boundary +96 rotation), plus present probe. Main independently checked every matrix, verdict, clean source/test tips and all nine installed/copied executable/library identities. Retained `ZSmpsh` was also a full pass before the testcase portability revision. Original rotation and startup-file-limit RED observations remain separately identified.

See [report](report.md), [safe final evidence](evidence/safe-summary.json), and [baseline summary](evidence/baseline-summary.json). Linux focused verification does not establish Windows/non-Linux runtime, CTest (disabled), whole-corpus QA or later HA/broker qualification. External callers must consume their pipes; ordinary filesystem stalls are not bounded by the lock retry policy. The stable lock inode must not be replaced while relays run. Final all-service combination belongs to ticket08.
