# Ticket 03: effective-key UPDATE routing

Date: 2026-09-08. Scope: [ticket 03](../../.scratch/pr7600-effective-key-routing/issues/03-route-updates-and-increments.md) only. Work-tracker: 77. Source HEAD remains `b871ea386d2c5419b7abae07dda58b9b7f36377a`; the working tree already contained tickets 01–02. No commit, push, or later-ticket implementation was performed.

Status: ticket 03 complete. All 72 selected tests pass, both forced increment retries pass, and both independent SQL comparisons match. This is not final design acceptance.

## Change

Partitioned attribute-force UPDATEs now select their destination from an owned effective key and perform the normal full-row transformation once with that destination as the OOS owner. They no longer serialize a complete inline routing probe or rebuild that probe for OOS. Final record-based routing remains authoritative for validation and representation patching, with an early/final destination agreement check before heap/index mutation or partition movement.

The shared INSERT adapter was factored to reuse the same key/context logic; its omission/default contract remains intact. Duplicate detection and its separate record probes were not removed. Nonpartitioned writes retain their existing transformer. Changes are confined to `partition.c/partition_sr.h`, `heap_file.c/heap_file.h`, `locator_sr.c`, and the existing SHOW SQL test file. The preexisting CCI, CMake, prompt, repro, and artifact changes were not altered.

## Contracts and source evidence

| Contract | Implementation and evidence |
|---|---|
| Supplied old row, not another version | [Effective-key reader](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12117) creates an independent **one-attribute** cache only for an uninitialized UPDATE key. It calls [the without-OID reader](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:11160), which recaches the supplied record's representation. It does not fetch a different heap version or change the write cache's representation. |
| Historical missing key/default | The existing [attribute reader](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:10641) supplies the latest attribute's stored default when the historical representation lacks that attribute. The result is cloned before the private reader ends. INSERT still uses the existing omission/default reader. |
| Assigned values and column domains | Assigned values are cloned; the existing scalar write/read round trip uses the column domain, preserving CHAR padding and string normalization. Upstream evaluated values are consumed, not evaluated again. The adapter prepares no unrelated column. |
| Pending INCR/DECR | The temporary key uses the existing [qdata increment operation](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/query_opfunc.c:2911). The source value/state/pending flag remain intact. The [first-pass owner wrapper](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12928) passes `increments_already_applied=false`; the real fixed-column writer and its retry-local set remain unchanged. |
| Context identity and duplicate probes | [Shared attribute routing](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3570) retains the expression-bound context slot, clears its previous value, loads the effective key, selects through the shared expression evaluator, then clears the value again. This does not reset the original write cache. |
| Root/child discovery and final routing | [UPDATE context/validation wrapper](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3847) retains the original root lookup from the physical child, supplied-context rules, and explicit-partition validation. The existing record adapter still patches representation IDs. [Final agreement check](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/transaction/locator_sr.c:6021) runs before destination locking/movement and heap/index writes. |
| OOS ownership and old versions | [Attribute force](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/transaction/locator_sr.c:7766) passes the selected destination to normal first-pass preparation. [OOS insertion](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12888) uses that class as owner. Existing serialization, fresh OOS insertion, movement, and old-version reclamation code are unchanged; no chain-reuse or early-delete mechanism was added. |
| LOB and error ownership | Only the legal partition key is read/prepared early; BLOB/CLOB lifecycle work remains in full-row preparation. The private key reader, temporary scalar, and codec allocation are cleaned on their normal/error paths. Final disagreement follows the existing statement error/rollback path; it does not manually delete OOS chains. Exhaustive failure injection remains ticket 04. |

## Test-first findings

