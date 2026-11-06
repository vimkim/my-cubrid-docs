---------------------------- MODULE OosSlackBound ----------------------------
(***************************************************************************)
(* Slack-bound growth for one OOS file (CBRD-27925 arena, b-slack-bound).  *)
(*                                                                         *)
(* Same actors, atomic steps and undo restriction as                      *)
(* growth-model/OosGrowthBound.tla.  A grow reclaims only when the tracker *)
(* reports more than K emptied pages (K = 0 with Design "set" is           *)
(* cand_fullboot).  Two trackers:                                          *)
(*                                                                         *)
(*   set    the VPIDs of emptied pages.  A grow checks the members.        *)
(*   count  an integer, no VPIDs.  +1 when a delete empties a page, -1     *)
(*          (saturating) when an empty page is refilled, fast-pathed or    *)
(*          reclaimed.  A grow runs the cursor lap until one reclaim or    *)
(*          the lap end.  After a restart the counter starts at 0, so a    *)
(*          -1 on a page emptied before the restart makes it drift low.    *)
(*                                                                         *)
(* BootLap: after a restart the tracker is unknown and grows run one full  *)
(* lap (cand_fullboot rule).  When FALSE, nothing rediscovers the empty    *)
(* pages of the previous boot.                                             *)
(* FreeGate: skip reclaim while a FREE page exists (no new sector).        *)
(*                                                                         *)
(* One page is one sector, so R is the file size on disk; R never shrinks. *)
(***************************************************************************)
EXTENDS Integers, FiniteSets

CONSTANTS Design, K, FreeGate, BootLap, MaxPages, Cap, L, Crashes, WritesDuringGrow

ASSUME Design \in {"set", "count"}
ASSUME K \in Nat /\ MaxPages \in Nat \ {0} /\ Cap \in Nat \ {0} /\ L \in Nat \ {0}

Pages == 1..MaxPages
FREE == -1

VARIABLES
  pg,          \* page -> FREE or chunk count
  R,           \* reserved pages 1..R (file size)
  live,        \* chunks in the file
  busy,        \* page WRITE-latched by the rollback undo, 0 if none
  lapOn, lapLeft, cursor,
  gpc,         \* grower: idle | cand | scan | alloc
  examined,    \* pages examined by this grow
  checked,     \* busy set members this grow passed over
  cand,        \* set tracker
  n,           \* count tracker
  unknown,     \* the tracker may be incomplete (restart with BootLap)
  stale,       \* pages empty at grow start that nothing wrote or latched since
  relatched,   \* the undo took a latch during this grow
  startClean,  \* no page was empty when this grow started or emptied since
  strongBroken,\* a grow expanded while a stale empty page existed (current spec)
  weakBroken,  \* a grow expanded while more than K stale empty pages existed (slack spec)
  overflow,    \* the file needed more than MaxPages
  futile,      \* a grow examined a page while startClean held
  maxDrift     \* most empty pages a known tracker missed when a grow decided

vars == <<pg, R, live, busy, lapOn, lapLeft, cursor, gpc, examined, checked, cand, n, unknown,
          stale, relatched, startClean, strongBroken, weakBroken, overflow, futile, maxDrift>>

IsSet == Design = "set"
IsCount == Design = "count"
Reserved == 1..R
EmptyPages == {p \in Reserved : pg[p] = 0}
Reclaimable(S) == {p \in S : pg[p] = 0 /\ busy # p}
HasFree == \E p \in Reserved : pg[p] = FREE
Dec(x) == IF x > 0 THEN x - 1 ELSE 0
Tracked == IF IsSet THEN Cardinality(cand) ELSE n
Missed == IF IsSet THEN Cardinality(EmptyPages \ cand) ELSE Cardinality(EmptyPages) - n

Init ==
  /\ pg = [p \in Pages |-> FREE]
  /\ R = 0 /\ live = 0 /\ busy = 0
  /\ lapOn = FALSE /\ lapLeft = 0 /\ cursor = 0
  /\ gpc = "idle" /\ examined = 0 /\ checked = {}
  /\ cand = {} /\ n = 0 /\ unknown = FALSE /\ stale = {}
  /\ relatched = FALSE /\ startClean = FALSE
  /\ strongBroken = FALSE /\ weakBroken = FALSE /\ overflow = FALSE /\ futile = FALSE
  /\ maxDrift = 0

(* A delete leaves k chunks on page p. *)
NoteDelete(p, k) ==
  /\ cand' = IF IsSet /\ k = 0 THEN cand \cup {p} ELSE cand
  /\ n' = IF IsCount /\ k = 0 THEN n + 1 ELSE n

(* Empty page p stops being empty (refill, fast path, reclaim). *)
LeaveEmpty(p) ==
  /\ cand' = cand \ {p}
  /\ n' = IF IsCount THEN Dec(n) ELSE n

Sticky == <<strongBroken, weakBroken, overflow, futile, maxDrift>>

-----------------------------------------------------------------------------
Insert ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ live + (IF gpc # "idle" THEN 1 ELSE 0) < L
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] < Cap /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = @ + 1]
       /\ live' = live + 1
       /\ stale' = stale \ {p}
       /\ IF pg[p] = 0 THEN LeaveEmpty(p) ELSE UNCHANGED <<cand, n>>
  /\ UNCHANGED <<R, busy, lapOn, lapLeft, cursor, gpc, examined, checked, unknown,
                 relatched, startClean>>
  /\ UNCHANGED Sticky

