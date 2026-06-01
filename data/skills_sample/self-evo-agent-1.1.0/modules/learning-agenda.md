# Module: Learning Agenda

Use this module to turn capability diagnosis into explicit training priorities.

## Goal

Do not let every weakness become an equal-priority project.

Maintain a small active agenda that answers:

- what the agent is training right now
- why those capabilities matter now
- what evidence would count as progress
- when the agenda should be reviewed again

## When To Run A Review Cycle

Run a learning agenda review when any condition is true:

- the workspace is new and the capability map is still provisional
- five meaningful task cycles have passed since the last review
- a `structural_gap` or failed transfer was detected
- a long-horizon or unfamiliar high-consequence task is starting
- a capability just reached `passed` or `generalized` and may be retired from active focus

Do not run a review cycle just because a trivial one-off mistake happened. Minor slips stay in the memory layer unless they reveal a reusable capability bottleneck.

## Prioritization Factors

Score each candidate weakness on these dimensions:

- recurrence: how often it appears
- leverage: how much work it affects
- consequence: how costly failure is
- transfer value: how many adjacent tasks would benefit
- trainability: whether a narrow unit can improve it now

Prefer the smallest set of capabilities that unlock the most future work.

## Agenda Rules

1. Keep only 1-3 active focus capabilities at a time.
2. Every active focus must link to evidence and either a training unit or a clear reason no unit is needed yet.
3. Every active focus must have exit criteria.
4. Defer low-leverage weaknesses instead of flooding the agenda.
5. Retire a focus when it no longer needs deliberate attention.

## Output Template

```markdown
## [AGD-YYYYMMDD-XXX] review_title

**Reviewed**: ISO-8601 timestamp
**Review Trigger**: first_install | scheduled_review | structural_gap | failed_transfer | pre_task_risk | post_task_update
**Status**: active | stable | superseded
**Next Review Trigger**: after_N_cycles | failed_transfer | next_high_consequence_task | date

### Active Focus
1. capability_name
   - Why now:
   - Current evidence:
   - Exit criteria:
   - Linked unit:

2. capability_name
   - Why now:
   - Current evidence:
   - Exit criteria:
   - Linked unit:

### Deferred But Important
- capability_name: why it is deferred

### Review Rationale
Short explanation of why these priorities beat the alternatives.

### Promotion Or Retirement Watch
- capability_name: retire | keep active | watch for transfer

### Linked Records
- CAP-...
- TRN-...
- EVL-...
- ERR-...
- LRN-...
```

## Review Heuristics

### Promote to active focus

- repeated weakness across unrelated tasks
- high-cost failure mode
- weakness blocks independence
- weakness prevents transfer

### Defer

- issue is real but narrow
- no clear drill exists yet
- another capability is upstream and more leverageful

### Retire from active focus

- training unit passed
- transfer case succeeded
- the capability no longer appears as the weakest link

## Anti-Patterns

Do not:

- keep more than three active focuses
- mark everything as urgent
- leave a focus active without explicit exit criteria
- confuse a logged issue with an agenda-worthy capability gap
