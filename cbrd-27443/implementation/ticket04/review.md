# Ticket 04 main review (in progress)

Dispatch fixed points: engine `74ee7520a76dd5c1635bed9e75a06c233026115a`, shell `8b00d634cfb36d654c88d747114aa126efa866c6`. Main performs Standards and Spec review directly under the approved one-worker-per-ticket topology.

Initial source `ac7f26091` is not accepted. Rotation baseline retained at `/home/vimkim/.cache/cbrd27443-04-red`: the old active file grows past the proposed 1 MiB limit. Native final evidence is outstanding.

## Standards

Pending corrections: legacy C++ default argument declaration needs personal-policy indent guards. New helper state must reset between attempts. Initial inline log helper is shared by launcher marker and relay, avoiding inconsistent rotation policy; POSIX-only build linkage remains explicit.

## Spec

Pending findings sent to worker04:

- Process-associated F_SETLK locks do not serialize concurrent threads, and closing another same-inode descriptor can release their locks. Use locking that covers both process and thread writer concurrency.
- Renaming an oversized existing active file merely creates an oversized archive. Define and verify retention migration for existing oversized files.
- Replace unbounded anonymous startup spools without truncating diagnostics; bounded pipes must be drained fairly during every original readiness wait, and finish must drain before waiting for acknowledgement. Preserve registration checks and existing timing criteria.
- Verify actual executable-generated stdout/stderr, including startup failure larger than archive retention. Observer writes to producer pipe endpoints are supplemental evidence.
- Runtime failure records must remain bounded and survive successful writes by other relays. Test observable failures and consider SIGXFSZ rather than relying solely on write returning errno. No claim assumes an unavailable filesystem and unavailable system logger can guarantee persistence.

Final acceptance requires all seven ticket checkboxes, clean source/test commits, exact installed/copied identities, native verdict and regression results. No completion claim yet.

## Review corrections through 731b39e0f

Worker replaced process-associated locks with flock on each independently opened lock description, bounded existing active/archives by retaining their newest 1 MiB under the same lock, reset per-attempt output error state, and guarded the legacy C++ declaration. The status record is fixed at 256 bytes and successful writers do not clear it. Relay reopens current log under lock for every append. Linux socket creation has a non-Linux fcntl fallback.

Focused source5604e9e04 rotation probe passed 87 checks. A further startup RLIMIT_FSIZE probe reproduced launcher termination by SIGXFSZ; source731b39e0f now blocks that synchronous signal only in the logging thread, consumes newly pending logging-generated signal and restores the prior mask/disposition. Relay handles its own SIGXFSZ as a write error. Both corrections still require final exact native evidence. Private syslog capture now precedes fault injection; full generated startup streams are counted separately for concurrent successful and failed attempts.

Current native attempt `cbrd27443-04-731b39e.ZSmpsh` has passed original121/master216 and is progressing through restart/boundary/rotation. It uses engine731b39e0f/test6193aee65 with clean exact installation match. Worker identified and main requested removal of a testcase dependency on pre-existing `/dev/log`: a private device directory with preserved essential devices and private syslog socket will replace it. Retain the current attempt and require final native evidence on the corrected committed fixture.
