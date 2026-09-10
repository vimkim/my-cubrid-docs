# PR #7600 Learning Resources

## Knowledge

- [Committed effective-key write journey](lessons/0005-effective-key-write-journey.md)
  Teaching guide grounded in locally inspected commit `213ce80f5`, with exact locator/heap/partition functions. Use for INSERT and moving UPDATE before defaults/increments. The local commit is not assumed publicly accessible.
- [Reviewed source handoff](../design/blocked-handoff-213ce80f5-codex.md)
  Identifies the committed routing source and links to primary-source traces and recorded evidence. Distinguishes supported implementation from unresolved lifecycle and runtime gates.

- [Pinned partition implementation](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3583)
  Primary source inspected locally. `partition_prune_insert` selects the partition and returns its class and heap identifiers. Start here for the write-path meaning of pruning, not the complete query optimizer.
- [Pinned write preparation](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7711)
  Primary source for the conditional inline probe and OOS rebuild. Use after the learner understands partition selection and ownership.
- [Existing source-guided foundations](chapters/01-foundations.md)
  Supporting course material with claim references; use its evidence map to find primary sources, not as independent proof.

## Wisdom (Communities)

- [PR #7600 author and reviewers](https://github.com/CUBRID/cubrid/pull/7600)
  Relevant practitioners for historical intent that source cannot prove. No outreach is authorized; do not present inferred rationale as an author statement.

## Gaps

- [Recorded measurements](../design/ticket06-measurements-b871ea386-codex.md) establish scoped resource savings; runtime acceptance remains unresolved. Do not present earlier absence of measurements or a proven universal speedup as current fact.
- Explicit historical rationale for choosing per-heap ownership over a logical-table shared file.
- Revisit the authoritative OOS context and actual implementation together before teaching OOS-specific invariants.
