--------------------------- MODULE OosReclaimRetry ---------------------------
(***************************************************************************)
(* Decision 3: how the D3 reclaimer deletes a dead chain so that a rerun   *)
(* after a crash or an error converges.                                    *)
(*                                                                         *)
(* Chain A is a1 -> a2 -> a3.  Its stub and its heap record are already    *)
(* gone, so no reader can reach it.  The reclaimer runs after commit and   *)
(* each delete is redo-only, so a freed slot is reusable at once.  T2 can *)
(* take one free slot.  At most one disruption happens: a crash, after     *)
(* which recovery runs the postpone again from the head, or an error in a  *)
(* delete step.                                                            *)
(*                                                                         *)
(* Order      "head_first": delete each chunk and follow its next link    *)
(*            "tail_first": read the chain from the head, then delete it  *)
(*            from the tail, the head last                                 *)
(* LinkStamp  TRUE: a next link also holds the next chunk's identity      *)
(*            stamp, and every step compares it; FALSE: only the stub's   *)
(*            head stamp is compared (the code)                            *)
(* OnError    "discard": the error of a postpone step is dropped and the  *)
(*            reclaim stops; "rerun": the reclaim runs again from the head *)
(***************************************************************************)
EXTENDS Naturals, Sequences

CONSTANTS Order, LinkStamp, OnError

ASSUME /\ Order \in {"head_first", "tail_first"}
       /\ LinkStamp \in BOOLEAN
       /\ OnError \in {"discard", "rerun"}

Nil == "nil"
Slots == {"a1", "a2", "a3"}

Rec(own, stamp, nxt, nstamp) ==
    [st |-> "used", own |-> own, stamp |-> stamp, nxt |-> nxt, nstamp |-> nstamp]
Free == [st |-> "free", own |-> "none", stamp |-> 0, nxt |-> Nil, nstamp |-> 0]

RecA(s) == CASE s = "a1" -> Rec("A", 1, "a2", 1)
             [] s = "a2" -> Rec("A", 1, "a3", 1)
             [] s = "a3" -> Rec("A", 1, Nil, 0)
RecT2 == Rec("T2", 2, Nil, 0)        \* younger record, so a larger stamp

VARIABLES
    slot,       \* [Slots -> record]
    rpc,        \* "start", "run", "done"
    cur,        \* head_first: the chunk to delete next
    list,       \* tail_first: <<[s, stamp]>> read from the head
    pos,        \* tail_first: list index to delete next
    disrupted,
    t2at,       \* slot that T2 took, or "none"
    last

vars == <<slot, rpc, cur, list, pos, disrupted, t2at, last>>
view == <<slot, rpc, cur, list, pos, disrupted, t2at>>

Init ==
    /\ slot = [s \in Slots |-> RecA(s)]
    /\ rpc = "start"
    /\ cur = Nil
    /\ list = <<>>
    /\ pos = 0
    /\ disrupted = FALSE
    /\ t2at = "none"
    /\ last = "initial state"

HeadValid == slot["a1"].st = "used" /\ slot["a1"].stamp = 1

\* May the walk step from record r to slot n?
Follows(r, n) ==
    /\ n # Nil
    /\ slot[n].st = "used"
    /\ LinkStamp => slot[n].stamp = r.nstamp

RECURSIVE Walk(_, _)
Walk(s, acc) ==
    LET r == slot[s]
        acc2 == Append(acc, [s |-> s, stamp |-> r.stamp])
    IN IF Follows(r, r.nxt) THEN Walk(r.nxt, acc2) ELSE acc2

Start ==
    /\ rpc = "start"
    /\ IF ~HeadValid
         THEN /\ rpc' = "done"
              /\ UNCHANGED <<cur, list, pos>>
              /\ last' = "reclaimer: the head is empty or has another stamp; nothing to do"
         ELSE IF Order = "head_first"
           THEN /\ rpc' = "run"
                /\ cur' = "a1"
                /\ UNCHANGED <<list, pos>>
                /\ last' = "reclaimer: the head matches the stub; delete from the head"
           ELSE /\ rpc' = "run"
                /\ list' = Walk("a1", <<>>)
                /\ pos' = Len(Walk("a1", <<>>))
                /\ UNCHANGED cur
                /\ last' = "reclaimer: the head matches the stub; read the chain ("
                           \o (IF Len(Walk("a1", <<>>)) = 3 THEN "3" ELSE IF Len(Walk("a1", <<>>)) = 2 THEN "2" ELSE "1")
                           \o " chunks) and delete from the tail"
    /\ UNCHANGED <<slot, disrupted, t2at>>

StepHeadFirst ==
    /\ Order = "head_first" /\ rpc = "run"
    /\ LET r == slot[cur]
       IN /\ slot' = [slot EXCEPT ![cur] = Free]
          /\ IF Follows(r, r.nxt)
               THEN /\ cur' = r.nxt
                    /\ rpc' = "run"
               ELSE /\ cur' = Nil
                    /\ rpc' = "done"
          /\ last' = "reclaimer: delete " \o cur \o " (redo-only), then follow its next link"
    /\ UNCHANGED <<list, pos, disrupted, t2at>>

StepTailFirst ==
    /\ Order = "tail_first" /\ rpc = "run"
    /\ LET e == list[pos]
           ok == slot[e.s].st = "used" /\ (LinkStamp => slot[e.s].stamp = e.stamp)
       IN /\ slot' = IF ok THEN [slot EXCEPT ![e.s] = Free] ELSE slot
          /\ last' = IF ok THEN "reclaimer: delete " \o e.s \o " (redo-only)"
                     ELSE "reclaimer: " \o e.s \o " no longer holds the chunk; skip"
    /\ pos' = pos - 1
    /\ rpc' = IF pos = 1 THEN "done" ELSE "run"
    /\ UNCHANGED <<cur, list, disrupted, t2at>>

Fail ==
    /\ ~disrupted /\ rpc = "run"
    /\ rpc' = IF OnError = "discard" THEN "done" ELSE "start"
    /\ disrupted' = TRUE
    /\ last' = IF OnError = "discard"
                 THEN "reclaimer: a delete step fails; the postpone error is dropped and the reclaim stops"
                 ELSE "reclaimer: a delete step fails; the reclaim runs again from the head"
    /\ UNCHANGED <<slot, cur, list, pos, t2at>>

Crash ==
    /\ ~disrupted /\ rpc = "run"
    /\ rpc' = "start"
    /\ disrupted' = TRUE
    /\ last' = "crash; recovery runs the reclaim postpone again from the head"
    /\ UNCHANGED <<slot, cur, list, pos, t2at>>

T2Insert ==
    /\ t2at = "none"
    /\ \E s \in Slots :
         /\ slot[s].st = "free"
         /\ slot' = [slot EXCEPT ![s] = RecT2]
         /\ t2at' = s
         /\ last' = "T2: an INSERT takes free slot " \o s \o " and commits"
    /\ UNCHANGED <<rpc, cur, list, pos, disrupted>>

Finished ==
    /\ rpc = "done"
    /\ UNCHANGED vars

Next == Start \/ StepHeadFirst \/ StepTailFirst \/ Fail \/ Crash \/ T2Insert \/ Finished

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
\* Properties

OtherRecordIntact == t2at # "none" => slot[t2at] = RecT2
ReclaimedWhenDone == rpc = "done" => \A s \in Slots : slot[s].own # "A"

\* Reasons.  The chunks that remain always form a prefix of the chain, so a
\* rerun from the head finds every one of them.
RemainingIsPrefix ==
    /\ slot["a2"].own = "A" => slot["a1"].own = "A"
    /\ slot["a3"].own = "A" => slot["a2"].own = "A"
\* Every list entry still to delete holds the chunk read for it.
ListStillNamesChain ==
    (Order = "tail_first" /\ rpc = "run") =>
        \A i \in 1..pos : slot[list[i].s].own = "A"

=============================================================================
