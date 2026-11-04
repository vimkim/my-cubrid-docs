--------------------------- MODULE SidecarLifecycle ---------------------------
(***************************************************************************)
(* Value lifecycle and reader safety of the Sidecar design.               *)
(*                                                                         *)
(* Design: /home/vimkim/gh/my-cubrid-docs/sidecar/design.md (sections 5.5, *)
(* 5.6, 6, 13, 16 A7).  Engine: CUBRID develop e64a04a79, paths under src/.*)
(*                                                                         *)
(* One hot row with one large column.  Its writers are serialized by the   *)
(* row X lock.  Each version of the row names at most one store record     *)
(* (slot) and the value it expects there.  Hot vacuum and store vacuum act *)
(* on their own DELIDs.  One reader of a class chosen from ReaderClasses   *)
(* reads the row once.  README.md maps every action to the design and code.*)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
  Writers,           \* writer transactions (model values)
  NSlots,            \* store slots 1..NSlots; 0 means "no ref" (value inline)
  MaxOps,            \* statements per writer transaction
  MaxStmts,          \* statements of all writers together
  MaxVals,           \* values the row ever gets (INSERT, LARGE, INLINE)
  MaxForeign,        \* store inserts by another row
  MaxRetry,          \* retry bound of the unprotected readers (design: 3)
  Ops,               \* statement kinds the writers may run
  ReaderClasses,     \* subset of {"snap", "lock", "committed", "dirty", "null"}
  \* Design switches.  The design is StoreReuse = FALSE, Pin = "none", and TRUE for the rest
  \* except VacuumUncommitted = FALSE.  Broken variants flip one switch.
  StoreReuse,        \* vacuum leaves a store slot REC_DELETED_WILL_REUSE instead of REC_MARKDELETED
  Pin,               \* "none", "before" or "after" the visibility decision (first draft, section 13)
  Retry,             \* retry rule of 5.6 (c)
  DeadRowTest,       \* the retry rule's "version carries a DELID whose writer is no longer active" test
  DeleteStamps,      \* DELETE stamps the store records the version names (I-4)
  StampFirst,        \* the stamp precedes the hot write (I-4)
  VacuumUncommitted, \* store vacuum also removes a record whose DELID writer is still active
  ResolveUnderLatch, \* heap-path unprotected readers resolve before they release the hot latch
  SnapRegister,      \* the snapshot reader's snapshot is registered (5.6 a)
  PinDeadRow         \* with a pin, a version whose DELID precedes the pin is dead (first draft, section 13)

NoSlot == 0
Slots == 1..NSlots
NoVer == [ins |-> 0, del |-> 0, ref |-> NoSlot, val |-> 0]
UClasses == {"committed", "dirty", "null"}
InFlight == {"begun", "work", "undo", "partial"}
HoldsLock == {"work", "undo", "partial"}

VARIABLES
  wst, wid, wops, wop, wpc, wold, wnew, wundo, wsave,   \* writer transactions
  nextId, lockOwner, nstmts,                            \* MVCCID counter, row lock, statements run
  hot, hlog,                                            \* current hot version, its prev_version chain
  store, nvals, nforeign, fslots,                       \* store slots, value counters, other row's slots
  committedLive, everCommitted, stampErr,               \* ghosts
  rcls, rpc, rver, rres, rtry, rreg, rsnap, rlatch, rabsent, rdrops   \* the reader

wv  == <<wst, wid, wops, wop, wpc, wold, wnew, wundo, wsave>>
sv  == <<nextId, lockOwner, nstmts>>
hv  == <<hot, hlog>>
stv == <<store, nvals, nforeign, fslots>>
gv  == <<committedLive, everCommitted, stampErr>>
rv  == <<rcls, rpc, rver, rres, rtry, rreg, rsnap, rlatch, rabsent, rdrops>>
vars == <<wv, sv, hv, stv, gv, rv>>

Min(S) == CHOOSE x \in S : \A y \in S : x <= y
Res(k, v) == [k |-> k, v |-> v]

-----------------------------------------------------------------------------
(* MVCC state.  transaction/mvcc_table.cpp:355 compute_oldest_visible_mvccid *)

