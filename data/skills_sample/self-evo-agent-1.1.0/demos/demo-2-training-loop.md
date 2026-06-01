# Demo 2: Recurring Weakness To Training Unit

## Scenario

Across two tasks, the agent keeps jumping into implementation before creating a checkpointed plan. It eventually finishes, but with avoidable churn and rework.

## Conversation

**User**
Please add export support for CSV, JSONL, and Markdown reports.

**Agent**
I started implementing all three outputs directly.

**User**
You missed that CSV requires flattening nested fields and Markdown needs grouped sections. Please step back and plan first.

**Agent**
You're right. This is the second time I started coding before defining output contracts and checkpoints. This looks like a planning and execution discipline weakness, not just a rushed iteration.

## Skill Output

```markdown
## [TRN-20260314-001] checkpointed-planning-before-implementation

**Capability**: planning
**Status**: active
**Priority**: high
**Created**: 2026-03-14T13:10:00Z
**Trigger Signature**: multi-output task with format-specific constraints

### Why This Unit Exists
The agent repeatedly begins implementation before defining structure, checkpoints, and format-specific constraints.

### Learning Objective
For multi-part tasks, produce a short decomposition and validation plan before touching code.

### Failure Pattern
- Starts implementation from the most obvious path
- Discovers format constraints too late
- Creates rework that a short planning pass would have prevented

### Drills
1. Given a task with three outputs, produce an execution plan with checkpoints only.
2. Compare a weak "just start coding" approach with a checkpointed plan.
3. Transfer drill: apply the same planning routine to a docs-generation task instead of code.

### Pass Criteria
- Plan is written before implementation.
- Checkpoints cover each output format's risk.
- Rework is reduced or avoided in the next task.

### Transfer Scenarios
- Multi-format export feature
- Multi-step documentation generator
```

```markdown
## [EVL-20260314-001] planning-checkpoints

**Capability**: planning
**State**: practiced
**Reviewed**: 2026-03-14T13:15:00Z
**Reviewer Judgment**: partial

### Target Behavior
Create a short decomposition and checkpoint plan before implementing multi-output tasks.

### Evidence
- Weakness identified across two tasks
- Training unit created with explicit drills
- No successful transfer case yet

### Self-Explanation Check
Planning first reduces rework by exposing hidden constraints before implementation cost compounds.

### Counterexample Check
For a tiny single-file edit with low consequence, a formal checkpoint plan may be unnecessary.

### Transfer Check
Not yet tested.

### Next Decision
Keep current state
```

