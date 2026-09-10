# CBRD-26659 — Public tracer bullet: worktree and first SQL case end to end (ticket 13)

> Observed: 2026-09-10 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (ticket 11); normative context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…` (ticket 12).
> Author: Claude Opus 5 (1M context), for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 13.
> Records: [`evidence/ticket13/`](evidence/ticket13/) — manifest, matrix, attempt record, replay-bundle index, the pre-run oracle, the derivation script and the activation-evidence script.
> Companions: [engine baseline](CBRD-26659-engine-baseline_f4299ac_claude.md), [requirement catalogue](CBRD-26659-requirement-catalogue_f4299ac_claude.md), [traceability schemas](CBRD-26659-traceability-schemas_f4299ac_claude.md).

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
| Replay bundle | `~/.cub/campaign/cbrd-26659/attempts/att-T13-0002`, sha256 `e0f27e71…` |

Existing worktrees of the public repository (`cubrid-testcases` on `tc/pr-6864`, `cubrid-testcases-feat-oos`, `oos-ctp` with its two `.sql.disable` files, `oos-ci-error-codes-sql`) were not touched.

## 2. The case, and why its expectations are assertable

Schema `(id INT PRIMARY KEY, big BIT VARYING, small BIT VARYING)` at 16 KiB pages, two rows, distinct hex byte patterns per value.

| Row | `big` | `small` | Record | Pinned gate 4,086 B | Normative target 4,060 B |
|---|---:|---:|---:|---|---|
| 2, comparator | 1,000 B (1,008 serialized) | 500 B (508) | 1,564 B | inline | inline |
| 1, OOS-backed | 3,000 B (3,008) | 1,200 B (1,208) | 4,264 B | demote `big` | demote `big` |

[`evidence/ticket13/derive_case_sizes.py`](evidence/ticket13/derive_case_sizes.py) computes the demotion decision twice — once with the pinned accounting (gate `DB_PAGESIZE/4`, 16-byte stub) and once with the normative one (CBRD-27057 target, CBRD-26950 24-byte stub) — reusing ticket 11's `oos_boundaries.py` rather than restating its arithmetic. Both agree for both rows, which is what makes the placement assertable rather than merely observed. After demoting `big`, row 1 measures 1,272 B pinned and 1,280 B normative, so the demotion loop stops with `small` inline under both.

**Why the case discriminates.** `small` is 1,208 B serialized, far above both eligibility floors (16 B pinned, 24 B normative). It stays inline because the largest-first loop stopped, not because it was ineligible. An engine that demoted the *smallest* candidate first would also stop after one demotion (record after = 3,072 B ≤ 4,086 B) and would still report one chunk — so the chunk **count** cannot separate the two. `Oos_recs_sumlen` can: 3,024 for `big` against 1,224 for `small`.

The expected output was written and justified in [`evidence/ticket13/expected-oracle.md`](evidence/ticket13/expected-oracle.md) **before** the engine was run, statement by statement, with the assertion count fixed at 15.

## 3. Execution, promotion and the negative control

| Step | Result |
|---|---|
| CTP discovery | 1 of 1, `execute_case:1`, case in `okList`, `notRunList` empty |
| First run against an empty answer | `Fail:1`, candidate `.result` written |
| Review | Candidate matched the pre-run oracle value for value: `DISK_SIZE` 1008/508 and 3008/1208, all four equality flags 1, `n_rows`/`n_exact`/`n_aliased` 2/2/0 |
| Promotion | By rename into `answers/`. The retained candidate and the promoted answer hash identically (`bd64083a…`), which is the proof the promotion was a rename and not an edit |
| Green run | `Total:1 Success:1 Fail:0`, `execute_case:1`, 39 s |
| Negative control | one hex digit of the OOS-backed row's `big_md5` changed; CTP reported `Fail:1`, so the comparison detects the planted defect |

The promotion is **unflagged**: `OOS-REP-01`, `OOS-REP-02` and `OOS-SQL-01` are all `assertable` with policy `assert`, and neither row lies in a disputed band. It still needs independent agent review, per the spec; the authoring session's review is not that review.

## 4. Activation evidence, and why it is `reused` rather than `proven`

[`evidence/ticket13/activation_check.sh`](evidence/ticket13/activation_check.sh) replays the same fixture in the same insert order under `csql -S`, with `SHOW HEAP OOS OF` interleaved, and **asserts** the nine observations below, exiting non-zero on any mismatch. It starts no server, so it cannot disturb anything.

| After | `Has_oos_file` | `Oos_num_recs` | `Oos_recs_sumlen` | Predicted |
|---|---:|---:|---:|---|
| `CREATE TABLE` | 0 | 0 | 0 | yes |
| comparator row | 0 | 0 | 0 | yes |
| OOS-backed row | 1 | 1 | 3,024 | yes |

Identical on the pinned release and debug installs; `checkdb -S` exit 0 on both.

The ticket asked for status `proven`. It is recorded as **`reused`**, deliberately, and the independent Spec review confirmed this is the correct call rather than under-claiming. The CTP invocation ran client-server over JDBC; the activation run ran standalone under `csql`. The server-side write path is the same, but the execution path is not identical, and the schema's `applicability` block exists precisely to force that distinction to be written down instead of assumed. Recording it as `proven` would have overclaimed. The evidence certifies the INSERT-side demotion decision only; it certifies no scan, recovery or vacuum path.

`Oos_recs_sumlen` 3,024 carries the pinned 16-byte chunk header where the accepted 24-byte header would give 3,032. That is a Capability gap (`OOS-REP-05`, CBRD-26950), recorded against the evidence channel in its own matrix row and never written into an answer. Ticket 13's expectations were chosen outside every band where the two layouts disagree, so the gap does not weaken them.

## 5. Three findings the next tickets need

**a. CTP will not run a case that has no answer, and still exits 0.** `ConsoleAgent` hardcodes `MODE_RESULT` (`ConsoleAgent.java:116`) and `ConsoleBO` sets `shouldRun=false` when the answer file is missing (`ConsoleBO.java:367-375`). The case then lands in `notRunList` with **`isSuccessFul=true`** and `execute_case:0`, while the launcher exits 0 and prints `Total:1`. A reader trusting the exit status, or the word "successful", would record a pass for a case that never ran — exactly the hazard the specification names. Every new case must be bootstrapped with an empty `.answer`, which makes the run report `Fail:1` and write the candidate `.result`. **This is why the manifest compares `execute_case` against the expected count.**

**b. The launcher exits 0 on genuine failures too.** The negative control reported `Fail:1` with exit status 0. Ticket 15's wrappers must read `main.info`, never `$?`.

**c. The pinned installs had no JDBC driver.** Ticket 11 initialised only the `cubrid-cci` submodule, so CTP could not load `cubrid.sql.CUBRIDOID`; it discovered the case and executed nothing. The driver was built from the pin's *own* submodule (`936df5f97a540ff92b1e623d5bab4fa94fe073b3`, version 11.4.0.0077) and installed as a client artifact under `<install>/jdbc/`. **All four engine library sha256 values were re-verified against ticket 11 afterwards and are unchanged**, so the engine identity of every ticket 11 citation still holds. The sibling install `oos-ci-f4299ac` was *not* borrowed from: despite its name it sits at commit `1efcabd2`, not the pin.

## 6. Timing and budget (for ticket 17)

| Quantity | Value |
|---|---|
| **First representative fast-tier timing** | **39 s** wall clock for a one-case invocation, setup included |
| Of which CTP fixed overhead | ~37 s (`pkill`, createdb at 16 KiB, service start, broker restart, teardown) |
| Case execution | `totalTime:67` ms |
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
- **Ticket 14 (private shell tracer):** the JDBC-driver prerequisite (finding c) and the `pkill cub` isolation requirement apply to the private runner too; check both before assuming a clean run.
- **Ticket 15 (tooling):** implement `execute_case` versus expected comparison and read `main.info` rather than the exit status (findings a and b). The four records here are hand-written examples of exactly the shapes the wrappers must generate.
- **Ticket 17 (timings):** 39 s is the first fast-tier data point; the per-invocation/per-case split in §6 is the number that should drive tier placement.
- **Independent review (spec requirement):** the answer promotion in §3 needs an independent agent's review. It is unflagged, so it does not need the user's sign-off.
- **User action:** the idle `cub_master` of the `develop` debug install (pid 551535) was stopped cleanly before the run, on the user's instruction. Restart it when convenient:
  `CUBRID=$HOME/.cub/install/develop/debug_gcc CUBRID_DATABASES=$HOME/.cub/db/develop/commondb $CUBRID/bin/cubrid service start`

---

## 9. Revision 2 — what the two-axis review changed

Revision 1 was reviewed on both axes before commit. The Standards axis returned COMMENT
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
| Matrix rows | 5: three PASS rows, one Delivery gap on `OOS-REP-02`, two Capability gaps (`OOS-REP-05` chunk header, `debug-oos-log` channel) |

### Still outstanding

- The spec's **independent agent review** of the answer promotion. The two-axis review
  above was commissioned by the authoring session and does not satisfy that requirement.
- Wiring `activation_check.sh` into a scheduled invocation, so that the largest-first
  discrimination becomes part of an executed suite rather than a manual step. That is the
  Delivery gap recorded against `OOS-REP-02`, and it belongs to tickets 15 and 22.
