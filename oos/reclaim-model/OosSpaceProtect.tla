--------------------------- MODULE OosSpaceProtect ---------------------------
(***************************************************************************)
(* Decision 1: how to keep the slot and the bytes of a deleted OOS chunk   *)
(* free for the undo of that delete.  Decision 4: whether an emptied page  *)
(* may be deallocated without the LSA reclaim gate.                        *)
(*                                                                         *)
(* Two vacuum workers each delete one dead two-chunk chain in a sysop.     *)
(* The chains cross pages in opposite order: A is p1 -> p2, C is p2 -> p1. *)
(* A page holds two one-unit records and has room for two units.  T2 is    *)
(* another transaction that inserts one one-unit record.  At most one      *)
(* disruption happens: a failed delete step or a crash.                    *)
(*                                                                         *)
(* Protect                                                                 *)
(*   "none"            the code: ANCHORED page, the latch is released      *)
(*                     after each chunk                                    *)
(*   "latch"           D1: keep every page latch until the sysop ends      *)
(*   "slot_only"       D2a: ANCHORED_DONT_REUSE_SLOTS; a postpone makes    *)
(*                     the slot reusable at commit; bytes are not kept     *)
(*   "slot_and_bytes"  D2b: as D2a, and the bytes stay reserved for the    *)
(*                     owner until the sysop ends                          *)
(*   "page_exclude"    D2c: the page is closed to inserts and to reclaim   *)
(*                     until the sysop ends                                *)
(*   "no_undo"         D3: the sysop only records a reclaim intent; the    *)
(*                     chunks are deleted after commit, redo-only          *)
(* Gate                                                                    *)
(*   "lsa"             the code: an emptied page is not deallocated while  *)
(*                     an open sysop may undo into it                      *)
(*   "none"            deallocate any page that holds no record            *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Protect, Gate

ASSUME /\ Protect \in {"none", "latch", "slot_only", "slot_and_bytes",
                       "page_exclude", "no_undo"}
       /\ Gate \in {"lsa", "none"}

Pages == {"p1", "p2"}
SlotIds == 1..3
Cap == 2
Workers == {"w1", "w2"}
Other(w) == IF w = "w1" THEN "w2" ELSE "w1"

Rec(own) == [st |-> "used", own |-> own]
\* "free" is REC_DELETED_WILL_REUSE, "marked" is REC_MARKDELETED,
\* "unused" is a slot id at or past num_slots.
Empty(st) == [st |-> st, own |-> "none"]

Chunk(w, k) ==
    CASE w = "w1" /\ k = 1 -> [p |-> "p1", s |-> 1, own |-> "A1"]
      [] w = "w1" /\ k = 2 -> [p |-> "p2", s |-> 1, own |-> "A2"]
      [] w = "w2" /\ k = 1 -> [p |-> "p2", s |-> 2, own |-> "C1"]
      [] w = "w2" /\ k = 2 -> [p |-> "p1", s |-> 2, own |-> "C2"]

DeadOwners == {"A1", "A2", "C1", "C2"}
ZeroRes == [w \in Workers |-> [p \in Pages |-> 0]]

VARIABLES
    slot,        \* [Pages -> [SlotIds -> record]]
    alloc,       \* [Pages -> BOOLEAN]: the page belongs to the OOS file
    wpc,         \* where each worker is
    wk,          \* the chunk each worker works on
    vlog,        \* undo records of each worker's open sysop
    held,        \* pages whose latch each worker keeps (D1)
    res,         \* bytes each worker keeps on each page (D2b)
    excl,        \* workers that closed each page (D2c)
    disrupted,
    t2at,        \* <<page, slot>> of T2's record, or "none"
    brokenSlot,  \* undo found another record in its slot
    brokenRoom,  \* undo found no room for its record
    brokenPage,  \* undo found its page deallocated
    last

vars == <<slot, alloc, wpc, wk, vlog, held, res, excl, disrupted, t2at,
          brokenSlot, brokenRoom, brokenPage, last>>
view == <<slot, alloc, wpc, wk, vlog, held, res, excl, disrupted, t2at,
          brokenSlot, brokenRoom, brokenPage>>

Init ==
    /\ slot = [p \in Pages |-> [s \in SlotIds |->
                 CASE p = "p1" /\ s = 1 -> Rec("A1")
                   [] p = "p1" /\ s = 2 -> Rec("C2")
                   [] p = "p2" /\ s = 1 -> Rec("A2")
                   [] p = "p2" /\ s = 2 -> Rec("C1")
                   [] OTHER -> Empty("unused")]]
    /\ alloc = [p \in Pages |-> TRUE]
    /\ wpc = [w \in Workers |-> "start"]
    /\ wk = [w \in Workers |-> 1]
    /\ vlog = [w \in Workers |-> <<>>]
    /\ held = [w \in Workers |-> {}]
    /\ res = ZeroRes
    /\ excl = [p \in Pages |-> {}]
    /\ disrupted = FALSE
    /\ t2at = "none"
    /\ brokenSlot = {}
    /\ brokenRoom = {}
    /\ brokenPage = {}
    /\ last = "initial state"

UsedIn(sl, p) == Cardinality({s \in SlotIds : sl[p][s].st = "used"})
Used(p) == UsedIn(slot, p)
ResOn(p) == res["w1"][p] + res["w2"][p]
PendingOn(p) ==
    Cardinality({<<w, i>> \in Workers \X (1..2) :
                   i <= Len(vlog[w]) /\ vlog[w][i].p = p})
InVlog(w, p, s) == \E i \in 1..Len(vlog[w]) : vlog[w][i].p = p /\ vlog[w][i].s = s
LatchedByOther(w, p) == p \in held[Other(w)]
OpenSysop(w) ==
    \/ Protect # "no_undo" /\ wpc[w] \in {"del", "commit"}
    \/ Protect = "no_undo" /\ wpc[w] = "commit"

\* Physical undo in reverse log order into the same slot
\* (spage_insert_for_recovery).  rs holds the bytes that other sysops keep.
RECURSIVE Undo(_, _, _, _, _, _, _)
Undo(w, sl, bs, br, bp, rs, lg) ==
    IF lg = <<>> THEN <<sl, bs, br, bp>>
    ELSE LET c == lg[Len(lg)]
             taken == sl[c.p][c.s].st = "used"
             room == Cap - UsedIn(sl, c.p) - rs[Other(w)][c.p]
         IN Undo(w, [sl EXCEPT ![c.p][c.s] = Rec(c.own)],
                 IF taken THEN bs \cup {c.own} ELSE bs,
                 IF ~taken /\ room < 1 THEN br \cup {c.own} ELSE br,
                 IF ~alloc[c.p] THEN bp \cup {c.own} ELSE bp,
                 rs, SubSeq(lg, 1, Len(lg) - 1))

Overwrote(newSlot, newRoom, newPage) ==
    (IF newSlot \ brokenSlot # {} THEN "; the undo writes over another record" ELSE "")
    \o (IF newRoom \ brokenRoom # {} THEN "; the undo finds no room on the page (SP_DOESNT_FIT, fatal)" ELSE "")
    \o (IF newPage \ brokenPage # {} THEN "; the undo targets a deallocated page" ELSE "")

-----------------------------------------------------------------------------

Start(w) ==
    /\ wpc[w] = "start"
    /\ wpc' = [wpc EXCEPT ![w] = IF Protect = "no_undo" THEN "commit" ELSE "del"]
    /\ wk' = [wk EXCEPT ![w] = 1]
    /\ last' = w \o ": log_sysop_start"
               \o (IF Protect = "no_undo" THEN " and a postponed reclaim intent for its chain" ELSE "")
    /\ UNCHANGED <<slot, alloc, vlog, held, res, excl, disrupted, t2at,
                   brokenSlot, brokenRoom, brokenPage>>

Delete(w) ==
    /\ Protect # "no_undo" /\ wpc[w] = "del"
    /\ LET c == Chunk(w, wk[w])
       IN /\ ~LatchedByOther(w, c.p)
          /\ vlog' = [vlog EXCEPT ![w] = Append(@, c)]
          /\ slot' = [slot EXCEPT ![c.p][c.s] =
                        Empty(IF Protect \in {"slot_only", "slot_and_bytes"}
                                THEN "marked" ELSE "free")]
          /\ held' = IF Protect = "latch"
                       THEN [held EXCEPT ![w] = @ \cup {c.p}] ELSE held
          /\ res' = IF Protect = "slot_and_bytes"
                      THEN [res EXCEPT ![w][c.p] = @ + 1] ELSE res
          /\ excl' = IF Protect = "page_exclude"
                       THEN [excl EXCEPT ![c.p] = @ \cup {w}] ELSE excl
          /\ last' = w \o ": RVOOS_DELETE with undo, spage_delete frees " \o c.own \o " on " \o c.p
                     \o (IF Protect = "latch" THEN ", the latch is kept" ELSE ", the latch is released")
    /\ wpc' = [wpc EXCEPT ![w] = IF wk[w] = 2 THEN "commit" ELSE "del"]
    /\ wk' = [wk EXCEPT ![w] = @ + 1]
    /\ UNCHANGED <<alloc, disrupted, t2at, brokenSlot, brokenRoom, brokenPage>>

Commit(w) ==
    /\ wpc[w] = "commit"
    /\ slot' = [p \in Pages |-> [s \in SlotIds |->
                  IF slot[p][s].st = "marked" /\ InVlog(w, p, s)
                    THEN Empty("free") ELSE slot[p][s]]]
    /\ vlog' = [vlog EXCEPT ![w] = <<>>]
    /\ held' = [held EXCEPT ![w] = {}]
    /\ res' = [res EXCEPT ![w] = [p \in Pages |-> 0]]
    /\ excl' = [p \in Pages |-> excl[p] \ {w}]
    /\ wpc' = [wpc EXCEPT ![w] = IF Protect = "no_undo" THEN "rc" ELSE "done"]
    /\ wk' = [wk EXCEPT ![w] = 1]
    /\ last' = w \o ": log_sysop_commit"
               \o (IF Protect \in {"slot_only", "slot_and_bytes"}
                     THEN "; the postpone makes its MARKDELETED slots reusable" ELSE "")
               \o (IF Protect = "no_undo" THEN "; the postponed reclaim starts" ELSE "")
    /\ UNCHANGED <<alloc, disrupted, t2at, brokenSlot, brokenRoom, brokenPage>>

\* D3: delete one chunk after commit; redo-only, the slot is reusable at once.
Reclaim(w) ==
    /\ wpc[w] = "rc"
    /\ LET c == Chunk(w, wk[w])
       IN /\ slot' = [slot EXCEPT ![c.p][c.s] = Empty("free")]
          /\ last' = w \o ": the reclaimer deletes " \o c.own \o " on " \o c.p \o " (redo-only, no undo)"
    /\ wpc' = [wpc EXCEPT ![w] = IF wk[w] = 2 THEN "done" ELSE "rc"]
    /\ wk' = [wk EXCEPT ![w] = @ + 1]
    /\ UNCHANGED <<alloc, vlog, held, res, excl, disrupted, t2at,
                   brokenSlot, brokenRoom, brokenPage>>

\* A delete step fails before chunk wk[w]; log_sysop_abort; the block is retried.
Fail(w) ==
    /\ ~disrupted /\ OpenSysop(w)
    /\ LET u == Undo(w, slot, brokenSlot, brokenRoom, brokenPage, res, vlog[w])
       IN /\ slot' = u[1]
          /\ brokenSlot' = u[2]
          /\ brokenRoom' = u[3]
          /\ brokenPage' = u[4]
          /\ last' = w \o ": a delete step fails; log_sysop_abort" \o Overwrote(u[2], u[3], u[4])
    /\ vlog' = [vlog EXCEPT ![w] = <<>>]
    /\ held' = [held EXCEPT ![w] = {}]
    /\ res' = [res EXCEPT ![w] = [p \in Pages |-> 0]]
    /\ excl' = [p \in Pages |-> excl[p] \ {w}]
    /\ wpc' = [wpc EXCEPT ![w] = "start"]
    /\ wk' = [wk EXCEPT ![w] = 1]
    /\ disrupted' = TRUE
    /\ UNCHANGED <<alloc, t2at>>

\* Restart recovery undoes every open sysop.  In-memory reservations are
\* gone, but no insert runs during recovery.  A D3 reclaim that had started
\* after commit is finished by recovery.
Crash ==
    /\ ~disrupted /\ \E w \in Workers : wpc[w] # "done"
    /\ LET l1 == IF OpenSysop("w1") THEN vlog["w1"] ELSE <<>>
           l2 == IF OpenSysop("w2") THEN vlog["w2"] ELSE <<>>
           u1 == Undo("w1", slot, brokenSlot, brokenRoom, brokenPage, ZeroRes, l1)
           u2 == Undo("w2", u1[1], u1[2], u1[3], u1[4], ZeroRes, l2)
       IN /\ slot' = u2[1]
          /\ brokenSlot' = u2[2]
          /\ brokenRoom' = u2[3]
          /\ brokenPage' = u2[4]
          /\ last' = "crash; restart recovery undoes the open sysops" \o Overwrote(u2[2], u2[3], u2[4])
    /\ wpc' = [w \in Workers |-> IF OpenSysop(w) THEN "start" ELSE wpc[w]]
    /\ wk' = [w \in Workers |-> IF OpenSysop(w) THEN 1 ELSE wk[w]]
    /\ vlog' = [w \in Workers |-> <<>>]
    /\ held' = [w \in Workers |-> {}]
    /\ res' = ZeroRes
    /\ excl' = [p \in Pages |-> {}]
    /\ disrupted' = TRUE
    /\ UNCHANGED <<alloc, t2at>>

-----------------------------------------------------------------------------

T2Insert ==
    /\ t2at = "none"
    /\ \E p \in Pages, s \in SlotIds :
         /\ alloc[p]
         /\ \A w \in Workers : p \notin held[w]
         /\ excl[p] = {}
         /\ slot[p][s].st \in {"free", "unused"}
         /\ Used(p) + ResOn(p) + 1 <= Cap
         /\ slot' = [slot EXCEPT ![p][s] = Rec("T2")]
         /\ t2at' = <<p, s>>
         /\ last' = "T2: an INSERT puts its record in slot " \o (IF s = 1 THEN "1" ELSE IF s = 2 THEN "2" ELSE "3")
                    \o " of " \o p \o " and commits"
    /\ UNCHANGED <<alloc, wpc, wk, vlog, held, res, excl, disrupted,
                   brokenSlot, brokenRoom, brokenPage>>

\* oos_reclaim_empty_pages: deallocate a page that holds no record.
Dealloc ==
    \E p \in Pages :
       /\ alloc[p] /\ Used(p) = 0
       /\ \A w \in Workers : p \notin held[w]
       /\ excl[p] = {}
       /\ Gate = "lsa" => PendingOn(p) = 0
       /\ alloc' = [alloc EXCEPT ![p] = FALSE]
       /\ last' = "oos_reclaim_empty_pages deallocates " \o p
                  \o (IF Gate = "lsa" THEN " (no open sysop wrote it)" ELSE " (no gate)")
       /\ UNCHANGED <<slot, wpc, wk, vlog, held, res, excl, disrupted, t2at,
                      brokenSlot, brokenRoom, brokenPage>>

Finished ==
    /\ \A w \in Workers : wpc[w] = "done"
    /\ UNCHANGED vars

Next ==
    \/ \E w \in Workers : Start(w) \/ Delete(w) \/ Commit(w) \/ Reclaim(w) \/ Fail(w)
    \/ Crash \/ T2Insert \/ Dealloc \/ Finished

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
\* Properties

UndoFindsEmptySlot == brokenSlot = {}
UndoFindsRoom == brokenRoom = {}
UndoFindsPage == brokenPage = {}
OtherRecordIntact == t2at # "none" => slot[t2at[1]][t2at[2]] = Rec("T2")
ReclaimedWhenDone ==
    (\A w \in Workers : wpc[w] = "done") =>
        \A p \in Pages, s \in SlotIds : slot[p][s].own \notin DeadOwners

\* Each worker waits for a page latch that the other worker keeps.  Page
\* latches have no deadlock detection, so both wait forever.
NoLatchWaitCycle ==
    ~ \A w \in Workers :
        /\ wpc[w] = "del"
        /\ LatchedByOther(w, Chunk(w, wk[w]).p)

\* Reasons: state invariants that make the properties hold.

\* Every slot that an open sysop may undo into is empty right now.
UndoSlotsStayEmpty ==
    \A w \in Workers : \A i \in 1..Len(vlog[w]) :
        slot[vlog[w][i].p][vlog[w][i].s].st # "used"
\* The records on a page plus the records that open sysops may restore fit.
UndoBytesStayFree == \A p \in Pages : Used(p) + PendingOn(p) <= Cap
\* Every page that an open sysop may undo into is still allocated.
UndoPagesStayAllocated ==
    \A w \in Workers : \A i \in 1..Len(vlog[w]) : alloc[vlog[w][i].p]

\* D1: the sysop still holds the latch of every page it may undo into.
LatchCoversUndo ==
    \A w \in Workers : \A i \in 1..Len(vlog[w]) : vlog[w][i].p \in held[w]
\* D2a, D2b: every slot an open sysop may undo into is MARKDELETED.
MarkCoversUndo ==
    \A w \in Workers : \A i \in 1..Len(vlog[w]) :
        slot[vlog[w][i].p][vlog[w][i].s].st = "marked"
\* D2b: reserved bytes match the pending undo and are never handed out.
ReserveCoversUndo ==
    /\ \A w \in Workers, p \in Pages :
         res[w][p] = Cardinality({i \in 1..Len(vlog[w]) : vlog[w][i].p = p})
    /\ \A p \in Pages : Used(p) + ResOn(p) <= Cap
\* D2c: every page an open sysop may undo into is closed by that sysop.
ExcludeCoversUndo ==
    \A w \in Workers : \A i \in 1..Len(vlog[w]) : w \in excl[vlog[w][i].p]
\* D3: no OOS chunk delete is ever undoable.
NothingToUndo == \A w \in Workers : vlog[w] = <<>>

=============================================================================
