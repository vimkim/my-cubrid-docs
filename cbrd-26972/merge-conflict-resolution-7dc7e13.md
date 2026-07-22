# PR #7382 merge conflict resolution report

## Report metadata

- PR: [CUBRID/cubrid#7382](https://github.com/CUBRID/cubrid/pull/7382)
- PR branch: `CBRD-26972-oos-show-heap-oos`
- Target branch: `origin/feat/oos`
- Merge commit: `7dc7e13833d7687575b5f5d5c3b2f09ada66a548`
- PR-side parent: `f5794fb4a40d82f630c9fc8ad16e23623c6a2100`
- Target-side parent: `4468c18f2b4a99ace039779d691af7614a0517ac`
- Merge base: `7d73eb765e3fc5a29dca3614b076bd95805d41b2`
- Resolution date: 2026-07-22

## Summary

PR #7382 had diverged from `origin/feat/oos`: the PR side contained 13 unique commits and the target side contained 8 unique commits. Merging the freshly fetched target produced one content conflict, in `src/storage/heap_oos.cpp`. Other files changed by both branches, including `src/storage/heap_file.c` and `src/storage/heap_file.h`, merged automatically.

The sole conflict was not a disagreement about OOS behavior. Both branches had inserted required headers at the same two positions in the include block:

| Header | Side | Why the final file needs it |
|---|---|---|
| `dbtype.h` | PR #7382 | `heap_oos_next_scan()` constructs SHOW result values with `db_make_*` APIs. |
| `heap_show_scan_context.hpp` | PR #7382 | `heap_oos_next_scan()` consumes `HEAP_SHOW_SCAN_CTX`. |
| `deduplicate_key.h` | `feat/oos` | The recdes-locality code checks `IS_DEDUPLICATE_KEY_ATTR_ID`. |
| `log_impl.h` | `feat/oos` | OOS insert publication reset uses `LOG_TDES` and `LOG_FIND_TDES`. |

Choosing either Git side wholesale would therefore have dropped dependencies required by the other feature. The resolution retained all four headers in the normal project include order.

## Conflict details

Git's remerge diff reconstructs the conflict as two adjacent include collisions:

```diff
 #include "heap_oos.hpp"

-<<<<<<< PR side
 #include "dbtype.h"
-=======
 #include "deduplicate_key.h"
->>>>>>> feat/oos
 #include "error_code.h"
 #include "error_manager.h"
 #include "file_manager.h"
 #include "heap_file.h"
-<<<<<<< PR side
 #include "heap_show_scan_context.hpp"
-=======
 #include "log_impl.h"
->>>>>>> feat/oos
 #include "object_representation.h"
```

The common ancestor had none of these four lines at the conflicting anchors. PR #7382 added the SHOW OOS scan dependencies, while target commit `4468c18f2` (`[CBRD-27006] Improve OOS recdes locality (#7391)`) added the deduplication and transaction-log dependencies. Because both changes used the same neighboring lines as insertion anchors, Git could not infer that they were additive.

The resolved block is:

```cpp
#include "heap_oos.hpp"

#include "dbtype.h"
#include "deduplicate_key.h"
#include "error_code.h"
#include "error_manager.h"
#include "file_manager.h"
#include "heap_file.h"
#include "heap_show_scan_context.hpp"
#include "log_impl.h"
#include "object_representation.h"
```

The rest of the upstream include additions, such as `porting.h` and the unit-test-only `<atomic>`, merged automatically. `memory_wrapper.hpp` remained the final include as required by the CUBRID source convention.

## Resolution procedure

1. Fetched the current `origin/feat/oos` tip and confirmed the branch divergence.
2. Previewed the three-way merge and identified `src/storage/heap_oos.cpp` as the only true textual conflict.
3. Performed the merge and resolved both conflict hunks additively.
4. Confirmed there were no unmerged index entries or remaining conflict markers.
5. Ran the whitespace/error check on the staged merge.
6. Built and tested the combined tree before creating the merge commit.
7. Created merge commit `7dc7e13` with both original tips as parents and pushed it to the PR branch.
8. Confirmed that GitHub recalculated PR #7382 as `MERGEABLE`.

No OOS storage semantics were selected or rewritten during resolution. The PR's standalone `SHOW HEAP OOS` diagnostics remained intact, and the target branch's grouped OOS read/insert locality and publication-state work remained intact.

## Verification

The merged tree passed the following local gates:

- Debug build completed successfully for the standalone, client, and server targets.
- The CTest run recorded 24 of 24 test entries as passed.
- The upstream `test_oos_server` suite passed all 33 tests, including the new recdes-locality and OOS publication-state coverage.
- The PR-specific `test_oos_sql_show` suite passed all four tests:
  - `HeapWithoutOosReportsZeroStats`
  - `HeapWithOosReportsPositiveStats`
  - `ShowAllHeapOosRunsForNonPartitionedClass`
  - `ShowAllHeapOosReportsPartitionRows`
- `git diff --cached --check` reported no whitespace errors before commit.
- After push, the local PR branch and its tracked remote had zero commit divergence.

Immediately after the push, GitHub reported `mergeable: MERGEABLE`. The overall merge-state field was temporarily `UNSTABLE` because the newly triggered checks were still queued or running, not because a merge conflict remained.

## Commit hygiene note

A local, untracked pre-commit formatter attempted to rewrite portions of upstream files, including a roughly 2,400-line formatting-only delta in `src/storage/heap_file.c`. Those formatter-generated working-tree changes were discarded before committing because they were unrelated to the conflict and would have made PR #7382 differ unnecessarily from its target branch. The pushed merge commit contains the tested merge result and the minimal additive conflict resolution only.

## Conclusion

The conflict was caused by concurrent include-block edits, not incompatible OOS designs. Retaining both branches' required dependencies was the minimal and semantically correct resolution. Merge commit `7dc7e13` preserves the SHOW OOS diagnostics and the latest `feat/oos` recdes-locality work, passes the complete local CTest gate, and leaves PR #7382 mergeable.
