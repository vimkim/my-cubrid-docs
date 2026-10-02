# Ticket 05 main review

Accepted at engine `8aa8fcab689088b3cd24ad6e44e567e3915eae7e`, shell `992b4076c3a8d8f8e2ee1aee7495ed8fe562b004`. Dispatch fixed points: engine `731b39e0f976a97f0dac62374aba976b9dca37f9`, shell `28d75755d9dd69ef61a1d80a80a37aabade3a7ab`. Main performed Standards and Spec review directly under the approved topology.

## Standards

No outstanding finding within this ticket. Source changes are scoped to master_heartbeat.c: bounded parent argument preparation and shared explicit launch replace both raw child branches. Failed exec cannot run master cleanup or return into parent flow. Existing HA state assignments, registration confirmation jobs and retry timing remain. Normal hooks, build/install, syntax and diff checks passed; source/tests are clean. Existing CMake excludes this HA source from Windows; no Windows/non-Linux runtime is claimed.

The shared helper preserves master/parent auto-reaping but resets producer SIGCHLD to default, whereas old raw HA exec inherited SIG_IGN. This matches initial helper-launched service producers; PL reinstates its explicit legacy policy. Server/PL behavior is tested here; actual copy/apply internal child behavior remains ticket06 qualification.

## Spec

All seven acceptance areas accepted within single-node scope. Baseline red2 shows restarted server inheritance of master.err and an actual socket; red4 shows managed utility inheritance of master.err and two sockets. Fixed immediate/pre-dispatch snapshots prove clean descriptor ownership, dedicated stdio, no extra failed child/relay and a surviving master. The internal missing-exec acknowledgement changes from0 to ER_FAILED/255; public heartbeat retains success0/failure1 and original diagnostics. This correction is explicit, not hidden as unchanged raw behavior.

Final tests verify startup/restart idle→standby→to-be-active→active transitions, exact SQL/PL result rows after EOF and recovery, high FD4096 above lowered soft1024, six capture forms, independent heartbeat-stop EOF/state, public missing-DB/exec/log-open failures, and live-service failure cleanup. HA recovery retains its first-registration basis: observed30.186s to first restart,17.130s from kill, then3 failed attempts over2.209s before recovery.

Fixture corrections remain distinguished from product defects: local-host spelling unexpectedly launched copy/apply; exiting-process /proc races now use a bounded same-PID retry without hiding live failures; soft128 exhausted legitimate server FDs; raw255 was initially mistaken for public1; warning filtering hid failed-spawn messages; recovery timing was initially measured from the wrong event. No product timing/severity was changed to fit those observations.

## Evidence and limits

Final exact native `cbrd27443-05-8aa8fca.UE7ABw`: 1 success, 0 failures/skips; 1,034 assertions (121 original +216 master +75 restart +374 boundary +96 rotation +152 HA), plus present probe. Main independently checked matrices, exact verdict/counts, all nine installed/copied hash pairs and clean source/test tips. See [report](report.md), [final evidence](evidence/safe-summary.json), and [baseline summary](evidence/baseline-summary.json).

Actual two-node replication and local direct copy/apply launch remain applicable ticket06 work. The changed shared master boundaries are not proof of data replication. Their output uses the existing bounded server-console policy; existing error logs remain separate. No CTest (disabled), Windows/non-Linux runtime, whole-corpus QA or broker qualification claim.
