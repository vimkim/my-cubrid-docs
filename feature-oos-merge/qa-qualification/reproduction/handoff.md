# Handoff: investigate and reproduce suspected OOS-related Linux QA failures

Prepared 2026-09-29. This document transfers the next phase to a fresh agent; it does not start testcase execution.

## Latest user intent

The user wants a new agent to read the QA analysis directory, identify failures plausibly related to OOS, and make those failures reproducible. Begin with **grill-with-docs** together with the user to agree detailed methods, environment, scope, and acceptance signals. Investigate facts independently; use the interview for decisions rather than asking the user to locate information already available.

Earlier requests deliberately limited analysis to reports without reproduction. That restriction governed the completed reporting phase. The latest request introduces a reproduction phase, with methods to be agreed through the interview. Do not start broad QA runs, repairs, answer rewrites, or develop synchronization solely because earlier messages contained suggested prompts.

## Read these artifacts, rather than reconstructing the conversation

Analysis directory:
`/home/vimkim/gh/my-cubrid-docs/feature-oos-merge/qa-qualification`

Read in this order:

1. `README.md` — retained files, evidence boundaries and integration contract.
2. `qa_source_triage_1ec35f8_codex.md` — prioritized action table, all candidate identities, confidence and prospective validation.
3. `triage-rqg-vacuum_1ec35f8_codex.md` — crash signatures, source boundaries, ranked falsifiable predictions and required core/WAL evidence.
4. `triage-expectations_1ec35f8_codex.md` — meaningful assertions versus defensible expectation changes.
5. `triage-develop-fixes_1ec35f8_codex.md` — upstream defect versus possible OOS attribution.
6. `qa_comparison_1ec35f8_codex.md` and `comparison_1ec35f8_codex.json` — exact suite/testcase comparison and raw-page references.

These artifacts already contain counts, stacks, source reasoning and plans. Do not duplicate them into a new speculative report before selecting the next investigation.

Published snapshot:
https://github.com/vimkim/my-cubrid-docs/tree/docs/oos-linux-qa-1ec35f8/feature-oos-merge/qa-qualification

Publication commit: `9e2f1d8668198792cc73f33046ab272d5cb99f97` in `vimkim/my-cubrid-docs`, branch `docs/oos-linux-qa-1ec35f8`. It was deliberately based on remote main to exclude an unrelated unpushed local commit. The temporary publication worktree was removed. The useful files remain in the original local directory; they may appear untracked on local docs main. Do not delete them as incidental untracked files.

## Source and evidence locations

Engine workspace: `/home/vimkim/gh/cb/feature-oos-merge`.
Verified current HEAD: `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21`.
Exact develop QA comparator: `e1c3db19800a0170942cec8b23cac4705efbb6e3`.
There is a pre-existing modified `AGENTS.md`; preserve it. No engine/testcase repairs, develop merge, or testcase reproduction were performed. A preparatory build was performed during the earlier phase; validate current build identity before using installed binaries.

Read `/home/vimkim/my-cubrid/CUBRID.md`, applicable repository AGENTS files, and the complete `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` with relevant ADRs. The local normative context contains working-tree changes outside the docs publication; do not overwrite or publish them incidentally. The integration contract is summarized in the analysis README and recorded locally at `.scratch/oos-develop-merge-repair/review.md`.

Retained authenticated QA snapshots:

- `/home/vimkim/gh/cubrid-qahome-fetcher/runs/20260929-140608-11.5.0.2625-1ec35f8`
- `/home/vimkim/gh/cubrid-qahome-fetcher/runs/20260929-140608-11.5.0.2622-e1c3db1`

The comparison JSON maps records to raw pages. Portal captures include analyzed stack text, not locally available core memory/WAL bundles. Some logs are truncated and HA replay detail pages contain names only. Use cubrid-qa-fetch to retrieve additional accessible evidence; establish whether full backups/cores and exact deployed testcase revisions can be obtained. Never expose credentials or copy whole consoles without redaction.

Available testcase workspace roots:

- `/home/vimkim/gh/cubrid-testcases/feature-oos-merge`
- `/home/vimkim/gh/cubrid-testcases-private-ex/feature-oos-merge`

The corresponding `tc/pr-7990` worktrees are supporting snapshots. Exact QA testcase SHAs remain unknown. Separate HA/CCI/JDBC/RQG corpus assets were not found in those available trees; discover actual access rather than assuming the report's path implies a runnable local testcase. The reports distinguish missing/incomplete develop comparators.

## Interview and reproduction entry

Agree a first bounded target and the meaning of “OOS-related.” Distinguish direct demotion/Resolve/Expand/replication effects, indirect shared-storage changes, a missing upstream develop fix, environment differences, and answer-only differences. Do not infer OOS causality from the branch name or a “big record” filename. Do not assume all additional candidates belong in the same repair campaign.

Use the existing action table to choose and justify targets. RQG and the preserved cardinality assertions warrant special attention, but establish artifact/environment feasibility with the user. Decide whether to reproduce the original tested feature revision first or work on a separately pinned synchronized baseline; preserve both comparison identities. Agree runner, build modes, hardware/configuration, seed/data, containment, timeout and artifact retention, required baseline comparison, and the exact red-capable symptom assertion. Record these decisions using the repository's domain-document layout, without replacing the authoritative OOS specification with session notes.

After agreement, enter diagnosing-bugs through a runnable feedback loop. Confirm the exact original symptom and minimize it; do not substitute a neighboring crash or a superficially passing test. Preserve meaningful cardinality, authorization, logical-data, index and concurrent-schedule assertions. Keep deferred CDC failures visible. Treat missing develop results as unknown, and leave cause labels provisional until differential evidence supports them.

Do not suppress assertions, loosen physical-page invariants, or rewrite answers to make cases pass. This phase is diagnosis/reproduction; engine fixes and publication should follow the agreed scope, not happen implicitly. Track substantive reproduction work expected to exceed 30 minutes. Work item 213 records completed analysis/publication and has status done; register the new reproduction effort distinctly.

## Suggested skills

Call these through the Skill tool when available; otherwise read their SKILL.md files.

- **grill-with-docs**: `/home/vimkim/.agents/skills/grill-with-docs/SKILL.md`. Start here; its implementation invokes **grilling** and **domain-modeling**. Resolve workspace/doc layout during the interview.
- **diagnosing-bugs**: construct and prove the red-capable feedback loop before runtime hypothesis testing or repairs.
- **cubrid-oos-context** and **cubrid-common**: authoritative OOS context and exact environment/runtime preflight.
- **cubrid-qa-fetch**: authenticated additional QA evidence; **cubrid-jira** for issue context if needed.
- **cubrid-build**: build exact pinned source revisions through the live preset-aware interface.
- **cubrid-test-sql-run**, **cubrid-test-shell-run**, or **cubrid-test-medium-run**: use only the skill matching the selected suite; prove verdict-bearing artifacts and containment. Do not use SQL/shell runners as substitutes for isolation/HA/RQG. Discover those suites' supported native/QA workflow separately. Legacy CTP execution requires explicit agreement, rather than being an implicit fallback.
- **track-work**: durable registration, evidence and handover for the reproduction effort.

## Suggested opening message to the new agent

“Read this handoff and the referenced QA directory. Use grill-with-docs with me to choose suspected OOS-related failures and agree detailed reproduction methods. Inspect available evidence and runners first. Do not launch tests or change code/answers until we have agreed the first bounded reproduction plan.”
