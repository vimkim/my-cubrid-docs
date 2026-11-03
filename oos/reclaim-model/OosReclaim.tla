------------------------------ MODULE OosReclaim ------------------------------
(***************************************************************************)
(* Design-level model of how OOS frees slots and decides that a value      *)
(* chain is dead, as implemented at feature/oos-merge dcbf09e4f.           *)
(*                                                                         *)
(* Each setting names one assumption of the current design:               *)
(*   ReuseAt       when another transaction may take a slot that an       *)
(*                 undoable delete freed.  The code is "immediate".       *)
(*   DecideFrom    what the forward-walk requires of the UPDATE whose     *)
(*                 undo image names the chain.  The code is "ended".      *)
(*   HeadIdentity  what a delete compares at the head chunk.  The code is *)
(*                 "stamp"; "none" is the code before CBRD-26950.         *)
(*                                                                         *)
(* Workload Op = "del": T1 deletes a relocated row whose value is the     *)
(* two-chunk chain A (a1 -> a2); vacuum REMOVE frees the forward slot and *)
(* chain A in one sysop.  Op = "upd": T1 updates the row to a new chain B *)
(* and commits or rolls back; the vacuum forward-walk deletes chain A in  *)
(* its own sysop.  T2 is another transaction that can take one free slot. *)
(* At most one disruption happens: a failed delete step, an interrupted   *)
(* block, or a crash.  One slot stands for one page's slot of interest.   *)
(***************************************************************************)
EXTENDS Naturals, Sequences

CONSTANTS Op, ReuseAt, DecideFrom, HeadIdentity

ASSUME /\ Op \in {"del", "upd"}
       /\ ReuseAt \in {"immediate", "final"}
       /\ DecideFrom \in {"ended", "committed"}
       /\ HeadIdentity \in {"none", "stamp"}

Nil == "nil"
Slots == {"fwd", "a1", "a2", "b1"}

Used(own, idx, stamp, nxt) ==
    [st |-> "used", own |-> own, idx |-> idx, stamp |-> stamp, nxt |-> nxt,
     reuse |-> FALSE]
Free(reusable) ==
    [st |-> "free", own |-> "none", idx |-> 0, stamp |-> 0, nxt |-> Nil,
     reuse |-> reusable]

RecFwd == Used("FWD", 0, 1, Nil)     \* REC_NEWHOME of the relocated row
RecA1 == Used("A", 1, 1, "a2")       \* head chunk of chain A
RecA2 == Used("A", 2, 1, Nil)
RecB == Used("B", 1, 2, Nil)         \* chain B written by T1's UPDATE
RecT2 == Used("T2", 1, 2, Nil)       \* T2's record; younger, so a larger stamp

HeadA == "a1"                        \* the stub of chain A: head OID ...
StampA == 1                          \* ... and its identity stamp

VARIABLES
    slot,       \* [Slots -> record]
    row,        \* the heap row: current version, delete mark, removed
    t1,         \* "idle", "active", "committed", "aborted"
    vpc,        \* where the vacuum worker is
    cur,        \* chunk that oos_delete_chain works on
    athead,     \* cur is the head chunk named by the stub
    vlog,       \* undo records of the open vacuum sysop, in log order
    vfreed,     \* slots that the open vacuum sysop freed
    disrupted,  \* the one disruption has happened
    t2slot,     \* slot that T2 took, or "none"
    broken,     \* slots where an undo found another record
    last        \* the last step, in code words (not part of the view)

vars == <<slot, row, t1, vpc, cur, athead, vlog, vfreed, disrupted, t2slot,
          broken, last>>
view == <<slot, row, t1, vpc, cur, athead, vlog, vfreed, disrupted, t2slot,
          broken>>

Init ==
    /\ slot = [s \in Slots |->
                 CASE s = "fwd" -> RecFwd
                   [] s = "a1" -> RecA1
                   [] s = "a2" -> RecA2
                   [] s = "b1" -> Free(FALSE)]
    /\ row = [ver |-> "v0", del |-> FALSE, gone |-> FALSE]
    /\ t1 = "idle"
    /\ vpc = "start"
    /\ cur = Nil
    /\ athead = FALSE
    /\ vlog = <<>>
    /\ vfreed = {}
    /\ disrupted = FALSE
    /\ t2slot = "none"
    /\ broken = {}
    /\ last = "initial state"

FreedSlot == Free(ReuseAt = "immediate")
ChunkPcs == {"rm_chunk", "fw_chunk"}
InSysop == vpc \in {"rm_fwd"} \cup ChunkPcs
T1Ended == t1 \in {"committed", "aborted"}

\* Physical undo in reverse log order: spage_insert_for_recovery writes the
\* old record back into the same slot, over whatever is there now.
RECURSIVE Undo(_, _, _)
Undo(sl, br, lg) ==
    IF lg = <<>> THEN <<sl, br>>
    ELSE LET e == lg[Len(lg)]
         IN Undo([sl EXCEPT ![e.s] = e.rec],
                 IF sl[e.s].st = "used" THEN br \cup {e.s} ELSE br,
                 SubSeq(lg, 1, Len(lg) - 1))

RolledBackRow == [ver |-> "v0", del |-> FALSE, gone |-> row.gone]

Overwrote(newbroken) ==
    IF t2slot \in newbroken \ broken
      THEN "; the undo writes the old record over T2's record in slot " \o t2slot
      ELSE ""

-----------------------------------------------------------------------------
\* T1

T1Delete ==
    /\ Op = "del" /\ t1 = "idle"
    /\ t1' = "active"
    /\ row' = [row EXCEPT !.del = TRUE]
    /\ last' = "T1: heap_delete sets the delete MVCCID; the record keeps the stub of chain A"
    /\ UNCHANGED <<slot, vpc, cur, athead, vlog, vfreed, disrupted, t2slot, broken>>

T1Update ==
    /\ Op = "upd" /\ t1 = "idle"
    /\ t1' = "active"
    /\ row' = [row EXCEPT !.ver = "v1"]
    /\ slot' = [slot EXCEPT !["b1"] = RecB]
    /\ last' = "T1: heap_update writes a new version with new chain B; the undo image keeps the stub of chain A"
    /\ UNCHANGED <<vpc, cur, athead, vlog, vfreed, disrupted, t2slot, broken>>

T1Commit ==
    /\ t1 = "active"
    /\ t1' = "committed"
    /\ last' = "T1 commits"
    /\ UNCHANGED <<slot, row, vpc, cur, athead, vlog, vfreed, disrupted, t2slot, broken>>

T1Abort ==
    /\ t1 = "active"
    /\ t1' = "aborted"
    /\ row' = RolledBackRow
    /\ slot' = IF Op = "upd" THEN [slot EXCEPT !["b1"] = Free(TRUE)] ELSE slot
    /\ last' = "T1 rolls back: the old record with the stub of chain A is restored; the insert of chain B is undone"
    /\ UNCHANGED <<vpc, cur, athead, vlog, vfreed, disrupted, t2slot, broken>>

-----------------------------------------------------------------------------
\* Vacuum: REMOVE (Op = "del")

RemoveStart ==
    /\ Op = "del" /\ vpc = "start" /\ T1Ended
    /\ IF t1 = "committed" /\ ~row.gone
         THEN /\ vpc' = "rm_fwd"
              /\ last' = "vacuum: REMOVE; vacuum_heap_record calls log_sysop_start"
         ELSE /\ vpc' = "done"
              /\ last' = "vacuum: nothing to remove in this block"
    /\ UNCHANGED <<slot, row, t1, cur, athead, vlog, vfreed, disrupted, t2slot, broken>>

RemoveForwardSlot ==
    /\ vpc = "rm_fwd"
    /\ vlog' = Append(vlog, [s |-> "fwd", rec |-> slot["fwd"]])
    /\ slot' = [slot EXCEPT !["fwd"] = FreedSlot]
    /\ vfreed' = vfreed \cup {"fwd"}
    /\ vpc' = "rm_chunk"
    /\ cur' = HeadA
    /\ athead' = TRUE
    /\ last' = "vacuum: spage_vacuum_slot frees the forward slot (reusable), logs it, and releases the forward page latch"
    /\ UNCHANGED <<row, t1, disrupted, t2slot, broken>>

-----------------------------------------------------------------------------
\* Vacuum: forward-walk (Op = "upd")

WalkStart ==
    /\ Op = "upd" /\ vpc = "start" /\ T1Ended
    /\ IF DecideFrom = "committed" /\ t1 = "aborted"
         THEN /\ vpc' = "done"
              /\ UNCHANGED <<cur, athead>>
              /\ last' = "vacuum: forward-walk skips the undo image of the rolled-back UPDATE"
         ELSE /\ vpc' = "fw_chunk"
              /\ cur' = HeadA
              /\ athead' = TRUE
              /\ last' = "vacuum: forward-walk takes the stub of chain A from the UPDATE undo image ("
                          \o (IF DecideFrom = "ended" THEN "the block requires only that T1 ended"
                              ELSE "T1 committed")
                          \o ") and calls log_sysop_start"
    /\ UNCHANGED <<slot, row, t1, vlog, vfreed, disrupted, t2slot, broken>>

-----------------------------------------------------------------------------
\* oos_delete_chain, shared by REMOVE and the forward-walk

HeadAbsent ==
    /\ vpc \in ChunkPcs /\ cur # Nil /\ athead
    /\ slot[cur].st = "free"
    /\ cur' = Nil
    /\ athead' = FALSE
    /\ last' = "vacuum: oos_delete_chain finds head slot " \o cur \o " empty: no-op"
    /\ UNCHANGED <<slot, row, t1, vpc, vlog, vfreed, disrupted, t2slot, broken>>

HeadStale ==
    /\ vpc \in ChunkPcs /\ cur # Nil /\ athead
    /\ slot[cur].st = "used"
    /\ HeadIdentity = "stamp" /\ slot[cur].stamp # StampA
    /\ cur' = Nil
    /\ athead' = FALSE
    /\ last' = "vacuum: oos_delete_chain finds another identity stamp at head slot " \o cur \o ": no-op"
    /\ UNCHANGED <<slot, row, t1, vpc, vlog, vfreed, disrupted, t2slot, broken>>

DeleteChunk ==
    /\ vpc \in ChunkPcs /\ cur # Nil
    /\ slot[cur].st = "used"
    /\ athead => (HeadIdentity = "none" \/ slot[cur].stamp = StampA)
    /\ vlog' = Append(vlog, [s |-> cur, rec |-> slot[cur]])
    /\ slot' = [slot EXCEPT ![cur] = FreedSlot]
    /\ vfreed' = vfreed \cup {cur}
    /\ cur' = slot[cur].nxt
    /\ athead' = FALSE
    /\ last' = "vacuum: oos_delete_chain logs RVOOS_DELETE (undo = whole record), spage_delete frees slot " \o cur \o ", the page latch is released"
    /\ UNCHANGED <<row, t1, vpc, disrupted, t2slot, broken>>

SysopCommit ==
    /\ vpc \in ChunkPcs /\ cur = Nil
    /\ slot' = [s \in Slots |->
                  IF s \in vfreed /\ slot[s].st = "free" THEN Free(TRUE)
                  ELSE slot[s]]
    /\ row' = IF Op = "del" THEN [row EXCEPT !.gone = TRUE] ELSE row
    /\ vlog' = <<>>
    /\ vfreed' = {}
    /\ vpc' = IF Op = "del" THEN "rm_end" ELSE "fw_end"
    /\ last' = "vacuum: log_sysop_commit"
    /\ UNCHANGED <<t1, cur, athead, disrupted, t2slot, broken>>

