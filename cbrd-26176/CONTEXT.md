# CUBRID Heap Bestspace

This context names the heap-local concepts used to select reusable pages for record insertion without treating free-space hints as authoritative state.

## Language

**Bestspace**:
A heap-local, non-authoritative set of free-space hints used when selecting an insertion page. A hinted page is still validated against its actual state before use.
_Avoid_: free-space map, authoritative free-space index

**Bestspace shard**:
A concurrency partition of one heap's bestspace entries. It is not a storage or ownership partition of the heap's pages.
_Avoid_: heap shard, data shard, storage shard

**Allocating**:
A transient bestspace-shard state indicating that one worker owns replenishment of that shard's page candidates. It does not mean that other workers wait on that shard immediately.
_Avoid_: allocation wait, insufficient shard

**Candidate**:
A heap page whose reclaimed free space has been offered to bestspace for later validation and possible admission to a shard. Being queued as a candidate does not mean the page is already tracked by a shard.
_Avoid_: registered page, free page
