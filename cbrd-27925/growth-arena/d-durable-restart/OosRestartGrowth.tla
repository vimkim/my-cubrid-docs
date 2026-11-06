--------------------------- MODULE OosRestartGrowth ---------------------------
(***************************************************************************)
(* Growth of one OOS file across restarts (CBRD-27925 arena, candidate D).  *)
(*                                                                         *)
(* Derived from ../../growth-model/OosGrowthBound.tla (the cand family).    *)
(* Every design keeps a candidate set `cand` of emptied pages, capacity K. *)
(* A note that does not fit raises `unknown`; a full lap clears it.        *)
(* The designs differ in where the set lives and what it holds after a     *)
(* restart:                                                                *)
(*                                                                         *)
(*   cand_fullboot  memory only; lost at restart; one full lap on the      *)
(*                  growth path (prior recommendation, baseline)           *)
(*   hdr_count      memory set plus a logged per-file empty-page count;    *)
(*                  the lap runs after restart only when the count is > 0  *)
(*   redofn_only    the RVOOS_DELETE redo FUNCTION notes; it runs only     *)
(*                  when page LSA < record LSA, so a page flushed after    *)
(*                  its empty event is missed                              *)
(*   redo_bg_slack  the redo SCAN notes every empty event at or after the  *)
(*                  redo start; a lap off the growth path covers the rest; *)
(*                  meanwhile growth may pass empty pages up to Slack      *)
(*                  pages above the size at restart                        *)
(*   ckpt_redo      memory set; every checkpoint logs a snapshot of it,    *)
(*                  taken AFTER the page flush; recovery loads the last    *)
(*                  snapshot and notes every empty event logged after the  *)
(*                  checkpoint began.  No lap after restart.               *)
(*   ckpt_early     control: as ckpt_redo, but the snapshot is taken when  *)
(*                  the checkpoint begins (before the flush)               *)
(*   hdr_list       the set lives in the OOS header page, logged; a page   *)
(*                  is noted BEFORE the delete that empties it and removed *)
(*                  when an insert refills it.  No recovery code.          *)
(*   hdr_late       control: as hdr_list, but the note is logged after the *)
(*                  delete, before unfix (a crash can fall in between)     *)
(*   hdr_lazy       as hdr_list, but a refill leaves the page listed; the  *)
(*                  grower drops it.  A grow examines each page once.      *)
(*                                                                         *)
(* An emptying delete by the rollback undo is two steps: UndoLatch logs    *)
(* the delete under the page WRITE latch, UndoRelease notes the page and   *)
(* unfixes (the note runs as late as the latch allows).  `pend` marks the  *)
(* page between the two.  hdr_list notes in UndoLatch, before the delete.  *)
(*                                                                         *)
(* Log model.  logEv: the pages recovery would note now.  For redo_*: the  *)
(* empty events logged after the last checkpoint.  For ckpt_*: the last    *)
(* completed checkpoint's snapshot plus the empty events logged after it   *)
(* began (one variable: recovery only reads their union).  logFn (redofn_  *)
(* only): the events whose page was not flushed since (the redo function   *)
(* would still run).  ck/ckNew: a checkpoint in progress and the events    *)
(* logged since it began.  A checkpoint cannot end while a page whose empty event *)
(* was logged before it began is still WRITE-latched: pgbuf_flush_        *)
(* checkpoint flushes every page with oldest_unflush_lsa <= the start LSA  *)
(* synchronously, and a WRITE-latched page is flushed by its holder at     *)
(* unfix (page_buffer.c pgbuf_bcb_safe_flush_internal).                    *)
(* Restart: analysis, redo, undo, then a checkpoint (log_recovery.c:937),  *)
(* modelled as one atomic step.                                            *)
(***************************************************************************)
EXTENDS Integers, FiniteSets

CONSTANTS Design, MaxPages, Cap, L, K, Slack, Crashes, WritesDuringGrow, Bound, CostBound

Designs == {"cand_fullboot", "hdr_count", "redofn_only", "redo_bg_slack",
            "ckpt_redo", "ckpt_early", "hdr_list", "hdr_late", "hdr_lazy"}

ASSUME Design \in Designs
ASSUME MaxPages \in Nat \ {0} /\ Cap \in Nat \ {0} /\ L \in Nat \ {0} /\ K \in Nat \ {0}
ASSUME Slack \in Nat

Pages == 1..MaxPages
FREE == -1

VARIABLES
  pg,            \* page -> FREE or chunk count
  R,             \* reserved pages 1..R (file size)
  live,          \* chunks in the file
  busy,          \* page WRITE-latched by the rollback undo, 0 if none
  pend,          \* the undo emptied `busy` and has not noted it yet
  lapOn,         \* a lap is in progress
  lapLeft,       \* pages the lap still has to visit
  lapDirty,      \* a note was dropped (set full) while the lap ran
  cursor,        \* last page the lap visited
  gpc,           \* grower: idle | cand | scan | alloc
  examined,      \* pages examined by this grow
  relap,         \* this grow already restarted a lap that ended after a dropped note
  checked,       \* candidates this grow passed over (busy; hdr_lazy: also dropped)
  cand,          \* candidate set (memory, or the header page for hdr_*)
  unknown,       \* the set may be incomplete (durable for hdr_*)
  stale,         \* pages empty when this grow started that nothing wrote or latched since
  strongBroken,  \* a grow reserved a page while a stale empty page existed
  strictBroken,  \* same, for a grow that started with unknown = FALSE
  overflow,      \* the file needed more than MaxPages
  relatched,     \* the undo took a latch during this grow
  startClean,    \* no page was empty when this grow started or emptied since
  startKnown,    \* this grow started with unknown = FALSE
  logEv,         \* pages recovery would note now (snapshot plus scanned events)
  logFn,         \* subset of logEv whose page was not flushed since the event
  ck,            \* a checkpoint is in progress
  ckNew,         \* empty events logged since the checkpoint in progress began
  ckCap,         \* ckpt_early: set captured when the checkpoint began
  ckCapU,        \* ckpt_early: unknown flag captured when the checkpoint began
  ckUnknown,     \* unknown flag in the last completed checkpoint
  bootR          \* redo_bg_slack: R at the last restart

lapVars  == <<lapOn, lapLeft, lapDirty, cursor>>
growVars == <<gpc, examined, relap, checked, stale, relatched, startClean, startKnown>>
flagVars == <<strongBroken, strictBroken, overflow>>
logVars  == <<logEv, logFn, ck, ckNew, ckCap, ckCapU, ckUnknown>>
vars == <<pg, R, live, busy, pend, cand, unknown, bootR, lapVars, growVars, flagVars, logVars>>

UsesScan   == Design \in {"redofn_only", "redo_bg_slack", "ckpt_redo", "ckpt_early"}
UsesCkpt   == Design \in {"ckpt_redo", "ckpt_early"}
Durable    == Design \in {"hdr_list", "hdr_late", "hdr_lazy"}
NoteFirst  == Design \in {"hdr_list", "hdr_lazy"}
LazyRefill == Design = "hdr_lazy"

Reserved == 1..R
EmptyPages == {p \in Reserved : pg[p] = 0}

Init ==
  /\ pg = [p \in Pages |-> FREE]
  /\ R = 0 /\ live = 0 /\ busy = 0 /\ pend = FALSE
  /\ lapOn = FALSE /\ lapLeft = 0 /\ lapDirty = FALSE /\ cursor = 0
  /\ gpc = "idle" /\ examined = 0 /\ relap = FALSE /\ checked = {}
  /\ cand = {} /\ unknown = FALSE           \* the file was created this boot
  /\ stale = {} /\ strongBroken = FALSE /\ strictBroken = FALSE /\ overflow = FALSE
  /\ relatched = FALSE /\ startClean = FALSE /\ startKnown = FALSE
  \* ckpt_*: the file's creation logs an empty snapshot, so a crash before the first
  \* checkpoint still knows the file.
  /\ logEv = {} /\ logFn = {} /\ ck = FALSE /\ ckNew = {} /\ ckCap = {} /\ ckCapU = FALSE
  /\ ckUnknown = FALSE
  /\ bootR = 0

-----------------------------------------------------------------------------
(* Set and log helpers *)

Fits(p) == p \in cand \/ Cardinality(cand) < K

(* Note page p in the set.  A note that does not fit raises unknown and dirties a lap
   in progress (the dropped page may be behind the cursor). *)
Note(p) ==
  /\ cand' = IF Fits(p) THEN cand \cup {p} ELSE cand
  /\ unknown' = (unknown \/ ~Fits(p))
  /\ lapDirty' = (lapDirty \/ (~Fits(p) /\ lapOn))

NoNote == UNCHANGED <<cand, unknown, lapDirty>>

(* An emptying delete of page p is logged. *)
LogEmpty(p) ==
  /\ logEv' = IF UsesScan THEN logEv \cup {p} ELSE logEv
  /\ logFn' = IF Design = "redofn_only" THEN logFn \cup {p} ELSE logFn
  /\ ckNew' = IF ck THEN ckNew \cup {p} ELSE ckNew

NoLog == UNCHANGED <<logEv, logFn, ckNew>>

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
       /\ cand' = IF LazyRefill THEN cand ELSE cand \ {p}
  /\ UNCHANGED <<R, busy, pend, unknown, bootR, lapVars, gpc, examined, relap, checked, relatched,
                 startClean, startKnown, flagVars, logVars>>

(* A vacuum chain delete on page p: logged and noted under one latch hold. *)
VacuumDelete ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0 /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ IF pg[p] = 1 THEN (Note(p) /\ LogEmpty(p)) ELSE (NoNote /\ NoLog)
       /\ stale' = stale \ {p}
       /\ startClean' = (startClean /\ pg[p] > 1)
  /\ UNCHANGED <<R, busy, pend, bootR, lapOn, lapLeft, cursor, gpc, examined, relap, checked, relatched,
                 startKnown, flagVars, ck, ckCap, ckCapU, ckUnknown>>

(* The vacuum fast path reclaims an empty page it emptied. *)
FastPath ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ \E p \in EmptyPages :
       /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = FREE]
       /\ cand' = cand \ {p}
       /\ stale' = stale \ {p}
  /\ UNCHANGED <<R, live, busy, pend, unknown, bootR, lapVars, gpc, examined, relap, checked, relatched,
                 startClean, startKnown, flagVars, logVars>>

