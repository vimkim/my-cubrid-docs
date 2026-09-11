Coexistence check, not a campaign attempt
=========================================

Purpose: run the new case in one invocation together with all ten existing cases of the
same issue bucket, to show that it neither breaks its neighbours nor depends on running
alone. It has no manifest, no attempt record and no matrix row, deliberately: it adds no
coverage, and the campaign's per-attempt taxonomy has nothing to say about a mixed
invocation. No ticket criterion asked for it either; it was run as the verification step
of this session's implementation workflow, and it is recorded here rather than claimed as
coverage.

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
