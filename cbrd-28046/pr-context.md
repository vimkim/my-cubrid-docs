# CBRD-28046 PR draft context

- Ticket: CBRD-28046 (develop, Improve Function/Performance; assignee set by the user to the team lead)
- Source repository/branch: vimkim/cubrid `CBRD-28046-commit-postpone-flush`
- SOURCE_COMMIT: 6a7ca6b4a89e5dd96bfea81b9f6655893641b9a7
- Base: CUBRID/cubrid `develop` (branch point 2d1513a8af)
- Observed remote head: branch does not exist on `vk` yet
- Target repository: CUBRID/cubrid; operation: create (draft)
- Proposed title: `[CBRD-28046] Flush the log once per commit with postpone actions`
- Request: the team lead asked "작업해두셨나요? 해두셨으면 PR을 올려주시면 거기서 검토할께요"; the user asked to open a develop-targeted draft PR (2026-11-11).

## Files

- Body: `cbrd-28046/pr-body.md`
- Context: `cbrd-28046/pr-context.md`
- Test scripts and results: `cbrd-28046/test/` (public URL linked from the body)

## Proposed operations

1. my-cubrid-docs: commit on `docs/cbrd-28046-pr`, rebase onto `main`, `git merge --ff-only`, push `main` (the body links `cbrd-28046/test`).
2. Source: `git push vk CBRD-28046-commit-postpone-flush`.
3. `gh pr create --draft --repo CUBRID/cubrid --base develop --head vimkim:CBRD-28046-commit-postpone-flush` with the title above and `pr-body.md`; assign `vimkim`.

## Evidence

- Premise audit of every `log_append_postpone` site: only `RVHF_LOB_REMOVE_DIR` (`locator_sr.c` `xlob_remove_dir`) has a non-WAL effect.
- Postpone crash test: 24 SIGKILLs during a 300-table DROP commit, release build of SOURCE_COMMIT; 0 partial, 0 lost acknowledged, checkdb 0 failures (`test/postpone-crash-results.csv`).
- LOB crash test under gdb (`test/lob_crash.sh`): kill after the LOB files are removed. This PR: table dropped after restart. Variant without the LOB guard: table back, 5 rows, all `BLOB_LENGTH` NULL.
- Not run: ctest, CI, debug-build crash test (CBRD-27987 makes debug analysis assert after a crash during nested postpone).
- Observation: a kill at the entry of `fileio_lob_remove_matching_dir` (before removal) left the 5 LOB files after recovery finished the drop; not checked whether develop without this change behaves the same.
