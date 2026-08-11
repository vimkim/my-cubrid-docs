# CUBRID source audit revision packet

- Role: CUBRID Source Tracer — independent chapter 05/06/09 audit revision
- Topic: CUBRID lock과 lock manager — acquire/conversion/escalation, wait/deadlock/release, lifecycle/durability/observability
- Frozen scope digest: `711d1a0f5bfebdbe1b55b4299973efc353d90636e2f00fc807f51d031766a839`
- CUBRID root: `/home/vimkim/gh/cb/cubrid-analysis`
- Revision: `f30f1c26003e5aa8e93182648e06cad76fc77064`
- Evidence state: cited source files are `COMMIT`; report-run provenance labels the enclosing worktree `WORKTREE` (status digest `6f459c90a9e5391919b0f19ac04ffd081eab7905b9fde6cc27658f45f817bad1`)
- Packet timestamp (UTC): `2026-08-11T09:58:25Z`
- Companion append-only claim candidates: `research/packets/cubrid-added-claims.jsonl`, proposed IDs `CUBRID-C050`–`CUBRID-C075`
- Writer boundary: this packet is integration material. It does not modify the HTML book, canonical claim ledger, experiments, quizzes, report manifest, or CUBRID source.

## 0. Integration contract

The final writer should first verify that `CUBRID-C050`–`CUBRID-C075` are still unused, append the companion JSONL records without rewriting existing evidence, and then expose the relevant IDs through each target section's `data-claim-id` plus a visible `<span class="claim-id">…</span>`. Every substantive row and pseudocode branch below already carries its intended ID. [CUBRID-C050–CUBRID-C075]

The source-confirmed records describe code that exists at the pinned revision. `CUBRID-C065` and `CUBRID-C069` are deliberately `INFERRED`: the former derives asymptotic bounds from explicit list/pair loops, and the latter derives the volatile/durable ownership boundary from allocation/free and caller seams plus negative searches. They must not be relabeled as runtime measurements or absolute architecture proofs. [CUBRID-C065, CUBRID-C069]

`CUBRID-C068` proves a formatter discrepancy in source, not a user-visible defect. The chapter must retain the wording “source-level suspicion; runtime reproduction required.” [CUBRID-C068]

Companion-ledger proposed primary anchors (exactly matching `report_locations`):

| Chapter | Anchor | Claim IDs |
|---|---|---|
| 05 | `#acquire-state-machine` | CUBRID-C052 |
| 05 | `#acquire-transition-table` | CUBRID-C073 |
| 05 | `#conversion` | CUBRID-C053 |
| 05 | `#escalation` | CUBRID-C054, CUBRID-C061 |
| 05 | `#performance-05` | CUBRID-C065 |
| 06 | `#wait-deadlock-release` | CUBRID-C055 |
| 06 | `#grant-before-wakeup` | CUBRID-C056 |
| 06 | `#timeout-interrupt-daemon` | CUBRID-C057 |
| 06 | `#deadlock` | CUBRID-C058 |
| 06 | `#concurrency-protection` | CUBRID-C063 |
| 06 | `#same-transaction-wait-train` | CUBRID-C064 |
| 06 | `#deadlock-victim-cleanup` | CUBRID-C072 |
| 06 | `#fairness-starvation-boundary` | CUBRID-C074 |
| 06 | `#release-order` | CUBRID-C059 |
| 06 | `#release-policy` | CUBRID-C071 |
| 09 | `#lock-manager-lifecycle` | CUBRID-C050, CUBRID-C051 |
| 09 | `#storage-durability-recovery` | CUBRID-C060, CUBRID-C069 |
| 09 | `#transaction-end-order` | CUBRID-C059 |
| 09 | `#error-pressure-matrix` | CUBRID-C070 |
| 09 | `#configuration-thresholds` | CUBRID-C057, CUBRID-C061 |
| 09 | `#memory-complexity` | CUBRID-C062, CUBRID-C065 |
| 09 | `#observability-measurement` | CUBRID-C066, CUBRID-C067, CUBRID-C075 |
| 09 | `#diagnostic-boundaries` | CUBRID-C068 |

## 1. Chapter 05 revision material — acquire, conversion, escalation

### 1.1 Reader outcome and concrete scenario

After this section, a reader should be able to distinguish four outcomes of one request: immediate grant on a new resource, immediate grant behind compatible current/queued modes, blocked new acquisition, and blocked conversion that retains its old granted mode. This is the minimum model needed to explain why “I already hold a lock” does not imply that an upgrade is either immediate or equivalent to a fresh queue entry. [CUBRID-C052, CUBRID-C053]

Use one running scenario: transaction T1 holds `S` on a resource and asks for a stronger mode while T2 holds an incompatible mode. T1 remains a holder under its old `granted_mode`, publishes its target in `blocked_mode`, and waits from the Upgrader Positioning Rule position; it does not discard the protection already obtained. [CUBRID-C053]

### 1.2 Interface-to-state-machine call flow

```text
SQL/storage caller
  -> lock_object(thread, oid, class_oid, requested_mode, cond_flag)
       -> reject invalid object/class input; NULL_LOCK is a no-op
       -> determine root/class/instance resource and required class intention
       -> acquire/check the class intention where the object hierarchy requires it
       -> lock_internal_perform_lock_object(...)
            -> FIND_RESOURCE
            -> NEW_REQUESTER or EXISTING_HOLDER
            -> optionally SUSPENDED
            -> POST_GRANT
            -> DONE
```

The wrapper-to-generic boundary and the root/class/instance plus class-intention decisions are evidenced by `lock_object`; the generic state set and its implementation are evidenced separately by `LK_PERFORM_STATE` and `lock_internal_perform_lock_object`. Do not compress these into “hash lookup then sleep,” because input validation, implicit class coverage, re-request, conversion, and failure-without-enqueue are distinct branches. [CUBRID-C052, CUBRID-C073]

The diagram is the ordinary `SERVER_MODE` worker path. In non-server mode `lock_object` uses the standalone X-lock flag and returns granted without this resource state machine; a `TT_LOADDB` worker instead validates that its session-side bulk-update coverage already exists and does not enter ordinary instance locking. These are front-door exceptions, not alternative branches inside `LK_PERFORM_STATE`. [CUBRID-C052]

The MVCCID transaction resource used by self-lock is not a separate scheduler: `lock_transaction_mvccid` enters this same generic state machine. Consequently, the acquire/conversion/wait mechanics explained here also apply to transaction-resource X/S conflicts, even though the key is an MVCCID rather than an object OID. [CUBRID-C066]

### 1.3 Legal state graph

```text
                       resource absent / new entry
                   +--------------------------------> NEW_REQUESTER
                   |                                      |
                   |                     grant / enqueue / fail
                   |                                      v
FIND_RESOURCE -----+                                  POST_GRANT
                   |                                      |
                   | holder found                         v
                   +--------------------------------> EXISTING_HOLDER
                                                          |
                                      re-request / convert / enqueue / fail
                                                          |
                                                          +----> SUSPENDED
                                                                    |
                                                    grant or terminal failure
                                                                    v
                                                              POST_GRANT / DONE

POST_GRANT --------------------------------------------------------> DONE
DONE or an unknown state re-entered by the loop -------------------> assert + error
```

This graph is an abstraction of the legal `LK_PERFORM_STATE` cases. It is deliberately not a transaction lifecycle graph and not a thread scheduler-state graph. [CUBRID-C073]

### 1.4 Legal and illegal transition table

