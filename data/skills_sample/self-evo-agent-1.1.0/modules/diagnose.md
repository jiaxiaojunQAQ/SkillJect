# Module: Diagnose

Use this module to convert task outcomes into capability-level diagnosis.

## Goal

Do not stop at "what happened." Explain:

- what capabilities the task depended on
- which capability became the bottleneck
- whether the problem is occasional or systemic
- what root cause best explains it

## Diagnosis Procedure

### 1. Map task demands

List the top capabilities required by the task.

Example:

- planning
- verification
- tool-use
- communication

### 2. Identify observed evidence

Collect concrete evidence:

- error messages
- user corrections
- unnecessary retries
- missed constraints
- verification omissions
- successful recovery behavior

### 3. Find the weakest link

Ask:

- If one capability had been stronger, would the task have gone smoothly?
- Which weakness created the most downstream damage?
- Which weakness is most likely to recur across tasks?

### 4. Classify the problem

Use one or more root-cause labels:

- `knowledge_gap`
- `decomposition_weakness`
- `verification_weakness`
- `tool_use_weakness`
- `communication_weakness`
- `memory_retrieval_weakness`
- `execution_discipline_weakness`
- `transfer_weakness`

### 5. Determine recurrence

Label as:

- `incidental`
- `emerging_pattern`
- `recurring_pattern`
- `structural_gap`

Use `recurring_pattern` only when there are at least two related incidents or one very strong prior signal plus one fresh failure.

### 6. Recommend action

Choose one:

- `log_only`
- `update_capability`
- `create_training_unit`
- `run_evaluation`
- `consider_promotion`

## Output Template

```markdown
## Task Diagnosis

**Task Class**: familiar | mixed | unfamiliar
**Consequence**: low | medium | high
**Primary Capabilities**: capability_a, capability_b, capability_c
**Weakest Link**: capability_name
**Root Cause**: knowledge_gap | decomposition_weakness | verification_weakness | tool_use_weakness | communication_weakness | memory_retrieval_weakness | execution_discipline_weakness | transfer_weakness
**Pattern Status**: incidental | emerging_pattern | recurring_pattern | structural_gap

### Evidence
- Concrete signal 1
- Concrete signal 2
- Concrete signal 3

### Why This Matters
One paragraph on how this weakness affected the task and why it matters beyond this incident.

### Recommended Next Step
log_only | update_capability | create_training_unit | run_evaluation | consider_promotion
```

## Diagnostic Heuristics

### Likely knowledge gap

- The agent did not know a necessary fact or concept.
- Once told, the path became straightforward.

### Likely decomposition weakness

- The agent had enough knowledge but structured the task poorly.
- The failure came from ordering, scoping, or chunking mistakes.

### Likely verification weakness

- The agent produced something plausible but insufficiently checked.
- Bugs or inaccuracies survived because validation was skipped or weak.

### Likely tool-use weakness

- The agent used the wrong tool, the right tool incorrectly, or failed to inspect outputs carefully.

### Likely communication weakness

- Requirements were available, but the output missed audience, format, tone, or clarity constraints.

### Likely memory retrieval weakness

- A relevant prior learning existed but was not surfaced in time.

### Likely execution discipline weakness

- The agent knew the correct path but failed to follow it consistently.

### Likely transfer weakness

- The strategy worked in one setting but failed in a slightly different context.

## Escalation Rule

Escalate to a training unit when the diagnosis suggests a reusable weakness, not just a one-off accident.

If the pattern is still `incidental`, the consequence was low, and verification contained the damage, prefer `log_only` or `update_capability` over the full training pipeline.

Escalate from a light loop into the full loop when:

- the same weakness appears again
- the user had to rescue the task
- the issue would have mattered under higher consequence
- the lesson appears transferable enough to affect future policy
