# Module: Capability Map

Use this module to maintain a capability-oriented view of the agent.

## Goal

A capability map should answer:

- What core capabilities does the agent currently have?
- What level is each capability at?
- What are the common failure modes?
- What is the next training focus?
- What must happen before the capability can level up?

## Default Capability Families

- research
- planning
- tool-use
- verification
- synthesis
- communication
- coding
- execution discipline
- memory retrieval
- long-horizon task handling

Add more only when the domain requires it.

## Level Rubric

Use a 5-level rubric:

- `L1 aware`
  - recognizes the capability and can follow direct guidance
- `L2 assisted`
  - can perform with scaffolding, reminders, or user correction
- `L3 reliable`
  - succeeds on routine cases independently
- `L4 adaptive`
  - handles variations and can recover from moderate surprises
- `L5 transferable`
  - generalizes across domains and teaches or composes the skill well

## Update Rules

### Bootstrap with conservative seeds

If the map is empty, start from conservative provisional entries instead of a blank file.

The first goal is not perfect calibration. The first goal is to make current strengths, limits, and next training focus explicit enough to drive behavior.

### Upgrade only when there is evidence

Good evidence includes:

- repeated successful use
- successful use under reduced support
- transfer to a new context
- correct self-correction before external correction

### Downgrade carefully

Downgrade when:

- repeated failure contradicts the current level
- success depended heavily on rescue or luck
- transfer attempts fail

### Keep the map stable

Do not change levels after every minor task. Prefer updating evidence, failure modes, and next focus first.

## What To Track Per Capability

- current level
- assessment status
- confidence
- recent evidence
- common failure modes
- next training focus
- upgrade condition
- last reviewed date

## Output Template

```markdown
## [CAP-YYYYMMDD-XXX] capability_name

**Level**: L1 aware | L2 assisted | L3 reliable | L4 adaptive | L5 transferable
**Assessment Status**: provisional | calibrated
**Confidence**: low | medium | high
**Last Reviewed**: ISO-8601 timestamp

### Current Strength
Short description of what the agent can reliably do now.

### Current Limits
Short description of where the capability breaks down.

### Common Failure Modes
- Failure mode 1
- Failure mode 2
- Failure mode 3

### Evidence
- Positive evidence
- Negative evidence
- Transfer evidence

### Next Training Focus
What should be practiced next.

### Upgrade Condition
What evidence is required for the next level.

### Linked Units
- TRN-...
- EVL-...
- LRN-...
- AGD-...
```

## Calibration Triggers

Recalibrate a capability when:

- it is selected as an active agenda focus
- a structural gap was diagnosed
- a transfer attempt succeeded or failed
- five meaningful cycles have accumulated since the last review

## Mapping Guidelines

### Research

Focus on source selection, synthesis quality, and relevance judgment.

### Planning

Focus on decomposition, sequencing, checkpointing, and scope control.

### Tool-use

Focus on tool selection, command correctness, and output inspection.

### Verification

Focus on test design, falsification, edge checks, and confidence calibration.

### Synthesis

Focus on combining evidence into coherent conclusions or artifacts.

### Communication

Focus on audience fit, structure, clarity, and precision.

### Coding

Focus on implementation quality, constraint-following, and change safety.

### Execution discipline

Focus on following the intended workflow under pressure.

### Memory retrieval

Focus on recalling the right prior learning at the right time.

### Long-horizon task handling

Focus on progress tracking, context maintenance, and multi-step closure.
