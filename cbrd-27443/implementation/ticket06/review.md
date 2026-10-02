# Ticket 06 main review — verified candidate; compatibility correction queued

Dispatch fixed points: engine `8aa8fcab689088b3cd24ad6e44e567e3915eae7e`, shell `992b4076c3a8d8f8e2ee1aee7495ed8fe562b004`. Candidate engine `41ac0c2ce39590349e8e5759dc376f88e1cb660b`, shell `8c1a1bc791e5e29174fd5f6e78d98d6cec02f7bb`. Main performs Standards and Spec review directly under the approved one-worker topology. This is not ticket acceptance.

## Standards

No outstanding source finding after review of the three changed source files. Explicit local HA batch ownership replaces only copy/apply asynchronous launch boundaries; generic synchronous proc_execute is unchanged. Parent preparation and existing shared exec policy keep child work constrained. Allocation precedes child creation. All three batch owners finalize channels on success and failure. Fair pumping and per-owned-PID nonblocking reaping account for synchronous management queries restoring SIGCHLD defaults. Optional framing is bounded to 8 KiB per stream/producer; existing unframed callers preserve their behavior. POSIX guards keep the new poll/batch code out of Windows HA paths. Formatting-only reference alignment was corrected before candidate41 build. No Windows runtime claim.

## Spec

A15 candidate evidence uses actual separate network/UTS/mount namespaces, private veth communication, private roots/configs/volumes/logs and independently created databases. Source-only inserts must appear through target-local CSQL. Main checked boot_cl.c:578–603 and the CSQL connection branch: explicit db@localhost supplies only that host, with no preferred-host routing/retry, so target SQL cannot silently read the source through registry fallback. Actual copy/apply replacements are distinct and leave the other utility running. Local capture variants and remote-managed launches require both EOF and subsequent replicated records.

Two material findings are recorded separately. First, exact8aa baseline local missing-executable calls return0 and contradictory success/failure lines because failed exec returns into launcher control flow. The safe helper returns1 and preserves execv errno text. User decision for this narrow exit-code exception is pending; do not label it preservation or resolve the failure-contract checkbox. Remote missing-exec1, unlisted-DB1 and late producer-failure1 remain preserved.

Second, initial batch pumping spliced short concurrent diagnostics. Baseline red4 capture10 had430000 stderr bytes and2000 intact lines per producer; green2 had equal bytes but only1994/1995 intact markers. Main required a source fix rather than weaker byte-only tests. Focused green3 on09a now has exactly2000 whole short lines per producer on both streams, independently counted by main, plus complete long newline-free payloads and unterminated tails. Candidate41 is a formatting-only successor; full native verification remains required.

## Verified evidence and remaining decision

Exact native `.cache/cbrd27443-06-41ac0c2.FvYAKF` passed1 case with0 failures/skips and1326 assertions:121 original +216 master +76 restart +383 boundary +96 rotation +152 HA +282 replication, plus the present probe. Main independently reran the focused verdict verifier and checked every assertion, all11 replicated records, both distinct automatic restarts, both remote launches, and all10 installed/copied/both-node identities. Both worktrees are clean and worker06 released ownership. See report.md and evidence/ for compact data, complete assertion lists and retained baseline/regression distinctions. Ticket07 proceeds independently under its accepted01 dependency; ticket06 remains unresolved solely for the public missing-executable exit-code decision. No approval is inferred from test success.

## Current next step

No exit-code exception was approved. Main will follow the existing spec by retaining legacy local missing-executable0 and caller diagnostics. The original06 worker receives that narrow correction after07 releases ownership, then requalifies the corrected integrated state before acceptance. The earlier0→1 candidate remains historical verified evidence, not an accepted contract change. This follows existing authorization rather than treating silence as an answer.

## Compatibility correction accepted

Final engine `b0f569011731d37516f2f62dad9d3d4c76312291`, tests `26ab88a3545aaa08a2bb5ef461b03fb0192e8a6d`; native `cbrd27443-06c-b0f5690.RGZgmT` passes one case with no failures/skips,1,843 assertions including313 replication checks,495 broker checks and11 replicated records. Nine supplemental broker assertions pass. Main independently ran the native verifier, inspected every assertion, hashed18 installed/native objects and90 actual fixture files, and compared baseline8aa captures4/8 against final28/35: identical local copy/apply code0, stdout and stderr. Evidence is in [compatibility-evidence/final](compatibility-evidence/final/).

Standards: the correction is confined to util_service.c and replication_matrix.py. Optional error classification is explicitly passed by callers; no unguarded C++ default arguments remain. Normal hooks and diff checks pass, and both worktrees are clean. Spec: invocation-local producer-exec classification preserves the original local and replication public codes without returning a failed child into parent code. Relay/log setup failures remain1, including after an earlier compatibility0 in the same request; final mixed fault restores the original PID set. Heartbeat-start remains1 and remote paths retain their checked result. Arbitrary baseline child interleavings and duplicate shutdown side effects are not reproduced, consistently with the safe-child-exit requirement.

The prior proposed0-to1 exception received no approval and is no longer a blocker: this correction follows the original preservation contract. Ticket06 has no outstanding finding within its qualified Linux scope. Ticket08 still owns combined interaction verification; Windows and gateway-backend limitations are unchanged.
