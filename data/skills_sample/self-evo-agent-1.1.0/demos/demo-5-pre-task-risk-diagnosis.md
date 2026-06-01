# Demo 5: Pre-Task Risk Diagnosis

## Scenario

The agent is asked to modify a production deployment workflow it has never touched before. Before making any changes, it runs a pre-task risk diagnosis to identify the most likely failure modes and choose a safer execution strategy.

## Conversation

**User**
I need you to modify the production deployment workflow so it supports blue-green deployments. You have never worked with this repo before.

**Agent**
Before I start editing, I should run a pre-task risk diagnosis. This is an unfamiliar, high-consequence task — exactly the kind of work where prior failures in verification and tool-use are most likely to recur.

## Skill Output

```markdown
## Pre-Task Risk Diagnosis

**Task Class**: unfamiliar
**Consequence**: high
**Horizon**: medium

### Required Capabilities
- tool-use (deployment CLI, config files)
- verification (production-impacting changes)
- planning (multi-step migration with rollback)
- coding (workflow script edits)

### Top Capability Risks
1. **verification** — past incidents show the agent normalizes CLI flags without checking accepted values. Blue-green deploy flags are likely unfamiliar.
2. **tool-use** — the agent has not used this repo's deploy tooling before. Incorrect assumptions about command syntax are likely.
3. **planning** — blue-green deployment requires a rollback plan. Skipping decomposition could lead to a partial migration with no safe revert path.

### Relevant Prior Learnings
- LRN-20260314-001: Do not normalize operational CLI flags without checking accepted values.
- AGD-20260318-002: verification and execution discipline are active training focuses.

### Mitigation Plan
- Read the deploy tool's help output and existing config before making any edits.
- Confirm accepted flag values from source or docs, not from intuition.
- Decompose into: (1) understand current workflow, (2) design blue-green extension, (3) implement with checkpoint, (4) validate before merge.

### Verification Plan
- After each edit, run the deploy command in dry-run mode if available.
- Compare generated config against the existing production config to catch unintended changes.
- Request user review before any production-facing commit.

### Chosen Execution Strategy
decompose-first + verification-at-each-step
```