| From | Guard/event | Action | Next/outcome | Failure semantics | Evidence |
|---|---|---|---|---|---|
| `FIND_RESOURCE` | resource absent and allocation succeeds | create/initialize resource entry under the object table path | `NEW_REQUESTER` | none | CUBRID-C052, CUBRID-C073 |
| `FIND_RESOURCE` | resource/entry allocation cannot be satisfied | set lock-allocation error; do not publish a waiter | `DONE`, failure | request-local failure; no half-enqueued waiter | CUBRID-C052, CUBRID-C070 |
| `FIND_RESOURCE` | resource exists, no holder owned by this transaction | retain resource mutex and classify as new requester | `NEW_REQUESTER` | none | CUBRID-C052, CUBRID-C073 |
| `FIND_RESOURCE` | current transaction already has holder entry | classify as re-request/conversion | `EXISTING_HOLDER` | none | CUBRID-C053, CUBRID-C073 |
| `NEW_REQUESTER` | request compatible with holder aggregate and preceding waiter aggregate | link entry as granted holder and transaction-held entry | `POST_GRANT` | none | CUBRID-C052, CUBRID-C063 |
| `NEW_REQUESTER` | conflict and zero-wait/conditional behavior applies | leave no waiter behind | `DONE`, not granted | expected conflict result, not a suspended request | CUBRID-C052 |
| `NEW_REQUESTER` | conflict, waiting permitted, allocation succeeds | enqueue waiter, publish thread wait metadata | `SUSPENDED` | detector/timeout/interrupt may later terminate | CUBRID-C052, CUBRID-C055 |
| `EXISTING_HOLDER` | requested mode is equal to or weaker than held protection | increment/reuse ownership count | `POST_GRANT` | none | CUBRID-C053 |
| `EXISTING_HOLDER` | conversion result is compatible with other-holder aggregate | replace granted mode with conversion result | `POST_GRANT` | none | CUBRID-C053 |
| `EXISTING_HOLDER` | conversion conflicts and zero-wait applies | keep old grant; do not publish blocked conversion | `DONE`, not granted | protection already held remains intact | CUBRID-C053 |
| `EXISTING_HOLDER` | conversion conflicts and waiting is permitted | preserve `granted_mode`, set `blocked_mode`, position as UPR blocked holder | `SUSPENDED` | later grant or cleanup after non-grant resume | CUBRID-C053, CUBRID-C055, CUBRID-C074 |
| `SUSPENDED` | release path grants request before wake | entry has already become holder/converted holder | `POST_GRANT` | wake is not itself the grant; publication precedes signal | CUBRID-C056, CUBRID-C063 |
| `SUSPENDED` | timeout, interrupt, or deadlock-victim resume | remove the request's wait/blocked state | `DONE`, failure | cleanup is branch-specific | CUBRID-C057, CUBRID-C072 |
| `POST_GRANT` | conversion/escalation cleanup and counters complete | finish return bookkeeping | `DONE`, granted | none | CUBRID-C054, CUBRID-C066, CUBRID-C073 |
| `DONE` or unknown | loop erroneously re-enters terminal/default case | assertion/error path | illegal | programming invariant failure, not a user wait result | CUBRID-C073 |

### 1.5 Branch-preserving acquire/conversion pseudocode

```text
function lock_object(resource_key, class_key, requested_mode, cond):
    if resource_key/class_key is invalid:
        return ERROR                         // CUBRID-C052
    if requested_mode == NULL_LOCK:
        return GRANTED                       // CUBRID-C052
    derive resource type and class intention // CUBRID-C052
    if class intention is required:
        acquire/check it first               // CUBRID-C052
    return generic_acquire(resource_key, requested_mode, cond)

function generic_acquire(key, requested_mode, cond):
    state = FIND_RESOURCE                    // CUBRID-C073
    while state != DONE:
        switch state:
        case FIND_RESOURCE:
            lock resource mutex or create resource
            if allocation failed:
                result = ERROR_ALLOC
                state = DONE                 // CUBRID-C052, CUBRID-C070
            else if my holder exists:
                state = EXISTING_HOLDER       // CUBRID-C053, CUBRID-C073
            else:
                state = NEW_REQUESTER         // CUBRID-C052, CUBRID-C073

        case NEW_REQUESTER:
            if compatible(requested_mode, holders_aggregate)
               and compatible(requested_mode, preceding_waiters_aggregate):
                link as holder
                link into transaction hold list
                state = POST_GRANT            // CUBRID-C052, CUBRID-C063
            else if zero_wait(cond):
                leave no waiter behind
                result = NOT_GRANTED
                state = DONE                  // CUBRID-C052
            else if another thread in my transaction already waits here:
                join its wait train
                if lead already woke:
                    unlock resource mutex
                    state = FIND_RESOURCE     // CUBRID-C064
                else:
                    state = SUSPENDED         // CUBRID-C064
            else if waiter-entry allocation failed:
                result = ERROR_ALLOC
                state = DONE                  // CUBRID-C052, CUBRID-C070
            else:
                enqueue waiter
                state = SUSPENDED             // CUBRID-C052, CUBRID-C055

        case EXISTING_HOLDER:
            if requested_mode <= protection already held:
                increment/reuse hold count
                state = POST_GRANT            // CUBRID-C053
            else:
                converted = lock_Conv[held][requested]
                if compatible(converted, other_holders_aggregate):
                    granted_mode = converted
                    state = POST_GRANT        // CUBRID-C053
                else if zero_wait(cond):
                    retain old granted_mode
                    result = NOT_GRANTED
                    state = DONE              // CUBRID-C053
                else:
                    retain old granted_mode
                    blocked_mode = converted
                    position by UPR
                    state = SUSPENDED         // CUBRID-C053, CUBRID-C074

        case SUSPENDED:
            publish lockwait/start/timeout/WFG metadata
            assert no forbidden permanent page fix
            release resource mutex and suspend
            if resume_state means granted:
                state = POST_GRANT            // CUBRID-C055, CUBRID-C056
            else:
                remove my wait/blocked state
                result = timeout/interrupt/deadlock error
                state = DONE                  // CUBRID-C057, CUBRID-C072

        case POST_GRANT:
            update generic acquire/convert/wait metrics if watched
            state = DONE                      // CUBRID-C066, CUBRID-C075

        case DONE or default:
            assert and return internal error  // CUBRID-C073
```

The aggregate check against earlier waiters is a fairness mechanism: it prevents a compatible-looking newcomer from automatically overtaking queued incompatible work. It is not a proof that every conversion finishes under adversarial arrival or scheduling. [CUBRID-C074]

### 1.6 Conversion invariants

| Invariant | Why it matters | Evidence |
|---|---|---|
| A weaker/equal re-request reuses the holder and increases its ownership count. | Recursive or repeated ownership is not a second independent waiter. | CUBRID-C053 |
| An immediately compatible upgrade changes `granted_mode` while the resource is protected. | Other requesters observe the stronger aggregate consistently. | CUBRID-C053, CUBRID-C063 |
| A blocked upgrade keeps the old grant and records the target as `blocked_mode`. | The transaction does not expose an unprotected gap while it waits. | CUBRID-C053 |
| UPR placement gives the blocked upgrade a defined ordering position. | Queue behavior is constrained, but starvation freedom remains unproven. | CUBRID-C074 |
| A non-grant wake removes the request's blocked/wait state before return. | Timeout/deadlock does not leave a ghost dependency. | CUBRID-C072 |

### 1.7 Escalation: separate state machine, not ordinary conversion shorthand

Escalation begins from per-class instance-lock pressure, but its policy guards precede the class conversion: `BU_LOCK`, missing class entry, an escalation already running, and the relevant granule count below threshold all skip the attempt. In a class hierarchy, a non-root superclass entry supplies that count; otherwise the class entry does. After the threshold guard passes, a false rollback policy maps class `IS -> S` and `IX/SIX -> X` and requests that class conversion with `LK_FORCE_ZERO_WAIT`; a true rollback policy takes the aborted path before conversion is attempted. [CUBRID-C054]

The exact pinned defaults are `lock_escalation = 100000` with minimum `5`, and `rollback_on_lock_escalation = false`. Despite the parameter name, the pinned true branch marks an abort immediately after escalation becomes necessary and before class conversion is attempted; it is not a reaction to a completed zero-wait conversion failure. [CUBRID-C061, CUBRID-C054]

