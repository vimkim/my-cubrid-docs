# Why PR7925 depends on PR7927 now

Date: 2026-10-08. PR7925: [CBRD-27424](https://github.com/CUBRID/cubrid/pull/7925), head `b755678cd9a3ab465215228d5664f7f1edf24846`, targeting `feature/oos-merge`. Compared with feature tip `fb567a629cdb390fff920542173fa36f454c74a0`, independent PR7925 implementation `1c660d22e4340ee707336ad08c8b4bf4b69744de`, and PR7927 implementation `f3144ab4b72fc2bf73f115c9da1cf193c756457a`.

The original standalone workspace OOS omission **can be fixed directly on `feature/oos-merge` without PR7927**. PR7925 previously did that. The current dependency comes from adopting PR7927's shared preparation/finalization and buffer ownership interface, and from the chosen separation of the two issues. It is not an inherent requirement that the entire other PR be merged before any workspace fix can work.

## The original implementation already handled destination ordering

At independent revision `1c660d22e`, INSERT calls `partition_prune_insert` with the original workspace record, receives `real_class_oid`/`real_hfid`, and only then invokes `locator_oos_demote_workspace_record` with `real_class_oid`. Therefore a claim that PR7927 first makes the destination available would be incorrect. [Pruning at line 5071](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L5071-L5072), [conversion at line 5146](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L5144-L5155).

The helper reads the inline workspace values through existing heap attrinfo, reuses `locator_allocate_copy_area_by_attr_info` with `LOB_FLAG_EXCLUDE_LOB`, retains the input when no demotion is selected, and restores workspace CHN after conversion. UPDATE prunes before conversion; a partition move forwards workspace provenance into the destination INSERT. [Original helper](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L4946-L4995), [UPDATE ordering](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L6084-L6152).

`git diff fb567a629 1c660d22e -- src/storage/heap_file.c src/query/partition.c` is empty. The independent fix reused the feature branch's transformer and partition code. Its eight-file net diff adds workspace provenance/conversion and tests; it does not require the later pending-record APIs.

Historical runtime evidence supports that this was an actual working implementation, not only a possible design. The retained exact-head review records successful Debug/Release builds and 37/37 CTests, including 13 loader/workspace and 21 comparison cases. The retained Debug CTest log explicitly passes both `PartitionsOwnSeparateOosFiles` and `PartitionMovementTransfersOwnership`. These are previous runs inspected for this analysis, not reruns, and do not prove all general SQL partition cases are fixed. [Exact-head review](code_review_1c660d22e_codex.md), [retained Debug log](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/.scratch/pr7925-restore/restored-full-ctest.log:1279).

## PR7927 fixes a different, broader ownership problem

On `fb567a629`, the ordinary attrinfo path constructs a disk record before calling `locator_insert_force`. That transformation already inserts OOS values using `attr_info->class_oid`; partition selection inside locator happens later. For a parent-targeted SQL write, this can write chains to the parent's OOS file before the actual child is known. The old workspace helper avoided that ordering for its inline input, but did not change ordinary SQL preparation. [Pre-force conversion and force call](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7698-L7713), [eager insertion](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L13813-L13821), [insertion under attrinfo class](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L13224-L13225).

PR7927 retains selected serialized values in `heap_pending_record` until routing finishes. Partition/key readers receive that owner to read pending values; finalization writes chains under the selected destination and replaces temporary references with durable OOS stubs. Already serialized received records are read through attrinfo and prepared without repeating external LOB copy effects. The previous workspace helper simply skipped records already containing OOS; it was not a general received-record ownership repair. [Old skip](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L4954-L4957), [retention versus immediate insertion](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/storage/heap_file.c#L13935-L13965), [received preparation](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/storage/heap_file.c#L13314-L13348), [destination finalization](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/storage/heap_oos.cpp#L120-L240).

The normative requirement is correct values and OOS file association with the heap, with OOS/heap changes inside the appropriate logged rollback scope. The normative specification does not prescribe PR7927, its class names, or its merge order. [OOS specification, sections 2–4](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md).

## Why the current PR7925 uses the prerequisite

At `b755678cd`, the original workspace helper and its separately freed copyarea have been removed. `locator_finalize_oos_record` accepts either copyarea or explicit workspace input, calls `heap_prepare_oos_record` into its existing force-local `heap_pending_record received`, and calls `heap_oos_finalize_record`. Those APIs and owner are absent from `fb567a629` and `1c660d22e`. Removing PR7927 while keeping this implementation would leave required interfaces missing. [Current shared finalizer and local owner](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/transaction/locator_sr.c#L4947-L5027).

This is a concrete integration simplification. Leaving both the old eager helper and the new received-record preparation active was previously tested in combined baseline `b59f243fd0f30bb94344558ffa1755c37c43d2d4`: 66/70 selected cases passed, but four workspace UPDATE utility cases failed exact OOS chunk-count assertions while their value/reference predicates passed. Removing the redundant converter in `9ba5e42ad6dfaa74cc9062f6fe55a459ba088924` passed all four failures plus four controls. These failures belong to the combined implementation, **not the independent `1c660d22e` implementation**, and do not prove that the original workspace fix inherently needed PR7927. [Combined baseline and repair evidence](/home/vimkim/gh/my-cubrid-docs/.scratch/pr7925-review-simplification/orchestration.md:196).

The selected ownership-cleanup specification explicitly says to wait for CBRD-27089's accepted interface and integrate its implementation before final shared partition acceptance. That is the recorded scope/integration decision: CBRD-27089 owns general partition selection and destination/OOS ownership, while CBRD-27424 adapts workspace writes to that boundary. It prevents solving or copying the broader issue into the workspace PR. [Implementation decisions, lines 92–99](/home/vimkim/gh/my-cubrid-docs/.scratch/pr7925-review-simplification/spec.md:92).

Source comparison verifies that current `heap_file.c`, `heap_oos.cpp`, `heap_pending_record.*`, `heap_oos_value_ref.*`, `partition.c`, and `query_executor.c` are identical to PR7927 `f3144ab4b`. The task-only diff against that prerequisite is eight files, 967 insertions and 31 deletions. Thus current PR7925 already contains the prerequisite implementation. It can run before an external PR merge; merging PR7927 first is the clean shared-branch integration order, not a runtime requirement to observe the external merge event.

## Choices and their costs

| Choice | What it solves | Consequence |
| --- | --- | --- |
| Retain an independent fix based on `1c660d22e` | Original SA loader/workspace omission, including its destination-aware workspace paths | Technically feasible and previously tested. Keep the existing broader SQL ownership defect separate, then reconcile workspace conversion when PR7927 lands. |
| Keep the current PR7925 architecture and integrate PR7927 first | Workspace fix using one accepted received owner and finalization contract, together with general destination ownership repair | Small workspace-specific production diff and separate review ownership; must verify against the actual prerequisite merge/squash result. |
| Extract only needed prerequisite machinery into an independent workspace PR | Potentially the current behavior without the entire PR7927 history | Requires defining and verifying a new dependency subset, preserving readers, owners, finalization and storage/transport guards. It duplicates or relocates CBRD-27089 work and changes the recorded scope; it is not proven necessary or preferable by the evidence here. |

The justified statement is: **“Merge PR7927 first if we retain the current shared-owner implementation and agreed issue separation.”** The stronger statement **“CBRD-27424 cannot be solved directly on `feature/oos-merge`”** is contradicted by the original source and its retained focused verification.

## Verification and limits

Read-only source/history comparisons, live PR/JIRA lookups, normative-context read, environment validation, and retained-evidence inspection were performed. The live `git ls-remote origin refs/heads/feature/oos-merge` result remains `fb567a629`; both PRs are open. No build, DB test, engine mutation, or external publication was performed for this investigation. Work-tracker item: 307. The unrelated dirty `cubrid-cci` submodule was preserved. Normative context fingerprint: `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`.

The decisive source comparisons can be repeated in the engine worktree:

```sh
git diff fb567a629 1c660d22e -- src/storage/heap_file.c src/query/partition.c
git diff f3144ab4b b755678cd -- src/storage/heap_file.c src/storage/heap_oos.cpp src/storage/heap_pending_record.cpp src/storage/heap_pending_record.hpp src/storage/heap_oos_value_ref.cpp src/storage/heap_oos_value_ref.hpp src/query/partition.c src/query/query_executor.c
git diff --stat f3144ab4b b755678cd
```

The first two commands return empty diffs; the third returns the eight-file workspace-specific delta described above. Required preparation/finalization APIs were also checked directly in all three revisions: absent in the feature baseline and independent fix, present in current HEAD.
