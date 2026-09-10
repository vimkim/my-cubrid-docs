# 8. Explain the design, then challenge it

## What this patch buys

The patch reuses the existing serializer and partition reader. The probe provides the byte representation that routing already understands, and an owner override lets final serialization keep using the original attribute metadata while selecting the destination heap. Its small interface additions connect query execution, locator orchestration and storage preparation. [C-015] [C-016]

The cost is a protocol spread across several parameters and mutable state. A nullable output pointer selects a mode; a wrapper silently assumes prior increment application; a LOB state enum carries history across calls. A future caller must know those preconditions. An explicit mode or prepared-write object could express them more directly, but adopting one would require reviewing all callers and retry behavior. That is a design option, not part of this PR. [C-033]

## An end-to-end explanation you should be able to give

For a root-targeted INSERT of `id=1`, the executor prepares attribute values and asks the locator to write them. The locator needs a record image before it can find p0. The probe produces inline bytes without OOS selection and reports that the forced value will need OOS. Pruning chooses p0 from the logical key. The locator discards probe memory but retains prepared attribute state. Final transformation uses p0's class OID for OOS-file lookup, creates the chain and puts its stub in the final image. The ordinary lower locator routes that image, locks and selects the child context, and stores the heap row. The regression checks value equality and root/p0/p1 file ownership. [C-001] [C-003] [C-016] [C-017]

For UPDATE, start with the existing child's old row, apply the new values during preparation and select the destination from the new record. If the partition key changes to 20, final OOS ownership should be p1; the lower update path can move the row. Old versions and their values remain subject to the existing MVCC/cleanup rules. [C-017] [C-027]

## Review exercises: change one line

For each hypothetical edit, identify the changed invariant, the expected observation and a test that would expose it.

1. Remove `continue` from the forced-outline suppression branch.
2. Pass null instead of `&would_demote_oos` in the partitioned probe call.
3. Pass `&class_oid` instead of `&pruned_class_oid` to the final allocator.
4. Change the final wrapper's last argument from true to false.
5. Delete `would_demote_oos` from the `copyarea != NULL && would_demote_oos` condition.
6. Free `attr_info` along with the probe copy area.
7. Replace the duplicate-key helper's probe with an ordinary transform.
8. Remove the lower locator's partition-pruning block because early pruning already ran.
9. Assert only SELECT equality and remove SHOW ownership assertions.
10. Treat a true return from `heap_oos_find_vfid(...,false)` as proof that an OOS file exists.

## Evidence boundaries

The source explanation is pinned to head `b871ea386d2c5419b7abae07dda58b9b7f36377a`, base `2940b1cfbc3c2d4d0fac3f9244a960350debd380`. The six diff files match the head. Unrelated working-tree and submodule changes are excluded. The hunk appendix includes every addition and deletion, and its coverage index is generated from the captured Git diff. [C-029]

The two substantive open boundaries are the current-server behavior of inconsistent ownership [C-013] and runtime coverage beyond the selected standalone regression [C-032]. Neither prevents understanding how the patch is constructed. Both limit operational claims such as “every possible vacuum failure is fixed” or “all side-effect paths were executed.”

**READY WITHIN DECLARED SCOPE.** The book supports the PR mechanism and the recorded regression. C-013 and C-032 remain explicit limits on broader correctness claims.

## Chapter checkpoint

Give a five-minute explanation using only the diagrams. Then open chapter 6 and explain each hunk without its commentary. Record which questions remain in `learning-progress.md`; completion of this book does not automatically mark your mastery complete.
