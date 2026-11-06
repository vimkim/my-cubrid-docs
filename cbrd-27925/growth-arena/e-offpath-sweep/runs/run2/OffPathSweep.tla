---------------------------- MODULE OffPathSweep ----------------------------
(***************************************************************************)
(* Off-path reclaim of emptied OOS pages, with a synchronous fallback on   *)
(* the allocation path when the off-path worker is behind by more than a   *)
(* slack S (CBRD-27925 growth arena, candidate e-offpath-sweep).           *)
(*                                                                         *)
(* Data shape: per file, a set E of VPIDs that a delete emptied and that   *)
(* nobody has reclaimed yet (the "debt"), plus a flag `unknown` that is    *)
(* TRUE after a restart until one discovery lap has covered the file.     *)
(* Every delete that empties a page adds it to E (vacuum chain delete and  *)
(* the INSERT-rollback undo).  An INSERT that writes an empty page removes *)
(* it from E.                                                              *)
(*                                                                         *)
(* Actors:                                                                 *)
(*   worker  the off-path reclaimer (vacuum fast path + a daemon).  It     *)
(*           takes a member of E under a zero-wait READ fix (WorkerPick)   *)
(*           and later deallocates it under a zero-wait WRITE fix          *)
(*           (WorkerFree).  Between the two steps any other actor may      *)
(*           run.  While `unknown`, it may run a background discovery lap. *)
(*   grower  one grow at a time (per-file single flight).  It checks |E|   *)
(*           in O(1); only when the debt it can act on exceeds S does it   *)
(*           reclaim a member of E itself.  When `unknown`, Boot decides:  *)
(*             sync      the grow runs the discovery lap itself first      *)
(*             bg        the grow ignores `unknown` (worker lap only)      *)
(*             bg_slack  S grows may skip the lap; then the grow runs it   *)
(*   inserts into existing pages, vacuum chunk deletes, one INSERT         *)
(*   rollback undo that WRITE-latches a page while it deletes a chunk     *)
(*   (at most one new latch per grow, as in OosGrowthBound.tla), crashes. *)
(*                                                                         *)
(* Fallback = FALSE is the pure off-path design: the grower never reclaims.*)
(* Worker = FALSE, S = 0, Boot = "sync" is cand_fullboot without the       *)
(* vacuum fast path; Worker = TRUE, S = 0, Boot = "sync" is cand_fullboot  *)
(* with it (the worker stands for the fast path and any drain).            *)
(*                                                                         *)
(* Post-ADR-0008 target: no LSA gate, chunk deletes are never undone.      *)
(* MaxCrash > 0 limits the number of restarts (0: unlimited).              *)
(* One page is one sector; R, the number of reserved pages, is the file    *)
(* size.  R never shrinks.                                                 *)
(***************************************************************************)
EXTENDS Integers, FiniteSets, Sequences, TLC

CONSTANTS MaxPages, Cap, L, S, Fallback, Boot, Worker, Recheck, Order,
          Crashes, MaxCrash, WritesDuringGrow,
          TrackGap, TrackCost  \* FALSE keeps stale or examined constant (smaller runs)

ASSUME Boot \in {"sync", "bg", "bg_slack"} /\ Order \in {"any", "fifo"}
ASSUME MaxCrash \in Nat /\ S \in Nat /\ MaxPages \in Nat \ {0} /\ Cap \in Nat \ {0} /\ L \in Nat \ {0}

Pages == 1..MaxPages
FREE == -1

VARIABLES
  pg,        \* page -> FREE or chunk count
  R,         \* reserved pages 1..R (file size)
  live,      \* chunks in the file (the truth; pg must agree)
  busy,      \* page WRITE-latched by the rollback undo, 0 if none
  Q,         \* emptied pages not yet reclaimed (the debt queue; E is its set)
  unknown,   \* E may miss pages emptied before the last restart
  grace,     \* bg_slack: grows left that may skip the lap while unknown
  gpc,       \* grower: idle | lap | sync | alloc
  glap,      \* grower discovery lap: pages left to visit (visits glap, glap-1, ..., 1)
  chk,       \* busy members of E this grow already passed over
  examined,  \* pages the grower fixed in this grow (allocation-path cost)
  wpc,       \* worker: idle | fixed
  wp,        \* page the worker READ-checked and will try to free
  wlapOn,    \* worker discovery lap in progress
  wlap,      \* worker lap: pages left to visit
  stale,     \* pages empty at grow start that nothing wrote or latched since
  ncrash,    \* restarts so far (stays 0 when MaxCrash = 0: unlimited restarts)
  overflow,  \* the file needed more than MaxPages
  relatched  \* the undo took a latch during this grow

vars == <<pg, R, live, busy, Q, unknown, grace, gpc, glap, chk, examined,
          wpc, wp, wlapOn, wlap, stale, ncrash, overflow, relatched>>