```text
function maybe_escalate(class_entry):
    if class_entry.granted_mode == BU_LOCK:
        return SKIP                         // CUBRID-C054
    if class_entry is NULL:
        return SKIP                         // CUBRID-C054
    if escalation_already_in_progress:
        return SKIP                         // CUBRID-C054
    count_entry = non-root superclass entry if present, else class_entry
    if count_entry.granule_count < lock_escalation:
        return SKIP                         // CUBRID-C054, CUBRID-C061

    if rollback_on_lock_escalation:
        set rollback-on-escalation error and abort reason
        return NOT_GRANTED_DUE_ABORTED      // CUBRID-C054, CUBRID-C061

    mark escalation in progress
    if class_mode in {NULL, S, X, SCH_M}:
        clear escalation-in-progress marker
        return GRANTED                      // CUBRID-C054

    target = S if class_mode == IS else X if class_mode in {IX, SIX}
    release transaction hold mutex before generic acquisition
    result = generic_acquire(class_resource, target, LK_FORCE_ZERO_WAIT)
                                                // CUBRID-C054, CUBRID-C063
    clear escalation-in-progress marker

    if result == GRANTED:
        remove instance locks covered by the class grant
        release the original class lock once to preserve its prior hold count
        return GRANTED                      // CUBRID-C054
    retain pre-existing instance locks and return the conversion failure
                                           // CUBRID-C054
```

The hold mutex is deliberately released before calling generic acquisition, avoiding a recursive/nested acquisition through a path that itself must update transaction-held lists. The general protected-state order remains resource mutex before hold mutex when both are needed. [CUBRID-C054, CUBRID-C063]

### 1.8 Fast, miss, retry, and failure matrix

| Path class | Representative branch | Observable result | Persistent state after return | Evidence |
|---|---|---|---|---|
| Fast | empty resource | grant and holder linkage | one granted entry | CUBRID-C052 |
| Fast | compatible holders and preceding waiters | immediate grant | one granted entry; aggregates updated | CUBRID-C052, CUBRID-C063 |
| Fast | equal/weaker re-request | ownership count increases | original holder remains | CUBRID-C053 |
| Fast conversion | upgrade compatible with other holders | stronger `granted_mode` | converted holder | CUBRID-C053 |
| Miss/no-wait | conflict with conditional/force-zero request | `NOT_GRANTED` | no new waiter; old holder retained for conversion | CUBRID-C052, CUBRID-C053 |
| Slow | incompatible new request | enqueue and suspend | waiter plus thread wait metadata | CUBRID-C055 |
| Slow conversion | incompatible upgrade | old grant plus blocked target, then suspend | blocked holder | CUBRID-C053, CUBRID-C055 |
| Retry | same-transaction lead waiter already woke during join | return to resource lookup | no duplicate waiter | CUBRID-C064 |
| Failure | LK_ENTRY allocation shortage | lock allocation error | no half-linked request | CUBRID-C052, CUBRID-C070 |
| Policy abort | threshold reached while rollback-on-escalation is true | aborted result before conversion attempt | existing instance locks remain for transaction abort cleanup | CUBRID-C054, CUBRID-C061 |
| Policy conversion miss | force-zero conversion fails while rollback-on-escalation is false | return conversion failure | covered instance locks are not removed | CUBRID-C054, CUBRID-C061 |

### 1.9 Performance boundary for chapter 05

The object hash supplies a direct bucket lookup, but work inside one hot resource is list based. With `H` holders and `W` waiters, holder lookup, aggregate checks, conversion placement, and release/grant scans can require worst-case `O(H + W)` work after the hash step. This is a code-structure inference, not measured latency. [CUBRID-C065]

Escalation trades resource-entry cardinality for a wider conflict domain. Self-lock also reduces per-row lock cardinality in its intended insert path, but it does so by using one MVCCID transaction resource rather than converting instance locks into one class lock; its generic acquire/wait counts are mixed into the general object-lock counters. [CUBRID-C054, CUBRID-C066]

## 2. Chapter 06 revision material — wait, deadlock, release

### 2.1 The critical publication rule

A thread enters the slow path only after its waiter or blocked conversion is linked under the resource mutex. It then locks its thread entry, releases the resource mutex, and `lock_suspend` publishes the lock pointer, start timestamp, timeout, and WFG marker under that thread mutex before the suspend-and-unlock operation. The source also asserts that an ordinary lock wait must not begin while the thread retains a permanently fixed page, subject to the narrow safe-lock exception. [CUBRID-C055]

Wakeup is not a promise to “try the lock again.” Release/grant code first changes resource ownership and aggregate modes, then clears/publishes the thread wait result under the thread-entry mutex, and only then signals the condition. Thus the waking thread consumes a state transition already committed in memory. [CUBRID-C056, CUBRID-C063]

### 2.2 Wait/release call flow

```text
lock_internal_perform_lock_object
  -> link waiter or set blocked_mode while holding LK_RES.res_mutex
  -> lock the waiter thread entry
  -> release LK_RES.res_mutex
  -> lock_suspend (caller still holds thread-entry mutex)
       -> publish thread lockwait/start/timeout/WFG state
       -> increment suspended-waiter accounting
       -> suspend-and-unlock thread entry on its condition

concurrent unlock
  -> lock_internal_perform_unlock_object (holds LK_RES.res_mutex)
       -> remove/downgrade releasing holder
       -> lock_grant_blocked_holder and/or lock_grant_blocked_waiter
            -> move blocked request to granted holder state
            -> update resource and transaction hold state
            -> lock_resume
                 -> lock thread-entry mutex
                 -> clear lockwait, publish resume state
                 -> condition signal

woken requester
  -> lock_suspend returns a specific resume state
  -> POST_GRANT, or remove its failed wait state and return error
```

The nested synchronization order visible in these paths is `resource mutex -> transaction hold mutex` for holder-list linkage and `resource mutex -> thread-entry mutex` for grant/resume publication. This is the code-supported order; the chapter should not invent a single global order covering unrelated page latches or every transaction subsystem mutex. [CUBRID-C063]

### 2.3 Branch-preserving wait pseudocode

```text
function suspend_lock_request(resource, request, timeout):
    // caller has already published waiter/blocked_mode under resource mutex
                                                // CUBRID-C055, CUBRID-C063
    lock thread-entry mutex while resource mutex is still held
    unlock resource mutex                       // CUBRID-C055, CUBRID-C063

    // lock_suspend starts with thread-entry mutex held
    assert thread has no forbidden permanent page fix
                                                // CUBRID-C055
    thread.lockwait = request
    thread.lockwait_start = now
    thread.lockwait_timeout = timeout
    thread.wfg_waiting_state = waiting
    atomic_increment(number_of_suspended_lock_waiters)
                                                // CUBRID-C055, CUBRID-C057
    resume_state = thread_suspend_and_unlock_entry_on_condition()

    atomic_decrement(number_of_suspended_lock_waiters)
    if resume_state == LOCK_RESUMED:
        return GRANTED                         // CUBRID-C056
    if resume_state == LOCK_RESUMED_ABORTED_FIRST:
        return DEADLOCK_ABORT_OWNER            // CUBRID-C072
    if resume_state == LOCK_RESUMED_ABORTED_OTHER:
        return DEADLOCK_ABORT_FOLLOWER_ERROR   // CUBRID-C072
    if resume_state is timeout or interrupt:
        return matching non-grant result       // CUBRID-C057
```

The `number_of_suspended_lock_waiters` update is atomic and is used as a detector gate, but atomics do not protect holder/waiter list contents. Those lists remain under the resource mutex. [CUBRID-C055, CUBRID-C057, CUBRID-C063]

### 2.4 Branch-preserving release/grant pseudocode

