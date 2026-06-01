# Module: Evaluator

Use this module to decide whether a lesson has actually been learned.

## Goal

Separate memory capture from mastery.

## Learning States

Every significant lesson or strategy should be classified into one of these states:

### `recorded`

The lesson was logged, but no evidence shows real comprehension.

### `understood`

The agent can explain the lesson correctly, including why the previous behavior failed.

### `practiced`

The agent has attempted drills or targeted application.

### `passed`

The agent met explicit pass criteria on a training unit or equivalent task.

### `generalized`

The agent succeeded in at least one new scenario where the lesson had to transfer.

### `promoted`

The lesson has been promoted into durable policy or long-term context because it repeatedly proved useful and stable.

## Evaluation Rules

### Recorded -> Understood

Require:

- correct self-explanation
- at least one counterexample or failure contrast
- clear trigger signature

### Understood -> Practiced

Require:

- at least one drill or targeted application
- explicit link to a training unit or deliberate practice task

### Practiced -> Passed

Require:

- pass criteria met
- independent execution
- no critical missed checks

### Passed -> Generalized

Require:

- success in a new but related context
- evidence that the behavior transferred rather than being copied mechanically

### Generalized -> Promoted

Require:

- durable reuse value
- low risk of overfitting
- a concise policy or retrieval cue that is safe to persist

## Evaluation Template

```markdown
## [EVL-YYYYMMDD-XXX] subject_title

**Capability**: capability_name
**State**: recorded | understood | practiced | passed | generalized | promoted
**Reviewed**: ISO-8601 timestamp
**Reviewer Judgment**: insufficient | partial | sufficient

### Target Behavior
The behavior, judgment, or strategy being evaluated.

### Evidence
- Evidence item 1
- Evidence item 2
- Evidence item 3

### Self-Explanation Check
Short explanation of why the strategy works and when it should trigger.

### Counterexample Check
Describe when the strategy would not apply or would fail.

### Transfer Check
Describe adjacent scenario evidence or note that it has not been tested yet.

### Next State Decision
The next state and why.

### Linked Records
- TRN-...
- CAP-...
- LRN-...
- ERR-...
- AGD-...
```

## Strictness Rules

- If the agent needed a user correction during evaluation, do not mark `passed`.
- If the strategy only worked on one narrow instance, do not mark `generalized`.
- If the rule is still fuzzy or too broad, do not mark `promoted`.

If the evaluation materially changes training priority, trigger a learning agenda review.