VacuumDelete ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0 /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ NoteDelete(p, pg[p] - 1)
       /\ stale' = stale \ {p}
       /\ startClean' = (startClean /\ pg[p] > 1)
  /\ UNCHANGED <<R, busy, lapOn, lapLeft, cursor, gpc, examined, checked, unknown, relatched>>
  /\ UNCHANGED Sticky

FastPath ==
  /\ (WritesDuringGrow \/ gpc = "idle")
  /\ \E p \in EmptyPages :
       /\ busy # p
       /\ pg' = [pg EXCEPT ![p] = FREE]
       /\ LeaveEmpty(p)
       /\ stale' = stale \ {p}
  /\ UNCHANGED <<R, live, busy, lapOn, lapLeft, cursor, gpc, examined, checked, unknown,
                 relatched, startClean>>
  /\ UNCHANGED Sticky

UndoLatch ==
  /\ busy = 0
  /\ (gpc = "idle" \/ ~relatched)
  /\ relatched' = (gpc # "idle")
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0
       /\ busy' = p
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ NoteDelete(p, pg[p] - 1)
       /\ stale' = stale \ {p}
       /\ startClean' = (startClean /\ pg[p] > 1)
  /\ UNCHANGED <<R, lapOn, lapLeft, cursor, gpc, examined, checked, unknown>>
  /\ UNCHANGED Sticky

UndoRelease ==
  /\ busy # 0
  /\ busy' = 0
  /\ UNCHANGED <<pg, R, live, lapOn, lapLeft, cursor, gpc, examined, checked, cand, n, unknown,
                 stale, relatched, startClean>>
  /\ UNCHANGED Sticky

Crash ==
  /\ Crashes
  /\ busy' = 0 /\ gpc' = "idle"
  /\ lapOn' = FALSE /\ lapLeft' = 0 /\ cursor' = 0
  /\ examined' = 0 /\ checked' = {}
  /\ cand' = {} /\ n' = 0 /\ unknown' = BootLap
  /\ stale' = {} /\ relatched' = FALSE /\ startClean' = FALSE
  /\ UNCHANGED <<pg, R, live>>
  /\ UNCHANGED Sticky

-----------------------------------------------------------------------------
StartLap == lapOn' = TRUE /\ lapLeft' = R
KeepLap == UNCHANGED <<lapOn, lapLeft>>

(* The slack rule, decided once per grow from the tracker alone. *)
Need ==
  /\ (~FreeGate \/ ~HasFree)
  /\ (unknown \/ Tracked > K)

StartGrow ==
  /\ gpc = "idle" /\ live < L
  /\ stale' = EmptyPages \ {busy}
  /\ relatched' = FALSE
  /\ startClean' = (EmptyPages = {})
  /\ maxDrift' = IF ~unknown /\ Missed > maxDrift THEN Missed ELSE maxDrift
  /\ IF ~Need
     THEN gpc' = "alloc" /\ KeepLap
     ELSE IF IsSet
          THEN gpc' = "cand" /\ KeepLap
          ELSE gpc' = "scan" /\ IF lapOn THEN KeepLap ELSE StartLap
  /\ UNCHANGED <<pg, R, live, busy, cursor, examined, checked, cand, n, unknown,
                 strongBroken, weakBroken, overflow, futile>>

(* set: check members; a busy one stays.  Set done: lap only after hint loss. *)
CandStep ==
  /\ gpc = "cand"
  /\ IF cand \ checked = {}
     THEN /\ IF unknown
             THEN gpc' = "scan" /\ IF lapOn THEN KeepLap ELSE StartLap
             ELSE gpc' = "alloc" /\ KeepLap
          /\ UNCHANGED <<pg, cand, checked, examined, stale, futile>>
     ELSE \E p \in cand \ checked :
            /\ examined' = examined + 1
            /\ futile' = (futile \/ startClean)
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
  /\ UNCHANGED <<R, live, busy, cursor, n, unknown, relatched, startClean>>
  /\ UNCHANGED <<strongBroken, weakBroken, overflow, maxDrift>>

