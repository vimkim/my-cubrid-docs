---------------------------- MODULE SidecarLatch ----------------------------
(***************************************************************************)
(* Sidecar design (design.md, 2026-11-04), latch order (I-7).              *)
(*                                                                         *)
(* Promise checked: NoDeadlock.  No reachable state has a cycle of page   *)
(* latch waits among readers (hot then store), the UPDATE writer with its  *)
(* plan read and store writes, store vacuum, the store-creation sysop      *)
(* under the hot heap header latch, and stock hot relocation.              *)
(*                                                                         *)
(* Pages: hot header HH, hot data pages H1 and H2, store data pages S1    *)
(* and S2.  The store header is left out: creation makes it on a new file *)
(* that no other thread can reach, and no Sidecar path fixes it while     *)
(* holding a hot page.                                                     *)
(*                                                                         *)
(* Latch rules modeled (storage/page_buffer.c):                            *)
(*  - plain fix (pgbuf_fix, unconditional): wait until granted;           *)
(*  - ordered fix (pgbuf_ordered_fix_release, :12444): if the thread      *)
(*    holds any page, try a conditional latch; if that fails, unfix every *)
(*    page held with a watcher that sorts after the requested page, wait  *)
(*    for the requested page, then fix the unfixed pages again in order.  *)
(*    Order is heap file (its header page), then header rank first, then  *)
(*    page id (pgbuf_compare_hold_vpid_for_sort, :12364-12418).  Pages    *)
(*    held by a plain fix are never unfixed by this logic;                *)
(*  - grant (pgbuf_latch_bcb_upon_fix, :6371): a read latch on a page     *)
(*    held for read is granted at once only if no thread waits for it;   *)
(*    waiters are served in arrival order, readers together.             *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Variant   \* "design" or one broken variant below

ASSUME Variant \in {"design", "multirow_under_latch", "multirow_store_write",
                    "reader_store_first", "cursor_two_pages"}

Pages == {"HH", "H1", "H2", "S1", "S2"}
Other(p) == CASE p = "S1" -> "S2" [] p = "S2" -> "S1" [] p = "H1" -> "H2" [] p = "H2" -> "H1"

F(p, m, k) == [op |-> "fix", page |-> p, mode |-> m, kind |-> k]
U(p) == [op |-> "unfix", page |-> p, mode |-> "none", kind |-> "none"]

\* Reader, design 6 Wide scan: scan_batch_next_page fixes the header, then
\* the data page with the header still held (query/scan_manager.c:7858-7912);
\* sidecar_read_value fixes one store page with a plain fix (I-7) and the
\* cursor releases it before the scan moves on.
ReaderProgs ==
    { <<F("HH", "S", "ord"), F("H1", "S", "ord"), U("HH"), F(a, "S", "plain"), U(a), U("H1")>>
      : a \in {"S1", "S2"} }

\* UPDATE that assigns a large column, design 6: plan under the hot latch
\* reads the old store value (plain fix), heap_unfix_watchers, store insert
\* and DELID stamp with no hot page (the stamp may relocate inside the store,
\* ordered fixes), then the hot write.
WriterProgs ==
    { <<F("H1", "X", "ord"), F(a, "S", "plain"), U(a), U("H1"),
        F(a, "X", "ord"), F(Other(a), "X", "ord"), U(Other(a)), U(a),
        F("H1", "X", "ord"), U("H1")>>
      : a \in {"S1", "S2"} }

\* Store vacuum, REL sysop: home page, then the forward page (query/vacuum.c:2374-2447).
StoreVacuumProgs ==
    { <<F(a, "X", "ord"), F(Other(a), "X", "ord"), U(Other(a)), U(a)>> : a \in {"S1", "S2"} }

\* First store creation (design 6 INSERT step 4, the heap_ovf_find_vfid
\* pattern): plain X fix of the hot header with no data page held.
CreateProgs == { <<F("HH", "X", "plain"), U("HH")>> }

\* Stock hot UPDATE that relocates the row: heap_fix_header_page and the
\* new home page, both ordered (storage/heap_file.c:21428-21450, :24313).
HotRelocProgs ==
    { <<F(a, "X", "ord"), F("HH", "X", "ord"), F(Other(a), "X", "ord"),
        U(Other(a)), U("HH"), U(a)>> : a \in {"H1", "H2"} }

\* Broken: locator_multi_insert_force keeps its batch page latched and the
\* insert hook creates the store and writes it (the shape I-7 forbids).
MultiRowProgs ==
    { <<F("H1", "X", "ord"), F("HH", "X", "plain"), U("HH"), F(a, "X", "ord"), U(a), U("H1")>>
      : a \in {"S1", "S2"} }

\* The same batch page held across a store write only (the store exists).
MultiRowWriteProgs ==
    { <<F("H1", "X", "ord"), F(a, "X", "ord"), U(a), U("H1")>> : a \in {"S1", "S2"} }

\* Broken: a reader that latches the store page, then the hot page.
StoreFirstReaderProgs ==
    { <<F(a, "S", "plain"), F("H1", "S", "ord"), U("H1"), U(a)>> : a \in {"S1", "S2"} }

\* Broken: a store cursor that fixes the next store page before it
\* releases the previous one.
TwoPageCursorProgs ==
    { <<F("H1", "S", "ord"), F(a, "S", "plain"), F(Other(a), "S", "plain"), U(a), U(Other(a)), U("H1")>>
      : a \in {"S1", "S2"} }

Th == CASE Variant = "design" -> {"reader", "writer", "svacuum", "creator", "hotreloc"}
        [] Variant \in {"multirow_under_latch", "multirow_store_write"} ->
              {"reader", "writer", "svacuum", "creator", "hotreloc", "multirow"}
        [] Variant = "reader_store_first" -> {"reader", "writer", "svacuum", "creator", "hotreloc"}
        [] Variant = "cursor_two_pages" -> {"reader", "reader2", "writer", "svacuum"}

ProgsOf(t) ==
    CASE t = "reader" -> IF Variant = "reader_store_first" THEN StoreFirstReaderProgs
                         ELSE IF Variant = "cursor_two_pages" THEN TwoPageCursorProgs
                         ELSE ReaderProgs
      [] t = "reader2" -> TwoPageCursorProgs
      [] t = "writer" -> WriterProgs
      [] t = "svacuum" -> StoreVacuumProgs
      [] t = "creator" -> CreateProgs
      [] t = "hotreloc" -> HotRelocProgs
      [] t = "multirow" -> IF Variant = "multirow_store_write" THEN MultiRowWriteProgs
                           ELSE MultiRowProgs

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

AllDone == \A t \in Th : CurOp(t).op = "end"
Done == AllDone /\ UNCHANGED vars

Next == (\E t \in Th : Arrive(t) \/ Serve(t) \/ Unfix(t)) \/ Done

Spec == Init /\ [][Next]_vars

---------------------------------------------------------------------------
\* t waits for every thread that holds its page in a conflicting mode and
\* for every thread queued ahead of it that it cannot overtake.
WaitsFor(t) ==
    IF ~Queued(t) THEN {}
    ELSE LET r == Req(t)
             p == r.page
             k == Pos(p, t)
         IN  {u \in Th \ {t} : held[u][p] = "X" \/ (r.mode = "X" /\ held[u][p] = "S")}
             \cup {queue[p][j] : j \in {j2 \in 1..(k - 1) :
                                         r.mode = "X" \/ Req(queue[p][j2]).mode = "X"}}

RECURSIVE Reach(_, _)
Reach(S, n) == IF n = 0 THEN S ELSE Reach(S \cup UNION {WaitsFor(u) : u \in S}, n - 1)

NoDeadlock == \A t \in Th : t \notin Reach(WaitsFor(t), Cardinality(Th))
=============================================================================
