# Ticket 05 main review (in progress)

Dispatch fixed points: engine `731b39e0f976a97f0dac62374aba976b9dca37f9`, shell `28d75755d9dd69ef61a1d80a80a37aabade3a7ab`. Main performs Standards and Spec review directly under the approved topology.

## Standards

Initial source `8aa8fcab6` changes only master_heartbeat.c. Parent-only bounded tokenization and stack storage replace child-side preparation; all child exec/failure handling goes through the shared explicit launcher. No child branch returns to master cleanup. Existing HB registration confirmation, state update and one-second failed-spawn requeue remain. CMake util:57–60 includes this file only for UNIX; no Windows runtime claim. Diff check passed; final build and clean state are pending.

## Spec

Retained dispatch baseline `cbrd27443-05-red2/ha.json` independently shows HA automatic restart inheriting the master error log and an identical socket target. Baseline `05-red4/ha.json` shows a managed utility inheriting the master error log and two sockets through actual cub_commdb IPC. Its missing-executable launch acknowledgement returned0; the new checked spawn may change this internal acknowledgement to failure. Public heartbeat failure code/messages/EOF and success registration semantics still require explicit verification.

First HA fixture used localhost and unexpectedly launched copy/apply because utility local-host recognition compares the node name with gethostname (including hostname-prefix equivalence), unlike master address normalization. Those caller-FD leaks are retained in05-red for ticket06; corrected single-node tests use the actual hostname mapped to private loopback. Red3 was only an installed-command spelling error and must not be presented as product failure.

All seven acceptance areas and final native evidence remain pending. The proposed server-console destination for HA server and managed utilities reuses ticket04 retention. Direct local copy/apply creation and real two-node replication remain ticket06 scope.
