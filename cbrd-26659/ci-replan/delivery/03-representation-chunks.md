# Ticket03: representation and discriminating chunks

Date: 2026-10-08 (Asia/Seoul). Ticket03 of [the approved developer regression specification](../spec.md).

Final native validation passes **three public SQL cases and one private shell case**, with zero selected failures or skips. The shell supplies 20 complete logical receipts, 40 positively parsed SHOW samples and 46 successful assertions. Three deliberately wrong physical expectations reject in disposable copies before clean runs. The correct [4,060-byte target reproducer](03-target-4060-reproducer.sql) separately confirms CBRD-27057 and receives no passing credit. All other Ticket03 criteria are implemented and locally verified; the ordinary-target conformance gap remains explicit.

## Delivered files and identities

Public `cubrid-testcases`, branch `task/oos-03-representation-chunks`, tested tip `f80e3e3ff8efaba2adb0316c0eb19f71210a7d1e`:

- `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_representation.sql` and matching answer.
- `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_chunk_boundaries.sql` and matching answer.
- `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_vot_many_attributes.sql` and matching answer.

Private `cubrid-testcases-private-ex`, branch `task/oos-03-representation-chunks`, tested tip `e5e3898cd19734b16b6f01ac07c60bad53ea32c3`:

- `shell/_40_guava/cbrd_26659_representation_chunks/cases/cbrd_26659_representation_chunks.sh`.
- That directory's `phase_commands.py`, `representation.sql/json`, `chunks.sql/json` and `widths.sql/json`.
- Existing `shell/_40_guava/oos_common/oos_observe.py` reused unchanged, SHA-256 `01cab781669134563b1f3ffcec32607a0b4449ce181708a01bd7b91678b1f348`.

Own public commits: `e8714d5c1`, `75985fb8f`, `a37144f4d`, `fb2024699`. Own private commits: `6eb0744d2`, `84889bebd`, `2867ac6bc`, `ecc468d55`. Integration merges include public `700f62ccad5886e798ae0892083b7b402382396b` and private `992cf93bc02d1221ee9cfcc82cc2de20aee75929` without changing reviewed Ticket03 files. Docs support fixture commit is `e78adc58102bfad01333ab40e841d41bc6584ab9`; docs integration `97517e490211d63396454d422f8357958c10e109` is included. Shared coverage and README changes belong to the merger.

Answers were independently authored before runtime, preserving the public JDBC separator/trailing-space convention. Public cases check complete ordered values, independent MD5 of complete lowercase hexadecimal text where applicable, exact bit/octet/serialized lengths and final catalog absence. Public logical and paired private physical evidence are separate invocations.

## Representation and selection model

Accepted inline stub and chunk header are **24 bytes**. VARBIT serialized length is `ALIGN_UP(prefix+CEIL(bits/8),4)`, with prefix 1 below 255 bits and 5 otherwise. Delivered byte payloads of at least 32 bytes use `ALIGN_UP(N+5,4)`. Empty non-NULL VARBIT serializes to 4; NULL has no value serialization. Tiny VARCHAR includes prefix 1 and terminator 1 before alignment. `DISK_SIZE(NULL)=0`, while bit/character lengths remain NULL. Root independently required the two NULL disk-size answer corrections from pinned [fetch.c:3850](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/fetch.c:3850) before runtime (`75985fb8f`), rather than adopting actual output.

Unequal 3,000/1,200-byte candidates serialize to 3,008/1,208. Fixed id 4, bound bits 4, MVCC insert header 16, short VOT 8 and future MVCC reserve 16 yield estimate 4,264. One largest-first demotion replaces 3,008 with 24, leaving 1,280. Required physical result is one chunk and **3,032** record bytes; incorrectly choosing the smaller value gives 1,232 and fails. The 1,000/500-byte comparator has estimate 1,564 and no OOS file. Neither enters the disputed ordinary gate band or asserts equal-size tie order.