Reserved == 1..R
E == {Q[i] : i \in DOMAIN Q}
(* fifo: append; any: keep Q sorted so the order adds no states. *)
Add(q, p) == IF \E i \in DOMAIN q : q[i] = p THEN q
             ELSE IF Order = "fifo" THEN Append(q, p)
             ELSE SelectSeq(q, LAMBDA x : x < p) \o <<p>> \o SelectSeq(q, LAMBDA x : x > p)
Del(q, p) == SelectSeq(q, LAMBDA x : x # p)
EmptyPages == {p \in Reserved : pg[p] = 0}
RECURSIVE ChunksUpTo(_)
ChunksUpTo(n) == IF n = 0 THEN 0 ELSE (IF pg[n] = FREE THEN 0 ELSE pg[n]) + ChunksUpTo(n - 1)
Chunks == ChunksUpTo(MaxPages)

Init ==
  /\ pg = [p \in Pages |-> FREE]
  /\ R = 0 /\ live = 0 /\ busy = 0
  /\ Q = <<>> /\ unknown = FALSE /\ grace = 0       \* the file was created this boot
  /\ gpc = "idle" /\ glap = 0 /\ chk = {} /\ examined = 0
  /\ wpc = "idle" /\ wp = 0 /\ wlapOn = FALSE /\ wlap = 0
  /\ stale = {} /\ ncrash = 0 /\ overflow = FALSE /\ relatched = FALSE

GrowVars == <<gpc, glap, chk, examined, grace>>
WorkVars == <<wpc, wp, wlapOn, wlap>>

-----------------------------------------------------------------------------
(* Foreground writers *)

Insert ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ live + (IF gpc # "idle" THEN 1 ELSE 0) < L
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] < Cap /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = @ + 1]
       /\ live' = live + 1
       /\ stale' = stale \ {p}
       /\ Q' = Del(Q, p)            \* page_was_empty is seen under the page latch
  /\ UNCHANGED <<R, busy, unknown, ncrash, overflow, relatched>>
  /\ UNCHANGED GrowVars /\ UNCHANGED WorkVars

VacuumDelete ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0 /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ Q' = IF pg[p] = 1 THEN Add(Q, p) ELSE Q
       /\ stale' = stale \ {p}
  /\ UNCHANGED <<R, busy, unknown, ncrash, overflow, relatched>>
  /\ UNCHANGED GrowVars /\ UNCHANGED WorkVars

(* oos_rv_redo_delete: deletes the chunk under the page WRITE latch and notes the page. *)
UndoLatch ==
  /\ busy = 0
  /\ (gpc = "idle" \/ ~relatched)
  /\ relatched' = (gpc # "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0
       /\ busy' = p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ Q' = IF pg[p] = 1 THEN Add(Q, p) ELSE Q
       /\ stale' = stale \ {p}
  /\ UNCHANGED <<R, unknown, ncrash, overflow>>
  /\ UNCHANGED GrowVars /\ UNCHANGED WorkVars

UndoRelease ==
  /\ busy # 0
  /\ busy' = 0
  /\ UNCHANGED <<pg, R, live, Q, unknown, stale, ncrash, overflow, relatched>>
  /\ UNCHANGED GrowVars /\ UNCHANGED WorkVars

(* Restart: pages persist; E and every other in-memory hint is lost. *)
Crash ==
  /\ Crashes
  /\ (MaxCrash = 0 \/ ncrash < MaxCrash)
  /\ ncrash' = IF MaxCrash = 0 THEN 0 ELSE ncrash + 1
  /\ busy' = 0 /\ Q' = <<>> /\ unknown' = TRUE /\ grace' = S
  /\ gpc' = "idle" /\ glap' = 0 /\ chk' = {} /\ examined' = 0
  /\ wpc' = "idle" /\ wp' = 0 /\ wlapOn' = FALSE /\ wlap' = 0
  /\ stale' = {} /\ relatched' = FALSE
  /\ UNCHANGED <<pg, R, live, overflow>>

-----------------------------------------------------------------------------
(* The off-path worker *)

(* Zero-wait READ fix of a debt page: an empty one is held for the free step; a latched one
   cannot be fixed, so the step is not enabled for it. *)
WorkerPickP(p) ==
  /\ Worker /\ wpc = "idle" /\ Q # <<>>
  /\ p \in (IF Order = "fifo" THEN {Head(Q)} ELSE E)
  /\ IF busy = p
     THEN /\ Order = "fifo"                             \* busy head: re-queue at the tail
          /\ Len(Q) > 1
          /\ Q' = Append(Tail(Q), p) /\ UNCHANGED <<wpc, wp>>
     ELSE IF pg[p] = 0
     THEN wpc' = "fixed" /\ wp' = p /\ UNCHANGED Q
     ELSE Q' = Del(Q, p) /\ UNCHANGED <<wpc, wp>>
  /\ UNCHANGED <<pg, R, live, busy, unknown, stale, ncrash, overflow, relatched, wlapOn, wlap>>
  /\ UNCHANGED GrowVars

