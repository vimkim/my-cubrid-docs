---------------------- MODULE DevelopHeapReservation ----------------------
(***************************************************************************)
(* One heap batch allocation (heap_alloc_new_pages) races one vacuum      *)
(* worker that empties and tries to remove an existing heap page P.       *)
(* Source: CUBRID develop 2362424f25bcebd1bd9733bddd59a993e2852ac5.       *)
(* README.md maps every action to its source range.                       *)
(***************************************************************************)
EXTENDS Naturals, Sequences

CONSTANTS
  Fixture,                   \* "partial": P is in S0, the only partial sector. "full": P is in full sector S1.
  InitFree,                  \* free bits in S0 when the batch starts; 0 means S0 does not exist
  Batch,                     \* pages one heap_alloc_new_pages call requests
  FullRoom,                  \* empty full-table slots when the batch starts
  SectorPages,               \* DISK_SECTOR_NPAGES
  TablePageSlots,            \* full-table entries one new table page holds
  BatchHoldsHeapHeader,      \* source fact: heap header WRITE spans file_alloc_multiple
  PostponeBeforeHeaderUnfix  \* source fact: vacuum runs the RVFL_DEALLOC postpone before it unfixes the heap header

ASSUME /\ Fixture \in {"partial", "full"}
       /\ InitFree \in Nat /\ (Fixture = "partial" => InitFree >= 1)
       /\ Batch \in 1..4 /\ FullRoom \in Nat
       /\ SectorPages \in Nat /\ SectorPages > Batch
       /\ TablePageSlots \in Nat /\ TablePageSlots >= 2
       /\ BatchHoldsHeapHeader \in BOOLEAN /\ PostponeBeforeHeaderUnfix \in BOOLEAN

PSector == IF Fixture = "partial" THEN "S0" ELSE "S1"
NewSector == <<"N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8">>

VARIABLES
  parts,       \* partial-sector table in allocation order: <<[id, free]>>
  fullRoom,    \* empty full-table slots
  nextId,      \* next reserved sector number
  reservations,
  userNew, tableNew,
  alloc,       \* allocator program counter
  iter,        \* user pages already allocated in this batch
  hdr,         \* heap header WRITE owner
  fhdr,        \* file header WRITE owner
  pRec,        \* P's records: "deleted" (last record awaits vacuum), "none" (physically empty), "new"
  pAlloc,      \* P's ownership: "linked", "unlinked", "postponed", "free"
  vac,         \* vacuum program counter
  freedFirst,  \* P's file bit was free before the allocator fixed the heap header
  reserveLog   \* one snapshot per sector reservation

vars == <<parts, fullRoom, nextId, reservations, userNew, tableNew, alloc, iter,
          hdr, fhdr, pRec, pAlloc, vac, freedFirst, reserveLog>>

RECURSIVE SumFree(_)
SumFree(s) == IF s = <<>> THEN 0 ELSE Head(s).free + SumFree(Tail(s))
NFree == SumFree(parts)

PhysicallyEmpty == pRec = "none" /\ pAlloc # "free"
CanUnlinkNow == pRec = "none" /\ pAlloc = "linked" /\ hdr # "alloc"
UnlinkedNotFree == pAlloc \in {"unlinked", "postponed"}

Snapshot(recursive) ==
  [recursive |-> recursive, nfree |-> NFree, physEmpty |-> PhysicallyEmpty,
   canUnlink |-> CanUnlinkNow, unlinkedNotFree |-> UnlinkedNotFree,
   pFree |-> pAlloc = "free", freedFirst |-> freedFirst]

Init ==
  /\ parts = IF InitFree > 0 THEN <<[id |-> "S0", free |-> InitFree]>> ELSE <<>>
  /\ fullRoom = FullRoom /\ nextId = 1 /\ reservations = 0
  /\ userNew = 0 /\ tableNew = 0
  /\ alloc = "start" /\ iter = 0
  /\ hdr = "none" /\ fhdr = "none"
  /\ pRec = "deleted" /\ pAlloc = "linked" /\ vac = "idle"
  /\ freedFirst = FALSE /\ reserveLog = <<>>

vacVars == <<pRec, pAlloc, vac>>