FORCE_OUTLINE isolates the strict profitable-value floor from that gate. NULL, empty, 19 bytes→20 serialized, 20 bytes→24, 23 bytes→24 and five bits→4 stay inline. At 24 payload bytes, serialized 28 exceeds the stub and creates one 52-byte record. The non-byte value is exactly 33,603 bits, 4,201 octets and 4,208 serialized bytes, contributing 4,232 with its header. Complete recipe equality and exact lengths are checked without claiming a digest of unused terminal bits. Tiny uncompressed VARCHAR 22/23-character controls serialize to 24/28 and require no file/one 52-byte record; NULL and empty remain distinct.

| Shell phase | Logical rows/predicates | Expected and observed Has/chunks/sum |
| --- | --- | --- |
| `rep_largest` | 1/1; both unequal values intact | 1 / 1 / 3032 |
| `rep_inline` | 1/1; both inline values intact | 0 / 0 / 0 |
| `rep_floor_inline` | 6/6; NULL/empty/floor/five-bit controls | 0 / 0 / 0 |
| `rep_floor_above` | 1/1; serialized 28 | 1 / 1 / 52 |
| `rep_nonbyte` | 1/1; exactly 33603 bits | 1 / 1 / 4232 |
| `rep_text_inline` | 3/3; NULL/empty/22 characters | 0 / 0 / 0 |
| `rep_text_above` | 1/1; 23 characters | 1 / 1 / 52 |

Pre-runtime [representation oracle](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket03/oracle-representation.md) and [root review](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket03/root-oracle-review-representation.md) freeze this model.

## Chunk boundaries and copy values

At 16 KiB I/O pages, `DB_PAGESIZE=16384−40=16344`. Slotted-page header is **32 bytes**: four 16-bit fields (8), five int32 fields (20), one bitfield word (4); a slot is 4. [spage_max_record_size](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/slotted_page.c:841) gives `16344−32−4=16308`. [oos_get_max_chunk_size_within_page](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/oos_file.cpp:3645) aligns down to 8 then subtracts the chunk header: **`ALIGN_DOWN(16308,8)−24=16280` payload bytes**. An initial 40-byte slotted-header research assumption was corrected before chunk fixture creation/runtime. No 16,272-byte or older 16,300-byte capacity oracle was accepted.

Count is `CEIL(L/16280)`; SHOW record sum is `L+24×count`, excluding slot/alignment waste. Each private phase is a separate fresh one-row heap with the corresponding complete public initial value committed before observation.

| Phase / public id | Payload N | Serialized L | Expected and observed chunks | Expected and observed sum |
| --- | ---: | ---: | ---: | ---: |
| `rep_chunk1` / 1 | 16271 | 16276 | 1 | 16300 |
| `rep_chunk2` / 2 | 16275 | 16280 | 1 | 16304 |
| `rep_chunk3` / 3 | 16276 | 16284 | 2 | 16332 |
| `rep_chunk4` / 4 | 32551 | 32556 | 2 | 32604 |
| `rep_chunk5` / 5 | 32555 | 32560 | 2 | 32608 |
| `rep_chunk6` / 6 | 32556 | 32564 | 3 | 32636 |
| `rep_chunk7` / 7 | 50003 | 50008 | 4 | 50104 |

Seven sizes preserve nearest representable below/exact/above controls at the first and second boundaries and a four-chunk value, rather than redundant bulk levels. For id `i`, hex bytes `3i`, `3i+1`, `3i+2` distinguish head/middle/tail regions. Head data is capped at 16,275 after the five-byte prefix, followed by at most 16,280 middle bytes and the tail. Row 7's 17,448-byte tail spans two physical chunks; this does not claim each physical chunk has a unique pattern or observed OID.

Public SQL checks initial source, INSERT SELECT copy, copy after updating only id 7, unchanged source after that update, then changed copy surviving source DROP. Changed row: `fa×16275+fb×16280+fc×17452`, 50,007 octets, serialized 50,012, lowercase-hex MD5 `ff19ad2821f79c8e4d0aa1ef9c0ef82c`. Each stage checks full literal equality, full independent digest and lengths for ordered ids 1..7. Surviving copy count/distinct digest count is 7/7; final fixture catalog count is 0. This proves logical value independence without claiming stub ownership or physical UPDATE reuse.

