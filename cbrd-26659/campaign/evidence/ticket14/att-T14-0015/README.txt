Negative control: checker validation, not a campaign attempt
============================================================

This directory holds the run of the deliberately wrong copy of the case, produced by
cases/make_negative_control.sh. It has no attempt record and no replay-bundle index, and
it appears in no manifest and no matrix row, deliberately: the campaign specification
places negative controls in checker validation --

    "For each distinct checking mechanism there is a controlled wrong-result or failure
     example that the checker must detect. These negative controls belong to checker
     validation and are never promoted as regression answers."

-- so recording it as an attempt with outcome FAIL would put a fabricated failure into
the coverage history of a requirement, where a later reader could mistake it for an
engine finding. Ticket 13 treated its public negative control the same way. What makes it
auditable is here instead: the generator is committed beside the case, its two mutations
are documented in its header and verified at generation time, and this directory holds
the result file, the summary, the journals and the case's own outcome file.

What it proves (summary.txt, oos_dur01_negative_control.result):

    Total Case 1, Execution 1, Success 0, Fail 1
    16 assertions executed, 15 OK, 1 NOK, 1 SKIP
    case_outcome = FAIL|1 assertion(s) failed

    oos_dur01_negative_control-12 : NOK recovered_value_id2_multi_chunk_oos :
      expected [OOSROW|2|05787a81...|16283|130264|16288|1]
      got      [OOSROW|2|02b6cc6d...|16284|130272|16292|0]

Exactly one assertion failed, and it failed on every axis the whole-value oracle uses at
once: the MD5 digest, the octet length, the bit length, the disk size and the SQL
equality flag. The other fifteen still passed, so the control is narrow rather than a
case that fails for any reason.

It demonstrates two more things:

  * the launcher exited 0 while reporting Total Fail Case:1, the same trap ticket 13
    found on the SQL seam. Tooling must read
    result/shell/current_runtime_logs/test_status.data, never $?.

  * the failure-evidence path works. Because the case sets SKIP_CHECK_RECOVERY_ERROR=TRUE
    on its post-crash utilities, CTP's own installation-snapshot channel is off, so the
    case preserves its own: the first failed assertion captured processes, journals,
    server status and the CUBRID logs, and cleanup copied the recovered database and the
    server logs aside before deleting them. See preserved-failure-evidence.txt; the
    images themselves (259 MiB) stay in the bundle under
    /home/vimkim/.cub/campaign/cbrd-26659/ticket14/attempts/att-T14-0015/.

The second checking mechanism this case relies on -- the acknowledgement parser that
turns csql output into the affected-row and error counts assert_txn judges a committed
transaction by -- has its own controlled failure example in
tools/checker_validation_journal.sh, whose output is checker-validation-journal.txt.
