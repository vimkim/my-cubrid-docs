# CBRD-26659 ticket 18 — expected output, justified before the engine ran

> Written 2026-09-21 (KST), before any CTP invocation of these nine cases, as the campaign
> specification requires ("Justify the expected whole value before running the engine. The first
> `.result` is a candidate; review it against the requirement, then promote by rename").
> Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (ticket 11, re-pinned by ticket 41);
> normative context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…`.
> Derivation: [`../ticket19/derive_ticket19_sizes.py`](../ticket19/derive_ticket19_sizes.py) →
> [`derivation-output.txt`](derivation-output.txt), self-test → [`selftest-output.txt`](selftest-output.txt).
> Per-literal expected scalars: [`oracle-values.txt`](oracle-values.txt).
> A syntax smoke on a throwaway standalone database is recorded in §12 for what it is: a check
> that the statements parse and execute, never a source of an expectation.

## 0. How to read this document

The nine cases make four kinds of claim, and they are justified differently.

| Kind | Example | How the expectation is justified |
|---|---|---|
| **Scalar value** | `octets`, `digest`, `payload_disk` | Arithmetic on the case's own literal, §1. Never observed. |
| **Boolean equality flag** | `ok`, `payload_ok`, `empty_ok` | Required to be `1`. A `0` is a failure, never an answer. |
| **Behavioural outcome** | row counts, error identities, what a rejected statement leaves behind | Derived from the normative specification or from the pinned engine's source and message catalogue, cited per case below. |
| **Placement** | which column moved out of the record, and into how many chunks | **Not in any answer.** No portable SQL exposes it. It is asserted, or observed, by the paired `SHOW HEAP OOS` check, whose expected figures are in §11. |

Every `ok` flag in every case is expected to be **1**, every `n_aliased` is expected to be **0**,
and every `n_classes` of a refused DDL is expected to be **0**. Those are not repeated per
statement below; only the outcomes that need a reason are.

## 1. The scalar rules

Every variable-length literal in every case is `CAST(REPEAT('<h>', 2N) AS BIT VARYING)` for a hex
character `<h>` and a byte count `N`, and every fixed filler is `CAST(REPEAT('<h>', 2F) AS
BIT(8F))`. Three scalars follow, with no engine involved:

| Scalar | Value | Source |
|---|---|---|
| `OCTET_LENGTH` | `N` | the value is exactly N bytes |
| `DISK_SIZE` | `ALIGN(5 + N, 4)` for `N ≥ 32` | `or_varbit_length_internal`, reproduced in ticket 11's `oos_boundaries.varbit_disk_len` |
| `MD5` | `md5("<h>" * 2N)` | CUBRID digests a BIT VARYING's lowercase hexadecimal form |

A fixed `BIT(8F)` filler follows the same three rules with `N = F`: `OCTET_LENGTH` is `F` and
`MD5` is `md5("<h>" * 2F)`. Revision 1 of this document did not say so and the derivation did not
tabulate the fillers; the first candidate review reported four filler digests as unpredicted and
all four turned out to be exactly that (finding T18-F3). The fillers are in the table now.

[`oracle-values.txt`](oracle-values.txt) tabulates all 168 distinct literal values the seventeen
cases of this scenario use, with these three scalars each; a candidate `.result` is reviewed
against that table by [`review_candidates.py`](review_candidates.py).

## 2. Why each fixture is the kind of fixture its case says it is

The campaign may assert a placement only where the pinned gate (`DB_PAGESIZE/4` = 4,086 B at
16 KiB) and the normative four-record target (CBRD-27057 = 4,060 B) agree, and where the 16-byte
pinned inline stub and the 24-byte normative one (CBRD-26950) do not separate the answer.
`derive_ticket19_sizes.classify()` enforces that and `gen_ticket19_cases.py` routes every fixture
row through it. Ticket 18 adds three expectations to it, each with its own obligation:

| Expectation | Obligation checked before the size may reach a case |
|---|---|
| `oos` | both accountings demote the same non-empty set; the record is at or below the gate afterwards; an **eligible** column is left inline, so the row can tell largest-first from any other order |
| `inline` | both accountings demote nothing |
| `oos-exhausted` | both accountings demote the same non-empty set; the record is still **above** the gate afterwards; **no eligible** column is left inline, because a loop that still wants to shrink the record cannot have passed one over. Together: everything left inline is below the floor |
| `disputed` | the two accountings demote **different** sets. Value assertions only. Placement observed, never asserted |

Four disagreement bands are **searched, not remembered** (`derivation-output.txt`, "Ticket 18
disagreement bands"):

| Band | Range | What the case does |
|---|---|---|
| record gate, schema-C `payload` | 3,700–3,723 B | 3,699 and 3,724 are the assertable pair, one byte outside on either side; 3,700 and 3,723 are carried as `disputed` |
| eligibility floor, `small` | 16–23 B | 15 and 24 are the assertable pair; 20 is carried as `disputed` |
| single-to-multi chunk | 16,276–16,283 B | 16,275 and 16,284 are the assertable pair; **no case enters the band** |
| OOS + bigone, filler `F` | 16,169–16,176 B | 16,168 and 16,177 are the assertable pair; **no case enters the band** |

## 3. `cbrd_26659_oos_rep01_gate_boundary` — OOS-REP-01, OOS-REP-02

| Statement group | Expected | Why |
|---|---|---|
| TEST 1, `id 1` | `payload_disk` 3704, `payload_octets` 3699, `payload_md5` `f64dc744e355123d411cbb3915630fd9`, `tag_disk` 308, `tag_octets` 300, both flags 1 | record 4,060 B, at or below both gates |
| TEST 2, `id 2` | `payload_disk` 3732, `payload_octets` 3724, `payload_md5` `295cedd921ff990aca3878b8f309bfec`, both flags 1 | record 4,088 B, above both gates |
| TEST 3, `id 3` | `payload_disk` 3708, `payload_octets` 3700, `payload_md5` `ca2f16d2aa0e108e7527b94b9e991a70`, both flags 1 | record 4,064 B, inside the band. **The expectation is the same under either reading of the gate** — the answer carries no placement |
| TEST 4, `id 4` | `payload_disk` 3728, `payload_octets` 3723, `payload_md5` `3d3f3230fe80487298214b77ab9bf30c`, both flags 1 | record 4,084 B, inside the band |
| TEST 5 | `n_rows` 4, `n_exact` 4, `n_distinct_payloads` 4, `n_aliased` 0 | four rows, each holding its own value |

INSERT affected-row counts: 1 each. DDL reports 0.

## 4. `cbrd_26659_oos_rep02_demotion_order` — OOS-REP-02

Every group prints one row per column: `col`, `name`, `octets`, `digest`, `ok`.

| Statement group | Expected | Why |
|---|---|---|
| TEST 1, `id 1` | three rows: `big1` 900, `big2` 800, `tag` 300, every `ok` 1 | record 2,072 B, below both gates |
| TEST 2, `id 2` | three rows: 2000, 1900, 300, every `ok` 1 | record 4,272 B; `big1` alone is demoted under both accountings |
| TEST 3, `id 3` | three rows: 2000, 2000, 300, every `ok` 1 | record 4,372 B; exactly one of the two equal candidates is demoted, and **which one is not asserted anywhere** |
| TEST 4 | `n_rows` 1, `n_aliased` 0, `n_same_length` 1 | the two equal-size values are different values |
| TEST 5 | four rows: 2200, 2100, 2000, 300, every `ok` 1 | record 6,684 B; two demotions are needed and the third-largest stays inline |
| TEST 6 | `n_rows` 3, `n_distinct_big1` 3, `n_aliased` 0 | three rows, three distinct `big1` values |

## 5. `cbrd_26659_oos_rep04_eligibility_floor` — OOS-REP-04, OOS-REP-02

| Statement group | Expected | Why |
|---|---|---|
| TEST 1, comparator | three rows: `filler` 100, `payload` 500, `small` 15, every `ok` 1 | record 672 B, below both gates |
| TEST 2, `id 1` | three rows: `filler` 5000, `payload` 4200, `small` 15, every `ok` 1 | record 9,272 B; `payload` is demoted and the record is still 5,080 B, above the gate |
| TEST 3, `id 2` | three rows: 5000, 4200, 24, every `ok` 1 | a 24 B value serializes to 28 B, above both floors, so the exhausted loop takes it too |
| TEST 4, `id 3` | three rows: 5000, 4200, 20, every `ok` 1 | inside the floor band. **Value assertions only** |
| TEST 5 | `n_rows` 3, `n_distinct_payloads` 3, `n_distinct_smalls` 3, `n_distinct_small_lengths` 3, `n_filler_exact` 3 | three rows, each with its own values, and every filler exactly 5,000 B |

## 6. `cbrd_26659_oos_rep07_chunk_boundary` — OOS-REP-07, OOS-REP-02

| Statement group | Expected | Why |
|---|---|---|
| TEST 1, `id 1` | `payload_octets` 3000, `payload_disk` 3008, both flags 1 | inline comparator |
| TEST 2, `id 2` | `payload_octets` 16275, `payload_disk` 16280, `payload_md5` `2e6c4d55bb49646c991eb76507310983`, both flags 1 | one chunk under both chunk headers |
| TEST 3, `id 3` | `payload_octets` 16284, `payload_disk` 16292, `payload_md5` `f9758709ca769f9151f0c20e5c803683`, both flags 1 | two chunks under both |
| TEST 4, `id 4` | `payload_octets` 32576, `payload_disk` 32584, `payload_md5` `d7c4cbc6a546fe11d2178db5df452199`, both flags 1 | three chunks under both |
| TEST 5 | `n_rows` 4, `n_distinct_payloads` 4, `payload_octets_total` **68135**, min 3000, max 32576, `n_aliased` 0 | 3000 + 16275 + 16284 + 32576 |
| TEST 6 | one row: `id` 4, 32576, the same digest | a multi-chunk value read through a predicate on itself |

**Two clauses of OOS-REP-07 are not claimed.** "Inserted tail first" is observable at neither
campaign seam, and "`total_data_length` excludes every chunk header" rests on the 24-byte
identity layout that is absent at this revision. Both are carried as their own matrix rows with
no case and no outcome.

## 7. `cbrd_26659_oos_rep08_bigone_rejection` — OOS-REP-08

| Statement group | Expected | Why |
|---|---|---|
| TEST 1, comparator | `filler` 100, `v` 64, both `ok` 1 | record 216 B |
| TEST 2, accepted | `filler` 16168, `v` 64, both `ok` 1 | record 16,284 B before demotion, **16,228 B after**, under `heap_Maxslotted_reclength` 16,236 |
| TEST 3, rejected | **`Error:-1382`** | `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`, `error_code.h:1782`. The demoted record measures 16,237 B, one byte over the threshold (`heap_file.c:13300-13304`). The context's -1375 is drift, reported to the context maintainer (ticket 11 §4 g) |
| TEST 4 | `n_rows` **0** | "no row is stored" |
| TEST 5, non-OOS bigone | `filler` 20000, `s` 10, both `ok` 1 | the 10 B value serializes to 12 B, below both floors, so nothing is demoted, `has_oos` is false and the 20,056 B record is an ordinary `REC_BIGONE` |
| TEST 6 | `n_comparator` 1, `n_accepted` 1, `n_rejected` 0, `n_bigone` 1 | four separate statements |

CTP renders a failed statement as `Error:-<code>` and nothing else, so the answer carries the
error identity and never the message text, whose byte counts are already in this table.

## 8. `cbrd_26659_oos_rep09_null_empty` — OOS-REP-09, OOS-REP-02

| Statement group | Expected | Why |
|---|---|---|
| TEST 1, `id 1` | `payload` 3000 and `tag` 300, both `ok` 1 | inline comparator carrying the same NULL and empty columns |
| TEST 2, `id 2` | `payload` 4200 and `tag` 300, both `ok` 1 | record 4,572 B; only `payload` is demoted |
| TEST 3 | two rows, each `nullable_is_null` 1, `empty_is_null` **0**, `empty_octets` **0**, `empty_ok` 1, `nullable_octets` **NULL** | a NULL variable value occupies no payload bytes (`mr_lengthval_varbit_internal` returns 0); a zero-length value still carries its 1-byte prefix, ALIGN(1,4) = 4 B serialized. Both are below every eligibility floor |
| TEST 4 | `payload_is_null` 1, `tag_ok` 1, `nullable_is_null` 1, `empty_octets` 0 | setting the demoted column to NULL leaves its neighbours untouched |
| TEST 5 | `payload` 4200 and `tag` 300, both `ok` 1 | reassignment reads back exactly |
| TEST 6 | first `empty_is_null` 1; then `empty_is_null` 0 and `empty_octets` 0 | NULL and empty are distinguishable in both directions |

## 9. `cbrd_26659_oos_rep10_many_stubs` — OOS-REP-10, OOS-REP-02

| Statement group | Expected | Why |
|---|---|---|
| TEST 1 | eighteen rows, every `octets` 30, every `ok` 1 | record 656 B, below both gates |
| TEST 2 | eighteen rows: 700, 690, … 530, every `ok` 1 | record 11,276 B; twelve demotions are needed before it fits |
| TEST 3 | `n_distinct_digests` **18**, `n_columns` **18** | no column borrowed another's value — the check that stops TEST 2 from passing on eighteen identical columns |
| TEST 4 | `n_rows` 2, `n_aliased_first_pair` 0, `n_aliased_last_pair` 0, `first_octets_total` **730**, `last_octets_total` **560** | 30 + 700 and 30 + 530 |

## 10. `cbrd_26659_oos_rep11_transitions` — OOS-REP-11, OOS-REP-01

| Statement group | Expected | Why |
|---|---|---|
| TEST 1 | `a` 40, `b` 40, both `ok` 1 | record 140 B; header + payload 124, at or below `OR_MAX_BYTE` 127, so one-byte offset entries |
| TEST 2 | `a` 40, `b` 44, both `ok` 1 | record 148 B; header + payload 128, above 127, so two-byte entries |
| TEST 3 | `payload` 4200, `tag` 30, both `ok` 1 | two-byte entries before the demotion, one-byte after it |
| TEST 4 to 7 | `payload` 3000 → 4200 → 3000 → 4200 → 3000, `tag` 300 throughout, every flag 1 | four crossings of the gate; the logical value is never affected |
| TEST 8 | `n_rows` 2, `n_distinct_payloads` 2, `n_aliased` 0 | the narrow row and the transitioned row |

## 11. `cbrd_26659_oos_rep13_placement_hints` — OOS-REP-13 (BLOCKED)

**This case asserts no placement, and its recorded outcome is BLOCKED, not PASS** (ticket 39
item 2; the catalogue gives OOS-REP-13 status BLOCKED, gap kind Specification gap, policy
`withhold`). What the answer carries is logical correctness and an error path, both of which hold
whatever the placement policy turns out to be.

| Statement group | Expected | Why |
|---|---|---|
| TEST 1 | `hinted` 40, `tag` 300, both `ok` 1 | `STORAGE FORCE_OUTLINE` on a record far below the gate |
| TEST 2 | `hinted` 2000, `other` 1900, `tag` 300, every `ok` 1 | `STORAGE PREFER_INLINE` on the largest column of a record above the gate |
| TEST 3 | the same three lengths, every `ok` 1 | `STORAGE PREFER_OUTLINE`, an alias of `STORAGE DEFAULT` at this revision (`parse_tree.h:1948-1949`) |
| TEST 4 | **`Error:-495`** | `ER_PT_EXECUTE`, `error_code.h:585`. `do_validate_oos_storage_setting` refuses a hint on anything but a variable-type normal attribute (`execute_schema.c:8075-8086`) and returns `ER_PT_SEMANTIC` internally, but it runs inside `do_add_attribute` in the **execution** phase, and a statement whose parser error list is non-empty after `do_statement` is reported to the client by `pt_report_to_ersys_with_statement (parser, PT_EXECUTION, statement)` (`db_vdb.c:2392`, `:2539`), which sets `ER_PT_EXECUTE` (`query_result.c:312-315`). **Corrected before promotion**: revision 1 of this document named -494, the internal return value, and the first candidate review caught it (finding T18-F2). The correction is a re-derivation from the two source sites above, not a value copied from the run |
| TEST 5 | `n_classes` **0** | the refused DDL created no class |
| TEST 6 | two groups of three rows, 2000 / 1900 / 300, every `ok` 1 | `ALTER … MODIFY … STORAGE FORCE_OUTLINE` and back to `STORAGE DEFAULT` leave every stored value exact |
| TEST 7 | four rows, each `n_rows` 1 and `n_distinct` 1 | every hinted table holds exactly its own row |

## 12. Placement: what the paired `SHOW HEAP OOS` check asserts, and what it only observes

None of these figures reaches an answer file. They are the expectations of the nine specs under
[`activation/`](activation/), run by `tools/activation_check_spec.sh` client-server in the case's
own run mode. A dash means the figure is **observed** — printed with its context and unable to
fail the run — which is what the authority policy requires of a quantity that is not settled at
this revision.

| Case / phase | `Has_oos_file` | `Oos_num_recs` | `Oos_recs_sumlen` | Note |
|---|---:|---:|---:|---|
| rep01 / inline | 0 | 0 | 0 | |
| rep01 / oosbacked | 1 | 1 | 3748 | |
| rep01 / band_low, band_high | – | – | – | the accepted four-record target would give 1 / 1 / 3724 and 1 / 1 / 3744; the pin keeps both inline |
| rep02 / comparator | 0 | 0 | 0 | |
| rep02 / unequal | 1 | 1 | **2024** | 1924 would mean the smaller candidate moved |
| rep02 / tie | 1 | 1 | 2024 | the same either way the tie broke |
| rep02 / cascade | 1 | 2 | 4348 | |
| rep04 / comparator | 0 | 0 | 0 | |
| rep04 / below_floor | 1 | **1** | 4224 | two would mean the 15 B value was demoted |
| rep04 / above_floor | 1 | **2** | 4268 | |
| rep04 / floor_band | – | – | – | the accepted 24-byte layout would give 1 / 1 / 4224; the pin demotes the 20 B value |
| rep07 / comparator | 0 | 0 | 0 | |
| rep07 / one_chunk | 1 | 1 | 16296 | |
| rep07 / two_chunks | 1 | 2 | 16324 | |
| rep07 / three_chunks | 1 | 3 | 32632 | |
| rep08 / comparator | 0 | 0 | 0 | |
| rep08 / accepted | 1 | 1 | 88 | |
| rep08 / rejected | **0** | **0** | **0** | "before any chunk is written" — the clause the case itself cannot see |
| rep08 / nonoos_bigone | 0 | 0 | 0 | |
| rep09 / comparator | 0 | 0 | 0 | |
| rep09 / oosbacked | 1 | **1** | 4224 | neither the NULL nor the empty column was demoted |
| rep09 / updated_to_null | – | – | – | chain reclamation after an UPDATE is a vacuum question (OOS-SQL-03) |
| rep10 / comparator | 0 | 0 | 0 | |
| rep10 / wide | 1 | **12** | 8016 | the sum names *which* twelve, not only how many |
| rep11 / vot_inline | 0 | 0 | 0 | |
| rep11 / vot_narrowed | 1 | 1 | 4224 | |
| rep11 / inline_before | 0 | 0 | 0 | |
| rep11 / crossed_up | 1 | 1 | 4224 | the one transition assertion of the family |
| rep11 / crossed_down | – | – | – | the chain the previous UPDATE created is not reclaimed synchronously (OOS-SQL-03) |
| rep13 / all four phases | – | – | – | OOS-REP-13 is BLOCKED; there is no expectation to assert |

`Oos_recs_sumlen` counts serialized payload plus one chunk header per chunk record, at the
**pinned** 16-byte header. The 24-byte normative header would give different numbers; that
difference is the Capability gap already recorded against OOS-REP-05, and it is why these figures
live in a checker and never in an answer.

## 13. The syntax smoke, and what it is not

Before any CTP invocation, the statement forms these cases use that had no precedent in the
scenario were executed once on a throwaway standalone database
([`syntax-smoke.sql`](syntax-smoke.sql), [`syntax-smoke.out`](syntax-smoke.out)): a zero-length
`CAST('' AS BIT VARYING)` beside a NULL, a `BIT(160000)` fixed column, the three storage hints and
an `ALTER … MODIFY … STORAGE`, a hint on an INT column, a 32,576-byte value, and an OOS + bigone
rejection. It answered four questions that shape the cases and the specs, and it is the source of
no expectation in this document:

1. **csql continues past an error when reading a file**, which is what lets the rep08 spec put a
   `SHOW HEAP OOS` after the rejected INSERT.
2. `CAST('' AS BIT VARYING)` yields a value that is not NULL and has zero octets.
3. A hint on an INT column is refused, and the refused `CREATE TABLE` creates no class.
4. The rejection message reports "16237 bytes … 16236 bytes", the two numbers §7 derives.

It also reproduced, incidentally, two figures this document derives independently:
`Oos_recs_sumlen` **32632** for the three-chunk value, and `MD5` `03b79d18…` for 32,576 bytes of
`'a'`, which `hashlib.md5(('a'*65152).encode())` gives without CUBRID. Where §1 to §12 and the
smoke disagree, this document is the oracle and the difference is a finding.
