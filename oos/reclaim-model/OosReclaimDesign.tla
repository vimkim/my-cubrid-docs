--------------------------- MODULE OosReclaimDesign ---------------------------
(***************************************************************************)
(* The chosen OOS reclaim design in one model, so that the decisions are  *)
(* checked together:                                                      *)
(*   D3   a chunk delete is never undone; the decision is a postponed     *)
(*        reclaim intent and the chunks are deleted after commit,         *)
(*        redo-only, so a freed slot is reusable at once                  *)
(*   no LSA reclaim gate: an empty page may be deallocated at once        *)
(*   A'   an UPDATE that drops a chain leaves a postpone; it runs after   *)
(*        LOG_COMMIT_WITH_POSTPONE and appends RVOOS_NOTIFY_VACUUM        *)
(*   the reclaimer reads the chain from the head, deletes it from the     *)
(*        tail with the head last, compares link stamps, and reruns       *)
(*        after an error or a crash                                       *)
(*                                                                        *)
(* The row starts at version v0 with chain A (a1 -> a2).  T1 updates it:  *)
(* "assign" writes chain B (b1) and drops A; "reuse" leaves the OOS       *)
(* attribute unassigned and keeps the stub of A (OOS-CONTEXT section 3).  *)
(* T1 may undo the UPDATE with a statement rollback, commit, or roll back.*)
(* Then T3 may delete the row.  Reader R takes one snapshot and later     *)
(* reads the chain of the version that the snapshot sees.  Vacuum         *)
(* consumes the notification and removes the deleted row; both run the    *)
(* same reclaimer.  T2 may insert one record into a free or deallocated   *)
(* slot.  Each slot is on its own page.  At most one disruption happens:  *)
(* a reclaimer error or a crash.                                          *)
(*                                                                        *)
(* The settings undo one decision each, to show that the checks can fail: *)
(*   Horizon    FALSE: vacuum ignores R's snapshot                        *)
(*   Notify     "undo_image": vacuum drops A when an UPDATE undo image    *)
(*              exists (the forward-walk), instead of A'                  *)
(*   LinkStamp  FALSE: the reclaimer follows next links by OID only       *)
(*                                                                        *)
(* Two settings replace a decision with an alternative instead:           *)
(*   Notify     "head_mark" (B3): the UPDATE writes T1's delete MVCCID    *)
(*              into the head of chain A with an undoable log record;     *)
(*              every rollback undoes it.  Vacuum reads the head when it  *)
(*              processes the block and starts the reclaimer if the mark  *)
(*              is there.  No postpone and no RVOOS_NOTIFY_VACUUM.        *)
(*   RemoveOrder "reclaim_first" (B2): vacuum REMOVE reclaims the chain   *)
(*              first and removes the heap record after the reclaimer     *)
(*              ends.  No postpone: after an error or a crash the vacuum  *)
(*              job runs again from the heap record that is still there.  *)
(***************************************************************************)
EXTENDS Naturals, Sequences

CONSTANTS Horizon, Notify, LinkStamp, RemoveOrder

ASSUME /\ Horizon \in BOOLEAN
       /\ Notify \in {"postpone", "undo_image", "head_mark"}
       /\ LinkStamp \in BOOLEAN
       /\ RemoveOrder \in {"postpone", "reclaim_first"}

Nil == "nil"
Slots == {"a1", "a2", "b1"}

Rec(own, stamp, nxt, nstamp) ==
    [st |-> "used", own |-> own, stamp |-> stamp, nxt |-> nxt, nstamp |-> nstamp]
Empty(st) == [st |-> st, own |-> "none", stamp |-> 0, nxt |-> Nil, nstamp |-> 0]

RecA1 == Rec("A", 1, "a2", 1)
RecA2 == Rec("A", 1, Nil, 0)
RecB == Rec("B", 2, Nil, 0)
RecT2 == Rec("T2", 3, Nil, 0)
HeadOf(c) == IF c = "A" THEN [s |-> "a1", stamp |-> 1] ELSE [s |-> "b1", stamp |-> 2]

VARIABLES
    slot,        \* [Slots -> record]; st is "used", "free", "dealloc", "unused"
    t1,          \* "idle", "active", "pp", "committed", "aborted"
    kind,        \* "none", "assign", "reuse"
    live,        \* T1's UPDATE has not been rolled back
    ppLive,      \* A': the postpone that names chain A is not cancelled
    notified,    \* RVOOS_NOTIFY_VACUUM for chain A is in the log
    mark,        \* B3: the head of chain A carries T1's delete MVCCID
    t3,          \* "idle", "active", "committed", "aborted"
    gone,        \* vacuum removed the heap record
    r,           \* "none", "active", "done"
    rseesT1,     \* R's snapshot sees T1's commit
    rseesT3,     \* R's snapshot sees T3's commit
    rbroken,     \* R found its chain damaged
    vdrop,       \* "pending", "done": vacuum's work for T1's UPDATE
    rc,          \* the reclaimer: [c, pc, list, pos]
    vjob,        \* B2: the REMOVE job, "none", "reclaim", "done"
    disrupted,
    t2at,        \* slot that T2 took, or "none"
    last

vars == <<slot, t1, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1,
          rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at, last>>
view == <<slot, t1, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1,
          rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

\* stop: the last walk stopped at a slot that holds another record.
Idle == [c |-> "none", pc |-> "idle", list |-> <<>>, pos |-> 0, stop |-> FALSE]

Init ==
    /\ slot = [s \in Slots |-> CASE s = "a1" -> RecA1
                                 [] s = "a2" -> RecA2
                                 [] s = "b1" -> Empty("unused")]
    /\ t1 = "idle"
    /\ kind = "none"
    /\ live = FALSE
    /\ ppLive = FALSE
    /\ notified = FALSE
    /\ mark = FALSE
    /\ t3 = "idle"
    /\ gone = FALSE
    /\ r = "none"
    /\ rseesT1 = FALSE
    /\ rseesT3 = FALSE
    /\ rbroken = FALSE
    /\ vdrop = "pending"
    /\ rc = Idle
    /\ vjob = "none"
    /\ disrupted = FALSE
    /\ t2at = "none"
    /\ last = "initial state"

T1Committed == t1 \in {"pp", "committed"}   \* logtb_complete_mvcc runs before the postpones
T1Ended == t1 \in {"committed", "aborted"}
\* The chain of the newest committed version.
CommittedChain == IF T1Committed /\ kind = "assign" /\ live THEN "B" ELSE "A"
\* The chain of the version that R's snapshot sees.
RChain ==
    IF rseesT3 THEN "none"
    ELSE IF rseesT1 /\ kind = "assign" /\ live THEN "B" ELSE "A"

Intact(c) ==
    IF c = "A" THEN slot["a1"] = RecA1 /\ slot["a2"] = RecA2
    ELSE slot["b1"] = RecB

\* T1's own insert of chain B is undone (statement rollback, rollback, crash).
UndoInsertB == [slot EXCEPT !["b1"] = Empty("free")]

-----------------------------------------------------------------------------
\* T1

T1Update ==
    /\ t1 = "idle"
    /\ \E k \in {"assign", "reuse"} :
         /\ kind' = k
         /\ slot' = IF k = "assign" THEN [slot EXCEPT !["b1"] = RecB] ELSE slot
         /\ ppLive' = (k = "assign" /\ Notify = "postpone")
         /\ mark' = (k = "assign" /\ Notify = "head_mark")
         /\ last' = IF k = "assign"
                      THEN "T1: UPDATE assigns the OOS attribute: new chain B"
                           \o (IF Notify = "postpone" THEN "; A' leaves a postpone that names chain A" ELSE "")
                           \o (IF Notify = "head_mark" THEN "; the head of chain A gets T1's delete MVCCID (undoable)" ELSE "")
                      ELSE "T1: UPDATE leaves the OOS attribute unassigned and keeps the stub of chain A"
    /\ t1' = "active"
    /\ live' = TRUE
    /\ UNCHANGED <<notified, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

T1StatementRollback ==
    /\ t1 = "active" /\ live
    /\ live' = FALSE
    /\ ppLive' = FALSE
    /\ mark' = FALSE
    /\ slot' = IF kind = "assign" THEN UndoInsertB ELSE slot
    /\ last' = "T1: a statement rollback undoes the UPDATE (and the insert of chain B)"
               \o (CASE Notify = "postpone" -> "; the postpone is cancelled"
                     [] Notify = "head_mark" -> "; the head mark is undone"
                     [] OTHER -> "")
    /\ UNCHANGED <<t1, kind, notified, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

T1Commit ==
    /\ t1 = "active"
    /\ t1' = IF Notify = "postpone" THEN "pp" ELSE "committed"
    /\ last' = IF Notify = "postpone"
                 THEN "T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed"
                 ELSE "T1 commits"
    /\ UNCHANGED <<slot, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

T1RunPostpone ==
    /\ t1 = "pp"
    /\ t1' = "committed"
    /\ notified' = ppLive
    /\ last' = IF ppLive THEN "T1: the postpone appends RVOOS_NOTIFY_VACUUM for chain A; LOG_COMMIT"
               ELSE "T1: no live postpone; LOG_COMMIT"
    /\ UNCHANGED <<slot, kind, live, ppLive, mark, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

T1Abort ==
    /\ t1 = "active"
    /\ t1' = "aborted"
    /\ slot' = IF kind = "assign" /\ live THEN UndoInsertB ELSE slot
    /\ live' = FALSE
    /\ ppLive' = FALSE
    /\ mark' = FALSE
    /\ last' = "T1 rolls back; the row keeps chain A"
    /\ UNCHANGED <<kind, notified, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

-----------------------------------------------------------------------------
\* T3 deletes the row after T1 ended.

T3Delete ==
    /\ t3 = "idle" /\ T1Ended
    /\ t3' = "active"
    /\ last' = "T3: heap_delete sets the delete MVCCID of the row"
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

T3Commit ==
    /\ t3 = "active"
    /\ t3' = "committed"
    /\ last' = "T3 commits"
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

T3Abort ==
    /\ t3 = "active"
    /\ t3' = "aborted"
    /\ last' = "T3 rolls back"
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

-----------------------------------------------------------------------------
\* Reader R

RSnapshot ==
    /\ r = "none"
    /\ r' = "active"
    /\ rseesT1' = T1Committed
    /\ rseesT3' = (t3 = "committed")
    /\ last' = "R takes a snapshot"
               \o (CASE T1Committed -> " after T1's commit"
                     [] t1 = "aborted" -> " after T1's rollback"
                     [] OTHER -> " before T1's commit")
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, t3, gone, rbroken, vdrop, rc, vjob, disrupted, t2at>>

RRead ==
    /\ r = "active"
    /\ r' = "done"
    /\ rbroken' = (RChain # "none" /\ ~Intact(RChain))
    /\ last' = "R reads chain " \o RChain \o " of the version its snapshot sees"
               \o (IF RChain # "none" /\ ~Intact(RChain) THEN ": oos_read fails (ER_HEAP_OOS_CORRUPTED_RECORD)" ELSE "")
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, t3, gone, rseesT1, rseesT3, vdrop, rc, vjob, disrupted, t2at>>

\* oldest_visible: vacuum may treat T1's or T3's change as dead only when no
\* active snapshot is older than that commit.
SafeFor(seen) == Horizon => ~(r = "active" /\ ~seen)

-----------------------------------------------------------------------------
\* Vacuum

DropDecided ==
    CASE Notify = "postpone" -> notified
      [] Notify = "head_mark" -> mark
      [] OTHER -> T1Ended /\ kind # "none"      \* any UPDATE undo image names chain A

ConsumeDrop ==
    /\ vdrop = "pending" /\ T1Ended /\ rc.pc = "idle"
    /\ SafeFor(rseesT1)
    /\ vdrop' = "done"
    /\ IF DropDecided
         THEN /\ rc' = [c |-> "A", pc |-> "start", list |-> <<>>, pos |-> 0, stop |-> FALSE]
              /\ last' = CASE Notify = "postpone" ->
                               "vacuum: consumes RVOOS_NOTIFY_VACUUM and starts the reclaimer for chain A"
                          [] Notify = "head_mark" ->
                               "vacuum: processes T1's head mark; the head of chain A still carries it, so start the reclaimer"
                          [] OTHER ->
                               "vacuum: the forward-walk finds T1's UPDATE undo image and starts the reclaimer for chain A"
         ELSE /\ UNCHANGED rc
              /\ last' = "vacuum: nothing to drop for T1"
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1, rseesT3, rbroken, vjob, disrupted, t2at>>

\* REMOVE: in one sysop, remove the heap record and leave a postponed reclaim
\* intent; log_sysop_commit runs the postpone.
Remove ==
    /\ RemoveOrder = "postpone"
    /\ t3 = "committed" /\ ~gone /\ rc.pc = "idle" /\ vdrop = "done"
    /\ SafeFor(rseesT3)
    /\ gone' = TRUE
    /\ rc' = [c |-> CommittedChain, pc |-> "start", list |-> <<>>, pos |-> 0, stop |-> FALSE]
    /\ last' = "vacuum: REMOVE removes the heap record; log_sysop_commit runs the reclaim intent for chain " \o CommittedChain
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, t3, r, rseesT1, rseesT3, rbroken, vdrop, vjob, disrupted, t2at>>

\* B2: reclaim the chain that the dead heap record names, then remove the
\* record.  The vacuum job is not finished until the record is gone, so an
\* error or a crash makes it run again from the record.
RemoveReclaimFirst ==
    /\ RemoveOrder = "reclaim_first"
    /\ t3 = "committed" /\ ~gone /\ vjob = "none" /\ rc.pc = "idle" /\ vdrop = "done"
    /\ SafeFor(rseesT3)
    /\ vjob' = "reclaim"
    /\ rc' = [c |-> CommittedChain, pc |-> "start", list |-> <<>>, pos |-> 0, stop |-> FALSE]
    /\ last' = "vacuum: the heap record is dead; reclaim chain " \o CommittedChain \o " before removing the record"
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, disrupted, t2at>>

RemoveRecordAfterReclaim ==
    /\ vjob = "reclaim" /\ rc.pc = "idle"
    /\ gone' = TRUE
    /\ vjob' = "done"
    /\ last' = "vacuum: the reclaimer ended; remove the heap record"
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, t3, r, rseesT1, rseesT3, rbroken, vdrop, rc, disrupted, t2at>>

Follows(rec, n) ==
    /\ n # Nil
    /\ slot[n].st = "used"
    /\ LinkStamp => slot[n].stamp = rec.nstamp

RECURSIVE Walk(_, _)
Walk(s, acc) ==
    LET x == slot[s]
        acc2 == Append(acc, [s |-> s, stamp |-> x.stamp])
    IN IF Follows(x, x.nxt) THEN Walk(x.nxt, acc2) ELSE acc2

ReclaimStart ==
    /\ rc.pc = "start"
    /\ LET h == HeadOf(rc.c)
           w == Walk(h.s, <<>>)
           n == slot[w[Len(w)].s].nxt
       IN IF slot[h.s].st = "used" /\ slot[h.s].stamp = h.stamp
            THEN /\ rc' = [rc EXCEPT !.pc = "run", !.list = w, !.pos = Len(w),
                                     !.stop = (n # Nil /\ slot[n].st = "used" /\ slot[n].own # rc.c)]
                 /\ last' = "reclaimer: the head of chain " \o rc.c \o " matches; read the chain and delete from the tail"
            ELSE /\ rc' = Idle
                 /\ last' = "reclaimer: the head of chain " \o rc.c \o " is gone or reused; nothing to do"
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, vjob, disrupted, t2at>>

ReclaimStep ==
    /\ rc.pc = "run"
    /\ LET e == rc.list[rc.pos]
           ok == slot[e.s].st = "used" /\ (LinkStamp => slot[e.s].stamp = e.stamp)
       IN /\ slot' = IF ok THEN [slot EXCEPT ![e.s] = Empty("free")] ELSE slot
          /\ last' = IF ok THEN "reclaimer: delete slot " \o e.s \o " (redo-only); the slot is reusable at once"
                     ELSE "reclaimer: slot " \o e.s \o " no longer holds the chunk; skip"
    /\ rc' = IF rc.pos = 1 THEN Idle ELSE [rc EXCEPT !.pos = @ - 1]
    /\ UNCHANGED <<t1, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, vjob, disrupted, t2at>>

ReclaimFail ==
    /\ ~disrupted /\ rc.pc = "run"
    /\ rc' = [rc EXCEPT !.pc = "start", !.list = <<>>, !.pos = 0]
    /\ disrupted' = TRUE
    /\ last' = "reclaimer: a delete step fails; the reclaim runs again from the head"
    /\ UNCHANGED <<slot, t1, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, vjob, t2at>>

-----------------------------------------------------------------------------
\* Crash and restart recovery

Crash ==
    /\ ~disrupted
    /\ ~(T1Ended /\ t3 \in {"committed", "aborted"} /\ gone /\ rc.pc = "idle")
    /\ t1' = CASE t1 = "active" -> "aborted"
               [] t1 = "pp" -> "committed"
               [] OTHER -> t1
    /\ notified' = IF t1 = "pp" THEN ppLive ELSE notified
    /\ slot' = IF t1 = "active" /\ kind = "assign" /\ live THEN UndoInsertB ELSE slot
    /\ live' = IF t1 = "active" THEN FALSE ELSE live
    /\ ppLive' = IF t1 = "active" THEN FALSE ELSE ppLive
    /\ mark' = IF t1 = "active" THEN FALSE ELSE mark
    /\ t3' = IF t3 = "active" THEN "aborted" ELSE t3
    /\ r' = IF r = "active" THEN "done" ELSE r
    \* B2: the interrupted REMOVE job runs again from the heap record.
    /\ rc' = CASE vjob = "reclaim" -> [c |-> CommittedChain, pc |-> "start", list |-> <<>>, pos |-> 0, stop |-> FALSE]
               [] rc.pc = "run" -> [rc EXCEPT !.pc = "start", !.list = <<>>, !.pos = 0]
               [] OTHER -> rc
    /\ disrupted' = TRUE
    /\ last' = "crash; recovery undoes active transactions, finishes T1's postpones, and the reclaimer reruns from the head"
               \o (IF vjob = "reclaim" THEN " (the interrupted vacuum job runs again)" ELSE "")
    /\ UNCHANGED <<kind, gone, rseesT1, rseesT3, rbroken, vdrop, vjob, t2at>>

-----------------------------------------------------------------------------
\* Other activity

T2Insert ==
    /\ t2at = "none"
    /\ \E s \in Slots :
         /\ slot[s].st \in {"free", "dealloc"}
         /\ slot' = [slot EXCEPT ![s] = RecT2]
         /\ t2at' = s
         /\ last' = "T2: an INSERT takes slot " \o s \o (IF slot[s].st = "dealloc" THEN " on a reallocated page" ELSE "") \o " and commits"
    /\ UNCHANGED <<t1, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted>>

\* oos_reclaim_empty_pages without the LSA gate.
Dealloc ==
    /\ \E s \in Slots :
         /\ slot[s].st = "free"
         /\ slot' = [slot EXCEPT ![s] = Empty("dealloc")]
         /\ last' = "oos_reclaim_empty_pages deallocates the page of slot " \o s \o " (no LSA gate)"
    /\ UNCHANGED <<t1, kind, live, ppLive, notified, mark, t3, gone, r, rseesT1, rseesT3, rbroken, vdrop, rc, vjob, disrupted, t2at>>

Quiescent ==
    /\ T1Ended /\ vdrop = "done" /\ rc.pc = "idle" /\ r # "active" /\ vjob # "reclaim"
    /\ t3 \in {"idle", "committed", "aborted"}
    /\ t3 = "committed" => gone

Finished == Quiescent /\ UNCHANGED vars

Next ==
    \/ T1Update \/ T1StatementRollback \/ T1Commit \/ T1RunPostpone \/ T1Abort
    \/ T3Delete \/ T3Commit \/ T3Abort
    \/ RSnapshot \/ RRead
    \/ ConsumeDrop \/ Remove \/ RemoveReclaimFirst \/ RemoveRecordAfterReclaim
    \/ ReclaimStart \/ ReclaimStep \/ ReclaimFail
    \/ Crash \/ T2Insert \/ Dealloc \/ Finished

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
\* Properties

\* Chains that the row and T1 still reference.
Needed ==
    (IF ~gone /\ t3 # "committed" THEN {CommittedChain} ELSE {})
    \cup (IF t1 = "active" /\ kind = "assign" /\ live THEN {"A", "B"} ELSE {})

\* CBRD-27237 and CBRD-27230: no referenced chain is deleted.
NeededChainsIntact == \A c \in Needed : Intact(c)

\* A snapshot always reads the chain of the version it sees.
ReaderSeesIntactChain == ~rbroken

\* CBRD-26950, CBRD-27781: another transaction's record is never lost.
OtherRecordIntact == t2at # "none" => slot[t2at] = RecT2

\* No orphan: once nothing is pending, only referenced chains hold slots.
NoOrphanWhenQuiescent ==
    Quiescent =>
        \A s \in Slots : slot[s].st = "used" =>
            slot[s].own \in {"T2"} \cup (IF gone THEN {} ELSE {CommittedChain})

\* CBRD-27230: an UPDATE that keeps the stub of chain A never loses chain A.
ReuseKeepsChain == kind = "reuse" => NeededChainsIntact

\* A heap record that still exists, dead or alive, names an intact chain.  It
\* matters to readers that do not use an MVCC snapshot; B2 gives it up.
HeapRecordNamesIntactChain == ~gone => Intact(CommittedChain)

\* Reasons for the design.

\* The reclaimer only works on a chain that nothing can reach.
ReclaimOnlyUnreachable ==
    rc.pc # "idle" =>
        /\ rc.c \notin Needed
        /\ (r = "active" => rc.c # RChain)

\* A notification exists only for a committed UPDATE that dropped chain A.
NotifyOnlyForCommittedDrop ==
    notified => T1Committed /\ kind = "assign" /\ live

\* B3: once T1 has ended, a head mark belongs to a committed UPDATE that
\* dropped chain A, because every rollback undoes the mark first.
MarkOnlyForCommittedDrop ==
    (mark /\ T1Ended) => T1Committed /\ kind = "assign" /\ live

\* The remaining chunks of chain A form a prefix, so a rerun from the head
\* finds all of them; every list entry still to delete names a chunk.
RemainingIsPrefix == slot["a2"].own = "A" => slot["a1"].own = "A"
ListStillNamesChain ==
    rc.pc = "run" => \A i \in 1..rc.pos : slot[rc.list[i].s].own = rc.c

\* Witnesses.  Each is expected to fail: its counterexample shows that the
\* design reaches the situation, so the passing checks are not vacuous.

\* Chain A is reclaimed through the notification and chain B through REMOVE.
WitnessBothChainsReclaimed ==
    ~(gone /\ t1 = "committed" /\ kind = "assign" /\ live /\ rc.pc = "idle"
      /\ \A s \in Slots : slot[s].own \notin {"A", "B"})
\* A kept chain is reclaimed by REMOVE.
WitnessReusedChainReclaimed ==
    ~(gone /\ t1 = "committed" /\ kind = "reuse" /\ rc.pc = "idle"
      /\ \A s \in Slots : slot[s].own # "A")
\* Vacuum waits for a snapshot taken before T1's commit.
WitnessVacuumWaitsForSnapshot ==
    ~(r = "active" /\ ~rseesT1 /\ notified /\ vdrop = "pending")
\* A rerun reads chain A, meets T2's record in the freed tail slot, and stops.
WitnessRerunStopsAtReusedSlot ==
    ~(rc.c = "A" /\ rc.pc = "run" /\ rc.stop)
\* A page is deallocated while the reclaimer still runs.
WitnessDeallocDuringReclaim ==
    ~(rc.pc = "run" /\ \E s \in Slots : slot[s].st = "dealloc")
\* B3: vacuum waits for a snapshot taken before T1's commit.
WitnessMarkWaitsForSnapshot ==
    ~(r = "active" /\ ~rseesT1 /\ mark /\ T1Ended /\ vdrop = "pending")
\* B3: a statement rollback undid the mark, T1 committed, and vacuum kept A.
WitnessUndoneMarkKeepsChain ==
    ~(t1 = "committed" /\ kind = "assign" /\ ~live /\ vdrop = "done" /\ Intact("A"))
\* B2: the REMOVE job starts over after part of the chain is gone, while the
\* heap record still exists.
WitnessRemoveJobReruns ==
    ~(vjob = "reclaim" /\ rc.pc = "start" /\ ~Intact(CommittedChain) /\ ~gone)
\* B2: the dead heap record names a chain that is partly reclaimed.
WitnessDeadRecordNamesPartialChain ==
    ~(vjob = "reclaim" /\ ~Intact(CommittedChain) /\ \E s \in Slots : slot[s].own = CommittedChain)

=============================================================================
