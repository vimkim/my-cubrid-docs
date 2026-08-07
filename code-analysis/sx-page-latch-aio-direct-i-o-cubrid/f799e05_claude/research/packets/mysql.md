# InnoDB SX Latch Research Packet

MySQL/InnoDB SX (Shared-eXclusive) latch semantics and page buffer management comparison for CUBRID.

Repository: `/home/vimkim/gh/mysql/mysql-server` (pinned HEAD 06a5c1c99c37)

---

## 1. Block Latch Modes at Page Fix Time

**Location:** `storage/innobase/buf/buf0buf.cc:4149–4180` (function `Buf_fetch<T>::mtr_add_page`)

Latch acquisition at page fix time via switch statement on `m_rw_latch`:

```c
// Lines 4149-4180
template <typename T>
void Buf_fetch<T>::mtr_add_page(buf_block_t *block) {
  mtr_memo_type_t fix_type;
  ut::Location loc{m_file, m_line};

  switch (m_rw_latch) {
    case RW_NO_LATCH:
      fix_type = MTR_MEMO_BUF_FIX;
      break;
    case RW_S_LATCH:
      rw_lock_s_lock_gen(&block->lock, 0, loc);
      fix_type = MTR_MEMO_PAGE_S_FIX;
      break;
    case RW_SX_LATCH:
      rw_lock_sx_lock_gen(&block->lock, 0, loc);
      fix_type = MTR_MEMO_PAGE_SX_FIX;
      break;
    default:
      ut_ad(m_rw_latch == RW_X_LATCH);
      rw_lock_x_lock_gen(&block->lock, 0, loc);
      fix_type = MTR_MEMO_PAGE_X_FIX;
      break;
  }
  mtr_memo_push(m_mtr, block, fix_type);
}
```

**Behavior:** Each mode acquires the corresponding latch on `block->lock` at fix time. The SX latch is acquired using `rw_lock_sx_lock_gen()` and tracked with `MTR_MEMO_PAGE_SX_FIX` memo type.

---

## 2. SX Lock Semantics and Compatibility

**Lock Compatibility Matrix:** `storage/innobase/sync/sync0rw.cc:93–97`

```
 LOCK COMPATIBILITY MATRIX
    S SX  X
 S  +  +  -
 SX +  -  -
 X  -  -  -
```

**SX Lock Definition:** `storage/innobase/include/sync0rw.h:200–207`

```c
// Lines 200-207
/** NOTE! Use the corresponding macro, not directly this function! Lock an
rw-lock in SX mode for the current thread. If the rw-lock is locked
in exclusive mode, or there is an exclusive lock request waiting,
the function spins a preset time (controlled by SYNC_SPIN_ROUNDS), waiting
for the lock, before suspending the thread. If the same thread has an x-lock
on the rw-lock, locking succeed, with the following exception: if pass != 0,
only a single sx-lock may be taken on the lock. NOTE: If the same thread has
an s-lock, locking does not succeed!
```

**Behavior:** SX is compatible with S, but **NOT** compatible with SX or X. Multiple S locks can coexist with one SX lock. An SX holder blocks other SX and all X requests. The lock word uses `X_LOCK_HALF_DECR = 0x10000000` for SX decrement, allowing both S and SX to coexist in the same word state.

---

## 3. Flush Acquires SX Lock (Non-Blocking, Then Blocking)

**Location:** `storage/innobase/buf/buf0flu.cc:1096–1146`

```c
// Lines 1096-1102: Initial nowait SX lock attempt
if (flush_type != BUF_FLUSH_LIST) {
  flush = rw_lock_sx_lock_nowait(rw_lock, BUF_IO_WRITE, UT_LOCATION_HERE);
} else {
  /* Will SX lock later */
  flush = true;
}

// Lines 1138-1147: BUF_FLUSH_LIST fallback path
if (flush_type == BUF_FLUSH_LIST && is_uncompressed &&
    !rw_lock_sx_lock_nowait(rw_lock, BUF_IO_WRITE, UT_LOCATION_HERE)) {
  if (!fsp_is_system_temporary(bpage->id.space()) && dblwr::is_enabled()) {
    dblwr::force_flush(flush_type, buf_pool_index(buf_pool));
  } else {
    buf_flush_sync_datafiles();
  }
  rw_lock_sx_lock_gen(rw_lock, BUF_IO_WRITE, UT_LOCATION_HERE);
}
```

**Behavior:** 
- For `BUF_FLUSH_SINGLE_PAGE` and `BUF_FLUSH_LRU`: Try non-blocking SX lock. If it fails, page is deferred.
- For `BUF_FLUSH_LIST`: Mark for later flush. On dequeue, try non-blocking SX. If that fails (reader holding S lock or another writer holding SX), **force-flush doublewrite buffer first**, then **acquire blocking SX lock** (line 1146).

This indicates InnoDB accepts a brief stall on writers to drain the doublewrite buffer under contention.

