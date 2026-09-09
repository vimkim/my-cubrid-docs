# CUBRID project vocabulary

Canonical domain vocabulary for the design notes in this repository.

## Out-of-row overflow storage

**OOS chain identity**:
The identity of one particular stored out-of-row value, distinct from the storage address that may later be reused for another value. Matching identity does not establish permission to reclaim that value.
_Avoid_: Reclamation eligibility when referring only to identity matching

**OOS reclamation eligibility**:
The condition that an out-of-row value may be removed without invalidating a value still required by transaction visibility, rollback, or recovery. This is distinct from correctly identifying the value to remove.
_Avoid_: Identity safety when referring to permission to reclaim
