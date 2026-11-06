# Coverage: PR #8417 at 1f9f09f362390e10ed06d80f9aae3ae2e361b2d2

| Paths | Invariant | Owner (model) | Evidence | Result |
|---|---|---|---|---|
| error_code.h, msg/*/cubrid.msg | -1393 consistent, message args match | Systems (opus) | L2 source; L4 compile | pass |
| fault_injection.c/.h | FI 700000 debug-only, inert unless installed | Systems | L4 compile + nm on release object | pass |
| vacuum_oos.cpp/.hpp | lookup helper, error propagation, logic-defect assert | Systems, Recovery | L2-3 | pass |
| vacuum.c vacuum_heap | er_stack balance, VFID skip, deferral flow | Systems, Concurrency | L3 | pass |
| vacuum.c job cursor gate | master-only state, no skip/double dispatch | Concurrency (sonnet), Systems | L3 | pass |
| vacuum.c finished_block asserts, SA branch | accept exactly -1393 | Concurrency, Recovery | L2 | pass |
| vacuum.c interrupted block lifecycle | idempotent re-run, restart persistence, log retention, no open sysop | Recovery (opus) | L3; earlier adversary A executed restart and SA vacuumdb probes | pass |
| unit_tests/oos/* | behavior-level tests, no production hook | Systems | L2; coordinator ran debug latch-timeout ctest 6/6 at 1f9f09f36 | pass |
| HA | none: no new log record or append; vacuum not replicated | coordinator | grep of patch | n/a |

Shared challenge (OOS leak / referenced OOS reclaimed / block marked vacuumed with skipped object): Concurrency (sonnet) and Recovery (opus) independently found no feasible path. Both level 3, source only.
