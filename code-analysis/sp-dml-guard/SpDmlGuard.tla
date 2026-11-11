---------------------------- MODULE SpDmlGuard ----------------------------
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS GuardMode, MetadataMode, LifetimeMode, Classifier, MaxDepth

Tables == {"t1", "t2", "t3"}
Stmt(kind, plan, refs, writes) ==
  [kind |-> kind, plan |-> plan, refs |-> refs, writes |-> writes]
Statements ==
  {Stmt("SELECT", "SELECT", {}, {}),
   Stmt("SELECT", "SELECT", {"t1"}, {}),
   Stmt("SELECT", "SELECT", {"t1", "t2"}, {}),
   Stmt("DML", "DML", {"t1"}, {"t1"}),
   Stmt("DML", "DML", {"t2"}, {"t2"}),
   Stmt("DML", "DML", {"t3"}, {"t3"}),
   Stmt("DML", "DML", {"t1", "t2"}, {"t1"}),
   Stmt("DML", "DML", {"t1", "t2"}, {"t1", "t2"}),
   Stmt("DML", "SELECT", {"t1"}, {"t1"}),
   Stmt("CALL", "CALL", {}, {})}

Metadata(s, cached) ==
  [kind |-> IF Classifier = "xasl" THEN s.plan ELSE s.kind,
   refs |-> IF MetadataMode = "cache-empty" /\ cached THEN {} ELSE s.refs,
   writes |-> IF Classifier = "xasl" /\ s.plan = "SELECT" THEN {} ELSE s.writes]

VARIABLES active, frames, prepared, selectSafe, overlapSafe, precise, event
vars == <<active, frames, prepared, selectSafe, overlapSafe, precise, event>>

NoSelectAncestor(stack) ==
  \A i \in 1..Len(stack): stack[i].kind # "SELECT"
NoOverlap(stack, writes) ==
  \A i \in 1..Len(stack):
    stack[i].kind # "DML" \/ stack[i].refs \cap writes = {}
Expected(stack, s) ==
  s.writes = {} \/ (NoSelectAncestor(stack) /\ NoOverlap(stack, s.writes))

CheckedFrames(stack) ==
  IF GuardMode = "top" /\ Len(stack) > 0
  THEN <<stack[Len(stack)]>> ELSE stack
Allowed(stack, m) ==
  LET scope == CheckedFrames(stack)
      selectOK == GuardMode = "no-select-check" \/ NoSelectAncestor(scope)
      overlapOK == GuardMode = "no-overlap-check" \/ NoOverlap(scope, m.writes)
  IN m.writes = {} \/ (GuardMode # "deny-all-writes" /\ selectOK /\ overlapOK)

Init ==
  /\ active = <<>>
  /\ frames = <<>>
  /\ prepared = [statement |-> Stmt("CALL", "CALL", {}, {}),
                   meta |-> Metadata(Stmt("CALL", "CALL", {}, {}), FALSE),
                   allowed |-> TRUE]
  /\ selectSafe = TRUE
  /\ overlapSafe = TRUE
  /\ precise = TRUE
  /\ event = "idle"

Prepare ==
  \E s \in Statements, cached \in BOOLEAN:
    /\ prepared' = [statement |-> s, meta |-> Metadata(s, cached),
                      allowed |-> Allowed(frames, Metadata(s, cached))]
    /\ event' = "prepare"
    /\ UNCHANGED <<active, frames, selectSafe, overlapSafe, precise>>

Execute ==
  /\ Len(active) < MaxDepth
  /\ LET s == prepared.statement
         permitted == IF LifetimeMode = "prepare-only"
                      THEN prepared.allowed ELSE Allowed(frames, prepared.meta)
     IN /\ active' = IF permitted THEN Append(active, s) ELSE active
        /\ frames' = IF permitted THEN Append(frames, prepared.meta) ELSE frames
        /\ selectSafe' = (selectSafe /\
             (~permitted \/ s.writes = {} \/ NoSelectAncestor(active)))
        /\ overlapSafe' = (overlapSafe /\
             (~permitted \/ s.writes = {} \/ NoOverlap(active, s.writes)))
        /\ precise' = (precise /\ (permitted = Expected(active, s)))
        /\ event' = IF permitted THEN "execute" ELSE "reject"
  /\ UNCHANGED prepared

Return ==
  /\ Len(active) > 0
  /\ active' = SubSeq(active, 1, Len(active) - 1)
  /\ frames' = SubSeq(frames, 1, Len(frames) - 1)
  /\ event' = "return"
  /\ UNCHANGED <<prepared, selectSafe, overlapSafe, precise>>

ErrorUnwind ==
  /\ Len(active) > 0
  /\ \E keep \in 0..(Len(active) - 1):
       /\ active' = SubSeq(active, 1, keep)
       /\ frames' = IF LifetimeMode = "leak-on-error" THEN frames
                     ELSE SubSeq(frames, 1, keep)
  /\ event' = "error"
  /\ UNCHANGED <<prepared, selectSafe, overlapSafe, precise>>

Done == /\ Len(active) = 0 /\ UNCHANGED vars
Next == Prepare \/ Execute \/ Return \/ ErrorUnwind \/ Done
Spec == Init /\ [][Next]_vars

TypeOK ==
  /\ active \in Seq(Statements)
  /\ Len(active) <= MaxDepth
  /\ selectSafe \in BOOLEAN /\ overlapSafe \in BOOLEAN /\ precise \in BOOLEAN
NoWritesUnderSelect == selectSafe
NoWritesToAncestorTables == overlapSafe
DecisionsMatchRules == precise
FramesFollowExecution == Len(frames) = Len(active)
=============================================================================