---

## 4. Write Completion Releases SX Lock

**Locations:** 
- `storage/innobase/buf/buf0buf.cc:5559–5561` (after stale-page write)
- `storage/innobase/buf/buf0buf.cc:5965–5973` (main I/O completion path)

```c
// Lines 5559-5561: Stale page write completion
if (owns_sx_lock) {
  rw_lock_sx_unlock_gen(&((buf_block_t *)bpage)->lock, BUF_IO_WRITE);
}

// Lines 5965-5973: Normal write completion in buf_page_io_complete
case BUF_IO_WRITE:
  buf_flush_write_complete(bpage);
  if (uncompressed) {
    rw_lock_sx_unlock_gen(&((buf_block_t *)bpage)->lock, BUF_IO_WRITE);
  }
  buf_pool->stat.n_pages_written.fetch_add(1);
```

**Behavior:** After write I/O completes (signaled by `buf_page_io_complete`), the SX lock is released via `rw_lock_sx_unlock_gen()`. For compressed pages, no lock is released (they use IO_FIX synchronization instead).

---

## 5. Page Copy During Flush (Doublewrite Buffer)

**Doublewrite Buffer Copy:** `storage/innobase/include/buf0dblwr.h:87–98`

```c
// Lines 85-98: Buffer::append method
/** Add the contents of ptr up to n_bytes to the buffer.
@return false if it won't fit. Nothing is copied if it won't fit. */
bool append(const void *ptr, size_t n_bytes) noexcept {
  ut_a(m_next >= m_ptr && m_next <= m_ptr + m_n_bytes);

  if (m_next + m_phy_size > m_ptr + m_n_bytes) {
    return false;
  }

  memcpy(m_next, ptr, n_bytes);  // <-- COPY HAPPENS HERE
  m_next += m_phy_size;
  return true;
}
```

**Page Prepare Path:** `storage/innobase/buf/buf0dblwr.cc:1370–1405` (function `Double_write::prepare`)

```c
// Lines 1398-1403: For uncompressed pages
*ptr = reinterpret_cast<buf_block_t *>(
    const_cast<buf_page_t *>(bpage))->frame;
UNIV_MEM_ASSERT_RW(*ptr, bpage->size.logical());
*len = bpage->size.logical();
```

**Doublewrite Write Flow:** `storage/innobase/buf/buf0dblwr.cc:2265–2295` (function `Double_write::write_dblwr_pages`)

```c
// Lines 2278-2284
batch_segment->start(this);
batch_segment->write(m_buffer);  // <-- Copies pages into dblwr buffer
m_bytes_written += m_buffer.size();
m_buffer.clear();
```

**Behavior:** 
1. `Double_write::prepare()` extracts a pointer to the live page frame (`block->frame` or `bpage->zip.data`).
2. `Buffer::append()` **copies the page data into a pre-allocated doublewrite buffer** (line 94: `memcpy`).
3. Then `write_to_datafile()` writes the doublewrite buffer, **not** the original page frame.
4. After doublewrite completes, the datafile write proceeds with the original frame pointer (SX lock held).

**Implication:** InnoDB **does NOT** have copy-free flush when doublewrite is enabled. The page is copied to the doublewrite buffer, then written to the doublewrite file, then the datafile write uses the original frame (now protected by SX latch for consistency).

---

## 6. B-Tree Read-Then-Modify Discipline (No S→X Upgrade)

### Index Lock Acquisition by BTR_MODIFY_TREE

**Location:** `storage/innobase/btr/btr0cur.cc:815–832` (function `btr_cur_search_to_nth_level`, within the switch on `latch_mode`)

```c
// Lines 815-832
case BTR_MODIFY_TREE:
  /* Most of delete-intended operations are purging.
  Free blocks and read IO bandwidth should be prior
  for them, when the history list is glowing huge. */
  if (lock_intention == BTR_INTENTION_DELETE &&
      trx_sys->rseg_history_len.load() > BTR_CUR_FINE_HISTORY_LENGTH &&
      buf_get_n_pending_read_ios()) {
    mtr_x_lock(dict_index_get_lock(index), mtr, UT_LOCATION_HERE);
  } else if (dict_index_is_spatial(index) &&
             lock_intention <= BTR_INTENTION_BOTH) {
    /* X lock the if there is possibility of
    pessimistic delete on spatial index. As we could
    lock upward for the tree */
    mtr_x_lock(dict_index_get_lock(index), mtr, UT_LOCATION_HERE);
  } else {
    mtr_sx_lock(dict_index_get_lock(index), mtr, UT_LOCATION_HERE);  // <-- SX
  }
  upper_rw_latch = RW_X_LATCH;
  break;
```

**Assertion:** `storage/innobase/btr/btr0cur.cc:223–225` (function `btr_cur_latch_leaves`)