```text
function unlock_one(resource, releasing_entry):
    lock resource.res_mutex
    update/remove releasing holder and aggregate modes
                                                // CUBRID-C056, CUBRID-C063

    for each blocked holder that is now compatible:
        granted_mode = conversion target
        clear blocked_mode
        update resource aggregate
        lock transaction hold mutex if hold-list update is needed
        publish converted ownership
        unlock transaction hold mutex
        resume_after_grant(thread)              // CUBRID-C056, CUBRID-C063

    for waiter from queue head:
        if waiter is incompatible with current aggregate:
            stop; do not bypass it              // CUBRID-C056, CUBRID-C074
        unlink waiter
        link as holder and into transaction hold list
        update aggregates
        resume_after_grant(thread)              // CUBRID-C056, CUBRID-C063

    unlock resource.res_mutex

function resume_after_grant(thread):
    lock thread-entry mutex
    thread.lockwait = NULL
    thread.resume_state = LOCK_RESUMED
    signal thread condition
    unlock thread-entry mutex                   // CUBRID-C056, CUBRID-C063
```

The release-side ordering creates the relevant happens-before relationship at the design level: resource grant is published under `res_mutex`; resume state is published and signaled under the waiter thread's mutex; the waiter returns from suspension and reads the categorized result. This statement is limited to these protected fields and synchronization calls, not a formal proof over all engine memory. [CUBRID-C056, CUBRID-C063]

### 2.5 Protected state and synchronization map

| Protected state | Synchronizer | Acquisition/order evidence | Boundary and failure if violated | Evidence |
|---|---|---|---|---|
| `LK_RES` holders, waiters, blocked modes, aggregate modes | `LK_RES.res_mutex` | held across acquire classification and release/grant scan | unsynchronized readers could see holder/aggregate disagreement | CUBRID-C063 |
| per-transaction instance/class/root hold lists and counts | `LK_TRAN_LOCK.hold_mutex` | when nested, resource mutex precedes hold mutex | reverse nesting is not evidenced and should not be taught | CUBRID-C063 |
| wait pointer, resume state, condition notification in a thread entry | thread-entry mutex | grant path enters it while resource state is already protected/published | signaling before ownership publication could expose a false grant | CUBRID-C056, CUBRID-C063 |
| number of suspended lock waiters | atomic increment/decrement | changed around the suspension interval | it is a gate/count, not a replacement for list mutexes | CUBRID-C055, CUBRID-C057 |
| page-fix/latch condition at wait boundary | assertion/precondition | permanent fixed page is forbidden before general lock suspend | blocking while pinning a page risks a cross-subsystem wait cycle; exact global latch order is outside this evidence | CUBRID-C055 |
| wait-for edge snapshot | detector structures plus timestamps/sequence validation | edges built from protected resource relationships and revalidated | a stale edge must not be treated as a current cycle | CUBRID-C058 |

### 2.6 Race boundaries and defenses

**Same transaction, same resource.** If another thread in the same transaction is already waiting, the newcomer attaches to a wait train instead of enqueueing a duplicate `LK_ENTRY`. If the lead thread has already awakened during the join race, the follower drops the resource mutex and restarts from `FIND_RESOURCE`; a lead wake also wakes the rest of the train. [CUBRID-C064]

**Grant versus timeout/interrupt.** Resource ownership is decided under the resource mutex and the wake result is categorized under the thread mutex. The requester branches on that result and removes its own wait state on non-grant. The claim here is the implemented serialization/cleanup protocol, not that wall-clock timeout has absolute priority over a concurrent grant. [CUBRID-C056, CUBRID-C057, CUBRID-C072]

**WFG snapshot versus live state.** Detector construction includes blocked-holder, holder-to-waiter, and waiter-ordering incompatibilities, then validates wait timestamps and edge sequence/current transaction activity before selecting a victim. This is the stale-edge defense; it does not make WFG construction free of cost. [CUBRID-C058, CUBRID-C065]

**Multiple waiters in one victim transaction.** The first woken victim thread receives `LOCK_RESUMED_ABORTED_FIRST` and owns rollback responsibility; remaining waiting threads receive `LOCK_RESUMED_ABORTED_OTHER` and follow the error/cleanup path. This prevents several workers from independently driving the same transaction rollback. [CUBRID-C072]

### 2.7 Detector, timeout, and deadlock pseudocode

```text
every 100 ms in deadlock detector daemon:
    scan finite waits for timeout and interrupt
                                              // CUBRID-C057
    if server restart is not complete:
        continue                              // CUBRID-C057
    if atomic_suspended_waiters < 2:
        continue                              // CUBRID-C057
    if deadlock_detection_interval has not elapsed:
        continue                              // CUBRID-C057

    build WFG edges from:
        incompatible blocked-holder pairs
        holder -> waiter incompatibilities
        incompatible waiter ordering
                                              // CUBRID-C058
    if edge capacity is exhausted:
        grow 200 -> reusable 1000 -> at most num_trans^2
        if allocation fails or cap is reached:
            report error for this detection attempt
                                              // CUBRID-C070

    discard stale edges using wait timestamp/sequence validation
                                              // CUBRID-C058
    for each validated cycle:
        choose an active-holder victim by priority,
        then logged-work proxy, timeout possibility, and transaction age
                                              // CUBRID-C058
        wake first victim thread as abort owner
        wake other victim threads as followers
                                              // CUBRID-C072

    if repeated cycles find no victim and all request handlers are suspended:
        force one waiter to timeout            // CUBRID-C058
```

Timeout and deadlock are therefore different transitions. Finite timeout/interrupt scanning may end one wait without a cycle; WFG detection ends a cycle by choosing a transaction victim. The default lock timeout is infinite, whereas the detector interval defaults to one second but its daemon checks eligibility on a 100 ms loop. [CUBRID-C057, CUBRID-C061]

### 2.8 Fairness, starvation, and cost boundary

New requesters must be compatible with preceding waiter aggregate; queue grant walks from the head and stops at the first incompatible request; blocked upgrades are placed by UPR. These mechanisms constrain overtaking. The pinned source does not prove starvation freedom, so the chapter must list adversarial conversion starvation as an open experiment rather than state a guarantee. [CUBRID-C074]

For one resource with `H` holders and `W` waiters, edge generation can examine holder/holder, holder/waiter, and waiter/waiter pairs, producing an inferred `O(H^2 + H*W + W^2)` local cost. Hot-resource fan-in can therefore affect detector work even when the object hash lookup itself is cheap. [CUBRID-C065]

### 2.9 Release lifetime and isolation policy

An ordinary early-release call does not freely drop every lock. Without force, non-shared write locks remain; `SERIALIZABLE` and `REPEATABLE_READ` retain shared locks, while `READ_COMMITTED` can release shared instance locks but preserves upper-level intention coverage. At transaction end, the lock manager releases instance, class, root, and non-2PL lists in its defined order. [CUBRID-C071]

For the traced logged local-update commit branch with `retain_lock == false`, MVCC completion occurs before the commit/unlock log record and lock release; the commit flush/completed transition follows unlock. Abort performs rollback first, then MVCC completion and `lock_unlock_all`. Read-only/unlogged, retained-lock, and non-local 2PC commit branches must be described separately. [CUBRID-C059]

## 3. Chapter 09 revision material — lifecycle, failure, durability, observability

### 3.1 Lock-manager lifecycle state diagram

```text
UNINITIALIZED
   |
   | transaction table + MVCC table ready
   v
INITIALIZING
   |  tran hold table -> object hash/freelist -> WFG -> detector daemon
   |  error from transaction/object/WFG initialization:
   |      lock_finalize(partial) -> FAILED/UNINITIALIZED
   v
RUNNING
   |\
   | \-- logged local commit, retain_lock=false:
   |       MVCC complete -> commit/unlock log -> unlock -> flush/complete
   |  \-- local abort: rollback -> MVCC complete -> unlock all
   |  \-- 2PC prepare: materialize insert X locks -> prepare record + flush
   |
   | normal shutdown
   v
FINALIZING
   | detector daemon -> WFG -> object structures -> transaction hold table
   v
UNINITIALIZED

PROCESS CRASH from RUNNING/PREPARED
   -> ordinary LK_RES/LK_ENTRY/wait queues vanish
   -> restart reconstructs database/log state outside ordinary lock-table replay
   -> prepared 2PC exception: read serialized object-lock list and reacquire X locks
```

