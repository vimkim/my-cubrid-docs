why is heap_attrvalue_transform_to_dbvalue () static int -> int?
Analyze static int -> int cases ( I see two)

Reply:

- Confirmed two formerly-static heap helpers were exported: `heap_attrvalue_transform_to_dbvalue()` and `heap_attrvalue_read()`.
- `heap_oos.cpp` needs `heap_attrvalue_transform_to_dbvalue()` after grouped `oos_read_many()` returns serialized OOS payloads; it must transform those payloads with the same scalar heap read contract instead of duplicating conversion logic.
- `heap_oos.cpp` needs `heap_attrvalue_read()` as the grouped Resolve fallback for non-OOS/default attributes in the same requested attribute set.
- Kept both implementations in `heap_file.c` and added header comments marking them as narrow exports for `heap_oos.cpp`, not general-purpose heap APIs.

My reply:

This part is very ugly. Read though heap_file and heap_oos files,
see caller and callees, and see if you can rewrite this part more readable and elegantly, without making the two functions public (they must be still static).

---

