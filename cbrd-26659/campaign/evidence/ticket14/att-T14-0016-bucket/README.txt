Coexistence check, not a campaign attempt
=========================================

Purpose: run the new case in one invocation together with all ten existing cases of the
same issue bucket, to show that it neither breaks its neighbours nor depends on running
alone. It has no manifest, no attempt record and no matrix row, deliberately: it adds no
coverage, and the campaign's per-attempt taxonomy has nothing to say about a mixed
invocation. No ticket criterion asked for it either; it was run as the verification step
of this session's implementation workflow, and it is recorded here rather than claimed as
coverage.

WHICH VERSION OF THE CASE THIS EXERCISED, and why it was not re-run. This invocation ran
the case as committed at revision 3; the committed case is revision 7. The whole
difference is in two paths this run never entered, and case-version-delta.diff carries it
so the claim is checkable rather than asserted:

  * the failure-preservation path, guarded by `[ ${nok_count} -gt 0 ]`, which a passing
    run does not reach. It gained preserve_failure_database() in place of two unchecked
    `cp -a … 2>/dev/null` calls.
  * the SHOW HEAP OOS failure classification, reached only when the statement does not
    answer. This run's SHOW HEAP OOS answered, twice, which is recorded in its
    operations.journal.
  * how the answered row's columns are located -- by header name rather than by position.
    This changes which field number is read, not whether a correct row is read: the
    revision-6 runs journalled has_oos=1, chunks=4, sumlen=24444, user_pages=4 and
    oos_page_size=16344, identical to what the by-position code read from the same
    fixture, which is the cross-check that the change is behaviour-preserving on a row
    the engine really produces. Revision 7 then merged the row selector and the column
    lookup into one awk pass; the revision-7 runs journalled the same five values again.

Re-running the bucket would have cost seven minutes and proved nothing the diff does not.
Both changed paths have their own direct evidence: att-T14-0028 exercised the preservation
path and journalled preservation|ok, and tools/checker_validation_classifier.sh exercises
all sixteen classification shapes.

Result (summary.txt):

  Total Case 11, Execution 11, Success 9, Fail 2, Skip 0, 397 s wall time
  cbrd_26659_oos_dur01 : 16 assertions executed, 16 OK, 0 NOK, 1 SKIP, 12 s
                         case_outcome = PASS -- identical to its isolated run att-T14-0013
  install_conf_drift_lines=0, install_databases_drift_lines=0, user_shell_fm_drift_lines=0
  the testcase worktree was left with zero untracked files afterwards

The two failures are in sibling cases and are not attributed to this ticket. The new case
is dispatched last (CTP's discovery uses `find` order and this directory is the newest),
so it had not run when either failed:

  cbrd_26777-1 : NOK Failed to start cubrid manager
      the case needs the CUBRID Manager server, which this pinned install does not start.
      A prerequisite of that case against this install.
  cbrd_27097-16, -17 : NOK
      a registry-related case; not investigated here.

Both failed identically in two earlier runs of the same bucket, and nothing this case
does precedes them in the invocation. Whether they are engine defects, Capability gaps of
the pinned install or stale cases is for the tickets that own those requirements;
recording the observation is all this check claims.
