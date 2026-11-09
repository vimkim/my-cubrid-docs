------------------------------ MODULE CandAttack ------------------------------
(***************************************************************************)
(* Adversarial model of cand_fullboot (CBRD-27925 growth arena).           *)
(*                                                                         *)
(* One OOS file.  A page is FREE (unallocated page of a reserved sector)   *)
(* or holds 0..Cap chunks.  One page = one sector, so R is the file size.  *)
(* R never shrinks (file_destroy only).  Target is post-ADR-0008: no LSA   *)
(* gate, a chunk delete is never undone, only an INSERT rollback undo      *)
(* (oos_rv_redo_delete) removes a chunk under a page WRITE latch.          *)
(*                                                                         *)
(* cand: emptied pages go into a per-file container; a grow pops entries,  *)
(* reclaims an empty unlatched one, puts a busy one back; after hint loss  *)
(* (crash or container overflow) `unknown` forces one single-flight lap.   *)
(*                                                                         *)
(* Relaxations, each a constant:                                           *)
(*   NU          concurrent rollbacks; each may latch any number of pages  *)
(*               during one grow (no per-grow latch limit)                 *)
(*   NG          concurrent growers; the source serializes only the sweep, *)
(*               not file_alloc, and cand needs no sweep when the set is   *)
(*               known                                                     *)
(*   Lazy        an insert into a set page leaves the entry; a grow drops  *)
(*               it when it finds the page non-empty                       *)
(*   Dedupe      FALSE: the container is a list; re-adding a page that is  *)
(*               already listed adds a duplicate                           *)
(*   K           container capacity; an add beyond K drops the entry and   *)
(*               sets unknown                                              *)
(*   EpochFix    TRUE: an overflow during a lap keeps unknown at lap end   *)
(*   InsertFails an insert can fail after it obtained its page and before  *)
(*               its first record: a new page stays allocated and empty;   *)
(*               an adopted empty page loses its entry if not Lazy         *)
(*   FailNote    the failure path adds the still-empty page to the set     *)
(*   AllocNote   every freshly allocated page enters the set (covers any    *)
(*               failure before the first record without an error hook)    *)
(*   LapMode     "call": the d52b1889e sweep shape; every grow that needs  *)
(*               the lap walks the whole file itself from the cursor and   *)
(*               stops at its first reclaim; only a complete lap clears    *)
(*               unknown.  "span": one lap is spread over several grows    *)
(*               and the grow that finishes it allocates.                  *)
(*   A lap visits the pages reserved when it started (cursor[2]); pages    *)
(*   reserved later were allocated after unknown was set.                  *)
(***************************************************************************)
EXTENDS Integers, FiniteSets

CONSTANTS MaxPages, Cap, L, NG, NU, K, Lazy, Dedupe, EpochFix, InsertFails, FailNote, AllocNote,
          LapMode, RelatchOnce, Revisit, TrackCost, Crashes, WritesDuringGrow, Bound, CostBound

ASSUME LapMode \in {"call", "span"}

Pages == 1..MaxPages
Gs == 1..NG
Us == 1..NU
FREE == -1

VARIABLES
  pg, R, live,
  ul,        \* u -> page WRITE-latched by rollback u, 0 if none
  cnt,       \* page -> number of container entries
  unknown,   \* container may be incomplete
  setOver,   \* the container overflowed at least once (diagnostic)
  lapOwner, lapLeft, lapDirty,
  cursor,    \* <<last page the lap visited, pages reserved when the lap started>>
  gpc,       \* g -> idle | cand | decide | scan | alloc
  claim,     \* g -> page popped and being examined, 0 if none
  checked,   \* g -> pages this grow already popped
  examined,  \* g -> pages this grow examined
  stale,     \* g -> pages empty at grow start, untouched since
  broken, overflow,
  relatched  \* a rollback latched a page while a grow was active (RelatchOnce)

vars == <<pg, R, live, ul, cnt, unknown, setOver, lapOwner, lapLeft, lapDirty, cursor,
          gpc, claim, checked, examined, stale, broken, overflow, relatched>>

