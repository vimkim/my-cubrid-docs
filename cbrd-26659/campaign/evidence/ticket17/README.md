# Evidence for CBRD-26659 campaign ticket 17 — representative timings and tier placement

Record: [`../../CBRD-26659-representative-timings-tier-placement_f4299ac_claude.md`](../../CBRD-26659-representative-timings-tier-placement_f4299ac_claude.md).
Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`, re-pinned without the unit-test seams by
[ticket 41](../../CBRD-26659-repin-without-unit-test-seams_f4299ac_claude.md) (`release_gcc_nounit`,
`debug_gcc_nounit`); instrumentation install `oos-instr-f4299ac0c/debug_gcc_nounit`, patch set `t16-set1`.
Bulky artifacts stay under `~/.cub/campaign/cbrd-26659/ticket17/` and are listed with sha256 in
[`SHA256SUMS-bulky.txt`](SHA256SUMS-bulky.txt) (1,328 files; database volumes are excluded, being
reproducible from the probes).

| Path | What it holds |
|---|---|
| `inv-T17-000{1,2,3,4}.json` | Four campaign manifests: the public tracer case alone, the nine-case public suite, and the private crash-and-recover case on release and on debug. `inv-T17-0001`'s proof verdict is `failure-of-proof` and is explained in §7 of the record: it is a finding about ticket 15's tooling, not about the case, which PASSed. |
| `att-T17-00{01..12}.json`, `bundle-att-T17-00{01..12}.json` | Twelve attempt records and their replay-bundle indexes, written by ticket 15's tooling. |
| `matrix.json` | Ticket 17's coverage matrix: 17 rows, every one PASS with proven OOS-path evidence. |
| `scope_matrix.py` | Adopts the hand-set gap kinds of tickets 19 and 41 onto those rows, so a re-measurement cannot widen a coverage claim the ticket that wrote the case had qualified. `--check` re-verifies it. |
| `config-domain/*.json` | The twelve cells of the configuration domain, one file per cell, each naming the engine commit, the four binary hashes, the page size the engine read back, the OOS-path evidence and the value roundtrip. Produced by [`../../tools/config_domain_probe.sh`](../../tools/config_domain_probe.sh), judged by [`../../tools/config_domain.py`](../../tools/config_domain.py). |
| `measurements.json` | Every measured quantity the placement rests on, derived from the probes' own outputs and from the retained CTP bundles of tickets 13, 14, 15, 17, 19 and 41 — never typed by hand. Written by `build_model.py`. |
| `tier-placement-model.json` | The caps and the workloads, the input `tools/tier_placement.py` computes the placement from. |
| `placement-table.md` | The rendered tier-placement table, regenerable with `tools/tier_placement.py place`. |
| `probes/seed-cost-{10-fresh,100-fresh,100-reused}.json` | Per-seed times of the seeded out-of-row churn workload: ten seeds and one hundred with a fresh fixture each, and one hundred on a reused fixture. Each seed records its phases and the `SHOW HEAP OOS` figures that show it reached the OOS path. |
| `probes/barrier-cost.json`, `probes/barrier-journal.txt` | The multi-session barrier MECHANISM, four participants over three acknowledged barriers. The barrier SCENARIO does not exist and is recorded as a Delivery gap; this measures what ticket 23 will build on. |
| `probes/instr-a1/` | The instrumented fault scenario ticket 17 re-ran (site a1, code 700000), fault and fault-disabled control, under `campaign_ns.sh`. |
| `probes/instr-site-walls.json` | The wall time of all twelve validated sites, fault and control, read out of `evidence/ticket41/instr-sites/run-all.log`. |
| `probes/resource-summary.json` | Peak and p95 CPU, peak resident memory, peak process count and storage delta of every invocation and probe, measured by [`../../tools/resource_sampler.py`](../../tools/resource_sampler.py). |

Reproduction: every tool names its own inputs on the command line and the record's §11 gives the
exact invocations. The configuration domain and the placement each have a checker that fails before
it passes — `tools/selftest_config_domain.py` and `tools/selftest_tier_placement.py`.
