--------------------------- MODULE SidecarRecovery ---------------------------
(***************************************************************************)
(* Sidecar design (design.md, 2026-11-04), crash recovery and undo safety. *)
(*                                                                         *)
(* Promises checked, one TLC run each:                                     *)
(*  UndoFindsEmptySlot  every undo finds its slot as it needs it: empty    *)
(*                      for a re-insert (spage_insert_for_recovery), its   *)
(*                      own record for an in-place rewrite (spage_update,  *)
(*                      heap_rv_mvcc_undo_delete).                         *)
(*  UndoFindsRoom       every undo that grows a record finds the bytes.    *)
(*  AtomicRow           after recovery and quiesced vacuum, a committed    *)
(*                      row's hot record and every store record it names   *)
(*                      are present, and no other store record is live.    *)
(*                                                                         *)
(* One hot page hp, two store pages s1 and s2.  Actors:                    *)
(*  - T, the row's own transaction, running one Sidecar flow of design     *)
(*    section 6 in the design's order (store writes, then the hot write),  *)
(*    then commit, rollback, or statement rollback and commit;             *)
(*  - one store vacuum worker removing a dead store record w (REC_HOME     *)
(*    bulk, REC_RELOCATION sysop or REC_BIGONE sysop), and the bulk        *)
(*    removal of T's stamped value v once vacuum may see T's DELID;        *)
(*  - other transactions, each inserting one record on any page, then      *)
(*    committing (other rows' store or hot records);                       *)
(*  - one crash at any point, then restart undo.                           *)
(*                                                                         *)
(* README.md maps every action to its design section and engine line.     *)
(* Bytes are abstract units.  Saved space is spage_save_space's memory     *)
(* reservation for T; an active transaction's insert subtracts it, an      *)
(* undo (TRAN_UNACTIVE_ABORTED or crash recovery) ignores it.              *)
(***************************************************************************)
EXTENDS Integers, Sequences, FiniteSets, TLC

CONSTANTS
    Flows,                    \* T's flows to explore
    VacKinds,                 \* record types of the dead store record w
    Inserters,                \* other transactions (model values)
    InsertSizes,              \* units one of their inserts takes
    HotFree0,                 \* free units on hp at the start
    StoreFree0,               \* free units on s1 and on s2 at the start
    TPost,                    \* whether T logged a postpone (LOG_COMMIT_WITH_POSTPONE)
    Fix775,                   \* vacuum keeps the forward page until log_sysop_commit
    Fix776,                   \* log_commit_local frees saved space after LOG_COMMIT
    StampMayRelocate,         \* a DELID stamp may relocate its store record
    HotFirst,                 \* broken: T's hot write precedes its store writes
    SkipStamp,                \* broken: UPDATE and DELETE leave the dropped value unstamped
    VacuumBeforeCommitRecord  \* broken: vacuum ignores the complete_mvcc guard

ASSUME Flows \subseteq {"INSERT", "UPD_REF", "UPD_EXT", "DELETE"} /\ Flows # {}
ASSUME VacKinds \subseteq {"REC_HOME", "REC_RELOCATION", "REC_BIGONE"} /\ VacKinds # {}
ASSUME TPost \subseteq BOOLEAN /\ TPost # {}
ASSUME InsertSizes \subseteq 1..2 /\ HotFree0 \subseteq 0..2 /\ StoreFree0 \subseteq 0..4
ASSUME \A b \in {Fix775, Fix776, StampMayRelocate, HotFirst, SkipStamp,
                 VacuumBeforeCommitRecord} : b \in BOOLEAN

VS == 2  \* a store record: SIDECAR_VALUE_HEADER and the value bytes
HS == 1  \* a hot record whose large value is a 16-byte ref
HB == 2  \* a hot record that holds the large value inline

Pages == {"hp", "s1", "s2"}
\* A page the heap allocates when no modeled page has room; nothing else
\* touches it, so only its slot matters, not its bytes.
NewPage == {"news", "newhp"}
PageName(p) == CASE p = "hp" -> "the hot page" [] p = "s1" -> "store page s1"
                 [] p = "s2" -> "store page s2" [] p = "news" -> "a new store page"
                 [] p = "newhp" -> "a new hot page"

\* Store slots that some undo writes back into:
\*  v   the value the row names before T, on s1 (UPD_REF, DELETE);
\*  wh  the home slot of the dead store record w, on s1;
\*  wf  w's REC_NEWHOME slot on s2 (w is REC_RELOCATION).
SlotIds == {"v", "wh", "wf"}
SlotPage(s) == IF s = "wf" THEN "s2" ELSE "s1"
OtherLoc(p) == "other_" \o p      \* a fresh slot no undo ever writes into

Rec(x) == [st |-> "rec", val |-> x]          \* a record of value x
Fwd(x) == [st |-> "fwd", val |-> x]          \* x's REC_RELOCATION or REC_BIGONE home record
Reuse == [st |-> "reuse", val |-> "none"]    \* REC_DELETED_WILL_REUSE
Marked == [st |-> "marked", val |-> "none"]  \* REC_MARKDELETED, never handed out
Absent == [st |-> "absent", val |-> "none"]  \* no such slot in this flow
Corrupt(x) == [st |-> "corrupt", val |-> x]  \* an undo wrote over x

\* nv: T's new value.  vreloc: v's body after a stamp relocated it.
Tracked == {"nv", "vreloc"} \cup Inserters

VARIABLES
    flow, vkind, tpost,     \* choices fixed at Init
    slot,                   \* [SlotIds -> slot state]
    loc,                    \* [Tracked -> where the record body is]
    delid,                  \* [{"v","vreloc"} -> T's DELID is in the record]
    hot,                    \* the row's hot record
    free,                   \* [Pages -> total_free]
    saved,                  \* [Pages -> bytes T saved with spage_save_space]
    tstep, tphase, trel,    \* where T is
    tcommit,                \* T's commit point (LOG_COMMIT or LOG_COMMIT_WITH_POSTPONE) is logged
    tmvcc,                  \* T ran logtb_complete_mvcc
    vpc, sysop, vlatch,     \* the vacuum worker on w
    vrm,                    \* vacuum removed v
    ipc,                    \* [Inserters -> where each other transaction is]
    log,                    \* log records an undo can apply, in LSA order
    phase,                  \* running, recovering, recovered, or failed (logpb_fatal_error)
    brokenSlot, brokenRoom, \* actors whose undo found the slot wrong or too few bytes
    last                    \* the last step in design words (not part of the state view)

vars == <<flow, vkind, tpost, slot, loc, delid, hot, free, saved, tstep, tphase,
          trel, tcommit, tmvcc, vpc, sysop, vlatch, vrm, ipc, log, phase,
          brokenSlot, brokenRoom, last>>
StateView == <<flow, vkind, tpost, slot, loc, delid, hot, free, saved, tstep,
               tphase, trel, tcommit, tmvcc, vpc, sysop, vlatch, vrm, ipc, log,
               phase, brokenSlot, brokenRoom>>

data == <<slot, loc, delid, hot, free, saved>>
tvars == <<tstep, tphase, trel, tcommit, tmvcc>>
vvars == <<vpc, sysop, vlatch, vrm>>
fixed == <<flow, vkind, tpost>>
checks == <<brokenSlot, brokenRoom>>

LR(t, k, p, s, n, x) == [txn |-> t, kind |-> k, page |-> p, slot |-> s,
                         size |-> n, val |-> x, undone |-> FALSE]

HotWrites == {"hot_insert", "hot_update", "hot_delete"}
BaseSteps ==
    CASE flow = "INSERT" -> <<"store_insert", "hot_insert">>
      [] flow = "UPD_REF" -> <<"store_insert", "stamp", "hot_update">>
      [] flow = "UPD_EXT" -> <<"store_insert", "hot_update">>
      [] flow = "DELETE" -> <<"stamp", "hot_delete">>
Steps0 == SelectSeq(BaseSteps, LAMBDA x : ~(SkipStamp /\ x = "stamp"))
TSteps == IF HotFirst
          THEN SelectSeq(Steps0, LAMBDA x : x \in HotWrites)
               \o SelectSeq(Steps0, LAMBDA x : x \notin HotWrites)
          ELSE Steps0
CurStep == IF tstep <= Len(TSteps) THEN TSteps[tstep] ELSE "end"

CanTake(p, s) == s = "other" \/ (p \in Pages /\ s \in SlotIds /\ SlotPage(s) = p /\ slot[s] = Reuse)
Put(s, r) == IF s = "other" THEN slot ELSE [slot EXCEPT ![s] = r]
Where(p, s) == IF s = "other" THEN OtherLoc(p) ELSE s
SlotWord(s) == CASE s = "other" -> "a fresh slot"
                 [] s = "wf" -> "w's freed REC_NEWHOME slot"
                 [] s = "wh" -> "w's home slot"
                 [] s = "v" -> "v's slot"
                 [] s = "h" -> "the row's hot slot"
\* An active transaction's insert: spage_has_enough_total_space subtracts saved space.
Fits(p, n) == IF p \in NewPage THEN TRUE ELSE n + saved[p] <= free[p]
Take(p, n) == IF p \in NewPage THEN free ELSE [free EXCEPT ![p] = @ - n]

Who(t) == IF t \in {"T", "vacuum"} THEN t ELSE "INSERT " \o ToString(t)

Undoable(T) == {i \in 1..Len(log) : log[i].txn \in T /\ ~log[i].undone}
LastUndoable(T) == CHOOSE i \in Undoable(T) : \A j \in Undoable(T) : j <= i

Init ==
    /\ flow \in Flows
    /\ vkind \in VacKinds
    /\ tpost \in TPost
    /\ slot = [s \in SlotIds |->
                 CASE s = "v" -> IF flow \in {"UPD_REF", "DELETE"} THEN Rec("v") ELSE Absent
                   [] s = "wh" -> IF vkind = "REC_HOME" THEN Rec("w") ELSE Fwd("w")
                   [] s = "wf" -> IF vkind = "REC_RELOCATION" THEN Rec("w") ELSE Absent]
    /\ loc = [x \in Tracked |-> "none"]
    /\ delid = [x \in {"v", "vreloc"} |-> FALSE]
    /\ hot = CASE flow = "INSERT" -> [ex |-> FALSE, names |-> "none", del |-> FALSE]
               [] flow = "UPD_EXT" -> [ex |-> TRUE, names |-> "inline", del |-> FALSE]
               [] OTHER -> [ex |-> TRUE, names |-> "v", del |-> FALSE]
    /\ free \in {[hp |-> a, s1 |-> b, s2 |-> c] : a \in HotFree0, b \in StoreFree0, c \in StoreFree0}
    /\ saved = [p \in Pages |-> 0]
    /\ tstep = 1 /\ tphase = "work" /\ trel = "none" /\ tcommit = FALSE /\ tmvcc = FALSE
    /\ vpc = "fix" /\ sysop = "none" /\ vlatch = {} /\ vrm = FALSE
    /\ ipc = [i \in Inserters |-> "idle"]
    /\ log = <<>>
    /\ phase = "running"
    /\ brokenSlot = {} /\ brokenRoom = {}
    /\ last = "start: T has not written; w is dead in the store"

---------------------------------------------------------------------------
(* Undo of one log record, by T's rollback, a vacuum sysop abort or       *)
(* restart recovery.  The undo runs as TRAN_UNACTIVE_ABORTED or in crash   *)
(* recovery, so its room test is total_free.  A failed undo ends in        *)
(* logpb_fatal_error (log_rv_undo_record), except that a re-insert over a  *)
(* live record is only a debug assertion: a release build overwrites it.   *)

UndoWord(r) ==
    CASE r.kind = "ins" -> "deletes the record it inserted in " \o SlotWord(r.slot)
                           \o " on " \o PageName(r.page) \o " (heap_rv_undo_insert)"
      [] r.kind = "stamp" -> "clears the DELID stamp on v (heap_rv_mvcc_undo_delete)"
      [] r.kind = "modhome" -> "writes v back over its forwarding record on s1 (RVHF_MVCC_DELETE_MODIFY_HOME, heap_rv_undo_update)"
      [] r.kind = "hotupd" -> "restores the old hot image (RVHF_UPDATE_NOTIFY_VACUUM, heap_rv_undo_update)"
      [] r.kind = "hotdel" -> "clears the hot DELID (heap_rv_mvcc_undo_delete)"
      [] r.kind = "vac" -> "re-inserts w's " \o (IF r.slot = "wf" THEN "REC_NEWHOME" ELSE "home record")
                           \o " on " \o PageName(r.page) \o " (RVVAC_HEAP_RECORD_VACUUM, spage_insert_for_recovery)"

UndoRec(i) ==
    LET r == log[i]
        p == r.page
        s == r.slot
        who == IF r.txn \in {"T", "vacuum"} THEN r.txn ELSE "inserter"
        needsRoom == r.kind \in {"modhome", "hotupd", "vac"}
        room == ~needsRoom \/ r.size <= free[p]
        slotOK == CASE r.kind = "stamp" -> slot["v"] = Rec("v")
                    [] r.kind = "modhome" -> slot["v"] = Fwd("v")
                    [] r.kind = "vac" -> slot[s].st \in {"reuse", "marked"}
                    [] OTHER -> TRUE
        fatal == ~room \/ (~slotOK /\ r.kind # "vac")
    IN  /\ log' = [log EXCEPT ![i].undone = TRUE]
        /\ brokenSlot' = IF slotOK THEN brokenSlot ELSE brokenSlot \cup {who}
        /\ brokenRoom' = IF room THEN brokenRoom ELSE brokenRoom \cup {who}
        /\ IF fatal
           THEN /\ phase' = "failed"
                /\ UNCHANGED data
           ELSE /\ phase' = phase
                /\ saved' = saved
                /\ CASE r.kind = "ins" ->
                          /\ slot' = IF s \in SlotIds THEN [slot EXCEPT ![s] = Reuse] ELSE slot
                          /\ loc' = IF r.val \in Tracked THEN [loc EXCEPT ![r.val] = "none"] ELSE loc
                          /\ hot' = IF s = "h" THEN [hot EXCEPT !.ex = FALSE] ELSE hot
                          /\ free' = IF p \in NewPage THEN free ELSE [free EXCEPT ![p] = @ + r.size]
                          /\ delid' = delid
                     [] r.kind = "stamp" ->
                          /\ delid' = [delid EXCEPT !["v"] = FALSE]
                          /\ UNCHANGED <<slot, loc, hot, free>>
                     [] r.kind = "modhome" ->
                          /\ slot' = [slot EXCEPT !["v"] = Rec("v")]
                          /\ free' = [free EXCEPT ![p] = @ - r.size]
                          /\ UNCHANGED <<loc, delid, hot>>
                     [] r.kind = "hotupd" ->
                          /\ hot' = [hot EXCEPT !.names = r.val]
                          /\ free' = [free EXCEPT ![p] = @ - r.size]
                          /\ UNCHANGED <<slot, loc, delid>>
                     [] r.kind = "hotdel" ->
                          /\ hot' = [hot EXCEPT !.del = FALSE]
                          /\ UNCHANGED <<slot, loc, delid, free>>
                     [] r.kind = "vac" ->
                          /\ slot' = [slot EXCEPT ![s] = IF ~slotOK THEN Corrupt(slot[s].val)
                                                         ELSE IF r.val = "wfwd" THEN Fwd("w")
                                                         ELSE Rec("w")]
                          /\ free' = [free EXCEPT ![p] = @ - r.size]
                          /\ UNCHANGED <<loc, delid, hot>>

FailWord(i) ==
    LET r == log[i]
        slotOK == CASE r.kind = "stamp" -> slot["v"] = Rec("v")
                    [] r.kind = "modhome" -> slot["v"] = Fwd("v")
                    [] r.kind = "vac" -> slot[r.slot].st \in {"reuse", "marked"}
                    [] OTHER -> TRUE
        room == r.kind \notin {"modhome", "hotupd", "vac"} \/ r.size <= free[r.page]
    IN  (IF ~slotOK THEN " -- the slot is not as the undo needs it" ELSE "")
        \o (IF ~room THEN " -- too few free bytes (SP_DOESNT_FIT, logpb_fatal_error)" ELSE "")

---------------------------------------------------------------------------
(* T: the row's transaction.  Each step holds one page latch for the     *)
(* whole step.  Between steps T holds no data page (I-7); the row X lock   *)
(* keeps other writers off the row.                                        *)

TWork == phase = "running" /\ tphase = "work"

\* sidecar_apply_plan -> heap_insert_logical on the store (design 6 INSERT step 5):
\* RVHF_MVCC_INSERT, undo heap_rv_undo_insert.
TStoreInsert(p, s) ==
    /\ TWork /\ CurStep = "store_insert"
    /\ p \in {"s1", "s2", "news"} /\ p \notin vlatch
    /\ Fits(p, VS) /\ CanTake(p, s)
    /\ slot' = Put(s, Rec("nv"))
    /\ loc' = [loc EXCEPT !["nv"] = Where(p, s)]
    /\ free' = Take(p, VS)
    /\ log' = Append(log, LR("T", "ins", p, s, VS, "nv"))
    /\ tstep' = tstep + 1
    /\ last' = "T: inserts the new value nv into " \o SlotWord(s) \o " on " \o PageName(p)
               \o " (store RVHF_MVCC_INSERT)"
    /\ UNCHANGED <<fixed, delid, hot, saved, tphase, trel, tcommit, tmvcc, vvars, ipc,
                   phase, checks>>

\* heap_delete_logical on the store, DELID fits: RVHF_MVCC_DELETE_REC_HOME.
TStampInPlace ==
    /\ TWork /\ CurStep = "stamp" /\ trel = "none"
    /\ "s1" \notin vlatch /\ slot["v"] = Rec("v")
    /\ delid' = [delid EXCEPT !["v"] = TRUE]
    /\ log' = Append(log, LR("T", "stamp", "s1", "v", 0, "v"))
    /\ tstep' = tstep + 1
    /\ last' = "T: stamps DELID on v in place (store RVHF_MVCC_DELETE_REC_HOME)"
    /\ UNCHANGED <<fixed, slot, loc, hot, free, saved, tphase, trel, tcommit, tmvcc,
                   vvars, ipc, phase, checks>>

\* heap_delete_home, DELID does not fit: heap_insert_newhome puts v with its
\* DELID on another store page (RVHF_INSERT_NEWHOME, undo heap_rv_undo_insert).
TStampNewhome(p, s) ==
    /\ TWork /\ CurStep = "stamp" /\ trel = "none" /\ StampMayRelocate
    /\ slot["v"] = Rec("v")
    /\ p \in {"s2", "news"} /\ p \notin vlatch /\ Fits(p, VS) /\ CanTake(p, s)
    /\ slot' = Put(s, Rec("vreloc"))
    /\ loc' = [loc EXCEPT !["vreloc"] = Where(p, s)]
    /\ delid' = [delid EXCEPT !["vreloc"] = TRUE]
    /\ free' = Take(p, VS)
    /\ log' = Append(log, LR("T", "ins", p, s, VS, "vreloc"))
    /\ trel' = "newhome"
    /\ last' = "T: the DELID does not fit; heap_insert_newhome puts v with its DELID into "
               \o SlotWord(s) \o " on " \o PageName(p) \o " (RVHF_INSERT_NEWHOME)"
    /\ UNCHANGED <<fixed, hot, saved, tstep, tphase, tcommit, tmvcc, vvars, ipc, phase,
                   checks>>

\* heap_mvcc_log_home_change_on_delete logs RVHF_MVCC_DELETE_MODIFY_HOME with
\* the whole old record as undo; heap_update_physical -> spage_update shrinks
\* the home slot to the forwarding record and saves the freed bytes.
TStampModifyHome ==
    /\ TWork /\ CurStep = "stamp" /\ trel = "newhome"
    /\ "s1" \notin vlatch /\ slot["v"] = Rec("v")
    /\ slot' = [slot EXCEPT !["v"] = Fwd("v")]
    /\ free' = [free EXCEPT !["s1"] = @ + VS]
    /\ saved' = [saved EXCEPT !["s1"] = @ + VS]
    /\ log' = Append(log, LR("T", "modhome", "s1", "v", VS, "v"))
    /\ trel' = "none"
    /\ tstep' = tstep + 1
    /\ last' = "T: v's home slot on s1 becomes a forwarding record (RVHF_MVCC_DELETE_MODIFY_HOME); spage_update saves the freed bytes for T"
    /\ UNCHANGED <<fixed, loc, delid, hot, tphase, tcommit, tmvcc, vvars, ipc, phase,
                   checks>>

\* heap_insert_logical continues with the hot record (INSERT step 7).
THotInsert(p) ==
    /\ TWork /\ CurStep = "hot_insert" /\ p \in {"hp", "newhp"} /\ Fits(p, HS)
    /\ hot' = [ex |-> TRUE, names |-> "nv", del |-> FALSE]
    /\ free' = Take(p, HS)
    /\ log' = Append(log, LR("T", "ins", p, "h", HS, "h"))
    /\ tstep' = tstep + 1
    /\ last' = "T: inserts the hot record naming nv on " \o PageName(p) \o " (hot RVHF_MVCC_INSERT)"
    /\ UNCHANGED <<fixed, slot, loc, delid, saved, tphase, trel, tcommit, tmvcc, vvars,
                   ipc, phase, checks>>

\* heap_update_logical repeats the location step and writes the hot record
\* (UPDATE step 6): RVHF_UPDATE_NOTIFY_VACUUM with the old image as undo.
\* UPD_EXT replaces an inline value by a ref, so spage_update shrinks the
\* record and saves the freed bytes.
THotUpdate ==
    /\ TWork /\ CurStep = "hot_update"
    /\ LET shrink == IF hot.names = "inline" THEN HB - HS ELSE 0
       IN  /\ hot' = [hot EXCEPT !.names = "nv"]
           /\ free' = [free EXCEPT !["hp"] = @ + shrink]
           /\ saved' = [saved EXCEPT !["hp"] = @ + shrink]
           /\ log' = Append(log, LR("T", "hotupd", "hp", "h", shrink, hot.names))
           /\ last' = "T: writes the hot record naming nv (RVHF_UPDATE_NOTIFY_VACUUM)"
                      \o (IF shrink > 0 THEN "; the record shrinks and spage_update saves the freed bytes for T"
                          ELSE "")
    /\ tstep' = tstep + 1
    /\ UNCHANGED <<fixed, slot, loc, delid, tphase, trel, tcommit, tmvcc, vvars, ipc,
                   phase, checks>>

\* heap_delete_logical on the hot record (DELETE step 3).
THotDelete ==
    /\ TWork /\ CurStep = "hot_delete"
    /\ hot' = [hot EXCEPT !.del = TRUE]
    /\ log' = Append(log, LR("T", "hotdel", "hp", "h", 0, "none"))
    /\ tstep' = tstep + 1
    /\ last' = "T: stamps DELID on the hot record (hot RVHF_MVCC_DELETE_REC_HOME)"
    /\ UNCHANGED <<fixed, slot, loc, delid, free, saved, tphase, trel, tcommit, tmvcc,
                   vvars, ipc, phase, checks>>

TWorkDone == tphase = "rbdone" \/ (tphase = "work" /\ CurStep = "end")

\* log_commit_local: logtb_complete_mvcc first.  complete_mvcc keeps T's
\* MVCCID in its lowest visible slot until LOG_COMMIT, so vacuum still
\* cannot remove what T deleted.
TCompleteMvcc ==
    /\ phase = "running" /\ TWorkDone
    /\ tmvcc' = TRUE
    /\ tphase' = IF tpost THEN "postpone" ELSE "ready"
    /\ last' = "T: log_commit_local runs logtb_complete_mvcc"
    /\ UNCHANGED <<fixed, data, tstep, trel, tcommit, vvars, ipc, log, phase, checks>>

\* log_tran_do_postpone -> log_append_commit_postpone flushes
\* LOG_COMMIT_WITH_POSTPONE: T is a winner from here.
TCommitWithPostpone ==
    /\ phase = "running" /\ tphase = "postpone"
    /\ tcommit' = TRUE
    /\ tphase' = "ready"
    /\ last' = "T: logs a postpone, so LOG_COMMIT_WITH_POSTPONE is written and flushed"
    /\ UNCHANGED <<fixed, data, tstep, trel, tmvcc, vvars, ipc, log, phase, checks>>

\* spage_free_saved_spaces (log_manager.c:5278 today; after LOG_COMMIT with 776).
TFreeSaved ==
    /\ phase = "running"
    /\ IF Fix776 THEN tphase = "logged" ELSE tphase = "ready"
    /\ saved' = [p \in Pages |-> 0]
    /\ tphase' = IF Fix776 THEN "committed" ELSE "freed"
    /\ last' = "T: spage_free_saved_spaces releases T's saved bytes"
               \o (IF tcommit THEN "" ELSE " before T has a commit record")
    /\ UNCHANGED <<fixed, slot, loc, delid, hot, free, tstep, trel, tcommit, tmvcc, vvars,
                   ipc, log, phase, checks>>

\* log_append_commit_log, then log_change_tran_as_completed flushes it.
TCommitRecord ==
    /\ phase = "running"
    /\ IF Fix776 THEN tphase = "ready" ELSE tphase = "freed"
    /\ tcommit' = TRUE
    /\ tphase' = IF Fix776 THEN "logged" ELSE "committed"
    /\ last' = "T: appends LOG_COMMIT and flushes it"
    /\ UNCHANGED <<fixed, data, tstep, trel, tmvcc, vvars, ipc, log, phase, checks>>

\* Rollback (design 6 Rollback): log_abort_local, TRAN_UNACTIVE_ABORTED.
TAbortStart ==
    /\ TWork /\ trel = "none" /\ Undoable({"T"}) # {}
    /\ tphase' = "aborting"
    /\ last' = "T: rolls back (log_abort_local)"
    /\ UNCHANGED <<fixed, data, tstep, trel, tcommit, tmvcc, vvars, ipc, log, phase, checks>>

\* Statement rollback (design 6): log_abort_partial runs log_sysop_abort,
\* which sets TRAN_UNACTIVE_ABORTED around log_rollback.  T then commits.
TStmtRollbackStart ==
    /\ TWork /\ trel = "none" /\ Undoable({"T"}) # {}
    /\ tphase' = "stmtrb"
    /\ last' = "T: the statement fails; log_abort_partial rolls it back"
    /\ UNCHANGED <<fixed, data, tstep, trel, tcommit, tmvcc, vvars, ipc, log, phase, checks>>

TUndo ==
    /\ phase = "running" /\ tphase \in {"aborting", "stmtrb"}
    /\ Undoable({"T"}) # {}
    /\ LET i == LastUndoable({"T"})
       IN  /\ log[i].page \notin vlatch
           /\ UndoRec(i)
           /\ last' = "T: rollback " \o UndoWord(log[i]) \o FailWord(i)
    /\ UNCHANGED <<fixed, tvars, vvars, ipc>>

TUndoDone ==
    /\ phase = "running" /\ tphase \in {"aborting", "stmtrb"}
    /\ Undoable({"T"}) = {}
    /\ saved' = IF tphase = "aborting" THEN [p \in Pages |-> 0] ELSE saved
    /\ tmvcc' = IF tphase = "aborting" THEN TRUE ELSE tmvcc
    /\ tphase' = IF tphase = "aborting" THEN "aborted" ELSE "rbdone"
    /\ last' = IF tphase = "aborting"
               THEN "T: log_abort_local frees the saved bytes and ends the rollback"
               ELSE "T: the statement rollback ends; T goes on to commit"
    /\ UNCHANGED <<fixed, slot, loc, delid, hot, free, tstep, trel, tcommit, vvars, ipc,
                   log, phase, checks>>

---------------------------------------------------------------------------
(* Store vacuum (design 6 Vacuum, query/vacuum.c:2374-2480).  w is a dead  *)
(* store record with a committed DELID.  The store is a FILE_HEAP, so      *)
(* helper->reusable is false and a vacuumed home slot is REC_MARKDELETED.  *)

VRun == phase = "running"

VacuumFixPages ==
    /\ VRun /\ vpc = "fix"
    /\ vlatch' = IF vkind = "REC_RELOCATION" THEN {"s1", "s2"} ELSE {"s1"}
    /\ vpc' = IF vkind = "REC_HOME" THEN "vacuum_home" ELSE "sysop_start"
    /\ last' = "vacuum: fixes s1" \o (IF vkind = "REC_RELOCATION" THEN " and the forward page s2" ELSE "")
               \o " to remove w (" \o vkind \o ")"
    /\ UNCHANGED <<fixed, data, tvars, sysop, vrm, ipc, log, phase, checks>>

VacuumSysopStart ==
    /\ VRun /\ vpc = "sysop_start"
    /\ sysop' = "open" /\ vpc' = "vacuum_home"
    /\ last' = "vacuum: log_sysop_start"
    /\ UNCHANGED <<fixed, data, tvars, vlatch, vrm, ipc, log, phase, checks>>

\* spage_vacuum_slot (home_page, ..., reusable = false); REC_HOME goes to the
\* redo-only bulk RVVAC_HEAP_PAGE_VACUUM, the others log RVVAC_HEAP_RECORD_VACUUM.
VacuumHomeSlot ==
    /\ VRun /\ vpc = "vacuum_home"
    /\ slot' = [slot EXCEPT !["wh"] = Marked]
    /\ free' = [free EXCEPT !["s1"] = @ + (IF vkind = "REC_HOME" THEN VS ELSE 0)]
    /\ log' = IF vkind = "REC_HOME" THEN log ELSE Append(log, LR("vacuum", "vac", "s1", "wh", 0, "wfwd"))
    /\ vpc' = CASE vkind = "REC_HOME" -> "return"
                [] vkind = "REC_RELOCATION" -> "vacuum_fwd"
                [] vkind = "REC_BIGONE" -> "ovf_delete"
    /\ last' = IF vkind = "REC_HOME"
               THEN "vacuum: w's home slot becomes REC_MARKDELETED (bulk, redo only)"
               ELSE "vacuum: w's home slot becomes REC_MARKDELETED (RVVAC_HEAP_RECORD_VACUUM)"
    /\ UNCHANGED <<fixed, loc, delid, hot, saved, tvars, sysop, vlatch, vrm, ipc, phase, checks>>

\* REC_RELOCATION: spage_vacuum_slot (forward_page, ..., true) makes the
\* REC_NEWHOME slot REC_DELETED_WILL_REUSE (vacuum.c:2428), its log
\* (:2436), and pgbuf_set_dirty (forward_page, FREE) (:2439) before
\* log_sysop_commit (:2442).  Fix775 keeps the page until after the commit.
VacuumForwardSlot ==
    /\ VRun /\ vpc = "vacuum_fwd"
    /\ slot' = [slot EXCEPT !["wf"] = Reuse]
    /\ free' = [free EXCEPT !["s2"] = @ + VS]
    /\ log' = Append(log, LR("vacuum", "vac", "s2", "wf", VS, "w"))
    /\ vlatch' = IF Fix775 THEN vlatch ELSE vlatch \ {"s2"}
    /\ vpc' = "commit"
    /\ last' = "vacuum: w's REC_NEWHOME slot on s2 becomes REC_DELETED_WILL_REUSE (RVVAC_HEAP_RECORD_VACUUM)"
               \o (IF Fix775 THEN "" ELSE "; the forward page is released before log_sysop_commit")
    /\ UNCHANGED <<fixed, loc, delid, hot, saved, tvars, sysop, vrm, ipc, phase, checks>>

OvfDelete ==
    /\ VRun /\ vpc = "ovf_delete"
    /\ vpc' = "commit"
    /\ last' = "vacuum: heap_ovf_delete succeeds"
    /\ UNCHANGED <<fixed, data, tvars, sysop, vlatch, vrm, ipc, log, phase, checks>>

OvfDeleteFails ==
    /\ VRun /\ vpc = "ovf_delete"
    /\ sysop' = "aborting" /\ vpc' = "abort"
    /\ last' = "vacuum: heap_ovf_delete fails; log_sysop_abort"
    /\ UNCHANGED <<fixed, data, tvars, vlatch, vrm, ipc, log, phase, checks>>

VacuumSysopCommit ==
    /\ VRun /\ vpc = "commit"
    /\ sysop' = "committed"
    /\ vlatch' = vlatch \ {"s2"}
    /\ vpc' = "return"
    /\ last' = "vacuum: log_sysop_commit appends LOG_SYSOP_END"
               \o (IF "s2" \in vlatch THEN ", then releases the forward page" ELSE "")
    /\ UNCHANGED <<fixed, data, tvars, vrm, ipc, log, phase, checks>>

VacuumAbortUndo ==
    /\ VRun /\ vpc = "abort" /\ Undoable({"vacuum"}) # {}
    /\ LET i == LastUndoable({"vacuum"})
       IN  /\ UndoRec(i)
           /\ last' = "vacuum: log_sysop_abort " \o UndoWord(log[i]) \o FailWord(i)
    /\ UNCHANGED <<fixed, tvars, vvars, ipc>>

VacuumAbortDone ==
    /\ VRun /\ vpc = "abort" /\ Undoable({"vacuum"}) = {}
    /\ sysop' = "aborted" /\ vpc' = "return"
    /\ last' = "vacuum: the sysop abort ends"
    /\ UNCHANGED <<fixed, data, tvars, vlatch, vrm, ipc, log, phase, checks>>

VacuumReturn ==
    /\ VRun /\ vpc = "return"
    /\ vlatch' = {} /\ vpc' = "done"
    /\ last' = "vacuum: vacuum_heap_page_log_and_reset releases s1"
    /\ UNCHANGED <<fixed, data, tvars, sysop, vrm, ipc, log, phase, checks>>

\* Vacuum of v by its own DELID (I-5): bulk REC_HOME removal, redo only.
\* It needs DELID older than the oldest visible MVCCID; complete_mvcc keeps
\* T in its lowest visible slot until LOG_COMMIT (mvcc_table.cpp:492-506).
VacuumRemoveV ==
    /\ VRun /\ ~vrm /\ "s1" \notin vlatch
    /\ slot["v"] = Rec("v") /\ delid["v"]
    /\ tcommit \/ (VacuumBeforeCommitRecord /\ tmvcc)
    /\ slot' = [slot EXCEPT !["v"] = Marked]
    /\ free' = [free EXCEPT !["s1"] = @ + VS]
    /\ vrm' = TRUE
    /\ last' = "vacuum: removes v by its DELID (bulk REC_HOME, redo only); v's slot becomes REC_MARKDELETED"
               \o (IF tcommit THEN "" ELSE " although T has no commit record")
    /\ UNCHANGED <<fixed, loc, delid, hot, saved, tvars, vpc, sysop, vlatch, ipc, log,
                   phase, checks>>

---------------------------------------------------------------------------
(* Other transactions: heap_insert_logical of one record (another row's   *)
(* store record or hot record), then commit.  spage_find_free_slot hands   *)
(* out only REC_DELETED_WILL_REUSE slots or new ones.                      *)

InsertRow(i, p, s, n) ==
    /\ phase = "running" /\ ipc[i] = "idle"
    /\ p \notin vlatch /\ Fits(p, n) /\ CanTake(p, s)
    /\ slot' = Put(s, Rec(i))
    /\ loc' = [loc EXCEPT ![i] = Where(p, s)]
    /\ free' = [free EXCEPT ![p] = @ - n]
    /\ log' = Append(log, LR(i, "ins", p, s, n, i))
    /\ ipc' = [ipc EXCEPT ![i] = "inserted"]
    /\ last' = "INSERT " \o ToString(i) \o ": puts a record of " \o ToString(n) \o " unit(s) into "
               \o SlotWord(s) \o " on " \o PageName(p)
    /\ UNCHANGED <<fixed, delid, hot, saved, tvars, vvars, phase, checks>>

InsertCommit(i) ==
    /\ phase = "running" /\ ipc[i] = "inserted"
    /\ ipc' = [ipc EXCEPT ![i] = "committed"]
    /\ last' = "INSERT " \o ToString(i) \o ": commits; the log is flushed through its commit record"
    /\ UNCHANGED <<fixed, data, tvars, vvars, log, phase, checks>>

---------------------------------------------------------------------------
(* Crash and restart (design 6 Crash recovery).  Every log record is      *)
(* durable when written (a shorter durable prefix is an earlier crash).    *)
(* log_recovery_undo undoes the losers and the open vacuum sysop in       *)
(* reverse LSA order; saved space is memory and is gone.                   *)

Losers == (IF sysop \in {"open", "aborting"} THEN {"vacuum"} ELSE {})
          \cup (IF tcommit THEN {} ELSE {"T"})
          \cup {i \in Inserters : ipc[i] # "committed"}

Crash ==
    /\ phase = "running" /\ Undoable(Losers) # {}
    /\ phase' = "recovering"
    /\ vlatch' = {}
    /\ saved' = [p \in Pages |-> 0]
    /\ last' = "the server crashes"
    /\ UNCHANGED <<fixed, slot, loc, delid, hot, free, tvars, vpc, sysop, vrm, ipc, log, checks>>

RecoveryUndo ==
    /\ phase = "recovering" /\ Undoable(Losers) # {}
    /\ LET i == LastUndoable(Losers)
       IN  /\ UndoRec(i)
           /\ last' = "restart undo of " \o Who(log[i].txn) \o ": " \o UndoWord(log[i]) \o FailWord(i)
    /\ UNCHANGED <<fixed, tvars, vvars, ipc>>

RecoveryDone ==
    /\ phase = "recovering" /\ Undoable(Losers) = {}
    /\ phase' = "recovered"
    /\ last' = "restart recovery ends"
    /\ UNCHANGED <<fixed, data, tvars, vvars, ipc, log, checks>>

Quiet ==
    \/ phase = "recovered"
    \/ /\ phase = "running"
       /\ tphase \in {"committed", "aborted"}
       /\ vpc = "done"
       /\ \A i \in Inserters : ipc[i] \in {"idle", "committed"}

Done == (Quiet \/ phase = "failed") /\ UNCHANGED vars

Next ==
    \/ \E p \in {"s1", "s2", "news"}, s \in SlotIds \cup {"other"} : TStoreInsert(p, s)
    \/ TStampInPlace
    \/ \E p \in {"s2", "news"}, s \in SlotIds \cup {"other"} : TStampNewhome(p, s)
    \/ TStampModifyHome \/ \E p \in {"hp", "newhp"} : THotInsert(p)
    \/ THotUpdate \/ THotDelete
    \/ TCompleteMvcc \/ TCommitWithPostpone \/ TFreeSaved \/ TCommitRecord
    \/ TAbortStart \/ TStmtRollbackStart \/ TUndo \/ TUndoDone
    \/ VacuumFixPages \/ VacuumSysopStart \/ VacuumHomeSlot \/ VacuumForwardSlot
    \/ OvfDelete \/ OvfDeleteFails \/ VacuumSysopCommit \/ VacuumAbortUndo
    \/ VacuumAbortDone \/ VacuumReturn \/ VacuumRemoveV
    \/ \E i \in Inserters, p \in Pages, s \in SlotIds \cup {"other"}, n \in InsertSizes :
          InsertRow(i, p, s, n)
    \/ \E i \in Inserters : InsertCommit(i)
    \/ Crash \/ RecoveryUndo \/ RecoveryDone
    \/ Done

Spec == Init /\ [][Next]_vars

---------------------------------------------------------------------------
(* Properties.                                                             *)

UndoFindsEmptySlot == brokenSlot = {}
UndoFindsRoom == brokenRoom = {}

\* A record body is intact where it was put: a fresh slot is never written
\* by an undo; a slot of interest must still hold that record.
Intact(x) == CASE x = "v" -> slot["v"] = Rec("v")
               [] loc[x] = "none" -> FALSE
               [] loc[x] \in SlotIds -> slot[loc[x]] = Rec(x)
               [] OTHER -> TRUE
\* Quiesced vacuum removes every store record whose DELID writer committed.
Live(x) == Intact(x) /\ ~(x \in {"v", "vreloc"} /\ delid[x] /\ tcommit)
\* The store value the row's current committed version names.
Named == IF hot.ex /\ ~hot.del /\ hot.names \in {"v", "nv"} THEN hot.names ELSE "none"
RowValues == {"v", "vreloc", "nv"}

AtomicRow ==
    Quiet =>
        /\ Named # "none" => Live(Named)
        /\ \A x \in RowValues \ {Named} : ~Live(x)
        /\ \A i \in Inserters : (ipc[i] = "committed") = Intact(i)
=============================================================================
