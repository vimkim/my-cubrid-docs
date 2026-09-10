# 9. Answers and teach-back rubric

Attempt the questions before reading this chapter. These are model answers you can compare with your own; explaining the dependency in your own words matters more than reproducing a phrase.

## Chapter 1

1. `id=10` belongs to p1 because p0's upper bound is exclusive. Moving 1 to 20 changes the destination from p0 to p1.
2. Class identity selects metadata and permissions; HFID selects the heap storage. A lookup connects them.
3. No. A probe is serialized bytes in memory. A normal OOS transform may already have written chains even though the heap row has not yet been inserted.
4. Root connects to two child classes; p0 connects to a heap page and row slot; p1 connects to its own heap. The root is not one page enclosing both heaps. [C-004] [C-006] [C-008]

## Chapter 2

1. The stub's physical OID may still reach the right bytes even if the OOS file belongs to the wrong heap.
2. In p0's heap header `oos_vfid`, which identifies p0's associated OOS file.
3. Inspect the return contract and actual branches at the pinned revision, then reproduce that path if making a runtime claim. True-with-null and false-on-error differ here.
4. The heap record is the row representation, the chunk record is one physical piece of an OOS value, and a chain is the sequence of chunks comprising the complete serialized value. [C-009] [C-011] [C-012]

## Chapter 3

1. Two transforms, one early pruning call and another in the lower INSERT locator for the normal partitioned path.
2. Retain the inline image and continue to the lower locator; skip the additional final transform.
3. The image has served routing. Clearing its pointer prevents reuse and avoids retaining two copy areas unnecessarily; prepared attribute state is separate.
4. p1's associated OOS file should receive the new chain.
5. Internal suppression is computed from pointer presence, so null selects normal behavior despite the wrapper's name. [C-015] [C-016] [C-017]

## Chapter 4

1. Verdict true; `has_oos=false`; selection false. Final mode changes selection and flag.
2. Plan selection, payload replacement accounting and `has_oos=true` would still execute.
3. The local set survives retries within a call. A second call needs a new set seeded from the successful probe's history.
4. The `HEAP_ATTRVALUE` inside the surviving attribute cache retains the state and updated DB_VALUE.
5. Retrying buffer output should not publish another chain for the same prepared value. [C-020] [C-021] [C-022] [C-024] [C-025]

## Chapter 5

1. The non-null pointer selects suppression; duplicate lookup does not need to know whether an eventual write would demote.
2. The attribute cache and its DB_VALUE changes survive; probe bytes do not.
3. Database records and transaction logs have a separate lifetime from a process memory buffer.
4. Final routing/representation handling, child locks, scan-cache selection and the move decision remain there.
5. Measure serialization CPU, temporary peak memory and repeat routing cost as logical value sizes grow. [C-026] [C-027] [C-028]

## Chapter 6

Use the coverage table to identify the file and old/new interval of each hunk. Explain the pointer arguments before interpreting a wrapper name. For the large locator hunk, trace both the successful early-prune branch and the no-demotion branch. For the test, explain first-tuple positioning before the loop and why all three `saw_*` checks matter. Source listings and C-101 through C-130 supply the exact answer key.

## Chapter 7

1. A result set that omitted p1 could pass all remaining per-row checks without proving p1 was inspected.
2. It reaches the forced loop while avoiding the ordinary size gate; this distinguishes the second commit's missing suppression case.
3. A value may have many chunks and a row may have many OOS-backed attributes.
4. Begin from fresh p0 ownership, UPDATE the partition key to p1, then verify the logical row is in p1 and the new chain is associated with p1. Separate old-version retention from leaks; in SERVER_MODE account for vacuum and older snapshots before expecting old counts to vanish. [C-003] [C-032]

## Chapter 8: counterfactual review

| Edit | Consequence to investigate |
|---|---|
| 1. Remove `continue` | Probe can select/write forced OOS values before routing. |
| 2. Null probe pointer | Ordinary transform can publish under the original class. |
| 3. Original class as final owner | Correct routing can still be paired with wrong OOS ownership, especially cross-partition UPDATE. |
| 4. Final increment flag false | A pending fixed increment can run twice. |
| 5. Always do second pass | Unnecessary serialization/routing on no-demotion writes; correctness requires rechecking the side-effect protocol. |
| 6. Free attribute cache | Final pass loses values/metadata and may access freed state. |
| 7. Ordinary duplicate probe | Candidate images can create chains that no inserted row owns. |
| 8. Remove lower pruning | Early outputs do not replace final class/HFID, representation and locking responsibilities. |
| 9. Equality-only test | Correct bytes can mask wrong ownership. |
| 10. True implies existing file | The documented true-with-null result is misinterpreted. |

These answers derive from the mode, writer and routing traces [C-008] [C-012] [C-016] [C-017] [C-024] [C-026]. A counterfactual is a prediction; no mutated engine was built for these exercises.

## A practical rubric

Score each of these five areas from 0 to 2: storage identities, old/new flow, side-effect lifetime, every-hunk explanation, and test evidence limits. Zero means recognition without explanation; one means you can explain with the source open; two means you can predict a changed input or missing line and then locate the evidence. A ten-point score requires explaining why SELECT success and a passing SA test have limited scope. Mark your own results in the progress file.