(* heap_alloc_new_pages: ordered fix of the heap header WRITE, then sysop start *)
AllocFixHeapHeader ==
  /\ alloc = "start"
  /\ IF BatchHoldsHeapHeader THEN hdr = "none" /\ hdr' = "alloc" ELSE UNCHANGED hdr
  /\ freedFirst' = (pAlloc = "free")
  /\ alloc' = "fixFile"
  /\ UNCHANGED <<parts, fullRoom, nextId, reservations, userNew, tableNew, iter, fhdr,
                 vacVars, reserveLog>>

(* file_alloc_multiple: file header WRITE for the whole batch *)
AllocFixFileHeader ==
  /\ alloc = "fixFile" /\ fhdr = "none"
  /\ fhdr' = "alloc" /\ alloc' = "user"
  /\ UNCHANGED <<parts, fullRoom, nextId, reservations, userNew, tableNew, iter, hdr,
                 vacVars, freedFirst, reserveLog>>

(* file_perm_expand: disk_reserve_sectors, new sectors appended to the partial table *)
Reserve(from, to) ==
  /\ alloc = from /\ NFree = 0
  /\ reserveLog' = Append(reserveLog, Snapshot(from = "expandTable"))
  /\ parts' = Append(parts, [id |-> NewSector[nextId], free |-> SectorPages])
  /\ nextId' = nextId + 1 /\ reservations' = reservations + 1
  /\ alloc' = to
  /\ UNCHANGED <<fullRoom, userNew, tableNew, iter, hdr, fhdr, vacVars, freedFirst>>

(* file_perm_alloc(FILE_ALLOC_USER_PAGE): expand at n_page_free == 0, else take a bit in the first partial sector *)
AllocUserPage ==
  /\ alloc = "user"
  /\ IF NFree = 0
       THEN /\ alloc' = "expandUser"
            /\ UNCHANGED <<parts, userNew>>
       ELSE LET h == Head(parts) IN
            /\ userNew' = userNew + 1
            /\ IF h.free = 1
                 THEN parts' = Tail(parts) /\ alloc' = "probe"
                 ELSE parts' = <<[h EXCEPT !.free = @ - 1]>> \o Tail(parts) /\ alloc' = "next"
  /\ UNCHANGED <<fullRoom, nextId, reservations, tableNew, iter, hdr, fhdr, vacVars,
                 freedFirst, reserveLog>>

(* file_table_add_full_sector: use a free full-table slot, else recurse for a table page *)
AllocProbeFullTable ==
  /\ alloc = "probe"
  /\ IF fullRoom > 0
       THEN fullRoom' = fullRoom - 1 /\ alloc' = "next"
       ELSE UNCHANGED fullRoom /\ alloc' = "table"
  /\ UNCHANGED <<parts, nextId, reservations, userNew, tableNew, iter, hdr, fhdr, vacVars,
                 freedFirst, reserveLog>>

(* file_perm_alloc(FILE_ALLOC_TABLE_PAGE_FULL_SECTOR): expand at n_page_free == 0, take a bit,
   append the table page, move its sector if full, then insert the pending full sector *)
AllocTablePage ==
  /\ alloc = "table"
  /\ IF NFree = 0
       THEN /\ alloc' = "expandTable"
            /\ UNCHANGED <<parts, fullRoom, tableNew>>
       ELSE LET h == Head(parts) IN
            /\ tableNew' = tableNew + 1
            /\ parts' = IF h.free = 1 THEN Tail(parts)
                        ELSE <<[h EXCEPT !.free = @ - 1]>> \o Tail(parts)
            /\ fullRoom' = fullRoom + TablePageSlots - (IF h.free = 1 THEN 1 ELSE 0) - 1
            /\ alloc' = "next"
  /\ UNCHANGED <<nextId, reservations, userNew, iter, hdr, fhdr, vacVars, freedFirst, reserveLog>>

AllocNext ==
  /\ alloc = "next"
  /\ iter' = iter + 1
  /\ alloc' = IF iter + 1 < Batch THEN "user" ELSE "releaseFile"
  /\ UNCHANGED <<parts, fullRoom, nextId, reservations, userNew, tableNew, hdr, fhdr, vacVars,
                 freedFirst, reserveLog>>

(* file_alloc_multiple exit: sysop commit, unfix the file header *)
AllocReleaseFileHeader ==
  /\ alloc = "releaseFile"
  /\ fhdr' = "none" /\ alloc' = "link"
  /\ UNCHANGED <<parts, fullRoom, nextId, reservations, userNew, tableNew, iter, hdr, vacVars,
                 freedFirst, reserveLog>>

