# CBRD-26659 — Representative timings and tier placement (ticket 17)

> Observed: 2026-09-18 (KST), on `dev2`. Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`,
> re-pinned without the unit-test seams by ticket 41 (`release_gcc_nounit`, `debug_gcc_nounit`);
> instrumentation install `oos-instr-f4299ac0c/debug_gcc_nounit`, patch set `t16-set1`; normative
> context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…`.
> Author: Claude Opus 5, for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 17.
> Records: [`evidence/ticket17/`](evidence/ticket17/) — four manifests, twelve attempt records, twelve
> replay-bundle indexes, the coverage matrix, the twelve configuration-domain cells, the measurement
> set, the placement model and the probes' outputs.
> Companions: [engine baseline](CBRD-26659-engine-baseline_f4299ac_claude.md),
> [re-pin](CBRD-26659-repin-without-unit-test-seams_f4299ac_claude.md),
> [tooling](CBRD-26659-manifest-matrix-replay-tooling_f4299ac_claude.md),
> [injection-site validation](CBRD-26659-injection-site-validation_f4299ac_claude.md),
> [public tracer bullet](CBRD-26659-public-tracer-bullet_f4299ac_claude.md),
> [private tracer bullet](CBRD-26659-private-tracer-bullet_f4299ac_claude.md),
> [SQL operations](CBRD-26659-sql-operations_f4299ac_claude.md).
> Revision 2, 2026-09-21: the specification's independent review of this record
> ([`CBRD-26659-ticket17-independent-review_f4299ac_claude.md`](CBRD-26659-ticket17-independent-review_f4299ac_claude.md))
> is closed by campaign ticket 49; what changed is in §15, and every section it touched says so in place.

Vocabulary follows the [docs glossary](../../CONTEXT.md).

## 1. What now exists

| Item | Where |
|---|---|
| The tier-placement table, sixteen workloads | §6, regenerable from [`evidence/ticket17/tier-placement-model.json`](evidence/ticket17/tier-placement-model.json) |
| The configuration domain, twelve cells, each proven runnable | §3, [`evidence/ticket17/config-domain/`](evidence/ticket17/config-domain/) |
| Every measured quantity the placement rests on | [`evidence/ticket17/measurements.json`](evidence/ticket17/measurements.json) |
| Configuration-domain probe and the module that judges it | [`tools/config_domain_probe.sh`](tools/config_domain_probe.sh), [`tools/config_domain.py`](tools/config_domain.py), checker [`tools/selftest_config_domain.py`](tools/selftest_config_domain.py) |
| Placement computation and its checker | [`tools/tier_placement.py`](tools/tier_placement.py), [`tools/selftest_tier_placement.py`](tools/selftest_tier_placement.py) |
| Resource sampler (CPU in logical CPUs, resident memory, disk usage) | [`tools/resource_sampler.py`](tools/resource_sampler.py) |
| Seeded out-of-row churn probe | [`tools/seed_cost_probe.py`](tools/seed_cost_probe.py) |
| Multi-session barrier **mechanism** probe | [`tools/barrier_cost_probe.sh`](tools/barrier_cost_probe.sh) |
| The private suite's multi-session barrier **scenario**, run twice at the seam (ticket 49, §5.6) | [`evidence/ticket49/`](evidence/ticket49/) — `att-T49-0001`, `att-T49-0002`, both halted by the isolation tool's own timeout; a Capability gap for its cost |
| Per-case timing extractor over every retained CTP bundle | [`tools/extract_ctp_timings.py`](tools/extract_ctp_timings.py) |
| Four campaign manifests, twelve attempt records, twelve bundle indexes, one matrix | [`evidence/ticket17/`](evidence/ticket17/) |
| Replay bundles and probe outputs | `~/.cub/campaign/cbrd-26659/ticket17/` (3.8 GiB disk usage, of which 3.0 GiB is the nine retained OOS-path-evidence databases) |

Nothing was pushed. Neither testcase worktree was modified: both are clean at `35c815943` (public)
and `c4fe45173` (private), the commits every invocation records.

## 2. What was measured and what was derived

Everything in §3 to §8 was measured on `dev2` on 2026-09-18 unless a row says `derived`. The host has
80 logical CPUs, 251 GiB of memory and 1.3 TiB free under `/home`, so the campaign's 8 CPU / 16 GiB /
100 GiB ceilings are self-imposed admission limits and not host limits — which matters for §8.

Four things are **derived, not measured**, and each says so in the table and carries its derivation:

1. **The four required multi-session schedule families have no case at either seam, and the
   barrier scenario the private suite does have could not be timed to completion.** Criterion 1
   asks for a multi-session barrier scenario to be timed. The first revision of this record said
   none existed in either suite; that was wrong (review F1, corrected by ticket 49):
   `shell/_06_issues/_18_2h/bug_bts_22449` is a four-participant, coordinator-released barrier
   scenario driven through CTP's isolation ctltool, present in the campaign's pinned CTP tree.
   Ticket 49 ran it at the shell seam twice; in both runs the schedule halts at its fourth
   participant and is killed by the tool's own timeout (§5.6), so the cost of a *completed* schedule
   is a **Capability gap** at the pin. The four families themselves are a **Delivery gap** (§9, F4),
   ticket 23's to close, and the §6 row for them keeps the figure derived from the *mechanism*
   probe decision ticket 05 requires — participants that acknowledge an explicit barrier and a
   coordinator that releases them — with the review's caveat that the probe measured uncontended
   coordination, a floor rather than a schedule (§5.6).
2. **The public suite projected to forty cases**, derived from the measured per-case cost and the
   measured launcher cost.
3. **HA replica correctness** and **4. CDC/flashback and encryption**: no scenario exists and nothing
   about them has been measured by this campaign. Their rows carry explicit *lower bounds*, not
   estimates, and the tickets that write those scenarios owe the measurement.


## 3. The configuration domain, re-verified against the pinned engine (criterion 2)

The specification's *Engine baseline* section is explicit that "a build directory's presence is not
proof of a matching binary", so each of the twelve combinations was **run**, not inspected. One probe
per cell creates a database at the declared page size with the pinned install whose library hashes
`campaign_env.sh` has already verified, inserts one 4,000-byte value, reads it back and asks the
engine for its own view of both facts: `cubrid spacedb` for the page size it actually created, and
`SHOW HEAP OOS` for whether the out-of-row path ran. A cell counts as proven only when it names the
engine commit and the sha256 of `libcubrid.so`, `libcubridsa.so`, `csql` and `cub_server`, the page
size reads back as declared, the OOS path was reached, and the value came back byte-identical —
`tools/config_domain.py` owns that rule so the probe cannot decide it about itself, and
`tools/selftest_config_domain.py` plants each way of faking it and requires the rule to catch it.
Since ticket 49 (review F4) the rule also verifies what the cell names: the two library hashes must
be ticket 41's pinned values (`campaign_records.LIBRARY_HASHES`, the same home `campaign_env.sh`
gates a run with) and `cubrid_rel`, the one field read out of the running binary, must name the
pinned commit and the cell's build — the first revision only checked that four hashes were present,
so a cell naming a foreign binary would have read as proven.

| Page size | Build | Run mode | Verdict | Engine | OOS-path evidence | Value | Wall |
|---|---|---|---|---|---|---|---:|
| 4 KiB | release | standalone | runnable | `1bbbe446…` | `Has_oos_file` 1, `Oos_num_recs` 2, `Oos_recs_sumlen` 4040 | byte-identical | 3.33 s |
| 4 KiB | release | client-server | runnable | `1bbbe446…` | `Has_oos_file` 1, `Oos_num_recs` 2, `Oos_recs_sumlen` 4040 | byte-identical | 3.93 s |
| 4 KiB | debug | standalone | runnable | `30c52062…` | `Has_oos_file` 1, `Oos_num_recs` 2, `Oos_recs_sumlen` 4040 | byte-identical | 4.01 s |
| 4 KiB | debug | client-server | runnable | `30c52062…` | `Has_oos_file` 1, `Oos_num_recs` 2, `Oos_recs_sumlen` 4040 | byte-identical | 4.52 s |
| 8 KiB | release | standalone | runnable | `1bbbe446…` | `Has_oos_file` 1, `Oos_num_recs` 1, `Oos_recs_sumlen` 4024 | byte-identical | 3.24 s |
| 8 KiB | release | client-server | runnable | `1bbbe446…` | `Has_oos_file` 1, `Oos_num_recs` 1, `Oos_recs_sumlen` 4024 | byte-identical | 3.98 s |
| 8 KiB | debug | standalone | runnable | `30c52062…` | `Has_oos_file` 1, `Oos_num_recs` 1, `Oos_recs_sumlen` 4024 | byte-identical | 3.82 s |
| 8 KiB | debug | client-server | runnable | `30c52062…` | `Has_oos_file` 1, `Oos_num_recs` 1, `Oos_recs_sumlen` 4024 | byte-identical | 4.56 s |
| 16 KiB | release | standalone | runnable | `1bbbe446…` | `Has_oos_file` 1, `Oos_num_recs` 1, `Oos_recs_sumlen` 4024 | byte-identical | 3.95 s |
| 16 KiB | release | client-server | runnable | `1bbbe446…` | `Has_oos_file` 1, `Oos_num_recs` 1, `Oos_recs_sumlen` 4024 | byte-identical | 4.73 s |
| 16 KiB | debug | standalone | runnable | `30c52062…` | `Has_oos_file` 1, `Oos_num_recs` 1, `Oos_recs_sumlen` 4024 | byte-identical | 4.97 s |
| 16 KiB | debug | client-server | runnable | `30c52062…` | `Has_oos_file` 1, `Oos_num_recs` 1, `Oos_recs_sumlen` 4024 | byte-identical | 5.33 s |

