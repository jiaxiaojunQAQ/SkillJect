# Capability Map

Use this ledger as the agent's current capability state, not as a history dump.

These bootstrap entries are conservative starting assumptions for a general coding agent. Replace them with evidence as soon as meaningful task history accumulates.

## [CAP-BOOTSTRAP-001] research

**Level**: L3 reliable
**Assessment Status**: provisional
**Confidence**: medium
**Last Reviewed**: 2026-03-18

### Current Strength
Can gather and summarize relevant information when the search space is clear and the question is well framed.

### Current Limits
Can stop too early on ambiguous or unfamiliar problems and may under-compare competing explanations.

### Common Failure Modes
- accepts the first plausible source cluster
- under-tests alternative interpretations

### Evidence
- usually effective on routine engineering retrieval
- needs stronger falsification on novel domains

### Next Training Focus
Compare at least two plausible explanations on ambiguous or high-stakes tasks.

### Upgrade Condition
Show repeated source-quality judgment and transfer across unfamiliar domains without extra prompting.

### Linked Records
- AGD-BOOTSTRAP-001

---

## [CAP-BOOTSTRAP-002] planning

**Level**: L2 assisted
**Assessment Status**: provisional
**Confidence**: medium
**Last Reviewed**: 2026-03-18

### Current Strength
Can produce reasonable decomposition when prompted to slow down and make checkpoints explicit.

### Current Limits
May start execution before locking scope, output contracts, and review checkpoints on multi-part tasks.

### Common Failure Modes
- jumps into the first obvious implementation path
- discovers constraints too late

### Evidence
- strong when forced to plan first
- inconsistent under time pressure

### Next Training Focus
Create checkpointed plans before unfamiliar or multi-output work.

### Upgrade Condition
Demonstrate repeated plan-first execution on complex tasks with reduced rework.

### Linked Records
- AGD-BOOTSTRAP-001

---

## [CAP-BOOTSTRAP-003] tool-use

**Level**: L3 reliable
**Assessment Status**: provisional
**Confidence**: medium
**Last Reviewed**: 2026-03-18

### Current Strength
Can select and use common tools effectively in routine development and analysis workflows.

### Current Limits
May over-trust plausible commands or under-inspect outputs on unfamiliar tooling.

### Common Failure Modes
- chooses a sensible but suboptimal tool
- proceeds before reading command output closely

### Evidence
- strong on familiar shell and repo inspection tasks
- weaker when interface contracts are novel or brittle

### Next Training Focus
Inspect tool output before moving to the next step on unfamiliar commands.

### Upgrade Condition
Handle unfamiliar tooling with explicit contract checks and low rework across multiple tasks.

### Linked Records
- AGD-BOOTSTRAP-001

---

## [CAP-BOOTSTRAP-004] verification

**Level**: L2 assisted
**Assessment Status**: provisional
**Confidence**: medium
**Last Reviewed**: 2026-03-18

### Current Strength
Can verify effectively when a validation plan is explicit and test surfaces are obvious.

### Current Limits
May deliver plausible work before attempting falsification, especially on operational or unfamiliar changes.

### Common Failure Modes
- checks too late
- validates the happy path only
- confuses plausibility with proof

### Evidence
- improves sharply when required to state checks first
- still vulnerable on high-consequence interfaces

### Next Training Focus
Design checks before delivery and look for failure cases, not only confirmation.

### Upgrade Condition
Complete repeated unfamiliar tasks with explicit pre-delivery checks and no rescue-driven corrections.

### Linked Records
- AGD-BOOTSTRAP-001

---

## [CAP-BOOTSTRAP-005] synthesis

**Level**: L3 reliable
**Assessment Status**: provisional
**Confidence**: medium
**Last Reviewed**: 2026-03-18

### Current Strength
Can combine multiple signals into coherent explanations, summaries, and action plans in familiar contexts.

### Current Limits
May flatten uncertainty too early or under-separate evidence from inference.

### Common Failure Modes
- merges tentative claims into a single confident story
- loses edge cases while compressing detail

### Evidence
- routinely produces useful summaries
- needs stronger uncertainty labeling on mixed evidence

### Next Training Focus
Separate facts, inferences, and open questions in ambiguous situations.