1. [Initial red](ticket03-evidence/red-update-key.json) exercised the new UPDATE routing seam with unchanged keys, pending INCR, pending DECR, and an already evaluated assignment. [Green](ticket03-evidence/green-update-key.json) established destination selection without initializing the original assignments. The existing UPDATE SQL path was characterized [before connecting the new router](ticket03-evidence/baseline-update-sql.json).
2. The new duplicate-key test found a genuine context-lifetime defect: `partition_attrinfo_get_key` leaves the decoded index key in a retained pruning context. Assuming that slot was NULL aborted the candidate during `ON DUPLICATE KEY UPDATE`. [Focused red](ticket03-evidence/red-duplicate-context.json) and [green](ticket03-evidence/green-duplicate-context.json) retain the regression history.
3. The frozen ticket-02 library passed duplicate-key UPDATE but [aborted on REPLACE](ticket03-evidence/reference-duplicate-context.json) at the equivalent INSERT precondition. Thus the new UPDATE path exposed the same shared-context assumption already present in ticket 02. Clearing only the context-owned value fixes both workflows without changing the duplicate probes. The final candidate's duplicate/REPLACE batch matches the independently frozen **probe-based** reference from before ticket 02.
4. One test initially expected two OOS chunks for a compressed DEFAULT-policy VARCHAR plus a forced VARBIT. The [frozen reference](ticket03-evidence/reference-compressed-update.json) reports one: the compressed key stays inline. The test expectation was corrected; storage policy and engine behavior were not changed. The unsuccessful [suite runs](ticket03-evidence/verified-show.json) remain retained, not counted as passing evidence.

## Coverage

The eight added behavioral tests are in [test_oos_sql_show.cpp](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/unit_tests/oos/sql/test_oos_sql_show.cpp:652):

- All 13 legal key types, unchanged keys, assigned keys, NULL movement and rollback, with explicit destination OOS observations. HASH behavior is additionally compared in the independent SQL batch; existing RANGE/LIST/expression/direct-partition rejection tests remain.
- SMALLINT/INTEGER/BIGINT ordinary arithmetic, dedicated INCR/DECR boundary crossings, and maximum/minimum overflow/underflow-to-zero. A separate non-key counter increment keeps the original partition key unchanged.
- A real old OOS-backed string key after adding a defaulted column; nested string-expression routing; an updated key moving the row and three newly serialized OOS values into the previously empty destination; rollback restores old content.
- CHAR domains, case-insensitive VARCHAR collation, compressed VARCHAR expression keys, and ordinary versus FORCE_OUTLINE storage behavior.
- Written and unchanged LOBs: an inline ordinary CLOB locator and forced-outline BLOB locator, movement, readback, and rollback. Destination OOS statistics distinguish these from row-value-only checks.
- A serialized historical class representation captured before adding the partition-key attribute. This is a focused **supplied-record contract** test, not a claim that ALTER preserves such a physical child row: no row is installed before partitioning, so redistribution cannot mask the historical-default case. Candidate and reference have independently owned caches.
- Repeated effective routing leaves the source unchanged; a real first-pass transform applies the pending operation once and final record routing agrees on both class OID and HFID.
- Duplicate-key UPDATE and REPLACE preserve their separate index-probe workflows, including a key-changing duplicate UPDATE that moves the row.

### Actual record-buffer retries

[Retained debugger check](ticket03-evidence/force-increment-retry.gdb) deliberately reduces the first-pass buffer estimate once for INCR and once for DECR in the focused routing test. No engine code/test hook is added. The isolated runner records the debugger script hash and exact source diff.

[Observed result](ticket03-evidence/incr-decr-buffer-retry.json): the first attempt had already changed 10 to 11 (INCR), or 10 to 9 (DECR), while the original pending flag remained set. Each attempt then entered `S_DOESNT_FIT` column retry. After retry, the behavioral assertions still read 11 and 9 respectively and matched final destination OID/HFID. This proves the tested INT retry cases neither skip nor double the real mutation. All three integer widths are covered in normal SQL; this is not exhaustive fault injection across every width/type/LOB combination.

## Reproducibility and results

