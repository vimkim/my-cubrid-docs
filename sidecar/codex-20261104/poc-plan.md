# Build and judge the Sidecar POC

The user wants a real-engine demonstration of the [proposed design](design.md).
This plan is prepared for approval on 2026-11-04, Asia/Seoul. Nothing below is
an engine test result. The baseline is CUBRID/CUBRID commit
`e64a04a79a5842827a124b3f8313516d0da2594c`.

The proposed approval would cover the implementation phases below on
`sidecar-codex` with local commits. It includes disposable test databases and isolated processes.
It excludes deployment, production data, pushing branches, and upgrade of
existing databases. A separate merge approval is required for `develop`.

## Design verification before engine approval

The [protocol models](formal-verification.md) and their rerunnable skill are
implemented. They verify finite design state machines and deliberately broken
variants. They do not implement `accept.py` or close any real-engine phase
below. Engine implementation still requires the handoff's explicit approval.
Keep the legacy heap-vacuum finding separate from passing proposed guards.

## Build the checker before the storage

Implement `contrib/benchmarks/sidecar/accept.py` as the single acceptance entry
point. It does not exist at this design checkpoint. Its planned CLI is:

```sh
python3 contrib/benchmarks/sidecar/accept.py --case all --baseline-ref e64a04a79a5842827a124b3f8313516d0da2594c --candidate-ref HEAD --root /tmp/sidecar-poc-772
```

The same command accepts each case name in the table below instead of `all`.
The driver records exact Git identities, dirty state, executable hashes,
toolchain, configuration, fixture seed, server PIDs, query results, and raw
observations. It creates separate source worktrees, release installations,
databases, and port sets. Its containment check rejects an existing unrelated
database or process. Logs go to files. It never opens a browser.

The intended exit codes are 0 for every required predicate verified, 1 for an
observed failure, and 2 for missing evidence or inconclusive measurement.
It emits one JSON result per case and an overall result. Skipped cases cannot
make `all` pass. The driver is proposed work, not a command verified today.

Existing engine commands to use behind the driver, after dependency and
environment preparation, are:

```sh
cmake --preset release
cmake --build --preset release
```

Both builds use matching compiler, flags, durability, page size, locale,
concurrency, and hardware. The baseline receives no Sidecar changes. Shared
fixture and measurement code must produce equivalent logical inputs on both.

## End each phase with observable evidence

