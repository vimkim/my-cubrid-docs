# Code review: CUBRID/cubrid#8693 (CBRD-28257)

[CBRD-28257] *Write zeros for the NULL fixed-length columns of a system catalog row instead of leaving the old memory of its buffer*: <https://github.com/CUBRID/cubrid/pull/8693>

- **Goal:** check whether the PR cleanly fixes CBRD-28257. The defect: unwritten bytes for NULL fixed-length columns in system catalog rows leak earlier heap memory, including plaintext of TDE-encrypted tables, into unencrypted catalog pages and the log. It made the shell TC `cbrd_27780` fail intermittently. Also review the companion TC PRs and the CI, build and static-check state.
- **Most consequential result:** no defect was found in the engine change. The new TC fails checks 2 and 4 on the base build and passes 5/5 on head, with counts identical to the PR description. Both independent reviewers conclude that no byte of a row the catalog encoder produces can still come from uninitialized memory. Separate older leak paths of the same class remain outside this PR (U-1, U-2 below).

## Snapshot

| Item | Value |
|---|---|
| Comparison | `git diff e23905d89ad8a49f17e7cff6eaef01a00de258fe 2a3d8b51475511d8e8e7f06e88e9f0cd54b0fe1f` (PR merge base → head) |
| Base (develop) / merge base | `e23905d89ad8a49f17e7cff6eaef01a00de258fe` |
| Head | `2a3d8b51475511d8e8e7f06e88e9f0cd54b0fe1f` (feature commit `6c7a53ca038f71105ec5d9fc8f78a296a627e858` plus a merge of develop) |
| Patch | 1 file, `src/storage/catalog_class.c` +3/−1; sha256 `3207bccc23e4c7554d1be01fcd76a2c82117f6a0b25f2ea61060582ec02f48fd` |
| TC PRs | [cubrid-testcases-private-ex#5098](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5098) head `478440ba32542385c7415e3fd1d5755c120d2694` (new `shell/_06_issues/_26_2h/cbrd_28257/cases/cbrd_28257.sh`, +156); [cubrid-testcases#4400](https://github.com/CUBRID/cubrid-testcases/pull/4400) head `03f5c6e2ed137a2cae7660238008abad8bfb068f` (draft, no changes) |
| Snapshot time | 2026-11-25 ~18:20 KST; head and base re-verified unchanged before publication |

## Verdict and follow-up

- **Verdict:** `no-confirmed-findings`. No confirmed defect within the inspected scope.
- **Formal review:** APPROVE submitted at head `2a3d8b5147` on the user's instruction, independent of the pending CI ([review](https://github.com/CUBRID/cubrid/pull/8693#pullrequestreview-6056223540)).
- **Follow-up review required:** no. The change, its callers and readers, recovery, HA, and the TC were all covered, with execution evidence on head and base.
- **Must complete before merge (not review work):** `gha-ci` test_sql, test_sql_by_cci and test_shell for head `2a3d8b5` were still pending at the snapshot. `TC Merge Gate / Check TC PRs` is in the expected `BLOCK` state; it is deferred to the final merge handoff, and the TC PRs stay open until then.
- **Recommended separately (not blockers):** U-1 and U-2 are filed as CBRD-28386 and CBRD-28387. Watch `cbrd_27780` in develop CI after the merge (U-3).

## The change

`catcls_put_or_value_into_buffer ()` (`src/storage/catalog_class.c:3268-3274` at head) now calls `or_pad ()` instead of `or_advance ()` for a NULL fixed-length column:

```c
-	  or_advance (buf_p, (*tp_Type_id_map[data_type]).disksize);
+	  /* write zeros: ... */
+	  or_pad (buf_p, (*tp_Type_id_map[data_type]).disksize);
 	  OR_CLEAR_BOUND_BIT (bound_bits, i);
```

`or_pad ()` is `memset (ptr, 0, n); ptr += n` with the same `assert (ptr + n <= endptr)` as `or_advance ()` (`src/base/object_representation.h:1578-1602`). The pointer moves exactly as before. Row length, layout, variable offsets and bound bits are byte-for-byte unchanged; only the content of unbound bytes changes, from stale `malloc` memory to zeros.

## Confirmed findings

None.

## Safety facts and effects outside the diff

| # | Safety fact | Owner | Evidence (pinned head) | Level |
|---|---|---|---|---|
| S1 | Every byte in `[record.data, record.data + record.length)` of a catalog row is written by the encoder. The `malloc` buffers at `catalog_class.c:3931/4261/4524` are never initialized, so this is the property that keeps old memory out. | R-A, R-B (shared question, independent) | Header, offset table (`OR_VAR_TABLE_SIZE(n_variable)` with n+1 `OR_PUT_OFFSET` writes), fixed area (non-NULL writers write their full `disksize`; catalog fixed types are only object/OID 8 B, int 4 B and datetime 8 B), trailing fixed pad `or_pad` (3285), bound bits `memset` + `or_put_data` (3240, 3297), `or_put_align32` → `or_pad` (`object_representation.h:1611`), strings (`or_put_varchar_internal` with NUL + align), sets always re-encoded through `or_put_set` (`object_representation.c:4197-4355`). `record_p->length = ptr - buffer` (3550), so no tail outside the written range is stored. | 3 (source), 4 (TC on head: 0 rows with `A5A5A5A5` under `MALLOC_PERTURB_`) |
| S2 | The pointer advance is unchanged, so the bounds are unchanged. | R-A | `or_pad`/`or_advance` have the same advance and assert. The patch writes only bytes below the final `ptr` that later writes already pass. `catcls_guess_record_length` (566-593) is an upper bound on its own. | 3 |
| S3 | Readers never read unbound fixed bytes, so zero-vs-garbage is invisible to queries. | R-B | `catcls_get_or_value_from_buffer` gates on the bound bit (`catalog_class.c:3438`). `heap_attrvalue_point_fixed` returns early on a cleared bound bit (`heap_file.c:11788-11791`). `catcls_update_instance` compares decoded values with `tp_value_compare` (4242), not raw bytes. The only raw-record `memcmp` (`heap_cmp`) is compiled out (`ENABLE_UNUSED_FUNCTION`). | 3; 4 (`checkdb` OK on head) |
| S4 | Recovery (redo/undo, MVCC header, vacuum) is unaffected. | R-B | No change in length or layout. Log records carry the record image (or its diff) for any byte values. Zeros only make the image deterministic. | 3 |
| S5 | HA is not applicable. | R-B | Catalog row writes pass `need_replication=false` (`catalog_class.c:3947-3948`) or `repl_info=NULL` (4277, 4539). Schema replication is statement-based (`locator_sr.c:14229-14238`), so a slave builds its own catalog rows. No byte-level catalog state is shipped. | 3 |
| S6 | Performance is unaffected. | R-A | One `memset` of ≤ 8 bytes per NULL fixed column, only on DDL and statistics updates. Not measured; it follows from the code. | 2 |
| S7 | The new TC detects the defect deterministically. | R-B, V | Record buffers come from libc `malloc` in SA and server builds; the dlmalloc behind `db_private_alloc` is mspace-only and does not interpose it. `MALLOC_PERTURB_=90` fills with 0xA5. `glibc.malloc.tcache_count=0` disables tcache, the only malloc path that skips the fill. | 3; **5**: base NOK twice, head OK twice, identical counts |

**Effects outside the diff that the PR itself documents:** existing databases keep the old bytes in a catalog row until it is rewritten (PR "Remarks"). The undo image of an update re-logs the old row. Both are JIRA ANALYSIS items 3 and 4, and neither is a merge blocker.

## Coverage and verification

See [code-review-pr8693-coverage.md](code-review-pr8693-coverage.md).

### Checks run

| Check | Command / revision | Result |
|---|---|---|
| Head build | `debug_gcc` preset (Debug), `configure-build-and-install` in a clean worktree at `2a3d8b5` | pass (0 `error:`), install commit match |
| Base build | same preset, detached worktree at `e23905d` | pass |
| TC `cbrd_28257` on head ×2 | native shell testkit under containment, TC `478440ba`, CTP `9c62858` | **5/5 OK** both runs |
| TC `cbrd_28257` on base ×2 | same | **checks 2 and 4 NOK** both runs: `2: _db_attribute=1 _db_class=1`; `4: _db_index=4 _db_attribute=9 _db_query_spec=1 _db_domain=13 _db_class=4`. Identical to the PR description's develop counts. |
| Coordinator replay | Read the raw testkit artifacts of all four runs | Results match the verifier's report |
| TC `cbrd_27780` on head | CTP `8af4f3b` | 14/14 OK (one run; the TC is probabilistic, so this is weak evidence) |
| TC `cbrd_27780` on head and base, CTP `9c62858` | — | identical NOK at 3 and 7 on both, from an environment problem: that CTP has no `wait_until` helper (`wait_until: command not found`). Inconclusive and not attributable. |
| `cubrid-static-check e23905d 2a3d8b5` | compile DB of the head build | 0 new cppcheck, clang-tidy (bugprone), clone or complexity findings; `catcls_put_or_value_into_buffer` CCN 11, length +2 |
| RB-1 replay | `printf ZZZZZ \| od -An -tx1 \| tr -d ' \n' \| tr a-f A-F` → `5A5A5A5A5A`; `awk '$0 ~ /A5A5A5A5/'` | matches (see T-1) |

### CI (GitHub, head `2a3d8b5`, run 45578594759)

| Check | State at snapshot |
|---|---|
| build (debug), build (release), test_medium | success |
| github-checks: license, pr-style, code-style, cppcheck, memory-monitor-check | success |
| test_sql, test_sql_by_cci, test_shell | **pending** (queued) |
| TC Merge Gate / Check TC PRs | failure = expected `BLOCK` while the TC PRs are open; deferred to the final merge handoff |

The earlier head `6c7a53c` (run 45154999819) had one failure each in shell shards 15 and 49 and in sql_by_cci shard 03. The testcase names could not be retrieved: the job logs carry only counts, and `cubrid-ci collect` needs `cubrid-pr-status`, which is not installed. That head was superseded by the develop merge and the `/run all` rerun. If the new run fails the same shards, analyze it with `cubrid-ci-analyze`.

### Limits

- Local TC runs used a debug build only. CI covers release.
- No local run in CS mode with the fill. Detection under CS mode is reasoned from the source (S7).
- `catcls_update_class_stats ()`, the third caller, was not exercised by any run (T-2). It shares the encoder, so S1 covers it at source level.
- Shell CI for the current head is pending.

## Unverified risks and separate defects (not attributable to this PR)

| ID | Statement | Evidence | Owner / next check |
|---|---|---|---|
| U-1 (pre-existing, same class, proposed P2) | `system_catalog.c` catalog-file records (`PAGE_CATALOG`, never TDE-encrypted, logged with `RVCT_INSERT`) are built in an uninitialized `db_private_alloc (thread_p, DB_PAGESIZE)` buffer (`system_catalog.c:2905`). `catalog_put_disk_attribute` (474-485) never writes bytes 32-79 of each 88-byte `DISK_ATTR`. Smaller gaps exist in the representation, B-tree stats and directory records. `UPDATE STATISTICS` writes these right after scanning the table. | Level 2-3 from source (coordinator re-read the layout at 98-118 and the writer at 474-485). After this review, the CBRD-28386 filing reproduced unwritten bytes in SA mode (`MALLOC_PERTURB_`, `use_system_malloc=yes`); see the issue for details. Plaintext of encrypted tables was not shown there. | Filed as [CBRD-28386](https://jira.cubrid.org/browse/CBRD-28386). Cheapest check: SA mode with `MALLOC_PERTURB_=90`, `create table t(a int, b varchar(10)); update statistics on t;`, then dump the catalog file and look for `A5` at DISK_ATTR offsets 32-79. The companion TC does not scan these pages. |
| U-2 (pre-existing, client side, proposed P3) | In a release build, partition expression streams keep stale client memory in their alignment padding. The zeroing is debug-only (`#if !defined(NDEBUG)` at `xasl_to_stream.c:9211-9217`, also 1439-1448 and 358-363). The stream is stored as a VARCHAR in the partition values (`execute_schema.c:16758`) and reaches `_db_partition` as string payload, and the root-class record as well. The catalog encoder writes these bytes faithfully, so S1 still holds; the content itself is stale. This is the TC's "another defect" note. | Level 3, source only (R-A; the coordinator verified the guard and the storage site). R-B had concluded that no client padding reaches the row, but did not trace that the stream is stored as string payload; R-A's trace prevails. | Filed as [CBRD-28387](https://jira.cubrid.org/browse/CBRD-28387) (fix in `xasl_to_stream.c`). Check: release build, partitioned table under the fill, dump `_db_partition`. |
| U-3 | `cbrd_27780` flakiness may not disappear entirely, because U-1 (48 B per attribute) can hold a full marker string. Smaller unpadded bytes in `heap_attrinfo_transform_*` (≤ 3 B, noted in the JIRA comment of 2026-11-23) cannot. | Level 2 (inference) | After merge, check `cbrd_27780` with `cubrid-tcc history`. Any recurrence points at U-1. |

### TC review notes ([private-ex#5098](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5098)): non-blocking suggestions

- **T-1 (P3, robustness):** `rec ~ /A5A5A5A5/` runs on hex without spaces, so it also matches off byte boundaries. Five consecutive `0x5A` bytes (`ZZZZZ`) produce `5A5A5A5A5A`, which matches; the coordinator replayed this. None of the TC's own object names contain such a run, so it cannot cause a false NOK today. Suggested fix: match on byte boundaries, e.g. keep the spaced hex and use `/A5 A5 A5 A5/`, or check an even offset.
- **T-2 (P3, coverage):** the statistics path (`catcls_update_class_stats ()`, e.g. `UPDATE STATISTICS ON t1`) is not exercised. Optionally add it under the fill.
- **T-3 (nit):** `rm -f *.log *.txt csql.err` in `do_cleanup` is broader than peer TCs. It is harmless in the TC's own directory.
- Conventions (`init.sh`, `write_ok`/`write_nok`, `finish`, `cubrid_createdb`) match peer TCs. The diagdb parsing matches the `heap_dump` format and fails closed. `cubrid-testcases#4400` has no changes and can be closed at the final handoff after its "no unlanded changes" check. Neither PR needs to change `cbrd_27780`.

### Dropped candidates

- R-A: 0 engine findings. "NULL fixed value with domain `DB_TYPE_NULL` overflows the guess" was rejected: the guess has slack of at least 8 B per column. "Ignored `data_writeval` return codes leave a gap" was rejected for this revision: no `or_put_*` fails partially. It is noted as an older robustness issue.
- R-B: 0 engine findings. Three hypotheses were rejected with source evidence: "the update path copies old garbage forward", "CUBRID allocators bypass the perturb fill", and "client padding is copied into the row" (superseded by U-2's trace).

## Budget accounting

- Mode: bounded (no absolute budget from the user). **No hard cap was enforced.** Targets were prompt-level only.
- Agents: 3 (R-A opus 5.5: Systems + Storage + Q1; R-B sonnet 5.5: Recovery + HA + TC + Q1; V sonnet 5.5: builds and TC runs). No retries, no nested agents.
- Measured by the harness per agent: R-A 182,128 tokens / 7.8 min; R-B 297,640 tokens / 15.9 min; V 151,439 tokens / 16.0 min. R-B reported slightly exceeding its target. Coordinator usage was not measured.
- Remaining envelope: not needed. No follow-up allocation.