Reserved == 1..R
Latched(p) == \E u \in Us : ul[u] = p
Claimed(p) == \E g \in Gs : claim[g] = p
Active == {g \in Gs : gpc[g] # "idle"}
Size == LET S[i \in 0..MaxPages] == IF i = 0 THEN 0 ELSE S[i - 1] + cnt[i] IN S[MaxPages]
Sat(n) == IF ~TrackCost THEN 0 ELSE IF n > 3 * MaxPages THEN 3 * MaxPages + 1 ELSE n
Quiet == WritesDuringGrow \/ Active = {}
Touch(p) == stale' = [g \in Gs |-> stale[g] \ {p}]

(* Add one entry for p; beyond K the entry is dropped and the container becomes unknown. *)
Add(p) ==
  IF Dedupe /\ cnt[p] > 0
  THEN UNCHANGED <<cnt, unknown, setOver, lapDirty>>
  ELSE IF Size < K
       THEN cnt' = [cnt EXCEPT ![p] = @ + 1] /\ UNCHANGED <<unknown, setOver, lapDirty>>
       ELSE /\ unknown' = TRUE /\ setOver' = TRUE /\ lapDirty' = TRUE
            /\ UNCHANGED cnt

Init ==
  /\ pg = [p \in Pages |-> FREE] /\ R = 0 /\ live = 0
  /\ ul = [u \in Us |-> 0] /\ cnt = [p \in Pages |-> 0]
  /\ unknown = FALSE /\ setOver = FALSE
  /\ lapOwner = 0 /\ lapLeft = 0 /\ lapDirty = FALSE /\ cursor = <<0, 0>>
  /\ gpc = [g \in Gs |-> "idle"] /\ claim = [g \in Gs |-> 0]
  /\ checked = [g \in Gs |-> {}] /\ examined = [g \in Gs |-> 0] /\ stale = [g \in Gs |-> {}]
  /\ broken = FALSE /\ overflow = FALSE /\ relatched = FALSE

-----------------------------------------------------------------------------
(* Writers *)

Insert ==
  /\ Quiet
  /\ live + Cardinality(Active) < L
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] < Cap /\ ~Latched(p)
       /\ pg' = [pg EXCEPT ![p] = @ + 1]
       /\ live' = live + 1
       /\ Touch(p)
       /\ cnt' = IF Lazy THEN cnt ELSE [cnt EXCEPT ![p] = 0]
  /\ UNCHANGED <<R, ul, unknown, setOver, lapOwner, lapLeft, lapDirty, cursor, gpc, claim,
                 checked, examined, broken, overflow, relatched>>

(* oos_find_best_page hands an empty page to an insert that then fails before its record. *)
AdoptFail ==
  /\ InsertFails /\ Quiet
  /\ \E p \in Reserved :
       /\ pg[p] = 0 /\ ~Latched(p)
       /\ Touch(p)
       /\ IF Lazy THEN UNCHANGED <<cnt, unknown, setOver, lapDirty>>
          ELSE IF FailNote THEN cnt' = [cnt EXCEPT ![p] = 1] /\ UNCHANGED <<unknown, setOver, lapDirty>>
          ELSE cnt' = [cnt EXCEPT ![p] = 0] /\ UNCHANGED <<unknown, setOver, lapDirty>>
  /\ UNCHANGED <<pg, R, live, ul, lapOwner, lapLeft, cursor, gpc, claim, checked, examined,
                 broken, overflow, relatched>>

(* The ADR-0008 reclaimer: a redo-only chunk delete; it adds the page when it empties it. *)
ReclaimerDelete ==
  /\ Quiet
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0 /\ ~Latched(p)
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ Touch(p)
       /\ IF pg[p] = 1 THEN Add(p) ELSE UNCHANGED <<cnt, unknown, setOver, lapDirty>>
  /\ UNCHANGED <<R, ul, lapOwner, lapLeft, cursor, gpc, claim, checked, examined, broken, overflow, relatched>>

(* Vacuum fast path: may reclaim an empty page that nobody latches or examines (fed by its own
   list, not by the set).  A lazy set keeps the entry for the freed page. *)
FastPath ==
  /\ Quiet
  /\ \E p \in Reserved :
       /\ pg[p] = 0 /\ ~Latched(p) /\ ~Claimed(p)
       /\ pg' = [pg EXCEPT ![p] = FREE]
       /\ cnt' = IF Lazy THEN cnt ELSE [cnt EXCEPT ![p] = 0]
       /\ Touch(p)
  /\ UNCHANGED <<R, live, ul, unknown, setOver, lapOwner, lapLeft, lapDirty, cursor, gpc, claim,
                 checked, examined, broken, overflow, relatched>>

(* INSERT rollback u: oos_rv_redo_delete removes a chunk under the WRITE latch and adds the page
   when it empties it.  No limit on how often u latches during one grow. *)
