# Handoff for PR 8402

The user requested a pinned CUBRID correctness review of TDE page deallocation, buffer reuse, and recovery. This bounded review stopped after the prior coordinator turn was interrupted or withheld and the parent coordinator requested a report from saved evidence without new failure injection or more specialist spending. Verdict is incomplete. No database defect was independently reproduced.

Repository and PR: https://github.com/CUBRID/cubrid/pull/8402. Base and merge base `063d84e537cbde1a359f369aabb510b01fe68a00`. Head `35eeb2b05cf9732638207f5011c1eb9d53cd8faa`, `YeunjunLee/cubrid:CBRD-27780`. Comparison is merge base to head. Patch SHA-256 `cf37a1a3ad75712bf115d368831651678ae3c200fe165273b5c33805950057e2`. Both remote SHAs matched at approximately 2026-11-11 10:50 UTC. Recheck before publication, retain this snapshot if moved, and request a delta review.

Artifacts are in `/home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/8402/`: `report.md`, `coverage.md`, `manifest.md`, `patch.diff`, `patch.sha256`, `changed-paths.txt`, `pr-comment.md`, specialist reports in `reviewers/`, and logs and probes in `evidence/`. Policy is `/home/vimkim/my-cubrid/CUBRID.md`; issue is https://jira.cubrid.org/browse/CBRD-27780. See the report for the self-contained source argument and commit-specific links.

- **R1, unverified.** When allocation reuses a separate partial-sector FTAB page, NEW_PAGE clear may erase contents needed by atomic allocation rollback. A crash after the clear record is durable and before initialization is the differentiating schedule. Production helper bodies show the byte mutation with stubbed page dirty/type operations, but full allocation, durability, dispatch, undo, and database behavior are unexecuted. R2 may stop recovery before R1's later state is visible.
- **R2, unverified.** Clear-record physical undo can need an OLD_PAGE fix while the page type is PAGE_UNKNOWN. Source suggests a debug assertion and release recovery error or skipped undo. Existing PR discussion reports a reproduction but has no raw evidence available to this review. No independent integrated run was completed.
- Foreign-flush safety and temporary, HA/CDC, redo and TDE confidentiality are supported by source arguments or narrow helper checks only. No crash, real concurrent flush, encrypted disk scan, replica, CDC stream, or release engine test was performed.

The helper scripts remain in the original local review directory, rather than this published documentation directory. The original owner can replay them with:

```sh
cd /home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/8402
python3 evidence/recovery/probe.py
python3 evidence/concurrency/probe.py
sha256sum patch.diff
```

These scripts extract pinned source bodies but stub the runtime boundaries stated in the report. They cannot independently establish either full candidate. A coordinator replay of both scripts already returned 0 in this session; the parent requested its own replay.

For a later authorized integrated check, use an isolated pinned-head and base build, dedicated install, databases, directories and ports. Never stop shared daemons. For R2, arrange a deterministic crash or abort after clear WAL is durable but before f_init or atomic sysop completion, then observe recovery in debug and release and compare the base. For R1, construct the specific all-items FTAB reuse branch, reach the same boundary, restart, and inspect the restored FTAB entries and successor link; also check a subsequent crash during compensation. A successful completion requires reproducible evidence against the actual database and coordinator replay, or a precise source-based disproof of each candidate and any newly affected callers.

Detached worktree `source/` is pinned at head and has a dedicated build tree. The dedicated installation path is `8402/install`. `debug_gcc` configure succeeded. A build-and-install was stopped while still running, exit 130. It produced no verified installed engine. The CCI submodule is pinned at `df47f014731e977263b25cb5ea53dc6d0846328a`. Preserve these artifacts for the next owner; no shared service was started.

Original target was 68 agent-minutes: four 12-minute seats and 20 agent-minutes coordinator reserve, with 8-minute seat checkpoints. No hard cap or per-agent usage telemetry was available, so remaining allocation and overshoot cannot be calculated reliably. New experiments or additional specialist work need a fresh allocation. The parent owns documentation integration, push, and PR comment; this handoff itself authorizes no publication.

Resume request: apply `cubrid-code-review` using the original local manifest `/home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/8402/manifest.md` and pinned comparison, adjudicate R1 and R2 with isolated integrated evidence, and recheck current PR refs before any publication.


Review date is 2026-11-11 in Asia/Seoul. The parent coordinator independently replayed both retained helper probes. Raw logs, the manifest, specialist notes, and build artifacts remain in the local run directory `/home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/8402`. The evidence and limitations needed to assess this report are stated above.
