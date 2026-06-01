# Demo 4: Proactive Agenda Review

## Scenario

The agent has finished five meaningful tasks. No catastrophic incident happened, but the same pattern keeps appearing: verification is improving, yet relevant past learnings are still retrieved too late and multi-step workflows still lose discipline under pressure.

## Conversation

**User**
Before we start the next unfamiliar migration task, review what the agent should deliberately train next instead of just waiting for the next failure.

**Agent**
I should run a learning agenda review. Recent tasks suggest that verification remains active, but the higher-leverage bottlenecks now are execution discipline and memory retrieval.

**User**
Why not planning?

**Agent**
Planning still matters, but the evidence suggests planning quality degrades mainly when workflow discipline collapses. Training execution discipline first should improve planning consistency as well.

## Skill Output

### Learning Agenda

```markdown
## [AGD-20260318-002] review-after-five-cycles

**Reviewed**: 2026-03-18T09:00:00Z
**Review Trigger**: scheduled_review
**Status**: active
**Next Review Trigger**: after_5_cycles

### Active Focus
1. verification
   - Why now: still the highest-cost failure surface on unfamiliar work.
   - Current evidence: checks are more explicit, but transfer is not yet fully stable.
   - Exit criteria: one more successful transfer case without user correction.
   - Linked unit: TRN-20260315-001

2. execution discipline
   - Why now: known workflows still collapse under momentum.
   - Current evidence: the agent can name the right loop but sometimes skips it in practice.
   - Exit criteria: three complex tasks completed with full-loop adherence.
   - Linked unit: TRN-20260318-003

3. memory retrieval
   - Why now: prior learnings still surface too late to prevent avoidable churn.
   - Current evidence: trigger signatures exist, but recall is not reliably timely.
   - Exit criteria: two adjacent tasks show successful retrieval before action.
   - Linked unit: TRN-20260318-004

### Deferred But Important
- planning: defer because execution discipline is the more upstream bottleneck right now.

### Review Rationale
These three priorities improve safety, consistency, and transfer more than starting a new planning unit immediately.

### Promotion Or Retirement Watch
- verification: watch for retirement after one more generalized success.
- execution discipline: keep active.
- memory retrieval: keep active.
```