(* Cursor lap.  Stops at the first reclaim or at the lap end.  A busy empty page stays
   tracked: the set adds it, the count already counts it (or drifted). *)
ScanStep ==
  /\ gpc = "scan"
  /\ IF lapLeft = 0
     THEN /\ lapOn' = FALSE
          /\ unknown' = FALSE
          /\ gpc' = "alloc"
          /\ UNCHANGED <<pg, lapLeft, cursor, examined, cand, n, stale, futile>>
     ELSE LET p == (cursor % R) + 1 IN
          /\ cursor' = p
          /\ examined' = examined + 1
          /\ futile' = (futile \/ startClean)
          /\ lapLeft' = lapLeft - 1
          /\ IF busy = p
             THEN /\ stale' = stale \ {p}
                  /\ cand' = IF IsSet /\ pg[p] = 0 THEN cand \cup {p} ELSE cand
                  /\ UNCHANGED <<pg, gpc, lapOn, n>>
             ELSE IF pg[p] = 0
                  THEN /\ pg' = [pg EXCEPT ![p] = FREE]
                       /\ LeaveEmpty(p)
                       /\ gpc' = "alloc"
                       \* count: d52b1889e returns without settling; the next grow starts a new lap.
                       /\ IF IsCount THEN lapOn' = FALSE /\ lapLeft' = 0 ELSE UNCHANGED lapOn
                       /\ UNCHANGED stale
                  ELSE /\ UNCHANGED <<pg, gpc, lapOn, cand, n, stale>>
          /\ UNCHANGED unknown
  /\ UNCHANGED <<R, live, busy, checked, relatched, startClean>>
  /\ UNCHANGED <<strongBroken, weakBroken, overflow, maxDrift>>

StaleEmpty == Reclaimable(stale)

Alloc ==
  /\ gpc = "alloc"
  /\ gpc' = "idle" /\ examined' = 0 /\ checked' = {} /\ stale' = {}
  /\ relatched' = FALSE /\ startClean' = FALSE
  /\ IF HasFree
     THEN \E p \in {q \in Reserved : pg[q] = FREE} :
            /\ pg' = [pg EXCEPT ![p] = 1]
            /\ live' = live + 1
            /\ UNCHANGED <<R, strongBroken, weakBroken, overflow>>
     ELSE IF R < MaxPages
          THEN /\ R' = R + 1
               /\ pg' = [pg EXCEPT ![R + 1] = 1]
               /\ live' = live + 1
               /\ strongBroken' = (strongBroken \/ StaleEmpty # {})
               /\ weakBroken' = (weakBroken \/ Cardinality(StaleEmpty) > K)
               /\ UNCHANGED overflow
          ELSE /\ overflow' = TRUE
               /\ UNCHANGED <<pg, R, live, strongBroken, weakBroken>>
  /\ UNCHANGED <<busy, lapOn, lapLeft, cursor, cand, n, unknown, futile, maxDrift>>

Next ==
  \/ Insert \/ VacuumDelete \/ FastPath \/ UndoLatch \/ UndoRelease \/ Crash
  \/ StartGrow \/ CandStep \/ ScanStep \/ Alloc

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
NoOverflow == ~overflow
NoFutileWork == ~futile
NoGrowthPastStaleEmpty == ~strongBroken
NoGrowthPastSlack == ~weakBroken
NoDrift == maxDrift = 0

(* The tracker never reports a page that is not empty: an error costs work, never a page. *)
TrackerNeverHigh ==
  IF IsSet THEN cand \subseteq EmptyPages ELSE n <= Cardinality(EmptyPages)

FreeHoldsNothing ==
  /\ \A p \in Pages : p > R => pg[p] = FREE
  /\ busy # 0 => (busy \in Reserved /\ pg[busy] # FREE)

TypeOK ==
  /\ pg \in [Pages -> {FREE} \cup 0..Cap]
  /\ R \in 0..MaxPages /\ live \in 0..L /\ busy \in 0..MaxPages
  /\ gpc \in {"idle", "cand", "scan", "alloc"}
  /\ cand \subseteq Pages /\ stale \subseteq Pages /\ n \in 0..MaxPages
  /\ maxDrift \in 0..MaxPages
=============================================================================
