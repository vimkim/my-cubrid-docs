# CBRD-26979 — OOS STORAGE variable-type validation plan

- JIRA: http://jira.cubrid.org/browse/CBRD-26979
- Source branch: `cbrd-26979-storage-syntax-error`
- Source commit: `07fef9d48b4776e60c42e8afa25b9f21c54b8226`
- Written: 2026-08-05

## Goal

Reject every explicit OOS `STORAGE` column option on attributes that cannot participate in OOS storage, and return a
clear user-facing semantic error. When an existing policy-bearing variable attribute is changed to an ineligible type
without an explicit `STORAGE` clause, allow the ALTER and silently remove the inherited policy.

## Agreed contract

All four explicit clauses are OOS policy syntax and therefore have the same eligibility rule:

- `STORAGE PREFER_INLINE`
- `STORAGE FORCE_OUTLINE`
- `STORAGE PREFER_OUTLINE`
- `STORAGE DEFAULT`

An attribute is eligible only when all of the following are true:

1. It is a normal instance attribute (`ID_ATTRIBUTE`).
2. It belongs to a real class (`SM_CLASS_CT`), not a VCLASS.
3. Its domain type satisfies `pr_is_variable_type()`.

`pr_is_variable_type()` is the schema-time source for the physical fixed/variable classification. The heap write path
later consumes the derived class representation through `OR_ATTRIBUTE.is_fixed`, so this is the correct validation
predicate for the SQL schema layer. This intentionally follows physical storage classification rather than whether a
SQL type name contains `VARYING`; for example, a physically variable `CHAR` is eligible while a fixed-layout `BIT(n)`
is not.

| DDL case | Expected result |
|---|---|
| Eligible variable attribute + any explicit STORAGE clause | Accept |
| Fixed-layout attribute + any explicit STORAGE clause | Reject with `ER_PT_SEMANTIC` |
| CLASS, SHARED, or VCLASS attribute + any explicit STORAGE clause | Reject with `ER_PT_SEMANTIC` |
| Existing policy + ALTER to an ineligible type with STORAGE omitted | Succeed and clear the inherited policy |
| Existing policy + ALTER to another eligible variable type with STORAGE omitted | Succeed and preserve the policy |
| Fixed-layout attribute with no STORAGE clause | Accept normally |

`STORAGE DEFAULT` and `STORAGE PREFER_OUTLINE` remain aliases for the default OOS policy, but explicitly spelling either
one is still an attempt to assign an OOS storage policy and must be rejected for ineligible attributes.

## Current implementation gap

At the source revision above:

- `STORAGE FORCE_OUTLINE` already validates normal-class and variable-type eligibility in both CREATE and ALTER.
- `STORAGE PREFER_INLINE` rejects CLASS/SHARED attributes but accepts fixed-layout attributes and can be accepted for a
  VCLASS.
- Explicit `STORAGE DEFAULT` and `STORAGE PREFER_OUTLINE` are accepted on fixed-layout attributes.
- ALTER with an omitted STORAGE clause silently removes an inherited `FORCE_OUTLINE` policy when the new type is
  ineligible, but does not symmetrically remove `PREFER_INLINE`.

The current behavior can consequently persist an inert `PREFER_INLINE` flag on a fixed-layout attribute and emit DDL
that the corrected implementation would reject.

## Implementation

### 1. Centralize STORAGE eligibility

Add a small helper in `src/query/execute_schema.c` that checks the normal-attribute, real-class, and physical
variable-type conditions. Use this helper for both CREATE/ADD and ALTER MODIFY/CHANGE so the accepted domain cannot
drift between schema paths.

### 2. Validate CREATE and ADD before mutating the template

In `do_add_attribute()`, validate every explicit setting (`attr_storage != PT_ATTR_STORAGE_UNSET`) after the domain and
attribute namespace are known but before `smt_add_attribute_w_dflt_w_order()` mutates the class template.

Replace the FORCE_OUTLINE-only validation and remove the later partial PREFER_INLINE namespace validation. Flag
persistence remains unchanged after the common validation succeeds.

### 3. Validate ALTER and clear incompatible inherited policies

In `build_attr_change_map()`, validate every explicit setting after resolving the new domain:

