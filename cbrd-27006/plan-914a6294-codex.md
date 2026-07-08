# Plan for 914a6294 review: keep heap attribute readers static

## Review input

`my-review-914a6294.md` asks to revisit the grouped OOS Resolve path introduced around
`heap_oos_read_dbvalues_grouped()` and avoid exporting these two heap attribute helpers:

- `heap_attrvalue_transform_to_dbvalue()`
- `heap_attrvalue_read()`

Both should remain `static` in `heap_file.c`.

## Current issue

`heap_oos.cpp` currently drives part of the attribute-layer DB_VALUE read flow:

- it detects requested OOS attributes with `heap_oos_find_attr_inline_ref()`;
- it batches the OOS payload fetch with `oos_read_many()`;
- it completes each OOS value by calling `heap_attrvalue_transform_to_dbvalue()`;
- it reads non-OOS/default attributes by calling `heap_attrvalue_read()`.

That split forces private heap read helpers into `heap_file.h`. The result is an awkward ownership
boundary: `heap_file.c` owns scalar attribute read invariants, but `heap_oos.cpp` now has to know how
to finish `HEAP_ATTRVALUE` state.

## Preferred shape

Treat grouped lazy OOS Resolve as a local optimization of
`heap_attrinfo_read_dbvalues_internal()`, not as a public heap_oos service.

Keep in `heap_file.c`:

- requested-attribute filtering;
- default/fixed/non-OOS fallback through the scalar reader;
- `HEAP_ATTRVALUE` state changes;
- disk raw value to `DB_VALUE` conversion;
- grouped lazy Resolve orchestration for `heap_attrinfo_read_dbvalues_internal()`.

Keep in `heap_oos.cpp`:

- record-level OOS Expand through `heap_record_replace_oos_oids()`;
- common OOS inline reference validation through `heap_oos_parse_inline_ref()`;
- OOS file write/delete helpers such as `heap_oos_insert_serialized_values()` and
  `heap_oos_delete_unreferenced()`.

## Implementation steps

1. Restore the private helper boundary.

   Change `heap_attrvalue_transform_to_dbvalue()` and `heap_attrvalue_read()` back to `static int`
   in `heap_file.c`, and remove their declarations from `heap_file.h`.

2. Move the grouped lazy Resolve code into `heap_file.c`.

   Move the logic currently in `heap_oos_find_attr_inline_ref()`,
   `heap_oos_read_dbvalues_grouped()`, and `heap_oos_read_dbvalues_grouped_if_needed()` next to
   `heap_attrinfo_read_dbvalues_internal()`. Rename the helpers to make the ownership clear, for
   example:

   - `heap_attrinfo_find_oos_inline_ref()`
   - `heap_attrinfo_read_dbvalues_grouped_oos()`
   - `heap_attrinfo_read_dbvalues_grouped_oos_if_needed()`

3. Keep the existing dispatch behavior.

   Preserve the current gate that only uses the grouped path when at least two requested attributes
   are OOS-marked. Single-OOS reads should still use the scalar path and its stack scratch buffer.

4. Keep OOS parsing shared, but only at the right level.

   Leave `heap_oos_parse_inline_ref()` public in `heap_oos.hpp`; both record-level Expand and
   attribute-level Resolve need the same inline-header corruption checks. After the grouped helper is
   moved, re-check whether `heap_recdes_get_var_offset_entry()` has any external caller. If not,
   make it `static` too and remove it from `heap_file.h`.

5. Simplify the heap_oos API.

   Remove `heap_oos_read_dbvalues_grouped_if_needed()` from `heap_oos.hpp` and delete the grouped
   DB_VALUE Resolve helpers from `heap_oos.cpp`. Update comments so `heap_oos.cpp` no longer claims
   ownership of attribute-level lazy Resolve.

6. Preserve cleanup and error behavior.

   The moved grouped helper should keep the current allocation and cleanup contract:

   - allocate grouped OOS raw buffers with `recdes_allocate_data_area()`;
   - call `oos_read_many()` once;
   - transform OOS raws with `heap_attrvalue_transform_to_dbvalue(..., true)`;
   - use `heap_attrvalue_read()` for non-OOS/default attributes;
   - free every allocated `RECDES` buffer on both success and error paths.

## Verification

- `rg -n "extern int heap_attrvalue_(transform_to_dbvalue|read)" src/storage/heap_file.h` should
  return no matches.
- `rg -n "heap_attrvalue_transform_to_dbvalue|heap_attrvalue_read" src/storage/heap_oos.cpp` should
  return no matches.
- `rg -n "static int heap_attrvalue_transform_to_dbvalue|static int heap_attrvalue_read" src/storage/heap_file.c`
  should find both definitions.
- Run `just build`.
- Run `just build-test`.

## Notes

Do not duplicate DB_VALUE conversion logic in `heap_oos.cpp`; that would create a second scalar read
contract. Also avoid a callback/bridge API just to keep the code split, since it would preserve the
same ownership problem in a less direct form.
