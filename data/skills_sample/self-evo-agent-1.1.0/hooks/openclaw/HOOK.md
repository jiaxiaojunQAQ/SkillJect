---
name: self-evolving-agent
description: "Injects a capability-evolution reminder during agent bootstrap"
metadata: {"openclaw":{"emoji":"🧭","events":["agent:bootstrap"]}}
---

# Self-Evolving Agent Hook

This hook reminds the agent to think in capability-evolution terms, not only in incident-logging terms.

## What It Injects

- default to the light loop and escalate only when evidence justifies the full pipeline
- inspect the active learning agenda
- retrieve relevant prior learnings
- inspect the legacy migration layer if it exists
- inspect capability risks for the upcoming task
- choose an execution strategy with a verification plan
- after the task, diagnose weaknesses and decide whether training or evaluation is needed
- refresh the learning agenda if priorities changed
- track progress through the evaluation ladder (`recorded` -> `promoted`)
- promote only validated, transferable strategies

## Enable

```bash
openclaw hooks enable self-evolving-agent
```