**All twelve cells are proven runnable. There are no Capability gaps in the configuration domain.**
`python3 tools/config_domain.py check --results evidence/ticket17/config-domain` reports 12 cells read,
12 expected, 0 problems.

Two things the sweep shows beyond the verdict:

- **The chunk boundary moves with the page size, and the probe sees it.** The same 4,000-byte value is
  one chunk at 8 and 16 KiB (`Oos_num_recs` 1, `Oos_recs_sumlen` 4024) and two at 4 KiB
  (`Oos_num_recs` 2, `Oos_recs_sumlen` 4040, `Oos_page_size` 4056). A single-chunk expectation written
  at 16 KiB is therefore wrong at 4 KiB; the cases tickets 18 to 32 write must derive chunk counts per
  page size, which is what the coverage decision already requires of boundary values.
- **Standalone and client-server agree cell for cell** on every observation: same chunk count, same
  payload sum, same byte-identical readback. The two run modes differ only in cost (§4).

Install hygiene: the six client-server cells need `$CUBRID/conf/cubrid.conf` to carry the campaign's
port (the install carries the 1523 default, and port 1523 belongs to other installs). Each backed the
file up, rewrote it, restored it and verified the restoration by hash: **six `verbatim`, six
`not-applicable`** (the standalone cells never touch it). Both installs end this ticket back at
`cubrid_port_id=1523`.

## 4. The two seams have opposite cost shapes

This is the single structural fact the placement rests on, and it is measured over **57 retained CTP
bundles** across tickets 13, 14, 15, 17, 19 and 41 — not over this ticket's runs alone.
`tools/extract_ctp_timings.py` reads them.

| Quantity | Public SQL seam | Private shell seam |
|---|---|---|
| Invocations read | 18 | 39 |
| Launcher wall clock | 39–55 s, median **41 s** | 7–432 s, and it tracks the case list |
| Fixed cost per invocation (launcher minus the cases) | 38.9–54.1 s, median **40.1 s** | 1.8–11.6 s, median **4.1 s** |
| Cost of the cases themselves | 26–950 **milliseconds** per case | 11.6–111.9 **seconds** per case |
| Does the launcher cost grow with the case count? | **No.** One case 43 s, nine cases 44 s | **Yes**, almost entirely |

So the SQL seam is a fixed 40-second toll with essentially free cases, and the shell seam is a
5-second toll with expensive ones. Two consequences the case tickets inherit:

- **The public suite must be one invocation.** Ticket 13 measured 39 s for one case and inferred the
  cost was per-invocation; nine cases now measure 44 s, of which the cases are 0.66 s. Splitting the
  public suite into N invocations costs 40N seconds and buys nothing.
- **Batching the private suite buys almost nothing**, and the per-case cap is the only thing that
  binds it. The eleven-case private bucket runs cases from 1.4 s to 111.9 s (`cbrd_27229`); 421 s of
  its 432 s launcher is the cases.

**What actually grows with the public case count is the paired OOS-path evidence check.** Each one
creates its own database, starts and stops its own server: **7.33 s per checked case**, measured as
the nine-case invocation's whole wall clock (110 s) minus its launcher (44 s), over nine checks. At
nine cases the checks are already half again the launcher. They also dominate campaign storage
(§8). If tickets 20 to 22 bring the public suite to several dozen cases, batching the checks into
fewer databases is the change that matters — not splitting the CTP run.

## 5. Representative timings (criterion 1)

Five representative scenarios were asked for. Four exist and were measured. The fifth, a
multi-session barrier scenario, exists in the private suite and was run twice by ticket 49; it does
not complete at the pin, so its cost is recorded as a Capability gap (§5.6) and its row stays
derived.

### 5.1 The public tracer case, alone — `inv-T17-0001`

Ticket 13's case run alone, from a scenario copy under the ticket 17 storage so that the repository
is not touched, declared by [`tools/declarations/ticket17-timing-tracer.json`](tools/declarations/ticket17-timing-tracer.json)
(ticket 19's entry for the case verbatim; only the scenario root and the checker's database name
differ). 43 s launcher, **55 ms** case execution, 7 s paired OOS-path evidence check, 52.3 s whole
invocation including the wrapper's own setup and restore. PASS, OOS-path evidence `proven` over
`show-heap-oos`. Consistent with ticket 13's 39 s, ticket 15's 44 s and ticket 41's 40 s.

Its manifest records **`proof.verdict: failure-of-proof`**, and that is a finding about ticket 15's
tooling rather than about the case — see §9, finding F2. The case itself PASSed and its attempt
record is a clean PASS.

### 5.2 The nine-case public suite — `inv-T17-0002`

44 s launcher, **661 ms** for all nine cases (28–231 ms each), nine paired OOS-path evidence checks at
7.33 s, 111.8 s whole invocation. All nine PASS, all nine `proven`, install and worktree drift zero.

### 5.3 The private tracer case, which is also the crash-and-recover scenario — `inv-T17-0003`, `inv-T17-0004`

`cbrd_26659_oos_dur01` kills the server with `kill -9`, restarts it, and asserts on the recovery log.
Release: 17 s launcher, **11.65 s** case, 21.8 s whole invocation, 17 assertions. Debug: 22 s
launcher, **16.17 s** case, 26.5 s whole invocation, 18 assertions. Both PASS with evidence `proven`.
Across all 28 recorded runs of this case the release times are 11.65–19.27 s (median 13.0) and the
debug times 16.17–19.14 s (median 17.4) — read from each bundle's recorded `build_mode`, never
inferred from the duration, because ticket 14's `att-T14-0001` is a *release* run at 19.27 s.

### 5.4 The bulk and churn workload

The bulk-100 and bulk-1000 groups are TEST 5 and TEST 6 of `cbrd_26659_oos_sql01_insert_select`, and
that case is the slowest of the nine in every one of the ten invocations that ran it: **231–950 ms**
(231 ms in `inv-T17-0002`). 1,100 rows of 4.1–4.9 KiB — 4.6 MB of payload — in under a second at the
seam, and the case's OOS-path evidence spec asserts that every one of them reached the out-of-row
path (`PHASE bulk100 … 1 100 457600`, `PHASE bulk1000 … 1 1000 4169540`: one chunk per row).

### 5.5 The instrumented fault scenario

