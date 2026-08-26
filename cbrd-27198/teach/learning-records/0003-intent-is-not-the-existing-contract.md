# Intended meaning is not the existing contract

The user correctly challenged the inference that `lock_timeout` must be lock-only merely because of its name and main use. Future review defense should distinguish declared/source-comment intent from the effective code contract, then demand code, documentation, history, and tests before accepting a behavior change.

## Evidence

The user identified that an application may intentionally depend on zero-wait page-latch behavior and insisted that the claim be checked against code rather than accepted from the parameter name.