BlockDone ==
    /\ vpc \in {"rm_end", "fw_end"}
    /\ vpc' = "done"
    /\ last' = "vacuum: the block is marked vacuumed"
    /\ UNCHANGED <<slot, row, t1, cur, athead, vlog, vfreed, disrupted, t2slot, broken>>

-----------------------------------------------------------------------------
\* Disruptions (at most one)

\* A delete step fails before chunk cur: heap_recdes_get_oos_refs, a chunk
\* page fix, or an interrupt.  REMOVE returns the error, so the block is
\* interrupted and retried.  The forward-walk logs and clears an ordinary
\* error and completes the block; ER_INTERRUPTED interrupts the block.
FailStep ==
    /\ ~disrupted /\ vpc \in ChunkPcs /\ cur # Nil
    /\ LET u == Undo(slot, broken, vlog)
       IN /\ slot' = u[1]
          /\ broken' = u[2]
    /\ vlog' = <<>>
    /\ vfreed' = {}
    /\ cur' = Nil
    /\ athead' = FALSE
    /\ disrupted' = TRUE
    /\ \/ /\ Op = "del"
          /\ vpc' = "start"
          /\ last' = "vacuum: a delete step fails; log_sysop_abort undoes the sysop and the block is retried"
                      \o Overwrote(broken')
       \/ /\ Op = "upd"
          /\ vpc' = "done"
          /\ last' = "vacuum: a delete step fails; log_sysop_abort undoes the sysop, the error is cleared and the block completes"
                      \o Overwrote(broken')
       \/ /\ Op = "upd"
          /\ vpc' = "start"
          /\ last' = "vacuum: a delete step is interrupted; log_sysop_abort undoes the sysop and the block is retried"
                      \o Overwrote(broken')
    /\ UNCHANGED <<row, t1, t2slot>>

Interrupt ==
    /\ ~disrupted /\ vpc \in {"rm_end", "fw_end"}
    /\ vpc' = "start"
    /\ disrupted' = TRUE
    /\ last' = "vacuum: interrupted after log_sysop_commit, before the block is marked vacuumed; the block restarts from start_lsa"
    /\ UNCHANGED <<slot, row, t1, cur, athead, vlog, vfreed, t2slot, broken>>

Crash ==
    /\ ~disrupted /\ vpc # "done"
    /\ LET u == IF InSysop THEN Undo(slot, broken, vlog) ELSE <<slot, broken>>
       IN /\ slot' = IF t1 = "active" /\ Op = "upd"
                       THEN [u[1] EXCEPT !["b1"] = Free(TRUE)]
                       ELSE u[1]
          /\ broken' = u[2]
    /\ row' = IF t1 = "active" THEN RolledBackRow ELSE row
    /\ t1' = IF t1 = "active" THEN "aborted" ELSE t1
    /\ vpc' = "start"
    /\ cur' = Nil
    /\ athead' = FALSE
    /\ vlog' = <<>>
    /\ vfreed' = {}
    /\ disrupted' = TRUE
    /\ last' = "crash; restart recovery undoes the open vacuum sysop and T1, then vacuum restarts the block"
                \o Overwrote(broken')
    /\ UNCHANGED t2slot

-----------------------------------------------------------------------------
\* T2: another transaction's INSERT

T2Insert ==
    /\ t2slot = "none"
    /\ \E s \in Slots :
         /\ slot[s].st = "free" /\ slot[s].reuse
         /\ slot' = [slot EXCEPT ![s] = RecT2]
         /\ t2slot' = s
         /\ last' = "T2: an INSERT gets the page latch, spage_find_free_slot hands out free slot " \o s \o ", T2 writes its record and commits"
    /\ UNCHANGED <<row, t1, vpc, cur, athead, vlog, vfreed, disrupted, broken>>

Finished ==
    /\ vpc = "done" /\ T1Ended
    /\ UNCHANGED vars

Next ==
    \/ T1Delete \/ T1Update \/ T1Commit \/ T1Abort
    \/ RemoveStart \/ RemoveForwardSlot \/ WalkStart
    \/ HeadAbsent \/ HeadStale \/ DeleteChunk \/ SysopCommit \/ BlockDone
    \/ FailStep \/ Interrupt \/ Crash
    \/ T2Insert
    \/ Finished

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
\* Properties

\* CBRD-27858: an undo writes the forward record over another record.
ForwardUndoFindsEmptySlot == "fwd" \notin broken

\* CBRD-27781: an undo writes an OOS chunk over another record.
ChunkUndoFindsEmptySlot == broken \cap {"a1", "a2"} = {}

Intact(c) ==
    CASE c = "A" -> slot["a1"] = RecA1 /\ slot["a2"] = RecA2
      [] c = "B" -> slot["b1"] = RecB

\* Chains that the row still needs: the visible version's chain, plus the
\* other version's chain while T1 can still roll back.
LiveRowChains ==
    IF row.gone THEN {}
    ELSE CASE t1 \in {"idle", "aborted"} -> {"A"}
           [] t1 = "active" -> IF Op = "upd" THEN {"A", "B"} ELSE {"A"}
           [] t1 = "committed" -> IF Op = "upd" THEN {"B"} ELSE {}

\* CBRD-27237: vacuum deletes a chain that the row still references.
RowChainIntact == \A c \in LiveRowChains : Intact(c)

\* CBRD-26950 (and the overwrite of CBRD-27858/27781): T2's record is lost.
OtherRecordIntact == t2slot # "none" => slot[t2slot] = RecT2

DeadAtEnd ==
    CASE Op = "upd" /\ t1 = "committed" -> {"A"}
      [] Op = "del" /\ t1 = "committed" -> {"A", "FWD"}
      [] OTHER -> {}

\* A dead chain or forward record is freed once the block is done.
ReclaimedWhenDone ==
    vpc = "done" =>
        \A c \in DeadAtEnd : \A s \in Slots : ~(slot[s].st = "used" /\ slot[s].own = c)

=============================================================================
