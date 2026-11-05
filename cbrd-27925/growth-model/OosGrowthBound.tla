---------------------------- MODULE OosGrowthBound ----------------------------
(***************************************************************************)
(* Growth of one OOS file under insert/delete/rollback churn, for five     *)
(* designs of the growth-side reclaim (CBRD-27925, Work821).               *)
(*                                                                         *)
(* A page is FREE (not allocated, inside a reserved sector) or holds       *)
(* 0..Cap chunks.  One page is one sector here, so R, the number of        *)
(* reserved pages, is the file size on disk.  Sectors are never returned   *)
(* to the disk (file_destroy only), so R never shrinks.                    *)
(*                                                                         *)
(* Actors: inserts into existing pages (bestspace hits), one grower (the   *)
(* per-file single-flight sweep serializes growers), vacuum chunk deletes, *)
(* the vacuum fast path, one INSERT-rollback undo that holds the page      *)
(* WRITE latch while it deletes a chunk and notes it, and crashes that     *)
(* drop every in-memory hint.  An insert may always choose to grow, as if  *)
(* every bestspace hint were lost.  The undo takes at most one new latch   *)
(* per grow: a zero-wait check cannot win against a scheduler that moves   *)
(* a latch onto each page just before the grower reaches it, so no design  *)
(* bounds growth without a bound on concurrent latch holders.  When       *)
(* WritesDuringGrow is FALSE, inserts and deletes wait for the grow to    *)
(* end; the undo may still release its latch mid-grow.                    *)
(*                                                                         *)
(* Designs:                                                                *)
(*   none        no growth-side reclaim (also: a background sweep that is  *)
(*               never scheduled)                                          *)
(*   full_skip   d52b1889e: any chunk delete arms; a lap walks the whole   *)
(*               file from the cursor, stops at the first reclaim; a page  *)
(*               busy under a latch is SKIPPED                             *)
(*   full_defer  full_skip, but a busy page is DEFERRED (keeps it armed)   *)
(*   budget      full_defer, but a grow examines at most N pages and the   *)
(*               lap resumes on the next grow                              *)
(*   full_retry  full_skip, plus Work818 option (b): a page that the       *)
(*               rollback callback empties goes into a retry set that      *)
(*               every grow checks first                                   *)
(*   cand        an exact set of emptied pages; only a delete that empties *)
(*               a page adds it.  A grow checks the set.  After hint loss  *)
(*               (crash) one lap covers the whole file, unbudgeted when    *)
(*               FallbackFull, else N pages per grow                       *)
(***************************************************************************)
EXTENDS Integers, FiniteSets

CONSTANTS Design, MaxPages, Cap, L, N, FallbackFull, Crashes, WritesDuringGrow, Bound, CostBound

ASSUME Design \in {"none", "full_skip", "full_defer", "full_retry", "budget", "cand"}
ASSUME MaxPages \in Nat \ {0} /\ Cap \in Nat \ {0} /\ L \in Nat \ {0} /\ N \in Nat \ {0}

Pages == 1..MaxPages
FREE == -1

VARIABLES
  pg,           \* page -> FREE or chunk count
  R,            \* reserved pages 1..R (file size)
  live,         \* chunks in the file
  busy,         \* page WRITE-latched by the rollback undo, 0 if none
  armed,        \* full/budget: pending_deletes > 0
  swept,        \* full/budget: swept_this_boot
  lapOn,        \* a lap is in progress
  lapLeft,      \* pages the lap still has to visit
  lapNote,      \* a delete was noted while the lap ran
  lapDefer,     \* the lap deferred a busy page
  cursor,       \* last page the sweep visited
  gpc,          \* grower: idle | cand | scan | alloc
  budget,       \* pages this grow may still examine (budgeted scans)
  examined,     \* pages examined by this grow (cost)
  checked,      \* busy candidates this grow already passed over
  cand,         \* cand: emptied pages not yet checked; full_retry: the retry set
  unknown,      \* cand: the set may be incomplete (hint loss)
  stale,        \* pages empty when this grow started that nothing wrote or latched since
  strongBroken, \* a grow reserved a page while a stale empty page existed
  overflow,     \* the file needed more than MaxPages
  relatched,    \* the undo took a latch during this grow
  startClean    \* no page was empty when this grow started or emptied since

