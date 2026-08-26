# Zero-wait demotion and the ticket intent are understood

The user can now state that a zero-wait logical policy is allowed to produce immediate rejection generally, but that CBRD-27198 changes the behavior for operations that request an unconditional structural-page latch. This unlocks the deeper design question of why waiting is preferred over unwinding and retrying at the sector-reservation caller.

## Evidence

After correcting the conditional/unconditional reversal, the user summarized that a logical zero-wait request must not prevent certain internal operations from completing unconditionally, then challenged why the caller could not handle immediate failure.
