# Demo 1: Incident To Capability Diagnosis

## Scenario

The agent is asked to refactor a build pipeline. It edits files quickly, but skips verification and breaks a deployment script. The user points out that the generated command uses the wrong environment flag.

## Conversation

**User**
Refactor the deployment workflow so staging and production share the same script.

**Agent**
I consolidated both scripts into one and updated the CI config.

**User**
This broke production. You changed `--env prod` to `--env production`, but the deploy tool only accepts `prod`.

**Agent**
Understood. I made a plausible normalization without verifying the tool's accepted values. I need to treat this as a verification and tool-use issue, not just a typo.

## Skill Output

```markdown
## Task Diagnosis

**Task Class**: mixed
**Consequence**: high
**Primary Capabilities**: coding, tool-use, verification
**Weakest Link**: verification
**Root Cause**: verification_weakness
**Pattern Status**: emerging_pattern

### Evidence
- The command flag was normalized without checking tool constraints.
- A high-consequence change was delivered without a validation step.
- The failure surfaced through user correction, not self-checking.

### Why This Matters
The agent can produce plausible refactors, but on operational workflows it still under-verifies assumptions. This is reusable risk, not a one-off typo.

### Recommended Next Step
create_training_unit
```

```markdown
## [LRN-20260314-001] best_practice

**Logged**: 2026-03-14T12:00:00Z
**Priority**: high
**State**: recorded
**Area**: verification

### Summary
Do not normalize operational CLI flags without checking accepted values.

### What Happened
During a deployment refactor, the agent changed `prod` to `production` because it looked semantically cleaner.

### Correct Understanding
Operational interfaces must be verified against actual accepted parameters, not inferred from naming intuition.

### Why It Matters
This applies across scripts, CLIs, and APIs where plausible aliases may still be invalid.

### Trigger Signature
Plausible change to an operational interface without direct validation.

### Counterexample
If the interface specification or tests explicitly permit aliases, normalization may be safe.
```

```markdown
## Capability Update

**Capability**: verification
**Previous Level**: L2 assisted
**Current Level**: L2 assisted (no upgrade; evidence supports staying)
**Assessment Status**: calibrated
**Evidence Added**: Skipped tool-contract validation on a high-consequence deploy refactor; user corrected.
**Failure Mode Added**: Normalizes CLI flags by semantic guessing instead of checking accepted values.
**Next Training Focus**: Verify operational interfaces against accepted parameters before committing changes.
```