The diagram combines five separately evidenced seams: initialization and partial unwind, reverse-order finalization, commit/abort ordering, volatile ordinary lock state, and prepared-transaction lock recovery. It must not be presented as one C enum implemented in `lock_manager.c`; it is a source-derived subsystem lifecycle model. [CUBRID-C050, CUBRID-C051, CUBRID-C059, CUBRID-C060, CUBRID-C069]

### 3.2 Lifecycle, legal transitions, guards, actions, and failures

| State/transition | Guard | Action and ownership | Failure/illegal edge | Evidence |
|---|---|---|---|---|
| `UNINITIALIZED -> INITIALIZING` | transaction and MVCC tables have been prepared in server startup | begin per-transaction lock table allocation | calling this table an independent persistent store is invalid | CUBRID-C050, CUBRID-C069 |
| `INITIALIZING -> RUNNING` | hold table, object structures, WFG initialize, then detector daemon is created | publish usable in-memory coordination structures | an error returned by the table/object/WFG initialization calls finalization to unwind already-built parts; no daemon-creation error return is claimed | CUBRID-C050, CUBRID-C070 |
| `RUNNING -> local COMMIT` | logged local update, `is_local_tran`, and `retain_lock == false` | complete MVCC; append commit/unlock log; unlock; then flush/change completed state | read-only/unlogged, retained-lock, and non-local 2PC branches are outside this row | CUBRID-C059 |
| `RUNNING -> local ABORT` | abort chosen and rollback executed | finish rollback, complete MVCC, release all locks | claiming lock release precedes rollback is illegal for this traced path | CUBRID-C059 |
| `RUNNING -> PREPARED` | global transaction prepares | materialize lockless insert OIDs as object X; serialize exclusive object-lock list to prepare log; flush | MVCCID self-lock is not the prepare record's lock-list format | CUBRID-C060 |
| `PREPARED -> crash/restart lock recovery` | recovery reads prepared record | reacquire each serialized object lock with infinite wait | replaying ordinary waiter queues or self-lock entries is not evidenced | CUBRID-C060, CUBRID-C069 |
| `RUNNING -> FINALIZING` | transaction-table teardown enters normal shutdown | destroy detector first, then WFG, object structures, transaction hold table | application quiescing before this call is outside the traced lock-manager responsibility | CUBRID-C051 |
| `FINALIZING -> UNINITIALIZED` | reverse cleanup finishes | no ordinary runtime holder/waiter table remains | retaining queue state for restart is not evidenced | CUBRID-C051, CUBRID-C069 |
| `RUNNING -> PROCESS CRASH` | process failure | volatile lock structures disappear with process memory | durable row/log recovery semantics are not owned by ordinary `LK_RES` transitions | CUBRID-C069 |

### 3.3 Startup and shutdown pseudocode

```text
function server_transaction_table_startup(config):
    initialize transaction table
    initialize system transaction and MVCC table
    result = lock_initialize_with_config(config)
                                               // CUBRID-C050
    if result != NO_ERROR:
        lock_finalize(partial = true)
        unwind already initialized transaction structures
        return ERROR                            // CUBRID-C050, CUBRID-C070
    continue with later server structures

function lock_initialize_with_config(config):
    allocate/init per-transaction hold table    // CUBRID-C050
    allocate/init object resource hash/freelist // CUBRID-C050, CUBRID-C062
    allocate/init WFG nodes/edges/victims       // CUBRID-C050, CUBRID-C062
    create detector daemon                      // CUBRID-C050
    on an error returned by an initialization step:
        lock_finalize(partial = true)           // CUBRID-C050, CUBRID-C070

function normal_shutdown():
    destroy detector daemon first
    release WFG storage
    release object hash/freelists
    release transaction hold table              // CUBRID-C051
```

Shutdown safety here is limited to the internal cleanup order. Whether connection handling has already stopped new user work is a higher-level boot/shutdown question and must remain outside this claim. [CUBRID-C051]

### 3.4 Commit, abort, and restart ordering

```text
function logged_local_update_commit_with_lock_release():
    complete MVCC transaction state
    append commit/unlock log record
    unlock transaction locks
    flush commit log and mark transaction completed
                                               // CUBRID-C059

function local_abort():
    rollback transaction changes
    complete MVCC transaction state
    unlock all transaction locks               // CUBRID-C059

function prepare_2pc():
    for each lockless-insert OID:
        materialize object X lock
    gather exclusive object-lock list
    append LOG_2PC_PREPARE containing that list
    flush prepare record                        // CUBRID-C060

function restart_prepared_transaction(record):
    read serialized object-lock list
    for each recorded object lock:
        reacquire with infinite wait            // CUBRID-C060
```

The ordinary self-lock's transaction-resource X is not serialized by this prepare-lock list. The exception is a conversion of lockless insert OIDs to ordinary object X locks before prepare; therefore “prepared 2PC persists self-lock” would be an overclaim. [CUBRID-C060]

### 3.5 Storage, WAL, checkpoint, disk, and corruption applicability table

| Concern | Ordinary `LK_RES`/`LK_ENTRY` state | Owner/seam that is evidenced | Chapter wording | Evidence |
|---|---|---|---|---|
| On-disk lock-table layout | N/A | allocation/finalization create and destroy volatile process structures | “No ordinary on-disk layout is evidenced.” | CUBRID-C069 (`INFERRED`) |
| Dirty-page tracking | N/A | buffer/storage subsystem, not ordinary lock holder/waiter transition | “Do not attribute page dirtiness to lock grant.” | CUBRID-C069 (`INFERRED`) |
| Checkpoint participation | N/A for ordinary queue replay | restart recovery owns durable state reconstruction | “Wait queues are not checkpoint-replayed by this path.” | CUBRID-C069 (`INFERRED`) |
| Commit WAL order | Applicable at caller seam, not inside ordinary acquire/release | on the logged local `retain_lock=false` branch, `log_commit_local` appends commit/unlock before unlock, then flushes/completes | “This traced WAL order surrounds lock release; other commit branches differ.” | CUBRID-C059 |
| Abort recovery | Applicable at caller seam | rollback, MVCC completion, then `lock_unlock_all` | “Abort cleanup orders data undo before lock release.” | CUBRID-C059 |
| Full disk / ENOSPC | No direct ordinary lock-manager transition evidenced | log/storage caller can fail independently | “Not applicable to in-memory lock state; do not imply immunity of commit/prepare.” | CUBRID-C069 (`INFERRED`) |
| Page corruption | No direct ordinary lock-manager transition evidenced | page/recovery subsystems outside traced module | “N/A to holder/waiter state machine.” | CUBRID-C069 (`INFERRED`) |
| Crash persistence of ordinary holders/waiters/self-lock | N/A | process memory is recreated | “Ordinary entries are volatile.” | CUBRID-C069 (`INFERRED`) |
| Prepared 2PC locks | Explicit exception | prepare log serializes exclusive object-lock list; recovery reacquires | “A restricted durable-lock seam exists.” | CUBRID-C060 |

The N/A rows are bounded inferences, not proof that storage failures can never affect a transaction holding locks. The evidence says that ordinary lock-manager structures do not themselves implement page dirtiness/checkpoint/disk transitions; commit and 2PC callers can still fail in their logging/storage work. [CUBRID-C059, CUBRID-C060, CUBRID-C069]