vars == <<pg, R, live, busy, armed, swept, lapOn, lapLeft, lapNote, lapDefer, cursor,
          gpc, budget, examined, checked, cand, unknown, stale, strongBroken, overflow, relatched, startClean>>

Counted == Design \in {"full_skip", "full_defer", "full_retry", "budget"}
HasSet == Design \in {"cand", "full_retry"}
Budgeted == Design = "budget" \/ (Design = "cand" /\ ~FallbackFull)

Reserved == 1..R
EmptyPages == {p \in Reserved : pg[p] = 0}

Init ==
  /\ pg = [p \in Pages |-> FREE]
  /\ R = 0 /\ live = 0 /\ busy = 0
  /\ armed = FALSE /\ swept = TRUE          \* the file was created this boot
  /\ lapOn = FALSE /\ lapLeft = 0 /\ lapNote = FALSE /\ lapDefer = FALSE
  /\ cursor = 0 /\ gpc = "idle" /\ budget = 0 /\ examined = 0 /\ checked = {}
  /\ cand = {} /\ unknown = FALSE /\ stale = {}
  /\ strongBroken = FALSE /\ overflow = FALSE /\ relatched = FALSE /\ startClean = FALSE

(* Bookkeeping of one chunk delete on page p that leaves k chunks; undo marks the rollback
   callback. *)
NoteDelete(p, k, undo) ==
  /\ armed' = (armed \/ Counted)
  /\ lapNote' = (lapNote \/ (lapOn /\ Counted))
  /\ cand' = IF k = 0 /\ (Design = "cand" \/ (Design = "full_retry" /\ undo))
             THEN cand \cup {p} ELSE cand

-----------------------------------------------------------------------------
(* Other actors *)

Insert ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ live + (IF gpc # "idle" THEN 1 ELSE 0) < L
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] < Cap /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = @ + 1]
       /\ live' = live + 1
       /\ stale' = stale \ {p}
       \* The insert path sees page_was_empty under its latch, so it can drop the entry.  A
       \* lazily dropped entry would cost one later check and change no verdict.
       /\ cand' = cand \ {p}
  /\ UNCHANGED <<R, busy, armed, swept, lapOn, lapLeft, lapNote, lapDefer, cursor, gpc,
                 budget, examined, checked, unknown, strongBroken, overflow, relatched, startClean>>

VacuumDelete ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0 /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ NoteDelete(p, pg[p] - 1, FALSE)
       /\ stale' = stale \ {p}
       /\ startClean' = (startClean /\ pg[p] > 1)
  /\ UNCHANGED <<R, busy, swept, lapOn, lapLeft, lapDefer, cursor, gpc, budget, examined,
                 checked, unknown, strongBroken, overflow, relatched>>

(* The vacuum fast path: may reclaim any empty unlatched page, or miss it. *)
FastPath ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ \E p \in EmptyPages :
       /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = FREE]
       /\ cand' = cand \ {p}
       /\ stale' = stale \ {p}
  /\ UNCHANGED <<R, live, busy, armed, swept, lapOn, lapLeft, lapNote, lapDefer, cursor, gpc,
                 budget, examined, checked, unknown, strongBroken, overflow, relatched, startClean>>

(* INSERT rollback: oos_rv_redo_delete deletes the chunk and notes it under the WRITE latch. *)
UndoLatch ==
  /\ busy = 0
  /\ (gpc = "idle" \/ ~relatched)
  /\ relatched' = (gpc # "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0
       /\ busy' = p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ NoteDelete(p, pg[p] - 1, TRUE)
       /\ stale' = stale \ {p}
       /\ startClean' = (startClean /\ pg[p] > 1)
  /\ UNCHANGED <<R, swept, lapOn, lapLeft, lapDefer, cursor, gpc, budget, examined, checked,
                 unknown, strongBroken, overflow>>

UndoRelease ==
  /\ busy # 0
  /\ busy' = 0
  /\ UNCHANGED <<pg, R, live, armed, swept, lapOn, lapLeft, lapNote, lapDefer, cursor, gpc,
                 budget, examined, checked, cand, unknown, stale, strongBroken, overflow, relatched, startClean>>

