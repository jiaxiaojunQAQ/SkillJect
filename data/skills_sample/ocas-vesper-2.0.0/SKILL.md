---
name: ocas-vesper
description: Daily briefing generator. Aggregates signals from across the system into concise morning and evening briefings. Surfaces outcomes, opportunities, and decisions in natural language without exposing internal processes. Use for morning/evening briefings, on-demand briefings, or pending decision review. Do not use for deep research (Sift), pattern analysis (Corvus), or message drafting (Dispatch).
metadata: {"openclaw":{"emoji":"🌅"}}
---

# Vesper

Vesper generates concise daily briefings by aggregating signals from across the system. It presents outcomes and opportunities in natural assistant language while hiding internal processes.

## When to use

- Generate morning or evening briefing
- Request an on-demand briefing
- Check pending decision requests
- Configure briefing schedule or sections

## When not to use

- Deep research — use Sift
- Pattern analysis — use Corvus
- Message drafting — use Dispatch
- Action execution — use relevant domain skill

## Responsibility boundary

Vesper owns briefing generation, signal aggregation, and decision presentation.

Vesper does not own: pattern analysis (Corvus), web research (Sift), communications delivery (Dispatch), action decisions (Praxis).

Vesper receives InsightProposal files from Corvus. Vesper may request Dispatch to deliver briefings.

## Commands

- `vesper.briefing.morning` — generate morning briefing
- `vesper.briefing.evening` — generate evening briefing
- `vesper.briefing.manual` — on-demand briefing
- `vesper.decisions.pending` — list unacted decision requests
- `vesper.config.set` — update schedule, sections, delivery
- `vesper.status` — last briefing time, pending decisions, schedule
- `vesper.journal` — write journal for the current run; called at end of every run

## Invocation modes

- **Automatic morning** — during configured morning window
- **Automatic evening** — during configured evening window
- **Manual** — on user request

## Signal filtering rules

Include: actionable information, meaningful outcomes, plan-affecting changes, multi-signal opportunities, preparation-useful information.

Exclude: routine background activity, already-experienced events, internal system reasoning, speculative observations.

Evening-specific: no past weather, no summaries of attended meetings.

Read `references/signal_filtering.md` for full rules.

## Formatting rules

- Conversational paragraphs, not bullet dumps
- Section headers use emoji: 📅 Today, ✉️ Messages, 🧭 Logistics, 📈 Markets, 🔐 Decisions, 🛠 System
- Links use `[[artifact name]]` format
- Weather in opening paragraph, no section header
- Decision requests: option, benefit, cost — framed as optional
- Opportunities surfaced without exposing underlying analysis

Read `references/briefing_templates.md` for structure and examples.

## Behavior constraints

- No nagging — ignored decisions are treated as intentional
- No internal system terminology
- No references to architecture or analysis processes
- No speculative observations
- Only concrete outcomes and actionable opportunities

## Inter-skill interfaces

Vesper receives InsightProposal files from Corvus at: `~/openclaw/data/ocas-vesper/intake/{proposal_id}.json`

Vesper checks its intake during briefing generation. Applies signal filtering rules before including. After processing each file, move to `intake/processed/`.

See `spec-ocas-interfaces.md` for the InsightProposal schema and handoff contract.

## Storage layout

```
~/openclaw/data/ocas-vesper/
  config.json
  briefings.jsonl
  signals_evaluated.jsonl
  decisions_presented.jsonl
  decisions.jsonl
  intake/
    {proposal_id}.json
    processed/

~/openclaw/journals/ocas-vesper/
  YYYY-MM-DD/
    {run_id}.json
```

The OCAS_ROOT environment variable overrides `~/openclaw` if set.

Default config.json:
```json
{
  "skill_id": "ocas-vesper",
  "skill_version": "2.0.0",
  "config_version": "1",
  "created_at": "",
  "updated_at": "",
  "schedule": {
    "morning_window": "07:00-09:00",
    "evening_window": "17:00-19:00",
    "timezone": "America/Los_Angeles"
  },
  "sections": {
    "today": true,
    "messages": true,
    "logistics": true,
    "markets": true,
    "decisions": true,
    "system": true
  },
  "retention": {
    "days": 30,
    "max_records": 10000
  }
}
```

## OKRs

Universal OKRs from spec-ocas-journal.md apply to all runs.

```yaml
skill_okrs:
  - name: signal_precision
    metric: fraction of included signals rated actionable by user
    direction: maximize
    target: 0.85
    evaluation_window: 30_runs
  - name: terminology_compliance
    metric: fraction of briefings free of internal system terminology
    direction: maximize
    target: 1.0
    evaluation_window: 30_runs
  - name: decision_framing
    metric: fraction of decision requests including option, benefit, and cost
    direction: maximize
    target: 1.0
    evaluation_window: 30_runs
```

## Optional skill cooperation

- Corvus — receives InsightProposal files via intake directory
- Dispatch — may request Dispatch to deliver briefings
- Rally — reads portfolio outcome signals
- Calendar/Weather — reads external context for briefing content

## Journal outputs

Action Journal — every briefing generation run.

## Visibility

public

## Support file map

File | When to read
`references/schemas.md` | Before creating briefings, sections, or decision requests
`references/briefing_templates.md` | Before generating briefing content
`references/signal_filtering.md` | Before evaluating signals for inclusion
`references/journal.md` | Before vesper.journal; at end of every run
