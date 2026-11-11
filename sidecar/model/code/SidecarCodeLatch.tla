--------------------------- MODULE SidecarCodeLatch ---------------------------
(***************************************************************************)
(* Sidecar POC code, the store cursor's page holds (I-7).                 *)
(*                                                                         *)
(* Promise checked: NoDeadlock.  A fixed heap scan whose store cursor     *)
(* keeps one store page between rows, a large-column UPDATE, store vacuum *)
(* of a relocated store record, and the worker that runs a stored         *)
(* procedure's SQL for the scan never close a cycle of page latch waits.  *)
(*                                                                         *)
(* The scan's program is built from the release sites that check.py      *)
(* finds in the code:                                                      *)
(*   RelBeforeCall      sidecar_cursor_release before a routine call      *)
(*                      (cubpl::executor::execute, sp/pl_executor.cpp);   *)
(*   RelBeforeHotFix    sidecar_cursor_before_hot_fix before a hot page   *)
(*                      fix (heap_scan_pb_latch_and_fetch,                *)
(*                      heap_prepare_object_page, scan_batch_next_page);  *)
(*   RelBeforeStoreFix  sidecar_cursor_unfix before the next store page   *)
(*                      (sidecar_cursor_read_value);                      *)
(*   FixGuard           pgbuf_fix_release releases a kept store page      *)
(*                      before any permanent page fix (release builds),   *)
(*                      which covers both fix sites above.                *)
(* The writer's program follows heap_update_logical: the plan reads the   *)
(* old value under the hot latch, heap_unfix_watchers releases the hot    *)
(* page before sidecar_apply_plan when ApplyNoPage, and the hot page is   *)
(* fixed again at relocate.                                               *)
(*                                                                         *)
(* The latch rules (ordered fix, conditional latch, grant order) are the  *)
(* ones of ../recovery/SidecarLatch.tla, copied unchanged.                *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    RelBeforeCall, RelBeforeHotFix, RelBeforeStoreFix, FixGuard, ApplyNoPage

ASSUME \A b \in {RelBeforeCall, RelBeforeHotFix, RelBeforeStoreFix, FixGuard, ApplyNoPage} : b \in BOOLEAN

Pages == {"HH", "H1", "H2", "S1", "S2"}
Other(p) == CASE p = "S1" -> "S2" [] p = "S2" -> "S1" [] p = "H1" -> "H2" [] p = "H2" -> "H1"

F(p, m, k) == [op |-> "fix", page |-> p, mode |-> m, kind |-> k]
U(p) == [op |-> "unfix", page |-> p, mode |-> "none", kind |-> "none"]
Call == [op |-> "call", page |-> "none", mode |-> "none", kind |-> "none"]
Begin == [op |-> "begin", page |-> "none", mode |-> "none", kind |-> "none"]

RelHot == RelBeforeHotFix \/ FixGuard
RelStore == RelBeforeStoreFix \/ FixGuard

\* The scan: row 1 on H1 keeps store page a; a routine call; row 2 reads a
\* again; row 3 reads a value on the other store page b; then H2, with H1
\* kept until H2 is fixed (heap_next).
CursorProgs ==
    { LET b == Other(a) IN
      <<F("H1", "S", "ord"), F(a, "S", "plain")>>
      \o (IF RelBeforeCall THEN <<U(a), Call, F(a, "S", "plain")>> ELSE <<Call>>)
      \o (IF RelStore THEN <<U(a), F(b, "S", "plain")>> ELSE <<F(b, "S", "plain"), U(a)>>)
      \o (IF RelHot THEN <<U(b), F("H2", "S", "ord"), U("H1")>> ELSE <<F("H2", "S", "ord"), U("H1"), U(b)>>)
      \o <<U("H2")>>
      : a \in {"S1", "S2"} }

\* heap_update_logical of a large column on H2: the plan under the hot latch
\* reads the old value (plain fix); then the store insert and the stamp,
\* which may relocate inside the store (ordered fixes); then the hot write.
WriterH2Progs ==
    IF ApplyNoPage
    THEN { <<F("H2", "X", "ord"), F(a, "S", "plain"), U(a), U("H2"),
             F(a, "X", "ord"), F(Other(a), "X", "ord"), U(Other(a)), U(a),
             F("H2", "X", "ord"), U("H2")>>
           : a \in {"S1", "S2"} }
    ELSE { <<F("H2", "X", "ord"), F(a, "S", "plain"), U(a),
             F(a, "X", "ord"), F(Other(a), "X", "ord"), U(Other(a)), U(a),
             U("H2")>>
           : a \in {"S1", "S2"} }

WorkerProgs == { <<Begin>> \o w : w \in WriterH2Progs }

\* Store vacuum of a relocated store record: home page, then the forward
\* page, both until the sysop ends (vacuum_heap_record with 775).
StoreVacuumProgs ==
    { <<F(a, "X", "ord"), F(Other(a), "X", "ord"), U(Other(a)), U(a)>> : a \in {"S1", "S2"} }

Th == {"reader", "writer", "svacuum", "worker"}

ProgsOf(t) ==
    CASE t = "reader" -> CursorProgs
      [] t = "writer" -> WriterH2Progs
      [] t = "worker" -> WorkerProgs
      [] t = "svacuum" -> StoreVacuumProgs

VARIABLES
    hotFirst,  \* the hot heap's header page id is lower than the store's
    prog,      \* [Th -> the thread's program]
    pc,        \* [Th -> index of the next operation]
    held,      \* [Th -> [Pages -> "none" | "S" | "X"]]
    kind,      \* [Th -> [Pages -> "none" | "ord" | "plain"]]
    pend,      \* [Th -> pages an ordered fix still has to fix, in order]
    queue,     \* [Pages -> threads waiting for the page, in arrival order]
    last

vars == <<hotFirst, prog, pc, held, kind, pend, queue, last>>
StateView == <<hotFirst, prog, pc, held, kind, pend, queue>>

Ord(p) == IF hotFirst
          THEN CASE p = "HH" -> 1 [] p = "H1" -> 2 [] p = "H2" -> 3 [] p = "S1" -> 4 [] p = "S2" -> 5
          ELSE CASE p = "S1" -> 1 [] p = "S2" -> 2 [] p = "HH" -> 3 [] p = "H1" -> 4 [] p = "H2" -> 5

CurOp(t) == IF pc[t] <= Len(prog[t]) THEN prog[t][pc[t]]
            ELSE [op |-> "end", page |-> "none", mode |-> "none", kind |-> "none"]
Req(t) == IF pend[t] # <<>> THEN Head(pend[t]) ELSE CurOp(t)
Queued(t) == \E p \in Pages : \E j \in 1..Len(queue[p]) : queue[p][j] = t
HoldsAny(t) == \E p \in Pages : held[t][p] # "none"
Compatible(t, p, m) == \A u \in Th \ {t} : held[u][p] = "none" \/ (m = "S" /\ held[u][p] = "S")

RECURSIVE SortByOrd(_)
SortByOrd(S) == IF S = {} THEN <<>>
                ELSE LET q == CHOOSE x \in S : \A y \in S : Ord(x) <= Ord(y)
                     IN <<q>> \o SortByOrd(S \ {q})

Pos(p, t) == CHOOSE j \in 1..Len(queue[p]) : queue[p][j] = t
Remove(sq, t) == SelectSeq(sq, LAMBDA x : x # t)

Words(t, r) == t \o " " \o (IF r.mode = "S" THEN "read" ELSE "write") \o "-latches " \o r.page
               \o (IF r.kind = "plain" THEN " (plain fix)" ELSE "")

Init ==
    /\ hotFirst \in BOOLEAN
    /\ prog \in [Th -> UNION {ProgsOf(t) : t \in Th}]
    /\ \A t \in Th : prog[t] \in ProgsOf(t)
    /\ pc = [t \in Th |-> 1]
    /\ held = [t \in Th |-> [p \in Pages |-> "none"]]
    /\ kind = [t \in Th |-> [p \in Pages |-> "none"]]
    /\ pend = [t \in Th |-> <<>>]
    /\ queue = [p \in Pages |-> <<>>]
    /\ last = "start"

\* Take the latch r; an ordered fix finishes when its pending list is empty.
Grant(t, r) ==
    /\ held' = [held EXCEPT ![t][r.page] = r.mode]
    /\ kind' = [kind EXCEPT ![t][r.page] = r.kind]
    /\ pend' = IF pend[t] # <<>> THEN [pend EXCEPT ![t] = Tail(@)] ELSE pend
    /\ pc' = IF pend[t] # <<>> /\ Len(pend[t]) > 1 THEN pc ELSE [pc EXCEPT ![t] = @ + 1]

\* A thread asks for its next latch.
Arrive(t) ==
    /\ ~Queued(t) /\ Req(t).op = "fix"
    /\ LET r == Req(t)
           p == r.page
           now == Compatible(t, p, r.mode) /\ queue[p] = <<>>
           conditional == pend[t] = <<>> /\ r.kind = "ord" /\ HoldsAny(t)
           rel == {q \in Pages : kind[t][q] = "ord" /\ Ord(q) > Ord(p)}
       IN  IF now
           THEN /\ Grant(t, r)
                /\ UNCHANGED queue
                /\ last' = Words(t, r)
           ELSE IF conditional
           THEN \* the conditional latch fails: unfix the watched pages after p
                /\ held' = [held EXCEPT ![t] = [q \in Pages |-> IF q \in rel THEN "none" ELSE @[q]]]
                /\ kind' = [kind EXCEPT ![t] = [q \in Pages |-> IF q \in rel THEN "none" ELSE @[q]]]
                /\ pend' = [pend EXCEPT ![t] =
                              <<r>> \o [j \in 1..Cardinality(rel) |->
                                         LET q == SortByOrd(rel)[j]
                                         IN [op |-> "fix", page |-> q, mode |-> held[t][q], kind |-> "ord"]]]
                /\ queue' = [queue EXCEPT ![p] = Append(@, t)]
                /\ UNCHANGED pc
                /\ last' = t \o " fails a conditional latch on " \o p
                           \o (IF rel = {} THEN "" ELSE ", unfixes its later pages,")
                           \o " and waits for " \o p
           ELSE /\ queue' = [queue EXCEPT ![p] = Append(@, t)]
                /\ UNCHANGED <<held, kind, pend, pc>>
                /\ last' = t \o " waits for " \o p
    /\ UNCHANGED <<hotFirst, prog>>

\* A waiting thread is served: writers alone at the head, readers with
\* only readers ahead of them.
Serve(t) ==
    /\ Queued(t)
    /\ LET r == Req(t)
           p == r.page
           k == Pos(p, t)
       IN  /\ Compatible(t, p, r.mode)
           /\ IF r.mode = "X" THEN k = 1
              ELSE \A j \in 1..(k - 1) : Req(queue[p][j]).mode = "S"
           /\ Grant(t, r)
           /\ queue' = [queue EXCEPT ![p] = Remove(@, t)]
           /\ last' = Words(t, r) \o " after waiting"
    /\ UNCHANGED <<hotFirst, prog>>

Unfix(t) ==
    /\ ~Queued(t) /\ pend[t] = <<>> /\ CurOp(t).op = "unfix"
    /\ held' = [held EXCEPT ![t][CurOp(t).page] = "none"]
    /\ kind' = [kind EXCEPT ![t][CurOp(t).page] = "none"]
    /\ pc' = [pc EXCEPT ![t] = @ + 1]
    /\ last' = t \o " unfixes " \o CurOp(t).page
    /\ UNCHANGED <<hotFirst, prog, pend, queue>>

\* The caller returns once the routine's SQL has finished.
CallReturn(t) ==
    /\ CurOp(t).op = "call" /\ CurOp("worker").op = "end"
    /\ pc' = [pc EXCEPT ![t] = @ + 1]
    /\ last' = t \o " returns from the routine call"
    /\ UNCHANGED <<hotFirst, prog, held, kind, pend, queue>>

\* The routine's SQL starts when the caller calls it.
WorkerStart(t) ==
    /\ CurOp(t).op = "begin" /\ CurOp("reader").op = "call"
    /\ pc' = [pc EXCEPT ![t] = @ + 1]
    /\ last' = "reader calls the routine, and " \o t \o " runs its SQL"
    /\ UNCHANGED <<hotFirst, prog, held, kind, pend, queue>>

AllDone == \A t \in Th : CurOp(t).op = "end"
Done == AllDone /\ UNCHANGED vars

Next == (\E t \in Th : Arrive(t) \/ Serve(t) \/ Unfix(t) \/ CallReturn(t) \/ WorkerStart(t)) \/ Done

Spec == Init /\ [][Next]_vars

---------------------------------------------------------------------------
\* t waits for every thread that holds its page in a conflicting mode and
\* for every thread queued ahead of it that it cannot overtake.  A caller in a
\* routine call waits for the worker that runs the routine's SQL.
WaitsFor(t) ==
    (IF CurOp(t).op = "call" /\ CurOp("worker").op # "end" THEN {"worker"} ELSE {})
    \cup
    (IF ~Queued(t) THEN {}
     ELSE LET r == Req(t)
              p == r.page
              k == Pos(p, t)
          IN  {u \in Th \ {t} : held[u][p] = "X" \/ (r.mode = "X" /\ held[u][p] = "S")}
              \cup {queue[p][j] : j \in {j2 \in 1..(k - 1) :
                                          r.mode = "X" \/ Req(queue[p][j2]).mode = "X"}})

RECURSIVE Reach(_, _)
Reach(S, n) == IF n = 0 THEN S ELSE Reach(S \cup UNION {WaitsFor(u) : u \in S}, n - 1)

NoDeadlock == \A t \in Th : t \notin Reach(WaitsFor(t), Cardinality(Th))
=============================================================================
