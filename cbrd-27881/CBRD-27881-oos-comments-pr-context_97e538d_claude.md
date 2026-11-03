# CBRD-27888 oos-comments PR draft context

- Ticket: CBRD-27888 (sub-task of CBRD-27881)
- SOURCE_COMMIT: 97e538d3539bb462d28f96fa941f21995cac2adb
- Agent: claude
- Source repository and branch: vimkim/cubrid, `CBRD-27881-oos-comments`
- Base: `feature/oos-merge` (tip dcbf09e4f2 at preparation)
- Observed remote head before publication: branch absent on `vk` (new PR)
- Target repository: CUBRID/CUBRID
- Operation: create
- Proposed title: `[CBRD-27888] Correct OOS comments that state false facts`
- Docs task branch: `docs/CBRD-27881-oos-refactor`; integration branch: `main`
- Body: `cbrd-27881/CBRD-27881-oos-comments-pr-body_97e538d_claude.md`
- Context: `cbrd-27881/CBRD-27881-oos-comments-pr-context_97e538d_claude.md`
- No explanation document.

## Proposed operations

1. Push `CBRD-27881-oos-comments` to the `vk` remote, no force.
2. Create the draft PR on `feature/oos-merge` (assignee vimkim) no earlier than 06:58 KST (PR 6 opens at 05:58), via scratchpad/publish_pr.sh.
3. After the tc branch sync, `cubrid-pr-tc-base-check-oos --pr N`, then one `/run all`.
4. Keep docs commits local; integrate into `main` and push during the CBRD-27881 final write-up.

## Authorization

The user wrote on 2026-11-03 at about 00:20 KST, before going to sleep:
"만약 좋은 후보가 나오면, draft PR을 생성해줘. 1시간마다 하나씩만 생성하고, subagent로 코드리뷰를 마친 뒤 고칠 점이 없으면 /run all 을 날려줘. 만약 고칠 점이 있다면 알아서 고치고 ci 를 돌려줘."
At 02:01 the user suggested one CBRD-27881 sub-task per PR; CBRD-27888 was created for this PR.

## Verification evidence before publication

- Owner (sonnet): 11 candidate comments proven false with file:line evidence; token diff empty except the removed empty `if`; build clean.
- Review lane (opus, independent): ISSUES at 70e782fd. Every new comment fact-checked OK and the token diff reproduced; two issues where the same "SA_MODE" fact stayed wrong in functions the PR already edits (heap_file.c ~24725, ~25212, ~24888), plus five wording nits.
- Coordinator fix (97e538d3): applied both issues with the reviewer's text, applied the nits (vacuum.c wording, vacuum_oos.cpp TODO, update_old_home wording, `!is_mvcc_op` phrasing, locator.h function names), reflowed comments to ≤120 columns, GNU indent unchanged, token diff still only the empty `if`, build 0 warnings. Wording-only fix round, so no second verifier.

## Execution record

- 06:59 KST: published with scratchpad/publish_pr.sh: pushed to `vk` (remote head 97e538d3539bb462d28f96fa941f21995cac2adb); created draft PR https://github.com/CUBRID/cubrid/pull/8373 (assignee vimkim); remote body matches the body file apart from trailing blank lines; TC branch sync SUCCESS; `cubrid-pr-tc-base-check-oos --pr 8373` exit 0; posted `/run all` (https://github.com/CUBRID/cubrid/pull/8373#issuecomment-6589557169); gha-ci run https://github.com/CUBRID/cubrid/actions/runs/41533557379 picked up all five contexts.
