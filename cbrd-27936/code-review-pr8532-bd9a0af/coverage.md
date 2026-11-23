# Coverage: PR #8532 @ `bd9a0afc7b`

This table covers the comparison from base `505c07dde1` to head `bd9a0afc7b`. One path changed: `src/transaction/log_manager.c`.

| Area / invariant | Path(s) | Owner | Evidence | Result | Remaining |
|---|---|---|---|---|---|
| Local commit: the saved-space release moved after the commit-log append | `log_commit_local` local branch | R1, R2, coordinator | SF1-SF4 (level 3, both reviewers); runtime replay at level 5 (head 3/3 pass, base 2/2 fail); TLA+ on the sync commit plus the patch (`commit-window-saved-space` no longer applies) | Safe; fixes the target defect | none |
| 2PC branch (`is_local_tran == false`) | `log_commit_local` else-branch; `log_2pc.c` callers | R1 | SF8 (level 2-3) | Behavior unchanged; comment wording N-1 | not executed (optional) |
| HA (repl and commit append, applier) | `log_manager.c:4821-4844` | R1 | SF9 (level 3) | Not affected | none |
| Every caller of `log_commit_local` | `log_manager.c:5647`; `log_2pc.c:600`, `760`, `2585` | R1 | Caller table (level 2-3) | Covered | none |
| `spage_free_saved_spaces` semantics, locks, ownership | `slotted_page.c:380-770`; `log_tran_table.c` | R2 | SF5, SF6 (level 2-3) | Safe | none |
| Code between the old and new release points | `log_cleanup_modified_class_list`; commit append | R2 | SF7 (level 3) | No dependency on the release | none |
| Concurrency during the longer reservation | `slotted_page.c:4611`; heap and bestspace paths | R2 | Section 2 of the R2 report (level 2-3) | Space-efficiency effect only | not measured |
| Performance | same as above | R2 | Source and model only | Small window (prior-node allocation plus mutex) | not measured (optional) |
| Abort path and `tail_lsa == NULL` branch | `log_abort_local` | R1, R2 | SF9 (R2), section 5 of R1 | Unchanged and safe | none |
| Shared question Q1 | as above | R1 (opus), R2 (sonnet) | Independent answers: both "no" | Agreed; R1 corrected R2 on 2PC async | none |
| Style and standards | diff | coordinator | GNU indent markers not needed (C-only code); CI code-style and cppcheck pass; comment lines are 120 characters or fewer | Pass; N-1 wording | none |
| Static analysis | diff | coordinator | `cubrid-static-check` exit 2 (no compile_commands.json at run time) | Not run | optional |

No domain is marked not applicable. The model abstraction (DELETE undo only) and the 2PC runtime are recorded as limits in the report.