The supporting negative search in pinned `src/transaction/lock_manager.c` found no match for `log_append|logpb_flush|checkpoint|fileio_(write|synchronize)|pgbuf_set_dirty|pgbuf_flush`, and no match for `ER_.*(DISK|FULL|CORRUPT)|out of space|ENOSPC|fsync|fdatasync`. Negative search narrows the claim; it is not a substitute for the positive caller-seam evidence in `log_manager.c` and `log_2pc.c`. [CUBRID-C069]

### 3.6 Error and resource-pressure transition table

| Failure | Detection site | State left behind | Required reader conclusion | Evidence |
|---|---|---|---|---|
| Startup allocation failure | per-transaction/object/WFG initialization | partial structures are finalized/unwound | server must not expose a half-initialized lock manager | CUBRID-C050, CUBRID-C070 |
| Acquire entry shortage | new requester/entry allocation | no half-enqueued waiter | request returns lock allocation error | CUBRID-C052, CUBRID-C070 |
| Zero-wait conflict | acquire or conversion | no new waiter; conversion keeps old grant | conflict result is distinct from timeout | CUBRID-C052, CUBRID-C053 |
| Timeout or interrupt | daemon scans finite waits on 100 ms loop | request cleanup follows non-grant resume | no WFG cycle is required | CUBRID-C057 |
| Deadlock victim | validated WFG cycle and victim policy | first victim thread owns abort; followers return error/cleanup | transaction-wide abort differs from one-request timeout | CUBRID-C058, CUBRID-C072 |
| WFG edge growth pressure | edge table grows 200 -> 1000 -> at most `T^2` | current detection attempt returns error on allocation failure/cap | detector memory is bounded by configured transaction capacity | CUBRID-C070 |
| Escalation policy abort | threshold passes while rollback policy is true | class conversion is not attempted; aborted result is returned | do not describe this as a reaction to conversion conflict | CUBRID-C054, CUBRID-C061 |
| Escalation conversion conflict | force-zero class conversion on the false-policy path | existing instance locks remain unless successful post-grant cleanup is reached | conversion failure is returned without the true-policy branch | CUBRID-C054, CUBRID-C061 |
| Shutdown | transaction-table teardown | daemon is stopped before graph/hash/hold storage is freed | daemon-first order prevents it using freed detector state | CUBRID-C051 |

### 3.7 Exact configuration and thresholds

| Parameter/mechanism | Pinned default | Minimum/cap | Behavioral use | Evidence |
|---|---:|---:|---|---|
| `lock_escalation` | `100000` | minimum `5` | class granule threshold; also feeds hash sizing | CUBRID-C061, CUBRID-C062 |
| `rollback_on_lock_escalation` | `false` | boolean | when true and escalation is needed, returns aborted before class conversion | CUBRID-C054, CUBRID-C061 |
| `lock_timeout` | infinite (`-1`) | session-changeable parameter | finite values are scanned for expiry; default itself does not expire | CUBRID-C057, CUBRID-C061 |
| `deadlock_detection_interval_in_secs` | `1.0 s` | minimum `0.1 s` | gates WFG detector invocation | CUBRID-C057, CUBRID-C061 |
| detector looper cadence | `100 ms` | implementation cadence, not the parameter | timeout/interrupt checking and eligibility checks | CUBRID-C057 |
| detector suspended-waiter threshold | at least `2` | fixed logical gate | detector invocation is skipped below this count | CUBRID-C057 |
| local `LK_ENTRY` pool | `10` per transaction | initial local supply | avoids shared allocation for a small held-lock set; not a hard maximum | CUBRID-C062 |
| WFG active edge start | `200` | reuse storage `1000`; maximum `T^2` | detector storage grows under dependency pressure | CUBRID-C062, CUBRID-C070 |
| victim slots | `300` | configured fixed allocation in default config | detector victim output capacity | CUBRID-C062 |
| hidden `stats_on` | `false` | boolean | true creates a permanent performance watcher at initialization | CUBRID-C075 |

The 100 ms looper and the 1.0 s deadlock interval are not contradictory: the daemon wakes/checks frequently, while the interval and other guards decide whether to build the WFG. [CUBRID-C057]

### 3.8 Memory sizing and complexity model

Let `T = configured number of transactions` and `E = lock_escalation`. The object-resource hash bucket count is:

```text
B = max(10,000, min(T * E * 3 / 1000, 2^23))
```

The source comment estimates eight bytes per bucket pointer, so the bucket array alone is approximately `8B` bytes and caps near 64 MiB at `2^23` buckets. This excludes `LK_RES`, `LK_ENTRY`, mutex internals, allocator metadata, transaction arrays, WFG storage, and daemon/thread objects. [CUBRID-C062]

An inventory formula suitable for a capacity worksheet is:

```text
lock_manager_memory ≈ 8B
                    + T * 10 * sizeof(LK_ENTRY)          # initial local entry pools
                    + R_alloc * sizeof(LK_RES)
                    + E_alloc * sizeof(LK_ENTRY)
                    + T * sizeof(WFG_NODE)
                    + WFG_edge_capacity * sizeof(WFG_EDGE)
                    + 300 * sizeof(victim slot)
                    + mutex/allocator/auxiliary overhead
```

Only the components and counts are source-confirmed; the sum is an accounting model. `xlock_dump`'s printed `size` covers only allocated `LK_ENTRY` plus `LK_RES`, so it must not be labeled total lock-manager resident memory. [CUBRID-C062, CUBRID-C067]

| Operation | Inferred bound after hash lookup | Premise | Excluded costs | Evidence |
|---|---:|---|---|---|
| holder lookup/acquire compatibility/conversion | `O(H + W)` worst case | linked holder/waiter scans | hash collisions, cache misses, allocation, scheduling | CUBRID-C065 (`INFERRED`) |
| release and compatible grant scan | `O(H + W)` worst case | recompute/walk holder and queue state | wake scheduler cost | CUBRID-C065 (`INFERRED`) |
| WFG pair construction for one hot resource | `O(H^2 + H*W + W^2)` | explicit pair relationships among holders/waiters | global graph cycle-analysis constant factors | CUBRID-C065 (`INFERRED`) |

These are worst-case structural bounds, not a performance benchmark. A runtime profile may show cache, scheduler, or allocator costs dominate, in which case tuning priorities must follow measurement. [CUBRID-C065]

### 3.9 Concrete observability surfaces

The generic performance counters include object acquisitions, conversions, re-requests, waits, and wait time. MVCCID self-lock passes through the same generic state machine, so its activity is mixed into these counters; no dedicated self-lock counter was found in the pinned path. [CUBRID-C066]

`xlock_dump` provides the lock escalation/deadlock settings, transaction status/timeout, counts of locked resources and allocated resource/entry objects, its limited `LK_ENTRY + LK_RES` size estimate, and resource holder/waiter aggregates. A transaction resource is rendered with its MVCCID, which makes self-lock holders and waiters inspectable in a point-in-time dump. [CUBRID-C067]

Performance increments are gated by performance-monitor initialization and watcher count. Because hidden `stats_on` defaults to false and enabling it establishes a permanent watcher, an experiment that attaches a watcher only after the workload may miss the target interval. [CUBRID-C075]

### 3.10 Reproducible measurement workflow

1. Record revision, server parameters (`lock_escalation`, rollback policy, lock timeout, detector interval, and `stats_on`), `T`, workload concurrency, SQL isolation, and whether the request is object or MVCCID resource. [CUBRID-C061, CUBRID-C062, CUBRID-C075]
2. Start the performance watcher before the workload, or document that permanent `stats_on` tracking was enabled before startup. Capture a baseline counter snapshot. [CUBRID-C075]
3. Start a bounded two-session or multi-session workload with explicit barriers so holder, waiter, and release times are known. Do not use elapsed time alone to infer resource identity. [CUBRID-C055, CUBRID-C056]
4. While blocked, collect `xlock_dump` and identify resource type/key, aggregate mode, holders, and waiters. For self-lock, require the transaction-resource/MVCCID rendering rather than infer it from SQL timing. [CUBRID-C067]
5. Capture counter deltas for acquired/converted/re-requested/waited/wait-time values. State explicitly that self-lock contributions are mixed with other object-lock traffic. [CUBRID-C066, CUBRID-C075]
6. Release/commit/abort the holder and record whether the waiter was granted, timed out, interrupted, or chosen as a deadlock victim. Match the outcome to the distinct cleanup path. [CUBRID-C056, CUBRID-C057, CUBRID-C072]
7. Repeat enough iterations to report a distribution, not one latency. Separate source-confirmed branch identity from runtime-measured frequency and duration. [CUBRID-C065, CUBRID-C066]
8. For memory, report `xlock_dump`'s entry/resource estimate and separately compute/configure the bucket/WFG/transaction components; never call the dump number total RSS. [CUBRID-C062, CUBRID-C067]