[Chunk oracle](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket03/oracle-chunks-vot-proposed.md), [independent review/source derivation](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket03/root-independent-review-chunks.md) and [literal arithmetic/digests](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket03/root-independent-chunk-arithmetic.json) were reviewed before runtime. A stale descriptive external updated-row sum 50,104 was corrected to **50,012+4×24=50,108** before runtime; this unasserted field changed no golden. It describes only the new chain, not post-UPDATE SHOW while old MVCC chains may remain.

## VOT and many-attribute model

Signed VOT offset maxima are 127/32,767 because a flag consumes the high bit. One fixed INT plus one VARBIT has insert overhead 28 for BYTE/SHORT, 32 for INT. The exact neighbors are:

| Phase | Payload N / hex byte | Serialized L | Pre-demotion record | Derived input→final VOT | Expected and observed Has/chunks/sum |
| --- | --- | ---: | ---: | --- | --- |
| `rep_vot1` | 91 / `71` | 96 | 124 | BYTE→BYTE | 0 / 0 / 0 |
| `rep_vot2` | 92 / `82` | 100 | 128 | SHORT→SHORT | 0 / 0 / 0 |
| `rep_vot3` | 32731 / `93` | 32736 | 32764 | SHORT→BYTE | 1 / 3 / 32808 |
| `rep_vot4` | 32732 / `a4` | 32740 | 32772 | INT→BYTE | 1 / 3 / 32812 |

Fourth input first reaches 32,768 with short overhead, then expands the header to 32,772. Large values demote their sole candidate and compact the final width. **Width labels are pinned-writer serialization models; SHOW does not introspect actual VOT width.** Exact logical values/digests and physical chunk results are directly checked, without binary VOT observation credit.

Twelve distinct attributes `c01..c12` contain 600,608,…,688 bytes with hex patterns `10..1b`. Each complete literal equality and full independent digest is checked separately; logical/serialized totals are 7,728/7,824. FORCE_OUTLINE demotes all twelve profitable values: 12 chunks, sum **8,112**, final inserted record 340/reserved estimate 356. Default initial estimate 7,892 falls to 4,612 after five largest demotions and 3,980 after six; exactly six must demote. Their unique maximum serialized sum 4,056 yields six records/sum **4,200**, discriminating largest-first selection. These distant estimates work with both desired 4,060/current 4,086 without blessing the latter or specifying tie order.

`rep_many_forced` and `rep_many_default` each return one row, id 1, all twelve predicates 1 and totals 7,728/7,824 before two SHOW samples. Six width/many phases supply six logical receipts/twelve SHOW samples/twelve anchored phase OK tokens. [Pre-runtime oracle](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket03/oracle-vot-many.md), [root review](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket03/root-oracle-review-vot-many.md) and [independent root arithmetic/digests](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket03/root-independent-vot-many.json) were approved before the negative and final clean runs.

## Desired target disposition: CBRD-27057

One INT/one VARBIT reserves 44 bytes including future MVCC fields. Payloads 4,011/4,012 serialize to 4,016/4,020, giving gate estimates **4,060/4,064**. Accepted behavior requires inline at 4,060 and one OOS record of **4,044** at 4,064. Source still uses raw `DB_PAGESIZE/4=4086`, conflicting with the accepted target.

The [supporting desired-target SQL](03-target-4060-reproducer.sql) preserves that normative fixture outside testcase corpus and every passing manifest. It is necessary to retain the correct boundary while safe distant/floor fixtures qualify; this report links it without a standalone delivery index row. Defect-only [oos306-sh03-gate01 proof](/home/vimkim/tmp/oos306-sh03-gate01/gate-disposition-proof.json) verifies both complete values, then the lower no-file control, before rejecting upper Has/chunks/sum 0/0/0 against unchanged desired 1/1/4044 with `wrong Has_oos_file`. Native artifacts show one failure/zero skips and successful failed cleanup. This is a gate mismatch, not setup/parse failure. No expected-to-actual adjustment or engine fix is included.

## Native evidence and measured cost

