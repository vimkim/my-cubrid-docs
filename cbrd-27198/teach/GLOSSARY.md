# PR #7630 Page-Access Glossary

This is the canonical language for separating CUBRID's logical concurrency control from physical buffer-page synchronization.

## Terms

**Transaction lock**:
A transaction-scoped concurrency-control claim on a logical database resource, with a lock mode that determines conflicting operations and preserves isolation.
_Avoid_: Page lock, latch

**Page latch**:
Short-lived synchronization that protects the physical consistency of a buffer page while threads access its in-memory contents.
_Avoid_: Transaction lock, durability lock

**Page fix**:
A page-buffer operation that makes a page resident and pins it for the caller while obtaining the requested page latch; it is later paired with an unfix.
_Avoid_: Disk read, lock acquisition

**Latch mode**:
The requested access compatibility, principally read or write.
_Avoid_: Wait mode

**Latch condition**:
Whether an unavailable latch may queue and wait (unconditional) or must be rejected immediately (conditional).
_Avoid_: Latch mode, timeout value

**Conditional latch request**:
A request that succeeds only if the latch can be granted immediately; current incompatibility produces immediate rejection without queueing.
_Avoid_: Timed latch request

**Unconditional latch request**:
A request that queues and waits when the latch cannot be granted immediately, while remaining subject to other error and timeout mechanisms.
_Avoid_: Infallible latch request, infinite latch
