--------------------------- MODULE OosDropDecision ---------------------------
(***************************************************************************)
(* Decision 2: from what information vacuum decides that the old chain A  *)
(* of an UPDATE is dead.                                                  *)
(*                                                                        *)
(* T1 updates the row from chain A (version v0) to chain B (version v1).  *)
(* T1 may roll the UPDATE back with a statement or savepoint rollback and *)
(* still commit, may commit, or may roll back.  The log is a sequence of  *)
(* records; a prefix of it is durable, and any WAL flush can extend that  *)
(* prefix.  At most one crash happens; recovery keeps the durable prefix. *)
(* After T1 ends, vacuum processes the block once.                        *)
(*                                                                        *)
(* Notify                                                                 *)
(*   "undo_image"     the code: delete A when the block has T1's UPDATE   *)
(*                    undo image (the block requires only that T1 ended)  *)
(*   "commit_filter"  B: as the code, but only if T1's commit record is   *)
(*                    in the log                                          *)
(*   "commit_hook"    A (spec section 3 step 3): the commit hook appends  *)
(*                    RVOOS_NOTIFY_VACUUM before the commit record; vacuum*)
(*                    deletes A only for a notification. The in-memory    *)
(*                    drop list follows statement and savepoint rollback. *)
(*   "postpone"       A': the UPDATE appends a postpone record; the       *)
(*                    postpone runs after LOG_COMMIT_WITH_POSTPONE and    *)
(*                    appends the notification. A partial rollback cancels*)
(*                    the postpone.                                       *)
(*   "commit_clr"     B4: as B, and the UPDATE's undo record has no       *)
(*                    compensation record (CLR) in the log                *)
(*   "head_mark"      B3: the UPDATE writes T1's delete MVCCID into the   *)
(*                    head chunk of A with an undoable log record; every  *)
(*                    rollback undoes it. Vacuum reads the head when it   *)
(*                    processes the block and deletes A if the mark is    *)
(*                    there.                                              *)
(***************************************************************************)
EXTENDS Naturals, Sequences

CONSTANT Notify

ASSUME Notify \in {"undo_image", "commit_filter", "commit_hook", "postpone", "commit_clr", "head_mark"}

VARIABLES
    log,         \* log records of T1, in order
    durable,     \* length of the durable prefix of log
    t1,          \* "idle", "active", "hooked", "pp", "committed", "aborted"
    row,         \* "v0" (references chain A) or "v1" (references chain B)
    updLive,     \* the UPDATE has not been rolled back
    droplist,    \* A: chains the commit hook will report
    ppLive,      \* A': the postpone for chain A is not cancelled
    mark,        \* B3: the head chunk of A carries T1's delete MVCCID
    vac,         \* "wait" or "done"
    deleted,     \* vacuum deleted chain A
    disrupted,
    last

vars == <<log, durable, t1, row, updLive, droplist, ppLive, mark, vac, deleted,
          disrupted, last>>
view == <<log, durable, t1, row, updLive, droplist, ppLive, mark, vac, deleted,
          disrupted>>

InLog(r) == \E i \in 1..Len(log) : log[i] = r

Init ==
    /\ log = <<>>
    /\ durable = 0
    /\ t1 = "idle"
    /\ row = "v0"
    /\ updLive = FALSE
    /\ droplist = {}
    /\ ppLive = FALSE
    /\ mark = FALSE
    /\ vac = "wait"
    /\ deleted = FALSE
    /\ disrupted = FALSE
    /\ last = "initial state"

Update ==
    /\ t1 = "idle"
    /\ t1' = "active"
    /\ log' = CASE Notify = "postpone" -> log \o <<"upd", "postpone">>
                [] Notify = "head_mark" -> log \o <<"upd", "mark">>
                [] OTHER -> Append(log, "upd")
    /\ row' = "v1"
    /\ updLive' = TRUE
    /\ droplist' = IF Notify = "commit_hook" THEN {"A"} ELSE droplist
    /\ ppLive' = (Notify = "postpone")
    /\ mark' = (Notify = "head_mark")
    /\ last' = "T1: heap_update moves the row to chain B; the undo image keeps the stub of chain A"
               \o (IF Notify = "postpone" THEN "; a postpone record names chain A" ELSE "")
               \o (IF Notify = "head_mark" THEN "; the head of chain A gets T1's delete MVCCID (undoable)" ELSE "")
               \o (IF Notify = "commit_hook" THEN "; chain A joins the drop list" ELSE "")
    /\ UNCHANGED <<durable, vac, deleted, disrupted>>

PartialRollback ==
    /\ t1 = "active" /\ updLive
    /\ log' = Append(log, "clr")
    /\ row' = "v0"
    /\ updLive' = FALSE
    /\ droplist' = {}
    /\ ppLive' = FALSE
    /\ mark' = FALSE
    /\ last' = "T1: a statement or savepoint rollback undoes the UPDATE; the row references chain A again"
               \o (IF Notify = "head_mark" THEN " and the head mark is undone" ELSE "")
    /\ UNCHANGED <<durable, t1, vac, deleted, disrupted>>

Flush ==
    /\ durable < Len(log)
    /\ durable' = Len(log)
    /\ last' = "a WAL flush makes the log durable up to its end"
    /\ UNCHANGED <<log, t1, row, updLive, droplist, ppLive, mark, vac, deleted, disrupted>>

PlainCommit ==
    /\ Notify \in {"undo_image", "commit_filter", "commit_clr", "head_mark"} /\ t1 = "active"
    /\ log' = Append(log, "commit")
    /\ durable' = Len(log')
    /\ t1' = "committed"
    /\ last' = "T1 commits"
    /\ UNCHANGED <<row, updLive, droplist, ppLive, mark, vac, deleted, disrupted>>

CommitHook ==
    /\ Notify = "commit_hook" /\ t1 = "active"
    /\ log' = IF droplist # {} THEN Append(log, "notify") ELSE log
    /\ t1' = "hooked"
    /\ last' = IF droplist # {}
                 THEN "T1: the commit hook appends RVOOS_NOTIFY_VACUUM for chain A before logtb_complete_mvcc"
                 ELSE "T1: the commit hook has nothing to report"
    /\ UNCHANGED <<durable, row, updLive, droplist, ppLive, mark, vac, deleted, disrupted>>

CommitRecord ==
    /\ Notify = "commit_hook" /\ t1 = "hooked"
    /\ log' = Append(log, "commit")
    /\ durable' = Len(log')
    /\ t1' = "committed"
    /\ last' = "T1: the commit record is appended and flushed"
    /\ UNCHANGED <<row, updLive, droplist, ppLive, mark, vac, deleted, disrupted>>

CommitWithPostpone ==
    /\ Notify = "postpone" /\ t1 = "active"
    /\ log' = Append(log, "commit_pp")
    /\ durable' = Len(log')
    /\ t1' = "pp"
    /\ last' = "T1: LOG_COMMIT_WITH_POSTPONE is appended and flushed"
    /\ UNCHANGED <<row, updLive, droplist, ppLive, mark, vac, deleted, disrupted>>

RunPostpone ==
    /\ Notify = "postpone" /\ t1 = "pp"
    /\ log' = IF ppLive THEN log \o <<"notify", "commit">> ELSE Append(log, "commit")
    /\ durable' = Len(log')
    /\ t1' = "committed"
    /\ last' = IF ppLive
                 THEN "T1: the postpone runs and appends RVOOS_NOTIFY_VACUUM for chain A; then LOG_COMMIT"
                 ELSE "T1: the cancelled postpone does not run; LOG_COMMIT"
    /\ UNCHANGED <<row, updLive, droplist, ppLive, mark, vac, deleted, disrupted>>

\* After the commit hook the commit decision is taken; only a crash stops it.
Abort ==
    /\ t1 = "active"
    /\ log' = Append(log, "abort")
    /\ durable' = Len(log')
    /\ t1' = "aborted"
    /\ row' = "v0"
    /\ updLive' = FALSE
    /\ droplist' = {}
    /\ ppLive' = FALSE
    /\ mark' = FALSE
    /\ last' = "T1 rolls back; the row references chain A again"
    /\ UNCHANGED <<vac, deleted, disrupted>>