Active(id) == \E w \in Writers : wid[w] = id /\ wst[w] \in InFlight
ActiveIds == {wid[w] : w \in {x \in Writers : wst[x] \in InFlight}}
CommittedIds == {wid[w] : w \in {x \in Writers : wst[x] = "committed"}}
LowestActive == IF ActiveIds = {} THEN nextId ELSE Min(ActiveIds)
\* The vacuum threshold: the global lowest active MVCCID and every registered lowest visible MVCCID.
Threshold == IF rreg = 0 THEN LowestActive ELSE Min({LowestActive, rreg})

Chain == IF hot = NoVer THEN <<>> ELSE <<hot>> \o hlog
Live(k) == store[k].st = "live"
CurLive == IF hot # NoVer /\ hot.del = 0 THEN hot ELSE NoVer
InCall == rpc \notin {"idle", "done"}

-----------------------------------------------------------------------------
(* Writers.  Statements are sequences of atomic steps (section 6 flows).     *)

Steps(op) ==
  CASE op = "INSERT" -> <<"sins", "hins">>
    [] op = "LARGE"  -> IF StampFirst THEN <<"sins", "stamp", "hupd">> ELSE <<"sins", "hupd", "stamp">>
    [] op = "INLINE" -> IF StampFirst THEN <<"stamp", "hupd">> ELSE <<"hupd", "stamp">>
    [] op = "SMALL"  -> <<"hupd">>
    [] op = "DELETE" -> IF DeleteStamps THEN <<"stamp", "hdel">> ELSE <<"hdel">>

InStep(w, s) == wst[w] = "work" /\ wop[w] # "none" /\ Steps(wop[w])[wpc[w] + 1] = s

Advance(w) ==
  IF wpc[w] + 1 = Len(Steps(wop[w]))
  THEN wpc' = [wpc EXCEPT ![w] = 0] /\ wop' = [wop EXCEPT ![w] = "none"]
  ELSE wpc' = [wpc EXCEPT ![w] = @ + 1] /\ UNCHANGED wop

Push(w, e) == wundo' = [wundo EXCEPT ![w] = Append(@, e)]

Begin(w) ==
  /\ wst[w] = "idle"
  /\ wst' = [wst EXCEPT ![w] = "begun"]
  /\ wid' = [wid EXCEPT ![w] = nextId]
  /\ nextId' = nextId + 1
  /\ UNCHANGED <<wops, wop, wpc, wold, wnew, wundo, wsave, lockOwner, nstmts, hv, stv, gv, rv>>

LockRow(w) ==
  /\ wst[w] = "begun" /\ lockOwner = "none"
  /\ lockOwner' = w
  /\ wst' = [wst EXCEPT ![w] = "work"]
  /\ UNCHANGED <<wid, wops, wop, wpc, wold, wnew, wundo, wsave, nextId, nstmts, hv, stv, gv, rv>>

CanStart(op) ==
  CASE op = "INSERT" -> hot = NoVer /\ ~everCommitted /\ nvals < MaxVals
    [] op = "LARGE"  -> hot # NoVer /\ hot.del = 0 /\ nvals < MaxVals
    [] op = "INLINE" -> hot # NoVer /\ hot.del = 0 /\ hot.ref # NoSlot /\ nvals < MaxVals
    [] op = "SMALL"  -> hot # NoVer /\ hot.del = 0
    [] op = "DELETE" -> hot # NoVer /\ hot.del = 0

\* The plan reads the old record under the hot latch and lists the dropped ref (sidecar_plan_update).
StartOp(w, op) ==
  /\ wst[w] = "work" /\ wop[w] = "none" /\ wops[w] < MaxOps /\ nstmts < MaxStmts
  /\ CanStart(op)
  /\ nstmts' = nstmts + 1
  /\ wop' = [wop EXCEPT ![w] = op]
  /\ wops' = [wops EXCEPT ![w] = @ + 1]
  /\ wsave' = [wsave EXCEPT ![w] = Len(wundo[w])]
  /\ wold' = [wold EXCEPT ![w] = hot.ref]
  /\ UNCHANGED <<wst, wid, wpc, wnew, wundo, nextId, lockOwner, hv, stv, gv, rv>>

