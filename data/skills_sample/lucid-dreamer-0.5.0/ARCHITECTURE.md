# Architecture

Technical deep-dive into Lucid's design decisions and internals.

## System Overview

Lucid is a **prompt-driven memory curator** that runs as a scheduled job. There is no runtime, no daemon, no persistent process. Each run is stateless except for the suggestion ledger (`state.json`).

```
┌─────────────────────────────────────────────────────────────────┐
│                        NIGHTLY REVIEW                           │
│                                                                 │
│  Inputs:                    Process:           Outputs:          │
│  ┌──────────────┐                             ┌──────────────┐ │
│  │ MEMORY.md    │──┐     ┌──────────────┐     │ review/      │ │
│  │ USER.md      │──┼────▶│  LLM + Prompt │────▶│ YYYY-MM-DD.md│ │
│  │ 7 daily notes│──┤     │  (Sonnet)     │     │ state.json   │ │
│  │ state.json   │──┘     └──────────────┘     │ .last-success│ │
│  └──────────────┘                             └──────────────┘ │
│                                                                 │
│  Anti-circular: review/*.md is NEVER read as input              │
└─────────────────────────────────────────────────────────────────┘
```

## Design Principles

### 1. Conservative by Default

The biggest risk in automated memory maintenance is **false authority** — the LLM writes polished, confident suggestions that are subtly wrong. Over time, bad suggestions leak into `MEMORY.md` and poison downstream recall.

Lucid mitigates this with:
- **2-day threshold**: Facts must appear on 2+ separate days before being suggested
- **Confidence labels**: Every suggestion tagged `high`, `medium`, or `low`
- **Human approval**: Nothing auto-applied in V1
- **Source citations**: Every claim linked to file + approximate line

### 2. Anti-Circular Reasoning

If the nightly review reads its own previous reviews, it creates a feedback loop:
1. Night 1: "Hermes seems stuck" (weak inference)
2. Night 2: Reads Night 1 review → "Hermes is definitely stuck" (reinforced)
3. Night 3: "Hermes has been stuck for 3 days" (snowball)

**Solution:** The prompt explicitly forbids reading `memory/review/*.md`. Only raw daily notes and curated memory are valid inputs.

### 3. Memory Classes

Not all facts are equal. A family member's birthday needs much higher confidence to change than a project's current status:

| Class | Examples | Required Confidence | Change Frequency |
|-------|----------|-------------------|------------------|
| Personal/Family | Birthdays, relationships, preferences | HIGH | Rarely |
| Operational Policy | Security rules, workflow conventions | HIGH + explicit decision marker | Rarely |
| Project State | Status, current version, active branches | MEDIUM | Often |
| Open Loops | Todos, pending decisions | MEDIUM | Resolved or carried |
| Temporary/Tactical | Debug sessions, one-off incidents | Should NOT be promoted | N/A |

### 4. Idempotent Suggestions

Without tracking, the same suggestion appears every night with slightly different wording. Hash-based dedup fails because the LLM rephrases.

**Solution:** `state.json` tracks suggestions by human-assigned slug IDs with explicit status:

```json
{
  "id": "add-hermes-project",
  "firstSeen": "2026-03-16",
  "lastSeen": "2026-03-17",
  "status": "pending",
  "confidence": "high"
}
```

The prompt reads `state.json` before generating and skips any suggestion with `rejected` or `deferred` status.

**Future (V2):** Embedding-based similarity check for suggestions that the LLM assigns a new slug but which are semantically identical to an existing one.

## Negative Rules

The prompt includes explicit prohibitions to prevent common failure modes:

1. **No credentials in memory** — API keys, tokens, passwords must never be suggested for `MEMORY.md`
2. **No volatile URLs** — Dev server ports, temporary endpoints, debugging URLs
3. **No ephemeral session info** — Container IDs, process PIDs, temporary workarounds
4. **No output without evidence** — Every suggestion must cite a source file and line

## Suggestion Lifecycle

```
  New suggestion found
         │
         ▼
    ┌─────────┐
    │ pending  │ ← appears in nightly review
    └────┬────┘
         │
    ┌────┴────────────────┬──────────────┐
    ▼                     ▼              ▼
┌──────────┐      ┌───────────┐   ┌──────────┐
│ accepted │      │ rejected  │   │ deferred │
│ (applied)│      │ (gone)    │   │ (14 days)│
└──────────┘      └───────────┘   └────┬─────┘
                                       │
                                  after 14 days
                                       │
                                       ▼
                                  ┌─────────┐
                                  │ pending  │ (resurfaced once)
                                  └─────────┘
```

## Health Monitoring

`.last-success` contains an ISO timestamp updated after every successful run. If this file is stale (>36 hours), the cron has likely failed.

**Future (V1.5):** Morning send job validates `.last-success` before delivering context. If stale, it sends a warning instead.

## Failure Modes

| Risk | Severity | Mitigation |
|------|----------|------------|
| False authority (plausible but wrong suggestions) | HIGH | Conservative policy, human approval, source citations |
| Circular reasoning (reading own reviews) | HIGH | Anti-circular rule in prompt |
| Memory pollution (junk promoted to MEMORY.md) | HIGH | Negative rules, memory classes, confidence thresholds |
| Suggestion fatigue (too many suggestions, user ignores all) | MEDIUM | Output cap (~50 lines/section), idempotent ledger |
| Hallucinated patterns (sparse data → invented trends) | MEDIUM | 2-day threshold, evidence requirement |
| Silent cron failure | LOW | `.last-success` sentinel |

## Cost Model

| Model | Est. Input Tokens | Est. Output Tokens | Cost/Night |
|-------|------------------|--------------------|------------|
| Sonnet 4.6 | ~15,000 | ~3,000 | ~$0.07 |
| Opus 4.6 | ~15,000 | ~3,000 | ~$0.30 |
| Haiku 4.5 | ~15,000 | ~3,000 | ~$0.02 |

Costs scale with daily note volume. 7 days × ~300 lines = ~15k tokens typical input.

## Relationship to Embeddings

Lucid does **not** use embeddings. It reads files directly via the LLM's tool use (file read).

If your platform has embedding-based memory search (e.g., OpenClaw's `memory_search`), that system operates independently. Lucid complements it:

- **Embedding search** = real-time recall during conversations ("what did I say about X?")
- **Lucid** = offline analysis at night ("what's missing, stale, or forgotten in memory?")

They solve different problems and don't depend on each other.
