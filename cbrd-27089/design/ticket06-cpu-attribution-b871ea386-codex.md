# Ticket 06: small-inline CPU work attribution

2026-09-09. Follow-up to the user's request to perform the next step after the [same-host interleaved measurements](ticket06-interleaved-b871ea386-codex.md).

## Result

The candidate performs **repeatably more user-space instructions** for small-inline INSERTs: approximately **+0.689% over the entire test process**. The nonpartitioned control differs by approximately **+0.00054%**. This is a stable instruction-count difference, **not a measured +0.689% runtime regression**. Runtime no-regression acceptance remains unmet because cycle/time variability still overwhelms precise attribution.

There is a concrete structural cost: **small-inline writes route twice in the candidate, once in the original**. Both implementations serialize the full row once in this case. The candidate adds effective-key preparation and an early routing pass while retaining final record routing and destination agreement checking. Large OOS-producing writes are different: removing their second full-row transformation still provides the already-demonstrated allocation/copy savings.

No engine code, schema contract, or accepted design was changed. Only the local evidence runner gained optional process-scoped profiling modes. Eight counter runs and two sampled-profile runs passed their SQL value, OOS ownership, and rollback checks. No commit or push was performed.

## Method and evidence limits

The diagnosing workflow was used to seek a sharper signal before proposing a fix. The original elapsed-time symptom still lacks a tight, deterministic red/green reproducer. Instruction counters establish a narrower work-count observation; they do not substitute for that missing runtime proof. No causal fix, hypothesis-driven engine perturbation, or regression waiver follows from this report.

- Same baseline and pre-format candidate release binaries as the previous reports: base `b871ea386d2c5419b7abae07dda58b9b7f36377a`; candidate engine diff SHA-256 `3d978ff8134516d0ab26a809b6fd790bd289a6865476a215921c8fa5e6eea34a`. Binary, engine-library, and test-source hashes were checked against the retained diagnostic evidence. This is not an exact benchmark of final integrated commit `213ce80f54dc54130fcef22e616cb28f4835f6d5`.
- `perf` version `5.14.0-570.30.1.el9_6.x86_64`. Read-only capability check found `perf_event_paranoid=-1`; a hardware-counter smoke check succeeded. No system settings were changed.
- Two workloads, each ABBA: small inline and nonpartitioned small. Each fresh process runs 1,024 statements per batch, two warmups, and 51 retained batches. CPU affinity 6; private databases on `/home`; no shared database or unrelated process was modified.
- `perf stat -x ';' -e instructions:u,cycles:u -- <test binary>` wraps **the whole SQL test process**, not database creation by the separate setup script. Counts include process initialization, DDL, SQL execution, both warmups, verification, rollback and teardown. All reported counters have 100% running coverage; no multiplex scaling is needed.
- Hardware counts are additional evidence, not replacements for the harness's narrower timed intervals. The machine remained shared; a read-only load snapshot during this work was 126.34. No load threshold or outlier exclusion was applied.
- Instruction-sampled profiles: one process per side, same workload dimensions, `perf record -e instructions:u -c 2000000 --call-graph dwarf,4096`. Baseline 8,539 samples; candidate 8,598; both reports show zero lost samples. Their instrumented runtimes are not acceptance evidence.
- Symbol reporting disables inline expansion and external debuginfo fetching. Initial report-conversion attempts were stopped after slow symbol processing; inspection identified an active `addr2line` child. Reports were regenerated from the same raw profiles with `--no-inline`, without rerunning the workload or changing samples. Profile call chains can be truncated or affected by optimized calls, tail calls and attribution skid; inclusive percentages overlap and must not be added.

## Hardware-counter results

| Workload | Run | User instructions | User cycles |
|---|---|---:|---:|
| Small inline | A1 | 17,079,681,849 | 25,729,670,409 |
| Small inline | B1 | 17,196,319,024 | 25,008,862,624 |
| Small inline | B2 | 17,196,773,595 | 24,691,726,466 |
| Small inline | A2 | 17,077,973,624 | 15,334,321,485 |
| Nonpartitioned small | A1 | 16,433,321,388 | 13,289,258,931 |
| Nonpartitioned small | B1 | 16,432,974,707 | 13,606,013,617 |
| Nonpartitioned small | B2 | 16,432,803,630 | 13,519,142,195 |
| Nonpartitioned small | A2 | 16,432,279,234 | 13,253,157,432 |

Using each side's mean whole-process instruction count, small-inline B/A is **1.00689266**; nonpartitioned B/A is **1.00000541**. The small-inline difference is about 117.7 million instructions across 53 × 1,024 inserted rows. Dividing gives roughly 2,169 instructions per inserted row, but this is only **amortized whole-process difference**, not a direct measurement of one routing call.

Baseline small-inline instructions differ by roughly 0.01% between its two runs, while its cycle counts differ dramatically. The stable instruction difference and unstable cycle difference are distinct observations. They support investigating added work without claiming that extra work explains the earlier 0–13.6% CPU-time range.

## Source-level operation accounting

These links point to inspected local sources; the baseline worktree remains at the original revision, while main contains the formatted candidate implementation.

