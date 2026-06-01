# Module: Curriculum Builder

Use this module when a weakness deserves deliberate practice instead of mere logging.

## Goal

Convert recurring or high-leverage weaknesses into structured training units.

## When To Create A Training Unit

Create or update a `TRAINING_UNIT` when any condition is true:

- the same failure pattern appears twice
- a high-value task was blocked by a weak capability
- the agent understood the lesson but could not execute it consistently
- a strategy worked only with heavy user rescue
- the weakness is likely to recur in adjacent tasks

## Training Design Principles

1. Train the capability, not just the incident.
2. Keep drills narrow enough to diagnose real improvement.
3. Define pass criteria before practice.
4. Include at least one transfer scenario.
5. Capture trigger signatures so retrieval becomes easier later.

## Training Unit Template

```markdown
## [TRN-YYYYMMDD-XXX] unit_title

**Capability**: research | planning | tool-use | verification | synthesis | communication | coding | execution discipline | memory retrieval | long-horizon task handling
**Status**: open | active | passed | archived
**Priority**: low | medium | high | critical
**Created**: ISO-8601 timestamp
**Trigger Signature**: Short phrase describing when this unit should activate

### Why This Unit Exists
Describe the recurring weakness or strategic importance.

### Learning Objective
State the exact behavior or judgment the agent should acquire.

### Failure Pattern
- Failure pattern 1
- Failure pattern 2

### Drills
1. Drill one
2. Drill two
3. Transfer drill

### Pass Criteria
- Criterion 1
- Criterion 2
- Criterion 3

### Transfer Scenarios
- Adjacent task scenario
- Harder task scenario

### Evidence To Record
- What success looks like
- What failure looks like

### Linked Evidence
- LRN-...
- ERR-...
- EVL-...
- CAP-...
- AGD-...
```

## Drill Patterns

### For knowledge gaps

- self-explanation drill
- compare correct vs incorrect examples
- retrieve and restate the rule from memory later

### For decomposition weakness

- plan-before-action drill
- generate checkpoints before execution
- compare a weak plan against a strong plan

### For verification weakness

- design explicit checks before delivering
- create counterexamples
- force failure-hunting before approval

### For tool-use weakness

- choose the tool and explain why
- inspect outputs before moving on
- recover from a simulated bad tool choice

### For memory retrieval weakness

- identify trigger signatures
- rehearse retrieval from related scenarios
- compare missed retrieval vs successful retrieval

## Graduation Rule

A training unit is not `passed` until the evaluator confirms:

- the pass criteria were met
- the behavior appeared without external rescue
- at least one transfer case succeeded

If a passed or failed unit changes what should be trained next, update the learning agenda.