Ticket 17 re-ran site `a1` (code 700000, `oos_publish_oos_oid`) fault and fault-disabled control
under `campaign_ns.sh`, against `oos-instr-f4299ac0c/debug_gcc_nounit` (`libcubrid.so`
`2b109c9d…`, ticket 41's identity): **fault 7.4 s with one acknowledgement, control 6.6 s with none**,
13.95 s for the pair. Across all twelve validated sites on the re-pinned build, read out of
ticket 41's `run-all.log`: fault runs 7.6–65.7 s, control runs 7.0–27.2 s, worst pair **79.3 s**
(site `i1`), whole twelve-site campaign **456.5 s**.

Two observations worth a line each. `t16_run.sh` writes `csql.err` into the **caller's** working
directory, not into its own output root, so running it from the docs repository leaves a debug log
there; ticket 17's copy was moved to `~/.cub/campaign/cbrd-26659/ticket17/t16root/csql.err-from-caller-cwd`
and a ticket that runs it should `cd` to its storage root first. And the instrumentation install's server log directory is shared across
tickets 16, 41 and 17, so the runner's acknowledgement count can include an earlier ticket's line —
`a1`'s fault run reported `acks: 2`, one from 2026-09-14 and one from this run. The timestamps
disambiguate and the control's zero is unaffected, but a ticket that counts acknowledgements
mechanically should filter by run rather than by file.

### 5.6 The multi-session barrier scenario — it exists, and it does not complete at the pin

*Corrected by ticket 49 (review F1). The first revision of this section was headed "it does not
exist" and opened "No barrier scenario exists in either suite"; it does.*
`shell/_06_issues/_18_2h/bug_bts_22449` in the private suite (commit `c4fe45173`, unchanged at
`66b66f1`) drives `22449.ctl` through CTP's isolation ctltool — `runone.sh`, `qactl`, `qacsql`, all
in the pinned tree at `/home/vimkim/CTP/isolation/ctltool/`: four clients, a coordinator that
releases them with explicit `MC: wait until Cn blocked | ready | unblocked` barriers on state each
client established with real database operations, C1 holding a transaction open while C2 (`CREATE
UNIQUE INDEX ... WITH ONLINE`), C3 (`INSERT`) and C4 (`ALTER TABLE ... ADD COLUMN`) block on its
locks. It is admissible on the standard §4 applies to the eleven-case bucket, whose binding case
`cbrd_27229` is pre-existing too, and the specification points at exactly this mechanism
("Existing isolation coordination mechanisms may be reused as dependencies inside private cases").

Ticket 49 ran it through `run_ctp_shell.sh` twice on 2026-09-21 — release build, client-server,
16 KiB pages, under `campaign_ns.sh` and the resource sampler, from a byte-identical copy of the
case directory under the ticket 49 storage (the case writes its isolation-tool outputs into its own
directory, and the repository worktree came back clean), with the full identity the other four
scenarios carry ([`evidence/ticket49/`](evidence/ticket49/), `inv-T49-000{1,2}/identity.txt`):

| | `att-T49-0001` | `att-T49-0002` (identical repeat) |
|---|---:|---:|
| CTP case time (`test-shell.xml`) | **132.0 s** | **130.7 s** |
| of which the ctltool schedule itself (`runone.log`) | 120.8 s | 120.7 s |
| CTP launcher wall | 139 s | 137 s |
| whole invocation, sampler wall (wrapper setup and restore included) | 143.6 s | 140.9 s |
| peak / p95 / mean CPUs | 1.49 / 0.30 / 0.08 | 1.11 / 0.22 / 0.07 |
| peak resident memory, peak processes | 0.74 GiB, 20 | 0.75 GiB, 20 |
| launcher exit, assertions | 0; 1 executed, 1 OK | 0; 1 executed, 1 OK |
| campaign outcome | FAIL — 131 s exceeds the fast tier's 120 s per-case cap | FAIL — same |
| install conf / databases / user `.CUBRID_SHELL_FM` drift | 0 / 0 / 0 | 0 / 0 / 0 |

Both runs halt at the same barrier. The controller's transcript
(`evidence/ticket49/inv-T49-000{1,2}/22449.ctl-transcript-formatted.log`) ends after C3's `INSERT`
has completed (`1 row affected`) with `WARNING! Client 4 blocked after waiting 100 seconds. => MC:
wait until C4 ready;` and then `Master controller 0 halting because of SIGTERM`, the tool's 120 s
timeout. The server log (`ctldb_server.err`) carries no lock timeout and no deadlock: C4 waited, with
`lock timeout INFINITE`, behind C2's online index build until the controller was killed. The case
still writes `OK` — its only assertion is `runone.sh`'s core-file scan, so a hang is invisible to it
and to CI, where it is not excluded — and the campaign records FAIL because the case time exceeds the
fast tier's per-case cap (a reached deadline never reports success). Where the 131 s go: about 6 s
compiling `qactl` and `qacsql` from the pinned CTP tree (the case builds them in place; ticket 49
removed the build products afterwards, the tree's listing hashed before and after), 5 s for
`prepare.sh`'s createdb and server start, under a second for C1 to C3 to establish state and
acknowledge, 100 s waiting on C4, the kill, and 2 s of cleanup.

**What this establishes, and what it does not.** The cost of a completed four-participant schedule
is not observable with this scenario at the pinned engine — a **Capability gap**, recorded on the §6
row (`capability_gap` in the model) — so the row keeps its derived 24.88 s with the review's O1 caveat
attached. What the two runs do establish is that a barrier schedule in which one participant blocks
costs more than the fast tier's 120 s per-case cap, which is consistent with the scheduled placement
and is why the row's tier does not move. Whether C4's blocking is the pinned engine's lock behaviour
for an `ALTER TABLE` behind an online index build, or the scenario's expectation from an older
engine, is not attributed here: the case asserts nothing about out-of-row storage and is not in the
campaign matrix (kind `coexistence`, ticket 14's precedent for an executed attempt that adds no
coverage). Ticket 23 should build on the ctltool mechanism, which works — four clients connected,
every barrier up to C3's held — and not on `22449.ctl` as it stands.

The mechanism probe's measurement stands as what it is: four participants, each opening its own
`csql` session, establishing state with a real out-of-row INSERT, acknowledging by creating a token,
and blocking until the coordinator releases it; three rounds; every wait deadline-bounded; sleep
pacing the poll and never proving ordering.

| Phase | Measured |
|---|---|
| Fixture (createdb 1.80 s + server start 3.04 s) | **4.84 s** |
| Four participants establish state and acknowledge | **0.107 s** |
| Release to all-acknowledged, per barrier | 0.104, 0.204, 0.204 s (mean **0.171 s**) |
| Whole probe | **5.61 s** |

**The barrier mechanism is cheap; the fixture is the whole cost of the probe.** Four sessions and
three acknowledged barriers cost 0.8 s of the 5.6 s. Read with the review's O1: the probe's
participants run a fresh `csql` per round, each on its own table, every statement autocommitting,
so nothing is held across a barrier and no two participants contend — 0.17 s per barrier is a
**floor** for uncontended coordination, not the cost of a schedule, and the two runs above show what
a schedule costs once a participant blocks. The four required families hold state across their
barriers; how much more they cost is ticket 23's measurement to make.

## 6. The tier-placement table (criterion 3)

The caps are decision ticket 08's and are **inputs**, not prose: `tools/tier_placement.py` reads them
from the model and computes the placement, and `selftest_tier_placement.py` check 10 requires that
lowering a cap moves a workload. A workload that fits no tier is reported, never squeezed.

| Tier | Invocation cap | Per-case cap |
|---|---:|---:|
| Fast regression | 900 s | 120 s |
| Scheduled | 7,200 s | 900 s |
| Extended | 28,800 s | 3,600 s |

`Invocation` is one of three things, and the *Invocation basis* column says which (added by ticket 49,
review F5; the first revision presented all eight measured-looking figures as measurements):
**measured whole**, one wall clock over the whole invocation (three rows); **composite**, assembled
from separately measured parts, named in the model's `composition` (five rows: the three seeded-churn
rows add the shell seam's 4.1 s launcher toll to a probe total that never paid it, and the
configuration sweep and the twelve-site fault campaign are sums of separately timed runs that were
never one invocation); **computed**, the seam's fixed cost plus cases times per-case cost (eight
rows). The worst-case-uniform figure — what an invocation would cost if every case were as slow as
the slowest — is computed beside every row and raised as a recorded risk when it crosses a cap the
figure in the table does not. A heterogeneous suite is placed by what it costs, and the risk of that
margin being composition rather than headroom is not hidden. *Per-case basis* says whether the
per-case figure was measured, and against what, or derived, and the model says from what.