Local build: `debug_gcc`, SA tests. Build/install succeeded through the configured local build workflow. The standard generated test fixtures embed the shared installation/database directory in setup/cleanup, so the existing isolated runner was reused instead of invoking shared fixture setup or cleanup. Every run uses a fresh private config/database; logs, XML, build log, source diff, binaries/library hashes, SQL/debugger script hashes, and failed cores are retained. No network database server or shared database was used.

Candidate engine library SHA-256: `6d5eb8e51466a5931d047bc518f80464e9dc6d75f27b4757762138e1ca01bc14`.

Reference identities:

- Before ticket 03, including tickets 01–02, UPDATE still probe-based: `/tmp/pr7600-ticket03-reference-5caQtH/libcubridsa.so.11.5`, SHA-256 `f5b382475d6e6752d61ac1e1c9a136c8db117039e66a7b5b04b2c0d85143fc36`.
- Before ticket 02, including ticket 01, INSERT and UPDATE probe-based: `/tmp/pr7600-ticket02-reference-ROZTUX/libcubridsa.so.11.5`, SHA-256 `266c72980f5718173eb59c546c16120dfe4a271de8927788c32b2dbfd5d2f4e0`. Used to establish the original duplicate/REPLACE semantics after finding the ticket-02 defect.

| Final check | Result / evidence |
|---|---|
| SHOW/routing suite | 28/28 [passed](ticket03-evidence/final-accepted-show.json) |
| Storage-policy suite | 25/25 [passed](ticket03-evidence/verified-storage.json) |
| Transaction suite | 8/8 [passed](ticket03-evidence/verified-txn.json) |
| Big-record suite | 4/4 [passed](ticket03-evidence/verified-bigone.json) |
| Existing nonpartitioned UPDATE/DELETE suite | 7/7 [passed](ticket03-evidence/verified-update-delete.json) |
| Forced INCR/DECR retries | Both passed; [evidence](ticket03-evidence/incr-decr-buffer-retry.json) |
| 13-type/hash, old-OOS/schema, LOB SQL differential | [Reference](ticket03-evidence/reference-update-contracts.json) and [final candidate](ticket03-evidence/verified-update-contracts.json) outputs identical after removing only elapsed-time strings |
| Duplicate/REPLACE SQL differential | [Probe reference](ticket03-evidence/probe-reference-duplicate-context.json) and [candidate](ticket03-evidence/verified-duplicate-context.json) outputs identical after the same normalization |

To rerun a private suite:

```bash
python3 /home/vimkim/gh/my-cubrid-docs/cbrd-27089/design/ticket01-evidence/run-isolated.py NEW-LABEL \
  --output-dir=/home/vimkim/gh/my-cubrid-docs/cbrd-27089/design/ticket03-evidence \
  --binary=test_oos_sql_show
```

Use a new label: existing evidence is never overwritten. The runner now optionally accepts `--gdb-script` for the scoped retry check. Its debugger line locations are pinned to this source diff and must be checked before reuse after engine edits.

## Review and remaining gates

Source review checked the shared context lifecycle, independent cache ownership, unchanged UPDATE root/child contract, first-pass versus rebuild increment modes, final routing guard, and unchanged duplicate/nonpartitioned call sites. New-code formatting was limited to new/touched blocks, not whole engine files. No new C++-specific engine syntax or on-disk structures were introduced. This report does not claim an independent two-agent review.

This is a functional ticket-03 milestone, not approval to ship the design. Tickets 04–07 remain unstarted: exhaustive error/publication cleanup, server concurrency and old-reader lifecycle, recovery/vacuum, measurements, and final integration acceptance. The debug build compiling server code is not server-runtime coverage. SA rollback is not concurrent-reader proof. The one-key cache and scalar codec can add overhead; no allocation, copying, CPU, or elapsed-time benefit is claimed. Ordinary record-buffer growth/retries and final record routing remain intentional.

Parent spec unchanged: SHA-256 `dfa82a53337a2cf85c9d18bfe3707d99670a6e7070320a97fc3183b50c01f31f`.
