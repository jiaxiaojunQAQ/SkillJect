# Module: Promotion

Use this module to decide what earns long-term persistence.

## Goal

Promote only validated, reusable strategies into durable agent behavior.

## Promotion Criteria

A strategy is promotion-eligible only if all are true:

1. It has clear trigger conditions.
2. It has reached at least `generalized`.
3. It has practical reuse value across future tasks.
4. It is concise enough to persist as a stable rule or cue.
5. It is unlikely to create regressions by overgeneralization.

## Promotion Targets

- `AGENTS.md` for workflow policy
- `TOOLS.md` for tool-specific constraints or patterns
- `SOUL.md` for durable behavioral guidance
- `MEMORY.md` for persistent project or operator facts

## Promotion Decision Template

```markdown
## Promotion Decision

**Candidate**: strategy_title
**Current State**: recorded | understood | practiced | passed | generalized | promoted
**Decision**: reject | defer | promote
**Target**: AGENTS.md | TOOLS.md | SOUL.md | MEMORY.md | none

### Trigger Signature
When should this strategy activate?

### Evidence For Promotion
- Evidence 1
- Evidence 2
- Evidence 3

### Transfer Proof
Describe the new context where the strategy also worked.

### Minimal Durable Rule
Write the smallest safe version of the rule to promote.

### Risks
- Overfitting risk
- Misfire risk
- Scope risk
```

## Promotion Heuristics

Promote:

- concise workflow rules that repeatedly prevent failures
- durable verification habits
- retrieval cues with strong transfer value
- tool constraints that are consistently true

Do not promote:

- one-off hacks
- environment-specific accidents without repeat evidence
- long procedural text that belongs in a training unit, not memory
- lessons that still require interpretation to apply safely

## Minimal Rule Principle

Promote the smallest stable abstraction.

Bad:

- "Always use approach X for all planning tasks"

Better:

- "For unfamiliar multi-step tasks, write checkpoints before execution"

