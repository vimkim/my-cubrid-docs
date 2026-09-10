# PR #7600 — Standards review

Reviewed 2026-09-09: `f4299ac0cd777a2a964c1f197ae5ebf9841a4936...988a4d2fa258222aef792a2a6afde9641b8c5228`, plus the uncommitted vacuum test. Independent Standards reviewer; repository guidance overrides the code-review skill's smell heuristics. Tooling-enforced formatting is excluded from substantive findings.

**0 substantive hard violations; 2 nonblocking judgement calls.**

1. **Possible Speculative Generality: obsolete two-pass transformation path.** [heap_file.c:12963](https://github.com/CUBRID/cubrid/blob/988a4d2fa258222aef792a2a6afde9641b8c5228/src/storage/heap_file.c#L12963) describes the second pass of a two-pass partitioned write; line 12973 passes `increments_already_applied=true`. Its sole production caller is the owner branch at [locator_sr.c:7563](https://github.com/CUBRID/cubrid/blob/988a4d2fa258222aef792a2a6afde9641b8c5228/src/transaction/locator_sr.c#L7563). Current public copy-area callers pass a NULL owner; partitioned writes use the internal first-pass path at lines 7791–7794. The rebuild API and increment-suppression state therefore have no active production consumer. Consider removing that branch/API and state while preserving the duplicate-key probe and normal owner-aware transform. This follows the skill's heuristic to remove abstraction without a current need.

2. **Possible Duplicated Code: repeated reference-routing fixture.** [test_oos_sql_show.cpp:1315](https://github.com/CUBRID/cubrid/blob/988a4d2fa258222aef792a2a6afde9641b8c5228/unit_tests/oos/sql/test_oos_sql_show.cpp#L1315), lines 1393 and 1473 repeat record construction, probe, record-based route, OID/HFID comparison, and teardown: `heap_attrinfo_transform_to_disk_probe_oos ... partition_prune_insert ... EXPECT_TRUE (OID_EQ ...)`. Consider a shared reference-route helper, retaining case-specific source-preservation assertions. This follows the skill's duplication heuristic; it is not a correctness blocker.

The SQL tests meaningfully check physical OOS ownership, payload readback, and rollback/error behavior. The uncommitted vacuum test adds a committed-delete witness before checking original OOS content after abort. It exercises heap/OOS APIs directly, not partition routing. See [fresh execution results](verification.md).

Sources: supplied root guidance, `src/AGENTS.md`, query/storage/transaction guidance, `unit_tests/AGENTS.md`, and the `code-review` smell baseline. The CCI revision mismatch is assessed separately in [the worktree review](verification.md#worktree-inventory); it is not a formatting finding.