\* spage_find_empty_slot takes the first REC_DELETED_WILL_REUSE slot of its page (storage/slotted_page.c:1286)
\* or a new slot; the page itself is the heap's choice, so either may happen.
FirstOf(S) == IF S = {} THEN {} ELSE {Min(S)}
InsertSlots ==
  FirstOf({k \in Slots : store[k].st = "reuse"}) \cup FirstOf({k \in Slots : store[k].st = "unused"})

StoreInsert(w) ==
  /\ InStep(w, "sins")
  /\ \E k \in InsertSlots :
       /\ store' = [store EXCEPT ![k] = [st |-> "live", val |-> nvals + 1, del |-> 0]]
       /\ wnew' = [wnew EXCEPT ![w] = [ref |-> k, val |-> nvals + 1]]
       /\ Push(w, [k |-> "sins", s |-> k, op |-> wop[w]])
  /\ nvals' = nvals + 1
  /\ Advance(w)
  /\ UNCHANGED <<wst, wid, wops, wold, wsave, sv, hv, nforeign, fslots, gv, rv>>

\* A stamp of a record that is absent or already stamped is an error of heap_delete_logical.
Stamp(w) ==
  /\ InStep(w, "stamp")
  /\ LET k == wold[w] IN
       IF k = NoSlot
       THEN UNCHANGED <<store, wundo, stampErr>>
       ELSE IF Live(k) /\ store[k].del = 0
            THEN /\ store' = [store EXCEPT ![k].del = wid[w]]
                 /\ Push(w, [k |-> "stamp", s |-> k, op |-> wop[w]])
                 /\ UNCHANGED stampErr
            ELSE /\ stampErr' = TRUE
                 /\ UNCHANGED <<store, wundo>>
  /\ Advance(w)
  /\ UNCHANGED <<wst, wid, wops, wold, wnew, wsave, sv, hv, nvals, nforeign, fslots,
                 committedLive, everCommitted, rv>>

HotInsert(w) ==
  /\ InStep(w, "hins") /\ ~rlatch
  /\ hot' = [ins |-> wid[w], del |-> 0, ref |-> wnew[w].ref, val |-> wnew[w].val]
  /\ hlog' = <<>>
  /\ Push(w, [k |-> "hins", s |-> NoSlot, op |-> wop[w]])
  /\ Advance(w)
  /\ UNCHANGED <<wst, wid, wops, wold, wnew, wsave, sv, stv, gv, rv>>

NewVersion(w) ==
  CASE wop[w] = "LARGE"  -> [ins |-> wid[w], del |-> 0, ref |-> wnew[w].ref, val |-> wnew[w].val]
    [] wop[w] = "INLINE" -> [ins |-> wid[w], del |-> 0, ref |-> NoSlot, val |-> nvals + 1]
    [] wop[w] = "SMALL"  -> [hot EXCEPT !.ins = wid[w]]

HotUpdate(w) ==
  /\ InStep(w, "hupd") /\ ~rlatch
  /\ hot' = NewVersion(w)
  /\ hlog' = <<hot>> \o hlog
  /\ nvals' = IF wop[w] = "INLINE" THEN nvals + 1 ELSE nvals
  /\ Push(w, [k |-> "hupd", s |-> NoSlot, op |-> wop[w]])
  /\ Advance(w)
  /\ UNCHANGED <<wst, wid, wops, wold, wnew, wsave, sv, store, nforeign, fslots, gv, rv>>

HotDelete(w) ==
  /\ InStep(w, "hdel") /\ ~rlatch
  /\ hot' = [hot EXCEPT !.del = wid[w]]
  /\ Push(w, [k |-> "hdel", s |-> NoSlot, op |-> wop[w]])
  /\ Advance(w)
  /\ UNCHANGED <<wst, wid, wops, wold, wnew, wsave, sv, hlog, stv, gv, rv>>

