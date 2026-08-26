# PR #7630 Page-Latch Resources

## Knowledge

- [Published review report](../PR-7630-report_1185f16_codex.md)
  Authoritative statement of the `REJECT` decision, blocking defect, evidence, and smallest required correction. Use for: review claims and scope.
- [PR #7630 at the exact reviewed commit](https://github.com/CUBRID/cubrid/pull/7630/files/1185f16d7e5f540ffdad4509cbd061ef0535f4df)
  The reviewed implementation baseline. Use for: tracing the new scoped flag and affected structural-page fixes.
- [Storage guidance: page-buffer protocol](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/AGENTS.md#buffer-pool-protocol)
  Establishes the local distinction between logical transaction locks and physical page latches. Use for: canonical terminology.
- [Wait-policy sentinel values](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/transaction/lock_manager.h#L55-L63)
  Defines zero-wait, forced zero-wait, and infinite-wait values. Use for: policy tracing.
- [Unconditional-request demotion](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L2273-L2283)
  Shows when a requested unconditional page latch becomes conditional. Use for: explaining the original zero-wait failure.
- [Page-latch wait and timeout classification](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L7284-L7296)
  Paired with the [classification branches](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L7373-L7425), this separates how long a latch waits from how expiry is classified.
- [Wait-policy override](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L16922-L16949)
  The blocking implementation site. Use for: demonstrating why positive finite values are currently reclassified.
- [Structural-page scopes](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L3233-L3236)
  Volume-header scope, paired with the [sector-table scope](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L3510-L3513). Use for: locating the save/set/fix/restore lifecycle.
- [Separate page-latch timeout parameter](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/base/system_parameter.c#L5308-L5319)
  Shows the independent elapsed page-latch timeout bound. Use for: separating wait-policy classification from elapsed duration.
- [Author's later architecture response](https://github.com/CUBRID/cubrid/pull/7630#issuecomment-5365130299)
  Accepts that `lock_timeout` is conceptually lock-oriented, while arguing that full latch-policy separation is too broad for this PR. Use for: separating architecture scope from the blocker.

## Wisdom (Communities)

- [PR #7630 review discussion](https://github.com/CUBRID/cubrid/pull/7630)
  The real reviewer conversation in which the final explanation must hold up. Use for: testing whether an answer addresses actual objections and scope arguments.