\* Restart recovery keeps the durable prefix.  A transaction with a durable
\* LOG_COMMIT_WITH_POSTPONE is finished: its postpones run again.  Any other
\* unfinished transaction is a loser and is undone.
Crash ==
    /\ ~disrupted /\ t1 \notin {"idle", "committed", "aborted"}
    /\ LET kept == SubSeq(log, 1, durable)
           has(r) == \E i \in 1..Len(kept) : kept[i] = r
           ppKept == has("postpone") /\ ~has("clr")
       IN IF has("commit_pp")
            THEN /\ log' = IF ppKept THEN kept \o <<"notify", "commit">> ELSE Append(kept, "commit")
                 /\ t1' = "committed"
                 /\ row' = IF has("clr") THEN "v0" ELSE "v1"
                 /\ updLive' = ~has("clr")
                 /\ last' = "crash; recovery finds LOG_COMMIT_WITH_POSTPONE and runs the postpones again"
            ELSE /\ log' = Append(kept, "abort")
                 /\ t1' = "aborted"
                 /\ row' = "v0"
                 /\ updLive' = FALSE
                 /\ last' = "crash; recovery undoes T1 as a loser and keeps the durable log prefix"
                            \o (IF \E i \in 1..Len(kept) : kept[i] = "notify"
                                  THEN " (RVOOS_NOTIFY_VACUUM is in it)" ELSE "")
    /\ durable' = Len(log')
    /\ droplist' = {}
    /\ ppLive' = FALSE
    /\ mark' = FALSE   \* T1 is a loser or has no mark: only a crash before T1's commit is possible
    /\ disrupted' = TRUE
    /\ UNCHANGED <<vac, deleted>>

