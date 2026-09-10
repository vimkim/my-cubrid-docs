# PR #7600: choose the partition before writing OOS data

The change has one main purpose: **write a row's OOS data for the heap that will receive the row.** Start with this example. The full code review is linked at the end.

## 1. Follow one row

A partitioned table divides its rows between child tables. In our example, `p0` receives IDs below 10. `p1` receives the other IDs.

Each child has a **heap**: the storage that holds its rows.

A column value can be stored outside the row. CUBRID calls this **OOS**, or out-of-row overflow storage. The row keeps **location information** instead of the value itself. “Follow the reference” means read the value at that location. The heap has an associated OOS file for these values.

We insert `id = 1` with a 64-byte value. The test forces the value into OOS, even though it is small. The row must go to `p0`, because 1 is below 10.

<details><summary>See the SQL setup</summary>

```sql
CREATE TABLE t_oos_show_part (
  id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE
) PARTITION BY RANGE (id) (
  PARTITION p0 VALUES LESS THAN (10),
  PARTITION p1 VALUES LESS THAN MAXVALUE
);
INSERT INTO t_oos_show_part VALUES (1, REPEAT(X'EE', 64));
COMMIT;
```

`STORAGE FORCE_OUTLINE` makes this test use OOS. `REPEAT(X'EE', 64)` supplies the test value.

</details>

## 2. What went wrong?

The old code could write the OOS value **before** it chose `p0`.

At that point, it still used the root table as the OOS owner. The root is the table named in the INSERT. The result could be:

- Row: stored in the `p0` heap.
- OOS value: stored in the root heap's OOS file.

What happens if we run SELECT in this incorrect state?

1. Read the row with `id = 1` from `p0`.
2. Read the location information in that row. It points to the value in the root heap's OOS file.
3. Read the 64-byte value at that location and return it.

The read can use the location recorded in the row. **SELECT can therefore return the correct value even when the OOS value was written for the wrong heap.**

But this row belongs in `p0`. Its OOS value must be stored in **the OOS file associated with the `p0` heap**. This storage relationship is what this guide means by “`p0` owns the OOS data.”

Vacuum relies on this relationship when it removes old data. When cleaning the row in `p0`, it looks for the OOS file associated with the `p0` heap. In this example, the value is stored for the root, and `p0` has no OOS file at all. A row that reads correctly can therefore cause a problem during cleanup.

## 3. What does the PR change?

The code now uses the partition key to choose the destination first. The partition key in this example is `id = 1`.

The new order is:

1. Use the key to select `p0`.
2. Build the row and write its OOS value using `p0` as the owner.
3. Check the destination again from the built row, then store the row.

The final check remains. If the destinations disagree, the operation reports an error. It must not send the row to another heap after choosing the OOS owner.

## 4. Where is that change in the code?

Read these two points first. You do not need every helper yet.

**Choose the destination:** in `locator_attribute_info_force`, the call to `partition_prune_insert_by_attrinfo` selects the child and fills `write_destination`. The later row-building call receives that destination. [Read these statements](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7775).

**Use that destination for OOS:** the OOS write selects its owner with this expression:

```cpp
oos_class_oid != NULL ? oos_class_oid : &attr_info->class_oid
```

This means: use the supplied OOS owner when one is present. Otherwise, use the class already in the attribute information. [Read the call](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12888).

Passing a separate owner lets the code retain the original class information for the rest of the operation.

## 5. How does the test detect the bug?

The test first checks that the value reads back correctly. It then checks **where the OOS data belongs**:

- Root: no OOS file, zero OOS chunks.
- `p0`: an OOS file, one OOS chunk.
- `p1`: no OOS file, zero OOS chunks.

These checks distinguish correct ownership from a value that merely reads correctly. [Read the test](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L437).

This describes the test's assertions. We did not rerun the engine test for this guide. This one case does not prove every UPDATE, rollback, or vacuum path.

## Pause before the detailed review

**Why does the test check the OOS file after checking the returned value?**

<details><summary>Show the answer</summary>

SELECT checks **“Do we get the same 64-byte value back?”** That check can pass even if the row in `p0` points to a value stored for the root.

The test also uses `SHOW ALL HEAP OOS` to check **“Is the OOS file holding this value associated with the root, or with `p0`?”**

For this example, `p0` must have an OOS file with one chunk, and the root must have none. These checks establish both the returned value and the required storage location.

</details>

When this example is clear, continue with UPDATE, the effective-key helper, and duplicate-key probes in the [full reference](review.en.md). The [Korean reference](review.ko.html) contains all 63 diff hunks. Those are further reading, not prerequisites for this example.

Source snapshot: `479cd960ec`, compared with `f4299ac0cd`.