Commit(w) ==
  /\ wst[w] = "work" /\ wop[w] = "none"
  /\ LET live == hot # NoVer /\ hot.del = 0
         stamped == \E i \in 1..Len(wundo[w]) : wundo[w][i].k = "stamp"
     IN /\ committedLive' = live
        /\ everCommitted' = (everCommitted \/ hot # NoVer)
        /\ rabsent' = (rabsent \/ (InCall /\ rcls \in UClasses /\ ~live))
        /\ rdrops' = IF InCall /\ rcls \in UClasses /\ stamped THEN rdrops + 1 ELSE rdrops
  /\ wst' = [wst EXCEPT ![w] = "committed"]
  /\ wundo' = [wundo EXCEPT ![w] = <<>>]
  /\ wold' = [wold EXCEPT ![w] = NoSlot]
  /\ wnew' = [wnew EXCEPT ![w] = [ref |-> NoSlot, val |-> 0]]
  /\ wops' = [wops EXCEPT ![w] = 0]
  /\ wsave' = [wsave EXCEPT ![w] = 0]
  /\ lockOwner' = "none"
  /\ UNCHANGED <<wid, wop, wpc, nextId, nstmts, hv, stv, stampErr,
                 rcls, rpc, rver, rres, rtry, rreg, rsnap, rlatch>>

Abort(w) ==
  /\ wst[w] = "work"
  /\ wst' = [wst EXCEPT ![w] = "undo"]
  /\ UNCHANGED <<wid, wops, wop, wpc, wold, wnew, wundo, wsave, sv, hv, stv, gv, rv>>

\* log_abort_partial (transaction/log_manager.c:5637): undo back to the start of the last statement.
PartialRollback(w) ==
  /\ wst[w] = "work" /\ Len(wundo[w]) > wsave[w]
  /\ wst' = [wst EXCEPT ![w] = "partial"]
  /\ UNCHANGED <<wid, wops, wop, wpc, wold, wnew, wundo, wsave, sv, hv, stv, gv, rv>>

\* One undo record, in reverse LSA order.  Hot undo needs the hot page X latch.
UndoStep(w) ==
  /\ wst[w] \in {"undo", "partial"}
  /\ Len(wundo[w]) > (IF wst[w] = "partial" THEN wsave[w] ELSE 0)
  /\ LET e == wundo[w][Len(wundo[w])] IN
       /\ (e.k \in {"hins", "hupd", "hdel"} => ~rlatch)
       /\ CASE e.k = "sins"  -> store' = [store EXCEPT ![e.s] = [st |-> "reuse", val |-> 0, del |-> 0]]
                                /\ UNCHANGED hv
            [] e.k = "stamp" -> store' = [store EXCEPT ![e.s].del = 0] /\ UNCHANGED hv
            [] e.k = "hins"  -> hot' = NoVer /\ hlog' = <<>> /\ UNCHANGED store
            [] e.k = "hupd"  -> hot' = Head(hlog) /\ hlog' = Tail(hlog) /\ UNCHANGED store
            [] e.k = "hdel"  -> hot' = [hot EXCEPT !.del = 0] /\ UNCHANGED <<store, hlog>>
  /\ wundo' = [wundo EXCEPT ![w] = SubSeq(@, 1, Len(@) - 1)]
  /\ UNCHANGED <<wst, wid, wops, wop, wpc, wold, wnew, wsave, sv, nvals, nforeign, fslots, gv, rv>>

\* log_rollback completes before logtb_complete_mvcc ends the MVCCID and before locks go
\* (transaction/log_manager.c:5371, :5384).
UndoEnd(w) ==
  /\ wst[w] = "undo" /\ wundo[w] = <<>>
  /\ wst' = [wst EXCEPT ![w] = "aborted"]
  /\ wold' = [wold EXCEPT ![w] = NoSlot]
  /\ wnew' = [wnew EXCEPT ![w] = [ref |-> NoSlot, val |-> 0]]
  /\ wops' = [wops EXCEPT ![w] = 0]
  /\ wop' = [wop EXCEPT ![w] = "none"]
  /\ wpc' = [wpc EXCEPT ![w] = 0]
  /\ wsave' = [wsave EXCEPT ![w] = 0]
  /\ lockOwner' = "none"
  /\ UNCHANGED <<wid, wundo, nextId, nstmts, hv, stv, gv, rv>>