The dump is a diagnostic snapshot and can perturb timing through traversal/output. Avoid collecting it in a tight loop when the quantity being measured is short wait latency; use one bounded snapshot for identity and perf-counter/time series for frequency. This observer-effect warning follows from the dump's traversal/output scope and should be presented as measurement discipline, not a quantified overhead claim. [CUBRID-C067]

### 3.11 Diagnostic boundary and suspected formatter issue

Both lock dump and event-log formatting render `LOCK_RESOURCE_TRANSACTION` with an MVCCID. In contrast, the simple-timeout branch passes the transaction resource union's OID fields into its error message arguments. This is a source-level discrepancy worth a targeted runtime reproduction, but the pinned source alone does not prove which values a user actually sees. [CUBRID-C068]

Suggested safe reproduction: create a finite-timeout S waiter on a held MVCCID self-lock, capture the timeout error, event log, and `xlock_dump`, and compare the rendered resource key. Run against a disposable database with bounded session cleanup; classify the result as a runtime claim only after preserving stdout/stderr/log artifacts and run manifest. [CUBRID-C068]

### 3.12 Tuning decision table

| Symptom | First evidence to collect | Candidate control | Trade-off/limit | Evidence |
|---|---|---|---|---|
| many row/object entries, little class contention | dump allocated entry/resource counts and per-class shape | lower `lock_escalation` cautiously | broader class conflicts; minimum 5; default 100000 | CUBRID-C054, CUBRID-C061, CUBRID-C067 |
| escalation abort/error | rollback policy, whether conversion was attempted, conflict holder, zero-wait result | `rollback_on_lock_escalation` plus threshold/workload shape | true aborts before conversion; false may attempt and fail zero-wait conversion | CUBRID-C054, CUBRID-C061 |
| long lock waits without deadlock victims | timeout setting, detector interval, dump queue | finite `lock_timeout` or workload/transaction redesign | timeout cancels a request; it is not cycle resolution | CUBRID-C057, CUBRID-C067 |
| detector CPU/memory on a hot key | `H`, `W`, WFG edge growth errors, interval | reduce fan-in/transaction duration; consider interval only with evidence | pair cost can be quadratic; slower detection prolongs cycles | CUBRID-C058, CUBRID-C065, CUBRID-C070 |
| counters stay zero despite observed blocking | watcher start time and `stats_on` | attach watcher before workload or enable documented tracking setup | permanent tracking may add ongoing monitoring cost; cost unquantified here | CUBRID-C075 |
| self-lock wait not distinguishable in aggregate stats | MVCCID resource block in dump plus controlled workload | isolate workload; correlate dump and counter deltas | no dedicated self-lock counter in pinned path | CUBRID-C066, CUBRID-C067 |
| apparent starvation during upgrades | queue order, arrivals, UPR blocked holders | reduce competing conversions/transaction scope; run adversarial experiment | ordering constrains overtaking but proves no starvation bound | CUBRID-C074 |

### 3.13 Explicit unknowns and safe experiment gaps

| Unknown | Why source is insufficient | Minimum useful experiment/evidence | Related claims |
|---|---|---|---|
| Self-lock memory and throughput benefit | generic counters mix resource types; formulas do not reveal workload frequency | same insert workload with resource-specific dump samples, counters, CPU/RSS, and controlled comparison | CUBRID-C062, CUBRID-C066, CUBRID-C067 |
| Hot-MVCCID fan-in cost | structural list/pair bounds are not latency measurements | barrier-driven N-way waiter sweep; report latency distribution and detector work | CUBRID-C065 |
| Starvation freedom under adversarial conversion | queue/UPR rules constrain order but do not prove liveness | bounded repeating newcomers plus one upgrader; measure maximum wait and completion | CUBRID-C074 |
| Transaction-resource timeout rendering | source formatters disagree | finite-timeout self-lock runtime capture with dump/event/error correlation | CUBRID-C068 |
| Full lock-manager memory | dump excludes buckets/WFG/mutex/allocator overhead | measure process RSS delta and inventory all configured components | CUBRID-C062, CUBRID-C067 |
| WFG allocation-failure runtime behavior | source branch exists but inducing allocator failure safely is environment-specific | fault-injection build or tiny controlled harness; never exhaust a shared host | CUBRID-C070 |
| Shutdown with active waiters | lock manager cleanup order does not prove higher-level quiescing | trace boot/shutdown callers and run disposable active-waiter shutdown test | CUBRID-C051 |
| Checkpoint/full-disk effect on transactions holding locks | ordinary lock structures do not own these transitions, but callers can fail | separate WAL/storage fault experiment; do not rewrite it as a lock-table failure | CUBRID-C059, CUBRID-C060, CUBRID-C069 |

## 4. Claim-to-source verifier index

The companion JSONL is the authority for exact source refs and file hashes. This compact index helps the final writer spot-check the most important additions without weakening the ledger contract.

