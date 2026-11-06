---------------------------- MODULE OosReuseFirst ----------------------------
(***************************************************************************)
(* CBRD-27925 growth arena, candidate c-reuse-first.                       *)
(*                                                                         *)
(* One OOS file under insert/delete/rollback churn.  A page is FREE (not   *)
(* allocated, inside a reserved sector) or holds 0..Cap chunks.  One page  *)
(* is one sector, so R (reserved pages) is the file size on disk; it never *)
(* shrinks (file_destroy only).                                            *)
(*                                                                         *)
(* Actors: bestspace-hit inserts into pages with room, vacuum chunk        *)
(* deletes, the vacuum fast path (file_dealloc of an empty page), one      *)
(* INSERT-rollback undo that WRITE-latches a page while it deletes a chunk *)
(* (oos_rv_redo_delete), restarts, and one grower.  The grower is the      *)
(* inserter whose bestspace lookup missed.  Every insert-side discovery    *)
(* runs under the OOS header WRITE latch (oos_find_best_page), which also *)
(* serializes the fast path's phase 2, so one grower suffices.             *)
(*                                                                         *)
(* Designs (what the grower does with a known-empty page):                 *)
(*   cand          prior cand_fullboot: exact emptied set E; a member is   *)
(*                 deallocated (sysop) and file_alloc reuses the free page *)
(*                 (second sysop).                                         *)
(*   hybrid_cand   the brief's hybrid: vacuum-emptied pages are reused     *)
(*                 through the lossy hint set H; a page the inserter       *)
(*                 cannot see (rollback-emptied, evicted, too full of dead *)
(*                 slots) goes to a cand set C and is deallocated there.   *)
(*   reuse         exact emptied set E; a member is WRITE-fixed            *)
(*                 conditionally, re-validated (OOS, owned, empty) and the *)
(*                 chunk is inserted into it.  No dealloc, no file_alloc.  *)
(*   reuse_noreinit reuse, but an empty page whose dead slots leave too    *)
(*                 little room for this chunk is skipped (kept in E).      *)
(*   reuse_nocheck reuse without the re-validation: trusts E.              *)
(*   hybrid        no new set for vacuum-emptied pages: they rely on the   *)
(*                 bestspace hint set H, which may lose an entry at any    *)
(*                 time (global capacity, restart).  A rollback-emptied    *)
(*                 page (hint removed at 3655) and an evicted empty page   *)
(*                 go to a cand set C.                                     *)
(*   hybrid_leaky  hybrid where only rollback-emptied pages go to C.       *)
(* MayNotFit: an emptied ANCHORED page keeps its dead slots                *)
(* (REC_DELETED_WILL_REUSE), so a max-size chunk may not fit it.  reuse    *)
(* then re-initializes the page in place in a short redo-only sysop.       *)
(* After a restart every design runs one lap over the file (boot rule).    *)
(* Recheck: how many times a grow re-reads its set after a finished lap    *)
(* before it allocates.                                                    *)
(* FastPathOn: the vacuum fast path deallocates empty pages.  The reuse    *)
(* proposal turns it off; with it on, reuse must survive its races.       *)
(* LazyRemove: a refill or a fast-path dealloc leaves the page in E/C; the *)
(* grower drops it when it re-validates.  FALSE: removed at once.          *)
(* RelatchOnce: the undo takes a new latch at most once per grow (the      *)
(* prior model's restriction).  FALSE: any number of times.                *)
(***************************************************************************)
EXTENDS Integers, FiniteSets, TLC

CONSTANTS Design, MaxPages, Cap, L, Recheck, Crashes, WritesDuringGrow, MayNotFit,
          FastPathOn, LazyRemove, RelatchOnce, Bound, CostBound, SysopBound

ASSUME Design \in {"cand", "reuse", "reuse_noreinit", "reuse_nocheck", "hybrid", "hybrid_leaky",
                   "hybrid_cand"}

Pages == 1..MaxPages
FREE == -1

VARIABLES
  pg,           \* page -> FREE or chunk count
  R,            \* reserved pages 1..R
  live,         \* chunks in the file
  busy,         \* page WRITE-latched by the rollback undo, 0 if none
  relatched,    \* the undo took a latch during this grow
  gpc,          \* grower: idle | pick | scan | alloc
  E,            \* exact emptied set (cand, reuse*) or cand set C (hybrid*)
  H,            \* hybrid*: bestspace hints of empty pages (lossy)
  unknown,      \* the sets may miss pages (after a restart, until a lap ends)
  lapOn, lapLeft, cursor,
  rechecks,     \* re-reads of the set after a lap, this grow
  examined,     \* pages this grow fixed (cost)
  sysops,       \* file_dealloc + file_alloc sysops this grow
  checked,      \* set members this grow already examined and passed over (busy or dropped)
  stale,        \* pages empty at grow start that nothing wrote or latched since
  startClean,   \* no page was empty at grow start or emptied since
  strongBroken, \* a grow reserved a new sector while a stale empty page existed
  overflow,     \* the file needed more than MaxPages
  badClaim      \* a grower inserted into a page that is not an allocated OOS page

vars == <<pg, R, live, busy, relatched, gpc, E, H, unknown, lapOn, lapLeft, cursor, rechecks,
          examined, sysops, checked, stale, startClean, strongBroken, overflow, badClaim>>

Hybrid == Design \in {"hybrid", "hybrid_leaky", "hybrid_cand"}
Reserved == 1..R
EmptyPages == {p \in Reserved : pg[p] = 0}
Avail == IF Hybrid THEN H \cup E ELSE E

Init ==
  /\ pg = [p \in Pages |-> FREE]
  /\ R = 0 /\ live = 0 /\ busy = 0 /\ relatched = FALSE
  /\ gpc = "idle" /\ E = {} /\ H = {} /\ unknown = FALSE
  /\ lapOn = FALSE /\ lapLeft = 0 /\ cursor = 0 /\ rechecks = 0
  /\ examined = 0 /\ sysops = 0 /\ checked = {} /\ stale = {} /\ startClean = FALSE
  /\ strongBroken = FALSE /\ overflow = FALSE /\ badClaim = FALSE
  /\ TLCSet(1, 0) /\ TLCSet(2, 0) /\ TLCSet(3, 0) /\ TLCSet(4, 0)
  /\ TLCSet(5, 0) /\ TLCSet(6, 0) /\ TLCSet(7, 0) /\ TLCSet(8, 0)

(* A chunk delete left k chunks on p.  undo: the rollback path (3655 removes the hint). *)
NoteDelete(p, k, undo) ==
  IF Hybrid
  THEN IF undo
       THEN /\ H' = H \ {p}
            /\ E' = IF k = 0 THEN E \cup {p} ELSE E
       ELSE /\ H' = IF k = 0 THEN H \cup {p} ELSE H     \* oos_stats_update, 3370
            /\ UNCHANGED E
  ELSE /\ E' = IF k = 0 THEN E \cup {p} ELSE E
       /\ UNCHANGED H

-----------------------------------------------------------------------------
(* Other actors *)

(* A bestspace hit.  It may land on an empty page; it drops the page from the sets
   (page_was_empty at 2158). *)
Insert ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ live + (IF gpc # "idle" THEN 1 ELSE 0) < L
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] < Cap /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = @ + 1]
       /\ live' = live + 1
       /\ stale' = stale \ {p}
       /\ E' = IF LazyRemove THEN E ELSE E \ {p}
       /\ H' = H \ {p}
  /\ UNCHANGED <<R, busy, relatched, gpc, unknown, lapOn, lapLeft, cursor, rechecks, examined,
                 sysops, checked, startClean, strongBroken, overflow, badClaim>>

VacuumDelete ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0 /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ NoteDelete(p, pg[p] - 1, FALSE)
       /\ stale' = stale \ {p}
       /\ startClean' = (startClean /\ pg[p] > 1)
  /\ UNCHANGED <<R, busy, relatched, gpc, unknown, lapOn, lapLeft, cursor, rechecks, examined,
                 sysops, checked, strongBroken, overflow, badClaim>>

(* The vacuum fast path deallocates an empty unlatched page.  It evicts the bestspace hint
   (1668) under bestspace_mutex, where it can also drop the page from E unless LazyRemove. *)
FastPath ==
  /\ FastPathOn
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ \E p \in EmptyPages :
       /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = FREE]
       /\ H' = H \ {p}
       /\ E' = IF LazyRemove THEN E ELSE E \ {p}
       /\ stale' = stale \ {p}
  /\ UNCHANGED <<R, live, busy, relatched, gpc, unknown, lapOn, lapLeft, cursor, rechecks,
                 examined, sysops, checked, startClean, strongBroken, overflow, badClaim>>

(* INSERT rollback: deletes one chunk under the page WRITE latch.  At most one new latch per
   grow (see the prior model: an unbounded number defeats every zero-wait check). *)
UndoLatch ==
  /\ busy = 0
  /\ (gpc = "idle" \/ ~relatched \/ ~RelatchOnce)
  /\ relatched' = (gpc # "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0
       /\ busy' = p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ NoteDelete(p, pg[p] - 1, TRUE)
       /\ stale' = stale \ {p}
       /\ startClean' = (startClean /\ pg[p] > 1)
  /\ UNCHANGED <<R, gpc, unknown, lapOn, lapLeft, cursor, rechecks, examined, sysops, checked,
                 strongBroken, overflow, badClaim>>

UndoRelease ==
  /\ busy # 0
  /\ busy' = 0
  /\ UNCHANGED <<pg, R, live, relatched, gpc, E, H, unknown, lapOn, lapLeft, cursor, rechecks,
                 examined, sysops, checked, stale, startClean, strongBroken, overflow, badClaim>>

(* A bestspace hint is lost: capacity (373), restart of the hash, phase-A eviction. *)
HintEvict ==
  /\ Hybrid
  /\ \E p \in H :
       /\ H' = H \ {p}
       /\ E' = IF Design \in {"hybrid", "hybrid_cand"} /\ pg[p] = 0 THEN E \cup {p} ELSE E
  /\ UNCHANGED <<pg, R, live, busy, relatched, gpc, unknown, lapOn, lapLeft, cursor, rechecks,
                 examined, sysops, checked, stale, startClean, strongBroken, overflow, badClaim>>

Crash ==
  /\ Crashes
  /\ busy' = 0 /\ relatched' = FALSE /\ gpc' = "idle"
  /\ E' = {} /\ H' = {} /\ unknown' = TRUE
  /\ lapOn' = FALSE /\ lapLeft' = 0 /\ cursor' = 0 /\ rechecks' = 0
  /\ examined' = 0 /\ sysops' = 0 /\ checked' = {} /\ stale' = {} /\ startClean' = FALSE
  /\ UNCHANGED <<pg, R, live, strongBroken, overflow, badClaim>>

-----------------------------------------------------------------------------
(* The grower *)

StartGrow ==
  /\ gpc = "idle" /\ live < L
  /\ gpc' = "pick"
  /\ stale' = EmptyPages \ {busy}
  /\ startClean' = (EmptyPages = {})
  /\ relatched' = FALSE /\ examined' = 0 /\ sysops' = 0 /\ checked' = {} /\ rechecks' = 0
  /\ UNCHANGED <<pg, R, live, busy, E, H, unknown, lapOn, lapLeft, cursor, strongBroken,
                 overflow, badClaim>>

(* cand deallocates p and goes on to file_alloc; hybrid_cand does so for a page the inserter
   cannot see (not in H). *)
Deallocs(p) == Design = "cand" \/ (Design = "hybrid_cand" /\ p \notin H)

(* The grower takes the empty, unlatched page p.  With dealloc it frees p and goes on to
   file_alloc; otherwise it inserts the chunk into p and is done. *)
TakeAs(p, reinit, dealloc) ==
  /\ E' = E \ {p} /\ H' = H \ {p}
  /\ IF dealloc
     THEN /\ pg' = [pg EXCEPT ![p] = FREE]
          /\ sysops' = sysops + 1
          /\ gpc' = "alloc"
          /\ UNCHANGED live
     ELSE /\ pg' = [pg EXCEPT ![p] = 1]
          /\ live' = live + 1
          /\ gpc' = "idle"
          /\ sysops' = sysops + (IF reinit THEN 1 ELSE 0)

Take(p, reinit) == TakeAs(p, reinit, Deallocs(p))

(* The chunk may not fit an emptied page (dead slots).  reuse and hybrid re-initialize it in
   place (one sysop); reuse_noreinit passes over it; in hybrid_cand the bestspace lookup drops
   the hint of a visible page that is too small and the same call deallocates it (one
   oos_find_best_page call reads the hints once, so it never comes back to that hint).  A
   deallocated page always fits after file_alloc. *)
Reinits == Design \in {"reuse", "reuse_nocheck", "hybrid", "hybrid_leaky"}

PickClaim(p) ==
  \/ Take(p, FALSE) /\ UNCHANGED checked
  \/ MayNotFit /\ Reinits /\ Take(p, TRUE) /\ UNCHANGED checked
  \/ /\ MayNotFit /\ Design = "reuse_noreinit"
     /\ checked' = checked \cup {p}
     /\ UNCHANGED <<pg, live, E, H, gpc, sysops>>
  \/ MayNotFit /\ Design = "hybrid_cand" /\ p \in H /\ TakeAs(p, FALSE, TRUE) /\ UNCHANGED checked

LapClaim(p) ==
  \/ Take(p, FALSE)
  \/ MayNotFit /\ Reinits /\ Take(p, TRUE)
  \/ /\ MayNotFit /\ Design = "reuse_noreinit"
     /\ E' = E \cup {p}
     /\ UNCHANGED <<pg, live, H, gpc, sysops>>

LapEnd ==
  /\ lapOn' = FALSE /\ unknown' = FALSE
  /\ IF rechecks < Recheck
     THEN gpc' = "pick" /\ rechecks' = rechecks + 1
     ELSE gpc' = "alloc" /\ UNCHANGED rechecks

PickStep ==
  /\ gpc = "pick"
  /\ IF Avail \ checked = {}
     THEN /\ IF unknown
             THEN /\ gpc' = "scan"
                  /\ IF lapOn THEN UNCHANGED <<lapOn, lapLeft, cursor>>
                     ELSE lapOn' = TRUE /\ lapLeft' = R /\ cursor' = 0
             ELSE /\ gpc' = "alloc"
                  /\ UNCHANGED <<lapOn, lapLeft, cursor>>
          /\ UNCHANGED <<pg, live, E, H, examined, sysops, checked, stale, badClaim>>
     ELSE \E p \in Avail \ checked :
            /\ examined' = examined + 1
            /\ UNCHANGED <<lapOn, lapLeft, cursor>>
            /\ IF busy = p
               THEN \* conditional WRITE fix fails; keep p for a later grow
                    /\ checked' = checked \cup {p}
                    /\ stale' = stale \ {p}
                    /\ UNCHANGED <<pg, live, E, H, gpc, sysops, badClaim>>
               ELSE IF pg[p] = 0
               THEN PickClaim(p) /\ UNCHANGED <<stale, badClaim>>
               ELSE IF Design = "reuse_nocheck" /\ pg[p] = FREE
               THEN \* no re-validation: the chunk goes into a deallocated page
                    /\ badClaim' = TRUE
                    /\ E' = E \ {p} /\ H' = H \ {p}
                    /\ gpc' = "idle"
                    /\ UNCHANGED <<pg, live, sysops, checked, stale>>
               ELSE \* refilled or deallocated: drop it.  Under LazyRemove it also joins checked:
                    \* there a writer that refills and re-empties p would livelock the grow.
                    /\ E' = E \ {p} /\ H' = H \ {p}
                    /\ checked' = IF LazyRemove THEN checked \cup {p} ELSE checked
                    /\ UNCHANGED <<pg, live, gpc, sysops, stale, badClaim>>
  /\ UNCHANGED <<R, busy, relatched, unknown, rechecks, startClean, strongBroken, overflow>>

(* The boot-rule lap: READ-fix pages 1..R in order, across grows, until one is claimed. *)
ScanStep ==
  /\ gpc = "scan"
  /\ IF lapLeft = 0
     THEN /\ LapEnd
          /\ UNCHANGED <<pg, live, E, H, lapLeft, cursor, examined, sysops, stale>>
     ELSE LET p == cursor + 1 IN
          /\ cursor' = p /\ lapLeft' = lapLeft - 1
          /\ examined' = examined + 1
          /\ UNCHANGED <<unknown, rechecks>>
          /\ IF busy = p
             THEN /\ E' = E \cup {p}
                  /\ stale' = stale \ {p}
                  /\ UNCHANGED <<pg, live, H, gpc, lapOn, sysops>>
             ELSE IF pg[p] = 0
                  THEN LapClaim(p) /\ UNCHANGED <<lapOn, stale>>
                  ELSE UNCHANGED <<pg, live, E, H, gpc, lapOn, sysops, stale>>
  /\ UNCHANGED <<R, busy, relatched, checked, startClean, strongBroken, overflow, badClaim>>

(* file_alloc: a free page of a reserved sector first, else a new sector. *)
Alloc ==
  /\ gpc = "alloc"
  /\ gpc' = "idle"
  /\ sysops' = sysops + 1
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
  /\ UNCHANGED <<busy, relatched, E, H, unknown, lapOn, lapLeft, cursor, rechecks, examined,
                 checked, stale, startClean, badClaim>>

Next ==
  \/ Insert \/ VacuumDelete \/ FastPath \/ UndoLatch \/ UndoRelease \/ HintEvict \/ Crash
  \/ StartGrow \/ PickStep \/ ScanStep \/ Alloc

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* Properties *)

TypeOK ==
  /\ pg \in [Pages -> {FREE} \cup 0..Cap]
  /\ R \in 0..MaxPages /\ live \in 0..L /\ busy \in 0..MaxPages
  /\ gpc \in {"idle", "pick", "scan", "alloc"}
  /\ E \subseteq Pages /\ H \subseteq Pages /\ stale \subseteq Pages

(* Safety: nothing past R is in use, the undo latch sits on an allocated page, and no grower
   ever put a chunk into a deallocated page. *)
Safe ==
  /\ \A p \in Pages : p > R => pg[p] = FREE
  /\ busy # 0 => (busy \in Reserved /\ pg[busy] # FREE)
  /\ ~badClaim

(* Outside a boot lap, the sets the grower reads cover every empty page. *)
SetComplete == ~unknown => EmptyPages \subseteq Avail

(* The current rule, with "reused" counting as satisfying it. *)
StrictRule == ~strongBroken

NoOverflow == ~overflow
SizeWithinBound == R <= Bound
CostWithinBound == examined <= CostBound
SysopWithinBound == sysops <= SysopBound
NoFutileWork == startClean => examined = 0

-----------------------------------------------------------------------------
(* Measurement in one full run (CONSTRAINT Track, -workers 1): print each new maximum and the
   first violation of each property.  run.py parses these lines. *)
Rec(i, name, v) == IF v > TLCGet(i) THEN TLCSet(i, v) /\ PrintT(<<"REC", name, v>>) ELSE TRUE
Flag(i, name, ok) == IF ~ok /\ TLCGet(i) = 0 THEN TLCSet(i, 1) /\ PrintT(<<"VIOL", name>>) ELSE TRUE

Track ==
  /\ Rec(1, "maxR", R)
  /\ Rec(2, "maxCost", examined)
  /\ Rec(3, "maxSysops", sysops)
  /\ Flag(4, "Safe", TypeOK /\ Safe)
  /\ Flag(5, "SetComplete", SetComplete)
  /\ Flag(6, "StrictRule", StrictRule)
  /\ Flag(7, "NoFutileWork", NoFutileWork)
  /\ Flag(8, "NoOverflow", NoOverflow)
=============================================================================