PartialEnd(w) ==
  /\ wst[w] = "partial" /\ Len(wundo[w]) = wsave[w]
  /\ wst' = [wst EXCEPT ![w] = "work"]
  /\ wop' = [wop EXCEPT ![w] = "none"]
  /\ wpc' = [wpc EXCEPT ![w] = 0]
  /\ wold' = [wold EXCEPT ![w] = NoSlot]
  /\ wnew' = [wnew EXCEPT ![w] = [ref |-> NoSlot, val |-> 0]]
  /\ UNCHANGED <<wid, wops, wundo, wsave, sv, hv, stv, gv, rv>>

\* Another row's INSERT.  Only a slot that was freed can meet this row's refs, so the other row
\* inserts only into a freed slot; a fresh slot would change nothing this row can observe.
ForeignInsert ==
  /\ nforeign < MaxForeign
  /\ \E k \in {j \in Slots : store[j].st = "reuse"} :
       /\ store' = [store EXCEPT ![k] = [st |-> "live", val |-> 100 + nforeign, del |-> 0]]
       /\ fslots' = fslots \cup {k}
  /\ nforeign' = nforeign + 1
  /\ UNCHANGED <<wv, sv, hv, nvals, gv, rv>>

-----------------------------------------------------------------------------
(* Vacuum.  Two streams, each from its own DELID, neither reads a ref (I-5).*)

StoreVacuumable(k) ==
  /\ Live(k) /\ store[k].del # 0
  /\ \/ store[k].del < Threshold
     \/ VacuumUncommitted /\ Active(store[k].del)

\* spage_vacuum_slot with reusable from the file type (query/vacuum.c:2398, :2568, slotted_page.c:4853-4860).
StoreVacuum(k) ==
  /\ StoreVacuumable(k)
  /\ store' = [store EXCEPT ![k] = [st |-> IF StoreReuse THEN "reuse" ELSE "markdel", val |-> 0, del |-> 0]]
  /\ UNCHANGED <<wv, sv, hv, nvals, nforeign, fslots, gv, rv>>

HotVacuumable == hot # NoVer /\ hot.del # 0 /\ hot.del < Threshold

HotVacuum ==
  /\ HotVacuumable /\ ~rlatch
  /\ hot' = NoVer /\ hlog' = <<>>
  /\ UNCHANGED <<wv, sv, stv, gv, rv>>

VacuumEnabled == HotVacuumable \/ \E k \in Slots : StoreVacuumable(k)

-----------------------------------------------------------------------------
(* The reader.  One reader, one fetch, of a class from section 5.6.         *)

Finish(res) ==
  /\ rres' = res /\ rpc' = "done" /\ rlatch' = FALSE /\ rreg' = 0

RStart(c) ==
  /\ rpc = "idle"
  /\ rcls' = c
  /\ rabsent' = (c \in UClasses /\ ~committedLive)
  /\ rpc' = IF c = "lock" THEN "lock" ELSE "read"
  /\ rreg' = CASE c = "snap"     -> (IF SnapRegister THEN LowestActive ELSE 0)
               [] c \in UClasses -> (IF Pin = "before" THEN LowestActive ELSE 0)
               [] OTHER          -> 0
  /\ rsnap' = IF c = "snap" THEN CommittedIds ELSE {}
  /\ UNCHANGED <<wv, sv, hv, stv, gv, rver, rres, rtry, rlatch, rdrops>>

\* (a) Snapshot reader.  heap_get_visible_version_internal: TOO_NEW_FOR_SNAPSHOT follows prev_version_lsa
\* into the undo log (storage/heap_file.c:27039-27047); TOO_OLD is a committed delete it sees.
SnapVisible(S) ==
  LET ch == Chain
      seen == {i \in 1..Len(ch) : ch[i].ins \in S}
  IN IF seen = {} THEN NoVer
     ELSE LET v == ch[Min(seen)] IN IF v.del # 0 /\ v.del \in S THEN NoVer ELSE v