(* Restart: pages persist; every in-memory hint is lost; the boot rule applies. *)
Crash ==
  /\ Crashes
  /\ busy' = 0 /\ gpc' = "idle"
  /\ armed' = FALSE /\ swept' = ~Counted
  /\ lapOn' = FALSE /\ lapLeft' = 0 /\ lapNote' = FALSE /\ lapDefer' = FALSE
  /\ cursor' = 0 /\ budget' = 0 /\ examined' = 0 /\ checked' = {}
  /\ cand' = {} /\ unknown' = (Design = "cand")
  /\ stale' = {} /\ relatched' = FALSE /\ startClean' = FALSE
  /\ UNCHANGED <<pg, R, live, strongBroken, overflow>>

-----------------------------------------------------------------------------
(* The grower *)

StartLap ==
  /\ lapOn' = TRUE /\ lapLeft' = R /\ lapNote' = FALSE /\ lapDefer' = FALSE

KeepLap == UNCHANGED <<lapOn, lapLeft, lapNote, lapDefer>>

StartGrow ==
  /\ gpc = "idle" /\ live < L
  /\ budget' = N
  /\ stale' = EmptyPages \ {busy}
  /\ relatched' = FALSE
  /\ startClean' = (EmptyPages = {})
  /\ CASE Design = "none" -> gpc' = "alloc" /\ KeepLap
       [] HasSet -> gpc' = "cand" /\ KeepLap
       [] OTHER ->
            IF lapOn
            THEN gpc' = "scan" /\ KeepLap
            ELSE IF armed \/ ~swept
                 THEN gpc' = "scan" /\ StartLap
                 ELSE gpc' = "alloc" /\ KeepLap
  /\ UNCHANGED <<pg, R, live, busy, armed, swept, cursor, examined, checked, cand, unknown,
                 strongBroken, overflow>>

(* cand, full_retry: check one set member; a busy one stays for a later grow.  When the set
   is done, cand scans only after hint loss and full_retry continues as full_skip. *)
CandStep ==
  /\ gpc = "cand"
  /\ IF cand \ checked = {}
     THEN /\ IF Design = "cand"
             THEN IF unknown
                  THEN /\ gpc' = "scan"
                       /\ IF lapOn THEN KeepLap ELSE StartLap
                  ELSE /\ gpc' = "alloc"
                       /\ KeepLap
             ELSE IF armed \/ ~swept
                  THEN gpc' = "scan" /\ StartLap
                  ELSE gpc' = "alloc" /\ KeepLap
          /\ UNCHANGED <<pg, cand, checked, examined, stale>>
     ELSE \E p \in cand \ checked :
            /\ examined' = examined + 1
            /\ IF busy = p
               THEN /\ checked' = checked \cup {p}
                    /\ stale' = stale \ {p}
                    /\ UNCHANGED <<pg, cand, gpc>>
               ELSE IF pg[p] = 0
                    THEN /\ pg' = [pg EXCEPT ![p] = FREE]
                         /\ cand' = cand \ {p}
                         /\ gpc' = "alloc"
                         /\ UNCHANGED <<checked, stale>>
                    ELSE /\ cand' = cand \ {p}
                         /\ UNCHANGED <<pg, gpc, checked, stale>>
            /\ KeepLap
  /\ UNCHANGED <<R, live, busy, armed, swept, cursor, budget, unknown, strongBroken, overflow, relatched, startClean>>

