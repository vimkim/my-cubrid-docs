# Sidecar

Sidecar is a proposed replacement for CUBRID OOS. It stores large column values outside the heap record, in a per-heap store of ordinary MVCC heap records, so that scans of small columns read fewer pages. No PR exists yet. JIRA epic: [CBRD-28053](https://jira.cubrid.org/browse/CBRD-28053); PR draft in [../CBRD-28053/README.md](../CBRD-28053/README.md). Engine work happens in the worktree `/home/vimkim/gh/cb/sidecar`, branch `sidecar`, based on `develop` `e64a04a79`. Work-tracker item 772 tracks the project.

Last modified: 2026-11-13, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [explainer.html](explainer.html) | Diagram walkthrough of how the POC code at `sidecar-poc1` `84e24e39f4` stores, writes, reads, versions and cleans up large values, with an OOS comparison and open items (Korean) | 2026-11-13 | 2026-11-13 | Understand Sidecar at a glance from diagrams |
| [design.md](design.md) | The design, acceptance predicates, POC plan and Gate 1 questions | 2026-11-04 | 2026-11-04 | The Gate 1 package the user approves before any engine code |
| [grounding.md](grounding.md) | How the existing engine stores, versions, vacuums, replicates and encrypts heap rows, at `e64a04a79` | 2026-11-04 | 2026-11-04 | Shared engine facts for the design and its reviewers |
| [interrogate.md](interrogate.md) | Adversarial review of the first draft: ten verified findings and their root causes | 2026-11-04 | 2026-11-04 | Evidence for the design revision |
| [decisions.tsv](decisions.tsv) | Decision trail, one row per decision with evidence | 2026-11-04 | 2026-11-04 | Lets a reviewer audit how the design was reached |

An independent Codex design with the same goal, Inner Table, is in [../inner-table/README.md](../inner-table/README.md). It uses a hidden chunk relation with logical value IDs instead of a store file addressed by OID.

Related `develop` defects found during this work are tracked separately as work-tracker items 774 (TDE plaintext in relocation vacuum undo), 775 (relocation vacuum releases the forward page before its sysop commits) and 776 (commit frees saved page space before the commit record). The TLA+ check behind 775 and 776 is `cubrid-verify-heap-slot-undo` in `/home/vimkim/gh/my-cubrid-formal-verification-skills`.
