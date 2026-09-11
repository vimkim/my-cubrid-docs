# CBRD-26659 — Independent review of ticket 14, the private tracer bullet

> Reviewed: 2026-09-11 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (ticket 11); normative context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…` (ticket 12).
> Reviewer: Claude Opus 5 (1M context), in a session that authored none of the artifacts under review and read the author's own review record (§8 and §9 of the ticket 14 report) only after forming the findings below.
> Subject: testcase commit `adbd8b745263800b242cf51415a5fdd6ca42e86b` on base `e9c2d86874b9c08cdd72b120c2ead84f525e15fc`, the evidence under [`evidence/ticket14/`](evidence/ticket14/), and the record [`CBRD-26659-private-tracer-bullet_f4299ac_claude.md`](CBRD-26659-private-tracer-bullet_f4299ac_claude.md).
> Satisfies: the [campaign specification](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) section *Review, sign-off and deferral* — "An independent agent session, never the authoring session, reviews Standards and Spec conformance per repository, validates the negative-control checkers, and audits replay and cleanup evidence before acceptance" — for the private shell repository at this commit. It does **not** discharge ticket 33, which is the whole-campaign acceptance review.

Vocabulary follows the [docs glossary](../../CONTEXT.md).

## Verdict

**All nine of ticket 14's criteria are met. Two specification findings are blocking, both of them overclaims that would propagate into the coverage matrix. Accept the tracer bullet; F1 and F2 must be closed before the four matrix rows stand as written.**

| | |
|---|---|
| Ticket criteria | 9 of 9 met |
| Blocking findings | F1 (activation evidence for the recovery path), F2 (`OOS-REP-07` quoted in truncated form) |
| Non-blocking findings | F3 (replay bundle's expected-versus-actual has no expected side), F4 (no attempt record for two executed runs), F5 (coexistence claim's revision) |
| Follow-up | [ticket 34](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/issues/34-ticket14-review-findings.md) |

**Method and its limits.** Static reading of the committed case, the campaign spec, ticket 12's catalogue and schemas, plus the saved evidence and the two full replay bundles under `/home/vimkim/.cub/campaign/cbrd-26659/ticket14/attempts/`. No CTP invocation and no `cubrid` command were run: other sessions were cycling CUBRID instances on this host under the same UNIX user, and the CTP shell helpers issue an unscoped `pkill cub` twice per invocation. Two consequences worth stating plainly. First, the runs are audited from their recorded evidence and were not reproduced, so this review confirms that the evidence is internally consistent and says what it claims, not that a fresh run reproduces it. Second, F1's supporting observation comes from a log the runs left behind in the pinned install rather than from a run of my own.

## Findings

### F1 — MAJOR, blocking. The recovery path is never shown to have run, and the evidence that would show it is discarded

The matrix records `oos_evidence.status: "proven"` with `gap_kind: "none"` for `OOS-DUR-01` on both configurations. The channel is `SHOW HEAP OOS`, read once after the committed INSERT (the insert path) and once after the restart (post-recovery *state*). Neither observation shows that recovery performed any work. The specification is explicit about exactly this inference:

> Proof of an insert path never certifies an unrelated scan, **recovery** or vacuum path.

Concretely: had every dirty page been flushed before the `kill -9`, this case passes identically on an engine that never logged an OOS operation at all — which is the invariant it cites (OOS-CONTEXT §4 Recovery & Replication Invariants, invariant 1, WAL completeness). The case cannot distinguish "the values survived because redo restored them" from "the values survived because the pages happened to be on disk".

`case-evidence/server_restart.out` does not close the gap. It holds the utility's unconditional banner — "This may take a long time depending on the amount of recovery works to do" — and is **byte-identical to `server_start.out`** in both attempt bundles.

The evidence exists, it is at the seam, and it is free. The pinned engine emits recovery progress at NOTIFICATION severity into `$CUBRID/log/server/<db>_*.err` (`msg/en_US.utf8/cubrid.msg` entries 1128, 1129, 1296–1301, emitted from `src/transaction/log_recovery.c`). The install still carried the negative control's log from 15:07:06 on a **release** build with default configuration:

```
Log recovery is started.
Log recovery: ANALYSIS Phase is started.
Log recovery: REDO Phase is started. Log pages to redo: 2, Log records to redo: 83.
Log recovery: UNDO Phase is started. Log pages to undo: 0, transactions to undo: 0.
Log recovery is finished.
```

So durability here is substantively real — recovery replayed 83 log records. But no ticket 14 artifact records it: the string `redo` appears nowhere in the report, the oracle, either manifest, the matrix or the case. `capture_failure_evidence` copies `${CUBRID}/log` only from `fail()` and the abort paths, so a **passing** run captures nothing, and the only copy sits in the install until the next run overwrites it.

There is no partial value available in ticket 12's `evidence_status` enum (`proven | reused | missing | not-applicable`), so downgrading the row is not the right answer either. Adding the channel is.

**What must change.** After the restart, assert that `$CUBRID/log/server/${db_name}_*.err` carries `Log recovery: REDO Phase is started`, journal the redo page and record counts as an observation, and copy that file into the evidence directory on every run, passing or failing. That turns `OOS-DUR-01` from "the values were there afterwards" into "recovery replayed N records and the values were there afterwards", which is what its citation says. It also yields `transactions to undo: 0` from the engine — an independent confirmation of the operation journal's transaction-state model, in the same artifact.

**Consequences to scope with it.** This is a new checking mechanism, so the specification's rule applies — "For each distinct checking mechanism there is a controlled wrong-result or failure example that the checker must detect" — and the ticket's own generalization applies too: write the controlled failure example for the fix, and show it discriminates by running it against the code it was written to catch. The channel is not in the matrix schema's `channel` enum; `other` with an explicit reference is legal today, and extending the enum with a `recovery-log` value is ticket 12's call, not this one's, if tickets 23 to 32 will all use it.

### F2 — MAJOR, blocking. `OOS-REP-07` is quoted in a truncated form, and the dropped clauses are precisely the ones the case cannot assert

The catalogue statement, in full:

> A value larger than one page's maximum single-chunk payload is stored as a chain of chunk records, **inserted tail first**, and is read back complete and byte-identical; **`total_data_length` excludes every chunk header**.

The oracle's §1 requirements table quotes it as "…is stored as a chain of chunk records and is read back complete and byte-identical." Both emphasised clauses are gone. The matrix then records `OOS-REP-07` as PASS with `gap_kind: "none"` on both configurations, with no note that half the statement is untested. `grep -ri "tail first\|total_data_length"` over the report and all of `evidence/ticket14/` returns nothing.

The second dropped clause is not incidental. `Oos_recs_sumlen` is the observable that would test "`total_data_length` excludes every chunk header", and oracle §3 **deliberately declines to assert it** because the 16-versus-24-byte chunk header divergence (`OOS-REP-05` / CBRD-26950) makes it non-portable at the pin. The one clause the case consciously cannot assert is the one the quotation drops. That is the shape of overclaim this campaign exists to prevent, and it is a Specification-gap-adjacent constraint being silently absorbed into a PASS.

Two smaller things ride along. The catalogue assigns `OOS-REP-07` `seam: "public-sql"`, and a private-shell case now carries its only matrix row. And `OOS-DUR-01`'s own statement already reads "including multi-chunk values", so the multi-chunk row is mandated by the durability requirement regardless of whether `OOS-REP-07` is claimed.

**What must change — one of two.** Either drop the `OOS-REP-07` claim and its two matrix rows, which costs the case nothing; or keep it and record the two untested clauses explicitly on those rows, with the seam question settled in the catalogue. What cannot stand is a `gap_kind: none` PASS against a statement quoted with its hard half removed.

### F3 — MINOR to MAJOR, non-blocking. The replay bundle's "expected versus actual" contains no expected side

`evidence/ticket14/tools/finalize_bundle.sh:48-49` generates the section headed *"assertion names in the order the oracle lists them"* by re-grepping **the actual result file**:

```sh
grep -oE '^'"${name}"'-(([0-9]+ : (OK|NOK))|skip : SKIP) *[a-z_]*' "${bundle}/${name}.result"
```

It never opens `expected-oracle.md`. The specification's replay-bundle item "expected versus actual" therefore holds actual, a tally of actual, and a transformed copy of actual. Two visible symptoms: `[a-z_]*` truncates every assertion name at its first digit or capital (`database_page_size_is_`, `server_crashed_by_kill_`, `recovered_value_id` three times), and the `skip : SKIP` alternative matches nothing the case emits — the case writes `<name>-<n> : SKIP <reason>` — so assertion 17 is absent from that section in all three attempts. The bundle index's note for the item, "The pre-derived oracle's ordered assertion list set against the result file the run produced", is not true of the file it points at.

The negative control's copy additionally carries the generator's static header, "expected: the 17 assertions of expected-oracle.md section 5, in order, each **OK**", which is the inverse of what that run was for.

This does not affect any run's correctness — the case is its own comparator, every assertion names itself and prints expected and actual on failure, and the negative control demonstrates it. It is a defect in the artifact a future reader consults to see what was expected, and it is the ticket's own lesson — a comment stronger than its code — in the evidence layer rather than the case.

### F4 — MINOR, non-blocking. Two executed runs have no attempt record

`att-T14-0028` (the negative control) and `att-T14-0016-bucket` (the coexistence run) carry the campaign's attempt-id naming but no attempt record and no replay-bundle index, so `tools/validate_records.py` never sees them. The specification's outcome taxonomy is stated per executed attempt, and negative-control validation is an item of this very review.

The author's reasoning against fabricating a FAIL attempt for the control is correct — the control must never become a matrix FAIL. But that argues for an attempt record with `kind: "checker-validation"` and no matrix row, which ticket 12's schema already provides through its kind-and-parent-linkage field, not for no record at all. The raw evidence for both runs is present, complete and legible, which is why this is not blocking.

### F5 — MINOR, non-blocking. The coexistence claim needs its qualifier in the summary, not only in the evidence

Ticket 14's Outcome says "Coexistence with all ten sibling cases of the bucket: 11/11 executed, this case unchanged." That invocation exercised revision 3; the committed case is revision 7. `att-T14-0016-bucket/README.txt` discloses this in full, confines the delta to three paths the run never entered, and ships `case-version-delta.diff` so the claim is checkable. The argument holds and re-running would prove little. The one-line summary is what needs the qualifier.

## What was verified and found sound

- **Provenance (criteria 1 and 9).** Branch is exactly `CBRD-26659-oos-testcases-handover`. Base `e9c2d8687` is `origin/develop`'s current tip *and* the merge-base with `HEAD`. One commit `adbd8b745`, no upstream configured for the branch, nothing pushed. The canonical clone `/home/vimkim/cubrid-testcases-private-ex` is still on `develop` at `6eb3b19ba` and clean; the three unrelated private worktrees are untouched.
- **Isolation (criterion 2).** `unshare --user --map-current-user --pid --fork --mount-proc --ipc`. The decoy demonstration carries matched **positive** controls — a decoy started inside the namespace dies to the same sweep, a segment created inside is destroyed by the same `ipcrm` — which is what makes it a demonstration rather than a nothing-happened observation. The stronger evidence is incidental and better: at 15:06 the host carried `cub_master` pid 487844, up since 12:51, while every case journalled `pre_existing_masters=[]`. The case could not see a real neighbour. Decision request 3, making the wrapper a campaign-wide precondition, is well founded.
- **Boundary sizes.** Re-derived independently: 4,036 ≥ max(4,036, 4,012); 4,011 ≤ min(4,036, 4,012) − 1; 16,284 ≥ max(16,284, 16,276). `DISK_SIZE = ALIGN(5 + N, 4)` gives 4,044 / 16,292 / 4,016, matching what both runs read back. The MD5 construction is engine-independent and the hex-form reasoning is correct: `REPEAT('AA', 4036)` is 8,072 hex characters, 4,036 bytes, and CUBRID's `MD5` of a bit string digests the lowercase hex form, which is what the `yes | head | tr | md5sum` pipeline reproduces. **Computing every boundary under both the implemented and the accepted normative accounting and using only sizes where the two agree is the strongest single idea in this case**, and it is what makes the placement assertable rather than merely observed.
- **`Oos_num_recs = 4` is sharper than its comment claims.** It is the only value a monotone demotion gate can produce for this fixture — a gate at ≤ 4,011 gives 5, one above 4,036 gives 2 — so the assertion pins `id = 3`'s inline placement as well, which is never asserted directly.
- **The three-outcome capability gate.** `classify_oos_output` returns 0 answered / 1 parser lacks the statement / 2 anything else, with 2 as the conservative default, on the correct reasoning that a 1 is a SKIP, carries no NOK, passes the case and leaves `activation_observed` at 0. The generalization to every capability gate in tickets 23 to 32 is right.
- **`oos_field`.** One awk pass; the header that supplies a column position and the row that supplies the value are the same header and the same row; columns located by name, not position; the single-quoted class name matched literally with `index()` so `ERROR: Unknown class "dba.oos_dur01".` cannot be read as a data row. `shape15-discriminates.txt` runs shape 15 against revision 6's extracted functions and shows it reading `16344`, which is `Oos_page_size`'s slot, where `4` is correct. **The control is demonstrated against the code it was written to catch**, which is the right standard and is not common practice.
- **Negative control (criterion 6).** Genuinely fails: assertion 12 reports NOK with all three axes diverging at once (MD5, octet length, SQL equality flag) and the case fails, `case_outcome=FAIL`. Non-discovery is demonstrated by running CTP's own `Dispatch.getAllTestCaseScripts` rule over the whole issue bucket, against 272 precedent helper scripts that live inside a `cases/` directory and are never selected. A second control, `tools/checker_validation_journal.sh`, covers the acknowledgement parser, which matters because `csql` has been observed exiting 0 while printing a connection error.
- **SKIP semantics (criterion 4).** `skip()` mirrors `write_ok`'s numbering exactly (`CTP/shell/init_path/init.sh:588-594`), so the result file stays contiguously numbered 1 to 17 while line 17 carries neither `OK` nor `NOK`; `skipped.journal` holds it machine-readably; `skip_reason` is populated in `inv-T14-0001`. The case-level outcome written to `<evidence>/case_outcome` is the correct answer to CTP having only two verdicts, and the SKIP branch is reachable rather than lost to a subshell.
- **Failure-evidence preservation.** Every copy step is checked and a failed copy is raised as a further NOK. This matters because the case sets `SKIP_CHECK_RECOVERY_ERROR=TRUE`, which removes CTP's own installation-snapshot channel, making the case's copy the only image a failing run leaves. `att-T14-0028` exercised the path and journalled `preservation|ok`.
- **Records (criterion 8).** Two manifests, two attempt records, two replay-bundle indexes and four matrix rows all validate against ticket 12's schemas under the campaign's own `minischema` evaluator. Timings recorded for ticket 17: 14 s and 18 s case time, 22 s and 23 s invocation.
- **Cleanup and install hygiene.** `install_conf_drift_lines=0`, `install_databases_drift_lines=0` and `user_shell_fm_drift_lines=0` on every attempt, with before-and-after copies retained in the bundles. That is a direct, checked answer to the hazard the ticket itself raises, that CTP rewrites `$CUBRID/conf` from `~/.CUBRID_SHELL_FM` before every case. The worktree is clean and the bucket run reported zero untracked files afterwards.

## On the four places the author's §9 says the review briefs steered

The ticket 14 record's §9 names four places where the authoring session's own six passes were steered or silent, and asks an independent reviewer to look there. Taken in turn, with the reviewer's own conclusion:

1. **The oracle's provenance wording.** The withdrawal is correctly scoped and should stand. "Justified before the engine is consulted" is a claim about the justification's *source*, and the justification here is arithmetic over ticket 11's constants plus two independent digest computations, which survives. The ordering claim does not survive, and it is withdrawn in the oracle, in `probes/README.txt` and in the report. The stated remedy — probe format on a fixture that is not the case's fixture — is the right one and should carry to tickets 18 to 32.
2. **`proven` rather than `reused`.** The word is defensible for what the applicability note actually describes: same invocation, same session, same fixture, insert-side demotion and chain survival. It is **not** defensible as the status on a Durability row whose recovery path is unevidenced. The remedy is F1's added channel, not a downgrade of the word — and ticket 12's enum has no partial value that a downgrade could honestly use.
3. **No attempt record for the negative control and the coexistence run.** F4. The reasoning against a fabricated FAIL attempt is right; it does not reach "therefore no record".
4. **The choice of `OOS-DUR-01` and `OOS-REP-07`, which no pass examined.** This is where the suspicion was correct, but not about the requirement it names. **`OOS-DUR-01` is a good fit and covering it without `OOS-DUR-02` is a real claim**: its statement is entirely about committed work, the case covers committed INSERT, UPDATE and DELETE including a multi-chunk value, and oracle §6 disclaims `OOS-DUR-02`, `-03`, `-05` and `-06` explicitly. The one thing `OOS-DUR-01` alone cannot distinguish is an engine that replays indiscriminately, and `committed_delete_survived_recovery` is already a partial guard against that; the residual risk is carried correctly by `OOS-DUR-02` remaining an open row in the matrix. F1 closes the rest of it for free, because `transactions to undo: 0` is the honest, in-scope statement `OOS-DUR-01` can make about its sibling's territory. **The requirement actually overclaimed is `OOS-REP-07`** — F2 — and no pass examined that either.

## Effect on other tickets

- **Ticket 15** consumes ticket 14's records ("Verified by regenerating tickets 13 and 14's records from their runs and matching the hand-written manifests and matrix rows in substance"). F1 changes the release build from 16 to 17 executed assertions and the debug build from 17 to 18, and adds an evidence channel. Ticket 15 should read assertion counts rather than hardcode them; it is otherwise unaffected and need not wait.
- **Ticket 17** takes its representative shell timing from this case. F1 adds a log read to the case, which is negligible against the 120-second per-case cap but means the recorded 14 s and 18 s figures should be refreshed after the fix.
- **Tickets 23 to 32** inherit the recovery-evidence pattern from F1 and the requirement-quotation discipline from F2, alongside the eight lessons ticket 14 already records.
- **Ticket 13**, the public tracer bullet, still carries "independent agent review outstanding" and is not covered by this review.
- **Ticket 33** is unaffected; this review is per-repository and does not discharge the campaign acceptance review.