SnapRead ==
  /\ rpc = "read" /\ rcls = "snap"
  /\ LET v == SnapVisible(rsnap) IN
       IF v = NoVer THEN rres' = Res("absent", 0) /\ rpc' = "release" /\ UNCHANGED rver
       ELSE rver' = v /\ rpc' = "resolve" /\ UNCHANGED rres
  /\ UNCHANGED <<wv, sv, hv, stv, gv, rcls, rtry, rreg, rsnap, rlatch, rabsent, rdrops>>

\* (b) Row-lock holder.  heap_get_last_version (storage/heap_file.c:27197) under the row lock; a version
\* deleted by a committed transaction gives S_DOESNT_EXIST (transaction/locator_sr.c:13206-13256).
LockAcquire ==
  /\ rpc = "lock" /\ lockOwner = "none"
  /\ lockOwner' = "reader" /\ rpc' = "read"
  /\ UNCHANGED <<wv, nextId, nstmts, hv, stv, gv, rcls, rver, rres, rtry, rreg, rsnap, rlatch, rabsent, rdrops>>

LockRead ==
  /\ rpc = "read" /\ rcls = "lock"
  /\ IF hot = NoVer \/ (hot.del # 0 /\ ~Active(hot.del))
     THEN rres' = Res("absent", 0) /\ rpc' = "release" /\ UNCHANGED rver
     ELSE rver' = hot /\ rpc' = "resolve" /\ UNCHANGED rres
  /\ UNCHANGED <<wv, sv, hv, stv, gv, rcls, rtry, rreg, rsnap, rlatch, rabsent, rdrops>>

\* Protected readers keep the record lazy and dereference later with no hot latch (sidecar_read_value).
\* A protected reader that finds the record absent stops with ER_SIDECAR_DANGLING_REF.
Deref(v) ==
  IF v.ref = NoSlot THEN Res("val", v.val)
  ELSE IF Live(v.ref) THEN Res("val", store[v.ref].val) ELSE Res("dangling", 0)

PResolve ==
  /\ rpc = "resolve" /\ rcls \in {"snap", "lock"}
  /\ rres' = Deref(rver) /\ rpc' = "release"
  /\ UNCHANGED <<wv, sv, hv, stv, gv, rcls, rver, rtry, rreg, rsnap, rlatch, rabsent, rdrops>>

PRelease ==
  /\ rpc = "release"
  /\ rpc' = "done" /\ rreg' = 0
  /\ lockOwner' = IF rcls = "lock" THEN "none" ELSE lockOwner
  /\ UNCHANGED <<wv, nextId, nstmts, hv, stv, gv, rcls, rver, rres, rtry, rsnap, rlatch, rabsent, rdrops>>

\* (c) Unprotected readers: committed snapshot (mvcc_satisfies_committed, transaction/mvcc.c:642-675),
\* dirty snapshot (mvcc_satisfies_dirty, :516-620) and no snapshot.  They read under the hot latch.
\* Only the committed reader can find the current version too new; it then reads an older version from
\* the undo log, and the log walk may release the hot page (storage/heap_file.c:26774-26781).
AfterRead == IF Pin = "after" THEN "pin" ELSE "resolve"

URead ==
  /\ rpc = "read" /\ rcls \in UClasses
  /\ IF hot = NoVer
     THEN Finish(Res("absent", 0)) /\ UNCHANGED rver
     ELSE IF rcls = "committed" /\ Active(hot.ins)
     THEN LET idx == {i \in 1..Len(hlog) : ~Active(hlog[i].ins)} IN
            IF idx = {}
            THEN Finish(Res("absent", 0)) /\ UNCHANGED rver
            ELSE LET v == hlog[Min(idx)] IN
                   IF v.del # 0 /\ ~Active(v.del)
                   THEN Finish(Res("absent", 0)) /\ UNCHANGED rver
                   ELSE /\ rver' = v /\ rpc' = AfterRead /\ rlatch' \in BOOLEAN
                        /\ UNCHANGED <<rres, rreg>>
     ELSE IF rcls # "null" /\ hot.del # 0 /\ ~Active(hot.del)
     THEN Finish(Res("absent", 0)) /\ UNCHANGED rver
     ELSE /\ rver' = hot /\ rpc' = AfterRead /\ rlatch' = ResolveUnderLatch
          /\ UNCHANGED <<rres, rreg>>
  /\ UNCHANGED <<wv, sv, hv, stv, gv, rcls, rtry, rsnap, rabsent, rdrops>>

\* First draft's horizon pin, taken after the visibility decision.
UPin ==
  /\ rpc = "pin"
  /\ rreg' = LowestActive /\ rpc' = "resolve"
  /\ UNCHANGED <<wv, sv, hv, stv, gv, rcls, rver, rres, rtry, rsnap, rlatch, rabsent, rdrops>>

\* sidecar_on_fetch and the retry rule (5.6 c).  The pin variants add the first draft's dead-row rule.
UResolve ==
  /\ rpc = "resolve" /\ rcls \in UClasses
  /\ IF rver.ref = NoSlot
     THEN Finish(Res("val", rver.val)) /\ UNCHANGED <<rver, rtry>>
     ELSE IF Pin # "none" /\ PinDeadRow /\ rver.del # 0 /\ rver.del < rreg
     THEN Finish(Res("absent", 0)) /\ UNCHANGED <<rver, rtry>>
     ELSE IF Live(rver.ref)
     THEN Finish(Res("val", store[rver.ref].val)) /\ UNCHANGED <<rver, rtry>>
     ELSE IF DeadRowTest /\ rver.del # 0 /\ ~Active(rver.del)
     THEN Finish(Res("absent", 0)) /\ UNCHANGED <<rver, rtry>>
     ELSE IF ~Retry
     THEN Finish(Res("absent", 0)) /\ UNCHANGED <<rver, rtry>>
     ELSE IF rtry < MaxRetry
     THEN /\ rtry' = rtry + 1 /\ rpc' = "read" /\ rlatch' = FALSE /\ rver' = NoVer
          /\ UNCHANGED <<rres, rreg>>
     ELSE Finish(Res("exhausted", 0)) /\ UNCHANGED <<rver, rtry>>
  /\ UNCHANGED <<wv, sv, hv, stv, gv, rcls, rsnap, rabsent, rdrops>>

-----------------------------------------------------------------------------

Init ==
  /\ wst = [w \in Writers |-> "idle"]
  /\ wid = [w \in Writers |-> 0]
  /\ wops = [w \in Writers |-> 0]
  /\ wop = [w \in Writers |-> "none"]
  /\ wpc = [w \in Writers |-> 0]
  /\ wold = [w \in Writers |-> NoSlot]
  /\ wnew = [w \in Writers |-> [ref |-> NoSlot, val |-> 0]]
  /\ wundo = [w \in Writers |-> <<>>]
  /\ wsave = [w \in Writers |-> 0]
  /\ nextId = 1
  /\ lockOwner = "none"
  /\ nstmts = 0
  /\ hot = NoVer
  /\ hlog = <<>>
  /\ store = [k \in Slots |-> [st |-> "unused", val |-> 0, del |-> 0]]
  /\ nvals = 0
  /\ nforeign = 0
  /\ fslots = {}
  /\ committedLive = FALSE
  /\ everCommitted = FALSE
  /\ stampErr = FALSE
  /\ rcls = "none"
  /\ rpc = "idle"
  /\ rver = NoVer
  /\ rres = Res("none", 0)
  /\ rtry = 0
  /\ rreg = 0
  /\ rsnap = {}
  /\ rlatch = FALSE
  /\ rabsent = FALSE
  /\ rdrops = 0

\* Every transaction ended, the reader is done and vacuum has nothing left: a correct end state.
Terminated ==
  /\ \A w \in Writers : wst[w] \in {"committed", "aborted"}
  /\ rpc = "done" \/ ReaderClasses = {}
  /\ ~VacuumEnabled
  /\ UNCHANGED vars

Next ==
  \/ \E w \in Writers :
       \/ Begin(w) \/ LockRow(w)
       \/ \E op \in Ops : StartOp(w, op)
       \/ StoreInsert(w) \/ Stamp(w) \/ HotInsert(w) \/ HotUpdate(w) \/ HotDelete(w)
       \/ Commit(w) \/ Abort(w) \/ PartialRollback(w) \/ UndoStep(w) \/ UndoEnd(w) \/ PartialEnd(w)
  \/ ForeignInsert
  \/ \E k \in Slots : StoreVacuum(k)
  \/ HotVacuum
  \/ \E c \in ReaderClasses : RStart(c)
  \/ SnapRead \/ LockAcquire \/ LockRead \/ PResolve \/ PRelease
  \/ URead \/ UPin \/ UResolve
  \/ Terminated

Spec == Init /\ [][Next]_vars

WriterSymmetry == Permutations(Writers)

\* Reader runs stop exploring once the reader is done.  Its result is final then, and TLC still
\* checks the invariants in the state where the reader finishes.
ReaderOpen == rpc # "done"

\* bound_3_four_commits only has to show the retry bound being exceeded, so it leaves out rollback.
NoRollback == \A w \in Writers : wst[w] \notin {"undo", "partial"}

-----------------------------------------------------------------------------
(* Properties.  README.md states each one and its harm in one sentence.     *)

\* Every value a reader returns is exactly the value its returned version names, and no writer
\* follows a ref that does not resolve.
NoDanglingRef ==
  /\ ~stampErr
  /\ rres.k # "dangling"
  /\ rres.k = "val" => rres.v = rver.val

\* An unprotected reader reports the row absent only if the row had no committed live version at
\* some moment of its call.
NoLostRow == (rcls \in UClasses /\ rres.k = "absent") => rabsent

\* The retry loop ends within MaxRetry retries.
Bounded == rres.k # "exhausted"

\* Each retry needs a distinct transaction that stamped a store record to commit during the fetch.
RetryNeedsCommit == rtry <= rdrops

\* Readers that resolve under the hot latch never retry (5.6 c, heap path).
HeapPathNoRetry == rcls \in {"dirty", "null"} => rtry = 0

Namers(k) ==
  (IF k \in fslots THEN {"other row"} ELSE {}) \cup (IF CurLive # NoVer /\ CurLive.ref = k THEN {"row"} ELSE {})

Quiescent ==
  /\ \A w \in Writers : wst[w] \notin InFlight
  /\ rpc \in {"idle", "done"}
  /\ ~VacuumEnabled

\* After every transaction ends and vacuum quiesces, every live store record is named by exactly one
\* current version, and the current version's ref resolves to its own value.
NoOrphan ==
  Quiescent =>
    /\ \A k \in Slots : Live(k) => Cardinality(Namers(k)) = 1
    /\ CurLive.ref # NoSlot => (Live(CurLive.ref) /\ store[CurLive.ref].val = CurLive.val)

\* I-2, whenever no writer holds the row lock: a live unstamped store record is named by exactly one
\* (row, attribute) in the current version; versions in the row's log that name a live record name a
\* record of this row; the current live version names a live, unstamped record.
OneOwner ==
  (\A w \in Writers : wst[w] \notin HoldsLock) =>
    /\ \A k \in Slots : (Live(k) /\ store[k].del = 0) => Cardinality(Namers(k)) = 1
    /\ \A k \in Slots : Live(k) => \A i \in 1..Len(Chain) : Chain[i].ref = k => k \notin fslots
    /\ CurLive.ref # NoSlot =>
         (Live(CurLive.ref) /\ store[CurLive.ref].del = 0 /\ store[CurLive.ref].val = CurLive.val)

\* Store identity (5.6): a slot that holds a live record holds the value every version of the row
\* that names the slot expects.
StoreIdentity ==
  \A k \in Slots : Live(k) => \A i \in 1..Len(Chain) : Chain[i].ref = k => Chain[i].val = store[k].val

TypeOK ==
  /\ wst \in [Writers -> {"idle", "begun", "work", "undo", "partial", "committed", "aborted"}]
  /\ lockOwner \in Writers \cup {"none", "reader"}
  /\ \A k \in Slots : store[k].st \in {"unused", "live", "markdel", "reuse"}
  /\ rpc \in {"idle", "lock", "read", "pin", "resolve", "release", "done"}
  /\ rtry \in 0..MaxRetry
=============================================================================