All copy/config preparation, runtime, verification and owned cleanup hold exclusive [validation.lock](/home/vimkim/tmp/oos-developer-regressions-20261008/coordination.md). Timing starts after lock acquisition, excluding wait. Source is `fb567a629cdb390fff920542173fa36f454c74a0`; root-verified optdebug install is `/home/vimkim/.cub/install/CBRD-26659-oos-testcases-handover/optdebug`, release `11.5.0.2637-fb567a6`. Matching JDBC SHA-256: `0f5e56c7eaed0ebeb1eba3a8bba5a5db513e7eec455498d268e2205d48c02576`; Java: `temurin-8.0.462+8`; CTP commit: `9c62858b10005d721546cc007be260844033b9e9`. [Shared install identity](/home/vimkim/tmp/oos-developer-regressions-20261008/install-identity.json) records root's separate 129.45-second build and preserved debug_gcc/host state/unrelated CCI header dirt. Ticket03 did not rebuild or modify engine/host CTP.

Public uses contained native JDBC/CS, HA-enabled 16 KiB I/O/log pages and explicit 64 MiB initial DB/log volumes. Private uses its own ordinary CS CSQL lifecycle, 16 KiB pages, 20 MiB volumes and offline checkdb. Physical shell evidence does not prove placement in the separate JDBC database. Every attempt owns copied install, registry, TMP, HOME, CTP/results and contained slot; `TESTKIT_SLOT_VOLATILE` stays unset. Explicit shell selection disables irrelevant whole-corpus platform macro filtering with the retained approved reason, and selected case contains no unsupported platform macros. No retries, answer updates or continuation are enabled.

| Retained attempt under `/home/vimkim/tmp/` | Exact outcome | Case seconds | Runner seconds | Locked runner+verify+cleanup seconds | Preparation seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| `oos306-sh03-neg01` | Copied largest sum 3032→3033 rejects, 1 failure/0 skips | 7.374 | 9.035 | 9.433 | 1.906 |
| `oos306-sql03-a01` | Representation SQL 1/1 pass | 0.106 | 90.762 | 91.268 | 1.178 |
| `oos306-sh03-a01` | Representation shell 1/1 pass, 20 OK | 9.874 | 11.521 | 11.904 | 1.034 |
| `oos306-sh03-gate01` | Correct desired gate fails; defect-only | 7.655 | 9.156 | 9.542 | 1.883 |
| `oos306-sh03-neg02` | Copied chunk3 count 2→1 rejects, 1 failure/0 skips | 9.338 | 10.867 | 11.250 | 1.855 |
| `oos306-sql03-a02` | Chunk SQL 1/1 pass | 0.107 | 94.386 | 94.884 | 1.034 |
| `oos306-sh03-a02` | Representation+chunks shell 1/1 pass, 34 OK | 10.783 | 12.319 | 12.697 | 1.238 |
| `oos306-sh03-neg03` | Copied forced-many count 12→11 rejects, 1 failure/0 skips | 10.849 | 12.488 | 12.896 | 2.155 |
| **`oos306-sql03-a03`** | **Final SQL 3/3 pass, zero failures** | **0.249 total** | **86.040** | **86.524** | **1.059** |
| **`oos306-sh03-a03`** | **Final shell 1/1 pass, 46 OK/0 NOK/0 skips** | **11.721** | **13.356** | **13.732** | **1.008** |

Native XML SQL case costs are chunk 0.109, representation 0.072, VOT/many 0.068 seconds. They are runner-reported; separately timed whole invocation includes setup and normal cleanup. Shell case time spans framework initialization, DB creation, all fixture/observation groups, offline checkdb and EXIT cleanup. No performance cutoff or whole-corpus projection is inferred. [Attempt summary](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket03/attempt-summary.json) preserves unrounded timings, historical identities and all failed artifacts.

Final exact SQL manifest:

```text
sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_chunk_boundaries.sql
sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_representation.sql
sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_vot_many_attributes.sql
```

[Strict final SQL proof](/home/vimkim/tmp/oos306-sql03-a03/strict-delivery-proof.json) binds this positive manifest, verifier exit 0, unchanged original case/answer hashes and complete cleanup. Result: `/home/vimkim/tmp/oos306-sql03-a03/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_0819305294_11.5.0.2637-fb567a6`.

