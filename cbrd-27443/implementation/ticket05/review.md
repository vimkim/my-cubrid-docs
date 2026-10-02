# Ticket 05 main review (in progress)

Dispatch fixed points: engine `731b39e0f976a97f0dac62374aba976b9dca37f9`, shell `28d75755d9dd69ef61a1d80a80a37aabade3a7ab`. Main performs Standards and Spec review directly under the approved topology.

## Standards

Initial source `8aa8fcab6` changes only master_heartbeat.c. Parent-only bounded tokenization and stack storage replace child-side preparation; all child exec/failure handling goes through the shared explicit launcher. No child branch returns to master cleanup. Existing HB registration confirmation, state update and one-second failed-spawn requeue remain. CMake util:57–60 includes this file only for UNIX; no Windows runtime claim. Diff check passed; final build and clean state are pending.

## Spec

Retained dispatch baseline `cbrd27443-05-red2/ha.json` independently shows HA automatic restart inheriting the master error log and an identical socket target. Baseline `05-red4/ha.json` shows a managed utility inheriting the master error log and two sockets through actual cub_commdb IPC. Its missing-executable launch acknowledgement returned0; the new checked spawn may change this internal acknowledgement to failure. Public heartbeat failure code/messages/EOF and success registration semantics still require explicit verification.

First HA fixture used localhost and unexpectedly launched copy/apply because utility local-host recognition compares the node name with gethostname (including hostname-prefix equivalence), unlike master address normalization. Those caller-FD leaks are retained in05-red for ticket06; corrected single-node tests use the actual hostname mapped to private loopback. Red3 was only an installed-command spelling error and must not be presented as product failure.

All seven acceptance areas and final native evidence remain pending. The proposed server-console destination for HA server and managed utilities reuses ticket04 retention. Direct local copy/apply creation and real two-node replication remain ticket06 scope.

## Fixture review during focused iteration

Keep product failure evidence separate from fixture corrections: an exiting PID can transiently deny /proc FD access before becoming Z, so the shared scanner now retries that same PID for at most200ms and still fails persistent unreadable live processes; final cleanup remains strict. A soft limit128 exhausted the server's own event/timer descriptors, so HA uses duplicated FD4096 above a viable lowered soft limit1024. Raw cub_commdb failure is255, while public heartbeat failure remains1.

Immediate managed-parent snapshots can still contain intentionally prepared producer pipes before parent cleanup. The fixture verifies dedicated child stdio first, then excludes only that declared handoff when comparing immediate parent internals with child non-stdio targets, retaining pre-dispatch evidence too.

HA recovery delay is measured from proc->frtime, assigned at first registration, not from the later SIGKILL timestamp. Source timers remain unchanged. Enable existing error_log_warning in the private config to observe ER_WARNING_SEVERITY failed-spawn diagnostics; do not change product severity to fit a test. Expanded proof includes post-restart SQL/PL, managed failures while master stays live, heartbeat-stop state and separate EOF, public startup failures and all capture modes. Final native evidence is still pending.
