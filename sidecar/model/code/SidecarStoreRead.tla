-------------------------- MODULE SidecarStoreRead --------------------------
(***************************************************************************)
(* Sidecar POC code, the read of one store record by its ref.              *)
(*                                                                         *)
(* sidecar_read_store_record_at (storage/sidecar.cpp) reads a store record *)
(* one store page at a time.  A REC_HOME record is copied from its home    *)
(* slot.  For a record that a DELID stamp relocated, the home slot gives   *)
(* the forward OID and the forward slot gives the bytes if it is           *)
(* REC_NEWHOME.  HomeRecheck says what follows:                            *)
(*  "on_miss" (the code since P3 storeread): a REC_NEWHOME copy is the     *)
(*     result; a miss starts over, and a home that forwards again to the   *)
(*     slot that missed reads as absent (a broken store);                  *)
(*  "always" (the code before): the home slot is read again after the      *)
(*     forward slot, and the bytes count only if it still forwards to the  *)
(*     same OID; otherwise the read starts over;                           *)
(*  "no": a broken variant with no recheck.                                *)
(* RereadBound 0 means no bound; otherwise the read reports the record     *)
(* absent after that many rounds.                                          *)
(*                                                                         *)
(* Other actors, each step one page latch in the code:                     *)
(*  - stamps of A and of B (heap_delete_home, MVCC delete of a store       *)
(*    record): in place, or relocated to a free slot (heap_insert_newhome *)
(*    with the home page held, then the home becomes REC_RELOCATION);      *)
(*  - rollback of a stamp: undo in reverse LSA order, the home first, then *)
(*    the newhome insert (heap_rv_undo_insert, spage_delete_for_recovery); *)
(*  - commit of a stamp, and store vacuum of a committed stamp, one step   *)
(*    over both pages because the forward page stays fixed until the      *)
(*    sysop ends (775).                                                    *)
(*                                                                         *)
(* Properties, one TLC run each:                                           *)
(*  ReadReturnsOwnValue  bytes the read returns are A's value.             *)
(*  AbsentOnlyIfRemoved  the read reports A absent only if vacuum removed  *)
(*                       A (a protected reader or a lock holder then gets  *)
(*                       ER_SIDECAR_DANGLING_REF for a live value).        *)
(***************************************************************************)
EXTENDS Naturals, Sequences, TLC

CONSTANTS
    RereadBound,     \* SIDECAR_REREAD_BOUND, 0 = none
    MaxStampsA,      \* stamp attempts on A while the read runs
    MaxStampsB,      \* stamp attempts on B
    HomeRecheck,     \* "on_miss" | "always" | "no", see above
    FwdTypeCheck,    \* the forward slot is read only if it is REC_NEWHOME
    FwdSlotReuse,    \* a forward slot freed by undo or vacuum becomes REC_DELETED_WILL_REUSE
    VacuumAtomic,    \* 775: vacuum holds the forward page until the sysop ends
    FwdSlots         \* names of the free slots a relocation can take

ASSUME RereadBound \in 0..10 /\ MaxStampsA \in 0..10 /\ MaxStampsB \in 0..3
ASSUME HomeRecheck \in {"on_miss", "always", "no"}
ASSUME \A b \in {FwdTypeCheck, FwdSlotReuse, VacuumAtomic} : b \in BOOLEAN

Recs == {"A", "B"}
Home(x) == IF x = "A" THEN "hA" ELSE "hB"
Slots == {"hA", "hB"} \cup FwdSlots

\* slot contents (spage record types)
HomeRec(x) == [t |-> "REC_HOME", v |-> x]
Reloc(f) == [t |-> "REC_RELOCATION", v |-> f]
NewHome(x) == [t |-> "REC_NEWHOME", v |-> x]
Free == [t |-> "REC_DELETED_WILL_REUSE", v |-> "none"]
Marked == [t |-> "REC_MARKDELETED", v |-> "none"]
FreedSlot == IF FwdSlotReuse THEN Free ELSE Marked

VARIABLES
    slot,     \* [Slots -> content]
    st,       \* [Recs -> "live" | "relocating" | "stamped" | "committed" | "removed"]
    fwd,      \* [Recs -> forward slot of the stamp, or "none"]
    undo,     \* [Recs -> undo steps left of a rollback: <<"home", "newhome">> in order]
    stamps,   \* [Recs -> stamp attempts so far]
    removedA, \* vacuum removed A at some point
    pc,       \* the read: "r1" | "r2" | "r3" | "done"
    round,    \* the read's round, from 0
    rfwd,     \* forward OID the read saw in the home slot
    rread,    \* the read copied a REC_NEWHOME record from the forward slot
    rval,     \* the value it copied
    missed,   \* "on_miss": the forward slot of the last round, which held no REC_NEWHOME
    result,   \* "none" | "present" | "absent"
    last

vars == <<slot, st, fwd, undo, stamps, removedA, pc, round, rfwd, rread, rval, missed, result, last>>
View == <<slot, st, fwd, undo, stamps, removedA, pc, round, rfwd, rread, rval, missed, result>>

MaxStamps(x) == IF x = "A" THEN MaxStampsA ELSE MaxStampsB

Init ==
    /\ slot = [s \in Slots |-> CASE s = "hA" -> HomeRec("A") [] s = "hB" -> HomeRec("B") [] OTHER -> Free]
    /\ st = [x \in Recs |-> "live"]
    /\ fwd = [x \in Recs |-> "none"]
    /\ undo = [x \in Recs |-> <<>>]
    /\ stamps = [x \in Recs |-> 0]
    /\ removedA = FALSE
    /\ pc = "r1" /\ round = 0 /\ rfwd = "none" /\ rread = FALSE /\ rval = "none" /\ missed = "none"
    /\ result = "none"
    /\ last = "start"

ReadVars == <<pc, round, rfwd, rread, rval, missed, result>>
\* The home page is X-latched by a stamp between its newhome insert and the home change.
HomeLatched(x) == st[x] = "relocating"

---------------------------------------------------------------------------
\* Stamps, rollbacks, commits and vacuum of A and B.

\* heap_delete_home: the stamped record fits in place (spage_is_updatable).
StampInPlace(x) ==
    /\ st[x] = "live" /\ undo[x] = <<>> /\ stamps[x] < MaxStamps(x)
    /\ st' = [st EXCEPT ![x] = "stamped"]
    /\ stamps' = [stamps EXCEPT ![x] = @ + 1]
    /\ last' = "a transaction stamps " \o x \o " in place (heap_delete_home)"
    /\ UNCHANGED <<slot, fwd, undo, removedA, ReadVars>>

\* heap_delete_home: REC_NEWHOME, heap_insert_newhome into a free slot, home page held.
StampNewHome(x, f) ==
    /\ st[x] = "live" /\ undo[x] = <<>> /\ stamps[x] < MaxStamps(x)
    /\ slot[f] = Free
    /\ slot' = [slot EXCEPT ![f] = NewHome(x)]
    /\ st' = [st EXCEPT ![x] = "relocating"]
    /\ fwd' = [fwd EXCEPT ![x] = f]
    /\ stamps' = [stamps EXCEPT ![x] = @ + 1]
    /\ last' = "a transaction stamps " \o x \o ", which no longer fits: heap_insert_newhome puts it in slot " \o f
    /\ UNCHANGED <<undo, removedA, ReadVars>>

\* heap_delete_home: the home slot becomes REC_RELOCATION; the home page is released.
StampHome(x) ==
    /\ st[x] = "relocating"
    /\ slot' = [slot EXCEPT ![Home(x)] = Reloc(fwd[x])]
    /\ st' = [st EXCEPT ![x] = "stamped"]
    /\ last' = "the stamp makes " \o Home(x) \o " REC_RELOCATION to " \o fwd[x]
    /\ UNCHANGED <<fwd, undo, stamps, removedA, ReadVars>>

\* log_abort_local / statement rollback: log_rollback undoes in reverse LSA order.
Rollback(x) ==
    /\ st[x] = "stamped"
    /\ undo' = [undo EXCEPT ![x] = IF fwd[x] = "none" THEN <<"home">> ELSE <<"home", "newhome">>]
    /\ st' = [st EXCEPT ![x] = "live"]
    /\ last' = "the stamping transaction of " \o x \o " rolls back"
    /\ UNCHANGED <<slot, fwd, stamps, removedA, ReadVars>>

UndoStep(x) ==
    /\ undo[x] # <<>>
    /\ LET u == Head(undo[x]) IN
       /\ slot' = IF u = "home" THEN [slot EXCEPT ![Home(x)] = HomeRec(x)]
                  ELSE [slot EXCEPT ![fwd[x]] = FreedSlot]
       /\ fwd' = IF u = "newhome" THEN [fwd EXCEPT ![x] = "none"] ELSE fwd
       /\ last' = IF u = "home" THEN "undo writes " \o x \o " back into " \o Home(x)
                  ELSE "undo of the newhome insert frees slot " \o fwd[x] \o " (spage_delete_for_recovery)"
    /\ undo' = [undo EXCEPT ![x] = Tail(@)]
    /\ UNCHANGED <<st, stamps, removedA, ReadVars>>

Commit(x) ==
    /\ st[x] = "stamped"
    /\ st' = [st EXCEPT ![x] = "committed"]
    /\ last' = "the stamping transaction of " \o x \o " commits"
    /\ UNCHANGED <<slot, fwd, undo, stamps, removedA, ReadVars>>

\* vacuum_heap_record: the home slot is never reused in the non-reuse store
\* (REC_MARKDELETED); the forward slot is vacuumed with reuse (vacuum.c).
VacuumHome(x) ==
    /\ st[x] = "committed"
    /\ slot' = IF fwd[x] = "none" \/ VacuumAtomic
               THEN [s \in Slots |-> IF s = Home(x) THEN Marked
                                     ELSE IF s = fwd[x] THEN FreedSlot ELSE slot[s]]
               ELSE [slot EXCEPT ![Home(x)] = Marked]
    /\ st' = [st EXCEPT ![x] = "removed"]
    /\ fwd' = IF VacuumAtomic THEN [fwd EXCEPT ![x] = "none"] ELSE fwd
    /\ removedA' = (removedA \/ x = "A")
    /\ last' = "store vacuum removes " \o x
    /\ UNCHANGED <<undo, stamps, ReadVars>>

\* Without 775 the forward slot is freed in a later step.
VacuumForward(x) ==
    /\ ~VacuumAtomic /\ st[x] = "removed" /\ fwd[x] # "none"
    /\ slot' = [slot EXCEPT ![fwd[x]] = FreedSlot]
    /\ fwd' = [fwd EXCEPT ![x] = "none"]
    /\ last' = "store vacuum frees the forward slot " \o fwd[x] \o " of " \o x
    /\ UNCHANGED <<st, undo, stamps, removedA, ReadVars>>

---------------------------------------------------------------------------
\* The read of A, sidecar_read_store_record_at.

R1 ==
    /\ pc = "r1" /\ ~HomeLatched("A")
    /\ LET c == slot["hA"] IN
       CASE c.t = "REC_HOME" ->
              /\ result' = "present" /\ rval' = c.v /\ pc' = "done"
              /\ UNCHANGED <<rfwd, rread, round>>
              /\ last' = "the read finds REC_HOME in hA and copies it"
         [] c.t = "REC_RELOCATION" /\ c.v = missed ->
              /\ result' = "absent" /\ pc' = "done"
              /\ UNCHANGED <<rfwd, rread, rval, round>>
              /\ last' = "the read finds hA forwarding again to " \o c.v \o ", which held nothing: SIDECAR_READ_ABSENT"
         [] c.t = "REC_RELOCATION" ->
              /\ rfwd' = c.v /\ pc' = "r2"
              /\ UNCHANGED <<result, rval, rread, round>>
              /\ last' = "the read finds hA REC_RELOCATION to " \o c.v \o " and releases the home page"
         [] OTHER ->
              /\ result' = "absent" /\ pc' = "done"
              /\ UNCHANGED <<rfwd, rread, rval, round>>
              /\ last' = "the read finds hA " \o c.t \o ": SIDECAR_READ_ABSENT"
    /\ UNCHANGED <<slot, st, fwd, undo, stamps, removedA, missed>>

Again ==
    IF RereadBound = 0 \/ round + 1 < RereadBound
    THEN /\ round' = (IF RereadBound = 0 THEN round ELSE round + 1) /\ pc' = "r1" /\ result' = "none"
    ELSE /\ round' = round /\ pc' = "done" /\ result' = "absent"

R2 ==
    /\ pc = "r2"
    /\ LET c == slot[rfwd]
           ok == c.t = "REC_NEWHOME" \/ (~FwdTypeCheck /\ c.t \in {"REC_NEWHOME", "REC_HOME"})
       IN /\ rread' = ok
          /\ rval' = IF ok THEN c.v ELSE "none"
          /\ IF ok /\ HomeRecheck = "on_miss"
             THEN /\ result' = "present" /\ pc' = "done" /\ UNCHANGED <<round, missed>>
                  /\ last' = "the read copies the REC_NEWHOME record in " \o rfwd \o ", which is " \o c.v \o ", and returns it"
             ELSE IF ~ok /\ HomeRecheck = "on_miss"
             THEN /\ missed' = rfwd /\ Again
                  /\ last' = "the read finds " \o rfwd \o " " \o c.t \o " and starts over"
             ELSE /\ pc' = IF HomeRecheck = "always" THEN "r3" ELSE "r3skip"
                  /\ UNCHANGED <<round, result, missed>>
                  /\ last' = IF ok THEN "the read copies the REC_NEWHOME record in " \o rfwd \o ", which is " \o c.v
                             ELSE "the read finds " \o rfwd \o " " \o c.t \o " and copies nothing"
    /\ UNCHANGED <<slot, st, fwd, undo, stamps, removedA, rfwd>>

R3 ==
    /\ pc = "r3" /\ ~HomeLatched("A")
    /\ LET same == rread /\ slot["hA"] = Reloc(rfwd) IN
       IF same
       THEN /\ result' = "present" /\ pc' = "done" /\ UNCHANGED round
            /\ last' = "the read finds hA still REC_RELOCATION to " \o rfwd \o " and returns the bytes it copied"
       ELSE /\ Again
            /\ last' = "the read finds hA changed and starts over"
    /\ UNCHANGED <<slot, st, fwd, undo, stamps, removedA, rfwd, rread, rval, missed>>

\* Broken variant: no home recheck.
R3Skip ==
    /\ pc = "r3skip"
    /\ IF rread
       THEN /\ result' = "present" /\ pc' = "done" /\ UNCHANGED round
       ELSE Again
    /\ last' = "the read does not read hA again"
    /\ UNCHANGED <<slot, st, fwd, undo, stamps, removedA, rfwd, rread, rval, missed>>

Done == pc = "done" /\ UNCHANGED vars

Next ==
    \/ \E x \in Recs : \/ StampInPlace(x) \/ StampHome(x) \/ Rollback(x) \/ UndoStep(x)
                       \/ Commit(x) \/ VacuumHome(x) \/ VacuumForward(x)
                       \/ \E f \in FwdSlots : StampNewHome(x, f)
    \/ R1 \/ R2 \/ R3 \/ R3Skip
    \/ Done

Spec == Init /\ [][Next]_vars

---------------------------------------------------------------------------
ReadReturnsOwnValue == result = "present" => rval = "A"
AbsentOnlyIfRemoved == result = "absent" => removedA
=============================================================================
