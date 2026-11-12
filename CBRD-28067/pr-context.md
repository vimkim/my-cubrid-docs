# CBRD-28067 publication context

## Source and target

- Ticket `CBRD-28067`, parent `CBRD-27881`.
- Source repository `vimkim/cubrid`, branch `CBRD-28067-oos-test-1min`.
- `SOURCE_COMMIT` is `158f80bba0a2b86306044661ca6385ec2cfbc5bd`.
- Local source commits `2afb8d716e` and `158f80bba0` contain four test files. Both use the ticket prefix and a model co-author trailer.
- The user explicitly requested a push to remote `vk`. That push is complete. The observed remote head equals `SOURCE_COMMIT`.
- Target repository `CUBRID/cubrid`, base `feature/oos-merge`.
- Observed base `67220b7e230ff1587ba5940001d72e10477a1fc4`.
- Operation `create`. No open PR matched this head, base and author during preparation.
- Proposed title `[CBRD-28067] Cap OOS CTest entries and parallelize workspace`.
- Create the PR as a draft and assign `vimkim`.

## Saved documents

- Docs task branch `docs/CBRD-28067-oos-test-1min`, integration branch `main`.
- Body `CBRD-28067/pr-body.md`.
- Context `CBRD-28067/pr-context.md`.
- Detail `CBRD-28067/verification.md`.
- Index `CBRD-28067/README.md`.
- Supporting files `CBRD-28067/entry-times.csv`, `CBRD-28067/case-times.csv`, and `CBRD-28067/check-ctest-coverage.py` substantiate the detail.
- Intended public detail URL `https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-28067/verification.md`. This URL must be published before PR creation.
- Body SHA-256 `8f6f65c4036ae50a7ec311c5f600012daafe042aadb78071c618c3b0465ca90f`.
- Detail SHA-256 `6a746cd0d293d685d58b6c1ca084170ab4f34b2c47f81cfee2fada8069b54a0d`.

## JIRA description

- The user requested adding feasible parallel execution to this same issue and changing its description on 2026-11-12.
- Proposed scope permits six private workspace groups and pure tests to overlap. Shared DB fixture operations remain serial.
- Notes repository `vimkim/my-cubrid-jira`, task branch `docs/CBRD-28067-parallel-scope`, integration branch `main`.
- Report `issues/CBRD-28067-oos-test-runtime.md`, local task commit `60b0ef0`.
- Report SHA-256 `a6911adc694bc114dc543d5d97d9061f04613f309002b10693aed542b87225cd`.
- Keep the existing live summary. Change only description of `CBRD-28067`.
- Duplicate search returned 20 candidates with complete index and search, synced 2026-11-12T08:32:41Z. Ignore the issue itself. No separate duplicate was found. CBRD-27883, CBRD-27424 and CBRD-27880 cover related helper or functional-test work.
- Description conversion dry-run contains one PUT request to the exact issue and only the description field. BMP and shared-link checks passed.
- The original notes checkout has unrelated dirt in `issues/CBRD-27259-storage-force-inline_bc8a895_codex.md`. Preserve it. A separate clean integration checkout is prepared for notes main integration.

## Proposed remaining operations

1. Rebase the docs task branch onto current local main, review and check, fast-forward merge, and push docs main. Include the body, context, verification, index and three supporting files named above.
2. Rebase and integrate the JIRA notes task commit into clean notes main, check and push notes main. Preserve the original dirty checkout.
3. Publish the already requested description-only JIRA update from the reviewed pushed file and verify the live description against its converted payload.
4. Create the draft PR with the exact reviewed body, proposed title, head and base above, and assign vimkim. Verify its state, refs and body.
5. Record publication outcomes in this context, check and commit the execution record, and integrate/push it under the same publication approval.

No CI trigger is proposed. PR creation awaits explicit confirmation after this body preview under cubrid-pr-create. The requested JIRA change is authorized; document main integration and push still follow the user's Git approval gate. This context records a proposal and completed observations, not an approval token.

## Review and current limits

The independent available model gpt-6-astra reviewed the active task transcript, decisions and raw evidence. This is an independent model review within the OpenAI family. Two documentation findings were corrected before review handoff. Write-open paths were disjoint, while Java also cleaned an already exited peer JVM performance file after ESRCH. The time-reduction choices were added to the append-only trail. No source behavior fix followed from this review.

All final serial and parallel full runs passed. The serial run under lower machine load had a maximum of 24.96 seconds. The busier runs had maxima of 36.32 and 45.26 seconds. All entries stayed below 60 seconds. These runs do not establish one universal whole-suite speedup ratio.