WorkerPick == \E p \in Pages : WorkerPickP(p)

(* Zero-wait WRITE fix and dealloc.  With Recheck, the free re-checks emptiness and the latch
   under the WRITE fix (oos_try_reclaim_page_internal phase 2).  Without it, the step trusts
   the READ verdict: the bug the safety invariant must catch. *)
WorkerFree ==
  /\ wpc = "fixed"
  /\ wpc' = "idle" /\ wp' = 0
  /\ LET p == wp IN
     IF Recheck
     THEN IF pg[p] = 0 /\ busy # p
          THEN pg' = [pg EXCEPT ![p] = FREE] /\ Q' = Del(Q, p) /\ stale' = stale \ {p}
          ELSE IF busy = p
               THEN Q' = Add(Del(Q, p), p) /\ UNCHANGED <<pg, stale>> \* DEFERRED: re-queued
               ELSE Q' = Del(Q, p) /\ UNCHANGED <<pg, stale>> \* refilled or already freed
     ELSE IF pg[p] # FREE /\ busy # p
          THEN pg' = [pg EXCEPT ![p] = FREE] /\ Q' = Del(Q, p) /\ stale' = stale \ {p}
          ELSE UNCHANGED <<pg, Q, stale>>
  /\ UNCHANGED <<R, live, busy, unknown, ncrash, overflow, relatched, wlapOn, wlap>>
  /\ UNCHANGED GrowVars

(* Background discovery lap after a restart: every empty page (latched or not) goes into E.
   Deleters keep adding to E during the lap, so a page emptied behind the lap is still known. *)
WorkerLap ==
  /\ Worker /\ wpc = "idle" /\ unknown
  /\ IF ~wlapOn
     THEN wlapOn' = TRUE /\ wlap' = R /\ UNCHANGED <<Q, unknown>>
     ELSE IF wlap = 0
          THEN wlapOn' = FALSE /\ unknown' = FALSE /\ UNCHANGED <<Q, wlap>>
          ELSE /\ wlap' = wlap - 1
               /\ Q' = IF pg[wlap] = 0 THEN Add(Q, wlap) ELSE Q
               /\ UNCHANGED <<wlapOn, unknown>>
  /\ UNCHANGED <<pg, R, live, busy, stale, ncrash, overflow, relatched, wpc, wp>>
  /\ UNCHANGED GrowVars

-----------------------------------------------------------------------------
(* The grower *)

StartGrow ==
  /\ gpc = "idle" /\ live < L
  /\ stale' = IF TrackGap THEN EmptyPages \ {busy} ELSE {}
  /\ relatched' = FALSE
  /\ IF unknown /\ (Boot = "sync" \/ (Boot = "bg_slack" /\ grace = 0))
     THEN gpc' = "lap" /\ glap' = R /\ UNCHANGED grace
     ELSE /\ gpc' = "sync" /\ UNCHANGED glap
          /\ grace' = IF unknown /\ Boot = "bg_slack" THEN grace - 1 ELSE grace
  /\ UNCHANGED <<pg, R, live, busy, Q, unknown, chk, examined, ncrash, overflow>>
  /\ UNCHANGED WorkVars

(* Synchronous discovery lap on the allocation path. *)
LapStep ==
  /\ gpc = "lap"
  /\ IF ~unknown \/ glap = 0
     THEN /\ gpc' = "sync" /\ glap' = 0
          /\ unknown' = FALSE
          /\ wlapOn' = FALSE /\ wlap' = 0
          /\ UNCHANGED <<Q, examined>>
     ELSE /\ glap' = glap - 1
          /\ examined' = IF TrackCost THEN examined + 1 ELSE 0
          /\ Q' = IF pg[glap] = 0 THEN Add(Q, glap) ELSE Q
          /\ UNCHANGED <<gpc, unknown, wlapOn, wlap>>
  /\ UNCHANGED <<pg, R, live, busy, grace, chk, stale, ncrash, overflow, relatched, wpc, wp>>

