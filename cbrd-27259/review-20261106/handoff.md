# Handoff: PR #8416 review follow-up

1. **Goal.** PR #8416 needs defect review before merge. Review is complete at head 9ae07b9491b1393841ecb0f3579752a598bf68ec with verdict changes-required (P3: R1, R2). Follow-up is needed because of these fixes and the open risks U1 to U4.
2. **Repository and comparison.**
   - Repository: CUBRID/cubrid.
   - PR: https://github.com/CUBRID/cubrid/pull/8416.
   - Base and merge base: d52b1889e907abcf84190ec504dde3bc93de260d.
   - Head: 9ae07b9491b1393841ecb0f3579752a598bf68ec.
   - Patch sha256: e7ffb902....
3. **Artifacts.** All files are in this directory: `manifest.md`, `report.md`, `coverage.md`, `reviewers/*/report.md`, `coordinator/replay_*.sh` and `evidence/`.
4. **Open items.**
   - R1: report fires during layout, not at the write.
   - R2: wording of the 16-byte window case.
   - U1: log volume.
   - U2: system-class exemption.
   - U3: report written while a latch is held on the MVCC re-evaluation path.
   - U4: HA row apply.
   - D1: product decision, linked to CBRD-27230.
5. **Inspected scope.** All 22 paths. Remaining checks: SERVER mode, a release build and an HA pair.
6. **Next commands.** Rebuild after the fix. Rerun `coordinator/replay_sys1.sh` and `coordinator/replay_f1.sh`, each with a scratch directory argument. Expected result: reports equal the number of BIGONE rows stored.
7. **Budget.** Best effort. Any new reviewer needs a new allocation.
8. **Proposed assignments.**
   - One reviewer for the fix delta covering R1, R2 and U3.
   - Optionally one server-mode probe for U1 and U2.
9. **Finish condition.** After a fix, revalidate `heap_attrinfo_transform_to_disk_internal`, the REPLACE and ODKU callers and the unit tests.

Resume request: `/cubrid-code-review` delta for PR #8416, manifest `review-20261106/manifest.md`, unresolved R1 R2 U1 U2 U3 U4.
