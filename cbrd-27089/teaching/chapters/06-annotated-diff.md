# 6. Every changed line, in its source context

This chapter covers all 30 default-context Git hunks. Read chapters 1–5 first, then use this appendix to connect every addition and deletion to the mechanism. The complete original diff is preserved in `evidence/pr-7600.patch`. Blank lines and brace-only changes are shown along with executable statements.

Each listing shows **old line | new line | diff sign | source text**. A dash means that side has no line. `+` is added at the head, `-` is deleted from the base, and a blank sign is unchanged context. Source text is preserved apart from display tab expansion. Hunk headers come from Git and may name a preceding symbol; the commentary identifies the actual affected function.

For each hunk: identify inputs, follow the described state changes, then explain what its omission would affect. Structural signature/include hunks make the changed code callable; they need not each produce an independent runtime effect.

## Coverage index

| Hunk | File | Old lines | New lines | Lesson |
|---|---|---|---|---|
| [H01](#h01) | `src/query/query_executor.c` | 11937–11942 | 11937–11943 | REPLACE allocates a mode selector |
| [H02](#h02) | `src/query/query_executor.c` | 11951–11957 | 11952–11962 | REPLACE suppresses discarded-image OOS writes |
| [H03](#h03) | `src/query/query_executor.c` | 12170–12175 | 12175–12181 | ODKU allocates its mode selector |
| [H04](#h04) | `src/query/query_executor.c` | 12189–12195 | 12195–12205 | ODKU obtains an inline key image |
| [H05](#h05) | `src/storage/heap_file.c` | 694–702 | 694–703 | Declare layout mode and verdict |
| [H06](#h06) | `src/storage/heap_file.c` | 782–788 | 783–790 | Declare the internal transformation protocol |
| [H07](#h07) | `src/storage/heap_file.c` | 12297–12305 | 12299–12309 | Document hypothetical versus actual layout |
| [H08](#h08) | `src/storage/heap_file.c` | 12307–12315 | 12311–12320 | Match the layout definition to its declaration |
| [H09](#h09) | `src/storage/heap_file.c` | 12320–12325 | 12325–12334 | Clear the verdict before planning |
| [H10](#h10) | `src/storage/heap_file.c` | 12334–12339 | 12343–12357 | Stop FORCE_OUTLINE selection inside a probe |
| [H11](#h11) | `src/storage/heap_file.c` | 12369–12374 | 12387–12405 | Return full inline size for an ordinary probe |
| [H12](#h12) | `src/storage/heap_file.c` | 12680–12690 | 12711–12725 | Carry an owner without replacing attribute metadata |
| [H13](#h13) | `src/storage/heap_file.c` | 12724–12730 | 12759–12765 | Select the actual OOS owner at publication |
| [H14](#h14) | `src/storage/heap_file.c` | 12755–12761 | 12790–12834 | Expose ordinary, probe and final wrappers |
| [H15](#h15) | `src/storage/heap_file.c` | 12775–12781 | 12848–12855 | Preserve the except-LOB entry point |
| [H16](#h16) | `src/storage/heap_file.c` | 13232–13243 | 13306–13322 | Specify the internal caller obligations |
| [H17](#h17) | `src/storage/heap_file.c` | 13245–13250 | 13324–13331 | Derive suppression and allocate an index variable |
| [H18](#h18) | `src/storage/heap_file.c` | 13258–13263 | 13339–13357 | Reconstruct the increment guard for the second pass |
| [H19](#h19) | `src/storage/heap_file.c` | 13271–13278 | 13365–13372 | Pass mode and verdict into layout calculation |
| [H20](#h20) | `src/storage/heap_file.c` | 13307–13313 | 13401–13407 | Forward the selected owner only when inserting OOS |
| [H21](#h21) | `src/storage/heap_file.c` | 28431–28436 | 28525–28530 | Keep the unit-test bridge on its original owner |
| [H22](#h22) | `src/storage/heap_file.h` | 507–512 | 507–518 | Publish the two transformation interfaces |
| [H23](#h23) | `src/transaction/locator_sr.c` | 7475–7486 | 7475–7492 | Extend the copy-area adapter |
| [H24](#h24) | `src/transaction/locator_sr.c` | 7504–7510 | 7510–7526 | Dispatch probe before owner before LOB mode |
| [H25](#h25) | `src/transaction/locator_sr.c` | 7692–7700 | 7708–7770 | Orchestrate probe, early routing and final serialization |
| [H26](#h26) | `src/transaction/locator_sr.c` | 13781–13787 | 13851–13857 | Keep MVCC reevaluation on its existing path |
| [H27](#h27) | `src/transaction/locator_sr.h` | 83–89 | 83–90 | Expose the adapter’s expanded signature |
| [H28](#h28) | `unit_tests/oos/sql/test_oos_sql_show.cpp` | 21–26 | 21–27 | Include the string type directly |
| [H29](#h29) | `unit_tests/oos/sql/test_oos_sql_show.cpp` | 154–159 | 155–192 | Copy and normalize the diagnostic name |
| [H30](#h30) | `unit_tests/oos/sql/test_oos_sql_show.cpp` | 351–356 | 384–458 | Check value and all three heap owners |

<a id="h01"></a>
## H01. REPLACE allocates a mode selector

[C-101] Head: [src/query/query_executor.c:11937–11943](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L11937-L11943). Base: [src/query/query_executor.c:11937–11942](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/query/query_executor.c#L11937-L11942).

```text
 11937  11937     OID class_oid, pruned_oid;
 11938  11938     BTID btid;
 11939  11939     bool is_global_index;
     —  11940 +   bool probe_would_demote_oos = false;
 11940  11941     HFID class_hfid, pruned_hfid;
 11941  11942     int local_op_type = SINGLE_ROW_DELETE;
 11942  11943     HEAP_SCANCACHE *local_scan_cache = NULL;
```

The new local bool starts false. Its address is passed below to select probe mode. Its value is not consumed later: the helper needs suppression, not a demotion decision. Its lifetime covers the synchronous allocator call. Without an addressable object the caller could not select the pointer-based mode.

<a id="h02"></a>
## H02. REPLACE suppresses discarded-image OOS writes

[C-102] Head: [src/query/query_executor.c:11952–11962](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L11952-L11962). Base: [src/query/query_executor.c:11951–11957](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/query/query_executor.c#L11951-L11957).

```text
 11951  11952         goto error_exit;
 11952  11953       }
 11953  11954   
 11954      — -   copyarea = locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &new_recdes, -1, LOB_FLAG_EXCLUDE_LOB);
     —  11955 +   /* This record image is only probed for duplicate keys, never inserted: suppress OOS demotion so
     —  11956 +    * no OOS value chain is written (and later orphaned) for it. */
     —  11957 +   copyarea =
     —  11958 +     locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &new_recdes, -1, LOB_FLAG_EXCLUDE_LOB, NULL,
     —  11959 + 					     &probe_would_demote_oos);
 11955  11960     if (copyarea == NULL)
 11956  11961       {
 11957  11962         goto error_exit;
```

The deleted call used the ordinary transform. The new comment identifies this image as a duplicate-key candidate, and the replacement call appends NULL owner plus &probe_would_demote_oos. The owner argument does not choose a heap in probe mode. LOB_FLAG_EXCLUDE_LOB is preserved. The existing null-result check still goes to error_exit. No duplicate-search/deletion logic is replaced by this hunk.

<a id="h03"></a>
## H03. ODKU allocates its mode selector

[C-103] Head: [src/query/query_executor.c:12175–12181](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L12175-L12181). Base: [src/query/query_executor.c:12170–12175](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/query/query_executor.c#L12170-L12175).

```text
 12170  12175     OID class_oid;
 12171  12176     HFID class_hfid;
 12172  12177     bool is_global_index = false;
     —  12178 +   bool probe_would_demote_oos = false;
 12173  12179     int local_op_type = SINGLE_ROW_UPDATE;
 12174  12180     BTREE_SEARCH r;
 12175  12181   
```

This second local bool belongs to the duplicate-OID lookup helper, not the final UPDATE. Starting at false avoids stale state; pointer presence selects suppression. It remains alive until the allocator returns and is intentionally not used to decide whether an UPDATE should occur.

<a id="h04"></a>
## H04. ODKU obtains an inline key image

[C-104] Head: [src/query/query_executor.c:12195–12205](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L12195-L12205). Base: [src/query/query_executor.c:12189–12195](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/query/query_executor.c#L12189-L12195).

```text
 12189  12195         goto error_exit;
 12190  12196       }
 12191  12197   
 12192      — -   copyarea = locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &recdes, -1, LOB_FLAG_INCLUDE_LOB);
     —  12198 +   /* This record image is only probed for unique-index duplicates, never inserted: suppress OOS
     —  12199 +    * demotion so no OOS value chain is written (and later orphaned) for it. */
     —  12200 +   copyarea =
     —  12201 +     locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &recdes, -1, LOB_FLAG_INCLUDE_LOB, NULL,
     —  12202 + 					     &probe_would_demote_oos);
 12193  12203     if (copyarea == NULL)
 12194  12204       {
 12195  12205         goto error_exit;
```

The new comment explains why this candidate must not publish OOS chains. The call keeps old_recdes=NULL because it describes candidate INSERT values, keeps the default copy-area hint -1, and retains LOB_FLAG_INCLUDE_LOB. NULL and the verdict address select probe mode. The existing failure jump is unchanged. The helper then reads key values and finds a duplicate OID; the surrounding executor decides whether to update or insert.

<a id="h05"></a>
## H05. Declare layout mode and verdict

[C-105] Head: [src/storage/heap_file.c:694–703](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L694-L703). Base: [src/storage/heap_file.c:694–702](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L694-L702).

```text
   694    694     DB_BIGINT length = 0;
   695    695   };
   696    696   static int heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class,
   697      — - 						size_t * offset_size_ptr,
     —    697 + 						bool suppress_oos, size_t * offset_size_ptr,
   698    698   						std::vector<heap_oos_column_plan> * oos_plan,
   699      — - 						bool * has_oos, size_t * inline_size_after_oos_ptr);
     —    699 + 						bool * has_oos, bool * would_demote_oos,
     —    700 + 						size_t * inline_size_after_oos_ptr);
   700    701   // *INDENT-ON*
   701    702   
   702    703   static void heap_attrvalue_point_fixed (RECDES * recdes, HEAP_CACHE_ATTRINFO * attr_info, OR_ATTRIBUTE * attrepr,
```

The static declaration gains suppress_oos before offset_size_ptr and would_demote_oos before the final size output. The existing vector parameter still carries actual per-column selections. These are distinct concepts: suppress_oos controls selection, would_demote_oos reports a hypothetical selection, and has_oos reports actual selected content. The line splits align a longer declaration; they do not change the vector type.

<a id="h06"></a>
## H06. Declare the internal transformation protocol

[C-106] Head: [src/storage/heap_file.c:783–790](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L783-L790). Base: [src/storage/heap_file.c:782–788](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L782-L788).

```text
   782    783   
   783    784   static SCAN_CODE heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
   784    785   							   RECDES * old_recdes, record_descriptor * new_recdes,
   785      — - 							   int lob_create_flag);
     —    786 + 							   int lob_create_flag, const OID * oos_class_oid,
     —    787 + 							   bool * would_demote_oos, bool increments_already_applied);
   786    788   
   787    789   static int heap_update_statistics (THREAD_ENTRY * thread_p, const HFID * hfid, HEAP_HDR_STATS * heap_hdr,
   788    790   				   PGBUF_WATCHER * header_watcher);
```

The internal declaration now receives an optional owner, an optional verdict and increments_already_applied after the LOB mode. Every wrapper must provide all three. The pointer types preserve caller data: const OID prevents this function from modifying the chosen identity; bool* permits reporting and also selects suppression. The final bool conveys successful prior preparation, not a request to increment.

<a id="h07"></a>
## H07. Document hypothetical versus actual layout

[C-107] Head: [src/storage/heap_file.c:12299–12309](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12299-L12309). Base: [src/storage/heap_file.c:12297–12305](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12297-L12305).

```text
 12297  12299    *   return: NO_ERROR, or error code
 12298  12300    *   attr_info(in/out): The attribute information structure
 12299  12301    *   is_mvcc_class(in): true, if MVCC class
     —  12302 +  *   suppress_oos(in): true to keep every column inline even when the record exceeds the OOS trigger
 12300  12303    *   offset_size_ptr(out): offset size
 12301  12304    *   oos_plan(out): selected columns are demoted to OOS
 12302  12305    *   has_oos(out): true if any column is demoted to OOS
     —  12306 +  *   would_demote_oos(out): with suppress_oos, true if a normal layout would have demoted a column
 12303  12307    *   inline_size_after_oos_ptr(out): inline heap record size after OOS demotion
 12304  12308    *
 12305  12309    * Note: Choose the OOS layout and compute the inline heap record size. This size is not the logical
```

The two added parameter comments describe suppression and the verdict. Existing has_oos and oos_plan outputs remain actual-layout outputs. The word trigger in the suppression comment must be read with the forced-outline branch below: suppression also applies below the ordinary size threshold. Comments specify intent; the two guarded branches implement it.

<a id="h08"></a>
## H08. Match the layout definition to its declaration

[C-108] Head: [src/storage/heap_file.c:12311–12320](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12311-L12320). Base: [src/storage/heap_file.c:12307–12315](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12307-L12315).

```text
 12307  12311    */
 12308  12312   // *INDENT-OFF*
 12309  12313   static int
 12310      — - heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class, size_t * offset_size_ptr,
     —  12314 + heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class, bool suppress_oos,
     —  12315 + 					     size_t * offset_size_ptr,
 12311  12316   					     std::vector<heap_oos_column_plan> * oos_plan, bool * has_oos,
 12312      — - 					     size_t * inline_size_after_oos_ptr)
     —  12317 + 					     bool * would_demote_oos, size_t * inline_size_after_oos_ptr)
 12313  12318   // *INDENT-ON*
 12314  12319   {
 12315  12320   // *INDENT-OFF*
```

The definition accepts suppress_oos and would_demote_oos in the same order as the declaration. offset_size_ptr still receives the VOT offset width. The new parameters are then available inside the function; this signature hunk alone does not suppress any effects. The surrounding INDENT directives delimit existing C++-formatted declarations.

<a id="h09"></a>
## H09. Clear the verdict before planning

[C-109] Head: [src/storage/heap_file.c:12325–12334](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12325-L12334). Base: [src/storage/heap_file.c:12320–12325](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12320-L12325).

```text
 12320  12325     int i;
 12321  12326   
 12322  12327     *has_oos = false;
     —  12328 +   if (would_demote_oos != NULL)
     —  12329 +     {
     —  12330 +       *would_demote_oos = false;
     —  12331 +     }
 12323  12332   
 12324  12333     /* calcuate the entire size of columns */
 12325  12334     payload_size = heap_attrinfo_get_record_payload_size (attr_info, &column_size);
```

has_oos is still reset unconditionally. The added null check protects the optional pointer, and its assignment starts each planning call with a false hypothetical verdict. The braces make that assignment conditional. Later forced and ordinary candidates can set it true. Not resetting it would allow a reused caller bool to falsely request a final pass for a no-demotion row.

<a id="h10"></a>
## H10. Stop FORCE_OUTLINE selection inside a probe

[C-110] Head: [src/storage/heap_file.c:12343–12357](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12343-L12357). Base: [src/storage/heap_file.c:12334–12339](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12334-L12339).

```text
 12334  12343   	  && attr_info->values[i].last_attrepr->oos_storage == OR_ATTRIBUTE_OOS_STORAGE_FORCE_OUTLINE
 12335  12344   	  && !db_value_is_null (&attr_info->values[i].dbvalue) && column_size[i] > OR_OOS_INLINE_SIZE)
 12336  12345   	{
     —  12346 + 	  if (suppress_oos)
     —  12347 + 	    {
     —  12348 + 	      if (would_demote_oos != NULL)
     —  12349 + 		{
     —  12350 + 		  *would_demote_oos = true;
     —  12351 + 		}
     —  12352 + 	      continue;
     —  12353 + 	    }
     —  12354 + 
 12337  12355   	  (*oos_plan)[i].selected = true;
 12338  12356   	  payload_size -= column_size[i];
 12339  12357   	  payload_size += OR_OOS_INLINE_SIZE;
```

The surrounding condition has already established a non-null variable forced value larger than a stub. The added if(suppress_oos) detects the probe; the nested pointer check guards the output write; true reports that a final transform will need OOS. continue jumps to the next attribute before selected=true, payload subtraction, stub-size addition and has_oos=true. It also avoids doing ordinary selection merely because the forced policy bypasses the normal size gate. This is the second commit’s decisive fix.

<a id="h11"></a>
## H11. Return full inline size for an ordinary probe

[C-111] Head: [src/storage/heap_file.c:12387–12405](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12387-L12405). Base: [src/storage/heap_file.c:12369–12374](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12369-L12374).

```text
 12369  12387   	    }
 12370  12388   	}
 12371  12389   
     —  12390 +       if (suppress_oos)
     —  12391 + 	{
     —  12392 + 	  /* The caller only wants a fully-inline image plus the demotion verdict (e.g. to route a
     —  12393 + 	   * partitioned write before the target heap of its OOS value chains is known). */
     —  12394 + 	  if (would_demote_oos != NULL && !oos_candidates.empty ())
     —  12395 + 	    {
     —  12396 + 	      *would_demote_oos = true;
     —  12397 + 	    }
     —  12398 + 
     —  12399 + 	  *inline_size_after_oos_ptr = header_size + payload_size;
     —  12400 + 	  return NO_ERROR;
     —  12401 + 	}
     —  12402 + 
 12372  12403         // *INDENT-OFF*
 12373  12404         /* Demote order: columns flagged STORAGE PREFER_INLINE sink to the tail and are externalized
 12374  12405          * only as a last resort; within each priority class, largest first. The idx-descending
```

This block runs after candidate collection inside the record-size gate. suppress_oos selects it. The nonempty check reports a possible demotion only if an eligible variable value exists; an oversized fixed-only record does not qualify. It does not reset a true result from the forced loop. The size assignment uses the unchanged payload plus current header; it is an output-buffer size, not a guarantee that a slotted page can hold it. return NO_ERROR exits before sorting and plan mutation. Normal mode falls through to the old demotion loop.

<a id="h12"></a>
## H12. Carry an owner without replacing attribute metadata

[C-112] Head: [src/storage/heap_file.c:12711–12725](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12711-L12725). Base: [src/storage/heap_file.c:12680–12690](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12680-L12690).

```text
 12680  12711    * the BLOB/CLOB ELO-locator copy step, with the inline record writer. This logical heap boundary
 12681  12712    * begins OOS insert publication before any fallible preparation; heap_oos.cpp owns the paired-reset
 12682  12713    * internals, OOS file lookup, and the batched OOS insert call.
     —  12714 +  *
     —  12715 +  * oos_class_oid designates the class whose heap receives the OOS value chains; NULL means
     —  12716 +  * attr_info->class_oid. A partitioned write must pass the pruned partition class, because the
     —  12717 +  * value chains must live in the OOS file of the heap that stores the record (CBRD-27089).
 12683  12718    */
 12684  12719   // *INDENT-OFF*
 12685  12720   static SCAN_CODE
 12686  12721   heap_attrinfo_insert_to_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, int lob_create_flag,
 12687      — - 			     std::vector<heap_oos_column_plan> * oos_plan)
     —  12722 + 			     const OID * oos_class_oid, std::vector<heap_oos_column_plan> * oos_plan)
 12688  12723   // *INDENT-ON*
 12689  12724   
 12690  12725   {
```

The added comment states the same-heap ownership rule and NULL fallback. The signature adds const OID* before the existing plan vector. The original attr_info remains the source of values, schema representation, MVCC classification and LOB serialization context. Only the downstream OOS file selection is redirected; changing attr_info->class_oid globally would have a wider effect.

<a id="h13"></a>
## H13. Select the actual OOS owner at publication

[C-113] Head: [src/storage/heap_file.c:12759–12765](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12759-L12765). Base: [src/storage/heap_file.c:12724–12730](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12724-L12730).

```text
 12724  12759         goto cleanup;
 12725  12760       }
 12726  12761   
 12727      — -   if (heap_oos_insert_serialized_values (thread_p, &attr_info->class_oid,
     —  12762 +   if (heap_oos_insert_serialized_values (thread_p, oos_class_oid != NULL ? oos_class_oid : &attr_info->class_oid,
 12728  12763   					 cubbase::span < oos_insert_request > (requests.data (), requests.size ()))
 12729  12764         != S_SUCCESS)
 12730  12765       {
```

The old expression always passed &attr_info->class_oid. The ternary now passes oos_class_oid when non-null, otherwise that original address. requests remains a span over the same prepared request vector, whose output OID pointers update plan entries. The existing failure condition still sends execution to cleanup. This one expression is where the early pruning decision becomes a storage-owner choice.

<a id="h14"></a>
## H14. Expose ordinary, probe and final wrappers

[C-114] Head: [src/storage/heap_file.c:12790–12834](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12790-L12834). Base: [src/storage/heap_file.c:12755–12761](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12755-L12761).

```text
 12755  12790   heap_attrinfo_transform_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
 12756  12791   				 record_descriptor * new_recdes)
 12757  12792   {
 12758      — -   return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_INCLUDE_LOB);
     —  12793 +   return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_INCLUDE_LOB,
     —  12794 + 						   NULL, NULL, false);
     —  12795 + }
     —  12796 + 
     —  12797 + /*
     —  12798 +  * heap_attrinfo_transform_to_disk_probe_oos () - Transform to disk with OOS demotion suppressed.
     —  12799 +  *
     —  12800 +  *   would_demote_oos(out): true if a normal transform would have demoted at least one column
     —  12801 +  *
     —  12802 +  * Note: Every column stays inline, so the resulting recdes can be larger than a slotted-page
     —  12803 +  * record allows; it is meant for record routing and key extraction, not for direct insertion.
     —  12804 +  * No OOS value chain is written. Side effects on attr_info (LOB copy, INCR/DECR application)
     —  12805 +  * still happen exactly once, so a subsequent heap_attrinfo_transform_to_disk_oos_class call
     —  12806 +  * completes the write without repeating them.
     —  12807 +  */
     —  12808 + SCAN_CODE
     —  12809 + heap_attrinfo_transform_to_disk_probe_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
     —  12810 + 					   RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag,
     —  12811 + 					   bool * would_demote_oos)
     —  12812 + {
     —  12813 +   return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, lob_create_flag,
     —  12814 + 						   NULL, would_demote_oos, false);
     —  12815 + }
     —  12816 + 
     —  12817 + /*
     —  12818 +  * heap_attrinfo_transform_to_disk_oos_class () - Transform to disk, writing OOS value chains to the
     —  12819 +  *                                                heap of oos_class_oid instead of attr_info->class_oid.
     —  12820 +  *
     —  12821 +  * Note: This is the second pass of a two-pass partitioned write; it assumes
     —  12822 +  * heap_attrinfo_transform_to_disk_probe_oos already ran on the same attr_info, so pending
     —  12823 +  * INCR/DECR assignments were already applied and are not applied again here.
     —  12824 +  */
     —  12825 + SCAN_CODE
     —  12826 + heap_attrinfo_transform_to_disk_oos_class (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
     —  12827 + 					   RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag,
     —  12828 + 					   const OID * oos_class_oid)
     —  12829 + {
     —  12830 +   return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, lob_create_flag,
     —  12831 + 						   oos_class_oid, NULL, true);
 12759  12832   }
 12760  12833   
 12761  12834   /*
```

The ordinary wrapper appends NULL,NULL,false, preserving ordinary layout and normal increment application. The first added documentation block explains that a probe image may exceed a page and writes no OOS chain; it still prepares DB_VALUE state. The probe wrapper forwards its LOB flag, no owner, the caller’s verdict pointer and false. A non-null verdict is a required caller convention. The second block documents the final wrapper’s successful-probe prerequisite. Its wrapper forwards the selected owner, NULL verdict and true. That disables suppression, restores normal policy and tells the internal writer not to repeat increments. All wrappers return SCAN_CODE directly, preserving error/status propagation; they introduce no local allocation or cleanup.

### Statement-by-statement reading guide

| Head lines | Meaning |
|---|---|
| 12793–12794 | Ordinary mode forwards include-LOB, no owner override, no verdict and no prior increment application. |
| 12797–12807 | Probe contract: inline bytes may exceed page capacity; OOS publication is suppressed but attribute preparation still occurs. |
| 12808–12811 | Public SCAN_CODE signature exposes the shared inputs and caller-owned verdict output. |
| 12813–12814 | Forward the verdict address to select suppression; false allows first-time increment application. |
| 12817–12824 | Final-pass contract requires the successful probe on the same attr_info; the selected class controls OOS ownership. |
| 12825–12828 | Final signature replaces the probe verdict with a const owner-class pointer. |
| 12830–12831 | Forward owner, NULL verdict and true: normal OOS policy, selected heap and seeded increment guard. |

<a id="h15"></a>
## H15. Preserve the except-LOB entry point

[C-115] Head: [src/storage/heap_file.c:12848–12855](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12848-L12855). Base: [src/storage/heap_file.c:12775–12781](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12775-L12781).

```text
 12775  12848   heap_attrinfo_transform_to_disk_except_lob (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 12776  12849   					    RECDES * old_recdes, record_descriptor * new_recdes)
 12777  12850   {
 12778      — -   return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_EXCLUDE_LOB);
     —  12851 +   return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_EXCLUDE_LOB,
     —  12852 + 						   NULL, NULL, false);
 12779  12853   }
 12780  12854   
 12781  12855   /*
```

The existing except-LOB wrapper gains NULL,NULL,false. It still passes LOB_FLAG_EXCLUDE_LOB, chooses no alternate owner and performs no probe. Updating this wrapper is necessary to match the longer internal signature, and preserves the existing behavior for callers that deliberately exclude LOB copying.

<a id="h16"></a>
## H16. Specify the internal caller obligations

[C-116] Head: [src/storage/heap_file.c:13306–13322](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13306-L13322). Base: [src/storage/heap_file.c:13232–13243](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L13232-L13243).

```text
 13232  13306    *   old_recdes(in): where the object's disk format is deposited
 13233  13307    *   new_recdes(in):
 13234  13308    *   lob_create_flag(in):
     —  13309 +  *   oos_class_oid(in): class whose heap receives the OOS value chains; NULL means attr_info->class_oid
     —  13310 +  *   would_demote_oos(out): non-NULL suppresses OOS demotion and reports whether it would have happened
     —  13311 +  *   increments_already_applied(in): true if a previous probe pass already applied INCR/DECR assignments
 13235  13312    *
 13236  13313    * Note: Transform the object represented by attr_info to disk format
 13237  13314    */
 13238  13315   static SCAN_CODE
 13239  13316   heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 13240      — - 					  RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag)
     —  13317 + 					  RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag,
     —  13318 + 					  const OID * oos_class_oid, bool * would_demote_oos,
     —  13319 + 					  bool increments_already_applied)
 13241  13320   {
 13242  13321     OR_BUF buf;
 13243  13322     size_t inline_size_after_oos, mvcc_extra;
```

Three parameter descriptions are added together with matching definition arguments. oos_class_oid picks storage owner with a NULL fallback; would_demote_oos selects suppressed mode when non-null; increments_already_applied says preparation already ran. The comments and definition must agree with both wrappers and the static declaration. The function continues to return SCAN_CODE; no new error enum is introduced.

<a id="h17"></a>
## H17. Derive suppression and allocate an index variable

[C-117] Head: [src/storage/heap_file.c:13324–13331](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13324-L13331). Base: [src/storage/heap_file.c:13245–13250](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L13245-L13250).

```text
 13245  13324     SCAN_CODE status;
 13246  13325     bool is_mvcc_class, is_update;
 13247  13326     bool has_oos;
     —  13327 +   bool suppress_oos = would_demote_oos != NULL;
     —  13328 +   int i;
 13248  13329     // *INDENT-OFF*
 13249  13330     std::vector<heap_oos_column_plan> oos_plan (attr_info->num_values);
 13250  13331     std::set<int> incremented_attrids;
```

bool suppress_oos = would_demote_oos != NULL tests the pointer, not the pointed-to value. int i supports the pre-seeding loop below. The existing oos_plan and incremented_attrids remain fresh per-call containers. Therefore a false value behind a non-null pointer still suppresses OOS, while a null pointer does not suppress it.

<a id="h18"></a>
## H18. Reconstruct the increment guard for the second pass

[C-118] Head: [src/storage/heap_file.c:13339–13357](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13339-L13357). Base: [src/storage/heap_file.c:13258–13263](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L13258-L13263).

```text
 13258  13339         return S_ERROR;
 13259  13340       }
 13260  13341   
     —  13342 +   if (increments_already_applied)
     —  13343 +     {
     —  13344 +       /* a probe pass already applied the pending INCR/DECR assignments to the dbvalues; pre-mark
     —  13345 +        * them so the column writer below does not apply them a second time */
     —  13346 +       for (i = 0; i < attr_info->num_values; i++)
     —  13347 + 	{
     —  13348 + 	  if (attr_info->values[i].do_increment != 0)
     —  13349 + 	    {
     —  13350 + 	      incremented_attrids.insert (i);
     —  13351 + 	    }
     —  13352 + 	}
     —  13353 +     }
     —  13354 + 
 13261  13355     /* get any of the values that have not been set/read */
 13262  13356     if (heap_attrinfo_set_uninitialized (thread_p, &attr_info->inst_oid, old_recdes, attr_info) != NO_ERROR)
 13263  13357       {
```

Only increments_already_applied enters this block. The loop visits each current attribute index, tests nonzero do_increment and inserts that index into the new set. It does not modify the DB_VALUE again or clear do_increment. The unchanged fixed writer later sees membership and skips qdata_increment_dbval. Braces delimit the mode guard, iteration and per-attribute guard. The successful probe on the same attr_info is essential: otherwise this set would falsely claim work had happened.

<a id="h19"></a>
## H19. Pass mode and verdict into layout calculation

[C-119] Head: [src/storage/heap_file.c:13365–13372](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13365-L13372). Base: [src/storage/heap_file.c:13271–13278](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L13271-L13278).

```text
 13271  13365     is_mvcc_class = !mvcc_is_mvcc_disabled_class (&(attr_info->class_oid));
 13272  13366   
 13273  13367     /* determine the layout and the size */
 13274      — -   if (heap_attrinfo_determine_disk_layout (attr_info, is_mvcc_class, &offset_size, &oos_plan, &has_oos,
 13275      — - 					   &inline_size_after_oos) != NO_ERROR)
     —  13368 +   if (heap_attrinfo_determine_disk_layout (attr_info, is_mvcc_class, suppress_oos, &offset_size, &oos_plan, &has_oos,
     —  13369 + 					   would_demote_oos, &inline_size_after_oos) != NO_ERROR)
 13276  13370       {
 13277  13371         return S_ERROR;
 13278  13372       }
```

The call adds suppress_oos after is_mvcc_class and the verdict before the size output, matching the new declaration. offset_size, plan and has_oos still receive concrete layout information. The existing comparison with NO_ERROR and S_ERROR return remain intact. Suppression is decided before layout, not patched into an already serialized record.

<a id="h20"></a>
## H20. Forward the selected owner only when inserting OOS

[C-120] Head: [src/storage/heap_file.c:13401–13407](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13401-L13407). Base: [src/storage/heap_file.c:13307–13313](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L13307-L13313).

```text
 13307  13401     if (has_oos)
 13308  13402       {
 13309  13403         /* insert big columns to OOS */
 13310      — -       status = heap_attrinfo_insert_to_oos (thread_p, attr_info, lob_create_flag, &oos_plan);
     —  13404 +       status = heap_attrinfo_insert_to_oos (thread_p, attr_info, lob_create_flag, oos_class_oid, &oos_plan);
 13311  13405         if (status != S_SUCCESS)
 13312  13406   	{
 13313  13407   	  return S_ERROR;
```

The call inside if(has_oos) adds oos_class_oid. A successful suppressed layout never enters this branch. Normal/final layouts use it to reach the conditional owner expression in the insertion helper. The existing S_SUCCESS check still returns S_ERROR on failure. This hunk does not move chain insertion into the buffer retry loop.

<a id="h21"></a>
## H21. Keep the unit-test bridge on its original owner

[C-121] Head: [src/storage/heap_file.c:28525–28530](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L28525-L28530). Base: [src/storage/heap_file.c:28431–28436](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L28431-L28436).

```text
 28431  28525   
 28432  28526     COPY_OID (&attr_info.class_oid, class_oid);
 28433  28527     attr_info.num_values = 0;
 28434      — -   return heap_attrinfo_insert_to_oos (thread_p, &attr_info, LOB_FLAG_INCLUDE_LOB, &oos_plan);
     —  28528 +   return heap_attrinfo_insert_to_oos (thread_p, &attr_info, LOB_FLAG_INCLUDE_LOB, NULL, &oos_plan);
 28435  28529   }
 28436  28530   #endif /* CUBRID_UNIT_TEST_ENABLED */
```

The bridge constructs attribute info with the provided class OID and no attribute values, then invokes the private helper. The new NULL argument means use the class already copied into attr_info. It is an API-compatibility adjustment for this test seam; it does not activate partition probing or force a second pass.

<a id="h22"></a>
## H22. Publish the two transformation interfaces

[C-122] Head: [src/storage/heap_file.h:507–518](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.h#L507-L518). Base: [src/storage/heap_file.h:507–512](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.h#L507-L512).

```text
   507    507   						  RECDES * old_recdes, record_descriptor * new_recdes);
   508    508   extern SCAN_CODE heap_attrinfo_transform_to_disk_except_lob (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
   509    509   							     RECDES * old_recdes, record_descriptor * new_recdes);
     —    510 + extern SCAN_CODE heap_attrinfo_transform_to_disk_probe_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
     —    511 + 							    RECDES * old_recdes, record_descriptor * new_recdes,
     —    512 + 							    int lob_create_flag, bool * would_demote_oos);
     —    513 + extern SCAN_CODE heap_attrinfo_transform_to_disk_oos_class (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
     —    514 + 							    RECDES * old_recdes, record_descriptor * new_recdes,
     —    515 + 							    int lob_create_flag, const OID * oos_class_oid);
   510    516   
   511    517   extern DB_VALUE *heap_attrinfo_generate_key (THREAD_ENTRY * thread_p, int n_atts, int *att_ids, int *atts_prefix_length,
   512    518   					     HEAP_CACHE_ATTRINFO * attr_info, RECDES * recdes, DB_VALUE * dbvalue,
```

The two extern declarations let locator_sr.c call the probe and final wrappers. Both retain thread, mutable attribute info, optional old record and managed output descriptor. Both accept the LOB flag. The last argument is a bool output for probe versus const class identity for final, reflecting their different contracts. Ordinary and except-LOB declarations remain available. These additions affect internal engine source interfaces, not a new SQL statement.

<a id="h23"></a>
## H23. Extend the copy-area adapter

[C-123] Head: [src/transaction/locator_sr.c:7475–7492](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7475-L7492). Base: [src/transaction/locator_sr.c:7475–7486](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/transaction/locator_sr.c#L7475-L7486).

```text
  7475   7475    *   copyarea_length_hint(in): An estimated size for the LC_COPYAREA or -1 if
  7476   7476    *                             an estimated size is not known.
  7477   7477    *   lob_create_flag(in) :
     —   7478 +  *   oos_class_oid(in): class whose heap receives the OOS value chains; NULL means
     —   7479 +  *                      attr_info->class_oid. A partitioned write passes the pruned partition.
     —   7480 +  *   probe_would_demote_oos(out): when non-NULL, suppress OOS demotion (build a fully-inline
     —   7481 +  *                                image, write no OOS value chain) and report whether a normal
     —   7482 +  *                                transform would have demoted a column.
  7478   7483    *
  7479   7484    * Note: The allocated should be freed by using locator_free_copy_area ()
  7480   7485    */
  7481   7486   LC_COPYAREA *
  7482   7487   locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
  7483      — - 					 RECDES * new_recdes, const int copyarea_length_hint, int lob_create_flag)
     —   7488 + 					 RECDES * new_recdes, const int copyarea_length_hint, int lob_create_flag,
     —   7489 + 					 const OID * oos_class_oid, bool * probe_would_demote_oos)
  7484   7490   {
  7485   7491     LC_COPYAREA *copyarea = NULL;
  7486   7492     int copyarea_length = copyarea_length_hint <= 0 ? DB_PAGESIZE : copyarea_length_hint;
```

The parameter comments explain the two pointer protocols. The function definition appends optional OOS owner and probe output arguments after lob_create_flag. Existing allocation size hint semantics are unchanged. The returned copy area still must be released by locator_free_copy_area; new_recdes describes bytes whose lifetime follows that area. Signature changes require all call sites and the header declaration to agree.

<a id="h24"></a>
## H24. Dispatch probe before owner before LOB mode

[C-124] Head: [src/transaction/locator_sr.c:7510–7526](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7510-L7526). Base: [src/transaction/locator_sr.c:7504–7510](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/transaction/locator_sr.c#L7504-L7510).

```text
  7504   7510     new_recdes->data = copyarea->mem;
  7505   7511     new_recdes->area_size = copyarea->length;
  7506   7512   
  7507      — -   if (lob_create_flag == LOB_FLAG_EXCLUDE_LOB)
     —   7513 +   if (probe_would_demote_oos != NULL)
     —   7514 +     {
     —   7515 +       scan = heap_attrinfo_transform_to_disk_probe_oos (thread_p, attr_info, old_recdes, &build_record,
     —   7516 + 							lob_create_flag, probe_would_demote_oos);
     —   7517 +     }
     —   7518 +   else if (oos_class_oid != NULL)
     —   7519 +     {
     —   7520 +       scan = heap_attrinfo_transform_to_disk_oos_class (thread_p, attr_info, old_recdes, &build_record,
     —   7521 + 							lob_create_flag, oos_class_oid);
     —   7522 +     }
     —   7523 +   else if (lob_create_flag == LOB_FLAG_EXCLUDE_LOB)
  7508   7524       {
  7509   7525         scan = heap_attrinfo_transform_to_disk_except_lob (thread_p, attr_info, old_recdes, &build_record);
  7510   7526       }
```

The new first if tests probe_would_demote_oos and forwards it to the probe wrapper. The else-if tests oos_class_oid and invokes the final-owner wrapper. The former top-level LOB condition becomes a later else-if, preserving the ordinary except-LOB branch. Both new calls pass the same attr_info and build_record so value state and buffer handling remain centralized. Probe has priority if both pointers are set; intended callers avoid that combination. The shared scan-status check below handles every branch.

<a id="h25"></a>
## H25. Orchestrate probe, early routing and final serialization

[C-125] Head: [src/transaction/locator_sr.c:7708–7770](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7708-L7770). Base: [src/transaction/locator_sr.c:7692–7700](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/transaction/locator_sr.c#L7692-L7700).

```text
  7692   7708       case LC_FLUSH_INSERT:
  7693   7709       case LC_FLUSH_INSERT_PRUNE:
  7694   7710       case LC_FLUSH_INSERT_PRUNE_VERIFY:
  7695      — -       copyarea =
  7696      — - 	locator_allocate_copy_area_by_attr_info (thread_p, attr_info, old_recdes, &new_recdes, -1,
  7697      — - 						 LOB_FLAG_INCLUDE_LOB);
     —   7711 +       if (pruning_type != DB_NOT_PARTITIONED_CLASS)
     —   7712 + 	{
     —   7713 + 	  bool would_demote_oos = false;
     —   7714 + 
     —   7715 + 	  /* An OOS value chain must live in the OOS file of the heap that stores its record, and the
     —   7716 + 	   * target heap of a partitioned write is only known after pruning. Build the record with OOS
     —   7717 + 	   * demotion suppressed, prune with that fully-inline image, and when demotion is needed
     —   7718 + 	   * rebuild the record with its OOS value chains written to the pruned partition's heap
     —   7719 + 	   * (CBRD-27089). */
     —   7720 + 	  copyarea =
     —   7721 + 	    locator_allocate_copy_area_by_attr_info (thread_p, attr_info, old_recdes, &new_recdes, -1,
     —   7722 + 						     LOB_FLAG_INCLUDE_LOB, NULL, &would_demote_oos);
     —   7723 + 	  if (copyarea != NULL && would_demote_oos)
     —   7724 + 	    {
     —   7725 + 	      OID pruned_class_oid;
     —   7726 + 	      HFID pruned_hfid;
     —   7727 + 	      OID superclass_oid;
     —   7728 + 
     —   7729 + 	      COPY_OID (&pruned_class_oid, &class_oid);
     —   7730 + 	      HFID_COPY (&pruned_hfid, &class_hfid);
     —   7731 + 	      OID_SET_NULL (&superclass_oid);
     —   7732 + 
     —   7733 + 	      if (LC_IS_FLUSH_INSERT (operation))
     —   7734 + 		{
     —   7735 + 		  error_code =
     —   7736 + 		    partition_prune_insert (thread_p, &class_oid, &new_recdes, scan_cache, pcontext, pruning_type,
     —   7737 + 					    &pruned_class_oid, &pruned_hfid, &superclass_oid);
     —   7738 + 		}
     —   7739 + 	      else
     —   7740 + 		{
     —   7741 + 		  assert (LC_IS_FLUSH_UPDATE (operation));
     —   7742 + 		  error_code =
     —   7743 + 		    partition_prune_update (thread_p, &class_oid, &new_recdes, pcontext, pruning_type,
     —   7744 + 					    &pruned_class_oid, &pruned_hfid, &superclass_oid);
     —   7745 + 		}
     —   7746 + 
     —   7747 + 	      locator_free_copy_area (copyarea);
     —   7748 + 	      copyarea = NULL;
     —   7749 + 	      new_recdes.data = NULL;
     —   7750 + 	      new_recdes.area_size = 0;
     —   7751 + 
     —   7752 + 	      if (error_code != NO_ERROR)
     —   7753 + 		{
     —   7754 + 		  break;
     —   7755 + 		}
     —   7756 + 
     —   7757 + 	      copyarea =
     —   7758 + 		locator_allocate_copy_area_by_attr_info (thread_p, attr_info, old_recdes, &new_recdes, -1,
     —   7759 + 							 LOB_FLAG_INCLUDE_LOB, &pruned_class_oid, NULL);
     —   7760 + 	    }
     —   7761 + 	}
     —   7762 +       else
     —   7763 + 	{
     —   7764 + 	  copyarea =
     —   7765 + 	    locator_allocate_copy_area_by_attr_info (thread_p, attr_info, old_recdes, &new_recdes, -1,
     —   7766 + 						     LOB_FLAG_INCLUDE_LOB, NULL, NULL);
     —   7767 + 	}
  7698   7768         if (copyarea == NULL)
  7699   7769   	{
  7700   7770   	  error_code = ER_FAILED;
```

The deleted unconditional allocator call becomes a partition-mode branch. The local bool and explanatory comment establish why routing precedes OOS publication. The probe call uses INCLUDE_LOB,NULL,&would_demote_oos. Short-circuiting copyarea != NULL && would_demote_oos avoids reading a failed probe as usable output and avoids a second pass when OOS is unnecessary. Three stack identifiers hold pruning outputs; COPY_OID/HFID_COPY seed them and OID_SET_NULL initializes the superclass. LC_IS_FLUSH_INSERT selects insert pruning; otherwise the assert establishes UPDATE and the update-pruning call is used. Both receive the fully-inline new_recdes. The probe is freed regardless of pruning success, then copyarea and descriptor pointer/capacity are cleared. On pruning failure break exits the operation switch before any final pass. On success the final allocation passes &pruned_class_oid and NULL verdict. The outer else preserves ordinary nonpartitioned allocation with both pointers NULL. The existing copyarea-null check below still handles either failed allocation. Important surrounding lines: UPDATE falls through into this code; lower locator_insert_force/locator_update_force still run; their ordinary pruning is not removed. The early HFID/superclass outputs do not overwrite the outer write context.

### Statement-by-statement reading guide

| Head lines | Meaning |
|---|---|
| 7711–7713 | Enter only for partitioned operation modes; create the addressable false verdict. |
| 7715–7719 | Explain the ownership invariant and ordering requirement in the source comment. |
| 7720–7722 | Pass old/new records and same attribute cache; -1 requests the default area hint; INCLUDE_LOB, NULL, &verdict selects preparation with suppression. |
| 7723–7724 | Only a successful probe that would demote requires early routing plus another transform. |
| 7725–7727 | Declare selected child class, selected heap and root/superclass outputs. |
| 7729 | Initialize class output from the current class as a safe starting value for pruning. |
| 7730 | Initialize heap output from the current heap. |
| 7731 | Initialize superclass to null so missing output cannot be read as a real class. |
| 7733–7737 | INSERT predicate selects insert pruning; capture status and all three output identities. |
| 7739–7744 | The alternative must be UPDATE, established by assert; call its pruning API, which lacks the insert scan-cache parameter. |
| 7747 | Release only the probe byte area, not attr_info or the old row. |
| 7748 | Null the owning copyarea pointer after free. |
| 7749 | Null the RECDES data pointer that referred to the freed bytes. |
| 7750 | Set advertised buffer capacity to zero; length is not reused before a new successful allocation. |
| 7752–7755 | A pruning error exits the operation switch; no final chain publication follows. |
| 7757–7759 | Rebuild using the selected child as OOS owner; NULL verdict restores normal selection and allocator dispatch chooses the final wrapper. |
| 7760–7761 | Close the second-pass condition and partition-mode branch; a false verdict kept the first copy area. |
| 7762–7767 | Nonpartitioned branch uses ordinary transform with both extra pointers null. |
| 7768–7772 | Unchanged shared failure guard translates a null copyarea into ER_FAILED and exits the switch. |

<a id="h26"></a>
## H26. Keep MVCC reevaluation on its existing path

[C-126] Head: [src/transaction/locator_sr.c:13851–13857](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L13851-L13857). Base: [src/transaction/locator_sr.c:13781–13787](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/transaction/locator_sr.c#L13781-L13787).

```text
 13781  13851   	}
 13782  13852         mvcc_reev_data->copyarea =
 13783  13853   	locator_allocate_copy_area_by_attr_info (thread_p, mvcc_reev_data->curr_attrinfo, recdes,
 13784      — - 						 mvcc_reev_data->new_recdes, -1, LOB_FLAG_INCLUDE_LOB);
     —  13854 + 						 mvcc_reev_data->new_recdes, -1, LOB_FLAG_INCLUDE_LOB, NULL, NULL);
 13785  13855         if (mvcc_reev_data->copyarea == NULL)
 13786  13856   	{
 13787  13857   	  ev_res = V_ERROR;
```

The reevaluation copy-area call gains NULL,NULL after INCLUDE_LOB. It therefore selects ordinary transformation, preserving prior behavior and satisfying the new signature. The adjacent null-result handling remains V_ERROR. This hunk is not evidence that all reevaluation paths gained the new two-pass protocol; it only shows the chosen mode at this particular call site.

<a id="h27"></a>
## H27. Expose the adapter’s expanded signature

[C-127] Head: [src/transaction/locator_sr.h:83–90](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.h#L83-L90). Base: [src/transaction/locator_sr.h:83–89](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/transaction/locator_sr.h#L83-L89).

```text
    83     83   					 bool need_locking);
    84     84   extern LC_COPYAREA *locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
    85     85   							     RECDES * old_recdes, RECDES * new_recdes,
    86      — - 							     const int copyarea_length_hint, int lob_create_flag);
     —     86 + 							     const int copyarea_length_hint, int lob_create_flag,
     —     87 + 							     const OID * oos_class_oid, bool * probe_would_demote_oos);
    87     88   extern int locator_other_insert_delete (THREAD_ENTRY * thread_p, HFID * hfid, OID * oid, BTID * btid,
    88     89   					bool btid_dup_key_locked, HFID * newhfid, OID * newoid,
    89     90   					HEAP_CACHE_ATTRINFO * attr_info, HEAP_SCANCACHE * scan_cache, int *force_count,
```

The public internal declaration appends const OID* and bool* in the same order as the definition. Every source caller now supplies an owner override or probe output, or two NULLs. The split line preserves the existing copy-area size hint and LOB arguments. Missing this hunk would leave callers and declaration inconsistent.

<a id="h28"></a>
## H28. Include the string type directly

[C-128] Head: [unit_tests/oos/sql/test_oos_sql_show.cpp:21–27](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L21-L27). Base: [unit_tests/oos/sql/test_oos_sql_show.cpp:21–26](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/unit_tests/oos/sql/test_oos_sql_show.cpp#L21-L26).

```text
    21     21    */
    22     22   
    23     23   #include <algorithm>
     —     24 + #include <string>
    24     25   
    25     26   #include "test_oos_sql_common.hpp"
    26     27   
```

The test now uses std::string for diagnostic names. Including <string> declares that dependency explicitly instead of relying on an incidental transitive include. Existing algorithm and common-test includes remain in their original order.

<a id="h29"></a>
## H29. Copy and normalize the diagnostic name

[C-129] Head: [unit_tests/oos/sql/test_oos_sql_show.cpp:155–192](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L155-L192). Base: [unit_tests/oos/sql/test_oos_sql_show.cpp:154–159](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/unit_tests/oos/sql/test_oos_sql_show.cpp#L154-L159).

```text
   154    155       db_value_clear (&val);
   155    156       return rc;
   156    157     }
     —    158 + 
     —    159 +   static int
     —    160 +   get_string_column (DB_QUERY_RESULT *result, int column, std::string *out_val)
     —    161 +   {
     —    162 +     DB_VALUE val;
     —    163 +     int rc;
     —    164 + 
     —    165 +     db_make_null (&val);
     —    166 +     rc = db_query_get_tuple_value (result, column, &val);
     —    167 +     if (rc == NO_ERROR)
     —    168 +       {
     —    169 + 	const char *str = db_get_string (&val);
     —    170 + 	if (str == nullptr)
     —    171 + 	  {
     —    172 + 	    rc = ER_FAILED;
     —    173 + 	  }
     —    174 + 	else
     —    175 + 	  {
     —    176 + 	    *out_val = str;
     —    177 + 	  }
     —    178 +       }
     —    179 + 
     —    180 +     db_value_clear (&val);
     —    181 +     return rc;
     —    182 +   }
     —    183 + 
     —    184 +   static std::string
     —    185 +   unqualified_table_name (const std::string &table_name)
     —    186 +   {
     —    187 +     std::string::size_type separator = table_name.rfind ('.');
     —    188 +     return separator == std::string::npos ? table_name : table_name.substr (separator + 1);
     —    189 +   }
   157    190   }
   158    191   
   159    192   class OosSqlShow : public ::testing::Test
```

get_string_column declares a DB_VALUE and status, initializes the value to null, fetches the requested column, and only reads a string on NO_ERROR. A null string produces ER_FAILED; a valid string is copied into the caller’s std::string before db_value_clear releases temporary storage. The unconditional clear and returned rc preserve cleanup/status for this helper. unqualified_table_name uses rfind to locate the last dot; npos returns the original name, otherwise substr(separator+1) returns the unqualified suffix. It is sufficient for the simple fixture names and is not a general SQL identifier parser. The helpers are in the existing anonymous namespace.

<a id="h30"></a>
## H30. Check value and all three heap owners

[C-130] Head: [unit_tests/oos/sql/test_oos_sql_show.cpp:384–458](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L384-L458). Base: [unit_tests/oos/sql/test_oos_sql_show.cpp:351–356](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/unit_tests/oos/sql/test_oos_sql_show.cpp#L351-L356).

```text
   351    384     db_query_end (result);
   352    385   }
   353    386   
     —    387 + TEST_F (OosSqlShow, PartitionedForceOutlineStoresOosInPrunedHeap)
     —    388 + {
     —    389 +   int rc = exec_sql ("CREATE TABLE t_oos_show_part ("
     —    390 + 		     "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
     —    391 + 		     "PARTITION BY RANGE (id) ("
     —    392 + 		     "PARTITION p0 VALUES LESS THAN (10), "
     —    393 + 		     "PARTITION p1 VALUES LESS THAN MAXVALUE)");
     —    394 +   ASSERT_GE (rc, 0);
     —    395 +   rc = exec_sql ("INSERT INTO t_oos_show_part VALUES (1, REPEAT(X'EE', 64))");
     —    396 +   ASSERT_GE (rc, 0);
     —    397 +   db_commit_transaction ();
     —    398 + 
     —    399 +   int value_matches = 0;
     —    400 +   rc = fetch_single_int ("SELECT data_col = CAST(REPEAT(X'EE', 64) AS BIT VARYING) "
     —    401 + 			 "FROM t_oos_show_part WHERE id = 1", &value_matches);
     —    402 +   ASSERT_EQ (rc, NO_ERROR);
     —    403 +   EXPECT_EQ (value_matches, 1);
     —    404 + 
     —    405 +   DB_QUERY_RESULT *result = nullptr;
     —    406 +   rc = show_heap_oos_query ("SHOW ALL HEAP OOS OF t_oos_show_part", &result);
     —    407 +   ASSERT_EQ (rc, NO_ERROR);
     —    408 +   ASSERT_NE (result, nullptr);
     —    409 + 
     —    410 +   bool saw_root = false;
     —    411 +   bool saw_p0 = false;
     —    412 +   bool saw_p1 = false;
     —    413 +   do
     —    414 +     {
     —    415 +       std::string table_name;
     —    416 +       int has_oos = -1;
     —    417 +       int num_recs = -1;
     —    418 + 
     —    419 +       rc = get_string_column (result, COL_TABLE_NAME, &table_name);
     —    420 +       ASSERT_EQ (rc, NO_ERROR);
     —    421 +       rc = get_int_column (result, COL_HAS_OOS_FILE, &has_oos);
     —    422 +       ASSERT_EQ (rc, NO_ERROR);
     —    423 +       rc = get_int_column (result, COL_OOS_NUM_RECS, &num_recs);
     —    424 +       ASSERT_EQ (rc, NO_ERROR);
     —    425 + 
     —    426 +       table_name = unqualified_table_name (table_name);
     —    427 +       if (table_name == "t_oos_show_part")
     —    428 + 	{
     —    429 + 	  saw_root = true;
     —    430 + 	  EXPECT_EQ (has_oos, 0);
     —    431 + 	  EXPECT_EQ (num_recs, 0);
     —    432 + 	}
     —    433 +       else if (table_name == "t_oos_show_part__p__p0")
     —    434 + 	{
     —    435 + 	  saw_p0 = true;
     —    436 + 	  EXPECT_EQ (has_oos, 1);
     —    437 + 	  EXPECT_EQ (num_recs, 1);
     —    438 + 	}
     —    439 +       else if (table_name == "t_oos_show_part__p__p1")
     —    440 + 	{
     —    441 + 	  saw_p1 = true;
     —    442 + 	  EXPECT_EQ (has_oos, 0);
     —    443 + 	  EXPECT_EQ (num_recs, 0);
     —    444 + 	}
     —    445 +     }
     —    446 +   while ((rc = db_query_next_tuple (result)) == DB_CURSOR_SUCCESS);
     —    447 + 
     —    448 +   EXPECT_EQ (rc, DB_CURSOR_END);
     —    449 +   EXPECT_TRUE (saw_root);
     —    450 +   EXPECT_TRUE (saw_p0);
     —    451 +   EXPECT_TRUE (saw_p1);
     —    452 + 
     —    453 +   db_query_end (result);
     —    454 + }
     —    455 + 
   354    456   int
   355    457   main (int argc, char **argv)
   356    458   {
```

The TEST_F declaration uses existing SetUp/TearDown table cleanup. Adjacent SQL string literals form one CREATE statement; FORCE_OUTLINE plus a 64-byte value exercises demotion below the normal threshold. ASSERT_GE checks successful SQL execution, and db_commit_transaction makes the write visible to later queries without asserting its return. The equality SELECT fills value_matches; ASSERT_EQ validates fetching and EXPECT_EQ checks true. The SHOW helper positions the first tuple, so do begins by inspecting that row. Three saw flags start false; per-row sentinels -1 prevent unnoticed default success. get_string_column and two get_int_column calls each have fatal status checks. Name normalization allows an optional schema prefix. Root expects zero file/records; p0 expects one file/record; p1 expects zero. Each matched branch marks its saw flag. db_query_next_tuple advances until not-success; DB_CURSOR_END must then be the reason for termination. All three saw flags must be true, and db_query_end releases the result on normal completion. The test does not reject additional unknown names, assert exact total row count, execute UPDATE or run a SERVER_MODE vacuum cycle. Its OOS_NUM_RECS expectation is for a small single-chunk value, not every row size.

### Statement-by-statement reading guide

| Head lines | Meaning |
|---|---|
| 387–388 | Register the test with the existing table-cleanup fixture. |
| 389–393 | Concatenate CREATE statement fragments: fixed id, forced variable value, range expression and both child bounds. |
| 394 | Require a nonnegative SQL result before using the table. |
| 395–396 | Insert the below-threshold forced value in p0 and require success. |
| 397 | Commit; this line does not check the commit return value. |
| 399 | Start equality output at false so missing assignment cannot look like true. |
| 400–401 | Fetch the boolean SQL equality as an integer for the id=1 row. |
| 402–403 | Require successful fetch, then nonfatally expect equality 1. |
| 405 | Initialize the query-result handle to null. |
| 406–408 | Request all heap OOS rows; require success and a real result handle. |
| 410–412 | Track whether root and both child rows were actually seen. |
| 413–417 | Inspect the already-positioned first tuple; initialize a string and sentinel numeric outputs per iteration. |
| 419–420 | Read and validate the name before branching on it. |
| 421–422 | Read the heap OOS-file indicator, not the row-level HAS_OOS bit. |
| 423–424 | Read OOS chunk-record count and require a valid typed result. |
| 426 | Remove a possible schema prefix from the simple fixture name. |
| 427–432 | Recognize root, record its presence, and expect neither file nor OOS records. |
| 433–438 | Recognize p0, record its presence, and expect exactly one file indicator and one chunk record. |
| 439–444 | Recognize p1, record its presence, and expect no OOS allocation. |
| 445–446 | Advance the cursor only after examining the current row; keep looping on SUCCESS. |
| 448 | Check that iteration stopped at END rather than a cursor error. |
| 449–451 | Require all three named rows; no order assumption is needed. |
| 453–454 | Close the query result and finish the normal test path. |

## Hunk checkpoint

Explain H10 without using the word “flag” ambiguously. Then trace H25 for both a successful forced-outline INSERT and a probe that reports false. Finally, walk H30 from the first tuple through cursor termination and explain the lifetime of each temporary value.
