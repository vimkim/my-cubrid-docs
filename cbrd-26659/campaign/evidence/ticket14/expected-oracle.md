# Expected oracle — `cbrd_26659_oos_dur01` (CBRD-26659 campaign, ticket 14)

> **Every number below is derived, not read off**: the sizes come from ticket 11's record
> accounting through [`derive_case_sizes.py`](derive_case_sizes.py), the digests from
> `md5sum` and `hashlib.md5` over the byte pattern, the lengths from the serialization
> formula, the chunk count from the same derivation. An independent reviewer re-derived all
> of them and they reproduce.
>
> **Correction, and a process finding.** An earlier revision of this file claimed that no
> OOS-backed value, placement, chunk count or recovery result of this fixture had been
> observed before it was written. That claim was **false** and is withdrawn.
> [`probes/probe_format.sh`](probes/probe_format.sh) ran at 12:58; this file was first
> written at 13:07. That probe used a table of the same shape with rows of exactly 4,036
> `AA`, 16,284 `BB` and 4,011 `CC`, applied the same `EE` update, crashed and restarted the
> server, and read back `COUNT(*)`, the three MD5 digests and `SHOW HEAP OOS` before and
> after recovery. So the engine's answer for this fixture *was* visible before the oracle was
> committed to paper.
>
> What survives, and what does not. The specification's requirement is that an expectation be
> "justified before the engine is consulted"; here the **justification** is independent of the
> engine — it is arithmetic over ticket 11's constants plus two independent digest
> computations, and it would have produced these same numbers with no engine available — but
> the **ordering** claim cannot be made. Independence rests on the derivation, not on
> ignorance of the answer. The two probes that *did* use a deliberately unrelated fixture
> ([`probes/probe_restart.sh`](probes/probe_restart.sh) and
> [`probe_restart2.sh`](probes/probe_restart2.sh), a one-row `CREATE TABLE p (i INT)`) show
> what the discipline should have been throughout.
>
> **For tickets 18 to 22 and 23 to 32: probe format on a fixture that is not the case's
> fixture.** It costs nothing and it keeps the stronger claim available.
> All four probes, their scripts and a note on what each settled are in [`probes/`](probes/).
>
> **Revision 8 (2026-09-11, ticket 34), written before the revision-8 runs.** The specification's
> [independent review](../../CBRD-26659-ticket14-independent-review_f4299ac_claude.md) found (F1) that
> nothing here showed the recovery path had run, and (F2) that `OOS-REP-07` was quoted with its two
> hard clauses removed. Assertion 10, `recovery_redo_phase_replayed_log_records`, is added and the
> former 10 to 17 become 11 to 18 (section 5); the `OOS-REP-07` claim is withdrawn (section 1); the
> recovery-log reader gets its controlled failure examples (section 7). No size, digest or count
> above changes.

## 1. Requirements under test

| ID | Statement (catalogue, sha256 `0cc33c82…`) | Policy |
|---|---|---|
| `OOS-DUR-01` | Committed INSERT, UPDATE and DELETE of OOS-backed rows, including multi-chunk values, are present with exact values after `kill -9` and restart. | assert |

The statement is quoted in full. It cites `OOS-CONTEXT.md` at revision
`f6543de680b91ae357466b72a983f982892859cd`, content hash
`sha256:c9daf3c4ed25e16356ebf3c79c55f6bb7391d76c5664675a9aaf55cd5ac11698` (§4 Recovery &
Replication Invariants, invariant 1, WAL completeness), and is `assertable` with `gap_kind: null`.