(* heap_alloc_new_pages: chain links, header stats, sysop commit, then unfix the heap header *)
AllocLinkCommitRelease ==
  /\ alloc = "link"
  /\ hdr' = IF hdr = "alloc" THEN "none" ELSE hdr
  /\ alloc' = "done"
  /\ UNCHANGED <<parts, fullRoom, nextId, reservations, userNew, tableNew, iter, fhdr, vacVars,
                 freedFirst, reserveLog>>

allocOnly == <<parts, fullRoom, nextId, reservations, userNew, tableNew, alloc, iter,
               freedFirst, reserveLog>>

(* vacuum_heap_page: P WRITE, the last record passes the MVCC and reusable gates and is removed *)
VacEmptyPage ==
  /\ vac = "idle" /\ pRec = "deleted"
  /\ pRec' = "none" /\ vac' = "holdP"
  /\ UNCHANGED <<allocOnly, hdr, fhdr, pAlloc>>

(* heap_remove_page_on_vacuum: ordered fix of the heap header while P is held.
   A free header is fixed at once. A held header either fails (zero wait) or makes
   vacuum unfix P and wait. *)
VacFixHeapHeader ==
  /\ vac = "holdP"
  /\ \/ hdr = "none" /\ hdr' = "vac" /\ vac' = "gates"
     \/ hdr # "none" /\ vac' = "giveUp" /\ UNCHANGED hdr
     \/ hdr # "none" /\ vac' = "waitHeader" /\ UNCHANGED hdr
  /\ UNCHANGED <<allocOnly, fhdr, pRec, pAlloc>>

VacGetHeapHeader ==
  /\ vac = "waitHeader" /\ hdr = "none"
  /\ hdr' = "vac" /\ vac' = "gates"
  /\ UNCHANGED <<allocOnly, fhdr, pRec, pAlloc>>

(* Another insert lands in P while vacuum has P unfixed, or after P returned to bestspace *)
OtherInsertIntoP ==
  /\ vac \in {"waitHeader", "kept"} /\ pRec = "none" /\ pAlloc = "linked"
  /\ pRec' = "new"
  /\ UNCHANGED <<allocOnly, hdr, fhdr, pAlloc, vac>>

(* Refix recheck, prevent-dealloc mark, waiters and neighbor fixes: any failure gives up *)
VacGates ==
  /\ vac = "gates"
  /\ \/ pRec = "none" /\ vac' = "unlink"
     \/ vac' = "giveUp"
  /\ UNCHANGED <<allocOnly, hdr, fhdr, pRec, pAlloc>>

(* Give up: release the heap header if held; vacuum_heap_page returns P to bestspace *)
VacGiveUp ==
  /\ vac = "giveUp"
  /\ hdr' = IF hdr = "vac" THEN "none" ELSE hdr
  /\ vac' = "kept"
  /\ UNCHANGED <<allocOnly, fhdr, pRec, pAlloc>>

(* Sysop start, header stats and neighbor links updated, P unfixed *)
VacUnlink ==
  /\ vac = "unlink"
  /\ pAlloc' = "unlinked" /\ vac' = "dealloc"
  /\ UNCHANGED <<allocOnly, hdr, fhdr, pRec>>

(* file_dealloc: permanent file, RVFL_DEALLOC postponed *)
VacFileDealloc ==
  /\ vac = "dealloc"
  /\ pAlloc' = "postponed" /\ vac' = "commit"
  /\ UNCHANGED <<allocOnly, hdr, fhdr, pRec>>

(* file_rv_dealloc_internal -> file_perm_dealloc under the file header. A partial sector gets
   its bit back. A full sector leaves the full table and enters the VSID-ordered partial table. *)
FreeP ==
  /\ fhdr = "none"
  /\ pAlloc' = "free"
  /\ IF \E i \in 1..Len(parts) : parts[i].id = PSector
       THEN /\ parts' = [i \in 1..Len(parts) |->
                          IF parts[i].id = PSector THEN [parts[i] EXCEPT !.free = @ + 1] ELSE parts[i]]
            /\ UNCHANGED fullRoom
       ELSE /\ fullRoom' = fullRoom + 1
            /\ \E k \in 0..Len(parts) :
                 parts' = SubSeq(parts, 1, k) \o <<[id |-> PSector, free |-> 1]>> \o SubSeq(parts, k + 1, Len(parts))