| Workload | Coverage family | Seam | Per case | Cases / invocation | Invocation | Invocation basis | Tier | Headroom (case / invocation) | Per-case basis |
|---|---|---|---:|---:|---:|---|---|---|---|
| Fixed deterministic public SQL cases, each with its paired OOS-path evidence check | Representation, SQL operations, Read paths, Schema and utilities | public SQL | 8.28 s | 9 | 111.83 s | measured whole | fast | 93.1% / 87.6% | measured (inv-T17-0002, inv-T19-0001..0010) |
| Bulk and churn SQL groups (100 and 1,000 out-of-row rows) | SQL operations | public SQL | 8.28 s | 1 | 49.28 s | computed | fast | 93.1% / 94.5% | measured (inv-T17-0002, inv-T19-0001..0010) |
| The public SQL suite projected to forty cases (tickets 18 to 22) | Representation, SQL operations, Read paths, Schema and utilities | public SQL | 8.28 s | 40 | 372.2 s | computed | fast | 93.1% / 58.6% | derived |
| Crash and recover (kill -9, restart, recovery-log assertion) | Durability | private shell | 19.27 s | 1 | 26.45 s | measured whole | fast | 83.9% / 97.1% | measured (inv-T17-0003, inv-T17-0004, inv-T41-0002, inv-T41-0003) |
| A whole private issue bucket, eleven cases, the campaign case among them | Durability | private shell | 111.9 s | 11 | 432 s | measured whole | fast | 6.8% / 52.0% | measured (att-T14-0008-bucket, att-T14-0012-bucket, att-T14-0016-bucket) |
| The four required multi-session schedule families, each four participants over three acknowledged barriers | Concurrent lifetime | private shell | 24.88 s | 4 | 103.62 s | computed | scheduled | 97.2% / 98.6% | derived |
| Randomized out-of-row churn, ten fixed seeds, fresh fixture per seed | Concurrent lifetime, Durability | private shell | 55.0 s | 1 | 62.27 s | composite | scheduled | 93.9% / 99.1% | measured (seeds-10-fresh, seeds-100-fresh) |
| Randomized out-of-row churn, one hundred recorded seeds, fresh fixture per seed | Concurrent lifetime, Durability | private shell | 550.0 s | 1 | 554.16 s | composite | extended | 84.7% / 98.1% | measured (seeds-100-fresh) |
| The same hundred seeds on one fixture reused across them | Concurrent lifetime, Durability | private shell | 10.2 s | 1 | 20.82 s | composite | scheduled | 98.9% / 99.7% | measured (seeds-100-reused) |
| One instrumented fault site, fault run plus its fault-disabled control | Resource pressure | private shell (instrumented configuration) | 79.3 s | 1 | 83.4 s | computed | scheduled | 91.2% / 98.8% | measured (t17-instr-a1, evidence/ticket41/instr-sites/run-all.log) |
| The whole validated fault campaign, twelve sites, fault plus control | Resource pressure | private shell (instrumented configuration) | 79.3 s | 12 | 456.5 s | composite | extended | 97.8% / 98.4% | measured (evidence/ticket41/instr-sites/run-all.log) |
| Corruption detection on copied database, page and log images, six experiments | Resource pressure | private shell (instrumented configuration) | 98.0 s | 1 | 102.1 s | computed | scheduled | 89.1% / 98.6% | measured (ticket 16 section 11 (Hand-offs): 98 s for six experiments) |
| Bounded test filesystem exhaustion | Resource pressure | private shell (instrumented configuration) | 31.0 s | 1 | 35.1 s | computed | scheduled | 96.6% / 99.5% | measured (ticket 16 section 11 (Hand-offs): 31 s) |
| The twelve-cell configuration sweep (4/8/16 KiB x release/debug x SA/CS) | Representation | neither (a probe, not a case) | 5.33 s | 12 | 50.37 s | composite | fast | 95.6% / 94.4% | measured (evidence/ticket17/config-domain/) |
| HA replica correctness (dedicated scenario, prerequisites declared) | Operational features | private shell | 30.0 s | 1 | 34.1 s | computed | scheduled | 96.7% / 99.5% | derived |
| CDC/flashback and encryption (dedicated scenarios, prerequisites declared) | Operational features | private shell | 38.54 s | 1 | 42.64 s | computed | scheduled | 95.7% / 99.4% | derived |

**No workload fits no tier.** Every row fits its proposed tier, and `tier_placement.py check` reports
0 problems and 1 recorded risk:

> `shell-issue-bucket`: placed in the fast tier on its measured invocation time (432 s), but if every
> one of its 11 cases cost as much as its slowest (111.9 s) the worst case would be 1,235 s, over the
> 900 s cap. The margin is the suite's composition, so adding slow cases consumes it.

That risk is worth naming plainly, because it is where the fast tier is actually tight: the private
bucket's slowest case, `cbrd_27229`, takes **111.9 s against a 120 s per-case cap — 6.8% headroom**,
and it is a pre-existing case this campaign did not write. The campaign's own private case costs
11.6–19.3 s. Every other row in the table has 84% or more per-case headroom.

Placement in words, for the seven tickets that consume this table:

- **Fast** — the whole public SQL suite in one invocation (with its paired OOS-path evidence checks),
  the bulk and churn groups, the crash-and-recover case, and the private issue bucket. At the
  model's figures — 8.28 s per case over a 41.0 s launcher — the 900 s invocation cap admits about
  a hundred cases (104); the forty-case projection in the table sits at 58.6% invocation headroom,
  so forty is a projection for tickets 18 to 22, not a limit (corrected by ticket 49, review F6; the
  first revision said "about 40 cases before the 900 s invocation cap becomes the constraint"). The
  configuration sweep fits too.
- **Scheduled** — the four required multi-session schedule families, ten-seed randomized churn, a
  single instrumented fault site, the corruption-detection procedure, the bounded-filesystem
  procedure, and the HA/CDC/encryption scenarios when they are written. Every one of these fits the
  fast tier's caps on time alone as costed here — though §5.6's two runs show that a barrier
  schedule with a blocked participant does not, which is one more reason the families sit in this
  tier; they are scheduled because the spec's *Execution tiers* section
  assigns concurrency, recovery and fault work there and because they need infrastructure the fast
  tier should not carry — not because they are slow.
- **Extended** — hundred-seed randomized churn and the whole twelve-site fault campaign. Both fit
  with over 84% headroom, so the extended tier's 8-hour cap is not the binding constraint on anything
  this campaign has measured. Storage is (§8).

## 7. Seed counts against measured per-seed times (criterion 4)

No randomized workload exists yet — tickets 23 to 32 own them — so ticket 17 built and ran the shape
one must have: a seeded out-of-row churn workload whose payload sizes, characters and churn set are
functions of the seed alone. Per seed: a 1,000-row deterministic helper, 500 rows of 3,000–6,999
bytes inserted, every third row UPDATEd to a new size (the multi-chunk growth path), every third row
DELETEd and re-INSERTed at a different size (the slot-reuse path), then whole-value verification and
`SHOW HEAP OOS`. Each seed reached the OOS path: 407–411 chunks and 2.179–2.210 MB of chunk payload
per seed in the ten-seed run, 381–421 chunks and 2.026–2.278 MB in the hundred-seed run
(`Oos_num_recs` and `Oos_recs_sumlen` per seed in `evidence/ticket17/probes/seed-cost-*.json`;
corrected by ticket 49, review F6 — the first revision's "401–411 chunks, 2.15–2.23 MB" fitted
neither run).

| Schedule | Seeds | Total | Per seed (mean) | Per seed (min–max) |
|---|---:|---:|---:|---:|
| Scheduled tier, fresh fixture per seed | 10 | **58.2 s** | 5.81 s | 5.44–6.69 s |
| Extended tier, fresh fixture per seed | 100 | **550.1 s** | 5.50 s | 5.33–7.68 s |
| The same hundred seeds, one fixture reused | 100 | **16.7 s** | 0.102 s | 0.096–0.117 s |

**Both seed counts hold, with room to spare.** Ten seeds cost 58 s against a 900 s scheduled per-case
cap; one hundred cost 550 s against a 3,600 s extended per-case cap — 85% headroom. **No decision
request to change a limit is needed, and none is made.**

The reason is worth recording, because it is not what the seed count suggests. Per seed the workload
itself costs **0.11 s**; the fixture costs **5.4 s** (createdb 2.19 s, server start 2.03 s, teardown
1.36 s). A fresh fixture per seed is 54 times the cost of the seed's own work. So:

- **The fixture policy, not the seed count, decides whether a randomized workload fits.** A hundred
  seeds are 550 s with a fresh fixture each and 17 s on a reused one.
- **The binding constraint on a bigger extended workload is storage, not time.** The extended per-case
  cap leaves about 36 s per seed at 100 seeds. Spending 30 s of that on the workload instead of the
  fixture would mean roughly 700 MB of out-of-row payload per seed at the measured rate, which
  exceeds the 100 GiB working-storage budget within a few seeds. Tickets 23 to 32 should size
  randomized workloads against §8, not against the clock.
- A fresh fixture per seed is what an independent trial needs, and decision ticket 07's three
  fresh-fixture reproductions assume it. The reused-fixture figure is recorded so a ticket that
  wants many more than 100 seeds knows what it would be trading away.

## 8. Resource ceilings against measured peak usage (criterion 5)

Decision ticket 08's ceilings are **aggregate campaign limits**: 8 logical CPUs, 16 GiB of memory,
100 GiB of working storage under `/home`, one infrastructure scenario at a time. Ticket 17 ran one at
a time throughout, so each row below is a whole-campaign figure at that moment.
`tools/resource_sampler.py` walks `/proc` every interval, takes the transitive descendants of the
command it started and sums their resident memory and their utime+stime deltas, reporting CPU in
logical CPUs (validated against four busy loops: 4.03).