- Explicit setting + ineligible new attribute: report the semantic error and reject the ALTER.
- Omitted setting + ineligible new attribute: mark each inherited OOS policy flag as lost.
- Omitted setting + eligible new attribute: retain the existing `UNCHANGED` behavior.

Generalize the existing FORCE_OUTLINE cleanup to both `P_OOS_FORCE_OUTLINE` and `P_OOS_PREFER_INLINE`. The existing
`do_change_att_schema_only()` application logic will then clear the corresponding schema flags. Clearing both also
self-heals an impossible/corrupt state where both flags are present.

### 4. Generalize the user error

Rename the FORCE_OUTLINE-specific semantic message identifier at parser semantic message slot 339 and update the
English and Korean catalogs with generic wording, for example:

```text
STORAGE options can be set only on variable-type normal attributes of a class: 'c'.
```

Use `ER_PT_SEMANTIC`; no new engine error code or catalog-format change is required. Generic wording is necessary
because `PT_ATTR_STORAGE_DEFAULT` also represents `PREFER_OUTLINE`, so the parse-tree state intentionally does not
retain which of those two equivalent spellings was used.

## Test plan

Extend `unit_tests/oos/sql/test_oos_sql_storage.cpp`, which exercises the full parser and schema path in SA_MODE.

### Explicit-clause rejection

- Reject all four clauses on `INT` during CREATE.
- Reject representative clauses on fixed-layout `BIT(n)` to prove that physical classification—not SQL spelling—is
  authoritative.
- Reject all four clauses during ALTER MODIFY/CHANGE to a fixed-layout type.
- Assert the generic user-facing message, not a FORCE_OUTLINE-specific string.

### Eligible types and object kinds

- Preserve acceptance for physically variable `VARCHAR`, `CHAR`, and `BIT VARYING` attributes.
- Preserve/reinforce rejection for CLASS and SHARED attributes.
- Reject STORAGE options on VCLASS attributes consistently, including PREFER_INLINE/default-policy spellings.

### ALTER policy transitions

- `PREFER_INLINE` + omitted STORAGE + variable-to-fixed type change succeeds and removes the policy from SHOW CREATE.
- Existing `FORCE_OUTLINE` variable-to-fixed cleanup remains successful.
- Omitted STORAGE on a variable-to-variable change preserves the current policy.
- A failed explicit fixed-type ALTER leaves the original schema policy and data unchanged after transaction abort.

The tests validate schema semantics only; predictable OOS value sizing is not involved. Existing OOS placement tests
continue to use `BIT VARYING` where physical size matters.

## Expected files

- `src/query/execute_schema.c`
- `src/parser/parser_message.h`
- `msg/en_US.utf8/cubrid.msg`
- `msg/ko_KR.utf8/cubrid.msg`
- `unit_tests/oos/sql/test_oos_sql_storage.cpp`

No changes are expected in the grammar, parse-tree storage enum, schema flag layout, object representation, heap OOS
demotion policy, OOS file code, or catalog disk format.

## Verification

For local development in this worktree:

1. Run the focused storage SQL test before and after the change.
2. Run `direnv exec . just build` after production-code changes.
3. Run `direnv exec . just build-test` for the configured regression set.
4. Run the focused `test_oos_sql_storage` test with failure output enabled.
5. Run the surrounding OOS SQL tests to catch schema/parser regressions.
6. Review the final diff for unintended formatting changes; CUBRID `.c` indentation must remain unchanged outside the
   semantic edits.

## Scope boundaries

- No retroactive heap-record rewrite: ALTER changes schema policy only, as before.
- No bulk catalog migration for experimental schemas that already contain an inert policy. An omitted-clause ALTER to
  an ineligible definition cleans the policy; future explicit invalid DDL is rejected.
- No change to OOS demotion thresholds, ordering, OOS inline-stub layout, WAL, replication, vacuum, or recovery.

## Execution status — 2026-08-05

Implemented in the `cbrd-26979-storage-syntax-error` working tree as uncommitted changes.

- Red verification: the expanded `test_oos_sql_storage` suite failed 6 tests against the original implementation,
  reproducing fixed-type acceptance, VCLASS acceptance, and retained PREFER_INLINE state.
- Green focused verification: all 21 `test_oos_sql_storage` test cases passed after the implementation.
- `direnv exec . just build`: passed.
- `direnv exec . just build-test`: passed all 25 configured tests, including the OOS unit, SERVER_MODE, and SQL suites.
