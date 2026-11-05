export const title = 'Heap batch allocation reserves a sector while vacuum holds an empty page it cannot unlink';

const allocator = (v) => {
  const after = v.reservations > 0 ? ', sector reserved' : '';
  return {
    start: 'Bestspace missed P',
    fixFile: 'Holds heap header',
    user: `Allocating user pages${after}`,
    next: `Allocating user pages${after}`,
    probe: `Full sector needs a full-table slot${after}`,
    table: `Full table full, allocating a table page${after}`,
    expandUser: 'No free bit for a user page',
    expandTable: 'No free bit for the table page',
    releaseFile: `Linking new pages${after}`,
    link: `Linking new pages${after}`,
    done: `Batch done${after}`,
  }[v.alloc];
};

const page = (v) => {
  if (v.pAlloc === 'free') return 'File bit free';
  if (v.pAlloc === 'postponed') return 'Deallocation postponed';
  if (v.pAlloc === 'unlinked') return 'Unlinked, still allocated';
  if (v.pRec === 'deleted') return 'Last record awaits vacuum';
  if (v.pRec === 'new') return 'Holds a new record';
  if (v.vac === 'holdP') return 'Empty, vacuum holds P';
  if (v.vac === 'waitHeader') return 'Empty, vacuum waits for heap header';
  if (v.vac === 'gates' || v.vac === 'unlink') return 'Empty, vacuum holds heap header';
  return 'Empty, back in bestspace';
};

export const state = (v) => ({ Allocator: allocator(v), 'Page P': page(v) });

export const step = (action, from, to) => ({
  AllocFixHeapHeader: 'allocator takes the heap header',
  AllocFixFileHeader: 'allocator takes the file header',
  AllocUserPage: to.alloc === 'expandUser' ? 'no free bit is left' :
    to.alloc === 'probe' ? 'the user page fills its sector' : 'a user page takes a free bit',
  AllocProbeFullTable: to.alloc === 'table' ? 'the full table has no slot' : 'the full table takes the sector',
  AllocTablePage: to.alloc === 'expandTable' ? 'no free bit is left' : 'a table page takes a free bit',
  AllocNext: 'the next user page starts',
  AllocReleaseFileHeader: 'allocator releases the file header',
  AllocLinkCommitRelease: 'allocator commits and releases the heap header',
  Reserve: 'a sector is reserved',
  VacEmptyPage: 'vacuum removes the last record',
  VacFixHeapHeader: to.vac === 'gates' ? 'vacuum takes the heap header' :
    to.vac === 'waitHeader' ? 'vacuum unfixes P and waits' : 'vacuum gives up at once',
  VacGetHeapHeader: 'vacuum gets the heap header and refixes P',
  OtherInsertIntoP: 'another insert uses P',
  VacGates: to.vac === 'unlink' ? 'the rechecks pass' : 'a recheck fails',
  VacGiveUp: 'vacuum returns P to bestspace',
  VacUnlink: 'vacuum unlinks P',
  VacFileDealloc: 'file_dealloc postpones the bit',
  VacCommit: 'vacuum commits and the postpone frees the bit',
  VacReleaseHeader: 'vacuum releases the heap header',
  VacLatePostpone: 'the late postpone frees the bit',
  Next: null,
}[action] ?? action);