| Order and case name | Work and exact pass predicate |
| --- | --- |
| 1. `lifecycle` | Model actual hot/chunk transaction identities, repeated overwrite, savepoint rollback, old snapshots, and vacuum. Run forced schedules against real heap allocation and restart. Every snapshot-visible reference has complete matching chunks. Slot, byte, and page protections each have a failing unsafe mutation. A model pass alone cannot close an engine scheduling gap. |
| 2. `storage` | Implement VARCHAR and VARBIT, IDs, chunk relation, compact record and typed row access. Test NULL, empty, multibyte strings, binary zeros, threshold boundaries, multi-page values, two cold columns, and a residual hot `REC_BIGONE`. Compare exact canonical values and row counts with an ordinary-table oracle. Reject partial or malformed chunk sets. |
| 3. `recovery` | Crash after chunk creation, after old-chunk deletion, after parent publication, during index changes, before and after logical-image completion, at commit, and during vacuum. Restart twice. Committed values and index answers equal the oracle. Uncommitted changes disappear. Repeated restart changes no result. Run rollback-to-savepoint after two overwrites and a hot-only update. |
| 4. `reclamation` | Hold an old snapshot over overwrite and DELETE. It reads the old full value while a new snapshot reads the committed replacement. Finish snapshots and drain vacuum. The quiescent checker finds no incomplete referenced ID, no unowned live ID, and no retired chunk or index entry past the vacuum horizon. Repeat churn and show reclaimed space is reusable before unjustified file growth. |
| 5. `transport` | Exercise full object fetch and load-unload-load, compact, representation change, drop, truncate, failed DDL, triggers, and standalone DML. Test simple, prefix, function, composite, and unique indexes, including uniqueness failure and rollback. Exact values and index queries match an ordinary-table oracle. No internal reference reaches a legacy client decoder. |
| 6. `history` | Emit complete images before old chunks become invisible to the writer. Savepoint-rolled-back operations emit no HA or CDC event. After live chunk vacuum and source restart, CDC and flashback return the exact supported old/new values from retained WAL. A manifest with a missing fragment fails explicitly. Every descriptor dependency remains retained until consumers advance. |
| 7. `ha` | Give source and replica different allocation histories. Stop the applier, overwrite and delete source values, vacuum, restart, and make the source server unavailable. Resume from retained archives. Full replica values equal the expected committed source state. Crash the replica before and after local apply commit and checkpoint. Resume without loss or duplicates. Include two surviving operations in one source transaction; concurrent readers must see the whole transaction after local commit. Include optional applier SQL logging. |
| 8. `encryption` | Enable TDE, change its algorithm, restart, archive, back up and restore. Confirm metadata and successful decryption. Scan data files, live/archived WAL, and backup for a planted long marker with no expected plaintext occurrence. Include hidden indexes and new page-less logical images. Report this as exercised encryption behavior, not cryptographic proof. |
| 9. `compatibility` | The exact unmodified baseline binary and baseline log readers refuse the new database/log format before writable recovery or apply. Record refusal and unchanged files. New binary reads its supported ordinary databases. Mixed-version HA and in-place upgrade remain unsupported by this POC. |
| 10. `projection` | For matched wide fixtures, a forced and verified heap scan returns equal small-column aggregates, performs zero cold-chunk and chunk-index page fixes, and touches strictly fewer distinct total data pages than baseline. Count heap, overflow, and chunk data pages together. Report all index pages separately and include them in a second total to expose hidden lookup costs. |
| 11. `unused` | For both never-enabled tables and enabled tables with every value inline, each INSERT, SELECT, UPDATE, and DELETE workload has a candidate/baseline throughput ratio whose lower 95% paired confidence bound is at least 0.95. The interval width must be at most 0.02. Equal results and plans are prerequisites. Insufficient precision is INCONCLUSIVE. |
| 12. `regressions` | Native focused SQL, shell, and complete ordered medium scenarios have zero failures and exactly the intended testcase set. New Sidecar cases cover the preceding behaviors. Full-corpus CI remains required before release and is reported separately. |

The driver must first run on an ordinary baseline fixture and reject an
intentionally wrong expected value, absent page events, and incomplete result
files. It must also reject an injected slowdown greater than 5% in each
unused workload. These negative controls prevent an empty or insensitive run
from satisfying a case.

Exercise reentrant SQL functions and trigger-driven writes before consuming
later requested attributes. Materialize the requested set before crossing a
callback or same-transaction mutation boundary. A saved snapshot cannot by
itself retain own-deleted chunks.

## Make the lifetime audit distinguish logical and physical garbage

At a quiescent snapshot after all test transactions finish, enumerate every
current external field and every visible chunk ID. Each external field must
have exactly one owner, ordinals `0..chunk_count-1`, and exactly its declared
byte length. Each visible chunk set must have an owner.

Before vacuum, MVCC-dead chunks are not logical orphans. Record them
separately. After the visibility horizon advances and vacuum drains, scan
physical chunk records and index entries to confirm that eligible dead data
was removed. Diagnose leftover records separately from empty reusable pages.
Ordinary heap policy may retain empty pages. It need not return identical
filesystem bytes or shrink a volume. The churn check must show reuse and
explain any retained capacity.

The checker must also validate transactionally owned hidden files after
crashed or rolled-back schema changes. Merely counting current SQL rows does
not detect orphaned files.

## Define page reads before counting them

Instrument foreground page fixes with query identity, database identity, file
generation, volume, page ID, and page category. The instrumentation is POC
work and must be absent from the throughput build. Compare instrumented
baseline and candidate only with each other for page counts.