(* INSERT rollback undo (oos_rv_redo_delete): WRITE-latches p and deletes one chunk.
   At most one new latch per grow (model restriction). *)
UndoLatch ==
  /\ busy = 0
  /\ (gpc = "idle" \/ ~relatched)
  /\ relatched' = (gpc # "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0
       /\ busy' = p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ IF pg[p] = 1
          THEN /\ LogEmpty(p)
               /\ IF NoteFirst THEN (Note(p) /\ pend' = FALSE)
                               ELSE (NoNote /\ pend' = TRUE)
          ELSE NoLog /\ NoNote /\ pend' = FALSE
       /\ stale' = stale \ {p}
       /\ startClean' = (startClean /\ pg[p] > 1)
  /\ UNCHANGED <<R, bootR, lapOn, lapLeft, cursor, gpc, examined, relap, checked, startKnown, flagVars,
                 ck, ckCap, ckCapU, ckUnknown>>

UndoRelease ==
  /\ busy # 0
  /\ IF pend THEN Note(busy) ELSE NoNote
  /\ busy' = 0 /\ pend' = FALSE
  /\ UNCHANGED <<pg, R, live, bootR, lapOn, lapLeft, cursor, growVars, flagVars, logVars>>

(* redofn_only: a flush writes a page whose empty event is in the log, so the redo function
   will skip that record.  A WRITE-latched page is not flushed before unfix. *)
FlushPage ==
  /\ Crashes /\ Design = "redofn_only"
  /\ \E p \in logFn \ {busy} : logFn' = logFn \ {p}
  /\ UNCHANGED <<pg, R, live, busy, pend, cand, unknown, bootR, lapVars, growVars, flagVars,
                 logEv, ck, ckNew, ckCap, ckCapU, ckUnknown>>

(* redofn_only, redo_bg_slack: one-step checkpoint (it waits for a pending latched page). *)
Checkpoint ==
  /\ Crashes /\ Design \in {"redofn_only", "redo_bg_slack"}
  /\ ~pend
  /\ logEv' = {} /\ logFn' = {}
  /\ UNCHANGED <<pg, R, live, busy, pend, cand, unknown, bootR, lapVars, growVars, flagVars,
                 ck, ckNew, ckCap, ckCapU, ckUnknown>>

(* ckpt_*: the checkpoint begins (LOG_START_CHKPT); ckpt_early captures the set here. *)
CkBegin ==
  /\ Crashes /\ UsesCkpt /\ ~ck
  /\ ck' = TRUE /\ ckNew' = {}
  /\ ckCap' = IF Design = "ckpt_early" THEN cand ELSE {}
  /\ ckCapU' = IF Design = "ckpt_early" THEN unknown ELSE FALSE
  /\ UNCHANGED <<pg, R, live, busy, pend, cand, unknown, bootR, lapVars, growVars, flagVars,
                 logEv, logFn, ckUnknown>>

(* ckpt_*: the flush is done and the checkpoint completes.  ckpt_redo captures the set
   here, after pgbuf_flush_checkpoint returned.  The recovery scan then starts at the
   checkpoint's start LSA. *)
CkEnd ==
  /\ ck
  /\ (~pend \/ busy \in ckNew)
  /\ ck' = FALSE /\ ckNew' = {} /\ ckCap' = {} /\ ckCapU' = FALSE
  /\ logEv' = (IF Design = "ckpt_early" THEN ckCap ELSE cand) \cup ckNew
  /\ ckUnknown' = IF Design = "ckpt_early" THEN ckCapU ELSE unknown
  /\ UNCHANGED <<pg, R, live, busy, pend, cand, unknown, bootR, lapVars, growVars, flagVars, logFn>>

(* Restart: pages and durable state persist, memory is lost, recovery rebuilds the set,
   then the end-of-recovery checkpoint runs. *)
Crash ==
  /\ Crashes
  /\ LET raw == CASE Design \in {"cand_fullboot", "hdr_count"} -> {}
                  [] Design = "redofn_only"   -> logFn
                  [] Design = "redo_bg_slack" -> logEv
                  [] UsesCkpt                 -> logEv
                  [] Durable                  -> cand
         tooBig == Cardinality(raw) > K
         newCand == IF tooBig THEN {} ELSE raw
         newUnknown == tooBig \/
                       (CASE Design = "cand_fullboot" -> TRUE
                          [] Design = "hdr_count"     -> EmptyPages # {}
                          [] Design = "redofn_only"   -> FALSE
                          [] Design = "redo_bg_slack" -> TRUE
                          [] UsesCkpt                 -> ckUnknown
                          [] Durable                  -> unknown)
     IN /\ cand' = newCand /\ unknown' = newUnknown
        \* the end-of-recovery checkpoint snapshots the rebuilt set
        /\ logEv' = IF UsesCkpt THEN newCand ELSE {}
        /\ ckUnknown' = IF UsesCkpt THEN newUnknown ELSE FALSE
  /\ logFn' = {} /\ ck' = FALSE /\ ckNew' = {} /\ ckCap' = {} /\ ckCapU' = FALSE
  /\ busy' = 0 /\ pend' = FALSE /\ gpc' = "idle"
  /\ lapOn' = FALSE /\ lapLeft' = 0 /\ lapDirty' = FALSE /\ cursor' = 0
  /\ examined' = 0 /\ relap' = FALSE /\ checked' = {}
  /\ stale' = {} /\ relatched' = FALSE /\ startClean' = FALSE /\ startKnown' = FALSE
  /\ bootR' = IF Design = "redo_bg_slack" THEN R ELSE 0
  /\ UNCHANGED <<pg, R, live, flagVars>>

-----------------------------------------------------------------------------
(* The lap, shared by the grower and the background step.  One page per step. *)

(* The lap visits the next page.  OnPath: the grower runs it and stops at a reclaimed page.
   Sets pg, cand, unknown, lapDirty, cursor, lapLeft, stale, gpc. *)
LapVisit(OnPath) ==
  LET p == (cursor % R) + 1 IN
  /\ cursor' = p
  /\ lapLeft' = lapLeft - 1
  /\ IF busy = p
     THEN /\ Note(p)
          /\ stale' = stale \ {p}
          /\ UNCHANGED <<pg, gpc>>
     ELSE /\ NoNote
          /\ IF pg[p] = 0
             THEN /\ pg' = [pg EXCEPT ![p] = FREE]
                  /\ gpc' = IF OnPath THEN "alloc" ELSE gpc
             ELSE UNCHANGED <<pg, gpc>>
          /\ UNCHANGED stale

(* The lap ends: the set is complete unless a note was dropped meanwhile. *)
LapEnd ==
  /\ lapOn' = FALSE /\ unknown' = lapDirty /\ lapDirty' = FALSE

(* A lap that ended after a dropped note runs once more in the same grow: the dropped
   page may be behind the cursor.  A second dropped note lets the grow proceed with
   unknown still set (that page was emptied during this grow). *)
ScanStep ==
  /\ gpc = "scan"
  /\ IF lapLeft = 0 /\ lapDirty /\ ~relap
     THEN /\ relap' = TRUE /\ lapLeft' = R /\ lapDirty' = FALSE
          /\ UNCHANGED <<pg, cand, unknown, lapOn, cursor, gpc, examined, stale>>
     ELSE IF lapLeft = 0
     THEN /\ LapEnd /\ gpc' = "alloc"
          /\ UNCHANGED <<pg, cand, lapLeft, cursor, examined, stale, relap>>
     ELSE /\ examined' = examined + 1
          /\ LapVisit(TRUE)
          /\ UNCHANGED <<lapOn, relap>>
  /\ UNCHANGED <<R, live, busy, pend, bootR, checked, relatched, startClean, startKnown,
                 flagVars, logVars>>

(* redo_bg_slack: a background step walks the lap while no grow runs (it holds the
   per-file single-flight).  Fairness is NOT assumed: it may never run. *)
BgStep ==
  /\ Design = "redo_bg_slack"
  /\ gpc = "idle" /\ unknown /\ R > 0
  /\ IF ~lapOn
     THEN /\ lapOn' = TRUE /\ lapLeft' = R /\ lapDirty' = FALSE
          /\ UNCHANGED <<pg, cursor, cand, unknown, stale>>
     ELSE IF lapLeft = 0
     THEN /\ LapEnd
          /\ UNCHANGED <<pg, lapLeft, cursor, cand, stale>>
     ELSE /\ LapVisit(FALSE)
          /\ UNCHANGED lapOn
  /\ UNCHANGED <<R, live, busy, pend, bootR, gpc, examined, relap, checked, relatched, startClean,
                 startKnown, flagVars, logVars>>

-----------------------------------------------------------------------------
(* The grower *)

StartGrow ==
  /\ gpc = "idle" /\ live < L
  /\ gpc' = "cand"
  /\ stale' = EmptyPages \ {busy}
  /\ relatched' = FALSE
  /\ startClean' = (~WritesDuringGrow /\ EmptyPages = {})   \* read only by NoFutileWork (quiet)
  /\ startKnown' = ~unknown
  /\ UNCHANGED <<pg, R, live, busy, pend, cand, unknown, bootR, lapVars, examined, relap, checked,
                 flagVars, logVars>>

(* The grow scans only when the set may be incomplete; redo_bg_slack skips the scan while
   the file is under bootR + Slack. *)
MustScan ==
  /\ unknown
  /\ (Design # "redo_bg_slack" \/ R >= bootR + Slack)

CandStep ==
  /\ gpc = "cand"
  /\ IF cand \ checked = {}
     THEN /\ IF MustScan
             THEN /\ gpc' = "scan"
                  /\ IF lapOn THEN UNCHANGED <<lapOn, lapLeft, lapDirty>>
                              ELSE lapOn' = TRUE /\ lapLeft' = R /\ lapDirty' = FALSE
             ELSE /\ gpc' = "alloc"
                  /\ UNCHANGED <<lapOn, lapLeft, lapDirty>>
          /\ UNCHANGED <<pg, cand, checked, examined, stale>>
     ELSE \E p \in cand \ checked :
            /\ examined' = examined + 1
            /\ IF busy = p
               THEN /\ checked' = checked \cup {p}
                    /\ stale' = stale \ {p}
                    /\ UNCHANGED <<pg, cand, gpc>>
               ELSE IF p \in Reserved /\ pg[p] = 0
                    THEN /\ pg' = [pg EXCEPT ![p] = FREE]
                         /\ cand' = cand \ {p}
                         /\ gpc' = "alloc"
                         /\ UNCHANGED <<checked, stale>>
                    ELSE /\ cand' = cand \ {p}
                         \* hdr_lazy: a refilled page can be noted again and refilled before
                         \* the next look, so a grow examines each page once
                         /\ checked' = IF LazyRefill THEN checked \cup {p} ELSE checked
                         /\ UNCHANGED <<pg, gpc, stale>>
            /\ UNCHANGED <<lapOn, lapLeft, lapDirty>>
  /\ UNCHANGED <<R, live, busy, pend, unknown, bootR, cursor, relap, relatched, startClean, startKnown,
                 flagVars, logVars>>

Alloc ==
  /\ gpc = "alloc"
  /\ gpc' = "idle" /\ examined' = 0 /\ relap' = FALSE /\ checked' = {} /\ stale' = {}
  /\ relatched' = FALSE /\ startClean' = FALSE /\ startKnown' = FALSE
  /\ IF \E p \in Reserved : pg[p] = FREE
     THEN \E p \in {q \in Reserved : pg[q] = FREE} :
            /\ pg' = [pg EXCEPT ![p] = 1]
            /\ live' = live + 1
            /\ UNCHANGED <<R, flagVars>>
     ELSE IF R < MaxPages
          THEN LET passed == \E p \in stale : pg[p] = 0 /\ busy # p IN
               /\ R' = R + 1
               /\ pg' = [pg EXCEPT ![R + 1] = 1]
               /\ live' = live + 1
               /\ strongBroken' = (strongBroken \/ passed)
               /\ strictBroken' = (strictBroken \/ (passed /\ startKnown))
               /\ UNCHANGED overflow
          ELSE /\ overflow' = TRUE
               /\ UNCHANGED <<pg, R, live, strongBroken, strictBroken>>
  /\ UNCHANGED <<busy, pend, cand, unknown, bootR, lapVars, logVars>>

Next ==
  \/ Insert \/ VacuumDelete \/ FastPath \/ UndoLatch \/ UndoRelease
  \/ FlushPage \/ Checkpoint \/ CkBegin \/ CkEnd \/ Crash \/ BgStep
  \/ StartGrow \/ CandStep \/ ScanStep \/ Alloc

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* Properties *)

NoOverflow == ~overflow
SizeWithinBound == R <= Bound
CostWithinBound == examined <= CostBound

(* The strict rule at every grow. *)
NoGrowthPastStaleEmpty == ~strongBroken

(* The strict rule at grows that start while the set is known complete. *)
StrictOutsideWindow == ~strictBroken

(* The set holds every empty page whenever it claims to be complete, except the page the
   undo emptied and has not noted yet (it notes before unfix). *)
SetCompleteWhenKnown ==
  ~unknown => (EmptyPages \ (IF pend THEN {busy} ELSE {})) \subseteq cand

NoFutileWork == startClean => examined = 0

FreeHoldsNothing ==
  /\ \A p \in Pages : p > R => pg[p] = FREE
  /\ busy # 0 => (busy \in Reserved /\ pg[busy] # FREE)
  /\ pend => busy # 0

TypeOK ==
  /\ pg \in [Pages -> {FREE} \cup 0..Cap]
  /\ R \in 0..MaxPages /\ live \in 0..L /\ busy \in 0..MaxPages
  /\ cursor \in 0..MaxPages /\ lapLeft \in 0..MaxPages
  /\ gpc \in {"idle", "cand", "scan", "alloc"}
  /\ cand \subseteq Pages /\ Cardinality(cand) <= K /\ stale \subseteq Pages
  /\ logFn \subseteq logEv \/ Design # "redofn_only"
  /\ logEv \subseteq Pages
=============================================================================
