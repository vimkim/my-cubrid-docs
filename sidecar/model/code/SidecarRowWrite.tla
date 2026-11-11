--------------------------- MODULE SidecarRowWrite ---------------------------
(***************************************************************************)
(* Sidecar POC code, one row with one large column: its writers, store    *)
(* vacuum, a reader that resolves under the hot latch, and a committed-   *)
(* snapshot fetch with its retry and its lock fallback.                   *)
(*                                                                         *)
(* Writers follow heap_update_logical and heap_delete_logical             *)
(* (storage/heap_file.c) with the Sidecar hooks:                          *)
(*   lock     the row's X lock, taken by the locator before the heap call;*)
(*   plan     heap_get_record_location, then heap_sidecar_plan under the  *)
(*            hot latch: the plan stamps the refs of the version it reads;*)
(*   insert   heap_unfix_watchers, then sidecar_apply_plan:              *)
(*            sidecar_insert_values, one store insert per fresh value;    *)
(*   stamp    sidecar_stamp_values, the MVCC delete of each planned ref;  *)
(*   relocate goto relocate: the hot page is fixed again and the plan     *)
(*            hook runs again (it returns at once on an applied plan);    *)
(*   hot      the hot write, under the hot latch;                         *)
(*   end      log_commit_local, or log_abort_local with undo in reverse   *)
(*            LSA order, one step per log record.                         *)
(* The order of insert, stamp and hot comes from WriteOrder.              *)
(*                                                                         *)
(* Readers:                                                                *)
(*   L  a dirty or NULL-snapshot reader (SIDECAR_READER_LATCHED): it      *)
(*      reads the current version and its store records while it holds   *)
(*      the hot page;                                                     *)
(*   C  xlocator_fetch with the committed snapshot (heap_get_visible_     *)
(*      version_internal, heap_sidecar_fetch_exit): heap path under the   *)
(*      latch, log path without it; an absent store record retries up to  *)
(*      SIDECAR_RETRY_BOUND, then S_SIDECAR_LOCK_NEEDED takes              *)
(*      sidecar_fetch_locked: S lock, heap_get_last_version as a lock     *)
(*      holder, the committed-snapshot test, the unlock.                  *)
(*                                                                         *)
(* Properties, one TLC run each:                                           *)
(*  LatchedReaderFinds  L never ends in ER_SIDECAR_DANGLING_REF.          *)
(*  FetchNoError        C never ends in an error.                         *)
(*  FetchNoLostRow      C reports the row missing only after a DELETE of  *)
(*                      it committed.                                     *)
(*  StoreMatchesRow     when every writer is done, the store records with *)
(*                      no DELID are exactly the ones the current version *)
(*                      names (no orphan, no unstamped dropped value).    *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Writers,        \* writer transactions (model values or strings)
    Ops,            \* operations a writer may run: subset of {"UPDATE", "DELETE"}
    RetryBound,     \* SIDECAR_RETRY_BOUND
    WriteOrder,     \* "store_then_hot" | "hot_then_store"
    PlanOnce,       \* the plan hook returns at once on SIDECAR_PLAN_APPLIED
    RowLock,        \* writers hold the row's X lock
    FallbackLock,   \* "s_lock_around_read" | "none"
    DelidTest,      \* sidecar_on_absent tests for a committed DELID first
    Fallback,       \* S_SIDECAR_LOCK_NEEDED goes to sidecar_fetch_locked
    OnAbsent        \* "retry" (S_SIDECAR_RETRY) | "doesnt_exist" (as develop treats a vanished record)

ASSUME Ops \subseteq {"UPDATE", "DELETE"} /\ Ops # {}
ASSUME RetryBound \in 0..5
ASSUME WriteOrder \in {"store_then_hot", "hot_then_store"}
ASSUME FallbackLock \in {"s_lock_around_read", "none"}
ASSUME \A b \in {PlanOnce, RowLock, DelidTest, Fallback} : b \in BOOLEAN
ASSUME OnAbsent \in {"retry", "doesnt_exist"}

Prog == IF WriteOrder = "store_then_hot"
        THEN <<"lock", "plan", "insert", "stamp", "relocate", "hot", "end">>
        ELSE <<"lock", "plan", "hot", "insert", "stamp", "end">>

NoTx == "none"
Init0 == "t0"    \* the committed INSERT of the row
MaxRec == 1 + 2 * Cardinality(Writers)
NoVer == [ref |-> 0, ins |-> NoTx, del |-> NoTx]

VARIABLES
    cur,        \* the current hot version [ref, ins, del]
    prev,       \* the version the latest UPDATE replaced (the log path's version)
    store,      \* [1..MaxRec -> [st |-> "none" | "live" | "gone", del |-> tx]]
    nrec,       \* the next store record id
    committed,  \* committed transactions
    delDone,    \* a DELETE of the row committed
    xlock,      \* holder of the row's X lock, or NoTx
    slock,      \* C holds the row's S lock
    latch,      \* readers that hold the hot page: subset of {"L", "C"}
    wpc,        \* [Writers -> index into Prog, or 0 when done]
    wop,        \* [Writers -> "UPDATE" | "DELETE" | "skip"]
    plan,       \* [Writers -> [stamps |-> set of refs, fresh |-> ref, passes |-> n]]
    wlog,       \* [Writers -> undo records, newest last]
    aborting,   \* [Writers -> TRUE while log_rollback runs]
    lpc, lver, lres,
    cpc, cver, catt, cres, csecond,
    last

wvars == <<wpc, wop, plan, wlog, aborting>>
lvars == <<lpc, lver, lres>>
cvars == <<cpc, cver, catt, cres, csecond>>
vars == <<cur, prev, store, nrec, committed, delDone, xlock, slock, latch, wvars, lvars, cvars, last>>
View == <<cur, prev, store, nrec, committed, delDone, xlock, slock, latch, wvars, lvars, cvars>>

Committed(t) == t = Init0 \/ t \in committed

Init ==
    /\ cur = [ref |-> 1, ins |-> Init0, del |-> NoTx]
    /\ prev = NoVer
    /\ store = [r \in 1..MaxRec |-> IF r = 1 THEN [st |-> "live", del |-> NoTx]
                                    ELSE [st |-> "none", del |-> NoTx]]
    /\ nrec = 2
    /\ committed = {} /\ delDone = FALSE
    /\ xlock = NoTx /\ slock = FALSE /\ latch = {}
    /\ wpc = [t \in Writers |-> 1]
    /\ wop = [t \in Writers |-> "skip"]
    /\ plan = [t \in Writers |-> [stamps |-> {}, fresh |-> 0, passes |-> 0]]
    /\ wlog = [t \in Writers |-> <<>>]
    /\ aborting = [t \in Writers |-> FALSE]
    /\ lpc = "l1" /\ lver = NoVer /\ lres = "none"
    /\ cpc = "c1" /\ cver = NoVer /\ catt = 0 /\ cres = "none" /\ csecond = FALSE
    /\ last = "start"

Step(t) == Prog[wpc[t]]
Advance(t) == wpc' = [wpc EXCEPT ![t] = @ + 1]
Goto(t, s) == wpc' = [wpc EXCEPT ![t] = CHOOSE i \in 1..Len(Prog) : Prog[i] = s]
HotFree == latch = {}   \* a writer's X latch on the hot page waits for the readers

---------------------------------------------------------------------------
\* Writers.

WLock(t) ==
    /\ wpc[t] > 0 /\ Step(t) = "lock" /\ ~aborting[t]
    /\ RowLock => (xlock = NoTx /\ ~slock)
    /\ \E op \in Ops :
         /\ wop' = [wop EXCEPT ![t] = op]
         /\ last' = t \o " takes the row's X lock for a " \o op
    /\ xlock' = IF RowLock THEN t ELSE xlock
    /\ Advance(t)
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, slock, latch, plan, wlog, aborting, lvars, cvars>>

\* heap_get_record_location, heap_sidecar_plan: sidecar_plan_update or
\* sidecar_plan_delete stamps the refs of the version read under the latch.
WPlan(t) ==
    /\ wpc[t] > 0 /\ Step(t) = "plan" /\ ~aborting[t] /\ HotFree
    /\ IF cur.del # NoTx
       THEN \* the row is deleted: the locator finds nothing to write
            /\ wpc' = [wpc EXCEPT ![t] = 0]
            /\ wop' = [wop EXCEPT ![t] = "skip"]
            /\ xlock' = IF xlock = t THEN NoTx ELSE xlock
            /\ committed' = committed \cup {t}
            /\ UNCHANGED plan
            /\ last' = t \o " finds the row deleted and ends"
       ELSE /\ plan' = [plan EXCEPT ![t] = [stamps |-> {cur.ref}, fresh |-> 0, passes |-> @.passes + 1]]
            /\ Advance(t)
            /\ UNCHANGED <<wop, xlock, committed>>
            /\ last' = t \o " plans under the hot latch: stamp store record " \o ToString(cur.ref)
                       \o "; heap_unfix_watchers releases the hot page"
    /\ UNCHANGED <<cur, prev, store, nrec, delDone, slock, latch, wlog, aborting, lvars, cvars>>

\* sidecar_insert_values: heap_insert_logical of the fresh value (UPDATE only).
WInsert(t) ==
    /\ wpc[t] > 0 /\ Step(t) = "insert" /\ ~aborting[t]
    /\ IF wop[t] = "UPDATE"
       THEN LET r == IF plan[t].fresh # 0 /\ store[plan[t].fresh].st = "none" THEN plan[t].fresh ELSE nrec
            IN /\ store' = [store EXCEPT ![r] = [st |-> "live", del |-> NoTx]]
               /\ nrec' = IF r = nrec THEN nrec + 1 ELSE nrec
               /\ plan' = [plan EXCEPT ![t].fresh = r]
               /\ wlog' = [wlog EXCEPT ![t] = Append(@, [k |-> "insert", r |-> r, v |-> NoVer, d |-> NoTx])]
               /\ last' = t \o " inserts store record " \o ToString(r) \o " (sidecar_insert_values)"
       ELSE /\ UNCHANGED <<store, nrec, plan, wlog>>
            /\ last' = t \o " has no fresh value"
    /\ Advance(t)
    /\ UNCHANGED <<cur, prev, committed, delDone, xlock, slock, latch, wop, aborting, lvars, cvars>>

\* sidecar_stamp_values: heap_delete_logical of each planned ref (MVCC DELID).
WStamp(t) ==
    /\ wpc[t] > 0 /\ Step(t) = "stamp" /\ ~aborting[t]
    /\ LET r == CHOOSE x \in plan[t].stamps : TRUE IN
       /\ store' = [store EXCEPT ![r].del = t]
       /\ wlog' = [wlog EXCEPT ![t] = Append(@, [k |-> "stamp", r |-> r, v |-> NoVer, d |-> store[r].del])]
       /\ last' = t \o " stamps store record " \o ToString(r) \o " (sidecar_stamp_values)"
    /\ Advance(t)
    /\ UNCHANGED <<cur, prev, nrec, committed, delDone, xlock, slock, latch, wop, plan, aborting, lvars, cvars>>

\* goto relocate: the hot page is fixed again and heap_sidecar_plan runs again.
WRelocate(t) ==
    /\ wpc[t] > 0 /\ Step(t) = "relocate" /\ ~aborting[t]
    /\ IF PlanOnce \/ plan[t].passes > 1
       THEN /\ Advance(t) /\ UNCHANGED plan
            /\ last' = t \o " fixes the hot page again; the applied plan returns at once"
       ELSE /\ Goto(t, "plan")
            /\ UNCHANGED plan
            /\ last' = t \o " fixes the hot page again and plans again"
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, xlock, slock, latch, wop, wlog, aborting, lvars, cvars>>

\* The hot write under the hot latch.
WHot(t) ==
    /\ wpc[t] > 0 /\ Step(t) = "hot" /\ ~aborting[t] /\ HotFree
    /\ IF wop[t] = "UPDATE"
       THEN LET r == IF plan[t].fresh # 0 THEN plan[t].fresh ELSE nrec IN
            /\ cur' = [ref |-> r, ins |-> t, del |-> NoTx]
            /\ prev' = cur
            /\ nrec' = IF r = nrec THEN nrec + 1 ELSE nrec
            /\ plan' = [plan EXCEPT ![t].fresh = r]
            /\ last' = t \o " writes the hot record, which names store record " \o ToString(r)
       ELSE /\ cur' = [cur EXCEPT !.del = t]
            /\ UNCHANGED <<prev, nrec, plan>>
            /\ last' = t \o " writes its DELID into the hot record"
    /\ wlog' = [wlog EXCEPT ![t] = Append(@, [k |-> "hot", r |-> 0, v |-> cur, d |-> NoTx])]
    /\ Advance(t)
    /\ UNCHANGED <<store, committed, delDone, xlock, slock, latch, wop, aborting, lvars, cvars>>

WCommit(t) ==
    /\ wpc[t] > 0 /\ Step(t) = "end" /\ ~aborting[t]
    /\ committed' = committed \cup {t}
    /\ delDone' = (delDone \/ wop[t] = "DELETE")
    /\ xlock' = IF xlock = t THEN NoTx ELSE xlock
    /\ wpc' = [wpc EXCEPT ![t] = 0]
    /\ last' = t \o " commits and releases the X lock"
    /\ UNCHANGED <<cur, prev, store, nrec, slock, latch, wop, plan, wlog, aborting, lvars, cvars>>

\* An error at any step after the lock, or the end: log_abort_local.
WAbort(t) ==
    /\ wpc[t] > 1 /\ ~aborting[t]
    /\ aborting' = [aborting EXCEPT ![t] = TRUE]
    /\ last' = t \o " fails and rolls back"
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, xlock, slock, latch, wpc, wop, plan, wlog, lvars, cvars>>

WUndo(t) ==
    /\ aborting[t] /\ wlog[t] # <<>>
    /\ LET u == wlog[t][Len(wlog[t])] IN
       /\ u.k = "hot" => HotFree
       /\ cur' = IF u.k = "hot" THEN u.v ELSE cur
       /\ store' = CASE u.k = "insert" -> [store EXCEPT ![u.r] = [st |-> "gone", del |-> NoTx]]
                     [] u.k = "stamp" -> [store EXCEPT ![u.r].del = u.d]
                     [] OTHER -> store
       /\ last' = t \o " undoes its " \o u.k
    /\ wlog' = [wlog EXCEPT ![t] = SubSeq(@, 1, Len(@) - 1)]
    /\ UNCHANGED <<prev, nrec, committed, delDone, xlock, slock, latch, wpc, wop, plan, aborting, lvars, cvars>>

WAbortEnd(t) ==
    /\ aborting[t] /\ wlog[t] = <<>> /\ wpc[t] > 0
    /\ wpc' = [wpc EXCEPT ![t] = 0]
    /\ xlock' = IF xlock = t THEN NoTx ELSE xlock
    /\ last' = t \o " ends its rollback and releases the X lock"
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, slock, latch, wop, plan, wlog, aborting, lvars, cvars>>

\* Store vacuum removes a store record whose stamp committed.
Vacuum(r) ==
    /\ store[r].st = "live" /\ store[r].del # NoTx /\ Committed(store[r].del)
    /\ store' = [store EXCEPT ![r].st = "gone"]
    /\ last' = "store vacuum removes store record " \o ToString(r)
    /\ UNCHANGED <<cur, prev, nrec, committed, delDone, xlock, slock, latch, wvars, lvars, cvars>>

---------------------------------------------------------------------------
\* L: SIDECAR_READER_LATCHED, the store records read with the hot page held.

L1 ==
    /\ lpc = "l1"
    /\ latch' = latch \cup {"L"}
    /\ lver' = cur /\ lpc' = "l2"
    /\ last' = "L read-latches the hot page and finds a version that names store record " \o ToString(cur.ref)
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, xlock, slock, wvars, lres, cvars>>

L2 ==
    /\ lpc = "l2"
    /\ lres' = IF store[lver.ref].st = "live" THEN "ok"
               ELSE IF DelidTest /\ lver.del # NoTx /\ Committed(lver.del) THEN "doesnt_exist"
               ELSE "error"
    /\ latch' = latch \ {"L"}
    /\ lpc' = "done"
    /\ last' = "L reads store record " \o ToString(lver.ref) \o ": " \o store[lver.ref].st
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, xlock, slock, wvars, lver, cvars>>

---------------------------------------------------------------------------
\* C: the committed-snapshot fetch of xlocator_fetch.

VisCommitted == IF Committed(cur.ins) THEN cur ELSE prev

C1 ==
    /\ cpc = "c1"
    /\ LET v == VisCommitted
           heap == Committed(cur.ins)
       IN IF v.del # NoTx /\ Committed(v.del)
          THEN /\ cres' = "doesnt_exist" /\ cpc' = "done" /\ UNCHANGED <<latch, cver>>
               /\ last' = "C finds the row's delete committed"
          ELSE /\ cver' = v /\ cpc' = "c2"
               /\ latch' = IF heap THEN latch \cup {"C"} ELSE latch
               /\ UNCHANGED cres
               /\ last' = "C reads the committed version from the " \o (IF heap THEN "heap, under the hot latch" ELSE "log")
                          \o ", which names store record " \o ToString(v.ref)
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, xlock, slock, wvars, lvars, catt, csecond>>

C2 ==
    /\ cpc = "c2"
    /\ latch' = latch \ {"C"}
    /\ IF store[cver.ref].st = "live"
       THEN /\ cres' = "ok" /\ cpc' = "done" /\ UNCHANGED catt
            /\ last' = "C reads store record " \o ToString(cver.ref)
       ELSE IF DelidTest /\ cver.del # NoTx /\ Committed(cver.del)
       THEN /\ cres' = "doesnt_exist" /\ cpc' = "done" /\ UNCHANGED catt
            /\ last' = "C finds store record " \o ToString(cver.ref) \o " absent and the delete committed"
       ELSE IF OnAbsent = "doesnt_exist"
       THEN /\ cres' = "doesnt_exist" /\ cpc' = "done" /\ UNCHANGED catt
            /\ last' = "C finds store record " \o ToString(cver.ref) \o " absent and reports the row missing"
       ELSE IF catt < RetryBound
       THEN /\ catt' = catt + 1 /\ cpc' = "c1" /\ UNCHANGED cres
            /\ last' = "C finds store record " \o ToString(cver.ref) \o " absent: S_SIDECAR_RETRY"
       ELSE IF Fallback /\ ~csecond
       THEN /\ cpc' = "f1" /\ UNCHANGED <<cres, catt>>
            /\ last' = "C finds store record " \o ToString(cver.ref) \o " absent after the bound: S_SIDECAR_LOCK_NEEDED"
       ELSE /\ cres' = "error" /\ cpc' = "done" /\ UNCHANGED catt
            /\ last' = "C fails with ER_SIDECAR_RESOLVE_RETRY"
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, xlock, slock, wvars, lvars, cver, csecond>>

\* sidecar_fetch_locked: lock_object (S_LOCK).
F1 ==
    /\ cpc = "f1"
    /\ FallbackLock = "s_lock_around_read" => xlock = NoTx
    /\ slock' = (FallbackLock = "s_lock_around_read")
    /\ cpc' = "f2"
    /\ last' = IF FallbackLock = "s_lock_around_read" THEN "C takes the row's S lock" ELSE "C takes no lock"
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, xlock, latch, wvars, lvars, cver, catt, cres, csecond>>

\* heap_get_last_version with sidecar_on_fetch (SIDECAR_READER_HOLDER), the
\* committed-snapshot test, and lock_unlock_object.
F2 ==
    /\ cpc = "f2" /\ HotFree
    /\ LET v == cur
           present == store[v.ref].st = "live"
       IN IF ~present
          THEN /\ cres' = IF DelidTest /\ v.del # NoTx /\ Committed(v.del) THEN "doesnt_exist" ELSE "error"
               /\ cpc' = "done" /\ UNCHANGED <<catt, csecond>>
               /\ last' = "C reads the last version as a lock holder: store record " \o ToString(v.ref) \o " absent"
          ELSE IF Committed(v.ins)
          THEN /\ cres' = IF v.del # NoTx /\ Committed(v.del) THEN "doesnt_exist" ELSE "ok"
               /\ cpc' = "done" /\ UNCHANGED <<catt, csecond>>
               /\ last' = "C reads the last version as a lock holder and it satisfies the snapshot"
          ELSE \* the default branch: heap_get_visible_version again, from attempt 0
               /\ cpc' = "c1" /\ catt' = 0 /\ csecond' = TRUE /\ UNCHANGED cres
               /\ last' = "C finds an uncommitted last version and reads the visible one again"
    /\ slock' = FALSE
    /\ UNCHANGED <<cur, prev, store, nrec, committed, delDone, xlock, latch, wvars, lvars, cver>>

---------------------------------------------------------------------------
Done == /\ \A t \in Writers : wpc[t] = 0
        /\ lpc = "done" /\ cpc = "done"
        /\ UNCHANGED vars

Next ==
    \/ \E t \in Writers : WLock(t) \/ WPlan(t) \/ WInsert(t) \/ WStamp(t) \/ WRelocate(t)
                          \/ WHot(t) \/ WCommit(t) \/ WAbort(t) \/ WUndo(t) \/ WAbortEnd(t)
    \/ \E r \in 1..MaxRec : Vacuum(r)
    \/ L1 \/ L2 \/ C1 \/ C2 \/ F1 \/ F2
    \/ Done

Spec == Init /\ [][Next]_vars

---------------------------------------------------------------------------
AllWritersDone == \A t \in Writers : wpc[t] = 0

LatchedReaderFinds == lres # "error"
FetchNoError == cres # "error"
FetchNoLostRow == cres = "doesnt_exist" => delDone
StoreMatchesRow ==
    AllWritersDone =>
        {r \in 1..MaxRec : store[r].st = "live" /\ store[r].del = NoTx}
            = (IF cur.del # NoTx THEN {} ELSE {cur.ref})
=============================================================================