Use wide fixtures with 8 KiB inline-capable values, 64 KiB values, multiple
cold columns, and interleaved small and large rows. Each has an unindexed
`hot_value` column. Compare `select sum(hot_value) from sc_io;` and verify the
actual plan scans the heap. A covering-index plan invalidates this case.
Read full large values separately to prove equal content and observe their
cost. A no-requested-cold-column query must never touch the hidden chunk index.

Use distinct data-page identities as the hard metric. Record TRACE `fetch`
and `ioread` as supporting operation and physical-read metrics. A warm-cache
`ioread=0` is insufficient evidence. Run both controlled cold-start and warm
sessions. Background vacuum and index pages remain separately attributable.

## Measure unused cost without mixing in enabled overhead

Reuse the existing ordinary scan and UPDATE fixtures before adding new ones.
The inspected retained implementation is under
`/home/vimkim/gh/cb/CBRD-27785-oos-read-performance/contrib/benchmarks/oos-performance`.
Its `ordinary.py` and `bench.py` do not cover the complete acceptance matrix.
The new driver supplies INSERT and DELETE, interleaving, and uncertainty.

Use at least twelve measured pairs per operation after two warmups. Alternate
baseline/candidate and candidate/baseline order. Restore equivalent database
state between samples. A sample is committed operations per wall-clock
second for an identical batch. Bootstrap the geometric mean of paired ratios
with a recorded seed. Extend runs when precision is insufficient. Never
convert an inconclusive result into a pass by choosing a favorable sample.

The user's hard budget applies when every value remains in the heap. Require
both never-enabled tables and enabled tables whose values remain inline to
pass, and report their results separately. Also report
enabled hot-update latency, WAL bytes per committed operation, cold lookup
cost, and full-row reads. They have no approved numerical target yet. Large
WAL amplification is a design tradeoff to show the user, not hide in the
unused-feature result.

Use `benchmark-checklist` and `principle-explain-the-number` before trusting
or reporting these measurements. Establish the limiter and exclude client
CPU, changed plans, background contention, and different durability settings
as alternative explanations.

## Run focused regressions through their native workflows

Follow `cubrid-test-sql-run`, `cubrid-test-shell-run`, and
`cubrid-test-medium-run` for contained configurations and artifact verdicts.
Existing native execution interfaces are:

```sh
TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 testkit sql -c "$CONF"
TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c "$CONF"
TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 testkit medium -c "$CONF"
```

`CONF` is produced by each workflow, not a configuration prepared in this
session. Candidate starting assets include SQL
`sql/_29_recovery/cases/update_overflow_rollback.sql`, SQL
`sql/_36_guava/cbrd_25717/cases/cbrd_25717_overflow_record.sql`, the complete
medium directory `medium/_05_err_x`, and private shell
`shell/_40_guava/cbrd_26857/cbrd_27120_recovery/cases/cbrd_27120_recovery.sh`.
These are source-discovered leads, not proof of Sidecar coverage.

Add explicit Sidecar fixtures rather than silently changing ordinary expected
results. Before release, run the full project SQL, shell, medium, and available
HA/recovery corpus. The local POC cannot claim those CI results before they
exist. Publication or external CI that needs a push remains subject to the
handoff's separate push authorization.

## Stop conditions and review checkpoints

Do not proceed past a phase with a violated invariant, unexplained value
disagreement, replay failure, leaked live value, or unsupported decoder.
Resolve whether a failure is model drift or engine behavior using real source
and a reproduced schedule. An ordinary heap defect found by this work gets
its own reviewed fix before the next phase relies on it.

At the storage/recovery checkpoint, review the implementation against the
approved shapes. If it needs a new lifecycle protocol or cannot provide
complete rollback-aware historical images, revise the design before adding
performance work. At the final checkpoint, report every predicate with its
command, artifacts, exact commit, and VERIFIED, NOT VERIFIED, or INCONCLUSIVE
verdict. The POC succeeds only when all local predicates are verified. Release
readiness additionally requires the full regressions and deployment review.
