---
name: self-evolving-agent
description: Build a goal-driven self-learning loop for OpenClaw and coding agents. Use when the agent should not only log mistakes, but diagnose capability gaps, maintain a capability map and learning agenda, generate training units, evaluate progress, validate transfer, and promote only proven strategies into long-term behavior. Also use before major tasks to retrieve relevant learnings, inspect capability risks, and choose safer execution strategies.
metadata:
  short-description: Capability evolution for agents
---

# Self-Evolving Agent

`self-evolving-agent` upgrades passive self-improvement into an explicit capability evolution system.

Use this skill when any of the following is true:

- A task is difficult, novel, high-stakes, or long-horizon.
- An error, correction, or near-miss reveals a deeper capability weakness.
- The same failure pattern appears more than once.
- A useful tactic might deserve promotion into long-term context, but has not been validated yet.
- You want to understand not just what went wrong, but what the agent can do now, what it still cannot do, and what it should train next.

Default to the light loop first. Escalate into the full capability-evolution loop only when the task or evidence justifies the extra cost.

## Core Principle

Do not treat logging as learning.

This skill separates six states of progress:

1. `recorded`
2. `understood`
3. `practiced`
4. `passed`
5. `generalized`
6. `promoted`

A lesson only becomes long-term policy after it survives training and transfer.

## What This Skill Preserves From Classic Self-Improvement

Keep the original strengths as the memory layer:

- Log errors, corrections, learnings, and feature requests.
- Detect recurring patterns.
- Review prior learnings before major work.
- Promote only high-value guidance into long-term context.
- Use workspace files and hooks to keep memory persistent across sessions.

## What This Skill Adds

This skill adds an active learning layer:

- Capability map with levels, failure modes, and upgrade criteria
- Proactive learning agenda that selects the next 1-3 capabilities to train
- Task-level diagnosis of root causes
- Training unit generation for recurring weaknesses
- Evaluation gates that separate recording from mastery
- Transfer checks on new tasks before promotion
- Reflection routines that force self-explanation and counterexamples

## Closed Loop

Run the following loop, in order:

1. Classify the task.
2. Retrieve relevant learnings and related capabilities.
3. Run a pre-task risk diagnosis.
4. Choose an execution strategy.
5. Perform the task.
6. Run post-task reflection.
7. Update the capability map.
8. Generate a training unit if weakness or recurrence is detected.
9. Evaluate learning progress.
10. Promote only validated strategies.

## Effort Modes

### Light loop

Use the lightweight pass when all of the following are true:

- The task is familiar.
- Consequence is low.
- Horizon is short.
- No active agenda focus is central to the task.
- No failure, near-miss, or user rescue exposed a deeper weakness.
- No learning needs training, evaluation, or promotion.

In the light loop:

1. Retrieve only the most relevant 1-3 memory items.
2. Name the single most likely risk and one verification check.
3. Do the work.
4. Log only unusually reusable lessons.
5. Stop unless an escalation trigger fires.

### Full loop

Run the full loop when any of the following is true:

- The task is mixed or unfamiliar.
- Consequence is medium or high and failure would matter.
- Horizon is medium or long with many dependencies.
- An active agenda focus is relevant.
- A failure, near-miss, or user correction suggests a reusable weakness.
- A similar issue repeated, transfer failed, or promotion is under consideration.
- The task itself is deliberate practice, evaluation, or promotion review.

### Escalation triggers

Escalate from light to full when any of the following appears during execution:

- non-trivial rework
- verification catches a real defect
- the user had to rescue or redirect the task
- a missed retrieval or repeated pattern appears
- the learning looks broad enough to affect future policy

## Control Loop

Outside the 10-step task loop, maintain an explicit learning agenda.

Run an agenda review when any of the following is true:

- The workspace is new and no calibrated capability map exists.
- Five meaningful cycles have passed since the last review.
- A `structural_gap` or failed transfer was detected.
- A long-horizon or unfamiliar task is about to begin.

During agenda review:

- choose the top 1-3 capabilities to train next
- defer lower-leverage weaknesses instead of training everything at once
- define what evidence would retire or advance each focus
- link each focus to existing or new training units

## File Map

- Main orchestration: `system/coordinator.md`
- Learning agenda and review cycle: `modules/learning-agenda.md`
- Diagnosis: `modules/diagnose.md`
- Capability definitions and update rules: `modules/capability-map.md`
- Training unit design: `modules/curriculum.md`
- Learning evaluation ladder: `modules/evaluator.md`
- Promotion gate: `modules/promotion.md`
- Reflection protocol: `modules/reflection.md`

Assets and ledgers:

- `assets/LEARNINGS.md`
- `assets/ERRORS.md`
- `assets/FEATURE_REQUESTS.md`
- `assets/CAPABILITIES.md`
- `assets/LEARNING_AGENDA.md`
- `assets/TRAINING_UNITS.md`
- `assets/EVALUATIONS.md`

## Operating Rules

### During migration from self-improving-agent

- Treat `.evolution/legacy-self-improving/` as a read-only memory layer.
- Search the legacy files during retrieval if they exist.
- Do not bulk-convert every old entry into the new schema on day one.
- Normalize a legacy learning into `.evolution` only when it is reused, agenda-worthy, or needed for evaluation.

### Before a substantial task

- Read `system/coordinator.md`.
- Check whether `assets/LEARNING_AGENDA.md` requires a review cycle.
- Retrieve relevant entries from `LEARNINGS`, `ERRORS`, `CAPABILITIES`, and `TRAINING_UNITS`.
- Identify the top 1-3 risk capabilities for this task.

### After every meaningful task

- Log incident-level observations in the memory files.
- Diagnose the weakest capability involved.
- Update the capability map with evidence, not vibes.
- Refresh the learning agenda if a focus should change.
- If the issue is recurring or high-leverage, create or revise a training unit.
- Record evaluation status using the six-state ladder.

### Before promotion

- Read `modules/evaluator.md` and `modules/promotion.md`.
- Confirm the strategy has passed training and succeeded in at least one transfer scenario.
- Promote the smallest stable rule that explains the success.

## When Not To Use Heavyweight Evaluation

Use a lightweight pass when all of the following are true:

- The task was trivial.
- No real uncertainty or failure occurred.
- No new behavior should be generalized.

In that case, log the learning only if it is unusually reusable.

## Output Contracts

When this skill is active, prefer producing these artifacts:

- A learning agenda review when triggers fire
- A short pre-task risk diagnosis
- A post-task capability diagnosis
- A `TRAINING_UNIT` when recurrence or weakness appears
- An `EVALUATION` entry when progress is tested
- A promotion decision with explicit evidence

## Recommended Workflow

1. Read `system/coordinator.md`.
2. Load only the modules needed for the current step.
3. Use the asset templates as the canonical output format.
4. Keep long-term memory strict: only promote validated patterns.