| Invocation or probe | Wall | Peak CPUs | p95 CPUs | Mean CPUs | Peak RSS | Peak procs | Storage delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| barrier mechanism, four participants, three acknowledged barriers | 7.69 s | 2.379 | 0.748 | 0.274 | 0.636 GiB | 13 | 0.222 GiB |
| inv-T17-0001 public SQL tracer case alone, release | 52.3 s | 2.379 | 0.693 | 0.126 | 0.763 GiB | 21 | 0.222 GiB |
| inv-T17-0002 public SQL suite, nine cases, release, fast tier | 111.83 s | 7.668 | 0.993 | 0.227 | 0.836 GiB | 21 | 2.745 GiB |
| inv-T17-0003 private shell durability (crash and recover), release | 21.79 s | 1.386 | 1.006 | 0.336 | 0.705 GiB | 15 | 0.001 GiB |
| inv-T17-0004 private shell durability (crash and recover), debug | 26.45 s | 1.405 | 1.01 | 0.33 | 0.856 GiB | 15 | 0.001 GiB |
| 10 seeds, fresh fixture, release, 16 KiB (scheduled-tier seed count) | 58.84 s | 1.313 | 1.121 | 0.258 | 0.66 GiB | 8 | 0.0 GiB |
| 100 seeds, fresh fixture, release, 16 KiB (extended-tier seed count) | 550.73 s | 0.697 | 0.658 | 0.246 | 0.66 GiB | 8 | 0.0 GiB |
| 100 seeds, reused fixture, release, 16 KiB (amortized schedule) | 17.43 s | 0.766 | 0.765 | 0.521 | 0.654 GiB | 7 | 0.0 GiB |
| instrumented fault scenario a1 (700000 oos_publish_oos_oid), fault then control | 13.95 s | 1.136 | 0.621 | 0.225 | 0.428 GiB | 7 | 0.506 GiB |

**Memory and processes: never close.** Peak resident memory across every invocation and probe is
**0.86 GiB of the 16 GiB ceiling (5.4%)**, peak process count 21.