**Claim withdrawn in revision 8: `OOS-REP-07`.** Revisions 1 to 7 also listed `OOS-REP-07` and
quoted it as "…is stored as a chain of chunk records and is read back complete and
byte-identical". The catalogue statement in full is: "A value larger than one page's maximum
single-chunk payload is stored as a chain of chunk records, **inserted tail first**, and is read
back complete and byte-identical; **`total_data_length` excludes every chunk header**." Neither
emphasised clause is assertable by this case: chunk insertion order is not observable at either
seam, and `total_data_length` is observable only through `Oos_recs_sumlen`, which section 3
deliberately declines to assert while the pinned 16-byte chunk header differs from the accepted
24-byte one (`OOS-REP-05` / CBRD-26950). A PASS recorded against a statement quoted with its hard
half removed is the overclaim the independent review's F2 named, and the review's option 1 —
drop the claim — costs the case nothing, because `OOS-DUR-01`'s own statement already mandates
"including multi-chunk values". So the multi-chunk row stays and this oracle claims exactly one
requirement. `OOS-REP-07` is a `public-sql` requirement in the catalogue and belongs to the
campaign's public Representation ticket (18), which owns the single-to-multi-chunk boundary.

## 2. Fixture and why each size was chosen

Schema is ticket 11's **schema A** verbatim, so the published boundary table applies without
re-derivation:

```sql
CREATE TABLE oos_dur01 (id INT, v BIT VARYING);
```

Sizes come from [`derive_case_sizes.py`](derive_case_sizes.py), which imports ticket 11's
`oos_boundaries.py` rather than restating its arithmetic, and computes every boundary
**twice** — once with the pinned accounting (gate `DB_PAGESIZE/4` = 4,086, 16-byte inline
stub, 16-byte chunk header) and once with the normative one (CBRD-27057 four-record target
= 4,060, CBRD-26950 24-byte stub and chunk header). A size is used only where the two agree,
which is what makes the placement **assertable** rather than merely observed: inside a band
where they disagree the requirement is a Capability gap of the pinned engine and its engine
output must never become an expectation (ticket 11 §5.2).

| Row | N (logical bytes of `v`) | Pattern | Placement | Why this N |
|---:|---:|---|---|---|
| `id = 1` | 4,036 | `AA` | OOS, 1 chunk | Smallest N demoted under **both** accountings (pinned 4,036; normative 4,012). Disputed demotion band \[4,012, 4,035] is avoided by taking the larger. |
| `id = 2` | 16,284 | `BB` | OOS, 2 chunks | Smallest N needing two chunks under **both** (pinned 16,284; normative 16,276). Disputed split band \[16,276, 16,283] avoided the same way. This row exercises `OOS-DUR-01`'s "including multi-chunk values" clause; the `OOS-REP-07` claim it carried until revision 7 is withdrawn (section 1). |
| `id = 3` | 4,011 | `CC` | inline | Largest N that stays inline under **both** (one below the *normative* trigger 4,012, not below the pinned 4,036). The inline comparator that separates OOS-specific failure from general SQL or harness failure. |
| `id = 4` | 4,036 | `DD` | OOS, 1 chunk | Same size as `id = 1`; exists only to be deleted and committed before the crash, so that the committed DELETE half of `OOS-DUR-01` is covered. |

After the committed INSERT, the update of `id = 1` rewrites `v` to pattern `EE` at the same
N = 4,036 (M1 UPDATE always allocates a fresh chain, OOS-CONTEXT §3), and `id = 4` is
deleted. Both are committed before the crash.

`BIT VARYING` is used per the context's testing principles: CUBRID compresses strings, so
only VARBIT gives an exact on-disk size. `CAST(REPEAT('AA', N) AS BIT VARYING)` yields
exactly N bytes; a distinct two-hex-digit pattern per value makes cross-row mixing
detectable.

## 3. Derived quantities

Serialized length of an N-byte `BIT VARYING` is `ALIGN(5 + N, 4)` for N ≥ 32
(`or_varbit_length_internal`, 5-byte prefix), which is exactly what `DISK_SIZE()` reports —
ticket 11 §5.2 confirms `DISK_SIZE` is the logical serialized size and **not** a placement
oracle.

