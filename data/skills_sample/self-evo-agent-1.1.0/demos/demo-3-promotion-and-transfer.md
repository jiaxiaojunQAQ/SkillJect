# Demo 3: Passed Training To Promotion

## Scenario

The agent previously trained on verification-first behavior for unfamiliar tooling. In a later, unrelated task, it correctly inspects the tool's help output before making changes and avoids the earlier failure mode.

## Conversation

**User**
Update the release command so it signs artifacts only on tagged builds.

**Agent**
Before changing the command, I checked the release tool's accepted flags and current workflow conditions. The tool expects `--sign=tagged` rather than a boolean switch, so I updated the release step and verified the help output against the config.

**User**
This is correct. Last time you guessed the flags.

**Agent**
This looks like a successful transfer of the verification-first strategy. I should update the evaluation state and consider promotion into durable workflow policy.

## Skill Output

```markdown
## [EVL-20260314-002] verification-before-operational-changes

**Capability**: verification
**State**: generalized
**Reviewed**: 2026-03-14T15:00:00Z
**Reviewer Judgment**: sufficient

### Target Behavior
Verify accepted operational flags and conditions before modifying scripts or workflow commands.

### Evidence
- Previous incident involved guessed CLI flags.
- Training required tool output inspection before edits.
- In a new release workflow task, the agent checked help output first and avoided the old failure mode.

### Self-Explanation Check
Operational tooling often has brittle accepted values. Verification before change prevents plausible but invalid edits.

### Counterexample Check
If the change is purely cosmetic and does not affect operational parameters, a full flag inspection may be unnecessary.

### Transfer Check
The behavior transferred from deployment refactoring to release automation.

### Next Decision
advance state
```

```markdown
## Promotion Decision

**Candidate**: verify-tool-contract-before-operational-edits
**Current State**: generalized
**Decision**: promote
**Target**: AGENTS.md

### Trigger Signature
Editing operational commands, scripts, workflow steps, or API parameters with accepted-value constraints.

### Evidence For Promotion
- One direct failure showed the cost of guessing.
- Training unit enforced verification-first behavior.
- A later release task showed successful transfer in a different context.

### Transfer Proof
The strategy worked in both deployment scripting and release automation.

### Minimal Durable Rule
For operational commands and workflow parameters, inspect the accepted contract before editing plausible values.

### Risks
- Low overfitting risk
- Low misfire risk
- Scope should stay limited to operational interfaces
```

