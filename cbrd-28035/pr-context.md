# CBRD-28035 PR draft context

Resume and publication bookkeeping for `pr-body.md`. This file is not uploaded.

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28035](https://jira.cubrid.org/browse/CBRD-28035) |
| Operation | create (draft PR) |
| Target repository | `CUBRID/cubrid` |
| Base | `feature/oos-merge` (branch point `67220b7e23`) |
| Source repository / branch | `vimkim/cubrid` / `CBRD-28035-serial-oos-chain-leak` |
| Head spec | `vimkim:CBRD-28035-serial-oos-chain-leak` |
| SOURCE_COMMIT | `bee96e66649344d6dfff31740e0746511af5f92a` |
| Remote head at preparation | branch absent on `vk`; no PR for this head |
| Proposed title | `[CBRD-28035] Reclaim the old OOS chain when NEXT VALUE updates a serial` |
| Docs task branch | `docs/CBRD-28035-pr-body` (integration branch `main`) |
| Body | `cbrd-28035/pr-body.md` |
| Context | `cbrd-28035/pr-context.md` |

## Authorization

The user's task brief, given on 2026-11-11 with the request "Read ... CBRD-28035-brief.md in full and execute it",
states: "Push the branch to the personal fork remote `vk`. Create a **draft** PR against `feature/oos-merge`.
The user has authorized this draft PR. Do not mark it ready. Do not merge it." It also says: "Do not push to
`origin`." This is the standing instruction for the operations below.

## Proposed operations

1. Commit `cbrd-28035/` files on `docs/CBRD-28035-pr-body`, rebase onto `main`, fast-forward `main`, push `main` to
   `origin` of my-cubrid-docs (docs merge-to-main push under the user's Git workflow).
2. Push `CBRD-28035-serial-oos-chain-leak` to remote `vk` (`github.com/vimkim/cubrid`), no force.
3. `gh pr create --repo CUBRID/cubrid --draft --base feature/oos-merge --head vimkim:CBRD-28035-serial-oos-chain-leak
   --assignee vimkim --title <proposed title> --body-file cbrd-28035/pr-body.md`.

## Execution record

2026-11-11 (Asia/Seoul), attempt 1. Body SHA-256 at upload `bfa2d16d3566bb014805e065942f31e88366658864edb3f8418bda8f6c130432`.

1. Docs commit `97d0c21` fast-forwarded to `main` and pushed to `origin`.
2. `CBRD-28035-serial-oos-chain-leak` pushed to `vk`; remote head `bee96e66649344d6dfff31740e0746511af5f92a` equals SOURCE_COMMIT.
3. Draft PR created: https://github.com/CUBRID/cubrid/pull/8492. Verified draft, base `feature/oos-merge`, head
   `bee96e666`, assignee `vimkim`, title as proposed. Published body equals `pr-body.md` byte for byte apart from
   the final newline.