(* Sweep: settle a finished lap, stop at the budget, or examine the next page. *)
ScanStep ==
  /\ gpc = "scan"
  /\ IF lapLeft = 0
     THEN /\ lapOn' = FALSE /\ lapNote' = FALSE /\ lapDefer' = FALSE
          /\ armed' = (lapNote \/ lapDefer)
          /\ swept' = TRUE
          /\ unknown' = FALSE
          /\ gpc' = "alloc"
          /\ UNCHANGED <<pg, lapLeft, cursor, budget, examined, cand, stale>>
     ELSE IF Budgeted /\ budget = 0
     THEN /\ gpc' = "alloc"
          /\ UNCHANGED <<pg, armed, swept, unknown, lapOn, lapLeft, lapNote, lapDefer, cursor,
                         budget, examined, cand, stale>>
     ELSE LET p == (cursor % R) + 1 IN
          /\ cursor' = p
          /\ examined' = examined + 1
          /\ budget' = IF budget > 0 THEN budget - 1 ELSE 0
          /\ IF busy = p
             THEN /\ stale' = stale \ {p}
                  /\ lapLeft' = lapLeft - 1
                  /\ lapDefer' = (lapDefer \/ Design \in {"full_defer", "budget"})
                  /\ cand' = IF Design = "cand" THEN cand \cup {p} ELSE cand
                  /\ UNCHANGED <<pg, gpc, lapOn, lapNote>>
             ELSE IF pg[p] = 0
                  THEN /\ pg' = [pg EXCEPT ![p] = FREE]
                       /\ cand' = cand \ {p}
                       /\ gpc' = "alloc"
                       \* d52b1889e returns without settling; the next grow starts a new lap.
                       /\ IF Design \in {"full_skip", "full_defer", "full_retry"}
                          THEN lapOn' = FALSE /\ lapLeft' = 0 /\ lapNote' = FALSE
                               /\ lapDefer' = FALSE
                          ELSE lapLeft' = lapLeft - 1 /\ UNCHANGED <<lapOn, lapNote, lapDefer>>
                       /\ UNCHANGED stale
                  ELSE /\ lapLeft' = lapLeft - 1
                       /\ UNCHANGED <<pg, gpc, lapOn, lapNote, lapDefer, cand, stale>>
          /\ UNCHANGED <<armed, swept, unknown>>
  /\ UNCHANGED <<R, live, busy, checked, strongBroken, overflow, relatched, startClean>>

(* file_alloc: a free page in a reserved sector first, else reserve a new one.  The grow ends
   and its per-grow bookkeeping is cleared. *)
Alloc ==
  /\ gpc = "alloc"
  /\ gpc' = "idle" /\ budget' = 0 /\ examined' = 0 /\ checked' = {} /\ stale' = {}
  /\ relatched' = FALSE /\ startClean' = FALSE
  /\ IF \E p \in Reserved : pg[p] = FREE
     THEN \E p \in {q \in Reserved : pg[q] = FREE} :
            /\ pg' = [pg EXCEPT ![p] = 1]
            /\ live' = live + 1
            /\ UNCHANGED <<R, strongBroken, overflow>>
     ELSE IF R < MaxPages
          THEN /\ R' = R + 1
               /\ pg' = [pg EXCEPT ![R + 1] = 1]
               /\ live' = live + 1
               /\ strongBroken' = (strongBroken \/ \E p \in stale : pg[p] = 0 /\ busy # p)
               /\ UNCHANGED overflow
          ELSE /\ overflow' = TRUE
               /\ UNCHANGED <<pg, R, live, strongBroken>>
  /\ UNCHANGED <<busy, armed, swept, lapOn, lapLeft, lapNote, lapDefer, cursor, cand, unknown>>

Next ==
  \/ Insert \/ VacuumDelete \/ FastPath \/ UndoLatch \/ UndoRelease \/ Crash
  \/ StartGrow \/ CandStep \/ ScanStep \/ Alloc

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* Properties *)

(* The file never needs more than MaxPages. *)
NoOverflow == ~overflow

(* The file never exceeds Bound pages; the smallest passing Bound is the worst size. *)
SizeWithinBound == R <= Bound

(* A grow never examines more than CostBound pages. *)
CostWithinBound == examined <= CostBound

(* A grow during which no page was empty examines nothing: arming follows emptied pages, not
   chunk deletes. *)
NoFutileWork == startClean => examined = 0

(* The current specification: a grow reserves a new page only when every page that was empty
   when it started, and that nothing wrote or latched since, has been reclaimed. *)
NoGrowthPastStaleEmpty == ~strongBroken

(* Safety: pages past R are unreserved, and the latched page is allocated. *)
FreeHoldsNothing ==
  /\ \A p \in Pages : p > R => pg[p] = FREE
  /\ busy # 0 => (busy \in Reserved /\ pg[busy] # FREE)

TypeOK ==
  /\ pg \in [Pages -> {FREE} \cup 0..Cap]
  /\ R \in 0..MaxPages /\ live \in 0..L /\ busy \in 0..MaxPages
  /\ cursor \in 0..MaxPages /\ lapLeft \in 0..MaxPages
  /\ gpc \in {"idle", "cand", "scan", "alloc"}
  /\ cand \subseteq Pages /\ stale \subseteq Pages
=============================================================================
