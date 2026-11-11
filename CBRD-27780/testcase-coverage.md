# Coverage matrix

The goal is to review testcase PR 4737 against CBRD-27780. The sole changed path is `shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh` at head `0f42c42b96fe2ebc9f496f03c3ca5c34f812dc50`.

| Scope and invariant | Owner | Evidence and result | Remaining action |
|---|---|---|---|
| Setup, marker scan, control and explicit NOK propagation, lines 65-203 | oracle; coordinator replay | Pinned shell functions with real file fixtures and native testkit verdict tests. F1: read error can produce OK. Syntax passes. | Fail closed on read error; rerun the full case. |
| Vacuum/deallocation, scenario 1, lines 205-239 | oracle | Capacity SQL sentinels require zero records/keys and reduced page counts; pinned engine counts overflow pages. Source review only. | Observe actual deallocated VPIDs in contained DB run; no full execution. |
| Buffer reuse, scenario 2, lines 241-267 | oracle | Source checks table size, row scan and markers; author-reported baseline/fix runs have not been independently replayed. | Run fixed and baseline engine in isolated native runner; verify physical scan/reuse. |
| Crash recovery, scenarios 3-4, lines 269-345 | recovery; oracle shared challenge | Both independently found REDO banner does not establish target-page redo. Pinned redo predicate executed with fixture LSAs. Actual page state untested. | R1: deterministic, instrumented crash, target VPID/LSA and disk-image evidence on fixed and baseline. |
| Scenario 4 page reuse, lines 306-324 | recovery; coordinator replay | Exact predicate returns OK for old header 128, old last page 190, new header 128; old header is PAGE_FTAB, not encrypted. Synthetic metadata only. | R2: prove actual same full VPID of an old encrypted page is allocated to the plain file. |
| PID, recovery and key-file cleanup, lines 70-94, 140-155, 325-355 | recovery | Source trace only. Server PID selected by database, xkill sends SIGKILL; no established external cleanup defect. | Native isolated end-to-end execution and verify cleanup; CI CTP revision. |
| Standalone HA, engine performance or source threading | combined/not applicable | Only a shell testcase changes. Relevant engine redo and storage facts traced as dependencies, no engine correctness verdict. | None within this review. |

Shared challenge: do scenarios 3 and 4 prove that affected pages were recovered by redo before prior page flush? Oracle (`gpt-6.1-sol`, xhigh) and recovery (`gpt-6.1-terra`, xhigh) independently answered no proof exists in the test. Full counterexample execution is still required. No reviewer dropped out. Source-only risks are not confirmed defects. Comment inspection was read-only and found no style finding.


Review date is 2026-11-11 in Asia/Seoul. The parent coordinator independently replayed the retained probes. Raw logs, the manifest, specialist notes, and build artifacts remain in the local run directory `/home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/4737`. The evidence and limitations needed to assess this report are stated above.