UndoLatch(u) ==
  /\ ul[u] = 0
  /\ ~(RelatchOnce /\ relatched /\ Active # {})
  /\ relatched' = (relatched \/ Active # {})
  /\ \E p \in Reserved :
       /\ pg[p] # FREE /\ pg[p] > 0 /\ ~Latched(p)
       /\ ul' = [ul EXCEPT ![u] = p]
       /\ pg' = [pg EXCEPT ![p] = @ - 1]
       /\ live' = live - 1
       /\ Touch(p)
       /\ IF pg[p] = 1 THEN Add(p) ELSE UNCHANGED <<cnt, unknown, setOver, lapDirty>>
  /\ UNCHANGED <<R, lapOwner, lapLeft, cursor, gpc, claim, checked, examined, broken, overflow>>

UndoRelease(u) ==
  /\ ul[u] # 0
  /\ ul' = [ul EXCEPT ![u] = 0]
  /\ UNCHANGED <<pg, R, live, cnt, unknown, setOver, lapOwner, lapLeft, lapDirty, cursor, gpc,
                 claim, checked, examined, stale, broken, overflow, relatched>>

Crash ==
  /\ Crashes
  /\ ul' = [u \in Us |-> 0] /\ cnt' = [p \in Pages |-> 0] /\ unknown' = TRUE
  /\ lapOwner' = 0 /\ lapLeft' = 0 /\ lapDirty' = FALSE /\ cursor' = <<0, 0>>
  /\ gpc' = [g \in Gs |-> "idle"] /\ claim' = [g \in Gs |-> 0]
  /\ checked' = [g \in Gs |-> {}] /\ examined' = [g \in Gs |-> 0] /\ stale' = [g \in Gs |-> {}]
  /\ relatched' = FALSE
  /\ UNCHANGED <<pg, R, live, setOver, broken, overflow>>

-----------------------------------------------------------------------------
(* Growers *)

StartGrow(g) ==
  /\ gpc[g] = "idle" /\ live + Cardinality(Active) < L
  /\ relatched' = (relatched /\ Active # {})
  /\ gpc' = [gpc EXCEPT ![g] = "cand"]
  /\ stale' = [stale EXCEPT ![g] = {p \in Reserved : pg[p] = 0 /\ ~Latched(p) /\ ~Claimed(p)}]
  /\ UNCHANGED <<pg, R, live, ul, cnt, unknown, setOver, lapOwner, lapLeft, lapDirty, cursor,
                 claim, checked, examined, broken, overflow>>

(* Pop one entry of a page this grow has not examined yet (under bestspace_mutex), so a grow
   examines each page at most once; or, with none left, go to the lap or allocate.  A grower
   that needs the lap while another grower owns it waits (pthread_cond_wait). *)
CandStep(g) ==
  /\ gpc[g] = "cand"
  /\ IF \E p \in Pages : cnt[p] > 0 /\ p \notin checked[g]
     THEN \E p \in Pages :
            /\ cnt[p] > 0 /\ p \notin checked[g]
            /\ cnt' = [cnt EXCEPT ![p] = @ - 1]
            /\ claim' = [claim EXCEPT ![g] = p]
            /\ checked' = IF Revisit THEN checked ELSE [checked EXCEPT ![g] = @ \cup {p}]
            /\ gpc' = [gpc EXCEPT ![g] = "decide"]
            /\ examined' = [examined EXCEPT ![g] = Sat(@ + 1)]
            /\ stale' = [h \in Gs |-> IF h = g THEN stale[h] ELSE stale[h] \ {p}]
            /\ UNCHANGED <<lapOwner, lapLeft, lapDirty, cursor>>
     ELSE IF ~unknown
     THEN /\ gpc' = [gpc EXCEPT ![g] = "alloc"]
          /\ UNCHANGED <<cnt, claim, checked, examined, stale, lapOwner, lapLeft, lapDirty, cursor>>
     ELSE /\ lapOwner = 0
          /\ lapOwner' = g
          /\ gpc' = [gpc EXCEPT ![g] = "scan"]
          /\ IF LapMode = "call" \/ lapLeft = 0
             THEN lapLeft' = R /\ lapDirty' = FALSE /\ cursor' = <<cursor[1], R>>
             ELSE UNCHANGED <<lapLeft, lapDirty, cursor>>
          /\ UNCHANGED <<cnt, claim, checked, examined, stale>>
  /\ UNCHANGED <<pg, R, live, ul, unknown, setOver, broken, overflow, relatched>>

(* oos_try_reclaim_page_internal on the popped page (phase 2 is the binding verdict). *)
Decide(g) ==
  /\ gpc[g] = "decide"
  /\ LET p == claim[g] IN
     /\ claim' = [claim EXCEPT ![g] = 0]
     /\ IF Latched(p)
        THEN /\ gpc' = [gpc EXCEPT ![g] = "cand"]
             /\ checked' = [checked EXCEPT ![g] = @ \cup {p}]
             /\ Add(p)
             /\ UNCHANGED pg
        ELSE IF pg[p] = 0
        THEN /\ pg' = [pg EXCEPT ![p] = FREE]
             /\ gpc' = [gpc EXCEPT ![g] = "alloc"]
             /\ UNCHANGED <<checked, cnt, unknown, setOver, lapDirty>>
        ELSE /\ gpc' = [gpc EXCEPT ![g] = "cand"]
             /\ UNCHANGED <<pg, checked, cnt, unknown, setOver, lapDirty>>
  /\ UNCHANGED <<R, live, ul, lapOwner, lapLeft, cursor, examined, stale, broken, overflow, relatched>>

(* The lap after hint loss: one page per step from the cursor; a busy page goes into the set.  The
   first reclaim ends this grow; in "call" mode it also abandons the lap.  A complete lap clears
   unknown unless the set overflowed during it (EpochFix). *)
ScanStep(g) ==
  /\ gpc[g] = "scan"
  /\ IF lapLeft = 0
     THEN /\ unknown' = (EpochFix /\ lapDirty)
          /\ lapOwner' = 0
          /\ gpc' = [gpc EXCEPT ![g] = "alloc"]
          /\ UNCHANGED <<pg, cnt, setOver, lapLeft, lapDirty, cursor, examined, stale>>
     ELSE LET p == (cursor[1] % cursor[2]) + 1 IN
          /\ cursor' = <<p, cursor[2]>>
          /\ examined' = [examined EXCEPT ![g] = Sat(@ + 1)]
          /\ IF Latched(p) \/ Claimed(p)
             THEN /\ Add(p)
                  /\ lapLeft' = lapLeft - 1
                  /\ UNCHANGED <<pg, gpc, lapOwner, unknown, stale>>
             ELSE IF pg[p] = 0
             THEN /\ pg' = [pg EXCEPT ![p] = FREE]
                  /\ cnt' = [cnt EXCEPT ![p] = 0]
                  /\ lapOwner' = 0
                  /\ lapLeft' = IF LapMode = "call" THEN 0 ELSE lapLeft - 1
                  /\ gpc' = [gpc EXCEPT ![g] = "alloc"]
                  /\ UNCHANGED <<unknown, setOver, lapDirty, stale>>
             ELSE /\ lapLeft' = lapLeft - 1
                  /\ UNCHANGED <<pg, gpc, cnt, lapOwner, unknown, setOver, lapDirty, stale>>
  /\ UNCHANGED <<R, live, ul, claim, checked, broken, overflow, relatched>>

(* file_alloc: a FREE page of a reserved sector first, else reserve a new sector.  With
   InsertFails the insert may fail before its first record and leave the page empty. *)
Alloc(g) ==
  /\ gpc[g] = "alloc"
  /\ gpc' = [gpc EXCEPT ![g] = "idle"]
  /\ checked' = [checked EXCEPT ![g] = {}] /\ examined' = [examined EXCEPT ![g] = 0]
  /\ \E fail \in (IF InsertFails THEN BOOLEAN ELSE {FALSE}) :
     LET Fill(p) ==
           /\ pg' = [pg EXCEPT ![p] = IF fail THEN 0 ELSE 1]
           /\ live' = IF fail THEN live ELSE live + 1
           /\ IF (fail /\ FailNote) \/ AllocNote THEN Add(p)
              ELSE UNCHANGED <<cnt, unknown, setOver, lapDirty>>
     IN IF \E p \in Reserved : pg[p] = FREE
        THEN /\ \E p \in {q \in Reserved : pg[q] = FREE} :
                  /\ Fill(p)
                  /\ stale' = [h \in Gs |-> IF h = g THEN {} ELSE stale[h] \ {p}]
             /\ UNCHANGED <<R, broken, overflow>>
        ELSE IF R < MaxPages
        THEN /\ R' = R + 1
             /\ Fill(R + 1)
             /\ broken' = (broken \/ \E p \in stale[g] : pg[p] = 0 /\ ~Latched(p) /\ ~Claimed(p))
             /\ stale' = [stale EXCEPT ![g] = {}]
             /\ UNCHANGED overflow
        ELSE /\ overflow' = TRUE
             /\ UNCHANGED <<pg, R, live, broken, stale, cnt, unknown, setOver, lapDirty>>
  /\ UNCHANGED <<ul, lapOwner, lapLeft, cursor, claim, relatched>>

Next ==
  \/ Insert \/ AdoptFail \/ ReclaimerDelete \/ FastPath \/ Crash
  \/ \E u \in Us : UndoLatch(u) \/ UndoRelease(u)
  \/ \E g \in Gs : StartGrow(g) \/ CandStep(g) \/ Decide(g) \/ ScanStep(g) \/ Alloc(g)

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
NoOverflow == ~overflow
SizeWithinBound == R <= Bound
CostWithinBound == \A g \in Gs : examined[g] <= CostBound
(* A grow reserves a sector only when no page that was empty at its start, and that nobody wrote,
   latched or examined since, is still empty. *)
Strict == ~broken
NoSetOverflow == ~setOver
Safety ==
  /\ \A p \in Pages : p > R => pg[p] = FREE
  /\ \A u \in Us : ul[u] # 0 => ul[u] \in Reserved /\ pg[ul[u]] # FREE
  /\ \A g \in Gs : lapOwner = g => gpc[g] = "scan"
=============================================================================