Final exact shell manifest: `shell/_40_guava/cbrd_26659_representation_chunks/cases/cbrd_26659_representation_chunks.sh`. [Strict observation proof](/home/vimkim/tmp/oos306-sh03-a03/strict-observation-proof.json) reparses retained logs against frozen source model hashes: 20 nonempty logical receipts, 40 complete fourteen-field named SHOW samples, identical normalized state for each pair, all 40 anchored logical/physical phase OK tokens exactly once. Representation/chunks/widths provide 14/14/12 tokens; checkdb plus five normal-cleanup assertions give **46 OK**, zero NOK. Native artifact verdict is 1/1/0, with zero skips; exit 0 alone never supplied credit. Result: `/home/vimkim/tmp/oos306-sh03-a03/CTP/result/shell/current_runtime_logs`.

## Cleanup, focused checks and limits

All normal, deliberately failed and defect-only attempts have owned-cleanup proof: no accessible process from copied install; empty registry/database/slot paths; restored copied configuration; unchanged testcase hashes; required cleanup tokens. Shell traps stop the owned server, require owned PID absence, delete owned database/registry/files and restore parameters. Normal flow stops before offline checkdb. Checkdb success may be silent: require actual status 0, a nonempty invocation-specific diagnostic log and no error/warning/corruption marker. Final SQL also proves normal stop/delete messages, restored runtime parameters and short TMP absence. Inaccessible/racing host PIDs are recorded without claiming ownership. Native containment bounds inherited framework process/IPC cleanup.

All six shell timeout sites use `--kill-after=5s`; commit `2867ac6bc` is a deadline-only revision reviewed before chunk runtime. Earlier representation/gate receipts preserve historical commits. No timeout occurred; bounds/trap wiring were checked statically, while failed cleanup was exercised by three discriminating negatives and the correct gate failure.

Focused checks pass: `bash -n`, `shellcheck -S warning`, `testkit check-cases` (one discoverable case, no missed failure helpers/self-comparison), Python compile/model emission and scoped Git whitespace checks. Representation's inherited block header with semicolons did not trigger native CQT fragments: its complete result matches the frozen answer, with no syntax/-493 fragments. Later headers use `--`; the documented multiline-comment compatibility limit remains relevant to future cases. Raw receipts/logs/generators/reparse scripts remain outside repositories.

## Coverage delta for shared integration

| Row | Concrete case/phase evidence | Credit and remaining disposition |
| --- | --- | --- |
| R02 | Representation SQL; `rep_largest`, `rep_inline`; VOT/many SQL and `rep_many_default` | Exact largest sum 3032 and six-largest count/sum 6/4200; no-file control. No tie-order claim. |
| R03 profitable floor | Representation SQL; `rep_floor_inline`, `rep_floor_above`, `rep_nonbyte`, `rep_text_inline`, `rep_text_above` | FORCE_OUTLINE strict serialized >24 floor. Correct 4060/4064 boundary remains failing CBRD-27057 evidence outside credit. |
| R04 | Representation and VOT/many SQL; seven representation and six width/many phases | NULL/empty, 5/33603-bit values, twelve attributes, signed-width neighbor model and physical demotion. No actual binary VOT introspection. |
| R05 | Chunk SQL source/copy/changed-copy/source DROP; `rep_chunk1..7` | Below/exact/above chunk controls, distinct complete regions, 1/2/3/4 records and sums. Logical copy value independence only; no ownership/UPDATE reuse/reclaim. |
| R07 relevant subset | Representation SQL and floor/non-byte/text phases | Uncompressed byte/non-byte VARBIT and tiny uncompressed VARCHAR. Broader mixed types/compression-sensitive lengths remain outside Ticket03. |

Every physical phase has positive parser evidence and two quiescent samples from fresh committed heaps without concurrent writers. Class/heap/file identifiers are valid observed identifiers, not fixed allocator identities; SHOW conditional latch behavior cannot justify adopting undercounts. No identity/retry/ownership, unassigned-chain reuse, snapshots, recovery, vacuum/reclaim, HA transport or whole-corpus qualification is claimed. Ordinary-target failure is the explicit accepted defect disposition, never a passing golden. Merger should index this report and apply these phase/proof/timing deltas to shared coverage.
