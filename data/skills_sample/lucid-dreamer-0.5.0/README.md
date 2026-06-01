# Lucid 🧠

> *Your AI sleeps. Lucid dreams.*

**Lucid keeps your AI's memory clean.** Every night, it reads what happened, checks what your AI already knows, and tells you what's outdated, missing, or forgotten.

No database. No embeddings. No dependencies. Just a prompt, a cron job, and markdown files.

## The Problem

AI agents forget. Between sessions, context is lost. Long-term memory files (`MEMORY.md`) get stale. Todos slip through the cracks. Nobody notices until it's too late.

**Lucid fixes this automatically.** While you sleep, it:

- 🔍 Finds facts worth remembering that aren't saved yet
- ⏳ Spots todos and decisions that were never resolved
- 🚧 Flags problems that keep coming back day after day
- 🔄 Tracks when your opinions or plans changed
- 🗑️ Catches outdated entries in your memory files
- 📎 Suggests merging duplicate entries
- 📈 Detects recurring issues, stale projects, and repeated mistakes over 14 days

You wake up to a short report. You approve what's useful, reject what's not. Done.

## How it works

```
Daily Notes (7 days)     MEMORY.md + USER.md
         \                    /
          \                  /
       ┌──────────────────────┐
       │   Nightly LLM Review │  ← runs at 3 AM
       └──────────────────────┘
                  │
          ┌───────┴───────┐
          │               │
    review file        state.json
   (for you to read)   (tracks suggestions)
          │
          ▼
    you approve/reject
          │
          ▼
    memory updated ✅
```

**Cost:** One LLM call per night (~$0.20 with Sonnet, less with Haiku).

## Quick Start

### With OpenClaw

1. Create the output directory:
```bash
mkdir -p memory/review
```

2. Add the nightly cron:
```bash
openclaw cron add \
  --name "lucid" \
  --cron "0 3 * * *" \
  --tz "Your/Timezone" \
  --model "anthropic/claude-sonnet-4-6" \
  --announce \
  --session isolated \
  --timeout-seconds 120 \
  --message "$(cat prompts/nightly-review.md)"
```

3. Check results in the morning:
```bash
cat memory/review/YYYY-MM-DD.md
```

4. Tell your agent what to accept or reject. It handles the rest.

### Without OpenClaw

Lucid is just a prompt. Copy `prompts/nightly-review.md`, give it to any LLM that can read and write files, and run it on a schedule. That's it.

## What you need

```
your-workspace/
├── MEMORY.md              # Your AI's long-term memory
├── USER.md                # User profile (optional but helpful)
├── memory/
│   ├── 2026-03-15.md      # Daily notes (Lucid reads last 7 days)
│   ├── 2026-03-16.md
│   └── review/            # Lucid writes here
│       ├── 2026-03-17.md  # The review (human-readable)
│       ├── state.json     # Suggestion tracker (machine-readable)
│       └── .last-success  # Health check timestamp
```

### What Lucid does NOT need

- ❌ No vector database
- ❌ No embeddings — your existing memory search (if any) stays separate
- ❌ No SQLite or any database
- ❌ No external APIs beyond the LLM call
- ❌ No Python, no Node packages, no runtime dependencies

## Trend Detection (v0.5.0)

Lucid now analyzes patterns across the last **14 days** of daily notes:

### 🔁 Recurring Issues
Scans for repeated problem keywords (errors, failures, timeouts, etc.) and clusters similar phrases. If the same issue appears on **3+ separate days**, it's flagged as a Recurring Issue.

### 🕸️ Stale Projects
Tracks projects listed in MEMORY.md. If a project hasn't been mentioned in **any** daily note for 30+ days, it's flagged as Possibly Stale with its last mention date.

### ⚠️ Escalated Patterns
Detects the same lesson learned or mistake appearing in **3+ daily notes** — a signal that the pattern hasn't been broken despite awareness.

### Output
Trends appear as a `## Trends` section in the nightly review file. Trend data is also persisted in `state.json` under the `trends` key for historical tracking.

### Standalone Usage
```bash
python3 scripts/trend_detection.py \
  --workspace /path/to/workspace \
  --days 14 \
  --stale-days 30 \
  --state memory/review/state.json
```

## Suggestion Tracking

Every suggestion gets tracked in `state.json` so you don't see the same thing twice:

- **pending** → New, waiting for your review
- **accepted** → Done, applied to memory
- **rejected** → Gone, won't come back
- **deferred** → Come back in 14 days

## Auto-Apply Configuration

Lucid can automatically apply high-confidence changes without requiring your review. This is opt-in and configurable.

**Edit `config/auto-apply.md`** to control which categories are auto-applied:

```
config/auto-apply.md
├── ✅ Enabled categories (edit freely)
│   ├── Version numbers
│   ├── New project entries (2+ days mentioned)
│   ├── Infrastructure facts (cron IDs, ports, paths)
│   ├── Lessons Learned (factual only)
│   ├── Closed Open Loops
│   └── Stale project status
└── ❌ Never auto-applied (hardcoded)
    ├── Belief updates / opinions
    ├── Key decisions
    ├── Family/personal facts
    └── Anything with medium or low confidence
```

**Conservative setup?** Remove all enabled categories — Lucid still generates suggestions but never applies them.

**Aggressive setup?** Keep all categories — just watch for false positives early on.

All auto-applied changes are git-committed with a `dreamer: auto-apply —` prefix so you can always `git revert` them.

## Safety Rules

Lucid is conservative by design:

- Only suggests new facts if mentioned on **2+ separate days**
- Only flags stale entries if the newer info **clearly** replaces the old
- Designed to avoid suggesting passwords, API keys, tokens, or temporary debug info in memory updates
- ⚠️ The skill reads all workspace markdown files. Do not run on a workspace containing unencrypted API keys or secrets in plain markdown files.
- Every suggestion includes a source link to the original daily note
- Auto-apply only triggers on **high confidence** — medium/low always require human review

## Inspiration

Built on ideas from:
- **[Honcho.dev](https://honcho.dev)** — Background "dreaming" over stored conversations
- **[Gigabrain](https://github.com/legendaryvibecoder/gigabrain)** — World model with entities, beliefs, and a suggestion ledger
- **[Nuggets](https://github.com/NeoVertex1/nuggets)** — Promotion of frequently recalled facts to permanent memory

Lucid takes the best concepts from each and implements them with zero infrastructure — just a prompt, a cron, and markdown.

## Roadmap

- [x] V1 — Nightly review, state ledger, human approval
- [x] V1 — Automatic delivery via announce (Telegram/Discord/etc.)
- [x] V1.5 — Auto-apply for high-confidence, low-risk suggestions (git-backed, revertable)
- [x] V1.5 — Configurable auto-apply categories via `config/auto-apply.md`
- [x] V1.5 — Stricter confidence gate: medium/low never auto-applied
- [x] V1.5 — Trend Detection: recurring issues, stale projects, escalated patterns (14-day window)
- [ ] V2 — Embedding-based dedup for similar suggestions
- [ ] V2 — Auto-promotion (facts referenced N times → suggest for memory)
- [ ] V2 — Weekly consolidation
- [ ] V3 — Publish as OpenClaw skill on ClawHub

For technical details, see [ARCHITECTURE.md](ARCHITECTURE.md).

## License

MIT