1. [Original locator path](/home/vimkim/gh/cb/pr7600-original-baseline/src/transaction/locator_sr.c:7710): creates the demotion-suppressed record. **Only when `would_demote_oos` is true** does it perform early routing and rebuild. Small inline is false, so the first serialized record is retained and only the later force routes it.
2. [Candidate locator path](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/transaction/locator_sr.c:7767): every scoped partitioned INSERT performs `partition_prune_insert_by_attrinfo`, transforms once with the selected OOS owner, then invokes final force. There is no small-inline exemption.
3. [Attribute routing](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3571): uses the context-owned key slot; clears its prior value, obtains the effective key, evaluates/matches the partition expression, copies the destination, then clears the temporary key. Context initialization is conditional, not necessarily a new context allocation per row.
4. [Effective-key preparation](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12117): the assigned, non-NULL integer in this workload follows the clone → disk-size → write/read codec path. The four-byte codec fits the stack buffer; the `length > 64` heap-allocation branch is not taken. Defaults, unchanged UPDATE keys and increments are other contracts, not exercised by this specific small-inline INSERT measurement.
5. [Final force](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/transaction/locator_sr.c:4990): still routes the serialized record, checks agreement with the early destination, then continues existing locking and write behavior. The accepted [ADR](../../../docs/adr/0001-pr7600-effective-key-routing.md) explicitly retains this stage.

The earlier scoped debugger counts corroborate this operation accounting without inferring call counts from sampled stacks. Warm batch, **two rows**:

| Operation / scoped resource | Original | Candidate |
|---|---:|---:|
| Full-row transformations | 2 | 2 |
| Early attribute routes | 0 | 2 |
| Final record routes | 2 | 2 |
| Effective-key preparations | 0 | 2 |
| Key-codec serialized bytes | 0 | 8 |
| Scoped private allocation bytes | 592 | 592 |
| Tracked temporary peak bytes | 16,680 | 16,680 |

Sources: `PR7600_DIAGNOSTIC` immediately preceding the `small_inline`, `rep=0` sample in [baseline](ticket06-evidence/baseline-diagnostic-final.json) and [candidate](ticket06-evidence/candidate-diagnostic-final.json). Allocation scope is exactly that of the earlier observer, not every process allocation. This case does not support blaming an extra heap allocation or an extra full-row serialization.

## Sampled distribution

| Candidate function | Inclusive instruction-sample share | Self share |
|---|---:|---:|
| `partition_find_partition_for_attrinfo` | 0.79% | 0.06% |
| `heap_attrinfo_get_effective_key` | 0.12% | 0.06% |
| `partition_find_partition_for_record` | 0.65% | 0.07% |

The key helper is nested inside early routing. These are rounded statistical shares with finite stack capture, not precise standalone costs. The profile supports directing attention at the **whole additional route**, not assuming integer serialization dominates it. It cannot allocate all 117.7 million extra instructions exactly among functions; shared functions, initialization, sampling and optimized call stacks prevent that inference.

## Design implications and next decision

There is no free generic removal of the second route within the current accepted contract:

| Option | Potential scope of saving | Contract / risk |
|---|---|---|
| Retain current candidate | Keeps proven large-value allocation/copy savings | Accepts measured extra instruction work; runtime gate is still unresolved, not waived |
| Shortcut the integer codec | Only part of effective-key preparation | Must prove stored-value equivalence; small sampled share and no evidence it dominates; do not add type special cases speculatively |
| Reuse the early destination in final force | Can remove duplicate expression/matching work | Reopens explicitly retained final routing; must preserve final validation, representation-ID handling, locks, indexes, movement and disagreement detection |
| Skip early routing when a row is proven non-OOS | Targets this small-inline case | Needs a trustworthy no-OOS decision after relevant normalization/defaults/increments and before OOS writes; raw caller sizes are not such a proof. Must not recreate the full probe or duplicate stateful preparation |

**Recommendation:** keep engine code unchanged and take the measured extra-route cost into a narrow design review. If pursuing another optimization, examine destination reuse with preserved final-force responsibilities before adding a scalar codec special case. This is a candidate for review, **not an approved design or a proven minimal patch**. A preparation/layout classification alternative should be compared explicitly if preserving independent final validation is non-negotiable.

The review must decide whether reducing this small measured instruction cost warrants reopening the final-routing safety contract. Instruction overhead alone neither establishes an unacceptable runtime regression nor authorizes accepting one. Final integrated measurements and the existing server lifecycle gate remain separate obligations.

## Reproduction artifacts

Subsequent design-only review: [destination reuse](destination-reuse-review-213ce80f5-codex.md). Final routing has representation and metadata effects in addition to selection. The review recommends retaining it for this PR; no replacement design has been approved.

- [Evidence directory](ticket06-evidence/cpu-attribution-20260909/): eight `perf-*.json` counter runs, two `profile-inline-*.json` runs, and two `profile-summary-*.json` symbol reports. Every run records exact commands, source diff and hashes, private fixture, all SQL samples and tool output.
- [Summarizer](ticket06-evidence/summarize-cpu-attribution.py): `python3 summarize-cpu-attribution.py` validates all ten runs against prior binary provenance, expected samples/rows and affinity; validates counter coverage and reproduces instruction ratios and symbol summaries. It prints observations, **not a runtime pass/fail assertion**.
- [Isolated runner](ticket01-evidence/run-isolated.py): optional `--perf-stat` / `--perf-record`, mutually exclusive with debugger and non-SQL modes. Unique labels prevent overwriting earlier evidence. The report flag was added during the stat sequence; each run records its runner hash and exact command, and the stat command semantics did not change.
- The raw `perf.data` files (approximately 35 MB each) remain at the private `/home` fixture paths recorded in their JSON files; they are not copied into the documentation repository. JSON symbol summaries remain readable without those raw files.
