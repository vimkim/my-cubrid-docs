# Storage documentation draft PR context

- Ticket. CBRD-28038, Sub-task of CBRD-27537.
- Operation. Create one draft PR in CUBRID/cubrid targeting develop.
- Proposed title. [CBRD-28038] docs(storage): correct guidance and references
- Source repository and branch. vimkim/cubrid, CBRD-28038-storage-docs.
- Source revision. a8e4a31475d81cd8f2ed9cf55a6f7c3174f7e293.
- Original reviewed documentation revision. 1631dac18ad0b2fbf1b97ca141f15bf7e58fc74f.
- Original analyzed engine base. e64a04a79a5842827a124b3f8313516d0da2594c.
- Current fetched base. 9f9f9d7154875df0b2791a1b2a189d1dcf839dc6.
- Observed remote source branch. Absent in the pre-publication ls-remote check.
- Existing matching PR. None found on the original task branch; recheck the ticket branch before creation.
- PR body. CBRD-28038/pr-body.md.
- Companion context. CBRD-28038/pr-context.md.
- Docs task branch. docs/storage-docs-publication-20261111.
- Docs integration branch. main; local integration and docs push are not included in this task.

## Authorization and operations

On 2026-11-11, the user explicitly rejected direct local develop integration and
requested "여기에 subtask 생성하고 무엇을 변경했는지 정리하고 draft PR을 열어줘."
This is the authorization for creation of the specified JIRA child, summary,
necessary personal-fork source push, and the actual draft PR. The source correction
and summary had already been presented in the prior turn. No further publication
confirmation is requested. No source merge is authorized.

The publication operations are a push of the source branch to vimkim/cubrid,
creation of the draft against CUBRID/cubrid develop, and assignment to vimkim.
The standing source instructions also authorize one CUBRID CI run after the push.
No testcase changes are required. Preserve draft status and leave TC PR closure to
the human. Keep both notes task branches locally committed and unmerged.

The explicit poteto-mode instructions determine the PR's Why/What changed/Scope/
Blast Radius/Verification headings. The general CUBRID material checker's fixed
Purpose/Implementation/Remarks heading contract cannot represent this override.
Run and record that structural mismatch, then validate the user-requested headings,
shared links, local-path exclusions, and factual claims directly. This exception
does not waive content, source-head, remote-target, or draft-status checks.

## Publication results

- JIRA child created. https://jira.cubrid.org/browse/CBRD-28038.
- Raw description equals the create dry-run payload; parent, Sub-task type,
  assignee vimkim, and Minor priority were read back and verified.
- Source push verified. vimkim/cubrid CBRD-28038-storage-docs points to
  a8e4a31475d81cd8f2ed9cf55a6f7c3174f7e293.
- Draft PR. https://github.com/CUBRID/cubrid/pull/8486.
- Live PR verification. Body bytes, title, develop base, source repository/branch,
  source SHA, draft status, and vimkim assignment match the prepared material.
- Published body SHA-256. 05c767be6ee3d2cbd1bfd4aef994821ebd8b0a9c735eea49a884024436d46b08.
- CI trigger. One /run all comment at 2026-11-11T07:10:54Z,
  https://github.com/CUBRID/cubrid/pull/8486#issuecomment-6789528271.
- CI run. https://github.com/CUBRID/cubrid/actions/runs/42977613860, attempt 1.
- Pickup. Both builds and all four suites point to that new run and are pending.
- Monitoring. Existing shared poller observed, watcher request 20. The installed
  watcher accepts shell, sql, and medium suites. Extra gh run watch and direct
  50-second GitHub polling were stopped after the user pointed out the duplicate
  monitoring. Remote polling is owned solely by the shared watch CLI at its
  default 15-minute interval; the session consumes its local meaningful events.
  The optional sql_by_cci result will be checked at a meaningful completion event.
- CI outcome. The workflow completed with failure on attempt 1. Both builds and
  test_shell, test_sql, and test_medium succeeded. The optional test_sql_by_cci
  context failed on the same head and run.
- Known issue. The shared cubrid-common known-ci-issues.md entry for sql_by_cci
  covers every branch and is unexpired through 2026-12-09. Classify this as the
  known issue, not caused by this PR; no root-cause investigation or fix was made.
- Watch outcome. Request 20 emitted complete/success event 88 at
  2026-11-11T10:00:13Z. That outcome covers its three registered suites and both
  builds, so it does not override the optional CCI failure or the full workflow
  conclusion. One fresh status snapshot after that meaningful event verified all
  six gha-ci contexts and the workflow conclusion.
- TC Merge Gate. Check TC PRs is failing. Public TC PR 4142 and private TC PR
  4843 remain open with zero changed files. Human closure is required; neither
  testcase PR was closed or merged by the agent.
- Final state. The PR remains a draft targeting develop at the recorded source
  head. Its body is unchanged and was read back again. No additional source push,
  CI rerun, or local develop integration occurred.

The latest-base source review confirmed one required addition for permanent-file
bulk destruction. The final disk/file reference now names header/file-table WAL
flush, bulk buffer discard before sector release, exclusive access, and vacuum
coordination. The source commit contains only the eight Markdown files.

The new-body material checker reported only the expected section-contract mismatch.
The explicit poteto headings, portable paths, shared links, and README links were
validated separately. No content or source-state failure was waived.