**CPU: within the ceiling, but the peak is 96% of it, and nothing enforces it.** The highest reading
is **7.67 logical CPUs** during the nine-case public SQL invocation — a single 0.5-second sample
(sample 30 of 215 in `samples/inv-T17-0002.json`): the sample before it reads 0.307 CPUs and the
sample after it 0 (corrected by ticket 49, review F6; the first revision said "0 CPU in the sample
either side"). Sustained usage is far lower: the 95th percentile is at most
1.12 CPUs and the mean at most 0.52 in every measurement.

The transient was attributed rather than left a mystery. Two probes at a 0.1-second interval:
`cubrid createdb` alone peaks at **1.05 CPUs**; `cub_server` boot peaks at **3.07 CPUs** while
allocating its 668 MB page buffer. So the peak is server boot, amplified under CTP by the JVM running
beside it. The barrier probe's own peak (2.38 CPUs) lands on exactly the sample where resident memory
jumps from 60 MB to 647 MB — server boot again.

Two things follow, and both are for the record rather than for this ticket to change:

- **The 8-CPU ceiling is an admission convention, not a control.** No cpuset, cgroup or `taskset`
  binds any campaign invocation, and the engine sizes itself from the host's 80 logical CPUs, not
  from the campaign's budget. Every measurement so far respects the ceiling; nothing would stop one
  from exceeding it. Proposal D4 in §10.
- **Server boot is the resource event of this campaign.** It is also 2.0 s of every fixture (§7), so
  the scenario that starts the fewest servers is both the cheapest and the calmest.

**Storage.** The campaign root `~/.cub/campaign/cbrd-26659` now holds **40 GiB of disk usage**
(51 GiB apparent) against the 100 GiB cap; ticket 17 added 3.8 GiB, of which 3.0 GiB is the nine
retained OOS-path-evidence databases and about 0.5 GiB the instrumentation re-run. The replay bundles
themselves are 3 MiB. Per public case checked, one evidence database costs **256–400 MiB** — which,
with §4's 7.33 s, makes the paired evidence check the dominant cost of the public seam in both time
and space.

Measured against the cap this is comfortable. Two cautions:

- A public suite of forty cases would retain about **13 GiB** of evidence databases, and the
  four-configuration sweep the scheduled and extended tiers owe would multiply that.
- `retention.py admit` reports **50.82 GiB used**, because `campaign_records.storage_used_bytes` sums
  `st_size` (apparent size) while ticket 44's finding F7 settled that the 100 GiB cap is **disk
  usage** — 40 GiB here. The gate is therefore 27% conservative: it will stop admitting work at about
  79 GiB of real usage. Nothing is at risk and nothing was changed; proposal D5 in §10.

## 9. Findings

### F1 — The CTP SQL runner **does** report per-case times; ticket 19 §10 says it does not

Ticket 19's record states: *"All nine cases' execution — 1,099 ms total (`summary.info` `totalTime`;
the SQL runner reports no per-case time, only this total)."* The second clause is wrong, and ticket
19's own retained bundles show it. `summary.info` carries one `<caseresult>` per case inside
`okList`/`nokList`, and each carries its own `<totalTime>`:

| Invocation | Slowest case | Per-case spread |
|---|---|---|
| `inv-T19-0008` | `cbrd_26659_oos_sql01_insert_select` 260 ms | 30–260 ms, sum 732 ms |
| `inv-T19-0009` | `cbrd_26659_oos_sql01_insert_select` 286 ms | 39–286 ms, sum 864 ms |
| `inv-T17-0002` | `cbrd_26659_oos_sql01_insert_select` 231 ms | 28–231 ms, sum 661 ms |

**Why it matters:** tier placement is judged against a *per-case* cap, and ticket 19's statement says
that number cannot be had at the public seam. It can, from sealed evidence, for every case the
campaign has ever run. `tools/extract_ctp_timings.py` reads it, and §4's table rests on it.

This does **not** touch ticket 35's finding F3, which is about the *assertion* count: the SQL runner
still reports no per-assertion count, `executed.assertion_count` is still correctly null, and nothing
in this finding manufactures one. The two are different quantities; only the timing claim is wrong.

Also worth noting beside it: ticket 19 §10's "1,099 ms" is the figure from `inv-T19-0004`. Across the
nine invocations that ran all nine cases the totals are 665, 703, 732, 843, 864, 909, 1,099, 1,828 and
2,061 ms, so 1,099 is the third highest. The number is real; it reads as a typical total when it is
not one, and the spread itself (a factor of three on the same cases and the same build) is the more
useful fact for a per-case cap.

### F2 — `--scenario-override` produces a spurious `failure-of-proof` against a multi-case scenario

`inv-T17-0001` ran one case from a scenario copy under the ticket 17 storage and recorded
`proof.verdict: failure-of-proof` with eight `unexpected-case` mismatches naming the *other eight*
cases of the repository's scenario directory. The case itself PASSed.

The cause is in `ctp_sql_records.py`: it derives the scenario directory from the declaration's
`repository` + `scenario` and scans it for undeclared `.sql` files, while the wrapper's
`--scenario-override` points CTP somewhere else entirely. The two disagree by construction. It was
latent until now because ticket 15's overrides ran when that directory held one case; ticket 19's
eight new cases exposed it.

**Why it matters:** a failure of proof that is not a failure of proof is as damaging as a pass that is
not a pass — the campaign's whole manifest mechanism rests on that verdict meaning something. Any
single-case timing run, any planted-defect control and any minimized reproducer that uses
`--scenario-override` against the public scenario will record it.

**Not fixed here**, deliberately: it is ticket 15's tooling, this ticket's measurements do not need it
(§4 gets per-case times from the full-scenario run, per F1), and changing shared tooling that seven
tickets depend on is not an implementation ticket's call. Proposal D3 in §10 carries the one-line fix.
`inv-T17-0001` is kept exactly as recorded, as the evidence.

### F3 — A fresh matrix silently widens a coverage claim the case's own ticket had qualified

`matrix_merge.py` writes `gap_kind: none` for a new row whose latest outcome is a PASS with proven
OOS-path evidence, and asks the author to scope it. Ticket 17 re-ran cases tickets 19 and 41 had
already scoped by hand under the qualified rule, into a matrix of its own — and **eight of its
seventeen rows came out `none` where the authoritative matrices read `Delivery gap`**.

Nothing was wrong with the merge; the qualification is a judgement about the requirement's text that
tooling cannot make. But the consequence is general: **any ticket that re-measures an existing case
into a new matrix will publish a wider coverage claim than the ticket that wrote the case.** Ticket
17 handled it with `evidence/ticket17/scope_matrix.py`, which adopts the authoritative gap kind, can
only narrow a claim, reports a row it finds in no authoritative matrix rather than guessing, and
re-verifies with `--check`. A general rule belongs in the record contract, not in one ticket's
script: proposal D6 in §10.

### F4 — The four required schedule families have no case at either seam; the barrier scenario the private suite has does not complete at the pin

*Corrected by ticket 49 (review F1); the first revision was headed "The barrier scenario criterion 1
asks for does not exist".* Recorded as a **Delivery gap**: the four required schedule families
(snapshot survival, rollback survival, slot reuse and cleanup retry, interrupted recovery) have no
case at either seam. Ticket 23 owns them and is blocked by ticket 17, so this ticket cannot close the
gap and ticket 23 cannot start without it. A multi-session barrier *scenario* does exist in the
private suite — `bug_bts_22449`, four participants under CTP's isolation ctltool — and ticket 49 ran
it twice (§5.6): it does not complete at the pin, its fourth participant blocked for the tool's whole
barrier wait, so its cost is a **Capability gap** and the §6 row for the families stays `derived` from
the mechanism probe, now with the review's O1 caveat and the two runs' lower bound (131 s, over the
fast tier's per-case cap) attached. The mechanism itself works and is what ticket 23 should build on.

## 10. Decision requests — proposed, never made

The specification is explicit: *"Agents propose; they never accept."* None of the following was
decided here, and no numeric limit, no `accepted_exclusions` entry and no answer promotion was
written by this ticket.

### D1 — What does "N seeds per selected randomized workload" cost against the per-case cap?

Decision ticket 08 says the scheduled tier runs "10 fixed seeds per selected randomized workload" and
the extended tier "100 recorded seeds", but not whether the seeds of one workload are **one case** or
**N cases**. The two readings differ by a factor of N against the per-case cap, and
`tools/tier_placement.py` therefore computes both:

| Reading | Scheduled, 10 seeds | Extended, 100 seeds |
|---|---|---|
| A: all seeds inside one case | 55.0 s per case (of 900 s) | 550.0 s per case (of 3,600 s) |
| B: each seed is its own case | 5.5 s per case, 10 cases | 5.5 s per case, 100 cases |

**Recommendation: reading A, all seeds of one workload inside one case.** Both readings fit at the
measured cost, so nothing is forced; A is preferable because the manifest then carries one expected
case identity per workload rather than N, because a per-seed case would multiply the manifest's
expected-count bookkeeping by 100, and because decision ticket 07's "three consecutive reproductions
from fresh fixtures" is about a failing *workload*, not a failing seed. The cost of A is that a
100-seed case that hits the per-case cap loses every seed's evidence at once, which argues for the
workload writing its per-seed record as it goes. **Whichever is chosen, the table in §6 holds.**

### D2 — A tier-placement table needs a home when the workloads change

§6 is a snapshot of sixteen workloads at the pin. Tickets 18 to 32 will add workloads and change the
shape of some of these (a forty-case public suite, real concurrency schedules, real HA scenarios).
Options: this record is the home and each ticket amends it; the model file
`evidence/ticket17/tier-placement-model.json` is the home and each ticket appends a workload and
re-renders; or the coverage matrix grows a placement column.

**Recommendation: the model file, amended by the ticket that changes a workload, with `tier_placement.py
check` run before that ticket's records are merged.** The table is then always a computation and never
a transcription, which is the property §6 is built for. This is a new design choice, so it is a map
decision, not something to settle here.

### D3 — `ctp_sql_records.py` should be told about `--scenario-override` (finding F2)

`run_ctp_sql.sh` already knows the override path; it simply does not pass it on, and the records tool
has no argument to receive it. The fix is an argument and one line at the call site, plus the
existing self-test pattern for a regression check.

**Recommendation: add `--scenario-dir` to `ctp_sql_records.py`, default to the declaration-derived
path, and have `run_ctp_sql.sh` pass `${scenario}`.** Owner: ticket 15's tooling, which already
carries an open follow-up (`att-T15-C04`). Until it lands, a single-case run against a multi-case
scenario records a `failure-of-proof` that is about the tooling.

### D4 — The 8-CPU ceiling has no enforcement (§8)

Nothing binds a campaign invocation to 8 logical CPUs; the engine sizes itself from the host's 80.
Measured peak is 7.67 CPUs, a sub-second `cub_server` boot transient at 96% of the ceiling. Options:
leave it an admission convention and record the measurement; run every invocation under
`taskset -c 0-7`; or add a cpuset. **Recommendation: leave it as a convention for now and re-measure
when concurrency schedules exist, because `taskset` would change what the campaign measures** — a
concurrency schedule confined to 8 of 80 CPUs exercises a different engine than the one a user runs,
and this campaign is about OOS correctness, not throughput. The measurement belongs in the final
report either way.

### D5 — `retention.py admit` measures apparent size where the cap is disk usage (§8)

`campaign_records.storage_used_bytes` sums `st_size`; ticket 44's F7 settled that the 100 GiB cap is
disk usage. CUBRID's volumes are sparse, so the gate currently reads 50.82 GiB where `du` reads 40 GiB
and will refuse work at about 79 GiB of real usage. **Recommendation: change `storage_used_bytes` to
`st_blocks * 512`,** which is what `tools/resource_sampler.py` already uses and what F7 decided. It is
a one-line change in ticket 15's tooling that makes the gate agree with the settled measure; it is
raised rather than made because it changes admission behaviour for every other ticket. The *limit*
does not change and must not.

### D6 — Re-measuring an existing case must not widen its coverage claim (finding F3)

`evidence/ticket17/scope_matrix.py` solves this for ticket 17 by adopting the authoritative gap kind.
The general rule belongs in the record contract. Options: the merge refuses to write `gap_kind: none`
for a (requirement, case, configuration) key that another canonical matrix already scoped otherwise;
the merge adopts the existing scoping automatically; or every ticket runs an adoption step by hand as
ticket 17 did. **Recommendation: the merge adopts, and reports each adoption** — it cannot widen a
claim by accident, and a ticket that genuinely means to widen one then has to say so in the row.
Owner: the record contract (ticket 36's successor), applied in ticket 15's tooling.

## 11. Ticket 17 criteria checklist

| Criterion | Status |
|---|---|
| Representative cases timed with full identities recorded: the two tracer cases, a multi-session barrier scenario, a crash-and-recover scenario, a bulk or churn workload, and one instrumented fault scenario | **partially met and disclosed** (corrected by ticket 49). Four of the five exist and are measured with full identities (§5.1–§5.5). The multi-session barrier scenario **exists** in the private suite (`bug_bts_22449`) and was run twice at the seam with full identities (§5.6, `evidence/ticket49/`); it does not complete at the pin, so its cost is a Capability gap, the four required schedule families remain a Delivery gap (finding F4), and the table's row is `derived` from the mechanism probe with the review's caveat |
| The configuration domain re-verified against the pinned engine: 4, 8 and 16 KiB pages, release and debug, standalone and client-server, each proven runnable with a matching binary or recorded as a Capability gap | **met** (§3). All twelve cells proven runnable by execution, each naming the engine commit and four binary hashes; **no Capability gaps** |
| The tier-placement table finalized per workload type against the per-case caps (2, 15 and 60 minutes) and invocation caps (15 minutes, 2 hours, 8 hours); any workload that cannot fit recorded, not squeezed | **met** (§6). Sixteen workloads, computed from the caps as inputs; 0 problems, 1 recorded risk; no workload fits no tier |
| Seed counts (10 for scheduled, 100 for extended) checked against measured per-seed times; if the caps cannot hold, a decision request rather than a silent change | **met** (§7). 10 seeds 58.2 s of 900 s; 100 seeds 550.1 s of 3,600 s. **Both hold; no limit was changed and none needed changing.** The open question about what a "seed" costs against a per-case cap is parked as D1 |
| Resource ceilings (8 logical CPUs, 16 GiB, 100 GiB under the home directory) checked against measured peak usage | **met** (§8). Peak 7.67 CPUs (a sub-second `cub_server` boot transient, attributed), p95 ≤ 1.12; peak memory 0.86 GiB of 16; storage 40 GiB of 100. Two observations parked as D4 and D5 |
| The timing record and the placement table committed in the docs repository campaign folder | **met.** This record and `evidence/ticket17/`; nothing pushed |

## 12. Reproduction

```bash
cd /home/vimkim/gh/my-cubrid-docs/cbrd-26659/campaign
export CAMPAIGN_TICKET_ROOT=/home/vimkim/.cub/campaign/cbrd-26659/ticket17
NS=/home/vimkim/.cub/campaign/cbrd-26659/ticket14/tools/campaign_ns.sh

# the configuration domain: one probe per cell, one infrastructure scenario at a time
for page in 4096 8192 16384; do for build in release debug; do for mode in standalone client-server; do
  $NS tools/config_domain_probe.sh --build $build --page-size $page --run-mode $mode \
      --out $CAMPAIGN_TICKET_ROOT/config-domain
done; done; done
python3 tools/config_domain.py check --results evidence/ticket17/config-domain

# the four CTP invocations, each under the resource sampler (see the record's §5 for the arguments)
python3 tools/resource_sampler.py --out <sample>.json --label '<label>' --interval 0.5 \
  --storage $CAMPAIGN_TICKET_ROOT \
  --command tools/run_ctp_sql.sh --declarations tools/declarations/ticket19-public-sql-operations.json \
     --build release --manifest-id inv-T17-0002 --attempt-ids att-T17-0002,...,att-T17-0010 \
     --evidence-dir evidence/ticket17 --tier fast

# the seeded churn probe (the driver backs up, repoints and restores $CUBRID/conf/cubrid.conf)
$NS $CAMPAIGN_TICKET_ROOT/run_seed_probe.sh release --page-size 16384 --seeds 100 --rows 500 \
   --fixture fresh --out $CAMPAIGN_TICKET_ROOT/seeds/100-fresh

# the barrier mechanism, and one instrumented fault site with its control
$NS tools/barrier_cost_probe.sh --build release --participants 4 --rounds 3 \
   --out $CAMPAIGN_TICKET_ROOT/barrier

# the barrier SCENARIO the private suite has (ticket 49): from a copy of the case directory, because
# the case writes its isolation-tool outputs into its own directory; kind coexistence, no matrix row
CAMPAIGN_TICKET_ROOT=/home/vimkim/.cub/campaign/cbrd-26659/ticket49 python3 tools/resource_sampler.py \
  --out <sample>.json --interval 0.5 --storage /home/vimkim/.cub/campaign/cbrd-26659/ticket49 \
  --command tools/run_ctp_shell.sh --declarations tools/declarations/ticket49-barrier-timing.json \
     --build release --manifest-id inv-T49-0001 --attempt-ids att-T49-0001 --evidence-dir evidence/ticket49 \
     --scenario-override /home/vimkim/.cub/campaign/cbrd-26659/ticket49/scenarios/barrier/bug_bts_22449 \
     --kind coexistence --tier fast
T16_ROOT=$CAMPAIGN_TICKET_ROOT/t16root $NS bash -c \
   'bash ~/.cub/campaign/cbrd-26659/ticket16/tools/t16_run.sh a1 fault; \
    bash ~/.cub/campaign/cbrd-26659/ticket16/tools/t16_run.sh a1 control'

# measurements -> model -> placement, and the checkers
python3 evidence/ticket17/build_model.py --storage $CAMPAIGN_TICKET_ROOT \
   --out-measurements evidence/ticket17/measurements.json \
   --out-model evidence/ticket17/tier-placement-model.json
# ticket 49's corrections to the model (F1, F5, F7), which build_model.py also applies; idempotent
python3 evidence/ticket17/apply_ticket49_model_corrections.py --model evidence/ticket17/tier-placement-model.json
python3 tools/tier_placement.py check --model evidence/ticket17/tier-placement-model.json
python3 tools/tier_placement.py place --model evidence/ticket17/tier-placement-model.json
python3 tools/selftest_config_domain.py && python3 tools/selftest_tier_placement.py

# the matrix, and the adoption that stops a re-measurement widening a coverage claim
python3 tools/matrix_merge.py --manifest evidence/ticket17/inv-T17-000{1,2,3,4}.json \
   --attempt-records-dir evidence/ticket17 --out evidence/ticket17/matrix.json
python3 evidence/ticket17/scope_matrix.py --matrix evidence/ticket17/matrix.json \
   --authoritative evidence/ticket19/matrix.json evidence/ticket41/matrix.json --check
```

Every invocation and probe ran under `campaign_ns.sh` (ticket 37 decision 2), against
`/home/vimkim/CTP` (decision 1), on the public seam's ports 26659 and 33120–33122 and the
instrumentation lane's 26671 and 33140–33142 (decision 5), one infrastructure scenario at a time.
The private seam's second port block (26660, 33130–33133) was not needed: ticket 17 is a single agent
running serially, so both seams used one lane in turn. Ticket 49's two runs used the same one block,
alone, because the wrappers know no other (ticket 50 applies the second lane).

## 13. What this does not claim, and what the next tickets owe

- **No barrier schedule of the four required families was written or run.** §5.6 measures a
  mechanism, and the pre-existing barrier scenario ticket 49 ran does not complete at the pin. A
  schedule that establishes a snapshot, survives a rollback, reuses a slot or is interrupted
  mid-recovery will cost more than the mechanism probe's 5.6 s — the two runs show that one blocked
  participant alone costs the isolation tool's whole 120 s timeout — and how much more is ticket 23's
  measurement to make.
- **HA, CDC/flashback and encryption are unmeasured.** Their rows in §6 are lower bounds with the
  derivation stated, not estimates. The tickets that write those scenarios owe the measurement, and
  §6 should be recomputed when they have it.
- **The debug public SQL suite was not run.** Ticket 17 measured debug cost on the shell seam
  (16.17 s against 11.65 s release) and on all six debug configuration cells (3.8–5.3 s against
  3.2–4.7 s release), giving a multiplier of about 1.2–1.4; the public suite's own debug cost is
  outstanding. It was left out because a debug run of ticket 19's nine cases could FAIL on
  build-dependent output and would then write `Under triage` rows against cases this ticket did not
  author. It belongs to ticket 22, which assembles the fast tier.
- **Nothing here is a per-case cap enforcement.** Ticket 37 decision 3 keeps the per-case cap
  measured rather than enforced, because CTP's own timeout kills a crash case and destroys its
  evidence. §6 is that measurement; an attempt a cap terminated still records BLOCKED.
- **The paired OOS-path evidence check is the public seam's real cost**, in both time (7.33 s per
  case) and storage (256–400 MiB per case). Tickets 20 to 22 should treat batching those checks into
  fewer databases as the scaling work, and §7's storage arithmetic as the limit on randomized
  workloads.

## 14. Verification (as of 2026-09-18; revision 2's verification is in §15)

| Check | Result |
|---|---|
| `python3 tools/validate_records.py evidence/` | **280 records, 0 failing** (119 attempt records, 34 manifests, 10 matrices, 117 replay-bundle indexes) |
| `python3 tools/check_campaign_records.py` | **exactly one item, and it is not ticket 17's**: `evidence/ticket15/controls/att-T15-C04.json`, the known ticket 15 follow-up recorded in the traceability-schemas document and in ticket 19's report §14 O1. Every other check in that file passes: schema subset, catalogue, scenario map, record schemas, matrix completeness for every other attempt, and document freshness |
| `python3 tools/render_docs.py --check` | `fresh` |
| `tools/selftest_config_domain.py` | 9 checks, 0 failing |
| `tools/selftest_tier_placement.py` | 15 checks, 0 failing |
| `tools/selftest_matrix_completeness.py` | 0 failing |
| `tools/selftest_matrix_merge.py` | 0 failing |
| `tools/selftest_promotions.py` | 0 failing |
| `tools/config_domain.py check` | 12 cells read, 12 expected, 0 problems |
| `tools/tier_placement.py check` | 16 workloads, 0 problems, 1 recorded risk |
| `evidence/ticket17/scope_matrix.py --check` | 17 rows, 0 disagreements, 0 unscoped |
| `sha256sum -c evidence/ticket17/SHA256SUMS-bulky.txt` | 1,328 files verify |

Both checkers written for this ticket were written **before** the thing they check and were seen to
fail: `selftest_config_domain.py` against a missing `config_domain` module, and
`selftest_tier_placement.py` against a missing `tier_placement` module and then against three
unimplemented checks (13 to 15, the measured-versus-worst-case distinction §6 rests on).

Install and worktree hygiene, on every invocation and probe: **`$CUBRID/conf` drift 0,
`$CUBRID/databases` drift 0, `~/.CUBRID_SHELL_FM` drift 0, testcase worktree drift 0**, on all four
CTP invocations; six configuration cells and the barrier and seed probes restored
`$CUBRID/conf/cubrid.conf` verbatim by hash; both installs end the ticket back at
`cubrid_port_id=1523`. Both testcase worktrees are clean at `35c815943` and `c4fe45173`. The engine
worktree shows one pre-existing modification, `cubrid-cci/win/cci_version.h` dated 2026-08-14, which
is a build artifact of an earlier configure and was not touched here.

## 15. Revision 2 — closing the specification's independent review (2026-09-21)

The review the specification requires ran on 2026-09-18, by a session that authored none of these
artifacts and reached them as primary sources. Verdict **REVISE**: every load-bearing number
re-derived and reproducing, both new checkers validated by re-execution, replay and cleanup evidence
sound, and two blocking findings. Its record is
[`CBRD-26659-ticket17-independent-review_f4299ac_claude.md`](CBRD-26659-ticket17-independent-review_f4299ac_claude.md).
Campaign ticket 49 carries its findings, closed by a session that authored neither this record nor
the review; every change below is in this repository. **No case, answer or testcase commit changed**
and no coverage claim widened: the two CTP invocations ticket 49 made are `coexistence` attempts that
reach no matrix. The eleven sections this revision touched say so in place.

| # | Finding | Resolution |
|---|---|---|
| F1 | **Blocking.** §5.6 said "no barrier scenario exists in either suite"; `bug_bts_22449` in the private suite is a four-participant, coordinator-released barrier scenario under CTP's isolation ctltool, admissible on the standard §4 applies to the eleven-case bucket, and the row ticket 23 inherits was derived where it could have been measured | **Corrected and timed.** §2, §5, §5.6, §9 F4, §11, §13, the model, `evidence/ticket17/README.md`, `tools/barrier_cost_probe.sh`'s header and the ticket's checklist now say what is true: the four required schedule families are a Delivery gap, ticket 23's; the scenario exists. Ticket 49 ran it at the shell seam twice with full identities (`att-T49-0001`, `att-T49-0002`, `evidence/ticket49/`): in both runs the schedule halts at `MC: wait until C4 ready` — C4's `ALTER TABLE` blocked behind C2's online index build for the tool's 100 s barrier wait — and the controller is killed by the tool's 120 s timeout, so the cost of a completed schedule is a **Capability gap** at the pin (§5.6). The row keeps its derived 24.88 s with O1's caveat and the gap recorded on it; the runs' 131 s lower bound, over the fast per-case cap, is consistent with the scheduled placement and moves nothing. The mechanism probe stays, relabelled as the uncontended floor it measures |
| F2 | **Blocking.** Eight of `inv-T17-0002`'s twelve attempt records and bundle indexes carried a digest and a `total_bytes` taken while the shared bundle was still growing — the defect ticket 44 F3 corrected in ticket 19 on the user's 2026-09-16 decision, reintroduced two days later | **Corrected, and made unrepeatable.** `evidence/ticket17/apply_ticket49_record_corrections.py` gives the eight attempt records, their eight indexes and the manifest's eight `bundle_hash` entries the finished bundle's `sha256:f0450fd5…` and 322,170 bytes, each attempt record's `notes` saying what it used to carry, and re-derives the fifteen matrix seals over the rewritten manifest; nothing re-hashed silently, no bundle touched (`sha256sum -c` verifies all 212 files). Ticket 47's `inv-T47-0001` carried the same defect from the same tooling (eight of nine records) and was corrected by the same script, disclosed in ticket 49's Answer. Tooling: both post-processors now seal a shared root **once**, after the invocation's last file (`campaign_records.seal_bundle_records`), which refuses a record sealed earlier; `tools/selftest_bundle_sealing.py` proves it on a synthetic three-case bundle per seam. Checker: `validate_records.py` cross-checks every bundle index whose root exists against sha256 of its `SHA256SUMS` and every citing attempt record, reporting protected-prefix bundles of the older conventions as notes; it reported 32 failing before the correction and 0 after |
| F3 | The seed arithmetic had no negative control: `per_case = per_seed` left all fifteen checks passing while the table lost a factor of ten | **Fixed.** `selftest_tier_placement.py` check 9b asserts the per-case figure the placement and the headroom use (58 s, 75 s worst-case invocation, 93.6% headroom); re-planting the mutation fails exactly that check (`evidence/ticket49/planted-defects.txt`) |
| F4 | `config_domain.py` never verified the binaries it said prove a cell: four `dead…beef` hashes and a `cubrid_rel` naming `11.5.0.0001-deadbee` both read as proven | **Fixed.** The two library hashes must equal `campaign_records.LIBRARY_HASHES[build]`, `cubrid_rel` must name the pinned commit and the cell's build, and a cell's fields must agree with its id (§3); `selftest_config_domain.py` checks 10 to 13 plant all four ways. Re-planting A and B against copies of the twelve real cells yields 3 named problems; the real cells still 0 |
| F5 | Five of eight `invocation_measured_seconds` were composites presented as measurements, and four purely computed invocation figures shared the `Basis` column with measured per-case ones | **Labelled.** Every measured-looking figure in the model carries `invocation_measurement` (`measured-whole` or `composite`, with the composition named from the probe outputs); `tier_placement.py` refuses a figure without the label, renders an *Invocation basis* column (measured whole / composite / computed) and renames the last column *Per-case basis*; §6 explains it; `selftest_tier_placement.py` checks 16 to 18 cover it. The launcher-median nit (41.0 s where the fixed-cost median is 40.1 s) is left as it is: it overstates, and F6's arithmetic uses the model's own 41.0 s |
| F6 | Three numbers did not hold: "room for about 40 cases", "401–411 chunks, 2.15–2.23 MB", "0 CPU in the sample either side" | **Re-derived.** About a hundred cases (104 at 8.28 s per case over a 41.0 s launcher; the forty-case row is a projection at 58.6% headroom) in §6, and the same correction in the ticket's Outcome; 407–411 chunks and 2.179–2.210 MB for the ten-seed run, 381–421 and 2.026–2.278 MB for the hundred-seed run, from `Oos_num_recs` and `Oos_recs_sumlen` per seed (§7); 0.307 CPUs before the peak sample and 0 after (§8) |
| F7 | Two rows cited "ticket 16 section 12" for figures in its section 11; the evidence README cited §7 and §11 of this record for §9 and §12 | **Fixed** in the model, `build_model.py`, the table and the README |
| O1 | The barrier probe measures uncontended coordination at its own poll resolution, not a schedule | **Attached** to the row's derivation and to §5.6; the two runs show what one blocked participant costs |

**Reproducibility caveat, found while regenerating the model.** On 2026-09-19 ticket 46's demotion
removed `ctp_result/` and `ctp_runtime_logs/` from six ticket 15 bundles, so `extract_ctp_timings.py`
now reads 51 of the 57 bundles §4 rests on (15 SQL and 36 shell). `build_model.py` regenerates every
corrected row of the model identically — the barrier row, the eight labels and the two citations
agree with `apply_ticket49_model_corrections.py` row for row — but the seam statistics it would write
today differ from `measurements.json` as sealed on 2026-09-18, which stays as recorded. What a
demoted core keeps is ticket 48 item 48.7's; this is an input to it.

**Verification (2026-09-21).** `validate_records.py evidence`: 307 records, 0 failing, 12 notes on
protected-prefix bundles (`evidence/ticket49/validate-after.txt`; 32 failing before,
`validate-before.txt`). `check_campaign_records.py`: exactly the pre-existing `att-T15-C04` item
(ticket 44 O1, ticket 15's). `render_docs.py --check`: fresh. Self-tests, all 0 failing:
`selftest_bundle_sealing.py` (7 checks, new), `selftest_config_domain.py` (13), `selftest_tier_placement.py`
(19), `selftest_matrix_completeness.py`, `selftest_matrix_merge.py`, `selftest_promotions.py`,
`selftest_retention.py` (its shared-directory fixtures now carry the finished figures the cross-check
requires). `tier_placement.py check`: 16 workloads, 0 problems, 1 recorded risk (the same one);
`placement-table.md` regenerates byte-identical. `config_domain.py check`: 12 cells, 0 problems.
`scope_matrix.py --check`: 17 rows, 0 disagreements. `sha256sum -c SHA256SUMS` on `inv-T17-0002`,
`inv-T47-0001`, `inv-T49-0001` and `inv-T49-0002`: every file verifies. Install hygiene on both ticket
49 runs: conf, databases and user `.CUBRID_SHELL_FM` drift 0; the ctltool tree's listing identical
before and after; both testcase worktrees clean (`git status`), the private one at `66b66f1` where
the barrier case is byte-identical to `c4fe45173`. Nothing pushed.
