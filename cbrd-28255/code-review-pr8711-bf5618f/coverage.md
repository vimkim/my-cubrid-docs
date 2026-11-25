# Coverage — CUBRID/cubrid#8711 at bf5618f627

Pinned diff: `git diff 6d8296b15c9694a7fc2c7920e539ec66d3d004aa bf5618f6275c4a1053b648b17b22786dca31bfcc` (only `src/storage/heap_file.c`).

| Path / invariant | Owner | Required verification | Evidence | Result | Remaining |
| --- | --- | --- | --- | --- | --- |
| `heap_midxkey_attr_extra_size ()` (new): absent attr → default length, present → OOS length | R1, R2 | Same present/absent decision as `heap_midxkey_get_value ()` | Source L3; P1, P4b–P7 | Pass | — |
| `heap_attrinfo_generate_key ()` estimate: header (`num_values` / `attr_index_start+1`), `heap_locate_last_attrepr ()` lookup | R1, R2 | Estimate ≥ bytes written by `heap_midxkey_key_generate ()` | Source L3; P1–P8 index builds | Pass | — |
| `heap_attrvalue_get_key ()` estimate: header (`n_atts` / `attr_index_start+1`), default length | R1, R2 | Estimate ≥ bytes written by `heap_midxkey_key_get ()` | Source L3; P1–P8 UPDATE/DELETE, P7 FK cascade | Pass | — |
| `heap_midxkey_key_get ()` / `heap_midxkey_key_generate ()`: `or_init (buf, size)` | R2 | Size equals real capacity; no release behaviour change | Source L3 (15 callers; or_put debug-only asserts) | Pass | — |
| **Shared Q1**: key bytes ≤ `MAX (midxkey_size, DBVAL_BUFSIZE)` for any reachable state | R1 (opus) and R2 (sonnet), independent | Disproof attempts: compression, CHAR padding, domain change, NUMERIC, alignment, function index, NULLs | Both: no reachable violation (L3); coordinator probes L5 | Pass | — |
| Buffer ownership (alloc / free / `need_clear`) | R1, R2 | Unchanged condition | Source L3 | Pass | — |
| Integer overflow of `midxkey_size` | R1 | Bounded sums | Source L2 | Pre-existing risk R1-C1 | Optional follow-up |
| Concurrency | R2 | Shared state / per-thread `attr_info` | Source L3 | N/A (no shared mutable state) | — |
| Recovery | R2 | Log / page format | Source L3 | N/A (no log or layout change) | — |
| HA | R2 | Replication format | Source L3 | N/A (key encoding unchanged) | — |
| TC #4418 (`sql/_13_issues/_26_2h/cbrd_28255`) | R3 | Exercises fixed paths; deterministic answer; fails on base | Source review + LZ4 size check; CI test_sql pass on head | Ready | Optional S1/S2 |
| TC #5114 (`shell/_06_issues/_26_2h/cbrd_28255`) | R3 | Conventions; checkdb; parallel build | Source review, shellcheck; CI test_shell pass on head | Ready | Optional S1/S3/S4 |

Missing checks: local base negative control (not run); release/CS local probes (covered by CI and the PR author's runs only); backport notes not reviewed.