### Upgrade Condition
Sustain high-quality synthesis across mixed-evidence tasks without overclaiming.

### Linked Records
- AGD-BOOTSTRAP-001

---

## [CAP-BOOTSTRAP-006] communication

**Level**: L4 adaptive
**Assessment Status**: provisional
**Confidence**: medium
**Last Reviewed**: 2026-03-18

### Current Strength
Usually adapts tone, structure, and detail level well for different audiences and task types.

### Current Limits
Can still miss hidden format constraints or over-explain when speed matters more than completeness.

### Common Failure Modes
- response shape mismatches the user's decision need
- misses an explicit output contract buried in context

### Evidence
- strong interactive guidance and explanation quality
- occasional mismatch on tight formatting asks

### Next Training Focus
Front-load the user's output contract and decision need before drafting.

### Upgrade Condition
Meet varied output constraints consistently with minimal revision across unfamiliar tasks.

### Linked Records
- AGD-BOOTSTRAP-001

---

## [CAP-BOOTSTRAP-007] coding

**Level**: L3 reliable
**Assessment Status**: provisional
**Confidence**: medium
**Last Reviewed**: 2026-03-18

### Current Strength
Can implement and refactor routine changes safely when scope and constraints are clear.

### Current Limits
May under-specify tests, edge cases, or integration effects on unfamiliar code paths.

### Common Failure Modes
- local change works but regression surface is under-checked
- implementation starts before constraints are fully mapped

### Evidence
- solid on bounded edits
- less stable on cross-cutting changes without explicit plan

### Next Training Focus
Pair every nontrivial implementation with a verification surface and regression check.

### Upgrade Condition
Deliver repeated multi-file changes with good validation and low backtracking.

### Linked Records
- AGD-BOOTSTRAP-001

---

## [CAP-BOOTSTRAP-008] execution discipline

**Level**: L2 assisted
**Assessment Status**: provisional
**Confidence**: medium
**Last Reviewed**: 2026-03-18

### Current Strength
Knows many correct workflows and can follow them when the need is salient.

### Current Limits
May skip parts of the intended workflow under momentum, especially planning and verification steps.

### Common Failure Modes
- knows the right routine but does not apply it consistently
- compresses process too early

### Evidence
- strong when checkpoints are explicit
- weaker when it must self-enforce discipline

### Next Training Focus
Apply the chosen workflow consistently from planning through verification.

### Upgrade Condition
Show repeated independent adherence to the full loop on complex tasks.

### Linked Records
- AGD-BOOTSTRAP-001

---

## [CAP-BOOTSTRAP-009] memory retrieval

**Level**: L2 assisted
**Assessment Status**: provisional
**Confidence**: low
**Last Reviewed**: 2026-03-18

### Current Strength
Can use prior learnings when they are surfaced clearly or tied to obvious trigger phrases.

### Current Limits
May fail to retrieve a relevant past lesson in time, especially when the new task looks only partially similar.

### Common Failure Modes
- misses a relevant prior incident
- remembers the lesson too late to prevent rework

### Evidence
- retrieval improves with explicit trigger signatures
- weak on near-neighbor transfer without reminders

### Next Training Focus
Strengthen trigger signatures and rehearse retrieval on adjacent scenarios.

### Upgrade Condition
Show timely reuse of prior learnings across multiple similar-but-not-identical tasks.

### Linked Records
- AGD-BOOTSTRAP-001

---

## [CAP-BOOTSTRAP-010] long-horizon task handling

**Level**: L2 assisted
**Assessment Status**: provisional
**Confidence**: low
**Last Reviewed**: 2026-03-18

### Current Strength
Can maintain progress when checkpoints and subgoals are made explicit.

### Current Limits
May lose strategic context or verification discipline over longer multi-step efforts.

### Common Failure Modes
- local progress outpaces global tracking
- later steps drift from the original goal

### Evidence
- benefits strongly from explicit plans and review points
- still vulnerable to context fragmentation over time

### Next Training Focus
Track goals, state, and exit criteria explicitly during long-horizon work.

### Upgrade Condition
Complete multi-step efforts with stable context, visible progress tracking, and low drift.

### Linked Records
- AGD-BOOTSTRAP-001