(* log_sysop_commit runs the sysop postpone before vacuum unfixes the heap header *)
VacCommit ==
  /\ vac = "commit"
  /\ IF PostponeBeforeHeaderUnfix
       THEN FreeP /\ vac' = "release" /\ UNCHANGED hdr
       ELSE hdr' = "none" /\ vac' = "postponeLater" /\ UNCHANGED <<parts, fullRoom, pAlloc>>
  /\ UNCHANGED <<nextId, reservations, userNew, tableNew, alloc, iter, freedFirst, reserveLog,
                 fhdr, pRec>>

VacReleaseHeader ==
  /\ vac = "release"
  /\ hdr' = "none" /\ vac' = "done"
  /\ UNCHANGED <<allocOnly, fhdr, pRec, pAlloc>>

(* Model-only control: the postpone runs after the heap header is released *)
VacLatePostpone ==
  /\ vac = "postponeLater"
  /\ FreeP /\ vac' = "done"
  /\ UNCHANGED <<nextId, reservations, userNew, tableNew, alloc, iter, freedFirst, reserveLog,
                 hdr, fhdr, pRec>>

Finished == alloc = "done" /\ vac \in {"done", "kept", "idle"}

Next ==
  \/ AllocFixHeapHeader \/ AllocFixFileHeader \/ AllocUserPage \/ AllocProbeFullTable
  \/ AllocTablePage \/ AllocNext \/ AllocReleaseFileHeader \/ AllocLinkCommitRelease
  \/ Reserve("expandUser", "user") \/ Reserve("expandTable", "table")
  \/ VacEmptyPage \/ VacFixHeapHeader \/ VacGetHeapHeader \/ OtherInsertIntoP \/ VacGates
  \/ VacGiveUp \/ VacUnlink \/ VacFileDealloc \/ VacCommit \/ VacReleaseHeader \/ VacLatePostpone
  \/ (Finished /\ UNCHANGED vars)

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* Structural invariants: expected to hold in every configuration. *)

TypeOK ==
  /\ fullRoom \in Nat /\ reservations \in Nat /\ iter \in 0..Batch
  /\ hdr \in {"none", "alloc", "vac"} /\ fhdr \in {"none", "alloc"}
  /\ pRec \in {"deleted", "none", "new"}
  /\ pAlloc \in {"linked", "unlinked", "postponed", "free"}
  /\ \A i \in 1..Len(parts) : parts[i].free \in 1..SectorPages

(* n_page_free == 0 implies no partial sector (file_header_sanity_check) *)
PartialSectorsHaveFreeBits == \A i \in 1..Len(parts) : parts[i].free >= 1

(* free + user + table pages balance, counting P's bit as free only after file_perm_dealloc *)
Accounting ==
  NFree + userNew + tableNew + (IF pAlloc = "free" THEN 0 ELSE 1)
    = InitFree + 1 + SectorPages * reservations

ReserveOnlyWithoutFreeBits == \A i \in 1..Len(reserveLog) : reserveLog[i].nfree = 0

(* Questions. Each runs as its own TLC invariant; the expected verdict is in run.py. *)

NoReserveWhileUnlinkable == \A i \in 1..Len(reserveLog) : ~reserveLog[i].canUnlink
NoReserveWhileUnlinkedNotFree == \A i \in 1..Len(reserveLog) : ~reserveLog[i].unlinkedNotFree
NoReserveWhilePhysicallyEmpty == \A i \in 1..Len(reserveLog) : ~reserveLog[i].physEmpty
NoRecursiveReserveWhilePhysicallyEmpty ==
  \A i \in 1..Len(reserveLog) : ~(reserveLog[i].recursive /\ reserveLog[i].physEmpty)
NoOuterReserveWhilePhysicallyEmpty ==
  \A i \in 1..Len(reserveLog) : ~(~reserveLog[i].recursive /\ reserveLog[i].physEmpty)
ReclaimFirstAvoidsReservation == ~(freedFirst /\ reservations > 0)
NoReservation == reservations = 0
NoCompletedRun == ~(Finished /\ vac \in {"done", "kept"})
=============================================================================