Decide ==
    CASE Notify = "undo_image" -> InLog("upd")
      [] Notify = "commit_filter" -> InLog("upd") /\ InLog("commit")
      [] Notify = "commit_clr" -> InLog("upd") /\ InLog("commit") /\ ~InLog("clr")
      [] Notify = "head_mark" -> mark
      [] OTHER -> InLog("notify")

Vacuum ==
    /\ vac = "wait" /\ t1 \in {"committed", "aborted"}
    /\ vac' = "done"
    /\ deleted' = Decide
    /\ last' = IF Decide THEN "vacuum: deletes chain A" ELSE "vacuum: keeps chain A"
    /\ UNCHANGED <<log, durable, t1, row, updLive, droplist, ppLive, mark, disrupted>>

Finished ==
    /\ vac = "done"
    /\ UNCHANGED vars

Next ==
    \/ Update \/ PartialRollback \/ Flush
    \/ PlainCommit \/ CommitHook \/ CommitRecord \/ CommitWithPostpone \/ RunPostpone
    \/ Abort \/ Crash \/ Vacuum \/ Finished

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
\* Properties

\* CBRD-27237: vacuum never deletes the chain that the row references.
RowChainIntact == ~(deleted /\ row = "v0")

\* The chain that a committed UPDATE dropped is deleted.
DroppedChainReclaimed == (vac = "done" /\ t1 = "committed" /\ row = "v1") => deleted

\* Reasons for A'.  Whenever the notification is durable, the commit decision
\* is durable too, so recovery cannot turn T1 into a loser after vacuum may
\* have seen the notification.
NotifyDurableOnlyWithCommit ==
    (\E i \in 1..durable : log[i] = "notify") =>
        \E i \in 1..durable : log[i] \in {"commit", "commit_pp"}
\* A notification exists only for an UPDATE that was not rolled back.
NotifyOnlyForSurvivingUpdate == InLog("notify") => ~InLog("clr")

\* Reason for B3.  Every rollback undoes the mark before T1 ends, so once T1
\* has ended a remaining mark belongs to a committed UPDATE that survived.
MarkFinalWhenEnded ==
    (t1 \in {"committed", "aborted"} /\ mark) => (t1 = "committed" /\ updLive)
\* Why B fails.  A commit record alone does not mean that the row moved.
CommitMeansMoved ==
    (t1 \in {"committed", "aborted"} /\ InLog("upd") /\ InLog("commit")) => row = "v1"
\* Reason for B4.  A commit record with an uncompensated UPDATE undo record
\* means that the row moved to chain B.
UncompensatedCommitMeansMoved ==
    (t1 \in {"committed", "aborted"} /\ InLog("upd") /\ InLog("commit") /\ ~InLog("clr"))
        => row = "v1"

\* Witnesses (expected to fail): the situation that breaks B is reachable, and
\* B3 and B4 keep chain A in it.
WitnessRollbackThenCommit == ~(t1 = "committed" /\ InLog("clr") /\ vac = "done")

=============================================================================
