# OOS integration: Linux QA comparison and source triage

Comparison date: 2026-09-29. Feature: `11.5.0.2625-1ec35f8`. Develop baseline: `11.5.0.2622-e1c3db1`.

Start with the [prioritized action report](qa_source_triage_1ec35f8_codex.md). The snapshot contains **46 additional non-CDC candidates across 35 testcase identities**, of which six lack completed develop comparators. This is an evidence-backed investigation, not a completed reproduction or merge qualification.

## Bounded reproduction update

[S04 재현 보고서](s04-reproduction_1ec35f8_codex.md): 별도 exact-source worktree 빌드와 승인된 6회 실행 완료. Feature card11/99986은 3/3 재현됐지만 develop도 기대값을 충족하지 못했다. Native 집계/XML proof gap을 보존했으며 OOS 원인 확정이나 answer 갱신은 하지 않았다.

[합의된 계약](reproduction/spec.md) · [결정 기록](reproduction/review.md) · [handoff](reproduction/handoff.md) · [실행 집계](reproduction/evidence/summary.json). Original source-triage reports below describe the earlier read-only phase; the reproduction report is the later execution record.

## Retained results

| File | Purpose |
|---|---|
| [Source triage](qa_source_triage_1ec35f8_codex.md) | All 23 action families, priorities, confidence, future validation, and first bounded repair recommendation. |
| [QA comparison](qa_comparison_1ec35f8_codex.md) | Suite counts, CDC exclusions, baseline overlap, complete additional-case inventory, and observed symptoms. Updated with the deeper cardinality/core findings. |
| [Develop-fix investigation](triage-develop-fixes_1ec35f8_codex.md) | Five missing baseline commits; direct CBRD-27407 match and integration dependencies. |
| [RQG investigation](triage-rqg-vacuum_1ec35f8_codex.md) | Five analyzed server cores, heap-page lifecycle boundaries, ranked untested predictions, and required core/WAL evidence. |
| [Expectation review](triage-expectations_1ec35f8_codex.md) | Justified diagnostic/layout candidates and assertions that must be preserved. |
| [S04 reproduction follow-up](s04-reproduction_1ec35f8_codex.md) | Six later local attempts reproduced the selected feature cardinalities; develop also failed the assertions, so OOS-specific attribution remains unresolved. |
| [Comparison JSON](comparison_1ec35f8_codex.json) | Complete parsed suite/testcase identities, findings, classifications and archived-page references for both snapshots. |
| [Comparison parser](compare_qa_1ec35f8_codex.py) | Recompute inventory from authenticated fetcher snapshots, preserving suite identity and Java method names. |

Source and testcase citations use pinned GitHub revisions. QA links point to the authenticated portal; private testcase links require repository access. The QA testcase deployment SHA remains unknown, so local testcase snapshots are supporting evidence only. Context citations point to committed revision `75f8b586`; the locally consulted OOS context contained additional working-tree notes, which are outside this publication.

The comparison and source-triage reports describe the initial read-only investigation. The S04
follow-up records a later reproduction batch and its native-runner evidence limits; it does not
establish merge qualification. During repository cleanup on 2026-09-29, rerunning the parser
against the retained raw archives reproduced the committed comparison JSON exactly.

## Integration contract

The agreed integration policy used in these reports treats `feature/oos-merge` as a stable integration branch: synchronize develop with a real merge commit; do not squash develop, cherry-pick it as a substitute for ancestry, rebase, amend, or force-push the integration history. Feature repairs arrive through focused reviewed changes. Pin the chosen develop target, review changes beyond the QA baseline separately, and use CBRD-27407's two isolation failures as the first eventual acceptance target.

The original local decision record is `.scratch/oos-develop-merge-repair/review.md` in the engine workspace. This paragraph preserves the relevant contract without publishing unrelated local planning files. No integration or engine/testcase change was performed for this analysis.

## Recomputing the inventory

The raw QA archives remain in the fetcher's local `runs/` directory. They are not included in this documentation commit; the reports retain the decisive signal and portal URLs. Keep those archives for future detailed HA and RQG investigation. JSON `run` and `pages` fields identify those original archives, rather than files bundled here.

The parser needs `beautifulsoup4` and `lxml`. With the existing `cubrid-qahome-fetcher` environment, run:

```bash
uv run python /path/to/qa-qualification/compare_qa_1ec35f8_codex.py \
  --feature-run /path/to/runs/20260929-140608-11.5.0.2625-1ec35f8 \
  --develop-run /path/to/runs/20260929-140608-11.5.0.2622-e1c3db1 \
  --output /tmp/oos-qa-comparison.json
```

Each input directory must retain `manifest.json`, `failure-report.json`, the raw functional summary, and fetched detail pages. The parser selects only `table[name=linux_func]` and checks every numeric suite's parsed failure count against its summary. It reads evidence; it does not launch testcases or retrieve fresh QA results. Reports include manually reviewed source assessments and should not be regenerated from symptoms alone.

Temporary configure/build logs, Python bytecode, the obsolete report writer, duplicated symptom-excerpt JSON, and the standalone statement-URL scratch file were removed. Their useful findings and statement-level QA links are preserved in the retained reports.