(* O(1) debt check; a synchronous reclaim only while the debt exceeds the slack. *)
SyncStep ==
  /\ gpc = "sync"
  /\ LET debt == E \ chk IN
     IF ~Fallback \/ Cardinality(debt) <= S
     THEN gpc' = "alloc" /\ UNCHANGED <<pg, Q, chk, examined, stale>>
     ELSE \E p \in debt :
            /\ examined' = IF TrackCost THEN examined + 1 ELSE 0
            /\ IF busy = p
               THEN chk' = chk \cup {p} /\ stale' = stale \ {p} /\ UNCHANGED <<pg, Q, gpc>>
               ELSE IF pg[p] = 0
                    THEN /\ pg' = [pg EXCEPT ![p] = FREE]
                         /\ Q' = Del(Q, p)
                         /\ gpc' = "alloc"
                         /\ UNCHANGED <<chk, stale>>
                    ELSE Q' = Del(Q, p) /\ UNCHANGED <<pg, gpc, chk, stale>>
  /\ UNCHANGED <<R, live, busy, unknown, grace, glap, ncrash, overflow, relatched>>
  /\ UNCHANGED WorkVars

(* file_alloc: a free page in a reserved sector first (one the worker or the grower freed),
   else reserve a new one. *)
Alloc ==
  /\ gpc = "alloc"
  /\ gpc' = "idle" /\ chk' = {} /\ examined' = 0 /\ stale' = {} /\ relatched' = FALSE
  /\ IF \E p \in Reserved : pg[p] = FREE
     THEN \E p \in {q \in Reserved : pg[q] = FREE} :
            /\ pg' = [pg EXCEPT ![p] = 1]
            /\ live' = live + 1
            /\ Q' = Del(Q, p)
            /\ UNCHANGED <<R, overflow>>
     ELSE IF R < MaxPages
          THEN /\ R' = R + 1
               /\ pg' = [pg EXCEPT ![R + 1] = 1]
               /\ live' = live + 1
               /\ UNCHANGED <<Q, overflow>>
          ELSE /\ overflow' = TRUE
               /\ UNCHANGED <<pg, R, live, Q>>
  /\ UNCHANGED <<busy, unknown, grace, glap, ncrash>>
  /\ UNCHANGED WorkVars

WorkerNext == WorkerPick \/ WorkerFree \/ WorkerLap

Next ==
  \/ Insert \/ VacuumDelete \/ UndoLatch \/ UndoRelease \/ Crash
  \/ WorkerNext
  \/ StartGrow \/ LapStep \/ SyncStep \/ Alloc

Spec == Init /\ [][Next]_vars

(* WeakSpec: weak fairness for the worker as a whole and for the undo's latch release.
   Nothing else is fair: the foreground may stop at any time.  With Order = "fifo" the worker
   takes the head of Q and re-queues a latched head, so no member is passed over forever. *)
WeakSpec ==
  /\ Spec
  /\ WF_vars(WorkerNext)
  /\ WF_vars(UndoRelease)

-----------------------------------------------------------------------------
(* Properties *)

TypeOK ==
  /\ pg \in [Pages -> {FREE} \cup 0..Cap]
  /\ R \in 0..MaxPages /\ live \in 0..L /\ busy \in 0..MaxPages
  /\ Q \in Seq(Pages) /\ Cardinality(E) = Len(Q) /\ chk \subseteq Pages /\ stale \subseteq Pages
  /\ gpc \in {"idle", "lap", "sync", "alloc"} /\ wpc \in {"idle", "fixed"}

(* Safety: no chunk is lost by a dealloc, pages past R are unreserved, the latched page is
   allocated, and E lists only reserved pages. *)
Safe ==
  /\ live = Chunks
  /\ E \subseteq Reserved
  /\ \A p \in Pages : p > R => pg[p] = FREE
  /\ busy # 0 => (busy \in Reserved /\ pg[busy] # FREE)

(* Every page that is empty while the worker knows nothing is missing is in E. *)
DebtExact == ~unknown => EmptyPages \subseteq E

NoOverflow == ~overflow

(* Pages that were empty when this grow started, that nothing wrote or latched since, and that are
   still empty and unlatched.  On a reserving step it counts the pages the grow left behind. *)
GapNow == Cardinality({p \in stale : pg[p] = 0 /\ busy # p})
Reserves == R' > R
(* Strict rule, checked on every reserving step: the grow leaves no such page behind. *)
Strict == [][Reserves => GapNow = 0]_vars

(* Measurement: TLC registers keep, per worker thread, the largest value seen so far; run.py takes
   the maximum over all printed values.  Both formulas are always TRUE. *)
ASSUME TLCSet(1, 0) /\ TLCSet(2, 0) /\ TLCSet(3, 0)
Hi(i, v) == IF v > TLCGet(i) THEN TLCSet(i, v) /\ PrintT(<<"HI", i, v>>) ELSE TRUE
Measure == Hi(1, R) /\ Hi(2, examined)        \* invariant: file size, pages fixed in one grow
GapMeasure == [][Reserves => Hi(3, GapNow)]_vars   \* property: pages left behind at a reservation

(* Liveness: a page that is empty is eventually reclaimed or written again. *)
EmptyEventuallyGone == \A p \in Pages : [](pg[p] = 0 => <>(pg[p] # 0))
=============================================================================