| N | `OCTET_LENGTH(v)` | `BIT_LENGTH(v)` | `DISK_SIZE(v)` |
|---:|---:|---:|---:|
| 4,036 | 4,036 | 32,288 | 4,044 |
| 16,284 | 16,284 | 130,272 | 16,292 |
| 4,011 | 4,011 | 32,088 | 4,016 |

**MD5 digests.** CUBRID's `MD5()` of a `BIT VARYING` digests its lowercase hexadecimal form,
so the expected digest of pattern `P` repeated N times is the MD5 of the ASCII string
`lower(P)` repeated N times. Each digest below was computed twice and independently of the
engine — once in Python (`hashlib.md5`) and once with coreutils
(`yes <p> | head -n N | tr -d '\n' | md5sum`) — and the two agree:

| Value | Pattern × N | Expected MD5 |
|---|---|---|
| `id = 1` **after** the update | `EE` × 4,036 | `b3f48c085d883a5c1796afa474ef8433` |
| `id = 1` before the update (must **not** survive as the current value) | `AA` × 4,036 | `44c5c2a376ce6478c16b3b446e60e806` |
| `id = 2` | `BB` × 16,284 | `02b6cc6daae92bb402016271b353e192` |
| `id = 3` | `CC` × 4,011 | `42db23afb2f04edfa44f7a5f840e7a09` |
| `id = 4` (deleted; must be absent) | `DD` × 4,036 | `c4bff33d746f9ee5163a2f5151a446e7` |

The case recomputes these at run time with the same coreutils pipeline rather than hard-coding
them, so the oracle stays correct if a future maintainer changes a pattern or a size; the
table above is the fixed reference this run is judged against.

**OOS chunk count after the committed INSERT**, before any UPDATE or DELETE:

```
id=1  1 chunk   id=2  2 chunks   id=3  0 (inline)   id=4  1 chunk   ->  Oos_num_recs = 4
```

This count is identical under the pinned and the normative chunk header, so it is asserted.
`Oos_recs_sumlen` is **not** asserted: at the pin it is 24,444 (= 4,044 + 16, + 16,292 + 2×16,
+ 4,044 + 16) but the accepted 24-byte header would give 24,476. The divergence is the
`OOS-REP-05` / CBRD-26950 Capability gap; the number is recorded as an observation only.

**OOS chunk count after recovery** is asserted as a range, `3 ≤ Oos_num_recs ≤ 5`, not a
point value: the live rows hold 3 chunks (`id = 1` one, `id = 2` two), and the two dead chains
— the pre-update chain of `id = 1` and the chain of the deleted `id = 4` — survive until
vacuum reclaims them (OOS-CONTEXT §4 invariants 3 and 4), which is asynchronous in
client-server mode. Asserting a point value here would make the case flaky for a reason that
has nothing to do with durability.

## 4. Transaction-state model and the operation journal

Both deadlines are set so that a run which reaches both of them still finishes inside the
campaign's 120-second per-case cap once setup, workload and verification are added; measured
on the pinned engine they are under a second and about three seconds. A reached deadline
captures schedule, log and process evidence, ends the attempt and cannot report success.

`OOS-DUR-01`'s authority note requires a verified durable-commit configuration and judging
the recovered database against the permitted transaction states from an external journal,
never against "a missing acknowledgement means rollback".

**Verified durable-commit configuration** (asserted from `cubrid paramdump -S` before the
workload, so a future default change cannot silently weaken the case):

| Parameter | Required value | Why |
|---|---|---|
| `async_commit` | `n` | With async commit the log flush may lag the acknowledgement, so an acknowledged commit would not be required to survive. |
| `group_commit_interval_in_msecs` | `0` | Group commit would likewise defer the flush past the acknowledgement. |
| `auto_restart_server` | `no` | Otherwise `cub_master` restarts the killed server on its own and recovery happens before the case asks for it; the restart must be the case's own action. |

**Journal.** Every DML statement writes a `request` line before `csql` is invoked and an
`ack` line after `csql` returns, carrying the statement tag, the affected-row count parsed
from the output and the `csql` exit status. Three transactions are acknowledged before the
crash:

