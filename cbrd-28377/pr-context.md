# CBRD-28377 PR draft context

Not uploaded material. Resume metadata for `cubrid-pr-create`.

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28377](https://jira.cubrid.org/browse/CBRD-28377) |
| Source commit | `ebdd0f0462ab32312d897805c09c207dfde550d3` (single commit on base) |
| Source repository / branch | `vimkim/cubrid` (`vk`) / `CBRD-28377` |
| Observed remote head | none at preparation (checked 2026-11-25); after the approved push: `ebdd0f0462ab32312d897805c09c207dfde550d3` |
| Base | `CUBRID/cubrid` `develop` at `ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e` |
| Target repository | `CUBRID/cubrid` |
| Operation | `create` (done: [CUBRID/cubrid#8757](https://github.com/CUBRID/cubrid/pull/8757), draft) |
| Proposed title | `[CBRD-28377] Defer OOS notification reclaim on a timed-out wait` |
| Body | `cbrd-28377/pr-body.md` |
| Detailed explanation | `cbrd-28377/verification.md` (not linked from the body) |
| Docs branch | `docs/cbrd-28377`, integrated into `main` |

## Proposed publication operations (approved 2026-11-26)

1. `git push vk CBRD-28377` (new branch on the personal fork).
2. Create a **draft** PR `vimkim:CBRD-28377` → `CUBRID/cubrid:develop` with the title above and `pr-body.md` as the body, assigned to `vimkim`.
3. After the PR exists: TC Branch Sync creates `tc/pr-<N>` PRs. No TC change is expected (the change adds unit tests only); keep those TC PRs open until the merge handoff.
4. Trigger CUBRID CI once (`/run`) through `cubrid-ci-trigger`, wait, and report.
5. JIRA `Confirmed -> Develop` transition.

The user approved steps 1, 2, 4 (as `/run all`) and 5 on 2026-11-26, in the session after the stop gate.

## Execution record (2026-11-26)

| Operation | Result |
| --- | --- |
| Source push | `git push -u vk CBRD-28377`; remote head verified `ebdd0f0462ab32312d897805c09c207dfde550d3` |
| Draft PR | [CUBRID/cubrid#8757](https://github.com/CUBRID/cubrid/pull/8757): draft, `vimkim:CBRD-28377` → `develop`, assignee `vimkim`, title as proposed. Published body equals `pr-body.md` (SHA-256 `194ad690740114bf...`) |
| TC Branch Sync | [cubrid-testcases#4476](https://github.com/CUBRID/cubrid-testcases/pull/4476), [cubrid-testcases-private-ex#5169](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5169) (draft). Baseline check PASS in both. No TC change needed; keep open until the merge handoff |
| CI | `/run all` ([comment](https://github.com/CUBRID/cubrid/pull/8757#issuecomment-7179436351), 2026-11-26T01:06:18Z) → [gha-ci run 45733438019](https://github.com/CUBRID/cubrid/actions/runs/45733438019) attempt 1; `cubrid-ci-watch` request #110 |
| JIRA | CBRD-28377 `Confirmed` → `Develop` (`Start Develop`), verified |
| CI result | Run 45733438019 attempt 1 finished 2026-11-26T02:10:48Z: **failure**. `build (debug)`, `build (release)`, `test_sql`, `test_medium` and `test_sql_by_cci` passed. `test_shell` failed on 6 shards (07, 24, 31, 34, 37, 44), 1 failed case each. Not analyzed yet. No rerun, per the user's instruction |

## Static check (cubrid-static-check `ca39c2c6a4..52bf95f21e`)

| Check | New |
| --- | --- |
| cppcheck (high-signal rules) | 0 |
| clang-tidy (bugprone-*) | 0 |
| Duplicated code (PMD CPD) | 0 |
| Function complexity (lizard) | 1 flag: `oos_reclaim_notified_chains` CCN 16 → 21 |

Disposition: the flag comes from the two deferral branches (unpack and reclaim). The classification lives in `oos_reclaim_error_is_transient ()` and the error setting in `oos_reclaim_defer_notification ()`, so each branch is one condition and one call. Accepted. The later review fixes (`ebdd0f0462`) did not touch that function.

## Decisions to confirm with the owner

- REMOVE / eager postpone path keeps fail-stop on -1123 (see `verification.md`, "Postpone path policy").
- OOS-CONTEXT §4 and OOS-ADR-0008 decision 3 need the wording amendment proposed in `verification.md`, "Spec conformance".
