# CBRD-26659 — Public tracer bullet: worktree and first SQL case end to end (ticket 13)

> Observed: 2026-09-10 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (ticket 11); normative context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…` (ticket 12).
> Author: Claude Opus 5 (1M context), for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 13.
> Records: [`evidence/ticket13/`](evidence/ticket13/) — manifest, matrix, attempt record, replay-bundle index, the pre-run oracle, the derivation script and the activation-evidence script.
> Companions: [engine baseline](CBRD-26659-engine-baseline_f4299ac_claude.md), [requirement catalogue](CBRD-26659-requirement-catalogue_f4299ac_claude.md), [traceability schemas](CBRD-26659-traceability-schemas_f4299ac_claude.md).
> **Build identity superseded for new runs (2026-09-14, ticket 41).** The runs recorded here used the ticket 11 build, which carries the unit-test seams. Ticket 39 item 1 re-pinned the campaign's unmodified build without them; see [engine baseline §10](CBRD-26659-engine-baseline_f4299ac_claude.md#10-revision-2-2026-09-14-the-re-pinned-build-without-the-unit-test-seams). These records and their evidence stay valid and unedited for the invocations that cite them; a new run uses the revision-2 identity.
> Revision 3 (2026-09-11) by Claude Fable 5.1, session 6f4722b1, for [ticket 35](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/issues/35-ticket13-review-findings.md): closes the findings F1 to F6 of the specification's [independent review](CBRD-26659-ticket13-independent-review_f4299ac_claude.md) and records its observations O1 and O2; §13 lists every change. §9, §10 and §12 describe passes commissioned by the authoring session — none of them is that review.

Vocabulary follows the [docs glossary](../../CONTEXT.md). This ticket is the public suite's critical path: tickets 18 to 22 are blocked on it. It delivers **one** case; it is a proof that the seam works, not coverage.

## 1. What now exists

| Item | Where |
|---|---|
| Public testcase worktree | `/home/vimkim/gh/tc/cubrid-testcases-cbrd-26659`, branch `CBRD-26659-oos-testcases-handover` |
| Base commit (verified `origin/develop` tip) | `b94995abfc7b196fb753aac158d52512288513a6` — `git ls-remote` and `git fetch` returned the same object |
| Testcase commits | `37b1ceff8` then `e64c16481` (local only; nothing pushed) |
| Case | `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_rep02_largest_first.sql` |
| Reviewed answer | `sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_rep02_largest_first.answer` |
| Negative controls | CTP comparison: `~/.cub/campaign/cbrd-26659/negative-control/`, **outside** the repository entirely. Activation checker: `activation_check.sh` run with a wrong expected sum. Derivation gate: `derive_case_sizes.py --self-test`. |
| Replay bundle, revision 2 | `~/.cub/campaign/cbrd-26659/attempts/att-T13-0002`, sha256 `00c906fa…` (19 files, every hash verified) |
| Replay bundle, revision 1 | `~/.cub/campaign/cbrd-26659/attempts/att-T13-0001`, sha256 `59c49a51…` (15 files, every hash verified). Its manifest `inv-T13-0001`, attempt record `att-T13-0001` and bundle index `bundle-att-T13-0001` were written in revision 3 (§13, F6) |

Existing worktrees of the public repository (`cubrid-testcases` on `tc/pr-6864`, `cubrid-testcases-feat-oos`, `oos-ctp` with its two `.sql.disable` files, `oos-ci-error-codes-sql`) were not touched.

## 2. The case, and why its expectations are assertable

Schema `(id INT PRIMARY KEY, big BIT VARYING, small BIT VARYING)` at 16 KiB pages, two rows, distinct hex byte patterns per value.

| Row | `big` | `small` | Record | Pinned gate 4,086 B | Normative target 4,060 B |
|---|---:|---:|---:|---|---|
| 2, comparator | 1,000 B (1,008 serialized) | 500 B (508) | 1,564 B | inline | inline |
| 1, OOS-backed | 3,000 B (3,008) | 1,200 B (1,208) | 4,264 B | demote `big` | demote `big` |

[`evidence/ticket13/derive_case_sizes.py`](evidence/ticket13/derive_case_sizes.py) computes the demotion decision twice — once with the pinned accounting (gate `DB_PAGESIZE/4`, 16-byte stub) and once with the normative one (CBRD-27057 target, CBRD-26950 24-byte stub) — reusing ticket 11's `oos_boundaries.py` rather than restating its arithmetic. Both agree for both rows, which is what makes the placement assertable rather than merely observed. After demoting `big`, row 1 measures 1,272 B pinned and 1,280 B normative, so the demotion loop stops with `small` inline under both.

**Why the case discriminates.** `small` is 1,208 B serialized, far above both eligibility floors (16 B pinned, 24 B normative). It stays inline because the largest-first loop stopped, not because it was ineligible. An engine that demoted the *smallest* candidate first would also stop after one demotion (record after = 3,072 B ≤ 4,086 B) and would still report one chunk — so the chunk **count** cannot separate the two. `Oos_recs_sumlen` can: 3,024 for `big` against 1,224 for `small`.

The expected output was written and justified in [`evidence/ticket13/expected-oracle.md`](evidence/ticket13/expected-oracle.md) **before** the engine was run, statement by statement. Revision 1 of the oracle fixed the assertion count at 15; revision 2 re-derived it as 27 after the length and digest columns were added (`expected-oracle.md`, "Revised assertion count"). Both counts are derived from the case text, not measured by CTP (§5 finding a, §13 F3).

## 3. Execution, promotion and the negative control

| Step | Result |
|---|---|
| CTP discovery | 1 of 1, `execute_case:1`, case in `okList`, `notRunList` empty |
| First run against an empty answer | `Fail:1`, candidate `.result` written |
| Review | Candidate matched the pre-run oracle value for value: `DISK_SIZE` 1008/508 and 3008/1208, all four equality flags 1, `n_rows`/`n_exact`/`n_aliased` 2/2/0 |
| Promotion | By rename into `answers/`. The retained candidate and the promoted answer hash identically (`b38a24b5…`), which is the proof the promotion was a rename and not an edit |
| Green run | `Total:1 Success:1 Fail:0`, `execute_case:1`, 39 s |
| Negative control | one hex digit of the OOS-backed row's `big_md5` changed; CTP reported `Fail:1`, so the comparison detects the planted defect |

The promotion is **unflagged**: `OOS-REP-01`, `OOS-REP-02` and `OOS-SQL-01` are all `assertable` with policy `assert`, and neither row lies in a disputed band. The specification's independent agent review of it is the [record of 2026-09-11](CBRD-26659-ticket13-independent-review_f4299ac_claude.md), performed by a session that authored none of this; it re-verified the unflagged classification and accepted the promotion. The passes recorded in §9, §10 and §12 were commissioned by the authoring session and are not that review.

## 4. Activation evidence, and why it is `reused` rather than `proven`

[`evidence/ticket13/activation_check.sh`](evidence/ticket13/activation_check.sh) replays the same fixture in the same insert order under `csql -S`, with `SHOW HEAP OOS OF` interleaved, and **asserts** the nine observations below, exiting non-zero on any mismatch. It starts no server, so it cannot disturb anything.

| After | `Has_oos_file` | `Oos_num_recs` | `Oos_recs_sumlen` | Predicted |
|---|---:|---:|---:|---|
| `CREATE TABLE` | 0 | 0 | 0 | yes |
| comparator row | 0 | 0 | 0 | yes |
| OOS-backed row | 1 | 1 | 3,024 | yes |

Identical on the pinned release and debug installs; `checkdb -S` exit 0 on both.

The ticket asked for status `proven`. It is recorded as **`reused`**, deliberately, and both the commissioned Spec pass (§9) and the specification's independent review (O2, below) confirmed this is the correct call rather than under-claiming. The CTP invocation ran client-server over JDBC; the activation run ran standalone under `csql`. The server-side write path is the same, but the execution path is not identical, and the schema's `applicability` block exists precisely to force that distinction to be written down instead of assumed. Recording it as `proven` would have overclaimed. The evidence certifies the INSERT-side demotion decision only; it certifies no scan, recovery or vacuum path.

**Accepted interpretation of the reuse rule (user decision, 2026-09-11).** The specification says activation evidence "is reused only when fixture, execution path, engine configuration and tested conditions match". This ticket read "execution path" as the OOS operation (insert, scan, recovery, vacuum), not the run mode, and reused standalone evidence for a client-server run on that reading. The independent review agreed with the reading and with `reused` over `proven`, but observed (O2) that a campaign-wide interpretation had been settled inside an implementation ticket, which the specification's reopening rule forbids, and put three options to the user. The user chose the reviewer's recommendation: the reading is recorded here and in the `applicability.execution_path` text of the three case rows, both manifests and both attempt records as the accepted interpretation of an existing rule covering ticket 13, so the map stays closed; and tickets 18 to 22 run their activation checks client-server under `campaign_ns.sh`, in the case's own run mode, so the question stops arising for public SQL. `reused` remains the correct status for this ticket's rows: the run mode did differ, and the record says so instead of upgrading the word.

`Oos_recs_sumlen` 3,024 carries the pinned 16-byte chunk header where the accepted 24-byte header would give 3,032. That is a Capability gap (`OOS-REP-05`, CBRD-26950), recorded against the evidence channel in its own matrix row and never written into an answer. Ticket 13's expectations were chosen outside every band where the two layouts disagree, so the gap does not weaken them.

## 5. Four findings the next tickets need

**a. CTP will not run a case that has no answer, and still exits 0.** `ConsoleAgent` hardcodes `MODE_RESULT` (`ConsoleAgent.java:116`) and `ConsoleBO` sets `shouldRun=false` when the answer file is missing (`ConsoleBO.java:367-375`). The case then lands in `notRunList` with **`isSuccessFul=true`** and `execute_case:0`, while the launcher exits 0 and prints `Total:1`. A reader trusting the exit status, or the word "successful", would record a pass for a case that never ran — exactly the hazard the specification names. Every new case must be bootstrapped with an empty `.answer`, which makes the run report `Fail:1` and write the candidate `.result`. **This is why the manifest compares `execute_case` against the expected count.**

**b. The launcher exits 0 on genuine failures too.** The negative control reported `Fail:1` with exit status 0. Ticket 15's wrappers must read `main.info`, never `$?`.

**c. The pinned installs had no JDBC driver.** Ticket 11 initialised only the `cubrid-cci` submodule, so CTP could not load `cubrid.sql.CUBRIDOID`; it discovered the case and executed nothing. The driver was built from the pin's *own* submodule (`936df5f97a540ff92b1e623d5bab4fa94fe073b3`, version 11.4.0.0077) and installed as a client artifact under `<install>/jdbc/`. **All four engine library sha256 values were re-verified against ticket 11 afterwards and are unchanged**, so the engine identity of every ticket 11 citation still holds. The sibling install `oos-ci-f4299ac` was *not* borrowed from: despite its name it sits at commit `1efcabd2`, not the pin.

**d. CTP's serialized `hasAnswer` is `false` on every run.** `summary.info` in all eight result directories this ticket produced — the answerless first run of finding (a) (`1020205027`: case in `notRunList`, `<shouldRun>false</shouldRun>`, `execute_case:0`), revision 1's bootstrap, green and negative-control runs (`1020225647`, `1020240166`, `1020251150`) and revision 2's bootstrap, green, negative-control and final runs (`1020410056`, `1020415767`, `1020463816`, `1020515363`) — carries `<hasAnswer>false</hasAnswer>`, in the seven runs that had an answer beside `<shouldRun>true</shouldRun>`, including the four that compared against an answer that existed and matched or mismatched it. In the answerless run `false` is the truthful value, so the field carries no information either way. `ConsoleBO.java:411` looks as if it should write `true`; the independent review (O1) reported the value as reproducible and unexplained, and this revision re-checked all eight files (the delta review's D3 added the eighth). Ticket 15's tooling must therefore detect the missing-answer trap of finding (a) from `notRunList` and `execute_case` in `main.info`, never from `hasAnswer`.

## 6. Timing and budget (for ticket 17)

| Quantity | Value |
|---|---|
| **First representative fast-tier timing** | **39 s** wall clock for a one-case invocation, setup included — identical for both revisions (`timing.txt`: 20:23:30 to 20:24:09 and 20:41:25 to 20:42:05) |
| Of which CTP fixed overhead | ~37 s (`pkill`, createdb at 16 KiB, service start, broker restart, teardown) |
| Case execution | `totalTime:69` ms for the revision-2 green run (`summary.info`, result dir `schedule_linux_sql_64bit_1020415767`). Revision 1's three runs recorded 61 / 67 / 257 ms and revision 2's four 59 / 69 / 54 / 55 ms; the 67 previously quoted here was revision 1's green run |
| Invocation cap | 900 s — not approached |
| Per-case cap | 120 s — not approached |
| Storage | 454 MiB under `/home/vimkim/.cub/campaign/cbrd-26659`; `/home` had 2.3 TiB free |

The dominant cost is per-invocation, not per-case: a fast-tier invocation should batch the public cases into one CTP run rather than paying ~37 s each.

## 7. Ticket 13 criteria checklist

| Criterion | Status |
|---|---|
| New public worktree on the exactly-named branch, based on a freshly fetched and verified `origin/develop` tip, base and testcase SHAs recorded; existing worktrees untouched | met (§1) |
| One case inserting and selecting an OOS-backed record, sizes from ticket 11's boundary table, exact whole-value oracle justified before the engine ran, inline comparator row | met (§2), oracle in `expected-oracle.md` |
| CTP SQL launcher runs the scenario by path, launcher compatibility confirmed, discovery and executed assertion counts recorded | met (§3), and see finding (a): compatibility needed the JDBC driver and the empty-answer bootstrap |
| First-run result treated as a candidate, reviewed against its requirement ID, promoted by rename, review note recorded | met (§3); identical hashes prove the rename |
| Paired unmodified debug run supplies activation evidence, recorded with applicability | met (§4), recorded as `reused` rather than `proven`, with the reason |
| One negative control shown to fail under the CTP comparison, kept outside the answers directory | met (§3); kept outside the repository entirely |
| Hand-written manifest and matrix row following ticket 12's schemas, stored in the evidence home | met — manifest, matrix, attempt record and replay-bundle index all validate; `tools/check_campaign_records.py` passes |
| Run time recorded as the first representative fast-tier timing | met (§6) |
| Committed locally on the testcase branch; nothing pushed | met (§1) |

## 8. Hand-offs

- **Tickets 18 to 22 (public SQL cases):** unblocked. Reuse `derive_case_sizes.py` for every new fixture, bootstrap each new case with an empty `.answer` (finding a), and batch cases into one invocation (§6). The scenario directory, the CTP configuration and the activation-evidence script are all reusable as they stand.
  **Matrix rule (independent review F2, §13; qualified after the ticket 35 delta review, D1):** a matrix row says where its OOS-path evidence comes from, and when that source is a checker outside every executed suite — today `activation_check.sh` — the row says so. The row must not carry `gap_kind: none` when a clause of the requirement's stated behavior is evidenced *only* by that non-executed checker (`OOS-REP-01`: all three clauses; `OOS-REP-02`: the placement half). A row whose every clause the case asserts at the seam records the checker as the source of its OOS-backed premise and may keep `gap_kind: none` (`OOS-SQL-01`: the value-correctness clauses are executed; only the premise that the row was OOS-backed comes from the checker). When the case executes no clause at all, use the two-row form F2 gave `OOS-REP-01`: a case row scoped to the executed attempt plus a caseless companion row with `latest_outcome: null` and `gap_kind: Delivery gap`, so that no outcome filter counts the requirement as covered.
  **Activation checks (user decision O2, §4):** run them client-server under `/home/vimkim/.cub/campaign/cbrd-26659/ticket14/tools/campaign_ns.sh`, in the same run mode as the case, so the evidence can be `proven` where fixture and conditions otherwise match and the reuse question does not arise.
- **Ticket 14 (private shell tracer):** the JDBC-driver prerequisite (finding c) and the `pkill cub` isolation requirement apply to the private runner too; check both before assuming a clean run.
- **Ticket 15 (tooling):** implement `execute_case` versus expected comparison and read `main.info` rather than the exit status (findings a and b). The records here are hand-written examples of exactly the shapes the wrappers must generate — since revision 3, seven of them: two manifests, two attempt records, two bundle indexes and the matrix. Also from the independent review: never read `hasAnswer` (finding d); executed assertion counts stay `null` until a real counter exists (F3); generate `configurations_not_run` from the one rule the manifests now state (F4); and every executed attempt, including a first revision's, gets a manifest, an attempt record and a bundle index (F6).
- **Ticket 17 (timings):** 39 s is the first fast-tier data point; the per-invocation/per-case split in §6 is the number that should drive tier placement.
- **Independent review (spec requirement):** done 2026-09-11 by a session that authored none of this — [record](CBRD-26659-ticket13-independent-review_f4299ac_claude.md). All nine criteria met; the promotion is unflagged and accepted, so it needs no user sign-off. Its six findings and two observations are closed in §13.
- **User action:** the idle `cub_master` of the `develop` debug install (pid 551535) was stopped cleanly before the run, on the user's instruction. Restart it when convenient:
  `CUBRID=$HOME/.cub/install/develop/debug_gcc CUBRID_DATABASES=$HOME/.cub/db/develop/commondb $CUBRID/bin/cubrid service start`
  Status at revision 3 (2026-09-11): still down. Port 1523 was held by the `CBRD-27398-pgbuf-inspector-contract` debug install's live `cub_master` (pid 487844, with a running `cub_server demodb`), and the `develop` debug install is also configured for `cubrid_port_id=1523`, so a `service start` would have collided; the user chose not to restart it yet. Check `ss -ltnp | grep :1523` in the terminal you would start it from.

---

## 9. Revision 2 — what the two-axis review changed

Revision 1 was reviewed on both axes before commit, by two passes the authoring session
commissioned and briefed (see the note that opens §10). The Standards axis returned COMMENT
(no blocking issue); the Spec axis returned REVISE with four findings. All were accepted
and fixed; none of revision 1's arithmetic was wrong, and the reviewer's independent hand
calculation reproduced every size, gate comparison and the 3,024 sum exactly.

| # | Finding | What changed |
|---|---|---|
| S1 | Case used uppercase SQL keywords; every 2026 sibling in `_36_guava` on `develop` is lowercase | Lowercased. I checked the claim rather than taking it: the uppercase OOS precedent `cbrd_27006` exists only on `feature/oos-m2`, **not** on this branch's base, so there was no in-repo precedent for uppercase at all |
| S2 | Header cited campaign documents unresolvable from the public repository, and left the engine revision unnamed | Header rewritten to stand alone: it names `f4299ac0c`, cites CBRD-27057 and CBRD-26950, and explains the demotion mechanism without reference to private material |
| P1 | **The committed asset had no regression power for `OOS-REP-02`** — a smallest-first engine would produce a byte-identical answer | Accepted as unavoidable for a portable SQL case, and recorded rather than hidden: the case header now says so explicitly, and the matrix carries a **Delivery gap** row against `OOS-REP-02`. The activation script was promoted from a passive evidence collector to a **validated checker** that asserts nine observations and exits non-zero on mismatch |
| P2 | Whole-value equality was self-referential — the engine comparing its own read-back | Added `OCTET_LENGTH`, `BIT_LENGTH` and `MD5` per value. CUBRID's `MD5` of a `BIT VARYING` digests its lowercase hex form, so all four digests were computed in Python **before** the run and are reproducible without CUBRID. Digests are emitted as values, so corruption shows as a changed digest rather than a silent `0` |
| P3 | One control for three checking mechanisms | Now one each: CTP text comparison (planted digest defect → `Fail:1`); activation checker (expected sum 1,224, the smallest-first value → 1 assertion fails, exit 1); derivation gate (`--self-test` with two fixtures derived to straddle the record-gate and eligibility-floor disputed bands → both correctly rejected) |
| P4 | `executed.assertion_count` was asserted, not measured | Kept at the recounted 27 but explicitly labelled **derived** in the manifest note: CTP has no assertion counter, so the number is justified only because a byte-identical `.result` entails that all 27 scalars matched. Ticket 15 must add a real counter |
| P5 | The debug run was made but never cited as its own evidence, and the handoff's required evidence-channel Capability gap row was missing | Both added: the debug assertion log is cited in the matrix, and a `debug-oos-log` Capability-gap row records that the channel cannot witness an insert at this pin (measured: `oos.log` stayed at 10 lines, 0 `oos_insert` lines) |
| P6 | No client-artifact identity recorded for the JDBC driver | The jar's sha256 and its gitlink provenance are now in the bundle's `identity.txt`. Worth stating plainly: a 11.4 driver fronts an 11.5.0.2648 server, and that is the pairing the pinned commit itself specifies through its own submodule gitlink, not a substitution |

**The negative controls earned their keep immediately.** Writing the activation checker's
control exposed a real defect *in the checker*: its assertion block was piped into `tee`,
so it ran in a subshell, the failure counter never propagated, and the script printed
`FAIL` while exiting `0`. A checker that cannot fail proves nothing, and only the control
revealed it. Fixed, then verified in both directions — good path exit 0, control exit 1.

### Revised numbers

| Quantity | Value |
|---|---|
| Assertion count (derived) | 27 |
| Activation checker assertions | 9, all passing on release and on debug |
| Fast-tier timing | 39 s, unchanged |
| Matrix rows | 6 at revision 2 after R4's split, re-derived from `matrix.json` in revision 3 (this row said 5): three PASS case rows, of which the `OOS-REP-02` row carries a Delivery gap; one caseless Delivery-gap row (`OOS-REP-02` placement discrimination); two Capability gaps (`OOS-REP-05` chunk header, `debug-oos-log` channel). 7 at revision 3 (§13) |

### Still outstanding

- ~~The spec's **independent agent review** of the answer promotion.~~ Done 2026-09-11, by a
  session that authored none of this: [record](CBRD-26659-ticket13-independent-review_f4299ac_claude.md). The two-axis review above was
  commissioned by the authoring session and does not satisfy that requirement; the record's
  findings are closed in §13.
- Wiring `activation_check.sh` into a scheduled invocation, so that the largest-first
  discrimination becomes part of an executed suite rather than a manual step. That is the
  Delivery gap recorded against `OOS-REP-02`, and it belongs to tickets 15 and 22.

---

## 10. Commissioned review pass, part one (2026-09-10) — not the specification's independent review

The campaign specification requires that "an independent agent session, never the authoring
session, reviews Standards and Spec conformance per repository, validates the
negative-control checkers, and audits replay and cleanup evidence before acceptance".
**This section does not record that review, and cannot.** The pass it describes was
commissioned by the authoring session: I wrote the brief (which, as §12 discloses, contained
a false premise about what was running on the host), chose which artifacts and which commit
it covered, and decided which findings to act on and how. That is the same principle as not
signing off on one's own authoring output, one level up, and it holds however many defects
the pass found — arguably more strongly the more it found, because a long list of fixed
findings is exactly what makes a change look cleared. Revisions 1 and 2 of this section
called the pass "independent" and recorded an ACCEPT verdict on the promotion; both
statements were wrong and are withdrawn.

The specification's independent review is the separate [record of 2026-09-11](CBRD-26659-ticket13-independent-review_f4299ac_claude.md),
performed by a session that authored none of these artifacts and read §9 to §12 only after
forming its findings; its verdict, and nothing below, is what stands on the promotion. The
places where the briefs I wrote steered attention, and so where that independent look was
worth most: the classification of the promotion as **unflagged**, which no commissioned pass
challenged (the independent review re-verified it and it holds); the **`reused`** framing of
the activation evidence, which I proposed and which rests on a specification interpretation
that was not this ticket's to settle (§4, O2); and the choice of **`OOS-REP-01`, `OOS-REP-02`
and `OOS-SQL-01`** as the requirements this case covers, which nothing in §9 to §12 examined
and where the independent review found the `OOS-REP-01` row to be an overclaim (§13, F2).

What the pass re-verified, and which held: the promotion is a pure rename (all
three copies of the answer hash identically); all four MD5 digests reproduce in Python and
match the committed answer byte for byte; the activation checker passes nine assertions on
the good path and fails on exactly the discriminating assertion under its control; the
derivation gate rejects both disputed fixtures, and the reviewer re-derived both bands from
ticket 11 §5 rather than trusting the script; all four engine library hashes match ticket
11; the pinned worktree is clean apart from ticket 11's own `cubrid-cci` artifact; all four
JSON records validate and `check_campaign_records.py` passes; `reused` is the correct
evidence status; nothing was pushed.

Four defects were found. **Every one was in the narrative or bookkeeping layer, none in the
engineering**, and all four are now fixed:

| # | Defect | Fix |
|---|---|---|
| R1 | The attempt record said `pkill` was denied "for two processes owned by another uid". The real count in `ctp.log` is 44 denial lines over **22 unique pids**. Worse, the wording implied CTP had scoped its kill | Count corrected, and the qualification that the earlier wording obscured is now stated outright: `pkill cub` is an unscoped pattern match, so the "no unrelated process was killed" outcome held **only because the kernel refused the signal**, not because the runner was careful. Any cub-named process this user owned would have died |
| R2 | `complete: true` was **false**. `ctp_final.log`, a fourth CTP invocation re-verifying the case after the review edits, sat in the bundle root but appeared in neither `SHA256SUMS` nor the index, leaving `total_bytes` understated by 5,818 B | Bundle re-indexed to 19 files, every hash verified with `sha256sum -c`, `total_bytes` corrected to 46,360, and the fourth run described in the index rather than left as an orphan |
| R3 | Three stale revision-1 citations: §3 quoted revision 1's promotion hash, §1 quoted a bundle hash that resolved to nothing, and `replay_command.txt` inside the *revision 2* bundle still named `att-T13-0001` and commit `37b1ceff8` | All three corrected. The replay command now matches its own bundle's `identity.txt`. (The two configurations are byte-identical, so a replay would still have run the right thing — but the record was self-contradictory) |
| R4 | The `OOS-REP-02` case row carried `latest_outcome: PASS` while its own summary admitted the case has no regression power, so anyone filtering on PASS would read the requirement as covered | Split into two rows. The case row keeps `PASS` — the attempt genuinely passed — but now states that it covers the logical half only and names its companion. A new caseless row, `OOS-REP-02/-/placement-discrimination`, carries `latest_outcome: null` with `gap_kind: Delivery gap`, so no outcome filter can count the requirement as covered |

R2 and R3 are both the same underlying mistake: I revised the work after the two-axis
review and updated the JSON records carefully while letting the prose and one copied file
drift behind. The lesson for tickets 14 to 32 is that the hand-written records need the
same re-derivation discipline on a revision as on a first write — or, better, that ticket
15's tooling should generate the hashes and counts that drifted here.

**Limits of the pass:** it was advisory on the two items it could
not settle — the spec reserves acceptance of incomplete coverage to the user alone. The
`OOS-REP-02` placement gap is proposed for tickets 15 and 22, not accepted; only the user
converts a coverage gap into an accepted exclusion.

## 11. Environment side effects a replaying ticket must expect

- **CTP rewrites the install's configuration.** `run.sh`'s `reset_cubrid_files` copies
  `conf/cubrid.conf` to `conf/cubrid.conf.forFun` on its first run against an install and
  restores from that backup on every later run. The pinned release install therefore now
  carries a `cubrid.conf.forFun` created at the first CTP invocation, and its live
  `cubrid.conf` was restored to the state ticket 11 left it in (`cubrid_port_id=26659`).
  Nothing about the engine binaries changed, but a ticket that edits the install's
  configuration between CTP runs will find its edit reverted.
- **`pkill cub` is unscoped.** Before running the SQL suite, confirm no CUBRID process this
  user owns is doing unrelated work. This host runs several installs concurrently
  (`~/.cub/install/*`), and they all default to `cubrid_port_id=1523`, so only one master
  can hold the default port at a time. A campaign run that stops someone else's master
  frees that port, and another install may take it before the original is restarted.
- **Databases retained as evidence.** `t13chk16k`, `t13chkd16k` and `t13chkn16k` under
  `~/.cub/campaign/cbrd-26659/db` are the activation checker's fixtures and its negative
  control. They are disposable, but they are referenced by the attempt record's
  `resources_owned`, so delete them only when the retention class expires.

## 12. Commissioned review pass, part two: two further findings and its limits

The commissioned pass's report arrived in two parts. The second part confirmed that the `OOS-REP-02`
row split above is exactly the fix it wanted, and added two findings and an important
correction to the brief it was given.

**R5 (MAJOR) — `executed.assertion_count` was a manufactured measurement, and the schema
caused it.** The reviewer's own hand count agreed that 27 is right under the stated
convention, but pointed out that `expected: 27` against `executed: 27` compares the
derivation to itself. The root cause is in ticket 12's manifest schema, not in this ticket:
`expected.assertion_count` is nullable, described as "null when the seam cannot pre-count",
while `executed.assertion_count` was forced to be an integer — so a runner with no
assertion counter is *obliged* to invent one.

Fixed at the source, as a minimal backward-compatible widening of ticket 12's schema (an
existing integer still validates): `executed.assertion_count` and
`case_result.assertions.executed` now accept null, with a description saying when null is
required and where the hand-counted figure belongs. The attempt record and its schema were
missed by this fix and carried the 27 as if measured until revision 3 closed the gap (§13,
F3). This manifest now records **null**,
and `proof.verdict` stays `proven` on what was genuinely observed — expected case count
1 = discovered 1 = executed 1, `execute_case:1`, and a byte-identical whole-result
comparison. Ticket 15 still owns a real counter.

*This edits another ticket's deliverable.* It is recorded here rather than done silently
because ticket 12's schemas are the campaign's contract: the change removes a trap that
would otherwise have made every later invocation fabricate an execution count.

**R6 (MINOR) — the Delivery gap named the wrong obstacle.** My wording, "no portable SQL
exposes per-attribute placement", was an assertion. The reviewer tested the obvious
alternative and found the real constraints, which are now what the matrix row records:
`SHOW` cannot be projected (`select … from (show heap oos of …) t` fails at parse time with
`Syntax error: unexpected 'oos', expecting JOIN`; the grammar admits `SHOW` only as a whole
statement, `csql_grammar.y:7379`), its full row carries volatile physical identifiers that
cannot go in an answer file, and `DISK_SIZE` is placement-blind. Tickets 15 and 22 need the
tested constraint, not the assertion.

### What the pass could not verify, and one thing I got wrong

**The brief I gave the reviewer contained a false premise.** I told it "it is expected that
no unrelated user cub process is running right now". By the time it ran, `pgrep` showed
`cub_master`, `cub_server demodb` and `cub_pl demodb` from the
`CBRD-27398-pgbuf-inspector-contract` install, started 20:58:45. The reviewer checked
rather than trusting me, and **declined to run CTP** because `do_clean`'s unscoped
`pkill cub` would have killed another session's live server. That was the right call, and
it is the second time in this ticket that the unscoped `pkill` has been the hazard. It
audited the retained result directories and logs instead, so the CTP figures in this record
are from the retained `main.info` files, not from an independent re-run.

Also outside what it could confirm, and recorded as such:

- That pid 551535 was stopped by hand, and that `ipcs -m` was empty before the run. Both
  are past states with no surviving artifact.
- That the oracle predated the run. File mtimes are consistent (20:39 < 20:41:25) but are
  not proof. The weight for that claim rests instead on the four digests being
  reproducible in Python from the byte patterns alone, which needs no trust in mtimes.

### Conditions, and their status

| Condition | Status |
|---|---|
| Fix the pkill count and its framing | done (R1) |
| Index or delete `ctp_final.log`; recompute `total_bytes` and `SHA256SUMS` | done — indexed, 19 files, all hashes verified (R2) |
| Correct the three revision-1 citations | done (R3) |
| Split the `OOS-REP-02` matrix row | done, as the reviewer specified (R4) |
| Relax the schema's executed-count field before any ticket claims a measured count | done now rather than deferred (R5) |

None of the conditions blocked the engineering. Whether the promotion stands was never this
pass's to say: that is the specification's independent review, recorded separately and
closed in §13.

---

## 13. Revision 3 — closing the specification's independent review (ticket 35, 2026-09-11)

The [independent review](CBRD-26659-ticket13-independent-review_f4299ac_claude.md) of 2026-09-11 was performed by a session that authored
none of the artifacts above and read §9 to §12 only after forming its findings. It found all
nine criteria met, accepted the unflagged promotion, and returned two blocking findings on
the record and matrix, four non-blocking ones and two observations. This revision closes
them. **No case, answer or branch changed, and no CTP run was made** (an unnecessary
invocation costs an unscoped `pkill cub` on a shared host); every change is in this
repository. The ticket 13 review record itself was not edited.

| # | Finding | What changed | Where |
|---|---|---|---|
| F1 (blocking) | §10 and §12 declared the specification's independent review done and the promotion accepted; both passes were commissioned by the authoring session | §10 and §12 retitled as commissioned passes; the ACCEPT verdict and both "the answer promotion is accepted" sentences removed; §10 opens by naming the record that is the specification's review, where the author's briefs steered attention (the unflagged classification, the `reused` framing, the choice of `OOS-REP-01`, `OOS-REP-02` and `OOS-SQL-01`), and why a long list of fixed findings is not a clearance; §3, §8 and §9 point at the record | this file |
| F2 (blocking) | `OOS-REP-01` carried `gap_kind: none` on evidence no executed suite produces | Split as R4 split `OOS-REP-02`, chosen over the single-row form the review also allowed because the case row's `PASS` must stay visible as an attempt outcome without any outcome filter counting `OOS-REP-01` as covered: the case row keeps `PASS` for the executed attempts but carries `gap_kind: Delivery gap` and a scope note saying the case observes none of the requirement's three clauses (`DISK_SIZE` is placement-blind, so a wrongly demoted comparator would leave the answer byte-identical); a caseless companion row `OOS-REP-01/-/inline-placement-observation` with `latest_outcome: null` carries the gap and the tested obstacle. `OOS-SQL-01` gains one sentence naming the non-executed checker as the source of its OOS-backed premise. The rule for tickets 18 to 22 is in §8 and on the companion row | `matrix.json` |
| F3 | The R5 widening reached the manifest schema but not the attempt record or its schema, so `att-T13-0002.json` still manufactured `executed: 27` | `attempt-record.schema.json` widens `assertions.executed` to integer or null with the manifest's description; `att-T13-0002.json` records null; the traceability-schemas document records both widenings as deliberate edits to ticket 12's contract (its §11); `check_campaign_records.py` and `render_docs.py --check` pass | `schemas/`, `att-T13-0002.json`, schemas document |
| F4 | `configurations_not_run` had 10 entries and matched no rule | Regenerated from one stated rule, "configurations the CTP case did not run in this invocation": 11 of the 12 page-size × build-mode × run-mode combinations; the two standalone activation-checker runs are treated alike as checker runs, not case executions; the rule is named in each manifest's note | `inv-T13-0002.json`, `inv-T13-0001.json` |
| F5 | Four stale numbers of the class R3 had reported fixed | Re-derived from the artifacts and cited beside each: §2 assertion count from `expected-oracle.md` (15 in revision 1, 27 in revision 2); §9 matrix-row count from `matrix.json` (6 at revision 2, 7 now); §6 case time from the revision-2 green run's `summary.info` (69 ms; the 67 was revision 1's green run); `expected-oracle.md` marks its revision-1 negative-control wording superseded and describes the control actually run (one hex digit of `big_md5`, `56d1d803…` → `56d2d803…`, answer line 23) | this file, `expected-oracle.md` |
| F6 | `att-T13-0001`, revision 1's green and promoted run, had a bundle and no record | `inv-T13-0001.json`, `att-T13-0001.json` and `bundle-att-T13-0001.json` written from the retained bundle (`SHA256SUMS` verified; bundle hash `59c49a51…`; 15 files, 29,594 bytes; `candidate.result` and `expected.answer` both `bd64083a…`; 39 s; `execute_case:1`); its promotion recorded in that manifest's `answer_promotions` and marked superseded by revision 2's answer; both attempts listed in every case row's `finding.history`, `flakiness.attempts` 2, both attempt records linked. Revision 1 stays PASS: the supersession is a revision of the case, not a FAIL of the attempt. Caseless rows have no attempts and their history stays empty | `evidence/ticket13/` |
| O1 | CTP's serialized `hasAnswer` reads `false` on every run | Recorded as finding (d) in §5, re-checked on all eight result directories of both revisions, including the answerless first run where `false` is the truthful value | this file |
| O2 (decided) | The evidence-reuse interpretation was settled inside an implementation ticket | The user's decision of 2026-09-11 recorded in §4 and in the `applicability.execution_path` text of the three case rows, both manifests and both attempt records; tickets 18 to 22 each carry the client-server activation-check line | this file, `matrix.json`, manifests, attempt records, tickets 18 to 22 |

Also aligned while the same records were open: `deadline.evidence_captured_on_timeout` is
`null` in both attempt records, as the schema's description asks when the deadline was not
reached (revision 2 had written `false`); and `inv-T13-0002`'s `answer_promotions[].reviewer`
no longer says the independent review is outstanding. §8's user-action bullet also gained a status
paragraph about the `develop` master and port 1523, recorded there because the check was made in
this session (the delta review's D7 asked for the disclosure).

### Numbers at revision 3

| Quantity | Value | Source |
|---|---|---|
| Assertion count (derived from the case text, not measured) | 27 (revision 2); 15 (revision 1) | `expected-oracle.md` |
| Executed attempts recorded | 2: `att-T13-0001` (revision 1, green, answer later superseded) and `att-T13-0002` (revision 2, green, committed answer) | `evidence/ticket13/` |
| Matrix rows | 7: three case rows (`OOS-REP-01`, `OOS-REP-02`, `OOS-SQL-01`, all PASS on both attempts; the first two carry Delivery gap), two caseless Delivery-gap rows (`OOS-REP-01` inline placement, `OOS-REP-02` placement discrimination), two Capability-gap rows (`OOS-REP-05` chunk header, `debug-oos-log` channel) | `matrix.json` |
| Fast-tier timing | 39 s wall clock, both revisions | `timing.txt` in each bundle |
| Case execution | 69 ms, revision-2 green run | `summary.info`, result dir `1020415767` |

### The delta review of this revision

A session that authored neither ticket 13's artifacts, nor the review record, nor this revision
reviewed docs commit `77366ee` on 2026-09-11 (its record is appended to [ticket 35](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/issues/35-ticket13-review-findings.md)):
**ACCEPT WITH FIXES**, every re-derived number, hash and timestamp matching. Its fixes are applied in
the commit that follows `77366ee`: D1 (MAJOR) — the matrix rule as first written contradicted the
`OOS-SQL-01` row, which rightly keeps `gap_kind: none`; the rule in §8, on the companion row and in
tickets 18 to 22 is now qualified by whether a clause of the requirement is evidenced only by the
non-executed checker. D2 — revision 1's negative control did run, as the `big_ok` flip its oracle
describes (result dir `1020251150`); the oracle's revision-3 wording said it was planned and not
run, and now says which control each revision ran. D3 — eight result directories, not seven
(finding d). D4 — the F2 row now says why the two-row form was chosen. D5 to D7 — wording and
disclosure. D8 needed nothing: the revision-1 attempt's evidence pointing at revision 2's checker
output is disclosed in its applicability text and is what `reused` is for.

### What the independent review found sound, and is not re-litigated here

The dual-accounting derivation and its self-test; the four Python-reproducible digests; the
promotion-by-rename proof; the whole-text CTP comparison and the derived-27 argument; all
three negative controls; the `SHOW HEAP OOS` substitution for the debug log and its
Capability-gap row; the `reused` status; the cleanup disclosure; and the unflagged
classification of the promotion. The review record lists these with its reasoning.