| Txn | Statements | Acknowledged | Permitted state after recovery |
|---|---|---|---|
| T1 | INSERT ids 1–4, COMMIT | yes | **committed** — all four rows durable |
| T2 | UPDATE id 1 to `EE`, COMMIT | yes | **committed** — `id = 1` holds `EE` |
| T3 | DELETE id 4, COMMIT | yes | **committed** — `id = 4` absent |

The crash is taken **after** T3's acknowledgement, so there is no transaction of unknown
outcome in this attempt and the permitted state is a single one. `OOS-DUR-03` (interrupted
commit, outcome genuinely unknown) is a different requirement and a different case; this
oracle deliberately does not claim to cover it.

## 5. Expected assertions, in order

The case emits exactly these. A `SKIP` line is written into the CTP result file on the
assertion's own number, in a form that contains neither `OK` nor `NOK`, so a skip is visible
but never counted as a pass (CTP fails a case iff a result line contains the substring
`NOK`). Counting executed assertions therefore means matching `OK|NOK` explicitly:
`grep -cE "^<case>-[0-9]+ : (OK|NOK)"`, which excludes the SKIP lines that share the
numbering.

| # | Name | Expectation | Skips when |
|---:|---|---|---|
| 1 | `engine_identity_recorded` | `cubrid_rel` output captured into the journal and non-empty | — |
| 2 | `database_page_size_is_16384` | `SHOW HEAP OOS`/`spacedb` page size, or the createdb argument, reports 16,384 | — |
| 3 | `durable_commit_configuration_verified` | the three parameters above hold | — |
| 4 | `insert_transaction_acknowledged` | journal: T1 request and ack present, 4 rows affected, csql status 0, no `ERROR:` in output | — |
| 5 | `oos_activation_after_insert` | `Has_oos_file = 1` and `Oos_num_recs = 4` | `SHOW HEAP OOS` not supported by the build |
| 6 | `update_transaction_acknowledged` | journal: T2 ack, 1 row affected | — |
| 7 | `delete_transaction_acknowledged` | journal: T3 ack, 1 row affected | — |
| 8 | `server_crashed_by_kill_9` | `cub_server`/`cub_pl`/`cub_master` pids extracted (extraction failure is a failure, never a silent pass), killed, and gone within 30 s | — |
| 9 | `server_restarted_within_deadline` | `cubrid server start` succeeds and a probe query answers within 60 s | — |
| 10 | `recovery_redo_phase_replayed_log_records` | the server's own error log for the database (`$CUBRID/log/server/<db>_*.err`, regular files only) carries exactly one more `Log recovery: REDO Phase is started` line than it did before the crash, and that line's `Log records to redo` is at least 1; the redo page and record counts and the UNDO line's `transactions to undo` are journalled as observations, and the log files are copied into the evidence directory on every run | — |
| 11 | `recovered_row_count_is_3` | `SELECT COUNT(*)` = 3 | — |
| 12 | `recovered_value_id1_single_chunk_oos` | MD5 `b3f48c…`, OCTET_LENGTH 4,036, BIT_LENGTH 32,288, DISK_SIZE 4,044, equality flag 1 | — |
| 13 | `recovered_value_id2_multi_chunk_oos` | MD5 `02b6cc…`, OCTET_LENGTH 16,284, BIT_LENGTH 130,272, DISK_SIZE 16,292, equality flag 1 | — |
| 14 | `recovered_value_id3_inline_comparator` | MD5 `42db23…`, OCTET_LENGTH 4,011, BIT_LENGTH 32,088, DISK_SIZE 4,016, equality flag 1 | — |
| 15 | `committed_delete_survived_recovery` | no row with `id = 4` | — |
| 16 | `oos_activation_after_recovery` | `Has_oos_file = 1` and `3 ≤ Oos_num_recs ≤ 5` | `SHOW HEAP OOS` not supported |
| 17 | `checkdb_after_recovery_is_clean` | `cubrid checkdb -S` exits 0 and prints no failure text | — |
| 18 | `debug_oos_log_records_chain_delete` | after a standalone-mode update of `id = 1`, `$CUBRID/log/oos.log` contains an `oos_delete` line | release build: `oos_debug` is compiled out under `NDEBUG` |

