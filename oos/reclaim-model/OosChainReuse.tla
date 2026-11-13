--------------------------- MODULE OosChainReuse ---------------------------
(***************************************************************************)
(* CBRD-27230: UPDATE reuses the OOS value chain of every attribute it    *)
(* does not assign, so one chain is shared by consecutive row versions.   *)
(* The chain is released exactly once: by the A' postpone of the UPDATE   *)
(* that drops it (RVOOS_UPDATE_DROP_POSTPONE -> RVOOS_NOTIFY_VACUUM ->    *)
(* vacuum), or by vacuum REMOVE of the row's last version.               *)
(*                                                                        *)
(* One row with two OOS attributes c1 and c2.  Update transactions in     *)
(* Txns run one after another (the row lock), each with up to MaxStmts    *)
(* statements.  A statement is an UPDATE that assigns any subset of       *)
(* {c1, c2} (the empty subset assigns only inline attributes) or a        *)
(* DELETE.  A statement rollback pops the newest statement; repeating it  *)
(* is a savepoint rollback.  A transaction commits or rolls back.         *)
(*                                                                        *)
(* A chain is <<slot, stamp>>: one head chunk with its identity stamp.    *)
(* Chunk-level reclaim order, link stamps and reclaimer reruns are        *)
(* checked in OosReclaimDesign and OosReclaimRetry; here a reclaim is one *)
(* step that deletes the head when its stamp matches.  A freed slot is    *)
(* reused at once by the next new chain, with a new stamp.                *)
(*                                                                        *)
(* Commit (A'): logtb_complete_mvcc, LOG_COMMIT_WITH_POSTPONE, then each  *)
(* surviving statement's postpone appends RVOOS_NOTIFY_VACUUM under the   *)
(* transaction's MVCCID and is marked run, then LOG_COMMIT.  One crash    *)
(* may happen anywhere: an active transaction is undone; a transaction    *)
(* with LOG_COMMIT_WITH_POSTPONE reruns every postpone not yet marked     *)
(* run, so a notification may be appended twice.  Vacuum consumes a      *)
(* notification once the transaction left the MVCC table and every       *)
(* active snapshot sees it, and may consume it again after a crash before *)
(* the block is marked done.  Readers each take one snapshot.             *)
(*                                                                        *)
(* Settings.  The chosen design is Reuse="copy", Source="latest",        *)
(* Drop="set_diff",                                                       *)
(* Publish="postpone", Cancel, Horizon, Identity, Rerun all TRUE,         *)
(* UndoFrees="created".  Each other value undoes one decision:            *)
(*   Reuse     "restamp": the reused stub gets a new stamp, written into  *)
(*             the head chunk too                                         *)
(*   Source    "snapshot": the reused stub is copied from the committed   *)
(*             version before the newest one (a snapshot-visible version) *)
(*             instead of the locked newest version                       *)
(*   Drop      "undo_image": the UPDATE drops every chain of the old      *)
(*             record (the removed forward-walk)                          *)
(*   Publish   "before_commit": a commit hook appends the notifications   *)
(*             before the commit record (decision A, rejected)            *)
(*   Cancel    FALSE: a statement rollback leaves its postpone            *)
(*   Horizon   FALSE: vacuum ignores snapshots                            *)
(*   Identity  FALSE: the reclaimer deletes the slot without comparing    *)
(*             the stamp                                                  *)
(*   Rerun     FALSE: restart does not rerun unfinished postpones         *)
(*   UndoFrees "new_record": the undo of an UPDATE frees every chain of   *)
(*             the new record, reused ones included                       *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS Txns, Readers, Slots, MaxStmts, MaxStamp, MaxNotes,
          Reuse, Source, Drop, Publish, Cancel, Horizon, Identity, Rerun, UndoFrees

ASSUME /\ Reuse \in {"copy", "restamp"}
       /\ Source \in {"latest", "snapshot"}
       /\ Drop \in {"set_diff", "undo_image"}
       /\ Publish \in {"postpone", "before_commit"}
       /\ Cancel \in BOOLEAN /\ Horizon \in BOOLEAN /\ Identity \in BOOLEAN /\ Rerun \in BOOLEAN
       /\ UndoFrees \in {"created", "new_record"}

Cols == <<"c1", "c2">>
ColSet == {"c1", "c2"}
None == "none"

\* A record: the chain of each attribute and the delete mark.
Chains(rec) == {rec.ch[c] : c \in ColSet}

InitRec == [ch |-> [c \in ColSet |-> IF c = "c1" THEN <<1, 1>> ELSE <<2, 2>>],
            del |-> FALSE, delby |-> None]

\* The final record of a transaction that has not committed.
NoRec == [ch |-> [c \in ColSet |-> <<0, 0>>], del |-> FALSE, delby |-> None]

VARIABLES
    store,       \* [Slots -> stamp of the head chunk in the slot, 0 when free]
    nextStamp,
    rec,         \* the newest record version (possibly uncommitted)
    removed,     \* vacuum REMOVE removed the heap record
    tx,          \* [Txns -> "idle", "active", "hooked", "pp", "committed", "aborted"]
    stack,       \* [Txns -> statements: [pre, drop, created, reused]]
    ppq,         \* [Txns -> drop sets whose postpone has not been marked run]
    ppHalf,      \* [Txns -> the head postpone appended its notification, not yet marked run]
    final,       \* [Txns -> the record the transaction committed, or NoRec]
    stale,       \* [Txns -> drop sets of rolled-back statements] (Cancel = FALSE)
    notes,       \* durable RVOOS_NOTIFY_VACUUM records: [t, drop]
    consumed,    \* indexes of notes whose vacuum block is done
    vacHalf,     \* index of the note vacuum reclaimed but has not marked done, or 0
    rs,          \* [Readers -> "none", "active", "done"]
    seen,        \* [Readers -> transactions the snapshot sees as committed]
    rver,        \* [Readers -> chains of the version the snapshot reads]
    crashed,
    wrongDel,    \* a reclaim deleted a chain its notification did not name
    shared,      \* chains that a committed statement kept by reuse
    prb,         \* transactions that rolled back a statement that dropped a chain
    prevRec,     \* the committed version before the newest committed one
    crashPp,     \* the crash hit a transaction between LOG_COMMIT_WITH_POSTPONE and LOG_COMMIT
    last

vars == <<store, nextStamp, rec, removed, tx, stack, ppq, ppHalf, final, stale, notes, consumed,
          vacHalf, rs, seen, rver, crashed, wrongDel, shared, prb, prevRec, crashPp, last>>
view == <<store, nextStamp, rec, removed, tx, stack, ppq, ppHalf, final, stale, notes, consumed,
          vacHalf, rs, seen, rver, crashed, wrongDel, shared, prb, prevRec, crashPp>>

Init ==
    /\ store = [s \in Slots |-> IF s = 1 THEN 1 ELSE IF s = 2 THEN 2 ELSE 0]
    /\ nextStamp = 3
    /\ rec = InitRec
    /\ removed = FALSE
    /\ tx = [t \in Txns |-> "idle"]
    /\ stack = [t \in Txns |-> <<>>]
    /\ ppq = [t \in Txns |-> <<>>]
    /\ ppHalf = [t \in Txns |-> FALSE]
    /\ final = [t \in Txns |-> NoRec]
    /\ stale = [t \in Txns |-> <<>>]
    /\ notes = <<>>
    /\ consumed = {}
    /\ vacHalf = 0
    /\ rs = [r \in Readers |-> "none"]
    /\ seen = [r \in Readers |-> {}]
    /\ rver = [r \in Readers |-> {}]
    /\ crashed = FALSE
    /\ wrongDel = FALSE
    /\ shared = {}
    /\ prb = {}
    /\ prevRec = InitRec
    /\ crashPp = FALSE
    /\ last = "initial state"

Live(ch) == store[ch[1]] = ch[2]
LiveChains == {<<s, store[s]>> : s \in {x \in Slots : store[x] # 0}}

\* The transaction that holds the row lock.
Busy == {t \in Txns : tx[t] \in {"active", "hooked", "pp"}}
Writing == {t \in Txns : tx[t] \in {"active", "hooked"}}
\* Transactions that MVCC treats as committed (logtb_complete_mvcc ran).
McCommitted == {t \in Txns : tx[t] \in {"pp", "committed"}}

\* The newest committed version: the first pre-image of a writing transaction.
CommittedRec ==
    IF \E t \in Writing : stack[t] # <<>>
      THEN LET t == CHOOSE x \in Writing : stack[x] # <<>> IN stack[t][1].pre
      ELSE rec

SeqSet(q) == {q[i] : i \in 1..Len(q)}
DropsOf(st) == [i \in 1..Len(st) |-> st[i].drop]
NonEmpty(q) == SelectSeq(q, LAMBDA d : d # {})

FreeChains(st, chs) == [s \in Slots |-> IF \E ch \in chs : ch[1] = s /\ st[s] = ch[2] THEN 0 ELSE st[s]]

\* What the undo of one statement frees.
UndoSet(e, cur) == IF UndoFrees = "created" THEN e.created ELSE Chains(cur)

\* Undo every statement of t, newest first.
RECURSIVE UndoAll(_, _, _)
UndoAll(st, cur, s) ==
    IF st = <<>> THEN <<cur, s>>
    ELSE LET e == st[Len(st)] IN UndoAll(SubSeq(st, 1, Len(st) - 1), e.pre, FreeChains(s, UndoSet(e, cur)))

-----------------------------------------------------------------------------
\* Update transactions

StmtGuard(t) ==
    /\ tx[t] \in {"idle", "active"}
    /\ Busy \subseteq {t}
    /\ ~rec.del
    /\ Len(stack[t]) < MaxStmts

\* The lowest free slots, one per assigned attribute, in column order.
FreeSlots == {s \in Slots : store[s] = 0}

Update(t, A) ==
    /\ StmtGuard(t)
    /\ LET n == Cardinality(A)
           fs == FreeSlots
           s1 == IF fs = {} THEN 0 ELSE CHOOSE s \in fs : \A x \in fs : s <= x
           s2 == IF fs \ {s1} = {} THEN 0 ELSE CHOOSE s \in fs \ {s1} : \A x \in fs \ {s1} : s <= x
           kept == ColSet \ A
           src == IF Source = "latest" THEN rec ELSE prevRec
           restamps == IF Reuse = "restamp" THEN Cardinality(kept) ELSE 0
           need == n + restamps
           newCh == [c \in ColSet |->
                       IF c \in A
                         THEN IF A = ColSet /\ c = "c2" THEN <<s2, nextStamp + 1>>
                              ELSE <<s1, nextStamp>>
                         ELSE IF Reuse = "copy" THEN src.ch[c]
                              ELSE <<rec.ch[c][1], nextStamp + n + (IF c = "c2" /\ kept = ColSet THEN 1 ELSE 0)>>]
           newRec == [rec EXCEPT !.ch = newCh]
           created == {newCh[c] : c \in A}
           dropped == IF Drop = "set_diff" THEN Chains(rec) \ Chains(newRec) ELSE Chains(rec)
       IN /\ n <= Cardinality(fs)
          /\ nextStamp + need - 1 <= MaxStamp
          /\ store' = LET W == {newCh[c] : c \in A} \cup (IF Reuse = "restamp" THEN {newCh[c] : c \in kept} ELSE {})
                      IN [s \in Slots |-> IF \E w \in W : w[1] = s THEN (CHOOSE w \in W : w[1] = s)[2] ELSE store[s]]
          /\ nextStamp' = nextStamp + need
          /\ rec' = newRec
          /\ stack' = [stack EXCEPT ![t] = Append(@, [pre |-> rec, drop |-> dropped, created |-> created,
                                                       reused |-> {newCh[c] : c \in kept}])]
          /\ last' = t \o ": UPDATE assigns " \o (IF A = {} THEN "no OOS attribute"
                                                  ELSE IF A = ColSet THEN "c1 and c2"
                                                  ELSE CHOOSE c \in A : TRUE)
                     \o "; the postpone names " \o (IF dropped = {} THEN "nothing" ELSE "the dropped chains")
    /\ tx' = [tx EXCEPT ![t] = "active"]
    /\ UNCHANGED <<removed, ppq, ppHalf, final, stale, notes, consumed, vacHalf, rs, seen, rver, crashed,
                   wrongDel, shared, prb, crashPp, prevRec>>

Delete(t) ==
    /\ StmtGuard(t)
    /\ rec' = [rec EXCEPT !.del = TRUE, !.delby = t]
    /\ stack' = [stack EXCEPT ![t] = Append(@, [pre |-> rec, drop |-> {}, created |-> {}, reused |-> {}])]
    /\ tx' = [tx EXCEPT ![t] = "active"]
    /\ last' = t \o ": DELETE sets the delete MVCCID; the chains stay for older snapshots"
    /\ UNCHANGED <<store, nextStamp, removed, ppq, ppHalf, final, stale, notes, consumed, vacHalf, rs, seen,
                   rver, crashed, wrongDel, shared, prb, crashPp, prevRec>>

\* Statement rollback; repeated, a savepoint rollback.
StmtRollback(t) ==
    /\ tx[t] = "active" /\ stack[t] # <<>>
    /\ LET e == stack[t][Len(stack[t])]
       IN /\ rec' = e.pre
          /\ store' = FreeChains(store, UndoSet(e, rec))
          /\ stack' = [stack EXCEPT ![t] = SubSeq(@, 1, Len(@) - 1)]
          /\ stale' = IF Cancel \/ e.drop = {} THEN stale ELSE [stale EXCEPT ![t] = Append(@, e.drop)]
          /\ prb' = IF e.drop # {} THEN prb \cup {t} ELSE prb
    /\ last' = t \o ": a statement rollback undoes its newest statement"
               \o (IF Cancel THEN " and cancels its postpone" ELSE "; its postpone stays")
    /\ UNCHANGED <<nextStamp, removed, tx, ppq, ppHalf, final, notes, consumed, vacHalf, rs, seen, rver,
                   crashed, wrongDel, shared, crashPp, prevRec>>

Abort(t) ==
    /\ tx[t] = "active"
    /\ LET u == UndoAll(stack[t], rec, store) IN rec' = u[1] /\ store' = u[2]
    /\ tx' = [tx EXCEPT ![t] = "aborted"]
    /\ stack' = [stack EXCEPT ![t] = <<>>]
    /\ stale' = [stale EXCEPT ![t] = <<>>]
    /\ last' = t \o " rolls back; its postpones are discarded"
    /\ UNCHANGED <<nextStamp, removed, ppq, ppHalf, final, notes, consumed, vacHalf, rs, seen, rver, crashed,
                   wrongDel, shared, prb, crashPp, prevRec>>

KeptByReuse(t) == UNION {stack[t][i].reused : i \in 1..Len(stack[t])}

\* A': logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE.
CommitWithPostpone(t) ==
    /\ Publish = "postpone" /\ tx[t] = "active"
    /\ tx' = [tx EXCEPT ![t] = "pp"]
    /\ ppq' = [ppq EXCEPT ![t] = NonEmpty(DropsOf(stack[t]) \o stale[t])]
    /\ final' = [final EXCEPT ![t] = rec]
    /\ shared' = shared \cup KeptByReuse(t)
    /\ prevRec' = IF stack[t] = <<>> THEN prevRec ELSE stack[t][1].pre
    /\ stack' = [stack EXCEPT ![t] = <<>>]
    /\ stale' = [stale EXCEPT ![t] = <<>>]
    /\ last' = t \o ": logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed"
    /\ UNCHANGED <<store, nextStamp, rec, removed, ppHalf, notes, consumed, vacHalf, rs, seen, rver, crashed,
                   wrongDel, prb, crashPp>>

RunPostpone(t) ==
    /\ tx[t] = "pp" /\ ppq[t] # <<>> /\ ~ppHalf[t]
    /\ notes' = Append(notes, [t |-> t, drop |-> Head(ppq[t])])
    /\ ppHalf' = [ppHalf EXCEPT ![t] = TRUE]
    /\ last' = t \o ": a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)"
    /\ UNCHANGED <<store, nextStamp, rec, removed, tx, stack, ppq, final, stale, consumed, vacHalf, rs, seen,
                   rver, crashed, wrongDel, shared, prb, crashPp, prevRec>>

PostponeDone(t) ==
    /\ tx[t] = "pp" /\ ppHalf[t]
    /\ ppq' = [ppq EXCEPT ![t] = Tail(@)]
    /\ ppHalf' = [ppHalf EXCEPT ![t] = FALSE]
    /\ last' = t \o ": the postpone is marked run (durable)"
    /\ UNCHANGED <<store, nextStamp, rec, removed, tx, stack, final, stale, notes, consumed, vacHalf, rs, seen,
                   rver, crashed, wrongDel, shared, prb, crashPp, prevRec>>

CommitEnd(t) ==
    /\ tx[t] = "pp" /\ ppq[t] = <<>>
    /\ tx' = [tx EXCEPT ![t] = "committed"]
    /\ last' = t \o ": LOG_COMMIT; the row lock is released"
    /\ UNCHANGED <<store, nextStamp, rec, removed, stack, ppq, ppHalf, final, stale, notes, consumed, vacHalf,
                   rs, seen, rver, crashed, wrongDel, shared, prb, crashPp, prevRec>>

\* Decision A (rejected): a commit hook appends the notifications before the
\* commit record and before logtb_complete_mvcc.  A WAL flush may make them
\* durable at once.
CommitHook(t) ==
    /\ Publish = "before_commit" /\ tx[t] = "active"
    /\ tx' = [tx EXCEPT ![t] = "hooked"]
    /\ LET q == NonEmpty(DropsOf(stack[t]) \o stale[t])
       IN notes' = notes \o [i \in 1..Len(q) |-> [t |-> t, drop |-> q[i]]]
    /\ last' = t \o ": the commit hook appends RVOOS_NOTIFY_VACUUM before the commit record (flushed)"
    /\ UNCHANGED <<store, nextStamp, rec, removed, stack, ppq, ppHalf, final, stale, consumed, vacHalf, rs,
                   seen, rver, crashed, wrongDel, shared, prb, crashPp, prevRec>>

CommitRecord(t) ==
    /\ tx[t] = "hooked"
    /\ tx' = [tx EXCEPT ![t] = "committed"]
    /\ final' = [final EXCEPT ![t] = rec]
    /\ shared' = shared \cup KeptByReuse(t)
    /\ prevRec' = IF stack[t] = <<>> THEN prevRec ELSE stack[t][1].pre
    /\ stack' = [stack EXCEPT ![t] = <<>>]
    /\ stale' = [stale EXCEPT ![t] = <<>>]
    /\ last' = t \o ": the commit record is flushed; logtb_complete_mvcc"
    /\ UNCHANGED <<store, nextStamp, rec, removed, ppq, ppHalf, notes, consumed, vacHalf, rs, seen, rver,
                   crashed, wrongDel, prb, crashPp>>

-----------------------------------------------------------------------------
\* Readers: one snapshot each, which reads the newest committed version.

Snapshot(r) ==
    /\ rs[r] = "none"
    /\ rs' = [rs EXCEPT ![r] = "active"]
    /\ seen' = [seen EXCEPT ![r] = McCommitted]
    /\ rver' = [rver EXCEPT ![r] = IF removed \/ (CommittedRec.del /\ CommittedRec.delby \in McCommitted)
                                     THEN {} ELSE Chains(CommittedRec)]
    /\ last' = r \o " takes a snapshot"
    /\ UNCHANGED <<store, nextStamp, rec, removed, tx, stack, ppq, ppHalf, final, stale, notes, consumed,
                   vacHalf, crashed, wrongDel, shared, prb, crashPp, prevRec>>

SnapshotEnd(r) ==
    /\ rs[r] = "active"
    /\ rs' = [rs EXCEPT ![r] = "done"]
    /\ last' = r \o " reads its version and ends"
    /\ UNCHANGED <<store, nextStamp, rec, removed, tx, stack, ppq, ppHalf, final, stale, notes, consumed,
                   vacHalf, seen, rver, crashed, wrongDel, shared, prb, crashPp, prevRec>>

-----------------------------------------------------------------------------
\* Vacuum

\* oldest_visible: no active snapshot misses t's commit.
SafeFor(t) == Horizon => \A r \in Readers : rs[r] = "active" => t \in seen[r]

\* One reclaim of the chains a notification or REMOVE names.
Reclaim(st, chs) ==
    [s \in Slots |-> IF \E ch \in chs : ch[1] = s /\ st[s] # 0 /\ (Identity => st[s] = ch[2]) THEN 0 ELSE st[s]]
WrongDelete(st, chs) == \E ch \in chs : st[ch[1]] # 0 /\ st[ch[1]] # ch[2] /\ ~Identity

Consume(i) ==
    /\ vacHalf = 0 /\ i \notin consumed
    /\ tx[notes[i].t] \notin {"active", "hooked"}
    /\ SafeFor(notes[i].t)
    /\ store' = Reclaim(store, notes[i].drop)
    /\ wrongDel' = (wrongDel \/ WrongDelete(store, notes[i].drop))
    /\ vacHalf' = i
    /\ last' = "vacuum: consumes notification " \o ToString(i) \o " and reclaims its chains (redo-only)"
    /\ UNCHANGED <<nextStamp, rec, removed, tx, stack, ppq, ppHalf, final, stale, notes, consumed, rs, seen,
                   rver, crashed, shared, prb, crashPp, prevRec>>

VacDone ==
    /\ vacHalf # 0
    /\ consumed' = consumed \cup {vacHalf}
    /\ vacHalf' = 0
    /\ last' = "vacuum: marks the block done"
    /\ UNCHANGED <<store, nextStamp, rec, removed, tx, stack, ppq, ppHalf, final, stale, notes, rs, seen, rver,
                   crashed, wrongDel, shared, prb, crashPp, prevRec>>

\* REMOVE of the last version: one sysop removes the heap record and runs the
\* reclaim intent for its chains at log_sysop_commit.
Remove ==
    /\ rec.del /\ ~removed /\ rec.delby \in McCommitted
    /\ SafeFor(rec.delby)
    /\ removed' = TRUE
    /\ store' = Reclaim(store, Chains(rec))
    /\ wrongDel' = (wrongDel \/ WrongDelete(store, Chains(rec)))
    /\ last' = "vacuum: REMOVE removes the heap record and reclaims its chains"
    /\ UNCHANGED <<nextStamp, rec, tx, stack, ppq, ppHalf, final, stale, notes, consumed, vacHalf, rs, seen,
                   rver, crashed, shared, prb, crashPp, prevRec>>

-----------------------------------------------------------------------------
\* Crash and restart recovery

Crash ==
    /\ ~crashed
    /\ LET losers == Writing
           u == IF losers = {} THEN <<rec, store>>
                ELSE LET t == CHOOSE x \in losers : TRUE IN UndoAll(stack[t], rec, store)
       IN /\ rec' = u[1]
          /\ store' = u[2]
          /\ tx' = [t \in Txns |-> IF t \in losers THEN "aborted" ELSE tx[t]]
          /\ stack' = [t \in Txns |-> IF t \in losers THEN <<>> ELSE stack[t]]
          /\ stale' = [t \in Txns |-> IF t \in losers THEN <<>> ELSE stale[t]]
          \* A postpone that appended its notification but was not marked run is run again.
          /\ ppq' = IF Rerun THEN ppq ELSE [t \in Txns |-> IF tx[t] = "pp" THEN <<>> ELSE ppq[t]]
          /\ ppHalf' = [t \in Txns |-> FALSE]
    /\ vacHalf' = 0
    /\ rs' = [r \in Readers |-> IF rs[r] = "active" THEN "done" ELSE rs[r]]
    /\ crashed' = TRUE
    /\ crashPp' = \E t \in Txns : tx[t] = "pp"
    /\ last' = "crash; recovery undoes active transactions and reruns unfinished postpones"
    /\ UNCHANGED <<nextStamp, removed, final, notes, consumed, seen, rver, wrongDel, shared, prb, prevRec>>

-----------------------------------------------------------------------------

SystemNext ==
    \/ \E t \in Txns : RunPostpone(t) \/ PostponeDone(t) \/ CommitEnd(t) \/ CommitRecord(t)
    \/ \E i \in 1..Len(notes) : Consume(i)
    \/ VacDone \/ Remove
    \/ \E r \in Readers : SnapshotEnd(r)

Next ==
    \/ \E t \in Txns :
         \/ \E A \in SUBSET ColSet : Update(t, A)
         \/ Delete(t) \/ StmtRollback(t) \/ Abort(t)
         \/ CommitWithPostpone(t) \/ CommitHook(t)
    \/ \E r \in Readers : Snapshot(r)
    \/ Crash
    \/ SystemNext

Fairness ==
    /\ \A t \in Txns : WF_vars(RunPostpone(t)) /\ WF_vars(PostponeDone(t))
                       /\ WF_vars(CommitEnd(t)) /\ WF_vars(CommitRecord(t))
    /\ \A i \in 1..MaxNotes : WF_vars(i <= Len(notes) /\ Consume(i))
    /\ WF_vars(VacDone) /\ WF_vars(Remove)
    /\ \A r \in Readers : WF_vars(SnapshotEnd(r))

Spec == Init /\ [][Next]_vars
LiveSpec == Spec /\ Fairness

-----------------------------------------------------------------------------
\* Properties

\* Chains that some version can still need: the heap record (live or dead
\* until REMOVE), every pre-image that a rollback or crash recovery can
\* restore, and the version of every active snapshot.
Needed ==
    (IF removed THEN {} ELSE Chains(rec))
    \cup UNION {UNION {Chains(stack[t][i].pre) : i \in 1..Len(stack[t])} : t \in Txns}
    \cup UNION {rver[r] : r \in {x \in Readers : rs[x] = "active"}}

\* A chain referenced by any version that a live or recoverable snapshot
\* (or rollback) can read is never reclaimed.
NeededChainsLive == \A ch \in Needed : Live(ch)

\* A reclaim deletes only the chain it names (a duplicate notification after
\* the slot was reused must be a no-op).
NoWrongDelete == ~wrongDel

\* No notification for a rolled-back UPDATE: every notification belongs to a
\* transaction that committed, and names no chain its committed version keeps.
NotifyOnlyForCommittedDrop ==
    \A i \in 1..Len(notes) :
        LET t == notes[i].t IN
          /\ tx[t] \in {"hooked", "pp", "committed"}
          /\ (tx[t] \in {"pp", "committed"} => notes[i].drop \cap Chains(final[t]) = {})

\* Garbage: a live chain that nothing references or can restore.
Garbage == LiveChains \ Needed

\* Liveness: every chain an UPDATE abandoned is eventually reclaimed after the
\* UPDATE commits (and the row's last chains after REMOVE).
ChainSpace == {<<s, k>> : s \in Slots, k \in 1..MaxStamp}
GarbageReclaimed == \A ch \in ChainSpace : (ch \in Garbage) ~> ~Live(ch)

\* Witnesses (each expected to fail: TLC shows the situation is reachable).
\* A chain that a committed UPDATE kept by reuse is reclaimed later.
WitnessSharedChainReclaimed == ~(\E ch \in shared : ~Live(ch))
\* A snapshot holds back the reclaim of a chain that a committed UPDATE dropped.
WitnessSnapshotHoldsReclaim ==
    ~(\E r \in Readers, i \in 1..Len(notes) :
        rs[r] = "active" /\ i \notin consumed /\ rver[r] \cap notes[i].drop # {} /\ notes[i].t \in McCommitted)
\* A restart rerun appended the same notification twice.
WitnessDuplicateNotify == ~(\E i, j \in 1..Len(notes) : i < j /\ notes[i] = notes[j])
\* A crash between LOG_COMMIT_WITH_POSTPONE and LOG_COMMIT, and the dropped chain is still reclaimed.
WitnessCrashInPostponeThenReclaim == ~(crashPp /\ consumed # {} /\ \A t \in Txns : tx[t] # "pp")
\* A transaction rolled back a statement that dropped a chain, then committed another drop.
WitnessPartialRollbackThenCommit ==
    ~(\E t \in prb : tx[t] = "committed" /\ \E i \in 1..Len(notes) : notes[i].t = t)

=============================================================================