| Claim | Kind/confidence | Primary symbols and exact lines | Proposed anchor |
|---|---|---|---|
| CUBRID-C050 | source / SOURCE-CONFIRMED | `logtb_define_trantable_log_latch:405-512`; `lock_initialize_with_config:5889-5943`; `lock_initialize_tran_lock_table:1107-1149` | 09 `#lock-manager-lifecycle` |
| CUBRID-C051 | source / SOURCE-CONFIRMED | `lock_finalize:5955-6174`; `logtb_undefine_trantable:573-602` | 09 `#lock-manager-lifecycle` |
| CUBRID-C052 | source / SOURCE-CONFIRMED | `lock_object:6234-6430`; `lock_internal_perform_lock_object:3478-3865` | 05 `#acquire-state-machine` |
| CUBRID-C053 | source / SOURCE-CONFIRMED | `lock_internal_perform_lock_object:3478-4163`; `lock_Conv:142-240` | 05 `#conversion` |
| CUBRID-C054 | source / SOURCE-CONFIRMED | `lock_check_escalate:3059-3106`; `lock_escalate_if_needed:3127-3217`; `lock_remove_all_inst_locks:4111-4148` | 05 `#escalation` |
| CUBRID-C055 | source / SOURCE-CONFIRMED | `lock_suspend:2304-2477`; `lock_internal_perform_lock_object:3478-4109` | 06 `#wait-publication` |
| CUBRID-C056 | source / SOURCE-CONFIRMED | `lock_resume:2491-2520`; `lock_grant_blocked_holder:2665-2769`; `lock_grant_blocked_waiter:2782-2893`; unlock `4197-4397` | 06 `#release-wakeup` |
| CUBRID-C057 | source / SOURCE-CONFIRMED | daemon `6039-6119`; timeout scan `7950-8005`; interval `8129-8151`; parameters `1300-1332` | 06 `#deadlock`, 09 `#config-thresholds` |
| CUBRID-C058 | source / SOURCE-CONFIRMED | WFG edge `4931-5052`; victim selection `5067-5474`; detector `8203-8539` | 06 `#deadlock` |
| CUBRID-C059 | source / SOURCE-CONFIRMED | `log_commit_local:5189-5260`; `log_abort_local:5307-5363`; `logtb_complete_mvcc:4394-4459` | 09 `#storage-durability-recovery` |
| CUBRID-C060 | source / SOURCE-CONFIRMED | 2PC materialize `4252-4285`; prepare `1314-1483`; read `1509-1582`; reacquire `8724-8780` | 09 `#storage-durability-recovery` |
| CUBRID-C061 | source / SOURCE-CONFIRMED | system lock parameters `1278-1332` | 09 `#config-thresholds` |
| CUBRID-C062 | source / SOURCE-CONFIRMED | hash constants `88-93`; default config `1153-1189`; object init `1263-1288`; WFG init `1300-1351`; dump `8953-9049` | 09 `#memory-complexity` |
| CUBRID-C063 | source / SOURCE-CONFIRMED | `res_mutex:191-211`; hold-list insert `1405-1499`; acquire `3478-3689`; waiter grant `2782-2852` | 06 `#wait-publication` |
| CUBRID-C064 | source / SOURCE-CONFIRMED | `lock_join_existing_wait_train:3415-3453`; `lock_suspend:2304-2399` | 06 `#wait-publication` |
| CUBRID-C065 | inference / INFERRED | holder lookup `3353-3399`; acquire `3478-4051`; release `4197-4397`; detector loops `8203-8353` | 05 `#performance-05`, 09 `#memory-complexity` |
| CUBRID-C066 | source / SOURCE-CONFIRMED | perf metadata `236-247`; acquire counters `3478-4145`; MVCCID entry `6433-6487` | 09 `#observability-measurement` |
| CUBRID-C067 | source / SOURCE-CONFIRMED | `xlock_dump:8953-9065`; `lock_dump_resource:5593-5739` | 09 `#observability-measurement` |
| CUBRID-C068 | source / SOURCE-CONFIRMED | timeout formatter `2002-2248`; dump `5593-5731`; event log `10076-10090` | 09 `#diagnostic-boundaries` |
| CUBRID-C069 | inference / INFERRED | init `5889-5943`; finalize `5955-6174`; commit `5189-5260`; 2PC prepare `1314-1483` | 09 `#storage-durability-recovery` |
| CUBRID-C070 | source / SOURCE-CONFIRMED | transaction init `1107-1149`; WFG init `1300-1351`; acquire `3478-3834`; WFG growth `4931-5032` | 09 `#errors-resource-pressure` |
| CUBRID-C071 | source / SOURCE-CONFIRMED | `lock_unlock_object:7137-7217`; `lock_unlock_all:7358-7423` | 06 `#release-order` |
| CUBRID-C072 | source / SOURCE-CONFIRMED | victim wake `2595-2644`; suspend `2304-2477`; acquire cleanup `3478-4104` | 06 `#deadlock` |
| CUBRID-C073 | source / SOURCE-CONFIRMED | `LK_PERFORM_STATE:3400-3412`; generic acquire `3478-4175` | 05 `#acquire-transition-table` |
| CUBRID-C074 | source / SOURCE-CONFIRMED | waiter grant `2782-2893`; acquire/UPR `3478-4051` | 06 `#fairness-starvation-boundary` |
| CUBRID-C075 | source / SOURCE-CONFIRMED | perf gates `884-907`, `1449-1472`; init/watch `3180-3208`, `3353-3419`; `stats_on:4474-4484` | 09 `#observability-measurement` |

## 5. Examined files and file digests

| Path | SHA-256 | Evidence state | Relevant symbols |
|---|---|---|---|
| `src/transaction/lock_manager.c` | `17736dd485b179a2176ce525f85b5e7a59f3c3c3630fbeb96fa00bc4f6121cc9` | COMMIT | acquire/conversion/escalation, wait/grant/release, WFG, lifecycle, dump |
| `src/transaction/lock_manager.h` | `d996e4e67bb74f11275c5c3b2f945ad82aa9117eccfa1b7589dce03e5c93b6c3` | COMMIT | `LK_RES.res_mutex` and protected resource state |
| `src/transaction/lock_table.c` | `6866e52b0abdb94b82782b50bc6c932f2e94d4e20492af8546e034c7291b2dba` | COMMIT | `lock_Conv` table |
| `src/transaction/log_tran_table.c` | `f6b98fcd69697aca8980a6b0d45e57b7eb0b29dac959f93cda59a52e6777e7fc` | COMMIT | startup/shutdown, MVCC completion, lockless-insert materialization |
| `src/transaction/log_manager.c` | `73969c9343765e8affdd44ae7b312aac5243365418df08592be90c3325761975` | COMMIT | local commit/abort ordering |
| `src/transaction/log_2pc.c` | `fee02b8ff4af4b54a556cedb3e8700ba670a397421122f4c399ed4e2f5faca13` | COMMIT | prepare log, read/recovery seam |
| `src/base/system_parameter.c` | `fb3823943a91eb3c059afcfb248761844ac2c87e221d23d79e31db0880c56614` | COMMIT | lock/deadlock/stats parameters |
| `src/base/perf_monitor.c` | `ea814281c6f84ae4799915b17c11a3f33a84e075171b35802a6fc30a9c601f6a` | COMMIT | counter metadata, watcher lifecycle |
| `src/base/perf_monitor.h` | `fce3513a8e14508e0e667c23d6ce2df50dcbafd38e14e7f270873736212caa59` | COMMIT | counter update gates |

## 6. Contradictions and negative-search record

- There is no contradiction between the 100 ms daemon loop and the 1.0 s default detector interval: one is wake/check cadence, the other is an invocation guard. [CUBRID-C057]
- “All locks are volatile” is too broad because prepared 2PC serializes and reacquires a restricted list of exclusive object locks. “Ordinary lock queues are WAL-persisted” is also unsupported. The precise boundary is ordinary volatile coordination plus a prepared-object-lock exception. [CUBRID-C060, CUBRID-C069]
- `xlock_dump`'s printed memory size is not total memory; it counts allocated `LK_ENTRY` and `LK_RES`, while hash buckets, WFG, mutex/allocator overhead and other arrays exist separately. [CUBRID-C062, CUBRID-C067]
- General object-lock counters include MVCCID self-lock activity, but no dedicated self-lock counter was identified. A report must not turn aggregate deltas into an exact self-lock count without an isolated workload. [CUBRID-C066]
- Transaction-resource dump/event formatting uses MVCCID, while simple timeout arguments use OID union fields. This contradiction is source-local; runtime output remains unknown. [CUBRID-C068]
- No source proof of starvation freedom was found. Queue aggregate checks, head stopping, and UPR are mechanisms, not a liveness theorem. [CUBRID-C074]

Negative searches were limited to pinned `src/transaction/lock_manager.c`; they do not apply to the whole repository. Patterns and result: `log_append|logpb_flush|checkpoint|fileio_(write|synchronize)|pgbuf_set_dirty|pgbuf_flush` -> no matches; `ER_.*(DISK|FULL|CORRUPT)|out of space|ENOSPC|fsync|fdatasync` -> no matches. [CUBRID-C069]

## 7. Final-writer checklist

- [ ] Collision-check IDs CUBRID-C050–CUBRID-C075 before ledger append.
- [ ] Preserve `kind: inference` and `confidence: INFERRED` for C065/C069.
- [ ] Preserve the runtime limitation on C068.
- [ ] Put visible claim IDs on every imported paragraph, row, and pseudocode block/branch.
- [ ] Do not label the lifecycle diagram as a literal source enum.
- [ ] Do not label `xlock_dump` size as total lock-manager memory.
- [ ] Do not claim watcher-free counters measure the workload.
- [ ] Keep storage/checkpoint/full-disk N/A scoped to ordinary in-memory lock state and retain commit/2PC seams.
- [ ] Keep timeout, interrupt, deadlock victim, and allocation failure as separate terminal branches.
- [ ] Keep fairness mechanisms separate from starvation-freedom proof.
- [ ] Retain unknowns and safe experiment gaps instead of converting them into conclusions.