**Expected assertion count: 18** (17 until revision 8). On the pinned **release** build, 17 are
executed and #18 is skipped; on the pinned **debug** build all 18 are executed. A skipped assertion
takes its own number in the result file, so the file stays contiguously numbered 1 to 18 the way `write_ok`
numbers it, but the line reads `SKIP` rather than `OK` or `NOK`. Unlike the SQL runner, the CTP
shell runner does give a real per-assertion counter — the `.result` file has one
`<case>-<n> : OK|NOK` line per assertion and `feedback.log` reproduces them — so
`executed` is measured, not derived. (This closes, for the shell seam, the counting defect
ticket 13 recorded as `P4`.)

**Why #10 exists, and what it does not claim.** Assertion 9 shows a server came back up; it does
not show that recovery replayed anything. Had every dirty page been flushed before the `kill -9`,
assertions 11 to 17 would pass on an engine that never logged an OOS operation — which is the
invariant this case cites — and the specification rules that inference out explicitly ("proof of
an insert path never certifies an unrelated scan, recovery or vacuum path"). The engine writes
its recovery progress at NOTIFICATION severity, on release and debug builds alike, into
`$CUBRID/log/server/<db>_<date>_<time>.err` (`log_recovery.c` through `cubrid.msg` entries 1128,
1129 and 1296 to 1301). Two facts shape the reader and are measured rather than assumed: a fresh
database's first start writes no recovery lines, and a restart within the same minute as the
first start appends to the same file. So the case counts REDO-phase lines across the database's
regular `.err` files before the crash and asserts the restart added **exactly one** — a stale
phase must not be read as the restart's — whose `Log records to redo` is **at least 1**, because a
REDO phase with nothing to replay is precisely the ambiguity the assertion exists to remove. The
exact counts are observations (the pinned release run seen by the independent review replayed 83
records over 2 pages; the number depends on what the workload logged and is not portable across
layouts). The `transactions to undo` count is journalled and not asserted: `OOS-DUR-02` is not
claimed, and the honest statement `OOS-DUR-01` can make about its sibling's territory is to
record the engine's own count. `server_restart.out` is not a substitute: it holds the utility's
unconditional "This may take a long time" banner and is byte-identical to `server_start.out`.

### The case-level outcome

CTP decides PASS or FAIL per case and has no third verdict, so assertion-level skips are not
enough on their own: on a build without `SHOW HEAP OOS`, assertions #5 and #16 would both
skip and the case would still report `[OK]` — a pass with **no activation evidence at all**,
which is precisely what the campaign forbids ("a case counts as OOS coverage only when
correct results are paired with evidence that its intended OOS path executed").

The case therefore states a campaign outcome of its own, in the result file and in
`<evidence>/case_outcome`, which the runner surfaces and the manifest takes its case outcome
from:

| Condition | Case outcome |
|---|---|
| any assertion failed | `FAIL` |
| every executed assertion passed but `SHOW HEAP OOS` never answered | `SKIP`, with the reason that durability was proved and the out-of-row path was never observed |
| every executed assertion passed and the out-of-row path was observed | `PASS` |

On both pinned builds the outcome is `PASS`. The `SKIP` branch is what keeps a future run on
a non-OOS build from being counted as coverage.

### Why #18 uses the standalone path

Ticket 11 §6 found that at the pin the debug `oos.log` carries **delete-side lines only**:
the SQL INSERT path calls `oos_insert_many`, which has no `oos_debug` call. The probe for
this ticket added a second fact: in **client-server** mode a committed UPDATE and DELETE
wrote nothing to `oos.log` within three seconds, because the chains are reclaimed by vacuum
asynchronously; the same statements in **standalone** mode wrote `heap_recdes_get_oos_oids`,
`oos_delete` and `oos_delete_chain` lines synchronously, through the SA_MODE eager path
(`heap_oos_delete_unreferenced`, OOS-CONTEXT §4). So assertion #18 runs its update in
standalone mode after all durability assertions have finished, which makes it deterministic
instead of racing vacuum. It is an evidence assertion, not a durability assertion: it runs
last and mutates only data the case has already judged.

## 6. What this case deliberately does **not** claim

- **Not** `OOS-DUR-02` (uncommitted work undone): every transaction here is acknowledged
  before the crash.
- **Not** `OOS-DUR-03` (interrupted commit): the crash is taken after the last
  acknowledgement, so no outcome is uncertain.
- **Not** `OOS-DUR-05` or the reclaim requirements: the case asserts a *range* for the
  post-recovery chunk count precisely because it does not test when vacuum reclaims.
- **Not** the normative identity layout: `Oos_recs_sumlen` is recorded, never asserted, while
  CBRD-26950 is unmerged at the pin.
- **Not** a claim that the engine is the pinned one. The case records `cubrid_rel` into its
  journal and asserts nothing about it, so the same case is meaningful on a later build; the
  pin is asserted by the campaign wrapper and recorded in the manifest, which is where engine
  identity belongs.

## 7. Checker validation

**The whole-value oracle.** `cases/make_negative_control.sh` derives a wrong-expectation
copy of the case by exactly two documented mutations and refuses to emit anything if either
stops applying, so the control cannot drift away from the case it validates. The defect is
one byte: the expected size of the multi-chunk row becomes 16,283 while the row still holds
16,284, which is the smallest change that still exercises the multi-chunk path. It must
produce a failed assertion and a failed case.

The generator is never itself run as a case, because CTP discovers a case iff the file name
equals its **grandparent directory name** plus `.sh` (`Dispatch.getAllTestCaseScripts`:
`find … -name "*.sh" | awk -F / '{ if ($(NF-2)".sh" == $NF) print }'`) — the directory
being called `cases` is not what makes a script a case. `make_negative_control.sh` does not
match `cbrd_26659_oos_dur01.sh`, which is the same reason the 272 other helper scripts that
live inside a `cases/` directory in this repository are never run. Non-discovery is
demonstrated in `discovery.txt` by running that exact command over the whole issue bucket.
The generated control is written outside the scenario root the launcher is pointed at, so
that copy is out of reach too.

**The acknowledgement parser.** The case's second checking mechanism is the parser that
turns `csql` output into the affected-row and error counts `assert_txn` judges a committed
transaction by. Its controlled failure examples are in
`tools/checker_validation_journal.sh` (output: `checker-validation-journal.txt`): a SQL
error and a connection failure must both yield `affected=0` with `errors≥1`. That matters
because `csql` was observed exiting 0 while printing `ERROR: Failed to connect`, so a parser
that read those shapes as success would let a transaction that never ran be journalled as
acknowledged.

**The recovery-log reader (revision 8).** The case's fourth checking mechanism turns the server's
error log into the verdict of assertion #10. Its controlled failure examples are in
`tools/checker_validation_recovery_log.sh` (output: `checker-validation-recovery-log.txt`): the
real five-line recovery sequence from a pinned release run is accepted with pages 2 and records
83, and each of these is rejected — the analysis lines with no REDO phase, an empty log, a REDO
phase with zero records, a second REDO phase when none existed before (a stale phase must not
pass as the restart's), a line whose counts do not parse, and the utility's unconditional
"This may take a long time" banner. Two REDO phases with one counted before the crash are
accepted with the last line's counts. `tools/recovery_log_discriminates.sh` shows the shapes
discriminate by running them against the code they were written to catch: revision 7's
post-restart judgement (exit status 0 and a probe query answered) passes every rejected shape,
because it never read the log (output: `recovery-log-discriminates.txt`).