```c
case BTR_MODIFY_TREE:
  /* It is exclusive for other operations which calls
  btr_page_set_prev() */
  ut_ad(mtr_memo_contains_flagged(mtr, dict_index_get_lock(cursor->index),
                                  MTR_MEMO_X_LOCK | MTR_MEMO_SX_LOCK) ||
        cursor->index->table->is_intrinsic());
```

**Behavior:** BTR_MODIFY_TREE **acquires the index lock in SX mode** (line 831) for the common case (non-delete, non-spatial). The leaf and non-leaf pages are then latched in RW_X_LATCH mode (lines 237-238, 252-253).

### Optimistic vs. Pessimistic Insert Retry

**Location:** `storage/innobase/row/row0ins.cc:2585–2596`

```c
// Lines 2585-2596
err = btr_cur_optimistic_insert(flags, cursor, &offsets, &offsets_heap,
                                entry, &insert_rec, &big_rec, thr, &mtr);

if (err == DB_FAIL) {
  err = btr_cur_pessimistic_insert(flags, cursor, &offsets, &offsets_heap,
                                   entry, &insert_rec, &big_rec, thr, &mtr);

  if (index->table->is_intrinsic() && err == DB_SUCCESS) {
    row_ins_temp_prebuilt_tree_modified(index->table);
  }
}
```

**Behavior:** 
- **Optimistic path:** Called with `BTR_MODIFY_LEAF`, acquires RW_X_LATCH on leaf only. If no space or split needed, returns `DB_FAIL`.
- **Pessimistic path:** Called with `BTR_MODIFY_TREE`, acquires index SX lock + RW_X_LATCH on all affected pages. Handles splits/merges.
- **No in-place S→X upgrade:** InnoDB does NOT upgrade a held S latch to X. Instead, it abandons the optimistic path and **restarts the entire search under BTR_MODIFY_TREE**, acquiring SX on the index upfront.

### Lock Upgrade API Check

**Result:** No `rw_lock_x_lock_upgrade()` or similar function exists in `storage/innobase/include/sync0rw.h` or `storage/innobase/sync/sync0rw.cc`. The codebase contains no S→X upgrade mechanism.

---

## Unknowns & Surprises

### 1. Nowait SX Lock Not Implemented for `buf_page_get_known_nowait()`

**Location:** `storage/innobase/buf/buf0buf.cc:4612–4665`

```c
// Line 4664
default:
  ut_error; /* RW_SX_LATCH is not implemented yet */
```

The non-blocking variant `buf_page_get_known_nowait()` **does NOT support RW_SX_LATCH**. Only S and X latches are implemented for the nowait path. This suggests SX latch was added later and may not be fully integrated into all code paths.

### 2. Doublewrite Force Flush Under Contention

The logic at `buf0flu.cc:1138–1146` (force doublewrite flush if SX lock cannot be acquired) is unusual. It suggests InnoDB prioritizes draining the doublewrite buffer under contention over stalling the flusher. This differs from a pure blocking-wait approach.

### 3. Index SX vs. X Lock Decision Based on Operation Intent

The choice between X and SX lock on the index (lines 819–831) depends on:
- Delete-heavy workloads with large history list → X lock
- Spatial index with potential pessimistic delete → X lock
- General insert/update → SX lock

This suggests SX is the "common path" and X is used only when strict mutual exclusion is necessary.

### 4. Compressed Pages Do Not Use SX (IO_FIX Only)

At `buf0buf.cc:5972`, SX unlock only happens for `uncompressed` pages. Compressed pages use `IO_FIX` synchronization instead, implying SX is only for uncompressed buffer blocks.

---

## Summary Table

| Aspect | InnoDB Behavior |
|--------|-----------------|
| **Page Fix Latch Modes** | RW_NO_LATCH, RW_S_LATCH, RW_SX_LATCH, RW_X_LATCH all supported |
| **SX Compatibility** | S + S = yes; S + SX = yes; SX + SX = no; all X = no |
| **Flush SX Acquisition** | Non-blocking first (except BUF_FLUSH_LIST); blocking with doublewrite drain on contention |
| **Write I/O Release** | SX released after write I/O completion (uncompressed only) |
| **Page Copy in Flush** | **YES** – copied to doublewrite buffer before datafile write |
| **B-tree Upgrade** | **NO S→X upgrade** – restart search under BTR_MODIFY_TREE with index SX |
| **Optimistic Fallback** | DB_FAIL → pessimistic insert with full tree lock |

---

## References

- Lock word semantics: `storage/innobase/sync/sync0rw.cc:61–91`
- MTR memo types: `storage/innobase/include/mtr0mtr.h` (MTR_MEMO_PAGE_SX_FIX, etc.)
- Buffer pool latch workflow: `storage/innobase/buf/buf0buf.cc:4070–4180`
- Doublewrite architecture: `storage/innobase/include/buf0dblwr.h`, `storage/innobase/buf/buf0dblwr.cc`
- B-tree latch ordering: `storage/innobase/btr/btr0cur.cc:173–450`
