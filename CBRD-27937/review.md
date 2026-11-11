# PR 8454: log encryption review

The goal is to keep values from encrypted tables out of active and archive log volumes, including page-less undo records. The review found no confirmed defect, but it did reproduce an unencrypted **node decision** after an injected page-header lookup failure. The probe stubs the buffer manager and log queue and does not prove that plaintext reaches a real log file. Restart recovery, cipher failures, and the claimed audit of other recovery indices also need follow-up.

**Verdict:** `incomplete`. **Follow-up review required:** yes, before relying on the stated confidentiality guarantee. This is not a merge-safety certification.

## Snapshot and scope

- PR: [CUBRID/cubrid#8454](https://github.com/CUBRID/cubrid/pull/8454), head repository `YeunjunLee/cubrid`, head branch `CBRD-27937`, base `develop`.
- Base and merge base: `2b1db6ca296db20d6bc86eba9f7f69e1866ae10e`. Head: `3ee2faece234768fe158986b4ff7e7960ac6c999`.
- Exact comparison: `git diff --binary 2b1db6ca296db20d6bc86eba9f7f69e1866ae10e 3ee2faece234768fe158986b4ff7e7960ac6c999`. Patch SHA-256: `16312c680f49f89e24bdb7d4bda117cda49a928abfa62193647c85d09fc875bb`.
- Changed paths: `src/storage/tde.h` and `src/transaction/log_manager.c`, 24 additions and 6 deletions. PR 8402 is a separate review and is not assumed merged.
- Intent: [CBRD-27937](https://jira.cubrid.org/browse/CBRD-27937) and the PR description. The [manual](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/security.rst#L187-L192) states that log data related to encrypted tables is encrypted in active and archive logs.
- Ref recheck: At 2026-11-11 10:51 UTC the GitHub connector returned the same base, head, branch names and head repository; no delta review is required for this snapshot.

## Confirmed findings

None. A stubbed boundary test is not evidence of a persisted leak, and no database or recovery execution was performed.

## Unverified risks

### R1. Lookup failure queues a page-less key without the encryption flag

The changed [undo path](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/transaction/log_manager.c#L2370-L2405) copies the undo record, attempts a conditional lookup of the index file's TDE algorithm, substitutes `TDE_ALGORITHM_NONE` on failure, then queues the node. The [index builder](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/storage/btree_load.c#L4740-L4794) can supply a key-bearing `RVBT_MVCC_NOTIFY_VACUUM` undo with a VFID and no page. [The file-header lookup](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/storage/file_manager.c#L5880-L5903) returns an error if the page fix fails. The buffer fix can return NULL on transaction interruption, and a conditional latch also rejects incompatible ownership. A fresh or otherwise unmarked log page and a subsequent flush are needed for plaintext on disk.

Two reviewers independently challenged this path. A competing file-header writer during the relevant notification remains unproven: parallel workers queue notifications and the leader drains them after worker completion. A transaction interruption or other fix error is a separate plausible trigger. A retained harness compiled the exact pinned `log_append_undo_crumbs`, `file_get_tde_algorithm`, internal algorithm reader, `prior_set_tde_encrypted`, and classification macro with explicit dependency stubs. On the head, it observed `queued=1 encrypted=1` for a successful page-less lookup and `queued=1 encrypted=0 marker_intact=1` when the stubbed `pgbuf_fix` returned NULL. The coordinator independently reran it with the same result. This proves the local decision under injected input; it does not execute the actual buffer manager, queue, log flush, or database. The base test queued the same record unencrypted even on the successful lookup. This is a potential **incomplete fix**, not a newly introduced leak.

**Next check:** on an isolated matching server, generate a key-bearing notification from an encrypted index and inject or cause a real header-fix failure. Force a flush, scan raw active and archive log pages for a unique incompressible key, record transaction outcome, and rule out masking by another marked record. Do not replace the conditional latch blindly: lock ordering must remain safe. Owner: systems and recovery.

### R2. Restart undo can queue an unmarked compensation record after page-fix failure

In an `NDEBUG` build, if restart undo cannot fix the target page for a relocated-row vacuum undo, [recovery](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/transaction/log_recovery.c#L200-L216) proceeds to [append compensation with a NULL page](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/transaction/log_recovery.c#L390-L399). The [compensation path](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/transaction/log_manager.c#L3186-L3204) skips encryption marking when the page is NULL, while the copied undo data can contain the row. Whether the resulting node is flushed before recovery stops remains untested. The NULL-page behavior existed at the base, which also leaked the original vacuum record; it is a residual confidentiality risk, not an established regression.

**Next check:** create a relocation and crash before the vacuum sysop commits, inject a page-specific fix failure during restart undo in an isolated `NDEBUG` build, and capture restart status, compensation log and raw flushed bytes. Owner: recovery.

### R3. Existing cipher-error and HA-copy behavior limits the claim

The existing [active log writer](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/transaction/log_page_buffer.c#L2332-L2350) and background archive writer clear the TDE flag and write the original page if encryption fails. The existing HA shipping path reads decrypted pages, while copylog re-encryption is guarded by `UNSTABLE_TDE_FOR_REPLICATION_LOG`; no checked-in definition was found. These behaviors precede this PR. A cipher fault or copylog marker scan was not run. Do not infer an all-failures or HA-copylog confidentiality guarantee from this patch. Owner: recovery and HA.

## Coverage and safety facts

The [six classifications](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/storage/tde.h#L131-L136) are present in the pinned macro. Source tracing covers their explicit producers, payloads and normal encryption decisions. The heap-page image path used by server loaddb sets the page's file-derived TDE flag before logging populated contents; the earlier initialization record has zero payload. This is a source-level result, not a loaddb test. Metadata-page slack bytes and dynamically selected or unlisted indices were not exhaustively audited.

On the successful path, a marked prior node marks current and continuation log pages, which existing writers encrypt and readers decrypt. The patch does not change log record layout or introduce a new HA decoder. Source tracing covered the primary log, archive, backup, utility, and HA consumers. None was exercised end to end, including crash restart, backup restore, replication, page boundaries, AES and ARIA. The author's broader assertion that all other relevant recovery indices contain no user data was not independently verified. See [coverage](coverage.md) and the specialist evidence retained with this review.

The source-only hypothesis that parallel shard workers themselves append notifications concurrently with the leader's allocations was rejected: they queue notifications for the leader. The hypothesis that the loaddb full page is necessarily logged before its TDE flag is set was also rejected for the traced path. No evidence supports dropping R1 or R2. Existing copylog and cipher error risks are separate from introduced changes.

## Verification and limits

The following commands ran in the original local review directory `/home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/8454` against its detached pinned source. The probe scripts remain local:

```text
git diff --check 2b1db6ca296db20d6bc86eba9f7f69e1866ae10e 3ee2faece234768fe158986b4ff7e7960ac6c999
# exit 0; no output
python3 evidence/check_tde_macro.py
# exit 0; all six additions classified; synthetic unlisted index excluded
python3 evidence/systems-probe.py
# exit 0; head: page_less_success queued=1 encrypted=1;
# page_less_fix_failure queued=1 encrypted=0 marker_intact=1;
# page_backed queued=1 encrypted=1. Base: all three encrypted=0.
```

The macro test compiles the exact extracted production macro using synthetic enum constants; it does not compile the complete header. The other probe extracts exact source functions from both commits and replaces external dependencies with stubs, including the fault and queue. The coordinator inspected its script and reran it; raw output is `evidence/coordinator-replay.log`. No build, real log flush, fault-injected database, restart, loaddb, archive, backup, or HA run was performed. The author-supplied marker counts in the PR were not independently replayed. Source checkout was clean at inspection. Starting `gh-pr-info` exited 2 with multiple historical matches, so explicit PR metadata was resolved through the GitHub connector.

## Budget and adjudication

Three specialist seats were allocated 12 minutes each with an 8-minute checkpoint, plus an 18 agent-minute coordinator reservation; total target 54 agent-minutes. No hard cap was enforced and no explicit user spending ceiling was provided. Weekly allowance observation was 93% remaining at about 2026-11-11 10:40 UTC; concurrent activity prevents per-agent attribution. Actual model and termination data: systems: `gpt-6.1-sol` xhigh; recovery: `gpt-6.1-terra` xhigh; HA: `gpt-6.1-sol` xhigh. All three returned before the 12-minute target; precise per-seat duration and usage were not recorded, so time and usage overshoot cannot be quantified. A checkpoint was collected early from each seat; HA described its own checkpoint as eight minutes, but no independent eight-minute timer was recorded. The coordinator also completed independent source inspection and harness replay; its usage is unknown. No additional seats, retries, or runtime resources were used. Reviewers traced sources independently; the shared question was investigated by systems (`gpt-6.1-sol`, xhigh) and recovery (`gpt-6.1-terra`, xhigh). HA independently corroborated the failure branch. Reviewers proposed no other confirmed defect. Rejected hypotheses and retained risks are listed above; source agreement is not runtime proof.


Review date is 2026-11-11 in Asia/Seoul. The parent coordinator independently replayed the retained probes. Raw logs, the manifest, specialist notes, and build artifacts remain in the local run directory `/home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/8454`. The evidence and limitations needed to assess this report are stated above.

The parent rechecked the PR base and head through the GitHub connector at 2026-11-11 10:54 UTC. Both still matched this snapshot.
